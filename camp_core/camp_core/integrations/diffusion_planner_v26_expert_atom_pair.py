"""Exact V26 atom materialization for training pairs and online candidates.

Passing an expert future builds the human-candidate training pair. Passing
``expert_future_xyh=None`` builds the decision-time candidate-only atom bank
used by the Diffusion Planner CAMP selector.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from camp_core.integrations.diffusion_planner import (
    _obb_corners,
)
from camp_core.integrations.diffusion_planner_v26_atom_sources import (
    CANDIDATE_LOCAL_EXACT_SPEED,
    build_observable_obbs,
    project_candidates_to_route,
)
from camp_core.integrations.nuplan_causal_adapter import NuPlanCausalSourceError
from camp_core.integrations.diffusion_planner_v26_sparse_schema import (
    V26_GLOBAL_ATOM_INDEX,
    V26_GLOBAL_ATOM_NAMES,
)


V26_MINIMAL_PAIR_ATOM_NAMES = (
    "predicted_obb_collision_exposure_fraction",
    "longitudinal_acceleration_energy_s",
    "lateral_acceleration_energy_s",
    "yaw_rate_energy_s",
    "yaw_acceleration_energy_s",
    "longitudinal_jerk_energy_s",
    "jerk_magnitude_energy_s",
)

V26_SAME_TICK_ATOM_BANK_NAMES = V26_GLOBAL_ATOM_NAMES

_T = 80
_DT_SECONDS = 0.1
_TTC_THRESHOLD_SECONDS = 0.95
_TTC_PROJECTION_HORIZON_SECONDS = 3.0
_TTC_STOPPED_SPEED_MPS = 5e-3
_RED_STOPPING_DECELERATION_MPS2 = 4.05
_COMFORT_THRESHOLDS = {
    "longitudinal_acceleration_positive": 2.40,
    "longitudinal_acceleration_negative": 4.05,
    "lateral_acceleration": 4.89,
    "yaw_rate": 0.95,
    "yaw_acceleration": 1.93,
    "longitudinal_jerk": 4.13,
    "jerk_magnitude": 8.37,
}


def load_nuplan_expert_ego_future(*args, **kwargs):
    from camp_core.integrations.nuplan_causal_adapter import (
        load_nuplan_expert_ego_future as loader,
    )

    return loader(*args, **kwargs)


def load_nuplan_same_tick_route_atom_context(*args, **kwargs):
    from camp_core.integrations.nuplan_causal_adapter import (
        load_nuplan_same_tick_route_atom_context as loader,
    )

    return loader(*args, **kwargs)


def load_nuplan_same_tick_drivable_area(*args, **kwargs):
    from camp_core.integrations.nuplan_causal_adapter import (
        load_nuplan_same_tick_drivable_area as loader,
    )

    return loader(*args, **kwargs)


def _validate_identity(identity: Mapping[str, Any]) -> dict[str, str | int | float | bool]:
    if not identity:
        raise ValueError("identity must be non-empty")
    result: dict[str, str | int | float | bool] = {}
    for key, value in identity.items():
        if not isinstance(key, str) or not isinstance(value, (str, int, float, bool)):
            raise ValueError("identity must contain only scalar JSON fields")
        result[key] = value
    return result


def _validate_scenario_reference(
    scenario_reference: Mapping[str, Any] | None,
) -> dict[str, str | int | float | bool] | None:
    if scenario_reference is None:
        return None
    result: dict[str, str | int | float | bool] = {}
    for key, value in scenario_reference.items():
        if not isinstance(key, str) or not isinstance(value, (str, int, float, bool)):
            raise ValueError("scenario_reference must contain only scalar JSON fields")
        result[key] = value
    return result


def _trajectory_xyh_from_candidate_tensor(candidates: np.ndarray) -> np.ndarray:
    candidates = np.asarray(candidates, dtype=np.float64)
    if candidates.ndim != 3 or candidates.shape[0] < 1 or candidates.shape[1:] != (_T, 4):
        raise ValueError(f"candidates must have shape [K,{_T},4] with K positive")
    if not np.isfinite(candidates).all():
        raise ValueError("candidates must be finite")
    heading_norm = np.linalg.norm(candidates[:, :, 2:4], axis=-1)
    if np.any(heading_norm < 1e-6):
        raise ValueError("candidate heading cos/sin direction must be nonzero")
    heading = np.unwrap(np.arctan2(candidates[:, :, 3], candidates[:, :, 2]), axis=1)
    return np.concatenate((candidates[:, :, :2], heading[:, :, None]), axis=-1)


def _validate_expert_future(expert_future_xyh: np.ndarray) -> np.ndarray:
    expert = np.asarray(expert_future_xyh, dtype=np.float64)
    if expert.shape != (_T, 3):
        raise ValueError(f"expert_future_xyh must have shape ({_T}, 3)")
    if not np.isfinite(expert).all():
        raise ValueError("expert_future_xyh must be finite")
    result = expert.copy()
    result[:, 2] = np.unwrap(result[:, 2])
    return result


def _obb_corners_batch(
    xy: np.ndarray,
    headings: np.ndarray,
    lengths: np.ndarray,
    widths: np.ndarray,
    wheelbases: np.ndarray | float | None = None,
) -> np.ndarray:
    """Vectorized equivalent of ``_obb_corners`` for matching array shapes."""

    xy_values = np.asarray(xy, dtype=np.float64)
    heading_values = np.asarray(headings, dtype=np.float64)
    length_values = np.asarray(lengths, dtype=np.float64)
    width_values = np.asarray(widths, dtype=np.float64)
    shape = heading_values.shape
    if xy_values.shape != shape + (2,):
        raise ValueError("xy and headings must have matching shapes")
    if length_values.shape != shape or width_values.shape != shape:
        raise ValueError("lengths and widths must match headings")
    if wheelbases is None:
        offsets = np.zeros(shape, dtype=np.float64)
    else:
        wheelbase_values = np.broadcast_to(
            np.asarray(wheelbases, dtype=np.float64), shape
        )
        offsets = np.where(
            np.isfinite(wheelbase_values) & (wheelbase_values > 0.0),
            wheelbase_values / 2.0,
            0.0,
        )

    directions = np.stack(
        (np.cos(heading_values), np.sin(heading_values)), axis=-1
    )
    lateral = np.stack((-directions[..., 1], directions[..., 0]), axis=-1)
    centers = xy_values + offsets[..., None] * directions
    longitudinal = 0.5 * length_values[..., None] * directions
    lateral_offset = 0.5 * width_values[..., None] * lateral
    return np.stack(
        (
            centers - longitudinal - lateral_offset,
            centers + longitudinal - lateral_offset,
            centers + longitudinal + lateral_offset,
            centers - longitudinal + lateral_offset,
        ),
        axis=-2,
    )


def _obb_collides_batch(corners_a: np.ndarray, corners_b: np.ndarray) -> np.ndarray:
    """Batch the same separating-axis test used by ``_obb_distance``."""

    first = np.asarray(corners_a, dtype=np.float64)
    second = np.asarray(corners_b, dtype=np.float64)
    if first.shape != second.shape or first.ndim != 3 or first.shape[1:] != (4, 2):
        raise ValueError("OBB corner batches must share shape [N,4,2]")
    if first.shape[0] == 0:
        return np.zeros(0, dtype=bool)
    edges = np.concatenate(
        (
            np.roll(first, -1, axis=1) - first,
            np.roll(second, -1, axis=1) - second,
        ),
        axis=1,
    )
    axes = np.stack((-edges[..., 1], edges[..., 0]), axis=-1)
    axes /= np.linalg.norm(axes, axis=-1, keepdims=True)
    first_projection = np.einsum("nci,nai->nca", first, axes)
    second_projection = np.einsum("nci,nai->nca", second, axes)
    separated = (
        (first_projection.max(axis=1) < second_projection.min(axis=1))
        | (second_projection.max(axis=1) < first_projection.min(axis=1))
    )
    return ~np.any(separated, axis=1)


def _point_segment_distances_batch(
    points: np.ndarray, segments: np.ndarray
) -> np.ndarray:
    starts = segments
    vectors = np.roll(segments, -1, axis=1) - segments
    offsets = points[:, :, None, :] - starts[:, None, :, :]
    denominator = np.sum(vectors * vectors, axis=-1)
    projection = np.sum(offsets * vectors[:, None, :, :], axis=-1)
    projection = np.divide(
        projection,
        denominator[:, None, :],
        out=np.zeros_like(projection),
        where=denominator[:, None, :] > 1e-12,
    )
    projection = np.clip(projection, 0.0, 1.0)
    closest = starts[:, None, :, :] + projection[..., None] * vectors[:, None, :, :]
    return np.linalg.norm(points[:, :, None, :] - closest, axis=-1)


def _obb_distance_batch(corners_a: np.ndarray, corners_b: np.ndarray) -> np.ndarray:
    """Vectorized equivalent of scalar ``_obb_distance``."""

    first = np.asarray(corners_a, dtype=np.float64)
    second = np.asarray(corners_b, dtype=np.float64)
    collided = _obb_collides_batch(first, second)
    result = np.zeros(first.shape[0], dtype=np.float64)
    separated = ~collided
    if np.any(separated):
        first_values = first[separated]
        second_values = second[separated]
        first_to_second = _point_segment_distances_batch(
            first_values, second_values
        )
        second_to_first = _point_segment_distances_batch(
            second_values, first_values
        )
        result[separated] = np.minimum(
            first_to_second.min(axis=(1, 2)),
            second_to_first.min(axis=(1, 2)),
        )
    return result


def _ego_centers(
    trajectories_xyh: np.ndarray, wheelbase: float
) -> np.ndarray:
    directions = np.stack(
        (
            np.cos(trajectories_xyh[..., 2]),
            np.sin(trajectories_xyh[..., 2]),
        ),
        axis=-1,
    )
    return trajectories_xyh[..., :2] + 0.5 * wheelbase * directions


def _collision_exposure(
    trajectories_xyh: np.ndarray,
    obstacle_obbs: np.ndarray,
    ego_shape: np.ndarray,
) -> np.ndarray:
    obstacles = np.asarray(obstacle_obbs, dtype=np.float64)
    candidate_count = int(trajectories_xyh.shape[0])
    if obstacles.ndim != 4 or obstacles.shape[0] != candidate_count or obstacles.shape[2:] != (_T, 5):
        raise ValueError("obstacle_obbs must have shape [K,N,80,5]")
    if not np.isfinite(obstacles).all():
        raise ValueError("obstacle_obbs must be finite")

    shape = np.asarray(ego_shape, dtype=np.float64)
    if shape.shape != (3,) or not np.isfinite(shape).all() or np.any(shape <= 0.0):
        raise ValueError("ego_shape must be finite positive [wheelbase, length, width]")
    wheelbase, length, width = (float(value) for value in shape)

    if obstacles.shape[1] == 0:
        return np.zeros(candidate_count, dtype=np.float64)

    ego_centers = _ego_centers(trajectories_xyh, wheelbase)
    ego_radius = float(np.hypot(length / 2.0, width / 2.0))
    actor_radii = np.hypot(obstacles[..., 3] / 2.0, obstacles[..., 4] / 2.0)
    center_distances = np.linalg.norm(
        obstacles[..., :2] - ego_centers[:, None, :, :], axis=-1
    )
    possible = (
        (obstacles[..., 3] > 0.0)
        & (obstacles[..., 4] > 0.0)
        & (center_distances <= ego_radius + actor_radii)
    )
    pair_indices, actor_indices, time_indices = np.nonzero(possible)
    if pair_indices.size == 0:
        return np.zeros(candidate_count, dtype=np.float64)

    ego_poses = trajectories_xyh[pair_indices, time_indices]
    actor_poses = obstacles[pair_indices, actor_indices, time_indices]
    ego_corners = _obb_corners_batch(
        ego_poses[:, :2],
        ego_poses[:, 2],
        np.full(pair_indices.size, length),
        np.full(pair_indices.size, width),
        wheelbase,
    )
    actor_corners = _obb_corners_batch(
        actor_poses[:, :2], actor_poses[:, 2], actor_poses[:, 3], actor_poses[:, 4]
    )
    contacts = _obb_distance_batch(ego_corners, actor_corners) <= 1e-12
    contact_frames = np.zeros((candidate_count, _T), dtype=bool)
    contact_frames[pair_indices[contacts], time_indices[contacts]] = True
    return np.mean(contact_frames, axis=1)


def _trajectory_velocity(trajectories_xyh: np.ndarray, dt_seconds: float) -> np.ndarray:
    trajectories = np.asarray(trajectories_xyh, dtype=np.float64)
    if trajectories.ndim != 3 or trajectories.shape[0] < 1 or trajectories.shape[1:] != (_T, 3) or not np.isfinite(trajectories).all():
        raise ValueError("trajectories must be finite [K,80,3]")
    velocity = np.empty((trajectories.shape[0], _T, 2), dtype=np.float64)
    velocity[:, :-1] = np.diff(trajectories[:, :, :2], axis=1) / dt_seconds
    velocity[:, -1] = velocity[:, -2]
    return velocity


def _dynamic_obb_velocity(dynamic_obbs: np.ndarray, dt_seconds: float) -> np.ndarray:
    obstacles = np.asarray(dynamic_obbs, dtype=np.float64)
    if obstacles.ndim != 4 or obstacles.shape[0] < 1 or obstacles.shape[2:] != (_T, 5):
        raise ValueError("dynamic_obbs must have shape [K,N,80,5]")
    if not np.isfinite(obstacles).all():
        raise ValueError("dynamic_obbs must be finite")
    velocity = np.empty(obstacles.shape[:3] + (2,), dtype=np.float64)
    velocity[:, :, :-1] = np.diff(obstacles[:, :, :, :2], axis=2) / dt_seconds
    velocity[:, :, -1] = velocity[:, :, -2]
    return velocity


def _ttc_lateral_relevance_mask(
    trajectories_xyh: np.ndarray,
    ego_shape: np.ndarray,
    route_atom_context: Mapping[str, Any],
) -> np.ndarray:
    try:
        from shapely import STRtree, points, polygons
    except ImportError as exc:  # pragma: no cover - dependency smoke
        raise ValueError("TTC lane/intersection relevance requires Shapely") from exc
    route_objects = route_atom_context.get("route_objects")
    if not isinstance(route_objects, (tuple, list)) or not route_objects:
        raise ValueError("TTC relevance requires source-complete route objects")
    shape = np.asarray(ego_shape, dtype=np.float64)
    wheelbase, length, width = (float(value) for value in shape)
    candidate_count = int(trajectories_xyh.shape[0])
    flat_count = candidate_count * _T
    trajectories = np.asarray(trajectories_xyh, dtype=np.float64)
    footprints = polygons(
        _obb_corners_batch(
            trajectories[..., :2].reshape(flat_count, 2),
            trajectories[..., 2].reshape(flat_count),
            np.full(flat_count, length),
            np.full(flat_count, width),
            wheelbase,
        )
    )
    route_geometries = [item["geometry"] for item in route_objects]
    covered_pairs = STRtree(route_geometries).query(
        footprints, predicate="covered_by"
    )
    fully_in_one_route_object = np.zeros(flat_count, dtype=bool)
    fully_in_one_route_object[covered_pairs[0]] = True

    connector_geometries = [
        item["geometry"] for item in route_objects if item["kind"] == "connector"
    ]
    in_intersection = np.zeros(flat_count, dtype=bool)
    if connector_geometries:
        center_points = points(trajectories[..., :2].reshape(flat_count, 2))
        connector_pairs = STRtree(connector_geometries).query(
            center_points, predicate="covered_by"
        )
        in_intersection[connector_pairs[0]] = True
    return (~fully_in_one_route_object | in_intersection).reshape(
        candidate_count, _T
    )


def _nuplan_semantic_ttc_deficit(
    trajectories_xyh: np.ndarray,
    dynamic_obbs: np.ndarray,
    ego_shape: np.ndarray,
    lateral_relevance_mask: np.ndarray,
    dt_seconds: float,
    actor_velocity_override: np.ndarray | None = None,
) -> np.ndarray:
    """Continuous deficit built from nuPlan's TTC projection/relevance semantics."""

    trajectories = np.asarray(trajectories_xyh, dtype=np.float64)
    obstacles = np.asarray(dynamic_obbs, dtype=np.float64)
    lateral = np.asarray(lateral_relevance_mask, dtype=bool)
    candidate_count = int(trajectories.shape[0])
    if obstacles.shape[0] != candidate_count or lateral.shape != (candidate_count, _T):
        raise ValueError("dynamic and lateral relevance inputs must share [K,80]")
    ego_velocity = _trajectory_velocity(trajectories, dt_seconds)
    actor_velocity = (
        _dynamic_obb_velocity(obstacles, dt_seconds)
        if actor_velocity_override is None
        else np.asarray(actor_velocity_override, dtype=np.float64)
    )
    if actor_velocity.shape != obstacles.shape[:3] + (2,) or not np.isfinite(actor_velocity).all():
        raise ValueError("actor velocity override must be finite [K,N,80,2]")
    wheelbase, ego_length, ego_width = (
        float(value) for value in np.asarray(ego_shape, dtype=np.float64)
    )
    projection_times = np.arange(
        dt_seconds, _TTC_PROJECTION_HORIZON_SECONDS, dt_seconds
    )
    actor_count = int(obstacles.shape[1])
    if actor_count == 0:
        return np.zeros(candidate_count, dtype=np.float64)

    ego_speed = np.linalg.norm(ego_velocity, axis=-1)
    ego_direction = np.stack(
        (np.cos(trajectories[..., 2]), np.sin(trajectories[..., 2])), axis=-1
    )
    ego_motion = ego_direction * ego_speed[..., None]
    ego_center = _ego_centers(trajectories, wheelbase)
    actor_center = obstacles[..., :2]
    actor_speed = np.linalg.norm(actor_velocity, axis=-1)
    actor_direction = np.stack(
        (np.cos(obstacles[..., 2]), np.sin(obstacles[..., 2])), axis=-1
    )
    actor_motion = actor_direction * actor_speed[..., None]

    relative = actor_center - ego_center[:, None, :, :]
    center_distance = np.linalg.norm(relative, axis=-1)
    relative_unit = np.divide(
        relative,
        center_distance[..., None],
        out=np.zeros_like(relative),
        where=center_distance[..., None] > 1e-12,
    )
    cosine = np.sum(ego_direction[:, None, :, :] * relative_unit, axis=-1)
    cosine = np.where(center_distance <= 1e-12, 1.0, np.clip(cosine, -1.0, 1.0))
    relative_angle = np.arccos(cosine)
    ahead = relative_angle < np.deg2rad(30.0)
    behind = relative_angle > np.deg2rad(150.0)
    relevant = ahead | (lateral[:, None, :] & ~behind)

    horizon = _TTC_PROJECTION_HORIZON_SECONDS
    elongated_ego_center = ego_center + 0.5 * horizon * ego_motion
    elongated_ego_length = ego_length + horizon * ego_speed
    elongated_ego_radius = np.hypot(elongated_ego_length / 2.0, ego_width / 2.0)
    elongated_actor_center = actor_center + 0.5 * horizon * actor_motion
    elongated_actor_length = obstacles[..., 3] + horizon * actor_speed
    elongated_actor_radius = np.hypot(
        elongated_actor_length / 2.0, obstacles[..., 4] / 2.0
    )
    elongated_center_distance = np.linalg.norm(
        elongated_actor_center - elongated_ego_center[:, None, :, :], axis=-1
    )
    possible = (
        (obstacles[..., 3] > 0.0)
        & (obstacles[..., 4] > 0.0)
        & (ego_speed[:, None, :] > _TTC_STOPPED_SPEED_MPS)
        & relevant
        & (
            elongated_center_distance
            <= elongated_ego_radius[:, None, :] + elongated_actor_radius
        )
    )
    pair_indices, actor_indices, time_indices = np.nonzero(possible)
    if pair_indices.size == 0:
        return np.zeros(candidate_count, dtype=np.float64)

    elongated_ego_corners = _obb_corners_batch(
        elongated_ego_center[pair_indices, time_indices],
        trajectories[pair_indices, time_indices, 2],
        elongated_ego_length[pair_indices, time_indices],
        np.full(pair_indices.size, ego_width),
    )
    elongated_actor_corners = _obb_corners_batch(
        elongated_actor_center[pair_indices, actor_indices, time_indices],
        obstacles[pair_indices, actor_indices, time_indices, 2],
        elongated_actor_length[pair_indices, actor_indices, time_indices],
        obstacles[pair_indices, actor_indices, time_indices, 4],
    )
    swept_overlap = (
        _obb_distance_batch(elongated_ego_corners, elongated_actor_corners)
        <= 1e-12
    )
    pair_indices = pair_indices[swept_overlap]
    actor_indices = actor_indices[swept_overlap]
    time_indices = time_indices[swept_overlap]
    if pair_indices.size == 0:
        return np.zeros(candidate_count, dtype=np.float64)

    ego_poses = trajectories[pair_indices, time_indices]
    actor_poses = obstacles[pair_indices, actor_indices, time_indices]
    ego_corners = _obb_corners_batch(
        ego_poses[:, :2],
        ego_poses[:, 2],
        np.full(pair_indices.size, ego_length),
        np.full(pair_indices.size, ego_width),
        wheelbase,
    )
    actor_corners = _obb_corners_batch(
        actor_poses[:, :2], actor_poses[:, 2], actor_poses[:, 3], actor_poses[:, 4]
    )
    initial_contact = _obb_distance_batch(ego_corners, actor_corners) <= 1e-12
    actor_minimum_ttc = np.full(pair_indices.size, np.inf, dtype=np.float64)
    actor_minimum_ttc[initial_contact] = 0.0

    moving_indices = np.flatnonzero(~initial_contact)
    if moving_indices.size:
        selected_pairs = pair_indices[moving_indices]
        selected_actors = actor_indices[moving_indices]
        selected_times = time_indices[moving_indices]
        selected_ego_center = ego_center[selected_pairs, selected_times]
        selected_ego_motion = ego_motion[selected_pairs, selected_times]
        selected_actor_center = actor_center[
            selected_pairs, selected_actors, selected_times
        ]
        selected_actor_motion = actor_motion[
            selected_pairs, selected_actors, selected_times
        ]
        projected_ego_center = (
            selected_ego_center[:, None, :]
            + projection_times[None, :, None] * selected_ego_motion[:, None, :]
        )
        projected_actor_center = (
            selected_actor_center[:, None, :]
            + projection_times[None, :, None] * selected_actor_motion[:, None, :]
        )
        ego_radius = float(np.hypot(ego_length / 2.0, ego_width / 2.0))
        selected_actor_radius = np.hypot(
            actor_poses[moving_indices, 3] / 2.0,
            actor_poses[moving_indices, 4] / 2.0,
        )
        projected_circle_overlap = (
            np.linalg.norm(projected_ego_center - projected_actor_center, axis=-1)
            <= ego_radius + selected_actor_radius[:, None]
        )
        moving_rows, projection_indices = np.nonzero(projected_circle_overlap)
        if moving_rows.size:
            projected_ego_corners = _obb_corners_batch(
                projected_ego_center[moving_rows, projection_indices],
                ego_poses[moving_indices[moving_rows], 2],
                np.full(moving_rows.size, ego_length),
                np.full(moving_rows.size, ego_width),
            )
            projected_actor_corners = _obb_corners_batch(
                projected_actor_center[moving_rows, projection_indices],
                actor_poses[moving_indices[moving_rows], 2],
                actor_poses[moving_indices[moving_rows], 3],
                actor_poses[moving_indices[moving_rows], 4],
            )
            projected_contact = (
                _obb_distance_batch(projected_ego_corners, projected_actor_corners)
                <= 1e-12
            )
            first_contact = np.full(moving_indices.size, np.inf, dtype=np.float64)
            np.minimum.at(
                first_contact,
                moving_rows[projected_contact],
                projection_times[projection_indices[projected_contact]],
            )
            actor_minimum_ttc[moving_indices] = first_contact

    frame_minimum_ttc = np.full((candidate_count, _T), np.inf, dtype=np.float64)
    np.minimum.at(
        frame_minimum_ttc,
        (pair_indices, time_indices),
        actor_minimum_ttc,
    )
    frame_deficits = np.maximum(
        _TTC_THRESHOLD_SECONDS - frame_minimum_ttc, 0.0
    )
    return dt_seconds * np.sum(frame_deficits**2, axis=1)


def _dynamic_clearance_deficit(
    trajectories_xyh: np.ndarray,
    dynamic_obbs: np.ndarray,
    ego_shape: np.ndarray,
    dt_seconds: float,
    actor_velocity_override: np.ndarray | None = None,
) -> np.ndarray:
    trajectories = np.asarray(trajectories_xyh, dtype=np.float64)
    obstacles = np.asarray(dynamic_obbs, dtype=np.float64)
    ego_velocity = _trajectory_velocity(trajectories, dt_seconds)
    actor_velocity = (
        _dynamic_obb_velocity(obstacles, dt_seconds)
        if actor_velocity_override is None
        else np.asarray(actor_velocity_override, dtype=np.float64)
    )
    if actor_velocity.shape != obstacles.shape[:3] + (2,) or not np.isfinite(actor_velocity).all():
        raise ValueError("actor velocity override must be finite [K,N,80,2]")
    candidate_count = int(trajectories.shape[0])
    if obstacles.shape[0] != candidate_count:
        raise ValueError("dynamic OBBs must share the candidate axis")
    wheelbase, length, width = (
        float(value) for value in np.asarray(ego_shape, dtype=np.float64)
    )
    actor_count = int(obstacles.shape[1])
    if actor_count == 0:
        return np.zeros(candidate_count, dtype=np.float64)

    ego_center = _ego_centers(trajectories, wheelbase)
    relative = obstacles[..., :2] - ego_center[:, None, :, :]
    center_distance = np.linalg.norm(relative, axis=-1)
    relative_unit = np.divide(
        relative,
        center_distance[..., None],
        out=np.zeros_like(relative),
        where=center_distance[..., None] > 1e-12,
    )
    relative_velocity = ego_velocity[:, None, :, :] - actor_velocity
    closing = np.maximum(
        np.sum(relative_velocity * relative_unit, axis=-1), 0.0
    )
    closing = np.where(center_distance <= 1e-12, 0.0, closing)
    ego_radius = float(np.hypot(length / 2.0, width / 2.0))
    actor_radius = np.hypot(obstacles[..., 3] / 2.0, obstacles[..., 4] / 2.0)
    circle_distance_lower_bound = np.maximum(
        center_distance - ego_radius - actor_radius, 0.0
    )
    threshold_distance = _TTC_THRESHOLD_SECONDS * closing
    possible = (
        (obstacles[..., 3] > 0.0)
        & (obstacles[..., 4] > 0.0)
        & (circle_distance_lower_bound < threshold_distance)
    )
    pair_indices, actor_indices, time_indices = np.nonzero(possible)
    if pair_indices.size == 0:
        return np.zeros(candidate_count, dtype=np.float64)

    ego_poses = trajectories[pair_indices, time_indices]
    actor_poses = obstacles[pair_indices, actor_indices, time_indices]
    ego_corners = _obb_corners_batch(
        ego_poses[:, :2],
        ego_poses[:, 2],
        np.full(pair_indices.size, length),
        np.full(pair_indices.size, width),
        wheelbase,
    )
    actor_corners = _obb_corners_batch(
        actor_poses[:, :2], actor_poses[:, 2], actor_poses[:, 3], actor_poses[:, 4]
    )
    distance = _obb_distance_batch(ego_corners, actor_corners)
    selected_threshold = threshold_distance[
        pair_indices, actor_indices, time_indices
    ]
    selected_deficit = np.maximum(selected_threshold - distance, 0.0)
    frame_deficits = np.zeros((candidate_count, _T), dtype=np.float64)
    np.maximum.at(
        frame_deficits,
        (pair_indices, time_indices),
        selected_deficit,
    )
    return dt_seconds * np.sum(frame_deficits**2, axis=1)


def materialize_v26_actual_future_actor_atom_pair(
    *,
    candidates: np.ndarray,
    expert_future_xyh: np.ndarray,
    actor_obbs: np.ndarray,
    actor_velocities: np.ndarray,
    actor_valid: np.ndarray,
    actor_source_complete: bool,
    actor_missing_reason: str | None,
    ego_shape: np.ndarray,
    route_atom_context: Mapping[str, Any] | None,
    dt_seconds: float = _DT_SECONDS,
) -> dict[str, Any]:
    """Compute only the three actor atoms from aligned actual future boxes."""

    candidate_xyh = _trajectory_xyh_from_candidate_tensor(candidates)
    expert_xyh = _validate_expert_future(expert_future_xyh)
    pair_count = int(candidate_xyh.shape[0])
    names = V26_SAME_TICK_ATOM_BANK_NAMES[:3]
    if not actor_source_complete:
        reason = actor_missing_reason or "official_future_actor_source_incomplete"
        return {
            "candidate_by_name": {},
            "expert_by_name": {},
            "states": [
                _atom_state(
                    name=name,
                    status="typed_missing",
                    unit=unit,
                    role="dynamic_safety",
                    formula=formula,
                    time_domain="0.1_to_8.0_seconds_80_samples",
                    source_authority="official_nuplan_v1.1_actual_future_lidar_box",
                    reason=reason,
                )
                for name, unit, formula in zip(
                    names,
                    ("dimensionless_fraction", "seconds_cubed", "m2_seconds"),
                    (
                        "mean_t_indicator_actual_actor_OBB_contact",
                        "dt_sum_t_max(0.95s-TTC_t,0)^2",
                        "dt_sum_t(max_j(max(0.95s*v_close_radial-d_OBB_surface,0)))^2",
                    ),
                    strict=True,
                )
            ],
        }
    obbs = np.asarray(actor_obbs, dtype=np.float64)
    velocities = np.asarray(actor_velocities, dtype=np.float64)
    valid = np.asarray(actor_valid, dtype=bool)
    if obbs.ndim != 3 or obbs.shape[1:] != (_T, 5):
        raise ValueError("actual actor OBBs must have shape [N,80,5]")
    if velocities.shape != obbs.shape[:2] + (2,) or valid.shape != obbs.shape[:2]:
        raise ValueError("actual actor velocity/valid shapes drifted")
    if not np.isfinite(obbs).all() or not np.isfinite(velocities).all():
        raise ValueError("actual actor tensors must be finite")
    masked = obbs.copy()
    masked[~valid, 3:] = 0.0
    expanded_obbs = np.repeat(masked[None, :, :, :], pair_count, axis=0)
    expanded_velocity = np.repeat(velocities[None, :, :, :], pair_count, axis=0)
    expert_pair = np.repeat(expert_xyh[None, :, :], pair_count, axis=0)
    candidate_values: dict[str, np.ndarray] = {
        names[0]: _collision_exposure(candidate_xyh, expanded_obbs, ego_shape),
        names[2]: _dynamic_clearance_deficit(
            candidate_xyh,
            expanded_obbs,
            ego_shape,
            dt_seconds,
            actor_velocity_override=expanded_velocity,
        ),
    }
    expert_values: dict[str, np.ndarray] = {
        names[0]: _collision_exposure(expert_pair, expanded_obbs, ego_shape),
        names[2]: _dynamic_clearance_deficit(
            expert_pair,
            expanded_obbs,
            ego_shape,
            dt_seconds,
            actor_velocity_override=expanded_velocity,
        ),
    }
    ttc_observed = obbs.shape[0] == 0 or bool(
        route_atom_context is not None and route_atom_context.get("route_objects")
    )
    if ttc_observed:
        candidate_lateral = (
            np.zeros((pair_count, _T), dtype=bool)
            if obbs.shape[0] == 0
            else _ttc_lateral_relevance_mask(candidate_xyh, ego_shape, route_atom_context)
        )
        expert_lateral = (
            np.zeros((pair_count, _T), dtype=bool)
            if obbs.shape[0] == 0
            else np.repeat(
                _ttc_lateral_relevance_mask(expert_xyh[None, :, :], ego_shape, route_atom_context),
                pair_count,
                axis=0,
            )
        )
        candidate_values[names[1]] = _nuplan_semantic_ttc_deficit(
            candidate_xyh,
            expanded_obbs,
            ego_shape,
            candidate_lateral,
            dt_seconds,
            actor_velocity_override=expanded_velocity,
        )
        expert_values[names[1]] = _nuplan_semantic_ttc_deficit(
            expert_pair,
            expanded_obbs,
            ego_shape,
            expert_lateral,
            dt_seconds,
            actor_velocity_override=expanded_velocity,
        )
    states = []
    for index, (name, unit, formula) in enumerate(
        zip(
            names,
            ("dimensionless_fraction", "seconds_cubed", "m2_seconds"),
            (
                "mean_t_indicator_actual_actor_OBB_contact",
                "dt_sum_t_max(0.95s-TTC_t,0)^2",
                "dt_sum_t(max_j(max(0.95s*v_close_radial-d_OBB_surface,0)))^2",
            ),
            strict=True,
        )
    ):
        states.append(
            _atom_state(
                name=name,
                status="observed" if index != 1 or ttc_observed else "typed_missing",
                unit=unit,
                role="dynamic_safety",
                formula=formula,
                time_domain="0.1_to_8.0_seconds_80_samples",
                source_authority="official_nuplan_v1.1_actual_future_lidar_box",
                reason=None if index != 1 or ttc_observed else "route_lane_intersection_relevance_source_missing",
            )
        )
    return {
        "candidate_by_name": candidate_values,
        "expert_by_name": expert_values,
        "states": states,
    }


def _geometry_coordinates(geometry: Any) -> list[tuple[float, float]]:
    if geometry is None or bool(getattr(geometry, "is_empty", True)):
        return []
    if hasattr(geometry, "coords"):
        try:
            return [(float(x), float(y)) for x, y, *_ in geometry.coords]
        except NotImplementedError:
            pass
    coordinates: list[tuple[float, float]] = []
    for child in getattr(geometry, "geoms", ()):
        coordinates.extend(_geometry_coordinates(child))
    return coordinates


def _movement_stop_arc(centerline: Any, stop_polygon: Any) -> float:
    try:
        from shapely import Point
    except ImportError as exc:  # pragma: no cover - dependency smoke
        raise ValueError("red atoms require Shapely") from exc
    crossing = centerline.intersection(stop_polygon)
    coordinates = _geometry_coordinates(crossing)
    if not coordinates:
        coordinates = _geometry_coordinates(stop_polygon.boundary)
    if not coordinates:
        raise ValueError("associated stop polygon has no baseline coordinates")
    return min(float(centerline.project(Point(point))) for point in coordinates)


def _front_arc(
    centerline: Any,
    x: float,
    y: float,
    heading: float,
    ego_shape: np.ndarray,
) -> float:
    try:
        from shapely import Point
    except ImportError as exc:  # pragma: no cover - dependency smoke
        raise ValueError("red atoms require Shapely") from exc
    wheelbase, length, width = (float(value) for value in ego_shape)
    return max(
        float(centerline.project(Point(float(point[0]), float(point[1]))))
        for point in _obb_corners(x, y, heading, length, width, wheelbase)
    )


def _centerline_tangent(centerline: Any, arc: float) -> np.ndarray:
    lower = max(float(arc) - 0.25, 0.0)
    upper = min(float(arc) + 0.25, float(centerline.length))
    if upper - lower <= 1e-9:
        raise ValueError("connector centerline has no local tangent support")
    start = np.asarray(centerline.interpolate(lower).coords[0], dtype=np.float64)
    end = np.asarray(centerline.interpolate(upper).coords[0], dtype=np.float64)
    tangent = end - start
    norm = float(np.linalg.norm(tangent))
    if norm <= 1e-9:
        raise ValueError("connector centerline tangent is degenerate")
    return tangent / norm


def _red_entry_and_stopping_atoms(
    trajectories_xyh: np.ndarray,
    ego_shape: np.ndarray,
    route_atom_context: Mapping[str, Any],
    dt_seconds: float,
) -> tuple[np.ndarray, np.ndarray]:
    try:
        from shapely import Polygon
    except ImportError as exc:  # pragma: no cover - dependency smoke
        raise ValueError("red atoms require Shapely") from exc
    movements = route_atom_context.get("red_movements")
    if not isinstance(movements, (tuple, list)) or not movements:
        raise ValueError("observed red atoms require movement-associated geometry")
    trajectories = np.asarray(trajectories_xyh, dtype=np.float64)
    candidate_count = int(trajectories.shape[0])
    velocity = _trajectory_velocity(trajectories, dt_seconds)
    shape = np.asarray(ego_shape, dtype=np.float64)
    wheelbase, length, width = (float(value) for value in shape)
    decision_footprint = Polygon(
        _obb_corners(0.0, 0.0, 0.0, length, width, wheelbase)
    )
    s7 = np.zeros(candidate_count, dtype=np.float64)
    s8 = np.zeros(candidate_count, dtype=np.float64)
    movement_metadata = []
    for movement in movements:
        centerline = movement["connector_centerline"]
        connector = movement["connector_geometry"]
        phases = tuple(str(value).lower() for value in movement["phases"])
        if len(phases) != _T:
            raise ValueError("movement phases must contain 80 actual-tick values")
        stop_arc = _movement_stop_arc(
            centerline, movement["stop_polygon_geometry"]
        )
        movement_metadata.append((centerline, connector, phases, stop_arc))

    for pair_index in range(candidate_count):
        exposure_fraction = np.zeros(_T, dtype=np.float64)
        stopping_deficit = np.zeros(_T, dtype=np.float64)
        footprints = [
            Polygon(
                _obb_corners(x, y, heading, length, width, wheelbase)
            )
            for x, y, heading in trajectories[pair_index]
        ]
        for centerline, connector, phases, stop_arc in movement_metadata:
            initially_inside = bool(decision_footprint.intersects(connector))
            consumed_entry = initially_inside
            active_red_entry = False
            previous_inside = initially_inside
            previous_front_arc = _front_arc(
                centerline, 0.0, 0.0, 0.0, shape
            )
            for time_index, (pose, footprint) in enumerate(
                zip(trajectories[pair_index], footprints)
            ):
                x, y, heading = pose
                current_inside = bool(footprint.intersects(connector))
                current_front_arc = _front_arc(
                    centerline, x, y, heading, shape
                )
                crossed_stop = (
                    previous_front_arc <= stop_arc + 1e-6
                    and current_front_arc > stop_arc + 1e-6
                )
                if (
                    not consumed_entry
                    and not previous_inside
                    and current_inside
                    and crossed_stop
                ):
                    consumed_entry = True
                    active_red_entry = phases[time_index] == "red"
                if active_red_entry and current_inside:
                    fraction = float(footprint.intersection(connector).area) / float(
                        footprint.area
                    )
                    exposure_fraction[time_index] = max(
                        exposure_fraction[time_index], fraction
                    )
                elif active_red_entry and not current_inside:
                    active_red_entry = False

                if phases[time_index] == "red" and current_front_arc < stop_arc:
                    tangent = _centerline_tangent(centerline, current_front_arc)
                    v_parallel = max(
                        float(np.dot(velocity[pair_index, time_index], tangent)),
                        0.0,
                    )
                    distance = float(stop_arc - current_front_arc)
                    deficit = max(
                        v_parallel**2
                        / (2.0 * _RED_STOPPING_DECELERATION_MPS2)
                        - distance,
                        0.0,
                    )
                    stopping_deficit[time_index] = max(
                        stopping_deficit[time_index], deficit
                    )
                previous_inside = current_inside
                previous_front_arc = current_front_arc
        s7[pair_index] = dt_seconds * float(np.sum(exposure_fraction))
        s8[pair_index] = dt_seconds * float(np.sum(stopping_deficit**2))
    return s7, s8


def _candidate_tensor_from_xyh(trajectories_xyh: np.ndarray) -> np.ndarray:
    trajectories = np.asarray(trajectories_xyh, dtype=np.float64)
    if trajectories.ndim != 3 or trajectories.shape[0] < 1 or trajectories.shape[1:] != (_T, 3) or not np.isfinite(trajectories).all():
        raise ValueError("trajectories_xyh must be finite [K,80,3]")
    return np.concatenate(
        (
            trajectories[:, :, :2],
            np.cos(trajectories[:, :, 2:3]),
            np.sin(trajectories[:, :, 2:3]),
        ),
        axis=2,
    )


def _overspeed_integral(
    trajectories_xyh: np.ndarray,
    speed_limit_mps: np.ndarray,
    dt_seconds: float,
) -> np.ndarray:
    trajectories = np.asarray(trajectories_xyh, dtype=np.float64)
    limits = np.asarray(speed_limit_mps, dtype=np.float64)
    candidate_count = int(trajectories.shape[0])
    if trajectories.ndim != 3 or trajectories.shape[1:] != (_T, 3) or limits.shape != (candidate_count, _T):
        raise ValueError("overspeed inputs must be [K,80,3] and [K,80]")
    if not np.isfinite(trajectories).all() or not np.isfinite(limits).all():
        raise ValueError("overspeed inputs must be finite")
    if np.any(limits <= 0.0):
        raise ValueError("overspeed requires positive exact route speed limits")
    speed = np.linalg.norm(np.diff(trajectories[:, :, :2], axis=1), axis=2) / float(
        dt_seconds
    )
    return float(dt_seconds) * np.sum(
        np.square(np.maximum(speed - limits[:, 1:], 0.0)), axis=1
    )


def _road_exit_severity(
    trajectories_xyh: np.ndarray,
    drivable_area_geometry: Any,
    ego_shape: np.ndarray,
    dt_seconds: float,
) -> np.ndarray:
    try:
        from shapely import area, difference, is_valid, polygons
    except ImportError as exc:  # pragma: no cover - exercised by dependency smoke
        raise ValueError("full-footprint road atom requires Shapely") from exc
    trajectories = np.asarray(trajectories_xyh, dtype=np.float64)
    shape = np.asarray(ego_shape, dtype=np.float64)
    if trajectories.ndim != 3 or trajectories.shape[0] < 1 or trajectories.shape[1:] != (_T, 3) or not np.isfinite(trajectories).all():
        raise ValueError("road trajectories must be finite [K,80,3]")
    if shape.shape != (3,) or not np.isfinite(shape).all() or np.any(shape <= 0.0):
        raise ValueError("ego_shape must be finite positive [wheelbase,length,width]")
    if (
        drivable_area_geometry is None
        or bool(getattr(drivable_area_geometry, "is_empty", True))
        or not bool(getattr(drivable_area_geometry, "is_valid", False))
    ):
        raise ValueError("drivable area geometry must be nonempty and valid")
    wheelbase, length, width = (float(value) for value in shape)
    candidate_count = int(trajectories.shape[0])
    flat_count = candidate_count * _T
    footprints = polygons(
        _obb_corners_batch(
            trajectories[..., :2].reshape(flat_count, 2),
            trajectories[..., 2].reshape(flat_count),
            np.full(flat_count, length),
            np.full(flat_count, width),
            wheelbase,
        )
    )
    footprint_area = area(footprints)
    if not np.all(is_valid(footprints)) or np.any(footprint_area <= 0.0):
        raise ValueError("ego footprint geometry is invalid")
    outside_area = area(difference(footprints, drivable_area_geometry))
    result = float(dt_seconds) * np.sum(
        (outside_area / footprint_area).reshape(candidate_count, _T), axis=1
    )
    if not np.isfinite(result).all() or np.any(result < 0.0):
        raise ValueError("road-exit severity must be finite nonnegative")
    return result


def _reverse_progress_severity(projected_arc_m: np.ndarray) -> np.ndarray:
    arc = np.asarray(projected_arc_m, dtype=np.float64)
    if arc.ndim != 2 or arc.shape[0] < 1 or arc.shape[1] != _T or not np.isfinite(arc).all():
        raise ValueError("projected route arc must be finite [K,80]")
    return np.mean(np.maximum(-(arc[:, 10:] - arc[:, :-10]), 0.0), axis=1)


def _progress_shortfall(
    candidate_progress_m: np.ndarray,
    expert_progress_m: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    candidate = np.asarray(candidate_progress_m, dtype=np.float64)
    expert = np.asarray(expert_progress_m, dtype=np.float64)
    if candidate.ndim != 1 or candidate.shape[0] < 1 or expert.shape != candidate.shape:
        raise ValueError("route progress must have matching shape [K]")
    if not np.isfinite(candidate).all() or not np.isfinite(expert).all():
        raise ValueError("route progress must be finite")
    reference = float(np.max(candidate))
    return (
        np.maximum(reference - candidate, 0.0),
        np.maximum(reference - expert, 0.0),
    )


def _atom_state(
    *,
    name: str,
    status: str,
    unit: str,
    role: str,
    formula: str,
    time_domain: str,
    source_authority: str,
    reason: str | None = None,
) -> dict[str, Any]:
    if status not in {"observed", "not_applicable", "typed_missing"}:
        raise ValueError("unknown atom state")
    return {
        "name": name,
        "status": status,
        "unit": unit,
        "role": role,
        "cost_direction": "lower_is_better",
        "formula": formula,
        "time_domain": time_domain,
        "source_authority": source_authority,
        "reason": reason,
    }


def _comfort_atoms(trajectories_xyh: np.ndarray, dt_seconds: float) -> np.ndarray:
    xy = trajectories_xyh[:, :, :2]
    heading = trajectories_xyh[:, :, 2]
    velocity = np.diff(xy, axis=1) / dt_seconds
    acceleration = np.diff(velocity, axis=1) / dt_seconds
    jerk_world = np.diff(acceleration, axis=1) / dt_seconds

    acceleration_heading = heading[:, 2:]
    acceleration_forward = np.stack(
        (np.cos(acceleration_heading), np.sin(acceleration_heading)), axis=-1
    )
    acceleration_left = np.stack(
        (-np.sin(acceleration_heading), np.cos(acceleration_heading)), axis=-1
    )
    longitudinal_acceleration = np.sum(acceleration * acceleration_forward, axis=-1)
    lateral_acceleration = np.sum(acceleration * acceleration_left, axis=-1)

    jerk_heading = heading[:, 3:]
    jerk_forward = np.stack((np.cos(jerk_heading), np.sin(jerk_heading)), axis=-1)
    longitudinal_jerk = np.sum(jerk_world * jerk_forward, axis=-1)
    jerk_magnitude = np.linalg.norm(jerk_world, axis=-1)

    yaw_rate = np.diff(heading, axis=1) / dt_seconds
    yaw_acceleration = np.diff(yaw_rate, axis=1) / dt_seconds

    positive_longitudinal = np.maximum(longitudinal_acceleration, 0.0)
    negative_longitudinal = np.minimum(longitudinal_acceleration, 0.0)
    atoms = np.stack(
        (
            dt_seconds
            * np.sum(
                np.square(
                    positive_longitudinal
                    / _COMFORT_THRESHOLDS["longitudinal_acceleration_positive"]
                )
                + np.square(
                    negative_longitudinal
                    / _COMFORT_THRESHOLDS["longitudinal_acceleration_negative"]
                ),
                axis=1,
            ),
            dt_seconds
            * np.sum(
                np.square(
                    lateral_acceleration
                    / _COMFORT_THRESHOLDS["lateral_acceleration"]
                ),
                axis=1,
            ),
            dt_seconds
            * np.sum(np.square(yaw_rate / _COMFORT_THRESHOLDS["yaw_rate"]), axis=1),
            dt_seconds
            * np.sum(
                np.square(
                    yaw_acceleration / _COMFORT_THRESHOLDS["yaw_acceleration"]
                ),
                axis=1,
            ),
            dt_seconds
            * np.sum(
                np.square(
                    longitudinal_jerk
                    / _COMFORT_THRESHOLDS["longitudinal_jerk"]
                ),
                axis=1,
            ),
            dt_seconds
            * np.sum(
                np.square(jerk_magnitude / _COMFORT_THRESHOLDS["jerk_magnitude"]),
                axis=1,
            ),
        ),
        axis=1,
    )
    if not np.isfinite(atoms).all() or np.any(atoms < 0.0):
        raise ValueError("comfort atoms must be finite and nonnegative")
    return atoms


def materialize_v26_minimal_expert_candidate_atom_pair(
    *,
    identity: Mapping[str, Any],
    candidates: np.ndarray,
    expert_future_xyh: np.ndarray,
    obstacle_obbs: np.ndarray,
    ego_shape: np.ndarray,
    dt_seconds: float = _DT_SECONDS,
    scenario_reference: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute pair-specific candidate and expert raw atoms at one source tick."""

    if float(dt_seconds) != _DT_SECONDS:
        raise ValueError(f"dt_seconds must equal the fixed {_DT_SECONDS}")
    candidate_xyh = _trajectory_xyh_from_candidate_tensor(candidates)
    candidate_count = int(candidate_xyh.shape[0])
    expert_xyh = _validate_expert_future(expert_future_xyh)
    expert_pair_xyh = np.repeat(expert_xyh[None, :, :], candidate_count, axis=0)

    candidate_collision = _collision_exposure(candidate_xyh, obstacle_obbs, ego_shape)
    expert_collision = _collision_exposure(expert_pair_xyh, obstacle_obbs, ego_shape)
    candidate_comfort = _comfort_atoms(candidate_xyh, dt_seconds)
    expert_comfort = _comfort_atoms(expert_pair_xyh, dt_seconds)
    candidate_atoms = np.concatenate((candidate_collision[:, None], candidate_comfort), axis=1)
    expert_atoms = np.concatenate((expert_collision[:, None], expert_comfort), axis=1)
    if not np.isfinite(candidate_atoms).all() or not np.isfinite(expert_atoms).all():
        raise ValueError("raw atoms must be finite")

    atom_states = [
        {
            "name": V26_MINIMAL_PAIR_ATOM_NAMES[0],
            "status": "observed",
            "unit": "dimensionless_fraction",
            "role": "dynamic_safety",
            "source_authority": "source_derived_existing_obb_geometry",
            "same_formula_and_unit_both_sides": True,
            "pair_context": "neighbor_predictions[pair_index]",
        }
    ]
    for name in V26_MINIMAL_PAIR_ATOM_NAMES[1:]:
        atom_states.append(
            {
                "name": name,
                "status": "observed",
                "unit": "seconds",
                "role": "comfort",
                "source_authority": "custom_full_horizon_threshold_normalized_squared_energy",
                "same_formula_and_unit_both_sides": True,
                "pair_context": "ego_trajectory_only",
            }
        )

    return {
        "identity": _validate_identity(identity),
        "K": candidate_count,
        "T": _T,
        "dt_seconds": _DT_SECONDS,
        "candidate0_row": 0,
        "ordered_atom_names": list(V26_MINIMAL_PAIR_ATOM_NAMES),
        "candidate_atoms_raw": candidate_atoms,
        "expert_atoms_raw": expert_atoms,
        "atom_states": atom_states,
        "scenario_reference": _validate_scenario_reference(scenario_reference),
    }


def materialize_v26_same_tick_full_atom_bank_pair(
    *,
    identity: Mapping[str, Any],
    candidates: np.ndarray,
    expert_future_xyh: np.ndarray | None,
    obstacle_obbs: np.ndarray,
    dynamic_obbs: np.ndarray | None,
    ego_shape: np.ndarray,
    route_lanes: np.ndarray,
    route_speed_limits: np.ndarray,
    route_has_speed_limits: np.ndarray,
    signal_authority: Mapping[str, Any],
    actor_source_complete: bool,
    route_atom_context: Mapping[str, Any] | None = None,
    drivable_area_geometry: Any | None = None,
    drivable_area_source_authority: str | None = None,
    dt_seconds: float = _DT_SECONDS,
    scenario_reference: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Materialize the fixed same-tick research bank without missing-value proxies.

    With an expert future, the returned raw matrices contain only atoms
    observed on both sides.  Without one, the returned candidate-only artifact
    contains every observed candidate-side column and no expert proxy.  The
    complete 15-atom bank and every non-observed state remain explicit in
    ``atom_states``; no NaN, zero placeholder, runtime schema substitution, or
    candidate-local mask is created.
    """

    if float(dt_seconds) != _DT_SECONDS:
        raise ValueError(f"dt_seconds must equal the fixed {_DT_SECONDS}")
    if not isinstance(actor_source_complete, bool):
        raise ValueError("actor_source_complete must be bool")
    candidate_xyh = _trajectory_xyh_from_candidate_tensor(candidates)
    candidate_count = int(candidate_xyh.shape[0])
    expert_single_xyh = None
    expert_pair_xyh = None
    if expert_future_xyh is not None:
        expert_xyh = _validate_expert_future(expert_future_xyh)
        expert_single_xyh = expert_xyh[None, :, :]
        expert_pair_xyh = np.repeat(expert_single_xyh, candidate_count, axis=0)
    candidate_tensor = _candidate_tensor_from_xyh(candidate_xyh)
    expert_tensor = (
        None
        if expert_single_xyh is None
        else _candidate_tensor_from_xyh(expert_single_xyh)
    )

    observed_candidate: dict[str, np.ndarray] = {}
    observed_expert: dict[str, np.ndarray] = {}
    states: list[dict[str, Any]] = []

    if actor_source_complete:
        observed_candidate[V26_SAME_TICK_ATOM_BANK_NAMES[0]] = _collision_exposure(
            candidate_xyh, obstacle_obbs, ego_shape
        )
        if expert_pair_xyh is not None:
            observed_expert[V26_SAME_TICK_ATOM_BANK_NAMES[0]] = _collision_exposure(
                expert_pair_xyh, obstacle_obbs, ego_shape
            )
        states.append(
            _atom_state(
                name=V26_SAME_TICK_ATOM_BANK_NAMES[0],
                status="observed",
                unit="dimensionless_fraction",
                role="dynamic_safety",
                formula="mean_t_indicator_min_pair_specific_OBB_surface_distance_equals_zero",
                time_domain="0.0_to_7.9_seconds_80_samples",
                source_authority="source_derived_existing_OBB_contact_geometry_same_c_i_both_sides",
            )
        )
    else:
        states.append(
            _atom_state(
                name=V26_SAME_TICK_ATOM_BANK_NAMES[0],
                status="typed_missing",
                unit="dimensionless_fraction",
                role="dynamic_safety",
                formula="mean_t_indicator_min_pair_specific_OBB_surface_distance_equals_zero",
                time_domain="0.0_to_7.9_seconds_80_samples",
                source_authority="source_derived_existing_OBB_contact_geometry_same_c_i_both_sides",
                reason="pair_specific_actor_prediction_or_OBB_source_incomplete",
            )
        )

    dynamic_source_observed = actor_source_complete and dynamic_obbs is not None
    ttc_source_observed = bool(
        dynamic_source_observed
        and route_atom_context is not None
        and route_atom_context.get("route_objects")
    )
    if ttc_source_observed:
        candidate_lateral = _ttc_lateral_relevance_mask(
            candidate_xyh, ego_shape, route_atom_context
        )
        expert_lateral = (
            None
            if expert_single_xyh is None
            else np.repeat(
                _ttc_lateral_relevance_mask(
                    expert_single_xyh, ego_shape, route_atom_context
                ),
                candidate_count,
                axis=0,
            )
        )
        observed_candidate[V26_SAME_TICK_ATOM_BANK_NAMES[1]] = (
            _nuplan_semantic_ttc_deficit(
                candidate_xyh,
                dynamic_obbs,
                ego_shape,
                candidate_lateral,
                dt_seconds,
            )
        )
        if expert_pair_xyh is not None and expert_lateral is not None:
            observed_expert[V26_SAME_TICK_ATOM_BANK_NAMES[1]] = (
                _nuplan_semantic_ttc_deficit(
                    expert_pair_xyh,
                    dynamic_obbs,
                    ego_shape,
                    expert_lateral,
                    dt_seconds,
                )
            )
    states.append(
        _atom_state(
            name=V26_SAME_TICK_ATOM_BANK_NAMES[1],
            status="observed" if ttc_source_observed else "typed_missing",
            unit="seconds_cubed",
            role="dynamic_safety",
            formula="dt_sum_t_max(0.95s-TTC_t,0)^2",
            time_domain="0.0_to_7.9_seconds_frames_with_0.1s_CV_projection_to_3.0s",
            source_authority="NuPlan_official_TTC_semantics_continuous_project_atom",
            reason=None
            if ttc_source_observed
            else "dynamic_actor_or_route_lane_intersection_relevance_source_missing",
        )
    )
    if dynamic_source_observed:
        observed_candidate[V26_SAME_TICK_ATOM_BANK_NAMES[2]] = (
            _dynamic_clearance_deficit(
                candidate_xyh, dynamic_obbs, ego_shape, dt_seconds
            )
        )
        if expert_pair_xyh is not None:
            observed_expert[V26_SAME_TICK_ATOM_BANK_NAMES[2]] = (
                _dynamic_clearance_deficit(
                    expert_pair_xyh, dynamic_obbs, ego_shape, dt_seconds
                )
            )
    states.append(
        _atom_state(
            name=V26_SAME_TICK_ATOM_BANK_NAMES[2],
            status="observed" if dynamic_source_observed else "typed_missing",
            unit="m2_seconds",
            role="dynamic_safety",
            formula="dt_sum_t(max_j(max(0.95s*v_close_radial-d_OBB_surface,0)))^2",
            time_domain="0.0_to_7.9_seconds_80_samples",
            source_authority="project_authoritative_source_grounded_custom_academic_atom",
            reason=None
            if dynamic_source_observed
            else "pair_specific_dynamic_actor_prediction_or_OBB_source_missing",
        )
    )

    route_candidate = None
    route_expert = None
    route_error = None
    try:
        route_candidate = project_candidates_to_route(
            candidate_tensor,
            route_lanes,
            route_speed_limits,
            route_has_speed_limits,
            speed_source_policy=CANDIDATE_LOCAL_EXACT_SPEED,
        )
        if expert_tensor is not None:
            route_expert = project_candidates_to_route(
                expert_tensor,
                route_lanes,
                route_speed_limits,
                route_has_speed_limits,
                speed_source_policy=CANDIDATE_LOCAL_EXACT_SPEED,
            )
    except (ValueError, TypeError) as exc:
        route_error = f"{type(exc).__name__}:{exc}"

    speed_observed = bool(
        route_candidate is not None
        and np.asarray(route_candidate["route_speed_source_eligible_mask"], dtype=bool).all()
        and (
            route_expert is None
            or np.asarray(
                route_expert["route_speed_source_eligible_mask"], dtype=bool
            ).all()
        )
    )
    if speed_observed:
        observed_candidate[V26_SAME_TICK_ATOM_BANK_NAMES[3]] = _overspeed_integral(
            candidate_xyh, route_candidate["speed_limit"], dt_seconds
        )
        if expert_single_xyh is not None and route_expert is not None:
            observed_expert[V26_SAME_TICK_ATOM_BANK_NAMES[3]] = _overspeed_integral(
                expert_single_xyh, route_expert["speed_limit"], dt_seconds
            ).repeat(candidate_count)
    states.append(
        _atom_state(
            name=V26_SAME_TICK_ATOM_BANK_NAMES[3],
            status="observed" if speed_observed else "typed_missing",
            unit="m2_per_s",
            role="safety",
            formula="dt_sum_n_max(norm_velocity_n_minus_exact_route_limit_n_plus_1,0)^2",
            time_domain="0.1_to_7.9_seconds_79_intervals",
            source_authority="source_derived_exact_directed_route_speed_limit",
            reason=None
            if speed_observed
            else (route_error or "exact_positive_speed_limit_not_available_for_every_pair"),
        )
    )

    road_observed = drivable_area_geometry is not None
    if road_observed:
        observed_candidate[V26_SAME_TICK_ATOM_BANK_NAMES[4]] = _road_exit_severity(
            candidate_xyh, drivable_area_geometry, ego_shape, dt_seconds
        )
        if expert_single_xyh is not None:
            observed_expert[V26_SAME_TICK_ATOM_BANK_NAMES[4]] = _road_exit_severity(
                expert_single_xyh, drivable_area_geometry, ego_shape, dt_seconds
            ).repeat(candidate_count)
    states.append(
        _atom_state(
            name=V26_SAME_TICK_ATOM_BANK_NAMES[4],
            status="observed" if road_observed else "typed_missing",
            unit="seconds",
            role="safety",
            formula="dt_sum_t_area(ego_footprint_t_minus_drivable_area)/area(ego_footprint_t)",
            time_domain="0.0_to_7.9_seconds_80_samples",
            source_authority=drivable_area_source_authority
            or "source_derived_full_drivable_polygon_union_required",
            reason=None if road_observed else "full_drivable_area_polygon_source_unavailable",
        )
    )

    route_observed = route_candidate is not None and (
        expert_pair_xyh is None or route_expert is not None
    )
    if route_observed:
        observed_candidate[V26_SAME_TICK_ATOM_BANK_NAMES[5]] = (
            _reverse_progress_severity(route_candidate["projected_arc"])
        )
        if route_expert is not None:
            observed_expert[V26_SAME_TICK_ATOM_BANK_NAMES[5]] = (
                _reverse_progress_severity(route_expert["projected_arc"]).repeat(
                    candidate_count
                )
            )
    states.append(
        _atom_state(
            name=V26_SAME_TICK_ATOM_BANK_NAMES[5],
            status="observed" if route_observed else "typed_missing",
            unit="metres",
            role="safety",
            formula="mean_t_0_to_69_max(-(route_arc_t_plus_10-route_arc_t),0)",
            time_domain="rolling_1_second_windows_over_0.0_to_7.9_seconds",
            source_authority="source_derived_directed_mission_route_projection",
            reason=None if route_observed else (route_error or "directed_route_projection_unavailable"),
        )
    )

    signal_state = (
        str(route_atom_context.get("signal_source_state"))
        if route_atom_context is not None
        else str(signal_authority.get("source_state", "typed_missing"))
    )
    if signal_state not in {"observed", "not_applicable", "typed_missing"}:
        signal_state = "typed_missing"
    red_reason = (
        None
        if signal_state == "observed"
        else (
            str(route_atom_context.get("signal_reason"))
            if route_atom_context is not None
            else "movement_associated_signal_context_missing"
        )
    )
    if signal_state == "observed":
        candidate_red, candidate_stop = _red_entry_and_stopping_atoms(
            candidate_xyh, ego_shape, route_atom_context, dt_seconds
        )
        observed_candidate[V26_SAME_TICK_ATOM_BANK_NAMES[6]] = candidate_red
        observed_candidate[V26_SAME_TICK_ATOM_BANK_NAMES[7]] = candidate_stop
        if expert_single_xyh is not None:
            expert_red, expert_stop = _red_entry_and_stopping_atoms(
                expert_single_xyh, ego_shape, route_atom_context, dt_seconds
            )
            observed_expert[V26_SAME_TICK_ATOM_BANK_NAMES[6]] = expert_red.repeat(
                candidate_count
            )
            observed_expert[V26_SAME_TICK_ATOM_BANK_NAMES[7]] = expert_stop.repeat(
                candidate_count
            )
    states.extend(
        [
            _atom_state(
                name=V26_SAME_TICK_ATOM_BANK_NAMES[6],
                status=signal_state,
                unit="seconds",
                role="traffic_safety",
                formula="dt_sum_t_area(EgoOBB_t_intersect_C_red_entry)/area(EgoOBB_t)",
                time_domain="0.0_to_7.9_seconds_80_samples",
                source_authority="NAVSIM_geometry_intersection_inspired_continuous_project_atom_with_nuPlan_movement_phase_source",
                reason=red_reason,
            ),
            _atom_state(
                name=V26_SAME_TICK_ATOM_BANK_NAMES[7],
                status=signal_state,
                unit="m2_seconds",
                role="traffic_safety_comfort",
                formula="dt_sum_t_max(v_parallel^2/(2*4.05mps2)-directed_front_stopline_distance,0)^2",
                time_domain="movement_associated_red_upstream_samples_over_0.0_to_7.9_seconds",
                source_authority="project_authoritative_source_grounded_custom_academic_atom",
                reason=red_reason,
            ),
        ]
    )

    if route_observed:
        candidate_progress = np.asarray(route_candidate["route_progress"], dtype=np.float64)
        candidate_shortfall = np.maximum(
            float(np.max(candidate_progress)) - candidate_progress, 0.0
        )
        observed_candidate[V26_SAME_TICK_ATOM_BANK_NAMES[8]] = candidate_shortfall
        if route_expert is not None:
            _, expert_shortfall = _progress_shortfall(
                candidate_progress,
                np.full(
                    candidate_count,
                    float(np.asarray(route_expert["route_progress"])[0]),
                    dtype=np.float64,
                ),
            )
            observed_expert[V26_SAME_TICK_ATOM_BANK_NAMES[8]] = expert_shortfall
    states.append(
        _atom_state(
            name=V26_SAME_TICK_ATOM_BANK_NAMES[8],
            status="observed" if route_observed else "typed_missing",
            unit="metres",
            role="efficiency_tradeoff",
            formula="max(max_candidate_final_route_progress-final_route_progress,0)",
            time_domain="0.0_to_8.0_seconds",
            source_authority="source_derived_directed_mission_route_projection_shared_across_K",
            reason=None if route_observed else (route_error or "directed_route_projection_unavailable"),
        )
    )

    candidate_comfort = _comfort_atoms(candidate_xyh, dt_seconds)
    expert_comfort = (
        None
        if expert_single_xyh is None
        else np.repeat(
            _comfort_atoms(expert_single_xyh, dt_seconds),
            candidate_count,
            axis=0,
        )
    )
    comfort_formulas = (
        "dt_sum[(max(a_parallel,0)/2.40)^2+(max(-a_parallel,0)/4.05)^2]",
        "dt_sum(a_lateral/4.89)^2",
        "dt_sum(yaw_rate/0.95)^2",
        "dt_sum(yaw_acceleration/1.93)^2",
        "dt_sum(world_jerk_projected_on_heading/4.13)^2",
        "dt_sum(norm(world_jerk)/8.37)^2",
    )
    comfort_domains = (
        "0.2_to_7.9_seconds_78_samples",
        "0.2_to_7.9_seconds_78_samples",
        "0.1_to_7.9_seconds_79_samples",
        "0.2_to_7.9_seconds_78_samples",
        "0.3_to_7.9_seconds_77_samples",
        "0.3_to_7.9_seconds_77_samples",
    )
    for offset, name in enumerate(V26_SAME_TICK_ATOM_BANK_NAMES[9:]):
        observed_candidate[name] = candidate_comfort[:, offset]
        if expert_comfort is not None:
            observed_expert[name] = expert_comfort[:, offset]
        states.append(
            _atom_state(
                name=name,
                status="observed",
                unit="seconds",
                role="comfort",
                formula=comfort_formulas[offset],
                time_domain=comfort_domains[offset],
                source_authority="custom_full_horizon_official_threshold_normalized_squared_energy",
            )
        )

    if tuple(state["name"] for state in states) != V26_SAME_TICK_ATOM_BANK_NAMES:
        raise RuntimeError("same-tick atom bank state order drifted")
    observed_names = tuple(
        name
        for name in V26_SAME_TICK_ATOM_BANK_NAMES
        if name in observed_candidate
        and (expert_pair_xyh is None or name in observed_expert)
    )
    candidate_atoms = np.column_stack(
        [observed_candidate[name] for name in observed_names]
    )
    expert_atoms = (
        None
        if expert_pair_xyh is None
        else np.column_stack([observed_expert[name] for name in observed_names])
    )
    if (
        candidate_atoms.shape != (candidate_count, len(observed_names))
        or not np.isfinite(candidate_atoms).all()
        or np.any(candidate_atoms < 0.0)
    ):
        raise RuntimeError("observed candidate raw atoms must be finite nonnegative")
    if expert_atoms is not None and (
        expert_atoms.shape != candidate_atoms.shape
        or not np.isfinite(expert_atoms).all()
        or np.any(expert_atoms < 0.0)
    ):
        raise RuntimeError("observed expert raw atoms must be finite nonnegative")
    artifact = {
        "artifact_role": (
            "candidate_q95_source" if expert_atoms is None else "expert_candidate_bt_pair"
        ),
        "identity": _validate_identity(identity),
        "K": candidate_count,
        "T": _T,
        "dt_seconds": _DT_SECONDS,
        "candidate0_row": 0,
        "bank_atom_names": list(V26_SAME_TICK_ATOM_BANK_NAMES),
        "observed_atom_names": list(observed_names),
        "observed_global_atom_indices": [
            V26_GLOBAL_ATOM_INDEX[name] for name in observed_names
        ],
        "candidate_atoms_raw": candidate_atoms,
        "atom_states": states,
        "scenario_reference": _validate_scenario_reference(scenario_reference),
    }
    if expert_atoms is None:
        artifact["expert_future_state"] = "typed_missing"
    else:
        artifact["expert_atoms_raw"] = expert_atoms
    return artifact


def materialize_v26_nuplan_expert_candidate_atom_pair_for_tick(
    *,
    db_path: str,
    lidar_pc_token: str | bytes,
    identity: Mapping[str, Any],
    candidates: np.ndarray,
    causal_input: Mapping[str, Any],
    neighbor_predictions: np.ndarray,
    neighbor_valid_mask: np.ndarray,
    scenario_reference: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind the minimal artifact to one existing fixed-DP nuPlan source tick."""

    required = ("neighbor_agents_past", "static_objects", "ego_shape")
    missing = [name for name in required if name not in causal_input]
    if missing:
        raise ValueError(f"causal_input is missing required fields: {missing}")
    expert_future = load_nuplan_expert_ego_future(
        db_path,
        lidar_pc_token,
        target_dt_s=_DT_SECONDS,
        horizon_steps=_T,
    )
    obstacle_obbs = build_observable_obbs(
        neighbor_predictions=neighbor_predictions,
        neighbor_valid_mask=neighbor_valid_mask,
        neighbor_history=np.asarray(causal_input["neighbor_agents_past"]),
        static_objects=np.asarray(causal_input["static_objects"]),
    )
    return materialize_v26_minimal_expert_candidate_atom_pair(
        identity=identity,
        candidates=candidates,
        expert_future_xyh=expert_future,
        obstacle_obbs=obstacle_obbs,
        ego_shape=np.asarray(causal_input["ego_shape"]),
        scenario_reference=scenario_reference,
    )


def bind_v26_nuplan_same_tick_full_atom_sources(
    *,
    db_path: str,
    map_path: str,
    lidar_pc_token: str | bytes,
    candidates: np.ndarray,
    causal_input: Mapping[str, Any],
    neighbor_predictions: np.ndarray,
    neighbor_valid_mask: np.ndarray,
    require_expert_future: bool = True,
    preloaded_expert_future_xyh: np.ndarray | None = None,
) -> dict[str, Any]:
    """Read one tick's authoritative sources before pure pair atom computation."""

    required = (
        "neighbor_agents_past",
        "static_objects",
        "ego_shape",
        "route_lanes",
        "route_lanes_speed_limit",
        "route_lanes_has_speed_limit",
    )
    missing = [name for name in required if name not in causal_input]
    if missing:
        raise ValueError(f"causal_input is missing required fields: {missing}")
    expert_future = None
    if preloaded_expert_future_xyh is not None:
        expert_future = _validate_expert_future(preloaded_expert_future_xyh)
    elif require_expert_future:
        expert_future = load_nuplan_expert_ego_future(
            db_path,
            lidar_pc_token,
            target_dt_s=_DT_SECONDS,
            horizon_steps=_T,
        )
    obstacle_obbs = build_observable_obbs(
        neighbor_predictions=neighbor_predictions,
        neighbor_valid_mask=neighbor_valid_mask,
        neighbor_history=np.asarray(causal_input["neighbor_agents_past"]),
        static_objects=np.asarray(causal_input["static_objects"]),
    )
    dynamic_obbs = build_observable_obbs(
        neighbor_predictions=neighbor_predictions,
        neighbor_valid_mask=neighbor_valid_mask,
        neighbor_history=np.asarray(causal_input["neighbor_agents_past"]),
        static_objects=np.asarray(causal_input["static_objects"]),
        include_static_objects=False,
    )
    candidate_xyh = _trajectory_xyh_from_candidate_tensor(candidates)
    geometry_xy = candidate_xyh[:, :, :2]
    if expert_future is not None:
        geometry_xy = np.concatenate(
            (geometry_xy, expert_future[None, :, :2]), axis=0
        )
    try:
        drivable = load_nuplan_same_tick_drivable_area(
            db_path,
            map_path,
            lidar_pc_token,
            geometry_xy.reshape(-1, 2),
            np.asarray(causal_input["ego_shape"]),
        )
    except NuPlanCausalSourceError as exc:
        drivable = {
            "geometry": None,
            "source_authority": f"typed_missing:{type(exc).__name__}:{exc}",
        }
    try:
        route_atom_context = load_nuplan_same_tick_route_atom_context(
            db_path,
            map_path,
            lidar_pc_token,
            local_trajectory_xy=geometry_xy.reshape(-1, 2),
            ego_shape=np.asarray(causal_input["ego_shape"]),
            target_dt_s=_DT_SECONDS,
            horizon_steps=_T,
        )
    except NuPlanCausalSourceError as exc:
        route_atom_context = {
            "route_objects": (),
            "red_movements": (),
            "signal_source_state": "typed_missing",
            "signal_reason": f"{type(exc).__name__}:{exc}",
            "source_authority": "typed_missing_nuplan_route_atom_context",
        }
    return {
        "expert_future_xyh": expert_future,
        "obstacle_obbs": obstacle_obbs,
        "dynamic_obbs": dynamic_obbs,
        "ego_shape": np.asarray(causal_input["ego_shape"]),
        "route_lanes": np.asarray(causal_input["route_lanes"]),
        "route_speed_limits": np.asarray(causal_input["route_lanes_speed_limit"]),
        "route_has_speed_limits": np.asarray(
            causal_input["route_lanes_has_speed_limit"]
        ),
        "route_atom_context": route_atom_context,
        "drivable_area_geometry": drivable["geometry"],
        "drivable_area_source_authority": str(drivable["source_authority"]),
    }


def materialize_v26_nuplan_same_tick_full_atom_bank_pair(
    *,
    db_path: str,
    map_path: str,
    lidar_pc_token: str | bytes,
    identity: Mapping[str, Any],
    candidates: np.ndarray,
    causal_input: Mapping[str, Any],
    neighbor_predictions: np.ndarray,
    neighbor_valid_mask: np.ndarray,
    signal_authority: Mapping[str, Any],
    scenario_reference: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute the full bank states transiently inside one fixed-DP tick."""

    sources = bind_v26_nuplan_same_tick_full_atom_sources(
        db_path=db_path,
        map_path=map_path,
        lidar_pc_token=lidar_pc_token,
        candidates=candidates,
        causal_input=causal_input,
        neighbor_predictions=neighbor_predictions,
        neighbor_valid_mask=neighbor_valid_mask,
    )
    return materialize_v26_same_tick_full_atom_bank_pair(
        identity=identity,
        candidates=candidates,
        signal_authority=signal_authority,
        actor_source_complete=True,
        scenario_reference=scenario_reference,
        **sources,
    )
