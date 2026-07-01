#!/usr/bin/env python3
"""Static contract review for v13 fresh member-source materialization plan.

This read-only gate consumes the materialization plan artifact and verifies
that the next gate remains an implementation plan only. It does not materialize
inputs, run the member-source builder, select fresh members, run DP, generate
fixed-DP candidates, replay, prepare data, train CAMP, modify DP, promote,
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
SOURCE_PLAN_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_plan_v1"
)
SOURCE_PLAN_READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_plan_ready"
)
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "static_contract_review_v1"
)
PASS_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "static_contract_review_passed"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "static_contract_review_rejected"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "materialization_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_remediation_"
    "materialization_implementation_plan_only"
)
EXPECTED_FUTURE_MATERIALIZER_SCRIPT = (
    "scripts/integrations/materialize_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source_inputs.py"
)
EXPECTED_FUTURE_MATERIALIZER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_member_source_materializer.py"
)
REQUIRED_SOURCE_INPUTS = (
    "candidate_member_source_manifest_json",
    "training_candidate_tensor_hash_registry_json",
    "training_path_signature_registry_json",
    "training_record_identity_registry_json",
    "training_split_manifest_root_registry_json",
    "recovered_prior_registry_manifest_json",
    "rejected_overlap_source_registry_manifest_json",
)
FUTURE_OUTPUTS = (
    "fresh_evaluation_split_member_source_manifest.json",
    "fresh_evaluation_split_member_source_nonoverlap_report.json",
    "fresh_evaluation_split_member_source_preflight_inputs.json",
    "SHA256SUMS.txt",
)
ZERO_INTERSECTION_KEYS = (
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
SOURCE_BLOCKED_FLAGS = (
    "materialization_execution_authorized_next",
    "member_source_builder_execution_authorized_next",
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
    "dp_modification_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
AUDIT_BLOCKED_FLAGS = (
    "materialization_execution_authorized_next",
    "member_source_builder_execution_authorized_next",
    "fresh_member_selection_execution_authorized_next",
    "fresh_evaluation_split_evaluation_authorized_next",
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
REQUIRED_SCRIPT_TERMS = (
    "missing_inputs_to_materialize",
    "future_outputs",
    "required_zero_intersections",
    "split_root_zero_alone_is_insufficient",
    "materialization_static_contract_review_only",
    SCORE_EXPRESSION,
)
REQUIRED_TEST_TERMS = (
    "rejects_wrong_audit_target",
    "rejects_source_action_leak",
    "rejects_source_failure_drift",
    "rejects_missing_contract_terms",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review the v13 fresh member-source materialization contract."
    )
    parser.add_argument("--materialization_plan_json", type=Path, required=True)
    parser.add_argument("--materialization_plan_script_py", type=Path, required=True)
    parser.add_argument("--materialization_plan_test_py", type=Path, required=True)
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
        materialization_plan_json=args.materialization_plan_json,
        materialization_plan_script_py=args.materialization_plan_script_py,
        materialization_plan_test_py=args.materialization_plan_test_py,
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
    materialization_plan_json: Path,
    materialization_plan_script_py: Path,
    materialization_plan_test_py: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    plan_path = materialization_plan_json.resolve()
    script_path = materialization_plan_script_py.resolve()
    test_path = materialization_plan_test_py.resolve()
    audit_path = v13_audit_md.resolve()
    source_plan = _load_json_dict(plan_path)
    script_text = _read_text(script_path)
    test_text = _read_text(test_path)
    audit_text = _read_text(audit_path)
    review = _static_contract_review(source_plan)
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
            "materialization_execution": False,
            "member_source_builder_execution": False,
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
            "materialization_plan_json": str(plan_path),
            "materialization_plan_script_py": str(script_path),
            "materialization_plan_test_py": str(test_path),
            "v13_audit_md": str(audit_path),
        },
        "source_hashes": {
            "materialization_plan_json_sha256": _sha256(plan_path),
            "materialization_plan_script_py_sha256": _sha256(script_path),
            "materialization_plan_test_py_sha256": _sha256(test_path),
            "v13_audit_md_sha256": _sha256(audit_path),
        },
        "source_summary": _source_summary(source_plan),
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
        "# V13 Fresh Member-Source Materialization Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation plan authorized: `{decision['materialization_implementation_plan_authorized_next']}`",
        f"- Materialization execution authorized: `{decision['materialization_execution_authorized_next']}`",
        f"- Fixed-DP candidate generation authorized: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
        f"- Training authorized: `{decision['training_execution_authorized_next']}`",
        "",
        "## Contract Groups",
        "",
    ]
    for group in review["required_contract_groups"]:
        lines.append(f"- `{group}`")
    lines.extend(
        [
            "",
            "This static review authorizes only a future implementation plan. It "
            "does not materialize inputs, run DP, generate fixed-DP candidates, "
            "replay, train CAMP, modify DP, promote, deploy, or claim safety/"
            "CAMP-over-DP benefit.",
            "",
        ]
    )
    return "\n".join(lines)


def _static_contract_review(source_plan: dict[str, Any]) -> dict[str, Any]:
    plan = _dict(source_plan.get("materialization_plan"))
    member_contract = _dict(plan.get("candidate_member_manifest_contract"))
    registry_contract = _dict(plan.get("registry_materialization_contract"))
    math_boundary = _dict(plan.get("math_boundary"))
    return {
        "required_contract_groups": [
            "rejected_validation_preflight_missing_inputs_contract",
            "future_materializer_input_and_output_contract",
            "four_way_zero_intersection_contract",
            "candidate_member_identity_and_exclusion_contract",
            "registry_fail_closed_and_split_root_rejection_contract",
            "fixed_dp_affine_simplex_boundary_contract",
            "no_action_authorization_beyond_implementation_plan_gate",
        ],
        "future_materializer_script": plan.get("future_materializer_script"),
        "future_materializer_test": plan.get("future_materializer_test"),
        "missing_inputs_to_materialize": plan.get("missing_inputs_to_materialize"),
        "future_outputs": plan.get("future_outputs"),
        "required_zero_intersections": plan.get("required_zero_intersections"),
        "candidate_member_manifest_contract": member_contract,
        "registry_materialization_contract": registry_contract,
        "future_materializer_contract": plan.get("future_materializer_contract"),
        "math_boundary": math_boundary,
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
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(source_plan.get("final_decision"))
    analysis = _dict(source_plan.get("analysis"))
    plan = _dict(source_plan.get("materialization_plan"))
    member_contract = _dict(review["candidate_member_manifest_contract"])
    registry_contract = _dict(review["registry_materialization_contract"])
    math_boundary = _dict(review["math_boundary"])
    return [
        _check("materialization_plan_json_exists", plan_path.is_file(), str(plan_path), "file exists"),
        _check("materialization_plan_script_exists", script_path.is_file(), str(script_path), "file exists"),
        _check("materialization_plan_test_exists", test_path.is_file(), str(test_path), "file exists"),
        _check("v13_audit_md_exists", audit_path.is_file(), str(audit_path), "file exists"),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_materialization_plan_ready", _latest_value(audit_text, "fresh_evaluation_split_member_source_materialization_plan_ready"), "True"),
        _expect("audit_static_review_authorized", _latest_value(audit_text, "materialization_static_contract_review_authorized_next"), "True"),
        *[
            _expect(f"audit_blocks_{flag}", _latest_value(audit_text, flag), "False")
            for flag in AUDIT_BLOCKED_FLAGS
        ],
        _expect("source_schema_version", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_status_ready", decision.get("status"), SOURCE_PLAN_READY_STATUS),
        _expect("source_passed", decision.get("passed"), True),
        _expect("source_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_authorizes_this_review", decision.get("authorized_next_work"), authorized_current_work),
        _expect("source_static_review_authorized", decision.get("materialization_static_contract_review_authorized_next"), True),
        *[
            _expect(f"source_blocks_{flag}", decision.get(flag), False)
            for flag in SOURCE_BLOCKED_FLAGS
        ],
        _expect("source_plan_ready_flag", plan.get("plan_ready_no_inputs_materialized"), True),
        _expect("source_plan_did_not_materialize", plan.get("materialization_performed_by_this_gate"), False),
        _expect("source_plan_from_rejected_validation", plan.get("source_rejected_validation_preflight"), True),
        _expect("future_materializer_script_expected", review["future_materializer_script"], EXPECTED_FUTURE_MATERIALIZER_SCRIPT),
        _expect("future_materializer_test_expected", review["future_materializer_test"], EXPECTED_FUTURE_MATERIALIZER_TEST),
        _check("all_required_source_inputs_listed", set(REQUIRED_SOURCE_INPUTS) <= set(_list(review["missing_inputs_to_materialize"])), review["missing_inputs_to_materialize"], "required source inputs"),
        _check("all_future_outputs_listed", set(FUTURE_OUTPUTS) <= set(_list(review["future_outputs"])), review["future_outputs"], "future outputs"),
        _check("all_zero_intersections_required", all(_dict(review["required_zero_intersections"]).get(key) == 0 for key in ZERO_INTERSECTION_KEYS), review["required_zero_intersections"], "all zero"),
        _expect("member_identity_candidate_hashes_required", member_contract.get("each_member_has_candidate_tensor_hashes"), True),
        _expect("member_identity_path_signatures_required", member_contract.get("each_member_has_path_signatures"), True),
        _expect("member_identity_record_hashes_required", member_contract.get("each_member_has_record_identity_hashes"), True),
        _expect("formal_seeds_excluded", member_contract.get("formal_seeds_11_12_13_excluded"), True),
        _expect("full36_excluded", member_contract.get("full36_excluded"), True),
        _expect("rejected_source_not_relabelled", member_contract.get("source_members_are_not_relabelled_from_rejected_overlap_artifact"), True),
        _expect("training_registries_loaded_before_selection", registry_contract.get("training_registries_loaded_before_selection"), True),
        _expect("recovered_prior_registry_loaded", registry_contract.get("recovered_prior_registry_loaded_before_selection"), True),
        _expect("rejected_overlap_registry_loaded", registry_contract.get("rejected_overlap_source_registry_loaded_before_selection"), True),
        _expect("missing_registry_fails_closed", registry_contract.get("missing_empty_or_unreadable_registry_fails_closed"), True),
        _expect("split_root_zero_alone_insufficient", registry_contract.get("split_root_zero_alone_is_insufficient"), True),
        _check("future_materializer_contract_blocks_actions", all(token in " ".join(_list(review["future_materializer_contract"])) for token in ("do not run DP", "fail closed", "zero candidate/path/record/split-root intersections")), review["future_materializer_contract"], "blocked action contract"),
        _expect("analysis_score_affine", analysis.get("score_expression"), SCORE_EXPRESSION),
        _expect("math_score_affine", math_boundary.get("score_expression"), SCORE_EXPRESSION),
        _expect("math_nonnegative_simplex", math_boundary.get("nonnegative_simplex_weights_only"), True),
        _expect("math_master_convex", math_boundary.get("master_problem_remains_convex"), True),
        _expect("math_executed_dp_top1", math_boundary.get("executed_trajectory_remains_dp_top1"), True),
        _check("script_contains_contract_terms", all(term in script_text for term in REQUIRED_SCRIPT_TERMS), "script terms", "required terms"),
        _check("test_contains_rejection_tests", all(term in test_text for term in REQUIRED_TEST_TERMS), "test terms", "required tests"),
        _expect("review_contract_groups_count", len(review["required_contract_groups"]), 7),
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
        "materialization_static_contract_review_passed": passed,
        "materialization_implementation_plan_authorized_next": passed,
        "materialization_execution_authorized_next": False,
        "member_source_builder_execution_authorized_next": False,
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
        "materialization_executed": False,
        "member_source_builder_executed": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }


def _source_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_plan.get("final_decision"))
    plan = _dict(source_plan.get("materialization_plan"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "future_materializer_script": plan.get("future_materializer_script"),
        "future_materializer_test": plan.get("future_materializer_test"),
        "missing_inputs_to_materialize": plan.get("missing_inputs_to_materialize"),
        "future_outputs": plan.get("future_outputs"),
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


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _is_git_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


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
