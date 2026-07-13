from __future__ import annotations

import math
from dataclasses import asdict
from types import SimpleNamespace
from typing import Any, Mapping, Optional, Sequence, Tuple

import numpy as np

from camp_core.integrations.carla_exact_speed_source import (
    LaneSurfaceSample,
    LiftingTolerances,
    RouteLiftingContext,
    _validate_lifting_context,
    canonical_json_sha256,
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
