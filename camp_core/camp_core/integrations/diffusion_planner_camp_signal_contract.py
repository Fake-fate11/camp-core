"""Neutral CAMP validation for current-tick signal atom inputs.

The protocol literals deliberately remain compatible with the frozen CAMP
atom representation.  This module owns only finite geometry, same-tick
receipt binding, and typed source-state validation; it has no V25 release,
opening, CAS, or artifact-policy dependency.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np


# Kept byte-compatible with pre-existing saved context and atom receipts.
CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION = "camp_dp_v25_causal_signal_atom_input_v2"
_PHASES = frozenset({"green", "yellow", "red"})
_SOURCE_STATES = frozenset({"available", "not_applicable", "unavailable"})


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_json_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _world_to_ego(
    points: np.ndarray, ego_position_world_m: np.ndarray, ego_heading_rad: float
) -> np.ndarray:
    relative = np.asarray(points, dtype=np.float64) - ego_position_world_m.reshape(1, 2)
    c = math.cos(float(ego_heading_rad))
    s = math.sin(float(ego_heading_rad))
    rotation = np.array([[c, s], [-s, c]], dtype=np.float64)
    return relative @ rotation.T


def _require_permitted_source_states(value: Sequence[str] | None) -> frozenset[str]:
    if value is None:
        return frozenset({"available", "not_applicable"})
    states = frozenset(value)
    if not states or not states <= _SOURCE_STATES:
        raise ValueError("permitted signal source states are invalid")
    return states


def validate_causal_signal_atom_input(
    payload: Mapping[str, Any],
    *,
    permitted_source_states: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Validate a V26-facing causal signal input without policy fallbacks.

    ``unavailable`` is accepted only when the caller's source-capability layer
    explicitly permits it.  The returned payload keeps the historical schema
    literal so existing atom arithmetic remains bit-compatible.
    """

    required = {
        "schema_version",
        "source_state",
        "source_valid",
        "applicable",
        "current_phase",
        "decision_time_s",
        "ego_position_world_m",
        "ego_heading_rad",
        "regulatory_element_id",
        "stop_line_id",
        "stop_line_geometry_world_m",
        "stop_line_geometry_ego_m",
        "stop_line_geometry_sha256",
        "route_tangent_world",
        "route_tangent_ego",
        "route_geometry_sha256",
        "route_arc_m",
        "source_chain_sha256",
        "runtime_receipt",
        "runtime_receipt_sha256",
    }
    if not isinstance(payload, Mapping) or set(payload) != required:
        raise ValueError("causal signal atom input field set drifted")
    if payload.get("schema_version") != CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION:
        raise ValueError("causal signal atom input schema drifted")
    permitted = _require_permitted_source_states(permitted_source_states)
    source_state = payload.get("source_state")
    if source_state not in permitted:
        raise ValueError("causal signal source state is not permitted by source capabilities")

    null_fields = {
        "ego_position_world_m",
        "ego_heading_rad",
        "regulatory_element_id",
        "stop_line_id",
        "stop_line_geometry_world_m",
        "stop_line_geometry_ego_m",
        "stop_line_geometry_sha256",
        "route_tangent_world",
        "route_tangent_ego",
        "route_arc_m",
    }
    if source_state == "unavailable":
        receipt = payload.get("runtime_receipt")
        if (
            payload.get("source_valid") is not False
            or payload.get("applicable") is not False
            or payload.get("current_phase") != "none"
            or any(payload.get(key) is not None for key in null_fields)
            or not isinstance(receipt, Mapping)
            or payload.get("runtime_receipt_sha256") != canonical_json_sha256(receipt)
            or receipt.get("source_mode")
            != "same_tick_signal_authority_unavailable_no_stopline_mapping"
            or receipt.get("source_state") != "unavailable"
            or receipt.get("current_phase") != "none"
            or receipt.get("source_chain_sha256") != payload.get("source_chain_sha256")
            or receipt.get("route_geometry_sha256") != payload.get("route_geometry_sha256")
            or float(receipt.get("decision_time_s", -1.0))
            != float(payload.get("decision_time_s"))
        ):
            raise ValueError("causal unavailable-signal atom source state is invalid")
        return dict(payload)

    if source_state == "not_applicable":
        receipt = payload.get("runtime_receipt")
        if (
            payload.get("source_valid") is not True
            or payload.get("applicable") is not False
            or payload.get("current_phase") != "none"
            or any(payload.get(key) is not None for key in null_fields)
            or not isinstance(receipt, Mapping)
            or payload.get("runtime_receipt_sha256") != canonical_json_sha256(receipt)
            or receipt.get("source_mode") != "same_tick_no_signal_rule_no_v2i"
            or receipt.get("current_phase") != "none"
            or receipt.get("source_chain_sha256") != payload.get("source_chain_sha256")
            or receipt.get("route_geometry_sha256") != payload.get("route_geometry_sha256")
            or float(receipt.get("decision_time_s", -1.0))
            != float(payload.get("decision_time_s"))
        ):
            raise ValueError("causal no-signal atom source state is invalid")
        return dict(payload)

    if (
        source_state != "available"
        or payload.get("source_valid") is not True
        or not isinstance(payload.get("applicable"), bool)
        or payload.get("current_phase") not in _PHASES
        or payload.get("applicable") is not (payload.get("current_phase") == "red")
    ):
        raise ValueError("causal signal atom source state is invalid")
    stop_world = np.asarray(payload.get("stop_line_geometry_world_m"), dtype=np.float64)
    stop_ego = np.asarray(payload.get("stop_line_geometry_ego_m"), dtype=np.float64)
    ego_position = np.asarray(payload.get("ego_position_world_m"), dtype=np.float64)
    heading = payload.get("ego_heading_rad")
    if (
        stop_world.ndim != 2
        or stop_world.shape[1] != 2
        or len(stop_world) < 2
        or stop_ego.shape != stop_world.shape
        or ego_position.shape != (2,)
        or not np.isfinite(
            np.concatenate((stop_world.ravel(), stop_ego.ravel(), ego_position))
        ).all()
        or isinstance(heading, bool)
        or not isinstance(heading, (int, float))
        or not math.isfinite(float(heading))
        or payload.get("stop_line_geometry_sha256")
        != canonical_json_sha256(stop_world.tolist())
    ):
        raise ValueError("causal signal stop-line geometry is invalid")
    expected_stop_ego = _world_to_ego(stop_world, ego_position, float(heading))
    if not np.allclose(stop_ego, expected_stop_ego, rtol=0.0, atol=1e-9):
        raise ValueError("causal signal ego-frame stop line does not match authority")
    tangent_world = np.asarray(payload.get("route_tangent_world"), dtype=np.float64)
    tangent_ego = np.asarray(payload.get("route_tangent_ego"), dtype=np.float64)
    c = math.cos(float(heading))
    s = math.sin(float(heading))
    expected_tangent_ego = np.array([[c, s], [-s, c]]) @ tangent_world
    if (
        tangent_world.shape != (2,)
        or tangent_ego.shape != (2,)
        or not np.isfinite(np.concatenate((tangent_world, tangent_ego))).all()
        or not np.isclose(np.linalg.norm(tangent_world), 1.0, atol=1e-6)
        or not np.allclose(tangent_ego, expected_tangent_ego, rtol=0.0, atol=1e-9)
    ):
        raise ValueError("causal signal route tangent is invalid")
    receipt = payload.get("runtime_receipt")
    if (
        not isinstance(receipt, Mapping)
        or payload.get("runtime_receipt_sha256") != canonical_json_sha256(receipt)
        or receipt.get("source_chain_sha256") != payload.get("source_chain_sha256")
        or receipt.get("stop_line_geometry_sha256") != payload.get("stop_line_geometry_sha256")
        or receipt.get("route_geometry_sha256") != payload.get("route_geometry_sha256")
        or receipt.get("regulatory_element_id") != payload.get("regulatory_element_id")
        or receipt.get("stop_line_id") != payload.get("stop_line_id")
        or receipt.get("current_phase") != payload.get("current_phase")
        or float(
            receipt.get("decision_time_s", receipt.get("decision_timestamp_s", -1.0))
        )
        != float(payload.get("decision_time_s"))
    ):
        raise ValueError("causal signal runtime receipt binding is invalid")
    return dict(payload)
