#!/usr/bin/env python3
"""Materialize v13 fresh member-source validation inputs.

This materializer is default-off and fail-closed. When explicitly enabled it
reads an already materialized candidate member-source manifest and already
materialized training/recovered/rejected registries, selects only fresh
non-overlapping members, and writes the member-source manifest, non-overlap
report, preflight inputs, and SHA256SUMS. It does not run Diffusion Planner,
generate candidates, rewrite trajectories, run replay, train CAMP, modify DP,
promote, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations import (
    build_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source as base,
)


FIXED_DP_HEAD = base.FIXED_DP_HEAD
SCORE_EXPRESSION = base.SCORE_EXPRESSION
SCHEMA_VERSION = "dp_camp_v13_fresh_evaluation_split_member_source_materializer_v1"
DISABLED_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materializer_default_off_disabled"
)
READY_STATUS = "dp_camp_v13_fresh_evaluation_split_member_source_materializer_complete"
REJECT_STATUS = "dp_camp_v13_fresh_evaluation_split_member_source_materializer_rejected"
SOURCE_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "implementation_static_contract_review_v1"
)
SOURCE_REVIEW_PASS_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "implementation_static_contract_review_passed"
)
POST_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "post_implementation_static_contract_review_v1"
)
POST_REVIEW_PASS_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "post_implementation_static_contract_review_passed"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_post_implementation_static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "materialization_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "validation_preflight_only"
)
MEMBER_SOURCE_MANIFEST_SCHEMA_VERSION = base.MEMBER_SOURCE_MANIFEST_SCHEMA_VERSION
NONOVERLAP_REPORT_SCHEMA_VERSION = base.NONOVERLAP_REPORT_SCHEMA_VERSION
PREFLIGHT_INPUTS_SCHEMA_VERSION = base.PREFLIGHT_INPUTS_SCHEMA_VERSION
SHA256SUMS_NAME = base.SHA256SUMS_NAME
OUTPUT_FILES = base.OUTPUT_FILES
ZERO_INTERSECTION_KEYS = base.ZERO_INTERSECTION_KEYS
REQUIRED_BEHAVIOR = (
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
SOURCE_FALSE_FLAGS = (
    "implementation_execution_authorized_next",
    "member_source_builder_execution_authorized_next",
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
POST_REVIEW_REQUIRED_TRUE_FLAGS = (
    "materialization_only_authorized_next",
    "materializer_execution_authorized_next",
    "materialization_execution_authorized_next",
)
AUDIT_FALSE_FLAGS = (
    "implementation_execution_authorized_next",
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
        description="Default-off fail-closed materializer for fresh member-source inputs."
    )
    parser.add_argument("--implementation_static_contract_review_json", type=Path, required=True)
    parser.add_argument("--expected_static_contract_review_sha256", required=True)
    parser.add_argument("--candidate_member_source_manifest_json", type=Path, required=True)
    parser.add_argument("--training_candidate_tensor_hash_registry_json", type=Path, required=True)
    parser.add_argument("--training_path_signature_registry_json", type=Path, required=True)
    parser.add_argument("--training_record_identity_registry_json", type=Path, required=True)
    parser.add_argument("--training_split_manifest_root_registry_json", type=Path, required=True)
    parser.add_argument("--recovered_prior_registry_manifest_json", type=Path, required=True)
    parser.add_argument("--rejected_overlap_source_registry_manifest_json", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument(
        "--enable_v13_fresh_evaluation_split_member_source_materializer",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_materialization_report(
        implementation_static_contract_review_json=(
            args.implementation_static_contract_review_json
        ),
        expected_static_contract_review_sha256=(
            args.expected_static_contract_review_sha256
        ),
        candidate_member_source_manifest_json=args.candidate_member_source_manifest_json,
        training_candidate_tensor_hash_registry_json=(
            args.training_candidate_tensor_hash_registry_json
        ),
        training_path_signature_registry_json=args.training_path_signature_registry_json,
        training_record_identity_registry_json=args.training_record_identity_registry_json,
        training_split_manifest_root_registry_json=(
            args.training_split_manifest_root_registry_json
        ),
        recovered_prior_registry_manifest_json=args.recovered_prior_registry_manifest_json,
        rejected_overlap_source_registry_manifest_json=(
            args.rejected_overlap_source_registry_manifest_json
        ),
        v13_audit_md=args.v13_audit_md,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_md=args.output_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        enabled=args.enable_v13_fresh_evaluation_split_member_source_materializer,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    if report["final_decision"]["member_source_manifest_written"]:
        base._write_sha256sums(args.output_dir, list(OUTPUT_FILES))
        report["output_hashes"]["sha256sums_txt_sha256"] = base._sha256(
            args.output_dir / SHA256SUMS_NAME
        )
    args.output_json.write_text(json.dumps(base._stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(base._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["status"] != REJECT_STATUS else 1


def build_materialization_report(
    *,
    implementation_static_contract_review_json: Path,
    expected_static_contract_review_sha256: str,
    candidate_member_source_manifest_json: Path,
    training_candidate_tensor_hash_registry_json: Path,
    training_path_signature_registry_json: Path,
    training_record_identity_registry_json: Path,
    training_split_manifest_root_registry_json: Path,
    recovered_prior_registry_manifest_json: Path,
    rejected_overlap_source_registry_manifest_json: Path,
    v13_audit_md: Path,
    output_dir: Path,
    output_json: Path,
    output_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    enabled: bool = False,
) -> dict[str, Any]:
    _patch_base_next_work(authorized_next_work)
    report = _empty_report(
        enabled=enabled,
        implementation_static_contract_review_json=(
            implementation_static_contract_review_json
        ),
        candidate_member_source_manifest_json=candidate_member_source_manifest_json,
        training_candidate_tensor_hash_registry_json=(
            training_candidate_tensor_hash_registry_json
        ),
        training_path_signature_registry_json=training_path_signature_registry_json,
        training_record_identity_registry_json=training_record_identity_registry_json,
        training_split_manifest_root_registry_json=(
            training_split_manifest_root_registry_json
        ),
        recovered_prior_registry_manifest_json=recovered_prior_registry_manifest_json,
        rejected_overlap_source_registry_manifest_json=(
            rejected_overlap_source_registry_manifest_json
        ),
        output_dir=output_dir,
        output_json=output_json,
        output_md=output_md,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
        authorized_next_work=authorized_next_work,
    )
    if not enabled:
        return report

    audit_text = base._read_text_if_exists(v13_audit_md)
    checks = [
        base._check("current_camp_head_is_sha", base._is_git_sha(current_camp_head), current_camp_head, "git sha"),
        base._check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        base._check("current_dp_head_fixed", current_dp_head == required_dp_head == FIXED_DP_HEAD, current_dp_head, FIXED_DP_HEAD),
        base._check("expected_static_contract_review_sha256_valid", base._is_sha256(expected_static_contract_review_sha256), expected_static_contract_review_sha256, "sha256"),
        base._check("output_dir_is_not_file", not output_dir.is_file(), str(output_dir), "not a file"),
        base._check("output_json_under_output_dir", base._is_relative_to(output_json, output_dir), str(output_json), str(output_dir)),
        base._check("output_md_under_output_dir", base._is_relative_to(output_md, output_dir), str(output_md), str(output_dir)),
        base._check("latest_audit_status_authorizes_materializer", base._latest_value(audit_text, "current_v13_status") == LATEST_AUDIT_STATUS, base._latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        base._check("latest_audit_target_authorizes_materializer", base._latest_value(audit_text, "next_work_target") == authorized_current_work, base._latest_value(audit_text, "next_work_target"), authorized_current_work),
    ]
    checks.extend(_audit_boundary_checks(audit_text))

    review_payload, review_checks = base._load_source_json(
        implementation_static_contract_review_json,
        "implementation_static_contract_review_json",
    )
    candidate_payload, candidate_checks = base._load_source_json(
        candidate_member_source_manifest_json,
        "candidate_member_source_manifest_json",
    )
    checks.extend(review_checks)
    checks.extend(candidate_checks)
    if implementation_static_contract_review_json.is_file():
        review_sha = base._sha256(implementation_static_contract_review_json)
        report["source_hashes"]["implementation_static_contract_review_json_sha256"] = review_sha
        checks.append(
            base._check(
                "static_contract_review_sha256_matches_expected",
                review_sha == expected_static_contract_review_sha256.lower(),
                review_sha,
                expected_static_contract_review_sha256.lower(),
            )
        )

    review_summary = _review_summary(review_payload)
    checks.extend(_source_review_checks(review_summary, authorized_current_work))

    training_bundle = base._training_registry_bundle(
        candidate_path=training_candidate_tensor_hash_registry_json,
        path_signature_path=training_path_signature_registry_json,
        record_identity_path=training_record_identity_registry_json,
        split_root_path=training_split_manifest_root_registry_json,
    )
    recovered_bundle = base._source_registry_bundle(
        recovered_prior_registry_manifest_json,
        "recovered_prior",
    )
    rejected_bundle = base._source_registry_bundle(
        rejected_overlap_source_registry_manifest_json,
        "rejected_overlap_source",
    )
    checks.extend(training_bundle["checks"])
    checks.extend(recovered_bundle["checks"])
    checks.extend(rejected_bundle["checks"])
    report["source_hashes"].update(training_bundle["hashes"])
    report["source_hashes"].update(recovered_bundle["hashes"])
    report["source_hashes"].update(rejected_bundle["hashes"])

    candidates = base._candidate_members(candidate_payload)
    selection = base._select_fresh_members(
        candidates=candidates,
        reference_bundles=[training_bundle, recovered_bundle, rejected_bundle],
        rejected_overlap_source_registry_manifest_json=(
            rejected_overlap_source_registry_manifest_json
        ),
    )
    checks.extend(base._selection_checks(selection))
    planned_outputs = base._build_outputs(
        review_summary=review_summary,
        candidate_member_source_manifest_json=candidate_member_source_manifest_json,
        training_bundle=training_bundle,
        recovered_bundle=recovered_bundle,
        rejected_bundle=rejected_bundle,
        selection=selection,
        output_dir=output_dir,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
    )
    checks.extend(base._output_absence_checks(planned_outputs, output_json, output_md))

    passed = all(check["passed"] for check in checks)
    report["checks"] = checks
    report["source_summaries"] = {
        "implementation_static_contract_review": review_summary,
        "candidate_member_source_manifest": {
            "schema_version": candidate_payload.get("schema_version"),
            "candidate_member_count": len(candidates),
        },
        "training_registries": base._bundle_summary(training_bundle),
        "recovered_prior_registry": base._bundle_summary(recovered_bundle),
        "rejected_overlap_source_registry": base._bundle_summary(rejected_bundle),
    }
    report["selection_summary"] = selection["summary"]
    report["planned_outputs"] = {key: str(value["path"]) for key, value in planned_outputs.items()}

    if passed:
        output_dir.mkdir(parents=True, exist_ok=True)
        base._write_json(
            planned_outputs["member_source_manifest"]["path"],
            planned_outputs["member_source_manifest"]["payload"],
        )
        base._write_json(
            planned_outputs["nonoverlap_report"]["path"],
            planned_outputs["nonoverlap_report"]["payload"],
        )
        base._write_json(
            planned_outputs["preflight_inputs"]["path"],
            planned_outputs["preflight_inputs"]["payload"],
        )
        report["output_hashes"].update(
            {
                "fresh_evaluation_split_member_source_manifest_sha256": base._sha256(
                    planned_outputs["member_source_manifest"]["path"]
                ),
                "fresh_evaluation_split_member_source_nonoverlap_report_sha256": base._sha256(
                    planned_outputs["nonoverlap_report"]["path"]
                ),
                "fresh_evaluation_split_member_source_preflight_inputs_sha256": base._sha256(
                    planned_outputs["preflight_inputs"]["path"]
                ),
            }
        )

    report["final_decision"] = _decision(
        passed=passed,
        enabled=True,
        authorized_next_work=authorized_next_work,
        failed=[check["name"] for check in checks if not check["passed"]],
    )
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# V13 Fresh Evaluation Split Member-Source Materializer",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Enabled: `{decision['enabled']}`",
        f"- Member-source manifest written: `{decision['member_source_manifest_written']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        (
            "This materializer is default-off and fail-closed. It consumes only "
            "already materialized member-source candidates and registries; it "
            "does not run DP, generate candidates, replay, train CAMP, modify "
            "DP, promote, deploy, or make safety/CAMP-over-DP claims."
        ),
        "",
    ]
    selection = report.get("selection_summary")
    if selection:
        lines.extend(
            [
                "## Selection Summary",
                "",
                f"- Candidate members: `{selection['candidate_member_count']}`",
                f"- Selected members: `{selection['selected_member_count']}`",
                f"- Rejected members: `{selection['rejected_member_count']}`",
                f"- Zero-intersection proof: `{selection['zero_intersection_counts']}`",
                "",
            ]
        )
    return "\n".join(lines)


def _empty_report(
    *,
    enabled: bool,
    implementation_static_contract_review_json: Path,
    candidate_member_source_manifest_json: Path,
    training_candidate_tensor_hash_registry_json: Path,
    training_path_signature_registry_json: Path,
    training_record_identity_registry_json: Path,
    training_split_manifest_root_registry_json: Path,
    recovered_prior_registry_manifest_json: Path,
    rejected_overlap_source_registry_manifest_json: Path,
    output_dir: Path,
    output_json: Path,
    output_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "default_off": not enabled,
            "implementation_gate": False,
            "materialization_gate": True,
            "materializer": True,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "nonnegative_simplex_weights_only": True,
            "master_problem_remains_convex": True,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "replay_execution": False,
            "training_execution": False,
            "dp_modification": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {
            "implementation_static_contract_review_json": str(
                implementation_static_contract_review_json
            ),
            "candidate_member_source_manifest_json": str(candidate_member_source_manifest_json),
            "training_candidate_tensor_hash_registry_json": str(
                training_candidate_tensor_hash_registry_json
            ),
            "training_path_signature_registry_json": str(
                training_path_signature_registry_json
            ),
            "training_record_identity_registry_json": str(
                training_record_identity_registry_json
            ),
            "training_split_manifest_root_registry_json": str(
                training_split_manifest_root_registry_json
            ),
            "recovered_prior_registry_manifest_json": str(
                recovered_prior_registry_manifest_json
            ),
            "rejected_overlap_source_registry_manifest_json": str(
                rejected_overlap_source_registry_manifest_json
            ),
            "output_dir": str(output_dir),
            "output_json": str(output_json),
            "output_md": str(output_md),
        },
        "source_hashes": {},
        "output_hashes": {},
        "source_summaries": {},
        "selection_summary": {},
        "planned_outputs": {},
        "checks": [],
        "final_decision": _decision(
            passed=False,
            enabled=enabled,
            authorized_next_work=authorized_next_work,
            failed=[],
        )
        | {
            "status": DISABLED_STATUS if not enabled else REJECT_STATUS,
            "authorized_current_work": authorized_current_work,
        },
    }


def _review_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = base._dict(payload.get("final_decision"))
    schema_version = payload.get("schema_version")
    if schema_version == POST_REVIEW_SCHEMA_VERSION:
        analysis = base._dict(payload.get("analysis"))
        passed_review_checks = [
            check
            for check in base._list(payload.get("review_checks"))
            if isinstance(check, dict) and check.get("passed") is True
        ]
        required_behavior = [
            str(check.get("expected"))
            for check in passed_review_checks
            if str(check.get("name", "")).startswith("materializer_contains_")
            and isinstance(check.get("expected"), str)
        ]
        return {
            "schema_version": schema_version,
            "status": decision.get("status"),
            "passed": decision.get("passed"),
            "failed_checks": decision.get("failed_checks"),
            "authorized_next_work": decision.get("authorized_next_work"),
            "post_review_checks_all_passed": all(
                isinstance(check, dict) and check.get("passed") is True
                for check in base._list(payload.get("review_checks"))
            ),
            **{flag: decision.get(flag) for flag in SOURCE_FALSE_FLAGS},
            **{flag: decision.get(flag) for flag in POST_REVIEW_REQUIRED_TRUE_FLAGS},
            "required_future_materializer_behavior": required_behavior,
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
            "math_boundary": {
                "candidate_operation": analysis.get("candidate_operation"),
                "score_expression": analysis.get("score_expression"),
                "nonnegative_simplex_weights_only": analysis.get(
                    "nonnegative_simplex_weights_only"
                ),
                "master_problem_remains_convex": analysis.get(
                    "master_problem_remains_convex"
                ),
            },
        }

    review = base._dict(payload.get("implementation_static_contract_review"))
    math_boundary = base._dict(review.get("math_boundary"))
    return {
        "schema_version": schema_version,
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "materialization_implementation_authorized_next": decision.get(
            "materialization_implementation_authorized_next"
        ),
        **{flag: decision.get(flag) for flag in SOURCE_FALSE_FLAGS},
        "required_future_materializer_behavior": base._list(
            review.get("required_future_materializer_behavior")
        ),
        "required_zero_intersections": base._dict(review.get("required_zero_intersections")),
        "required_registry_inputs": base._dict(review.get("required_registry_inputs")),
        "math_boundary": math_boundary,
    }


def _source_review_checks(
    summary: dict[str, Any],
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    if summary["schema_version"] == POST_REVIEW_SCHEMA_VERSION:
        return [
            base._check("source_review_schema_version", summary["schema_version"] == POST_REVIEW_SCHEMA_VERSION, summary["schema_version"], POST_REVIEW_SCHEMA_VERSION),
            base._check("source_review_status_passed", summary["status"] == POST_REVIEW_PASS_STATUS, summary["status"], POST_REVIEW_PASS_STATUS),
            base._check("source_review_passed", summary["passed"] is True, summary["passed"], True),
            base._check("source_review_failed_checks_empty", summary["failed_checks"] == [], summary["failed_checks"], []),
            base._check("source_review_authorizes_current_work", summary["authorized_next_work"] == authorized_current_work, summary["authorized_next_work"], authorized_current_work),
            base._check("source_review_materialization_flags_true", all(summary.get(flag) is True for flag in POST_REVIEW_REQUIRED_TRUE_FLAGS), {flag: summary.get(flag) for flag in POST_REVIEW_REQUIRED_TRUE_FLAGS}, "all True"),
            base._check("source_review_blocks_action_leaks", all(summary.get(flag) is False for flag in SOURCE_FALSE_FLAGS), {flag: summary.get(flag) for flag in SOURCE_FALSE_FLAGS}, "all False"),
            base._check("source_review_checks_all_passed", summary["post_review_checks_all_passed"] is True, summary["post_review_checks_all_passed"], True),
            base._check("source_review_required_behavior_present", set(REQUIRED_BEHAVIOR) <= set(summary["required_future_materializer_behavior"]), summary["required_future_materializer_behavior"], "required behavior"),
            base._check("source_review_zero_contract_all_zero", all(summary["required_zero_intersections"].get(key) == 0 for key in ZERO_INTERSECTION_KEYS), summary["required_zero_intersections"], "all zero"),
            base._check("source_review_math_score_affine", summary["math_boundary"].get("score_expression") == SCORE_EXPRESSION, summary["math_boundary"], SCORE_EXPRESSION),
            base._check("source_review_math_simplex_convex", summary["math_boundary"].get("nonnegative_simplex_weights_only") is True and summary["math_boundary"].get("master_problem_remains_convex") is True, summary["math_boundary"], "nonnegative simplex convex"),
        ]

    return [
        base._check("source_review_schema_version", summary["schema_version"] == SOURCE_REVIEW_SCHEMA_VERSION, summary["schema_version"], SOURCE_REVIEW_SCHEMA_VERSION),
        base._check("source_review_status_passed", summary["status"] == SOURCE_REVIEW_PASS_STATUS, summary["status"], SOURCE_REVIEW_PASS_STATUS),
        base._check("source_review_passed", summary["passed"] is True, summary["passed"], True),
        base._check("source_review_failed_checks_empty", summary["failed_checks"] == [], summary["failed_checks"], []),
        base._check("source_review_authorizes_current_work", summary["authorized_next_work"] == authorized_current_work, summary["authorized_next_work"], authorized_current_work),
        base._check("source_review_authorizes_materialization_implementation", summary["materialization_implementation_authorized_next"] is True, summary["materialization_implementation_authorized_next"], True),
        base._check("source_review_blocks_action_leaks", all(summary.get(flag) is False for flag in SOURCE_FALSE_FLAGS), {flag: summary.get(flag) for flag in SOURCE_FALSE_FLAGS}, "all False"),
        base._check("source_review_required_behavior_present", set(REQUIRED_BEHAVIOR) <= set(summary["required_future_materializer_behavior"]), summary["required_future_materializer_behavior"], "required behavior"),
        base._check("source_review_zero_contract_all_zero", all(summary["required_zero_intersections"].get(key) == 0 for key in ZERO_INTERSECTION_KEYS), summary["required_zero_intersections"], "all zero"),
        base._check("source_review_math_score_affine", summary["math_boundary"].get("score_expression") == SCORE_EXPRESSION, summary["math_boundary"], SCORE_EXPRESSION),
        base._check("source_review_math_simplex_convex", summary["math_boundary"].get("nonnegative_simplex_weights_only") is True and summary["math_boundary"].get("master_problem_remains_convex") is True, summary["math_boundary"], "nonnegative simplex convex"),
    ]


def _audit_boundary_checks(audit_text: str) -> list[dict[str, Any]]:
    checks = [
        base._check(
            f"audit_blocks_{flag}",
            base._latest_value(audit_text, flag) == "False",
            base._latest_value(audit_text, flag),
            "False",
        )
        for flag in AUDIT_FALSE_FLAGS
    ]
    checks.extend(
        [
            base._check(
                "audit_authorizes_materialization_only",
                base._latest_value(audit_text, "materialization_only_authorized_next")
                == "True",
                base._latest_value(audit_text, "materialization_only_authorized_next"),
                "True",
            ),
            base._check(
                "audit_authorizes_materialization_execution",
                base._latest_value(audit_text, "materialization_execution_authorized_next")
                == "True",
                base._latest_value(
                    audit_text, "materialization_execution_authorized_next"
                ),
                "True",
            ),
        ]
    )
    return checks


def _decision(
    *,
    passed: bool,
    enabled: bool,
    authorized_next_work: str | None,
    failed: list[str],
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else (REJECT_STATUS if enabled else DISABLED_STATUS),
        "passed": passed,
        "enabled": enabled,
        "failed_checks": failed,
        "authorized_next_work": authorized_next_work if passed else None,
        "member_source_manifest_written": passed,
        "materialization_complete": passed,
        "validation_preflight_authorized_next": passed,
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
        "fixed_dp_candidate_generation_executed": False,
        "candidate_generation_by_camp_executed": False,
        "trajectory_generation_by_camp_executed": False,
        "trajectory_modification_by_camp_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }


def _patch_base_next_work(authorized_next_work: str) -> None:
    base.AUTHORIZED_NEXT_WORK = authorized_next_work


if __name__ == "__main__":
    raise SystemExit(main())
