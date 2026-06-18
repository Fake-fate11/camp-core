#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
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

PRIOR_THRESHOLDS = (0.0, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0)
SPEED_LOSS_THRESHOLDS = (0.0, 0.005, 0.01, 0.02, 0.05)
PROGRESS_GAIN_CAPS = (0.0, 0.1, 0.25, 0.5, 1.0)

FEATURES: tuple[tuple[str, str, str], ...] = (
    ("route_progress", "candidate_route_progress", "higher"),
    ("target_speed", "candidate_perfect_tracker_target_speed_mps", "higher"),
    ("tail_average_speed", "candidate_perfect_tracker_tail_average_speed_mps", "higher"),
    ("dp_prior_deviation", "candidate_dp_prior_deviation_cost", "lower"),
    ("dp_prior_jerk_excess", "candidate_dp_prior_jerk_excess_cost", "lower"),
    ("dp_prior_lateral_excess", "candidate_dp_prior_lateral_acceleration_excess_cost", "lower"),
    ("tracker_jerk", "candidate_perfect_tracker_jerk_magnitude_mps3", "lower"),
    ("tracker_lateral", "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2", "lower"),
    ("selection_score", "selection_scores", "lower"),
)

BENCHMARK_DELTA_FIELDS = (
    "safety_cost_v1",
    "route_completion_rate",
    "near_miss_rate",
    "lane_violation_rate",
    "mean_jerk_magnitude_mps3",
)


@dataclass(frozen=True)
class Rule:
    name: str
    description: str
    prior_threshold: float | None = None
    speed_loss_threshold: float | None = None
    progress_gain_cap: float | None = None
    require_prior: bool = False
    require_speed_loss: bool = False
    require_progress_cap: bool = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Outcome-free feasible-tick Top-1 preservation shadow sweep. "
            "Rules use fixed current-tick finite-candidate diagnostics only."
        )
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--max_change_rate", type=float, default=0.35)
    parser.add_argument("--max_top1_selected_rate", type=float, default=0.50)
    parser.add_argument("--min_bad_run_changed_rate", type=float, default=0.25)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    comparison = args.comparison or args.root / "benchmark_comparison.json"
    report = analyze(
        args.root,
        comparison=comparison,
        label=args.label,
        max_change_rate=args.max_change_rate,
        max_top1_selected_rate=args.max_top1_selected_rate,
        min_bad_run_changed_rate=args.min_bad_run_changed_rate,
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
    root: Path,
    *,
    comparison: Path,
    label: str | None = None,
    max_change_rate: float = 0.35,
    max_top1_selected_rate: float = 0.50,
    min_bad_run_changed_rate: float = 0.25,
) -> dict[str, Any]:
    if not 0.0 <= max_change_rate <= 1.0:
        raise ValueError("max_change_rate must be in [0, 1].")
    if not 0.0 <= max_top1_selected_rate <= 1.0:
        raise ValueError("max_top1_selected_rate must be in [0, 1].")
    if not 0.0 <= min_bad_run_changed_rate <= 1.0:
        raise ValueError("min_bad_run_changed_rate must be in [0, 1].")

    comparison_data = json.loads(Path(comparison).read_text(encoding="utf-8"))
    run_records = _load_run_records(root, comparison_data)
    rules = _rules()
    rule_reports = [_rule_report(rule, run_records) for rule in rules]
    ranked = _rank_candidates(
        rule_reports,
        max_change_rate=max_change_rate,
        max_top1_selected_rate=max_top1_selected_rate,
        min_bad_run_changed_rate=min_bad_run_changed_rate,
    )
    return {
        "analysis": {
            "name": "dp_camp_feasible_top1_shadow_sweep_v1",
            "label": label,
            "root": str(root),
            "comparison": str(comparison),
            "training": False,
            "online_selector_change": False,
            "closed_loop_outcome_labels_used": False,
            "future_outcome_leakage": False,
            "rules_evaluated": len(rule_reports),
            "screen": {
                "max_change_rate": float(max_change_rate),
                "max_top1_selected_rate": float(max_top1_selected_rate),
                "min_bad_run_changed_rate": float(min_bad_run_changed_rate),
            },
            "math_boundary": (
                "Each rule preserves DP Top-1 only on feasible current-tick "
                "records where logged static CAMP selected a nonzero candidate "
                "and fixed candidate diagnostics meet threshold conditions. "
                "The diagnostics are candidate_dp_prior_deviation_cost, "
                "candidate_perfect_tracker_target_speed_mps, and "
                "candidate_route_progress. No future outcomes, DP generation, "
                "tracker dynamics, CAMP weights, or affine score definitions "
                "are changed. This is a finite-candidate shadow sweep, not "
                "Benders decomposition."
            ),
        },
        "records": {
            "static_runs": len(run_records),
            "selection_records": int(sum(len(item["records"]) for item in run_records)),
        },
        "ranked_candidates": ranked,
        "rules": rule_reports,
    }


def _load_run_records(root: Path, comparison_data: dict[str, Any]) -> list[dict[str, Any]]:
    runs = comparison_data.get("runs")
    if not isinstance(runs, list):
        raise ValueError("benchmark comparison must contain a runs list.")
    static_runs = [
        run for run in runs if isinstance(run, dict) and run.get("variant") == STATIC_VARIANT
    ]
    if not static_runs:
        raise ValueError("benchmark comparison has no static runs.")
    log_by_output_dir = {str(path.parent): path for path in iter_selection_log_paths([root])}
    result = []
    for static_run in static_runs:
        output_dir = str(static_run.get("output_dir", ""))
        log_path = log_by_output_dir.get(output_dir)
        if log_path is None:
            raise ValueError(f"Missing static selection log for {output_dir}.")
        baseline = _baseline_for_run(runs, static_run)
        result.append(
            {
                "run": static_run,
                "baseline": baseline,
                "log_path": str(log_path),
                "records": _load_records(log_path),
                "benchmark_delta_static_minus_top1": _benchmark_deltas(static_run, baseline),
            }
        )
    return result


def _baseline_for_run(runs: list[Any], static_run: dict[str, Any]) -> dict[str, Any] | None:
    run_key = static_run.get("run_key")
    for run in runs:
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
        "features": features,
    }


def _rules() -> list[Rule]:
    rules = [
        Rule(name="static_baseline", description="retain logged static CAMP selection"),
    ]
    for prior in PRIOR_THRESHOLDS:
        rules.append(
            Rule(
                name=f"prior_ge_{_tag(prior)}",
                description=f"preserve Top-1 when DP-prior deviation loss >= {prior:g}",
                prior_threshold=prior,
                require_prior=True,
            )
        )
    for speed in SPEED_LOSS_THRESHOLDS:
        rules.append(
            Rule(
                name=f"speed_loss_ge_{_tag(speed)}",
                description=f"preserve Top-1 when target-speed loss >= {speed:g} m/s",
                speed_loss_threshold=speed,
                require_speed_loss=True,
            )
        )
    for prior in (0.0, 0.25, 0.5, 1.0, 2.0):
        rules.append(
            Rule(
                name=f"prior_ge_{_tag(prior)}_and_speed_loss_ge_0",
                description=(
                    "preserve Top-1 when DP-prior deviation is large and "
                    "static target speed is below Top-1"
                ),
                prior_threshold=prior,
                speed_loss_threshold=0.0,
                require_prior=True,
                require_speed_loss=True,
            )
        )
    for prior in (0.25, 0.5, 1.0, 2.0):
        for progress_cap in PROGRESS_GAIN_CAPS:
            rules.append(
                Rule(
                    name=f"prior_ge_{_tag(prior)}_and_progress_gain_le_{_tag(progress_cap)}",
                    description=(
                        "preserve Top-1 when DP-prior deviation is large and "
                        "the static branch has limited route-progress gain"
                    ),
                    prior_threshold=prior,
                    progress_gain_cap=progress_cap,
                    require_prior=True,
                    require_progress_cap=True,
                )
            )
    return rules


def _rule_report(rule: Rule, run_records: list[dict[str, Any]]) -> dict[str, Any]:
    run_reports = [_run_report(rule, item) for item in run_records]
    return {
        "name": rule.name,
        "description": rule.description,
        "thresholds": {
            "prior_threshold": rule.prior_threshold,
            "speed_loss_threshold": rule.speed_loss_threshold,
            "progress_gain_cap": rule.progress_gain_cap,
        },
        "overall": _aggregate_runs(run_reports),
        "runs": sorted(run_reports, key=_run_sort_key),
    }


def _run_report(rule: Rule, item: dict[str, Any]) -> dict[str, Any]:
    rows = [_shadow_row(rule, record) for record in item["records"]]
    return {
        "route_name": item["run"].get("route_name"),
        "max_npcs": item["run"].get("max_npcs"),
        "traffic_lights": item["run"].get("traffic_lights"),
        "benchmark_delta_static_minus_top1": item["benchmark_delta_static_minus_top1"],
        "bad_run": _is_bad_run(item["benchmark_delta_static_minus_top1"]),
        "records": len(rows),
        "changed_from_static_rate": _mean(row["shadow_selected"] != row["static_selected"] for row in rows),
        "top1_selected_rate": _mean(row["shadow_selected"] == 0 for row in rows),
        "static_top1_selected_rate": _mean(row["static_selected"] == 0 for row in rows),
        "prior_trigger_rate": _mean("prior" in row["reasons"] for row in rows),
        "speed_trigger_rate": _mean("speed" in row["reasons"] for row in rows),
        "progress_cap_trigger_rate": _mean("progress_cap" in row["reasons"] for row in rows),
        "score_penalty_shadow_minus_static": _summary(row["score_penalty"] for row in rows),
        "feature_delta_shadow_minus_top1": _feature_delta_summary(rows, "shadow_selected"),
    }


def _shadow_row(rule: Rule, record: dict[str, Any]) -> dict[str, Any]:
    static_selected = int(record["selected"])
    shadow_selected = static_selected
    reasons: list[str] = []
    feasible = record["feasible"]
    candidate0_feasible = bool(feasible.size and feasible[0])
    if candidate0_feasible and static_selected != 0:
        if _rule_matches(rule, record):
            shadow_selected = 0
            if rule.require_prior:
                reasons.append("prior")
            if rule.require_speed_loss:
                reasons.append("speed")
            if rule.require_progress_cap:
                reasons.append("progress_cap")
    score = record["features"].get("selection_score")
    score_penalty = None
    if score is not None:
        score_penalty = float(score[shadow_selected] - score[static_selected])
    return {
        "static_selected": static_selected,
        "shadow_selected": int(shadow_selected),
        "reasons": reasons,
        "features": record["features"],
        "score_penalty": score_penalty,
    }


def _rule_matches(rule: Rule, record: dict[str, Any]) -> bool:
    if rule.name == "static_baseline":
        return False
    selected = int(record["selected"])
    features = record["features"]
    if rule.require_prior:
        prior = features.get("dp_prior_deviation")
        if prior is None:
            return False
        if prior[selected] - prior[0] < float(rule.prior_threshold or 0.0) - TOL:
            return False
    if rule.require_speed_loss:
        speed = features.get("target_speed")
        if speed is None:
            return False
        if speed[0] - speed[selected] < float(rule.speed_loss_threshold or 0.0) - TOL:
            return False
    if rule.require_progress_cap:
        progress = features.get("route_progress")
        if progress is None:
            return False
        if progress[selected] - progress[0] > float(rule.progress_gain_cap or 0.0) + TOL:
            return False
    return True


def _benchmark_deltas(static_run: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any]:
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


def _is_bad_run(delta: dict[str, Any]) -> bool:
    safety = _finite(delta.get("safety_cost_v1"))
    completion = _finite(delta.get("route_completion_rate"))
    lane = _finite(delta.get("lane_violation_rate"))
    return bool(
        (safety is not None and safety > 0.05)
        or (completion is not None and completion < -0.01)
        or (lane is not None and lane > 0.0)
    )


def _aggregate_runs(run_reports: list[dict[str, Any]]) -> dict[str, Any]:
    bad_runs = [row for row in run_reports if row["bad_run"]]
    return {
        "changed_from_static_rate": _weighted_mean(run_reports, "changed_from_static_rate"),
        "top1_selected_rate": _weighted_mean(run_reports, "top1_selected_rate"),
        "static_top1_selected_rate": _weighted_mean(run_reports, "static_top1_selected_rate"),
        "bad_run_changed_rate": _weighted_mean(bad_runs, "changed_from_static_rate"),
        "bad_run_top1_selected_rate": _weighted_mean(bad_runs, "top1_selected_rate"),
        "prior_trigger_rate": _weighted_mean(run_reports, "prior_trigger_rate"),
        "speed_trigger_rate": _weighted_mean(run_reports, "speed_trigger_rate"),
        "progress_cap_trigger_rate": _weighted_mean(run_reports, "progress_cap_trigger_rate"),
        "score_penalty_shadow_minus_static": _summary(
            _run_summary_mean(row["score_penalty_shadow_minus_static"])
            for row in run_reports
        ),
        "feature_delta_shadow_minus_top1": _aggregate_feature_delta(run_reports),
    }


def _rank_candidates(
    rule_reports: list[dict[str, Any]],
    *,
    max_change_rate: float,
    max_top1_selected_rate: float,
    min_bad_run_changed_rate: float,
) -> list[dict[str, Any]]:
    candidates = []
    for report in rule_reports:
        if report["name"] == "static_baseline":
            continue
        overall = report["overall"]
        change = _finite(overall.get("changed_from_static_rate"))
        top1 = _finite(overall.get("top1_selected_rate"))
        bad_change = _finite(overall.get("bad_run_changed_rate"))
        if change is None or top1 is None or bad_change is None:
            continue
        passed = (
            change <= max_change_rate + TOL
            and top1 <= max_top1_selected_rate + TOL
            and bad_change >= min_bad_run_changed_rate - TOL
        )
        prior = overall["feature_delta_shadow_minus_top1"].get("dp_prior_deviation", {})
        completion_proxy = overall["feature_delta_shadow_minus_top1"].get("target_speed", {})
        candidates.append(
            {
                "name": report["name"],
                "passed_shadow_screen": bool(passed),
                "changed_from_static_rate": change,
                "top1_selected_rate": top1,
                "bad_run_changed_rate": bad_change,
                "score_penalty_mean": _finite(
                    overall["score_penalty_shadow_minus_static"].get("mean")
                ),
                "dp_prior_deviation_mean_delta": _finite(
                    prior.get("mean_of_run_mean_delta")
                ),
                "target_speed_mean_delta": _finite(
                    completion_proxy.get("mean_of_run_mean_delta")
                ),
            }
        )
    return sorted(
        candidates,
        key=lambda row: (
            not row["passed_shadow_screen"],
            -float(row["bad_run_changed_rate"]),
            float(row["changed_from_static_rate"]),
            abs(float(row["score_penalty_mean"] or 0.0)),
        ),
    )


def _feature_delta_summary(rows: list[dict[str, Any]], selected_key: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, _, direction in FEATURES:
        deltas = []
        better = []
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


def _aggregate_feature_delta(run_reports: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, _, _ in FEATURES:
        means = []
        rates = []
        for row in run_reports:
            feature = row["feature_delta_shadow_minus_top1"].get(name)
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


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP-CAMP Feasible Top-1 Shadow Sweep",
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
            "## Ranked Candidates",
            "",
            "| Rule | Pass | Changed | Top1 Rate | Bad-Run Changed | Score Penalty | DP-Prior Delta | Target-Speed Delta |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["ranked_candidates"][:20]:
        lines.append(
            "| "
            f"`{row['name']}` | `{row['passed_shadow_screen']}` | "
            f"{_fmt(row.get('changed_from_static_rate'))} | "
            f"{_fmt(row.get('top1_selected_rate'))} | "
            f"{_fmt(row.get('bad_run_changed_rate'))} | "
            f"{_fmt(row.get('score_penalty_mean'))} | "
            f"{_fmt(row.get('dp_prior_deviation_mean_delta'))} | "
            f"{_fmt(row.get('target_speed_mean_delta'))} |"
        )
    lines.extend(
        [
            "",
            "## Rule Details",
            "",
            "| Rule | Changed | Top1 Rate | Bad-Run Changed | Prior Trigger | Speed Trigger | Progress Trigger |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for rule in report["rules"]:
        overall = rule["overall"]
        lines.append(
            "| "
            f"`{rule['name']}` | "
            f"{_fmt(overall.get('changed_from_static_rate'))} | "
            f"{_fmt(overall.get('top1_selected_rate'))} | "
            f"{_fmt(overall.get('bad_run_changed_rate'))} | "
            f"{_fmt(overall.get('prior_trigger_rate'))} | "
            f"{_fmt(overall.get('speed_trigger_rate'))} | "
            f"{_fmt(overall.get('progress_cap_trigger_rate'))} |"
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


def _tag(value: float) -> str:
    return f"{value:g}".replace(".", "p").replace("-", "m")


def _run_sort_key(row: dict[str, Any]) -> tuple[str, int, str]:
    return (
        str(row.get("route_name")),
        int(row.get("max_npcs") or 0),
        str(row.get("traffic_lights")),
    )


if __name__ == "__main__":
    main()
