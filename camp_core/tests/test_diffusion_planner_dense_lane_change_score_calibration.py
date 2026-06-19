from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_dense_lane_change_score_calibration import (
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
    loose_norm_guard: float,
    loose_outcome: dict[str, object],
    selected_outcome: dict[str, object],
    formal_seed: bool = False,
) -> dict[str, object]:
    selected_norm = [0.1, 0.1]
    loose_norm = [loose_norm_guard, 0.1]
    top1_norm = [0.9, 0.0]
    record = _load_record(
        {
            "num_candidates": 3,
            "selected_index": 1,
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
            "selection_normalized_atoms": [top1_norm, selected_norm, loose_norm],
            "selection_weights": [1.0, 1.0],
            "selection_scores": [
                sum(top1_norm),
                sum(selected_norm),
                sum(loose_norm),
            ],
            "atom_names": ["guard_atom", "neutral_atom"],
            "candidate_closed_loop_outcomes": [
                _outcome(near_miss=True),
                selected_outcome,
                loose_outcome,
            ],
        },
        "unit score calibration record",
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


def test_score_calibration_reports_atom_contribution_separation() -> None:
    records = [
        _record(
            loose_norm_guard=0.6,
            selected_outcome=_outcome(),
            loose_outcome=_outcome(collision=True, progress=9.95),
        ),
        _record(
            loose_norm_guard=0.15,
            selected_outcome=_outcome(near_miss=True),
            loose_outcome=_outcome(progress=9.95),
        ),
    ]

    report = analyze_records(records)

    assert report["final_decision"]["status"] == (
        "score_schema_calibration_diagnostic_complete"
    )
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["records"]["supported_target_records"] == 2
    assert report["records"]["camp_advantage_records"] == 1
    assert report["records"]["loose_regresses_current_safety_records"] == 1
    assert report["records"]["loose_improves_current_safety_records"] == 1
    assert report["score_schema"]["records_with_schema"] == 2
    assert report["score_schema"]["score_reconstruction_abs_error"]["max"] == pytest.approx(0.0)

    separation = {
        row["atom"]: row for row in report["atom_contribution_separation"]
    }
    guard = separation["guard_atom"]
    assert guard["loose_hurts_mean_contribution_margin"] == pytest.approx(0.5)
    assert guard["loose_helps_mean_contribution_margin"] == pytest.approx(0.05)
    assert guard["hurts_minus_helps_contribution_margin"] == pytest.approx(0.45)

    markdown = render_markdown(report)
    assert "Score Schema Calibration Diagnostic" in markdown
    assert "not classical Benders decomposition" in markdown
    assert "Positive contribution margin" in markdown


def test_score_calibration_rejects_formal_seed_records() -> None:
    record = _record(
        loose_norm_guard=0.6,
        selected_outcome=_outcome(),
        loose_outcome=_outcome(collision=True),
        formal_seed=True,
    )

    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records([record], fail_on_formal_seeds=True)


def test_score_calibration_reports_missing_schema_without_crashing() -> None:
    record = _load_record(
        {
            "num_candidates": 3,
            "selected_index": 1,
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
            "selection_scores": [0.9, 0.2, 0.7],
            "candidate_closed_loop_outcomes": [
                _outcome(near_miss=True),
                _outcome(),
                _outcome(collision=True),
            ],
        },
        "unit missing schema record",
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

    report = analyze_records([record])

    assert report["final_decision"]["status"] == "score_schema_calibration_inconclusive"
    assert report["score_schema"]["records_with_schema"] == 0
    assert report["score_schema"]["records_missing_schema"] == 1
    assert report["atom_contribution_separation"] == []
