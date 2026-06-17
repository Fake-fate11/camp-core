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
REWARD_FIELD = "latency_ms_reward_scoring"

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

CONTEXT_FIELDS = (
    "latency_ms_candidate_generation",
    "latency_ms_camp_selection",
    "latency_ms_camp_atom_computation",
    "latency_ms_context_and_obstacles",
    "latency_ms_shadow_obstacle_clearance",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Attribute reward-scoring latency tails inside existing DP-CAMP "
            "selection logs. This is read-only and does not replay or change "
            "selector semantics."
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
        if row["latencies"].get(TOTAL_FIELD) is not None
        and row["latencies"].get(CLEARANCE_FIELD) is not None
    ]
    if not usable_rows:
        raise ValueError(
            f"No records had finite {TOTAL_FIELD} and {CLEARANCE_FIELD} values."
        )

    scale_ratio = reference_new_clearance_p95_ms / reference_old_clearance_p95_ms
    projection_modes: dict[str, Callable[[float], float]] = {
        "constant_new_p95": lambda old: reference_new_clearance_p95_ms,
        "cap_at_new_p95": lambda old: min(old, reference_new_clearance_p95_ms),
        "scale_by_smoke_p95_ratio": lambda old: old * scale_ratio,
    }
    return {
        "analysis": {
            "name": "dp_camp_reward_latency_tail_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_outcome_labels_used": False,
            "projection_not_replay_measurement": True,
            "selector_semantics_changed": False,
            "budget_ms": float(budget_ms),
            "tail_percentile": float(tail_percentile),
            "math_boundary": (
                "Reward latency attribution is engineering plumbing over fixed "
                "current-tick logs. It does not change candidates, reward "
                "values, feasibility masks, CAMP atoms, affine scoring, "
                "Benders-style subproblems, duals, or cuts."
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
                row["latencies"].get(TOTAL_FIELD) is None for row in rows
            ),
            "missing_clearance_latency": sum(
                row["latencies"].get(CLEARANCE_FIELD) is None for row in rows
            ),
        },
        "projection_modes": {
            mode_name: _mode_report(
                usable_rows,
                projection_fn=projection_fn,
                budget_ms=budget_ms,
                tail_percentile=tail_percentile,
                max_examples=max_examples,
            )
            for mode_name, projection_fn in projection_modes.items()
        },
    }


def _mode_report(
    rows: Sequence[dict[str, Any]],
    *,
    projection_fn: Callable[[float], float],
    budget_ms: float,
    tail_percentile: float,
    max_examples: int,
) -> dict[str, Any]:
    projected_rows = [_project_row(row, projection_fn) for row in rows]
    run_summaries, tail_rows = _run_summaries(
        projected_rows,
        budget_ms=budget_ms,
        tail_percentile=tail_percentile,
    )
    over_budget_runs = [row for row in run_summaries if row["over_budget"]]
    return {
        "runs": len(run_summaries),
        "runs_over_budget": len(over_budget_runs),
        "tail_rows": len(tail_rows),
        "tail_reward_scoring_ms": _summary(
            _latency_values(tail_rows, REWARD_FIELD)
        ),
        "tail_reward_breakdown_sum_ms": _summary(
            [_reward_breakdown_sum(row["latencies"]) for row in tail_rows]
        ),
        "tail_reward_unattributed_residual_ms": _summary(
            [_reward_residual(row["latencies"]) for row in tail_rows]
        ),
        "tail_context_latency_ms": _component_summaries(tail_rows, CONTEXT_FIELDS),
        "tail_reward_breakdown_ms": _component_summaries(
            tail_rows,
            REWARD_BREAKDOWN_FIELDS,
        ),
        "top_reward_components_by_tail_mean_ms": _top_components(
            tail_rows,
            fields=(*REWARD_BREAKDOWN_FIELDS, "reward_unattributed_residual"),
            max_examples=max_examples,
        ),
        "reward_component_savings": _reward_component_savings(
            projected_rows,
            budget_ms=budget_ms,
            max_examples=max_examples,
        ),
        "over_budget_runs": over_budget_runs[:max_examples],
        "top_tail_records": _top_tail_records(tail_rows, max_examples),
    }


def _reward_component_savings(
    rows: Sequence[dict[str, Any]],
    *,
    budget_ms: float,
    max_examples: int,
) -> dict[str, Any]:
    scenarios: dict[str, Callable[[dict[str, float | None]], float]] = {}
    for field in (*REWARD_BREAKDOWN_FIELDS, "reward_unattributed_residual"):
        for fraction in (0.25, 0.50, 1.0):
            suffix = "zero" if fraction == 1.0 else f"{int(fraction * 100)}pct"
            scenarios[f"{field}_{suffix}_saving"] = (
                lambda latencies, field=field, fraction=fraction: (
                    fraction * _reward_component_value(latencies, field)
                )
            )
    for fraction in (0.25, 0.50, 1.0):
        suffix = "zero" if fraction == 1.0 else f"{int(fraction * 100)}pct"
        scenarios[f"all_instrumented_reward_breakdown_{suffix}_saving"] = (
            lambda latencies, fraction=fraction: (
                fraction * _reward_breakdown_sum(latencies)
            )
        )

    reports = {}
    for name, saving_fn in scenarios.items():
        adjusted_rows = []
        for row in rows:
            saving = min(
                max(float(saving_fn(row["latencies"])), 0.0),
                _latency(row["latencies"], REWARD_FIELD),
            )
            adjusted_rows.append(
                {
                    **row,
                    "adjusted_total_ms": max(
                        float(row[PROJECTED_TOTAL_FIELD]) - saving,
                        0.0,
                    ),
                    "scenario_saving_ms": saving,
                }
            )
        run_summaries = _adjusted_run_summaries(
            adjusted_rows,
            budget_ms=budget_ms,
        )
        over_budget = [run for run in run_summaries if run["over_budget"]]
        reports[name] = {
            "runs": len(run_summaries),
            "runs_over_budget": len(over_budget),
            "per_run_p95_ms": _summary([run["p95_ms"] for run in run_summaries]),
            "per_run_shortfall_ms": _summary(
                [run["shortfall_ms"] for run in over_budget]
            ),
            "mean_record_saving_ms": _summary(
                [row["scenario_saving_ms"] for row in adjusted_rows]
            ),
            "over_budget_runs": over_budget[:max_examples],
        }
    return dict(
        sorted(
            reports.items(),
            key=lambda item: (
                item[1]["runs_over_budget"],
                item[1]["per_run_shortfall_ms"]["max"]
                if item[1]["per_run_shortfall_ms"]["max"] is not None
                else -1.0,
                item[0],
            ),
        )
    )


def _project_row(
    row: dict[str, Any],
    projection_fn: Callable[[float], float],
) -> dict[str, Any]:
    latencies = dict(row["latencies"])
    total = _latency(latencies, TOTAL_FIELD)
    old_clearance = _latency(latencies, CLEARANCE_FIELD)
    projected_clearance = float(projection_fn(old_clearance))
    projected_total = max(total - old_clearance + projected_clearance, 0.0)
    return {
        **row,
        "latencies": latencies,
        "projected_clearance_ms": projected_clearance,
        PROJECTED_TOTAL_FIELD: projected_total,
    }


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
        values = [float(row[PROJECTED_TOTAL_FIELD]) for row in run_rows]
        p95 = _percentile(values, 95.0)
        over_budget = p95 > budget_ms
        summary = {
            "run_key": run_key,
            "records": len(run_rows),
            "p95_ms": float(p95),
            "shortfall_ms": float(max(p95 - budget_ms, 0.0)),
            "over_budget": bool(over_budget),
        }
        if over_budget:
            threshold = _percentile(values, tail_percentile)
            run_tail_rows = [
                row
                for row in run_rows
                if float(row[PROJECTED_TOTAL_FIELD]) >= threshold
            ]
            summary["tail_threshold_ms"] = float(threshold)
            summary["tail_rows"] = len(run_tail_rows)
            summary["top_reward_components_by_tail_mean_ms"] = _top_components(
                run_tail_rows,
                fields=(*REWARD_BREAKDOWN_FIELDS, "reward_unattributed_residual"),
                max_examples=5,
            )
            tail_rows.extend(run_tail_rows)
        summaries.append(summary)
    summaries.sort(key=lambda row: (row["p95_ms"], row["run_key"]), reverse=True)
    return summaries, tail_rows


def _adjusted_run_summaries(
    rows: Sequence[dict[str, Any]],
    *,
    budget_ms: float,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["run_key"], []).append(row)
    result = []
    for run_key, run_rows in grouped.items():
        values = [float(row["adjusted_total_ms"]) for row in run_rows]
        p95 = _percentile(values, 95.0)
        result.append(
            {
                "run_key": run_key,
                "records": len(run_rows),
                "p95_ms": float(p95),
                "shortfall_ms": float(max(p95 - budget_ms, 0.0)),
                "over_budget": bool(p95 > budget_ms),
            }
        )
    return sorted(result, key=lambda row: (row["p95_ms"], row["run_key"]), reverse=True)


def _top_tail_records(
    rows: Sequence[dict[str, Any]],
    max_examples: int,
) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        rows,
        key=lambda row: float(row[PROJECTED_TOTAL_FIELD]),
        reverse=True,
    )
    examples = []
    for row in sorted_rows[:max_examples]:
        fields = (
            TOTAL_FIELD,
            PROJECTED_TOTAL_FIELD,
            CLEARANCE_FIELD,
            REWARD_FIELD,
            *REWARD_BREAKDOWN_FIELDS,
        )
        examples.append(
            {
                "run_key": row["run_key"],
                "log_path": row["log_path"],
                "record_index": row["record_index"],
                "selection_step": row["selection_step"],
                "latencies": {
                    field: (
                        row[PROJECTED_TOTAL_FIELD]
                        if field == PROJECTED_TOTAL_FIELD
                        else row["latencies"].get(field)
                    )
                    for field in fields
                    if (
                        row[PROJECTED_TOTAL_FIELD]
                        if field == PROJECTED_TOTAL_FIELD
                        else row["latencies"].get(field)
                    )
                    is not None
                },
                "reward_breakdown_sum_ms": _reward_breakdown_sum(row["latencies"]),
                "reward_unattributed_residual_ms": _reward_residual(
                    row["latencies"]
                ),
            }
        )
    return examples


def _component_summaries(
    rows: Sequence[dict[str, Any]],
    fields: Sequence[str],
) -> dict[str, Any]:
    result = {}
    for field in fields:
        values = _latency_values(rows, field)
        if values:
            result[field] = _summary(values)
    return result


def _top_components(
    rows: Sequence[dict[str, Any]],
    *,
    fields: Sequence[str],
    max_examples: int,
) -> list[dict[str, Any]]:
    ranked = []
    for field in fields:
        if field == "reward_unattributed_residual":
            values = [_reward_residual(row["latencies"]) for row in rows]
        else:
            values = _latency_values(rows, field)
        summary = _summary(values)
        if summary["n"] == 0 or summary["mean"] is None:
            continue
        ranked.append({"field": field, **summary})
    ranked.sort(
        key=lambda row: (row["mean"], row["p95"] or 0.0, row["field"]),
        reverse=True,
    )
    return ranked[:max_examples]


def _latency_values(rows: Sequence[dict[str, Any]], field: str) -> list[float]:
    values = []
    for row in rows:
        value = row["latencies"].get(field)
        if value is not None:
            values.append(float(value))
    return values


def _reward_component_value(
    latencies: dict[str, float | None],
    field: str,
) -> float:
    if field == "reward_unattributed_residual":
        return max(_reward_residual(latencies), 0.0)
    return _latency(latencies, field)


def _reward_breakdown_sum(latencies: dict[str, float | None]) -> float:
    return sum(_latency(latencies, field) for field in REWARD_BREAKDOWN_FIELDS)


def _reward_residual(latencies: dict[str, float | None]) -> float:
    return _latency(latencies, REWARD_FIELD) - _reward_breakdown_sum(latencies)


def _load_rows(
    log_paths: Sequence[Path],
    roots: Sequence[Path],
) -> list[dict[str, Any]]:
    fields = (
        TOTAL_FIELD,
        CLEARANCE_FIELD,
        REWARD_FIELD,
        *REWARD_BREAKDOWN_FIELDS,
        *CONTEXT_FIELDS,
    )
    rows: list[dict[str, Any]] = []
    for log_path in log_paths:
        records = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(records, list):
            raise ValueError(f"{log_path} must contain a JSON list.")
        run_key = _run_key(log_path, roots)
        for record_index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            rows.append(
                {
                    "log_path": str(log_path),
                    "run_key": run_key,
                    "record_index": int(record_index),
                    "selection_step": record.get("selection_step", record_index),
                    "latencies": {
                        field: _finite(record.get(field))
                        for field in dict.fromkeys(fields)
                    },
                }
            )
    return rows


def _directory_inputs(paths: Sequence[Path]) -> list[Path]:
    roots = [Path(path).resolve() for path in paths if Path(path).is_dir()]
    return sorted(roots, key=lambda path: len(path.parts), reverse=True)


def _run_key(log_path: Path, roots: Sequence[Path]) -> str:
    resolved = Path(log_path).resolve()
    for root in roots:
        try:
            return str(resolved.parent.relative_to(root))
        except ValueError:
            continue
    return str(resolved.parent)


def _latency(latencies: dict[str, float | None], field: str) -> float:
    value = latencies.get(field)
    return 0.0 if value is None else float(value)


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not np.isfinite(result):
        return None
    return result


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


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP-CAMP Reward Latency Tail Attribution",
        "",
        f"Label: `{report['analysis'].get('label')}`",
        "",
        "> Projection only: reward latency savings are hypothetical engineering "
        "diagnostics and do not change selector semantics.",
        "",
        "## Records",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in report["records"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(["", "## Projection Modes", ""])
    for mode_name, mode in report["projection_modes"].items():
        lines.extend(
            [
                f"### `{mode_name}`",
                "",
                f"Runs over budget: `{mode['runs_over_budget']}` / `{mode['runs']}`",
                "",
                "| Reward Tail Summary | Mean | P50 | P95 | Max | N |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
                _summary_row("reward_scoring", mode["tail_reward_scoring_ms"]),
                _summary_row(
                    "reward_breakdown_sum",
                    mode["tail_reward_breakdown_sum_ms"],
                ),
                _summary_row(
                    "reward_unattributed_residual",
                    mode["tail_reward_unattributed_residual_ms"],
                ),
                "",
                "| Top Reward Component | Mean | P95 | Max | N |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in mode["top_reward_components_by_tail_mean_ms"]:
            lines.append(
                f"| `{row['field']}` | {_fmt(row['mean'])} | "
                f"{_fmt(row['p95'])} | {_fmt(row['max'])} | {row['n']} |"
            )
        lines.extend(
            [
                "",
                "| Reward Savings Scenario | Runs Over Budget | P95 of Run P95 | Shortfall Max | Mean Record Saving |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for name, scenario in list(mode["reward_component_savings"].items())[:12]:
            lines.append(
                f"| `{name}` | `{scenario['runs_over_budget']} / {scenario['runs']}` | "
                f"{_fmt(scenario['per_run_p95_ms']['p95'])} | "
                f"{_fmt(scenario['per_run_shortfall_ms']['max'])} | "
                f"{_fmt(scenario['mean_record_saving_ms']['mean'])} |"
            )
        lines.append("")
    lines.extend(["## Mathematical Boundary", "", report["analysis"]["math_boundary"]])
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
