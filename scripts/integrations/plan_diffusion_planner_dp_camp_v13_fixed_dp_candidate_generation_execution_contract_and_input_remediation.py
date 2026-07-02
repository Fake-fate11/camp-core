#!/usr/bin/env python3
"""Plan fixed-DP candidate-generation execution contract/input remediation.

This plan-only gate consumes the failed execution artifact and defines the
next implementation boundary. It does not run Diffusion Planner, generate
candidates, train CAMP, modify DP, promote, deploy, or make safety/CAMP-over-DP
claims.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_"
    "remediation_runner_implementation_v1"
)
SOURCE_REJECT_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_runner_contract_"
    "remediation_runner_implementation_rejected"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_"
    "remediation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_"
    "remediation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_"
    "remediation_plan_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_execution_rejected_runner_contract_authorization_"
    "mismatch_and_missing_inputs"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_contract_and_"
    "input_remediation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_contract_and_"
    "input_remediation_static_contract_review_only"
)
RUNNER_SCRIPT = (
    "scripts/integrations/run_diffusion_planner_dp_camp_v13_fixed_candidate_generation.py"
)
PREFLIGHT_SCRIPT = (
    "scripts/integrations/preflight_diffusion_planner_dp_camp_v13_fixed_dp_candidate_"
    "generation_execution.py"
)
FUTURE_STATIC_REVIEW_SCRIPT = (
    "scripts/integrations/review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_"
    "generation_execution_contract_and_input_remediation_static_contract.py"
)
FUTURE_STATIC_REVIEW_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_"
    "execution_contract_and_input_remediation_static_contract.py"
)
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
)
REQUIRED_FAILED_CHECKS = (
    "source_authorized_next_work",
    "audit_authorizes_implementation",
    "audit_forbids_fixed_dp_candidate_generation_authorized_next",
    "audit_forbids_fixed_dp_candidate_generation_execution_authorized_next",
    "audit_forbids_fixed_dp_candidate_generation_authorized_by_current_boundary",
)
CONTRACT_REMEDIATIONS = (
    "split_runner_validation_between_implementation_gate_and_execution_gate",
    "allow_preflight_authorized_fixed_dp_execution_flags_only_in_execution_gate",
    "remove_execution_gate_dependency_on_runner_contract_remediation_implementation_authorized_next",
    "refresh_runbook_current_camp_head_after_audit_commit",
    "keep_guard_env_required_for_execution",
    "keep_dp_repo_code_config_weights_and_checkpoints_read_only",
    "preserve_fixed_dp_head_check",
    "preserve_forbidden_generation_repair_rewrite_blend_guidance_postprocess_checks",
)
INPUT_REMEDIATIONS = (
    "materialize_valid_set_list_json_from_approved_fresh_nonformal_fixed_dp_npz_sources",
    "require_nonempty_valid_set_list_before_execution",
    "stage_existing_fixed_dp_checkpoint_path_without_modifying_checkpoint",
    "stage_existing_fixed_dp_args_json_path_without_modifying_dp_config",
    "reject_full36_and_formal_seeds_11_12_13",
    "record_zero_overlap_keys_before_holdout_or_evaluation_use",
)
AUDIT_FALSE_FLAGS = (
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution_rejection_json", type=Path, required=True)
    parser.add_argument("--execution_rejection_artifact_dir", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--dp_repo", type=Path, default=Path("/root/autodl-tmp/Diffusion-Planner"))
    parser.add_argument("--camp_repo", type=Path, default=Path("/root/autodl-tmp/camp_core"))
    parser.add_argument("--fixed_dp_checkpoint", type=Path, required=True)
    parser.add_argument("--fixed_dp_args_json", type=Path, required=True)
    parser.add_argument("--required_valid_set_list", type=Path, required=True)
    parser.add_argument("--candidate_output_dir", type=Path, required=True)
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
        execution_rejection_json=args.execution_rejection_json,
        execution_rejection_artifact_dir=args.execution_rejection_artifact_dir,
        v13_audit_md=args.v13_audit_md,
        dp_repo=args.dp_repo,
        camp_repo=args.camp_repo,
        fixed_dp_checkpoint=args.fixed_dp_checkpoint,
        fixed_dp_args_json=args.fixed_dp_args_json,
        required_valid_set_list=args.required_valid_set_list,
        candidate_output_dir=args.candidate_output_dir,
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
    execution_rejection_json: Path,
    execution_rejection_artifact_dir: Path,
    v13_audit_md: Path,
    dp_repo: Path,
    camp_repo: Path,
    fixed_dp_checkpoint: Path,
    fixed_dp_args_json: Path,
    required_valid_set_list: Path,
    candidate_output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    source_payload = _load_json_dict(execution_rejection_json)
    source_decision = _dict(source_payload.get("final_decision"))
    audit_text = _read_text(v13_audit_md)
    checks = _checks(
        execution_rejection_json=execution_rejection_json,
        execution_rejection_artifact_dir=execution_rejection_artifact_dir,
        v13_audit_md=v13_audit_md,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        fixed_dp_checkpoint=fixed_dp_checkpoint,
        fixed_dp_args_json=fixed_dp_args_json,
        required_valid_set_list=required_valid_set_list,
        candidate_output_dir=candidate_output_dir,
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
        "source_execution_rejection": {
            "path": str(execution_rejection_json),
            "artifact_dir": str(execution_rejection_artifact_dir),
            "failed_checks": source_decision.get("failed_checks"),
            "runner_execution_present": "runner_execution" in source_payload,
            "fixed_dp_candidate_generation_executed": source_decision.get(
                "fixed_dp_candidate_generation_executed"
            ),
        },
        "remediation_plan": {
            "implementation_performed_by_this_gate": False,
            "fixed_dp_execution_started_by_this_gate": False,
            "future_runner_script": RUNNER_SCRIPT,
            "future_preflight_script": PREFLIGHT_SCRIPT,
            "future_static_review_script": FUTURE_STATIC_REVIEW_SCRIPT,
            "future_static_review_test": FUTURE_STATIC_REVIEW_TEST,
            "contract_remediations": list(CONTRACT_REMEDIATIONS),
            "input_remediations": list(INPUT_REMEDIATIONS),
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
            "fixed_dp_checkpoint": str(fixed_dp_checkpoint),
            "fixed_dp_args_json": str(fixed_dp_args_json),
            "required_valid_set_list": str(required_valid_set_list),
            "candidate_output_dir": str(candidate_output_dir),
            "dp_repo_modification_allowed": False,
            "candidate_generation_by_camp_allowed": False,
            "training_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
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
    execution_rejection_json: Path,
    execution_rejection_artifact_dir: Path,
    v13_audit_md: Path,
    dp_repo: Path,
    camp_repo: Path,
    fixed_dp_checkpoint: Path,
    fixed_dp_args_json: Path,
    required_valid_set_list: Path,
    candidate_output_dir: Path,
    source_payload: dict[str, Any],
    source_decision: dict[str, Any],
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    exit_txt = execution_rejection_artifact_dir / "exit.txt"
    checks = [
        _expect("execution_rejection_json_exists", execution_rejection_json.exists(), True),
        _expect("execution_rejection_artifact_dir_exists", execution_rejection_artifact_dir.is_dir(), True),
        _expect("v13_audit_exists", v13_audit_md.exists(), True),
        _expect("source_schema_version", source_payload.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status", source_decision.get("status"), SOURCE_REJECT_STATUS),
        _expect("source_passed", source_decision.get("passed"), False),
        _expect("source_authorized_next_work_none", source_decision.get("authorized_next_work"), None),
        _expect("source_runner_execution_absent", "runner_execution" in source_payload, False),
        _expect("source_fixed_dp_generation_not_executed", source_decision.get("fixed_dp_candidate_generation_executed"), False),
        _expect("source_dp_modification_forbidden", source_decision.get("dp_modification_authorized"), False),
        _expect("source_training_preflight_forbidden", source_decision.get("training_preflight_authorized_next"), False),
        _expect("source_safety_claim_forbidden", source_decision.get("safety_benefit_claim_authorized"), False),
        _expect("source_camp_over_dp_claim_forbidden", source_decision.get("camp_over_dp_top1_claim_authorized"), False),
        _expect("execution_exit_recorded_as_1", _read_text(exit_txt).strip() if exit_txt.exists() else None, "1"),
        _expect("dp_repo_exists", dp_repo.is_dir(), True),
        _expect("camp_repo_exists", camp_repo.is_dir(), True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("fixed_dp_checkpoint_exists", fixed_dp_checkpoint.is_file(), True),
        _expect("fixed_dp_args_json_exists", fixed_dp_args_json.is_file(), True),
        _expect("required_valid_set_list_missing_before_remediation", required_valid_set_list.exists(), False),
        _expect("candidate_output_dir_not_created", candidate_output_dir.exists(), False),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_authorizes_remediation_plan", _latest_value(audit_text, "fixed_dp_candidate_generation_execution_contract_and_input_remediation_plan_authorized_next"), "True"),
        _expect("audit_records_execution_rejected", _latest_value(audit_text, "fixed_dp_candidate_generation_execution_rejected"), "True"),
    ]
    failed_checks = set(_list(source_decision.get("failed_checks")))
    for check_name in REQUIRED_FAILED_CHECKS:
        checks.append(_expect(f"source_failed_check_{_slug(check_name)}", check_name in failed_checks, True))
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
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_plan_ready": passed,
        "fixed_dp_candidate_generation_execution_contract_and_input_remediation_static_contract_review_authorized_next": passed,
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
    plan = _dict(report["remediation_plan"])
    return "\n".join(
        [
            "# Fixed-DP Candidate Generation Execution Contract/Input Remediation Plan",
            "",
            f"- status: `{decision['status']}`",
            f"- passed: `{decision['passed']}`",
            f"- failed_checks: `{decision['failed_checks']}`",
            f"- authorized_next_work: `{decision['authorized_next_work']}`",
            f"- future_runner_script: `{plan['future_runner_script']}`",
            f"- future_preflight_script: `{plan['future_preflight_script']}`",
            f"- fixed_dp_execution_started_by_this_gate: `{plan['fixed_dp_execution_started_by_this_gate']}`",
            f"- candidate_generation_by_camp_allowed: `{plan['candidate_generation_by_camp_allowed']}`",
            f"- training_authorized: `{plan['training_authorized']}`",
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
