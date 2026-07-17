from __future__ import annotations

import copy

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_route_signal_authority import (
    MAPPED_SIGNAL_CHAIN_SCHEMA_VERSION,
    apply_controlled_same_tick_override,
    build_mapped_signal_runtime_receipt,
    observe_same_tick_request_phase,
    validate_mapped_signal_chain,
    validate_mapped_signal_runtime_receipt,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
    SEMANTIC_PAYLOAD_SCHEMA_VERSION,
    canonical_json_sha256,
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
