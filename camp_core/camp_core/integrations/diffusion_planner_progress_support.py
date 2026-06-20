from __future__ import annotations

import time
from typing import Any

import numpy as np


PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION = "dp_camp_progress_support_logging_v1"

PROGRESS_SUPPORT_FIELD_NAMES = (
    "candidate_route_progress_s_profile_m",
    "candidate_plan_arc_length_profile_m",
    "candidate_speed_profile_mps",
    "candidate_route_remaining_m",
    "candidate_goal_alignment_progress_m",
)

PROGRESS_SUPPORT_ATOM_NAMES = (
    "route_progress_deficit_envelope_v1",
    "route_progress_regression_envelope_v1",
    "plan_arc_support_deficit_v1",
    "tail_speed_support_deficit_v1",
    "route_remaining_excess_vs_top1_v1",
    "goal_alignment_progress_deficit_v1",
    "low_speed_progress_conflict_v1",
)

PROGRESS_SUPPORT_LATENCY_KEYS = (
    "latency_ms_progress_support_logging",
    "latency_ms_progress_support_route_projection",
    "latency_ms_progress_support_plan_arc",
    "latency_ms_progress_support_speed_profile",
    "latency_ms_progress_support_route_remaining",
    "latency_ms_progress_support_goal_alignment",
    "latency_ms_progress_support_atom_compute",
    "latency_ms_progress_support_payload_serialization",
)

_ROUTE_PROJECTION_SEGMENT_CHUNK_SIZE = 256
_ROUTE_PROJECTION_MAX_INTERMEDIATE_ELEMENTS = 4_000_000


def build_progress_support_logging_payload(
    *,
    candidates: np.ndarray,
    route_centerline_ego: np.ndarray,
    support_steps: int,
    dt_s: float = 0.1,
) -> dict[str, Any]:
    """Build default-off progress-support diagnostics from current candidates.

    The function intentionally accepts only current-tick candidate geometry and
    route geometry. It does not accept closed-loop outcome labels or simulator
    execution state, which keeps the resulting fields runtime-eligible.
    """
    start = time.perf_counter()
    trajectories = np.asarray(candidates, dtype=np.float64)
    route = np.asarray(route_centerline_ego, dtype=np.float64)
    if trajectories.ndim != 3 or trajectories.shape[0] < 1 or trajectories.shape[1] < 2:
        raise ValueError("candidates must have shape [K,T,>=2].")
    if trajectories.shape[2] < 2:
        raise ValueError("candidates must contain x/y coordinates.")
    if route.ndim != 2 or route.shape[0] < 2 or route.shape[1] < 2:
        raise ValueError("route_centerline_ego must have shape [N,>=2] with N>=2.")
    if float(dt_s) <= 0.0:
        raise ValueError("dt_s must be positive.")

    horizon = min(max(int(support_steps), 2), int(trajectories.shape[1]))
    xy = trajectories[:, :horizon, :2]
    route_xy = route[:, :2]

    route_projection_start = time.perf_counter()
    route_progress = _route_progress_profiles(xy, route_xy)
    route_projection_done = time.perf_counter()
    plan_arc_start = time.perf_counter()
    plan_arc = _plan_arc_length_profiles(xy)
    plan_arc_done = time.perf_counter()
    speed_start = time.perf_counter()
    speed = _speed_profiles(xy, float(dt_s))
    speed_done = time.perf_counter()
    route_remaining_start = time.perf_counter()
    route_lengths = _route_cumulative_lengths(route_xy)
    route_total = float(route_lengths[-1])
    final_progress = route_progress[:, -1]
    route_remaining = np.maximum(route_total - final_progress, 0.0)
    route_remaining_done = time.perf_counter()
    goal_alignment_start = time.perf_counter()
    goal_alignment = _goal_alignment_progress(xy, route_xy)
    goal_alignment_done = time.perf_counter()
    atom_start = time.perf_counter()
    atoms = _progress_support_atoms(
        route_progress=route_progress,
        plan_arc=plan_arc,
        speed=speed,
        route_remaining=route_remaining,
        goal_alignment=goal_alignment,
    )
    atom_done = time.perf_counter()
    fields = {
        "candidate_route_progress_s_profile_m": route_progress,
        "candidate_plan_arc_length_profile_m": plan_arc,
        "candidate_speed_profile_mps": speed,
        "candidate_route_remaining_m": route_remaining,
        "candidate_goal_alignment_progress_m": goal_alignment,
    }
    finite_checks = {
        name: bool(np.all(np.isfinite(value)))
        for name, value in fields.items()
    }
    finite_checks["progress_support_atoms"] = bool(np.all(np.isfinite(atoms)))
    finite_checks["progress_support_atoms_nonnegative"] = bool(np.all(atoms >= -1e-12))
    serialization_start = time.perf_counter()
    field_lists = {
        name: np.asarray(value, dtype=np.float64).tolist()
        for name, value in fields.items()
    }
    atom_list = atoms.tolist()
    serialization_done = time.perf_counter()
    latency_ms = (serialization_done - start) * 1000.0
    latency_breakdown_ms = {
        "latency_ms_progress_support_logging": float(latency_ms),
        "latency_ms_progress_support_route_projection": (
            route_projection_done - route_projection_start
        )
        * 1000.0,
        "latency_ms_progress_support_plan_arc": (
            plan_arc_done - plan_arc_start
        )
        * 1000.0,
        "latency_ms_progress_support_speed_profile": (
            speed_done - speed_start
        )
        * 1000.0,
        "latency_ms_progress_support_route_remaining": (
            route_remaining_done - route_remaining_start
        )
        * 1000.0,
        "latency_ms_progress_support_goal_alignment": (
            goal_alignment_done - goal_alignment_start
        )
        * 1000.0,
        "latency_ms_progress_support_atom_compute": (
            atom_done - atom_start
        )
        * 1000.0,
        "latency_ms_progress_support_payload_serialization": (
            serialization_done - serialization_start
        )
        * 1000.0,
    }
    payload: dict[str, Any] = {
        "schema_version": PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "definition": (
            "current-tick progress-support fields and nonnegative candidate "
            "atom coefficients computed from fixed DP candidates and current route geometry"
        ),
        "candidate_count": int(trajectories.shape[0]),
        "horizons": {
            "support_steps": int(horizon),
            "dt_s": float(dt_s),
        },
        "field_shapes": {
            name: list(np.asarray(value).shape)
            for name, value in fields.items()
        },
        "finite_checks": finite_checks,
        "latency_ms": latency_breakdown_ms,
        **field_lists,
        "progress_support_atom_names": list(PROGRESS_SUPPORT_ATOM_NAMES),
        "progress_support_atoms": atom_list,
        "math_boundary": (
            "Progress-support atoms are fixed finite-candidate nonnegative "
            "coefficients. CAMP score remains affine in weights: score_k(w)=a_k^T w."
        ),
        "classical_benders_claim": False,
    }
    return payload


def _route_cumulative_lengths(route_xy: np.ndarray) -> np.ndarray:
    deltas = np.diff(route_xy, axis=0)
    lengths = np.linalg.norm(deltas, axis=1)
    return np.concatenate([[0.0], np.cumsum(lengths)])


def _route_progress_profiles(candidates_xy: np.ndarray, route_xy: np.ndarray) -> np.ndarray:
    try:
        profiles = _route_progress_profiles_chunked(
            candidates_xy,
            route_xy,
            segment_chunk_size=_ROUTE_PROJECTION_SEGMENT_CHUNK_SIZE,
            max_intermediate_elements=_ROUTE_PROJECTION_MAX_INTERMEDIATE_ELEMENTS,
        )
    except (MemoryError, ValueError, FloatingPointError):
        return _route_progress_profiles_reference(candidates_xy, route_xy)
    if profiles.shape != np.asarray(candidates_xy).shape[:2]:
        return _route_progress_profiles_reference(candidates_xy, route_xy)
    if not np.all(np.isfinite(profiles)):
        return _route_progress_profiles_reference(candidates_xy, route_xy)
    return profiles


def _route_progress_profiles_reference(
    candidates_xy: np.ndarray,
    route_xy: np.ndarray,
) -> np.ndarray:
    route_lengths = _route_cumulative_lengths(route_xy)
    segments = route_xy[1:] - route_xy[:-1]
    segment_lengths_sq = np.sum(segments * segments, axis=1)
    profiles = np.zeros(candidates_xy.shape[:2], dtype=np.float64)
    for cand_idx in range(candidates_xy.shape[0]):
        for step_idx in range(candidates_xy.shape[1]):
            point = candidates_xy[cand_idx, step_idx]
            best_distance = np.inf
            best_s = 0.0
            for seg_idx, segment in enumerate(segments):
                denom = float(segment_lengths_sq[seg_idx])
                if denom <= 1e-12:
                    continue
                rel = point - route_xy[seg_idx]
                t = float(np.clip(np.dot(rel, segment) / denom, 0.0, 1.0))
                projection = route_xy[seg_idx] + t * segment
                distance = float(np.linalg.norm(point - projection))
                if distance < best_distance:
                    best_distance = distance
                    best_s = float(route_lengths[seg_idx] + t * np.sqrt(denom))
            profiles[cand_idx, step_idx] = best_s
    return profiles


def _route_progress_profiles_chunked(
    candidates_xy: np.ndarray,
    route_xy: np.ndarray,
    *,
    segment_chunk_size: int = _ROUTE_PROJECTION_SEGMENT_CHUNK_SIZE,
    max_intermediate_elements: int = _ROUTE_PROJECTION_MAX_INTERMEDIATE_ELEMENTS,
) -> np.ndarray:
    points_by_candidate = np.asarray(candidates_xy, dtype=np.float64)
    route = np.asarray(route_xy, dtype=np.float64)
    if (
        points_by_candidate.ndim != 3
        or points_by_candidate.shape[0] < 1
        or points_by_candidate.shape[1] < 1
        or points_by_candidate.shape[2] < 2
    ):
        raise ValueError("candidates_xy must have shape [K,H,>=2].")
    if route.ndim != 2 or route.shape[0] < 2 or route.shape[1] < 2:
        raise ValueError("route_xy must have shape [N,>=2] with N>=2.")
    if segment_chunk_size < 1:
        raise ValueError("segment_chunk_size must be positive.")
    if max_intermediate_elements < 1:
        raise ValueError("max_intermediate_elements must be positive.")
    points = points_by_candidate[:, :, :2].reshape(-1, 2)
    route_xy_only = route[:, :2]
    if not np.all(np.isfinite(points)) or not np.all(np.isfinite(route_xy_only)):
        raise ValueError("route projection inputs must be finite.")

    route_lengths = _route_cumulative_lengths(route_xy_only)
    starts_all = route_xy_only[:-1]
    segments_all = route_xy_only[1:] - route_xy_only[:-1]
    segment_lengths_sq_all = np.sum(segments_all * segments_all, axis=1)
    valid_segments = segment_lengths_sq_all > 1e-12
    if not np.any(valid_segments):
        raise ValueError("route contains no non-degenerate segments.")

    point_count = int(points.shape[0])
    best_distance = np.full(point_count, np.inf, dtype=np.float64)
    best_s = np.zeros(point_count, dtype=np.float64)
    segment_count = int(segments_all.shape[0])
    for chunk_start in range(0, segment_count, int(segment_chunk_size)):
        chunk_end = min(chunk_start + int(segment_chunk_size), segment_count)
        valid = valid_segments[chunk_start:chunk_end]
        if not np.any(valid):
            continue
        if point_count * int(np.count_nonzero(valid)) > max_intermediate_elements:
            raise MemoryError("route projection chunk exceeds intermediate guard.")
        chunk_indices = np.arange(chunk_start, chunk_end, dtype=np.int64)[valid]
        starts = starts_all[chunk_indices]
        segments = segments_all[chunk_indices]
        denom = segment_lengths_sq_all[chunk_indices]
        relative = points[:, np.newaxis, :] - starts[np.newaxis, :, :]
        t = np.sum(relative * segments[np.newaxis, :, :], axis=2)
        t = np.clip(t / denom[np.newaxis, :], 0.0, 1.0)
        projections = starts[np.newaxis, :, :] + t[:, :, np.newaxis] * segments[
            np.newaxis, :, :
        ]
        distances = np.linalg.norm(points[:, np.newaxis, :] - projections, axis=2)
        chunk_best = np.argmin(distances, axis=1)
        row_indices = np.arange(point_count, dtype=np.int64)
        chunk_best_distance = distances[row_indices, chunk_best]
        better = chunk_best_distance < best_distance
        if not np.any(better):
            continue
        chunk_s = route_lengths[chunk_indices][np.newaxis, :] + t * np.sqrt(
            denom[np.newaxis, :]
        )
        best_distance[better] = chunk_best_distance[better]
        best_s[better] = chunk_s[row_indices[better], chunk_best[better]]
    return best_s.reshape(points_by_candidate.shape[:2])


def _plan_arc_length_profiles(candidates_xy: np.ndarray) -> np.ndarray:
    deltas = np.diff(candidates_xy, axis=1)
    lengths = np.linalg.norm(deltas, axis=2)
    return np.concatenate(
        [
            np.zeros((candidates_xy.shape[0], 1), dtype=np.float64),
            np.cumsum(lengths, axis=1),
        ],
        axis=1,
    )


def _speed_profiles(candidates_xy: np.ndarray, dt_s: float) -> np.ndarray:
    deltas = np.diff(candidates_xy, axis=1)
    return np.linalg.norm(deltas, axis=2) / float(dt_s)


def _goal_alignment_progress(candidates_xy: np.ndarray, route_xy: np.ndarray) -> np.ndarray:
    route_delta = route_xy[-1] - route_xy[0]
    norm = float(np.linalg.norm(route_delta))
    if norm <= 1e-12:
        tangent = np.asarray([1.0, 0.0], dtype=np.float64)
    else:
        tangent = route_delta / norm
    endpoints = candidates_xy[:, -1, :]
    return np.maximum(endpoints @ tangent, 0.0)


def _progress_support_atoms(
    *,
    route_progress: np.ndarray,
    plan_arc: np.ndarray,
    speed: np.ndarray,
    route_remaining: np.ndarray,
    goal_alignment: np.ndarray,
) -> np.ndarray:
    top1_route_progress = route_progress[0]
    route_progress_deficit = np.max(
        np.maximum(top1_route_progress.reshape(1, -1) - route_progress, 0.0),
        axis=1,
    )
    route_regression = np.max(
        np.maximum(route_progress[:, :-1] - route_progress[:, 1:], 0.0),
        axis=1,
    )
    plan_arc_deficit = np.maximum(plan_arc[0, -1] - plan_arc[:, -1], 0.0)
    tail_speed = speed[:, -1] if speed.shape[1] else np.zeros(speed.shape[0], dtype=np.float64)
    tail_speed_deficit = np.maximum(tail_speed[0] - tail_speed, 0.0)
    route_remaining_excess = np.maximum(route_remaining - route_remaining[0], 0.0)
    goal_alignment_deficit = np.maximum(goal_alignment[0] - goal_alignment, 0.0)
    low_speed_progress_conflict = route_progress_deficit * tail_speed_deficit
    atoms = np.stack(
        [
            route_progress_deficit,
            route_regression,
            plan_arc_deficit,
            tail_speed_deficit,
            route_remaining_excess,
            goal_alignment_deficit,
            low_speed_progress_conflict,
        ],
        axis=1,
    )
    return np.maximum(atoms, 0.0)
