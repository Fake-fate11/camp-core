from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from camp_core.atoms.driver_atoms import DriverAtomContext, compute_atom_bank_vector
from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
    MATERIALIZER_SCHEMA_VERSION,
    materialize_causal_dp_input,
)


class _Batch:
    @property
    def agent_fut(self):
        raise AssertionError("GT ego future was accessed")

    @property
    def neigh_fut(self):
        raise AssertionError("GT neighbor future was accessed")

    @property
    def holdout_label(self):
        raise AssertionError("holdout label was accessed")


def _batch(*, neighbor_y: float = 4.0) -> _Batch:
    batch = _Batch()
    batch.dt = np.array([0.5], dtype=np.float32)
    batch.history_pad_dir = np.array(1, dtype=np.int64)

    headings = np.array(
        [3.00, 3.10, -3.10, -2.50, -1.70, -0.80, 0.00],
        dtype=np.float32,
    )
    history = np.zeros((1, 7, 8), dtype=np.float32)
    history[0, :, 0] = np.linspace(-3.0, 0.0, 7)
    history[0, :, 2] = 1.0
    history[0, :, 6] = np.sin(headings)
    history[0, :, 7] = np.cos(headings)
    batch.agent_hist = history
    batch.agent_hist_len = np.array([7], dtype=np.int64)
    batch.agent_hist_extent = np.tile(
        np.array([4.5, 1.8, 1.5], dtype=np.float32), (1, 7, 1)
    )
    batch.curr_agent_state = np.array(
        [[0.0, 0.0, 1.0, 0.0, 0.2, 0.0, float(headings[-1])]],
        dtype=np.float32,
    )

    neighbor = np.zeros((1, 1, 7, 8), dtype=np.float32)
    neighbor[0, 0, :, 0] = 4.0
    neighbor[0, 0, :, 1] = neighbor_y
    neighbor[0, 0, :, 6] = 0.0
    neighbor[0, 0, :, 7] = 1.0
    batch.neigh_hist = neighbor
    batch.neigh_hist_len = np.array([[7]], dtype=np.int64)
    batch.neigh_hist_extents = np.tile(
        np.array([4.2, 1.7, 1.5], dtype=np.float32), (1, 1, 7, 1)
    )
    batch.neigh_types = np.array([[1]], dtype=np.float32)
    batch.agents_from_world_tf = np.eye(3, dtype=np.float32)[None]
    return batch


def _lane(start_x: float) -> np.ndarray:
    lane = np.zeros((20, 33), dtype=np.float32)
    lane[:, 0] = np.linspace(start_x, start_x + 19.0, 20)
    lane[:, 2] = 1.0
    lane[:, 5] = 2.0
    lane[:, 7] = -2.0
    lane[:, 12] = 1.0  # DP no-light channel; availability stays explicit metadata.
    lane[:, 13] = 1.0
    lane[:, 23] = 1.0
    return lane


def _decision_context() -> dict[str, object]:
    lanes = np.zeros((140, 20, 33), dtype=np.float32)
    lanes[0] = _lane(100.0)
    lanes[1] = _lane(-100.0)
    route = np.zeros((25, 20, 33), dtype=np.float32)
    route[0] = _lane(0.0)
    route[1] = _lane(19.0)
    lane_limits = np.zeros((140, 1), dtype=np.float32)
    lane_has_limits = np.zeros((140, 1), dtype=bool)
    route_limits = np.zeros((25, 1), dtype=np.float32)
    route_limits[:2, 0] = [8.0, 12.0]
    route_has_limits = np.zeros((25, 1), dtype=bool)
    route_has_limits[:2, 0] = True
    line_strings = np.zeros((60, 20, 4), dtype=np.float32)
    line_strings[0, 0] = [5.0, 2.0, 1.0, 0.0]
    polygons = np.zeros((10, 40, 3), dtype=np.float32)
    polygons[0, 0] = [6.0, -3.0, 1.0]
    static_objects = np.zeros((5, 10), dtype=np.float32)
    static_objects[0, :4] = [7.0, 1.0, 1.0, 0.0]
    return {
        "map_frame": "world",
        "decision_id": "scene-token:sample-token",
        "route_source": "current_map_topology_successors",
        "lanes": lanes,
        "lanes_speed_limit": lane_limits,
        "lanes_has_speed_limit": lane_has_limits,
        "route_lanes": route,
        "route_lanes_speed_limit": route_limits,
        "route_lanes_has_speed_limit": route_has_limits,
        "line_strings": line_strings,
        "polygons": polygons,
        "static_objects": static_objects,
        "turn_indicators": np.zeros(31, dtype=np.int32),
        "turn_indicators_available": False,
        "traffic_light_state_available": False,
        "ego_wheelbase_m": 2.7,
    }


def test_materializer_has_exact_inference_schema_and_never_reads_future() -> None:
    result = materialize_causal_dp_input(_batch(), _decision_context())

    assert set(result.dp_input) == set(CAUSAL_DP_INPUT_SCHEMA)
    assert not any("future" in key for key in result.dp_input)
    assert result.metadata == {
        "schema_version": MATERIALIZER_SCHEMA_VERSION,
        "source_dt_s": 0.5,
        "target_dt_s": 0.1,
        "history_steps": 31,
        "candidate_horizon_steps": 80,
        "candidate_horizon_s": 8.0,
        "coordinate_frame": "ego_base_link",
        "heading_unit": "radian",
        "distance_unit": "meter",
        "speed_unit": "meter_per_second",
        "traffic_light_state_available": False,
        "turn_indicators_available": False,
        "decision_id": "scene-token:sample-token",
        "route_source": "current_map_topology_successors",
    }
    np.testing.assert_allclose(result.dp_input["goal_pose"], [38.0, 0.0, 0.0])


def test_materializer_accepts_all_fixed_dp_turn_indicator_classes() -> None:
    context = _decision_context()
    context["turn_indicators_available"] = True
    context["turn_indicators"] = np.full(31, 4, dtype=np.int32)

    result = materialize_causal_dp_input(_batch(), context)

    np.testing.assert_array_equal(result.dp_input["turn_indicators"], 4)


def test_materializer_rejects_lossy_categorical_casts() -> None:
    context = _decision_context()
    context["turn_indicators_available"] = True
    context["turn_indicators"] = np.full(31, 4.9, dtype=np.float32)
    with pytest.raises(ValueError, match="turn_indicators.*integer"):
        materialize_causal_dp_input(_batch(), context)

    context = _decision_context()
    context["route_lanes_has_speed_limit"] = np.asarray(
        context["route_lanes_has_speed_limit"], dtype=np.float32
    )
    with pytest.raises(ValueError, match="route_lanes_has_speed_limit.*bool"):
        materialize_causal_dp_input(_batch(), context)


def test_materializer_rejects_fractional_history_contract_values() -> None:
    batch = _batch()
    batch.history_pad_dir = np.array(1.5, dtype=np.float32)
    with pytest.raises(ValueError, match="history_pad_dir.*integer"):
        materialize_causal_dp_input(batch, _decision_context())

    batch = _batch()
    batch.agent_hist_len = np.array([7.5], dtype=np.float32)
    with pytest.raises(ValueError, match="agent_hist_len.*integer"):
        materialize_causal_dp_input(batch, _decision_context())

    batch = _batch()
    batch.neigh_hist_len = np.array([[7.5]], dtype=np.float32)
    with pytest.raises(ValueError, match="neigh_hist_len.*integer"):
        materialize_causal_dp_input(batch, _decision_context())


def test_materializer_rejects_nonbinary_traffic_channels() -> None:
    available = _decision_context()
    available["traffic_light_state_available"] = True
    available["route_lanes"][0, 0, 8:13] = [-1.0, 2.0, 0.0, 0.0, 0.0]
    with pytest.raises(ValueError, match="traffic channels must be binary"):
        materialize_causal_dp_input(_batch(), available)

    unavailable = _decision_context()
    unavailable["route_lanes"][0, 0, 12] = 42.0
    with pytest.raises(ValueError, match="traffic channels must be binary"):
        materialize_causal_dp_input(_batch(), unavailable)


def test_materializer_resamples_physical_time_and_wraps_heading() -> None:
    result = materialize_causal_dp_input(_batch(), _decision_context())
    ego = result.dp_input["ego_agent_past"]

    np.testing.assert_allclose(ego[:, 0], np.linspace(-3.0, 0.0, 31), atol=1e-6)
    wrapped_steps = np.angle(np.exp(1j * np.diff(ego[:, 2])))
    assert np.max(np.abs(wrapped_steps)) < 0.2
    assert np.min(np.abs(ego[5:11, 2])) > 3.0

    short = _batch()
    short.agent_hist_len[0] = 6
    with pytest.raises(ValueError, match="ego history covers"):
        materialize_causal_dp_input(short, _decision_context())


def test_materializer_rejects_non_right_padded_trajdata_histories() -> None:
    batch = _batch()
    batch.history_pad_dir = np.array(0, dtype=np.int64)

    with pytest.raises(ValueError, match="history_pad_dir"):
        materialize_causal_dp_input(batch, _decision_context())


def test_short_neighbor_history_uses_zero_mask_not_an_origin_trajectory() -> None:
    batch = _batch()
    batch.neigh_hist_len[0, 0] = 6
    batch.neigh_hist[0, 0, 6] = np.nan
    batch.neigh_hist_extents[0, 0, 6] = np.nan

    neighbor = materialize_causal_dp_input(
        batch, _decision_context()
    ).dp_input["neighbor_agents_past"][0]

    np.testing.assert_array_equal(neighbor[:5], 0.0)
    assert np.all(neighbor[5:, 8] == 1.0)
    np.testing.assert_allclose(neighbor[-1, :2], [4.0, 4.0])


def test_route_is_explicit_connected_and_keeps_boundaries_and_speed_slots() -> None:
    context = _decision_context()
    first = materialize_causal_dp_input(_batch(), context).dp_input
    permuted = deepcopy(context)
    permuted["lanes"] = np.asarray(permuted["lanes"])[::-1].copy()
    second = materialize_causal_dp_input(_batch(), permuted).dp_input

    np.testing.assert_array_equal(first["route_lanes"], second["route_lanes"])
    np.testing.assert_array_equal(
        first["route_lanes_speed_limit"], second["route_lanes_speed_limit"]
    )
    np.testing.assert_allclose(
        np.linalg.norm(first["route_lanes"][:2, :, 4:6], axis=-1), 2.0
    )
    np.testing.assert_allclose(
        np.linalg.norm(first["route_lanes"][:2, :, 6:8], axis=-1), 2.0
    )
    np.testing.assert_allclose(first["route_lanes_speed_limit"][:2, 0], [8.0, 12.0])

    disconnected = _decision_context()
    disconnected["route_lanes"][1] = _lane(30.0)
    with pytest.raises(ValueError, match="route is disconnected"):
        materialize_causal_dp_input(_batch(), disconnected)


def test_lane_boundaries_must_be_lateral_and_route_headings_must_continue() -> None:
    tangent_boundaries = _decision_context()
    tangent_boundaries["route_lanes"][0, :, 4:6] = [1.0, 0.0]
    tangent_boundaries["route_lanes"][0, :, 6:8] = [-1.0, 0.0]
    with pytest.raises(ValueError, match="boundary offsets must be lateral"):
        materialize_causal_dp_input(_batch(), tangent_boundaries)

    reversed_successor = _decision_context()
    reversed_lane = _lane(0.0)[::-1].copy()
    reversed_lane[:, 2:4] = [-1.0, 0.0]
    reversed_lane[:, 4:6] = [0.0, -2.0]
    reversed_lane[:, 6:8] = [0.0, 2.0]
    reversed_successor["route_lanes"][1] = reversed_lane
    with pytest.raises(ValueError, match="route heading discontinuity"):
        materialize_causal_dp_input(_batch(), reversed_successor)


def test_world_to_ego_rotation_must_match_current_heading() -> None:
    batch = _batch()
    batch.curr_agent_state[0, 6] = 0.7

    with pytest.raises(ValueError, match="agents_from_world_tf.*heading"):
        materialize_causal_dp_input(batch, _decision_context())


def _globally_transform(
    batch: _Batch,
    context: dict[str, object],
    rotation: np.ndarray,
    translation: np.ndarray,
) -> tuple[_Batch, dict[str, object]]:
    transformed_batch = _batch()
    transformed_context = deepcopy(context)
    for key in ("lanes", "route_lanes"):
        array = np.asarray(transformed_context[key]).copy()
        valid = np.sum(np.abs(array[..., :8]), axis=-1) > 0.0
        array[..., :2][valid] = array[..., :2][valid] @ rotation.T + translation
        for start in (2, 4, 6):
            array[..., start : start + 2][valid] = (
                array[..., start : start + 2][valid] @ rotation.T
            )
        transformed_context[key] = array

    for key in ("line_strings", "polygons"):
        array = np.asarray(transformed_context[key]).copy()
        valid = np.sum(np.abs(array), axis=-1) > 0.0
        array[..., :2][valid] = array[..., :2][valid] @ rotation.T + translation
        transformed_context[key] = array
    static_objects = np.asarray(transformed_context["static_objects"]).copy()
    static_valid = np.sum(np.abs(static_objects), axis=-1) > 0.0
    static_objects[:, :2][static_valid] = (
        static_objects[:, :2][static_valid] @ rotation.T + translation
    )
    static_objects[:, 2:4][static_valid] = (
        static_objects[:, 2:4][static_valid] @ rotation.T
    )
    transformed_context["static_objects"] = static_objects

    transform = np.eye(3, dtype=np.float32)
    transform[:2, :2] = rotation.T
    transform[:2, 2] = -rotation.T @ translation
    transformed_batch.agents_from_world_tf = transform[None]
    transformed_batch.curr_agent_state[0, :2] = translation
    transformed_batch.curr_agent_state[0, 2:4] = (
        batch.curr_agent_state[0, 2:4] @ rotation.T
    )
    transformed_batch.curr_agent_state[0, 4:6] = (
        batch.curr_agent_state[0, 4:6] @ rotation.T
    )
    transformed_batch.curr_agent_state[0, 6] = batch.curr_agent_state[0, 6] + np.arctan2(
        rotation[1, 0], rotation[0, 0]
    )
    return transformed_batch, transformed_context


def test_materializer_is_invariant_to_global_se2_change() -> None:
    batch = _batch()
    context = _decision_context()
    angle = 0.7
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]],
        dtype=np.float32,
    )
    moved_batch, moved_context = _globally_transform(
        batch, context, rotation, np.array([23.0, -9.0], dtype=np.float32)
    )
    expected = materialize_causal_dp_input(batch, context).dp_input
    actual = materialize_causal_dp_input(moved_batch, moved_context).dp_input

    for key in CAUSAL_DP_INPUT_SCHEMA:
        np.testing.assert_allclose(actual[key], expected[key], atol=2e-5)


def _clearance_atom(dp_input: dict[str, np.ndarray]) -> float:
    current_neighbor = dp_input["neighbor_agents_past"][0, -1, :2]
    obstacle = np.repeat(current_neighbor[None], 80, axis=0)
    candidate = np.column_stack(
        [np.linspace(0.0, 8.0, 80, dtype=np.float32), np.zeros(80, dtype=np.float32)]
    )
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [8.0, 0.0]]),
        dynamic_obstacles={0: obstacle},
        speed_limit=30.0,
    )
    return float(compute_atom_bank_vector(context, candidate)[8])


def test_neighbor_history_perturbation_changes_causal_clearance() -> None:
    far = materialize_causal_dp_input(_batch(neighbor_y=5.0), _decision_context()).dp_input
    near = materialize_causal_dp_input(_batch(neighbor_y=0.5), _decision_context()).dp_input

    assert _clearance_atom(near) > _clearance_atom(far)


def test_fixed_dp_loader_and_normalizer_accept_observable_only_schema(
    tmp_path, monkeypatch
) -> None:
    import json
    import os

    dp_repo = os.environ.get("FIXED_DP_REPO")
    if not dp_repo:
        pytest.skip("FIXED_DP_REPO is required for the upstream contract check")

    from pathlib import Path

    repo = Path(dp_repo)
    monkeypatch.syspath_prepend(str(repo / "diffusion_planner"))
    import torch
    from diffusion_planner.train_epoch import heading_to_cos_sin
    from diffusion_planner.utils.dataset import DiffusionPlannerData
    from diffusion_planner.utils.normalizer import ObservationNormalizer

    dp_input = materialize_causal_dp_input(
        _batch(), _decision_context()
    ).dp_input
    input_npz = tmp_path / "causal_input.npz"
    np.savez_compressed(input_npz, **dp_input)
    manifest = tmp_path / "files.json"
    manifest.write_text(json.dumps({"files": [str(input_npz)]}), encoding="utf-8")

    loaded = DiffusionPlannerData(str(manifest))[0]
    assert set(loaded) == set(CAUSAL_DP_INPUT_SCHEMA)
    assert not any("future" in key for key in loaded)

    tensors = {
        key: torch.as_tensor(value).unsqueeze(0) for key, value in loaded.items()
    }
    tensors["ego_agent_past"] = heading_to_cos_sin(tensors["ego_agent_past"])
    tensors["goal_pose"] = heading_to_cos_sin(tensors["goal_pose"])
    normalized = ObservationNormalizer.from_json(
        str(repo / "diffusion_planner" / "normalization.json")
    )(tensors)
    assert set(normalized) == set(CAUSAL_DP_INPUT_SCHEMA)
    assert all(bool(torch.isfinite(value).all()) for value in normalized.values())
