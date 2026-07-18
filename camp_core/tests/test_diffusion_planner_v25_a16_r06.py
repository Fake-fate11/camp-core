from __future__ import annotations

import copy

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_route_signal_authority import (
    MAPPED_SIGNAL_CHAIN_SCHEMA_VERSION,
    apply_controlled_same_tick_override,
    build_mapped_signal_causal_atom_input,
    build_mapped_signal_runtime_receipt,
    observe_same_tick_request_phase,
    validate_mapped_signal_chain,
    validate_mapped_signal_runtime_receipt,
)
from scripts.integrations import (
    review_diffusion_planner_v25_controlled_training_corpus as corpus_reviewer,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
    SEMANTIC_PAYLOAD_SCHEMA_VERSION,
    canonical_json_sha256,
)
from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (
    MODEL_INPUT_SIGNAL_CACHE_RECEIPT_SCHEMA_VERSION,
)


def _semantic(mode: str, phase: str | None) -> dict:
    signal = (
        {
            "current_phase": phase,
            "mapped_source_required": True,
            "source_mode": "no_v2i",
        }
        if mode == "controlled_same_tick_override"
        else {
            "current_phase": "none",
            "mapped_source_required": False,
            "source_mode": "no_v2i",
        }
    )
    return {
        "schema_version": SEMANTIC_PAYLOAD_SCHEMA_VERSION,
        "family": "red_light_phase_timing" if phase else "lead_vehicle_hard_brake",
        "tier": "high_risk",
        "semantic_variant": "fixture",
        "parameters": {},
        "actors": [],
        "signal": signal,
        "route_polyline_local_m": [[float(i), 0.0] for i in range(64)],
        "stop_line_local_m": [[10.0, -1.0], [10.0, 1.0]],
    }


def _chain(
    mode: str = "observe_same_tick_request", phase: str | None = None
) -> dict:
    semantic = _semantic(mode, phase)
    stop = [[10.0, -1.0], [10.0, 1.0]]
    payload = {
        "schema_version": MAPPED_SIGNAL_CHAIN_SCHEMA_VERSION,
        "scenario_id": "1" * 64,
        "route_identity_sha256": "2" * 64,
        "source_map_sha256": "3" * 64,
        "phase_authority_mode": mode,
        "expected_current_phase": phase,
        "formal_phase": phase if phase else "none",
        "formal_mapped_source_required": phase is not None,
        "formal_route_mapped_traffic_light": True,
        "phase_remaining_available": False,
        "regulatory_element_ids": [101],
        "physical_light_ids": [201],
        "bulb_ids": [301, 302, 303],
        "controlled_lanelet_ids": [11],
        "route_lanelet_ids": [10, 11],
        "route_geometry_sha256": canonical_json_sha256(
            {
                "route_polyline_local_m": semantic["route_polyline_local_m"],
                "stop_line_local_m": semantic["stop_line_local_m"],
            }
        ),
        "stop_line_id": 401,
        "stop_line_geometry_m": stop,
        "stop_line_geometry_sha256": canonical_json_sha256(stop),
        "stop_line_route_distance_m": 0.01,
        "route_arc_m": 10.0,
        "route_length_m": 63.0,
        "route_tangent_world": [1.0, 0.0],
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": canonical_json_sha256(semantic),
        "source_chain_sha256": "",
    }
    payload["source_chain_sha256"] = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "source_chain_sha256"}
    )
    return payload


def _tensors(phase: str = "green") -> tuple[np.ndarray, np.ndarray]:
    route = np.zeros((2, 20, 33), dtype=np.float64)
    mapped = np.zeros((2, 20, 33), dtype=np.float64)
    column = {"green": 8, "yellow": 9, "red": 10}[phase]
    route[1, :, column] = 1.0
    mapped[0, :, column] = 1.0
    return route, mapped


def test_observe_mode_reads_same_tick_route_and_map_without_mutation() -> None:
    chain = validate_mapped_signal_chain(_chain())
    route, mapped = _tensors("green")
    route_before = route.copy()
    map_before = mapped.copy()
    observed = observe_same_tick_request_phase(
        chain,
        route_tensor=route,
        route_lanelet_ids=[10, 11],
        map_tensor=mapped,
        map_lanelet_ids=[11, 12],
    )
    assert observed["current_phase"] == "green"
    assert observed["observed_route_lanelet_ids"] == [11]
    assert observed["observed_map_lanelet_ids"] == [11]
    assert np.array_equal(route, route_before)
    assert np.array_equal(mapped, map_before)


def test_controlled_override_is_copy_only_and_reads_back_frozen_phase() -> None:
    chain = validate_mapped_signal_chain(
        _chain("controlled_same_tick_override", "red")
    )
    route, mapped = _tensors("green")
    changed_route, changed_map = apply_controlled_same_tick_override(
        chain,
        route_tensor=route,
        route_lanelet_ids=[10, 11],
        map_tensor=mapped,
        map_lanelet_ids=[11, 12],
    )
    assert np.all(changed_route[1, :, 10] == 1.0)
    assert np.all(changed_map[0, :, 10] == 1.0)
    assert np.all(route[1, :, 8] == 1.0)
    receipt = build_mapped_signal_runtime_receipt(
        chain,
        tick_index=0,
        decision_timestamp_s=0.0,
        source_timestamp_s=0.0,
        route_tensor=changed_route,
        route_lanelet_ids=[10, 11],
        map_tensor=changed_map,
        map_lanelet_ids=[11, 12],
    )
    assert receipt["current_phase"] == "red"
    assert receipt["source_valid"] is True
    assert receipt["applicable"] is True
    assert receipt["phase_remaining_available"] is False


@pytest.mark.parametrize(
    ("phase", "applicable"),
    [("green", False), ("yellow", False), ("red", True)],
)
def test_mapped_phase_is_source_valid_and_only_red_is_applicable(
    phase: str, applicable: bool
) -> None:
    chain = _chain()
    route, mapped = _tensors(phase)
    receipt = build_mapped_signal_runtime_receipt(
        chain,
        tick_index=7,
        decision_timestamp_s=0.7,
        source_timestamp_s=0.7,
        route_tensor=route,
        route_lanelet_ids=[10, 11],
        map_tensor=mapped,
        map_lanelet_ids=[11, 12],
    )
    assert receipt["current_phase"] == phase
    assert receipt["source_valid"] is True
    assert receipt["applicable"] is applicable
    assert receipt["freshness"] == "same_tick"
    assert receipt["source_id"] == (
        "fixed_dp_current_request_route_map_signal_one_hot"
    )
    assert validate_mapped_signal_runtime_receipt(
        receipt,
        chain,
        route_tensor=route,
        route_lanelet_ids=[10, 11],
        map_tensor=mapped,
        map_lanelet_ids=[11, 12],
    ) == receipt


@pytest.mark.parametrize(
    "mutation",
    [
        lambda c: c.update(phase_authority_mode="red_family"),
        lambda c: c.update(expected_current_phase="red"),
        lambda c: c.update(formal_route_mapped_traffic_light=False),
        lambda c: c.update(phase_remaining_available=True),
        lambda c: c.update(future_schedule=["red"]),
        lambda c: c.update(regulatory_element_ids=[101, 102]),
        lambda c: c.update(controlled_lanelet_ids=[99]),
    ],
)
def test_static_authority_rejects_mode_alias_leakage_and_wrong_chain(mutation) -> None:
    changed = copy.deepcopy(_chain())
    mutation(changed)
    changed["source_chain_sha256"] = canonical_json_sha256(
        {key: value for key, value in changed.items() if key != "source_chain_sha256"}
    )
    with pytest.raises(ValueError):
        validate_mapped_signal_chain(changed)


@pytest.mark.parametrize("bad", ["missing", "multi", "unknown", "conflict"])
def test_observed_request_fails_closed_on_invalid_or_conflicting_phase(bad: str) -> None:
    chain = _chain()
    route, mapped = _tensors("green")
    if bad == "missing":
        route[1, :, 8:13] = 0.0
    elif bad == "multi":
        route[1, :, 9] = 1.0
    elif bad == "unknown":
        route[1, :, 8:13] = 0.0
        route[1, :, 12] = 1.0
    else:
        mapped[0, :, 8:13] = 0.0
        mapped[0, :, 10] = 1.0
    with pytest.raises(ValueError):
        observe_same_tick_request_phase(
            chain,
            route_tensor=route,
            route_lanelet_ids=[10, 11],
            map_tensor=mapped,
            map_lanelet_ids=[11, 12],
        )


@pytest.mark.parametrize(
    ("source_time", "decision_time"),
    [(0.0, 0.1), (0.2, 0.1)],
)
def test_runtime_receipt_rejects_stale_or_future_timestamp(
    source_time: float, decision_time: float
) -> None:
    route, mapped = _tensors("green")
    with pytest.raises(ValueError):
        build_mapped_signal_runtime_receipt(
            _chain(),
            tick_index=1,
            decision_timestamp_s=decision_time,
            source_timestamp_s=source_time,
            route_tensor=route,
            route_lanelet_ids=[10, 11],
            map_tensor=mapped,
            map_lanelet_ids=[11, 12],
        )


def test_runtime_receipt_rejects_wrong_lanelet_and_unknown_field() -> None:
    route, mapped = _tensors("red")
    with pytest.raises(ValueError):
        build_mapped_signal_runtime_receipt(
            _chain(),
            tick_index=0,
            decision_timestamp_s=0.0,
            source_timestamp_s=0.0,
            route_tensor=route,
            route_lanelet_ids=[10, 99],
            map_tensor=mapped,
            map_lanelet_ids=[98, 12],
        )
    receipt = build_mapped_signal_runtime_receipt(
        _chain(),
        tick_index=0,
        decision_timestamp_s=0.0,
        source_timestamp_s=0.0,
        route_tensor=route,
        route_lanelet_ids=[10, 11],
        map_tensor=mapped,
        map_lanelet_ids=[11, 12],
    )
    receipt["schedule"] = ["green", "red"]
    with pytest.raises(ValueError):
        validate_mapped_signal_runtime_receipt(
            receipt,
            _chain(),
            route_tensor=route,
            route_lanelet_ids=[10, 11],
            map_tensor=mapped,
            map_lanelet_ids=[11, 12],
        )


def test_observe_mode_accepts_map_only_when_route_tensor_has_no_controlled_row() -> None:
    route, mapped = _tensors("yellow")
    observed = observe_same_tick_request_phase(
        _chain(),
        route_tensor=route[:1],
        route_lanelet_ids=[10],
        map_tensor=mapped,
        map_lanelet_ids=[11, 12],
    )
    assert observed["current_phase"] == "yellow"
    assert observed["observed_route_lanelet_ids"] == []
    assert observed["observed_map_lanelet_ids"] == [11]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.update(source_id="scenario_schedule"),
        lambda r: r.update(tick_index=False),
        lambda r: r.update(source_valid=1),
        lambda r: r.update(applicable=0),
    ],
)
def test_runtime_receipt_rejects_source_alias_and_type_smuggling(mutation) -> None:
    route, mapped = _tensors("red")
    receipt = build_mapped_signal_runtime_receipt(
        _chain(),
        tick_index=0,
        decision_timestamp_s=0.0,
        source_timestamp_s=0.0,
        route_tensor=route,
        route_lanelet_ids=[10, 11],
        map_tensor=mapped,
        map_lanelet_ids=[11, 12],
    )
    mutation(receipt)
    with pytest.raises(ValueError):
        validate_mapped_signal_runtime_receipt(
            receipt,
            _chain(),
            route_tensor=route,
            route_lanelet_ids=[10, 11],
            map_tensor=mapped,
            map_lanelet_ids=[11, 12],
        )


def _snapshot_signal_sidecar(phase: str = "green", tick_index: int = 7) -> dict:
    chain = _chain()
    route, mapped = _tensors(phase)
    observed = observe_same_tick_request_phase(
        chain,
        route_tensor=route,
        route_lanelet_ids=[10, 11],
        map_tensor=mapped,
        map_lanelet_ids=[11, 12],
    )
    timestamp = 0.1 * tick_index
    receipt = build_mapped_signal_runtime_receipt(
        chain,
        tick_index=tick_index,
        decision_timestamp_s=timestamp,
        source_timestamp_s=timestamp,
        route_tensor=route,
        route_lanelet_ids=[10, 11],
        map_tensor=mapped,
        map_lanelet_ids=[11, 12],
    )
    causal = build_mapped_signal_causal_atom_input(
        chain,
        receipt,
        route_tensor=route,
        route_lanelet_ids=[10, 11],
        map_tensor=mapped,
        map_lanelet_ids=[11, 12],
        ego_position_world_m=[0.0, 0.0],
        ego_heading_rad=0.0,
    )
    evidence = {
        "schema_version": "camp_dp_v25_production_signal_tensor_evidence_v2",
        "tick_index": tick_index,
        "decision_timestamp_s": timestamp,
        "source_timestamp_s": timestamp,
        "route_signal_rows": observed["route_signal_rows"],
        "map_signal_rows": observed["map_signal_rows"],
        "current_phase": phase,
        "route_signal_tensor_sha256": observed["route_signal_tensor_sha256"],
        "map_signal_tensor_sha256": observed["map_signal_tensor_sha256"],
        "future_schedule_consumed": False,
        "phase_remaining_available": False,
    }
    return {
        "context_source_receipt": {
            "mode": "no_v2i",
            "phase_remaining_available": False,
            "regulatory_signal_mapped": True,
        },
        "signal_source_class": "mapped_signal",
        "phase_authority_mode": "observe_same_tick_request",
        "controlled_signal_source_receipt": receipt,
        "controlled_signal_tensor_evidence": evidence,
        "causal_signal_atom_input": causal,
        "scenario_id": chain["scenario_id"],
        "tick_index": tick_index,
        "controlled_model_input_cache_receipt": {
            "schema_version": MODEL_INPUT_SIGNAL_CACHE_RECEIPT_SCHEMA_VERSION,
            "scenario_id": chain["scenario_id"],
            "tick_index": tick_index,
            "signal_source_class": "mapped_signal",
            "phase_authority_mode": "observe_same_tick_request",
            "scene_map_tl_sha256": "1" * 64,
            "model_cache_tl_sha256_before": "1" * 64,
            "model_cache_tl_sha256_after": "1" * 64,
            "model_route_lanes_tl_sha256": "2" * 64,
            "cache_matches_scene_after": True,
            "observe_cache_unchanged": True,
            "sync_applied_before_tensor_conversion": True,
            "future_schedule_consumed": False,
            "phase_remaining_available": False,
        },
    }


def test_snapshot_reviewer_independently_recomputes_mapped_signal_rows() -> None:
    sidecar = _snapshot_signal_sidecar("green", 7)
    corpus_reviewer._validate_context_and_signal_receipts(sidecar)


@pytest.mark.parametrize(
    "mutation",
    [
        "stale",
        "future",
        "multihot",
        "missing",
        "conflict",
        "phase_transition_mismatch",
    ],
)
def test_snapshot_reviewer_rejects_timestamp_and_phase_evidence_drift(
    mutation: str,
) -> None:
    sidecar = _snapshot_signal_sidecar("green", 7)
    receipt = sidecar["controlled_signal_source_receipt"]
    evidence = sidecar["controlled_signal_tensor_evidence"]
    if mutation == "stale":
        receipt["source_timestamp_s"] = 0.6
        receipt["source_age_s"] = 0.1
    elif mutation == "future":
        receipt["source_timestamp_s"] = 0.8
        receipt["source_age_s"] = -0.1
    elif mutation == "multihot":
        evidence["route_signal_rows"][0]["signal_channels_8_12"][0][1] = 1.0
    elif mutation == "missing":
        evidence["route_signal_rows"] = []
        evidence["map_signal_rows"] = []
    elif mutation == "conflict":
        rows = evidence["map_signal_rows"][0]["signal_channels_8_12"]
        for row in rows:
            row[0] = 0.0
            row[2] = 1.0
    else:
        evidence["current_phase"] = "yellow"
    with pytest.raises(ValueError):
        corpus_reviewer._validate_context_and_signal_receipts(sidecar)


@pytest.mark.parametrize("mutation", ["duplicate_lanelet", "one_plus_epsilon"])
def test_snapshot_reviewer_rejects_lanelet_alias_and_strict_one_hot_drift(
    mutation: str,
) -> None:
    sidecar = _snapshot_signal_sidecar("green", 7)
    evidence = sidecar["controlled_signal_tensor_evidence"]
    receipt = sidecar["controlled_signal_source_receipt"]
    if mutation == "duplicate_lanelet":
        duplicate = copy.deepcopy(evidence["route_signal_rows"][0])
        evidence["route_signal_rows"].append(duplicate)
        receipt["observed_route_lanelet_ids"].append(
            receipt["observed_route_lanelet_ids"][0]
        )
    else:
        evidence["route_signal_rows"][0]["signal_channels_8_12"][0][0] = (
            1.0 + 2.0e-8
        )
    with pytest.raises(ValueError):
        corpus_reviewer._validate_context_and_signal_receipts(sidecar)


def test_snapshot_route_source_row_binding_rejects_cross_identity_receipt_swap() -> None:
    sidecar = _snapshot_signal_sidecar("green", 7)
    sidecar.update(
        {
            "family": "lead_vehicle_hard_brake",
            "tier": "easy",
            "seed": 25001,
            "source_map_sha256": "3" * 64,
            "route_identity_sha256": "2" * 64,
            "route_signal_source_artifact_root_sha256": "4" * 64,
        }
    )
    chain = _chain()
    row = {
        "scenario_id": "1" * 64,
        "formal_case_sha256": "5" * 64,
        "runner_eligible": True,
        "retention_role": "executable",
        "family": "lead_vehicle_hard_brake",
        "tier": "easy",
        "seed": 25001,
        "source_map_sha256": "3" * 64,
        "route_identity_sha256": "2" * 64,
        "actual_mapped_signal": True,
        "id_free_tensor_layout": {},
        "source_class": "mapped_signal",
        "phase_authority_mode": "observe_same_tick_request",
        "source_chain": chain,
        "runtime_receipt": {},
        "tensor_evidence": {},
    }
    sidecar["route_signal_source_row_sha256"] = corpus_reviewer._oracle_sha256(row)
    rows = {row["scenario_id"]: row}
    corpus_reviewer._validate_route_source_row_binding(
        sidecar, source_rows=rows, source_root_sha256="4" * 64
    )

    swapped = copy.deepcopy(sidecar)
    swapped["controlled_signal_source_receipt"]["scenario_id"] = "6" * 64
    with pytest.raises(ValueError, match="swapped"):
        corpus_reviewer._validate_route_source_row_binding(
            swapped, source_rows=rows, source_root_sha256="4" * 64
        )
