from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_dense_lane_change_outcome_screen import (
    _load_record,
)
from scripts.integrations.analyze_diffusion_planner_dense_lane_change_score_margin import (
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
    score_penalty: float,
) -> dict[str, object]:
    record = _load_record(
        {
            "num_candidates": 3,
            "selected_index": 1,
            "feasible_mask": [True, True, True],
            "candidate_route_progress": [10.0, 10.0, 10.0],
            "candidate_perfect_tracker_target_speed_mps": [4.0, 4.0, 4.0],
            "candidate_dp_prior_deviation_cost": [0.0, 1.0, 0.4],
            "candidate_perfect_tracker_jerk_magnitude_mps3": [0.8, 0.8, 0.8],
            "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [
                0.4,
                0.4,
                0.4,
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


def _helpful_record() -> dict[str, object]:
    return _record(
        score_penalty=0.01,
        outcomes=[
            _outcome(near_miss=True),
            _outcome(collision=True),
            _outcome(),
        ],
    )


def _harmful_high_penalty_record() -> dict[str, object]:
    return _record(
        score_penalty=0.08,
        outcomes=[
            _outcome(near_miss=True),
            _outcome(),
            _outcome(collision=True),
        ],
    )


def test_score_margin_screen_passes_when_threshold_blocks_high_penalty_harm() -> None:
    records = [_helpful_record() for _ in range(20)]
    records.extend(_harmful_high_penalty_record() for _ in range(4))

    report = analyze_records(
        records,
        thresholds=(0.02, 0.10),
        bootstrap_resamples=200,
        seed=5,
        min_changed_supported_rate=0.5,
    )

    by_threshold = {item["threshold"]: item for item in report["grid"]}
    low = by_threshold[0.02]
    high = by_threshold[0.10]

    assert low["gate"]["passed"] is True
    assert low["changed_supported_records"] == 20
    assert low["changed_supported_rate"] == pytest.approx(20 / 24)
    assert low["dense_lane_change"]["safety_cost_delta_vs_current"]["ci95_high"] < 0.0
    assert low["supported_target"]["safety_cost_delta_vs_current"]["ci95_high"] < 0.0

    assert high["changed_supported_records"] == 24
    assert high["gate"]["passed"] is False
    assert "hard_components_worse_vs_current" in high["gate"]["reasons"]

    assert report["final_decision"]["status"] == "score_margin_screen_passed"
    assert report["final_decision"]["passing_thresholds"] == [0.02]
    assert report["final_decision"]["online_selector_authorized"] is False

    markdown = render_markdown(report)
    assert "Score-Margin Preservation Screen" in markdown
    assert "not classical Benders decomposition" in markdown


def test_score_margin_screen_rejects_when_only_harmful_low_penalty_changes() -> None:
    records = [
        _record(
            score_penalty=0.01,
            outcomes=[
                _outcome(near_miss=True),
                _outcome(),
                _outcome(collision=True),
            ],
        )
        for _ in range(10)
    ]

    report = analyze_records(
        records,
        thresholds=(0.02,),
        bootstrap_resamples=100,
        seed=9,
        min_changed_supported_rate=0.5,
    )

    threshold = report["grid"][0]
    assert threshold["gate"]["passed"] is False
    assert "dense_safety_vs_current_not_proven" in threshold["gate"]["reasons"]
    assert "hard_components_worse_vs_current" in threshold["gate"]["reasons"]
    assert report["final_decision"]["status"] == "score_margin_screen_rejected"
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False
