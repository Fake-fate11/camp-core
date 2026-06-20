from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_observable_state_payload_coverage import (
    INSUFFICIENT_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    analyze,
)


LATENCY_FIELDS = (
    "latency_ms_observable_state_route_topology",
    "latency_ms_observable_state_traffic_light_relation",
    "latency_ms_observable_state_route_turn",
    "latency_ms_observable_state_neighbor_clearance",
)


def _payload(*, red_context: bool = False, offset: float = 0.0) -> dict:
    red_distance = (
        [[12.0 + offset, 11.0 + offset], [9.0 + offset, 8.5 + offset]]
        if red_context
        else None
    )
    red_alignment = (
        [[0.9, 0.8], [0.3, 0.2]]
        if red_context
        else None
    )
    return {
        "schema_version": "dp_camp_observable_state_logging_v1",
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "candidate_count": 2,
        "route_segment_count": 3,
        "red_route_point_count": 2 if red_context else 0,
        "horizons": {
            "support_steps": 2,
            "traffic_light_steps": 2,
            "turn_steps": 2,
        },
        "field_shapes": {
            "candidate_route_segment_index": [2, 2],
            "candidate_route_projection_s_m": [2, 2],
            "candidate_route_lateral_error_m": [2, 2],
            "candidate_red_stopline_distance_m": [2, 2] if red_context else None,
            "candidate_red_heading_alignment": [2, 2] if red_context else None,
            "candidate_route_heading_change_rad": [2, 1],
            "route_curvature_context_abs": [2],
            "candidate_min_obstacle_clearance_lower_bound_m": [2],
            "candidate_obstacle_slot_count": [2],
        },
        "finite_checks": {
            "candidate_route_segment_index": True,
            "candidate_route_projection_s_m": True,
            "candidate_route_lateral_error_m": True,
            "candidate_red_stopline_distance_m": True,
            "candidate_red_heading_alignment": True,
            "candidate_route_heading_change_rad": True,
            "route_curvature_context_abs": True,
            "candidate_min_obstacle_clearance_lower_bound_m": True,
            "candidate_obstacle_slot_count": True,
        },
        "latency_ms": {
            "latency_ms_observable_state_route_topology": 0.10,
            "latency_ms_observable_state_traffic_light_relation": 0.02,
            "latency_ms_observable_state_route_turn": 0.03,
            "latency_ms_observable_state_neighbor_clearance": 0.04,
        },
        "candidate_route_segment_index": [[0, 1], [1, 2]],
        "candidate_route_projection_s_m": [
            [offset, offset + 1.0],
            [offset + 0.1, offset + 1.4],
        ],
        "candidate_route_lateral_error_m": [[0.0, 0.2], [0.1, -0.4]],
        "candidate_red_stopline_distance_m": red_distance,
        "candidate_red_heading_alignment": red_alignment,
        "candidate_route_heading_change_rad": [[0.02], [0.12]],
        "route_curvature_context_abs": [0.01, 0.03],
        "candidate_min_obstacle_clearance_lower_bound_m": [3.0, 1.5],
        "candidate_obstacle_slot_count": [0, 2],
    }


def _record(payload: dict) -> dict:
    record = {
        "candidate_closed_loop_outcomes": None,
        "observable_state_logging": payload,
    }
    for field in LATENCY_FIELDS:
        record[field] = payload["latency_ms"][field]
    return record


def _write_log(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records), encoding="utf-8")


def test_payload_coverage_validates_tiny_no_red_smoke_as_insufficient(
    tmp_path: Path,
) -> None:
    records = [_record(_payload(offset=float(index))) for index in range(3)]
    log_path = tmp_path / "logging_enabled" / "camp_selection_log.json"
    _write_log(log_path, records)

    report = analyze([log_path], label="unit")

    assert report["validation"]["errors"] == []
    assert report["final_decision"]["status"] == INSUFFICIENT_STATUS
    assert report["final_decision"]["primary_gap"] == (
        "too_few_logged_records_for_materiality"
    )
    assert report["context"]["red_context_records"] == 0
    assert report["final_decision"]["closed_loop_replay_authorized"] is False
    assert report["final_decision"]["authorized_next_work"] == (
        "default_off_observable_state_logging_broader_nonformal_plan_only"
    )


def test_payload_coverage_rejects_future_outcome_leakage(tmp_path: Path) -> None:
    payload = _payload(red_context=True)
    payload["candidate_closed_loop_outcomes"] = [{"collision": True}]
    record = _record(payload)
    record["candidate_closed_loop_outcomes"] = [{"collision": False}]
    log_path = tmp_path / "camp_selection_log.json"
    _write_log(log_path, [record])

    report = analyze([log_path], min_records_for_materiality=1)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["validation_passed"] is False
    assert any("closed-loop outcome" in error for error in report["validation"]["errors"])
    assert report["final_decision"]["authorized_next_work"] is None


def test_payload_coverage_accepts_sufficient_synthetic_materiality(
    tmp_path: Path,
) -> None:
    records = [
        _record(_payload(red_context=True, offset=float(index)))
        for index in range(12)
    ]
    log_path = tmp_path / "seed_1" / "camp_selection_log.json"
    _write_log(log_path, records)

    report = analyze([tmp_path], label="sufficient")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["materiality_gate_passed"] is True
    assert report["context"]["red_context_records"] == 12
    assert len(report["material_candidate_fields"]) >= 4
    assert report["final_decision"]["authorized_next_work"] == (
        "offline_no_leak_observable_descriptor_separability_design_only"
    )
    assert report["final_decision"]["full36_authorized"] is False
    assert report["analysis"]["future_outcome_leakage"] is False


def test_payload_coverage_rejects_finite_check_failure(tmp_path: Path) -> None:
    payload = copy.deepcopy(_payload(red_context=True))
    payload["finite_checks"]["candidate_route_projection_s_m"] = False
    log_path = tmp_path / "camp_selection_log.json"
    _write_log(log_path, [_record(payload)])

    report = analyze([log_path], min_records_for_materiality=1)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert any("finite_checks failed" in error for error in report["validation"]["errors"])
