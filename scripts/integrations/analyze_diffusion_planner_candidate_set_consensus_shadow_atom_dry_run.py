#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
if str(CAMP_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CAMP_CORE_SRC))

from camp_core.integrations.diffusion_planner_candidate_set_consensus_payload import (
    CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES,
    CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_dry_run import (
    ATOM_NAME,
    AUTHORIZED_NEXT_WORK as SOURCE_READY_NEXT_WORK,
    BLOCKED_ACTIONS as SOURCE_BLOCKED_ACTIONS,
    COEFFICIENT_FIELD,
    FORMAL_SEEDS,
    PAYLOAD_KEY,
    READY_STATUS as SOURCE_READY_STATUS,
)


READY_STATUS = "candidate_set_consensus_shadow_atom_dry_run_ready"
REJECT_STATUS = "candidate_set_consensus_shadow_atom_dry_run_rejected"
AUTHORIZED_NEXT_WORK = "candidate_set_consensus_shadow_atom_dry_run_result_review_only"

LOG_NAME = "camp_selection_log.json"
BASE_SCORE_TOLERANCE = 1e-9
SHADOW_SCORE_TOLERANCE = 0.0

BLOCKED_ACTIONS = (
    "safety_benefit_evidence",
    "atom_promotion_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Shadow-only dry run for appending the candidate-set consensus "
            "coefficient to offline CAMP atom tables with zero weight. This "
            "reads existing logs only and does not execute DP, train CAMP, "
            "promote atoms, or mutate online selection."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--shadow_plan_json", type=Path)
    source.add_argument(
        "--atom_design_review_json",
        dest="shadow_plan_json",
        type=Path,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--expected_logs", type=int, required=True)
    parser.add_argument("--expected_records", type=int, required=True)
    parser.add_argument("--expected_candidates", type=int, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        shadow_plan=_load_json(args.shadow_plan_json),
        candidate_root=args.candidate_root,
        expected_logs=args.expected_logs,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        label=args.label,
        paths={
            "shadow_plan_json": str(args.shadow_plan_json),
            "candidate_root": str(args.candidate_root),
        },
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(1)


def analyze(
    *,
    shadow_plan: dict[str, Any],
    candidate_root: Path,
    expected_logs: int,
    expected_records: int,
    expected_candidates: int,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    if expected_logs <= 0:
        raise ValueError("expected_logs must be positive.")
    if expected_records <= 0:
        raise ValueError("expected_records must be positive.")
    if expected_candidates <= 0:
        raise ValueError("expected_candidates must be positive.")

    log_payloads = _load_selection_logs(candidate_root)
    source = _source_summary(shadow_plan)
    records = [
        _shadow_record(
            record=record,
            run_id=log["run_id"],
            log_path=log["path"],
            formal_seed_detected=bool(log["formal_seed_detected"]),
            record_index=record_index,
            global_index=global_index,
            expected_candidates=expected_candidates,
        )
        for global_index, (log, record_index, record) in enumerate(
            _iter_records(log_payloads)
        )
    ]
    summary = _summary(records, log_payloads)
    checks = [
        *_source_checks(
            source,
            expected_logs=expected_logs,
            expected_records=expected_records,
            expected_candidates=expected_candidates,
        ),
        *_input_checks(
            summary,
            expected_logs=expected_logs,
            expected_records=expected_records,
        ),
        *_shadow_checks(summary),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_shadow_atom_dry_run_v1",
            "label": label,
            "role": (
                "read-only shadow atom table append over existing broader "
                "nonformal logs"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "deployed_atom_schema_change": False,
            "future_outcome_labels_used": False,
            "safety_score_fields_read": False,
            "formal_seed_records": int(summary["formal_seed_log_count"]),
            "paths": paths or {"candidate_root": str(candidate_root)},
            "math_boundary": (
                "This dry run reads existing logging-enabled nonformal records "
                "only. For available payloads it appends the fixed current-tick "
                "candidate-set consensus coefficient as a shadow atom and "
                "appends a zero shadow weight. Therefore selector-visible "
                "score_k(w)=a_k^T w values, selection_scores, selected_index, "
                "feasible_mask, fallback mode, and infeasibility reasons must "
                "remain unchanged. It does not train CAMP, execute or modify DP, "
                "deploy the atom, read closed-loop outcomes or safety scores, "
                "use formal seeds, or claim a DP-side classical Benders "
                "decomposition."
            ),
        },
        "source_summary": source,
        "record_checks": checks,
        "dry_run_records": records,
        "dry_run_summary": summary,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks, summary),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["dry_run_summary"]
    lines = [
        "# Candidate-Set Consensus Shadow Atom Dry Run",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Shadow appended records: `{summary['shadow_appended_records']}`",
        f"- Ranking signal records: `{summary['ranking_signal_records']}`",
        f"- Consensus-only changed records: `{summary['consensus_only_would_change_selected_index_records']}`",
        f"- Max zero-weight score diff: `{summary['max_shadow_zero_weight_score_abs_diff']}`",
        f"- Max zero-weight selection-score diff: `{summary['max_shadow_zero_weight_selection_score_abs_diff']}`",
        f"- Formal seed logs: `{summary['formal_seed_log_count']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        "",
        "## Summary",
        "",
        f"`{summary}`",
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["record_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    plan = _dict(report.get("dry_run_plan"))
    policy = _dict(plan.get("shadow_append_policy"))
    conflicts = [
        key
        for key in set((*SOURCE_BLOCKED_ACTIONS, *BLOCKED_ACTIONS))
        if bool(decision.get(key))
    ]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "shadow_atom_dry_run_plan_ready": bool(
            decision.get("shadow_atom_dry_run_plan_ready")
        ),
        "dry_run_implementation_authorized": bool(
            decision.get("dry_run_implementation_authorized")
        ),
        "dry_run_execution_authorized": bool(
            decision.get("dry_run_execution_authorized")
        ),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "blocked_action_conflicts": sorted(conflicts),
        "plan_only": bool(plan.get("plan_only")),
        "expected_logs": _optional_int(plan.get("expected_logs")),
        "expected_records": _optional_int(plan.get("expected_records")),
        "expected_candidates": _optional_int(plan.get("expected_candidates")),
        "formal_seeds_forbidden": sorted(
            _optional_int(seed)
            for seed in (plan.get("formal_seeds_forbidden") or [])
            if _optional_int(seed) is not None
        ),
        "atom_name": plan.get("atom_name"),
        "payload_key": plan.get("payload_key"),
        "coefficient_field": plan.get("coefficient_field"),
        "weight_append_value": _optional_float(policy.get("weight_append_value")),
        "selection_weight_append_value": _optional_float(
            policy.get("selection_weight_append_value")
        ),
        "score_delta_tolerance": _optional_float(policy.get("score_delta_tolerance")),
        "write_runtime_logs": bool(policy.get("write_runtime_logs")),
    }


def _source_checks(
    source: dict[str, Any],
    *,
    expected_logs: int,
    expected_records: int,
    expected_candidates: int,
) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_implementation_unit_tests",
            source["authorized_next_work"],
            SOURCE_READY_NEXT_WORK,
        ),
        _check_equal(
            "source_shadow_plan_ready",
            source["shadow_atom_dry_run_plan_ready"],
            True,
        ),
        _check_equal(
            "source_implementation_authorized",
            source["dry_run_implementation_authorized"],
            True,
        ),
        _check_equal(
            "source_execution_not_pre_authorized",
            source["dry_run_execution_authorized"],
            False,
        ),
        _check_equal(
            "source_atom_promotion_not_authorized",
            source["atom_promotion_authorized"],
            False,
        ),
        _check_equal(
            "source_safety_benefit_not_claimed",
            source["safety_benefit_evidence"],
            False,
        ),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal("source_plan_only", source["plan_only"], True),
        _check_equal("source_expected_logs", source["expected_logs"], expected_logs),
        _check_equal(
            "source_expected_records",
            source["expected_records"],
            expected_records,
        ),
        _check_equal(
            "source_expected_candidates",
            source["expected_candidates"],
            expected_candidates,
        ),
        _check_equal(
            "source_formal_seeds_forbidden",
            source["formal_seeds_forbidden"],
            sorted(FORMAL_SEEDS),
        ),
        _check_equal("source_atom_name", source["atom_name"], ATOM_NAME),
        _check_equal("source_payload_key", source["payload_key"], PAYLOAD_KEY),
        _check_equal(
            "source_coefficient_field",
            source["coefficient_field"],
            COEFFICIENT_FIELD,
        ),
        _check_equal("source_zero_weight_append", source["weight_append_value"], 0.0),
        _check_equal(
            "source_zero_selection_weight_append",
            source["selection_weight_append_value"],
            0.0,
        ),
        _check_equal(
            "source_score_delta_tolerance_exact_zero",
            source["score_delta_tolerance"],
            SHADOW_SCORE_TOLERANCE,
        ),
        _check_equal("source_runtime_logs_not_written", source["write_runtime_logs"], False),
    ]


def _input_checks(
    summary: dict[str, Any],
    *,
    expected_logs: int,
    expected_records: int,
) -> list[dict[str, Any]]:
    return [
        _check_equal("log_count", summary["log_count"], expected_logs),
        _check_equal("record_count", summary["records"], expected_records),
        _check_equal("no_formal_seed_logs", summary["formal_seed_log_count"], 0),
    ]


def _shadow_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("all_records_valid", summary["valid_records"], summary["records"]),
        _check_equal("all_payloads_available", summary["available_records"], summary["records"]),
        _check_equal(
            "shadow_appended_all_records",
            summary["shadow_appended_records"],
            summary["records"],
        ),
        _check_equal("record_errors_empty", summary["record_error_counts"], {}),
        _check_equal(
            "ranking_signal_present",
            summary["ranking_signal_records"] > 0,
            True,
        ),
        _check_equal(
            "deployed_selection_preserved_all_records",
            summary["deployed_selection_preserved_records"],
            summary["records"],
        ),
        _check_equal(
            "fallback_state_preserved_all_records",
            summary["fallback_state_preserved_records"],
            summary["records"],
        ),
        _check_equal(
            "base_affine_scores_match_logs",
            summary["max_base_score_abs_diff"] <= BASE_SCORE_TOLERANCE,
            True,
        ),
        _check_equal(
            "base_affine_selection_scores_match_logs",
            summary["max_base_selection_score_abs_diff"] <= BASE_SCORE_TOLERANCE,
            True,
        ),
        _check_equal(
            "shadow_zero_weight_scores_unchanged",
            summary["max_shadow_zero_weight_score_abs_diff"],
            SHADOW_SCORE_TOLERANCE,
        ),
        _check_equal(
            "shadow_zero_weight_selection_scores_unchanged",
            summary["max_shadow_zero_weight_selection_score_abs_diff"],
            SHADOW_SCORE_TOLERANCE,
        ),
        _check_equal("online_selector_mutated", False, False),
        _check_equal("deployed_atom_schema_mutated", False, False),
        _check_equal("safety_score_fields_read", False, False),
    ]


def _shadow_record(
    *,
    record: dict[str, Any],
    run_id: str,
    log_path: str,
    formal_seed_detected: bool,
    record_index: int,
    global_index: int,
    expected_candidates: int,
) -> dict[str, Any]:
    errors: list[str] = []
    if formal_seed_detected:
        errors.append("formal_seed_detected")
    payload = record.get(PAYLOAD_KEY)
    if not isinstance(payload, dict):
        return _record_error(
            run_id,
            log_path,
            record_index,
            global_index,
            "payload_missing",
            extra_errors=errors,
        )

    _payload_boundary_errors(payload, record, errors)
    selected_index = _optional_int(record.get("selected_index"))
    candidate_count = _optional_int(payload.get("candidate_count"))
    if candidate_count != expected_candidates:
        errors.append("candidate_count_mismatch")

    atom_names = _string_list(record.get("atom_names"))
    weights = _float_vector(record.get("weights"))
    selection_weights = _float_vector(record.get("selection_weights"))
    atoms = _matrix(record.get("atoms"))
    normalized_atoms = _matrix(record.get("normalized_atoms"))
    selection_normalized_atoms = _matrix(record.get("selection_normalized_atoms"))
    if not selection_normalized_atoms:
        selection_normalized_atoms = normalized_atoms
    scores = _score_vector(record.get("scores"))
    selection_scores = _score_vector(record.get("selection_scores"))
    feasible_mask = _bool_vector(record.get("feasible_mask"), expected_candidates)
    infeasibility_reasons = record.get("infeasibility_reasons")
    has_fallback_mode = "camp_fallback_mode" in record
    has_used_fallback = "used_fallback" in record

    if not atom_names:
        errors.append("atom_names_missing")
    if len(weights) != len(atom_names):
        errors.append("weights_shape_mismatch")
    if len(selection_weights) != len(atom_names):
        errors.append("selection_weights_shape_mismatch")
    if _shape(atoms) != [expected_candidates, len(atom_names)]:
        errors.append("atoms_shape_mismatch")
    if _shape(normalized_atoms) != [expected_candidates, len(atom_names)]:
        errors.append("normalized_atoms_shape_mismatch")
    if _shape(selection_normalized_atoms) != [expected_candidates, len(atom_names)]:
        errors.append("selection_normalized_atoms_shape_mismatch")
    if len(scores) != expected_candidates:
        errors.append("scores_shape_mismatch")
    if len(selection_scores) != expected_candidates:
        errors.append("selection_scores_shape_mismatch")
    if len(feasible_mask) != expected_candidates:
        errors.append("feasible_mask_shape_mismatch")
    if selected_index is None or selected_index < 0 or selected_index >= expected_candidates:
        errors.append("selected_index_invalid")
    if not has_fallback_mode:
        errors.append("camp_fallback_mode_missing")
    if not has_used_fallback:
        errors.append("used_fallback_missing")
    if not isinstance(infeasibility_reasons, list):
        errors.append("infeasibility_reasons_missing")

    base_scores = _dot_scores(normalized_atoms, weights)
    base_selection_scores = _masked_selection_scores(
        _dot_scores(selection_normalized_atoms, selection_weights),
        feasible_mask,
    )
    base_score_max_abs_diff = _max_abs_score_diff(base_scores, scores)
    base_selection_score_max_abs_diff = _max_abs_score_diff(
        base_selection_scores,
        selection_scores,
    )
    if (
        not math.isfinite(base_score_max_abs_diff)
        or base_score_max_abs_diff > BASE_SCORE_TOLERANCE
    ):
        errors.append("base_affine_score_mismatch")
    if (
        not math.isfinite(base_selection_score_max_abs_diff)
        or base_selection_score_max_abs_diff > BASE_SCORE_TOLERANCE
    ):
        errors.append("selection_affine_score_mismatch")
    base_selected_from_scores = _argmin(selection_scores)
    if selected_index is not None and base_selected_from_scores != selected_index:
        errors.append("selected_index_selection_score_mismatch")

    available = bool(payload.get("available"))
    availability_reason = payload.get("availability_reason")
    if not available:
        errors.append("payload_unavailable")
        return {
            "run_id": run_id,
            "log_path": log_path,
            "record_index": record_index,
            "global_index": global_index,
            "available": False,
            "availability_reason": availability_reason,
            "selected_index": selected_index,
            "candidate_count": candidate_count,
            "base_atom_count": len(atom_names),
            "shadow_atom_count": len(atom_names),
            "shadow_append_available": False,
            "shadow_append_reason": "fail_closed_unavailable",
            "base_score_max_abs_diff": base_score_max_abs_diff,
            "base_selection_score_max_abs_diff": base_selection_score_max_abs_diff,
            "shadow_zero_weight_score_max_abs_diff": 0.0,
            "shadow_zero_weight_selection_score_max_abs_diff": 0.0,
            "deployed_selection_preserved": False,
            "fallback_state_preserved": not any(
                error
                in {
                    "camp_fallback_mode_missing",
                    "used_fallback_missing",
                    "infeasibility_reasons_missing",
                }
                for error in errors
            ),
            "ranking_signal_present": False,
            "consensus_only_best_index": None,
            "consensus_only_would_change_selected_index": False,
            "errors": errors,
            "passed": False,
        }

    coeff = _float_vector(payload.get(COEFFICIENT_FIELD))
    if len(coeff) != expected_candidates:
        errors.append("coefficient_shape_mismatch")
    if any((not math.isfinite(value)) or value < 0.0 for value in coeff):
        errors.append("coefficient_nonfinite_or_negative")

    shadow_weights = [*weights, 0.0]
    shadow_selection_weights = [*selection_weights, 0.0]
    shadow_atoms = _append_column(atoms, coeff)
    shadow_normalized_atoms = _append_column(normalized_atoms, coeff)
    shadow_selection_normalized_atoms = _append_column(selection_normalized_atoms, coeff)
    shadow_scores = _dot_scores(shadow_normalized_atoms, shadow_weights)
    shadow_selection_scores = _masked_selection_scores(
        _dot_scores(shadow_selection_normalized_atoms, shadow_selection_weights),
        feasible_mask,
    )
    shadow_zero_diff = _max_abs_score_diff(shadow_scores, base_scores)
    shadow_selection_zero_diff = _max_abs_score_diff(
        shadow_selection_scores,
        base_selection_scores,
    )
    if shadow_zero_diff != SHADOW_SCORE_TOLERANCE:
        errors.append("shadow_zero_weight_score_changed")
    if shadow_selection_zero_diff != SHADOW_SCORE_TOLERANCE:
        errors.append("shadow_zero_weight_selection_score_changed")
    shadow_selected_index = _argmin(shadow_selection_scores)
    if selected_index is not None and shadow_selected_index != selected_index:
        errors.append("shadow_selected_index_changed")

    consensus_only_best = _argmin_feasible(coeff, feasible_mask)
    consensus_only_changed = (
        selected_index is not None
        and consensus_only_best is not None
        and consensus_only_best != selected_index
    )
    fallback_state_preserved = not any(
        error
        in {
            "camp_fallback_mode_missing",
            "used_fallback_missing",
            "infeasibility_reasons_missing",
        }
        for error in errors
    )
    return {
        "run_id": run_id,
        "log_path": log_path,
        "record_index": record_index,
        "global_index": global_index,
        "available": True,
        "availability_reason": availability_reason,
        "selected_index": selected_index,
        "base_selected_index_from_selection_scores": base_selected_from_scores,
        "shadow_selected_index": shadow_selected_index,
        "candidate_count": candidate_count,
        "base_atom_count": len(atom_names),
        "shadow_atom_count": len(atom_names) + 1,
        "shadow_atom_name": ATOM_NAME,
        "shadow_append_available": True,
        "shadow_append_reason": "available_current_tick_coefficient",
        "base_atom_table_shape": _shape(atoms),
        "shadow_atom_table_shape": _shape(shadow_atoms),
        "shadow_normalized_atom_table_shape": _shape(shadow_normalized_atoms),
        "shadow_selection_normalized_atom_table_shape": _shape(
            shadow_selection_normalized_atoms
        ),
        "shadow_weight_count": len(shadow_weights),
        "shadow_weight_last": 0.0,
        "shadow_selection_weight_last": 0.0,
        "base_score_max_abs_diff": base_score_max_abs_diff,
        "base_selection_score_max_abs_diff": base_selection_score_max_abs_diff,
        "shadow_zero_weight_score_max_abs_diff": shadow_zero_diff,
        "shadow_zero_weight_selection_score_max_abs_diff": shadow_selection_zero_diff,
        "selection_effect": False,
        "deployed_selection_preserved": shadow_selected_index == selected_index,
        "feasible_mask_preserved": True,
        "fallback_state_preserved": fallback_state_preserved,
        "used_fallback": bool(record.get("used_fallback", False)),
        "camp_fallback_mode": record.get("camp_fallback_mode"),
        "infeasibility_reasons_preserved": isinstance(infeasibility_reasons, list),
        "ranking_signal_present": _has_ranking_signal(coeff),
        "consensus_only_best_index": consensus_only_best,
        "consensus_only_would_change_selected_index": consensus_only_changed,
        "consensus_coefficient_min": min(coeff) if coeff else None,
        "consensus_coefficient_max": max(coeff) if coeff else None,
        "errors": errors,
        "passed": not errors,
    }


def _payload_boundary_errors(
    payload: dict[str, Any],
    record: dict[str, Any],
    errors: list[str],
) -> None:
    expected_scalars = {
        "schema_version": CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "deployed_atom_vector_change": False,
        "classical_benders_claim": False,
    }
    for key, expected in expected_scalars.items():
        if payload.get(key) != expected:
            errors.append(f"payload_{key}_mismatch")
    if payload.get("atom_candidate_names") != list(
        CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES
    ):
        errors.append("payload_atom_candidate_names_mismatch")
    if record.get("candidate_closed_loop_outcomes") is not None:
        errors.append("candidate_closed_loop_outcomes_present")


def _record_error(
    run_id: str,
    log_path: str,
    record_index: int,
    global_index: int,
    reason: str,
    *,
    extra_errors: list[str] | None = None,
) -> dict[str, Any]:
    errors = [*(extra_errors or []), reason]
    return {
        "run_id": run_id,
        "log_path": log_path,
        "record_index": record_index,
        "global_index": global_index,
        "available": False,
        "shadow_append_available": False,
        "errors": errors,
        "passed": False,
    }


def _summary(
    records: list[dict[str, Any]],
    log_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    available = [record for record in records if record.get("available") is True]
    unavailable = [record for record in records if record.get("available") is False]
    valid = [record for record in records if record.get("passed") is True]
    ranking = [record for record in available if record.get("ranking_signal_present")]
    consensus_change = [
        record
        for record in available
        if record.get("consensus_only_would_change_selected_index")
    ]
    score_diffs = [
        float(record.get("shadow_zero_weight_score_max_abs_diff", math.nan))
        for record in records
    ]
    selection_score_diffs = [
        float(record.get("shadow_zero_weight_selection_score_max_abs_diff", math.nan))
        for record in records
    ]
    base_score_diffs = [
        float(record.get("base_score_max_abs_diff", math.nan)) for record in records
    ]
    base_selection_score_diffs = [
        float(record.get("base_selection_score_max_abs_diff", math.nan))
        for record in records
    ]
    formal_logs = [log for log in log_payloads if log.get("formal_seed_detected")]
    return {
        "log_count": len(log_payloads),
        "records": len(records),
        "valid_records": len(valid),
        "available_records": len(available),
        "unavailable_records": len(unavailable),
        "fail_closed_unavailable_records": sum(
            1
            for record in unavailable
            if record.get("shadow_append_reason") == "fail_closed_unavailable"
        ),
        "formal_seed_log_count": len(formal_logs),
        "formal_seed_log_paths": [str(log["path"]) for log in formal_logs],
        "shadow_appended_records": sum(
            1 for record in records if record.get("shadow_append_available") is True
        ),
        "ranking_signal_records": len(ranking),
        "consensus_only_would_change_selected_index_records": len(consensus_change),
        "consensus_only_changed_indices": [
            record["global_index"] for record in consensus_change
        ],
        "deployed_selection_preserved_records": sum(
            1 for record in records if record.get("deployed_selection_preserved") is True
        ),
        "fallback_state_preserved_records": sum(
            1 for record in records if record.get("fallback_state_preserved") is True
        ),
        "max_base_score_abs_diff": _finite_max(base_score_diffs),
        "max_base_selection_score_abs_diff": _finite_max(base_selection_score_diffs),
        "max_shadow_zero_weight_score_abs_diff": _finite_max(score_diffs),
        "max_shadow_zero_weight_selection_score_abs_diff": _finite_max(
            selection_score_diffs
        ),
        "record_error_counts": _error_counts(records),
        "shadow_weight_policy": "append_zero_weight_no_deployed_effect",
    }


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "shadow_atom_dry_run_ready": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "ranking_signal_records": summary["ranking_signal_records"],
        "consensus_only_would_change_selected_index_records": summary[
            "consensus_only_would_change_selected_index_records"
        ],
        "max_shadow_zero_weight_score_abs_diff": summary[
            "max_shadow_zero_weight_score_abs_diff"
        ],
        "max_shadow_zero_weight_selection_score_abs_diff": summary[
            "max_shadow_zero_weight_selection_score_abs_diff"
        ],
        "next_step": (
            "Review the dry-run result artifact only. Keep the atom shadow-only; "
            "do not train CAMP, deploy online selection, run replay, run Full36, "
            "use formal seeds, modify DP, or claim safety benefit."
            if passed
            else "Reject the shadow atom dry-run and inspect failed source/input/record checks."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _load_selection_logs(root: Path) -> list[dict[str, Any]]:
    paths = sorted(path for path in root.glob(f"*/{LOG_NAME}") if path.is_file())
    result = []
    for path in paths:
        payload = _load_json(path)
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON list.")
        path_text = str(path)
        run_id = path.parent.name
        result.append(
            {
                "run_id": run_id,
                "path": path_text,
                "formal_seed_detected": _contains_formal_seed(
                    f"{run_id} {path_text}"
                ),
                "records": [row for row in payload if isinstance(row, dict)],
            }
        )
    return result


def _iter_records(
    logs: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], int, dict[str, Any]]]:
    rows: list[tuple[dict[str, Any], int, dict[str, Any]]] = []
    for log in logs:
        rows.extend(
            (log, index, record)
            for index, record in enumerate(log.get("records") or [])
            if isinstance(record, dict)
        )
    return rows


def _contains_formal_seed(text: str) -> bool:
    lower = text.lower()
    for seed in FORMAL_SEEDS:
        if re.search(rf"(?<!\d)seed[-_]?{seed}(?!\d)", lower):
            return True
        if re.search(rf"(?<!\d)formal[-_]?seed[-_]?{seed}(?!\d)", lower):
            return True
    return False


def _append_column(matrix: list[list[float]], values: list[float]) -> list[list[float]]:
    if len(matrix) != len(values):
        return []
    return [[*row, values[index]] for index, row in enumerate(matrix)]


def _dot_scores(matrix: list[list[float]], weights: list[float]) -> list[float]:
    if not matrix or not weights:
        return []
    return [sum(value * weight for value, weight in zip(row, weights)) for row in matrix]


def _masked_selection_scores(scores: list[float], feasible_mask: list[bool]) -> list[float]:
    if feasible_mask and not any(feasible_mask):
        return list(scores)
    return [
        score if index < len(feasible_mask) and feasible_mask[index] else math.inf
        for index, score in enumerate(scores)
    ]


def _max_abs_score_diff(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return math.inf
    diffs = []
    for a, b in zip(left, right):
        if math.isinf(a) and math.isinf(b):
            diffs.append(0.0)
        elif math.isfinite(a) and math.isfinite(b):
            diffs.append(abs(a - b))
        else:
            return math.inf
    return max(diffs) if diffs else 0.0


def _argmin(values: list[float]) -> int | None:
    if not values:
        return None
    best_index, _ = min(enumerate(values), key=lambda item: (item[1], item[0]))
    return int(best_index)


def _argmin_feasible(values: list[float], feasible_mask: list[bool]) -> int | None:
    candidates = [
        (index, value)
        for index, value in enumerate(values)
        if index < len(feasible_mask) and feasible_mask[index]
    ]
    if not candidates:
        return None
    best_index, _ = min(candidates, key=lambda item: (item[1], item[0]))
    return int(best_index)


def _has_ranking_signal(values: list[float]) -> bool:
    return bool(values) and max(values) > min(values)


def _shape(matrix: list[list[float]]) -> list[int]:
    if not matrix:
        return [0, 0]
    return [len(matrix), len(matrix[0]) if matrix[0] else 0]


def _matrix(value: Any) -> list[list[float]]:
    if not isinstance(value, list):
        return []
    matrix = []
    for row in value:
        if not isinstance(row, list):
            return []
        parsed = _float_vector(row)
        if len(parsed) != len(row):
            return []
        matrix.append(parsed)
    return matrix


def _float_vector(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            return []
    return result


def _score_vector(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if item == "inf":
            result.append(math.inf)
            continue
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            return []
    return result


def _bool_vector(value: Any, expected_candidates: int) -> list[bool]:
    if isinstance(value, list):
        return [bool(item) for item in value]
    return [True for _ in range(expected_candidates)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _finite_max(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return max(finite) if finite else math.inf


def _error_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for error in record.get("errors") or []:
            counts[error] = counts.get(error, 0) + 1
    return counts


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
