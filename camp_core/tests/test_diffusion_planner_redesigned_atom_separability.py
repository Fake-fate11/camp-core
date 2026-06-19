from __future__ import annotations

import copy

import pytest

from scripts.integrations.analyze_diffusion_planner_material_atom_weight_sensitivity import (
    PREDECLARED_VARIANTS,
)
from scripts.integrations.analyze_diffusion_planner_redesigned_atom_separability import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze_records,
)


def _preflight_report(
    status: str = "atom_schema_redesign_preflight_ready_for_offline_separability_audit",
) -> dict:
    return {
        "final_decision": {
            "status": status,
            "authorized_next_work": "offline_redesigned_atom_separability_audit_design_only",
            "failed_atoms": [],
            "failed_math_checks": [],
        },
        "records": {"total": 2, "candidate_rows": 4},
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": "/fake/camp_selection_log.json",
        "record_index": 0,
        "seed": seed,
        "scenario_buckets": ["overall", "traffic_light"],
    }


def _record(*, harmful: bool) -> dict:
    chosen_progress = 8.0 if harmful else 10.0
    chosen_step_reach = 8.0 if harmful else 10.0
    return {
        "num_candidates": 2,
        "selected_index": 0,
        "feasible_mask": [True, True],
        "candidate_step_reach": [10.0, chosen_step_reach],
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
                "progress_m": chosen_progress,
                "mean_jerk_mps3": 1.0,
                "mean_lateral_acceleration_mps2": 1.2,
                "collision": False,
                "near_miss": False,
                "lane_violation": False,
                "red_light_violation": False,
            },
        ],
    }


def test_redesigned_atom_separability_finds_promising_toy_screen() -> None:
    report = analyze_records(
        [
            {"raw": _record(harmful=True), "context": _context()},
            {"raw": _record(harmful=False), "context": _context()},
        ],
        atom_schema_preflight_report=_preflight_report(),
        fail_on_formal_seeds=True,
        variants=(PREDECLARED_VARIANTS[1],),
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["analysis"]["future_outcome_labels_used_for_atoms"] is False
    assert report["analysis"]["thresholds_are_offline_oracle_diagnostics"] is True
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["failure_gap"]["primary_gap"] == (
        "no_gap_promising_redesigned_atom_screen_found"
    )
    best = report["ranked_atom_screens"][0]
    assert best["promising_descriptor_screen"] is True
    assert best["harmful_block_rate"] == 1.0
    assert best["beneficial_retain_rate"] == 1.0


def test_redesigned_atom_separability_blocks_when_preflight_not_ready() -> None:
    report = analyze_records(
        [{"raw": _record(harmful=True), "context": _context()}],
        atom_schema_preflight_report=_preflight_report(
            "atom_schema_redesign_preflight_rejected"
        ),
        variants=(PREDECLARED_VARIANTS[1],),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_redesigned_atom_separability_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [{"raw": _record(harmful=True), "context": _context(seed=11)}],
            atom_schema_preflight_report=_preflight_report(),
            fail_on_formal_seeds=True,
            variants=(PREDECLARED_VARIANTS[1],),
        )


def test_redesigned_atom_separability_atom_values_are_outcome_independent() -> None:
    base = _record(harmful=True)
    mutated = copy.deepcopy(base)
    mutated["candidate_closed_loop_outcomes"][0]["red_light_violation"] = False
    mutated["candidate_closed_loop_outcomes"][1]["red_light_violation"] = True
    mutated["candidate_closed_loop_outcomes"][1]["collision"] = True
    mutated["candidate_closed_loop_outcomes"][1]["progress_m"] = 0.0

    base_report = analyze_records(
        [{"raw": base, "context": _context()}],
        atom_schema_preflight_report=_preflight_report(),
        variants=(PREDECLARED_VARIANTS[1],),
    )
    mutated_report = analyze_records(
        [{"raw": mutated, "context": _context()}],
        atom_schema_preflight_report=_preflight_report(),
        variants=(PREDECLARED_VARIANTS[1],),
    )

    base_coverage = base_report["atom_coverage"]
    mutated_coverage = mutated_report["atom_coverage"]
    assert base_coverage == mutated_coverage

    base_rows = {
        row["screen_name"]: (row["allowed_switches"], row["blocked_switches"])
        for report in base_report["variants"][0]["atom_reports"]
        for row in report["threshold_screens"]
    }
    mutated_rows = {
        row["screen_name"]: (row["allowed_switches"], row["blocked_switches"])
        for report in mutated_report["variants"][0]["atom_reports"]
        for row in report["threshold_screens"]
    }
    assert base_rows == mutated_rows
