from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np


class NuPlanCausalSourceError(ValueError):
    """Raised when nuPlan source data cannot satisfy the causal DP contract."""


@dataclass(frozen=True)
class EncodedRouteLane:
    tensor: np.ndarray
    speed_limit_mps: float


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
