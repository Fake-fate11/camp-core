from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_tracker_branch_attribution import (
    compute_tracker_branch_attribution,
)


def test_tracker_branch_attribution_reports_matched_change(tmp_path) -> None:
    baseline_root, variant_root = _write_pair(tmp_path)

    report = compute_tracker_branch_attribution(
        baseline_root,
        variant_root,
        horizons=(3, 5),
    )

    assert report["pairing"] == {
        "runs": 1,
        "total_steps": 6,
        "changed_runs": 1,
        "changed_records": 1,
    }
    assert report["event_prestate"]["matched_records"] == 1
    assert report["immediate_candidate_deltas"]["command_jerk"]["mean"] == -1.0
    assert report["immediate_candidate_deltas"]["horizon_jerk"]["mean"] == 1.0
    assert report["planned_red_status_differences"]["variant_extra"] == 1
    assert report["planned_red_status_differences"]["variant_extra_lags"] == {
        "0": 1
    }
    assert report["window_responses"]["3"]["distance_delta_m"]["mean"] > 0.0


def test_tracker_branch_attribution_rejects_candidate_outcomes(tmp_path) -> None:
    baseline_root, variant_root = _write_pair(tmp_path)
    log_path = next(variant_root.rglob("camp_selection_log.json"))
    records = json.loads(log_path.read_text(encoding="utf-8"))
    records[0]["candidate_closed_loop_outcomes"] = [{}, {}]
    log_path.write_text(json.dumps(records), encoding="utf-8")

    with pytest.raises(ValueError, match="closed-loop outcomes"):
        compute_tracker_branch_attribution(baseline_root, variant_root)


def _write_pair(tmp_path):
    baseline_root = tmp_path / "baseline"
    variant_root = tmp_path / "variant"
    relative = (
        "sample59_86/seed_1/npc_0/spawn_0p3/tl_on/static"
    )
    baseline_dir = baseline_root / relative
    variant_dir = variant_root / relative
    baseline_dir.mkdir(parents=True)
    variant_dir.mkdir(parents=True)

    benchmark = {
        "route": "/route.pkl",
        "seed": 1,
        "steps": 6,
        "max_npcs": 0,
        "spawn_probability": 0.3,
        "traffic_lights": True,
        "advance_mode": "perfect",
    }
    (baseline_dir / "camp_validation_summary.json").write_text(
        json.dumps({"benchmark": benchmark, "advance_mode": "perfect"}),
        encoding="utf-8",
    )
    (variant_dir / "camp_validation_summary.json").write_text(
        json.dumps(
            {
                "benchmark": benchmark,
                "advance_mode": "perfect",
                "camp_perfect_tracker_command_postselection": {
                    "enabled": True,
                    "selection_effect": True,
                },
                "camp_shadow_perfect_tracker_command": {},
            }
        ),
        encoding="utf-8",
    )

    baseline_selection = []
    variant_selection = []
    variant_speeds = [1.0, 1.0, 3.0, 3.0, 3.0, 3.0]
    for step in range(6):
        baseline_selection.append(
            {
                "selected_index": 0,
                "feasible_mask": [True, True],
                "dp_scene_features": [0.0, 0.0],
            }
        )
        changed = step == 1
        selected = 1 if changed else 0
        next_speed = variant_speeds[min(step + 1, 5)]
        variant_selection.append(
            {
                "selected_index": selected,
                "camp_selected_index_before_tracker_postselection": 0,
                "perfect_tracker_command_postselection": {
                    "changed": changed,
                },
                "candidate_closed_loop_outcomes": None,
                "feasible_mask": [True, True],
                "dp_scene_features": [0.0, 0.0],
                "dp_candidate_rewards": [
                    {"progress": 1.0, "red_light": 0.0},
                    {"progress": 1.1, "red_light": 0.0},
                ],
                "candidate_perfect_tracker_target_speed_mps": [
                    next_speed,
                    next_speed,
                ],
                "candidate_first_reference_heading_rad": [0.0, 0.0],
                "candidate_perfect_tracker_jerk_magnitude_mps3": [5.0, 4.0],
                "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [
                    0.5,
                    0.4,
                ],
                "candidate_dp_prior_jerk_excess_cost": [1.0, 2.0],
                "candidate_horizon_lateral_acceleration_cost": [1.0, 2.0],
            }
        )
    (baseline_dir / "camp_selection_log.json").write_text(
        json.dumps(baseline_selection),
        encoding="utf-8",
    )
    (variant_dir / "camp_selection_log.json").write_text(
        json.dumps(variant_selection),
        encoding="utf-8",
    )

    baseline_trajectory = [
        {
            "step": step,
            "x": step * 0.1,
            "y": 0.0,
            "heading": 0.0,
            "speed": 1.0,
            "goal_d": 10.0 - step * 0.1,
        }
        for step in range(6)
    ]
    variant_x = [0.0, 0.1, 0.4, 0.7, 1.0, 1.3]
    variant_trajectory = [
        {
            "step": step,
            "x": variant_x[step],
            "y": 0.0,
            "heading": 0.0,
            "speed": variant_speeds[step],
            "goal_d": 10.0 - variant_x[step],
        }
        for step in range(6)
    ]
    (baseline_dir / "trajectory_log.json").write_text(
        json.dumps(baseline_trajectory),
        encoding="utf-8",
    )
    (variant_dir / "trajectory_log.json").write_text(
        json.dumps(variant_trajectory),
        encoding="utf-8",
    )

    baseline_metrics = [
        {"pred_red_light": 0.0} for _ in range(6)
    ]
    variant_metrics = [
        {"pred_red_light": -1.0 if step == 1 else 0.0}
        for step in range(6)
    ]
    (baseline_dir / "camp_metric_log.json").write_text(
        json.dumps(baseline_metrics),
        encoding="utf-8",
    )
    (variant_dir / "camp_metric_log.json").write_text(
        json.dumps(variant_metrics),
        encoding="utf-8",
    )
    return baseline_root, variant_root
