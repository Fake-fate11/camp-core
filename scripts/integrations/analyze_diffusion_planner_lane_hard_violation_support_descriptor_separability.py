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
from camp_core.integrations.diffusion_planner_lane_hard_violation_support import (  # noqa: E402
    LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES,
    LANE_HARD_VIOLATION_SUPPORT_FIELD_NAMES,
    LANE_HARD_VIOLATION_SUPPORT_LOGGING_SCHEMA_VERSION,
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
    _load_json,
    _matrix,
    _matrix_any_width,
    _normalization,
    _outcome,
    _path_seeds,
    _record_candidate_count,
    _record_seed,
    _screen_sort_key,
    _single_descriptor_screens,
    _vector,
)


READY_STATUS = (
    "lane_hard_violation_support_descriptor_separability_promising_for_certificate_design"
)
REJECT_STATUS = "lane_hard_violation_support_descriptor_separability_rejected"
SOURCE_BLOCKED_STATUS = (
    "lane_hard_violation_support_descriptor_separability_source_not_ready"
)
FORMAL_SEED_STATUS = "lane_hard_violation_support_descriptor_separability_formal_seed_conflict"

CONTRACT_READY_STATUS = "matched_lane_hard_violation_support_outcome_contract_passed"
CONTRACT_NEXT_WORK = (
    "offline_lane_hard_violation_support_descriptor_separability_screen_only"
)

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
class DerivedDescriptorSpec:
    name: str
    source: str
    rationale: str


DERIVED_DESCRIPTOR_SPECS: tuple[DerivedDescriptorSpec, ...] = (
    DerivedDescriptorSpec(
        "max_lateral_envelope_excess_m",
        "candidate_route_lateral_error_profile_m/candidate_route_corridor_half_width_profile_m",
        "maximum current-tick support-horizon lateral envelope excess",
    ),
    DerivedDescriptorSpec(
        "final_lateral_envelope_excess_m",
        "candidate_route_lateral_error_profile_m/candidate_route_corridor_half_width_profile_m",
        "final support-horizon lateral envelope excess",
    ),
    DerivedDescriptorSpec(
        "max_abs_lateral_error_worse_vs_top1_m",
        "candidate_route_lateral_error_profile_m",
        "extra absolute lateral route error versus DP Top-1",
    ),
    DerivedDescriptorSpec(
        "max_heading_error_rad",
        "candidate_route_heading_error_profile_rad",
        "maximum route-heading divergence over the support horizon",
    ),
    DerivedDescriptorSpec(
        "max_heading_error_worse_vs_top1_rad",
        "candidate_route_heading_error_profile_rad",
        "extra route-heading divergence versus DP Top-1",
    ),
    DerivedDescriptorSpec(
        "max_lateral_error_rate_abs_mps",
        "candidate_lateral_error_rate_profile_mps",
        "maximum absolute lateral-error growth rate",
    ),
    DerivedDescriptorSpec(
        "max_lateral_error_rate_worse_vs_top1_mps",
        "candidate_lateral_error_rate_profile_mps",
        "extra lateral-error growth rate versus DP Top-1",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline no-leak separability screen over matched DP-CAMP "
            "lane/hard-violation support descriptors and candidate outcome "
            "labels. This is an oracle diagnostic over existing nonformal "
            "logs, not CAMP training and not an online selector."
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
    ranked = sorted([*single_screens, *affine_screens], key=_screen_sort_key, reverse=True)
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
            "name": "dp_camp_lane_hard_violation_support_descriptor_separability_v1",
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
                "Lane/hard-violation support descriptors are fixed current-tick "
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
            source="lane_hard_violation_support_atoms",
            rationale=(
                "nonnegative lane/hard-violation support atom emitted by the "
                "runtime payload; lower value is lower diagnostic risk"
            ),
        )
        for name in LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES
    )
    derived = tuple(
        DescriptorSpec(
            name=spec.name,
            source=spec.source,
            rationale=spec.rationale,
        )
        for spec in DERIVED_DESCRIPTOR_SPECS
    )
    return (*atom_specs, *derived)


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
    payload = raw.get("lane_hard_violation_support_logging")
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
        payload.get("lane_hard_violation_support_atoms"),
        candidate_count,
        len(LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES),
        f"{label} lane_hard_violation_support_atoms",
    )
    lateral_error = _matrix_any_width(
        payload.get("candidate_route_lateral_error_profile_m"),
        candidate_count,
        f"{label} candidate_route_lateral_error_profile_m",
    )
    corridor = _matrix_any_width(
        payload.get("candidate_route_corridor_half_width_profile_m"),
        candidate_count,
        f"{label} candidate_route_corridor_half_width_profile_m",
    )
    heading = _matrix_any_width(
        payload.get("candidate_route_heading_error_profile_rad"),
        candidate_count,
        f"{label} candidate_route_heading_error_profile_rad",
    )
    lateral_rate = _matrix_any_width(
        payload.get("candidate_lateral_error_rate_profile_mps"),
        candidate_count,
        f"{label} candidate_lateral_error_rate_profile_mps",
    )
    if corridor.shape != lateral_error.shape or heading.shape != lateral_error.shape:
        raise ValueError(f"{label} lane/hard profile shapes do not match.")

    abs_lateral = np.abs(lateral_error)
    envelope_excess = np.maximum(abs_lateral - corridor, 0.0)
    abs_rate = np.abs(lateral_rate)
    values: dict[str, np.ndarray] = {}
    for atom_index, atom_name in enumerate(LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES):
        values[f"atom_{atom_name}"] = np.maximum(atoms[:, atom_index], 0.0)
    values["max_lateral_envelope_excess_m"] = np.max(envelope_excess, axis=1)
    values["final_lateral_envelope_excess_m"] = envelope_excess[:, -1]
    values["max_abs_lateral_error_worse_vs_top1_m"] = np.max(
        np.maximum(abs_lateral - abs_lateral[0:1, :], 0.0),
        axis=1,
    )
    values["max_heading_error_rad"] = np.max(np.abs(heading), axis=1)
    values["max_heading_error_worse_vs_top1_rad"] = np.max(
        np.maximum(np.abs(heading) - np.abs(heading[0:1, :]), 0.0),
        axis=1,
    )
    values["max_lateral_error_rate_abs_mps"] = np.max(abs_rate, axis=1)
    values["max_lateral_error_rate_worse_vs_top1_mps"] = np.max(
        np.maximum(abs_rate - abs_rate[0:1, :], 0.0),
        axis=1,
    )
    expected = {spec.name for spec in descriptor_specs}
    missing = sorted(expected - set(values))
    if missing:
        raise ValueError(f"{label} missing descriptor values {missing}.")
    return values


def _validate_payload(payload: Any, candidate_count: int, label: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} missing lane_hard_violation_support_logging payload.")
    expected = {
        "schema_version": LANE_HARD_VIOLATION_SUPPORT_LOGGING_SCHEMA_VERSION,
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
                f"{label} lane_hard_violation_support_logging "
                f"{field}={payload.get(field)!r}."
            )
    if "candidate_closed_loop_outcomes" in payload:
        raise ValueError(f"{label} lane/hard payload embeds outcome labels.")
    if payload.get("candidate_count") != candidate_count:
        raise ValueError(f"{label} lane/hard candidate_count mismatch.")
    finite_checks = payload.get("finite_checks")
    if not isinstance(finite_checks, dict):
        raise ValueError(f"{label} lane/hard finite checks missing.")
    for field in (
        *LANE_HARD_VIOLATION_SUPPORT_FIELD_NAMES,
        "lane_hard_violation_support_atoms",
        "lane_hard_violation_support_atoms_nonnegative",
    ):
        if finite_checks.get(field) is not True:
            raise ValueError(f"{label} lane/hard finite check failed {field}.")


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
        primary_gap = "matched_lane_hard_support_contract_gate_not_passed"
        next_work = "fix_matched_lane_hard_support_outcome_contract_before_separability"
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        next_work = None
    elif class_counts.get(CLASS_BENEFICIAL, 0) < int(min_beneficial_candidates):
        status = REJECT_STATUS
        primary_gap = "beneficial_candidate_support_insufficient"
        next_work = "expand_matched_lane_hard_support_label_coverage_before_selector_design"
    elif class_counts.get(CLASS_HARMFUL, 0) < int(min_harmful_candidates):
        status = REJECT_STATUS
        primary_gap = "harmful_candidate_support_insufficient"
        next_work = "expand_matched_lane_hard_support_label_coverage_before_selector_design"
    elif promising:
        status = READY_STATUS
        primary_gap = "no_gap_promising_lane_hard_support_descriptor_screen_found"
        next_work = "offline_lane_hard_violation_support_certificate_design_only"
    else:
        status = REJECT_STATUS
        primary_gap = "lane_hard_violation_support_descriptors_do_not_separate_candidates"
        next_work = "diagnose_lane_hard_support_descriptor_bottleneck_before_retraining"
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
        primary = "no_finite_lane_hard_support_descriptor_screen"
    elif best["harmful_block_rate"] < HARMFUL_BLOCK_RATE_TARGET:
        primary = "harmful_block_rate_insufficient"
    elif best["beneficial_retain_rate"] < BENEFICIAL_RETAIN_RATE_TARGET:
        primary = "beneficial_retain_rate_insufficient"
    elif best["allowed_harmful_rate"] > ALLOWED_HARMFUL_RATE_TARGET:
        primary = "allowed_harmful_rate_too_high"
    else:
        primary = "no_gap_promising_lane_hard_support_descriptor_screen_found"
    return {"primary_gap": primary, "best_screen": best}


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP CAMP Lane/Hard Support Descriptor Separability",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Top Screens",
        "",
        "| Rank | Screen | Promising | Harmful block | Beneficial retain | Allowed harmful |",
        "| ---: | --- | --- | ---: | ---: | ---: |",
    ]
    for index, row in enumerate(report["ranked_screens"][:10], start=1):
        lines.append(
            f"| {index} | `{row['screen_name']}` | `{row['promising_screen']}` | "
            f"{row['harmful_block_rate']:.6f} | "
            f"{row['beneficial_retain_rate']:.6f} | "
            f"{row['allowed_harmful_rate']:.6f} |"
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
