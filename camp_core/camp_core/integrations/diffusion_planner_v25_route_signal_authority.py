"""V25 family-independent route/tick traffic-signal source authority.

This module is deliberately independent of model, simulator, candidate, and
outcome code.  A mapped signal is a property of the certified route and the
current request tick, not of the controlled semantic family.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner_v25_semantic_authority import (
    canonical_json_sha256,
    validate_semantic_clone_payload,
)


MAPPED_SIGNAL_CHAIN_SCHEMA_VERSION = (
    "camp_dp_v25_family_independent_mapped_signal_source_chain_v1"
)
MAPPED_SIGNAL_RUNTIME_RECEIPT_SCHEMA_VERSION = (
    "camp_dp_v25_family_independent_current_signal_receipt_v1"
)
ROUTE_SOURCE_SUPPLEMENT_SCHEMA_VERSION = (
    "camp_dp_v25_formal_route_source_contract_supplement_v1"
)
PHASE_AUTHORITY_MODES = frozenset(
    {"controlled_same_tick_override", "observe_same_tick_request"}
)
CURRENT_PHASES = frozenset({"green", "yellow", "red"})
SAME_TICK_MAX_AGE_S = 1e-9
CURRENT_REQUEST_SOURCE_ID = "fixed_dp_current_request_route_map_signal_one_hot"
_SHA_CHARS = frozenset("0123456789abcdef")
_PHASE_CHANNELS = {"green": 8, "yellow": 9, "red": 10}
_SIGNAL_SLICE = slice(8, 13)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and not set(value) - _SHA_CHARS
    )


def _strict_int_list(value: Any, *, label: str, nonempty: bool) -> list[int]:
    if (
        not isinstance(value, list)
        or (nonempty and not value)
        or any(type(item) is not int for item in value)
        or len(value) != len(set(value))
    ):
        raise ValueError(f"{label} must be a unique native-integer list")
    return list(value)


def _strict_finite_number(value: Any, *, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be a finite native number")
    return float(value)


def _strict_json_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            _strict_json_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _strict_json_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def validate_mapped_signal_chain(chain: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the exact static route-level mapped-signal source receipt."""

    required = {
        "schema_version",
        "scenario_id",
        "route_identity_sha256",
        "source_map_sha256",
        "phase_authority_mode",
        "expected_current_phase",
        "formal_phase",
        "formal_mapped_source_required",
        "formal_route_mapped_traffic_light",
        "phase_remaining_available",
        "regulatory_element_ids",
        "physical_light_ids",
        "bulb_ids",
        "controlled_lanelet_ids",
        "route_lanelet_ids",
        "route_geometry_sha256",
        "stop_line_id",
        "stop_line_geometry_m",
        "stop_line_geometry_sha256",
        "stop_line_route_distance_m",
        "route_arc_m",
        "route_length_m",
        "route_tangent_world",
        "semantic_clone_payload",
        "semantic_clone_sha256",
        "source_chain_sha256",
    }
    if not isinstance(chain, Mapping) or set(chain) != required:
        raise ValueError("mapped-signal source-chain field set drifted")
    if chain.get("schema_version") != MAPPED_SIGNAL_CHAIN_SCHEMA_VERSION:
        raise ValueError("mapped-signal source-chain schema drifted")
    for key in (
        "scenario_id",
        "route_identity_sha256",
        "source_map_sha256",
        "route_geometry_sha256",
        "stop_line_geometry_sha256",
        "semantic_clone_sha256",
        "source_chain_sha256",
    ):
        if not _is_sha256(chain.get(key)):
            raise ValueError(f"mapped-signal {key} is invalid")

    mode = chain.get("phase_authority_mode")
    expected_phase = chain.get("expected_current_phase")
    formal_phase = chain.get("formal_phase")
    formal_required = chain.get("formal_mapped_source_required")
    if mode not in PHASE_AUTHORITY_MODES:
        raise ValueError("mapped-signal phase authority mode is invalid")
    if chain.get("phase_remaining_available") is not False:
        raise ValueError("no-V2I mapped-signal authority exposed phase remaining")
    if chain.get("formal_route_mapped_traffic_light") is not True:
        raise ValueError("formal route mapped-signal authority drifted")
    if mode == "controlled_same_tick_override":
        if (
            expected_phase not in CURRENT_PHASES
            or formal_phase != expected_phase
            or formal_required is not True
        ):
            raise ValueError("controlled signal override contract drifted")
    elif (
        expected_phase is not None
        or formal_phase != "none"
        or formal_required is not False
    ):
        raise ValueError("observed signal request contract drifted")

    regulatory = _strict_int_list(
        chain.get("regulatory_element_ids"),
        label="regulatory IDs",
        nonempty=True,
    )
    physical = _strict_int_list(
        chain.get("physical_light_ids"), label="physical-light IDs", nonempty=True
    )
    bulbs = _strict_int_list(chain.get("bulb_ids"), label="bulb IDs", nonempty=True)
    controlled = _strict_int_list(
        chain.get("controlled_lanelet_ids"),
        label="controlled-lanelet IDs",
        nonempty=True,
    )
    route = _strict_int_list(
        chain.get("route_lanelet_ids"), label="route-lanelet IDs", nonempty=True
    )
    if len(regulatory) != 1 or not set(controlled).issubset(route):
        raise ValueError("mapped-signal regulatory/route relation is ambiguous")

    if type(chain.get("stop_line_id")) is not int:
        raise ValueError("mapped-signal stop-line ID is invalid")
    stop_raw = chain.get("stop_line_geometry_m")
    if not isinstance(stop_raw, list):
        raise ValueError("mapped-signal stop-line geometry is not JSON-native")
    for row in stop_raw:
        if (
            not isinstance(row, list)
            or len(row) != 2
            or any(type(item) not in (int, float) for item in row)
        ):
            raise ValueError("mapped-signal stop-line geometry type drifted")
    stop = np.asarray(stop_raw, dtype=np.float64)
    if (
        stop.ndim != 2
        or stop.shape[1] != 2
        or len(stop) < 2
        or not np.isfinite(stop).all()
        or float(np.linalg.norm(stop[-1] - stop[0])) <= 1e-6
        or chain["stop_line_geometry_sha256"]
        != canonical_json_sha256(stop.tolist())
    ):
        raise ValueError("mapped-signal stop-line source is invalid")

    distance = _strict_finite_number(
        chain.get("stop_line_route_distance_m"), label="stop-line route distance"
    )
    arc = _strict_finite_number(chain.get("route_arc_m"), label="route arc")
    length = _strict_finite_number(chain.get("route_length_m"), label="route length")
    if (
        distance < 0.0
        or distance > 0.1
        or arc < -1e-8
        or length <= 0.0
        or arc > length + 1e-8
    ):
        raise ValueError("mapped-signal stop-line/route-arc relation is invalid")
    tangent_raw = chain.get("route_tangent_world")
    if (
        not isinstance(tangent_raw, list)
        or len(tangent_raw) != 2
        or any(type(item) not in (int, float) for item in tangent_raw)
    ):
        raise ValueError("mapped-signal route tangent type drifted")
    tangent = np.asarray(tangent_raw, dtype=np.float64)
    if not np.isfinite(tangent).all() or not np.isclose(
        np.linalg.norm(tangent), 1.0, rtol=0.0, atol=1e-6
    ):
        raise ValueError("mapped-signal route tangent is invalid")

    semantic = validate_semantic_clone_payload(chain.get("semantic_clone_payload"))
    expected_semantic_signal = (
        {
            "current_phase": expected_phase,
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
    if (
        "stop_line_local_m" not in semantic
        or semantic.get("signal") != expected_semantic_signal
        or chain["route_geometry_sha256"]
        != canonical_json_sha256(
            {
                "route_polyline_local_m": semantic["route_polyline_local_m"],
                "stop_line_local_m": semantic["stop_line_local_m"],
            }
        )
        or chain["semantic_clone_sha256"] != canonical_json_sha256(semantic)
    ):
        raise ValueError("mapped-signal semantic/source-mode binding drifted")
    without_hash = {
        key: value for key, value in chain.items() if key != "source_chain_sha256"
    }
    if chain["source_chain_sha256"] != canonical_json_sha256(without_hash):
        raise ValueError("mapped-signal source-chain hash mismatch")
    return dict(chain)


def _validate_tensor(
    tensor: Any, lanelet_ids: Sequence[int], *, label: str
) -> tuple[np.ndarray, list[int]]:
    if (
        not isinstance(lanelet_ids, (list, tuple))
        or any(type(value) is not int for value in lanelet_ids)
        or len(set(lanelet_ids)) != len(lanelet_ids)
    ):
        raise ValueError(f"{label} lanelet IDs are invalid")
    values = np.asarray(tensor)
    if (
        values.ndim != 3
        or values.shape[0] != len(lanelet_ids)
        or values.shape[1] < 1
        or values.shape[2] < 13
        or values.dtype.kind not in "iuf"
        or not np.isfinite(values).all()
    ):
        raise ValueError(f"{label} signal tensor is invalid")
    return values.astype(np.float64, copy=False), list(lanelet_ids)


def _decode_controlled_rows(
    tensor: np.ndarray,
    lanelet_ids: Sequence[int],
    controlled_lanelet_ids: set[int],
    *,
    label: str,
) -> tuple[list[str], list[int], list[dict[str, Any]]]:
    phases: list[str] = []
    observed_ids: list[int] = []
    saved_rows: list[dict[str, Any]] = []
    for index, lanelet_id in enumerate(lanelet_ids):
        if lanelet_id not in controlled_lanelet_ids:
            continue
        state = np.asarray(tensor[index, :, _SIGNAL_SLICE], dtype=np.float64)
        active = np.any(np.abs(state) > 1e-12, axis=1)
        if not np.any(active):
            raise ValueError(f"{label} controlled lanelet has no current signal source")
        active_state = state[active]
        valid = np.zeros(len(active_state), dtype=bool)
        row_phases: list[str] = []
        for phase, column in _PHASE_CHANNELS.items():
            local = column - _SIGNAL_SLICE.start
            matches = np.isclose(active_state[:, local], 1.0, rtol=0.0, atol=1e-8)
            other = np.delete(active_state, local, axis=1)
            matches &= np.all(np.isclose(other, 0.0, rtol=0.0, atol=1e-8), axis=1)
            valid |= matches
            row_phases.extend([phase] * int(matches.sum()))
        if not np.all(valid) or len(set(row_phases)) != 1:
            raise ValueError(
                f"{label} controlled lanelet phase is missing, multi-hot, or unknown"
            )
        phases.append(row_phases[0])
        observed_ids.append(lanelet_id)
        saved_rows.append(
            {
                "lanelet_id": lanelet_id,
                "signal_channels_8_12": state.tolist(),
            }
        )
    return phases, observed_ids, saved_rows


def observe_same_tick_request_phase(
    chain: Mapping[str, Any],
    *,
    route_tensor: Any,
    route_lanelet_ids: Sequence[int],
    map_tensor: Any,
    map_lanelet_ids: Sequence[int],
) -> dict[str, Any]:
    """Read exactly one current phase from route/map request tensors."""

    validated = validate_mapped_signal_chain(chain)
    route, route_ids = _validate_tensor(
        route_tensor, route_lanelet_ids, label="route request"
    )
    mapped, map_ids = _validate_tensor(map_tensor, map_lanelet_ids, label="map request")
    controlled = set(validated["controlled_lanelet_ids"])
    route_phases, observed_route_ids, route_rows = _decode_controlled_rows(
        route, route_ids, controlled, label="route request"
    )
    map_phases, observed_map_ids, map_rows = _decode_controlled_rows(
        mapped, map_ids, controlled, label="map request"
    )
    phases = route_phases + map_phases
    if not phases or len(set(phases)) != 1:
        raise ValueError("route/map current signal phases are absent or inconsistent")
    return {
        "current_phase": phases[0],
        "observed_route_lanelet_ids": observed_route_ids,
        "observed_map_lanelet_ids": observed_map_ids,
        "route_signal_rows": route_rows,
        "map_signal_rows": map_rows,
        "route_signal_tensor_sha256": canonical_json_sha256(route_rows),
        "map_signal_tensor_sha256": canonical_json_sha256(map_rows),
    }


def apply_controlled_same_tick_override(
    chain: Mapping[str, Any],
    *,
    route_tensor: Any,
    route_lanelet_ids: Sequence[int],
    map_tensor: Any,
    map_lanelet_ids: Sequence[int],
) -> tuple[np.ndarray, np.ndarray]:
    """Apply only the frozen current-tick phase to copies of request tensors."""

    validated = validate_mapped_signal_chain(chain)
    if validated["phase_authority_mode"] != "controlled_same_tick_override":
        raise ValueError("signal override is not authorized for observed-request mode")
    route, route_ids = _validate_tensor(
        route_tensor, route_lanelet_ids, label="route request"
    )
    mapped, map_ids = _validate_tensor(map_tensor, map_lanelet_ids, label="map request")
    route = route.copy()
    mapped = mapped.copy()
    controlled = set(validated["controlled_lanelet_ids"])
    channel = _PHASE_CHANNELS[validated["expected_current_phase"]]
    applied = 0
    for values, ids in ((route, route_ids), (mapped, map_ids)):
        for index, lanelet_id in enumerate(ids):
            if lanelet_id not in controlled:
                continue
            if not np.any(np.abs(values[index, :, _SIGNAL_SLICE]) > 1e-12):
                raise ValueError("controlled signal row lacks a current source slot")
            values[index, :, _SIGNAL_SLICE] = 0.0
            values[index, :, channel] = 1.0
            applied += 1
    if applied == 0:
        raise ValueError("controlled signal override found no certified request row")
    observed = observe_same_tick_request_phase(
        validated,
        route_tensor=route,
        route_lanelet_ids=route_ids,
        map_tensor=mapped,
        map_lanelet_ids=map_ids,
    )
    if observed["current_phase"] != validated["expected_current_phase"]:
        raise ValueError("controlled signal override did not read back same tick")
    return route, mapped


def build_mapped_signal_runtime_receipt(
    chain: Mapping[str, Any],
    *,
    tick_index: int,
    decision_timestamp_s: float,
    source_timestamp_s: float,
    route_tensor: Any,
    route_lanelet_ids: Sequence[int],
    map_tensor: Any,
    map_lanelet_ids: Sequence[int],
) -> dict[str, Any]:
    """Build the exact same-tick mapped-signal receipt from current tensors."""

    validated = validate_mapped_signal_chain(chain)
    if type(tick_index) is not int or tick_index < 0:
        raise ValueError("mapped-signal tick index is invalid")
    decision = _strict_finite_number(
        decision_timestamp_s, label="decision timestamp"
    )
    source = _strict_finite_number(source_timestamp_s, label="source timestamp")
    age = decision - source
    if decision < 0.0 or source < 0.0 or age < -1e-12 or age > SAME_TICK_MAX_AGE_S:
        raise ValueError("mapped-signal current source is stale or future-dated")
    observed = observe_same_tick_request_phase(
        validated,
        route_tensor=route_tensor,
        route_lanelet_ids=route_lanelet_ids,
        map_tensor=map_tensor,
        map_lanelet_ids=map_lanelet_ids,
    )
    phase = observed["current_phase"]
    if (
        validated["phase_authority_mode"] == "controlled_same_tick_override"
        and phase != validated["expected_current_phase"]
    ):
        raise ValueError("controlled current phase does not match frozen override")
    return {
        "schema_version": MAPPED_SIGNAL_RUNTIME_RECEIPT_SCHEMA_VERSION,
        "scenario_id": validated["scenario_id"],
        "tick_index": tick_index,
        "phase_authority_mode": validated["phase_authority_mode"],
        "current_phase": phase,
        "decision_timestamp_s": decision,
        "source_timestamp_s": source,
        "source_age_s": age,
        "freshness": "same_tick",
        "source_id": CURRENT_REQUEST_SOURCE_ID,
        "regulatory_element_id": validated["regulatory_element_ids"][0],
        "physical_light_ids": list(validated["physical_light_ids"]),
        "bulb_ids": list(validated["bulb_ids"]),
        "controlled_lanelet_ids": list(validated["controlled_lanelet_ids"]),
        "stop_line_id": validated["stop_line_id"],
        "stop_line_geometry_sha256": validated["stop_line_geometry_sha256"],
        "route_geometry_sha256": validated["route_geometry_sha256"],
        "route_arc_m": validated["route_arc_m"],
        "source_chain_sha256": validated["source_chain_sha256"],
        "observed_route_lanelet_ids": observed["observed_route_lanelet_ids"],
        "observed_map_lanelet_ids": observed["observed_map_lanelet_ids"],
        "route_signal_tensor_sha256": observed["route_signal_tensor_sha256"],
        "map_signal_tensor_sha256": observed["map_signal_tensor_sha256"],
        "phase_remaining_available": False,
        "source_valid": True,
        "applicable": phase == "red",
    }


def validate_mapped_signal_runtime_receipt(
    receipt: Mapping[str, Any],
    chain: Mapping[str, Any],
    *,
    route_tensor: Any,
    route_lanelet_ids: Sequence[int],
    map_tensor: Any,
    map_lanelet_ids: Sequence[int],
) -> dict[str, Any]:
    required = {
        "schema_version",
        "scenario_id",
        "tick_index",
        "phase_authority_mode",
        "current_phase",
        "decision_timestamp_s",
        "source_timestamp_s",
        "source_age_s",
        "freshness",
        "source_id",
        "regulatory_element_id",
        "physical_light_ids",
        "bulb_ids",
        "controlled_lanelet_ids",
        "stop_line_id",
        "stop_line_geometry_sha256",
        "route_geometry_sha256",
        "route_arc_m",
        "source_chain_sha256",
        "observed_route_lanelet_ids",
        "observed_map_lanelet_ids",
        "route_signal_tensor_sha256",
        "map_signal_tensor_sha256",
        "phase_remaining_available",
        "source_valid",
        "applicable",
    }
    if not isinstance(receipt, Mapping) or set(receipt) != required:
        raise ValueError("mapped-signal runtime receipt field set drifted")
    if receipt.get("schema_version") != MAPPED_SIGNAL_RUNTIME_RECEIPT_SCHEMA_VERSION:
        raise ValueError("mapped-signal runtime receipt schema drifted")
    expected = build_mapped_signal_runtime_receipt(
        chain,
        tick_index=receipt.get("tick_index"),
        decision_timestamp_s=receipt.get("decision_timestamp_s"),
        source_timestamp_s=receipt.get("source_timestamp_s"),
        route_tensor=route_tensor,
        route_lanelet_ids=route_lanelet_ids,
        map_tensor=map_tensor,
        map_lanelet_ids=map_lanelet_ids,
    )
    if not _strict_json_equal(dict(receipt), expected):
        raise ValueError("mapped-signal runtime receipt value/type drifted")
    return expected
