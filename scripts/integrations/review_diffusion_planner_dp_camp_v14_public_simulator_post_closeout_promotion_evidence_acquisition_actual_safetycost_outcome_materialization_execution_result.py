#!/usr/bin/env python3
"""Read-only result review for actual SafetyCost materialization evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_execution_module():
    script_path = Path(__file__).resolve().with_name(
        "execute_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_actual_safetycost_outcome_materialization.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization_execution",
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


EXECUTION_MODULE = _load_execution_module()

FIXED_DP_HEAD = EXECUTION_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = EXECUTION_MODULE.SCORE_EXPRESSION
SOURCE_EXECUTION_SCHEMA = EXECUTION_MODULE.SCHEMA_VERSION
SOURCE_EXECUTION_STATUS = EXECUTION_MODULE.READY_STATUS
SOURCE_EXECUTION_JSON_NAME = EXECUTION_MODULE.EXECUTION_JSON_NAME
SOURCE_EXECUTION_MD_NAME = EXECUTION_MODULE.EXECUTION_MD_NAME
BLOCKED_ACTIONS = EXECUTION_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = EXECUTION_MODULE.FALSE_EXECUTION_FLAGS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "actual_safetycost_outcome_materialization_execution_result_review_v1"
)
AUTHORIZED_CURRENT_WORK = EXECUTION_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_execution_result_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_execution_result_review_rejected"
)
CLAIM_REVIEW_PLAN_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_claim_authorization_boundary_plan_only"
)
NO_PROMOTION_CLOSEOUT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_no_promotion_no_claim_closeout_record_only"
)

REVIEW_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_execution_result_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_execution_result_review.md"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_execution_json", type=Path, required=True)
    parser.add_argument("--source_execution_md", type=Path, required=True)
    parser.add_argument("--source_execution_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_summary_count", type=int, default=32)
    parser.add_argument("--expected_runtime_record_count", type=int, default=3200)
    parser.add_argument("--expected_selection_log_count", type=int, default=32)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization_execution_result_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_execution_artifact_dir=args.source_execution_artifact_dir,
        source_execution_json=args.source_execution_json,
        source_execution_md=args.source_execution_md,
        source_execution_sha256s=args.source_execution_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_summary_count=args.expected_summary_count,
        expected_runtime_record_count=args.expected_runtime_record_count,
        expected_selection_log_count=args.expected_selection_log_count,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization_execution_result_review
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_execution_artifact_dir: Path,
    source_execution_json: Path,
    source_execution_md: Path,
    source_execution_sha256s: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_summary_count: int = 32,
    expected_runtime_record_count: int = 3200,
    expected_selection_log_count: int = 32,
    enabled: bool = False,
) -> dict[str, Any]:
    source_execution_artifact_dir = source_execution_artifact_dir.resolve()
    source_execution_json = source_execution_json.resolve()
    source_execution_md = source_execution_md.resolve()
    source_execution_sha256s = source_execution_sha256s.resolve()
    output_dir = output_dir.resolve()

    source_execution = _read_json_dict(source_execution_json)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    heads = _parse_key_values(_read_text(source_execution_artifact_dir / "HEADS"))
    run_exit = _read_text(source_execution_artifact_dir / "run.exit").strip()
    root_sha256s = _read_sha256sums(source_execution_artifact_dir / "SHA256SUMS")
    nested_sha256s = _read_sha256sums(source_execution_sha256s)
    checks = _checks(
        enabled=enabled,
        source_execution_artifact_dir=source_execution_artifact_dir,
        source_execution_json=source_execution_json,
        source_execution_md=source_execution_md,
        source_execution_sha256s=source_execution_sha256s,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        run_exit=run_exit,
        source_execution=source_execution,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_summary_count=expected_summary_count,
        expected_runtime_record_count=expected_runtime_record_count,
        expected_selection_log_count=expected_selection_log_count,
    )
    passed = all(check["passed"] for check in checks)
    claim_rule = _claim_rule_summary(source_execution)
    decision = _decision(passed=passed, checks=checks, claim_rule=claim_rule, source_execution=source_execution)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "result_review_only": True,
            "actual_safetycost_outcome_materialization_executed_by_review": False,
            "replay_executed_by_review": False,
            "training_executed_by_review": False,
            "candidate_generation_executed_by_review": False,
            "dp_modified_by_review": False,
            "promotion_executed_by_review": False,
            "deployment_executed_by_review": False,
            "online_selector_change_by_review": False,
            "safety_or_camp_over_dp_claim_by_review": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "source_execution_artifact_dir": str(source_execution_artifact_dir),
            "source_execution_json": str(source_execution_json),
            "source_execution_md": str(source_execution_md),
            "source_execution_sha256s": str(source_execution_sha256s),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir),
        },
        "source_artifact_hashes": _source_hashes(
            source_execution_artifact_dir=source_execution_artifact_dir,
            source_execution_json=source_execution_json,
            source_execution_md=source_execution_md,
            source_execution_sha256s=source_execution_sha256s,
        ),
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_artifact_camp_head": _kv(heads, "CAMP_HEAD", "camp_head"),
            "source_artifact_camp_origin_main": _kv(heads, "CAMP_ORIGIN_MAIN", "camp_origin_main"),
            "source_artifact_dp_head": _kv(heads, "DP_HEAD", "dp_head"),
        },
        "source_execution_summary": _source_execution_summary(source_execution),
        "actual_safetycost_claim_rule_summary": claim_rule,
        "review_checks": checks,
        "final_decision": decision,
    }


def _checks(
    *,
    enabled: bool,
    source_execution_artifact_dir: Path,
    source_execution_json: Path,
    source_execution_md: Path,
    source_execution_sha256s: Path,
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    run_exit: str,
    source_execution: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_summary_count: int,
    expected_runtime_record_count: int,
    expected_selection_log_count: int,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    decision = _dict(source_execution.get("final_decision"))
    materialization = _dict(source_execution.get("materialization_summary"))
    runtime = _dict(source_execution.get("runtime_source_summary"))
    delta = _dict(materialization.get("delta_summary"))
    bootstrap = _dict(materialization.get("delta_bootstrap_ci95"))
    no_go = _dict(materialization.get("no_go_report"))

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

    latest_audit_status = _latest_value(v14_text, "current_v14_status")
    latest_audit_next = _latest_value(v14_text, "next_work_target")
    latest_status_doc_status = _latest_value(status_text, "current_v14_status")
    latest_status_doc_next = _latest_value(status_text, "next_work_target")

    require("result_review_enabled", enabled)
    require("source_execution_artifact_dir_exists", source_execution_artifact_dir.is_dir())
    require("source_execution_json_exists", source_execution_json.is_file())
    require("source_execution_md_exists", source_execution_md.is_file())
    require("source_execution_sha256s_exists", source_execution_sha256s.is_file())
    require("source_execution_heads_exists", (source_execution_artifact_dir / "HEADS").is_file())
    require("source_execution_command_exists", (source_execution_artifact_dir / "COMMAND").is_file())
    require("source_execution_stdout_exists", (source_execution_artifact_dir / "stdout").is_file())
    require("source_execution_stderr_exists", (source_execution_artifact_dir / "stderr").is_file())
    require("source_execution_run_exit_exists", (source_execution_artifact_dir / "run.exit").is_file())
    require("source_execution_root_sha256s_exists", (source_execution_artifact_dir / "SHA256SUMS").is_file())

    expect("current_dp_head_fixed", current_dp_head, required_dp_head)
    expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main)
    expect("source_artifact_dp_head_fixed", _kv(heads, "DP_HEAD", "dp_head"), required_dp_head)
    expect("source_execution_run_exit", run_exit, "0")
    expect("audit_latest_status", latest_audit_status, SOURCE_EXECUTION_STATUS)
    expect("audit_latest_next_work", latest_audit_next, AUTHORIZED_CURRENT_WORK)
    expect("status_doc_latest_status", latest_status_doc_status, SOURCE_EXECUTION_STATUS)
    expect("status_doc_latest_next_work", latest_status_doc_next, AUTHORIZED_CURRENT_WORK)

    expect("source_execution_schema", source_execution.get("schema_version"), SOURCE_EXECUTION_SCHEMA)
    expect("source_execution_passed", decision.get("passed"), True)
    expect("source_execution_status", decision.get("status"), SOURCE_EXECUTION_STATUS)
    expect("source_execution_failed_checks", decision.get("failed_checks"), [])
    expect("source_execution_authorized_next", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK)
    expect("source_actual_safetycost_materialized", decision.get("actual_safetycost_outcome_materialization_executed_by_this_gate"), True)
    expect("source_actual_safetycost_available", decision.get("actual_safetycost_v1_available"), True)
    expect("source_actual_safetycost_claim_rule_evaluable", decision.get("actual_safetycost_v1_claim_rule_evaluable"), True)
    expect(
        "source_closed_loop_outcome_training_or_online_input_authorized",
        decision.get("closed_loop_outcome_training_or_online_input_authorized"),
        False,
    )
    for action in BLOCKED_ACTIONS:
        expect(f"source_execution_decision_{action}", decision.get(action), False)
    for flag in FALSE_EXECUTION_FLAGS:
        expect(f"source_execution_decision_{flag}", decision.get(flag), False)

    expect("runtime_selection_log_count", runtime.get("selection_log_count"), expected_selection_log_count)
    expect("runtime_record_count", runtime.get("record_count"), expected_runtime_record_count)
    expect("runtime_candidate_tensor_mutation_records", runtime.get("candidate_tensor_mutation_records"), 0)
    expect("runtime_closed_loop_outcomes_training_or_online_input", runtime.get("closed_loop_outcomes_training_or_online_input"), False)
    expect("runtime_full36_path_records", runtime.get("full36_path_records"), 0)
    expect("runtime_formal_seed_records", runtime.get("formal_seed_records"), 0)
    expect("top1_summary_count", materialization.get("top1_summary_count"), expected_summary_count)
    expect("shadow_summary_count", materialization.get("shadow_summary_count"), expected_summary_count)
    expect("paired_run_key_count", materialization.get("paired_run_key_count"), expected_summary_count)
    expect("delta_count", materialization.get("delta_count"), expected_summary_count)
    expect("duplicate_run_key_count", materialization.get("duplicate_run_key_count"), 0)
    expect("unpaired_run_key_count", materialization.get("unpaired_run_key_count"), 0)
    expect("invalid_summary_count", materialization.get("invalid_summary_count"), 0)
    expect("materialization_no_go_failed_count", no_go.get("failed_count"), 0)
    expect("materialization_actual_safetycost_available", materialization.get("actual_safetycost_v1_available"), True)
    expect("materialization_actual_safetycost_claim_rule_evaluable", materialization.get("actual_safetycost_v1_claim_rule_evaluable"), True)
    expect("delta_summary_count", delta.get("count"), expected_summary_count)
    require("delta_summary_mean_present", delta.get("mean") is not None, delta.get("mean"), "numeric")
    require("delta_bootstrap_ci95_present", bootstrap.get("ci95_low") is not None and bootstrap.get("ci95_high") is not None)
    expect("safetycost_v1_claim_authorized", materialization.get("safetycost_v1_claim_authorized"), False)
    expect("camp_over_dp_top1_claim_authorized", materialization.get("camp_over_dp_top1_claim_authorized"), False)

    _expect_sha(checks, "nested_execution_json_sha", nested_sha256s, [source_execution_json.name], source_execution_json)
    _expect_sha(checks, "nested_execution_md_sha", nested_sha256s, [source_execution_md.name], source_execution_md)
    _expect_sha(
        checks,
        "root_execution_json_sha",
        root_sha256s,
        [f"./materialization/{source_execution_json.name}", f"materialization/{source_execution_json.name}"],
        source_execution_json,
    )
    _expect_sha(
        checks,
        "root_execution_md_sha",
        root_sha256s,
        [f"./materialization/{source_execution_md.name}", f"materialization/{source_execution_md.name}"],
        source_execution_md,
    )
    _expect_sha(
        checks,
        "root_execution_sha256s_sha",
        root_sha256s,
        ["./materialization/SHA256SUMS", "materialization/SHA256SUMS"],
        source_execution_sha256s,
    )
    return checks


def _decision(
    *,
    passed: bool,
    checks: list[dict[str, Any]],
    claim_rule: dict[str, Any],
    source_execution: dict[str, Any],
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    claim_supported = bool(passed and claim_rule["safety_benefit_claim_supported"])
    if passed:
        failure_class = None
    elif "result_review_enabled" in failed:
        failure_class = "explicit_actual_safetycost_result_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_execution_") for name in failed):
        failure_class = "source_actual_safetycost_materialization_execution_contract_failure"
    elif any(name.startswith(("runtime_", "materialization_", "delta_", "top1_", "shadow_", "paired_")) for name in failed):
        failure_class = "actual_safetycost_result_contract_failure"
    else:
        failure_class = "artifact_hash_or_review_contract_failure"

    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": (
            CLAIM_REVIEW_PLAN_WORK if claim_supported else NO_PROMOTION_CLOSEOUT_WORK
        )
        if passed
        else None,
        "post_closeout_promotion_evidence_acquisition_actual_safetycost_result_review_passed": bool(passed),
        "actual_safetycost_outcome_materialization_executed_by_this_gate": False,
        "actual_safetycost_outcome_materialization_reviewed_by_this_gate": True,
        "actual_safetycost_v1_available": claim_rule["actual_safetycost_v1_available"],
        "actual_safetycost_v1_claim_rule_evaluable": claim_rule["actual_safetycost_v1_claim_rule_evaluable"],
        "actual_safetycost_delta_mean": claim_rule["delta_mean"],
        "actual_safetycost_delta_ci95_low": claim_rule["delta_ci95_low"],
        "actual_safetycost_delta_ci95_high": claim_rule["delta_ci95_high"],
        "actual_safetycost_better_records": claim_rule["better_records"],
        "actual_safetycost_worse_records": claim_rule["worse_records"],
        "safety_benefit_claim_supported": claim_supported,
        "camp_over_dp_top1_claim_supported": claim_supported,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "no_promotion_closeout_recommended": bool(passed and not claim_supported),
        "previous_no_promotion_closeout_preserved": True,
        "direct_promotion_recommendation": False,
        "recommendation": (
            "plan_claim_authorization_boundary_review_only"
            if claim_supported
            else "record_no_promotion_no_claim_closeout_for_actual_safetycost_materialization"
        )
        if passed
        else "repair_or_rerun_same_review_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    for flag in (
        "training_executed_by_this_gate",
        "replay_executed_by_this_gate",
        "candidate_generation_executed_by_this_gate",
        "dp_modified_by_this_gate",
        "promotion_executed_by_this_gate",
        "deployment_executed_by_this_gate",
    ):
        decision[flag] = False
    return decision


def _claim_rule_summary(source_execution: dict[str, Any]) -> dict[str, Any]:
    materialization = _dict(source_execution.get("materialization_summary"))
    delta = _dict(materialization.get("delta_summary"))
    bootstrap = _dict(materialization.get("delta_bootstrap_ci95"))
    no_go = _dict(materialization.get("no_go_report"))
    actual_available = materialization.get("actual_safetycost_v1_available") is True
    claim_evaluable = materialization.get("actual_safetycost_v1_claim_rule_evaluable") is True
    delta_mean = delta.get("mean")
    ci95_low = bootstrap.get("ci95_low")
    ci95_high = bootstrap.get("ci95_high")
    better = int(delta.get("better_records") or 0)
    worse = int(delta.get("worse_records") or 0)
    no_go_failed = int(no_go.get("failed_count") or 0)
    supported = (
        actual_available
        and claim_evaluable
        and isinstance(delta_mean, (int, float))
        and isinstance(ci95_high, (int, float))
        and delta_mean < 0.0
        and ci95_high < 0.0
        and better > worse
        and no_go_failed == 0
    )
    return {
        "actual_safetycost_v1_available": actual_available,
        "actual_safetycost_v1_claim_rule_evaluable": claim_evaluable,
        "delta_count": materialization.get("delta_count"),
        "delta_mean": delta_mean,
        "delta_min": delta.get("min"),
        "delta_max": delta.get("max"),
        "delta_ci95_low": ci95_low,
        "delta_ci95_high": ci95_high,
        "better_records": better,
        "worse_records": worse,
        "tie_records": int(delta.get("tie_records") or 0),
        "no_go_failed_count": no_go_failed,
        "safety_benefit_claim_supported": bool(supported),
        "claim_rule": "shadow_minus_top1 SafetyCost mean < 0, CI95 high < 0, better>worse, no-go failed count == 0",
    }


def _source_execution_summary(source_execution: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_execution.get("final_decision"))
    runtime = _dict(source_execution.get("runtime_source_summary"))
    materialization = _dict(source_execution.get("materialization_summary"))
    delta = _dict(materialization.get("delta_summary"))
    bootstrap = _dict(materialization.get("delta_bootstrap_ci95"))
    no_go = _dict(materialization.get("no_go_report"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "runtime_selection_log_count": runtime.get("selection_log_count"),
        "runtime_record_count": runtime.get("record_count"),
        "top1_summary_count": materialization.get("top1_summary_count"),
        "shadow_summary_count": materialization.get("shadow_summary_count"),
        "paired_run_key_count": materialization.get("paired_run_key_count"),
        "delta_count": materialization.get("delta_count"),
        "delta_mean": delta.get("mean"),
        "delta_ci95_low": bootstrap.get("ci95_low"),
        "delta_ci95_high": bootstrap.get("ci95_high"),
        "better_records": delta.get("better_records"),
        "worse_records": delta.get("worse_records"),
        "no_go_failed_count": no_go.get("failed_count"),
    }


def _source_hashes(
    *,
    source_execution_artifact_dir: Path,
    source_execution_json: Path,
    source_execution_md: Path,
    source_execution_sha256s: Path,
) -> dict[str, Any]:
    root_sha = source_execution_artifact_dir / "SHA256SUMS"
    return {
        "source_execution_json_sha256": _sha256_if_file(source_execution_json),
        "source_execution_md_sha256": _sha256_if_file(source_execution_md),
        "source_execution_sha256s_sha256": _sha256_if_file(source_execution_sha256s),
        "source_execution_root_sha256s_sha256": _sha256_if_file(root_sha),
        "heads_sha256": _sha256_if_file(source_execution_artifact_dir / "HEADS"),
        "command_sha256": _sha256_if_file(source_execution_artifact_dir / "COMMAND"),
        "stdout_sha256": _sha256_if_file(source_execution_artifact_dir / "stdout"),
        "stderr_sha256": _sha256_if_file(source_execution_artifact_dir / "stderr"),
        "run_exit_sha256": _sha256_if_file(source_execution_artifact_dir / "run.exit"),
    }


def _expect_sha(
    checks: list[dict[str, Any]],
    name: str,
    sums: dict[str, str],
    keys: list[str],
    path: Path,
) -> None:
    actual = next((sums[key] for key in keys if key in sums), None)
    expected = _sha256_if_file(path)
    checks.append({"name": name, "passed": actual == expected, "actual": actual, "expected": expected})


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    json_path.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    sums = [f"{_sha256(path)}  {path.name}" for path in (json_path, md_path)]
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_execution_summary"]
    claim = report["actual_safetycost_claim_rule_summary"]
    lines = [
        "# v14 Actual SafetyCost Materialization Result Review",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Materialized Evidence",
        "",
        f"- Runtime selection logs / records: `{summary['runtime_selection_log_count']} / {summary['runtime_record_count']}`",
        f"- Top-1 / shadow summaries: `{summary['top1_summary_count']} / {summary['shadow_summary_count']}`",
        f"- Paired run keys / deltas: `{summary['paired_run_key_count']} / {summary['delta_count']}`",
        f"- Delta mean: `{summary['delta_mean']}`",
        f"- Delta CI95: `[{summary['delta_ci95_low']}, {summary['delta_ci95_high']}]`",
        f"- Better / worse records: `{summary['better_records']} / {summary['worse_records']}`",
        f"- No-go failed count: `{summary['no_go_failed_count']}`",
        "",
        "## Claim Rule",
        "",
        f"- Rule: `{claim['claim_rule']}`",
        f"- Safety benefit claim supported: `{claim['safety_benefit_claim_supported']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- CAMP-over-DP Top-1 claim authorized: `{decision['camp_over_dp_top1_claim_authorized']}`",
        f"- No-promotion closeout recommended: `{decision['no_promotion_closeout_recommended']}`",
        "",
        "## Boundary",
        "",
        "- Review only: no replay, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
        f"- Score expression: `{report['analysis']['score_expression']}`",
    ]
    return "\n".join(lines) + "\n"


def _read_json_dict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_sha256sums(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    sums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, name = line.partition("  ")
        if digest and name:
            sums[name.strip()] = digest.strip()
    return sums


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip()] = value.strip()
    return values


def _latest_value(text: str, key: str) -> str | None:
    token = f"{key}="
    if token not in text:
        return None
    return text.rsplit(token, maxsplit=1)[1].splitlines()[0]


def _kv(values: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        if key in values:
            return values[key]
    return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_if_file(path: Path) -> str | None:
    return _sha256(path) if path.is_file() else None


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
