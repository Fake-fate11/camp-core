#!/usr/bin/env python3
"""Plan a fresh v13 evaluation split after non-overlap failure remediation.

This gate is plan-only. It consumes the static contract review artifact and
defines the constraints for a later fresh fixed-DP evaluation split. It does not
run replay, generate fixed-DP candidates, train CAMP, modify Diffusion Planner,
promote artifacts, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
STATIC_REVIEW_PASS_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_static_contract_review_passed"
)
SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_plan_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_"
    "artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_"
    "static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_static_contract_review_only"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan a fresh non-overlapping v13 evaluation split."
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
    static_contract_review_json = static_contract_review_json.resolve()
    v13_audit_md = v13_audit_md.resolve()
    static_review = _load_json_dict(static_contract_review_json)
    audit_text = v13_audit_md.read_text(encoding="utf-8")
    split_plan = _fresh_split_plan(static_review)
    checks = _checks(
        static_contract_review_json=static_contract_review_json,
        v13_audit_md=v13_audit_md,
        audit_text=audit_text,
        static_review=static_review,
        split_plan=split_plan,
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
            "read_only_inputs": True,
            "training_preflight": False,
            "training_execution": False,
            "replay_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "dp_modification": False,
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
            "static_contract_review_json": str(static_contract_review_json),
            "v13_audit_md": str(v13_audit_md),
        },
        "static_contract_review_summary": _static_review_summary(static_review),
        "fresh_evaluation_split_plan": split_plan,
        "plan_checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "fresh_evaluation_split_static_contract_review_authorized_next": passed,
            "implementation_authorized_next": False,
            "training_preflight_authorized_next": False,
            "training_execution_authorized_next": False,
            "replay_execution_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }


def _fresh_split_plan(static_review: dict[str, Any]) -> dict[str, Any]:
    review_summary = _static_review_summary(static_review)
    return {
        "objective": (
            "define a future evaluation split that is fresh against the full "
            "76c2 training manifest, the recovered missing-prior registry, and "
            "the rejected overlapping evaluation source"
        ),
        "future_scope_contract": {
            "selection_log_count": 32,
            "record_count": 3200,
            "candidate_count": 8,
            "atom_count": 14,
            "routes_minimum": 4,
            "seeds_minimum": 2,
            "route_traffic_light_buckets_minimum": 8,
            "formal_seeds_11_12_13_excluded": True,
            "full36_excluded": True,
        },
        "freshness_requirements": {
            "load_full_training_manifest_76c2": True,
            "load_recovered_missing_prior_registry": True,
            "load_rejected_eval_source_registry": True,
            "candidate_tensor_eval_hashes_in_previous_count_must_be_zero": True,
            "candidate_hash_intersection_count_must_be_zero": True,
            "path_signature_intersection_count_must_be_zero": True,
            "record_identity_intersection_count_must_be_zero": True,
            "split_manifest_root_intersection_count_must_be_zero": True,
            "raw_log_absence_must_not_disable_registry_checks": True,
        },
        "forbidden_sources": {
            "current_failed_shadow_replay_evaluation_output": True,
            "any_selection_log_in_76c2_training_manifest": True,
            "recovered_prior_c92_registry_records": True,
            "route_seed_npc_spawn_tl_static_shadow_signature_already_in_training": True,
        },
        "runtime_boundary": {
            "fixed_dp_head_required": FIXED_DP_HEAD,
            "default_off_shadow_selector_required": True,
            "selection_effect_must_be_false": True,
            "executed_output_policy_must_remain_dp_top1": True,
            "candidate_generation_by_camp_forbidden": True,
            "camp_trajectory_generation_or_modification_forbidden": True,
            "reference_blend_guidance_postselection_forbidden": True,
            "closed_loop_outcome_as_input_forbidden": True,
            "score_expression": SCORE_EXPRESSION,
            "nonnegative_simplex_weights_only": True,
        },
        "minimum_acceptance_before_execution": {
            "next_gate": "fresh_evaluation_split_static_contract_review_only",
            "implementation_or_preflight_not_authorized_by_this_plan": True,
            "static_review_must_reject_missing_registry_checks": True,
            "static_review_must_reject_any_action_authorization_leak": True,
            "static_review_must_reject_formal_seed_or_full36_scope": True,
        },
        "source_static_review": review_summary,
    }


def _checks(
    *,
    static_contract_review_json: Path,
    v13_audit_md: Path,
    audit_text: str,
    static_review: dict[str, Any],
    split_plan: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(static_review.get("final_decision"))
    analysis = _dict(static_review.get("analysis"))
    plan_summary = _dict(static_review.get("plan_summary"))
    latest_status = _latest_value(audit_text, "current_v13_status")
    latest_target = _latest_value(audit_text, "next_work_target")
    return [
        _check("static_contract_review_json_exists", static_contract_review_json.is_file(), str(static_contract_review_json), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _check("latest_audit_status_is_static_review_passed", latest_status == LATEST_AUDIT_STATUS, latest_status, LATEST_AUDIT_STATUS),
        _check("latest_audit_target_authorizes_this_plan", latest_target == authorized_current_work, latest_target, authorized_current_work),
        _check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        _check("dp_head_fixed", current_dp_head == required_dp_head == FIXED_DP_HEAD, current_dp_head, FIXED_DP_HEAD),
        _check("static_review_passed", decision.get("passed") is True, decision.get("passed"), True),
        _check("static_review_status_expected", decision.get("status") == STATIC_REVIEW_PASS_STATUS, decision.get("status"), STATIC_REVIEW_PASS_STATUS),
        _check("static_review_authorizes_this_plan", decision.get("authorized_next_work") == authorized_current_work, decision.get("authorized_next_work"), authorized_current_work),
        _check("static_review_blocks_training_preflight", decision.get("training_preflight_authorized_next") is False, decision.get("training_preflight_authorized_next"), False),
        _check("static_review_blocks_replay", decision.get("replay_execution_authorized_next") is False, decision.get("replay_execution_authorized_next"), False),
        _check("static_review_blocks_fixed_dp_candidate_generation", decision.get("fixed_dp_candidate_generation_authorized_next") is False, decision.get("fixed_dp_candidate_generation_authorized_next"), False),
        _check("static_review_blocks_dp_modification", decision.get("dp_modification_authorized") is False, decision.get("dp_modification_authorized"), False),
        _check("analysis_read_only", analysis.get("read_only_inputs") is True, analysis.get("read_only_inputs"), True),
        _check("analysis_score_affine", analysis.get("score_expression") == SCORE_EXPRESSION, analysis.get("score_expression"), SCORE_EXPRESSION),
        _check("source_overlap_was_full_record_identity", plan_summary.get("record_identity_intersection_count") == 3200, plan_summary.get("record_identity_intersection_count"), 3200),
        _check("source_candidate_overlap_rate_one", plan_summary.get("candidate_tensor_eval_hashes_in_previous_rate") == 1.0, plan_summary.get("candidate_tensor_eval_hashes_in_previous_rate"), 1.0),
        _check("split_plan_requires_zero_candidate_overlap", split_plan["freshness_requirements"]["candidate_tensor_eval_hashes_in_previous_count_must_be_zero"], True, True),
        _check("split_plan_requires_zero_path_overlap", split_plan["freshness_requirements"]["path_signature_intersection_count_must_be_zero"], True, True),
        _check("split_plan_requires_zero_record_identity_overlap", split_plan["freshness_requirements"]["record_identity_intersection_count_must_be_zero"], True, True),
        _check("split_plan_excludes_formal_seeds", split_plan["future_scope_contract"]["formal_seeds_11_12_13_excluded"], True, True),
        _check("split_plan_excludes_full36", split_plan["future_scope_contract"]["full36_excluded"], True, True),
        _check("split_plan_blocks_implementation", split_plan["minimum_acceptance_before_execution"]["implementation_or_preflight_not_authorized_by_this_plan"], True, True),
    ]


def _static_review_summary(static_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(static_review.get("final_decision"))
    plan_summary = _dict(static_review.get("plan_summary"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "failure_class": plan_summary.get("failure_class"),
        "record_identity_intersection_count": plan_summary.get(
            "record_identity_intersection_count"
        ),
        "candidate_tensor_eval_hashes_in_previous_rate": plan_summary.get(
            "candidate_tensor_eval_hashes_in_previous_rate"
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["fresh_evaluation_split_plan"]
    lines = [
        "# V13 Fresh Evaluation Split Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Objective",
        "",
        plan["objective"],
        "",
        "## Freshness Requirements",
        "",
    ]
    for key, value in plan["freshness_requirements"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Boundary", ""])
    lines.append(
        "This plan is read-only and authorizes only a static contract review. "
        "It does not authorize replay, fixed-DP candidate generation, CAMP "
        "training, DP modification, promotion, deployment, or claims."
    )
    lines.append("")
    return "\n".join(lines)


def _load_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _latest_value(text: str, key: str) -> str | None:
    values = re.findall(rf"^{re.escape(key)}=(.+)$", text, re.M)
    return values[-1] if values else None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
