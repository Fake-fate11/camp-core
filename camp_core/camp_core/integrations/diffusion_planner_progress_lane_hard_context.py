from __future__ import annotations

import time
from typing import Any

import numpy as np

from camp_core.integrations.diffusion_planner_lane_hard_violation_support import (
    _candidate_heading_profile,
    _corridor_half_width_profile,
    _project_to_route,
    _wrap_to_pi,
)
from camp_core.integrations.diffusion_planner_progress_support import (
    _route_progress_profiles,
    _speed_profiles,
)


PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION = (
    "dp_camp_progress_lane_hard_context_logging_v1"
)

PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES = (
    "route_curvature_context_abs_radpm",
    "candidate_lateral_error_rate_profile_mps",
    "candidate_speed_profile_mps",
    "candidate_route_progress_delta_profile_m",
    "candidate_route_corridor_margin_profile_m",
    "candidate_route_heading_error_profile_rad",
)

PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES = (
    "curvature_conditioned_lateral_rate_excess_v1",
    "corridor_margin_exhaustion_v1",
    "heading_curvature_residual_v1",
    "lane_progress_coherence_excess_v1",
)

PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS = (
    "latency_ms_progress_lane_hard_context_logging",
    "latency_ms_progress_lane_hard_context_projection",
    "latency_ms_progress_lane_hard_context_route_curvature",
    "latency_ms_progress_lane_hard_context_kinematics",
    "latency_ms_progress_lane_hard_context_atom_compute",
    "latency_ms_progress_lane_hard_context_payload_serialization",
)


def build_progress_lane_hard_context_logging_payload(
    *,
    candidates: np.ndarray,
    route_centerline_ego: np.ndarray,
    support_steps: int,
    dt_s: float = 0.1,
    corridor_half_width_m: float | np.ndarray = 1.75,
    curvature_lateral_rate_gain: float = 1.0,
    lateral_rate_margin_mps: float = 0.0,
    corridor_safety_margin_m: float = 0.25,
    heading_curvature_gain: float = 1.0,
    heading_margin_rad: float = 0.0,
    progress_lateral_rate_gain: float = 1.0,
    progress_curvature_gain: float = 1.0,
) -> dict[str, Any]:
    """Build default-off progress+lane/hard context diagnostics.

    The function accepts only current-tick candidate geometry, route geometry,
    and explicit budget/gain parameters. It does not accept closed-loop
    outcomes, tracker execution state, or simulator future state.
    """
    start = time.perf_counter()
    trajectories = np.asarray(candidates, dtype=np.float64)
    route = np.asarray(route_centerline_ego, dtype=np.float64)
    _validate_inputs(
        trajectories=trajectories,
        route=route,
        dt_s=dt_s,
        curvature_lateral_rate_gain=curvature_lateral_rate_gain,
        lateral_rate_margin_mps=lateral_rate_margin_mps,
        corridor_safety_margin_m=corridor_safety_margin_m,
        heading_curvature_gain=heading_curvature_gain,
        heading_margin_rad=heading_margin_rad,
        progress_lateral_rate_gain=progress_lateral_rate_gain,
        progress_curvature_gain=progress_curvature_gain,
    )

    horizon = min(max(int(support_steps), 2), int(trajectories.shape[1]))
    xy = trajectories[:, :horizon, :2]
    route_xy = route[:, :2]

    projection_start = time.perf_counter()
    projection = _project_to_route(xy, route_xy)
    lateral_error = projection["signed_lateral_error_m"]
    corridor_half_width = _corridor_half_width_profile(
        corridor_half_width_m,
        candidate_shape=lateral_error.shape,
        segment_indices=projection["segment_indices"],
        route_point_count=route_xy.shape[0],
    )
    route_progress = _route_progress_profiles(xy, route_xy)
    projection_done = time.perf_counter()

    curvature_start = time.perf_counter()
    route_curvature = _route_curvature_context_abs_radpm(route_xy, horizon)
    curvature_done = time.perf_counter()

    kinematics_start = time.perf_counter()
    speed = _speed_profiles(xy, float(dt_s))
    route_progress_delta = np.diff(route_progress, axis=1)
    lateral_error_rate = np.diff(lateral_error, axis=1) / float(dt_s)
    corridor_margin = corridor_half_width - np.abs(lateral_error)
    candidate_heading = _candidate_heading_profile(xy)
    route_heading = projection["route_heading_rad"]
    heading_error = np.abs(_wrap_to_pi(candidate_heading - route_heading))
    kinematics_done = time.perf_counter()

    atom_start = time.perf_counter()
    atoms = _progress_lane_hard_context_atoms(
        route_curvature_context_abs_radpm=route_curvature,
        lateral_error_rate=lateral_error_rate,
        speed=speed,
        route_progress_delta=route_progress_delta,
        corridor_margin=corridor_margin,
        heading_error=heading_error,
        curvature_lateral_rate_gain=float(curvature_lateral_rate_gain),
        lateral_rate_margin_mps=float(lateral_rate_margin_mps),
        corridor_safety_margin_m=float(corridor_safety_margin_m),
        heading_curvature_gain=float(heading_curvature_gain),
        heading_margin_rad=float(heading_margin_rad),
        progress_lateral_rate_gain=float(progress_lateral_rate_gain),
        progress_curvature_gain=float(progress_curvature_gain),
    )
    atom_done = time.perf_counter()

    fields = {
        "route_curvature_context_abs_radpm": route_curvature,
        "candidate_lateral_error_rate_profile_mps": lateral_error_rate,
        "candidate_speed_profile_mps": speed,
        "candidate_route_progress_delta_profile_m": route_progress_delta,
        "candidate_route_corridor_margin_profile_m": corridor_margin,
        "candidate_route_heading_error_profile_rad": heading_error,
    }
    finite_checks = {
        name: bool(np.all(np.isfinite(value)))
        for name, value in fields.items()
    }
    finite_checks["progress_lane_hard_context_atoms"] = bool(
        np.all(np.isfinite(atoms))
    )
    finite_checks["progress_lane_hard_context_atoms_nonnegative"] = bool(
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
        "latency_ms_progress_lane_hard_context_logging": float(latency_ms),
        "latency_ms_progress_lane_hard_context_projection": (
            projection_done - projection_start
        )
        * 1000.0,
        "latency_ms_progress_lane_hard_context_route_curvature": (
            curvature_done - curvature_start
        )
        * 1000.0,
        "latency_ms_progress_lane_hard_context_kinematics": (
            kinematics_done - kinematics_start
        )
        * 1000.0,
        "latency_ms_progress_lane_hard_context_atom_compute": (
            atom_done - atom_start
        )
        * 1000.0,
        "latency_ms_progress_lane_hard_context_payload_serialization": (
            serialization_done - serialization_start
        )
        * 1000.0,
    }
    return {
        "schema_version": PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "definition": (
            "current-tick progress+lane/hard context fields and nonnegative "
            "candidate atom coefficients computed from fixed DP candidates, "
            "current route geometry, and explicit route-corridor parameters"
        ),
        "candidate_count": int(trajectories.shape[0]),
        "horizons": {
            "support_steps": int(horizon),
            "dt_s": float(dt_s),
        },
        "budgets": {
            "curvature_lateral_rate_gain": float(curvature_lateral_rate_gain),
            "lateral_rate_margin_mps": float(lateral_rate_margin_mps),
            "corridor_safety_margin_m": float(corridor_safety_margin_m),
            "heading_curvature_gain": float(heading_curvature_gain),
            "heading_margin_rad": float(heading_margin_rad),
            "progress_lateral_rate_gain": float(progress_lateral_rate_gain),
            "progress_curvature_gain": float(progress_curvature_gain),
        },
        "field_shapes": {
            name: list(np.asarray(value).shape)
            for name, value in fields.items()
        },
        "finite_checks": finite_checks,
        "latency_ms": latency_breakdown_ms,
        **field_lists,
        "progress_lane_hard_context_atom_names": list(
            PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES
        ),
        "progress_lane_hard_context_atoms": atom_list,
        "math_boundary": (
            "Progress+lane/hard context atoms are fixed finite-candidate "
            "nonnegative coefficients. CAMP score remains affine in weights: "
            "score_k(w)=a_k^T w. No global convexity over trajectory "
            "coordinates and no classical Benders claim is made."
        ),
        "classical_benders_claim": False,
    }


def _validate_inputs(
    *,
    trajectories: np.ndarray,
    route: np.ndarray,
    dt_s: float,
    curvature_lateral_rate_gain: float,
    lateral_rate_margin_mps: float,
    corridor_safety_margin_m: float,
    heading_curvature_gain: float,
    heading_margin_rad: float,
    progress_lateral_rate_gain: float,
    progress_curvature_gain: float,
) -> None:
    if trajectories.ndim != 3 or trajectories.shape[0] < 1 or trajectories.shape[1] < 2:
        raise ValueError("candidates must have shape [K,T,>=2].")
    if trajectories.shape[2] < 2:
        raise ValueError("candidates must contain x/y coordinates.")
    if route.ndim != 2 or route.shape[0] < 2 or route.shape[1] < 2:
        raise ValueError("route_centerline_ego must have shape [N,>=2] with N>=2.")
    if not np.all(np.isfinite(trajectories[:, :, :2])) or not np.all(
        np.isfinite(route[:, :2])
    ):
        raise ValueError("candidate and route coordinates must be finite.")
    if float(dt_s) <= 0.0 or not np.isfinite(float(dt_s)):
        raise ValueError("dt_s must be finite and positive.")
    nonnegative_values = {
        "curvature_lateral_rate_gain": curvature_lateral_rate_gain,
        "lateral_rate_margin_mps": lateral_rate_margin_mps,
        "corridor_safety_margin_m": corridor_safety_margin_m,
        "heading_curvature_gain": heading_curvature_gain,
        "heading_margin_rad": heading_margin_rad,
        "progress_lateral_rate_gain": progress_lateral_rate_gain,
        "progress_curvature_gain": progress_curvature_gain,
    }
    for name, value in nonnegative_values.items():
        scalar = float(value)
        if scalar < 0.0 or not np.isfinite(scalar):
            raise ValueError(f"{name} must be finite and nonnegative.")


def _route_curvature_context_abs_radpm(
    route_xy: np.ndarray,
    horizon: int,
) -> np.ndarray:
    route = np.asarray(route_xy, dtype=np.float64)
    segments = np.diff(route[:, :2], axis=0)
    segment_lengths = np.linalg.norm(segments, axis=1)
    valid = segment_lengths > 1e-12
    if not np.any(valid):
        raise ValueError("route contains no non-degenerate segments.")
    headings = np.arctan2(segments[:, 1], segments[:, 0])
    transition = np.abs(_wrap_to_pi(np.diff(headings)))
    if transition.size == 0:
        transition_curvature = np.zeros(0, dtype=np.float64)
    else:
        denom = 0.5 * (segment_lengths[:-1] + segment_lengths[1:])
        denom = np.maximum(denom, 1e-12)
        transition_curvature = transition / denom
    interval_count = int(horizon) - 1
    result = np.zeros(interval_count, dtype=np.float64)
    if transition_curvature.size:
        usable = min(interval_count - 1, transition_curvature.size)
        if usable > 0:
            result[1 : 1 + usable] = transition_curvature[:usable]
        if 1 + usable < interval_count:
            result[1 + usable :] = transition_curvature[-1]
    return result


def _progress_lane_hard_context_atoms(
    *,
    route_curvature_context_abs_radpm: np.ndarray,
    lateral_error_rate: np.ndarray,
    speed: np.ndarray,
    route_progress_delta: np.ndarray,
    corridor_margin: np.ndarray,
    heading_error: np.ndarray,
    curvature_lateral_rate_gain: float,
    lateral_rate_margin_mps: float,
    corridor_safety_margin_m: float,
    heading_curvature_gain: float,
    heading_margin_rad: float,
    progress_lateral_rate_gain: float,
    progress_curvature_gain: float,
) -> np.ndarray:
    curvature = np.asarray(route_curvature_context_abs_radpm, dtype=np.float64).reshape(
        1, -1
    )
    rate_abs = np.abs(np.asarray(lateral_error_rate, dtype=np.float64))
    speed = np.asarray(speed, dtype=np.float64)
    progress_delta = np.asarray(route_progress_delta, dtype=np.float64)
    if rate_abs.shape != speed.shape or rate_abs.shape != progress_delta.shape:
        raise ValueError("rate, speed, and progress-delta profiles must match.")
    if curvature.shape[1] != rate_abs.shape[1]:
        raise ValueError("route curvature context must match support intervals.")

    curvature_rate_allowance = (
        float(curvature_lateral_rate_gain) * curvature * np.maximum(speed, 0.0)
    )
    curvature_conditioned_lateral_rate_excess = np.max(
        np.maximum(rate_abs - curvature_rate_allowance - float(lateral_rate_margin_mps), 0.0),
        axis=1,
    )
    corridor_margin_exhaustion = np.max(
        np.maximum(float(corridor_safety_margin_m) - corridor_margin, 0.0),
        axis=1,
    )
    heading_interval = np.abs(np.asarray(heading_error, dtype=np.float64)[:, :-1])
    heading_curvature_residual = np.max(
        np.maximum(
            heading_interval
            - float(heading_curvature_gain) * curvature
            - float(heading_margin_rad),
            0.0,
        ),
        axis=1,
    )
    lane_progress_coherence_excess = np.max(
        np.maximum(
            rate_abs
            - float(progress_lateral_rate_gain) * np.maximum(progress_delta, 0.0)
            - float(progress_curvature_gain) * curvature * np.maximum(speed, 0.0),
            0.0,
        ),
        axis=1,
    )
    atoms = np.stack(
        [
            curvature_conditioned_lateral_rate_excess,
            corridor_margin_exhaustion,
            heading_curvature_residual,
            lane_progress_coherence_excess,
        ],
        axis=1,
    )
    return np.maximum(atoms, 0.0)
