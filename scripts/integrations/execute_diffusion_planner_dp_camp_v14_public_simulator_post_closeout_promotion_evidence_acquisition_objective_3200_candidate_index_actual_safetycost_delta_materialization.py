#!/usr/bin/env python3
"""Materialize objective-3200 candidate-index SafetyCost deltas.

This gate is evidence-only. It consumes the audited candidate-index
delta-materialization preflight static review plus the audited candidate-index
replay outcome-acquisition execution artifact, then computes paired
SafetyCost_v1(CAMP shadow-selected fixed-DP candidate) -
SafetyCost_v1(DP Top-1 candidate index 0) rows. It never reruns replay,
generates or rewrites trajectories, modifies Diffusion Planner, trains CAMP,
promotes a selector, deploys, enables online selection, or makes claims.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import random
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


def _load_source_static_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_candidate_index_"
        "actual_safetycost_delta_materialization_preflight_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_delta_materialization_preflight_static_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_candidate_execution_module():
    execution_path = Path(__file__).resolve().with_name(
        "execute_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_candidate_index_"
        "replay_outcome_acquisition.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_replay_outcome_acquisition_execution",
        execution_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_STATIC_REVIEW_MODULE = _load_source_static_review_module()
CANDIDATE_EXECUTION_MODULE = _load_candidate_execution_module()
HELPER_MODULE = SOURCE_STATIC_REVIEW_MODULE.HELPER_MODULE

FIXED_DP_HEAD = SOURCE_STATIC_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_STATIC_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_STATIC_REVIEW_SCHEMA = SOURCE_STATIC_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_STATIC_REVIEW_STATUS = SOURCE_STATIC_REVIEW_MODULE.READY_STATUS
SOURCE_STATIC_REVIEW_JSON_NAME = SOURCE_STATIC_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_STATIC_REVIEW_MD_NAME = SOURCE_STATIC_REVIEW_MODULE.REVIEW_MD_NAME
CANDIDATE_EXECUTION_SCHEMA = CANDIDATE_EXECUTION_MODULE.SCHEMA_VERSION
CANDIDATE_EXECUTION_STATUS = CANDIDATE_EXECUTION_MODULE.READY_STATUS
CANDIDATE_EXECUTION_JSON_NAME = CANDIDATE_EXECUTION_MODULE.EXECUTION_JSON_NAME
CANDIDATE_EXECUTION_MD_NAME = CANDIDATE_EXECUTION_MODULE.EXECUTION_MD_NAME
BLOCKED_ACTIONS = SOURCE_STATIC_REVIEW_MODULE.BLOCKED_ACTIONS
OBJECTIVE_REQUIRED_RECORDS = SOURCE_STATIC_REVIEW_MODULE.OBJECTIVE_REQUIRED_RECORDS
EXPECTED_SELECTION_LOG_COUNT = SOURCE_STATIC_REVIEW_MODULE.EXPECTED_SELECTION_LOG_COUNT
EXPECTED_NUM_CANDIDATES = CANDIDATE_EXECUTION_MODULE.EXPECTED_NUM_CANDIDATES

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_actual_safetycost_delta_materialization_execution_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_STATIC_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_execution_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_execution_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_execution_result_review_only"
)
FAILED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_execution_failed_user_decision_required"
)

EXECUTION_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_execution.json"
)
EXECUTION_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_delta_materialization_execution.md"
)
DELTA_TABLE_JSONL_NAME = "actual_safetycost_v1_delta_table.jsonl"

SAFETY_WEIGHT_KEYS = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light",
    "mean_jerk",
    "mean_lateral_acceleration",
)
BOOTSTRAP_RESAMPLES = 10_000
EPS = 1e-9


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_preflight_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_json", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_md", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--candidate_index_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--candidate_index_execution_json", type=Path, required=True)
    parser.add_argument("--candidate_index_execution_md", type=Path, required=True)
    parser.add_argument("--candidate_index_execution_sha256s", type=Path, required=True)
    parser.add_argument("--candidate_index_output_root", type=Path, default=None)
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
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_delta_materialization_execution",
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
        candidate_index_execution_artifact_dir=args.candidate_index_execution_artifact_dir,
        candidate_index_execution_json=args.candidate_index_execution_json,
        candidate_index_execution_md=args.candidate_index_execution_md,
        candidate_index_execution_sha256s=args.candidate_index_execution_sha256s,
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
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_delta_materialization_execution
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
    candidate_index_execution_artifact_dir: Path,
    candidate_index_execution_json: Path,
    candidate_index_execution_md: Path,
    candidate_index_execution_sha256s: Path,
    candidate_index_output_root: Path | None,
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
) -> dict[str, Any]:
    source_artifact_dir = source_preflight_static_review_artifact_dir.resolve()
    candidate_artifact_dir = candidate_index_execution_artifact_dir.resolve()
    paths = {
        "source_preflight_static_review_json": source_preflight_static_review_json.resolve(),
        "source_preflight_static_review_md": source_preflight_static_review_md.resolve(),
        "source_preflight_static_review_sha256s": source_preflight_static_review_sha256s.resolve(),
        "candidate_index_execution_json": candidate_index_execution_json.resolve(),
        "candidate_index_execution_md": candidate_index_execution_md.resolve(),
        "candidate_index_execution_sha256s": candidate_index_execution_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    source_files = _source_artifact_files(source_artifact_dir)
    candidate_files = _candidate_execution_files(candidate_artifact_dir)

    source_review = _read_json_dict(paths["source_preflight_static_review_json"])
    candidate_execution = _read_json_dict(paths["candidate_index_execution_json"])
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])
    source_heads = _parse_key_values(_read_text(source_files["heads"]))
    candidate_heads = _parse_key_values(_read_text(candidate_files["heads"]))
    source_root_sha256s = _read_sha256sums(source_files["root_sha256s"])
    source_nested_sha256s = _read_sha256sums(paths["source_preflight_static_review_sha256s"])
    candidate_root_sha256s = _read_sha256sums(candidate_files["root_sha256s"])
    candidate_nested_sha256s = _read_sha256sums(paths["candidate_index_execution_sha256s"])

    candidate_root = _candidate_output_root(candidate_execution, candidate_index_output_root)
    materialization = _materialize_delta_table(
        candidate_root,
        expected_num_candidates=expected_num_candidates,
    )
    checks = _checks(
        enabled=enabled,
        source_artifact_dir=source_artifact_dir,
        candidate_artifact_dir=candidate_artifact_dir,
        paths=paths,
        source_files=source_files,
        candidate_files=candidate_files,
        source_review=source_review,
        candidate_execution=candidate_execution,
        source_heads=source_heads,
        candidate_heads=candidate_heads,
        source_root_sha256s=source_root_sha256s,
        source_nested_sha256s=source_nested_sha256s,
        candidate_root_sha256s=candidate_root_sha256s,
        candidate_nested_sha256s=candidate_nested_sha256s,
        v14_text=v14_text,
        status_text=status_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_record_count=expected_record_count,
        expected_selection_log_count=expected_selection_log_count,
        expected_num_candidates=expected_num_candidates,
        materialization=materialization,
    )
    passed = all(check["passed"] for check in checks)
    decision = _decision(passed=passed, checks=checks, materialization=materialization)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "objective_3200_candidate_index_actual_safetycost_delta_materialization_execution": True,
            "execution_enabled": bool(enabled),
            "read_only_existing_candidate_index_outcomes": True,
            "candidate_index_replay_execution_executed_by_this_gate": False,
            "outcome_acquisition_executed_by_this_gate": False,
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
            "candidate_index_execution_artifact_dir": str(candidate_artifact_dir),
            "candidate_index_output_root": str(candidate_root),
            "output_dir": str(output_dir.resolve()),
            **{name: str(path) for name, path in paths.items()},
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_static_review_camp_head": _kv(source_heads, "CAMP_HEAD", "camp_head"),
            "source_static_review_camp_origin_main": _kv(
                source_heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main"
            ),
            "source_static_review_dp_head": _kv(source_heads, "DP_HEAD", "dp_head"),
            "candidate_index_execution_camp_head": _kv(candidate_heads, "CAMP_HEAD", "camp_head"),
            "candidate_index_execution_camp_origin_main": _kv(
                candidate_heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main"
            ),
            "candidate_index_execution_dp_head": _kv(candidate_heads, "DP_HEAD", "dp_head"),
        },
        "source_artifact_hashes": _source_hashes(
            source_files=source_files,
            candidate_files=candidate_files,
            paths=paths,
        ),
        "source_static_review_summary": _source_static_review_summary(source_review),
        "candidate_index_execution_summary": _candidate_execution_summary(candidate_execution),
        "safetycost_v1_metric_spec": _safetycost_metric_spec(materialization),
        "delta_materialization_summary": _drop_rows(materialization),
        "paired_safetycost_v1_rows": materialization["paired_safetycost_v1_rows"],
        "no_go_report": materialization["no_go_report"],
        "execution_checks": checks,
        "final_decision": decision,
    }


def _checks(
    *,
    enabled: bool,
    source_artifact_dir: Path,
    candidate_artifact_dir: Path,
    paths: dict[str, Path],
    source_files: dict[str, Path],
    candidate_files: dict[str, Path],
    source_review: dict[str, Any],
    candidate_execution: dict[str, Any],
    source_heads: dict[str, str],
    candidate_heads: dict[str, str],
    source_root_sha256s: dict[str, str],
    source_nested_sha256s: dict[str, str],
    candidate_root_sha256s: dict[str, str],
    candidate_nested_sha256s: dict[str, str],
    v14_text: str,
    status_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_record_count: int,
    expected_selection_log_count: int,
    expected_num_candidates: int,
    materialization: dict[str, Any],
) -> list[dict[str, Any]]:
    source_decision = _dict(source_review.get("final_decision"))
    candidate_decision = _dict(candidate_execution.get("final_decision"))
    candidate_summary = _dict(candidate_execution.get("candidate_index_outcome_summary"))
    strict_pairing = _dict(candidate_execution.get("strict_pairing_summary"))
    no_go = _dict(candidate_execution.get("no_go_report"))
    checks = [
        _expect("execution_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("status_doc_latest_status", _latest_value(status_text, "current_v14_status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("status_doc_latest_next_work", _latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _check("source_artifact_dir_exists", source_artifact_dir.is_dir(), str(source_artifact_dir), "directory"),
        _check("candidate_index_execution_artifact_dir_exists", candidate_artifact_dir.is_dir(), str(candidate_artifact_dir), "directory"),
        _expect("source_artifact_run_exit", _read_text(source_files["run_exit"]).strip(), "0"),
        _expect("candidate_index_execution_run_exit", _read_text(candidate_files["run_exit"]).strip(), "0"),
        _expect("source_static_review_schema", source_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA),
        _expect("source_static_review_passed", source_decision.get("passed"), True),
        _expect("source_static_review_status", source_decision.get("status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("source_static_review_authorized_next", source_decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect(
            "source_static_review_execution_authorized",
            source_decision.get("actual_safetycost_delta_materialization_execution_authorized"),
            True,
        ),
        _expect(
            "source_static_review_no_delta_execution",
            source_decision.get("actual_safetycost_delta_materialization_executed_by_this_gate"),
            False,
        ),
        _expect("source_static_review_dp_head_fixed", _kv(source_heads, "DP_HEAD", "dp_head"), required_dp_head),
        _expect("candidate_index_execution_schema", candidate_execution.get("schema_version"), CANDIDATE_EXECUTION_SCHEMA),
        _expect("candidate_index_execution_passed", candidate_decision.get("passed"), True),
        _expect("candidate_index_execution_status", candidate_decision.get("status"), CANDIDATE_EXECUTION_STATUS),
        _expect(
            "candidate_index_execution_replay_executed",
            candidate_decision.get("candidate_index_replay_execution_executed_by_this_gate"),
            True,
        ),
        _expect(
            "candidate_index_execution_outcome_acquisition_executed",
            candidate_decision.get("outcome_acquisition_executed_by_this_gate"),
            True,
        ),
        _expect("candidate_index_execution_dp_head_fixed", _kv(candidate_heads, "DP_HEAD", "dp_head"), required_dp_head),
        _expect("candidate_index_execution_selection_logs", candidate_summary.get("selection_log_count"), expected_selection_log_count),
        _expect("candidate_index_execution_record_count", candidate_summary.get("record_count"), expected_record_count),
        _expect(
            "candidate_index_execution_candidate_closed_loop_outcome_records",
            candidate_summary.get("candidate_closed_loop_outcome_records"),
            expected_record_count,
        ),
        _expect(
            "candidate_index_execution_missing_candidate_closed_loop_outcome_records",
            candidate_summary.get("missing_candidate_closed_loop_outcome_records"),
            0,
        ),
        _expect("candidate_index_execution_paired_record_key_count", strict_pairing.get("paired_record_key_count"), expected_record_count),
        _expect("candidate_index_execution_no_go_failed_count", no_go.get("failed_count"), 0),
        _expect("candidate_index_execution_actual_safetycost_before_materialization", candidate_decision.get("actual_safetycost_v1_available"), False),
        _expect("candidate_index_output_root_exists", materialization["candidate_index_output_root_exists"], True),
        _expect("delta_selection_log_count", materialization["selection_log_count"], expected_selection_log_count),
        _expect("delta_record_count", materialization["record_count"], expected_record_count),
        _expect("delta_unique_record_key_count", materialization["unique_record_key_count"], expected_record_count),
        _expect("delta_duplicate_record_key_count", materialization["duplicate_record_key_count"], 0),
        _expect("delta_missing_candidate_outcome_records", materialization["missing_candidate_outcome_records"], 0),
        _expect("delta_missing_top1_outcome_records", materialization["missing_top1_outcome_records"], 0),
        _expect("delta_missing_shadow_outcome_records", materialization["missing_shadow_outcome_records"], 0),
        _expect("delta_invalid_safetycost_records", materialization["invalid_safetycost_records"], 0),
        _expect("delta_num_candidate_mismatch_records", materialization["num_candidate_mismatch_records"], 0),
        _expect("delta_candidate_tensor_mutation_records", materialization["candidate_tensor_mutation_records"], 0),
        _expect("delta_reference_blend_records", materialization["reference_blend_records"], 0),
        _expect("delta_closed_loop_training_or_online_input_records", materialization["closed_loop_training_or_online_input_records"], 0),
        _expect("delta_non_affine_score_records", materialization["non_affine_score_records"], 0),
        _expect("delta_non_simplex_weight_records", materialization["non_simplex_weight_records"], 0),
        _expect("delta_materialized_row_count", materialization["paired_safetycost_v1_row_count"], expected_record_count),
        _expect("delta_actual_safetycost_v1_available", materialization["actual_safetycost_v1_available"], True),
        _expect("delta_actual_safetycost_v1_claim_rule_evaluable", materialization["actual_safetycost_v1_claim_rule_evaluable"], True),
        _expect("delta_no_go_failed_count", materialization["no_go_report"]["failed_count"], 0),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, allow_empty=False))
    for name, path in source_files.items():
        checks.extend(_path_checks(f"source_artifact_{name}", path, allow_empty=name == "stderr"))
    for name, path in candidate_files.items():
        checks.extend(_path_checks(f"candidate_index_execution_artifact_{name}", path, allow_empty=name == "stderr"))
    checks.extend(
        _sha_checks(
            prefix="source",
            root_sha256s=source_root_sha256s,
            nested_sha256s=source_nested_sha256s,
            files=source_files,
            json_name=SOURCE_STATIC_REVIEW_JSON_NAME,
            md_name=SOURCE_STATIC_REVIEW_MD_NAME,
            subdir="review",
        )
    )
    checks.extend(
        _sha_checks(
            prefix="candidate_index_execution",
            root_sha256s=candidate_root_sha256s,
            nested_sha256s=candidate_nested_sha256s,
            files=candidate_files,
            json_name=CANDIDATE_EXECUTION_JSON_NAME,
            md_name=CANDIDATE_EXECUTION_MD_NAME,
            subdir="report",
        )
    )
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_static_review_{action}", source_decision.get(action), False))
        checks.append(_expect(f"candidate_index_execution_{action}", candidate_decision.get(action), False))
    return checks


def _materialize_delta_table(root: Path, *, expected_num_candidates: int) -> dict[str, Any]:
    logs = sorted(root.rglob("camp_selection_log.json")) if root.is_dir() else []
    rows: list[dict[str, Any]] = []
    record_keys: set[str] = set()
    duplicate_count = 0
    counters: Counter[str] = Counter()
    errors: list[dict[str, Any]] = []
    weight_hashes: Counter[str] = Counter()
    for log in logs:
        records = _records_from_payload(_read_json(log))
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                counters["invalid_record_payloads"] += 1
                continue
            counters["record_count"] += 1
            record_key = _record_key(root, log, index)
            if record_key in record_keys:
                duplicate_count += 1
            record_keys.add(record_key)
            _boundary_counters(record, counters, expected_num_candidates=expected_num_candidates)
            try:
                row = _delta_row(root=root, log=log, index=index, record=record)
                rows.append(row)
                weight_hashes[row["safetycost_v1_weight_sha256"]] += 1
            except ValueError as exc:
                counters["invalid_safetycost_records"] += 1
                if len(errors) < 10:
                    errors.append({"record_key": record_key, "reason": str(exc)})
    deltas = [row["delta_safetycost_v1"] for row in rows]
    no_go = _no_go_report(
        counters=counters,
        row_count=len(rows),
        duplicate_count=duplicate_count,
    )
    actual_available = (
        bool(root.is_dir())
        and counters["record_count"] > 0
        and len(rows) == counters["record_count"]
        and duplicate_count == 0
        and no_go["failed_count"] == 0
    )
    return {
        "candidate_index_output_root": str(root),
        "candidate_index_output_root_exists": root.is_dir(),
        "selection_log_count": len(logs),
        "record_count": counters["record_count"],
        "unique_record_key_count": len(record_keys),
        "duplicate_record_key_count": duplicate_count,
        "record_key_sha256": hashlib.sha256("\n".join(sorted(record_keys)).encode("utf-8")).hexdigest(),
        "paired_safetycost_v1_row_count": len(rows),
        "same_as_top1_records": sum(1 for row in rows if row["shadow_selected_index"] == 0),
        "non_top1_shadow_selected_records": sum(1 for row in rows if row["shadow_selected_index"] != 0),
        "missing_candidate_outcome_records": counters["missing_candidate_outcome_records"],
        "missing_top1_outcome_records": counters["missing_top1_outcome_records"],
        "missing_shadow_outcome_records": counters["missing_shadow_outcome_records"],
        "invalid_safetycost_records": counters["invalid_safetycost_records"],
        "invalid_record_payloads": counters["invalid_record_payloads"],
        "num_candidate_mismatch_records": counters["num_candidate_mismatch_records"],
        "candidate_tensor_mutation_records": counters["candidate_tensor_mutation_records"],
        "reference_blend_records": counters["reference_blend_records"],
        "closed_loop_training_or_online_input_records": counters["closed_loop_training_or_online_input_records"],
        "non_affine_score_records": counters["non_affine_score_records"],
        "non_simplex_weight_records": counters["non_simplex_weight_records"],
        "unique_safetycost_v1_weight_hash_count": len(weight_hashes),
        "safetycost_v1_weight_hash_preview": sorted(weight_hashes)[:5],
        "delta_summary": _delta_summary(deltas),
        "delta_bootstrap_ci95": _bootstrap_ci(deltas),
        "claim_rule": _claim_rule(deltas=deltas, no_go=no_go),
        "actual_safetycost_v1_available": actual_available,
        "actual_safetycost_v1_claim_rule_evaluable": actual_available,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "paired_safetycost_v1_rows": rows,
        "invalid_examples": errors,
        "no_go_report": no_go,
    }


def _delta_row(*, root: Path, log: Path, index: int, record: dict[str, Any]) -> dict[str, Any]:
    outcomes = record.get("candidate_closed_loop_outcomes")
    if not isinstance(outcomes, list) or not outcomes:
        raise ValueError("candidate_closed_loop_outcomes_missing")
    weights = _safety_weights(record.get("candidate_closed_loop_outcome_weights"))
    shadow_index = _int_or_none(record.get("shadow_selected_index"))
    if shadow_index is None:
        raise ValueError("shadow_selected_index_missing")
    top1 = _outcome_by_index(outcomes, 0)
    shadow = _outcome_by_index(outcomes, shadow_index)
    if top1 is None:
        raise ValueError("top1_candidate_outcome_missing")
    if shadow is None:
        raise ValueError("shadow_selected_candidate_outcome_missing")
    top1_cost, top1_components = _candidate_safetycost_v1(top1, weights)
    shadow_cost, shadow_components = _candidate_safetycost_v1(shadow, weights)
    delta = shadow_cost - top1_cost
    return {
        "record_key": _record_key(root, log, index),
        "selection_log": str(log),
        "record_index": index,
        "selection_step": record.get("selection_step"),
        "top1_candidate_index": 0,
        "shadow_selected_index": shadow_index,
        "executed_index": record.get("executed_index"),
        "top1_safetycost_v1": top1_cost,
        "camp_shadow_selected_safetycost_v1": shadow_cost,
        "delta_safetycost_v1": delta,
        "delta_direction": "better" if delta < -EPS else "worse" if delta > EPS else "tie",
        "top1_progress_m": _number_or_none(top1.get("progress_m")),
        "camp_shadow_selected_progress_m": _number_or_none(shadow.get("progress_m")),
        "top1_value": _number_or_none(top1.get("value")),
        "camp_shadow_selected_value": _number_or_none(shadow.get("value")),
        "top1_feasible": top1.get("feasible"),
        "camp_shadow_selected_feasible": shadow.get("feasible"),
        "top1_components": top1_components,
        "camp_shadow_selected_components": shadow_components,
        "safetycost_v1_weights": weights,
        "safetycost_v1_weight_sha256": hashlib.sha256(
            json.dumps(_stable(weights), sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }


def _candidate_safetycost_v1(outcome: dict[str, Any], weights: dict[str, float]) -> tuple[float, dict[str, float]]:
    collision = _binary_metric(outcome.get("collision")) * weights["collision"]
    near_miss = _binary_metric(outcome.get("near_miss")) * weights["near_miss"]
    lane = _binary_metric(outcome.get("lane_violation")) * weights["lane_violation"]
    red = _binary_metric(outcome.get("red_light_violation")) * weights["red_light"]
    jerk = max(_required_number(outcome, "mean_jerk_mps3"), 0.0) * weights["mean_jerk"]
    lateral = max(_required_number(outcome, "mean_lateral_acceleration_mps2"), 0.0) * weights[
        "mean_lateral_acceleration"
    ]
    components = {
        "collision": collision,
        "near_miss": near_miss,
        "lane_violation": lane,
        "red_light_violation": red,
        "mean_jerk": jerk,
        "mean_lateral_acceleration": lateral,
    }
    return float(sum(components.values())), components


def _safety_weights(payload: Any) -> dict[str, float]:
    if not isinstance(payload, dict):
        raise ValueError("candidate_closed_loop_outcome_weights_missing")
    weights: dict[str, float] = {}
    for key in SAFETY_WEIGHT_KEYS:
        value = _number_or_none(payload.get(key))
        if value is None:
            raise ValueError(f"safety_weight_missing:{key}")
        weights[key] = value
    return weights


def _boundary_counters(record: dict[str, Any], counters: Counter[str], *, expected_num_candidates: int) -> None:
    outcomes = record.get("candidate_closed_loop_outcomes")
    if not isinstance(outcomes, list) or not outcomes:
        counters["missing_candidate_outcome_records"] += 1
    else:
        if _outcome_by_index(outcomes, 0) is None:
            counters["missing_top1_outcome_records"] += 1
        shadow_index = _int_or_none(record.get("shadow_selected_index"))
        if shadow_index is None or _outcome_by_index(outcomes, shadow_index) is None:
            counters["missing_shadow_outcome_records"] += 1
        if len(outcomes) != expected_num_candidates:
            counters["num_candidate_mismatch_records"] += 1
    if record.get("num_candidates") not in (None, expected_num_candidates):
        counters["num_candidate_mismatch_records"] += 1
    provenance = _dict(record.get("camp_candidate_tensor_provenance"))
    if provenance.get("candidate_tensor_mutation_effect") is True:
        counters["candidate_tensor_mutation_records"] += 1
    if provenance.get("pre_post_tensor_hash_equal") is False:
        counters["candidate_tensor_mutation_records"] += 1
    if provenance.get("reference_blend_present") is True or record.get("candidate_reference_blend_steps") not in (0, None):
        counters["reference_blend_records"] += 1
    generation = _dict(record.get("candidate_generation_contract"))
    if generation.get("reference_blend_steps") is not None:
        counters["reference_blend_records"] += 1
    replay = _dict(record.get("candidate_index_replay_harness"))
    if replay.get("closed_loop_outcomes_used_for_training") is True:
        counters["closed_loop_training_or_online_input_records"] += 1
    if replay.get("closed_loop_outcomes_used_for_online_selector") is True:
        counters["closed_loop_training_or_online_input_records"] += 1
    if provenance.get("outcome_label_input") is True:
        counters["closed_loop_training_or_online_input_records"] += 1
    selector = _dict(record.get("default_off_shadow_selector"))
    if selector and selector.get("score_expression") != SCORE_EXPRESSION:
        counters["non_affine_score_records"] += 1
    if not _is_simplex(record.get("selection_weights", record.get("weights"))):
        counters["non_simplex_weight_records"] += 1


def _no_go_report(*, counters: Counter[str], row_count: int, duplicate_count: int) -> dict[str, Any]:
    failures = []
    if row_count == 0:
        failures.append("actual_safetycost_delta_rows_missing")
    if duplicate_count:
        failures.append("duplicate_record_keys")
    for key in (
        "missing_candidate_outcome_records",
        "missing_top1_outcome_records",
        "missing_shadow_outcome_records",
        "invalid_safetycost_records",
        "invalid_record_payloads",
        "num_candidate_mismatch_records",
        "candidate_tensor_mutation_records",
        "reference_blend_records",
        "closed_loop_training_or_online_input_records",
        "non_affine_score_records",
        "non_simplex_weight_records",
    ):
        if counters[key]:
            failures.append(key)
    return {
        "entries": [
            "actual_safetycost_delta_rows_missing",
            "candidate_index_outcomes_missing_or_unlocked",
            "dp_top1_baseline_outcomes_missing_or_unlocked",
            "unmatched_or_duplicate_paired_run_keys",
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


def _delta_summary(deltas: list[float]) -> dict[str, Any]:
    if not deltas:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
            "better_records": 0,
            "tie_records": 0,
            "worse_records": 0,
        }
    sorted_deltas = sorted(deltas)
    return {
        "count": len(deltas),
        "mean": sum(deltas) / len(deltas),
        "median": statistics.median(sorted_deltas),
        "min": min(sorted_deltas),
        "max": max(sorted_deltas),
        "p05": _percentile(sorted_deltas, 0.05),
        "p95": _percentile(sorted_deltas, 0.95),
        "better_records": sum(1 for delta in deltas if delta < -EPS),
        "tie_records": sum(1 for delta in deltas if abs(delta) <= EPS),
        "worse_records": sum(1 for delta in deltas if delta > EPS),
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


def _claim_rule(*, deltas: list[float], no_go: dict[str, Any]) -> dict[str, Any]:
    ci = _bootstrap_ci(deltas)
    evaluable = bool(deltas) and no_go["failed_count"] == 0
    passed = bool(evaluable and ci["ci95_high"] is not None and ci["ci95_high"] < 0.0)
    return {
        "hard_gates_passed": no_go["failed_count"] == 0,
        "ci95_high_lt_zero_required": True,
        "evaluable": evaluable,
        "passed": passed,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], materialization: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "execution_enabled" in failed:
        failure_class = "explicit_candidate_index_actual_safetycost_delta_materialization_execution_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_drift"
    elif any(name.startswith("source_static_review") or name.startswith("source_artifact") for name in failed):
        failure_class = "source_static_review_contract_failure"
    elif any(name.startswith("candidate_index_execution") for name in failed):
        failure_class = "candidate_index_execution_source_contract_failure"
    elif any(name.startswith("delta_") for name in failed):
        failure_class = "actual_safetycost_delta_materialization_contract_failure"
    else:
        failure_class = "candidate_index_actual_safetycost_delta_materialization_execution_contract_failure"
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else FAILED_NEXT_WORK,
        "objective_3200_candidate_index_actual_safetycost_delta_materialization_execution_passed": bool(passed),
        "actual_safetycost_delta_materialization_executed_by_this_gate": True,
        "candidate_index_replay_executed_by_this_gate": False,
        "outcome_acquisition_executed_by_this_gate": False,
        "objective_required_records": OBJECTIVE_REQUIRED_RECORDS,
        "paired_safetycost_v1_row_count": materialization["paired_safetycost_v1_row_count"],
        "same_as_top1_records": materialization["same_as_top1_records"],
        "non_top1_shadow_selected_records": materialization["non_top1_shadow_selected_records"],
        "actual_safetycost_v1_available": materialization["actual_safetycost_v1_available"],
        "actual_safetycost_v1_claim_rule_evaluable": materialization["actual_safetycost_v1_claim_rule_evaluable"],
        "delta_mean_safetycost_v1": materialization["delta_summary"]["mean"],
        "delta_ci95_low": materialization["delta_bootstrap_ci95"]["ci95_low"],
        "delta_ci95_high": materialization["delta_bootstrap_ci95"]["ci95_high"],
        "delta_better_records": materialization["delta_summary"]["better_records"],
        "delta_tie_records": materialization["delta_summary"]["tie_records"],
        "delta_worse_records": materialization["delta_summary"]["worse_records"],
        "claim_rule_evaluable": materialization["claim_rule"]["evaluable"],
        "claim_rule_passed": materialization["claim_rule"]["passed"],
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "closed_loop_outcome_training_or_online_input_authorized": False,
        "recommendation": "static_review_candidate_index_actual_safetycost_delta_materialization_execution_result_only"
        if passed
        else "repair_or_rerun_same_materialization_execution_gate",
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    return decision


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / EXECUTION_JSON_NAME
    md_path = output_dir / EXECUTION_MD_NAME
    table_path = output_dir / DELTA_TABLE_JSONL_NAME
    json_path.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    table_path.write_text(
        "".join(json.dumps(_stable(row), sort_keys=True) + "\n" for row in report["paired_safetycost_v1_rows"]),
        encoding="utf-8",
    )
    (output_dir / "SHA256SUMS").write_text(
        "\n".join(f"{_sha256(path)}  {path.name}" for path in (json_path, md_path, table_path)) + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    delta = report["delta_materialization_summary"]
    summary = delta["delta_summary"]
    ci = delta["delta_bootstrap_ci95"]
    claim = delta["claim_rule"]
    return "\n".join(
        [
            "# Objective-3200 Candidate-Index Actual-SafetyCost Delta Materialization Execution",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failure class: `{decision['failure_class']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
            "## Materialization",
            "",
            f"- Candidate-index output root: `{delta['candidate_index_output_root']}`",
            f"- Selection logs: `{delta['selection_log_count']}`",
            f"- Records: `{delta['record_count']}`",
            f"- Delta rows: `{delta['paired_safetycost_v1_row_count']}`",
            f"- Shadow-selected Top-1 / non-Top-1 records: `{delta['same_as_top1_records']} / {delta['non_top1_shadow_selected_records']}`",
            f"- Actual SafetyCost_v1 available: `{delta['actual_safetycost_v1_available']}`",
            f"- Claim rule evaluable: `{delta['actual_safetycost_v1_claim_rule_evaluable']}`",
            "",
            "## Delta Summary",
            "",
            f"- Mean / median / min / max: `{summary['mean']}` / `{summary['median']}` / `{summary['min']}` / `{summary['max']}`",
            f"- Better / tie / worse: `{summary['better_records']}` / `{summary['tie_records']}` / `{summary['worse_records']}`",
            f"- CI95 low / high: `{ci['ci95_low']}` / `{ci['ci95_high']}`",
            f"- Claim rule evaluable / passed: `{claim['evaluable']}` / `{claim['passed']}`",
            "",
            "## Boundary",
            "",
            "- Evidence only: no replay, training, candidate generation, Diffusion Planner modification, promotion, deployment, online selector activation, or claim.",
            "- DP Top-1 is candidate index `0`; CAMP is `shadow_selected_index` from the same fixed DP candidate tensor record.",
            f"- Score expression remains `{report['analysis']['score_expression']}`.",
            "",
        ]
    )


def _source_static_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_review.get("final_decision"))
    return {
        "schema_version": source_review.get("schema_version"),
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "actual_safetycost_delta_materialization_execution_authorized": decision.get(
            "actual_safetycost_delta_materialization_execution_authorized"
        ),
        "actual_safetycost_v1_available": decision.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": decision.get("actual_safetycost_v1_claim_rule_evaluable"),
    }


def _candidate_execution_summary(candidate_execution: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(candidate_execution.get("final_decision"))
    candidate_summary = _dict(candidate_execution.get("candidate_index_outcome_summary"))
    strict_pairing = _dict(candidate_execution.get("strict_pairing_summary"))
    return {
        "schema_version": candidate_execution.get("schema_version"),
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "selection_log_count": candidate_summary.get("selection_log_count"),
        "record_count": candidate_summary.get("record_count"),
        "candidate_closed_loop_outcome_records": candidate_summary.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": candidate_summary.get(
            "missing_candidate_closed_loop_outcome_records"
        ),
        "paired_record_key_count": strict_pairing.get("paired_record_key_count"),
        "actual_safetycost_v1_available": decision.get("actual_safetycost_v1_available"),
        "actual_safetycost_v1_claim_rule_evaluable": decision.get("actual_safetycost_v1_claim_rule_evaluable"),
    }


def _safetycost_metric_spec(materialization: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "candidate_index_actual_safetycost_v1_metric_spec",
        "comparison": "SafetyCost_v1(CAMP shadow_selected_index) - SafetyCost_v1(DP Top-1 candidate index 0)",
        "component_formula": (
            "collision*w_collision + near_miss*w_near_miss + lane_violation*w_lane_violation + "
            "red_light_violation*w_red_light + mean_jerk_mps3*w_mean_jerk + "
            "mean_lateral_acceleration_mps2*w_mean_lateral_acceleration"
        ),
        "weights_source": "candidate_closed_loop_outcome_weights in each audited selection-log record",
        "progress_m": "reported for audit context only, not included in SafetyCost_v1",
        "unique_safetycost_v1_weight_hash_count": materialization["unique_safetycost_v1_weight_hash_count"],
        "safetycost_v1_weight_hash_preview": materialization["safetycost_v1_weight_hash_preview"],
        "claim_rule": "evaluable only after hard gates pass; passed only when ci95_high(DeltaSafetyCost_v1) < 0",
        "claim_authorized_by_this_gate": False,
    }


def _source_hashes(
    *,
    source_files: dict[str, Path],
    candidate_files: dict[str, Path],
    paths: dict[str, Path],
) -> dict[str, Any]:
    return {
        "source_static_review": {
            "artifact_root_sha256s": _sha256(source_files["root_sha256s"]),
            "json_sha256": _sha256(paths["source_preflight_static_review_json"]),
            "md_sha256": _sha256(paths["source_preflight_static_review_md"]),
            "sha256s_sha256": _sha256(paths["source_preflight_static_review_sha256s"]),
        },
        "candidate_index_execution": {
            "artifact_root_sha256s": _sha256(candidate_files["root_sha256s"]),
            "json_sha256": _sha256(paths["candidate_index_execution_json"]),
            "md_sha256": _sha256(paths["candidate_index_execution_md"]),
            "sha256s_sha256": _sha256(paths["candidate_index_execution_sha256s"]),
        },
    }


def _source_artifact_files(artifact_dir: Path) -> dict[str, Path]:
    return {
        "heads": artifact_dir / "HEADS",
        "command": artifact_dir / "COMMAND",
        "stdout": artifact_dir / "stdout",
        "stderr": artifact_dir / "stderr",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "json": artifact_dir / "review" / SOURCE_STATIC_REVIEW_JSON_NAME,
        "md": artifact_dir / "review" / SOURCE_STATIC_REVIEW_MD_NAME,
        "sha256s": artifact_dir / "review" / "SHA256SUMS",
    }


def _candidate_execution_files(artifact_dir: Path) -> dict[str, Path]:
    return {
        "heads": artifact_dir / "HEADS",
        "command": artifact_dir / "COMMAND",
        "stdout": artifact_dir / "stdout",
        "stderr": artifact_dir / "stderr",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "json": artifact_dir / "report" / CANDIDATE_EXECUTION_JSON_NAME,
        "md": artifact_dir / "report" / CANDIDATE_EXECUTION_MD_NAME,
        "sha256s": artifact_dir / "report" / "SHA256SUMS",
    }


def _candidate_output_root(candidate_execution: dict[str, Any], explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    inputs = _dict(candidate_execution.get("inputs"))
    summary = _dict(candidate_execution.get("candidate_index_outcome_summary"))
    value = inputs.get("candidate_index_output_root") or summary.get("root")
    return Path(str(value or "")).resolve()


def _sha_checks(
    *,
    prefix: str,
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    files: dict[str, Path],
    json_name: str,
    md_name: str,
    subdir: str,
) -> list[dict[str, Any]]:
    return [
        _expect(f"{prefix}_root_heads_sha", _sha_for_suffix(root_sha256s, "HEADS"), _sha256(files["heads"])),
        _expect(f"{prefix}_root_command_sha", _sha_for_suffix(root_sha256s, "COMMAND"), _sha256(files["command"])),
        _expect(f"{prefix}_root_stdout_sha", _sha_for_suffix(root_sha256s, "stdout"), _sha256(files["stdout"])),
        _expect(f"{prefix}_root_stderr_sha", _sha_for_suffix(root_sha256s, "stderr"), _sha256(files["stderr"])),
        _expect(f"{prefix}_root_run_exit_sha", _sha_for_suffix(root_sha256s, "run.exit"), _sha256(files["run_exit"])),
        _expect(f"{prefix}_root_json_sha", _sha_for_suffix(root_sha256s, f"{subdir}/{json_name}"), _sha256(files["json"])),
        _expect(f"{prefix}_root_md_sha", _sha_for_suffix(root_sha256s, f"{subdir}/{md_name}"), _sha256(files["md"])),
        _expect(
            f"{prefix}_root_nested_sha256s_sha",
            _sha_for_suffix(root_sha256s, f"{subdir}/SHA256SUMS"),
            _sha256(files["sha256s"]),
        ),
        _expect(f"{prefix}_nested_json_sha", _sha_for_suffix(nested_sha256s, json_name), _sha256(files["json"])),
        _expect(f"{prefix}_nested_md_sha", _sha_for_suffix(nested_sha256s, md_name), _sha256(files["md"])),
    ]


def _path_checks(name: str, path: Path, *, allow_empty: bool) -> list[dict[str, Any]]:
    exists = path.is_file()
    checks = [_check(f"{name}_exists", exists, str(path), "file")]
    if exists and not allow_empty:
        checks.append(_check(f"{name}_nonempty", path.stat().st_size > 0, path.stat().st_size, ">0 bytes"))
    return checks


def _drop_rows(materialization: dict[str, Any]) -> dict[str, Any]:
    dropped = dict(materialization)
    dropped.pop("paired_safetycost_v1_rows", None)
    return dropped


def _outcome_by_index(outcomes: list[Any], candidate_index: int | None) -> dict[str, Any] | None:
    if candidate_index is None:
        return None
    for outcome in outcomes:
        if isinstance(outcome, dict) and _int_or_none(outcome.get("candidate_index")) == candidate_index:
            return outcome
    if 0 <= candidate_index < len(outcomes) and isinstance(outcomes[candidate_index], dict):
        return outcomes[candidate_index]
    return None


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


def _binary_metric(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    number = _number_or_none(value)
    if number is None:
        raise ValueError("binary_or_numeric_metric_missing")
    return min(max(number, 0.0), 1.0)


def _required_number(payload: dict[str, Any], key: str) -> float:
    value = _number_or_none(payload.get(key))
    if value is None:
        raise ValueError(f"numeric_metric_missing:{key}")
    return value


def _number_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


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


def _percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("percentile requires at least one value")
    index = (len(sorted_values) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return sorted_values[int(index)]
    return sorted_values[lower] * (upper - index) + sorted_values[upper] * (index - lower)


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


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


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
