#!/usr/bin/env python3
"""Execute the v14 post-closeout paired-evaluation evidence gate.

This gate materializes strict paired evidence for CAMP shadow-selected
candidates versus DP Top-1 over an existing fixed-DP-candidate runtime artifact.
It does not run replay, generate candidates, train CAMP, modify Diffusion
Planner, promote a selector, deploy, enable the online selector, or authorize a
safety/CAMP-over-DP claim.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _load_source_static_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_STATIC_REVIEW_MODULE = _load_source_static_review_module()
BASE_MODULE = SOURCE_STATIC_REVIEW_MODULE.BASE_MODULE

FIXED_DP_HEAD = SOURCE_STATIC_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_STATIC_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_STATUS = SOURCE_STATIC_REVIEW_MODULE.READY_STATUS
SOURCE_PREFLIGHT_STATUS = SOURCE_STATIC_REVIEW_MODULE.SOURCE_PREFLIGHT_STATUS
SOURCE_PREFLIGHT_STATIC_REVIEW_JSON_NAME = SOURCE_STATIC_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_PREFLIGHT_JSON_NAME = SOURCE_STATIC_REVIEW_MODULE.PREFLIGHT_MODULE.PREFLIGHT_JSON_NAME

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_evidence_acquisition_paired_evaluation_execution_v1"
)
AUTHORIZED_CURRENT_WORK = SOURCE_STATIC_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_result_review_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_rejected"
)

EXECUTION_JSON_NAME = "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution.json"
EXECUTION_MD_NAME = "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution.md"

EXPECTED_SELECTION_LOG_COUNT = 32
EXPECTED_RECORD_COUNT = 3200
EXPECTED_RECORDS_PER_LOG = 100
EXPECTED_NUM_CANDIDATES = 8
FORMAL_SEEDS = {11, 12, 13}
FULL36_MARKERS = ("full36", "full_36", "formal36")
SIMPLEX_TOLERANCE = 1e-6
AFFINE_TOLERANCE = 1e-6
COMPARISON_TOLERANCE = 1e-12
BOOTSTRAP_RESAMPLES = 10_000

BLOCKED_ACTIONS = SOURCE_STATIC_REVIEW_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = SOURCE_STATIC_REVIEW_MODULE.FALSE_EXECUTION_FLAGS

LOWER_BETTER_METRICS = (
    "candidate_red_stopping_margin_cost",
    "candidate_full_horizon_planned_red_light_cost",
    "candidate_horizon_union_planned_red_light_cost",
    "candidate_dp_prior_deviation_cost",
    "candidate_dp_prior_jerk_excess_cost",
    "candidate_dp_prior_acceleration_excess_cost",
    "candidate_horizon_lateral_acceleration_cost",
    "candidate_dp_prior_lateral_acceleration_excess_cost",
    "candidate_horizon_yaw_rate_cost",
    "candidate_dp_prior_yaw_rate_excess_cost",
)
HIGHER_BETTER_METRICS = (
    "candidate_route_progress",
    "candidate_step_reach",
    "candidate_perfect_tracker_first_step_reach_m",
    "candidate_perfect_tracker_tail_average_speed_mps",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime_execution_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_json", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_md", type=Path, required=True)
    parser.add_argument("--source_preflight_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_json", type=Path, required=True)
    parser.add_argument("--source_preflight_md", type=Path, required=True)
    parser.add_argument("--source_preflight_sha256s", type=Path, required=True)
    parser.add_argument("--runtime_result_review_json", type=Path, required=True)
    parser.add_argument("--shadow_delta_review_json", type=Path, required=True)
    parser.add_argument("--safety_score_doc", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_selection_log_count", type=int, default=EXPECTED_SELECTION_LOG_COUNT)
    parser.add_argument("--expected_record_count", type=int, default=EXPECTED_RECORD_COUNT)
    parser.add_argument("--expected_records_per_log", type=int, default=EXPECTED_RECORDS_PER_LOG)
    parser.add_argument("--expected_num_candidates", type=int, default=EXPECTED_NUM_CANDIDATES)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runtime_execution_dir=args.runtime_execution_dir,
        source_preflight_static_review_artifact_dir=args.source_preflight_static_review_artifact_dir,
        source_preflight_static_review_json=args.source_preflight_static_review_json,
        source_preflight_static_review_md=args.source_preflight_static_review_md,
        source_preflight_static_review_sha256s=args.source_preflight_static_review_sha256s,
        source_preflight_artifact_dir=args.source_preflight_artifact_dir,
        source_preflight_json=args.source_preflight_json,
        source_preflight_md=args.source_preflight_md,
        source_preflight_sha256s=args.source_preflight_sha256s,
        runtime_result_review_json=args.runtime_result_review_json,
        shadow_delta_review_json=args.shadow_delta_review_json,
        safety_score_doc=args.safety_score_doc,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_selection_log_count=args.expected_selection_log_count,
        expected_record_count=args.expected_record_count,
        expected_records_per_log=args.expected_records_per_log,
        expected_num_candidates=args.expected_num_candidates,
        enabled=args.enable_v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runtime_execution_dir: Path,
    source_preflight_static_review_artifact_dir: Path,
    source_preflight_static_review_json: Path,
    source_preflight_static_review_md: Path,
    source_preflight_static_review_sha256s: Path,
    source_preflight_artifact_dir: Path,
    source_preflight_json: Path,
    source_preflight_md: Path,
    source_preflight_sha256s: Path,
    runtime_result_review_json: Path,
    shadow_delta_review_json: Path,
    safety_score_doc: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_selection_log_count: int = EXPECTED_SELECTION_LOG_COUNT,
    expected_record_count: int = EXPECTED_RECORD_COUNT,
    expected_records_per_log: int = EXPECTED_RECORDS_PER_LOG,
    expected_num_candidates: int = EXPECTED_NUM_CANDIDATES,
    enabled: bool = False,
) -> dict[str, Any]:
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    source_static_review = _read_json_dict(source_preflight_static_review_json)
    source_preflight = _read_json_dict(source_preflight_json)
    runtime_result_review = _read_json_dict(runtime_result_review_json)
    shadow_delta_review = _read_json_dict(shadow_delta_review_json)
    safety_text = _read_text(safety_score_doc)

    selection_logs = sorted(runtime_execution_dir.rglob("camp_selection_log.json"))
    paired = _summarize_paired_logs(
        runtime_execution_dir=runtime_execution_dir,
        selection_logs=selection_logs,
        expected_num_candidates=expected_num_candidates,
    )
    source = _source_artifact_summary(
        source_preflight_static_review_artifact_dir=source_preflight_static_review_artifact_dir,
        source_preflight_static_review_json=source_preflight_static_review_json,
        source_preflight_static_review_md=source_preflight_static_review_md,
        source_preflight_static_review_sha256s=source_preflight_static_review_sha256s,
        source_preflight_artifact_dir=source_preflight_artifact_dir,
        source_preflight_json=source_preflight_json,
        source_preflight_md=source_preflight_md,
        source_preflight_sha256s=source_preflight_sha256s,
    )
    checks = _checks(
        enabled=enabled,
        runtime_execution_dir=runtime_execution_dir,
        output_dir=output_dir,
        source_preflight_static_review_artifact_dir=source_preflight_static_review_artifact_dir,
        source_preflight_artifact_dir=source_preflight_artifact_dir,
        source_static_review=source_static_review,
        source_preflight=source_preflight,
        runtime_result_review=runtime_result_review,
        shadow_delta_review=shadow_delta_review,
        safety_score_doc=safety_score_doc,
        safety_text=safety_text,
        v14_text=v14_text,
        status_text=status_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        paired=paired,
        expected_selection_log_count=expected_selection_log_count,
        expected_record_count=expected_record_count,
        expected_records_per_log=expected_records_per_log,
    )
    passed = all(check["passed"] for check in checks)
    decision = _decision(passed=passed, checks=checks, paired=paired)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "output_dir": str(output_dir),
            "runtime_execution_dir": str(runtime_execution_dir),
            "source_preflight_static_review_artifact_dir": str(source_preflight_static_review_artifact_dir),
            "source_preflight_artifact_dir": str(source_preflight_artifact_dir),
            "read_only_existing_runtime_artifact": True,
            "paired_evaluation_execution": True,
            "replay_execution": False,
            "training_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "online_selector_change": False,
            "safety_or_camp_over_dp_claim": False,
            "score_expression": SCORE_EXPRESSION,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "source_artifacts": source,
        "paired_run_key_index": paired["paired_run_key_index"],
        "candidate_tensor_identity_table": paired["candidate_tensor_identity_table"],
        "shadow_vs_top1_metric_delta_table": paired["shadow_vs_top1_metric_delta_table"],
        "safetycost_v1_confidence_interval_table": paired["safetycost_v1_confidence_interval_table"],
        "coverage_uncertainty_bucket_table": paired["coverage_uncertainty_bucket_table"],
        "paired_execution_no_go_report": paired["paired_execution_no_go_report"],
        "paired_record_summary": paired["paired_record_summary"],
        "source_summaries": {
            "source_preflight_static_review": _source_static_review_summary(source_static_review),
            "source_preflight": _source_preflight_summary(source_preflight),
            "runtime_result_review": _runtime_result_review_summary(runtime_result_review),
            "shadow_delta_review": _shadow_delta_review_summary(shadow_delta_review),
        },
        "execution_checks": checks,
        "final_decision": decision,
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
    }


def _checks(
    *,
    enabled: bool,
    runtime_execution_dir: Path,
    output_dir: Path,
    source_preflight_static_review_artifact_dir: Path,
    source_preflight_artifact_dir: Path,
    source_static_review: dict[str, Any],
    source_preflight: dict[str, Any],
    runtime_result_review: dict[str, Any],
    shadow_delta_review: dict[str, Any],
    safety_score_doc: Path,
    safety_text: str,
    v14_text: str,
    status_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    paired: dict[str, Any],
    expected_selection_log_count: int,
    expected_record_count: int,
    expected_records_per_log: int,
) -> list[dict[str, Any]]:
    source_static_decision = _dict(source_static_review.get("final_decision"))
    source_preflight_decision = _dict(source_preflight.get("final_decision"))
    runtime_records = _dict(runtime_result_review.get("records"))
    runtime_execution = _dict(runtime_result_review.get("execution"))
    runtime_decision = _dict(runtime_result_review.get("final_decision"))
    delta_records = _dict(shadow_delta_review.get("records"))
    delta_decision = _dict(shadow_delta_review.get("final_decision"))
    record_summary = paired["paired_record_summary"]
    tensor_table = paired["candidate_tensor_identity_table"]
    score_table = paired["shadow_vs_top1_metric_delta_table"]
    run_keys = paired["paired_run_key_index"]
    safety_table = paired["safetycost_v1_confidence_interval_table"]
    no_go = paired["paired_execution_no_go_report"]

    checks: list[dict[str, Any]] = []

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

    latest_audit_status = BASE_MODULE._latest_value(v14_text, "current_v14_status")
    latest_audit_next = BASE_MODULE._latest_value(v14_text, "next_work_target")
    latest_status_doc_status = BASE_MODULE._latest_value(status_text, "current_v14_status")
    latest_status_doc_next = BASE_MODULE._latest_value(status_text, "next_work_target")

    require("execution_enabled", enabled)
    require("runtime_execution_dir_exists", runtime_execution_dir.is_dir(), str(runtime_execution_dir), "directory")
    require("source_static_review_artifact_dir_exists", source_preflight_static_review_artifact_dir.is_dir())
    require("source_preflight_artifact_dir_exists", source_preflight_artifact_dir.is_dir())
    require("safety_score_doc_exists", safety_score_doc.is_file())
    require("output_dir_parent_exists_or_creatable", output_dir.parent.exists() or output_dir.parent.parent.exists())

    expect("current_dp_head_fixed", current_dp_head, required_dp_head)
    expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main)
    expect("audit_latest_status", latest_audit_status, SOURCE_STATUS)
    expect("audit_latest_next_work", latest_audit_next, AUTHORIZED_CURRENT_WORK)
    expect("status_doc_latest_status", latest_status_doc_status, SOURCE_STATUS)
    expect("status_doc_latest_next_work", latest_status_doc_next, AUTHORIZED_CURRENT_WORK)

    expect("source_static_review_passed", source_static_decision.get("passed"), True)
    expect("source_static_review_status", source_static_decision.get("status"), SOURCE_STATUS)
    expect("source_static_review_authorized_next", source_static_decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK)
    expect("source_static_review_authorizes_execution", source_static_decision.get("paired_evaluation_execution_authorized"), True)
    expect("source_static_review_no_execution", source_static_decision.get("paired_evaluation_executed_by_this_gate"), False)
    for action in BLOCKED_ACTIONS:
        expect(f"source_static_review_decision_{action}", source_static_decision.get(action), False)

    expect("source_preflight_passed", source_preflight_decision.get("passed"), True)
    expect("source_preflight_status", source_preflight_decision.get("status"), SOURCE_PREFLIGHT_STATUS)
    expect("source_preflight_no_execution", source_preflight_decision.get("paired_evaluation_executed_by_this_gate"), False)
    for action in BLOCKED_ACTIONS:
        expect(f"source_preflight_decision_{action}", source_preflight_decision.get(action), False)

    expect("runtime_result_review_passed", runtime_decision.get("passed"), True)
    expect("runtime_result_record_count", runtime_records.get("record_count"), expected_record_count)
    expect("runtime_result_executed_top1_records", runtime_records.get("executed_top1_records"), expected_record_count)
    expect("runtime_result_selection_log_count", runtime_execution.get("selection_log_count"), expected_selection_log_count)
    expect("shadow_delta_review_passed", delta_decision.get("passed"), True)
    expect("shadow_delta_static_objective_supported", delta_decision.get("static_objective_delta_supported"), True)
    expect("shadow_delta_record_count", delta_records.get("record_count"), expected_record_count)

    require("safety_score_doc_has_safetycost", "SafetyCost_v1" in safety_text, "SafetyCost_v1", "present")
    require(
        "safety_score_doc_has_claim_rule",
        "ci95_high(DeltaSafetyCost_v1) < 0" in safety_text,
        "ci95_high(DeltaSafetyCost_v1) < 0",
        "present",
    )

    expect("selection_log_count", record_summary["selection_log_count"], expected_selection_log_count)
    expect("record_count", record_summary["record_count"], expected_record_count)
    expect("records_per_log_min", record_summary["records_per_log_min"], expected_records_per_log)
    expect("records_per_log_max", record_summary["records_per_log_max"], expected_records_per_log)
    expect("paired_run_key_unique_records", run_keys["unique_paired_run_key_count"], expected_record_count)
    expect("paired_run_key_duplicate_records", run_keys["duplicate_paired_run_key_count"], 0)
    expect("executed_top1_records", record_summary["executed_top1_records"], expected_record_count)
    expect("selected_matches_executed_records", record_summary["selected_matches_executed_records"], expected_record_count)
    expect("default_off_selector_records", record_summary["default_off_selector_records"], expected_record_count)
    expect("selector_contract_ready_records", record_summary["selector_contract_ready_records"], expected_record_count)
    expect("score_expression_records", record_summary["score_expression_records"], expected_record_count)
    expect("candidate_operation_records", record_summary["candidate_operation_records"], expected_record_count)
    expect("candidate_count_bad_records", record_summary["candidate_count_bad_records"], 0)
    expect("formal_seed_records", record_summary["formal_seed_records"], 0)
    expect("full36_path_records", record_summary["full36_path_records"], 0)
    expect("candidate_tensor_identity_records", tensor_table["identity_match_records"], expected_record_count)
    expect("candidate_tensor_mutation_records", tensor_table["candidate_tensor_mutation_records"], 0)
    expect("reference_blend_records", tensor_table["reference_blend_records"], 0)
    expect("closed_loop_outcome_input_records", tensor_table["closed_loop_outcome_input_records"], 0)
    expect("closed_loop_outcome_fields_read_records", tensor_table["closed_loop_outcome_fields_read_records"], 0)
    expect("dp_modification_authorized_records", tensor_table["dp_modification_authorized_records"], 0)
    expect("candidate_generation_authorized_records", tensor_table["candidate_generation_authorized_records"], 0)
    expect("non_affine_score_records", record_summary["non_affine_score_records"], 0)
    expect("non_simplex_weight_records", record_summary["non_simplex_weight_records"], 0)
    expect("negative_weight_records", record_summary["negative_weight_records"], 0)
    expect("selection_score_uncomparable_records", score_table["selection_score_delta"]["uncomparable_records"], 0)
    expect("selection_score_worse_records", score_table["selection_score_delta"]["worse_records"], 0)
    require("static_objective_delta_supported", score_table["selection_score_delta"]["better_records"] > 0)
    expect("actual_safetycost_v1_claim_not_evaluable", safety_table["actual_safetycost_v1_claim_rule_evaluable"], False)
    expect("safetycost_v1_claim_authorized_by_execution", safety_table["safetycost_v1_claim_authorized"], False)
    expect("no_go_failed_count", no_go["failed_count"], 0)
    return checks


def _summarize_paired_logs(
    *,
    runtime_execution_dir: Path,
    selection_logs: list[Path],
    expected_num_candidates: int,
) -> dict[str, Any]:
    counters: Counter[str] = Counter()
    per_log_counts: list[int] = []
    selected_indices: Counter[str] = Counter()
    shadow_indices: Counter[str] = Counter()
    executed_indices: Counter[str] = Counter()
    seeds: Counter[str] = Counter()
    scenarios: Counter[str] = Counter()
    tl_modes: Counter[str] = Counter()
    feasible_pairs: Counter[str] = Counter()
    tensor_hashes: Counter[str] = Counter()
    tensor_shapes: Counter[str] = Counter()
    atom_names_seen: Counter[str] = Counter()
    paired_keys: list[str] = []
    paired_key_seen: set[str] = set()
    duplicate_keys = 0
    selection_score = _new_comparison_summary()
    raw_score = _new_comparison_summary()
    metric_deltas: dict[str, dict[str, Any]] = {
        name: _new_metric_summary("lower") for name in LOWER_BETTER_METRICS
    }
    metric_deltas.update({name: _new_metric_summary("higher") for name in HIGHER_BETTER_METRICS})
    normalized_atom_deltas: defaultdict[str, list[float]] = defaultdict(list)
    latency_ms: list[float] = []
    margin_values: list[float] = []
    safety_proxy_deltas: list[float] = []

    for log in selection_logs:
        rows = _records_from_payload(_read_json(log))
        per_log_counts.append(len(rows))
        log_key = _log_key(runtime_execution_dir, log)
        for row in rows:
            counters["record_count"] += 1
            step = _int_or_none(row.get("selection_step"))
            seed = log_key.get("seed")
            scenario = log_key.get("scenario") or "unknown"
            tl_mode = log_key.get("tl_mode") or "unknown"
            pair_key = f"{scenario}|seed_{seed}|{tl_mode}|step_{step}"
            paired_keys.append(pair_key)
            if pair_key in paired_key_seen:
                duplicate_keys += 1
            paired_key_seen.add(pair_key)
            scenarios[scenario] += 1
            seeds[str(seed)] += 1
            tl_modes[tl_mode] += 1
            if seed in FORMAL_SEEDS:
                counters["formal_seed_records"] += 1
            if _path_has_any_marker(log, FULL36_MARKERS):
                counters["full36_path_records"] += 1

            selector = _dict(row.get("default_off_shadow_selector"))
            provenance = _dict(row.get("camp_candidate_tensor_provenance"))
            selected = _int_or_none(row.get("selected_index"))
            executed = _int_or_none(row.get("executed_index"))
            shadow = _int_or_none(selector.get("shadow_selected_index"))
            if shadow is None:
                shadow = _int_or_none(row.get("shadow_selected_index"))
            selected_indices[str(selected)] += 1
            shadow_indices[str(shadow)] += 1
            executed_indices[str(executed)] += 1
            if selected == executed:
                counters["selected_matches_executed_records"] += 1
            if executed == 0:
                counters["executed_top1_records"] += 1
            if shadow not in (None, 0):
                counters["shadow_selected_index_nonzero_records"] += 1
            if shadow != executed:
                counters["shadow_selected_index_differs_from_executed_index_records"] += 1

            if _selector_contract_ready(selector):
                counters["default_off_selector_records"] += 1
            if selector.get("artifact_contract_ready") is True:
                counters["selector_contract_ready_records"] += 1
            if selector.get("score_expression") == SCORE_EXPRESSION:
                counters["score_expression_records"] += 1
            if selector.get("candidate_operation") == "fixed DP candidate reranking only":
                counters["candidate_operation_records"] += 1
            if row.get("num_candidates") != expected_num_candidates:
                counters["candidate_count_bad_records"] += 1

            _record_tensor_identity(row, selector, provenance, tensor_hashes, tensor_shapes, counters)
            _record_affine_boundary(row, counters, expected_num_candidates)

            feasible = row.get("feasible_mask")
            if (
                isinstance(feasible, list)
                and executed is not None
                and shadow is not None
                and len(feasible) > max(executed, shadow)
            ):
                feasible_pairs[f"top1_{bool(feasible[executed])}_shadow_{bool(feasible[shadow])}"] += 1

            _add_comparison(selection_score, row.get("selection_scores"), challenger_index=shadow, baseline_index=executed)
            _add_comparison(raw_score, row.get("scores"), challenger_index=shadow, baseline_index=executed)
            _record_metric_deltas(row, shadow, executed, metric_deltas)
            _record_atom_deltas(row, shadow, executed, normalized_atom_deltas, atom_names_seen)
            _record_safety_proxy_delta(row, shadow, executed, safety_proxy_deltas)

            latency = _number_or_none(row.get("latency_ms_camp_selection"))
            if latency is not None:
                latency_ms.append(latency)
            scores = row.get("selection_scores")
            if (
                isinstance(scores, list)
                and executed is not None
                and shadow is not None
                and len(scores) > max(executed, shadow)
            ):
                top1_score = _number_or_none(scores[executed])
                shadow_score = _number_or_none(scores[shadow])
                if top1_score is not None and shadow_score is not None:
                    margin_values.append(top1_score - shadow_score)

    ordered_keys = sorted(paired_keys)
    key_digest = hashlib.sha256("\n".join(ordered_keys).encode("utf-8")).hexdigest()
    selection_score_final = _finalize_comparison(selection_score)
    raw_score_final = _finalize_comparison(raw_score)
    finalized_metrics = {
        name: _finalize_metric_summary(summary) for name, summary in sorted(metric_deltas.items())
    }
    atom_delta_summaries = {
        name: _summarize_deltas(values) for name, values in sorted(normalized_atom_deltas.items())
    }
    safety_table = _safetycost_table(
        record_count=counters["record_count"],
        candidate_closed_loop_outcome_records=counters["candidate_closed_loop_outcome_records"],
        safety_proxy_deltas=safety_proxy_deltas,
        latency_ms=latency_ms,
    )
    no_go = _no_go_report(counters, total_records=counters["record_count"])
    return {
        "paired_run_key_index": {
            "paired_run_key_count": len(paired_keys),
            "unique_paired_run_key_count": len(paired_key_seen),
            "duplicate_paired_run_key_count": duplicate_keys,
            "paired_run_key_sha256": key_digest,
            "paired_run_key_components": ["scenario", "seed", "traffic_light_mode", "selection_step"],
            "preview": ordered_keys[:10],
        },
        "candidate_tensor_identity_table": {
            "identity_match_records": counters["candidate_tensor_identity_records"],
            "candidate_tensor_mutation_records": counters["candidate_tensor_mutation_records"],
            "reference_blend_records": counters["reference_blend_records"],
            "closed_loop_outcome_input_records": counters["closed_loop_outcome_input_records"],
            "closed_loop_outcome_fields_read_records": counters["closed_loop_outcome_fields_read_records"],
            "dp_modification_authorized_records": counters["dp_modification_authorized_records"],
            "candidate_generation_authorized_records": counters["candidate_generation_authorized_records"],
            "unique_candidate_tensor_hash_count": len(tensor_hashes),
            "candidate_tensor_hash_preview": sorted(tensor_hashes)[:10],
            "candidate_tensor_shape_counts": dict(sorted(tensor_shapes.items())),
        },
        "shadow_vs_top1_metric_delta_table": {
            "selection_score_delta": selection_score_final,
            "raw_affine_score_delta": raw_score_final,
            "candidate_metric_deltas": finalized_metrics,
            "normalized_atom_delta_summaries": atom_delta_summaries,
        },
        "safetycost_v1_confidence_interval_table": safety_table,
        "coverage_uncertainty_bucket_table": {
            "scenario_record_counts": dict(sorted(scenarios.items())),
            "seed_record_counts": dict(sorted(seeds.items())),
            "traffic_light_mode_record_counts": dict(sorted(tl_modes.items())),
            "selected_index_counts": dict(sorted(selected_indices.items())),
            "executed_index_counts": dict(sorted(executed_indices.items())),
            "shadow_selected_index_counts": dict(sorted(shadow_indices.items())),
            "feasible_pair_counts": dict(sorted(feasible_pairs.items())),
            "fallback_rate": _ratio(counters["fallback_records"], counters["record_count"]),
            "uncertainty_source": "selection_score_margin_proxy",
            "uncertainty_source_is_closed_loop_outcome": False,
            "selection_margin_proxy_summary": _summarize_deltas(margin_values),
            "selection_latency_ms_summary": _summarize_deltas(latency_ms),
            "atom_names": sorted(atom_names_seen),
        },
        "paired_execution_no_go_report": no_go,
        "paired_record_summary": {
            "selection_log_count": len(selection_logs),
            "record_count": counters["record_count"],
            "records_per_log_min": min(per_log_counts) if per_log_counts else 0,
            "records_per_log_max": max(per_log_counts) if per_log_counts else 0,
            "executed_top1_records": counters["executed_top1_records"],
            "selected_matches_executed_records": counters["selected_matches_executed_records"],
            "shadow_selected_index_nonzero_records": counters["shadow_selected_index_nonzero_records"],
            "shadow_selected_index_differs_from_executed_index_records": counters[
                "shadow_selected_index_differs_from_executed_index_records"
            ],
            "default_off_selector_records": counters["default_off_selector_records"],
            "selector_contract_ready_records": counters["selector_contract_ready_records"],
            "score_expression_records": counters["score_expression_records"],
            "candidate_operation_records": counters["candidate_operation_records"],
            "candidate_count_bad_records": counters["candidate_count_bad_records"],
            "formal_seed_records": counters["formal_seed_records"],
            "full36_path_records": counters["full36_path_records"],
            "non_affine_score_records": counters["non_affine_score_records"],
            "non_simplex_weight_records": counters["non_simplex_weight_records"],
            "negative_weight_records": counters["negative_weight_records"],
            "fallback_records": counters["fallback_records"],
        },
    }


def _record_tensor_identity(
    row: dict[str, Any],
    selector: dict[str, Any],
    provenance: dict[str, Any],
    tensor_hashes: Counter[str],
    tensor_shapes: Counter[str],
    counters: Counter[str],
) -> None:
    selector_hash = _dict(selector.get("candidate_tensor_hash"))
    pre_hash = _dict(provenance.get("pre_camp_scoring_tensor"))
    post_hash = _dict(provenance.get("post_camp_selector_tensor"))
    hashes = [selector_hash.get("sha256"), pre_hash.get("sha256"), post_hash.get("sha256")]
    if all(isinstance(value, str) and value for value in hashes) and len(set(hashes)) == 1:
        counters["candidate_tensor_identity_records"] += 1
        tensor_hashes[hashes[0]] += 1
    else:
        counters["candidate_tensor_mutation_records"] += 1
    shape = selector_hash.get("shape") or pre_hash.get("shape") or post_hash.get("shape")
    dtype = selector_hash.get("dtype") or pre_hash.get("dtype") or post_hash.get("dtype")
    tensor_shapes[f"{dtype}:{shape}"] += 1
    if provenance.get("candidate_tensor_mutation_effect") is True or provenance.get("pre_post_tensor_hash_equal") is False:
        counters["candidate_tensor_mutation_records"] += 1
    if provenance.get("reference_blend_present") is True or row.get("candidate_reference_blend_steps") not in (0, None):
        counters["reference_blend_records"] += 1
    if provenance.get("outcome_label_input") is True:
        counters["closed_loop_outcome_input_records"] += 1
    if provenance.get("closed_loop_outcome_fields_read") is True:
        counters["closed_loop_outcome_fields_read_records"] += 1
    if provenance.get("dp_modification_authorized") is True:
        counters["dp_modification_authorized_records"] += 1
    if provenance.get("candidate_generation_authorized") is True:
        counters["candidate_generation_authorized_records"] += 1
    closed_loop = row.get("candidate_closed_loop_outcomes")
    if isinstance(closed_loop, list) and closed_loop:
        counters["candidate_closed_loop_outcome_records"] += 1
    if row.get("used_fallback") is True:
        counters["fallback_records"] += 1


def _record_affine_boundary(row: dict[str, Any], counters: Counter[str], expected_num_candidates: int) -> None:
    weights = row.get("selection_weights", row.get("weights"))
    atoms = row.get("selection_normalized_atoms", row.get("normalized_atoms"))
    scores = row.get("selection_scores", row.get("scores"))
    if not isinstance(weights, list) or not weights:
        counters["non_simplex_weight_records"] += 1
        counters["non_affine_score_records"] += 1
        return
    numeric_weights = [_number_or_none(value) for value in weights]
    if any(value is None for value in numeric_weights):
        counters["non_simplex_weight_records"] += 1
        counters["non_affine_score_records"] += 1
        return
    weights_float = [float(value) for value in numeric_weights if value is not None]
    if any(weight < -SIMPLEX_TOLERANCE for weight in weights_float):
        counters["negative_weight_records"] += 1
    if abs(sum(weights_float) - 1.0) > SIMPLEX_TOLERANCE:
        counters["non_simplex_weight_records"] += 1
    if not isinstance(atoms, list) or not isinstance(scores, list) or len(atoms) < expected_num_candidates:
        counters["non_affine_score_records"] += 1
        return
    for candidate_index in range(expected_num_candidates):
        atom_row = atoms[candidate_index] if candidate_index < len(atoms) else None
        score = _number_or_none(scores[candidate_index] if candidate_index < len(scores) else None)
        if not isinstance(atom_row, list) or score is None or len(atom_row) < len(weights_float):
            counters["non_affine_score_records"] += 1
            return
        atom_values = [_number_or_none(value) for value in atom_row[: len(weights_float)]]
        if any(value is None for value in atom_values):
            counters["non_affine_score_records"] += 1
            return
        predicted = sum(float(a) * weight for a, weight in zip(atom_values, weights_float))
        if abs(predicted - score) > AFFINE_TOLERANCE:
            counters["non_affine_score_records"] += 1
            return


def _record_metric_deltas(
    row: dict[str, Any],
    shadow: int | None,
    executed: int | None,
    metric_deltas: dict[str, dict[str, Any]],
) -> None:
    for name in LOWER_BETTER_METRICS:
        _add_metric_delta(metric_deltas[name], row.get(name), shadow, executed)
    for name in HIGHER_BETTER_METRICS:
        _add_metric_delta(metric_deltas[name], row.get(name), shadow, executed)


def _record_atom_deltas(
    row: dict[str, Any],
    shadow: int | None,
    executed: int | None,
    normalized_atom_deltas: defaultdict[str, list[float]],
    atom_names_seen: Counter[str],
) -> None:
    atom_names = row.get("atom_names")
    atoms = row.get("selection_normalized_atoms", row.get("normalized_atoms"))
    if not isinstance(atom_names, list):
        return
    for name in atom_names:
        atom_names_seen[str(name)] += 1
    if not (
        isinstance(atoms, list)
        and executed is not None
        and shadow is not None
        and len(atoms) > max(executed, shadow)
        and isinstance(atoms[executed], list)
        and isinstance(atoms[shadow], list)
    ):
        return
    for index, name in enumerate(atom_names):
        baseline = _number_or_none(atoms[executed][index] if index < len(atoms[executed]) else None)
        challenger = _number_or_none(atoms[shadow][index] if index < len(atoms[shadow]) else None)
        if baseline is not None and challenger is not None:
            normalized_atom_deltas[str(name)].append(challenger - baseline)


def _record_safety_proxy_delta(
    row: dict[str, Any],
    shadow: int | None,
    executed: int | None,
    safety_proxy_deltas: list[float],
) -> None:
    top1 = _candidate_safety_proxy(row, executed)
    challenger = _candidate_safety_proxy(row, shadow)
    if top1 is not None and challenger is not None:
        safety_proxy_deltas.append(challenger - top1)


def _candidate_safety_proxy(row: dict[str, Any], index: int | None) -> float | None:
    if index is None:
        return None
    planned_red = _candidate_number(row, "candidate_full_horizon_planned_red_light_cost", index)
    jerk = _candidate_number(row, "candidate_perfect_tracker_jerk_magnitude_mps3", index)
    lateral = _candidate_number(row, "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2", index)
    progress_values = row.get("candidate_route_progress")
    progress = _candidate_number(row, "candidate_route_progress", index)
    if planned_red is None or jerk is None or lateral is None or progress is None or not isinstance(progress_values, list):
        return None
    numeric_progress = [value for value in (_number_or_none(item) for item in progress_values) if value is not None]
    if not numeric_progress:
        return None
    route_shortfall = max(numeric_progress) - progress
    return (
        15.0 * _clip(planned_red, 0.0, 1.0)
        + 1.0 * _clip(jerk / 10.0, 0.0, 10.0)
        + 2.0 * _clip(lateral / 2.0, 0.0, 10.0)
        + 2.0 * _clip(route_shortfall, 0.0, 1.0)
    )


def _safetycost_table(
    *,
    record_count: int,
    candidate_closed_loop_outcome_records: int,
    safety_proxy_deltas: list[float],
    latency_ms: list[float],
) -> dict[str, Any]:
    actual_available = candidate_closed_loop_outcome_records == record_count and record_count > 0
    proxy_ci = _bootstrap_ci(safety_proxy_deltas)
    latency_summary = _summarize_deltas(latency_ms)
    return {
        "SafetyCost_v1_contract": "run-level replay outcome score; lower is better",
        "DeltaSafetyCost_v1_claim_rule": "ci95_high(DeltaSafetyCost_v1) < 0",
        "actual_safetycost_v1_available": actual_available,
        "actual_safetycost_v1_claim_rule_evaluable": False,
        "candidate_closed_loop_outcome_records": candidate_closed_loop_outcome_records,
        "record_count": record_count,
        "unavailable_reason": (
            None
            if actual_available
            else "locked runtime selection logs do not contain shadow-selected run-level closed-loop outcomes"
        ),
        "candidate_branch_planned_proxy": {
            "is_actual_SafetyCost_v1": False,
            "claim_authorized_from_proxy": False,
            "finite_delta_count": len(safety_proxy_deltas),
            "delta_summary": _summarize_deltas(safety_proxy_deltas),
            "deterministic_bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "delta_mean_ci95": proxy_ci,
        },
        "hard_gate_summary": {
            "hard_gate_passed": False,
            "reason": "formal SafetyCost_v1 hard gates require actual paired closed-loop outcome summaries",
            "latency_selection_ms_summary": latency_summary,
            "latency_p95_selection_ms": _percentile(latency_ms, 0.95),
            "latency_p95_threshold_ms": 95.0,
        },
        "safetycost_v1_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _no_go_report(counters: Counter[str], *, total_records: int) -> dict[str, Any]:
    entries = [
        ("fixed_dp_candidate_tensor_identity", counters["candidate_tensor_mutation_records"] == 0),
        ("no_reference_blend_guidance_or_postselection_effect", counters["reference_blend_records"] == 0),
        ("no_closed_loop_outcome_training_or_online_input", counters["closed_loop_outcome_input_records"] == 0),
        ("no_closed_loop_outcome_fields_read_by_selector", counters["closed_loop_outcome_fields_read_records"] == 0),
        ("no_formal_seed_11_12_13", counters["formal_seed_records"] == 0),
        ("no_full36", counters["full36_path_records"] == 0),
        ("affine_score_boundary", counters["non_affine_score_records"] == 0),
        ("nonnegative_simplex_weight_boundary", counters["non_simplex_weight_records"] == 0 and counters["negative_weight_records"] == 0),
        ("no_dp_modification", counters["dp_modification_authorized_records"] == 0),
        ("no_camp_candidate_generation_authorized", counters["candidate_generation_authorized_records"] == 0),
        ("paired_records_present", total_records > 0),
    ]
    rows = [{"name": name, "passed": bool(passed)} for name, passed in entries]
    return {
        "entries": rows,
        "failed_count": sum(1 for row in rows if not row["passed"]),
        "promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], paired: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "execution_enabled" in failed:
        failure_class = "explicit_paired_evaluation_execution_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_") for name in failed):
        failure_class = "source_execution_preflight_static_review_contract_failure"
    elif any(name.startswith(("runtime_", "shadow_delta_")) for name in failed):
        failure_class = "locked_source_evidence_contract_failure"
    elif any(name.startswith(("candidate_tensor_", "closed_loop_", "reference_blend")) for name in failed):
        failure_class = "fixed_candidate_tensor_boundary_failure"
    elif any(name.startswith(("non_", "selection_score_", "static_objective")) for name in failed):
        failure_class = "paired_static_objective_contract_failure"
    else:
        failure_class = "paired_evaluation_execution_contract_failure"
    decision: dict[str, Any] = {
        "passed": passed,
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_passed": passed,
        "paired_evaluation_executed_by_this_gate": True,
        "paired_evaluation_execution_authorized": bool(passed),
        "paired_record_count": paired["paired_record_summary"]["record_count"],
        "paired_run_key_count": paired["paired_run_key_index"]["paired_run_key_count"],
        "actual_safetycost_v1_available": paired["safetycost_v1_confidence_interval_table"][
            "actual_safetycost_v1_available"
        ],
        "actual_safetycost_v1_claim_rule_evaluable": paired["safetycost_v1_confidence_interval_table"][
            "actual_safetycost_v1_claim_rule_evaluable"
        ],
        "safetycost_v1_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "previous_no_promotion_closeout_preserved": True,
        "direct_promotion_recommendation": False,
        "recommendation": "result_review_paired_evaluation_execution_only" if passed else "repair_or_rerun_same_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def _source_artifact_summary(
    *,
    source_preflight_static_review_artifact_dir: Path,
    source_preflight_static_review_json: Path,
    source_preflight_static_review_md: Path,
    source_preflight_static_review_sha256s: Path,
    source_preflight_artifact_dir: Path,
    source_preflight_json: Path,
    source_preflight_md: Path,
    source_preflight_sha256s: Path,
) -> dict[str, Any]:
    return {
        "source_preflight_static_review": _artifact_hashes(
            source_preflight_static_review_artifact_dir,
            {
                "json": source_preflight_static_review_json,
                "md": source_preflight_static_review_md,
                "sha256s": source_preflight_static_review_sha256s,
            },
        ),
        "source_preflight": _artifact_hashes(
            source_preflight_artifact_dir,
            {
                "json": source_preflight_json,
                "md": source_preflight_md,
                "sha256s": source_preflight_sha256s,
            },
        ),
    }


def _artifact_hashes(root: Path, paths: dict[str, Path]) -> dict[str, Any]:
    root_sha = root / "SHA256SUMS"
    result = {"artifact_dir": str(root), "root_sha256s": str(root_sha), "root_sha256s_sha256": None}
    if root_sha.is_file():
        result["root_sha256s_sha256"] = _sha256(root_sha)
    for name, path in paths.items():
        result[f"{name}_path"] = str(path)
        result[f"{name}_sha256"] = _sha256(path) if path.is_file() else None
    return result


def _source_static_review_summary(source_static_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_static_review.get("final_decision"))
    return {
        "schema_version": source_static_review.get("schema_version"),
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "paired_evaluation_execution_authorized": decision.get("paired_evaluation_execution_authorized"),
    }


def _source_preflight_summary(source_preflight: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_preflight.get("final_decision"))
    return {
        "schema_version": source_preflight.get("schema_version"),
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "future_output_count": len(_list(source_preflight.get("future_outputs"))),
        "required_input_manifest_count": len(_list(source_preflight.get("required_input_manifests"))),
    }


def _runtime_result_review_summary(runtime_result_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(runtime_result_review.get("final_decision"))
    records = _dict(runtime_result_review.get("records"))
    execution = _dict(runtime_result_review.get("execution"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "record_count": records.get("record_count"),
        "executed_top1_records": records.get("executed_top1_records"),
        "selection_log_count": execution.get("selection_log_count"),
    }


def _shadow_delta_review_summary(shadow_delta_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(shadow_delta_review.get("final_decision"))
    records = _dict(shadow_delta_review.get("records"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "static_objective_delta_supported": decision.get("static_objective_delta_supported"),
        "record_count": records.get("record_count"),
    }


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
    records = report["paired_record_summary"]
    selection = report["shadow_vs_top1_metric_delta_table"]["selection_score_delta"]
    safety = report["safetycost_v1_confidence_interval_table"]
    no_go = report["paired_execution_no_go_report"]
    lines = [
        "# v14 Post-Closeout Paired Evaluation Execution",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Paired records: `{records['record_count']}`",
        f"- Paired run-key SHA256: `{report['paired_run_key_index']['paired_run_key_sha256']}`",
        "",
        "## Scope",
        "",
        "- Evidence only: no replay, training, candidate generation, DP modification, promotion, deployment, or online selector activation.",
        "- CAMP remains default-off and only shadow-selects from the fixed DP candidate tensor.",
        "- The executed output remains DP Top-1.",
        "- Safety/CAMP-over-DP claims remain unauthorized.",
        "",
        "## Paired Counts",
        "",
        f"- Selection logs: `{records['selection_log_count']}`",
        f"- Executed DP Top-1 records: `{records['executed_top1_records']}`",
        f"- Shadow differs from executed records: `{records['shadow_selected_index_differs_from_executed_index_records']}`",
        f"- Formal seed records: `{records['formal_seed_records']}`",
        f"- Full36 path records: `{records['full36_path_records']}`",
        "",
        "## Static Objective Delta",
        "",
        f"- Better records: `{selection['better_records']}`",
        f"- Worse records: `{selection['worse_records']}`",
        f"- Tie records: `{selection['tie_records']}`",
        f"- Mean delta: `{selection['finite_delta_mean']}`",
        "",
        "## SafetyCost v1",
        "",
        f"- Actual SafetyCost v1 available: `{safety['actual_safetycost_v1_available']}`",
        f"- Claim rule evaluable: `{safety['actual_safetycost_v1_claim_rule_evaluable']}`",
        f"- Unavailable reason: `{safety['unavailable_reason']}`",
        f"- SafetyCost v1 claim authorized: `{safety['safetycost_v1_claim_authorized']}`",
        "",
        "## No-Go Report",
        "",
        f"- Failed no-go checks: `{no_go['failed_count']}`",
        f"- Promotion authorized: `{no_go['promotion_authorized']}`",
        f"- Deployment authorized: `{no_go['deployment_authorized']}`",
        f"- Online selector change authorized: `{no_go['online_selector_change_authorized']}`",
    ]
    return "\n".join(lines) + "\n"


def _selector_contract_ready(selector: dict[str, Any]) -> bool:
    return (
        selector.get("schema_version") == "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1"
        and selector.get("enabled") is True
        and selector.get("default_off") is True
        and selector.get("source_scope") == "public_simulator_fixed_dp_candidate_tensor"
        and selector.get("selection_effect") is False
        and selector.get("online_selector_change") is False
        and selector.get("candidate_operation") == "fixed DP candidate reranking only"
        and selector.get("score_expression") == SCORE_EXPRESSION
        and selector.get("executed_output_policy") == "dp_top1"
    )


def _new_comparison_summary() -> dict[str, Any]:
    return {
        "records": 0,
        "better_records": 0,
        "worse_records": 0,
        "tie_records": 0,
        "uncomparable_records": 0,
        "finite_deltas": [],
    }


def _add_comparison(
    summary: dict[str, Any],
    values: Any,
    *,
    challenger_index: int | None,
    baseline_index: int | None,
) -> None:
    summary["records"] += 1
    outcome, delta = _compare_lower(values, challenger_index, baseline_index)
    if outcome == "better":
        summary["better_records"] += 1
    elif outcome == "worse":
        summary["worse_records"] += 1
    elif outcome == "tie":
        summary["tie_records"] += 1
    else:
        summary["uncomparable_records"] += 1
    if delta is not None:
        summary["finite_deltas"].append(delta)


def _compare_lower(values: Any, challenger_index: int | None, baseline_index: int | None) -> tuple[str, float | None]:
    if not isinstance(values, list) or challenger_index is None or baseline_index is None:
        return "uncomparable", None
    if challenger_index < 0 or baseline_index < 0 or len(values) <= max(challenger_index, baseline_index):
        return "uncomparable", None
    challenger = _number_or_none(values[challenger_index])
    baseline = _number_or_none(values[baseline_index])
    if challenger is None or baseline is None:
        return "uncomparable", None
    delta = challenger - baseline
    if delta < -COMPARISON_TOLERANCE:
        return "better", delta
    if delta > COMPARISON_TOLERANCE:
        return "worse", delta
    return "tie", delta


def _finalize_comparison(summary: dict[str, Any]) -> dict[str, Any]:
    deltas = list(summary.pop("finite_deltas"))
    finalized = dict(summary)
    finalized.update(_summarize_deltas(deltas))
    return finalized


def _new_metric_summary(direction: str) -> dict[str, Any]:
    return {
        "direction": direction,
        "records": 0,
        "improved_records": 0,
        "worse_records": 0,
        "tie_records": 0,
        "uncomparable_records": 0,
        "deltas": [],
    }


def _add_metric_delta(summary: dict[str, Any], values: Any, shadow: int | None, executed: int | None) -> None:
    summary["records"] += 1
    if not isinstance(values, list) or shadow is None or executed is None or shadow < 0 or executed < 0:
        summary["uncomparable_records"] += 1
        return
    if len(values) <= max(shadow, executed):
        summary["uncomparable_records"] += 1
        return
    baseline = _number_or_none(values[executed])
    challenger = _number_or_none(values[shadow])
    if baseline is None or challenger is None:
        summary["uncomparable_records"] += 1
        return
    delta = challenger - baseline
    summary["deltas"].append(delta)
    if abs(delta) <= COMPARISON_TOLERANCE:
        summary["tie_records"] += 1
    elif (summary["direction"] == "lower" and delta < 0) or (summary["direction"] == "higher" and delta > 0):
        summary["improved_records"] += 1
    else:
        summary["worse_records"] += 1


def _finalize_metric_summary(summary: dict[str, Any]) -> dict[str, Any]:
    deltas = list(summary.pop("deltas"))
    finalized = dict(summary)
    finalized.update(_summarize_deltas(deltas))
    return finalized


def _summarize_deltas(deltas: list[float]) -> dict[str, Any]:
    if not deltas:
        return {
            "finite_delta_count": 0,
            "finite_delta_mean": None,
            "finite_delta_median": None,
            "finite_delta_min": None,
            "finite_delta_max": None,
            "finite_delta_ci95_low_normal": None,
            "finite_delta_ci95_high_normal": None,
            "finite_delta_lower_better_wins": 0,
            "finite_delta_lower_better_losses": 0,
            "finite_delta_ties": 0,
        }
    mean = sum(deltas) / len(deltas)
    stdev = statistics.pstdev(deltas) if len(deltas) > 1 else 0.0
    half_width = 1.96 * stdev / math.sqrt(len(deltas)) if len(deltas) > 1 else 0.0
    wins = sum(1 for delta in deltas if delta < -COMPARISON_TOLERANCE)
    losses = sum(1 for delta in deltas if delta > COMPARISON_TOLERANCE)
    ties = len(deltas) - wins - losses
    return {
        "finite_delta_count": len(deltas),
        "finite_delta_mean": mean,
        "finite_delta_median": statistics.median(deltas),
        "finite_delta_min": min(deltas),
        "finite_delta_max": max(deltas),
        "finite_delta_ci95_low_normal": mean - half_width,
        "finite_delta_ci95_high_normal": mean + half_width,
        "finite_delta_lower_better_wins": wins,
        "finite_delta_lower_better_losses": losses,
        "finite_delta_ties": ties,
    }


def _bootstrap_ci(deltas: list[float]) -> dict[str, Any]:
    if not deltas:
        return {"mean": None, "ci95_low": None, "ci95_high": None}
    rng = random.Random(20260705)
    n = len(deltas)
    means = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        total = 0.0
        for _ in range(n):
            total += deltas[rng.randrange(n)]
        means.append(total / n)
    means.sort()
    low_index = max(0, int(0.025 * BOOTSTRAP_RESAMPLES) - 1)
    high_index = min(BOOTSTRAP_RESAMPLES - 1, int(0.975 * BOOTSTRAP_RESAMPLES) - 1)
    return {
        "mean": sum(deltas) / n,
        "ci95_low": means[low_index],
        "ci95_high": means[high_index],
    }


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = int(math.ceil(q * len(ordered))) - 1
    index = max(0, min(index, len(ordered) - 1))
    return ordered[index]


def _records_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return [item for item in payload["records"] if isinstance(item, dict)]
    return []


def _log_key(root: Path, log: Path) -> dict[str, Any]:
    try:
        parts = log.relative_to(root).parts
    except ValueError:
        parts = log.parts
    seed = None
    scenario = parts[0] if parts else None
    tl_mode = None
    for part in parts:
        if part.startswith("seed_"):
            seed = _int_or_none(part.removeprefix("seed_"))
        elif part in {"tl_on", "tl_off"}:
            tl_mode = part
    return {"scenario": scenario, "seed": seed, "tl_mode": tl_mode}


def _path_has_any_marker(path: Path, markers: tuple[str, ...]) -> bool:
    lowered = str(path).lower()
    return any(marker in lowered for marker in markers)


def _candidate_number(row: dict[str, Any], name: str, index: int | None) -> float | None:
    if index is None:
        return None
    values = row.get(name)
    if not isinstance(values, list) or index < 0 or index >= len(values):
        return None
    return _number_or_none(values[index])


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_dict(path: Path) -> dict[str, Any]:
    value = _read_json(path)
    return value if isinstance(value, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _number_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


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
