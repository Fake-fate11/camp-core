from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

from camp_core.integrations.diffusion_planner import (
    CAMP_ATOM_NAMES,
    DP_CAMP_ATOM_NAMES,
    DP_CAMP_ATOM_NAMES_V8,
    DP_CAMP_ATOM_NAMES_V9,
    DP_CAMP_ATOM_NAMES_V10,
    _obb_center_and_radius,
    _obb_corners,
    _obb_distance,
    _red_route_points_from_lanes,
    compute_dp_prior_comfort_excess_costs,
    compute_lateral_comfort_shadow_costs,
    compute_red_stopping_margin_costs,
)
from camp_core.integrations.diffusion_planner_causal_materializer import (
    validate_causal_dp_input,
)


OBSERVABLE_FEASIBILITY_SCOPE = (
    "frozen_observable_32_dynamic_plus_5_static_only"
)
FULL_WINDOW_EXACT_SPEED = "full_window_exact_speed"
CANDIDATE_LOCAL_EXACT_SPEED = "candidate_local_exact_speed"
_SPEED_SOURCE_POLICIES = frozenset(
    {FULL_WINDOW_EXACT_SPEED, CANDIDATE_LOCAL_EXACT_SPEED}
)


@dataclass(frozen=True)
class AtomContract:
    name: str
    unit: str
    formula: str
    inputs: tuple[str, ...]
    decision_time_availability: str
    future_dependency: str
    nuscenes_availability: str
    test_evidence: tuple[str, ...]
    nonnegative: bool = True
    finite_required: bool = True
    depends_on_w: bool = False
    depends_on_rank: bool = False
    depends_on_selected_index: bool = False
    gt_future_allowed: bool = False
    holdout_label_allowed: bool = False
    candidate_index_dependency: str = "none"


_BASE_TEST = (
    "camp_core/tests/test_diffusion_planner_component_benchmark.py::"
    "test_profiled_atom_vector_matches_production_definition"
)
_AVAILABILITY_TEST = (
    "camp_core/tests/test_diffusion_planner_v17_causal_atom_availability.py::"
    "test_contract_table_is_canonical_causal_and_fail_closed"
)


def _contract(
    name: str,
    unit: str,
    formula: str,
    inputs: tuple[str, ...],
    availability: str,
    future_dependency: str,
    nuscenes: str,
    test: str,
    *,
    candidate_index_dependency: str = "none",
) -> AtomContract:
    return AtomContract(
        name=name,
        unit=unit,
        formula=formula,
        inputs=inputs,
        decision_time_availability=availability,
        future_dependency=future_dependency,
        nuscenes_availability=nuscenes,
        test_evidence=(test, _AVAILABILITY_TEST),
        candidate_index_dependency=candidate_index_dependency,
    )


CANONICAL_ATOM_CONTRACTS = (
    _contract(
        "jerk_early",
        "m^2/s^5",
        "dt * sum(||third_difference(candidate_xy)/dt^3||^2) over first third",
        ("fixed DP candidate_xy[K,80,2]", "dt=0.1 s"),
        "available after fixed DP produces causal K=8 candidates",
        "planned candidate horizon only; no observed or GT future",
        "available_from_fixed_dp_candidate_tensor",
        _BASE_TEST,
    ),
    _contract(
        "jerk_late",
        "m^2/s^5",
        "dt * sum(||third_difference(candidate_xy)/dt^3||^2) after first third",
        ("fixed DP candidate_xy[K,80,2]", "dt=0.1 s"),
        "available after fixed DP produces causal K=8 candidates",
        "planned candidate horizon only; no observed or GT future",
        "available_from_fixed_dp_candidate_tensor",
        _BASE_TEST,
    ),
    _contract(
        "jerk_full",
        "m^2/s^5",
        "dt * sum(||third_difference(candidate_xy)/dt^3||^2) over full horizon",
        ("fixed DP candidate_xy[K,80,2]", "dt=0.1 s"),
        "available after fixed DP produces causal K=8 candidates",
        "planned candidate horizon only; no observed or GT future",
        "available_from_fixed_dp_candidate_tensor",
        _BASE_TEST,
    ),
    _contract(
        "rms_acceleration",
        "m/s^2",
        "sqrt(mean(||second_difference(candidate_xy)/dt^2||^2))",
        ("fixed DP candidate_xy[K,80,2]", "dt=0.1 s"),
        "available after fixed DP produces causal K=8 candidates",
        "planned candidate horizon only; no observed or GT future",
        "available_from_fixed_dp_candidate_tensor",
        _BASE_TEST,
    ),
    *(
        _contract(
            f"speed_limit_margin_{str(margin).replace('.', '_')}",
            "m^2/s",
            f"dt * sum(max(speed_t - (route_limit_t - {margin}), 0)^2)",
            (
                "fixed DP candidate_xy[K,80,2]",
                "ordered current route",
                "actual route-segment speed_limit_mps",
                "dt=0.1 s",
            ),
            "requires a decision-time speed limit for each projected route segment",
            "planned candidate horizon plus current static route rule; no GT future",
            "unavailable:no speed or limit field exists in nuScenes map or metadata",
            _BASE_TEST,
        )
        for margin in (0.0, 0.5, 1.0)
    ),
    _contract(
        "lane_deviation",
        "m^2*s",
        "dt * sum(max(abs(projected_lateral_offset) - lane_half_width, 0)^2)",
        (
            "fixed DP candidate_xy[K,80,2]",
            "ordered current route centerline",
            "explicit left/right boundary offsets",
        ),
        "requires a decision-time topology route and measured lane boundaries",
        "planned candidate horizon plus current static map; no GT future",
        "conditional:nuScenes has geometry but no mission route",
        _BASE_TEST,
    ),
    _contract(
        "clearance",
        "m^2*s",
        "dt * sum(max(safety_radius + margin - minimum_obstacle_distance_t, 0)^2)",
        (
            "fixed DP candidate_xy[K,80,2]",
            "candidate-specific fixed-DP neighbor predictions[K,M,80,D]",
            "current static obstacles",
        ),
        "requires candidate-specific neighbor predictions from the same fixed DP call",
        "fixed-DP predicted neighbor horizon only; GT neighbor future forbidden",
        "conditional:requires new causal fixed-DP neighbor prediction export",
        "camp_core/tests/test_diffusion_planner_integration.py::"
        "test_vectorized_atom_clearance_matches_hinge_definition",
    ),
    _contract(
        "progress_shortfall",
        "m",
        "max(max_progress_over_feasible_K - route_progress_k, 0)",
        (
            "fixed DP candidate set K=8",
            "ordered current route centerline",
            "current-tick feasibility mask",
        ),
        "requires a decision-time topology route and all K candidates",
        "planned candidate set only; no observed or GT future",
        "conditional:nuScenes has geometry but no mission route",
        "camp_core/tests/test_diffusion_planner_integration.py::"
        "test_dp_selector_appends_progress_shortfall_atom",
    ),
    _contract(
        "planned_red_light_cost",
        "dimensionless DP reward cost",
        "max(-fixed_dp_planned_red_light_reward_k, 0)",
        (
            "fixed DP candidate set K=8",
            "current traffic-light phase aligned to route",
        ),
        "requires explicit current route signal phase",
        "planned candidate horizon plus current signal phase; no GT future",
        "unavailable:nuScenes supplies traffic-light geometry but no current phase",
        "camp_core/tests/test_diffusion_planner_integration.py::"
        "test_dp_v8_selector_appends_red_light_and_lateral_atoms",
    ),
    _contract(
        "planned_lateral_acceleration_cost",
        "m/s^2",
        "mean(abs(candidate_acceleration dot candidate_lateral_axis))",
        ("fixed DP candidate_xy[K,80,2]", "dt=0.1 s"),
        "available after fixed DP produces causal K=8 candidates",
        "planned candidate horizon only; no observed or GT future",
        "available_from_fixed_dp_candidate_tensor",
        "camp_core/tests/test_diffusion_planner_integration.py::"
        "test_lateral_comfort_shadow_costs_are_horizon_aligned_and_anchored",
    ),
    _contract(
        "red_stopping_margin_cost",
        "m^2/s",
        "dt * sum(proximity * max(speed - sqrt(2*a*max(distance-buffer,0)),0)^2)",
        (
            "fixed DP candidate_xy[K,80,2]",
            "current red route points and directions",
            "dt=0.1 s",
        ),
        "requires explicit current red signal state aligned to route",
        "planned candidate horizon plus current signal phase; no GT future",
        "unavailable:nuScenes supplies traffic-light geometry but no current phase",
        "camp_core/tests/test_diffusion_planner_integration.py::"
        "test_red_stopping_margin_cost_is_continuous_before_hard_violation",
    ),
    _contract(
        "dp_prior_jerk_excess_cost",
        "m/s^3",
        "max(mean_jerk_norm_k - mean_jerk_norm_candidate0, 0)",
        ("fixed DP candidate_xy[K,80,2]", "candidate 0 DP Top-1 semantic", "dt=0.1 s"),
        "available only after candidate 0 is verified as deterministic DP Top-1",
        "planned candidate horizon only; no observed or GT future",
        "available_after_candidate0_top1_semantic_verification",
        "camp_core/tests/test_diffusion_planner_integration.py::"
        "test_dp_prior_comfort_excess_costs_anchor_deterministic_candidate",
        candidate_index_dependency="candidate 0 is the fixed DP-prior reference",
    ),
)


_SCHEMAS = {
    "camp_legacy_v1_9d": CAMP_ATOM_NAMES,
    "dp_camp_v7_10d": DP_CAMP_ATOM_NAMES,
    "dp_camp_v8_12d": DP_CAMP_ATOM_NAMES_V8,
    "dp_camp_v9_13d": DP_CAMP_ATOM_NAMES_V9,
    "dp_camp_v10_14d": DP_CAMP_ATOM_NAMES_V10,
}


class UnavailableAtomInputsError(ValueError):
    pass


def project_candidates_to_route(
    candidates: np.ndarray,
    route_lanes: np.ndarray,
    route_speed_limits: np.ndarray,
    route_has_speed_limits: np.ndarray,
    *,
    speed_source_policy: str = FULL_WINDOW_EXACT_SPEED,
) -> dict[str, np.ndarray]:
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

    points = []
    left_offsets = []
    right_offsets = []
    speeds = []
    for slot in range(route.shape[0]):
        valid = route[slot, :, 13] > 0.5
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
            left_offset = (
                left_start[segment]
                + fraction * (left_end[segment] - left_start[segment])
            )
            right_offset = (
                right_start[segment]
                + fraction * (right_end[segment] - right_start[segment])
            )
            lateral[candidate_index, step] = np.dot(
                point - projections[segment], normal
            )
            left_width[candidate_index, step] = np.dot(left_offset, normal)
            right_width[candidate_index, step] = -np.dot(right_offset, normal)
            speed_limit[candidate_index, step] = (
                speed_start[segment]
                + fraction * (speed_end[segment] - speed_start[segment])
            )
            projected_arc[candidate_index, step] = arc_starts[segment] + along[segment]
    if np.any(left_width <= 0.0) or np.any(right_width <= 0.0):
        raise ValueError("projected route boundaries and speed limits must be positive")
    route_speed_source_eligible = np.isfinite(speed_limit).all(axis=1) & (
        speed_limit > 0.0
    ).all(axis=1)
    if speed_source_policy == FULL_WINDOW_EXACT_SPEED and not (
        route_speed_source_eligible.all()
    ):
        raise ValueError("projected route boundaries and speed limits must be positive")
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
) -> np.ndarray:
    predictions = np.asarray(neighbor_predictions, dtype=np.float64)
    valid = np.asarray(neighbor_valid_mask, dtype=bool).reshape(-1)
    history = np.asarray(neighbor_history, dtype=np.float64)
    static = np.asarray(static_objects, dtype=np.float64)
    if predictions.shape != (8, 32, 80, 4) or not np.isfinite(predictions).all():
        raise ValueError("neighbor predictions must be finite [8,32,80,4]")
    if valid.shape != (32,):
        raise ValueError("neighbor_valid_mask must have shape [32]")
    if history.shape != (32, 31, 11) or not np.isfinite(history).all():
        raise ValueError("neighbor history must be finite [32,31,11]")
    if static.shape != (5, 10) or not np.isfinite(static).all():
        raise ValueError("static objects must be finite [5,10]")

    obstacles = np.zeros((8, 37, 80, 5), dtype=np.float64)
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


def observable_feasibility(
    candidates: np.ndarray,
    signal_mask: np.ndarray,
    route_projection: Mapping[str, np.ndarray],
    obstacle_obbs: np.ndarray,
    ego_shape: np.ndarray,
) -> dict[str, object]:
    trajectories = np.asarray(candidates, dtype=np.float64)
    signal = np.asarray(signal_mask, dtype=bool).reshape(-1)
    obstacles = np.asarray(obstacle_obbs, dtype=np.float64)
    shape = np.asarray(ego_shape, dtype=np.float64).reshape(-1)
    if trajectories.shape != (8, 80, 4) or not np.isfinite(trajectories).all():
        raise ValueError("candidates must be finite [8,80,4]")
    if signal.shape != (8,):
        raise ValueError("signal_mask must have shape [8]")
    if obstacles.shape != (8, 37, 80, 5) or not np.isfinite(obstacles).all():
        raise ValueError("obstacle_obbs must be finite [8,37,80,5]")
    if shape.shape != (3,) or not np.isfinite(shape).all() or np.any(shape <= 0.0):
        raise ValueError("ego_shape must be positive [wheelbase,length,width]")

    lateral = np.asarray(route_projection["lateral_offset"], dtype=np.float64)
    left = np.asarray(route_projection["left_width"], dtype=np.float64)
    right = np.asarray(route_projection["right_width"], dtype=np.float64)
    if any(values.shape != (8, 80) for values in (lateral, left, right)):
        raise ValueError("route projection arrays must have shape [8,80]")
    lane_violation = (lateral > left + 1.0) | (lateral < -(right + 1.0))
    lane_feasible = ~lane_violation.any(axis=1)

    heading_vectors = trajectories[:, :, 2:4]
    if np.any(np.linalg.norm(heading_vectors, axis=2) < 0.5):
        raise ValueError("candidate headings must be valid cos/sin vectors")
    headings = np.arctan2(heading_vectors[:, :, 1], heading_vectors[:, :, 0])
    wheelbase, ego_length, ego_width = shape
    collision_free = np.ones(8, dtype=bool)
    clearance_clip_m = 3.0
    minimum_clearance = np.full(
        (8, 80), clearance_clip_m, dtype=np.float64
    )
    for candidate_index in range(8):
        for step in range(80):
            ego_center, ego_radius = _obb_center_and_radius(
                trajectories[candidate_index, step, 0],
                trajectories[candidate_index, step, 1],
                headings[candidate_index, step],
                ego_length,
                ego_width,
                wheelbase,
            )
            ego_box = _obb_corners(
                trajectories[candidate_index, step, 0],
                trajectories[candidate_index, step, 1],
                headings[candidate_index, step],
                ego_length,
                ego_width,
                wheelbase,
            )
            for obstacle in obstacles[candidate_index, :, step]:
                if obstacle[3] <= 0.0 or obstacle[4] <= 0.0:
                    continue
                obstacle_center, obstacle_radius = _obb_center_and_radius(
                    obstacle[0],
                    obstacle[1],
                    obstacle[2],
                    obstacle[3],
                    obstacle[4],
                )
                lower_bound = (
                    float(np.linalg.norm(ego_center - obstacle_center))
                    - ego_radius
                    - obstacle_radius
                )
                if lower_bound >= clearance_clip_m:
                    continue
                obstacle_box = _obb_corners(
                    obstacle[0],
                    obstacle[1],
                    obstacle[2],
                    obstacle[3],
                    obstacle[4],
                )
                distance = _obb_distance(ego_box, obstacle_box)
                minimum_clearance[candidate_index, step] = min(
                    minimum_clearance[candidate_index, step], distance
                )
                if distance <= 1e-12:
                    collision_free[candidate_index] = False

    physical = signal & lane_feasible & collision_free
    reasons = []
    for candidate_index in range(8):
        candidate_reasons = []
        if not signal[candidate_index]:
            candidate_reasons.append("signal_source_unavailable")
        if not lane_feasible[candidate_index]:
            candidate_reasons.append("lane_corridor")
        if not collision_free[candidate_index]:
            candidate_reasons.append("obb_collision")
        reasons.append(tuple(candidate_reasons))
    return {
        "signal_mask": signal,
        "lane_feasible_mask": lane_feasible,
        "obb_collision_free_mask": collision_free,
        "physical_feasible_mask": physical,
        "candidate_reasons": tuple(reasons),
        "minimum_obb_clearance": minimum_clearance,
        "minimum_obb_clearance_clip_m": clearance_clip_m,
        "feasibility_scope": OBSERVABLE_FEASIBILITY_SCOPE,
        "closed_loop_safety_claim": False,
    }


def materialize_canonical_14d(
    *,
    candidates: np.ndarray,
    causal_input: Mapping[str, np.ndarray],
    neighbor_predictions: np.ndarray,
    neighbor_valid_mask: np.ndarray,
    signal_mask: np.ndarray,
    planned_red_light_cost: np.ndarray,
    dt: float,
    speed_source_policy: str = FULL_WINDOW_EXACT_SPEED,
) -> dict[str, object]:
    errors = validate_causal_dp_input(causal_input)
    if errors:
        raise ValueError("invalid causal input: " + "; ".join(errors))
    if not np.isfinite(dt) or not np.isclose(dt, 0.1, rtol=0.0, atol=1e-8):
        raise ValueError("dt must equal the frozen 0.1-second contract")
    trajectories = np.asarray(candidates, dtype=np.float64)
    if trajectories.shape != (8, 80, 4) or not np.isfinite(trajectories).all():
        raise ValueError("candidates must be finite [8,80,4]")
    planned_red = np.asarray(planned_red_light_cost, dtype=np.float64).reshape(-1)
    if (
        planned_red.shape != (8,)
        or not np.isfinite(planned_red).all()
        or np.any(planned_red < 0.0)
    ):
        raise ValueError("planned_red_light_cost must be finite nonnegative [8]")

    projection = project_candidates_to_route(
        trajectories,
        causal_input["route_lanes"],
        causal_input["route_lanes_speed_limit"],
        causal_input["route_lanes_has_speed_limit"],
        speed_source_policy=speed_source_policy,
    )
    obstacle_obbs = build_observable_obbs(
        neighbor_predictions,
        neighbor_valid_mask,
        causal_input["neighbor_agents_past"],
        causal_input["static_objects"],
    )
    feasibility = observable_feasibility(
        trajectories,
        signal_mask,
        projection,
        obstacle_obbs,
        causal_input["ego_shape"],
    )
    source_complete = np.asarray(
        projection["route_speed_source_eligible_mask"], dtype=bool
    )
    physical = np.asarray(feasibility["physical_feasible_mask"], dtype=bool).copy()
    physical &= source_complete
    candidate_reasons = tuple(
        tuple(reasons)
        + (() if source_complete[index] else ("route_speed_source_unavailable",))
        for index, reasons in enumerate(feasibility["candidate_reasons"])
    )
    feasibility = {
        **feasibility,
        "physical_feasible_mask": physical,
        "candidate_reasons": candidate_reasons,
    }
    result: dict[str, object] = {
        **feasibility,
        "baseline_semantics": "fixed_dp_deterministic_map_baseline",
        "baseline_equivalence_verified": False,
        "native_ranked_top1": False,
        "atom_names": tuple(DP_CAMP_ATOM_NAMES_V10),
        "atom_matrix": None,
        "canonical_eligible": False,
        "exclusion_reason": None,
        "route_progress": projection["route_progress"],
        "route_speed_source_eligible_mask": source_complete,
        "minimum_obb_clearance": feasibility["minimum_obb_clearance"],
        "progress_reference": None,
    }
    signal = np.asarray(feasibility["signal_mask"], dtype=bool)
    if not signal.all():
        result["exclusion_reason"] = "signal_source_incomplete"
        return result
    if not source_complete.any():
        result["exclusion_reason"] = (
            "all_candidates_route_speed_source_ineligible"
        )
        return result
    if not physical.any():
        result["exclusion_reason"] = "all_candidates_physically_infeasible"
        return result

    xy = trajectories[:, :, :2]
    velocity = np.diff(xy, axis=1) / float(dt)
    acceleration = np.diff(velocity, axis=1) / float(dt)
    jerk = np.diff(acceleration, axis=1) / float(dt)
    jerk_squared = np.sum(jerk**2, axis=2)
    split = max(1, jerk_squared.shape[1] // 3)
    jerk_atoms = np.column_stack(
        [
            float(dt) * np.sum(jerk_squared[:, :split], axis=1),
            float(dt) * np.sum(jerk_squared[:, split:], axis=1),
            float(dt) * np.sum(jerk_squared, axis=1),
        ]
    )
    rms_acceleration = np.sqrt(np.mean(np.sum(acceleration**2, axis=2), axis=1))
    speeds = np.linalg.norm(velocity, axis=2)
    speed_atoms = np.zeros((8, 3), dtype=np.float64)
    for candidate_index in np.flatnonzero(source_complete):
        candidate_limits = np.asarray(
            projection["speed_limit"][candidate_index, 1:], dtype=np.float64
        )
        speed_atoms[candidate_index] = [
            float(dt)
            * np.sum(
                np.maximum(
                    speeds[candidate_index] - (candidate_limits - margin),
                    0.0,
                )
                ** 2
            )
            for margin in (0.0, 0.5, 1.0)
        ]
    lateral = np.asarray(projection["lateral_offset"], dtype=np.float64)
    left = np.asarray(projection["left_width"], dtype=np.float64)
    right = np.asarray(projection["right_width"], dtype=np.float64)
    boundary_overrun = np.where(
        lateral >= 0.0,
        np.maximum(lateral - left, 0.0),
        np.maximum(-lateral - right, 0.0),
    )
    lane_deviation = float(dt) * np.sum(boundary_overrun**2, axis=1)
    minimum_clearance = np.asarray(
        feasibility["minimum_obb_clearance"], dtype=np.float64
    )
    clearance = float(dt) * np.sum(
        np.maximum(3.0 - minimum_clearance, 0.0) ** 2,
        axis=1,
    )
    progress = np.asarray(projection["route_progress"], dtype=np.float64)
    progress_reference = float(np.max(progress[physical]))
    progress_shortfall = np.maximum(progress_reference - progress, 0.0)
    lateral_acceleration = compute_lateral_comfort_shadow_costs(
        trajectories, float(dt)
    )[0]
    red_stopping = compute_red_stopping_margin_costs(
        trajectories,
        _red_route_points_from_lanes(causal_input["route_lanes"]),
        float(dt),
    )
    dp_prior_jerk = compute_dp_prior_comfort_excess_costs(
        trajectories, float(dt)
    )[0]
    matrix = np.column_stack(
        [
            jerk_atoms,
            rms_acceleration,
            speed_atoms,
            lane_deviation,
            clearance,
            progress_shortfall,
            planned_red,
            lateral_acceleration,
            red_stopping,
            dp_prior_jerk,
        ]
    )
    availability = canonical_atom_availability(
        candidate_count=8,
        fixed_dp_candidates_available=True,
        route_topology_available=True,
        lane_boundaries_available=True,
        route_speed_limit_full_horizon_available=True,
        candidate_neighbor_predictions_available=True,
        static_obstacle_context_available=True,
        feasibility_mask_available=True,
        traffic_light_state_available=True,
        red_stop_geometry_available=True,
        # Legacy availability flag name: this certifies the fixed candidate-0
        # reference position only, not native K=8 ranking or independent
        # deterministic/MAP equivalence evidence.
        dp_top1_semantic_verified=True,
    )
    result.update(
        {
            "atom_matrix": validate_canonical_atom_matrix(
                "dp_camp_v10_14d", availability, matrix
            ),
            "availability": availability,
            "canonical_eligible": True,
            "progress_reference": progress_reference,
        }
    )
    return result


def canonical_atom_availability(
    *,
    candidate_count: int,
    fixed_dp_candidates_available: bool,
    route_topology_available: bool,
    lane_boundaries_available: bool,
    route_speed_limit_full_horizon_available: bool,
    candidate_neighbor_predictions_available: bool,
    static_obstacle_context_available: bool,
    feasibility_mask_available: bool,
    traffic_light_state_available: bool,
    red_stop_geometry_available: bool,
    dp_top1_semantic_verified: bool,
) -> dict[str, bool]:
    if isinstance(candidate_count, bool) or candidate_count != 8:
        raise ValueError("candidate_count must be 8")
    flags = {
        "fixed_dp_candidates_available": fixed_dp_candidates_available,
        "route_topology_available": route_topology_available,
        "lane_boundaries_available": lane_boundaries_available,
        "route_speed_limit_full_horizon_available": (
            route_speed_limit_full_horizon_available
        ),
        "candidate_neighbor_predictions_available": (
            candidate_neighbor_predictions_available
        ),
        "static_obstacle_context_available": static_obstacle_context_available,
        "feasibility_mask_available": feasibility_mask_available,
        "traffic_light_state_available": traffic_light_state_available,
        "red_stop_geometry_available": red_stop_geometry_available,
        "dp_top1_semantic_verified": dp_top1_semantic_verified,
    }
    for name, value in flags.items():
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be bool")

    candidates = fixed_dp_candidates_available
    route = candidates and route_topology_available
    speed = route and route_speed_limit_full_horizon_available
    traffic = route and traffic_light_state_available
    return {
        "jerk_early": candidates,
        "jerk_late": candidates,
        "jerk_full": candidates,
        "rms_acceleration": candidates,
        "speed_limit_margin_0_0": speed,
        "speed_limit_margin_0_5": speed,
        "speed_limit_margin_1_0": speed,
        "lane_deviation": route and lane_boundaries_available,
        "clearance": (
            candidates
            and candidate_neighbor_predictions_available
            and static_obstacle_context_available
        ),
        "progress_shortfall": route and feasibility_mask_available,
        "planned_red_light_cost": traffic,
        "planned_lateral_acceleration_cost": candidates,
        "red_stopping_margin_cost": traffic and red_stop_geometry_available,
        "dp_prior_jerk_excess_cost": candidates and dp_top1_semantic_verified,
    }


def require_canonical_schema(
    schema_version: str,
    availability: Mapping[str, bool],
) -> tuple[str, ...]:
    try:
        names = _SCHEMAS[schema_version]
    except KeyError as exc:
        raise ValueError(f"unsupported canonical atom schema {schema_version!r}") from exc
    expected = set(DP_CAMP_ATOM_NAMES_V10)
    missing_keys = expected - set(availability)
    extra_keys = set(availability) - expected
    if missing_keys or extra_keys:
        raise ValueError(
            f"availability keys mismatch: missing={sorted(missing_keys)}, "
            f"extra={sorted(extra_keys)}"
        )
    invalid = [name for name, value in availability.items() if not isinstance(value, bool)]
    if invalid:
        raise ValueError(f"availability values must be bool: {sorted(invalid)}")
    unavailable = tuple(name for name in names if not availability[name])
    if unavailable:
        raise UnavailableAtomInputsError(
            f"{schema_version} has unavailable causal atoms: {', '.join(unavailable)}"
        )
    return tuple(names)


def validate_canonical_atom_matrix(
    schema_version: str,
    availability: Mapping[str, bool],
    atom_matrix: np.ndarray,
) -> np.ndarray:
    names = require_canonical_schema(schema_version, availability)
    matrix = np.asarray(atom_matrix, dtype=np.float64)
    expected_shape = (8, len(names))
    if matrix.shape != expected_shape:
        raise ValueError(
            f"atom_matrix shape must be {expected_shape}, got {matrix.shape}"
        )
    if not np.all(np.isfinite(matrix)):
        raise ValueError("atom_matrix must contain only finite values")
    if np.any(matrix < 0.0):
        raise ValueError("atom_matrix must be nonnegative")
    return matrix
