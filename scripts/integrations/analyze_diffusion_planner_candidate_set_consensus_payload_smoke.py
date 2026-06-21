#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import numpy as np

from camp_core.integrations.diffusion_planner_candidate_set_consensus_payload import (
    CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES,
    CANDIDATE_SET_CONSENSUS_PAYLOAD_FIELD_NAMES,
    CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS,
    CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
)


LOG_NAME = "camp_selection_log.json"
SUMMARY_NAME = "camp_validation_summary.json"
PAYLOAD_KEY = "candidate_set_consensus_payload_logging"
SUMMARY_KEY = "camp_candidate_set_consensus_payload_logging"
COEFFICIENT_KEY = "candidate_set_consensus_center_rms_m"
RANK_KEY = "candidate_set_consensus_center_rms_rank"
FORBIDDEN_SEEDS = frozenset({11, 12, 13})
READY_STATUS = "candidate_set_consensus_payload_smoke_audit_passed"
REJECT_STATUS = "candidate_set_consensus_payload_smoke_audit_rejected"
ANALYSIS_NAME = "dp_camp_candidate_set_consensus_payload_smoke_audit_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit paired default-off candidate-set consensus payload smoke "
            "outputs. This reads replay logs only; it does not execute "
            "Diffusion Planner."
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
    baseline_logs = _discover_logs(baseline_root)
    candidate_logs = _discover_logs(candidate_root)
    errors: list[str] = []
    record_reports: list[dict[str, Any]] = []
    latency_values: dict[str, list[float]] = {
        key: [] for key in CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS
    }

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
            for latency_key in CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS:
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
            for latency_key in CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS:
                latency = float(candidate.get(latency_key, -1.0))
                if latency < 0.0 or not np.isfinite(latency):
                    errors.append(
                        f"{key} record {idx}: invalid record latency "
                        f"{latency_key}={latency}"
                    )
                else:
                    latency_values[latency_key].append(latency)
            record_reports.append(payload_report)

    if candidate_payload_records != total_records:
        errors.append(
            f"candidate_payload_records={candidate_payload_records} "
            f"total_records={total_records}"
        )
    if available_payload_records < int(min_available_records):
        errors.append(
            "available_payload_records expected >= "
            f"{min_available_records}, got {available_payload_records}"
        )

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
                "This audit checks default-off current-tick candidate-set "
                "consensus payload logs only. The coefficient is a fixed "
                "finite-candidate RMS distance to the candidate-set median "
                "center, nonnegative when available, and fail-closed when the "
                "candidate tensor is insufficient. The audit does not train "
                "CAMP, change selection, execute DP, or claim classical Benders."
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
        "latency_ms": {
            key: _summary(values) for key, values in latency_values.items()
        },
        "record_reports": record_reports,
        "errors": errors,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": (
                "evaluate_candidate_set_consensus_payload_smoke_result"
                if passed
                else None
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
    expected_scalars = {
        "schema_version": CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "deployed_atom_vector_change": False,
        "classical_benders_claim": False,
    }
    for scalar_key, expected in expected_scalars.items():
        if payload.get(scalar_key) != expected:
            errors.append(f"{prefix}: {scalar_key}={payload.get(scalar_key)!r}")
    if record.get("candidate_closed_loop_outcomes") is not None:
        errors.append(f"{prefix}: candidate_closed_loop_outcomes_present")
    if int(payload.get("candidate_count", -1)) != int(expected_candidates):
        errors.append(
            f"{prefix}: candidate_count={payload.get('candidate_count')} "
            f"expected={expected_candidates}"
        )
    if payload.get("atom_candidate_names") != list(
        CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES
    ):
        errors.append(f"{prefix}: atom_candidate_names mismatch")
    for field_name in CANDIDATE_SET_CONSENSUS_PAYLOAD_FIELD_NAMES:
        if field_name not in payload:
            errors.append(f"{prefix}: {field_name}_missing")
    finite_checks = payload.get("finite_checks")
    if not isinstance(finite_checks, dict):
        errors.append(f"{prefix}: finite_checks missing")
        finite_checks = {}
    payload_valid = bool(finite_checks.get("payload_valid", False))
    available = bool(payload.get("available", False))
    if available:
        if not payload_valid:
            errors.append(f"{prefix}: available payload has invalid finite checks")
        _validate_available_payload_fields(
            payload,
            prefix=prefix,
            expected_candidates=expected_candidates,
            errors=errors,
        )
    else:
        if not payload.get("availability_reason"):
            errors.append(f"{prefix}: unavailable payload missing reason")
        if payload.get(COEFFICIENT_KEY) is not None:
            errors.append(f"{prefix}: unavailable payload has coefficient values")

    payload_latency = payload.get("latency_ms", {})
    for latency_key in CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS:
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
    costs = np.asarray(payload.get(COEFFICIENT_KEY), dtype=np.float64)
    ranks = np.asarray(payload.get(RANK_KEY), dtype=np.int64)
    center = np.asarray(
        payload.get("candidate_set_consensus_center_xy"),
        dtype=np.float64,
    )
    if costs.shape != (int(expected_candidates),):
        errors.append(f"{prefix}: {COEFFICIENT_KEY}_shape={list(costs.shape)}")
    if ranks.shape != (int(expected_candidates),):
        errors.append(f"{prefix}: {RANK_KEY}_shape={list(ranks.shape)}")
    if center.ndim != 2 or center.shape[1] != 2:
        errors.append(f"{prefix}: candidate_set_consensus_center_xy_shape={list(center.shape)}")
    if not np.all(np.isfinite(costs)):
        errors.append(f"{prefix}: {COEFFICIENT_KEY}_nonfinite")
    if not np.all(costs >= -1e-12):
        errors.append(f"{prefix}: {COEFFICIENT_KEY}_negative")
    if not np.array_equal(np.sort(ranks), np.arange(int(expected_candidates))):
        errors.append(f"{prefix}: {RANK_KEY}_not_permutation")
    median_value = payload.get("candidate_set_consensus_center_rms_median_m")
    mad_value = payload.get("candidate_set_consensus_center_rms_mad_m")
    if median_value is None or not np.isfinite(float(median_value)):
        errors.append(f"{prefix}: rms_median_invalid")
    if mad_value is None or not np.isfinite(float(mad_value)) or float(mad_value) < 0.0:
        errors.append(f"{prefix}: rms_mad_invalid")
    field_shapes = payload.get("field_shapes", {})
    expected_shapes = {
        COEFFICIENT_KEY: [int(expected_candidates)],
        RANK_KEY: [int(expected_candidates)],
        "candidate_set_consensus_center_xy": list(center.shape),
        "candidate_set_consensus_center_rms_median_m": [],
        "candidate_set_consensus_center_rms_mad_m": [],
    }
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
        "schema_version": CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
        "enabled": expected_enabled,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "deployed_atom_vector_change": False,
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
    if metadata.get("fields") != list(CANDIDATE_SET_CONSENSUS_PAYLOAD_FIELD_NAMES):
        errors.append(f"{key}: summary fields mismatch")
    if metadata.get("atom_candidate_names") != list(
        CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES
    ):
        errors.append(f"{key}: summary atom candidate names mismatch")
    if metadata.get("latency_fields") != list(
        CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS
    ):
        errors.append(f"{key}: summary latency fields mismatch")


def _discover_logs(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    return {str(path.parent.relative_to(root)): path for path in sorted(root.rglob(LOG_NAME))}


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
        "# Candidate-Set Consensus Payload Smoke Audit",
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


if __name__ == "__main__":
    main()
