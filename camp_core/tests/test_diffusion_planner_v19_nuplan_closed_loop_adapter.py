import importlib
import math
from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.integrations import nuplan_causal_adapter
from camp_core.integrations.diffusion_planner_causal_materializer import (
    validate_causal_dp_input,
)


def _point(x: float, y: float, heading: float = 0.0) -> SimpleNamespace:
    return SimpleNamespace(x=x, y=y, heading=heading)


def _lane(
    lane_id: str,
    start: float,
    stop: float,
    *,
    y: float = 0.0,
) -> SimpleNamespace:
    center = [_point(start, y), _point(stop, y)]
    left = [_point(start, y + 2.0), _point(stop, y + 2.0)]
    right = [_point(start, y - 2.0), _point(stop, y - 2.0)]
    return SimpleNamespace(
        id=lane_id,
        baseline_path=SimpleNamespace(discrete_path=center),
        left_boundary=SimpleNamespace(discrete_path=left),
        right_boundary=SimpleNamespace(discrete_path=right),
        speed_limit_mps=10.0,
        outgoing_edges=[],
    )


def _state(x: float, timestamp_us: int) -> SimpleNamespace:
    return SimpleNamespace(
        rear_axle=_point(x, 0.0),
        dynamic_car_state=SimpleNamespace(
            rear_axle_velocity_2d=SimpleNamespace(x=1.0, y=0.0),
            rear_axle_acceleration_2d=SimpleNamespace(x=0.0, y=0.0),
        ),
        car_footprint=SimpleNamespace(
            length=5.0,
            width=2.0,
            vehicle_parameters=SimpleNamespace(wheel_base=3.0),
        ),
        time_us=timestamp_us,
    )


def _tracked(
    token: str,
    kind: str,
    x: float,
    *,
    length: float = 4.0,
    width: float = 2.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        track_token=token,
        tracked_object_type=SimpleNamespace(name=kind),
        center=_point(x, 0.0),
        velocity=SimpleNamespace(x=1.0, y=0.0),
        box=SimpleNamespace(length=length, width=width, height=1.5),
    )


def _fixture(*, stale_traffic: bool = False, future: bool = False):
    ego_states = [_state(index * 0.1, index * 100_000) for index in range(31)]
    observations = []
    for index in range(31):
        ego_x = index * 0.1
        objects = [_tracked("vehicle-a", "VEHICLE", ego_x + 5.0)]
        if index == 30:
            objects.append(_tracked("barrier-a", "BARRIER", ego_x + 8.0))
        observations.append(
            SimpleNamespace(
                tracked_objects=SimpleNamespace(tracked_objects=objects)
            )
        )
    history = SimpleNamespace(
        ego_states=ego_states,
        observations=observations,
        sample_interval=0.1,
    )
    current = SimpleNamespace(
        history=history,
        iteration=SimpleNamespace(index=30, time_us=3_000_000),
        traffic_light_data=[
            SimpleNamespace(
                lane_connector_id="lane-0",
                status=SimpleNamespace(name="GREEN"),
                timestamp=2_900_000 if stale_traffic else 3_000_000,
            )
        ],
    )
    if future:
        current.expert_future = np.ones((80, 3), dtype=np.float32)

    first = _lane("lane-0", 0.0, 10.0)
    second = _lane("lane-1", 10.0, 20.0)
    first.outgoing_edges = [second]
    map_api = SimpleNamespace(
        get_map_object=lambda object_id, _layer: {
            "rb-0": SimpleNamespace(interior_edges=[first]),
            "rb-1": SimpleNamespace(interior_edges=[second]),
        }.get(object_id)
    )
    initialization = SimpleNamespace(
        route_roadblock_ids=["rb-0", "rb-1"],
        mission_goal=_point(20.0, 0.0),
        map_api=map_api,
    )
    return current, initialization


def test_live_planner_input_materializes_exact_causal_schema() -> None:
    current, initialization = _fixture()

    materialized = nuplan_causal_adapter.materialize_nuplan_planner_input(
        current, initialization
    )

    assert validate_causal_dp_input(materialized.dp_input) == []
    assert materialized.metadata["source"] == "official_nuplan_planner_input"
    assert materialized.metadata["observable_dynamic_limit"] == 32
    assert materialized.metadata["observable_static_limit"] == 5
    assert materialized.dp_input["neighbor_agents_past"][0, -1, 0] == pytest.approx(
        5.0
    )
    assert materialized.dp_input["static_objects"][0, 0] == pytest.approx(8.0)
    assert materialized.dp_input["route_lanes_has_speed_limit"][:2].all()
    assert materialized.dp_input["route_lanes"][0, 0, 8] == pytest.approx(1.0)


def test_live_planner_input_rejects_future_and_stale_traffic() -> None:
    current, initialization = _fixture(future=True)
    with pytest.raises(ValueError, match="future|label|outcome"):
        nuplan_causal_adapter.materialize_nuplan_planner_input(
            current, initialization
        )

    current, initialization = _fixture(stale_traffic=True)
    with pytest.raises(ValueError, match="same.*tick"):
        nuplan_causal_adapter.materialize_nuplan_planner_input(
            current, initialization
        )


def test_relative_pose_conversion_does_not_rewrite_trajectory() -> None:
    try:
        module = importlib.import_module(
            "camp_core.integrations.nuplan_closed_loop_adapter"
        )
    except ModuleNotFoundError:
        pytest.fail("the official nuPlan AbstractPlanner adapter is missing")
    trajectory = np.zeros((80, 4), dtype=np.float32)
    trajectory[:, 0] = np.arange(80, dtype=np.float32) * 0.1
    trajectory[:, 2] = math.cos(0.25)
    trajectory[:, 3] = math.sin(0.25)

    poses = module.dp_trajectory_to_relative_poses(trajectory)

    assert np.array_equal(poses[:, :2], trajectory[:, :2])
    assert np.allclose(poses[:, 2], 0.25)
    trajectory[0, 0] = 99.0
    assert poses[0, 0] != 99.0


def test_official_planner_is_a_non_oracle_detections_tracks_adapter(tmp_path) -> None:
    abstract = pytest.importorskip(
        "nuplan.planning.simulation.planner.abstract_planner"
    )
    observation = pytest.importorskip(
        "nuplan.planning.simulation.observation.observation_type"
    )
    module = importlib.import_module(
        "camp_core.integrations.nuplan_closed_loop_adapter"
    )

    assert issubclass(module.NuPlanCAMPPlanner, abstract.AbstractPlanner)
    planner = module.NuPlanCAMPPlanner(
        arm="dp_default",
        bridge_root=tmp_path,
        worker_command=("/fixed/dp/python", "/fixed/worker.py"),
        log_name="log-a",
        scenario_token="scenario-a",
        camp_head="a" * 40,
        dp_head="b" * 40,
        nuplan_head="c" * 40,
    )

    assert planner.requires_scenario is False
    assert planner.name() == "DP-default deterministic/MAP baseline"
    assert planner.observation_type() is observation.DetectionsTracks
