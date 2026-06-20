#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import math
import re
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
from camp_core.integrations.diffusion_planner_progress_support import (  # noqa: E402
    PROGRESS_SUPPORT_ATOM_NAMES,
    PROGRESS_SUPPORT_FIELD_NAMES,
    PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
)


READY_STATUS = "progress_support_descriptor_separability_promising_for_certificate_design"
REJECT_STATUS = "progress_support_descriptor_separability_rejected"
SOURCE_BLOCKED_STATUS = "progress_support_descriptor_separability_source_not_ready"
FORMAL_SEED_STATUS = "progress_support_descriptor_separability_formal_seed_conflict"

CONTRACT_READY_STATUS = "matched_progress_support_outcome_contract_passed"
CONTRACT_NEXT_WORK = "offline_progress_support_descriptor_separability_screen_only"
FORMAL_SEEDS = frozenset({11, 12, 13})

MIN_VALUE_GAIN = 0.25
MIN_VALUE_LOSS = 0.25
PROGRESS_LOSS_BUDGET_M = 0.05
HARMFUL_BLOCK_RATE_TARGET = 0.75
BENEFICIAL_RETAIN_RATE_TARGET = 0.75
ALLOWED_HARMFUL_RATE_TARGET = 0.10
MIN_BENEFICIAL_CANDIDATES = 5
MIN_HARMFUL_CANDIDATES = 5
MAX_TOP_DESCRIPTORS = 10
MAX_AFFINE_TERMS = 3
SIMPLEX_DENOMINATOR = 4
NORMALIZATION_PERCENTILE = 95.0
THRESHOLD_PERCENTILES = (
    0.0,
    5.0,
    10.0,
    20.0,
    30.0,
    40.0,
    50.0,
    60.0,
    70.0,
    80.0,
    90.0,
    95.0,
    100.0,
)

CLASS_BENEFICIAL = "beneficial_alternative"
CLASS_HARMFUL = "harmful_alternative"
CLASS_NEUTRAL = "neutral_alternative"
CLASS_TOP1 = "top1_reference"

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
class DescriptorSpec:
    name: str
    source: str
    rationale: str


DERIVED_DESCRIPTOR_SPECS: tuple[DescriptorSpec, ...] = (
    DescriptorSpec(
        "final_route_progress_deficit_vs_top1_m",
        "candidate_route_progress_s_profile_m",
        "final support-horizon route-progress deficit versus DP Top-1",
    ),
    DescriptorSpec(
        "max_route_progress_deficit_vs_top1_m",
        "candidate_route_progress_s_profile_m",
        "maximum support-horizon route-progress deficit versus DP Top-1",
    ),
    DescriptorSpec(
        "final_plan_arc_deficit_vs_top1_m",
        "candidate_plan_arc_length_profile_m",
        "final plan-arc deficit versus DP Top-1",
    ),
    DescriptorSpec(
        "tail_speed_deficit_vs_top1_mps",
        "candidate_speed_profile_mps",
        "tail support speed deficit versus DP Top-1",
    ),
    DescriptorSpec(
        "route_remaining_excess_vs_top1_m",
        "candidate_route_remaining_m",
        "remaining-route excess versus DP Top-1",
    ),
    DescriptorSpec(
        "goal_alignment_deficit_vs_top1_m",
        "candidate_goal_alignment_progress_m",
        "goal-alignment progress deficit versus DP Top-1",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline no-leak separability screen over matched DP-CAMP "
            "progress-support descriptors and candidate outcome labels. This "
            "is an oracle diagnostic over existing nonformal logs, not CAMP "
            "training and not an online selector."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--matched_contract_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
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
        matched_contract_report=_load_json(args.matched_contract_json),
        label=args.label,
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
    matched_contract_report: dict[str, Any],
    label: str | None = None,
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
    items: list[dict[str, Any]] = []
    for log_path in log_paths:
        rows = _load_json(log_path)
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, raw in enumerate(rows):
            if not isinstance(raw, dict):
                raise ValueError(f"{log_path} record {record_index} must be an object.")
            items.append(
                {
                    "raw": raw,
                    "context": {
                        "log_path": str(log_path),
                        "record_index": record_index,
                        "path_seeds": sorted(_path_seeds(log_path)),
                    },
                }
            )
    return analyze_records(
        items,
        matched_contract_report=matched_contract_report,
        label=label,
        min_value_gain=min_value_gain,
        min_value_loss=min_value_loss,
        progress_loss_budget_m=progress_loss_budget_m,
        harmful_block_rate_target=harmful_block_rate_target,
        beneficial_retain_rate_target=beneficial_retain_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
        max_top_descriptors=max_top_descriptors,
        max_affine_terms=max_affine_terms,
        simplex_denominator=simplex_denominator,
        normalization_percentile=normalization_percentile,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    matched_contract_report: dict[str, Any],
    label: str | None = None,
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
    if not items:
        raise ValueError("At least one selection record is required.")
    source = _source_gate(matched_contract_report)
    rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    descriptor_specs = _descriptor_specs()
    for index, item in enumerate(items):
        record_rows, formal_seed = _candidate_rows(
            item["raw"],
            item["context"],
            f"record {index}",
            descriptor_specs,
            min_value_gain=min_value_gain,
            min_value_loss=min_value_loss,
            progress_loss_budget_m=progress_loss_budget_m,
        )
        rows.extend(record_rows)
        formal_seed_records += int(formal_seed)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    alternative_rows = [row for row in rows if row["class"] != CLASS_TOP1]
    class_counts = _class_counts(alternative_rows)
    normalization = _normalization(
        alternative_rows,
        descriptor_specs,
        percentile=normalization_percentile,
    )
    single_screens = _single_descriptor_screens(
        alternative_rows,
        descriptor_specs,
        harmful_block_rate_target=harmful_block_rate_target,
        beneficial_retain_rate_target=beneficial_retain_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
    )
    affine_screens = _affine_screens(
        alternative_rows,
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
            "name": "dp_camp_progress_support_descriptor_separability_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_descriptors": False,
            "future_outcome_labels_used_for_classification": True,
            "future_outcome_labels_used_for_thresholds": True,
            "future_outcome_labels_used_for_evaluation": True,
            "thresholds_are_offline_oracle_diagnostics": True,
            "top1_reference_candidate_index": 0,
            "descriptor_specs": [spec.__dict__ for spec in descriptor_specs],
            "label_definition": {
                "beneficial": (
                    "candidate k>0 is feasible, improves outcome value over "
                    "candidate0 by min_value_gain, preserves progress within "
                    "progress_loss_budget_m, and is hard-safety-nonworse"
                ),
                "harmful": (
                    "candidate k>0 is infeasible, hard-safety-worse, loses "
                    "more than min_value_loss in outcome value, or exceeds the "
                    "progress loss budget"
                ),
                "neutral": "all other k>0 candidates",
                "outcome_value_direction": "higher_is_better",
            },
            "affine_search": {
                "nonnegative_simplex_coefficients": True,
                "max_top_descriptors": int(max_top_descriptors),
                "max_affine_terms": int(max_affine_terms),
                "simplex_denominator": int(simplex_denominator),
                "candidate_scalarizations": len(affine_screens),
            },
            "accept_criteria": {
                "min_beneficial_candidates": int(min_beneficial_candidates),
                "min_harmful_candidates": int(min_harmful_candidates),
                "harmful_block_rate": f">= {harmful_block_rate_target}",
                "beneficial_retain_rate": f">= {beneficial_retain_rate_target}",
                "allowed_harmful_rate": f"<= {allowed_harmful_rate_target}",
            },
            "math_boundary": (
                "Progress-support descriptors are fixed current-tick "
                "finite-candidate quantities computed before candidate "
                "closed-loop outcomes. Outcome labels define only offline "
                "beneficial/harmful classes and threshold diagnostics. "
                "Nonnegative simplex scalarizations preserve affine "
                "score_k(w)=a_k^T w after atomization and remain compatible "
                "with the simplex/CVaR/L2 convex master. No DP-side classical "
                "Benders master/subproblem, dual, or cut is constructed."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_matched_contract_gate": source,
        "records": {
            "total_records": len(items),
            "candidate_rows": len(rows),
            "alternative_rows": len(alternative_rows),
            "formal_seed_records": formal_seed_records,
            "class_counts": class_counts,
        },
        "descriptor_coverage": _descriptor_coverage(alternative_rows, descriptor_specs),
        "normalization": normalization,
        "single_descriptor_screens": single_screens[:50],
        "affine_screens": affine_screens[:50],
        "ranked_screens": ranked[:50],
        "failure_gap": _failure_gap(ranked, class_counts),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _descriptor_specs() -> tuple[DescriptorSpec, ...]:
    atom_specs = tuple(
        DescriptorSpec(
            name=f"atom_{name}",
            source="progress_support_atoms",
            rationale=(
                "nonnegative progress-support atom emitted by the runtime "
                "payload; lower value is lower diagnostic risk"
            ),
        )
        for name in PROGRESS_SUPPORT_ATOM_NAMES
    )
    return (*atom_specs, *DERIVED_DESCRIPTOR_SPECS)


def _candidate_rows(
    raw: dict[str, Any],
    context: dict[str, Any],
    label: str,
    descriptor_specs: tuple[DescriptorSpec, ...],
    *,
    min_value_gain: float,
    min_value_loss: float,
    progress_loss_budget_m: float,
) -> tuple[list[dict[str, Any]], bool]:
    payload = raw.get("progress_support_logging")
    outcomes = raw.get("candidate_closed_loop_outcomes")
    candidate_count = _record_candidate_count(raw, payload, outcomes, label)
    _validate_payload(payload, candidate_count, label)
    if not isinstance(outcomes, list) or len(outcomes) != candidate_count:
        raise ValueError(f"{label} must contain complete candidate outcomes.")
    formal_seed = bool(set(context.get("path_seeds") or ()) & FORMAL_SEEDS)
    record_seed = _record_seed(raw)
    if record_seed in FORMAL_SEEDS:
        formal_seed = True

    top1 = _outcome(outcomes[0], f"{label} outcome 0")
    feature_values = _descriptor_values(payload, descriptor_specs, candidate_count, label)
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
                "red_light_worse_than_top1": (
                    outcome["red_light_violation"] and not top1["red_light_violation"]
                ),
                "lane_worse_than_top1": (
                    outcome["lane_violation"] and not top1["lane_violation"]
                ),
                "collision_worse_than_top1": (
                    outcome["collision"] and not top1["collision"]
                ),
                "near_miss_worse_than_top1": (
                    outcome["near_miss"] and not top1["near_miss"]
                ),
                "features": {
                    name: float(values[candidate_index])
                    for name, values in feature_values.items()
                    if np.isfinite(values[candidate_index])
                },
            }
        )
    return rows, formal_seed


def _descriptor_values(
    payload: dict[str, Any],
    descriptor_specs: tuple[DescriptorSpec, ...],
    candidate_count: int,
    label: str,
) -> dict[str, np.ndarray]:
    atoms = _matrix(
        payload.get("progress_support_atoms"),
        candidate_count,
        len(PROGRESS_SUPPORT_ATOM_NAMES),
        f"{label} progress_support_atoms",
    )
    route_progress = _matrix_any_width(
        payload.get("candidate_route_progress_s_profile_m"),
        candidate_count,
        f"{label} candidate_route_progress_s_profile_m",
    )
    plan_arc = _matrix_any_width(
        payload.get("candidate_plan_arc_length_profile_m"),
        candidate_count,
        f"{label} candidate_plan_arc_length_profile_m",
    )
    speed = _matrix_any_width(
        payload.get("candidate_speed_profile_mps"),
        candidate_count,
        f"{label} candidate_speed_profile_mps",
    )
    route_remaining = _vector(
        payload.get("candidate_route_remaining_m"),
        candidate_count,
        f"{label} candidate_route_remaining_m",
    )
    goal_alignment = _vector(
        payload.get("candidate_goal_alignment_progress_m"),
        candidate_count,
        f"{label} candidate_goal_alignment_progress_m",
    )

    values: dict[str, np.ndarray] = {}
    for atom_index, atom_name in enumerate(PROGRESS_SUPPORT_ATOM_NAMES):
        values[f"atom_{atom_name}"] = np.maximum(atoms[:, atom_index], 0.0)
    values["final_route_progress_deficit_vs_top1_m"] = np.maximum(
        route_progress[0, -1] - route_progress[:, -1],
        0.0,
    )
    values["max_route_progress_deficit_vs_top1_m"] = np.max(
        np.maximum(route_progress[0:1, :] - route_progress, 0.0),
        axis=1,
    )
    values["final_plan_arc_deficit_vs_top1_m"] = np.maximum(
        plan_arc[0, -1] - plan_arc[:, -1],
        0.0,
    )
    values["tail_speed_deficit_vs_top1_mps"] = np.maximum(
        speed[0, -1] - speed[:, -1],
        0.0,
    )
    values["route_remaining_excess_vs_top1_m"] = np.maximum(
        route_remaining - route_remaining[0],
        0.0,
    )
    values["goal_alignment_deficit_vs_top1_m"] = np.maximum(
        goal_alignment[0] - goal_alignment,
        0.0,
    )
    expected = {spec.name for spec in descriptor_specs}
    missing = sorted(expected - set(values))
    if missing:
        raise ValueError(f"{label} missing descriptor values {missing}.")
    return values


def _single_descriptor_screens(
    rows: list[dict[str, Any]],
    descriptor_specs: tuple[DescriptorSpec, ...],
    *,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    allowed_harmful_rate_target: float,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> list[dict[str, Any]]:
    reports = []
    for spec in descriptor_specs:
        values = np.asarray(
            [row["features"].get(spec.name, np.nan) for row in rows],
            dtype=np.float64,
        )
        screens = [
            _screen_metrics(
                rows,
                values=values,
                threshold=threshold,
                screen_name=f"{spec.name}:allow_low",
                descriptor_names=(spec.name,),
                coefficients={spec.name: 1.0},
                harmful_block_rate_target=harmful_block_rate_target,
                beneficial_retain_rate_target=beneficial_retain_rate_target,
                allowed_harmful_rate_target=allowed_harmful_rate_target,
                min_beneficial_candidates=min_beneficial_candidates,
                min_harmful_candidates=min_harmful_candidates,
            )
            for threshold in _thresholds(values[np.isfinite(values)])
        ]
        best = _best_screen(screens)
        if best is not None:
            best = {
                **best,
                "source": spec.source,
                "rationale": spec.rationale,
                "coverage": _coverage(rows, spec.name),
                "auc_beneficial_vs_harmful": _auc_for_values(rows, values),
            }
            reports.append(best)
    return sorted(reports, key=_screen_sort_key, reverse=True)


def _affine_screens(
    rows: list[dict[str, Any]],
    single_screens: list[dict[str, Any]],
    normalization: dict[str, float],
    *,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    allowed_harmful_rate_target: float,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
    max_top_descriptors: int,
    max_affine_terms: int,
    simplex_denominator: int,
) -> list[dict[str, Any]]:
    descriptor_names = []
    for screen in single_screens:
        name = str(screen["descriptor_names"][0])
        if name not in descriptor_names:
            descriptor_names.append(name)
        if len(descriptor_names) >= int(max_top_descriptors):
            break
    screens: list[dict[str, Any]] = []
    for term_count in range(2, int(max_affine_terms) + 1):
        for names in itertools.combinations(descriptor_names, term_count):
            for weights in _simplex_weights(term_count, int(simplex_denominator)):
                values = _affine_values(rows, names, weights, normalization)
                coefficients = {
                    name: float(weight)
                    for name, weight in zip(names, weights, strict=True)
                }
                for threshold in _thresholds(values[np.isfinite(values)]):
                    screens.append(
                        _screen_metrics(
                            rows,
                            values=values,
                            threshold=threshold,
                            screen_name=(
                                "affine_simplex:"
                                + "+".join(
                                    f"{coefficients[name]:.3f}*{name}"
                                    for name in names
                                )
                            ),
                            descriptor_names=names,
                            coefficients=coefficients,
                            harmful_block_rate_target=harmful_block_rate_target,
                            beneficial_retain_rate_target=beneficial_retain_rate_target,
                            allowed_harmful_rate_target=allowed_harmful_rate_target,
                            min_beneficial_candidates=min_beneficial_candidates,
                            min_harmful_candidates=min_harmful_candidates,
                        )
                    )
    return sorted(screens, key=_screen_sort_key, reverse=True)


def _screen_metrics(
    rows: list[dict[str, Any]],
    *,
    values: np.ndarray,
    threshold: float,
    screen_name: str,
    descriptor_names: tuple[str, ...],
    coefficients: dict[str, float],
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    allowed_harmful_rate_target: float,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> dict[str, Any]:
    finite = np.isfinite(values)
    allowed = finite & (values <= float(threshold) + 1e-12)
    classes = np.asarray([row["class"] for row in rows], dtype=object)
    harmful = classes == CLASS_HARMFUL
    beneficial = classes == CLASS_BENEFICIAL
    neutral = classes == CLASS_NEUTRAL
    harmful_count = int(np.sum(harmful))
    beneficial_count = int(np.sum(beneficial))
    allowed_count = int(np.sum(allowed))
    harmful_block_rate = _rate(np.sum(harmful & ~allowed), harmful_count)
    beneficial_retain_rate = _rate(np.sum(beneficial & allowed), beneficial_count)
    allowed_harmful_rate = _rate(np.sum(harmful & allowed), allowed_count)
    value_deltas = np.asarray(
        [row["outcome_value_delta_vs_top1"] for row in rows],
        dtype=np.float64,
    )
    progress_deltas = np.asarray(
        [row["progress_delta_vs_top1_m"] for row in rows],
        dtype=np.float64,
    )
    promising = (
        harmful_count >= int(min_harmful_candidates)
        and beneficial_count >= int(min_beneficial_candidates)
        and harmful_block_rate >= float(harmful_block_rate_target)
        and beneficial_retain_rate >= float(beneficial_retain_rate_target)
        and allowed_harmful_rate <= float(allowed_harmful_rate_target)
    )
    return {
        "screen_name": screen_name,
        "descriptor_names": list(descriptor_names),
        "coefficients": coefficients,
        "direction": "allow_low",
        "threshold": float(threshold),
        "considered_candidates": int(np.sum(finite)),
        "allowed_candidates": allowed_count,
        "blocked_candidates": int(len(rows) - allowed_count),
        "harmful_count": harmful_count,
        "beneficial_count": beneficial_count,
        "neutral_count": int(np.sum(neutral)),
        "harmful_block_rate": harmful_block_rate,
        "beneficial_retain_rate": beneficial_retain_rate,
        "allowed_harmful_rate": allowed_harmful_rate,
        "allowed_value_delta_mean": _mean(value_deltas[allowed]),
        "allowed_progress_delta_mean_m": _mean(progress_deltas[allowed]),
        "promising_screen": promising,
    }


def _validate_payload(payload: Any, candidate_count: int, label: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} missing progress_support_logging payload.")
    expected = {
        "schema_version": PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "classical_benders_claim": False,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise ValueError(
                f"{label} progress_support_logging {field}={payload.get(field)!r}."
            )
    if "candidate_closed_loop_outcomes" in payload:
        raise ValueError(f"{label} progress-support payload embeds outcome labels.")
    if payload.get("candidate_count") != candidate_count:
        raise ValueError(f"{label} progress-support candidate_count mismatch.")
    finite_checks = payload.get("finite_checks")
    if not isinstance(finite_checks, dict):
        raise ValueError(f"{label} progress-support finite checks missing.")
    for field in (
        *PROGRESS_SUPPORT_FIELD_NAMES,
        "progress_support_atoms",
        "progress_support_atoms_nonnegative",
    ):
        if finite_checks.get(field) is not True:
            raise ValueError(f"{label} progress-support finite check failed {field}.")


def _record_candidate_count(
    raw: dict[str, Any],
    payload: Any,
    outcomes: Any,
    label: str,
) -> int:
    candidates = raw.get("num_candidates")
    if not isinstance(candidates, int) or isinstance(candidates, bool) or candidates <= 1:
        if isinstance(payload, dict) and isinstance(payload.get("candidate_count"), int):
            candidates = payload["candidate_count"]
        elif isinstance(outcomes, list):
            candidates = len(outcomes)
    if not isinstance(candidates, int) or isinstance(candidates, bool) or candidates <= 1:
        raise ValueError(f"{label} has invalid candidate count.")
    return candidates


def _outcome(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object.")
    required = ("value", "feasible", "progress_m")
    missing = [field for field in required if field not in raw]
    if missing:
        raise ValueError(f"{label} missing {missing}.")
    hard_fields = (
        "collision",
        "near_miss",
        "lane_violation",
        "red_light_violation",
    )
    return {
        "value": _finite_float(raw["value"], f"{label}.value"),
        "feasible": bool(raw["feasible"]),
        "progress_m": _finite_float(raw["progress_m"], f"{label}.progress_m"),
        "hard_violation_count": sum(int(bool(raw.get(field))) for field in hard_fields),
        "collision": bool(raw.get("collision")),
        "near_miss": bool(raw.get("near_miss")),
        "lane_violation": bool(raw.get("lane_violation")),
        "red_light_violation": bool(raw.get("red_light_violation")),
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    status = decision.get("status")
    next_work = decision.get("authorized_next_work")
    passed = (
        bool(decision.get("passed"))
        and status == CONTRACT_READY_STATUS
        and next_work == CONTRACT_NEXT_WORK
    )
    return {
        "passed": passed,
        "status": status,
        "authorized_next_work": next_work,
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
        primary_gap = "matched_progress_support_contract_gate_not_passed"
        next_work = "fix_matched_progress_support_outcome_contract_before_separability"
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        next_work = None
    elif class_counts.get(CLASS_BENEFICIAL, 0) < int(min_beneficial_candidates):
        status = REJECT_STATUS
        primary_gap = "beneficial_candidate_support_insufficient"
        next_work = "expand_matched_progress_support_label_coverage_before_selector_design"
    elif class_counts.get(CLASS_HARMFUL, 0) < int(min_harmful_candidates):
        status = REJECT_STATUS
        primary_gap = "harmful_candidate_support_insufficient"
        next_work = "expand_matched_progress_support_label_coverage_before_selector_design"
    elif promising:
        status = READY_STATUS
        primary_gap = "no_gap_promising_progress_support_descriptor_screen_found"
        next_work = "offline_progress_support_certificate_design_only"
    else:
        status = REJECT_STATUS
        primary_gap = "progress_support_descriptors_do_not_separate_candidates"
        next_work = "diagnose_progress_support_descriptor_bottleneck_before_retraining"
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        "promising_screen_count": len(promising),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _failure_gap(
    ranked: list[dict[str, Any]],
    class_counts: dict[str, int],
) -> dict[str, Any]:
    best = ranked[0] if ranked else None
    if class_counts.get(CLASS_BENEFICIAL, 0) < MIN_BENEFICIAL_CANDIDATES:
        primary = "beneficial_candidate_support_insufficient"
    elif class_counts.get(CLASS_HARMFUL, 0) < MIN_HARMFUL_CANDIDATES:
        primary = "harmful_candidate_support_insufficient"
    elif best is None:
        primary = "no_finite_progress_support_descriptor_screen"
    elif best["harmful_block_rate"] < HARMFUL_BLOCK_RATE_TARGET:
        primary = "harmful_block_rate_insufficient"
    elif best["beneficial_retain_rate"] < BENEFICIAL_RETAIN_RATE_TARGET:
        primary = "beneficial_retain_rate_insufficient"
    elif best["allowed_harmful_rate"] > ALLOWED_HARMFUL_RATE_TARGET:
        primary = "allowed_harmful_rate_too_high"
    else:
        primary = "no_gap_promising_progress_support_descriptor_screen_found"
    return {"primary_gap": primary, "best_screen": best}


def _descriptor_coverage(
    rows: list[dict[str, Any]],
    specs: tuple[DescriptorSpec, ...],
) -> dict[str, Any]:
    return {spec.name: _coverage(rows, spec.name) for spec in specs}


def _coverage(rows: list[dict[str, Any]], name: str) -> dict[str, int]:
    finite = [
        row
        for row in rows
        if name in row["features"] and np.isfinite(float(row["features"][name]))
    ]
    return {"finite": len(finite), "total": len(rows)}


def _normalization(
    rows: list[dict[str, Any]],
    specs: tuple[DescriptorSpec, ...],
    *,
    percentile: float,
) -> dict[str, float]:
    result = {}
    for spec in specs:
        values = np.asarray(
            [row["features"].get(spec.name, np.nan) for row in rows],
            dtype=np.float64,
        )
        finite = np.abs(values[np.isfinite(values)])
        scale = float(np.percentile(finite, percentile)) if finite.size else 1.0
        if not np.isfinite(scale) or scale <= 1e-9:
            scale = 1.0
        result[spec.name] = scale
    return result


def _affine_values(
    rows: list[dict[str, Any]],
    names: tuple[str, ...],
    weights: tuple[float, ...],
    normalization: dict[str, float],
) -> np.ndarray:
    values = []
    for row in rows:
        total = 0.0
        ok = True
        for name, weight in zip(names, weights, strict=True):
            value = row["features"].get(name)
            if value is None or not np.isfinite(float(value)):
                ok = False
                break
            total += float(weight) * float(value) / float(normalization[name])
        values.append(total if ok else np.nan)
    return np.asarray(values, dtype=np.float64)


def _simplex_weights(term_count: int, denominator: int) -> list[tuple[float, ...]]:
    if term_count < 1 or denominator < term_count:
        return []
    weights = []
    for parts in itertools.product(range(1, denominator + 1), repeat=term_count):
        if sum(parts) == denominator:
            weights.append(tuple(part / denominator for part in parts))
    return weights


def _thresholds(values: np.ndarray) -> list[float]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return []
    return sorted(
        {float(np.percentile(finite, percentile)) for percentile in THRESHOLD_PERCENTILES}
    )


def _best_screen(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return max(rows, key=_screen_sort_key) if rows else None


def _screen_sort_key(row: dict[str, Any] | None) -> tuple[float, float, float, float, float]:
    if row is None:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    return (
        float(row.get("promising_screen", False)),
        float(row.get("harmful_block_rate", 0.0)),
        float(row.get("beneficial_retain_rate", 0.0)),
        -float(row.get("allowed_harmful_rate", 1.0)),
        float(row.get("considered_candidates", 0.0)),
    )


def _class_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        cls: sum(int(row["class"] == cls) for row in rows)
        for cls in (CLASS_BENEFICIAL, CLASS_HARMFUL, CLASS_NEUTRAL)
    }


def _auc_for_values(rows: list[dict[str, Any]], values: np.ndarray) -> float | None:
    pairs = [
        (float(value), row["class"])
        for row, value in zip(rows, values, strict=True)
        if np.isfinite(value) and row["class"] in {CLASS_BENEFICIAL, CLASS_HARMFUL}
    ]
    beneficial = [value for value, cls in pairs if cls == CLASS_BENEFICIAL]
    harmful = [value for value, cls in pairs if cls == CLASS_HARMFUL]
    if not beneficial or not harmful:
        return None
    wins = 0.0
    total = 0
    for good in beneficial:
        for bad in harmful:
            total += 1
            if good < bad:
                wins += 1.0
            elif good == bad:
                wins += 0.5
    return wins / total if total else None


def _rate(numerator: Any, denominator: Any) -> float:
    denominator = int(denominator)
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _mean(values: np.ndarray) -> float | None:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return None
    return float(np.mean(finite))


def _matrix(value: Any, rows: int, cols: int, label: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (rows, cols):
        raise ValueError(f"{label} shape={list(array.shape)} expected={[rows, cols]}.")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} contains nonfinite values.")
    return array


def _matrix_any_width(value: Any, rows: int, label: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 2 or array.shape[0] != rows or array.shape[1] < 1:
        raise ValueError(f"{label} shape={list(array.shape)} has invalid row/width.")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} contains nonfinite values.")
    return array


def _vector(value: Any, rows: int, label: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (rows,):
        raise ValueError(f"{label} shape={list(array.shape)} expected={[rows]}.")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} contains nonfinite values.")
    return array


def _finite_float(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be finite.") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite.")
    return result


def _record_seed(record: dict[str, Any]) -> int | None:
    for key in ("seed", "scenario_seed"):
        value = record.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        for key in ("seed", "scenario_seed"):
            value = metadata.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
    return None


def _path_seeds(path: Path) -> set[int]:
    return {
        int(match.group(1))
        for match in re.finditer(r"(?:^|[/\\])seed[_-]?(\d+)(?:[/\\]|$)", str(path))
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP CAMP Progress-Support Descriptor Separability Screen",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Best Screens",
        "",
        "| Rank | Screen | Promising | Harmful Block | Beneficial Retain | Allowed Harmful |",
        "| ---: | --- | --- | ---: | ---: | ---: |",
    ]
    for index, screen in enumerate(report["ranked_screens"][:10], start=1):
        lines.append(
            f"| {index} | `{screen['screen_name']}` | `{screen['promising_screen']}` | "
            f"{screen['harmful_block_rate']:.3f} | "
            f"{screen['beneficial_retain_rate']:.3f} | "
            f"{screen['allowed_harmful_rate']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Failure Gap",
            "",
            "```json",
            json.dumps(report["failure_gap"], indent=2, sort_keys=True),
            "```",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
