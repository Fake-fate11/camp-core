#!/usr/bin/env python3
"""Preflight objective-3200 shadow-selected outcome acquisition.

This gate consumes the audited acquisition-plan static review plus its source
plan artifact. It locks the fixed-DP, fixed-candidate, strict-pairing, and
artifact contracts for a future acquisition execution gate. It does not execute
outcome acquisition, replay, training, candidate generation, promotion,
deployment, online selector activation, Diffusion Planner modification, or any
safety/CAMP-over-DP claim.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_source_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_outcome_acquisition_"
        "plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_objective_3200_acquisition_plan_static_review",
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
SOURCE_PLAN_SCHEMA = SOURCE_REVIEW_MODULE.SOURCE_PLAN_SCHEMA
SOURCE_PLAN_STATUS = SOURCE_REVIEW_MODULE.SOURCE_PLAN_STATUS
SOURCE_REVIEW_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
SOURCE_PLAN_JSON_NAME = SOURCE_REVIEW_MODULE.SOURCE_PLAN_JSON_NAME
SOURCE_PLAN_MD_NAME = SOURCE_REVIEW_MODULE.SOURCE_PLAN_MD_NAME
BLOCKED_ACTIONS = SOURCE_REVIEW_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = SOURCE_REVIEW_MODULE.FALSE_EXECUTION_FLAGS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_outcome_acquisition_preflight_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_preflight_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_preflight_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_preflight_static_review_only"
)

PREFLIGHT_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_preflight.json"
)
PREFLIGHT_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_preflight.md"
)

OBJECTIVE_REQUIRED_RECORDS = PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS
EXISTING_RUN_LEVEL_PAIR_TARGET = PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET
EXPECTED_PLAN_STEPS = SOURCE_REVIEW_MODULE.EXPECTED_PLAN_STEPS
EXPECTED_NO_GO = SOURCE_REVIEW_MODULE.EXPECTED_NO_GO

EXPECTED_PREFLIGHT_ITEMS = (
    "lock_source_static_review_and_plan_artifacts",
    "lock_3200_runtime_record_identity_contract",
    "predeclare_fixed_dp_candidate_tensor_identity_requirements",
    "predeclare_shadow_selected_candidate_binding_requirements",
    "predeclare_closed_loop_outcome_acquisition_request_schema",
    "emit_static_review_ready_acquisition_preflight_artifact",
)
EXPECTED_PLANNED_OUTPUTS = (
    "fixed_dp_candidate_row_manifest",
    "shadow_selected_candidate_binding_manifest",
    "candidate_tensor_identity_verification_table",
    "shadow_selected_closed_loop_outcome_summary_manifest",
    "strict_top1_shadow_pairing_join_manifest",
    "no_go_and_failure_attribution_report",
)
PREFLIGHT_NO_GO = (
    "source_static_review_missing_or_failed",
    "source_plan_missing_or_failed",
    "dp_head_drift",
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
    parser.add_argument("--source_acquisition_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_acquisition_plan_json", type=Path, required=True)
    parser.add_argument("--source_acquisition_plan_md", type=Path, required=True)
    parser.add_argument("--source_acquisition_plan_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_record_count", type=int, default=OBJECTIVE_REQUIRED_RECORDS)
    parser.add_argument("--expected_existing_delta_count", type=int, default=EXISTING_RUN_LEVEL_PAIR_TARGET)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_preflight",
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
        source_acquisition_plan_artifact_dir=args.source_acquisition_plan_artifact_dir,
        source_acquisition_plan_json=args.source_acquisition_plan_json,
        source_acquisition_plan_md=args.source_acquisition_plan_md,
        source_acquisition_plan_sha256s=args.source_acquisition_plan_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_record_count=args.expected_record_count,
        expected_existing_delta_count=args.expected_existing_delta_count,
        enabled=args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_preflight,
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
    source_acquisition_plan_artifact_dir: Path,
    source_acquisition_plan_json: Path,
    source_acquisition_plan_md: Path,
    source_acquisition_plan_sha256s: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_record_count: int = OBJECTIVE_REQUIRED_RECORDS,
    expected_existing_delta_count: int = EXISTING_RUN_LEVEL_PAIR_TARGET,
    enabled: bool = False,
) -> dict[str, Any]:
    static_artifact_dir = source_static_review_artifact_dir.resolve()
    plan_artifact_dir = source_acquisition_plan_artifact_dir.resolve()
    paths = {
        "source_static_review_json": source_static_review_json.resolve(),
        "source_static_review_md": source_static_review_md.resolve(),
        "source_static_review_sha256s": source_static_review_sha256s.resolve(),
        "source_acquisition_plan_json": source_acquisition_plan_json.resolve(),
        "source_acquisition_plan_md": source_acquisition_plan_md.resolve(),
        "source_acquisition_plan_sha256s": source_acquisition_plan_sha256s.resolve(),
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

    source_review = _read_json_dict(paths["source_static_review_json"])
    source_plan = _read_json_dict(paths["source_acquisition_plan_json"])
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])
    static_heads = _parse_key_values(_read_text(static_files["heads"]))
    plan_heads = _parse_key_values(_read_text(plan_files["heads"]))
    static_root_sha256s = _read_sha256sums(static_files["root_sha256s"])
    static_nested_sha256s = _read_sha256sums(paths["source_static_review_sha256s"])
    plan_root_sha256s = _read_sha256sums(plan_files["root_sha256s"])
    plan_nested_sha256s = _read_sha256sums(paths["source_acquisition_plan_sha256s"])
    static_run_exit = _read_text(static_files["run_exit"]).strip()
    plan_run_exit = _read_text(plan_files["run_exit"]).strip()

    checks = _checks(
        enabled=enabled,
        static_artifact_dir=static_artifact_dir,
        plan_artifact_dir=plan_artifact_dir,
        paths=paths,
        static_files=static_files,
        plan_files=plan_files,
        source_review=source_review,
        source_plan=source_plan,
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
        expected_existing_delta_count=expected_existing_delta_count,
    )
    passed = all(check["passed"] for check in checks)
    objective = _objective_summary(source_review=source_review, source_plan=source_plan)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "read_only": True,
            "objective_3200_outcome_acquisition_preflight_only": True,
            "outcome_acquisition_execution": False,
            "outcome_acquisition_executed": False,
            "closed_loop_replay_execution": False,
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
            "source_acquisition_plan_artifact_dir": str(plan_artifact_dir),
            **{name: str(path) for name, path in paths.items()},
            "output_dir": str(output_dir.resolve()),
        },
        "source_artifact_hashes": {
            "source_static_review_root_sha256s": _sha256(static_files["root_sha256s"]),
            "source_static_review_review_sha256s": _sha256(paths["source_static_review_sha256s"]),
            "source_acquisition_plan_root_sha256s": _sha256(plan_files["root_sha256s"]),
            "source_acquisition_plan_plan_sha256s": _sha256(paths["source_acquisition_plan_sha256s"]),
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_static_review_camp_head": _kv(static_heads, "CAMP_HEAD", "camp_head"),
            "source_static_review_camp_origin_main": _kv(static_heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main"),
            "source_static_review_dp_head": _kv(static_heads, "DP_HEAD", "dp_head"),
            "source_acquisition_plan_camp_head": _kv(plan_heads, "CAMP_HEAD", "camp_head"),
            "source_acquisition_plan_camp_origin_main": _kv(plan_heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main"),
            "source_acquisition_plan_dp_head": _kv(plan_heads, "DP_HEAD", "dp_head"),
        },
        "source_static_review_summary": _source_review_summary(source_review),
        "source_acquisition_plan_summary": _source_plan_summary(source_plan),
        "objective_3200_summary": objective,
        "preflight_items": _preflight_items(),
        "future_acquisition_execution_contract": _future_execution_contract(objective),
        "planned_outputs": list(EXPECTED_PLANNED_OUTPUTS),
        "no_go_register": list(PREFLIGHT_NO_GO),
        "preflight_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, objective=objective),
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
    expected_existing_delta_count: int,
) -> list[dict[str, Any]]:
    review_decision = _dict(source_review.get("final_decision"))
    plan_decision = _dict(source_plan.get("final_decision"))
    review_analysis = _dict(source_review.get("analysis"))
    plan_analysis = _dict(source_plan.get("analysis"))
    review_objective = _source_review_objective(source_review)
    plan_gap = _dict(source_plan.get("objective_gap_summary"))
    plan_steps = [item.get("step") for item in _list_of_dicts(source_plan.get("acquisition_plan"))]

    checks: list[dict[str, Any]] = [
        _expect("acquisition_preflight_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("status_doc_latest_status", _latest_value(status_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        _expect("status_doc_latest_next_work", _latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _check("source_static_review_artifact_dir_exists", static_artifact_dir.is_dir(), str(static_artifact_dir), "directory"),
        _check("source_acquisition_plan_artifact_dir_exists", plan_artifact_dir.is_dir(), str(plan_artifact_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, require_file=True))
    for name, path in static_files.items():
        checks.extend(_path_checks(f"source_static_review_artifact_{name}", path, require_file=True, allow_empty=name == "stderr"))
    for name, path in plan_files.items():
        checks.extend(_path_checks(f"source_acquisition_plan_artifact_{name}", path, require_file=True, allow_empty=name == "stderr"))

    checks.extend(
        [
            _expect("source_static_review_run_exit", static_run_exit, "0"),
            _expect("source_acquisition_plan_run_exit", plan_run_exit, "0"),
            _expect("source_static_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA),
            _expect("source_static_review_passed", review_decision.get("passed"), True),
            _expect("source_static_review_status", review_decision.get("status"), SOURCE_REVIEW_STATUS),
            _expect("source_static_review_authorized_next", review_decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
            _expect("source_static_review_read_only", review_analysis.get("read_only"), True),
            _expect("source_static_review_static_review_only", review_analysis.get("static_review_only"), True),
            _expect("source_static_review_outcome_acquisition_executed", review_analysis.get("outcome_acquisition_executed"), False),
            _expect("source_static_review_replay_execution", review_analysis.get("closed_loop_replay_execution"), False),
            _expect("source_static_review_dp_modification", review_analysis.get("dp_modification"), False),
            _expect("source_static_review_score_expression", review_analysis.get("score_expression"), SCORE_EXPRESSION),
            _expect("source_acquisition_plan_schema", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA),
            _expect("source_acquisition_plan_passed", plan_decision.get("passed"), True),
            _expect("source_acquisition_plan_status", plan_decision.get("status"), SOURCE_PLAN_STATUS),
            _expect("source_acquisition_plan_authorized_next", plan_decision.get("authorized_next_work"), SOURCE_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK),
            _expect("source_acquisition_plan_read_only", plan_analysis.get("read_only"), True),
            _expect("source_acquisition_plan_plan_only", plan_analysis.get("plan_only"), True),
            _expect("source_acquisition_plan_outcome_acquisition_executed", plan_analysis.get("outcome_acquisition_executed"), False),
            _expect("source_acquisition_plan_replay_execution", plan_analysis.get("closed_loop_replay_execution"), False),
            _expect("source_acquisition_plan_score_expression", plan_analysis.get("score_expression"), SCORE_EXPRESSION),
            _expect("source_static_review_dp_head_fixed", _kv(static_heads, "DP_HEAD", "dp_head"), required_dp_head),
            _expect("source_acquisition_plan_dp_head_fixed", _kv(plan_heads, "DP_HEAD", "dp_head"), required_dp_head),
            _expect("source_static_review_camp_head_matches_origin", _kv(static_heads, "CAMP_HEAD", "camp_head"), _kv(static_heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main")),
            _expect("source_acquisition_plan_camp_head_matches_origin", _kv(plan_heads, "CAMP_HEAD", "camp_head"), _kv(plan_heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main")),
            _expect("objective_required_records", review_objective["objective_required_records"], expected_record_count),
            _expect("runtime_record_count", review_objective["runtime_record_count"], expected_record_count),
            _expect("candidate_closed_loop_outcome_records", review_objective["candidate_closed_loop_outcome_records"], 0),
            _expect("missing_candidate_closed_loop_outcome_records", review_objective["missing_candidate_closed_loop_outcome_records"], expected_record_count),
            _expect("source_plan_objective_required_records", int(plan_gap.get("objective_required_records") or 0), expected_record_count),
            _expect("source_plan_existing_delta_count", int(plan_gap.get("existing_delta_count") or 0), expected_existing_delta_count),
            _expect("source_plan_candidate_closed_loop_outcome_records", int(plan_gap.get("candidate_closed_loop_outcome_records") or 0), 0),
            _expect("source_plan_missing_candidate_closed_loop_outcome_records", int(plan_gap.get("missing_candidate_closed_loop_outcome_records") or 0), expected_record_count),
            _expect("source_plan_existing_artifacts_satisfy_objective", plan_gap.get("existing_artifacts_satisfy_objective"), False),
            _expect("source_plan_requires_acquisition_plan", plan_gap.get("requires_acquisition_plan"), True),
            _expect("source_plan_steps", plan_steps, list(EXPECTED_PLAN_STEPS)),
            _expect("source_plan_no_go_register", source_plan.get("no_go_register"), list(EXPECTED_NO_GO)),
        ]
    )
    checks.extend(
        _sha_checks(
            label="source_static_review",
            root_sha256s=static_root_sha256s,
            nested_sha256s=static_nested_sha256s,
            json_path=paths["source_static_review_json"],
            md_path=paths["source_static_review_md"],
            sha256s_path=paths["source_static_review_sha256s"],
            root_json_suffix=f"review/{SOURCE_REVIEW_JSON_NAME}",
            root_md_suffix=f"review/{SOURCE_REVIEW_MD_NAME}",
            root_sha_suffix="review/SHA256SUMS",
        )
    )
    checks.extend(
        _sha_checks(
            label="source_acquisition_plan",
            root_sha256s=plan_root_sha256s,
            nested_sha256s=plan_nested_sha256s,
            json_path=paths["source_acquisition_plan_json"],
            md_path=paths["source_acquisition_plan_md"],
            sha256s_path=paths["source_acquisition_plan_sha256s"],
            root_json_suffix=f"plan/{SOURCE_PLAN_JSON_NAME}",
            root_md_suffix=f"plan/{SOURCE_PLAN_MD_NAME}",
            root_sha_suffix="plan/SHA256SUMS",
        )
    )
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_static_review_{action}", review_decision.get(action), False))
        checks.append(_expect(f"source_acquisition_plan_{action}", plan_decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        checks.append(_expect(f"source_static_review_{flag}", review_decision.get(flag), False))
        checks.append(_expect(f"source_acquisition_plan_{flag}", plan_decision.get(flag), False))
    return checks


def _sha_checks(
    *,
    label: str,
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    json_path: Path,
    md_path: Path,
    sha256s_path: Path,
    root_json_suffix: str,
    root_md_suffix: str,
    root_sha_suffix: str,
) -> list[dict[str, Any]]:
    json_sha = _sha256(json_path)
    md_sha = _sha256(md_path)
    sha_sha = _sha256(sha256s_path)
    return [
        _expect(f"{label}_root_json_sha", _sha_for_suffix(root_sha256s, root_json_suffix), json_sha),
        _expect(f"{label}_root_md_sha", _sha_for_suffix(root_sha256s, root_md_suffix), md_sha),
        _expect(f"{label}_root_nested_sha256s_sha", _sha_for_suffix(root_sha256s, root_sha_suffix), sha_sha),
        _expect(f"{label}_nested_json_sha", _sha_for_suffix(nested_sha256s, json_path.name), json_sha),
        _expect(f"{label}_nested_md_sha", _sha_for_suffix(nested_sha256s, md_path.name), md_sha),
    ]


def _source_review_objective(source_review: dict[str, Any]) -> dict[str, int]:
    decision = _dict(source_review.get("final_decision"))
    source_plan_summary = _dict(source_review.get("source_plan_summary"))
    return {
        "objective_required_records": int(decision.get("objective_required_records") or source_plan_summary.get("objective_required_records") or 0),
        "runtime_record_count": int(decision.get("runtime_record_count") or source_plan_summary.get("runtime_record_count") or 0),
        "candidate_closed_loop_outcome_records": int(decision.get("candidate_closed_loop_outcome_records") or source_plan_summary.get("candidate_closed_loop_outcome_records") or 0),
        "missing_candidate_closed_loop_outcome_records": int(decision.get("missing_candidate_closed_loop_outcome_records") or source_plan_summary.get("missing_candidate_closed_loop_outcome_records") or 0),
    }


def _objective_summary(*, source_review: dict[str, Any], source_plan: dict[str, Any]) -> dict[str, Any]:
    review_objective = _source_review_objective(source_review)
    plan_gap = _dict(source_plan.get("objective_gap_summary"))
    return {
        "objective_required_records": review_objective["objective_required_records"],
        "runtime_record_count": review_objective["runtime_record_count"],
        "existing_delta_count": int(plan_gap.get("existing_delta_count") or 0),
        "candidate_closed_loop_outcome_records": review_objective["candidate_closed_loop_outcome_records"],
        "missing_candidate_closed_loop_outcome_records": review_objective["missing_candidate_closed_loop_outcome_records"],
        "existing_artifacts_satisfy_objective": plan_gap.get("existing_artifacts_satisfy_objective"),
        "requires_acquisition_execution": True,
    }


def _preflight_items() -> list[dict[str, Any]]:
    return [
        {"item": "lock_source_static_review_and_plan_artifacts", "purpose": "Pin source artifact roots, nested SHA256SUMS, HEADS, COMMAND, stdout, stderr, and run.exit."},
        {"item": "lock_3200_runtime_record_identity_contract", "purpose": "Require 3200 scenario/seed/sample/traffic-light/run-key records before execution."},
        {"item": "predeclare_fixed_dp_candidate_tensor_identity_requirements", "purpose": "Require every shadow-selected row to resolve to an unmodified fixed-DP candidate tensor."},
        {"item": "predeclare_shadow_selected_candidate_binding_requirements", "purpose": "Use only shadow_selected_index over the fixed DP candidate tensor."},
        {"item": "predeclare_closed_loop_outcome_acquisition_request_schema", "purpose": "Record the future outcome summary schema and failure attribution fields."},
        {"item": "emit_static_review_ready_acquisition_preflight_artifact", "purpose": "Authorize static review before any acquisition execution."},
    ]


def _future_execution_contract(objective: dict[str, Any]) -> dict[str, Any]:
    return {
        "future_execution_authorized_by_this_gate": False,
        "future_execution_requires_static_review": True,
        "candidate_source": "fixed_dp_candidate_tensor_only",
        "camp_action": "read_shadow_selected_index_and_select_existing_candidate_only",
        "required_candidate_outcome_records": objective["objective_required_records"],
        "currently_available_candidate_outcome_records": objective["candidate_closed_loop_outcome_records"],
        "missing_candidate_outcome_records": objective["missing_candidate_closed_loop_outcome_records"],
        "forbidden": [
            "dp_code_config_weight_checkpoint_modification",
            "camp_trajectory_generation_repair_rewrite_or_blend",
            "reference_blend_guidance_postprocess_postselection",
            "full36_or_formal_seed_11_12_13",
            "closed_loop_outcome_training_or_online_input",
            "promotion_deployment_online_selector_or_claim",
        ],
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], objective: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "acquisition_preflight_enabled" in failed:
        failure_class = "explicit_objective_3200_outcome_acquisition_preflight_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_static_review") for name in failed):
        failure_class = "source_static_review_contract_failure"
    elif any(name.startswith("source_acquisition_plan") or name.startswith("source_plan") for name in failed):
        failure_class = "source_acquisition_plan_contract_failure"
    else:
        failure_class = "objective_3200_outcome_acquisition_preflight_contract_failure"
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_outcome_acquisition_preflight_ready": bool(passed),
        "objective_3200_outcome_acquisition_preflight_static_review_authorized": bool(passed),
        "objective_required_records": objective["objective_required_records"],
        "runtime_record_count": objective["runtime_record_count"],
        "candidate_closed_loop_outcome_records": objective["candidate_closed_loop_outcome_records"],
        "missing_candidate_closed_loop_outcome_records": objective["missing_candidate_closed_loop_outcome_records"],
        "existing_artifacts_satisfy_objective": objective["existing_artifacts_satisfy_objective"],
        "requires_acquisition_execution": bool(passed),
        "direct_replay_execution_authorized": False,
        "direct_acquisition_execution_authorized": False,
        "recommendation": "static_review_objective_3200_outcome_acquisition_preflight_only" if passed else "repair_or_rerun_same_preflight_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def _source_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_review.get("final_decision"))
    objective = _source_review_objective(source_review)
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        **objective,
    }


def _source_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_plan.get("final_decision"))
    gap = _dict(source_plan.get("objective_gap_summary"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "plan_step_count": len(_list_of_dicts(source_plan.get("acquisition_plan"))),
        "no_go_count": len(source_plan.get("no_go_register") or []),
        "objective_required_records": gap.get("objective_required_records"),
        "candidate_closed_loop_outcome_records": gap.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": gap.get("missing_candidate_closed_loop_outcome_records"),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PREFLIGHT_JSON_NAME
    md_path = output_dir / PREFLIGHT_MD_NAME
    json_path.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    sums = [f"{_sha256(path)}  {path.name}" for path in (json_path, md_path)]
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    objective = report["objective_3200_summary"]
    return "\n".join(
        [
            "# Objective-3200 Outcome Acquisition Preflight",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
            "## Objective",
            "",
            f"- Objective required records: `{objective['objective_required_records']}`",
            f"- Runtime records: `{objective['runtime_record_count']}`",
            f"- Existing deltas: `{objective['existing_delta_count']}`",
            f"- Per-record shadow-selected outcomes: `{objective['candidate_closed_loop_outcome_records']}`",
            f"- Missing per-record shadow-selected outcomes: `{objective['missing_candidate_closed_loop_outcome_records']}`",
            f"- Requires acquisition execution: `{objective['requires_acquisition_execution']}`",
            "",
            "## Boundary",
            "",
            "- Preflight only: no outcome acquisition, replay execution, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
            f"- Score expression: `{report['analysis']['score_expression']}`",
        ]
    ) + "\n"


def _path_checks(
    name: str,
    path: Path,
    *,
    require_file: bool,
    allow_empty: bool = False,
) -> list[dict[str, Any]]:
    exists = path.is_file() if require_file else path.exists()
    checks = [_check(f"{name}_exists", exists, str(path), "file" if require_file else "path")]
    if exists and require_file and not allow_empty:
        checks.append(_check(f"{name}_nonempty", path.stat().st_size > 0, path.stat().st_size, ">0 bytes"))
    return checks


def _read_json_dict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_sha256sums(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            entries[parts[1].lstrip("*")] = parts[0]
    return entries


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip()] = value.strip()
    return values


def _sha_for_suffix(entries: dict[str, str], suffix: str) -> str | None:
    normalized_suffix = suffix.replace("\\", "/")
    for key, value in entries.items():
        if key.replace("\\", "/").endswith(normalized_suffix):
            return value
    return None


def _latest_value(text: str, key: str) -> str | None:
    token = f"{key}="
    if token not in text:
        return None
    return text.rsplit(token, maxsplit=1)[1].splitlines()[0]


def _kv(values: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        if key in values:
            return values[key]
    return None


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": actual == expected, "actual": actual, "expected": expected}


def _check(name: str, passed: bool, actual: Any | None = None, expected: Any = True) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual if actual is not None else bool(passed), "expected": expected}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value.lower())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
