#!/usr/bin/env python3
"""Execution preflight for v13 fixed-DP candidate generation.

This gate validates the already-reviewed CAMP-owned fixed-DP runner and emits
an execution runbook for a future gate. It does not run Diffusion Planner,
generate candidates, train CAMP, modify DP, promote, deploy, or make
safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Sequence


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
GUARD_ENV_VAR = "DP_CAMP_V13_FIXED_DP_CANDIDATE_GENERATION_EXECUTE"
RUNNER_SCRIPT = (
    "scripts/integrations/run_diffusion_planner_dp_camp_v13_fixed_candidate_generation.py"
)
SOURCE_SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_"
    "remediation_post_implementation_static_contract_review_v1"
)
SOURCE_READY_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_"
    "remediation_post_implementation_static_contract_review_passed"
)
RUNNER_SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_"
    "remediation_implementation_v1"
)
RUNNER_READY_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_contract_and_input_"
    "remediation_implementation_ready"
)
INPUT_CONTRACT_SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_inputs_materialization_v1"
)
INPUT_CONTRACT_READY_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_execution_inputs_materialized"
)
SCHEMA_VERSION = "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_v1"
READY_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_ready"
REJECT_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_rejected"
DISABLED_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_disabled"
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_execution_contract_and_input_remediation_post_"
    "implementation_static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_only"
)
EXECUTION_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_zero_overlap_validation_only"
)
REMEDIATION_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "runner_contract_remediation_plan_only"
)
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
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
FORBIDDEN_COMMAND_SNIPPETS = (
    "reference_blend",
    "guidance",
    "postprocess",
    "postselection",
    "splice",
    "repair",
    "rewrite",
    "closed_loop",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--post_review_json", type=Path, required=True)
    parser.add_argument("--input_contract_json", type=Path)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--candidate_output_dir", type=Path, required=True)
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
    parser.add_argument("--output_runbook", type=Path, required=True)
    parser.add_argument(
        "--enable_fixed_dp_candidate_generation_execution_preflight",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        post_review_json=args.post_review_json,
        input_contract_json=args.input_contract_json,
        v13_audit_md=args.v13_audit_md,
        candidate_output_dir=args.candidate_output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        dp_repo=args.dp_repo,
        camp_repo=args.camp_repo,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        enabled=args.enable_fixed_dp_candidate_generation_execution_preflight,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_runbook.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    args.output_runbook.write_text(render_runbook(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    post_review_json: Path,
    v13_audit_md: Path,
    candidate_output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    dp_repo: Path = Path("/root/autodl-tmp/Diffusion-Planner"),
    camp_repo: Path = Path("/root/autodl-tmp/camp_core"),
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    enabled: bool,
    input_contract_json: Path | None = None,
) -> dict[str, Any]:
    post_review = _load_json_if_exists(post_review_json)
    source_decision = _dict(post_review.get("final_decision"))
    source_runner_summary = _dict(post_review.get("source_runner_implementation"))
    runner_implementation_json = _path_or_missing(source_runner_summary.get("path"))
    runner_artifact_dir = _path_or_missing(source_runner_summary.get("artifact_dir"))
    runner_implementation = _load_json_if_exists(runner_implementation_json)
    runner_decision = _dict(runner_implementation.get("final_decision"))
    runner_contract = _dict(runner_implementation.get("runner_contract"))
    input_contract_path = _path_or_missing(input_contract_json)
    input_contract_payload = _load_json_if_exists(input_contract_path)
    input_decision = _dict(input_contract_payload.get("final_decision"))
    input_contract = _dict(input_contract_payload.get("input_contract"))
    source_static_review = _dict(runner_implementation.get("source_static_review"))
    source_static_review_json = _path_or_missing(source_static_review.get("path"))
    runner_script = str(runner_contract.get("runner_script") or RUNNER_SCRIPT)
    runner_script_path = _repo_path(camp_repo, runner_script)
    runner_script_text = _read_text_if_exists(runner_script_path)
    source_runner_planned_command = [str(part) for part in _list(runner_contract.get("planned_command"))]
    base_dp_command = _base_dp_command(source_runner_planned_command, input_contract)
    base_dp_command_entrypoint_path = _command_entrypoint_path(dp_repo, base_dp_command)
    candidate_output_dir = candidate_output_dir.resolve()
    planned_command = _planned_command(
        camp_repo=camp_repo,
        runner_script_path=runner_script_path,
        source_static_review_json=source_static_review_json,
        v13_audit_md=v13_audit_md,
        dp_repo=dp_repo,
        candidate_output_dir=candidate_output_dir,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        base_dp_command=base_dp_command,
    )
    if not enabled:
        return _base_report(
            enabled=enabled,
            post_review_json=post_review_json,
            input_contract_json=input_contract_path,
            runner_implementation_json=runner_implementation_json,
            runner_artifact_dir=runner_artifact_dir,
            source_static_review_json=source_static_review_json,
            candidate_output_dir=candidate_output_dir,
            dp_repo=dp_repo,
            camp_repo=camp_repo,
            runner_script=runner_script,
            runner_script_path=runner_script_path,
            source_runner_planned_command=source_runner_planned_command,
            base_dp_command=base_dp_command,
            base_dp_command_entrypoint_path=base_dp_command_entrypoint_path,
            planned_command=planned_command,
            current_camp_head=current_camp_head,
            current_camp_origin_main=current_camp_origin_main,
            current_dp_head=current_dp_head,
            required_dp_head=required_dp_head,
            checks=[],
            passed=False,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        )

    audit_text = _read_text_if_exists(v13_audit_md)
    checks = _checks(
        post_review_json=post_review_json,
        input_contract_json=input_contract_path,
        v13_audit_md=v13_audit_md,
        post_review=post_review,
        source_decision=source_decision,
        source_runner_summary=source_runner_summary,
        input_contract_payload=input_contract_payload,
        input_decision=input_decision,
        input_contract=input_contract,
        runner_implementation_json=runner_implementation_json,
        runner_artifact_dir=runner_artifact_dir,
        runner_implementation=runner_implementation,
        runner_decision=runner_decision,
        runner_contract=runner_contract,
        source_static_review_json=source_static_review_json,
        runner_script_path=runner_script_path,
        runner_script_text=runner_script_text,
        audit_text=audit_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        candidate_output_dir=candidate_output_dir,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        source_runner_planned_command=source_runner_planned_command,
        base_dp_command=base_dp_command,
        base_dp_command_entrypoint_path=base_dp_command_entrypoint_path,
        planned_command=planned_command,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _base_report(
        enabled=enabled,
        post_review_json=post_review_json,
        input_contract_json=input_contract_path,
        runner_implementation_json=runner_implementation_json,
        runner_artifact_dir=runner_artifact_dir,
        source_static_review_json=source_static_review_json,
        candidate_output_dir=candidate_output_dir,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        runner_script=runner_script,
        runner_script_path=runner_script_path,
        source_runner_planned_command=source_runner_planned_command,
        base_dp_command=base_dp_command,
        base_dp_command_entrypoint_path=base_dp_command_entrypoint_path,
        planned_command=planned_command,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        checks=checks,
        passed=passed,
        authorized_current_work=authorized_current_work,
        authorized_next_work=authorized_next_work,
    )


def _checks(
    *,
    post_review_json: Path,
    input_contract_json: Path,
    v13_audit_md: Path,
    post_review: dict[str, Any],
    source_decision: dict[str, Any],
    source_runner_summary: dict[str, Any],
    input_contract_payload: dict[str, Any],
    input_decision: dict[str, Any],
    input_contract: dict[str, Any],
    runner_implementation_json: Path,
    runner_artifact_dir: Path,
    runner_implementation: dict[str, Any],
    runner_decision: dict[str, Any],
    runner_contract: dict[str, Any],
    source_static_review_json: Path,
    runner_script_path: Path,
    runner_script_text: str,
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    candidate_output_dir: Path,
    dp_repo: Path,
    camp_repo: Path,
    source_runner_planned_command: list[str],
    base_dp_command: list[str],
    base_dp_command_entrypoint_path: Path | None,
    planned_command: list[str],
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add = checks.append
    source_command_text = " ".join(source_runner_planned_command).lower()
    planned_command_text = " ".join(planned_command).lower()
    zero_keys = set(_list(runner_contract.get("required_zero_overlap_keys")))
    input_zero_keys = set(_list(input_contract.get("required_zero_overlap_keys")))
    source_output_arg = _option_value(source_runner_planned_command, "--save_predictions_dir")
    base_entrypoint_exists = (
        base_dp_command_entrypoint_path is not None and base_dp_command_entrypoint_path.is_file()
    )

    add(_expect("post_review_json_exists", post_review_json.exists(), True))
    add(_expect("input_contract_json_exists", input_contract_json.is_file(), True))
    add(_expect("v13_audit_exists", v13_audit_md.exists(), True))
    add(_expect("source_schema_version", post_review.get("schema_version"), SOURCE_SCHEMA_VERSION))
    add(_expect("source_status", source_decision.get("status"), SOURCE_READY_STATUS))
    add(_expect("source_passed", source_decision.get("passed"), True))
    add(_expect("source_failed_checks_empty", source_decision.get("failed_checks"), []))
    add(_expect("source_authorized_next_work", source_decision.get("authorized_next_work"), authorized_current_work))
    add(_expect("source_preflight_authorized", source_decision.get("fixed_dp_candidate_generation_execution_preflight_authorized_next"), True))
    add(
        _expect(
            "source_post_review_passed",
            source_decision.get(
                "fixed_dp_candidate_generation_execution_contract_and_input_remediation_post_implementation_static_contract_review_passed"
            ),
            True,
        )
    )
    for flag in SOURCE_FALSE_FLAGS:
        add(_expect(f"source_forbids_{flag}", source_decision.get(flag), False))
    add(_expect("source_candidate_operation", source_decision.get("candidate_operation"), "fixed DP candidate reranking only"))
    add(_expect("source_score_expression", source_decision.get("score_expression"), SCORE_EXPRESSION))

    add(_expect("input_contract_schema_version", input_contract_payload.get("schema_version"), INPUT_CONTRACT_SCHEMA_VERSION))
    add(_expect("input_contract_status", input_decision.get("status"), INPUT_CONTRACT_READY_STATUS))
    add(_expect("input_contract_passed", input_decision.get("passed"), True))
    add(_expect("input_contract_failed_checks_empty", input_decision.get("failed_checks"), []))
    add(_expect("input_contract_no_fixed_dp_execution", input_decision.get("fixed_dp_candidate_generation_executed"), False))
    add(_expect("input_contract_no_camp_generation", input_decision.get("candidate_generation_by_camp_authorized"), False))
    add(_expect("input_contract_no_dp_modification", input_decision.get("dp_modification_authorized"), False))
    add(_expect("input_contract_valid_set_list_exists", _path_or_missing(input_contract.get("valid_set_list")).is_file(), True))
    add(_expect("input_contract_valid_set_list_nonempty", bool(_list(input_contract.get("valid_set_files"))), True))
    add(_expect("input_contract_fixed_dp_checkpoint_exists", _path_or_missing(input_contract.get("fixed_dp_checkpoint")).is_file(), True))
    add(_expect("input_contract_fixed_dp_args_json_exists", _path_or_missing(input_contract.get("fixed_dp_args_json")).is_file(), True))
    add(_expect("input_contract_closed_loop_not_read", input_contract.get("closed_loop_outcome_read"), False))
    add(_expect("input_contract_dp_modification_false", input_contract.get("dp_modification"), False))
    for key in ZERO_OVERLAP_KEYS:
        add(_expect(f"input_contract_requires_zero_overlap_{key}", key in input_zero_keys, True))

    add(_expect("runner_implementation_json_exists", runner_implementation_json.exists(), True))
    add(_expect("runner_artifact_dir_exists", runner_artifact_dir.exists(), True))
    add(_expect("runner_summary_schema_version", source_runner_summary.get("schema_version"), RUNNER_SCHEMA_VERSION))
    add(_expect("runner_summary_status", source_runner_summary.get("status"), RUNNER_READY_STATUS))
    add(_expect("runner_summary_passed", source_runner_summary.get("passed"), True))
    add(_expect("runner_schema_version", runner_implementation.get("schema_version"), RUNNER_SCHEMA_VERSION))
    add(_expect("runner_status", runner_decision.get("status"), RUNNER_READY_STATUS))
    add(_expect("runner_passed", runner_decision.get("passed"), True))
    add(_expect("runner_failed_checks_empty", runner_decision.get("failed_checks"), []))
    add(_expect("runner_source_static_review_exists", source_static_review_json.exists(), True))
    add(_expect("runner_script_contract", runner_contract.get("runner_script"), RUNNER_SCRIPT))
    add(_expect("runner_script_exists", runner_script_path.exists(), True))
    add(_expect("runner_contract_guard_env", runner_contract.get("guard_env_var"), GUARD_ENV_VAR))
    add(_expect("runner_contract_execution_false", runner_contract.get("fixed_dp_candidate_generation_executed"), False))
    add(_expect("runner_contract_candidate_generation_by_camp_false", runner_contract.get("candidate_generation_by_camp"), False))
    add(_expect("runner_contract_dp_modification_false", runner_contract.get("dp_modification"), False))
    add(_expect("runner_script_does_not_hard_reject_execute", "runner_is_default_off_for_this_gate" in runner_script_text, False))
    for key in ZERO_OVERLAP_KEYS:
        add(_expect(f"runner_contract_requires_zero_overlap_{key}", key in zero_keys, True))

    add(_expect("camp_repo_exists", camp_repo.is_dir(), True))
    add(_expect("dp_repo_exists", dp_repo.is_dir(), True))
    add(_expect("candidate_output_dir_absent", candidate_output_dir.exists(), False))
    add(_expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main))
    add(_expect("current_dp_head_fixed", current_dp_head, required_dp_head))
    add(_expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD))
    add(_expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS))
    add(_expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work))
    add(_expect("audit_authorizes_preflight", _latest_value(audit_text, "fixed_dp_candidate_generation_execution_preflight_authorized_next"), "True"))
    for flag in AUDIT_FALSE_FLAGS:
        add(_expect(f"audit_forbids_{flag}", _latest_value(audit_text, flag), "False"))

    add(_expect("runner_contract_required_fixed_dp_head", runner_contract.get("required_fixed_dp_head"), FIXED_DP_HEAD))
    add(_expect("runner_contract_forbids_full36", runner_contract.get("forbid_full36"), True))
    add(_expect("runner_contract_forbids_formal_seeds", runner_contract.get("forbidden_formal_seeds"), ["11", "12", "13"]))
    add(_expect("runner_contract_writes_zero_overlap_registries", runner_contract.get("write_zero_overlap_registries"), True))
    add(_expect("source_runner_command_uses_valid_predictor", _uses_valid_dp_export_entrypoint(source_runner_planned_command), True))
    add(_expect("source_runner_command_has_valid_set_list", "--valid_set_list" in source_runner_planned_command, True))
    add(_expect("source_runner_command_has_resume_model_path", "--resume_model_path" in source_runner_planned_command, True))
    add(_expect("source_runner_command_has_args_json_path", "--args_json_path" in source_runner_planned_command, True))
    add(_expect("source_runner_command_has_save_predictions_dir", source_output_arg is not None, True))
    add(_expect("source_runner_command_does_not_use_planner_generate_placeholder", "planner_generate.py" in source_command_text, False))
    add(_expect("base_dp_command_nonempty", bool(base_dp_command), True))
    add(_expect("base_dp_command_strips_save_predictions_dir", "--save_predictions_dir" in base_dp_command, False))
    add(_expect("base_dp_command_uses_valid_predictor", _uses_valid_dp_export_entrypoint(base_dp_command), True))
    add(_expect("base_dp_command_entrypoint_exists", base_entrypoint_exists, True))

    add(_expect("planned_command_uses_guard", GUARD_ENV_VAR.lower() in planned_command_text, True))
    add(_expect("planned_command_uses_camp_runner", str(runner_script_path) in " ".join(planned_command), True))
    add(_expect("planned_command_uses_source_static_review", str(source_static_review_json) in " ".join(planned_command), True))
    add(_expect("planned_command_uses_execute", "--execute" in planned_command, True))
    add(_expect("planned_command_delegates_dp_command", "--dp_command" in planned_command, True))
    add(_expect("planned_command_has_required_dp_head", FIXED_DP_HEAD in planned_command, True))
    add(_expect("planned_command_sets_execution_gate_work", AUTHORIZED_NEXT_WORK in planned_command, True))
    add(_expect("planned_command_sets_execution_next_work", EXECUTION_NEXT_WORK in planned_command, True))
    for snippet in FORBIDDEN_COMMAND_SNIPPETS:
        combined = f"{source_command_text} {planned_command_text}"
        add(_expect(f"planned_command_forbids_{_slug(snippet)}", snippet in combined, False))
    return checks


def _base_report(
    *,
    enabled: bool,
    post_review_json: Path,
    input_contract_json: Path,
    runner_implementation_json: Path,
    runner_artifact_dir: Path,
    source_static_review_json: Path,
    candidate_output_dir: Path,
    dp_repo: Path,
    camp_repo: Path,
    runner_script: str,
    runner_script_path: Path,
    source_runner_planned_command: list[str],
    base_dp_command: list[str],
    base_dp_command_entrypoint_path: Path | None,
    planned_command: list[str],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    checks: list[dict[str, Any]],
    passed: bool,
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "enabled": enabled,
            "execution_preflight_only": True,
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
            "promotion": False,
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
        "source_artifacts": {
            "post_review_json": str(post_review_json),
            "post_review_json_sha256": _sha256(post_review_json) if post_review_json.is_file() else None,
            "input_contract_json": str(input_contract_json),
            "input_contract_json_sha256": _sha256(input_contract_json)
            if input_contract_json.is_file()
            else None,
            "runner_implementation_json": str(runner_implementation_json),
            "runner_implementation_json_sha256": _sha256(runner_implementation_json)
            if runner_implementation_json.is_file()
            else None,
            "runner_artifact_dir": str(runner_artifact_dir),
            "source_static_review_json": str(source_static_review_json),
            "source_static_review_json_sha256": _sha256(source_static_review_json)
            if source_static_review_json.is_file()
            else None,
        },
        "execution_preflight": {
            "candidate_output_dir": str(candidate_output_dir),
            "candidate_output_dir_exists": candidate_output_dir.exists(),
            "dp_repo": str(dp_repo),
            "camp_repo": str(camp_repo),
            "runner_script": runner_script,
            "runner_script_path": str(runner_script_path),
            "runner_script_exists": runner_script_path.exists(),
            "base_dp_command": base_dp_command,
            "base_dp_command_entrypoint_path": str(base_dp_command_entrypoint_path)
            if base_dp_command_entrypoint_path is not None
            else None,
            "base_dp_command_entrypoint_exists": (
                base_dp_command_entrypoint_path is not None and base_dp_command_entrypoint_path.is_file()
            ),
            "guard_env_var": GUARD_ENV_VAR,
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
            "source_runner_planned_command": source_runner_planned_command,
            "planned_command": planned_command,
        },
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            enabled=enabled,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def _decision(
    *,
    passed: bool,
    failed: list[str],
    enabled: bool,
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    if not enabled:
        status = DISABLED_STATUS
    else:
        status = READY_STATUS if passed else REJECT_STATUS
    return {
        "status": status,
        "enabled": enabled,
        "passed": passed,
        "failed_checks": failed,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "recommended_next_work": None if passed or not enabled else REMEDIATION_NEXT_WORK,
        "failure_class": None if passed else ("disabled" if not enabled else _failure_class(failed)),
        "fixed_dp_candidate_generation_execution_preflight_passed": passed,
        "fixed_dp_candidate_generation_authorized_next": passed,
        "fixed_dp_candidate_generation_execution_authorized_next": passed,
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
    preflight = _dict(report.get("execution_preflight"))
    failed = decision.get("failed_checks") or []
    return "\n".join(
        [
            "# Fixed-DP Candidate Generation Execution Preflight",
            "",
            f"- Status: `{decision.get('status')}`",
            f"- Passed: `{decision.get('passed')}`",
            f"- Failed checks: `{failed}`",
            f"- Failure class: `{decision.get('failure_class')}`",
            f"- Authorized next work: `{decision.get('authorized_next_work')}`",
            f"- Recommended next work: `{decision.get('recommended_next_work')}`",
            f"- Candidate output dir: `{preflight.get('candidate_output_dir')}`",
            f"- Runner script path: `{preflight.get('runner_script_path')}`",
            f"- Runner script exists: `{preflight.get('runner_script_exists')}`",
            f"- Base DP command entrypoint: `{preflight.get('base_dp_command_entrypoint_path')}`",
            f"- Base DP command entrypoint exists: `{preflight.get('base_dp_command_entrypoint_exists')}`",
            f"- Fixed-DP generation executed: `{decision.get('fixed_dp_candidate_generation_executed')}`",
            f"- CAMP candidate generation authorized: `{decision.get('candidate_generation_by_camp_authorized')}`",
            f"- Training preflight authorized next: `{decision.get('training_preflight_authorized_next')}`",
            f"- DP modification authorized: `{decision.get('dp_modification_authorized')}`",
            f"- Candidate operation: `{decision.get('candidate_operation')}`",
            f"- Score expression: `{decision.get('score_expression')}`",
            "",
        ]
    )


def render_runbook(report: dict[str, Any]) -> str:
    decision = _dict(report.get("final_decision"))
    preflight = _dict(report.get("execution_preflight"))
    command = _list(preflight.get("planned_command"))
    command_text = " ".join(_shell_quote(str(part)) for part in command)
    failed = ",".join(str(item) for item in _list(decision.get("failed_checks")))
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Generated by the execution preflight. It must only run after this",
        "# preflight passes and the audit EOF authorizes the execution gate.",
        f"if [ \"{str(decision.get('passed'))}\" != \"True\" ]; then",
        f"  echo 'Refusing to run: preflight did not pass ({failed})' >&2",
        "  exit 39",
        "fi",
        f"if [ \"${{{GUARD_ENV_VAR}:-}}\" != \"1\" ]; then",
        f"  echo 'Refusing to run: set {GUARD_ENV_VAR}=1 in the execution gate' >&2",
        "  exit 40",
        "fi",
        "source /etc/network_turbo >/dev/null 2>&1 || true",
        f"if [ \"$(git -C {_shell_quote(str(preflight.get('camp_repo')))} rev-parse HEAD)\" != {_shell_quote(str(report.get('heads', {}).get('current_camp_head', '')))} ]; then",
        "  echo 'CAMP HEAD mismatch' >&2",
        "  exit 41",
        "fi",
        f"if [ \"$(git -C {_shell_quote(str(preflight.get('dp_repo')))} rev-parse HEAD)\" != {_shell_quote(FIXED_DP_HEAD)} ]; then",
        "  echo 'DP HEAD mismatch' >&2",
        "  exit 42",
        "fi",
        f"if [ -e {_shell_quote(str(preflight.get('candidate_output_dir')))} ]; then",
        "  echo 'Candidate output dir already exists' >&2",
        "  exit 43",
        "fi",
        command_text,
        "",
    ]
    return "\n".join(lines)


def _planned_command(
    *,
    camp_repo: Path,
    runner_script_path: Path,
    source_static_review_json: Path,
    v13_audit_md: Path,
    dp_repo: Path,
    candidate_output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    base_dp_command: list[str],
) -> list[str]:
    runner_json = candidate_output_dir.parent / f"{candidate_output_dir.name}_runner_execution.json"
    runner_md = candidate_output_dir.parent / f"{candidate_output_dir.name}_runner_execution.md"
    return [
        "env",
        f"{GUARD_ENV_VAR}=1",
        "python",
        str(runner_script_path),
        "--implementation_static_contract_review_json",
        str(source_static_review_json),
        "--v13_audit_md",
        str(v13_audit_md),
        "--dp_repo",
        str(dp_repo),
        "--camp_repo",
        str(camp_repo),
        "--output_dir",
        str(candidate_output_dir),
        "--current_camp_head",
        current_camp_head,
        "--current_camp_origin_main",
        current_camp_origin_main,
        "--current_dp_head",
        current_dp_head,
        "--required_dp_head",
        required_dp_head,
        "--authorized_current_work",
        AUTHORIZED_NEXT_WORK,
        "--authorized_next_work",
        EXECUTION_NEXT_WORK,
        "--output_json",
        str(runner_json),
        "--output_md",
        str(runner_md),
        "--execute",
        "--dp_command",
        *base_dp_command,
    ]


def _base_dp_command(source_runner_planned_command: list[str], input_contract: dict[str, Any]) -> list[str]:
    if input_contract:
        return [
            "python",
            "-m",
            "torch.distributed.run",
            "--nnodes",
            "1",
            "--nproc-per-node",
            "1",
            "--standalone",
            "diffusion_planner/valid_predictor.py",
            "--valid_set_list",
            str(input_contract.get("valid_set_list")),
            "--resume_model_path",
            str(input_contract.get("fixed_dp_checkpoint")),
            "--args_json_path",
            str(input_contract.get("fixed_dp_args_json")),
        ]
    if "--output_dir" not in source_runner_planned_command:
        return _without_option_value(source_runner_planned_command, "--save_predictions_dir")
    return _without_option_value(
        list(source_runner_planned_command[: source_runner_planned_command.index("--output_dir")]),
        "--save_predictions_dir",
    )


def _command_entrypoint_path(dp_repo: Path, command: list[str]) -> Path | None:
    for part in command:
        text = str(part).replace("\\", "/")
        if text.endswith(".py"):
            path = Path(part)
            return path if path.is_absolute() else dp_repo / path
    if not command:
        return None
    executable = Path(command[0]).name.lower()
    if executable.startswith("python"):
        return None
    path = Path(command[0])
    return path if path.is_absolute() else dp_repo / path


def _uses_valid_dp_export_entrypoint(command: Sequence[str]) -> bool:
    return any(str(part).replace("\\", "/") == "diffusion_planner/valid_predictor.py" for part in command)


def _option_value(command: Sequence[str], option: str) -> str | None:
    parts = [str(part) for part in command]
    if option not in parts:
        return None
    index = parts.index(option)
    if index + 1 >= len(parts):
        return None
    return parts[index + 1]


def _without_option_value(command: Sequence[str], option: str) -> list[str]:
    result: list[str] = []
    skip_next = False
    for part in command:
        if skip_next:
            skip_next = False
            continue
        if part == option:
            skip_next = True
            continue
        result.append(str(part))
    return result


def _repo_path(repo: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo / path


def _path_or_missing(value: Any) -> Path:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    return Path("__missing_path__")


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object at {path}")
    return payload


def _read_text_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


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


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _failure_class(failed: list[str]) -> str:
    if any("runner_script_does_not_hard_reject_execute" in check for check in failed):
        return "runner_execution_contract_not_authorized"
    if any("base_dp_command" in check for check in failed):
        return "missing_fixed_dp_candidate_generation_command"
    if any("audit" in check for check in failed):
        return "audit_authorization_mismatch"
    if any("source" in check or "runner" in check for check in failed):
        return "source_runner_artifact_contract_mismatch"
    return "execution_preflight_contract_failure"


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
