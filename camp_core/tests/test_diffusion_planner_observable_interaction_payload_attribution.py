from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_observable_interaction_payload_attribution import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    SUPPORT_PRESENT_STATUS,
    analyze,
)
from scripts.integrations.analyze_diffusion_planner_observable_interaction_scenario_support import (
    BOTTLENECK_STATUS,
)


def _scenario_support_bottleneck() -> dict:
    return {
        "final_decision": {
            "status": BOTTLENECK_STATUS,
            "passed": False,
        }
    }


def _route_geometry_ready() -> dict:
    return {
        "analysis": {"name": "dp_camp_route_scenario_inspection_v1"},
        "routes": [
            {
                "name": "tl_route",
                "geometry": {"traffic_light_lanelet_count": 2},
            }
        ],
    }


def _payload(kind: str) -> dict:
    if kind == "attribution":
        return {
            "candidate_count": 3,
            "red_route_point_count": 5,
            "candidate_red_stopline_distance_m": [
                [4.0, 4.5],
                [7.0, 7.5],
                [4.0, 4.2],
            ],
            "candidate_red_heading_alignment": [
                [-0.3, -0.1],
                [0.2, 0.4],
                [0.4, -0.6],
            ],
            "candidate_min_obstacle_clearance_lower_bound_m": [None, 40.0, 3.0],
            "candidate_obstacle_slot_count": [0, 1, 1],
        }
    if kind == "support":
        return {
            "candidate_count": 1,
            "red_route_point_count": 3,
            "candidate_red_stopline_distance_m": [[4.0, 4.2]],
            "candidate_red_heading_alignment": [[0.2, 0.4]],
            "candidate_min_obstacle_clearance_lower_bound_m": [1.5],
            "candidate_obstacle_slot_count": [1],
        }
    raise AssertionError(kind)


def _write_log(root: Path, *, seed: int, kind: str) -> Path:
    log_dir = root / "route" / f"seed_{seed}" / "npc_1" / "spawn_0p3" / "tl_on" / "static"
    log_dir.mkdir(parents=True)
    rows = [
        {"observable_state_logging": None},
        {"observable_state_logging": _payload(kind)},
    ]
    path = log_dir / "camp_selection_log.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def test_payload_attribution_diagnoses_missing_support(tmp_path: Path) -> None:
    _write_log(tmp_path, seed=1, kind="attribution")

    report = analyze(
        [tmp_path],
        scenario_support_report=_scenario_support_bottleneck(),
        route_geometry_report=_route_geometry_ready(),
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["new_replay_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["red_attribution"]["candidate_reason_counts"] == {
        "red_alignment_nonpositive": 1,
        "red_distance_outside_budget": 1,
        "red_step_positive_but_mean_nonpositive": 1,
    }
    assert report["clearance_attribution"]["candidate_reason_counts"] == {
        "obstacle_slots_absent": 1,
        "obstacles_present_but_far": 2,
    }
    red_metrics = report["red_attribution"]["metrics"]
    assert red_metrics["candidate_red_distance_within_budget_count"] == 2
    assert red_metrics["candidate_red_step_alignment_positive_count"] == 2
    assert red_metrics["candidate_red_support_count"] == 0
    clearance_metrics = report["clearance_attribution"]["metrics"]
    assert clearance_metrics["candidate_obstacle_slots_positive_count"] == 2
    assert clearance_metrics["candidate_clearance_within_budget_count"] == 0


def test_payload_attribution_reports_support_when_present(tmp_path: Path) -> None:
    _write_log(tmp_path, seed=1, kind="support")

    report = analyze(
        [tmp_path],
        scenario_support_report=_scenario_support_bottleneck(),
        route_geometry_report=_route_geometry_ready(),
    )

    assert report["final_decision"]["status"] == SUPPORT_PRESENT_STATUS
    assert report["red_attribution"]["candidate_reason_counts"]["red_supported"] == 1
    assert (
        report["clearance_attribution"]["candidate_reason_counts"][
            "clearance_supported"
        ]
        == 1
    )


def test_payload_attribution_excludes_formal_seed_logs(tmp_path: Path) -> None:
    _write_log(tmp_path, seed=11, kind="support")
    _write_log(tmp_path, seed=1, kind="attribution")

    report = analyze(
        [tmp_path],
        scenario_support_report=_scenario_support_bottleneck(),
        route_geometry_report=_route_geometry_ready(),
    )

    assert report["counts"]["input_log_paths"] == 2
    assert report["counts"]["excluded_formal_seed_logs"] == 1
    assert report["counts"]["formal_seed_records"] == 0
    assert report["final_decision"]["status"] == READY_STATUS


def test_payload_attribution_blocks_when_sources_are_not_ready(tmp_path: Path) -> None:
    _write_log(tmp_path, seed=1, kind="support")
    source = deepcopy(_scenario_support_bottleneck())
    source["final_decision"]["status"] = "unexpected"

    report = analyze(
        [tmp_path],
        scenario_support_report=source,
        route_geometry_report=_route_geometry_ready(),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["source_gate"]["passed"] is False
