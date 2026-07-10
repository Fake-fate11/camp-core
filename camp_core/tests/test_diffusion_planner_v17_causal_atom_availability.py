from __future__ import annotations

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner import (
    DP_CAMP_ATOM_NAMES_V10,
)
from camp_core.integrations.diffusion_planner_causal_atoms import (
    CANONICAL_ATOM_CONTRACTS,
    UnavailableAtomInputsError,
    canonical_atom_availability,
    require_canonical_schema,
    validate_canonical_atom_matrix,
)


SCHEMA_VERSIONS = (
    "camp_legacy_v1_9d",
    "dp_camp_v7_10d",
    "dp_camp_v8_12d",
    "dp_camp_v9_13d",
    "dp_camp_v10_14d",
)


def _availability(**overrides: bool):
    inputs = {
        "candidate_count": 8,
        "fixed_dp_candidates_available": True,
        "route_topology_available": True,
        "lane_boundaries_available": True,
        "route_speed_limit_full_horizon_available": True,
        "candidate_neighbor_predictions_available": True,
        "static_obstacle_context_available": True,
        "feasibility_mask_available": True,
        "traffic_light_state_available": True,
        "red_stop_geometry_available": True,
        "dp_top1_semantic_verified": True,
    }
    inputs.update(overrides)
    return canonical_atom_availability(**inputs)


def test_contract_table_is_canonical_causal_and_fail_closed() -> None:
    assert tuple(contract.name for contract in CANONICAL_ATOM_CONTRACTS) == (
        DP_CAMP_ATOM_NAMES_V10
    )
    for contract in CANONICAL_ATOM_CONTRACTS:
        assert contract.inputs
        assert contract.unit
        assert contract.formula
        assert contract.decision_time_availability
        assert contract.future_dependency
        assert contract.nonnegative is True
        assert contract.finite_required is True
        assert contract.depends_on_w is False
        assert contract.depends_on_rank is False
        assert contract.depends_on_selected_index is False
        assert contract.gt_future_allowed is False
        assert contract.holdout_label_allowed is False
        assert contract.nuscenes_availability
        assert contract.test_evidence


def test_live_nuscenes_missing_speed_and_signal_blocks_every_approved_schema() -> None:
    availability = _availability(
        route_speed_limit_full_horizon_available=False,
        traffic_light_state_available=False,
    )

    for name in (
        "speed_limit_margin_0_0",
        "speed_limit_margin_0_5",
        "speed_limit_margin_1_0",
        "planned_red_light_cost",
        "red_stopping_margin_cost",
    ):
        assert availability[name] is False
    assert availability["jerk_early"] is True
    assert availability["planned_lateral_acceleration_cost"] is True
    assert availability["dp_prior_jerk_excess_cost"] is True

    for schema_version in SCHEMA_VERSIONS:
        with pytest.raises(UnavailableAtomInputsError):
            require_canonical_schema(schema_version, availability)


def test_missing_signal_allows_only_9d_and_10d_when_speed_is_real() -> None:
    availability = _availability(traffic_light_state_available=False)

    assert len(require_canonical_schema("camp_legacy_v1_9d", availability)) == 9
    assert len(require_canonical_schema("dp_camp_v7_10d", availability)) == 10
    for schema_version in SCHEMA_VERSIONS[2:]:
        with pytest.raises(
            UnavailableAtomInputsError, match="planned_red_light_cost"
        ):
            require_canonical_schema(schema_version, availability)


def test_full_14d_requires_k8_and_explicit_boolean_source_evidence() -> None:
    availability = _availability()
    assert require_canonical_schema("dp_camp_v10_14d", availability) == (
        DP_CAMP_ATOM_NAMES_V10
    )

    with pytest.raises(ValueError, match="candidate_count must be 8"):
        _availability(candidate_count=7)
    with pytest.raises(
        ValueError, match="route_speed_limit_full_horizon_available must be bool"
    ):
        _availability(route_speed_limit_full_horizon_available=1)


def test_gate_requires_feasibility_static_context_and_red_stop_geometry() -> None:
    assert _availability(feasibility_mask_available=False)["progress_shortfall"] is False
    assert _availability(static_obstacle_context_available=False)["clearance"] is False
    assert _availability(red_stop_geometry_available=False)[
        "red_stopping_margin_cost"
    ] is False


def test_atom_matrix_validation_enforces_shape_finite_and_nonnegative() -> None:
    availability = _availability(traffic_light_state_available=False)
    valid = np.zeros((8, 10), dtype=np.float64)
    validated = validate_canonical_atom_matrix(
        "dp_camp_v7_10d", availability, valid
    )
    np.testing.assert_array_equal(validated, valid)

    with pytest.raises(ValueError, match="shape"):
        validate_canonical_atom_matrix(
            "dp_camp_v7_10d", availability, np.zeros((7, 10))
        )
    invalid = valid.copy()
    invalid[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        validate_canonical_atom_matrix("dp_camp_v7_10d", availability, invalid)
    invalid = valid.copy()
    invalid[0, 0] = -1.0
    with pytest.raises(ValueError, match="nonnegative"):
        validate_canonical_atom_matrix("dp_camp_v7_10d", availability, invalid)
