#!/usr/bin/env python3
"""Plan implementation of fixed-DP execution contract/input remediation."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_"
    "remediation_static_contract_review_v1"
)
SOURCE_PASS_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_"
    "remediation_static_contract_review_passed"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_"
    "remediation_implementation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_"
    "remediation_implementation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_"
    "remediation_implementation_plan_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_execution_contract_and_input_remediation_static_contract_"
    "review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_contract_and_"
    "input_remediation_implementation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_contract_and_"
    "input_remediation_implementation_static_contract_review_only"
)
RUNNER_SCRIPT = (
    "scripts/integrations/run_diffusion_planner_dp_camp_v13_fixed_candidate_generation.py"
)
PREFLIGHT_SCRIPT = (
    "scripts/integrations/preflight_diffusion_planner_dp_camp_v13_fixed_dp_candidate_"
    "generation_execution.py"
)
INPUT_MATERIALIZER_SCRIPT = (
    "scripts/integrations/materialize_diffusion_planner_dp_camp_v13_fixed_dp_candidate_"
    "generation_execution_inputs.py"
)
RUNNER_TEST = "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_candidate_generation_runner.py"
PREFLIGHT_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_"
    "execution_preflight.py"
)
INPUT_MATERIALIZER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_"
    "execution_inputs_materializer.py"
)
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
)
IMPLEMENTATION_TARGETS = (
    RUNNER_SCRIPT,
    PREFLIGHT_SCRIPT,
    INPUT_MATERIALIZER_SCRIPT,
)
IMPLEMENTATION_TEST_TARGETS = (
    RUNNER_TEST,
    PREFLIGHT_TEST,
    INPUT_MATERIALIZER_TEST,
)
RUNNER_REQUIREMENTS = (
    "split_build_report_checks_for_implementation_gate_and_execution_gate",
    "allow_execution_gate_audit_authorization_flags_only_when_authorized_current_work_is_execution",
    "stop_requiring_runner_contract_remediation_implementation_authorized_next_in_execution_gate",
    "accept_current_post_audit_camp_head_for_execution_runbook",
    "require_guard_env_var_before_subprocess_execution",
    "write_runner_execution_result_without_marking_candidate_generation_executed_on_pre_subprocess_reject",
)
PREFLIGHT_REQUIREMENTS = (
    "consume_materialized_input_contract_instead_of_execution_gate_required_placeholders",
    "regenerate_runbook_with_current_camp_head_and_actual_fixed_dp_inputs",
    "reject_missing_nonempty_valid_set_list_before_execution",
    "reject_missing_fixed_dp_checkpoint_or_args_json",
    "preserve_fixed_dp_head_and_forbidden_command_checks",
)
INPUT_MATERIALIZER_REQUIREMENTS = (
    "materialize_valid_set_list_json_with_files_array",
    "require_nonempty_npz_source_list",
    "accept_only_approved_fresh_nonformal_fixed_dp_npz_sources",
    "reject_full36_and_formal_seeds_11_12_13",
    "record_source_manifest_root_and_npz_path_signatures",
    "record_candidate_tensor_hash_path_signature_record_identity_split_manifest_root_fields_for_later_zero_overlap",
    "never_read_closed_loop_outcomes_as_training_or_online_inputs",
    "never_modify_dp_code_config_weights_or_checkpoint",
)
SOURCE_FALSE_FLAGS = (
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
    "fixed_dp_candidate_generation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "fixed_dp_candidate_generation_executed",
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_by_current_boundary",
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
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static_review_json", type=Path, required=True)
    parser.add_argument("--static_review_artifact_dir", type=Path, required=True)
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
    audit_text = _read_text(v13_audit_md)
    checks = _checks(
        static_review_json=static_review_json,
        static_review_artifact_dir=static_review_artifact_dir,
        v13_audit_md=v13_audit_md,
        source_payload=source_payload,
        source_decision=source_decision,
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
        "source_static_review": {
            "path": str(static_review_json),
            "artifact_dir": str(static_review_artifact_dir),
            "status": source_decision.get("status"),
        },
        "implementation_plan": {
            "implementation_performed_by_this_gate": False,
            "fixed_dp_execution_started_by_this_gate": False,
            "implementation_targets": list(IMPLEMENTATION_TARGETS),
            "test_targets": list(IMPLEMENTATION_TEST_TARGETS),
            "runner_requirements": list(RUNNER_REQUIREMENTS),
            "preflight_requirements": list(PREFLIGHT_REQUIREMENTS),
            "input_materializer_requirements": list(INPUT_MATERIALIZER_REQUIREMENTS),
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
            "dp_repo_modification_allowed": False,
            "candidate_generation_by_camp_allowed": False,
            "training_authorized": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def _checks(
    *,
    static_review_json: Path,
    static_review_artifact_dir: Path,
    v13_audit_md: Path,
    source_payload: dict[str, Any],
    source_decision: dict[str, Any],
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks = [
        _expect("static_review_json_exists", static_review_json.exists(), True),
        _expect("static_review_artifact_dir_exists", static_review_artifact_dir.is_dir(), True),
        _expect("v13_audit_exists", v13_audit_md.exists(), True),
        _expect("source_schema_version", source_payload.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status", source_decision.get("status"), SOURCE_PASS_STATUS),
        _expect("source_passed", source_decision.get("passed"), True),
        _expect("source_failed_checks_empty", source_decision.get("failed_checks"), []),
        _expect("source_authorized_next_work", source_decision.get("authorized_next_work"), authorized_current_work),
        _expect("source_authorizes_implementation_plan", source_decision.get("fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_plan_authorized_next"), True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_authorizes_implementation_plan", _latest_value(audit_text, "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_plan_authorized_next"), "True"),
    ]
    for flag in SOURCE_FALSE_FLAGS:
        checks.append(_expect(f"source_forbids_{flag}", source_decision.get(flag), False))
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_forbids_{flag}", _latest_value(audit_text, flag), "False"))
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
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_plan_ready": passed,
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_implementation_static_contract_review_authorized_next": passed,
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
    return "\n".join(
        [
            "# Fixed-DP Execution Contract/Input Remediation Implementation Plan",
            "",
            f"- status: `{decision['status']}`",
            f"- passed: `{decision['passed']}`",
            f"- failed_checks: `{decision['failed_checks']}`",
            f"- authorized_next_work: `{decision['authorized_next_work']}`",
            f"- fixed_dp_generation_executed: `{decision['fixed_dp_candidate_generation_executed']}`",
            f"- training_preflight_authorized: `{decision['training_preflight_authorized_next']}`",
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


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": actual == expected, "actual": actual, "expected": expected}


def _latest_value(text: str, key: str) -> str | None:
    token = f"{key}="
    if token not in text:
        return None
    return text.rsplit(token, maxsplit=1)[1].splitlines()[0].strip()


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
