from __future__ import annotations

import numpy as np

from scripts.integrations.inspect_diffusion_planner_routes import (
    _comparison_context_by_route,
    _labeling_guidance,
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
        transition_relations=[
            {
                "from_lanelet_id": 1,
                "to_lanelet_id": 2,
                "relation": "Successor",
                "is_lateral": False,
            }
        ],
    )

    assert report["route_length_m"] == 20.0
    assert report["endpoint_distance_m"] == np.sqrt(200.0)
    assert report["max_single_step_heading_change_deg"] == 90.0
    assert report["max_10m_net_heading_change_deg"] == 90.0
    assert report["traffic_light_lanelet_ids"] == [2]
    assert report["traffic_light_group_ids"] == [99]
    assert report["traffic_light_lanelet_geometry"] == [
        {
            "route_index": 1,
            "lanelet_id": 2,
            "length_m": 10.0,
            "cumulative_start_m": 10.0,
            "cumulative_end_m": 20.0,
            "net_heading_change_deg": 0.0,
            "max_single_step_heading_change_deg": 0.0,
            "traffic_light_group_id": 99,
        }
    ]
    assert report["transition_relation_counts"] == {"Successor": 1}
    assert report["lateral_transition_count"] == 0
    assert report["has_lane_change_or_merge_evidence"] is False


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


def test_route_inspection_reports_lane_change_transition_evidence() -> None:
    report = inspect_route_geometry(
        lanelet_ids=[7, 8, 568],
        centerlines=[
            np.array([[0.0, 0.0], [10.0, 0.0]]),
            np.array([[0.0, -3.5], [10.0, -3.5]]),
            np.array([[10.0, -3.5], [30.0, -3.5]]),
        ],
        traffic_light_groups={},
        transition_relations=[
            {
                "from_lanelet_id": 7,
                "to_lanelet_id": 8,
                "relation": "Right",
                "is_lateral": True,
            },
            {
                "from_lanelet_id": 8,
                "to_lanelet_id": 568,
                "relation": "Successor",
                "is_lateral": False,
            },
        ],
    )
    guidance = _labeling_guidance(report)

    assert report["transition_relation_counts"] == {"Right": 1, "Successor": 1}
    assert report["lateral_transition_count"] == 1
    assert report["has_lane_change_or_merge_evidence"] is True
    assert guidance["lane_change_or_merge_route_evidence"] == {
        "has_lateral_transition": True,
        "lateral_transition_count": 1,
        "transition_relation_counts": {"Right": 1, "Successor": 1},
    }
    assert guidance["candidate_buckets_supported_by_route_evidence"] == [
        "lane_change_or_merge"
    ]


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
