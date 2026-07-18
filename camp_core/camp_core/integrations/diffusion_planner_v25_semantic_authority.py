"""Frozen V25 source-independent semantics and red-signal authority helpers."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np


SEMANTIC_PAYLOAD_SCHEMA_VERSION = "camp_dp_v25_semantic_clone_payload_v3"
SIGNAL_CHAIN_SCHEMA_VERSION = "camp_dp_v25_red_signal_source_chain_v2"
NO_SIGNAL_CHAIN_SCHEMA_VERSION = "camp_dp_v25_no_signal_source_chain_v1"
RUNTIME_SIGNAL_RECEIPT_SCHEMA_VERSION = (
    "camp_dp_v25_current_signal_runtime_receipt_v2"
)
CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION = (
    "camp_dp_v25_causal_signal_atom_input_v2"
)
_SHA_CHARS = frozenset("0123456789abcdef")
_PHASES = frozenset({"green", "yellow", "red"})
_SCENARIO_PHASES = frozenset({"none", "green", "yellow", "red"})
_PARAMETER_FIELDS = frozenset(
    {
        "headway_m",
        "ego_speed_mps",
        "other_speed_mps",
        "deceleration_mps2",
        "trigger_time_s",
        "lateral_offset_m",
        "lateral_speed_mps",
        "crossing_speed_mps",
        "variant",
    }
)
_ACTOR_FIELDS = frozenset(
    {
        "id",
        "agent_type",
        "initial_xy",
        "initial_heading_rad",
        "route_tangent",
        "route_normal",
        "trigger_time_s",
        "longitudinal_speed_mps",
        "lateral_offset_m",
        "lateral_speed_mps",
        "lateral_target_m",
        "longitudinal_acceleration_mps2",
        "length_m",
        "width_m",
        "wheelbase_m",
    }
)
_SEMANTIC_ACTOR_FIELDS = frozenset(
    {
        "agent_type",
        "initial_xy_local_m",
        "initial_heading_local_unit",
        "route_tangent_local",
        "route_normal_local",
        "trigger_time_s",
        "longitudinal_speed_mps",
        "lateral_offset_m",
        "lateral_speed_mps",
        "lateral_target_m",
        "longitudinal_acceleration_mps2",
        "length_m",
        "width_m",
        "wheelbase_m",
    }
)
_FORBIDDEN_SEMANTIC_TOKENS = (
    "outcome",
    "fresh",
    "holdout",
    "future",
    "split",
    "seed",
    "scenario_id",
    "route_identity",
    "map_family",
    "route_family",
    "parameter_block",
    "source_family",
    "source_map",
    "repository",
    "record_key",
)


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


def _round_clean(values: np.ndarray, decimals: int = 6) -> np.ndarray:
    rounded = np.round(np.asarray(values, dtype=np.float64), decimals)
    rounded[np.abs(rounded) < 0.5 * 10.0 ** (-decimals)] = 0.0
    return rounded


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
        return _round_clean((point - origin) @ rotation).tolist()

    parameters_raw = case.get("parameters", {})
    if not isinstance(parameters_raw, Mapping):
        raise ValueError("semantic parameters are invalid")
    unexpected_parameters = set(parameters_raw) - _PARAMETER_FIELDS
    if unexpected_parameters:
        raise ValueError(
            "semantic parameter whitelist rejected fields: "
            f"{sorted(unexpected_parameters)}"
        )
    parameters: dict[str, float] = {}
    for key, value in parameters_raw.items():
        if key == "variant":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("semantic parameter variant must be an integer")
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"semantic parameter {key} must be a physical scalar")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError(f"semantic parameter {key} must be finite")
        parameters[key] = numeric

    actors = []
    for actor in case.get("actors", []):
        if not isinstance(actor, Mapping):
            raise ValueError("semantic actor is invalid")
        unexpected_actor = set(actor) - _ACTOR_FIELDS
        if unexpected_actor:
            raise ValueError(
                "semantic actor whitelist rejected fields: "
                f"{sorted(unexpected_actor)}"
            )
        required_actor = _ACTOR_FIELDS - {"id"}
        if not required_actor.issubset(actor):
            raise ValueError(
                "semantic actor is missing physical fields: "
                f"{sorted(required_actor - set(actor))}"
            )
        tangent = np.asarray(actor["route_tangent"], dtype=np.float64)
        actor_normal = np.asarray(actor["route_normal"], dtype=np.float64)
        if (
            tangent.shape != (2,)
            or actor_normal.shape != (2,)
            or not np.isfinite(np.concatenate((tangent, actor_normal))).all()
            or not np.isclose(np.linalg.norm(tangent), 1.0, atol=1e-6)
            or not np.isclose(np.linalg.norm(actor_normal), 1.0, atol=1e-6)
            or not np.isclose(float(tangent @ actor_normal), 0.0, atol=1e-6)
        ):
            raise ValueError("semantic actor route frame is invalid")
        heading = actor["initial_heading_rad"]
        if isinstance(heading, bool) or not isinstance(heading, (int, float)) or not math.isfinite(float(heading)):
            raise ValueError("semantic actor heading is invalid")
        heading_world = np.array(
            [math.cos(float(heading)), math.sin(float(heading))], dtype=np.float64
        )
        heading_local = heading_world @ rotation
        item: dict[str, Any] = {
            "agent_type": str(actor["agent_type"]),
            "initial_xy_local_m": local(actor["initial_xy"]),
            # Keep the direction on S1 instead of serializing atan2.  A scalar
            # angle has two encodings at the +/-pi branch cut and therefore
            # cannot be a canonical SE(2)-invariant semantic-clone field.
            "initial_heading_local_unit": _round_clean(heading_local).tolist(),
            "route_tangent_local": _round_clean(tangent @ rotation).tolist(),
            "route_normal_local": _round_clean(actor_normal @ rotation).tolist(),
        }
        for key in sorted(
            required_actor
            - {
                "agent_type",
                "initial_xy",
                "initial_heading_rad",
                "route_tangent",
                "route_normal",
            }
        ):
            value = actor[key]
            if value is None and key == "lateral_target_m":
                item[key] = None
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"semantic actor {key} must be a physical scalar")
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"semantic actor {key} must be finite")
            item[key] = numeric
        actors.append(item)
    actors.sort(key=canonical_json_sha256)
    signal = case.get("signal")
    if (
        not isinstance(signal, Mapping)
        or set(signal) not in (
            {"phase", "mapped_source_required"},
            {"phase", "phase_remaining_s", "mapped_source_required"},
        )
        or signal.get("phase") not in _SCENARIO_PHASES
        or type(signal.get("mapped_source_required")) is not bool
        or (
            "phase_remaining_s" in signal
            and (
                type(signal["phase_remaining_s"]) not in (int, float)
                or not math.isfinite(float(signal["phase_remaining_s"]))
                or float(signal["phase_remaining_s"]) < 0.0
            )
        )
    ):
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
        "route_polyline_local_m": _round_clean(
            (sampled - origin) @ rotation
        ).tolist(),
    }
    if stop_line_world is not None:
        stop = np.asarray(stop_line_world, dtype=np.float64)
        if stop.ndim != 2 or stop.shape[1] != 2 or len(stop) < 2:
            raise ValueError("stop-line geometry is invalid")
        payload["stop_line_local_m"] = _round_clean(
            (stop - origin) @ rotation
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
    for container in (parameters_raw, *case.get("actors", [])):
        for key in container:
            lowered = str(key).lower()
            if any(token in lowered for token in _FORBIDDEN_SEMANTIC_TOKENS):
                raise ValueError("semantic input contains a forbidden outcome/future/ID proxy")
    return payload


def _strict_json_vector(value: Any, *, label: str, unit: bool = False) -> np.ndarray:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(type(item) not in (int, float) for item in value)
    ):
        raise ValueError(f"{label} must be a native numeric length-two JSON list")
    result = np.asarray(value, dtype=np.float64)
    if not np.isfinite(result).all():
        raise ValueError(f"{label} must be finite")
    if unit and not np.isclose(np.linalg.norm(result), 1.0, rtol=0.0, atol=2e-6):
        raise ValueError(f"{label} must be a unit vector")
    return result


def _strict_json_polyline(value: Any, *, label: str, exact_count: int | None) -> np.ndarray:
    if not isinstance(value, list) or (exact_count is not None and len(value) != exact_count):
        raise ValueError(f"{label} row count drifted")
    rows = [_strict_json_vector(row, label=label) for row in value]
    if len(rows) < 2:
        raise ValueError(f"{label} requires at least two points")
    result = np.stack(rows)
    if float(np.linalg.norm(np.diff(result, axis=0), axis=1).sum()) <= 1e-9:
        raise ValueError(f"{label} has no positive arc length")
    return result


def validate_semantic_clone_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the exact frozen v3 source/ID/outcome-independent payload."""
    if not isinstance(payload, Mapping):
        raise ValueError("semantic clone payload must be an object")
    required = {
        "schema_version",
        "family",
        "tier",
        "semantic_variant",
        "parameters",
        "actors",
        "signal",
        "route_polyline_local_m",
    }
    allowed = required | {"stop_line_local_m"}
    if set(payload) not in (required, allowed):
        raise ValueError("semantic clone payload field set drifted")
    if payload.get("schema_version") != SEMANTIC_PAYLOAD_SCHEMA_VERSION:
        raise ValueError("semantic clone payload schema drifted")
    for key in ("family", "tier", "semantic_variant"):
        if not isinstance(payload.get(key), str) or not payload[key] or payload[key] == "None":
            raise ValueError(f"semantic clone {key} is invalid")

    parameters = payload.get("parameters")
    if not isinstance(parameters, Mapping) or set(parameters) - (_PARAMETER_FIELDS - {"variant"}):
        raise ValueError("semantic clone parameter field set drifted")
    for key, value in parameters.items():
        if type(value) not in (int, float) or not math.isfinite(float(value)):
            raise ValueError(f"semantic clone parameter {key} is not finite native numeric")

    actors = payload.get("actors")
    if not isinstance(actors, list):
        raise ValueError("semantic clone actors must be a list")
    normalized_actors: list[dict[str, Any]] = []
    for actor in actors:
        if not isinstance(actor, Mapping) or set(actor) != _SEMANTIC_ACTOR_FIELDS:
            raise ValueError("semantic clone actor field set drifted")
        if not isinstance(actor.get("agent_type"), str) or not actor["agent_type"]:
            raise ValueError("semantic clone actor type is invalid")
        _strict_json_vector(actor.get("initial_xy_local_m"), label="actor position")
        heading = _strict_json_vector(
            actor.get("initial_heading_local_unit"), label="actor heading", unit=True
        )
        tangent = _strict_json_vector(
            actor.get("route_tangent_local"), label="actor route tangent", unit=True
        )
        normal = _strict_json_vector(
            actor.get("route_normal_local"), label="actor route normal", unit=True
        )
        if not np.isclose(float(tangent @ normal), 0.0, rtol=0.0, atol=2e-6):
            raise ValueError("semantic clone actor route frame is not orthogonal")
        if not np.isfinite(heading).all():  # explicit readability of the S1 contract
            raise ValueError("semantic clone actor heading is invalid")
        for key in _SEMANTIC_ACTOR_FIELDS - {
            "agent_type",
            "initial_xy_local_m",
            "initial_heading_local_unit",
            "route_tangent_local",
            "route_normal_local",
        }:
            value = actor[key]
            if key == "lateral_target_m" and value is None:
                continue
            if type(value) not in (int, float) or not math.isfinite(float(value)):
                raise ValueError(f"semantic clone actor {key} is not finite native numeric")
        normalized_actors.append(dict(actor))
    if normalized_actors != sorted(normalized_actors, key=canonical_json_sha256):
        raise ValueError("semantic clone actors are not in canonical order")

    signal = payload.get("signal")
    if not isinstance(signal, Mapping) or set(signal) != {
        "current_phase",
        "mapped_source_required",
        "source_mode",
    }:
        raise ValueError("semantic clone signal field set drifted")
    if (
        signal.get("current_phase") not in _SCENARIO_PHASES
        or type(signal.get("mapped_source_required")) is not bool
        or signal.get("source_mode") != "no_v2i"
    ):
        raise ValueError("semantic clone signal contract drifted")
    route = _strict_json_polyline(
        payload.get("route_polyline_local_m"),
        label="semantic route polyline",
        exact_count=64,
    )
    if not np.allclose(route[0], np.zeros(2), rtol=0.0, atol=1e-9):
        raise ValueError("semantic route local origin drifted")
    if "stop_line_local_m" in payload:
        _strict_json_polyline(
            payload["stop_line_local_m"], label="semantic stop line", exact_count=None
        )
    return dict(payload)


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
        "route_tangent_world",
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
    tangent = np.asarray(chain.get("route_tangent_world"), dtype=np.float64)
    if (
        tangent.shape != (2,)
        or not np.isfinite(tangent).all()
        or not np.isclose(np.linalg.norm(tangent), 1.0, atol=1e-6)
    ):
        raise ValueError("red signal route tangent is invalid")
    semantic = validate_semantic_clone_payload(chain.get("semantic_clone_payload"))
    if (
        "stop_line_local_m" not in semantic
        or semantic["signal"] != {
            "current_phase": chain.get("expected_current_phase"),
            "mapped_source_required": True,
            "source_mode": "no_v2i",
        }
        or chain.get("route_geometry_sha256")
        != canonical_json_sha256(
            {
                "route_polyline_local_m": semantic["route_polyline_local_m"],
                "stop_line_local_m": semantic["stop_line_local_m"],
            }
        )
        or chain.get("semantic_clone_sha256") != canonical_json_sha256(semantic)
    ):
        raise ValueError("semantic clone payload/hash mismatch")
    without_hash = {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    if chain.get("source_chain_sha256") != canonical_json_sha256(without_hash):
        raise ValueError("red signal source-chain hash mismatch")
    return dict(chain)


def validate_no_signal_chain(chain: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a source-only receipt proving that a route has no signal rule."""
    required = {
        "schema_version",
        "scenario_id",
        "route_identity_sha256",
        "source_map_sha256",
        "route_lanelet_ids",
        "route_geometry_sha256",
        "traffic_light_regulatory_element_ids",
        "semantic_clone_payload",
        "semantic_clone_sha256",
        "source_chain_sha256",
    }
    if not isinstance(chain, Mapping) or set(chain) != required:
        raise ValueError("no-signal source-chain field set drifted")
    if chain.get("schema_version") != NO_SIGNAL_CHAIN_SCHEMA_VERSION:
        raise ValueError("no-signal source-chain schema drifted")
    for key in (
        "scenario_id",
        "route_identity_sha256",
        "source_map_sha256",
        "route_geometry_sha256",
    ):
        if not _is_sha256(chain.get(key)):
            raise ValueError(f"no-signal source-chain {key} is invalid")
    route = chain.get("route_lanelet_ids")
    if (
        not isinstance(route, list)
        or not route
        or len(set(route)) != len(route)
        or any(isinstance(value, bool) or not isinstance(value, int) for value in route)
        or chain.get("traffic_light_regulatory_element_ids") != []
    ):
        raise ValueError("no-signal route authority is invalid")
    semantic = validate_semantic_clone_payload(chain.get("semantic_clone_payload"))
    if (
        "stop_line_local_m" in semantic
        or semantic["signal"] != {
            "current_phase": "none",
            "mapped_source_required": False,
            "source_mode": "no_v2i",
        }
        or chain.get("route_geometry_sha256")
        != canonical_json_sha256(
            {"route_polyline_local_m": semantic["route_polyline_local_m"]}
        )
        or chain.get("semantic_clone_sha256") != canonical_json_sha256(semantic)
    ):
        raise ValueError("no-signal semantic clone payload/hash mismatch")
    without_hash = {
        key: value for key, value in chain.items() if key != "source_chain_sha256"
    }
    if chain.get("source_chain_sha256") != canonical_json_sha256(without_hash):
        raise ValueError("no-signal source-chain hash mismatch")
    return dict(chain)


def build_runtime_no_signal_receipt(
    chain: Mapping[str, Any],
    *,
    scenario_id: str,
    tick_index: int,
    decision_time_s: float,
) -> dict[str, Any]:
    validated = validate_no_signal_chain(chain)
    if scenario_id != validated["scenario_id"]:
        raise ValueError("runtime no-signal scenario/source-chain mismatch")
    if isinstance(tick_index, bool) or not isinstance(tick_index, int) or tick_index < 0:
        raise ValueError("runtime no-signal tick is invalid")
    if not math.isfinite(float(decision_time_s)) or float(decision_time_s) < 0.0:
        raise ValueError("runtime no-signal decision time is invalid")
    return {
        "schema_version": RUNTIME_SIGNAL_RECEIPT_SCHEMA_VERSION,
        "scenario_id": scenario_id,
        "tick_index": tick_index,
        "decision_time_s": float(decision_time_s),
        "source_mode": "same_tick_no_signal_rule_no_v2i",
        "current_phase": "none",
        "route_geometry_sha256": validated["route_geometry_sha256"],
        "route_lanelet_ids": list(validated["route_lanelet_ids"]),
        "traffic_light_regulatory_element_ids": [],
        "source_chain_sha256": validated["source_chain_sha256"],
        "semantic_clone_sha256": validated["semantic_clone_sha256"],
        "phase_remaining_available": False,
        "source_valid": True,
        "applicable": False,
    }


def validate_runtime_no_signal_receipt(
    receipt: Mapping[str, Any], chain: Mapping[str, Any]
) -> dict[str, Any]:
    expected = build_runtime_no_signal_receipt(
        chain,
        scenario_id=str(receipt.get("scenario_id")),
        tick_index=receipt.get("tick_index"),
        decision_time_s=receipt.get("decision_time_s"),
    )
    if dict(receipt) != expected:
        raise ValueError("runtime no-signal receipt field/value mismatch")
    return expected


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
        "route_tangent_world": list(validated["route_tangent_world"]),
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


def _world_to_ego(
    points: np.ndarray, ego_position_world_m: np.ndarray, ego_heading_rad: float
) -> np.ndarray:
    relative = np.asarray(points, dtype=np.float64) - ego_position_world_m.reshape(1, 2)
    c = math.cos(float(ego_heading_rad))
    s = math.sin(float(ego_heading_rad))
    rotation = np.array([[c, s], [-s, c]], dtype=np.float64)
    return relative @ rotation.T


def build_causal_signal_atom_input(
    chain: Mapping[str, Any],
    runtime_receipt: Mapping[str, Any],
    *,
    ego_position_world_m: Sequence[float],
    ego_heading_rad: float,
) -> dict[str, Any]:
    """Bind the authorized regulatory stop line to the same-tick ego frame."""
    validated = validate_signal_chain(chain)
    receipt = validate_runtime_signal_receipt(runtime_receipt, validated)
    ego_position = np.asarray(ego_position_world_m, dtype=np.float64)
    if (
        ego_position.shape != (2,)
        or not np.isfinite(ego_position).all()
        or isinstance(ego_heading_rad, bool)
        or not isinstance(ego_heading_rad, (int, float))
        or not math.isfinite(float(ego_heading_rad))
    ):
        raise ValueError("causal signal ego pose is invalid")
    stop_world = np.asarray(validated["stop_line_geometry_m"], dtype=np.float64)
    stop_ego = _world_to_ego(stop_world, ego_position, float(ego_heading_rad))
    tangent_world = np.asarray(validated["route_tangent_world"], dtype=np.float64)
    c = math.cos(float(ego_heading_rad))
    s = math.sin(float(ego_heading_rad))
    rotation = np.array([[c, s], [-s, c]], dtype=np.float64)
    tangent_ego = rotation @ tangent_world
    phase = str(receipt["current_phase"])
    payload = {
        "schema_version": CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION,
        "source_state": "available",
        "source_valid": True,
        "applicable": phase == "red",
        "current_phase": phase,
        "decision_time_s": float(receipt["decision_time_s"]),
        "ego_position_world_m": ego_position.tolist(),
        "ego_heading_rad": float(ego_heading_rad),
        "regulatory_element_id": validated["regulatory_element_ids"][0],
        "stop_line_id": validated["stop_line_id"],
        "stop_line_geometry_world_m": stop_world.tolist(),
        "stop_line_geometry_ego_m": stop_ego.tolist(),
        "stop_line_geometry_sha256": validated["stop_line_geometry_sha256"],
        "route_tangent_world": tangent_world.tolist(),
        "route_tangent_ego": tangent_ego.tolist(),
        "route_geometry_sha256": validated["route_geometry_sha256"],
        "route_arc_m": float(validated["route_arc_m"]),
        "source_chain_sha256": validated["source_chain_sha256"],
        "runtime_receipt": receipt,
        "runtime_receipt_sha256": canonical_json_sha256(receipt),
    }
    return validate_causal_signal_atom_input(payload)


def build_no_signal_causal_atom_input(
    chain: Mapping[str, Any], runtime_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    validated = validate_no_signal_chain(chain)
    receipt = validate_runtime_no_signal_receipt(runtime_receipt, validated)
    payload = {
        "schema_version": CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION,
        "source_state": "not_applicable",
        "source_valid": True,
        "applicable": False,
        "current_phase": "none",
        "decision_time_s": float(receipt["decision_time_s"]),
        "ego_position_world_m": None,
        "ego_heading_rad": None,
        "regulatory_element_id": None,
        "stop_line_id": None,
        "stop_line_geometry_world_m": None,
        "stop_line_geometry_ego_m": None,
        "stop_line_geometry_sha256": None,
        "route_tangent_world": None,
        "route_tangent_ego": None,
        "route_geometry_sha256": validated["route_geometry_sha256"],
        "route_arc_m": None,
        "source_chain_sha256": validated["source_chain_sha256"],
        "runtime_receipt": receipt,
        "runtime_receipt_sha256": canonical_json_sha256(receipt),
    }
    return validate_causal_signal_atom_input(payload)


def validate_causal_signal_atom_input(
    payload: Mapping[str, Any],
    chain: Mapping[str, Any] | None = None,
    runtime_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
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
    if payload.get("source_state") == "not_applicable":
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
        receipt = payload.get("runtime_receipt")
        if (
            payload.get("source_valid") is not True
            or payload.get("applicable") is not False
            or payload.get("current_phase") != "none"
            or any(payload.get(key) is not None for key in null_fields)
            or not isinstance(receipt, Mapping)
            or payload.get("runtime_receipt_sha256")
            != canonical_json_sha256(receipt)
            or receipt.get("source_mode") != "same_tick_no_signal_rule_no_v2i"
            or receipt.get("current_phase") != "none"
            or receipt.get("source_chain_sha256")
            != payload.get("source_chain_sha256")
            or receipt.get("route_geometry_sha256")
            != payload.get("route_geometry_sha256")
            or float(receipt.get("decision_time_s", -1.0))
            != float(payload.get("decision_time_s"))
        ):
            raise ValueError("causal no-signal atom source state is invalid")
        if chain is not None or runtime_receipt is not None:
            if chain is None or runtime_receipt is None:
                raise ValueError("chain and runtime receipt must be provided together")
            expected = build_no_signal_causal_atom_input(chain, runtime_receipt)
            if dict(payload) != expected:
                raise ValueError("causal no-signal input does not match source chain")
        return dict(payload)
    if (
        payload.get("source_state") != "available"
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
        or not np.isfinite(np.concatenate((stop_world.ravel(), stop_ego.ravel(), ego_position))).all()
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
        or receipt.get("stop_line_geometry_sha256")
        != payload.get("stop_line_geometry_sha256")
        or receipt.get("route_geometry_sha256") != payload.get("route_geometry_sha256")
        or receipt.get("regulatory_element_id") != payload.get("regulatory_element_id")
        or receipt.get("stop_line_id") != payload.get("stop_line_id")
        or receipt.get("current_phase") != payload.get("current_phase")
        or float(
            receipt.get(
                "decision_time_s", receipt.get("decision_timestamp_s", -1.0)
            )
        )
        != float(payload.get("decision_time_s"))
    ):
        raise ValueError("causal signal runtime receipt binding is invalid")
    if chain is not None or runtime_receipt is not None:
        if chain is None or runtime_receipt is None:
            raise ValueError("chain and runtime receipt must be provided together")
        expected = build_causal_signal_atom_input(
            chain,
            runtime_receipt,
            ego_position_world_m=ego_position,
            ego_heading_rad=float(heading),
        )
        if dict(payload) != expected:
            raise ValueError("causal signal atom input does not match source chain")
    return dict(payload)
