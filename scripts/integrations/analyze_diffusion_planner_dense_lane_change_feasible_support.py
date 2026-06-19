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
EPS = 1e-12


@dataclass(frozen=True)
class SupportRule:
    name: str
    description: str
    allow_top1: bool
    only_top1: bool
    progress_loss_budget: float
    target_speed_loss_budget: float
    jerk_worse_budget: float
    lateral_worse_budget: float
    score_penalty_budget: float | None = None


RULES: tuple[SupportRule, ...] = (
    SupportRule(
        name="non_top1_strict",
        description=(
            "non-Top1 feasible alternative with lower DP-prior deviation and no "
            "planned-progress, target-speed, jerk, or lateral proxy regression"
        ),
        allow_top1=False,
        only_top1=False,
        progress_loss_budget=0.0,
        target_speed_loss_budget=0.0,
        jerk_worse_budget=0.0,
        lateral_worse_budget=0.0,
    ),
    SupportRule(
        name="non_top1_progress005_speed010_comfort_nonworse",
        description=(
            "non-Top1 feasible alternative with lower DP-prior deviation, at "
            "most 0.05 planned-progress loss, at most 0.10 m/s target-speed "
            "loss, and nonworse jerk/lateral proxies"
        ),
        allow_top1=False,
        only_top1=False,
        progress_loss_budget=0.05,
        target_speed_loss_budget=0.10,
        jerk_worse_budget=0.0,
        lateral_worse_budget=0.0,
    ),
    SupportRule(
        name="non_top1_progress010_speed020_comfort005",
        description=(
            "non-Top1 feasible alternative with lower DP-prior deviation, small "
            "planned-progress/target-speed loss, and 0.05 comfort-proxy slack"
        ),
        allow_top1=False,
        only_top1=False,
        progress_loss_budget=0.10,
        target_speed_loss_budget=0.20,
        jerk_worse_budget=0.05,
        lateral_worse_budget=0.05,
    ),
    SupportRule(
        name="any_progress005_speed010_comfort_nonworse",
        description=(
            "same as the 0.05/0.10 nonworse rule, but allows candidate0 to "
            "measure Top-1 dependence"
        ),
        allow_top1=True,
        only_top1=False,
        progress_loss_budget=0.05,
        target_speed_loss_budget=0.10,
        jerk_worse_budget=0.0,
        lateral_worse_budget=0.0,
    ),
    SupportRule(
        name="top1_progress005_speed010_comfort_nonworse",
        description=(
            "candidate0-only support under the same 0.05/0.10 nonworse budgets"
        ),
        allow_top1=True,
        only_top1=True,
        progress_loss_budget=0.05,
        target_speed_loss_budget=0.10,
        jerk_worse_budget=0.0,
        lateral_worse_budget=0.0,
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only dense lane-change feasible-tick support audit. It checks "
            "whether current DP candidate pools contain non-Top1 alternatives "
            "that improve DP-prior deviation without sacrificing current-tick "
            "completion and comfort proxies."
        )
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--min_bad_support_rate", type=float, default=0.25)
    parser.add_argument("--max_any_top1_chosen_rate", type=float, default=0.50)
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
        min_bad_support_rate=args.min_bad_support_rate,
        max_any_top1_chosen_rate=args.max_any_top1_chosen_rate,
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
    min_bad_support_rate: float = 0.25,
    max_any_top1_chosen_rate: float = 0.50,
) -> dict[str, Any]:
    comparison_data = json.loads(Path(comparison).read_text(encoding="utf-8"))
    return analyze_run_records(
        _load_run_records(root, comparison_data),
        label=label,
        root=str(root),
        comparison=str(comparison),
        min_bad_support_rate=min_bad_support_rate,
        max_any_top1_chosen_rate=max_any_top1_chosen_rate,
    )


def analyze_run_records(
    run_records: list[dict[str, Any]],
    *,
    label: str | None = None,
    root: str | None = None,
    comparison: str | None = None,
    min_bad_support_rate: float = 0.25,
    max_any_top1_chosen_rate: float = 0.50,
) -> dict[str, Any]:
    if not 0.0 <= min_bad_support_rate <= 1.0:
        raise ValueError("min_bad_support_rate must be in [0, 1].")
    if not 0.0 <= max_any_top1_chosen_rate <= 1.0:
        raise ValueError("max_any_top1_chosen_rate must be in [0, 1].")
    lane_change_runs = [item for item in run_records if _is_dense_lane_change(item)]
    bad_lane_change_runs = [
        item for item in lane_change_runs if _is_bad_deployable_run(item["delta"])
    ]
    rules = [
        _rule_report(rule, run_records, lane_change_runs, bad_lane_change_runs)
        for rule in RULES
    ]
    decision = _decision(
        rules,
        min_bad_support_rate=min_bad_support_rate,
        max_any_top1_chosen_rate=max_any_top1_chosen_rate,
    )
    return {
        "analysis": {
            "name": "dp_camp_dense_lane_change_feasible_support_v1",
            "label": label,
            "root": root,
            "comparison": comparison,
            "training": False,
            "online_selector_change": False,
            "closed_loop_outcome_labels_used": False,
            "future_outcome_leakage": False,
            "screen": {
                "min_bad_support_rate": float(min_bad_support_rate),
                "max_any_top1_chosen_rate": float(max_any_top1_chosen_rate),
            },
            "math_boundary": (
                "All support checks use fixed current-tick finite-candidate "
                "quantities: feasible_mask, candidate0 index, logged static "
                "selection, candidate_dp_prior_deviation_cost, planned progress "
                "or step reach, target speed, tracker jerk/lateral proxies, and "
                "selection score. Candidate outcomes are not read. This audit "
                "does not change DP, CAMP weights, atom schemas, or the affine "
                "score a_k^T w. It is not classical Benders decomposition."
            ),
        },
        "records": {
            "static_runs": len(run_records),
            "dense_lane_change_runs": len(lane_change_runs),
            "bad_dense_lane_change_runs": len(bad_lane_change_runs),
            "selection_records": int(sum(len(item["records"]) for item in run_records)),
            "dense_lane_change_selection_records": int(
                sum(len(item["records"]) for item in lane_change_runs)
            ),
            "bad_dense_lane_change_selection_records": int(
                sum(len(item["records"]) for item in bad_lane_change_runs)
            ),
        },
        "dense_lane_change_baseline": _baseline_summary(bad_lane_change_runs),
        "rules": rules,
        "ranked_rules": _rank_rules(rules),
        "final_decision": decision,
    }


def _load_run_records(
    root: Path,
    comparison_data: dict[str, Any],
) -> list[dict[str, Any]]:
    runs = comparison_data.get("runs")
    if not isinstance(runs, list):
        raise ValueError("benchmark comparison must contain a runs list.")
    static_runs = [
        run for run in runs if isinstance(run, dict) and run.get("variant") == STATIC_VARIANT
    ]
    if not static_runs:
        raise ValueError("benchmark comparison has no static runs.")
    log_by_output_dir = {str(path.parent): path for path in iter_selection_log_paths([root])}
    result: list[dict[str, Any]] = []
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
                "delta": _benchmark_deltas(static_run, baseline),
                "log_path": str(log_path),
                "records": _load_records(log_path),
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


def _load_record(raw: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(raw.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected = int(raw.get("selected_index"))
    if selected < 0 or selected >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    feasible = _bool_vector(raw.get("feasible_mask"), candidate_count, f"{label} feasible_mask")
    return {
        "candidate_count": candidate_count,
        "selected": selected,
        "feasible": feasible,
        "used_fallback": bool(raw.get("used_fallback", not feasible.any())),
        "features": {
            "planned_progress": _first_float_vector(
                raw,
                candidate_count,
                label,
                ("candidate_route_progress", "candidate_step_reach"),
            ),
            "target_speed": _first_float_vector(
                raw,
                candidate_count,
                label,
                ("candidate_perfect_tracker_target_speed_mps",),
                default=0.0,
            ),
            "dp_prior_deviation": _first_float_vector(
                raw,
                candidate_count,
                label,
                ("candidate_dp_prior_deviation_cost",),
            ),
            "tracker_jerk": _first_float_vector(
                raw,
                candidate_count,
                label,
                (
                    "candidate_perfect_tracker_jerk_magnitude_mps3",
                    "candidate_dp_prior_jerk_excess_cost",
                ),
                default=0.0,
            ),
            "tracker_lateral": _first_float_vector(
                raw,
                candidate_count,
                label,
                (
                    "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
                    "candidate_horizon_lateral_acceleration_cost",
                    "candidate_dp_prior_lateral_acceleration_excess_cost",
                ),
                default=0.0,
            ),
            "selection_score": _first_float_vector(
                raw,
                candidate_count,
                label,
                ("selection_scores",),
                default=0.0,
                allow_positive_infinity=True,
            ),
        },
    }


def _benchmark_deltas(
    static_run: dict[str, Any],
    baseline_run: dict[str, Any] | None,
) -> dict[str, float | None]:
    fields = (
        "safety_cost_v1",
        "route_completion_rate",
        "near_miss_rate",
        "lane_violation_rate",
        "p95_selection_latency_ms",
        "mean_jerk_magnitude_mps3",
    )
    result: dict[str, float | None] = {}
    for field in fields:
        static_value = _finite(static_run.get(field))
        baseline_value = None if baseline_run is None else _finite(baseline_run.get(field))
        result[field] = (
            float(static_value - baseline_value)
            if static_value is not None and baseline_value is not None
            else None
        )
    result["static_p95_selection_latency_ms"] = _finite(
        static_run.get("p95_selection_latency_ms")
    )
    return result


def _is_dense_lane_change(item: dict[str, Any]) -> bool:
    run = item["run"]
    route = str(run.get("route_name") or run.get("run_key") or run.get("output_dir") or "")
    npcs = _finite(run.get("max_npcs"))
    return "lane_change" in route and npcs is not None and float(npcs) >= 8.0


def _is_bad_deployable_run(delta: dict[str, float | None]) -> bool:
    safety = delta.get("safety_cost_v1")
    lane = delta.get("lane_violation_rate")
    completion = delta.get("route_completion_rate")
    latency = delta.get("static_p95_selection_latency_ms")
    return bool(
        (safety is not None and safety > 0.0)
        or (lane is not None and lane > 0.0)
        or (completion is not None and completion < -0.01)
        or (latency is not None and latency >= 100.0)
    )


def _baseline_summary(run_records: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [_record_row(record) for item in run_records for record in item["records"]]
    target = [row for row in rows if row["target_record"]]
    return {
        "records": len(rows),
        "feasible_records": int(sum(row["feasible_tick"] for row in rows)),
        "all_infeasible_records": int(sum(row["all_infeasible"] for row in rows)),
        "selected_non_top1_records": int(sum(row["selected_non_top1"] for row in rows)),
        "target_records": len(target),
        "target_record_rate": _rate(len(target), len(rows)),
        "mean_selected_dp_prior_delta_vs_top1": _mean(
            row["selected_dp_prior_delta_vs_top1"] for row in target
        ),
        "mean_selected_progress_delta_vs_top1": _mean(
            row["selected_progress_delta_vs_top1"] for row in target
        ),
        "mean_selected_target_speed_delta_vs_top1": _mean(
            row["selected_target_speed_delta_vs_top1"] for row in target
        ),
    }


def _rule_report(
    rule: SupportRule,
    all_runs: list[dict[str, Any]],
    lane_change_runs: list[dict[str, Any]],
    bad_lane_change_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "name": rule.name,
        "description": rule.description,
        "budgets": {
            "allow_top1": rule.allow_top1,
            "only_top1": rule.only_top1,
            "progress_loss_budget": rule.progress_loss_budget,
            "target_speed_loss_budget": rule.target_speed_loss_budget,
            "jerk_worse_budget": rule.jerk_worse_budget,
            "lateral_worse_budget": rule.lateral_worse_budget,
            "score_penalty_budget": rule.score_penalty_budget,
        },
        "overall": _support_metrics(rule, all_runs),
        "dense_lane_change": _support_metrics(rule, lane_change_runs),
        "bad_dense_lane_change": _support_metrics(rule, bad_lane_change_runs),
    }


def _support_metrics(
    rule: SupportRule,
    run_records: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = []
    for item in run_records:
        for record in item["records"]:
            base = _record_row(record)
            if not base["target_record"]:
                rows.append({**base, "supported": False, "choice": None})
                continue
            choice = _support_choice(rule, record)
            rows.append({**base, "supported": choice is not None, "choice": choice})
    target = [row for row in rows if row["target_record"]]
    supported = [row for row in target if row["supported"]]
    choices = [row["choice"] for row in supported if row["choice"] is not None]
    return {
        "records": len(rows),
        "target_records": len(target),
        "target_record_rate": _rate(len(target), len(rows)),
        "supported_records": len(supported),
        "support_rate": _rate(len(supported), len(target)),
        "chosen_top1_rate": _rate(
            sum(1 for choice in choices if choice["candidate"] == 0),
            len(choices),
        ),
        "chosen_non_top1_rate": _rate(
            sum(1 for choice in choices if choice["candidate"] not in (None, 0)),
            len(choices),
        ),
        "mean_dp_prior_gain": _mean(choice["dp_prior_gain"] for choice in choices),
        "mean_progress_loss": _mean(choice["progress_loss"] for choice in choices),
        "mean_target_speed_loss": _mean(choice["target_speed_loss"] for choice in choices),
        "mean_jerk_worse": _mean(choice["jerk_worse"] for choice in choices),
        "mean_lateral_worse": _mean(choice["lateral_worse"] for choice in choices),
        "mean_score_penalty": _mean(choice["score_penalty"] for choice in choices),
        "max_score_penalty": _max(choice["score_penalty"] for choice in choices),
    }


def _record_row(record: dict[str, Any]) -> dict[str, Any]:
    selected = int(record["selected"])
    feasible = record["feasible"]
    features = record["features"]
    all_infeasible = not bool(feasible.any())
    feasible_tick = not all_infeasible
    top1_feasible = bool(feasible.size and feasible[0])
    selected_non_top1 = selected != 0
    prior = features["dp_prior_deviation"]
    progress = features["planned_progress"]
    speed = features["target_speed"]
    selected_dp_prior_delta = float(prior[selected] - prior[0])
    target_record = bool(
        feasible_tick
        and top1_feasible
        and selected_non_top1
        and selected_dp_prior_delta > EPS
    )
    return {
        "all_infeasible": all_infeasible,
        "feasible_tick": feasible_tick,
        "top1_feasible": top1_feasible,
        "selected_non_top1": selected_non_top1,
        "target_record": target_record,
        "selected_dp_prior_delta_vs_top1": selected_dp_prior_delta,
        "selected_progress_delta_vs_top1": float(progress[selected] - progress[0]),
        "selected_target_speed_delta_vs_top1": float(speed[selected] - speed[0]),
    }


def _support_choice(rule: SupportRule, record: dict[str, Any]) -> dict[str, Any] | None:
    selected = int(record["selected"])
    feasible = record["feasible"]
    features = record["features"]
    candidates: list[dict[str, Any]] = []
    for idx in range(int(record["candidate_count"])):
        if idx == selected:
            continue
        if idx == 0 and not rule.allow_top1:
            continue
        if rule.only_top1 and idx != 0:
            continue
        if not bool(feasible[idx]):
            continue
        candidate = _candidate_delta(record, idx)
        if candidate["dp_prior_gain"] <= EPS:
            continue
        if candidate["progress_loss"] > rule.progress_loss_budget + EPS:
            continue
        if candidate["target_speed_loss"] > rule.target_speed_loss_budget + EPS:
            continue
        if candidate["jerk_worse"] > rule.jerk_worse_budget + EPS:
            continue
        if candidate["lateral_worse"] > rule.lateral_worse_budget + EPS:
            continue
        if (
            rule.score_penalty_budget is not None
            and candidate["score_penalty"] > rule.score_penalty_budget + EPS
        ):
            continue
        candidates.append(candidate)
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            item["candidate"] == 0,
            -item["dp_prior_gain"],
            item["progress_loss"],
            item["target_speed_loss"],
            item["jerk_worse"],
            item["lateral_worse"],
            item["score_penalty"],
            item["candidate"],
        )
    )
    return candidates[0]


def _candidate_delta(record: dict[str, Any], candidate: int) -> dict[str, Any]:
    selected = int(record["selected"])
    features = record["features"]
    prior = features["dp_prior_deviation"]
    progress = features["planned_progress"]
    speed = features["target_speed"]
    jerk = features["tracker_jerk"]
    lateral = features["tracker_lateral"]
    score = features["selection_score"]
    return {
        "candidate": int(candidate),
        "dp_prior_gain": float(prior[selected] - prior[candidate]),
        "progress_loss": max(float(progress[selected] - progress[candidate]), 0.0),
        "target_speed_loss": max(float(speed[selected] - speed[candidate]), 0.0),
        "jerk_worse": max(float(jerk[candidate] - jerk[selected]), 0.0),
        "lateral_worse": max(float(lateral[candidate] - lateral[selected]), 0.0),
        "score_penalty": max(float(score[candidate] - score[selected]), 0.0),
    }


def _rank_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for rule in rules:
        bad = rule["bad_dense_lane_change"]
        ranked.append(
            {
                "name": rule["name"],
                "bad_support_rate": bad["support_rate"],
                "bad_chosen_top1_rate": bad["chosen_top1_rate"],
                "bad_mean_score_penalty": bad["mean_score_penalty"],
                "bad_mean_dp_prior_gain": bad["mean_dp_prior_gain"],
                "overall_support_rate": rule["overall"]["support_rate"],
                "overall_chosen_top1_rate": rule["overall"]["chosen_top1_rate"],
            }
        )
    return sorted(
        ranked,
        key=lambda row: (
            -(row["bad_support_rate"] or 0.0),
            row["bad_chosen_top1_rate"] or 0.0,
            row["bad_mean_score_penalty"] or 0.0,
        ),
    )


def _decision(
    rules: list[dict[str, Any]],
    *,
    min_bad_support_rate: float,
    max_any_top1_chosen_rate: float,
) -> dict[str, Any]:
    non_top1_rules = [
        rule
        for rule in rules
        if not rule["budgets"]["allow_top1"] and not rule["budgets"]["only_top1"]
    ]
    passing_non_top1 = [
        rule
        for rule in non_top1_rules
        if (rule["bad_dense_lane_change"]["support_rate"] or 0.0)
        >= min_bad_support_rate
    ]
    any_rules = [rule for rule in rules if rule["budgets"]["allow_top1"]]
    top1_dependent = [
        rule
        for rule in any_rules
        if (rule["bad_dense_lane_change"]["support_rate"] or 0.0)
        >= min_bad_support_rate
        and (rule["bad_dense_lane_change"]["chosen_top1_rate"] or 0.0)
        > max_any_top1_chosen_rate
    ]
    status = (
        "non_top1_candidate_support_present"
        if passing_non_top1
        else "non_top1_candidate_support_insufficient"
    )
    conclusions = []
    if passing_non_top1:
        conclusions.append(
            "Bad dense lane-change feasible ticks contain non-Top1 alternatives "
            "that improve DP-prior deviation while preserving current-tick "
            "completion/comfort proxies under at least one predeclared budget."
        )
    else:
        conclusions.append(
            "Bad dense lane-change feasible ticks do not contain enough non-Top1 "
            "support under the predeclared completion/comfort budgets."
        )
    if top1_dependent:
        conclusions.append(
            "Support that allows candidate0 is mostly Top-1 dependent, so a "
            "hard preservation filter would repeat the rejected Top-1-collapse path."
        )
    conclusions.append(
        "This support audit is not a selector and cannot authorize smoke, Full36, "
        "formal seeds, or retraining by itself."
    )
    return {
        "status": status,
        "passing_non_top1_rules": [rule["name"] for rule in passing_non_top1],
        "top1_dependent_rules": [rule["name"] for rule in top1_dependent],
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "conclusions": conclusions,
        "next_step": (
            "If non-Top1 support is present, run a separate outcome-labeled "
            "offline selector screen on the supported rule family. If support is "
            "insufficient, reject finite filters and treat the remaining issue "
            "as schema/calibration or candidate-generation support."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Dense Lane-Change Feasible-Tick Support Audit",
        "",
        "This report is read-only. It does not run DP, train CAMP, change online selection, run Full36, or use formal seeds.",
        "",
        "## Verdict",
        "",
        f"- Status: `{report['final_decision']['status']}`",
        f"- Online selector authorized: `{report['final_decision']['online_selector_authorized']}`",
        f"- CAMP retraining authorized: `{report['final_decision']['camp_retraining_authorized']}`",
        "",
        "## Records",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in report["records"].items():
        lines.append(f"| `{key}` | {_fmt(value)} |")
    lines.extend(
        [
            "",
            "## Bad Dense Lane-Change Baseline",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ]
    )
    for key, value in report["dense_lane_change_baseline"].items():
        lines.append(f"| `{key}` | {_fmt(value)} |")
    lines.extend(
        [
            "",
            "## Rule Support",
            "",
            "| Rule | Bad support | Bad Top1 chosen | Bad score penalty | Bad DP-prior gain | Overall support | Overall Top1 chosen |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for rule in report["ranked_rules"]:
        lines.append(
            f"| `{rule['name']}` | "
            f"{_fmt(rule['bad_support_rate'])} | "
            f"{_fmt(rule['bad_chosen_top1_rate'])} | "
            f"{_fmt(rule['bad_mean_score_penalty'])} | "
            f"{_fmt(rule['bad_mean_dp_prior_gain'])} | "
            f"{_fmt(rule['overall_support_rate'])} | "
            f"{_fmt(rule['overall_chosen_top1_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Mechanism",
            "",
        ]
    )
    for item in report["final_decision"]["conclusions"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            f"Next step: {report['final_decision']['next_step']}",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _bool_vector(value: Any, length: int, label: str) -> np.ndarray:
    arr = np.asarray(value, dtype=bool).reshape(-1)
    if arr.shape != (length,):
        raise ValueError(f"{label} must have shape [{length}].")
    return arr


def _first_float_vector(
    raw: dict[str, Any],
    length: int,
    label: str,
    keys: tuple[str, ...],
    *,
    default: float | None = None,
    allow_positive_infinity: bool = False,
) -> np.ndarray:
    for key in keys:
        if raw.get(key) is None:
            continue
        arr = np.asarray(raw.get(key), dtype=np.float64).reshape(-1)
        if arr.shape != (length,):
            raise ValueError(f"{label} {key} must have shape [{length}].")
        if allow_positive_infinity:
            valid = np.isfinite(arr) | np.isposinf(arr)
        else:
            valid = np.isfinite(arr)
        if not bool(np.all(valid)):
            raise ValueError(f"{label} {key} must be finite.")
        return arr
    if default is None:
        raise ValueError(f"{label} requires one of {', '.join(keys)}.")
    return np.full(length, float(default), dtype=np.float64)


def _finite(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def _mean(values: Any) -> float | None:
    arr = np.asarray([value for value in values if value is not None], dtype=np.float64)
    if arr.size == 0:
        return None
    return float(np.mean(arr))


def _max(values: Any) -> float | None:
    arr = np.asarray([value for value in values if value is not None], dtype=np.float64)
    if arr.size == 0:
        return None
    return float(np.max(arr))


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return float(numerator) / float(denominator)


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


if __name__ == "__main__":
    main()
