from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.analyze_diffusion_planner_observable_interaction_descriptor_separability import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    analyze_records,
)


def _preflight(status: str = "observable_interaction_descriptor_preflight_ready") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status == "observable_interaction_descriptor_preflight_ready",
            "authorized_next_work": (
                "offline_observable_interaction_descriptor_separability_screen_only"
            ),
        }
    }


def _contract(status: str = "matched_observable_outcome_contract_passed") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status == "matched_observable_outcome_contract_passed",
            "authorized_next_work": "offline_observable_descriptor_separability_screen_only",
        }
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": f"/tmp/route/seed_{seed}/camp_selection_log.json",
        "record_index": 0,
        "path_seeds": [seed],
    }


def _outcome(value: float, progress: float = 10.0, *, red: bool = False) -> dict:
    return {
        "value": value,
        "feasible": True,
        "progress_m": progress,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": red,
    }


def _payload(*, candidate_red_distance: float, candidate_red_alignment: float) -> dict:
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
        "candidate_route_projection_s_m": [[0.0, 1.0], [0.0, 1.0]],
        "candidate_route_lateral_error_m": [[0.0, 0.0], [0.0, 0.0]],
        "candidate_route_segment_index": [[0.0, 1.0], [0.0, 1.0]],
        "candidate_route_heading_change_rad": [[0.0], [0.0]],
        "candidate_min_obstacle_clearance_lower_bound_m": [5.0, 5.0],
        "candidate_obstacle_slot_count": [0.0, 0.0],
        "candidate_red_stopline_distance_m": [
            [1.0, 1.0],
            [candidate_red_distance, candidate_red_distance],
        ],
        "candidate_red_heading_alignment": [
            [1.0, 1.0],
            [candidate_red_alignment, candidate_red_alignment],
        ],
        "route_curvature_context_abs": [0.0, 0.0],
    }


def _record(*, beneficial: bool, red_distance: float, red_alignment: float) -> dict:
    return {
        "num_candidates": 2,
        "seed": 1,
        "observable_state_logging": _payload(
            candidate_red_distance=red_distance,
            candidate_red_alignment=red_alignment,
        ),
        "candidate_closed_loop_outcomes": [
            _outcome(0.0),
            _outcome(2.0 if beneficial else -2.0),
        ],
    }


def test_interaction_screen_finds_toy_red_separator() -> None:
    items = [
        {
            "raw": _record(beneficial=True, red_distance=10.0, red_alignment=0.0),
            "context": _context(),
        },
        {
            "raw": _record(beneficial=True, red_distance=10.0, red_alignment=0.0),
            "context": _context(),
        },
        {
            "raw": _record(beneficial=False, red_distance=1.0, red_alignment=1.0),
            "context": _context(),
        },
        {
            "raw": _record(beneficial=False, red_distance=1.0, red_alignment=1.0),
            "context": _context(),
        },
    ]

    report = analyze_records(
        items,
        preflight_report=_preflight(),
        matched_contract_report=_contract(),
        min_beneficial_candidates=2,
        min_harmful_candidates=2,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["analysis"]["future_outcome_labels_used_for_descriptors"] is False
    assert report["final_decision"]["new_replay_authorized"] is False
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["final_decision"]["classic_benders_claim_authorized"] is False
    best = report["ranked_screens"][0]
    assert best["promising_screen"] is True
    assert best["harmful_block_rate"] == 1.0
    assert best["beneficial_retain_rate"] == 1.0


def test_interaction_screen_blocks_without_preflight() -> None:
    report = analyze_records(
        [
            {
                "raw": _record(
                    beneficial=True,
                    red_distance=10.0,
                    red_alignment=0.0,
                ),
                "context": _context(),
            }
        ],
        preflight_report=_preflight("unexpected"),
        matched_contract_report=_contract(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_interaction_preflight_before_separability"
    )


def test_interaction_values_are_outcome_independent() -> None:
    base = _record(beneficial=True, red_distance=10.0, red_alignment=0.0)
    mutated = _record(beneficial=True, red_distance=10.0, red_alignment=0.0)
    mutated["candidate_closed_loop_outcomes"][1]["mean_jerk_mps3"] = 99.0

    base_report = analyze_records(
        [{"raw": base, "context": _context()}],
        preflight_report=_preflight(),
        matched_contract_report=_contract(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )
    mutated_report = analyze_records(
        [{"raw": mutated, "context": _context()}],
        preflight_report=_preflight(),
        matched_contract_report=_contract(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert base_report["feature_coverage"] == mutated_report["feature_coverage"]
    assert base_report["feature_reports"] == mutated_report["feature_reports"]


def test_interaction_screen_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [
                {
                    "raw": _record(
                        beneficial=True,
                        red_distance=10.0,
                        red_alignment=0.0,
                    ),
                    "context": _context(seed=11),
                }
            ],
            preflight_report=_preflight(),
            matched_contract_report=_contract(),
            fail_on_formal_seeds=True,
            min_beneficial_candidates=1,
            min_harmful_candidates=1,
        )


def test_interaction_cli_reads_selection_log(tmp_path: Path) -> None:
    log_path = tmp_path / "route" / "seed_1" / "camp_selection_log.json"
    log_path.parent.mkdir(parents=True)
    log_path.write_text(
        json.dumps(
            [
                _record(beneficial=True, red_distance=10.0, red_alignment=0.0),
                _record(beneficial=False, red_distance=1.0, red_alignment=1.0),
            ]
        ),
        encoding="utf-8",
    )

    report = analyze(
        [log_path],
        preflight_report=_preflight(),
        matched_contract_report=_contract(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
