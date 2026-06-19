from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_observable_state_logging_smoke import (
    analyze,
)
from scripts.integrations.plan_diffusion_planner_observable_state_logging_smoke import (
    READY_STATUS,
    REJECT_STATUS,
    build_report,
)


LATENCY_FIELDS = (
    "latency_ms_observable_state_route_topology",
    "latency_ms_observable_state_traffic_light_relation",
    "latency_ms_observable_state_route_turn",
    "latency_ms_observable_state_neighbor_clearance",
)


def _metadata(*, enabled: bool, records: int) -> dict:
    return {
        "camp_observable_state_logging": {
            "schema_version": "dp_camp_observable_state_logging_v1",
            "enabled": enabled,
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "online_selector_change": False,
            "classical_benders_claim": False,
            "records": records,
            "fields": [
                "candidate_route_segment_index",
                "candidate_route_projection_s_m",
                "candidate_route_lateral_error_m",
                "candidate_red_stopline_distance_m",
                "candidate_red_heading_alignment",
                "candidate_route_heading_change_rad",
                "route_curvature_context_abs",
                "candidate_min_obstacle_clearance_lower_bound_m",
                "candidate_obstacle_slot_count",
            ],
            "latency_fields": list(LATENCY_FIELDS),
        },
        "benchmark": {"seed": 1, "advance_mode": "perfect"},
    }


def _payload() -> dict:
    return {
        "schema_version": "dp_camp_observable_state_logging_v1",
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "candidate_count": 2,
        "route_segment_count": 1,
        "red_route_point_count": 0,
        "horizons": {
            "support_steps": 3,
            "traffic_light_steps": 3,
            "turn_steps": 3,
        },
        "field_shapes": {
            "candidate_route_segment_index": [2, 3],
            "candidate_route_projection_s_m": [2, 3],
            "candidate_route_lateral_error_m": [2, 3],
            "candidate_red_stopline_distance_m": None,
            "candidate_red_heading_alignment": None,
            "candidate_route_heading_change_rad": [2, 2],
            "route_curvature_context_abs": [],
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
            "latency_ms_observable_state_route_topology": 0.1,
            "latency_ms_observable_state_traffic_light_relation": 0.2,
            "latency_ms_observable_state_route_turn": 0.3,
            "latency_ms_observable_state_neighbor_clearance": 0.4,
        },
        "candidate_route_segment_index": [[0, 0, 0], [0, 0, 0]],
        "candidate_route_projection_s_m": [[0.0, 1.0, 2.0], [0.0, 0.9, 1.8]],
        "candidate_route_lateral_error_m": [[0.0, 0.1, 0.2], [0.0, -0.1, -0.2]],
        "candidate_red_stopline_distance_m": None,
        "candidate_red_heading_alignment": None,
        "candidate_route_heading_change_rad": [[0.0, 0.0], [0.0, 0.0]],
        "route_curvature_context_abs": [],
        "candidate_min_obstacle_clearance_lower_bound_m": [1.0, None],
        "candidate_obstacle_slot_count": [1, 0],
    }


def _record(*, payload: dict | None) -> dict:
    record = {
        "candidate_closed_loop_outcomes": None,
        "observable_state_logging": payload,
    }
    for field in LATENCY_FIELDS:
        record[field] = 0.0 if payload is None else payload["latency_ms"][field]
    return record


def _write_run(root: Path, *, enabled: bool, payload: dict | None) -> None:
    root.mkdir(parents=True)
    root.joinpath("camp_selection_log.json").write_text(
        json.dumps([_record(payload=payload)]),
        encoding="utf-8",
    )
    root.joinpath("camp_validation_summary.json").write_text(
        json.dumps(_metadata(enabled=enabled, records=int(enabled))),
        encoding="utf-8",
    )


def test_observable_state_logging_smoke_audit_accepts_paired_payload(
    tmp_path: Path,
) -> None:
    _write_run(tmp_path / "baseline", enabled=False, payload=None)
    _write_run(tmp_path / "candidate", enabled=True, payload=_payload())

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["passed"] is True
    assert report["counts"]["baseline_payload_records"] == 0
    assert report["counts"]["candidate_payload_records"] == 1
    assert report["errors"] == []


def test_observable_state_logging_smoke_audit_rejects_future_payload_key(
    tmp_path: Path,
) -> None:
    payload = deepcopy(_payload())
    payload["candidate_closed_loop_outcomes"] = [{"collision": True}]
    _write_run(tmp_path / "baseline", enabled=False, payload=None)
    _write_run(tmp_path / "candidate", enabled=True, payload=payload)

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["passed"] is False
    assert any("future outcome key" in error for error in report["errors"])


def test_observable_state_logging_smoke_plan_authorizes_paired_three_step_only() -> None:
    report = build_report(label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["closed_loop_replay_authorized"] is True
    assert report["final_decision"]["Full36_authorized"] is False
    baseline_command = report["commands"]["baseline_replay"]
    candidate_command = report["commands"]["candidate_replay"]
    assert "--camp_observable_state_logging" not in baseline_command
    assert "--camp_observable_state_logging" in candidate_command
    assert baseline_command[baseline_command.index("--steps") + 1] == "3"
    assert candidate_command[candidate_command.index("--seed") + 1] == "1"


def test_observable_state_logging_smoke_plan_rejects_missing_payload_audit(
    tmp_path: Path,
) -> None:
    report = build_report(payload_audit_source=tmp_path / "missing.py")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["closed_loop_replay_authorized"] is False
    failed = [check for check in report["source_checks"] if not check["passed"]]
    assert [check["name"] for check in failed] == ["payload_audit_available"]
