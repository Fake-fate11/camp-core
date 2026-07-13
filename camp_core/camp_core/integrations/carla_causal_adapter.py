from __future__ import annotations

import hashlib
import math
from dataclasses import asdict
from types import SimpleNamespace
from typing import Any, Mapping, Optional, Sequence, Tuple
import xml.etree.ElementTree as ET

import numpy as np

from camp_core.integrations.carla_exact_speed_source import (
    LaneSectionBounds,
    LaneSurfaceSample,
    LiftingTolerances,
    RouteLiftingContext,
    _validate_lifting_context,
    canonical_json_sha256,
    parse_opendrive_lane_section_bounds,
    route_identity_directions,
)
from camp_core.integrations.diffusion_planner_causal_materializer import (
    CausalDPMaterialization,
    materialize_causal_dp_input,
)


_FORBIDDEN_SOURCE_PARTS = (
    "future",
    "outcome",
    "label",
    "holdout",
    "metric",
    "safety",
    "collision",
    "ade",
    "fde",
)
_ROUTE_SAMPLE_FIELDS = {
    "road_id",
    "section_id",
    "lane_id",
    "s",
    "x",
    "y",
    "z",
    "lane_width",
    "is_junction",
}
CARLA_ROUTE_CORRIDOR_SCHEMA = "dp_camp_v20_carla_route_corridor_v1"


def _waypoint_identity(waypoint: Any) -> Tuple[str, int, int]:
    try:
        raw_road_id = waypoint.road_id
        raw_section_id = waypoint.section_id
        raw_lane_id = waypoint.lane_id
    except AttributeError as exc:
        raise ValueError("CARLA route waypoint metadata is invalid") from exc
    if (
        isinstance(raw_road_id, bool)
        or not isinstance(raw_road_id, (int, str))
        or not str(raw_road_id)
        or isinstance(raw_section_id, bool)
        or not isinstance(raw_section_id, int)
        or raw_section_id < 0
        or isinstance(raw_lane_id, bool)
        or not isinstance(raw_lane_id, int)
        or raw_lane_id == 0
    ):
        raise ValueError("CARLA route waypoint metadata is invalid")
    return (str(raw_road_id), raw_section_id, raw_lane_id)


def _lane_surface_sample_payload(waypoint: Any) -> dict[str, Any]:
    identity = _waypoint_identity(waypoint)
    try:
        location = waypoint.transform.location
        s = float(waypoint.s)
        x = float(location.x)
        y = float(location.y)
        z = float(location.z)
        lane_width = float(waypoint.lane_width)
        is_junction = waypoint.is_junction
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("CARLA route waypoint metadata is invalid") from exc
    if (
        not all(math.isfinite(value) for value in (s, x, y, z, lane_width))
        or s < 0.0
        or lane_width <= 0.0
        or not isinstance(is_junction, bool)
    ):
        raise ValueError("CARLA route waypoint metadata is invalid")
    return {
        "road_id": identity[0],
        "section_id": identity[1],
        "lane_id": identity[2],
        "s": s,
        "x": x,
        "y": y,
        "z": z,
        "lane_width": lane_width,
        "is_junction": is_junction,
    }


def _boundary_sample_payload(
    map_api: Any,
    identity: Tuple[str, int, int],
    lookup_s: float,
    station_allowance_m: float,
    is_junction: bool,
) -> dict[str, Any]:
    try:
        waypoint = map_api.get_waypoint_xodr(
            int(identity[0]), identity[2], lookup_s
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("route corridor boundary lookup failed") from exc
    if waypoint is None:
        raise ValueError("route corridor boundary lookup failed")
    payload = _lane_surface_sample_payload(waypoint)
    if (
        (payload["road_id"], payload["section_id"], payload["lane_id"])
        != identity
        or abs(payload["s"] - lookup_s) > station_allowance_m
        or payload["is_junction"] is not is_junction
    ):
        raise ValueError("route corridor boundary identity verification failed")
    return payload


def _opendrive_driving_lane_direction(
    opendrive_xml: str, identity: Tuple[str, int, int]
) -> tuple[int, str, str]:
    try:
        root = ET.fromstring(opendrive_xml)
    except ET.ParseError as exc:
        raise ValueError("invalid OpenDRIVE XML") from exc
    road = next((item for item in root.findall("road") if item.get("id") == identity[0]), None)
    sections = [] if road is None else road.findall("./lanes/laneSection")
    if not 0 <= identity[1] < len(sections):
        raise ValueError("predecessor OpenDRIVE lane evidence is missing")
    road_rule = road.get("rule", "RHT")
    if road_rule not in {"RHT", "LHT"}:
        raise ValueError("predecessor OpenDRIVE direction semantics are unsupported")
    side = "left" if identity[2] > 0 else "right"
    lanes = []
    for lane in sections[identity[1]].findall(f"./{side}/lane"):
        try:
            lane_id = int(lane.get("id", ""))
        except ValueError as exc:
            raise ValueError("predecessor OpenDRIVE lane evidence is invalid") from exc
        if lane_id == identity[2]:
            lanes.append(lane)
    if len(lanes) != 1 or lanes[0].get("type") != "driving":
        raise ValueError("predecessor OpenDRIVE driving lane evidence is missing")
    lane_direction = lanes[0].get("direction", "standard")
    if (
        lane_direction not in {"standard", "reversed"}
        or lanes[0].get("dynamicLaneDirection", "false") != "false"
    ):
        raise ValueError("predecessor OpenDRIVE direction semantics are unsupported")
    station_direction = -1 if identity[2] > 0 else 1
    if road_rule == "LHT":
        station_direction *= -1
    if lane_direction == "reversed":
        station_direction *= -1
    return station_direction, road_rule, lane_direction


def build_pre_generation_route_corridor(
    *,
    route: Sequence[Any],
    map_api: Any,
    opendrive_xml: str,
    route_sample_step_m: float,
    station_allowance_m: float,
    contact_tolerance_m: float,
) -> dict[str, Any]:
    if len(route) < 2:
        raise ValueError("route corridor needs at least two future samples")
    for name, value in (
        ("route step", route_sample_step_m),
        ("station allowance", station_allowance_m),
    ):
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"{name} must be finite and positive")
    if route_sample_step_m != 5.0:
        raise ValueError("route step must equal 5.0")
    if not math.isfinite(contact_tolerance_m) or contact_tolerance_m < 0.0:
        raise ValueError("contact tolerance must be finite and nonnegative")
    predecessors = list(route[0].previous(route_sample_step_m))
    if len(predecessors) != 1:
        raise ValueError("route corridor requires exactly one predecessor")
    source_waypoints = [predecessors[0], *route]

    source_samples = [_lane_surface_sample_payload(item) for item in source_waypoints]
    groups = []
    seen = set()
    for sample in source_samples:
        identity = (sample["road_id"], sample["section_id"], sample["lane_id"])
        if not groups or groups[-1][0] != identity:
            if identity in seen:
                raise ValueError("route identity must occupy one contiguous block")
            seen.add(identity)
            groups.append((identity, []))
        groups[-1][1].append(sample)
    successor_identity = _waypoint_identity(route[0])
    directions = []
    predecessor_direction_evidence = None
    for index, (identity, samples) in enumerate(groups):
        if index == 0 and len(samples) == 1 and identity != successor_identity:
            direction, road_rule, lane_direction = _opendrive_driving_lane_direction(
                opendrive_xml, identity
            )
            predecessor_direction_evidence = {
                "source": "opendrive_static_lane_direction",
                "lane_type": "driving",
                "road_rule": road_rule,
                "lane_direction": lane_direction,
                "station_direction": direction,
                "successor_identity": list(successor_identity),
            }
        else:
            direction = route_identity_directions(
                [LaneSurfaceSample(**sample) for sample in samples],
                station_allowance_m,
            )[0][1]
            if index == 0:
                predecessor_direction_evidence = {
                    "source": "ordered_station_samples",
                    "successor_identity": list(successor_identity),
                }
        directions.append((identity, direction))
    directions = tuple(directions)

    bounds_by_identity = {
        (bounds.road_id, bounds.section_id): bounds
        for bounds in parse_opendrive_lane_section_bounds(opendrive_xml)
    }
    corridor_samples = []
    boundary_receipts = []
    boundary_samples = []
    for (identity, direction), (_, samples) in zip(directions, groups):
        bounds: Optional[LaneSectionBounds] = bounds_by_identity.get(identity[:2])
        if bounds is None or any(
            sample["s"] < bounds.start_s or sample["s"] > bounds.end_s
            for sample in samples
        ):
            raise ValueError("route corridor identity has invalid lane-section bounds")
        junction_states = {sample["is_junction"] for sample in samples}
        if len(junction_states) != 1:
            raise ValueError("route corridor junction state is inconsistent")
        is_junction = junction_states.pop()
        exact_entry_s = bounds.start_s if direction == 1 else bounds.end_s
        exact_exit_s = bounds.end_s if direction == 1 else bounds.start_s
        lookup_entry_s = exact_entry_s + direction * station_allowance_m
        lookup_exit_s = exact_exit_s - direction * station_allowance_m
        if not (
            bounds.start_s < lookup_entry_s < bounds.end_s
            and bounds.start_s < lookup_exit_s < bounds.end_s
        ):
            raise ValueError("route corridor boundary lookup must stay inside section")
        entry = _boundary_sample_payload(
            map_api,
            identity,
            lookup_entry_s,
            station_allowance_m,
            is_junction,
        )
        exit_sample = _boundary_sample_payload(
            map_api,
            identity,
            lookup_exit_s,
            station_allowance_m,
            is_junction,
        )
        ordered = sorted(
            [entry, *samples, exit_sample], key=lambda sample: direction * sample["s"]
        )
        deduplicated = []
        for sample in ordered:
            if (
                not deduplicated
                or abs(sample["s"] - deduplicated[-1]["s"])
                > station_allowance_m
            ):
                deduplicated.append(sample)
        corridor_samples.extend(deduplicated)
        entry_xyz = [entry[axis] for axis in ("x", "y", "z")]
        exit_xyz = [exit_sample[axis] for axis in ("x", "y", "z")]
        boundary_samples.append((entry_xyz, exit_xyz))
        boundary_receipts.append(
            {
                "identity": list(identity),
                "direction": direction,
                "exact_entry_s": exact_entry_s,
                "exact_exit_s": exact_exit_s,
                "lookup_entry_s": lookup_entry_s,
                "lookup_exit_s": lookup_exit_s,
                "entry_xyz": entry_xyz,
                "exit_xyz": exit_xyz,
                "contact_to_next_m": None,
                "identity_verified": True,
            }
        )

    contact_gaps = []
    for index, (left, right) in enumerate(zip(boundary_samples, boundary_samples[1:])):
        gap = math.dist(left[1], right[0])
        if gap > contact_tolerance_m:
            raise ValueError("route corridor boundary contact exceeds tolerance")
        contact_gaps.append(gap)
        boundary_receipts[index]["contact_to_next_m"] = gap
    directed_edges = [
        [list(left[0]), list(right[0])]
        for left, right in zip(directions, directions[1:])
    ]
    payload = {
        "schema_version": CARLA_ROUTE_CORRIDOR_SCHEMA,
        "map_sha256": hashlib.sha256(opendrive_xml.encode("utf-8")).hexdigest(),
        "route_sample_step_m": float(route_sample_step_m),
        "station_allowance_m": float(station_allowance_m),
        "contact_tolerance_m": float(contact_tolerance_m),
        "route_samples": corridor_samples,
        "directed_edges": directed_edges,
        "identity_directions": [
            [list(identity), direction] for identity, direction in directions
        ],
        "predecessor_receipt": {
            "predecessor_count": 1,
            "route_step_m": float(route_sample_step_m),
            "identity": list(_waypoint_identity(predecessors[0])),
            "s": float(predecessors[0].s),
            "direction": directions[0][1],
            "direction_evidence": predecessor_direction_evidence,
        },
        "boundary_receipts": boundary_receipts,
        "max_contact_gap_m": max(contact_gaps, default=0.0),
    }
    payload["corridor_sha256"] = canonical_json_sha256(payload)
    return payload


def _reject_forbidden_source_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in _FORBIDDEN_SOURCE_PARTS):
                raise ValueError("forbidden source field: %s" % key)
            _reject_forbidden_source_fields(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_forbidden_source_fields(child)


def _state(value: Any, name: str) -> np.ndarray:
    state = np.asarray(value, dtype=np.float64).reshape(-1)
    if state.shape != (7,) or not np.isfinite(state).all():
        raise ValueError("%s must contain finite x,y,vx,vy,ax,ay,heading" % name)
    return state


def build_carla_history_batch(
    frames: Sequence[Mapping[str, Any]],
) -> Tuple[np.ndarray, SimpleNamespace]:
    """Encode 31 official CARLA tick snapshots for the shared materializer."""
    _reject_forbidden_source_fields(frames)
    if len(frames) != 31:
        raise ValueError("CARLA history must contain 31 frames")
    timestamps = np.asarray(
        [frame["timestamp_us"] for frame in frames], dtype=np.int64
    )
    if not np.all(np.diff(timestamps) == 100_000):
        raise ValueError("CARLA history timestamps must be uniform 0.1s ticks")

    ego_states = [_state(frame["ego_state"], "ego_state") for frame in frames]
    ego_extents = np.asarray([frame["ego_extent"] for frame in frames], dtype=np.float32)
    if ego_extents.shape != (31, 3) or not np.isfinite(ego_extents).all():
        raise ValueError("ego_extent must contain 31 finite length,width,height rows")
    if np.any(ego_extents <= 0.0):
        raise ValueError("ego extents must be positive")
    current = ego_states[-1]
    c, s = math.cos(float(current[6])), math.sin(float(current[6]))
    rotation = np.array([[c, s], [-s, c]], dtype=np.float64)
    transform = np.eye(3, dtype=np.float64)
    transform[:2, :2] = rotation
    transform[:2, 2] = -rotation @ current[:2]

    ego_history = np.zeros((31, 8), dtype=np.float32)
    for index, state in enumerate(ego_states):
        ego_history[index, :6] = state[:6]
        ego_history[index, 6:] = [math.sin(state[6]), math.cos(state[6])]

    actor_frames = []
    for frame in frames:
        values = {str(actor["track_id"]): actor for actor in frame.get("actors", [])}
        if len(values) != len(frame.get("actors", [])):
            raise ValueError("CARLA actor track IDs must be unique within a tick")
        actor_frames.append(values)
    active = actor_frames[-1]
    ordered = sorted(
        active,
        key=lambda track_id: (
            float(
                np.linalg.norm(
                    _state(active[track_id]["state"], "actor state")[:2]
                    - current[:2]
                )
            ),
            track_id,
        ),
    )
    histories = np.zeros((len(ordered), 31, 8), dtype=np.float32)
    extents = np.zeros((len(ordered), 31, 3), dtype=np.float32)
    lengths = np.zeros(len(ordered), dtype=np.int64)
    types = np.zeros(len(ordered), dtype=np.float32)
    for actor_index, track_id in enumerate(ordered):
        contiguous = []
        for values in reversed(actor_frames):
            actor = values.get(track_id)
            if actor is None:
                break
            contiguous.append(actor)
        contiguous.reverse()
        lengths[actor_index] = len(contiguous)
        types[actor_index] = float(contiguous[-1]["type_id"])
        for state_index, actor in enumerate(contiguous):
            state = _state(actor["state"], "actor state")
            local_xy = rotation @ (state[:2] - current[:2])
            local_velocity = rotation @ state[2:4]
            local_acceleration = rotation @ state[4:6]
            local_heading = math.atan2(
                math.sin(state[6] - current[6]), math.cos(state[6] - current[6])
            )
            histories[actor_index, state_index] = [
                local_xy[0],
                local_xy[1],
                local_velocity[0],
                local_velocity[1],
                local_acceleration[0],
                local_acceleration[1],
                math.sin(local_heading),
                math.cos(local_heading),
            ]
            extent = np.asarray(actor["extent"], dtype=np.float32).reshape(-1)
            if extent.shape != (3,) or not np.isfinite(extent).all() or np.any(extent <= 0):
                raise ValueError("actor extent must contain positive length,width,height")
            extents[actor_index, state_index] = extent

    return timestamps, SimpleNamespace(
        dt=np.array([0.1], dtype=np.float32),
        history_pad_dir=np.array(1, dtype=np.int64),
        agent_hist=ego_history[None],
        agent_hist_len=np.array([31], dtype=np.int64),
        agent_hist_extent=ego_extents[None],
        curr_agent_state=np.asarray([current], dtype=np.float64),
        neigh_hist=histories[None],
        neigh_hist_len=lengths[None],
        neigh_hist_extents=extents[None],
        neigh_types=types[None],
        agents_from_world_tf=transform[None],
    )


def build_route_lifting_context(
    *,
    route_source: str,
    route_samples: Sequence[Mapping[str, Any]],
    directed_edges: Sequence[Sequence[Sequence[Any]]],
    route_sample_step_m: float,
    tolerances: LiftingTolerances,
    map_sha256: str,
) -> RouteLiftingContext:
    """Freeze the decision-time route samples into the pure lifting contract."""
    if route_source != "current_map_topology_successors":
        raise ValueError("route source must be current_map_topology_successors")
    _reject_forbidden_source_fields(route_samples)

    samples = []
    for raw in route_samples:
        if set(raw) != _ROUTE_SAMPLE_FIELDS:
            raise ValueError("route sample fields do not match the frozen contract")
        if (
            not isinstance(raw["road_id"], str)
            or not raw["road_id"]
            or isinstance(raw["section_id"], bool)
            or not isinstance(raw["section_id"], int)
            or isinstance(raw["lane_id"], bool)
            or not isinstance(raw["lane_id"], int)
            or not isinstance(raw["is_junction"], bool)
        ):
            raise ValueError("route sample identity metadata is invalid")
        samples.append(
            LaneSurfaceSample(
                road_id=raw["road_id"],
                section_id=raw["section_id"],
                lane_id=raw["lane_id"],
                s=float(raw["s"]),
                x=float(raw["x"]),
                y=float(raw["y"]),
                z=float(raw["z"]),
                lane_width=float(raw["lane_width"]),
                is_junction=raw["is_junction"],
            )
        )

    def identity(raw: Sequence[Any]) -> Tuple[str, int, int]:
        if (
            len(raw) != 3
            or not isinstance(raw[0], str)
            or not raw[0]
            or isinstance(raw[1], bool)
            or not isinstance(raw[1], int)
            or isinstance(raw[2], bool)
            or not isinstance(raw[2], int)
        ):
            raise ValueError("route edge identity is invalid")
        return (raw[0], raw[1], raw[2])

    edges = []
    for raw in directed_edges:
        if len(raw) != 2:
            raise ValueError("route edge must contain source and target identities")
        edges.append((identity(raw[0]), identity(raw[1])))

    directions = route_identity_directions(
        samples, tolerances.continuity_epsilon_m
    )
    route_graph_sha256 = canonical_json_sha256(
        {
            "identity_directions": [
                [list(identity), direction] for identity, direction in directions
            ],
            "directed_edges": edges,
        }
    )
    source_sha256 = canonical_json_sha256(
        {
            "route_source": route_source,
            "route_samples": [asdict(sample) for sample in samples],
            "route_sample_step_m": float(route_sample_step_m),
            "tolerances": asdict(tolerances),
            "map_sha256": map_sha256,
            "route_graph_sha256": route_graph_sha256,
        }
    )
    context = RouteLiftingContext(
        samples=tuple(samples),
        edges=tuple(edges),
        identity_directions=directions,
        route_sample_step_m=float(route_sample_step_m),
        tolerances=tolerances,
        map_sha256=map_sha256,
        source_sha256=source_sha256,
        route_graph_sha256=route_graph_sha256,
    )
    _validate_lifting_context(context)
    return context


def materialize_carla_snapshot(
    *,
    timestamps_us: Any,
    decision_timestamp_us: int,
    traffic_timestamp_us: Optional[int],
    batch: Any,
    decision_context: Mapping[str, Any],
    source_metadata: Mapping[str, Any],
) -> CausalDPMaterialization:
    """Validate one source-only CARLA tick and reuse the fixed causal boundary."""
    _reject_forbidden_source_fields(source_metadata)
    timestamps = np.asarray(timestamps_us)
    if timestamps.shape != (31,) or timestamps.dtype.kind not in "iu":
        raise ValueError("CARLA history must contain 31 timestamps")
    if not np.all(np.diff(timestamps) == 100_000):
        raise ValueError("CARLA history timestamps must be uniform 0.1s ticks")
    decision = int(decision_timestamp_us)
    if int(timestamps[-1]) != decision:
        raise ValueError("CARLA history must end at the decision tick")
    traffic_available = decision_context.get("traffic_light_state_available")
    if traffic_available is True and (
        traffic_timestamp_us is None or int(traffic_timestamp_us) != decision
    ):
        raise ValueError("CARLA traffic timestamp must equal the decision tick")
    if decision_context.get("route_source") != "current_map_topology_successors":
        raise ValueError("CARLA route must use current_map_topology_successors")

    materialized = materialize_causal_dp_input(batch, decision_context)
    return CausalDPMaterialization(
        dp_input=materialized.dp_input,
        metadata={
            **materialized.metadata,
            "source": "official_carla_snapshot",
            "observable_dynamic_limit": 32,
            "observable_static_limit": 5,
            "source_metadata": dict(source_metadata),
        },
    )
