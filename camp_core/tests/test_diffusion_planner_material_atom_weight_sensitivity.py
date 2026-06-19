from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_material_atom_weight_sensitivity import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze_records,
)


def _availability(status: str = "material_atom_schema_availability_ready_for_offline_weight_audit") -> dict:
    return {
        "final_decision": {
            "status": status,
            "authorized_next_work": "offline_material_atom_weight_audit_design_only",
            "missing_atom_families": [],
            "missing_required_buckets": [],
            "failed_convexity_checks": [],
        },
        "records": {"total": 1, "candidate_rows": 3},
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": "/fake/camp_selection_log.json",
        "record_index": 0,
        "seed": seed,
        "scenario_buckets": ["overall", "normal", "traffic_light", "dense_scene"],
    }


def _record() -> dict:
    return {
        "num_candidates": 3,
        "selected_index": 0,
        "feasible_mask": [True, True, False],
        "candidate_step_reach": [10.0, 9.99, 10.0],
        "candidate_perfect_tracker_target_speed_mps": [5.0, 5.0, 5.0],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [4.0, 1.0, 1.0],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [
            2.5,
            1.0,
            1.0,
        ],
        "candidate_dp_prior_deviation_cost": [0.0, 0.05, 0.20],
        "candidate_horizon_union_planned_red_light_cost": [1.0, 0.0, 0.0],
        "candidate_full_horizon_planned_red_light_cost": [1.0, 0.0, 0.0],
        "candidate_red_stopping_margin_cost": [0.8, 0.0, 0.0],
        "candidate_closed_loop_outcomes": [
            {
                "candidate_index": 0,
                "progress_m": 10.0,
                "mean_jerk_mps3": 4.0,
                "mean_lateral_acceleration_mps2": 2.5,
                "collision": False,
                "near_miss": False,
                "lane_violation": False,
                "red_light_violation": True,
            },
            {
                "candidate_index": 1,
                "progress_m": 9.99,
                "mean_jerk_mps3": 1.0,
                "mean_lateral_acceleration_mps2": 1.0,
                "collision": False,
                "near_miss": False,
                "lane_violation": False,
                "red_light_violation": False,
            },
            {
                "candidate_index": 2,
                "progress_m": 10.0,
                "mean_jerk_mps3": 1.0,
                "mean_lateral_acceleration_mps2": 1.0,
                "collision": False,
                "near_miss": False,
                "lane_violation": False,
                "red_light_violation": False,
            },
        ],
    }


def test_material_atom_weight_sensitivity_finds_predeclared_passing_variant() -> None:
    report = analyze_records(
        [{"raw": _record(), "context": _context()}],
        availability_report=_availability(),
        bootstrap_resamples=20,
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert "traffic_rule_focus" in report["final_decision"]["passing_variants"]
    assert report["analysis"]["training"] is False
    assert report["analysis"]["future_outcome_labels_used_for_selection"] is False
    assert report["analysis"]["future_outcome_labels_used_for_evaluation"] is True
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False
    traffic = {row["name"]: row for row in report["variants"]}["traffic_rule_focus"]
    assert traffic["changed_records"] == 1
    assert traffic["hard_nonworse_vs_current"] == 1.0
    assert traffic["safety_cost_delta_vs_current"]["mean"] < 0.0


def test_material_atom_weight_sensitivity_blocks_when_source_gate_not_ready() -> None:
    report = analyze_records(
        [{"raw": _record(), "context": _context()}],
        availability_report=_availability("material_atom_schema_availability_incomplete"),
        bootstrap_resamples=0,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_material_atom_weight_sensitivity_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [{"raw": _record(), "context": _context(seed=11)}],
            availability_report=_availability(),
            bootstrap_resamples=0,
            fail_on_formal_seeds=True,
        )


def test_material_atom_weight_sensitivity_retains_all_infeasible_fallback() -> None:
    record = _record()
    record["feasible_mask"] = [False, False, False]

    report = analyze_records(
        [{"raw": record, "context": _context()}],
        availability_report=_availability(),
        bootstrap_resamples=0,
    )

    for variant in report["variants"]:
        assert variant["changed_records"] == 0
        assert variant["fallback_retained_rate"] == 1.0


def test_material_atom_weight_sensitivity_selection_is_outcome_independent() -> None:
    base = _record()
    mutated = _record()
    mutated["candidate_closed_loop_outcomes"][0]["red_light_violation"] = False
    mutated["candidate_closed_loop_outcomes"][1]["red_light_violation"] = True
    mutated["candidate_closed_loop_outcomes"][1]["collision"] = True

    base_report = analyze_records(
        [{"raw": base, "context": _context()}],
        availability_report=_availability(),
        bootstrap_resamples=0,
    )
    mutated_report = analyze_records(
        [{"raw": mutated, "context": _context()}],
        availability_report=_availability(),
        bootstrap_resamples=0,
    )

    base_changed = {
        variant["name"]: variant["changed_records"]
        for variant in base_report["variants"]
    }
    mutated_changed = {
        variant["name"]: variant["changed_records"]
        for variant in mutated_report["variants"]
    }
    assert base_changed == mutated_changed
