#!/usr/bin/env python3
"""Plan implementation of v13 fresh member-source materialization.

This gate consumes the passed materialization static-contract review and plans
the future implementation contract. It does not implement the materializer,
materialize inputs, run the member-source builder, select fresh members, run DP,
generate fixed-DP candidates, replay, prepare data, train CAMP, modify DP,
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
SOURCE_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "static_contract_review_v1"
)
SOURCE_REVIEW_PASS_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "static_contract_review_passed"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "implementation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "implementation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "implementation_plan_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "materialization_implementation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "materialization_implementation_static_contract_review_only"
)
EXPECTED_FUTURE_MATERIALIZER_SCRIPT = (
    "scripts/integrations/materialize_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source_inputs.py"
)
EXPECTED_FUTURE_MATERIALIZER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source_materializer.py"
)
REQUIRED_SOURCE_INPUTS = (
    "candidate_member_source_manifest_json",
    "training_candidate_tensor_hash_registry_json",
    "training_path_signature_registry_json",
    "training_record_identity_registry_json",
    "training_split_manifest_root_registry_json",
    "recovered_prior_registry_manifest_json",
    "rejected_overlap_source_registry_manifest_json",
)
FUTURE_OUTPUTS = (
    "fresh_evaluation_split_member_source_manifest.json",
    "fresh_evaluation_split_member_source_nonoverlap_report.json",
    "fresh_evaluation_split_member_source_preflight_inputs.json",
    "SHA256SUMS.txt",
)
ZERO_INTERSECTION_KEYS = (
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
REQUIRED_FUTURE_BEHAVIOR = (
    "load_candidate_member_source_manifest_before_selection",
    "load_training_candidate_tensor_hash_registry_before_selection",
    "load_training_path_signature_registry_before_selection",
    "load_training_record_identity_registry_before_selection",
    "load_training_split_manifest_root_registry_before_selection",
    "load_recovered_prior_registry_before_selection",
    "load_rejected_overlap_source_registry_before_selection",
    "fail_closed_when_any_required_input_is_missing_empty_or_unreadable",
    "exclude_rejected_overlap_source_members",
    "exclude_formal_seeds_11_12_13_and_full36",
    "prove_zero_candidate_tensor_hash_intersection",
    "prove_zero_path_signature_intersection",
    "prove_zero_record_identity_intersection",
    "prove_zero_split_manifest_root_intersection",
    "reject_split_root_only_acceptance",
    "write_fresh_member_source_manifest_nonoverlap_report_preflight_inputs_and_sha256sums",
    "preserve_default_off_shadow_selector_and_executed_dp_top1",
    "forbid_camp_candidate_generation_or_trajectory_modification",
    "forbid_dp_code_config_or_weight_changes",
)
FUTURE_STATIC_REVIEW_REQUIREMENTS = (
    "reject_if_implementation_code_is_included_in_plan_gate",
    "reject_if_any_required_input_or_registry_can_be_optional",
    "reject_if_missing_empty_or_unreadable_inputs_do_not_fail_closed",
    "reject_if_any_zero_intersection_check_is_missing_or_nonfatal",
    "reject_if_split_root_zero_alone_can_pass",
    "reject_if_rejected_overlap_source_can_be_reused_or_relabelled",
    "reject_if_formal_seeds_11_12_13_or_full36_can_enter_member_source",
    "reject_if_future_outputs_lack_sha256_manifest",
    "reject_if_dp_or_fixed_dp_candidate_generation_can_run",
    "reject_if_replay_training_data_preparation_or_training_is_authorized",
    "reject_if_score_is_not_affine_or_weights_are_not_nonnegative_simplex",
    "reject_if_dp_modification_promotion_deployment_or_safety_claims_are_authorized",
)
BLOCKED_SOURCE_FLAGS = (
    "materialization_execution_authorized_next",
    "member_source_builder_execution_authorized_next",
    "fresh_member_selection_execution_authorized_next",
    "fresh_evaluation_split_evaluation_authorized_next",
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "replay_execution_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "candidate_generation_by_camp_authorized",
    "dp_modification_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
AUDIT_BLOCKED_FLAGS = (
    "materialization_execution_authorized_next",
    "member_source_builder_execution_authorized_next",
    "fresh_member_selection_execution_authorized_next",
    "fresh_evaluation_split_evaluation_authorized_next",
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
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
REQUIRED_REVIEW_SCRIPT_TERMS = (
    "all_required_source_inputs_listed",
    "all_future_outputs_listed",
    "all_zero_intersections_required",
    "split_root_zero_alone_insufficient",
    "materialization_implementation_plan_only",
)
REQUIRED_REVIEW_TEST_TERMS = (
    "rejects_wrong_audit_target",
    "rejects_action_leak",
    "rejects_missing_contracts",
    "rejects_root_only_acceptance",
    "rejects_dp_head_drift",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan implementation of the v13 fresh member-source materializer."
    )
    parser.add_argument("--materialization_static_review_json", type=Path, required=True)
    parser.add_argument("--materialization_static_review_script_py", type=Path, required=True)
    parser.add_argument("--materialization_static_review_test_py", type=Path, required=True)
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
        materialization_static_review_json=args.materialization_static_review_json,
        materialization_static_review_script_py=args.materialization_static_review_script_py,
        materialization_static_review_test_py=args.materialization_static_review_test_py,
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
    materialization_static_review_json: Path,
    materialization_static_review_script_py: Path,
    materialization_static_review_test_py: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    review_path = materialization_static_review_json.resolve()
    script_path = materialization_static_review_script_py.resolve()
    test_path = materialization_static_review_test_py.resolve()
    audit_path = v13_audit_md.resolve()
    source_review = _load_json_dict(review_path)
    script_text = _read_text(script_path)
    test_text = _read_text(test_path)
    audit_text = _read_text(audit_path)
    plan = _implementation_plan(source_review)
    checks = _checks(
        review_path=review_path,
        script_path=script_path,
        test_path=test_path,
        audit_path=audit_path,
        audit_text=audit_text,
        source_review=source_review,
        plan=plan,
        script_text=script_text,
        test_text=test_text,
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
            "plan_only": True,
            "implementation_execution": False,
            "materialization_execution": False,
            "member_source_builder_execution": False,
            "fresh_member_selection_execution": False,
            "evaluation_execution": False,
            "data_preparation_execution": False,
            "training_preflight": False,
            "training_execution": False,
            "replay_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "dp_modification": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "deployable_checkpoint_claim": False,
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
            "materialization_static_review_json": str(review_path),
            "materialization_static_review_script_py": str(script_path),
            "materialization_static_review_test_py": str(test_path),
            "v13_audit_md": str(audit_path),
        },
        "source_hashes": {
            "materialization_static_review_json_sha256": _sha256(review_path),
            "materialization_static_review_script_py_sha256": _sha256(script_path),
            "materialization_static_review_test_py_sha256": _sha256(test_path),
            "v13_audit_md_sha256": _sha256(audit_path),
        },
        "source_review_summary": _source_review_summary(source_review),
        "implementation_plan": plan,
        "plan_checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["implementation_plan"]
    lines = [
        "# V13 Fresh Member-Source Materialization Implementation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation execution authorized: `{decision['implementation_execution_authorized_next']}`",
        f"- Materialization execution authorized: `{decision['materialization_execution_authorized_next']}`",
        f"- Fixed-DP candidate generation authorized: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
        f"- Future materializer script: `{plan['future_materializer_script']}`",
        f"- Future materializer test: `{plan['future_materializer_test']}`",
        "",
        "## Required Future Behavior",
        "",
    ]
    for item in plan["required_future_materializer_behavior"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This implementation plan does not implement or execute the "
            "materializer. It authorizes only a static contract review of this "
            "plan before any code implementation gate.",
            "",
        ]
    )
    return "\n".join(lines)


def _implementation_plan(source_review: dict[str, Any]) -> dict[str, Any]:
    review = _dict(source_review.get("static_contract_review"))
    return {
        "implementation_performed_by_this_gate": False,
        "materialization_performed_by_this_gate": False,
        "future_materializer_script": review.get(
            "future_materializer_script", EXPECTED_FUTURE_MATERIALIZER_SCRIPT
        ),
        "future_materializer_test": review.get(
            "future_materializer_test", EXPECTED_FUTURE_MATERIALIZER_TEST
        ),
        "required_source_inputs": list(REQUIRED_SOURCE_INPUTS),
        "future_outputs": list(FUTURE_OUTPUTS),
        "required_future_materializer_behavior": list(REQUIRED_FUTURE_BEHAVIOR),
        "required_zero_intersections": {key: 0 for key in ZERO_INTERSECTION_KEYS},
        "required_registry_inputs": {
            "candidate_member_source_manifest_required": True,
            "training_candidate_tensor_hash_registry_required": True,
            "training_path_signature_registry_required": True,
            "training_record_identity_registry_required": True,
            "training_split_manifest_root_registry_required": True,
            "recovered_prior_registry_required": True,
            "rejected_overlap_source_registry_required": True,
        },
        "source_static_review_to_implement": _source_review_summary(source_review),
        "future_static_contract_review_requirements": list(
            FUTURE_STATIC_REVIEW_REQUIREMENTS
        ),
        "forbidden_paths": [
            "implementation_code_edit_by_this_plan_gate",
            "materialization_execution_by_this_plan_gate",
            "member_source_builder_execution_by_this_plan_gate",
            "fixed_dp_candidate_generation_execution_by_this_plan_gate",
            "camp_candidate_generation_or_trajectory_modification",
            "diffusion_planner_code_config_or_weight_change",
            "replay_training_promotion_deployment_or_safety_claim",
        ],
        "math_boundary": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "nonnegative_simplex_weights_only": True,
            "master_problem_remains_convex": True,
            "executed_trajectory_remains_dp_top1": True,
        },
        "next_gate": (
            "fresh_evaluation_split_member_source_remediation_"
            "materialization_implementation_static_contract_review_only"
        ),
    }


def _checks(
    *,
    review_path: Path,
    script_path: Path,
    test_path: Path,
    audit_path: Path,
    audit_text: str,
    source_review: dict[str, Any],
    plan: dict[str, Any],
    script_text: str,
    test_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(source_review.get("final_decision"))
    review = _dict(source_review.get("static_contract_review"))
    return [
        _check("source_review_json_exists", review_path.is_file(), str(review_path), "file exists"),
        _check("source_review_script_exists", script_path.is_file(), str(script_path), "file exists"),
        _check("source_review_test_exists", test_path.is_file(), str(test_path), "file exists"),
        _check("v13_audit_md_exists", audit_path.is_file(), str(audit_path), "file exists"),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_static_review_passed", _latest_value(audit_text, "fresh_evaluation_split_member_source_materialization_static_contract_review_passed"), "True"),
        _expect("audit_implementation_plan_authorized", _latest_value(audit_text, "materialization_implementation_plan_authorized_next"), "True"),
        *[
            _expect(f"audit_blocks_{flag}", _latest_value(audit_text, flag), "False")
            for flag in AUDIT_BLOCKED_FLAGS
        ],
        _expect("source_schema_version", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA_VERSION),
        _expect("source_status_passed", decision.get("status"), SOURCE_REVIEW_PASS_STATUS),
        _expect("source_passed", decision.get("passed"), True),
        _expect("source_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_authorizes_this_plan", decision.get("authorized_next_work"), authorized_current_work),
        _expect("source_implementation_plan_authorized", decision.get("materialization_implementation_plan_authorized_next"), True),
        *[
            _expect(f"source_blocks_{flag}", decision.get(flag), False)
            for flag in BLOCKED_SOURCE_FLAGS
        ],
        _expect("source_review_future_script_expected", review.get("future_materializer_script"), EXPECTED_FUTURE_MATERIALIZER_SCRIPT),
        _expect("source_review_future_test_expected", review.get("future_materializer_test"), EXPECTED_FUTURE_MATERIALIZER_TEST),
        _check("source_review_has_contract_groups", len(_list(review.get("required_contract_groups"))) == 7, review.get("required_contract_groups"), "7 contract groups"),
        _expect("plan_does_not_implement", plan["implementation_performed_by_this_gate"], False),
        _expect("plan_does_not_materialize", plan["materialization_performed_by_this_gate"], False),
        _expect("plan_next_gate_static_review", plan["next_gate"], "fresh_evaluation_split_member_source_remediation_materialization_implementation_static_contract_review_only"),
        _check("plan_lists_required_inputs", set(REQUIRED_SOURCE_INPUTS) <= set(plan["required_source_inputs"]), plan["required_source_inputs"], "required source inputs"),
        _check("plan_lists_future_outputs", set(FUTURE_OUTPUTS) <= set(plan["future_outputs"]), plan["future_outputs"], "future outputs"),
        _check("plan_lists_required_behavior", set(REQUIRED_FUTURE_BEHAVIOR) <= set(plan["required_future_materializer_behavior"]), plan["required_future_materializer_behavior"], "required behavior"),
        _check("plan_lists_static_review_requirements", set(FUTURE_STATIC_REVIEW_REQUIREMENTS) <= set(plan["future_static_contract_review_requirements"]), plan["future_static_contract_review_requirements"], "static review requirements"),
        _check("plan_requires_zero_intersections", all(plan["required_zero_intersections"].get(key) == 0 for key in ZERO_INTERSECTION_KEYS), plan["required_zero_intersections"], "all zero"),
        _check("plan_requires_all_registries", all(plan["required_registry_inputs"].values()), plan["required_registry_inputs"], "all True"),
        _expect("plan_score_affine", plan["math_boundary"]["score_expression"], SCORE_EXPRESSION),
        _expect("plan_nonnegative_simplex", plan["math_boundary"]["nonnegative_simplex_weights_only"], True),
        _expect("plan_master_convex", plan["math_boundary"]["master_problem_remains_convex"], True),
        _expect("plan_executed_dp_top1", plan["math_boundary"]["executed_trajectory_remains_dp_top1"], True),
        _check("plan_forbidden_paths_complete", {
            "implementation_code_edit_by_this_plan_gate",
            "materialization_execution_by_this_plan_gate",
            "member_source_builder_execution_by_this_plan_gate",
            "fixed_dp_candidate_generation_execution_by_this_plan_gate",
            "camp_candidate_generation_or_trajectory_modification",
            "diffusion_planner_code_config_or_weight_change",
            "replay_training_promotion_deployment_or_safety_claim",
        } <= set(plan["forbidden_paths"]), plan["forbidden_paths"], "forbidden paths"),
        _check("source_review_script_terms_present", all(term in script_text for term in REQUIRED_REVIEW_SCRIPT_TERMS), "script terms", "required terms"),
        _check("source_review_test_terms_present", all(term in test_text for term in REQUIRED_REVIEW_TEST_TERMS), "test terms", "required tests"),
    ]


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
        "materialization_implementation_plan_ready": passed,
        "materialization_implementation_static_contract_review_authorized_next": passed,
        "implementation_execution_authorized_next": False,
        "materialization_execution_authorized_next": False,
        "member_source_builder_execution_authorized_next": False,
        "fresh_member_selection_execution_authorized_next": False,
        "fresh_evaluation_split_evaluation_authorized_next": False,
        "data_preparation_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "replay_execution_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "implementation_executed": False,
        "materialization_executed": False,
        "member_source_builder_executed": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }


def _source_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_review.get("final_decision"))
    review = _dict(source_review.get("static_contract_review"))
    return {
        "schema_version": source_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "future_materializer_script": review.get("future_materializer_script"),
        "future_materializer_test": review.get("future_materializer_test"),
        "contract_group_count": len(_list(review.get("required_contract_groups"))),
    }


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _latest_value(text: str, key: str) -> str | None:
    marker = f"{key}="
    if marker not in text:
        return None
    return text.rsplit(marker, maxsplit=1)[1].splitlines()[0].strip()


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _is_git_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
