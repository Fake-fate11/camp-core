from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import sqlite3
import struct
from typing import Mapping, Sequence

import numpy as np


class NuPlanCausalSourceError(ValueError):
    """Raised when nuPlan source data cannot satisfy the causal DP contract."""


@dataclass(frozen=True)
class EncodedRouteLane:
    tensor: np.ndarray
    speed_limit_mps: float


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
        route = tuple(str(value) for value in str(scene[1]).split())
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
            [goal[0], goal[1], _quaternion_yaw(*goal[2:])], dtype=np.float32
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

        route_lanes = np.zeros((25, 20, 33), dtype=np.float32)
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
            )
            route_lanes[index] = encoded.tensor
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
        )
    finally:
        db.close()
        map_db.close()


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
    for fid, center, speed, left_fid, right_fid, exit_fid, entry_fid, lights in rows:
        boundaries = map_db.execute(
            "SELECT fid, geom FROM boundaries WHERE fid IN (?, ?)",
            (left_fid, right_fid),
        ).fetchall()
        by_id = {row[0]: row[1] for row in boundaries}
        if speed is None or left_fid not in by_id or right_fid not in by_id:
            raise NuPlanCausalSourceError(
                f"roadblock {roadblock_id} lane {fid} lacks speed or boundaries"
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
                "speed_limit_mps": float(speed),
                "exit_lane_fid": (None if exit_fid is None else int(exit_fid)),
                "entry_lane_fid": (None if entry_fid is None else int(entry_fid)),
                "controlled": bool(lights),
            }
        )
    if not candidates:
        raise NuPlanCausalSourceError(f"roadblock {roadblock_id} has no lanes")
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
) -> EncodedRouteLane:
    if speed_limit_mps is None or not np.isfinite(speed_limit_mps):
        raise NuPlanCausalSourceError("route speed_limit_mps is required")
    speed_limit = float(speed_limit_mps)
    if speed_limit <= 0.0:
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
    tensor = np.zeros((20, 33), dtype=np.float32)
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
