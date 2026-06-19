from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_material_weight_failure_attribution import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze_records,
)


def _weight_report(status: str = "material_atom_weight_sensitivity_rejected") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passing_variants": [],
        },
        "records": {"total": 2, "candidate_rows": 6},
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": "/fake/camp_selection_log.json",
        "record_index": 0,
        "seed": seed,
        "scenario_buckets": ["overall", "traffic_light", "dense_scene"],
    }


def _record(*, harmful: bool) -> dict:
    chosen_progress = 8.0 if harmful else 10.0
    chosen_red = False
    chosen_collision = False
    return {
        "num_candidates": 2,
        "selected_index": 0,
        "feasible_mask": [True, True],
        "candidate_step_reach": [10.0, chosen_progress],
        "candidate_perfect_tracker_target_speed_mps": [5.0, 5.0],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [2.0, 1.0],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [2.0, 1.0],
        "candidate_dp_prior_deviation_cost": [0.0, 0.05],
        "candidate_horizon_union_planned_red_light_cost": [1.0, 0.0],
        "candidate_full_horizon_planned_red_light_cost": [1.0, 0.0],
        "candidate_red_stopping_margin_cost": [0.5, 0.0],
        "candidate_closed_loop_outcomes": [
            {
                "candidate_index": 0,
                "progress_m": 10.0,
                "mean_jerk_mps3": 2.0,
                "mean_lateral_acceleration_mps2": 2.0,
                "collision": False,
                "near_miss": False,
                "lane_violation": False,
                "red_light_violation": True,
            },
            {
                "candidate_index": 1,
                "progress_m": chosen_progress,
                "mean_jerk_mps3": 1.0,
                "mean_lateral_acceleration_mps2": 1.0,
                "collision": chosen_collision,
                "near_miss": False,
                "lane_violation": False,
                "red_light_violation": chosen_red,
            },
        ],
    }


def test_failure_attribution_identifies_traffic_driver_and_promising_certificate() -> None:
    report = analyze_records(
        [
            {"raw": _record(harmful=True), "context": _context()},
            {"raw": _record(harmful=False), "context": _context()},
        ],
        weight_sensitivity_report=_weight_report(),
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["analysis"]["future_outcome_labels_used_for_selection"] is False
    assert report["analysis"]["future_outcome_labels_used_for_attribution"] is False
    assert report["analysis"]["future_outcome_labels_used_for_evaluation"] is True
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False
    variant = {row["name"]: row for row in report["variants"]}["traffic_rule_focus"]
    assert variant["classification_counts"]["harmful_switch"] == 1
    assert variant["classification_counts"]["beneficial_switch"] == 1
    assert (
        variant["harmful_driver_summary"]["dominant_driver_counts"][
            "traffic_rule_exposure"
        ]
        >= 1
    )
    best = variant["best_certificate"]
    assert best["promising_progress_support_certificate"] is True
    assert best["harmful_block_rate"] == 1.0
    assert best["beneficial_retain_rate"] == 1.0


def test_failure_attribution_blocks_when_source_weight_gate_not_rejected() -> None:
    report = analyze_records(
        [{"raw": _record(harmful=True), "context": _context()}],
        weight_sensitivity_report=_weight_report(
            "material_atom_weight_sensitivity_ready_for_offline_selector_screen"
        ),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_failure_attribution_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [{"raw": _record(harmful=True), "context": _context(seed=11)}],
            weight_sensitivity_report=_weight_report(),
            fail_on_formal_seeds=True,
        )


def test_failure_attribution_selection_and_driver_are_outcome_independent() -> None:
    base = _record(harmful=True)
    mutated = _record(harmful=True)
    mutated["candidate_closed_loop_outcomes"][0]["red_light_violation"] = False
    mutated["candidate_closed_loop_outcomes"][1]["red_light_violation"] = True

    base_report = analyze_records(
        [{"raw": base, "context": _context()}],
        weight_sensitivity_report=_weight_report(),
    )
    mutated_report = analyze_records(
        [{"raw": mutated, "context": _context()}],
        weight_sensitivity_report=_weight_report(),
    )

    base_driver = base_report["variants"][0]["harmful_driver_summary"][
        "dominant_driver_counts"
    ]
    mutated_driver = mutated_report["variants"][0]["harmful_driver_summary"][
        "dominant_driver_counts"
    ]
    assert base_driver == mutated_driver
