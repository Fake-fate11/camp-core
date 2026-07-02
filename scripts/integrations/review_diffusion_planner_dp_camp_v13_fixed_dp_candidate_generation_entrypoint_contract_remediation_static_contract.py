#!/usr/bin/env python3
"""Review the fixed-DP candidate-generation entrypoint remediation contract.

This is a read-only static review gate. It consumes the entrypoint remediation
plan artifact and verifies that the next step is only a CAMP-owned
implementation plan for the missing fixed-DP candidate-generation entrypoint.
It does not run Diffusion Planner, generate candidates, train CAMP, modify DP,
promote, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
PLAN_SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_plan_v1"
)
PLAN_READY_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_plan_ready"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "static_contract_review_v1"
)
PASS_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "static_contract_review_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_entrypoint_contract_remediation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "entrypoint_contract_remediation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "entrypoint_contract_remediation_implementation_plan_only"
)
STATIC_REVIEW_SCRIPT = (
    "scripts/integrations/review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_"
    "entrypoint_contract_remediation_static_contract.py"
)
STATIC_REVIEW_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_"
    "entrypoint_contract_remediation_static_contract.py"
)
FUTURE_IMPLEMENTATION_TARGET = (
    "scripts/integrations/run_diffusion_planner_dp_camp_v13_fixed_candidate_generation.py"
)
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
)
REQUIRED_CONTRACT_CHANGES = (
    "replace_dp_repo_tools_entrypoint_with_camp_owned_adapter",
    "keep_diffusion_planner_checkout_read_only_at_required_commit",
    "fail_if_required_dp_head_or_candidate_count_drifts",
    "emit_fixed_dp_candidate_tensor_registries_for_zero_overlap",
    "preserve_guard_env_before_any_future_execution",
    "forbid_camp_trajectory_generation_repair_rewrite_or_blend",
    "forbid_reference_blend_guidance_postprocess_and_postselection",
    "forbid_closed_loop_outcomes_full36_and_formal_seeds",
    "keep_score_affine_and_simplex_contracts_unchanged",
)
PLAN_DECISION_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "fixed_dp_candidate_generation_executed",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "data_preparation_authorized_next",
    "replay_execution_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "dp_modification_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
ANALYSIS_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_execution",
    "candidate_generation_by_camp",
    "trajectory_generation_by_camp",
    "trajectory_modification_by_camp",
    "reference_blend",
    "guidance",
    "postprocess_or_postselection",
    "closed_loop_outcome_input",
    "data_preparation_execution",
    "replay_execution",
    "training_preflight",
    "training_execution",
    "dp_modification",
    "selector_promotion",
    "atom_promotion",
    "deployment",
    "safety_benefit_claim",
    "camp_over_dp_top1_claim",
)
AUDIT_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_execution_preflight_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "fixed_dp_candidate_generation_executed",
    "fresh_member_source_materialization_execution_authorized_next",
    "fresh_evaluation_split_evaluation_execution_authorized_next",
    "fresh_evaluation_split_evaluation_result_review_authorized_next",
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_by_current_boundary",
    "runtime_shadow_selector_execution_authorized",
    "replay_execution_authorized_by_current_boundary",
    "fixed_dp_candidate_generation_authorized_by_current_boundary",
    "candidate_generation_by_camp_authorized_by_current_boundary",
    "trajectory_generation_by_camp_authorized_by_current_boundary",
    "trajectory_modification_by_camp_authorized_by_current_boundary",
    "dp_modification_authorized_by_current_boundary",
    "formal_seed_11_12_13_execution_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
REQUIRED_PLAN_SCRIPT_SNIPPETS = (
    "FUTURE_STATIC_REVIEW_SCRIPT",
    "entrypoint_contract_remediation_static_contract.py",
    FUTURE_IMPLEMENTATION_TARGET,
    "entrypoint_contract_remediation_static_contract_review_authorized_next",
)
REQUIRED_PLAN_TEST_SNIPPETS = (
    "test_entrypoint_contract_remediation_plan_authorizes_static_review_only",
    "entrypoint_contract_remediation_static_contract_review_authorized_next",
    "FUTURE_IMPLEMENTATION_TARGET",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan_json", type=Path, required=True)
    parser.add_argument("--plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--plan_script", type=Path, required=True)
    parser.add_argument("--plan_test", type=Path, required=True)
    parser.add_argument("--static_review_script", type=Path, required=True)
    parser.add_argument("--static_review_test", type=Path, required=True)
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
        plan_json=args.plan_json,
        plan_artifact_dir=args.plan_artifact_dir,
        plan_script=args.plan_script,
        plan_test=args.plan_test,
        static_review_script=args.static_review_script,
        static_review_test=args.static_review_test,
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
    plan_json: Path,
    plan_artifact_dir: Path,
    plan_script: Path,
    plan_test: Path,
    static_review_script: Path,
    static_review_test: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    plan_payload = _load_json_dict(plan_json)
    plan_script_text = _read_text(plan_script)
    plan_test_text = _read_text(plan_test)
    static_review_script_text = _read_text(static_review_script)
    static_review_test_text = _read_text(static_review_test)
    audit_text = _read_text(v13_audit_md)
    review = _static_contract_review(plan_payload)
    checks = _checks(
        plan_json=plan_json,
        plan_artifact_dir=plan_artifact_dir,
        plan_script=plan_script,
        plan_test=plan_test,
        static_review_script=static_review_script,
        static_review_test=static_review_test,
        v13_audit_md=v13_audit_md,
        plan_payload=plan_payload,
        plan_script_text=plan_script_text,
        plan_test_text=plan_test_text,
        static_review_script_text=static_review_script_text,
        static_review_test_text=static_review_test_text,
        audit_text=audit_text,
        review=review,
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
            "static_contract_review_only": True,
            "read_only_inputs": True,
            "implementation_plan_authorized_next": passed,
            "implementation_authorized_next": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "data_preparation_execution": False,
            "replay_execution": False,
            "training_preflight": False,
            "training_execution": False,
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
            "plan_json": str(plan_json.resolve()),
            "plan_artifact_dir": str(plan_artifact_dir.resolve()),
            "plan_script": str(plan_script.resolve()),
            "plan_test": str(plan_test.resolve()),
            "static_review_script": str(static_review_script.resolve()),
            "static_review_test": str(static_review_test.resolve()),
            "v13_audit_md": str(v13_audit_md.resolve()),
            "plan_json_sha256": _sha256(plan_json),
            "plan_script_sha256": _sha256(plan_script),
            "plan_test_sha256": _sha256(plan_test),
            "static_review_script_sha256": _sha256(static_review_script),
            "static_review_test_sha256": _sha256(static_review_test),
        },
        "source_plan_summary": _plan_summary(plan_payload),
        "static_contract_review": review,
        "review_checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def _static_contract_review(plan_payload: dict[str, Any]) -> dict[str, Any]:
    plan = _dict(plan_payload.get("entrypoint_contract_remediation_plan"))
    decision = _dict(plan_payload.get("final_decision"))
    analysis = _dict(plan_payload.get("analysis"))
    return {
        "required_contract_groups": [
            "camp_owned_entrypoint_adapter_contract",
            "fixed_dp_read_only_contract",
            "zero_overlap_registry_contract",
            "fixed_candidate_tensor_only_contract",
            "forbidden_generation_and_postprocess_contract",
            "affine_score_and_simplex_math_contract",
            "no_action_authorization_beyond_next_implementation_plan_gate",
        ],
        "entrypoint_contract": {
            "remediation_scope": plan.get("remediation_scope"),
            "missing_entrypoint_path": plan.get("missing_entrypoint_path"),
            "future_static_review_script": plan.get("future_static_review_script"),
            "future_static_review_test": plan.get("future_static_review_test"),
            "future_implementation_target": plan.get("future_implementation_target"),
            "dp_repo_modification_allowed": plan.get("dp_repo_modification_allowed"),
            "dp_config_weight_checkpoint_change_allowed": plan.get(
                "dp_config_weight_checkpoint_change_allowed"
            ),
            "next_gate_is_static_review_only": plan.get("next_gate_is_static_review_only"),
            "execution_authorized_by_this_gate": plan.get("execution_authorized_by_this_gate"),
        },
        "zero_overlap_contract": {
            key: key in set(_list(plan.get("required_zero_overlap_keys")))
            for key in ZERO_OVERLAP_KEYS
        },
        "required_contract_changes_present": {
            name: name in set(_list(plan.get("required_contract_changes")))
            for name in REQUIRED_CONTRACT_CHANGES
        },
        "no_action_boundary": {
            name: decision.get(name) is False for name in PLAN_DECISION_FALSE_FLAGS
        },
        "analysis_boundary": {
            name: analysis.get(name) is False for name in ANALYSIS_FALSE_FLAGS
        },
        "math_boundary": {
            "candidate_operation": decision.get("candidate_operation"),
            "score_expression": decision.get("score_expression"),
            "score_is_affine": decision.get("score_expression") == SCORE_EXPRESSION,
        },
    }


def _checks(
    *,
    plan_json: Path,
    plan_artifact_dir: Path,
    plan_script: Path,
    plan_test: Path,
    static_review_script: Path,
    static_review_test: Path,
    v13_audit_md: Path,
    plan_payload: dict[str, Any],
    plan_script_text: str,
    plan_test_text: str,
    static_review_script_text: str,
    static_review_test_text: str,
    audit_text: str,
    review: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(plan_payload.get("final_decision"))
    analysis = _dict(plan_payload.get("analysis"))
    entrypoint = _dict(review.get("entrypoint_contract"))
    math_boundary = _dict(review.get("math_boundary"))
    checks: list[dict[str, Any]] = [
        _check("plan_json_exists", plan_json.exists(), str(plan_json)),
        _check("plan_artifact_dir_exists", plan_artifact_dir.exists(), str(plan_artifact_dir)),
        _check("plan_script_exists", plan_script.exists(), str(plan_script)),
        _check("plan_test_exists", plan_test.exists(), str(plan_test)),
        _check("static_review_script_exists", static_review_script.exists(), str(static_review_script)),
        _check("static_review_test_exists", static_review_test.exists(), str(static_review_test)),
        _check("v13_audit_exists", v13_audit_md.exists(), str(v13_audit_md)),
        _check("plan_schema_version_expected", plan_payload.get("schema_version") == PLAN_SCHEMA_VERSION),
        _check("plan_status_ready", decision.get("status") == PLAN_READY_STATUS),
        _check("plan_passed", decision.get("passed") is True),
        _check("plan_failed_checks_empty", decision.get("failed_checks") == []),
        _check("plan_authorizes_this_static_review", decision.get("authorized_next_work") == authorized_current_work),
        _check(
            "plan_static_review_authorized_next",
            decision.get("entrypoint_contract_remediation_static_contract_review_authorized_next")
            is True,
        ),
        _check("camp_head_matches_origin", current_camp_head == current_camp_origin_main),
        _check("dp_head_fixed", current_dp_head == required_dp_head == FIXED_DP_HEAD),
        _check("analysis_plan_only", analysis.get("plan_only") is True),
        _check(
            "analysis_candidate_operation_fixed",
            analysis.get("candidate_operation") == "fixed DP candidate reranking only",
        ),
        _check("analysis_score_expression_affine", analysis.get("score_expression") == SCORE_EXPRESSION),
        _check(
            "audit_latest_status_authorizes_static_review",
            _latest_value(audit_text, "current_v13_status") == LATEST_AUDIT_STATUS,
            _latest_value(audit_text, "current_v13_status"),
        ),
        _check(
            "audit_latest_target_authorizes_static_review",
            _latest_value(audit_text, "next_work_target") == authorized_current_work,
            _latest_value(audit_text, "next_work_target"),
        ),
        _check(
            "audit_static_review_authorized_next",
            _latest_value(audit_text, "entrypoint_contract_remediation_static_contract_review_authorized_next")
            == "True",
        ),
        _check("entrypoint_scope_camp_owned", entrypoint.get("remediation_scope") == "CAMP-owned entrypoint contract only"),
        _check("entrypoint_dp_repo_modification_forbidden", entrypoint.get("dp_repo_modification_allowed") is False),
        _check(
            "entrypoint_dp_config_weight_checkpoint_change_forbidden",
            entrypoint.get("dp_config_weight_checkpoint_change_allowed") is False,
        ),
        _check("entrypoint_static_review_script_matches", entrypoint.get("future_static_review_script") == STATIC_REVIEW_SCRIPT),
        _check("entrypoint_static_review_test_matches", entrypoint.get("future_static_review_test") == STATIC_REVIEW_TEST),
        _check(
            "entrypoint_future_implementation_target_matches",
            entrypoint.get("future_implementation_target") == FUTURE_IMPLEMENTATION_TARGET,
        ),
        _check("entrypoint_next_gate_was_static_review_only", entrypoint.get("next_gate_is_static_review_only") is True),
        _check("entrypoint_execution_not_authorized_by_plan", entrypoint.get("execution_authorized_by_this_gate") is False),
        _check("missing_dp_entrypoint_path_recorded", bool(entrypoint.get("missing_entrypoint_path"))),
        _check("missing_dp_entrypoint_still_missing", not Path(str(entrypoint.get("missing_entrypoint_path"))).exists()),
        _check("zero_overlap_keys_complete", all(review["zero_overlap_contract"].values()), review["zero_overlap_contract"]),
        _check(
            "required_contract_changes_complete",
            all(review["required_contract_changes_present"].values()),
            review["required_contract_changes_present"],
        ),
        _check("plan_no_action_boundary_false", all(review["no_action_boundary"].values()), review["no_action_boundary"]),
        _check(
            "analysis_no_action_boundary_false",
            all(review["analysis_boundary"].values()),
            review["analysis_boundary"],
        ),
        _check(
            "math_boundary_fixed_and_affine",
            math_boundary.get("candidate_operation") == "fixed DP candidate reranking only"
            and math_boundary.get("score_expression") == SCORE_EXPRESSION
            and math_boundary.get("score_is_affine") is True,
        ),
        _check("static_review_script_declares_pass_status", "PASS_STATUS" in static_review_script_text),
        _check("static_review_test_checks_next_gate", "AUTHORIZED_NEXT_WORK" in static_review_test_text),
    ]
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_check(f"audit_forbids_{flag}", _latest_value(audit_text, flag) == "False"))
    for snippet in REQUIRED_PLAN_SCRIPT_SNIPPETS:
        checks.append(_check(f"plan_script_contains_{_slug(snippet)}", snippet in plan_script_text))
    for snippet in REQUIRED_PLAN_TEST_SNIPPETS:
        checks.append(_check(f"plan_test_contains_{_slug(snippet)}", snippet in plan_test_text))
    return checks


def _decision(
    *,
    passed: bool,
    failed: list[str],
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": PASS_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "entrypoint_contract_remediation_static_contract_review_passed": passed,
        "entrypoint_contract_remediation_implementation_plan_authorized_next": passed,
        "entrypoint_contract_remediation_implementation_authorized_next": False,
        "fixed_dp_candidate_generation_preflight_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "fixed_dp_candidate_generation_execution_authorized_next": False,
        "fixed_dp_candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "data_preparation_authorized_next": False,
        "replay_execution_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def _plan_summary(plan_payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(plan_payload.get("final_decision"))
    plan = _dict(plan_payload.get("entrypoint_contract_remediation_plan"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "missing_entrypoint_path": plan.get("missing_entrypoint_path"),
        "remediation_scope": plan.get("remediation_scope"),
        "future_implementation_target": plan.get("future_implementation_target"),
        "required_zero_overlap_keys": plan.get("required_zero_overlap_keys"),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = _dict(report["final_decision"])
    summary = _dict(report["source_plan_summary"])
    checks = report["review_checks"]
    lines = [
        "# Fixed-DP Candidate Generation Entrypoint Contract Static Review",
        "",
        f"- schema_version: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failed_checks: `{decision['failed_checks']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- source_plan_status: `{summary['status']}`",
        f"- missing_entrypoint_path: `{summary['missing_entrypoint_path']}`",
        f"- remediation_scope: `{summary['remediation_scope']}`",
        f"- future_implementation_target: `{summary['future_implementation_target']}`",
        f"- fixed_dp_generation_executed: `{decision['fixed_dp_candidate_generation_executed']}`",
        f"- fixed_dp_generation_authorized: `{decision['fixed_dp_candidate_generation_execution_authorized_next']}`",
        f"- dp_modification_authorized: `{decision['dp_modification_authorized']}`",
        f"- training_preflight_authorized: `{decision['training_preflight_authorized_next']}`",
        f"- candidate_operation: `{decision['candidate_operation']}`",
        f"- score_expression: `{decision['score_expression']}`",
        "",
        "## Checks",
        "",
    ]
    lines.extend(
        f"- {check['name']}: {check['passed']}"
        + (f" ({check['detail']})" if check.get("detail") is not None else "")
        for check in checks
    )
    lines.append("")
    return "\n".join(lines)


def _load_json_dict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object at {path}")
    return payload


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _check(name: str, passed: bool, detail: Any | None = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")[:80]


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
