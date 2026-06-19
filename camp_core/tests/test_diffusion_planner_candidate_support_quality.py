from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_candidate_support_quality import (
    GUARDS,
    _current_tick_guard_mask,
    _outcome_nonregressing_mask,
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
    planned_loose_progress: float = 9.99,
    selected_outcome: dict[str, object] | None = None,
    loose_outcome: dict[str, object] | None = None,
    formal_seed: bool = False,
) -> dict[str, object]:
    selected_outcome = selected_outcome or _outcome(near_miss=True)
    loose_outcome = loose_outcome or _outcome(progress=9.99)
    record = _load_record(
        {
            "num_candidates": 3,
            "selected_index": 1,
            "feasible_mask": [True, True, True],
            "candidate_route_progress": [10.0, 10.0, planned_loose_progress],
            "candidate_perfect_tracker_target_speed_mps": [4.0, 4.0, 4.0],
            "candidate_dp_prior_deviation_cost": [0.0, 1.0, 0.4],
            "candidate_perfect_tracker_jerk_magnitude_mps3": [0.8, 0.8, 0.8],
            "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [
                0.4,
                0.4,
                0.4,
            ],
            "selection_normalized_atoms": [
                [1.0, 1.0],
                [0.1, 0.1],
                [0.0, 0.0],
            ],
            "selection_weights": [1.0, 1.0],
            "selection_scores": [2.0, 0.2, 0.0],
            "atom_names": ["dp_prior_jerk_excess_cost", "jerk_early"],
            "candidate_closed_loop_outcomes": [
                _outcome(collision=True),
                selected_outcome,
                loose_outcome,
            ],
        },
        "unit candidate support record",
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


def test_candidate_support_quality_detects_no_leak_guarded_support() -> None:
    records = [_record() for _ in range(20)]

    report = analyze_records(records, bootstrap_resamples=200, seed=3)

    assert report["final_decision"]["status"] == (
        "no_leak_guarded_candidate_support_present"
    )
    assert "strict_current_tick_guarded_oracle_passed" in report["final_decision"][
        "reasons"
    ]
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False

    dense = report["slices"]["dense_lane_change"]["strategies"]
    strict = dense["oracle_guarded_strict_progress005_speed010_comfort_nonworse"]
    assert strict["changed_rate"] == pytest.approx(1.0)
    assert strict["safety_cost_delta_vs_current"]["ci95_high"] < 0.0
    assert strict["progress_delta_vs_current"]["ci95_low"] >= -0.05
    assert strict["hard_nonworse_vs_current"] == pytest.approx(1.0)

    markdown = render_markdown(report)
    assert "Candidate Support Quality Diagnostic" in markdown
    assert "not classical Benders decomposition" in markdown


def test_candidate_support_quality_distinguishes_outcome_support_from_reachability() -> None:
    records = [
        _record(
            planned_loose_progress=8.0,
            selected_outcome=_outcome(near_miss=True),
            loose_outcome=_outcome(progress=9.99),
        )
        for _ in range(20)
    ]

    report = analyze_records(records, bootstrap_resamples=200, seed=5)

    assert report["final_decision"]["status"] == (
        "no_leak_guarded_candidate_support_insufficient"
    )
    assert "outcome_support_exists_but_current_tick_guards_fail" in report[
        "final_decision"
    ]["reasons"]

    dense = report["slices"]["dense_lane_change"]["strategies"]
    outcome_oracle = dense["oracle_outcome_nonregressing"]
    strict = dense["oracle_guarded_strict_progress005_speed010_comfort_nonworse"]
    assert outcome_oracle["safety_cost_delta_vs_current"]["ci95_high"] < 0.0
    assert strict["changed_rate"] == pytest.approx(0.0)
    assert strict["safety_cost_delta_vs_current"]["ci95_high"] == pytest.approx(0.0)


def test_candidate_support_quality_rejects_formal_seed_records() -> None:
    record = _record(formal_seed=True)

    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records([record], fail_on_formal_seeds=True)


def test_candidate_support_masks_do_not_mutate_feasibility() -> None:
    record = _record(
        planned_loose_progress=9.99,
        selected_outcome=_outcome(near_miss=True, jerk=0.5, lateral=0.2),
        loose_outcome=_outcome(progress=9.99, jerk=1.0, lateral=0.4),
    )

    outcome_mask = _outcome_nonregressing_mask(record)
    guard_mask = _current_tick_guard_mask(record, GUARDS[0])

    assert outcome_mask.tolist() == [False, True, False]
    assert record["feasible"].tolist() == [True, True, True]
    assert guard_mask.tolist() == [True, True, True]
