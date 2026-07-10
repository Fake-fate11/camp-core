from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import struct

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_materializer import (
    materialize_causal_dp_input,
)
from camp_core.integrations.nuplan_causal_adapter import (
    NuPlanCausalSourceError,
    causal_history,
    decode_projected_gpkg_geometry,
    derive_source_dt_s,
    encode_route_lane,
    load_nuplan_route_snapshot,
    select_mission_route_window,
)


def test_gpkg_geometry_is_projected_from_header_crs_to_map_crs() -> None:
    from shapely import LineString, to_wkb

    source = LineString([(-115.1700, 36.1000), (-115.1690, 36.1000)])
    gpkg_blob = b"GP" + bytes([0, 1]) + struct.pack("<i", 4326) + to_wkb(source)

    projected = decode_projected_gpkg_geometry(gpkg_blob, "epsg:32611")

    start, end = projected.coords
    assert 600_000.0 < start[0] < 700_000.0
    assert 3_900_000.0 < start[1] < 4_100_000.0
    assert 80.0 < projected.length < 100.0
    assert end[0] > start[0]


def test_real_nuplan_mini_route_snapshot_is_causal_and_connected() -> None:
    dataset_root = os.environ.get("NUPLAN_DATA_ROOT")
    if not dataset_root:
        pytest.skip("NUPLAN_DATA_ROOT is required for the real mini contract check")
    root = Path(dataset_root)
    snapshot = load_nuplan_route_snapshot(
        root
        / "data/cache/mini/2021.05.12.22.00.38_veh-35_01008_01518.db",
        root / "maps/us-nv-las-vegas-strip/9.15.1915/map.gpkg",
        "8b9c1329bd1855c9",
    )

    assert snapshot.decision_timestamp_us == 1_620_857_893_850_826
    assert snapshot.source_dt_s == pytest.approx(0.05, abs=2e-4)
    assert snapshot.current_roadblock_id == "66976"
    assert snapshot.route_roadblock_ids[0] == "66976"
    assert len(snapshot.route_roadblock_ids) == 18
    assert snapshot.traffic_light_state_available is True
    assert np.any(snapshot.route_lanes[:, :, 10] == 1.0)
    assert np.all(snapshot.route_has_speed_limit[:18])
    assert np.all(snapshot.route_speed_limit[:18] > 0.0)
    assert np.linalg.norm(snapshot.mission_goal_pose[:2] - [38.0, 0.0]) > 100.0

    gaps = np.linalg.norm(
        snapshot.route_lanes[:-1, -1, :2]
        - snapshot.route_lanes[1:, 0, :2],
        axis=1,
    )
    assert np.max(gaps[:17]) <= 8.0


def test_source_dt_comes_from_real_monotonic_timestamps() -> None:
    assert derive_source_dt_s([1_000_000, 1_050_000, 1_100_010]) == pytest.approx(
        0.050005
    )

    with pytest.raises(NuPlanCausalSourceError, match="strictly increasing"):
        derive_source_dt_s([1_000_000, 1_050_000, 1_050_000])
    with pytest.raises(NuPlanCausalSourceError, match="irregular"):
        derive_source_dt_s([1_000_000, 1_050_000, 1_200_000])


def test_causal_history_ignores_future_rows_and_requires_the_exact_tick() -> None:
    timestamps = np.array([900_000, 950_000, 1_000_000, 1_050_000])
    states = np.arange(8, dtype=np.float64).reshape(4, 2)
    changed_future = states.copy()
    changed_future[-1] = [9_999.0, -9_999.0]

    expected = causal_history(states, timestamps, 1_000_000)
    actual = causal_history(changed_future, timestamps, 1_000_000)

    np.testing.assert_array_equal(actual, expected)
    np.testing.assert_array_equal(actual, states[:3])
    with pytest.raises(NuPlanCausalSourceError, match="exact decision tick"):
        causal_history(states, timestamps, 975_000)


def test_route_window_is_anchored_at_current_roadblock_and_connected() -> None:
    route = tuple(f"rb-{index}" for index in range(40))
    successors = {
        route[index]: (route[index + 1],) for index in range(len(route) - 1)
    }

    assert select_mission_route_window(route, "rb-10", successors) == route[10:35]

    broken = dict(successors)
    broken["rb-14"] = ("other",)
    with pytest.raises(NuPlanCausalSourceError, match="disconnected"):
        select_mission_route_window(route, "rb-10", broken)
    with pytest.raises(NuPlanCausalSourceError, match="current roadblock"):
        select_mission_route_window(route, "absent", successors)


def test_route_lane_keeps_true_boundaries_speed_and_exact_tick_traffic() -> None:
    encoded = encode_route_lane(
        centerline=np.array([[0.0, 0.0], [19.0, 0.0]]),
        left_boundary=np.array([[0.0, 2.0], [19.0, 2.0]]),
        right_boundary=np.array([[0.0, -3.0], [19.0, -3.0]]),
        speed_limit_mps=11.2,
        traffic_light_status="red",
        traffic_timestamp_us=1_000_000,
        decision_timestamp_us=1_000_000,
    )

    assert encoded.tensor.shape == (20, 33)
    assert encoded.tensor.dtype == np.float32
    assert encoded.speed_limit_mps == pytest.approx(11.2)
    np.testing.assert_allclose(
        encoded.tensor[:, 4:6], np.tile([0.0, 2.0], (20, 1)), atol=1e-5
    )
    np.testing.assert_allclose(
        encoded.tensor[:, 6:8], np.tile([0.0, -3.0], (20, 1)), atol=1e-5
    )
    np.testing.assert_array_equal(encoded.tensor[:, 8:13].sum(axis=1), np.ones(20))
    np.testing.assert_array_equal(encoded.tensor[:, 10], np.ones(20))
    np.testing.assert_array_equal(encoded.tensor[:, 12], np.zeros(20))

    with pytest.raises(NuPlanCausalSourceError, match="speed_limit_mps"):
        encode_route_lane(
            centerline=np.array([[0.0, 0.0], [1.0, 0.0]]),
            left_boundary=np.array([[0.0, 1.0], [1.0, 1.0]]),
            right_boundary=np.array([[0.0, -1.0], [1.0, -1.0]]),
            speed_limit_mps=None,
        )
    with pytest.raises(NuPlanCausalSourceError, match="same lidar tick"):
        encode_route_lane(
            centerline=np.array([[0.0, 0.0], [1.0, 0.0]]),
            left_boundary=np.array([[0.0, 1.0], [1.0, 1.0]]),
            right_boundary=np.array([[0.0, -1.0], [1.0, -1.0]]),
            speed_limit_mps=10.0,
            traffic_light_status="green",
            traffic_timestamp_us=999_999,
            decision_timestamp_us=1_000_000,
        )


class _Batch:
    @property
    def agent_fut(self):
        raise AssertionError("GT ego future was accessed")

    @property
    def neigh_fut(self):
        raise AssertionError("GT neighbor future was accessed")


def _batch() -> _Batch:
    batch = _Batch()
    batch.dt = np.array([0.5], dtype=np.float32)
    batch.history_pad_dir = np.array(1, dtype=np.int64)
    history = np.zeros((1, 7, 8), dtype=np.float32)
    history[0, :, 0] = np.linspace(-3.0, 0.0, 7)
    history[0, :, 2] = 1.0
    history[0, :, 7] = 1.0
    batch.agent_hist = history
    batch.agent_hist_len = np.array([7], dtype=np.int64)
    batch.agent_hist_extent = np.tile(
        np.array([4.5, 1.8, 1.5], dtype=np.float32), (1, 7, 1)
    )
    batch.curr_agent_state = np.array(
        [[0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]], dtype=np.float32
    )
    batch.neigh_hist = np.zeros((1, 0, 7, 8), dtype=np.float32)
    batch.neigh_hist_len = np.zeros((1, 0), dtype=np.int64)
    batch.neigh_hist_extents = np.zeros((1, 0, 7, 3), dtype=np.float32)
    batch.neigh_types = np.zeros((1, 0), dtype=np.float32)
    batch.agents_from_world_tf = np.eye(3, dtype=np.float32)[None]
    return batch


def _lane(start_x: float) -> np.ndarray:
    return encode_route_lane(
        centerline=np.array([[start_x, 0.0], [start_x + 19.0, 0.0]]),
        left_boundary=np.array([[start_x, 2.0], [start_x + 19.0, 2.0]]),
        right_boundary=np.array([[start_x, -2.0], [start_x + 19.0, -2.0]]),
        speed_limit_mps=10.0,
    ).tensor


def _context() -> dict[str, object]:
    lanes = np.zeros((140, 20, 33), dtype=np.float32)
    route = np.zeros((25, 20, 33), dtype=np.float32)
    lanes[0] = _lane(0.0)
    route[0] = _lane(0.0)
    route[1] = _lane(19.0)
    lane_speeds = np.zeros((140, 1), dtype=np.float32)
    lane_speeds[0] = 10.0
    lane_has_speeds = np.zeros((140, 1), dtype=bool)
    lane_has_speeds[0] = True
    route_speeds = np.zeros((25, 1), dtype=np.float32)
    route_speeds[:2] = 10.0
    route_has_speeds = np.zeros((25, 1), dtype=bool)
    route_has_speeds[:2] = True
    return {
        "map_frame": "world",
        "decision_id": "scene:lidar-pc",
        "route_source": "nuplan_mission_route_current_roadblock_successors",
        "mission_goal_pose": np.array([80.0, 7.0, 0.4], dtype=np.float32),
        "lanes": lanes,
        "lanes_speed_limit": lane_speeds,
        "lanes_has_speed_limit": lane_has_speeds,
        "route_lanes": route,
        "route_lanes_speed_limit": route_speeds,
        "route_lanes_has_speed_limit": route_has_speeds,
        "line_strings": np.zeros((60, 20, 4), dtype=np.float32),
        "polygons": np.zeros((10, 40, 3), dtype=np.float32),
        "static_objects": np.zeros((5, 10), dtype=np.float32),
        "turn_indicators": np.zeros(31, dtype=np.int32),
        "turn_indicators_available": False,
        "traffic_light_state_available": False,
        "ego_wheelbase_m": 2.7,
    }


def test_materializer_uses_mission_goal_not_route_window_endpoint() -> None:
    result = materialize_causal_dp_input(_batch(), _context())

    np.testing.assert_allclose(result.dp_input["goal_pose"], [80.0, 7.0, 0.4])
    assert not np.allclose(result.dp_input["goal_pose"][:2], [38.0, 0.0])

    missing_goal = _context()
    del missing_goal["mission_goal_pose"]
    with pytest.raises(ValueError, match="mission_goal_pose"):
        materialize_causal_dp_input(_batch(), missing_goal)


def test_mission_goal_is_invariant_to_global_se2_change() -> None:
    context = _context()
    moved = deepcopy(context)
    angle = 0.7
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]],
        dtype=np.float32,
    )
    translation = np.array([23.0, -9.0], dtype=np.float32)
    for key in ("lanes", "route_lanes"):
        values = np.asarray(moved[key]).copy()
        valid = np.sum(np.abs(values[..., :8]), axis=-1) > 0.0
        values[..., :2][valid] = values[..., :2][valid] @ rotation.T + translation
        for start in (2, 4, 6):
            values[..., start : start + 2][valid] = (
                values[..., start : start + 2][valid] @ rotation.T
            )
        moved[key] = values
    goal = np.asarray(moved["mission_goal_pose"]).copy()
    goal[:2] = goal[:2] @ rotation.T + translation
    goal[2] += angle
    moved["mission_goal_pose"] = goal

    batch = _batch()
    transform = np.eye(3, dtype=np.float32)
    transform[:2, :2] = rotation.T
    transform[:2, 2] = -rotation.T @ translation
    batch.agents_from_world_tf = transform[None]
    batch.curr_agent_state[0, :2] = translation
    batch.curr_agent_state[0, 2:4] = [np.cos(angle), np.sin(angle)]
    batch.curr_agent_state[0, 6] = angle

    expected = materialize_causal_dp_input(_batch(), context).dp_input["goal_pose"]
    actual = materialize_causal_dp_input(batch, moved).dp_input["goal_pose"]
    np.testing.assert_allclose(actual, expected, atol=2e-5)
