#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
    parse_selection_log_metadata,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SUPPORTED_SCENARIO_BUCKETS,
    _load_scenario_bucket_manifest,
    _run_key,
    _scenario_buckets,
)


FORMAL_SEEDS = {11, 12, 13}
LATERAL_ACCELERATION_LIMIT_MPS2 = 2.0

ATOM_FAMILIES = (
    "hard_feasibility_deficit",
    "support_preservation_deficit",
    "comfort_envelope_excess",
    "top1_shape_deviation",
    "traffic_rule_exposure",
)

DEFAULT_REQUIRED_BUCKETS = (
    "normal",
    "traffic_light",
    "red_light_turn",
    "sharp_turn",
    "dense_scene",
    "lane_change_or_merge",
)

BLOCKED_ACTIONS = (
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only availability audit for the next DP-CAMP material atom "
            "schema. It checks fixed current-tick finite-candidate atom "
            "coverage and mathematical compatibility before any training or "
            "replay is authorized."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument(
        "--required_bucket",
        action="append",
        choices=sorted(SUPPORTED_SCENARIO_BUCKETS - {"overall"}),
        default=[],
        help=(
            "Scenario bucket required by the gate. If omitted, the default "
            "material atom gate buckets are used."
        ),
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(
        paths,
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        required_buckets=tuple(args.required_bucket) or DEFAULT_REQUIRED_BUCKETS,
        label=args.label,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
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


def analyze(
    paths: list[Path],
    *,
    scenario_bucket_manifest: Path | None = None,
    required_buckets: tuple[str, ...] = DEFAULT_REQUIRED_BUCKETS,
    label: str | None = None,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)
    items: list[dict[str, Any]] = []
    for log_path in log_paths:
        context = _log_context(log_path, manifest)
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for index, raw in enumerate(payload):
            if not isinstance(raw, dict):
                raise ValueError(f"{log_path} record {index} must be an object.")
            items.append(
                {
                    "raw": raw,
                    "context": {
                        **context,
                        "record_index": index,
                    },
                }
            )
    return analyze_records(
        items,
        required_buckets=required_buckets,
        label=label,
        scenario_bucket_manifest=(
            None if scenario_bucket_manifest is None else str(scenario_bucket_manifest)
        ),
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    required_buckets: tuple[str, ...] = DEFAULT_REQUIRED_BUCKETS,
    label: str | None = None,
    scenario_bucket_manifest: str | None = None,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")
    _validate_required_buckets(required_buckets)
    records = [
        _record_analysis(item["raw"], item["context"], f"record {index}")
        for index, item in enumerate(items)
    ]
    formal_seed_records = sum(int(record["context"]["formal_seed"]) for record in records)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")
    field_coverage = _field_coverage(records)
    atom_summary = _atom_summary(records)
    bucket_counts = _scenario_bucket_counts(records)
    convexity_checks = _convexity_checks(
        records,
        field_coverage,
        atom_summary,
        bucket_counts,
        required_buckets=required_buckets,
    )
    decision = _decision(
        field_coverage,
        convexity_checks,
        bucket_counts,
        formal_seed_records=formal_seed_records,
        required_buckets=required_buckets,
    )
    return {
        "analysis": {
            "name": "dp_camp_material_atom_schema_availability_v1",
            "label": label,
            "role": (
                "read-only no-leak availability audit for fixed current-tick "
                "finite-candidate material CAMP atoms"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used_for_atoms": False,
            "scenario_bucket_manifest": scenario_bucket_manifest,
            "required_buckets": list(required_buckets),
            "formal_seed_policy": (
                "forbidden" if fail_on_formal_seeds else "reported_only"
            ),
            "atom_definitions": _atom_definitions(),
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. Every "
                "reported material atom is computed from fixed current-tick "
                "finite-candidate quantities before any optimization over "
                "weights. Candidate closed-loop outcomes are not used to build "
                "atoms. For candidate k, score_k(w)=a_k^T w remains affine in "
                "w; simplex constraints, CVaR terms, and L2 regularization in "
                "the CAMP master remain convex over fixed atoms. This audit "
                "does not construct a DP-side master/subproblem, dual, or cut, "
                "so it does not claim classical Benders decomposition."
            ),
        },
        "records": {
            "logs": len({record["context"].get("log_path") for record in records}),
            "total": len(records),
            "candidate_rows": int(sum(record["candidate_count"] for record in records)),
            "candidate_count_values": sorted(
                {int(record["candidate_count"]) for record in records}
            ),
            "formal_seed_records": int(formal_seed_records),
            "outcome_labels_present_records": int(
                sum(record["outcome_labels_present"] for record in records)
            ),
            "scenario_bucket_counts": bucket_counts,
        },
        "field_coverage": field_coverage,
        "atom_summary": atom_summary,
        "convexity_checks": convexity_checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _record_analysis(
    raw: dict[str, Any],
    context: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    candidate_count = int(raw.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected = int(raw.get("selected_index"))
    if selected < 0 or selected >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    families = {
        "hard_feasibility_deficit": _hard_feasibility(raw, candidate_count, label),
        "support_preservation_deficit": _support_preservation(
            raw,
            candidate_count,
            selected,
            label,
        ),
        "comfort_envelope_excess": _comfort_envelope(
            raw,
            candidate_count,
            selected,
            label,
        ),
        "top1_shape_deviation": _top1_shape_deviation(raw, candidate_count, label),
        "traffic_rule_exposure": _traffic_rule_exposure(raw, candidate_count, label),
    }
    return {
        "context": _normalized_context(context),
        "candidate_count": candidate_count,
        "selected_index": selected,
        "outcome_labels_present": isinstance(
            raw.get("candidate_closed_loop_outcomes"),
            list,
        ),
        "families": families,
    }


def _hard_feasibility(
    raw: dict[str, Any],
    candidate_count: int,
    label: str,
) -> dict[str, Any]:
    if "feasible_mask" not in raw:
        return _missing_family(["feasible_mask"])
    feasible = _bool_vector(raw["feasible_mask"], candidate_count, f"{label} feasible_mask")
    return _family(
        1.0 - feasible.astype(np.float64),
        components=["feasible_mask"],
        source_fields=["feasible_mask"],
    )


def _support_preservation(
    raw: dict[str, Any],
    candidate_count: int,
    selected: int,
    label: str,
) -> dict[str, Any]:
    components: list[np.ndarray] = []
    component_names: list[str] = []
    source_fields: list[str] = []

    progress = _first_vector(
        raw,
        candidate_count,
        label,
        ("candidate_route_progress", "candidate_step_reach"),
        nonnegative=False,
    )
    if progress is not None:
        key, values = progress
        components.append(np.maximum(float(values[selected]) - values, 0.0))
        component_names.append(f"selected_{key}_deficit")
        source_fields.append(key)

    target_speed = _first_vector(
        raw,
        candidate_count,
        label,
        ("candidate_perfect_tracker_target_speed_mps",),
        nonnegative=True,
    )
    if target_speed is not None:
        key, values = target_speed
        components.append(np.maximum(float(values[selected]) - values, 0.0))
        component_names.append(f"selected_{key}_deficit")
        source_fields.append(key)

    if not components:
        return _missing_family(
            [
                "candidate_route_progress",
                "candidate_step_reach",
                "candidate_perfect_tracker_target_speed_mps",
            ]
        )
    return _family(
        _component_max(components),
        components=component_names,
        source_fields=source_fields,
    )


def _comfort_envelope(
    raw: dict[str, Any],
    candidate_count: int,
    selected: int,
    label: str,
) -> dict[str, Any]:
    components: list[np.ndarray] = []
    component_names: list[str] = []
    source_fields: list[str] = []

    for keys, prefix in (
        (
            (
                "candidate_perfect_tracker_jerk_magnitude_mps3",
                "candidate_dp_prior_jerk_excess_cost",
            ),
            "selected_jerk",
        ),
        (
            (
                "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
                "candidate_horizon_lateral_acceleration_cost",
                "candidate_dp_prior_lateral_acceleration_excess_cost",
            ),
            "selected_lateral",
        ),
    ):
        match = _first_vector(raw, candidate_count, label, keys, nonnegative=True)
        if match is None:
            continue
        key, values = match
        components.append(np.maximum(values - float(values[selected]), 0.0))
        component_names.append(f"{prefix}_excess")
        source_fields.append(key)

    lateral = _first_vector(
        raw,
        candidate_count,
        label,
        ("candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",),
        nonnegative=True,
    )
    if lateral is not None:
        key, values = lateral
        components.append(np.maximum(values - LATERAL_ACCELERATION_LIMIT_MPS2, 0.0))
        component_names.append("absolute_lateral_acceleration_limit_excess")
        source_fields.append(key)

    if not components:
        return _missing_family(
            [
                "candidate_perfect_tracker_jerk_magnitude_mps3",
                "candidate_dp_prior_jerk_excess_cost",
                "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
                "candidate_horizon_lateral_acceleration_cost",
                "candidate_dp_prior_lateral_acceleration_excess_cost",
            ]
        )
    return _family(
        _component_max(components),
        components=component_names,
        source_fields=source_fields,
    )


def _top1_shape_deviation(
    raw: dict[str, Any],
    candidate_count: int,
    label: str,
) -> dict[str, Any]:
    dp_prior = _first_vector(
        raw,
        candidate_count,
        label,
        ("candidate_dp_prior_deviation_cost",),
        nonnegative=True,
    )
    if dp_prior is not None:
        key, values = dp_prior
        return _family(
            values,
            components=[key],
            source_fields=[key],
        )

    prefix = raw.get("candidate_perfect_tracker_postprocessed_reference_prefix")
    if prefix is not None:
        values = _prefix_shape_deviation(prefix, candidate_count, label)
        return _family(
            values,
            components=["top1_prefix_l2_deviation"],
            source_fields=["candidate_perfect_tracker_postprocessed_reference_prefix"],
        )

    return _missing_family(
        [
            "candidate_dp_prior_deviation_cost",
            "candidate_perfect_tracker_postprocessed_reference_prefix",
        ]
    )


def _traffic_rule_exposure(
    raw: dict[str, Any],
    candidate_count: int,
    label: str,
) -> dict[str, Any]:
    components: list[np.ndarray] = []
    component_names: list[str] = []
    source_fields: list[str] = []
    for key in (
        "candidate_horizon_union_planned_red_light_cost",
        "candidate_full_horizon_planned_red_light_cost",
        "candidate_red_stopping_margin_cost",
        "candidate_planned_red_light_cost",
        "candidate_horizon_planned_red_light_cost",
        "candidate_red_light_cost",
    ):
        if key not in raw:
            continue
        try:
            values = _vector(
                raw[key],
                candidate_count,
                f"{label} {key}",
                nonnegative=True,
            )
        except ValueError:
            continue
        components.append(values)
        component_names.append(key)
        source_fields.append(key)
    if not components:
        return _missing_family(
            [
                "candidate_horizon_union_planned_red_light_cost",
                "candidate_full_horizon_planned_red_light_cost",
                "candidate_red_stopping_margin_cost",
            ]
        )
    return _family(
        _component_max(components),
        components=component_names,
        source_fields=source_fields,
    )


def _family(
    values: np.ndarray,
    *,
    components: list[str],
    source_fields: list[str],
) -> dict[str, Any]:
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    finite = bool(np.all(np.isfinite(arr)))
    nonnegative = bool(np.all(arr >= -1e-12))
    if nonnegative:
        arr = np.maximum(arr, 0.0)
    return {
        "available": True,
        "components": components,
        "source_fields": source_fields,
        "finite": finite,
        "nonnegative": nonnegative,
        "values": arr,
    }


def _missing_family(missing_fields: list[str]) -> dict[str, Any]:
    return {
        "available": False,
        "components": [],
        "source_fields": [],
        "missing_source_fields": missing_fields,
        "finite": False,
        "nonnegative": False,
        "values": None,
    }


def _field_coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    coverage: dict[str, Any] = {}
    total_records = len(records)
    total_candidate_rows = int(sum(record["candidate_count"] for record in records))
    for family in ATOM_FAMILIES:
        available_records = [
            record for record in records if record["families"][family]["available"]
        ]
        missing_records = total_records - len(available_records)
        candidate_rows = int(sum(record["candidate_count"] for record in available_records))
        components: dict[str, int] = defaultdict(int)
        source_fields: dict[str, int] = defaultdict(int)
        missing_fields: dict[str, int] = defaultdict(int)
        for record in records:
            item = record["families"][family]
            for component in item.get("components", []):
                components[component] += 1
            for source_field in item.get("source_fields", []):
                source_fields[source_field] += 1
            for missing in item.get("missing_source_fields", []):
                missing_fields[missing] += 1
        coverage[family] = {
            "records_available": len(available_records),
            "records_total": total_records,
            "record_coverage_rate": len(available_records) / max(total_records, 1),
            "candidate_rows_available": candidate_rows,
            "candidate_rows_total": total_candidate_rows,
            "candidate_row_coverage_rate": candidate_rows / max(total_candidate_rows, 1),
            "records_missing": missing_records,
            "components": dict(sorted(components.items())),
            "source_fields": dict(sorted(source_fields.items())),
            "missing_source_fields": dict(sorted(missing_fields.items())),
        }
    return coverage


def _atom_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    for family in ATOM_FAMILIES:
        arrays = [
            record["families"][family]["values"]
            for record in records
            if record["families"][family]["available"]
        ]
        selected_values = [
            float(record["families"][family]["values"][record["selected_index"]])
            for record in records
            if record["families"][family]["available"]
        ]
        if arrays:
            values = np.concatenate(arrays).astype(np.float64)
        else:
            values = np.asarray([], dtype=np.float64)
        summary = _summary(values)
        summary.update(
            {
                "finite": bool(values.size > 0 and np.all(np.isfinite(values))),
                "nonnegative": bool(values.size > 0 and np.all(values >= -1e-12)),
                "nonzero_rate": (
                    float(np.mean(values > 1e-12)) if values.size else None
                ),
                "selected_mean": (
                    float(np.mean(selected_values)) if selected_values else None
                ),
            }
        )
        summaries[family] = summary
    return summaries


def _convexity_checks(
    records: list[dict[str, Any]],
    field_coverage: dict[str, Any],
    atom_summary: dict[str, Any],
    bucket_counts: dict[str, dict[str, int]],
    *,
    required_buckets: tuple[str, ...],
) -> dict[str, Any]:
    all_families_available = all(
        field_coverage[family]["records_available"] == field_coverage[family]["records_total"]
        for family in ATOM_FAMILIES
    )
    all_vectors_ok = all(
        bool(atom_summary[family]["finite"]) and bool(atom_summary[family]["nonnegative"])
        for family in ATOM_FAMILIES
    )
    present_buckets = set(bucket_counts)
    return {
        "current_tick_fixed_candidate_quantities": True,
        "finite_candidate_sets": all(record["candidate_count"] > 0 for record in records),
        "future_outcome_labels_used_for_atoms": False,
        "all_atom_families_available_for_all_records": all_families_available,
        "all_available_atoms_finite_and_nonnegative": all_vectors_ok,
        "score_affine_in_weights_preserved": True,
        "simplex_cvar_l2_master_convex_preserved": True,
        "dp_side_classical_benders_claimed": False,
        "required_scenario_buckets_present": all(
            bucket in present_buckets for bucket in required_buckets
        ),
        "missing_required_buckets": [
            bucket for bucket in required_buckets if bucket not in present_buckets
        ],
    }


def _decision(
    field_coverage: dict[str, Any],
    convexity_checks: dict[str, Any],
    bucket_counts: dict[str, dict[str, int]],
    *,
    formal_seed_records: int,
    required_buckets: tuple[str, ...],
) -> dict[str, Any]:
    missing_families = [
        family
        for family in ATOM_FAMILIES
        if field_coverage[family]["records_available"]
        < field_coverage[family]["records_total"]
    ]
    expected_false_checks = {
        "future_outcome_labels_used_for_atoms",
        "dp_side_classical_benders_claimed",
    }
    failed_checks = [
        key
        for key, value in convexity_checks.items()
        if isinstance(value, bool)
        and (
            (key in expected_false_checks and value)
            or (key not in expected_false_checks and not value)
        )
    ]
    missing_buckets = [
        bucket for bucket in required_buckets if bucket not in set(bucket_counts)
    ]
    if formal_seed_records:
        status = "material_atom_schema_availability_formal_seed_conflict"
        next_step = "Exclude formal seeds before using this atom availability evidence."
    elif missing_families:
        status = "material_atom_schema_availability_incomplete"
        next_step = (
            "Do not train or replay. Fill or redesign missing material atom "
            "families before any weight audit."
        )
    elif missing_buckets:
        status = "material_atom_schema_availability_bucket_incomplete"
        next_step = (
            "Do not train or replay. Re-run the audit on non-formal logs with "
            "the required scenario bucket coverage."
        )
    elif failed_checks:
        status = "material_atom_schema_availability_math_conflict"
        next_step = "Reject this atom schema or repair failed convexity/leakage checks."
    else:
        status = "material_atom_schema_availability_ready_for_offline_weight_audit"
        next_step = (
            "Only an offline no-leak weight/sensitivity audit is justified next; "
            "online selector promotion, closed-loop replay, formal seeds, and "
            "CAMP retraining remain blocked."
        )
    return {
        "status": status,
        "missing_atom_families": missing_families,
        "missing_required_buckets": missing_buckets,
        "failed_convexity_checks": failed_checks,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "authorized_next_work": (
            "offline_material_atom_weight_audit_design_only"
            if status == "material_atom_schema_availability_ready_for_offline_weight_audit"
            else None
        ),
        "next_step": next_step,
    }


def _log_context(log_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    metadata = parse_selection_log_metadata(log_path)
    validation_summary = _read_json_if_exists(
        log_path.with_name("camp_validation_summary.json")
    )
    benchmark = validation_summary.get("benchmark", {})
    if not isinstance(benchmark, dict):
        benchmark = {}
    route = benchmark.get("route")
    route_name = Path(str(route)).stem if route is not None else metadata.route
    traffic_lights = benchmark.get("traffic_lights")
    if traffic_lights is None:
        traffic_lights = metadata.traffic_light == "on"
    max_npcs = benchmark.get("max_npcs")
    if max_npcs is None:
        max_npcs = metadata.npc_count
    seed = benchmark.get("seed")
    if seed is None:
        seed = metadata.seed
    row = {
        "run_key": _run_key(validation_summary, log_path.parent),
        "route": route,
        "route_name": route_name,
        "seed": seed,
        "max_npcs": max_npcs,
        "traffic_lights": bool(traffic_lights),
        "advance_mode": benchmark.get(
            "advance_mode",
            validation_summary.get("advance_mode"),
        ),
    }
    return {
        **row,
        "log_path": str(log_path),
        "scenario_buckets": _scenario_buckets(row, manifest),
    }


def _normalized_context(context: dict[str, Any]) -> dict[str, Any]:
    seed = context.get("seed")
    try:
        seed_value = None if seed is None else int(seed)
    except (TypeError, ValueError):
        seed_value = None
    buckets = context.get("scenario_buckets")
    if not isinstance(buckets, list) or not buckets:
        buckets = ["overall"]
    for bucket in buckets:
        if bucket not in SUPPORTED_SCENARIO_BUCKETS:
            raise ValueError(f"Unsupported scenario bucket: {bucket}")
    return {
        **context,
        "seed": seed_value,
        "formal_seed": bool(context.get("formal_seed", seed_value in FORMAL_SEEDS)),
        "scenario_buckets": list(dict.fromkeys(str(bucket) for bucket in buckets)),
    }


def _scenario_bucket_counts(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        for bucket in record["context"]["scenario_buckets"]:
            grouped[bucket].append(record)
    return {
        bucket: {
            "records": len(bucket_records),
            "candidate_rows": int(
                sum(record["candidate_count"] for record in bucket_records)
            ),
        }
        for bucket, bucket_records in sorted(
            grouped.items(),
            key=lambda item: (_bucket_order(item[0]), item[0]),
        )
    }


def _bucket_order(bucket: str) -> int:
    order = [
        "overall",
        "normal",
        "traffic_light",
        "red_light_turn",
        "sharp_turn",
        "npc_interaction",
        "dense_scene",
        "lane_change_or_merge",
    ]
    return order.index(bucket) if bucket in order else len(order)


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def _first_vector(
    raw: dict[str, Any],
    candidate_count: int,
    label: str,
    keys: tuple[str, ...],
    *,
    nonnegative: bool,
) -> tuple[str, np.ndarray] | None:
    for key in keys:
        if key not in raw:
            continue
        try:
            return (
                key,
                _vector(
                    raw[key],
                    candidate_count,
                    f"{label} {key}",
                    nonnegative=nonnegative,
                ),
            )
        except ValueError:
            continue
    return None


def _vector(
    value: Any,
    size: int,
    label: str,
    *,
    nonnegative: bool,
) -> np.ndarray:
    arr = np.asarray(value, dtype=np.float64).reshape(-1)
    if arr.shape != (size,):
        raise ValueError(f"{label} must have shape [{size}], got {arr.shape}.")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{label} must contain finite values.")
    if nonnegative and np.any(arr < -1e-12):
        raise ValueError(f"{label} must contain nonnegative values.")
    return np.maximum(arr, 0.0) if nonnegative else arr


def _bool_vector(value: Any, size: int, label: str) -> np.ndarray:
    arr = np.asarray(value, dtype=bool).reshape(-1)
    if arr.shape != (size,):
        raise ValueError(f"{label} must have shape [{size}], got {arr.shape}.")
    return arr


def _component_max(components: list[np.ndarray]) -> np.ndarray:
    return np.max(np.vstack([np.asarray(item, dtype=np.float64) for item in components]), axis=0)


def _prefix_shape_deviation(value: Any, candidate_count: int, label: str) -> np.ndarray:
    arr = np.asarray(value, dtype=np.float64)
    if arr.ndim < 3 or arr.shape[0] != candidate_count or arr.shape[-1] < 2:
        raise ValueError(
            f"{label} candidate_perfect_tracker_postprocessed_reference_prefix "
            "must have shape [num_candidates, horizon, >=2]."
        )
    if not np.all(np.isfinite(arr)):
        raise ValueError(
            f"{label} candidate_perfect_tracker_postprocessed_reference_prefix "
            "must contain finite values."
        )
    delta = arr[..., :2] - arr[0:1, ..., :2]
    return np.mean(np.linalg.norm(delta, axis=-1), axis=-1)


def _summary(values: np.ndarray) -> dict[str, Any]:
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return {
            "n": 0,
            "mean": None,
            "min": None,
            "p50": None,
            "p95": None,
            "max": None,
        }
    return {
        "n": int(finite.size),
        "mean": float(np.mean(finite)),
        "min": float(np.min(finite)),
        "p50": float(np.percentile(finite, 50.0)),
        "p95": float(np.percentile(finite, 95.0)),
        "max": float(np.max(finite)),
    }


def _validate_required_buckets(required_buckets: tuple[str, ...]) -> None:
    invalid = [
        bucket
        for bucket in required_buckets
        if bucket not in SUPPORTED_SCENARIO_BUCKETS or bucket == "overall"
    ]
    if invalid:
        raise ValueError(f"Unsupported required scenario buckets: {invalid}.")


def _atom_definitions() -> dict[str, Any]:
    return {
        "hard_feasibility_deficit": (
            "1 - feasible_mask for each DP candidate, interpreted as a "
            "nonnegative hard-feasibility deficit."
        ),
        "support_preservation_deficit": (
            "max nonnegative deficit in planned route progress, step reach, or "
            "target speed relative to the current selected candidate."
        ),
        "comfort_envelope_excess": (
            "max nonnegative relative jerk/lateral excess versus the current "
            "selected candidate plus an absolute 2.0 m/s^2 lateral guard when "
            "tracker lateral acceleration is available."
        ),
        "top1_shape_deviation": (
            "nonnegative DP-prior deviation cost, or mean prefix L2 deviation "
            "from candidate0 when the DP-prior scalar is unavailable."
        ),
        "traffic_rule_exposure": (
            "max nonnegative planned red-light or red-stopping exposure from "
            "current-tick candidate diagnostics."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Material Atom Schema Availability Audit",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Decision: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Records",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in (
        "logs",
        "total",
        "candidate_rows",
        "formal_seed_records",
        "outcome_labels_present_records",
    ):
        lines.append(f"| `{key}` | `{report['records'][key]}` |")
    lines.extend(
        [
            "",
            "## Field Coverage",
            "",
            "| Atom Family | Records | Candidate Rows | Missing Records | Source Fields |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for family in ATOM_FAMILIES:
        coverage = report["field_coverage"][family]
        fields = ", ".join(f"`{key}`" for key in coverage["source_fields"]) or "`none`"
        lines.append(
            f"| `{family}` | `{coverage['records_available']}/{coverage['records_total']}` | "
            f"`{coverage['candidate_rows_available']}/{coverage['candidate_rows_total']}` | "
            f"`{coverage['records_missing']}` | {fields} |"
        )
    lines.extend(
        [
            "",
            "## Atom Summary",
            "",
            "| Atom Family | Nonnegative | Finite | Mean | P95 | Nonzero Rate |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for family in ATOM_FAMILIES:
        summary = report["atom_summary"][family]
        lines.append(
            f"| `{family}` | `{summary['nonnegative']}` | `{summary['finite']}` | "
            f"{_fmt(summary['mean'])} | {_fmt(summary['p95'])} | "
            f"{_fmt(summary['nonzero_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Scenario Buckets",
            "",
            "| Bucket | Records | Candidate Rows |",
            "| --- | ---: | ---: |",
        ]
    )
    for bucket, counts in report["records"]["scenario_bucket_counts"].items():
        lines.append(
            f"| `{bucket}` | `{counts['records']}` | `{counts['candidate_rows']}` |"
        )
    lines.extend(
        [
            "",
            "## Convexity And Leakage Checks",
            "",
            "| Check | Value |",
            "| --- | --- |",
        ]
    )
    for key, value in report["convexity_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
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
