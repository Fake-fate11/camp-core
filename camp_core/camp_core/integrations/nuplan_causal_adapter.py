from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import sqlite3
import struct
from typing import Any, Mapping, Sequence
from types import SimpleNamespace

import numpy as np

from camp_core.integrations.diffusion_planner_causal_atoms import (
    CANDIDATE_LOCAL_EXACT_SPEED,
    FULL_WINDOW_EXACT_SPEED,
)


class NuPlanCausalSourceError(ValueError):
    """Raised when nuPlan source data cannot satisfy the causal DP contract."""


_STATIC_OBJECT_TYPES = {
    "czone_sign": (1.0, 0.0, 0.0, 0.0),
    "barrier": (0.0, 1.0, 0.0, 0.0),
    "traffic_cone": (0.0, 0.0, 1.0, 0.0),
    "generic_object": (0.0, 0.0, 0.0, 1.0),
}


@dataclass(frozen=True)
class EncodedRouteLane:
    tensor: np.ndarray
    speed_limit_mps: float | None


@dataclass(frozen=True)
class NuPlanRouteSnapshot:
    decision_id: str
    decision_timestamp_us: int
    source_dt_s: float
    current_roadblock_id: str
    route_roadblock_ids: tuple[str, ...]
    mission_goal_pose: np.ndarray
    route_lanes: np.ndarray
    route_has_speed_limit: np.ndarray
    route_speed_limit: np.ndarray
    traffic_light_state_available: bool
    raw_route_roadblock_ids: tuple[str, ...] = ()
    collapsed_consecutive_roadblock_ids: tuple[str, ...] = ()
    route_lane_mapping: tuple[Mapping[str, object], ...] = ()


def decode_projected_gpkg_geometry(blob: bytes, projected_crs: str):
    data = bytes(blob)
    if len(data) < 9 or data[:2] != b"GP" or data[2] != 0:
        raise NuPlanCausalSourceError("unsupported GeoPackage geometry header")
    flags = data[3]
    byte_order = "<" if flags & 1 else ">"
    source_srs = struct.unpack(f"{byte_order}i", data[4:8])[0]
    envelope_sizes = {0: 0, 1: 4, 2: 6, 3: 6, 4: 8}
    envelope_type = (flags >> 1) & 0x07
    if envelope_type not in envelope_sizes:
        raise NuPlanCausalSourceError("unsupported GeoPackage geometry envelope")
    wkb_offset = 8 + envelope_sizes[envelope_type] * 8
    if len(data) <= wkb_offset:
        raise NuPlanCausalSourceError("GeoPackage geometry contains no WKB payload")
    try:
        from pyproj import Transformer
        from shapely import from_wkb
        from shapely.ops import transform
    except ImportError as exc:
        raise NuPlanCausalSourceError(
            "Shapely>=2.0 and pyproj>=3.6 are required; install camp_core[nuplan]"
        ) from exc
    geometry = from_wkb(data[wkb_offset:])
    transformer = Transformer.from_crs(
        f"EPSG:{source_srs}", str(projected_crs), always_xy=True
    )
    return transform(transformer.transform, geometry)


def load_nuplan_route_snapshot(
    db_path: str | Path,
    map_path: str | Path,
    lidar_pc_token: str | bytes,
) -> NuPlanRouteSnapshot:
    token = _token_bytes(lidar_pc_token)
    db = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
    map_db = sqlite3.connect(f"file:{Path(map_path).as_posix()}?mode=ro", uri=True)
    try:
        decision = db.execute(
            """
            SELECT l.scene_token, l.timestamp, e.x, e.y
            FROM lidar_pc AS l
            JOIN ego_pose AS e ON e.token = l.ego_pose_token
            WHERE l.token = ?
            """,
            (token,),
        ).fetchone()
        if decision is None:
            raise NuPlanCausalSourceError("lidar_pc_token is absent from the nuPlan DB")
        scene_token, decision_timestamp, ego_x, ego_y = decision
        scene = db.execute(
            "SELECT goal_ego_pose_token, roadblock_ids FROM scene WHERE token = ?",
            (scene_token,),
        ).fetchone()
        if scene is None or scene[0] is None or not scene[1]:
            raise NuPlanCausalSourceError("scene requires a mission goal and route")
        raw_route = tuple(str(value) for value in str(scene[1]).split())
        route, collapsed_roadblocks = _collapse_consecutive_route_roadblocks(raw_route)
        goal = db.execute(
            """
            SELECT x, y, qw, qx, qy, qz
            FROM ego_pose
            WHERE token = ?
            """,
            (scene[0],),
        ).fetchone()
        if goal is None:
            raise NuPlanCausalSourceError("scene mission goal does not resolve")
        mission_goal = np.array(
            [goal[0], goal[1], _quaternion_yaw(*goal[2:])], dtype=np.float64
        )
        history_timestamps = [
            row[0]
            for row in db.execute(
                """
                SELECT timestamp
                FROM lidar_pc
                WHERE scene_token = ? AND timestamp <= ?
                ORDER BY timestamp DESC
                LIMIT 80
                """,
                (scene_token, decision_timestamp),
            )
        ][::-1]
        source_dt = derive_source_dt_s(history_timestamps)

        projected_crs_row = map_db.execute(
            "SELECT value FROM meta WHERE key = 'projectedCoordSystem'"
        ).fetchone()
        if projected_crs_row is None or not projected_crs_row[0]:
            raise NuPlanCausalSourceError("map projectedCoordSystem is missing")
        projected_crs = str(projected_crs_row[0])
        current_roadblock = _current_route_roadblock(
            map_db,
            route,
            float(ego_x),
            float(ego_y),
            projected_crs,
        )
        successors = _validated_route_successors(map_db, route)
        route_window = select_mission_route_window(
            route, current_roadblock, successors
        )
        traffic = {
            int(lane_connector_id): str(status).lower()
            for lane_connector_id, status in db.execute(
                """
                SELECT lane_connector_id, status
                FROM traffic_light_status
                WHERE lidar_pc_token = ?
                """,
                (token,),
            )
        }
        candidate_slots = [
            _roadblock_lane_candidates(map_db, roadblock_id, projected_crs)
            for roadblock_id in route_window
        ]
        selected = _connected_lane_path(
            candidate_slots, np.array([ego_x, ego_y], dtype=np.float64)
        )

        route_lanes = np.zeros((25, 20, 33), dtype=np.float64)
        route_has_speed = np.zeros((25, 1), dtype=bool)
        route_speed = np.zeros((25, 1), dtype=np.float32)
        for index, candidate in enumerate(selected):
            status = None
            if candidate["kind"] == "connector":
                status = traffic.get(int(candidate["fid"]))
                if candidate["controlled"] and status is None:
                    status = "unknown"
            encoded = encode_route_lane(
                centerline=np.asarray(candidate["center"].coords),
                left_boundary=np.asarray(candidate["left"].coords),
                right_boundary=np.asarray(candidate["right"].coords),
                speed_limit_mps=candidate["speed_limit_mps"],
                traffic_light_status=status,
                traffic_timestamp_us=(decision_timestamp if status else None),
                decision_timestamp_us=(decision_timestamp if status else None),
                require_speed_limit=False,
            )
            route_lanes[index] = encoded.tensor
            if encoded.speed_limit_mps is not None:
                route_has_speed[index, 0] = True
                route_speed[index, 0] = encoded.speed_limit_mps
        gaps = np.linalg.norm(
            route_lanes[: len(selected) - 1, -1, :2]
            - route_lanes[1 : len(selected), 0, :2],
            axis=1,
        )
        if gaps.size and np.max(gaps) > 8.0:
            raise NuPlanCausalSourceError(
                f"selected mission route is disconnected: max gap={np.max(gaps):.3f}m"
            )
        return NuPlanRouteSnapshot(
            decision_id=f"{bytes(scene_token).hex()}:{token.hex()}",
            decision_timestamp_us=int(decision_timestamp),
            source_dt_s=source_dt,
            current_roadblock_id=current_roadblock,
            route_roadblock_ids=route_window,
            mission_goal_pose=mission_goal,
            route_lanes=route_lanes,
            route_has_speed_limit=route_has_speed,
            route_speed_limit=route_speed,
            traffic_light_state_available=bool(traffic),
            raw_route_roadblock_ids=raw_route,
            collapsed_consecutive_roadblock_ids=collapsed_roadblocks,
            route_lane_mapping=tuple(
                dict(candidate["source_mapping"]) for candidate in selected
            ),
        )
    finally:
        db.close()
        map_db.close()


def materialize_nuplan_decision(
    db_path: str | Path,
    map_path: str | Path,
    lidar_pc_token: str | bytes,
):
    from camp_core.integrations.diffusion_planner_causal_materializer import (
        CausalDPMaterialization,
        materialize_causal_dp_input,
    )

    snapshot = load_nuplan_route_snapshot(db_path, map_path, lidar_pc_token)
    batch = _load_nuplan_batch(
        db_path,
        lidar_pc_token,
        source_dt_s=snapshot.source_dt_s,
    )
    lanes = np.zeros((140, 20, 33), dtype=np.float64)
    lanes[: len(snapshot.route_roadblock_ids)] = snapshot.route_lanes[
        : len(snapshot.route_roadblock_ids)
    ]
    lanes_has_speed = np.zeros((140, 1), dtype=bool)
    lanes_has_speed[:25] = snapshot.route_has_speed_limit
    lanes_speed = np.zeros((140, 1), dtype=np.float32)
    lanes_speed[:25] = snapshot.route_speed_limit
    context = {
        "map_frame": "world",
        "decision_id": snapshot.decision_id,
        "route_source": "nuplan_mission_route_current_roadblock_successors",
        "mission_goal_pose": snapshot.mission_goal_pose,
        "lanes": lanes,
        "lanes_speed_limit": lanes_speed,
        "lanes_has_speed_limit": lanes_has_speed,
        "route_lanes": snapshot.route_lanes,
        "route_lanes_speed_limit": snapshot.route_speed_limit,
        "route_lanes_has_speed_limit": snapshot.route_has_speed_limit,
        "line_strings": np.zeros((60, 20, 4), dtype=np.float32),
        "polygons": np.zeros((10, 40, 3), dtype=np.float32),
        "static_objects": batch.static_objects,
        "turn_indicators": np.zeros(31, dtype=np.int32),
        "turn_indicators_available": False,
        "traffic_light_state_available": snapshot.traffic_light_state_available,
        "ego_wheelbase_m": 3.089,
    }
    materialized = materialize_causal_dp_input(batch, context)
    return CausalDPMaterialization(
        dp_input=materialized.dp_input,
        metadata={
            **materialized.metadata,
            "source": "official_nuplan_saved_state_input",
            "decision_timestamp_us": snapshot.decision_timestamp_us,
            "traffic_light_state_available": snapshot.traffic_light_state_available,
            "route_roadblock_ids": list(snapshot.route_roadblock_ids),
            "raw_route_roadblock_ids": list(snapshot.raw_route_roadblock_ids),
            "collapsed_consecutive_roadblock_ids": list(
                snapshot.collapsed_consecutive_roadblock_ids
            ),
            "route_lane_mapping": [dict(item) for item in snapshot.route_lane_mapping],
        },
    )


def materialize_nuplan_planner_input(
    current_input: Any,
    initialization: Any,
    *,
    speed_source_policy: str = FULL_WINDOW_EXACT_SPEED,
):
    """Materialize the fixed-DP causal schema from one live nuPlan tick."""
    if speed_source_policy not in {
        FULL_WINDOW_EXACT_SPEED,
        CANDIDATE_LOCAL_EXACT_SPEED,
    }:
        raise ValueError("unsupported route speed-source policy")
    for name in ("expert_future", "future_trajectory", "label", "outcome"):
        if getattr(current_input, name, None) is not None:
            raise NuPlanCausalSourceError(
                f"future, label, and outcome fields are forbidden: {name}"
            )
    batch, static_objects = _live_planner_batch(current_input)
    context = _live_planner_context(
        current_input,
        initialization,
        static_objects=static_objects,
        wheelbase=float(
            current_input.history.ego_states[-1]
            .car_footprint.vehicle_parameters.wheel_base
        ),
        speed_source_policy=speed_source_policy,
    )
    from camp_core.integrations.diffusion_planner_causal_materializer import (
        CausalDPMaterialization,
        materialize_causal_dp_input,
    )

    materialized = materialize_causal_dp_input(batch, context)
    return CausalDPMaterialization(
        dp_input=materialized.dp_input,
        metadata={
            **materialized.metadata,
            "source": "official_nuplan_planner_input",
            "observable_dynamic_limit": 32,
            "observable_static_limit": 5,
            "speed_source_policy": speed_source_policy,
        },
    )


def _causal_history_view(history: Any) -> SimpleNamespace:
    ego_states = list(history.ego_states)
    observations = list(history.observations)
    if len(ego_states) != len(observations):
        raise NuPlanCausalSourceError("ego and observation history must align")
    source_dt = float(history.sample_interval)
    if np.isclose(source_dt, 0.05, rtol=0.0, atol=1e-8):
        count, stride = 61, 2
    elif np.isclose(source_dt, 0.1, rtol=0.0, atol=1e-8):
        count, stride = 31, 1
    else:
        raise NuPlanCausalSourceError(
            "history must use 0.05 or 0.1 second samples"
        )
    if len(ego_states) < count:
        raise NuPlanCausalSourceError("history must cover three seconds")
    ego_states = ego_states[-count:]
    observations = observations[-count:]
    timestamps = np.asarray(
        [_state_time_us(state) for state in ego_states], dtype=np.int64
    )
    if not np.allclose(
        np.diff(timestamps) / 1_000_000.0,
        source_dt,
        rtol=0.0,
        atol=1e-3,
    ):
        raise NuPlanCausalSourceError("history timestamps must be uniformly sampled")
    return SimpleNamespace(
        ego_states=ego_states[::stride],
        observations=observations[::stride],
        sample_interval=0.1,
    )


def _live_planner_batch(current_input: Any) -> tuple[SimpleNamespace, np.ndarray]:
    history = _causal_history_view(current_input.history)
    ego_states = list(history.ego_states)
    observations = list(history.observations)
    if len(ego_states) < 31 or len(observations) < 31:
        raise NuPlanCausalSourceError("live history must contain at least 31 ticks")
    ego_states = ego_states[-31:]
    observations = observations[-31:]
    source_dt = float(history.sample_interval)
    if not np.isclose(source_dt, 0.1, rtol=0.0, atol=1e-8):
        raise NuPlanCausalSourceError("live history dt must equal 0.1 seconds")
    timestamps = np.asarray([_state_time_us(state) for state in ego_states])
    if not np.allclose(np.diff(timestamps), 100_000, rtol=0.0, atol=2_000):
        raise NuPlanCausalSourceError("live ego timestamps must be regular 0.1s ticks")
    decision_time = _iteration_time_us(current_input.iteration)
    if int(timestamps[-1]) != decision_time:
        raise NuPlanCausalSourceError("live history must end at the decision tick")

    current = ego_states[-1]
    current_pose = current.rear_axle
    heading = float(current_pose.heading)
    rotation = np.array(
        [[math.cos(heading), math.sin(heading)], [-math.sin(heading), math.cos(heading)]],
        dtype=np.float64,
    )
    transform = np.eye(3, dtype=np.float64)
    transform[:2, :2] = rotation
    transform[:2, 2] = -rotation @ np.array(
        [float(current_pose.x), float(current_pose.y)], dtype=np.float64
    )

    agent_hist = np.zeros((31, 8), dtype=np.float64)
    agent_extents = np.zeros((31, 3), dtype=np.float32)
    for index, state in enumerate(ego_states):
        pose = state.rear_axle
        velocity = state.dynamic_car_state.rear_axle_velocity_2d
        acceleration = state.dynamic_car_state.rear_axle_acceleration_2d
        agent_hist[index] = [
            pose.x,
            pose.y,
            velocity.x,
            velocity.y,
            acceleration.x,
            acceleration.y,
            math.sin(pose.heading),
            math.cos(pose.heading),
        ]
        footprint = state.car_footprint
        agent_extents[index] = [footprint.length, footprint.width, 1.0]

    dynamic_by_tick = [_dynamic_objects(observation) for observation in observations]
    active = dynamic_by_tick[-1]
    ordered = sorted(
        active,
        key=lambda item: (
            float(
                np.linalg.norm(
                    np.array([item.center.x, item.center.y])
                    - np.array([current_pose.x, current_pose.y])
                )
            ),
            str(item.track_token),
        ),
    )
    histories = np.zeros((len(ordered), 31, 8), dtype=np.float32)
    lengths = np.zeros(len(ordered), dtype=np.int64)
    extents = np.zeros((len(ordered), 31, 3), dtype=np.float32)
    types = np.zeros(len(ordered), dtype=np.float32)
    for neighbor_index, active_object in enumerate(ordered):
        token = str(active_object.track_token)
        continuous = []
        for objects in reversed(dynamic_by_tick):
            match = next(
                (item for item in objects if str(item.track_token) == token), None
            )
            if match is None:
                break
            continuous.append(match)
        continuous.reverse()
        lengths[neighbor_index] = len(continuous)
        types[neighbor_index] = _dynamic_type_id(active_object)
        for state_index, item in enumerate(continuous):
            xy = np.array([item.center.x, item.center.y], dtype=np.float64)
            local_xy = transform @ np.array([xy[0], xy[1], 1.0])
            velocity = np.array([item.velocity.x, item.velocity.y]) @ rotation.T
            local_heading = math.atan2(
                math.sin(float(item.center.heading) - heading),
                math.cos(float(item.center.heading) - heading),
            )
            histories[neighbor_index, state_index] = [
                local_xy[0],
                local_xy[1],
                velocity[0],
                velocity[1],
                0.0,
                0.0,
                math.sin(local_heading),
                math.cos(local_heading),
            ]
            extents[neighbor_index, state_index] = [
                item.box.length,
                item.box.width,
                item.box.height,
            ]

    static_objects = _live_static_objects(observations[-1], current_pose)
    velocity = current.dynamic_car_state.rear_axle_velocity_2d
    acceleration = current.dynamic_car_state.rear_axle_acceleration_2d
    batch = SimpleNamespace(
        dt=np.array([source_dt], dtype=np.float32),
        history_pad_dir=np.array(1, dtype=np.int64),
        agent_hist=agent_hist[None],
        agent_hist_len=np.array([31], dtype=np.int64),
        agent_hist_extent=agent_extents[None],
        curr_agent_state=np.array(
            [
                [
                    current_pose.x,
                    current_pose.y,
                    velocity.x,
                    velocity.y,
                    acceleration.x,
                    acceleration.y,
                    current_pose.heading,
                ]
            ],
            dtype=np.float64,
        ),
        neigh_hist=histories[None],
        neigh_hist_len=lengths[None],
        neigh_hist_extents=extents[None],
        neigh_types=types[None],
        agents_from_world_tf=transform[None],
    )
    return batch, static_objects


def _live_planner_context(
    current_input: Any,
    initialization: Any,
    *,
    static_objects: np.ndarray,
    wheelbase: float,
    speed_source_policy: str,
) -> dict[str, Any]:
    route_ids = [str(value) for value in initialization.route_roadblock_ids]
    if not route_ids or len(set(route_ids)) != len(route_ids):
        raise NuPlanCausalSourceError("mission route must be nonempty and unique")
    roadblocks = [_map_roadblock(initialization.map_api, value) for value in route_ids]
    current_pose = current_input.history.ego_states[-1].rear_axle
    current_xy = np.array([current_pose.x, current_pose.y], dtype=np.float64)
    distances = [
        min(
            np.linalg.norm(_polyline(edge.baseline_path.discrete_path) - current_xy, axis=1).min()
            for edge in roadblock.interior_edges
        )
        for roadblock in roadblocks
    ]
    start = int(np.argmin(distances))
    roadblocks = roadblocks[start : start + 25]
    selected = _connected_live_lane_path(roadblocks, current_xy)
    decision_time = _iteration_time_us(current_input.iteration)
    traffic = {}
    for item in current_input.traffic_light_data or []:
        timestamp = int(item.timestamp)
        if timestamp != decision_time:
            raise NuPlanCausalSourceError(
                "traffic-light status must come from the same decision tick"
            )
        traffic[str(item.lane_connector_id)] = str(item.status.name).lower()

    route_lanes = np.zeros((25, 20, 33), dtype=np.float64)
    route_has_speed = np.zeros((25, 1), dtype=bool)
    route_speed = np.zeros((25, 1), dtype=np.float32)
    for index, lane in enumerate(selected):
        encoded = encode_route_lane(
            centerline=_polyline(lane.baseline_path.discrete_path),
            left_boundary=_polyline(lane.left_boundary.discrete_path),
            right_boundary=_polyline(lane.right_boundary.discrete_path),
            speed_limit_mps=lane.speed_limit_mps,
            traffic_light_status=traffic.get(str(lane.id)),
            traffic_timestamp_us=decision_time if str(lane.id) in traffic else None,
            decision_timestamp_us=decision_time,
            require_speed_limit=(
                speed_source_policy == FULL_WINDOW_EXACT_SPEED
            ),
        )
        route_lanes[index] = encoded.tensor
        if encoded.speed_limit_mps is not None:
            route_has_speed[index, 0] = True
            route_speed[index, 0] = encoded.speed_limit_mps
    lanes = np.zeros((140, 20, 33), dtype=np.float64)
    lanes[: len(selected)] = route_lanes[: len(selected)]
    lanes_has_speed = np.zeros((140, 1), dtype=bool)
    lanes_speed = np.zeros((140, 1), dtype=np.float32)
    lanes_has_speed[: len(selected)] = route_has_speed[: len(selected)]
    lanes_speed[: len(selected)] = route_speed[: len(selected)]
    goal = initialization.mission_goal
    return {
        "map_frame": "world",
        "decision_id": f"{int(current_input.iteration.index)}:{decision_time}",
        "route_source": "nuplan_mission_route_current_roadblock_successors",
        "mission_goal_pose": np.array([goal.x, goal.y, goal.heading]),
        "lanes": lanes,
        "lanes_has_speed_limit": lanes_has_speed,
        "lanes_speed_limit": lanes_speed,
        "route_lanes": route_lanes,
        "route_lanes_has_speed_limit": route_has_speed,
        "route_lanes_speed_limit": route_speed,
        "line_strings": np.zeros((60, 20, 4), dtype=np.float32),
        "polygons": np.zeros((10, 40, 3), dtype=np.float32),
        "static_objects": static_objects,
        "turn_indicators": np.zeros(31, dtype=np.int32),
        "turn_indicators_available": False,
        "traffic_light_state_available": bool(traffic),
        "ego_wheelbase_m": wheelbase,
    }


def _map_roadblock(map_api: Any, roadblock_id: str) -> Any:
    try:
        from nuplan.common.maps.maps_datatypes import SemanticMapLayer

        layers = (SemanticMapLayer.ROADBLOCK, SemanticMapLayer.ROADBLOCK_CONNECTOR)
    except ImportError:
        layers = ("ROADBLOCK", "ROADBLOCK_CONNECTOR")
    for layer in layers:
        value = map_api.get_map_object(roadblock_id, layer)
        if value is not None:
            if not value.interior_edges:
                raise NuPlanCausalSourceError(
                    f"route roadblock {roadblock_id} has no lanes"
                )
            return value
    raise NuPlanCausalSourceError(f"route roadblock {roadblock_id} is missing")


def _connected_live_lane_path(roadblocks: Sequence[Any], current_xy: np.ndarray):
    candidates = [list(roadblock.interior_edges) for roadblock in roadblocks]
    first = min(
        candidates[0],
        key=lambda lane: (
            np.linalg.norm(_polyline(lane.baseline_path.discrete_path) - current_xy, axis=1).min(),
            str(lane.id),
        ),
    )
    result = [first]
    for slot in candidates[1:]:
        outgoing = {str(edge.id) for edge in getattr(result[-1], "outgoing_edges", [])}
        connected = [lane for lane in slot if str(lane.id) in outgoing]
        if not connected:
            raise NuPlanCausalSourceError(
                f"mission route is disconnected after lane {result[-1].id}"
            )
        result.append(sorted(connected, key=lambda lane: str(lane.id))[0])
    return result


def _polyline(points: Sequence[Any]) -> np.ndarray:
    result = np.asarray([[point.x, point.y] for point in points], dtype=np.float64)
    if result.shape[0] < 2 or not np.isfinite(result).all():
        raise NuPlanCausalSourceError("map polyline must contain finite points")
    return result


def _objects(observation: Any) -> list[Any]:
    return list(observation.tracked_objects.tracked_objects)


def _dynamic_objects(observation: Any) -> list[Any]:
    allowed = {"VEHICLE", "PEDESTRIAN", "BICYCLE", "MOTORCYCLE"}
    return [
        item
        for item in _objects(observation)
        if str(item.tracked_object_type.name).upper() in allowed
    ]


def _dynamic_type_id(item: Any) -> float:
    return {
        "VEHICLE": 1.0,
        "PEDESTRIAN": 2.0,
        "BICYCLE": 3.0,
        "MOTORCYCLE": 4.0,
    }[str(item.tracked_object_type.name).upper()]


def _live_static_objects(observation: Any, ego_pose: Any) -> np.ndarray:
    encoded = []
    ego_xy = np.array([ego_pose.x, ego_pose.y], dtype=np.float64)
    for item in _objects(observation):
        kind = str(item.tracked_object_type.name).lower()
        if kind not in _STATIC_OBJECT_TYPES:
            continue
        row = np.array(
            [
                item.center.x,
                item.center.y,
                math.cos(item.center.heading),
                math.sin(item.center.heading),
                item.box.width,
                item.box.length,
                *_STATIC_OBJECT_TYPES[kind],
            ],
            dtype=np.float32,
        )
        encoded.append(
            (float(np.linalg.norm(row[:2] - ego_xy)), str(item.track_token), row)
        )
    encoded.sort(key=lambda item: (item[0], item[1]))
    result = np.zeros((5, 10), dtype=np.float32)
    for index, (_, _, row) in enumerate(encoded[:5]):
        result[index] = row
    return result


def _state_time_us(state: Any) -> int:
    value = getattr(state, "time_us", None)
    if value is None:
        value = state.time_point.time_us
    return int(value)


def _iteration_time_us(iteration: Any) -> int:
    value = getattr(iteration, "time_us", None)
    if value is None:
        value = iteration.time_point.time_us
    return int(value)


def load_nuplan_expert_ego_future(
    db_path: str | Path,
    lidar_pc_token: str | bytes,
    *,
    target_dt_s: float,
    horizon_steps: int = 80,
) -> np.ndarray:
    if not np.isfinite(target_dt_s) or target_dt_s <= 0.0:
        raise NuPlanCausalSourceError("target_dt_s must be finite and positive")
    if isinstance(horizon_steps, bool) or horizon_steps < 1:
        raise NuPlanCausalSourceError("horizon_steps must be a positive integer")
    token = _token_bytes(lidar_pc_token)
    db = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
    try:
        decision = db.execute(
            "SELECT scene_token, timestamp FROM lidar_pc WHERE token = ?",
            (token,),
        ).fetchone()
        if decision is None:
            raise NuPlanCausalSourceError("decision lidar token is absent")
        rows = db.execute(
            """
            SELECT l.timestamp, e.x, e.y, e.qw, e.qx, e.qy, e.qz
            FROM lidar_pc AS l
            JOIN ego_pose AS e ON e.token = l.ego_pose_token
            WHERE l.scene_token = ? AND l.timestamp >= ?
            ORDER BY l.timestamp
            """,
            decision,
        ).fetchall()
    finally:
        db.close()

    timestamps = np.asarray([row[0] for row in rows], dtype=np.int64)
    if timestamps.size < 2 or np.any(np.diff(timestamps) <= 0):
        raise NuPlanCausalSourceError(
            "expert timestamps must be strictly increasing"
        )
    source_t = (timestamps - int(decision[1])) / 1_000_000.0
    target_t = (
        np.arange(1, int(horizon_steps) + 1, dtype=np.float64) * target_dt_s
    )
    if source_t[0] != 0.0 or source_t[-1] < target_t[-1]:
        raise NuPlanCausalSourceError(
            "expert future does not bracket target horizon; extrapolation forbidden"
        )
    xy = np.asarray([[row[1], row[2]] for row in rows], dtype=np.float64)
    yaw = np.unwrap(
        np.asarray([_quaternion_yaw(*row[3:7]) for row in rows], dtype=np.float64)
    )
    if not np.isfinite(xy).all() or not np.isfinite(yaw).all():
        raise NuPlanCausalSourceError("expert future poses must be finite")

    decision_xy = xy[0]
    decision_yaw = float(yaw[0])
    world_xy = np.column_stack(
        [np.interp(target_t, source_t, xy[:, axis]) for axis in range(2)]
    )
    c, s = math.cos(decision_yaw), math.sin(decision_yaw)
    rotation = np.array([[c, s], [-s, c]], dtype=np.float64)
    local_xy = (world_xy - decision_xy) @ rotation.T
    interpolated_yaw = np.interp(target_t, source_t, yaw) - decision_yaw
    local_yaw = np.arctan2(np.sin(interpolated_yaw), np.cos(interpolated_yaw))
    return np.column_stack([local_xy, local_yaw]).astype(np.float32)


def _load_nuplan_batch(
    db_path: str | Path,
    lidar_pc_token: str | bytes,
    *,
    source_dt_s: float,
) -> SimpleNamespace:
    token = _token_bytes(lidar_pc_token)
    db = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
    try:
        decision = db.execute(
            "SELECT scene_token, timestamp FROM lidar_pc WHERE token = ?",
            (token,),
        ).fetchone()
        if decision is None:
            raise NuPlanCausalSourceError("lidar_pc_token is absent from the nuPlan DB")
        lidar_rows = db.execute(
            """
            SELECT l.token, l.timestamp,
                   e.x, e.y, e.vx, e.vy,
                   e.acceleration_x, e.acceleration_y,
                   e.qw, e.qx, e.qy, e.qz
            FROM lidar_pc AS l
            JOIN ego_pose AS e ON e.token = l.ego_pose_token
            WHERE l.scene_token = ? AND l.timestamp <= ?
            ORDER BY l.timestamp DESC
            LIMIT 80
            """,
            decision,
        ).fetchall()[::-1]
        if len(lidar_rows) < 2:
            raise NuPlanCausalSourceError("ego history is too short")
        timestamps = np.asarray([row[1] for row in lidar_rows], dtype=np.int64)
        if int(timestamps[-1]) != int(decision[1]):
            raise NuPlanCausalSourceError("ego history does not end at the decision tick")
        if (timestamps[-1] - timestamps[0]) / 1_000_000.0 < 3.0:
            raise NuPlanCausalSourceError("ego history does not cover three seconds")

        ego_history = np.zeros((len(lidar_rows), 8), dtype=np.float64)
        headings = []
        for index, row in enumerate(lidar_rows):
            yaw = _quaternion_yaw(*row[8:12])
            headings.append(yaw)
            ego_history[index] = [
                row[2],
                row[3],
                row[4],
                row[5],
                row[6],
                row[7],
                math.sin(yaw),
                math.cos(yaw),
            ]
        current = lidar_rows[-1]
        static_objects = _load_static_objects(
            db,
            token,
            np.asarray(current[2:4], dtype=np.float64),
        )
        current_yaw = headings[-1]
        rotation = np.array(
            [
                [math.cos(current_yaw), math.sin(current_yaw)],
                [-math.sin(current_yaw), math.cos(current_yaw)],
            ],
            dtype=np.float64,
        )
        transform = np.eye(3, dtype=np.float64)
        transform[:2, :2] = rotation
        transform[:2, 2] = -rotation @ np.asarray(current[2:4], dtype=np.float64)

        neighbors, neighbor_lengths, neighbor_extents, neighbor_types = (
            _load_neighbor_histories(db, lidar_rows, rotation, current_yaw)
        )
        batch = SimpleNamespace()
        batch.dt = np.array([source_dt_s], dtype=np.float32)
        batch.history_pad_dir = np.array(1, dtype=np.int64)
        batch.agent_hist = ego_history[None]
        batch.agent_hist_len = np.array([len(ego_history)], dtype=np.int64)
        batch.agent_hist_extent = np.tile(
            np.array([5.176, 2.297, 1.777], dtype=np.float32),
            (1, len(ego_history), 1),
        )
        batch.curr_agent_state = np.array(
            [
                [
                    current[2],
                    current[3],
                    current[4],
                    current[5],
                    current[6],
                    current[7],
                    current_yaw,
                ]
            ],
            dtype=np.float64,
        )
        batch.neigh_hist = neighbors[None]
        batch.neigh_hist_len = neighbor_lengths[None]
        batch.neigh_hist_extents = neighbor_extents[None]
        batch.neigh_types = neighbor_types[None]
        batch.agents_from_world_tf = transform[None]
        batch.static_objects = static_objects
        return batch
    finally:
        db.close()


def _load_static_objects(
    db: sqlite3.Connection,
    lidar_pc_token: bytes,
    current_ego_xy: np.ndarray,
) -> np.ndarray:
    rows = db.execute(
        """
        SELECT b.track_token, b.x, b.y, b.yaw, b.width, b.length, c.name
        FROM lidar_box AS b
        JOIN track AS t ON t.token = b.track_token
        JOIN category AS c ON c.token = t.category_token
        WHERE b.lidar_pc_token = ?
        """,
        (lidar_pc_token,),
    ).fetchall()
    encoded = []
    ego_xy = np.asarray(current_ego_xy, dtype=np.float64).reshape(2)
    for track_token, x, y, yaw, width, length, category in rows:
        name = str(category).lower()
        if name not in _STATIC_OBJECT_TYPES:
            continue
        values = np.asarray([x, y, yaw, width, length], dtype=np.float64)
        if (
            not np.isfinite(values).all()
            or float(width) <= 0.0
            or float(length) <= 0.0
        ):
            raise NuPlanCausalSourceError(
                "static object pose and dimensions must be finite and positive"
            )
        row = np.array(
            [
                x,
                y,
                math.cos(yaw),
                math.sin(yaw),
                width,
                length,
                *_STATIC_OBJECT_TYPES[name],
            ],
            dtype=np.float32,
        )
        encoded.append(
            (float(np.linalg.norm(row[:2] - ego_xy)), bytes(track_token), row)
        )
    encoded.sort(key=lambda item: (item[0], item[1]))
    result = np.zeros((5, 10), dtype=np.float32)
    for index, (_, _, row) in enumerate(encoded[:5]):
        result[index] = row
    return result


def _load_neighbor_histories(
    db: sqlite3.Connection,
    lidar_rows: Sequence[Sequence[object]],
    rotation: np.ndarray,
    current_yaw: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    lidar_tokens = [row[0] for row in lidar_rows]
    timestamps = [int(row[1]) for row in lidar_rows]
    placeholders = ",".join("?" for _ in lidar_tokens)
    rows = db.execute(
        f"""
        SELECT l.timestamp, b.track_token,
               b.x, b.y, b.vx, b.vy, b.yaw,
               b.length, b.width, b.height, c.name
        FROM lidar_pc AS l
        JOIN lidar_box AS b ON b.lidar_pc_token = l.token
        JOIN track AS t ON t.token = b.track_token
        JOIN category AS c ON c.token = t.category_token
        WHERE l.token IN ({placeholders})
        ORDER BY l.timestamp
        """,
        lidar_tokens,
    ).fetchall()
    by_track: dict[bytes, dict[int, Sequence[object]]] = {}
    for row in rows:
        category = str(row[10]).lower()
        if category not in {"vehicle", "pedestrian", "bicycle"}:
            continue
        by_track.setdefault(row[1], {})[int(row[0])] = row
    current_timestamp = timestamps[-1]
    active = [values for values in by_track.values() if current_timestamp in values]
    max_history = len(timestamps)
    histories = np.zeros((len(active), max_history, 8), dtype=np.float32)
    lengths = np.zeros(len(active), dtype=np.int64)
    extents = np.zeros((len(active), max_history, 3), dtype=np.float32)
    types = np.zeros(len(active), dtype=np.float32)
    current_ego_xy = np.asarray(lidar_rows[-1][2:4], dtype=np.float64)
    type_ids = {"vehicle": 1.0, "pedestrian": 2.0, "bicycle": 3.0}
    for track_index, values in enumerate(active):
        continuous = []
        for timestamp in reversed(timestamps):
            row = values.get(timestamp)
            if row is None:
                break
            continuous.append(row)
        continuous.reverse()
        lengths[track_index] = len(continuous)
        category = str(continuous[-1][10]).lower()
        types[track_index] = type_ids[category]
        for state_index, row in enumerate(continuous):
            local_xy = (np.asarray(row[2:4]) - current_ego_xy) @ rotation.T
            local_velocity = np.asarray(row[4:6]) @ rotation.T
            local_yaw = math.atan2(
                math.sin(float(row[6]) - current_yaw),
                math.cos(float(row[6]) - current_yaw),
            )
            histories[track_index, state_index] = [
                local_xy[0],
                local_xy[1],
                local_velocity[0],
                local_velocity[1],
                0.0,
                0.0,
                math.sin(local_yaw),
                math.cos(local_yaw),
            ]
            extents[track_index, state_index] = [row[7], row[8], row[9]]
    return histories, lengths, extents, types


def _token_bytes(value: str | bytes) -> bytes:
    if isinstance(value, bytes):
        return value
    try:
        return bytes.fromhex(str(value))
    except ValueError as exc:
        raise NuPlanCausalSourceError("nuPlan token must be hexadecimal") from exc


def _quaternion_yaw(qw: float, qx: float, qy: float, qz: float) -> float:
    return math.atan2(
        2.0 * (float(qw) * float(qz) + float(qx) * float(qy)),
        1.0 - 2.0 * (float(qy) ** 2 + float(qz) ** 2),
    )


def _current_route_roadblock(
    map_db: sqlite3.Connection,
    route: tuple[str, ...],
    ego_x: float,
    ego_y: float,
    projected_crs: str,
) -> str:
    from shapely import Point

    ego = Point(ego_x, ego_y)
    distances = []
    for index, roadblock_id in enumerate(route):
        row = map_db.execute(
            "SELECT geom FROM lane_groups_polygons WHERE fid = ?",
            (roadblock_id,),
        ).fetchone()
        if row is None:
            row = map_db.execute(
                "SELECT geom FROM lane_group_connectors WHERE fid = ?",
                (roadblock_id,),
            ).fetchone()
        if row is None:
            raise NuPlanCausalSourceError(
                f"mission roadblock {roadblock_id} is absent from the map"
            )
        geometry = decode_projected_gpkg_geometry(row[0], projected_crs)
        distances.append((float(geometry.distance(ego)), index, roadblock_id))
    distance, _, roadblock_id = min(distances)
    if distance > 8.0:
        raise NuPlanCausalSourceError(
            f"ego is {distance:.3f}m from the closest mission roadblock"
        )
    return roadblock_id


def _validated_route_successors(
    map_db: sqlite3.Connection, route: tuple[str, ...]
) -> dict[str, tuple[str, ...]]:
    group_ids = {
        str(row[0])
        for row in map_db.execute(
            "SELECT fid FROM lane_groups_polygons WHERE fid IN ({})".format(
                ",".join("?" for _ in route)
            ),
            route,
        )
    }
    successors: dict[str, tuple[str, ...]] = {}
    for source, target in zip(route, route[1:]):
        if source in group_ids:
            linked = map_db.execute(
                """
                SELECT 1 FROM lane_group_connectors
                WHERE fid = ? AND from_lane_group_fid = ?
                """,
                (target, source),
            ).fetchone()
        else:
            linked = map_db.execute(
                """
                SELECT 1 FROM lane_group_connectors
                WHERE fid = ? AND to_lane_group_fid = ?
                """,
                (source, target),
            ).fetchone()
        if linked is None:
            raise NuPlanCausalSourceError(
                f"mission route is disconnected between {source} and {target}"
            )
        successors[source] = (target,)
    return successors


def _collapse_consecutive_route_roadblocks(
    route: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Normalize only duplicate adjacent source IDs before map-edge lookup."""

    if not route:
        raise NuPlanCausalSourceError("mission route is empty")
    normalized: list[str] = []
    collapsed: list[str] = []
    for roadblock_id in route:
        if normalized and roadblock_id == normalized[-1]:
            collapsed.append(roadblock_id)
            continue
        normalized.append(roadblock_id)
    return tuple(normalized), tuple(collapsed)


def _roadblock_lane_candidates(
    map_db: sqlite3.Connection,
    roadblock_id: str,
    projected_crs: str,
) -> list[dict[str, object]]:
    is_group = map_db.execute(
        "SELECT 1 FROM lane_groups_polygons WHERE fid = ?", (roadblock_id,)
    ).fetchone()
    if is_group:
        rows = map_db.execute(
            """
            SELECT l.lane_fid, b.geom, l.speed_limit_mps,
                   l.left_boundary_fid, l.right_boundary_fid,
                   NULL, NULL, NULL
            FROM lanes_polygons AS l
            JOIN baseline_paths AS b ON b.lane_fid = l.lane_fid
            WHERE l.lane_group_fid = ?
            """,
            (roadblock_id,),
        ).fetchall()
        kind = "lane"
    else:
        rows = map_db.execute(
            """
            SELECT l.fid, b.geom, l.speed_limit_mps,
                   p.left_boundary_fid, p.right_boundary_fid,
                   l.exit_lane_fid, l.entry_lane_fid,
                   l.traffic_light_stop_line_fids
            FROM lane_connectors AS l
            JOIN baseline_paths AS b ON b.lane_connector_fid = l.fid
            JOIN gen_lane_connectors_scaled_width_polygons AS p
              ON p.lane_connector_fid = l.fid
            WHERE l.lane_group_connector_fid = ?
            """,
            (roadblock_id,),
        ).fetchall()
        kind = "connector"
    candidates = []
    rejected: list[tuple[int, tuple[str, ...]]] = []
    for fid, center, speed, left_fid, right_fid, exit_fid, entry_fid, lights in rows:
        missing: list[str] = []
        if left_fid is None or right_fid is None:
            missing.append("boundary_fid")
        if missing:
            rejected.append((int(fid), tuple(missing)))
            continue
        boundaries = map_db.execute(
            "SELECT fid, geom FROM boundaries WHERE fid IN (?, ?)",
            (left_fid, right_fid),
        ).fetchall()
        by_id = {row[0]: row[1] for row in boundaries}
        if left_fid not in by_id or right_fid not in by_id:
            rejected.append((int(fid), ("boundary_geometry",)))
            continue
        has_speed_limit = bool(
            speed is not None and np.isfinite(speed) and float(speed) > 0.0
        )
        candidates.append(
            {
                "kind": kind,
                "fid": int(fid),
                "center": decode_projected_gpkg_geometry(center, projected_crs),
                "left": decode_projected_gpkg_geometry(
                    by_id[left_fid], projected_crs
                ),
                "right": decode_projected_gpkg_geometry(
                    by_id[right_fid], projected_crs
                ),
                "speed_limit_mps": (float(speed) if has_speed_limit else None),
                "exit_lane_fid": (None if exit_fid is None else int(exit_fid)),
                "entry_lane_fid": (None if entry_fid is None else int(entry_fid)),
                "controlled": bool(lights),
                "source_mapping": {
                    "roadblock_id": str(roadblock_id),
                    "lane_fid": int(fid),
                    "kind": kind,
                    "speed_limit_source": (
                        "official_lane_table"
                        if has_speed_limit
                        else "missing_or_invalid_authoritative"
                    ),
                    "speed_limit_available": has_speed_limit,
                    "boundary_source": "official_boundaries_table",
                },
            }
        )
    if not candidates:
        raise NuPlanCausalSourceError(
            f"roadblock {roadblock_id} has no source-complete lanes; rejected={rejected}"
        )
    return candidates


def _connected_lane_path(
    slots: list[list[dict[str, object]]], ego_xy: np.ndarray
) -> list[dict[str, object]]:
    from shapely import Point

    if not slots:
        raise NuPlanCausalSourceError("route window has no lane slots")
    ego = Point(float(ego_xy[0]), float(ego_xy[1]))
    states = {
        index: (float(candidate["center"].distance(ego)), [index])
        for index, candidate in enumerate(slots[0])
    }
    for slot_index in range(1, len(slots)):
        next_states = {}
        for next_index, next_candidate in enumerate(slots[slot_index]):
            best = None
            for previous_index, (cost, path) in states.items():
                previous = slots[slot_index - 1][previous_index]
                if not _lanes_are_connected(previous, next_candidate):
                    continue
                previous_end = np.asarray(previous["center"].coords[-1])
                next_start = np.asarray(next_candidate["center"].coords[0])
                candidate = (cost + float(np.linalg.norm(next_start - previous_end)), path + [next_index])
                if best is None or candidate[0] < best[0]:
                    best = candidate
            if best is not None:
                next_states[next_index] = best
        if not next_states:
            raise NuPlanCausalSourceError(
                f"no connected lane path reaches route slot {slot_index}"
            )
        states = next_states
    _, path = min(states.values(), key=lambda value: value[0])
    return [slots[index][candidate_index] for index, candidate_index in enumerate(path)]


def _lanes_are_connected(
    previous: Mapping[str, object], following: Mapping[str, object]
) -> bool:
    if previous["kind"] == "lane":
        return previous["fid"] == following["exit_lane_fid"]
    return previous["entry_lane_fid"] == following["fid"]


def derive_source_dt_s(timestamps_us: Sequence[int]) -> float:
    timestamps = np.asarray(timestamps_us, dtype=np.int64).reshape(-1)
    if timestamps.size < 2:
        raise NuPlanCausalSourceError("at least two timestamps are required")
    deltas = np.diff(timestamps)
    if np.any(deltas <= 0):
        raise NuPlanCausalSourceError("timestamps must be strictly increasing")
    median = float(np.median(deltas))
    if np.max(np.abs(deltas - median)) > 0.1 * median:
        raise NuPlanCausalSourceError("timestamps are too irregular for one source dt")
    return median / 1_000_000.0


def causal_history(
    states: np.ndarray,
    timestamps_us: Sequence[int],
    decision_timestamp_us: int,
) -> np.ndarray:
    values = np.asarray(states)
    timestamps = np.asarray(timestamps_us, dtype=np.int64).reshape(-1)
    if values.ndim < 1 or values.shape[0] != timestamps.size:
        raise NuPlanCausalSourceError("states and timestamps must have equal length")
    if timestamps.size == 0 or np.any(np.diff(timestamps) <= 0):
        raise NuPlanCausalSourceError("timestamps must be nonempty and strictly increasing")
    matches = np.flatnonzero(timestamps == int(decision_timestamp_us))
    if matches.size != 1:
        raise NuPlanCausalSourceError("history must contain the exact decision tick")
    return values[: int(matches[0]) + 1].copy()


def select_mission_route_window(
    route_roadblock_ids: Sequence[str],
    current_roadblock_id: str,
    successors: Mapping[str, Sequence[str]],
    *,
    limit: int = 25,
) -> tuple[str, ...]:
    route = tuple(str(value) for value in route_roadblock_ids)
    if not route or len(set(route)) != len(route):
        raise NuPlanCausalSourceError("mission route must be nonempty and unique")
    if limit <= 0:
        raise NuPlanCausalSourceError("route window limit must be positive")
    try:
        start = route.index(str(current_roadblock_id))
    except ValueError as exc:
        raise NuPlanCausalSourceError(
            "current roadblock is absent from the mission route"
        ) from exc
    window = route[start : start + limit]
    for source, target in zip(window, window[1:]):
        if target not in tuple(str(value) for value in successors.get(source, ())):
            raise NuPlanCausalSourceError(
                f"mission route is disconnected between {source} and {target}"
            )
    return window


def encode_route_lane(
    *,
    centerline: np.ndarray,
    left_boundary: np.ndarray,
    right_boundary: np.ndarray,
    speed_limit_mps: float | None,
    traffic_light_status: str | None = None,
    traffic_timestamp_us: int | None = None,
    decision_timestamp_us: int | None = None,
    require_speed_limit: bool = True,
) -> EncodedRouteLane:
    speed_limit = None
    if speed_limit_mps is not None and np.isfinite(speed_limit_mps):
        speed_limit = float(speed_limit_mps)
        if speed_limit <= 0.0:
            speed_limit = None
    if require_speed_limit and speed_limit is None:
        if speed_limit_mps is None or not np.isfinite(speed_limit_mps):
            raise NuPlanCausalSourceError("route speed_limit_mps is required")
        raise NuPlanCausalSourceError("route speed_limit_mps must be positive")

    center = _resample_polyline(centerline)
    left = _aligned_boundary(left_boundary, center[0])
    right = _aligned_boundary(right_boundary, center[0])
    direction = np.empty_like(center)
    direction[:-1] = center[1:] - center[:-1]
    direction[-1] = direction[-2]
    direction_norm = np.linalg.norm(direction, axis=1)
    if np.any(direction_norm < 1e-6):
        raise NuPlanCausalSourceError("centerline contains a zero-length direction")

    left_offset = left - center
    right_offset = right - center
    left_cross = (
        direction[:, 0] * left_offset[:, 1]
        - direction[:, 1] * left_offset[:, 0]
    )
    right_cross = (
        direction[:, 0] * right_offset[:, 1]
        - direction[:, 1] * right_offset[:, 0]
    )
    if np.any(left_cross <= 0.0) or np.any(right_cross >= 0.0):
        raise NuPlanCausalSourceError(
            "left/right boundary semantics do not match centerline direction"
        )

    traffic = _traffic_light_encoding(
        traffic_light_status,
        traffic_timestamp_us=traffic_timestamp_us,
        decision_timestamp_us=decision_timestamp_us,
    )
    tensor = np.zeros((20, 33), dtype=np.float64)
    tensor[:, :2] = center
    tensor[:, 2:4] = direction
    tensor[:, 4:6] = left_offset
    tensor[:, 6:8] = right_offset
    tensor[:, 8:13] = traffic
    tensor[:, 13] = 1.0
    tensor[:, 23] = 1.0
    return EncodedRouteLane(tensor=tensor, speed_limit_mps=speed_limit)


def _resample_polyline(points: np.ndarray) -> np.ndarray:
    values = np.asarray(points, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 2 or values.shape[0] < 2:
        raise NuPlanCausalSourceError("polyline must have shape (N, 2), N >= 2")
    if not np.isfinite(values).all():
        raise NuPlanCausalSourceError("polyline must be finite")
    try:
        from shapely import LineString
    except ImportError as exc:
        raise NuPlanCausalSourceError(
            "Shapely>=2.0 is required; install camp_core[nuplan]"
        ) from exc
    line = LineString(values)
    if not line.is_valid or line.length <= 0.0:
        raise NuPlanCausalSourceError("polyline must have positive valid length")
    return np.asarray(
        [
            line.interpolate(distance).coords[0]
            for distance in np.linspace(0, line.length, 20)
        ],
        dtype=np.float64,
    )


def _aligned_boundary(points: np.ndarray, center_start: np.ndarray) -> np.ndarray:
    boundary = _resample_polyline(points)
    if np.linalg.norm(boundary[-1] - center_start) < np.linalg.norm(
        boundary[0] - center_start
    ):
        boundary = boundary[::-1].copy()
    return boundary


def _traffic_light_encoding(
    status: str | None,
    *,
    traffic_timestamp_us: int | None,
    decision_timestamp_us: int | None,
) -> np.ndarray:
    encoding = np.zeros(5, dtype=np.float32)
    if status is None:
        encoding[4] = 1.0
        return encoding
    if traffic_timestamp_us is None or decision_timestamp_us is None:
        raise NuPlanCausalSourceError(
            "traffic-light status requires both traffic and decision timestamps"
        )
    if int(traffic_timestamp_us) != int(decision_timestamp_us):
        raise NuPlanCausalSourceError(
            "traffic-light status must come from the same lidar tick"
        )
    indices = {"green": 0, "yellow": 1, "red": 2, "unknown": 3}
    try:
        encoding[indices[str(status).lower()]] = 1.0
    except KeyError as exc:
        raise NuPlanCausalSourceError(
            f"unsupported traffic-light status: {status}"
        ) from exc
    return encoding
