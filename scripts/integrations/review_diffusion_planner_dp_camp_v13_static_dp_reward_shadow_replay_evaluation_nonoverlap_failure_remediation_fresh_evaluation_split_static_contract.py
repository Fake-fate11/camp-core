#!/usr/bin/env python3
"""Review the v13 fresh evaluation split static contract.

This is a read-only static review gate. It consumes the fresh evaluation split
plan artifact and verifies that a later split implementation plan must preserve
the fixed-DP/CAMP reranking boundary, full non-overlap registry checks, and the
no-promotion/no-claim boundary before any execution gate is considered.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PLAN_SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_plan_v1"
)
PLAN_READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_plan_ready"
)
SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_static_contract_review_v1"
)
PASS_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_static_contract_review_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_"
    "artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_"
    "fresh_evaluation_split_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_implementation_plan_only"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


FRESHNESS_REQUIREMENTS = (
    "load_full_training_manifest_76c2",
    "load_recovered_missing_prior_registry",
    "load_rejected_eval_source_registry",
    "candidate_tensor_eval_hashes_in_previous_count_must_be_zero",
    "candidate_hash_intersection_count_must_be_zero",
    "path_signature_intersection_count_must_be_zero",
    "record_identity_intersection_count_must_be_zero",
    "split_manifest_root_intersection_count_must_be_zero",
    "raw_log_absence_must_not_disable_registry_checks",
)

FORBIDDEN_SOURCES = (
    "current_failed_shadow_replay_evaluation_output",
    "any_selection_log_in_76c2_training_manifest",
    "recovered_prior_c92_registry_records",
    "route_seed_npc_spawn_tl_static_shadow_signature_already_in_training",
)

RUNTIME_BOUNDARY_REQUIREMENTS = (
    "default_off_shadow_selector_required",
    "selection_effect_must_be_false",
    "executed_output_policy_must_remain_dp_top1",
    "candidate_generation_by_camp_forbidden",
    "camp_trajectory_generation_or_modification_forbidden",
    "reference_blend_guidance_postselection_forbidden",
    "closed_loop_outcome_as_input_forbidden",
    "nonnegative_simplex_weights_only",
)

BLOCKED_FINAL_DECISION_FLAGS = (
    "implementation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "replay_execution_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
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
        description="Review the fresh non-overlap evaluation split static contract."
    )
    parser.add_argument("--fresh_evaluation_split_plan_json", type=Path, required=True)
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
        fresh_evaluation_split_plan_json=args.fresh_evaluation_split_plan_json,
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
    fresh_evaluation_split_plan_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    plan_path = fresh_evaluation_split_plan_json.resolve()
    audit_path = v13_audit_md.resolve()
    plan = _load_json_dict(plan_path)
    audit_text = audit_path.read_text(encoding="utf-8")
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
            "fresh_evaluation_split_plan_json": str(plan_path),
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
            "fresh_evaluation_split_implementation_plan_authorized_next": passed,
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


def _static_contract_review(plan: dict[str, Any]) -> dict[str, Any]:
    split_plan = _dict(plan.get("fresh_evaluation_split_plan"))
    future_scope = _dict(split_plan.get("future_scope_contract"))
    freshness = _dict(split_plan.get("freshness_requirements"))
    forbidden = _dict(split_plan.get("forbidden_sources"))
    runtime = _dict(split_plan.get("runtime_boundary"))
    minimum = _dict(split_plan.get("minimum_acceptance_before_execution"))
    return {
        "required_contract_groups": [
            "future_scope_contract",
            "full_registry_nonoverlap_contract",
            "forbidden_source_exclusion_contract",
            "fixed_dp_default_off_runtime_boundary_contract",
            "affine_simplex_math_boundary_contract",
            "no_action_authorization_beyond_next_implementation_plan_gate",
        ],
        "future_scope_contract": {
            "selection_log_count": future_scope.get("selection_log_count"),
            "record_count": future_scope.get("record_count"),
            "candidate_count": future_scope.get("candidate_count"),
            "atom_count": future_scope.get("atom_count"),
            "routes_minimum": future_scope.get("routes_minimum"),
            "seeds_minimum": future_scope.get("seeds_minimum"),
            "route_traffic_light_buckets_minimum": future_scope.get(
                "route_traffic_light_buckets_minimum"
            ),
            "formal_seeds_11_12_13_excluded": future_scope.get(
                "formal_seeds_11_12_13_excluded"
            ),
            "full36_excluded": future_scope.get("full36_excluded"),
        },
        "freshness_requirements_present": {
            name: freshness.get(name) is True for name in FRESHNESS_REQUIREMENTS
        },
        "forbidden_sources_present": {
            name: forbidden.get(name) is True for name in FORBIDDEN_SOURCES
        },
        "runtime_boundary": {
            name: runtime.get(name) is True for name in RUNTIME_BOUNDARY_REQUIREMENTS
        }
        | {
            "fixed_dp_head_required": runtime.get("fixed_dp_head_required"),
            "score_expression": runtime.get("score_expression"),
        },
        "minimum_acceptance_before_execution": {
            "next_gate": minimum.get("next_gate"),
            "implementation_or_preflight_not_authorized_by_this_plan": minimum.get(
                "implementation_or_preflight_not_authorized_by_this_plan"
            ),
            "static_review_must_reject_missing_registry_checks": minimum.get(
                "static_review_must_reject_missing_registry_checks"
            ),
            "static_review_must_reject_any_action_authorization_leak": minimum.get(
                "static_review_must_reject_any_action_authorization_leak"
            ),
            "static_review_must_reject_formal_seed_or_full36_scope": minimum.get(
                "static_review_must_reject_formal_seed_or_full36_scope"
            ),
        },
        "math_boundary": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "nonnegative_simplex_weights_only": True,
        },
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
    analysis = _dict(plan.get("analysis"))
    split_plan = _dict(plan.get("fresh_evaluation_split_plan"))
    latest_status = _latest_value(audit_text, "current_v13_status")
    latest_target = _latest_value(audit_text, "next_work_target")
    future_scope = _dict(review.get("future_scope_contract"))
    runtime = _dict(review.get("runtime_boundary"))
    minimum = _dict(review.get("minimum_acceptance_before_execution"))
    return [
        _check("plan_json_exists", plan_path.exists(), str(plan_path)),
        _check("audit_md_exists", audit_path.exists(), str(audit_path)),
        _check("plan_schema_version_expected", plan.get("schema_version") == PLAN_SCHEMA_VERSION),
        _check("plan_status_expected", decision.get("status") == PLAN_READY_STATUS),
        _check("plan_passed", decision.get("passed") is True),
        _check("plan_failed_checks_empty", decision.get("failed_checks") == []),
        _check(
            "plan_authorizes_this_static_review",
            decision.get("authorized_next_work") == authorized_current_work,
        ),
        _check(
            "latest_audit_status_authorizes_static_review",
            latest_status == LATEST_AUDIT_STATUS,
            latest_status,
        ),
        _check(
            "latest_audit_target_authorizes_static_review",
            latest_target == authorized_current_work,
            latest_target,
        ),
        _check("camp_head_matches_origin", current_camp_head == current_camp_origin_main),
        _check("dp_head_fixed", current_dp_head == required_dp_head == FIXED_DP_HEAD),
        _check("plan_only", analysis.get("plan_only") is True),
        _check("read_only_inputs", analysis.get("read_only_inputs") is True),
        _check(
            "candidate_operation_fixed_dp_reranking_only",
            analysis.get("candidate_operation") == "fixed DP candidate reranking only",
        ),
        _check("score_expression_affine", analysis.get("score_expression") == SCORE_EXPRESSION),
        _check(
            "future_scope_counts_expected",
            future_scope.get("selection_log_count") == 32
            and future_scope.get("record_count") == 3200
            and future_scope.get("candidate_count") == 8
            and future_scope.get("atom_count") == 14,
        ),
        _check(
            "future_scope_coverage_expected",
            future_scope.get("routes_minimum", 0) >= 4
            and future_scope.get("seeds_minimum", 0) >= 2
            and future_scope.get("route_traffic_light_buckets_minimum", 0) >= 8,
        ),
        _check(
            "future_scope_excludes_formal_and_full36",
            future_scope.get("formal_seeds_11_12_13_excluded") is True
            and future_scope.get("full36_excluded") is True,
        ),
        _check(
            "all_freshness_requirements_present",
            all(review["freshness_requirements_present"].values()),
            review["freshness_requirements_present"],
        ),
        _check(
            "all_forbidden_sources_present",
            all(review["forbidden_sources_present"].values()),
            review["forbidden_sources_present"],
        ),
        _check(
            "runtime_boundary_complete",
            all(runtime[name] is True for name in RUNTIME_BOUNDARY_REQUIREMENTS)
            and runtime.get("fixed_dp_head_required") == FIXED_DP_HEAD
            and runtime.get("score_expression") == SCORE_EXPRESSION,
        ),
        _check(
            "minimum_acceptance_reviews_before_execution",
            minimum.get("next_gate") == "fresh_evaluation_split_static_contract_review_only"
            and minimum.get("implementation_or_preflight_not_authorized_by_this_plan") is True
            and minimum.get("static_review_must_reject_missing_registry_checks") is True
            and minimum.get("static_review_must_reject_any_action_authorization_leak") is True
            and minimum.get("static_review_must_reject_formal_seed_or_full36_scope") is True,
        ),
        _check(
            "fresh_split_static_review_was_authorized_next",
            decision.get("fresh_evaluation_split_static_contract_review_authorized_next") is True,
        ),
        _check(
            "blocked_final_decision_flags_false",
            all(decision.get(name) is False for name in BLOCKED_FINAL_DECISION_FLAGS),
            {name: decision.get(name) for name in BLOCKED_FINAL_DECISION_FLAGS},
        ),
        _check(
            "split_plan_object_present",
            split_plan.get("objective") is not None
            and _dict(split_plan.get("source_static_review")).get("status")
            == "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_failure_remediation_static_contract_review_passed",
        ),
    ]


def _plan_summary(plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(plan.get("final_decision"))
    split_plan = _dict(plan.get("fresh_evaluation_split_plan"))
    source = _dict(split_plan.get("source_static_review"))
    future_scope = _dict(split_plan.get("future_scope_contract"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "source_static_review_status": source.get("status"),
        "source_record_identity_intersection_count": source.get(
            "record_identity_intersection_count"
        ),
        "source_candidate_tensor_eval_hashes_in_previous_rate": source.get(
            "candidate_tensor_eval_hashes_in_previous_rate"
        ),
        "future_selection_log_count": future_scope.get("selection_log_count"),
        "future_record_count": future_scope.get("record_count"),
        "future_candidate_count": future_scope.get("candidate_count"),
        "future_atom_count": future_scope.get("atom_count"),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = _dict(report["final_decision"])
    summary = _dict(report["plan_summary"])
    checks = report["review_checks"]
    lines = [
        "# V13 Fresh Evaluation Split Static Contract Review",
        "",
        f"- schema_version: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failed_checks: `{decision['failed_checks']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- source_plan_status: `{summary['status']}`",
        f"- future_selection_log_count: `{summary['future_selection_log_count']}`",
        f"- future_record_count: `{summary['future_record_count']}`",
        f"- future_candidate_count: `{summary['future_candidate_count']}`",
        f"- future_atom_count: `{summary['future_atom_count']}`",
        f"- candidate_operation: `{report['analysis']['candidate_operation']}`",
        f"- score_expression: `{report['analysis']['score_expression']}`",
        "",
        "## Checks",
        "",
    ]
    lines.extend(
        f"- {check['name']}: {check['passed']}" + (
            f" ({check['detail']})" if check.get("detail") is not None else ""
        )
        for check in checks
    )
    lines.append("")
    return "\n".join(lines)


def _check(name: str, passed: bool, detail: Any | None = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _load_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


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
