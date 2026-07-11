from __future__ import annotations

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner import (
    CAMP_ATOM_NAMES,
    DP_CAMP_ATOM_NAMES,
    DP_CAMP_ATOM_NAMES_V8,
    DP_CAMP_ATOM_NAMES_V9,
    DP_CAMP_ATOM_NAMES_V10,
    atom_schema_for_dimension,
)
from camp_core.outer_master.robust_margin_master import (
    RobustMarginConfig,
    solve_robust_margin_cutting_plane,
)


def test_deployed_dp_camp_atom_schemas_are_nested_and_versioned() -> None:
    expected = [
        ("camp_legacy_v1_9d", CAMP_ATOM_NAMES),
        ("dp_camp_v7_10d", DP_CAMP_ATOM_NAMES),
        ("dp_camp_v8_12d", DP_CAMP_ATOM_NAMES_V8),
        ("dp_camp_v9_13d", DP_CAMP_ATOM_NAMES_V9),
        ("dp_camp_v10_14d", DP_CAMP_ATOM_NAMES_V10),
    ]

    previous_names: tuple[str, ...] = ()
    for expected_version, expected_names in expected:
        version, names = atom_schema_for_dimension(len(expected_names))

        assert version == expected_version
        assert names == expected_names
        assert names[: len(previous_names)] == previous_names
        previous_names = names


def test_deployed_v10_schema_excludes_non_atom_routes() -> None:
    forbidden_names = {
        "candidate_reference_blend",
        "candidate_guidance",
        "traffic_light_hybrid_postselection",
        "perfect_tracker_command_postselection",
        "underprogress_relaxation",
        "splice_shadow_rule",
        "candidate_closed_loop_outcomes",
        "candidate_set_consensus_payload",
    }

    assert forbidden_names.isdisjoint(set(DP_CAMP_ATOM_NAMES_V10))


def test_fixed_candidate_atom_scores_are_affine_in_simplex_weights() -> None:
    atoms = np.arange(1, 1 + 3 * len(DP_CAMP_ATOM_NAMES_V10), dtype=np.float64)
    atoms = atoms.reshape(3, len(DP_CAMP_ATOM_NAMES_V10))
    scales = np.linspace(1.0, 3.0, len(DP_CAMP_ATOM_NAMES_V10))
    normalized = atoms / scales.reshape(1, -1)

    weight_a = np.full(len(DP_CAMP_ATOM_NAMES_V10), 1.0)
    weight_a = weight_a / weight_a.sum()
    weight_b = np.linspace(1.0, 2.0, len(DP_CAMP_ATOM_NAMES_V10))
    weight_b = weight_b / weight_b.sum()
    alpha = 0.37
    mixed = alpha * weight_a + (1.0 - alpha) * weight_b

    assert np.all(np.isfinite(normalized))
    assert np.all(normalized >= 0.0)
    np.testing.assert_allclose(
        normalized @ mixed,
        alpha * (normalized @ weight_a) + (1.0 - alpha) * (normalized @ weight_b),
        rtol=0.0,
        atol=1e-12,
    )


def test_robust_margin_master_rejects_negative_atom_coefficients() -> None:
    normalized_atoms = np.ones((1, 2, len(DP_CAMP_ATOM_NAMES_V10)), dtype=np.float64)
    normalized_atoms[0, 1, 0] = -0.1
    feasible_mask = np.array([[True, True]], dtype=bool)
    oracle_indices = np.array([0], dtype=np.int64)
    margins = np.zeros((1, 2), dtype=np.float64)

    with pytest.raises(ValueError, match="nonnegative cost features"):
        solve_robust_margin_cutting_plane(
            normalized_atoms,
            oracle_indices,
            margins,
            feasible_mask,
            config=RobustMarginConfig(mode="static", max_iter=1),
        )


def test_robust_margin_master_forwards_frozen_solver_options(monkeypatch) -> None:
    cp = pytest.importorskip("cvxpy")

    observed = []
    original = cp.Problem.solve

    def recording_solve(problem, *args, **kwargs):
        observed.append(dict(kwargs))
        return original(problem, *args, **kwargs)

    monkeypatch.setattr(cp.Problem, "solve", recording_solve)
    solve_robust_margin_cutting_plane(
        np.array([[[0.0, 0.0], [1.0, 1.0]]], dtype=np.float64),
        np.array([0], dtype=np.int64),
        np.zeros((1, 2), dtype=np.float64),
        np.ones((1, 2), dtype=bool),
        config=RobustMarginConfig(
            mode="static",
            max_iter=1,
            solver_options=(("tol_feas", 1e-10),),
        ),
    )

    assert observed
    assert all(call["tol_feas"] == 1e-10 for call in observed)


def test_robust_margin_master_rejects_non_string_solver_option_key() -> None:
    with pytest.raises(ValueError, match="solver_options"):
        RobustMarginConfig(
            mode="static", solver_options=((1, 1e-10),)
        ).validate()
