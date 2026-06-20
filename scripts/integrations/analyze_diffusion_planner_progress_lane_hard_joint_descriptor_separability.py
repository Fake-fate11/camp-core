#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)
from scripts.integrations.analyze_diffusion_planner_lane_hard_violation_support_descriptor_separability import (  # noqa: E402
    _candidate_rows as _lane_hard_candidate_rows,
    _descriptor_specs as _lane_hard_descriptor_specs,
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
    _affine_screens,
    _candidate_rows as _progress_candidate_rows,
    _class_counts,
    _descriptor_coverage,
    _descriptor_specs as _progress_descriptor_specs,
    _load_json,
    _normalization,
    _path_seeds,
    _screen_sort_key,
    _single_descriptor_screens,
)


READY_STATUS = (
    "progress_lane_hard_joint_descriptor_separability_promising_for_certificate_design"
)
REJECT_STATUS = "progress_lane_hard_joint_descriptor_separability_rejected"
SOURCE_BLOCKED_STATUS = "progress_lane_hard_joint_descriptor_separability_source_not_ready"
FORMAL_SEED_STATUS = "progress_lane_hard_joint_descriptor_separability_formal_seed_conflict"

PROGRESS_CONTRACT_STATUS = "matched_progress_support_outcome_contract_passed"
LANE_HARD_CONTRACT_STATUS = "matched_lane_hard_violation_support_outcome_contract_passed"

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "online_optimization_promotion_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline no-leak separability screen over same-record co-logged "
            "progress-support and lane/hard support descriptors. This is an "
            "oracle diagnostic over existing nonformal logs, not CAMP training "
            "and not an online selector."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--progress_contract_json", type=Path, required=True)
    parser.add_argument("--lane_hard_contract_json", type=Path, required=True)
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
        progress_contract_report=_load_json(args.progress_contract_json),
        lane_hard_contract_report=_load_json(args.lane_hard_contract_json),
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
    progress_contract_report: dict[str, Any],
    lane_hard_contract_report: dict[str, Any],
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
        progress_contract_report=progress_contract_report,
        lane_hard_contract_report=lane_hard_contract_report,
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
    progress_contract_report: dict[str, Any],
    lane_hard_contract_report: dict[str, Any],
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
    source = _source_gate(progress_contract_report, lane_hard_contract_report)
    progress_specs = _progress_descriptor_specs()
    lane_specs = _lane_hard_descriptor_specs()
    descriptor_specs = (*progress_specs, *lane_specs)
    _validate_unique_descriptor_names(descriptor_specs)

    rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    for index, item in enumerate(items):
        progress_rows, progress_formal_seed = _progress_candidate_rows(
            item["raw"],
            item["context"],
            f"record {index}",
            progress_specs,
            min_value_gain=min_value_gain,
            min_value_loss=min_value_loss,
            progress_loss_budget_m=progress_loss_budget_m,
        )
        lane_rows, lane_formal_seed = _lane_hard_candidate_rows(
            item["raw"],
            item["context"],
            f"record {index}",
            lane_specs,
            min_value_gain=min_value_gain,
            min_value_loss=min_value_loss,
            progress_loss_budget_m=progress_loss_budget_m,
        )
        rows.extend(_merge_record_rows(progress_rows, lane_rows, f"record {index}"))
        formal_seed_records += int(progress_formal_seed or lane_formal_seed)
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
            "name": "dp_camp_progress_lane_hard_joint_descriptor_separability_v1",
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
            "descriptor_families": {
                "progress_support": len(progress_specs),
                "lane_hard_support": len(lane_specs),
                "joint_total": len(descriptor_specs),
            },
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
                "Progress-support and lane/hard support descriptors are fixed "
                "current-tick finite-candidate quantities computed before "
                "candidate closed-loop outcomes. Outcome labels define only "
                "offline beneficial/harmful classes and threshold diagnostics. "
                "Concatenating nonnegative atom vectors preserves affine "
                "score_k(w)=a_k^T w after atomization and remains compatible "
                "with the simplex/CVaR/L2 convex master. No DP-side classical "
                "Benders master/subproblem, dual, or cut is constructed."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_contract_gates": source,
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


def _source_gate(
    progress_contract_report: dict[str, Any],
    lane_hard_contract_report: dict[str, Any],
) -> dict[str, Any]:
    progress = _contract_gate(progress_contract_report, PROGRESS_CONTRACT_STATUS)
    lane_hard = _contract_gate(lane_hard_contract_report, LANE_HARD_CONTRACT_STATUS)
    return {
        "passed": progress["passed"] and lane_hard["passed"],
        "progress_support": progress,
        "lane_hard_support": lane_hard,
    }


def _contract_gate(report: dict[str, Any], expected_status: str) -> dict[str, Any]:
    final = report.get("final_decision") if isinstance(report, dict) else None
    counts = report.get("counts") if isinstance(report, dict) else None
    if not isinstance(final, dict):
        return {"passed": False, "status": "missing_final_decision"}
    if not isinstance(counts, dict):
        counts = {}
    passed = (
        final.get("passed") is True
        and final.get("status") == expected_status
        and int(counts.get("formal_seed_records") or 0) == 0
        and int(counts.get("records") or 0) > 0
        and int(counts.get("outcome_records") or 0) == int(counts.get("records") or -1)
    )
    return {
        "passed": passed,
        "status": final.get("status"),
        "authorized_next_work": final.get("authorized_next_work"),
        "records": counts.get("records"),
        "outcome_records": counts.get("outcome_records"),
        "candidate_rows": counts.get("candidate_rows"),
        "formal_seed_records": counts.get("formal_seed_records"),
    }


def _validate_unique_descriptor_names(descriptor_specs: tuple[Any, ...]) -> None:
    names = [spec.name for spec in descriptor_specs]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"Duplicate joint descriptor names: {duplicates}.")


def _merge_record_rows(
    progress_rows: list[dict[str, Any]],
    lane_rows: list[dict[str, Any]],
    label: str,
) -> list[dict[str, Any]]:
    if len(progress_rows) != len(lane_rows):
        raise ValueError(f"{label} progress/lane row count mismatch.")
    merged: list[dict[str, Any]] = []
    for progress, lane in zip(progress_rows, lane_rows, strict=True):
        _validate_row_alignment(progress, lane, label)
        overlap = set(progress["features"]) & set(lane["features"])
        if overlap:
            raise ValueError(f"{label} duplicate feature names {sorted(overlap)}.")
        merged.append(
            {
                **progress,
                "features": {
                    **progress["features"],
                    **lane["features"],
                },
            }
        )
    return merged


def _validate_row_alignment(
    progress: dict[str, Any],
    lane: dict[str, Any],
    label: str,
) -> None:
    keys = (
        "candidate_index",
        "class",
        "outcome_value_delta_vs_top1",
        "progress_delta_vs_top1_m",
        "hard_violation_delta_vs_top1",
        "red_light_worse_than_top1",
        "lane_worse_than_top1",
        "collision_worse_than_top1",
        "near_miss_worse_than_top1",
    )
    for key in keys:
        if progress.get(key) != lane.get(key):
            raise ValueError(f"{label} progress/lane row mismatch for {key}.")


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
        primary_gap = "joint_matched_contract_gate_not_passed"
        next_work = "fix_joint_cologged_contract_before_separability"
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        next_work = None
    elif class_counts.get(CLASS_BENEFICIAL, 0) < int(min_beneficial_candidates):
        status = REJECT_STATUS
        primary_gap = "beneficial_candidate_support_insufficient"
        next_work = "expand_joint_cologged_label_coverage_before_selector_design"
    elif class_counts.get(CLASS_HARMFUL, 0) < int(min_harmful_candidates):
        status = REJECT_STATUS
        primary_gap = "harmful_candidate_support_insufficient"
        next_work = "expand_joint_cologged_label_coverage_before_selector_design"
    elif promising:
        status = READY_STATUS
        primary_gap = "no_gap_promising_progress_lane_hard_joint_screen_found"
        next_work = "offline_progress_lane_hard_joint_certificate_design_only"
    else:
        status = REJECT_STATUS
        primary_gap = "progress_lane_hard_joint_descriptors_do_not_separate_candidates"
        next_work = "diagnose_progress_lane_hard_joint_descriptor_bottleneck_before_retraining"
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
        primary = "no_finite_progress_lane_hard_joint_descriptor_screen"
    elif best["harmful_block_rate"] < HARMFUL_BLOCK_RATE_TARGET:
        primary = "harmful_block_rate_insufficient"
    elif best["beneficial_retain_rate"] < BENEFICIAL_RETAIN_RATE_TARGET:
        primary = "beneficial_retain_rate_insufficient"
    elif best["allowed_harmful_rate"] > ALLOWED_HARMFUL_RATE_TARGET:
        primary = "allowed_harmful_rate_too_high"
    else:
        primary = "no_gap_promising_progress_lane_hard_joint_screen_found"
    return {"primary_gap": primary, "best_screen": best}


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP CAMP Progress + Lane/Hard Joint Descriptor Separability",
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
