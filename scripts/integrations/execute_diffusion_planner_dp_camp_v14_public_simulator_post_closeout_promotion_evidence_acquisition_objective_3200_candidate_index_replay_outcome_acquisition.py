#!/usr/bin/env python3
"""Execute objective-3200 candidate-index replay outcome acquisition.

This gate consumes the audited candidate-index outcome-acquisition preflight
static review plus the prior DP Top-1 default-off runtime runbook. It rewrites
that runbook to execute the logged ``shadow_selected_index`` from the same fixed
DP candidate tensor while collecting closed-loop outcomes. It does not modify
Diffusion Planner, generate or rewrite trajectories, train CAMP, promote,
deploy, enable an online selector, or make any safety/CAMP-over-DP claim.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import shlex
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Any


def _load_source_static_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_candidate_index_"
        "replay_outcome_acquisition_preflight_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_replay_outcome_acquisition_preflight_static_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_STATIC_REVIEW_MODULE = _load_source_static_review_module()
PLAN_MODULE = SOURCE_STATIC_REVIEW_MODULE.PLAN_MODULE

FIXED_DP_HEAD = SOURCE_STATIC_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_STATIC_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_STATIC_REVIEW_SCHEMA = SOURCE_STATIC_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_STATIC_REVIEW_STATUS = SOURCE_STATIC_REVIEW_MODULE.READY_STATUS
SOURCE_STATIC_REVIEW_JSON_NAME = SOURCE_STATIC_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_STATIC_REVIEW_MD_NAME = SOURCE_STATIC_REVIEW_MODULE.REVIEW_MD_NAME
BLOCKED_ACTIONS = SOURCE_STATIC_REVIEW_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = SOURCE_STATIC_REVIEW_MODULE.FALSE_EXECUTION_FLAGS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_replay_outcome_acquisition_execution_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_STATIC_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_execution_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_execution_failed"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_execution_result_review_only"
)
FAILED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_execution_failed_user_decision_required"
)

EXECUTION_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_execution.json"
)
EXECUTION_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_execution.md"
)
RUNBOOK_NAME = "run_candidate_index_replay_outcome_acquisition.sh"
GUARD_ENV_VAR = (
    "DP_CAMP_V14_OBJECTIVE_3200_CANDIDATE_INDEX_REPLAY_OUTCOME_ACQUISITION_EXECUTE"
)

OBJECTIVE_REQUIRED_RECORDS = SOURCE_STATIC_REVIEW_MODULE.OBJECTIVE_REQUIRED_RECORDS
EXPECTED_SELECTION_LOG_COUNT = 32
EXPECTED_NUM_CANDIDATES = 8
FORMAL_SEEDS = {11, 12, 13}
FULL36_MARKERS = ("full36", "formal36", "full_36")
FORBIDDEN_COMMAND_SNIPPETS = (
    "--candidate_reference_blend_steps",
    "--candidate_guidance_config",
    "--candidate_guidance_scale",
    "--camp_traffic_light_hybrid_postselection",
    "--camp_underprogress_relaxation",
    "--camp_splice_shadow_rule",
    "--camp_perfect_tracker_command_postselection",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_preflight_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_json", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_md", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_runtime_execution_dir", type=Path, required=True)
    parser.add_argument("--source_runtime_runbook", type=Path, required=True)
    parser.add_argument("--candidate_index_output_root", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_record_count", type=int, default=OBJECTIVE_REQUIRED_RECORDS)
    parser.add_argument("--expected_selection_log_count", type=int, default=EXPECTED_SELECTION_LOG_COUNT)
    parser.add_argument("--expected_num_candidates", type=int, default=EXPECTED_NUM_CANDIDATES)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_execution",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_preflight_static_review_artifact_dir=args.source_preflight_static_review_artifact_dir,
        source_preflight_static_review_json=args.source_preflight_static_review_json,
        source_preflight_static_review_md=args.source_preflight_static_review_md,
        source_preflight_static_review_sha256s=args.source_preflight_static_review_sha256s,
        source_runtime_execution_dir=args.source_runtime_execution_dir,
        source_runtime_runbook=args.source_runtime_runbook,
        candidate_index_output_root=args.candidate_index_output_root,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_record_count=args.expected_record_count,
        expected_selection_log_count=args.expected_selection_log_count,
        expected_num_candidates=args.expected_num_candidates,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_execution
        ),
        execute_commands=True,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_preflight_static_review_artifact_dir: Path,
    source_preflight_static_review_json: Path,
    source_preflight_static_review_md: Path,
    source_preflight_static_review_sha256s: Path,
    source_runtime_execution_dir: Path,
    source_runtime_runbook: Path,
    candidate_index_output_root: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_record_count: int = OBJECTIVE_REQUIRED_RECORDS,
    expected_selection_log_count: int = EXPECTED_SELECTION_LOG_COUNT,
    expected_num_candidates: int = EXPECTED_NUM_CANDIDATES,
    enabled: bool = False,
    execute_commands: bool = True,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    source_artifact_dir = source_preflight_static_review_artifact_dir.resolve()
    source_runtime_root = source_runtime_execution_dir.resolve()
    candidate_output_root = candidate_index_output_root.resolve()
    paths = {
        "source_preflight_static_review_json": source_preflight_static_review_json.resolve(),
        "source_preflight_static_review_md": source_preflight_static_review_md.resolve(),
        "source_preflight_static_review_sha256s": source_preflight_static_review_sha256s.resolve(),
        "source_runtime_runbook": source_runtime_runbook.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    source_files = {
        "heads": source_artifact_dir / "HEADS",
        "command": source_artifact_dir / "COMMAND",
        "stdout": source_artifact_dir / "stdout",
        "stderr": source_artifact_dir / "stderr",
        "run_exit": source_artifact_dir / "run.exit",
        "root_sha256s": source_artifact_dir / "SHA256SUMS",
        "review_json": source_artifact_dir / "review" / SOURCE_STATIC_REVIEW_JSON_NAME,
        "review_md": source_artifact_dir / "review" / SOURCE_STATIC_REVIEW_MD_NAME,
        "review_sha256s": source_artifact_dir / "review" / "SHA256SUMS",
    }
    source_review = _read_json_dict(paths["source_preflight_static_review_json"])
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])
    source_runbook_text = _read_text(paths["source_runtime_runbook"])
    source_heads = _parse_key_values(_read_text(source_files["heads"]))
    root_sha256s = _read_sha256sums(source_files["root_sha256s"])
    nested_sha256s = _read_sha256sums(paths["source_preflight_static_review_sha256s"])
    run_exit = _read_text(source_files["run_exit"]).strip()
    source_runtime = _source_root_summary(
        source_runtime_root,
        expected_num_candidates=expected_num_candidates,
    )
    rewrite = _rewrite_runbook_commands(
        source_runbook_text=source_runbook_text,
        source_runtime_root=source_runtime_root,
        candidate_output_root=candidate_output_root,
    )
    prechecks = _prechecks(
        enabled=enabled,
        source_artifact_dir=source_artifact_dir,
        paths=paths,
        source_files=source_files,
        source_review=source_review,
        source_heads=source_heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        run_exit=run_exit,
        v14_text=v14_text,
        status_text=status_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_record_count=expected_record_count,
        expected_selection_log_count=expected_selection_log_count,
        source_runtime=source_runtime,
        candidate_output_root=candidate_output_root,
        rewrite=rewrite,
    )
    precheck_passed = all(check["passed"] for check in prechecks)
    execution = {
        "attempted": False,
        "commands_executed": 0,
        "first_failed_command": None,
        "runbook_exit_code": None,
        "runbook_stdout_log": str(output_dir / "runbook.stdout.log"),
        "runbook_stderr_log": str(output_dir / "runbook.stderr.log"),
        "runbook_exit": str(output_dir / "runbook.exit"),
        "elapsed_seconds": 0.0,
    }
    if precheck_passed and execute_commands:
        output_dir.mkdir(parents=True, exist_ok=True)
        runbook_path = output_dir / RUNBOOK_NAME
        runbook_path.write_text(
            _render_runbook(
                commands=rewrite["candidate_index_commands"],
                current_camp_head=current_camp_head,
                current_dp_head=current_dp_head,
                candidate_output_root=candidate_output_root,
            ),
            encoding="utf-8",
        )
        execution = _execute_commands(
            commands=rewrite["candidate_index_commands"],
            output_dir=output_dir,
        )
    candidate_summary = _source_root_summary(
        candidate_output_root,
        expected_num_candidates=expected_num_candidates,
    )
    acquisition = _acquisition_summary(
        source_runtime=source_runtime,
        candidate=candidate_summary,
        expected_record_count=expected_record_count,
    )
    postchecks = _postchecks(
        execution=execution,
        source_runtime=source_runtime,
        candidate=candidate_summary,
        acquisition=acquisition,
        expected_record_count=expected_record_count,
        expected_selection_log_count=expected_selection_log_count,
    )
    checks = prechecks + postchecks
    passed = all(check["passed"] for check in checks)
    report = {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "objective_3200_candidate_index_replay_outcome_acquisition_execution": True,
            "execution_enabled": bool(enabled),
            "candidate_index_replay_execution_executed_by_this_gate": bool(execution["attempted"]),
            "outcome_acquisition_executed_by_this_gate": bool(execution["attempted"]),
            "training_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "candidate_tensor_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
            "closed_loop_outcome_usage": "offline_evaluation_evidence_only",
            "closed_loop_outcomes_used_for_training": False,
            "closed_loop_outcomes_used_for_online_selector": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "source_preflight_static_review_artifact_dir": str(source_artifact_dir),
            "source_runtime_execution_dir": str(source_runtime_root),
            "candidate_index_output_root": str(candidate_output_root),
            "output_dir": str(output_dir),
            **{name: str(path) for name, path in paths.items()},
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_preflight_static_review_camp_head": _kv(source_heads, "CAMP_HEAD", "camp_head"),
            "source_preflight_static_review_camp_origin_main": _kv(
                source_heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main"
            ),
            "source_preflight_static_review_dp_head": _kv(source_heads, "DP_HEAD", "dp_head"),
        },
        "source_artifact_hashes": _source_hashes(
            artifact_dir=source_artifact_dir,
            review_json=paths["source_preflight_static_review_json"],
            review_md=paths["source_preflight_static_review_md"],
            review_sha256s=paths["source_preflight_static_review_sha256s"],
            source_runtime_runbook=paths["source_runtime_runbook"],
        ),
        "command_manifest": {
            "schema_version": "candidate_index_replay_command_manifest_v1",
            "source_command_count": rewrite["source_command_count"],
            "candidate_index_command_count": rewrite["candidate_index_command_count"],
            "candidate_index_command_sha256": rewrite["candidate_index_command_sha256"],
            "commands": rewrite["command_manifest"],
        },
        "source_runtime_summary": _drop_record_keys(source_runtime),
        "candidate_index_outcome_summary": _drop_record_keys(candidate_summary),
        "strict_pairing_summary": acquisition,
        "execution": execution,
        "no_go_report": _no_go_report(candidate=candidate_summary, acquisition=acquisition),
        "execution_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, acquisition=acquisition, execution=execution),
    }
    return report


def _prechecks(
    *,
    enabled: bool,
    source_artifact_dir: Path,
    paths: dict[str, Path],
    source_files: dict[str, Path],
    source_review: dict[str, Any],
    source_heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    run_exit: str,
    v14_text: str,
    status_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_record_count: int,
    expected_selection_log_count: int,
    source_runtime: dict[str, Any],
    candidate_output_root: Path,
    rewrite: dict[str, Any],
) -> list[dict[str, Any]]:
    decision = _dict(source_review.get("final_decision"))
    analysis = _dict(source_review.get("analysis"))
    checks = [
        _expect("execution_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("status_doc_latest_status", _latest_value(status_text, "current_v14_status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("status_doc_latest_next_work", _latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _check("source_artifact_dir_exists", source_artifact_dir.is_dir(), str(source_artifact_dir), "directory"),
        _expect("source_artifact_run_exit", run_exit, "0"),
        _expect("source_static_review_schema", source_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA),
        _expect("source_static_review_passed", decision.get("passed"), True),
        _expect("source_static_review_status", decision.get("status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("source_static_review_authorized_next", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_static_review_execution_authorized", decision.get("objective_3200_candidate_index_replay_outcome_acquisition_execution_authorized"), True),
        _expect("source_static_review_static_review_only", analysis.get("static_review_only"), True),
        _expect("source_static_review_outcome_acquisition_executed", analysis.get("outcome_acquisition_executed"), False),
        _expect("source_static_review_dp_modification", analysis.get("dp_modification"), False),
        _expect("source_static_review_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_static_review_dp_head_fixed", _kv(source_heads, "DP_HEAD", "dp_head"), required_dp_head),
        _expect(
            "source_static_review_camp_head_matches_origin",
            _kv(source_heads, "CAMP_HEAD", "camp_head"),
            _kv(source_heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main"),
        ),
        _expect("source_runtime_selection_log_count", source_runtime["selection_log_count"], expected_selection_log_count),
        _expect("source_runtime_record_count", source_runtime["record_count"], expected_record_count),
        _expect("source_runtime_candidate_closed_loop_outcome_records", source_runtime["candidate_closed_loop_outcome_records"], 0),
        _expect("source_runtime_formal_seed_records", source_runtime["formal_seed_records"], 0),
        _expect("source_runtime_full36_path_records", source_runtime["full36_path_records"], 0),
        _expect("source_runtime_candidate_tensor_mutation_records", source_runtime["candidate_tensor_mutation_records"], 0),
        _expect("source_runtime_closed_loop_training_or_online_input_records", source_runtime["closed_loop_training_or_online_input_records"], 0),
        _expect("source_runbook_command_count", rewrite["source_command_count"], expected_selection_log_count),
        _expect("candidate_index_command_count", rewrite["candidate_index_command_count"], expected_selection_log_count),
        _expect("candidate_index_command_rewrite_failures", rewrite["rewrite_failure_count"], 0),
        _expect("candidate_index_command_forbidden_snippet_count", rewrite["forbidden_snippet_count"], 0),
        _expect("candidate_index_output_root_preexisting", candidate_output_root.exists(), False),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, allow_empty=False))
    for name, path in source_files.items():
        checks.extend(_path_checks(f"source_artifact_{name}", path, allow_empty=name == "stderr"))
    checks.extend(_sha_checks(root_sha256s=root_sha256s, nested_sha256s=nested_sha256s, files=source_files))
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_static_review_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        checks.append(_expect(f"source_static_review_{flag}", decision.get(flag, False), False))
    return checks


def _postchecks(
    *,
    execution: dict[str, Any],
    source_runtime: dict[str, Any],
    candidate: dict[str, Any],
    acquisition: dict[str, Any],
    expected_record_count: int,
    expected_selection_log_count: int,
) -> list[dict[str, Any]]:
    return [
        _expect("runbook_exit_code", execution["runbook_exit_code"], 0),
        _expect("candidate_selection_log_count", candidate["selection_log_count"], expected_selection_log_count),
        _expect("candidate_record_count", candidate["record_count"], expected_record_count),
        _expect("candidate_closed_loop_outcome_records", candidate["candidate_closed_loop_outcome_records"], expected_record_count),
        _expect("candidate_missing_closed_loop_outcome_records", candidate["missing_candidate_closed_loop_outcome_records"], 0),
        _expect("candidate_index_replay_payload_records", candidate["candidate_index_replay_payload_records"], expected_record_count),
        _expect("candidate_index_replay_invalid_payload_records", candidate["candidate_index_replay_invalid_payload_records"], 0),
        _expect("candidate_index_replay_not_executed_shadow_records", candidate["candidate_index_replay_not_executed_shadow_records"], 0),
        _expect("candidate_formal_seed_records", candidate["formal_seed_records"], 0),
        _expect("candidate_full36_path_records", candidate["full36_path_records"], 0),
        _expect("candidate_tensor_mutation_records", candidate["candidate_tensor_mutation_records"], 0),
        _expect("candidate_reference_blend_records", candidate["reference_blend_records"], 0),
        _expect("candidate_closed_loop_training_or_online_input_records", candidate["closed_loop_training_or_online_input_records"], 0),
        _expect("candidate_non_affine_score_records", candidate["non_affine_score_records"], 0),
        _expect("candidate_non_simplex_weight_records", candidate["non_simplex_weight_records"], 0),
        _expect("source_candidate_key_count", source_runtime["unique_record_key_count"], expected_record_count),
        _expect("paired_record_key_count", acquisition["paired_record_key_count"], expected_record_count),
        _expect("unpaired_source_record_key_count", acquisition["unpaired_source_record_key_count"], 0),
        _expect("unpaired_candidate_record_key_count", acquisition["unpaired_candidate_record_key_count"], 0),
        _expect("objective_3200_candidate_index_outcome_acquisition_satisfied", acquisition["objective_3200_candidate_index_outcome_acquisition_satisfied"], True),
    ]


def _rewrite_runbook_commands(
    *,
    source_runbook_text: str,
    source_runtime_root: Path,
    candidate_output_root: Path,
) -> dict[str, Any]:
    commands: list[list[str]] = []
    manifest: list[dict[str, Any]] = []
    failures: list[str] = []
    forbidden_count = 0
    for line in source_runbook_text.splitlines():
        stripped = line.strip()
        if "run_diffusion_planner_camp_replay.py" not in stripped:
            continue
        try:
            command = shlex.split(stripped)
        except ValueError as exc:
            failures.append(f"shlex_parse:{exc}")
            continue
        output_dir = _arg_value(command, "--output_dir")
        if output_dir is None:
            failures.append("missing_output_dir")
            continue
        try:
            rel_output = Path(output_dir).resolve().relative_to(source_runtime_root)
        except ValueError:
            failures.append(f"output_dir_not_under_source_root:{output_dir}")
            continue
        rewritten = list(command)
        new_output = candidate_output_root / rel_output
        _replace_arg(rewritten, "--output_dir", str(new_output))
        if "--camp_collect_closed_loop_outcomes" not in rewritten:
            rewritten.append("--camp_collect_closed_loop_outcomes")
        if "--candidate_index_replay" not in rewritten and "--camp_candidate_index_replay_harness" not in rewritten:
            rewritten.append("--candidate_index_replay")
        for required in (
            "--camp_default_off_shadow_selector",
            "--camp_candidate_tensor_provenance_logging",
            "--camp_collect_closed_loop_outcomes",
        ):
            if required not in rewritten:
                failures.append(f"missing_required_flag:{required}")
        if "--candidate_index_replay" not in rewritten and "--camp_candidate_index_replay_harness" not in rewritten:
            failures.append("missing_candidate_index_replay_flag")
        if _arg_value(rewritten, "--num_candidates") != str(EXPECTED_NUM_CANDIDATES):
            failures.append("num_candidates_not_fixed_8")
        snippets = " ".join(rewritten)
        if any(snippet in snippets for snippet in FORBIDDEN_COMMAND_SNIPPETS):
            forbidden_count += 1
        commands.append(rewritten)
        manifest.append(
            {
                "source_output_dir": output_dir,
                "candidate_index_output_dir": str(new_output),
                "relative_output_dir": rel_output.as_posix(),
                "command": rewritten,
            }
        )
    command_text = "\n".join(shlex.join(command) for command in commands)
    return {
        "source_command_count": len(commands),
        "candidate_index_command_count": len(commands),
        "rewrite_failures": failures,
        "rewrite_failure_count": len(failures),
        "forbidden_snippet_count": forbidden_count,
        "candidate_index_command_sha256": hashlib.sha256(command_text.encode("utf-8")).hexdigest(),
        "candidate_index_commands": commands,
        "command_manifest": manifest,
    }


def _execute_commands(*, commands: list[list[str]], output_dir: Path) -> dict[str, Any]:
    stdout_path = output_dir / "runbook.stdout.log"
    stderr_path = output_dir / "runbook.stderr.log"
    exit_path = output_dir / "runbook.exit"
    start = time.time()
    env = os.environ.copy()
    env[GUARD_ENV_VAR] = "1"
    attempted = False
    commands_executed = 0
    first_failed_command = None
    runbook_exit_code = 0
    with stdout_path.open("ab") as stdout_file, stderr_path.open("ab") as stderr_file:
        for index, command in enumerate(commands, start=1):
            attempted = True
            stdout_file.write(f"Running candidate-index replay command {index}/{len(commands)}\n".encode("utf-8"))
            stdout_file.flush()
            result = subprocess.run(command, stdout=stdout_file, stderr=stderr_file, env=env)
            commands_executed += 1
            if result.returncode != 0:
                first_failed_command = index
                runbook_exit_code = int(result.returncode)
                break
    exit_path.write_text(f"{runbook_exit_code}\n", encoding="utf-8")
    return {
        "attempted": attempted,
        "commands_executed": commands_executed,
        "first_failed_command": first_failed_command,
        "runbook_exit_code": runbook_exit_code,
        "runbook_stdout_log": str(stdout_path),
        "runbook_stderr_log": str(stderr_path),
        "runbook_exit": str(exit_path),
        "elapsed_seconds": round(time.time() - start, 6),
    }


def _source_root_summary(root: Path, *, expected_num_candidates: int) -> dict[str, Any]:
    logs = sorted(root.rglob("camp_selection_log.json")) if root.is_dir() else []
    summaries = sorted(root.rglob("camp_validation_summary.json")) if root.is_dir() else []
    counters: Counter[str] = Counter()
    keys: set[str] = set()
    duplicate_keys = 0
    missing_examples: list[dict[str, Any]] = []
    tensor_hashes: Counter[str] = Counter()
    for log in logs:
        rows = _records_from_payload(_read_json(log))
        seed = _seed_from_path(log)
        formal = seed in FORMAL_SEEDS
        full36 = _path_has_any_marker(log, FULL36_MARKERS)
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            counters["record_count"] += 1
            key = _record_key(root, log, index)
            if key in keys:
                duplicate_keys += 1
            keys.add(key)
            if formal:
                counters["formal_seed_records"] += 1
            if full36:
                counters["full36_path_records"] += 1
            closed_loop = row.get("candidate_closed_loop_outcomes")
            if isinstance(closed_loop, list) and closed_loop:
                counters["candidate_closed_loop_outcome_records"] += 1
            else:
                counters["missing_candidate_closed_loop_outcome_records"] += 1
                if len(missing_examples) < 5:
                    missing_examples.append({"log": str(log), "record_index": index, "key": key})
            _record_candidate_boundary(
                row,
                counters,
                tensor_hashes,
                expected_num_candidates=expected_num_candidates,
            )
    return {
        "root": str(root),
        "selection_log_count": len(logs),
        "validation_summary_count": len(summaries),
        "record_count": counters["record_count"],
        "unique_record_key_count": len(keys),
        "duplicate_record_key_count": duplicate_keys,
        "record_key_sha256": hashlib.sha256("\n".join(sorted(keys)).encode("utf-8")).hexdigest(),
        "candidate_closed_loop_outcome_records": counters["candidate_closed_loop_outcome_records"],
        "missing_candidate_closed_loop_outcome_records": counters["missing_candidate_closed_loop_outcome_records"],
        "candidate_index_replay_payload_records": counters["candidate_index_replay_payload_records"],
        "candidate_index_replay_invalid_payload_records": counters["candidate_index_replay_invalid_payload_records"],
        "candidate_index_replay_not_executed_shadow_records": counters["candidate_index_replay_not_executed_shadow_records"],
        "formal_seed_records": counters["formal_seed_records"],
        "full36_path_records": counters["full36_path_records"],
        "candidate_tensor_mutation_records": counters["candidate_tensor_mutation_records"],
        "reference_blend_records": counters["reference_blend_records"],
        "closed_loop_training_or_online_input_records": counters["closed_loop_training_or_online_input_records"],
        "non_affine_score_records": counters["non_affine_score_records"],
        "non_simplex_weight_records": counters["non_simplex_weight_records"],
        "unique_candidate_tensor_hash_count": len(tensor_hashes),
        "candidate_tensor_hash_preview": sorted(tensor_hashes)[:10],
        "missing_candidate_closed_loop_outcome_examples": missing_examples,
        "record_keys": sorted(keys),
    }


def _record_candidate_boundary(
    row: dict[str, Any],
    counters: Counter[str],
    tensor_hashes: Counter[str],
    *,
    expected_num_candidates: int,
) -> None:
    replay = _dict(row.get("candidate_index_replay_harness"))
    if replay:
        counters["candidate_index_replay_payload_records"] += 1
        if replay.get("payload_valid") is not True:
            counters["candidate_index_replay_invalid_payload_records"] += 1
        if replay.get("executed_shadow_selected_index") is not True:
            counters["candidate_index_replay_not_executed_shadow_records"] += 1
        if replay.get("closed_loop_outcomes_used_for_training") is True:
            counters["closed_loop_training_or_online_input_records"] += 1
        if replay.get("closed_loop_outcomes_used_for_online_selector") is True:
            counters["closed_loop_training_or_online_input_records"] += 1
    selector = _dict(row.get("default_off_shadow_selector"))
    provenance = _dict(row.get("camp_candidate_tensor_provenance"))
    hashes = _candidate_hashes(selector, replay, provenance)
    for value in hashes:
        tensor_hashes[str(value)] += 1
    if len(set(hashes)) > 1:
        counters["candidate_tensor_mutation_records"] += 1
    if provenance.get("candidate_tensor_mutation_effect") is True:
        counters["candidate_tensor_mutation_records"] += 1
    if provenance.get("pre_post_tensor_hash_equal") is False:
        counters["candidate_tensor_mutation_records"] += 1
    if provenance.get("reference_blend_present") is True or row.get("candidate_reference_blend_steps") not in (0, None):
        counters["reference_blend_records"] += 1
    generation_contract = _dict(row.get("candidate_generation_contract"))
    if generation_contract.get("reference_blend_steps") is not None:
        counters["reference_blend_records"] += 1
    if provenance.get("outcome_label_input") is True:
        counters["closed_loop_training_or_online_input_records"] += 1
    if selector and selector.get("score_expression") != SCORE_EXPRESSION:
        counters["non_affine_score_records"] += 1
    weights = row.get("selection_weights", row.get("weights"))
    if not _is_simplex(weights):
        counters["non_simplex_weight_records"] += 1
    if row.get("num_candidates") not in (None, expected_num_candidates):
        counters["candidate_tensor_mutation_records"] += 1


def _candidate_hashes(*payloads: dict[str, Any]) -> list[str]:
    hashes: list[str] = []
    for payload in payloads:
        for key in (
            "candidate_tensor_hash",
            "pre_camp_scoring_tensor",
            "post_camp_selector_tensor",
        ):
            value = _dict(payload.get(key)).get("sha256")
            if value:
                hashes.append(str(value))
    return hashes


def _acquisition_summary(
    *,
    source_runtime: dict[str, Any],
    candidate: dict[str, Any],
    expected_record_count: int,
) -> dict[str, Any]:
    source_keys = set(source_runtime["record_keys"])
    candidate_keys = set(candidate["record_keys"])
    paired = sorted(source_keys & candidate_keys)
    unpaired_source = sorted(source_keys - candidate_keys)
    unpaired_candidate = sorted(candidate_keys - source_keys)
    satisfied = (
        source_runtime["record_count"] == expected_record_count
        and candidate["record_count"] == expected_record_count
        and candidate["candidate_closed_loop_outcome_records"] == expected_record_count
        and candidate["missing_candidate_closed_loop_outcome_records"] == 0
        and candidate["candidate_index_replay_payload_records"] == expected_record_count
        and candidate["candidate_index_replay_invalid_payload_records"] == 0
        and candidate["candidate_index_replay_not_executed_shadow_records"] == 0
        and len(paired) == expected_record_count
        and not unpaired_source
        and not unpaired_candidate
    )
    return {
        "objective_required_records": expected_record_count,
        "source_runtime_record_count": source_runtime["record_count"],
        "candidate_index_record_count": candidate["record_count"],
        "candidate_closed_loop_outcome_records": candidate["candidate_closed_loop_outcome_records"],
        "missing_candidate_closed_loop_outcome_records": candidate["missing_candidate_closed_loop_outcome_records"],
        "candidate_index_replay_payload_records": candidate["candidate_index_replay_payload_records"],
        "paired_record_key_count": len(paired),
        "paired_record_key_sha256": hashlib.sha256("\n".join(paired).encode("utf-8")).hexdigest(),
        "unpaired_source_record_key_count": len(unpaired_source),
        "unpaired_candidate_record_key_count": len(unpaired_candidate),
        "unpaired_source_record_key_preview": unpaired_source[:10],
        "unpaired_candidate_record_key_preview": unpaired_candidate[:10],
        "objective_3200_candidate_index_outcome_acquisition_satisfied": satisfied,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
    }


def _no_go_report(*, candidate: dict[str, Any], acquisition: dict[str, Any]) -> dict[str, Any]:
    failures = []
    if not acquisition["objective_3200_candidate_index_outcome_acquisition_satisfied"]:
        failures.append("objective_3200_candidate_index_outcome_acquisition_incomplete")
    for key in (
        "formal_seed_records",
        "full36_path_records",
        "candidate_tensor_mutation_records",
        "reference_blend_records",
        "closed_loop_training_or_online_input_records",
        "non_affine_score_records",
        "non_simplex_weight_records",
        "candidate_index_replay_invalid_payload_records",
        "candidate_index_replay_not_executed_shadow_records",
    ):
        if candidate.get(key):
            failures.append(key)
    return {
        "entries": [
            "objective_3200_candidate_index_outcome_acquisition_incomplete",
            "candidate_index_not_shadow_selected_fixed_dp_candidate",
            "candidate_tensor_identity_missing_or_mutated",
            "reference_blend_or_trajectory_edit",
            "full36_or_formal_seed_11_12_13_present",
            "closed_loop_outcome_training_or_online_input",
            "non_affine_score_or_non_simplex_weight",
            "promotion_deployment_online_selector_or_claim",
        ],
        "failures": sorted(set(failures)),
        "failed_count": len(set(failures)),
        "promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_or_camp_over_dp_claim_authorized": False,
    }


def _decision(
    *,
    passed: bool,
    checks: list[dict[str, Any]],
    acquisition: dict[str, Any],
    execution: dict[str, Any],
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "execution_enabled" in failed:
        failure_class = "explicit_candidate_index_replay_outcome_acquisition_execution_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_drift"
    elif "runbook_exit_code" in failed:
        failure_class = "candidate_index_replay_runbook_failed"
    elif "candidate_closed_loop_outcome_records" in failed:
        failure_class = "candidate_index_closed_loop_outcome_acquisition_incomplete"
    else:
        failure_class = "candidate_index_replay_outcome_acquisition_execution_contract_failure"
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else FAILED_NEXT_WORK,
        "objective_3200_candidate_index_replay_outcome_acquisition_execution_passed": bool(passed),
        "candidate_index_replay_execution_executed_by_this_gate": bool(execution["attempted"]),
        "outcome_acquisition_executed_by_this_gate": bool(execution["attempted"]),
        "objective_required_records": acquisition["objective_required_records"],
        "candidate_closed_loop_outcome_records": acquisition["candidate_closed_loop_outcome_records"],
        "missing_candidate_closed_loop_outcome_records": acquisition["missing_candidate_closed_loop_outcome_records"],
        "paired_record_key_count": acquisition["paired_record_key_count"],
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    return decision


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    runbook_path = output_dir / RUNBOOK_NAME
    if not runbook_path.is_file():
        runbook_path.write_text(
            _render_runbook(
                commands=report["command_manifest"]["commands_as_lists"]
                if "commands_as_lists" in report["command_manifest"]
                else [item["command"] for item in report["command_manifest"]["commands"]],
                current_camp_head=report["heads"]["current_camp_head"],
                current_dp_head=report["heads"]["current_dp_head"],
                candidate_output_root=Path(report["inputs"]["candidate_index_output_root"]),
            ),
            encoding="utf-8",
        )
    json_path = output_dir / EXECUTION_JSON_NAME
    md_path = output_dir / EXECUTION_MD_NAME
    json_path.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    sha_entries = [json_path, md_path, runbook_path]
    for optional_name in ("runbook.stdout.log", "runbook.stderr.log", "runbook.exit"):
        optional = output_dir / optional_name
        if optional.exists():
            sha_entries.append(optional)
    (output_dir / "SHA256SUMS").write_text(
        "\n".join(f"{_sha256(path)}  {path.name}" for path in sha_entries) + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    acquisition = report["strict_pairing_summary"]
    execution = report["execution"]
    no_go = report["no_go_report"]
    return "\n".join(
        [
            "# Objective-3200 Candidate-Index Replay Outcome-Acquisition Execution",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failure class: `{decision['failure_class']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
            "## Execution",
            "",
            f"- Attempted: `{execution['attempted']}`",
            f"- Commands executed: `{execution['commands_executed']}`",
            f"- First failed command: `{execution['first_failed_command']}`",
            f"- Runbook exit code: `{execution['runbook_exit_code']}`",
            "",
            "## Objective",
            "",
            f"- Required records: `{acquisition['objective_required_records']}`",
            f"- Candidate records: `{acquisition['candidate_index_record_count']}`",
            f"- Candidate closed-loop outcome records: `{acquisition['candidate_closed_loop_outcome_records']}`",
            f"- Missing candidate outcomes: `{acquisition['missing_candidate_closed_loop_outcome_records']}`",
            f"- Strict paired record keys: `{acquisition['paired_record_key_count']}`",
            f"- Satisfied: `{acquisition['objective_3200_candidate_index_outcome_acquisition_satisfied']}`",
            "",
            "## No-Go",
            "",
            f"- Failed count: `{no_go['failed_count']}`",
            f"- Failures: `{no_go['failures']}`",
            "",
            "This gate does not promote, deploy, enable an online selector, or make safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _render_runbook(
    *,
    commands: list[list[str]],
    current_camp_head: str,
    current_dp_head: str,
    candidate_output_root: Path,
) -> str:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Generated by the objective-3200 candidate-index replay outcome-acquisition execution gate.",
        f'if [ "${{{GUARD_ENV_VAR}:-}}" != "1" ]; then',
        "  echo 'Refusing to run: candidate-index replay outcome acquisition guard is not set' >&2",
        "  exit 40",
        "fi",
        "source /etc/network_turbo >/dev/null 2>&1 || true",
        f"test \"$(git -C /root/autodl-tmp/camp_core rev-parse HEAD)\" = {shlex.quote(current_camp_head)}",
        f"test \"$(git -C /root/autodl-tmp/Diffusion-Planner rev-parse HEAD)\" = {shlex.quote(current_dp_head)}",
        f"if [ -e {shlex.quote(str(candidate_output_root))} ]; then",
        "  echo 'Refusing to run: candidate-index output root already exists' >&2",
        "  exit 44",
        "fi",
        "",
    ]
    for index, command in enumerate(commands, start=1):
        lines.append(f"echo 'Running candidate-index replay outcome command {index}/{len(commands)}'")
        lines.append(shlex.join(command))
        lines.append("")
    return "\n".join(lines)


def _source_hashes(
    *,
    artifact_dir: Path,
    review_json: Path,
    review_md: Path,
    review_sha256s: Path,
    source_runtime_runbook: Path,
) -> dict[str, Any]:
    files = {
        "artifact_root_sha256s": artifact_dir / "SHA256SUMS",
        "review_json": review_json,
        "review_md": review_md,
        "review_sha256s": review_sha256s,
        "source_runtime_runbook": source_runtime_runbook,
    }
    return {name: _sha256(path) for name, path in files.items() if path.is_file()}


def _drop_record_keys(summary: dict[str, Any]) -> dict[str, Any]:
    dropped = dict(summary)
    dropped.pop("record_keys", None)
    return dropped


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
        _expect("root_json_sha", _sha_for_suffix(root_sha256s, f"review/{SOURCE_STATIC_REVIEW_JSON_NAME}"), _sha256(files["review_json"])),
        _expect("root_md_sha", _sha_for_suffix(root_sha256s, f"review/{SOURCE_STATIC_REVIEW_MD_NAME}"), _sha256(files["review_md"])),
        _expect("root_review_sha256s_sha", _sha_for_suffix(root_sha256s, "review/SHA256SUMS"), _sha256(files["review_sha256s"])),
        _expect("nested_json_sha", _sha_for_suffix(nested_sha256s, SOURCE_STATIC_REVIEW_JSON_NAME), _sha256(files["review_json"])),
        _expect("nested_md_sha", _sha_for_suffix(nested_sha256s, SOURCE_STATIC_REVIEW_MD_NAME), _sha256(files["review_md"])),
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


def _arg_value(command: list[str], flag: str) -> str | None:
    try:
        return command[command.index(flag) + 1]
    except (ValueError, IndexError):
        return None


def _replace_arg(command: list[str], flag: str, value: str) -> None:
    index = command.index(flag)
    command[index + 1] = value


def _record_key(root: Path, log: Path, index: int) -> str:
    try:
        rel = log.relative_to(root).as_posix()
    except ValueError:
        rel = str(log)
    return f"{rel}#{index:04d}"


def _records_from_payload(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return payload["records"]
    return []


def _seed_from_path(path: Path) -> int | None:
    for part in path.parts:
        match = re.fullmatch(r"seed_(\d+)", part)
        if match:
            return int(match.group(1))
    return None


def _path_has_any_marker(path: Path, markers: tuple[str, ...]) -> bool:
    text = path.as_posix().lower()
    return any(marker in text for marker in markers)


def _is_simplex(values: Any) -> bool:
    if not isinstance(values, list) or not values:
        return True
    numbers = [_number_or_none(value) for value in values]
    if any(value is None for value in numbers):
        return False
    concrete = [float(value) for value in numbers if value is not None]
    if any(value < -1e-9 for value in concrete):
        return False
    return math.isclose(sum(concrete), 1.0, rel_tol=1e-6, abs_tol=1e-6)


def _number_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


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
        if path.replace("\\", "/").endswith(suffix):
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


def _is_git_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
