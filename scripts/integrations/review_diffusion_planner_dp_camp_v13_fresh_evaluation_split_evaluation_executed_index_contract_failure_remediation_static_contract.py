#!/usr/bin/env python3
"""Static contract review for executed-index remediation.

This review consumes the plan-only artifact for a rejected v13 fresh
evaluation execution and validates the future implementation contract. It does
not run DP, generate candidates, replay, train CAMP, modify DP, promote,
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
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_"
    "contract_failure_remediation_static_contract_review_v1"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_"
    "contract_failure_remediation_static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_"
    "contract_failure_remediation_static_contract_review_rejected"
)
PLAN_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_"
    "contract_failure_remediation_plan_v1"
)
PLAN_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_"
    "contract_failure_remediation_plan_ready"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_"
    "contract_failure_remediation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_"
    "contract_failure_remediation_implementation_only"
)
REQUIRED_CONTRACTS = (
    "member_source_selection_must_require_default_off_shadow_selector_payload",
    "selected_index_must_remain_dp_top1_zero",
    "executed_index_must_remain_dp_top1_zero",
    "shadow_selected_index_required_for_camp_choice",
    "legacy_selection_logs_with_nonzero_executed_index_rejected",
    "zero_overlap_four_registries_still_required",
    "split_root_zero_alone_remains_insufficient",
    "same_failed_execution_artifact_must_not_be_reused_as_holdout",
)
REQUIRED_IMPLEMENTATION = (
    "add_strict_default_off_member_source_filter_before_selection",
    "record_rejection_reasons_for_contract_failed_members",
    "require_zero_selected_contract_failed_members_in_selected_split",
    "preserve_existing_nonoverlap_registry_checks",
    "do_not_modify_candidate_tensors_or_trajectories",
    "do_not_change_dp_code_config_or_weights",
    "do_not_use_closed_loop_outcomes",
)
REQUIRED_VERIFICATION = (
    "unit_test_rejects_legacy_nonzero_executed_index_member",
    "unit_test_accepts_default_off_shadow_member_with_shadow_index_nonzero",
    "materialized_fresh_member_source_must_pass_evaluation_execution_before_result_review",
    "formal_seeds_11_12_13_and_full36_remain_excluded",
)
FALSE_FLAGS = (
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
AUDIT_FALSE_FLAGS = (
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
    parser = argparse.ArgumentParser(
        description="Static contract review for executed-index remediation."
    )
    parser.add_argument("--plan_artifact_dir", type=Path, required=True)
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
        plan_artifact_dir=args.plan_artifact_dir,
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
    plan_artifact_dir: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    artifact_dir = plan_artifact_dir.resolve()
    audit_md = v13_audit_md.resolve()
    plan_json = artifact_dir / "executed_index_contract_failure_remediation_plan.json"
    plan = _load_json_dict(plan_json)
    audit_text = _read_text(audit_md)
    review = _static_contract_review(plan)
    checks = _checks(
        artifact_dir=artifact_dir,
        plan_json=plan_json,
        audit_md=audit_md,
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
            "implementation_execution": False,
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
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "nonnegative_simplex_weights_only": True,
            "master_problem_remains_convex": True,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {
            "plan_artifact_dir": str(artifact_dir),
            "plan_json": str(plan_json),
            "v13_audit_md": str(audit_md),
        },
        "source_hashes": {
            "plan_json_sha256": _sha256(plan_json) if plan_json.is_file() else None,
            "v13_audit_md_sha256": _sha256(audit_md) if audit_md.is_file() else None,
        },
        "plan_summary": _plan_summary(plan),
        "static_contract_review": review,
        "review_checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "implementation_authorized_next": passed,
            "static_contract_review_authorized_next": False,
            **{flag: False for flag in FALSE_FLAGS},
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["static_contract_review"]
    return "\n".join(
        [
            "# V13 Executed-Index Remediation Static Contract Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Required contracts: `{len(review['required_contracts'])}`",
            f"- Implementation requirements: `{len(review['implementation_requirements'])}`",
            "",
            (
                "The next gate may implement member-source contract filtering "
                "only. It may not run evaluation, replay, candidate generation, "
                "training, promotion, deployment, or DP modification."
            ),
            "",
        ]
    )


def _static_contract_review(plan: dict[str, Any]) -> dict[str, Any]:
    remediation = _dict(plan.get("remediation_plan"))
    return {
        "required_contracts": {
            name: _dict(remediation.get("required_contracts")).get(name)
            for name in REQUIRED_CONTRACTS
        },
        "implementation_requirements": {
            name: _dict(remediation.get("implementation_requirements")).get(name)
            for name in REQUIRED_IMPLEMENTATION
        },
        "verification_requirements": {
            name: _dict(remediation.get("verification_requirements")).get(name)
            for name in REQUIRED_VERIFICATION
        },
        "math_boundary": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": _dict(plan.get("analysis")).get("score_expression"),
            "nonnegative_simplex_weights_only": _dict(plan.get("analysis")).get(
                "nonnegative_simplex_weights_only"
            ),
            "master_problem_remains_convex": _dict(plan.get("analysis")).get(
                "master_problem_remains_convex"
            ),
        },
        "future_allowed_scope": {
            "implementation_only": True,
            "member_source_contract_filtering": True,
            "evaluation_execution": False,
            "candidate_generation": False,
            "replay": False,
            "training": False,
            "dp_modification": False,
            "promotion": False,
            "deployment": False,
        },
    }


def _plan_summary(plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(plan.get("final_decision"))
    failure = _dict(plan.get("failure_summary"))
    source = _dict(plan.get("source_log_contract_summary"))
    return {
        "schema_version": plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "static_contract_review_authorized_next": decision.get(
            "static_contract_review_authorized_next"
        ),
        "failure_executed_index_violations": _int(
            failure.get("executed_index_violations")
        ),
        "source_missing_default_off_shadow_selector_records": _int(
            source.get("missing_default_off_shadow_selector_records")
        ),
        "source_nonzero_executed_index_records": _int(
            source.get("nonzero_executed_index_records")
        ),
    }


def _checks(
    *,
    artifact_dir: Path,
    plan_json: Path,
    audit_md: Path,
    audit_text: str,
    plan: dict[str, Any],
    review: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    summary = _plan_summary(plan)
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        _check("current_dp_head_fixed", current_dp_head == required_dp_head == FIXED_DP_HEAD, current_dp_head, FIXED_DP_HEAD),
        _check("plan_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
        _check("plan_json_exists", plan_json.is_file(), str(plan_json), "file"),
        _check("v13_audit_md_exists", audit_md.is_file(), str(audit_md), "file"),
        _check("plan_schema_version", summary["schema_version"] == PLAN_SCHEMA_VERSION, summary["schema_version"], PLAN_SCHEMA_VERSION),
        _check("plan_status_ready", summary["status"] == PLAN_STATUS, summary["status"], PLAN_STATUS),
        _check("plan_passed", summary["passed"] is True, summary["passed"], True),
        _check("plan_failed_checks_empty", summary["failed_checks"] == [], summary["failed_checks"], []),
        _check("plan_authorizes_current_work", summary["authorized_next_work"] == AUTHORIZED_CURRENT_WORK, summary["authorized_next_work"], AUTHORIZED_CURRENT_WORK),
        _check("plan_authorizes_static_review", summary["static_contract_review_authorized_next"] is True, summary["static_contract_review_authorized_next"], True),
        _check("plan_failure_executed_index_violations_positive", (summary["failure_executed_index_violations"] or 0) > 0, summary["failure_executed_index_violations"], ">0"),
        _check("plan_source_missing_default_off_payloads_positive", (summary["source_missing_default_off_shadow_selector_records"] or 0) > 0, summary["source_missing_default_off_shadow_selector_records"], ">0"),
        _check("audit_latest_status_is_plan_ready", _latest_value(audit_text, "current_v13_status") == LATEST_AUDIT_STATUS, _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _check("audit_latest_next_work", _latest_value(audit_text, "next_work_target") == authorized_current_work, _latest_value(audit_text, "next_work_target"), authorized_current_work),
    ]
    for name, value in review["required_contracts"].items():
        checks.append(_check(f"required_contract_{name}", value is True, value, True))
    for name, value in review["implementation_requirements"].items():
        checks.append(_check(f"implementation_requirement_{name}", value is True, value, True))
    for name, value in review["verification_requirements"].items():
        checks.append(_check(f"verification_requirement_{name}", value is True, value, True))
    math_boundary = review["math_boundary"]
    checks.extend(
        [
            _check("math_score_affine", math_boundary["score_expression"] == SCORE_EXPRESSION, math_boundary["score_expression"], SCORE_EXPRESSION),
            _check("math_nonnegative_simplex", math_boundary["nonnegative_simplex_weights_only"] is True, math_boundary["nonnegative_simplex_weights_only"], True),
            _check("math_master_convex", math_boundary["master_problem_remains_convex"] is True, math_boundary["master_problem_remains_convex"], True),
        ]
    )
    future = review["future_allowed_scope"]
    checks.append(_check("future_scope_implementation_only", future["implementation_only"] is True, future["implementation_only"], True))
    for key in ("evaluation_execution", "candidate_generation", "replay", "training", "dp_modification", "promotion", "deployment"):
        checks.append(_check(f"future_scope_blocks_{key}", future[key] is False, future[key], False))
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(
            _check(
                f"audit_blocks_{flag}",
                _latest_value(audit_text, flag) == "False",
                _latest_value(audit_text, flag),
                "False",
            )
        )
    return checks


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.*)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_git_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
