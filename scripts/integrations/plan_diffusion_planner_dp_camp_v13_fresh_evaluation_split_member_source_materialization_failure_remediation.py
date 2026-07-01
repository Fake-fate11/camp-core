#!/usr/bin/env python3
"""Plan remediation for rejected v13 fresh member-source materialization.

This gate is plan-only. It consumes the rejected materializer artifact that
proved candidate member-source inputs are missing, then defines the next
remediation contract. It does not materialize member sources, run DP, generate
candidates, replay, train CAMP, modify DP, promote, deploy, or make
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
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_plan_rejected"
)
SOURCE_SCHEMA_VERSION = "dp_camp_v13_fresh_evaluation_split_member_source_materializer_v1"
SOURCE_REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materializer_rejected"
)
ABSENCE_SCAN_SCHEMA_VERSION = (
    "dp_camp_v13_candidate_member_source_manifest_absence_scan_v1"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_rejected_missing_candidate_member_"
    "source_manifest"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_plan_only"
)
REQUIRED_FAILED_CHECKS = (
    "candidate_member_source_manifest_json_exists",
    "training_split_manifest_roots_json_exists",
    "training_split_manifest_roots_nonempty",
    "candidate_member_source_members_nonempty",
    "fresh_member_source_candidates_after_filters_nonempty",
)
BLOCKED_ACTION_FLAGS = (
    "validation_preflight_authorized_next",
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
BLOCKED_EXECUTION_FLAGS = (
    "fixed_dp_candidate_generation_executed",
    "candidate_generation_by_camp_executed",
    "trajectory_generation_by_camp_executed",
    "trajectory_modification_by_camp_executed",
    "replay_executed",
    "training_executed",
    "dp_modification_executed",
)
AUDIT_FALSE_FLAGS = (
    "validation_preflight_authorized_next",
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
        description=(
            "Plan-only gate for remediating rejected v13 fresh member-source "
            "materialization after candidate member-source inputs were absent."
        )
    )
    parser.add_argument("--materialization_rejection_json", type=Path, required=True)
    parser.add_argument("--expected_materialization_rejection_sha256", required=True)
    parser.add_argument(
        "--candidate_member_source_manifest_absence_scan_json",
        type=Path,
        required=True,
    )
    parser.add_argument("--expected_absence_scan_sha256", required=True)
    parser.add_argument("--materializer_script_py", type=Path, required=True)
    parser.add_argument("--builder_script_py", type=Path, required=True)
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
        materialization_rejection_json=args.materialization_rejection_json,
        expected_materialization_rejection_sha256=(
            args.expected_materialization_rejection_sha256
        ),
        candidate_member_source_manifest_absence_scan_json=(
            args.candidate_member_source_manifest_absence_scan_json
        ),
        expected_absence_scan_sha256=args.expected_absence_scan_sha256,
        materializer_script_py=args.materializer_script_py,
        builder_script_py=args.builder_script_py,
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
    args.output_json.write_text(
        json.dumps(_stable(report), indent=2) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    materialization_rejection_json: Path,
    expected_materialization_rejection_sha256: str,
    candidate_member_source_manifest_absence_scan_json: Path,
    expected_absence_scan_sha256: str,
    materializer_script_py: Path,
    builder_script_py: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    paths = {
        "materialization_rejection_json": materialization_rejection_json.resolve(),
        "candidate_member_source_manifest_absence_scan_json": (
            candidate_member_source_manifest_absence_scan_json.resolve()
        ),
        "materializer_script_py": materializer_script_py.resolve(),
        "builder_script_py": builder_script_py.resolve(),
        "v13_audit_md": v13_audit_md.resolve(),
    }
    source = _load_json_dict(paths["materialization_rejection_json"])
    absence_scan = _load_json_dict(
        paths["candidate_member_source_manifest_absence_scan_json"]
    )
    materializer_text = _read_text(paths["materializer_script_py"])
    builder_text = _read_text(paths["builder_script_py"])
    audit_text = _read_text(paths["v13_audit_md"])
    remediation_plan = _remediation_plan(source, absence_scan)
    checks = _checks(
        paths=paths,
        source=source,
        absence_scan=absence_scan,
        materializer_text=materializer_text,
        builder_text=builder_text,
        audit_text=audit_text,
        remediation_plan=remediation_plan,
        expected_materialization_rejection_sha256=(
            expected_materialization_rejection_sha256
        ),
        expected_absence_scan_sha256=expected_absence_scan_sha256,
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
            "materialization_execution": False,
            "member_source_builder_execution": False,
            "validation_preflight_execution": False,
            "data_preparation_execution": False,
            "training_preflight": False,
            "training_execution": False,
            "replay_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "dp_modification": False,
            "selector_promotion": False,
            "deployment": False,
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
        "materialization_rejection_summary": _rejection_summary(source, absence_scan),
        "remediation_plan": remediation_plan,
        "forbidden_paths": _forbidden_paths(),
        "plan_checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["materialization_rejection_summary"]
    plan = report["remediation_plan"]
    lines = [
        "# V13 Fresh Member-Source Materialization Failure Remediation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Materialization execution authorized: `{decision['materialization_execution_authorized_next']}`",
        f"- Fixed-DP candidate generation authorized: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
        f"- Training authorized: `{decision['training_execution_authorized_next']}`",
        "",
        "## Rejection Summary",
        "",
        f"- Candidate member manifest structures found: `{summary['candidate_member_source_manifest_structures_found']}`",
        f"- Candidate member count: `{summary['candidate_member_count']}`",
        f"- Training split-root registry count: `{summary['training_split_manifest_root_count']}`",
        "",
        "## Required Remediation",
        "",
    ]
    for item in plan["required_remediation_steps"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "The rejected materialization artifact is not an evaluation holdout. "
            "This plan-only gate does not materialize inputs, run DP, generate "
            "candidates, replay, train CAMP, modify DP, promote, deploy, or "
            "authorize safety/CAMP-over-DP claims.",
            "",
        ]
    )
    return "\n".join(lines)


def _remediation_plan(
    source: dict[str, Any],
    absence_scan: dict[str, Any],
) -> dict[str, Any]:
    summary = _rejection_summary(source, absence_scan)
    return {
        "plan_ready_no_inputs_materialized": True,
        "materialization_performed_by_this_gate": False,
        "failure_class": "missing_candidate_member_source_manifest_and_training_split_root_registry",
        "failure_attribution": {
            "candidate_member_source_manifest_missing": (
                summary["candidate_member_source_manifest_structures_found"] == 0
                and summary["candidate_member_count"] == 0
            ),
            "training_split_manifest_root_registry_missing": (
                summary["training_split_manifest_root_count"] == 0
            ),
            "split_manifest_root_zero_alone_is_insufficient": True,
            "rejected_materialization_is_not_holdout": True,
        },
        "required_remediation_steps": [
            "materialize_candidate_member_source_manifest_from_existing_fixed_dp_current_source_artifacts_or_plan_a_separate_fixed_dp_candidate_generation_gate_if_none_exist",
            "require_each_candidate_member_to_carry_member_id_source_path_route_seed_candidate_tensor_hashes_path_signatures_record_identity_hashes_and_split_manifest_roots",
            "materialize_nonempty_training_split_manifest_root_registry_in_addition_to_training_candidate_path_and_record_registries",
            "reject_missing_empty_or_unreadable_candidate_member_source_or_training_split_root_inputs_fail_closed",
            "exclude_rejected_overlap_source_artifact_from_evaluation_holdout_and_training_data",
            "require_zero_candidate_tensor_hash_path_signature_record_identity_and_split_manifest_root_intersections_before_validation_replay_or_training",
            "keep_camp_as_fixed_dp_candidate_tensor_reranker_only",
        ],
        "candidate_member_source_manifest_contract": {
            "members_nonempty": True,
            "member_id_required": True,
            "source_path_required": True,
            "route_required": True,
            "seed_required": True,
            "candidate_tensor_hashes_required": True,
            "path_signatures_required": True,
            "record_identity_hashes_required": True,
            "split_manifest_roots_required": True,
            "formal_seeds_11_12_13_excluded": True,
            "full36_excluded": True,
        },
        "training_split_root_registry_contract": {
            "nonempty_registry_required": True,
            "training_candidate_tensor_hash_count_observed": summary[
                "training_candidate_tensor_hash_count"
            ],
            "training_path_signature_count_observed": summary[
                "training_path_signature_count"
            ],
            "training_record_identity_hash_count_observed": summary[
                "training_record_identity_hash_count"
            ],
            "training_split_manifest_root_count_observed": summary[
                "training_split_manifest_root_count"
            ],
            "split_root_zero_alone_is_insufficient": True,
        },
        "required_zero_intersections": {
            "candidate_tensor_hash_intersection_count": 0,
            "path_signature_intersection_count": 0,
            "record_identity_intersection_count": 0,
            "split_manifest_root_intersection_count": 0,
        },
        "math_boundary": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "nonnegative_simplex_weights_only": True,
            "master_problem_remains_convex": True,
            "executed_trajectory_remains_dp_top1": True,
        },
        "next_gate": "fresh_evaluation_split_member_source_materialization_failure_remediation_implementation_plan_only",
    }


def _checks(
    *,
    paths: dict[str, Path],
    source: dict[str, Any],
    absence_scan: dict[str, Any],
    materializer_text: str,
    builder_text: str,
    audit_text: str,
    remediation_plan: dict[str, Any],
    expected_materialization_rejection_sha256: str,
    expected_absence_scan_sha256: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(source.get("final_decision"))
    summaries = _dict(source.get("source_summaries"))
    training = _dict(summaries.get("training_registries"))
    candidate_manifest = _dict(summaries.get("candidate_member_source_manifest"))
    failed_checks = _list(decision.get("failed_checks"))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_candidate_manifest_missing", _latest_value(audit_text, "candidate_member_source_manifest_missing"), "True"),
        _expect("audit_training_split_root_registry_missing", _latest_value(audit_text, "training_split_manifest_root_registry_missing"), "True"),
        _expect("source_schema_version", source.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status_rejected", decision.get("status"), SOURCE_REJECT_STATUS),
        _expect("source_passed_false", decision.get("passed"), False),
        _expect("source_authorized_next_none", decision.get("authorized_next_work"), None),
        _expect("source_materialization_complete_false", decision.get("materialization_complete"), False),
        _expect("source_member_source_manifest_written_false", decision.get("member_source_manifest_written"), False),
        _expect("source_candidate_member_count_zero", candidate_manifest.get("candidate_member_count"), 0),
        _expect("source_training_split_roots_zero", training.get("split_manifest_root_count"), 0),
        _check("source_training_candidate_hashes_nonempty", _int(training.get("candidate_tensor_hash_count")) > 0, training.get("candidate_tensor_hash_count"), ">0"),
        _check("source_training_path_signatures_nonempty", _int(training.get("path_signature_count")) > 0, training.get("path_signature_count"), ">0"),
        _check("source_training_record_hashes_nonempty", _int(training.get("record_identity_hash_count")) > 0, training.get("record_identity_hash_count"), ">0"),
        _expect("absence_scan_schema_version", absence_scan.get("schema_version"), ABSENCE_SCAN_SCHEMA_VERSION),
        _expect("absence_scan_structures_found_zero", absence_scan.get("candidate_member_source_manifest_structures_found"), 0),
        _expect("materialization_rejection_sha256", _sha256(paths["materialization_rejection_json"]), expected_materialization_rejection_sha256),
        _expect("absence_scan_sha256", _sha256(paths["candidate_member_source_manifest_absence_scan_json"]), expected_absence_scan_sha256),
    ]
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file exists"))
    for failed_name in REQUIRED_FAILED_CHECKS:
        checks.append(
            _check(
                f"source_failed_check_contains_{failed_name}",
                failed_name in failed_checks,
                failed_checks,
                failed_name,
            )
        )
    for flag in BLOCKED_ACTION_FLAGS:
        checks.append(_expect(f"source_blocks_{flag}", decision.get(flag), False))
    for flag in BLOCKED_EXECUTION_FLAGS:
        checks.append(_expect(f"source_did_not_execute_{flag}", decision.get(flag), False))
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _latest_value(audit_text, flag), "False"))
    for needle in (
        "candidate_member_source_manifest_json",
        "training_split_manifest_root_registry_json",
        "reject_split_root_only_acceptance",
        "exclude_formal_seeds_11_12_13_and_full36",
        "SCORE_EXPRESSION",
    ):
        checks.append(_contains(f"materializer_contains_{_slug(needle)}", materializer_text, needle))
    for needle in (
        "candidate_member_source_manifest_json",
        "training_split_manifest_root_registry_json",
        "exclude_every_member_from_the_rejected_overlap_source",
        "reject_split_root_only_acceptance",
        SCORE_EXPRESSION,
    ):
        checks.append(_contains(f"builder_contains_{_slug(needle)}", builder_text, needle))
    checks.extend(_plan_checks(remediation_plan))
    return checks


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    attribution = plan["failure_attribution"]
    manifest = plan["candidate_member_source_manifest_contract"]
    split_root = plan["training_split_root_registry_contract"]
    math_boundary = plan["math_boundary"]
    required_steps = set(plan["required_remediation_steps"])
    return [
        _expect("plan_does_not_materialize_inputs", plan["materialization_performed_by_this_gate"], False),
        _expect("plan_next_gate_implementation_plan_only", plan["next_gate"], "fresh_evaluation_split_member_source_materialization_failure_remediation_implementation_plan_only"),
        _expect("plan_attribution_candidate_manifest_missing", attribution["candidate_member_source_manifest_missing"], True),
        _expect("plan_attribution_training_split_root_missing", attribution["training_split_manifest_root_registry_missing"], True),
        _expect("plan_rejects_split_root_zero_only", attribution["split_manifest_root_zero_alone_is_insufficient"], True),
        _expect("plan_rejects_rejected_artifact_as_holdout", attribution["rejected_materialization_is_not_holdout"], True),
        _expect("plan_requires_member_id", manifest["member_id_required"], True),
        _expect("plan_requires_split_roots_on_members", manifest["split_manifest_roots_required"], True),
        _expect("plan_excludes_formal_seeds", manifest["formal_seeds_11_12_13_excluded"], True),
        _expect("plan_training_split_root_nonempty_required", split_root["nonempty_registry_required"], True),
        _expect("plan_score_affine", math_boundary["score_expression"], SCORE_EXPRESSION),
        _expect("plan_nonnegative_simplex", math_boundary["nonnegative_simplex_weights_only"], True),
        _expect("plan_master_convex", math_boundary["master_problem_remains_convex"], True),
        _check(
            "plan_requires_zero_intersections",
            all(value == 0 for value in plan["required_zero_intersections"].values()),
            plan["required_zero_intersections"],
            "all zero",
        ),
        _check(
            "plan_requires_candidate_manifest_materialization",
            any("candidate_member_source_manifest" in item for item in required_steps),
            sorted(required_steps),
            "candidate_member_source_manifest remediation",
        ),
    ]


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
        "materialization_failure_remediation_plan_ready": passed,
        "materialization_failure_remediation_implementation_plan_authorized_next": passed,
        "materialization_execution_authorized_next": False,
        "member_source_builder_execution_authorized_next": False,
        "validation_preflight_authorized_next": False,
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
        "materialization_executed": False,
        "member_source_builder_executed": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }


def _rejection_summary(
    source: dict[str, Any],
    absence_scan: dict[str, Any],
) -> dict[str, Any]:
    decision = _dict(source.get("final_decision"))
    summaries = _dict(source.get("source_summaries"))
    candidate_manifest = _dict(summaries.get("candidate_member_source_manifest"))
    training = _dict(summaries.get("training_registries"))
    recovered = _dict(summaries.get("recovered_prior_registry"))
    rejected = _dict(summaries.get("rejected_overlap_source_registry"))
    return {
        "schema_version": source.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": _list(decision.get("failed_checks")),
        "candidate_member_source_manifest_structures_found": absence_scan.get(
            "candidate_member_source_manifest_structures_found"
        ),
        "candidate_member_count": candidate_manifest.get("candidate_member_count"),
        "training_candidate_tensor_hash_count": training.get("candidate_tensor_hash_count"),
        "training_path_signature_count": training.get("path_signature_count"),
        "training_record_identity_hash_count": training.get("record_identity_hash_count"),
        "training_split_manifest_root_count": training.get("split_manifest_root_count"),
        "recovered_prior_split_manifest_root_count": recovered.get("split_manifest_root_count"),
        "rejected_overlap_source_split_manifest_root_count": rejected.get("split_manifest_root_count"),
    }


def _forbidden_paths() -> list[str]:
    return [
        "materializing candidate member-source inputs in this plan gate",
        "running the member-source builder in this plan gate",
        "running Diffusion Planner or fixed-DP candidate generation in this plan gate",
        "using CAMP to generate, repair, rewrite, or blend trajectories",
        "using rejected-overlap artifacts as evaluation holdout or training data",
        "treating split_manifest_root_intersection_count=0 as sufficient when the training split-root registry is empty",
        "running replay, preparing training data, or training CAMP",
        "modifying DP code, config, weights, or checkpoint",
        "promoting selectors or atoms, deploying, or claiming safety/CAMP-over-DP benefit",
    ]


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
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, "present" if needle in text else "missing", needle)


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


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _is_git_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value.lower()).strip("_")[:80]


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
