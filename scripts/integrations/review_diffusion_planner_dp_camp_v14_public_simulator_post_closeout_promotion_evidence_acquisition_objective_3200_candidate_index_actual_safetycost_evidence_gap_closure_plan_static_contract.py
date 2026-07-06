#!/usr/bin/env python3
"""Static review for the candidate-index actual-SafetyCost gap-closure plan."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_plan_module():
    plan_path = Path(__file__).resolve().with_name(
        "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_candidate_index_"
        "actual_safetycost_evidence_gap_closure.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_evidence_gap_closure_plan",
        plan_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PLAN_MODULE = _load_plan_module()
HELPER_MODULE = PLAN_MODULE.SOURCE_REVIEW_MODULE

FIXED_DP_HEAD = PLAN_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = PLAN_MODULE.SCORE_EXPRESSION
SOURCE_PLAN_SCHEMA = PLAN_MODULE.SCHEMA_VERSION
SOURCE_PLAN_STATUS = PLAN_MODULE.READY_STATUS
SOURCE_PLAN_JSON_NAME = PLAN_MODULE.PLAN_JSON_NAME
SOURCE_PLAN_MD_NAME = PLAN_MODULE.PLAN_MD_NAME
BLOCKED_ACTIONS = PLAN_MODULE.BLOCKED_ACTIONS
OBJECTIVE_REQUIRED_RECORDS = PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS
EXPECTED_SELECTION_LOG_COUNT = PLAN_MODULE.EXPECTED_SELECTION_LOG_COUNT

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_actual_safetycost_evidence_gap_closure_plan_static_review_v1"
)
AUTHORIZED_CURRENT_WORK = PLAN_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_evidence_gap_closure_plan_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_evidence_gap_closure_plan_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_preflight_plan_only"
)

REVIEW_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_evidence_gap_closure_plan_static_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_evidence_gap_closure_plan_static_review.md"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate_index_actual_safetycost_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--candidate_index_actual_safetycost_plan_json", type=Path, required=True)
    parser.add_argument("--candidate_index_actual_safetycost_plan_md", type=Path, required=True)
    parser.add_argument("--candidate_index_actual_safetycost_plan_sha256s", type=Path, required=True)
    parser.add_argument("--candidate_index_actual_safetycost_plan_script_py", type=Path, required=True)
    parser.add_argument("--candidate_index_actual_safetycost_plan_test_py", type=Path, required=True)
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
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_evidence_gap_closure_plan_static_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        candidate_index_actual_safetycost_plan_artifact_dir=(
            args.candidate_index_actual_safetycost_plan_artifact_dir
        ),
        candidate_index_actual_safetycost_plan_json=args.candidate_index_actual_safetycost_plan_json,
        candidate_index_actual_safetycost_plan_md=args.candidate_index_actual_safetycost_plan_md,
        candidate_index_actual_safetycost_plan_sha256s=args.candidate_index_actual_safetycost_plan_sha256s,
        candidate_index_actual_safetycost_plan_script_py=(
            args.candidate_index_actual_safetycost_plan_script_py
        ),
        candidate_index_actual_safetycost_plan_test_py=args.candidate_index_actual_safetycost_plan_test_py,
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
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_evidence_gap_closure_plan_static_review
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(HELPER_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    candidate_index_actual_safetycost_plan_artifact_dir: Path,
    candidate_index_actual_safetycost_plan_json: Path,
    candidate_index_actual_safetycost_plan_md: Path,
    candidate_index_actual_safetycost_plan_sha256s: Path,
    candidate_index_actual_safetycost_plan_script_py: Path,
    candidate_index_actual_safetycost_plan_test_py: Path,
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
    artifact_dir = candidate_index_actual_safetycost_plan_artifact_dir.resolve()
    plan_json = candidate_index_actual_safetycost_plan_json.resolve()
    plan_md = candidate_index_actual_safetycost_plan_md.resolve()
    plan_sha256s = candidate_index_actual_safetycost_plan_sha256s.resolve()
    script_py = candidate_index_actual_safetycost_plan_script_py.resolve()
    test_py = candidate_index_actual_safetycost_plan_test_py.resolve()
    output_dir = output_dir.resolve()
    source_plan = HELPER_MODULE._read_json_dict(plan_json)
    v14_text = HELPER_MODULE._read_text(v14_audit_md)
    status_text = HELPER_MODULE._read_text(current_status_md)
    heads = HELPER_MODULE._parse_key_values(HELPER_MODULE._read_text(artifact_dir / "HEADS"))
    run_exit = HELPER_MODULE._read_text(artifact_dir / "run.exit").strip()
    root_sha256s = HELPER_MODULE._read_sha256sums(artifact_dir / "SHA256SUMS")
    nested_sha256s = HELPER_MODULE._read_sha256sums(plan_sha256s)
    script_text = HELPER_MODULE._read_text(script_py)
    test_text = HELPER_MODULE._read_text(test_py)
    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        plan_json=plan_json,
        plan_md=plan_md,
        plan_sha256s=plan_sha256s,
        script_py=script_py,
        test_py=test_py,
        script_text=script_text,
        test_text=test_text,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        run_exit=run_exit,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        source_plan=source_plan,
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
            "static_review_only": True,
            "read_only": True,
            "candidate_index_actual_safetycost_plan_static_review_only": True,
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
            "candidate_index_actual_safetycost_plan_artifact_dir": str(artifact_dir),
            "candidate_index_actual_safetycost_plan_json": str(plan_json),
            "candidate_index_actual_safetycost_plan_md": str(plan_md),
            "candidate_index_actual_safetycost_plan_sha256s": str(plan_sha256s),
            "candidate_index_actual_safetycost_plan_script_py": str(script_py),
            "candidate_index_actual_safetycost_plan_test_py": str(test_py),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir),
        },
        "source_artifact_hashes": _source_hashes(
            artifact_dir=artifact_dir,
            plan_json=plan_json,
            plan_md=plan_md,
            plan_sha256s=plan_sha256s,
        ),
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_artifact_camp_head": HELPER_MODULE._kv(heads, "CAMP_HEAD", "camp_head"),
            "source_artifact_camp_origin_main": HELPER_MODULE._kv(heads, "CAMP_ORIGIN_MAIN", "camp_origin_main"),
            "source_artifact_dp_head": HELPER_MODULE._kv(heads, "DP_HEAD", "dp_head"),
        },
        "source_plan_summary": _source_plan_summary(source_plan),
        "evidence_gap_closure_summary": source_plan.get("evidence_gap_closure_summary", {}),
        "static_review_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, source_plan=source_plan),
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    plan_json: Path,
    plan_md: Path,
    plan_sha256s: Path,
    script_py: Path,
    test_py: Path,
    script_text: str,
    test_text: str,
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    run_exit: str,
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    source_plan: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_record_count: int,
    expected_selection_log_count: int,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    decision = HELPER_MODULE._dict(source_plan.get("final_decision"))
    summary = HELPER_MODULE._dict(source_plan.get("source_result_review_summary"))
    gap = HELPER_MODULE._dict(source_plan.get("evidence_gap_closure_summary"))

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

    require("static_review_enabled", enabled)
    require("source_plan_artifact_dir_exists", artifact_dir.is_dir())
    for name, path in {
        "plan_json": plan_json,
        "plan_md": plan_md,
        "plan_sha256s": plan_sha256s,
        "plan_script_py": script_py,
        "plan_test_py": test_py,
        "artifact_heads": artifact_dir / "HEADS",
        "artifact_command": artifact_dir / "COMMAND",
        "artifact_stdout": artifact_dir / "stdout",
        "artifact_stderr": artifact_dir / "stderr",
        "artifact_run_exit": artifact_dir / "run.exit",
        "artifact_root_sha256s": artifact_dir / "SHA256SUMS",
    }.items():
        require(f"{name}_exists", path.is_file())

    expect("current_dp_head_fixed", current_dp_head, required_dp_head)
    expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD)
    expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main)
    expect("source_artifact_dp_head_fixed", HELPER_MODULE._kv(heads, "DP_HEAD", "dp_head"), required_dp_head)
    expect(
        "source_artifact_camp_matches_origin",
        HELPER_MODULE._kv(heads, "CAMP_HEAD", "camp_head"),
        HELPER_MODULE._kv(heads, "CAMP_ORIGIN_MAIN", "camp_origin_main"),
    )
    expect("artifact_run_exit", run_exit, "0")
    expect("audit_latest_status", HELPER_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_PLAN_STATUS)
    expect("audit_latest_next_work", HELPER_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK)
    expect("status_doc_latest_status", HELPER_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_PLAN_STATUS)
    expect("status_doc_latest_next_work", HELPER_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK)

    expect("source_plan_schema", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA)
    expect("source_plan_passed", decision.get("passed"), True)
    expect("source_plan_status", decision.get("status"), SOURCE_PLAN_STATUS)
    expect("source_plan_failed_checks", decision.get("failed_checks"), [])
    expect("source_plan_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK)
    expect("source_plan_ready", decision.get("objective_3200_candidate_index_actual_safetycost_evidence_gap_closure_plan_ready"), True)
    expect(
        "source_plan_static_review_authorized",
        decision.get("objective_3200_candidate_index_actual_safetycost_evidence_gap_closure_plan_static_review_authorized"),
        True,
    )
    expect("source_plan_no_delta_materialization", decision.get("actual_safetycost_delta_materialization_executed_by_this_gate"), False)
    expect("source_plan_no_candidate_index_replay", decision.get("candidate_index_replay_executed_by_this_gate"), False)
    expect("source_plan_no_outcome_acquisition", decision.get("outcome_acquisition_executed_by_this_gate"), False)
    expect("source_plan_consumes_result_review", decision.get("source_result_review_consumed_by_this_gate"), True)
    expect("source_plan_actual_safetycost_available", decision.get("actual_safetycost_v1_available"), False)
    expect("source_plan_claim_rule_evaluable", decision.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    for action in BLOCKED_ACTIONS:
        expect(f"source_plan_decision_{action}", decision.get(action), False)

    expect("source_plan_check_count", len(_list(source_plan.get("plan_checks"))), 75)
    expect("source_plan_failed_check_count", decision.get("failed_check_count"), 0)
    expect("source_required_input_names", [item.get("name") for item in _list(source_plan.get("required_inputs"))], list(PLAN_MODULE.EXPECTED_REQUIRED_INPUTS))
    expect("source_closure_plan_names", [item.get("name") for item in _list(source_plan.get("closure_plan"))], list(PLAN_MODULE.EXPECTED_PLAN_ITEMS))
    expect(
        "source_closure_plan_no_delta_materialization",
        sorted({item.get("materializes_safetycost_deltas") for item in _list(source_plan.get("closure_plan"))}),
        [False],
    )
    expect("source_planned_output_names", [item.get("name") for item in _list(source_plan.get("planned_outputs"))], list(PLAN_MODULE.EXPECTED_PLANNED_OUTPUTS))
    expect("source_no_go_names", [item.get("name") for item in _list(source_plan.get("no_go_register"))], list(PLAN_MODULE.EXPECTED_NO_GO))

    expect("source_summary_objective_required_records", summary.get("objective_required_records"), expected_record_count)
    expect("source_summary_paired_record_key_count", summary.get("paired_record_key_count"), expected_record_count)
    expect("source_summary_candidate_closed_loop_outcome_records", summary.get("candidate_closed_loop_outcome_records"), expected_record_count)
    expect("source_summary_missing_candidate_closed_loop_outcome_records", summary.get("missing_candidate_closed_loop_outcome_records"), 0)
    expect("source_summary_source_runtime_record_count", summary.get("source_runtime_record_count"), expected_record_count)
    expect("source_summary_candidate_index_record_count", summary.get("candidate_index_record_count"), expected_record_count)
    expect("source_summary_candidate_index_replay_payload_records", summary.get("candidate_index_replay_payload_records"), expected_record_count)
    expect("source_summary_selection_log_count", summary.get("selection_log_count"), expected_selection_log_count)
    expect("source_summary_no_go_failed_count", summary.get("no_go_failed_count"), 0)
    expect("source_summary_candidate_tensor_mutation_records", summary.get("candidate_tensor_mutation_records"), 0)
    expect("source_summary_reference_blend_records", summary.get("reference_blend_records"), 0)
    expect("source_summary_full36_path_records", summary.get("full36_path_records"), 0)
    expect("source_summary_formal_seed_records", summary.get("formal_seed_records"), 0)
    expect("source_summary_closed_loop_training_or_online_input_records", summary.get("closed_loop_training_or_online_input_records"), 0)
    expect("source_summary_non_affine_score_records", summary.get("non_affine_score_records"), 0)
    expect("source_summary_non_simplex_weight_records", summary.get("non_simplex_weight_records"), 0)
    expect("gap_actual_safetycost_available", gap.get("actual_safetycost_v1_available"), False)
    expect("gap_claim_rule_evaluable", gap.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    expect(
        "gap_next_evidence_need",
        gap.get("next_evidence_need"),
        "materialize SafetyCost_v1 deltas from paired candidate-index closed-loop outcomes",
    )

    _expect_sha(checks, "nested_plan_json_sha", nested_sha256s, plan_json.name, plan_json)
    _expect_sha(checks, "nested_plan_md_sha", nested_sha256s, plan_md.name, plan_md)
    _expect_sha(checks, "root_plan_json_sha", root_sha256s, f"plan/{plan_json.name}", plan_json)
    _expect_sha(checks, "root_plan_md_sha", root_sha256s, f"plan/{plan_md.name}", plan_md)
    _expect_sha(checks, "root_plan_sha256s_sha", root_sha256s, "plan/SHA256SUMS", plan_sha256s)
    checks.extend(_source_surface_checks(script_text, test_text))
    return checks


def _source_surface_checks(script_text: str, test_text: str) -> list[dict[str, Any]]:
    expected_script_tokens = [
        "candidate_index_actual_safetycost_evidence_gap_closure_plan_only",
        "actual_safetycost_delta_materialization_executed_by_this_gate",
        "SafetyCost_v1 deltas from locked paired candidate-index outcomes",
        "score_expression",
    ]
    expected_test_tokens = [
        "test_candidate_index_actual_safetycost_evidence_gap_closure_plan_passes",
        "test_candidate_index_actual_safetycost_evidence_gap_closure_plan_rejects_source_claim_leak",
        "test_candidate_index_actual_safetycost_evidence_gap_closure_plan_rejects_missing_outcomes",
        "test_candidate_index_actual_safetycost_evidence_gap_closure_plan_rejects_hash_drift",
    ]
    checks = []
    for index, token in enumerate(expected_script_tokens, start=1):
        checks.append(
            {
                "name": f"plan_script_contains_{index}",
                "passed": token in script_text,
                "actual": token if token in script_text else "missing",
                "expected": token,
            }
        )
    for index, token in enumerate(expected_test_tokens, start=1):
        checks.append(
            {
                "name": f"plan_test_contains_{index}",
                "passed": token in test_text,
                "actual": token if token in test_text else "missing",
                "expected": token,
            }
        )
    return checks


def _decision(*, passed: bool, checks: list[dict[str, Any]], source_plan: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "static_review_enabled" in failed:
        failure_class = "explicit_candidate_index_actual_safetycost_plan_static_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_plan_") for name in failed):
        failure_class = "source_candidate_index_actual_safetycost_plan_contract_failure"
    elif any(name.startswith(("source_", "gap_")) for name in failed):
        failure_class = "source_candidate_index_evidence_gap_contract_failure"
    elif any(name.startswith(("nested_", "root_", "artifact_")) for name in failed):
        failure_class = "artifact_hash_contract_failure"
    else:
        failure_class = "candidate_index_actual_safetycost_plan_static_review_contract_failure"
    source_decision = HELPER_MODULE._dict(source_plan.get("final_decision"))
    summary = HELPER_MODULE._dict(source_plan.get("source_result_review_summary"))
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_candidate_index_actual_safetycost_evidence_gap_closure_plan_static_review_passed": bool(passed),
        "objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_plan_authorized": bool(passed),
        "source_plan_consumed_by_this_gate": True,
        "actual_safetycost_delta_materialization_executed_by_this_gate": False,
        "candidate_index_replay_executed_by_this_gate": False,
        "outcome_acquisition_executed_by_this_gate": False,
        "actual_safetycost_v1_available": source_decision.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": source_decision.get("actual_safetycost_v1_claim_rule_evaluable"),
        "objective_required_records": summary.get("objective_required_records"),
        "paired_record_key_count": summary.get("paired_record_key_count"),
        "candidate_closed_loop_outcome_records": summary.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": summary.get("missing_candidate_closed_loop_outcome_records"),
        "source_runtime_record_count": summary.get("source_runtime_record_count"),
        "candidate_index_record_count": summary.get("candidate_index_record_count"),
        "candidate_index_replay_payload_records": summary.get("candidate_index_replay_payload_records"),
        "selection_log_count": summary.get("selection_log_count"),
        "no_go_failed_count": summary.get("no_go_failed_count"),
        "direct_promotion_recommendation": False,
        "claim_supported_by_this_review": False,
        "promotion_supported_by_this_review": False,
        "recommendation": "plan_candidate_index_actual_safetycost_delta_materialization_preflight_only" if passed else "repair_or_rerun_same_static_review_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    decision.update({name: False for name in BLOCKED_ACTIONS})
    return decision


def _source_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = HELPER_MODULE._dict(source_plan.get("final_decision"))
    summary = HELPER_MODULE._dict(source_plan.get("source_result_review_summary"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "plan_check_count": len(_list(source_plan.get("plan_checks"))),
        "failed_check_count": decision.get("failed_check_count"),
        "required_input_count": len(_list(source_plan.get("required_inputs"))),
        "closure_plan_count": len(_list(source_plan.get("closure_plan"))),
        "planned_output_count": len(_list(source_plan.get("planned_outputs"))),
        "no_go_count": len(_list(source_plan.get("no_go_register"))),
        "objective_required_records": summary.get("objective_required_records"),
        "paired_record_key_count": summary.get("paired_record_key_count"),
        "candidate_closed_loop_outcome_records": summary.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": summary.get("missing_candidate_closed_loop_outcome_records"),
        "selection_log_count": summary.get("selection_log_count"),
        "no_go_failed_count": summary.get("no_go_failed_count"),
    }


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _source_hashes(*, artifact_dir: Path, plan_json: Path, plan_md: Path, plan_sha256s: Path) -> dict[str, Any]:
    return {
        "plan_json_sha256": HELPER_MODULE._sha256(plan_json),
        "plan_md_sha256": HELPER_MODULE._sha256(plan_md),
        "plan_sha256s_sha256": HELPER_MODULE._sha256(plan_sha256s),
        "root_sha256s_sha256": HELPER_MODULE._sha256(artifact_dir / "SHA256SUMS"),
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
    suffix: str,
    path: Path,
) -> None:
    actual = HELPER_MODULE._sha_for_suffix(sums, suffix)
    expected = HELPER_MODULE._sha256(path)
    checks.append({"name": name, "passed": actual == expected, "actual": actual, "expected": expected})


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    json_path.write_text(
        json.dumps(HELPER_MODULE._stable(report), indent=2) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        "\n".join(f"{HELPER_MODULE._sha256(path)}  {path.name}" for path in [json_path, md_path]) + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_plan_summary"]
    gap = report["evidence_gap_closure_summary"]
    lines = [
        "# Objective-3200 Candidate-Index Actual-SafetyCost Gap-Closure Plan Static Review",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failure class: `{decision['failure_class']}`",
        f"- Checks / failed checks: `{decision['check_count']} / {decision['failed_check_count']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Plan",
        "",
        f"- Plan checks / failed checks: `{summary['plan_check_count']} / {summary['failed_check_count']}`",
        f"- Objective records / paired keys: `{summary['objective_required_records']} / {summary['paired_record_key_count']}`",
        f"- Candidate outcomes / missing: `{summary['candidate_closed_loop_outcome_records']} / {summary['missing_candidate_closed_loop_outcome_records']}`",
        f"- Selection logs / no-go failed count: `{summary['selection_log_count']} / {summary['no_go_failed_count']}`",
        "",
        "## Evidence Gap",
        "",
        f"- Actual SafetyCost_v1 available: `{gap.get('actual_safetycost_v1_available')}`",
        f"- Claim rule evaluable: `{gap.get('actual_safetycost_v1_claim_rule_evaluable')}`",
        f"- Next evidence need: `{gap.get('next_evidence_need')}`",
        "",
        "## Boundary",
        "",
        "- Static review only: no SafetyCost delta materialization, replay, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
        f"- Score expression: `{report['analysis']['score_expression']}`",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
