from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_outcome_free_bounded_selector import (
    analyze,
)


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


def _prefix(h10: float) -> list[list[float]]:
    return [[1.0 + (h10 - 1.0) * idx / 9.0, 0.0, 0.0] for idx in range(10)]


def _base_record() -> dict:
    return {
        "num_candidates": 4,
        "selected_index": 0,
        "feasible_mask": [True, True, True, True],
        "candidate_closed_loop_outcomes": [
            _outcome(0, progress=10.0, jerk=5.0, lateral=2.0, value=0.0),
            _outcome(1, progress=9.8, jerk=3.0, lateral=1.0, value=1.0),
            _outcome(2, progress=9.9, jerk=4.0, lateral=0.8, value=1.5),
            _outcome(3, progress=9.8, jerk=2.0, lateral=0.5, value=2.0, red=True),
        ],
        "selection_scores": [0.0, 2.0, 1.0, 3.0],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0, 0.0, 1.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.0, 0.0, 0.0],
        "candidate_route_progress": None,
        "candidate_step_reach": [1.0, 0.95, 0.96, 0.95],
        "candidate_perfect_tracker_target_speed_mps": [5.0, 4.95, 4.96, 4.95],
        "candidate_perfect_tracker_postprocessed_reference_prefix": [
            _prefix(10.0),
            _prefix(9.95),
            _prefix(9.96),
            _prefix(9.95),
        ],
        "candidate_horizon_lateral_acceleration_cost": [2.0, 1.0, 0.8, 0.5],
        "candidate_dp_prior_jerk_excess_cost": [1.0, 1.5, 0.5, 0.2],
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


def test_outcome_free_screen_keeps_baseline_when_no_candidate_passes(tmp_path) -> None:
    record = _base_record()
    record["candidate_horizon_lateral_acceleration_cost"] = [2.0, 2.5, 2.2, 1.0]

    report = analyze([_write_log(tmp_path, [record])], label="unit")
    moderate = _screen(report, "moderate_lateral")

    assert moderate["records"]["changed"] == 0
    assert moderate["rates"]["change_rate"] == 0.0
    assert moderate["outcome_delta_summary"]["progress_m"]["mean"] == pytest.approx(0.0)


def test_outcome_free_screen_applies_red_and_budget_guards(tmp_path) -> None:
    report = analyze([_write_log(tmp_path, [_base_record()])], label="unit")
    moderate = _screen(report, "moderate_lateral")
    jerk_safe = _screen(report, "moderate_lateral_jerk_nondegrading")

    assert moderate["records"]["changed"] == 1
    assert moderate["changed_outcome_delta_summary"]["mean_lateral_acceleration_mps2"][
        "mean"
    ] == pytest.approx(-1.2)
    assert moderate["changed_diagnostic_delta_summary"]["raw_jerk_delta"]["mean"] == pytest.approx(
        -0.5
    )
    assert jerk_safe["records"]["changed"] == 1
    assert jerk_safe["changed_diagnostic_delta_summary"]["raw_jerk_delta"]["mean"] <= 0.0


def test_outcome_free_screen_reports_safety_regression_posterior(tmp_path) -> None:
    record = _base_record()
    record["candidate_closed_loop_outcomes"][2]["red_light_violation"] = True

    report = analyze([_write_log(tmp_path, [record])], label="unit")
    moderate = _screen(report, "moderate_lateral")

    assert moderate["records"]["changed"] == 1
    assert moderate["records"]["outcome_safety_regressions"] == 1


def test_outcome_free_screen_accepts_nonfinite_selection_score_tiebreaks(tmp_path) -> None:
    record = _base_record()
    record["selection_scores"] = [0.0, float("nan"), float("inf"), float("-inf")]

    report = analyze([_write_log(tmp_path, [record])], label="unit")
    moderate = _screen(report, "moderate_lateral")

    assert moderate["records"]["changed"] == 1
    assert moderate["changed_diagnostic_delta_summary"]["raw_lateral_delta"]["mean"] == pytest.approx(
        -1.2
    )


def test_outcome_free_screen_prefers_dp_reward_progress_proxy(tmp_path) -> None:
    record = _base_record()
    record["dp_candidate_rewards"] = [
        {"progress": 10.0},
        {"progress": 9.99},
        {"progress": 9.0},
        {"progress": 9.99},
    ]

    report = analyze([_write_log(tmp_path, [record])], label="unit")
    moderate = _screen(report, "moderate_lateral")

    assert report["records"]["progress_proxy_source_counts"]["dp_reward_progress"] == 1
    assert report["records"]["progress_proxy_source_counts"]["step_reach_fallback"] == 0
    assert moderate["records"]["changed"] == 1
    assert moderate["changed_diagnostic_delta_summary"]["raw_lateral_delta"]["mean"] == pytest.approx(
        -1.0
    )
