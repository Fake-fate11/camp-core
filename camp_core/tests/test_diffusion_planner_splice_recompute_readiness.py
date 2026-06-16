from __future__ import annotations

import json

import numpy as np

from scripts.integrations.analyze_diffusion_planner_splice_recompute_readiness import (
    analyze,
    render_markdown,
)


def _prefix(end_x: float, end_y: float, *, steps: int = 12) -> list[list[float]]:
    rows = []
    for step in range(steps):
        ratio = float(step + 1) / float(steps)
        rows.append([end_x * ratio, end_y * ratio, 0.0, 1.0])
    return rows


def _selection_record() -> dict:
    atoms = [[0.0, 1.0], [1.0, 0.0]]
    return {
        "num_candidates": 2,
        "selected_index": 0,
        "feasible_mask": [True, True],
        "candidate_raw_trajectory_prefix": [
            _prefix(12.0, 0.0),
            _prefix(9.0, -3.0),
        ],
        "candidate_planned_red_light_cost": [0.0, 0.0],
        "candidate_full_horizon_planned_red_light_cost": [5.0, 1.0],
        "atoms": atoms,
        "normalized_atoms": atoms,
        "selection_scores": [0.0, 1.0],
        "selection_weights": [0.5, 0.5],
        "infeasibility_reasons": [[], []],
        "perfect_tracker_command_inputs": {
            "dt": 0.1,
            "current_speed_mps": 1.0,
            "current_longitudinal_acceleration_mps2": 0.0,
        },
        "perfect_tracker_open_loop_rollout_inputs": {
            "current_acceleration_ego_xy": [0.0, 0.0],
        },
        "perfect_tracker_candidate_preprocessing": {
            "source": "scenario_generation.mpc_tracker.postprocess_reference",
            "sg_smooth_enabled": True,
            "sg_filter_window": 11,
            "sg_filter_order": 3,
        },
    }


def test_readiness_fails_closed_without_reward_tensor_context(tmp_path) -> None:
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps([_selection_record()]), encoding="utf-8")

    report = analyze([path])

    assert report["selection_logs"]["selected_h30_safe_full_red_records"] == 1
    stages = report["selection_logs"]["stages"]
    assert stages["raw_splice_geometry_from_selection_log"]["target_ready_count"] == 1
    assert (
        stages["perfect_tracker_splice_recompute_from_selection_log"][
            "target_ready_count"
        ]
        == 1
    )
    assert (
        stages["red_stopping_margin_splice_recompute_from_selection_log"][
            "target_ready_count"
        ]
        == 0
    )
    assert (
        stages["dp_reward_red_recompute_from_selection_log"]["target_ready_count"]
        == 0
    )
    assert not report["gate"]["can_recompute_splice_red_feasibility_from_selection_logs"]
    assert not report["gate"]["can_recompute_splice_red_feasibility_from_snapshots"]
    assert "Fail-closed" in report["gate"]["decision"]
    assert (
        stages["dp_reward_red_recompute_from_selection_log"][
            "target_missing_counts"
        ]["reward_input__route_lanes"]
        == 1
    )

    markdown = render_markdown(report)
    assert "Stop-Aware Splice Recompute Readiness Audit" in markdown
    assert "Fail-closed" in markdown


def test_readiness_accepts_complete_snapshot_tensor_contract(tmp_path) -> None:
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps([_selection_record()]), encoding="utf-8")
    snapshot = tmp_path / "camp_microbenchmark_step_0000.npz"
    metadata = {
        "current_speed_mps": 1.0,
        "current_longitudinal_acceleration_mps2": 0.0,
        "reward_horizon_steps": 10,
        "sg_smooth_enabled": True,
        "sg_filter_window": 11,
        "sg_filter_order": 3,
    }
    np.savez_compressed(
        snapshot,
        metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)),
        candidates=np.zeros((2, 12, 4), dtype=np.float32),
        current_acceleration_ego_xy=np.zeros(2, dtype=np.float32),
        red_route_points=np.zeros((3, 2), dtype=np.float32),
        reward_input__lanes=np.zeros((1, 2, 3, 4), dtype=np.float32),
        reward_input__route_lanes=np.zeros((1, 2, 3, 4), dtype=np.float32),
        reward_input__line_strings=np.zeros((1, 2, 3, 4), dtype=np.float32),
        reward_input__ego_shape=np.zeros((1, 4), dtype=np.float32),
        reward_input__neighbor_agents_future=np.zeros((1, 1, 12, 4), dtype=np.float32),
        reward_input__neighbor_agents_past=np.zeros((1, 1, 4, 4), dtype=np.float32),
        reward_input__goal_pose=np.zeros((1, 3), dtype=np.float32),
    )

    report = analyze([path], snapshot_paths=[snapshot])

    assert report["snapshots"]["files"] == 1
    assert (
        report["snapshots"]["stages"]["dp_reward_red_recompute_from_snapshot"][
            "ready_count"
        ]
        == 1
    )
    assert report["gate"]["can_recompute_splice_red_feasibility_from_snapshots"]
    assert "next step can implement" in report["gate"]["decision"]
