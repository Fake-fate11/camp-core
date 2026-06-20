from __future__ import annotations

import inspect

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_lane_hard_violation_support import (
    LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES,
    LANE_HARD_VIOLATION_SUPPORT_FIELD_NAMES,
    LANE_HARD_VIOLATION_SUPPORT_LATENCY_KEYS,
    LANE_HARD_VIOLATION_SUPPORT_LOGGING_SCHEMA_VERSION,
    build_lane_hard_violation_support_logging_payload,
)


def _route() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0],
            [5.0, 0.0],
            [10.0, 0.0],
        ],
        dtype=np.float64,
    )


def _candidates() -> np.ndarray:
    return np.asarray(
        [
            [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0]],
            [[0.0, 0.0], [1.0, 0.6], [2.0, 1.4], [3.0, 2.0]],
            [[0.0, 0.0], [1.0, 0.2], [2.0, 0.2], [3.0, 0.2]],
        ],
        dtype=np.float64,
    )


def test_lane_hard_violation_payload_schema_shapes_and_metadata() -> None:
    payload = build_lane_hard_violation_support_logging_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        support_steps=4,
        dt_s=0.1,
        corridor_half_width_m=1.0,
        lateral_error_rate_budget_mps=1.0,
    )

    assert payload["schema_version"] == LANE_HARD_VIOLATION_SUPPORT_LOGGING_SCHEMA_VERSION
    assert payload["enabled"] is True
    assert payload["default_off"] is True
    assert payload["selection_effect"] is False
    assert payload["future_outcome_leakage"] is False
    assert payload["closed_loop_outcome_fields_read"] is False
    assert payload["classical_benders_claim"] is False
    assert "score_k(w)=a_k^T w" in payload["math_boundary"]
    assert payload["candidate_count"] == 3
    assert payload["horizons"] == {"support_steps": 4, "dt_s": 0.1}
    assert payload["budgets"]["lateral_error_rate_budget_mps"] == 1.0
    assert set(payload["field_shapes"]) == set(LANE_HARD_VIOLATION_SUPPORT_FIELD_NAMES)
    assert payload["field_shapes"]["candidate_route_lateral_error_profile_m"] == [3, 4]
    assert payload["field_shapes"]["candidate_route_corridor_half_width_profile_m"] == [
        3,
        4,
    ]
    assert payload["field_shapes"]["candidate_route_heading_error_profile_rad"] == [3, 4]
    assert payload["field_shapes"]["candidate_lateral_error_rate_profile_mps"] == [3, 3]
    assert all(payload["finite_checks"].values())
    assert set(payload["latency_ms"]) == set(LANE_HARD_VIOLATION_SUPPORT_LATENCY_KEYS)
    assert all(float(value) >= 0.0 for value in payload["latency_ms"].values())
    assert payload["lane_hard_violation_support_atom_names"] == list(
        LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES
    )
    assert np.asarray(payload["lane_hard_violation_support_atoms"]).shape == (
        3,
        len(LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES),
    )


def test_lane_hard_violation_atoms_are_nonnegative_fixed_coefficients() -> None:
    payload = build_lane_hard_violation_support_logging_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        support_steps=4,
        dt_s=0.1,
        corridor_half_width_m=1.0,
        lateral_error_rate_budget_mps=1.0,
    )
    atoms = np.asarray(payload["lane_hard_violation_support_atoms"], dtype=np.float64)
    atom_index = {
        name: idx
        for idx, name in enumerate(payload["lane_hard_violation_support_atom_names"])
    }

    assert np.all(atoms >= 0.0)
    np.testing.assert_allclose(atoms[0], np.zeros(atoms.shape[1]))
    assert atoms[1, atom_index["route_lateral_envelope_excess_v1"]] > 0.0
    assert atoms[1, atom_index["route_lateral_margin_deficit_vs_top1_v1"]] > 0.0
    assert atoms[1, atom_index["route_heading_divergence_excess_vs_top1_v1"]] > 0.0
    assert atoms[1, atom_index["lateral_error_rate_excess_v1"]] > 0.0
    assert atoms[1, atom_index["lateral_divergence_growth_v1"]] > 0.0
    assert atoms[1, atom_index["lane_hard_violation_support_conflict_v1"]] > 0.0
    assert atoms[2, atom_index["route_lateral_envelope_excess_v1"]] == 0.0


def test_lane_hard_violation_payload_accepts_route_width_profile() -> None:
    payload = build_lane_hard_violation_support_logging_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        support_steps=4,
        corridor_half_width_m=np.asarray([1.0, 1.2, 1.4], dtype=np.float64),
    )

    width = np.asarray(
        payload["candidate_route_corridor_half_width_profile_m"],
        dtype=np.float64,
    )
    assert width.shape == (3, 4)
    assert np.all(width >= 1.0)


def test_lane_hard_violation_payload_does_not_accept_outcome_inputs() -> None:
    signature = inspect.signature(build_lane_hard_violation_support_logging_payload)

    assert "outcome" not in str(signature).lower()
    assert "closed_loop" not in str(signature).lower()
    assert list(signature.parameters) == [
        "candidates",
        "route_centerline_ego",
        "support_steps",
        "dt_s",
        "corridor_half_width_m",
        "lateral_error_rate_budget_mps",
    ]


def test_lane_hard_violation_timing_does_not_change_logged_values() -> None:
    first = build_lane_hard_violation_support_logging_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        support_steps=4,
        corridor_half_width_m=1.0,
    )
    second = build_lane_hard_violation_support_logging_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        support_steps=4,
        corridor_half_width_m=1.0,
    )

    assert set(first["latency_ms"]) == set(LANE_HARD_VIOLATION_SUPPORT_LATENCY_KEYS)
    assert set(second["latency_ms"]) == set(LANE_HARD_VIOLATION_SUPPORT_LATENCY_KEYS)
    first_without_latency = dict(first)
    second_without_latency = dict(second)
    first_without_latency.pop("latency_ms")
    second_without_latency.pop("latency_ms")
    assert first_without_latency == second_without_latency


def test_lane_hard_violation_payload_validates_inputs() -> None:
    with pytest.raises(ValueError, match="candidates must have shape"):
        build_lane_hard_violation_support_logging_payload(
            candidates=np.zeros((4, 2), dtype=np.float64),
            route_centerline_ego=_route(),
            support_steps=4,
        )
    with pytest.raises(ValueError, match="route_centerline_ego"):
        build_lane_hard_violation_support_logging_payload(
            candidates=_candidates(),
            route_centerline_ego=np.zeros((1, 2), dtype=np.float64),
            support_steps=4,
        )
    with pytest.raises(ValueError, match="dt_s"):
        build_lane_hard_violation_support_logging_payload(
            candidates=_candidates(),
            route_centerline_ego=_route(),
            support_steps=4,
            dt_s=0.0,
        )
    with pytest.raises(ValueError, match="corridor_half_width_m"):
        build_lane_hard_violation_support_logging_payload(
            candidates=_candidates(),
            route_centerline_ego=_route(),
            support_steps=4,
            corridor_half_width_m=0.0,
        )
    with pytest.raises(ValueError, match="lateral_error_rate_budget_mps"):
        build_lane_hard_violation_support_logging_payload(
            candidates=_candidates(),
            route_centerline_ego=_route(),
            support_steps=4,
            lateral_error_rate_budget_mps=-1.0,
        )
