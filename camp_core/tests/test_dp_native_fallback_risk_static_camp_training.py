from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.integrations.build_diffusion_planner_dp_native_fallback_risk_training_data import (  # noqa: E402
    DATASET_SCHEMA_VERSION,
)
from scripts.integrations.train_diffusion_planner_dp_native_fallback_risk_static_camp import (  # noqa: E402
    COMPLETE_STATUS,
    DISABLED_STATUS,
    REJECT_STATUS,
    main,
    train_fallback_risk_static_camp,
)
from scripts.integrations.validate_dp_native_fallback_risk_training_sufficiency_preflight import (  # noqa: E402
    APPROVED_ATOM_NAMES,
    APPROVED_ATOM_SCHEMA,
    COMPLETE_STATUS as PREFLIGHT_COMPLETE_STATUS,
)


DRY_RUN_FALSE_FLAGS = (
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


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _group(source_log: str, run_id: str, record_index: int) -> str:
    return f"{source_log}|{run_id}|{record_index}"


def _atoms(*, oracle_is_one: bool = True) -> list[list[float]]:
    high = [8.0] + [1.0 for _ in APPROVED_ATOM_NAMES[1:]]
    low = [0.25] + [1.0 for _ in APPROVED_ATOM_NAMES[1:]]
    return [high, low] if oracle_is_one else [low, high]


def _record(source_log: str, run_id: str, record_index: int, *, oracle_index: int = 1) -> dict[str, Any]:
    atoms = _atoms(oracle_is_one=oracle_index == 1)
    return {
        "schema_version": DATASET_SCHEMA_VERSION,
        "source_log": source_log,
        "source_log_sha256": "a" * 64,
        "source_artifact_sha256": "b" * 64,
        "run_id": run_id,
        "record_index": record_index,
        "selection_step": None,
        "candidate_count": 2,
        "selected_index": 0,
        "oracle_index": oracle_index,
        "oracle_policy": ["red", "lane", "quality"],
        "costs": [
            {"red": 1.0, "lane": 0.0, "quality": 1.0},
            {"red": 0.0, "lane": 0.0, "quality": 0.5},
        ],
        "margins": [1.0, 0.0] if oracle_index == 1 else [0.0, 1.0],
        "atom_schema_version": APPROVED_ATOM_SCHEMA,
        "atom_names": list(APPROVED_ATOM_NAMES),
        "atoms": copy.deepcopy(atoms),
        "normalized_atoms": copy.deepcopy(atoms),
        "training_authorized": False,
        "selected_index_used_as_feature": False,
        "candidate_rank_used_as_feature": False,
        "fallback_label_is_not_a_deployed_atom": True,
    }


def _base_artifacts(tmp_path: Path) -> dict[str, Path | str]:
    records = [
        _record("log_a", "run_0", 0),
        _record("log_a", "run_0", 1),
        _record("log_b", "run_1", 0),
    ]
    train_groups = [_group("log_a", "run_0", 0), _group("log_a", "run_0", 1)]
    validation_groups = [_group("log_b", "run_1", 0)]
    dataset = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "source_hashes": {"log_a": "a" * 64, "log_b": "a" * 64},
        "record_counts": {
            "records_total": 3,
            "records_without_feasible_candidate": 3,
            "records_with_feasible_candidate": 0,
            "records_built": 3,
            "failed_records": 0,
        },
        "records": records,
        "failed_records": [],
        "final_decision": {
            "status": "dp_native_fallback_risk_training_data_builder_complete",
            "passed": True,
            "enabled": True,
            "errors": [],
            "training_authorized": False,
            **{flag: False for flag in DRY_RUN_FALSE_FLAGS},
        },
    }
    dataset_path = _write(tmp_path / "dataset.json", dataset)
    dataset_sha = _sha(dataset_path)
    split = {
        "schema_version": "dp_native_fallback_risk_training_split_manifest_v1",
        "group_key_fields": ["source_log", "run_id", "record_index"],
        "training_groups": train_groups,
        "validation_groups": validation_groups,
        "record_assignments": [],
        "seeds": [21, 22],
        "formal_eval_artifact_included": False,
        "final_decision": {"passed": True, "enabled": True, "errors": []},
    }
    split_path = _write(tmp_path / "split.json", split)
    split_sha = _sha(split_path)
    scales = {
        "schema_version": "dp_native_fallback_risk_training_train_only_scale_manifest_v1",
        "source_dataset_sha256": dataset_sha,
        "source_split_manifest_sha256": split_sha,
        "fit_groups": train_groups,
        "excluded_validation_groups": validation_groups,
        "fit_seeds": [21, 22],
        "formal_eval_artifact_included": False,
        "atom_schema_version": APPROVED_ATOM_SCHEMA,
        "atom_names": list(APPROVED_ATOM_NAMES),
        "atom_scales": {name: 1.0 for name in APPROVED_ATOM_NAMES},
        "final_decision": {"passed": True, "enabled": True, "errors": []},
    }
    scales_path = _write(tmp_path / "scales.json", scales)
    scales_sha = _sha(scales_path)
    master = {
        "schema_version": "dp_native_fallback_risk_fallback_master_config_v1",
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
    }
    master_path = _write(tmp_path / "master.json", master)
    master_sha = _sha(master_path)
    command = {
        "schema_version": "dp_native_fallback_risk_training_command_plan_v1",
        "training_command_authorization": False,
        "training_execution_authorized": False,
        "training_authorized": False,
        "post_training_nonpromotion_plan_required": True,
        "development_holdout_acceptance_gate_required": True,
        **{flag: False for flag in DRY_RUN_FALSE_FLAGS},
    }
    command_path = _write(tmp_path / "command.json", command)
    command_sha = _sha(command_path)
    preflight = {
        "schema_version": "dp_native_fallback_risk_training_sufficiency_preflight_v1",
        "source_hashes": {
            "split_manifest": split_sha,
            "scale_manifest": scales_sha,
            "fallback_master_config": master_sha,
            "training_command_plan": command_sha,
        },
        "final_decision": {
            "status": PREFLIGHT_COMPLETE_STATUS,
            "passed": True,
            "enabled": True,
            "errors": [],
            "ready_for_future_training_authorization": True,
            "training_authorized": False,
            "camp_retraining_authorized_now": False,
        },
    }
    preflight_path = _write(tmp_path / "preflight.json", preflight)
    preflight_sha = _sha(preflight_path)
    return {
        "dataset_json": dataset_path,
        "expected_dataset_sha256": dataset_sha,
        "training_split_manifest_json": split_path,
        "expected_split_manifest_sha256": split_sha,
        "train_only_scale_manifest_json": scales_path,
        "expected_scale_manifest_sha256": scales_sha,
        "fallback_master_config_json": master_path,
        "expected_master_config_sha256": master_sha,
        "training_command_plan_json": command_path,
        "expected_training_command_plan_sha256": command_sha,
        "preflight_json": preflight_path,
        "expected_preflight_sha256": preflight_sha,
    }


def _kwargs(artifacts: dict[str, Path | str], output_dir: Path) -> dict[str, Any]:
    return {
        **artifacts,
        "output_dir": output_dir,
    }


def test_static_camp_training_is_default_off_and_does_not_read_missing_inputs(tmp_path: Path) -> None:
    report = train_fallback_risk_static_camp(
        dataset_json=tmp_path / "missing_dataset.json",
        expected_dataset_sha256="a" * 64,
        training_split_manifest_json=tmp_path / "missing_split.json",
        expected_split_manifest_sha256="b" * 64,
        train_only_scale_manifest_json=tmp_path / "missing_scales.json",
        expected_scale_manifest_sha256="c" * 64,
        fallback_master_config_json=tmp_path / "missing_master.json",
        expected_master_config_sha256="d" * 64,
        training_command_plan_json=tmp_path / "missing_command.json",
        expected_training_command_plan_sha256="e" * 64,
        preflight_json=tmp_path / "missing_preflight.json",
        expected_preflight_sha256="f" * 64,
        enabled=False,
        user_authorized=False,
        output_dir=tmp_path / "training",
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["training_executed"] is False
    assert report["source_hashes"] == {}
    assert not (tmp_path / "training" / "offline_weights_dp_fallback_risk_static.npy").exists()


def test_static_camp_training_requires_user_authorization_before_reads(tmp_path: Path) -> None:
    artifacts = _base_artifacts(tmp_path)

    report = train_fallback_risk_static_camp(
        **_kwargs(artifacts, tmp_path / "training"),
        enabled=True,
        user_authorized=False,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "user_camp_retraining_authorization_missing" in report["final_decision"]["errors"]
    assert report["source_hashes"] == {}
    assert not (tmp_path / "training").exists()


def test_static_camp_training_writes_nonpromotion_fixed_candidate_artifacts(tmp_path: Path) -> None:
    artifacts = _base_artifacts(tmp_path)
    output_json = tmp_path / "out" / "summary.json"
    output_md = tmp_path / "out" / "summary.md"
    output_dir = tmp_path / "training"

    exit_code = main(
        [
            "--dataset_json",
            str(artifacts["dataset_json"]),
            "--expected_dataset_sha256",
            str(artifacts["expected_dataset_sha256"]),
            "--training_split_manifest_json",
            str(artifacts["training_split_manifest_json"]),
            "--expected_split_manifest_sha256",
            str(artifacts["expected_split_manifest_sha256"]),
            "--train_only_scale_manifest_json",
            str(artifacts["train_only_scale_manifest_json"]),
            "--expected_scale_manifest_sha256",
            str(artifacts["expected_scale_manifest_sha256"]),
            "--fallback_master_config_json",
            str(artifacts["fallback_master_config_json"]),
            "--expected_master_config_sha256",
            str(artifacts["expected_master_config_sha256"]),
            "--training_command_plan_json",
            str(artifacts["training_command_plan_json"]),
            "--expected_training_command_plan_sha256",
            str(artifacts["expected_training_command_plan_sha256"]),
            "--preflight_json",
            str(artifacts["preflight_json"]),
            "--expected_preflight_sha256",
            str(artifacts["expected_preflight_sha256"]),
            "--enable_default_off_fallback_risk_static_camp_training",
            "--user_camp_retraining_authorized",
            "--epochs",
            "20",
            "--risk_type",
            "mean",
            "--output_dir",
            str(output_dir),
            "--output_summary_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    report = json.loads(output_json.read_text(encoding="utf-8"))
    weights = np.load(output_dir / "offline_weights_dp_fallback_risk_static.npy")

    assert exit_code == 0
    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert report["final_decision"]["training_execution_authorized"] is True
    assert report["final_decision"]["camp_retraining_authorized_now"] is True
    assert report["final_decision"]["fixed_dp_candidate_reranking_only"] is True
    assert report["final_decision"]["candidate_generation_authorized"] is False
    assert report["final_decision"]["dp_modification_authorized"] is False
    assert report["final_decision"]["selector_promotion_authorized"] is False
    assert report["final_decision"]["atom_promotion_authorized"] is False
    assert report["final_decision"]["safety_benefit_claim_authorized"] is False
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False
    assert output_md.read_text(encoding="utf-8").count("score_k(w)=a_k^T w") >= 1
    assert weights.shape == (len(APPROVED_ATOM_NAMES),)
    assert np.isclose(float(np.sum(weights)), 1.0)
    assert float(np.min(weights)) >= 0.0
    assert (output_dir / "offline_weights_dp_fallback_risk_static.json").is_file()
    assert (output_dir / "atom_scales_dp_fallback_risk_static.json").is_file()


def test_static_camp_training_rejects_formal_seed_and_feature_leaks(tmp_path: Path) -> None:
    artifacts = _base_artifacts(tmp_path)
    dataset_path = Path(artifacts["dataset_json"])
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    payload["records"][0]["selected_index_used_as_feature"] = True
    dataset_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    split_path = Path(artifacts["training_split_manifest_json"])
    split = json.loads(split_path.read_text(encoding="utf-8"))
    split["seeds"] = [11]
    split_path.write_text(json.dumps(split, sort_keys=True), encoding="utf-8")

    report = train_fallback_risk_static_camp(
        **_kwargs(artifacts, tmp_path / "training"),
        enabled=True,
        user_authorized=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dataset_sha256_mismatch" in report["final_decision"]["errors"]
    assert "split_manifest_sha256_mismatch" in report["final_decision"]["errors"]
    assert "formal_seed_in_development_split" in report["final_decision"]["errors"]
    assert not (tmp_path / "training").exists()
