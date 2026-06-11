from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass

import numpy as np

from camp_core.atoms.driver_atoms import DriverAtomContext
from camp_core.integrations.diffusion_planner import (
    CAMP_ATOM_NAMES,
    DP_SCENE_FEATURE_NAMES,
    CAMPSelector,
    build_context_from_scene,
    extract_dp_scene_features,
    install_lanelet2_projection_fallback,
    project_simplex,
    sanitize_lanelet2_map,
    summarize_replay_artifacts,
    summarize_selection_records,
)
from scripts.integrations.run_diffusion_planner_camp_replay import (
    _candidate_feasibility_from_rewards,
)
from scripts.integrations.train_diffusion_planner_theta import (
    load_scene_training_records,
    normalize_features,
    robust_feature_normalization,
    train_scene_theta,
)
from scripts.integrations.train_diffusion_planner_static_camp import (
    load_candidate_reward_values,
    load_training_records,
    oracle_indices,
    reward_oracle_indices,
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


def test_extract_dp_scene_features_is_fixed_width() -> None:
    inputs = {
        "ego_current_state": np.array([[1.0, 2.0, 3.0]]),
        "route_lanes": np.ones((1, 2, 3, 4), dtype=np.float64),
    }

    features = extract_dp_scene_features(inputs)

    assert features.shape == (len(DP_SCENE_FEATURE_NAMES),)
    assert np.all(np.isfinite(features))
    assert features[0] == 1.0


def test_linear_selector_loads_dp_theta_npz_with_normalization(tmp_path) -> None:
    scales_path = tmp_path / "scales.json"
    scales_path.write_text(json.dumps([1.0] * 9), encoding="utf-8")
    checkpoint_path = tmp_path / "theta.npz"
    theta = np.zeros((9, 3), dtype=np.float64)
    theta[0, 0] = 2.0
    theta[1, 0] = -2.0
    np.savez(
        checkpoint_path,
        Theta=theta,
        feature_center=np.array([10.0, 0.0]),
        feature_scale=np.array([2.0, 1.0]),
        feature_clip=np.array(5.0),
        linear_activation=np.asarray("softmax"),
    )

    selector = CAMPSelector.from_files(
        atom_scales_path=scales_path,
        checkpoint_path=checkpoint_path,
        mode="linear",
    )
    weights = selector.weights_for(np.array([12.0, 0.0]))

    np.testing.assert_allclose(weights.sum(), 1.0)
    assert weights[0] > weights[1]


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


def test_dp_candidate_reward_labels_prefer_best_feasible_candidate(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(
        json.dumps(
            [
                {
                    "atoms": [[0.0] * 9, [1.0] * 9, [2.0] * 9],
                    "feasible_mask": [True, False, True],
                    "dp_candidate_rewards": [
                        {"total": 2.0},
                        {"total": 100.0},
                        {"total": 5.0},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    _, feasible = load_training_records([log_path])
    rewards = load_candidate_reward_values([log_path])
    labels = reward_oracle_indices(rewards, feasible)

    assert rewards.tolist() == [[2.0, 100.0, 5.0]]
    assert labels.tolist() == [2]


def test_train_diffusion_planner_scene_theta_from_selection_log(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    feature_dim = len(DP_SCENE_FEATURE_NAMES)
    base_feature = np.zeros(feature_dim, dtype=np.float64)
    records = []
    for idx in range(6):
        features = base_feature.copy()
        features[0] = 1.0
        features[2] = float(idx)
        records.append(
            {
                "dp_scene_features": features.tolist(),
                "atoms": [
                    [3.0, 3.0, 3.0, 1.0, 0.0, 0.0, 0.0, 0.0, 5.0],
                    [0.1, 0.1, 0.1, 0.5, 0.0, 0.0, 0.0, 0.0, 0.1],
                    [1.0, 1.0, 1.0, 0.8, 0.0, 0.0, 0.0, 4.0, 0.0],
                ],
                "feasible_mask": [True, True, False],
            }
        )
    log_path.write_text(json.dumps(records), encoding="utf-8")

    features, atoms, feasible = load_scene_training_records([log_path])
    center, scale = robust_feature_normalization(features)
    normalized_features = normalize_features(features, center, scale, clip=5.0)
    atom_scales = robust_atom_scales(atoms, percentile=95.0)
    normalized_atoms = np.clip(atoms / atom_scales.reshape(1, 1, -1), 0.0, 10.0)
    labels = oracle_indices(normalized_atoms, feasible, np.ones(len(CAMP_ATOM_NAMES)))
    theta, history, final_metrics = train_scene_theta(
        normalized_features,
        normalized_atoms,
        feasible,
        labels,
        epochs=20,
        lr=0.01,
        l2_reg=0.0,
        seed=1,
        val_fraction=0.2,
    )

    assert features.shape == (6, feature_dim)
    assert theta.shape == (len(CAMP_ATOM_NAMES), feature_dim + 1)
    assert history
    assert final_metrics["train_records"] > 0


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
    assert result.infeasibility_reasons == ((), ())
    assert not result.used_fallback


def test_selector_respects_configurable_lane_corridor_buffer() -> None:
    x = np.linspace(0.5, 4.0, 8)
    candidate = np.column_stack([x, np.full_like(x, 2.6)])
    selector = CAMPSelector(
        atom_scales=np.ones(9),
        static_weights=np.ones(9),
        mode="static",
    )

    strict = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=1.5,
        lane_corridor_buffer=1.0,
        speed_limit=50.0,
    )
    relaxed = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=1.5,
        lane_corridor_buffer=1.25,
        speed_limit=50.0,
    )

    strict_result = selector.select(candidate[np.newaxis], strict)
    relaxed_result = selector.select(candidate[np.newaxis], relaxed)

    assert strict_result.feasible_mask.tolist() == [False]
    assert strict_result.infeasibility_reasons == (("lane_corridor",),)
    assert relaxed_result.feasible_mask.tolist() == [True]
    assert relaxed_result.infeasibility_reasons == ((),)


def test_selector_accepts_external_feasibility_without_context_lane_gate() -> None:
    x = np.linspace(0.5, 4.0, 8)
    candidates = np.stack(
        [
            np.column_stack([x, np.full_like(x, 3.0)]),
            np.column_stack([x, np.full_like(x, 4.0)]),
        ]
    )
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=1.0,
        lane_corridor_buffer=0.0,
        speed_limit=50.0,
    )
    selector = CAMPSelector(
        atom_scales=np.ones(9),
        static_weights=np.ones(9),
        mode="static",
    )

    result = selector.select(
        candidates,
        context,
        external_feasible_mask=np.array([True, False]),
        external_infeasibility_reasons=((), ("dp_lane_crossing",)),
        apply_context_feasibility=False,
    )

    assert result.feasible_mask.tolist() == [True, False]
    assert result.infeasibility_reasons == ((), ("dp_lane_crossing",))
    assert result.selected_index == 0


def test_dp_reward_feasibility_applies_safety_and_progress_gates() -> None:
    rewards = [
        {"progress": 10.0, "red_light": 0.0},
        {"progress": 7.0, "red_light": 0.0},
        {"progress": 12.0, "red_light": 0.0, "collision_step": 4},
    ]

    feasible, reasons = _candidate_feasibility_from_rewards(
        rewards,
        min_progress_ratio=0.8,
    )

    assert feasible.tolist() == [True, False, False]
    assert reasons == ((), ("dp_underprogress",), ("dp_collision",))


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
    assert result.infeasibility_reasons == (("dynamic_point_clearance",), ())
    assert result.selected_index == 1


def test_selector_uses_obb_collision_when_obstacle_shape_is_available() -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, -10.0], [0.0, 10.0]]),
        lane_half_width=20.0,
        speed_limit=50.0,
        desired_speed=5.0,
        safety_radius=0.1,
    )
    y = np.linspace(0.0, 3.5, 8)
    colliding = np.column_stack([np.zeros_like(y), y, np.ones_like(y), np.zeros_like(y)])
    clear = np.column_stack([np.full_like(y, 6.0), y, np.ones_like(y), np.zeros_like(y)])
    candidates = np.stack([colliding, clear])

    obstacles = np.zeros((2, 1, 8, 6), dtype=np.float64)
    obstacles[:, 0, :, 0] = 0.0
    obstacles[:, 0, :, 1] = 1.0
    obstacles[:, 0, :, 2] = np.pi / 2.0
    obstacles[:, 0, :, 3] = 4.5
    obstacles[:, 0, :, 4] = 1.9
    obstacles[:, 0, :, 5] = 2.9

    selector = CAMPSelector(
        atom_scales=np.ones(9),
        static_weights=np.ones(9),
        mode="static",
    )
    result = selector.select(
        candidates,
        context,
        candidate_obstacles=obstacles,
        ego_length=4.5,
        ego_width=1.9,
        ego_wheelbase=2.9,
    )

    assert result.feasible_mask.tolist() == [False, True]
    assert result.infeasibility_reasons == (("dynamic_obb_collision",), ())
    assert result.selected_index == 1


def test_summarize_replay_artifacts_without_selection_log(tmp_path) -> None:
    trajectory = [
        {"step": 0, "x": 0.0, "y": 0.0, "heading": 0.0, "speed": 1.0, "goal_d": 10.0},
        {"step": 1, "x": 1.0, "y": 0.0, "heading": 0.0, "speed": 2.0, "goal_d": 9.0},
        {"step": 2, "x": 3.0, "y": 0.0, "heading": 0.0, "speed": 2.5, "goal_d": 7.0},
    ]
    (tmp_path / "trajectory_log.json").write_text(json.dumps(trajectory), encoding="utf-8")
    (tmp_path / "clearance_log.json").write_text(
        json.dumps(
            {
                "records": [
                    {"moving_dist": 3.0, "stopped_dist": None, "rb_dist": 4.0},
                    {"moving_dist": 1.0, "stopped_dist": None, "rb_dist": 2.0},
                    {"moving_dist": 0.0, "stopped_dist": None, "rb_dist": 1.5},
                ]
            }
        ),
        encoding="utf-8",
    )

    summary = summarize_replay_artifacts(
        tmp_path,
        replay_result={"reason": "max_steps", "final_step": 2, "goal_reached": False},
        route_centerline=np.array(
            [[0.0, 0.0], [5.0, 0.0], [10.0, 0.0], [0.1, 0.0]]
        ),
        near_miss_threshold_m=2.0,
    )

    assert summary["selection_steps"] is None
    assert summary["closed_loop_steps"] == 3
    assert summary["distance_traveled_m"] == 3.0
    assert summary["goal_distance_reduction_rate"] == 0.3
    assert 0.1 < summary["route_completion_rate"] < 0.2
    assert summary["obb_collision_steps"] == 1
    assert summary["near_miss_steps"] == 2


def test_summarize_replay_artifacts_reports_realized_red_light(tmp_path) -> None:
    trajectory = [
        {"step": 0, "x": 0.0, "y": 0.0, "heading": 0.0, "speed": 5.0, "goal_d": 10.0},
        {"step": 1, "x": 1.0, "y": 0.0, "heading": 0.0, "speed": 5.0, "goal_d": 9.0},
    ]
    (tmp_path / "trajectory_log.json").write_text(json.dumps(trajectory), encoding="utf-8")
    evaluation_records = [
        {
            "step": 0,
            "x": 0.0,
            "y": 0.0,
            "heading": 0.0,
            "red_route_points": [[1.0, 0.0, 1.0, 0.0]],
        },
        {
            "step": 1,
            "x": 1.0,
            "y": 0.0,
            "heading": 0.0,
            "red_route_points": [[1.0, 0.0, 1.0, 0.0]],
        },
    ]
    metric_records = [
        {
            "lane_crossing": False,
            "pred_lane_crossing": True,
            "collision": False,
            "pred_collision": False,
            "pred_red_light": -10.5,
        }
    ]

    summary = summarize_replay_artifacts(
        tmp_path,
        replay_result={"reason": "max_steps", "final_step": 1, "goal_reached": False},
        metric_records=metric_records,
        evaluation_records=evaluation_records,
    )

    assert summary["realized_red_light_violation_steps"] == 1
    assert summary["red_light_violation_rate"] == 1.0
    assert summary["planned_red_light_violation_rate"] == 1.0
    assert summary["lane_violation_rate"] == 0.0
    assert summary["planned_lane_violation_rate"] == 1.0


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

    context = build_context_from_scene(
        _FakeScene(agent, map_data),
        "ego",
        lane_corridor_buffer=1.25,
    )

    np.testing.assert_allclose(
        context.lane_centerline,
        np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]]),
    )
    np.testing.assert_allclose(context.static_obstacles, np.array([[4.0, 0.0]]))
    assert context.lane_half_width == 2.0
    assert context.lane_corridor_buffer == 1.25
    assert context.speed_limit == 13.0
    assert context.desired_speed == 4.0
