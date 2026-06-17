#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

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
CLEARANCE_FIELD = "latency_ms_shadow_obstacle_clearance"
PROJECTED_TOTAL_FIELD = "projected_latency_ms_including_candidate_generation"
PROJECTED_CLEARANCE_FIELD = "projected_latency_ms_shadow_obstacle_clearance"

PRIMARY_COMPONENT_FIELDS = (
    "latency_ms_candidate_generation",
    "latency_ms_shadow_dp_prior_deviation",
    "latency_ms_shadow_dp_prior_comfort_excess",
    "latency_ms_shadow_lateral_comfort",
    "latency_ms_context_and_obstacles",
    CLEARANCE_FIELD,
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

NESTED_COMPONENT_FIELDS = (
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

ANALYZED_FIELDS = (
    TOTAL_FIELD,
    PROJECTED_TOTAL_FIELD,
    CLEARANCE_FIELD,
    PROJECTED_CLEARANCE_FIELD,
    *PRIMARY_COMPONENT_FIELDS,
    *NESTED_COMPONENT_FIELDS,
    *REWARD_BREAKDOWN_FIELDS,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Attribute the remaining projected DP-CAMP latency tail after "
            "clearance vectorization. This is read-only and does not replay."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--budget_ms", type=float, default=100.0)
    parser.add_argument("--tail_percentile", type=float, default=95.0)
    parser.add_argument("--max_examples", type=int, default=10)
    parser.add_argument(
        "--reference_old_clearance_p95_ms",
        type=float,
        required=True,
        help="Old smoke-test clearance p95 used as the scale baseline.",
    )
    parser.add_argument(
        "--reference_new_clearance_p95_ms",
        type=float,
        required=True,
        help="New vectorized smoke-test clearance p95 used for projection.",
    )
    parser.add_argument(
        "--reference_source",
        default=None,
        help="Human-readable path/SHA note for the smoke artifact source.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        [*args.root, *args.selection_log],
        label=args.label,
        budget_ms=args.budget_ms,
        tail_percentile=args.tail_percentile,
        max_examples=args.max_examples,
        reference_old_clearance_p95_ms=args.reference_old_clearance_p95_ms,
        reference_new_clearance_p95_ms=args.reference_new_clearance_p95_ms,
        reference_source=args.reference_source,
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
    paths: Sequence[Path],
    *,
    label: str | None = None,
    budget_ms: float = 100.0,
    tail_percentile: float = 95.0,
    max_examples: int = 10,
    reference_old_clearance_p95_ms: float,
    reference_new_clearance_p95_ms: float,
    reference_source: str | None = None,
) -> dict[str, Any]:
    if budget_ms <= 0.0:
        raise ValueError("budget_ms must be positive.")
    if tail_percentile <= 0.0 or tail_percentile >= 100.0:
        raise ValueError("tail_percentile must be in (0, 100).")
    if max_examples < 0:
        raise ValueError("max_examples must be nonnegative.")
    if reference_old_clearance_p95_ms <= 0.0:
        raise ValueError("reference_old_clearance_p95_ms must be positive.")
    if reference_new_clearance_p95_ms < 0.0:
        raise ValueError("reference_new_clearance_p95_ms must be nonnegative.")

    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    roots = _directory_inputs(paths)
    rows = _load_rows(log_paths, roots)
    usable_rows = [
        row
        for row in rows
        if row["latencies"][TOTAL_FIELD] is not None
        and row["latencies"][CLEARANCE_FIELD] is not None
    ]
    if not usable_rows:
        raise ValueError(
            f"No records had finite {TOTAL_FIELD} and {CLEARANCE_FIELD} values."
        )

    scale_ratio = reference_new_clearance_p95_ms / reference_old_clearance_p95_ms
    modes: dict[str, Callable[[float], float]] = {
        "constant_new_p95": lambda old: reference_new_clearance_p95_ms,
        "cap_at_new_p95": lambda old: min(old, reference_new_clearance_p95_ms),
        "scale_by_smoke_p95_ratio": lambda old: old * scale_ratio,
    }
    return {
        "analysis": {
            "name": "dp_camp_projected_latency_tail_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_outcome_labels_used": False,
            "projection_not_replay_measurement": True,
            "selector_semantics_changed": False,
            "budget_ms": float(budget_ms),
            "tail_percentile": float(tail_percentile),
            "math_boundary": (
                "This is a read-only engineering attribution over existing "
                "current-tick latency logs. Latency components are not CAMP "
                "risk atoms, constraints, Benders subproblems, duals, or cuts."
            ),
        },
        "reference": {
            "source": reference_source,
            "old_clearance_p95_ms": float(reference_old_clearance_p95_ms),
            "new_clearance_p95_ms": float(reference_new_clearance_p95_ms),
            "scale_ratio": float(scale_ratio),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(rows),
            "usable": len(usable_rows),
            "missing_total_latency": sum(
                row["latencies"][TOTAL_FIELD] is None for row in rows
            ),
            "missing_clearance_latency": sum(
                row["latencies"][CLEARANCE_FIELD] is None for row in rows
            ),
        },
        "projection_modes": {
            name: _mode_report(
                usable_rows,
                budget_ms=budget_ms,
                tail_percentile=tail_percentile,
                max_examples=max_examples,
                replacement_fn=replacement_fn,
            )
            for name, replacement_fn in modes.items()
        },
    }


def _directory_inputs(paths: Sequence[Path]) -> list[Path]:
    roots = [Path(path).resolve() for path in paths if Path(path).is_dir()]
    return sorted(roots, key=lambda path: len(path.parts), reverse=True)


def _load_rows(
    log_paths: Sequence[Path],
    roots: Sequence[Path],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fields = tuple(dict.fromkeys((*PRIMARY_COMPONENT_FIELDS, *NESTED_COMPONENT_FIELDS, *REWARD_BREAKDOWN_FIELDS)))
    for log_path in log_paths:
        records = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(records, list):
            raise ValueError(f"{log_path} must contain a JSON list.")
        run_key = _run_key(log_path, roots)
        for record_index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            latencies = {
                TOTAL_FIELD: _finite(record.get(TOTAL_FIELD)),
                **{field: _finite(record.get(field)) for field in fields},
            }
            rows.append(
                {
                    "log_path": str(log_path),
                    "run_key": run_key,
                    "record_index": int(record_index),
                    "selection_step": record.get("selection_step", record_index),
                    "selected_index": record.get("selected_index"),
                    "used_fallback": bool(record.get("used_fallback", False)),
                    "latencies": latencies,
                }
            )
    return rows


def _mode_report(
    rows: Sequence[dict[str, Any]],
    *,
    budget_ms: float,
    tail_percentile: float,
    max_examples: int,
    replacement_fn: Callable[[float], float],
) -> dict[str, Any]:
    projected_rows = [_project_row(row, replacement_fn) for row in rows]
    run_summaries, tail_rows = _run_summaries(
        projected_rows,
        budget_ms=budget_ms,
        tail_percentile=tail_percentile,
    )
    over_budget_runs = [
        row for row in run_summaries if row["projected_over_budget"]
    ]
    return {
        "runs": len(run_summaries),
        "runs_over_budget": len(over_budget_runs),
        "tail_rows": len(tail_rows),
        "per_run_projected_total_p95_ms": _summary(
            [row["projected_total_p95_ms"] for row in run_summaries]
        ),
        "over_budget_run_shortfall_ms": _summary(
            [row["projected_p95_shortfall_ms"] for row in over_budget_runs]
        ),
        "tail_latency_ms": _component_summaries(tail_rows),
        "tail_primary_residual_ms": _summary(
            [_primary_residual(row) for row in tail_rows]
        ),
        "top_tail_primary_components_by_mean_ms": _top_components(
            tail_rows,
            fields=[
                field
                for field in PRIMARY_COMPONENT_FIELDS
                if field != CLEARANCE_FIELD
            ],
            max_examples=max_examples,
        ),
        "over_budget_runs": over_budget_runs[:max_examples],
        "top_tail_records": _top_tail_records(tail_rows, max_examples),
    }


def _project_row(
    row: dict[str, Any],
    replacement_fn: Callable[[float], float],
) -> dict[str, Any]:
    latencies = dict(row["latencies"])
    total = float(latencies[TOTAL_FIELD])
    old_clearance = float(latencies[CLEARANCE_FIELD])
    projected_clearance = float(replacement_fn(old_clearance))
    projected_total = max(total - old_clearance + projected_clearance, 0.0)
    latencies[PROJECTED_CLEARANCE_FIELD] = projected_clearance
    latencies[PROJECTED_TOTAL_FIELD] = projected_total
    return {**row, "latencies": latencies}


def _run_summaries(
    rows: Sequence[dict[str, Any]],
    *,
    budget_ms: float,
    tail_percentile: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["run_key"], []).append(row)
    summaries: list[dict[str, Any]] = []
    tail_rows: list[dict[str, Any]] = []
    for run_key, run_rows in grouped.items():
        baseline_values = [
            float(row["latencies"][TOTAL_FIELD]) for row in run_rows
        ]
        projected_values = [
            float(row["latencies"][PROJECTED_TOTAL_FIELD]) for row in run_rows
        ]
        baseline_p95 = _percentile(baseline_values, 95.0)
        projected_p95 = _percentile(projected_values, 95.0)
        projected_over_budget = projected_p95 > budget_ms
        row = {
            "run_key": run_key,
            "records": len(run_rows),
            "baseline_total_p95_ms": float(baseline_p95),
            "projected_total_p95_ms": float(projected_p95),
            "p95_delta_ms": float(projected_p95 - baseline_p95),
            "projected_p95_shortfall_ms": float(max(projected_p95 - budget_ms, 0.0)),
            "baseline_over_budget": bool(baseline_p95 > budget_ms),
            "projected_over_budget": bool(projected_over_budget),
        }
        if projected_over_budget:
            threshold = _percentile(projected_values, tail_percentile)
            run_tail_rows = [
                candidate
                for candidate in run_rows
                if float(candidate["latencies"][PROJECTED_TOTAL_FIELD]) >= threshold
            ]
            row["tail_threshold_ms"] = float(threshold)
            row["tail_rows"] = len(run_tail_rows)
            row["top_tail_primary_components_by_mean_ms"] = _top_components(
                run_tail_rows,
                fields=[
                    field
                    for field in PRIMARY_COMPONENT_FIELDS
                    if field != CLEARANCE_FIELD
                ],
                max_examples=5,
            )
            tail_rows.extend(run_tail_rows)
        summaries.append(row)
    summaries.sort(
        key=lambda row: (
            row["projected_total_p95_ms"],
            row["baseline_total_p95_ms"],
            row["run_key"],
        ),
        reverse=True,
    )
    return summaries, tail_rows


def _component_summaries(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        field: _summary(_field_values(rows, field))
        for field in ANALYZED_FIELDS
        if _field_values(rows, field)
    }


def _top_components(
    rows: Sequence[dict[str, Any]],
    *,
    fields: Sequence[str],
    max_examples: int,
) -> list[dict[str, Any]]:
    ranked = []
    for field in fields:
        summary = _summary(_field_values(rows, field))
        if summary["n"] == 0 or summary["mean"] is None:
            continue
        ranked.append({"field": field, **summary})
    ranked.sort(
        key=lambda row: (row["mean"], row["p95"] or 0.0, row["field"]),
        reverse=True,
    )
    return ranked[:max_examples]


def _top_tail_records(
    rows: Sequence[dict[str, Any]],
    max_examples: int,
) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        rows,
        key=lambda row: float(row["latencies"][PROJECTED_TOTAL_FIELD]),
        reverse=True,
    )
    examples = []
    fields = (
        TOTAL_FIELD,
        PROJECTED_TOTAL_FIELD,
        CLEARANCE_FIELD,
        PROJECTED_CLEARANCE_FIELD,
        "latency_ms_candidate_generation",
        "latency_ms_reward_scoring",
        "latency_ms_camp_selection",
        "latency_ms_context_and_obstacles",
        "latency_ms_shadow_perfect_tracker_open_loop",
    )
    for row in sorted_rows[:max_examples]:
        examples.append(
            {
                "run_key": row["run_key"],
                "log_path": row["log_path"],
                "record_index": row["record_index"],
                "selection_step": row["selection_step"],
                "selected_index": row["selected_index"],
                "used_fallback": row["used_fallback"],
                "latencies": {
                    field: row["latencies"].get(field)
                    for field in fields
                    if row["latencies"].get(field) is not None
                },
            }
        )
    return examples


def _primary_residual(row: dict[str, Any]) -> float:
    latencies = row["latencies"]
    projected_total = float(latencies[PROJECTED_TOTAL_FIELD])
    primary_sum = 0.0
    for field in PRIMARY_COMPONENT_FIELDS:
        if field == CLEARANCE_FIELD:
            value = latencies.get(PROJECTED_CLEARANCE_FIELD)
        else:
            value = latencies.get(field)
        if value is not None:
            primary_sum += float(value)
    return projected_total - primary_sum


def _field_values(rows: Sequence[dict[str, Any]], field: str) -> list[float]:
    values = []
    for row in rows:
        value = row["latencies"].get(field)
        if value is not None:
            values.append(float(value))
    return values


def _run_key(log_path: Path, roots: Sequence[Path]) -> str:
    resolved = Path(log_path).resolve()
    for root in roots:
        try:
            return str(resolved.parent.relative_to(root))
        except ValueError:
            continue
    return str(resolved.parent)


def _summary(values: Sequence[float]) -> dict[str, Any]:
    finite_values = [
        float(value)
        for value in values
        if not isinstance(value, bool) and np.isfinite(float(value))
    ]
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


def _percentile(values: Sequence[float], percentile: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=np.float64), percentile))


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not np.isfinite(result):
        return None
    return result


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP-CAMP Projected Latency Tail Attribution",
        "",
        f"Label: `{report['analysis'].get('label')}`",
        "",
        "> Projection only: this is not replay-measured latency and does not "
        "change selector semantics.",
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
            "## Projection Modes",
            "",
        ]
    )
    for mode, mode_report in report["projection_modes"].items():
        lines.extend(
            [
                f"### `{mode}`",
                "",
                f"Runs over budget: `{mode_report['runs_over_budget']}` / "
                f"`{mode_report['runs']}`",
                "",
                "| Tail Summary | Mean | P50 | P95 | Max | N |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
                _summary_row(
                    "projected_total",
                    mode_report["tail_latency_ms"].get(
                        PROJECTED_TOTAL_FIELD,
                        _summary([]),
                    ),
                ),
                _summary_row(
                    "projected_clearance",
                    mode_report["tail_latency_ms"].get(
                        PROJECTED_CLEARANCE_FIELD,
                        _summary([]),
                    ),
                ),
                _summary_row(
                    "primary_residual",
                    mode_report["tail_primary_residual_ms"],
                ),
                "",
                "| Top Primary Tail Component | Mean | P95 | Max | N |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in mode_report["top_tail_primary_components_by_mean_ms"]:
            lines.append(
                f"| `{row['field']}` | {_fmt(row['mean'])} | "
                f"{_fmt(row['p95'])} | {_fmt(row['max'])} | {row['n']} |"
            )
        lines.extend(
            [
                "",
                "| Over-Budget Run | Projected P95 | Shortfall | Tail Rows | Top Tail Components |",
                "| --- | ---: | ---: | ---: | --- |",
            ]
        )
        for row in mode_report["over_budget_runs"]:
            components = ", ".join(
                f"{component['field']}={component['mean']:.3f}"
                for component in row.get(
                    "top_tail_primary_components_by_mean_ms", []
                )[:3]
            )
            lines.append(
                "| "
                f"`{row['run_key']}` | {_fmt(row['projected_total_p95_ms'])} | "
                f"{_fmt(row['projected_p95_shortfall_ms'])} | "
                f"{row.get('tail_rows', 0)} | `{components}` |"
            )
        lines.append("")
    lines.extend(
        [
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
