from __future__ import annotations

import time
from typing import Any

import numpy as np


LANE_HARD_VIOLATION_SUPPORT_LOGGING_SCHEMA_VERSION = (
    "dp_camp_lane_hard_violation_support_logging_v1"
)

LANE_HARD_VIOLATION_SUPPORT_FIELD_NAMES = (
    "candidate_route_lateral_error_profile_m",
    "candidate_route_corridor_half_width_profile_m",
    "candidate_route_heading_error_profile_rad",
    "candidate_lateral_error_rate_profile_mps",
)

LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES = (
    "route_lateral_envelope_excess_v1",
    "route_lateral_margin_deficit_vs_top1_v1",
    "route_heading_divergence_excess_vs_top1_v1",
    "lateral_error_rate_excess_v1",
    "lateral_divergence_growth_v1",
    "lane_hard_violation_support_conflict_v1",
)

LANE_HARD_VIOLATION_SUPPORT_LATENCY_KEYS = (
    "latency_ms_lane_hard_violation_support_logging",
    "latency_ms_lane_hard_violation_projection",
    "latency_ms_lane_hard_violation_heading",
    "latency_ms_lane_hard_violation_rate",
    "latency_ms_lane_hard_violation_atom_compute",
    "latency_ms_lane_hard_violation_payload_serialization",
)


def build_lane_hard_violation_support_logging_payload(
    *,
    candidates: np.ndarray,
    route_centerline_ego: np.ndarray,
    support_steps: int,
    dt_s: float = 0.1,
    corridor_half_width_m: float | np.ndarray = 1.75,
    lateral_error_rate_budget_mps: float = 1.0,
) -> dict[str, Any]:
    """Build default-off lane/hard-violation diagnostics from current candidates.

    The function accepts only current-tick candidate geometry, route geometry,
    and explicit corridor/budget parameters. It does not accept closed-loop
    outcomes, tracker execution state, or simulator future state.
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
    if float(dt_s) <= 0.0 or not np.isfinite(float(dt_s)):
        raise ValueError("dt_s must be finite and positive.")
    if float(lateral_error_rate_budget_mps) < 0.0 or not np.isfinite(
        float(lateral_error_rate_budget_mps)
    ):
        raise ValueError("lateral_error_rate_budget_mps must be finite and nonnegative.")

    horizon = min(max(int(support_steps), 2), int(trajectories.shape[1]))
    xy = trajectories[:, :horizon, :2]
    route_xy = route[:, :2]
    if not np.all(np.isfinite(xy)) or not np.all(np.isfinite(route_xy)):
        raise ValueError("candidate and route coordinates must be finite.")

    projection_start = time.perf_counter()
    projection = _project_to_route(xy, route_xy)
    lateral_error = projection["signed_lateral_error_m"]
    corridor = _corridor_half_width_profile(
        corridor_half_width_m,
        candidate_shape=lateral_error.shape,
        segment_indices=projection["segment_indices"],
        route_point_count=route_xy.shape[0],
    )
    projection_done = time.perf_counter()

    heading_start = time.perf_counter()
    candidate_heading = _candidate_heading_profile(xy)
    route_heading = projection["route_heading_rad"]
    heading_error = np.abs(_wrap_to_pi(candidate_heading - route_heading))
    heading_done = time.perf_counter()

    rate_start = time.perf_counter()
    lateral_error_rate = np.diff(lateral_error, axis=1) / float(dt_s)
    rate_done = time.perf_counter()

    atom_start = time.perf_counter()
    atoms = _lane_hard_violation_support_atoms(
        lateral_error=lateral_error,
        corridor_half_width=corridor,
        heading_error=heading_error,
        lateral_error_rate=lateral_error_rate,
        lateral_error_rate_budget_mps=float(lateral_error_rate_budget_mps),
    )
    atom_done = time.perf_counter()

    fields = {
        "candidate_route_lateral_error_profile_m": lateral_error,
        "candidate_route_corridor_half_width_profile_m": corridor,
        "candidate_route_heading_error_profile_rad": heading_error,
        "candidate_lateral_error_rate_profile_mps": lateral_error_rate,
    }
    finite_checks = {
        name: bool(np.all(np.isfinite(value)))
        for name, value in fields.items()
    }
    finite_checks["lane_hard_violation_support_atoms"] = bool(
        np.all(np.isfinite(atoms))
    )
    finite_checks["lane_hard_violation_support_atoms_nonnegative"] = bool(
        np.all(atoms >= -1e-12)
    )

    serialization_start = time.perf_counter()
    field_lists = {
        name: np.asarray(value, dtype=np.float64).tolist()
        for name, value in fields.items()
    }
    atom_list = atoms.tolist()
    serialization_done = time.perf_counter()

    latency_ms = (serialization_done - start) * 1000.0
    latency_breakdown_ms = {
        "latency_ms_lane_hard_violation_support_logging": float(latency_ms),
        "latency_ms_lane_hard_violation_projection": (
            projection_done - projection_start
        )
        * 1000.0,
        "latency_ms_lane_hard_violation_heading": (
            heading_done - heading_start
        )
        * 1000.0,
        "latency_ms_lane_hard_violation_rate": (rate_done - rate_start)
        * 1000.0,
        "latency_ms_lane_hard_violation_atom_compute": (
            atom_done - atom_start
        )
        * 1000.0,
        "latency_ms_lane_hard_violation_payload_serialization": (
            serialization_done - serialization_start
        )
        * 1000.0,
    }
    return {
        "schema_version": LANE_HARD_VIOLATION_SUPPORT_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "definition": (
            "current-tick lane/hard-violation support fields and nonnegative "
            "candidate atom coefficients computed from fixed DP candidates, "
            "current route geometry, and explicit corridor parameters"
        ),
        "candidate_count": int(trajectories.shape[0]),
        "horizons": {
            "support_steps": int(horizon),
            "dt_s": float(dt_s),
        },
        "budgets": {
            "lateral_error_rate_budget_mps": float(lateral_error_rate_budget_mps),
        },
        "field_shapes": {
            name: list(np.asarray(value).shape)
            for name, value in fields.items()
        },
        "finite_checks": finite_checks,
        "latency_ms": latency_breakdown_ms,
        **field_lists,
        "lane_hard_violation_support_atom_names": list(
            LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES
        ),
        "lane_hard_violation_support_atoms": atom_list,
        "math_boundary": (
            "Lane/hard-violation support atoms are fixed finite-candidate "
            "nonnegative coefficients. CAMP score remains affine in weights: "
            "score_k(w)=a_k^T w. No global convexity over trajectory "
            "coordinates and no classical Benders claim is made."
        ),
        "classical_benders_claim": False,
    }


def _project_to_route(candidates_xy: np.ndarray, route_xy: np.ndarray) -> dict[str, np.ndarray]:
    route_segments = route_xy[1:] - route_xy[:-1]
    segment_lengths = np.linalg.norm(route_segments, axis=1)
    valid = segment_lengths > 1e-12
    if not np.any(valid):
        raise ValueError("route contains no non-degenerate segments.")
    starts = route_xy[:-1][valid]
    segments = route_segments[valid]
    lengths = segment_lengths[valid]
    valid_indices = np.nonzero(valid)[0]
    unit_segments = segments / lengths[:, np.newaxis]

    points = np.asarray(candidates_xy, dtype=np.float64).reshape(-1, 2)
    rel = points[:, np.newaxis, :] - starts[np.newaxis, :, :]
    t = np.sum(rel * segments[np.newaxis, :, :], axis=2) / (
        lengths[np.newaxis, :] ** 2
    )
    t = np.clip(t, 0.0, 1.0)
    projections = starts[np.newaxis, :, :] + t[:, :, np.newaxis] * segments[
        np.newaxis, :, :
    ]
    distances = np.linalg.norm(points[:, np.newaxis, :] - projections, axis=2)
    best = np.argmin(distances, axis=1)
    row_indices = np.arange(points.shape[0])
    best_projection = projections[row_indices, best]
    best_unit = unit_segments[best]
    signed_lateral = _cross2d(best_unit, points - best_projection)
    heading = np.arctan2(best_unit[:, 1], best_unit[:, 0])
    candidate_shape = candidates_xy.shape[:2]
    return {
        "signed_lateral_error_m": signed_lateral.reshape(candidate_shape),
        "route_heading_rad": heading.reshape(candidate_shape),
        "segment_indices": valid_indices[best].reshape(candidate_shape),
    }


def _corridor_half_width_profile(
    corridor_half_width_m: float | np.ndarray,
    *,
    candidate_shape: tuple[int, int],
    segment_indices: np.ndarray,
    route_point_count: int,
) -> np.ndarray:
    width = np.asarray(corridor_half_width_m, dtype=np.float64)
    if width.ndim == 0:
        value = float(width)
        if value <= 0.0 or not np.isfinite(value):
            raise ValueError("corridor_half_width_m must be finite and positive.")
        return np.full(candidate_shape, value, dtype=np.float64)
    if not np.all(np.isfinite(width)) or np.any(width <= 0.0):
        raise ValueError("corridor_half_width_m values must be finite and positive.")
    if width.shape == candidate_shape:
        return width.astype(np.float64, copy=True)
    if width.ndim == 1 and width.shape[0] == route_point_count - 1:
        return width[np.asarray(segment_indices, dtype=np.int64)]
    if width.ndim == 1 and width.shape[0] == route_point_count:
        per_segment = 0.5 * (width[:-1] + width[1:])
        return per_segment[np.asarray(segment_indices, dtype=np.int64)]
    raise ValueError(
        "corridor_half_width_m must be scalar, [K,H], [N-1], or [N]."
    )


def _candidate_heading_profile(candidates_xy: np.ndarray) -> np.ndarray:
    deltas = np.diff(candidates_xy, axis=1)
    headings = np.arctan2(deltas[:, :, 1], deltas[:, :, 0])
    if headings.shape[1] == 0:
        return np.zeros(candidates_xy.shape[:2], dtype=np.float64)
    return np.concatenate([headings, headings[:, -1:]], axis=1)


def _lane_hard_violation_support_atoms(
    *,
    lateral_error: np.ndarray,
    corridor_half_width: np.ndarray,
    heading_error: np.ndarray,
    lateral_error_rate: np.ndarray,
    lateral_error_rate_budget_mps: float,
) -> np.ndarray:
    abs_lateral_error = np.abs(lateral_error)
    lateral_excess_profile = np.maximum(abs_lateral_error - corridor_half_width, 0.0)
    route_lateral_envelope_excess = np.max(lateral_excess_profile, axis=1)
    lateral_margin = np.min(corridor_half_width - abs_lateral_error, axis=1)
    route_lateral_margin_deficit = np.maximum(lateral_margin[0] - lateral_margin, 0.0)
    max_heading = np.max(heading_error, axis=1)
    route_heading_divergence_excess = np.maximum(max_heading - max_heading[0], 0.0)
    max_abs_lateral_rate = np.max(np.abs(lateral_error_rate), axis=1)
    lateral_error_rate_excess = np.maximum(
        max_abs_lateral_rate - float(lateral_error_rate_budget_mps),
        0.0,
    )
    lateral_growth = np.max(
        np.maximum(abs_lateral_error[:, 1:] - abs_lateral_error[:, :-1], 0.0),
        axis=1,
    )
    lateral_divergence_growth = lateral_growth * max_abs_lateral_rate
    lane_hard_violation_support_conflict = (
        route_lateral_envelope_excess * route_heading_divergence_excess
    )
    atoms = np.stack(
        [
            route_lateral_envelope_excess,
            route_lateral_margin_deficit,
            route_heading_divergence_excess,
            lateral_error_rate_excess,
            lateral_divergence_growth,
            lane_hard_violation_support_conflict,
        ],
        axis=1,
    )
    return np.maximum(atoms, 0.0)


def _wrap_to_pi(angle: np.ndarray) -> np.ndarray:
    return (angle + np.pi) % (2.0 * np.pi) - np.pi


def _cross2d(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
