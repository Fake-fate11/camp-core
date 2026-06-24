from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension
from scripts.integrations.build_diffusion_planner_dp_native_fallback_risk_training_data import (
    COMPLETE_STATUS as BUILDER_COMPLETE_STATUS,
    DATASET_SCHEMA_VERSION,
)
from scripts.integrations.validate_dp_native_fallback_risk_training_data_contract import (
    COMPLETE_STATUS,
    DISABLED_STATUS,
    REJECT_STATUS,
    main,
    validate_fallback_risk_training_data,
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hex(char: str = "a") -> str:
    return char * 64


def _source_record(
    *,
    feasible_mask: list[Any] | None = None,
    generation_overrides: dict[str, Any] | None = None,
    provenance_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    version, names = atom_schema_for_dimension(9)
    atoms = [[0.1 * float(row + col + 1) for col in range(len(names))] for row in range(2)]
    generation = {
        "schema_version": "dp_candidate_generation_contract_v1",
        "num_candidates": 2,
        "reference_blend_steps": None,
        "guidance_enabled": False,
        "changes_diffusion_planner_weights": False,
    }
    generation.update(generation_overrides or {})
    provenance = {
        "schema_version": "dp_native_candidate_tensor_provenance_payload_v1",
        "payload_valid": True,
        "candidate_count": 2,
        "post_selector_candidate_count": 2,
        "selected_index": 0,
        "selected_index_in_range": True,
        "pre_post_tensor_hash_equal": True,
        "no_candidate_row_append": True,
        "no_coordinate_heading_speed_rewrite_by_camp": True,
        "selection_effect": False,
        "candidate_generation_effect": False,
        "candidate_tensor_mutation_effect": False,
        "candidate_generation_authorized": False,
        "trajectory_rewrite_authorized": False,
        "dp_modification_authorized": False,
        "outcome_label_input": False,
        "closed_loop_outcome_fields_read": False,
    }
    provenance.update(provenance_overrides or {})
    return {
        "selected_index": 0,
        "feasible_mask": feasible_mask if feasible_mask is not None else [False, False],
        "dp_candidate_rewards": [{"total": -1.0}, {"total": -2.0}],
        "atom_schema_version": version,
        "atom_names": list(names),
        "atoms": atoms,
        "normalized_atoms": copy.deepcopy(atoms),
        "candidate_generation_contract": generation,
        "camp_candidate_tensor_provenance": provenance,
    }


def _write_source_log(tmp_path: Path, records: list[dict[str, Any]]) -> Path:
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps(records, sort_keys=True), encoding="utf-8")
    return path


def _dataset(tmp_path: Path) -> Path:
    source = _source_record()
    source_log = _write_source_log(tmp_path, [source])
    source_sha = _sha256_file(source_log)
    version, names = atom_schema_for_dimension(9)
    record = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "source_log": str(source_log),
        "source_log_sha256": source_sha,
        "source_artifact_sha256": _hex("b"),
        "run_id": "synthetic_run",
        "record_index": 0,
        "candidate_count": 2,
        "selected_index": 0,
        "oracle_index": 1,
        "oracle_policy": ["red", "lane", "quality"],
        "costs": [
            {"red": 1.0, "lane": 0.0, "quality": 2.0},
            {"red": 0.0, "lane": 0.0, "quality": 1.0},
        ],
        "margins": [1.0, 0.0],
        "atom_schema_version": version,
        "atom_names": list(names),
        "atoms": copy.deepcopy(source["atoms"]),
        "normalized_atoms": copy.deepcopy(source["normalized_atoms"]),
        "training_authorized": False,
        "selected_index_used_as_feature": False,
        "candidate_rank_used_as_feature": False,
        "fallback_label_is_not_a_deployed_atom": True,
    }
    decision = {
        "status": BUILDER_COMPLETE_STATUS,
        "passed": True,
        "enabled": True,
        "errors": [],
        "training_authorized": False,
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
        "production_selector_change_authorized": False,
        "online_selector_change_authorized": False,
        "feasible_ranking_master_change_authorized": False,
        "hard_feasibility_relaxation_authorized": False,
        "all_infeasible_records_added_to_feasible_training": False,
    }
    dataset = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "source_hashes": {str(source_log): source_sha},
        "record_counts": {
            "records_total": 1,
            "records_without_feasible_candidate": 1,
            "records_with_feasible_candidate": 0,
            "records_built": 1,
            "failed_records": 0,
        },
        "records": [record],
        "failed_records": [],
        "final_decision": decision,
    }
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(dataset, sort_keys=True), encoding="utf-8")
    return path


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_validator_is_default_off_and_does_not_read_missing_dataset(tmp_path: Path) -> None:
    report = validate_fallback_risk_training_data(
        dataset_json=tmp_path / "missing.json",
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["record_counts"]["records_checked"] == 0


def test_validator_accepts_clean_dataset_and_cli_writes_outputs(tmp_path: Path) -> None:
    dataset = _dataset(tmp_path)
    output_json = tmp_path / "out" / "validation.json"
    output_md = tmp_path / "out" / "validation.md"

    report = validate_fallback_risk_training_data(dataset_json=dataset, enabled=True)
    exit_code = main(
        [
            "--dataset_json",
            str(dataset),
            "--enable_default_off_fallback_risk_training_data_validator",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    written = _load(output_json)
    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert report["record_counts"]["records_checked"] == 1
    assert report["record_counts"]["failed_records"] == 0
    assert exit_code == 0
    assert written["final_decision"]["status"] == COMPLETE_STATUS
    assert "training_authorized=False" in output_md.read_text(encoding="utf-8")


def test_validator_rejects_top_level_summary_and_forbidden_flags(tmp_path: Path) -> None:
    dataset = _dataset(tmp_path)
    payload = _load(dataset)
    payload["schema_version"] = "wrong"
    payload["record_counts"]["records_built"] = 2
    payload["final_decision"]["status"] = "failed"
    payload["final_decision"]["camp_training_authorized"] = True
    dataset.write_text(json.dumps(payload), encoding="utf-8")

    report = validate_fallback_risk_training_data(dataset_json=dataset, enabled=True)
    errors = report["final_decision"]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    for needle in [
        "dataset_schema_version_mismatch",
        "records_built_count_mismatch",
        "records_built_without_feasible_count_mismatch",
        "final_decision_status_invalid",
        "final_decision_camp_training_authorized_not_false",
    ]:
        assert needle in errors


def test_validator_rejects_source_log_readback_failures(tmp_path: Path) -> None:
    dataset = _dataset(tmp_path)
    payload = _load(dataset)
    source_log = Path(payload["records"][0]["source_log"])
    payload["source_hashes"][str(source_log)] = _hex("c")
    dataset.write_text(json.dumps(payload), encoding="utf-8")

    report = validate_fallback_risk_training_data(dataset_json=dataset, enabled=True)
    assert any("source_log_hash_mismatch" in item for item in report["final_decision"]["errors"])

    payload = _load(dataset)
    source = json.loads(source_log.read_text(encoding="utf-8"))
    source[0]["feasible_mask"] = [False, True]
    source_log.write_text(json.dumps(source, sort_keys=True), encoding="utf-8")
    source_sha = _sha256_file(source_log)
    payload["records"][0]["source_log_sha256"] = source_sha
    payload["source_hashes"][str(source_log)] = source_sha
    dataset.write_text(json.dumps(payload), encoding="utf-8")

    report = validate_fallback_risk_training_data(dataset_json=dataset, enabled=True)
    assert any("source_feasible_mask_any_true" in item for item in report["final_decision"]["errors"])


def test_validator_rejects_record_margin_atom_index_and_promotion_flags(tmp_path: Path) -> None:
    dataset = _dataset(tmp_path)
    payload = _load(dataset)
    record = payload["records"][0]
    record["selected_index"] = 99
    record["margins"] = [0.0, -1.0]
    record["atoms"][0][0] = -0.1
    record["normalized_atoms"][1] = [0.1]
    record["training_authorized"] = True
    record["selected_index_used_as_feature"] = True
    record["fallback_label_is_not_a_deployed_atom"] = False
    dataset.write_text(json.dumps(payload), encoding="utf-8")

    report = validate_fallback_risk_training_data(dataset_json=dataset, enabled=True)
    errors = report["final_decision"]["errors"]

    for needle in [
        "selected_index_out_of_range",
        "margins_1_not_finite_nonnegative",
        "record_atoms_0_0_not_finite_nonnegative",
        "record_normalized_atoms_1_shape_mismatch",
        "training_authorized_invalid",
        "selected_index_used_as_feature_invalid",
        "fallback_label_is_not_a_deployed_atom_invalid",
    ]:
        assert any(needle in item for item in errors)
