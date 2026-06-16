from __future__ import annotations

import numpy as np

from scripts.integrations.analyze_diffusion_planner_splice_recompute_gate import (
    _donor_indices,
    build_splice_candidates,
    h10_preserving_heading_splice,
    h10_preserving_tail_splice_xy,
    heading_features_from_xy,
    reason_counts,
    reward_budget_sensitivity,
    reward_hard_feasibility,
    reward_metric_vector,
    reward_progress_screen,
)


def _candidate(end_x: float, end_y: float, *, steps: int = 8) -> np.ndarray:
    traj = np.zeros((steps, 4), dtype=np.float64)
    for step in range(steps):
        ratio = float(step + 1) / float(steps)
        traj[step, 0] = end_x * ratio
        traj[step, 1] = end_y * ratio
    traj[:, 2:4] = heading_features_from_xy(traj[:, :2])
    return traj


def _heading_from_angles(angles: np.ndarray) -> np.ndarray:
    return np.stack((np.cos(angles), np.sin(angles)), axis=1)


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


def test_h10_preserving_heading_splice_keeps_anchor_and_offsets_tail() -> None:
    selected_angles = np.linspace(0.1, 0.4, 8, dtype=np.float64)
    donor_angles = np.linspace(-0.5, 0.7, 8, dtype=np.float64)
    selected = _heading_from_angles(selected_angles)
    donor = _heading_from_angles(donor_angles)

    splice = h10_preserving_heading_splice(
        selected,
        donor,
        anchor_steps=4,
        blend_steps=2,
    )

    np.testing.assert_allclose(splice[:4], selected[:4], atol=1e-12)
    np.testing.assert_allclose(np.linalg.norm(splice, axis=1), 1.0, atol=1e-12)
    expected_tail = selected_angles[3] + (donor_angles - donor_angles[3])
    expected_tail_heading = _heading_from_angles(expected_tail)
    np.testing.assert_allclose(splice[5:], expected_tail_heading[5:], atol=1e-12)


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


def test_build_splice_candidates_can_use_donor_offset_heading_mode() -> None:
    candidates = np.stack(
        [
            _candidate(8.0, 0.0),
            _candidate(4.0, 4.0),
        ]
    )
    candidates[0, :, 2:4] = _heading_from_angles(
        np.linspace(0.1, 0.4, 8, dtype=np.float64)
    )
    candidates[1, :, 2:4] = _heading_from_angles(
        np.linspace(-0.5, 0.7, 8, dtype=np.float64)
    )

    splices = build_splice_candidates(
        candidates,
        selected_index=0,
        donor_indices=np.array([1], dtype=np.int64),
        anchor_steps=4,
        blend_steps=2,
        heading_mode="donor_offset",
    )

    np.testing.assert_allclose(splices[0, :4, 2:4], candidates[0, :4, 2:4])
    np.testing.assert_allclose(
        np.linalg.norm(splices[0, :, 2:4], axis=1),
        1.0,
        atol=1e-12,
    )


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


def test_reward_hard_feasibility_matches_replay_red_and_lane_checks() -> None:
    feasible, reasons = reward_hard_feasibility(
        [
            {"red_light": 0.0, "progress": 10.0},
            {"red_light": -1.0, "progress": 9.0},
            {"lane_crossing": True, "red_light": 0.0, "progress": 8.0},
        ]
    )

    np.testing.assert_array_equal(feasible, np.array([True, False, False]))
    assert reasons[1] == ("dp_red_light",)
    assert reasons[2] == ("dp_lane_crossing",)


def test_reward_progress_screen_is_separate_from_hard_feasibility() -> None:
    hard = np.array([True, True, False])
    feasible, reasons = reward_progress_screen(
        [
            {"progress": 10.0},
            {"progress": 6.0},
            {"progress": 100.0},
        ],
        hard,
        min_progress_ratio=0.8,
    )

    np.testing.assert_array_equal(feasible, np.array([True, False, False]))
    assert reasons[1] == ("dp_underprogress",)
    assert reasons[2] == ()


def test_reward_metric_vector_requires_finite_values() -> None:
    values = reward_metric_vector(
        [{"progress": 1.0}, {"progress": 2.5}],
        "progress",
    )

    np.testing.assert_allclose(values, np.array([1.0, 2.5]))


def test_reward_budget_sensitivity_counts_budgeted_lower_red_candidates() -> None:
    rows = reward_budget_sensitivity(
        progress=np.array([9.8, 9.0, 8.0]),
        smoothness=np.array([0.9, 0.0, 0.9]),
        lower_union=np.array([True, True, True]),
        hard_feasible=np.array([True, True, False]),
        selected_progress=10.0,
        selected_smoothness=1.0,
        progress_loss_budgets_m=(0.5, 1.5),
        smoothness_loss_budgets=(0.2, 1.2),
    )

    by_budget = {
        (row["progress_loss_budget_m"], row["smoothness_loss_budget"]): row
        for row in rows
    }
    assert by_budget[(0.5, 0.2)]["count"] == 1
    assert by_budget[(0.5, 0.2)]["has_candidate"] is True
    assert by_budget[(0.5, 1.2)]["count"] == 1
    assert by_budget[(1.5, 0.2)]["count"] == 1
    assert by_budget[(1.5, 1.2)]["count"] == 2
    assert np.isclose(by_budget[(1.5, 1.2)]["min_progress_loss_m"], 0.2)


def test_reason_counts_can_be_masked() -> None:
    counts = reason_counts(
        (
            ("dp_lane_crossing", "dp_red_light"),
            ("dp_lane_crossing",),
            ("dp_kinematic",),
        ),
        np.array([True, False, True]),
    )

    assert counts == {"dp_kinematic": 1, "dp_lane_crossing": 1, "dp_red_light": 1}
