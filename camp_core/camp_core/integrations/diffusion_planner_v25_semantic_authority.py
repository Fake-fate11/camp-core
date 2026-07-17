"""Frozen V25 source-independent semantics and red-signal authority helpers."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np


SEMANTIC_PAYLOAD_SCHEMA_VERSION = "camp_dp_v25_semantic_clone_payload_v1"
SIGNAL_CHAIN_SCHEMA_VERSION = "camp_dp_v25_red_signal_source_chain_v1"
RUNTIME_SIGNAL_RECEIPT_SCHEMA_VERSION = (
    "camp_dp_v25_current_signal_runtime_receipt_v1"
)
_SHA_CHARS = frozenset("0123456789abcdef")
_PHASES = frozenset({"green", "yellow", "red"})
_SCENARIO_PHASES = frozenset({"none", "green", "yellow", "red"})


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


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and not set(value) - _SHA_CHARS
    )


def _resample_polyline(points: np.ndarray, count: int = 64) -> np.ndarray:
    values = np.asarray(points, dtype=np.float64)
    if (
        values.ndim != 2
        or values.shape[1] != 2
        or len(values) < 2
        or not np.isfinite(values).all()
    ):
        raise ValueError("route polyline must be finite [N>=2,2]")
    segment = np.linalg.norm(np.diff(values, axis=0), axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(segment)))
    if not math.isfinite(float(cumulative[-1])) or cumulative[-1] <= 1e-9:
        raise ValueError("route polyline has no positive arc length")
    targets = np.linspace(0.0, float(cumulative[-1]), count)
    result = np.empty((count, 2), dtype=np.float64)
    for index, target in enumerate(targets):
        left = min(
            max(int(np.searchsorted(cumulative, target, side="right") - 1), 0),
            len(values) - 2,
        )
        span = float(cumulative[left + 1] - cumulative[left])
        fraction = 0.0 if span <= 1e-12 else (target - cumulative[left]) / span
        result[index] = values[left] + fraction * (values[left + 1] - values[left])
    return result


def _local_frame(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sampled = _resample_polyline(points)
    origin = sampled[0]
    direction = sampled[1] - sampled[0]
    norm = float(np.linalg.norm(direction))
    if norm <= 1e-12:
        raise ValueError("route local-frame heading is degenerate")
    tangent = direction / norm
    normal = np.array([-tangent[1], tangent[0]], dtype=np.float64)
    rotation = np.stack((tangent, normal), axis=1)
    return sampled, origin, rotation


def build_semantic_clone_payload(
    case: Mapping[str, Any],
    *,
    route_polyline_world: np.ndarray,
    stop_line_world: np.ndarray | None,
) -> dict[str, Any]:
    """Build the ID/source/path-independent geometry+semantic dedup payload."""
    sampled, origin, rotation = _local_frame(route_polyline_world)

    def local(values: Sequence[float]) -> list[float]:
        point = np.asarray(values, dtype=np.float64)
        if point.shape != (2,) or not np.isfinite(point).all():
            raise ValueError("semantic geometry point is invalid")
        return np.round((point - origin) @ rotation, 6).tolist()

    actors = []
    for actor in case.get("actors", []):
        if not isinstance(actor, Mapping):
            raise ValueError("semantic actor is invalid")
        item = {
            key: value
            for key, value in actor.items()
            if key
            not in {
                "id",
                "scenario_id",
                "route_identity_sha256",
                "record_key",
            }
        }
        if "initial_xy" in item:
            item["initial_xy_local_m"] = local(item.pop("initial_xy"))
        actors.append(item)
    actors.sort(key=canonical_json_sha256)
    parameters = {
        key: value
        for key, value in dict(case.get("parameters", {})).items()
        if key != "variant"
    }
    signal = case.get("signal")
    if not isinstance(signal, Mapping) or signal.get("phase") not in _SCENARIO_PHASES:
        raise ValueError("semantic red-signal phase is invalid")
    payload: dict[str, Any] = {
        "schema_version": SEMANTIC_PAYLOAD_SCHEMA_VERSION,
        "family": str(case.get("family")),
        "tier": str(case.get("tier")),
        "semantic_variant": str(case.get("semantic_variant")),
        "parameters": parameters,
        "actors": actors,
        "signal": {
            "current_phase": str(signal["phase"]),
            "mapped_source_required": signal.get("mapped_source_required") is True,
            "source_mode": "no_v2i",
        },
        "route_polyline_local_m": np.round(
            (sampled - origin) @ rotation, 6
        ).tolist(),
    }
    if stop_line_world is not None:
        stop = np.asarray(stop_line_world, dtype=np.float64)
        if stop.ndim != 2 or stop.shape[1] != 2 or len(stop) < 2:
            raise ValueError("stop-line geometry is invalid")
        payload["stop_line_local_m"] = np.round(
            (stop - origin) @ rotation, 6
        ).tolist()
    forbidden = (
        "source_map_path",
        "source_map_sha256",
        "source_family",
        "repository",
        "map_family_id",
        "route_identity_sha256",
        "route_family_id",
        "scenario_id",
        "parameter_block_id",
        "split",
        "seed",
        "record_key",
    )
    encoded = canonical_json_bytes(payload).decode("utf-8")
    if any(f'"{key}"' in encoded for key in forbidden):
        raise ValueError("semantic clone payload contains a forbidden ID/source key")
    return payload


def validate_signal_chain(chain: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "scenario_id",
        "route_identity_sha256",
        "source_map_sha256",
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
        "expected_current_phase",
        "semantic_clone_payload",
        "semantic_clone_sha256",
        "source_chain_sha256",
    }
    if not isinstance(chain, Mapping) or set(chain) != required:
        raise ValueError("red signal source-chain field set drifted")
    if chain.get("schema_version") != SIGNAL_CHAIN_SCHEMA_VERSION:
        raise ValueError("red signal source-chain schema drifted")
    for key in ("scenario_id", "route_identity_sha256", "source_map_sha256"):
        if not _is_sha256(chain.get(key)):
            raise ValueError(f"red signal source-chain {key} is invalid")
    if not _is_sha256(chain.get("route_geometry_sha256")):
        raise ValueError("red signal route geometry SHA is invalid")
    regulatory = chain.get("regulatory_element_ids")
    physical = chain.get("physical_light_ids")
    bulbs = chain.get("bulb_ids")
    controlled = chain.get("controlled_lanelet_ids")
    route = chain.get("route_lanelet_ids")
    if (
        not isinstance(regulatory, list)
        or len(regulatory) != 1
        or not isinstance(physical, list)
        or not physical
        or not isinstance(bulbs, list)
        or not bulbs
        or not isinstance(controlled, list)
        or not controlled
        or not isinstance(route, list)
        or not route
        or any(isinstance(value, bool) or not isinstance(value, int) for values in (regulatory, physical, bulbs, controlled, route) for value in values)
        or len(set(physical)) != len(physical)
        or len(set(bulbs)) != len(bulbs)
        or len(set(controlled)) != len(controlled)
        or not set(controlled).issubset(route)
    ):
        raise ValueError("red signal IDs are missing, ambiguous, or inconsistent")
    stop = np.asarray(chain.get("stop_line_geometry_m"), dtype=np.float64)
    if (
        isinstance(chain.get("stop_line_id"), bool)
        or not isinstance(chain.get("stop_line_id"), int)
        or stop.ndim != 2
        or stop.shape[1] != 2
        or len(stop) < 2
        or not np.isfinite(stop).all()
        or float(np.linalg.norm(stop[-1] - stop[0])) <= 1e-6
        or chain.get("stop_line_geometry_sha256")
        != canonical_json_sha256(stop.tolist())
    ):
        raise ValueError("red signal stop-line source is invalid")
    distance = chain.get("stop_line_route_distance_m")
    arc = chain.get("route_arc_m")
    length = chain.get("route_length_m")
    if (
        any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in (distance, arc, length))
        or not all(math.isfinite(float(value)) for value in (distance, arc, length))
        or float(distance) < 0.0
        or float(distance) > 0.1
        or float(length) <= 0.0
        or float(arc) < -1e-8
        or float(arc) > float(length) + 1e-8
    ):
        raise ValueError("red signal stop-line/route-arc relation is invalid")
    if chain.get("expected_current_phase") not in _PHASES:
        raise ValueError("red signal expected current phase is invalid")
    if chain.get("semantic_clone_sha256") != canonical_json_sha256(
        chain.get("semantic_clone_payload")
    ):
        raise ValueError("semantic clone payload/hash mismatch")
    without_hash = {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    if chain.get("source_chain_sha256") != canonical_json_sha256(without_hash):
        raise ValueError("red signal source-chain hash mismatch")
    return dict(chain)


def build_runtime_signal_receipt(
    chain: Mapping[str, Any],
    *,
    scenario_id: str,
    tick_index: int,
    decision_time_s: float,
    current_phase: str,
    applied_route_lanelet_ids: Sequence[int],
    applied_map_lanelet_ids: Sequence[int],
) -> dict[str, Any]:
    validated = validate_signal_chain(chain)
    if scenario_id != validated["scenario_id"]:
        raise ValueError("runtime signal receipt scenario/source-chain mismatch")
    if current_phase != validated["expected_current_phase"]:
        raise ValueError("runtime current phase does not match qualified source")
    if isinstance(tick_index, bool) or not isinstance(tick_index, int) or tick_index < 0:
        raise ValueError("runtime signal tick is invalid")
    if not math.isfinite(float(decision_time_s)) or float(decision_time_s) < 0.0:
        raise ValueError("runtime signal decision time is invalid")
    route_rows = [int(value) for value in applied_route_lanelet_ids]
    map_rows = [int(value) for value in applied_map_lanelet_ids]
    applied = route_rows + map_rows
    if not applied or not set(applied).issubset(validated["controlled_lanelet_ids"]):
        raise ValueError("runtime signal applied a wrong or absent controlled lanelet")
    return {
        "schema_version": RUNTIME_SIGNAL_RECEIPT_SCHEMA_VERSION,
        "scenario_id": scenario_id,
        "tick_index": tick_index,
        "decision_time_s": float(decision_time_s),
        "source_mode": "same_tick_current_phase_no_v2i",
        "current_phase": current_phase,
        "regulatory_element_id": validated["regulatory_element_ids"][0],
        "physical_light_ids": list(validated["physical_light_ids"]),
        "bulb_ids": list(validated["bulb_ids"]),
        "controlled_lanelet_ids": list(validated["controlled_lanelet_ids"]),
        "stop_line_id": validated["stop_line_id"],
        "stop_line_geometry_sha256": validated["stop_line_geometry_sha256"],
        "route_geometry_sha256": validated["route_geometry_sha256"],
        "route_arc_m": validated["route_arc_m"],
        "source_chain_sha256": validated["source_chain_sha256"],
        "semantic_clone_sha256": validated["semantic_clone_sha256"],
        "applied_route_lanelet_ids": route_rows,
        "applied_map_lanelet_ids": map_rows,
        "phase_remaining_available": False,
        "source_valid": True,
    }


def validate_runtime_signal_receipt(
    receipt: Mapping[str, Any],
    chain: Mapping[str, Any],
) -> dict[str, Any]:
    expected = build_runtime_signal_receipt(
        chain,
        scenario_id=str(receipt.get("scenario_id")),
        tick_index=receipt.get("tick_index"),
        decision_time_s=receipt.get("decision_time_s"),
        current_phase=str(receipt.get("current_phase")),
        applied_route_lanelet_ids=receipt.get("applied_route_lanelet_ids", []),
        applied_map_lanelet_ids=receipt.get("applied_map_lanelet_ids", []),
    )
    if dict(receipt) != expected:
        raise ValueError("runtime signal receipt field/value mismatch")
    return expected
