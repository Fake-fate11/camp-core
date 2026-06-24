from __future__ import annotations

import copy
import hashlib
import json
import math
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


DATASET_SCHEMA_VERSION = "dp_native_fallback_risk_training_data_v1"
COMPLETE_STATUS = "dp_native_fallback_risk_training_data_builder_complete"

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
    "production_selector_change_authorized",
    "online_selector_change_authorized",
    "feasible_ranking_master_change_authorized",
    "hard_feasibility_relaxation_authorized",
    "all_infeasible_records_added_to_feasible_training",
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hex(char: str = "a") -> str:
    return char * 64


def _record_identity_hash(record: dict[str, Any]) -> str:
    identity = {
        "source_log": record.get("source_log"),
        "source_log_sha256": record.get("source_log_sha256"),
        "run_id": record.get("run_id"),
        "record_index": record.get("record_index"),
    }
    return hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _nonnegative_matrix(candidate_count: int, atom_dim: int) -> list[list[float]]:
    return [
        [0.1 * float(candidate_index + atom_index + 1) for atom_index in range(atom_dim)]
        for candidate_index in range(candidate_count)
    ]


def _source_record(
    *,
    candidate_count: int = 2,
    selected_index: int = 0,
    feasible_mask: list[Any] | None = None,
    atoms: list[list[float]] | None = None,
    normalized_atoms: list[list[float]] | None = None,
    generation_overrides: dict[str, Any] | None = None,
    provenance_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    version, names = atom_schema_for_dimension(9)
    atoms = atoms or _nonnegative_matrix(candidate_count, len(names))
    normalized_atoms = normalized_atoms or copy.deepcopy(atoms)
    generation = {
        "schema_version": "dp_candidate_generation_contract_v1",
        "num_candidates": candidate_count,
        "reference_blend_steps": None,
        "guidance_enabled": False,
        "changes_diffusion_planner_weights": False,
    }
    generation.update(generation_overrides or {})
    provenance = {
        "schema_version": "dp_native_candidate_tensor_provenance_payload_v1",
        "payload_valid": True,
        "candidate_count": candidate_count,
        "post_selector_candidate_count": candidate_count,
        "selected_index": selected_index,
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
        "selected_index": selected_index,
        "feasible_mask": feasible_mask if feasible_mask is not None else [False] * candidate_count,
        "dp_candidate_rewards": [
            {
                "red_light": -float(index + 1),
                "lane_crossing": False,
                "static_crossing": False,
                "off_road_fraction": 0.0,
                "lane_near_frac": 0.0,
                "lane_wide_frac": 0.0,
                "centerline": 0.0,
                "total": -10.0 + float(index),
            }
            for index in range(candidate_count)
        ],
        "atom_schema_version": version,
        "atom_names": list(names),
        "atoms": atoms,
        "normalized_atoms": normalized_atoms,
        "candidate_generation_contract": generation,
        "camp_candidate_tensor_provenance": provenance,
    }


def _write_source_log(tmp_path: Path, records: list[dict[str, Any]]) -> Path:
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps(records, sort_keys=True), encoding="utf-8")
    return path


def _dataset(tmp_path: Path) -> dict[str, Any]:
    source_record = _source_record()
    source_log = _write_source_log(tmp_path, [source_record])
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
            {"red": 1.0, "lane": 0.0, "quality": 10.0},
            {"red": 0.0, "lane": 0.0, "quality": 9.0},
        ],
        "margins": [1.0, 0.0],
        "atom_schema_version": version,
        "atom_names": list(names),
        "atoms": copy.deepcopy(source_record["atoms"]),
        "normalized_atoms": copy.deepcopy(source_record["normalized_atoms"]),
        "training_authorized": False,
        "selected_index_used_as_feature": False,
        "candidate_rank_used_as_feature": False,
        "fallback_label_is_not_a_deployed_atom": True,
    }
    record["record_identity_hash"] = _record_identity_hash(record)
    decision = {
        "status": COMPLETE_STATUS,
        "passed": True,
        "enabled": True,
        "errors": [],
        "training_authorized": False,
    }
    for flag in FORBIDDEN_FLAGS:
        decision[flag] = False
    return {
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


def _validate_dataset_contract(dataset: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if dataset.get("schema_version") != DATASET_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    records = dataset.get("records")
    if not isinstance(records, list):
        return ["records_not_list"]
    counts = dataset.get("record_counts")
    if not isinstance(counts, dict):
        errors.append("record_counts_missing")
        counts = {}
    if counts.get("records_built") != len(records):
        errors.append("records_built_count_mismatch")
    if counts.get("records_built") != counts.get("records_without_feasible_candidate"):
        errors.append("records_built_without_feasible_count_mismatch")
    if counts.get("failed_records") != 0 or dataset.get("failed_records") not in ([], None):
        errors.append("failed_records_nonzero")

    decision = dataset.get("final_decision")
    if not isinstance(decision, dict):
        errors.append("final_decision_missing")
        decision = {}
    if decision.get("status") != COMPLETE_STATUS:
        errors.append("final_decision_status_invalid")
    if decision.get("passed") is not True:
        errors.append("final_decision_not_passed")
    if decision.get("enabled") is not True:
        errors.append("final_decision_not_enabled")
    if decision.get("errors") not in ([], None):
        errors.append("final_decision_errors_nonempty")
    for flag in FORBIDDEN_FLAGS + ("training_authorized",):
        if decision.get(flag) is not False:
            errors.append(f"decision_{flag}_not_false")

    source_hashes = dataset.get("source_hashes")
    if not isinstance(source_hashes, dict):
        errors.append("source_hashes_missing")
        source_hashes = {}
    for record_index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record_{record_index}_not_object")
            continue
        errors.extend(_validate_dataset_record(record, source_hashes, record_index))
    return errors


def _validate_dataset_record(
    record: dict[str, Any],
    source_hashes: dict[str, Any],
    record_position: int,
) -> list[str]:
    errors: list[str] = []
    candidate_count = _strict_int(record.get("candidate_count"), "candidate_count", errors)
    if candidate_count is None or candidate_count < 1:
        errors.append("candidate_count_invalid")
        candidate_count = 0
    selected_index = _index(record.get("selected_index"), candidate_count, "selected_index", errors)
    _index(record.get("oracle_index"), candidate_count, "oracle_index", errors)
    if record.get("oracle_policy") not in (
        ["red", "lane", "quality"],
        ["lane", "red", "quality"],
        ["quality", "red", "lane"],
    ):
        errors.append("oracle_policy_invalid")
    errors.extend(_validate_costs(record.get("costs"), candidate_count))
    errors.extend(_validate_numbers(record.get("margins"), candidate_count, "margins"))
    errors.extend(_validate_atoms(record, candidate_count))
    if "record_identity_hash" not in record:
        errors.append("record_identity_hash_missing")
    elif record.get("record_identity_hash") != _record_identity_hash(record):
        errors.append("record_identity_hash_mismatch")
    for field, expected in (
        ("training_authorized", False),
        ("selected_index_used_as_feature", False),
        ("candidate_rank_used_as_feature", False),
        ("fallback_label_is_not_a_deployed_atom", True),
    ):
        if record.get(field) is not expected:
            errors.append(f"{field}_invalid")
    errors.extend(
        _validate_source_readback(
            record,
            source_hashes,
            record_position=record_position,
            candidate_count=candidate_count,
            selected_index=selected_index,
        )
    )
    return errors


def _validate_source_readback(
    record: dict[str, Any],
    source_hashes: dict[str, Any],
    *,
    record_position: int,
    candidate_count: int,
    selected_index: int | None,
) -> list[str]:
    errors: list[str] = []
    source_log = record.get("source_log")
    source_sha = record.get("source_log_sha256")
    if not isinstance(source_log, str) or not source_log:
        return ["source_log_missing"]
    if not _is_hex_sha(source_sha):
        errors.append("source_log_sha256_invalid")
    path = Path(source_log)
    if not path.is_file():
        errors.append("source_log_missing_on_disk")
        return errors
    actual_sha = _sha256_file(path)
    if actual_sha != source_sha or source_hashes.get(source_log) != source_sha:
        errors.append("source_log_hash_mismatch")
    source_records = json.loads(path.read_text(encoding="utf-8"))
    source_index = _strict_int(record.get("record_index"), "record_index", errors)
    if source_index is None or source_index < 0 or source_index >= len(source_records):
        errors.append("source_record_missing")
        return errors
    source_record = source_records[source_index]
    feasible = source_record.get("feasible_mask")
    if not isinstance(feasible, list) or not all(isinstance(item, bool) for item in feasible):
        errors.append("source_feasible_mask_non_bool")
    elif any(feasible):
        errors.append("source_feasible_mask_any_true")
    rewards = source_record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or len(rewards) != candidate_count:
        errors.append("source_candidate_count_mismatch")
    if source_record.get("selected_index") != selected_index:
        errors.append("source_selected_index_mismatch")
    errors.extend(_validate_generation(source_record.get("candidate_generation_contract"), candidate_count))
    errors.extend(
        _validate_provenance(
            source_record.get("camp_candidate_tensor_provenance"),
            candidate_count,
            selected_index,
        )
    )
    errors.extend(_validate_atoms(source_record, candidate_count, prefix="source"))
    return errors


def _validate_generation(contract: Any, candidate_count: int) -> list[str]:
    if not isinstance(contract, dict):
        return ["source_candidate_generation_contract_missing"]
    errors: list[str] = []
    if contract.get("schema_version") != "dp_candidate_generation_contract_v1":
        errors.append("source_candidate_generation_schema_mismatch")
    if contract.get("num_candidates") != candidate_count:
        errors.append("source_candidate_generation_count_mismatch")
    if contract.get("reference_blend_steps") is not None:
        errors.append("source_reference_blend_enabled")
    if contract.get("guidance_enabled") is not False:
        errors.append("source_guidance_enabled")
    if contract.get("changes_diffusion_planner_weights") is not False:
        errors.append("source_dp_weight_change_enabled")
    return errors


def _validate_provenance(payload: Any, candidate_count: int, selected_index: int | None) -> list[str]:
    if not isinstance(payload, dict):
        return ["source_provenance_missing"]
    errors: list[str] = []
    if payload.get("schema_version") != "dp_native_candidate_tensor_provenance_payload_v1":
        errors.append("source_provenance_schema_mismatch")
    for field in (
        "payload_valid",
        "pre_post_tensor_hash_equal",
        "selected_index_in_range",
        "no_candidate_row_append",
        "no_coordinate_heading_speed_rewrite_by_camp",
    ):
        if payload.get(field) is not True:
            errors.append(f"source_provenance_{field}_not_true")
    for field in (
        "selection_effect",
        "candidate_generation_effect",
        "candidate_tensor_mutation_effect",
        "candidate_generation_authorized",
        "trajectory_rewrite_authorized",
        "dp_modification_authorized",
        "outcome_label_input",
        "closed_loop_outcome_fields_read",
    ):
        if payload.get(field) is not False:
            errors.append(f"source_provenance_{field}_not_false")
    if payload.get("candidate_count") != candidate_count:
        errors.append("source_provenance_candidate_count_mismatch")
    if payload.get("post_selector_candidate_count") != candidate_count:
        errors.append("source_provenance_post_selector_candidate_count_mismatch")
    if payload.get("selected_index") != selected_index:
        errors.append("source_provenance_selected_index_mismatch")
    return errors


def _validate_atoms(record: dict[str, Any], candidate_count: int, prefix: str = "record") -> list[str]:
    errors: list[str] = []
    atoms = record.get("atoms")
    normalized = record.get("normalized_atoms")
    if not isinstance(atoms, list) or len(atoms) != candidate_count:
        return [f"{prefix}_atoms_candidate_count_mismatch"]
    atom_dim = len(atoms[0]) if atoms and isinstance(atoms[0], list) else 0
    try:
        version, names = atom_schema_for_dimension(atom_dim)
    except ValueError:
        version, names = "", ()
        errors.append(f"{prefix}_atom_schema_dimension_not_approved")
    if record.get("atom_schema_version") != version:
        errors.append(f"{prefix}_atom_schema_version_mismatch")
    if tuple(record.get("atom_names") or ()) != tuple(names):
        errors.append(f"{prefix}_atom_names_mismatch")
    errors.extend(_validate_matrix(atoms, candidate_count, atom_dim, f"{prefix}_atoms"))
    errors.extend(_validate_matrix(normalized, candidate_count, atom_dim, f"{prefix}_normalized_atoms"))
    return errors


def _validate_costs(value: Any, candidate_count: int) -> list[str]:
    if not isinstance(value, list) or len(value) != candidate_count:
        return ["costs_count_mismatch"]
    errors: list[str] = []
    for row_index, row in enumerate(value):
        if not isinstance(row, dict):
            errors.append(f"costs_{row_index}_not_object")
            continue
        for field in ("red", "lane", "quality"):
            number = row.get(field)
            if isinstance(number, bool) or not isinstance(number, (int, float)):
                errors.append(f"costs_{row_index}_{field}_not_numeric")
            elif not math.isfinite(float(number)) or float(number) < 0.0:
                errors.append(f"costs_{row_index}_{field}_not_finite_nonnegative")
    return errors


def _validate_numbers(value: Any, count: int, field: str) -> list[str]:
    if not isinstance(value, list) or len(value) != count:
        return [f"{field}_count_mismatch"]
    errors: list[str] = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            errors.append(f"{field}_{index}_not_numeric")
        elif not math.isfinite(float(item)) or float(item) < 0.0:
            errors.append(f"{field}_{index}_not_finite_nonnegative")
    return errors


def _validate_matrix(value: Any, rows: int, cols: int, field: str) -> list[str]:
    if not isinstance(value, list) or len(value) != rows:
        return [f"{field}_row_count_mismatch"]
    errors: list[str] = []
    for row_index, row in enumerate(value):
        if not isinstance(row, list) or len(row) != cols:
            errors.append(f"{field}_{row_index}_shape_mismatch")
            continue
        for col_index, item in enumerate(row):
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                errors.append(f"{field}_{row_index}_{col_index}_not_numeric")
            elif not math.isfinite(float(item)) or float(item) < 0.0:
                errors.append(f"{field}_{row_index}_{col_index}_not_finite_nonnegative")
    return errors


def _strict_int(value: Any, field: str, errors: list[str]) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{field}_not_int")
        return None
    return value


def _index(value: Any, candidate_count: int, field: str, errors: list[str]) -> int | None:
    index = _strict_int(value, field, errors)
    if index is None:
        return None
    if index < 0 or index >= candidate_count:
        errors.append(f"{field}_out_of_range")
    return index


def _is_hex_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdefABCDEF" for char in value)
    )


def test_reference_contract_accepts_clean_fallback_dataset(tmp_path: Path) -> None:
    dataset = _dataset(tmp_path)

    assert _validate_dataset_contract(dataset) == []


def test_reference_contract_rejects_top_level_summary_mismatches(tmp_path: Path) -> None:
    dataset = _dataset(tmp_path)
    dataset["schema_version"] = "wrong"
    dataset["record_counts"]["records_built"] = 2
    dataset["final_decision"]["status"] = "failed"
    dataset["final_decision"]["errors"] = ["bad"]

    errors = _validate_dataset_contract(dataset)

    for needle in [
        "schema_version_mismatch",
        "records_built_count_mismatch",
        "records_built_without_feasible_count_mismatch",
        "final_decision_status_invalid",
        "final_decision_errors_nonempty",
    ]:
        assert needle in errors


def test_reference_contract_rejects_source_log_readback_failures(tmp_path: Path) -> None:
    dataset = _dataset(tmp_path)
    dataset["source_hashes"][dataset["records"][0]["source_log"]] = _hex("c")
    errors = _validate_dataset_contract(dataset)
    assert "source_log_hash_mismatch" in errors

    source_log = Path(dataset["records"][0]["source_log"])
    source = json.loads(source_log.read_text(encoding="utf-8"))
    source[0]["feasible_mask"] = [False, True]
    source_log.write_text(json.dumps(source, sort_keys=True), encoding="utf-8")
    sha = _sha256_file(source_log)
    dataset["records"][0]["source_log_sha256"] = sha
    dataset["source_hashes"][str(source_log)] = sha
    errors = _validate_dataset_contract(dataset)
    assert "source_feasible_mask_any_true" in errors

    source[0]["feasible_mask"] = [False, "false"]
    source_log.write_text(json.dumps(source, sort_keys=True), encoding="utf-8")
    sha = _sha256_file(source_log)
    dataset["records"][0]["source_log_sha256"] = sha
    dataset["source_hashes"][str(source_log)] = sha
    errors = _validate_dataset_contract(dataset)
    assert "source_feasible_mask_non_bool" in errors


def test_reference_contract_rejects_missing_or_mismatched_record_identity_hash(
    tmp_path: Path,
) -> None:
    dataset = _dataset(tmp_path)
    dataset["records"][0].pop("record_identity_hash")
    errors = _validate_dataset_contract(dataset)
    assert "record_identity_hash_missing" in errors

    dataset = _dataset(tmp_path)
    dataset["records"][0]["record_identity_hash"] = _hex("f")
    errors = _validate_dataset_contract(dataset)
    assert "record_identity_hash_mismatch" in errors


def test_reference_contract_rejects_record_margin_index_and_atom_failures(tmp_path: Path) -> None:
    dataset = _dataset(tmp_path)
    record = dataset["records"][0]
    record["selected_index"] = 99
    record["oracle_policy"] = ["rank", "selected", "future"]
    record["margins"] = [0.0, -1.0]
    record["atoms"][0][0] = -0.1
    record["normalized_atoms"][1] = [0.1]

    errors = _validate_dataset_contract(dataset)

    for needle in [
        "selected_index_out_of_range",
        "oracle_policy_invalid",
        "margins_1_not_finite_nonnegative",
        "record_atoms_0_0_not_finite_nonnegative",
        "record_normalized_atoms_1_shape_mismatch",
        "source_selected_index_mismatch",
    ]:
        assert needle in errors


def test_reference_contract_rejects_training_and_promotion_flags(tmp_path: Path) -> None:
    dataset = _dataset(tmp_path)
    record = dataset["records"][0]
    decision = dataset["final_decision"]
    record["training_authorized"] = True
    record["selected_index_used_as_feature"] = True
    record["candidate_rank_used_as_feature"] = True
    record["fallback_label_is_not_a_deployed_atom"] = False
    decision["camp_training_authorized"] = True
    decision["selector_promotion_authorized"] = True
    decision["safety_benefit_claim_authorized"] = True

    errors = _validate_dataset_contract(dataset)

    for needle in [
        "training_authorized_invalid",
        "selected_index_used_as_feature_invalid",
        "candidate_rank_used_as_feature_invalid",
        "fallback_label_is_not_a_deployed_atom_invalid",
        "decision_camp_training_authorized_not_false",
        "decision_selector_promotion_authorized_not_false",
        "decision_safety_benefit_claim_authorized_not_false",
    ]:
        assert needle in errors
