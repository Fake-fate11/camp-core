#!/usr/bin/env python3
"""Plan implementation of the fixed-DP candidate-generation entrypoint remediation.

This plan-only gate consumes the passed entrypoint-remediation static contract
review and defines a future CAMP-owned runner/adapter contract. It does not
implement that runner, run Diffusion Planner, generate candidates, train CAMP,
modify DP, promote, deploy, or make safety/CAMP-over-DP claims.
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
SOURCE_SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "static_contract_review_v1"
)
SOURCE_PASS_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "static_contract_review_passed"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "implementation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "implementation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_"
    "implementation_plan_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_entrypoint_contract_remediation_static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "entrypoint_contract_remediation_implementation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "entrypoint_contract_remediation_implementation_static_contract_review_only"
)
FUTURE_RUNNER_SCRIPT = (
    "scripts/integrations/run_diffusion_planner_dp_camp_v13_fixed_candidate_generation.py"
)
FUTURE_RUNNER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_candidate_generation_runner.py"
)
FUTURE_IMPLEMENTATION_STATIC_REVIEW_SCRIPT = (
    "scripts/integrations/review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_"
    "entrypoint_contract_remediation_implementation_static_contract.py"
)
FUTURE_IMPLEMENTATION_STATIC_REVIEW_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_"
    "entrypoint_contract_remediation_implementation_static_contract.py"
)
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
)
RUNNER_CONTRACT_REQUIREMENTS = (
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
FUTURE_STATIC_REVIEW_REQUIREMENTS = (
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
SOURCE_DECISION_FALSE_FLAGS = (
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
REQUIRED_SOURCE_SCRIPT_SNIPPETS = (
    "entrypoint_contract_remediation_implementation_plan_authorized_next",
    "entrypoint_contract_remediation_implementation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "candidate_generation_by_camp_authorized",
    "FUTURE_IMPLEMENTATION_TARGET",
    "score_expression",
)
REQUIRED_SOURCE_TEST_SNIPPETS = (
    "entrypoint_contract_remediation_implementation_plan_authorized_next",
    "entrypoint_contract_remediation_implementation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "candidate_generation_by_camp_authorized",
    "AUTHORIZED_NEXT_WORK",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static_review_json", type=Path, required=True)
    parser.add_argument("--static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--static_review_script", type=Path, required=True)
    parser.add_argument("--static_review_test", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--dp_repo", type=Path, default=Path("/root/autodl-tmp/Diffusion-Planner"))
    parser.add_argument("--camp_repo", type=Path, default=Path("/root/autodl-tmp/camp_core"))
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        static_review_json=args.static_review_json,
        static_review_artifact_dir=args.static_review_artifact_dir,
        static_review_script=args.static_review_script,
        static_review_test=args.static_review_test,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        dp_repo=args.dp_repo,
        camp_repo=args.camp_repo,
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
    static_review_json: Path,
    static_review_artifact_dir: Path,
    static_review_script: Path,
    static_review_test: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    dp_repo: Path = Path("/root/autodl-tmp/Diffusion-Planner"),
    camp_repo: Path = Path("/root/autodl-tmp/camp_core"),
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    source_payload = _load_json_dict(static_review_json)
    source_decision = _dict(source_payload.get("final_decision"))
    source_review = _dict(source_payload.get("static_contract_review"))
    source_summary = _dict(source_payload.get("source_plan_summary"))
    source_script_text = _read_text(static_review_script)
    source_test_text = _read_text(static_review_test)
    audit_text = _read_text(v13_audit_md)
    plan = _implementation_plan(
        source_review=source_review,
        source_summary=source_summary,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
    )
    checks = _checks(
        static_review_json=static_review_json,
        static_review_artifact_dir=static_review_artifact_dir,
        static_review_script=static_review_script,
        static_review_test=static_review_test,
        v13_audit_md=v13_audit_md,
        source_payload=source_payload,
        source_decision=source_decision,
        source_review=source_review,
        source_summary=source_summary,
        source_script_text=source_script_text,
        source_test_text=source_test_text,
        audit_text=audit_text,
        plan=plan,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
            "implementation_execution": False,
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
        "source_static_review": {
            "path": str(static_review_json.resolve()),
            "artifact_dir": str(static_review_artifact_dir.resolve()),
            "schema_version": source_payload.get("schema_version"),
            "status": source_decision.get("status"),
            "passed": source_decision.get("passed"),
            "failed_checks": source_decision.get("failed_checks"),
            "json_sha256": _sha256(static_review_json),
        },
        "entrypoint_contract_remediation_implementation_plan": plan,
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def _implementation_plan(
    *,
    source_review: dict[str, Any],
    source_summary: dict[str, Any],
    dp_repo: Path,
    camp_repo: Path,
) -> dict[str, Any]:
    missing_entrypoint = str(source_summary.get("missing_entrypoint_path") or "")
    return {
        "implementation_performed_by_this_gate": False,
        "future_runner_script": FUTURE_RUNNER_SCRIPT,
        "future_runner_test": FUTURE_RUNNER_TEST,
        "future_implementation_static_review_script": FUTURE_IMPLEMENTATION_STATIC_REVIEW_SCRIPT,
        "future_implementation_static_review_test": FUTURE_IMPLEMENTATION_STATIC_REVIEW_TEST,
        "runner_owner_repo": "CAMP",
        "camp_repo": str(camp_repo),
        "dp_repo": str(dp_repo),
        "missing_dp_repo_entrypoint_path": missing_entrypoint,
        "missing_dp_repo_entrypoint_will_not_be_created": True,
        "dp_repo_modification_allowed": False,
        "dp_config_weight_checkpoint_change_allowed": False,
        "candidate_source": "fixed Diffusion Planner candidate tensor only",
        "required_dp_head": FIXED_DP_HEAD,
        "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
        "runner_contract_requirements": list(RUNNER_CONTRACT_REQUIREMENTS),
        "future_static_review_requirements": list(FUTURE_STATIC_REVIEW_REQUIREMENTS),
        "source_contract_groups": _list(source_review.get("required_contract_groups")),
        "acceptance_summary": {
            "camp_role": "CAMP remains a reranker/selector over fixed DP candidate tensors",
            "entrypoint_location": "future runner must live under scripts/integrations in CAMP",
            "dp_boundary": "Diffusion Planner checkout remains read-only at the required commit",
            "execution_boundary": "candidate generation remains unauthorized until a later preflight/execution gate",
            "training_boundary": "training remains unauthorized until generation and zero-overlap checks pass",
        },
    }


def _checks(
    *,
    static_review_json: Path,
    static_review_artifact_dir: Path,
    static_review_script: Path,
    static_review_test: Path,
    v13_audit_md: Path,
    source_payload: dict[str, Any],
    source_decision: dict[str, Any],
    source_review: dict[str, Any],
    source_summary: dict[str, Any],
    source_script_text: str,
    source_test_text: str,
    audit_text: str,
    plan: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    dp_repo: Path,
    camp_repo: Path,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add = checks.append
    add(_expect("static_review_json_exists", static_review_json.exists(), True))
    add(_expect("static_review_artifact_dir_exists", static_review_artifact_dir.exists(), True))
    add(_expect("static_review_script_exists", static_review_script.exists(), True))
    add(_expect("static_review_test_exists", static_review_test.exists(), True))
    add(_expect("v13_audit_exists", v13_audit_md.exists(), True))
    add(_expect("source_schema_version", source_payload.get("schema_version"), SOURCE_SCHEMA_VERSION))
    add(_expect("source_status", source_decision.get("status"), SOURCE_PASS_STATUS))
    add(_expect("source_passed", source_decision.get("passed"), True))
    add(_expect("source_failed_checks_empty", source_decision.get("failed_checks"), []))
    add(_expect("source_authorized_next_work", source_decision.get("authorized_next_work"), authorized_current_work))
    add(
        _expect(
            "source_authorizes_implementation_plan",
            source_decision.get("entrypoint_contract_remediation_implementation_plan_authorized_next"),
            True,
        )
    )
    for flag in SOURCE_DECISION_FALSE_FLAGS:
        add(_expect(f"source_forbids_{flag}", source_decision.get(flag), False))
    add(_expect("source_candidate_operation", source_decision.get("candidate_operation"), "fixed DP candidate reranking only"))
    add(_expect("source_score_expression", source_decision.get("score_expression"), SCORE_EXPRESSION))
    add(_expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main))
    add(_expect("current_dp_head_fixed", current_dp_head, required_dp_head))
    add(_expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD))
    add(_expect("camp_repo_exists", camp_repo.is_dir(), True))
    add(_expect("dp_repo_exists", dp_repo.is_dir(), True))
    add(_expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS))
    add(_expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work))
    add(
        _expect(
            "audit_authorizes_implementation_plan",
            _latest_value(audit_text, "entrypoint_contract_remediation_implementation_plan_authorized_next"),
            "True",
        )
    )
    for flag in AUDIT_FALSE_FLAGS:
        add(_expect(f"audit_forbids_{flag}", _latest_value(audit_text, flag), "False"))
    missing_entrypoint = str(source_summary.get("missing_entrypoint_path") or "")
    add(_expect("source_missing_entrypoint_path_nonempty", bool(missing_entrypoint), True))
    add(_expect("source_future_implementation_target", source_summary.get("future_implementation_target"), FUTURE_RUNNER_SCRIPT))
    add(_expect("source_missing_entrypoint_path_under_dp_repo", missing_entrypoint.startswith(str(dp_repo)), True))
    add(_expect("source_missing_dp_entrypoint_still_missing", Path(missing_entrypoint).exists(), False))
    source_zero_keys = set(_list(source_summary.get("required_zero_overlap_keys")))
    plan_zero_keys = set(_list(plan.get("required_zero_overlap_keys")))
    for key in ZERO_OVERLAP_KEYS:
        add(_expect(f"source_requires_zero_overlap_{key}", key in source_zero_keys, True))
        add(_expect(f"plan_requires_zero_overlap_{key}", key in plan_zero_keys, True))
    entrypoint_contract = _dict(source_review.get("entrypoint_contract"))
    add(_expect("source_entrypoint_scope_camp_owned", entrypoint_contract.get("remediation_scope"), "CAMP-owned entrypoint contract only"))
    add(_expect("source_entrypoint_dp_modification_forbidden", entrypoint_contract.get("dp_repo_modification_allowed"), False))
    add(_expect("plan_future_runner_script", plan.get("future_runner_script"), FUTURE_RUNNER_SCRIPT))
    add(_expect("plan_runner_owner_repo", plan.get("runner_owner_repo"), "CAMP"))
    add(_expect("plan_missing_dp_entrypoint_will_not_be_created", plan.get("missing_dp_repo_entrypoint_will_not_be_created"), True))
    add(_expect("plan_forbids_dp_modification", plan.get("dp_repo_modification_allowed"), False))
    add(_expect("plan_forbids_dp_config_weight_checkpoint_change", plan.get("dp_config_weight_checkpoint_change_allowed"), False))
    add(_expect("plan_implementation_not_performed", plan.get("implementation_performed_by_this_gate"), False))
    required = set(_list(plan.get("runner_contract_requirements")))
    for item in RUNNER_CONTRACT_REQUIREMENTS:
        add(_expect(f"plan_requires_{_slug(item)}", item in required, True))
    future_review = set(_list(plan.get("future_static_review_requirements")))
    for item in FUTURE_STATIC_REVIEW_REQUIREMENTS:
        add(_expect(f"plan_future_review_requires_{_slug(item)}", item in future_review, True))
    for snippet in REQUIRED_SOURCE_SCRIPT_SNIPPETS:
        add(_expect(f"source_script_contains_{_slug(snippet)}", snippet in source_script_text, True))
    for snippet in REQUIRED_SOURCE_TEST_SNIPPETS:
        add(_expect(f"source_test_contains_{_slug(snippet)}", snippet in source_test_text, True))
    return checks


def _decision(
    *,
    passed: bool,
    failed: list[str],
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "entrypoint_contract_remediation_implementation_plan_ready": passed,
        "entrypoint_contract_remediation_implementation_static_contract_review_authorized_next": passed,
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


def render_markdown(report: dict[str, Any]) -> str:
    decision = _dict(report.get("final_decision"))
    plan = _dict(report.get("entrypoint_contract_remediation_implementation_plan"))
    failed = decision.get("failed_checks") or []
    return "\n".join(
        [
            "# Fixed-DP Candidate Generation Entrypoint Remediation Implementation Plan",
            "",
            f"- Status: `{decision.get('status')}`",
            f"- Passed: `{decision.get('passed')}`",
            f"- Failed checks: `{failed}`",
            f"- Authorized next work: `{decision.get('authorized_next_work')}`",
            f"- Implementation performed by this gate: `{plan.get('implementation_performed_by_this_gate')}`",
            f"- Future runner script: `{plan.get('future_runner_script')}`",
            f"- Future static review script: `{plan.get('future_implementation_static_review_script')}`",
            f"- Missing DP entrypoint will be created: `{not plan.get('missing_dp_repo_entrypoint_will_not_be_created')}`",
            f"- Fixed-DP generation execution authorized: `{decision.get('fixed_dp_candidate_generation_execution_authorized_next')}`",
            f"- CAMP candidate generation authorized: `{decision.get('candidate_generation_by_camp_authorized')}`",
            f"- Training preflight authorized next: `{decision.get('training_preflight_authorized_next')}`",
            f"- DP modification authorized: `{decision.get('dp_modification_authorized')}`",
            f"- Candidate operation: `{decision.get('candidate_operation')}`",
            f"- Score expression: `{decision.get('score_expression')}`",
            "",
        ]
    )


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


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": actual == expected, "actual": actual, "expected": expected}


def _latest_value(text: str, key: str) -> str | None:
    token = f"{key}="
    if token not in text:
        return None
    return text.rsplit(token, maxsplit=1)[1].splitlines()[0].strip()


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
