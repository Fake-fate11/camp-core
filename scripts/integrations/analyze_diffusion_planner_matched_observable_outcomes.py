#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import numpy as np


LOG_NAME = "camp_selection_log.json"
OBSERVABLE_SCHEMA_VERSION = "dp_camp_observable_state_logging_v1"
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
EXPECTED_OBSERVABLE_FLAGS = {
    "schema_version": OBSERVABLE_SCHEMA_VERSION,
    "enabled": True,
    "default_off": True,
    "selection_effect": False,
    "future_outcome_leakage": False,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed audit for matched DP-CAMP observable-state payloads and "
            "candidate outcome labels collected in the same nonformal replay "
            "records. This is read-only and does not run Diffusion Planner."
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
    observable_records = 0
    outcome_records = 0
    formal_seed_records = 0
    candidate_rows = 0
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
        log_observable_records = 0
        log_outcome_records = 0
        for record_index, raw in enumerate(payload):
            records_total += 1
            if not isinstance(raw, dict):
                errors.append(f"{log_path} record {record_index}: row is not an object")
                continue
            if _record_seed(raw) in FORBIDDEN_SEEDS:
                formal_seed_records += 1
            record_prefix = f"{log_path} record {record_index}"
            observable_ok = _validate_observable_payload(
                raw,
                record_prefix=record_prefix,
                expected_candidates=expected_candidates,
                errors=errors,
            )
            outcome_ok = _validate_outcomes(
                raw,
                record_prefix=record_prefix,
                expected_candidates=expected_candidates,
                errors=errors,
            )
            observable_records += int(observable_ok)
            outcome_records += int(outcome_ok)
            log_observable_records += int(observable_ok)
            log_outcome_records += int(outcome_ok)
            if observable_ok and outcome_ok:
                candidate_rows += int(expected_candidates)
        per_log.append(
            {
                "selection_log": str(log_path),
                "records": len(payload),
                "observable_records": log_observable_records,
                "outcome_records": log_outcome_records,
            }
        )

    if not log_paths:
        errors.append("no_selection_logs_found")
    if formal_seed_records:
        errors.append(f"formal_seed_records={formal_seed_records}")
    if records_total and observable_records != records_total:
        errors.append(
            f"observable_records={observable_records} records_total={records_total}"
        )
    if records_total and outcome_records != records_total:
        errors.append(f"outcome_records={outcome_records} records_total={records_total}")

    passed = not errors
    return {
        "analysis": {
            "name": "dp_camp_matched_observable_outcome_contract_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "formal_seeds_forbidden": sorted(FORBIDDEN_SEEDS),
            "math_boundary": (
                "Observable-state descriptors are current-tick fixed "
                "finite-candidate quantities. Candidate closed-loop outcomes "
                "are present only as offline labels in the same record and are "
                "not runtime features. CAMP scoring remains affine "
                "score_k(w)=a_k^T w over fixed atoms, preserving the "
                "simplex/CVaR/L2 convex master. No DP-side classical Benders "
                "dual or cut is constructed."
            ),
        },
        "inputs": {
            "paths": [str(path) for path in paths],
            "selection_logs": [str(path) for path in log_paths],
        },
        "counts": {
            "logs": len(log_paths),
            "records": records_total,
            "observable_records": observable_records,
            "outcome_records": outcome_records,
            "candidate_rows": candidate_rows,
            "expected_candidates": int(expected_candidates),
            "formal_seed_records": formal_seed_records,
        },
        "per_log": per_log,
        "validation": {"errors": errors, "warnings": warnings},
        "final_decision": {
            "status": (
                "matched_observable_outcome_contract_passed"
                if passed
                else "matched_observable_outcome_contract_rejected"
            ),
            "passed": passed,
            "authorized_next_work": (
                "offline_observable_descriptor_separability_screen_only"
                if passed
                else "fix_matched_label_collection_before_separability"
            ),
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
        },
    }


def _validate_observable_payload(
    record: dict[str, Any],
    *,
    record_prefix: str,
    expected_candidates: int,
    errors: list[str],
) -> bool:
    payload = record.get("observable_state_logging")
    if not isinstance(payload, dict):
        errors.append(f"{record_prefix}: observable_state_logging missing")
        return False
    for field, expected in EXPECTED_OBSERVABLE_FLAGS.items():
        if payload.get(field) != expected:
            errors.append(
                f"{record_prefix}: observable_state_logging.{field}="
                f"{payload.get(field)!r}"
            )
    if "candidate_closed_loop_outcomes" in payload:
        errors.append(
            f"{record_prefix}: observable payload contains candidate outcomes"
        )
    candidate_count = _as_int(payload.get("candidate_count"))
    if candidate_count != int(expected_candidates):
        errors.append(
            f"{record_prefix}: observable candidate_count={candidate_count} "
            f"expected={expected_candidates}"
        )
    finite_checks = payload.get("finite_checks")
    if not isinstance(finite_checks, dict) or not finite_checks:
        errors.append(f"{record_prefix}: observable finite_checks missing")
    else:
        failed = sorted(field for field, value in finite_checks.items() if not value)
        if failed:
            errors.append(f"{record_prefix}: observable finite checks failed {failed}")
    return not any(error.startswith(record_prefix) for error in errors)


def _validate_outcomes(
    record: dict[str, Any],
    *,
    record_prefix: str,
    expected_candidates: int,
    errors: list[str],
) -> bool:
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
    return not any(error.startswith(record_prefix) for error in errors)


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
        "# DP CAMP Matched Observable Outcome Contract Audit",
        "",
        "This read-only audit requires every checked selection-log record to carry "
        "both a no-leak observable-state payload and offline candidate outcome "
        "labels in the same fixed candidate ordering.",
        "",
        "## Counts",
        "",
        "```json",
        json.dumps(report["counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Decision",
        "",
        f"status=`{report['final_decision']['status']}`",
        f"passed=`{report['final_decision']['passed']}`",
        "",
        "## Validation Errors",
        "",
    ]
    errors = report["validation"]["errors"]
    lines.extend(f"- {error}" for error in errors) if errors else lines.append("- none")
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
