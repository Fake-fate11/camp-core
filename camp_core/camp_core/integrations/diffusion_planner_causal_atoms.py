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
