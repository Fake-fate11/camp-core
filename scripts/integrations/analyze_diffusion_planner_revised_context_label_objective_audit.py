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
    _group_rows,
    _mean,
    _rate,
)
from scripts.integrations.analyze_diffusion_planner_revised_context_atom_separability_bottleneck import (  # noqa: E402
    READY_STATUS as BOTTLENECK_READY_STATUS,
)
from scripts.integrations.analyze_diffusion_planner_revised_progress_lane_hard_context_atom_separability import (  # noqa: E402
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_NEUTRAL,
    CLASS_TOP1,
    MIN_VALUE_GAIN,
    MIN_VALUE_LOSS,
    PAYLOAD_KEY,
    PROGRESS_LOSS_BUDGET_M,
    _candidate_rows,
    _class_counts,
    _descriptor_specs,
    _descriptor_values,
    _is_formal_seed,
    _load_json,
    _path_seeds,
    _record_candidate_count,
    _validate_payload,
)


READY_STATUS = "revised_context_label_objective_audit_diagnosed"
SOURCE_BLOCKED_STATUS = "revised_context_label_objective_audit_source_not_ready"

SOURCE_PRIMARY_GAP = (
    "strict_atom_screens_overblock_beneficial_and_high_retain_screens_allow_harmful"
)
SOURCE_NEXT_WORK = "revise_atom_label_or_objective_before_retraining"
NEXT_WORK = "predeclare_revised_label_or_atom_change_before_new_replay"

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "online_optimization_promotion_authorized",
)

HARD_FIELDS = (
    "collision",
    "near_miss",
    "red_light_violation",
    "lane_violation",
)

SAFETY_PENALTY_WEIGHTS = {
    "collision": 100.0,
    "near_miss": 50.0,
    "red_light_violation": 25.0,
    "lane_violation": 10.0,
    "infeasible": 5.0,
    "mean_lateral_acceleration_mps2": 0.5,
    "mean_jerk_mps3": 0.1,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only audit splitting the rejected revised atom bottleneck "
            "into label permissiveness, atom over-penalty, and DP candidate-set "
            "support hypotheses. Closed-loop outcomes are offline labels only."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--bottleneck_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--strict_progress_loss_budget_m",
        type=float,
        default=PROGRESS_LOSS_BUDGET_M,
    )
    parser.add_argument("--strict_jerk_delta_budget", type=float, default=0.0)
    parser.add_argument("--strict_lateral_delta_budget", type=float, default=0.0)
    parser.add_argument(
        "--strict_safety_penalty_improvement",
        type=float,
        default=0.05,
    )
    parser.add_argument(
        "--min_strict_good_record_rate",
        type=float,
        default=0.25,
    )
    parser.add_argument(
        "--min_strict_good_beneficial_rate",
        type=float,
        default=0.25,
    )
    parser.add_argument(
        "--atom_overpenalty_block_rate",
        type=float,
        default=0.50,
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
        bottleneck_report=_load_json(args.bottleneck_json),
        label=args.label,
        strict_progress_loss_budget_m=args.strict_progress_loss_budget_m,
        strict_jerk_delta_budget=args.strict_jerk_delta_budget,
        strict_lateral_delta_budget=args.strict_lateral_delta_budget,
        strict_safety_penalty_improvement=args.strict_safety_penalty_improvement,
        min_strict_good_record_rate=args.min_strict_good_record_rate,
        min_strict_good_beneficial_rate=args.min_strict_good_beneficial_rate,
        atom_overpenalty_block_rate=args.atom_overpenalty_block_rate,
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
    bottleneck_report: dict[str, Any],
    label: str | None = None,
    strict_progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    strict_jerk_delta_budget: float = 0.0,
    strict_lateral_delta_budget: float = 0.0,
    strict_safety_penalty_improvement: float = 0.05,
    min_strict_good_record_rate: float = 0.25,
    min_strict_good_beneficial_rate: float = 0.25,
    atom_overpenalty_block_rate: float = 0.50,
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
        bottleneck_report=bottleneck_report,
        label=label,
        strict_progress_loss_budget_m=strict_progress_loss_budget_m,
        strict_jerk_delta_budget=strict_jerk_delta_budget,
        strict_lateral_delta_budget=strict_lateral_delta_budget,
        strict_safety_penalty_improvement=strict_safety_penalty_improvement,
        min_strict_good_record_rate=min_strict_good_record_rate,
        min_strict_good_beneficial_rate=min_strict_good_beneficial_rate,
        atom_overpenalty_block_rate=atom_overpenalty_block_rate,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    bottleneck_report: dict[str, Any],
    label: str | None = None,
    strict_progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    strict_jerk_delta_budget: float = 0.0,
    strict_lateral_delta_budget: float = 0.0,
    strict_safety_penalty_improvement: float = 0.05,
    min_strict_good_record_rate: float = 0.25,
    min_strict_good_beneficial_rate: float = 0.25,
    atom_overpenalty_block_rate: float = 0.50,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")

    source = _source_gate(bottleneck_report)
    best = _best_screen(bottleneck_report)
    rows, formal_seed_records, missing_outcome_records, payload_candidate_rows = (
        _rows_from_items(
            items,
            strict_progress_loss_budget_m=strict_progress_loss_budget_m,
            strict_jerk_delta_budget=strict_jerk_delta_budget,
            strict_lateral_delta_budget=strict_lateral_delta_budget,
            strict_safety_penalty_improvement=strict_safety_penalty_improvement,
        )
    )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")

    alternative_rows = [row for row in rows if row["class"] != CLASS_TOP1]
    screened = _apply_screen(alternative_rows, best)
    grouped = _group_rows(screened)
    label_audit = _label_audit(screened)
    atom_audit = _atom_audit(grouped)
    candidate_set_audit = _candidate_set_audit(screened, len(items))
    hypothesis = _hypothesis(
        label_audit,
        atom_audit,
        candidate_set_audit,
        min_strict_good_record_rate=min_strict_good_record_rate,
        min_strict_good_beneficial_rate=min_strict_good_beneficial_rate,
        atom_overpenalty_block_rate=atom_overpenalty_block_rate,
    )
    source_ready = bool(source["passed"] and best and rows and not missing_outcome_records)
    final = {
        "status": READY_STATUS if source_ready else SOURCE_BLOCKED_STATUS,
        "passed": source_ready,
        "primary_gap": (
            hypothesis["primary_gap"]
            if source_ready
            else _blocked_primary_gap(source, best, rows, missing_outcome_records)
        ),
        "authorized_next_work": (
            NEXT_WORK
            if source_ready
            else "fix_revised_context_label_objective_source_before_audit"
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }
    return {
        "analysis": {
            "name": "dp_camp_revised_context_label_objective_audit_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_atoms": False,
            "future_outcome_labels_used_for_offline_diagnosis": True,
            "diagnostic_thresholds": {
                "strict_progress_loss_budget_m": strict_progress_loss_budget_m,
                "strict_jerk_delta_budget": strict_jerk_delta_budget,
                "strict_lateral_delta_budget": strict_lateral_delta_budget,
                "strict_safety_penalty_improvement": strict_safety_penalty_improvement,
                "min_strict_good_record_rate": min_strict_good_record_rate,
                "min_strict_good_beneficial_rate": min_strict_good_beneficial_rate,
                "atom_overpenalty_block_rate": atom_overpenalty_block_rate,
            },
            "offline_safety_penalty": {
                "direction": "lower_is_better",
                "weights": SAFETY_PENALTY_WEIGHTS,
                "status": "diagnostic_only_not_a_runtime_selector_score",
            },
            "math_boundary": (
                "This audit keeps DP as a fixed black-box candidate generator "
                "and reads closed-loop outcomes only as offline labels. Atom "
                "values remain current-tick finite coefficients and are not "
                "recomputed from outcome labels. Any future accepted atom or "
                "label change must preserve affine score_k(w)=a_k^T w for the "
                "simplex/CVaR/L2 convex CAMP master. This audit does not build "
                "a DP-side classical Benders master/subproblem, dual, or cut."
            ),
        },
        "source_bottleneck_gate": source,
        "source_records": _source_records(bottleneck_report),
        "best_screen": best,
        "records": {
            "total_records": len(items),
            "payload_candidate_rows": payload_candidate_rows,
            "classified_candidate_rows": len(rows),
            "alternative_rows": len(alternative_rows),
            "missing_outcome_records": missing_outcome_records,
            "formal_seed_records": formal_seed_records,
            "class_counts": _class_counts(alternative_rows),
        },
        "screen_counts": _counts(grouped),
        "label_audit": label_audit,
        "atom_audit": atom_audit,
        "candidate_set_audit": candidate_set_audit,
        "hypothesis_diagnosis": hypothesis,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _rows_from_items(
    items: list[dict[str, Any]],
    *,
    strict_progress_loss_budget_m: float,
    strict_jerk_delta_budget: float,
    strict_lateral_delta_budget: float,
    strict_safety_penalty_improvement: float,
) -> tuple[list[dict[str, Any]], int, int, int]:
    specs = _descriptor_specs()
    rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    missing_outcome_records = 0
    payload_candidate_rows = 0
    for index, item in enumerate(items):
        raw = item["raw"]
        context = item["context"]
        label = f"record {index}"
        payload = raw.get(PAYLOAD_KEY)
        outcomes = raw.get("candidate_closed_loop_outcomes")
        candidate_count = _record_candidate_count(raw, payload, outcomes, label)
        payload_candidate_rows += int(candidate_count)
        _validate_payload(payload, candidate_count, label)
        formal_seed_records += int(_is_formal_seed(raw, context))
        if not isinstance(outcomes, list) or len(outcomes) != candidate_count:
            missing_outcome_records += 1
            continue
        feature_values = _descriptor_values(payload, specs, candidate_count, label)
        base_rows = _candidate_rows(
            raw,
            context,
            label,
            specs,
            feature_values=feature_values,
            min_value_gain=MIN_VALUE_GAIN,
            min_value_loss=MIN_VALUE_LOSS,
            progress_loss_budget_m=PROGRESS_LOSS_BUDGET_M,
        )
        parsed_outcomes = [_parse_outcome(outcome, f"{label} outcome {i}") for i, outcome in enumerate(outcomes)]
        top1 = parsed_outcomes[0]
        for row, outcome in zip(base_rows, parsed_outcomes):
            rows.append(
                {
                    **row,
                    **_outcome_deltas(
                        row,
                        outcome,
                        top1,
                        strict_progress_loss_budget_m=strict_progress_loss_budget_m,
                        strict_jerk_delta_budget=strict_jerk_delta_budget,
                        strict_lateral_delta_budget=strict_lateral_delta_budget,
                        strict_safety_penalty_improvement=strict_safety_penalty_improvement,
                    ),
                }
            )
    return rows, formal_seed_records, missing_outcome_records, payload_candidate_rows


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
    outcome["hard_violation_count"] = sum(int(outcome[field]) for field in HARD_FIELDS)
    outcome["safety_penalty"] = _safety_penalty(outcome)
    return outcome


def _outcome_deltas(
    row: dict[str, Any],
    outcome: dict[str, Any],
    top1: dict[str, Any],
    *,
    strict_progress_loss_budget_m: float,
    strict_jerk_delta_budget: float,
    strict_lateral_delta_budget: float,
    strict_safety_penalty_improvement: float,
) -> dict[str, Any]:
    jerk_delta = _optional_delta(outcome["mean_jerk_mps3"], top1["mean_jerk_mps3"])
    lateral_delta = _optional_delta(
        outcome["mean_lateral_acceleration_mps2"],
        top1["mean_lateral_acceleration_mps2"],
    )
    hard_improved = any(top1[field] and not outcome[field] for field in HARD_FIELDS)
    hard_worse = any(outcome[field] and not top1[field] for field in HARD_FIELDS)
    feasible_improved = outcome["feasible"] and not top1["feasible"]
    feasible_worse = top1["feasible"] and not outcome["feasible"]
    progress_compatible = row["progress_delta_vs_top1_m"] >= -float(
        strict_progress_loss_budget_m
    )
    jerk_compatible = jerk_delta is None or jerk_delta <= float(strict_jerk_delta_budget)
    lateral_compatible = (
        lateral_delta is None or lateral_delta <= float(strict_lateral_delta_budget)
    )
    hard_nonworse = not hard_worse and not feasible_worse
    hard_safety_improved = hard_improved or feasible_improved
    safety_penalty_delta = outcome["safety_penalty"] - top1["safety_penalty"]
    penalty_improved = safety_penalty_delta <= -float(strict_safety_penalty_improvement)
    strict_good = (
        row["candidate_index"] != 0
        and row["class"] == CLASS_BENEFICIAL
        and progress_compatible
        and jerk_compatible
        and lateral_compatible
        and hard_nonworse
        and (hard_safety_improved or penalty_improved)
    )
    return {
        "mean_jerk_delta_vs_top1_mps3": jerk_delta,
        "mean_lateral_acceleration_delta_vs_top1_mps2": lateral_delta,
        "safety_penalty_delta_vs_top1": safety_penalty_delta,
        "hard_safety_improved_vs_top1": hard_safety_improved,
        "hard_safety_worse_vs_top1": hard_worse or feasible_worse,
        "progress_compatible": progress_compatible,
        "jerk_compatible": jerk_compatible,
        "lateral_compatible": lateral_compatible,
        "strict_safety_progress_comfort_good": strict_good,
        "original_beneficial_but_not_strict_good": (
            row["class"] == CLASS_BENEFICIAL and not strict_good
        ),
        "record_key": _record_key(row),
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    status = decision.get("status")
    primary_gap = decision.get("primary_gap")
    next_work = decision.get("authorized_next_work")
    passed = (
        bool(decision.get("passed"))
        and status == BOTTLENECK_READY_STATUS
        and primary_gap == SOURCE_PRIMARY_GAP
        and next_work == SOURCE_NEXT_WORK
    )
    return {
        "passed": passed,
        "status": status,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
    }


def _source_records(report: dict[str, Any]) -> dict[str, Any]:
    records = report.get("records")
    if not isinstance(records, dict):
        return {}
    return {
        "total_records": records.get("total_records"),
        "payload_candidate_rows": records.get("payload_candidate_rows"),
        "classified_candidate_rows": records.get("classified_candidate_rows"),
        "alternative_rows": records.get("alternative_rows"),
        "formal_seed_records": records.get("formal_seed_records"),
        "class_counts": records.get("class_counts"),
    }


def _best_screen(report: dict[str, Any]) -> dict[str, Any] | None:
    best = report.get("best_screen")
    if isinstance(best, dict):
        return best
    failure_gap = report.get("failure_gap")
    if isinstance(failure_gap, dict) and isinstance(failure_gap.get("best_screen"), dict):
        return failure_gap["best_screen"]
    return None


def _label_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    beneficial = [row for row in rows if row["class"] == CLASS_BENEFICIAL]
    strict = [row for row in beneficial if row["strict_safety_progress_comfort_good"]]
    permissive = [
        row for row in beneficial if row["original_beneficial_but_not_strict_good"]
    ]
    return {
        "original_beneficial_count": len(beneficial),
        "strict_safety_progress_comfort_good_count": len(strict),
        "original_beneficial_but_not_strict_good_count": len(permissive),
        "strict_good_rate_among_original_beneficial": _rate(len(strict), len(beneficial)),
        "permissive_reason_counts": _compatibility_reason_counts(permissive),
        "strict_good_summary": _row_summary(strict),
        "permissive_beneficial_summary": _row_summary(permissive),
    }


def _atom_audit(grouped: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    blocked_beneficial = grouped["blocked_beneficial"]
    retained_beneficial = grouped["retained_beneficial"]
    strict_blocked = [
        row for row in blocked_beneficial if row["strict_safety_progress_comfort_good"]
    ]
    strict_retained = [
        row for row in retained_beneficial if row["strict_safety_progress_comfort_good"]
    ]
    strict_total = len(strict_blocked) + len(strict_retained)
    return {
        "blocked_beneficial_count": len(blocked_beneficial),
        "retained_beneficial_count": len(retained_beneficial),
        "strict_good_blocked_count": len(strict_blocked),
        "strict_good_retained_count": len(strict_retained),
        "strict_good_block_rate": _rate(len(strict_blocked), strict_total),
        "blocked_beneficial_reason_counts": _compatibility_reason_counts(blocked_beneficial),
        "strict_good_blocked_summary": _row_summary(strict_blocked),
        "retained_beneficial_summary": _row_summary(retained_beneficial),
    }


def _candidate_set_audit(rows: list[dict[str, Any]], record_count: int) -> dict[str, Any]:
    record_keys = {_record_key(row) for row in rows}
    strict_record_keys = {
        _record_key(row)
        for row in rows
        if row["strict_safety_progress_comfort_good"]
    }
    beneficial_record_keys = {
        _record_key(row) for row in rows if row["class"] == CLASS_BENEFICIAL
    }
    harmful_record_keys = {
        _record_key(row) for row in rows if row["class"] == CLASS_HARMFUL
    }
    strict_rows = [
        row for row in rows if row["strict_safety_progress_comfort_good"]
    ]
    return {
        "record_count": record_count,
        "alternative_record_count": len(record_keys),
        "records_with_original_beneficial": len(beneficial_record_keys),
        "records_with_harmful": len(harmful_record_keys),
        "records_with_strict_good_candidate": len(strict_record_keys),
        "strict_good_record_rate": _rate(len(strict_record_keys), record_count),
        "strict_good_candidate_count": len(strict_rows),
        "strict_good_summary": _row_summary(strict_rows),
    }


def _hypothesis(
    label_audit: dict[str, Any],
    atom_audit: dict[str, Any],
    candidate_set_audit: dict[str, Any],
    *,
    min_strict_good_record_rate: float,
    min_strict_good_beneficial_rate: float,
    atom_overpenalty_block_rate: float,
) -> dict[str, Any]:
    strict_good_rate = float(
        label_audit["strict_good_rate_among_original_beneficial"]
    )
    strict_record_rate = float(candidate_set_audit["strict_good_record_rate"])
    strict_block_rate = float(atom_audit["strict_good_block_rate"])
    if strict_good_rate < float(min_strict_good_beneficial_rate):
        primary = "beneficial_label_too_permissive_for_safety_score_intent"
        recommended = "tighten_offline_label_definition_before_atom_redesign"
    elif strict_record_rate < float(min_strict_good_record_rate):
        primary = "dp_candidate_set_strict_good_support_insufficient"
        recommended = "expand_nonformal_support_or_reject_revised_context_route"
    elif strict_block_rate >= float(atom_overpenalty_block_rate):
        primary = "revised_atoms_overpenalize_strict_good_candidates"
        recommended = "predeclare_new_no_leak_atom_shape_before_replay"
    else:
        primary = "mixed_label_atom_candidate_set_bottleneck"
        recommended = "predeclare_label_and_atom_sensitivity_audit"
    return {
        "primary_gap": primary,
        "recommended_next_gate": recommended,
        "strict_good_rate_among_original_beneficial": strict_good_rate,
        "strict_good_record_rate": strict_record_rate,
        "strict_good_block_rate": strict_block_rate,
        "camp_retraining_recommended": False,
        "online_selector_recommended": False,
    }


def _compatibility_reason_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        reasons = []
        if not row["progress_compatible"]:
            reasons.append("progress_loss")
        if not row["jerk_compatible"]:
            reasons.append("jerk_worse")
        if not row["lateral_compatible"]:
            reasons.append("lateral_worse")
        if row["hard_safety_worse_vs_top1"]:
            reasons.append("hard_safety_worse")
        if not row["hard_safety_improved_vs_top1"]:
            reasons.append("no_hard_safety_improvement")
        if row["safety_penalty_delta_vs_top1"] > -0.05:
            reasons.append("diagnostic_safety_penalty_not_improved")
        if not reasons:
            reasons.append("strict_good")
        for reason in reasons:
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _row_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(rows),
        "value_delta_mean": _mean([row["outcome_value_delta_vs_top1"] for row in rows]),
        "progress_delta_mean_m": _mean([row["progress_delta_vs_top1_m"] for row in rows]),
        "safety_penalty_delta_mean": _mean(
            [row["safety_penalty_delta_vs_top1"] for row in rows]
        ),
        "jerk_delta_mean_mps3": _mean(
            [row["mean_jerk_delta_vs_top1_mps3"] for row in rows]
        ),
        "lateral_delta_mean_mps2": _mean(
            [row["mean_lateral_acceleration_delta_vs_top1_mps2"] for row in rows]
        ),
        "top_examples": _examples(rows),
    }


def _examples(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
                "strict_safety_progress_comfort_good": row[
                    "strict_safety_progress_comfort_good"
                ],
                "outcome_value_delta_vs_top1": row["outcome_value_delta_vs_top1"],
                "progress_delta_vs_top1_m": row["progress_delta_vs_top1_m"],
                "safety_penalty_delta_vs_top1": row["safety_penalty_delta_vs_top1"],
                "mean_jerk_delta_vs_top1_mps3": row[
                    "mean_jerk_delta_vs_top1_mps3"
                ],
                "mean_lateral_acceleration_delta_vs_top1_mps2": row[
                    "mean_lateral_acceleration_delta_vs_top1_mps2"
                ],
            }
        )
    return examples


def _safety_penalty(outcome: dict[str, Any]) -> float:
    penalty = 0.0
    for field in HARD_FIELDS:
        penalty += SAFETY_PENALTY_WEIGHTS[field] * int(bool(outcome[field]))
    penalty += SAFETY_PENALTY_WEIGHTS["infeasible"] * int(not outcome["feasible"])
    if outcome["mean_lateral_acceleration_mps2"] is not None:
        penalty += (
            SAFETY_PENALTY_WEIGHTS["mean_lateral_acceleration_mps2"]
            * float(outcome["mean_lateral_acceleration_mps2"])
        )
    if outcome["mean_jerk_mps3"] is not None:
        penalty += (
            SAFETY_PENALTY_WEIGHTS["mean_jerk_mps3"]
            * float(outcome["mean_jerk_mps3"])
        )
    return float(penalty)


def _blocked_primary_gap(
    source: dict[str, Any],
    best: dict[str, Any] | None,
    rows: list[dict[str, Any]],
    missing_outcome_records: int,
) -> str:
    if not source.get("passed"):
        return "source_bottleneck_gate_not_ready"
    if best is None:
        return "source_bottleneck_report_missing_best_screen"
    if missing_outcome_records:
        return "matched_outcomes_missing_for_label_objective_audit"
    if not rows:
        return "no_classified_candidate_rows_for_label_objective_audit"
    return "source_not_ready"


def _record_key(row: dict[str, Any]) -> str:
    context = row.get("context") or {}
    return f"{context.get('log_path')}#{context.get('record_index')}"


def _finite_float(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be finite.") from exc
    if not np.isfinite(result):
        raise ValueError(f"{label} must be finite.")
    return result


def _optional_finite_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def _optional_delta(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None:
        return None
    return float(value) - float(baseline)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Revised Context Label/Objective Audit",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Gate",
        "",
        "```json",
        json.dumps(report["source_bottleneck_gate"], indent=2, sort_keys=True),
        "```",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Label Audit",
        "",
        "```json",
        json.dumps(report["label_audit"], indent=2, sort_keys=True),
        "```",
        "",
        "## Atom Audit",
        "",
        "```json",
        json.dumps(report["atom_audit"], indent=2, sort_keys=True),
        "```",
        "",
        "## Candidate-Set Audit",
        "",
        "```json",
        json.dumps(report["candidate_set_audit"], indent=2, sort_keys=True),
        "```",
        "",
        "## Hypothesis Diagnosis",
        "",
        "```json",
        json.dumps(report["hypothesis_diagnosis"], indent=2, sort_keys=True),
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
