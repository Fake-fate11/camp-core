from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_context import (
    CONTEXT_SCHEMA_VERSION,
    RAW_FEATURE_NAMES,
)
from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (
    build_controlled_scenario_case,
)
from scripts.integrations import run_diffusion_planner_dp_camp_v21_native as runner
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (
    CORPUS_STEPS,
    EXPECTED_SEED,
    SNAPSHOT_SCHEMA_VERSION,
    build_controlled_train_config,
    combine_snapshot_context,
)


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "configs" / "diffusion_planner_v22_native_capability.json"


def _case() -> dict:
    x = np.linspace(0.0, 100.0, 101)
    route = {
        "record_key": "train/map/route",
        "identity_sha256": "1" * 64,
        "map_family_id": "map_family_d7f16a17d3eb",
        "route_serialization_sha256": "2" * 64,
        "source_map_path": "/maps/train.osm",
        "source_map_sha256": "3" * 64,
        "source_route_length_m": 100.0,
        "centerline_samples_m": np.column_stack((x, np.zeros_like(x))).tolist(),
        "centerline_headings_rad": np.zeros(101).tolist(),
        "route_spec": {
            "map_path": "/maps/train.osm",
            "start_pose": [0.0, 0.0, 0.0],
            "goal_pose": [100.0, 0.0, 0.0],
            "lanelet_ids": [1],
            "route_length_m": 100.0,
        },
        "source_stratum": {
            "branch_intersection": False,
            "short_progress_opportunity": False,
            "tight_corridor": True,
            "traffic_light": False,
        },
    }
    case = build_controlled_scenario_case(
        route=route,
        corridor_group_sha256="4" * 64,
        split="train",
        family="lead_vehicle_hard_brake",
        tier="high_risk",
        variant=0,
        seeds=[EXPECTED_SEED],
    )
    case["retention_role"] = "executable"
    return case


def _config() -> dict:
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    return build_controlled_train_config(
        template,
        _case(),
        {"path": "/artifact/route.pkl", "sha256": "5" * 64},
    )


def test_controlled_train_config_is_exactly_64_tick_train_only() -> None:
    config = _config()

    runner.validate_v25_controlled_train_config(config)
    runner._validate_native_config(config)
    assert config["schema_version"] == "camp_dp_v25_controlled_train_v2"
    assert config["spawn_config"]["max_steps"] == CORPUS_STEPS
    assert config["seeds"]["scenario"] == EXPECTED_SEED
    assert config["protocol"]["sample_every_ticks"] == 1
    assert config["protocol"]["training_data_generation_authorized"] is True
    assert config["protocol"]["selector_training_execution_authorized"] is False
    assert config["protocol"]["fresh_b_opened"] is False
    assert config["protocol"]["context_mode"] == "no_v2i"
    assert config["selector"]["normalization_contract"].endswith(
        "scale,0,10)"
    )


def test_controlled_train_config_rejects_split_seed_or_outcome_drift() -> None:
    for mutate, match in (
        (lambda value: value["controlled_scenario"].update(split="fresh_b"), "split"),
        (lambda value: value["seeds"].update(scenario=25002), "seed"),
        (
            lambda value: value["controlled_scenario"].update(
                outcome_fields_consumed=["collision"]
            ),
            "outcome",
        ),
    ):
        config = copy.deepcopy(_config())
        mutate(config)
        with pytest.raises(ValueError, match=match):
            runner.validate_v25_controlled_train_config(config)


def _snapshot() -> dict:
    rows = [f"{index + 10:064x}" for index in range(8)]
    return {
        "schema_version": "v22_native_decision_snapshot_v1",
        "feature_payload": {
            "atom_matrix": np.ones((8, 14), dtype=np.float64).tolist(),
            "source_valid_mask": [True] * 8,
            "candidate_row_sha256": rows,
        },
        "sidecar": {
            "candidate_tensor_sha256_before": "a" * 64,
            "candidate_tensor_sha256_after": "a" * 64,
            "candidate0_sha256": rows[0],
            "normalized_atom_matrix_sha256": "d" * 64,
            "selected_index": 0,
            "score_contract": "score_k=clip(a_k/s,0,10)^T w",
            "tie_break_contract": "lowest_eligible_candidate_index",
            "scores": [0.0] * 8,
            "causal_input_sha256": "b" * 64,
            "physical_feasible_mask": [True] * 8,
            "source_valid_mask": [True] * 8,
            "all_k_high_risk": False,
        },
    }


def _context() -> dict:
    raw = {name: float(index) for index, name in enumerate(RAW_FEATURE_NAMES)}
    raw["traffic_signal_phase_remaining_s"] = 0.0
    complete = {name: True for name in RAW_FEATURE_NAMES}
    complete["traffic_signal_phase_remaining_s"] = False
    return {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "raw_context": raw,
        "source_complete": complete,
        "source_receipt": {
            "mode": "no_v2i",
            "phase_remaining_available": False,
            "regulatory_signal_mapped": True,
        },
    }


def test_combined_snapshot_keeps_context_causal_and_outcomes_absent() -> None:
    payload = combine_snapshot_context(
        snapshot=_snapshot(), context=_context(), case=_case(), tick_index=7
    )

    assert payload["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert tuple(payload["feature_payload"]["raw_context"]) == RAW_FEATURE_NAMES
    assert payload["sidecar"]["outcome_fields_consumed"] == []
    assert payload["sidecar"]["fresh_b_opened"] is False
    assert "collision" not in json.dumps(payload, sort_keys=True).lower()


def test_combined_snapshot_rejects_candidate_mutation() -> None:
    snapshot = _snapshot()
    snapshot["sidecar"]["candidate_tensor_sha256_after"] = "c" * 64

    with pytest.raises(ValueError, match="immutability"):
        combine_snapshot_context(
            snapshot=snapshot, context=_context(), case=_case(), tick_index=0
        )
