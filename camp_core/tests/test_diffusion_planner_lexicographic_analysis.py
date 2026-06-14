from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_camp_lexicographic import (
    compute_lexicographic_counterfactual_report,
)


def test_lexicographic_counterfactual_reconstructs_base_feasibility(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(
        json.dumps(
            [
                {
                    "selected_index": 0,
                    "scores": [0.0, 0.2, 0.1],
                    "infeasibility_reasons": [
                        [],
                        ["candidate0_step_reach_underprogress"],
                        ["dp_lane_crossing"],
                    ],
                    "candidate_step_reach": [0.4, 0.39, 0.5],
                    "dp_candidate_rewards": [
                        {"progress": 5.0, "red_light": 0.0},
                        {"progress": 6.0, "red_light": 0.0},
                        {"progress": 9.0, "red_light": 0.0},
                    ],
                    "candidate_dp_prior_jerk_excess_cost": [1.0, 0.0, 0.0],
                    "candidate_horizon_lateral_acceleration_cost": [
                        0.3,
                        0.1,
                        0.0,
                    ],
                    "candidate_dp_prior_lateral_acceleration_excess_cost": [
                        0.2,
                        0.0,
                        0.0,
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    report = compute_lexicographic_counterfactual_report(
        [log_path],
        ignored_infeasibility_reasons=(
            "candidate0_step_reach_underprogress",
        ),
        progress_epsilon_m=2.0,
        red_epsilon=0.0,
        jerk_epsilon=1.0,
        lateral_epsilon=0.05,
    )

    assert report["records"]["base_feasible"] == 1
    assert report["analysis"]["contract"]["new_fallback_records"] == 0
    assert report["selection"]["change_vs_base_rate"] == 1.0
    paired = report["paired_selected_minus_base"]
    assert paired["progress"]["mean"] == 1.0
    assert paired["progress"]["nonworse_rate"] == 1.0
    assert paired["jerk_excess"]["mean"] == -1.0
    assert paired["jerk_excess"]["nonworse_rate"] == 1.0
    assert paired["lateral_absolute"]["mean"] == pytest.approx(-0.2)


def test_lexicographic_counterfactual_rejects_nonfinite_scores(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(
        json.dumps(
            [
                {
                    "selected_index": 0,
                    "scores": [float("nan")],
                    "infeasibility_reasons": [[]],
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid scores"):
        compute_lexicographic_counterfactual_report(
            [log_path],
            progress_epsilon_m=1.0,
            red_epsilon=0.0,
            jerk_epsilon=0.0,
            lateral_epsilon=0.0,
        )
