#!/usr/bin/env python3
"""Plan the actual-SafetyCost evidence-gap closure gate without executing it."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_source_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_paired_evaluation_execution_result.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_result_review",
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
BLOCKED_ACTIONS = SOURCE_REVIEW_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = SOURCE_REVIEW_MODULE.FALSE_EXECUTION_FLAGS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "actual_safetycost_evidence_gap_closure_plan_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_evidence_gap_closure_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_evidence_gap_closure_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_evidence_gap_closure_plan_static_review_only"
)

PLAN_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_evidence_gap_closure_plan.json"
)
PLAN_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_evidence_gap_closure_plan.md"
)

EXPECTED_REQUIRED_INPUTS = (
    "passed_paired_evaluation_execution_result_review_artifact",
    "fixed_dp_candidate_tensor_identity_manifest",
    "paired_shadow_vs_top1_run_key_index",
    "shadow_selected_run_level_closed_loop_outcome_collection_plan",
    "dp_top1_run_level_closed_loop_outcome_reference_manifest",
    "safetycost_v1_hard_gate_and_ci_config",
    "no_training_or_online_input_outcome_boundary",
    "artifact_hash_heads_command_stdout_stderr_contract",
)
EXPECTED_PLAN_ITEMS = (
    "lock_source_result_review_artifact_and_hashes",
    "identify_paired_shadow_selected_runs_missing_closed_loop_outcomes",
    "predeclare_closed_loop_outcome_summary_schema",
    "plan_outcome_materialization_without_training_or_online_input",
    "pair_shadow_selected_outcomes_against_dp_top1_by_run_key",
    "compute_safetycost_v1_delta_ci_and_hard_gate_after_outcomes_exist",
    "enforce_fixed_dp_candidate_tensor_and_no_trajectory_modification",
    "emit_static_reviewable_outcome_materialization_preflight_contract",
)
EXPECTED_PLANNED_OUTPUTS = (
    "outcome_request_manifest",
    "closed_loop_outcome_summary_schema",
    "paired_outcome_join_plan",
    "safetycost_v1_claim_rule_evaluation_plan",
    "leakage_and_boundary_no_go_plan",
    "outcome_materialization_preflight_artifact_contract",
)
EXPECTED_NO_GO = (
    "source_result_review_missing_or_failed",
    "dp_head_drift",
    "camp_generates_repairs_rewrites_or_blends_trajectory",
    "candidate_tensor_not_fixed_dp_source",
    "full36_or_formal_seed_11_12_13_present",
    "closed_loop_outcome_used_for_training_or_online_input",
    "non_affine_score_or_nonconvex_master",
    "promotion_deployment_or_online_selector_change",
    "safety_or_camp_over_dp_claim_before_actual_outcome_evidence",
    "unmatched_run_keys_or_candidate_tensor_identity_drift",
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
    parser.add_argument("--expected_record_count", type=int, default=3200)
    parser.add_argument("--expected_shadow_diff_records", type=int, default=2832)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_evidence_gap_closure_plan",
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
        expected_shadow_diff_records=args.expected_shadow_diff_records,
        label=args.label,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_evidence_gap_closure_plan
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
    expected_record_count: int = 3200,
    expected_shadow_diff_records: int = 2832,
    label: str | None = None,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = source_result_review_artifact_dir.resolve()
    source_result_review_json = source_result_review_json.resolve()
    source_result_review_md = source_result_review_md.resolve()
    source_result_review_sha256s = source_result_review_sha256s.resolve()
    output_dir = output_dir.resolve()
    source_review = SOURCE_REVIEW_MODULE._read_json_dict(source_result_review_json)
    v14_text = SOURCE_REVIEW_MODULE._read_text(v14_audit_md)
    status_text = SOURCE_REVIEW_MODULE._read_text(current_status_md)
    heads = SOURCE_REVIEW_MODULE._parse_key_values(SOURCE_REVIEW_MODULE._read_text(artifact_dir / "HEADS"))
    run_exit = SOURCE_REVIEW_MODULE._read_text(artifact_dir / "run.exit").strip()
    root_sha256s = SOURCE_REVIEW_MODULE._read_sha256sums(artifact_dir / "SHA256SUMS")
    nested_sha256s = SOURCE_REVIEW_MODULE._read_sha256sums(source_result_review_sha256s)

    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        source_result_review_json=source_result_review_json,
        source_result_review_md=source_result_review_md,
        source_result_review_sha256s=source_result_review_sha256s,
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
            "actual_safetycost_evidence_gap_closure_plan_only": True,
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
            "source_result_review_artifact_dir": str(artifact_dir),
            "source_result_review_json": str(source_result_review_json),
            "source_result_review_md": str(source_result_review_md),
            "source_result_review_sha256s": str(source_result_review_sha256s),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir),
        },
        "source_artifact_hashes": _source_hashes(
            artifact_dir=artifact_dir,
            source_result_review_json=source_result_review_json,
            source_result_review_md=source_result_review_md,
            source_result_review_sha256s=source_result_review_sha256s,
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
        "source_result_review_summary": _source_result_review_summary(source_review),
        "evidence_gap_closure_summary": _evidence_gap_closure_summary(source_review),
        "required_inputs": _required_inputs(source_review),
        "closure_plan": _closure_plan(),
        "planned_outputs": _planned_outputs(),
        "no_go_register": _no_go_register(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, source_review=source_review),
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    source_result_review_json: Path,
    source_result_review_md: Path,
    source_result_review_sha256s: Path,
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

    require("actual_safetycost_evidence_gap_closure_plan_enabled", enabled)
    require("source_result_review_artifact_dir_exists", artifact_dir.is_dir())
    for name, path in {
        "source_result_review_json": source_result_review_json,
        "source_result_review_md": source_result_review_md,
        "source_result_review_sha256s": source_result_review_sha256s,
        "source_result_review_heads": artifact_dir / "HEADS",
        "source_result_review_command": artifact_dir / "COMMAND",
        "source_result_review_stdout": artifact_dir / "stdout",
        "source_result_review_stderr": artifact_dir / "stderr",
        "source_result_review_run_exit": artifact_dir / "run.exit",
        "source_result_review_root_sha256s": artifact_dir / "SHA256SUMS",
    }.items():
        require(f"{name}_exists", path.is_file())

    expect("current_dp_head_fixed", current_dp_head, required_dp_head)
    expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD)
    expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main)
    expect("source_artifact_dp_head_fixed", heads.get("DP_HEAD"), required_dp_head)
    expect("source_artifact_camp_matches_origin", heads.get("CAMP_HEAD"), heads.get("CAMP_ORIGIN_MAIN"))
    expect("source_result_review_run_exit", run_exit, "0")
    expect("audit_latest_status", SOURCE_REVIEW_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_REVIEW_STATUS)
    expect("audit_latest_next_work", SOURCE_REVIEW_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK)
    expect("status_doc_latest_status", SOURCE_REVIEW_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_REVIEW_STATUS)
    expect("status_doc_latest_next_work", SOURCE_REVIEW_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK)

    expect("source_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA)
    expect("source_review_passed", decision.get("passed"), True)
    expect("source_review_status", decision.get("status"), SOURCE_REVIEW_STATUS)
    expect("source_review_failed_checks", decision.get("failed_checks"), [])
    expect("source_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK)
    expect("source_review_result_review_passed", decision.get("post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_result_review_passed"), True)
    expect("source_review_actual_safetycost_plan_authorized", decision.get("actual_safetycost_evidence_gap_closure_plan_authorized"), True)
    expect("source_review_paired_evaluation_executed_by_this_gate", decision.get("paired_evaluation_executed_by_this_gate"), False)
    expect("source_review_execution_reviewed_by_this_gate", decision.get("paired_evaluation_execution_reviewed_by_this_gate"), True)
    expect("source_review_actual_safetycost_available", decision.get("actual_safetycost_v1_available"), False)
    expect("source_review_claim_rule_evaluable", decision.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    for action in BLOCKED_ACTIONS:
        expect(f"source_review_decision_{action}", decision.get(action), False)
    for flag in FALSE_EXECUTION_FLAGS:
        expect(f"source_review_decision_{flag}", decision.get(flag), False)

    expect("source_paired_record_count", source_summary.get("paired_record_count"), expected_record_count)
    expect("source_unique_paired_run_key_count", source_summary.get("unique_paired_run_key_count"), expected_record_count)
    expect("source_shadow_diff_records", source_summary.get("shadow_diff_records"), expected_shadow_diff_records)
    expect("source_candidate_tensor_identity_records", source_summary.get("candidate_tensor_identity_records"), expected_record_count)
    expect("source_candidate_tensor_mutation_records", source_summary.get("candidate_tensor_mutation_records"), 0)
    expect("source_selection_score_worse_records", source_summary.get("selection_score_worse_records"), 0)
    expect("source_no_go_failed_count", source_summary.get("no_go_failed_count"), 0)
    expect("gap_actual_safetycost_available", gap.get("actual_safetycost_v1_available"), False)
    expect("gap_claim_rule_evaluable", gap.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    expect("gap_next_evidence_need", gap.get("next_evidence_need"), "paired shadow-selected run-level closed-loop outcome summaries")

    _expect_sha(checks, "nested_result_review_json_sha", nested_sha256s, source_result_review_json.name, source_result_review_json)
    _expect_sha(checks, "nested_result_review_md_sha", nested_sha256s, source_result_review_md.name, source_result_review_md)
    _expect_sha(checks, "root_result_review_json_sha", root_sha256s, f"./review/{source_result_review_json.name}", source_result_review_json)
    _expect_sha(checks, "root_result_review_md_sha", root_sha256s, f"./review/{source_result_review_md.name}", source_result_review_md)
    _expect_sha(checks, "root_result_review_sha256s_sha", root_sha256s, "./review/SHA256SUMS", source_result_review_sha256s)
    checks.extend(_plan_contract_checks())
    return checks


def _plan_contract_checks() -> list[dict[str, Any]]:
    return [
        {"name": "required_input_names", "passed": [item["name"] for item in _required_inputs({})] == list(EXPECTED_REQUIRED_INPUTS), "actual": [item["name"] for item in _required_inputs({})], "expected": list(EXPECTED_REQUIRED_INPUTS)},
        {"name": "closure_plan_item_names", "passed": [item["name"] for item in _closure_plan()] == list(EXPECTED_PLAN_ITEMS), "actual": [item["name"] for item in _closure_plan()], "expected": list(EXPECTED_PLAN_ITEMS)},
        {"name": "closure_plan_does_not_materialize_outcomes", "passed": sorted({item["materializes_outcomes"] for item in _closure_plan()}) == [False], "actual": sorted({item["materializes_outcomes"] for item in _closure_plan()}), "expected": [False]},
        {"name": "planned_output_names", "passed": [item["name"] for item in _planned_outputs()] == list(EXPECTED_PLANNED_OUTPUTS), "actual": [item["name"] for item in _planned_outputs()], "expected": list(EXPECTED_PLANNED_OUTPUTS)},
        {"name": "no_go_names", "passed": [item["name"] for item in _no_go_register()] == list(EXPECTED_NO_GO), "actual": [item["name"] for item in _no_go_register()], "expected": list(EXPECTED_NO_GO)},
    ]


def _required_inputs(source_review: dict[str, Any]) -> list[dict[str, Any]]:
    summary = _source_result_review_summary(source_review)
    return [
        {"name": "passed_paired_evaluation_execution_result_review_artifact", "requirement": "consume the passed result-review artifact and root SHA256SUMS as immutable source evidence", "source_status": summary.get("status")},
        {"name": "fixed_dp_candidate_tensor_identity_manifest", "requirement": "candidate tensor identity and mutation-free evidence must remain locked"},
        {"name": "paired_shadow_vs_top1_run_key_index", "requirement": "shadow-selected and DP Top-1 rows must be paired by the audited run key"},
        {"name": "shadow_selected_run_level_closed_loop_outcome_collection_plan", "requirement": "define how missing shadow-selected closed-loop outcome summaries would be obtained in a future authorized gate"},
        {"name": "dp_top1_run_level_closed_loop_outcome_reference_manifest", "requirement": "lock the already executed DP Top-1 outcome reference used for paired comparison"},
        {"name": "safetycost_v1_hard_gate_and_ci_config", "requirement": "freeze SafetyCost v1, hard gates, and CI rules before any outcome materialization"},
        {"name": "no_training_or_online_input_outcome_boundary", "requirement": "closed-loop outcomes remain evaluation evidence only and cannot become training or online selector input"},
        {"name": "artifact_hash_heads_command_stdout_stderr_contract", "requirement": "future artifacts must include JSON, MD, SHA256SUMS, HEADS, COMMAND, stdout, stderr, and run.exit"},
    ]


def _closure_plan() -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "plan_only", "materializes_outcomes": False}
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
        "paired_record_count": source_summary.get("paired_record_count"),
        "unique_paired_run_key_count": source_summary.get("unique_paired_run_key_count"),
        "shadow_diff_records": source_summary.get("shadow_diff_records"),
        "candidate_tensor_mutation_records": source_summary.get("candidate_tensor_mutation_records"),
        "selection_score_worse_records": source_summary.get("selection_score_worse_records"),
        "no_go_failed_count": source_summary.get("no_go_failed_count"),
    }


def _evidence_gap_closure_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    gap = SOURCE_REVIEW_MODULE._dict(source_review.get("evidence_gap_summary"))
    return {
        "actual_safetycost_v1_available": gap.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": gap.get("actual_safetycost_v1_claim_rule_evaluable"),
        "next_evidence_need": gap.get("next_evidence_need"),
        "planned_resolution": "preflight a future artifact that would materialize paired shadow-selected run-level closed-loop outcome summaries without using them for training or online input",
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], source_review: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "actual_safetycost_evidence_gap_closure_plan_enabled" in failed:
        failure_class = "explicit_actual_safetycost_evidence_gap_closure_plan_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_review_") for name in failed):
        failure_class = "source_result_review_contract_failure"
    elif any(name.startswith(("source_", "gap_")) for name in failed):
        failure_class = "source_evidence_gap_contract_failure"
    elif any(name.startswith(("required_", "closure_plan_", "planned_", "no_go_")) for name in failed):
        failure_class = "actual_safetycost_evidence_gap_closure_plan_contract_failure"
    else:
        failure_class = "artifact_hash_or_plan_contract_failure"
    source_decision = SOURCE_REVIEW_MODULE._dict(source_review.get("final_decision"))
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_evidence_gap_closure_plan_ready": bool(passed),
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_evidence_gap_closure_plan_static_review_authorized": bool(passed),
        "actual_safetycost_outcome_materialization_executed_by_this_gate": False,
        "paired_evaluation_executed_by_this_gate": False,
        "source_result_review_consumed_by_this_gate": True,
        "actual_safetycost_v1_available": source_decision.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": source_decision.get("actual_safetycost_v1_claim_rule_evaluable"),
        "previous_no_promotion_closeout_preserved": True,
        "direct_promotion_recommendation": False,
        "recommendation": "static_review_actual_safetycost_evidence_gap_closure_plan_only" if passed else "repair_or_rerun_same_plan_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def _source_hashes(
    *,
    artifact_dir: Path,
    source_result_review_json: Path,
    source_result_review_md: Path,
    source_result_review_sha256s: Path,
) -> dict[str, Any]:
    return {
        "source_result_review_json_sha256": SOURCE_REVIEW_MODULE._sha256(source_result_review_json),
        "source_result_review_md_sha256": SOURCE_REVIEW_MODULE._sha256(source_result_review_md),
        "source_result_review_sha256s_sha256": SOURCE_REVIEW_MODULE._sha256(source_result_review_sha256s),
        "source_result_review_root_sha256s_sha256": SOURCE_REVIEW_MODULE._sha256(artifact_dir / "SHA256SUMS"),
        "heads_sha256": SOURCE_REVIEW_MODULE._sha256(artifact_dir / "HEADS"),
        "command_sha256": SOURCE_REVIEW_MODULE._sha256(artifact_dir / "COMMAND"),
        "stdout_sha256": SOURCE_REVIEW_MODULE._sha256(artifact_dir / "stdout"),
        "stderr_sha256": SOURCE_REVIEW_MODULE._sha256(artifact_dir / "stderr"),
        "run_exit_sha256": SOURCE_REVIEW_MODULE._sha256(artifact_dir / "run.exit"),
    }


def _expect_sha(
    checks: list[dict[str, Any]],
    name: str,
    sums: dict[str, str],
    key: str,
    path: Path,
) -> None:
    actual = sums.get(key) or sums.get(key.removeprefix("./")) or sums.get(f"./{key}")
    expected = SOURCE_REVIEW_MODULE._sha256(path) if path.is_file() else None
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
    sums = [f"{SOURCE_REVIEW_MODULE._sha256(path)}  {path.name}" for path in (json_path, md_path)]
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_result_review_summary"]
    gap = report["evidence_gap_closure_summary"]
    lines = [
        "# v14 Actual-SafetyCost Evidence-Gap Closure Plan",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Result Review",
        "",
        f"- Paired records: `{summary['paired_record_count']}`",
        f"- Unique paired keys: `{summary['unique_paired_run_key_count']}`",
        f"- Shadow differs from Top-1 records: `{summary['shadow_diff_records']}`",
        f"- Candidate tensor mutation records: `{summary['candidate_tensor_mutation_records']}`",
        f"- Selection-score worse records: `{summary['selection_score_worse_records']}`",
        f"- No-go failed count: `{summary['no_go_failed_count']}`",
        "",
        "## Evidence Gap Closure",
        "",
        f"- Actual SafetyCost v1 available: `{gap['actual_safetycost_v1_available']}`",
        f"- Claim rule evaluable: `{gap['actual_safetycost_v1_claim_rule_evaluable']}`",
        f"- Next evidence need: `{gap['next_evidence_need']}`",
        f"- Planned resolution: `{gap['planned_resolution']}`",
        "",
        "## Boundary",
        "",
        "- Plan only: no closed-loop outcome materialization, replay, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
        f"- Score expression: `{report['analysis']['score_expression']}`",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
