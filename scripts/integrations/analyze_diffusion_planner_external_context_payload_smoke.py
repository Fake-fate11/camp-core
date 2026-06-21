#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from camp_core.integrations.diffusion_planner_external_context_payload import (
    EXTERNAL_CONTEXT_PAYLOAD_FIELD_NAMES,
    EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS,
    EXTERNAL_CONTEXT_PAYLOAD_SCHEMA_VERSION,
)


FORMAL_SEEDS = frozenset({11, 12, 13})
READY_STATUS = "external_context_payload_smoke_audit_passed"
REJECT_STATUS = "external_context_payload_smoke_audit_rejected"
ANALYSIS_NAME = "dp_camp_external_context_payload_smoke_audit_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit paired default-off external-context payload smoke outputs. "
            "This reads replay logs only; it does not execute Diffusion Planner."
        )
    )
    parser.add_argument("--baseline_root", type=Path, required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--expected_logs", type=int, required=True)
    parser.add_argument("--expected_records", type=int, required=True)
    parser.add_argument("--expected_candidates", type=int, required=True)
    parser.add_argument("--min_available_records", type=int, default=1)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        baseline_root=args.baseline_root,
        candidate_root=args.candidate_root,
        expected_logs=args.expected_logs,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        min_available_records=args.min_available_records,
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
        raise SystemExit(1)


def analyze(
    *,
    baseline_root: Path,
    candidate_root: Path,
    expected_logs: int,
    expected_records: int,
    expected_candidates: int,
    min_available_records: int = 1,
) -> dict[str, Any]:
    baseline_records = _load_json(baseline_root / "camp_selection_log.json")
    candidate_records = _load_json(candidate_root / "camp_selection_log.json")
    baseline_summary = _load_json(baseline_root / "camp_validation_summary.json")
    candidate_summary = _load_json(candidate_root / "camp_validation_summary.json")

    errors: list[str] = []
    record_reports = [
        _record_report(record, expected_candidates=expected_candidates)
        for record in candidate_records
    ]
    counts = {
        "baseline_records": len(baseline_records),
        "candidate_records": len(candidate_records),
        "candidate_payload_records": sum(
            1 for row in record_reports if row["payload_present"]
        ),
        "available_payload_records": sum(
            1 for row in record_reports if row["available"] is True
        ),
        "route_speed_available_records": sum(
            1 for row in record_reports if row["route_speed_context_available"] is True
        ),
        "traffic_signal_available_records": sum(
            1
            for row in record_reports
            if row["traffic_signal_context_available"] is True
        ),
    }

    errors.extend(
        _summary_errors(
            summary=baseline_summary,
            expected_enabled=False,
            expected_logs=0,
            expected_records=expected_records,
            prefix="baseline",
        )
    )
    errors.extend(
        _summary_errors(
            summary=candidate_summary,
            expected_enabled=True,
            expected_logs=expected_logs,
            expected_records=expected_records,
            prefix="candidate",
        )
    )
    if len(baseline_records) != expected_records:
        errors.append(
            f"baseline_record_count expected {expected_records}, got {len(baseline_records)}"
        )
    if len(candidate_records) != expected_records:
        errors.append(
            f"candidate_record_count expected {expected_records}, got {len(candidate_records)}"
        )
    if counts["candidate_payload_records"] != expected_records:
        errors.append(
            "candidate_payload_records expected "
            f"{expected_records}, got {counts['candidate_payload_records']}"
        )
    if counts["available_payload_records"] < min_available_records:
        errors.append(
            "available_payload_records expected >= "
            f"{min_available_records}, got {counts['available_payload_records']}"
        )
    for root_name, root in (("baseline", baseline_root), ("candidate", candidate_root)):
        formal = _formal_seed_in_path(root)
        if formal is not None:
            errors.append(f"{root_name}_formal_seed_detected={formal}")

    for idx, row in enumerate(record_reports):
        for error in row["errors"]:
            errors.append(f"record[{idx}].{error}")

    latency = {
        key: _summary(
            [
                float(record[key])
                for record in candidate_records
                if key in record and record[key] is not None
            ]
        )
        for key in EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS
    }
    passed = not errors
    return {
        "analysis": {
            "name": ANALYSIS_NAME,
            "baseline_root": str(baseline_root),
            "candidate_root": str(candidate_root),
            "expected_logs": expected_logs,
            "expected_records": expected_records,
            "expected_candidates": expected_candidates,
            "min_available_records": min_available_records,
            "future_outcome_labels_used": False,
            "selection_effect_allowed": False,
            "math_boundary": (
                "This audit checks default-off current-tick external-context "
                "payload logs only. The payload fields are fixed finite-candidate "
                "coefficients or fail-closed diagnostics. The audit does not "
                "train CAMP, change selection, execute DP, or claim classical "
                "Benders."
            ),
        },
        "counts": counts,
        "latency_ms": latency,
        "record_reports": record_reports,
        "errors": errors,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": (
                "evaluate_external_context_payload_smoke_result" if passed else None
            ),
            "closed_loop_smoke_authorized": False,
            "online_selector_authorized": False,
            "camp_retraining_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def _record_report(record: dict[str, Any], *, expected_candidates: int) -> dict[str, Any]:
    payload = record.get("external_context_payload_logging")
    errors: list[str] = []
    if payload is None:
        return {
            "payload_present": False,
            "available": False,
            "route_speed_context_available": False,
            "traffic_signal_context_available": False,
            "errors": ["external_context_payload_logging_missing"],
        }

    if payload.get("schema_version") != EXTERNAL_CONTEXT_PAYLOAD_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    for key in (
        "selection_effect",
        "future_outcome_leakage",
        "closed_loop_outcome_fields_read",
        "online_selector_change",
        "deployed_atom_vector_change",
        "classical_benders_claim",
    ):
        if bool(payload.get(key)):
            errors.append(f"{key}_must_be_false")
    if record.get("candidate_closed_loop_outcomes") is not None:
        errors.append("candidate_closed_loop_outcomes_present")
    if int(payload.get("candidate_count", -1)) != expected_candidates:
        errors.append(
            f"candidate_count expected {expected_candidates}, got {payload.get('candidate_count')}"
        )
    for key in EXTERNAL_CONTEXT_PAYLOAD_FIELD_NAMES:
        if key not in payload:
            errors.append(f"{key}_missing")
    for key in EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS:
        value = record.get(key, payload.get("latency_ms", {}).get(key))
        if value is None or not np.isfinite(float(value)) or float(value) < 0.0:
            errors.append(f"{key}_invalid")
    checks = payload.get("finite_checks") or {}
    if payload.get("available") is True and checks.get("payload_valid") is not True:
        errors.append("available_payload_without_finite_checks.payload_valid")
    _check_nonnegative_list(
        payload,
        "candidate_right_of_way_blocked_indicator",
        errors,
        binary=True,
    )
    _check_nonnegative_list(payload, "candidate_route_speed_limit_min_mps", errors)
    _check_nonnegative_list(
        payload,
        "candidate_speed_limit_excess_integral_mps",
        errors,
    )
    _check_unit_interval_list(
        payload,
        "candidate_speed_limit_available_fraction",
        errors,
    )
    return {
        "payload_present": True,
        "available": bool(payload.get("available")),
        "route_speed_context_available": bool(
            payload.get("route_speed_context_available")
        ),
        "traffic_signal_context_available": bool(
            payload.get("traffic_signal_context_available")
        ),
        "errors": errors,
    }


def _summary_errors(
    *,
    summary: dict[str, Any],
    expected_enabled: bool,
    expected_logs: int,
    expected_records: int,
    prefix: str,
) -> list[str]:
    errors: list[str] = []
    meta = summary.get("camp_external_context_payload_logging")
    if meta is None:
        errors.append(f"{prefix}_summary_missing")
        return errors
    if bool(meta.get("enabled")) is not expected_enabled:
        errors.append(f"{prefix}_summary_enabled_mismatch")
    if bool(meta.get("selection_effect")):
        errors.append(f"{prefix}_summary_selection_effect_true")
    if bool(meta.get("future_outcome_leakage")):
        errors.append(f"{prefix}_summary_future_outcome_leakage_true")
    if bool(meta.get("closed_loop_outcome_fields_read")):
        errors.append(f"{prefix}_summary_closed_loop_outcome_fields_read_true")
    if bool(meta.get("classical_benders_claim")):
        errors.append(f"{prefix}_summary_classical_benders_claim_true")
    if expected_enabled and int(meta.get("records", -1)) != expected_records:
        errors.append(f"{prefix}_summary_records_mismatch")
    if not expected_enabled and int(meta.get("records", 0)) != expected_logs:
        errors.append(f"{prefix}_summary_records_mismatch")
    return errors


def _check_nonnegative_list(
    payload: dict[str, Any],
    key: str,
    errors: list[str],
    *,
    binary: bool = False,
) -> None:
    values = payload.get(key)
    if values is None:
        return
    array = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(array)):
        errors.append(f"{key}_nonfinite")
    if not np.all(array >= -1e-12):
        errors.append(f"{key}_negative")
    if binary and not np.all((array == 0.0) | (array == 1.0)):
        errors.append(f"{key}_not_binary")


def _check_unit_interval_list(
    payload: dict[str, Any],
    key: str,
    errors: list[str],
) -> None:
    values = payload.get(key)
    if values is None:
        return
    array = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(array)):
        errors.append(f"{key}_nonfinite")
    if not np.all((array >= -1e-12) & (array <= 1.0 + 1e-12)):
        errors.append(f"{key}_outside_unit_interval")


def _formal_seed_in_path(path: Path) -> int | None:
    text = str(path).replace("\\", "/")
    for seed in FORMAL_SEEDS:
        if f"seed_{seed}" in text or f"/{seed}/" in text:
            return seed
    return None


def _summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "mean": None, "max": None}
    array = np.asarray(values, dtype=np.float64)
    return {
        "count": int(array.size),
        "min": float(np.min(array)),
        "mean": float(np.mean(array)),
        "max": float(np.max(array)),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# External Context Payload Smoke Audit",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- errors: `{len(report['errors'])}`",
        "",
        "## Counts",
        "",
    ]
    lines.extend(f"- `{key}`: `{value}`" for key, value in report["counts"].items())
    lines.extend(["", "## Latency", ""])
    for key, value in report["latency_ms"].items():
        lines.append(f"- `{key}`: `{value}`")
    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in report["errors"])
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
