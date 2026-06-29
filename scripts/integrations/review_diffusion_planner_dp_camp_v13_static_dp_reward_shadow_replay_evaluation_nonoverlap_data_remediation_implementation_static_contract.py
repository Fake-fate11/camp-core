#!/usr/bin/env python3
"""Static contract review for v13 non-overlap remediation implementation plan.

This is a read-only review gate. It consumes the completed implementation-plan
artifact and verifies that the future implementation scope is still limited to
non-overlap result-readiness hardening. It does not implement result-readiness,
run replay, generate candidates, train CAMP, modify Diffusion Planner, promote
artifacts, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_implementation_static_contract_review_v1"
)
READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_implementation_static_contract_review_complete"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_implementation_static_contract_review_rejected"
)
SOURCE_PLAN_SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_implementation_plan_v1"
)
SOURCE_PLAN_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_implementation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_data_remediation_implementation_only"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14
MINIMUM_HOLDOUT_RECORDS = 3200
MINIMUM_HOLDOUT_SELECTION_LOGS = 32
FUTURE_RESULT_READINESS_SCRIPT = (
    "scripts/integrations/"
    "review_diffusion_planner_dp_camp_v13_static_dp_reward_"
    "shadow_replay_evaluation_result_readiness.py"
)
FUTURE_RESULT_READINESS_TEST = (
    "camp_core/tests/"
    "test_diffusion_planner_dp_camp_v13_static_dp_reward_"
    "shadow_replay_evaluation_result_readiness.py"
)
FUTURE_IMPLEMENTATION_STATIC_CONTRACT_TEST = (
    "camp_core/tests/"
    "test_diffusion_planner_dp_camp_v13_static_dp_reward_"
    "shadow_replay_evaluation_nonoverlap_data_remediation_"
    "implementation_static_contract.py"
)
EXPECTED_FUTURE_CLI_ARGS = (
    "--split_manifest_json",
    "--candidate_tensor_hash_registry_json",
    "--path_signature_registry_json",
    "--record_identity_hash_registry_json",
)
REQUIRED_FUTURE_CHANGE_PHRASES = (
    "split_manifest_json",
    "train and holdout selection-log roots to be disjoint",
    "candidate_tensor_hash train/eval intersection count to be zero",
    "path_signature train/eval intersection count to be zero",
    "record_identity_hash train/eval intersection count to be zero",
    "every training_summary.selection_logs entry",
    "formal seeds 11/12/13",
    "diagnosed prior evaluation root",
    "training-summary selection logs",
    "default-off shadow selector",
    "fixed DP Top-1",
    "score_k(w)=a_k^T w",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only static contract review for the v13 static DP-reward "
            "non-overlap data remediation implementation plan."
        )
    )
    parser.add_argument("--implementation_plan_json", type=Path, required=True)
    parser.add_argument("--implementation_plan_script_py", type=Path, required=True)
    parser.add_argument("--implementation_plan_test_py", type=Path, required=True)
    parser.add_argument("--result_readiness_py", type=Path, required=True)
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
        implementation_plan_script_py=args.implementation_plan_script_py,
        implementation_plan_test_py=args.implementation_plan_test_py,
        result_readiness_py=args.result_readiness_py,
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
    implementation_plan_script_py: Path,
    implementation_plan_test_py: Path,
    result_readiness_py: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    implementation_plan_json = implementation_plan_json.resolve()
    implementation_plan_script_py = implementation_plan_script_py.resolve()
    implementation_plan_test_py = implementation_plan_test_py.resolve()
    result_readiness_py = result_readiness_py.resolve()
    v13_audit_md = v13_audit_md.resolve()

    source_plan = _load_json_dict(implementation_plan_json)
    implementation_plan_script_text = _read_text(implementation_plan_script_py)
    implementation_plan_test_text = _read_text(implementation_plan_test_py)
    result_readiness_text = _read_text(result_readiness_py)
    audit_text = _read_text(v13_audit_md)
    source_summary = _source_summary(source_plan)
    planned_implementation = _planned_implementation(source_plan)

    checks = _checks(
        implementation_plan_json=implementation_plan_json,
        implementation_plan_script_py=implementation_plan_script_py,
        implementation_plan_test_py=implementation_plan_test_py,
        result_readiness_py=result_readiness_py,
        v13_audit_md=v13_audit_md,
        implementation_plan_script_text=implementation_plan_script_text,
        implementation_plan_test_text=implementation_plan_test_text,
        result_readiness_text=result_readiness_text,
        audit_text=audit_text,
        source_plan=source_plan,
        source_summary=source_summary,
        planned_implementation=planned_implementation,
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
            "implementation_execution": False,
            "training_preflight": False,
            "training_execution": False,
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
            "implementation_plan_json": str(implementation_plan_json),
            "implementation_plan_script_py": str(implementation_plan_script_py),
            "implementation_plan_test_py": str(implementation_plan_test_py),
            "result_readiness_py": str(result_readiness_py),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_hashes": {
            "implementation_plan_json_sha256": _sha256(implementation_plan_json),
            "implementation_plan_script_py_sha256": _sha256(implementation_plan_script_py),
            "implementation_plan_test_py_sha256": _sha256(implementation_plan_test_py),
            "result_readiness_py_sha256": _sha256(result_readiness_py),
            "v13_audit_md_sha256": _sha256(v13_audit_md),
        },
        "source_summary": source_summary,
        "planned_implementation": planned_implementation,
        "review_checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "implementation_static_contract_review_complete": passed,
            "implementation_authorized_next": passed,
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


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["planned_implementation"]
    lines = [
        "# V13 Static DP-Reward Non-Overlap Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation authorized next: `{decision['implementation_authorized_next']}`",
        f"- Training preflight authorized next: `{decision['training_preflight_authorized_next']}`",
        f"- Replay authorized next: `{decision['replay_execution_authorized_next']}`",
        f"- Fixed-DP candidate generation authorized next: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Plan",
        "",
        f"- Status: `{report['source_summary'].get('status')}`",
        f"- Plan status: `{plan.get('status')}`",
        f"- Future script: `{plan.get('future_result_readiness_script')}`",
        f"- Future test: `{plan.get('future_result_readiness_test')}`",
        f"- Candidate operation: `{plan.get('candidate_operation')}`",
        f"- Score expression: `{plan.get('score_expression')}`",
        "",
        "This review is read-only. It does not implement result-readiness, build a split manifest, run replay, generate candidates, train CAMP, modify DP, promote, deploy, or authorize safety/CAMP-over-DP claims.",
        "",
    ]
    return "\n".join(lines)


def _source_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_plan.get("final_decision"))
    summary = _dict(source_plan.get("source_summary"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "implementation_plan_ready": decision.get("implementation_plan_ready"),
        "implementation_static_contract_review_authorized_next": decision.get(
            "implementation_static_contract_review_authorized_next"
        ),
        "implementation_authorized_next": decision.get("implementation_authorized_next"),
        "training_preflight_authorized_next": decision.get("training_preflight_authorized_next"),
        "training_execution_authorized_next": decision.get("training_execution_authorized_next"),
        "replay_execution_authorized_next": decision.get("replay_execution_authorized_next"),
        "fixed_dp_candidate_generation_authorized_next": decision.get(
            "fixed_dp_candidate_generation_authorized_next"
        ),
        "candidate_generation_by_camp_authorized": decision.get(
            "candidate_generation_by_camp_authorized"
        ),
        "dp_modification_authorized": decision.get("dp_modification_authorized"),
        "selector_promotion_authorized": decision.get("selector_promotion_authorized"),
        "atom_promotion_authorized": decision.get("atom_promotion_authorized"),
        "deployment_authorized": decision.get("deployment_authorized"),
        "safety_benefit_claim_authorized": decision.get("safety_benefit_claim_authorized"),
        "camp_over_dp_top1_claim_authorized": decision.get("camp_over_dp_top1_claim_authorized"),
        "source_status": summary.get("status"),
        "source_authorized_next_work": summary.get("authorized_next_work"),
        "split_manifest_required": summary.get("split_manifest_required"),
        "candidate_tensor_hash_registry_required": summary.get(
            "candidate_tensor_hash_registry_required"
        ),
        "path_signature_registry_required": summary.get("path_signature_registry_required"),
        "record_identity_hash_registry_required": summary.get(
            "record_identity_hash_registry_required"
        ),
        "train_eval_candidate_tensor_intersection_must_be_zero": summary.get(
            "train_eval_candidate_tensor_intersection_must_be_zero"
        ),
        "train_eval_path_signature_intersection_must_be_zero": summary.get(
            "train_eval_path_signature_intersection_must_be_zero"
        ),
        "result_readiness_must_compare_against_all_training_summary_selection_logs": summary.get(
            "result_readiness_must_compare_against_all_training_summary_selection_logs"
        ),
        "formal_seeds_11_12_13_excluded": summary.get("formal_seeds_11_12_13_excluded"),
        "minimum_holdout_records": summary.get("minimum_holdout_records"),
        "minimum_holdout_selection_logs": summary.get("minimum_holdout_selection_logs"),
        "expected_candidate_count": summary.get("expected_candidate_count"),
        "expected_atom_count": summary.get("expected_atom_count"),
        "candidate_operation": summary.get("candidate_operation"),
        "score_expression": summary.get("score_expression"),
    }


def _planned_implementation(source_plan: dict[str, Any]) -> dict[str, Any]:
    plan = _dict(source_plan.get("implementation_plan"))
    acceptance = _dict(plan.get("future_result_readiness_acceptance"))
    return {
        "status": plan.get("status"),
        "implementation_performed_by_this_gate": plan.get("implementation_performed_by_this_gate"),
        "future_result_readiness_script": plan.get("future_result_readiness_script"),
        "future_result_readiness_test": plan.get("future_result_readiness_test"),
        "future_implementation_static_contract_test": plan.get(
            "future_implementation_static_contract_test"
        ),
        "future_cli_extensions": _list(plan.get("future_cli_extensions")),
        "required_future_changes": _list(plan.get("required_future_changes")),
        "minimum_holdout_records": acceptance.get("minimum_holdout_records"),
        "minimum_holdout_selection_logs": acceptance.get("minimum_holdout_selection_logs"),
        "expected_candidate_count": acceptance.get("expected_candidate_count"),
        "expected_atom_count": acceptance.get("expected_atom_count"),
        "candidate_operation": acceptance.get("candidate_operation"),
        "score_expression": acceptance.get("score_expression"),
        "not_authorized_by_this_plan": _dict(plan.get("not_authorized_by_this_plan")),
    }


def _checks(
    *,
    implementation_plan_json: Path,
    implementation_plan_script_py: Path,
    implementation_plan_test_py: Path,
    result_readiness_py: Path,
    v13_audit_md: Path,
    implementation_plan_script_text: str,
    implementation_plan_test_text: str,
    result_readiness_text: str,
    audit_text: str,
    source_plan: dict[str, Any],
    source_summary: dict[str, Any],
    planned_implementation: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks = [
        _check("implementation_plan_json_exists", implementation_plan_json.is_file(), str(implementation_plan_json), "file exists"),
        _check("implementation_plan_script_py_exists", implementation_plan_script_py.is_file(), str(implementation_plan_script_py), "file exists"),
        _check("implementation_plan_test_py_exists", implementation_plan_test_py.is_file(), str(implementation_plan_test_py), "file exists"),
        _check("result_readiness_py_exists", result_readiness_py.is_file(), str(result_readiness_py), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        _check("current_dp_head_fixed", current_dp_head == required_dp_head, current_dp_head, required_dp_head),
        _check("required_dp_head_fixed", required_dp_head == FIXED_DP_HEAD, required_dp_head, FIXED_DP_HEAD),
        _contains("current_gate_authorized_in_audit", audit_text, f"next_work_target={authorized_current_work}"),
        _contains(
            "current_status_implementation_plan_ready",
            audit_text,
            "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_"
            "shadow_replay_evaluation_nonoverlap_data_remediation_implementation_plan_ready",
        ),
        _contains(
            "audit_keeps_implementation_disabled",
            audit_text,
            "implementation_authorized_by_current_boundary=False",
        ),
        _contains(
            "audit_keeps_training_preflight_disabled",
            audit_text,
            "static_dp_reward_training_preflight_authorized_by_current_boundary=False",
        ),
        _contains(
            "audit_keeps_training_execution_disabled",
            audit_text,
            "training_execution_authorized_by_current_boundary=False",
        ),
        _contains(
            "audit_keeps_replay_disabled",
            audit_text,
            "replay_execution_authorized_by_current_boundary=False",
        ),
        _contains(
            "audit_keeps_fixed_dp_candidate_generation_disabled",
            audit_text,
            "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        ),
        _contains(
            "audit_keeps_camp_candidate_generation_disabled",
            audit_text,
            "candidate_generation_by_camp_authorized_by_current_boundary=False",
        ),
        _contains("audit_keeps_dp_modification_disabled", audit_text, "dp_modification_authorized_by_current_boundary=False"),
        _expect_summary(source_summary, "schema_version", SOURCE_PLAN_SCHEMA_VERSION),
        _expect_summary(source_summary, "status", SOURCE_PLAN_STATUS),
        _expect_summary(source_summary, "passed", True),
        _expect_summary(source_summary, "failed_checks", []),
        _expect_summary(source_summary, "authorized_next_work", authorized_current_work),
        _expect_summary(source_summary, "implementation_plan_ready", True),
        _expect_summary(source_summary, "implementation_static_contract_review_authorized_next", True),
        _expect_summary(source_summary, "implementation_authorized_next", False),
        _expect_summary(source_summary, "training_preflight_authorized_next", False),
        _expect_summary(source_summary, "training_execution_authorized_next", False),
        _expect_summary(source_summary, "replay_execution_authorized_next", False),
        _expect_summary(source_summary, "fixed_dp_candidate_generation_authorized_next", False),
        _expect_summary(source_summary, "candidate_generation_by_camp_authorized", False),
        _expect_summary(source_summary, "dp_modification_authorized", False),
        _expect_summary(source_summary, "selector_promotion_authorized", False),
        _expect_summary(source_summary, "atom_promotion_authorized", False),
        _expect_summary(source_summary, "deployment_authorized", False),
        _expect_summary(source_summary, "safety_benefit_claim_authorized", False),
        _expect_summary(source_summary, "camp_over_dp_top1_claim_authorized", False),
        _expect_summary(
            source_summary,
            "source_status",
            "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
            "nonoverlap_data_remediation_static_contract_review_complete",
        ),
        _expect_summary(
            source_summary,
            "source_authorized_next_work",
            "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
            "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
            "nonoverlap_data_remediation_implementation_plan_only",
        ),
        _expect_summary(source_summary, "split_manifest_required", True),
        _expect_summary(source_summary, "candidate_tensor_hash_registry_required", True),
        _expect_summary(source_summary, "path_signature_registry_required", True),
        _expect_summary(source_summary, "record_identity_hash_registry_required", True),
        _expect_summary(source_summary, "train_eval_candidate_tensor_intersection_must_be_zero", True),
        _expect_summary(source_summary, "train_eval_path_signature_intersection_must_be_zero", True),
        _expect_summary(
            source_summary,
            "result_readiness_must_compare_against_all_training_summary_selection_logs",
            True,
        ),
        _expect_summary(source_summary, "formal_seeds_11_12_13_excluded", True),
        _expect_summary(source_summary, "minimum_holdout_records", MINIMUM_HOLDOUT_RECORDS),
        _expect_summary(source_summary, "minimum_holdout_selection_logs", MINIMUM_HOLDOUT_SELECTION_LOGS),
        _expect_summary(source_summary, "expected_candidate_count", EXPECTED_CANDIDATE_COUNT),
        _expect_summary(source_summary, "expected_atom_count", EXPECTED_ATOM_COUNT),
        _expect_summary(source_summary, "candidate_operation", "fixed DP candidate reranking only"),
        _expect_summary(source_summary, "score_expression", SCORE_EXPRESSION),
        _expect_plan(planned_implementation, "status", "plan_ready_no_implementation"),
        _expect_plan(planned_implementation, "implementation_performed_by_this_gate", False),
        _expect_plan(planned_implementation, "future_result_readiness_script", FUTURE_RESULT_READINESS_SCRIPT),
        _expect_plan(planned_implementation, "future_result_readiness_test", FUTURE_RESULT_READINESS_TEST),
        _expect_plan(
            planned_implementation,
            "future_implementation_static_contract_test",
            FUTURE_IMPLEMENTATION_STATIC_CONTRACT_TEST,
        ),
        _expect_plan(planned_implementation, "minimum_holdout_records", MINIMUM_HOLDOUT_RECORDS),
        _expect_plan(planned_implementation, "minimum_holdout_selection_logs", MINIMUM_HOLDOUT_SELECTION_LOGS),
        _expect_plan(planned_implementation, "expected_candidate_count", EXPECTED_CANDIDATE_COUNT),
        _expect_plan(planned_implementation, "expected_atom_count", EXPECTED_ATOM_COUNT),
        _expect_plan(planned_implementation, "candidate_operation", "fixed DP candidate reranking only"),
        _expect_plan(planned_implementation, "score_expression", SCORE_EXPRESSION),
        _contains(
            "implementation_plan_script_mentions_plan_current_gate",
            implementation_plan_script_text,
            "nonoverlap_data_remediation_implementation_plan_only",
        ),
        _contains(
            "implementation_plan_script_mentions_plan_next_gate",
            implementation_plan_script_text,
            "nonoverlap_data_remediation_implementation_static_contract_review_only",
        ),
        _contains("implementation_plan_script_mentions_plan_status", implementation_plan_script_text, "plan_ready_no_implementation"),
        _contains(
            "implementation_plan_script_mentions_no_implementation",
            implementation_plan_script_text,
            "implementation_performed_by_this_gate",
        ),
        _contains("implementation_plan_test_rejects_implementation_auth", implementation_plan_test_text, "test_nonoverlap_implementation_plan_rejects_source_implementation_auth"),
        _contains("implementation_plan_test_rejects_training_preflight_auth", implementation_plan_test_text, "test_nonoverlap_implementation_plan_rejects_source_training_preflight_auth"),
        _contains("implementation_plan_test_rejects_zero_intersection_drift", implementation_plan_test_text, "test_nonoverlap_implementation_plan_rejects_missing_zero_intersection_contract"),
        _contains("implementation_plan_test_rejects_dp_head_drift", implementation_plan_test_text, "test_nonoverlap_implementation_plan_rejects_dp_head_drift"),
        _contains("result_readiness_has_previous_training_summary_input", result_readiness_text, "previous_training_summary_json"),
        _contains("result_readiness_compares_candidate_tensor_hashes", result_readiness_text, "_compare_candidate_tensor_hashes"),
        _contains("result_readiness_has_max_overlap_rate", result_readiness_text, "max_previous_overlap_rate"),
    ]
    for arg in EXPECTED_FUTURE_CLI_ARGS:
        checks.append(
            _list_contains(
                f"planned_future_cli_arg_{arg.removeprefix('--')}",
                planned_implementation["future_cli_extensions"],
                arg,
            )
        )
        checks.append(_contains(f"implementation_plan_script_mentions_{arg.removeprefix('--')}", implementation_plan_script_text, arg))
    for phrase in REQUIRED_FUTURE_CHANGE_PHRASES:
        checks.append(
            _list_contains(
                f"planned_future_change_{_slug(phrase)}",
                planned_implementation["required_future_changes"],
                phrase,
            )
        )
    for key in (
        "implementation",
        "training_preflight",
        "training_execution",
        "replay_execution",
        "fixed_dp_candidate_generation",
        "candidate_generation_by_camp",
        "dp_modification",
        "promotion",
        "deployment",
        "safety_claim",
        "camp_over_dp_top1_claim",
    ):
        blocked = planned_implementation["not_authorized_by_this_plan"].get(key)
        checks.append(_check(f"plan_blocks_{key}", blocked is True, blocked, True))
    return checks


def _expect_summary(summary: dict[str, Any], key: str, expected: Any) -> dict[str, Any]:
    return _check(key, summary.get(key) == expected, summary.get(key), expected)


def _expect_plan(plan: dict[str, Any], key: str, expected: Any) -> dict[str, Any]:
    return _check(f"implementation_plan_{key}", plan.get(key) == expected, plan.get(key), expected)


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else None, needle)


def _list_contains(name: str, items: list[Any], needle: str) -> dict[str, Any]:
    observed = [item for item in items if isinstance(item, str) and needle in item]
    return _check(name, bool(observed), observed, f"contains {needle}")


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


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def _slug(value: str) -> str:
    return (
        value.lower()
        .replace("--", "")
        .replace("/", "_")
        .replace(" ", "_")
        .replace("-", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("=", "_")
    )


if __name__ == "__main__":
    raise SystemExit(main())
