#!/usr/bin/env python3
"""Review the v13 non-overlap failure remediation static contract.

This gate consumes the plan-only remediation artifact and verifies that its
contract is strong enough to govern a later fresh evaluation split plan. It is
read-only: it does not run replay, generate candidates, train CAMP, modify
Diffusion Planner, promote artifacts, deploy, or make safety/CAMP-over-DP
claims.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PLAN_READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_failure_remediation_plan_ready"
)
SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_failure_remediation_static_contract_review_v1"
)
PASS_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_failure_remediation_static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_failure_remediation_static_contract_review_rejected"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_plan_only"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_"
    "artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_"
    "plan_ready"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


REQUIRED_CONTRACTS = (
    "split_manifest_required",
    "training_manifest_sources_must_be_loaded",
    "recovered_missing_prior_registry_must_be_loaded",
    "candidate_tensor_hash_registry_required",
    "path_signature_registry_required",
    "record_identity_hash_registry_required",
    "candidate_tensor_eval_hashes_in_previous_must_be_zero",
    "candidate_hash_intersection_must_be_zero",
    "path_signature_intersection_must_be_zero",
    "record_identity_intersection_must_be_zero",
    "raw_log_absence_must_not_disable_registry_overlap_checks",
    "default_off_shadow_selector_contract_required",
    "affine_score_contract_required",
    "dp_head_fixed_contract_required",
)

BLOCKED_ACTIONS = (
    "training_preflight",
    "training_execution",
    "replay_execution",
    "fixed_dp_candidate_generation_execution",
    "candidate_generation_by_camp",
    "trajectory_generation_by_camp",
    "trajectory_modification_by_camp",
    "dp_modification",
    "selector_promotion",
    "atom_promotion",
    "deployment",
    "deployable_checkpoint_claim",
    "safety_benefit_claim",
    "camp_over_dp_top1_claim",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review the v13 non-overlap remediation static contract."
    )
    parser.add_argument("--nonoverlap_failure_remediation_plan_json", type=Path, required=True)
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
        nonoverlap_failure_remediation_plan_json=(
            args.nonoverlap_failure_remediation_plan_json
        ),
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
    nonoverlap_failure_remediation_plan_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    plan_path = nonoverlap_failure_remediation_plan_json.resolve()
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
            "nonoverlap_failure_remediation_plan_json": str(plan_path),
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
            "fresh_evaluation_split_plan_authorized_next": passed,
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
    required = _dict(_dict(plan.get("remediation_plan")).get("required_static_contracts"))
    blocked = _dict(_dict(plan.get("remediation_plan")).get("blocked_by_this_plan"))
    forbidden = _dict(_dict(plan.get("remediation_plan")).get("forbidden_reuse"))
    return {
        "required_contracts_present": {
            name: required.get(name) is True for name in REQUIRED_CONTRACTS
        },
        "blocked_actions_present": {
            name: blocked.get(name) is True for name in BLOCKED_ACTIONS
        },
        "forbidden_reuse_contracts_present": {
            "reuse_current_failed_evaluation_output_dir": (
                forbidden.get("reuse_current_failed_evaluation_output_dir") is True
            ),
            "reuse_any_training_manifest_selection_log_as_eval": (
                forbidden.get("reuse_any_training_manifest_selection_log_as_eval") is True
            ),
            "reuse_recovered_prior_c92_registry_records_as_eval": (
                forbidden.get("reuse_recovered_prior_c92_registry_records_as_eval") is True
            ),
            "reuse_eval_route_seed_npc_spawn_tl_static_shadow_signature_in_training": (
                forbidden.get(
                    "reuse_eval_route_seed_npc_spawn_tl_static_shadow_signature_in_training"
                )
                is True
            ),
        },
        "math_boundary": {
            "fixed_dp_candidate_reranking_only": True,
            "score_expression": SCORE_EXPRESSION,
            "nonnegative_simplex_weights_required": True,
            "closed_loop_outcomes_forbidden_as_input": True,
        },
        "next_gate": {
            "kind": "fresh_evaluation_split_plan_only",
            "must_remain_plan_only": True,
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
    summary = _dict(plan.get("attribution_summary"))
    analysis = _dict(plan.get("analysis"))
    latest_status = _latest_value(audit_text, "current_v13_status")
    latest_target = _latest_value(audit_text, "next_work_target")
    required_values = review["required_contracts_present"]
    blocked_values = review["blocked_actions_present"]
    forbidden_values = review["forbidden_reuse_contracts_present"]
    return [
        _check("plan_json_exists", plan_path.is_file(), str(plan_path), "file exists"),
        _check("v13_audit_md_exists", audit_path.is_file(), str(audit_path), "file exists"),
        _check("latest_audit_status_is_plan_ready", latest_status == LATEST_AUDIT_STATUS, latest_status, LATEST_AUDIT_STATUS),
        _check("latest_audit_target_authorizes_static_review", latest_target == authorized_current_work, latest_target, authorized_current_work),
        _check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        _check("dp_head_fixed", current_dp_head == required_dp_head == FIXED_DP_HEAD, current_dp_head, FIXED_DP_HEAD),
        _check("plan_passed", decision.get("passed") is True, decision.get("passed"), True),
        _check("plan_status_ready", decision.get("status") == PLAN_READY_STATUS, decision.get("status"), PLAN_READY_STATUS),
        _check("plan_authorizes_this_static_review", decision.get("authorized_next_work") == authorized_current_work, decision.get("authorized_next_work"), authorized_current_work),
        _check("plan_blocks_training_preflight", decision.get("training_preflight_authorized_next") is False, decision.get("training_preflight_authorized_next"), False),
        _check("plan_blocks_replay_execution", decision.get("replay_execution_authorized_next") is False, decision.get("replay_execution_authorized_next"), False),
        _check("plan_blocks_fixed_dp_candidate_generation", decision.get("fixed_dp_candidate_generation_authorized_next") is False, decision.get("fixed_dp_candidate_generation_authorized_next"), False),
        _check("plan_blocks_dp_modification", decision.get("dp_modification_authorized") is False, decision.get("dp_modification_authorized"), False),
        _check("analysis_read_only", analysis.get("read_only_inputs") is True, analysis.get("read_only_inputs"), True),
        _check("analysis_score_affine", analysis.get("score_expression") == SCORE_EXPRESSION, analysis.get("score_expression"), SCORE_EXPRESSION),
        _check("all_required_contracts_present", all(required_values.values()), required_values, "all True"),
        _check("all_blocked_actions_present", all(blocked_values.values()), blocked_values, "all True"),
        _check("forbidden_reuse_contracts_present", all(forbidden_values.values()), forbidden_values, "all True"),
        _check("source_failure_class_expected", summary.get("failure_class") == "evaluation_set_overlaps_training_manifest_recovered_prior_source", summary.get("failure_class"), "evaluation_set_overlaps_training_manifest_recovered_prior_source"),
        _check("source_record_identity_overlap_full", summary.get("record_identity_intersection_count") == 3200, summary.get("record_identity_intersection_count"), 3200),
        _check("source_candidate_overlap_rate_one", summary.get("candidate_tensor_eval_hashes_in_previous_rate") == 1.0, summary.get("candidate_tensor_eval_hashes_in_previous_rate"), 1.0),
    ]


def _plan_summary(plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(plan.get("final_decision"))
    summary = _dict(plan.get("attribution_summary"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "failure_class": summary.get("failure_class"),
        "record_identity_intersection_count": summary.get(
            "record_identity_intersection_count"
        ),
        "candidate_tensor_eval_hashes_in_previous_rate": summary.get(
            "candidate_tensor_eval_hashes_in_previous_rate"
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# V13 Non-Overlap Failure Remediation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Boundary",
        "",
        "This review is read-only and authorizes only a later fresh evaluation "
        "split plan. It does not run replay, generate candidates, train CAMP, "
        "modify DP, promote artifacts, deploy, or make safety/CAMP-over-DP "
        "claims.",
        "",
        "## Required Contract Groups",
        "",
        "- full training manifest plus recovered missing-prior registry checks",
        "- zero candidate tensor, path signature, and record identity overlap",
        "- default-off fixed-DP candidate reranking with affine score",
        "- no action authorization beyond the next plan-only gate",
        "",
    ]
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
