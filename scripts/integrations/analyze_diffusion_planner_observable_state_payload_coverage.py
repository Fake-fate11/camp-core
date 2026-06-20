#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import numpy as np


LOG_NAME = "camp_selection_log.json"
SCHEMA_VERSION = "dp_camp_observable_state_logging_v1"
EXPECTED_FIELDS = (
    "candidate_route_segment_index",
    "candidate_route_projection_s_m",
    "candidate_route_lateral_error_m",
    "candidate_red_stopline_distance_m",
    "candidate_red_heading_alignment",
    "candidate_route_heading_change_rad",
    "route_curvature_context_abs",
    "candidate_min_obstacle_clearance_lower_bound_m",
    "candidate_obstacle_slot_count",
)
CANDIDATE_FIELDS = (
    "candidate_route_segment_index",
    "candidate_route_projection_s_m",
    "candidate_route_lateral_error_m",
    "candidate_red_stopline_distance_m",
    "candidate_red_heading_alignment",
    "candidate_route_heading_change_rad",
    "candidate_min_obstacle_clearance_lower_bound_m",
    "candidate_obstacle_slot_count",
)
LATENCY_FIELDS = (
    "latency_ms_observable_state_route_topology",
    "latency_ms_observable_state_traffic_light_relation",
    "latency_ms_observable_state_route_turn",
    "latency_ms_observable_state_neighbor_clearance",
)
FORBIDDEN_SEEDS = frozenset({11, 12, 13})
EPS = 1e-9


READY_STATUS = "observable_state_payload_coverage_ready_for_offline_separability_design"
INSUFFICIENT_STATUS = "observable_state_payload_coverage_insufficient_for_materiality"
REJECT_STATUS = "observable_state_payload_coverage_rejected"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only coverage/materiality audit for default-off DP CAMP "
            "observable-state logging payloads. This never changes selection, "
            "runs replay, trains CAMP, or uses closed-loop outcome labels."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--min_records_for_materiality", type=int, default=12)
    parser.add_argument("--min_red_context_records", type=int, default=1)
    parser.add_argument("--min_material_candidate_fields", type=int, default=4)
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
        min_red_context_records=args.min_red_context_records,
        min_material_candidate_fields=args.min_material_candidate_fields,
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
    min_red_context_records: int = 1,
    min_material_candidate_fields: int = 4,
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
                    "payload": raw.get("observable_state_logging"),
                }
            )
    if formal_seed_records:
        errors.append(f"formal_seed_records={formal_seed_records}")

    payload_records = [
        record for record in records if isinstance(record["payload"], dict)
    ]
    missing_payload_records = len(records) - len(payload_records)
    if missing_payload_records:
        warnings.append(f"records_without_observable_payload={missing_payload_records}")

    for item in payload_records:
        _validate_payload_record(item, errors)

    field_coverage = {
        field: _field_coverage(payload_records, field)
        for field in EXPECTED_FIELDS
    }
    materiality = {
        field: _candidate_field_materiality(payload_records, field)
        for field in CANDIDATE_FIELDS
    }
    material_candidate_fields = [
        field
        for field, report in materiality.items()
        if int(report["records_with_candidate_variation"]) > 0
    ]
    latency = _latency_report(payload_records)
    context = _context_report(payload_records)
    decision = _decision(
        records_total=len(records),
        payload_records=len(payload_records),
        errors=errors,
        material_candidate_fields=material_candidate_fields,
        context=context,
        min_records_for_materiality=min_records_for_materiality,
        min_red_context_records=min_red_context_records,
        min_material_candidate_fields=min_material_candidate_fields,
    )
    return {
        "analysis": {
            "name": "dp_camp_observable_state_payload_coverage_v1",
            "label": label,
            "schema_version": SCHEMA_VERSION,
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
                "red_context_records": f">= {int(min_red_context_records)}",
                "material_candidate_fields": (
                    f">= {int(min_material_candidate_fields)}"
                ),
            },
            "math_boundary": (
                "This is a read-only audit over already logged current-tick "
                "finite-candidate descriptors. It does not use closed-loop "
                "outcome labels, run replay, alter DP candidates, change CAMP "
                "weights, or change selection. If any descriptor is later "
                "atomized, it must enter as a fixed candidate coefficient a_k "
                "so score_k(w)=a_k^T w remains affine and the simplex/CVaR/L2 "
                "master remains convex. No DP-side classical Benders "
                "decomposition, dual, or cut is claimed."
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
        "candidate_field_materiality": materiality,
        "material_candidate_fields": material_candidate_fields,
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
        "schema_version": SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
    }
    for field, expected in expected_flags.items():
        if payload.get(field) != expected:
            errors.append(f"{prefix}: payload {field}={payload.get(field)!r}")
    if "candidate_closed_loop_outcomes" in payload:
        errors.append(f"{prefix}: payload contains candidate_closed_loop_outcomes")
    if record.get("candidate_closed_loop_outcomes") is not None:
        errors.append(f"{prefix}: record contains closed-loop outcome labels")
    candidate_count = _payload_candidate_count(payload)
    if candidate_count <= 0:
        errors.append(f"{prefix}: invalid candidate_count={candidate_count}")
    finite_checks = payload.get("finite_checks")
    if not isinstance(finite_checks, dict):
        errors.append(f"{prefix}: missing finite_checks")
    else:
        missing = sorted(set(EXPECTED_FIELDS) - set(finite_checks))
        if missing:
            errors.append(f"{prefix}: finite_checks missing {missing}")
        failed = sorted(field for field, value in finite_checks.items() if not value)
        if failed:
            errors.append(f"{prefix}: finite_checks failed {failed}")
    shapes = payload.get("field_shapes")
    if not isinstance(shapes, dict):
        errors.append(f"{prefix}: missing field_shapes")
    else:
        missing = sorted(set(EXPECTED_FIELDS) - set(shapes))
        if missing:
            errors.append(f"{prefix}: field_shapes missing {missing}")
    latency = payload.get("latency_ms")
    if not isinstance(latency, dict):
        errors.append(f"{prefix}: missing latency_ms")
    else:
        for field in LATENCY_FIELDS:
            value = _as_float(latency.get(field))
            if value is None or value < 0.0:
                errors.append(f"{prefix}: invalid latency {field}={latency.get(field)!r}")
            record_value = _as_float(record.get(field))
            if record_value is not None and value is not None:
                if abs(record_value - value) > 1e-9:
                    errors.append(f"{prefix}: record/payload latency mismatch {field}")
    if int(payload.get("red_route_point_count", 0)) == 0:
        for field in (
            "candidate_red_stopline_distance_m",
            "candidate_red_heading_alignment",
        ):
            if payload.get(field) is not None:
                errors.append(f"{prefix}: empty-red field {field} must be null")
    for field in EXPECTED_FIELDS:
        if field not in payload:
            errors.append(f"{prefix}: payload missing {field}")


def _field_coverage(items: list[dict[str, Any]], field: str) -> dict[str, Any]:
    records_present = 0
    nonempty_records = 0
    finite_values = 0
    total_values = 0
    for item in items:
        payload = item["payload"]
        if field not in payload or payload[field] is None:
            continue
        records_present += 1
        values = _flatten_numbers(payload[field])
        if values.size:
            nonempty_records += 1
            finite_values += int(np.sum(np.isfinite(values)))
            total_values += int(values.size)
    denom = max(len(items), 1)
    return {
        "records_present": records_present,
        "record_coverage_rate": records_present / denom,
        "nonempty_records": nonempty_records,
        "finite_values": finite_values,
        "total_values": total_values,
        "finite_value_rate": finite_values / max(total_values, 1),
    }


def _candidate_field_materiality(
    items: list[dict[str, Any]],
    field: str,
) -> dict[str, Any]:
    candidate_ranges: list[float] = []
    varied_records = 0
    available_records = 0
    for item in items:
        values = _candidate_scalar_values(item["payload"], field)
        if values is None or values.size < 2:
            continue
        available_records += 1
        finite = values[np.isfinite(values)]
        if finite.size < 2:
            continue
        value_range = float(np.max(finite) - np.min(finite))
        candidate_ranges.append(value_range)
        if value_range > EPS:
            varied_records += 1
    ranges = np.asarray(candidate_ranges, dtype=np.float64)
    return {
        "available_records": available_records,
        "records_with_candidate_variation": varied_records,
        "variation_record_rate": varied_records / max(len(items), 1),
        "max_candidate_range": _finite_max(ranges),
        "mean_candidate_range": _finite_mean(ranges),
        "materiality_rule": "cross_candidate_range_gt_1e-9",
    }


def _candidate_scalar_values(payload: dict[str, Any], field: str) -> np.ndarray | None:
    raw = payload.get(field)
    if raw is None:
        return None
    candidate_count = _payload_candidate_count(payload)
    arr = _numeric_array(raw)
    if arr is None or arr.size == 0:
        return None
    if arr.ndim == 0:
        return None
    if arr.shape[0] != candidate_count:
        return None
    if arr.ndim == 1:
        return arr.astype(np.float64)
    flat = arr.reshape(candidate_count, -1)
    with np.errstate(invalid="ignore"):
        return np.nanmean(flat, axis=1)


def _context_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    red_context_records = 0
    route_curvature_nonempty_records = 0
    obstacle_context_records = 0
    route_segment_counts: list[int] = []
    red_route_point_counts: list[int] = []
    candidate_counts: list[int] = []
    for item in items:
        payload = item["payload"]
        red_count = int(payload.get("red_route_point_count", 0))
        route_count = int(payload.get("route_segment_count", 0))
        candidate_counts.append(_payload_candidate_count(payload))
        red_route_point_counts.append(red_count)
        route_segment_counts.append(route_count)
        red_context_records += int(red_count > 0)
        curvature = _flatten_numbers(payload.get("route_curvature_context_abs"))
        route_curvature_nonempty_records += int(curvature.size > 0)
        slots = _flatten_numbers(payload.get("candidate_obstacle_slot_count"))
        obstacle_context_records += int(slots.size > 0 and np.nanmax(slots) > 0)
    return {
        "red_context_records": red_context_records,
        "red_context_record_rate": red_context_records / max(len(items), 1),
        "route_curvature_nonempty_records": route_curvature_nonempty_records,
        "obstacle_context_records": obstacle_context_records,
        "candidate_count_values": sorted(set(candidate_counts)),
        "route_segment_count_values": sorted(set(route_segment_counts)),
        "red_route_point_count_values": sorted(set(red_route_point_counts)),
    }


def _latency_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for field in LATENCY_FIELDS:
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
    material_candidate_fields: list[str],
    context: dict[str, Any],
    min_records_for_materiality: int,
    min_red_context_records: int,
    min_material_candidate_fields: int,
) -> dict[str, Any]:
    if errors:
        status = REJECT_STATUS
        primary_gap = "schema_or_no_leak_validation_failed"
        authorized_next_work = None
    elif payload_records < min_records_for_materiality:
        status = INSUFFICIENT_STATUS
        primary_gap = "too_few_logged_records_for_materiality"
        authorized_next_work = "default_off_observable_state_logging_broader_nonformal_plan_only"
    elif context["red_context_records"] < min_red_context_records:
        status = INSUFFICIENT_STATUS
        primary_gap = "missing_red_light_context_coverage"
        authorized_next_work = "default_off_observable_state_logging_broader_nonformal_plan_only"
    elif len(material_candidate_fields) < min_material_candidate_fields:
        status = INSUFFICIENT_STATUS
        primary_gap = "insufficient_cross_candidate_descriptor_variation"
        authorized_next_work = "default_off_observable_state_logging_broader_nonformal_plan_only"
    else:
        status = READY_STATUS
        primary_gap = "observable_payload_has_minimum_coverage_and_materiality"
        authorized_next_work = "offline_no_leak_observable_descriptor_separability_design_only"
    return {
        "status": status,
        "validation_passed": not errors,
        "materiality_gate_passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "records_total": records_total,
        "payload_records": payload_records,
        "material_candidate_fields": material_candidate_fields,
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
        "# Observable State Payload Coverage Audit",
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
        f"| `red_context_records` | `{context['red_context_records']}` |",
        f"| `route_curvature_nonempty_records` | `{context['route_curvature_nonempty_records']}` |",
        f"| `obstacle_context_records` | `{context['obstacle_context_records']}` |",
        "",
        "## Candidate Field Materiality",
        "",
        "| Field | Varied Records | Variation Rate | Max Range | Mean Range |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
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
