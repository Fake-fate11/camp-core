from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_materiality_gap import analyze


def _outcome(
    index: int,
    *,
    progress: float,
    jerk: float,
    lateral: float,
    value: float = 0.0,
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
        "feasible": not red,
        "value": value,
    }


def _prefix(offset_y: float) -> list[list[float]]:
    return [[float(idx + 1), offset_y * idx, 0.0] for idx in range(10)]


def _rollout(values: list[float]) -> dict:
    return {
        str(horizon): {
            "distance_m": values,
            "mean_vector_jerk_mps3": values,
            "max_vector_jerk_mps3": values,
            "mean_lateral_acceleration_mps2": values,
            "max_lateral_acceleration_mps2": values,
        }
        for horizon in (3, 5, 10)
    }


def _record() -> dict:
    return {
        "num_candidates": 3,
        "selected_index": 0,
        "feasible_mask": [True, True, True],
        "candidate_closed_loop_outcomes": [
            _outcome(0, progress=10.0, jerk=5.0, lateral=2.0, value=1.0),
            _outcome(1, progress=9.8, jerk=3.0, lateral=1.0, value=2.0),
            _outcome(2, progress=10.0, jerk=1.0, lateral=0.5, red=True),
        ],
        "candidate_route_progress": [10.0, 9.8, 10.0],
        "candidate_step_reach": [1.0, 0.8, 1.0],
        "candidate_dp_prior_jerk_excess_cost": [4.0, 2.0, 1.0],
        "candidate_dp_prior_lateral_acceleration_excess_cost": [3.0, 1.0, 1.0],
        "candidate_horizon_lateral_acceleration_cost": [2.0, 1.0, 1.0],
        "candidate_horizon_yaw_rate_cost": [0.5, 0.4, 0.3],
        "candidate_perfect_tracker_first_step_reach_m": [1.0, 0.8, 1.0],
        "candidate_perfect_tracker_tail_average_speed_mps": [4.0, 3.0, 4.0],
        "candidate_perfect_tracker_target_speed_mps": [4.0, 3.0, 4.0],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [8.0, 9.0, 2.0],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [
            1.0,
            1.5,
            0.1,
        ],
        "candidate_perfect_tracker_yaw_rate_magnitude_rps": [0.5, 0.6, 0.1],
        "candidate_perfect_tracker_postprocessed_reference_prefix": [
            _prefix(0.0),
            _prefix(0.01),
            _prefix(0.0),
        ],
        "candidate_perfect_tracker_open_loop_rollout": _rollout([5.0, 4.0, 3.0]),
    }


def _write_log(tmp_path, records: list[dict]):
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_materiality_gap_reports_layer_deltas(tmp_path) -> None:
    report = analyze([_write_log(tmp_path, [_record()])], label="unit")

    assert report["records"]["with_oracle_donor"] == 1
    assert report["summary"]["outcome_jerk_delta_mps3"]["mean"] == pytest.approx(-2.0)
    assert report["summary"]["raw_dp_prior_jerk_excess_delta"]["mean"] == pytest.approx(-2.0)
    assert report["summary"]["tracker_command_jerk_delta_mps3"]["mean"] == pytest.approx(1.0)
    assert report["summary"]["rollout_h3_mean_vector_jerk_mps3_delta"]["mean"] == pytest.approx(-1.0)
    assert report["rates"]["raw_jerk_proxy_improvement_rate"] == 1.0
    assert report["rates"]["tracker_jerk_proxy_improvement_rate"] == 0.0


def test_materiality_gap_ignores_safety_regressing_donor(tmp_path) -> None:
    record = _record()
    record["candidate_closed_loop_outcomes"][1]["red_light_violation"] = True
    record["candidate_closed_loop_outcomes"][1]["feasible"] = False

    report = analyze([_write_log(tmp_path, [record])], label="unit")

    assert report["records"]["with_oracle_donor"] == 0
    assert report["records"]["without_oracle_donor"] == 1
