#!/usr/bin/env python3
"""Default-off builder for v13 fresh evaluation split member sources.

This implementation is a fail-closed data-contract builder. It can select
fresh split member-source records only from an already materialized candidate
member manifest and already materialized registries. It does not run Diffusion
Planner, generate candidates, rewrite trajectories, run replay, train CAMP,
modify DP, promote, deploy, or make safety/CAMP-over-DP claims.
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
SCHEMA_VERSION = "dp_camp_v13_fresh_evaluation_split_member_source_builder_v1"
DISABLED_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_builder_default_off_disabled"
)
READY_STATUS = "dp_camp_v13_fresh_evaluation_split_member_source_builder_complete"
REJECT_STATUS = "dp_camp_v13_fresh_evaluation_split_member_source_builder_rejected"
SOURCE_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_"
    "implementation_static_contract_review_v1"
)
SOURCE_REVIEW_PASS_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_"
    "implementation_static_contract_review_passed"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_remediation_implementation_static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "implementation_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "post_implementation_static_contract_review_only"
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
SHA256SUMS_NAME = "SHA256SUMS.txt"
OUTPUT_FILES = (
    "fresh_evaluation_split_member_source_manifest.json",
    "fresh_evaluation_split_member_source_nonoverlap_report.json",
    "fresh_evaluation_split_member_source_preflight_inputs.json",
)
ZERO_INTERSECTION_KEYS = (
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
REQUIRED_BEHAVIOR = (
    "load_training_candidate_tensor_hash_registry_before_member_selection",
    "load_training_path_signature_registry_before_member_selection",
    "load_training_record_identity_registry_before_member_selection",
    "load_training_split_manifest_root_registry_before_member_selection",
    "load_recovered_prior_registry_before_member_selection",
    "load_rejected_overlap_source_registry_before_member_selection",
    "fail_closed_when_any_required_registry_is_missing_empty_or_unreadable",
    "exclude_every_member_from_the_rejected_overlap_source",
    "prove_zero_candidate_tensor_hash_intersection",
    "prove_zero_path_signature_intersection",
    "prove_zero_record_identity_intersection",
    "prove_zero_split_manifest_root_intersection",
    "reject_split_root_only_acceptance",
    "exclude_formal_seeds_11_12_13_and_full36",
    "preserve_default_off_shadow_selector_and_executed_dp_top1",
    "forbid_camp_candidate_generation_or_trajectory_modification",
    "forbid_reference_blend_guidance_postprocess_postselection",
    "forbid_closed_loop_outcomes_as_training_or_online_input",
    "write_immutable_sha256_manifest_for_all_outputs",
)
SOURCE_FALSE_FLAGS = (
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
FORMAL_SEEDS = {11, 12, 13}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Default-off fail-closed builder for fresh evaluation split "
            "member-source manifests."
        )
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
        "--enable_v13_fresh_evaluation_split_member_source_builder",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_member_source_report(
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
        enabled=args.enable_v13_fresh_evaluation_split_member_source_builder,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    if report["final_decision"]["member_source_manifest_written"]:
        _write_sha256sums(args.output_dir, list(OUTPUT_FILES))
        report["output_hashes"]["sha256sums_txt_sha256"] = _sha256(
            args.output_dir / SHA256SUMS_NAME
        )
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["status"] != REJECT_STATUS else 1


def build_member_source_report(
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

    audit_text = _read_text_if_exists(v13_audit_md)
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _check(
            "camp_head_matches_origin_main",
            current_camp_head == current_camp_origin_main,
            current_camp_head,
            current_camp_origin_main,
        ),
        _check(
            "current_dp_head_fixed",
            current_dp_head == required_dp_head == FIXED_DP_HEAD,
            current_dp_head,
            FIXED_DP_HEAD,
        ),
        _check(
            "expected_static_contract_review_sha256_valid",
            _is_sha256(expected_static_contract_review_sha256),
            expected_static_contract_review_sha256,
            "sha256",
        ),
        _check("output_dir_is_not_file", not output_dir.is_file(), str(output_dir), "not a file"),
        _check("output_json_under_output_dir", _is_relative_to(output_json, output_dir), str(output_json), str(output_dir)),
        _check("output_md_under_output_dir", _is_relative_to(output_md, output_dir), str(output_md), str(output_dir)),
        _check(
            "latest_audit_status_authorizes_builder",
            _latest_value(audit_text, "current_v13_status") == LATEST_AUDIT_STATUS,
            _latest_value(audit_text, "current_v13_status"),
            LATEST_AUDIT_STATUS,
        ),
        _check(
            "latest_audit_target_authorizes_builder",
            _latest_value(audit_text, "next_work_target") == authorized_current_work,
            _latest_value(audit_text, "next_work_target"),
            authorized_current_work,
        ),
    ]
    checks.extend(_audit_boundary_checks(audit_text))

    review_payload, review_checks = _load_source_json(
        implementation_static_contract_review_json,
        "implementation_static_contract_review_json",
    )
    candidate_payload, candidate_checks = _load_source_json(
        candidate_member_source_manifest_json,
        "candidate_member_source_manifest_json",
    )
    checks.extend(review_checks)
    checks.extend(candidate_checks)
    if implementation_static_contract_review_json.is_file():
        review_sha = _sha256(implementation_static_contract_review_json)
        report["source_hashes"]["implementation_static_contract_review_json_sha256"] = review_sha
        checks.append(
            _check(
                "static_contract_review_sha256_matches_expected",
                review_sha == expected_static_contract_review_sha256.lower(),
                review_sha,
                expected_static_contract_review_sha256.lower(),
            )
        )

    review_summary = _review_summary(review_payload)
    checks.extend(_source_review_checks(review_summary, authorized_current_work))

    training_bundle = _training_registry_bundle(
        candidate_path=training_candidate_tensor_hash_registry_json,
        path_signature_path=training_path_signature_registry_json,
        record_identity_path=training_record_identity_registry_json,
        split_root_path=training_split_manifest_root_registry_json,
    )
    recovered_bundle = _source_registry_bundle(
        recovered_prior_registry_manifest_json,
        "recovered_prior",
    )
    rejected_bundle = _source_registry_bundle(
        rejected_overlap_source_registry_manifest_json,
        "rejected_overlap_source",
    )
    checks.extend(training_bundle["checks"])
    checks.extend(recovered_bundle["checks"])
    checks.extend(rejected_bundle["checks"])
    report["source_hashes"].update(training_bundle["hashes"])
    report["source_hashes"].update(recovered_bundle["hashes"])
    report["source_hashes"].update(rejected_bundle["hashes"])

    candidates = _candidate_members(candidate_payload)
    selection = _select_fresh_members(
        candidates=candidates,
        reference_bundles=[training_bundle, recovered_bundle, rejected_bundle],
        rejected_overlap_source_registry_manifest_json=(
            rejected_overlap_source_registry_manifest_json
        ),
    )
    checks.extend(_selection_checks(selection))
    planned_outputs = _build_outputs(
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
    checks.extend(_output_absence_checks(planned_outputs, output_json, output_md))

    passed = all(check["passed"] for check in checks)
    report["checks"] = checks
    report["source_summaries"] = {
        "implementation_static_contract_review": review_summary,
        "candidate_member_source_manifest": {
            "schema_version": candidate_payload.get("schema_version"),
            "candidate_member_count": len(candidates),
        },
        "training_registries": _bundle_summary(training_bundle),
        "recovered_prior_registry": _bundle_summary(recovered_bundle),
        "rejected_overlap_source_registry": _bundle_summary(rejected_bundle),
    }
    report["selection_summary"] = selection["summary"]
    report["planned_outputs"] = {key: str(value["path"]) for key, value in planned_outputs.items()}

    if passed:
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(
            planned_outputs["member_source_manifest"]["path"],
            planned_outputs["member_source_manifest"]["payload"],
        )
        _write_json(
            planned_outputs["nonoverlap_report"]["path"],
            planned_outputs["nonoverlap_report"]["payload"],
        )
        _write_json(
            planned_outputs["preflight_inputs"]["path"],
            planned_outputs["preflight_inputs"]["payload"],
        )
        report["output_hashes"].update(
            {
                "fresh_evaluation_split_member_source_manifest_sha256": _sha256(
                    planned_outputs["member_source_manifest"]["path"]
                ),
                "fresh_evaluation_split_member_source_nonoverlap_report_sha256": _sha256(
                    planned_outputs["nonoverlap_report"]["path"]
                ),
                "fresh_evaluation_split_member_source_preflight_inputs_sha256": _sha256(
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
        "# V13 Fresh Evaluation Split Member-Source Builder",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Enabled: `{decision['enabled']}`",
        f"- Member-source manifest written: `{decision['member_source_manifest_written']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        (
            "This builder is default-off and fail-closed. It consumes only "
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
            "implementation_gate": True,
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
    decision = _dict(payload.get("final_decision"))
    review = _dict(payload.get("static_contract_review"))
    math_boundary = _dict(review.get("math_boundary"))
    return {
        "schema_version": payload.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "member_source_remediation_implementation_authorized_next": decision.get(
            "member_source_remediation_implementation_authorized_next"
        ),
        "implementation_authorized_next": decision.get("implementation_authorized_next"),
        **{flag: decision.get(flag) for flag in SOURCE_FALSE_FLAGS},
        "required_future_builder_behavior": _list(
            review.get("required_future_builder_behavior")
        ),
        "required_zero_intersections": _dict(review.get("required_zero_intersections")),
        "required_registry_inputs": _dict(review.get("required_registry_inputs")),
        "source_failure_to_remediate": _dict(review.get("source_failure_to_remediate")),
        "math_boundary": math_boundary,
    }


def _source_review_checks(
    summary: dict[str, Any],
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    return [
        _check("source_review_schema_version", summary["schema_version"] == SOURCE_REVIEW_SCHEMA_VERSION, summary["schema_version"], SOURCE_REVIEW_SCHEMA_VERSION),
        _check("source_review_status_passed", summary["status"] == SOURCE_REVIEW_PASS_STATUS, summary["status"], SOURCE_REVIEW_PASS_STATUS),
        _check("source_review_passed", summary["passed"] is True, summary["passed"], True),
        _check("source_review_failed_checks_empty", summary["failed_checks"] == [], summary["failed_checks"], []),
        _check("source_review_authorizes_current_work", summary["authorized_next_work"] == authorized_current_work, summary["authorized_next_work"], authorized_current_work),
        _check("source_review_authorizes_implementation", summary["implementation_authorized_next"] is True, summary["implementation_authorized_next"], True),
        _check("source_review_blocks_action_leaks", all(summary.get(flag) is False for flag in SOURCE_FALSE_FLAGS), {flag: summary.get(flag) for flag in SOURCE_FALSE_FLAGS}, "all False"),
        _check("source_review_required_behavior_present", set(REQUIRED_BEHAVIOR) <= set(summary["required_future_builder_behavior"]), summary["required_future_builder_behavior"], "required behavior"),
        _check("source_review_zero_contract_all_zero", all(summary["required_zero_intersections"].get(key) == 0 for key in ZERO_INTERSECTION_KEYS), summary["required_zero_intersections"], "all zero"),
        _check("source_review_math_score_affine", summary["math_boundary"].get("score_expression") == SCORE_EXPRESSION, summary["math_boundary"], SCORE_EXPRESSION),
        _check("source_review_math_simplex_convex", summary["math_boundary"].get("nonnegative_simplex_weights_only") is True and summary["math_boundary"].get("master_problem_remains_convex") is True, summary["math_boundary"], "nonnegative simplex convex"),
    ]


def _training_registry_bundle(
    *,
    candidate_path: Path,
    path_signature_path: Path,
    record_identity_path: Path,
    split_root_path: Path,
) -> dict[str, Any]:
    bundle = _empty_bundle("training")
    for kind, path, keys in (
        ("candidate_tensor_hashes", candidate_path, _candidate_hash_keys()),
        ("path_signatures", path_signature_path, _path_signature_keys()),
        ("record_identity_hashes", record_identity_path, _record_identity_keys()),
        ("split_manifest_roots", split_root_path, _split_root_keys()),
    ):
        values, checks, digest = _load_direct_registry(path, f"training_{kind}", keys)
        bundle[kind] = values
        bundle["checks"].extend(checks)
        if digest:
            bundle["hashes"][f"training_{kind}_sha256"] = digest
    return bundle


def _source_registry_bundle(path: Path, label: str) -> dict[str, Any]:
    bundle = _empty_bundle(label)
    payload, checks = _load_source_json(path, f"{label}_registry_manifest_json")
    bundle["checks"].extend(checks)
    if path.is_file():
        bundle["hashes"][f"{label}_registry_manifest_json_sha256"] = _sha256(path)
    references = {
        "candidate_tensor_hashes": (
            "candidate_tensor_hash_registry_json",
            "candidate_tensor_hashes_json",
        ),
        "path_signatures": (
            "path_signature_registry_json",
            "path_signatures_json",
        ),
        "record_identity_hashes": (
            "record_identity_hash_registry_json",
            "record_identity_hashes_json",
        ),
        "split_manifest_roots": (
            "split_manifest_root_registry_json",
            "split_manifest_json",
        ),
    }
    key_lookup = {
        "candidate_tensor_hashes": _candidate_hash_keys(),
        "path_signatures": _path_signature_keys(),
        "record_identity_hashes": _record_identity_keys(),
        "split_manifest_roots": _split_root_keys(),
    }
    for kind, ref_keys in references.items():
        values = _extract_registry_values(payload, key_lookup[kind])
        ref_path = _first_existing_reference(payload, ref_keys)
        if ref_path is not None:
            ref_values, ref_checks, digest = _load_direct_registry(
                ref_path,
                f"{label}_{kind}",
                key_lookup[kind],
            )
            values |= ref_values
            bundle["checks"].extend(ref_checks)
            if digest:
                bundle["hashes"][f"{label}_{kind}_sha256"] = digest
        bundle[kind] = values
        bundle["checks"].append(
            _check(
                f"{label}_{kind}_nonempty",
                len(values) > 0,
                len(values),
                ">0 values",
            )
        )
    return bundle


def _load_direct_registry(
    path: Path,
    label: str,
    keys: tuple[str, ...],
) -> tuple[set[str], list[dict[str, Any]], str | None]:
    payload, checks = _load_source_json(path, f"{label}_json")
    digest = _sha256(path) if path.is_file() else None
    values = _extract_registry_values(payload, keys)
    checks.append(_check(f"{label}_nonempty", len(values) > 0, len(values), ">0 values"))
    return values, checks, digest


def _empty_bundle(label: str) -> dict[str, Any]:
    return {
        "label": label,
        "candidate_tensor_hashes": set(),
        "path_signatures": set(),
        "record_identity_hashes": set(),
        "split_manifest_roots": set(),
        "checks": [],
        "hashes": {},
    }


def _candidate_members(payload: dict[str, Any]) -> list[dict[str, Any]]:
    members = payload.get("members")
    if not isinstance(members, list):
        members = payload.get("candidate_members")
    return [member for member in _list(members) if isinstance(member, dict)]


def _select_fresh_members(
    *,
    candidates: list[dict[str, Any]],
    reference_bundles: list[dict[str, Any]],
    rejected_overlap_source_registry_manifest_json: Path,
) -> dict[str, Any]:
    reference_sets = {
        "candidate_tensor_hashes": set().union(
            *(bundle["candidate_tensor_hashes"] for bundle in reference_bundles)
        ),
        "path_signatures": set().union(
            *(bundle["path_signatures"] for bundle in reference_bundles)
        ),
        "record_identity_hashes": set().union(
            *(bundle["record_identity_hashes"] for bundle in reference_bundles)
        ),
        "split_manifest_roots": set().union(
            *(bundle["split_manifest_roots"] for bundle in reference_bundles)
        ),
    }
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    rejected_manifest = str(rejected_overlap_source_registry_manifest_json)
    for index, member in enumerate(candidates):
        member_sets = _member_sets(member)
        reasons = []
        intersections = {
            "candidate_tensor_hash_intersection_count": len(
                member_sets["candidate_tensor_hashes"] & reference_sets["candidate_tensor_hashes"]
            ),
            "path_signature_intersection_count": len(
                member_sets["path_signatures"] & reference_sets["path_signatures"]
            ),
            "record_identity_intersection_count": len(
                member_sets["record_identity_hashes"] & reference_sets["record_identity_hashes"]
            ),
            "split_manifest_root_intersection_count": len(
                member_sets["split_manifest_roots"] & reference_sets["split_manifest_roots"]
            ),
        }
        for key, count in intersections.items():
            if count:
                reasons.append(key)
        if _member_uses_rejected_source(member, rejected_manifest):
            reasons.append("rejected_overlap_source_member")
        if _member_formal_seed_count(member):
            reasons.append("formal_seed_11_12_13")
        if _member_is_full36(member):
            reasons.append("full36")
        if any(len(member_sets[key]) == 0 for key in member_sets):
            reasons.append("missing_member_identity_fields")
        if reasons:
            rejected.append(
                {
                    "member_index": index,
                    "member_id": member.get("member_id") or member.get("id") or str(index),
                    "reasons": sorted(set(reasons)),
                    "intersection_counts": intersections,
                }
            )
            continue
        selected.append(_selected_member(member, index, member_sets))

    selected_sets = {
        key: set().union(*(_member_sets(member)[key] for member in selected))
        if selected
        else set()
        for key in (
            "candidate_tensor_hashes",
            "path_signatures",
            "record_identity_hashes",
            "split_manifest_roots",
        )
    }
    zero_counts = {
        "candidate_tensor_hash_intersection_count": len(
            selected_sets["candidate_tensor_hashes"] & reference_sets["candidate_tensor_hashes"]
        ),
        "path_signature_intersection_count": len(
            selected_sets["path_signatures"] & reference_sets["path_signatures"]
        ),
        "record_identity_intersection_count": len(
            selected_sets["record_identity_hashes"] & reference_sets["record_identity_hashes"]
        ),
        "split_manifest_root_intersection_count": len(
            selected_sets["split_manifest_roots"] & reference_sets["split_manifest_roots"]
        ),
    }
    return {
        "selected_members": selected,
        "rejected_members": rejected,
        "summary": {
            "candidate_member_count": len(candidates),
            "selected_member_count": len(selected),
            "rejected_member_count": len(rejected),
            "zero_intersection_counts": zero_counts,
            "selected_formal_seed_count": sum(_member_formal_seed_count(member) for member in selected),
            "selected_full36_count": sum(1 for member in selected if _member_is_full36(member)),
            "selected_rejected_source_count": sum(
                1 for member in selected if _member_uses_rejected_source(member, rejected_manifest)
            ),
        },
    }


def _selected_member(
    member: dict[str, Any],
    index: int,
    member_sets: dict[str, set[str]],
) -> dict[str, Any]:
    return {
        "member_id": str(member.get("member_id") or member.get("id") or index),
        "source_path": member.get("source_path"),
        "route": member.get("route"),
        "seed": member.get("seed"),
        "candidate_tensor_hashes": sorted(member_sets["candidate_tensor_hashes"]),
        "path_signatures": sorted(member_sets["path_signatures"]),
        "record_identity_hashes": sorted(member_sets["record_identity_hashes"]),
        "split_manifest_roots": sorted(member_sets["split_manifest_roots"]),
    }


def _selection_checks(selection: dict[str, Any]) -> list[dict[str, Any]]:
    summary = selection["summary"]
    zero_counts = summary["zero_intersection_counts"]
    return [
        _check("candidate_member_source_members_nonempty", summary["candidate_member_count"] > 0, summary["candidate_member_count"], ">0 candidates"),
        _check("fresh_member_source_candidates_after_filters_nonempty", summary["selected_member_count"] > 0, summary["selected_member_count"], ">0 selected"),
        _check("selected_candidate_tensor_hash_intersection_zero", zero_counts["candidate_tensor_hash_intersection_count"] == 0, zero_counts["candidate_tensor_hash_intersection_count"], 0),
        _check("selected_path_signature_intersection_zero", zero_counts["path_signature_intersection_count"] == 0, zero_counts["path_signature_intersection_count"], 0),
        _check("selected_record_identity_intersection_zero", zero_counts["record_identity_intersection_count"] == 0, zero_counts["record_identity_intersection_count"], 0),
        _check("selected_split_manifest_root_intersection_zero", zero_counts["split_manifest_root_intersection_count"] == 0, zero_counts["split_manifest_root_intersection_count"], 0),
        _check("rejected_overlap_source_excluded", summary["selected_rejected_source_count"] == 0, summary["selected_rejected_source_count"], 0),
        _check("formal_seeds_excluded", summary["selected_formal_seed_count"] == 0, summary["selected_formal_seed_count"], 0),
        _check("full36_excluded", summary["selected_full36_count"] == 0, summary["selected_full36_count"], 0),
    ]


def _build_outputs(
    *,
    review_summary: dict[str, Any],
    candidate_member_source_manifest_json: Path,
    training_bundle: dict[str, Any],
    recovered_bundle: dict[str, Any],
    rejected_bundle: dict[str, Any],
    selection: dict[str, Any],
    output_dir: Path,
    current_camp_head: str,
    current_dp_head: str,
) -> dict[str, dict[str, Any]]:
    selected_members = selection["selected_members"]
    zero_counts = selection["summary"]["zero_intersection_counts"]
    common_contract = {
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
        "nonnegative_simplex_weights_only": True,
        "master_problem_remains_convex": True,
        "default_off_shadow_selector": True,
        "executed_trajectory_remains_dp_top1": True,
        "fixed_dp_candidate_generation": False,
        "candidate_generation_by_camp": False,
        "trajectory_generation_by_camp": False,
        "trajectory_modification_by_camp": False,
        "reference_blend": False,
        "guidance": False,
        "postprocess_or_postselection": False,
        "closed_loop_outcome_input": False,
        "replay": False,
        "training": False,
        "dp_modification": False,
        "promotion": False,
        "deployment": False,
        "safety_or_camp_over_dp_claim": False,
    }
    manifest = {
        "schema_version": MEMBER_SOURCE_MANIFEST_SCHEMA_VERSION,
        "manifest_role": "fresh_evaluation_split_member_source_manifest",
        "current_camp_head": current_camp_head,
        "current_dp_head": current_dp_head,
        "source_candidate_member_source_manifest_json": str(candidate_member_source_manifest_json),
        "source_candidate_member_source_manifest_sha256": _sha256(candidate_member_source_manifest_json),
        "selected_member_count": len(selected_members),
        "selected_members": selected_members,
        "required_zero_intersections": {
            key: review_summary["required_zero_intersections"].get(key, 0)
            for key in ZERO_INTERSECTION_KEYS
        },
        "zero_intersection_counts": zero_counts,
        "math_and_runtime_boundary": common_contract,
    }
    report = {
        "schema_version": NONOVERLAP_REPORT_SCHEMA_VERSION,
        "manifest_role": "fresh_evaluation_split_member_source_nonoverlap_report",
        "zero_intersection_proof_executed_by_this_builder": True,
        "zero_intersection_counts": zero_counts,
        "training_registry_summary": _bundle_summary(training_bundle),
        "recovered_prior_registry_summary": _bundle_summary(recovered_bundle),
        "rejected_overlap_source_registry_summary": _bundle_summary(rejected_bundle),
        "rejected_members": selection["rejected_members"],
        "split_root_only_acceptance": False,
        "rejected_overlap_source_reuse": False,
        "formal_seed_11_12_13": False,
        "full36": False,
        "math_and_runtime_boundary": common_contract,
    }
    preflight_inputs = {
        "schema_version": PREFLIGHT_INPUTS_SCHEMA_VERSION,
        "manifest_role": "fresh_evaluation_split_member_source_preflight_inputs",
        "fresh_member_source_manifest_json": str(
            output_dir / "fresh_evaluation_split_member_source_manifest.json"
        ),
        "fresh_member_source_nonoverlap_report_json": str(
            output_dir / "fresh_evaluation_split_member_source_nonoverlap_report.json"
        ),
        "expected_zero_intersections": {key: 0 for key in ZERO_INTERSECTION_KEYS},
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "forbidden_next_actions": {
            "fixed_dp_candidate_generation": True,
            "replay": True,
            "training": True,
            "dp_modification": True,
            "promotion": True,
            "deployment": True,
            "safety_or_camp_over_dp_claim": True,
        },
    }
    return {
        "member_source_manifest": {
            "path": output_dir / "fresh_evaluation_split_member_source_manifest.json",
            "payload": manifest,
        },
        "nonoverlap_report": {
            "path": output_dir / "fresh_evaluation_split_member_source_nonoverlap_report.json",
            "payload": report,
        },
        "preflight_inputs": {
            "path": output_dir / "fresh_evaluation_split_member_source_preflight_inputs.json",
            "payload": preflight_inputs,
        },
    }


def _bundle_summary(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": bundle["label"],
        "candidate_tensor_hash_count": len(bundle["candidate_tensor_hashes"]),
        "path_signature_count": len(bundle["path_signatures"]),
        "record_identity_hash_count": len(bundle["record_identity_hashes"]),
        "split_manifest_root_count": len(bundle["split_manifest_roots"]),
    }


def _output_absence_checks(
    planned: dict[str, dict[str, Any]],
    output_json: Path,
    output_md: Path,
) -> list[dict[str, Any]]:
    checks = [
        _check("output_json_absent_before_write", not output_json.exists(), str(output_json), "path absent"),
        _check("output_md_absent_before_write", not output_md.exists(), str(output_md), "path absent"),
    ]
    for key, item in planned.items():
        path = item["path"]
        checks.append(_check(f"{key}_absent_before_write", not path.exists(), str(path), "path absent"))
    checks.append(
        _check(
            "sha256sums_absent_before_write",
            not (planned["member_source_manifest"]["path"].parent / SHA256SUMS_NAME).exists(),
            str(planned["member_source_manifest"]["path"].parent / SHA256SUMS_NAME),
            "path absent",
        )
    )
    return checks


def _audit_boundary_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check(
            f"audit_blocks_{flag}",
            _latest_value(audit_text, flag) == "False",
            _latest_value(audit_text, flag),
            "False",
        )
        for flag in AUDIT_FALSE_FLAGS
    ]


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
        "member_source_remediation_implementation_complete": passed,
        "post_implementation_static_contract_review_authorized_next": passed,
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


def _member_sets(member: dict[str, Any]) -> dict[str, set[str]]:
    return {
        "candidate_tensor_hashes": _extract_registry_values(member, _candidate_hash_keys()),
        "path_signatures": _extract_registry_values(member, _path_signature_keys()),
        "record_identity_hashes": _extract_registry_values(member, _record_identity_keys()),
        "split_manifest_roots": _extract_registry_values(member, _split_root_keys()),
    }


def _candidate_hash_keys() -> tuple[str, ...]:
    return (
        "candidate_tensor_hashes",
        "candidate_tensor_hash",
        "candidate_hashes",
        "candidate_hash",
        "candidate_tensor_eval_hashes",
        "hashes",
    )


def _path_signature_keys() -> tuple[str, ...]:
    return ("path_signatures", "path_signature", "path_signature_hashes")


def _record_identity_keys() -> tuple[str, ...]:
    return (
        "record_identity_hashes",
        "record_identity_hash",
        "record_identities",
        "record_identity",
    )


def _split_root_keys() -> tuple[str, ...]:
    return (
        "split_manifest_roots",
        "split_manifest_root",
        "split_manifest_root_hashes",
        "split_manifest_root_hash",
        "split_manifest_sha256",
    )


def _extract_registry_values(payload: Any, keys: tuple[str, ...]) -> set[str]:
    values: set[str] = set()
    if isinstance(payload, dict):
        for key in keys:
            if key in payload:
                values |= _string_values(payload[key])
        for fallback in ("values", "items"):
            if not values and fallback in payload:
                values |= _string_values(payload[fallback])
        entries = payload.get("entries")
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    for key in (*keys, "value", "hash", "sha256"):
                        if key in entry:
                            values |= _string_values(entry[key])
                else:
                    values |= _string_values(entry)
    else:
        values |= _string_values(payload)
    return {value for value in values if value}


def _string_values(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value} if value else set()
    if isinstance(value, (int, float, bool)):
        return {str(value)}
    if isinstance(value, list):
        values: set[str] = set()
        for item in value:
            values |= _string_values(item)
        return values
    if isinstance(value, dict):
        values: set[str] = set()
        for item in value.values():
            values |= _string_values(item)
        return values
    return set()


def _first_existing_reference(payload: dict[str, Any], keys: tuple[str, ...]) -> Path | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return Path(value)
    return None


def _member_uses_rejected_source(member: dict[str, Any], rejected_manifest: str) -> bool:
    if member.get("source_role") == "rejected_overlap_source":
        return True
    rejected_norm = _norm_path(rejected_manifest)
    for key in ("source_artifact", "source_manifest", "source_registry_manifest", "source_path"):
        value = member.get(key)
        if isinstance(value, str) and _norm_path(value) == rejected_norm:
            return True
    return False


def _member_formal_seed_count(member: dict[str, Any]) -> int:
    seeds = set()
    seed = member.get("seed")
    if isinstance(seed, int):
        seeds.add(seed)
    text = json.dumps(_stable(member), sort_keys=True)
    seeds |= {int(value) for value in re.findall(r"seed[_/-](\d+)", text)}
    return len(seeds & FORMAL_SEEDS)


def _member_is_full36(member: dict[str, Any]) -> bool:
    return bool(member.get("is_full36")) or "full36" in json.dumps(
        _stable(member),
        sort_keys=True,
    ).lower()


def _load_source_json(path: Path, check_name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not path.is_file():
        return {}, [_check(f"{check_name}_exists", False, str(path), "file exists")]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [_check(check_name, False, type(exc).__name__, "valid JSON object")]
    if not isinstance(data, dict):
        return {}, [_check(check_name, False, type(data).__name__, "dict")]
    return data, [
        _check(f"{check_name}_exists", True, str(path), "file exists"),
        _check(check_name, True, "dict", "dict"),
    ]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path, names: list[str]) -> None:
    lines = []
    for name in names:
        path = output_dir / name
        if path.is_file():
            lines.append(f"{_sha256(path)}  {name}")
    (output_dir / SHA256SUMS_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_text_if_exists(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in value)


def _is_git_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _norm_path(value: str) -> str:
    return str(Path(value)).replace("\\", "/").rstrip("/")


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
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
    if isinstance(value, set):
        return sorted(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
