#!/usr/bin/env python3
"""Static review for the actual-SafetyCost outcome-materialization preflight."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_preflight_module():
    preflight_path = Path(__file__).resolve().with_name(
        "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_actual_safetycost_outcome_materialization.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization_preflight",
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
FALSE_EXECUTION_FLAGS = PREFLIGHT_MODULE.FALSE_EXECUTION_FLAGS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "actual_safetycost_outcome_materialization_preflight_static_review_v1"
)
AUTHORIZED_CURRENT_WORK = PREFLIGHT_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_preflight_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_preflight_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_execution_only"
)

REVIEW_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_preflight_static_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_preflight_static_review.md"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outcome_materialization_preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--outcome_materialization_preflight_json", type=Path, required=True)
    parser.add_argument("--outcome_materialization_preflight_md", type=Path, required=True)
    parser.add_argument("--outcome_materialization_preflight_sha256s", type=Path, required=True)
    parser.add_argument("--outcome_materialization_preflight_script_py", type=Path, required=True)
    parser.add_argument("--outcome_materialization_preflight_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization_preflight_static_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        outcome_materialization_preflight_artifact_dir=args.outcome_materialization_preflight_artifact_dir,
        outcome_materialization_preflight_json=args.outcome_materialization_preflight_json,
        outcome_materialization_preflight_md=args.outcome_materialization_preflight_md,
        outcome_materialization_preflight_sha256s=args.outcome_materialization_preflight_sha256s,
        outcome_materialization_preflight_script_py=args.outcome_materialization_preflight_script_py,
        outcome_materialization_preflight_test_py=args.outcome_materialization_preflight_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization_preflight_static_review
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(HELPER_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    outcome_materialization_preflight_artifact_dir: Path,
    outcome_materialization_preflight_json: Path,
    outcome_materialization_preflight_md: Path,
    outcome_materialization_preflight_sha256s: Path,
    outcome_materialization_preflight_script_py: Path,
    outcome_materialization_preflight_test_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = outcome_materialization_preflight_artifact_dir.resolve()
    preflight_json = outcome_materialization_preflight_json.resolve()
    preflight_md = outcome_materialization_preflight_md.resolve()
    preflight_sha256s = outcome_materialization_preflight_sha256s.resolve()
    script_py = outcome_materialization_preflight_script_py.resolve()
    test_py = outcome_materialization_preflight_test_py.resolve()
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
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "static_review_only": True,
            "read_only": True,
            "actual_safetycost_outcome_materialization_preflight_static_review_only": True,
            "actual_safetycost_outcome_materialization_execution": False,
            "actual_safetycost_outcome_materialization_executed": False,
            "paired_evaluation_execution": False,
            "replay_execution": False,
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
            "outcome_materialization_preflight_artifact_dir": str(artifact_dir),
            "outcome_materialization_preflight_json": str(preflight_json),
            "outcome_materialization_preflight_md": str(preflight_md),
            "outcome_materialization_preflight_sha256s": str(preflight_sha256s),
            "outcome_materialization_preflight_script_py": str(script_py),
            "outcome_materialization_preflight_test_py": str(test_py),
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
            "source_artifact_camp_head": heads.get("CAMP_HEAD"),
            "source_artifact_camp_origin_main": heads.get("CAMP_ORIGIN_MAIN"),
            "source_artifact_dp_head": heads.get("DP_HEAD"),
        },
        "source_preflight_summary": _source_preflight_summary(source_preflight),
        "source_static_review_summary": HELPER_MODULE._dict(source_preflight.get("source_static_review_summary")),
        "source_preflight_plan_summary": HELPER_MODULE._dict(source_preflight.get("source_preflight_plan_summary")),
        "preflight_scope_summary": HELPER_MODULE._dict(source_preflight.get("preflight_scope_summary")),
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
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    decision = HELPER_MODULE._dict(source_preflight.get("final_decision"))
    source_review = HELPER_MODULE._dict(source_preflight.get("source_static_review_summary"))
    source_plan = HELPER_MODULE._dict(source_preflight.get("source_preflight_plan_summary"))
    scope = HELPER_MODULE._dict(source_preflight.get("preflight_scope_summary"))

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
        require(f"{name}_exists", path.is_file())

    expect("current_dp_head_fixed", current_dp_head, required_dp_head)
    expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD)
    expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main)
    expect("source_artifact_dp_head_fixed", heads.get("DP_HEAD"), required_dp_head)
    expect("source_artifact_camp_matches_origin", heads.get("CAMP_HEAD"), heads.get("CAMP_ORIGIN_MAIN"))
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
    expect("source_preflight_ready", decision.get("post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_outcome_materialization_preflight_ready"), True)
    expect("source_preflight_static_review_authorized", decision.get("post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_outcome_materialization_preflight_static_review_authorized"), True)
    expect("source_preflight_executed", decision.get("actual_safetycost_outcome_materialization_preflight_executed_by_this_gate"), True)
    expect("source_preflight_execution_not_authorized", decision.get("actual_safetycost_outcome_materialization_execution_authorized"), False)
    expect("source_preflight_no_outcome_materialization", decision.get("actual_safetycost_outcome_materialization_executed_by_this_gate"), False)
    expect("source_preflight_no_paired_execution", decision.get("paired_evaluation_executed_by_this_gate"), False)
    expect("source_preflight_no_closed_loop_training_input", decision.get("closed_loop_outcome_training_or_online_input_authorized"), False)
    expect("source_preflight_actual_safetycost_available", decision.get("actual_safetycost_v1_available"), False)
    expect("source_preflight_claim_rule_evaluable", decision.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    for action in BLOCKED_ACTIONS:
        expect(f"source_preflight_decision_{action}", decision.get(action), False)
    for flag in FALSE_EXECUTION_FLAGS:
        expect(f"source_preflight_decision_{flag}", decision.get(flag), False)

    expect("source_preflight_check_count", len(_list(source_preflight.get("preflight_checks"))), 76)
    expect("source_static_review_check_count", source_review.get("static_review_check_count"), 82)
    expect("source_static_review_failed_count", source_review.get("failed_check_count"), 0)
    expect("source_plan_preflight_check_count", source_plan.get("preflight_plan_check_count"), 74)
    expect("source_plan_failed_check_count", source_plan.get("failed_check_count"), 0)
    expect("source_paired_record_count", source_plan.get("source_paired_record_count"), 3200)
    expect("source_shadow_diff_records", source_plan.get("source_shadow_diff_records"), 2832)
    expect("scope_actual_safetycost_available", scope.get("actual_safetycost_v1_available"), False)
    expect("scope_claim_rule_evaluable", scope.get("actual_safetycost_v1_claim_rule_evaluable"), False)
    expect("scope_materialization_scope", scope.get("planned_materialization_scope"), "shadow-selected run-level closed-loop outcome summaries only")
    expect("scope_closed_loop_training_input", scope.get("closed_loop_outcomes_training_or_online_input"), False)
    expect("materialization_input_names", [item.get("name") for item in _list(source_preflight.get("materialization_inputs"))], list(PREFLIGHT_MODULE.EXPECTED_MATERIALIZATION_INPUTS))
    expect("preflight_step_names", [item.get("name") for item in _list(source_preflight.get("preflight_steps"))], list(PREFLIGHT_MODULE.EXPECTED_PREFLIGHT_STEPS))
    expect("preflight_steps_no_materialization", sorted({item.get("materializes_outcomes") for item in _list(source_preflight.get("preflight_steps"))}), [False])
    expect("future_output_names", [item.get("name") for item in _list(source_preflight.get("future_outputs"))], list(PREFLIGHT_MODULE.EXPECTED_FUTURE_OUTPUTS))
    expect("no_go_names", [item.get("name") for item in _list(source_preflight.get("no_go_register"))], list(PREFLIGHT_MODULE.EXPECTED_NO_GO))

    _expect_sha(checks, "nested_preflight_json_sha", nested_sha256s, preflight_json.name, preflight_json)
    _expect_sha(checks, "nested_preflight_md_sha", nested_sha256s, preflight_md.name, preflight_md)
    _expect_sha(checks, "root_preflight_json_sha", root_sha256s, f"./preflight/{preflight_json.name}", preflight_json)
    _expect_sha(checks, "root_preflight_md_sha", root_sha256s, f"./preflight/{preflight_md.name}", preflight_md)
    _expect_sha(checks, "root_preflight_sha256s_sha", root_sha256s, "./preflight/SHA256SUMS", preflight_sha256s)
    checks.extend(_source_surface_checks(script_text, test_text))
    return checks


def _source_surface_checks(script_text: str, test_text: str) -> list[dict[str, Any]]:
    script_tokens = [
        "actual_safetycost_outcome_materialization_preflight_only",
        "actual_safetycost_outcome_materialization_execution_authorized",
        "materializes_outcomes",
        "score_expression",
    ]
    test_tokens = [
        "test_actual_safetycost_outcome_materialization_preflight_passes",
        "test_actual_safetycost_outcome_materialization_preflight_rejects_source_claim_leak",
        "test_actual_safetycost_outcome_materialization_preflight_rejects_hash_drift",
        "test_actual_safetycost_outcome_materialization_preflight_requires_enable",
    ]
    return [
        {"name": f"preflight_script_contains_{index}", "passed": token in script_text, "actual": token if token in script_text else "missing", "expected": token}
        for index, token in enumerate(script_tokens, start=1)
    ] + [
        {"name": f"preflight_test_contains_{index}", "passed": token in test_text, "actual": token if token in test_text else "missing", "expected": token}
        for index, token in enumerate(test_tokens, start=1)
    ]


def _source_preflight_summary(source_preflight: dict[str, Any]) -> dict[str, Any]:
    decision = HELPER_MODULE._dict(source_preflight.get("final_decision"))
    return {
        "schema_version": source_preflight.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "preflight_check_count": len(_list(source_preflight.get("preflight_checks"))),
        "failed_check_count": len(_list(decision.get("failed_checks"))),
        "actual_safetycost_outcome_materialization_preflight_executed_by_this_gate": decision.get("actual_safetycost_outcome_materialization_preflight_executed_by_this_gate"),
        "actual_safetycost_outcome_materialization_execution_authorized": decision.get("actual_safetycost_outcome_materialization_execution_authorized"),
        "actual_safetycost_outcome_materialization_executed_by_this_gate": decision.get("actual_safetycost_outcome_materialization_executed_by_this_gate"),
    }


def _contract_summary(source_preflight: dict[str, Any]) -> dict[str, Any]:
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
        failure_class = "explicit_actual_safetycost_outcome_materialization_preflight_static_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_preflight_") for name in failed):
        failure_class = "source_preflight_contract_failure"
    elif any(name.startswith(("source_", "scope_")) for name in failed):
        failure_class = "source_preflight_scope_contract_failure"
    elif any(name.startswith(("nested_", "root_", "artifact_")) for name in failed):
        failure_class = "artifact_hash_contract_failure"
    else:
        failure_class = "static_review_contract_failure"
    source_decision = HELPER_MODULE._dict(source_preflight.get("final_decision"))
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_outcome_materialization_preflight_static_review_passed": bool(passed),
        "actual_safetycost_outcome_materialization_execution_authorized": bool(passed),
        "actual_safetycost_outcome_materialization_executed_by_this_gate": False,
        "paired_evaluation_executed_by_this_gate": False,
        "source_preflight_consumed_by_this_gate": True,
        "actual_safetycost_v1_available": source_decision.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": source_decision.get("actual_safetycost_v1_claim_rule_evaluable"),
        "closed_loop_outcome_training_or_online_input_authorized": False,
        "previous_no_promotion_closeout_preserved": True,
        "direct_promotion_recommendation": False,
        "recommendation": "execute_actual_safetycost_outcome_materialization_only" if passed else "repair_or_rerun_same_static_review_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def _source_hashes(*, artifact_dir: Path, preflight_json: Path, preflight_md: Path, preflight_sha256s: Path) -> dict[str, Any]:
    return {
        "preflight_json_sha256": HELPER_MODULE._sha256(preflight_json),
        "preflight_md_sha256": HELPER_MODULE._sha256(preflight_md),
        "preflight_sha256s_sha256": HELPER_MODULE._sha256(preflight_sha256s),
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
    summary = report["source_preflight_summary"]
    contract = report["contract_summary"]
    scope = report["preflight_scope_summary"]
    lines = [
        "# v14 Actual-SafetyCost Outcome-Materialization Preflight Static Review",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Preflight",
        "",
        f"- Preflight checks: `{summary['preflight_check_count']}`",
        f"- Failed checks: `{summary['failed_check_count']}`",
        f"- Materialization inputs / preflight steps / future outputs / no-go entries: `{contract['materialization_input_count']} / {contract['preflight_step_count']} / {contract['future_output_count']} / {contract['no_go_count']}`",
        "",
        "## Preflight Scope",
        "",
        f"- Actual SafetyCost v1 available: `{scope.get('actual_safetycost_v1_available')}`",
        f"- Claim rule evaluable: `{scope.get('actual_safetycost_v1_claim_rule_evaluable')}`",
        f"- Planned materialization scope: `{scope.get('planned_materialization_scope')}`",
        f"- Closed-loop outcomes used for training or online input: `{scope.get('closed_loop_outcomes_training_or_online_input')}`",
        "",
        "## Boundary",
        "",
        "- Static review only: no outcome materialization, replay, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
        f"- Score expression: `{report['analysis']['score_expression']}`",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
