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

from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (  # noqa: E402
    PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS,
    PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
)


LOG_NAME = "camp_selection_log.json"
PAYLOAD_KEY = "progress_lane_hard_context_logging"
ATOMS_KEY = "progress_lane_hard_context_atoms"
ATOM_NAMES_KEY = "progress_lane_hard_context_atom_names"
FORBIDDEN_SEEDS = frozenset({11, 12, 13})
EPS = 1e-9

CANDIDATE_FIELDS = (
    "candidate_lateral_error_rate_profile_mps",
    "candidate_speed_profile_mps",
    "candidate_route_progress_delta_profile_m",
    "candidate_route_corridor_margin_profile_m",
    "candidate_route_heading_error_profile_rad",
)

READY_STATUS = (
    "progress_lane_hard_context_payload_coverage_ready_for_offline_separability_design"
)
INSUFFICIENT_STATUS = (
    "progress_lane_hard_context_payload_coverage_insufficient_for_materiality"
)
REJECT_STATUS = "progress_lane_hard_context_payload_coverage_rejected"

BROADER_PLAN_NEXT_WORK = "progress_lane_hard_context_broader_nonformal_plan_only"
SEPARABILITY_NEXT_WORK = (
    "offline_no_leak_progress_lane_hard_context_descriptor_separability_design_only"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only coverage/materiality audit for default-off DP CAMP "
            "progress+lane/hard context logging payloads. This consumes "
            "already logged current-tick finite-candidate descriptors only."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--min_records_for_materiality", type=int, default=12)
    parser.add_argument("--min_context_records", type=int, default=1)
    parser.add_argument("--min_material_atom_fields", type=int, default=2)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--require_valid",
        action="store_true",
        help="Exit with status 2 if schema/no-leak validation fails.",
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
        min_records_for_materiality=args.min_records_for_materiality,
        min_context_records=args.min_context_records,
        min_material_atom_fields=args.min_material_atom_fields,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")
    if args.require_valid and report["validation"]["errors"]:
        raise SystemExit(2)


def analyze(
    paths: list[Path],
    *,
    label: str | None = None,
    min_records_for_materiality: int = 12,
    min_context_records: int = 1,
    min_material_atom_fields: int = 2,
) -> dict[str, Any]:
    log_paths = _discover_logs(paths)
    if not log_paths:
        raise ValueError("No camp_selection_log.json files were found.")

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    formal_seed_records = 0
    for log_path in log_paths:
        formal_seed_records += int(bool(_path_seeds(log_path) & FORBIDDEN_SEEDS))
        payload = _read_json(log_path)
        if not isinstance(payload, list):
            errors.append(f"{log_path}: selection log must contain a JSON list")
            continue
        for record_index, raw in enumerate(payload):
            if not isinstance(raw, dict):
                errors.append(f"{log_path} record {record_index}: row is not an object")
                continue
            if _record_seed(raw) in FORBIDDEN_SEEDS:
                formal_seed_records += 1
            records.append(
                {
                    "log_path": str(log_path),
                    "record_index": record_index,
                    "record": raw,
                    "payload": raw.get(PAYLOAD_KEY),
                }
            )
    if formal_seed_records:
        errors.append(f"formal_seed_records={formal_seed_records}")

    payload_records = [
        record for record in records if isinstance(record["payload"], dict)
    ]
    missing_payload_records = len(records) - len(payload_records)
    if missing_payload_records:
        warnings.append(
            f"records_without_progress_lane_hard_context_payload={missing_payload_records}"
        )

    for item in payload_records:
        _validate_payload_record(item, errors)

    field_coverage = {
        field: _field_coverage(payload_records, field)
        for field in PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES
    }
    candidate_field_materiality = {
        field: _candidate_field_materiality(payload_records, field)
        for field in CANDIDATE_FIELDS
    }
    atom_materiality = {
        atom: _atom_materiality(payload_records, atom)
        for atom in PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES
    }
    material_atom_fields = [
        atom
        for atom, report in atom_materiality.items()
        if int(report["records_with_candidate_variation"]) > 0
    ]
    context = _context_report(payload_records)
    latency = _latency_report(payload_records)
    decision = _decision(
        records_total=len(records),
        payload_records=len(payload_records),
        errors=errors,
        material_atom_fields=material_atom_fields,
        context=context,
        min_records_for_materiality=min_records_for_materiality,
        min_context_records=min_context_records,
        min_material_atom_fields=min_material_atom_fields,
    )
    return {
        "analysis": {
            "name": "dp_camp_progress_lane_hard_context_payload_coverage_v1",
            "label": label,
            "schema_version": PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
            "training": False,
            "closed_loop_replay": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_labels_allowed": False,
            "formal_seeds_forbidden": sorted(FORBIDDEN_SEEDS),
            "accept_criteria": {
                "records": f">= {int(min_records_for_materiality)}",
                "context_records": f">= {int(min_context_records)}",
                "material_atom_fields": f">= {int(min_material_atom_fields)}",
            },
            "math_boundary": (
                "This is a read-only audit over already logged current-tick "
                "finite-candidate progress+lane/hard context descriptors. It "
                "does not use closed-loop outcome labels, run replay, alter DP "
                "candidates, change CAMP weights, or change selection. If any "
                "descriptor is later atomized, it must enter as a fixed "
                "candidate coefficient a_k so score_k(w)=a_k^T w remains "
                "affine and the simplex/CVaR/L2 master remains convex. No "
                "DP-side classical Benders decomposition, dual, or cut is "
                "claimed."
            ),
        },
        "inputs": {
            "paths": [str(path) for path in paths],
            "selection_logs": [str(path) for path in log_paths],
        },
        "counts": {
            "logs": len(log_paths),
            "records": len(records),
            "payload_records": len(payload_records),
            "records_without_payload": missing_payload_records,
            "candidate_rows": int(
                sum(_payload_candidate_count(item["payload"]) for item in payload_records)
            ),
        },
        "context": context,
        "field_coverage": field_coverage,
        "candidate_field_materiality": candidate_field_materiality,
        "atom_materiality": atom_materiality,
        "material_atom_fields": material_atom_fields,
        "latency_ms": latency,
        "validation": {
            "errors": errors,
            "warnings": warnings,
        },
        "final_decision": decision,
    }


def _discover_logs(paths: list[Path]) -> list[Path]:
    logs: list[Path] = []
    for path in paths:
        if path.is_file():
            logs.append(path)
        elif path.is_dir():
            logs.extend(sorted(path.rglob(LOG_NAME)))
    return sorted(dict.fromkeys(logs))


def _validate_payload_record(item: dict[str, Any], errors: list[str]) -> None:
    payload = item["payload"]
    record = item["record"]
    prefix = f"{item['log_path']} record {item['record_index']}"
    expected_flags = {
        "schema_version": PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
    }
    for field, expected in expected_flags.items():
        if payload.get(field) != expected:
            errors.append(f"{prefix}: payload {field}={payload.get(field)!r}")
    if "candidate_closed_loop_outcomes" in payload:
        errors.append(f"{prefix}: payload contains candidate_closed_loop_outcomes")
    if record.get("candidate_closed_loop_outcomes") is not None:
        errors.append(f"{prefix}: record contains closed-loop outcome labels")
    if payload.get(ATOM_NAMES_KEY) != list(PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES):
        errors.append(f"{prefix}: unexpected atom names")
    candidate_count = _payload_candidate_count(payload)
    if candidate_count <= 0:
        errors.append(f"{prefix}: invalid candidate_count={candidate_count}")
    for field in PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES:
        if field not in payload:
            errors.append(f"{prefix}: missing field {field}")
    finite_checks = payload.get("finite_checks")
    if not isinstance(finite_checks, dict):
        errors.append(f"{prefix}: missing finite_checks")
    else:
        failed = [key for key, value in finite_checks.items() if value is not True]
        if failed:
            errors.append(f"{prefix}: finite_checks failed {sorted(failed)}")
    atoms = _numeric_array(payload.get(ATOMS_KEY))
    if atoms is None:
        errors.append(f"{prefix}: atoms are not numeric")
    elif atoms.shape != (candidate_count, len(PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES)):
        errors.append(f"{prefix}: atom_shape={list(atoms.shape)}")
    elif np.any(atoms < -1e-12):
        errors.append(f"{prefix}: atoms contain negative entries")
    for latency_key in PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS:
        latency = _as_float(payload.get("latency_ms", {}).get(latency_key))
        record_latency = _as_float(record.get(latency_key))
        if latency is None or latency < 0.0:
            errors.append(f"{prefix}: invalid payload latency {latency_key}")
        if record_latency is None or record_latency < 0.0:
            errors.append(f"{prefix}: invalid record latency {latency_key}")


def _field_coverage(items: list[dict[str, Any]], field: str) -> dict[str, Any]:
    present = 0
    finite = 0
    nonempty = 0
    for item in items:
        payload = item["payload"]
        if field in payload:
            present += 1
        arr = _numeric_array(payload.get(field))
        if arr is not None and arr.size > 0:
            nonempty += 1
            finite += int(bool(np.all(np.isfinite(arr))))
    total = len(items)
    return {
        "present_records": present,
        "finite_records": finite,
        "nonempty_records": nonempty,
        "present_rate": present / max(total, 1),
        "finite_rate": finite / max(total, 1),
    }


def _candidate_field_materiality(
    items: list[dict[str, Any]], field: str
) -> dict[str, Any]:
    ranges: list[float] = []
    varied = 0
    for item in items:
        payload = item["payload"]
        candidate_count = _payload_candidate_count(payload)
        values = _candidate_scalar_values(payload.get(field), candidate_count)
        if values is None or values.size == 0:
            continue
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            continue
        spread = float(np.nanmax(finite) - np.nanmin(finite))
        ranges.append(spread)
        varied += int(spread > EPS)
    return _materiality_report(varied, ranges, len(items))


def _atom_materiality(items: list[dict[str, Any]], atom: str) -> dict[str, Any]:
    ranges: list[float] = []
    varied = 0
    atom_names = list(PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES)
    if atom not in atom_names:
        return _materiality_report(0, ranges, len(items))
    atom_index = atom_names.index(atom)
    for item in items:
        atoms = _numeric_array(item["payload"].get(ATOMS_KEY))
        if atoms is None or atoms.ndim != 2 or atoms.shape[1] <= atom_index:
            continue
        values = atoms[:, atom_index]
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            continue
        spread = float(np.nanmax(finite) - np.nanmin(finite))
        ranges.append(spread)
        varied += int(spread > EPS)
    return _materiality_report(varied, ranges, len(items))


def _materiality_report(
    varied: int, ranges: list[float], record_count: int
) -> dict[str, Any]:
    finite = np.asarray(ranges, dtype=np.float64)
    return {
        "records_with_candidate_variation": int(varied),
        "variation_record_rate": varied / max(record_count, 1),
        "max_candidate_range": _finite_max(finite),
        "mean_candidate_range": _finite_mean(finite),
    }


def _candidate_scalar_values(raw: Any, candidate_count: int) -> np.ndarray | None:
    arr = _numeric_array(raw)
    if arr is None or candidate_count <= 0:
        return None
    if arr.ndim == 0:
        return None
    if arr.shape[0] != candidate_count:
        return None
    flat = arr.reshape(candidate_count, -1)
    with np.errstate(invalid="ignore"):
        return np.nanmean(flat, axis=1)


def _context_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    curvature_context_records = 0
    corridor_pressure_records = 0
    positive_atom_records = 0
    candidate_counts: list[int] = []
    support_steps: list[int] = []
    for item in items:
        payload = item["payload"]
        candidate_counts.append(_payload_candidate_count(payload))
        try:
            support_steps.append(int(payload.get("horizons", {}).get("support_steps", 0)))
        except (TypeError, ValueError):
            support_steps.append(0)
        curvature = _flatten_numbers(payload.get("route_curvature_context_abs_radpm"))
        curvature_context_records += int(curvature.size > 0 and np.nanmax(curvature) > EPS)
        margin = _flatten_numbers(payload.get("candidate_route_corridor_margin_profile_m"))
        safety_margin = _as_float(payload.get("budgets", {}).get("corridor_safety_margin_m"))
        if safety_margin is not None and margin.size > 0:
            corridor_pressure_records += int(np.nanmin(margin) <= safety_margin + EPS)
        atoms = _numeric_array(payload.get(ATOMS_KEY))
        if atoms is not None and atoms.size > 0:
            positive_atom_records += int(np.nanmax(atoms) > EPS)
    context_records = max(
        curvature_context_records,
        corridor_pressure_records,
        positive_atom_records,
    )
    return {
        "context_records": context_records,
        "curvature_context_records": curvature_context_records,
        "corridor_pressure_records": corridor_pressure_records,
        "positive_atom_records": positive_atom_records,
        "candidate_count_values": sorted(set(candidate_counts)),
        "support_step_values": sorted(set(support_steps)),
    }


def _latency_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for field in PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS:
        values = np.asarray(
            [
                _as_float(item["payload"].get("latency_ms", {}).get(field))
                for item in items
            ],
            dtype=np.float64,
        )
        finite = values[np.isfinite(values)]
        report[field] = {
            "max_ms": _finite_max(finite),
            "mean_ms": _finite_mean(finite),
            "records": int(finite.size),
        }
    return report


def _decision(
    *,
    records_total: int,
    payload_records: int,
    errors: list[str],
    material_atom_fields: list[str],
    context: dict[str, Any],
    min_records_for_materiality: int,
    min_context_records: int,
    min_material_atom_fields: int,
) -> dict[str, Any]:
    if errors:
        status = REJECT_STATUS
        primary_gap = "schema_or_no_leak_validation_failed"
        authorized_next_work = None
    elif payload_records < min_records_for_materiality:
        status = INSUFFICIENT_STATUS
        primary_gap = "too_few_logged_records_for_materiality"
        authorized_next_work = BROADER_PLAN_NEXT_WORK
    elif int(context["context_records"]) < min_context_records:
        status = INSUFFICIENT_STATUS
        primary_gap = "missing_curvature_or_corridor_context_coverage"
        authorized_next_work = BROADER_PLAN_NEXT_WORK
    elif len(material_atom_fields) < min_material_atom_fields:
        status = INSUFFICIENT_STATUS
        primary_gap = "insufficient_cross_candidate_context_atom_variation"
        authorized_next_work = BROADER_PLAN_NEXT_WORK
    else:
        status = READY_STATUS
        primary_gap = "progress_lane_hard_context_payload_has_minimum_materiality"
        authorized_next_work = SEPARABILITY_NEXT_WORK
    return {
        "status": status,
        "validation_passed": not errors,
        "materiality_gate_passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "records_total": records_total,
        "payload_records": payload_records,
        "material_atom_fields": material_atom_fields,
        "authorized_next_work": authorized_next_work,
        "closed_loop_replay_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
    }


def _payload_candidate_count(payload: dict[str, Any]) -> int:
    try:
        return int(payload.get("candidate_count", 0))
    except (TypeError, ValueError):
        return 0


def _record_seed(record: dict[str, Any]) -> int | None:
    for key in ("seed", "scenario_seed"):
        if key in record:
            try:
                return int(record[key])
            except (TypeError, ValueError):
                return None
    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        for key in ("seed", "scenario_seed"):
            if key in metadata:
                try:
                    return int(metadata[key])
                except (TypeError, ValueError):
                    return None
    return None


def _path_seeds(path: Path) -> set[int]:
    return {
        int(match.group(1))
        for match in re.finditer(r"(?:^|[/\\])seed[_-]?(\d+)(?:[/\\]|$)", str(path))
    }


def _numeric_array(raw: Any) -> np.ndarray | None:
    try:
        return np.asarray(_replace_none(raw), dtype=np.float64)
    except (TypeError, ValueError):
        return None


def _replace_none(raw: Any) -> Any:
    if raw is None:
        return np.nan
    if isinstance(raw, list):
        return [_replace_none(value) for value in raw]
    return raw


def _flatten_numbers(raw: Any) -> np.ndarray:
    arr = _numeric_array(raw)
    if arr is None:
        return np.zeros(0, dtype=np.float64)
    return arr.reshape(-1)


def _as_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(result):
        return None
    return result


def _finite_max(values: np.ndarray) -> float | None:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return None
    return float(np.max(finite))


def _finite_mean(values: np.ndarray) -> float | None:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return None
    return float(np.mean(finite))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    counts = report["counts"]
    context = report["context"]
    lines = [
        "# Progress+Lane/Hard Context Payload Coverage Audit",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Primary gap: `{decision['primary_gap']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Logs: `{counts['logs']}`",
        f"- Records: `{counts['records']}`",
        f"- Payload records: `{counts['payload_records']}`",
        f"- Candidate rows: `{counts['candidate_rows']}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Context Coverage",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| `context_records` | `{context['context_records']}` |",
        f"| `curvature_context_records` | `{context['curvature_context_records']}` |",
        f"| `corridor_pressure_records` | `{context['corridor_pressure_records']}` |",
        f"| `positive_atom_records` | `{context['positive_atom_records']}` |",
        "",
        "## Atom Materiality",
        "",
        "| Atom | Varied Records | Variation Rate | Max Range | Mean Range |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for atom, row in report["atom_materiality"].items():
        lines.append(
            f"| `{atom}` | `{row['records_with_candidate_variation']}` | "
            f"{_fmt(row['variation_record_rate'])} | "
            f"{_fmt(row['max_candidate_range'])} | "
            f"{_fmt(row['mean_candidate_range'])} |"
        )
    lines.extend(
        [
            "",
            "## Candidate Field Materiality",
            "",
            "| Field | Varied Records | Variation Rate | Max Range | Mean Range |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for field, row in report["candidate_field_materiality"].items():
        lines.append(
            f"| `{field}` | `{row['records_with_candidate_variation']}` | "
            f"{_fmt(row['variation_record_rate'])} | "
            f"{_fmt(row['max_candidate_range'])} | "
            f"{_fmt(row['mean_candidate_range'])} |"
        )
    lines.extend(["", "## Validation", ""])
    errors = report["validation"]["errors"]
    if errors:
        lines.extend(f"- error: `{error}`" for error in errors)
    else:
        lines.append("- errors: none")
    warnings = report["validation"]["warnings"]
    for warning in warnings:
        lines.append(f"- warning: `{warning}`")
    lines.extend(
        [
            "",
            "This audit does not authorize replay, Full36, formal seeds, online "
            "selector promotion, CAMP retraining, or DP modification.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "`n/a`"
    try:
        result = float(value)
    except (TypeError, ValueError):
        return "`n/a`"
    if not np.isfinite(result):
        return "`n/a`"
    return f"`{result:.6g}`"


if __name__ == "__main__":
    main()
