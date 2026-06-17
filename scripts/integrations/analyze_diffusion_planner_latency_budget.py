#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)


TOTAL_FIELD = "latency_ms_including_candidate_generation"

CRITICAL_PATH_FIELDS = (
    "latency_ms_candidate_generation",
    "latency_ms_shadow_dp_prior_deviation",
    "latency_ms_shadow_dp_prior_comfort_excess",
    "latency_ms_shadow_lateral_comfort",
    "latency_ms_context_and_obstacles",
    "latency_ms_shadow_obstacle_clearance",
    "latency_ms_shadow_perfect_tracker_command",
    "latency_ms_shadow_perfect_tracker_open_loop",
    "latency_ms_reward_scoring",
    "latency_ms_outcome_collection",
    "latency_ms_red_stopping_margin_atom",
    "latency_ms_camp_selection",
    "latency_ms_underprogress_relaxation",
    "latency_ms_splice_shadow_rule",
    "latency_ms_traffic_light_hybrid_postselection",
    "latency_ms_perfect_tracker_command_postselection",
)

NESTED_FIELDS = (
    "latency_ms_shadow_full_horizon_red_light",
    "latency_ms_camp_atom_computation",
    "latency_ms_camp_feasibility",
    "latency_ms_camp_collision_checks",
    "latency_ms_camp_scoring",
)

REWARD_BREAKDOWN_FIELDS = (
    "latency_ms_reward_npz_dump",
    "latency_ms_reward_tensor_setup",
    "latency_ms_reward_sg_smoothing",
    "latency_ms_reward_candidate_tensor_transfer",
    "latency_ms_reward_batch_compute",
    "latency_ms_reward_postprocess",
    "latency_ms_reward_full_horizon_red_light",
    "latency_ms_reward_red_route_points",
    "latency_ms_reward_feasibility",
    "latency_ms_reward_field_extraction",
    "latency_ms_reward_step_reach_guard",
    "latency_ms_reward_route_progress",
    "latency_ms_reward_route_progress_guard",
    "latency_ms_reward_lexicographic_filter",
)

REMOVAL_FIELDS = (
    "latency_ms_candidate_generation",
    "latency_ms_reward_scoring",
    "latency_ms_camp_selection",
    "latency_ms_shadow_obstacle_clearance",
    "latency_ms_shadow_perfect_tracker_open_loop",
    "latency_ms_shadow_perfect_tracker_command",
    "latency_ms_shadow_lateral_comfort",
    "latency_ms_context_and_obstacles",
    "latency_ms_red_stopping_margin_atom",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only latency budget attribution for DP-CAMP selection logs. "
            "This does not select trajectories or read closed-loop outcome labels."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--tail_percentile", type=float, default=95.0)
    parser.add_argument("--max_examples", type=int, default=10)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        [*args.root, *args.selection_log],
        label=args.label,
        tail_percentile=args.tail_percentile,
        max_examples=args.max_examples,
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
    label: str | None = None,
    tail_percentile: float = 95.0,
    max_examples: int = 10,
) -> dict[str, Any]:
    if tail_percentile <= 0.0 or tail_percentile >= 100.0:
        raise ValueError("tail_percentile must be in (0, 100).")
    if max_examples < 0:
        raise ValueError("max_examples must be nonnegative.")

    rows = _load_rows(paths)
    if not rows:
        raise ValueError("No selection records were found.")

    total_values = _values(rows, TOTAL_FIELD)
    if not total_values:
        raise ValueError(f"No finite {TOTAL_FIELD} values were found.")
    total_p95 = _percentile(total_values, 95.0)
    tail_threshold = _percentile(total_values, tail_percentile)
    tail_rows = [
        row
        for row in rows
        if _finite(row["latencies"].get(TOTAL_FIELD)) is not None
        and float(row["latencies"][TOTAL_FIELD]) >= tail_threshold
    ]

    report = {
        "analysis": {
            "name": "dp_camp_latency_budget_attribution_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_outcome_labels_used": False,
            "total_latency_field": TOTAL_FIELD,
            "tail_percentile": float(tail_percentile),
            "tail_threshold_ms": float(tail_threshold),
            "math_boundary": (
                "Latency attribution is a read-only engineering diagnostic. "
                "It does not define atoms, constraints, Benders subproblems, "
                "cuts, or selector inputs."
            ),
        },
        "records": {
            "logs": len({row["log_path"] for row in rows}),
            "total": len(rows),
            "tail": len(tail_rows),
        },
        "overall_latency_ms": {
            field: _summary(_values(rows, field))
            for field in (
                TOTAL_FIELD,
                *CRITICAL_PATH_FIELDS,
                *NESTED_FIELDS,
                *REWARD_BREAKDOWN_FIELDS,
            )
        },
        "tail_mean_latency_ms": _field_means(tail_rows),
        "derived_latency_ms": _derived_latency(rows),
        "removal_sensitivity": _removal_sensitivity(rows, total_p95),
        "top_total_latency_records": _examples(rows, max_examples),
    }
    return report


def _load_rows(paths: list[Path]) -> list[dict[str, Any]]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    rows: list[dict[str, Any]] = []
    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list):
            raise ValueError(f"{log_path} must contain a JSON list.")
        for record_index, record in enumerate(payload):
            if not isinstance(record, dict):
                continue
            latencies = {
                field: _finite(record.get(field))
                for field in (
                    TOTAL_FIELD,
                    *CRITICAL_PATH_FIELDS,
                    *NESTED_FIELDS,
                    *REWARD_BREAKDOWN_FIELDS,
                )
            }
            rows.append(
                {
                    "log_path": str(log_path),
                    "record_index": int(record_index),
                    "selection_step": record.get("selection_step", record_index),
                    "selected_index": record.get("selected_index"),
                    "used_fallback": bool(record.get("used_fallback", False)),
                    "latencies": latencies,
                }
            )
    return rows


def _values(rows: list[dict[str, Any]], field: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = _finite(row["latencies"].get(field))
        if value is not None:
            values.append(value)
    return values


def _derived_latency(rows: list[dict[str, Any]]) -> dict[str, Any]:
    non_candidate: list[float] = []
    residual: list[float] = []
    critical_sum_values: list[float] = []
    reward_breakdown_sum_values: list[float] = []
    reward_breakdown_residual: list[float] = []
    for row in rows:
        total = _finite(row["latencies"].get(TOTAL_FIELD))
        if total is None:
            continue
        candidate_generation = _finite(
            row["latencies"].get("latency_ms_candidate_generation")
        )
        if candidate_generation is not None:
            non_candidate.append(max(total - candidate_generation, 0.0))
        critical_sum = sum(
            _finite(row["latencies"].get(field)) or 0.0
            for field in CRITICAL_PATH_FIELDS
        )
        critical_sum_values.append(critical_sum)
        residual.append(total - critical_sum)
        reward_total = _finite(row["latencies"].get("latency_ms_reward_scoring"))
        reward_components = [
            _finite(row["latencies"].get(field))
            for field in REWARD_BREAKDOWN_FIELDS
        ]
        finite_reward_components = [
            float(value) for value in reward_components if value is not None
        ]
        if reward_total is not None and finite_reward_components:
            reward_sum = sum(finite_reward_components)
            reward_breakdown_sum_values.append(reward_sum)
            reward_breakdown_residual.append(float(reward_total) - reward_sum)
    return {
        "non_candidate_generation": _summary(non_candidate),
        "critical_path_sum": _summary(critical_sum_values),
        "uninstrumented_residual": _summary(residual),
        "reward_breakdown_sum": _summary(reward_breakdown_sum_values),
        "reward_unattributed_residual": _summary(reward_breakdown_residual),
    }


def _field_means(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in (
        TOTAL_FIELD,
        *CRITICAL_PATH_FIELDS,
        *NESTED_FIELDS,
        *REWARD_BREAKDOWN_FIELDS,
    ):
        values = _values(rows, field)
        result[field] = {
            "n": len(values),
            "mean": float(np.mean(values)) if values else None,
        }
    return result


def _removal_sensitivity(
    rows: list[dict[str, Any]],
    baseline_p95: float,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in REMOVAL_FIELDS:
        adjusted: list[float] = []
        component_values: list[float] = []
        for row in rows:
            total = _finite(row["latencies"].get(TOTAL_FIELD))
            component = _finite(row["latencies"].get(field))
            if total is None or component is None:
                continue
            adjusted.append(max(total - component, 0.0))
            component_values.append(component)
        adjusted_summary = _summary(adjusted)
        adjusted_p95 = adjusted_summary["p95"]
        result[field] = {
            "records": len(adjusted),
            "component": _summary(component_values),
            "p95_if_removed_ms": adjusted_p95,
            "p95_reduction_ms": (
                float(baseline_p95 - adjusted_p95)
                if adjusted_p95 is not None
                else None
            ),
        }
    return result


def _examples(rows: list[dict[str, Any]], max_examples: int) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        rows,
        key=lambda row: _finite(row["latencies"].get(TOTAL_FIELD)) or -np.inf,
        reverse=True,
    )
    examples: list[dict[str, Any]] = []
    for row in sorted_rows[:max_examples]:
        latencies = {
            field: row["latencies"].get(field)
            for field in (
                TOTAL_FIELD,
                *CRITICAL_PATH_FIELDS,
                *NESTED_FIELDS,
                *REWARD_BREAKDOWN_FIELDS,
            )
            if row["latencies"].get(field) is not None
        }
        examples.append(
            {
                "log_path": row["log_path"],
                "record_index": row["record_index"],
                "selection_step": row["selection_step"],
                "selected_index": row["selected_index"],
                "used_fallback": row["used_fallback"],
                "latencies": latencies,
            }
        )
    return examples


def _summary(values: list[float]) -> dict[str, Any]:
    finite_values = [float(value) for value in values if _finite(value) is not None]
    if not finite_values:
        return {"n": 0, "mean": None, "p50": None, "p95": None, "min": None, "max": None}
    arr = np.asarray(finite_values, dtype=np.float64)
    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "p50": float(np.percentile(arr, 50.0)),
        "p95": float(np.percentile(arr, 95.0)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def _percentile(values: list[float], percentile: float) -> float:
    arr = np.asarray(values, dtype=np.float64)
    return float(np.percentile(arr, percentile))


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not np.isfinite(result):
        return None
    return result


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP-CAMP Latency Budget Attribution",
        "",
        f"Label: `{report['analysis'].get('label')}`",
        "",
        "## Records",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in report["records"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Overall Latency",
            "",
            "| Field | Mean | P50 | P95 | Max | N |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for field, summary in report["overall_latency_ms"].items():
        if summary["n"] == 0:
            continue
        lines.append(_summary_row(field, summary))
    lines.extend(
        [
            "",
            "## Derived Latency",
            "",
            "| Field | Mean | P50 | P95 | Max | N |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for field, summary in report["derived_latency_ms"].items():
        lines.append(_summary_row(field, summary))
    lines.extend(
        [
            "",
            "## Removal Sensitivity",
            "",
            "| Component | Component P95 | Total P95 If Removed | P95 Reduction | Records |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for field, row in report["removal_sensitivity"].items():
        component_p95 = row["component"]["p95"]
        removed_p95 = row["p95_if_removed_ms"]
        reduction = row["p95_reduction_ms"]
        lines.append(
            "| "
            f"`{field}` | {_fmt(component_p95)} | {_fmt(removed_p95)} | "
            f"{_fmt(reduction)} | {row['records']} |"
        )
    lines.extend(
        [
            "",
            "## Top Total-Latency Records",
            "",
            "| Log | Step | Total | Candidate Gen | Reward | CAMP | Clearance |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["top_total_latency_records"]:
        latencies = row["latencies"]
        lines.append(
            "| "
            f"`{row['log_path']}` | {row['selection_step']} | "
            f"{_fmt(latencies.get(TOTAL_FIELD))} | "
            f"{_fmt(latencies.get('latency_ms_candidate_generation'))} | "
            f"{_fmt(latencies.get('latency_ms_reward_scoring'))} | "
            f"{_fmt(latencies.get('latency_ms_camp_selection'))} | "
            f"{_fmt(latencies.get('latency_ms_shadow_obstacle_clearance'))} |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
        ]
    )
    return "\n".join(lines) + "\n"


def _summary_row(field: str, summary: dict[str, Any]) -> str:
    return (
        f"| `{field}` | {_fmt(summary['mean'])} | {_fmt(summary['p50'])} | "
        f"{_fmt(summary['p95'])} | {_fmt(summary['max'])} | {summary['n']} |"
    )


def _fmt(value: Any) -> str:
    if value is None:
        return "`null`"
    return f"`{float(value):.6f}`"


if __name__ == "__main__":
    main()
