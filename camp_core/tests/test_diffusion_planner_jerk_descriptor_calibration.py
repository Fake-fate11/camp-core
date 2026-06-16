from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_jerk_descriptor_calibration import (
    analyze,
    render_markdown,
)


def _outcome(index: int, *, progress: float, jerk: float, lateral: float) -> dict:
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
        "value": 0.0,
    }


def _prefix(h10: float) -> list[list[float]]:
    return [[1.0 + (h10 - 1.0) * idx / 9.0, 0.0, 0.0] for idx in range(10)]


def _rollout() -> dict:
    return {
        str(horizon): {
            "mean_vector_jerk_mps3": [2.0, 3.0, 1.0],
            "max_vector_jerk_mps3": [2.5, 3.5, 1.5],
            "mean_lateral_acceleration_mps2": [0.5, 0.6, 0.4],
            "max_lateral_acceleration_mps2": [0.7, 0.8, 0.6],
            "distance_m": [10.0, 9.95, 9.96],
        }
        for horizon in (3, 5, 10)
    }


def _record() -> dict:
    return {
        "num_candidates": 3,
        "selected_index": 0,
        "feasible_mask": [True, True, True],
        "candidate_closed_loop_outcomes": [
            _outcome(0, progress=10.0, jerk=5.0, lateral=2.0),
            _outcome(1, progress=9.95, jerk=6.0, lateral=1.0),
            _outcome(2, progress=9.96, jerk=4.0, lateral=1.2),
        ],
        "selection_scores": [0.0, 1.0, 2.0],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0, 0.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.0, 0.0],
        "candidate_route_progress": None,
        "dp_candidate_rewards": [
            {"progress": 10.0},
            {"progress": 9.95},
            {"progress": 9.96},
        ],
        "candidate_step_reach": [1.0, 0.95, 0.96],
        "candidate_perfect_tracker_target_speed_mps": [5.0, 4.95, 4.96],
        "candidate_perfect_tracker_postprocessed_reference_prefix": [
            _prefix(10.0),
            _prefix(9.95),
            _prefix(9.96),
        ],
        "candidate_horizon_lateral_acceleration_cost": [2.0, 0.5, 0.8],
        "candidate_dp_prior_jerk_excess_cost": [1.0, 0.5, 0.5],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [2.0, 3.0, 1.0],
        "candidate_perfect_tracker_open_loop_rollout": _rollout(),
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


def test_jerk_descriptor_calibration_scores_failure_tick_candidates(tmp_path) -> None:
    report = analyze(
        [_write_log(tmp_path, [_record()])],
        label="unit",
        screen_names=("balanced_lateral_jerk_nondegrading",),
    )
    screen = _screen(report, "balanced_lateral_jerk_nondegrading")
    failure_group = screen["groups"]["failure_tick_admissible"]

    assert failure_group["records"]["candidate_rows"] == 2
    assert failure_group["records"]["posterior_jerk_improvements"] == 1
    assert screen["calibration_gate_pass"] is True

    tracker = failure_group["features"]["tracker_command_jerk_mps3"]
    assert tracker["auc"]["posterior_jerk_improvement"] == pytest.approx(1.0)
    assert tracker["nonworse_rule"]["posterior_jerk_improvement"][
        "precision"
    ] == pytest.approx(1.0)
    assert tracker["nonworse_rule"]["posterior_joint_comfort_success"][
        "recall"
    ] == pytest.approx(1.0)

    raw = failure_group["features"]["raw_jerk"]
    assert raw["auc"]["posterior_jerk_improvement"] == pytest.approx(0.5)
    h5_rollout = failure_group["features"]["rollout_h5_mean_vector_jerk_mps3"]
    assert h5_rollout["auc"]["posterior_jerk_improvement"] == pytest.approx(1.0)

    markdown = render_markdown(report)
    assert "Jerk Descriptor Calibration" in markdown
    assert "tracker_command_jerk_mps3" in markdown
