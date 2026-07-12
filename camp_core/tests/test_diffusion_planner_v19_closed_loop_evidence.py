from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from shapely.geometry import box

from camp_core.integrations.diffusion_planner import _summarize_trajectory_log
from camp_core.integrations.nuplan_closed_loop_evidence import (
    materialize_closed_loop_evidence,
)


def _point(x: float, y: float) -> SimpleNamespace:
    return SimpleNamespace(x=x, y=y, heading=0.0)


def _state(index: int, *, y: float = 0.0) -> SimpleNamespace:
    x = float(index)
    return SimpleNamespace(
        time_us=index * 50_000,
        rear_axle=_point(x, y),
        dynamic_car_state=SimpleNamespace(speed=20.0),
        car_footprint=SimpleNamespace(
            geometry=box(x - 0.4, y - 0.4, x + 0.4, y + 0.4)
        ),
    )


def _tracked(x: float, y: float) -> SimpleNamespace:
    return SimpleNamespace(
        box=SimpleNamespace(geometry=box(x - 0.4, y - 0.4, x + 0.4, y + 0.4))
    )


def _fixture():
    states = [_state(0), _state(1), _state(2), _state(3, y=3.0)]
    obstacle_x = [0.0, 2.8, 5.8, None]
    samples = []
    for index, state in enumerate(states):
        objects = [] if obstacle_x[index] is None else [_tracked(obstacle_x[index], 0.0)]
        traffic = []
        if index == 0:
            traffic = [
                SimpleNamespace(
                    lane_connector_id="lc",
                    status=SimpleNamespace(name="RED"),
                )
            ]
        samples.append(
            SimpleNamespace(
                iteration=SimpleNamespace(index=index),
                ego_state=state,
                observation=SimpleNamespace(
                    tracked_objects=SimpleNamespace(tracked_objects=objects)
                ),
                traffic_light_status=traffic,
            )
        )
    lane = SimpleNamespace(
        id="lane",
        polygon=box(-1.0, -1.0, 5.0, 1.0),
        baseline_path=SimpleNamespace(
            discrete_path=[_point(0.0, 0.0), _point(4.0, 0.0)]
        ),
        outgoing_edges=[],
    )
    roadblock = SimpleNamespace(interior_edges=[lane])
    connector = SimpleNamespace(
        baseline_path=SimpleNamespace(
            discrete_path=[_point(1.0, 0.0), _point(2.0, 0.0)]
        )
    )
    map_api = SimpleNamespace(
        get_map_object=lambda object_id, _layer: {
            "rb": roadblock,
            "lc": connector,
        }.get(str(object_id))
    )
    scenario = SimpleNamespace(
        map_api=map_api,
        get_route_roadblock_ids=lambda: ["rb"],
        get_mission_goal=lambda: _point(4.0, 0.0),
    )
    receipts = [
        {
            "iteration_index": index,
            "selected_planned_red_light_cost": cost,
            "planned_red_source": "fixed_dp_red_cost_v18",
        }
        for index, cost in enumerate((0.0, 2e-12, 0.0))
    ]
    return SimpleNamespace(data=samples), scenario, receipts


def test_closed_loop_evidence_materializes_frozen_safety_fields() -> None:
    history, scenario, receipts = _fixture()

    summary = materialize_closed_loop_evidence(history, scenario, receipts)

    assert summary["obb_collision_rate"] == pytest.approx(1 / 4)
    assert summary["near_miss_rate"] == pytest.approx(2 / 4)
    assert summary["lane_violation_rate"] == pytest.approx(1 / 4)
    assert summary["red_light_violation_rate"] == pytest.approx(1 / 3)
    assert summary["planned_red_light_violation_rate"] == pytest.approx(1 / 3)
    assert summary["mean_jerk_magnitude_mps3"] == pytest.approx(0.0)
    assert summary["mean_lateral_acceleration_mps2"] == pytest.approx(0.0)
    assert summary["route_completion_rate"] == pytest.approx(0.75)
    assert summary["source_scope"] == "official_full_posterior_observation"


def test_closed_loop_evidence_rejects_incomplete_sources() -> None:
    history, scenario, receipts = _fixture()
    with pytest.raises(ValueError, match="receipt"):
        materialize_closed_loop_evidence(history, scenario, receipts[:-1])

    history.data[2].ego_state.time_us += 2_000
    with pytest.raises(ValueError, match="timestamp"):
        materialize_closed_loop_evidence(history, scenario, receipts)


def test_trajectory_summary_uses_observed_dt() -> None:
    records = [
        {"x": float(index), "y": 0.0, "heading": 0.0, "speed": speed}
        for index, speed in enumerate((0.0, 1.0, 3.0, 6.0))
    ]

    summary = _summarize_trajectory_log(records, dt=0.05)

    assert summary["mean_jerk_magnitude_mps3"] == pytest.approx(400.0)
