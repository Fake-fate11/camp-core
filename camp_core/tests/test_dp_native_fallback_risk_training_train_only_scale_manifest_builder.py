from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.integrations.build_diffusion_planner_dp_native_fallback_risk_training_train_only_scale_manifest import (  # noqa: E402
    COMPLETE_STATUS,
    DISABLED_STATUS,
    REJECT_STATUS,
    SCALE_MANIFEST_SCHEMA_VERSION,
    build_scale_manifest_report,
    main,
)
from scripts.integrations.validate_dp_native_fallback_risk_training_sufficiency_preflight import (  # noqa: E402
    APPROVED_ATOM_NAMES,
    APPROVED_ATOM_SCHEMA,
    COMPLETE_STATUS as PREFLIGHT_COMPLETE_STATUS,
    validate_training_sufficiency_preflight,
)


DATASET_SCHEMA_VERSION = "dp_native_fallback_risk_training_data_v1"
SPLIT_MANIFEST_SCHEMA_VERSION = "dp_native_fallback_risk_training_split_manifest_v1"
VALIDATED_DATASET_SHA = "1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf"
VALIDATOR_SHA = "572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b"


def _group(source_log: str, run_id: str, record_index: int) -> str:
    return f"{source_log}|{run_id}|{record_index}"


def _atom_row(value: float, *, zero_last: bool = False) -> list[float]:
    row = [float(value) for _ in APPROVED_ATOM_NAMES]
    if zero_last:
        row[-1] = 0.0
    return row


def _record(
    source_log: str,
    run_id: str,
    record_index: int,
    atoms: list[list[float]],
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_log": source_log,
        "source_log_sha256": "a" * 64,
        "run_id": run_id,
        "record_index": record_index,
        "candidate_count": len(atoms),
        "selected_index": 0,
        "oracle_index": 0,
        "atom_schema_version": APPROVED_ATOM_SCHEMA,
        "atom_names": list(APPROVED_ATOM_NAMES),
        "atoms": atoms,
        "normalized_atoms": atoms,
        "training_authorized": False,
        "selected_index_used_as_feature": False,
        "candidate_rank_used_as_feature": False,
        "closed_loop_outcome_used_as_feature": False,
        "learned_weights_used_as_feature": False,
    }
    payload.update(overrides)
    return payload


def _dataset(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": DATASET_SCHEMA_VERSION,
        "records": records,
        "record_counts": {
            "records_total": len(records),
            "records_without_feasible_candidate": len(records),
            "records_with_feasible_candidate": 0,
            "records_built": len(records),
            "failed_records": 0,
        },
        "failed_records": [],
        "final_decision": {
            "status": "dp_native_fallback_risk_training_data_builder_complete",
            "passed": True,
            "enabled": True,
            "errors": [],
            "training_authorized": False,
            "camp_training_authorized": False,
            "camp_retraining_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
        },
    }


def _split(
    *,
    training_groups: list[str],
    validation_groups: list[str],
    seeds: list[int] | None = None,
    formal_eval_artifact_included: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": SPLIT_MANIFEST_SCHEMA_VERSION,
        "group_key_fields": ["source_log", "run_id", "record_index"],
        "training_groups": training_groups,
        "validation_groups": validation_groups,
        "seeds": seeds or [21, 22],
        "formal_eval_artifact_included": formal_eval_artifact_included,
        "final_decision": {
            "status": "dp_native_fallback_risk_training_split_manifest_builder_complete",
            "passed": True,
            "enabled": True,
            "errors": [],
            "training_authorized": False,
            "camp_training_authorized": False,
            "camp_retraining_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
        },
    }


def _write_json(tmp_path: Path, name: str, payload: dict[str, Any]) -> tuple[Path, str]:
    path = tmp_path / name
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _clean_inputs(tmp_path: Path) -> tuple[Path, str, Path, str, dict[str, Any], dict[str, Any]]:
    train_a = _group("log_a", "run_0", 0)
    train_b = _group("log_a", "run_0", 1)
    val_a = _group("log_b", "run_1", 0)
    dataset = _dataset(
        [
            _record("log_a", "run_0", 0, [_atom_row(2.0, zero_last=True)]),
            _record("log_a", "run_0", 1, [_atom_row(4.0, zero_last=True)]),
            _record("log_b", "run_1", 0, [_atom_row(999.0)]),
        ]
    )
    split = _split(
        training_groups=[train_a, train_b],
        validation_groups=[val_a],
    )
    dataset_path, dataset_sha = _write_json(tmp_path, "dataset.json", dataset)
    split_path, split_sha = _write_json(tmp_path, "split.json", split)
    return dataset_path, dataset_sha, split_path, split_sha, dataset, split


def _preflight_paths(
    tmp_path: Path,
    scale_manifest: dict[str, Any],
    split: dict[str, Any],
) -> dict[str, Path]:
    def write(name: str, payload: dict[str, Any]) -> Path:
        return _write_json(tmp_path, name, payload)[0]

    return {
        "validated_dataset_summary_json": write(
            "validated_dataset.json",
            {
                "sha256": VALIDATED_DATASET_SHA,
                "records": 15,
                "validator_status": "dp_native_fallback_risk_training_data_validator_complete",
                "validator_passed": True,
                "training_sufficiency_claim": False,
                "deployable_checkpoint_claim": False,
            },
        ),
        "training_split_manifest_json": write("preflight_split.json", split),
        "train_only_scale_manifest_json": write("scales.json", scale_manifest),
        "fallback_master_config_json": write(
            "master.json",
            {
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
        ),
        "training_command_plan_json": write(
            "command.json",
            {
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
        ),
    }


def test_scale_builder_is_default_off_and_does_not_read_missing_inputs(tmp_path: Path) -> None:
    report = build_scale_manifest_report(
        dataset_json=tmp_path / "missing_dataset.json",
        expected_dataset_sha256="a" * 64,
        training_split_manifest_json=tmp_path / "missing_split.json",
        expected_split_manifest_sha256="b" * 64,
        validator_output_sha256=VALIDATOR_SHA,
        enabled=False,
    )

    assert report["schema_version"] == SCALE_MANIFEST_SCHEMA_VERSION
    assert report["source_hashes"] == {}
    assert report["atom_scales"] == {}
    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["passed"] is True


def test_scale_builder_enabled_writes_preflight_compatible_manifest(tmp_path: Path) -> None:
    dataset_path, dataset_sha, split_path, split_sha, _, split = _clean_inputs(tmp_path)
    output_json = tmp_path / "out" / "scales.json"
    output_md = tmp_path / "out" / "scales.md"

    exit_code = main(
        [
            "--dataset_json",
            str(dataset_path),
            "--expected_dataset_sha256",
            dataset_sha,
            "--training_split_manifest_json",
            str(split_path),
            "--expected_split_manifest_sha256",
            split_sha,
            "--validator_output_sha256",
            VALIDATOR_SHA,
            "--enable_default_off_fallback_risk_training_train_only_scale_manifest_builder",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )
    written = json.loads(output_json.read_text(encoding="utf-8"))
    preflight = validate_training_sufficiency_preflight(
        enabled=True,
        **_preflight_paths(tmp_path, written, split),
    )

    assert exit_code == 0
    assert written["final_decision"]["status"] == COMPLETE_STATUS
    assert written["final_decision"]["training_authorized"] is False
    assert written["atom_schema_version"] == APPROVED_ATOM_SCHEMA
    assert written["atom_names"] == list(APPROVED_ATOM_NAMES)
    assert preflight["final_decision"]["status"] == PREFLIGHT_COMPLETE_STATUS
    assert "training_authorized=False" in output_md.read_text(encoding="utf-8")


def test_scale_builder_fits_only_training_groups_and_uses_p95_or_one(tmp_path: Path) -> None:
    dataset_path, dataset_sha, split_path, split_sha, _, _ = _clean_inputs(tmp_path)

    report = build_scale_manifest_report(
        dataset_json=dataset_path,
        expected_dataset_sha256=dataset_sha,
        training_split_manifest_json=split_path,
        expected_split_manifest_sha256=split_sha,
        validator_output_sha256=VALIDATOR_SHA,
        enabled=True,
    )

    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert report["fit_record_counts"]["training_records_seen"] == 2
    assert report["fit_record_counts"]["validation_records_seen"] == 1
    assert report["atom_scales"]["jerk_early"] == 4.0
    assert report["atom_scales"][APPROVED_ATOM_NAMES[-1]] == 1.0
    assert all(value > 0.0 for value in report["atom_scales"].values())


def test_scale_builder_rejects_sha_split_formal_and_record_scope_errors(tmp_path: Path) -> None:
    dataset_path, dataset_sha, split_path, split_sha, dataset, split = _clean_inputs(tmp_path)
    split["training_groups"].append(split["validation_groups"][0])
    split["seeds"] = [11]
    split["formal_eval_artifact_included"] = True
    dataset["records"].append(_record("log_extra", "run_x", 9, [_atom_row(1.0)]))
    dataset_path, _ = _write_json(tmp_path, "bad_dataset.json", dataset)
    split_path, _ = _write_json(tmp_path, "bad_split.json", split)

    report = build_scale_manifest_report(
        dataset_json=dataset_path,
        expected_dataset_sha256=dataset_sha,
        training_split_manifest_json=split_path,
        expected_split_manifest_sha256=split_sha,
        validator_output_sha256=VALIDATOR_SHA,
        enabled=True,
    )
    errors = report["final_decision"]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    for needle in [
        "dataset_sha256_mismatch",
        "split_manifest_sha256_mismatch",
        "training_validation_overlap",
        "formal_seed_in_split",
        "formal_eval_artifact_included",
        "record_3:dataset_record_not_in_split_manifest",
    ]:
        assert needle in errors


def test_scale_builder_rejects_feature_leaks_schema_mismatch_and_bad_atoms(tmp_path: Path) -> None:
    train_a = _group("log_a", "run_0", 0)
    train_b = _group("log_a", "run_0", 1)
    val_a = _group("log_b", "run_1", 0)
    dataset = _dataset(
        [
            _record(
                "log_a",
                "run_0",
                0,
                [[float("nan") for _ in APPROVED_ATOM_NAMES]],
                atom_schema_version="wrong",
                selected_index_scale_feature=True,
                candidate_rank_scale_feature=True,
            ),
            _record(
                "log_a",
                "run_0",
                1,
                [[7.0] + [-1.0 for _ in APPROVED_ATOM_NAMES[1:]]],
                atom_names=list(APPROVED_ATOM_NAMES[:-1]),
                closed_loop_outcome_scale_feature=True,
                learned_weights_scale_feature=True,
            ),
            _record("log_b", "run_1", 0, [_atom_row(1.0)]),
        ]
    )
    split = _split(training_groups=[train_a, train_b], validation_groups=[val_a])
    dataset_path, dataset_sha = _write_json(tmp_path, "dataset.json", dataset)
    split_path, split_sha = _write_json(tmp_path, "split.json", split)

    report = build_scale_manifest_report(
        dataset_json=dataset_path,
        expected_dataset_sha256=dataset_sha,
        training_split_manifest_json=split_path,
        expected_split_manifest_sha256=split_sha,
        validator_output_sha256=VALIDATOR_SHA,
        enabled=True,
    )
    errors = report["final_decision"]["errors"]

    for needle in [
        "record_0:selected_index_scale_feature_leak",
        "record_0:candidate_rank_scale_feature_leak",
        "record_1:closed_loop_outcome_scale_feature_leak",
        "record_1:learned_weights_scale_feature_leak",
        "record_0:atom_schema_mismatch",
        "record_1:atom_names_mismatch",
        "record_0:jerk_early_not_finite_numeric",
        "record_1:jerk_late_negative",
    ]:
        assert needle in errors
    assert report["atom_scales"]["jerk_early"] == 1.0
