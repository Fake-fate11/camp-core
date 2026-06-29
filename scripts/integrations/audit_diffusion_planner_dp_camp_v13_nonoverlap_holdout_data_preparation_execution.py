#!/usr/bin/env python3
"""Audit a completed v13 non-overlap holdout data-preparation artifact.

This is a read-only evidence audit for a completed fixed-DP data-preparation
run. It does not run replay, generate candidates, train CAMP, modify Diffusion
Planner, promote artifacts, deploy, or make safety/CAMP-over-DP Top-1 claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Optional


SCHEMA_VERSION = "dp_camp_v13_nonoverlap_holdout_data_preparation_execution_audit_v1"
READY_STATUS = "dp_camp_v13_nonoverlap_holdout_data_preparation_execution_audit_passed"
REJECT_STATUS = "dp_camp_v13_nonoverlap_holdout_data_preparation_execution_audit_rejected"
SOURCE_SCHEMA_VERSION = "dp_camp_v13_nonoverlap_holdout_data_preparation_v1"
SOURCE_READY_STATUS = "dp_camp_v13_nonoverlap_holdout_data_preparation_complete"
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_static_dp_reward_training_preflight_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
FORMAL_SEEDS = {11, 12, 13}
POSTSELECTION_FIELDS = (
    "perfect_tracker_command_postselection",
    "traffic_light_hybrid_postselection",
    "underprogress_relaxation",
    "splice_shadow_rule",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only audit for a completed v13 non-overlap holdout "
            "data-preparation artifact."
        )
    )
    parser.add_argument("--source_artifact_dir", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_log_count", type=int, default=128)
    parser.add_argument("--expected_steps_per_log", type=int, default=100)
    parser.add_argument("--expected_records", type=int, default=12800)
    parser.add_argument("--expected_candidate_count", type=int, default=8)
    parser.add_argument("--expected_atom_count", type=int, default=14)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_source_sha256sums", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_artifact_dir=args.source_artifact_dir,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_log_count=args.expected_log_count,
        expected_steps_per_log=args.expected_steps_per_log,
        expected_records=args.expected_records,
        expected_candidate_count=args.expected_candidate_count,
        expected_atom_count=args.expected_atom_count,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_source_sha256sums.parent.mkdir(parents=True, exist_ok=True)
    args.output_source_sha256sums.write_text(
        "\n".join(report["source_artifact_post_execution_sha256sums"]) + "\n",
        encoding="utf-8",
    )
    args.output_json.write_text(
        json.dumps(_stable(report), indent=2) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    _write_sha256sums(args.output_json.parent)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_artifact_dir: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_log_count: int = 128,
    expected_steps_per_log: int = 100,
    expected_records: int = 12800,
    expected_candidate_count: int = 8,
    expected_atom_count: int = 14,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    source_root = source_artifact_dir.resolve()
    holdout_dir = source_root / "holdout_data"
    summary_path = source_root / "data_preparation_summary.json"
    summary = _load_json_dict(summary_path)
    decision = _dict(summary.get("final_decision"))
    execution = _dict(summary.get("execution"))
    selection_summary = _dict(summary.get("selection_log_summary"))
    registry_summary = _dict(summary.get("registry_summary"))
    training_contract = _dict(summary.get("training_data_contract"))
    heads = _dict(summary.get("heads"))
    audit_text = _read_text(v13_audit_md)
    actual_logs = _scan_selection_logs(holdout_dir, expected_steps_per_log)
    registry_files = _registry_file_summary(holdout_dir)
    source_sha_check = _verify_source_sha256sums(source_root)
    launch_metadata = _source_launch_metadata(source_root)

    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, observed: Any, expected: Any = True) -> None:
        checks.append(
            {
                "name": name,
                "passed": bool(passed),
                "observed": observed,
                "expected": expected,
            }
        )

    check("source_artifact_dir_exists", source_root.is_dir(), str(source_root))
    check("source_summary_exists", summary_path.is_file(), str(summary_path))
    check("source_schema_version", summary.get("schema_version") == SOURCE_SCHEMA_VERSION, summary.get("schema_version"), SOURCE_SCHEMA_VERSION)
    check("source_final_status", decision.get("status") == SOURCE_READY_STATUS, decision.get("status"), SOURCE_READY_STATUS)
    check("source_final_passed", decision.get("passed") is True, decision.get("passed"))
    check("source_final_failed_checks_empty", decision.get("failed_checks") == [], decision.get("failed_checks"), [])
    check("source_authorized_next_work", decision.get("authorized_next_work") == authorized_next_work, decision.get("authorized_next_work"), authorized_next_work)
    check("source_training_preflight_authorized_next", decision.get("training_preflight_authorized_next") is True, decision.get("training_preflight_authorized_next"))
    check("source_data_preparation_executed", decision.get("data_preparation_executed") is True, decision.get("data_preparation_executed"))
    check("source_fixed_dp_candidate_generation_executed", decision.get("fixed_dp_candidate_generation_executed") is True, decision.get("fixed_dp_candidate_generation_executed"))
    check("source_training_not_executed", decision.get("training_executed") is False, decision.get("training_executed"), False)
    check("source_replay_evaluation_not_executed", decision.get("replay_evaluation_executed") is False, decision.get("replay_evaluation_executed"), False)
    check("source_dp_not_modified", decision.get("dp_modification_authorized") is False, decision.get("dp_modification_authorized"), False)
    check("source_no_camp_candidate_generation", decision.get("candidate_generation_by_camp_authorized") is False, decision.get("candidate_generation_by_camp_authorized"), False)
    check("source_no_trajectory_generation", decision.get("trajectory_generation_by_camp_authorized") is False, decision.get("trajectory_generation_by_camp_authorized"), False)
    check("source_no_trajectory_modification", decision.get("trajectory_modification_by_camp_authorized") is False, decision.get("trajectory_modification_by_camp_authorized"), False)
    check("source_no_selector_promotion", decision.get("selector_promotion_authorized") is False, decision.get("selector_promotion_authorized"), False)
    check("source_no_atom_promotion", decision.get("atom_promotion_authorized") is False, decision.get("atom_promotion_authorized"), False)
    check("source_no_deployment", decision.get("deployment_authorized") is False, decision.get("deployment_authorized"), False)
    check("source_no_safety_claim", decision.get("safety_benefit_claim_authorized") is False, decision.get("safety_benefit_claim_authorized"), False)
    check("source_no_camp_over_dp_top1_claim", decision.get("camp_over_dp_top1_claim_authorized") is False, decision.get("camp_over_dp_top1_claim_authorized"), False)
    check("source_candidate_operation", decision.get("candidate_operation") == "fixed DP candidate reranking only", decision.get("candidate_operation"), "fixed DP candidate reranking only")
    check("source_score_expression", decision.get("score_expression") == SCORE_EXPRESSION, decision.get("score_expression"), SCORE_EXPRESSION)
    check("source_approved_atoms_nonnegative_simplex", decision.get("approved_atoms_nonnegative_simplex_only") is True, decision.get("approved_atoms_nonnegative_simplex_only"))
    check("source_master_convexity_preserved", decision.get("simplex_cvar_l2_master_convexity_preserved") is True, decision.get("simplex_cvar_l2_master_convexity_preserved"))
    check("execution_commands_completed", execution.get("commands_completed") == expected_log_count, execution.get("commands_completed"), expected_log_count)
    check("execution_commands_planned", execution.get("commands_planned") == expected_log_count, execution.get("commands_planned"), expected_log_count)
    check("execution_failed_commands_empty", execution.get("failed_commands") == [], execution.get("failed_commands"), [])
    check("summary_log_count", selection_summary.get("log_count") == expected_log_count, selection_summary.get("log_count"), expected_log_count)
    check("summary_record_count", selection_summary.get("record_count") == expected_records, selection_summary.get("record_count"), expected_records)
    check("summary_expected_log_count", selection_summary.get("expected_log_count") == expected_log_count, selection_summary.get("expected_log_count"), expected_log_count)
    check("summary_expected_records", selection_summary.get("expected_records") == expected_records, selection_summary.get("expected_records"), expected_records)
    check("summary_executed_index_violations_zero", selection_summary.get("executed_index_violations") == 0, selection_summary.get("executed_index_violations"), 0)
    check("summary_default_off_missing_zero", selection_summary.get("default_off_missing") == 0, selection_summary.get("default_off_missing"), 0)
    check("summary_atom_schema_violations_zero", selection_summary.get("atom_schema_violations") == 0, selection_summary.get("atom_schema_violations"), 0)
    check("summary_forbidden_runtime_flags_zero", selection_summary.get("forbidden_runtime_flags") == 0, selection_summary.get("forbidden_runtime_flags"), 0)
    check("actual_log_count", actual_logs["log_count"] == expected_log_count, actual_logs["log_count"], expected_log_count)
    check("actual_record_count", actual_logs["record_count"] == expected_records, actual_logs["record_count"], expected_records)
    check("actual_records_per_log", actual_logs["wrong_step_logs"] == [], actual_logs["wrong_step_logs"], [])
    check("actual_executed_index_violations_zero", actual_logs["executed_index_violations"] == 0, actual_logs["executed_index_violations"], 0)
    check("actual_shadow_index_missing_zero", actual_logs["shadow_index_missing"] == 0, actual_logs["shadow_index_missing"], 0)
    check("actual_default_off_missing_zero", actual_logs["default_off_missing"] == 0, actual_logs["default_off_missing"], 0)
    check("actual_atom_schema_violations_zero", actual_logs["atom_schema_violations"] == 0, actual_logs["atom_schema_violations"], 0)
    check("actual_forbidden_runtime_flags_zero", actual_logs["forbidden_runtime_flags"] == 0, actual_logs["forbidden_runtime_flags"], 0)
    check("formal_seed_count_zero", actual_logs["formal_seed_count"] == 0, actual_logs["formal_seed_count"], 0)
    check("candidate_tensor_registry_count", registry_summary.get("candidate_tensor_hash_count") == expected_records, registry_summary.get("candidate_tensor_hash_count"), expected_records)
    check("candidate_tensor_registry_unique_count", registry_summary.get("unique_candidate_tensor_hash_count") == expected_records, registry_summary.get("unique_candidate_tensor_hash_count"), expected_records)
    check("path_signature_registry_count", registry_summary.get("path_signature_count") == expected_log_count, registry_summary.get("path_signature_count"), expected_log_count)
    check("record_identity_registry_count", registry_summary.get("record_identity_hash_count") == expected_records, registry_summary.get("record_identity_hash_count"), expected_records)
    check("record_identity_registry_unique_count", registry_summary.get("unique_record_identity_hash_count") == expected_records, registry_summary.get("unique_record_identity_hash_count"), expected_records)
    check("candidate_tensor_registry_file", registry_files["candidate_tensor_hash_registry"]["exists"], registry_files["candidate_tensor_hash_registry"])
    check("path_signature_registry_file", registry_files["path_signature_registry"]["exists"], registry_files["path_signature_registry"])
    check("record_identity_registry_file", registry_files["record_identity_hash_registry"]["exists"], registry_files["record_identity_hash_registry"])
    check("selection_logs_manifest_file", registry_files["selection_logs"]["exists"], registry_files["selection_logs"])
    check("candidate_tensor_registry_file_count", registry_files["candidate_tensor_hash_registry"]["entries"] == expected_records, registry_files["candidate_tensor_hash_registry"]["entries"], expected_records)
    check("path_signature_registry_file_count", registry_files["path_signature_registry"]["entries"] == expected_log_count, registry_files["path_signature_registry"]["entries"], expected_log_count)
    check("record_identity_registry_file_count", registry_files["record_identity_hash_registry"]["entries"] == expected_records, registry_files["record_identity_hash_registry"]["entries"], expected_records)
    check("selection_logs_manifest_file_count", registry_files["selection_logs"]["lines"] == expected_log_count, registry_files["selection_logs"]["lines"], expected_log_count)
    check("training_data_contract_passed", training_contract.get("passed") is True, training_contract.get("passed"))
    check("training_data_contract_records", training_contract.get("records") == expected_records, training_contract.get("records"), expected_records)
    check("training_data_contract_failed_records_zero", training_contract.get("failed_records") == 0, training_contract.get("failed_records"), 0)
    check("training_input_contract_satisfied", training_contract.get("future_training_input_contract_satisfied") is True, training_contract.get("future_training_input_contract_satisfied"))
    check("source_camp_head_present", _is_sha(heads.get("current_camp_head")), heads.get("current_camp_head"), "40-hex sha")
    check("source_camp_origin_main_present", _is_sha(heads.get("current_camp_origin_main")), heads.get("current_camp_origin_main"), "40-hex sha")
    check("source_camp_head_matches_origin_main", heads.get("current_camp_head") == heads.get("current_camp_origin_main"), heads, "source CAMP head equals source origin/main")
    check("audit_camp_head_present", _is_sha(current_camp_head), current_camp_head, "40-hex sha")
    check("audit_camp_origin_main_present", _is_sha(current_camp_origin_main), current_camp_origin_main, "40-hex sha")
    check("audit_camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, {"current": current_camp_head, "origin": current_camp_origin_main}, "audit CAMP head equals audit origin/main")
    check("source_current_dp_head", heads.get("current_dp_head") == required_dp_head, heads.get("current_dp_head"), required_dp_head)
    check("source_required_dp_head", heads.get("required_dp_head") == required_dp_head, heads.get("required_dp_head"), required_dp_head)
    check("audit_current_dp_head", current_dp_head == required_dp_head, current_dp_head, required_dp_head)
    check("audit_current_next_work", f"next_work_target={authorized_current_work}" in audit_text, _latest_value(audit_text, "next_work_target"), authorized_current_work)
    check("audit_data_preparation_authorized", "data_preparation_authorized_by_current_boundary=True" in audit_text, "data_preparation_authorized_by_current_boundary=True")
    check("audit_training_execution_not_authorized", "training_execution_authorized_by_current_boundary=False" in audit_text, "training_execution_authorized_by_current_boundary=False")
    check("audit_dp_modification_not_authorized", "dp_modification_authorized_by_current_boundary=False" in audit_text, "dp_modification_authorized_by_current_boundary=False")

    failed = [row["name"] for row in checks if not row["passed"]]
    warnings = _warnings(source_sha_check, launch_metadata)
    source_hashes = _hash_tree(source_root)
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "read_only": True,
            "data_preparation_execution_audit_only": True,
            "data_preparation_executed_by_source": True,
            "fixed_dp_candidate_generation_executed_by_source": True,
            "training_executed": False,
            "replay_evaluation_executed": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "dp_modification": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "source_artifact_dir": str(source_root),
        "source_summary_json": str(summary_path),
        "audit_heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "source_heads": heads,
        "source_decision": decision,
        "source_execution": execution,
        "selection_log_summary": selection_summary,
        "actual_selection_log_scan": actual_logs,
        "registry_summary": registry_summary,
        "registry_files": registry_files,
        "training_data_contract": training_contract,
        "source_sha256sums_verification": source_sha_check,
        "source_launch_metadata": launch_metadata,
        "source_artifact_post_execution_sha256sums": source_hashes,
        "checks": checks,
        "warnings": warnings,
        "final_decision": _decision(passed, failed, warnings, authorized_next_work),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    selection = report["actual_selection_log_scan"]
    registry = report["registry_summary"]
    return "\n".join(
        [
            "# V13 Non-Overlap Holdout Data-Preparation Execution Audit",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Source artifact: `{report['source_artifact_dir']}`",
            f"- Selection logs: `{selection['log_count']}`",
            f"- Records: `{selection['record_count']}`",
            f"- Candidate tensor hashes: `{registry.get('candidate_tensor_hash_count')}`",
            f"- Record identity hashes: `{registry.get('record_identity_hash_count')}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Warnings: `{decision['warnings']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
        ]
    )


def _decision(
    passed: bool,
    failed: list[str],
    warnings: list[str],
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": sorted(failed),
        "warnings": sorted(warnings),
        "authorized_next_work": authorized_next_work if passed else None,
        "training_preflight_authorized_next": bool(passed),
        "data_preparation_executed": True,
        "fixed_dp_candidate_generation_executed": True,
        "training_executed": False,
        "replay_evaluation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
        "approved_atoms_nonnegative_simplex_only": True,
        "simplex_cvar_l2_master_convexity_preserved": True,
    }


def _scan_selection_logs(root: Path, expected_steps_per_log: int) -> dict[str, Any]:
    logs = sorted(root.rglob("camp_selection_log.json"))
    record_count = 0
    wrong_step_logs: list[str] = []
    executed_index_violations = 0
    shadow_index_missing = 0
    default_off_missing = 0
    atom_schema_violations = 0
    forbidden_runtime_flags = 0
    formal_seed_count = 0
    for log_path in logs:
        records = _load_json_list(log_path)
        if len(records) != expected_steps_per_log:
            wrong_step_logs.append(str(log_path))
        formal_seed_count += _formal_seed_mentions(log_path)
        record_count += len(records)
        for record in records:
            if record.get("selected_index") != 0 or record.get("executed_index") != 0:
                executed_index_violations += 1
            if record.get("shadow_selected_index") is None:
                shadow_index_missing += 1
            if not isinstance(record.get("default_off_shadow_selector"), dict):
                default_off_missing += 1
            if record.get("atom_schema_version") != ATOM_SCHEMA_VERSION:
                atom_schema_violations += 1
            if any(record.get(field) is not None for field in POSTSELECTION_FIELDS):
                forbidden_runtime_flags += 1
            generation = _dict(record.get("candidate_generation_contract"))
            if generation.get("reference_blend_steps") is not None:
                forbidden_runtime_flags += 1
            if generation.get("guidance_enabled") not in (False, None):
                forbidden_runtime_flags += 1
    return {
        "log_count": len(logs),
        "record_count": record_count,
        "wrong_step_logs": wrong_step_logs,
        "executed_index_violations": executed_index_violations,
        "shadow_index_missing": shadow_index_missing,
        "default_off_missing": default_off_missing,
        "atom_schema_violations": atom_schema_violations,
        "forbidden_runtime_flags": forbidden_runtime_flags,
        "formal_seed_count": formal_seed_count,
    }


def _registry_file_summary(root: Path) -> dict[str, dict[str, Any]]:
    return {
        "candidate_tensor_hash_registry": _json_entries_file(root / "candidate_tensor_hash_registry.json"),
        "path_signature_registry": _json_entries_file(root / "path_signature_registry.json"),
        "record_identity_hash_registry": _json_entries_file(root / "record_identity_hash_registry.json"),
        "selection_logs": _line_file(root / "selection_logs.txt"),
    }


def _json_entries_file(path: Path) -> dict[str, Any]:
    payload = _load_json_dict(path)
    entries = payload.get("entries")
    return {
        "path": str(path),
        "exists": path.is_file(),
        "entries": len(entries) if isinstance(entries, list) else None,
        "sha256": _sha256(path) if path.is_file() else None,
    }


def _line_file(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    return {
        "path": str(path),
        "exists": path.is_file(),
        "lines": len([line for line in lines if line.strip()]),
        "sha256": _sha256(path) if path.is_file() else None,
    }


def _verify_source_sha256sums(root: Path) -> dict[str, Any]:
    sha_path = root / "SHA256SUMS"
    if not sha_path.is_file():
        return {
            "path": str(sha_path),
            "exists": False,
            "checked": 0,
            "matches": 0,
            "mismatches": [],
            "missing": [],
            "verifies": False,
        }
    mismatches = []
    missing = []
    matches = 0
    checked = 0
    for line in sha_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        expected_hash, relative = parts
        path = root / relative.strip()
        checked += 1
        if not path.is_file():
            missing.append(relative.strip())
            continue
        actual_hash = _sha256(path)
        if actual_hash != expected_hash:
            mismatches.append(
                {
                    "path": relative.strip(),
                    "expected": expected_hash,
                    "actual": actual_hash,
                }
            )
        else:
            matches += 1
    return {
        "path": str(sha_path),
        "exists": True,
        "checked": checked,
        "matches": matches,
        "mismatches": mismatches,
        "missing": missing,
        "verifies": not mismatches and not missing,
    }


def _source_launch_metadata(root: Path) -> dict[str, Any]:
    exit_path = root / "run_data_preparation.exit"
    pid_path = root / "execution.pid"
    stdout_path = root / "execution.stdout.txt"
    stderr_path = root / "execution.stderr.txt"
    return {
        "run_data_preparation_exit_path": str(exit_path),
        "run_data_preparation_exit_present": exit_path.is_file(),
        "run_data_preparation_exit_value": (
            exit_path.read_text(encoding="utf-8").strip() if exit_path.is_file() else None
        ),
        "execution_pid_present": pid_path.is_file(),
        "execution_pid": pid_path.read_text(encoding="utf-8").strip() if pid_path.is_file() else None,
        "execution_stdout_sha256": _sha256(stdout_path) if stdout_path.is_file() else None,
        "execution_stderr_sha256": _sha256(stderr_path) if stderr_path.is_file() else None,
        "execution_stderr_size": stderr_path.stat().st_size if stderr_path.is_file() else None,
    }


def _warnings(
    source_sha_check: dict[str, Any],
    launch_metadata: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if not launch_metadata.get("run_data_preparation_exit_present"):
        warnings.append("source_raw_run_data_preparation_exit_missing")
    elif launch_metadata.get("run_data_preparation_exit_value") != "0":
        warnings.append("source_raw_run_data_preparation_exit_nonzero")
    if not source_sha_check.get("verifies"):
        warnings.append("source_sha256sums_does_not_verify_post_execution")
    return warnings


def _hash_tree(root: Path) -> list[str]:
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            lines.append(f"{_sha256(path)}  {path.relative_to(root).as_posix()}")
    return lines


def _write_sha256sums(root: Path) -> None:
    mutable_wrapper_files = {
        "audit.exit",
        "audit.stderr.txt",
        "audit.stdout.txt",
        "execution.pid",
        "execution.stderr.txt",
        "execution.stdout.txt",
    }
    lines = []
    for path in sorted(root.rglob("*")):
        if (
            path.is_file()
            and path.name != "SHA256SUMS"
            and path.name not in mutable_wrapper_files
        ):
            lines.append(f"{_sha256(path)}  {path.relative_to(root).as_posix()}")
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        rows = payload.get("records", payload.get("selection_records", []))
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _formal_seed_mentions(path: Path) -> int:
    count = 0
    text = path.as_posix()
    for match in re.finditer(r"seed_(\d+)", text):
        if int(match.group(1)) in FORMAL_SEEDS:
            count += 1
    return count


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def _latest_value(text: str, key: str) -> Optional[str]:
    marker = f"{key}="
    if marker not in text:
        return None
    return text.rsplit(marker, maxsplit=1)[1].splitlines()[0]


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
