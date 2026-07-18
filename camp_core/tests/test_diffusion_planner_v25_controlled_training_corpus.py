from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_context import (
    CONTEXT_SCHEMA_VERSION,
    RAW_FEATURE_NAMES,
)
from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (
    MODEL_INPUT_SIGNAL_CACHE_RECEIPT_SCHEMA_VERSION,
    build_controlled_scenario_case,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
    NO_SIGNAL_CHAIN_SCHEMA_VERSION,
    build_no_signal_causal_atom_input,
    build_runtime_no_signal_receipt,
    build_semantic_clone_payload,
    canonical_json_sha256,
)
from scripts.integrations import run_diffusion_planner_dp_camp_v21_native as runner
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (
    CORPUS_STEPS,
    CORRECTED_GENERATION_SCALES,
    EXPECTED_SEED,
    SNAPSHOT_SCHEMA_VERSION,
    _file_sha256,
    build_capability_failure_allowlist,
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


def test_capability_allowlist_is_route_source_state_not_scenario_family() -> None:
    mapped_non_red = _case()
    mapped_non_red["signal_source_class"] = "mapped_signal"
    mapped_non_red["phase_authority_mode"] = "observe_same_tick_request"
    no_signal = copy.deepcopy(mapped_non_red)
    no_signal["scenario_id"] = "9" * 64
    no_signal["signal_source_class"] = "no_signal"
    no_signal["phase_authority_mode"] = None

    allowlist = build_capability_failure_allowlist([mapped_non_red, no_signal])
    assert allowlist == {
        mapped_non_red["scenario_id"]: {
            "family": "lead_vehicle_hard_brake",
            "source_class": "mapped_signal",
            "phase_authority_mode": "observe_same_tick_request",
            "reasons": ["mapped_current_signal_source_unavailable"],
        }
    }


def _snapshot() -> dict:
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    candidates[:, :, 2] = 1.0
    for index in range(8):
        candidates[index, :, 0] = float(index)
    default = np.array(candidates[0], copy=True)
    rows = [
        hashlib.sha256(np.ascontiguousarray(row).tobytes()).hexdigest()
        for row in candidates
    ]
    tensor_sha = hashlib.sha256(
        np.ascontiguousarray(candidates).tobytes()
    ).hexdigest()
    return {
        "schema_version": "v22_native_decision_snapshot_v1",
        "feature_payload": {
            "atom_matrix": np.ones((8, 14), dtype=np.float64).tolist(),
            "source_valid_mask": [True] * 8,
            "candidate_row_sha256": rows,
            "candidate_tensor": candidates.tolist(),
            "default_output": default.tolist(),
            "atom_source_valid_mask": np.ones((8, 14), dtype=np.bool_).tolist(),
            "atom_applicable_mask": np.ones((8, 14), dtype=np.bool_).tolist(),
        },
        "sidecar": {
            "candidate_tensor_sha256_before": tensor_sha,
            "candidate_tensor_sha256_after": tensor_sha,
            "candidate0_sha256": rows[0],
            "default_output_sha256": rows[0],
            "default_candidate0_identity": {
                "elementwise_equal": True,
                "max_abs_difference": 0.0,
                "default_output_sha256": rows[0],
                "candidate0_sha256": rows[0],
                "native_ranked_k8": False,
            },
            "normalized_atom_matrix_sha256": "d" * 64,
            "selected_index": 0,
            "selected_trajectory_sha256": rows[0],
            "score_contract": "score_k=clip(a_k/s,0,10)^T w",
            "tie_break_contract": "lowest_eligible_candidate_index",
            "scores": [0.0] * 8,
            "causal_input_sha256": "b" * 64,
            "physical_feasible_mask": [True] * 8,
            "source_valid_mask": [True] * 8,
            "all_k_high_risk": False,
        },
    }


def _no_signal_authority(case: dict, *, tick_index: int = 7) -> tuple[dict, dict]:
    route = np.column_stack((np.linspace(0.0, 100.0, 101), np.zeros(101)))
    semantic = build_semantic_clone_payload(
        case, route_polyline_world=route, stop_line_world=None
    )
    chain = {
        "schema_version": NO_SIGNAL_CHAIN_SCHEMA_VERSION,
        "scenario_id": case["scenario_id"],
        "route_identity_sha256": case["route_identity_sha256"],
        "source_map_sha256": case["source_map_sha256"],
        "route_lanelet_ids": list(case["route_spec"]["lanelet_ids"]),
        "route_geometry_sha256": canonical_json_sha256(
            {"route_polyline_local_m": semantic["route_polyline_local_m"]}
        ),
        "traffic_light_regulatory_element_ids": [],
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": canonical_json_sha256(semantic),
        "source_chain_sha256": "",
    }
    chain["source_chain_sha256"] = canonical_json_sha256(
        {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    )
    receipt = build_runtime_no_signal_receipt(
        chain,
        scenario_id=case["scenario_id"],
        tick_index=tick_index,
        decision_time_s=0.1 * tick_index,
    )
    return chain, receipt


def _combine_no_signal(snapshot: dict, *, tick_index: int = 0) -> dict:
    case = _case()
    chain, receipt = _no_signal_authority(case, tick_index=tick_index)
    case.update(
        {
            "no_signal_authority": chain,
            "canonical_semantic_clone_sha256": chain["semantic_clone_sha256"],
            "signal_source_class": "no_signal",
            "phase_authority_mode": None,
            "route_signal_source_artifact_root_sha256": "6" * 64,
            "route_signal_source_row_sha256": "7" * 64,
        }
    )
    for row in snapshot["feature_payload"]["atom_matrix"]:
        row[10] = 0.0
        row[12] = 0.0
    for row in snapshot["feature_payload"]["atom_applicable_mask"]:
        row[10] = False
        row[12] = False
    snapshot["sidecar"]["causal_signal_atom_input"] = (
        build_no_signal_causal_atom_input(chain, receipt)
    )
    return combine_snapshot_context(
        snapshot=snapshot,
        context=_context(),
        case=case,
        tick_index=tick_index,
        controlled_scene_receipt={
            "signal": {"source_receipt": receipt},
            "model_input_cache": _model_input_cache_receipt(
                case, tick_index=tick_index
            ),
        },
    )


def _model_input_cache_receipt(case: dict, *, tick_index: int) -> dict:
    digest = "8" * 64
    return {
        "schema_version": MODEL_INPUT_SIGNAL_CACHE_RECEIPT_SCHEMA_VERSION,
        "scenario_id": case["scenario_id"],
        "tick_index": tick_index,
        "signal_source_class": case["signal_source_class"],
        "phase_authority_mode": case["phase_authority_mode"],
        "scene_map_tl_sha256": digest,
        "model_cache_tl_sha256_before": digest,
        "model_cache_tl_sha256_after": digest,
        "model_route_lanes_tl_sha256": "9" * 64,
        "cache_matches_scene_after": True,
        "observe_cache_unchanged": True,
        "sync_applied_before_tensor_conversion": True,
        "future_schedule_consumed": False,
        "phase_remaining_available": False,
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
    case = _case()
    chain, receipt = _no_signal_authority(case)
    case["no_signal_authority"] = chain
    case["canonical_semantic_clone_sha256"] = chain["semantic_clone_sha256"]
    case["signal_source_class"] = "no_signal"
    case["phase_authority_mode"] = None
    case["route_signal_source_artifact_root_sha256"] = "6" * 64
    case["route_signal_source_row_sha256"] = "7" * 64
    snapshot = _snapshot()
    for row in snapshot["feature_payload"]["atom_matrix"]:
        row[10] = 0.0
        row[12] = 0.0
    for row in snapshot["feature_payload"]["atom_applicable_mask"]:
        row[10] = False
        row[12] = False
    snapshot["sidecar"]["causal_signal_atom_input"] = (
        build_no_signal_causal_atom_input(chain, receipt)
    )
    payload = combine_snapshot_context(
        snapshot=snapshot,
        context=_context(),
        case=case,
        tick_index=7,
        controlled_scene_receipt={
            "signal": {"source_receipt": receipt},
            "model_input_cache": _model_input_cache_receipt(case, tick_index=7),
        },
    )

    assert payload["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert tuple(payload["feature_payload"]["raw_context"]) == RAW_FEATURE_NAMES
    assert payload["sidecar"]["outcome_fields_consumed"] == []
    assert payload["sidecar"]["fresh_b_opened"] is False
    assert payload["sidecar"]["default_output_sha256"] == payload["sidecar"][
        "candidate0_sha256"
    ]
    assert payload["sidecar"]["candidate0_semantics"] == (
        "operational_default_alias_from_same_forward"
    )
    assert payload["sidecar"]["candidate0_independent_second_forward"] is False
    assert payload["feature_payload"]["physical_feasible_mask"] == [True] * 8
    assert payload["sidecar"]["canonical_semantic_clone_sha256"] == chain[
        "semantic_clone_sha256"
    ]
    assert payload["sidecar"]["generation_behavior_scale_sha256"] == _file_sha256(
        CORRECTED_GENERATION_SCALES
    )
    assert "collision" not in json.dumps(payload, sort_keys=True).lower()


def test_combined_snapshot_rejects_candidate_mutation() -> None:
    snapshot = _snapshot()
    snapshot["sidecar"]["candidate_tensor_sha256_after"] = "c" * 64

    with pytest.raises(ValueError, match="immutability"):
        combine_snapshot_context(
            snapshot=snapshot, context=_context(), case=_case(), tick_index=0
        )


def test_combined_snapshot_rejects_default_candidate0_identity_drift() -> None:
    snapshot = _snapshot()
    snapshot["sidecar"]["default_output_sha256"] = "e" * 64

    with pytest.raises(ValueError, match="score/mask invariant"):
        combine_snapshot_context(
            snapshot=snapshot, context=_context(), case=_case(), tick_index=0
        )


@pytest.mark.parametrize(
    "field,mutate",
    [
        ("atom", lambda snapshot: snapshot["feature_payload"]["atom_matrix"][0].__setitem__(0, "0.0")),
        ("candidate", lambda snapshot: snapshot["feature_payload"]["candidate_tensor"][0][0].__setitem__(0, True)),
        ("default", lambda snapshot: snapshot["feature_payload"]["default_output"][0].__setitem__(0, "0")),
        ("score", lambda snapshot: snapshot["sidecar"]["scores"].__setitem__(0, "0.0")),
    ],
)
def test_combined_snapshot_rejects_numeric_json_coercion(field: str, mutate) -> None:
    snapshot = _snapshot()
    mutate(snapshot)
    with pytest.raises(ValueError, match="finite native numbers"):
        combine_snapshot_context(
            snapshot=snapshot, context=_context(), case=_case(), tick_index=0
        )

    context = _context()
    context["raw_context"][RAW_FEATURE_NAMES[0]] = "0.0"
    with pytest.raises(ValueError, match="finite native numbers"):
        combine_snapshot_context(
            snapshot=_snapshot(), context=context, case=_case(), tick_index=0
        )


@pytest.mark.parametrize(
    "source_valid,physical,all_k_high_risk,passes",
    [
        ([True] * 7 + [False], [False] * 8, False, True),
        ([True] * 8, [False] * 8, True, True),
        ([True] * 8, [True] + [False] * 7, False, True),
        ([True] * 7 + [False], [False] * 8, True, False),
        ([True] * 8, [False] * 8, False, False),
        ([True] * 8, [True] + [False] * 7, True, False),
    ],
)
def test_combined_snapshot_freezes_all_k_high_risk_definition(
    source_valid: list[bool],
    physical: list[bool],
    all_k_high_risk: bool,
    passes: bool,
) -> None:
    snapshot = _snapshot()
    snapshot["feature_payload"]["source_valid_mask"] = source_valid
    snapshot["feature_payload"]["atom_source_valid_mask"] = [
        [value] * 14 for value in source_valid
    ]
    snapshot["feature_payload"]["atom_applicable_mask"] = [
        [value] * 14 for value in source_valid
    ]
    snapshot["sidecar"]["source_valid_mask"] = source_valid
    snapshot["sidecar"]["physical_feasible_mask"] = physical
    snapshot["sidecar"]["all_k_high_risk"] = all_k_high_risk

    if passes:
        payload = _combine_no_signal(snapshot, tick_index=0)
        assert payload["sidecar"]["all_k_high_risk"] is all_k_high_risk
    else:
        with pytest.raises(ValueError, match="score/mask invariant"):
            combine_snapshot_context(
                snapshot=snapshot, context=_context(), case=_case(), tick_index=0
            )


def test_combined_snapshot_rejects_non_bool_all_k_high_risk() -> None:
    snapshot = _snapshot()
    snapshot["sidecar"]["all_k_high_risk"] = 0
    with pytest.raises(ValueError, match="score/mask invariant"):
        combine_snapshot_context(
            snapshot=snapshot, context=_context(), case=_case(), tick_index=0
        )
