#!/usr/bin/env python3
"""Plan implementation for v13 non-overlap holdout data preparation.

This is a plan-only gate. It consumes the completed static contract review for
the holdout data preparation plan and defines the future implementation scope.
It does not implement the builder, prepare data, run replay, generate fixed-DP
candidates, train CAMP, modify Diffusion Planner, promote artifacts, deploy, or
make safety/CAMP-over-DP claims.
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
    "nonoverlap_holdout_data_preparation_implementation_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_implementation_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_implementation_plan_rejected"
)
SOURCE_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_static_contract_review_v1"
)
SOURCE_REVIEW_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_static_contract_review_complete"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_implementation_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_implementation_static_contract_review_only"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
TARGET_HOLDOUT_SELECTION_LOGS = 128
TARGET_HOLDOUT_RECORDS = 12800
MINIMUM_HOLDOUT_SELECTION_LOGS = 32
MINIMUM_HOLDOUT_RECORDS = 3200
EXPECTED_STEPS_PER_LOG = 100
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14
FUTURE_BUILDER_SCRIPT = (
    "scripts/integrations/build_diffusion_planner_dp_camp_v13_"
    "nonoverlap_holdout_data_preparation_manifest.py"
)
FUTURE_BUILDER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "nonoverlap_holdout_data_preparation_manifest_builder.py"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only implementation plan for v13 static DP-reward "
            "non-overlap holdout data preparation."
        )
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
    source_review = _load_json_dict(static_contract_review_json)
    audit_text = _read_text(v13_audit_md)
    source_summary = _source_summary(source_review)
    implementation_plan = _implementation_plan(source_review)
    checks = _checks(
        static_contract_review_json=static_contract_review_json,
        v13_audit_md=v13_audit_md,
        source_review=source_review,
        audit_text=audit_text,
        source_summary=source_summary,
        implementation_plan=implementation_plan,
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
            "implementation_execution": False,
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
            "static_contract_review_json": str(static_contract_review_json),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_hashes": {
            "static_contract_review_json_sha256": _sha256(static_contract_review_json),
            "v13_audit_md_sha256": _sha256(v13_audit_md),
        },
        "source_summary": source_summary,
        "implementation_plan": implementation_plan,
        "plan_checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "implementation_plan_ready": passed,
            "implementation_static_contract_review_authorized_next": passed,
            "implementation_authorized_next": False,
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


def _source_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_review.get("final_decision"))
    contract = _dict(source_review.get("contract_summary"))
    return {
        "schema_version": source_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "implementation_plan_authorized_next": decision.get(
            "implementation_plan_authorized_next"
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
        "camp_over_dp_top1_claim_authorized": decision.get(
            "camp_over_dp_top1_claim_authorized"
        ),
        "source_plan_status": contract.get("source_plan_status"),
        "target_holdout_records": contract.get("target_holdout_records"),
        "target_holdout_selection_logs": contract.get("target_holdout_selection_logs"),
        "minimum_holdout_records": contract.get("minimum_holdout_records"),
        "minimum_holdout_selection_logs": contract.get("minimum_holdout_selection_logs"),
        "train_eval_candidate_tensor_intersection_must_be_zero": contract.get(
            "train_eval_candidate_tensor_intersection_must_be_zero"
        ),
        "candidate_generation_by_camp_forbidden": contract.get(
            "candidate_generation_by_camp_forbidden"
        ),
        "dp_modification_forbidden": contract.get("dp_modification_forbidden"),
        "executed_trajectory_must_remain_dp_top1": contract.get(
            "executed_trajectory_must_remain_dp_top1"
        ),
        "score_expression": contract.get("score_expression"),
        "nonnegative_simplex_weights_only": contract.get("nonnegative_simplex_weights_only"),
    }


def _implementation_plan(source_review: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "plan_ready_no_implementation",
        "implementation_performed_by_this_gate": False,
        "future_builder_script": FUTURE_BUILDER_SCRIPT,
        "future_builder_test": FUTURE_BUILDER_TEST,
        "future_builder_scope": {
            "materialize_holdout_request_manifest": True,
            "materialize_exclusion_registry_manifest": True,
            "materialize_validation_runbook": True,
            "materialize_expected_output_manifest": True,
            "run_fixed_dp_candidate_generation": False,
            "run_replay": False,
            "train_camp": False,
            "modify_dp": False,
        },
        "future_builder_inputs": [
            "source static contract review json",
            "prior training summary json path from source plan",
            "rejected evaluation registry paths from source plan",
            "non-formal route/seed candidate manifest",
        ],
        "future_builder_outputs": [
            "holdout_candidate_request_manifest.json",
            "nonoverlap_exclusion_registry_manifest.json",
            "holdout_preparation_runbook.sh",
            "expected_holdout_artifact_manifest.json",
            "SHA256SUMS",
        ],
        "future_static_review_requirements": [
            "confirm builder is manifest-only and does not invoke DP",
            "confirm builder rejects formal seeds 11/12/13",
            "confirm builder requires target 128 logs and 12800 records",
            "confirm builder carries zero-intersection registry requirements forward",
            "confirm builder keeps CAMP candidate generation forbidden",
            "confirm builder keeps score_k(w)=a_k^T w and nonnegative simplex boundaries",
        ],
        "not_authorized_by_this_plan": {
            "implementation": True,
            "data_preparation": True,
            "training_preflight": True,
            "training_execution": True,
            "replay_execution": True,
            "fixed_dp_candidate_generation": True,
            "candidate_generation_by_camp": True,
            "dp_modification": True,
            "promotion": True,
            "deployment": True,
            "safety_claim": True,
            "camp_over_dp_top1_claim": True,
        },
        "source_static_review_hashes": _dict(source_review.get("source_hashes")),
    }


def _checks(
    *,
    static_contract_review_json: Path,
    v13_audit_md: Path,
    source_review: dict[str, Any],
    audit_text: str,
    source_summary: dict[str, Any],
    implementation_plan: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    return [
        _check("static_contract_review_json_exists", static_contract_review_json.is_file(), str(static_contract_review_json), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _check("current_gate_authorized_in_audit", f"next_work_target={authorized_current_work}" in audit_text, authorized_current_work, "present as next_work_target"),
        _check("current_status_static_contract_complete", "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_nonoverlap_holdout_data_preparation_static_contract_review_complete" in audit_text, "static_contract_review_complete", "present in audit"),
        _check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        _check("current_dp_head_fixed", current_dp_head == required_dp_head, current_dp_head, required_dp_head),
        _check("required_dp_head_fixed", required_dp_head == FIXED_DP_HEAD, required_dp_head, FIXED_DP_HEAD),
        _check("source_schema_version", source_review.get("schema_version") == SOURCE_REVIEW_SCHEMA_VERSION, source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA_VERSION),
        _expect_value(source_summary, "status", SOURCE_REVIEW_STATUS),
        _expect_value(source_summary, "passed", True),
        _expect_value(source_summary, "failed_checks", []),
        _expect_value(source_summary, "authorized_next_work", authorized_current_work),
        _expect_value(source_summary, "implementation_plan_authorized_next", True),
        _expect_value(source_summary, "data_preparation_authorized_next", False),
        _expect_value(source_summary, "implementation_authorized_next", False),
        _expect_value(source_summary, "training_preflight_authorized_next", False),
        _expect_value(source_summary, "training_execution_authorized_next", False),
        _expect_value(source_summary, "replay_execution_authorized_next", False),
        _expect_value(source_summary, "fixed_dp_candidate_generation_authorized_next", False),
        _expect_value(source_summary, "candidate_generation_by_camp_authorized", False),
        _expect_value(source_summary, "dp_modification_authorized", False),
        _expect_value(source_summary, "selector_promotion_authorized", False),
        _expect_value(source_summary, "atom_promotion_authorized", False),
        _expect_value(source_summary, "deployment_authorized", False),
        _expect_value(source_summary, "safety_benefit_claim_authorized", False),
        _expect_value(source_summary, "camp_over_dp_top1_claim_authorized", False),
        _expect_value(source_summary, "source_plan_status", "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_holdout_data_preparation_plan_ready"),
        _expect_value(source_summary, "target_holdout_records", TARGET_HOLDOUT_RECORDS),
        _expect_value(source_summary, "target_holdout_selection_logs", TARGET_HOLDOUT_SELECTION_LOGS),
        _expect_value(source_summary, "minimum_holdout_records", MINIMUM_HOLDOUT_RECORDS),
        _expect_value(source_summary, "minimum_holdout_selection_logs", MINIMUM_HOLDOUT_SELECTION_LOGS),
        _expect_value(source_summary, "train_eval_candidate_tensor_intersection_must_be_zero", True),
        _expect_value(source_summary, "candidate_generation_by_camp_forbidden", True),
        _expect_value(source_summary, "dp_modification_forbidden", True),
        _expect_value(source_summary, "executed_trajectory_must_remain_dp_top1", True),
        _expect_value(source_summary, "score_expression", SCORE_EXPRESSION),
        _expect_value(source_summary, "nonnegative_simplex_weights_only", True),
        _check("implementation_plan_is_plan_only", implementation_plan["implementation_performed_by_this_gate"] is False, implementation_plan["implementation_performed_by_this_gate"], False),
        _check("implementation_plan_future_builder_named", implementation_plan["future_builder_script"] == FUTURE_BUILDER_SCRIPT, implementation_plan["future_builder_script"], FUTURE_BUILDER_SCRIPT),
        _check("implementation_plan_builder_manifest_only", implementation_plan["future_builder_scope"]["run_fixed_dp_candidate_generation"] is False, implementation_plan["future_builder_scope"]["run_fixed_dp_candidate_generation"], False),
        _check("implementation_plan_blocks_data_preparation", implementation_plan["not_authorized_by_this_plan"]["data_preparation"] is True, True, True),
        _check("implementation_plan_blocks_training", implementation_plan["not_authorized_by_this_plan"]["training_execution"] is True, True, True),
        _check("implementation_plan_blocks_dp_modification", implementation_plan["not_authorized_by_this_plan"]["dp_modification"] is True, True, True),
        _contains("audit_blocks_data_preparation", audit_text, "data_preparation_authorized_by_current_boundary=False"),
        _contains("audit_blocks_training_preflight", audit_text, "static_dp_reward_training_preflight_authorized_by_current_boundary=False"),
        _contains("audit_blocks_fixed_dp_candidate_generation", audit_text, "fixed_dp_candidate_generation_authorized_by_current_boundary=False"),
        _contains("audit_blocks_dp_modification", audit_text, "dp_modification_authorized_by_current_boundary=False"),
        _contains("audit_blocks_safety_claim", audit_text, "safety_benefit_claim_authorized=False"),
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["implementation_plan"]
    return "\n".join(
        [
            "# V13 Static DP-Reward Non-Overlap Holdout Data Preparation Implementation Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Future builder: `{plan['future_builder_script']}`",
            f"- Implementation authorized: `{decision['implementation_authorized_next']}`",
            f"- Data preparation authorized: `{decision['data_preparation_authorized_next']}`",
            f"- Fixed-DP candidate generation authorized: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
            "",
            "This gate is plan-only. It does not implement the builder, prepare data, run replay, generate candidates, train CAMP, modify DP, promote, deploy, or make safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _expect_value(summary: dict[str, Any], key: str, expected: Any) -> dict[str, Any]:
    return _check(key, summary.get(key) == expected, summary.get(key), expected)


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else None, needle)


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
