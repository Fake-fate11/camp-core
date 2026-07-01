#!/usr/bin/env python3
"""Static review for v13 materialization failure remediation implementation plan.

This read-only gate consumes the failure-remediation implementation plan and
checks whether a future missing-input materializer may be implemented. It does
not implement code, materialize inputs, run DP, generate candidates, replay,
train CAMP, modify DP, promote, deploy, or make safety/CAMP-over-DP claims.
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
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_plan_v1"
)
SOURCE_PLAN_READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_plan_ready"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_static_contract_review_v1"
)
PASS_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_static_contract_review_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_failure_remediation_implementation_"
    "plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_only"
)
EXPECTED_FUTURE_INPUT_MATERIALIZER_SCRIPT = (
    "scripts/integrations/materialize_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source_missing_inputs.py"
)
EXPECTED_FUTURE_INPUT_MATERIALIZER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source_missing_input_materializer.py"
)
FUTURE_OUTPUTS = (
    "candidate_member_source_manifest.json",
    "training_split_manifest_roots.json",
    "candidate_member_source_manifest_provenance_report.json",
    "SHA256SUMS",
)
REQUIRED_MEMBER_FIELDS = (
    "member_id",
    "source_path",
    "route",
    "seed",
    "candidate_tensor_hashes",
    "path_signatures",
    "record_identity_hashes",
    "split_manifest_roots",
)
REQUIRED_IMPLEMENTATION_CONTRACTS = (
    "read_only_existing_fixed_dp_current_source_artifacts",
    "derive_candidate_members_only_from_explicit_candidate_tensor_and_identity_evidence",
    "write_nonempty_candidate_member_source_manifest_or_reject",
    "write_nonempty_training_split_manifest_root_registry_or_reject",
    "require_member_id_source_path_route_seed_and_four_identity_sets",
    "exclude_full36_and_formal_seeds_11_12_13",
    "exclude_rejected_overlap_source_as_holdout_or_training_data",
    "reject_split_root_zero_alone_acceptance",
    "require_future_zero_overlap_preflight_before_training",
    "preserve_affine_score_and_nonnegative_simplex_boundary",
)
ZERO_INTERSECTION_KEYS = (
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
SOURCE_BLOCKED_FLAGS = (
    "implementation_execution_authorized_next",
    "input_materialization_execution_authorized_next",
    "materialization_execution_authorized_next",
    "member_source_builder_execution_authorized_next",
    "validation_preflight_authorized_next",
    "data_preparation_authorized_next",
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
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
AUDIT_FALSE_FLAGS = (
    "implementation_execution_authorized_next",
    "input_materialization_execution_authorized_next",
    "materialization_execution_authorized_next",
    "member_source_builder_execution_authorized_next",
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
REQUIRED_PLAN_SCRIPT_TERMS = (
    "REQUIRED_IMPLEMENTATION_CONTRACTS",
    "FUTURE_INPUT_MATERIALIZER_SCRIPT",
    "must_reject_if_no_existing_member_source_evidence",
    "must_not_synthesize_identity_hashes",
    "split_root_zero_alone_is_insufficient",
    "failure_remediation_implementation_plan_only",
    "materialization_failure_remediation_implementation_static_contract_review_only",
    SCORE_EXPRESSION,
)
REQUIRED_PLAN_TEST_TERMS = (
    "test_materialization_failure_remediation_implementation_plan_ready",
    "test_materialization_failure_remediation_implementation_plan_rejects_wrong_audit_target",
    "test_materialization_failure_remediation_implementation_plan_rejects_source_action_leak",
    "test_materialization_failure_remediation_implementation_plan_rejects_sha_mismatch",
    "test_materialization_failure_remediation_implementation_plan_rejects_missing_failure_evidence",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only static review for the v13 missing-input materializer "
            "implementation plan."
        )
    )
    parser.add_argument("--implementation_plan_json", type=Path, required=True)
    parser.add_argument("--expected_implementation_plan_sha256", required=True)
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
        expected_implementation_plan_sha256=args.expected_implementation_plan_sha256,
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
    args.output_json.write_text(
        json.dumps(_stable(report), indent=2) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    implementation_plan_json: Path,
    expected_implementation_plan_sha256: str,
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
    review = _static_review(source_plan)
    checks = _checks(
        plan_path=plan_path,
        script_path=script_path,
        test_path=test_path,
        audit_path=audit_path,
        audit_text=audit_text,
        source_plan=source_plan,
        review=review,
        script_text=script_text,
        test_text=test_text,
        expected_implementation_plan_sha256=expected_implementation_plan_sha256,
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
            "read_only_static_review": True,
            "implementation_execution": False,
            "input_materialization_execution": False,
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
        "source_plan_summary": _source_plan_summary(source_plan),
        "static_contract_review": review,
        "review_checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["static_contract_review"]
    lines = [
        "# V13 Materialization Failure Remediation Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation execution authorized: `{decision['implementation_execution_authorized_next']}`",
        f"- Input materialization execution authorized: `{decision['input_materialization_execution_authorized_next']}`",
        f"- Fixed-DP candidate generation authorized: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
        "",
        "## Required Contracts",
        "",
    ]
    for item in review["required_implementation_contracts"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This static-review gate authorizes only a later implementation-only "
            "code gate. It does not implement code, materialize inputs, run DP, "
            "generate candidates, replay, train CAMP, modify DP, promote, deploy, "
            "or make safety/CAMP-over-DP claims.",
            "",
        ]
    )
    return "\n".join(lines)


def _static_review(source_plan: dict[str, Any]) -> dict[str, Any]:
    plan = _dict(source_plan.get("implementation_plan"))
    return {
        "future_input_materializer_script": plan.get(
            "future_input_materializer_script",
            EXPECTED_FUTURE_INPUT_MATERIALIZER_SCRIPT,
        ),
        "future_input_materializer_test": plan.get(
            "future_input_materializer_test",
            EXPECTED_FUTURE_INPUT_MATERIALIZER_TEST,
        ),
        "future_outputs": _list(plan.get("future_outputs")),
        "required_member_fields": _list(plan.get("required_member_fields")),
        "required_implementation_contracts": _list(
            plan.get("required_implementation_contracts")
        ),
        "required_zero_intersections_after_materialization": _dict(
            plan.get("required_zero_intersections_after_materialization")
        ),
        "candidate_member_source_strategy": _dict(
            plan.get("candidate_member_source_strategy")
        ),
        "training_split_root_registry_strategy": _dict(
            plan.get("training_split_root_registry_strategy")
        ),
        "math_boundary": _dict(plan.get("math_boundary")),
    }


def _checks(
    *,
    plan_path: Path,
    script_path: Path,
    test_path: Path,
    audit_path: Path,
    audit_text: str,
    source_plan: dict[str, Any],
    review: dict[str, Any],
    script_text: str,
    test_text: str,
    expected_implementation_plan_sha256: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(source_plan.get("final_decision"))
    checks = [
        _check("implementation_plan_json_exists", plan_path.is_file(), str(plan_path), "file exists"),
        _check("implementation_plan_script_exists", script_path.is_file(), str(script_path), "file exists"),
        _check("implementation_plan_test_exists", test_path.is_file(), str(test_path), "file exists"),
        _check("v13_audit_md_exists", audit_path.is_file(), str(audit_path), "file exists"),
        _expect("implementation_plan_sha256", _sha256(plan_path), expected_implementation_plan_sha256),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_implementation_plan_ready", _latest_value(audit_text, "fresh_evaluation_split_member_source_materialization_failure_remediation_implementation_plan_ready"), "True"),
        _expect("audit_static_review_authorized", _latest_value(audit_text, "materialization_failure_remediation_implementation_static_contract_review_authorized_next"), "True"),
        _expect("source_schema_version", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_status_ready", decision.get("status"), SOURCE_PLAN_READY_STATUS),
        _expect("source_passed", decision.get("passed"), True),
        _expect("source_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_authorizes_this_review", decision.get("authorized_next_work"), authorized_current_work),
        _expect("source_static_review_authorized", decision.get("materialization_failure_remediation_implementation_static_contract_review_authorized_next"), True),
    ]
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(_expect(f"audit_blocks_{flag}", _latest_value(audit_text, flag), "False"))
    for flag in SOURCE_BLOCKED_FLAGS:
        checks.append(_expect(f"source_blocks_{flag}", decision.get(flag), False))
    checks.extend(_review_contract_checks(review))
    checks.append(
        _check(
            "plan_script_terms_present",
            all(term in script_text for term in REQUIRED_PLAN_SCRIPT_TERMS),
            "script terms",
            "required terms",
        )
    )
    checks.append(
        _check(
            "plan_test_terms_present",
            all(term in test_text for term in REQUIRED_PLAN_TEST_TERMS),
            "test terms",
            "required tests",
        )
    )
    return checks


def _review_contract_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect("review_future_script_expected", review["future_input_materializer_script"], EXPECTED_FUTURE_INPUT_MATERIALIZER_SCRIPT),
        _expect("review_future_test_expected", review["future_input_materializer_test"], EXPECTED_FUTURE_INPUT_MATERIALIZER_TEST),
        _check("review_lists_future_outputs", set(FUTURE_OUTPUTS) <= set(review["future_outputs"]), review["future_outputs"], "future outputs"),
        _check("review_lists_member_fields", set(REQUIRED_MEMBER_FIELDS) <= set(review["required_member_fields"]), review["required_member_fields"], "member fields"),
        _check("review_lists_contracts", set(REQUIRED_IMPLEMENTATION_CONTRACTS) <= set(review["required_implementation_contracts"]), review["required_implementation_contracts"], "contracts"),
        _check("review_requires_zero_intersections", all(review["required_zero_intersections_after_materialization"].get(key) == 0 for key in ZERO_INTERSECTION_KEYS), review["required_zero_intersections_after_materialization"], "all zero"),
        _expect("review_rejects_missing_member_evidence", review["candidate_member_source_strategy"].get("must_reject_if_no_existing_member_source_evidence"), True),
        _expect("review_does_not_synthesize_hashes", review["candidate_member_source_strategy"].get("must_not_synthesize_identity_hashes"), True),
        _expect("review_rejects_rejected_overlap_holdout", review["candidate_member_source_strategy"].get("must_not_use_rejected_overlap_artifact_as_holdout"), True),
        _expect("review_writes_nonempty_split_roots", review["training_split_root_registry_strategy"].get("must_write_nonempty_training_split_root_registry"), True),
        _expect("review_rejects_split_root_zero_only", review["training_split_root_registry_strategy"].get("split_root_zero_alone_is_insufficient"), True),
        _expect("review_score_affine", review["math_boundary"].get("score_expression"), SCORE_EXPRESSION),
        _expect("review_nonnegative_simplex", review["math_boundary"].get("nonnegative_simplex_weights_only"), True),
        _expect("review_master_convex", review["math_boundary"].get("master_problem_remains_convex"), True),
        _expect("review_executed_dp_top1", review["math_boundary"].get("executed_trajectory_remains_dp_top1"), True),
    ]


def _decision(
    *,
    passed: bool,
    failed: list[str],
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": PASS_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "materialization_failure_remediation_implementation_static_contract_review_passed": passed,
        "materialization_failure_remediation_implementation_authorized_next": passed,
        "implementation_execution_authorized_next": False,
        "input_materialization_execution_authorized_next": False,
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
        "implementation_executed": False,
        "input_materialization_executed": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }


def _source_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_plan.get("final_decision"))
    plan = _dict(source_plan.get("implementation_plan"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "future_input_materializer_script": plan.get("future_input_materializer_script"),
        "future_input_materializer_test": plan.get("future_input_materializer_test"),
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
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


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
