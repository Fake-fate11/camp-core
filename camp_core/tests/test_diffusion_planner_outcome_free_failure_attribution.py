from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_outcome_free_failure_attribution import (
    analyze,
    render_markdown,
)


def _outcome(
    index: int,
    *,
    progress: float,
    jerk: float,
    lateral: float,
    value: float = 0.0,
) -> dict:
    return {
        "candidate_index": index,
        "progress_m": progress,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
        "feasible": True,
        "value": value,
    }


def _prefix(h10: float) -> list[list[float]]:
    return [[1.0 + (h10 - 1.0) * idx / 9.0, 0.0, 0.0] for idx in range(10)]


def _rollout(values: list[float]) -> dict:
    return {
        str(horizon): {
            "mean_vector_jerk_mps3": values,
            "max_vector_jerk_mps3": values,
            "mean_lateral_acceleration_mps2": values,
            "max_lateral_acceleration_mps2": values,
            "distance_m": [10.0, 9.95],
        }
        for horizon in (3, 5, 10)
    }


def _record(*, candidate_jerk_outcome: float, tracker_jerk: list[float]) -> dict:
    return {
        "num_candidates": 2,
        "selected_index": 0,
        "feasible_mask": [True, True],
        "candidate_closed_loop_outcomes": [
            _outcome(0, progress=10.0, jerk=5.0, lateral=2.0),
            _outcome(1, progress=9.95, jerk=candidate_jerk_outcome, lateral=1.0),
        ],
        "selection_scores": [0.0, 1.0],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.0],
        "candidate_route_progress": None,
        "dp_candidate_rewards": [{"progress": 10.0}, {"progress": 9.95}],
        "candidate_step_reach": [1.0, 0.95],
        "candidate_perfect_tracker_target_speed_mps": [5.0, 4.95],
        "candidate_perfect_tracker_postprocessed_reference_prefix": [
            _prefix(10.0),
            _prefix(9.95),
        ],
        "candidate_horizon_lateral_acceleration_cost": [2.0, 1.0],
        "candidate_dp_prior_jerk_excess_cost": [1.0, 0.5],
        "candidate_dp_prior_lateral_acceleration_excess_cost": [2.0, 1.0],
        "candidate_dp_prior_acceleration_excess_cost": [2.0, 1.0],
        "candidate_dp_prior_deviation_cost": [2.0, 1.0],
        "candidate_dp_prior_yaw_rate_excess_cost": [2.0, 1.0],
        "candidate_horizon_yaw_rate_cost": [2.0, 1.0],
        "candidate_perfect_tracker_jerk_magnitude_mps3": tracker_jerk,
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [2.0, 1.0],
        "candidate_perfect_tracker_yaw_rate_magnitude_rps": [2.0, 1.0],
        "candidate_perfect_tracker_acceleration_mps2": [2.0, 1.0],
        "candidate_perfect_tracker_tail_average_speed_mps": [5.0, 4.95],
        "candidate_perfect_tracker_open_loop_rollout": _rollout(tracker_jerk),
    }


def _write_log(tmp_path, records: list[dict]):
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def _screen(report: dict, name: str) -> dict:
    for screen in report["screens"]:
        if screen["name"] == name:
            return screen
    raise AssertionError(f"missing screen {name}")


def test_failure_attribution_reports_single_guard_separation(tmp_path) -> None:
    log_path = _write_log(
        tmp_path,
        [
            _record(candidate_jerk_outcome=4.0, tracker_jerk=[2.0, 1.0]),
            _record(candidate_jerk_outcome=6.0, tracker_jerk=[2.0, 3.0]),
        ],
    )

    report = analyze(
        [log_path],
        label="unit",
        screen_names=("balanced_lateral_jerk_nondegrading",),
    )
    screen = _screen(report, "balanced_lateral_jerk_nondegrading")

    assert screen["records"]["changed"] == 2
    assert screen["records"]["posterior_joint_comfort_success"] == 1
    assert screen["records"]["posterior_joint_comfort_failure"] == 1
    assert screen["failure_modes"]["jerk_not_improved"] == 1

    guards = {item["feature"]: item for item in screen["single_nonworse_guards"]}
    jerk_guard = guards["tracker_command_jerk_delta_mps3"]
    assert jerk_guard["kept_success"] == 1
    assert jerk_guard["kept_failure"] == 0
    assert jerk_guard["failure_removal_rate"] == pytest.approx(1.0)
    assert jerk_guard["success_keep_rate"] == pytest.approx(1.0)

    markdown = render_markdown(report)
    assert "Outcome-Free Failure Attribution" in markdown
    assert "tracker_command_jerk_delta_mps3" in markdown
