#!/usr/bin/env python3
"""Plan candidate-index actual-SafetyCost evidence-gap closure.

This gate is read-only and plan-only. It consumes the audited objective-3200
candidate-index outcome-acquisition execution result review and preregisters
how a future gate may materialize SafetyCost_v1 paired deltas. It does not
materialize deltas, run replay, train, generate candidates, modify Diffusion
Planner, promote, deploy, enable an online selector, or make claims.
"""

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
        "replay_outcome_acquisition_execution_result.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_replay_outcome_acquisition_execution_result_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_source_review_module()

FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_REVIEW_SCHEMA = SOURCE_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_STATUS = SOURCE_REVIEW_MODULE.READY_STATUS
SOURCE_REVIEW_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
OBJECTIVE_REQUIRED_RECORDS = SOURCE_REVIEW_MODULE.OBJECTIVE_REQUIRED_RECORDS
EXPECTED_SELECTION_LOG_COUNT = SOURCE_REVIEW_MODULE.EXPECTED_SELECTION_LOG_COUNT
BLOCKED_ACTIONS = SOURCE_REVIEW_MODULE.BLOCKED_ACTIONS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_actual_safetycost_evidence_gap_closure_plan_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_evidence_gap_closure_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_evidence_gap_closure_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_evidence_gap_closure_plan_static_review_only"
)

PLAN_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_evidence_gap_closure_plan.json"
)
PLAN_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_evidence_gap_closure_plan.md"
)

EXPECTED_REQUIRED_INPUTS = (
    "passed_candidate_index_execution_result_review_artifact",
    "paired_candidate_index_closed_loop_outcome_manifest",
    "dp_top1_closed_loop_outcome_reference_manifest",
    "fixed_dp_candidate_tensor_identity_manifest",
    "paired_run_key_index",
    "safetycost_v1_metric_and_claim_rule_spec",
    "offline_evaluation_only_outcome_boundary",
    "artifact_hash_heads_command_stdout_stderr_contract",
)
EXPECTED_PLAN_ITEMS = (
    "lock_result_review_artifact_and_hashes",
    "freeze_safetycost_v1_metric_spec",
    "resolve_dp_top1_baseline_outcome_reference_manifest",
    "join_candidate_index_and_dp_top1_outcomes_by_paired_key",
    "predeclare_safetycost_v1_delta_table_schema",
    "predeclare_confidence_interval_and_bootstrap_protocol",
    "enforce_no_training_online_selector_or_candidate_mutation",
    "emit_static_reviewable_materialization_preflight_contract",
)
EXPECTED_PLANNED_OUTPUTS = (
    "actual_safetycost_v1_metric_spec",
    "paired_outcome_join_manifest",
    "safetycost_v1_delta_table_schema",
    "confidence_interval_and_bootstrap_protocol",
    "claim_rule_evaluation_plan",
    "materialization_preflight_artifact_contract",
)
EXPECTED_NO_GO = (
    "source_result_review_missing_or_failed",
    "dp_head_drift",
    "candidate_index_closed_loop_outcomes_missing",
    "dp_top1_baseline_outcomes_missing_or_unlocked",
    "unmatched_paired_run_keys",
    "candidate_tensor_identity_missing_or_mutated",
    "camp_generates_repairs_rewrites_or_blends_trajectory",
    "dp_code_config_weight_or_checkpoint_modified",
    "full36_or_formal_seed_11_12_13_present",
    "closed_loop_outcome_used_for_training_or_online_input",
    "non_affine_score_or_non_simplex_weight",
    "promotion_deployment_online_selector_or_claim",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_result_review_json", type=Path, required=True)
    parser.add_argument("--source_result_review_md", type=Path, required=True)
    parser.add_argument("--source_result_review_sha256s", type=Path, required=True)
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
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_evidence_gap_closure_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_result_review_artifact_dir=args.source_result_review_artifact_dir,
        source_result_review_json=args.source_result_review_json,
        source_result_review_md=args.source_result_review_md,
        source_result_review_sha256s=args.source_result_review_sha256s,
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
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_evidence_gap_closure_plan
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(SOURCE_REVIEW_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_result_review_artifact_dir: Path,
    source_result_review_json: Path,
    source_result_review_md: Path,
    source_result_review_sha256s: Path,
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
    artifact_dir = source_result_review_artifact_dir.resolve()
    paths = {
        "source_result_review_json": source_result_review_json.resolve(),
        "source_result_review_md": source_result_review_md.resolve(),
        "source_result_review_sha256s": source_result_review_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    files = {
        "heads": artifact_dir / "HEADS",
        "command": artifact_dir / "COMMAND",
        "stdout": artifact_dir / "stdout",
        "stderr": artifact_dir / "stderr",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
    }
    source_review = SOURCE_REVIEW_MODULE._read_json_dict(paths["source_result_review_json"])
    v14_text = SOURCE_REVIEW_MODULE._read_text(paths["v14_audit_md"])
    status_text = SOURCE_REVIEW_MODULE._read_text(paths["current_status_md"])
    heads = SOURCE_REVIEW_MODULE._parse_key_values(SOURCE_REVIEW_MODULE._read_text(files["heads"]))
    root_sha256s = SOURCE_REVIEW_MODULE._read_sha256sums(files["root_sha256s"])
    nested_sha256s = SOURCE_REVIEW_MODULE._read_sha256sums(paths["source_result_review_sha256s"])
    run_exit = SOURCE_REVIEW_MODULE._read_text(files["run_exit"]).strip()
    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        paths=paths,
        files=files,
        source_review=source_review,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        run_exit=run_exit,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_record_count=expected_record_count,
        expected_selection_log_count=expected_selection_log_count,
    )
    passed = all(check["passed"] for check in checks)
    decision = _decision(passed=passed, checks=checks, source_review=source_review)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
            "read_only": True,
            "candidate_index_actual_safetycost_evidence_gap_closure_plan_only": True,
            "actual_safetycost_delta_materialization_executed": False,
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
            "source_result_review_artifact_dir": str(artifact_dir),
            "source_result_review_json": str(paths["source_result_review_json"]),
            "source_result_review_md": str(paths["source_result_review_md"]),
            "source_result_review_sha256s": str(paths["source_result_review_sha256s"]),
            "v14_audit_md": str(paths["v14_audit_md"]),
            "current_status_md": str(paths["current_status_md"]),
            "output_dir": str(output_dir.resolve()),
        },
        "source_artifact_hashes": _source_hashes(files=files, paths=paths),
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_artifact_camp_head": SOURCE_REVIEW_MODULE._kv(heads, "CAMP_HEAD", "camp_head"),
            "source_artifact_camp_origin_main": SOURCE_REVIEW_MODULE._kv(heads, "CAMP_ORIGIN_MAIN", "camp_origin_main"),
            "source_artifact_dp_head": SOURCE_REVIEW_MODULE._kv(heads, "DP_HEAD", "dp_head"),
        },
        "source_result_review_summary": _source_result_review_summary(source_review),
        "evidence_gap_closure_summary": _evidence_gap_closure_summary(source_review),
        "required_inputs": _required_inputs(source_review),
        "closure_plan": _closure_plan(),
        "planned_outputs": _planned_outputs(),
        "no_go_register": _no_go_register(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": checks,
        "final_decision": decision,
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    paths: dict[str, Path],
    files: dict[str, Path],
    source_review: dict[str, Any],
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    run_exit: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_record_count: int,
    expected_selection_log_count: int,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    decision = SOURCE_REVIEW_MODULE._dict(source_review.get("final_decision"))
    source_summary = SOURCE_REVIEW_MODULE._dict(source_review.get("source_execution_summary"))
    gap = SOURCE_REVIEW_MODULE._dict(source_review.get("evidence_gap_summary"))

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

    require("candidate_index_actual_safetycost_evidence_gap_closure_plan_enabled", enabled)
    require("source_result_review_artifact_dir_exists", artifact_dir.is_dir())
    for name, path in paths.items():
        require(f"{name}_exists", path.is_file(), str(path), "file")
    for name, path in files.items():
        require(f"source_artifact_{name}_exists", path.is_file(), str(path), "file")

    expect("current_dp_head_fixed", current_dp_head, required_dp_head)
    expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD)
    expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main)
    expect("source_artifact_dp_head_fixed", SOURCE_REVIEW_MODULE._kv(heads, "DP_HEAD", "dp_head"), required_dp_head)
    expect(
        "source_artifact_camp_matches_origin",
        SOURCE_REVIEW_MODULE._kv(heads, "CAMP_HEAD", "camp_head"),
        SOURCE_REVIEW_MODULE._kv(heads, "CAMP_ORIGIN_MAIN", "camp_origin_main"),
    )
    expect("source_result_review_run_exit", run_exit, "0")
    expect("audit_latest_status", SOURCE_REVIEW_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_REVIEW_STATUS)
    expect("audit_latest_next_work", SOURCE_REVIEW_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK)
    expect("status_doc_latest_status", SOURCE_REVIEW_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_REVIEW_STATUS)
    expect("status_doc_latest_next_work", SOURCE_REVIEW_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK)

    expect("source_result_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA)
    expect("source_result_review_passed", decision.get("passed"), True)
    expect("source_result_review_status", decision.get("status"), SOURCE_REVIEW_STATUS)
    expect("source_result_review_failed_checks", decision.get("failed_checks"), [])
    expect("source_result_review_authorized_next", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK)
    expect("source_candidate_index_execution_reviewed", decision.get("candidate_index_execution_reviewed_by_this_gate"), True)
    expect("source_candidate_index_replay_executed_by_review", decision.get("candidate_index_replay_executed_by_this_gate"), False)
    expect("source_outcome_acquisition_executed_by_review", decision.get("outcome_acquisition_executed_by_this_gate"), False)
    expect("source_actual_safetycost_available", decision.get("actual_safetycost_v1_available"), False)
    expect("source_actual_safetycost_claim_rule_evaluable", decision.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    expect("source_actual_safetycost_plan_authorized", decision.get("actual_safetycost_evidence_gap_closure_plan_authorized"), True)
    for action in BLOCKED_ACTIONS:
        expect(f"source_result_review_decision_{action}", decision.get(action), False)

    expect("source_objective_required_records", source_summary.get("objective_required_records"), expected_record_count)
    expect("source_paired_record_key_count", source_summary.get("paired_record_key_count"), expected_record_count)
    expect("source_candidate_closed_loop_outcome_records", source_summary.get("candidate_closed_loop_outcome_records"), expected_record_count)
    expect("source_missing_candidate_closed_loop_outcome_records", source_summary.get("missing_candidate_closed_loop_outcome_records"), 0)
    expect("source_runtime_record_count", source_summary.get("source_runtime_record_count"), expected_record_count)
    expect("source_candidate_index_record_count", source_summary.get("candidate_index_record_count"), expected_record_count)
    expect("source_candidate_index_replay_payload_records", source_summary.get("candidate_index_replay_payload_records"), expected_record_count)
    expect("source_selection_log_count", source_summary.get("selection_log_count"), expected_selection_log_count)
    expect("source_no_go_failed_count", source_summary.get("no_go_failed_count"), 0)
    expect("source_candidate_tensor_mutation_records", source_summary.get("candidate_tensor_mutation_records"), 0)
    expect("source_reference_blend_records", source_summary.get("reference_blend_records"), 0)
    expect("source_full36_path_records", source_summary.get("full36_path_records"), 0)
    expect("source_formal_seed_records", source_summary.get("formal_seed_records"), 0)
    expect("source_closed_loop_training_or_online_input_records", source_summary.get("closed_loop_training_or_online_input_records"), 0)
    expect("source_non_affine_score_records", source_summary.get("non_affine_score_records"), 0)
    expect("source_non_simplex_weight_records", source_summary.get("non_simplex_weight_records"), 0)
    expect("gap_actual_safetycost_available", gap.get("actual_safetycost_v1_available"), False)
    expect("gap_claim_rule_evaluable", gap.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    expect(
        "gap_next_evidence_need",
        gap.get("next_evidence_need"),
        "materialize SafetyCost_v1 deltas from paired candidate-index closed-loop outcomes",
    )
    expect("gap_claim_supported_by_review", gap.get("claim_supported_by_this_review"), False)
    expect("gap_promotion_supported_by_review", gap.get("promotion_supported_by_this_review"), False)

    _expect_sha(checks, "nested_result_review_json_sha", nested_sha256s, SOURCE_REVIEW_JSON_NAME, paths["source_result_review_json"])
    _expect_sha(checks, "nested_result_review_md_sha", nested_sha256s, SOURCE_REVIEW_MD_NAME, paths["source_result_review_md"])
    _expect_sha(checks, "root_heads_sha", root_sha256s, "HEADS", files["heads"])
    _expect_sha(checks, "root_command_sha", root_sha256s, "COMMAND", files["command"])
    _expect_sha(checks, "root_stdout_sha", root_sha256s, "stdout", files["stdout"])
    _expect_sha(checks, "root_stderr_sha", root_sha256s, "stderr", files["stderr"])
    _expect_sha(checks, "root_run_exit_sha", root_sha256s, "run.exit", files["run_exit"])
    _expect_sha(checks, "root_result_review_json_sha", root_sha256s, SOURCE_REVIEW_JSON_NAME, paths["source_result_review_json"])
    _expect_sha(checks, "root_result_review_md_sha", root_sha256s, SOURCE_REVIEW_MD_NAME, paths["source_result_review_md"])
    _expect_sha(checks, "root_result_review_sha256s_sha", root_sha256s, "SHA256SUMS", paths["source_result_review_sha256s"])
    checks.extend(_plan_contract_checks())
    return checks


def _plan_contract_checks() -> list[dict[str, Any]]:
    return [
        {
            "name": "required_input_names",
            "passed": [item["name"] for item in _required_inputs({})] == list(EXPECTED_REQUIRED_INPUTS),
            "actual": [item["name"] for item in _required_inputs({})],
            "expected": list(EXPECTED_REQUIRED_INPUTS),
        },
        {
            "name": "closure_plan_item_names",
            "passed": [item["name"] for item in _closure_plan()] == list(EXPECTED_PLAN_ITEMS),
            "actual": [item["name"] for item in _closure_plan()],
            "expected": list(EXPECTED_PLAN_ITEMS),
        },
        {
            "name": "closure_plan_does_not_materialize_deltas",
            "passed": sorted({item["materializes_safetycost_deltas"] for item in _closure_plan()}) == [False],
            "actual": sorted({item["materializes_safetycost_deltas"] for item in _closure_plan()}),
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
    summary = _source_result_review_summary(source_review)
    return [
        {
            "name": "passed_candidate_index_execution_result_review_artifact",
            "requirement": "consume the passed candidate-index execution result review and root SHA256SUMS as immutable source evidence",
            "source_status": summary.get("status"),
        },
        {"name": "paired_candidate_index_closed_loop_outcome_manifest", "requirement": "3200 CAMP shadow-selected fixed-DP candidate outcome records must remain locked"},
        {"name": "dp_top1_closed_loop_outcome_reference_manifest", "requirement": "DP Top-1 baseline outcomes must be identified from the paired fixed-DP source runtime evidence"},
        {"name": "fixed_dp_candidate_tensor_identity_manifest", "requirement": "candidate tensor identity and mutation-free evidence must remain locked"},
        {"name": "paired_run_key_index", "requirement": "CAMP shadow-selected and DP Top-1 rows must be paired by the audited run key"},
        {"name": "safetycost_v1_metric_and_claim_rule_spec", "requirement": "SafetyCost_v1, hard gates, bootstrap, and CI rules must be frozen before materialization"},
        {"name": "offline_evaluation_only_outcome_boundary", "requirement": "closed-loop outcomes remain offline evaluation evidence only"},
        {"name": "artifact_hash_heads_command_stdout_stderr_contract", "requirement": "future artifacts must include JSON, MD, SHA256SUMS, HEADS, COMMAND, stdout, stderr, and run.exit"},
    ]


def _closure_plan() -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "plan_only", "materializes_safetycost_deltas": False}
        for name in EXPECTED_PLAN_ITEMS
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


def _source_result_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = SOURCE_REVIEW_MODULE._dict(source_review.get("final_decision"))
    source_summary = SOURCE_REVIEW_MODULE._dict(source_review.get("source_execution_summary"))
    return {
        "schema_version": source_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "objective_required_records": source_summary.get("objective_required_records"),
        "paired_record_key_count": source_summary.get("paired_record_key_count"),
        "candidate_closed_loop_outcome_records": source_summary.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": source_summary.get("missing_candidate_closed_loop_outcome_records"),
        "source_runtime_record_count": source_summary.get("source_runtime_record_count"),
        "candidate_index_record_count": source_summary.get("candidate_index_record_count"),
        "candidate_index_replay_payload_records": source_summary.get("candidate_index_replay_payload_records"),
        "selection_log_count": source_summary.get("selection_log_count"),
        "no_go_failed_count": source_summary.get("no_go_failed_count"),
        "candidate_tensor_mutation_records": source_summary.get("candidate_tensor_mutation_records"),
        "reference_blend_records": source_summary.get("reference_blend_records"),
        "full36_path_records": source_summary.get("full36_path_records"),
        "formal_seed_records": source_summary.get("formal_seed_records"),
        "closed_loop_training_or_online_input_records": source_summary.get("closed_loop_training_or_online_input_records"),
        "non_affine_score_records": source_summary.get("non_affine_score_records"),
        "non_simplex_weight_records": source_summary.get("non_simplex_weight_records"),
    }


def _evidence_gap_closure_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    gap = SOURCE_REVIEW_MODULE._dict(source_review.get("evidence_gap_summary"))
    return {
        "actual_safetycost_v1_available": gap.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": gap.get("actual_safetycost_v1_claim_rule_evaluable"),
        "next_evidence_need": gap.get("next_evidence_need"),
        "planned_resolution": "preflight a future materialization gate for SafetyCost_v1 deltas from locked paired candidate-index outcomes and DP Top-1 baselines",
        "claim_supported_by_this_plan": False,
        "promotion_supported_by_this_plan": False,
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], source_review: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "candidate_index_actual_safetycost_evidence_gap_closure_plan_enabled" in failed:
        failure_class = "explicit_candidate_index_actual_safetycost_evidence_gap_closure_plan_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_result_review_") for name in failed):
        failure_class = "source_candidate_index_result_review_contract_failure"
    elif any(name.startswith(("source_", "gap_")) for name in failed):
        failure_class = "source_candidate_index_evidence_gap_contract_failure"
    elif any(name.startswith(("required_", "closure_plan_", "planned_", "no_go_")) for name in failed):
        failure_class = "candidate_index_actual_safetycost_evidence_gap_closure_plan_contract_failure"
    else:
        failure_class = "artifact_hash_or_plan_contract_failure"
    source_decision = SOURCE_REVIEW_MODULE._dict(source_review.get("final_decision"))
    source_summary = SOURCE_REVIEW_MODULE._dict(source_review.get("source_execution_summary"))
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_candidate_index_actual_safetycost_evidence_gap_closure_plan_ready": bool(passed),
        "objective_3200_candidate_index_actual_safetycost_evidence_gap_closure_plan_static_review_authorized": bool(passed),
        "source_result_review_consumed_by_this_gate": True,
        "actual_safetycost_delta_materialization_executed_by_this_gate": False,
        "candidate_index_replay_executed_by_this_gate": False,
        "outcome_acquisition_executed_by_this_gate": False,
        "actual_safetycost_v1_available": source_decision.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": source_decision.get("actual_safetycost_v1_claim_rule_evaluable"),
        "objective_required_records": source_summary.get("objective_required_records"),
        "paired_record_key_count": source_summary.get("paired_record_key_count"),
        "candidate_closed_loop_outcome_records": source_summary.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": source_summary.get("missing_candidate_closed_loop_outcome_records"),
        "source_runtime_record_count": source_summary.get("source_runtime_record_count"),
        "candidate_index_record_count": source_summary.get("candidate_index_record_count"),
        "candidate_index_replay_payload_records": source_summary.get("candidate_index_replay_payload_records"),
        "selection_log_count": source_summary.get("selection_log_count"),
        "no_go_failed_count": source_summary.get("no_go_failed_count"),
        "direct_promotion_recommendation": False,
        "claim_supported_by_this_plan": False,
        "promotion_supported_by_this_plan": False,
        "recommendation": "static_review_candidate_index_actual_safetycost_evidence_gap_closure_plan_only" if passed else "repair_or_rerun_same_plan_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    decision.update({name: False for name in BLOCKED_ACTIONS})
    return decision


def _source_hashes(*, files: dict[str, Path], paths: dict[str, Path]) -> dict[str, str | None]:
    return {
        "artifact_root_sha256s": SOURCE_REVIEW_MODULE._sha256(files["root_sha256s"]),
        "result_review_json": SOURCE_REVIEW_MODULE._sha256(paths["source_result_review_json"]),
        "result_review_md": SOURCE_REVIEW_MODULE._sha256(paths["source_result_review_md"]),
        "result_review_sha256s": SOURCE_REVIEW_MODULE._sha256(paths["source_result_review_sha256s"]),
        "heads": SOURCE_REVIEW_MODULE._sha256(files["heads"]),
        "command": SOURCE_REVIEW_MODULE._sha256(files["command"]),
        "stdout": SOURCE_REVIEW_MODULE._sha256(files["stdout"]),
        "stderr": SOURCE_REVIEW_MODULE._sha256(files["stderr"]),
        "run_exit": SOURCE_REVIEW_MODULE._sha256(files["run_exit"]),
    }


def _expect_sha(
    checks: list[dict[str, Any]],
    name: str,
    sums: dict[str, str],
    suffix: str,
    path: Path,
) -> None:
    actual = SOURCE_REVIEW_MODULE._sha_for_suffix(sums, suffix)
    expected = SOURCE_REVIEW_MODULE._sha256(path)
    checks.append({"name": name, "passed": actual == expected, "actual": actual, "expected": expected})


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PLAN_JSON_NAME
    md_path = output_dir / PLAN_MD_NAME
    json_path.write_text(
        json.dumps(SOURCE_REVIEW_MODULE._stable(report), indent=2) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        "\n".join(
            f"{SOURCE_REVIEW_MODULE._sha256(path)}  {path.name}"
            for path in [json_path, md_path]
        )
        + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_result_review_summary"]
    gap = report["evidence_gap_closure_summary"]
    lines = [
        "# Objective-3200 Candidate-Index Actual-SafetyCost Evidence-Gap Closure Plan",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failure class: `{decision['failure_class']}`",
        f"- Checks / failed checks: `{decision['check_count']} / {decision['failed_check_count']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Result Review",
        "",
        f"- Objective records / paired keys: `{summary['objective_required_records']} / {summary['paired_record_key_count']}`",
        f"- Candidate outcomes / missing: `{summary['candidate_closed_loop_outcome_records']} / {summary['missing_candidate_closed_loop_outcome_records']}`",
        f"- Source runtime / candidate-index / payload records: `{summary['source_runtime_record_count']} / {summary['candidate_index_record_count']} / {summary['candidate_index_replay_payload_records']}`",
        f"- Selection logs / no-go failed count: `{summary['selection_log_count']} / {summary['no_go_failed_count']}`",
        f"- Candidate tensor mutation / reference blend / Full36 / formal seed records: `{summary['candidate_tensor_mutation_records']} / {summary['reference_blend_records']} / {summary['full36_path_records']} / {summary['formal_seed_records']}`",
        f"- Closed-loop training-or-online input / non-affine / non-simplex records: `{summary['closed_loop_training_or_online_input_records']} / {summary['non_affine_score_records']} / {summary['non_simplex_weight_records']}`",
        "",
        "## Evidence Gap Closure",
        "",
        f"- Actual SafetyCost_v1 available: `{gap['actual_safetycost_v1_available']}`",
        f"- Claim rule evaluable: `{gap['actual_safetycost_v1_claim_rule_evaluable']}`",
        f"- Next evidence need: `{gap['next_evidence_need']}`",
        f"- Planned resolution: `{gap['planned_resolution']}`",
        "",
        "## Boundary",
        "",
        "- Plan only: no SafetyCost delta materialization, replay, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
        f"- Score expression: `{report['analysis']['score_expression']}`",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
