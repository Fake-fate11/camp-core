from __future__ import annotations

import copy

import pytest

from scripts.integrations.analyze_diffusion_planner_atom_schema_redesign_preflight import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze_records,
)


def _descriptor_report(status: str = "descriptor_separability_rejected") -> dict:
    return {
        "final_decision": {
            "status": status,
            "authorized_next_work": None,
        },
        "failure_gap": {"primary_gap": "beneficial_and_harmful_descriptor_overlap"},
        "records": {"total": 1, "candidate_rows": 2},
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": "/fake/camp_selection_log.json",
        "record_index": 0,
        "seed": seed,
        "scenario_buckets": ["overall", "normal"],
    }


def _record() -> dict:
    return {
        "num_candidates": 2,
        "selected_index": 0,
        "feasible_mask": [True, True],
        "candidate_step_reach": [10.0, 9.5],
        "candidate_perfect_tracker_first_step_reach_m": [1.0, 0.9],
        "candidate_perfect_tracker_tail_average_speed_mps": [4.0, 3.5],
        "candidate_perfect_tracker_target_speed_mps": [5.0, 4.8],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [1.0, 1.2],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [1.1, 1.3],
        "candidate_perfect_tracker_yaw_rate_magnitude_rps": [0.1, 0.2],
        "candidate_dp_prior_deviation_cost": [1.0, 0.25],
        "candidate_horizon_union_planned_red_light_cost": [0.8, 0.2],
        "candidate_full_horizon_planned_red_light_cost": [0.9, 0.3],
        "candidate_red_stopping_margin_cost": [0.4, 0.1],
        "candidate_closed_loop_outcomes": [
            {
                "candidate_index": 0,
                "progress_m": 10.0,
                "mean_jerk_mps3": 1.0,
                "mean_lateral_acceleration_mps2": 1.1,
                "collision": False,
                "near_miss": False,
                "lane_violation": False,
                "red_light_violation": True,
            },
            {
                "candidate_index": 1,
                "progress_m": 9.5,
                "mean_jerk_mps3": 1.2,
                "mean_lateral_acceleration_mps2": 1.3,
                "collision": False,
                "near_miss": False,
                "lane_violation": False,
                "red_light_violation": False,
            },
        ],
    }


def test_atom_schema_redesign_preflight_authorizes_only_next_offline_audit() -> None:
    report = analyze_records(
        [{"raw": _record(), "context": _context()}],
        descriptor_separability_report=_descriptor_report(),
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "offline_redesigned_atom_separability_audit_design_only"
    )
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["analysis"]["future_outcome_labels_used_for_atoms"] is False
    assert report["analysis"]["future_outcome_labels_used_for_evaluation"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    assert all(row["passed_preflight"] for row in report["atom_reports"])
    assert all(check["passed"] for check in report["math_checks"])


def test_atom_schema_redesign_preflight_blocks_when_source_not_rejected() -> None:
    report = analyze_records(
        [{"raw": _record(), "context": _context()}],
        descriptor_separability_report=_descriptor_report(
            "descriptor_separability_promising_for_offline_certificate_design"
        ),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_atom_schema_redesign_preflight_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [{"raw": _record(), "context": _context(seed=11)}],
            descriptor_separability_report=_descriptor_report(),
            fail_on_formal_seeds=True,
        )


def test_atom_schema_redesign_preflight_is_outcome_independent() -> None:
    base = _record()
    mutated = copy.deepcopy(base)
    mutated["candidate_closed_loop_outcomes"][0]["red_light_violation"] = False
    mutated["candidate_closed_loop_outcomes"][1]["collision"] = True
    mutated["candidate_closed_loop_outcomes"][1]["progress_m"] = 0.0

    base_report = analyze_records(
        [{"raw": base, "context": _context()}],
        descriptor_separability_report=_descriptor_report(),
    )
    mutated_report = analyze_records(
        [{"raw": mutated, "context": _context()}],
        descriptor_separability_report=_descriptor_report(),
    )

    base_atoms = {
        row["name"]: row["summary"]
        for row in base_report["atom_reports"]
    }
    mutated_atoms = {
        row["name"]: row["summary"]
        for row in mutated_report["atom_reports"]
    }
    assert base_atoms == mutated_atoms
