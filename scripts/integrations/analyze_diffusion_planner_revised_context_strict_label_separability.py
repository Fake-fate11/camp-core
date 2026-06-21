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
from scripts.integrations.analyze_diffusion_planner_revised_context_label_objective_audit import (  # noqa: E402
    HARD_FIELDS,
    READY_STATUS as LABEL_AUDIT_READY_STATUS,
    SAFETY_PENALTY_WEIGHTS,
    _finite_float,
    _optional_delta,
    _optional_finite_float,
    _safety_penalty,
)
from scripts.integrations.analyze_diffusion_planner_revised_progress_lane_hard_context_atom_separability import (  # noqa: E402
    ALLOWED_HARMFUL_RATE_TARGET,
    BENEFICIAL_RETAIN_RATE_TARGET,
    BLOCKED_ACTIONS,
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_NEUTRAL,
    CLASS_TOP1,
    HARMFUL_BLOCK_RATE_TARGET,
    MAX_AFFINE_TERMS,
    MAX_TOP_DESCRIPTORS,
    MIN_HARMFUL_CANDIDATES,
    NORMALIZATION_PERCENTILE,
    PAYLOAD_KEY,
    PROGRESS_LOSS_BUDGET_M,
    REVISED_ATOMS_KEY,
    SIMPLEX_DENOMINATOR,
    _affine_screens,
    _class_counts,
    _descriptor_coverage,
    _descriptor_specs,
    _descriptor_values,
    _failure_gap,
    _is_formal_seed,
    _load_json,
    _normalization,
    _path_seeds,
    _payload_descriptor_coverage,
    _record_candidate_count,
    _single_descriptor_screens,
    _validate_payload,
)


READY_STATUS = "revised_context_strict_label_separability_promising"
REJECT_STATUS = "revised_context_strict_label_separability_rejected"
SOURCE_BLOCKED_STATUS = "revised_context_strict_label_separability_source_not_ready"
FORMAL_SEED_STATUS = "revised_context_strict_label_separability_formal_seed_conflict"
MISSING_OUTCOMES_STATUS = (
    "revised_context_strict_label_separability_missing_outcomes"
)

SOURCE_PRIMARY_GAP = "beneficial_label_too_permissive_for_safety_score_intent"
SOURCE_NEXT_WORK = "predeclare_revised_label_or_atom_change_before_new_replay"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Re-label existing revised-context matched logs with a stricter "
            "offline comprehensive safety-score label, then screen revised "
            "atoms for fixed-candidate separability. This is offline-only and "
            "does not train CAMP, run DP, or alter the online selector."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label_objective_audit_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--progress_loss_budget_m",
        type=float,
        default=PROGRESS_LOSS_BUDGET_M,
    )
    parser.add_argument("--comfort_jerk_delta_budget", type=float, default=0.0)
    parser.add_argument("--comfort_lateral_delta_budget", type=float, default=0.0)
    parser.add_argument("--safety_improvement_margin", type=float, default=0.05)
    parser.add_argument("--harmful_safety_margin", type=float, default=0.05)
    parser.add_argument(
        "--min_strict_beneficial_candidates",
        type=int,
        default=8,
    )
    parser.add_argument(
        "--min_harmful_candidates",
        type=int,
        default=MIN_HARMFUL_CANDIDATES,
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
        label_objective_audit_report=_load_json(args.label_objective_audit_json),
        label=args.label,
        progress_loss_budget_m=args.progress_loss_budget_m,
        comfort_jerk_delta_budget=args.comfort_jerk_delta_budget,
        comfort_lateral_delta_budget=args.comfort_lateral_delta_budget,
        safety_improvement_margin=args.safety_improvement_margin,
        harmful_safety_margin=args.harmful_safety_margin,
        min_strict_beneficial_candidates=args.min_strict_beneficial_candidates,
        min_harmful_candidates=args.min_harmful_candidates,
        harmful_block_rate_target=args.harmful_block_rate_target,
        beneficial_retain_rate_target=args.beneficial_retain_rate_target,
        allowed_harmful_rate_target=args.allowed_harmful_rate_target,
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
    label_objective_audit_report: dict[str, Any],
    label: str | None = None,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    comfort_jerk_delta_budget: float = 0.0,
    comfort_lateral_delta_budget: float = 0.0,
    safety_improvement_margin: float = 0.05,
    harmful_safety_margin: float = 0.05,
    min_strict_beneficial_candidates: int = 8,
    min_harmful_candidates: int = MIN_HARMFUL_CANDIDATES,
    harmful_block_rate_target: float = HARMFUL_BLOCK_RATE_TARGET,
    beneficial_retain_rate_target: float = BENEFICIAL_RETAIN_RATE_TARGET,
    allowed_harmful_rate_target: float = ALLOWED_HARMFUL_RATE_TARGET,
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
        label_objective_audit_report=label_objective_audit_report,
        label=label,
        progress_loss_budget_m=progress_loss_budget_m,
        comfort_jerk_delta_budget=comfort_jerk_delta_budget,
        comfort_lateral_delta_budget=comfort_lateral_delta_budget,
        safety_improvement_margin=safety_improvement_margin,
        harmful_safety_margin=harmful_safety_margin,
        min_strict_beneficial_candidates=min_strict_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
        harmful_block_rate_target=harmful_block_rate_target,
        beneficial_retain_rate_target=beneficial_retain_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
        max_top_descriptors=max_top_descriptors,
        max_affine_terms=max_affine_terms,
        simplex_denominator=simplex_denominator,
        normalization_percentile=normalization_percentile,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    label_objective_audit_report: dict[str, Any],
    label: str | None = None,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    comfort_jerk_delta_budget: float = 0.0,
    comfort_lateral_delta_budget: float = 0.0,
    safety_improvement_margin: float = 0.05,
    harmful_safety_margin: float = 0.05,
    min_strict_beneficial_candidates: int = 8,
    min_harmful_candidates: int = MIN_HARMFUL_CANDIDATES,
    harmful_block_rate_target: float = HARMFUL_BLOCK_RATE_TARGET,
    beneficial_retain_rate_target: float = BENEFICIAL_RETAIN_RATE_TARGET,
    allowed_harmful_rate_target: float = ALLOWED_HARMFUL_RATE_TARGET,
    max_top_descriptors: int = MAX_TOP_DESCRIPTORS,
    max_affine_terms: int = MAX_AFFINE_TERMS,
    simplex_denominator: int = SIMPLEX_DENOMINATOR,
    normalization_percentile: float = NORMALIZATION_PERCENTILE,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")

    source = _source_gate(label_objective_audit_report)
    descriptor_specs = _descriptor_specs()
    rows: list[dict[str, Any]] = []
    payload_rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    missing_outcome_records = 0
    outcome_records = 0

    for index, item in enumerate(items):
        raw = item["raw"]
        context = item["context"]
        label_prefix = f"record {index}"
        payload = raw.get(PAYLOAD_KEY)
        outcomes = raw.get("candidate_closed_loop_outcomes")
        candidate_count = _record_candidate_count(raw, payload, outcomes, label_prefix)
        _validate_payload(payload, candidate_count, label_prefix)
        formal_seed_records += int(_is_formal_seed(raw, context))
        feature_values = _descriptor_values(
            payload,
            descriptor_specs,
            candidate_count,
            label_prefix,
        )
        payload_rows.extend(
            {
                "context": context,
                "candidate_index": candidate_index,
                "features": {
                    name: float(values[candidate_index])
                    for name, values in feature_values.items()
                    if np.isfinite(values[candidate_index])
                },
            }
            for candidate_index in range(candidate_count)
        )
        if not isinstance(outcomes, list) or len(outcomes) != candidate_count:
            missing_outcome_records += 1
            continue
        outcome_records += 1
        rows.extend(
            _strict_candidate_rows(
                raw,
                context,
                label_prefix,
                descriptor_specs,
                feature_values=feature_values,
                progress_loss_budget_m=progress_loss_budget_m,
                comfort_jerk_delta_budget=comfort_jerk_delta_budget,
                comfort_lateral_delta_budget=comfort_lateral_delta_budget,
                safety_improvement_margin=safety_improvement_margin,
                harmful_safety_margin=harmful_safety_margin,
            )
        )

    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    alternative_rows = [row for row in rows if row["class"] != CLASS_TOP1]
    class_counts = _class_counts(alternative_rows)
    normalization = _normalization(
        alternative_rows,
        descriptor_specs,
        percentile=normalization_percentile,
    )
    single_screens: list[dict[str, Any]] = []
    affine_screens: list[dict[str, Any]] = []
    ranked: list[dict[str, Any]] = []
    if source["passed"] and not missing_outcome_records and rows:
        single_screens = _single_descriptor_screens(
            alternative_rows,
            descriptor_specs,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            allowed_harmful_rate_target=allowed_harmful_rate_target,
            min_beneficial_candidates=min_strict_beneficial_candidates,
            min_harmful_candidates=min_harmful_candidates,
        )
        affine_screens = _affine_screens(
            alternative_rows,
            single_screens,
            normalization,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            allowed_harmful_rate_target=allowed_harmful_rate_target,
            min_beneficial_candidates=min_strict_beneficial_candidates,
            min_harmful_candidates=min_harmful_candidates,
            max_top_descriptors=max_top_descriptors,
            max_affine_terms=max_affine_terms,
            simplex_denominator=simplex_denominator,
        )
        ranked = sorted(
            [*single_screens, *affine_screens],
            key=_strict_screen_sort_key,
            reverse=True,
        )

    decision = _decision(
        source,
        ranked,
        class_counts,
        formal_seed_records=formal_seed_records,
        missing_outcome_records=missing_outcome_records,
        min_strict_beneficial_candidates=min_strict_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
    )
    return {
        "analysis": {
            "name": "dp_camp_revised_context_strict_label_separability_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_atoms": False,
            "future_outcome_labels_used_for_strict_label": bool(outcome_records),
            "thresholds_are_offline_oracle_diagnostics": True,
            "top1_reference_candidate_index": 0,
            "descriptor_specs": [spec.__dict__ for spec in descriptor_specs],
            "strict_label_definition": {
                "beneficial": (
                    "candidate k>0 has lower diagnostic safety penalty than "
                    "Top-1 by safety_improvement_margin, is feasible, has no "
                    "hard-safety regression, preserves progress within the "
                    "budget, and has no jerk/lateral comfort regression beyond "
                    "the declared budgets"
                ),
                "harmful": (
                    "candidate k>0 is infeasible, hard-safety-worse, loses "
                    "progress beyond budget, worsens jerk/lateral beyond "
                    "budget, or increases diagnostic safety penalty by "
                    "harmful_safety_margin"
                ),
                "neutral": "all other k>0 candidates",
                "diagnostic_safety_penalty_direction": "lower_is_better",
            },
            "diagnostic_parameters": {
                "progress_loss_budget_m": progress_loss_budget_m,
                "comfort_jerk_delta_budget": comfort_jerk_delta_budget,
                "comfort_lateral_delta_budget": comfort_lateral_delta_budget,
                "safety_improvement_margin": safety_improvement_margin,
                "harmful_safety_margin": harmful_safety_margin,
                "safety_penalty_weights": SAFETY_PENALTY_WEIGHTS,
            },
            "accept_criteria": {
                "min_strict_beneficial_candidates": int(
                    min_strict_beneficial_candidates
                ),
                "min_harmful_candidates": int(min_harmful_candidates),
                "harmful_block_rate": f">= {harmful_block_rate_target}",
                "beneficial_retain_rate": f">= {beneficial_retain_rate_target}",
                "allowed_harmful_rate": f"<= {allowed_harmful_rate_target}",
            },
            "math_boundary": (
                "This audit only relabels fixed DP candidates with offline "
                "closed-loop outcomes. Revised atom values are read from the "
                "current-tick default-off payload and are not recomputed from "
                "outcomes. Nonnegative simplex scalarizations preserve affine "
                "score_k(w)=a_k^T w if later atomized for the CAMP "
                "simplex/CVaR/L2 convex master. No DP-side classical Benders "
                "master/subproblem, dual, or cut is constructed."
            ),
        },
        "source_label_objective_gate": source,
        "records": {
            "total_records": len(items),
            "outcome_records": outcome_records,
            "missing_outcome_records": missing_outcome_records,
            "candidate_rows": len(payload_rows),
            "classified_candidate_rows": len(rows),
            "alternative_rows": len(alternative_rows),
            "formal_seed_records": formal_seed_records,
            "class_counts": class_counts,
            "records_with_strict_beneficial": len(
                {
                    row["record_key"]
                    for row in alternative_rows
                    if row["class"] == CLASS_BENEFICIAL
                }
            ),
        },
        "strict_label_summary": _strict_label_summary(alternative_rows),
        "payload_descriptor_coverage": _payload_descriptor_coverage(
            payload_rows,
            descriptor_specs,
        ),
        "descriptor_coverage": _descriptor_coverage(alternative_rows, descriptor_specs),
        "normalization": normalization,
        "single_descriptor_screens": single_screens[:50],
        "affine_screens": affine_screens[:50],
        "ranked_screens": ranked[:50],
        "failure_gap": _failure_gap(ranked, class_counts),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _strict_candidate_rows(
    raw: dict[str, Any],
    context: dict[str, Any],
    label: str,
    descriptor_specs: tuple[Any, ...],
    *,
    feature_values: dict[str, np.ndarray],
    progress_loss_budget_m: float,
    comfort_jerk_delta_budget: float,
    comfort_lateral_delta_budget: float,
    safety_improvement_margin: float,
    harmful_safety_margin: float,
) -> list[dict[str, Any]]:
    outcomes = raw.get("candidate_closed_loop_outcomes")
    candidate_count = len(outcomes)
    parsed = [_parse_outcome(outcome, f"{label} outcome {i}") for i, outcome in enumerate(outcomes)]
    top1 = parsed[0]
    rows = []
    for candidate_index, outcome in enumerate(parsed):
        value_delta = outcome["value"] - top1["value"]
        progress_delta = outcome["progress_m"] - top1["progress_m"]
        jerk_delta = _optional_delta(
            outcome["mean_jerk_mps3"],
            top1["mean_jerk_mps3"],
        )
        lateral_delta = _optional_delta(
            outcome["mean_lateral_acceleration_mps2"],
            top1["mean_lateral_acceleration_mps2"],
        )
        hard_worse = any(outcome[field] and not top1[field] for field in HARD_FIELDS)
        feasible_worse = top1["feasible"] and not outcome["feasible"]
        safety_penalty_delta = outcome["safety_penalty"] - top1["safety_penalty"]
        progress_compatible = progress_delta >= -float(progress_loss_budget_m)
        jerk_compatible = (
            jerk_delta is None or jerk_delta <= float(comfort_jerk_delta_budget)
        )
        lateral_compatible = (
            lateral_delta is None
            or lateral_delta <= float(comfort_lateral_delta_budget)
        )
        beneficial = (
            candidate_index != 0
            and outcome["feasible"]
            and not hard_worse
            and progress_compatible
            and jerk_compatible
            and lateral_compatible
            and safety_penalty_delta <= -float(safety_improvement_margin)
        )
        harmful = (
            candidate_index != 0
            and (
                not outcome["feasible"]
                or hard_worse
                or feasible_worse
                or not progress_compatible
                or not jerk_compatible
                or not lateral_compatible
                or safety_penalty_delta >= float(harmful_safety_margin)
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
        row = {
            "context": context,
            "record_key": f"{context.get('log_path')}#{context.get('record_index')}",
            "candidate_index": candidate_index,
            "class": cls,
            "outcome_value_delta_vs_top1": value_delta,
            "progress_delta_vs_top1_m": progress_delta,
            "safety_penalty_delta_vs_top1": safety_penalty_delta,
            "mean_jerk_delta_vs_top1_mps3": jerk_delta,
            "mean_lateral_acceleration_delta_vs_top1_mps2": lateral_delta,
            "hard_safety_worse_than_top1": bool(hard_worse or feasible_worse),
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
            "progress_compatible": progress_compatible,
            "jerk_compatible": jerk_compatible,
            "lateral_compatible": lateral_compatible,
            "features": {
                spec.name: float(feature_values[spec.name][candidate_index])
                for spec in descriptor_specs
                if np.isfinite(feature_values[spec.name][candidate_index])
            },
        }
        rows.append(row)
    if len(rows) != candidate_count:
        raise ValueError(f"{label} row construction failed.")
    return rows


def _parse_outcome(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object.")
    required = ("value", "feasible", "progress_m")
    missing = [field for field in required if field not in raw]
    if missing:
        raise ValueError(f"{label} missing {missing}.")
    outcome = {
        "value": _finite_float(raw["value"], f"{label}.value"),
        "feasible": bool(raw["feasible"]),
        "progress_m": _finite_float(raw["progress_m"], f"{label}.progress_m"),
        "mean_jerk_mps3": _optional_finite_float(raw.get("mean_jerk_mps3")),
        "mean_lateral_acceleration_mps2": _optional_finite_float(
            raw.get("mean_lateral_acceleration_mps2")
        ),
    }
    for field in HARD_FIELDS:
        outcome[field] = bool(raw.get(field))
    outcome["safety_penalty"] = _safety_penalty(outcome)
    return outcome


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    status = decision.get("status")
    primary_gap = decision.get("primary_gap")
    next_work = decision.get("authorized_next_work")
    passed = (
        bool(decision.get("passed"))
        and status == LABEL_AUDIT_READY_STATUS
        and primary_gap == SOURCE_PRIMARY_GAP
        and next_work == SOURCE_NEXT_WORK
    )
    return {
        "passed": passed,
        "status": status,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
    }


def _decision(
    source: dict[str, Any],
    ranked: list[dict[str, Any]],
    class_counts: dict[str, int],
    *,
    formal_seed_records: int,
    missing_outcome_records: int,
    min_strict_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> dict[str, Any]:
    promising = [row for row in ranked if row["promising_screen"]]
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "label_objective_audit_gate_not_passed"
        next_work = "fix_label_objective_audit_before_strict_label_screen"
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        next_work = None
    elif missing_outcome_records:
        status = MISSING_OUTCOMES_STATUS
        primary_gap = "candidate_closed_loop_outcomes_missing_for_strict_label"
        next_work = "rerun_matched_outcome_collection_before_strict_label_screen"
    elif class_counts.get(CLASS_BENEFICIAL, 0) < int(min_strict_beneficial_candidates):
        status = REJECT_STATUS
        primary_gap = "strict_beneficial_support_insufficient"
        next_work = "relax_or_redefine_strict_label_or_expand_nonformal_support"
    elif class_counts.get(CLASS_HARMFUL, 0) < int(min_harmful_candidates):
        status = REJECT_STATUS
        primary_gap = "strict_harmful_support_insufficient"
        next_work = "expand_strict_label_harmful_support_before_selector_design"
    elif promising:
        status = READY_STATUS
        primary_gap = "no_gap_promising_strict_label_revised_atom_screen_found"
        next_work = "offline_strict_label_revised_atom_certificate_design_only"
    else:
        status = REJECT_STATUS
        primary_gap = "strict_label_revised_atoms_do_not_separate_candidates"
        next_work = "diagnose_strict_label_atom_bottleneck_before_replay"
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        "promising_screen_count": len(promising),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _strict_label_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_class = {
        CLASS_BENEFICIAL: [row for row in rows if row["class"] == CLASS_BENEFICIAL],
        CLASS_HARMFUL: [row for row in rows if row["class"] == CLASS_HARMFUL],
        CLASS_NEUTRAL: [row for row in rows if row["class"] == CLASS_NEUTRAL],
    }
    return {
        "beneficial": _row_summary(by_class[CLASS_BENEFICIAL]),
        "harmful": _row_summary(by_class[CLASS_HARMFUL]),
        "neutral": _row_summary(by_class[CLASS_NEUTRAL]),
    }


def _row_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(rows),
        "value_delta_mean": _mean(
            [row["outcome_value_delta_vs_top1"] for row in rows]
        ),
        "progress_delta_mean_m": _mean(
            [row["progress_delta_vs_top1_m"] for row in rows]
        ),
        "safety_penalty_delta_mean": _mean(
            [row["safety_penalty_delta_vs_top1"] for row in rows]
        ),
        "jerk_delta_mean_mps3": _mean(
            [row["mean_jerk_delta_vs_top1_mps3"] for row in rows]
        ),
        "lateral_delta_mean_mps2": _mean(
            [row["mean_lateral_acceleration_delta_vs_top1_mps2"] for row in rows]
        ),
    }


def _mean(values: list[Any]) -> float | None:
    array = np.asarray([value for value in values if value is not None], dtype=np.float64)
    array = array[np.isfinite(array)]
    if array.size == 0:
        return None
    return float(np.mean(array))


def _strict_screen_sort_key(row: dict[str, Any] | None) -> tuple[float, float, float, float, float]:
    if row is None:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    return (
        float(row.get("promising_screen", False)),
        float(row.get("harmful_block_rate", 0.0)),
        float(row.get("beneficial_retain_rate", 0.0)),
        -float(row.get("allowed_harmful_rate", 1.0)),
        float(row.get("considered_candidates", 0.0)),
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Revised Context Strict Label Separability",
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
        "## Strict Label Summary",
        "",
        "```json",
        json.dumps(report["strict_label_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Payload Descriptor Coverage",
        "",
        "```json",
        json.dumps(report["payload_descriptor_coverage"], indent=2, sort_keys=True),
        "```",
        "",
        "## Best Screens",
        "",
        "| Rank | Screen | Promising | Harmful Block | Beneficial Retain | Allowed Harmful |",
        "| ---: | --- | --- | ---: | ---: | ---: |",
    ]
    for index, screen in enumerate(report["ranked_screens"][:10], start=1):
        lines.append(
            "| "
            f"{index} | `{screen['screen_name']}` | "
            f"{screen['promising_screen']} | "
            f"{screen['harmful_block_rate']:.6f} | "
            f"{screen['beneficial_retain_rate']:.6f} | "
            f"{screen['allowed_harmful_rate']:.6f} |"
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
