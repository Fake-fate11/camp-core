#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_non_turn_logit_interaction_payload import (  # noqa: E402
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_ATOM_CANDIDATE_NAMES,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_DIAGNOSTIC_FIELD_NAMES,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_LATENCY_KEYS,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_SCHEMA_VERSION,
)


LOG_NAME = "camp_selection_log.json"
PAYLOAD_KEY = "non_turn_logit_interaction_payload_logging"
FORBIDDEN_SEEDS = frozenset({11, 12, 13})
REQUIRED_OUTCOME_FIELDS = frozenset(
    {
        "value",
        "feasible",
        "collision",
        "near_miss",
        "lane_violation",
        "red_light_violation",
        "mean_jerk_mps3",
        "mean_lateral_acceleration_mps2",
    }
)
EXPECTED_PAYLOAD_FLAGS = {
    "schema_version": NON_TURN_LOGIT_INTERACTION_PAYLOAD_SCHEMA_VERSION,
    "enabled": True,
    "default_off": True,
    "selection_effect": False,
    "future_outcome_leakage": False,
    "closed_loop_outcome_fields_read": False,
    "online_selector_change": False,
    "deployed_atom_vector_change": False,
    "classical_benders_claim": False,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed audit for matched DP-CAMP non-turn-logit interaction "
            "payloads and candidate closed-loop outcome labels collected in "
            "the same nonformal replay records. This is read-only and does not "
            "run Diffusion Planner."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--expected_logs", type=int, default=None)
    parser.add_argument("--expected_records", type=int, default=None)
    parser.add_argument("--expected_candidates", type=int, default=8)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--require_pass",
        action="store_true",
        help="Exit with status 2 unless the contract audit passes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(
        paths,
        label=args.label,
        expected_logs=args.expected_logs,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(2)


def analyze(
    paths: list[Path],
    *,
    label: str | None = None,
    expected_logs: int | None = None,
    expected_records: int | None = None,
    expected_candidates: int = 8,
) -> dict[str, Any]:
    log_paths = _discover_logs(paths)
    errors: list[str] = []
    warnings: list[str] = []
    records_total = 0
    payload_records = 0
    outcome_records = 0
    formal_seed_records = 0
    candidate_rows = 0
    max_latency_ms = {
        key: 0.0 for key in NON_TURN_LOGIT_INTERACTION_PAYLOAD_LATENCY_KEYS
    }
    per_log: list[dict[str, Any]] = []

    if expected_logs is not None and len(log_paths) != int(expected_logs):
        errors.append(f"log_count={len(log_paths)} expected={expected_logs}")

    for log_path in log_paths:
        if _path_seeds(log_path) & FORBIDDEN_SEEDS:
            formal_seed_records += 1
        payload = _read_json(log_path)
        if not isinstance(payload, list):
            errors.append(f"{log_path}: selection log must contain a JSON list")
            continue
        if expected_records is not None and len(payload) != int(expected_records):
            errors.append(
                f"{log_path}: record_count={len(payload)} expected={expected_records}"
            )
        log_payload_records = 0
        log_outcome_records = 0
        for record_index, raw in enumerate(payload):
            records_total += 1
            if not isinstance(raw, dict):
                errors.append(f"{log_path} record {record_index}: row is not an object")
                continue
            if _record_seed(raw) in FORBIDDEN_SEEDS:
                formal_seed_records += 1
            record_prefix = f"{log_path} record {record_index}"
            payload_ok = _validate_payload(
                raw,
                record_prefix=record_prefix,
                expected_candidates=expected_candidates,
                errors=errors,
                max_latency_ms=max_latency_ms,
            )
            outcome_ok = _validate_outcomes(
                raw,
                record_prefix=record_prefix,
                expected_candidates=expected_candidates,
                errors=errors,
            )
            payload_records += int(payload_ok)
            outcome_records += int(outcome_ok)
            log_payload_records += int(payload_ok)
            log_outcome_records += int(outcome_ok)
            if payload_ok and outcome_ok:
                candidate_rows += int(expected_candidates)
        per_log.append(
            {
                "selection_log": str(log_path),
                "records": len(payload),
                "payload_records": log_payload_records,
                "outcome_records": log_outcome_records,
            }
        )

    if not log_paths:
        errors.append("no_selection_logs_found")
    if formal_seed_records:
        errors.append(f"formal_seed_records={formal_seed_records}")
    if records_total and payload_records != records_total:
        errors.append(f"payload_records={payload_records} records_total={records_total}")
    if records_total and outcome_records != records_total:
        errors.append(f"outcome_records={outcome_records} records_total={records_total}")

    passed = not errors
    return {
        "analysis": {
            "name": "dp_camp_non_turn_logit_interaction_matched_outcome_contract_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "formal_seeds_forbidden": sorted(FORBIDDEN_SEEDS),
            "math_boundary": (
                "Non-turn-logit interaction payload fields are current-tick "
                "fixed finite-candidate quantities. Candidate closed-loop "
                "outcomes are present only as offline labels in the same "
                "record and are not runtime features. CAMP scoring remains "
                "affine score_k(w)=a_k^T w over fixed nonnegative coefficients, "
                "preserving the simplex/CVaR/L2 convex master. No DP-side "
                "classical Benders dual or cut is constructed."
            ),
        },
        "inputs": {
            "paths": [str(path) for path in paths],
            "selection_logs": [str(path) for path in log_paths],
        },
        "counts": {
            "logs": len(log_paths),
            "records": records_total,
            "payload_records": payload_records,
            "outcome_records": outcome_records,
            "candidate_rows": candidate_rows,
            "expected_candidates": int(expected_candidates),
            "formal_seed_records": formal_seed_records,
        },
        "latency_ms": max_latency_ms,
        "per_log": per_log,
        "validation": {"errors": errors, "warnings": warnings},
        "final_decision": {
            "status": (
                "non_turn_logit_interaction_matched_outcome_contract_passed"
                if passed
                else "non_turn_logit_interaction_matched_outcome_contract_rejected"
            ),
            "passed": passed,
            "authorized_next_work": (
                "non_turn_logit_interaction_outcome_separability_plan_only"
                if passed
                else "fix_non_turn_logit_interaction_matched_outcome_contract"
            ),
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def _validate_payload(
    record: dict[str, Any],
    *,
    record_prefix: str,
    expected_candidates: int,
    errors: list[str],
    max_latency_ms: dict[str, float],
) -> bool:
    initial_error_count = len(errors)
    payload = record.get(PAYLOAD_KEY)
    if not isinstance(payload, dict):
        errors.append(f"{record_prefix}: {PAYLOAD_KEY} missing")
        return False
    for field, expected in EXPECTED_PAYLOAD_FLAGS.items():
        if payload.get(field) != expected:
            errors.append(f"{record_prefix}: {PAYLOAD_KEY}.{field}={payload.get(field)!r}")
    if "candidate_closed_loop_outcomes" in payload:
        errors.append(f"{record_prefix}: interaction payload contains candidate outcomes")
    if record.get("candidate_closed_loop_outcomes") is None:
        errors.append(f"{record_prefix}: record candidate outcomes missing")
    if bool(payload.get("available")) is not True:
        errors.append(f"{record_prefix}: interaction payload unavailable")
    candidate_count = _as_int(payload.get("candidate_count"))
    if candidate_count != int(expected_candidates):
        errors.append(
            f"{record_prefix}: payload candidate_count={candidate_count} "
            f"expected={expected_candidates}"
        )
    if payload.get("diagnostic_field_names") != list(
        NON_TURN_LOGIT_INTERACTION_PAYLOAD_DIAGNOSTIC_FIELD_NAMES
    ):
        errors.append(f"{record_prefix}: diagnostic_field_names mismatch")
    if payload.get("atom_candidate_names") != list(
        NON_TURN_LOGIT_INTERACTION_PAYLOAD_ATOM_CANDIDATE_NAMES
    ):
        errors.append(f"{record_prefix}: atom_candidate_names mismatch")
    finite_checks = payload.get("finite_checks")
    if not isinstance(finite_checks, dict):
        errors.append(f"{record_prefix}: finite_checks missing")
    elif finite_checks.get("payload_valid") is not True:
        errors.append(f"{record_prefix}: finite_checks.payload_valid false")

    _validate_payload_vectors(
        payload,
        record_prefix=record_prefix,
        expected_candidates=expected_candidates,
        errors=errors,
    )
    latency = payload.get("latency_ms")
    if not isinstance(latency, dict):
        errors.append(f"{record_prefix}: payload latency_ms missing")
    else:
        for key in NON_TURN_LOGIT_INTERACTION_PAYLOAD_LATENCY_KEYS:
            value = _as_float(latency.get(key))
            if value is None or value < 0.0 or not np.isfinite(value):
                errors.append(f"{record_prefix}: payload latency {key}={value}")
            else:
                max_latency_ms[key] = max(max_latency_ms[key], value)
            record_value = _as_float(record.get(key))
            if value is not None and record_value is not None and abs(record_value - value) > 1e-9:
                errors.append(f"{record_prefix}: record/payload latency mismatch {key}")
    return len(errors) == initial_error_count


def _validate_payload_vectors(
    payload: dict[str, Any],
    *,
    record_prefix: str,
    expected_candidates: int,
    errors: list[str],
) -> None:
    expected_shape = (int(expected_candidates),)
    values = {
        field: np.asarray(payload.get(field), dtype=np.float64)
        for field in NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES
    }
    for field, array in values.items():
        if array.shape != expected_shape:
            errors.append(f"{record_prefix}: {field} shape={list(array.shape)}")
        elif not np.all(np.isfinite(array)):
            errors.append(f"{record_prefix}: {field} not finite")
        elif not np.all(array >= -1e-12):
            errors.append(f"{record_prefix}: {field} has negative values")
    progress = values["route_progress_deficit_vs_top1_m"]
    jerk = values["dp_prior_jerk_excess_cost"]
    interaction = values["comfort_progress_interaction_cost"]
    if (
        progress.shape == expected_shape
        and jerk.shape == expected_shape
        and interaction.shape == expected_shape
        and not np.allclose(interaction, progress * jerk, atol=1e-9, rtol=1e-9)
    ):
        errors.append(f"{record_prefix}: interaction is not progress_deficit * jerk")
    if progress.shape == expected_shape and abs(float(progress[0])) > 1e-9:
        errors.append(f"{record_prefix}: candidate0 progress deficit is not zero")
    field_shapes = payload.get("field_shapes", {})
    for field in NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES:
        if field_shapes.get(field) != [int(expected_candidates)]:
            errors.append(f"{record_prefix}: field_shapes.{field}={field_shapes.get(field)}")


def _validate_outcomes(
    record: dict[str, Any],
    *,
    record_prefix: str,
    expected_candidates: int,
    errors: list[str],
) -> bool:
    initial_error_count = len(errors)
    outcomes = record.get("candidate_closed_loop_outcomes")
    if not isinstance(outcomes, list) or len(outcomes) != int(expected_candidates):
        errors.append(f"{record_prefix}: candidate_closed_loop_outcomes incomplete")
        return False
    for candidate_idx, outcome in enumerate(outcomes):
        if not isinstance(outcome, dict):
            errors.append(f"{record_prefix}: outcome {candidate_idx} is not an object")
            continue
        missing = sorted(REQUIRED_OUTCOME_FIELDS - set(outcome))
        if missing:
            errors.append(f"{record_prefix}: outcome {candidate_idx} missing {missing}")
        value = _as_float(outcome.get("value"))
        if value is None or not np.isfinite(value):
            errors.append(f"{record_prefix}: outcome {candidate_idx} value invalid")
    return len(errors) == initial_error_count


def _discover_logs(paths: list[Path]) -> list[Path]:
    logs: list[Path] = []
    for path in paths:
        if path.is_file():
            logs.append(path)
        elif path.is_dir():
            logs.extend(sorted(path.rglob(LOG_NAME)))
    return sorted(dict.fromkeys(logs))


def _path_seeds(path: Path) -> set[int]:
    return {
        int(match.group(1))
        for match in re.finditer(r"(?:^|[/\\])seed[_-]?(\d+)(?:[/\\]|$)", str(path))
    }


def _record_seed(record: dict[str, Any]) -> int | None:
    for key in ("seed", "scenario_seed"):
        value = record.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        for key in ("seed", "scenario_seed"):
            value = metadata.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
    return None


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP CAMP Non-Turn-Logit Interaction Matched Outcome Contract Audit",
        "",
        "This read-only audit requires every checked selection-log record to carry "
        "both a no-leak interaction payload and offline candidate outcome labels "
        "in the same fixed candidate ordering.",
        "",
        "## Counts",
        "",
        "```json",
        json.dumps(report["counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Latency Maxima",
        "",
        "| Field | Max ms |",
        "| --- | ---: |",
    ]
    for key, value in report["latency_ms"].items():
        lines.append(f"| `{key}` | `{value:.6f}` |")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"status=`{report['final_decision']['status']}`",
            f"passed=`{report['final_decision']['passed']}`",
            "",
            "## Validation Errors",
            "",
        ]
    )
    errors = report["validation"]["errors"]
    lines.extend(f"- {error}" for error in errors) if errors else lines.append("- none")
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
