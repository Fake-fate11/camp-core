#!/usr/bin/env python3
"""Static review for the fresh split member-source implementation plan.

This read-only gate consumes the member-source remediation implementation plan
and verifies that the next step is limited to implementing a fail-closed fresh
member-source builder. It does not implement the builder, select fresh members,
run evaluation or replay, generate fixed-DP candidates, train CAMP, modify DP,
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
SOURCE_PLAN_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_"
    "implementation_plan_v1"
)
SOURCE_PLAN_READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_"
    "implementation_plan_ready"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_"
    "implementation_static_contract_review_v1"
)
PASS_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_"
    "implementation_static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_remediation_"
    "implementation_static_contract_review_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_"
    "artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_"
    "evaluation_split_member_source_remediation_implementation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "implementation_only"
)
EXPECTED_FUTURE_BUILDER_SCRIPT = (
    "scripts/integrations/build_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source.py"
)
EXPECTED_FUTURE_BUILDER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source_builder.py"
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
REQUIRED_STATIC_REVIEW_REQUIREMENTS = (
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
)
BLOCKED_SOURCE_FLAGS = (
    "implementation_authorized_next",
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only static review for member-source implementation plan."
    )
    parser.add_argument("--implementation_plan_json", type=Path, required=True)
    parser.add_argument("--implementation_plan_script_py", type=Path, required=True)
    parser.add_argument("--implementation_plan_test_py", type=Path, required=True)
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
        implementation_plan_json=args.implementation_plan_json,
        implementation_plan_script_py=args.implementation_plan_script_py,
        implementation_plan_test_py=args.implementation_plan_test_py,
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
    implementation_plan_json: Path,
    implementation_plan_script_py: Path,
    implementation_plan_test_py: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    plan_path = implementation_plan_json.resolve()
    script_path = implementation_plan_script_py.resolve()
    test_path = implementation_plan_test_py.resolve()
    audit_path = v13_audit_md.resolve()
    source_plan = _load_json_dict(plan_path)
    script_text = _read_text(script_path)
    test_text = _read_text(test_path)
    audit_text = _read_text(audit_path)
    source_summary = _source_summary(source_plan)
    review = _static_review(source_summary)
    checks = _checks(
        plan_path=plan_path,
        script_path=script_path,
        test_path=test_path,
        audit_path=audit_path,
        audit_text=audit_text,
        source_plan=source_plan,
        source_summary=source_summary,
        review=review,
        script_text=script_text,
        test_text=test_text,
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
            "read_only": True,
            "static_contract_review_only": True,
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
            "implementation_plan_json": str(plan_path),
            "implementation_plan_script_py": str(script_path),
            "implementation_plan_test_py": str(test_path),
            "v13_audit_md": str(audit_path),
        },
        "source_hashes": {
            "implementation_plan_json_sha256": _sha256(plan_path),
            "implementation_plan_script_py_sha256": _sha256(script_path),
            "implementation_plan_test_py_sha256": _sha256(test_path),
            "v13_audit_md_sha256": _sha256(audit_path),
        },
        "source_summary": source_summary,
        "static_contract_review": review,
        "review_checks": checks,
        "final_decision": {
            "status": PASS_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "member_source_remediation_implementation_authorized_next": passed,
            "implementation_authorized_next": passed,
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
    review = report["static_contract_review"]
    lines = [
        "# V13 Fresh Evaluation Split Member-Source Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation authorized next: `{decision['implementation_authorized_next']}`",
        f"- Fresh member selection authorized next: `{decision['fresh_member_selection_execution_authorized_next']}`",
        f"- Fixed-DP candidate generation authorized next: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
        f"- Future builder script: `{review['future_builder_script']}`",
        f"- Future builder test: `{review['future_builder_test']}`",
        "",
        "## Required Behavior",
        "",
    ]
    for item in review["required_future_builder_behavior"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This static review authorizes only the next implementation gate. It "
            "does not authorize evaluation, replay, fixed-DP candidate generation, "
            "CAMP training, DP modification, promotion, deployment, or claims.",
            "",
        ]
    )
    return "\n".join(lines)


def _source_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_plan.get("final_decision"))
    plan = _dict(source_plan.get("implementation_plan"))
    source_failure = _dict(plan.get("source_failure_to_remediate"))
    math_boundary = _dict(plan.get("math_boundary"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "member_source_remediation_implementation_static_contract_review_authorized_next": decision.get(
            "member_source_remediation_implementation_static_contract_review_authorized_next"
        ),
        "implementation_performed_by_this_gate": plan.get(
            "implementation_performed_by_this_gate"
        ),
        "future_builder_script": plan.get("future_builder_script"),
        "future_builder_test": plan.get("future_builder_test"),
        "future_artifacts": plan.get("future_artifacts"),
        "required_future_builder_behavior": plan.get("required_future_builder_behavior"),
        "required_zero_intersections": plan.get("required_zero_intersections"),
        "required_registry_inputs": plan.get("required_registry_inputs"),
        "source_failure_to_remediate": source_failure,
        "future_static_contract_review_requirements": source_plan.get(
            "future_static_contract_review_requirements"
        ),
        "forbidden_paths": source_plan.get("forbidden_paths"),
        "next_gate": plan.get("next_gate"),
        "math_boundary": math_boundary,
        **{flag: decision.get(flag) for flag in BLOCKED_SOURCE_FLAGS},
    }


def _static_review(source_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "future_builder_script": source_summary["future_builder_script"],
        "future_builder_test": source_summary["future_builder_test"],
        "required_future_builder_behavior": source_summary[
            "required_future_builder_behavior"
        ],
        "required_zero_intersections": source_summary["required_zero_intersections"],
        "required_registry_inputs": source_summary["required_registry_inputs"],
        "source_failure_to_remediate": source_summary["source_failure_to_remediate"],
        "future_static_contract_review_requirements": source_summary[
            "future_static_contract_review_requirements"
        ],
        "forbidden_paths": source_summary["forbidden_paths"],
        "math_boundary": source_summary["math_boundary"],
    }


def _checks(
    *,
    plan_path: Path,
    script_path: Path,
    test_path: Path,
    audit_path: Path,
    audit_text: str,
    source_plan: dict[str, Any],
    source_summary: dict[str, Any],
    review: dict[str, Any],
    script_text: str,
    test_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    return [
        _check("implementation_plan_json_exists", plan_path.is_file(), str(plan_path), "file exists"),
        _check("implementation_plan_script_exists", script_path.is_file(), str(script_path), "file exists"),
        _check("implementation_plan_test_exists", test_path.is_file(), str(test_path), "file exists"),
        _check("v13_audit_md_exists", audit_path.is_file(), str(audit_path), "file exists"),
        _expect("source_schema_version", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_status_ready", source_summary["status"], SOURCE_PLAN_READY_STATUS),
        _expect("source_passed", source_summary["passed"], True),
        _expect("source_failed_checks_empty", source_summary["failed_checks"], []),
        _expect("source_authorizes_this_review", source_summary["authorized_next_work"], authorized_current_work),
        _expect(
            "source_authorizes_implementation_static_review",
            source_summary[
                "member_source_remediation_implementation_static_contract_review_authorized_next"
            ],
            True,
        ),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect(
            "source_plan_did_not_implement",
            source_summary["implementation_performed_by_this_gate"],
            False,
        ),
        _expect("future_builder_script_expected", review["future_builder_script"], EXPECTED_FUTURE_BUILDER_SCRIPT),
        _expect("future_builder_test_expected", review["future_builder_test"], EXPECTED_FUTURE_BUILDER_TEST),
        _check(
            "all_required_behavior_present",
            set(REQUIRED_BEHAVIOR)
            <= set(_list(review["required_future_builder_behavior"])),
            review["required_future_builder_behavior"],
            "required behavior",
        ),
        _check(
            "all_static_review_requirements_present",
            set(REQUIRED_STATIC_REVIEW_REQUIREMENTS)
            <= set(_list(review["future_static_contract_review_requirements"])),
            review["future_static_contract_review_requirements"],
            "required static requirements",
        ),
        _check(
            "zero_intersection_contract_preserved",
            all(_dict(review["required_zero_intersections"]).get(key) == 0 for key in ZERO_INTERSECTION_KEYS),
            review["required_zero_intersections"],
            "all zero",
        ),
        _check(
            "source_failure_overlap_evidence_preserved",
            _int(_dict(review["source_failure_to_remediate"]).get("candidate_tensor_hash_intersection_count")) > 0
            and _int(_dict(review["source_failure_to_remediate"]).get("path_signature_intersection_count")) > 0
            and _int(_dict(review["source_failure_to_remediate"]).get("record_identity_intersection_count")) > 0
            and _dict(review["source_failure_to_remediate"]).get("split_manifest_root_intersection_count") == 0
            and _dict(review["source_failure_to_remediate"]).get("root_zero_is_not_sufficient") is True,
            review["source_failure_to_remediate"],
            "candidate/path/record overlap and root zero insufficient",
        ),
        _expect("math_score_affine", _dict(review["math_boundary"]).get("score_expression"), SCORE_EXPRESSION),
        _expect(
            "math_simplex_and_convex",
            _dict(review["math_boundary"]).get("nonnegative_simplex_weights_only")
            and _dict(review["math_boundary"]).get("master_problem_remains_convex"),
            True,
        ),
        _check(
            "forbidden_paths_complete",
            {
                "implementation_code_edit_by_this_gate",
                "fresh_member_selection_by_this_gate",
                "fixed_dp_candidate_generation_execution_by_this_gate",
                "camp_candidate_generation_or_trajectory_modification",
                "diffusion_planner_code_config_or_weight_change",
                "safety_benefit_or_camp_over_dp_top1_claim",
            }
            <= set(_list(review["forbidden_paths"])),
            review["forbidden_paths"],
            "forbidden paths",
        ),
        _check(
            "source_blocked_action_flags_false",
            all(source_summary.get(flag) is False for flag in BLOCKED_SOURCE_FLAGS),
            {flag: source_summary.get(flag) for flag in BLOCKED_SOURCE_FLAGS},
            "all False",
        ),
        _check(
            "plan_script_contains_contract_terms",
            all(
                token in script_text
                for token in (
                    "required_zero_intersections",
                    "fail_closed_when_any_required_registry_is_missing_empty_or_unreadable",
                    "reject_split_root_only_acceptance",
                    "implementation_static_contract_review_only",
                )
            ),
            "script terms",
            "required terms",
        ),
        _check(
            "plan_test_contains_rejection_tests",
            all(
                token in test_text
                for token in (
                    "rejects_wrong_audit_target",
                    "rejects_source_action_leak",
                    "rejects_missing_zero_contract",
                    "rejects_root_only_or_holdout_reuse",
                    "rejects_dp_head_drift",
                )
            ),
            "test terms",
            "required tests",
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
