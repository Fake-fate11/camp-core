from __future__ import annotations

import numpy as np

from scripts.integrations.analyze_diffusion_planner_world_frame_bridge_screen import (
    REJECT_STATUS,
    READY_STATUS,
    WorldFrameBridgeConfig,
    build_world_frame_bridge_candidates,
    render_markdown,
    tracker_budget_sensitivity,
    world_frame_donor_tail_bridge_heading,
    world_frame_donor_tail_bridge_xy,
    _decision,
)


def _trajectory(end_x: float, end_y: float, *, steps: int = 8) -> np.ndarray:
    traj = np.zeros((steps, 4), dtype=np.float64)
    for step in range(steps):
        ratio = float(step + 1) / float(steps)
        traj[step, 0] = end_x * ratio
        traj[step, 1] = end_y * ratio
    headings = np.diff(traj[:, :2], axis=0, prepend=np.zeros((1, 2)))
    norms = np.linalg.norm(headings, axis=1, keepdims=True)
    valid = norms[:, 0] > 1e-12
    traj[valid, 2:4] = headings[valid] / norms[valid]
    traj[~valid, 2] = 1.0
    return traj


def _heading(angles: np.ndarray) -> np.ndarray:
    return np.stack((np.cos(angles), np.sin(angles)), axis=1)


def test_world_frame_bridge_preserves_selected_prefix_and_absolute_donor_tail() -> None:
    selected = _trajectory(8.0, 0.0)[:, :2]
    donor = _trajectory(100.0, 40.0)[:, :2]

    bridge = world_frame_donor_tail_bridge_xy(
        selected,
        donor,
        preserve_steps=2,
        bridge_steps=3,
    )

    np.testing.assert_allclose(bridge[:2], selected[:2])
    np.testing.assert_allclose(bridge[4:], donor[4:])
    assert not np.allclose(bridge[4:], selected[1] + (donor - donor[1])[4:])
    assert np.linalg.norm(bridge[2] - donor[2]) < np.linalg.norm(selected[2] - donor[2])


def test_world_frame_bridge_heading_preserves_donor_tail_heading() -> None:
    selected_angles = np.linspace(0.1, 0.5, 8, dtype=np.float64)
    donor_angles = np.linspace(-0.7, 1.0, 8, dtype=np.float64)

    bridge = world_frame_donor_tail_bridge_heading(
        _heading(selected_angles),
        _heading(donor_angles),
        preserve_steps=2,
        bridge_steps=3,
    )

    np.testing.assert_allclose(bridge[:2], _heading(selected_angles[:2]))
    np.testing.assert_allclose(bridge[4:], _heading(donor_angles[4:]), atol=1e-12)
    np.testing.assert_allclose(np.linalg.norm(bridge, axis=1), 1.0, atol=1e-12)


def test_build_world_frame_bridge_candidates_skips_selected_donor() -> None:
    candidates = np.stack(
        [
            _trajectory(8.0, 0.0),
            _trajectory(100.0, 40.0),
            _trajectory(50.0, -10.0),
        ]
    )

    transformed = build_world_frame_bridge_candidates(
        candidates,
        selected_index=0,
        donor_indices=np.array([0, 2], dtype=np.int64),
        preserve_steps=1,
        bridge_steps=0,
    )

    assert transformed.shape == (1, 8, 4)
    np.testing.assert_allclose(transformed[0, :1], candidates[0, :1])
    np.testing.assert_allclose(transformed[0, 1:], candidates[2, 1:])


def test_tracker_budget_sensitivity_requires_lower_red_hard_feasible_and_comfort() -> None:
    config = WorldFrameBridgeConfig(
        progress_loss_budgets_m=(0.5, 1.0),
        smoothness_loss_budgets=(0.5,),
        command_jerk_worse_budget_mps3=0.2,
        command_lateral_worse_budget_mps2=0.2,
        rollout_distance_loss_budget_m=0.2,
        rollout_jerk_worse_budget_mps3=0.2,
        rollout_lateral_worse_budget_mps2=0.2,
    )

    rows = tracker_budget_sensitivity(
        union_red=np.array([0.0, 0.0, 2.0, 0.0]),
        progress=np.array([9.8, 9.0, 10.0, 9.9]),
        smoothness=np.array([0.8, 0.8, 0.8, 0.4]),
        hard_feasible=np.array([True, True, True, False]),
        tracker={
            "command_jerk_mps3": np.array([1.1, 1.1, 1.0, 1.0]),
            "command_lateral_mps2": np.array([0.6, 0.6, 0.5, 0.5]),
            "rollout_distance_m": np.array([2.95, 2.85, 3.0, 3.0]),
            "rollout_jerk_mps3": np.array([2.1, 2.1, 2.0, 2.0]),
            "rollout_lateral_mps2": np.array([0.9, 0.9, 0.8, 0.8]),
        },
        selected_union_red=1.0,
        selected_progress=10.0,
        selected_smoothness=1.0,
        selected_tracker={
            "command_jerk_mps3": 1.0,
            "command_lateral_mps2": 0.5,
            "rollout_distance_m": 3.0,
            "rollout_jerk_mps3": 2.0,
            "rollout_lateral_mps2": 0.8,
        },
        config=config,
    )

    by_budget = {row["progress_loss_budget_m"]: row for row in rows}
    assert by_budget[0.5]["count"] == 1
    assert by_budget[0.5]["has_candidate"] is True
    assert by_budget[1.0]["count"] == 2
    assert np.isclose(by_budget[1.0]["max_rollout_distance_loss_m"], 0.15)


def test_decision_and_markdown_never_authorize_replay_or_training() -> None:
    decision = _decision(
        {
            "hard_feasible_snapshot_support_pass": True,
            "comfort_admissible_snapshot_support_pass": True,
            "has_lower_union_red_hard_feasible_candidates": True,
            "has_comfort_admissible_candidates": True,
        }
    )

    assert decision["status"] == READY_STATUS
    assert decision["full36_authorized"] is False
    assert decision["camp_retraining_authorized"] is False

    rejected = _decision(
        {
            "hard_feasible_snapshot_support_pass": True,
            "comfort_admissible_snapshot_support_pass": False,
            "has_lower_union_red_hard_feasible_candidates": True,
            "has_comfort_admissible_candidates": False,
        }
    )
    assert rejected["status"] == REJECT_STATUS

    markdown = render_markdown(
        {
            "analysis": {"math_boundary": "finite candidate boundary"},
            "config": {
                "preserve_steps": 1,
                "bridge_steps": 10,
                "heading_mode": "world_donor_tail",
                "donor_pool": "lower_logged_union_red",
                "rollout_horizon": 3,
            },
            "snapshots": {"count": 1, "with_donors": 1},
            "transformed": {
                "lower_union_red_count": 1,
                "lower_union_red_hard_feasible_count": 1,
                "lower_union_red_progress_feasible_count": 1,
                "comfort_admissible_count": 1,
                "lower_union_red_hard_infeasibility_reason_counts": {},
                "budget_sensitivity": [],
            },
            "support_gate": {
                "hard_feasible_snapshot_support_rate": 1.0,
                "comfort_admissible_snapshot_support_rate": 1.0,
            },
            "latency_ms": {
                key: {"mean": 1.0, "p95": 1.0, "max": 1.0}
                for key in (
                    "baseline_reward",
                    "baseline_tracker",
                    "transform_build",
                    "transformed_reward",
                    "transformed_tracker",
                    "total",
                )
            },
            "shadow_rule": {
                "enabled": False,
                "selection_effect": False,
                "changed_snapshots": 0,
                "reason_counts": {},
            },
            "final_decision": decision,
        }
    )
    assert "not replay" in markdown
    assert "finite candidate boundary" in markdown
