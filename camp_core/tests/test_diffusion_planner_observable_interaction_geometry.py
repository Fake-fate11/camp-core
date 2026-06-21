from __future__ import annotations

import json
import pickle
from pathlib import Path
from types import SimpleNamespace

from scripts.integrations.analyze_diffusion_planner_observable_interaction_geometry import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
)


def _inventory_source(*, ready: bool = True) -> dict:
    return {
        "final_decision": {
            "status": (
                "observable_interaction_scenario_support_bottleneck_recorded"
                if ready
                else "observable_interaction_scenario_support_found"
            ),
            "passed": False if ready else True,
            "authorized_next_work": (
                "reject_observable_interaction_coverage_or_inspect_map_geometry_before_replay"
            ),
            "new_replay_authorized": False,
            "offline_separability_authorized": False,
            "camp_retraining_authorized": False,
        }
    }


def _plan(route_path: Path) -> dict:
    return {
        "plan_spec": {
            "runs": [
                {
                    "run_id": "tl_route59_seed1_npc4_tlon",
                    "route": str(route_path),
                }
            ]
        }
    }


def _payload() -> dict:
    return {
        "candidate_count": 2,
        "candidate_red_stopline_distance_m": [
            [4.0, 4.5, 5.5],
            [6.0, 6.5, 7.0],
        ],
        # Candidate 0 has a raw positive sample, but reduced mean alignment is
        # still nonpositive. This mirrors the real failure mode.
        "candidate_red_heading_alignment": [
            [-0.6, -0.3, 0.1],
            [-0.4, -0.2, -0.1],
        ],
        "candidate_min_obstacle_clearance_lower_bound_m": [40.0, None],
        "candidate_obstacle_slot_count": [1, 0],
    }


def _write_log(root: Path) -> None:
    baseline = root / "logs" / "tl_route59_seed1_npc4_tlon" / "baseline"
    observable = root / "logs" / "tl_route59_seed1_npc4_tlon" / "observable_logging"
    baseline.mkdir(parents=True)
    observable.mkdir(parents=True)
    baseline_rows = [{"observable_state_logging": None}]
    observable_rows = [{"observable_state_logging": _payload()}]
    (baseline / "camp_selection_log.json").write_text(
        json.dumps(baseline_rows),
        encoding="utf-8",
    )
    (observable / "camp_selection_log.json").write_text(
        json.dumps(observable_rows),
        encoding="utf-8",
    )


def _write_route(path: Path) -> None:
    map_path = path.with_suffix(".osm")
    map_path.write_text(
        "<osm><relation id='59'/><relation id='124'/></osm>",
        encoding="utf-8",
    )
    route = SimpleNamespace(
        map_path=str(map_path),
        start_pose=[117.0, 143.0, -1.0],
        goal_pose=[-5.0, -5.0, -1.4],
        start_lanelet_id=59,
        goal_lanelet_id=86,
        route_lanelet_ids=[59, 124, 33],
    )
    with path.open("wb") as handle:
        pickle.dump(route, handle)


def test_geometry_audit_diagnoses_reduced_alignment_and_clearance_budget(
    tmp_path: Path,
) -> None:
    route_path = tmp_path / "route.pkl"
    _write_route(route_path)
    _write_log(tmp_path)

    report = analyze(
        inventory_report=_inventory_source(),
        plan_report=_plan(route_path),
        root=tmp_path,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["current_observable_interaction_route_rejected"]
    assert report["final_decision"]["new_replay_authorized"] is False
    assert report["bottlenecks"]["red_bottleneck"] == "reduced_red_alignment_nonpositive"
    assert report["bottlenecks"]["clearance_bottleneck"] == (
        "clearance_budget_never_active"
    )
    assert report["geometry"]["red"]["reduced_near_budget_candidates"] == 1
    assert report["geometry"]["red"]["reduced_positive_alignment_candidates"] == 0
    assert report["geometry"]["red"]["raw_positive_alignment_samples"] == 1
    assert report["geometry"]["clearance"]["positive_obstacle_slot_candidates"] == 1
    assert report["geometry"]["clearance"]["inside_budget_candidates"] == 0
    assert report["route_summaries"][0]["map_exists"] is True
    assert report["route_summaries"][0]["map_route_relation_hits"] == 2


def test_geometry_audit_blocks_wrong_source(tmp_path: Path) -> None:
    route_path = tmp_path / "route.pkl"
    _write_route(route_path)
    _write_log(tmp_path)

    report = analyze(
        inventory_report=_inventory_source(ready=False),
        plan_report=_plan(route_path),
        root=tmp_path,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["source_gate"]["passed"] is False
    assert report["final_decision"]["new_replay_authorized"] is False
