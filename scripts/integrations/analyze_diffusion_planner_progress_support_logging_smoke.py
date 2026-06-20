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

from camp_core.integrations.diffusion_planner_progress_support import (  # noqa: E402
    PROGRESS_SUPPORT_ATOM_NAMES,
    PROGRESS_SUPPORT_FIELD_NAMES,
    PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
)


LOG_NAME = "camp_selection_log.json"
SUMMARY_NAME = "camp_validation_summary.json"
LATENCY_FIELDS = ("latency_ms_progress_support_logging",)
FORBIDDEN_SEEDS = frozenset({11, 12, 13})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit a paired default-off progress-support logging smoke. The "
            "baseline run must keep logging disabled and the candidate run must "
            "enable progress-support logging without collecting future outcomes."
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

    record_reports: list[dict[str, Any]] = []
    baseline_payload_records = 0
    candidate_payload_records = 0
    total_records = 0
    max_latency_ms = {key: 0.0 for key in LATENCY_FIELDS}

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
            errors=errors,
        )
        _validate_summary(
            candidate_summary,
            key=key,
            expected_enabled=True,
            errors=errors,
        )

        for idx, (baseline, candidate) in enumerate(zip(baseline_rows, candidate_rows)):
            if not isinstance(baseline, dict) or not isinstance(candidate, dict):
                errors.append(f"{key} record {idx}: rows must be objects")
                continue
            baseline_payload = baseline.get("progress_support_logging")
            candidate_payload = candidate.get("progress_support_logging")
            if baseline_payload is not None:
                baseline_payload_records += 1
                errors.append(f"{key} record {idx}: baseline payload is not disabled")
            for latency_key in LATENCY_FIELDS:
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
            _validate_payload(
                candidate_payload,
                record=candidate,
                key=key,
                record_index=idx,
                expected_candidates=expected_candidates,
                errors=errors,
            )
            for latency_key in LATENCY_FIELDS:
                latency = float(candidate.get(latency_key, -1.0))
                if latency < 0.0 or not np.isfinite(latency):
                    errors.append(
                        f"{key} record {idx}: invalid record latency "
                        f"{latency_key}={latency}"
                    )
                max_latency_ms[latency_key] = max(
                    max_latency_ms[latency_key],
                    latency,
                )
            record_reports.append(
                {
                    "log_key": key,
                    "record_index": idx,
                    "candidate_count": candidate_payload.get("candidate_count"),
                    "support_steps": candidate_payload.get("horizons", {}).get(
                        "support_steps"
                    ),
                    "atom_count": len(
                        candidate_payload.get("progress_support_atom_names", [])
                    ),
                }
            )

    if candidate_payload_records != total_records:
        errors.append(
            f"candidate_payload_records={candidate_payload_records} "
            f"total_records={total_records}"
        )

    return {
        "analysis": {
            "name": "dp_camp_progress_support_logging_smoke_audit_v1",
            "baseline_root": str(baseline_root),
            "candidate_root": str(candidate_root),
            "schema_version": PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
            "expected_logs": int(expected_logs),
            "expected_records": int(expected_records),
            "expected_candidates": int(expected_candidates),
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_labels_allowed": False,
            "formal_seeds_forbidden": sorted(FORBIDDEN_SEEDS),
            "math_boundary": (
                "Progress-support payloads are current-tick finite-candidate "
                "geometry diagnostics. Logged atoms are fixed nonnegative "
                "candidate coefficients and preserve affine CAMP scores in "
                "weights."
            ),
        },
        "counts": {
            "paired_logs": len(set(baseline_logs) & set(candidate_logs)),
            "records": total_records,
            "baseline_payload_records": baseline_payload_records,
            "candidate_payload_records": candidate_payload_records,
        },
        "latency_ms": max_latency_ms,
        "records": record_reports,
        "warnings": warnings,
        "errors": errors,
        "final_decision": {
            "status": (
                "progress_support_logging_smoke_passed"
                if not errors
                else "progress_support_logging_smoke_rejected"
            ),
            "passed": not errors,
            "authorized_next_work": (
                "progress_support_logging_smoke_result_documentation_only"
                if not errors
                else None
            ),
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
        },
    }


def _discover_logs(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    return {
        str(path.parent.relative_to(root)): path
        for path in root.rglob(LOG_NAME)
    }


def _load_summary_for_log(log_path: Path, errors: list[str]) -> dict[str, Any]:
    path = log_path.parent / SUMMARY_NAME
    if not path.is_file():
        errors.append(f"missing_summary={path}")
        return {}
    summary = _read_json(path)
    if not isinstance(summary, dict):
        errors.append(f"summary_not_object={path}")
        return {}
    return summary


def _validate_summary(
    summary: dict[str, Any],
    *,
    key: str,
    expected_enabled: bool,
    errors: list[str],
) -> None:
    metadata = summary.get("camp_progress_support_logging")
    if not isinstance(metadata, dict):
        errors.append(f"{key}: missing camp_progress_support_logging summary")
        return
    expected = {
        "schema_version": PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
        "enabled": expected_enabled,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "classical_benders_claim": False,
    }
    for field, value in expected.items():
        if metadata.get(field) != value:
            errors.append(
                f"{key}: summary {field}={metadata.get(field)!r} expected={value!r}"
            )
    if expected_enabled and int(metadata.get("records", -1)) <= 0:
        errors.append(f"{key}: enabled summary has no progress-support records")
    if expected_enabled and metadata.get("fields") != list(PROGRESS_SUPPORT_FIELD_NAMES):
        errors.append(f"{key}: summary field list mismatch")
    if expected_enabled and metadata.get("atom_names") != list(PROGRESS_SUPPORT_ATOM_NAMES):
        errors.append(f"{key}: summary atom list mismatch")
    if expected_enabled and metadata.get("latency_fields") != list(LATENCY_FIELDS):
        errors.append(f"{key}: summary latency field list mismatch")


def _validate_payload(
    payload: dict[str, Any],
    *,
    record: dict[str, Any],
    key: str,
    record_index: int,
    expected_candidates: int,
    errors: list[str],
) -> None:
    prefix = f"{key} record {record_index}"
    expected = {
        "schema_version": PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "classical_benders_claim": False,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            errors.append(f"{prefix}: payload {field}={payload.get(field)!r}")
    if "candidate_closed_loop_outcomes" in payload:
        errors.append(f"{prefix}: payload contains future outcome key")
    if record.get("candidate_closed_loop_outcomes") is not None:
        errors.append(f"{prefix}: record contains closed-loop outcomes")
    if int(payload.get("candidate_count", -1)) != int(expected_candidates):
        errors.append(f"{prefix}: candidate_count mismatch")

    horizons = payload.get("horizons")
    if not isinstance(horizons, dict):
        errors.append(f"{prefix}: horizons missing")
        support_steps = None
    else:
        support_steps = int(horizons.get("support_steps", -1))
        if support_steps < 2:
            errors.append(f"{prefix}: invalid support_steps={support_steps}")
        dt_s = float(horizons.get("dt_s", -1.0))
        if dt_s <= 0.0 or not np.isfinite(dt_s):
            errors.append(f"{prefix}: invalid dt_s={dt_s}")

    finite_checks = payload.get("finite_checks")
    if not isinstance(finite_checks, dict):
        errors.append(f"{prefix}: finite_checks missing")
    else:
        missing = sorted(set(PROGRESS_SUPPORT_FIELD_NAMES) - set(finite_checks))
        if missing:
            errors.append(f"{prefix}: finite_checks missing {missing}")
        for field in (
            *PROGRESS_SUPPORT_FIELD_NAMES,
            "progress_support_atoms",
            "progress_support_atoms_nonnegative",
        ):
            if finite_checks.get(field) is not True:
                errors.append(f"{prefix}: finite_checks failed {field}")

    shapes = payload.get("field_shapes")
    if not isinstance(shapes, dict):
        errors.append(f"{prefix}: field_shapes missing")
    elif support_steps is not None:
        expected_shapes = {
            "candidate_route_progress_s_profile_m": [
                int(expected_candidates),
                support_steps,
            ],
            "candidate_plan_arc_length_profile_m": [
                int(expected_candidates),
                support_steps,
            ],
            "candidate_speed_profile_mps": [
                int(expected_candidates),
                support_steps - 1,
            ],
            "candidate_route_remaining_m": [int(expected_candidates)],
            "candidate_goal_alignment_progress_m": [int(expected_candidates)],
        }
        for field, expected_shape in expected_shapes.items():
            if shapes.get(field) != expected_shape:
                errors.append(
                    f"{prefix}: field_shapes {field}={shapes.get(field)!r} "
                    f"expected={expected_shape!r}"
                )

    for field in PROGRESS_SUPPORT_FIELD_NAMES:
        if field not in payload:
            errors.append(f"{prefix}: payload missing {field}")
        elif not _finite_nested(payload[field]):
            errors.append(f"{prefix}: payload field {field} is not finite")

    if payload.get("progress_support_atom_names") != list(PROGRESS_SUPPORT_ATOM_NAMES):
        errors.append(f"{prefix}: progress_support_atom_names mismatch")
    atoms = np.asarray(payload.get("progress_support_atoms"), dtype=np.float64)
    if atoms.shape != (int(expected_candidates), len(PROGRESS_SUPPORT_ATOM_NAMES)):
        errors.append(f"{prefix}: progress_support_atoms shape={list(atoms.shape)}")
    elif not np.all(np.isfinite(atoms)):
        errors.append(f"{prefix}: progress_support_atoms not finite")
    elif not np.all(atoms >= -1e-12):
        errors.append(f"{prefix}: progress_support_atoms has negative values")

    latency = payload.get("latency_ms")
    if not isinstance(latency, dict):
        errors.append(f"{prefix}: payload latency_ms missing")
    else:
        for latency_key in LATENCY_FIELDS:
            value = float(latency.get(latency_key, -1.0))
            if value < 0.0 or not np.isfinite(value):
                errors.append(f"{prefix}: payload latency {latency_key}={value}")
            record_value = float(record.get(latency_key, -1.0))
            if abs(record_value - value) > 1e-9:
                errors.append(f"{prefix}: record/payload latency mismatch {latency_key}")


def _finite_nested(value: Any) -> bool:
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError):
        return False
    return bool(np.all(np.isfinite(array)))


def _path_seeds(path: Path) -> set[int]:
    return {
        int(match.group(1))
        for match in re.finditer(r"(?:^|[/\\])seed[_-]?(\d+)(?:[/\\]|$)", str(path))
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Progress-Support Logging Smoke Audit",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- paired logs: `{report['counts']['paired_logs']}`",
        f"- records: `{report['counts']['records']}`",
        "",
        "## Latency Maxima",
        "",
        "| Field | Max ms |",
        "| --- | ---: |",
    ]
    for key, value in report["latency_ms"].items():
        lines.append(f"| `{key}` | `{value:.6f}` |")
    lines.extend(["", "## Errors", ""])
    if report["errors"]:
        lines.extend(f"- `{error}`" for error in report["errors"])
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
