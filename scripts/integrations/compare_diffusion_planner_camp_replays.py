#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    summarize_replay_artifacts,
)


SUMMARY_KEYS = (
    "closed_loop_steps",
    "num_candidates",
    "goal_reached",
    "replay_reason",
    "final_goal_distance_m",
    "min_goal_distance_m",
    "goal_distance_reduction_rate",
    "route_completion_rate",
    "safety_cost_v1",
    "distance_traveled_m",
    "obb_collision_rate",
    "near_miss_rate",
    "lane_violation_rate",
    "red_light_violation_rate",
    "planned_red_light_violation_rate",
    "mean_acceleration_magnitude_mps2",
    "max_acceleration_magnitude_mps2",
    "mean_jerk_magnitude_mps3",
    "max_jerk_magnitude_mps3",
    "mean_lateral_acceleration_mps2",
    "max_lateral_acceleration_mps2",
    "fallback_rate",
    "candidate_feasible_rate",
    "p95_selection_latency_ms",
    "n_npc_spawned",
)
BENCHMARK_KEYS = (
    "route",
    "seed",
    "steps",
    "max_npcs",
    "spawn_probability",
    "traffic_lights",
    "advance_mode",
)
PAPER_METRICS = (
    "route_completion_rate",
    "safety_cost_v1",
    "obb_collision_rate",
    "near_miss_rate",
    "lane_violation_rate",
    "red_light_violation_rate",
    "planned_red_light_violation_rate",
    "mean_jerk_magnitude_mps3",
    "fallback_rate",
    "p95_selection_latency_ms",
)
BOOTSTRAP_RESAMPLES = 10_000
SAFETY_COST_V1_ALPHA = 0.9
SAFETY_COST_V1_CLIP = 10.0
SAFETY_COST_V1_WEIGHTS = {
    "collision": 100.0,
    "near_miss": 10.0,
    "lane_violation": 20.0,
    "realized_red_light": 30.0,
    "planned_red_light": 15.0,
    "mean_jerk": 1.0,
    "mean_lateral_acceleration": 2.0,
    "route_shortfall": 2.0,
}
SAFETY_COST_V1_NORMALIZATION = {
    "mean_jerk_magnitude_mps3": 10.0,
    "mean_lateral_acceleration_mps2": 2.0,
}
SAFETY_COST_V1_NO_WORSE_METRICS = (
    "obb_collision_rate",
    "near_miss_rate",
    "lane_violation_rate",
    "red_light_violation_rate",
)
SAFETY_COST_V1_COMPLETION_TOLERANCE = 0.001
SAFETY_COST_V1_LATENCY_BUDGET_MS = 100.0
SAFETY_COST_V1_LATENCY_MARGIN_MS = 5.0
FORMAL_SEEDS = {11, 12, 13}
SUPPORTED_SCENARIO_BUCKETS = {
    "overall",
    "normal",
    "traffic_light",
    "red_light_turn",
    "sharp_turn",
    "npc_interaction",
    "dense_scene",
    "lane_change_or_merge",
}
SCENARIO_BUCKET_FILTER_FIELDS = {
    "route",
    "route_name",
    "route_stem",
    "seed",
    "steps",
    "max_npcs",
    "spawn_probability",
    "traffic_lights",
    "advance_mode",
}


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"Missing replay artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_or_build_summary(output_dir: Path) -> dict[str, Any]:
    summary_path = output_dir / "camp_validation_summary.json"
    if summary_path.is_file():
        return _read_json(summary_path)

    replay_summary = _read_json(output_dir / "camp_replay_summary.json")
    selection_log = output_dir / "camp_selection_log.json"
    records = _read_json(selection_log) if selection_log.is_file() else None
    metric_log = output_dir / "camp_metric_log.json"
    metric_records = _read_json(metric_log) if metric_log.is_file() else None
    evaluation_log = output_dir / "camp_evaluation_state_log.json"
    evaluation_records = (
        _read_json(evaluation_log) if evaluation_log.is_file() else None
    )
    summary = summarize_replay_artifacts(
        output_dir,
        selection_records=records,
        replay_result=replay_summary.get("replay_result"),
        metric_records=metric_records,
        evaluation_records=evaluation_records,
    )
    summary["selector_mode"] = replay_summary.get("selector_mode")
    summary["num_candidates"] = replay_summary.get("num_candidates")
    summary["candidate_noise_scale"] = replay_summary.get("candidate_noise_scale")
    if "benchmark" in replay_summary:
        summary["benchmark"] = replay_summary["benchmark"]
    return summary


def _run_key(summary: dict[str, Any], output_dir: Path) -> str:
    benchmark = summary.get("benchmark")
    if isinstance(benchmark, dict):
        fields = [
            benchmark.get("route"),
            benchmark.get("seed"),
            benchmark.get("steps"),
            benchmark.get("max_npcs"),
            benchmark.get("spawn_probability"),
            benchmark.get("traffic_lights"),
            benchmark.get("advance_mode"),
        ]
        if any(field is not None for field in fields):
            return "|".join(str(field) for field in fields)
    explicit = summary.get("benchmark_key")
    if explicit:
        return str(explicit)
    return str(output_dir)


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _bounded_nonnegative(value: Any, *, upper: float | None = None) -> float | None:
    number = _numeric(value)
    if number is None:
        return None
    number = max(float(number), 0.0)
    if upper is not None:
        number = min(number, float(upper))
    return number


def _safety_cost_v1_components(row: dict[str, Any]) -> dict[str, Any]:
    """Return normalized weighted SafetyCost v1 components for one run row."""

    raw_components = {
        "collision": _bounded_nonnegative(row.get("obb_collision_rate"), upper=1.0),
        "near_miss": _bounded_nonnegative(row.get("near_miss_rate"), upper=1.0),
        "lane_violation": _bounded_nonnegative(
            row.get("lane_violation_rate"),
            upper=1.0,
        ),
        "realized_red_light": _bounded_nonnegative(
            row.get("red_light_violation_rate"),
            upper=1.0,
        ),
        "planned_red_light": _bounded_nonnegative(
            row.get("planned_red_light_violation_rate"),
            upper=1.0,
        ),
        "route_shortfall": None,
        "mean_jerk": None,
        "mean_lateral_acceleration": None,
    }
    completion = _numeric(row.get("route_completion_rate"))
    if completion is not None:
        raw_components["route_shortfall"] = min(max(1.0 - completion, 0.0), 1.0)
    jerk = _bounded_nonnegative(row.get("mean_jerk_magnitude_mps3"))
    if jerk is not None:
        raw_components["mean_jerk"] = min(
            jerk / SAFETY_COST_V1_NORMALIZATION["mean_jerk_magnitude_mps3"],
            SAFETY_COST_V1_CLIP,
        )
    lateral = _bounded_nonnegative(row.get("mean_lateral_acceleration_mps2"))
    if lateral is not None:
        raw_components["mean_lateral_acceleration"] = min(
            lateral
            / SAFETY_COST_V1_NORMALIZATION["mean_lateral_acceleration_mps2"],
            SAFETY_COST_V1_CLIP,
        )

    missing = sorted(key for key, value in raw_components.items() if value is None)
    if missing:
        return {
            "available": False,
            "missing_components": missing,
            "raw_components": raw_components,
            "weighted_components": None,
            "cost": None,
        }
    weighted = {
        key: float(raw_components[key]) * SAFETY_COST_V1_WEIGHTS[key]
        for key in raw_components
    }
    return {
        "available": True,
        "missing_components": [],
        "raw_components": raw_components,
        "weighted_components": weighted,
        "cost": float(sum(weighted.values())),
    }


def _apply_safety_cost_v1(row: dict[str, Any]) -> None:
    components = _safety_cost_v1_components(row)
    row["safety_cost_v1_components"] = components
    row["safety_cost_v1"] = components["cost"]
    row["safety_cost_v1_available"] = bool(components["available"])


def _upper_tail_cvar(values: list[float], *, alpha: float) -> float | None:
    if not values:
        return None
    array = np.sort(np.asarray(values, dtype=np.float64))
    tail_count = max(1, int(np.ceil((1.0 - alpha) * array.size)))
    return float(np.mean(array[-tail_count:]))


def _cvar_ci(
    values: list[float],
    *,
    alpha: float = SAFETY_COST_V1_ALPHA,
    seed_key: str = "",
) -> dict[str, Any]:
    cvar_value = _upper_tail_cvar(values, alpha=alpha)
    if cvar_value is None:
        return {
            "n": 0,
            "cvar": None,
            "alpha": alpha,
            "ci95": None,
            "ci95_low": None,
            "ci95_high": None,
            "ci_method": "bootstrap_percentile",
        }
    if len(values) == 1:
        return {
            "n": 1,
            "cvar": cvar_value,
            "alpha": alpha,
            "ci95": 0.0,
            "ci95_low": cvar_value,
            "ci95_high": cvar_value,
            "ci_method": "bootstrap_percentile",
        }
    array = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(_seed_from_key(seed_key))
    indices = rng.integers(
        0,
        len(array),
        size=(BOOTSTRAP_RESAMPLES, len(array)),
    )
    bootstrap = [
        _upper_tail_cvar(array[index].tolist(), alpha=alpha)
        for index in indices
    ]
    low, high = np.percentile(np.asarray(bootstrap, dtype=np.float64), [2.5, 97.5])
    return {
        "n": len(values),
        "cvar": cvar_value,
        "alpha": alpha,
        "ci95": float((high - low) / 2.0),
        "ci95_low": float(low),
        "ci95_high": float(high),
        "ci_method": "bootstrap_percentile",
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
    }


def _paired_cvar_delta_ci(
    lhs_values: list[float],
    rhs_values: list[float],
    *,
    alpha: float = SAFETY_COST_V1_ALPHA,
    seed_key: str = "",
) -> dict[str, Any]:
    if len(lhs_values) != len(rhs_values):
        raise ValueError("paired CVaR deltas require equal-length vectors.")
    if not lhs_values:
        return {
            "n": 0,
            "cvar_delta": None,
            "alpha": alpha,
            "ci95": None,
            "ci95_low": None,
            "ci95_high": None,
            "ci_method": "bootstrap_percentile",
        }
    lhs = np.asarray(lhs_values, dtype=np.float64)
    rhs = np.asarray(rhs_values, dtype=np.float64)
    delta = float(
        _upper_tail_cvar(lhs.tolist(), alpha=alpha)
        - _upper_tail_cvar(rhs.tolist(), alpha=alpha)
    )
    if len(lhs_values) == 1:
        return {
            "n": 1,
            "cvar_delta": delta,
            "alpha": alpha,
            "ci95": 0.0,
            "ci95_low": delta,
            "ci95_high": delta,
            "ci_method": "bootstrap_percentile",
        }
    rng = np.random.default_rng(_seed_from_key(seed_key))
    indices = rng.integers(0, len(lhs), size=(BOOTSTRAP_RESAMPLES, len(lhs)))
    bootstrap = []
    for index in indices:
        bootstrap.append(
            _upper_tail_cvar(lhs[index].tolist(), alpha=alpha)
            - _upper_tail_cvar(rhs[index].tolist(), alpha=alpha)
        )
    low, high = np.percentile(np.asarray(bootstrap, dtype=np.float64), [2.5, 97.5])
    return {
        "n": len(lhs_values),
        "cvar_delta": delta,
        "alpha": alpha,
        "ci95": float((high - low) / 2.0),
        "ci95_low": float(low),
        "ci95_high": float(high),
        "ci_method": "bootstrap_percentile",
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
    }


def _seed_from_key(key: str) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little", signed=False)


def _mean_ci(values: list[float], *, seed_key: str = "") -> dict[str, Any]:
    if not values:
        return {
            "n": 0,
            "mean": None,
            "std": None,
            "ci95": None,
            "ci95_low": None,
            "ci95_high": None,
            "ci_method": "bootstrap_percentile",
        }
    if len(values) == 1:
        return {
            "n": 1,
            "mean": values[0],
            "std": 0.0,
            "ci95": 0.0,
            "ci95_low": values[0],
            "ci95_high": values[0],
            "ci_method": "bootstrap_percentile",
        }

    array = np.asarray(values, dtype=np.float64)
    mean = float(np.mean(array))
    std = float(np.std(array, ddof=1))
    rng = np.random.default_rng(_seed_from_key(seed_key))
    indices = rng.integers(
        0,
        len(array),
        size=(BOOTSTRAP_RESAMPLES, len(array)),
    )
    bootstrap_means = np.mean(array[indices], axis=1)
    low, high = np.percentile(bootstrap_means, [2.5, 97.5])
    return {
        "n": len(values),
        "mean": mean,
        "std": std,
        "ci95": float((high - low) / 2.0),
        "ci95_low": float(low),
        "ci95_high": float(high),
        "ci_method": "bootstrap_percentile",
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
    }


def _aggregate_rows(
    rows: list[dict[str, Any]],
    *,
    seed_prefix: str = "aggregate",
) -> list[dict[str, Any]]:
    by_variant: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_variant[str(row["variant"])].append(row)

    aggregates = []
    for variant, group in by_variant.items():
        aggregate: dict[str, Any] = {"variant": variant, "n_runs": len(group)}
        for key in SUMMARY_KEYS:
            values = [
                numeric
                for numeric in (_numeric(row.get(key)) for row in group)
                if numeric is not None
            ]
            if values:
                aggregate[key] = _mean_ci(
                    values,
                    seed_key=f"{seed_prefix}|{variant}|{key}",
                )
                if key == "safety_cost_v1":
                    aggregate["safety_cost_v1_cvar90"] = _cvar_ci(
                        values,
                        alpha=SAFETY_COST_V1_ALPHA,
                        seed_key=f"{seed_prefix}|{variant}|{key}|cvar90",
                    )
        aggregates.append(aggregate)
    return aggregates


def _paired_deltas(
    rows: list[dict[str, Any]],
    *,
    baseline: str,
    seed_prefix: str = "paired",
) -> list[dict[str, Any]]:
    by_variant: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        variant = str(row["variant"])
        run_key = str(row["run_key"])
        if run_key in by_variant[variant]:
            raise ValueError(f"Duplicate run key for {variant}: {run_key}")
        by_variant[variant][run_key] = row
    baseline_rows = by_variant.get(baseline, {})

    deltas = []
    for variant, keyed_rows in by_variant.items():
        if variant == baseline:
            continue
        common_keys = sorted(set(baseline_rows) & set(keyed_rows))
        if not common_keys:
            continue
        entry: dict[str, Any] = {
            "baseline": baseline,
            "variant": variant,
            "n_pairs": len(common_keys),
        }
        for key in SUMMARY_KEYS:
            values = []
            lhs_safety_values = []
            rhs_safety_values = []
            for run_key in common_keys:
                lhs = _numeric(keyed_rows[run_key].get(key))
                rhs = _numeric(baseline_rows[run_key].get(key))
                if lhs is not None and rhs is not None:
                    values.append(lhs - rhs)
                    if key == "safety_cost_v1":
                        lhs_safety_values.append(lhs)
                        rhs_safety_values.append(rhs)
            if values:
                entry[key] = _mean_ci(
                    values,
                    seed_key=f"{seed_prefix}|{baseline}|{variant}|{key}",
                )
                if key == "safety_cost_v1":
                    entry["safety_cost_v1_cvar90_delta"] = (
                        _paired_cvar_delta_ci(
                            lhs_safety_values,
                            rhs_safety_values,
                            alpha=SAFETY_COST_V1_ALPHA,
                            seed_key=(
                                f"{seed_prefix}|{baseline}|{variant}|"
                                f"{key}|cvar90_delta"
                            ),
                        )
                    )
        deltas.append(entry)
    return deltas


def _all_pairwise_deltas(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    variants = list(dict.fromkeys(str(row["variant"]) for row in rows))
    pairwise = []
    for baseline, variant in combinations(variants, 2):
        entries = _paired_deltas(
            rows,
            baseline=baseline,
            seed_prefix="all_pairwise",
        )
        pairwise.extend(entry for entry in entries if entry["variant"] == variant)
    return pairwise


def _pairing_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_variant: dict[str, set[str]] = defaultdict(set)
    duplicates = []
    for row in rows:
        variant = str(row["variant"])
        run_key = str(row["run_key"])
        if run_key in by_variant[variant]:
            duplicates.append({"variant": variant, "run_key": run_key})
        by_variant[variant].add(run_key)

    variants = list(by_variant)
    common = set.intersection(*(by_variant[variant] for variant in variants))
    union = set.union(*(by_variant[variant] for variant in variants))
    return {
        "variant_run_counts": {
            variant: len(run_keys) for variant, run_keys in by_variant.items()
        },
        "common_run_count": len(common),
        "union_run_count": len(union),
        "missing_run_keys": {
            variant: sorted(union - run_keys)
            for variant, run_keys in by_variant.items()
        },
        "duplicate_run_keys": duplicates,
        "strictly_paired": (
            not duplicates
            and bool(variants)
            and all(run_keys == common for run_keys in by_variant.values())
        ),
    }


def require_strict_pairing(pairing_audit: dict[str, Any]) -> None:
    if pairing_audit.get("strictly_paired"):
        return
    raise ValueError(
        "Formal comparison requires identical run keys for every variant and "
        "no duplicates. Pairing audit: "
        + json.dumps(pairing_audit, sort_keys=True)
    )


def _stratum_value(row: dict[str, Any], fields: tuple[str, ...]) -> str:
    return "|".join(f"{field}={row.get(field)}" for field in fields)


def _stratified_statistics(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dimensions = (
        ("route_name",),
        ("max_npcs",),
        ("traffic_lights",),
        ("scenario_bucket",),
        ("route_name", "max_npcs", "traffic_lights"),
    )
    aggregates = []
    pairwise = []
    for fields in dimensions:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        source_rows = (
            _expand_scenario_bucket_rows(rows)
            if fields == ("scenario_bucket",)
            else rows
        )
        for row in source_rows:
            grouped[_stratum_value(row, fields)].append(row)
        for value, group in sorted(grouped.items()):
            for entry in _aggregate_rows(
                group,
                seed_prefix=f"stratified|{','.join(fields)}|{value}",
            ):
                aggregates.append(
                    {
                        "group_by": list(fields),
                        "group_value": value,
                        **entry,
                    }
                )
            for entry in _all_pairwise_deltas(group):
                pairwise.append(
                    {
                        "group_by": list(fields),
                        "group_value": value,
                        **entry,
                    }
                )
    return aggregates, pairwise


def _load_scenario_bucket_manifest(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"run_keys": {}, "routes": {}, "filters": [], "default_buckets": []}
    raw = _read_json(path)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    manifest = {
        "run_keys": raw.get("run_keys", {}),
        "routes": raw.get("routes", {}),
        "filters": raw.get("filters", []),
        "default_buckets": raw.get("default_buckets", []),
    }
    if not isinstance(manifest["run_keys"], dict):
        raise ValueError("scenario bucket manifest run_keys must be an object.")
    if not isinstance(manifest["routes"], dict):
        raise ValueError("scenario bucket manifest routes must be an object.")
    if not isinstance(manifest["filters"], list):
        raise ValueError("scenario bucket manifest filters must be a list.")
    if not isinstance(manifest["default_buckets"], list):
        raise ValueError("scenario bucket manifest default_buckets must be a list.")
    for source in ("run_keys", "routes"):
        for key, buckets in manifest[source].items():
            if not isinstance(key, str) or not isinstance(buckets, list):
                raise ValueError(
                    f"scenario bucket manifest {source} entries must map "
                    "strings to lists."
                )
            _validate_scenario_buckets(buckets)
    for index, entry in enumerate(manifest["filters"]):
        _validate_scenario_bucket_filter(entry, index)
    _validate_scenario_buckets(manifest["default_buckets"])
    return manifest


def _validate_scenario_buckets(buckets: list[Any]) -> None:
    invalid = [
        bucket
        for bucket in buckets
        if not isinstance(bucket, str) or bucket not in SUPPORTED_SCENARIO_BUCKETS
    ]
    if invalid:
        raise ValueError(
            "Unsupported scenario bucket(s): "
            f"{invalid}. Supported buckets: {sorted(SUPPORTED_SCENARIO_BUCKETS)}."
        )


def _validate_scenario_bucket_filter(entry: Any, index: int) -> None:
    if not isinstance(entry, dict):
        raise ValueError(f"scenario bucket filter {index} must be an object.")
    name = entry.get("name", f"filter_{index}")
    if not isinstance(name, str) or not name:
        raise ValueError(f"scenario bucket filter {index} name must be a string.")
    match = entry.get("match")
    buckets = entry.get("buckets")
    if not isinstance(match, dict) or not match:
        raise ValueError(f"scenario bucket filter {name!r} match must be an object.")
    if not isinstance(buckets, list):
        raise ValueError(f"scenario bucket filter {name!r} buckets must be a list.")
    invalid_fields = sorted(set(match) - SCENARIO_BUCKET_FILTER_FIELDS)
    if invalid_fields:
        raise ValueError(
            f"scenario bucket filter {name!r} uses unsupported match field(s): "
            f"{invalid_fields}. Supported fields: "
            f"{sorted(SCENARIO_BUCKET_FILTER_FIELDS)}."
        )
    for field, value in match.items():
        if isinstance(value, dict):
            raise ValueError(
                f"scenario bucket filter {name!r} field {field!r} must be a "
                "scalar or list of scalars."
            )
        values = value if isinstance(value, list) else [value]
        if not values:
            raise ValueError(
                f"scenario bucket filter {name!r} field {field!r} has no values."
            )
        if any(isinstance(item, dict) or isinstance(item, list) for item in values):
            raise ValueError(
                f"scenario bucket filter {name!r} field {field!r} must contain "
                "only scalar values."
            )
    _validate_scenario_buckets(buckets)


def _scenario_buckets(
    row: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    buckets = ["overall"]
    run_key = str(row.get("run_key"))
    route_name = row.get("route_name")
    route_stem = _scenario_filter_value(row, "route_stem")
    manifest_run_keys = manifest.get("run_keys", {})
    manifest_routes = manifest.get("routes", {})
    for bucket in manifest_run_keys.get(run_key, []):
        if bucket not in buckets:
            buckets.append(bucket)
    route_labels = []
    for route_label in (route_name, route_stem):
        if route_label is not None and route_label not in route_labels:
            route_labels.append(route_label)
    for route_label in route_labels:
        for bucket in manifest_routes.get(str(route_label), []):
            if bucket not in buckets:
                buckets.append(bucket)
    for entry in manifest.get("filters", []):
        if _scenario_bucket_filter_matches(row, entry):
            for bucket in entry.get("buckets", []):
                if bucket not in buckets:
                    buckets.append(bucket)
    if len(buckets) == 1:
        for bucket in manifest.get("default_buckets", []):
            if bucket not in buckets:
                buckets.append(bucket)
    return buckets


def _scenario_bucket_filter_matches(
    row: dict[str, Any],
    entry: dict[str, Any],
) -> bool:
    match = entry.get("match", {})
    return all(
        _scenario_value_matches(_scenario_filter_value(row, field), expected)
        for field, expected in match.items()
    )


def _scenario_filter_value(row: dict[str, Any], field: str) -> Any:
    if field == "route_stem":
        route = row.get("route")
        if route is not None:
            return Path(str(route)).stem
        route_name = row.get("route_name")
        return None if route_name is None else str(route_name)
    if field not in SCENARIO_BUCKET_FILTER_FIELDS:
        raise ValueError(f"Unsupported scenario bucket filter field: {field}")
    return row.get(field)


def _scenario_value_matches(actual: Any, expected: Any) -> bool:
    values = expected if isinstance(expected, list) else [expected]
    return any(_scenario_scalar_matches(actual, value) for value in values)


def _scenario_scalar_matches(actual: Any, expected: Any) -> bool:
    if isinstance(actual, bool) or isinstance(expected, bool):
        return (
            isinstance(actual, bool)
            and isinstance(expected, bool)
            and actual is expected
        )
    if actual is None or expected is None:
        return actual is expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return abs(float(actual) - float(expected)) <= 1e-9
    return str(actual) == str(expected)


def _expand_scenario_bucket_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded = []
    for row in rows:
        buckets = row.get("scenario_buckets")
        if not isinstance(buckets, list) or not buckets:
            buckets = ["overall"]
        for bucket in buckets:
            expanded_row = dict(row)
            expanded_row["scenario_bucket"] = bucket
            expanded.append(expanded_row)
    return expanded


def _contract_verified_for_row(row: dict[str, Any]) -> bool:
    value = row.get("finite_candidate_contract_verified")
    return bool(value)


def _uses_formal_seed(row: dict[str, Any]) -> bool:
    seed = row.get("seed")
    if isinstance(seed, bool) or seed is None:
        return False
    try:
        return int(seed) in FORMAL_SEEDS
    except (TypeError, ValueError):
        return False


def _stat_passes_nonworse(stat: Any) -> bool:
    if not isinstance(stat, dict):
        return False
    mean = stat.get("mean")
    high = stat.get("ci95_high")
    return (
        mean is not None
        and high is not None
        and float(mean) <= 0.0
        and float(high) <= 0.0
    )


def _safety_gate_assessments(
    rows: list[dict[str, Any]],
    paired_deltas: list[dict[str, Any]],
    aggregates: list[dict[str, Any]],
    *,
    baseline: str,
) -> list[dict[str, Any]]:
    by_variant: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_variant[str(row["variant"])][str(row["run_key"])] = row
    aggregate_by_variant = {
        str(aggregate["variant"]): aggregate for aggregate in aggregates
    }
    baseline_rows = by_variant.get(baseline, {})
    assessments = []
    for delta in paired_deltas:
        variant = str(delta["variant"])
        variant_rows = by_variant.get(variant, {})
        common_keys = sorted(set(baseline_rows) & set(variant_rows))
        checks: dict[str, Any] = {}
        for metric in SAFETY_COST_V1_NO_WORSE_METRICS:
            checks[f"{metric}_nonworse"] = {
                "passed": _stat_passes_nonworse(delta.get(metric)),
                "delta": delta.get(metric),
            }
        completion_delta = delta.get("route_completion_rate")
        checks["completion_not_significantly_lower"] = {
            "passed": (
                isinstance(completion_delta, dict)
                and completion_delta.get("ci95_low") is not None
                and float(completion_delta["ci95_low"])
                >= -SAFETY_COST_V1_COMPLETION_TOLERANCE
            ),
            "delta": completion_delta,
            "tolerance": SAFETY_COST_V1_COMPLETION_TOLERANCE,
        }
        safety_delta = delta.get("safety_cost_v1")
        checks["safety_cost_significantly_lower"] = {
            "passed": (
                isinstance(safety_delta, dict)
                and safety_delta.get("ci95_high") is not None
                and float(safety_delta["ci95_high"]) < 0.0
            ),
            "delta": safety_delta,
        }
        latency = aggregate_by_variant.get(variant, {}).get(
            "p95_selection_latency_ms"
        )
        checks["latency_budget_with_margin"] = {
            "passed": (
                isinstance(latency, dict)
                and latency.get("ci95_high") is not None
                and float(latency["ci95_high"])
                <= SAFETY_COST_V1_LATENCY_BUDGET_MS
                - SAFETY_COST_V1_LATENCY_MARGIN_MS
            ),
            "aggregate": latency,
            "budget_ms": SAFETY_COST_V1_LATENCY_BUDGET_MS,
            "margin_ms": SAFETY_COST_V1_LATENCY_MARGIN_MS,
        }
        contract_rows = [variant_rows[key] for key in common_keys]
        checks["finite_candidate_contract_verified"] = {
            "passed": bool(contract_rows)
            and all(_contract_verified_for_row(row) for row in contract_rows),
            "verified_rows": sum(
                int(_contract_verified_for_row(row)) for row in contract_rows
            ),
            "required_rows": len(contract_rows),
        }
        formal_seed_rows = [
            row
            for key in common_keys
            for row in (baseline_rows[key], variant_rows[key])
            if _uses_formal_seed(row)
        ]
        checks["formal_seeds_absent"] = {
            "passed": not formal_seed_rows,
            "formal_seed_rows": [
                {"variant": row["variant"], "run_key": row["run_key"]}
                for row in formal_seed_rows
            ],
        }
        hard_gate_keys = [
            f"{metric}_nonworse" for metric in SAFETY_COST_V1_NO_WORSE_METRICS
        ] + [
            "completion_not_significantly_lower",
            "latency_budget_with_margin",
            "finite_candidate_contract_verified",
            "formal_seeds_absent",
        ]
        hard_gate_passed = all(checks[key]["passed"] for key in hard_gate_keys)
        assessment = {
            "baseline": baseline,
            "variant": variant,
            "n_pairs": len(common_keys),
            "hard_gate_passed": hard_gate_passed,
            "safety_cost_claim_passed": (
                hard_gate_passed
                and checks["safety_cost_significantly_lower"]["passed"]
            ),
            "checks": checks,
            "claim_rule": (
                "CAMP is better than DP Top-1 only if the hard gate passes "
                "and paired SafetyCost v1 has ci95_high < 0."
            ),
        }
        assessments.append(assessment)
    return assessments


def _parse_variant(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            "variant must have the form NAME=/path/to/replay_output"
        )
    name, path = value.split("=", 1)
    name = name.strip()
    if not name:
        raise argparse.ArgumentTypeError("variant name must not be empty")
    return name, Path(path)


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    headers = ("variant", "run_key") + SUMMARY_KEYS
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        values = []
        for key in headers:
            value = row.get(key)
            if isinstance(value, float):
                values.append(f"{value:.6g}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def _aggregate_markdown_table(rows: list[dict[str, Any]]) -> str:
    headers = ("variant", "n_runs") + SUMMARY_KEYS
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        values = []
        for key in headers:
            value = row.get(key)
            if isinstance(value, dict):
                mean = value.get("mean")
                if mean is None:
                    values.append("None")
                else:
                    low = value.get("ci95_low")
                    high = value.get("ci95_high")
                    values.append(f"{mean:.6g} [{low:.3g}, {high:.3g}]")
            elif isinstance(value, float):
                values.append(f"{value:.6g}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def _paired_markdown_table(rows: list[dict[str, Any]]) -> str:
    headers = ("baseline", "variant", "n_pairs") + PAPER_METRICS
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        values = []
        for key in headers:
            value = row.get(key)
            if isinstance(value, dict):
                mean = value.get("mean")
                low = value.get("ci95_low")
                high = value.get("ci95_high")
                values.append(
                    "None"
                    if mean is None
                    else f"{mean:.6g} [{low:.3g}, {high:.3g}]"
                )
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def _safety_gate_markdown_table(rows: list[dict[str, Any]]) -> str:
    headers = (
        "baseline",
        "variant",
        "n_pairs",
        "hard_gate_passed",
        "safety_cost_claim_passed",
        "safety_cost_delta",
        "latency_gate",
        "contract_gate",
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        checks = row.get("checks", {})
        safety_delta = checks.get("safety_cost_significantly_lower", {}).get("delta")
        if isinstance(safety_delta, dict) and safety_delta.get("mean") is not None:
            safety_value = (
                f"{safety_delta['mean']:.6g} "
                f"[{safety_delta['ci95_low']:.3g}, "
                f"{safety_delta['ci95_high']:.3g}]"
            )
        else:
            safety_value = "None"
        values = [
            str(row.get("baseline")),
            str(row.get("variant")),
            str(row.get("n_pairs")),
            str(row.get("hard_gate_passed")),
            str(row.get("safety_cost_claim_passed")),
            safety_value,
            str(
                checks.get("latency_budget_with_margin", {}).get(
                    "passed",
                    False,
                )
            ),
            str(
                checks.get("finite_candidate_contract_verified", {}).get(
                    "passed",
                    False,
                )
            ),
        ]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare multiple DP+CAMP replay summaries under matched settings."
    )
    parser.add_argument(
        "--variant",
        action="append",
        type=_parse_variant,
        required=True,
        help="NAME=/path/to/replay_output. Repeat for each comparable variant.",
    )
    parser.add_argument(
        "--baseline",
        type=str,
        default=None,
        help="Variant name used for paired deltas. Defaults to the first variant.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_markdown", type=Path, default=None)
    parser.add_argument(
        "--scenario_bucket_manifest",
        type=Path,
        default=None,
        help=(
            "Optional JSON with run_keys/routes/default_buckets lists. Buckets "
            "are explicit only; no route is auto-labeled as critical."
        ),
    )
    parser.add_argument(
        "--require_strict_pairing",
        action="store_true",
        help="Fail instead of writing a comparison with missing or duplicate pairs.",
    )
    args = parser.parse_args()

    scenario_bucket_manifest = _load_scenario_bucket_manifest(
        args.scenario_bucket_manifest
    )
    rows = []
    for name, output_dir in args.variant:
        summary = _load_or_build_summary(output_dir)
        benchmark = summary.get("benchmark")
        benchmark = benchmark if isinstance(benchmark, dict) else {}
        route = benchmark.get("route")
        contract = summary.get("dp_camp_finite_candidate_contract")
        contract_verified = (
            isinstance(contract, dict)
            and contract.get("schema_version")
            == "dp_camp_finite_candidate_contract_v1"
            and contract.get("classical_benders_claim") is False
        )
        row = {
            "variant": name,
            "run_key": _run_key(summary, output_dir),
            "output_dir": str(output_dir),
            "route_name": Path(str(route)).stem if route is not None else None,
            "finite_candidate_contract_verified": contract_verified,
        }
        for key in BENCHMARK_KEYS:
            row[key] = benchmark.get(key)
        for key in SUMMARY_KEYS:
            row[key] = summary.get(key)
        _apply_safety_cost_v1(row)
        row["scenario_buckets"] = _scenario_buckets(row, scenario_bucket_manifest)
        rows.append(row)

    baseline = args.baseline or rows[0]["variant"]
    aggregates = _aggregate_rows(rows)
    paired_deltas = _paired_deltas(rows, baseline=baseline)
    all_pairwise_deltas = _all_pairwise_deltas(rows)
    safety_gate_assessments = _safety_gate_assessments(
        rows,
        paired_deltas,
        aggregates,
        baseline=baseline,
    )
    stratified_aggregates, stratified_pairwise_deltas = _stratified_statistics(
        rows
    )
    pairing_audit = _pairing_audit(rows)
    if args.require_strict_pairing:
        require_strict_pairing(pairing_audit)
    result = {
        "comparison_type": "diffusion_planner_camp_replay_variants",
        "runs": rows,
        "aggregates": aggregates,
        "paired_deltas": paired_deltas,
        "all_pairwise_deltas": all_pairwise_deltas,
        "safety_cost_v1": {
            "weights": SAFETY_COST_V1_WEIGHTS,
            "normalization": SAFETY_COST_V1_NORMALIZATION,
            "clip": SAFETY_COST_V1_CLIP,
            "tail_alpha": SAFETY_COST_V1_ALPHA,
            "lower_is_better": True,
            "hard_gate": {
                "no_worse_metrics": list(SAFETY_COST_V1_NO_WORSE_METRICS),
                "completion_tolerance": SAFETY_COST_V1_COMPLETION_TOLERANCE,
                "latency_budget_ms": SAFETY_COST_V1_LATENCY_BUDGET_MS,
                "latency_margin_ms": SAFETY_COST_V1_LATENCY_MARGIN_MS,
                "formal_seeds": sorted(FORMAL_SEEDS),
                "requires_finite_candidate_contract": True,
            },
        },
        "safety_gate_assessments": safety_gate_assessments,
        "stratified_aggregates": stratified_aggregates,
        "stratified_pairwise_deltas": stratified_pairwise_deltas,
        "pairing_audit": pairing_audit,
        "baseline": baseline,
        "ci_method": "deterministic bootstrap percentile",
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "caveat": (
            "Rows are comparable only when route, map, seed, NPC settings, "
            "steps, DP checkpoint, candidate count, and spawn config match."
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if args.output_markdown is not None:
        args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.output_markdown.write_text(
            "## Runs\n\n"
            + _markdown_table(rows)
            + "\n## Aggregates\n\n"
            + _aggregate_markdown_table(aggregates)
            + "\n## All Pairwise Deltas (variant - baseline)\n\n"
            + _paired_markdown_table(all_pairwise_deltas)
            + "\n## SafetyCost v1 Hard Gate\n\n"
            + _safety_gate_markdown_table(safety_gate_assessments)
            + "\n## Pairing Audit\n\n"
            + "```json\n"
            + json.dumps(pairing_audit, indent=2)
            + "\n```\n",
            encoding="utf-8",
        )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
