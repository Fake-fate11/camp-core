#!/usr/bin/env python3
"""Read-only preflight for the v13 fresh evaluation split manifest.

This gate validates fixed manifest-builder outputs and the referenced registry
files before any later evaluation execution is considered. It does not run
Diffusion Planner, generate candidates, replay, train CAMP, modify DP, promote
artifacts, deploy, or make safety/CAMP-over-DP claims.
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
SCHEMA_VERSION = "dp_camp_v13_fresh_evaluation_split_preflight_v1"
PASS_STATUS = "dp_camp_v13_fresh_evaluation_split_preflight_passed"
REJECT_STATUS = "dp_camp_v13_fresh_evaluation_split_preflight_rejected"
SOURCE_BUILDER_SCHEMA_VERSION = "dp_camp_v13_fresh_evaluation_split_manifest_builder_v1"
SOURCE_BUILDER_STATUS = "dp_camp_v13_fresh_evaluation_split_manifest_builder_complete"
SOURCE_BUILDER_AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_post_implementation_static_contract_"
    "review_only"
)
SCOPE_MANIFEST_SCHEMA_VERSION = "dp_camp_v13_fresh_evaluation_split_scope_manifest_v1"
REGISTRY_REPORT_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_nonoverlap_registry_report_v1"
)
MEMBER_SOURCE_VALIDATION_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_validation_preflight_v1"
)
MEMBER_SOURCE_VALIDATION_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_validation_preflight_passed"
)
MEMBER_SOURCE_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_manifest_v1"
)
MEMBER_SOURCE_NONOVERLAP_REPORT_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_nonoverlap_report_v1"
)
MEMBER_SOURCE_PREFLIGHT_INPUTS_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_preflight_inputs_v1"
)
SOURCE_REGISTRY_SCHEMA_VERSION = (
    "dp_camp_v13_current_source_result_review_source_registry_manifest_v1"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_manifest_builder_post_implementation_static_contract_review_complete"
)
MEMBER_SOURCE_REMEDIATION_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_remediation_validation_preflight_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_preflight_only"
)
MEMBER_SOURCE_REMEDIATION_AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "fresh_evaluation_split_preflight_only"
)
AUTHORIZED_PASS_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_static_contract_review_only"
)
AUTHORIZED_REMEDIATION_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_plan_only"
)
TARGET_SELECTION_LOGS = 32
TARGET_RECORDS = 3200
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14
FORMAL_SEEDS = {11, 12, 13}
ZERO_INTERSECTION_KEYS = (
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
BLOCKED_FLAGS = (
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
    parser = argparse.ArgumentParser(
        description="Read-only v13 fresh evaluation split preflight."
    )
    parser.add_argument("--manifest_builder_json", type=Path)
    parser.add_argument("--expected_manifest_builder_json_sha256")
    parser.add_argument("--scope_manifest_json", type=Path)
    parser.add_argument("--nonoverlap_registry_report_json", type=Path)
    parser.add_argument("--member_source_validation_json", type=Path)
    parser.add_argument("--expected_member_source_validation_json_sha256")
    parser.add_argument("--member_source_manifest_json", type=Path)
    parser.add_argument("--member_source_nonoverlap_report_json", type=Path)
    parser.add_argument("--member_source_preflight_inputs_json", type=Path)
    parser.add_argument("--sha256sums_txt", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_pass_next_work", default=AUTHORIZED_PASS_NEXT_WORK)
    parser.add_argument(
        "--authorized_remediation_next_work",
        default=AUTHORIZED_REMEDIATION_NEXT_WORK,
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if _has_member_source_args(args):
        report = build_member_source_remediation_report(
            member_source_validation_json=_required_path(
                args.member_source_validation_json,
                "--member_source_validation_json",
            ),
            expected_member_source_validation_json_sha256=_required_str(
                args.expected_member_source_validation_json_sha256,
                "--expected_member_source_validation_json_sha256",
            ),
            member_source_manifest_json=_required_path(
                args.member_source_manifest_json,
                "--member_source_manifest_json",
            ),
            member_source_nonoverlap_report_json=_required_path(
                args.member_source_nonoverlap_report_json,
                "--member_source_nonoverlap_report_json",
            ),
            member_source_preflight_inputs_json=_required_path(
                args.member_source_preflight_inputs_json,
                "--member_source_preflight_inputs_json",
            ),
            sha256sums_txt=args.sha256sums_txt,
            v13_audit_md=args.v13_audit_md,
            current_camp_head=args.current_camp_head,
            current_camp_origin_main=args.current_camp_origin_main,
            current_dp_head=args.current_dp_head,
            required_dp_head=args.required_dp_head,
            authorized_current_work=(
                args.authorized_current_work
                if args.authorized_current_work != AUTHORIZED_CURRENT_WORK
                else MEMBER_SOURCE_REMEDIATION_AUTHORIZED_CURRENT_WORK
            ),
            authorized_pass_next_work=args.authorized_pass_next_work,
            authorized_remediation_next_work=args.authorized_remediation_next_work,
        )
    else:
        report = build_report(
            manifest_builder_json=_required_path(
                args.manifest_builder_json,
                "--manifest_builder_json",
            ),
            expected_manifest_builder_json_sha256=_required_str(
                args.expected_manifest_builder_json_sha256,
                "--expected_manifest_builder_json_sha256",
            ),
            scope_manifest_json=_required_path(
                args.scope_manifest_json,
                "--scope_manifest_json",
            ),
            nonoverlap_registry_report_json=_required_path(
                args.nonoverlap_registry_report_json,
                "--nonoverlap_registry_report_json",
            ),
            sha256sums_txt=args.sha256sums_txt,
            v13_audit_md=args.v13_audit_md,
            current_camp_head=args.current_camp_head,
            current_camp_origin_main=args.current_camp_origin_main,
            current_dp_head=args.current_dp_head,
            required_dp_head=args.required_dp_head,
            authorized_current_work=args.authorized_current_work,
            authorized_pass_next_work=args.authorized_pass_next_work,
            authorized_remediation_next_work=args.authorized_remediation_next_work,
        )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0


def build_report(
    *,
    manifest_builder_json: Path,
    expected_manifest_builder_json_sha256: str,
    scope_manifest_json: Path,
    nonoverlap_registry_report_json: Path,
    sha256sums_txt: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_pass_next_work: str = AUTHORIZED_PASS_NEXT_WORK,
    authorized_remediation_next_work: str = AUTHORIZED_REMEDIATION_NEXT_WORK,
) -> dict[str, Any]:
    paths = {
        "manifest_builder_json": manifest_builder_json.resolve(),
        "scope_manifest_json": scope_manifest_json.resolve(),
        "nonoverlap_registry_report_json": nonoverlap_registry_report_json.resolve(),
        "sha256sums_txt": sha256sums_txt.resolve(),
        "v13_audit_md": v13_audit_md.resolve(),
    }
    builder = _load_json_dict(paths["manifest_builder_json"])
    scope = _load_json_dict(paths["scope_manifest_json"])
    registry_report = _load_json_dict(paths["nonoverlap_registry_report_json"])
    audit_text = _read_text(paths["v13_audit_md"])
    source_registry = _load_json_dict(
        Path(str(scope.get("rejected_evaluation_source_registry_manifest_json", "")))
    )
    split_result = _compute_split_result(source_registry)

    checks = _checks(
        paths=paths,
        builder=builder,
        scope=scope,
        registry_report=registry_report,
        source_registry=source_registry,
        split_result=split_result,
        audit_text=audit_text,
        expected_manifest_builder_json_sha256=expected_manifest_builder_json_sha256,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
    )
    failed_checks = [check["name"] for check in checks if not check["passed"]]
    zero_proof_passed = split_result["all_required_intersections_zero"]
    passed = not failed_checks and zero_proof_passed
    failure_class = None if passed else _failure_class(failed_checks, split_result)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "read_only": True,
            "preflight_only": True,
            "fixed_manifest_inputs_only": True,
            "fresh_split_member_selection_execution": False,
            "data_preparation_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "replay_execution": False,
            "training_execution": False,
            "dp_modification": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
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
        "inputs": {name: str(path) for name, path in paths.items()},
        "source_registry_manifest": str(
            Path(str(scope.get("rejected_evaluation_source_registry_manifest_json", ""))).resolve()
        ),
        "source_hashes": _source_hashes(paths, scope),
        "manifest_summary": _manifest_summary(builder, scope, registry_report),
        "preflight_result": split_result,
        "preflight_checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed_checks=failed_checks,
            failure_class=failure_class,
            authorized_current_work=authorized_current_work,
            authorized_pass_next_work=authorized_pass_next_work,
            authorized_remediation_next_work=authorized_remediation_next_work,
        ),
    }


def build_member_source_remediation_report(
    *,
    member_source_validation_json: Path,
    expected_member_source_validation_json_sha256: str,
    member_source_manifest_json: Path,
    member_source_nonoverlap_report_json: Path,
    member_source_preflight_inputs_json: Path,
    sha256sums_txt: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = MEMBER_SOURCE_REMEDIATION_AUTHORIZED_CURRENT_WORK,
    authorized_pass_next_work: str = AUTHORIZED_PASS_NEXT_WORK,
    authorized_remediation_next_work: str = AUTHORIZED_REMEDIATION_NEXT_WORK,
) -> dict[str, Any]:
    paths = {
        "member_source_validation_json": member_source_validation_json.resolve(),
        "member_source_manifest_json": member_source_manifest_json.resolve(),
        "member_source_nonoverlap_report_json": member_source_nonoverlap_report_json.resolve(),
        "member_source_preflight_inputs_json": member_source_preflight_inputs_json.resolve(),
        "sha256sums_txt": sha256sums_txt.resolve(),
        "v13_audit_md": v13_audit_md.resolve(),
    }
    validation = _load_json_dict(paths["member_source_validation_json"])
    manifest = _load_json_dict(paths["member_source_manifest_json"])
    nonoverlap = _load_json_dict(paths["member_source_nonoverlap_report_json"])
    preflight_inputs = _load_json_dict(paths["member_source_preflight_inputs_json"])
    audit_text = _read_text(paths["v13_audit_md"])
    split_result = _member_source_split_result(manifest, nonoverlap)
    checks = _member_source_remediation_checks(
        paths=paths,
        validation=validation,
        manifest=manifest,
        nonoverlap=nonoverlap,
        preflight_inputs=preflight_inputs,
        audit_text=audit_text,
        expected_member_source_validation_json_sha256=expected_member_source_validation_json_sha256,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
    )
    failed_checks = [check["name"] for check in checks if not check["passed"]]
    zero_proof_passed = split_result["all_required_intersections_zero"]
    passed = not failed_checks and zero_proof_passed
    failure_class = None if passed else _failure_class(failed_checks, split_result)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "read_only": True,
            "preflight_only": True,
            "fixed_manifest_inputs_only": True,
            "member_source_remediation_mode": True,
            "fresh_split_member_selection_execution": False,
            "data_preparation_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "replay_execution": False,
            "training_execution": False,
            "dp_modification": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
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
        "inputs": {name: str(path) for name, path in paths.items()},
        "source_hashes": {
            f"{name}_sha256": _sha256_if_file(path) for name, path in paths.items()
        },
        "manifest_summary": _member_source_manifest_summary(
            validation,
            manifest,
            nonoverlap,
            preflight_inputs,
        ),
        "preflight_result": split_result,
        "preflight_checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed_checks=failed_checks,
            failure_class=failure_class,
            authorized_current_work=authorized_current_work,
            authorized_pass_next_work=authorized_pass_next_work,
            authorized_remediation_next_work=authorized_remediation_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    result = report["preflight_result"]
    return "\n".join(
        [
            "# V13 Fresh Evaluation Split Preflight",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Failure class: `{decision['failure_class']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Candidate hash intersection: `{result['candidate_tensor_hash_intersection_count']}`",
            f"- Path signature intersection: `{result['path_signature_intersection_count']}`",
            f"- Record identity intersection: `{result['record_identity_intersection_count']}`",
            f"- Split root intersection: `{result['split_manifest_root_intersection_count']}`",
            "",
            "This preflight is read-only and fixed-input only. It does not run DP, "
            "generate candidates, replay, train CAMP, modify DP, promote, deploy, "
            "or authorize safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _checks(
    *,
    paths: dict[str, Path],
    builder: dict[str, Any],
    scope: dict[str, Any],
    registry_report: dict[str, Any],
    source_registry: dict[str, Any],
    split_result: dict[str, Any],
    audit_text: str,
    expected_manifest_builder_json_sha256: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(builder.get("final_decision"))
    runtime = _dict(scope.get("required_runtime_contract"))
    executions = _dict(scope.get("executions_requested_by_this_manifest"))
    future = _dict(scope.get("future_preflight_must_prove"))
    requirements = _dict(registry_report.get("nonoverlap_requirements_for_future_fresh_split"))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check(
            "expected_manifest_builder_json_sha256_valid",
            _is_sha256(expected_manifest_builder_json_sha256),
            expected_manifest_builder_json_sha256,
            "sha256",
        ),
    ]
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file exists"))
    if paths["manifest_builder_json"].is_file():
        checks.append(
            _expect(
                "manifest_builder_json_sha256_matches_expected",
                _sha256(paths["manifest_builder_json"]),
                expected_manifest_builder_json_sha256.lower(),
            )
        )
    checks.extend(_sha256sum_checks(paths["sha256sums_txt"], paths))
    checks.extend(
        [
            _expect("builder_schema_version", builder.get("schema_version"), SOURCE_BUILDER_SCHEMA_VERSION),
            _expect("builder_status_complete", decision.get("status"), SOURCE_BUILDER_STATUS),
            _expect("builder_passed", decision.get("passed"), True),
            _expect("builder_authorizes_post_review", decision.get("authorized_next_work"), SOURCE_BUILDER_AUTHORIZED_NEXT_WORK),
            _expect("scope_schema_version", scope.get("schema_version"), SCOPE_MANIFEST_SCHEMA_VERSION),
            _expect("registry_report_schema_version", registry_report.get("schema_version"), REGISTRY_REPORT_SCHEMA_VERSION),
            _expect("source_registry_schema_version", source_registry.get("schema_version"), SOURCE_REGISTRY_SCHEMA_VERSION),
            _expect("scope_target_selection_log_count", scope.get("target_selection_log_count"), TARGET_SELECTION_LOGS),
            _expect("scope_target_record_count", scope.get("target_record_count"), TARGET_RECORDS),
            _expect("scope_candidate_count", scope.get("expected_candidate_count"), EXPECTED_CANDIDATE_COUNT),
            _expect("scope_atom_count", scope.get("expected_atom_count"), EXPECTED_ATOM_COUNT),
            _expect("scope_candidate_operation", scope.get("candidate_operation"), "fixed DP candidate reranking only"),
            _expect("scope_score_expression", scope.get("score_expression"), SCORE_EXPRESSION),
            _expect("scope_nonnegative_simplex", scope.get("nonnegative_simplex_weights_only"), True),
            _expect("runtime_default_off_selector", runtime.get("default_off_shadow_selector"), True),
            _expect("runtime_executed_dp_top1", runtime.get("executed_dp_top1"), True),
            _expect("runtime_blocks_reference_blend", runtime.get("reference_blend"), False),
            _expect("runtime_blocks_guidance", runtime.get("guidance"), False),
            _expect("runtime_blocks_postprocess", runtime.get("postprocess_or_postselection"), False),
            _expect("runtime_blocks_closed_loop", runtime.get("closed_loop_outcomes_as_training_or_online_input"), False),
            _expect("source_registry_formal_training_seed_count", source_registry.get("training_formal_seed_count"), 0),
            _expect("source_registry_formal_evaluation_seed_count", source_registry.get("evaluation_formal_seed_count"), 0),
            _expect("preflight_target_selection_log_count", split_result["evaluation_source_log_count"], TARGET_SELECTION_LOGS),
            _expect("preflight_target_record_count", split_result["evaluation_record_count"], TARGET_RECORDS),
        ]
    )
    for key in (
        "candidate_tensor_hash_intersection_count",
        "path_signature_intersection_count",
        "record_identity_intersection_count",
        "split_manifest_root_intersection_count",
    ):
        checks.append(_expect(f"scope_requires_zero_{key}", future.get(key), 0))
        checks.append(_expect(f"registry_report_requires_zero_{key}", requirements.get(key), 0))
    for key in (
        "fixed_dp_candidate_generation",
        "data_preparation",
        "replay",
        "training",
        "dp_modification",
        "selector_or_atom_promotion",
        "deployment",
    ):
        checks.append(_expect(f"scope_requests_no_{key}", executions.get(key), False))
    checks.extend(_audit_checks(audit_text, authorized_current_work))
    return checks


def _member_source_remediation_checks(
    *,
    paths: dict[str, Path],
    validation: dict[str, Any],
    manifest: dict[str, Any],
    nonoverlap: dict[str, Any],
    preflight_inputs: dict[str, Any],
    audit_text: str,
    expected_member_source_validation_json_sha256: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(validation.get("final_decision"))
    manifest_boundary = _dict(manifest.get("math_and_runtime_boundary"))
    nonoverlap_boundary = _dict(nonoverlap.get("math_and_runtime_boundary"))
    forbidden = _dict(preflight_inputs.get("forbidden_next_actions"))
    zero_counts = _member_source_zero_counts(manifest, nonoverlap)
    selected_members = _list(manifest.get("selected_members"))
    selected_count = _int(manifest.get("selected_member_count"))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check(
            "expected_member_source_validation_json_sha256_valid",
            _is_sha256(expected_member_source_validation_json_sha256),
            expected_member_source_validation_json_sha256,
            "sha256",
        ),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), MEMBER_SOURCE_REMEDIATION_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_preflight_authorized", _latest_value(audit_text, "fresh_evaluation_split_preflight_authorized_next"), "True"),
    ]
    for flag in BLOCKED_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _latest_value(audit_text, flag), "False"))
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file exists"))
    if paths["member_source_validation_json"].is_file():
        checks.append(
            _expect(
                "member_source_validation_json_sha256_matches_expected",
                _sha256(paths["member_source_validation_json"]),
                expected_member_source_validation_json_sha256.lower(),
            )
        )
    checks.extend(
        [
            _expect("validation_schema_version", validation.get("schema_version"), MEMBER_SOURCE_VALIDATION_SCHEMA_VERSION),
            _expect("validation_status", decision.get("status"), MEMBER_SOURCE_VALIDATION_STATUS),
            _expect("validation_passed", decision.get("passed"), True),
            _expect("validation_failed_checks_empty", decision.get("failed_checks"), []),
            _expect("validation_authorizes_this_preflight", decision.get("authorized_next_work"), authorized_current_work),
            _expect("validation_preflight_authorized_next", decision.get("fresh_evaluation_split_preflight_authorized_next"), True),
            _expect("validation_member_source_builder_not_executed", decision.get("member_source_builder_executed"), False),
            _expect("validation_real_fresh_member_selection_not_executed", decision.get("real_fresh_member_selection_executed"), False),
            _expect("validation_fixed_dp_generation_not_executed", decision.get("fixed_dp_candidate_generation_executed"), False),
            _expect("validation_replay_not_executed", decision.get("replay_executed"), False),
            _expect("validation_training_not_executed", decision.get("training_executed"), False),
            _expect("validation_dp_modification_not_executed", decision.get("dp_modification_executed"), False),
            _expect("member_source_manifest_schema_version", manifest.get("schema_version"), MEMBER_SOURCE_MANIFEST_SCHEMA_VERSION),
            _expect("member_source_nonoverlap_schema_version", nonoverlap.get("schema_version"), MEMBER_SOURCE_NONOVERLAP_REPORT_SCHEMA_VERSION),
            _expect("member_source_preflight_inputs_schema_version", preflight_inputs.get("schema_version"), MEMBER_SOURCE_PREFLIGHT_INPUTS_SCHEMA_VERSION),
            _expect("member_source_selected_count", selected_count, TARGET_SELECTION_LOGS),
            _expect("member_source_selected_count_matches_list", len(selected_members), selected_count),
            _expect("nonoverlap_zero_proof_executed", nonoverlap.get("zero_intersection_proof_executed_by_this_builder"), True),
            _expect("nonoverlap_split_root_only_acceptance_false", nonoverlap.get("split_root_only_acceptance"), False),
            _expect("nonoverlap_rejected_overlap_source_reuse_false", nonoverlap.get("rejected_overlap_source_reuse"), False),
            _expect("nonoverlap_formal_seed_false", nonoverlap.get("formal_seed_11_12_13"), False),
            _expect("nonoverlap_full36_false", nonoverlap.get("full36"), False),
            _expect("manifest_score_affine", manifest_boundary.get("score_expression"), SCORE_EXPRESSION),
            _expect("nonoverlap_score_affine", nonoverlap_boundary.get("score_expression"), SCORE_EXPRESSION),
            _expect("manifest_fixed_dp_reranking_only", manifest_boundary.get("candidate_operation"), "fixed DP candidate reranking only"),
            _expect("manifest_nonnegative_simplex", manifest_boundary.get("nonnegative_simplex_weights_only"), True),
            _expect("manifest_master_convex", manifest_boundary.get("master_problem_remains_convex"), True),
            _expect("manifest_default_off_shadow_selector", manifest_boundary.get("default_off_shadow_selector"), True),
            _expect("manifest_executed_trajectory_dp_top1", manifest_boundary.get("executed_trajectory_remains_dp_top1"), True),
            _expect(
                "preflight_inputs_manifest_path_matches",
                _path_matches(preflight_inputs.get("fresh_member_source_manifest_json"), paths["member_source_manifest_json"]),
                True,
            ),
            _expect(
                "preflight_inputs_nonoverlap_path_matches",
                _path_matches(preflight_inputs.get("fresh_member_source_nonoverlap_report_json"), paths["member_source_nonoverlap_report_json"]),
                True,
            ),
        ]
    )
    for key in ZERO_INTERSECTION_KEYS:
        checks.append(_expect(f"{key}_is_zero", zero_counts.get(key), 0))
        checks.append(
            _expect(
                f"preflight_inputs_expect_zero_{key}",
                _dict(preflight_inputs.get("expected_zero_intersections")).get(key),
                0,
            )
        )
    for key in (
        "fixed_dp_candidate_generation",
        "candidate_generation_by_camp",
        "trajectory_generation_by_camp",
        "trajectory_modification_by_camp",
        "reference_blend",
        "guidance",
        "postprocess_or_postselection",
        "closed_loop_outcome_input",
        "replay",
        "training",
        "dp_modification",
        "promotion",
        "deployment",
        "safety_or_camp_over_dp_claim",
    ):
        checks.append(_expect(f"manifest_boundary_blocks_{key}", manifest_boundary.get(key), False))
        checks.append(_expect(f"nonoverlap_boundary_blocks_{key}", nonoverlap_boundary.get(key), False))
    for key in (
        "fixed_dp_candidate_generation",
        "replay",
        "training",
        "dp_modification",
        "promotion",
        "deployment",
        "safety_or_camp_over_dp_claim",
    ):
        checks.append(_expect(f"preflight_inputs_forbid_{key}", forbidden.get(key), True))
    checks.extend(_member_source_sha256sum_checks(paths))
    return checks


def _audit_checks(text: str, authorized_current_work: str) -> list[dict[str, Any]]:
    checks = [
        _expect("audit_latest_status", _latest_value(text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(text, "next_work_target"), authorized_current_work),
        _expect("audit_preflight_authorized", _latest_value(text, "fresh_evaluation_split_preflight_authorized_next"), "True"),
    ]
    for flag in BLOCKED_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _latest_value(text, flag), "False"))
    return checks


def _compute_split_result(source_registry: dict[str, Any]) -> dict[str, Any]:
    candidate_registry = _load_json_dict(Path(str(source_registry.get("candidate_tensor_hash_registry_json", ""))))
    path_registry = _load_json_dict(Path(str(source_registry.get("path_signature_registry_json", ""))))
    record_registry = _load_json_dict(Path(str(source_registry.get("record_identity_hash_registry_json", ""))))
    split_manifest = _load_json_dict(Path(str(source_registry.get("split_manifest_json", ""))))
    candidate_eval, candidate_train = _registry_sets(candidate_registry, "values")
    path_eval, path_train = _registry_sets(path_registry, "signatures")
    record_eval, record_train = _registry_sets(record_registry, "record_identities")
    holdout_roots = set(_list(_dict(split_manifest.get("holdout")).get("selection_log_roots")))
    training_roots = set(_list(_dict(split_manifest.get("training")).get("selection_log_roots")))
    candidate_intersection = candidate_eval & candidate_train
    path_intersection = path_eval & path_train
    record_intersection = record_eval & record_train
    root_intersection = holdout_roots & training_roots
    return {
        "candidate_tensor_hash_evaluation_count": len(candidate_eval),
        "candidate_tensor_hash_training_count": len(candidate_train),
        "path_signature_evaluation_count": len(path_eval),
        "path_signature_training_count": len(path_train),
        "record_identity_evaluation_count": len(record_eval),
        "record_identity_training_count": len(record_train),
        "evaluation_source_log_count": len(holdout_roots),
        "evaluation_record_count": len(_list(_dict(record_registry.get("evaluation")).get("record_identities"))),
        "split_manifest_holdout_root_count": len(holdout_roots),
        "split_manifest_training_root_count": len(training_roots),
        "candidate_tensor_hash_intersection_count": len(candidate_intersection),
        "path_signature_intersection_count": len(path_intersection),
        "record_identity_intersection_count": len(record_intersection),
        "split_manifest_root_intersection_count": len(root_intersection),
        "candidate_tensor_hash_intersection_sample": sorted(candidate_intersection)[:5],
        "path_signature_intersection_sample": sorted(path_intersection)[:5],
        "record_identity_intersection_sample": sorted(record_intersection)[:5],
        "split_manifest_root_intersection_sample": sorted(root_intersection)[:5],
        "all_required_intersections_zero": not (
            candidate_intersection or path_intersection or record_intersection or root_intersection
        ),
    }


def _member_source_split_result(
    manifest: dict[str, Any],
    nonoverlap: dict[str, Any],
) -> dict[str, Any]:
    zero_counts = _member_source_zero_counts(manifest, nonoverlap)
    result = {
        "candidate_tensor_hash_intersection_count": zero_counts.get(
            "candidate_tensor_hash_intersection_count"
        ),
        "path_signature_intersection_count": zero_counts.get(
            "path_signature_intersection_count"
        ),
        "record_identity_intersection_count": zero_counts.get(
            "record_identity_intersection_count"
        ),
        "split_manifest_root_intersection_count": zero_counts.get(
            "split_manifest_root_intersection_count"
        ),
        "evaluation_source_log_count": _int(manifest.get("selected_member_count")),
        "selected_member_count": _int(manifest.get("selected_member_count")),
        "candidate_tensor_hash_intersection_sample": [],
        "path_signature_intersection_sample": [],
        "record_identity_intersection_sample": [],
        "split_manifest_root_intersection_sample": [],
    }
    result["all_required_intersections_zero"] = all(
        result[key] == 0 for key in ZERO_INTERSECTION_KEYS
    )
    return result


def _registry_sets(payload: dict[str, Any], field: str) -> tuple[set[str], set[str]]:
    evaluation = set(str(value) for value in _list(_dict(payload.get("evaluation")).get(field)))
    training = set(str(value) for value in _list(_dict(payload.get("training")).get(field)))
    return evaluation, training


def _sha256sum_checks(sha256sums_txt: Path, paths: dict[str, Path]) -> list[dict[str, Any]]:
    text = _read_text(sha256sums_txt)
    entries: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2 and _is_sha256(parts[0]):
            entries[parts[1].lstrip("*")] = parts[0].lower()
    checks = []
    artifact_dir = paths["scope_manifest_json"].parent
    for filename in (
        "fresh_evaluation_split_scope_manifest.json",
        "fresh_evaluation_split_nonoverlap_registry_report.json",
        "run_fresh_evaluation_split_preflight.sh",
    ):
        path = artifact_dir / filename
        checks.append(_expect(f"sha256sums_entry_{_slug(filename)}", entries.get(filename), _sha256(path) if path.is_file() else None))
    return checks


def _member_source_sha256sum_checks(paths: dict[str, Path]) -> list[dict[str, Any]]:
    entries = _sha256_entries_by_name(paths["sha256sums_txt"])
    required = {
        "fresh_evaluation_split_member_source_manifest.json": paths["member_source_manifest_json"],
        "fresh_evaluation_split_member_source_nonoverlap_report.json": paths[
            "member_source_nonoverlap_report_json"
        ],
        "fresh_evaluation_split_member_source_preflight_inputs.json": paths[
            "member_source_preflight_inputs_json"
        ],
    }
    checks = []
    for filename, path in required.items():
        checks.append(_check(f"sha256sums_entry_{_slug(filename)}", filename in entries, sorted(entries), filename))
        checks.append(
            _expect(
                f"sha256sums_match_{_slug(filename)}",
                _sha256_if_file(path),
                entries.get(filename),
            )
        )
    return checks


def _source_hashes(paths: dict[str, Path], scope: dict[str, Any]) -> dict[str, str | None]:
    hashes: dict[str, str | None] = {
        f"{name}_sha256": _sha256(path) if path.is_file() else None
        for name, path in paths.items()
    }
    for key in (
        "training_selection_manifest_json",
        "recovered_prior_registry_manifest_json",
        "rejected_evaluation_source_registry_manifest_json",
    ):
        path = Path(str(scope.get(key, "")))
        hashes[f"{key}_sha256"] = _sha256(path) if path.is_file() else None
    return hashes


def _member_source_manifest_summary(
    validation: dict[str, Any],
    manifest: dict[str, Any],
    nonoverlap: dict[str, Any],
    preflight_inputs: dict[str, Any],
) -> dict[str, Any]:
    decision = _dict(validation.get("final_decision"))
    return {
        "validation_status": decision.get("status"),
        "validation_passed": decision.get("passed"),
        "selected_member_count": _int(manifest.get("selected_member_count")),
        "zero_intersection_counts": _member_source_zero_counts(manifest, nonoverlap),
        "manifest_role": manifest.get("manifest_role"),
        "nonoverlap_report_role": nonoverlap.get("manifest_role"),
        "preflight_inputs_role": preflight_inputs.get("manifest_role"),
    }


def _manifest_summary(
    builder: dict[str, Any],
    scope: dict[str, Any],
    registry_report: dict[str, Any],
) -> dict[str, Any]:
    decision = _dict(builder.get("final_decision"))
    return {
        "builder_status": decision.get("status"),
        "builder_passed": decision.get("passed"),
        "builder_authorized_next_work": decision.get("authorized_next_work"),
        "scope_schema_version": scope.get("schema_version"),
        "registry_report_schema_version": registry_report.get("schema_version"),
        "target_selection_log_count": scope.get("target_selection_log_count"),
        "target_record_count": scope.get("target_record_count"),
        "fresh_split_members_selected_by_builder": scope.get(
            "fresh_split_members_selected_by_this_builder"
        ),
        "future_zero_intersection_preflight_required": registry_report.get(
            "future_zero_intersection_preflight_required"
        ),
    }


def _member_source_zero_counts(
    manifest: dict[str, Any],
    nonoverlap: dict[str, Any],
) -> dict[str, int | None]:
    values = _dict(manifest.get("zero_intersection_counts"))
    if not values:
        values = _dict(nonoverlap.get("zero_intersection_counts"))
    return {key: _int(values.get(key)) if key in values else None for key in ZERO_INTERSECTION_KEYS}


def _decision(
    *,
    passed: bool,
    failed_checks: list[str],
    failure_class: str | None,
    authorized_current_work: str,
    authorized_pass_next_work: str,
    authorized_remediation_next_work: str,
) -> dict[str, Any]:
    authorized_next = authorized_pass_next_work if passed else authorized_remediation_next_work
    return {
        "status": PASS_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed_checks,
        "failure_class": failure_class,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next,
        "fresh_evaluation_split_preflight_passed": passed,
        "fresh_evaluation_split_member_source_remediation_plan_authorized_next": not passed,
        "fresh_evaluation_split_evaluation_authorized_next": passed,
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
    }


def _failure_class(failed_checks: list[str], result: dict[str, Any]) -> str:
    if result["candidate_tensor_hash_intersection_count"] > 0:
        return "candidate_tensor_hash_overlap_with_training_registry"
    if result["path_signature_intersection_count"] > 0:
        return "path_signature_overlap_with_training_registry"
    if result["record_identity_intersection_count"] > 0:
        return "record_identity_overlap_with_training_registry"
    if result["split_manifest_root_intersection_count"] > 0:
        return "split_manifest_root_overlap_with_training_registry"
    if failed_checks:
        return "static_contract_check_failed"
    return "unknown_preflight_failure"


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_if_file(path: Path) -> str | None:
    return _sha256(path) if path.is_file() else None


def _sha256_entries_by_name(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in _read_text(path).splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2 and _is_sha256(parts[0]):
            entries[Path(parts[1].lstrip("*")).name] = parts[0].lower()
    return entries


def _is_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", value or ""))


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


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _path_matches(value: Any, expected: Path) -> bool:
    try:
        return Path(str(value)).resolve() == expected.resolve()
    except OSError:
        return False


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")


def _has_member_source_args(args: argparse.Namespace) -> bool:
    return any(
        getattr(args, name) is not None
        for name in (
            "member_source_validation_json",
            "expected_member_source_validation_json_sha256",
            "member_source_manifest_json",
            "member_source_nonoverlap_report_json",
            "member_source_preflight_inputs_json",
        )
    )


def _required_path(value: Path | None, flag: str) -> Path:
    if value is None:
        raise SystemExit(f"missing required argument {flag}")
    return value


def _required_str(value: str | None, flag: str) -> str:
    if value is None:
        raise SystemExit(f"missing required argument {flag}")
    return value


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
