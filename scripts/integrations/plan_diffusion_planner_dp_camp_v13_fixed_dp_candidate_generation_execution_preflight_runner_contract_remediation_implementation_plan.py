#!/usr/bin/env python3
"""Plan implementation of fixed-DP execution-preflight runner remediation.

This plan-only gate consumes the passed runner-contract static review and
defines the future CAMP-side runner/preflight remediation. It does not modify
the runner, run Diffusion Planner, generate candidates, train CAMP, modify DP,
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
SOURCE_SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_"
    "remediation_static_contract_review_v1"
)
SOURCE_PASS_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_"
    "remediation_static_contract_review_passed"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_"
    "remediation_implementation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_"
    "remediation_implementation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_"
    "remediation_implementation_plan_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_execution_preflight_runner_contract_remediation_static_"
    "contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "runner_contract_remediation_implementation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "runner_contract_remediation_implementation_static_contract_review_only"
)
RUNNER_SCRIPT = (
    "scripts/integrations/run_diffusion_planner_dp_camp_v13_fixed_candidate_generation.py"
)
PREFLIGHT_SCRIPT = (
    "scripts/integrations/preflight_diffusion_planner_dp_camp_v13_fixed_dp_candidate_"
    "generation_execution.py"
)
RUNNER_TEST = "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_candidate_generation_runner.py"
PREFLIGHT_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_"
    "execution_preflight.py"
)
FUTURE_IMPLEMENTATION_STATIC_REVIEW_SCRIPT = (
    "scripts/integrations/review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_"
    "generation_execution_preflight_runner_contract_remediation_implementation_static_contract.py"
)
FUTURE_IMPLEMENTATION_STATIC_REVIEW_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_"
    "execution_preflight_runner_contract_remediation_implementation_static_contract.py"
)
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
)
REQUIRED_CONTRACT_CHANGES = (
    "replace_runner_implementation_only_execute_rejection_with_execution_gate_check",
    "replace_planner_generate_placeholder_with_validated_fixed_dp_candidate_export_command",
    "preserve_zero_overlap_registry_requirements",
    "require_guard_env_var_for_any_future_execution",
    "keep_affine_score_contract",
    "keep_nonexecution_gates_default_off",
)
RUNNER_IMPLEMENTATION_REQUIREMENTS = (
    "remove_unconditional_execute_rejection_without_authorizing_this_gate",
    "require_authorized_execution_gate_and_guard_env_for_future_execute",
    "replace_planner_generate_placeholder_with_existing_fixed_dp_candidate_export_command",
    "validate_fixed_dp_command_entrypoint_exists_under_dp_repo",
    "refuse_forbidden_reference_blend_guidance_postprocess_postselection_commands",
    "keep_dp_repo_code_config_weights_and_checkpoints_read_only",
    "preserve_fixed_dp_head_check_before_any_future_execution",
    "materialize_only_fixed_dp_candidate_tensors_not_camp_generated_trajectories",
    "record_candidate_tensor_hash_path_signature_record_identity_split_manifest_root",
    "exclude_full36_and_formal_seeds_11_12_13",
    "preserve_affine_score_and_nonnegative_simplex_boundaries",
)
PREFLIGHT_IMPLEMENTATION_REQUIREMENTS = (
    "consume_runner_implementation_artifact",
    "reject_runner_missing_execution_gate_check",
    "reject_missing_fixed_dp_command_entrypoint",
    "reject_missing_zero_overlap_registry_requirements",
    "emit_runbook_only_until_execution_gate",
    "authorize_execution_preflight_pass_only_when_runner_and_command_contract_pass",
)
FUTURE_STATIC_REVIEW_REQUIREMENTS = (
    "reject_if_runner_still_hard_rejects_execute_without_gate_check",
    "reject_if_base_dp_command_uses_planner_generate_placeholder",
    "reject_if_runner_can_modify_dp_code_config_weights_or_checkpoint",
    "reject_if_runner_can_generate_repair_rewrite_blend_or_postprocess_trajectories",
    "reject_if_zero_overlap_registry_keys_are_missing",
    "reject_if_training_generation_execution_or_claims_are_authorized",
    "reject_if_score_expression_is_not_affine",
)
SOURCE_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_execution_preflight_authorized_next",
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
    "runner_contract_remediation_implementation_plan_authorized_next",
    "fixed_dp_candidate_generation_execution_preflight_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "candidate_generation_by_camp_authorized",
    "plan_static_contract",
    "score_expression",
)
REQUIRED_SOURCE_TEST_SNIPPETS = (
    "test_static_contract_review_authorizes_implementation_plan_only",
    "test_static_contract_review_rejects_source_execution_auth_leak",
    "AUTHORIZED_NEXT_WORK",
    "fixed_dp_candidate_generation_execution_authorized_next",
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
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    source_payload = _load_json_dict(static_review_json)
    source_decision = _dict(source_payload.get("final_decision"))
    source_contract = _dict(source_payload.get("plan_static_contract"))
    source_script_text = _read_text(static_review_script)
    source_test_text = _read_text(static_review_test)
    audit_text = _read_text(v13_audit_md)
    plan = _implementation_plan(source_contract=source_contract)
    checks = _checks(
        static_review_json=static_review_json,
        static_review_artifact_dir=static_review_artifact_dir,
        static_review_script=static_review_script,
        static_review_test=static_review_test,
        v13_audit_md=v13_audit_md,
        source_payload=source_payload,
        source_decision=source_decision,
        source_contract=source_contract,
        source_script_text=source_script_text,
        source_test_text=source_test_text,
        audit_text=audit_text,
        plan=plan,
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
            "implementation_performed": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
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
        "source_static_review": {
            "path": str(static_review_json.resolve()),
            "artifact_dir": str(static_review_artifact_dir.resolve()),
            "schema_version": source_payload.get("schema_version"),
            "status": source_decision.get("status"),
            "passed": source_decision.get("passed"),
            "json_sha256": _sha256(static_review_json),
        },
        "runner_contract_remediation_implementation_plan": plan,
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def _implementation_plan(*, source_contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "implementation_performed_by_this_gate": False,
        "future_implementation_targets": list(FUTURE_IMPLEMENTATION_TARGETS()),
        "future_runner_script": RUNNER_SCRIPT,
        "future_preflight_script": PREFLIGHT_SCRIPT,
        "future_runner_test": RUNNER_TEST,
        "future_preflight_test": PREFLIGHT_TEST,
        "future_implementation_static_review_script": FUTURE_IMPLEMENTATION_STATIC_REVIEW_SCRIPT,
        "future_implementation_static_review_test": FUTURE_IMPLEMENTATION_STATIC_REVIEW_TEST,
        "runner_owner_repo": "CAMP",
        "dp_repo_modification_allowed": False,
        "dp_config_weight_checkpoint_change_allowed": False,
        "fixed_dp_candidate_generation_authorized_by_this_gate": False,
        "fixed_dp_candidate_generation_execution_authorized_by_this_gate": False,
        "training_authorized_by_this_gate": False,
        "candidate_generation_by_camp_allowed": False,
        "trajectory_generation_by_camp_allowed": False,
        "trajectory_modification_by_camp_allowed": False,
        "source_required_contract_changes": _list(source_contract.get("required_contract_changes")),
        "source_future_implementation_targets": _list(source_contract.get("future_implementation_targets")),
        "required_contract_changes": list(REQUIRED_CONTRACT_CHANGES),
        "runner_implementation_requirements": list(RUNNER_IMPLEMENTATION_REQUIREMENTS),
        "preflight_implementation_requirements": list(PREFLIGHT_IMPLEMENTATION_REQUIREMENTS),
        "future_static_review_requirements": list(FUTURE_STATIC_REVIEW_REQUIREMENTS),
        "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def FUTURE_IMPLEMENTATION_TARGETS() -> tuple[str, str]:
    return (RUNNER_SCRIPT, PREFLIGHT_SCRIPT)


def _checks(
    *,
    static_review_json: Path,
    static_review_artifact_dir: Path,
    static_review_script: Path,
    static_review_test: Path,
    v13_audit_md: Path,
    source_payload: dict[str, Any],
    source_decision: dict[str, Any],
    source_contract: dict[str, Any],
    source_script_text: str,
    source_test_text: str,
    audit_text: str,
    plan: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add = checks.append
    source_targets = set(_list(source_contract.get("future_implementation_targets")))
    source_changes = set(_list(source_contract.get("required_contract_changes")))
    plan_targets = set(_list(plan.get("future_implementation_targets")))

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
            "source_static_review_passed",
            source_decision.get("runner_contract_remediation_static_contract_review_passed"),
            True,
        )
    )
    add(
        _expect(
            "source_authorizes_implementation_plan",
            source_decision.get("runner_contract_remediation_implementation_plan_authorized_next"),
            True,
        )
    )
    for flag in SOURCE_FALSE_FLAGS:
        add(_expect(f"source_forbids_{flag}", source_decision.get(flag), False))
    add(_expect("source_candidate_operation", source_decision.get("candidate_operation"), "fixed DP candidate reranking only"))
    add(_expect("source_score_expression", source_decision.get("score_expression"), SCORE_EXPRESSION))

    add(_expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main))
    add(_expect("current_dp_head_fixed", current_dp_head, required_dp_head))
    add(_expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD))
    add(_expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS))
    add(_expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work))
    add(
        _expect(
            "audit_authorizes_implementation_plan",
            _latest_value(audit_text, "runner_contract_remediation_implementation_plan_authorized_next"),
            "True",
        )
    )
    for flag in AUDIT_FALSE_FLAGS:
        add(_expect(f"audit_forbids_{flag}", _latest_value(audit_text, flag), "False"))

    for target in FUTURE_IMPLEMENTATION_TARGETS():
        add(_expect(f"source_targets_{_slug(target)}", target in source_targets, True))
        add(_expect(f"plan_targets_{_slug(target)}", target in plan_targets, True))
    for change in REQUIRED_CONTRACT_CHANGES:
        add(_expect(f"source_requires_{_slug(change)}", change in source_changes, True))
        add(_expect(f"plan_requires_{_slug(change)}", change in set(plan["required_contract_changes"]), True))
    add(_expect("plan_implementation_not_performed", plan.get("implementation_performed_by_this_gate"), False))
    add(_expect("plan_runner_owner_repo", plan.get("runner_owner_repo"), "CAMP"))
    add(_expect("plan_forbids_dp_modification", plan.get("dp_repo_modification_allowed"), False))
    add(
        _expect(
            "plan_forbids_dp_config_weight_checkpoint_change",
            plan.get("dp_config_weight_checkpoint_change_allowed"),
            False,
        )
    )
    add(_expect("plan_forbids_generation_execution", plan.get("fixed_dp_candidate_generation_execution_authorized_by_this_gate"), False))
    add(_expect("plan_forbids_training", plan.get("training_authorized_by_this_gate"), False))
    for key in ZERO_OVERLAP_KEYS:
        add(_expect(f"plan_requires_zero_overlap_{key}", key in set(plan["required_zero_overlap_keys"]), True))
    for item in RUNNER_IMPLEMENTATION_REQUIREMENTS:
        add(_expect(f"plan_runner_requires_{_slug(item)}", item in set(plan["runner_implementation_requirements"]), True))
    for item in PREFLIGHT_IMPLEMENTATION_REQUIREMENTS:
        add(_expect(f"plan_preflight_requires_{_slug(item)}", item in set(plan["preflight_implementation_requirements"]), True))
    for item in FUTURE_STATIC_REVIEW_REQUIREMENTS:
        add(_expect(f"plan_static_review_requires_{_slug(item)}", item in set(plan["future_static_review_requirements"]), True))
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
        "runner_contract_remediation_implementation_plan_ready": passed,
        "runner_contract_remediation_implementation_static_contract_review_authorized_next": passed,
        "runner_contract_remediation_implementation_authorized_next": False,
        "fixed_dp_candidate_generation_execution_preflight_authorized_next": False,
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
    plan = _dict(report.get("runner_contract_remediation_implementation_plan"))
    return "\n".join(
        [
            "# Runner Contract Remediation Implementation Plan",
            "",
            f"- Status: `{decision.get('status')}`",
            f"- Passed: `{decision.get('passed')}`",
            f"- Failed checks: `{decision.get('failed_checks')}`",
            f"- Authorized next work: `{decision.get('authorized_next_work')}`",
            f"- Implementation performed by this gate: `{plan.get('implementation_performed_by_this_gate')}`",
            f"- Future runner script: `{plan.get('future_runner_script')}`",
            f"- Future preflight script: `{plan.get('future_preflight_script')}`",
            f"- Future static review script: `{plan.get('future_implementation_static_review_script')}`",
            f"- Fixed-DP generation execution authorized: `{decision.get('fixed_dp_candidate_generation_execution_authorized_next')}`",
            f"- Training preflight authorized: `{decision.get('training_preflight_authorized_next')}`",
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
