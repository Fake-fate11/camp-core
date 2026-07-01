#!/usr/bin/env python3
"""Review the v13 fresh split member-source remediation static contract.

This read-only gate consumes the member-source remediation plan and verifies
that the next gate remains an implementation plan only. It does not select
fresh members, evaluate, replay, generate fixed-DP candidates, train CAMP,
modify DP, promote, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
PLAN_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_plan_v1"
)
PLAN_READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_plan_ready"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_static_"
    "contract_review_v1"
)
PASS_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_static_"
    "contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_static_"
    "contract_review_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_"
    "artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_"
    "evaluation_split_member_source_remediation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_static_"
    "contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "implementation_plan_only"
)
ZERO_INTERSECTION_KEYS = (
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
BLOCKED_FINAL_DECISION_FLAGS = (
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
        description="Review the v13 fresh split member-source remediation contract."
    )
    parser.add_argument("--member_source_remediation_plan_json", type=Path, required=True)
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
        member_source_remediation_plan_json=args.member_source_remediation_plan_json,
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
    member_source_remediation_plan_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    plan_path = member_source_remediation_plan_json.resolve()
    audit_path = v13_audit_md.resolve()
    plan = _load_json_dict(plan_path)
    audit_text = _read_text(audit_path)
    review = _static_contract_review(plan)
    checks = _checks(
        plan_path=plan_path,
        audit_path=audit_path,
        audit_text=audit_text,
        plan=plan,
        review=review,
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
            "static_contract_review_only": True,
            "read_only_inputs": True,
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
            "member_source_remediation_plan_json": str(plan_path),
            "v13_audit_md": str(audit_path),
        },
        "plan_summary": _plan_summary(plan),
        "static_contract_review": review,
        "review_checks": checks,
        "final_decision": {
            "status": PASS_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "member_source_remediation_implementation_plan_authorized_next": passed,
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


def _static_contract_review(plan: dict[str, Any]) -> dict[str, Any]:
    remediation = _dict(plan.get("member_source_remediation_plan"))
    required = _dict(remediation.get("required_fresh_member_source_contract"))
    attribution = _dict(remediation.get("failure_attribution"))
    constraints = _dict(remediation.get("rejected_source_constraints"))
    next_requirements = _dict(remediation.get("next_gate_requirements"))
    boundary = _dict(remediation.get("boundary"))
    return {
        "required_contract_groups": [
            "rejected_preflight_failure_attribution_contract",
            "four_way_zero_intersection_member_source_contract",
            "rejected_source_exclusion_contract",
            "split_root_only_rejection_contract",
            "fixed_dp_affine_simplex_boundary_contract",
            "no_action_authorization_beyond_implementation_plan_gate",
        ],
        "failure_attribution_contract": {
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
            "failed_checks_empty_is_not_pass": attribution.get(
                "failed_checks_empty_is_not_pass"
            ),
        },
        "required_fresh_member_source_contract": {
            key: required.get(key) for key in ZERO_INTERSECTION_KEYS
        },
        "required_registry_inputs": {
            "candidate_tensor_hash_registry_required": required.get(
                "candidate_tensor_hash_registry_required"
            ),
            "path_signature_registry_required": required.get(
                "path_signature_registry_required"
            ),
            "record_identity_hash_registry_required": required.get(
                "record_identity_hash_registry_required"
            ),
            "split_manifest_root_registry_required": required.get(
                "split_manifest_root_registry_required"
            ),
            "training_registry_must_be_loaded": required.get(
                "training_registry_must_be_loaded"
            ),
            "recovered_prior_registry_must_be_loaded": required.get(
                "recovered_prior_registry_must_be_loaded"
            ),
            "rejected_source_registry_must_be_loaded": required.get(
                "rejected_source_registry_must_be_loaded"
            ),
        },
        "rejected_source_constraints": {
            "rejected_overlap_artifact_is_not_evaluation_holdout": constraints.get(
                "rejected_overlap_artifact_is_not_evaluation_holdout"
            ),
            "do_not_relabel_overlapping_members_as_fresh": constraints.get(
                "do_not_relabel_overlapping_members_as_fresh"
            ),
            "candidate_path_record_overlap_requires_member_source_replacement": constraints.get(
                "candidate_path_record_overlap_requires_member_source_replacement"
            ),
        },
        "next_gate_requirements": {
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
        },
        "boundary": boundary,
    }


def _checks(
    *,
    plan_path: Path,
    audit_path: Path,
    audit_text: str,
    plan: dict[str, Any],
    review: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(plan.get("final_decision"))
    remediation = _dict(plan.get("member_source_remediation_plan"))
    boundary = _dict(remediation.get("boundary"))
    attribution = _dict(remediation.get("failure_attribution"))
    next_requirements = _dict(remediation.get("next_gate_requirements"))
    source_constraints = _dict(remediation.get("rejected_source_constraints"))
    required = _dict(remediation.get("required_fresh_member_source_contract"))
    return [
        _check("plan_json_exists", plan_path.is_file(), str(plan_path), "file exists"),
        _check("v13_audit_md_exists", audit_path.is_file(), str(audit_path), "file exists"),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("plan_schema_version", plan.get("schema_version"), PLAN_SCHEMA_VERSION),
        _expect("plan_status_ready", decision.get("status"), PLAN_READY_STATUS),
        _expect("plan_passed", decision.get("passed"), True),
        _expect("plan_authorizes_this_review", decision.get("authorized_next_work"), authorized_current_work),
        _expect("plan_score_affine", _dict(plan.get("analysis")).get("score_expression"), SCORE_EXPRESSION),
        _check("source_candidate_overlap_nonzero", _int(attribution.get("candidate_tensor_hash_intersection_count")) > 0, attribution.get("candidate_tensor_hash_intersection_count"), ">0"),
        _check("source_path_overlap_nonzero", _int(attribution.get("path_signature_intersection_count")) > 0, attribution.get("path_signature_intersection_count"), ">0"),
        _check("source_record_overlap_nonzero", _int(attribution.get("record_identity_intersection_count")) > 0, attribution.get("record_identity_intersection_count"), ">0"),
        _expect("source_root_overlap_zero", attribution.get("split_manifest_root_intersection_count"), 0),
        _expect("root_zero_marked_insufficient", attribution.get("root_zero_is_not_sufficient"), True),
        _expect("failed_checks_empty_not_pass", attribution.get("failed_checks_empty_is_not_pass"), True),
        _expect("rejected_overlap_not_holdout", source_constraints.get("rejected_overlap_artifact_is_not_evaluation_holdout"), True),
        _expect("do_not_relabel_overlapping_members", source_constraints.get("do_not_relabel_overlapping_members_as_fresh"), True),
        _expect("candidate_path_record_overlap_requires_replacement", source_constraints.get("candidate_path_record_overlap_requires_member_source_replacement"), True),
        _expect("review_rejects_missing_registry_inputs", next_requirements.get("review_must_reject_missing_registry_inputs"), True),
        _expect("review_rejects_split_root_only_acceptance", next_requirements.get("review_must_reject_split_root_only_acceptance"), True),
        _expect("review_rejects_rejected_source_reuse", next_requirements.get("review_must_reject_reusing_rejected_overlap_source"), True),
        _expect("review_rejects_action_leak", next_requirements.get("review_must_reject_any_action_authorization_leak"), True),
        _expect("review_preserves_fixed_dp_head", next_requirements.get("review_must_preserve_fixed_dp_head"), FIXED_DP_HEAD),
        _expect("review_preserves_score_affine", next_requirements.get("review_must_preserve_score_affine"), SCORE_EXPRESSION),
        _check("all_zero_intersection_contracts_present", all(required.get(key) == 0 for key in ZERO_INTERSECTION_KEYS), {key: required.get(key) for key in ZERO_INTERSECTION_KEYS}, "all zero"),
        _check("all_registry_inputs_required", all(required.get(key) is True for key in (
            "candidate_tensor_hash_registry_required",
            "path_signature_registry_required",
            "record_identity_hash_registry_required",
            "split_manifest_root_registry_required",
            "training_registry_must_be_loaded",
            "recovered_prior_registry_must_be_loaded",
            "rejected_source_registry_must_be_loaded",
        )), required, "all required"),
        _expect("boundary_plan_only", boundary.get("plan_only"), True),
        _expect("boundary_blocks_member_selection_execution", boundary.get("fresh_member_selection_execution_authorized"), False),
        _expect("boundary_blocks_evaluation", boundary.get("evaluation_execution_authorized"), False),
        _expect("boundary_blocks_fixed_dp_candidate_generation", boundary.get("fixed_dp_candidate_generation_authorized"), False),
        _expect("boundary_blocks_replay", boundary.get("replay_authorized"), False),
        _expect("boundary_blocks_training", boundary.get("training_authorized"), False),
        _expect("boundary_blocks_dp_modification", boundary.get("dp_modification_authorized"), False),
        _check("blocked_final_decision_flags_false", all(decision.get(flag) is False for flag in BLOCKED_FINAL_DECISION_FLAGS), {flag: decision.get(flag) for flag in BLOCKED_FINAL_DECISION_FLAGS}, "all False"),
        _expect("review_contract_groups_count", len(review["required_contract_groups"]), 6),
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["static_contract_review"]
    lines = [
        "# V13 Fresh Evaluation Split Member-Source Remediation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Contract Groups",
        "",
    ]
    for group in review["required_contract_groups"]:
        lines.append(f"- `{group}`")
    lines.extend(
        [
            "",
            "The review requires four-way zero intersection and explicitly rejects "
            "root-only acceptance or reuse of the rejected overlap source.",
            "",
            "No evaluation, replay, fixed-DP candidate generation, CAMP training, "
            "DP modification, promotion, deployment, or safety/CAMP-over-DP claim "
            "is authorized by this gate.",
            "",
        ]
    )
    return "\n".join(lines)


def _plan_summary(plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(plan.get("final_decision"))
    remediation = _dict(plan.get("member_source_remediation_plan"))
    attribution = _dict(remediation.get("failure_attribution"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
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
    }


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


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
