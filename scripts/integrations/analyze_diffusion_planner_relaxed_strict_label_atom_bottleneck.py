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
from scripts.integrations.analyze_diffusion_planner_progress_lane_hard_context_separability_bottleneck import (  # noqa: E402
    _apply_screen,
    _counts,
    _descriptor_overlap,
    _group_rows,
    _rate,
)
from scripts.integrations.analyze_diffusion_planner_relaxed_strict_label_atom_separability import (  # noqa: E402
    BLOCKED_ACTIONS,
    NEXT_WORK_DIAGNOSIS as SOURCE_NEXT_WORK,
    REJECT_STATUS as SOURCE_REJECT_STATUS,
    _descriptor_specs,
    _feature_values,
    _load_json,
    _path_seeds,
)
from scripts.integrations.analyze_diffusion_planner_revised_context_strict_label_separability import (  # noqa: E402
    _strict_candidate_rows,
)
from scripts.integrations.analyze_diffusion_planner_revised_progress_lane_hard_context_atom_separability import (  # noqa: E402
    ALLOWED_HARMFUL_RATE_TARGET,
    BENEFICIAL_RETAIN_RATE_TARGET,
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_NEUTRAL,
    CLASS_TOP1,
)


READY_STATUS = "relaxed_strict_label_atom_bottleneck_diagnosed"
SOURCE_BLOCKED_STATUS = "relaxed_strict_label_atom_bottleneck_source_not_ready"

SOURCE_PRIMARY_GAP = "relaxed_strict_atoms_do_not_separate_candidates"
NEXT_WORK_NEW_ATOM = "reject_or_redesign_relaxed_strict_no_leak_atom_family"
NEXT_WORK_LABEL_BUDGET = "revisit_relaxed_strict_label_budget_before_atom_redesign"
NEXT_WORK_SUPPORT = "record_relaxed_strict_candidate_support_limit_before_replay"

RETAIN_RATE_TARGETS = (0.10, 0.25, 0.50, 0.75, 1.00)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only bottleneck diagnosis for the rejected relaxed strict-label "
            "atom separability screen. It reuses existing matched logs, applies "
            "the rejected best screen, and reports whether the failure is atom "
            "overblocking, harmful leakage under threshold relaxation, label "
            "budget mismatch, or intrinsic overlap."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--separability_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument(
        "--min_beneficial_block_rate_for_atom_gap",
        type=float,
        default=0.50,
    )
    parser.add_argument(
        "--allowed_harmful_rate_target",
        type=float,
        default=ALLOWED_HARMFUL_RATE_TARGET,
    )
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
        separability_report=_load_json(args.separability_json),
        label=args.label,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
        min_beneficial_block_rate_for_atom_gap=(
            args.min_beneficial_block_rate_for_atom_gap
        ),
        allowed_harmful_rate_target=args.allowed_harmful_rate_target,
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
    separability_report: dict[str, Any],
    label: str | None = None,
    fail_on_formal_seeds: bool = False,
    min_beneficial_block_rate_for_atom_gap: float = 0.50,
    allowed_harmful_rate_target: float = ALLOWED_HARMFUL_RATE_TARGET,
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
        separability_report=separability_report,
        label=label,
        fail_on_formal_seeds=fail_on_formal_seeds,
        min_beneficial_block_rate_for_atom_gap=(
            min_beneficial_block_rate_for_atom_gap
        ),
        allowed_harmful_rate_target=allowed_harmful_rate_target,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    separability_report: dict[str, Any],
    label: str | None = None,
    fail_on_formal_seeds: bool = False,
    min_beneficial_block_rate_for_atom_gap: float = 0.50,
    allowed_harmful_rate_target: float = ALLOWED_HARMFUL_RATE_TARGET,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")

    source = _source_gate(separability_report)
    best_screen = _best_screen(separability_report)
    params = _selected_label_params(separability_report)
    rows, payload_rows, formal_seed_records, missing_outcome_records = _rows_from_items(
        items,
        params=params,
    )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    alternative_rows = [row for row in rows if row["class"] != CLASS_TOP1]
    screened = _apply_screen(alternative_rows, best_screen)
    grouped = _group_rows(screened)
    counts = _counts(grouped)
    threshold_counterfactuals = _threshold_counterfactuals(
        screened,
        best_screen,
        retain_rate_targets=RETAIN_RATE_TARGETS,
    )
    diagnosis = _diagnosis(
        counts,
        threshold_counterfactuals,
        min_beneficial_block_rate_for_atom_gap=(
            min_beneficial_block_rate_for_atom_gap
        ),
        allowed_harmful_rate_target=allowed_harmful_rate_target,
    )
    source_ready = bool(
        source["passed"]
        and best_screen
        and rows
        and not missing_outcome_records
    )
    final = {
        "status": READY_STATUS if source_ready else SOURCE_BLOCKED_STATUS,
        "passed": source_ready,
        "primary_gap": (
            diagnosis["primary_gap"] if source_ready else _blocked_primary_gap(
                source,
                best_screen,
                rows,
                missing_outcome_records,
            )
        ),
        "authorized_next_work": (
            diagnosis["recommended_next_work"]
            if source_ready
            else "fix_relaxed_strict_atom_bottleneck_source_before_diagnosis"
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }
    return {
        "analysis": {
            "name": "dp_camp_relaxed_strict_label_atom_bottleneck_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_atoms": False,
            "future_outcome_labels_used_for_diagnosis": True,
            "thresholds_are_offline_oracle_diagnostics": True,
            "selected_label_params": params,
            "retain_rate_targets": list(RETAIN_RATE_TARGETS),
            "math_boundary": (
                "The diagnosis applies a rejected offline screen to fixed "
                "current-tick relaxed strict atom coefficients. Candidate "
                "closed-loop outcomes are used only to explain offline labels "
                "and screen error modes, never as runtime atom features. Each "
                "atom remains a nonnegative finite-candidate coefficient a_k; "
                "CAMP scoring remains affine score_k(w)=a_k^T w and the "
                "simplex/CVaR/L2 master remains convex in w. No DP-side "
                "classical Benders master/subproblem, dual, or cut is "
                "constructed."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_separability_gate": source,
        "source_records": _source_records(separability_report),
        "source_failure_gap": _source_failure_gap(separability_report),
        "best_screen": best_screen,
        "records": {
            "total_records": len(items),
            "candidate_rows": len(payload_rows),
            "classified_candidate_rows": len(rows),
            "alternative_rows": len(alternative_rows),
            "missing_outcome_records": missing_outcome_records,
            "formal_seed_records": formal_seed_records,
        },
        "counts": counts,
        "diagnosis": diagnosis,
        "threshold_counterfactuals": threshold_counterfactuals,
        "descriptor_overlap": _descriptor_overlap(alternative_rows),
        "blocked_beneficial": _summary_for_rows(
            grouped["blocked_beneficial"],
            best_screen,
        ),
        "retained_beneficial": _summary_for_rows(
            grouped["retained_beneficial"],
            best_screen,
        ),
        "allowed_harmful": _summary_for_rows(
            grouped["allowed_harmful"],
            best_screen,
        ),
        "blocked_harmful": _summary_for_rows(
            grouped["blocked_harmful"],
            best_screen,
        ),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _rows_from_items(
    items: list[dict[str, Any]],
    *,
    params: dict[str, float],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
    descriptor_specs = _descriptor_specs()
    rows: list[dict[str, Any]] = []
    payload_rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    missing_outcome_records = 0
    for index, item in enumerate(items):
        raw = item["raw"]
        context = item["context"]
        label = f"record {index}"
        feature_values, candidate_count, formal_seed = _feature_values(
            raw,
            context,
            label,
            descriptor_specs,
        )
        formal_seed_records += int(formal_seed)
        for candidate_index in range(candidate_count):
            payload_rows.append(
                {
                    "context": context,
                    "candidate_index": candidate_index,
                    "features": {
                        name: float(values[candidate_index])
                        for name, values in feature_values.items()
                        if np.isfinite(values[candidate_index])
                    },
                }
            )
        outcomes = raw.get("candidate_closed_loop_outcomes")
        if not isinstance(outcomes, list) or len(outcomes) != candidate_count:
            missing_outcome_records += 1
            continue
        rows.extend(
            _strict_candidate_rows(
                raw,
                context,
                label,
                descriptor_specs,
                feature_values=feature_values,
                progress_loss_budget_m=params["progress_loss_budget_m"],
                comfort_jerk_delta_budget=params["comfort_jerk_delta_budget"],
                comfort_lateral_delta_budget=params["comfort_lateral_delta_budget"],
                safety_improvement_margin=params["safety_improvement_margin"],
                harmful_safety_margin=params["harmful_safety_margin"],
            )
        )
    return rows, payload_rows, formal_seed_records, missing_outcome_records


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    status = decision.get("status")
    primary_gap = decision.get("primary_gap")
    next_work = decision.get("authorized_next_work")
    blocked_actions = report.get("blocked_actions")
    blocked_clear = True
    if isinstance(blocked_actions, dict):
        blocked_clear = not any(bool(blocked_actions.get(key)) for key in BLOCKED_ACTIONS)
    passed = (
        decision.get("passed") is False
        and status == SOURCE_REJECT_STATUS
        and primary_gap == SOURCE_PRIMARY_GAP
        and next_work == SOURCE_NEXT_WORK
        and int(decision.get("promising_screen_count", -1)) == 0
        and blocked_clear
    )
    return {
        "passed": passed,
        "status": status,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        "promising_screen_count": decision.get("promising_screen_count"),
        "blocked_actions_clear": blocked_clear,
    }


def _selected_label_params(report: dict[str, Any]) -> dict[str, float]:
    analysis = report.get("analysis") if isinstance(report, dict) else None
    params = analysis.get("selected_grid_params") if isinstance(analysis, dict) else None
    if not isinstance(params, dict):
        raise ValueError("separability report missing analysis.selected_grid_params")
    required = (
        "progress_loss_budget_m",
        "comfort_jerk_delta_budget",
        "comfort_lateral_delta_budget",
        "safety_improvement_margin",
        "harmful_safety_margin",
    )
    missing = [key for key in required if key not in params]
    if missing:
        raise ValueError(f"separability report label params missing {missing}")
    return {key: float(params[key]) for key in required}


def _best_screen(report: dict[str, Any]) -> dict[str, Any] | None:
    failure_gap = report.get("failure_gap") if isinstance(report, dict) else None
    if isinstance(failure_gap, dict) and isinstance(failure_gap.get("best_screen"), dict):
        return failure_gap["best_screen"]
    ranked = report.get("ranked_screens") if isinstance(report, dict) else None
    if isinstance(ranked, list) and ranked and isinstance(ranked[0], dict):
        return ranked[0]
    return None


def _source_records(report: dict[str, Any]) -> dict[str, Any]:
    records = report.get("records") if isinstance(report, dict) else None
    if not isinstance(records, dict):
        return {}
    return {
        "total_records": records.get("total_records"),
        "candidate_rows": records.get("candidate_rows"),
        "alternative_rows": records.get("alternative_rows"),
        "formal_seed_records": records.get("formal_seed_records"),
        "class_counts": records.get("class_counts"),
    }


def _source_failure_gap(report: dict[str, Any]) -> dict[str, Any]:
    failure_gap = report.get("failure_gap") if isinstance(report, dict) else None
    if not isinstance(failure_gap, dict):
        return {}
    best = failure_gap.get("best_screen")
    return {
        "primary_gap": failure_gap.get("primary_gap"),
        "best_screen_name": None if not isinstance(best, dict) else best.get("screen_name"),
        "best_screen_beneficial_retain_rate": (
            None if not isinstance(best, dict) else best.get("beneficial_retain_rate")
        ),
        "best_screen_harmful_block_rate": (
            None if not isinstance(best, dict) else best.get("harmful_block_rate")
        ),
        "best_screen_allowed_harmful_rate": (
            None if not isinstance(best, dict) else best.get("allowed_harmful_rate")
        ),
    }


def _threshold_counterfactuals(
    rows: list[dict[str, Any]],
    screen: dict[str, Any] | None,
    *,
    retain_rate_targets: tuple[float, ...],
) -> list[dict[str, Any]]:
    if not screen:
        return []
    beneficial_scores = sorted(
        float(row["screen_score"])
        for row in rows
        if row["class"] == CLASS_BENEFICIAL and row["screen_score"] is not None
    )
    if not beneficial_scores:
        return []
    counterfactuals = []
    for target in retain_rate_targets:
        count = max(1, int(np.ceil(float(target) * len(beneficial_scores))))
        threshold = beneficial_scores[min(count, len(beneficial_scores)) - 1]
        applied = _apply_threshold(rows, threshold)
        grouped = _group_rows(applied)
        counts = _counts(grouped)
        allowed_nonneutral = counts["harmful_allowed"] + counts["beneficial_retained"]
        counterfactuals.append(
            {
                "target_beneficial_retain_rate": float(target),
                "threshold": float(threshold),
                "counts": counts,
                "harmful_block_rate": _rate(
                    counts["harmful_blocked"],
                    counts["harmful_total"],
                ),
                "beneficial_retain_rate": _rate(
                    counts["beneficial_retained"],
                    counts["beneficial_total"],
                ),
                "allowed_harmful_rate": _rate(
                    counts["harmful_allowed"],
                    allowed_nonneutral,
                ),
                "allowed_harmful_count": counts["harmful_allowed"],
            }
        )
    return counterfactuals


def _apply_threshold(rows: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        score = row.get("screen_score")
        result.append(
            {
                **row,
                "screen_allowed": bool(
                    score is not None and float(score) <= float(threshold) + 1e-12
                ),
            }
        )
    return result


def _diagnosis(
    counts: dict[str, int],
    threshold_counterfactuals: list[dict[str, Any]],
    *,
    min_beneficial_block_rate_for_atom_gap: float,
    allowed_harmful_rate_target: float,
) -> dict[str, Any]:
    beneficial_block_rate = _rate(
        counts["beneficial_blocked"],
        counts["beneficial_total"],
    )
    current_allowed_harmful_rate = _rate(
        counts["harmful_allowed"],
        counts["harmful_allowed"] + counts["beneficial_retained"],
    )
    atom_overblocks = beneficial_block_rate >= float(
        min_beneficial_block_rate_for_atom_gap
    )
    current_allows_harmful = current_allowed_harmful_rate > float(
        allowed_harmful_rate_target
    )
    high_retain = [
        row
        for row in threshold_counterfactuals
        if float(row["target_beneficial_retain_rate"]) >= BENEFICIAL_RETAIN_RATE_TARGET
    ]
    high_retain_leaks_harmful = any(
        float(row["allowed_harmful_rate"]) > float(allowed_harmful_rate_target)
        for row in high_retain
    )
    high_retain_zero_harmful = [
        row
        for row in high_retain
        if int(row["allowed_harmful_count"]) == 0
        and float(row["beneficial_retain_rate"]) >= BENEFICIAL_RETAIN_RATE_TARGET
    ]
    if atom_overblocks and high_retain_leaks_harmful:
        primary = "relaxed_strict_atom_threshold_tradeoff_overblocks_or_leaks_harmful"
        next_work = NEXT_WORK_NEW_ATOM
    elif atom_overblocks and not high_retain_zero_harmful:
        primary = "relaxed_strict_atom_screen_overblocks_beneficial"
        next_work = NEXT_WORK_NEW_ATOM
    elif current_allows_harmful:
        primary = "relaxed_strict_atom_screen_allows_harmful"
        next_work = NEXT_WORK_NEW_ATOM
    elif high_retain_zero_harmful:
        primary = "relaxed_strict_atom_threshold_budget_too_strict"
        next_work = NEXT_WORK_LABEL_BUDGET
    else:
        primary = "relaxed_strict_atom_bottleneck_support_limited"
        next_work = NEXT_WORK_SUPPORT
    return {
        "primary_gap": primary,
        "beneficial_block_rate": beneficial_block_rate,
        "current_allowed_harmful_rate_among_allowed_nonneutral": (
            current_allowed_harmful_rate
        ),
        "atom_overblocks_beneficial": atom_overblocks,
        "current_screen_allows_harmful": current_allows_harmful,
        "high_retain_threshold_leaks_harmful": high_retain_leaks_harmful,
        "high_retain_zero_harmful_threshold_exists": bool(high_retain_zero_harmful),
        "current_relaxed_strict_atom_family_recommended": False,
        "camp_retraining_recommended": False,
        "online_selector_recommended": False,
        "recommended_next_work": next_work,
    }


def _summary_for_rows(
    rows: list[dict[str, Any]],
    screen: dict[str, Any] | None,
) -> dict[str, Any]:
    names = [] if screen is None else [str(name) for name in screen.get("descriptor_names", [])]
    return {
        "count": len(rows),
        "outcome_summary": {
            "value_delta_mean": _mean([row["outcome_value_delta_vs_top1"] for row in rows]),
            "progress_delta_mean_m": _mean([row["progress_delta_vs_top1_m"] for row in rows]),
            "safety_penalty_delta_mean": _mean(
                [row["safety_penalty_delta_vs_top1"] for row in rows]
            ),
            "safety_penalty_delta_max": _max(
                [row["safety_penalty_delta_vs_top1"] for row in rows]
            ),
            "jerk_delta_mean_mps3": _mean(
                [row["mean_jerk_delta_vs_top1_mps3"] for row in rows]
            ),
            "lateral_delta_mean_mps2": _mean(
                [row["mean_lateral_acceleration_delta_vs_top1_mps2"] for row in rows]
            ),
            "progress_compatible_count": sum(int(row["progress_compatible"]) for row in rows),
            "jerk_compatible_count": sum(int(row["jerk_compatible"]) for row in rows),
            "lateral_compatible_count": sum(int(row["lateral_compatible"]) for row in rows),
            "hard_safety_worse_count": sum(int(row["hard_safety_worse_than_top1"]) for row in rows),
            "red_light_worse_count": sum(int(row["red_light_worse_than_top1"]) for row in rows),
            "lane_worse_count": sum(int(row["lane_worse_than_top1"]) for row in rows),
            "collision_worse_count": sum(int(row["collision_worse_than_top1"]) for row in rows),
            "near_miss_worse_count": sum(int(row["near_miss_worse_than_top1"]) for row in rows),
        },
        "screen_score_summary": _score_summary(rows),
        "descriptor_contribution_mean": {
            name: _mean([row["screen_contributions"].get(name, 0.0) for row in rows])
            for name in names
        },
        "dominant_contribution_counts": _dominant_contribution_counts(rows),
        "reason_counts": _reason_counts(rows),
        "top_examples": _examples(rows, names),
    }


def _reason_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for reason in _reasons(row):
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _reasons(row: dict[str, Any]) -> list[str]:
    reasons = []
    if not row["progress_compatible"]:
        reasons.append("progress_incompatible")
    if not row["jerk_compatible"]:
        reasons.append("jerk_incompatible")
    if not row["lateral_compatible"]:
        reasons.append("lateral_incompatible")
    if row["hard_safety_worse_than_top1"]:
        reasons.append("hard_safety_worse")
    if row["safety_penalty_delta_vs_top1"] > 0.0:
        reasons.append("safety_penalty_worse")
    if row["class"] == CLASS_BENEFICIAL and not reasons:
        reasons.append("low_risk_beneficial_blocked_by_atom_score")
    if not reasons:
        reasons.append("shape_overlap")
    return reasons


def _dominant_contribution_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        contributions = row.get("screen_contributions") or {}
        if not contributions:
            key = "none"
        else:
            key = max(contributions, key=lambda name: abs(float(contributions[name])))
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _score_summary(rows: list[dict[str, Any]]) -> dict[str, float | None]:
    scores = [row.get("screen_score") for row in rows if row.get("screen_score") is not None]
    if not scores:
        return {"min": None, "median": None, "max": None}
    array = np.asarray(scores, dtype=np.float64)
    return {
        "min": float(np.min(array)),
        "median": float(np.median(array)),
        "max": float(np.max(array)),
    }


def _examples(rows: list[dict[str, Any]], names: list[str]) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            -float(row.get("screen_score") or 0.0),
            str(row["context"].get("log_path", "")),
            int(row["context"].get("record_index", 0)),
            int(row["candidate_index"]),
        ),
    )
    examples = []
    for row in ranked[:8]:
        examples.append(
            {
                "log_path": row["context"].get("log_path"),
                "record_index": row["context"].get("record_index"),
                "candidate_index": row["candidate_index"],
                "class": row["class"],
                "screen_score": row.get("screen_score"),
                "screen_allowed": row.get("screen_allowed"),
                "outcome_value_delta_vs_top1": row["outcome_value_delta_vs_top1"],
                "progress_delta_vs_top1_m": row["progress_delta_vs_top1_m"],
                "safety_penalty_delta_vs_top1": row["safety_penalty_delta_vs_top1"],
                "jerk_delta_vs_top1_mps3": row["mean_jerk_delta_vs_top1_mps3"],
                "lateral_delta_vs_top1_mps2": row[
                    "mean_lateral_acceleration_delta_vs_top1_mps2"
                ],
                "progress_compatible": row["progress_compatible"],
                "jerk_compatible": row["jerk_compatible"],
                "lateral_compatible": row["lateral_compatible"],
                "hard_safety_worse_than_top1": row["hard_safety_worse_than_top1"],
                "red_light_worse_than_top1": row["red_light_worse_than_top1"],
                "lane_worse_than_top1": row["lane_worse_than_top1"],
                "reasons": _reasons(row),
                "descriptor_values": {name: row["features"].get(name) for name in names},
                "screen_contributions": {
                    name: row["screen_contributions"].get(name) for name in names
                },
            }
        )
    return examples


def _mean(values: list[Any]) -> float | None:
    array = np.asarray([value for value in values if value is not None], dtype=np.float64)
    array = array[np.isfinite(array)]
    if array.size == 0:
        return None
    return float(np.mean(array))


def _max(values: list[Any]) -> float | None:
    array = np.asarray([value for value in values if value is not None], dtype=np.float64)
    array = array[np.isfinite(array)]
    if array.size == 0:
        return None
    return float(np.max(array))


def _blocked_primary_gap(
    source: dict[str, Any],
    best_screen: dict[str, Any] | None,
    rows: list[dict[str, Any]],
    missing_outcome_records: int,
) -> str:
    if not source.get("passed"):
        return "source_relaxed_strict_separability_gate_not_rejected_as_expected"
    if not best_screen:
        return "source_relaxed_strict_separability_best_screen_missing"
    if missing_outcome_records:
        return "matched_outcomes_missing_for_relaxed_strict_atom_bottleneck"
    if not rows:
        return "no_classified_rows_for_relaxed_strict_atom_bottleneck"
    return "source_not_ready"


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Relaxed Strict-Label Atom Bottleneck",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Gate",
        "",
        "```json",
        json.dumps(report["source_separability_gate"], indent=2, sort_keys=True),
        "```",
        "",
        "## Best Screen",
        "",
        "```json",
        json.dumps(report["best_screen"], indent=2, sort_keys=True),
        "```",
        "",
        "## Counts",
        "",
        "```json",
        json.dumps(report["counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Diagnosis",
        "",
        "```json",
        json.dumps(report["diagnosis"], indent=2, sort_keys=True),
        "```",
        "",
        "## Threshold Counterfactuals",
        "",
        "```json",
        json.dumps(report["threshold_counterfactuals"], indent=2, sort_keys=True),
        "```",
        "",
        "## Descriptor Overlap",
        "",
        "```json",
        json.dumps(report["descriptor_overlap"], indent=2, sort_keys=True),
        "```",
        "",
        "## Blocked Beneficial",
        "",
        "```json",
        json.dumps(report["blocked_beneficial"], indent=2, sort_keys=True),
        "```",
        "",
        "## Allowed Harmful",
        "",
        "```json",
        json.dumps(report["allowed_harmful"], indent=2, sort_keys=True),
        "```",
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
