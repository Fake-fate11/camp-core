from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_dense_lane_change_camp_advantage import (
    analyze_records,
    render_markdown,
)
from scripts.integrations.analyze_diffusion_planner_dense_lane_change_outcome_screen import (
    _load_record,
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
    score_penalty: float = 0.2,
) -> dict[str, object]:
    record = _load_record(
        {
            "num_candidates": 3,
            "selected_index": 1,
            "feasible_mask": [True, True, True],
            "candidate_route_progress": [10.0, 10.0, 9.95],
            "candidate_perfect_tracker_target_speed_mps": [4.0, 4.0, 3.95],
            "candidate_dp_prior_deviation_cost": [0.0, 1.0, 0.4],
            "candidate_perfect_tracker_jerk_magnitude_mps3": [0.8, 0.8, 0.82],
            "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [
                0.4,
                0.4,
                0.42,
            ],
            "selection_scores": [0.0, 0.1, 0.1 + score_penalty],
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


def test_camp_advantage_attribution_flags_preservation_need() -> None:
    camp_advantage = _record(
        outcomes=[
            _outcome(progress=9.8, near_miss=True),
            _outcome(progress=10.0),
            _outcome(progress=9.7),
        ],
        score_penalty=0.02,
    )
    loose_helpful = _record(
        outcomes=[
            _outcome(progress=9.9, near_miss=True),
            _outcome(progress=9.8, collision=True),
            _outcome(progress=10.0),
        ],
        score_penalty=0.3,
    )

    report = analyze_records(
        [camp_advantage, loose_helpful],
        bootstrap_resamples=100,
        seed=11,
    )

    assert report["records"]["supported_target_records"] == 2
    assert report["records"]["camp_advantage_records"] == 1
    assert report["records"]["loose_regresses_current_safety_records"] == 1
    assert report["records"]["loose_improves_current_safety_records"] == 1
    assert (
        report["final_decision"]["status"]
        == "current_camp_advantage_requires_preservation"
    )
    assert "current_camp_advantage_records_exist" in report["final_decision"][
        "reasons"
    ]
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False
    assert report["camp_advantage_records"]["rates"]["camp_beats_top1"] == pytest.approx(
        1.0
    )
    assert report["camp_advantage_records"]["rates"]["camp_beats_loose"] == pytest.approx(
        1.0
    )

    separation = {
        item["descriptor"]: item for item in report["descriptor_separation"]
    }
    assert separation["score_penalty"]["loose_hurts_mean"] == pytest.approx(0.02)
    assert separation["score_penalty"]["loose_helps_mean"] == pytest.approx(0.3)


def test_camp_advantage_attribution_markdown_keeps_math_boundary() -> None:
    report = analyze_records(
        [
            _record(
                outcomes=[
                    _outcome(progress=9.8, near_miss=True),
                    _outcome(progress=10.0),
                    _outcome(progress=9.7),
                ]
            )
        ],
        bootstrap_resamples=10,
        seed=3,
    )

    markdown = render_markdown(report)
    assert "Current CAMP Advantage Attribution" in markdown
    assert "read-only attribution screen" in markdown
    assert "not classical Benders decomposition" in markdown
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
