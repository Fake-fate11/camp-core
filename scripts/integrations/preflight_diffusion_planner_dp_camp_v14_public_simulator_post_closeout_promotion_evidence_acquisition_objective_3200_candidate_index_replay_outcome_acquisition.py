#!/usr/bin/env python3
"""Preflight objective-3200 candidate-index replay outcome acquisition.

This gate is read-only and preflight-only. It consumes the audited
outcome-acquisition preflight-plan static review and its source plan artifact,
then locks the future execution contract. It does not run candidate-index
replay, acquire outcomes, train, generate candidates, modify Diffusion Planner,
promote, deploy, enable an online selector, or make claims.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_source_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_candidate_index_"
        "replay_outcome_acquisition_preflight_plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_replay_outcome_acquisition_preflight_plan_static_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_source_review_module()
PLAN_MODULE = SOURCE_REVIEW_MODULE.PLAN_MODULE

FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_REVIEW_SCHEMA = SOURCE_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_STATUS = SOURCE_REVIEW_MODULE.READY_STATUS
SOURCE_REVIEW_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
SOURCE_PLAN_SCHEMA = SOURCE_REVIEW_MODULE.SOURCE_PLAN_SCHEMA
SOURCE_PLAN_STATUS = SOURCE_REVIEW_MODULE.SOURCE_PLAN_STATUS
SOURCE_PLAN_JSON_NAME = SOURCE_REVIEW_MODULE.SOURCE_PLAN_JSON_NAME
SOURCE_PLAN_MD_NAME = SOURCE_REVIEW_MODULE.SOURCE_PLAN_MD_NAME
BLOCKED_ACTIONS = SOURCE_REVIEW_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = SOURCE_REVIEW_MODULE.FALSE_EXECUTION_FLAGS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_replay_outcome_acquisition_preflight_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight_static_review_only"
)

PREFLIGHT_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight.json"
)
PREFLIGHT_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_replay_outcome_acquisition_preflight.md"
)

OBJECTIVE_REQUIRED_RECORDS = PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS
EXPECTED_PREFLIGHT_ITEMS = (
    "lock_static_review_and_plan_artifacts",
    "verify_fixed_dp_head_and_artifact_hashes",
    "predeclare_candidate_index_replay_command_inputs",
    "predeclare_3200_strict_pairing_manifest_requirements",
    "predeclare_outcome_acquisition_output_contract",
    "authorize_static_review_only",
)
EXPECTED_PLANNED_OUTPUTS = (
    "candidate_index_replay_command_manifest",
    "fixed_dp_candidate_tensor_identity_table",
    "shadow_selected_candidate_binding_manifest",
    "shadow_selected_closed_loop_outcome_manifest",
    "strict_top1_shadow_pairing_manifest",
    "no_go_and_failure_attribution_report",
)
PREFLIGHT_NO_GO = (
    "source_static_review_missing_or_failed",
    "source_plan_missing_or_failed",
    "dp_head_drift",
    "candidate_index_replay_harness_missing",
    "candidate_tensor_identity_missing_or_mutated",
    "shadow_selected_candidate_not_from_fixed_dp_tensor",
    "camp_generates_repairs_rewrites_or_blends_trajectory",
    "full36_or_formal_seed_11_12_13_present",
    "closed_loop_outcome_used_for_training_or_online_input",
    "non_affine_score_or_non_simplex_weight",
    "promotion_deployment_online_selector_or_claim",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_md", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_preflight_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_plan_json", type=Path, required=True)
    parser.add_argument("--source_preflight_plan_md", type=Path, required=True)
    parser.add_argument("--source_preflight_plan_sha256s", type=Path, required=True)
    parser.add_argument("--runtime_replay_script_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_record_count", type=int, default=OBJECTIVE_REQUIRED_RECORDS)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_preflight",
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
        source_preflight_plan_artifact_dir=args.source_preflight_plan_artifact_dir,
        source_preflight_plan_json=args.source_preflight_plan_json,
        source_preflight_plan_md=args.source_preflight_plan_md,
        source_preflight_plan_sha256s=args.source_preflight_plan_sha256s,
        runtime_replay_script_py=args.runtime_replay_script_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_record_count=args.expected_record_count,
        enabled=args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_preflight,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(PLAN_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_static_review_md: Path,
    source_static_review_sha256s: Path,
    source_preflight_plan_artifact_dir: Path,
    source_preflight_plan_json: Path,
    source_preflight_plan_md: Path,
    source_preflight_plan_sha256s: Path,
    runtime_replay_script_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_record_count: int = OBJECTIVE_REQUIRED_RECORDS,
    enabled: bool = False,
) -> dict[str, Any]:
    static_artifact_dir = source_static_review_artifact_dir.resolve()
    plan_artifact_dir = source_preflight_plan_artifact_dir.resolve()
    paths = {
        "source_static_review_json": source_static_review_json.resolve(),
        "source_static_review_md": source_static_review_md.resolve(),
        "source_static_review_sha256s": source_static_review_sha256s.resolve(),
        "source_preflight_plan_json": source_preflight_plan_json.resolve(),
        "source_preflight_plan_md": source_preflight_plan_md.resolve(),
        "source_preflight_plan_sha256s": source_preflight_plan_sha256s.resolve(),
        "runtime_replay_script_py": runtime_replay_script_py.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    static_files = {
        "heads": static_artifact_dir / "HEADS",
        "command": static_artifact_dir / "COMMAND",
        "stdout": static_artifact_dir / "stdout",
        "stderr": static_artifact_dir / "stderr",
        "run_exit": static_artifact_dir / "run.exit",
        "root_sha256s": static_artifact_dir / "SHA256SUMS",
        "review_json": static_artifact_dir / "review" / SOURCE_REVIEW_JSON_NAME,
        "review_md": static_artifact_dir / "review" / SOURCE_REVIEW_MD_NAME,
        "review_sha256s": static_artifact_dir / "review" / "SHA256SUMS",
    }
    plan_files = {
        "heads": plan_artifact_dir / "HEADS",
        "command": plan_artifact_dir / "COMMAND",
        "stdout": plan_artifact_dir / "stdout",
        "stderr": plan_artifact_dir / "stderr",
        "run_exit": plan_artifact_dir / "run.exit",
        "root_sha256s": plan_artifact_dir / "SHA256SUMS",
        "plan_json": plan_artifact_dir / "plan" / SOURCE_PLAN_JSON_NAME,
        "plan_md": plan_artifact_dir / "plan" / SOURCE_PLAN_MD_NAME,
        "plan_sha256s": plan_artifact_dir / "plan" / "SHA256SUMS",
    }
    source_review = PLAN_MODULE._read_json_dict(paths["source_static_review_json"])
    source_plan = PLAN_MODULE._read_json_dict(paths["source_preflight_plan_json"])
    v14_text = PLAN_MODULE._read_text(paths["v14_audit_md"])
    status_text = PLAN_MODULE._read_text(paths["current_status_md"])
    runtime_text = PLAN_MODULE._read_text(paths["runtime_replay_script_py"])
    static_heads = PLAN_MODULE._parse_key_values(PLAN_MODULE._read_text(static_files["heads"]))
    plan_heads = PLAN_MODULE._parse_key_values(PLAN_MODULE._read_text(plan_files["heads"]))
    static_root_sha256s = PLAN_MODULE._read_sha256sums(static_files["root_sha256s"])
    static_nested_sha256s = PLAN_MODULE._read_sha256sums(paths["source_static_review_sha256s"])
    plan_root_sha256s = PLAN_MODULE._read_sha256sums(plan_files["root_sha256s"])
    plan_nested_sha256s = PLAN_MODULE._read_sha256sums(paths["source_preflight_plan_sha256s"])
    static_run_exit = PLAN_MODULE._read_text(static_files["run_exit"]).strip()
    plan_run_exit = PLAN_MODULE._read_text(plan_files["run_exit"]).strip()
    runner_surface = PLAN_MODULE._runner_surface(runtime_text)
    source_summary = _source_summary(source_review, source_plan)
    checks = _checks(
        enabled=enabled,
        static_artifact_dir=static_artifact_dir,
        plan_artifact_dir=plan_artifact_dir,
        paths=paths,
        static_files=static_files,
        plan_files=plan_files,
        source_review=source_review,
        source_plan=source_plan,
        source_summary=source_summary,
        runner_surface=runner_surface,
        v14_text=v14_text,
        status_text=status_text,
        static_heads=static_heads,
        plan_heads=plan_heads,
        static_root_sha256s=static_root_sha256s,
        static_nested_sha256s=static_nested_sha256s,
        plan_root_sha256s=plan_root_sha256s,
        plan_nested_sha256s=plan_nested_sha256s,
        static_run_exit=static_run_exit,
        plan_run_exit=plan_run_exit,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_record_count=expected_record_count,
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "read_only": True,
            "preflight_only": True,
            "candidate_index_replay_outcome_acquisition_preflight_only": True,
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
            "source_static_review_artifact_dir": str(static_artifact_dir),
            "source_preflight_plan_artifact_dir": str(plan_artifact_dir),
            "output_dir": str(output_dir.resolve()),
            **{name: str(path) for name, path in paths.items()},
        },
        "source_hashes": {
            name: PLAN_MODULE._sha256(path)
            for name, path in {**paths, **static_files, **plan_files}.items()
            if path.is_file()
        },
        "source_summary": source_summary,
        "runner_surface_inventory": runner_surface,
        "preflight_items": [{"item": item} for item in EXPECTED_PREFLIGHT_ITEMS],
        "planned_outputs": list(EXPECTED_PLANNED_OUTPUTS),
        "no_go_register": list(PREFLIGHT_NO_GO),
        "future_execution_contract": _future_execution_contract(),
        "preflight_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, source_summary=source_summary),
    }


def _checks(
    *,
    enabled: bool,
    static_artifact_dir: Path,
    plan_artifact_dir: Path,
    paths: dict[str, Path],
    static_files: dict[str, Path],
    plan_files: dict[str, Path],
    source_review: dict[str, Any],
    source_plan: dict[str, Any],
    source_summary: dict[str, Any],
    runner_surface: dict[str, Any],
    v14_text: str,
    status_text: str,
    static_heads: dict[str, str],
    plan_heads: dict[str, str],
    static_root_sha256s: dict[str, str],
    static_nested_sha256s: dict[str, str],
    plan_root_sha256s: dict[str, str],
    plan_nested_sha256s: dict[str, str],
    static_run_exit: str,
    plan_run_exit: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_record_count: int,
) -> list[dict[str, Any]]:
    review_decision = PLAN_MODULE._dict(source_review.get("final_decision"))
    review_analysis = PLAN_MODULE._dict(source_review.get("analysis"))
    plan_decision = PLAN_MODULE._dict(source_plan.get("final_decision"))
    plan_analysis = PLAN_MODULE._dict(source_plan.get("analysis"))
    checks = [
        PLAN_MODULE._expect("preflight_enabled", enabled, True),
        PLAN_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        PLAN_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        PLAN_MODULE._expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        PLAN_MODULE._check("current_camp_head_is_sha", PLAN_MODULE._is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        PLAN_MODULE._expect("audit_latest_status", PLAN_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        PLAN_MODULE._expect("audit_latest_next_work", PLAN_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._expect("status_doc_latest_status", PLAN_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        PLAN_MODULE._expect("status_doc_latest_next_work", PLAN_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PLAN_MODULE._check("source_static_review_artifact_dir_exists", static_artifact_dir.is_dir(), str(static_artifact_dir), "directory"),
        PLAN_MODULE._check("source_preflight_plan_artifact_dir_exists", plan_artifact_dir.is_dir(), str(plan_artifact_dir), "directory"),
        PLAN_MODULE._expect("source_static_review_run_exit_zero", static_run_exit, "0"),
        PLAN_MODULE._expect("source_preflight_plan_run_exit_zero", plan_run_exit, "0"),
        PLAN_MODULE._expect("source_static_review_dp_head_fixed", PLAN_MODULE._kv(static_heads, "DP_HEAD", "dp_head"), required_dp_head),
        PLAN_MODULE._expect("source_preflight_plan_dp_head_fixed", PLAN_MODULE._kv(plan_heads, "DP_HEAD", "dp_head"), required_dp_head),
    ]
    for name, path in paths.items():
        checks.extend(PLAN_MODULE._path_checks(name, path, allow_empty=False))
    for name, path in static_files.items():
        checks.extend(PLAN_MODULE._path_checks(f"source_static_review_{name}", path, allow_empty=(name == "stderr")))
    for name, path in plan_files.items():
        checks.extend(PLAN_MODULE._path_checks(f"source_preflight_plan_{name}", path, allow_empty=(name == "stderr")))
    checks.extend(_static_artifact_hash_checks(static_files, static_root_sha256s, static_nested_sha256s))
    checks.extend(_plan_artifact_hash_checks(plan_files, plan_root_sha256s, plan_nested_sha256s))
    checks.extend(
        [
            PLAN_MODULE._expect("source_static_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA),
            PLAN_MODULE._expect("source_static_review_passed", review_decision.get("passed"), True),
            PLAN_MODULE._expect("source_static_review_status", review_decision.get("status"), SOURCE_REVIEW_STATUS),
            PLAN_MODULE._expect("source_static_review_authorized_next", review_decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
            PLAN_MODULE._expect("source_static_review_preflight_authorized", review_decision.get("objective_3200_candidate_index_replay_outcome_acquisition_preflight_authorized"), True),
            PLAN_MODULE._expect("source_static_review_read_only", review_analysis.get("read_only"), True),
            PLAN_MODULE._expect("source_static_review_static_review_only", review_analysis.get("static_review_only"), True),
            PLAN_MODULE._expect("source_preflight_plan_schema", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA),
            PLAN_MODULE._expect("source_preflight_plan_passed", plan_decision.get("passed"), True),
            PLAN_MODULE._expect("source_preflight_plan_status", plan_decision.get("status"), SOURCE_PLAN_STATUS),
            PLAN_MODULE._expect("source_preflight_plan_authorized_next", plan_decision.get("authorized_next_work"), SOURCE_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK),
            PLAN_MODULE._expect("source_preflight_plan_read_only", plan_analysis.get("read_only"), True),
            PLAN_MODULE._expect("source_preflight_plan_plan_only", plan_analysis.get("plan_only"), True),
            PLAN_MODULE._expect("objective_required_records", source_summary["objective_required_records"], expected_record_count),
            PLAN_MODULE._expect("candidate_closed_loop_outcome_records", source_summary["candidate_closed_loop_outcome_records"], 0),
            PLAN_MODULE._expect("missing_candidate_closed_loop_outcome_records", source_summary["missing_candidate_closed_loop_outcome_records"], expected_record_count),
            PLAN_MODULE._expect("runner_has_candidate_index_replay_flag", runner_surface["has_candidate_index_replay_flag"], True),
            PLAN_MODULE._expect("runner_has_harness_alias_flag", runner_surface["has_harness_alias_flag"], True),
            PLAN_MODULE._expect("runner_routes_shadow_selected_index", runner_surface["routes_shadow_selected_index"], True),
            PLAN_MODULE._expect("runner_records_harness_payload", runner_surface["records_harness_payload"], True),
        ]
    )
    for action in BLOCKED_ACTIONS:
        checks.append(PLAN_MODULE._expect(f"source_static_review_{action}", review_decision.get(action), False))
        checks.append(PLAN_MODULE._expect(f"source_preflight_plan_{action}", plan_decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        checks.append(PLAN_MODULE._expect(f"source_static_review_{flag}", bool(review_decision.get(flag, False)), False))
        checks.append(PLAN_MODULE._expect(f"source_preflight_plan_{flag}", bool(plan_decision.get(flag, False)), False))
    return checks


def _static_artifact_hash_checks(
    files: dict[str, Path],
    root: dict[str, str],
    nested: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._expect("source_static_review_root_heads_sha", PLAN_MODULE._sha_for_suffix(root, "HEADS"), PLAN_MODULE._sha256(files["heads"])),
        PLAN_MODULE._expect("source_static_review_root_command_sha", PLAN_MODULE._sha_for_suffix(root, "COMMAND"), PLAN_MODULE._sha256(files["command"])),
        PLAN_MODULE._expect("source_static_review_root_stdout_sha", PLAN_MODULE._sha_for_suffix(root, "stdout"), PLAN_MODULE._sha256(files["stdout"])),
        PLAN_MODULE._expect("source_static_review_root_stderr_sha", PLAN_MODULE._sha_for_suffix(root, "stderr"), PLAN_MODULE._sha256(files["stderr"])),
        PLAN_MODULE._expect("source_static_review_root_run_exit_sha", PLAN_MODULE._sha_for_suffix(root, "run.exit"), PLAN_MODULE._sha256(files["run_exit"])),
        PLAN_MODULE._expect("source_static_review_root_json_sha", PLAN_MODULE._sha_for_suffix(root, f"review/{SOURCE_REVIEW_JSON_NAME}"), PLAN_MODULE._sha256(files["review_json"])),
        PLAN_MODULE._expect("source_static_review_root_md_sha", PLAN_MODULE._sha_for_suffix(root, f"review/{SOURCE_REVIEW_MD_NAME}"), PLAN_MODULE._sha256(files["review_md"])),
        PLAN_MODULE._expect("source_static_review_root_sha256s_sha", PLAN_MODULE._sha_for_suffix(root, "review/SHA256SUMS"), PLAN_MODULE._sha256(files["review_sha256s"])),
        PLAN_MODULE._expect("source_static_review_nested_json_sha", PLAN_MODULE._sha_for_suffix(nested, SOURCE_REVIEW_JSON_NAME), PLAN_MODULE._sha256(files["review_json"])),
        PLAN_MODULE._expect("source_static_review_nested_md_sha", PLAN_MODULE._sha_for_suffix(nested, SOURCE_REVIEW_MD_NAME), PLAN_MODULE._sha256(files["review_md"])),
    ]


def _plan_artifact_hash_checks(
    files: dict[str, Path],
    root: dict[str, str],
    nested: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        PLAN_MODULE._expect("source_preflight_plan_root_heads_sha", PLAN_MODULE._sha_for_suffix(root, "HEADS"), PLAN_MODULE._sha256(files["heads"])),
        PLAN_MODULE._expect("source_preflight_plan_root_command_sha", PLAN_MODULE._sha_for_suffix(root, "COMMAND"), PLAN_MODULE._sha256(files["command"])),
        PLAN_MODULE._expect("source_preflight_plan_root_stdout_sha", PLAN_MODULE._sha_for_suffix(root, "stdout"), PLAN_MODULE._sha256(files["stdout"])),
        PLAN_MODULE._expect("source_preflight_plan_root_stderr_sha", PLAN_MODULE._sha_for_suffix(root, "stderr"), PLAN_MODULE._sha256(files["stderr"])),
        PLAN_MODULE._expect("source_preflight_plan_root_run_exit_sha", PLAN_MODULE._sha_for_suffix(root, "run.exit"), PLAN_MODULE._sha256(files["run_exit"])),
        PLAN_MODULE._expect("source_preflight_plan_root_json_sha", PLAN_MODULE._sha_for_suffix(root, f"plan/{SOURCE_PLAN_JSON_NAME}"), PLAN_MODULE._sha256(files["plan_json"])),
        PLAN_MODULE._expect("source_preflight_plan_root_md_sha", PLAN_MODULE._sha_for_suffix(root, f"plan/{SOURCE_PLAN_MD_NAME}"), PLAN_MODULE._sha256(files["plan_md"])),
        PLAN_MODULE._expect("source_preflight_plan_root_sha256s_sha", PLAN_MODULE._sha_for_suffix(root, "plan/SHA256SUMS"), PLAN_MODULE._sha256(files["plan_sha256s"])),
        PLAN_MODULE._expect("source_preflight_plan_nested_json_sha", PLAN_MODULE._sha_for_suffix(nested, SOURCE_PLAN_JSON_NAME), PLAN_MODULE._sha256(files["plan_json"])),
        PLAN_MODULE._expect("source_preflight_plan_nested_md_sha", PLAN_MODULE._sha_for_suffix(nested, SOURCE_PLAN_MD_NAME), PLAN_MODULE._sha256(files["plan_md"])),
    ]


def _source_summary(source_review: dict[str, Any], source_plan: dict[str, Any]) -> dict[str, Any]:
    review_decision = PLAN_MODULE._dict(source_review.get("final_decision"))
    plan_decision = PLAN_MODULE._dict(source_plan.get("final_decision"))
    return {
        "objective_required_records": int(review_decision.get("objective_required_records") or plan_decision.get("objective_required_records") or 0),
        "candidate_closed_loop_outcome_records": int(review_decision.get("candidate_closed_loop_outcome_records") or plan_decision.get("candidate_closed_loop_outcome_records") or 0),
        "missing_candidate_closed_loop_outcome_records": int(review_decision.get("missing_candidate_closed_loop_outcome_records") or plan_decision.get("missing_candidate_closed_loop_outcome_records") or 0),
    }


def _future_execution_contract() -> dict[str, Any]:
    return {
        "required_records": OBJECTIVE_REQUIRED_RECORDS,
        "candidate_selection_source": "shadow_selected_index from audited default-off CAMP selector",
        "allowed_candidate_source": "existing fixed DP candidate tensor only",
        "top1_reference_index": 0,
        "requires_candidate_tensor_provenance_logging": True,
        "requires_closed_loop_outcome_collection": True,
        "closed_loop_outcome_usage": "offline_evaluation_evidence_only",
        "future_gate_authorized_by_this_gate": "static_review_only",
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
    elif "preflight_enabled" in failed:
        failure_class = "explicit_candidate_index_replay_outcome_acquisition_preflight_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any("sha" in name for name in failed):
        failure_class = "source_artifact_hash_mismatch"
    else:
        failure_class = "candidate_index_replay_outcome_acquisition_preflight_contract_failure"
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_candidate_index_replay_outcome_acquisition_preflight_ready": bool(passed),
        "objective_3200_candidate_index_replay_outcome_acquisition_preflight_static_review_authorized": bool(passed),
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
    json_path = output_dir / PREFLIGHT_JSON_NAME
    md_path = output_dir / PREFLIGHT_MD_NAME
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
    summary = report["source_summary"]
    return "\n".join(
        [
            "# Objective-3200 Candidate-Index Replay Outcome-Acquisition Preflight",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
            "## Objective",
            "",
            f"- Required records: `{summary['objective_required_records']}`",
            f"- Candidate outcome records: `{summary['candidate_closed_loop_outcome_records']}`",
            f"- Missing candidate outcomes: `{summary['missing_candidate_closed_loop_outcome_records']}`",
            "",
            "This gate authorizes static review only; it does not run replay or acquire outcomes.",
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
