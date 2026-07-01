#!/usr/bin/env python3
"""Plan-only gate for fresh member-source rematerialization.

The executed-index remediation changed the member-source builder so legacy
selection logs can no longer enter a fresh evaluation split. This gate plans
the next minimal implementation step needed to rematerialize a member source
under that stricter contract. It does not run the builder, materialize data,
evaluate logs, replay, generate candidates, train CAMP, modify DP, promote,
deploy, or make safety/CAMP-over-DP claims.
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
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fresh_member_source_rematerialization_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fresh_member_source_rematerialization_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fresh_member_source_rematerialization_plan_rejected"
)
POST_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_post_implementation_static_contract_review_v1"
)
POST_REVIEW_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_post_implementation_static_contract_review_passed"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_"
    "post_implementation_static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fresh_member_source_rematerialization_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fresh_member_source_rematerialization_implementation_only"
)
AUDIT_FALSE_FLAGS = (
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
REQUIRED_PLAN_STEPS = (
    "parameterize_or_wrap_member_source_builder_for_new_audit_current_work",
    "preserve_previous_static_review_as_source_contract_evidence",
    "run_strict_default_off_member_source_selection_against_existing_candidates",
    "require_selected_index_and_executed_index_zero_for_every_source_record",
    "require_shadow_selected_index_for_camp_choice",
    "require_candidate_path_record_split_root_zero_intersections",
    "fail_closed_if_no_valid_default_off_member_sources_remain",
    "do_not_reuse_rejected_legacy_evaluation_member_source_as_holdout",
    "do_not_run_fresh_evaluation_until_rematerialized_member_source_passes_preflight",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan-only fresh member-source rematerialization for executed-index remediation."
    )
    parser.add_argument("--post_review_artifact_dir", type=Path, required=True)
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
        post_review_artifact_dir=args.post_review_artifact_dir,
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
    post_review_artifact_dir: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    artifact_dir = post_review_artifact_dir.resolve()
    post_review_json = artifact_dir / "post_implementation_static_contract_review.json"
    post_review = _load_json_dict(post_review_json)
    audit_text = _read_text(v13_audit_md)
    plan = _plan(post_review, authorized_next_work=authorized_next_work)
    checks = _checks(
        artifact_dir=artifact_dir,
        post_review_json=post_review_json,
        post_review=post_review,
        audit_text=audit_text,
        v13_audit_md=v13_audit_md,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
        plan=plan,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
            "fresh_member_source_materialization_execution": False,
            "fresh_evaluation_split_evaluation_execution": False,
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
            "promotion": False,
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
        "inputs": {
            "post_review_artifact_dir": str(artifact_dir),
            "post_review_json": str(post_review_json),
            "v13_audit_md": str(v13_audit_md.resolve()),
        },
        "source_hashes": {
            "post_review_json_sha256": _sha256(post_review_json),
            "v13_audit_md_sha256": _sha256(v13_audit_md),
        },
        "post_review_summary": _post_review_summary(post_review),
        "rematerialization_plan": plan,
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    return "\n".join(
        [
            "# V13 Fresh Member-Source Rematerialization Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Implementation authorized next: `{decision['rematerialization_implementation_authorized_next']}`",
            f"- Training authorized next: `{decision['training_execution_authorized_next']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            "",
            "The next gate must implement a small rematerialization path that "
            "uses the strict default-off member-source builder contract without "
            "reusing the rejected legacy evaluation member source as a holdout. "
            "This plan does not execute materialization, evaluation, replay, "
            "candidate generation, or training.",
            "",
        ]
    )


def _plan(post_review: dict[str, Any], *, authorized_next_work: str) -> dict[str, Any]:
    return {
        "required_steps": list(REQUIRED_PLAN_STEPS),
        "requires_post_review_passed": True,
        "requires_default_off_schema": post_review.get("static_contract_review", {}).get(
            "default_off_shadow_selector_schema_required"
        ),
        "requires_selected_index_zero": True,
        "requires_executed_index_zero": True,
        "requires_shadow_selected_index": True,
        "requires_four_zero_intersection_registries": True,
        "rejected_legacy_evaluation_member_source_reusable_as_holdout": False,
        "if_no_valid_default_off_sources_remain": (
            "fail closed and open a later fixed-DP candidate generation plan; "
            "do not relax the executed-index contract"
        ),
        "authorized_next_gate": authorized_next_work,
    }


def _checks(
    *,
    artifact_dir: Path,
    post_review_json: Path,
    post_review: dict[str, Any],
    audit_text: str,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    decision = _dict(post_review.get("final_decision"))
    review = _dict(post_review.get("static_contract_review"))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("post_review_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory exists"),
        _check("post_review_json_exists", post_review_json.is_file(), str(post_review_json), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _expect("post_review_schema", post_review.get("schema_version"), POST_REVIEW_SCHEMA_VERSION),
        _expect("post_review_status", decision.get("status"), POST_REVIEW_STATUS),
        _expect("post_review_passed", decision.get("passed"), True),
        _expect("post_review_authorized_this_gate", decision.get("authorized_next_work"), authorized_current_work),
        _expect("post_review_blocks_evaluation_execution", decision.get("fresh_evaluation_split_evaluation_execution_authorized_next"), False),
        _expect("post_review_blocks_training", decision.get("training_execution_authorized_next"), False),
        _expect("post_review_blocks_dp_modification", decision.get("dp_modification_authorized"), False),
        _expect("post_review_requires_source_path_file", review.get("source_path_file_required"), True),
        _expect("post_review_requires_selected_zero", review.get("selected_index_must_remain_dp_top1_zero"), True),
        _expect("post_review_requires_executed_zero", review.get("executed_index_must_remain_dp_top1_zero"), True),
        _expect("post_review_rejects_legacy_logs", review.get("legacy_non_default_off_selection_logs_rejected"), True),
        _expect("post_review_score_affine", review.get("score_expression"), SCORE_EXPRESSION),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_authorizes_plan", _latest_value(audit_text, "fresh_member_source_rematerialization_plan_authorized_next"), "True"),
        _expect("plan_has_all_required_steps", sorted(plan["required_steps"]), sorted(REQUIRED_PLAN_STEPS)),
        _expect("plan_rejects_reusing_legacy_holdout", plan["rejected_legacy_evaluation_member_source_reusable_as_holdout"], False),
    ]
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _latest_value(audit_text, flag), "False"))
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
        "rematerialization_plan_ready": passed,
        "rematerialization_implementation_authorized_next": passed,
        "fresh_member_source_materialization_execution_authorized_next": False,
        "fresh_evaluation_split_evaluation_execution_authorized_next": False,
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
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "fresh_member_source_materialization_executed": False,
        "fresh_evaluation_split_evaluation_executed": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def _post_review_summary(post_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(post_review.get("final_decision"))
    review = _dict(post_review.get("static_contract_review"))
    return {
        "schema_version": post_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "source_path_file_required": review.get("source_path_file_required"),
        "executed_index_must_remain_dp_top1_zero": review.get(
            "executed_index_must_remain_dp_top1_zero"
        ),
        "legacy_non_default_off_selection_logs_rejected": review.get(
            "legacy_non_default_off_selection_logs_rejected"
        ),
    }


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


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


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


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value.lower())


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
