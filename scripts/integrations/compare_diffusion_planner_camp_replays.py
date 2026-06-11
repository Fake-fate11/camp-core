#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


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
    "distance_traveled_m",
    "obb_collision_rate",
    "near_miss_rate",
    "lane_violation_rate",
    "red_light_violation_rate",
    "fallback_rate",
    "candidate_feasible_rate",
    "p95_selection_latency_ms",
    "n_npc_spawned",
)


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
    summary = summarize_replay_artifacts(
        output_dir,
        selection_records=records,
        replay_result=replay_summary.get("replay_result"),
    )
    summary["selector_mode"] = replay_summary.get("selector_mode")
    summary["num_candidates"] = replay_summary.get("num_candidates")
    summary["candidate_noise_scale"] = replay_summary.get("candidate_noise_scale")
    if "benchmark" in replay_summary:
        summary["benchmark"] = replay_summary["benchmark"]
    return summary


def _run_key(summary: dict[str, Any], output_dir: Path) -> str:
    explicit = summary.get("benchmark_key")
    if explicit:
        return str(explicit)
    benchmark = summary.get("benchmark")
    if isinstance(benchmark, dict):
        fields = [
            benchmark.get("route"),
            benchmark.get("seed"),
            benchmark.get("steps"),
            benchmark.get("max_npcs"),
            benchmark.get("spawn_probability"),
        ]
        if any(field is not None for field in fields):
            return "|".join(str(field) for field in fields)
    return str(output_dir)


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _mean_ci(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "mean": None, "std": None, "ci95": None}
    if len(values) == 1:
        return {"n": 1, "mean": values[0], "std": 0.0, "ci95": 0.0}
    import math

    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    std = math.sqrt(variance)
    ci95 = 1.96 * std / math.sqrt(len(values))
    return {"n": len(values), "mean": mean, "std": std, "ci95": ci95}


def _aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
                aggregate[key] = _mean_ci(values)
        aggregates.append(aggregate)
    return aggregates


def _paired_deltas(
    rows: list[dict[str, Any]],
    *,
    baseline: str,
) -> list[dict[str, Any]]:
    by_variant: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_variant[str(row["variant"])][str(row["run_key"])] = row
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
                entry[key] = _mean_ci(values)
        deltas.append(entry)
    return deltas


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
                ci95 = value.get("ci95")
                if mean is None:
                    values.append("None")
                else:
                    values.append(f"{mean:.6g} +/- {ci95:.3g}")
            elif isinstance(value, float):
                values.append(f"{value:.6g}")
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
    args = parser.parse_args()

    rows = []
    for name, output_dir in args.variant:
        summary = _load_or_build_summary(output_dir)
        row = {
            "variant": name,
            "run_key": _run_key(summary, output_dir),
            "output_dir": str(output_dir),
        }
        for key in SUMMARY_KEYS:
            row[key] = summary.get(key)
        rows.append(row)

    baseline = args.baseline or rows[0]["variant"]
    aggregates = _aggregate_rows(rows)
    paired_deltas = _paired_deltas(rows, baseline=baseline)
    result = {
        "comparison_type": "diffusion_planner_camp_replay_variants",
        "runs": rows,
        "aggregates": aggregates,
        "paired_deltas": paired_deltas,
        "baseline": baseline,
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
            + _aggregate_markdown_table(aggregates),
            encoding="utf-8",
        )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
