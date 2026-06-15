from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_rollout_outcome_alignment import (
    analyze,
)


def _record() -> dict:
    outcomes = [
        {
            "candidate_index": index,
            "mean_jerk_mps3": jerk,
            "mean_lateral_acceleration_mps2": lateral,
            "feasible": True,
        }
        for index, (jerk, lateral) in enumerate(
            ((1.0, 3.0), (2.0, 2.0), (3.0, 1.0))
        )
    ]
    rollout = {
        str(horizon): {
            "mean_vector_jerk_mps3": [1.0, 2.0, 3.0],
            "mean_lateral_acceleration_mps2": [3.0, 2.0, 1.0],
        }
        for horizon in (3, 5, 10)
    }
    return {
        "feasible_mask": [True, True, True],
        "candidate_closed_loop_outcomes": outcomes,
        "candidate_perfect_tracker_open_loop_rollout": rollout,
        "candidate_dp_prior_jerk_excess_cost": [3.0, 2.0, 1.0],
        "candidate_horizon_lateral_acceleration_cost": [1.0, 2.0, 3.0],
        "candidate_dp_prior_lateral_acceleration_excess_cost": [1.0, 2.0, 3.0],
    }


def _write_log(tmp_path, record: dict):
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps([record]), encoding="utf-8")
    return path


def test_rollout_features_align_with_candidate_outcomes(tmp_path) -> None:
    report = analyze([_write_log(tmp_path, _record())])

    jerk = report["features"]["rollout_h3_mean_vector_jerk_mps3"]
    lateral = report[
        "features"
    ]["rollout_h3_mean_lateral_acceleration_mps2"]
    prior_jerk = report["features"]["dp_prior_jerk_excess"]

    assert report["records"]["total"] == 1
    assert jerk["record_availability_rate"] == 1.0
    assert jerk["feasible_candidate_pearson"] == pytest.approx(1.0)
    assert jerk["feasible_pairwise_order_agreement_rate"] == 1.0
    assert jerk["feasible_oracle_match_rate"] == 1.0
    assert lateral["feasible_candidate_pearson"] == pytest.approx(1.0)
    assert prior_jerk["feasible_candidate_pearson"] == pytest.approx(-1.0)


def test_rollout_analysis_rejects_negative_online_feature(tmp_path) -> None:
    record = _record()
    record["candidate_perfect_tracker_open_loop_rollout"]["3"][
        "mean_vector_jerk_mps3"
    ][1] = -1.0

    with pytest.raises(ValueError, match="must be nonnegative"):
        analyze([_write_log(tmp_path, record)])


def test_rollout_analysis_requires_candidate_outcomes(tmp_path) -> None:
    record = _record()
    record["candidate_closed_loop_outcomes"] = None

    with pytest.raises(ValueError, match="missing candidate closed-loop outcomes"):
        analyze([_write_log(tmp_path, record)])
