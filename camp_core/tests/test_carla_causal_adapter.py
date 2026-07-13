from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.integrations.carla_causal_adapter import (
    build_carla_history_batch,
    build_route_lifting_context,
    materialize_carla_snapshot,
)
from camp_core.integrations.carla_exact_speed_source import LiftingTolerances
from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
)


def _lane(start_x: float) -> np.ndarray:
    lane = np.zeros((20, 33), dtype=np.float32)
    lane[:, 0] = np.linspace(start_x, start_x + 19.0, 20)
    lane[:, 2] = 1.0
    lane[:, 5] = 2.0
    lane[:, 7] = -2.0
    lane[:, 12] = 1.0
    lane[:, 13] = 1.0
    lane[:, 23] = 1.0
    return lane


def _batch(neighbor_count: int = 33) -> SimpleNamespace:
    history = np.zeros((1, 31, 8), dtype=np.float32)
    history[0, :, 0] = np.linspace(-3.0, 0.0, 31)
    history[0, :, 2] = 1.0
    history[0, :, 7] = 1.0
    neighbors = np.zeros((1, neighbor_count, 31, 8), dtype=np.float32)
    for index in range(neighbor_count):
        neighbors[0, index, :, 0] = float(index + 1)
        neighbors[0, index, :, 7] = 1.0
    return SimpleNamespace(
        dt=np.array([0.1], dtype=np.float32),
        history_pad_dir=np.array(1, dtype=np.int64),
        agent_hist=history,
        agent_hist_len=np.array([31], dtype=np.int64),
        agent_hist_extent=np.tile(
            np.array([4.5, 1.8, 1.5], dtype=np.float32), (1, 31, 1)
        ),
        curr_agent_state=np.array(
            [[0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]], dtype=np.float32
        ),
        neigh_hist=neighbors,
        neigh_hist_len=np.full((1, neighbor_count), 31, dtype=np.int64),
        neigh_hist_extents=np.tile(
            np.array([4.2, 1.7, 1.5], dtype=np.float32),
            (1, neighbor_count, 31, 1),
        ),
        neigh_types=np.ones((1, neighbor_count), dtype=np.float32),
        agents_from_world_tf=np.eye(3, dtype=np.float32)[None],
    )


def _context() -> dict[str, object]:
    lanes = np.zeros((140, 20, 33), dtype=np.float32)
    route = np.zeros((25, 20, 33), dtype=np.float32)
    route[0] = _lane(0.0)
    route[1] = _lane(19.0)
    lanes[:2] = route[:2]
    route_has_speed = np.zeros((25, 1), dtype=bool)
    route_has_speed[:2] = True
    route_speed = np.zeros((25, 1), dtype=np.float32)
    route_speed[:2] = 11.176
    lane_has_speed = np.zeros((140, 1), dtype=bool)
    lane_has_speed[:2] = True
    lane_speed = np.zeros((140, 1), dtype=np.float32)
    lane_speed[:2] = 11.176
    return {
        "map_frame": "world",
        "decision_id": "Town01:3411:30",
        "route_source": "current_map_topology_successors",
        "lanes": lanes,
        "lanes_has_speed_limit": lane_has_speed,
        "lanes_speed_limit": lane_speed,
        "route_lanes": route,
        "route_lanes_has_speed_limit": route_has_speed,
        "route_lanes_speed_limit": route_speed,
        "line_strings": np.zeros((60, 20, 4), dtype=np.float32),
        "polygons": np.zeros((10, 40, 3), dtype=np.float32),
        "static_objects": np.zeros((5, 10), dtype=np.float32),
        "turn_indicators": np.zeros(31, dtype=np.int32),
        "turn_indicators_available": False,
        "traffic_light_state_available": True,
        "ego_wheelbase_m": 2.875,
    }


def _timestamps() -> np.ndarray:
    return np.arange(31, dtype=np.int64) * 100_000


def test_snapshot_delegates_to_fixed_schema_and_preserves_observable_caps() -> None:
    result = materialize_carla_snapshot(
        timestamps_us=_timestamps(),
        decision_timestamp_us=3_000_000,
        traffic_timestamp_us=3_000_000,
        batch=_batch(),
        decision_context=_context(),
        source_metadata={"map": "Town01", "seed": 3411},
    )

    assert set(result.dp_input) == set(CAUSAL_DP_INPUT_SCHEMA)
    assert result.dp_input["neighbor_agents_past"].shape == (32, 31, 11)
    assert result.dp_input["static_objects"].shape == (5, 10)
    assert result.metadata["source"] == "official_carla_snapshot"
    assert result.metadata["candidate_horizon_s"] == 8.0


@pytest.mark.parametrize(
    ("timestamps", "decision", "match"),
    [
        (np.arange(30) * 100_000, 2_900_000, "31 timestamps"),
        (np.r_[np.arange(30) * 100_000, 3_000_001], 3_000_001, "uniform"),
        (_timestamps(), 3_100_000, "decision tick"),
    ],
)
def test_snapshot_rejects_noncausal_history(
    timestamps: np.ndarray, decision: int, match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        materialize_carla_snapshot(
            timestamps_us=timestamps,
            decision_timestamp_us=decision,
            traffic_timestamp_us=decision,
            batch=_batch(),
            decision_context=_context(),
            source_metadata={},
        )


def test_snapshot_rejects_stale_traffic_and_outcome_fields() -> None:
    with pytest.raises(ValueError, match="traffic timestamp"):
        materialize_carla_snapshot(
            timestamps_us=_timestamps(),
            decision_timestamp_us=3_000_000,
            traffic_timestamp_us=2_900_000,
            batch=_batch(),
            decision_context=_context(),
            source_metadata={},
        )

    with pytest.raises(ValueError, match="forbidden source field"):
        materialize_carla_snapshot(
            timestamps_us=_timestamps(),
            decision_timestamp_us=3_000_000,
            traffic_timestamp_us=3_000_000,
            batch=_batch(),
            decision_context=_context(),
            source_metadata={"closed_loop_outcome": 0.0},
        )


def _frames() -> list[dict[str, object]]:
    frames = []
    for index in range(31):
        actors = [
            {
                "track_id": "vehicle-a",
                "type_id": 1,
                "state": [float(index), 5.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                "extent": [4.2, 1.7, 1.5],
            }
        ]
        if index >= 29:
            actors.append(
                {
                    "track_id": "walker-b",
                    "type_id": 2,
                    "state": [float(index), 2.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    "extent": [0.5, 0.5, 1.8],
                }
            )
        frames.append(
            {
                "timestamp_us": index * 100_000,
                "ego_state": [float(index), 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                "ego_extent": [4.5, 1.8, 1.5],
                "actors": actors,
            }
        )
    return frames


def test_history_collector_builds_contiguous_actor_histories_in_ego_frame() -> None:
    timestamps, batch = build_carla_history_batch(_frames())

    np.testing.assert_array_equal(timestamps, _timestamps())
    assert batch.agent_hist.shape == (1, 31, 8)
    assert batch.neigh_hist.shape == (1, 2, 31, 8)
    np.testing.assert_array_equal(batch.neigh_hist_len, [[2, 31]])
    np.testing.assert_allclose(batch.curr_agent_state[0, :2], [30.0, 0.0])
    np.testing.assert_allclose(batch.agents_from_world_tf[0] @ [30, 0, 1], [0, 0, 1])
    np.testing.assert_allclose(batch.neigh_hist[0, 0, :2, :2], [[-1, 2], [0, 2]])
    np.testing.assert_allclose(batch.neigh_hist[0, 1, -1, :2], [0, 5])


def test_history_collector_rejects_outcome_fields() -> None:
    frames = _frames()
    frames[-1]["metric_outcome"] = 0.0

    with pytest.raises(ValueError, match="forbidden source field"):
        build_carla_history_batch(frames)


def _route_samples() -> list[dict[str, object]]:
    return [
        {
            "road_id": road,
            "section_id": 0,
            "lane_id": -1,
            "s": s,
            "x": x,
            "y": 0.0,
            "z": 1.0,
            "lane_width": 3.5,
            "is_junction": road == "2",
        }
        for road, s, x in (
            ("1", 0.0, 0.0),
            ("1", 5.0, 5.0),
            ("2", 0.0, 10.0),
            ("2", 5.0, 15.0),
        )
    ]


def test_route_lifting_context_is_deterministic_and_route_only() -> None:
    kwargs = {
        "route_source": "current_map_topology_successors",
        "route_samples": _route_samples(),
        "directed_edges": [(("1", 0, -1), ("2", 0, -1))],
        "route_sample_step_m": 5.0,
        "tolerances": LiftingTolerances(1.5, 1e-9, 1e-9, 1e-9),
        "map_sha256": "a" * 64,
    }

    first = build_route_lifting_context(**kwargs)
    second = build_route_lifting_context(**kwargs)

    assert first == second
    assert tuple(sample.identity for sample in first.samples) == (
        ("1", 0, -1),
        ("1", 0, -1),
        ("2", 0, -1),
        ("2", 0, -1),
    )
    assert first.edges == ((("1", 0, -1), ("2", 0, -1)),)
    assert first.identity_directions == ((('1', 0, -1), 1), (('2', 0, -1), 1))
    assert len(first.source_sha256) == len(first.route_graph_sha256) == 64


def test_route_lifting_context_rejects_nonroute_and_outcome_sources() -> None:
    common = {
        "route_samples": _route_samples(),
        "directed_edges": [],
        "route_sample_step_m": 5.0,
        "tolerances": LiftingTolerances(1.5, 1e-9, 1e-9, 1e-9),
        "map_sha256": "a" * 64,
    }
    with pytest.raises(ValueError, match="current_map_topology_successors"):
        build_route_lifting_context(route_source="global_map", **common)

    samples = _route_samples()
    samples[0]["future_outcome"] = 1.0
    with pytest.raises(ValueError, match="forbidden source field"):
        build_route_lifting_context(
            route_source="current_map_topology_successors",
            **{**common, "route_samples": samples},
        )

    with pytest.raises(ValueError, match="route edge identity"):
        build_route_lifting_context(
            route_source="current_map_topology_successors",
            **{
                **common,
                "directed_edges": [(("1", 0.5, -1), ("2", 0, -1))],
            },
        )
