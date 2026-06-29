#!/usr/bin/env python3
"""Static contract review for v13 non-overlap holdout data preparation planning.

This is a read-only review gate. It consumes the plan-only holdout data
preparation artifact and verifies that the future data-preparation scope
preserves the fixed-DP/CAMP reranking boundary before any later implementation
plan. It does not prepare data, run replay, generate candidates, train CAMP,
modify Diffusion Planner, promote artifacts, deploy, or make safety/CAMP-over-DP
claims.
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
    "nonoverlap_holdout_data_preparation_static_contract_review_v1"
)
READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_static_contract_review_complete"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_static_contract_review_rejected"
)
SOURCE_PLAN_SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_plan_v1"
)
SOURCE_PLAN_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_plan_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_implementation_plan_only"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
MINIMUM_HOLDOUT_RECORDS = 3200
MINIMUM_HOLDOUT_SELECTION_LOGS = 32
TARGET_HOLDOUT_RECORDS = 12800
TARGET_HOLDOUT_SELECTION_LOGS = 128
EXPECTED_STEPS_PER_LOG = 100
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only static contract review of a v13 static DP-reward "
            "non-overlap holdout data preparation plan."
        )
    )
    parser.add_argument("--holdout_plan_json", type=Path, required=True)
    parser.add_argument("--holdout_plan_script_py", type=Path, required=True)
    parser.add_argument("--holdout_plan_test_py", type=Path, required=True)
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
        holdout_plan_json=args.holdout_plan_json,
        holdout_plan_script_py=args.holdout_plan_script_py,
        holdout_plan_test_py=args.holdout_plan_test_py,
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
    holdout_plan_json: Path,
    holdout_plan_script_py: Path,
    holdout_plan_test_py: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    holdout_plan_json = holdout_plan_json.resolve()
    holdout_plan_script_py = holdout_plan_script_py.resolve()
    holdout_plan_test_py = holdout_plan_test_py.resolve()
    v13_audit_md = v13_audit_md.resolve()
    plan = _load_json_dict(holdout_plan_json)
    script_text = _read_text(holdout_plan_script_py)
    test_text = _read_text(holdout_plan_test_py)
    audit_text = _read_text(v13_audit_md)
    contract = _contract_summary(plan)
    checks = _checks(
        holdout_plan_json=holdout_plan_json,
        holdout_plan_script_py=holdout_plan_script_py,
        holdout_plan_test_py=holdout_plan_test_py,
        v13_audit_md=v13_audit_md,
        plan=plan,
        script_text=script_text,
        test_text=test_text,
        audit_text=audit_text,
        contract=contract,
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
            "holdout_plan_json": str(holdout_plan_json),
            "holdout_plan_script_py": str(holdout_plan_script_py),
            "holdout_plan_test_py": str(holdout_plan_test_py),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_hashes": {
            "holdout_plan_json_sha256": _sha256(holdout_plan_json),
            "holdout_plan_script_py_sha256": _sha256(holdout_plan_script_py),
            "holdout_plan_test_py_sha256": _sha256(holdout_plan_test_py),
            "v13_audit_md_sha256": _sha256(v13_audit_md),
        },
        "contract_summary": contract,
        "review_checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "failed_checks": failed,
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work if passed else None,
            "implementation_plan_authorized_next": passed,
            "data_preparation_authorized_next": False,
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


def _contract_summary(plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(plan.get("final_decision"))
    holdout = _dict(plan.get("holdout_data_preparation_plan"))
    source = _dict(plan.get("source_summary"))
    target = _dict(holdout.get("target_scale"))
    minimum = _dict(holdout.get("minimum_scale"))
    required = _dict(holdout.get("required_nonoverlap_contracts"))
    constraints = _dict(holdout.get("future_execution_constraints"))
    math = _dict(holdout.get("math_contract"))
    blocked = _dict(holdout.get("blocked_by_this_plan"))
    return {
        "source_plan_status": decision.get("status"),
        "source_plan_passed": decision.get("passed"),
        "source_failed_checks": decision.get("failed_checks"),
        "source_authorized_next_work": decision.get("authorized_next_work"),
        "source_static_contract_review_authorized_next": decision.get(
            "static_contract_review_authorized_next"
        ),
        "source_records_total": source.get("records_total"),
        "source_selection_log_count": source.get("selection_log_count"),
        "source_candidate_tensor_intersection": source.get(
            "candidate_tensor_registry_intersection_count"
        ),
        "source_path_signature_intersection": source.get(
            "path_signature_registry_intersection_count"
        ),
        "source_record_identity_intersection": source.get(
            "record_identity_registry_intersection_count"
        ),
        "data_preparation_performed_by_source_plan": holdout.get(
            "data_preparation_performed_by_this_gate"
        ),
        "target_holdout_records": target.get("target_holdout_records"),
        "target_holdout_selection_logs": target.get("target_holdout_selection_logs"),
        "expected_candidate_count": target.get("expected_candidate_count"),
        "expected_atom_count": target.get("expected_atom_count"),
        "minimum_holdout_records": minimum.get("minimum_holdout_records"),
        "minimum_holdout_selection_logs": minimum.get("minimum_holdout_selection_logs"),
        "expected_steps_per_log": minimum.get("expected_steps_per_log"),
        "train_holdout_root_intersection_must_be_zero": required.get(
            "train_holdout_root_intersection_must_be_zero"
        ),
        "train_eval_candidate_tensor_intersection_must_be_zero": required.get(
            "train_eval_candidate_tensor_intersection_must_be_zero"
        ),
        "train_eval_path_signature_intersection_must_be_zero": required.get(
            "train_eval_path_signature_intersection_must_be_zero"
        ),
        "train_eval_record_identity_intersection_must_be_zero": required.get(
            "train_eval_record_identity_intersection_must_be_zero"
        ),
        "holdout_must_exclude_rejected_eval_path_signatures": required.get(
            "holdout_must_exclude_rejected_eval_path_signatures"
        ),
        "holdout_must_exclude_rejected_eval_record_identities": required.get(
            "holdout_must_exclude_rejected_eval_record_identities"
        ),
        "holdout_must_exclude_rejected_eval_candidate_tensors": required.get(
            "holdout_must_exclude_rejected_eval_candidate_tensors"
        ),
        "formal_seeds_11_12_13_excluded": required.get("formal_seeds_11_12_13_excluded"),
        "selection_log_count_check_required": required.get("selection_log_count_check_required"),
        "record_count_check_required": required.get("record_count_check_required"),
        "sha256_manifest_required": required.get("sha256_manifest_required"),
        "fixed_dp_candidate_generation_requires_later_explicit_gate": constraints.get(
            "fixed_dp_candidate_generation_requires_later_explicit_gate"
        ),
        "candidate_generation_by_camp_forbidden": constraints.get(
            "candidate_generation_by_camp_forbidden"
        ),
        "trajectory_generation_by_camp_forbidden": constraints.get(
            "trajectory_generation_by_camp_forbidden"
        ),
        "trajectory_modification_by_camp_forbidden": constraints.get(
            "trajectory_modification_by_camp_forbidden"
        ),
        "dp_modification_forbidden": constraints.get("dp_modification_forbidden"),
        "executed_trajectory_must_remain_dp_top1": constraints.get(
            "executed_trajectory_must_remain_dp_top1"
        ),
        "candidate_operation": math.get("candidate_operation"),
        "score_expression": math.get("score_expression"),
        "approved_atoms_only": math.get("approved_atoms_only"),
        "nonnegative_simplex_weights_only": math.get("nonnegative_simplex_weights_only"),
        "simplex_cvar_l2_master_convexity_preserved": math.get(
            "simplex_cvar_l2_master_convexity_preserved"
        ),
        "blocked_implementation": blocked.get("implementation"),
        "blocked_training_preflight": blocked.get("training_preflight"),
        "blocked_training_execution": blocked.get("training_execution"),
        "blocked_replay_execution": blocked.get("replay_execution"),
        "blocked_fixed_dp_candidate_generation": blocked.get("fixed_dp_candidate_generation"),
        "blocked_candidate_generation_by_camp": blocked.get("candidate_generation_by_camp"),
        "blocked_dp_modification": blocked.get("dp_modification"),
        "blocked_selector_promotion": blocked.get("selector_promotion"),
        "blocked_atom_promotion": blocked.get("atom_promotion"),
        "blocked_deployment": blocked.get("deployment"),
        "blocked_safety_claim": blocked.get("safety_benefit_claim"),
        "blocked_camp_over_dp_top1_claim": blocked.get("camp_over_dp_top1_claim"),
    }


def _checks(
    *,
    holdout_plan_json: Path,
    holdout_plan_script_py: Path,
    holdout_plan_test_py: Path,
    v13_audit_md: Path,
    plan: dict[str, Any],
    script_text: str,
    test_text: str,
    audit_text: str,
    contract: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(plan.get("final_decision"))
    return [
        _check("holdout_plan_json_exists", holdout_plan_json.is_file(), str(holdout_plan_json), "file exists"),
        _check("holdout_plan_script_py_exists", holdout_plan_script_py.is_file(), str(holdout_plan_script_py), "file exists"),
        _check("holdout_plan_test_py_exists", holdout_plan_test_py.is_file(), str(holdout_plan_test_py), "file exists"),
        _check("v13_audit_md_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _check("current_gate_authorized_in_audit", f"next_work_target={authorized_current_work}" in audit_text, authorized_current_work, "present as next_work_target"),
        _check("current_status_plan_ready", "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_nonoverlap_holdout_data_preparation_plan_ready" in audit_text, "nonoverlap_holdout_data_preparation_plan_ready", "present in audit"),
        _check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        _check("current_dp_head_fixed", current_dp_head == required_dp_head, current_dp_head, required_dp_head),
        _check("required_dp_head_fixed", required_dp_head == FIXED_DP_HEAD, required_dp_head, FIXED_DP_HEAD),
        _check("source_schema_version", plan.get("schema_version") == SOURCE_PLAN_SCHEMA_VERSION, plan.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _check("source_plan_passed", decision.get("passed") is True, decision.get("passed"), True),
        _check("source_plan_failed_checks_empty", decision.get("failed_checks") == [], decision.get("failed_checks"), []),
        _check("source_plan_status_ready", decision.get("status") == SOURCE_PLAN_STATUS, decision.get("status"), SOURCE_PLAN_STATUS),
        _check("source_plan_authorizes_current_review", decision.get("authorized_next_work") == authorized_current_work, decision.get("authorized_next_work"), authorized_current_work),
        _expect_true(contract, "source_static_contract_review_authorized_next"),
        _expect_value(contract, "source_records_total", MINIMUM_HOLDOUT_RECORDS),
        _expect_value(contract, "source_selection_log_count", MINIMUM_HOLDOUT_SELECTION_LOGS),
        _expect_positive(contract, "source_candidate_tensor_intersection"),
        _expect_positive(contract, "source_path_signature_intersection"),
        _expect_positive(contract, "source_record_identity_intersection"),
        _expect_value(contract, "data_preparation_performed_by_source_plan", False),
        _expect_value(contract, "target_holdout_records", TARGET_HOLDOUT_RECORDS),
        _expect_value(contract, "target_holdout_selection_logs", TARGET_HOLDOUT_SELECTION_LOGS),
        _expect_value(contract, "expected_candidate_count", EXPECTED_CANDIDATE_COUNT),
        _expect_value(contract, "expected_atom_count", EXPECTED_ATOM_COUNT),
        _expect_value(contract, "minimum_holdout_records", MINIMUM_HOLDOUT_RECORDS),
        _expect_value(contract, "minimum_holdout_selection_logs", MINIMUM_HOLDOUT_SELECTION_LOGS),
        _expect_value(contract, "expected_steps_per_log", EXPECTED_STEPS_PER_LOG),
        _expect_true(contract, "train_holdout_root_intersection_must_be_zero"),
        _expect_true(contract, "train_eval_candidate_tensor_intersection_must_be_zero"),
        _expect_true(contract, "train_eval_path_signature_intersection_must_be_zero"),
        _expect_true(contract, "train_eval_record_identity_intersection_must_be_zero"),
        _expect_true(contract, "holdout_must_exclude_rejected_eval_path_signatures"),
        _expect_true(contract, "holdout_must_exclude_rejected_eval_record_identities"),
        _expect_true(contract, "holdout_must_exclude_rejected_eval_candidate_tensors"),
        _expect_true(contract, "formal_seeds_11_12_13_excluded"),
        _expect_true(contract, "selection_log_count_check_required"),
        _expect_true(contract, "record_count_check_required"),
        _expect_true(contract, "sha256_manifest_required"),
        _expect_true(contract, "fixed_dp_candidate_generation_requires_later_explicit_gate"),
        _expect_true(contract, "candidate_generation_by_camp_forbidden"),
        _expect_true(contract, "trajectory_generation_by_camp_forbidden"),
        _expect_true(contract, "trajectory_modification_by_camp_forbidden"),
        _expect_true(contract, "dp_modification_forbidden"),
        _expect_true(contract, "executed_trajectory_must_remain_dp_top1"),
        _expect_value(contract, "candidate_operation", "fixed DP candidate reranking only"),
        _expect_value(contract, "score_expression", SCORE_EXPRESSION),
        _expect_true(contract, "approved_atoms_only"),
        _expect_true(contract, "nonnegative_simplex_weights_only"),
        _expect_true(contract, "simplex_cvar_l2_master_convexity_preserved"),
        _expect_true(contract, "blocked_implementation"),
        _expect_true(contract, "blocked_training_preflight"),
        _expect_true(contract, "blocked_training_execution"),
        _expect_true(contract, "blocked_replay_execution"),
        _expect_true(contract, "blocked_fixed_dp_candidate_generation"),
        _expect_true(contract, "blocked_candidate_generation_by_camp"),
        _expect_true(contract, "blocked_dp_modification"),
        _expect_true(contract, "blocked_selector_promotion"),
        _expect_true(contract, "blocked_atom_promotion"),
        _expect_true(contract, "blocked_deployment"),
        _expect_true(contract, "blocked_safety_claim"),
        _expect_true(contract, "blocked_camp_over_dp_top1_claim"),
        _check("script_mentions_target_scale", "TARGET_HOLDOUT_RECORDS" in script_text and "TARGET_HOLDOUT_SELECTION_LOGS" in script_text, "target scale constants", "present"),
        _check("script_mentions_formal_seed_exclusion", "formal_seeds_11_12_13_excluded" in script_text, "formal seed exclusion", "present"),
        _check("test_covers_count_distribution", "count_distribution=True" in test_text, "count distribution test", "present"),
        _check("source_plan_does_not_authorize_data_preparation", decision.get("data_preparation_authorized_next") in (None, False), decision.get("data_preparation_authorized_next"), False),
        _check("source_plan_does_not_authorize_implementation", decision.get("implementation_authorized_next") is False, decision.get("implementation_authorized_next"), False),
        _check("source_plan_does_not_authorize_training_preflight", decision.get("training_preflight_authorized_next") is False, decision.get("training_preflight_authorized_next"), False),
        _check("source_plan_does_not_authorize_training_execution", decision.get("training_execution_authorized_next") is False, decision.get("training_execution_authorized_next"), False),
        _check("source_plan_does_not_authorize_replay_execution", decision.get("replay_execution_authorized_next") is False, decision.get("replay_execution_authorized_next"), False),
        _check("source_plan_does_not_authorize_fixed_dp_candidate_generation", decision.get("fixed_dp_candidate_generation_authorized_next") is False, decision.get("fixed_dp_candidate_generation_authorized_next"), False),
        _check("source_plan_does_not_authorize_camp_candidate_generation", decision.get("candidate_generation_by_camp_authorized") is False, decision.get("candidate_generation_by_camp_authorized"), False),
        _check("source_plan_does_not_authorize_dp_modification", decision.get("dp_modification_authorized") is False, decision.get("dp_modification_authorized"), False),
        _contains("audit_blocks_training_preflight", audit_text, "static_dp_reward_training_preflight_authorized_by_current_boundary=False"),
        _contains("audit_blocks_fixed_dp_candidate_generation", audit_text, "fixed_dp_candidate_generation_authorized_by_current_boundary=False"),
        _contains("audit_blocks_dp_modification", audit_text, "dp_modification_authorized_by_current_boundary=False"),
        _contains("audit_blocks_safety_claim", audit_text, "safety_benefit_claim_authorized=False"),
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    contract = report["contract_summary"]
    return "\n".join(
        [
            "# V13 Static DP-Reward Non-Overlap Holdout Data Preparation Static Contract Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source plan status: `{contract['source_plan_status']}`",
            f"- Target holdout records: `{contract['target_holdout_records']}`",
            f"- Target holdout logs: `{contract['target_holdout_selection_logs']}`",
            f"- Data preparation authorized next: `{decision['data_preparation_authorized_next']}`",
            f"- Fixed-DP candidate generation authorized next: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
            "",
            "This review is read-only. It does not prepare data, run replay, generate candidates, train CAMP, modify DP, promote selectors or atoms, deploy, or make safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _expect_true(contract: dict[str, Any], key: str) -> dict[str, Any]:
    return _check(key, contract.get(key) is True, contract.get(key), True)


def _expect_value(contract: dict[str, Any], key: str, expected: Any) -> dict[str, Any]:
    return _check(key, contract.get(key) == expected, contract.get(key), expected)


def _expect_positive(contract: dict[str, Any], key: str) -> dict[str, Any]:
    observed = contract.get(key)
    return _check(key, isinstance(observed, (int, float)) and observed > 0, observed, "> 0")


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
