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

from camp_core.integrations.diffusion_planner_turn_logit_payload import (  # noqa: E402
    TURN_LOGIT_PAYLOAD_ATOM_CANDIDATE_NAMES,
    TURN_LOGIT_PAYLOAD_FIELD_NAMES,
    TURN_LOGIT_PAYLOAD_LATENCY_KEYS,
    TURN_LOGIT_PAYLOAD_SCHEMA_VERSION,
)


LOG_NAME = "camp_selection_log.json"
SUMMARY_NAME = "camp_validation_summary.json"
PAYLOAD_KEY = "turn_logit_payload_logging"
SUMMARY_KEY = "camp_turn_logit_payload_logging"
FORBIDDEN_SEEDS = frozenset({11, 12, 13})
FORBIDDEN_PAYLOAD_KEYS = (
    "candidate_closed_loop_outcomes",
    "closed_loop_outcomes",
    "realized_outcomes",
    "future_outcome_labels",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit a paired default-off turn-logit payload smoke. The baseline "
            "run keeps logging disabled; the candidate run enables only "
            "--camp_turn_logit_payload_logging."
        )
    )
    parser.add_argument("--baseline_root", type=Path, required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--expected_logs", type=int, default=1)
    parser.add_argument("--expected_records", type=int, default=3)
    parser.add_argument("--expected_candidates", type=int, default=8)
    parser.add_argument(
        "--require_pass",
        action="store_true",
        help="Exit with status 2 unless the smoke audit passes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        baseline_root=args.baseline_root,
        candidate_root=args.candidate_root,
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
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(2)


def analyze(
    *,
    baseline_root: Path,
    candidate_root: Path,
    expected_logs: int = 1,
    expected_records: int = 3,
    expected_candidates: int = 8,
) -> dict[str, Any]:
    baseline_logs = _discover_logs(baseline_root)
    candidate_logs = _discover_logs(candidate_root)
    errors: list[str] = []
    warnings: list[str] = []

    if len(baseline_logs) != int(expected_logs):
        errors.append(
            f"baseline_log_count={len(baseline_logs)} expected={expected_logs}"
        )
    if len(candidate_logs) != int(expected_logs):
        errors.append(
            f"candidate_log_count={len(candidate_logs)} expected={expected_logs}"
        )
    if set(baseline_logs) != set(candidate_logs):
        errors.append(
            "paired_log_keys_mismatch="
            f"missing={sorted(set(baseline_logs) - set(candidate_logs))},"
            f"unexpected={sorted(set(candidate_logs) - set(baseline_logs))}"
        )

    forbidden_seen = sorted(
        {
            seed
            for path in [*baseline_logs.values(), *candidate_logs.values()]
            for seed in _path_seeds(path)
            if seed in FORBIDDEN_SEEDS
        }
    )
    if forbidden_seen:
        errors.append(f"formal_seed_detected={forbidden_seen}")

    baseline_payload_records = 0
    candidate_payload_records = 0
    available_payload_records = 0
    invalid_payload_records = 0
    total_records = 0
    max_latency_ms = {key: 0.0 for key in TURN_LOGIT_PAYLOAD_LATENCY_KEYS}
    record_reports: list[dict[str, Any]] = []

    for key in sorted(set(baseline_logs) & set(candidate_logs)):
        baseline_rows = _read_json(baseline_logs[key])
        candidate_rows = _read_json(candidate_logs[key])
        if not isinstance(baseline_rows, list) or not isinstance(candidate_rows, list):
            errors.append(f"{key}: selection logs must contain JSON lists")
            continue
        if len(baseline_rows) != len(candidate_rows):
            errors.append(
                f"{key}: record_count_mismatch={len(baseline_rows)}!={len(candidate_rows)}"
            )
            continue
        if len(candidate_rows) != int(expected_records):
            errors.append(
                f"{key}: record_count={len(candidate_rows)} expected={expected_records}"
            )
        total_records += len(candidate_rows)

        baseline_summary = _load_summary_for_log(baseline_logs[key], errors)
        candidate_summary = _load_summary_for_log(candidate_logs[key], errors)
        _validate_summary(
            baseline_summary,
            key=key,
            expected_enabled=False,
            expected_records=0,
            errors=errors,
        )
        _validate_summary(
            candidate_summary,
            key=key,
            expected_enabled=True,
            expected_records=len(candidate_rows),
            errors=errors,
        )

        for idx, (baseline, candidate) in enumerate(zip(baseline_rows, candidate_rows)):
            if not isinstance(baseline, dict) or not isinstance(candidate, dict):
                errors.append(f"{key} record {idx}: rows must be objects")
                continue
            baseline_payload = baseline.get(PAYLOAD_KEY)
            candidate_payload = candidate.get(PAYLOAD_KEY)
            if baseline_payload is not None:
                baseline_payload_records += 1
                errors.append(f"{key} record {idx}: baseline payload is not disabled")
            for latency_key in TURN_LOGIT_PAYLOAD_LATENCY_KEYS:
                latency = float(baseline.get(latency_key, 0.0))
                if abs(latency) > 1e-12:
                    errors.append(
                        f"{key} record {idx}: disabled baseline latency "
                        f"{latency_key}={latency}"
                    )
            if candidate_payload is None:
                errors.append(f"{key} record {idx}: candidate payload missing")
                continue
            candidate_payload_records += 1
            payload_report = _validate_payload(
                candidate_payload,
                record=candidate,
                key=key,
                record_index=idx,
                expected_candidates=expected_candidates,
                errors=errors,
            )
            if payload_report["available"]:
                available_payload_records += 1
            if not payload_report["payload_valid"]:
                invalid_payload_records += 1
            for latency_key in TURN_LOGIT_PAYLOAD_LATENCY_KEYS:
                latency = float(candidate.get(latency_key, -1.0))
                if latency < 0.0 or not np.isfinite(latency):
                    errors.append(
                        f"{key} record {idx}: invalid record latency "
                        f"{latency_key}={latency}"
                    )
                max_latency_ms[latency_key] = max(max_latency_ms[latency_key], latency)
            record_reports.append(payload_report)

    if candidate_payload_records != total_records:
        errors.append(
            f"candidate_payload_records={candidate_payload_records} "
            f"total_records={total_records}"
        )

    passed = not errors
    return {
        "analysis": {
            "name": "dp_camp_turn_logit_payload_smoke_audit_v1",
            "future_outcome_labels_used": False,
            "selection_effect": False,
            "formal_seed_records": 0 if not forbidden_seen else len(forbidden_seen),
            "math_boundary": (
                "The audit validates default-off current-tick turn-logit "
                "payload logging only. If later atomized, logged values are "
                "fixed finite-candidate coefficients preserving affine "
                "score_k(w)=a_k^T w and the simplex/CVaR/L2 convex master. "
                "This is not a DP-side classical Benders decomposition."
            ),
        },
        "counts": {
            "baseline_logs": len(baseline_logs),
            "candidate_logs": len(candidate_logs),
            "records": total_records,
            "baseline_payload_records": baseline_payload_records,
            "candidate_payload_records": candidate_payload_records,
            "available_payload_records": available_payload_records,
            "invalid_payload_records": invalid_payload_records,
        },
        "latency_ms": max_latency_ms,
        "record_reports": record_reports,
        "errors": errors,
        "warnings": warnings,
        "final_decision": {
            "status": (
                "turn_logit_payload_smoke_passed"
                if passed
                else "turn_logit_payload_smoke_rejected"
            ),
            "passed": passed,
            "authorized_next_work": (
                "turn_logit_payload_availability_and_latency_result_documentation_only"
                if passed
                else "fix_turn_logit_payload_smoke_before_any_replay_expansion"
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
    payload: Any,
    *,
    record: dict[str, Any],
    key: str,
    record_index: int,
    expected_candidates: int,
    errors: list[str],
) -> dict[str, Any]:
    prefix = f"{key} record {record_index}"
    if not isinstance(payload, dict):
        errors.append(f"{prefix}: payload must be object")
        return {"available": False, "payload_valid": False}
    for forbidden_key in FORBIDDEN_PAYLOAD_KEYS:
        if forbidden_key in payload:
            errors.append(f"{prefix}: payload contains future outcome key {forbidden_key}")
    expected_scalars = {
        "schema_version": TURN_LOGIT_PAYLOAD_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "classical_benders_claim": False,
    }
    for scalar_key, expected in expected_scalars.items():
        if payload.get(scalar_key) != expected:
            errors.append(f"{prefix}: {scalar_key}={payload.get(scalar_key)!r}")
    if int(payload.get("candidate_count", -1)) != int(expected_candidates):
        errors.append(
            f"{prefix}: candidate_count={payload.get('candidate_count')} "
            f"expected={expected_candidates}"
        )
    if payload.get("turn_logit_atomization_candidate_names") != list(
        TURN_LOGIT_PAYLOAD_ATOM_CANDIDATE_NAMES
    ):
        errors.append(f"{prefix}: atomization candidate names mismatch")
    finite_checks = payload.get("finite_checks")
    if not isinstance(finite_checks, dict):
        errors.append(f"{prefix}: finite_checks missing")
        finite_checks = {}
    payload_valid = bool(finite_checks.get("payload_valid", False))
    if not payload_valid:
        errors.append(f"{prefix}: finite_checks.payload_valid is false")

    available = bool(payload.get("available", False))
    if available:
        _validate_available_payload_fields(
            payload,
            prefix=prefix,
            expected_candidates=expected_candidates,
            errors=errors,
        )
    else:
        if not payload.get("availability_reason"):
            errors.append(f"{prefix}: unavailable payload missing reason")
        for field_name in TURN_LOGIT_PAYLOAD_FIELD_NAMES:
            if payload.get(field_name) is not None:
                errors.append(f"{prefix}: unavailable field {field_name} not null")
        if payload.get("turn_logit_atomization_candidates_available") is not False:
            errors.append(f"{prefix}: unavailable atomization flag is not false")

    payload_latency = payload.get("latency_ms", {})
    for latency_key in TURN_LOGIT_PAYLOAD_LATENCY_KEYS:
        latency = float(payload_latency.get(latency_key, -1.0))
        record_latency = float(record.get(latency_key, -1.0))
        if latency < 0.0 or not np.isfinite(latency):
            errors.append(f"{prefix}: invalid payload latency {latency_key}={latency}")
        if abs(latency - record_latency) > 1e-9:
            errors.append(
                f"{prefix}: latency mismatch {latency_key} "
                f"payload={latency} record={record_latency}"
            )
    return {
        "log_key": key,
        "record_index": record_index,
        "candidate_count": payload.get("candidate_count"),
        "available": available,
        "payload_valid": payload_valid,
        "availability_reason": payload.get("availability_reason"),
    }


def _validate_available_payload_fields(
    payload: dict[str, Any],
    *,
    prefix: str,
    expected_candidates: int,
    errors: list[str],
) -> None:
    logits = np.asarray(payload.get("candidate_turn_indicator_logits"), dtype=np.float64)
    probabilities = np.asarray(
        payload.get("candidate_turn_indicator_probabilities"),
        dtype=np.float64,
    )
    top_class = np.asarray(payload.get("candidate_turn_indicator_top_class"))
    if logits.ndim != 2 or logits.shape[0] != int(expected_candidates):
        errors.append(f"{prefix}: logits shape={list(logits.shape)}")
        return
    if probabilities.shape != logits.shape:
        errors.append(f"{prefix}: probabilities shape={list(probabilities.shape)}")
    if top_class.shape != (int(expected_candidates),):
        errors.append(f"{prefix}: top_class shape={list(top_class.shape)}")
    if not np.all(np.isfinite(logits)):
        errors.append(f"{prefix}: logits not finite")
    if not np.all(np.isfinite(probabilities)):
        errors.append(f"{prefix}: probabilities not finite")
    if not np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-9, rtol=1e-9):
        errors.append(f"{prefix}: probabilities row sums not one")
    expected_shapes = {
        "candidate_turn_indicator_logits": list(logits.shape),
        "candidate_turn_indicator_probabilities": list(probabilities.shape),
        "candidate_turn_indicator_top_class": list(top_class.shape),
    }
    field_shapes = payload.get("field_shapes", {})
    for field_name, expected_shape in expected_shapes.items():
        if field_shapes.get(field_name) != expected_shape:
            errors.append(
                f"{prefix}: field_shapes.{field_name}={field_shapes.get(field_name)}"
            )


def _validate_summary(
    summary: dict[str, Any] | None,
    *,
    key: str,
    expected_enabled: bool,
    expected_records: int,
    errors: list[str],
) -> None:
    if summary is None:
        errors.append(f"{key}: summary missing")
        return
    metadata = summary.get(SUMMARY_KEY)
    if not isinstance(metadata, dict):
        errors.append(f"{key}: {SUMMARY_KEY} missing")
        return
    expected_scalars = {
        "schema_version": TURN_LOGIT_PAYLOAD_SCHEMA_VERSION,
        "enabled": expected_enabled,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "classical_benders_claim": False,
    }
    for scalar_key, expected in expected_scalars.items():
        if metadata.get(scalar_key) != expected:
            errors.append(f"{key}: summary {scalar_key}={metadata.get(scalar_key)!r}")
    if int(metadata.get("records", -1)) != int(expected_records):
        errors.append(
            f"{key}: summary records={metadata.get('records')} "
            f"expected={expected_records}"
        )
    if metadata.get("fields") != list(TURN_LOGIT_PAYLOAD_FIELD_NAMES):
        errors.append(f"{key}: summary fields mismatch")
    if metadata.get("atomization_candidate_names") != list(
        TURN_LOGIT_PAYLOAD_ATOM_CANDIDATE_NAMES
    ):
        errors.append(f"{key}: summary atomization candidate names mismatch")
    if metadata.get("latency_fields") != list(TURN_LOGIT_PAYLOAD_LATENCY_KEYS):
        errors.append(f"{key}: summary latency fields mismatch")


def _discover_logs(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    return {
        str(path.parent.relative_to(root)): path
        for path in sorted(root.rglob(LOG_NAME))
    }


def _load_summary_for_log(log_path: Path, errors: list[str]) -> dict[str, Any] | None:
    summary_path = log_path.parent / SUMMARY_NAME
    if not summary_path.exists():
        errors.append(f"{log_path}: missing {SUMMARY_NAME}")
        return None
    summary = _read_json(summary_path)
    if not isinstance(summary, dict):
        errors.append(f"{summary_path}: summary must be object")
        return None
    return summary


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _path_seeds(path: Path) -> set[int]:
    return {int(match) for match in re.findall(r"(?:seed[_-]?)(\d+)", str(path))}


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Turn-Logit Payload Smoke Audit",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Counts",
        "",
    ]
    for key, value in report["counts"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Latency", ""])
    for key, value in report["latency_ms"].items():
        lines.append(f"- {key}: `{value}`")
    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in report["errors"])
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
