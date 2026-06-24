#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.build_diffusion_planner_dp_native_fallback_risk_training_data import (  # noqa: E402
    DATASET_SCHEMA_VERSION,
)
from scripts.integrations.train_diffusion_planner_dp_native_fallback_risk_static_camp import (  # noqa: E402
    COMPLETE_STATUS as TRAINING_COMPLETE_STATUS,
    TRAINING_SCHEMA_VERSION,
)
from scripts.integrations.validate_dp_native_fallback_risk_training_sufficiency_preflight import (  # noqa: E402
    APPROVED_ATOM_NAMES,
    APPROVED_ATOM_SCHEMA,
)


AUDIT_SCHEMA_VERSION = "dp_native_fallback_risk_static_camp_training_development_holdout_acceptance_audit_v1"
DISABLED_STATUS = "dp_native_fallback_risk_static_camp_training_development_holdout_acceptance_audit_default_off_disabled"
COMPLETE_STATUS = "dp_native_fallback_risk_static_camp_training_development_holdout_acceptance_audit_complete"
REJECT_STATUS = "dp_native_fallback_risk_static_camp_training_development_holdout_acceptance_audit_rejected"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FORMAL_SEEDS = {11, 12, 13}

FORBIDDEN_FLAGS = (
    "training_authorized",
    "training_execution_authorized",
    "camp_retraining_authorized_now",
    "fallback_risk_training_authorized_now",
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "Full36_authorized",
    "formal_seeds_11_12_13_authorized",
    "dp_modification_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_postselection_authorized",
    "closed_loop_outcome_online_input_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "feasible_ranking_master_change_authorized",
    "hard_feasibility_relaxation_authorized",
    "all_infeasible_records_added_to_feasible_training",
    "production_selector_change_authorized",
    "online_selector_change_authorized",
    "deployment_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Default-off read-only development holdout acceptance audit for "
            "fallback-risk static CAMP fixed-candidate reranking artifacts."
        )
    )
    parser.add_argument("--dataset_json", type=Path, required=True)
    parser.add_argument("--expected_dataset_sha256", required=True)
    parser.add_argument("--training_split_manifest_json", type=Path, required=True)
    parser.add_argument("--expected_split_manifest_sha256", required=True)
    parser.add_argument("--train_only_scale_manifest_json", type=Path, required=True)
    parser.add_argument("--expected_scale_manifest_sha256", required=True)
    parser.add_argument("--fallback_master_config_json", type=Path, required=True)
    parser.add_argument("--expected_master_config_sha256", required=True)
    parser.add_argument("--preflight_json", type=Path, required=True)
    parser.add_argument("--expected_preflight_sha256", required=True)
    parser.add_argument("--training_summary_json", type=Path, required=True)
    parser.add_argument("--expected_training_summary_sha256", required=True)
    parser.add_argument("--weights_json", type=Path, required=True)
    parser.add_argument("--expected_weights_json_sha256", required=True)
    parser.add_argument("--weights_npy", type=Path, required=True)
    parser.add_argument("--expected_weights_npy_sha256", required=True)
    parser.add_argument("--atom_scales_json", type=Path, required=True)
    parser.add_argument("--expected_atom_scales_json_sha256", required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_default_off_fallback_risk_static_camp_training_development_holdout_acceptance_audit",
        action="store_true",
        help="Explicit opt-in required before reading fixed training artifacts.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = audit_development_holdout_acceptance(
        dataset_json=args.dataset_json,
        expected_dataset_sha256=args.expected_dataset_sha256,
        training_split_manifest_json=args.training_split_manifest_json,
        expected_split_manifest_sha256=args.expected_split_manifest_sha256,
        train_only_scale_manifest_json=args.train_only_scale_manifest_json,
        expected_scale_manifest_sha256=args.expected_scale_manifest_sha256,
        fallback_master_config_json=args.fallback_master_config_json,
        expected_master_config_sha256=args.expected_master_config_sha256,
        preflight_json=args.preflight_json,
        expected_preflight_sha256=args.expected_preflight_sha256,
        training_summary_json=args.training_summary_json,
        expected_training_summary_sha256=args.expected_training_summary_sha256,
        weights_json=args.weights_json,
        expected_weights_json_sha256=args.expected_weights_json_sha256,
        weights_npy=args.weights_npy,
        expected_weights_npy_sha256=args.expected_weights_npy_sha256,
        atom_scales_json=args.atom_scales_json,
        expected_atom_scales_json_sha256=args.expected_atom_scales_json_sha256,
        current_camp_head=args.current_camp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_default_off_fallback_risk_static_camp_training_development_holdout_acceptance_audit,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 1 if report["final_decision"]["status"] == REJECT_STATUS else 0


def audit_development_holdout_acceptance(
    *,
    dataset_json: Path,
    expected_dataset_sha256: str,
    training_split_manifest_json: Path,
    expected_split_manifest_sha256: str,
    train_only_scale_manifest_json: Path,
    expected_scale_manifest_sha256: str,
    fallback_master_config_json: Path,
    expected_master_config_sha256: str,
    preflight_json: Path,
    expected_preflight_sha256: str,
    training_summary_json: Path,
    expected_training_summary_sha256: str,
    weights_json: Path,
    expected_weights_json_sha256: str,
    weights_npy: Path,
    expected_weights_npy_sha256: str,
    atom_scales_json: Path,
    expected_atom_scales_json_sha256: str,
    current_camp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    report = _empty_report(
        enabled=enabled,
        current_camp_head=current_camp_head,
        required_dp_head=required_dp_head,
    )
    if not enabled:
        return report

    errors: list[str] = []
    expected_hashes = {
        "dataset": expected_dataset_sha256,
        "split_manifest": expected_split_manifest_sha256,
        "scale_manifest": expected_scale_manifest_sha256,
        "fallback_master_config": expected_master_config_sha256,
        "preflight": expected_preflight_sha256,
        "training_summary": expected_training_summary_sha256,
        "weights_json": expected_weights_json_sha256,
        "weights_npy": expected_weights_npy_sha256,
        "atom_scales_json": expected_atom_scales_json_sha256,
    }
    for name, value in expected_hashes.items():
        _validate_sha_literal(value, f"expected_{name}_sha256", errors)
    _validate_git_sha_literal(current_camp_head, "current_camp_head", errors)
    _validate_git_sha_literal(required_dp_head, "required_dp_head", errors)
    if required_dp_head != FIXED_DP_HEAD:
        errors.append("required_dp_head_not_fixed_tieriv_commit")

    path_by_name = {
        "dataset": dataset_json,
        "split_manifest": training_split_manifest_json,
        "scale_manifest": train_only_scale_manifest_json,
        "fallback_master_config": fallback_master_config_json,
        "preflight": preflight_json,
        "training_summary": training_summary_json,
        "weights_json": weights_json,
        "weights_npy": weights_npy,
        "atom_scales_json": atom_scales_json,
    }
    payloads: dict[str, Any] = {}
    for name, path in path_by_name.items():
        actual = _sha256_file_if_present(path, name, errors)
        if actual is not None:
            report["source_hashes"][name] = actual
            if _is_sha256(expected_hashes[name]) and actual != expected_hashes[name]:
                errors.append(f"{name}_sha256_mismatch")
        if name != "weights_npy":
            payloads[name] = _load_json(path, name, errors)

    split_info = _validate_split(payloads.get("split_manifest"), errors)
    _validate_scale_manifest(payloads.get("scale_manifest"), split_info, errors)
    _validate_master_config(payloads.get("fallback_master_config"), errors)
    _validate_preflight(payloads.get("preflight"), report["source_hashes"], errors)
    _validate_training_summary(payloads.get("training_summary"), split_info, errors)
    weights = _validate_weights_json(payloads.get("weights_json"), errors)
    weights_npy_array = _validate_weights_npy(weights_npy, errors)
    if not _vectors_close(weights, weights_npy_array):
        errors.append("weights_json_npy_mismatch")
    _validate_atom_scales(payloads.get("atom_scales_json"), errors)

    holdout = _audit_holdout_records(payloads.get("dataset"), split_info, weights, errors)
    report["holdout"] = holdout
    report["final_decision"] = _decision(
        status=REJECT_STATUS if errors else COMPLETE_STATUS,
        passed=not errors,
        enabled=True,
        errors=errors,
    )
    return report


def _empty_report(*, enabled: bool, current_camp_head: str, required_dp_head: str) -> dict[str, Any]:
    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "analysis": {
            "name": "dp_native_fallback_risk_static_camp_training_development_holdout_acceptance_audit_v1",
            "default_off": True,
            "enabled": bool(enabled),
            "read_only_existing_artifacts": True,
            "audit_only": True,
            "records_scope": "validation_groups_only",
            "fallback_branch_only": True,
            "records_without_feasible_candidate_only": True,
            "fixed_dp_candidate_reranking_only": True,
            "score_expression": "score_k(w)=a_k^T w",
            "selection_rule": "argmin_k score_k(w)",
            "current_camp_head": current_camp_head,
            "required_dp_head": required_dp_head,
            "replay_executed": False,
            "candidate_generation_executed": False,
            "camp_retraining_executed": False,
            "diffusion_planner_executed": False,
            "diffusion_planner_modified": False,
            "trajectory_generation_executed": False,
            "trajectory_rewrite_executed": False,
            "reference_blend_executed": False,
            "guidance_executed": False,
            "postprocess_postselection_executed": False,
            "selector_promotion_executed": False,
            "atom_promotion_executed": False,
            "deployment_executed": False,
        },
        "source_hashes": {},
        "holdout": {},
        "final_decision": _decision(
            status=DISABLED_STATUS,
            passed=True,
            enabled=enabled,
            errors=[],
        ),
    }


def _validate_split(payload: Any, errors: list[str]) -> dict[str, set[str]]:
    info = {"training_groups": set(), "validation_groups": set()}
    if not isinstance(payload, dict):
        errors.append("split_manifest_not_object")
        return info
    if tuple(payload.get("group_key_fields") or ()) != ("source_log", "run_id", "record_index"):
        errors.append("split_group_key_invalid")
    training = _string_set(payload.get("training_groups"), "training_groups", errors)
    validation = _string_set(payload.get("validation_groups"), "validation_groups", errors)
    if not validation:
        errors.append("split_validation_groups_empty")
    if training & validation:
        errors.append("split_training_validation_overlap")
    seeds = _int_set(payload.get("seeds"), "split_seeds", errors)
    if seeds & FORMAL_SEEDS:
        errors.append("split_formal_seed_leak")
    if payload.get("formal_eval_artifact_included") is not False:
        errors.append("split_formal_eval_artifact_included")
    info["training_groups"] = training
    info["validation_groups"] = validation
    return info


def _validate_scale_manifest(payload: Any, split_info: dict[str, set[str]], errors: list[str]) -> None:
    if not isinstance(payload, dict):
        errors.append("scale_manifest_not_object")
        return
    if payload.get("atom_schema_version") != APPROVED_ATOM_SCHEMA:
        errors.append("scale_atom_schema_version_mismatch")
    if tuple(payload.get("atom_names") or ()) != APPROVED_ATOM_NAMES:
        errors.append("scale_atom_names_mismatch")
    fit_groups = _string_set(payload.get("fit_groups"), "scale_fit_groups", errors)
    if fit_groups != split_info["training_groups"]:
        errors.append("scale_fit_groups_not_training_only")
    if fit_groups & split_info["validation_groups"]:
        errors.append("scale_validation_leak")
    fit_seeds = _int_set(payload.get("fit_seeds"), "scale_fit_seeds", errors)
    if fit_seeds & FORMAL_SEEDS:
        errors.append("scale_formal_seed_leak")
    if payload.get("formal_eval_artifact_included") is not False:
        errors.append("scale_formal_eval_artifact_included")


def _validate_master_config(payload: Any, errors: list[str]) -> None:
    if not isinstance(payload, dict):
        errors.append("fallback_master_config_not_object")
        return
    expected = {
        "fallback_only": True,
        "feasible_branch_records_allowed": False,
        "all_infeasible_records_added_to_feasible_training": False,
        "all_infeasible_records_relabelled_feasible": False,
        "hard_feasibility_relaxation_authorized": False,
        "feasible_ranking_master_change_authorized": False,
        "atoms_fixed_nonnegative": True,
        "fallback_label_is_deployed_atom": False,
        "margins_nonnegative": True,
        "simplex_cvar_l2_convex": True,
    }
    for field, expected_value in expected.items():
        if payload.get(field) is not expected_value:
            errors.append(f"fallback_master_config_{field}_mismatch")
    if payload.get("score_expression") != "score_k(w)=a_k^T w":
        errors.append("fallback_master_config_score_expression_not_affine")


def _validate_preflight(payload: Any, source_hashes: dict[str, str], errors: list[str]) -> None:
    if not isinstance(payload, dict):
        errors.append("preflight_not_object")
        return
    decision = payload.get("final_decision")
    if not isinstance(decision, dict):
        errors.append("preflight_final_decision_missing")
        return
    if decision.get("passed") is not True:
        errors.append("preflight_not_passed")
    if decision.get("training_authorized") is not False:
        errors.append("preflight_training_authorized_not_false")
    hashes = payload.get("source_hashes")
    if not isinstance(hashes, dict):
        errors.append("preflight_source_hashes_missing")
        return
    for source_name, report_name in (
        ("split_manifest", "split_manifest"),
        ("scale_manifest", "scale_manifest"),
        ("fallback_master_config", "fallback_master_config"),
    ):
        if hashes.get(source_name) != source_hashes.get(report_name):
            errors.append(f"preflight_{source_name}_hash_mismatch")


def _validate_training_summary(payload: Any, split_info: dict[str, set[str]], errors: list[str]) -> None:
    if not isinstance(payload, dict):
        errors.append("training_summary_not_object")
        return
    if payload.get("schema_version") != TRAINING_SCHEMA_VERSION:
        errors.append("training_summary_schema_version_mismatch")
    training = payload.get("training")
    if not isinstance(training, dict):
        errors.append("training_summary_training_missing")
    else:
        if training.get("training_type") != "dp_native_fallback_risk_static_candidate_reranking":
            errors.append("training_summary_training_type_mismatch")
        if training.get("training_scope") != "fallback_only_all_infeasible_fixed_dp_candidates":
            errors.append("training_summary_training_scope_mismatch")
        if training.get("score_expression") != "score_k(w)=a_k^T w":
            errors.append("training_summary_score_expression_not_affine")
        if training.get("objective") not in {"simplex_hinge_cvar_l2", "simplex_hinge_mean_l2"}:
            errors.append("training_summary_objective_invalid")
        if training.get("atom_schema_version") != APPROVED_ATOM_SCHEMA:
            errors.append("training_summary_atom_schema_mismatch")
        if tuple(training.get("atom_names") or ()) != APPROVED_ATOM_NAMES:
            errors.append("training_summary_atom_names_mismatch")
        if training.get("validation_records") != len(split_info["validation_groups"]):
            errors.append("training_summary_validation_record_count_mismatch")
    decision = payload.get("final_decision")
    if not isinstance(decision, dict):
        errors.append("training_summary_final_decision_missing")
        return
    if decision.get("status") != TRAINING_COMPLETE_STATUS:
        errors.append("training_summary_status_not_complete")
    if decision.get("passed") is not True:
        errors.append("training_summary_not_passed")
    for flag in (
        "fixed_dp_candidate_reranking_only",
        "fallback_only_training",
    ):
        if decision.get(flag) is not True:
            errors.append(f"training_summary_{flag}_not_true")
    for flag in FORBIDDEN_FLAGS:
        if flag.startswith(("training_", "camp_retraining", "fallback_risk_training")):
            continue
        if flag in decision and decision.get(flag) is not False:
            errors.append(f"training_summary_{flag}_not_false")


def _validate_weights_json(payload: Any, errors: list[str]) -> np.ndarray | None:
    if not isinstance(payload, dict):
        errors.append("weights_json_not_object")
        return None
    if payload.get("atom_schema_version") != APPROVED_ATOM_SCHEMA:
        errors.append("weights_json_atom_schema_version_mismatch")
    if tuple(payload.get("atom_names") or ()) != APPROVED_ATOM_NAMES:
        errors.append("weights_json_atom_names_mismatch")
    if payload.get("score_expression") != "score_k(w)=a_k^T w":
        errors.append("weights_json_score_expression_not_affine")
    if payload.get("fallback_only") is not True:
        errors.append("weights_json_fallback_only_not_true")
    if payload.get("selector_promotion_executed") is not False:
        errors.append("weights_json_selector_promotion_executed_not_false")
    weights = _vector(payload.get("weights"), "weights_json_weights", errors)
    if not _is_simplex_nonnegative(weights):
        errors.append("weights_json_not_simplex_nonnegative")
    return weights


def _validate_weights_npy(path: Path, errors: list[str]) -> np.ndarray | None:
    try:
        weights = np.load(path, allow_pickle=False).astype(np.float64)
    except (OSError, ValueError) as exc:
        errors.append(f"weights_npy_unreadable:{type(exc).__name__}")
        return None
    if weights.shape != (len(APPROVED_ATOM_NAMES),):
        errors.append("weights_npy_shape_mismatch")
        return None
    if not _is_simplex_nonnegative(weights):
        errors.append("weights_npy_not_simplex_nonnegative")
    return weights


def _validate_atom_scales(payload: Any, errors: list[str]) -> None:
    if not isinstance(payload, dict):
        errors.append("atom_scales_json_not_object")
        return
    if payload.get("atom_schema_version") != APPROVED_ATOM_SCHEMA:
        errors.append("atom_scales_json_atom_schema_version_mismatch")
    if tuple(payload.get("atom_names") or ()) != APPROVED_ATOM_NAMES:
        errors.append("atom_scales_json_atom_names_mismatch")
    scales = _vector(payload.get("scales"), "atom_scales_json_scales", errors)
    if scales is None or any(value <= 0.0 for value in scales):
        errors.append("atom_scales_json_not_strictly_positive")


def _audit_holdout_records(
    dataset: Any,
    split_info: dict[str, set[str]],
    weights: np.ndarray | None,
    errors: list[str],
) -> dict[str, Any]:
    if weights is None:
        errors.append("holdout_weights_missing")
        weights = np.zeros((len(APPROVED_ATOM_NAMES),), dtype=np.float64)
    if not isinstance(dataset, dict):
        errors.append("dataset_not_object")
        return _empty_holdout()
    if dataset.get("schema_version") != DATASET_SCHEMA_VERSION:
        errors.append("dataset_schema_version_mismatch")
    counts = dataset.get("record_counts")
    if not isinstance(counts, dict):
        errors.append("dataset_record_counts_missing")
    else:
        if counts.get("records_built") != counts.get("records_without_feasible_candidate"):
            errors.append("dataset_not_fallback_only")
        if counts.get("failed_records") != 0:
            errors.append("dataset_failed_records_nonzero")
    records = dataset.get("records")
    if not isinstance(records, list):
        errors.append("dataset_records_not_list")
        return _empty_holdout()

    validation_groups = split_info["validation_groups"]
    selected_records = []
    records_by_group = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record_{index}_not_object")
            continue
        group = _group_id(record)
        if group is not None:
            records_by_group[group] = record
    missing = sorted(validation_groups - set(records_by_group))
    if missing:
        errors.append("validation_groups_missing_from_dataset")
    for group in sorted(validation_groups):
        record = records_by_group.get(group)
        if record is not None:
            selected_records.append((group, record))

    record_reports = []
    static_oracle_matches = 0
    recorded_oracle_matches = 0
    uniform_oracle_matches = 0
    candidate0_oracle_matches = 0
    static_violations = []
    recorded_min_red = 0
    recorded_min_lane = 0
    recorded_min_quality = 0
    static_min_red = 0
    static_min_lane = 0
    static_min_quality = 0
    candidate_count_ok = True
    selected_index_ok = True
    tensor_ok = True
    source_hashes_present = True
    provenance_pairs_present = False
    provenance_pairs_equal = True

    uniform = np.full((len(APPROVED_ATOM_NAMES),), 1.0 / len(APPROVED_ATOM_NAMES), dtype=np.float64)
    for local_index, (group, record) in enumerate(selected_records):
        record_errors: list[str] = []
        parsed = _parse_record(record, local_index, record_errors)
        if record_errors:
            errors.extend(record_errors)
            candidate_count_ok = False
            selected_index_ok = False
            tensor_ok = False
            continue
        atoms = parsed["atoms"]
        margins = parsed["margins"]
        costs = parsed["costs"]
        oracle_index = parsed["oracle_index"]
        recorded_index = parsed["recorded_index"]
        static_scores = atoms @ weights
        static_index = int(np.argmin(static_scores))
        uniform_index = int(np.argmin(atoms @ uniform))
        candidate0_index = 0
        static_violation = _violation(atoms, margins, oracle_index, weights)
        static_violations.append(static_violation)
        static_oracle_matches += int(static_index == oracle_index)
        recorded_oracle_matches += int(recorded_index == oracle_index)
        uniform_oracle_matches += int(uniform_index == oracle_index)
        candidate0_oracle_matches += int(candidate0_index == oracle_index)
        min_red = _min_cost_index(costs, "red")
        min_lane = _min_cost_index(costs, "lane")
        min_quality = _min_cost_index(costs, "quality")
        recorded_min_red += int(recorded_index == min_red)
        recorded_min_lane += int(recorded_index == min_lane)
        recorded_min_quality += int(recorded_index == min_quality)
        static_min_red += int(static_index == min_red)
        static_min_lane += int(static_index == min_lane)
        static_min_quality += int(static_index == min_quality)
        source_hashes_present = source_hashes_present and bool(record.get("source_log_sha256")) and bool(record.get("source_artifact_sha256"))
        pre_hash = record.get("pre_candidate_tensor_sha256")
        post_hash = record.get("post_candidate_tensor_sha256")
        if pre_hash is not None or post_hash is not None:
            provenance_pairs_present = True
            if pre_hash != post_hash:
                provenance_pairs_equal = False
        record_reports.append(
            {
                "group": group,
                "candidate_count": int(parsed["candidate_count"]),
                "recorded_selected_index": int(recorded_index),
                "static_selected_index": int(static_index),
                "uniform_selected_index": int(uniform_index),
                "oracle_index": int(oracle_index),
                "selected_index_in_range": True,
                "candidate_count_unchanged": True,
                "static_score_min": float(np.min(static_scores)),
                "static_score_max": float(np.max(static_scores)),
                "static_violation": float(static_violation),
                "min_red_index": int(min_red),
                "min_lane_index": int(min_lane),
                "min_quality_index": int(min_quality),
            }
        )

    n = len(record_reports)
    if n == 0:
        errors.append("holdout_validation_records_empty")
        return _empty_holdout()
    return {
        "validation_records": n,
        "records_scope": "validation_groups_only",
        "fallback_branch_only": True,
        "records_without_feasible_candidate_only": True,
        "selected_index_in_range": bool(selected_index_ok),
        "candidate_count_unchanged": bool(candidate_count_ok),
        "candidate_tensor_unchanged": bool(tensor_ok),
        "source_hashes_present": bool(source_hashes_present),
        "pre_post_candidate_provenance_pairs_present": bool(provenance_pairs_present),
        "pre_post_candidate_provenance_hashes_equal_if_present": bool(provenance_pairs_equal),
        "static_oracle_match_rate": static_oracle_matches / n,
        "recorded_oracle_match_rate": recorded_oracle_matches / n,
        "uniform_oracle_match_rate": uniform_oracle_matches / n,
        "candidate0_oracle_match_rate": candidate0_oracle_matches / n,
        "static_mean_margin_violation": float(np.mean(static_violations)),
        "static_selected_min_red_match_rate": static_min_red / n,
        "static_selected_min_lane_match_rate": static_min_lane / n,
        "static_selected_min_quality_match_rate": static_min_quality / n,
        "recorded_selected_min_red_match_rate": recorded_min_red / n,
        "recorded_selected_min_lane_match_rate": recorded_min_lane / n,
        "recorded_selected_min_quality_match_rate": recorded_min_quality / n,
        "records": record_reports,
    }


def _empty_holdout() -> dict[str, Any]:
    return {
        "validation_records": 0,
        "records_scope": "validation_groups_only",
        "fallback_branch_only": True,
        "records_without_feasible_candidate_only": True,
        "selected_index_in_range": False,
        "candidate_count_unchanged": False,
        "candidate_tensor_unchanged": False,
    }


def _parse_record(record: dict[str, Any], index: int, errors: list[str]) -> dict[str, Any]:
    candidate_count = _strict_int(record.get("candidate_count"), f"record_{index}_candidate_count", errors)
    recorded_index = _strict_int(record.get("selected_index"), f"record_{index}_selected_index", errors)
    oracle_index = _strict_int(record.get("oracle_index"), f"record_{index}_oracle_index", errors)
    atoms = _matrix(record.get("normalized_atoms"), f"record_{index}_normalized_atoms", errors)
    margins = _vector_any_len(record.get("margins"), f"record_{index}_margins", errors)
    costs = record.get("costs")
    if not isinstance(costs, list) or not costs or not all(isinstance(item, dict) for item in costs):
        errors.append(f"record_{index}_costs_not_dict_list")
        costs = []
    if record.get("atom_schema_version") != APPROVED_ATOM_SCHEMA:
        errors.append(f"record_{index}_atom_schema_version_mismatch")
    if tuple(record.get("atom_names") or ()) != APPROVED_ATOM_NAMES:
        errors.append(f"record_{index}_atom_names_mismatch")
    if record.get("selected_index_used_as_feature") is not False:
        errors.append(f"record_{index}_selected_index_feature_leak")
    if record.get("candidate_rank_used_as_feature") is not False:
        errors.append(f"record_{index}_candidate_rank_feature_leak")
    if record.get("fallback_label_is_not_a_deployed_atom") is not True:
        errors.append(f"record_{index}_fallback_label_promoted_to_atom")
    if record.get("training_authorized") is not False:
        errors.append(f"record_{index}_training_authorized_not_false")
    if atoms is None or margins is None or candidate_count is None or recorded_index is None or oracle_index is None:
        return {}
    if atoms.shape != (candidate_count, len(APPROVED_ATOM_NAMES)):
        errors.append(f"record_{index}_atom_shape_mismatch")
    if len(margins) != candidate_count or len(costs) != candidate_count:
        errors.append(f"record_{index}_candidate_count_mismatch")
    if not (0 <= recorded_index < candidate_count):
        errors.append(f"record_{index}_selected_index_out_of_range")
    if not (0 <= oracle_index < candidate_count):
        errors.append(f"record_{index}_oracle_index_out_of_range")
    if np.min(atoms) < -1e-10:
        errors.append(f"record_{index}_atoms_negative")
    if np.min(margins) < -1e-10:
        errors.append(f"record_{index}_margins_negative")
    return {
        "candidate_count": candidate_count,
        "recorded_index": recorded_index,
        "oracle_index": oracle_index,
        "atoms": atoms,
        "margins": margins,
        "costs": costs,
    }


def _group_id(record: dict[str, Any]) -> str | None:
    values = []
    for field in ("source_log", "run_id", "record_index"):
        value = record.get(field)
        if value in (None, ""):
            return None
        values.append(str(value))
    return "|".join(values)


def _violation(atoms: np.ndarray, margins: np.ndarray, oracle_index: int, weights: np.ndarray) -> float:
    oracle_atoms = atoms[int(oracle_index)]
    values = margins + (oracle_atoms[None, :] - atoms) @ weights
    return float(max(float(np.max(values)), 0.0))


def _min_cost_index(costs: list[dict[str, Any]], key: str) -> int:
    values = []
    for item in costs:
        value = item.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            values.append(float("inf"))
        else:
            values.append(float(value))
    return int(np.argmin(np.asarray(values, dtype=np.float64)))


def _load_json(path: Path, name: str, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{name}_unreadable:{type(exc).__name__}")
        return {}


def _matrix(value: Any, field: str, errors: list[str]) -> np.ndarray | None:
    if not isinstance(value, list) or not value or not all(isinstance(row, list) and row for row in value):
        errors.append(f"{field}_not_nonempty_matrix")
        return None
    rows = []
    width: int | None = None
    for row_index, row in enumerate(value):
        parsed = []
        for item in row:
            if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)):
                errors.append(f"{field}_{row_index}_not_finite_numeric")
                return None
            parsed.append(float(item))
        if width is None:
            width = len(parsed)
        elif len(parsed) != width:
            errors.append(f"{field}_ragged")
            return None
        rows.append(parsed)
    return np.asarray(rows, dtype=np.float64)


def _vector(value: Any, field: str, errors: list[str]) -> np.ndarray | None:
    vector = _vector_any_len(value, field, errors)
    if vector is not None and vector.shape != (len(APPROVED_ATOM_NAMES),):
        errors.append(f"{field}_dimension_mismatch")
        return None
    return vector


def _vector_any_len(value: Any, field: str, errors: list[str]) -> np.ndarray | None:
    if not isinstance(value, list) or not value:
        errors.append(f"{field}_not_nonempty_vector")
        return None
    parsed = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)):
            errors.append(f"{field}_not_finite_numeric")
            return None
        parsed.append(float(item))
    return np.asarray(parsed, dtype=np.float64)


def _strict_int(value: Any, field: str, errors: list[str]) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{field}_not_int")
        return None
    return int(value)


def _string_set(value: Any, field: str, errors: list[str]) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        errors.append(f"{field}_not_string_list")
        return set()
    return set(value)


def _int_set(value: Any, field: str, errors: list[str]) -> set[int]:
    if not isinstance(value, list) or any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        errors.append(f"{field}_not_int_list")
        return set()
    return set(value)


def _is_simplex_nonnegative(weights: np.ndarray | None) -> bool:
    if weights is None or weights.shape != (len(APPROVED_ATOM_NAMES),):
        return False
    if not np.all(np.isfinite(weights)):
        return False
    return bool(np.min(weights) >= -1e-10 and abs(float(np.sum(weights)) - 1.0) <= 1e-8)


def _vectors_close(left: np.ndarray | None, right: np.ndarray | None) -> bool:
    if left is None or right is None:
        return False
    return bool(left.shape == right.shape and np.allclose(left, right, rtol=1e-9, atol=1e-10))


def _validate_sha_literal(value: Any, field: str, errors: list[str]) -> None:
    if not _is_sha256(value):
        errors.append(f"{field}_invalid")


def _validate_git_sha_literal(value: Any, field: str, errors: list[str]) -> None:
    if not _is_git_sha(value):
        errors.append(f"{field}_invalid")


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value.lower())


def _is_git_sha(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 40:
        return False
    return all(char in "0123456789abcdef" for char in value.lower())


def _sha256_file_if_present(path: Path, name: str, errors: list[str]) -> str | None:
    try:
        return _sha256_file(path)
    except OSError as exc:
        errors.append(f"{name}_unreadable:{type(exc).__name__}")
        return None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decision(*, status: str, passed: bool, enabled: bool, errors: list[str]) -> dict[str, Any]:
    decision = {
        "status": status,
        "passed": bool(passed),
        "enabled": bool(enabled),
        "errors": sorted(set(errors)),
        "development_holdout_acceptance_audit_passed": bool(enabled and passed),
        "audit_only": True,
        "plan_only": False,
        "fixed_dp_candidate_reranking_only": bool(enabled and passed),
        "fallback_branch_only": True,
        "records_scope": "validation_groups_only",
        "records_without_feasible_candidate_only": True,
        "score_expression": "score_k(w)=a_k^T w",
        "selection_rule": "argmin_k score_k(w)",
    }
    for flag in FORBIDDEN_FLAGS:
        decision[flag] = False
    return decision


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    analysis = report["analysis"]
    holdout = report.get("holdout") or {}
    lines = [
        "# DP Native Fallback Risk Static CAMP Development Holdout Acceptance Audit",
        "",
        "```text",
        f"status={decision['status']}",
        f"passed={decision['passed']}",
        f"enabled={decision['enabled']}",
        f"development_holdout_acceptance_audit_passed={decision['development_holdout_acceptance_audit_passed']}",
        f"audit_only={decision['audit_only']}",
        f"fixed_dp_candidate_reranking_only={decision['fixed_dp_candidate_reranking_only']}",
        f"records_scope={decision['records_scope']}",
        f"score_expression={decision['score_expression']}",
        f"selection_rule={decision['selection_rule']}",
        f"current_camp_head={analysis['current_camp_head']}",
        f"required_dp_head={analysis['required_dp_head']}",
        "training_authorized=False",
        "training_execution_authorized=False",
        "camp_retraining_authorized_now=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "deployment_authorized=False",
        "```",
        "",
    ]
    if holdout:
        lines.extend(["## Holdout Metrics", "", "```text"])
        for key in (
            "validation_records",
            "selected_index_in_range",
            "candidate_count_unchanged",
            "candidate_tensor_unchanged",
            "source_hashes_present",
            "pre_post_candidate_provenance_pairs_present",
            "pre_post_candidate_provenance_hashes_equal_if_present",
            "static_oracle_match_rate",
            "recorded_oracle_match_rate",
            "uniform_oracle_match_rate",
            "candidate0_oracle_match_rate",
            "static_mean_margin_violation",
            "static_selected_min_red_match_rate",
            "static_selected_min_lane_match_rate",
            "static_selected_min_quality_match_rate",
        ):
            if key in holdout:
                lines.append(f"{key}={holdout[key]}")
        lines.extend(["```", ""])
    if decision["errors"]:
        lines.extend(["## Errors", "", "```text"])
        lines.extend(str(error) for error in decision["errors"])
        lines.extend(["```", ""])
    lines.append(
        "This audit only recomputes fixed-candidate validation-holdout scores "
        "from existing artifacts. It does not run replay, generate or modify "
        "candidates, retrain CAMP, alter Diffusion Planner, promote selectors "
        "or atoms, deploy a checkpoint, or claim safety benefit."
    )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
