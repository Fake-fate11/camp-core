#!/usr/bin/env python3
"""Materialize actual SafetyCost evidence from audited shadow run summaries.

This gate is evidence-only. It never runs replay, generates candidates, edits
Diffusion Planner, promotes a selector, deploys, enables online selection, or
authorizes a SafetyCost/CAMP-over-DP claim.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import random
from pathlib import Path
from typing import Any


def _load_source_static_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_actual_safetycost_outcome_materialization_"
        "preflight_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization_preflight_static_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_STATIC_REVIEW_MODULE = _load_source_static_review_module()
HELPER_MODULE = SOURCE_STATIC_REVIEW_MODULE.HELPER_MODULE

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
    "actual_safetycost_outcome_materialization_execution_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_STATIC_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_execution_result_review_only"
)
FAILED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_execution_failed_user_decision_required"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_execution_passed"
)
SHADOW_SELECTED_EXECUTION_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_shadow_selected_"
    "closed_loop_outcome_evaluation_execution_passed"
)
AUTHORIZED_EOF_STATUSES = {SOURCE_STATIC_REVIEW_STATUS, SHADOW_SELECTED_EXECUTION_STATUS}
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_execution_rejected"
)

EXECUTION_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_execution.json"
)
EXECUTION_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_outcome_materialization_execution.md"
)

FORMAL_SEEDS = {11, 12, 13}
FULL36_MARKERS = ("full36", "full_36", "formal36")
BOOTSTRAP_RESAMPLES = 10_000
SAFETY_COST_WEIGHTS = {
    "collision_rate": 100.0,
    "near_miss_rate": 10.0,
    "lane_violation_rate": 20.0,
    "red_light_violation_rate": 30.0,
    "planned_red_light_violation_rate": 15.0,
    "mean_jerk_magnitude_mps3": 1.0,
    "mean_lateral_acceleration_mps2": 2.0,
    "route_shortfall": 2.0,
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_preflight_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_json", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_md", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--paired_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--paired_execution_json", type=Path, required=True)
    parser.add_argument("--paired_execution_sha256s", type=Path, required=True)
    parser.add_argument("--runtime_execution_dir", type=Path, required=True)
    parser.add_argument("--shadow_selected_summary_root", type=Path, default=None)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_record_count", type=int, default=3200)
    parser.add_argument("--expected_selection_log_count", type=int, default=32)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization_execution",
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
        paired_execution_artifact_dir=args.paired_execution_artifact_dir,
        paired_execution_json=args.paired_execution_json,
        paired_execution_sha256s=args.paired_execution_sha256s,
        runtime_execution_dir=args.runtime_execution_dir,
        shadow_selected_summary_root=args.shadow_selected_summary_root,
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
            args.enable_v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_outcome_materialization_execution
        ),
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
    paired_execution_artifact_dir: Path,
    paired_execution_json: Path,
    paired_execution_sha256s: Path,
    runtime_execution_dir: Path,
    shadow_selected_summary_root: Path | None,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_record_count: int = 3200,
    expected_selection_log_count: int = 32,
    enabled: bool = False,
) -> dict[str, Any]:
    source_preflight_static_review_artifact_dir = source_preflight_static_review_artifact_dir.resolve()
    source_preflight_static_review_json = source_preflight_static_review_json.resolve()
    source_preflight_static_review_md = source_preflight_static_review_md.resolve()
    source_preflight_static_review_sha256s = source_preflight_static_review_sha256s.resolve()
    paired_execution_artifact_dir = paired_execution_artifact_dir.resolve()
    paired_execution_json = paired_execution_json.resolve()
    paired_execution_sha256s = paired_execution_sha256s.resolve()
    runtime_execution_dir = runtime_execution_dir.resolve()
    shadow_root = shadow_selected_summary_root.resolve() if shadow_selected_summary_root else None

    source_review = _read_json_dict(source_preflight_static_review_json)
    paired_execution = _read_json_dict(paired_execution_json)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    source_heads = _parse_key_values(_read_text(source_preflight_static_review_artifact_dir / "HEADS"))
    source_run_exit = _read_text(source_preflight_static_review_artifact_dir / "run.exit").strip()
    paired_heads = _parse_key_values(_read_text(paired_execution_artifact_dir / "HEADS"))
    paired_run_exit = _read_text(paired_execution_artifact_dir / "run.exit").strip()

    source = _source_summary(
        source_preflight_static_review_artifact_dir=source_preflight_static_review_artifact_dir,
        source_preflight_static_review_json=source_preflight_static_review_json,
        source_preflight_static_review_md=source_preflight_static_review_md,
        source_preflight_static_review_sha256s=source_preflight_static_review_sha256s,
        paired_execution_artifact_dir=paired_execution_artifact_dir,
        paired_execution_json=paired_execution_json,
        paired_execution_sha256s=paired_execution_sha256s,
    )
    runtime = _runtime_summary(runtime_execution_dir)
    materialization = _materialization_summary(runtime_execution_dir, shadow_root)
    checks = _checks(
        enabled=enabled,
        source_review=source_review,
        paired_execution=paired_execution,
        source_heads=source_heads,
        source_run_exit=source_run_exit,
        paired_heads=paired_heads,
        paired_run_exit=paired_run_exit,
        v14_text=v14_text,
        status_text=status_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_record_count=expected_record_count,
        expected_selection_log_count=expected_selection_log_count,
        runtime=runtime,
        materialization=materialization,
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "actual_safetycost_outcome_materialization_execution": True,
            "read_only_existing_runtime_artifact": True,
            "replay_execution": False,
            "training_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "candidate_tensor_modification": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "online_selector_change": False,
            "safety_or_camp_over_dp_claim": False,
            "closed_loop_outcomes_training_or_online_input": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "source_preflight_static_review_artifact_dir": str(source_preflight_static_review_artifact_dir),
            "source_preflight_static_review_json": str(source_preflight_static_review_json),
            "paired_execution_artifact_dir": str(paired_execution_artifact_dir),
            "paired_execution_json": str(paired_execution_json),
            "runtime_execution_dir": str(runtime_execution_dir),
            "shadow_selected_summary_root": str(shadow_root) if shadow_root else None,
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir.resolve()),
        },
        "source_artifacts": source,
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_artifact_dp_head": source_heads.get("DP_HEAD"),
            "paired_execution_dp_head": paired_heads.get("DP_HEAD"),
        },
        "runtime_source_summary": runtime,
        "materialization_summary": materialization,
        "execution_checks": checks,
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "final_decision": _decision(passed=passed, checks=checks, materialization=materialization),
    }


def _checks(
    *,
    enabled: bool,
    source_review: dict[str, Any],
    paired_execution: dict[str, Any],
    source_heads: dict[str, str],
    source_run_exit: str,
    paired_heads: dict[str, str],
    paired_run_exit: str,
    v14_text: str,
    status_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_record_count: int,
    expected_selection_log_count: int,
    runtime: dict[str, Any],
    materialization: dict[str, Any],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    source_decision = _dict(source_review.get("final_decision"))
    paired_decision = _dict(paired_execution.get("final_decision"))
    paired_records = _dict(paired_execution.get("paired_record_summary"))
    paired_tensor = _dict(paired_execution.get("candidate_tensor_identity_table"))

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

    require("execution_enabled", enabled)
    expect("current_dp_head_fixed", current_dp_head, required_dp_head)
    expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD)
    expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main)
    expect("source_artifact_dp_head_fixed", source_heads.get("DP_HEAD"), required_dp_head)
    expect("paired_execution_artifact_dp_head_fixed", paired_heads.get("DP_HEAD"), required_dp_head)
    expect("source_static_review_run_exit", source_run_exit, "0")
    expect("paired_execution_run_exit", paired_run_exit, "0")
    audit_latest_status = HELPER_MODULE._latest_value(v14_text, "current_v14_status")
    status_doc_latest_status = HELPER_MODULE._latest_value(status_text, "current_v14_status")
    require(
        "audit_latest_status_authorizes_materialization",
        audit_latest_status in AUTHORIZED_EOF_STATUSES,
        audit_latest_status,
        "source static review passed or shadow-selected execution passed",
    )
    expect("audit_latest_next_work", HELPER_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK)
    require(
        "status_doc_latest_status_authorizes_materialization",
        status_doc_latest_status in AUTHORIZED_EOF_STATUSES,
        status_doc_latest_status,
        "source static review passed or shadow-selected execution passed",
    )
    expect("status_doc_latest_next_work", HELPER_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK)

    expect("source_static_review_schema", source_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA)
    expect("source_static_review_passed", source_decision.get("passed"), True)
    expect("source_static_review_status", source_decision.get("status"), SOURCE_STATIC_REVIEW_STATUS)
    expect("source_static_review_authorized_next", source_decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK)
    expect("source_static_review_authorizes_execution", source_decision.get("actual_safetycost_outcome_materialization_execution_authorized"), True)
    expect("source_static_review_no_execution", source_decision.get("actual_safetycost_outcome_materialization_executed_by_this_gate"), False)
    for action in BLOCKED_ACTIONS:
        expect(f"source_static_review_decision_{action}", source_decision.get(action), False)
    for flag in FALSE_EXECUTION_FLAGS:
        expect(f"source_static_review_decision_{flag}", source_decision.get(flag), False)

    expect("paired_execution_passed", paired_decision.get("passed"), True)
    expect("paired_execution_actual_safetycost_available_before_materialization", paired_decision.get("actual_safetycost_v1_available"), False)
    expect("paired_execution_record_count", paired_records.get("record_count"), expected_record_count)
    expect("paired_execution_candidate_tensor_mutation_records", paired_tensor.get("candidate_tensor_mutation_records"), 0)

    expect("runtime_selection_log_count", runtime["selection_log_count"], expected_selection_log_count)
    expect("runtime_record_count", runtime["record_count"], expected_record_count)
    expect("runtime_formal_seed_records", runtime["formal_seed_records"], 0)
    expect("runtime_full36_path_records", runtime["full36_path_records"], 0)
    expect("runtime_candidate_tensor_mutation_records", runtime["candidate_tensor_mutation_records"], 0)
    expect("runtime_closed_loop_training_or_online_input", runtime["closed_loop_outcomes_training_or_online_input"], False)

    require(
        "shadow_selected_summary_root_provided",
        materialization["shadow_summary_root_provided"],
        materialization["shadow_summary_root"],
        "existing directory",
    )
    expect("materialization_top1_summary_count", materialization["top1_summary_count"], runtime["validation_summary_count"])
    expect("materialization_shadow_summary_count", materialization["shadow_summary_count"], materialization["top1_summary_count"])
    expect("materialization_duplicate_run_keys", materialization["duplicate_run_key_count"], 0)
    expect("materialization_unpaired_run_keys", materialization["unpaired_run_key_count"], 0)
    expect("materialization_invalid_summary_count", materialization["invalid_summary_count"], 0)
    expect("materialization_delta_count", materialization["delta_count"], materialization["top1_summary_count"])
    expect("materialization_actual_safetycost_v1_available", materialization["actual_safetycost_v1_available"], True)
    expect("materialization_no_go_failed_count", materialization["no_go_report"]["failed_count"], 0)
    return checks


def _runtime_summary(runtime_execution_dir: Path) -> dict[str, Any]:
    logs = sorted(runtime_execution_dir.rglob("camp_selection_log.json"))
    summaries = sorted(runtime_execution_dir.rglob("camp_validation_summary.json"))
    record_count = 0
    outcome_records = 0
    missing_outcome_records = 0
    formal_seed_records = 0
    full36_path_records = 0
    tensor_mutation_records = 0
    examples: list[dict[str, Any]] = []
    for log in logs:
        rows = _records_from_payload(_read_json(log))
        seed = _seed_from_path(log)
        is_formal = seed in FORMAL_SEEDS
        is_full36 = _path_has_any_marker(log, FULL36_MARKERS)
        for index, row in enumerate(rows):
            record_count += 1
            if is_formal:
                formal_seed_records += 1
            if is_full36:
                full36_path_records += 1
            provenance = _dict(row.get("camp_candidate_tensor_provenance"))
            if bool(provenance.get("candidate_tensor_mutation_effect")):
                tensor_mutation_records += 1
            if isinstance(row.get("candidate_closed_loop_outcomes"), list):
                outcome_records += 1
            else:
                missing_outcome_records += 1
                if len(examples) < 5:
                    examples.append({"log": str(log), "record_index": index, "reason": "candidate_closed_loop_outcomes_missing"})
    return {
        "runtime_execution_dir": str(runtime_execution_dir),
        "selection_log_count": len(logs),
        "validation_summary_count": len(summaries),
        "record_count": record_count,
        "candidate_closed_loop_outcome_records": outcome_records,
        "missing_candidate_closed_loop_outcome_records": missing_outcome_records,
        "formal_seed_records": formal_seed_records,
        "full36_path_records": full36_path_records,
        "candidate_tensor_mutation_records": tensor_mutation_records,
        "closed_loop_outcomes_training_or_online_input": False,
        "missing_outcome_examples": examples,
    }


def _materialization_summary(runtime_execution_dir: Path, shadow_root: Path | None) -> dict[str, Any]:
    top1, top1_duplicates = _summary_index(runtime_execution_dir)
    shadow, shadow_duplicates = _summary_index(shadow_root) if shadow_root and shadow_root.is_dir() else ({}, [])
    duplicate_keys = sorted({*top1_duplicates, *shadow_duplicates})
    common = sorted(set(top1) & set(shadow))
    unpaired = sorted(set(top1) ^ set(shadow))
    rows = []
    deltas = []
    invalid = 0
    for key in common:
        try:
            top1_cost = _safetycost_v1(top1[key]["summary"])
            shadow_cost = _safetycost_v1(shadow[key]["summary"])
        except ValueError:
            invalid += 1
            continue
        delta = shadow_cost - top1_cost
        deltas.append(delta)
        rows.append(
            {
                "run_key": key,
                "top1_summary": top1[key]["path"],
                "shadow_selected_summary": shadow[key]["path"],
                "top1_safetycost_v1": top1_cost,
                "shadow_selected_safetycost_v1": shadow_cost,
                "delta_safetycost_v1": delta,
            }
        )
    actual_available = bool(top1) and bool(shadow) and not duplicate_keys and not unpaired and invalid == 0 and len(deltas) == len(top1)
    no_go_failures = []
    if shadow_root is None or not shadow_root.is_dir():
        no_go_failures.append("shadow_selected_run_level_summaries_missing")
    if duplicate_keys:
        no_go_failures.append("duplicate_run_keys")
    if unpaired:
        no_go_failures.append("unpaired_run_keys")
    if invalid:
        no_go_failures.append("invalid_safetycost_v1_summary")
    if not top1:
        no_go_failures.append("top1_run_level_summaries_missing")
    return {
        "shadow_summary_root_provided": bool(shadow_root and shadow_root.is_dir()),
        "shadow_summary_root": str(shadow_root) if shadow_root else None,
        "top1_summary_count": len(top1),
        "shadow_summary_count": len(shadow),
        "paired_run_key_count": len(common),
        "duplicate_run_key_count": len(duplicate_keys),
        "unpaired_run_key_count": len(unpaired),
        "invalid_summary_count": invalid,
        "delta_count": len(deltas),
        "paired_safetycost_v1_rows": rows[:100],
        "paired_safetycost_v1_row_count": len(rows),
        "delta_summary": _delta_summary(deltas),
        "delta_bootstrap_ci95": _bootstrap_ci(deltas),
        "actual_safetycost_v1_available": actual_available,
        "actual_safetycost_v1_claim_rule_evaluable": actual_available,
        "safetycost_v1_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "unavailable_reason": None if actual_available else ", ".join(no_go_failures),
        "no_go_report": {
            "entries": [
                "source_static_review_missing_or_failed",
                "dp_head_drift",
                "candidate_tensor_identity_drift",
                "shadow_selected_run_level_summaries_missing",
                "duplicate_or_unpaired_run_keys",
                "invalid_safetycost_v1_summary",
                "closed_loop_outcome_training_or_online_input",
                "full36_or_formal_seed_11_12_13_present",
                "promotion_deployment_online_selector_or_claim",
            ],
            "failures": no_go_failures,
            "failed_count": len(no_go_failures),
            "promotion_authorized": False,
            "deployment_authorized": False,
            "online_selector_change_authorized": False,
            "safety_or_camp_over_dp_claim_authorized": False,
        },
    }


def _summary_index(root: Path | None) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if root is None or not root.is_dir():
        return {}, []
    result: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    for path in sorted(root.rglob("camp_validation_summary.json")):
        summary = _read_json_dict(path)
        key = _summary_run_key(summary, path)
        if key not in result:
            result[key] = {"path": str(path), "summary": summary}
        else:
            duplicates.add(key)
    return result, sorted(duplicates)


def _summary_run_key(summary: dict[str, Any], path: Path) -> str:
    benchmark = _dict(summary.get("benchmark"))
    route = Path(str(benchmark.get("route") or path.parents[3].name)).stem
    seed = benchmark.get("seed") or _seed_from_path(path)
    max_npcs = benchmark.get("max_npcs")
    spawn = benchmark.get("spawn_probability")
    traffic = benchmark.get("traffic_lights")
    advance = summary.get("advance_mode") or benchmark.get("advance_mode")
    return "|".join(
        [
            f"route={route}",
            f"seed={seed}",
            f"max_npcs={max_npcs}",
            f"spawn_probability={spawn}",
            f"traffic_lights={traffic}",
            f"advance_mode={advance}",
        ]
    )


def _safetycost_v1(summary: dict[str, Any]) -> float:
    collision = _clip01(_number(summary, "obb_collision_rate"))
    near_miss = _clip01(_number(summary, "near_miss_rate"))
    lane = _clip01(_number(summary, "lane_violation_rate"))
    red = _clip01(_number(summary, "red_light_violation_rate"))
    planned_red = _clip01(_number(summary, "planned_red_light_violation_rate", default=0.0))
    jerk = min(max(_number(summary, "mean_jerk_magnitude_mps3") / 10.0, 0.0), 10.0)
    lateral = min(max(_number(summary, "mean_lateral_acceleration_mps2") / 2.0, 0.0), 10.0)
    route_shortfall = _clip01(1.0 - _number(summary, "route_completion_rate"))
    return float(
        100.0 * collision
        + 10.0 * near_miss
        + 20.0 * lane
        + 30.0 * red
        + 15.0 * planned_red
        + jerk
        + 2.0 * lateral
        + 2.0 * route_shortfall
    )


def _source_summary(
    *,
    source_preflight_static_review_artifact_dir: Path,
    source_preflight_static_review_json: Path,
    source_preflight_static_review_md: Path,
    source_preflight_static_review_sha256s: Path,
    paired_execution_artifact_dir: Path,
    paired_execution_json: Path,
    paired_execution_sha256s: Path,
) -> dict[str, Any]:
    return {
        "source_static_review": {
            "artifact_dir": str(source_preflight_static_review_artifact_dir),
            "json_sha256": _sha256(source_preflight_static_review_json),
            "md_sha256": _sha256(source_preflight_static_review_md),
            "sha256s_sha256": _sha256(source_preflight_static_review_sha256s),
            "root_sha256s_sha256": _sha256(source_preflight_static_review_artifact_dir / "SHA256SUMS"),
        },
        "paired_execution": {
            "artifact_dir": str(paired_execution_artifact_dir),
            "json_sha256": _sha256(paired_execution_json),
            "sha256s_sha256": _sha256(paired_execution_sha256s),
            "root_sha256s_sha256": _sha256(paired_execution_artifact_dir / "SHA256SUMS"),
        },
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], materialization: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "execution_enabled" in failed:
        failure_class = "explicit_actual_safetycost_outcome_materialization_execution_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_static_review") for name in failed):
        failure_class = "source_static_review_contract_failure"
    elif any(name.startswith("paired_execution") for name in failed):
        failure_class = "paired_execution_source_contract_failure"
    elif any(name.startswith(("runtime_", "materialization_")) for name in failed):
        failure_class = "actual_safetycost_outcome_source_missing"
    else:
        failure_class = "actual_safetycost_outcome_materialization_execution_contract_failure"
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "recommended_next_work": AUTHORIZED_NEXT_WORK if passed else FAILED_NEXT_WORK,
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_outcome_materialization_execution_passed": bool(passed),
        "actual_safetycost_outcome_materialization_executed_by_this_gate": True,
        "actual_safetycost_v1_available": materialization["actual_safetycost_v1_available"],
        "actual_safetycost_v1_claim_rule_evaluable": materialization["actual_safetycost_v1_claim_rule_evaluable"],
        "safetycost_v1_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "closed_loop_outcome_training_or_online_input_authorized": False,
        "previous_no_promotion_closeout_preserved": True,
        "direct_promotion_recommendation": False,
        "recommendation": "result_review_actual_safetycost_outcome_materialization_only" if passed else "provide_shadow_selected_run_level_outcome_summaries_before_rerun",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / EXECUTION_JSON_NAME
    md_path = output_dir / EXECUTION_MD_NAME
    json_path.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    sums = [f"{_sha256(path)}  {path.name}" for path in (json_path, md_path)]
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    runtime = report["runtime_source_summary"]
    materialization = report["materialization_summary"]
    lines = [
        "# v14 Actual-SafetyCost Outcome-Materialization Execution",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failure class: `{decision['failure_class']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Recommended next work: `{decision['recommended_next_work']}`",
        "",
        "## Runtime Source",
        "",
        f"- Selection logs: `{runtime['selection_log_count']}`",
        f"- Selection records: `{runtime['record_count']}`",
        f"- Candidate closed-loop outcome records: `{runtime['candidate_closed_loop_outcome_records']}`",
        f"- Missing candidate closed-loop outcome records: `{runtime['missing_candidate_closed_loop_outcome_records']}`",
        f"- Validation summaries: `{runtime['validation_summary_count']}`",
        "",
        "## Materialization",
        "",
        f"- Top-1 summaries: `{materialization['top1_summary_count']}`",
        f"- Shadow-selected summaries: `{materialization['shadow_summary_count']}`",
        f"- Paired run keys: `{materialization['paired_run_key_count']}`",
        f"- Actual SafetyCost v1 available: `{materialization['actual_safetycost_v1_available']}`",
        f"- Claim rule evaluable: `{materialization['actual_safetycost_v1_claim_rule_evaluable']}`",
        f"- Unavailable reason: `{materialization['unavailable_reason']}`",
        "",
        "## Boundary",
        "",
        "- Evidence only: no replay, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
        "- Closed-loop outcomes remain forbidden as training or online selector inputs.",
        f"- Score expression: `{report['analysis']['score_expression']}`",
    ]
    return "\n".join(lines) + "\n"


def _delta_summary(deltas: list[float]) -> dict[str, Any]:
    if not deltas:
        return {"count": 0, "mean": None, "min": None, "max": None, "better_records": 0, "worse_records": 0, "tie_records": 0}
    return {
        "count": len(deltas),
        "mean": sum(deltas) / len(deltas),
        "min": min(deltas),
        "max": max(deltas),
        "better_records": sum(1 for delta in deltas if delta < 0.0),
        "worse_records": sum(1 for delta in deltas if delta > 0.0),
        "tie_records": sum(1 for delta in deltas if delta == 0.0),
    }


def _bootstrap_ci(deltas: list[float]) -> dict[str, Any]:
    if not deltas:
        return {"mean": None, "ci95_low": None, "ci95_high": None, "resamples": BOOTSTRAP_RESAMPLES}
    rng = random.Random(20260706)
    means: list[float] = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        total = 0.0
        for _ in deltas:
            total += deltas[rng.randrange(len(deltas))]
        means.append(total / len(deltas))
    means.sort()
    return {
        "mean": sum(deltas) / len(deltas),
        "ci95_low": means[int(0.025 * BOOTSTRAP_RESAMPLES)],
        "ci95_high": means[min(BOOTSTRAP_RESAMPLES - 1, int(0.975 * BOOTSTRAP_RESAMPLES))],
        "resamples": BOOTSTRAP_RESAMPLES,
    }


def _records_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return [item for item in payload["records"] if isinstance(item, dict)]
    return []


def _duplicate_keys(keys: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for key in keys:
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return sorted(duplicates)


def _path_has_any_marker(path: Path, markers: tuple[str, ...]) -> bool:
    lowered = str(path).lower()
    return any(marker in lowered for marker in markers)


def _seed_from_path(path: Path) -> int | None:
    for part in path.parts:
        if part.startswith("seed_"):
            return _int_or_none(part.removeprefix("seed_"))
    return None


def _number(summary: dict[str, Any], key: str, default: float | None = None) -> float:
    value = summary.get(key, default)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be numeric.") from None
    if not math.isfinite(number):
        raise ValueError(f"{key} must be finite.")
    return number


def _clip01(value: float) -> float:
    return min(max(float(value), 0.0), 1.0)


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_dict(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip()] = value.strip()
    return values


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
