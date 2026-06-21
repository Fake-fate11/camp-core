from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_observable_interaction_descriptor_bottleneck import (
    NEXT_WORK_COVERAGE_PLAN,
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    analyze_records,
)


def _source(status: str = "observable_interaction_descriptor_separability_rejected") -> dict:
    return {
        "failure_gap": {
            "primary_gap": "harmful_block_rate_insufficient",
            "best_screen": {
                "screen_name": "top1_deviation_without_current_safety_gain_v1:allow_low",
                "feature_names": ["top1_deviation_without_current_safety_gain_v1"],
                "directions": ["allow_low"],
                "thresholds": [0.1],
                "harmful_block_rate": 0.6,
                "beneficial_retain_rate": 0.6,
                "allowed_harmful_rate": 0.4,
            },
        },
        "final_decision": {
            "status": status,
            "passed": False,
            "primary_gap": "observable_interaction_descriptors_do_not_separate_beneficial_and_harmful_candidates",
            "authorized_next_work": (
                "diagnose_observable_interaction_descriptor_bottleneck_before_new_replay"
            ),
            "promising_screen_count": 0,
        },
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": f"/tmp/route/seed_{seed}/camp_selection_log.json",
        "record_index": 0,
        "path_seeds": [seed],
    }


def _outcome(value: float, progress: float = 10.0) -> dict:
    return {
        "value": value,
        "feasible": True,
        "progress_m": progress,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
    }


def _payload(*, lateral: float = 0.0, projection: float = 1.0) -> dict:
    return {
        "schema_version": "dp_camp_observable_state_logging_v1",
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "candidate_count": 2,
        "finite_checks": {
            "candidate_route_projection_s_m": True,
            "candidate_route_lateral_error_m": True,
            "candidate_route_segment_index": True,
            "candidate_route_heading_change_rad": True,
            "candidate_min_obstacle_clearance_lower_bound_m": True,
            "candidate_obstacle_slot_count": True,
            "route_curvature_context_abs": True,
            "candidate_red_stopline_distance_m": True,
            "candidate_red_heading_alignment": True,
        },
        "candidate_route_projection_s_m": [[0.0, 1.0], [0.0, projection]],
        "candidate_route_lateral_error_m": [[0.0, 0.0], [0.0, lateral]],
        "candidate_route_segment_index": [[0.0, 1.0], [0.0, 1.0]],
        "candidate_route_heading_change_rad": [[0.0], [0.0]],
        "candidate_min_obstacle_clearance_lower_bound_m": [5.0, 5.0],
        "candidate_obstacle_slot_count": [0.0, 0.0],
        "candidate_red_stopline_distance_m": None,
        "candidate_red_heading_alignment": None,
        "route_curvature_context_abs": [0.0, 0.0],
    }


def _record(*, beneficial: bool, lateral: float = 0.0, projection: float = 1.0) -> dict:
    return {
        "num_candidates": 2,
        "seed": 1,
        "observable_state_logging": _payload(lateral=lateral, projection=projection),
        "candidate_closed_loop_outcomes": [
            _outcome(0.0),
            _outcome(2.0 if beneficial else -2.0),
        ],
    }


def test_bottleneck_diagnoses_collapsed_context_variation() -> None:
    report = analyze_records(
        [
            {"raw": _record(beneficial=True), "context": _context()},
            {"raw": _record(beneficial=False), "context": _context()},
        ],
        separability_report=_source(),
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == NEXT_WORK_COVERAGE_PLAN
    assert report["diagnosis"]["primary_gap"] == (
        "interaction_descriptors_collapse_due_to_missing_context_variation"
    )
    assert report["descriptor_diagnostics"]["collapsed_descriptor_count"] >= 3
    assert report["payload_materiality"]["red_context_material"] is False
    assert report["blocked_actions"]["camp_retraining_authorized"] is False
    assert report["blocked_actions"]["classic_benders_claim_authorized"] is False


def test_bottleneck_blocks_when_source_is_not_rejected() -> None:
    report = analyze_records(
        [{"raw": _record(beneficial=True), "context": _context()}],
        separability_report=_source("unexpected"),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_interaction_separability_source_before_bottleneck"
    )


def test_bottleneck_reports_best_screen_residual() -> None:
    report = analyze_records(
        [
            {"raw": _record(beneficial=True, lateral=0.0), "context": _context()},
            {"raw": _record(beneficial=False, lateral=0.0), "context": _context()},
            {"raw": _record(beneficial=True, lateral=1.0), "context": _context()},
        ],
        separability_report=_source(),
    )

    residual = report["screen_residual"]
    assert residual["has_best_screen"] is True
    assert residual["allowed_harmful_count"] >= 1
    assert "value_loss" in residual["allowed_harmful_reasons"]


def test_bottleneck_cli_reads_selection_log(tmp_path: Path) -> None:
    log_path = tmp_path / "route" / "seed_1" / "camp_selection_log.json"
    log_path.parent.mkdir(parents=True)
    log_path.write_text(
        json.dumps(
            [
                _record(beneficial=True),
                _record(beneficial=False),
            ]
        ),
        encoding="utf-8",
    )

    report = analyze([log_path], separability_report=_source())

    assert report["final_decision"]["status"] == READY_STATUS
