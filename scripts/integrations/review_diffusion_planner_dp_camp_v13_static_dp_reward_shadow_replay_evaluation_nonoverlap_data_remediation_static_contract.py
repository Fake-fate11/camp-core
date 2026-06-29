#!/usr/bin/env python3
"""Static contract review for v13 non-overlap data remediation planning.

This is a read-only review gate. It consumes the plan-only non-overlap data
remediation artifact and verifies that the plan preserves the fixed-DP/CAMP
reranking boundary before any later implementation-plan gate. It does not run
replay, generate candidates, train CAMP, modify Diffusion Planner, promote
artifacts, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_static_contract_review_v1"
)
READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_static_contract_review_complete"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_static_contract_review_rejected"
)
PLAN_READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_implementation_plan_only"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only static contract review of a v13 static DP-reward "
            "non-overlap data remediation plan."
        )
    )
    parser.add_argument("--nonoverlap_plan_json", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        nonoverlap_plan_json=args.nonoverlap_plan_json,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    nonoverlap_plan_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    nonoverlap_plan_json = nonoverlap_plan_json.resolve()
    v13_audit_md = v13_audit_md.resolve()
    plan = _load_json_dict(nonoverlap_plan_json)
    audit_text = _read_text(v13_audit_md)
    contract = _contract_summary(plan)
    checks = _checks(
        nonoverlap_plan_json=nonoverlap_plan_json,
        v13_audit_md=v13_audit_md,
        audit_text=audit_text,
        plan=plan,
        contract=contract,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "read_only": True,
            "static_contract_review_only": True,
            "training_execution": False,
            "training_preflight": False,
            "replay_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "dp_modification": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {
            "nonoverlap_plan_json": str(nonoverlap_plan_json),
            "v13_audit_md": str(v13_audit_md),
        },
        "contract_summary": contract,
        "review_checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "implementation_plan_authorized_next": passed,
            "implementation_authorized_next": False,
            "training_preflight_authorized_next": False,
            "training_execution_authorized_next": False,
            "replay_execution_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }


def _contract_summary(plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(plan.get("final_decision"))
    remediation = _dict(plan.get("remediation_plan"))
    required = _dict(remediation.get("required_contracts"))
    future = _dict(remediation.get("future_preflight_requirements"))
    verification = _dict(remediation.get("verification_requirements"))
    blocked = _dict(remediation.get("blocked_by_this_plan"))
    analysis = _dict(plan.get("analysis"))
    diagnosis = _dict(plan.get("diagnosis_summary"))
    return {
        "source_plan_status": decision.get("status"),
        "source_plan_passed": decision.get("passed"),
        "source_authorized_next_work": decision.get("authorized_next_work"),
        "source_static_contract_review_authorized_next": decision.get(
            "static_contract_review_authorized_next"
        ),
        "source_diagnosis_status": diagnosis.get("status"),
        "source_diagnosis_not_independent_holdout": diagnosis.get(
            "current_evaluation_is_not_independent_holdout"
        ),
        "source_matched_evaluation_records": diagnosis.get("matched_evaluation_record_count"),
        "split_manifest_required": required.get("split_manifest_required"),
        "training_selection_logs_must_exclude_holdout_roots": required.get(
            "training_selection_logs_must_exclude_holdout_roots"
        ),
        "holdout_selection_logs_must_exclude_training_roots": required.get(
            "holdout_selection_logs_must_exclude_training_roots"
        ),
        "candidate_tensor_hash_registry_required": required.get(
            "candidate_tensor_hash_registry_required"
        ),
        "path_signature_registry_required": required.get("path_signature_registry_required"),
        "record_identity_hash_registry_required": required.get(
            "record_identity_hash_registry_required"
        ),
        "train_eval_candidate_tensor_intersection_must_be_zero": required.get(
            "train_eval_candidate_tensor_intersection_must_be_zero"
        ),
        "train_eval_path_signature_intersection_must_be_zero": required.get(
            "train_eval_path_signature_intersection_must_be_zero"
        ),
        "result_readiness_must_compare_against_all_training_summary_selection_logs": required.get(
            "result_readiness_must_compare_against_all_training_summary_selection_logs"
        ),
        "formal_seeds_11_12_13_excluded": required.get("formal_seeds_11_12_13_excluded"),
        "new_nonoverlap_source_root_required": future.get("new_nonoverlap_source_root_required"),
        "reuse_of_diagnosed_prior_eval_root_for_holdout_forbidden": future.get(
            "reuse_of_diagnosed_prior_eval_root_for_holdout_forbidden"
        ),
        "reuse_of_training_summary_selection_logs_for_holdout_forbidden": future.get(
            "reuse_of_training_summary_selection_logs_for_holdout_forbidden"
        ),
        "minimum_holdout_records": future.get("minimum_holdout_records"),
        "minimum_holdout_selection_logs": future.get("minimum_holdout_selection_logs"),
        "expected_candidate_count": future.get("expected_candidate_count"),
        "expected_atom_count": future.get("expected_atom_count"),
        "fixed_dp_candidate_generation_requires_later_explicit_preflight": future.get(
            "fixed_dp_candidate_generation_requires_later_explicit_preflight"
        ),
        "candidate_tensor_hash_overlap_check_required": verification.get(
            "candidate_tensor_hash_overlap_check_required"
        ),
        "path_signature_overlap_check_required": verification.get(
            "path_signature_overlap_check_required"
        ),
        "same_signature_and_step_hash_overlap_check_required": verification.get(
            "same_signature_and_step_hash_overlap_check_required"
        ),
        "default_off_contract_validation_required": verification.get(
            "default_off_contract_validation_required"
        ),
        "affine_score_contract_required": verification.get("affine_score_contract_required"),
        "dp_head_fixed_check_required": verification.get("dp_head_fixed_check_required"),
        "blocked_training_preflight": blocked.get("training_preflight"),
        "blocked_training_execution": blocked.get("training_execution"),
        "blocked_replay_execution": blocked.get("replay_execution"),
        "blocked_candidate_generation_execution": blocked.get("candidate_generation_execution"),
        "blocked_candidate_generation_by_camp": blocked.get("candidate_generation_by_camp"),
        "blocked_dp_modification": blocked.get("dp_modification"),
        "blocked_selector_promotion": blocked.get("selector_promotion"),
        "blocked_atom_promotion": blocked.get("atom_promotion"),
        "blocked_deployment": blocked.get("deployment"),
        "blocked_safety_claim": blocked.get("safety_benefit_claim"),
        "blocked_camp_over_dp_top1_claim": blocked.get("camp_over_dp_top1_claim"),
        "plan_score_expression": analysis.get("score_expression"),
        "plan_candidate_operation": analysis.get("candidate_operation"),
    }


def _checks(
    *,
    nonoverlap_plan_json: Path,
    v13_audit_md: Path,
    audit_text: str,
    plan: dict[str, Any],
    contract: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(plan.get("final_decision"))
    return [
        _check("nonoverlap_plan_json_exists", nonoverlap_plan_json.is_file(), str(nonoverlap_plan_json), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _check("current_gate_authorized_in_audit", f"next_work_target={authorized_current_work}" in audit_text, authorized_current_work, "present as next_work_target"),
        _check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        _check("dp_head_fixed", current_dp_head == required_dp_head, current_dp_head, required_dp_head),
        _check("source_plan_passed", decision.get("passed") is True, decision.get("passed"), True),
        _check("source_plan_status_ready", decision.get("status") == PLAN_READY_STATUS, decision.get("status"), PLAN_READY_STATUS),
        _check("source_plan_authorizes_current_review", decision.get("authorized_next_work") == authorized_current_work, decision.get("authorized_next_work"), authorized_current_work),
        _expect_true(contract, "source_static_contract_review_authorized_next"),
        _expect_true(contract, "source_diagnosis_not_independent_holdout"),
        _expect_value(contract, "source_matched_evaluation_records", 3200),
        _expect_true(contract, "split_manifest_required"),
        _expect_true(contract, "training_selection_logs_must_exclude_holdout_roots"),
        _expect_true(contract, "holdout_selection_logs_must_exclude_training_roots"),
        _expect_true(contract, "candidate_tensor_hash_registry_required"),
        _expect_true(contract, "path_signature_registry_required"),
        _expect_true(contract, "record_identity_hash_registry_required"),
        _expect_true(contract, "train_eval_candidate_tensor_intersection_must_be_zero"),
        _expect_true(contract, "train_eval_path_signature_intersection_must_be_zero"),
        _expect_true(contract, "result_readiness_must_compare_against_all_training_summary_selection_logs"),
        _expect_true(contract, "formal_seeds_11_12_13_excluded"),
        _expect_true(contract, "new_nonoverlap_source_root_required"),
        _expect_true(contract, "reuse_of_diagnosed_prior_eval_root_for_holdout_forbidden"),
        _expect_true(contract, "reuse_of_training_summary_selection_logs_for_holdout_forbidden"),
        _expect_value(contract, "minimum_holdout_records", 3200),
        _expect_value(contract, "minimum_holdout_selection_logs", 32),
        _expect_value(contract, "expected_candidate_count", 8),
        _expect_value(contract, "expected_atom_count", 14),
        _expect_true(contract, "fixed_dp_candidate_generation_requires_later_explicit_preflight"),
        _expect_true(contract, "candidate_tensor_hash_overlap_check_required"),
        _expect_true(contract, "path_signature_overlap_check_required"),
        _expect_true(contract, "same_signature_and_step_hash_overlap_check_required"),
        _expect_true(contract, "default_off_contract_validation_required"),
        _expect_true(contract, "affine_score_contract_required"),
        _expect_true(contract, "dp_head_fixed_check_required"),
        _expect_true(contract, "blocked_training_preflight"),
        _expect_true(contract, "blocked_training_execution"),
        _expect_true(contract, "blocked_replay_execution"),
        _expect_true(contract, "blocked_candidate_generation_execution"),
        _expect_true(contract, "blocked_candidate_generation_by_camp"),
        _expect_true(contract, "blocked_dp_modification"),
        _expect_true(contract, "blocked_selector_promotion"),
        _expect_true(contract, "blocked_atom_promotion"),
        _expect_true(contract, "blocked_deployment"),
        _expect_true(contract, "blocked_safety_claim"),
        _expect_true(contract, "blocked_camp_over_dp_top1_claim"),
        _expect_value(contract, "plan_score_expression", SCORE_EXPRESSION),
        _expect_value(contract, "plan_candidate_operation", "fixed DP candidate reranking only"),
        _check("source_plan_does_not_authorize_training_preflight", decision.get("training_preflight_authorized_next") is False, decision.get("training_preflight_authorized_next"), False),
        _check("source_plan_does_not_authorize_training_execution", decision.get("training_execution_authorized_next") is False, decision.get("training_execution_authorized_next"), False),
        _check("source_plan_does_not_authorize_replay_execution", decision.get("replay_execution_authorized_next") is False, decision.get("replay_execution_authorized_next"), False),
        _check("source_plan_does_not_authorize_candidate_generation", decision.get("fixed_dp_candidate_generation_authorized_next") is False, decision.get("fixed_dp_candidate_generation_authorized_next"), False),
        _check("source_plan_does_not_authorize_camp_candidate_generation", decision.get("candidate_generation_by_camp_authorized") is False, decision.get("candidate_generation_by_camp_authorized"), False),
        _check("source_plan_does_not_authorize_dp_modification", decision.get("dp_modification_authorized") is False, decision.get("dp_modification_authorized"), False),
        _check("source_plan_does_not_authorize_selector_promotion", decision.get("selector_promotion_authorized") is False, decision.get("selector_promotion_authorized"), False),
        _check("source_plan_does_not_authorize_atom_promotion", decision.get("atom_promotion_authorized") is False, decision.get("atom_promotion_authorized"), False),
        _check("source_plan_does_not_authorize_deployment", decision.get("deployment_authorized") is False, decision.get("deployment_authorized"), False),
        _check("source_plan_does_not_authorize_safety_claim", decision.get("safety_benefit_claim_authorized") is False, decision.get("safety_benefit_claim_authorized"), False),
        _check("source_plan_does_not_authorize_camp_over_dp_top1_claim", decision.get("camp_over_dp_top1_claim_authorized") is False, decision.get("camp_over_dp_top1_claim_authorized"), False),
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    contract = report["contract_summary"]
    return "\n".join(
        [
            "# V13 Static DP-Reward Non-Overlap Static Contract Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source plan status: `{contract['source_plan_status']}`",
            f"- Split manifest required: `{contract['split_manifest_required']}`",
            f"- Candidate tensor registry required: `{contract['candidate_tensor_hash_registry_required']}`",
            f"- Zero candidate tensor intersection required: `{contract['train_eval_candidate_tensor_intersection_must_be_zero']}`",
            f"- Training preflight authorized next: `{decision['training_preflight_authorized_next']}`",
            "",
            "This review is read-only. It does not run replay, generate candidates, train CAMP, modify DP, promote selectors or atoms, deploy, or make safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _expect_true(contract: dict[str, Any], key: str) -> dict[str, Any]:
    return _check(key, contract.get(key) is True, contract.get(key), True)


def _expect_value(contract: dict[str, Any], key: str, expected: Any) -> dict[str, Any]:
    return _check(key, contract.get(key) == expected, contract.get(key), expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _load_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
