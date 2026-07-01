#!/usr/bin/env python3
"""Plan implementation for fresh split member-source remediation.

This gate is plan-only. It consumes the passed member-source remediation static
contract review and defines the future implementation contract for selecting a
truly fresh evaluation split member source. It does not select members, run
evaluation or replay, generate fixed-DP candidates, train CAMP, modify DP,
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
SOURCE_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_static_"
    "contract_review_v1"
)
SOURCE_REVIEW_PASS_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_static_"
    "contract_review_passed"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_"
    "implementation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_"
    "implementation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_"
    "implementation_plan_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_"
    "artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_"
    "evaluation_split_member_source_remediation_static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "implementation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "implementation_static_contract_review_only"
)
FUTURE_BUILDER_SCRIPT = (
    "scripts/integrations/build_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source.py"
)
FUTURE_BUILDER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source_builder.py"
)
ZERO_INTERSECTION_KEYS = (
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
REQUIRED_REGISTRY_KEYS = (
    "candidate_tensor_hash_registry_required",
    "path_signature_registry_required",
    "record_identity_hash_registry_required",
    "split_manifest_root_registry_required",
    "training_registry_must_be_loaded",
    "recovered_prior_registry_must_be_loaded",
    "rejected_source_registry_must_be_loaded",
)
BLOCKED_SOURCE_FLAGS = (
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
REQUIRED_CONTRACT_GROUPS = (
    "rejected_preflight_failure_attribution_contract",
    "four_way_zero_intersection_member_source_contract",
    "rejected_source_exclusion_contract",
    "split_root_only_rejection_contract",
    "fixed_dp_affine_simplex_boundary_contract",
    "no_action_authorization_beyond_implementation_plan_gate",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan-only implementation plan for fresh split member-source remediation."
    )
    parser.add_argument("--static_contract_review_json", type=Path, required=True)
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
        static_contract_review_json=args.static_contract_review_json,
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
    static_contract_review_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    source_path = static_contract_review_json.resolve()
    audit_path = v13_audit_md.resolve()
    source_review = _load_json_dict(source_path)
    audit_text = _read_text(audit_path)
    source_summary = _source_summary(source_review)
    plan = _implementation_plan(source_summary)
    checks = _checks(
        source_path=source_path,
        audit_path=audit_path,
        audit_text=audit_text,
        source_review=source_review,
        source_summary=source_summary,
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
            "implementation_execution": False,
            "fresh_member_selection_execution": False,
            "evaluation_execution": False,
            "data_preparation_execution": False,
            "training_preflight": False,
            "training_execution": False,
            "replay_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "dp_modification": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "deployable_checkpoint_claim": False,
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
        "inputs": {
            "static_contract_review_json": str(source_path),
            "v13_audit_md": str(audit_path),
        },
        "source_hashes": {
            "static_contract_review_json_sha256": _sha256(source_path),
            "v13_audit_md_sha256": _sha256(audit_path),
        },
        "source_summary": source_summary,
        "implementation_plan": plan,
        "future_static_contract_review_requirements": _future_static_review_requirements(),
        "forbidden_paths": _forbidden_paths(),
        "plan_checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "member_source_remediation_implementation_plan_ready": passed,
            "member_source_remediation_implementation_static_contract_review_authorized_next": passed,
            "implementation_authorized_next": False,
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
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["implementation_plan"]
    lines = [
        "# V13 Fresh Evaluation Split Member-Source Remediation Implementation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation authorized next: `{decision['implementation_authorized_next']}`",
        f"- Fresh member selection authorized next: `{decision['fresh_member_selection_execution_authorized_next']}`",
        f"- Fixed-DP candidate generation authorized next: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
        f"- Source status: `{report['source_summary']['status']}`",
        f"- Future builder script: `{plan['future_builder_script']}`",
        f"- Future builder test: `{plan['future_builder_test']}`",
        "",
        "## Required Future Builder Behavior",
        "",
    ]
    for item in plan["required_future_builder_behavior"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Future Static Review Requirements", ""])
    for item in report["future_static_contract_review_requirements"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This plan-only gate does not select fresh members, generate candidates, "
            "train CAMP, modify DP, replay, promote, deploy, or make safety/CAMP-over-DP claims.",
            "",
        ]
    )
    return "\n".join(lines)


def _source_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_review.get("final_decision"))
    review = _dict(source_review.get("static_contract_review"))
    attribution = _dict(review.get("failure_attribution_contract"))
    required = _dict(review.get("required_fresh_member_source_contract"))
    registries = _dict(review.get("required_registry_inputs"))
    constraints = _dict(review.get("rejected_source_constraints"))
    next_requirements = _dict(review.get("next_gate_requirements"))
    analysis = _dict(source_review.get("analysis"))
    return {
        "schema_version": source_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "member_source_remediation_implementation_plan_authorized_next": decision.get(
            "member_source_remediation_implementation_plan_authorized_next"
        ),
        "required_contract_groups": review.get("required_contract_groups"),
        "candidate_tensor_hash_intersection_count": attribution.get(
            "candidate_tensor_hash_intersection_count"
        ),
        "path_signature_intersection_count": attribution.get(
            "path_signature_intersection_count"
        ),
        "record_identity_intersection_count": attribution.get(
            "record_identity_intersection_count"
        ),
        "split_manifest_root_intersection_count": attribution.get(
            "split_manifest_root_intersection_count"
        ),
        "root_zero_is_not_sufficient": attribution.get("root_zero_is_not_sufficient"),
        "failed_checks_empty_is_not_pass": attribution.get("failed_checks_empty_is_not_pass"),
        "rejected_overlap_artifact_is_not_evaluation_holdout": constraints.get(
            "rejected_overlap_artifact_is_not_evaluation_holdout"
        ),
        "do_not_relabel_overlapping_members_as_fresh": constraints.get(
            "do_not_relabel_overlapping_members_as_fresh"
        ),
        "candidate_path_record_overlap_requires_member_source_replacement": constraints.get(
            "candidate_path_record_overlap_requires_member_source_replacement"
        ),
        "required_zero_intersections": {
            key: required.get(key) for key in ZERO_INTERSECTION_KEYS
        },
        "required_registry_inputs": {
            key: registries.get(key) for key in REQUIRED_REGISTRY_KEYS
        },
        "review_must_reject_missing_registry_inputs": next_requirements.get(
            "review_must_reject_missing_registry_inputs"
        ),
        "review_must_reject_split_root_only_acceptance": next_requirements.get(
            "review_must_reject_split_root_only_acceptance"
        ),
        "review_must_reject_reusing_rejected_overlap_source": next_requirements.get(
            "review_must_reject_reusing_rejected_overlap_source"
        ),
        "review_must_reject_any_action_authorization_leak": next_requirements.get(
            "review_must_reject_any_action_authorization_leak"
        ),
        "review_must_preserve_fixed_dp_head": next_requirements.get(
            "review_must_preserve_fixed_dp_head"
        ),
        "review_must_preserve_score_affine": next_requirements.get(
            "review_must_preserve_score_affine"
        ),
        "candidate_operation": analysis.get("candidate_operation"),
        "score_expression": analysis.get("score_expression"),
        **{flag: decision.get(flag) for flag in BLOCKED_SOURCE_FLAGS},
    }


def _implementation_plan(source_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "implementation_performed_by_this_gate": False,
        "future_builder_script": FUTURE_BUILDER_SCRIPT,
        "future_builder_test": FUTURE_BUILDER_TEST,
        "future_artifacts": [
            "fresh_evaluation_split_member_source_manifest.json",
            "fresh_evaluation_split_member_source_nonoverlap_report.json",
            "fresh_evaluation_split_member_source_preflight_inputs.json",
            "SHA256SUMS.txt",
        ],
        "required_future_builder_behavior": [
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
        ],
        "required_zero_intersections": source_summary["required_zero_intersections"],
        "required_registry_inputs": source_summary["required_registry_inputs"],
        "source_failure_to_remediate": {
            "candidate_tensor_hash_intersection_count": source_summary[
                "candidate_tensor_hash_intersection_count"
            ],
            "path_signature_intersection_count": source_summary[
                "path_signature_intersection_count"
            ],
            "record_identity_intersection_count": source_summary[
                "record_identity_intersection_count"
            ],
            "split_manifest_root_intersection_count": source_summary[
                "split_manifest_root_intersection_count"
            ],
            "root_zero_is_not_sufficient": source_summary["root_zero_is_not_sufficient"],
        },
        "math_boundary": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "nonnegative_simplex_weights_only": True,
            "master_problem_remains_convex": True,
        },
        "next_gate": (
            "fresh_evaluation_split_member_source_remediation_"
            "implementation_static_contract_review_only"
        ),
    }


def _future_static_review_requirements() -> list[str]:
    return [
        "reject_if_member_source_builder_implementation_is_included_in_plan_gate",
        "reject_if_any_required_registry_input_is_missing",
        "reject_if_any_zero_intersection_check_is_missing_or_not_fail_closed",
        "reject_if_candidate_path_record_or_split_root_overlap_can_pass",
        "reject_if_rejected_overlap_source_can_be_reused_or_relabelled_as_fresh",
        "reject_if_split_root_zero_alone_can_pass",
        "reject_if_formal_seeds_11_12_13_or_full36_are_authorized",
        "reject_if_replay_training_evaluation_or_candidate_generation_is_authorized",
        "reject_if_camp_candidate_generation_or_trajectory_modification_is_possible",
        "reject_if_dp_code_config_or_weight_changes_are_authorized",
        "reject_if_reference_blend_guidance_postprocess_or_postselection_is_allowed",
        "reject_if_closed_loop_outcomes_are_used_as_training_or_online_inputs",
        "reject_if_score_is_not_affine_or_weights_are_not_nonnegative_simplex",
        "reject_if_promotion_deployment_or_safety_claims_are_authorized",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "implementation_code_edit_by_this_gate",
        "fresh_member_selection_by_this_gate",
        "fresh_split_preflight_execution_by_this_gate",
        "evaluation_execution_by_this_gate",
        "replay_execution_by_this_gate",
        "fixed_dp_candidate_generation_execution_by_this_gate",
        "camp_candidate_generation_or_trajectory_modification",
        "diffusion_planner_code_config_or_weight_change",
        "selector_or_atom_promotion",
        "deployment_or_deployable_checkpoint_claim",
        "safety_benefit_or_camp_over_dp_top1_claim",
    ]


def _checks(
    *,
    source_path: Path,
    audit_path: Path,
    audit_text: str,
    source_review: dict[str, Any],
    source_summary: dict[str, Any],
    plan: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    return [
        _check("static_contract_review_json_exists", source_path.is_file(), str(source_path), "file exists"),
        _check("v13_audit_md_exists", audit_path.is_file(), str(audit_path), "file exists"),
        _expect("source_schema_version", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA_VERSION),
        _expect("source_status_passed", source_summary["status"], SOURCE_REVIEW_PASS_STATUS),
        _expect("source_passed", source_summary["passed"], True),
        _expect("source_failed_checks_empty", source_summary["failed_checks"], []),
        _expect("source_authorizes_this_plan", source_summary["authorized_next_work"], authorized_current_work),
        _expect(
            "source_authorizes_member_source_implementation_plan",
            source_summary["member_source_remediation_implementation_plan_authorized_next"],
            True,
        ),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check(
            "source_contract_groups_complete",
            set(REQUIRED_CONTRACT_GROUPS)
            <= set(_list(source_summary["required_contract_groups"])),
            source_summary["required_contract_groups"],
            "required contract groups",
        ),
        _check(
            "source_failure_overlap_evidence_preserved",
            _int(source_summary["candidate_tensor_hash_intersection_count"]) > 0
            and _int(source_summary["path_signature_intersection_count"]) > 0
            and _int(source_summary["record_identity_intersection_count"]) > 0
            and source_summary["split_manifest_root_intersection_count"] == 0,
            {
                key: source_summary[key]
                for key in (
                    "candidate_tensor_hash_intersection_count",
                    "path_signature_intersection_count",
                    "record_identity_intersection_count",
                    "split_manifest_root_intersection_count",
                )
            },
            "candidate/path/record overlap and root zero",
        ),
        _expect("source_root_zero_marked_insufficient", source_summary["root_zero_is_not_sufficient"], True),
        _expect("source_failed_checks_empty_not_pass", source_summary["failed_checks_empty_is_not_pass"], True),
        _expect(
            "source_rejected_overlap_not_holdout",
            source_summary["rejected_overlap_artifact_is_not_evaluation_holdout"],
            True,
        ),
        _expect(
            "source_do_not_relabel_overlapping_members",
            source_summary["do_not_relabel_overlapping_members_as_fresh"],
            True,
        ),
        _check(
            "source_zero_intersection_contracts_present",
            all(source_summary["required_zero_intersections"].get(key) == 0 for key in ZERO_INTERSECTION_KEYS),
            source_summary["required_zero_intersections"],
            "all zero",
        ),
        _check(
            "source_required_registry_inputs_present",
            all(source_summary["required_registry_inputs"].get(key) is True for key in REQUIRED_REGISTRY_KEYS),
            source_summary["required_registry_inputs"],
            "all required",
        ),
        _expect(
            "source_rejects_missing_registry_inputs",
            source_summary["review_must_reject_missing_registry_inputs"],
            True,
        ),
        _expect(
            "source_rejects_split_root_only_acceptance",
            source_summary["review_must_reject_split_root_only_acceptance"],
            True,
        ),
        _expect(
            "source_rejects_rejected_source_reuse",
            source_summary["review_must_reject_reusing_rejected_overlap_source"],
            True,
        ),
        _expect(
            "source_rejects_action_authorization_leak",
            source_summary["review_must_reject_any_action_authorization_leak"],
            True,
        ),
        _expect("source_preserves_fixed_dp_head", source_summary["review_must_preserve_fixed_dp_head"], FIXED_DP_HEAD),
        _expect("source_score_affine", source_summary["review_must_preserve_score_affine"], SCORE_EXPRESSION),
        _expect("source_analysis_score_affine", source_summary["score_expression"], SCORE_EXPRESSION),
        _check(
            "source_blocked_action_flags_false",
            all(source_summary.get(flag) is False for flag in BLOCKED_SOURCE_FLAGS),
            {flag: source_summary.get(flag) for flag in BLOCKED_SOURCE_FLAGS},
            "all False",
        ),
        _check(
            "implementation_plan_is_plan_only",
            plan["implementation_performed_by_this_gate"] is False
            and plan["next_gate"]
            == "fresh_evaluation_split_member_source_remediation_implementation_static_contract_review_only",
            plan["next_gate"],
            "implementation static contract review only",
        ),
        _check(
            "implementation_plan_preserves_zero_intersection_contract",
            plan["required_zero_intersections"] == source_summary["required_zero_intersections"],
            plan["required_zero_intersections"],
            source_summary["required_zero_intersections"],
        ),
        _expect("implementation_plan_score_affine", plan["math_boundary"]["score_expression"], SCORE_EXPRESSION),
        _expect(
            "implementation_plan_simplex_convex",
            plan["math_boundary"]["nonnegative_simplex_weights_only"]
            and plan["math_boundary"]["master_problem_remains_convex"],
            True,
        ),
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
    marker = f"{key}="
    if marker not in text:
        return None
    return text.rsplit(marker, maxsplit=1)[1].splitlines()[0].strip()


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


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
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


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
