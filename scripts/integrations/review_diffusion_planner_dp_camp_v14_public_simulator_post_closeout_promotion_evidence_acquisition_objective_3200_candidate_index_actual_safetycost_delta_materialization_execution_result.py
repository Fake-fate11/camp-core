#!/usr/bin/env python3
"""Read-only review for objective-3200 candidate-index SafetyCost deltas."""

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
        "promotion_evidence_acquisition_objective_3200_candidate_index_"
        "actual_safetycost_delta_materialization.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_delta_materialization_execution",
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
SOURCE_DELTA_TABLE_JSONL_NAME = EXECUTION_MODULE.DELTA_TABLE_JSONL_NAME
OBJECTIVE_REQUIRED_RECORDS = EXECUTION_MODULE.OBJECTIVE_REQUIRED_RECORDS
EXPECTED_SELECTION_LOG_COUNT = EXECUTION_MODULE.EXPECTED_SELECTION_LOG_COUNT
BLOCKED_ACTIONS = EXECUTION_MODULE.BLOCKED_ACTIONS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_actual_safetycost_delta_materialization_execution_result_review_v1"
)
AUTHORIZED_CURRENT_WORK = EXECUTION_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_execution_result_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_execution_result_review_rejected"
)
CLAIM_AUTHORIZATION_BOUNDARY_PLAN_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_claim_authorization_boundary_plan_only"
)
NO_PROMOTION_CLOSEOUT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_no_promotion_no_claim_closeout_record_only"
)

REVIEW_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_execution_result_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_execution_result_review.md"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_execution_json", type=Path, required=True)
    parser.add_argument("--source_execution_md", type=Path, required=True)
    parser.add_argument("--source_execution_delta_jsonl", type=Path, required=True)
    parser.add_argument("--source_execution_sha256s", type=Path, required=True)
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
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_delta_materialization_execution_result_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_execution_artifact_dir=args.source_execution_artifact_dir,
        source_execution_json=args.source_execution_json,
        source_execution_md=args.source_execution_md,
        source_execution_delta_jsonl=args.source_execution_delta_jsonl,
        source_execution_sha256s=args.source_execution_sha256s,
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
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_delta_materialization_execution_result_review
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
    source_execution_delta_jsonl: Path,
    source_execution_sha256s: Path,
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
    artifact_dir = source_execution_artifact_dir.resolve()
    paths = {
        "source_execution_json": source_execution_json.resolve(),
        "source_execution_md": source_execution_md.resolve(),
        "source_execution_delta_jsonl": source_execution_delta_jsonl.resolve(),
        "source_execution_sha256s": source_execution_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    files = _artifact_files(artifact_dir)
    source_execution = _read_json_dict(paths["source_execution_json"])
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])
    heads = _parse_key_values(_read_text(files["heads"]))
    root_sha256s = _read_sha256sums(files["root_sha256s"])
    nested_sha256s = _read_sha256sums(paths["source_execution_sha256s"])
    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        paths=paths,
        files=files,
        source_execution=source_execution,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_record_count=expected_record_count,
        expected_selection_log_count=expected_selection_log_count,
    )
    passed = all(check["passed"] for check in checks)
    claim_rule = _claim_rule_summary(source_execution)
    decision = _decision(passed=passed, checks=checks, claim_rule=claim_rule, source_execution=source_execution)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "result_review_only": True,
            "actual_safetycost_delta_materialization_executed_by_review": False,
            "candidate_index_replay_executed_by_review": False,
            "outcome_acquisition_executed_by_review": False,
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
            "source_execution_artifact_dir": str(artifact_dir),
            **{name: str(path) for name, path in paths.items()},
            "output_dir": str(output_dir.resolve()),
        },
        "source_artifact_hashes": _source_hashes(files=files, paths=paths),
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_artifact_camp_head": _kv(heads, "CAMP_HEAD", "camp_head"),
            "source_artifact_camp_origin_main": _kv(heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main"),
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
    artifact_dir: Path,
    paths: dict[str, Path],
    files: dict[str, Path],
    source_execution: dict[str, Any],
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_record_count: int,
    expected_selection_log_count: int,
) -> list[dict[str, Any]]:
    decision = _dict(source_execution.get("final_decision"))
    delta = _dict(source_execution.get("delta_materialization_summary"))
    delta_summary = _dict(delta.get("delta_summary"))
    bootstrap = _dict(delta.get("delta_bootstrap_ci95"))
    claim = _dict(delta.get("claim_rule"))
    no_go = _dict(source_execution.get("no_go_report"))
    analysis = _dict(source_execution.get("analysis"))
    checks = [
        _expect("result_review_enabled", enabled, True),
        _check("source_execution_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
        _expect("source_execution_json_path_matches_artifact", paths["source_execution_json"], files["report_json"]),
        _expect("source_execution_md_path_matches_artifact", paths["source_execution_md"], files["report_md"]),
        _expect("source_execution_delta_jsonl_path_matches_artifact", paths["source_execution_delta_jsonl"], files["delta_jsonl"]),
        _expect("source_execution_sha256s_path_matches_artifact", paths["source_execution_sha256s"], files["report_sha256s"]),
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), SOURCE_EXECUTION_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("status_doc_latest_status", _latest_value(status_text, "current_v14_status"), SOURCE_EXECUTION_STATUS),
        _expect("status_doc_latest_next_work", _latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("source_artifact_dp_head_fixed", _kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
        _expect("source_execution_run_exit", _read_text(files["run_exit"]).strip(), "0"),
        _expect("source_execution_schema", source_execution.get("schema_version"), SOURCE_EXECUTION_SCHEMA),
        _expect("source_execution_passed", decision.get("passed"), True),
        _expect("source_execution_status", decision.get("status"), SOURCE_EXECUTION_STATUS),
        _expect("source_execution_failed_checks", decision.get("failed_checks"), []),
        _expect("source_execution_authorized_next", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_delta_execution_executed", decision.get("actual_safetycost_delta_materialization_executed_by_this_gate"), True),
        _expect("source_candidate_index_replay_executed_by_this_gate", decision.get("candidate_index_replay_executed_by_this_gate"), False),
        _expect("source_outcome_acquisition_executed_by_this_gate", decision.get("outcome_acquisition_executed_by_this_gate"), False),
        _expect("source_actual_safetycost_available", decision.get("actual_safetycost_v1_available"), True),
        _expect("source_actual_safetycost_claim_rule_evaluable", decision.get("actual_safetycost_v1_claim_rule_evaluable"), True),
        _expect("source_claim_rule_evaluable", decision.get("claim_rule_evaluable"), True),
        _expect("source_paired_rows", decision.get("paired_safetycost_v1_row_count"), expected_record_count),
        _expect("source_same_plus_non_top1", decision.get("same_as_top1_records", 0) + decision.get("non_top1_shadow_selected_records", 0), expected_record_count),
        _expect(
            "source_better_tie_worse_sum",
            decision.get("delta_better_records", 0) + decision.get("delta_tie_records", 0) + decision.get("delta_worse_records", 0),
            expected_record_count,
        ),
        _expect("delta_record_count", delta.get("record_count"), expected_record_count),
        _expect("delta_selection_log_count", delta.get("selection_log_count"), expected_selection_log_count),
        _expect("delta_paired_row_count", delta.get("paired_safetycost_v1_row_count"), expected_record_count),
        _expect("delta_actual_safetycost_available", delta.get("actual_safetycost_v1_available"), True),
        _expect("delta_actual_safetycost_claim_rule_evaluable", delta.get("actual_safetycost_v1_claim_rule_evaluable"), True),
        _expect("delta_no_go_failed_count", _dict(delta.get("no_go_report")).get("failed_count"), 0),
        _expect("no_go_failed_count", no_go.get("failed_count"), 0),
        _expect("delta_summary_count", delta_summary.get("count"), expected_record_count),
        _expect("delta_summary_better_tie_worse_sum", delta_summary.get("better_records", 0) + delta_summary.get("tie_records", 0) + delta_summary.get("worse_records", 0), expected_record_count),
        _check("bootstrap_ci95_low_present", bootstrap.get("ci95_low") is not None, bootstrap.get("ci95_low"), "number"),
        _check("bootstrap_ci95_high_present", bootstrap.get("ci95_high") is not None, bootstrap.get("ci95_high"), "number"),
        _expect("claim_rule_evaluable", claim.get("evaluable"), True),
        _expect("claim_rule_claim_authorization", claim.get("safety_benefit_claim_authorized"), False),
        _expect("claim_rule_camp_claim_authorization", claim.get("camp_over_dp_top1_claim_authorized"), False),
        _expect("analysis_candidate_generation", analysis.get("candidate_generation"), False),
        _expect("analysis_candidate_tensor_modification", analysis.get("candidate_tensor_modification"), False),
        _expect("analysis_closed_loop_outcomes_used_for_training", analysis.get("closed_loop_outcomes_used_for_training"), False),
        _expect("analysis_closed_loop_outcomes_used_for_online_selector", analysis.get("closed_loop_outcomes_used_for_online_selector"), False),
        _expect("analysis_dp_modification", analysis.get("dp_modification"), False),
        _expect("analysis_training_execution", analysis.get("training_execution"), False),
        _expect("analysis_promotion_executed", analysis.get("promotion_executed"), False),
        _expect("analysis_deployment_executed", analysis.get("deployment_executed"), False),
        _expect("analysis_online_selector_change", analysis.get("online_selector_change"), False),
        _expect("analysis_safety_or_camp_over_dp_claim", analysis.get("safety_or_camp_over_dp_claim"), False),
        _expect("analysis_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, allow_empty=False))
    for name, path in files.items():
        checks.extend(_path_checks(f"source_artifact_{name}", path, allow_empty=name == "stderr"))
    checks.extend(_sha_checks(root_sha256s=root_sha256s, nested_sha256s=nested_sha256s, files=files))
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_execution_decision_{action}", decision.get(action), False))
    return checks


def _decision(
    *,
    passed: bool,
    checks: list[dict[str, Any]],
    claim_rule: dict[str, Any],
    source_execution: dict[str, Any],
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    supported = bool(passed and claim_rule["claim_rule_passed"] and claim_rule["delta_ci95_high"] < 0.0)
    if passed:
        failure_class = None
    elif "result_review_enabled" in failed:
        failure_class = "explicit_candidate_index_actual_safetycost_result_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_drift"
    elif any("sha" in name for name in failed):
        failure_class = "source_artifact_hash_mismatch"
    elif any(name.startswith("source_execution_decision") for name in failed):
        failure_class = "source_execution_claim_or_boundary_leak"
    else:
        failure_class = "candidate_index_actual_safetycost_delta_result_review_contract_failure"
    source_decision = _dict(source_execution.get("final_decision"))
    return {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": CLAIM_AUTHORIZATION_BOUNDARY_PLAN_WORK if supported else NO_PROMOTION_CLOSEOUT_WORK if passed else None,
        "objective_3200_candidate_index_actual_safetycost_delta_materialization_execution_result_review_passed": bool(passed),
        "candidate_index_actual_safetycost_delta_materialization_execution_reviewed_by_this_gate": True,
        "actual_safetycost_delta_materialization_executed_by_this_gate": False,
        "candidate_index_replay_executed_by_this_gate": False,
        "outcome_acquisition_executed_by_this_gate": False,
        "actual_safetycost_v1_available": source_decision.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": source_decision.get("actual_safetycost_v1_claim_rule_evaluable"),
        "claim_rule_passed": claim_rule["claim_rule_passed"],
        "safety_benefit_claim_supported": supported,
        "camp_over_dp_top1_claim_supported": supported,
        "claim_authorization_boundary_plan_authorized": supported,
        "no_promotion_closeout_recommended": bool(passed and not supported),
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _source_execution_summary(source_execution: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_execution.get("final_decision"))
    delta = _dict(source_execution.get("delta_materialization_summary"))
    summary = _dict(delta.get("delta_summary"))
    bootstrap = _dict(delta.get("delta_bootstrap_ci95"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "paired_safetycost_v1_row_count": decision.get("paired_safetycost_v1_row_count"),
        "same_as_top1_records": decision.get("same_as_top1_records"),
        "non_top1_shadow_selected_records": decision.get("non_top1_shadow_selected_records"),
        "delta_better_records": summary.get("better_records"),
        "delta_tie_records": summary.get("tie_records"),
        "delta_worse_records": summary.get("worse_records"),
        "delta_mean": summary.get("mean"),
        "delta_ci95_low": bootstrap.get("ci95_low"),
        "delta_ci95_high": bootstrap.get("ci95_high"),
    }


def _claim_rule_summary(source_execution: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_execution.get("final_decision"))
    delta = _dict(source_execution.get("delta_materialization_summary"))
    summary = _dict(delta.get("delta_summary"))
    bootstrap = _dict(delta.get("delta_bootstrap_ci95"))
    claim = _dict(delta.get("claim_rule"))
    return {
        "actual_safetycost_v1_available": decision.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": decision.get("actual_safetycost_v1_claim_rule_evaluable"),
        "delta_mean": summary.get("mean"),
        "delta_ci95_low": bootstrap.get("ci95_low"),
        "delta_ci95_high": bootstrap.get("ci95_high"),
        "claim_rule_evaluable": claim.get("evaluable"),
        "claim_rule_passed": claim.get("passed"),
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    json_path.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        "\n".join(f"{_sha256(path)}  {path.name}" for path in (json_path, md_path)) + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_execution_summary"]
    claim = report["actual_safetycost_claim_rule_summary"]
    return "\n".join(
        [
            "# Objective-3200 Candidate-Index Actual-SafetyCost Delta Execution Result Review",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failure class: `{decision['failure_class']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
            "## Reviewed Evidence",
            "",
            f"- Delta rows: `{summary['paired_safetycost_v1_row_count']}`",
            f"- Shadow-selected Top-1 / non-Top-1: `{summary['same_as_top1_records']} / {summary['non_top1_shadow_selected_records']}`",
            f"- Better / tie / worse: `{summary['delta_better_records']} / {summary['delta_tie_records']} / {summary['delta_worse_records']}`",
            f"- Mean delta: `{summary['delta_mean']}`",
            f"- CI95 low / high: `{summary['delta_ci95_low']}` / `{summary['delta_ci95_high']}`",
            f"- Claim rule evaluable / passed: `{claim['claim_rule_evaluable']}` / `{claim['claim_rule_passed']}`",
            "",
            "## Boundary",
            "",
            "- Review only: no delta materialization, replay, outcome acquisition, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
            "- Claim support may authorize only a later claim-boundary plan gate; this review itself authorizes no claim.",
            "",
        ]
    )


def _artifact_files(artifact_dir: Path) -> dict[str, Path]:
    return {
        "heads": artifact_dir / "HEADS",
        "command": artifact_dir / "COMMAND",
        "stdout": artifact_dir / "stdout",
        "stderr": artifact_dir / "stderr",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "report_json": artifact_dir / "report" / SOURCE_EXECUTION_JSON_NAME,
        "report_md": artifact_dir / "report" / SOURCE_EXECUTION_MD_NAME,
        "delta_jsonl": artifact_dir / "report" / SOURCE_DELTA_TABLE_JSONL_NAME,
        "report_sha256s": artifact_dir / "report" / "SHA256SUMS",
    }


def _source_hashes(*, files: dict[str, Path], paths: dict[str, Path]) -> dict[str, str | None]:
    return {
        "artifact_root_sha256s": _sha256(files["root_sha256s"]),
        "execution_json": _sha256(paths["source_execution_json"]),
        "execution_md": _sha256(paths["source_execution_md"]),
        "delta_jsonl": _sha256(paths["source_execution_delta_jsonl"]),
        "execution_sha256s": _sha256(paths["source_execution_sha256s"]),
    }


def _sha_checks(
    *,
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    files: dict[str, Path],
) -> list[dict[str, Any]]:
    return [
        _expect("root_heads_sha", _sha_for_suffix(root_sha256s, "HEADS"), _sha256(files["heads"])),
        _expect("root_command_sha", _sha_for_suffix(root_sha256s, "COMMAND"), _sha256(files["command"])),
        _expect("root_stdout_sha", _sha_for_suffix(root_sha256s, "stdout"), _sha256(files["stdout"])),
        _expect("root_stderr_sha", _sha_for_suffix(root_sha256s, "stderr"), _sha256(files["stderr"])),
        _expect("root_run_exit_sha", _sha_for_suffix(root_sha256s, "run.exit"), _sha256(files["run_exit"])),
        _expect("root_report_json_sha", _sha_for_suffix(root_sha256s, f"report/{SOURCE_EXECUTION_JSON_NAME}"), _sha256(files["report_json"])),
        _expect("root_report_md_sha", _sha_for_suffix(root_sha256s, f"report/{SOURCE_EXECUTION_MD_NAME}"), _sha256(files["report_md"])),
        _expect("root_delta_jsonl_sha", _sha_for_suffix(root_sha256s, f"report/{SOURCE_DELTA_TABLE_JSONL_NAME}"), _sha256(files["delta_jsonl"])),
        _expect("root_report_sha256s_sha", _sha_for_suffix(root_sha256s, "report/SHA256SUMS"), _sha256(files["report_sha256s"])),
        _expect("nested_execution_json_sha", _sha_for_suffix(nested_sha256s, SOURCE_EXECUTION_JSON_NAME), _sha256(files["report_json"])),
        _expect("nested_execution_md_sha", _sha_for_suffix(nested_sha256s, SOURCE_EXECUTION_MD_NAME), _sha256(files["report_md"])),
        _expect("nested_delta_jsonl_sha", _sha_for_suffix(nested_sha256s, SOURCE_DELTA_TABLE_JSONL_NAME), _sha256(files["delta_jsonl"])),
    ]


def _path_checks(name: str, path: Path, *, allow_empty: bool) -> list[dict[str, Any]]:
    exists = path.is_file()
    checks = [_check(f"{name}_exists", exists, str(path), "file")]
    if exists and not allow_empty:
        checks.append(_check(f"{name}_nonempty", path.stat().st_size > 0, path.stat().st_size, ">0 bytes"))
    return checks


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _latest_value(text: str, key: str) -> str | None:
    value = None
    prefix = f"{key}="
    for line in text.splitlines():
        if line.startswith(prefix):
            value = line[len(prefix) :].strip()
    return value


def _sha_for_suffix(sums: dict[str, str], suffix: str) -> str | None:
    suffix = suffix.replace("\\", "/")
    for path, value in sums.items():
        normalized = path.replace("\\", "/")
        if normalized == suffix or normalized.endswith(f"/{suffix}"):
            return value
    return None


def _read_sha256sums(path: Path) -> dict[str, str]:
    sums: dict[str, str] = {}
    for line in _read_text(path).splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            sums[parts[1].strip()] = parts[0].strip()
    return sums


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _kv(values: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        if key in values:
            return values[key]
    return None


def _read_json_dict(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    return payload if isinstance(payload, dict) else {}


def _read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    if not path or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _stable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
