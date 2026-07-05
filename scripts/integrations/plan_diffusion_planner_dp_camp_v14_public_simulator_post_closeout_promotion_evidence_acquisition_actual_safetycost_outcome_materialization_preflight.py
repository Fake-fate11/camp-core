#!/usr/bin/env python3
"""Plan actual-SafetyCost outcome-materialization preflight without executing it."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_source_static_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_actual_safetycost_evidence_gap_closure_"
        "plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_evidence_gap_closure_plan_static_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_source_static_review_module()
HELPER_MODULE = SOURCE_REVIEW_MODULE.HELPER_MODULE

FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_REVIEW_SCHEMA = SOURCE_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_STATUS = SOURCE_REVIEW_MODULE.READY_STATUS
SOURCE_REVIEW_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
BLOCKED_ACTIONS = SOURCE_REVIEW_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = SOURCE_REVIEW_MODULE.FALSE_EXECUTION_FLAGS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "actual_safetycost_outcome_materialization_preflight_plan_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_preflight_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_preflight_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_preflight_plan_static_review_only"
)

PLAN_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_preflight_plan.json"
)
PLAN_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_preflight_plan.md"
)

EXPECTED_REQUIRED_INPUTS = (
    "passed_actual_safetycost_evidence_gap_closure_plan_static_review_artifact",
    "fixed_dp_candidate_tensor_identity_manifest",
    "paired_shadow_selected_run_key_manifest",
    "closed_loop_outcome_materialization_execution_boundary",
    "outcome_storage_schema_and_hash_contract",
    "no_training_or_online_input_leakage_guard",
    "safetycost_v1_claim_rule_config",
    "artifact_heads_command_stdout_stderr_contract",
)
EXPECTED_PREFLIGHT_ITEMS = (
    "lock_static_review_artifact_and_source_plan_hashes",
    "enumerate_shadow_selected_run_keys_requiring_outcomes",
    "predeclare_closed_loop_runner_inputs_without_dp_modification",
    "predeclare_outcome_summary_schema_and_pairing_keys",
    "predeclare_no_training_online_input_and_no_claim_guard",
    "predeclare_full36_formal_seed_and_split_exclusion_checks",
    "predeclare_safetycost_v1_delta_ci_hard_gate_evaluation",
    "emit_static_reviewable_materialization_preflight_contract",
)
EXPECTED_PLANNED_OUTPUTS = (
    "shadow_selected_outcome_materialization_request_manifest",
    "outcome_summary_schema",
    "paired_outcome_identity_join_manifest",
    "safetycost_v1_evaluation_config_snapshot",
    "leakage_and_forbidden_action_no_go_register",
    "materialization_preflight_artifact_contract",
)
EXPECTED_NO_GO = (
    "source_static_review_missing_or_failed",
    "dp_head_drift",
    "candidate_tensor_identity_drift",
    "camp_generates_repairs_rewrites_or_blends_trajectory",
    "dp_code_config_weight_checkpoint_modification",
    "closed_loop_outcome_training_or_online_input",
    "full36_or_formal_seed_11_12_13_present",
    "non_affine_score_or_nonconvex_master",
    "promotion_deployment_online_selector_or_claim",
    "unpaired_or_duplicate_run_keys",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_md", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_record_count", type=int, default=3200)
    parser.add_argument("--expected_shadow_diff_records", type=int, default=2832)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization_preflight_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_md=args.source_static_review_md,
        source_static_review_sha256s=args.source_static_review_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_record_count=args.expected_record_count,
        expected_shadow_diff_records=args.expected_shadow_diff_records,
        label=args.label,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization_preflight_plan
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(HELPER_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_static_review_md: Path,
    source_static_review_sha256s: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_record_count: int = 3200,
    expected_shadow_diff_records: int = 2832,
    label: str | None = None,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = source_static_review_artifact_dir.resolve()
    review_json = source_static_review_json.resolve()
    review_md = source_static_review_md.resolve()
    review_sha256s = source_static_review_sha256s.resolve()
    output_dir = output_dir.resolve()

    source_review = HELPER_MODULE._read_json_dict(review_json)
    v14_text = HELPER_MODULE._read_text(v14_audit_md)
    status_text = HELPER_MODULE._read_text(current_status_md)
    heads = HELPER_MODULE._parse_key_values(HELPER_MODULE._read_text(artifact_dir / "HEADS"))
    run_exit = HELPER_MODULE._read_text(artifact_dir / "run.exit").strip()
    root_sha256s = HELPER_MODULE._read_sha256sums(artifact_dir / "SHA256SUMS")
    nested_sha256s = HELPER_MODULE._read_sha256sums(review_sha256s)

    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        review_json=review_json,
        review_md=review_md,
        review_sha256s=review_sha256s,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        run_exit=run_exit,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        source_review=source_review,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_record_count=expected_record_count,
        expected_shadow_diff_records=expected_shadow_diff_records,
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "plan_only": True,
            "read_only": True,
            "actual_safetycost_outcome_materialization_preflight_plan_only": True,
            "actual_safetycost_outcome_materialization_executed": False,
            "paired_evaluation_execution": False,
            "replay_execution": False,
            "training_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "source_static_review_artifact_dir": str(artifact_dir),
            "source_static_review_json": str(review_json),
            "source_static_review_md": str(review_md),
            "source_static_review_sha256s": str(review_sha256s),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir),
        },
        "source_artifact_hashes": _source_hashes(
            artifact_dir=artifact_dir,
            review_json=review_json,
            review_md=review_md,
            review_sha256s=review_sha256s,
        ),
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_artifact_camp_head": heads.get("CAMP_HEAD"),
            "source_artifact_camp_origin_main": heads.get("CAMP_ORIGIN_MAIN"),
            "source_artifact_dp_head": heads.get("DP_HEAD"),
        },
        "source_static_review_summary": _source_static_review_summary(source_review),
        "outcome_materialization_preflight_summary": _outcome_materialization_preflight_summary(source_review),
        "required_inputs": _required_inputs(source_review),
        "preflight_plan": _preflight_plan(),
        "planned_outputs": _planned_outputs(),
        "no_go_register": _no_go_register(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "preflight_plan_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, source_review=source_review),
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    review_json: Path,
    review_md: Path,
    review_sha256s: Path,
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    run_exit: str,
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    source_review: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_record_count: int,
    expected_shadow_diff_records: int,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    decision = HELPER_MODULE._dict(source_review.get("final_decision"))
    source_plan = HELPER_MODULE._dict(source_review.get("source_plan_summary"))
    gap = HELPER_MODULE._dict(source_review.get("evidence_gap_closure_summary"))

    def expect(name: str, actual: Any, expected: Any) -> None:
        checks.append({"name": name, "passed": actual == expected, "actual": actual, "expected": expected})

    def require(name: str, passed: bool, actual: Any = None, expected: Any = True) -> None:
        checks.append(
            {
                "name": name,
                "passed": bool(passed),
                "actual": actual if actual is not None else bool(passed),
                "expected": expected,
            }
        )

    require("outcome_materialization_preflight_plan_enabled", enabled)
    require("source_static_review_artifact_dir_exists", artifact_dir.is_dir())
    for name, path in {
        "source_static_review_json": review_json,
        "source_static_review_md": review_md,
        "source_static_review_sha256s": review_sha256s,
        "source_static_review_heads": artifact_dir / "HEADS",
        "source_static_review_command": artifact_dir / "COMMAND",
        "source_static_review_stdout": artifact_dir / "stdout",
        "source_static_review_stderr": artifact_dir / "stderr",
        "source_static_review_run_exit": artifact_dir / "run.exit",
        "source_static_review_root_sha256s": artifact_dir / "SHA256SUMS",
    }.items():
        require(f"{name}_exists", path.is_file())

    expect("current_dp_head_fixed", current_dp_head, required_dp_head)
    expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD)
    expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main)
    expect("source_artifact_dp_head_fixed", heads.get("DP_HEAD"), required_dp_head)
    expect("source_artifact_camp_matches_origin", heads.get("CAMP_HEAD"), heads.get("CAMP_ORIGIN_MAIN"))
    expect("source_static_review_run_exit", run_exit, "0")
    expect("audit_latest_status", HELPER_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_REVIEW_STATUS)
    expect("audit_latest_next_work", HELPER_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK)
    expect("status_doc_latest_status", HELPER_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_REVIEW_STATUS)
    expect("status_doc_latest_next_work", HELPER_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK)

    expect("source_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA)
    expect("source_review_passed", decision.get("passed"), True)
    expect("source_review_status", decision.get("status"), SOURCE_REVIEW_STATUS)
    expect("source_review_failed_checks", decision.get("failed_checks"), [])
    expect("source_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK)
    expect("source_review_static_review_passed", decision.get("post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_evidence_gap_closure_plan_static_review_passed"), True)
    expect("source_review_preflight_plan_authorized", decision.get("actual_safetycost_outcome_materialization_preflight_plan_authorized"), True)
    expect("source_review_no_outcome_materialization", decision.get("actual_safetycost_outcome_materialization_executed_by_this_gate"), False)
    expect("source_review_no_paired_execution", decision.get("paired_evaluation_executed_by_this_gate"), False)
    expect("source_review_actual_safetycost_available", decision.get("actual_safetycost_v1_available"), False)
    expect("source_review_claim_rule_evaluable", decision.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    for action in BLOCKED_ACTIONS:
        expect(f"source_review_decision_{action}", decision.get(action), False)
    for flag in FALSE_EXECUTION_FLAGS:
        expect(f"source_review_decision_{flag}", decision.get(flag), False)

    expect("source_static_review_check_count", len(_list(source_review.get("static_review_checks"))), 82)
    expect("source_plan_check_count", source_plan.get("plan_check_count"), 71)
    expect("source_plan_failed_check_count", source_plan.get("failed_check_count"), 0)
    expect("source_required_input_count", source_plan.get("required_input_count"), 8)
    expect("source_closure_plan_count", source_plan.get("closure_plan_count"), 8)
    expect("source_planned_output_count", source_plan.get("planned_output_count"), 6)
    expect("source_no_go_count", source_plan.get("no_go_count"), 10)
    expect("source_paired_record_count", source_plan.get("paired_record_count"), expected_record_count)
    expect("source_unique_paired_run_key_count", source_plan.get("unique_paired_run_key_count"), expected_record_count)
    expect("source_shadow_diff_records", source_plan.get("shadow_diff_records"), expected_shadow_diff_records)
    expect("gap_actual_safetycost_available", gap.get("actual_safetycost_v1_available"), False)
    expect("gap_claim_rule_evaluable", gap.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    expect("gap_next_evidence_need", gap.get("next_evidence_need"), "paired shadow-selected run-level closed-loop outcome summaries")

    _expect_sha(checks, "nested_static_review_json_sha", nested_sha256s, review_json.name, review_json)
    _expect_sha(checks, "nested_static_review_md_sha", nested_sha256s, review_md.name, review_md)
    _expect_sha(checks, "root_static_review_json_sha", root_sha256s, f"./review/{review_json.name}", review_json)
    _expect_sha(checks, "root_static_review_md_sha", root_sha256s, f"./review/{review_md.name}", review_md)
    _expect_sha(checks, "root_static_review_sha256s_sha", root_sha256s, "./review/SHA256SUMS", review_sha256s)
    checks.extend(_preflight_contract_checks())
    return checks


def _preflight_contract_checks() -> list[dict[str, Any]]:
    return [
        {
            "name": "required_input_names",
            "passed": [item["name"] for item in _required_inputs({})] == list(EXPECTED_REQUIRED_INPUTS),
            "actual": [item["name"] for item in _required_inputs({})],
            "expected": list(EXPECTED_REQUIRED_INPUTS),
        },
        {
            "name": "preflight_plan_item_names",
            "passed": [item["name"] for item in _preflight_plan()] == list(EXPECTED_PREFLIGHT_ITEMS),
            "actual": [item["name"] for item in _preflight_plan()],
            "expected": list(EXPECTED_PREFLIGHT_ITEMS),
        },
        {
            "name": "preflight_plan_does_not_materialize_outcomes",
            "passed": sorted({item["materializes_outcomes"] for item in _preflight_plan()}) == [False],
            "actual": sorted({item["materializes_outcomes"] for item in _preflight_plan()}),
            "expected": [False],
        },
        {
            "name": "planned_output_names",
            "passed": [item["name"] for item in _planned_outputs()] == list(EXPECTED_PLANNED_OUTPUTS),
            "actual": [item["name"] for item in _planned_outputs()],
            "expected": list(EXPECTED_PLANNED_OUTPUTS),
        },
        {
            "name": "no_go_names",
            "passed": [item["name"] for item in _no_go_register()] == list(EXPECTED_NO_GO),
            "actual": [item["name"] for item in _no_go_register()],
            "expected": list(EXPECTED_NO_GO),
        },
    ]


def _required_inputs(source_review: dict[str, Any]) -> list[dict[str, Any]]:
    summary = _source_static_review_summary(source_review)
    return [
        {"name": "passed_actual_safetycost_evidence_gap_closure_plan_static_review_artifact", "requirement": "consume the passed static-review artifact and SHA256SUMS as immutable source evidence", "source_status": summary.get("status")},
        {"name": "fixed_dp_candidate_tensor_identity_manifest", "requirement": "candidate tensor identity must remain fixed to DP source candidates"},
        {"name": "paired_shadow_selected_run_key_manifest", "requirement": "shadow-selected run keys must match audited paired evaluation keys"},
        {"name": "closed_loop_outcome_materialization_execution_boundary", "requirement": "future materialization may execute only after preflight static review passes"},
        {"name": "outcome_storage_schema_and_hash_contract", "requirement": "future outcome summaries must be hashed, paired, immutable, and reviewable"},
        {"name": "no_training_or_online_input_leakage_guard", "requirement": "closed-loop outcomes are evaluation evidence only"},
        {"name": "safetycost_v1_claim_rule_config", "requirement": "SafetyCost v1, hard gates, and CI rules stay frozen before materialization"},
        {"name": "artifact_heads_command_stdout_stderr_contract", "requirement": "future artifacts must include JSON, MD, SHA256SUMS, HEADS, COMMAND, stdout, stderr, and run.exit"},
    ]


def _preflight_plan() -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "plan_only", "materializes_outcomes": False}
        for name in EXPECTED_PREFLIGHT_ITEMS
    ]


def _planned_outputs() -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "planned_not_materialized"}
        for name in EXPECTED_PLANNED_OUTPUTS
    ]


def _no_go_register() -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "predeclared_reject_condition"}
        for name in EXPECTED_NO_GO
    ]


def _source_static_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = HELPER_MODULE._dict(source_review.get("final_decision"))
    source_plan = HELPER_MODULE._dict(source_review.get("source_plan_summary"))
    return {
        "schema_version": source_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "static_review_check_count": len(_list(source_review.get("static_review_checks"))),
        "failed_check_count": len(_list(decision.get("failed_checks"))),
        "source_plan_check_count": source_plan.get("plan_check_count"),
        "source_paired_record_count": source_plan.get("paired_record_count"),
        "source_shadow_diff_records": source_plan.get("shadow_diff_records"),
    }


def _outcome_materialization_preflight_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    gap = HELPER_MODULE._dict(source_review.get("evidence_gap_closure_summary"))
    return {
        "actual_safetycost_v1_available": gap.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": gap.get("actual_safetycost_v1_claim_rule_evaluable"),
        "next_evidence_need": gap.get("next_evidence_need"),
        "planned_materialization_scope": "shadow-selected run-level closed-loop outcome summaries only",
        "closed_loop_outcomes_training_or_online_input": False,
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], source_review: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "outcome_materialization_preflight_plan_enabled" in failed:
        failure_class = "explicit_actual_safetycost_outcome_materialization_preflight_plan_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_review_") for name in failed):
        failure_class = "source_static_review_contract_failure"
    elif any(name.startswith(("source_", "gap_")) for name in failed):
        failure_class = "source_evidence_contract_failure"
    elif any(name.startswith(("nested_", "root_", "artifact_")) for name in failed):
        failure_class = "artifact_hash_contract_failure"
    else:
        failure_class = "outcome_materialization_preflight_plan_contract_failure"
    source_decision = HELPER_MODULE._dict(source_review.get("final_decision"))
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_outcome_materialization_preflight_plan_ready": bool(passed),
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_outcome_materialization_preflight_plan_static_review_authorized": bool(passed),
        "actual_safetycost_outcome_materialization_executed_by_this_gate": False,
        "paired_evaluation_executed_by_this_gate": False,
        "source_static_review_consumed_by_this_gate": True,
        "actual_safetycost_v1_available": source_decision.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": source_decision.get("actual_safetycost_v1_claim_rule_evaluable"),
        "closed_loop_outcome_training_or_online_input_authorized": False,
        "previous_no_promotion_closeout_preserved": True,
        "direct_promotion_recommendation": False,
        "recommendation": "static_review_actual_safetycost_outcome_materialization_preflight_plan_only" if passed else "repair_or_rerun_same_plan_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def _source_hashes(*, artifact_dir: Path, review_json: Path, review_md: Path, review_sha256s: Path) -> dict[str, Any]:
    return {
        "source_static_review_json_sha256": HELPER_MODULE._sha256(review_json),
        "source_static_review_md_sha256": HELPER_MODULE._sha256(review_md),
        "source_static_review_sha256s_sha256": HELPER_MODULE._sha256(review_sha256s),
        "source_static_review_root_sha256s_sha256": HELPER_MODULE._sha256(artifact_dir / "SHA256SUMS"),
        "heads_sha256": HELPER_MODULE._sha256(artifact_dir / "HEADS"),
        "command_sha256": HELPER_MODULE._sha256(artifact_dir / "COMMAND"),
        "stdout_sha256": HELPER_MODULE._sha256(artifact_dir / "stdout"),
        "stderr_sha256": HELPER_MODULE._sha256(artifact_dir / "stderr"),
        "run_exit_sha256": HELPER_MODULE._sha256(artifact_dir / "run.exit"),
    }


def _expect_sha(
    checks: list[dict[str, Any]],
    name: str,
    sums: dict[str, str],
    key: str,
    path: Path,
) -> None:
    actual = sums.get(key) or sums.get(key.removeprefix("./")) or sums.get(f"./{key}")
    expected = HELPER_MODULE._sha256(path) if path.is_file() else None
    checks.append({"name": name, "passed": actual == expected, "actual": actual, "expected": expected})


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PLAN_JSON_NAME
    md_path = output_dir / PLAN_MD_NAME
    json_path.write_text(
        json.dumps(HELPER_MODULE._stable(report), indent=2) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")
    sums = [f"{HELPER_MODULE._sha256(path)}  {path.name}" for path in (json_path, md_path)]
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_static_review_summary"]
    preflight = report["outcome_materialization_preflight_summary"]
    lines = [
        "# v14 Actual-SafetyCost Outcome-Materialization Preflight Plan",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Static Review",
        "",
        f"- Static-review checks: `{summary['static_review_check_count']}`",
        f"- Failed checks: `{summary['failed_check_count']}`",
        f"- Source paired records: `{summary['source_paired_record_count']}`",
        f"- Source shadow differs from Top-1 records: `{summary['source_shadow_diff_records']}`",
        "",
        "## Preflight Scope",
        "",
        f"- Actual SafetyCost v1 available: `{preflight['actual_safetycost_v1_available']}`",
        f"- Claim rule evaluable: `{preflight['actual_safetycost_v1_claim_rule_evaluable']}`",
        f"- Planned materialization scope: `{preflight['planned_materialization_scope']}`",
        f"- Closed-loop outcomes used for training or online input: `{preflight['closed_loop_outcomes_training_or_online_input']}`",
        "",
        "## Boundary",
        "",
        "- Plan only: no outcome materialization, replay, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
        f"- Score expression: `{report['analysis']['score_expression']}`",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
