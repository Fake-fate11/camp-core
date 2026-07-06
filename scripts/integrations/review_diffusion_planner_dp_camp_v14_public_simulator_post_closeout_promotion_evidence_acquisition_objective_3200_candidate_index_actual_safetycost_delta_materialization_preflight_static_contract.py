#!/usr/bin/env python3
"""Static review for the candidate-index SafetyCost delta-materialization preflight."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_preflight_module():
    preflight_path = Path(__file__).resolve().with_name(
        "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_candidate_index_"
        "actual_safetycost_delta_materialization.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_delta_materialization_preflight",
        preflight_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PREFLIGHT_MODULE = _load_preflight_module()
HELPER_MODULE = PREFLIGHT_MODULE.HELPER_MODULE

FIXED_DP_HEAD = PREFLIGHT_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = PREFLIGHT_MODULE.SCORE_EXPRESSION
SOURCE_PREFLIGHT_SCHEMA = PREFLIGHT_MODULE.SCHEMA_VERSION
SOURCE_PREFLIGHT_STATUS = PREFLIGHT_MODULE.READY_STATUS
SOURCE_PREFLIGHT_JSON_NAME = PREFLIGHT_MODULE.PREFLIGHT_JSON_NAME
SOURCE_PREFLIGHT_MD_NAME = PREFLIGHT_MODULE.PREFLIGHT_MD_NAME
BLOCKED_ACTIONS = PREFLIGHT_MODULE.BLOCKED_ACTIONS
OBJECTIVE_REQUIRED_RECORDS = PREFLIGHT_MODULE.OBJECTIVE_REQUIRED_RECORDS
EXPECTED_SELECTION_LOG_COUNT = PREFLIGHT_MODULE.EXPECTED_SELECTION_LOG_COUNT

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_static_review_v1"
)
AUTHORIZED_CURRENT_WORK = PREFLIGHT_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_preflight_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_preflight_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_execution_only"
)

REVIEW_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_preflight_static_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_preflight_static_review.md"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delta_materialization_preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--delta_materialization_preflight_json", type=Path, required=True)
    parser.add_argument("--delta_materialization_preflight_md", type=Path, required=True)
    parser.add_argument("--delta_materialization_preflight_sha256s", type=Path, required=True)
    parser.add_argument("--delta_materialization_preflight_script_py", type=Path, required=True)
    parser.add_argument("--delta_materialization_preflight_test_py", type=Path, required=True)
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
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_static_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        delta_materialization_preflight_artifact_dir=args.delta_materialization_preflight_artifact_dir,
        delta_materialization_preflight_json=args.delta_materialization_preflight_json,
        delta_materialization_preflight_md=args.delta_materialization_preflight_md,
        delta_materialization_preflight_sha256s=args.delta_materialization_preflight_sha256s,
        delta_materialization_preflight_script_py=args.delta_materialization_preflight_script_py,
        delta_materialization_preflight_test_py=args.delta_materialization_preflight_test_py,
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
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_static_review
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(HELPER_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    delta_materialization_preflight_artifact_dir: Path,
    delta_materialization_preflight_json: Path,
    delta_materialization_preflight_md: Path,
    delta_materialization_preflight_sha256s: Path,
    delta_materialization_preflight_script_py: Path,
    delta_materialization_preflight_test_py: Path,
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
    artifact_dir = delta_materialization_preflight_artifact_dir.resolve()
    preflight_json = delta_materialization_preflight_json.resolve()
    preflight_md = delta_materialization_preflight_md.resolve()
    preflight_sha256s = delta_materialization_preflight_sha256s.resolve()
    script_py = delta_materialization_preflight_script_py.resolve()
    test_py = delta_materialization_preflight_test_py.resolve()
    output_dir = output_dir.resolve()

    source_preflight = HELPER_MODULE._read_json_dict(preflight_json)
    v14_text = HELPER_MODULE._read_text(v14_audit_md)
    status_text = HELPER_MODULE._read_text(current_status_md)
    heads = HELPER_MODULE._parse_key_values(HELPER_MODULE._read_text(artifact_dir / "HEADS"))
    run_exit = HELPER_MODULE._read_text(artifact_dir / "run.exit").strip()
    root_sha256s = HELPER_MODULE._read_sha256sums(artifact_dir / "SHA256SUMS")
    nested_sha256s = HELPER_MODULE._read_sha256sums(preflight_sha256s)
    script_text = HELPER_MODULE._read_text(script_py)
    test_text = HELPER_MODULE._read_text(test_py)

    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        preflight_json=preflight_json,
        preflight_md=preflight_md,
        preflight_sha256s=preflight_sha256s,
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
        source_preflight=source_preflight,
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
            "candidate_index_actual_safetycost_delta_materialization_preflight_static_review_only": True,
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
            "delta_materialization_preflight_artifact_dir": str(artifact_dir),
            "delta_materialization_preflight_json": str(preflight_json),
            "delta_materialization_preflight_md": str(preflight_md),
            "delta_materialization_preflight_sha256s": str(preflight_sha256s),
            "delta_materialization_preflight_script_py": str(script_py),
            "delta_materialization_preflight_test_py": str(test_py),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir),
        },
        "source_artifact_hashes": _source_hashes(
            artifact_dir=artifact_dir,
            preflight_json=preflight_json,
            preflight_md=preflight_md,
            preflight_sha256s=preflight_sha256s,
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
        "source_preflight_summary": _source_preflight_summary(source_preflight),
        "contract_summary": _contract_summary(source_preflight),
        "static_review_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, source_preflight=source_preflight),
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    preflight_json: Path,
    preflight_md: Path,
    preflight_sha256s: Path,
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
    source_preflight: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_record_count: int,
    expected_selection_log_count: int,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    decision = HELPER_MODULE._dict(source_preflight.get("final_decision"))
    summary = _source_preflight_summary(source_preflight)
    contract = _contract_summary(source_preflight)

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
    require("source_preflight_artifact_dir_exists", artifact_dir.is_dir())
    for name, path in {
        "source_preflight_json": preflight_json,
        "source_preflight_md": preflight_md,
        "source_preflight_sha256s": preflight_sha256s,
        "source_preflight_script_py": script_py,
        "source_preflight_test_py": test_py,
        "source_preflight_heads": artifact_dir / "HEADS",
        "source_preflight_command": artifact_dir / "COMMAND",
        "source_preflight_stdout": artifact_dir / "stdout",
        "source_preflight_stderr": artifact_dir / "stderr",
        "source_preflight_run_exit": artifact_dir / "run.exit",
        "source_preflight_root_sha256s": artifact_dir / "SHA256SUMS",
    }.items():
        require(f"{name}_exists", path.is_file(), str(path), "file")

    expect("current_dp_head_fixed", current_dp_head, required_dp_head)
    expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD)
    expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main)
    expect("source_artifact_dp_head_fixed", HELPER_MODULE._kv(heads, "DP_HEAD", "dp_head"), required_dp_head)
    expect(
        "source_artifact_camp_matches_origin",
        HELPER_MODULE._kv(heads, "CAMP_HEAD", "camp_head"),
        HELPER_MODULE._kv(heads, "CAMP_ORIGIN_MAIN", "camp_origin_main"),
    )
    expect("source_preflight_run_exit", run_exit, "0")
    expect("audit_latest_status", HELPER_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_PREFLIGHT_STATUS)
    expect("audit_latest_next_work", HELPER_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK)
    expect("status_doc_latest_status", HELPER_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_PREFLIGHT_STATUS)
    expect("status_doc_latest_next_work", HELPER_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK)

    expect("source_preflight_schema", source_preflight.get("schema_version"), SOURCE_PREFLIGHT_SCHEMA)
    expect("source_preflight_passed", decision.get("passed"), True)
    expect("source_preflight_status", decision.get("status"), SOURCE_PREFLIGHT_STATUS)
    expect("source_preflight_failed_checks", decision.get("failed_checks"), [])
    expect("source_preflight_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK)
    expect("source_preflight_ready_flag", decision.get("objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_ready"), True)
    expect("source_preflight_static_review_authorized", decision.get("objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_static_review_authorized"), True)
    expect("source_preflight_executed", decision.get("actual_safetycost_delta_materialization_preflight_executed_by_this_gate"), True)
    expect("source_preflight_no_delta_materialization", decision.get("actual_safetycost_delta_materialization_executed_by_this_gate"), False)
    expect("source_preflight_no_delta_execution_auth", decision.get("actual_safetycost_delta_materialization_execution_authorized"), False)
    expect("source_preflight_no_candidate_index_replay", decision.get("candidate_index_replay_executed_by_this_gate"), False)
    expect("source_preflight_no_outcome_acquisition", decision.get("outcome_acquisition_executed_by_this_gate"), False)
    expect("source_preflight_actual_safetycost_available", decision.get("actual_safetycost_v1_available"), False)
    expect("source_preflight_claim_rule_evaluable", decision.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    expect("source_preflight_check_count", decision.get("check_count"), 104)
    expect("source_preflight_failed_check_count", decision.get("failed_check_count"), 0)
    expect("source_preflight_objective_required_records", summary.get("objective_required_records"), expected_record_count)
    expect("source_preflight_paired_record_key_count", summary.get("paired_record_key_count"), expected_record_count)
    expect("source_preflight_candidate_closed_loop_outcome_records", summary.get("candidate_closed_loop_outcome_records"), expected_record_count)
    expect("source_preflight_missing_candidate_closed_loop_outcome_records", summary.get("missing_candidate_closed_loop_outcome_records"), 0)
    expect("source_preflight_selection_log_count", summary.get("selection_log_count"), expected_selection_log_count)
    expect("source_preflight_no_go_failed_count", summary.get("no_go_failed_count"), 0)
    expect("contract_materialization_input_count", contract.get("materialization_input_count"), len(PREFLIGHT_MODULE.EXPECTED_MATERIALIZATION_INPUTS))
    expect("contract_preflight_step_count", contract.get("preflight_step_count"), len(PREFLIGHT_MODULE.EXPECTED_PREFLIGHT_STEPS))
    expect("contract_future_output_count", contract.get("future_output_count"), len(PREFLIGHT_MODULE.EXPECTED_FUTURE_OUTPUTS))
    expect("contract_no_go_count", contract.get("no_go_count"), len(PREFLIGHT_MODULE.EXPECTED_NO_GO))
    for action in BLOCKED_ACTIONS:
        expect(f"source_preflight_decision_{action}", decision.get(action), False)

    require("script_schema_constant", "SCHEMA_VERSION" in script_text and "delta_materialization_preflight_v1" in script_text)
    require("script_authorizes_static_review_only", "preflight_static_review_only" in script_text)
    require("script_source_preflight_only_boundary", "preflight_only" in script_text)
    require("script_keeps_no_claim_boundary", "safety_or_camp_over_dp_claim" in script_text)
    require("test_has_pass_case", "delta_materialization_preflight_passes" in test_text)
    require("test_has_enable_guard", "requires_enable" in test_text)
    require("test_has_hash_drift_guard", "rejects_plan_hash_drift" in test_text)

    _expect_sha(checks, "nested_preflight_json_sha", nested_sha256s, SOURCE_PREFLIGHT_JSON_NAME, preflight_json)
    _expect_sha(checks, "nested_preflight_md_sha", nested_sha256s, SOURCE_PREFLIGHT_MD_NAME, preflight_md)
    _expect_sha(checks, "root_preflight_json_sha", root_sha256s, f"preflight/{SOURCE_PREFLIGHT_JSON_NAME}", preflight_json)
    _expect_sha(checks, "root_preflight_md_sha", root_sha256s, f"preflight/{SOURCE_PREFLIGHT_MD_NAME}", preflight_md)
    _expect_sha(checks, "root_preflight_sha256s_sha", root_sha256s, "preflight/SHA256SUMS", preflight_sha256s)
    for name in ("HEADS", "COMMAND", "stdout", "stderr", "run.exit"):
        _expect_sha(checks, f"root_{name.lower().replace('.', '_')}_sha", root_sha256s, name, artifact_dir / name)
    return checks


def _source_preflight_summary(source_preflight: dict[str, Any]) -> dict[str, Any]:
    decision = HELPER_MODULE._dict(source_preflight.get("final_decision"))
    return {
        "schema_version": source_preflight.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "preflight_check_count": decision.get("check_count"),
        "failed_check_count": decision.get("failed_check_count"),
        "objective_required_records": decision.get("objective_required_records"),
        "paired_record_key_count": decision.get("paired_record_key_count"),
        "candidate_closed_loop_outcome_records": decision.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": decision.get("missing_candidate_closed_loop_outcome_records"),
        "selection_log_count": decision.get("selection_log_count"),
        "no_go_failed_count": decision.get("no_go_failed_count"),
    }


def _contract_summary(source_preflight: dict[str, Any]) -> dict[str, int]:
    return {
        "materialization_input_count": len(_list(source_preflight.get("materialization_inputs"))),
        "preflight_step_count": len(_list(source_preflight.get("preflight_steps"))),
        "future_output_count": len(_list(source_preflight.get("future_outputs"))),
        "no_go_count": len(_list(source_preflight.get("no_go_register"))),
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], source_preflight: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "static_review_enabled" in failed:
        failure_class = "explicit_candidate_index_delta_materialization_preflight_static_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_preflight_") for name in failed):
        failure_class = "source_delta_materialization_preflight_contract_failure"
    elif any(name.startswith(("nested_", "root_")) for name in failed):
        failure_class = "artifact_hash_contract_failure"
    else:
        failure_class = "candidate_index_delta_materialization_preflight_static_contract_failure"
    source_decision = HELPER_MODULE._dict(source_preflight.get("final_decision"))
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_static_review_passed": bool(passed),
        "objective_3200_candidate_index_actual_safetycost_delta_materialization_execution_authorized": bool(passed),
        "source_preflight_consumed_by_this_gate": True,
        "actual_safetycost_delta_materialization_preflight_executed_by_this_gate": False,
        "actual_safetycost_delta_materialization_execution_authorized": bool(passed),
        "actual_safetycost_delta_materialization_executed_by_this_gate": False,
        "candidate_index_replay_executed_by_this_gate": False,
        "outcome_acquisition_executed_by_this_gate": False,
        "actual_safetycost_v1_available": source_decision.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": source_decision.get("actual_safetycost_v1_claim_rule_evaluable"),
        "objective_required_records": source_decision.get("objective_required_records"),
        "paired_record_key_count": source_decision.get("paired_record_key_count"),
        "candidate_closed_loop_outcome_records": source_decision.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": source_decision.get("missing_candidate_closed_loop_outcome_records"),
        "selection_log_count": source_decision.get("selection_log_count"),
        "no_go_failed_count": source_decision.get("no_go_failed_count"),
        "closed_loop_outcome_training_or_online_input_authorized": False,
        "claim_supported_by_this_review": False,
        "promotion_supported_by_this_review": False,
        "direct_promotion_recommendation": False,
        "recommendation": "execute_candidate_index_actual_safetycost_delta_materialization_only" if passed else "repair_or_rerun_same_static_review_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    decision.update({name: False for name in BLOCKED_ACTIONS})
    return decision


def _source_hashes(
    *,
    artifact_dir: Path,
    preflight_json: Path,
    preflight_md: Path,
    preflight_sha256s: Path,
) -> dict[str, str | None]:
    return {
        "source_preflight_json_sha256": HELPER_MODULE._sha256(preflight_json),
        "source_preflight_md_sha256": HELPER_MODULE._sha256(preflight_md),
        "source_preflight_sha256s_sha256": HELPER_MODULE._sha256(preflight_sha256s),
        "source_preflight_root_sha256s_sha256": HELPER_MODULE._sha256(artifact_dir / "SHA256SUMS"),
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
    expected = HELPER_MODULE._sha256(path) if path.is_file() else None
    checks.append({"name": name, "passed": actual == expected, "actual": actual, "expected": expected})


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    json_path.write_text(
        json.dumps(HELPER_MODULE._stable(report), indent=2) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")
    sums = [f"{HELPER_MODULE._sha256(path)}  {path.name}" for path in (json_path, md_path)]
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_preflight_summary"]
    contract = report["contract_summary"]
    lines = [
        "# Objective-3200 Candidate-Index Actual-SafetyCost Delta-Materialization Preflight Static Review",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failure class: `{decision['failure_class']}`",
        f"- Checks / failed checks: `{decision['check_count']} / {decision['failed_check_count']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Preflight",
        "",
        f"- Source preflight checks / failed checks: `{source['preflight_check_count']} / {source['failed_check_count']}`",
        f"- Objective records / paired keys: `{source['objective_required_records']} / {source['paired_record_key_count']}`",
        f"- Candidate outcomes / missing: `{source['candidate_closed_loop_outcome_records']} / {source['missing_candidate_closed_loop_outcome_records']}`",
        f"- Selection logs / no-go failed count: `{source['selection_log_count']} / {source['no_go_failed_count']}`",
        "",
        "## Contract",
        "",
        f"- Materialization inputs / preflight steps / future outputs / no-go entries: `{contract['materialization_input_count']} / {contract['preflight_step_count']} / {contract['future_output_count']} / {contract['no_go_count']}`",
        "",
        "## Boundary",
        "",
        "- Static review only: no SafetyCost delta materialization, replay, outcome acquisition, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
        f"- Score expression: `{report['analysis']['score_expression']}`",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
