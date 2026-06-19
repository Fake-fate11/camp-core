from __future__ import annotations

import copy

import pytest

from scripts.integrations.analyze_diffusion_planner_observable_state_inventory import (
    READY_STATUS,
    REJECT_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze_records,
)


def _source_report(
    status: str = "candidate_set_observable_support_rejected",
    bottleneck: str = "missing_observable_state_or_descriptor_information",
) -> dict:
    return {
        "final_decision": {
            "status": status,
            "primary_bottleneck": bottleneck,
            "authorized_next_work": None,
        },
        "records": {"total": 1, "candidate_rows": 2},
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": "/fake/camp_selection_log.json",
        "record_index": 0,
        "seed": seed,
        "scenario_buckets": ["overall", "traffic_light"],
    }


def _record(*, with_new_state: bool) -> dict:
    record = {
        "num_candidates": 2,
        "feasible_mask": [True, True],
        "candidate_dp_prior_deviation_cost": [0.0, 1.0],
        "candidate_step_reach": [10.0, 9.5],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [1.0, 1.1],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [1.0, 1.2],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 1.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.5],
        "dp_candidate_rewards": [
            {"centerline": -0.1, "lane_crossing": False, "sc_min_dist": 99.0},
            {"centerline": -0.2, "lane_crossing": True, "sc_min_dist": 8.0},
        ],
        "dp_scene_feature_names": [
            "route_lanes.present",
            "traffic_lights.present",
            "neighbor_agents_past.present",
        ],
        "dp_scene_features": [1.0, 1.0, 1.0],
        "candidate_closed_loop_outcomes": [
            {"collision": False, "progress_m": 10.0},
            {"collision": True, "progress_m": 9.0},
        ],
    }
    if with_new_state:
        record["candidate_lanelet_ids"] = [[10, 11], [10, 12]]
    return record


def test_observable_state_inventory_finds_new_candidate_state() -> None:
    report = analyze_records(
        [{"raw": _record(with_new_state=True), "context": _context()}],
        candidate_set_support_report=_source_report(),
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "offline_new_descriptor_separability_audit_design_only"
    )
    assert "candidate_lane_topology" in (
        report["final_decision"]["available_new_candidate_state_families"]
    )
    assert report["analysis"]["future_outcome_labels_inspected"] is False
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False


def test_observable_state_inventory_rejects_existing_proxies_only() -> None:
    report = analyze_records(
        [{"raw": _record(with_new_state=False), "context": _context()}],
        candidate_set_support_report=_source_report(),
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["primary_bottleneck"] == (
        "missing_logged_candidate_state"
    )
    assert report["final_decision"]["authorized_next_work"] == (
        "default_off_logging_preflight_design_only"
    )
    assert "existing_shape_support_proxy" in (
        report["final_decision"]["available_existing_proxy_families"]
    )


def test_observable_state_inventory_blocks_wrong_source_gate() -> None:
    report = analyze_records(
        [{"raw": _record(with_new_state=True), "context": _context()}],
        candidate_set_support_report=_source_report(
            status="candidate_set_observable_support_promising",
            bottleneck="observable_support_present",
        ),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_observable_state_inventory_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [{"raw": _record(with_new_state=True), "context": _context(seed=11)}],
            candidate_set_support_report=_source_report(),
            fail_on_formal_seeds=True,
        )


def test_observable_state_inventory_ignores_outcomes() -> None:
    base = _record(with_new_state=True)
    mutated = copy.deepcopy(base)
    mutated["candidate_closed_loop_outcomes"][0]["collision"] = True
    mutated["candidate_closed_loop_outcomes"][1]["collision"] = False
    mutated["candidate_closed_loop_outcomes"][1]["progress_m"] = 100.0

    base_report = analyze_records(
        [{"raw": base, "context": _context()}],
        candidate_set_support_report=_source_report(),
    )
    mutated_report = analyze_records(
        [{"raw": mutated, "context": _context()}],
        candidate_set_support_report=_source_report(),
    )

    assert base_report["family_reports"] == mutated_report["family_reports"]
