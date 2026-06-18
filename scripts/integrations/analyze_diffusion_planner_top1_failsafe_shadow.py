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


BASELINE_VARIANT = "top1"
STATIC_VARIANT = "static"
TOL = 1e-12

RULES: tuple[dict[str, Any], ...] = (
    {
        "name": "static_baseline",
        "description": "retain logged static CAMP selection",
    },
    {
        "name": "top1_on_all_infeasible",
        "top1_on_all_infeasible": True,
        "description": (
            "when CAMP feasibility rejects every candidate, preserve DP Top-1; "
            "otherwise retain logged static CAMP"
        ),
    },
    {
        "name": "top1_on_dp_prior_deviation_worse",
        "dp_prior_deviation_eps": 0.0,
        "description": (
            "when candidate0 is feasible and static selection has higher "
            "candidate_dp_prior_deviation_cost than DP Top-1, preserve Top-1"
        ),
    },
    {
        "name": "top1_on_all_infeasible_or_dp_prior_deviation_worse",
        "top1_on_all_infeasible": True,
        "dp_prior_deviation_eps": 0.0,
        "description": (
            "combine all-infeasible Top-1 fallback with DP-prior-deviation "
            "preservation"
        ),
    },
    {
        "name": "top1_on_fallback_or_prior_or_speed_loss_0p1",
        "top1_on_all_infeasible": True,
        "dp_prior_deviation_eps": 0.0,
        "target_speed_loss_budget_mps": 0.1,
        "description": (
            "combine all-infeasible Top-1 fallback, DP-prior-deviation "
            "preservation, and Top-1 preservation when static selection loses "
            "more than 0.1 m/s target speed"
        ),
    },
)

FEATURES: tuple[tuple[str, str, str], ...] = (
    ("route_progress", "candidate_route_progress", "higher"),
    ("target_speed", "candidate_perfect_tracker_target_speed_mps", "higher"),
    (
        "tail_average_speed",
        "candidate_perfect_tracker_tail_average_speed_mps",
        "higher",
    ),
    ("dp_prior_deviation", "candidate_dp_prior_deviation_cost", "lower"),
    ("dp_prior_jerk_excess", "candidate_dp_prior_jerk_excess_cost", "lower"),
    (
        "dp_prior_lateral_excess",
        "candidate_dp_prior_lateral_acceleration_excess_cost",
        "lower",
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
    ("selection_score", "selection_scores", "lower"),
)

BENCHMARK_DELTA_FIELDS = (
    "safety_cost_v1",
    "route_completion_rate",
    "near_miss_rate",
    "lane_violation_rate",
    "mean_jerk_magnitude_mps3",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Outcome-free Top-1 failsafe shadow audit for deployable static "
            "CAMP selection logs. This reads only current-tick finite-candidate "
            "diagnostics; it does not change online selection."
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
    static_runs = _static_runs(comparison_data)
    log_by_output_dir = {str(path.parent): path for path in iter_selection_log_paths([root])}
    run_records: list[dict[str, Any]] = []
    for static_run in static_runs:
        output_dir = str(static_run.get("output_dir", ""))
        log_path = log_by_output_dir.get(output_dir)
        if log_path is None:
            raise ValueError(f"Missing static selection log for {output_dir}.")
        records = _load_records(log_path)
        run_records.append(
            {
                "run": static_run,
                "baseline": _baseline_for_run(comparison_data, static_run),
                "log_path": str(log_path),
                "records": records,
            }
        )

    rule_reports = [_rule_report(rule, run_records) for rule in RULES]
    return {
        "analysis": {
            "name": "dp_camp_top1_failsafe_shadow_v1",
            "label": label,
            "root": str(root),
            "comparison": str(comparison),
            "training": False,
            "online_selector_change": False,
            "closed_loop_outcome_labels_used": False,
            "future_outcome_leakage": False,
            "rules": [
                {
                    "name": rule["name"],
                    "description": rule["description"],
                    **{
                        key: value
                        for key, value in rule.items()
                        if key
                        in {
                            "top1_on_all_infeasible",
                            "dp_prior_deviation_eps",
                            "target_speed_loss_budget_mps",
                        }
                    },
                }
                for rule in RULES
            ],
            "math_boundary": (
                "Every shadow rule uses only fixed current-tick finite-candidate "
                "diagnostics: feasible_mask, candidate0 index, logged static "
                "selected index, DP-prior deviation cost, target speed, and "
                "selection scores. It does not use future outcomes, does not "
                "modify DP, and does not change CAMP weights or the affine "
                "score. This is a finite-candidate failsafe audit, not "
                "classical Benders decomposition."
            ),
            "acceptance_boundary": (
                "This artifact can only justify a later default-off online "
                "smoke if a rule materially reduces the diagnosed dense "
                "lane-change fallback/DP-prior-deviation mechanism while "
                "preserving deterministic fail-closed behavior. It cannot by "
                "itself prove closed-loop SafetyCost improvement."
            ),
        },
        "records": {
            "static_runs": len(run_records),
            "selection_records": int(sum(len(item["records"]) for item in run_records)),
        },
        "rules": rule_reports,
    }


def _static_runs(comparison_data: dict[str, Any]) -> list[dict[str, Any]]:
    runs = comparison_data.get("runs")
    if not isinstance(runs, list):
        raise ValueError("benchmark comparison must contain a runs list.")
    static_runs = [
        run for run in runs if isinstance(run, dict) and run.get("variant") == STATIC_VARIANT
    ]
    if not static_runs:
        raise ValueError("benchmark comparison has no static runs.")
    return static_runs


def _baseline_for_run(
    comparison_data: dict[str, Any],
    static_run: dict[str, Any],
) -> dict[str, Any] | None:
    run_key = static_run.get("run_key")
    for run in comparison_data.get("runs", []):
        if (
            isinstance(run, dict)
            and run.get("variant") == BASELINE_VARIANT
            and run.get("run_key") == run_key
        ):
            return run
    return None


def _load_records(log_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{log_path} must contain a nonempty JSON list.")
    return [_load_record(record, f"{log_path} record {idx}") for idx, record in enumerate(payload)]


def _load_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(record.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected = int(record.get("selected_index"))
    if selected < 0 or selected >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    feasible = _bool_vector(record.get("feasible_mask"), candidate_count, f"{label} feasible_mask")
    features = {
        name: _float_vector(record.get(field), candidate_count)
        for name, field, _ in FEATURES
    }
    return {
        "candidate_count": candidate_count,
        "selected": selected,
        "feasible": feasible,
        "used_fallback": bool(record.get("used_fallback", not feasible.any())),
        "features": features,
    }


def _rule_report(
    rule: dict[str, Any],
    run_records: list[dict[str, Any]],
) -> dict[str, Any]:
    run_reports = [_run_report(rule, item) for item in run_records]
    return {
        "name": rule["name"],
        "description": rule["description"],
        "overall": _aggregate_runs(run_reports),
        "runs": sorted(run_reports, key=_run_sort_key),
        "worst_coverage": _worst_coverage(run_reports),
    }


def _run_report(rule: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    static_run = item["run"]
    baseline = item["baseline"]
    records = item["records"]
    shadow_rows = [_shadow_row(rule, record) for record in records]
    deltas = _benchmark_deltas(static_run, baseline)
    return {
        "route_name": static_run.get("route_name"),
        "max_npcs": static_run.get("max_npcs"),
        "traffic_lights": static_run.get("traffic_lights"),
        "benchmark_delta_static_minus_top1": deltas,
        "static_p95_selection_latency_ms": _finite(
            static_run.get("p95_selection_latency_ms")
        ),
        "records": len(shadow_rows),
        "changed_from_static_rate": _mean(row["shadow_selected"] != row["static_selected"] for row in shadow_rows),
        "top1_selected_rate": _mean(row["shadow_selected"] == 0 for row in shadow_rows),
        "static_top1_selected_rate": _mean(row["static_selected"] == 0 for row in shadow_rows),
        "all_infeasible_top1_restored_rate": _conditional_rate(
            shadow_rows,
            lambda row: row["all_infeasible"],
            lambda row: row["shadow_selected"] == 0 and row["static_selected"] != 0,
        ),
        "dp_prior_deviation_trigger_rate": _mean(
            "dp_prior_deviation_worse" in row["reasons"] for row in shadow_rows
        ),
        "target_speed_trigger_rate": _mean(
            "target_speed_loss" in row["reasons"] for row in shadow_rows
        ),
        "score_penalty_shadow_minus_static": _summary(
            row["score_penalty"] for row in shadow_rows
        ),
        "feature_delta_shadow_minus_top1": _feature_delta_summary(
            shadow_rows,
            selected_key="shadow_selected",
        ),
        "feature_delta_static_minus_top1": _feature_delta_summary(
            shadow_rows,
            selected_key="static_selected",
        ),
    }


def _shadow_row(rule: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    static_selected = int(record["selected"])
    shadow_selected = static_selected
    reasons: list[str] = []
    all_infeasible = not bool(record["feasible"].any())
    candidate0_feasible = bool(record["feasible"].size and record["feasible"][0])
    if rule.get("top1_on_all_infeasible") and all_infeasible and static_selected != 0:
        shadow_selected = 0
        reasons.append("all_infeasible")

    dp_prior_eps = rule.get("dp_prior_deviation_eps")
    dp_prior = record["features"].get("dp_prior_deviation")
    if (
        dp_prior_eps is not None
        and candidate0_feasible
        and static_selected != 0
        and dp_prior is not None
        and dp_prior[static_selected] > dp_prior[0] + float(dp_prior_eps) + TOL
    ):
        shadow_selected = 0
        reasons.append("dp_prior_deviation_worse")

    speed_budget = rule.get("target_speed_loss_budget_mps")
    target_speed = record["features"].get("target_speed")
    if (
        speed_budget is not None
        and candidate0_feasible
        and static_selected != 0
        and target_speed is not None
        and target_speed[0] - target_speed[static_selected] > float(speed_budget) + TOL
    ):
        shadow_selected = 0
        reasons.append("target_speed_loss")

    score = record["features"].get("selection_score")
    score_penalty = None
    if score is not None:
        score_penalty = float(score[shadow_selected] - score[static_selected])

    return {
        "static_selected": static_selected,
        "shadow_selected": int(shadow_selected),
        "reasons": reasons,
        "all_infeasible": all_infeasible,
        "candidate0_feasible": candidate0_feasible,
        "score_penalty": score_penalty,
        "features": record["features"],
    }


def _benchmark_deltas(
    static_run: dict[str, Any],
    baseline: dict[str, Any] | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in BENCHMARK_DELTA_FIELDS:
        static_value = _finite(static_run.get(field))
        baseline_value = None if baseline is None else _finite(baseline.get(field))
        result[field] = (
            float(static_value - baseline_value)
            if static_value is not None and baseline_value is not None
            else None
        )
    return result


def _feature_delta_summary(
    rows: list[dict[str, Any]],
    *,
    selected_key: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, _, direction in FEATURES:
        deltas: list[float] = []
        better: list[bool] = []
        for row in rows:
            selected = int(row[selected_key])
            values = row["features"].get(name)
            if values is None:
                continue
            delta = float(values[selected] - values[0])
            deltas.append(delta)
            better.append(delta >= -TOL if direction == "higher" else delta <= TOL)
        if deltas:
            result[name] = {
                "direction": direction,
                "delta": _summary(deltas),
                "selected_better_or_equal_rate": _mean(better),
            }
    return result


def _aggregate_runs(run_reports: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "changed_from_static_rate": _weighted_mean(run_reports, "changed_from_static_rate"),
        "top1_selected_rate": _weighted_mean(run_reports, "top1_selected_rate"),
        "static_top1_selected_rate": _weighted_mean(run_reports, "static_top1_selected_rate"),
        "all_infeasible_top1_restored_rate": _mean(
            row.get("all_infeasible_top1_restored_rate") for row in run_reports
        ),
        "dp_prior_deviation_trigger_rate": _weighted_mean(
            run_reports,
            "dp_prior_deviation_trigger_rate",
        ),
        "target_speed_trigger_rate": _weighted_mean(
            run_reports,
            "target_speed_trigger_rate",
        ),
        "score_penalty_shadow_minus_static": _summary(
            _run_summary_mean(row["score_penalty_shadow_minus_static"])
            for row in run_reports
        ),
        "feature_delta_shadow_minus_top1": _aggregate_feature_delta(
            run_reports,
            "feature_delta_shadow_minus_top1",
        ),
    }


def _aggregate_feature_delta(
    run_reports: list[dict[str, Any]],
    key: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, _, _ in FEATURES:
        means = []
        rates = []
        for row in run_reports:
            feature = row[key].get(name)
            if not feature:
                continue
            mean = feature["delta"].get("mean")
            rate = feature.get("selected_better_or_equal_rate")
            if mean is not None:
                means.append(float(mean))
            if rate is not None:
                rates.append(float(rate))
        if means:
            result[name] = {
                "mean_of_run_mean_delta": _mean(means),
                "mean_selected_better_or_equal_rate": _mean(rates),
            }
    return result


def _worst_coverage(run_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in run_reports:
        delta = row["benchmark_delta_static_minus_top1"]
        score = 0.0
        for field in ("safety_cost_v1", "near_miss_rate", "lane_violation_rate"):
            value = delta.get(field)
            if value is not None:
                score += max(float(value), 0.0)
        completion = delta.get("route_completion_rate")
        if completion is not None:
            score += max(-float(completion), 0.0)
        latency = row.get("static_p95_selection_latency_ms")
        if latency is not None:
            score += max(float(latency) - 100.0, 0.0) / 100.0
        scored.append((score, row))
    return [
        {
            "route_name": row["route_name"],
            "max_npcs": row["max_npcs"],
            "traffic_lights": row["traffic_lights"],
            "benchmark_delta_static_minus_top1": row["benchmark_delta_static_minus_top1"],
            "changed_from_static_rate": row["changed_from_static_rate"],
            "top1_selected_rate": row["top1_selected_rate"],
            "all_infeasible_top1_restored_rate": row["all_infeasible_top1_restored_rate"],
            "dp_prior_deviation_trigger_rate": row["dp_prior_deviation_trigger_rate"],
            "target_speed_trigger_rate": row["target_speed_trigger_rate"],
        }
        for _, row in sorted(scored, key=lambda item: item[0], reverse=True)[:5]
    ]


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP-CAMP Top-1 Failsafe Shadow Audit",
        "",
        f"Label: `{report['analysis'].get('label')}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        report["analysis"]["acceptance_boundary"],
        "",
        "## Records",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in report["records"].items():
        lines.append(f"| `{key}` | `{value}` |")
    for rule in report["rules"]:
        overall = rule["overall"]
        lines.extend(
            [
                "",
                f"## Rule: `{rule['name']}`",
                "",
                rule["description"],
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| `changed_from_static_rate` | {_fmt(overall.get('changed_from_static_rate'))} |",
                f"| `top1_selected_rate` | {_fmt(overall.get('top1_selected_rate'))} |",
                f"| `static_top1_selected_rate` | {_fmt(overall.get('static_top1_selected_rate'))} |",
                f"| `all_infeasible_top1_restored_rate` | {_fmt(overall.get('all_infeasible_top1_restored_rate'))} |",
                f"| `dp_prior_deviation_trigger_rate` | {_fmt(overall.get('dp_prior_deviation_trigger_rate'))} |",
                f"| `target_speed_trigger_rate` | {_fmt(overall.get('target_speed_trigger_rate'))} |",
                f"| `score_penalty_mean` | {_fmt((overall.get('score_penalty_shadow_minus_static') or {}).get('mean'))} |",
                "",
                "### Worst-Run Coverage",
                "",
                "| Route | NPC | TL | Safety Delta | Completion Delta | Changed | Top1 Rate | All-Infeasible Restored | Prior Trigger | Speed Trigger |",
                "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in rule["worst_coverage"]:
            delta = row["benchmark_delta_static_minus_top1"]
            lines.append(
                "| "
                f"`{row['route_name']}` | `{row['max_npcs']}` | `{row['traffic_lights']}` | "
                f"{_fmt(delta.get('safety_cost_v1'))} | "
                f"{_fmt(delta.get('route_completion_rate'))} | "
                f"{_fmt(row.get('changed_from_static_rate'))} | "
                f"{_fmt(row.get('top1_selected_rate'))} | "
                f"{_fmt(row.get('all_infeasible_top1_restored_rate'))} | "
                f"{_fmt(row.get('dp_prior_deviation_trigger_rate'))} | "
                f"{_fmt(row.get('target_speed_trigger_rate'))} |"
            )
        lines.extend(
            [
                "",
                "### Shadow Feature Deltas",
                "",
                "Values are shadow selected candidate minus DP Top-1.",
                "",
                "| Feature | Mean Run Delta | Better-or-Equal Rate |",
                "| --- | ---: | ---: |",
            ]
        )
        for name, row in overall["feature_delta_shadow_minus_top1"].items():
            lines.append(
                "| "
                f"`{name}` | {_fmt(row.get('mean_of_run_mean_delta'))} | "
                f"{_fmt(row.get('mean_selected_better_or_equal_rate'))} |"
            )
    lines.append("")
    return "\n".join(lines)


def _bool_vector(value: Any, size: int, label: str) -> np.ndarray:
    arr = np.asarray(value, dtype=bool).reshape(-1)
    if arr.size != size:
        raise ValueError(f"{label} must have length {size}.")
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


def _weighted_mean(rows: list[dict[str, Any]], key: str) -> float | None:
    values = []
    weights = []
    for row in rows:
        value = _finite(row.get(key))
        if value is None:
            continue
        values.append(value)
        weights.append(int(row.get("records", 0)))
    if not values or not weights or sum(weights) <= 0:
        return None
    return float(np.average(np.asarray(values, dtype=np.float64), weights=weights))


def _conditional_rate(
    rows: list[dict[str, Any]],
    denominator_predicate: Any,
    numerator_predicate: Any,
) -> float | None:
    selected = [row for row in rows if denominator_predicate(row)]
    if not selected:
        return None
    return float(np.mean([bool(numerator_predicate(row)) for row in selected]))


def _summary(values: Any) -> dict[str, Any]:
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


def _run_summary_mean(summary: dict[str, Any]) -> float | None:
    return _finite(summary.get("mean"))


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
