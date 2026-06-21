from __future__ import annotations

import json
import pickle
from pathlib import Path
from types import SimpleNamespace

from scripts.integrations.plan_diffusion_planner_observable_interaction_route_support_discovery import (
    AUTHORIZED_REJECT_NEXT_WORK,
    REJECT_STATUS,
    build_report,
)


def _support_preflight(*, ready: bool = True) -> dict:
    return {
        "route_rejection": {
            "red_reason": "reduced_red_alignment_nonpositive",
            "red_reduced_near_budget_candidates": 2,
            "red_reduced_positive_alignment_candidates": 0,
            "clearance_reason": "clearance_budget_never_active",
            "clearance_positive_obstacle_slot_candidates": 16,
            "clearance_inside_budget_candidates": 0,
        },
        "final_decision": {
            "status": (
                "observable_interaction_support_preflight_current_route_rejected"
                if ready
                else "observable_interaction_support_preflight_source_not_ready"
            ),
            "passed": ready,
            "current_observable_interaction_route_rejected": ready,
            "support_smoke_predeclared": False,
            "authorized_next_work": (
                "predeclare_observable_interaction_route_support_discovery_only"
                if ready
                else None
            ),
            "new_replay_authorized": False,
            "offline_separability_authorized": False,
            "CAMP_retraining_authorized": False,
        },
    }


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


def _write_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "npc": {"spawn_probability": 0.3},
                "traffic_lights": "on",
            }
        ),
        encoding="utf-8",
    )


def test_route_support_discovery_rejects_family_without_justified_candidate(
    tmp_path: Path,
) -> None:
    route = tmp_path / "route.pkl"
    config = tmp_path / "replay_default.json"
    _write_route(route)
    _write_config(config)

    report = build_report(
        support_preflight_report=_support_preflight(),
        routes=[route],
        sim_configs=[config],
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["observable_interaction_route_family_rejected"]
    assert report["final_decision"]["support_smoke_predeclared"] is False
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_REJECT_NEXT_WORK
    assert report["final_decision"]["new_replay_authorized"] is False
    assert report["final_decision"]["offline_separability_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    assert report["candidate_proposals"] == []
    assert report["route_inventory"]["routes"][0]["map_route_relation_hits"] == 2
    assert report["sim_config_inventory"]["configs"][0][
        "has_spawn_configuration"
    ] is True
    assert report["evidence_assessment"][
        "can_justify_positive_reduced_red_alignment"
    ] is False
    assert report["evidence_assessment"]["can_justify_near_clearance_support"] is False


def test_route_support_discovery_blocks_invalid_preflight_source(
    tmp_path: Path,
) -> None:
    route = tmp_path / "route.pkl"
    _write_route(route)

    report = build_report(
        support_preflight_report=_support_preflight(ready=False),
        routes=[route],
    )

    assert report["final_decision"]["status"] == (
        "observable_interaction_route_support_discovery_source_not_ready"
    )
    assert report["final_decision"]["passed"] is False
    assert report["source_gate"]["passed"] is False
    assert report["final_decision"]["authorized_next_work"] is None
    assert report["final_decision"]["new_replay_authorized"] is False
