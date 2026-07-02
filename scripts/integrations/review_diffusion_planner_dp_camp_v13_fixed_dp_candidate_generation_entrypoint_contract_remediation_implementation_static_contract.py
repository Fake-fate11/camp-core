#!/usr/bin/env python3
"""Review the entrypoint-remediation implementation plan static contract.

This read-only gate consumes the implementation-plan artifact for the
CAMP-owned fixed-DP candidate-generation runner. It can authorize only the
future code implementation gate; it does not implement the runner, execute
candidate generation, train CAMP, modify DP, promote, deploy, or make claims.
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
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "implementation_plan_v1"
)
PLAN_READY_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "implementation_plan_ready"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "implementation_static_contract_review_v1"
)
PASS_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "implementation_static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "implementation_static_contract_review_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_entrypoint_contract_remediation_implementation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "entrypoint_contract_remediation_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "entrypoint_contract_remediation_implementation_only"
)
FUTURE_RUNNER_SCRIPT = (
    "scripts/integrations/run_diffusion_planner_dp_camp_v13_fixed_candidate_generation.py"
)
FUTURE_RUNNER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_candidate_generation_runner.py"
)
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
)
REQUIRED_RUNNER_CONTRACT_REQUIREMENTS = (
    "runner_lives_in_camp_repo_not_diffusion_planner_repo",
    "runner_requires_fixed_dp_head_before_any_future_execution",
    "runner_refuses_if_dp_config_weights_checkpoint_or_source_dirty",
    "runner_invokes_only_existing_fixed_diffusion_planner_candidate_generation_path",
    "runner_materializes_fixed_dp_candidate_tensor_without_camp_modification",
    "runner_records_candidate_tensor_hash_path_signature_record_identity_and_split_root",
    "runner_excludes_full36_and_formal_seeds_11_12_13",
    "runner_forbids_reference_blend_guidance_postprocess_and_postselection",
    "runner_forbids_closed_loop_outcomes_as_training_or_online_inputs",
    "runner_preserves_affine_score_and_nonnegative_simplex_contracts",
    "runner_writes_zero_overlap_inputs_for_future_preflight",
    "runner_requires_explicit_execution_guard_env_before_future_execution",
)
REQUIRED_FUTURE_STATIC_REVIEW_REQUIREMENTS = (
    "reject_if_runner_path_is_in_diffusion_planner_repo",
    "reject_if_runner_can_modify_dp_code_config_weights_or_checkpoints",
    "reject_if_runner_can_generate_repair_rewrite_or_blend_trajectories_with_camp",
    "reject_if_runner_omits_candidate_tensor_hash_registry",
    "reject_if_runner_omits_path_signature_registry",
    "reject_if_runner_omits_record_identity_registry",
    "reject_if_runner_omits_split_manifest_root_registry",
    "reject_if_runner_allows_full36_or_formal_seeds_11_12_13",
    "reject_if_training_data_preparation_promotion_or_deployment_is_authorized",
    "reject_if_score_is_not_affine_or_weights_are_not_nonnegative_simplex",
)
PLAN_DECISION_FALSE_FLAGS = (
    "entrypoint_contract_remediation_implementation_authorized_next",
    "fixed_dp_candidate_generation_preflight_authorized_next",
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
AUDIT_FALSE_FLAGS = (
    "entrypoint_contract_remediation_implementation_authorized_next",
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
    "FUTURE_RUNNER_SCRIPT",
    "entrypoint_contract_remediation_implementation_static_contract_review_authorized_next",
    "entrypoint_contract_remediation_implementation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "candidate_generation_by_camp_authorized",
)
REQUIRED_PLAN_TEST_SNIPPETS = (
    "AUTHORIZED_NEXT_WORK",
    "entrypoint_contract_remediation_implementation_static_contract_review_authorized_next",
    "entrypoint_contract_remediation_implementation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "candidate_generation_by_camp_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation_plan_json", type=Path, required=True)
    parser.add_argument("--implementation_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--implementation_plan_script", type=Path, required=True)
    parser.add_argument("--implementation_plan_test", type=Path, required=True)
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
        implementation_plan_json=args.implementation_plan_json,
        implementation_plan_artifact_dir=args.implementation_plan_artifact_dir,
        implementation_plan_script=args.implementation_plan_script,
        implementation_plan_test=args.implementation_plan_test,
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
    implementation_plan_json: Path,
    implementation_plan_artifact_dir: Path,
    implementation_plan_script: Path,
    implementation_plan_test: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    plan_payload = _load_json_dict(implementation_plan_json)
    decision = _dict(plan_payload.get("final_decision"))
    plan = _dict(plan_payload.get("entrypoint_contract_remediation_implementation_plan"))
    script_text = _read_text(implementation_plan_script)
    test_text = _read_text(implementation_plan_test)
    audit_text = _read_text(v13_audit_md)
    review = _static_contract_review(plan)
    checks = _checks(
        implementation_plan_json=implementation_plan_json,
        implementation_plan_artifact_dir=implementation_plan_artifact_dir,
        implementation_plan_script=implementation_plan_script,
        implementation_plan_test=implementation_plan_test,
        v13_audit_md=v13_audit_md,
        plan_payload=plan_payload,
        decision=decision,
        plan=plan,
        review=review,
        script_text=script_text,
        test_text=test_text,
        audit_text=audit_text,
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
            "implementation_authorized_next": passed,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "data_preparation_execution": False,
            "training_preflight": False,
            "training_execution": False,
            "dp_modification": False,
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
        "source_implementation_plan": {
            "path": str(implementation_plan_json.resolve()),
            "artifact_dir": str(implementation_plan_artifact_dir.resolve()),
            "schema_version": plan_payload.get("schema_version"),
            "status": decision.get("status"),
            "passed": decision.get("passed"),
            "json_sha256": _sha256(implementation_plan_json),
        },
        "implementation_static_contract_review": review,
        "review_checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def _static_contract_review(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "required_contract_groups": [
            "camp_owned_runner_location_contract",
            "fixed_dp_read_only_contract",
            "fixed_candidate_tensor_only_contract",
            "zero_overlap_registry_contract",
            "forbidden_generation_and_postprocess_contract",
            "affine_score_and_simplex_math_contract",
            "no_execution_or_training_authorization_contract",
        ],
        "runner_contract": {
            "future_runner_script": plan.get("future_runner_script"),
            "future_runner_test": plan.get("future_runner_test"),
            "runner_owner_repo": plan.get("runner_owner_repo"),
            "missing_dp_repo_entrypoint_will_not_be_created": plan.get(
                "missing_dp_repo_entrypoint_will_not_be_created"
            ),
            "dp_repo_modification_allowed": plan.get("dp_repo_modification_allowed"),
            "dp_config_weight_checkpoint_change_allowed": plan.get(
                "dp_config_weight_checkpoint_change_allowed"
            ),
            "required_dp_head": plan.get("required_dp_head"),
            "candidate_source": plan.get("candidate_source"),
        },
        "zero_overlap_contract": {
            key: key in set(_list(plan.get("required_zero_overlap_keys")))
            for key in ZERO_OVERLAP_KEYS
        },
        "runner_requirements_present": {
            item: item in set(_list(plan.get("runner_contract_requirements")))
            for item in REQUIRED_RUNNER_CONTRACT_REQUIREMENTS
        },
        "future_review_requirements_present": {
            item: item in set(_list(plan.get("future_static_review_requirements")))
            for item in REQUIRED_FUTURE_STATIC_REVIEW_REQUIREMENTS
        },
        "math_boundary": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "score_is_affine": True,
        },
    }


def _checks(
    *,
    implementation_plan_json: Path,
    implementation_plan_artifact_dir: Path,
    implementation_plan_script: Path,
    implementation_plan_test: Path,
    v13_audit_md: Path,
    plan_payload: dict[str, Any],
    decision: dict[str, Any],
    plan: dict[str, Any],
    review: dict[str, Any],
    script_text: str,
    test_text: str,
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = [
        _check("implementation_plan_json_exists", implementation_plan_json.exists(), str(implementation_plan_json)),
        _check("implementation_plan_artifact_dir_exists", implementation_plan_artifact_dir.exists(), str(implementation_plan_artifact_dir)),
        _check("implementation_plan_script_exists", implementation_plan_script.exists(), str(implementation_plan_script)),
        _check("implementation_plan_test_exists", implementation_plan_test.exists(), str(implementation_plan_test)),
        _check("v13_audit_exists", v13_audit_md.exists(), str(v13_audit_md)),
        _check("plan_schema_version_expected", plan_payload.get("schema_version") == PLAN_SCHEMA_VERSION),
        _check("plan_status_ready", decision.get("status") == PLAN_READY_STATUS),
        _check("plan_passed", decision.get("passed") is True),
        _check("plan_failed_checks_empty", decision.get("failed_checks") == []),
        _check("plan_authorizes_this_static_review", decision.get("authorized_next_work") == authorized_current_work),
        _check(
            "plan_static_review_authorized_next",
            decision.get("entrypoint_contract_remediation_implementation_static_contract_review_authorized_next")
            is True,
        ),
        _check("camp_head_matches_origin", current_camp_head == current_camp_origin_main),
        _check("dp_head_fixed", current_dp_head == required_dp_head == FIXED_DP_HEAD),
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
            _latest_value(audit_text, "entrypoint_contract_remediation_implementation_static_contract_review_authorized_next")
            == "True",
        ),
        _check("runner_script_expected", plan.get("future_runner_script") == FUTURE_RUNNER_SCRIPT),
        _check("runner_test_expected", plan.get("future_runner_test") == FUTURE_RUNNER_TEST),
        _check("runner_owner_camp", plan.get("runner_owner_repo") == "CAMP"),
        _check("runner_not_in_dp_repo", not str(plan.get("future_runner_script", "")).startswith("/root/autodl-tmp/Diffusion-Planner")),
        _check("dp_entrypoint_not_created_by_plan", plan.get("missing_dp_repo_entrypoint_will_not_be_created") is True),
        _check("dp_modification_forbidden_by_plan", plan.get("dp_repo_modification_allowed") is False),
        _check(
            "dp_config_weight_checkpoint_change_forbidden_by_plan",
            plan.get("dp_config_weight_checkpoint_change_allowed") is False,
        ),
        _check("plan_implementation_not_performed", plan.get("implementation_performed_by_this_gate") is False),
        _check("plan_required_dp_head_fixed", plan.get("required_dp_head") == FIXED_DP_HEAD),
        _check(
            "plan_candidate_source_fixed_dp_only",
            plan.get("candidate_source") == "fixed Diffusion Planner candidate tensor only",
        ),
        _check("zero_overlap_contract_complete", all(review["zero_overlap_contract"].values()), review["zero_overlap_contract"]),
        _check(
            "runner_requirements_complete",
            all(review["runner_requirements_present"].values()),
            review["runner_requirements_present"],
        ),
        _check(
            "future_static_review_requirements_complete",
            all(review["future_review_requirements_present"].values()),
            review["future_review_requirements_present"],
        ),
    ]
    for flag in PLAN_DECISION_FALSE_FLAGS:
        checks.append(_check(f"plan_forbids_{flag}", decision.get(flag) is False, decision.get(flag)))
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_check(f"audit_forbids_{flag}", _latest_value(audit_text, flag) == "False"))
    for snippet in REQUIRED_PLAN_SCRIPT_SNIPPETS:
        checks.append(_check(f"plan_script_contains_{_slug(snippet)}", snippet in script_text))
    for snippet in REQUIRED_PLAN_TEST_SNIPPETS:
        checks.append(_check(f"plan_test_contains_{_slug(snippet)}", snippet in test_text))
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
        "entrypoint_contract_remediation_implementation_static_contract_review_passed": passed,
        "entrypoint_contract_remediation_implementation_authorized_next": passed,
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


def render_markdown(report: dict[str, Any]) -> str:
    decision = _dict(report["final_decision"])
    runner = _dict(_dict(report["implementation_static_contract_review"]).get("runner_contract"))
    lines = [
        "# Entrypoint Remediation Implementation Static Contract Review",
        "",
        f"- schema_version: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failed_checks: `{decision['failed_checks']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- future_runner_script: `{runner.get('future_runner_script')}`",
        f"- runner_owner_repo: `{runner.get('runner_owner_repo')}`",
        f"- fixed_dp_generation_execution_authorized: `{decision['fixed_dp_candidate_generation_execution_authorized_next']}`",
        f"- training_preflight_authorized: `{decision['training_preflight_authorized_next']}`",
        f"- dp_modification_authorized: `{decision['dp_modification_authorized']}`",
        f"- candidate_operation: `{decision['candidate_operation']}`",
        f"- score_expression: `{decision['score_expression']}`",
        "",
    ]
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
