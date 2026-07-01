#!/usr/bin/env python3
"""Read-only validation preflight for v13 fresh member-source artifacts.

This gate validates already materialized fresh evaluation split member-source
artifacts before any later evaluation split work can be considered. It does
not run the member-source builder, select members, run Diffusion Planner,
generate candidates, replay, train CAMP, modify DP, promote, deploy, or make
safety/CAMP-over-DP claims.
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
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_validation_preflight_v1"
)
PASS_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_validation_preflight_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_validation_preflight_rejected"
)
POST_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_builder_"
    "post_implementation_static_contract_review_v1"
)
POST_REVIEW_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_builder_"
    "post_implementation_static_contract_review_complete"
)
MEMBER_SOURCE_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_manifest_v1"
)
NONOVERLAP_REPORT_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_nonoverlap_report_v1"
)
PREFLIGHT_INPUTS_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_preflight_inputs_v1"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_builder_post_implementation_static_contract_review_complete"
)
MATERIALIZATION_COMPLETE_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_remediation_materialization_complete"
)
AUTHORIZED_AUDIT_STATUSES = (
    LATEST_AUDIT_STATUS,
    MATERIALIZATION_COMPLETE_AUDIT_STATUS,
)
MATERIALIZER_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materializer_v1"
)
MATERIALIZER_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materializer_complete"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "validation_preflight_only"
)
AUTHORIZED_PASS_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "fresh_evaluation_split_preflight_only"
)
AUTHORIZED_MISSING_INPUT_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "materialization_plan_only"
)
ZERO_INTERSECTION_KEYS = (
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
REQUIRED_SHA_FILES = (
    "fresh_evaluation_split_member_source_manifest.json",
    "fresh_evaluation_split_member_source_nonoverlap_report.json",
    "fresh_evaluation_split_member_source_preflight_inputs.json",
)
AUDIT_FALSE_FLAGS = (
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
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
POST_REVIEW_FALSE_FLAGS = (
    "fresh_member_selection_execution_authorized_next",
    "fresh_evaluation_split_evaluation_authorized_next",
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "replay_execution_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "dp_modification_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only validation preflight for already materialized v13 fresh "
            "evaluation split member-source artifacts."
        )
    )
    parser.add_argument("--post_review_json", type=Path, required=True)
    parser.add_argument("--expected_post_review_json_sha256", required=True)
    parser.add_argument("--member_source_manifest_json", type=Path, required=True)
    parser.add_argument("--nonoverlap_report_json", type=Path, required=True)
    parser.add_argument("--preflight_inputs_json", type=Path, required=True)
    parser.add_argument("--sha256sums_txt", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_pass_next_work", default=AUTHORIZED_PASS_NEXT_WORK)
    parser.add_argument(
        "--authorized_missing_input_next_work",
        default=AUTHORIZED_MISSING_INPUT_NEXT_WORK,
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        post_review_json=args.post_review_json,
        expected_post_review_json_sha256=args.expected_post_review_json_sha256,
        member_source_manifest_json=args.member_source_manifest_json,
        nonoverlap_report_json=args.nonoverlap_report_json,
        preflight_inputs_json=args.preflight_inputs_json,
        sha256sums_txt=args.sha256sums_txt,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_pass_next_work=args.authorized_pass_next_work,
        authorized_missing_input_next_work=args.authorized_missing_input_next_work,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0


def build_report(
    *,
    post_review_json: Path,
    expected_post_review_json_sha256: str,
    member_source_manifest_json: Path,
    nonoverlap_report_json: Path,
    preflight_inputs_json: Path,
    sha256sums_txt: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_pass_next_work: str = AUTHORIZED_PASS_NEXT_WORK,
    authorized_missing_input_next_work: str = AUTHORIZED_MISSING_INPUT_NEXT_WORK,
) -> dict[str, Any]:
    paths = {
        "post_review_json": post_review_json.resolve(),
        "member_source_manifest_json": member_source_manifest_json.resolve(),
        "nonoverlap_report_json": nonoverlap_report_json.resolve(),
        "preflight_inputs_json": preflight_inputs_json.resolve(),
        "sha256sums_txt": sha256sums_txt.resolve(),
        "v13_audit_md": v13_audit_md.resolve(),
    }
    post_review = _load_json_dict(paths["post_review_json"])
    manifest = _load_json_dict(paths["member_source_manifest_json"])
    nonoverlap = _load_json_dict(paths["nonoverlap_report_json"])
    preflight_inputs = _load_json_dict(paths["preflight_inputs_json"])
    audit_text = _read_text(paths["v13_audit_md"])
    sha_entries = _sha256_entries(paths["sha256sums_txt"])
    checks = _checks(
        paths=paths,
        post_review=post_review,
        manifest=manifest,
        nonoverlap=nonoverlap,
        preflight_inputs=preflight_inputs,
        sha_entries=sha_entries,
        audit_text=audit_text,
        expected_post_review_json_sha256=expected_post_review_json_sha256,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    failure_class = _failure_class(failed, paths)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "read_only": True,
            "validation_preflight_only": True,
            "already_materialized_member_source_inputs_only": True,
            "member_source_builder_execution": False,
            "fresh_member_selection_execution": False,
            "fresh_evaluation_split_evaluation_execution": False,
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
        "source_hashes": {name: _sha256(path) for name, path in paths.items()},
        "member_source_summary": _member_source_summary(manifest, nonoverlap),
        "sha256sums_summary": {
            "required_files": list(REQUIRED_SHA_FILES),
            "present_files": sorted(sha_entries),
        },
        "preflight_checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed_checks=failed,
            failure_class=failure_class,
            authorized_current_work=authorized_current_work,
            authorized_pass_next_work=authorized_pass_next_work,
            authorized_missing_input_next_work=authorized_missing_input_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["member_source_summary"]
    return "\n".join(
        [
            "# V13 Fresh Evaluation Split Member-Source Validation Preflight",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Failure class: `{decision['failure_class']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Selected member count: `{summary['selected_member_count']}`",
            f"- Candidate hash intersection: `{summary['zero_intersection_counts'].get('candidate_tensor_hash_intersection_count')}`",
            f"- Path signature intersection: `{summary['zero_intersection_counts'].get('path_signature_intersection_count')}`",
            f"- Record identity intersection: `{summary['zero_intersection_counts'].get('record_identity_intersection_count')}`",
            f"- Split root intersection: `{summary['zero_intersection_counts'].get('split_manifest_root_intersection_count')}`",
            "",
            "This validation preflight is read-only. It does not run the "
            "member-source builder, select members, run DP, generate candidates, "
            "replay, train CAMP, modify DP, promote, deploy, or authorize "
            "safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _checks(
    *,
    paths: dict[str, Path],
    post_review: dict[str, Any],
    manifest: dict[str, Any],
    nonoverlap: dict[str, Any],
    preflight_inputs: dict[str, Any],
    sha_entries: dict[str, str],
    audit_text: str,
    expected_post_review_json_sha256: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check(
            "expected_post_review_json_sha256_valid",
            _is_sha256(expected_post_review_json_sha256),
            expected_post_review_json_sha256,
            "sha256",
        ),
        _check(
            "audit_latest_status",
            _latest_value(audit_text, "current_v13_status") in AUTHORIZED_AUDIT_STATUSES,
            _latest_value(audit_text, "current_v13_status"),
            list(AUTHORIZED_AUDIT_STATUSES),
        ),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect(
            "audit_authorizes_validation_preflight",
            _latest_value(
                audit_text,
                "fresh_evaluation_split_member_source_remediation_validation_preflight_authorized_next",
            ),
            "True",
        ),
    ]
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _latest_value(audit_text, flag), "False"))
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file exists"))
    post_review_sha = _sha256(paths["post_review_json"])
    checks.append(
        _expect(
            "post_review_json_sha256_matches_expected",
            post_review_sha,
            expected_post_review_json_sha256.lower(),
        )
    )
    checks.extend(_post_review_checks(post_review, authorized_current_work))
    checks.extend(_member_source_checks(manifest, nonoverlap, preflight_inputs))
    checks.extend(_sha256_checks(paths, sha_entries))
    return checks


def _post_review_checks(
    post_review: dict[str, Any],
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(post_review.get("final_decision"))
    if post_review.get("schema_version") == MATERIALIZER_SCHEMA_VERSION:
        return [
            _expect("source_schema_version", post_review.get("schema_version"), MATERIALIZER_SCHEMA_VERSION),
            _expect("source_status", decision.get("status"), MATERIALIZER_STATUS),
            _expect("source_passed", decision.get("passed"), True),
            _expect("source_failed_checks_empty", decision.get("failed_checks"), []),
            _expect("source_authorizes_this_preflight", decision.get("authorized_next_work"), authorized_current_work),
            _expect("source_validation_preflight_authorized", decision.get("validation_preflight_authorized_next"), True),
            _expect("source_materialization_complete", decision.get("materialization_complete"), True),
            _expect("source_member_source_manifest_written", decision.get("member_source_manifest_written"), True),
            *[
                _expect(f"source_blocks_{flag}", decision.get(flag), False)
                for flag in POST_REVIEW_FALSE_FLAGS
            ],
            _expect("source_fixed_dp_candidate_generation_not_executed", decision.get("fixed_dp_candidate_generation_executed"), False),
            _expect("source_candidate_generation_by_camp_not_executed", decision.get("candidate_generation_by_camp_executed"), False),
            _expect("source_trajectory_generation_by_camp_not_executed", decision.get("trajectory_generation_by_camp_executed"), False),
            _expect("source_trajectory_modification_by_camp_not_executed", decision.get("trajectory_modification_by_camp_executed"), False),
            _expect("source_replay_not_executed", decision.get("replay_executed"), False),
            _expect("source_training_not_executed", decision.get("training_executed"), False),
            _expect("source_dp_modification_not_executed", decision.get("dp_modification_executed"), False),
        ]

    return [
        _expect("post_review_schema_version", post_review.get("schema_version"), POST_REVIEW_SCHEMA_VERSION),
        _expect("post_review_status", decision.get("status"), POST_REVIEW_STATUS),
        _expect("post_review_passed", decision.get("passed"), True),
        _expect("post_review_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("post_review_authorizes_this_preflight", decision.get("authorized_next_work"), authorized_current_work),
        _expect("post_review_validation_preflight_authorized", decision.get("validation_preflight_authorized_next"), True),
        *[
            _expect(f"post_review_blocks_{flag}", decision.get(flag), False)
            for flag in POST_REVIEW_FALSE_FLAGS
        ],
        _expect("post_review_real_fresh_member_selection_not_executed", decision.get("real_fresh_member_selection_executed"), False),
        _expect("post_review_fixed_dp_candidate_generation_not_executed", decision.get("fixed_dp_candidate_generation_executed"), False),
        _expect("post_review_replay_not_executed", decision.get("replay_executed"), False),
        _expect("post_review_training_not_executed", decision.get("training_executed"), False),
        _expect("post_review_dp_modification_not_executed", decision.get("dp_modification_executed"), False),
    ]


def _member_source_checks(
    manifest: dict[str, Any],
    nonoverlap: dict[str, Any],
    preflight_inputs: dict[str, Any],
) -> list[dict[str, Any]]:
    manifest_boundary = _dict(manifest.get("math_and_runtime_boundary"))
    nonoverlap_boundary = _dict(nonoverlap.get("math_and_runtime_boundary"))
    zero_counts = _zero_counts(manifest, nonoverlap)
    selected_count = _int(manifest.get("selected_member_count"))
    selected_members = _list(manifest.get("selected_members"))
    forbidden = _dict(preflight_inputs.get("forbidden_next_actions"))
    checks = [
        _expect("member_source_manifest_schema_version", manifest.get("schema_version"), MEMBER_SOURCE_MANIFEST_SCHEMA_VERSION),
        _expect("nonoverlap_report_schema_version", nonoverlap.get("schema_version"), NONOVERLAP_REPORT_SCHEMA_VERSION),
        _expect("preflight_inputs_schema_version", preflight_inputs.get("schema_version"), PREFLIGHT_INPUTS_SCHEMA_VERSION),
        _check("selected_member_count_positive", selected_count > 0, selected_count, ">0"),
        _expect("selected_member_count_matches_list", len(selected_members), selected_count),
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
    ]
    for key in ZERO_INTERSECTION_KEYS:
        checks.append(_expect(f"{key}_is_zero", zero_counts.get(key), 0))
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
    return checks


def _sha256_checks(paths: dict[str, Path], sha_entries: dict[str, str]) -> list[dict[str, Any]]:
    path_by_name = {
        "fresh_evaluation_split_member_source_manifest.json": paths["member_source_manifest_json"],
        "fresh_evaluation_split_member_source_nonoverlap_report.json": paths["nonoverlap_report_json"],
        "fresh_evaluation_split_member_source_preflight_inputs.json": paths["preflight_inputs_json"],
    }
    checks = []
    for name, path in path_by_name.items():
        checks.append(_check(f"sha256sums_contains_{name}", name in sha_entries, sorted(sha_entries), name))
        checks.append(_expect(f"sha256sums_matches_{name}", _sha256(path), sha_entries.get(name)))
    return checks


def _member_source_summary(
    manifest: dict[str, Any],
    nonoverlap: dict[str, Any],
) -> dict[str, Any]:
    return {
        "selected_member_count": _int(manifest.get("selected_member_count")),
        "selected_member_ids": [
            str(_dict(member).get("member_id"))
            for member in _list(manifest.get("selected_members"))
        ],
        "zero_intersection_counts": _zero_counts(manifest, nonoverlap),
    }


def _zero_counts(
    manifest: dict[str, Any],
    nonoverlap: dict[str, Any],
) -> dict[str, Any]:
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
    authorized_missing_input_next_work: str,
) -> dict[str, Any]:
    return {
        "status": PASS_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed_checks,
        "failure_class": failure_class,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": (
            authorized_pass_next_work if passed else authorized_missing_input_next_work
        ),
        "validation_preflight_complete": True,
        "fresh_evaluation_split_preflight_authorized_next": passed,
        "member_source_materialization_plan_authorized_next": not passed,
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
        "member_source_builder_executed": False,
        "real_fresh_member_selection_executed": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }


def _failure_class(failed: list[str], paths: dict[str, Path]) -> str | None:
    if not failed:
        return None
    missing_names = [name for name, path in paths.items() if not path.is_file()]
    if missing_names:
        return "fresh_member_source_artifact_missing"
    if any(name.startswith("audit_") for name in failed):
        return "audit_authorization_mismatch"
    if any(name.endswith("_is_zero") for name in failed):
        return "nonzero_member_source_registry_overlap"
    if any("_blocks_" in name or "_forbid_" in name for name in failed):
        return "forbidden_action_authorization_leak"
    return "validation_contract_failed"


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _sha256_entries(path: Path) -> dict[str, str]:
    text = _read_text(path)
    entries: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2 and _is_sha256(parts[0]):
            entries[Path(parts[1].strip()).name] = parts[0].lower()
    return entries


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _is_sha256(value: str | None) -> bool:
    return bool(value) and len(value) == 64 and all(
        ch in "0123456789abcdefABCDEF" for ch in value
    )


def _is_git_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "actual": actual,
        "expected": expected,
    }


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
