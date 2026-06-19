from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_dense_lane_change_outcome_screen import (
    LooseRuleConfig,
    _load_record,
    analyze_records,
    render_markdown,
)


def _outcome(
    *,
    progress: float = 10.0,
    collision: bool = False,
    near_miss: bool = False,
    lane_violation: bool = False,
    red_light_violation: bool = False,
    jerk: float = 1.0,
    lateral: float = 0.5,
) -> dict[str, object]:
    return {
        "progress_m": progress,
        "collision": collision,
        "near_miss": near_miss,
        "lane_violation": lane_violation,
        "red_light_violation": red_light_violation,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
    }


def _record(
    *,
    outcomes: list[dict[str, object]],
    selected: int = 1,
) -> dict[str, object]:
    record = _load_record(
        {
            "num_candidates": 3,
            "selected_index": selected,
            "feasible_mask": [True, True, True],
            "candidate_route_progress": [10.0, 10.0, 9.95],
            "candidate_perfect_tracker_target_speed_mps": [4.0, 4.0, 3.9],
            "candidate_dp_prior_deviation_cost": [0.0, 1.0, 0.4],
            "candidate_perfect_tracker_jerk_magnitude_mps3": [0.8, 0.8, 0.83],
            "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [
                0.4,
                0.4,
                0.43,
            ],
            "selection_scores": [0.0, 0.1, 0.2],
            "candidate_closed_loop_outcomes": outcomes,
        },
        "unit record",
    )
    record["context"] = {
        "log_path": "/fake/camp_selection_log.json",
        "record_index": 0,
        "route": "nishishinjuku_lane_change",
        "seed": 1,
        "formal_seed": False,
        "npc_count": 8,
        "traffic_light": "off",
        "mode": "static",
    }
    return record


def test_loose_rule_outcome_screen_can_pass_with_posterior_safety_gain() -> None:
    records = [
        _record(
            outcomes=[
                _outcome(near_miss=True),
                _outcome(collision=True),
                _outcome(),
            ],
        ),
        _record(
            outcomes=[
                _outcome(near_miss=True, progress=9.9),
                _outcome(lane_violation=True, progress=9.8),
                _outcome(progress=10.0),
            ],
        ),
    ]

    report = analyze_records(records, bootstrap_resamples=100, seed=7)

    assert report["final_decision"]["status"] == "loose_rule_outcome_screen_passed"
    assert report["final_decision"]["closed_loop_smoke_authorized"] is True
    assert report["mechanism"]["dense_support_rate"] == pytest.approx(1.0)
    assert report["mechanism"]["override_top1_chosen_rate"] == pytest.approx(0.0)
    assert (
        report["dense_lane_change"]["safety_cost_delta_vs_current"]["ci95_high"]
        < 0.0
    )
    assert report["dense_lane_change"]["safety_cost_delta_vs_top1"]["ci95_high"] < 0.0
    assert report["dense_lane_change"]["hard_nonworse_vs_current"] == pytest.approx(
        1.0
    )

    markdown = render_markdown(report)
    assert "Dense Lane-Change Loose Rule Outcome Screen" in markdown
    assert "not classical Benders decomposition" in markdown


def test_loose_rule_outcome_screen_rejects_posterior_hard_regression() -> None:
    records = [
        _record(
            outcomes=[
                _outcome(),
                _outcome(),
                _outcome(collision=True),
            ],
        ),
    ]

    report = analyze_records(
        records,
        config=LooseRuleConfig(min_dense_support_rate=0.5),
        bootstrap_resamples=100,
        seed=9,
    )

    assert report["mechanism"]["dense_support_rate"] == pytest.approx(1.0)
    assert report["final_decision"]["status"] == "loose_rule_outcome_screen_rejected"
    assert "hard_components_worse_vs_current" in report["final_decision"]["reasons"]
    assert "hard_components_worse_vs_top1" in report["final_decision"]["reasons"]
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
