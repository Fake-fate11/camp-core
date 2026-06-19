from __future__ import annotations

import copy

import pytest

from scripts.integrations.analyze_diffusion_planner_candidate_set_observable_support import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze_records,
)


def _source_report(status: str = "redesigned_atom_separability_rejected") -> dict:
    return {
        "final_decision": {
            "status": status,
            "authorized_next_work": None,
        },
        "failure_gap": {"primary_gap": "redesigned_atoms_block_beneficial_opportunities"},
        "records": {"total": 2, "candidate_rows": 4},
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": "/fake/camp_selection_log.json",
        "record_index": 0,
        "seed": seed,
        "scenario_buckets": ["overall", "traffic_light"],
    }


def _record(*, eligible: bool) -> dict:
    candidate_progress = 10.0 if eligible else 8.0
    return {
        "num_candidates": 2,
        "selected_index": 0,
        "feasible_mask": [True, True],
        "candidate_step_reach": [10.0, candidate_progress],
        "candidate_perfect_tracker_first_step_reach_m": [1.0, 1.0],
        "candidate_perfect_tracker_tail_average_speed_mps": [5.0, 5.0],
        "candidate_perfect_tracker_target_speed_mps": [5.0, 5.0],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [2.0, 1.0],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [1.5, 1.2],
        "candidate_perfect_tracker_yaw_rate_magnitude_rps": [0.2, 0.1],
        "candidate_dp_prior_deviation_cost": [1.0, 0.0],
        "candidate_horizon_union_planned_red_light_cost": [1.0, 0.0],
        "candidate_full_horizon_planned_red_light_cost": [1.0, 0.0],
        "candidate_red_stopping_margin_cost": [0.5, 0.0],
        "candidate_closed_loop_outcomes": [
            {
                "candidate_index": 0,
                "progress_m": 10.0,
                "mean_jerk_mps3": 2.0,
                "mean_lateral_acceleration_mps2": 1.5,
                "collision": False,
                "near_miss": False,
                "lane_violation": False,
                "red_light_violation": True,
            },
            {
                "candidate_index": 1,
                "progress_m": candidate_progress,
                "mean_jerk_mps3": 1.0,
                "mean_lateral_acceleration_mps2": 1.2,
                "collision": False,
                "near_miss": False,
                "lane_violation": False,
                "red_light_violation": False,
            },
        ],
    }


def test_candidate_set_observable_support_finds_toy_signal() -> None:
    report = analyze_records(
        [
            {"raw": _record(eligible=True), "context": _context()},
            {"raw": _record(eligible=False), "context": _context()},
        ],
        redesigned_atom_separability_report=_source_report(),
        fail_on_formal_seeds=True,
        min_eligible_oracle_record_rate=0.1,
        min_observable_auc=0.7,
        min_top1_oracle_capture_rate=0.5,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "offline_oracle_feature_screen_design_only"
    )
    assert report["analysis"]["future_outcome_labels_used_for_features"] is False
    assert report["analysis"]["future_outcome_labels_used_for_oracle_labels"] is True
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False
    assert report["candidate_support"]["eligible_oracle_records"] == 1
    best = report["final_decision"]["best_feature"]
    assert best["best_auc"] >= 0.7
    assert best["top1_oracle_capture_rate"] >= 0.5


def test_candidate_set_observable_support_blocks_when_source_not_rejected() -> None:
    report = analyze_records(
        [{"raw": _record(eligible=True), "context": _context()}],
        redesigned_atom_separability_report=_source_report(
            "redesigned_atom_separability_promising_for_offline_weight_screen"
        ),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_candidate_set_observable_support_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [{"raw": _record(eligible=True), "context": _context(seed=11)}],
            redesigned_atom_separability_report=_source_report(),
            fail_on_formal_seeds=True,
        )


def test_candidate_set_observable_features_are_outcome_independent() -> None:
    base = _record(eligible=True)
    mutated = copy.deepcopy(base)
    mutated["candidate_closed_loop_outcomes"][0]["red_light_violation"] = False
    mutated["candidate_closed_loop_outcomes"][1]["red_light_violation"] = True
    mutated["candidate_closed_loop_outcomes"][1]["collision"] = True
    mutated["candidate_closed_loop_outcomes"][1]["progress_m"] = 0.0

    base_report = analyze_records(
        [{"raw": base, "context": _context()}],
        redesigned_atom_separability_report=_source_report(),
    )
    mutated_report = analyze_records(
        [{"raw": mutated, "context": _context()}],
        redesigned_atom_separability_report=_source_report(),
    )

    assert base_report["feature_catalog"] == mutated_report["feature_catalog"]
