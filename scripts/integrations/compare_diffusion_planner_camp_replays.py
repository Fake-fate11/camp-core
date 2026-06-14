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
            for run_key in common_keys:
                lhs = _numeric(keyed_rows[run_key].get(key))
                rhs = _numeric(baseline_rows[run_key].get(key))
                if lhs is not None and rhs is not None:
                    values.append(lhs - rhs)
            if values:
                entry[key] = _mean_ci(
                    values,
                    seed_key=f"{seed_prefix}|{baseline}|{variant}|{key}",
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
        ("route_name", "max_npcs", "traffic_lights"),
    )
    aggregates = []
    pairwise = []
    for fields in dimensions:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
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
        "--require_strict_pairing",
        action="store_true",
        help="Fail instead of writing a comparison with missing or duplicate pairs.",
    )
    args = parser.parse_args()

    rows = []
    for name, output_dir in args.variant:
        summary = _load_or_build_summary(output_dir)
        benchmark = summary.get("benchmark")
        benchmark = benchmark if isinstance(benchmark, dict) else {}
        route = benchmark.get("route")
        row = {
            "variant": name,
            "run_key": _run_key(summary, output_dir),
            "output_dir": str(output_dir),
            "route_name": Path(str(route)).stem if route is not None else None,
        }
        for key in BENCHMARK_KEYS:
            row[key] = benchmark.get(key)
        for key in SUMMARY_KEYS:
            row[key] = summary.get(key)
        rows.append(row)

    baseline = args.baseline or rows[0]["variant"]
    aggregates = _aggregate_rows(rows)
    paired_deltas = _paired_deltas(rows, baseline=baseline)
    all_pairwise_deltas = _all_pairwise_deltas(rows)
    stratified_aggregates, stratified_pairwise_deltas = _stratified_statistics(rows)
    pairing_audit = _pairing_audit(rows)
    if args.require_strict_pairing:
        require_strict_pairing(pairing_audit)
    result = {
        "comparison_type": "diffusion_planner_camp_replay_variants",
        "runs": rows,
        "aggregates": aggregates,
        "paired_deltas": paired_deltas,
        "all_pairwise_deltas": all_pairwise_deltas,
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
            + "\n## Pairing Audit\n\n"
            + "```json\n"
            + json.dumps(pairing_audit, indent=2)
            + "\n```\n",
            encoding="utf-8",
        )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
