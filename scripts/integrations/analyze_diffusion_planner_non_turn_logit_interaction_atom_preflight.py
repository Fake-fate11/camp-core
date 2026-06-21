#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
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
from scripts.integrations.analyze_diffusion_planner_progress_support_descriptor_separability import (  # noqa: E402
    ALLOWED_HARMFUL_RATE_TARGET,
    BENEFICIAL_RETAIN_RATE_TARGET,
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_NEUTRAL,
    CLASS_TOP1,
    FORMAL_SEEDS,
    HARMFUL_BLOCK_RATE_TARGET,
    MAX_AFFINE_TERMS,
    MAX_TOP_DESCRIPTORS,
    MIN_BENEFICIAL_CANDIDATES,
    MIN_HARMFUL_CANDIDATES,
    MIN_VALUE_GAIN,
    MIN_VALUE_LOSS,
    NORMALIZATION_PERCENTILE,
    PROGRESS_LOSS_BUDGET_M,
    SIMPLEX_DENOMINATOR,
    DescriptorSpec,
    _affine_screens,
    _class_counts,
    _descriptor_coverage,
    _failure_gap,
    _load_json,
    _normalization,
    _outcome,
    _path_seeds,
    _record_candidate_count,
    _record_seed,
    _screen_sort_key,
    _single_descriptor_screens,
)


READY_STATUS = (
    "non_turn_logit_interaction_atom_preflight_promising_for_payload_design"
)
REJECT_STATUS = "non_turn_logit_interaction_atom_preflight_rejected"
SOURCE_BLOCKED_STATUS = "non_turn_logit_interaction_atom_preflight_source_not_ready"
FORMAL_SEED_STATUS = "non_turn_logit_interaction_atom_preflight_formal_seed_conflict"

SOURCE_STATUS = "turn_logit_atom_bottleneck_diagnosed"
SOURCE_NEXT_WORK = "design_non_turn_logit_or_interaction_atoms_before_retraining"

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "online_optimization_promotion_authorized",
)


@dataclass(frozen=True)
class AtomFormula:
    name: str
    definition: str
    source_fields: tuple[str, ...]
    nonnegative: bool = True
    fixed_current_tick: bool = True
    convex_master_compatible: bool = True


ATOM_FORMULAS: tuple[AtomFormula, ...] = (
    AtomFormula(
        "route_progress_deficit_vs_top1_m",
        "max(route_progress_0 - route_progress_k, 0)",
        ("candidate_route_progress",),
    ),
    AtomFormula(
        "dp_reward_total_deficit_vs_top1",
        "max(dp_reward_total_0 - dp_reward_total_k, 0)",
        ("dp_candidate_rewards.total",),
    ),
    AtomFormula(
        "union_red_light_cost",
        "max(candidate_horizon_union_planned_red_light_cost_k, 0)",
        ("candidate_horizon_union_planned_red_light_cost",),
    ),
    AtomFormula(
        "red_stopping_margin_cost",
        "max(candidate_red_stopping_margin_cost_k, 0)",
        ("candidate_red_stopping_margin_cost",),
    ),
    AtomFormula(
        "dp_prior_jerk_excess_cost",
        "max(candidate_dp_prior_jerk_excess_cost_k, 0)",
        ("candidate_dp_prior_jerk_excess_cost",),
    ),
    AtomFormula(
        "lateral_acceleration_excess_vs_top1",
        "max(candidate_horizon_lateral_acceleration_cost_k - cost_0, 0)",
        ("candidate_horizon_lateral_acceleration_cost",),
    ),
    AtomFormula(
        "dp_prior_deviation_excess_vs_top1",
        "max(candidate_dp_prior_deviation_cost_k - cost_0, 0)",
        ("candidate_dp_prior_deviation_cost",),
    ),
    AtomFormula(
        "soft_clearance_violation_cost",
        "max(candidate_obstacle_clearance.soft_clearance_violation_cost_k, 0)",
        ("candidate_obstacle_clearance.soft_clearance_violation_cost",),
    ),
    AtomFormula(
        "near_miss_violation_cost",
        "max(candidate_obstacle_clearance.near_miss_violation_cost_k, 0)",
        ("candidate_obstacle_clearance.near_miss_violation_cost",),
    ),
    AtomFormula(
        "red_progress_interaction_cost",
        "union_red_light_cost * route_progress_deficit_vs_top1_m",
        (
            "candidate_horizon_union_planned_red_light_cost",
            "candidate_route_progress",
        ),
    ),
    AtomFormula(
        "comfort_progress_interaction_cost",
        "dp_prior_jerk_excess_cost * route_progress_deficit_vs_top1_m",
        ("candidate_dp_prior_jerk_excess_cost", "candidate_route_progress"),
    ),
    AtomFormula(
        "clearance_progress_interaction_cost",
        "soft_clearance_violation_cost * route_progress_deficit_vs_top1_m",
        (
            "candidate_obstacle_clearance.soft_clearance_violation_cost",
            "candidate_route_progress",
        ),
    ),
    AtomFormula(
        "reward_red_interaction_cost",
        "dp_reward_total_deficit_vs_top1 * (1 + union_red_light_cost)",
        ("dp_candidate_rewards.total", "candidate_horizon_union_planned_red_light_cost"),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only preflight over non-turn-logit and interaction atom "
            "candidates using existing matched nonformal logs. This does not "
            "run replay, train CAMP, or promote a selector."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--source_bottleneck_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--expected_logs", type=int, default=None)
    parser.add_argument("--expected_records", type=int, default=None)
    parser.add_argument("--expected_candidates", type=int, default=8)
    parser.add_argument("--min_value_gain", type=float, default=MIN_VALUE_GAIN)
    parser.add_argument("--min_value_loss", type=float, default=MIN_VALUE_LOSS)
    parser.add_argument(
        "--progress_loss_budget_m",
        type=float,
        default=PROGRESS_LOSS_BUDGET_M,
    )
    parser.add_argument(
        "--harmful_block_rate_target",
        type=float,
        default=HARMFUL_BLOCK_RATE_TARGET,
    )
    parser.add_argument(
        "--beneficial_retain_rate_target",
        type=float,
        default=BENEFICIAL_RETAIN_RATE_TARGET,
    )
    parser.add_argument(
        "--allowed_harmful_rate_target",
        type=float,
        default=ALLOWED_HARMFUL_RATE_TARGET,
    )
    parser.add_argument(
        "--min_beneficial_candidates",
        type=int,
        default=MIN_BENEFICIAL_CANDIDATES,
    )
    parser.add_argument(
        "--min_harmful_candidates",
        type=int,
        default=MIN_HARMFUL_CANDIDATES,
    )
    parser.add_argument("--max_top_descriptors", type=int, default=MAX_TOP_DESCRIPTORS)
    parser.add_argument("--max_affine_terms", type=int, default=MAX_AFFINE_TERMS)
    parser.add_argument("--simplex_denominator", type=int, default=SIMPLEX_DENOMINATOR)
    parser.add_argument(
        "--normalization_percentile",
        type=float,
        default=NORMALIZATION_PERCENTILE,
    )
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
        source_bottleneck_report=_load_json(args.source_bottleneck_json),
        label=args.label,
        expected_logs=args.expected_logs,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        min_value_gain=args.min_value_gain,
        min_value_loss=args.min_value_loss,
        progress_loss_budget_m=args.progress_loss_budget_m,
        harmful_block_rate_target=args.harmful_block_rate_target,
        beneficial_retain_rate_target=args.beneficial_retain_rate_target,
        allowed_harmful_rate_target=args.allowed_harmful_rate_target,
        min_beneficial_candidates=args.min_beneficial_candidates,
        min_harmful_candidates=args.min_harmful_candidates,
        max_top_descriptors=args.max_top_descriptors,
        max_affine_terms=args.max_affine_terms,
        simplex_denominator=args.simplex_denominator,
        normalization_percentile=args.normalization_percentile,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def analyze(
    paths: list[Path],
    *,
    source_bottleneck_report: dict[str, Any],
    label: str | None = None,
    expected_logs: int | None = None,
    expected_records: int | None = None,
    expected_candidates: int = 8,
    min_value_gain: float = MIN_VALUE_GAIN,
    min_value_loss: float = MIN_VALUE_LOSS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    harmful_block_rate_target: float = HARMFUL_BLOCK_RATE_TARGET,
    beneficial_retain_rate_target: float = BENEFICIAL_RETAIN_RATE_TARGET,
    allowed_harmful_rate_target: float = ALLOWED_HARMFUL_RATE_TARGET,
    min_beneficial_candidates: int = MIN_BENEFICIAL_CANDIDATES,
    min_harmful_candidates: int = MIN_HARMFUL_CANDIDATES,
    max_top_descriptors: int = MAX_TOP_DESCRIPTORS,
    max_affine_terms: int = MAX_AFFINE_TERMS,
    simplex_denominator: int = SIMPLEX_DENOMINATOR,
    normalization_percentile: float = NORMALIZATION_PERCENTILE,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    if expected_logs is not None and len(log_paths) != int(expected_logs):
        raise ValueError(f"log_count={len(log_paths)} expected={expected_logs}.")
    descriptor_specs = _descriptor_specs()
    rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    missing_feature_records = 0
    for log_path in log_paths:
        payload = _load_json(log_path)
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        if expected_records is not None and len(payload) != int(expected_records):
            raise ValueError(
                f"{log_path} record_count={len(payload)} expected={expected_records}."
            )
        for record_index, raw in enumerate(payload):
            if not isinstance(raw, dict):
                raise ValueError(f"{log_path} record {record_index} must be an object.")
            record_rows, formal_seed, missing_features = _candidate_rows(
                raw,
                {
                    "log_path": str(log_path),
                    "record_index": record_index,
                    "path_seeds": sorted(_path_seeds(log_path)),
                },
                f"{log_path} record {record_index}",
                descriptor_specs,
                expected_candidates=expected_candidates,
                min_value_gain=min_value_gain,
                min_value_loss=min_value_loss,
                progress_loss_budget_m=progress_loss_budget_m,
            )
            rows.extend(record_rows)
            formal_seed_records += int(formal_seed)
            missing_feature_records += int(missing_features)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    alternatives = [row for row in rows if row["class"] != CLASS_TOP1]
    class_counts = _class_counts(alternatives)
    normalization = _normalization(
        alternatives,
        descriptor_specs,
        percentile=normalization_percentile,
    )
    single_screens = _single_descriptor_screens(
        alternatives,
        descriptor_specs,
        harmful_block_rate_target=harmful_block_rate_target,
        beneficial_retain_rate_target=beneficial_retain_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
    )
    affine_screens = _affine_screens(
        alternatives,
        single_screens,
        normalization,
        harmful_block_rate_target=harmful_block_rate_target,
        beneficial_retain_rate_target=beneficial_retain_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
        max_top_descriptors=max_top_descriptors,
        max_affine_terms=max_affine_terms,
        simplex_denominator=simplex_denominator,
    )
    ranked = sorted(
        [*single_screens, *affine_screens],
        key=_screen_sort_key,
        reverse=True,
    )
    source = _source_gate(source_bottleneck_report)
    decision = _decision(
        source,
        ranked,
        class_counts,
        formal_seed_records=formal_seed_records,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
    )
    return {
        "analysis": {
            "name": "dp_camp_non_turn_logit_interaction_atom_preflight_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_atoms": False,
            "future_outcome_labels_used_for_classification": True,
            "future_outcome_labels_used_for_thresholds": True,
            "avoids_rejected_direct_turn_logit_atoms": True,
            "atom_formulas": [formula.__dict__ for formula in ATOM_FORMULAS],
            "math_boundary": (
                "All proposed descriptors are fixed current-tick finite-candidate "
                "coefficients computed from already logged candidate reward, "
                "red-light, route-progress, comfort, or clearance diagnostics. "
                "The interaction descriptors are products of nonnegative fixed "
                "coefficients; once materialized as candidate coefficients a_k, "
                "CAMP score remains affine in w, score_k(w)=a_k^T w, and the "
                "simplex/CVaR/L2 robust master remains convex. No convexity in "
                "trajectory coordinates and no DP-side classical Benders "
                "decomposition is claimed. Outcome labels are used only offline "
                "for class labels and thresholds."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_gate": source,
        "records": {
            "total_records": len(rows) // int(expected_candidates),
            "candidate_rows": len(rows),
            "alternative_rows": len(alternatives),
            "formal_seed_records": formal_seed_records,
            "missing_feature_records": missing_feature_records,
            "class_counts": class_counts,
        },
        "descriptor_coverage": _descriptor_coverage(alternatives, descriptor_specs),
        "normalization": normalization,
        "single_descriptor_screens": single_screens[:50],
        "affine_screens": affine_screens[:50],
        "ranked_screens": ranked[:50],
        "failure_gap": _failure_gap(ranked, class_counts),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _descriptor_specs() -> tuple[DescriptorSpec, ...]:
    return tuple(
        DescriptorSpec(
            formula.name,
            ",".join(formula.source_fields),
            formula.definition,
        )
        for formula in ATOM_FORMULAS
    )


def _candidate_rows(
    raw: dict[str, Any],
    context: dict[str, Any],
    label: str,
    descriptor_specs: tuple[DescriptorSpec, ...],
    *,
    expected_candidates: int,
    min_value_gain: float,
    min_value_loss: float,
    progress_loss_budget_m: float,
) -> tuple[list[dict[str, Any]], bool, bool]:
    outcomes = raw.get("candidate_closed_loop_outcomes")
    candidate_count = _record_candidate_count(raw, None, outcomes, label)
    if candidate_count != int(expected_candidates):
        raise ValueError(
            f"{label} candidate_count={candidate_count} expected={expected_candidates}."
        )
    if not isinstance(outcomes, list) or len(outcomes) != candidate_count:
        raise ValueError(f"{label} must contain complete candidate outcomes.")
    formal_seed = bool(set(context.get("path_seeds") or ()) & FORMAL_SEEDS)
    record_seed = _record_seed(raw)
    if record_seed in FORMAL_SEEDS:
        formal_seed = True

    feature_values, missing_features = _feature_values(raw, candidate_count, label)
    expected = {spec.name for spec in descriptor_specs}
    missing = sorted(expected - set(feature_values))
    if missing:
        raise ValueError(f"{label} missing descriptor values {missing}.")

    top1 = _outcome(outcomes[0], f"{label} outcome 0")
    rows = []
    for candidate_index, raw_outcome in enumerate(outcomes):
        outcome = _outcome(raw_outcome, f"{label} outcome {candidate_index}")
        value_delta = outcome["value"] - top1["value"]
        progress_delta = outcome["progress_m"] - top1["progress_m"]
        hard_worse = outcome["hard_violation_count"] > top1["hard_violation_count"]
        beneficial = (
            candidate_index != 0
            and outcome["feasible"]
            and value_delta >= float(min_value_gain)
            and progress_delta >= -float(progress_loss_budget_m)
            and not hard_worse
        )
        harmful = (
            candidate_index != 0
            and (
                not outcome["feasible"]
                or hard_worse
                or value_delta <= -float(min_value_loss)
                or progress_delta < -float(progress_loss_budget_m)
            )
        )
        if candidate_index == 0:
            cls = CLASS_TOP1
        elif beneficial:
            cls = CLASS_BENEFICIAL
        elif harmful:
            cls = CLASS_HARMFUL
        else:
            cls = CLASS_NEUTRAL
        rows.append(
            {
                "context": context,
                "candidate_index": candidate_index,
                "class": cls,
                "outcome_value_delta_vs_top1": value_delta,
                "progress_delta_vs_top1_m": progress_delta,
                "hard_violation_delta_vs_top1": (
                    outcome["hard_violation_count"] - top1["hard_violation_count"]
                ),
                "features": {
                    name: float(values[candidate_index])
                    for name, values in feature_values.items()
                    if np.isfinite(values[candidate_index])
                },
            }
        )
    return rows, formal_seed, missing_features


def _feature_values(
    raw: dict[str, Any],
    candidate_count: int,
    label: str,
) -> tuple[dict[str, np.ndarray], bool]:
    route_progress = _vector(raw.get("candidate_route_progress"), candidate_count, label, "candidate_route_progress")
    route_progress_deficit = np.maximum(route_progress[0] - route_progress, 0.0)
    reward_total = _reward_vector(raw.get("dp_candidate_rewards"), candidate_count, "total", label)
    reward_total_deficit = np.maximum(reward_total[0] - reward_total, 0.0)
    union_red = np.maximum(
        _vector(
            raw.get("candidate_horizon_union_planned_red_light_cost"),
            candidate_count,
            label,
            "candidate_horizon_union_planned_red_light_cost",
        ),
        0.0,
    )
    red_stopping = np.maximum(
        _vector(raw.get("candidate_red_stopping_margin_cost"), candidate_count, label, "candidate_red_stopping_margin_cost"),
        0.0,
    )
    jerk = np.maximum(
        _vector(raw.get("candidate_dp_prior_jerk_excess_cost"), candidate_count, label, "candidate_dp_prior_jerk_excess_cost"),
        0.0,
    )
    lateral = _vector(
        raw.get("candidate_horizon_lateral_acceleration_cost"),
        candidate_count,
        label,
        "candidate_horizon_lateral_acceleration_cost",
    )
    lateral_excess = np.maximum(lateral - lateral[0], 0.0)
    deviation = _vector(
        raw.get("candidate_dp_prior_deviation_cost"),
        candidate_count,
        label,
        "candidate_dp_prior_deviation_cost",
    )
    deviation_excess = np.maximum(deviation - deviation[0], 0.0)
    clearance = raw.get("candidate_obstacle_clearance")
    soft_clearance, soft_missing = _clearance_vector(
        clearance,
        "soft_clearance_violation_cost",
        candidate_count,
    )
    near_miss, near_missing = _clearance_vector(
        clearance,
        "near_miss_violation_cost",
        candidate_count,
    )
    values = {
        "route_progress_deficit_vs_top1_m": route_progress_deficit,
        "dp_reward_total_deficit_vs_top1": reward_total_deficit,
        "union_red_light_cost": union_red,
        "red_stopping_margin_cost": red_stopping,
        "dp_prior_jerk_excess_cost": jerk,
        "lateral_acceleration_excess_vs_top1": lateral_excess,
        "dp_prior_deviation_excess_vs_top1": deviation_excess,
        "soft_clearance_violation_cost": soft_clearance,
        "near_miss_violation_cost": near_miss,
        "red_progress_interaction_cost": union_red * route_progress_deficit,
        "comfort_progress_interaction_cost": jerk * route_progress_deficit,
        "clearance_progress_interaction_cost": soft_clearance * route_progress_deficit,
        "reward_red_interaction_cost": reward_total_deficit * (1.0 + union_red),
    }
    for name, vector in values.items():
        if vector.shape != (candidate_count,) or not np.all(np.isfinite(vector)):
            raise ValueError(f"{label} invalid feature vector {name}.")
        values[name] = np.maximum(vector, 0.0)
    return values, bool(soft_missing or near_missing)


def _reward_vector(
    rewards: Any,
    candidate_count: int,
    field: str,
    label: str,
) -> np.ndarray:
    if not isinstance(rewards, list) or len(rewards) != candidate_count:
        raise ValueError(f"{label} dp_candidate_rewards shape mismatch.")
    values = []
    for index, reward in enumerate(rewards):
        if not isinstance(reward, dict) or field not in reward:
            raise ValueError(f"{label} dp_candidate_rewards[{index}].{field} missing.")
        values.append(_finite_float(reward[field], f"{label} reward {index} {field}"))
    return np.asarray(values, dtype=np.float64)


def _clearance_vector(
    clearance: Any,
    key: str,
    candidate_count: int,
) -> tuple[np.ndarray, bool]:
    if not isinstance(clearance, dict) or key not in clearance:
        return np.zeros(candidate_count, dtype=np.float64), True
    raw = clearance.get(key)
    if not isinstance(raw, list) or len(raw) != candidate_count:
        return np.zeros(candidate_count, dtype=np.float64), True
    values = []
    missing = False
    for item in raw:
        if item is None:
            values.append(0.0)
            missing = True
        else:
            values.append(float(item))
    vector = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(vector)):
        raise ValueError(f"candidate_obstacle_clearance.{key} contains nonfinite values.")
    return np.maximum(vector, 0.0), missing


def _vector(value: Any, rows: int, label: str, field: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (rows,):
        raise ValueError(f"{label} {field} shape={list(array.shape)} expected={[rows]}.")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} {field} contains nonfinite values.")
    return array


def _finite_float(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be finite.") from exc
    if not np.isfinite(result):
        raise ValueError(f"{label} must be finite.")
    return result


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    return {
        "passed": decision.get("status") == SOURCE_STATUS
        and decision.get("authorized_next_work") == SOURCE_NEXT_WORK
        and decision.get("passed") is True,
        "status": decision.get("status"),
        "passed_value": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "primary_bottleneck": decision.get("primary_bottleneck"),
    }


def _decision(
    source: dict[str, Any],
    ranked: list[dict[str, Any]],
    class_counts: dict[str, int],
    *,
    formal_seed_records: int,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> dict[str, Any]:
    promising = [row for row in ranked if row["promising_screen"]]
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "source_bottleneck_gate_not_ready"
        next_work = "fix_or_run_turn_logit_bottleneck_before_preflight"
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        next_work = None
    elif class_counts.get(CLASS_BENEFICIAL, 0) < int(min_beneficial_candidates):
        status = REJECT_STATUS
        primary_gap = "beneficial_candidate_support_insufficient"
        next_work = "expand_nonformal_support_before_atom_payload_design"
    elif class_counts.get(CLASS_HARMFUL, 0) < int(min_harmful_candidates):
        status = REJECT_STATUS
        primary_gap = "harmful_candidate_support_insufficient"
        next_work = "expand_nonformal_support_before_atom_payload_design"
    elif promising:
        status = READY_STATUS
        primary_gap = "no_gap_promising_non_turn_logit_interaction_screen_found"
        next_work = "non_turn_logit_interaction_atom_payload_design_plan_only"
    else:
        status = REJECT_STATUS
        primary_gap = "non_turn_logit_interaction_atoms_do_not_separate_candidates"
        next_work = "diagnose_non_turn_logit_interaction_bottleneck_before_retraining"
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        "promising_screen_count": len(promising),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Non-Turn-Logit Interaction Atom Preflight",
        "",
        "This is a read-only preflight over existing matched nonformal logs.",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- promising screens: `{decision['promising_screen_count']}`",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Top Screens",
        "",
    ]
    for screen in report["ranked_screens"][:10]:
        lines.append(
            "- `{}`: promising=`{}`, harmful_block_rate=`{:.3f}`, "
            "beneficial_retain_rate=`{:.3f}`, allowed_harmful_rate=`{:.3f}`".format(
                screen["screen_name"],
                screen["promising_screen"],
                screen["harmful_block_rate"],
                screen["beneficial_retain_rate"],
                screen["allowed_harmful_rate"],
            )
        )
    lines.extend(["", "## Atom Formulas", "", "```json"])
    lines.append(json.dumps(report["analysis"]["atom_formulas"], indent=2, sort_keys=True))
    lines.extend(["```", "", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
