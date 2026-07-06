#!/usr/bin/env python3
"""Preflight candidate-index SafetyCost delta materialization without running it."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_source_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_candidate_index_"
        "actual_safetycost_delta_materialization_preflight_plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_delta_materialization_preflight_plan_static_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_source_review_module()
PLAN_MODULE = SOURCE_REVIEW_MODULE.PLAN_MODULE
HELPER_MODULE = SOURCE_REVIEW_MODULE.HELPER_MODULE

FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_REVIEW_SCHEMA = SOURCE_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_STATUS = SOURCE_REVIEW_MODULE.READY_STATUS
SOURCE_REVIEW_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
SOURCE_PLAN_SCHEMA = SOURCE_REVIEW_MODULE.SOURCE_PLAN_SCHEMA
SOURCE_PLAN_STATUS = SOURCE_REVIEW_MODULE.SOURCE_PLAN_STATUS
SOURCE_PLAN_JSON_NAME = SOURCE_REVIEW_MODULE.SOURCE_PLAN_JSON_NAME
SOURCE_PLAN_MD_NAME = SOURCE_REVIEW_MODULE.SOURCE_PLAN_MD_NAME
BLOCKED_ACTIONS = SOURCE_REVIEW_MODULE.BLOCKED_ACTIONS
OBJECTIVE_REQUIRED_RECORDS = SOURCE_REVIEW_MODULE.OBJECTIVE_REQUIRED_RECORDS
EXPECTED_SELECTION_LOG_COUNT = SOURCE_REVIEW_MODULE.EXPECTED_SELECTION_LOG_COUNT

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_preflight_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_preflight_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_preflight_static_review_only"
)

PREFLIGHT_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_preflight.json"
)
PREFLIGHT_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_preflight.md"
)

EXPECTED_MATERIALIZATION_INPUTS = (
    "passed_delta_materialization_preflight_plan_static_review_artifact",
    "source_delta_materialization_preflight_plan_artifact",
    "locked_candidate_index_closed_loop_outcome_manifest",
    "locked_dp_top1_closed_loop_outcome_reference_manifest",
    "fixed_dp_candidate_tensor_identity_manifest",
    "paired_run_key_index",
    "safetycost_v1_metric_spec",
    "delta_table_schema_and_statistics_contract",
    "ci95_bootstrap_and_claim_rule_contract",
    "offline_evaluation_only_outcome_boundary",
    "artifact_hash_heads_command_stdout_stderr_contract",
)
EXPECTED_PREFLIGHT_STEPS = (
    "lock_static_review_and_plan_artifacts",
    "verify_fixed_dp_head_and_source_hashes",
    "verify_3200_paired_candidate_and_top1_outcome_coverage",
    "verify_candidate_tensor_identity_and_shadow_selection_binding",
    "freeze_safetycost_v1_formula_and_delta_schema",
    "freeze_ci95_bootstrap_and_claim_rule_fields",
    "verify_no_training_online_input_promotion_deployment_or_claim",
    "emit_static_reviewable_delta_materialization_preflight_artifact",
)
EXPECTED_FUTURE_OUTPUTS = (
    "actual_safetycost_v1_delta_table",
    "paired_delta_summary_statistics",
    "win_tie_loss_summary",
    "ci95_bootstrap_summary",
    "claim_rule_evaluation_fields",
    "leakage_and_forbidden_action_no_go_register",
)
EXPECTED_NO_GO = PLAN_MODULE.EXPECTED_NO_GO


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_md", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_preflight_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_plan_json", type=Path, required=True)
    parser.add_argument("--source_preflight_plan_md", type=Path, required=True)
    parser.add_argument("--source_preflight_plan_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_record_count", type=int, default=OBJECTIVE_REQUIRED_RECORDS)
    parser.add_argument("--expected_selection_log_count", type=int, default=EXPECTED_SELECTION_LOG_COUNT)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight",
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
        source_preflight_plan_artifact_dir=args.source_preflight_plan_artifact_dir,
        source_preflight_plan_json=args.source_preflight_plan_json,
        source_preflight_plan_md=args.source_preflight_plan_md,
        source_preflight_plan_sha256s=args.source_preflight_plan_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_record_count=args.expected_record_count,
        expected_selection_log_count=args.expected_selection_log_count,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight
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
    source_preflight_plan_artifact_dir: Path,
    source_preflight_plan_json: Path,
    source_preflight_plan_md: Path,
    source_preflight_plan_sha256s: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_record_count: int = OBJECTIVE_REQUIRED_RECORDS,
    expected_selection_log_count: int = EXPECTED_SELECTION_LOG_COUNT,
    enabled: bool = False,
) -> dict[str, Any]:
    review_artifact_dir = source_static_review_artifact_dir.resolve()
    plan_artifact_dir = source_preflight_plan_artifact_dir.resolve()
    paths = {
        "source_static_review_json": source_static_review_json.resolve(),
        "source_static_review_md": source_static_review_md.resolve(),
        "source_static_review_sha256s": source_static_review_sha256s.resolve(),
        "source_preflight_plan_json": source_preflight_plan_json.resolve(),
        "source_preflight_plan_md": source_preflight_plan_md.resolve(),
        "source_preflight_plan_sha256s": source_preflight_plan_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    review_files = _artifact_files(review_artifact_dir)
    plan_files = _artifact_files(plan_artifact_dir)
    source_review = HELPER_MODULE._read_json_dict(paths["source_static_review_json"])
    source_plan = HELPER_MODULE._read_json_dict(paths["source_preflight_plan_json"])
    v14_text = HELPER_MODULE._read_text(paths["v14_audit_md"])
    status_text = HELPER_MODULE._read_text(paths["current_status_md"])
    review_heads = HELPER_MODULE._parse_key_values(HELPER_MODULE._read_text(review_files["heads"]))
    plan_heads = HELPER_MODULE._parse_key_values(HELPER_MODULE._read_text(plan_files["heads"]))
    review_run_exit = HELPER_MODULE._read_text(review_files["run_exit"]).strip()
    plan_run_exit = HELPER_MODULE._read_text(plan_files["run_exit"]).strip()
    review_root_sha256s = HELPER_MODULE._read_sha256sums(review_files["root_sha256s"])
    review_nested_sha256s = HELPER_MODULE._read_sha256sums(paths["source_static_review_sha256s"])
    plan_root_sha256s = HELPER_MODULE._read_sha256sums(plan_files["root_sha256s"])
    plan_nested_sha256s = HELPER_MODULE._read_sha256sums(paths["source_preflight_plan_sha256s"])
    materialization_inputs = _materialization_inputs(source_review, source_plan)
    preflight_steps = _preflight_steps()
    future_outputs = _future_outputs()
    no_go = _no_go_register()
    checks = _checks(
        enabled=enabled,
        review_artifact_dir=review_artifact_dir,
        plan_artifact_dir=plan_artifact_dir,
        paths=paths,
        review_files=review_files,
        plan_files=plan_files,
        source_review=source_review,
        source_plan=source_plan,
        v14_text=v14_text,
        status_text=status_text,
        review_heads=review_heads,
        plan_heads=plan_heads,
        review_run_exit=review_run_exit,
        plan_run_exit=plan_run_exit,
        review_root_sha256s=review_root_sha256s,
        review_nested_sha256s=review_nested_sha256s,
        plan_root_sha256s=plan_root_sha256s,
        plan_nested_sha256s=plan_nested_sha256s,
        materialization_inputs=materialization_inputs,
        preflight_steps=preflight_steps,
        future_outputs=future_outputs,
        no_go=no_go,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_record_count=expected_record_count,
        expected_selection_log_count=expected_selection_log_count,
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "preflight_only": True,
            "read_only": True,
            "candidate_index_actual_safetycost_delta_materialization_preflight_only": True,
            "actual_safetycost_delta_materialization_execution": False,
            "candidate_index_replay_execution": False,
            "outcome_acquisition_execution": False,
            "training_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "candidate_tensor_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "source_static_review_artifact_dir": str(review_artifact_dir),
            "source_static_review_json": str(paths["source_static_review_json"]),
            "source_static_review_md": str(paths["source_static_review_md"]),
            "source_static_review_sha256s": str(paths["source_static_review_sha256s"]),
            "source_preflight_plan_artifact_dir": str(plan_artifact_dir),
            "source_preflight_plan_json": str(paths["source_preflight_plan_json"]),
            "source_preflight_plan_md": str(paths["source_preflight_plan_md"]),
            "source_preflight_plan_sha256s": str(paths["source_preflight_plan_sha256s"]),
            "v14_audit_md": str(paths["v14_audit_md"]),
            "current_status_md": str(paths["current_status_md"]),
            "output_dir": str(output_dir.resolve()),
        },
        "source_artifact_hashes": _source_hashes(
            review_files=review_files,
            plan_files=plan_files,
            paths=paths,
        ),
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_review_camp_head": HELPER_MODULE._kv(review_heads, "CAMP_HEAD", "camp_head"),
            "source_review_camp_origin_main": HELPER_MODULE._kv(review_heads, "CAMP_ORIGIN_MAIN", "camp_origin_main"),
            "source_review_dp_head": HELPER_MODULE._kv(review_heads, "DP_HEAD", "dp_head"),
            "source_plan_camp_head": HELPER_MODULE._kv(plan_heads, "CAMP_HEAD", "camp_head"),
            "source_plan_camp_origin_main": HELPER_MODULE._kv(plan_heads, "CAMP_ORIGIN_MAIN", "camp_origin_main"),
            "source_plan_dp_head": HELPER_MODULE._kv(plan_heads, "DP_HEAD", "dp_head"),
        },
        "source_static_review_summary": _source_static_review_summary(source_review),
        "source_plan_summary": _source_plan_summary(source_plan),
        "delta_materialization_preflight_summary": _delta_materialization_preflight_summary(source_review, source_plan),
        "materialization_inputs": materialization_inputs,
        "preflight_steps": preflight_steps,
        "future_outputs": future_outputs,
        "no_go_register": no_go,
        "preflight_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, source_review=source_review),
    }


def _checks(
    *,
    enabled: bool,
    review_artifact_dir: Path,
    plan_artifact_dir: Path,
    paths: dict[str, Path],
    review_files: dict[str, Path],
    plan_files: dict[str, Path],
    source_review: dict[str, Any],
    source_plan: dict[str, Any],
    v14_text: str,
    status_text: str,
    review_heads: dict[str, str],
    plan_heads: dict[str, str],
    review_run_exit: str,
    plan_run_exit: str,
    review_root_sha256s: dict[str, str],
    review_nested_sha256s: dict[str, str],
    plan_root_sha256s: dict[str, str],
    plan_nested_sha256s: dict[str, str],
    materialization_inputs: list[dict[str, Any]],
    preflight_steps: list[dict[str, Any]],
    future_outputs: list[dict[str, Any]],
    no_go: list[dict[str, Any]],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_record_count: int,
    expected_selection_log_count: int,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    review_decision = HELPER_MODULE._dict(source_review.get("final_decision"))
    plan_decision = HELPER_MODULE._dict(source_plan.get("final_decision"))
    review_source_plan_summary = HELPER_MODULE._dict(source_review.get("source_plan_summary"))
    plan_source_review_summary = HELPER_MODULE._dict(source_plan.get("source_static_review_summary"))
    delta_summary = HELPER_MODULE._dict(source_review.get("delta_materialization_preflight_summary"))

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

    require("delta_materialization_preflight_enabled", enabled)
    require("source_static_review_artifact_dir_exists", review_artifact_dir.is_dir())
    require("source_preflight_plan_artifact_dir_exists", plan_artifact_dir.is_dir())
    for name, path in paths.items():
        require(f"{name}_exists", path.is_file(), str(path), "file")
    for name, path in review_files.items():
        require(f"source_static_review_artifact_{name}_exists", path.is_file(), str(path), "file")
    for name, path in plan_files.items():
        require(f"source_plan_artifact_{name}_exists", path.is_file(), str(path), "file")

    expect("current_dp_head_fixed", current_dp_head, required_dp_head)
    expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD)
    expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main)
    expect("source_review_artifact_dp_head_fixed", HELPER_MODULE._kv(review_heads, "DP_HEAD", "dp_head"), required_dp_head)
    expect("source_plan_artifact_dp_head_fixed", HELPER_MODULE._kv(plan_heads, "DP_HEAD", "dp_head"), required_dp_head)
    expect(
        "source_review_artifact_camp_matches_origin",
        HELPER_MODULE._kv(review_heads, "CAMP_HEAD", "camp_head"),
        HELPER_MODULE._kv(review_heads, "CAMP_ORIGIN_MAIN", "camp_origin_main"),
    )
    expect(
        "source_plan_artifact_camp_matches_origin",
        HELPER_MODULE._kv(plan_heads, "CAMP_HEAD", "camp_head"),
        HELPER_MODULE._kv(plan_heads, "CAMP_ORIGIN_MAIN", "camp_origin_main"),
    )
    expect("source_static_review_run_exit", review_run_exit, "0")
    expect("source_preflight_plan_run_exit", plan_run_exit, "0")
    expect("audit_latest_status", HELPER_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_REVIEW_STATUS)
    expect("audit_latest_next_work", HELPER_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK)
    expect("status_doc_latest_status", HELPER_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_REVIEW_STATUS)
    expect("status_doc_latest_next_work", HELPER_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK)

    expect("source_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA)
    expect("source_review_passed", review_decision.get("passed"), True)
    expect("source_review_status", review_decision.get("status"), SOURCE_REVIEW_STATUS)
    expect("source_review_failed_checks", review_decision.get("failed_checks"), [])
    expect("source_review_authorized_next_work", review_decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK)
    expect(
        "source_review_static_review_passed",
        review_decision.get("objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_plan_static_review_passed"),
        True,
    )
    expect(
        "source_review_preflight_authorized",
        review_decision.get("objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_authorized"),
        True,
    )
    expect("source_review_no_delta_materialization", review_decision.get("actual_safetycost_delta_materialization_executed_by_this_gate"), False)
    expect("source_review_no_candidate_index_replay", review_decision.get("candidate_index_replay_executed_by_this_gate"), False)
    expect("source_review_no_outcome_acquisition", review_decision.get("outcome_acquisition_executed_by_this_gate"), False)
    expect("source_review_actual_safetycost_available", review_decision.get("actual_safetycost_v1_available"), False)
    expect("source_review_claim_rule_evaluable", review_decision.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    for action in BLOCKED_ACTIONS:
        expect(f"source_review_decision_{action}", review_decision.get(action), False)
    expect("source_review_check_count", review_decision.get("check_count"), 68)
    expect("source_review_failed_check_count", review_decision.get("failed_check_count"), 0)

    expect("source_plan_schema", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA)
    expect("source_plan_passed", plan_decision.get("passed"), True)
    expect("source_plan_status", plan_decision.get("status"), SOURCE_PLAN_STATUS)
    expect("source_plan_failed_checks", plan_decision.get("failed_checks"), [])
    expect("source_plan_authorized_next_work", plan_decision.get("authorized_next_work"), SOURCE_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK)
    expect("source_plan_check_count", plan_decision.get("check_count"), 66)
    expect("source_plan_failed_check_count", plan_decision.get("failed_check_count"), 0)

    for prefix, summary in (
        ("source_review", review_source_plan_summary),
        ("source_plan", plan_source_review_summary),
    ):
        expect(f"{prefix}_objective_required_records", summary.get("objective_required_records"), expected_record_count)
        expect(f"{prefix}_paired_record_key_count", summary.get("paired_record_key_count"), expected_record_count)
        expect(f"{prefix}_candidate_closed_loop_outcome_records", summary.get("candidate_closed_loop_outcome_records"), expected_record_count)
        expect(f"{prefix}_missing_candidate_closed_loop_outcome_records", summary.get("missing_candidate_closed_loop_outcome_records"), 0)
        expect(f"{prefix}_selection_log_count", summary.get("selection_log_count"), expected_selection_log_count)
        expect(f"{prefix}_no_go_failed_count", summary.get("no_go_failed_count"), 0)

    expect("delta_summary_actual_safetycost_available", delta_summary.get("actual_safetycost_v1_available"), False)
    expect("delta_summary_claim_rule_evaluable", delta_summary.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    expect("delta_summary_materialization_executed", delta_summary.get("delta_materialization_executed_by_this_gate"), False)
    expect("delta_summary_claim_supported", delta_summary.get("claim_supported_by_this_plan"), False)
    expect("delta_summary_promotion_supported", delta_summary.get("promotion_supported_by_this_plan"), False)

    _expect_sha(checks, "nested_static_review_json_sha", review_nested_sha256s, SOURCE_REVIEW_JSON_NAME, paths["source_static_review_json"])
    _expect_sha(checks, "nested_static_review_md_sha", review_nested_sha256s, SOURCE_REVIEW_MD_NAME, paths["source_static_review_md"])
    _expect_sha(checks, "root_static_review_json_sha", review_root_sha256s, f"review/{SOURCE_REVIEW_JSON_NAME}", paths["source_static_review_json"])
    _expect_sha(checks, "root_static_review_md_sha", review_root_sha256s, f"review/{SOURCE_REVIEW_MD_NAME}", paths["source_static_review_md"])
    _expect_sha(checks, "root_static_review_sha256s_sha", review_root_sha256s, "review/SHA256SUMS", paths["source_static_review_sha256s"])
    for key, path in review_files.items():
        if key != "root_sha256s":
            _expect_sha(checks, f"root_static_review_{key}_sha", review_root_sha256s, path.name, path)

    _expect_sha(checks, "nested_source_plan_json_sha", plan_nested_sha256s, SOURCE_PLAN_JSON_NAME, paths["source_preflight_plan_json"])
    _expect_sha(checks, "nested_source_plan_md_sha", plan_nested_sha256s, SOURCE_PLAN_MD_NAME, paths["source_preflight_plan_md"])
    _expect_sha(checks, "root_source_plan_json_sha", plan_root_sha256s, f"plan/{SOURCE_PLAN_JSON_NAME}", paths["source_preflight_plan_json"])
    _expect_sha(checks, "root_source_plan_md_sha", plan_root_sha256s, f"plan/{SOURCE_PLAN_MD_NAME}", paths["source_preflight_plan_md"])
    _expect_sha(checks, "root_source_plan_sha256s_sha", plan_root_sha256s, "plan/SHA256SUMS", paths["source_preflight_plan_sha256s"])
    for key, path in plan_files.items():
        if key != "root_sha256s":
            _expect_sha(checks, f"root_source_plan_{key}_sha", plan_root_sha256s, path.name, path)

    checks.extend(_preflight_contract_checks(materialization_inputs, preflight_steps, future_outputs, no_go))
    return checks


def _preflight_contract_checks(
    materialization_inputs: list[dict[str, Any]],
    preflight_steps: list[dict[str, Any]],
    future_outputs: list[dict[str, Any]],
    no_go: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "name": "materialization_input_names",
            "passed": [item["name"] for item in materialization_inputs] == list(EXPECTED_MATERIALIZATION_INPUTS),
            "actual": [item["name"] for item in materialization_inputs],
            "expected": list(EXPECTED_MATERIALIZATION_INPUTS),
        },
        {
            "name": "preflight_step_names",
            "passed": [item["name"] for item in preflight_steps] == list(EXPECTED_PREFLIGHT_STEPS),
            "actual": [item["name"] for item in preflight_steps],
            "expected": list(EXPECTED_PREFLIGHT_STEPS),
        },
        {
            "name": "preflight_steps_do_not_materialize_deltas",
            "passed": sorted({item["materializes_safetycost_deltas"] for item in preflight_steps}) == [False],
            "actual": sorted({item["materializes_safetycost_deltas"] for item in preflight_steps}),
            "expected": [False],
        },
        {
            "name": "future_output_names",
            "passed": [item["name"] for item in future_outputs] == list(EXPECTED_FUTURE_OUTPUTS),
            "actual": [item["name"] for item in future_outputs],
            "expected": list(EXPECTED_FUTURE_OUTPUTS),
        },
        {
            "name": "no_go_names",
            "passed": [item["name"] for item in no_go] == list(EXPECTED_NO_GO),
            "actual": [item["name"] for item in no_go],
            "expected": list(EXPECTED_NO_GO),
        },
    ]


def _materialization_inputs(source_review: dict[str, Any], source_plan: dict[str, Any]) -> list[dict[str, Any]]:
    review_summary = _source_static_review_summary(source_review)
    plan_summary = _source_plan_summary(source_plan)
    return [
        {
            "name": name,
            "status": "locked_for_static_review",
            "materializes_safetycost_deltas": False,
            "source_status": review_summary.get("status") if index == 0 else plan_summary.get("status") if index == 1 else None,
        }
        for index, name in enumerate(EXPECTED_MATERIALIZATION_INPUTS)
    ]


def _preflight_steps() -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "preflight_checked", "materializes_safetycost_deltas": False}
        for name in EXPECTED_PREFLIGHT_STEPS
    ]


def _future_outputs() -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "future_output_not_materialized"}
        for name in EXPECTED_FUTURE_OUTPUTS
    ]


def _no_go_register() -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "predeclared_reject_condition"}
        for name in EXPECTED_NO_GO
    ]


def _source_static_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = HELPER_MODULE._dict(source_review.get("final_decision"))
    summary = HELPER_MODULE._dict(source_review.get("source_plan_summary"))
    return {
        "schema_version": source_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "check_count": decision.get("check_count"),
        "failed_check_count": decision.get("failed_check_count"),
        "objective_required_records": summary.get("objective_required_records"),
        "paired_record_key_count": summary.get("paired_record_key_count"),
        "candidate_closed_loop_outcome_records": summary.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": summary.get("missing_candidate_closed_loop_outcome_records"),
        "selection_log_count": summary.get("selection_log_count"),
        "no_go_failed_count": summary.get("no_go_failed_count"),
    }


def _source_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = HELPER_MODULE._dict(source_plan.get("final_decision"))
    summary = HELPER_MODULE._dict(source_plan.get("source_static_review_summary"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "check_count": decision.get("check_count"),
        "failed_check_count": decision.get("failed_check_count"),
        "objective_required_records": summary.get("objective_required_records"),
        "paired_record_key_count": summary.get("paired_record_key_count"),
        "candidate_closed_loop_outcome_records": summary.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": summary.get("missing_candidate_closed_loop_outcome_records"),
        "selection_log_count": summary.get("selection_log_count"),
        "no_go_failed_count": summary.get("no_go_failed_count"),
    }


def _delta_materialization_preflight_summary(source_review: dict[str, Any], source_plan: dict[str, Any]) -> dict[str, Any]:
    review_delta = HELPER_MODULE._dict(source_review.get("delta_materialization_preflight_summary"))
    plan_delta = HELPER_MODULE._dict(source_plan.get("delta_materialization_preflight_summary"))
    return {
        "actual_safetycost_v1_available": review_delta.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": review_delta.get("actual_safetycost_v1_claim_rule_evaluable"),
        "next_evidence_need": review_delta.get("next_evidence_need"),
        "planned_resolution": review_delta.get("planned_resolution"),
        "source_plan_next_evidence_need": plan_delta.get("next_evidence_need"),
        "delta_materialization_preflight_executed_by_this_gate": True,
        "delta_materialization_executed_by_this_gate": False,
        "candidate_index_replay_executed_by_this_gate": False,
        "outcome_acquisition_executed_by_this_gate": False,
        "claim_supported_by_this_preflight": False,
        "promotion_supported_by_this_preflight": False,
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], source_review: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "delta_materialization_preflight_enabled" in failed:
        failure_class = "explicit_candidate_index_delta_materialization_preflight_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_review_") for name in failed):
        failure_class = "source_plan_static_review_contract_failure"
    elif any(name.startswith("source_plan_") for name in failed):
        failure_class = "source_delta_materialization_plan_contract_failure"
    elif any(name.startswith(("nested_", "root_")) for name in failed):
        failure_class = "artifact_hash_contract_failure"
    else:
        failure_class = "candidate_index_delta_materialization_preflight_contract_failure"
    source_decision = HELPER_MODULE._dict(source_review.get("final_decision"))
    summary = HELPER_MODULE._dict(source_review.get("source_plan_summary"))
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_ready": bool(passed),
        "objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_static_review_authorized": bool(passed),
        "source_static_review_consumed_by_this_gate": True,
        "source_preflight_plan_consumed_by_this_gate": True,
        "actual_safetycost_delta_materialization_preflight_executed_by_this_gate": bool(passed),
        "actual_safetycost_delta_materialization_execution_authorized": False,
        "actual_safetycost_delta_materialization_executed_by_this_gate": False,
        "candidate_index_replay_executed_by_this_gate": False,
        "outcome_acquisition_executed_by_this_gate": False,
        "actual_safetycost_v1_available": source_decision.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": source_decision.get("actual_safetycost_v1_claim_rule_evaluable"),
        "objective_required_records": summary.get("objective_required_records"),
        "paired_record_key_count": summary.get("paired_record_key_count"),
        "candidate_closed_loop_outcome_records": summary.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": summary.get("missing_candidate_closed_loop_outcome_records"),
        "selection_log_count": summary.get("selection_log_count"),
        "no_go_failed_count": summary.get("no_go_failed_count"),
        "closed_loop_outcome_training_or_online_input_authorized": False,
        "claim_supported_by_this_preflight": False,
        "promotion_supported_by_this_preflight": False,
        "direct_promotion_recommendation": False,
        "recommendation": "static_review_candidate_index_actual_safetycost_delta_materialization_preflight_only" if passed else "repair_or_rerun_same_preflight_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    decision.update({name: False for name in BLOCKED_ACTIONS})
    return decision


def _artifact_files(artifact_dir: Path) -> dict[str, Path]:
    return {
        "heads": artifact_dir / "HEADS",
        "command": artifact_dir / "COMMAND",
        "stdout": artifact_dir / "stdout",
        "stderr": artifact_dir / "stderr",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
    }


def _source_hashes(
    *,
    review_files: dict[str, Path],
    plan_files: dict[str, Path],
    paths: dict[str, Path],
) -> dict[str, str | None]:
    return {
        "source_static_review_json": HELPER_MODULE._sha256(paths["source_static_review_json"]),
        "source_static_review_md": HELPER_MODULE._sha256(paths["source_static_review_md"]),
        "source_static_review_sha256s": HELPER_MODULE._sha256(paths["source_static_review_sha256s"]),
        "source_static_review_root_sha256s": HELPER_MODULE._sha256(review_files["root_sha256s"]),
        "source_static_review_heads": HELPER_MODULE._sha256(review_files["heads"]),
        "source_static_review_command": HELPER_MODULE._sha256(review_files["command"]),
        "source_static_review_stdout": HELPER_MODULE._sha256(review_files["stdout"]),
        "source_static_review_stderr": HELPER_MODULE._sha256(review_files["stderr"]),
        "source_static_review_run_exit": HELPER_MODULE._sha256(review_files["run_exit"]),
        "source_preflight_plan_json": HELPER_MODULE._sha256(paths["source_preflight_plan_json"]),
        "source_preflight_plan_md": HELPER_MODULE._sha256(paths["source_preflight_plan_md"]),
        "source_preflight_plan_sha256s": HELPER_MODULE._sha256(paths["source_preflight_plan_sha256s"]),
        "source_preflight_plan_root_sha256s": HELPER_MODULE._sha256(plan_files["root_sha256s"]),
        "source_preflight_plan_heads": HELPER_MODULE._sha256(plan_files["heads"]),
        "source_preflight_plan_command": HELPER_MODULE._sha256(plan_files["command"]),
        "source_preflight_plan_stdout": HELPER_MODULE._sha256(plan_files["stdout"]),
        "source_preflight_plan_stderr": HELPER_MODULE._sha256(plan_files["stderr"]),
        "source_preflight_plan_run_exit": HELPER_MODULE._sha256(plan_files["run_exit"]),
    }


def _expect_sha(
    checks: list[dict[str, Any]],
    name: str,
    sums: dict[str, str],
    suffix: str,
    path: Path,
) -> None:
    actual = HELPER_MODULE._sha_for_suffix(sums, suffix)
    expected = HELPER_MODULE._sha256(path) if path.is_file() else None
    checks.append({"name": name, "passed": actual == expected, "actual": actual, "expected": expected})


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PREFLIGHT_JSON_NAME
    md_path = output_dir / PREFLIGHT_MD_NAME
    json_path.write_text(
        json.dumps(HELPER_MODULE._stable(report), indent=2) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")
    sums = [f"{HELPER_MODULE._sha256(path)}  {path.name}" for path in (json_path, md_path)]
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["source_static_review_summary"]
    delta = report["delta_materialization_preflight_summary"]
    lines = [
        "# Objective-3200 Candidate-Index Actual-SafetyCost Delta Materialization Preflight",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failure class: `{decision['failure_class']}`",
        f"- Checks / failed checks: `{decision['check_count']} / {decision['failed_check_count']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Static Review",
        "",
        f"- Static-review checks / failed checks: `{review['check_count']} / {review['failed_check_count']}`",
        f"- Objective records / paired keys: `{review['objective_required_records']} / {review['paired_record_key_count']}`",
        f"- Candidate outcomes / missing: `{review['candidate_closed_loop_outcome_records']} / {review['missing_candidate_closed_loop_outcome_records']}`",
        f"- Selection logs / no-go failed count: `{review['selection_log_count']} / {review['no_go_failed_count']}`",
        "",
        "## Delta Materialization Preflight",
        "",
        f"- Actual SafetyCost_v1 available: `{delta['actual_safetycost_v1_available']}`",
        f"- Claim rule evaluable: `{delta['actual_safetycost_v1_claim_rule_evaluable']}`",
        f"- Next evidence need: `{delta['next_evidence_need']}`",
        f"- Planned resolution: `{delta['planned_resolution']}`",
        f"- Delta materialization executed by this gate: `{delta['delta_materialization_executed_by_this_gate']}`",
        "",
        "## Boundary",
        "",
        "- Preflight only: no SafetyCost delta materialization, replay, outcome acquisition, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
        f"- Score expression: `{report['analysis']['score_expression']}`",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
