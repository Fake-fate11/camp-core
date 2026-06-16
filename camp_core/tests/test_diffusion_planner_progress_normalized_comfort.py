from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_progress_normalized_comfort import (
    analyze,
)


def _record() -> dict:
    outcomes = [
        {
            "candidate_index": 0,
            "progress_m": 10.0,
            "value": 5.0,
            "mean_jerk_mps3": 4.0,
            "mean_lateral_acceleration_mps2": 2.0,
            "collision": False,
            "near_miss": False,
            "lane_violation": False,
            "red_light_violation": False,
            "feasible": True,
        },
        {
            "candidate_index": 1,
            "progress_m": 9.98,
            "value": 4.98,
            "mean_jerk_mps3": 3.5,
            "mean_lateral_acceleration_mps2": 1.0,
            "collision": False,
            "near_miss": False,
            "lane_violation": False,
            "red_light_violation": False,
            "feasible": True,
        },
        {
            "candidate_index": 2,
            "progress_m": 8.0,
            "value": 4.0,
            "mean_jerk_mps3": 1.0,
            "mean_lateral_acceleration_mps2": 0.5,
            "collision": False,
            "near_miss": False,
            "lane_violation": False,
            "red_light_violation": True,
            "feasible": True,
        },
    ]
    return {
        "num_candidates": 3,
        "selected_index": 0,
        "atom_names": ["progress_shortfall"],
        "atoms": [[0.0], [0.02], [2.0]],
        "feasible_mask": [True, True, True],
        "candidate_horizon_lateral_acceleration_cost": [2.0, 1.0, 0.5],
        "candidate_dp_prior_jerk_excess_cost": [4.0, 3.5, 1.0],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0, 1.0],
        "candidate_red_stopping_margin_cost": [0.1, 0.1, 0.0],
        "selection_scores": [0.1, 0.2, 0.0],
        "candidate_closed_loop_outcomes": outcomes,
    }


def _write_log(tmp_path, record: dict):
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps([record]), encoding="utf-8")
    return path


def test_progress_normalized_comfort_respects_progress_budget(tmp_path) -> None:
    report = analyze([_write_log(tmp_path, _record())])
    screens = {
        (screen["metric"], screen["progress_budget_m"]): screen
        for screen in report["screens"]
    }

    zero_budget = screens[("horizon_lateral", 0.0)]
    loose_budget = screens[("horizon_lateral", 0.05)]

    assert zero_budget["changed_records"] == 0
    assert loose_budget["changed_records"] == 1
    assert loose_budget["outcome_delta_mean"]["progress_m"] == pytest.approx(-0.02)
    assert loose_budget["outcome_delta_mean"][
        "mean_lateral_acceleration_mps2"
    ] == pytest.approx(-1.0)
    assert loose_budget["outcome_delta_mean"]["red_light_violation"] == 0.0


def test_progress_normalized_comfort_retains_fallback(tmp_path) -> None:
    record = _record()
    record["feasible_mask"] = [False, False, False]

    report = analyze([_write_log(tmp_path, record)])

    assert report["records"]["fallback"] == 1
    assert all(screen["changed_records"] == 0 for screen in report["screens"])


def test_progress_normalized_comfort_requires_outcomes(tmp_path) -> None:
    record = _record()
    record["candidate_closed_loop_outcomes"] = None

    with pytest.raises(ValueError, match="candidate outcomes"):
        analyze([_write_log(tmp_path, record)])
