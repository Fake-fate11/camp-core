from __future__ import annotations

import numpy as np

from scripts.integrations.analyze_diffusion_planner_splice_recompute_gate import (
    _donor_indices,
    build_splice_candidates,
    h10_preserving_tail_splice_xy,
    heading_features_from_xy,
)


def _candidate(end_x: float, end_y: float, *, steps: int = 8) -> np.ndarray:
    traj = np.zeros((steps, 4), dtype=np.float64)
    for step in range(steps):
        ratio = float(step + 1) / float(steps)
        traj[step, 0] = end_x * ratio
        traj[step, 1] = end_y * ratio
    traj[:, 2:4] = heading_features_from_xy(traj[:, :2])
    return traj


def test_h10_preserving_tail_splice_keeps_anchor_prefix() -> None:
    selected = _candidate(8.0, 0.0)[:, :2]
    donor = _candidate(4.0, 4.0)[:, :2]

    splice = h10_preserving_tail_splice_xy(
        selected,
        donor,
        anchor_steps=4,
        blend_steps=0,
    )

    np.testing.assert_allclose(splice[:4], selected[:4])
    donor_tail = selected[3] + (donor - donor[3])
    np.testing.assert_allclose(splice[4:], donor_tail[4:])


def test_build_splice_candidates_reconstructs_unit_heading() -> None:
    candidates = np.stack(
        [
            _candidate(8.0, 0.0),
            _candidate(4.0, 4.0),
            _candidate(5.0, -3.0),
        ]
    )

    splices = build_splice_candidates(
        candidates,
        selected_index=0,
        donor_indices=np.array([1, 2], dtype=np.int64),
        anchor_steps=4,
        blend_steps=2,
    )

    assert splices.shape == (2, 8, 4)
    expected_prefix = np.broadcast_to(candidates[0, :4, :2], (2, 4, 2))
    np.testing.assert_allclose(splices[:, :4, :2], expected_prefix)
    heading_norms = np.linalg.norm(splices[:, :, 2:4], axis=2)
    np.testing.assert_allclose(heading_norms, 1.0, atol=1e-12)


def test_donor_indices_use_logged_union_red() -> None:
    arrays = {
        "candidate_planned_red_light_cost": np.array([0.0, 0.0, 1.0, 0.0]),
        "candidate_full_horizon_planned_red_light_cost": np.array([5.0, 3.0, 0.0, 7.0]),
    }
    metadata = {"selected_index": 0}

    donors = _donor_indices(
        arrays,
        metadata,
        "lower_logged_union_red",
        count=4,
    )

    np.testing.assert_array_equal(donors, np.array([1, 2], dtype=np.int64))


def test_donor_indices_all_nonselected_smoke_pool() -> None:
    donors = _donor_indices(
        {},
        {"selected_index": 1},
        "all_nonselected",
        count=4,
    )

    np.testing.assert_array_equal(donors, np.array([0, 2, 3], dtype=np.int64))
