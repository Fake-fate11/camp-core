#!/usr/bin/env python3
"""Static contract review for v13 holdout data preparation implementation plan.

This is a read-only review gate. It consumes the implementation-plan-only
artifact for non-overlap holdout data preparation and verifies that the future
implementation is limited to a manifest-only builder. It does not implement the
builder, prepare data, run fixed-DP candidate generation, run replay, train
CAMP, modify Diffusion Planner, promote artifacts, deploy, or make safety/CAMP-
over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_implementation_static_contract_review_v1"
)
READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_implementation_static_contract_review_complete"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_implementation_static_contract_review_rejected"
)
SOURCE_PLAN_SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_implementation_plan_v1"
)
SOURCE_PLAN_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_implementation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_implementation_only"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
TARGET_HOLDOUT_SELECTION_LOGS = 128
TARGET_HOLDOUT_RECORDS = 12800
MINIMUM_HOLDOUT_SELECTION_LOGS = 32
MINIMUM_HOLDOUT_RECORDS = 3200
FUTURE_BUILDER_SCRIPT = (
    "scripts/integrations/build_diffusion_planner_dp_camp_v13_"
    "nonoverlap_holdout_data_preparation_manifest.py"
)
FUTURE_BUILDER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "nonoverlap_holdout_data_preparation_manifest_builder.py"
)
REQUIRED_FUTURE_OUTPUTS = (
    "holdout_candidate_request_manifest.json",
    "nonoverlap_exclusion_registry_manifest.json",
    "holdout_preparation_runbook.sh",
    "expected_holdout_artifact_manifest.json",
    "SHA256SUMS",
)
REQUIRED_STATIC_REVIEW_PHRASES = (
    "manifest-only",
    "does not invoke DP",
    "formal seeds 11/12/13",
    "target 128 logs and 12800 records",
    "zero-intersection registry requirements",
    "CAMP candidate generation forbidden",
    "score_k(w)=a_k^T w",
    "nonnegative simplex",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only static contract review for the v13 static DP-reward "
            "non-overlap holdout data preparation implementation plan."
        )
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
    implementation_plan_json = implementation_plan_json.resolve()
    implementation_plan_script_py = implementation_plan_script_py.resolve()
    implementation_plan_test_py = implementation_plan_test_py.resolve()
    v13_audit_md = v13_audit_md.resolve()

    source_plan = _load_json_dict(implementation_plan_json)
    script_text = _read_text(implementation_plan_script_py)
    test_text = _read_text(implementation_plan_test_py)
    audit_text = _read_text(v13_audit_md)
    source_summary = _source_summary(source_plan)
    implementation_plan = _implementation_plan_summary(source_plan)
    checks = _checks(
        implementation_plan_json=implementation_plan_json,
        implementation_plan_script_py=implementation_plan_script_py,
        implementation_plan_test_py=implementation_plan_test_py,
        v13_audit_md=v13_audit_md,
        source_plan=source_plan,
        source_summary=source_summary,
        implementation_plan=implementation_plan,
        script_text=script_text,
        test_text=test_text,
        audit_text=audit_text,
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
            "builder_implementation_execution": False,
            "data_preparation_execution": False,
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
            "implementation_plan_json": str(implementation_plan_json),
            "implementation_plan_script_py": str(implementation_plan_script_py),
            "implementation_plan_test_py": str(implementation_plan_test_py),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_hashes": {
            "implementation_plan_json_sha256": _sha256(implementation_plan_json),
            "implementation_plan_script_py_sha256": _sha256(implementation_plan_script_py),
            "implementation_plan_test_py_sha256": _sha256(implementation_plan_test_py),
            "v13_audit_md_sha256": _sha256(v13_audit_md),
        },
        "source_summary": source_summary,
        "implementation_plan": implementation_plan,
        "review_checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "implementation_static_contract_review_complete": passed,
            "builder_implementation_authorized_next": passed,
            "data_preparation_authorized_next": False,
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


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["implementation_plan"]
    return "\n".join(
        [
            "# V13 Static DP-Reward Holdout Preparation Implementation Static Contract Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Builder implementation authorized next: `{decision['builder_implementation_authorized_next']}`",
            f"- Data preparation authorized next: `{decision['data_preparation_authorized_next']}`",
            f"- Fixed-DP candidate generation authorized next: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
            f"- Future builder script: `{plan['future_builder_script']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            "",
            "This review is read-only. It does not implement the builder, prepare data, run fixed-DP candidate generation, run replay, train CAMP, modify DP, promote, deploy, or authorize safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _source_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_plan.get("final_decision"))
    summary = _dict(source_plan.get("source_summary"))
    analysis = _dict(source_plan.get("analysis"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "implementation_plan_ready": decision.get("implementation_plan_ready"),
        "implementation_static_contract_review_authorized_next": decision.get(
            "implementation_static_contract_review_authorized_next"
        ),
        "data_preparation_authorized_next": decision.get("data_preparation_authorized_next"),
        "implementation_authorized_next": decision.get("implementation_authorized_next"),
        "training_preflight_authorized_next": decision.get("training_preflight_authorized_next"),
        "training_execution_authorized_next": decision.get("training_execution_authorized_next"),
        "replay_execution_authorized_next": decision.get("replay_execution_authorized_next"),
        "fixed_dp_candidate_generation_authorized_next": decision.get(
            "fixed_dp_candidate_generation_authorized_next"
        ),
        "candidate_generation_by_camp_authorized": decision.get(
            "candidate_generation_by_camp_authorized"
        ),
        "dp_modification_authorized": decision.get("dp_modification_authorized"),
        "selector_promotion_authorized": decision.get("selector_promotion_authorized"),
        "atom_promotion_authorized": decision.get("atom_promotion_authorized"),
        "deployment_authorized": decision.get("deployment_authorized"),
        "safety_benefit_claim_authorized": decision.get("safety_benefit_claim_authorized"),
        "camp_over_dp_top1_claim_authorized": decision.get("camp_over_dp_top1_claim_authorized"),
        "source_review_status": summary.get("status"),
        "source_review_authorized_next_work": summary.get("authorized_next_work"),
        "target_holdout_selection_logs": summary.get("target_holdout_selection_logs"),
        "target_holdout_records": summary.get("target_holdout_records"),
        "minimum_holdout_selection_logs": summary.get("minimum_holdout_selection_logs"),
        "minimum_holdout_records": summary.get("minimum_holdout_records"),
        "train_eval_candidate_tensor_intersection_must_be_zero": summary.get(
            "train_eval_candidate_tensor_intersection_must_be_zero"
        ),
        "candidate_generation_by_camp_forbidden": summary.get(
            "candidate_generation_by_camp_forbidden"
        ),
        "dp_modification_forbidden": summary.get("dp_modification_forbidden"),
        "executed_trajectory_must_remain_dp_top1": summary.get(
            "executed_trajectory_must_remain_dp_top1"
        ),
        "nonnegative_simplex_weights_only": summary.get("nonnegative_simplex_weights_only"),
        "score_expression": summary.get("score_expression"),
        "plan_only": analysis.get("plan_only"),
        "data_preparation_execution": analysis.get("data_preparation_execution"),
        "fixed_dp_candidate_generation_execution": analysis.get(
            "fixed_dp_candidate_generation_execution"
        ),
        "training_execution": analysis.get("training_execution"),
        "replay_execution": analysis.get("replay_execution"),
        "candidate_operation": analysis.get("candidate_operation"),
    }


def _implementation_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    plan = _dict(source_plan.get("implementation_plan"))
    scope = _dict(plan.get("future_builder_scope"))
    blocked = _dict(plan.get("not_authorized_by_this_plan"))
    return {
        "status": plan.get("status"),
        "implementation_performed_by_this_gate": plan.get("implementation_performed_by_this_gate"),
        "future_builder_script": plan.get("future_builder_script"),
        "future_builder_test": plan.get("future_builder_test"),
        "future_builder_inputs": _list(plan.get("future_builder_inputs")),
        "future_builder_outputs": _list(plan.get("future_builder_outputs")),
        "future_static_review_requirements": _list(plan.get("future_static_review_requirements")),
        "scope": scope,
        "materialize_holdout_request_manifest": scope.get("materialize_holdout_request_manifest"),
        "materialize_exclusion_registry_manifest": scope.get(
            "materialize_exclusion_registry_manifest"
        ),
        "materialize_validation_runbook": scope.get("materialize_validation_runbook"),
        "materialize_expected_output_manifest": scope.get("materialize_expected_output_manifest"),
        "scope_modify_dp": scope.get("modify_dp"),
        "scope_run_fixed_dp_candidate_generation": scope.get("run_fixed_dp_candidate_generation"),
        "scope_run_replay": scope.get("run_replay"),
        "scope_train_camp": scope.get("train_camp"),
        "not_authorized_by_this_plan": blocked,
    }


def _checks(
    *,
    implementation_plan_json: Path,
    implementation_plan_script_py: Path,
    implementation_plan_test_py: Path,
    v13_audit_md: Path,
    source_plan: dict[str, Any],
    source_summary: dict[str, Any],
    implementation_plan: dict[str, Any],
    script_text: str,
    test_text: str,
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks = [
        _check("implementation_plan_json_exists", implementation_plan_json.is_file(), str(implementation_plan_json), "file exists"),
        _check("implementation_plan_script_py_exists", implementation_plan_script_py.is_file(), str(implementation_plan_script_py), "file exists"),
        _check("implementation_plan_test_py_exists", implementation_plan_test_py.is_file(), str(implementation_plan_test_py), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        _check("current_dp_head_fixed", current_dp_head == required_dp_head, current_dp_head, required_dp_head),
        _check("required_dp_head_fixed", required_dp_head == FIXED_DP_HEAD, required_dp_head, FIXED_DP_HEAD),
        _contains("current_gate_authorized_in_audit", audit_text, f"next_work_target={authorized_current_work}"),
        _contains(
            "current_status_implementation_plan_ready",
            audit_text,
            "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_"
            "shadow_replay_evaluation_nonoverlap_holdout_data_preparation_"
            "implementation_plan_ready",
        ),
        _contains(
            "audit_keeps_data_preparation_disabled",
            audit_text,
            "data_preparation_authorized_by_current_boundary=False",
        ),
        _contains(
            "audit_keeps_training_execution_disabled",
            audit_text,
            "training_execution_authorized_by_current_boundary=False",
        ),
        _contains(
            "audit_keeps_fixed_dp_candidate_generation_disabled",
            audit_text,
            "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        ),
        _contains(
            "audit_keeps_camp_candidate_generation_disabled",
            audit_text,
            "candidate_generation_by_camp_authorized_by_current_boundary=False",
        ),
        _contains("audit_keeps_dp_modification_disabled", audit_text, "dp_modification_authorized_by_current_boundary=False"),
        _expect_summary(source_summary, "schema_version", SOURCE_PLAN_SCHEMA_VERSION),
        _expect_summary(source_summary, "status", SOURCE_PLAN_STATUS),
        _expect_summary(source_summary, "passed", True),
        _expect_summary(source_summary, "failed_checks", []),
        _expect_summary(source_summary, "authorized_next_work", authorized_current_work),
        _expect_summary(source_summary, "implementation_plan_ready", True),
        _expect_summary(source_summary, "implementation_static_contract_review_authorized_next", True),
        _expect_summary(source_summary, "data_preparation_authorized_next", False),
        _expect_summary(source_summary, "implementation_authorized_next", False),
        _expect_summary(source_summary, "training_preflight_authorized_next", False),
        _expect_summary(source_summary, "training_execution_authorized_next", False),
        _expect_summary(source_summary, "replay_execution_authorized_next", False),
        _expect_summary(source_summary, "fixed_dp_candidate_generation_authorized_next", False),
        _expect_summary(source_summary, "candidate_generation_by_camp_authorized", False),
        _expect_summary(source_summary, "dp_modification_authorized", False),
        _expect_summary(source_summary, "selector_promotion_authorized", False),
        _expect_summary(source_summary, "atom_promotion_authorized", False),
        _expect_summary(source_summary, "deployment_authorized", False),
        _expect_summary(source_summary, "safety_benefit_claim_authorized", False),
        _expect_summary(source_summary, "camp_over_dp_top1_claim_authorized", False),
        _expect_summary(
            source_summary,
            "source_review_status",
            "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
            "nonoverlap_holdout_data_preparation_static_contract_review_complete",
        ),
        _expect_summary(
            source_summary,
            "source_review_authorized_next_work",
            "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
            "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
            "nonoverlap_holdout_data_preparation_implementation_plan_only",
        ),
        _expect_summary(source_summary, "target_holdout_selection_logs", TARGET_HOLDOUT_SELECTION_LOGS),
        _expect_summary(source_summary, "target_holdout_records", TARGET_HOLDOUT_RECORDS),
        _expect_summary(source_summary, "minimum_holdout_selection_logs", MINIMUM_HOLDOUT_SELECTION_LOGS),
        _expect_summary(source_summary, "minimum_holdout_records", MINIMUM_HOLDOUT_RECORDS),
        _expect_summary(source_summary, "train_eval_candidate_tensor_intersection_must_be_zero", True),
        _expect_summary(source_summary, "candidate_generation_by_camp_forbidden", True),
        _expect_summary(source_summary, "dp_modification_forbidden", True),
        _expect_summary(source_summary, "executed_trajectory_must_remain_dp_top1", True),
        _expect_summary(source_summary, "nonnegative_simplex_weights_only", True),
        _expect_summary(source_summary, "score_expression", SCORE_EXPRESSION),
        _expect_summary(source_summary, "plan_only", True),
        _expect_summary(source_summary, "data_preparation_execution", False),
        _expect_summary(source_summary, "fixed_dp_candidate_generation_execution", False),
        _expect_summary(source_summary, "training_execution", False),
        _expect_summary(source_summary, "replay_execution", False),
        _expect_summary(source_summary, "candidate_operation", "fixed DP candidate reranking only"),
        _expect_plan(implementation_plan, "status", "plan_ready_no_implementation"),
        _expect_plan(implementation_plan, "implementation_performed_by_this_gate", False),
        _expect_plan(implementation_plan, "future_builder_script", FUTURE_BUILDER_SCRIPT),
        _expect_plan(implementation_plan, "future_builder_test", FUTURE_BUILDER_TEST),
        _expect_plan(implementation_plan, "materialize_holdout_request_manifest", True),
        _expect_plan(implementation_plan, "materialize_exclusion_registry_manifest", True),
        _expect_plan(implementation_plan, "materialize_validation_runbook", True),
        _expect_plan(implementation_plan, "materialize_expected_output_manifest", True),
        _expect_plan(implementation_plan, "scope_modify_dp", False),
        _expect_plan(implementation_plan, "scope_run_fixed_dp_candidate_generation", False),
        _expect_plan(implementation_plan, "scope_run_replay", False),
        _expect_plan(implementation_plan, "scope_train_camp", False),
        _contains("implementation_plan_script_mentions_current_gate", script_text, "nonoverlap_holdout_data_preparation_implementation_plan_only"),
        _contains("implementation_plan_script_mentions_next_gate", script_text, "nonoverlap_holdout_data_preparation_implementation_static_contract_review_only"),
        _contains("implementation_plan_script_mentions_future_builder_constant", script_text, "FUTURE_BUILDER_SCRIPT"),
        _contains(
            "implementation_plan_script_mentions_future_builder_filename",
            script_text,
            "nonoverlap_holdout_data_preparation_manifest.py",
        ),
        _contains("implementation_plan_script_mentions_no_implementation", script_text, "implementation_performed_by_this_gate"),
        _contains("implementation_plan_test_rejects_data_preparation_auth", test_text, "test_holdout_data_preparation_implementation_plan_rejects_data_preparation_auth"),
        _contains("implementation_plan_test_rejects_zero_intersection_drift", test_text, "test_holdout_data_preparation_implementation_plan_rejects_missing_zero_contract"),
        _contains("implementation_plan_test_rejects_dp_head_drift", test_text, "test_holdout_data_preparation_implementation_plan_rejects_dp_head_drift"),
    ]
    for output_name in REQUIRED_FUTURE_OUTPUTS:
        checks.append(
            _list_contains(
                f"planned_future_output_{_slug(output_name)}",
                implementation_plan["future_builder_outputs"],
                output_name,
            )
        )
    for phrase in REQUIRED_STATIC_REVIEW_PHRASES:
        checks.append(
            _list_contains(
                f"future_static_review_requirement_{_slug(phrase)}",
                implementation_plan["future_static_review_requirements"],
                phrase,
            )
        )
    for key in (
        "data_preparation",
        "implementation",
        "training_preflight",
        "training_execution",
        "replay_execution",
        "fixed_dp_candidate_generation",
        "candidate_generation_by_camp",
        "dp_modification",
        "promotion",
        "deployment",
        "safety_claim",
        "camp_over_dp_top1_claim",
    ):
        blocked = implementation_plan["not_authorized_by_this_plan"].get(key)
        checks.append(_check(f"plan_blocks_{key}", blocked is True, blocked, True))
    return checks


def _expect_summary(summary: dict[str, Any], key: str, expected: Any) -> dict[str, Any]:
    return _check(key, summary.get(key) == expected, summary.get(key), expected)


def _expect_plan(plan: dict[str, Any], key: str, expected: Any) -> dict[str, Any]:
    return _check(f"implementation_plan_{key}", plan.get(key) == expected, plan.get(key), expected)


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else None, needle)


def _list_contains(name: str, items: list[Any], needle: str) -> dict[str, Any]:
    observed = [item for item in items if isinstance(item, str) and needle in item]
    return _check(name, bool(observed), observed, f"contains {needle}")


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _load_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value.lower()).strip("_")


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
