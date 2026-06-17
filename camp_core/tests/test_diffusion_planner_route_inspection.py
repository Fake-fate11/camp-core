from __future__ import annotations

import numpy as np

from scripts.integrations.inspect_diffusion_planner_routes import (
    _comparison_context_by_route,
    inspect_route_geometry,
)


def test_route_inspection_reports_turn_and_traffic_light_evidence() -> None:
    report = inspect_route_geometry(
        lanelet_ids=[1, 2],
        centerlines=[
            np.array([[0.0, 0.0], [10.0, 0.0]]),
            np.array([[10.0, 0.0], [10.0, 10.0]]),
        ],
        traffic_light_groups={2: 99},
    )

    assert report["route_length_m"] == 20.0
    assert report["endpoint_distance_m"] == np.sqrt(200.0)
    assert report["max_single_step_heading_change_deg"] == 90.0
    assert report["max_10m_net_heading_change_deg"] == 90.0
    assert report["traffic_light_lanelet_ids"] == [2]
    assert report["traffic_light_group_ids"] == [99]


def test_route_inspection_keeps_straight_route_low_turn() -> None:
    report = inspect_route_geometry(
        lanelet_ids=[1],
        centerlines=[np.array([[0.0, 0.0], [5.0, 0.0], [10.0, 0.0]])],
        traffic_light_groups={},
    )

    assert report["route_length_m"] == 10.0
    assert report["max_single_step_heading_change_deg"] == 0.0
    assert report["max_25m_net_heading_change_deg"] == 0.0
    assert report["traffic_light_lanelet_count"] == 0


def test_comparison_context_groups_run_keys_by_route() -> None:
    comparison = {
        "runs": [
            {
                "variant": "top1",
                "run_key": "route-a|1|200|0|0.3|True|perfect",
                "route_name": "route-a",
                "seed": 1,
                "steps": 200,
                "max_npcs": 0,
                "spawn_probability": 0.3,
                "traffic_lights": True,
                "advance_mode": "perfect",
            },
            {
                "variant": "camp",
                "run_key": "route-a|1|200|0|0.3|True|perfect",
                "route_name": "route-a",
                "seed": 1,
                "steps": 200,
                "max_npcs": 0,
                "spawn_probability": 0.3,
                "traffic_lights": True,
                "advance_mode": "perfect",
            },
        ]
    }

    context = _comparison_context_by_route(comparison)

    assert context["route-a"]["row_count"] == 2
    assert context["route-a"]["run_key_count"] == 1
    assert context["route-a"]["variants"] == ["camp", "top1"]
    assert context["route-a"]["traffic_lights"] == [True]
