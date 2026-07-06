#!/usr/bin/env python3
"""Static review for objective-3200 candidate-index outcome preflight."""

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
        "replay_outcome_acquisition.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_replay_outcome_acquisition_preflight",
        preflight_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PREFLIGHT_MODULE = _load_preflight_module()
PLAN_MODULE = PREFLIGHT_MODULE.PLAN_MODULE

FIXED_DP_HEAD = PREFLIGHT_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = PREFLIGHT_MODULE.SCORE_EXPRESSION
SOURCE_PREFLIGHT_SCHEMA = PREFLIGHT_MODULE.SCHEMA_VERSION
SOURCE_PREFLIGHT_STATUS = PREFLIGHT_MODULE.READY_STATUS
SOURCE_PREFLIGHT_JSON_NAME = PREFLIGHT_MODULE.PREFLIGHT_JSON_NAME
SOURCE_PREFLIGHT_MD_NAME = PREFLIGHT_MODULE.PREFLIGHT_MD_NAME
BLOCKED_ACTIONS = PREFLIGHT_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = PREFLIGHT_MODULE.FALSE_EXECUTION_FLAGS
OBJECTIVE_REQUIRED_RECORDS = PREFLIGHT_MODULE.OBJECTIVE_REQUIRED_RECORDS
EXPECTED_PREFLIGHT_ITEM_COUNT = len(PREFLIGHT_MODULE.EXPECTED_PREFLIGHT_ITEMS)
EXPECTED_PLANNED_OUTPUT_COUNT = len(PREFLIGHT_MODULE.EXPECTED_PLANNED_OUTPUTS)
EXPECTED_NO_GO_COUNT = len(PREFLIGHT_MODULE.PREFLIGHT_NO_GO)

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_replay_outcome_acquisition_preflight_static_review_v1"
)
AUTHORIZED_CURRENT_WORK = PREFLIGHT_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_execution_only"
)

REVIEW_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_static_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_static_review.md"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate_index_outcome_preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--candidate_index_outcome_preflight_json", type=Path, required=True)
    parser.add_argument("--candidate_index_outcome_preflight_md", type=Path, required=True)
    parser.add_argument("--candidate_index_outcome_preflight_sha256s", type=Path, required=True)
    parser.add_argument("--candidate_index_outcome_preflight_script_py", type=Path, required=True)
    parser.add_argument("--candidate_index_outcome_preflight_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_preflight_static_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        candidate_index_outcome_preflight_artifact_dir=args.candidate_index_outcome_preflight_artifact_dir,
        candidate_index_outcome_preflight_json=args.candidate_index_outcome_preflight_json,
        candidate_index_outcome_preflight_md=args.candidate_index_outcome_preflight_md,
        candidate_index_outcome_preflight_sha256s=args.candidate_index_outcome_preflight_sha256s,
        candidate_index_outcome_preflight_script_py=args.candidate_index_outcome_preflight_script_py,
        candidate_index_outcome_preflight_test_py=args.candidate_index_outcome_preflight_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_preflight_static_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(PLAN_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    candidate_index_outcome_preflight_artifact_dir: Path,
    candidate_index_outcome_preflight_json: Path,
    candidate_index_outcome_preflight_md: Path,
    candidate_index_outcome_preflight_sha256s: Path,
    candidate_index_outcome_preflight_script_py: Path,
    candidate_index_outcome_preflight_test_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = candidate_index_outcome_preflight_artifact_dir.resolve()
    paths = {
        "candidate_index_outcome_preflight_json": candidate_index_outcome_preflight_json.resolve(),
        "candidate_index_outcome_preflight_md": candidate_index_outcome_preflight_md.resolve(),
        "candidate_index_outcome_preflight_sha256s": candidate_index_outcome_preflight_sha256s.resolve(),
        "candidate_index_outcome_preflight_script_py": candidate_index_outcome_preflight_script_py.resolve(),
        "candidate_index_outcome_preflight_test_py": candidate_index_outcome_preflight_test_py.resolve(),
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
        "preflight_json": artifact_dir / "preflight" / SOURCE_PREFLIGHT_JSON_NAME,
        "preflight_md": artifact_dir / "preflight" / SOURCE_PREFLIGHT_MD_NAME,
        "preflight_sha256s": artifact_dir / "preflight" / "SHA256SUMS",
    }
    source_preflight = PLAN_MODULE._read_json_dict(paths["candidate_index_outcome_preflight_json"])
    v14_text = PLAN_MODULE._read_text(paths["v14_audit_md"])
    status_text = PLAN_MODULE._read_text(paths["current_status_md"])
    script_text = PLAN_MODULE._read_text(paths["candidate_index_outcome_preflight_script_py"])
    test_text = PLAN_MODULE._read_text(paths["candidate_index_outcome_preflight_test_py"])
    heads = PLAN_MODULE._parse_key_values(PLAN_MODULE._read_text(artifact_files["heads"]))
    root_sha256s = PLAN_MODULE._read_sha256sums(artifact_files["root_sha256s"])
    nested_sha256s = PLAN_MODULE._read_sha256sums(paths["candidate_index_outcome_preflight_sha256s"])
    run_exit = PLAN_MODULE._read_text(artifact_files["run_exit"]).strip()
    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        paths=paths,
        artifact_files=artifact_files,
        source_preflight=source_preflight,
        v14_text=v14_text,
        status_text=status_text,
        script_text=script_text,
        test_text=test_text,
        heads=heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        run_exit=run_exit,
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
            "objective_3200_candidate_index_replay_outcome_acquisition_preflight_static_review_only": True,
            "candidate_index_replay_execution": False,
            "outcome_acquisition_execution": False,
            "outcome_acquisition_executed": False,
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
            "candidate_index_outcome_preflight_artifact_dir": str(artifact_dir),
            **{name: str(path) for name, path in paths.items()},
            "output_dir": str(output_dir.resolve()),
        },
        "source_artifact_hashes": {
            "root_sha256s": PLAN_MODULE._sha256(artifact_files["root_sha256s"]),
            "preflight_json": PLAN_MODULE._sha256(paths["candidate_index_outcome_preflight_json"]),
            "preflight_md": PLAN_MODULE._sha256(paths["candidate_index_outcome_preflight_md"]),
            "preflight_sha256s": PLAN_MODULE._sha256(paths["candidate_index_outcome_preflight_sha256s"]),
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_preflight_camp_head": PLAN_MODULE._kv(heads, "CAMP_HEAD", "camp_head"),
            "source_preflight_camp_origin_main": PLAN_MODULE._kv(
                heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main"
            ),
            "source_preflight_dp_head": PLAN_MODULE._kv(heads, "DP_HEAD", "dp_head"),
        },
        "source_preflight_summary": _source_preflight_summary(source_preflight),
        "static_review_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, source_preflight=source_preflight),
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    paths: dict[str, Path],
    artifact_files: dict[str, Path],
    source_preflight: dict[str, Any],
    v14_text: str,
    status_text: str,
    script_text: str,
    test_text: str,
    heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    run_exit: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
) -> list[dict[str, Any]]:
    decision = PLAN_MODULE._dict(source_preflight.get("final_decision"))
    analysis = PLAN_MODULE._dict(source_preflight.get("analysis"))
    summary = _source_preflight_summary(source_preflight)
    future_contract = PLAN_MODULE._dict(source_preflight.get("future_execution_contract"))
    checks = [
        PLAN_MODULE._expect("static_review_enabled", enabled, True),
        PLAN_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        PLAN_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        PLAN_MODULE._expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        PLAN_MODULE._check("current_camp_head_is_sha", PLAN_MODULE._is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        PLAN_MODULE._expect("audit_latest_status", PLAN_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_PREFLIGHT_STATUS),
        PLAN_MODULE._expect("audit_latest_next_work", PLAN_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._expect("status_doc_latest_status", PLAN_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_PREFLIGHT_STATUS),
        PLAN_MODULE._expect("status_doc_latest_next_work", PLAN_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._check("candidate_index_outcome_preflight_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(PLAN_MODULE._path_checks(name, path, allow_empty=False))
    for name, path in artifact_files.items():
        checks.extend(PLAN_MODULE._path_checks(f"artifact_{name}", path, allow_empty=name == "stderr"))
    checks.extend(
        [
            PLAN_MODULE._expect("preflight_json_matches_artifact_layout", paths["candidate_index_outcome_preflight_json"], artifact_files["preflight_json"].resolve()),
            PLAN_MODULE._expect("preflight_md_matches_artifact_layout", paths["candidate_index_outcome_preflight_md"], artifact_files["preflight_md"].resolve()),
            PLAN_MODULE._expect("preflight_sha256s_matches_artifact_layout", paths["candidate_index_outcome_preflight_sha256s"], artifact_files["preflight_sha256s"].resolve()),
            PLAN_MODULE._expect("source_preflight_run_exit", run_exit, "0"),
            PLAN_MODULE._expect("source_preflight_schema", source_preflight.get("schema_version"), SOURCE_PREFLIGHT_SCHEMA),
            PLAN_MODULE._expect("source_preflight_passed", decision.get("passed"), True),
            PLAN_MODULE._expect("source_preflight_status", decision.get("status"), SOURCE_PREFLIGHT_STATUS),
            PLAN_MODULE._expect("source_preflight_authorized_next", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
            PLAN_MODULE._expect("source_preflight_ready", decision.get("objective_3200_candidate_index_replay_outcome_acquisition_preflight_ready"), True),
            PLAN_MODULE._expect("source_preflight_static_review_authorized", decision.get("objective_3200_candidate_index_replay_outcome_acquisition_preflight_static_review_authorized"), True),
            PLAN_MODULE._expect("source_preflight_harness_implemented", decision.get("candidate_index_replay_harness_implemented"), True),
            PLAN_MODULE._expect("source_preflight_harness_execution_authorized", decision.get("candidate_index_replay_harness_execution_authorized"), False),
            PLAN_MODULE._expect("source_preflight_direct_candidate_index_replay", decision.get("direct_candidate_index_replay_execution_authorized"), False),
            PLAN_MODULE._expect("source_preflight_direct_outcome_acquisition", decision.get("direct_outcome_acquisition_execution_authorized"), False),
            PLAN_MODULE._expect("source_preflight_read_only", analysis.get("read_only"), True),
            PLAN_MODULE._expect("source_preflight_preflight_only", analysis.get("preflight_only"), True),
            PLAN_MODULE._expect("source_preflight_candidate_index_preflight_only", analysis.get("candidate_index_replay_outcome_acquisition_preflight_only"), True),
            PLAN_MODULE._expect("source_preflight_candidate_index_replay_execution", analysis.get("candidate_index_replay_execution"), False),
            PLAN_MODULE._expect("source_preflight_outcome_acquisition_execution", analysis.get("outcome_acquisition_execution"), False),
            PLAN_MODULE._expect("source_preflight_training_execution", analysis.get("training_execution"), False),
            PLAN_MODULE._expect("source_preflight_candidate_generation", analysis.get("candidate_generation"), False),
            PLAN_MODULE._expect("source_preflight_dp_modification", analysis.get("dp_modification"), False),
            PLAN_MODULE._expect("source_preflight_candidate_tensor_modification", analysis.get("candidate_tensor_modification"), False),
            PLAN_MODULE._expect("source_preflight_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
            PLAN_MODULE._expect("source_preflight_dp_head_fixed", PLAN_MODULE._kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
            PLAN_MODULE._expect("source_preflight_camp_head_matches_origin", PLAN_MODULE._kv(heads, "CAMP_HEAD", "camp_head"), PLAN_MODULE._kv(heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main")),
            PLAN_MODULE._expect("objective_required_records", summary["objective_required_records"], OBJECTIVE_REQUIRED_RECORDS),
            PLAN_MODULE._expect("candidate_closed_loop_outcome_records", summary["candidate_closed_loop_outcome_records"], 0),
            PLAN_MODULE._expect("missing_candidate_closed_loop_outcome_records", summary["missing_candidate_closed_loop_outcome_records"], OBJECTIVE_REQUIRED_RECORDS),
            PLAN_MODULE._expect("preflight_item_count", summary["preflight_item_count"], EXPECTED_PREFLIGHT_ITEM_COUNT),
            PLAN_MODULE._expect("planned_output_count", summary["planned_output_count"], EXPECTED_PLANNED_OUTPUT_COUNT),
            PLAN_MODULE._expect("no_go_count", summary["no_go_count"], EXPECTED_NO_GO_COUNT),
            PLAN_MODULE._expect("future_contract_required_records", future_contract.get("required_records"), OBJECTIVE_REQUIRED_RECORDS),
            PLAN_MODULE._expect("future_contract_allowed_candidate_source", future_contract.get("allowed_candidate_source"), "existing fixed DP candidate tensor only"),
            PLAN_MODULE._expect("future_contract_top1_reference_index", future_contract.get("top1_reference_index"), 0),
            PLAN_MODULE._expect("future_contract_requires_candidate_tensor_provenance", future_contract.get("requires_candidate_tensor_provenance_logging"), True),
            PLAN_MODULE._expect("future_contract_requires_closed_loop_outcome_collection", future_contract.get("requires_closed_loop_outcome_collection"), True),
            PLAN_MODULE._expect("future_contract_closed_loop_usage", future_contract.get("closed_loop_outcome_usage"), "offline_evaluation_evidence_only"),
            PLAN_MODULE._expect("future_gate_authorized_by_source_preflight", future_contract.get("future_gate_authorized_by_this_gate"), "static_review_only"),
            PLAN_MODULE._check("script_mentions_static_review_boundary", "future_gate_authorized_by_this_gate" in script_text),
            PLAN_MODULE._check("script_blocks_direct_execution", "direct_candidate_index_replay_execution_authorized" in script_text),
            PLAN_MODULE._check("test_asserts_no_direct_execution", "direct_candidate_index_replay_execution_authorized\"] is False" in test_text),
        ]
    )
    checks.extend(_sha_checks(root_sha256s=root_sha256s, nested_sha256s=nested_sha256s, paths=paths))
    for action in BLOCKED_ACTIONS:
        checks.append(PLAN_MODULE._expect(f"source_preflight_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        checks.append(PLAN_MODULE._expect(f"source_preflight_{flag}", bool(decision.get(flag, False)), False))
    return checks


def _sha_checks(
    *,
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    paths: dict[str, Path],
) -> list[dict[str, Any]]:
    json_path = paths["candidate_index_outcome_preflight_json"]
    md_path = paths["candidate_index_outcome_preflight_md"]
    sha256s_path = paths["candidate_index_outcome_preflight_sha256s"]
    return [
        PLAN_MODULE._expect(
            "root_preflight_json_sha",
            PLAN_MODULE._sha_for_suffix(root_sha256s, f"preflight/{SOURCE_PREFLIGHT_JSON_NAME}"),
            PLAN_MODULE._sha256(json_path),
        ),
        PLAN_MODULE._expect(
            "root_preflight_md_sha",
            PLAN_MODULE._sha_for_suffix(root_sha256s, f"preflight/{SOURCE_PREFLIGHT_MD_NAME}"),
            PLAN_MODULE._sha256(md_path),
        ),
        PLAN_MODULE._expect(
            "root_preflight_sha256s_sha",
            PLAN_MODULE._sha_for_suffix(root_sha256s, "preflight/SHA256SUMS"),
            PLAN_MODULE._sha256(sha256s_path),
        ),
        PLAN_MODULE._expect(
            "nested_preflight_json_sha",
            PLAN_MODULE._sha_for_suffix(nested_sha256s, json_path.name),
            PLAN_MODULE._sha256(json_path),
        ),
        PLAN_MODULE._expect(
            "nested_preflight_md_sha",
            PLAN_MODULE._sha_for_suffix(nested_sha256s, md_path.name),
            PLAN_MODULE._sha256(md_path),
        ),
    ]


def _source_preflight_summary(source_preflight: dict[str, Any]) -> dict[str, Any]:
    decision = PLAN_MODULE._dict(source_preflight.get("final_decision"))
    source_summary = PLAN_MODULE._dict(source_preflight.get("source_summary"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "objective_required_records": int(
            decision.get("objective_required_records") or source_summary.get("objective_required_records") or 0
        ),
        "candidate_closed_loop_outcome_records": int(
            decision.get("candidate_closed_loop_outcome_records")
            or source_summary.get("candidate_closed_loop_outcome_records")
            or 0
        ),
        "missing_candidate_closed_loop_outcome_records": int(
            decision.get("missing_candidate_closed_loop_outcome_records")
            or source_summary.get("missing_candidate_closed_loop_outcome_records")
            or 0
        ),
        "preflight_item_count": len(source_preflight.get("preflight_items") or []),
        "planned_output_count": len(source_preflight.get("planned_outputs") or []),
        "no_go_count": len(source_preflight.get("no_go_register") or []),
    }


def _decision(
    *,
    passed: bool,
    checks: list[dict[str, Any]],
    source_preflight: dict[str, Any],
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    summary = _source_preflight_summary(source_preflight)
    source_decision = PLAN_MODULE._dict(source_preflight.get("final_decision"))
    if passed:
        failure_class = None
    elif "static_review_enabled" in failed:
        failure_class = "explicit_candidate_index_replay_outcome_acquisition_preflight_static_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_preflight") for name in failed):
        failure_class = "source_preflight_contract_failure"
    elif any(name.endswith("_sha") for name in failed):
        failure_class = "source_preflight_hash_contract_failure"
    else:
        failure_class = "candidate_index_replay_outcome_acquisition_preflight_static_review_contract_failure"
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_candidate_index_replay_outcome_acquisition_preflight_static_review_passed": bool(passed),
        "objective_3200_candidate_index_replay_outcome_acquisition_execution_authorized": bool(passed),
        "objective_required_records": summary["objective_required_records"],
        "candidate_closed_loop_outcome_records": summary["candidate_closed_loop_outcome_records"],
        "missing_candidate_closed_loop_outcome_records": summary["missing_candidate_closed_loop_outcome_records"],
        "candidate_index_replay_harness_implemented": bool(source_decision.get("candidate_index_replay_harness_implemented")),
        "candidate_index_replay_harness_execution_authorized": False,
        "direct_candidate_index_replay_execution_authorized": False,
        "direct_outcome_acquisition_execution_authorized": False,
        "outcome_acquisition_executed_by_this_gate": False,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
        "recommendation": "execute_candidate_index_replay_outcome_acquisition_only" if passed else "repair_or_rerun_same_static_review_gate",
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
    sums = [f"{PLAN_MODULE._sha256(path)}  {path.name}" for path in (json_path, md_path)]
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_preflight_summary"]
    return "\n".join(
        [
            "# Objective-3200 Candidate-Index Replay Outcome-Acquisition Preflight Static Review",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
            "## Source Preflight",
            "",
            f"- Objective required records: `{summary['objective_required_records']}`",
            f"- Missing per-record shadow-selected outcomes: `{summary['missing_candidate_closed_loop_outcome_records']}`",
            f"- Preflight items / planned outputs / no-go checks: `{summary['preflight_item_count']} / {summary['planned_output_count']} / {summary['no_go_count']}`",
            "",
            "## Boundary",
            "",
            "- Static review only: no candidate-index replay, outcome acquisition, training, candidate generation, DP modification, candidate tensor mutation, promotion, deployment, online selector activation, or claim.",
            f"- Score expression: `{report['analysis']['score_expression']}`",
        ]
    ) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
