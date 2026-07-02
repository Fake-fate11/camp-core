#!/usr/bin/env python3
"""Execution preflight for v13 fixed-DP candidate generation.

This gate validates the prior fixed-DP candidate-generation builder and
post-implementation review artifacts, then emits an execution runbook for a
future gate. It does not run Diffusion Planner, generate candidates, train
CAMP, modify DP, promote, deploy, or make safety/CAMP-over-DP claims.
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
GUARD_ENV_VAR = "DP_CAMP_V13_FIXED_DP_CANDIDATE_GENERATION_EXECUTE"
SOURCE_SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_post_implementation_static_contract_review_v1"
)
SOURCE_READY_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_post_implementation_static_contract_review_passed"
)
BUILDER_SCHEMA_VERSION = "dp_camp_v13_fixed_dp_candidate_generation_builder_v1"
BUILDER_READY_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_builder_complete"
MANIFEST_SCHEMA_VERSION = "dp_camp_v13_fixed_dp_candidate_generation_manifest_v1"
SCHEMA_VERSION = "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_v1"
READY_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_ready"
REJECT_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_rejected"
DISABLED_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_execution_preflight_disabled"
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_post_implementation_static_contract_review_passed"
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
REMEDIATION_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_execution_preflight_"
    "entrypoint_contract_remediation_plan_only"
)
TARGET_MIN_CANDIDATE_MEMBERS = 1024
TARGET_CANDIDATES_PER_MEMBER = 8
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
    "--candidate_reference_blend_steps",
    "--candidate_guidance_config",
    "--candidate_guidance_scale",
    "--camp_traffic_light_hybrid_postselection",
    "--camp_underprogress_relaxation",
    "--camp_splice_shadow_rule",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--post_review_json", type=Path, required=True)
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
) -> dict[str, Any]:
    post_review = _load_json_if_exists(post_review_json)
    source_decision = _dict(post_review.get("final_decision"))
    source_summary = _dict(post_review.get("artifact_summary"))
    builder_json = Path(str(source_summary.get("builder_json", "")))
    builder_artifact_dir = Path(str(source_summary.get("builder_artifact_dir", "")))
    manifest_path = Path(str(source_summary.get("manifest_path", "")))
    builder_runbook_path = Path(str(source_summary.get("runbook_path", "")))
    builder = _load_json_if_exists(builder_json)
    builder_decision = _dict(builder.get("final_decision"))
    generation_builder = _dict(builder.get("generation_builder"))
    manifest = _load_json_if_exists(manifest_path)
    builder_runbook = _read_text_if_exists(builder_runbook_path)
    audit_text = _read_text_if_exists(v13_audit_md)
    dp_entrypoint = str(manifest.get("dp_entrypoint", ""))
    dp_entrypoint_path = _entrypoint_path(dp_repo, dp_entrypoint)
    candidate_output_dir = candidate_output_dir.resolve()
    planned_command = _planned_command(
        dp_repo=dp_repo,
        dp_entrypoint=dp_entrypoint,
        candidate_output_dir=candidate_output_dir,
        target_min_candidate_members=int(manifest.get("target_min_candidate_members") or 0),
        target_candidates_per_member=int(manifest.get("target_candidates_per_member") or 0),
        required_dp_head=required_dp_head,
    )
    if not enabled:
        return _base_report(
            enabled=enabled,
            post_review_json=post_review_json,
            builder_json=builder_json,
            builder_artifact_dir=builder_artifact_dir,
            manifest_path=manifest_path,
            builder_runbook_path=builder_runbook_path,
            candidate_output_dir=candidate_output_dir,
            dp_repo=dp_repo,
            camp_repo=camp_repo,
            dp_entrypoint=dp_entrypoint,
            dp_entrypoint_path=dp_entrypoint_path,
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

    checks = _checks(
        post_review_json=post_review_json,
        v13_audit_md=v13_audit_md,
        post_review=post_review,
        source_decision=source_decision,
        builder_json=builder_json,
        builder_artifact_dir=builder_artifact_dir,
        builder=builder,
        builder_decision=builder_decision,
        generation_builder=generation_builder,
        manifest_path=manifest_path,
        manifest=manifest,
        builder_runbook_path=builder_runbook_path,
        builder_runbook=builder_runbook,
        audit_text=audit_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        candidate_output_dir=candidate_output_dir,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        dp_entrypoint=dp_entrypoint,
        dp_entrypoint_path=dp_entrypoint_path,
        planned_command=planned_command,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _base_report(
        enabled=enabled,
        post_review_json=post_review_json,
        builder_json=builder_json,
        builder_artifact_dir=builder_artifact_dir,
        manifest_path=manifest_path,
        builder_runbook_path=builder_runbook_path,
        candidate_output_dir=candidate_output_dir,
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        dp_entrypoint=dp_entrypoint,
        dp_entrypoint_path=dp_entrypoint_path,
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
    v13_audit_md: Path,
    post_review: dict[str, Any],
    source_decision: dict[str, Any],
    builder_json: Path,
    builder_artifact_dir: Path,
    builder: dict[str, Any],
    builder_decision: dict[str, Any],
    generation_builder: dict[str, Any],
    manifest_path: Path,
    manifest: dict[str, Any],
    builder_runbook_path: Path,
    builder_runbook: str,
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    candidate_output_dir: Path,
    dp_repo: Path,
    camp_repo: Path,
    dp_entrypoint: str,
    dp_entrypoint_path: Path,
    planned_command: list[str],
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add = checks.append
    add(_expect("post_review_json_exists", post_review_json.exists(), True))
    add(_expect("v13_audit_exists", v13_audit_md.exists(), True))
    add(_expect("source_schema_version", post_review.get("schema_version"), SOURCE_SCHEMA_VERSION))
    add(_expect("source_status", source_decision.get("status"), SOURCE_READY_STATUS))
    add(_expect("source_passed", source_decision.get("passed"), True))
    add(_expect("source_failed_checks_empty", source_decision.get("failed_checks"), []))
    add(_expect("source_authorized_next_work", source_decision.get("authorized_next_work"), authorized_current_work))
    add(_expect("source_preflight_authorized", source_decision.get("fixed_dp_candidate_generation_execution_preflight_authorized_next"), True))
    add(_expect("source_post_review_passed", source_decision.get("fixed_dp_candidate_generation_post_implementation_static_contract_review_passed"), True))
    for flag in SOURCE_FALSE_FLAGS:
        add(_expect(f"source_forbids_{flag}", source_decision.get(flag), False))
    add(_expect("source_candidate_operation", source_decision.get("candidate_operation"), "fixed DP candidate reranking only"))
    add(_expect("source_score_expression", source_decision.get("score_expression"), SCORE_EXPRESSION))
    add(_expect("builder_json_exists", builder_json.exists(), True))
    add(_expect("builder_artifact_dir_exists", builder_artifact_dir.exists(), True))
    add(_expect("builder_schema_version", builder.get("schema_version"), BUILDER_SCHEMA_VERSION))
    add(_expect("builder_status", builder_decision.get("status"), BUILDER_READY_STATUS))
    add(_expect("builder_passed", builder_decision.get("passed"), True))
    add(_expect("builder_generation_not_executed", builder_decision.get("fixed_dp_candidate_generation_executed"), False))
    add(_expect("builder_manifest_written", generation_builder.get("manifest_written"), True))
    add(_expect("builder_guard_env_var", generation_builder.get("runbook_guard_env_var"), GUARD_ENV_VAR))
    add(_expect("manifest_exists", manifest_path.exists(), True))
    add(_expect("builder_runbook_exists", builder_runbook_path.exists(), True))
    add(_expect("manifest_schema_version", manifest.get("schema_version"), MANIFEST_SCHEMA_VERSION))
    add(_expect("manifest_fixed_dp_generation_not_executed", manifest.get("fixed_dp_candidate_generation_executed"), False))
    add(_expect("manifest_candidate_generation_by_camp_false", manifest.get("candidate_generation_by_camp"), False))
    add(_expect("manifest_dp_modification_false", manifest.get("dp_modification"), False))
    add(_expect("manifest_required_dp_head", manifest.get("required_dp_head"), FIXED_DP_HEAD))
    add(_expect("manifest_target_members_at_least_1000", int(manifest.get("target_min_candidate_members") or 0) >= TARGET_MIN_CANDIDATE_MEMBERS, True))
    add(_expect("manifest_candidates_per_member", int(manifest.get("target_candidates_per_member") or 0), TARGET_CANDIDATES_PER_MEMBER))
    manifest_zero_keys = set(_list(manifest.get("required_zero_overlap_keys")))
    builder_zero_keys = set(_list(generation_builder.get("required_zero_overlap_keys")))
    for key in ZERO_OVERLAP_KEYS:
        add(_expect(f"manifest_requires_zero_overlap_{key}", key in manifest_zero_keys, True))
        add(_expect(f"builder_requires_zero_overlap_{key}", key in builder_zero_keys, True))
    add(_expect("builder_runbook_guard_env_present", GUARD_ENV_VAR in builder_runbook, True))
    add(_expect("builder_runbook_checks_dp_head", "DP HEAD mismatch" in builder_runbook, True))
    add(_expect("builder_runbook_forbids_formal_seeds", "--forbid_formal_seeds 11 12 13" in builder_runbook, True))
    add(_expect("builder_runbook_writes_zero_overlap_registries", "--write_zero_overlap_registries" in builder_runbook, True))
    add(_expect("camp_repo_exists", camp_repo.is_dir(), True))
    add(_expect("dp_repo_exists", dp_repo.is_dir(), True))
    add(_expect("dp_entrypoint_manifest_nonempty", bool(dp_entrypoint), True))
    add(_expect("dp_entrypoint_manifest_relative", bool(dp_entrypoint) and not Path(dp_entrypoint).is_absolute(), True))
    add(_expect("dp_entrypoint_exists", dp_entrypoint_path.is_file(), True))
    add(_expect("candidate_output_dir_absent", candidate_output_dir.exists(), False))
    add(_expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main))
    add(_expect("current_dp_head_fixed", current_dp_head, required_dp_head))
    add(_expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD))
    add(_expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS))
    add(_expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work))
    add(_expect("audit_authorizes_preflight", _latest_value(audit_text, "fixed_dp_candidate_generation_execution_preflight_authorized_next"), "True"))
    for flag in AUDIT_FALSE_FLAGS:
        add(_expect(f"audit_forbids_{flag}", _latest_value(audit_text, flag), "False"))
    command_text = " ".join(planned_command)
    add(_expect("planned_command_uses_guard", GUARD_ENV_VAR in command_text, True))
    add(_expect("planned_command_uses_fixed_dp_entrypoint", str(dp_entrypoint_path) in command_text, True))
    add(_expect("planned_command_forbids_full36", "--forbid_full36" in planned_command, True))
    add(_expect("planned_command_forbids_formal_seeds", "--forbid_formal_seeds" in planned_command and "11" in planned_command and "12" in planned_command and "13" in planned_command, True))
    add(_expect("planned_command_writes_zero_overlap_registries", "--write_zero_overlap_registries" in planned_command, True))
    add(_expect("planned_command_candidate_operation", "fixed DP candidate reranking only" in planned_command, True))
    add(_expect("planned_command_score_affine", SCORE_EXPRESSION in planned_command, True))
    for snippet in FORBIDDEN_COMMAND_SNIPPETS:
        add(_expect(f"planned_command_forbids_{_slug(snippet)}", snippet in command_text, False))
    return checks


def _base_report(
    *,
    enabled: bool,
    post_review_json: Path,
    builder_json: Path,
    builder_artifact_dir: Path,
    manifest_path: Path,
    builder_runbook_path: Path,
    candidate_output_dir: Path,
    dp_repo: Path,
    camp_repo: Path,
    dp_entrypoint: str,
    dp_entrypoint_path: Path,
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
            "builder_json": str(builder_json),
            "builder_json_sha256": _sha256(builder_json) if builder_json.is_file() else None,
            "builder_artifact_dir": str(builder_artifact_dir),
            "manifest_path": str(manifest_path),
            "manifest_sha256": _sha256(manifest_path) if manifest_path.is_file() else None,
            "builder_runbook_path": str(builder_runbook_path),
            "builder_runbook_sha256": _sha256(builder_runbook_path) if builder_runbook_path.is_file() else None,
        },
        "execution_preflight": {
            "candidate_output_dir": str(candidate_output_dir),
            "candidate_output_dir_exists": candidate_output_dir.exists(),
            "dp_repo": str(dp_repo),
            "camp_repo": str(camp_repo),
            "dp_entrypoint": dp_entrypoint,
            "dp_entrypoint_path": str(dp_entrypoint_path),
            "dp_entrypoint_exists": dp_entrypoint_path.is_file(),
            "guard_env_var": GUARD_ENV_VAR,
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
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
            f"- DP entrypoint path: `{preflight.get('dp_entrypoint_path')}`",
            f"- DP entrypoint exists: `{preflight.get('dp_entrypoint_exists')}`",
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
    dp_repo: Path,
    dp_entrypoint: str,
    candidate_output_dir: Path,
    target_min_candidate_members: int,
    target_candidates_per_member: int,
    required_dp_head: str,
) -> list[str]:
    entrypoint = _entrypoint_path(dp_repo, dp_entrypoint)
    return [
        "env",
        f"{GUARD_ENV_VAR}=1",
        "python",
        str(entrypoint),
        "--output_dir",
        str(candidate_output_dir),
        "--target_min_candidate_members",
        str(target_min_candidate_members),
        "--target_candidates_per_member",
        str(target_candidates_per_member),
        "--forbid_full36",
        "--forbid_formal_seeds",
        "11",
        "12",
        "13",
        "--fixed_dp_head",
        required_dp_head,
        "--candidate_operation",
        "fixed DP candidate reranking only",
        "--score_expression",
        SCORE_EXPRESSION,
        "--write_zero_overlap_registries",
    ]


def _entrypoint_path(dp_repo: Path, dp_entrypoint: str) -> Path:
    if not dp_entrypoint:
        return dp_repo
    path = Path(dp_entrypoint)
    return path if path.is_absolute() else dp_repo / path


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
    if any("dp_entrypoint" in check for check in failed):
        return "missing_fixed_dp_candidate_generation_entrypoint"
    if any("audit" in check for check in failed):
        return "audit_authorization_mismatch"
    if any("source" in check or "builder" in check or "manifest" in check for check in failed):
        return "source_artifact_contract_mismatch"
    return "execution_preflight_contract_failure"


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
