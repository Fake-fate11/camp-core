from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_progress_deficit_attribution import (
    analyze,
)


def _outcome(
    index: int,
    *,
    progress: float,
    jerk: float,
    lateral: float,
    red: bool = False,
) -> dict:
    return {
        "candidate_index": index,
        "progress_m": progress,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": red,
        "feasible": True,
    }


def _record() -> dict:
    outcomes = [
        _outcome(0, progress=10.0, jerk=5.0, lateral=2.0),
        _outcome(1, progress=9.8, jerk=4.0, lateral=1.0),
        _outcome(2, progress=9.95, jerk=4.5, lateral=1.5),
        _outcome(3, progress=10.0, jerk=3.0, lateral=1.0, red=True),
    ]
    return {
        "num_candidates": 4,
        "selected_index": 0,
        "feasible_mask": [True, True, True, True],
        "candidate_closed_loop_outcomes": outcomes,
        "candidate_step_reach": [1.0, 0.5, 0.8, 1.0],
        "candidate_perfect_tracker_first_step_reach_m": [1.0, 0.5, 0.8, 1.0],
        "candidate_perfect_tracker_tail_average_speed_mps": [4.0, 2.0, 3.0, 4.0],
        "candidate_perfect_tracker_target_speed_mps": [5.0, 3.0, 4.0, 5.0],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [9.0, 4.0, 5.0, 1.0],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [
            2.0,
            1.0,
            1.5,
            0.5,
        ],
        "candidate_perfect_tracker_restart_push": [False, True, False, False],
        "candidate_dp_prior_jerk_excess_cost": [3.0, 1.0, 2.0, 0.5],
        "candidate_horizon_lateral_acceleration_cost": [2.0, 1.0, 1.5, 0.5],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0, 0.0, 1.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.0, 0.0, 1.0],
        "candidate_perfect_tracker_open_loop_rollout": {
            "3": {"distance_m": [3.0, 1.5, 2.4, 3.0]},
            "5": {"distance_m": [5.0, 2.5, 4.0, 5.0]},
            "10": {"distance_m": [10.0, 5.0, 8.0, 10.0]},
        },
    }


def _write_log(tmp_path, records: list[dict]):
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_progress_deficit_attribution_chooses_min_deficit_candidate(tmp_path) -> None:
    report = analyze([_write_log(tmp_path, [_record()])], label="unit")

    assert report["records"]["with_safety_joint_comfort"] == 1
    assert report["progress_deficit_m"]["mean"] == pytest.approx(0.05)
    assert report["delta_summary"]["outcome_progress_delta_m"]["mean"] == pytest.approx(-0.05)
    assert report["delta_summary"][
        "perfect_tracker_target_speed_delta_mps"
    ]["mean"] == -1.0
    assert report["delta_summary"]["rollout_h3_distance_delta_m"]["mean"] == pytest.approx(-0.6)
    assert report["rates"]["candidate_lower_target_speed_rate"] == 1.0
    assert report["rates"]["candidate_lower_first_step_reach_rate"] == 1.0
    assert report["rates"]["candidate_lower_h3_distance_rate"] == 1.0
    assert report["rates"]["candidate_restart_push_rate"] == 0.0


def test_progress_deficit_attribution_ignores_safety_regressing_candidate(tmp_path) -> None:
    record = _record()
    record["candidate_closed_loop_outcomes"][1]["red_light_violation"] = True

    report = analyze([_write_log(tmp_path, [record])], label="unit")

    assert report["records"]["with_safety_joint_comfort"] == 1
    assert report["progress_deficit_m"]["mean"] == pytest.approx(0.05)
    assert report["delta_summary"]["outcome_jerk_delta_mps3"]["mean"] == -0.5
