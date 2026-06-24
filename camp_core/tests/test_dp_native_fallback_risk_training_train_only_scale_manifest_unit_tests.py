from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.integrations.validate_dp_native_fallback_risk_training_sufficiency_preflight import (  # noqa: E402
    APPROVED_ATOM_NAMES,
    APPROVED_ATOM_SCHEMA,
    COMPLETE_STATUS as PREFLIGHT_COMPLETE_STATUS,
    REJECT_STATUS as PREFLIGHT_REJECT_STATUS,
    validate_training_sufficiency_preflight,
)


DISABLED_STATUS = "dp_native_fallback_risk_training_train_only_scale_manifest_default_off_disabled"
COMPLETE_STATUS = "dp_native_fallback_risk_training_train_only_scale_manifest_contract_complete"
REJECT_STATUS = "dp_native_fallback_risk_training_train_only_scale_manifest_contract_rejected"
VALIDATED_DATASET_SHA = "1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf"
FORMAL_SEEDS = {11, 12, 13}
FORBIDDEN_FLAGS = (
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "camp_training_authorized",
    "camp_retraining_authorized",
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
    "fallback_risk_training_authorized_now",
    "feasible_ranking_master_change_authorized",
    "hard_feasibility_relaxation_authorized",
    "all_infeasible_records_added_to_feasible_training",
    "production_selector_change_authorized",
    "online_selector_change_authorized",
)


def _atom_row(value: float, *, zero_last: bool = False) -> list[float]:
    row = [float(value) for _ in APPROVED_ATOM_NAMES]
    if zero_last:
        row[-1] = 0.0
    return row


def _record(
    group: str,
    atoms: list[list[float]],
    *,
    atom_schema_version: str = APPROVED_ATOM_SCHEMA,
    atom_names: list[str] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "group_key": group,
        "atom_schema_version": atom_schema_version,
        "atom_names": list(APPROVED_ATOM_NAMES if atom_names is None else atom_names),
        "atoms": atoms,
        "selected_index": 0,
        "candidate_count": len(atoms),
    }
    payload.update(overrides)
    return payload


def _dataset(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "sha256": VALIDATED_DATASET_SHA,
        "records": records,
        "record_counts": {"records_without_feasible_candidate": len(records)},
        "training_sufficiency_claim": False,
        "deployable_checkpoint_claim": False,
    }


def _split(
    *,
    train: list[str] | None = None,
    validation: list[str] | None = None,
    seeds: list[int] | None = None,
    formal_eval_artifact_included: bool = False,
) -> dict[str, Any]:
    return {
        "group_key_fields": ["source_log", "run_id", "record_index"],
        "training_groups": train or ["train_a", "train_b"],
        "validation_groups": validation or ["val_a"],
        "seeds": seeds or [21, 22],
        "formal_eval_artifact_included": formal_eval_artifact_included,
    }


def _nearest_rank_p95(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return float(ordered[index])


def _decision(status: str, *, passed: bool, enabled: bool, errors: list[str]) -> dict[str, Any]:
    decision: dict[str, Any] = {
        "status": status,
        "passed": passed,
        "enabled": enabled,
        "errors": sorted(set(errors)),
        "train_only_scale_manifest_builder_authorized": False,
        "train_only_scale_manifest_unit_tests_complete": True,
        "training_authorized": False,
        "fallback_dataset_training_sufficiency_claim": False,
    }
    for flag in FORBIDDEN_FLAGS:
        decision[flag] = False
    return decision


def _scale_contract_report(
    dataset: dict[str, Any] | None,
    split: dict[str, Any] | None,
    *,
    enabled: bool,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": "dp_native_fallback_risk_training_train_only_scale_manifest_contract_tests_v1",
        "analysis": {
            "default_off": True,
            "enabled": enabled,
            "synthetic_fixtures_only": True,
            "builder_implemented": False,
            "replay_executed": False,
            "candidate_generation_executed": False,
            "camp_training_executed": False,
            "diffusion_planner_modified": False,
        },
        "manifest": None,
        "final_decision": _decision(
            DISABLED_STATUS,
            passed=True,
            enabled=False,
            errors=[],
        ),
    }
    if not enabled:
        return report

    errors: list[str] = []
    if not isinstance(dataset, dict):
        errors.append("dataset_not_object")
        dataset = {"records": []}
    if not isinstance(split, dict):
        errors.append("split_not_object")
        split = {}

    train = _string_set(split.get("training_groups"), "training_groups", errors)
    validation = _string_set(split.get("validation_groups"), "validation_groups", errors)
    if not train:
        errors.append("training_groups_empty")
    if not validation:
        errors.append("validation_groups_empty")
    if train & validation:
        errors.append("training_validation_overlap")
    seeds = _int_set(split.get("seeds"), "split_seeds", errors)
    if seeds & FORMAL_SEEDS:
        errors.append("formal_seed_in_split")
    if split.get("formal_eval_artifact_included") is not False:
        errors.append("formal_eval_artifact_included")

    positives_by_atom: dict[str, list[float]] = {name: [] for name in APPROVED_ATOM_NAMES}
    seen_groups: set[str] = set()
    records = dataset.get("records")
    if not isinstance(records, list):
        errors.append("dataset_records_not_list")
        records = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record_{index}_not_object")
            continue
        group = record.get("group_key")
        if not isinstance(group, str) or not group:
            errors.append(f"record_{index}_missing_group_key")
            continue
        seen_groups.add(group)
        if group not in train and group not in validation:
            errors.append(f"dataset_record_not_in_split:{group}")
        for field in (
            "selected_index_scale_feature",
            "candidate_rank_scale_feature",
            "closed_loop_outcome_scale_feature",
            "learned_weights_scale_feature",
        ):
            if record.get(field) not in (None, False):
                errors.append(f"{field}_leak")
        if group not in train:
            continue
        if record.get("atom_schema_version") != APPROVED_ATOM_SCHEMA:
            errors.append(f"record_{index}_atom_schema_mismatch")
        if tuple(record.get("atom_names") or ()) != APPROVED_ATOM_NAMES:
            errors.append(f"record_{index}_atom_names_mismatch")
        rows = record.get("atoms")
        if not isinstance(rows, list):
            errors.append(f"record_{index}_atoms_not_list")
            continue
        for row_index, row in enumerate(rows):
            if not isinstance(row, list) or len(row) != len(APPROVED_ATOM_NAMES):
                errors.append(f"record_{index}_atoms_{row_index}_dimension_mismatch")
                continue
            for atom_name, value in zip(APPROVED_ATOM_NAMES, row):
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                ):
                    errors.append(f"record_{index}_{atom_name}_not_finite_numeric")
                    continue
                if float(value) < 0.0:
                    errors.append(f"record_{index}_{atom_name}_negative")
                    continue
                if float(value) > 0.0:
                    positives_by_atom[atom_name].append(float(value))

    missing_train = train - seen_groups
    missing_validation = validation - seen_groups
    if missing_train:
        errors.append("missing_training_groups")
    if missing_validation:
        errors.append("missing_validation_groups")

    atom_scales = {
        atom: (_nearest_rank_p95(values) if values else 1.0)
        for atom, values in positives_by_atom.items()
    }
    manifest = {
        "schema_version": "dp_native_fallback_risk_training_train_only_scale_manifest_v1",
        "source_dataset_sha256": dataset.get("sha256"),
        "fit_groups": list(split.get("training_groups") or []),
        "excluded_validation_groups": list(split.get("validation_groups") or []),
        "fit_seeds": list(split.get("seeds") or []),
        "formal_eval_artifact_included": False,
        "atom_schema_version": APPROVED_ATOM_SCHEMA,
        "atom_names": list(APPROVED_ATOM_NAMES),
        "scale_policy": "train_only_positive_finite_p95_or_one_v1",
        "atom_scales": atom_scales,
    }
    report["manifest"] = manifest
    report["final_decision"] = _decision(
        REJECT_STATUS if errors else COMPLETE_STATUS,
        passed=not errors,
        enabled=True,
        errors=errors,
    )
    return report


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


def _write(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _preflight_payloads(scale_manifest: dict[str, Any], split: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "dataset": {
            "sha256": VALIDATED_DATASET_SHA,
            "records": 15,
            "validator_status": "dp_native_fallback_risk_training_data_validator_complete",
            "validator_passed": True,
            "training_sufficiency_claim": False,
            "deployable_checkpoint_claim": False,
        },
        "split": split,
        "scales": scale_manifest,
        "master": {
            "fallback_only": True,
            "feasible_branch_records_allowed": False,
            "all_infeasible_records_added_to_feasible_training": False,
            "all_infeasible_records_relabelled_feasible": False,
            "hard_feasibility_relaxation_authorized": False,
            "feasible_ranking_master_change_authorized": False,
            "score_expression": "score_k(w)=a_k^T w",
            "atoms_fixed_nonnegative": True,
            "fallback_label_is_deployed_atom": False,
            "margins_nonnegative": True,
            "simplex_cvar_l2_convex": True,
        },
        "command": {
            "training_command_authorization": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "camp_training_authorized": False,
            "camp_retraining_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_11_12_13_authorized": False,
            "dp_modification_authorized": False,
            "reference_blend_authorized": False,
            "guidance_authorized": False,
            "postprocess_postselection_authorized": False,
            "closed_loop_outcome_online_input_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "fallback_risk_training_authorized_now": False,
            "feasible_ranking_master_change_authorized": False,
            "hard_feasibility_relaxation_authorized": False,
            "all_infeasible_records_added_to_feasible_training": False,
            "production_selector_change_authorized": False,
            "online_selector_change_authorized": False,
            "post_training_nonpromotion_plan_required": True,
            "development_holdout_acceptance_gate_required": True,
        },
    }


def _run_preflight(tmp_path: Path, payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return validate_training_sufficiency_preflight(
        enabled=True,
        validated_dataset_summary_json=_write(tmp_path / "dataset.json", payloads["dataset"]),
        training_split_manifest_json=_write(tmp_path / "split.json", payloads["split"]),
        train_only_scale_manifest_json=_write(tmp_path / "scales.json", payloads["scales"]),
        fallback_master_config_json=_write(tmp_path / "master.json", payloads["master"]),
        training_command_plan_json=_write(tmp_path / "command.json", payloads["command"]),
    )


def test_scale_contract_is_default_off_and_does_not_need_inputs() -> None:
    report = _scale_contract_report(None, None, enabled=False)

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["manifest"] is None
    assert report["analysis"]["builder_implemented"] is False
    assert report["analysis"]["replay_executed"] is False
    assert report["analysis"]["camp_training_executed"] is False


def test_scale_contract_computes_train_only_positive_p95_or_one() -> None:
    split = _split()
    dataset = _dataset(
        [
            _record("train_a", [_atom_row(2.0, zero_last=True)]),
            _record("train_b", [_atom_row(4.0, zero_last=True)]),
            _record("val_a", [_atom_row(999.0)]),
        ]
    )

    report = _scale_contract_report(dataset, split, enabled=True)
    manifest = report["manifest"]

    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert manifest["fit_groups"] == ["train_a", "train_b"]
    assert manifest["excluded_validation_groups"] == ["val_a"]
    assert manifest["atom_schema_version"] == APPROVED_ATOM_SCHEMA
    assert manifest["atom_names"] == list(APPROVED_ATOM_NAMES)
    assert manifest["atom_scales"]["jerk_early"] == 4.0
    assert manifest["atom_scales"][APPROVED_ATOM_NAMES[-1]] == 1.0
    assert all(value > 0.0 for value in manifest["atom_scales"].values())


def test_scale_contract_rejects_split_validation_and_formal_leaks() -> None:
    split = _split(
        train=["train_a", "val_a"],
        validation=["val_a"],
        seeds=[11],
        formal_eval_artifact_included=True,
    )
    dataset = _dataset(
        [
            _record("train_a", [_atom_row(1.0)]),
            _record("val_a", [_atom_row(1.0)]),
            _record("extra", [_atom_row(1.0)]),
        ]
    )

    errors = _scale_contract_report(dataset, split, enabled=True)["final_decision"]["errors"]

    for needle in [
        "training_validation_overlap",
        "formal_seed_in_split",
        "formal_eval_artifact_included",
        "dataset_record_not_in_split:extra",
    ]:
        assert needle in errors


def test_scale_contract_rejects_feature_leakage_schema_mismatch_and_bad_atoms() -> None:
    split = _split()
    dataset = _dataset(
        [
            _record(
                "train_a",
                [[float("inf") for _ in APPROVED_ATOM_NAMES]],
                atom_schema_version="wrong",
                selected_index_scale_feature=True,
            ),
            _record(
                "train_b",
                [[-1.0 for _ in APPROVED_ATOM_NAMES]],
                atom_names=list(APPROVED_ATOM_NAMES[:-1]),
                candidate_rank_scale_feature=True,
                closed_loop_outcome_scale_feature=True,
                learned_weights_scale_feature=True,
            ),
            _record("val_a", [_atom_row(1.0)]),
        ]
    )

    errors = _scale_contract_report(dataset, split, enabled=True)["final_decision"]["errors"]

    for needle in [
        "selected_index_scale_feature_leak",
        "candidate_rank_scale_feature_leak",
        "closed_loop_outcome_scale_feature_leak",
        "learned_weights_scale_feature_leak",
        "record_0_atom_schema_mismatch",
        "record_1_atom_names_mismatch",
        "record_0_jerk_early_not_finite_numeric",
        "record_1_jerk_early_negative",
    ]:
        assert needle in errors


def test_scale_contract_preflight_accepts_clean_manifest_and_rejects_scale_leaks(
    tmp_path: Path,
) -> None:
    split = _split()
    dataset = _dataset(
        [
            _record("train_a", [_atom_row(1.0)]),
            _record("train_b", [_atom_row(2.0)]),
            _record("val_a", [_atom_row(3.0)]),
        ]
    )
    manifest = _scale_contract_report(dataset, split, enabled=True)["manifest"]
    payloads = _preflight_payloads(manifest, split)

    clean = _run_preflight(tmp_path, payloads)
    assert clean["final_decision"]["status"] == PREFLIGHT_COMPLETE_STATUS
    assert clean["final_decision"]["ready_for_future_training_authorization"] is True
    assert clean["final_decision"]["training_authorized"] is False

    payloads["scales"]["fit_groups"] = ["train_a", "val_a"]
    payloads["scales"]["fit_seeds"] = [12]
    payloads["scales"]["atom_scales"]["jerk_early"] = 0.0
    rejected = _run_preflight(tmp_path, payloads)
    errors = rejected["final_decision"]["errors"]
    assert rejected["final_decision"]["status"] == PREFLIGHT_REJECT_STATUS
    for needle in [
        "scale_fit_groups_not_training_only",
        "scale_fit_validation_leak",
        "scale_fit_formal_seed_leak",
        "atom_scale_jerk_early_not_strictly_positive",
    ]:
        assert needle in errors


def test_scale_contract_forbids_execution_training_dp_changes_and_claims() -> None:
    report = _scale_contract_report(
        _dataset(
            [
                _record("train_a", [_atom_row(1.0)]),
                _record("train_b", [_atom_row(2.0)]),
                _record("val_a", [_atom_row(3.0)]),
            ]
        ),
        _split(),
        enabled=True,
    )

    assert report["final_decision"]["status"] == COMPLETE_STATUS
    for flag in FORBIDDEN_FLAGS:
        assert report["final_decision"][flag] is False
    assert report["final_decision"]["train_only_scale_manifest_builder_authorized"] is False
    assert report["final_decision"]["training_authorized"] is False
    assert report["analysis"]["candidate_generation_executed"] is False
    assert report["analysis"]["diffusion_planner_modified"] is False
