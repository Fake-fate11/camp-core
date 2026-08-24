"""Neutral same-tick source geometry for the V26 academic atom bank.

This module only validates and projects source tensors.  It does not decide
candidate feasibility, eligibility, selection, or fallback behavior.
"""

from __future__ import annotations

import numpy as np


FULL_WINDOW_EXACT_SPEED = "full_window_exact_speed"
CANDIDATE_LOCAL_EXACT_SPEED = "candidate_local_exact_speed"
_SPEED_SOURCE_POLICIES = frozenset(
    {FULL_WINDOW_EXACT_SPEED, CANDIDATE_LOCAL_EXACT_SPEED}
)


def project_candidates_to_route(
    candidates: np.ndarray,
    route_lanes: np.ndarray,
    route_speed_limits: np.ndarray,
    route_has_speed_limits: np.ndarray,
    *,
    speed_source_policy: str = FULL_WINDOW_EXACT_SPEED,
) -> dict[str, np.ndarray]:
    """Project finite trajectories onto the supplied same-tick route geometry."""

    if speed_source_policy not in _SPEED_SOURCE_POLICIES:
        raise ValueError("unsupported route speed-source policy")
    trajectories = np.asarray(candidates, dtype=np.float64)
    route = np.asarray(route_lanes, dtype=np.float64)
    limits = np.asarray(route_speed_limits, dtype=np.float64).reshape(-1)
    has_limits = np.asarray(route_has_speed_limits, dtype=bool).reshape(-1)
    if (
        trajectories.ndim != 3
        or trajectories.shape[0] < 1
        or trajectories.shape[1:] != (80, 4)
        or not np.isfinite(trajectories).all()
    ):
        raise ValueError("candidates must be finite with shape [K,80,4]")
    if route.shape != (25, 20, 33) or not np.isfinite(route).all():
        raise ValueError("route_lanes must be finite with shape [25,20,33]")
    if limits.shape != (25,) or has_limits.shape != (25,):
        raise ValueError("route speed-limit fields must have shape [25,1]")

    points: list[np.ndarray] = []
    left_offsets: list[np.ndarray] = []
    right_offsets: list[np.ndarray] = []
    speeds: list[np.ndarray] = []
    for slot in range(route.shape[0]):
        valid = np.any(np.abs(route[slot, :, :8]) > 1e-8, axis=1)
        if not valid.any():
            continue
        speed_available = bool(
            has_limits[slot]
            and np.isfinite(limits[slot])
            and limits[slot] > 0
        )
        if speed_source_policy == FULL_WINDOW_EXACT_SPEED and not speed_available:
            raise ValueError(f"route slot {slot} requires a positive speed limit")
        rows = route[slot, valid]
        if rows.shape[0] < 2:
            raise ValueError(f"route slot {slot} requires at least two valid points")
        points.append(rows[:, :2])
        left_offsets.append(rows[:, 4:6])
        right_offsets.append(rows[:, 6:8])
        speeds.append(
            np.full(
                rows.shape[0],
                limits[slot] if speed_available else np.nan,
                dtype=np.float64,
            )
        )
    if not points:
        raise ValueError("route has no valid points")

    centers = np.concatenate(points)
    left = np.concatenate(left_offsets)
    right = np.concatenate(right_offsets)
    point_speeds = np.concatenate(speeds)
    deltas = np.diff(centers, axis=0)
    lengths = np.linalg.norm(deltas, axis=1)
    valid_segments = lengths > 1e-6
    if not valid_segments.any():
        raise ValueError("route has no nonzero segment")
    starts = centers[:-1][valid_segments]
    directions = deltas[valid_segments] / lengths[valid_segments, None]
    segment_lengths = lengths[valid_segments]
    left_start = left[:-1][valid_segments]
    left_end = left[1:][valid_segments]
    right_start = right[:-1][valid_segments]
    right_end = right[1:][valid_segments]
    speed_start = point_speeds[:-1][valid_segments]
    speed_end = point_speeds[1:][valid_segments]
    arc_starts = np.concatenate([[0.0], np.cumsum(segment_lengths[:-1])])

    shape = trajectories.shape[:2]
    lateral = np.empty(shape, dtype=np.float64)
    left_width = np.empty(shape, dtype=np.float64)
    right_width = np.empty(shape, dtype=np.float64)
    speed_limit = np.empty(shape, dtype=np.float64)
    projected_arc = np.empty(shape, dtype=np.float64)
    for candidate_index, trajectory in enumerate(trajectories):
        for step, point in enumerate(trajectory[:, :2]):
            relative = point - starts
            along = np.clip(
                np.einsum("ij,ij->i", relative, directions),
                0.0,
                segment_lengths,
            )
            projections = starts + directions * along[:, None]
            segment = int(np.argmin(np.linalg.norm(point - projections, axis=1)))
            fraction = along[segment] / segment_lengths[segment]
            normal = np.array(
                [-directions[segment, 1], directions[segment, 0]],
                dtype=np.float64,
            )
            left_offset = left_start[segment] + fraction * (
                left_end[segment] - left_start[segment]
            )
            right_offset = right_start[segment] + fraction * (
                right_end[segment] - right_start[segment]
            )
            lateral[candidate_index, step] = np.dot(
                point - projections[segment], normal
            )
            left_width[candidate_index, step] = np.dot(left_offset, normal)
            right_width[candidate_index, step] = -np.dot(right_offset, normal)
            speed_limit[candidate_index, step] = speed_start[segment] + fraction * (
                speed_end[segment] - speed_start[segment]
            )
            projected_arc[candidate_index, step] = arc_starts[segment] + along[segment]
    if np.any(left_width <= 0.0) or np.any(right_width <= 0.0):
        raise ValueError("projected route boundaries must be positive")
    route_speed_source_eligible = np.isfinite(speed_limit).all(axis=1) & (
        speed_limit > 0.0
    ).all(axis=1)
    if speed_source_policy == FULL_WINDOW_EXACT_SPEED and not (
        route_speed_source_eligible.all()
    ):
        raise ValueError("projected speed limits must be positive")
    route_progress = np.maximum.accumulate(projected_arc, axis=1)[:, -1]
    return {
        "lateral_offset": lateral,
        "left_width": left_width,
        "right_width": right_width,
        "speed_limit": speed_limit,
        "projected_arc": projected_arc,
        "route_progress": route_progress,
        "route_speed_source_eligible_mask": route_speed_source_eligible,
    }


def build_observable_obbs(
    neighbor_predictions: np.ndarray,
    neighbor_valid_mask: np.ndarray,
    neighbor_history: np.ndarray,
    static_objects: np.ndarray,
    *,
    include_static_objects: bool = True,
) -> np.ndarray:
    """Build candidate-associated actor OBB tensors from decision-time sources."""

    predictions = np.asarray(neighbor_predictions, dtype=np.float64)
    valid = np.asarray(neighbor_valid_mask, dtype=bool).reshape(-1)
    history = np.asarray(neighbor_history, dtype=np.float64)
    static = np.asarray(static_objects, dtype=np.float64)
    if predictions.ndim != 4 or predictions.shape[0] < 1 or predictions.shape[1:] != (32, 80, 4) or not np.isfinite(predictions).all():
        raise ValueError("neighbor predictions must be finite [K,32,80,4]")
    if valid.shape != (32,):
        raise ValueError("neighbor_valid_mask must have shape [32]")
    if history.shape != (32, 31, 11) or not np.isfinite(history).all():
        raise ValueError("neighbor history must be finite [32,31,11]")
    if static.shape != (5, 10) or not np.isfinite(static).all():
        raise ValueError("static objects must be finite [5,10]")
    if not isinstance(include_static_objects, bool):
        raise ValueError("include_static_objects must be bool")

    obstacle_count = 37 if include_static_objects else 32
    candidate_count = int(predictions.shape[0])
    obstacles = np.zeros((candidate_count, obstacle_count, 80, 5), dtype=np.float64)
    for slot in np.flatnonzero(valid):
        width, length = history[slot, -1, 6:8]
        if width <= 0.0 or length <= 0.0:
            raise ValueError(f"neighbor slot {slot} requires positive width/length")
        headings = predictions[:, slot, :, 2:4]
        if np.any(np.linalg.norm(headings, axis=2) < 1e-6):
            raise ValueError(f"neighbor slot {slot} has invalid heading")
        obstacles[:, slot, :, :2] = predictions[:, slot, :, :2]
        obstacles[:, slot, :, 2] = np.arctan2(
            headings[:, :, 1], headings[:, :, 0]
        )
        obstacles[:, slot, :, 3] = length
        obstacles[:, slot, :, 4] = width

    if include_static_objects:
        for static_slot, row in enumerate(static):
            if not np.any(np.abs(row[:6]) > 1e-8):
                continue
            heading_norm = float(np.linalg.norm(row[2:4]))
            width, length = row[4:6]
            if heading_norm < 0.5 or width <= 0.0 or length <= 0.0:
                raise ValueError(
                    f"static slot {static_slot} requires valid heading and dimensions"
                )
            obstacle = np.array(
                [row[0], row[1], np.arctan2(row[3], row[2]), length, width],
                dtype=np.float64,
            )
            obstacles[:, 32 + static_slot, :, :] = obstacle
    return obstacles


def tracked_constant_velocity_neighbor_predictions(
    neighbor_history: np.ndarray,
    *,
    candidate_count: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Extrapolate one decision-time tracked-actor source for every trajectory.

    The returned prediction is deliberately candidate independent.  It uses
    only the current tracked position, velocity, and heading already present in
    ``neighbor_agents_past`` and is broadcast to the human demonstration and
    every fixed DP candidate.
    """

    history = np.asarray(neighbor_history, dtype=np.float64)
    if history.shape != (32, 31, 11) or not np.isfinite(history).all():
        raise ValueError("neighbor history must be finite [32,31,11]")
    if isinstance(candidate_count, bool) or int(candidate_count) < 1:
        raise ValueError("candidate_count must be a positive integer")
    valid = np.any(np.abs(history) > 1e-8, axis=(1, 2))
    current = history[:, -1]
    if np.any(np.linalg.norm(current[valid, 2:4], axis=1) < 1e-6):
        raise ValueError("tracked actor current heading is invalid")
    times = 0.1 * np.arange(1, 81, dtype=np.float64)
    one = np.zeros((32, 80, 4), dtype=np.float64)
    one[:, :, 0] = current[:, 0, None] + current[:, 4, None] * times[None, :]
    one[:, :, 1] = current[:, 1, None] + current[:, 5, None] * times[None, :]
    one[:, :, 2:4] = current[:, None, 2:4]
    one[~valid] = 0.0
    predictions = np.broadcast_to(
        one[None, :, :, :], (int(candidate_count), 32, 80, 4)
    ).copy()
    return predictions, valid
