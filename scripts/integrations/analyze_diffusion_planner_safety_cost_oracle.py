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
    FORMAL_SEEDS,
    SAFETY_COST_V1_ALPHA,
    SAFETY_COST_V1_CLIP,
    SAFETY_COST_V1_NORMALIZATION,
    SAFETY_COST_V1_WEIGHTS,
    SUPPORTED_SCENARIO_BUCKETS,
    _load_scenario_bucket_manifest,
    _mean_ci,
    _paired_cvar_delta_ci,
    _run_key,
    _scenario_buckets,
)


EPS = 1e-12
TOP1_INDEX = 0
REQUIRED_OUTCOME_FIELDS = (
    "progress_m",
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
    "mean_jerk_mps3",
    "mean_lateral_acceleration_mps2",
)
BOOL_COMPONENTS = (
    ("collision", "collision"),
    ("near_miss", "near_miss"),
    ("lane_violation", "lane_violation"),
    ("red_light_violation", "realized_red_light"),
)
ORDERED_BUCKETS = (
    "overall",
    "normal",
    "traffic_light",
    "red_light_turn",
    "sharp_turn",
    "npc_interaction",
    "dense_scene",
    "lane_change_or_merge",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only candidate-branch SafetyCost v1 oracle opportunity audit "
            "for fixed Diffusion Planner candidate pools."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--fail_on_formal_seeds",
        action="store_true",
        help="Exit nonzero if any selection log belongs to seeds 11, 12, or 13.",
    )
    return parser.parse_args()


def analyze(
    paths: list[Path],
    *,
    scenario_bucket_manifest: Path | None = None,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")

    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)
    rows: list[dict[str, Any]] = []
    logs: list[dict[str, Any]] = []
    for log_path in log_paths:
        context = _log_context(log_path, manifest)
        formal_seed = context["seed"] in FORMAL_SEEDS
        if formal_seed and fail_on_formal_seeds:
            raise ValueError(f"Formal seed log is forbidden: {log_path}")
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        logs.append(
            {
                "path": str(log_path),
                "run_key": context["run_key"],
                "seed": context["seed"],
                "formal_seed": formal_seed,
                "scenario_buckets": context["scenario_buckets"],
                "records": len(payload),
            }
        )
        for record_index, record in enumerate(payload):
            rows.append(
                _record_row(
                    record,
                    label=f"{log_path} record {record_index}",
                    log_path=log_path,
                    record_index=record_index,
                    context=context,
                    formal_seed=formal_seed,
                )
            )

    formal_seed_logs = [log["path"] for log in logs if log["formal_seed"]]
    return {
        "analysis": {
            "name": "dp_camp_candidate_branch_safety_cost_v1_oracle",
            "role": "offline opportunity audit for a fixed DP candidate pool",
            "training": False,
            "online_selector_change": False,
            "top1_definition": "candidate index 0 from the fixed DP pool",
            "oracle_definition": (
                "minimum candidate-branch SafetyCost v1 among base-feasible "
                "candidates; when all candidates are base-infeasible, the "
                "fallback branch audits all candidates separately"
            ),
            "safety_cost_scope": (
                "candidate branch proxy, not full closed-loop run-level "
                "SafetyCost v1"
            ),
            "progress_component": (
                "route_shortfall weight is approximated by per-record "
                "relative progress shortfall from the best eligible branch"
            ),
            "planned_red_component": (
                "uses candidate_horizon_union_planned_red_light_cost when "
                "available, then candidate_full_horizon_planned_red_light_cost; "
                "missing values are recorded and contribute zero"
            ),
            "future_outcome_leakage": (
                "candidate_closed_loop_outcomes are offline labels only; this "
                "audit must not be used as an online selector"
            ),
            "math_boundary": (
                "The audit does not change DP, CAMP atoms, feasible masks, "
                "affine scores, fallback policy, or the simplex/CVaR/L2 master. "
                "It is not a Benders subproblem."
            ),
            "scenario_bucket_manifest": (
                None
                if scenario_bucket_manifest is None
                else str(scenario_bucket_manifest)
            ),
            "explicit_bucket_labels_only": True,
            "formal_seed_policy": (
                "forbidden" if fail_on_formal_seeds else "reported_only"
            ),
            "formal_seed_logs": formal_seed_logs,
        },
        "logs": {
            "total": len(logs),
            "formal_seed_logs": len(formal_seed_logs),
            "items": logs,
        },
        "records": _record_summary(rows),
        "overall": _aggregate(rows, seed_key="overall"),
        "by_bucket": [
            {
                "bucket": bucket,
                **_aggregate(bucket_rows, seed_key=f"bucket:{bucket}"),
            }
            for bucket, bucket_rows in _records_by_bucket(rows).items()
        ],
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
        "steps": benchmark.get("steps"),
        "max_npcs": max_npcs,
        "spawn_probability": benchmark.get("spawn_probability"),
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


def _record_row(
    record: dict[str, Any],
    *,
    label: str,
    log_path: Path,
    record_index: int,
    context: dict[str, Any],
    formal_seed: bool,
) -> dict[str, Any]:
    candidate_count = _candidate_count(record, label)
    selected_index = _selected_index(record, candidate_count, label)
    feasible = _bool_vector(
        record.get("feasible_mask"),
        candidate_count,
        f"{label} feasible_mask",
    )
    outcomes = _outcomes(
        record.get("candidate_closed_loop_outcomes"),
        candidate_count,
        label,
    )
    planned_red, planned_red_source = _planned_red_values(record, candidate_count)
    eligible = feasible.copy()
    branch = "base_feasible"
    if not eligible.any():
        eligible = np.ones(candidate_count, dtype=bool)
        branch = "fallback_all_infeasible"

    components = _candidate_branch_components(
        outcomes,
        planned_red,
        eligible,
    )
    costs = np.asarray([component["cost"] for component in components], dtype=np.float64)
    oracle_index = _oracle_index(costs, eligible)
    top1_cost = float(costs[TOP1_INDEX])
    camp_cost = float(costs[selected_index])
    oracle_cost = float(costs[oracle_index])
    top1_outcome = outcomes[TOP1_INDEX]
    camp_outcome = outcomes[selected_index]
    oracle_outcome = outcomes[oracle_index]
    return {
        "log_path": str(log_path),
        "record_index": int(record_index),
        "run_key": context["run_key"],
        "route_name": context["route_name"],
        "seed": context["seed"],
        "formal_seed": bool(formal_seed),
        "scenario_buckets": context["scenario_buckets"],
        "branch": branch,
        "candidate_count": int(candidate_count),
        "eligible_candidate_count": int(eligible.sum()),
        "top1_index": TOP1_INDEX,
        "camp_index": int(selected_index),
        "oracle_index": int(oracle_index),
        "top1_eligible": bool(eligible[TOP1_INDEX]),
        "camp_eligible": bool(eligible[selected_index]),
        "planned_red_source": planned_red_source,
        "costs": {
            "top1": top1_cost,
            "camp": camp_cost,
            "oracle": oracle_cost,
        },
        "deltas": {
            "camp_minus_top1": camp_cost - top1_cost,
            "oracle_minus_top1": oracle_cost - top1_cost,
            "camp_minus_oracle": camp_cost - oracle_cost,
            "oracle_progress_minus_top1_m": _outcome_float(
                oracle_outcome,
                "progress_m",
            )
            - _outcome_float(top1_outcome, "progress_m"),
            "camp_progress_minus_top1_m": _outcome_float(camp_outcome, "progress_m")
            - _outcome_float(top1_outcome, "progress_m"),
            "oracle_jerk_minus_top1_mps3": _outcome_float(
                oracle_outcome,
                "mean_jerk_mps3",
            )
            - _outcome_float(top1_outcome, "mean_jerk_mps3"),
            "oracle_lateral_minus_top1_mps2": _outcome_float(
                oracle_outcome,
                "mean_lateral_acceleration_mps2",
            )
            - _outcome_float(top1_outcome, "mean_lateral_acceleration_mps2"),
        },
        "relations": {
            "oracle_beats_top1": oracle_cost < top1_cost - EPS,
            "camp_beats_top1": camp_cost < top1_cost - EPS,
            "camp_matches_top1": selected_index == TOP1_INDEX,
            "oracle_matches_top1": oracle_index == TOP1_INDEX,
            "camp_matches_oracle": selected_index == oracle_index,
        },
        "hard_components": {
            "top1": _hard_components(top1_outcome),
            "camp": _hard_components(camp_outcome),
            "oracle": _hard_components(oracle_outcome),
        },
        "component_costs": {
            "top1": components[TOP1_INDEX],
            "camp": components[selected_index],
            "oracle": components[oracle_index],
        },
    }


def _candidate_branch_components(
    outcomes: list[dict[str, Any]],
    planned_red: np.ndarray,
    eligible: np.ndarray,
) -> list[dict[str, Any]]:
    progress = np.asarray(
        [_outcome_float(outcome, "progress_m") for outcome in outcomes],
        dtype=np.float64,
    )
    progress_ref = float(np.max(progress[eligible])) if eligible.any() else float(np.max(progress))
    progress_denom = max(progress_ref, 1.0)
    components = []
    for index, outcome in enumerate(outcomes):
        raw_components = {
            "collision": float(bool(outcome["collision"])),
            "near_miss": float(bool(outcome["near_miss"])),
            "lane_violation": float(bool(outcome["lane_violation"])),
            "realized_red_light": float(bool(outcome["red_light_violation"])),
            "planned_red_light": min(max(float(planned_red[index]), 0.0), 1.0),
            "mean_jerk": min(
                _outcome_float(outcome, "mean_jerk_mps3")
                / SAFETY_COST_V1_NORMALIZATION["mean_jerk_magnitude_mps3"],
                SAFETY_COST_V1_CLIP,
            ),
            "mean_lateral_acceleration": min(
                _outcome_float(outcome, "mean_lateral_acceleration_mps2")
                / SAFETY_COST_V1_NORMALIZATION[
                    "mean_lateral_acceleration_mps2"
                ],
                SAFETY_COST_V1_CLIP,
            ),
            "route_shortfall": min(
                max((progress_ref - float(progress[index])) / progress_denom, 0.0),
                1.0,
            ),
        }
        weighted = {
            key: float(value) * SAFETY_COST_V1_WEIGHTS[key]
            for key, value in raw_components.items()
        }
        components.append(
            {
                "raw_components": raw_components,
                "weighted_components": weighted,
                "cost": float(sum(weighted.values())),
            }
        )
    return components


def _aggregate(rows: list[dict[str, Any]], *, seed_key: str) -> dict[str, Any]:
    if not rows:
        return {
            "records": 0,
            "logs": 0,
            "cost_mean": _empty_named_metrics(("top1", "camp", "oracle")),
            "record_rates": _empty_named_metrics(
                (
                    "oracle_beats_top1",
                    "camp_beats_top1",
                    "camp_matches_top1",
                    "oracle_matches_top1",
                    "camp_matches_oracle",
                )
            ),
            "run_level_delta_ci": {},
            "run_level_cvar90_delta": {},
            "progress_and_comfort_delta_mean": {},
            "hard_component_nonworse_rate": {},
        }
    costs = {name: [row["costs"][name] for row in rows] for name in ("top1", "camp", "oracle")}
    relation_names = tuple(next(iter(rows))["relations"].keys())
    deltas = {
        "camp_minus_top1": [row["deltas"]["camp_minus_top1"] for row in rows],
        "oracle_minus_top1": [
            row["deltas"]["oracle_minus_top1"] for row in rows
        ],
        "camp_minus_oracle": [row["deltas"]["camp_minus_oracle"] for row in rows],
    }
    grouped = _rows_by_log(rows)
    run_delta_values = {
        name: [_mean([row["deltas"][name] for row in log_rows]) for log_rows in grouped.values()]
        for name in deltas
    }
    return {
        "records": len(rows),
        "logs": len(grouped),
        "base_feasible_records": sum(row["branch"] == "base_feasible" for row in rows),
        "fallback_all_infeasible_records": sum(
            row["branch"] == "fallback_all_infeasible" for row in rows
        ),
        "formal_seed_records": sum(int(row["formal_seed"]) for row in rows),
        "mean_eligible_candidates": _mean(
            [float(row["eligible_candidate_count"]) for row in rows]
        ),
        "cost_mean": {name: _mean(values) for name, values in costs.items()},
        "record_delta_mean": {name: _mean(values) for name, values in deltas.items()},
        "record_rates": {
            name: _mean([float(row["relations"][name]) for row in rows])
            for name in relation_names
        },
        "run_level_delta_ci": {
            name: _mean_ci(values, seed_key=f"{seed_key}|{name}")
            for name, values in run_delta_values.items()
        },
        "run_level_cvar90_delta": {
            "camp_minus_top1": _paired_cvar_delta_ci(
                [_mean([row["costs"]["camp"] for row in log_rows]) for log_rows in grouped.values()],
                [_mean([row["costs"]["top1"] for row in log_rows]) for log_rows in grouped.values()],
                alpha=SAFETY_COST_V1_ALPHA,
                seed_key=f"{seed_key}|camp_minus_top1|cvar90",
            ),
            "oracle_minus_top1": _paired_cvar_delta_ci(
                [_mean([row["costs"]["oracle"] for row in log_rows]) for log_rows in grouped.values()],
                [_mean([row["costs"]["top1"] for row in log_rows]) for log_rows in grouped.values()],
                alpha=SAFETY_COST_V1_ALPHA,
                seed_key=f"{seed_key}|oracle_minus_top1|cvar90",
            ),
        },
        "progress_and_comfort_delta_mean": {
            name: _mean([row["deltas"][name] for row in rows])
            for name in (
                "oracle_progress_minus_top1_m",
                "camp_progress_minus_top1_m",
                "oracle_jerk_minus_top1_mps3",
                "oracle_lateral_minus_top1_mps2",
            )
        },
        "hard_component_nonworse_rate": _hard_component_nonworse_rates(rows),
        "planned_red_sources": _value_counts(
            [str(row["planned_red_source"]) for row in rows]
        ),
    }


def _record_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total": len(rows),
        "base_feasible": sum(row["branch"] == "base_feasible" for row in rows),
        "fallback_all_infeasible": sum(
            row["branch"] == "fallback_all_infeasible" for row in rows
        ),
        "formal_seed_records": sum(int(row["formal_seed"]) for row in rows),
        "scenario_bucket_counts": {
            bucket: len(bucket_rows)
            for bucket, bucket_rows in _records_by_bucket(rows).items()
        },
    }


def _hard_component_nonworse_rates(rows: list[dict[str, Any]]) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for candidate_name in ("camp", "oracle"):
        for outcome_field, component_name in BOOL_COMPONENTS:
            result[f"{candidate_name}_{component_name}_vs_top1"] = _mean(
                [
                    float(
                        row["hard_components"][candidate_name][outcome_field]
                        <= row["hard_components"]["top1"][outcome_field]
                    )
                    for row in rows
                ]
            )
    return result


def _records_by_bucket(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets = row.get("scenario_buckets")
        if not isinstance(buckets, list) or not buckets:
            buckets = ["overall"]
        for bucket in buckets:
            if bucket not in SUPPORTED_SCENARIO_BUCKETS:
                raise ValueError(f"Unsupported scenario bucket: {bucket}")
            grouped[str(bucket)].append(row)
    ordered = [bucket for bucket in ORDERED_BUCKETS if bucket in grouped]
    ordered.extend(sorted(bucket for bucket in grouped if bucket not in ordered))
    return {bucket: grouped[bucket] for bucket in ordered}


def _rows_by_log(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["log_path"])].append(row)
    return dict(sorted(grouped.items()))


def _oracle_index(costs: np.ndarray, eligible: np.ndarray) -> int:
    masked = np.where(eligible, costs, np.inf)
    min_cost = float(np.min(masked))
    indices = np.flatnonzero(np.isclose(masked, min_cost, atol=EPS, rtol=0.0))
    if indices.size == 0:
        raise ValueError("No eligible candidate for oracle selection.")
    return int(indices[0])


def _candidate_count(record: dict[str, Any], label: str) -> int:
    raw = record.get("num_candidates")
    if raw is None and isinstance(record.get("candidate_closed_loop_outcomes"), list):
        raw = len(record["candidate_closed_loop_outcomes"])
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must declare num_candidates.") from None
    if value <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    return value


def _selected_index(record: dict[str, Any], candidate_count: int, label: str) -> int:
    try:
        selected = int(record.get("selected_index"))
    except (TypeError, ValueError):
        raise ValueError(f"{label} selected_index is invalid.") from None
    if selected < 0 or selected >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    return selected


def _outcomes(values: Any, size: int, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, list) or len(values) != size:
        raise ValueError(f"{label} must contain {size} candidate outcomes.")
    outcomes: list[dict[str, Any]] = []
    for index, outcome in enumerate(values):
        if not isinstance(outcome, dict):
            raise ValueError(f"{label} outcome {index} must be a dict.")
        if outcome.get("candidate_index", index) != index:
            raise ValueError(f"{label} outcome indices must be contiguous.")
        missing = [field for field in REQUIRED_OUTCOME_FIELDS if field not in outcome]
        if missing:
            raise ValueError(f"{label} outcome {index} missing fields: {missing}")
        outcomes.append(outcome)
    return outcomes


def _planned_red_values(record: dict[str, Any], size: int) -> tuple[np.ndarray, str]:
    for key in (
        "candidate_horizon_union_planned_red_light_cost",
        "candidate_full_horizon_planned_red_light_cost",
    ):
        values = record.get(key)
        if values is not None:
            return _finite_nonnegative_vector(values, size, key), key
    return np.zeros(size, dtype=np.float64), "missing_zero"


def _bool_vector(values: Any, size: int, label: str) -> np.ndarray:
    raw = np.asarray(values, dtype=object).reshape(-1)
    if raw.shape != (size,) or not all(isinstance(value, (bool, np.bool_)) for value in raw):
        raise ValueError(f"{label} must contain {size} booleans.")
    return raw.astype(bool)


def _finite_nonnegative_vector(values: Any, size: int, label: str) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float64).reshape(-1)
    if vector.shape != (size,):
        raise ValueError(f"{label} must have shape [{size}].")
    if not np.all(np.isfinite(vector)) or np.any(vector < 0.0):
        raise ValueError(f"{label} must be finite and nonnegative.")
    return vector


def _outcome_float(outcome: dict[str, Any], field: str) -> float:
    try:
        value = float(outcome[field])
    except (TypeError, ValueError):
        raise ValueError(f"Outcome {field} must be numeric.") from None
    if not np.isfinite(value) or value < 0.0:
        raise ValueError(f"Outcome {field} must be finite and nonnegative.")
    return value


def _hard_components(outcome: dict[str, Any]) -> dict[str, float]:
    return {
        outcome_field: float(bool(outcome[outcome_field]))
        for outcome_field, _ in BOOL_COMPONENTS
    }


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def _value_counts(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _empty_named_metrics(names: tuple[str, ...]) -> dict[str, None]:
    return {name: None for name in names}


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def render_markdown(report: dict[str, Any]) -> str:
    records = report["records"]
    overall = report["overall"]
    delta = overall["run_level_delta_ci"]
    lines = [
        "# DP-CAMP Candidate-Branch SafetyCost v1 Oracle Audit",
        "",
        "This is an offline opportunity audit over fixed DP candidate pools. It "
        "does not change the online selector, train CAMP, modify DP, or prove "
        "full closed-loop run-level SafetyCost improvement.",
        "",
        f"- Logs: `{report['logs']['total']}`",
        f"- Records: `{records['total']}`",
        f"- Base-feasible records: `{records['base_feasible']}`",
        f"- All-infeasible fallback records: `{records['fallback_all_infeasible']}`",
        f"- Formal-seed records: `{records['formal_seed_records']}`",
        "",
        "## Overall Opportunity",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Mean Top-1 branch cost | {_fmt(overall['cost_mean']['top1'])} |",
        f"| Mean CAMP branch cost | {_fmt(overall['cost_mean']['camp'])} |",
        f"| Mean oracle branch cost | {_fmt(overall['cost_mean']['oracle'])} |",
        f"| Oracle beats Top-1 rate | {_fmt(overall['record_rates']['oracle_beats_top1'])} |",
        f"| CAMP beats Top-1 rate | {_fmt(overall['record_rates']['camp_beats_top1'])} |",
        f"| CAMP matches oracle rate | {_fmt(overall['record_rates']['camp_matches_oracle'])} |",
        f"| Oracle mean delta vs Top-1 | {_fmt(delta['oracle_minus_top1']['mean'])} |",
        f"| Oracle delta CI high | {_fmt(delta['oracle_minus_top1']['ci95_high'])} |",
        f"| CAMP mean delta vs Top-1 | {_fmt(delta['camp_minus_top1']['mean'])} |",
        f"| CAMP delta CI high | {_fmt(delta['camp_minus_top1']['ci95_high'])} |",
        "",
        "## Scenario Buckets",
        "",
        "| Bucket | Records | Logs | Oracle beats Top-1 | Oracle mean delta | CI high | CAMP mean delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["by_bucket"]:
        bucket_delta = row["run_level_delta_ci"]
        lines.append(
            f"| `{row['bucket']}` | "
            f"{row['records']} | "
            f"{row['logs']} | "
            f"{_fmt(row['record_rates']['oracle_beats_top1'])} | "
            f"{_fmt(bucket_delta['oracle_minus_top1']['mean'])} | "
            f"{_fmt(bucket_delta['oracle_minus_top1']['ci95_high'])} | "
            f"{_fmt(bucket_delta['camp_minus_top1']['mean'])} |"
        )
    hard = overall["hard_component_nonworse_rate"]
    progress = overall["progress_and_comfort_delta_mean"]
    lines.extend(
        [
            "",
            "## Guards",
            "",
            "| Guard diagnostic | Value |",
            "| --- | ---: |",
            f"| Oracle collision nonworse vs Top-1 | {_fmt(hard['oracle_collision_vs_top1'])} |",
            f"| Oracle near-miss nonworse vs Top-1 | {_fmt(hard['oracle_near_miss_vs_top1'])} |",
            f"| Oracle lane nonworse vs Top-1 | {_fmt(hard['oracle_lane_violation_vs_top1'])} |",
            f"| Oracle red-light nonworse vs Top-1 | {_fmt(hard['oracle_realized_red_light_vs_top1'])} |",
            f"| Mean oracle progress delta vs Top-1 (m) | {_fmt(progress['oracle_progress_minus_top1_m'])} |",
            f"| Mean oracle jerk delta vs Top-1 (m/s^3) | {_fmt(progress['oracle_jerk_minus_top1_mps3'])} |",
            f"| Mean oracle lateral delta vs Top-1 (m/s^2) | {_fmt(progress['oracle_lateral_minus_top1_mps2'])} |",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
        ]
    )
    return "\n".join(lines) + "\n"


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (bool, np.bool_)):
        return str(bool(value))
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(number):
        return str(number)
    return f"{number:.6f}"


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    report = analyze(
        paths,
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
