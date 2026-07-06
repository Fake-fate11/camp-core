#!/usr/bin/env python3
"""Static review for the objective-3200 candidate-index outcome preflight plan."""

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
        "replay_outcome_acquisition_preflight.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan",
        plan_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PLAN_MODULE = _load_plan_module()

FIXED_DP_HEAD = PLAN_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = PLAN_MODULE.SCORE_EXPRESSION
SOURCE_PLAN_SCHEMA = PLAN_MODULE.SCHEMA_VERSION
SOURCE_PLAN_STATUS = PLAN_MODULE.READY_STATUS
SOURCE_PLAN_JSON_NAME = PLAN_MODULE.PLAN_JSON_NAME
SOURCE_PLAN_MD_NAME = PLAN_MODULE.PLAN_MD_NAME
OBJECTIVE_REQUIRED_RECORDS = PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS
EXPECTED_PREFLIGHT_PLAN_ITEMS = PLAN_MODULE.EXPECTED_PREFLIGHT_PLAN_ITEMS
EXPECTED_NO_GO = PLAN_MODULE.EXPECTED_NO_GO
BLOCKED_ACTIONS = PLAN_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = PLAN_MODULE.FALSE_EXECUTION_FLAGS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_v1"
)
AUTHORIZED_CURRENT_WORK = PLAN_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_plan_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_plan_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_only"
)

REVIEW_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_plan_static_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_plan_static_review.md"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--preflight_plan_json", type=Path, required=True)
    parser.add_argument("--preflight_plan_md", type=Path, required=True)
    parser.add_argument("--preflight_plan_sha256s", type=Path, required=True)
    parser.add_argument("--plan_script_py", type=Path, required=True)
    parser.add_argument("--plan_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_static_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        preflight_plan_artifact_dir=args.preflight_plan_artifact_dir,
        preflight_plan_json=args.preflight_plan_json,
        preflight_plan_md=args.preflight_plan_md,
        preflight_plan_sha256s=args.preflight_plan_sha256s,
        plan_script_py=args.plan_script_py,
        plan_test_py=args.plan_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_static_review
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(PLAN_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    preflight_plan_artifact_dir: Path,
    preflight_plan_json: Path,
    preflight_plan_md: Path,
    preflight_plan_sha256s: Path,
    plan_script_py: Path,
    plan_test_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = preflight_plan_artifact_dir.resolve()
    paths = {
        "preflight_plan_json": preflight_plan_json.resolve(),
        "preflight_plan_md": preflight_plan_md.resolve(),
        "preflight_plan_sha256s": preflight_plan_sha256s.resolve(),
        "plan_script_py": plan_script_py.resolve(),
        "plan_test_py": plan_test_py.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    artifact_files = {
        "heads": artifact_dir / "HEADS",
        "command": artifact_dir / "COMMAND",
        "stdout": artifact_dir / "stdout",
        "stderr": artifact_dir / "stderr",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "plan_json": artifact_dir / "plan" / SOURCE_PLAN_JSON_NAME,
        "plan_md": artifact_dir / "plan" / SOURCE_PLAN_MD_NAME,
        "plan_sha256s": artifact_dir / "plan" / "SHA256SUMS",
    }
    source_plan = PLAN_MODULE._read_json_dict(paths["preflight_plan_json"])
    v14_text = PLAN_MODULE._read_text(paths["v14_audit_md"])
    status_text = PLAN_MODULE._read_text(paths["current_status_md"])
    heads = PLAN_MODULE._parse_key_values(PLAN_MODULE._read_text(artifact_files["heads"]))
    root_sha256s = PLAN_MODULE._read_sha256sums(artifact_files["root_sha256s"])
    nested_sha256s = PLAN_MODULE._read_sha256sums(paths["preflight_plan_sha256s"])
    run_exit = PLAN_MODULE._read_text(artifact_files["run_exit"]).strip()
    script_text = PLAN_MODULE._read_text(paths["plan_script_py"])
    test_text = PLAN_MODULE._read_text(paths["plan_test_py"])
    source_summary = _source_plan_summary(source_plan)
    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        paths=paths,
        artifact_files=artifact_files,
        source_plan=source_plan,
        source_summary=source_summary,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        run_exit=run_exit,
        script_text=script_text,
        test_text=test_text,
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
            "preflight_plan_static_review_only": True,
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
            "preflight_plan_artifact_dir": str(artifact_dir),
            "output_dir": str(output_dir.resolve()),
            **{name: str(path) for name, path in paths.items()},
        },
        "source_hashes": {
            name: PLAN_MODULE._sha256(path)
            for name, path in {**paths, **artifact_files}.items()
            if path.is_file()
        },
        "source_plan_summary": source_summary,
        "static_review_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, source_summary=source_summary),
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    paths: dict[str, Path],
    artifact_files: dict[str, Path],
    source_plan: dict[str, Any],
    source_summary: dict[str, Any],
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    run_exit: str,
    script_text: str,
    test_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
) -> list[dict[str, Any]]:
    decision = PLAN_MODULE._dict(source_plan.get("final_decision"))
    analysis = PLAN_MODULE._dict(source_plan.get("analysis"))
    protocol = PLAN_MODULE._dict(source_plan.get("strict_pairing_and_metrics_protocol"))
    artifact_contract = PLAN_MODULE._dict(source_plan.get("artifact_contract"))
    plan_items = [
        PLAN_MODULE._dict(item).get("name")
        for item in source_plan.get("outcome_acquisition_preflight_plan", [])
    ]
    no_go_names = [
        PLAN_MODULE._dict(item).get("name")
        for item in source_plan.get("no_go_register", [])
    ]
    checks = [
        PLAN_MODULE._expect("static_review_enabled", enabled, True),
        PLAN_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        PLAN_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        PLAN_MODULE._expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        PLAN_MODULE._check("current_camp_head_is_sha", PLAN_MODULE._is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        PLAN_MODULE._expect("audit_latest_status", PLAN_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_PLAN_STATUS),
        PLAN_MODULE._expect("audit_latest_next_work", PLAN_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._expect("status_doc_latest_status", PLAN_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_PLAN_STATUS),
        PLAN_MODULE._expect("status_doc_latest_next_work", PLAN_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._check("source_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
        PLAN_MODULE._expect("source_artifact_run_exit_zero", run_exit, "0"),
        PLAN_MODULE._expect("source_artifact_dp_head_fixed", PLAN_MODULE._kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
        PLAN_MODULE._expect(
            "source_artifact_camp_head_matches_origin",
            PLAN_MODULE._kv(heads, "CAMP_HEAD", "camp_head"),
            PLAN_MODULE._kv(heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main"),
        ),
    ]
    for name, path in paths.items():
        checks.extend(PLAN_MODULE._path_checks(name, path, allow_empty=False))
    for name, path in artifact_files.items():
        checks.extend(PLAN_MODULE._path_checks(f"artifact_{name}", path, allow_empty=(name == "stderr")))
    checks.extend(_artifact_hash_checks(artifact_files, root_sha256s, nested_sha256s))
    checks.extend(
        [
            PLAN_MODULE._expect("plan_json_matches_artifact_layout", paths["preflight_plan_json"], artifact_files["plan_json"].resolve()),
            PLAN_MODULE._expect("plan_md_matches_artifact_layout", paths["preflight_plan_md"], artifact_files["plan_md"].resolve()),
            PLAN_MODULE._expect("plan_sha256s_matches_artifact_layout", paths["preflight_plan_sha256s"], artifact_files["plan_sha256s"].resolve()),
            PLAN_MODULE._expect("source_plan_schema", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA),
            PLAN_MODULE._expect("source_plan_passed", decision.get("passed"), True),
            PLAN_MODULE._expect("source_plan_status", decision.get("status"), SOURCE_PLAN_STATUS),
            PLAN_MODULE._expect("source_plan_authorized_next", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
            PLAN_MODULE._expect("source_plan_static_review_authorized", decision.get("objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_authorized"), True),
            PLAN_MODULE._expect("source_plan_harness_implemented", decision.get("candidate_index_replay_harness_implemented"), True),
            PLAN_MODULE._expect("source_plan_harness_execution_authorized", decision.get("candidate_index_replay_harness_execution_authorized"), False),
            PLAN_MODULE._expect("source_plan_direct_candidate_index_replay", decision.get("direct_candidate_index_replay_execution_authorized"), False),
            PLAN_MODULE._expect("source_plan_direct_outcome_acquisition", decision.get("direct_outcome_acquisition_execution_authorized"), False),
            PLAN_MODULE._expect("source_plan_actual_safetycost_available", decision.get("actual_safetycost_v1_available"), False),
            PLAN_MODULE._expect("source_analysis_read_only", analysis.get("read_only"), True),
            PLAN_MODULE._expect("source_analysis_plan_only", analysis.get("plan_only"), True),
            PLAN_MODULE._expect("source_analysis_preflight_plan_only", analysis.get("candidate_index_replay_outcome_acquisition_preflight_plan_only"), True),
            PLAN_MODULE._expect("source_analysis_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
            PLAN_MODULE._expect("source_objective_required_records", source_summary["objective_required_records"], OBJECTIVE_REQUIRED_RECORDS),
            PLAN_MODULE._expect("source_candidate_outcome_records", source_summary["candidate_closed_loop_outcome_records"], 0),
            PLAN_MODULE._expect("source_missing_outcome_records", source_summary["missing_candidate_closed_loop_outcome_records"], OBJECTIVE_REQUIRED_RECORDS),
            PLAN_MODULE._expect("source_plan_items", plan_items, list(EXPECTED_PREFLIGHT_PLAN_ITEMS)),
            PLAN_MODULE._expect("source_no_go_names", no_go_names, list(EXPECTED_NO_GO)),
            PLAN_MODULE._expect("strict_protocol_required_rows", protocol.get("required_rows"), OBJECTIVE_REQUIRED_RECORDS),
            PLAN_MODULE._check("strict_protocol_exact_pairing_rule", "exactly_3200_strict_pairs" in protocol.get("pass_fail_criteria", [])),
            PLAN_MODULE._expect("artifact_contract_next_gate", artifact_contract.get("next_gate"), AUTHORIZED_CURRENT_WORK),
            PLAN_MODULE._expect("artifact_contract_preflight_execution", artifact_contract.get("preflight_execution_authorized_by_this_gate"), False),
            PLAN_MODULE._expect("artifact_contract_replay_execution", artifact_contract.get("replay_execution_authorized_by_this_gate"), False),
            PLAN_MODULE._expect("artifact_contract_outcome_acquisition", artifact_contract.get("outcome_acquisition_authorized_by_this_gate"), False),
            PLAN_MODULE._check(
                "plan_script_schema_present",
                "SCHEMA_VERSION" in script_text
                and "candidate_index_replay_outcome_acquisition_preflight_plan_v1" in script_text,
            ),
            PLAN_MODULE._check("plan_test_exercises_hash_drift", "rejects_hash_drift" in test_text),
        ]
    )
    for action in BLOCKED_ACTIONS:
        checks.append(PLAN_MODULE._expect(f"source_plan_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        checks.append(PLAN_MODULE._expect(f"source_plan_{flag}", bool(decision.get(flag, False)), False))
    return checks


def _artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._expect("root_heads_sha", PLAN_MODULE._sha_for_suffix(root_sha256s, "HEADS"), PLAN_MODULE._sha256(artifact_files["heads"])),
        PLAN_MODULE._expect("root_command_sha", PLAN_MODULE._sha_for_suffix(root_sha256s, "COMMAND"), PLAN_MODULE._sha256(artifact_files["command"])),
        PLAN_MODULE._expect("root_stdout_sha", PLAN_MODULE._sha_for_suffix(root_sha256s, "stdout"), PLAN_MODULE._sha256(artifact_files["stdout"])),
        PLAN_MODULE._expect("root_stderr_sha", PLAN_MODULE._sha_for_suffix(root_sha256s, "stderr"), PLAN_MODULE._sha256(artifact_files["stderr"])),
        PLAN_MODULE._expect("root_run_exit_sha", PLAN_MODULE._sha_for_suffix(root_sha256s, "run.exit"), PLAN_MODULE._sha256(artifact_files["run_exit"])),
        PLAN_MODULE._expect("root_plan_json_sha", PLAN_MODULE._sha_for_suffix(root_sha256s, f"plan/{SOURCE_PLAN_JSON_NAME}"), PLAN_MODULE._sha256(artifact_files["plan_json"])),
        PLAN_MODULE._expect("root_plan_md_sha", PLAN_MODULE._sha_for_suffix(root_sha256s, f"plan/{SOURCE_PLAN_MD_NAME}"), PLAN_MODULE._sha256(artifact_files["plan_md"])),
        PLAN_MODULE._expect("root_plan_sha256s_sha", PLAN_MODULE._sha_for_suffix(root_sha256s, "plan/SHA256SUMS"), PLAN_MODULE._sha256(artifact_files["plan_sha256s"])),
        PLAN_MODULE._expect("nested_plan_json_sha", PLAN_MODULE._sha_for_suffix(nested_sha256s, SOURCE_PLAN_JSON_NAME), PLAN_MODULE._sha256(artifact_files["plan_json"])),
        PLAN_MODULE._expect("nested_plan_md_sha", PLAN_MODULE._sha_for_suffix(nested_sha256s, SOURCE_PLAN_MD_NAME), PLAN_MODULE._sha256(artifact_files["plan_md"])),
    ]


def _source_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = PLAN_MODULE._dict(source_plan.get("final_decision"))
    source = PLAN_MODULE._dict(source_plan.get("source_static_review_summary"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "objective_required_records": int(decision.get("objective_required_records") or 0),
        "candidate_closed_loop_outcome_records": int(decision.get("candidate_closed_loop_outcome_records") or 0),
        "missing_candidate_closed_loop_outcome_records": int(
            decision.get("missing_candidate_closed_loop_outcome_records") or 0
        ),
        "source_static_review_status": source.get("status"),
    }


def _decision(
    *,
    passed: bool,
    checks: list[dict[str, Any]],
    source_summary: dict[str, Any],
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "static_review_enabled" in failed:
        failure_class = "explicit_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_plan_") for name in failed):
        failure_class = "source_preflight_plan_contract_failure"
    elif any("sha" in name for name in failed):
        failure_class = "source_preflight_plan_hash_mismatch"
    else:
        failure_class = "candidate_index_replay_outcome_acquisition_preflight_plan_static_review_contract_failure"
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_passed": bool(passed),
        "objective_3200_candidate_index_replay_outcome_acquisition_preflight_authorized": bool(passed),
        "objective_required_records": source_summary["objective_required_records"],
        "candidate_closed_loop_outcome_records": source_summary["candidate_closed_loop_outcome_records"],
        "missing_candidate_closed_loop_outcome_records": source_summary["missing_candidate_closed_loop_outcome_records"],
        "candidate_index_replay_harness_implemented": bool(passed),
        "candidate_index_replay_harness_execution_authorized": False,
        "direct_candidate_index_replay_execution_authorized": False,
        "direct_outcome_acquisition_execution_authorized": False,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    json_path.write_text(json.dumps(PLAN_MODULE._stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        "\n".join(
            [
                f"{PLAN_MODULE._sha256(json_path)}  {json_path.name}",
                f"{PLAN_MODULE._sha256(md_path)}  {md_path.name}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_plan_summary"]
    return "\n".join(
        [
            "# Objective-3200 Candidate-Index Replay Outcome-Acquisition Preflight Plan Static Review",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
            "## Source Plan",
            "",
            f"- Objective records: `{source['objective_required_records']}`",
            f"- Candidate outcome records: `{source['candidate_closed_loop_outcome_records']}`",
            f"- Missing outcome records: `{source['missing_candidate_closed_loop_outcome_records']}`",
            "",
            "This gate authorizes only the future preflight gate; it does not run replay or acquire outcomes.",
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
