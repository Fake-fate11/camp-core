from __future__ import annotations

import time
from typing import Any

import numpy as np

from camp_core.integrations.diffusion_planner_lane_hard_violation_support import (
    _project_to_route,
)
from camp_core.integrations.diffusion_planner_progress_support import (
    _route_progress_profiles,
    _speed_profiles,
)


EXTERNAL_CONTEXT_PAYLOAD_SCHEMA_VERSION = "dp_camp_external_context_payload_v1"

EXTERNAL_CONTEXT_PAYLOAD_FIELD_NAMES = (
    "candidate_first_signal_arrival_time_s",
    "candidate_signal_phase_change_margin_s",
    "candidate_right_of_way_blocked_indicator",
    "candidate_route_speed_limit_min_mps",
    "candidate_speed_limit_excess_integral_mps",
    "candidate_speed_limit_available_fraction",
)

EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS = (
    "latency_ms_external_context_payload",
    "latency_ms_external_context_traffic_signal_payload",
    "latency_ms_external_context_route_speed_payload",
    "latency_ms_external_context_payload_serialization",
)

EXTERNAL_CONTEXT_PAYLOAD_ATOM_CANDIDATE_NAMES = (
    "signal_arrival_time_cost_v1",
    "signal_phase_margin_violation_v1",
    "right_of_way_blocked_indicator_v1",
    "route_speed_limit_excess_integral_v1",
    "route_speed_limit_missing_context_v1",
)


def build_external_context_payload(
    *,
    candidates: np.ndarray,
    route_centerline_ego: np.ndarray | None,
    support_steps: int,
    dt_s: float = 0.1,
    signal_context: dict[str, Any] | None = None,
    route_speed_limit_mps: Any = None,
    route_has_speed_limit: Any = None,
) -> dict[str, Any]:
    """Build default-off current-tick traffic/speed context diagnostics.

    The function accepts only fixed DP candidates and explicit current-tick
    context. It does not read closed-loop outcomes, mutate CAMP atoms, call DP,
    or change selection.
    """
    start = time.perf_counter()
    trajectories = np.asarray(candidates, dtype=np.float64)
    candidate_count = _validate_candidates(trajectories)
    horizon = min(max(int(support_steps), 2), int(trajectories.shape[1]))
    dt = _validate_dt(dt_s)
    xy = trajectories[:, :horizon, :2]
    route = _optional_route(route_centerline_ego)

    fields: dict[str, Any] = {
        name: None for name in EXTERNAL_CONTEXT_PAYLOAD_FIELD_NAMES
    }
    field_shapes: dict[str, list[int] | None] = {
        name: None for name in EXTERNAL_CONTEXT_PAYLOAD_FIELD_NAMES
    }
    finite_checks: dict[str, bool] = {
        "payload_valid": True,
        "candidate_count_matches": True,
        "traffic_signal_context_valid_or_absent": True,
        "route_speed_context_valid_or_absent": True,
        "candidate_first_signal_arrival_time_s_finite": True,
        "candidate_signal_phase_change_margin_s_finite": True,
        "candidate_right_of_way_blocked_indicator_finite": True,
        "candidate_right_of_way_blocked_indicator_binary": True,
        "candidate_route_speed_limit_min_mps_finite": True,
        "candidate_route_speed_limit_min_mps_nonnegative": True,
        "candidate_speed_limit_excess_integral_mps_finite": True,
        "candidate_speed_limit_excess_integral_mps_nonnegative": True,
        "candidate_speed_limit_available_fraction_finite": True,
        "candidate_speed_limit_available_fraction_unit_interval": True,
    }

    traffic_start = time.perf_counter()
    traffic_available = False
    traffic_reason = "signal_context_absent"
    if route is not None and signal_context is not None:
        (
            traffic_available,
            traffic_reason,
            traffic_fields,
            traffic_shapes,
            traffic_checks,
        ) = _traffic_signal_fields(
            xy=xy,
            route_xy=route[:, :2],
            dt_s=dt,
            signal_context=signal_context,
            candidate_count=candidate_count,
        )
        fields.update(traffic_fields)
        field_shapes.update(traffic_shapes)
        finite_checks.update(traffic_checks)
    elif route is None and signal_context is not None:
        traffic_reason = "route_centerline_absent_for_signal_context"
        finite_checks["traffic_signal_context_valid_or_absent"] = False
    traffic_done = time.perf_counter()

    route_speed_start = time.perf_counter()
    route_speed_available = False
    route_speed_reason = "route_speed_context_absent"
    if route is not None and route_speed_limit_mps is not None:
        (
            route_speed_available,
            route_speed_reason,
            route_speed_fields,
            route_speed_shapes,
            route_speed_checks,
        ) = _route_speed_fields(
            xy=xy,
            route_xy=route[:, :2],
            dt_s=dt,
            route_speed_limit_mps=route_speed_limit_mps,
            route_has_speed_limit=route_has_speed_limit,
            candidate_count=candidate_count,
        )
        fields.update(route_speed_fields)
        field_shapes.update(route_speed_shapes)
        finite_checks.update(route_speed_checks)
    elif route is None and route_speed_limit_mps is not None:
        route_speed_reason = "route_centerline_absent_for_speed_context"
        finite_checks["route_speed_context_valid_or_absent"] = False
    route_speed_done = time.perf_counter()

    available = bool(traffic_available or route_speed_available)
    reasons = [
        reason
        for reason in (traffic_reason, route_speed_reason)
        if reason is not None
    ]
    if not available:
        finite_checks["payload_valid"] = False
    else:
        finite_checks["payload_valid"] = bool(all(finite_checks.values()))
        if not finite_checks["payload_valid"]:
            available = False
            reasons.append("derived_external_context_invalid")

    serialization_start = time.perf_counter()
    serialization_done = time.perf_counter()
    latency_ms = (serialization_done - start) * 1000.0
    latency = {
        "latency_ms_external_context_payload": float(latency_ms),
        "latency_ms_external_context_traffic_signal_payload": (
            traffic_done - traffic_start
        )
        * 1000.0,
        "latency_ms_external_context_route_speed_payload": (
            route_speed_done - route_speed_start
        )
        * 1000.0,
        "latency_ms_external_context_payload_serialization": (
            serialization_done - serialization_start
        )
        * 1000.0,
    }
    return {
        "schema_version": EXTERNAL_CONTEXT_PAYLOAD_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "deployed_atom_vector_change": False,
        "definition": (
            "default-off current-tick traffic-signal and route speed-limit "
            "context diagnostics computed from fixed DP candidates and explicit "
            "pre-selection context"
        ),
        "candidate_count": int(candidate_count),
        "horizons": {
            "support_steps": int(horizon),
            "dt_s": float(dt),
        },
        "available": bool(available),
        "availability_reason": None if available else ";".join(reasons),
        "traffic_signal_context_available": bool(traffic_available),
        "traffic_signal_context_reason": traffic_reason,
        "route_speed_context_available": bool(route_speed_available),
        "route_speed_context_reason": route_speed_reason,
        "field_shapes": field_shapes,
        "finite_checks": finite_checks,
        "latency_ms": latency,
        **fields,
        "atom_candidate_names": list(EXTERNAL_CONTEXT_PAYLOAD_ATOM_CANDIDATE_NAMES),
        "math_boundary": (
            "External-context payload fields are fixed current-tick "
            "finite-candidate coefficients or null fail-closed diagnostics. "
            "Right-of-way and speed-excess fields are nonnegative; phase margin "
            "requires signed-split or hinge atomization before use. If later "
            "promoted after a separate atom gate, CAMP score remains affine in "
            "weights: score_k(w)=a_k^T w, and the simplex/CVaR/L2 master "
            "remains convex. No trajectory-coordinate convexity or DP-side "
            "classical Benders claim is made."
        ),
        "classical_benders_claim": False,
    }


def _traffic_signal_fields(
    *,
    xy: np.ndarray,
    route_xy: np.ndarray,
    dt_s: float,
    signal_context: dict[str, Any],
    candidate_count: int,
) -> tuple[bool, str | None, dict[str, Any], dict[str, list[int] | None], dict[str, bool]]:
    signal_s = _signal_s_m(signal_context, route_xy)
    phase = str(signal_context.get("current_phase") or "").lower()
    blocked_phases = {
        str(value).lower()
        for value in signal_context.get("blocked_phases", ("red",))
    }
    phase_remaining = signal_context.get("phase_remaining_s")
    if signal_s is None:
        return _null_traffic("signal_position_unavailable")
    if phase not in {"red", "yellow", "green", "white", "none"}:
        return _null_traffic("signal_phase_invalid_or_absent")
    if phase_remaining is not None:
        phase_remaining = float(phase_remaining)
        if not np.isfinite(phase_remaining) or phase_remaining < 0.0:
            return _null_traffic("signal_phase_remaining_invalid")

    progress = _route_progress_profiles(xy, route_xy)
    reached = progress >= float(signal_s)
    arrival = np.full(candidate_count, np.nan, dtype=np.float64)
    blocked = np.zeros(candidate_count, dtype=np.float64)
    for idx in range(candidate_count):
        hits = np.flatnonzero(reached[idx])
        if hits.size:
            arrival[idx] = float(hits[0]) * dt_s
            blocked[idx] = 1.0 if phase in blocked_phases else 0.0
    margin = None
    if phase_remaining is not None:
        margin = np.where(np.isfinite(arrival), phase_remaining - arrival, np.nan)
    fields = {
        "candidate_first_signal_arrival_time_s": _nan_to_none_list(arrival),
        "candidate_signal_phase_change_margin_s": (
            None if margin is None else _nan_to_none_list(margin)
        ),
        "candidate_right_of_way_blocked_indicator": blocked.tolist(),
    }
    shapes = {
        "candidate_first_signal_arrival_time_s": [candidate_count],
        "candidate_signal_phase_change_margin_s": (
            None if margin is None else [candidate_count]
        ),
        "candidate_right_of_way_blocked_indicator": [candidate_count],
    }
    checks = {
        "candidate_first_signal_arrival_time_s_finite": bool(
            np.all(np.isfinite(arrival) | np.isnan(arrival))
        ),
        "candidate_signal_phase_change_margin_s_finite": (
            True if margin is None else bool(np.all(np.isfinite(margin) | np.isnan(margin)))
        ),
        "candidate_right_of_way_blocked_indicator_finite": bool(
            np.all(np.isfinite(blocked))
        ),
        "candidate_right_of_way_blocked_indicator_binary": bool(
            np.all((blocked == 0.0) | (blocked == 1.0))
        ),
    }
    return True, None, fields, shapes, checks


def _route_speed_fields(
    *,
    xy: np.ndarray,
    route_xy: np.ndarray,
    dt_s: float,
    route_speed_limit_mps: Any,
    route_has_speed_limit: Any,
    candidate_count: int,
) -> tuple[bool, str | None, dict[str, Any], dict[str, list[int] | None], dict[str, bool]]:
    if xy.shape[1] < 2:
        return _null_route_speed("candidate_horizon_too_short")
    step_xy = xy[:, :-1, :]
    projection = _project_to_route(step_xy, route_xy)
    speed = _speed_profiles(xy, dt_s)
    limits, has_limit = _speed_limit_profile(
        route_speed_limit_mps,
        route_has_speed_limit,
        segment_indices=projection["segment_indices"],
        route_point_count=route_xy.shape[0],
    )
    valid = has_limit & np.isfinite(limits) & (limits >= 0.0)
    min_limit = np.full(candidate_count, np.nan, dtype=np.float64)
    excess_integral = np.full(candidate_count, np.nan, dtype=np.float64)
    available_fraction = np.mean(valid, axis=1).astype(np.float64)
    for idx in range(candidate_count):
        if valid[idx].any():
            row_limits = limits[idx][valid[idx]]
            row_speed = speed[idx][valid[idx]]
            min_limit[idx] = float(np.min(row_limits))
            excess_integral[idx] = float(
                np.sum(np.maximum(row_speed - row_limits, 0.0)) * dt_s
            )
    fields = {
        "candidate_route_speed_limit_min_mps": _nan_to_none_list(min_limit),
        "candidate_speed_limit_excess_integral_mps": _nan_to_none_list(
            excess_integral
        ),
        "candidate_speed_limit_available_fraction": available_fraction.tolist(),
    }
    shapes = {
        "candidate_route_speed_limit_min_mps": [candidate_count],
        "candidate_speed_limit_excess_integral_mps": [candidate_count],
        "candidate_speed_limit_available_fraction": [candidate_count],
    }
    checks = {
        "candidate_route_speed_limit_min_mps_finite": bool(
            np.all(np.isfinite(min_limit) | np.isnan(min_limit))
        ),
        "candidate_route_speed_limit_min_mps_nonnegative": bool(
            np.all((min_limit >= 0.0) | np.isnan(min_limit))
        ),
        "candidate_speed_limit_excess_integral_mps_finite": bool(
            np.all(np.isfinite(excess_integral) | np.isnan(excess_integral))
        ),
        "candidate_speed_limit_excess_integral_mps_nonnegative": bool(
            np.all((excess_integral >= -1e-12) | np.isnan(excess_integral))
        ),
        "candidate_speed_limit_available_fraction_finite": bool(
            np.all(np.isfinite(available_fraction))
        ),
        "candidate_speed_limit_available_fraction_unit_interval": bool(
            np.all((available_fraction >= -1e-12) & (available_fraction <= 1.0 + 1e-12))
        ),
    }
    return bool(valid.any()), None if valid.any() else "route_speed_context_empty", fields, shapes, checks


def _speed_limit_profile(
    route_speed_limit_mps: Any,
    route_has_speed_limit: Any,
    *,
    segment_indices: np.ndarray,
    route_point_count: int,
) -> tuple[np.ndarray, np.ndarray]:
    shape = segment_indices.shape
    limits = np.asarray(route_speed_limit_mps, dtype=np.float64)
    if limits.ndim == 0:
        limit_profile = np.full(shape, float(limits), dtype=np.float64)
    else:
        flat = limits.reshape(-1)
        if flat.size == route_point_count:
            per_segment = 0.5 * (flat[:-1] + flat[1:])
        elif flat.size == route_point_count - 1:
            per_segment = flat
        else:
            raise ValueError(
                "route_speed_limit_mps must be scalar, [route_points], or [route_segments]."
            )
        limit_profile = per_segment[np.asarray(segment_indices, dtype=np.int64)]
    if route_has_speed_limit is None:
        has_profile = np.isfinite(limit_profile) & (limit_profile > 0.0)
    else:
        has = np.asarray(route_has_speed_limit, dtype=bool)
        if has.ndim == 0:
            has_profile = np.full(shape, bool(has), dtype=bool)
        else:
            flat_has = has.reshape(-1)
            if flat_has.size == route_point_count:
                per_segment_has = flat_has[:-1] | flat_has[1:]
            elif flat_has.size == route_point_count - 1:
                per_segment_has = flat_has
            else:
                raise ValueError(
                    "route_has_speed_limit must be scalar, [route_points], or [route_segments]."
                )
            has_profile = per_segment_has[np.asarray(segment_indices, dtype=np.int64)]
    return limit_profile, has_profile


def _signal_s_m(signal_context: dict[str, Any], route_xy: np.ndarray) -> float | None:
    if signal_context.get("signal_s_m") is not None:
        value = float(signal_context["signal_s_m"])
        return value if np.isfinite(value) and value >= 0.0 else None
    if signal_context.get("signal_distance_m") is not None:
        value = float(signal_context["signal_distance_m"])
        return value if np.isfinite(value) and value >= 0.0 else None
    if signal_context.get("signal_position_ego") is not None:
        point = np.asarray(signal_context["signal_position_ego"], dtype=np.float64).reshape(-1)
        if point.size < 2 or not np.all(np.isfinite(point[:2])):
            return None
        return float(_route_progress_profiles(point[:2].reshape(1, 1, 2), route_xy)[0, 0])
    return None


def _null_traffic(reason: str):
    fields = {
        "candidate_first_signal_arrival_time_s": None,
        "candidate_signal_phase_change_margin_s": None,
        "candidate_right_of_way_blocked_indicator": None,
    }
    shapes = {key: None for key in fields}
    checks = {"traffic_signal_context_valid_or_absent": False}
    return False, reason, fields, shapes, checks


def _null_route_speed(reason: str):
    fields = {
        "candidate_route_speed_limit_min_mps": None,
        "candidate_speed_limit_excess_integral_mps": None,
        "candidate_speed_limit_available_fraction": None,
    }
    shapes = {key: None for key in fields}
    checks = {"route_speed_context_valid_or_absent": False}
    return False, reason, fields, shapes, checks


def _optional_route(route_centerline_ego: np.ndarray | None) -> np.ndarray | None:
    if route_centerline_ego is None:
        return None
    route = np.asarray(route_centerline_ego, dtype=np.float64)
    if route.ndim != 2 or route.shape[0] < 2 or route.shape[1] < 2:
        raise ValueError("route_centerline_ego must have shape [N,>=2] with N>=2.")
    if not np.all(np.isfinite(route[:, :2])):
        raise ValueError("route_centerline_ego coordinates must be finite.")
    return route


def _validate_candidates(candidates: np.ndarray) -> int:
    if candidates.ndim != 3 or candidates.shape[0] < 1 or candidates.shape[1] < 2:
        raise ValueError("candidates must have shape [K,T,>=2].")
    if candidates.shape[2] < 2:
        raise ValueError("candidates must contain x/y coordinates.")
    if not np.all(np.isfinite(candidates[:, :, :2])):
        raise ValueError("candidate coordinates must be finite.")
    return int(candidates.shape[0])


def _validate_dt(dt_s: float) -> float:
    dt = float(dt_s)
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("dt_s must be finite and positive.")
    return dt


def _nan_to_none_list(values: np.ndarray) -> list[float | None]:
    return [None if not np.isfinite(value) else float(value) for value in values]
