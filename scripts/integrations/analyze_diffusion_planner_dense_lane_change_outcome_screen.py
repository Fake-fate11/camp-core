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
    parse_selection_log_metadata,
)
from scripts.integrations.analyze_diffusion_planner_dp_prior_atom_candidate import (  # noqa: E402
    BOOL_FIELDS,
    EPS,
    _candidate_safety_cost,
    _conditional_rate,
    _fmt,
    _nonnegative_float,
    _paired_summary,
    _summary,
    _vector,
)


FORMAL_SEEDS = {11, 12, 13}


@dataclass(frozen=True)
class LooseRuleConfig:
    progress_loss_budget: float = 0.10
    target_speed_loss_budget_mps: float = 0.20
    jerk_worse_budget: float = 0.05
    lateral_worse_budget: float = 0.05
    min_dense_support_rate: float = 0.25
    max_override_top1_rate: float = 0.0
    min_progress_delta_ci_low: float = -0.05
    min_hard_nonworse_rate: float = 0.99


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Outcome-labeled offline screen for the dense lane-change loose "
            "non-Top1 support rule. Runtime predicates use current-tick fixed "
            "candidate features; candidate outcomes are posterior labels only."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--bootstrap_resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--progress_loss_budget", type=float, default=0.10)
    parser.add_argument("--target_speed_loss_budget_mps", type=float, default=0.20)
    parser.add_argument("--jerk_worse_budget", type=float, default=0.05)
    parser.add_argument("--lateral_worse_budget", type=float, default=0.05)
    parser.add_argument("--min_dense_support_rate", type=float, default=0.25)
    parser.add_argument("--max_override_top1_rate", type=float, default=0.0)
    parser.add_argument("--min_progress_delta_ci_low", type=float, default=-0.05)
    parser.add_argument("--min_hard_nonworse_rate", type=float, default=0.99)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(
        paths,
        label=args.label,
        config=LooseRuleConfig(
            progress_loss_budget=args.progress_loss_budget,
            target_speed_loss_budget_mps=args.target_speed_loss_budget_mps,
            jerk_worse_budget=args.jerk_worse_budget,
            lateral_worse_budget=args.lateral_worse_budget,
            min_dense_support_rate=args.min_dense_support_rate,
            max_override_top1_rate=args.max_override_top1_rate,
            min_progress_delta_ci_low=args.min_progress_delta_ci_low,
            min_hard_nonworse_rate=args.min_hard_nonworse_rate,
        ),
        bootstrap_resamples=args.bootstrap_resamples,
        seed=args.seed,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
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
    config: LooseRuleConfig = LooseRuleConfig(),
    bootstrap_resamples: int = 5000,
    seed: int = 12345,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    _validate_config(config)
    records = _load_records(paths, fail_on_formal_seeds=fail_on_formal_seeds)
    if not records:
        raise ValueError("No outcome-labeled records were found.")
    return analyze_records(
        records,
        label=label,
        config=config,
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    records: list[dict[str, Any]],
    *,
    label: str | None = None,
    config: LooseRuleConfig = LooseRuleConfig(),
    bootstrap_resamples: int = 5000,
    seed: int = 12345,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    _validate_config(config)
    if not records:
        raise ValueError("At least one record is required.")
    choices = [_choice(record, config) for record in records]
    chosen = np.asarray([choice["chosen"] for choice in choices], dtype=np.int64)
    selected = np.asarray([record["selected"] for record in records], dtype=np.int64)
    top1 = np.zeros(len(records), dtype=np.int64)
    dense_mask = np.asarray([_is_dense_lane_change(record) for record in records], dtype=bool)
    target_mask = np.asarray([choice["target_record"] for choice in choices], dtype=bool)
    changed_mask = chosen != selected
    formal_seed_records = int(
        sum(record["context"].get("formal_seed", False) for record in records)
    )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")
    dense_records = _subset(records, dense_mask)
    dense_chosen = chosen[dense_mask]
    dense_selected = selected[dense_mask]
    dense_top1 = top1[dense_mask]
    return {
        "analysis": {
            "name": "dense_lane_change_loose_rule_outcome_screen_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "future_outcome_leakage": (
                "candidate outcomes are used only after deterministic selection "
                "for posterior SafetyCost evaluation; runtime predicates use "
                "current-tick fixed candidate features only"
            ),
            "rule": {
                "name": "non_top1_progress010_speed020_comfort005",
                "definition": (
                    "on dense lane-change feasible target ticks, choose a "
                    "non-Top1 feasible candidate with lower DP-prior deviation "
                    "than the logged selection, progress loss <=0.10, target "
                    "speed loss <=0.20 m/s, and jerk/lateral proxy regression "
                    "<=0.05; otherwise keep logged selection"
                ),
                "config": config.__dict__,
            },
            "math_boundary": (
                "All rule predicates are fixed current-tick finite-candidate "
                "constants. If any predicate is atomized later, the CAMP score "
                "must remain affine a_k^T w and the simplex/CVaR/L2 robust "
                "master remains convex. This is a finite-candidate offline "
                "screen, not classical Benders decomposition."
            ),
            "bootstrap_resamples": int(bootstrap_resamples),
            "seed": int(seed),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "records": _record_summary(records, choices),
        "overall": _metrics(
            records,
            chosen,
            selected,
            top1,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "dense_lane_change": _metrics(
            dense_records,
            dense_chosen,
            dense_selected,
            dense_top1,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "changed_records": _metrics(
            _subset(records, changed_mask),
            chosen[changed_mask],
            selected[changed_mask],
            top1[changed_mask],
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "target_records": _metrics(
            _subset(records, target_mask),
            chosen[target_mask],
            selected[target_mask],
            top1[target_mask],
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "mechanism": _mechanism(records, choices),
        "final_decision": _decision(
            records,
            choices,
            dense_records,
            dense_chosen,
            dense_selected,
            dense_top1,
            config=config,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
    }


def _load_records(
    paths: list[Path],
    *,
    fail_on_formal_seeds: bool,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for log_path in iter_selection_log_paths(paths):
        metadata = parse_selection_log_metadata(log_path)
        formal_seed = metadata.seed in FORMAL_SEEDS
        if formal_seed and fail_on_formal_seeds:
            raise ValueError(f"Formal seed log is forbidden: {log_path}")
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list):
            raise ValueError(f"{log_path} must contain a JSON list.")
        for record_index, raw in enumerate(payload):
            try:
                record = _load_record(raw, f"{log_path} record {record_index}")
            except ValueError as exc:
                if "candidate_closed_loop_outcomes" in str(exc):
                    continue
                raise
            record["context"] = {
                "log_path": str(log_path),
                "record_index": int(record_index),
                "route": metadata.route,
                "seed": metadata.seed,
                "formal_seed": formal_seed,
                "npc_count": metadata.npc_count,
                "traffic_light": metadata.traffic_light,
                "mode": metadata.mode,
            }
            records.append(record)
    return records


def _load_record(raw: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(raw.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected = int(raw.get("selected_index"))
    if selected < 0 or selected >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    outcomes = raw.get("candidate_closed_loop_outcomes")
    if not isinstance(outcomes, list) or len(outcomes) != candidate_count:
        raise ValueError(f"{label} requires complete candidate_closed_loop_outcomes.")
    feasible = np.asarray(raw.get("feasible_mask"), dtype=bool).reshape(-1)
    if feasible.shape != (candidate_count,):
        raise ValueError(f"{label} feasible_mask must have shape [{candidate_count}].")
    planned_progress = _first_vector(
        raw,
        candidate_count,
        label,
        ("candidate_route_progress", "candidate_step_reach"),
    )
    target_speed = _first_vector(
        raw,
        candidate_count,
        label,
        ("candidate_perfect_tracker_target_speed_mps",),
        default=0.0,
    )
    dp_prior = _vector(
        raw.get("candidate_dp_prior_deviation_cost"),
        candidate_count,
        f"{label} candidate_dp_prior_deviation_cost",
    )
    jerk = _first_vector(
        raw,
        candidate_count,
        label,
        (
            "candidate_perfect_tracker_jerk_magnitude_mps3",
            "candidate_dp_prior_jerk_excess_cost",
        ),
        default=0.0,
    )
    lateral = _first_vector(
        raw,
        candidate_count,
        label,
        (
            "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
            "candidate_horizon_lateral_acceleration_cost",
            "candidate_dp_prior_lateral_acceleration_excess_cost",
        ),
        default=0.0,
    )
    scores = _first_vector(
        raw,
        candidate_count,
        label,
        ("selection_scores",),
        default=0.0,
        allow_positive_infinity=True,
    )
    costs = np.asarray(
        [_candidate_safety_cost(outcome, raw, idx) for idx, outcome in enumerate(outcomes)],
        dtype=np.float64,
    )
    outcome_progress = np.asarray(
        [_nonnegative_float(outcome, "progress_m") for outcome in outcomes],
        dtype=np.float64,
    )
    return {
        "selected": selected,
        "candidate_count": candidate_count,
        "feasible": feasible,
        "planned_progress": planned_progress,
        "target_speed": target_speed,
        "dp_prior_deviation": dp_prior,
        "tracker_jerk": jerk,
        "tracker_lateral": lateral,
        "scores": scores,
        "safety_cost": costs,
        "outcome_progress": outcome_progress,
        "outcomes": outcomes,
        "context": {},
    }


def _choice(record: dict[str, Any], config: LooseRuleConfig) -> dict[str, Any]:
    selected = int(record["selected"])
    feasible = record["feasible"]
    top1_feasible = bool(feasible.size and feasible[0])
    all_infeasible = not bool(feasible.any())
    selected_non_top1 = selected != 0
    selected_prior_delta = float(
        record["dp_prior_deviation"][selected] - record["dp_prior_deviation"][0]
    )
    target_record = bool(
        _is_dense_lane_change(record)
        and not all_infeasible
        and top1_feasible
        and selected_non_top1
        and selected_prior_delta > EPS
    )
    if not target_record:
        return {
            "chosen": selected,
            "changed": False,
            "target_record": False,
            "support": False,
            "candidate": None,
            "reason": "not_target_record",
        }
    candidates = []
    for idx in range(int(record["candidate_count"])):
        if idx == selected or idx == 0:
            continue
        if not bool(feasible[idx]):
            continue
        delta = _candidate_delta(record, idx)
        if delta["dp_prior_gain"] <= EPS:
            continue
        if delta["progress_loss"] > config.progress_loss_budget + EPS:
            continue
        if delta["target_speed_loss"] > config.target_speed_loss_budget_mps + EPS:
            continue
        if delta["jerk_worse"] > config.jerk_worse_budget + EPS:
            continue
        if delta["lateral_worse"] > config.lateral_worse_budget + EPS:
            continue
        candidates.append(delta)
    if not candidates:
        return {
            "chosen": selected,
            "changed": False,
            "target_record": True,
            "support": False,
            "candidate": None,
            "reason": "no_supported_non_top1_candidate",
        }
    candidates.sort(
        key=lambda item: (
            -item["dp_prior_gain"],
            item["progress_loss"],
            item["target_speed_loss"],
            item["jerk_worse"],
            item["lateral_worse"],
            item["score_penalty"],
            item["candidate"],
        )
    )
    candidate = candidates[0]
    return {
        "chosen": int(candidate["candidate"]),
        "changed": True,
        "target_record": True,
        "support": True,
        "candidate": candidate,
        "reason": "selected_supported_non_top1_candidate",
    }


def _candidate_delta(record: dict[str, Any], candidate: int) -> dict[str, Any]:
    selected = int(record["selected"])
    return {
        "candidate": int(candidate),
        "dp_prior_gain": float(
            record["dp_prior_deviation"][selected]
            - record["dp_prior_deviation"][candidate]
        ),
        "progress_loss": max(
            float(record["planned_progress"][selected] - record["planned_progress"][candidate]),
            0.0,
        ),
        "target_speed_loss": max(
            float(record["target_speed"][selected] - record["target_speed"][candidate]),
            0.0,
        ),
        "jerk_worse": max(
            float(record["tracker_jerk"][candidate] - record["tracker_jerk"][selected]),
            0.0,
        ),
        "lateral_worse": max(
            float(record["tracker_lateral"][candidate] - record["tracker_lateral"][selected]),
            0.0,
        ),
        "score_penalty": max(
            float(record["scores"][candidate] - record["scores"][selected]),
            0.0,
        ),
    }


def _metrics(
    records: list[dict[str, Any]],
    chosen: np.ndarray,
    selected: np.ndarray,
    top1: np.ndarray,
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    if not records:
        return {
            "records": 0,
            "changed_rate": None,
            "top1_selected_rate": None,
            "safety_cost_delta_vs_current": _empty_summary(),
            "safety_cost_delta_vs_top1": _empty_summary(),
            "progress_delta_vs_current": _empty_summary(),
            "progress_delta_vs_top1": _empty_summary(),
            "planned_progress_delta_vs_current": _empty_summary(),
            "hard_nonworse_vs_current": None,
            "hard_nonworse_vs_top1": None,
            "hard_component_nonworse_vs_current": {},
            "hard_component_nonworse_vs_top1": {},
            "beneficial_current_preserved_rate": None,
            "harmful_current_changed_rate": None,
        }
    rows = np.arange(len(records))
    costs = np.asarray([record["safety_cost"] for record in records], dtype=np.float64)
    outcome_progress = np.asarray(
        [record["outcome_progress"] for record in records],
        dtype=np.float64,
    )
    planned_progress = np.asarray(
        [record["planned_progress"] for record in records],
        dtype=np.float64,
    )
    current_cost = costs[rows, selected]
    chosen_cost = costs[rows, chosen]
    top1_cost = costs[:, 0]
    current_progress = outcome_progress[rows, selected]
    chosen_progress = outcome_progress[rows, chosen]
    top1_progress = outcome_progress[:, 0]
    current_planned = planned_progress[rows, selected]
    chosen_planned = planned_progress[rows, chosen]
    harmful_current = (current_cost - top1_cost) > EPS
    beneficial_current = (top1_cost - current_cost) > EPS
    return {
        "records": int(len(records)),
        "changed_rate": float(np.mean(chosen != selected)),
        "top1_selected_rate": float(np.mean(chosen == top1)),
        "safety_cost_delta_vs_current": _summary_with_cvar(
            chosen_cost - current_cost,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "safety_cost_delta_vs_top1": _summary_with_cvar(
            chosen_cost - top1_cost,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "progress_delta_vs_current": _paired_summary(
            chosen_progress - current_progress,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "progress_delta_vs_top1": _paired_summary(
            chosen_progress - top1_progress,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "planned_progress_delta_vs_current": _paired_summary(
            chosen_planned - current_planned,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        ),
        "hard_nonworse_vs_current": _hard_nonworse_rate(records, chosen, selected),
        "hard_nonworse_vs_top1": _hard_nonworse_rate(records, chosen, top1),
        "hard_component_nonworse_vs_current": _hard_component_nonworse_rates(
            records,
            chosen,
            selected,
        ),
        "hard_component_nonworse_vs_top1": _hard_component_nonworse_rates(
            records,
            chosen,
            top1,
        ),
        "beneficial_current_preserved_rate": _conditional_rate(
            chosen == selected,
            beneficial_current,
        ),
        "harmful_current_changed_rate": _conditional_rate(
            chosen != selected,
            harmful_current,
        ),
    }


def _mechanism(records: list[dict[str, Any]], choices: list[dict[str, Any]]) -> dict[str, Any]:
    target = [choice for choice in choices if choice["target_record"]]
    supported = [choice for choice in target if choice["support"]]
    candidates = [choice["candidate"] for choice in supported if choice["candidate"]]
    dense_records = [record for record in records if _is_dense_lane_change(record)]
    all_infeasible_changed = sum(
        int((not bool(record["feasible"].any())) and choice["changed"])
        for record, choice in zip(records, choices)
    )
    return {
        "target_records": len(target),
        "supported_target_records": len(supported),
        "dense_support_rate": (
            None if not target else float(len(supported)) / float(len(target))
        ),
        "dense_records": len(dense_records),
        "all_infeasible_changed_records": int(all_infeasible_changed),
        "override_top1_chosen_rate": (
            None
            if not supported
            else float(np.mean([choice["chosen"] == 0 for choice in supported]))
        ),
        "mean_dp_prior_gain": _summary(
            choice["dp_prior_gain"] for choice in candidates
        ),
        "mean_progress_loss": _summary(
            choice["progress_loss"] for choice in candidates
        ),
        "mean_target_speed_loss": _summary(
            choice["target_speed_loss"] for choice in candidates
        ),
        "mean_jerk_worse": _summary(
            choice["jerk_worse"] for choice in candidates
        ),
        "mean_lateral_worse": _summary(
            choice["lateral_worse"] for choice in candidates
        ),
        "mean_score_penalty": _summary(
            choice["score_penalty"] for choice in candidates
        ),
    }


def _decision(
    records: list[dict[str, Any]],
    choices: list[dict[str, Any]],
    dense_records: list[dict[str, Any]],
    dense_chosen: np.ndarray,
    dense_selected: np.ndarray,
    dense_top1: np.ndarray,
    *,
    config: LooseRuleConfig,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    mechanism = _mechanism(records, choices)
    dense_metrics = _metrics(
        dense_records,
        dense_chosen,
        dense_selected,
        dense_top1,
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )
    reasons: list[str] = []
    support_rate = mechanism["dense_support_rate"]
    if support_rate is None or support_rate < config.min_dense_support_rate:
        reasons.append("insufficient_dense_support")
    override_top1 = mechanism["override_top1_chosen_rate"]
    if override_top1 is not None and override_top1 > config.max_override_top1_rate + EPS:
        reasons.append("top1_collapse_risk")
    if mechanism["all_infeasible_changed_records"]:
        reasons.append("all_infeasible_branch_changed")
    current_safety = dense_metrics["safety_cost_delta_vs_current"]
    top1_safety = dense_metrics["safety_cost_delta_vs_top1"]
    if current_safety["ci95_high"] is None or current_safety["ci95_high"] >= 0.0:
        reasons.append("dense_safety_vs_current_not_proven")
    if top1_safety["ci95_high"] is None or top1_safety["ci95_high"] >= 0.0:
        reasons.append("dense_safety_vs_top1_not_proven")
    progress = dense_metrics["progress_delta_vs_current"]
    if (
        progress["ci95_low"] is None
        or progress["ci95_low"] < config.min_progress_delta_ci_low
    ):
        reasons.append("dense_progress_regression")
    if (
        dense_metrics["hard_nonworse_vs_current"] is None
        or dense_metrics["hard_nonworse_vs_current"] < config.min_hard_nonworse_rate
    ):
        reasons.append("hard_components_worse_vs_current")
    if (
        dense_metrics["hard_nonworse_vs_top1"] is None
        or dense_metrics["hard_nonworse_vs_top1"] < config.min_hard_nonworse_rate
    ):
        reasons.append("hard_components_worse_vs_top1")
    passed = not reasons
    return {
        "status": (
            "loose_rule_outcome_screen_passed"
            if passed
            else "loose_rule_outcome_screen_rejected"
        ),
        "passed": passed,
        "reasons": reasons,
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": bool(passed),
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "next_step": (
            "If this screen passes, design a default-off implementation and a "
            "small paired non-formal smoke. If it fails, reject this loose "
            "finite-filter route and return to schema/calibration evidence."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Dense Lane-Change Loose Rule Outcome Screen",
        "",
        "This is an offline outcome-labeled screen. Runtime predicates use only current-tick fixed candidate features; outcomes are posterior SafetyCost labels.",
        "",
        "## Verdict",
        "",
        f"- Status: `{report['final_decision']['status']}`",
        f"- Passed: `{report['final_decision']['passed']}`",
        f"- Closed-loop smoke authorized: `{report['final_decision']['closed_loop_smoke_authorized']}`",
        f"- CAMP retraining authorized: `{report['final_decision']['camp_retraining_authorized']}`",
        "",
        "Reasons:",
    ]
    if report["final_decision"]["reasons"]:
        for reason in report["final_decision"]["reasons"]:
            lines.append(f"- `{reason}`")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Records",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ]
    )
    for key, value in report["records"].items():
        lines.append(f"| `{key}` | {_fmt_value(value)} |")
    lines.extend(
        [
            "",
            "## Mechanism",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ]
    )
    for key, value in report["mechanism"].items():
        if isinstance(value, dict):
            lines.append(f"| `{key}.mean` | {_fmt_value(value.get('mean'))} |")
        else:
            lines.append(f"| `{key}` | {_fmt_value(value)} |")
    lines.extend(
        [
            "",
            "## Dense Lane-Change Metrics",
            "",
            "| Metric | Mean | CI Low | CI High | CVaR90 |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    dense = report["dense_lane_change"]
    for name in (
        "safety_cost_delta_vs_current",
        "safety_cost_delta_vs_top1",
        "progress_delta_vs_current",
        "progress_delta_vs_top1",
        "planned_progress_delta_vs_current",
    ):
        metric = dense[name]
        lines.append(
            f"| `{name}` | {_fmt_value(metric.get('mean'))} | "
            f"{_fmt_value(metric.get('ci95_low'))} | "
            f"{_fmt_value(metric.get('ci95_high'))} | "
            f"{_fmt_value(metric.get('cvar90_worst_tail'))} |"
        )
    lines.extend(
        [
            "",
            "## Hard Components",
            "",
            "| Comparison | Collision | Near miss | Lane | Red light | All hard |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for label, key, all_key in (
        ("vs current", "hard_component_nonworse_vs_current", "hard_nonworse_vs_current"),
        ("vs Top-1", "hard_component_nonworse_vs_top1", "hard_nonworse_vs_top1"),
    ):
        hard = dense[key]
        lines.append(
            f"| {label} | {_fmt_value(hard.get('collision'))} | "
            f"{_fmt_value(hard.get('near_miss'))} | "
            f"{_fmt_value(hard.get('lane_violation'))} | "
            f"{_fmt_value(hard.get('red_light_violation'))} | "
            f"{_fmt_value(dense.get(all_key))} |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _record_summary(
    records: list[dict[str, Any]],
    choices: list[dict[str, Any]],
) -> dict[str, Any]:
    changed = [choice for choice in choices if choice["changed"]]
    dense = [_is_dense_lane_change(record) for record in records]
    target = [choice["target_record"] for choice in choices]
    support = [choice["support"] for choice in choices]
    return {
        "total_records": len(records),
        "logs": len({record["context"].get("log_path") for record in records}),
        "formal_seed_records": int(
            sum(record["context"].get("formal_seed", False) for record in records)
        ),
        "dense_lane_change_records": int(sum(dense)),
        "target_records": int(sum(target)),
        "supported_target_records": int(sum(support)),
        "changed_records": len(changed),
        "changed_rate": _rate(len(changed), len(records)),
        "selected_non_top1_rate": float(
            np.mean([record["selected"] != 0 for record in records])
        ),
        "candidate_count_values": sorted({record["candidate_count"] for record in records}),
    }


def _first_vector(
    raw: dict[str, Any],
    size: int,
    label: str,
    keys: tuple[str, ...],
    *,
    default: float | None = None,
    allow_positive_infinity: bool = False,
) -> np.ndarray:
    for key in keys:
        if raw.get(key) is None:
            continue
        values = _vector(
            raw.get(key),
            size,
            f"{label} {key}",
            allow_positive_infinity=allow_positive_infinity,
        )
        if np.any(values < 0.0):
            raise ValueError(f"{label} {key} must be nonnegative.")
        return values
    if default is None:
        raise ValueError(f"{label} requires one of {', '.join(keys)}.")
    return np.full(size, float(default), dtype=np.float64)


def _hard_nonworse_rate(
    records: list[dict[str, Any]],
    chosen: np.ndarray,
    reference: np.ndarray,
) -> float | None:
    if not records:
        return None
    rates = _hard_component_nonworse_rates(records, chosen, reference)
    return float(np.mean([rates[field] for field in BOOL_FIELDS]))


def _hard_component_nonworse_rates(
    records: list[dict[str, Any]],
    chosen: np.ndarray,
    reference: np.ndarray,
) -> dict[str, float]:
    if not records:
        return {field: 0.0 for field in BOOL_FIELDS}
    result = {}
    for field in BOOL_FIELDS:
        rows = []
        for record, chosen_idx, reference_idx in zip(records, chosen, reference):
            chosen_outcome = record["outcomes"][int(chosen_idx)]
            reference_outcome = record["outcomes"][int(reference_idx)]
            rows.append(
                float(bool(chosen_outcome[field]))
                <= float(bool(reference_outcome[field]))
            )
        result[field] = float(np.mean(rows))
    return result


def _summary_with_cvar(
    values: np.ndarray,
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, Any]:
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    summary = _paired_summary(
        arr,
        bootstrap_resamples=bootstrap_resamples,
        seed=seed,
    )
    if arr.size == 0:
        return {**summary, "cvar90_worst_tail": None}
    threshold = float(np.percentile(arr, 90.0))
    tail = arr[arr >= threshold]
    return {**summary, "cvar90_worst_tail": float(np.mean(tail))}


def _empty_summary() -> dict[str, Any]:
    return {
        "n": 0,
        "mean": None,
        "min": None,
        "p50": None,
        "p95": None,
        "max": None,
        "ci95_low": None,
        "ci95_high": None,
        "cvar90_worst_tail": None,
    }


def _subset(records: list[dict[str, Any]], mask: np.ndarray) -> list[dict[str, Any]]:
    return [record for record, keep in zip(records, mask) if bool(keep)]


def _is_dense_lane_change(record: dict[str, Any]) -> bool:
    context = record.get("context", {})
    route = str(context.get("route") or "")
    npc_count = context.get("npc_count")
    npc = -1 if npc_count is None else int(npc_count)
    return ("lane_change" in route or "nishishinjuku" in route) and npc >= 8


def _validate_config(config: LooseRuleConfig) -> None:
    for name, value in config.__dict__.items():
        numeric = float(value)
        if not np.isfinite(numeric):
            raise ValueError(f"{name} must be finite.")
        if name != "min_progress_delta_ci_low" and numeric < 0.0:
            raise ValueError(f"{name} must be nonnegative.")


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return float(numerator) / float(denominator)


def _fmt_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    try:
        return _fmt(value)
    except (TypeError, ValueError):
        return str(value)


if __name__ == "__main__":
    main()
