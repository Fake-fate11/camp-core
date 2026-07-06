#!/usr/bin/env python3
"""Plan objective-3200 candidate-index replay outcome-acquisition preflight.

This gate is read-only and plan-only. It consumes the audited candidate-index
replay harness post-implementation static review and preregisters the contract
for a future outcome-acquisition preflight. It does not run candidate-index
replay, acquire outcomes, train, generate candidates, modify Diffusion Planner,
promote, deploy, enable an online selector, or make claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_REVIEW_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_replay_harness_post_implementation_static_review_v1"
)
SOURCE_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_harness_post_implementation_static_review_passed"
)
SOURCE_REVIEW_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_harness_post_implementation_static_review.json"
)
SOURCE_REVIEW_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_harness_post_implementation_static_review.md"
)

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_v1"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_plan_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_plan_static_review_only"
)

PLAN_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_plan.json"
)
PLAN_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_plan.md"
)

OBJECTIVE_REQUIRED_RECORDS = 3200
EXPECTED_PREFLIGHT_PLAN_ITEMS = (
    "lock_post_implementation_static_review",
    "pre_register_candidate_index_replay_inputs",
    "pre_register_strict_pairing_and_metrics",
    "pre_register_fixed_candidate_tensor_identity_checks",
    "pre_register_no_go_checks",
    "authorize_static_review_only",
)
EXPECTED_NO_GO = (
    "source_static_review_missing_or_failed",
    "dp_head_drift",
    "harness_flag_missing_or_guard_changed",
    "candidate_index_not_from_shadow_selected_index",
    "candidate_tensor_identity_missing_or_mutated",
    "camp_generates_repairs_rewrites_or_blends_trajectory",
    "dp_code_config_weight_or_checkpoint_modified",
    "full36_or_formal_seed_11_12_13_present",
    "closed_loop_outcome_used_for_training_or_online_input",
    "non_affine_score_or_non_simplex_weight",
    "direct_execution_before_static_review",
    "promotion_deployment_online_selector_or_claim",
)
BLOCKED_ACTIONS = (
    "selector_promotion_authorized",
    "deployment_authorized",
    "online_selector_change_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
FALSE_EXECUTION_FLAGS = (
    "candidate_index_replay_execution_executed_by_this_gate",
    "outcome_acquisition_executed_by_this_gate",
    "training_executed_by_this_gate",
    "candidate_generation_executed_by_this_gate",
    "dp_modified_by_this_gate",
    "candidate_tensor_modified_by_this_gate",
    "promotion_executed_by_this_gate",
    "deployment_executed_by_this_gate",
)
ANALYSIS_FALSE_FLAGS = (
    "candidate_index_replay_execution",
    "outcome_acquisition_execution",
    "training_execution",
    "candidate_generation",
    "dp_modification",
    "candidate_tensor_modification",
    "online_selector_change",
    "promotion_executed",
    "deployment_executed",
    "safety_or_camp_over_dp_claim",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_md", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--runtime_replay_script_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_md=args.source_static_review_md,
        source_static_review_sha256s=args.source_static_review_sha256s,
        runtime_replay_script_py=args.runtime_replay_script_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_static_review_md: Path,
    source_static_review_sha256s: Path,
    runtime_replay_script_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = source_static_review_artifact_dir.resolve()
    paths = {
        "source_static_review_json": source_static_review_json.resolve(),
        "source_static_review_md": source_static_review_md.resolve(),
        "source_static_review_sha256s": source_static_review_sha256s.resolve(),
        "runtime_replay_script_py": runtime_replay_script_py.resolve(),
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
        "review_json": artifact_dir / "review" / SOURCE_REVIEW_JSON_NAME,
        "review_md": artifact_dir / "review" / SOURCE_REVIEW_MD_NAME,
        "review_sha256s": artifact_dir / "review" / "SHA256SUMS",
    }
    source_review = _read_json_dict(paths["source_static_review_json"])
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])
    heads = _parse_key_values(_read_text(artifact_files["heads"]))
    root_sha256s = _read_sha256sums(artifact_files["root_sha256s"])
    nested_sha256s = _read_sha256sums(paths["source_static_review_sha256s"])
    run_exit = _read_text(artifact_files["run_exit"]).strip()
    runtime_script = _read_text(paths["runtime_replay_script_py"])
    source_summary = _source_review_summary(source_review)
    runner_surface = _runner_surface(runtime_script)
    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        paths=paths,
        artifact_files=artifact_files,
        source_review=source_review,
        source_summary=source_summary,
        runner_surface=runner_surface,
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
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "read_only": True,
            "plan_only": True,
            "candidate_index_replay_outcome_acquisition_preflight_plan_only": True,
            "score_expression": SCORE_EXPRESSION,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            **{flag: False for flag in ANALYSIS_FALSE_FLAGS},
        },
        "inputs": {
            "source_static_review_artifact_dir": str(artifact_dir),
            "output_dir": str(output_dir.resolve()),
            **{name: str(path) for name, path in paths.items()},
        },
        "source_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in {**paths, **artifact_files}.items()
        },
        "source_static_review_summary": source_summary,
        "runner_surface_inventory": runner_surface,
        "outcome_acquisition_preflight_plan": _outcome_acquisition_preflight_plan(runner_surface),
        "strict_pairing_and_metrics_protocol": _strict_pairing_and_metrics_protocol(),
        "artifact_contract": _artifact_contract(),
        "no_go_register": [{"name": name} for name in EXPECTED_NO_GO],
        "plan_checks": checks,
        "final_decision": _decision(
            passed=passed,
            checks=checks,
            source_summary=source_summary,
            runner_surface=runner_surface,
        ),
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    paths: dict[str, Path],
    artifact_files: dict[str, Path],
    source_review: dict[str, Any],
    source_summary: dict[str, Any],
    runner_surface: dict[str, Any],
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
) -> list[dict[str, Any]]:
    decision = _dict(source_review.get("final_decision"))
    analysis = _dict(source_review.get("analysis"))
    checks = [
        _expect("outcome_acquisition_preflight_plan_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("status_doc_latest_status", _latest_value(status_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        _expect("status_doc_latest_next_work", _latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _check("source_static_review_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
        _expect("source_static_review_run_exit_zero", run_exit, "0"),
        _expect("source_static_review_dp_head_fixed", _kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
        _expect(
            "source_static_review_camp_head_matches_origin",
            _kv(heads, "CAMP_HEAD", "camp_head"),
            _kv(heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main"),
        ),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, allow_empty=False))
    for name, path in artifact_files.items():
        checks.extend(_path_checks(f"artifact_{name}", path, allow_empty=(name == "stderr")))
    checks.extend(_artifact_hash_checks(artifact_files, root_sha256s, nested_sha256s))
    checks.extend(
        [
            _expect("source_static_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA),
            _expect("source_static_review_passed", decision.get("passed"), True),
            _expect("source_static_review_status", decision.get("status"), SOURCE_REVIEW_STATUS),
            _expect("source_static_review_authorized_next", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
            _expect("source_static_review_authorized_this_plan", decision.get("objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_authorized"), True),
            _expect("source_static_review_harness_implemented", decision.get("candidate_index_replay_harness_implemented"), True),
            _expect("source_static_review_harness_execution_authorized", decision.get("candidate_index_replay_harness_execution_authorized"), False),
            _expect("source_static_review_direct_candidate_index_replay", decision.get("direct_candidate_index_replay_execution_authorized"), False),
            _expect("source_static_review_direct_outcome_acquisition", decision.get("direct_outcome_acquisition_execution_authorized"), False),
            _expect("source_static_review_actual_safetycost_available", decision.get("actual_safetycost_v1_available"), False),
            _expect("source_analysis_static_review_only", analysis.get("static_review_only"), True),
            _expect("source_analysis_read_only", analysis.get("read_only"), True),
            _expect("source_analysis_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
            _expect("source_analysis_harness_implemented", analysis.get("candidate_index_replay_harness_implemented"), True),
            _expect("source_analysis_candidate_index_replay_execution", analysis.get("candidate_index_replay_execution_executed_by_this_gate"), False),
            _expect("source_analysis_outcome_acquisition_execution", analysis.get("outcome_acquisition_executed_by_this_gate"), False),
            _expect("source_objective_required_records", source_summary["objective_required_records"], OBJECTIVE_REQUIRED_RECORDS),
            _expect("source_candidate_outcome_records", source_summary["candidate_closed_loop_outcome_records"], 0),
            _expect("source_missing_outcome_records", source_summary["missing_candidate_closed_loop_outcome_records"], OBJECTIVE_REQUIRED_RECORDS),
            _expect("source_candidate_index_flag_present", source_summary["candidate_index_replay_flag_present"], True),
            _expect("runner_has_candidate_index_replay_flag", runner_surface["has_candidate_index_replay_flag"], True),
            _expect("runner_has_harness_alias_flag", runner_surface["has_harness_alias_flag"], True),
            _expect("runner_requires_collect_closed_loop", runner_surface["requires_collect_closed_loop_outcomes"], True),
            _expect("runner_requires_candidate_tensor_provenance", runner_surface["requires_candidate_tensor_provenance_logging"], True),
            _expect("runner_routes_shadow_selected_index", runner_surface["routes_shadow_selected_index"], True),
            _expect("runner_records_harness_payload", runner_surface["records_harness_payload"], True),
        ]
    )
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_static_review_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        checks.append(_expect(f"decision_{flag}", decision.get(flag), False))
    return checks


def _artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _expect("root_heads_sha", _sha_for_suffix(root_sha256s, "HEADS"), _sha256(artifact_files["heads"])),
        _expect("root_command_sha", _sha_for_suffix(root_sha256s, "COMMAND"), _sha256(artifact_files["command"])),
        _expect("root_stdout_sha", _sha_for_suffix(root_sha256s, "stdout"), _sha256(artifact_files["stdout"])),
        _expect("root_stderr_sha", _sha_for_suffix(root_sha256s, "stderr"), _sha256(artifact_files["stderr"])),
        _expect("root_run_exit_sha", _sha_for_suffix(root_sha256s, "run.exit"), _sha256(artifact_files["run_exit"])),
        _expect("root_review_json_sha", _sha_for_suffix(root_sha256s, f"review/{SOURCE_REVIEW_JSON_NAME}"), _sha256(artifact_files["review_json"])),
        _expect("root_review_md_sha", _sha_for_suffix(root_sha256s, f"review/{SOURCE_REVIEW_MD_NAME}"), _sha256(artifact_files["review_md"])),
        _expect("root_review_sha256s_sha", _sha_for_suffix(root_sha256s, "review/SHA256SUMS"), _sha256(artifact_files["review_sha256s"])),
        _expect("nested_review_json_sha", _sha_for_suffix(nested_sha256s, SOURCE_REVIEW_JSON_NAME), _sha256(artifact_files["review_json"])),
        _expect("nested_review_md_sha", _sha_for_suffix(nested_sha256s, SOURCE_REVIEW_MD_NAME), _sha256(artifact_files["review_md"])),
    ]


def _source_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_review.get("final_decision"))
    source_summary = _dict(source_review.get("source_implementation_summary"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "objective_required_records": int(source_summary.get("objective_required_records") or 0),
        "candidate_closed_loop_outcome_records": int(source_summary.get("candidate_closed_loop_outcome_records") or 0),
        "missing_candidate_closed_loop_outcome_records": int(source_summary.get("missing_candidate_closed_loop_outcome_records") or 0),
        "candidate_index_replay_flag_present": bool(source_summary.get("candidate_index_replay_flag_present")),
        "harness_execution_executed_by_this_gate": bool(source_summary.get("harness_execution_executed_by_this_gate")),
        "outcome_acquisition_executed_by_this_gate": bool(source_summary.get("outcome_acquisition_executed_by_this_gate")),
    }


def _runner_surface(text: str) -> dict[str, Any]:
    return {
        "has_candidate_index_replay_flag": "--candidate_index_replay" in text,
        "has_harness_alias_flag": "--camp_candidate_index_replay_harness" in text,
        "requires_collect_closed_loop_outcomes": (
            "--camp_collect_closed_loop_outcomes" in text
            and "requires --camp_collect_closed_loop_outcomes" in text
        ),
        "requires_candidate_tensor_provenance_logging": (
            "--camp_candidate_tensor_provenance_logging" in text
            and "requires --camp_candidate_tensor_provenance_logging" in text
        ),
        "routes_shadow_selected_index": (
            "shadow_selected_index" in text
            and "selected_index = int(shadow_selected_index)" in text
        ),
        "records_harness_payload": (
            "_build_candidate_index_replay_harness_payload" in text
            and "candidate_index_replay_harness" in text
        ),
        "paper_faithful_boundary_present": "PAPER_FAITHFUL_BOUNDARY_ERROR" in text,
    }


def _outcome_acquisition_preflight_plan(runner_surface: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": "lock_post_implementation_static_review",
            "executes_replay": False,
            "purpose": "Use the passed harness post-implementation static review as the only source artifact for this continuation.",
        },
        {
            "name": "pre_register_candidate_index_replay_inputs",
            "executes_replay": False,
            "purpose": "Require the future preflight to bind every row to the audited shadow_selected_index and immutable fixed DP candidate tensor.",
            "harness_flags_present": {
                "candidate_index_replay": runner_surface["has_candidate_index_replay_flag"],
                "camp_candidate_index_replay_harness": runner_surface["has_harness_alias_flag"],
            },
        },
        {
            "name": "pre_register_strict_pairing_and_metrics",
            "executes_replay": False,
            "purpose": "Define row-level CAMP shadow-selected versus DP Top-1 pairing and SafetyCost_v1 delta schema before execution.",
        },
        {
            "name": "pre_register_fixed_candidate_tensor_identity_checks",
            "executes_replay": False,
            "purpose": "Require candidate tensor provenance and pre/post tensor identity checks; reject any DP or tensor mutation.",
        },
        {
            "name": "pre_register_no_go_checks",
            "executes_replay": False,
            "purpose": "Fail closed on forbidden splits, trajectory edits, closed-loop training input, non-affine scoring, non-simplex weights, and claims.",
        },
        {
            "name": "authorize_static_review_only",
            "executes_replay": False,
            "purpose": "Review this plan before any outcome-acquisition preflight execution gate.",
        },
    ]


def _strict_pairing_and_metrics_protocol() -> dict[str, Any]:
    return {
        "required_rows": OBJECTIVE_REQUIRED_RECORDS,
        "camp_action": "select_existing_fixed_dp_candidate_by_shadow_selected_index_only",
        "dp_baseline": "fixed_dp_candidate_tensor_top1_index_0",
        "pairing_keys": ["scenario", "seed", "sample", "traffic_light_mode", "run_key"],
        "required_inputs": [
            "audited_shadow_selection_log",
            "fixed_dp_candidate_tensor_identity",
            "dp_top1_closed_loop_outcome",
            "candidate_index_replay_harness_payload",
        ],
        "required_metrics": [
            "SafetyCost_v1_shadow_selected",
            "SafetyCost_v1_dp_top1",
            "delta_shadow_minus_top1",
            "paired_record_count",
            "missing_record_count",
        ],
        "pass_fail_criteria": [
            "exactly_3200_strict_pairs",
            "zero_missing_shadow_selected_outcomes",
            "zero_candidate_tensor_identity_mismatches",
            "zero_forbidden_split_records",
            "zero_dp_code_config_weight_checkpoint_changes",
        ],
        "claim_rule": "claims remain unauthorized until a later evidence review gate evaluates the completed paired outcome artifact",
        "closed_loop_outcome_usage": "offline_evaluation_evidence_only",
    }


def _artifact_contract() -> dict[str, Any]:
    return {
        "required_root_files": ["HEADS", "COMMAND", "stdout", "stderr", "run.exit", "SHA256SUMS"],
        "required_nested_files": [PLAN_JSON_NAME, PLAN_MD_NAME, "SHA256SUMS"],
        "source_artifact_required": "objective_3200_candidate_index_replay_harness_post_implementation_static_review",
        "next_gate": AUTHORIZED_NEXT_WORK,
        "preflight_execution_authorized_by_this_gate": False,
        "replay_execution_authorized_by_this_gate": False,
        "outcome_acquisition_authorized_by_this_gate": False,
    }


def _decision(
    *,
    passed: bool,
    checks: list[dict[str, Any]],
    source_summary: dict[str, Any],
    runner_surface: dict[str, Any],
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "outcome_acquisition_preflight_plan_enabled" in failed:
        failure_class = "explicit_candidate_index_replay_outcome_acquisition_preflight_plan_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_static_review_") for name in failed):
        failure_class = "source_static_review_contract_failure"
    elif any(name.startswith("runner_") for name in failed):
        failure_class = "candidate_index_replay_harness_surface_missing"
    else:
        failure_class = "candidate_index_replay_outcome_acquisition_preflight_plan_contract_failure"
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_ready": bool(passed),
        "objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_authorized": bool(passed),
        "objective_required_records": source_summary["objective_required_records"],
        "candidate_closed_loop_outcome_records": source_summary["candidate_closed_loop_outcome_records"],
        "missing_candidate_closed_loop_outcome_records": source_summary["missing_candidate_closed_loop_outcome_records"],
        "candidate_index_replay_harness_implemented": bool(runner_surface["has_candidate_index_replay_flag"]),
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
    json_path = output_dir / PLAN_JSON_NAME
    md_path = output_dir / PLAN_MD_NAME
    json_path.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        "\n".join(
            [
                f"{_sha256(json_path)}  {json_path.name}",
                f"{_sha256(md_path)}  {md_path.name}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_static_review_summary"]
    runner = report["runner_surface_inventory"]
    return "\n".join(
        [
            "# Objective-3200 Candidate-Index Replay Outcome-Acquisition Preflight Plan",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
            "## Source",
            "",
            f"- Objective records: `{source['objective_required_records']}`",
            f"- Candidate outcome records: `{source['candidate_closed_loop_outcome_records']}`",
            f"- Missing outcome records: `{source['missing_candidate_closed_loop_outcome_records']}`",
            "",
            "## Runner Surface",
            "",
            f"- Candidate-index replay flag present: `{runner['has_candidate_index_replay_flag']}`",
            f"- Harness alias flag present: `{runner['has_harness_alias_flag']}`",
            f"- Shadow-selected routing present: `{runner['routes_shadow_selected_index']}`",
            "",
            "This gate authorizes static review only; it does not run replay or acquire outcomes.",
            "",
        ]
    )


def _path_checks(name: str, path: Path, *, allow_empty: bool) -> list[dict[str, Any]]:
    checks = [_check(f"{name}_exists", path.is_file(), str(path), "file")]
    if path.is_file() and not allow_empty:
        checks.append(_check(f"{name}_nonempty", path.stat().st_size > 0, path.stat().st_size, ">0 bytes"))
    return checks


def _read_json_dict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_sha256sums(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in _read_text(path).splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            result[parts[1].strip()] = parts[0]
    return result


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _latest_value(text: str, key: str) -> str | None:
    token = f"{key}="
    if token not in text:
        return None
    return text.rsplit(token, maxsplit=1)[1].splitlines()[0].strip()


def _kv(mapping: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _sha_for_suffix(mapping: dict[str, str], suffix: str) -> str | None:
    normalized = suffix.replace("\\", "/")
    for path, digest in mapping.items():
        if path.replace("\\", "/").endswith(normalized):
            return digest
    return None


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": actual == expected, "actual": actual, "expected": expected}


def _check(name: str, passed: bool, actual: Any = None, expected: Any = True) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual if actual is not None else bool(passed), "expected": expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value.lower())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
