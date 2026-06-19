from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_dense_lane_change_atom_aware_screen import (
    analyze_records,
    render_markdown,
)
from scripts.integrations.analyze_diffusion_planner_dense_lane_change_score_calibration import (
    _load_record,
)


def _outcome(
    *,
    progress: float = 10.0,
    collision: bool = False,
    near_miss: bool = False,
    lane_violation: bool = False,
    red_light_violation: bool = False,
    jerk: float = 0.5,
    lateral: float = 0.2,
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
    loose_norm: list[float],
    selected_norm: list[float],
    selected_outcome: dict[str, object],
    loose_outcome: dict[str, object],
    formal_seed: bool = False,
) -> dict[str, object]:
    top1_norm = [1.0, 1.0, 0.0]
    record = _load_record(
        {
            "num_candidates": 3,
            "selected_index": 1,
            "feasible_mask": [True, True, True],
            "candidate_route_progress": [10.0, 10.0, 9.95],
            "candidate_perfect_tracker_target_speed_mps": [4.0, 4.0, 3.95],
            "candidate_dp_prior_deviation_cost": [0.0, 1.0, 0.4],
            "candidate_perfect_tracker_jerk_magnitude_mps3": [0.8, 0.8, 0.8],
            "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [
                0.4,
                0.4,
                0.4,
            ],
            "selection_normalized_atoms": [top1_norm, selected_norm, loose_norm],
            "selection_weights": [1.0, 1.0, 1.0],
            "selection_scores": [
                sum(top1_norm),
                sum(selected_norm),
                sum(loose_norm),
            ],
            "atom_names": [
                "dp_prior_jerk_excess_cost",
                "jerk_early",
                "neutral_atom",
            ],
            "candidate_closed_loop_outcomes": [
                _outcome(near_miss=True),
                selected_outcome,
                loose_outcome,
            ],
        },
        "unit atom-aware record",
    )
    record["context"] = {
        "log_path": "/fake/camp_selection_log.json",
        "record_index": 0,
        "route": "nishishinjuku_lane_change",
        "seed": 11 if formal_seed else 1,
        "formal_seed": formal_seed,
        "npc_count": 8,
        "traffic_light": "off",
        "mode": "static",
    }
    return record


def test_atom_aware_screen_can_pass_by_preserving_positive_protective_margin() -> None:
    protected_bad_loose = _record(
        selected_norm=[0.1, 0.1, 0.0],
        loose_norm=[0.4, 0.3, 0.0],
        selected_outcome=_outcome(),
        loose_outcome=_outcome(collision=True, progress=9.95, jerk=1.0, lateral=0.4),
    )
    good_loose_records = [
        _record(
            selected_norm=[0.1, 0.1, 0.0],
            loose_norm=[0.0, 0.0, 0.3],
            selected_outcome=_outcome(near_miss=True, jerk=1.0, lateral=0.4),
            loose_outcome=_outcome(jerk=0.5, lateral=0.2),
        )
        for _ in range(19)
    ]

    report = analyze_records(
        [protected_bad_loose, *good_loose_records],
        thresholds=(0.0,),
        bootstrap_resamples=200,
        seed=3,
        min_changed_supported_rate=0.5,
    )

    grid = report["threshold_grid"][0]
    assert report["final_decision"]["status"] == "atom_aware_offline_screen_passed"
    assert report["final_decision"]["closed_loop_smoke_authorized"] is True
    assert report["final_decision"]["online_selector_authorized"] is False
    assert grid["changed_supported_records"] == 19
    assert grid["preserved_by_positive_protective_margin"] == 1
    assert grid["fallback_changed_records"] == 0
    assert grid["dense_lane_change"]["safety_cost_delta_vs_current"]["ci95_high"] < 0.0
    assert grid["dense_lane_change"]["mean_jerk_delta_vs_current"]["ci95_high"] <= 0.0
    assert grid["dense_lane_change"]["mean_lateral_delta_vs_current"]["ci95_high"] <= 0.0

    markdown = render_markdown(report)
    assert "Atom-Aware No-Leak Screen" in markdown
    assert "not classical Benders decomposition" in markdown


def test_atom_aware_screen_rejects_formal_seed_records() -> None:
    record = _record(
        selected_norm=[0.1, 0.1, 0.0],
        loose_norm=[0.0, 0.0, 0.3],
        selected_outcome=_outcome(near_miss=True),
        loose_outcome=_outcome(),
        formal_seed=True,
    )

    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records([record], fail_on_formal_seeds=True)


def test_atom_aware_screen_fails_closed_when_protective_atom_missing() -> None:
    record = _load_record(
        {
            "num_candidates": 3,
            "selected_index": 1,
            "feasible_mask": [True, True, True],
            "candidate_route_progress": [10.0, 10.0, 9.95],
            "candidate_perfect_tracker_target_speed_mps": [4.0, 4.0, 3.95],
            "candidate_dp_prior_deviation_cost": [0.0, 1.0, 0.4],
            "candidate_perfect_tracker_jerk_magnitude_mps3": [0.8, 0.8, 0.8],
            "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [
                0.4,
                0.4,
                0.4,
            ],
            "selection_normalized_atoms": [
                [1.0, 0.0],
                [0.1, 0.0],
                [0.0, 0.3],
            ],
            "selection_weights": [1.0, 1.0],
            "selection_scores": [1.0, 0.1, 0.3],
            "atom_names": ["other_atom", "neutral_atom"],
            "candidate_closed_loop_outcomes": [
                _outcome(near_miss=True),
                _outcome(near_miss=True),
                _outcome(),
            ],
        },
        "unit missing protective atom record",
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

    report = analyze_records([record], thresholds=(0.0,), bootstrap_resamples=50, seed=5)

    grid = report["threshold_grid"][0]
    assert report["records"]["protective_margin_available_records"] == 0
    assert grid["missing_protective_margin_records"] == 1
    assert grid["changed_supported_records"] == 0
    assert report["final_decision"]["status"] == "atom_aware_offline_screen_rejected"
