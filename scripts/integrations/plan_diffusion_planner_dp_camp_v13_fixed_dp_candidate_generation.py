#!/usr/bin/env python3
"""Plan fixed-DP candidate generation for the v13 CAMP/DP integration.

This plan-only gate turns the completed default-off member-source builder into a
concrete next step for collecting a larger fixed-DP candidate-member source. It
does not run Diffusion Planner, generate candidates, prepare data, replay, train
CAMP, modify DP, promote, deploy, or make safety/CAMP-over-DP claims.
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
SCHEMA_VERSION = "dp_camp_v13_fixed_dp_candidate_generation_plan_v1"
READY_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_plan_ready"
REJECT_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_plan_rejected"
POST_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_default_off_member_source_generation_"
    "post_implementation_static_contract_review_v1"
)
POST_REVIEW_STATUS = (
    "dp_camp_v13_default_off_member_source_generation_"
    "post_implementation_static_contract_review_complete"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_default_off_"
    "member_source_generation_post_implementation_static_contract_review_complete"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_static_contract_review_only"
)
TARGET_MIN_CANDIDATE_MEMBERS = 1024
TARGET_CANDIDATES_PER_MEMBER = 8
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
)
FALSE_SOURCE_FLAGS = (
    "fixed_dp_candidate_generation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "replay_execution_authorized_next",
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "dp_modification_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
AUDIT_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "fresh_member_source_materialization_execution_authorized_next",
    "fresh_evaluation_split_evaluation_execution_authorized_next",
    "fresh_evaluation_split_evaluation_result_review_authorized_next",
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--post_review_json", type=Path, required=True)
    parser.add_argument("--post_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--target_min_candidate_members", type=int, default=TARGET_MIN_CANDIDATE_MEMBERS)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        post_review_json=args.post_review_json,
        post_review_artifact_dir=args.post_review_artifact_dir,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        target_min_candidate_members=args.target_min_candidate_members,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    post_review_json: Path,
    post_review_artifact_dir: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    target_min_candidate_members: int = TARGET_MIN_CANDIDATE_MEMBERS,
) -> dict[str, Any]:
    post_review = _load_json_dict(post_review_json)
    audit_text = _read_text(v13_audit_md)
    post_decision = _dict(post_review.get("final_decision"))
    post_summary = _dict(post_review.get("artifact_summary"))
    checks = _checks(
        post_review_json=post_review_json,
        post_review_artifact_dir=post_review_artifact_dir,
        v13_audit_md=v13_audit_md,
        post_review=post_review,
        post_decision=post_decision,
        post_summary=post_summary,
        audit_text=audit_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
        target_min_candidate_members=target_min_candidate_members,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome": False,
            "data_preparation_execution": False,
            "replay_execution": False,
            "training_execution": False,
            "dp_modification": False,
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
        "source_post_review": {
            "path": str(post_review_json.resolve()),
            "artifact_dir": str(post_review_artifact_dir.resolve()),
            "schema_version": post_review.get("schema_version"),
            "status": post_decision.get("status"),
            "passed": post_decision.get("passed"),
            "selected_member_count": post_summary.get("selected_member_count"),
            "zero_intersection_counts": post_summary.get("zero_intersection_counts"),
            "json_sha256": _sha256(post_review_json),
        },
        "fixed_dp_candidate_generation_plan": _generation_plan(
            target_min_candidate_members=target_min_candidate_members,
        ),
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def _generation_plan(*, target_min_candidate_members: int) -> dict[str, Any]:
    return {
        "target_min_candidate_members": target_min_candidate_members,
        "target_candidate_members_range": "hundreds_to_thousands",
        "target_candidates_per_member": TARGET_CANDIDATES_PER_MEMBER,
        "candidate_source": "fixed Diffusion Planner candidate tensor only",
        "allowed_execution_engine": "Diffusion-Planner at fixed commit",
        "required_dp_head": FIXED_DP_HEAD,
        "forbidden_sources": [
            "CAMP trajectory generation",
            "CAMP trajectory repair",
            "CAMP trajectory rewrite",
            "reference_blend",
            "guidance",
            "postprocess",
            "postselection",
            "closed-loop outcomes",
            "Full36",
            "formal seeds 11/12/13",
        ],
        "per_record_requirements": [
            "candidate_tensor_hash",
            "path_signature",
            "record_identity",
            "split_manifest_root",
            "default_off_shadow_selector log with selected_index=0",
            "executed_index=0",
            "shadow_selected_index recorded without execution effect",
            "score_k(w)=a_k^T w",
        ],
        "zero_overlap_required_against_training_registries": list(ZERO_OVERLAP_KEYS),
        "next_gate": AUTHORIZED_NEXT_WORK,
        "execution_authorized_by_this_gate": False,
    }


def _checks(
    *,
    post_review_json: Path,
    post_review_artifact_dir: Path,
    v13_audit_md: Path,
    post_review: dict[str, Any],
    post_decision: dict[str, Any],
    post_summary: dict[str, Any],
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
    target_min_candidate_members: int,
) -> list[dict[str, Any]]:
    zero_counts = _dict(post_summary.get("zero_intersection_counts"))
    checks = [
        _check("post_review_json_exists", post_review_json.is_file(), str(post_review_json), "file exists"),
        _check("post_review_artifact_dir_exists", post_review_artifact_dir.is_dir(), str(post_review_artifact_dir), "directory exists"),
        _check("v13_audit_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("post_review_schema", post_review.get("schema_version"), POST_REVIEW_SCHEMA_VERSION),
        _expect("post_review_status", post_decision.get("status"), POST_REVIEW_STATUS),
        _expect("post_review_passed", post_decision.get("passed"), True),
        _expect("post_review_failed_checks_empty", post_decision.get("failed_checks"), []),
        _expect("post_review_authorized_next", post_decision.get("authorized_next_work"), authorized_current_work),
        _expect("post_review_plan_authorized", post_decision.get("fixed_dp_candidate_generation_plan_authorized_next"), True),
        _expect("post_review_generation_execution_not_authorized", post_decision.get("fixed_dp_candidate_generation_execution_authorized_next"), False),
        _expect("post_review_candidate_operation", post_decision.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("post_review_score_expression", post_decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_plan_authorized", _latest_value(audit_text, "fixed_dp_candidate_generation_plan_authorized_next"), "True"),
        _check("target_members_hundreds_to_thousands", target_min_candidate_members >= 100, target_min_candidate_members, ">= 100"),
    ]
    checks.extend(
        _expect(f"post_review_forbids_{flag}", post_decision.get(flag), False)
        for flag in FALSE_SOURCE_FLAGS
    )
    checks.extend(
        _expect(f"audit_forbids_{flag}", _latest_value(audit_text, flag), "False")
        for flag in AUDIT_FALSE_FLAGS
    )
    checks.extend(
        _expect(f"source_zero_{key}", zero_counts.get(f"{key}_intersection_count"), 0)
        for key in ("candidate_tensor_hash", "path_signature", "record_identity", "split_manifest_root")
    )
    return checks


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
        "fixed_dp_candidate_generation_plan_ready": passed,
        "fixed_dp_candidate_generation_static_contract_review_authorized_next": passed,
        "fixed_dp_candidate_generation_execution_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "data_preparation_authorized_next": False,
        "replay_execution_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["fixed_dp_candidate_generation_plan"]
    lines = [
        "# Fixed-DP Candidate Generation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Target minimum candidate members: `{plan['target_min_candidate_members']}`",
        f"- Candidate source: `{plan['candidate_source']}`",
        f"- Execution authorized by this gate: `{plan['execution_authorized_by_this_gate']}`",
        f"- Fixed-DP generation execution authorized next: `{decision['fixed_dp_candidate_generation_execution_authorized_next']}`",
        f"- CAMP candidate generation authorized: `{decision['candidate_generation_by_camp_authorized']}`",
        f"- Training authorized next: `{decision['training_execution_authorized_next']}`",
        f"- DP modification authorized: `{decision['dp_modification_authorized']}`",
        f"- Score expression: `{decision['score_expression']}`",
        "",
        "The next gate is static contract review only; it must still prove the fixed-DP generation contract before any candidate generation execution.",
        "",
    ]
    return "\n".join(lines)


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


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
    if isinstance(value, set):
        return sorted(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
