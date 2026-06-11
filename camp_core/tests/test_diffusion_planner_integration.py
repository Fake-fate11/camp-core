from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass

import numpy as np

from camp_core.atoms.driver_atoms import DriverAtomContext
from camp_core.integrations.diffusion_planner import (
    CAMP_ATOM_NAMES,
    CAMPSelector,
    build_context_from_scene,
    install_lanelet2_projection_fallback,
    project_simplex,
    sanitize_lanelet2_map,
    summarize_selection_records,
)
from scripts.integrations.train_diffusion_planner_static_camp import (
    load_training_records,
    oracle_indices,
    robust_atom_scales,
    train_static_weights,
)


def test_project_simplex_returns_probability_vector() -> None:
    projected = project_simplex(np.array([-1.0, 0.5, 2.0]))
    np.testing.assert_allclose(projected.sum(), 1.0)
    assert np.all(projected >= 0.0)


def test_no_ros_projection_fallback_installs_utm_factory(
    tmp_path, monkeypatch
) -> None:
    map_path = tmp_path / "map.osm"
    map_path.write_text(
        '<osm><node id="1" lat="35.0" lon="139.0"/></osm>',
        encoding="utf-8",
    )
    captured = {}

    class _Origin:
        def __init__(self, lat, lon) -> None:
            captured["origin"] = (lat, lon)

    class _Projector:
        pass

    def _utm_projector(origin, *args):
        captured["projector_args"] = (origin, args)
        return _Projector()

    fake_lanelet2 = types.SimpleNamespace(
        io=types.SimpleNamespace(Origin=_Origin),
        projection=types.SimpleNamespace(UtmProjector=_utm_projector),
    )
    monkeypatch.delitem(sys.modules, "autoware_lanelet2_extension_python", raising=False)
    monkeypatch.delitem(
        sys.modules,
        "autoware_lanelet2_extension_python.projection",
        raising=False,
    )
    monkeypatch.setitem(sys.modules, "lanelet2", fake_lanelet2)

    installed = install_lanelet2_projection_fallback(map_path)
    from autoware_lanelet2_extension_python.projection import MGRSProjector

    assert installed
    assert captured["origin"] == (35.0, 139.0)
    assert isinstance(MGRSProjector(None), _Projector)


def test_sanitize_lanelet2_map_removes_only_unsupported_relations(tmp_path) -> None:
    source = tmp_path / "source.osm"
    destination = tmp_path / "sanitized.osm"
    source.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">
  <relation id="10">
    <member type="relation" ref="20" role="regulatory_element"/>
    <member type="relation" ref="21" role="regulatory_element"/>
    <tag k="type" v="lanelet"/>
  </relation>
  <relation id="20">
    <tag k="type" v="regulatory_element"/>
    <tag k="subtype" v="road_marking"/>
  </relation>
  <relation id="21">
    <tag k="type" v="regulatory_element"/>
    <tag k="subtype" v="traffic_light"/>
  </relation>
</osm>
""",
        encoding="utf-8",
    )

    summary = sanitize_lanelet2_map(source, destination)

    text = destination.read_text(encoding="utf-8")
    assert 'id="20"' not in text
    assert 'ref="20"' not in text
    assert 'id="21"' in text
    assert 'ref="21"' in text
    assert summary["removed_regulatory_relations"] == 1
    assert summary["removed_references"] == 1
    assert summary["removed_by_subtype"] == {"road_marking": 1}


def test_selector_loads_numpy_weights_without_torch(tmp_path) -> None:
    scales_path = tmp_path / "scales.json"
    scales_path.write_text(json.dumps([1.0] * 9), encoding="utf-8")
    weights_path = tmp_path / "weights.npy"
    np.save(weights_path, np.arange(1.0, 10.0))

    selector = CAMPSelector.from_files(
        atom_scales_path=scales_path,
        static_weights_path=weights_path,
        mode="static",
    )

    np.testing.assert_allclose(selector.static_weights.sum(), 1.0)
    assert selector.static_weights.shape == (9,)


def test_train_diffusion_planner_static_camp_from_selection_log(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    records = [
        {
            "atoms": [
                [3.0, 3.0, 3.0, 1.0, 0.0, 0.0, 0.0, 0.0, 5.0],
                [0.1, 0.1, 0.1, 0.5, 0.0, 0.0, 0.0, 0.0, 0.1],
                [1.0, 1.0, 1.0, 0.8, 0.0, 0.0, 0.0, 4.0, 0.0],
            ],
            "feasible_mask": [True, True, False],
        },
        {
            "atoms": [
                [0.2, 0.2, 0.2, 0.2, 0.0, 0.0, 0.0, 5.0, 5.0],
                [0.4, 0.4, 0.4, 0.3, 0.0, 0.0, 0.0, 0.1, 0.1],
                [0.1, 0.1, 0.1, 0.1, 0.0, 0.0, 0.0, 7.0, 7.0],
            ],
            "feasible_mask": [True, True, True],
        },
    ]
    log_path.write_text(json.dumps(records), encoding="utf-8")

    atoms, feasible = load_training_records([log_path])
    scales = robust_atom_scales(atoms, percentile=95.0)
    normalized = np.clip(atoms / scales.reshape(1, 1, -1), 0.0, 10.0)
    labels = oracle_indices(normalized, feasible, np.ones(len(CAMP_ATOM_NAMES)))
    weights, history = train_static_weights(
        normalized,
        labels,
        epochs=50,
        lr=0.2,
        l2_reg=0.0,
    )

    assert atoms.shape == (2, 3, len(CAMP_ATOM_NAMES))
    assert labels.tolist() == [1, 1]
    np.testing.assert_allclose(weights.sum(), 1.0)
    assert np.all(weights > 0.0)
    assert history


def test_summarize_selection_records_reports_candidate_usage() -> None:
    records = [
        {
            "selected_index": 0,
            "used_fallback": False,
            "feasible_mask": [True, False],
            "latency_ms_including_candidate_generation": 10.0,
        },
        {
            "selected_index": 1,
            "used_fallback": True,
            "feasible_mask": [False, False],
            "latency_ms_including_candidate_generation": 20.0,
        },
    ]

    summary = summarize_selection_records(
        records,
        {"reason": "max_steps", "final_step": 1, "goal_reached": False},
    )

    assert summary["selection_steps"] == 2
    assert summary["selected_index_counts"] == {"0": 1, "1": 1}
    assert summary["nonzero_selection_rate"] == 0.5
    assert summary["fallback_rate"] == 0.5
    assert summary["candidate_feasible_rate"] == 0.25
    assert summary["mean_selection_latency_ms"] == 15.0
    assert summary["replay_reason"] == "max_steps"


def test_static_selector_prefers_smoother_feasible_candidate() -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=3.0,
        speed_limit=30.0,
        desired_speed=5.0,
    )
    x = np.linspace(0.5, 4.0, 8)
    smooth = np.column_stack([x, np.zeros_like(x)])
    oscillating = np.column_stack([x, np.array([0.0, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5, 0.0])])
    candidates = np.stack([smooth, oscillating])

    selector = CAMPSelector(
        atom_scales=np.ones(9),
        static_weights=np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        mode="static",
    )
    result = selector.select(candidates, context)

    assert result.selected_index == 0
    assert result.feasible_mask.tolist() == [True, True]
    assert not result.used_fallback


def test_selector_masks_candidate_that_collides_with_predicted_neighbor() -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=10.0,
        speed_limit=50.0,
        desired_speed=5.0,
        safety_radius=1.0,
    )
    x = np.linspace(0.5, 4.0, 8)
    colliding = np.column_stack([x, np.zeros_like(x)])
    clear = np.column_stack([x, np.full_like(x, 3.0)])
    candidates = np.stack([colliding, clear])

    obstacles = np.zeros((2, 1, 8, 2), dtype=np.float64)
    obstacles[:, 0, :, 0] = x
    selector = CAMPSelector(
        atom_scales=np.ones(9),
        static_weights=np.ones(9),
        mode="static",
    )
    result = selector.select(
        candidates,
        context,
        candidate_obstacles=obstacles,
    )

    assert result.feasible_mask.tolist() == [False, True]
    assert result.selected_index == 1


@dataclass
class _FakeAgent:
    route_lanes: np.ndarray
    route_speed_limit: np.ndarray
    route_has_speed_limit: np.ndarray
    current_position: np.ndarray
    current_heading: float
    current_velocity: np.ndarray


@dataclass
class _FakeMap:
    static_objects: np.ndarray


class _FakeScene:
    dt = 0.1

    def __init__(self, agent: _FakeAgent, map_data: _FakeMap) -> None:
        self._agent = agent
        self.map_data = map_data

    def get_agent(self, agent_id: str) -> _FakeAgent:
        assert agent_id == "ego"
        return self._agent


def test_build_context_transforms_route_and_extracts_limits() -> None:
    route = np.zeros((1, 3, 33), dtype=np.float32)
    route[0, :, :2] = np.array([[10.0, 5.0], [11.0, 5.0], [12.0, 5.0]])
    route[0, :, 2:4] = np.array([1.0, 0.0])
    route[0, :, 4:6] = np.array([0.0, 2.0])
    route[0, :, 6:8] = np.array([0.0, -2.0])
    agent = _FakeAgent(
        route_lanes=route,
        route_speed_limit=np.array([[13.0]], dtype=np.float32),
        route_has_speed_limit=np.array([[True]]),
        current_position=np.array([10.0, 5.0]),
        current_heading=0.0,
        current_velocity=np.array([4.0, 0.0]),
    )
    map_data = _FakeMap(
        static_objects=np.array([[14.0, 5.0, 1.0, 0.0, 2.0, 4.0, 0.0, 0.0, 0.0, 0.0]])
    )

    context = build_context_from_scene(_FakeScene(agent, map_data), "ego")

    np.testing.assert_allclose(
        context.lane_centerline,
        np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]]),
    )
    np.testing.assert_allclose(context.static_obstacles, np.array([[4.0, 0.0]]))
    assert context.lane_half_width == 2.0
    assert context.speed_limit == 13.0
    assert context.desired_speed == 4.0
