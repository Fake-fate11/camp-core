from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_weight_sensitivity import (
    analyze,
)


ATOM_NAMES = (
    "jerk_early",
    "progress_shortfall",
    "planned_lateral_acceleration_cost",
    "red_stopping_margin_cost",
    "dp_prior_jerk_excess_cost",
)


def _record() -> dict:
    weights = [0.2, 0.6, 0.0, 0.05, 0.15]
    normalized_atoms = [
        [1.0, 0.1, 2.0, 0.0, 1.0],
        [1.0, 0.2, 0.0, 0.0, 0.8],
        [1.0, 0.5, 0.0, 0.0, 0.0],
    ]
    return {
        "atom_names": list(ATOM_NAMES),
        "weights": weights,
        "normalized_atoms": normalized_atoms,
        "atoms": normalized_atoms,
        "feasible_mask": [True, True, True],
        "selected_index": 0,
        "candidate_closed_loop_outcomes": [
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
                "progress_m": 9.8,
                "value": 4.9,
                "mean_jerk_mps3": 3.0,
                "mean_lateral_acceleration_mps2": 1.0,
                "collision": False,
                "near_miss": False,
                "lane_violation": False,
                "red_light_violation": False,
                "feasible": True,
            },
            {
                "candidate_index": 2,
                "progress_m": 9.0,
                "value": 4.0,
                "mean_jerk_mps3": 1.0,
                "mean_lateral_acceleration_mps2": 1.0,
                "collision": False,
                "near_miss": False,
                "lane_violation": False,
                "red_light_violation": True,
                "feasible": True,
            },
        ],
    }


def _write_log(tmp_path, *records: dict):
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps(list(records)), encoding="utf-8")
    return path


def test_weight_sensitivity_keeps_baseline_and_reports_transfer(tmp_path) -> None:
    report = analyze([_write_log(tmp_path, _record())])
    variants = {variant["name"]: variant for variant in report["variants"]}

    assert report["records"]["total"] == 1
    assert variants["baseline_redstopfloor05"]["changed_records"] == 0

    lateral = variants["progress_to_lateral_0p05"]
    assert lateral["changed_records"] == 1
    assert lateral["red_stopping_lower_bound_preserved"]
    assert lateral["simplex_sum"] == pytest.approx(1.0)
    assert lateral["minimum_weight"] >= 0.0
    assert lateral["outcome_delta_mean"]["progress_m"] == pytest.approx(-0.2)
    assert lateral["outcome_delta_mean"][
        "mean_lateral_acceleration_mps2"
    ] == pytest.approx(-1.0)


def test_weight_sensitivity_retains_all_infeasible_fallback(tmp_path) -> None:
    record = _record()
    record["feasible_mask"] = [False, False, False]

    report = analyze([_write_log(tmp_path, record)])
    variants = {variant["name"]: variant for variant in report["variants"]}

    assert report["records"]["fallback"] == 1
    assert variants["progress_to_lateral_0p05"]["changed_records"] == 0
    assert variants["progress_to_lateral_0p05"]["nonfallback_records"] == 0


def test_weight_sensitivity_requires_outcomes(tmp_path) -> None:
    record = _record()
    record["candidate_closed_loop_outcomes"] = None

    with pytest.raises(ValueError, match="candidate outcomes"):
        analyze([_write_log(tmp_path, record)])
