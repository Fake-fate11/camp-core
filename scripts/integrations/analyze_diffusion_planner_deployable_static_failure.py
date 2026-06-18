#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
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


BASELINE_VARIANT = "top1"
STATIC_VARIANT = "static"

FEATURE_SPECS: tuple[tuple[str, str, str], ...] = (
    ("route_progress", "candidate_route_progress", "higher"),
    ("step_reach", "candidate_step_reach", "higher"),
    ("target_speed", "candidate_perfect_tracker_target_speed_mps", "higher"),
    (
        "tail_average_speed",
        "candidate_perfect_tracker_tail_average_speed_mps",
        "higher",
    ),
    (
        "tracker_jerk",
        "candidate_perfect_tracker_jerk_magnitude_mps3",
        "lower",
    ),
    (
        "tracker_lateral",
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
        "lower",
    ),
    (
        "horizon_lateral_cost",
        "candidate_horizon_lateral_acceleration_cost",
        "lower",
    ),
    (
        "dp_prior_jerk_excess",
        "candidate_dp_prior_jerk_excess_cost",
        "lower",
    ),
    (
        "dp_prior_lateral_excess",
        "candidate_dp_prior_lateral_acceleration_excess_cost",
        "lower",
    ),
    ("dp_prior_deviation", "candidate_dp_prior_deviation_cost", "lower"),
    ("horizon_yaw_rate_cost", "candidate_horizon_yaw_rate_cost", "lower"),
    (
        "horizon_planned_red",
        "candidate_horizon_union_planned_red_light_cost",
        "lower",
    ),
    (
        "full_horizon_planned_red",
        "candidate_full_horizon_planned_red_light_cost",
        "lower",
    ),
    ("red_stopping_margin", "candidate_red_stopping_margin_cost", "lower"),
    ("selection_score", "selection_scores", "lower"),
)

BENCHMARK_DELTA_FIELDS = (
    "safety_cost_v1",
    "route_completion_rate",
    "near_miss_rate",
    "lane_violation_rate",
    "red_light_violation_rate",
    "planned_red_light_violation_rate",
    "mean_jerk_magnitude_mps3",
    "mean_lateral_acceleration_mps2",
    "distance_traveled_m",
    "final_goal_distance_m",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Outcome-free diagnosis for a deployable static CAMP closed-loop "
            "smoke. Joins benchmark deltas with current-tick finite-candidate "
            "selection logs."
        )
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    comparison = args.comparison or args.root / "benchmark_comparison.json"
    report = analyze(args.root, comparison=comparison, label=args.label)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def analyze(root: Path, *, comparison: Path, label: str | None = None) -> dict[str, Any]:
    comparison_data = json.loads(Path(comparison).read_text(encoding="utf-8"))
    runs = comparison_data.get("runs")
    if not isinstance(runs, list):
        raise ValueError("benchmark comparison must contain a runs list.")
    by_variant_key: dict[tuple[str, str], dict[str, Any]] = {}
    for run in runs:
        if not isinstance(run, dict):
            continue
        variant = str(run.get("variant"))
        run_key = str(run.get("run_key"))
        if variant and run_key:
            by_variant_key[(variant, run_key)] = run

    static_runs = [
        run
        for run in runs
        if isinstance(run, dict) and run.get("variant") == STATIC_VARIANT
    ]
    if not static_runs:
        raise ValueError("benchmark comparison has no static runs.")

    log_paths = iter_selection_log_paths([Path(root)])
    log_by_output_dir = {str(path.parent): path for path in log_paths}

    run_rows: list[dict[str, Any]] = []
    missing_logs: list[str] = []
    for static_run in static_runs:
        run_key = str(static_run.get("run_key"))
        baseline = by_variant_key.get((BASELINE_VARIANT, run_key))
        output_dir = str(static_run.get("output_dir", ""))
        log_path = log_by_output_dir.get(output_dir)
        if log_path is None:
            missing_logs.append(output_dir)
            continue
        records = _load_records(log_path)
        selection = _selection_summary(records)
        feature_deltas = _feature_delta_summary(records)
        run_rows.append(
            {
                "run_key": run_key,
                "route_name": static_run.get("route_name"),
                "max_npcs": static_run.get("max_npcs"),
                "traffic_lights": static_run.get("traffic_lights"),
                "output_dir": output_dir,
                "log_path": str(log_path),
                "benchmark": _benchmark_summary(static_run, baseline),
                "selection": selection,
                "feature_deltas_selected_minus_top1": feature_deltas,
                "top_infeasibility_reasons": _top_counter(
                    selection["infeasibility_reasons"], limit=6
                ),
            }
        )

    if missing_logs:
        raise ValueError(
            "Missing static selection logs for output dirs: "
            + ", ".join(missing_logs[:5])
        )

    return {
        "analysis": {
            "name": "dp_camp_deployable_static_failure_diagnosis_v1",
            "label": label,
            "root": str(root),
            "comparison": str(comparison),
            "training": False,
            "online_selector_change": False,
            "closed_loop_outcome_labels_used": False,
            "future_outcome_leakage": False,
            "math_boundary": (
                "This diagnostic reads closed-loop aggregate metrics and "
                "current-tick finite-candidate logs only. Candidate feature "
                "deltas are fixed before selection. No DP generation, CAMP "
                "weights, affine score semantics, or simplex/CVaR/L2 master "
                "logic is changed. This is not Benders decomposition."
            ),
        },
        "records": {
            "static_runs": len(run_rows),
            "selection_records": int(sum(row["selection"]["records"] for row in run_rows)),
        },
        "overall": _overall_summary(run_rows, comparison_data),
        "runs": sorted(run_rows, key=_run_sort_key),
        "worst_runs": _worst_runs(run_rows),
    }


def _load_records(log_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{log_path} must contain a nonempty JSON list.")
    records = [record for record in payload if isinstance(record, dict)]
    if len(records) != len(payload):
        raise ValueError(f"{log_path} contains non-object records.")
    return records


def _benchmark_summary(
    static_run: dict[str, Any],
    baseline_run: dict[str, Any] | None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "static": {
            "safety_cost_v1": _finite(static_run.get("safety_cost_v1")),
            "route_completion_rate": _finite(static_run.get("route_completion_rate")),
            "near_miss_rate": _finite(static_run.get("near_miss_rate")),
            "lane_violation_rate": _finite(static_run.get("lane_violation_rate")),
            "p95_selection_latency_ms": _finite(
                static_run.get("p95_selection_latency_ms")
            ),
            "fallback_rate": _finite(static_run.get("fallback_rate")),
            "candidate_feasible_rate": _finite(
                static_run.get("candidate_feasible_rate")
            ),
        },
        "delta_static_minus_top1": {},
    }
    if baseline_run is None:
        summary["baseline_missing"] = True
        return summary
    for field in BENCHMARK_DELTA_FIELDS:
        static_value = _finite(static_run.get(field))
        baseline_value = _finite(baseline_run.get(field))
        summary["delta_static_minus_top1"][field] = (
            float(static_value - baseline_value)
            if static_value is not None and baseline_value is not None
            else None
        )
    return summary


def _selection_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    reason_counter: Counter[str] = Counter()
    selected_counter: Counter[str] = Counter()
    for record in records:
        candidate_count = int(record.get("num_candidates", 0))
        selected = _selected_index(record, candidate_count)
        feasible = _bool_vector(record.get("feasible_mask"), candidate_count)
        used_fallback = bool(record.get("used_fallback", not feasible.any()))
        feasible_count = int(feasible.sum())
        rows.append(
            {
                "candidate_count": candidate_count,
                "selected": selected,
                "used_fallback": used_fallback,
                "feasible_count": feasible_count,
                "top1_feasible": bool(feasible[0]) if feasible.size else False,
                "selected_feasible": (
                    bool(feasible[selected])
                    if selected is not None and feasible.size
                    else False
                ),
                "selected_top1": selected == 0,
            }
        )
        selected_counter[str(selected)] += 1
        for reason in record.get("infeasibility_reasons") or []:
            if isinstance(reason, list):
                for item in reason:
                    if item:
                        reason_counter[str(item)] += 1
            elif reason:
                reason_counter[str(reason)] += 1

    return {
        "records": len(rows),
        "fallback_rate": _mean([row["used_fallback"] for row in rows]),
        "candidate_feasible_rate": _mean(
            [
                row["feasible_count"] / row["candidate_count"]
                for row in rows
                if row["candidate_count"] > 0
            ]
        ),
        "mean_feasible_count": _mean([row["feasible_count"] for row in rows]),
        "all_feasible_rate": _mean(
            [
                row["feasible_count"] == row["candidate_count"]
                for row in rows
                if row["candidate_count"] > 0
            ]
        ),
        "top1_feasible_rate": _mean([row["top1_feasible"] for row in rows]),
        "selected_feasible_rate": _mean([row["selected_feasible"] for row in rows]),
        "selected_top1_rate": _mean([row["selected_top1"] for row in rows]),
        "selected_non_top1_rate": _mean([not row["selected_top1"] for row in rows]),
        "selected_index_counts": dict(selected_counter),
        "infeasibility_reasons": dict(reason_counter),
    }


def _feature_delta_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, field, direction in FEATURE_SPECS:
        deltas: list[float] = []
        better: list[bool] = []
        changed_deltas: list[float] = []
        changed_better: list[bool] = []
        for record in records:
            candidate_count = int(record.get("num_candidates", 0))
            selected = _selected_index(record, candidate_count)
            if selected is None or selected == 0:
                continue
            values = _float_vector(record.get(field), candidate_count)
            if values is None:
                continue
            delta = float(values[selected] - values[0])
            if not np.isfinite(delta):
                continue
            is_better = delta >= 0.0 if direction == "higher" else delta <= 0.0
            deltas.append(delta)
            better.append(is_better)
            changed_deltas.append(delta)
            changed_better.append(is_better)
        if deltas:
            result[name] = {
                "field": field,
                "direction": direction,
                "changed_records": len(changed_deltas),
                "delta": _summary(changed_deltas),
                "selected_better_or_equal_rate": _mean(changed_better),
            }
    return result


def _overall_summary(
    run_rows: list[dict[str, Any]],
    comparison_data: dict[str, Any],
) -> dict[str, Any]:
    selection = [row["selection"] for row in run_rows]
    deltas = [row["benchmark"]["delta_static_minus_top1"] for row in run_rows]
    safety_gate = comparison_data.get("safety_gate_assessments", [])
    return {
        "gate": safety_gate[0] if safety_gate else None,
        "mean_static_fallback_rate": _mean(
            row.get("fallback_rate") for row in selection
        ),
        "mean_static_candidate_feasible_rate": _mean(
            row.get("candidate_feasible_rate") for row in selection
        ),
        "mean_static_selected_non_top1_rate": _mean(
            row.get("selected_non_top1_rate") for row in selection
        ),
        "benchmark_delta_means": {
            field: _mean(delta.get(field) for delta in deltas)
            for field in BENCHMARK_DELTA_FIELDS
        },
        "global_infeasibility_reasons": _top_counter(
            _sum_counters(row["selection"]["infeasibility_reasons"] for row in run_rows),
            limit=10,
        ),
        "feature_deltas_selected_minus_top1": _aggregate_feature_deltas(run_rows),
    }


def _aggregate_feature_deltas(run_rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, _, _ in FEATURE_SPECS:
        values: list[float] = []
        rates: list[float] = []
        records = 0
        for row in run_rows:
            feature = row["feature_deltas_selected_minus_top1"].get(name)
            if not feature:
                continue
            records += int(feature["changed_records"])
            mean_delta = feature["delta"].get("mean")
            rate = feature.get("selected_better_or_equal_rate")
            if mean_delta is not None:
                values.append(float(mean_delta))
            if rate is not None:
                rates.append(float(rate))
        if records:
            result[name] = {
                "runs": len(values),
                "changed_records": records,
                "mean_of_run_mean_delta": _mean(values),
                "mean_selected_better_or_equal_rate": _mean(rates),
            }
    return result


def _worst_runs(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in run_rows:
        delta = row["benchmark"]["delta_static_minus_top1"]
        safety = delta.get("safety_cost_v1")
        completion = delta.get("route_completion_rate")
        lane = delta.get("lane_violation_rate")
        near = delta.get("near_miss_rate")
        latency = row["benchmark"]["static"].get("p95_selection_latency_ms")
        score = 0.0
        for value in (safety, lane, near):
            if value is not None:
                score += max(float(value), 0.0)
        if completion is not None:
            score += max(-float(completion), 0.0)
        if latency is not None:
            score += max(float(latency) - 100.0, 0.0) / 100.0
        scored.append((score, row))
    return [
        {
            "route_name": row["route_name"],
            "max_npcs": row["max_npcs"],
            "traffic_lights": row["traffic_lights"],
            "benchmark": row["benchmark"],
            "selection": {
                key: row["selection"][key]
                for key in (
                    "fallback_rate",
                    "candidate_feasible_rate",
                    "selected_non_top1_rate",
                    "top1_feasible_rate",
                )
            },
            "top_infeasibility_reasons": row["top_infeasibility_reasons"],
        }
        for _, row in sorted(scored, key=lambda item: item[0], reverse=True)[:5]
    ]


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP-CAMP Deployable Static Failure Diagnosis",
        "",
        f"Label: `{report['analysis'].get('label')}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
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
            "## Gate",
            "",
        ]
    )
    gate = report["overall"].get("gate") or {}
    if gate:
        lines.extend(
            [
                "| Check | Value |",
                "| --- | --- |",
                f"| `hard_gate_passed` | `{gate.get('hard_gate_passed')}` |",
                f"| `safety_cost_claim_passed` | `{gate.get('safety_cost_claim_passed')}` |",
                f"| `claim_rule` | `{gate.get('claim_rule')}` |",
            ]
        )

    lines.extend(
        [
            "",
            "## Run Diagnostics",
            "",
            "| Route | NPC | TL | Safety Delta | Completion Delta | Near Delta | Lane Delta | P95 Latency | Fallback | Feasible | Non-Top1 Selected | Top Reasons |",
            "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in report["runs"]:
        delta = row["benchmark"]["delta_static_minus_top1"]
        static = row["benchmark"]["static"]
        sel = row["selection"]
        reasons = ", ".join(
            f"{item['reason']}:{item['count']}"
            for item in row["top_infeasibility_reasons"][:3]
        )
        lines.append(
            "| "
            f"`{row['route_name']}` | `{row['max_npcs']}` | `{row['traffic_lights']}` | "
            f"{_fmt(delta.get('safety_cost_v1'))} | "
            f"{_fmt(delta.get('route_completion_rate'))} | "
            f"{_fmt(delta.get('near_miss_rate'))} | "
            f"{_fmt(delta.get('lane_violation_rate'))} | "
            f"{_fmt(static.get('p95_selection_latency_ms'))} | "
            f"{_fmt(sel.get('fallback_rate'))} | "
            f"{_fmt(sel.get('candidate_feasible_rate'))} | "
            f"{_fmt(sel.get('selected_non_top1_rate'))} | {reasons} |"
        )

    lines.extend(
        [
            "",
            "## Overall Feature Deltas",
            "",
            "Values are selected candidate minus DP Top-1 on records where static CAMP did not select Top-1.",
            "",
            "| Feature | Changed Records | Mean Run Delta | Better-or-Equal Rate |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for name, row in report["overall"]["feature_deltas_selected_minus_top1"].items():
        lines.append(
            "| "
            f"`{name}` | `{row['changed_records']}` | "
            f"{_fmt(row.get('mean_of_run_mean_delta'))} | "
            f"{_fmt(row.get('mean_selected_better_or_equal_rate'))} |"
        )

    lines.extend(
        [
            "",
            "## Worst Runs",
            "",
            "| Route | NPC | TL | Safety Delta | Completion Delta | Near Delta | Lane Delta | P95 Latency | Fallback | Feasible | Reasons |",
            "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in report["worst_runs"]:
        delta = row["benchmark"]["delta_static_minus_top1"]
        static = row["benchmark"]["static"]
        sel = row["selection"]
        reasons = ", ".join(
            f"{item['reason']}:{item['count']}"
            for item in row["top_infeasibility_reasons"][:4]
        )
        lines.append(
            "| "
            f"`{row['route_name']}` | `{row['max_npcs']}` | `{row['traffic_lights']}` | "
            f"{_fmt(delta.get('safety_cost_v1'))} | "
            f"{_fmt(delta.get('route_completion_rate'))} | "
            f"{_fmt(delta.get('near_miss_rate'))} | "
            f"{_fmt(delta.get('lane_violation_rate'))} | "
            f"{_fmt(static.get('p95_selection_latency_ms'))} | "
            f"{_fmt(sel.get('fallback_rate'))} | "
            f"{_fmt(sel.get('candidate_feasible_rate'))} | {reasons} |"
        )

    lines.append("")
    return "\n".join(lines)


def _selected_index(record: dict[str, Any], candidate_count: int) -> int | None:
    try:
        selected = int(record.get("selected_index"))
    except (TypeError, ValueError):
        return None
    if selected < 0 or selected >= candidate_count:
        return None
    return selected


def _bool_vector(value: Any, size: int) -> np.ndarray:
    arr = np.asarray(value, dtype=bool).reshape(-1)
    if arr.size != size:
        return np.zeros(size, dtype=bool)
    return arr


def _float_vector(value: Any, size: int) -> np.ndarray | None:
    if value is None:
        return None
    try:
        arr = np.asarray(value, dtype=np.float64).reshape(-1)
    except (TypeError, ValueError):
        return None
    if arr.size != size or not np.all(np.isfinite(arr)):
        return None
    return arr


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if np.isfinite(result) else None


def _mean(values: Any) -> float | None:
    finite_values: list[float] = []
    for value in values:
        if isinstance(value, bool):
            finite_values.append(float(value))
            continue
        finite = _finite(value)
        if finite is not None:
            finite_values.append(finite)
    if not finite_values:
        return None
    return float(np.mean(np.asarray(finite_values, dtype=np.float64)))


def _summary(values: list[float]) -> dict[str, Any]:
    finite_values = [
        float(value)
        for value in values
        if _finite(value) is not None
    ]
    if not finite_values:
        return {"n": 0, "mean": None, "min": None, "p50": None, "p95": None, "max": None}
    arr = np.asarray(finite_values, dtype=np.float64)
    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "min": float(np.min(arr)),
        "p50": float(np.percentile(arr, 50.0)),
        "p95": float(np.percentile(arr, 95.0)),
        "max": float(np.max(arr)),
    }


def _top_counter(counter_like: dict[str, int] | Counter[str], *, limit: int) -> list[dict[str, Any]]:
    counter = Counter(counter_like)
    return [
        {"reason": str(reason), "count": int(count)}
        for reason, count in counter.most_common(limit)
    ]


def _sum_counters(items: Any) -> Counter[str]:
    counter: Counter[str] = Counter()
    for item in items:
        counter.update(item)
    return counter


def _fmt(value: Any) -> str:
    finite = _finite(value)
    if finite is None:
        return "n/a"
    return f"`{finite:.6g}`"


def _run_sort_key(row: dict[str, Any]) -> tuple[str, int, str]:
    return (
        str(row.get("route_name")),
        int(row.get("max_npcs") or 0),
        str(row.get("traffic_lights")),
    )


if __name__ == "__main__":
    main()
