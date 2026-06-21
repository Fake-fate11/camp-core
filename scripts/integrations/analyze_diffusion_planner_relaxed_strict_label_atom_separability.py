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
from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (  # noqa: E402
    PROGRESS_LANE_HARD_CONTEXT_RELAXED_STRICT_ATOM_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_RELAXED_STRICT_ATOM_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_revised_context_relaxed_strict_label_atom_bottleneck import (  # noqa: E402
    _grid_params,
    _selected_grid,
    _source_gate as _sensitivity_source_gate,
)
from scripts.integrations.analyze_diffusion_planner_revised_context_strict_label_separability import (  # noqa: E402
    _strict_candidate_rows,
)
from scripts.integrations.analyze_diffusion_planner_revised_progress_lane_hard_context_atom_separability import (  # noqa: E402
    ALLOWED_HARMFUL_RATE_TARGET,
    BENEFICIAL_RETAIN_RATE_TARGET,
    BLOCKED_ACTIONS as BASE_BLOCKED_ACTIONS,
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_TOP1,
    HARMFUL_BLOCK_RATE_TARGET,
    MAX_AFFINE_TERMS,
    MAX_TOP_DESCRIPTORS,
    MIN_BENEFICIAL_CANDIDATES,
    MIN_HARMFUL_CANDIDATES,
    NORMALIZATION_PERCENTILE,
    SIMPLEX_DENOMINATOR,
    DescriptorSpec,
    _affine_screens,
    _class_counts,
    _descriptor_coverage,
    _failure_gap,
    _load_json,
    _normalization,
    _path_seeds,
    _payload_descriptor_coverage,
    _screen_sort_key,
    _single_descriptor_screens,
)
from scripts.integrations.analyze_diffusion_planner_revised_context_relaxed_strict_label_atom_schema_preflight import (  # noqa: E402
    ATOM_SPECS as RELAXED_STRICT_ATOM_SPECS,
    NEXT_WORK as PREFLIGHT_NEXT_WORK,
    READY_STATUS as PREFLIGHT_READY_STATUS,
    _atom_values as _preflight_atom_values,
    _record as _preflight_record,
)


READY_STATUS = "relaxed_strict_label_atom_separability_promising"
REJECT_STATUS = "relaxed_strict_label_atom_separability_rejected"
SOURCE_BLOCKED_STATUS = "relaxed_strict_label_atom_separability_source_not_ready"
FORMAL_SEED_STATUS = "relaxed_strict_label_atom_separability_formal_seed_conflict"
MISSING_OUTCOMES_STATUS = (
    "relaxed_strict_label_atom_separability_missing_outcome_labels"
)

NEXT_WORK_CERTIFICATE = "offline_relaxed_strict_label_atom_certificate_design_only"
NEXT_WORK_DIAGNOSIS = (
    "diagnose_relaxed_strict_label_atom_separability_bottleneck_before_replay"
)
NEXT_WORK_SUPPORT = "expand_relaxed_strict_label_matched_support_before_selector_design"

BLOCKED_ACTIONS = (
    *BASE_BLOCKED_ACTIONS,
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline no-leak separability screen over the relaxed strict-label "
            "atom family. Atom values are computed from current-tick context "
            "payload fields; candidate closed-loop outcomes are used only as "
            "offline beneficial/harmful labels."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--preflight_json", type=Path, required=True)
    parser.add_argument("--sensitivity_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--grid_choice",
        choices=("best_by_support", "best_by_screen"),
        default="best_by_support",
    )
    parser.add_argument("--harmful_block_rate_target", type=float, default=HARMFUL_BLOCK_RATE_TARGET)
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
    parser.add_argument("--min_beneficial_candidates", type=int, default=MIN_BENEFICIAL_CANDIDATES)
    parser.add_argument("--min_harmful_candidates", type=int, default=MIN_HARMFUL_CANDIDATES)
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
        preflight_report=_load_json(args.preflight_json),
        sensitivity_report=_load_json(args.sensitivity_json),
        label=args.label,
        grid_choice=args.grid_choice,
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
    preflight_report: dict[str, Any],
    sensitivity_report: dict[str, Any],
    label: str | None = None,
    grid_choice: str = "best_by_support",
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
        preflight_report=preflight_report,
        sensitivity_report=sensitivity_report,
        label=label,
        grid_choice=grid_choice,
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
    preflight_report: dict[str, Any],
    sensitivity_report: dict[str, Any],
    label: str | None = None,
    grid_choice: str = "best_by_support",
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

    preflight = _preflight_gate(preflight_report)
    sensitivity = _sensitivity_source_gate(sensitivity_report)
    selected_grid = _selected_grid(sensitivity_report, grid_choice)
    params = _grid_params(selected_grid)
    descriptor_specs = _descriptor_specs()

    payload_rows: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    missing_outcome_records = 0
    outcome_records = 0

    for index, item in enumerate(items):
        raw = item["raw"]
        context = item["context"]
        label_prefix = f"record {index}"
        feature_values, candidate_count, formal_seed = _feature_values(
            raw,
            context,
            label_prefix,
            descriptor_specs,
        )
        formal_seed_records += int(formal_seed)
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
        outcomes = raw.get("candidate_closed_loop_outcomes")
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
                progress_loss_budget_m=params["progress_loss_budget_m"],
                comfort_jerk_delta_budget=params["comfort_jerk_delta_budget"],
                comfort_lateral_delta_budget=params["comfort_lateral_delta_budget"],
                safety_improvement_margin=params["safety_improvement_margin"],
                harmful_safety_margin=params["harmful_safety_margin"],
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
    source_ready = bool(preflight["passed"] and sensitivity["passed"] and selected_grid)
    single_screens: list[dict[str, Any]] = []
    affine_screens: list[dict[str, Any]] = []
    ranked: list[dict[str, Any]] = []
    if source_ready and not missing_outcome_records and rows:
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
        preflight,
        sensitivity,
        selected_grid,
        ranked,
        class_counts,
        formal_seed_records=formal_seed_records,
        missing_outcome_records=missing_outcome_records,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
    )
    return {
        "analysis": {
            "name": "dp_camp_relaxed_strict_label_atom_separability_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_atoms": False,
            "future_outcome_labels_used_for_classification": bool(outcome_records),
            "future_outcome_labels_used_for_thresholds": bool(outcome_records),
            "future_outcome_labels_used_for_evaluation": bool(outcome_records),
            "thresholds_are_offline_oracle_diagnostics": True,
            "top1_reference_candidate_index": 0,
            "runtime_atom_schema_version": (
                PROGRESS_LANE_HARD_CONTEXT_RELAXED_STRICT_ATOM_SCHEMA_VERSION
            ),
            "runtime_atom_names": list(PROGRESS_LANE_HARD_CONTEXT_RELAXED_STRICT_ATOM_NAMES),
            "descriptor_specs": [spec.__dict__ for spec in descriptor_specs],
            "selected_grid_params": params,
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
                "Relaxed strict-label atoms are recomputed from current-tick "
                "speed, lateral-rate, heading-error, and corridor-margin "
                "profiles already present in the default-off context payload. "
                "Candidate closed-loop outcomes define only offline labels and "
                "oracle screen thresholds. Each atom value is a fixed "
                "nonnegative finite-candidate coefficient a_k before weight "
                "optimization; CAMP scoring remains affine score_k(w)=a_k^T w "
                "and the simplex/CVaR/L2 master remains convex in w. Products "
                "are products of fixed descriptors, not trajectory-coordinate "
                "optimization. No DP-side classical Benders master/subproblem, "
                "dual, or cut is constructed."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "preflight_gate": preflight,
        "sensitivity_gate": sensitivity,
        "selected_grid": selected_grid,
        "records": {
            "total_records": len(items),
            "outcome_records": outcome_records,
            "missing_outcome_records": missing_outcome_records,
            "candidate_rows": len(payload_rows),
            "classified_candidate_rows": len(rows),
            "alternative_rows": len(alternative_rows),
            "formal_seed_records": formal_seed_records,
            "class_counts": class_counts,
        },
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


def _descriptor_specs() -> tuple[DescriptorSpec, ...]:
    return tuple(
        DescriptorSpec(
            name=f"relaxed_strict_atom_{name}",
            source="computed_from_progress_lane_hard_context_logging_fields",
            rationale=(
                "nonnegative relaxed strict-label atom recomputed from "
                "current-tick context fields; lower value is lower diagnostic risk"
            ),
        )
        for name in PROGRESS_LANE_HARD_CONTEXT_RELAXED_STRICT_ATOM_NAMES
    )


def _feature_values(
    raw: dict[str, Any],
    context: dict[str, Any],
    label: str,
    descriptor_specs: tuple[DescriptorSpec, ...],
) -> tuple[dict[str, np.ndarray], int, bool]:
    record, formal_seed = _preflight_record(raw, context, label)
    values: dict[str, np.ndarray] = {}
    for runtime_name, spec in zip(
        PROGRESS_LANE_HARD_CONTEXT_RELAXED_STRICT_ATOM_NAMES,
        RELAXED_STRICT_ATOM_SPECS,
    ):
        if spec.name != runtime_name:
            raise ValueError("Runtime relaxed strict atom names do not match preflight spec.")
        key = f"relaxed_strict_atom_{runtime_name}"
        values[key] = _preflight_atom_values(spec, record)
    expected = {spec.name for spec in descriptor_specs}
    missing = sorted(expected - set(values))
    if missing:
        raise ValueError(f"{label} missing relaxed strict atom values {missing}.")
    return values, int(record["candidate_count"]), formal_seed


def _preflight_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    analysis = report.get("analysis") if isinstance(report, dict) else None
    if not isinstance(analysis, dict):
        analysis = {}
    status = decision.get("status")
    next_work = decision.get("authorized_next_work")
    passed = (
        bool(decision.get("passed"))
        and status == PREFLIGHT_READY_STATUS
        and next_work == PREFLIGHT_NEXT_WORK
        and analysis.get("future_outcome_labels_used_for_atoms") is False
    )
    return {
        "passed": passed,
        "status": status,
        "primary_gap": decision.get("primary_gap"),
        "authorized_next_work": next_work,
        "future_outcome_labels_used_for_atoms": analysis.get(
            "future_outcome_labels_used_for_atoms"
        ),
    }


def _decision(
    preflight: dict[str, Any],
    sensitivity: dict[str, Any],
    selected_grid: dict[str, Any] | None,
    ranked: list[dict[str, Any]],
    class_counts: dict[str, int],
    *,
    formal_seed_records: int,
    missing_outcome_records: int,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> dict[str, Any]:
    promising = [row for row in ranked if row["promising_screen"]]
    if not preflight["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "relaxed_strict_atom_schema_preflight_not_ready"
        next_work = "fix_relaxed_strict_atom_schema_preflight_before_separability"
    elif not sensitivity["passed"] or not selected_grid:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "relaxed_strict_label_sensitivity_source_not_ready"
        next_work = "fix_relaxed_strict_label_sensitivity_before_atom_screen"
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        next_work = None
    elif missing_outcome_records:
        status = MISSING_OUTCOMES_STATUS
        primary_gap = "candidate_closed_loop_outcomes_missing_for_relaxed_strict_screen"
        next_work = "rerun_matched_outcome_collection_before_relaxed_strict_screen"
    elif class_counts.get(CLASS_BENEFICIAL, 0) < int(min_beneficial_candidates):
        status = REJECT_STATUS
        primary_gap = "relaxed_strict_beneficial_support_insufficient"
        next_work = NEXT_WORK_SUPPORT
    elif class_counts.get(CLASS_HARMFUL, 0) < int(min_harmful_candidates):
        status = REJECT_STATUS
        primary_gap = "relaxed_strict_harmful_support_insufficient"
        next_work = NEXT_WORK_SUPPORT
    elif promising:
        status = READY_STATUS
        primary_gap = "no_gap_promising_relaxed_strict_atom_screen_found"
        next_work = NEXT_WORK_CERTIFICATE
    else:
        status = REJECT_STATUS
        primary_gap = "relaxed_strict_atoms_do_not_separate_candidates"
        next_work = NEXT_WORK_DIAGNOSIS
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
        "# Relaxed Strict-Label Atom Separability",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Gates",
        "",
        "```json",
        json.dumps(
            {
                "preflight_gate": report["preflight_gate"],
                "sensitivity_gate": report["sensitivity_gate"],
            },
            indent=2,
            sort_keys=True,
        ),
        "```",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
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
            f"| {index} | `{screen['screen_name']}` | "
            f"`{screen['promising_screen']}` | "
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
