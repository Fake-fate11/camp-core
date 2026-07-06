#!/usr/bin/env python3
"""Read-only review for candidate-index outcome acquisition execution."""

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
        "replay_outcome_acquisition.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_replay_outcome_acquisition_execution",
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
OBJECTIVE_REQUIRED_RECORDS = EXECUTION_MODULE.OBJECTIVE_REQUIRED_RECORDS
EXPECTED_SELECTION_LOG_COUNT = EXECUTION_MODULE.EXPECTED_SELECTION_LOG_COUNT
BLOCKED_ACTIONS = EXECUTION_MODULE.BLOCKED_ACTIONS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_replay_outcome_acquisition_execution_result_review_v1"
)
AUTHORIZED_CURRENT_WORK = EXECUTION_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_execution_result_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_execution_result_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_evidence_gap_closure_plan_only"
)

REVIEW_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_execution_result_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_execution_result_review.md"
)
FALSE_SOURCE_EXECUTION_FLAGS = (
    "training_executed_by_this_gate",
    "candidate_generation_executed_by_this_gate",
    "dp_modified_by_this_gate",
    "candidate_tensor_modified_by_this_gate",
    "promotion_executed_by_this_gate",
    "deployment_executed_by_this_gate",
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
    parser.add_argument("--expected_record_count", type=int, default=OBJECTIVE_REQUIRED_RECORDS)
    parser.add_argument("--expected_selection_log_count", type=int, default=EXPECTED_SELECTION_LOG_COUNT)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_execution_result_review",
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
        expected_record_count=args.expected_record_count,
        expected_selection_log_count=args.expected_selection_log_count,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_execution_result_review
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
    expected_record_count: int = OBJECTIVE_REQUIRED_RECORDS,
    expected_selection_log_count: int = EXPECTED_SELECTION_LOG_COUNT,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = source_execution_artifact_dir.resolve()
    paths = {
        "source_execution_json": source_execution_json.resolve(),
        "source_execution_md": source_execution_md.resolve(),
        "source_execution_sha256s": source_execution_sha256s.resolve(),
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
        "report_json": artifact_dir / "report" / SOURCE_EXECUTION_JSON_NAME,
        "report_md": artifact_dir / "report" / SOURCE_EXECUTION_MD_NAME,
        "report_sha256s": artifact_dir / "report" / "SHA256SUMS",
    }
    source_execution = _read_json_dict(paths["source_execution_json"])
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])
    heads = _parse_key_values(_read_text(files["heads"]))
    root_sha256s = _read_sha256sums(files["root_sha256s"])
    nested_sha256s = _read_sha256sums(paths["source_execution_sha256s"])
    run_exit = _read_text(files["run_exit"]).strip()
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
        run_exit=run_exit,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_record_count=expected_record_count,
        expected_selection_log_count=expected_selection_log_count,
    )
    passed = all(check["passed"] for check in checks)
    decision = _decision(passed=passed, checks=checks, source_execution=source_execution)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "result_review_only": True,
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
            "source_execution_json": str(paths["source_execution_json"]),
            "source_execution_md": str(paths["source_execution_md"]),
            "source_execution_sha256s": str(paths["source_execution_sha256s"]),
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
            "source_artifact_camp_head": _kv(heads, "CAMP_HEAD", "camp_head"),
            "source_artifact_camp_origin_main": _kv(heads, "CAMP_ORIGIN_MAIN", "camp_origin_main"),
            "source_artifact_dp_head": _kv(heads, "DP_HEAD", "dp_head"),
        },
        "source_execution_summary": _source_execution_summary(source_execution),
        "evidence_gap_summary": _evidence_gap_summary(source_execution),
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
    run_exit: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_record_count: int,
    expected_selection_log_count: int,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    decision = _dict(source_execution.get("final_decision"))
    strict = _dict(source_execution.get("strict_pairing_summary"))
    outcome = _dict(source_execution.get("candidate_index_outcome_summary"))
    execution = _dict(source_execution.get("execution"))
    analysis = _dict(source_execution.get("analysis"))
    no_go = _dict(source_execution.get("no_go_report"))

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

    require("result_review_enabled", enabled)
    require("source_execution_artifact_dir_exists", artifact_dir.is_dir())
    for name, path in paths.items():
        require(f"{name}_exists", path.is_file(), str(path), "file")
    for name, path in files.items():
        require(f"source_artifact_{name}_exists", path.is_file(), str(path), "file")
    expect("source_execution_json_path_matches_artifact", paths["source_execution_json"], files["report_json"])
    expect("source_execution_md_path_matches_artifact", paths["source_execution_md"], files["report_md"])
    expect("source_execution_sha256s_path_matches_artifact", paths["source_execution_sha256s"], files["report_sha256s"])

    latest_audit_status = _latest_value(v14_text, "current_v14_status")
    latest_audit_next = _latest_value(v14_text, "next_work_target")
    latest_status_doc_status = _latest_value(status_text, "current_v14_status")
    latest_status_doc_next = _latest_value(status_text, "next_work_target")
    expect("audit_latest_status", latest_audit_status, SOURCE_EXECUTION_STATUS)
    expect("audit_latest_next_work", latest_audit_next, AUTHORIZED_CURRENT_WORK)
    expect("status_doc_latest_status", latest_status_doc_status, SOURCE_EXECUTION_STATUS)
    expect("status_doc_latest_next_work", latest_status_doc_next, AUTHORIZED_CURRENT_WORK)

    expect("current_dp_head_fixed", current_dp_head, required_dp_head)
    expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD)
    expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main)
    expect("source_artifact_dp_head_fixed", _kv(heads, "DP_HEAD", "dp_head"), required_dp_head)
    expect("source_execution_run_exit", run_exit, "0")

    expect("source_execution_schema", source_execution.get("schema_version"), SOURCE_EXECUTION_SCHEMA)
    expect("source_execution_passed", decision.get("passed"), True)
    expect("source_execution_status", decision.get("status"), SOURCE_EXECUTION_STATUS)
    expect("source_execution_failed_checks", decision.get("failed_checks"), [])
    expect("source_execution_authorized_next", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK)
    expect("source_candidate_index_replay_executed", decision.get("candidate_index_replay_execution_executed_by_this_gate"), True)
    expect("source_outcome_acquisition_executed", decision.get("outcome_acquisition_executed_by_this_gate"), True)
    expect("source_actual_safetycost_available", decision.get("actual_safetycost_v1_available"), False)
    expect("source_actual_safetycost_claim_rule_evaluable", decision.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    for action in BLOCKED_ACTIONS:
        expect(f"source_execution_decision_{action}", decision.get(action), False)
    for flag in FALSE_SOURCE_EXECUTION_FLAGS:
        expect(f"source_execution_decision_{flag}", decision.get(flag, False), False)

    expect("strict_objective_required_records", strict.get("objective_required_records"), expected_record_count)
    expect("strict_paired_record_key_count", strict.get("paired_record_key_count"), expected_record_count)
    expect("strict_candidate_closed_loop_outcome_records", strict.get("candidate_closed_loop_outcome_records"), expected_record_count)
    expect("strict_missing_candidate_closed_loop_outcome_records", strict.get("missing_candidate_closed_loop_outcome_records"), 0)
    expect("strict_source_runtime_record_count", strict.get("source_runtime_record_count"), expected_record_count)
    expect("strict_candidate_index_record_count", strict.get("candidate_index_record_count"), expected_record_count)
    expect("strict_candidate_index_replay_payload_records", strict.get("candidate_index_replay_payload_records"), expected_record_count)
    expect("strict_unpaired_source_record_key_count", strict.get("unpaired_source_record_key_count"), 0)
    expect("strict_unpaired_candidate_record_key_count", strict.get("unpaired_candidate_record_key_count"), 0)
    expect("strict_actual_safetycost_available", strict.get("actual_safetycost_v1_available"), False)
    expect("strict_actual_safetycost_claim_rule_evaluable", strict.get("actual_safetycost_v1_claim_rule_evaluable"), False)

    expect("outcome_record_count", outcome.get("record_count"), expected_record_count)
    expect("outcome_unique_record_key_count", outcome.get("unique_record_key_count"), expected_record_count)
    expect("outcome_duplicate_record_key_count", outcome.get("duplicate_record_key_count"), 0)
    expect("outcome_selection_log_count", outcome.get("selection_log_count"), expected_selection_log_count)
    expect("outcome_validation_summary_count", outcome.get("validation_summary_count"), expected_selection_log_count)
    expect("outcome_candidate_closed_loop_outcome_records", outcome.get("candidate_closed_loop_outcome_records"), expected_record_count)
    expect("outcome_missing_candidate_closed_loop_outcome_records", outcome.get("missing_candidate_closed_loop_outcome_records"), 0)
    expect("outcome_candidate_index_replay_payload_records", outcome.get("candidate_index_replay_payload_records"), expected_record_count)
    expect("outcome_candidate_tensor_mutation_records", outcome.get("candidate_tensor_mutation_records"), 0)
    expect("outcome_reference_blend_records", outcome.get("reference_blend_records"), 0)
    expect("outcome_full36_path_records", outcome.get("full36_path_records"), 0)
    expect("outcome_formal_seed_records", outcome.get("formal_seed_records"), 0)
    expect("outcome_closed_loop_training_or_online_input_records", outcome.get("closed_loop_training_or_online_input_records"), 0)
    expect("outcome_non_affine_score_records", outcome.get("non_affine_score_records"), 0)
    expect("outcome_non_simplex_weight_records", outcome.get("non_simplex_weight_records"), 0)
    expect("no_go_failed_count", no_go.get("failed_count"), 0)
    expect("execution_attempted", execution.get("attempted"), True)
    expect("execution_runbook_exit_code", execution.get("runbook_exit_code"), 0)
    expect("execution_commands_executed", execution.get("commands_executed"), expected_selection_log_count)

    expect("analysis_candidate_generation", analysis.get("candidate_generation"), False)
    expect("analysis_candidate_tensor_modification", analysis.get("candidate_tensor_modification"), False)
    expect("analysis_closed_loop_outcomes_used_for_training", analysis.get("closed_loop_outcomes_used_for_training"), False)
    expect("analysis_closed_loop_outcomes_used_for_online_selector", analysis.get("closed_loop_outcomes_used_for_online_selector"), False)
    expect("analysis_dp_modification", analysis.get("dp_modification"), False)
    expect("analysis_training_execution", analysis.get("training_execution"), False)
    expect("analysis_promotion_executed", analysis.get("promotion_executed"), False)
    expect("analysis_deployment_executed", analysis.get("deployment_executed"), False)
    expect("analysis_online_selector_change", analysis.get("online_selector_change"), False)
    expect("analysis_safety_or_camp_over_dp_claim", analysis.get("safety_or_camp_over_dp_claim"), False)
    expect("analysis_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION)

    _expect_sha(checks, "nested_execution_json_sha", nested_sha256s, SOURCE_EXECUTION_JSON_NAME, files["report_json"])
    _expect_sha(checks, "nested_execution_md_sha", nested_sha256s, SOURCE_EXECUTION_MD_NAME, files["report_md"])
    _expect_sha(checks, "root_heads_sha", root_sha256s, "HEADS", files["heads"])
    _expect_sha(checks, "root_command_sha", root_sha256s, "COMMAND", files["command"])
    _expect_sha(checks, "root_stdout_sha", root_sha256s, "stdout", files["stdout"])
    _expect_sha(checks, "root_stderr_sha", root_sha256s, "stderr", files["stderr"])
    _expect_sha(checks, "root_run_exit_sha", root_sha256s, "run.exit", files["run_exit"])
    _expect_sha(checks, "root_report_json_sha", root_sha256s, f"report/{SOURCE_EXECUTION_JSON_NAME}", files["report_json"])
    _expect_sha(checks, "root_report_md_sha", root_sha256s, f"report/{SOURCE_EXECUTION_MD_NAME}", files["report_md"])
    _expect_sha(checks, "root_report_sha256s_sha", root_sha256s, "report/SHA256SUMS", files["report_sha256s"])
    return checks


def _decision(*, passed: bool, checks: list[dict[str, Any]], source_execution: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    strict = _dict(source_execution.get("strict_pairing_summary"))
    outcome = _dict(source_execution.get("candidate_index_outcome_summary"))
    if passed:
        failure_class = None
    elif "result_review_enabled" in failed:
        failure_class = "explicit_candidate_index_execution_result_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_execution_") for name in failed):
        failure_class = "source_candidate_index_execution_contract_failure"
    elif any(name.startswith(("strict_", "outcome_", "no_go_", "execution_", "analysis_")) for name in failed):
        failure_class = "candidate_index_outcome_contract_failure"
    else:
        failure_class = "artifact_hash_or_review_contract_failure"
    actual_available = bool(strict.get("actual_safetycost_v1_available"))
    claim_evaluable = bool(strict.get("actual_safetycost_v1_claim_rule_evaluable"))
    decision = {
        "passed": passed,
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
        "candidate_index_execution_reviewed_by_this_gate": True,
        "candidate_index_replay_executed_by_this_gate": False,
        "outcome_acquisition_executed_by_this_gate": False,
        "actual_safetycost_v1_available": actual_available,
        "actual_safetycost_v1_claim_rule_evaluable": claim_evaluable,
        "actual_safetycost_evidence_gap_closure_plan_authorized": passed and not actual_available,
        "objective_required_records": strict.get("objective_required_records"),
        "paired_record_key_count": strict.get("paired_record_key_count"),
        "candidate_closed_loop_outcome_records": strict.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": strict.get("missing_candidate_closed_loop_outcome_records"),
        "source_runtime_record_count": strict.get("source_runtime_record_count"),
        "candidate_index_record_count": strict.get("candidate_index_record_count"),
        "candidate_index_replay_payload_records": strict.get("candidate_index_replay_payload_records"),
        "selection_log_count": outcome.get("selection_log_count"),
        "no_go_failed_count": _dict(source_execution.get("no_go_report")).get("failed_count"),
    }
    decision.update({name: False for name in BLOCKED_ACTIONS})
    return decision


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    json_path.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    sha_path = output_dir / "SHA256SUMS"
    sha_path.write_text(
        "\n".join(f"{_sha256(path)}  {path.name}" for path in [json_path, md_path]) + "\n",
        encoding="utf-8",
    )


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_execution_summary"]
    gap = report["evidence_gap_summary"]
    return "\n".join(
        [
            "# Objective-3200 Candidate-Index Execution Result Review",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failure class: `{decision['failure_class']}`",
            f"- Checks / failed checks: `{decision['check_count']} / {decision['failed_check_count']}`",
            f"- Objective records / paired keys: `{decision['objective_required_records']} / {decision['paired_record_key_count']}`",
            f"- Candidate outcomes / missing: `{decision['candidate_closed_loop_outcome_records']} / {decision['missing_candidate_closed_loop_outcome_records']}`",
            f"- Selection logs: `{decision['selection_log_count']}`",
            f"- No-go failed count: `{decision['no_go_failed_count']}`",
            f"- Actual SafetyCost_v1 available / claim-rule evaluable: `{decision['actual_safetycost_v1_available']} / {decision['actual_safetycost_v1_claim_rule_evaluable']}`",
            f"- Evidence-gap closure plan authorized: `{decision['actual_safetycost_evidence_gap_closure_plan_authorized']}`",
            f"- Next work: `{decision['authorized_next_work']}`",
            f"- Candidate tensor mutation / reference blend / Full36 / formal seed records: `{summary['candidate_tensor_mutation_records']} / {summary['reference_blend_records']} / {summary['full36_path_records']} / {summary['formal_seed_records']}`",
            f"- Closed-loop training-or-online input / non-affine / non-simplex records: `{summary['closed_loop_training_or_online_input_records']} / {summary['non_affine_score_records']} / {summary['non_simplex_weight_records']}`",
            f"- Next evidence need: `{gap['next_evidence_need']}`",
            "",
        ]
    )


def _source_execution_summary(source_execution: dict[str, Any]) -> dict[str, Any]:
    strict = _dict(source_execution.get("strict_pairing_summary"))
    outcome = _dict(source_execution.get("candidate_index_outcome_summary"))
    execution = _dict(source_execution.get("execution"))
    return {
        "objective_required_records": strict.get("objective_required_records"),
        "paired_record_key_count": strict.get("paired_record_key_count"),
        "candidate_closed_loop_outcome_records": strict.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": strict.get("missing_candidate_closed_loop_outcome_records"),
        "source_runtime_record_count": strict.get("source_runtime_record_count"),
        "candidate_index_record_count": strict.get("candidate_index_record_count"),
        "candidate_index_replay_payload_records": strict.get("candidate_index_replay_payload_records"),
        "paired_record_key_sha256": strict.get("paired_record_key_sha256"),
        "record_count": outcome.get("record_count"),
        "selection_log_count": outcome.get("selection_log_count"),
        "validation_summary_count": outcome.get("validation_summary_count"),
        "unique_candidate_tensor_hash_count": outcome.get("unique_candidate_tensor_hash_count"),
        "duplicate_record_key_count": outcome.get("duplicate_record_key_count"),
        "candidate_tensor_mutation_records": outcome.get("candidate_tensor_mutation_records"),
        "reference_blend_records": outcome.get("reference_blend_records"),
        "full36_path_records": outcome.get("full36_path_records"),
        "formal_seed_records": outcome.get("formal_seed_records"),
        "closed_loop_training_or_online_input_records": outcome.get("closed_loop_training_or_online_input_records"),
        "non_affine_score_records": outcome.get("non_affine_score_records"),
        "non_simplex_weight_records": outcome.get("non_simplex_weight_records"),
        "commands_executed": execution.get("commands_executed"),
        "runbook_exit_code": execution.get("runbook_exit_code"),
    }


def _evidence_gap_summary(source_execution: dict[str, Any]) -> dict[str, Any]:
    strict = _dict(source_execution.get("strict_pairing_summary"))
    return {
        "actual_safetycost_v1_available": strict.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": strict.get("actual_safetycost_v1_claim_rule_evaluable"),
        "next_evidence_need": "materialize SafetyCost_v1 deltas from paired candidate-index closed-loop outcomes",
        "claim_supported_by_this_review": False,
        "promotion_supported_by_this_review": False,
    }


def _source_hashes(*, files: dict[str, Path], paths: dict[str, Path]) -> dict[str, str | None]:
    return {
        "artifact_root_sha256s": _sha256(files["root_sha256s"]),
        "execution_json": _sha256(paths["source_execution_json"]),
        "execution_md": _sha256(paths["source_execution_md"]),
        "execution_sha256s": _sha256(paths["source_execution_sha256s"]),
        "heads": _sha256(files["heads"]),
        "command": _sha256(files["command"]),
        "stdout": _sha256(files["stdout"]),
        "stderr": _sha256(files["stderr"]),
        "run_exit": _sha256(files["run_exit"]),
    }


def _expect_sha(checks: list[dict[str, Any]], name: str, sums: dict[str, str], suffix: str, path: Path) -> None:
    actual = _sha_for_suffix(sums, suffix)
    expected = _sha256(path)
    checks.append({"name": name, "passed": actual == expected, "actual": actual, "expected": expected})


def _latest_value(text: str, key: str) -> str | None:
    value = None
    prefix = f"{key}="
    for line in text.splitlines():
        if line.startswith(prefix):
            value = line[len(prefix) :].strip()
    return value


def _sha_for_suffix(sums: dict[str, str], suffix: str) -> str | None:
    suffix = suffix.replace("\\", "/").lstrip("./")
    for path, value in sums.items():
        if path.replace("\\", "/").lstrip("./") == suffix:
            return value
    for path, value in sums.items():
        normalized = path.replace("\\", "/").lstrip("./")
        if normalized.endswith(f"/{suffix}"):
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
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
