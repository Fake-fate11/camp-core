from __future__ import annotations

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v26_atom_sources import (
    CANDIDATE_LOCAL_EXACT_SPEED,
    FULL_WINDOW_EXACT_SPEED,
    build_observable_obbs,
    project_candidates_to_route,
)


def _route() -> np.ndarray:
    route = np.zeros((25, 20, 33), dtype=np.float64)
    route[0, :, 0] = np.arange(20, dtype=np.float64)
    route[0, :, 4:6] = np.array([0.0, 2.0])
    route[0, :, 6:8] = np.array([0.0, -2.0])
    return route


def _candidate() -> np.ndarray:
    candidate = np.zeros((1, 80, 4), dtype=np.float64)
    candidate[0, :, 0] = np.arange(80, dtype=np.float64) * 0.1
    candidate[0, :, 2] = 1.0
    return candidate


def test_route_projection_preserves_observed_speed_and_global_geometry() -> None:
    projection = project_candidates_to_route(
        _candidate(),
        _route(),
        np.array([8.0] + [0.0] * 24),
        np.array([True] + [False] * 24),
        speed_source_policy=CANDIDATE_LOCAL_EXACT_SPEED,
    )

    assert projection["route_speed_source_eligible_mask"].tolist() == [True]
    np.testing.assert_allclose(projection["speed_limit"], 8.0)
    np.testing.assert_allclose(projection["lateral_offset"], 0.0)
    np.testing.assert_allclose(projection["left_width"], 2.0)
    np.testing.assert_allclose(projection["right_width"], 2.0)


def test_route_projection_keeps_missing_speed_distinct_from_zero() -> None:
    projection = project_candidates_to_route(
        _candidate(),
        _route(),
        np.zeros(25),
        np.zeros(25, dtype=bool),
        speed_source_policy=CANDIDATE_LOCAL_EXACT_SPEED,
    )

    assert projection["route_speed_source_eligible_mask"].tolist() == [False]
    assert np.isnan(projection["speed_limit"]).all()
    with pytest.raises(ValueError, match="positive speed limit"):
        project_candidates_to_route(
            _candidate(),
            _route(),
            np.zeros(25),
            np.zeros(25, dtype=bool),
            speed_source_policy=FULL_WINDOW_EXACT_SPEED,
        )


def test_observable_obb_builder_can_select_dynamic_only_or_combined_source() -> None:
    predictions = np.zeros((8, 32, 80, 4), dtype=np.float64)
    predictions[:, 0, :, 0] = 3.0
    predictions[:, 0, :, 2] = 1.0
    valid = np.zeros(32, dtype=bool)
    valid[0] = True
    history = np.zeros((32, 31, 11), dtype=np.float64)
    history[0, -1, 6:8] = np.array([2.0, 4.0])
    static = np.zeros((5, 10), dtype=np.float64)
    static[0, :6] = np.array([10.0, 1.0, 1.0, 0.0, 2.5, 5.0])

    dynamic = build_observable_obbs(
        predictions, valid, history, static, include_static_objects=False
    )
    combined = build_observable_obbs(
        predictions, valid, history, static, include_static_objects=True
    )

    assert dynamic.shape == (8, 32, 80, 5)
    assert combined.shape == (8, 37, 80, 5)
    np.testing.assert_allclose(
        dynamic[:, 0, :, 3:5], np.broadcast_to([4.0, 2.0], (8, 80, 2))
    )
    np.testing.assert_allclose(
        combined[:, 32, :, 3:5], np.broadcast_to([5.0, 2.5], (8, 80, 2))
    )
    assert np.isfinite(dynamic).all() and np.isfinite(combined).all()
