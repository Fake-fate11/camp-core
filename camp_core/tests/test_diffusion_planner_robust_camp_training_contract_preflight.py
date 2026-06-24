from __future__ import annotations

import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension
from scripts.integrations.train_diffusion_planner_robust_camp import (
    _run_dp_native_training_data_contract_preflight,
)
from scripts.integrations.validate_dp_native_training_data_contract import (
    PROVENANCE_SCHEMA_VERSION,
)


def _sha(value: str) -> str:
    return value * 64


def _valid_record() -> dict[str, object]:
    version, names = atom_schema_for_dimension(9)
    return {
        "selected_index": 0,
        "atom_schema_version": version,
        "atom_names": list(names),
        "atoms": [
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            [0.2, 0.1, 0.4, 0.3, 0.6, 0.5, 0.8, 0.7, 1.0],
        ],
        "feasible_mask": [True, True],
        "candidate_generation_contract": {
            "schema_version": "dp_candidate_generation_contract_v1",
            "num_candidates": 2,
            "noise_strategy": "iid",
            "reference_blend_steps": None,
            "guidance_enabled": False,
            "changes_diffusion_planner_weights": False,
        },
        "camp_candidate_tensor_provenance": {
            "schema_version": PROVENANCE_SCHEMA_VERSION,
            "selection_effect": False,
            "candidate_generation_effect": False,
            "candidate_tensor_mutation_effect": False,
            "candidate_generation_authorized": False,
            "trajectory_rewrite_authorized": False,
            "dp_modification_authorized": False,
            "payload_valid": True,
            "pre_post_tensor_hash_equal": True,
            "selected_index_in_range": True,
            "no_candidate_row_append": True,
            "no_coordinate_heading_speed_rewrite_by_camp": True,
            "reference_blend_stage_hash_separated": True,
            "outcome_label_input": False,
            "closed_loop_outcome_fields_read": False,
            "candidate_count": 2,
            "post_selector_candidate_count": 2,
            "selected_index": 0,
            "pre_camp_scoring_tensor": {
                "sha256": _sha("b"),
                "shape": [2, 80, 4],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
            "post_camp_selector_tensor": {
                "sha256": _sha("b"),
                "shape": [2, 80, 4],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
        },
        "candidate_closed_loop_outcomes": [
            {"candidate_index": 0, "value": 0.0, "feasible": True},
            {"candidate_index": 1, "value": 1.0, "feasible": True},
        ],
    }


def _write_log(path: Path, record: dict[str, object]) -> Path:
    log_path = path / "camp_selection_log.json"
    log_path.write_text(json.dumps([record]), encoding="utf-8")
    return log_path


def test_preflight_default_off_does_not_touch_selection_logs(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing_camp_selection_log.json"

    report = _run_dp_native_training_data_contract_preflight(
        [missing_path],
        required=False,
    )

    assert report is None


def test_preflight_required_accepts_clean_dp_native_log(tmp_path: Path) -> None:
    log_path = _write_log(tmp_path, _valid_record())

    report = _run_dp_native_training_data_contract_preflight(
        [log_path],
        required=True,
    )

    assert report is not None
    assert report["passed"] is True
    assert report["training_execution_authorized"] is False
    assert report["replay_executed"] is False
    assert report["candidate_generation_executed"] is False


def test_preflight_required_fails_before_training_on_invalid_log(
    tmp_path: Path,
) -> None:
    record = _valid_record()
    record.pop("camp_candidate_tensor_provenance")
    log_path = _write_log(tmp_path, record)

    with pytest.raises(ValueError, match="validation failed before training"):
        _run_dp_native_training_data_contract_preflight(
            [log_path],
            required=True,
        )
