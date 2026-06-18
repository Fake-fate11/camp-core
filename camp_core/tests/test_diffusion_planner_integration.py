from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

import camp_core.integrations.diffusion_planner as diffusion_planner_module
from camp_core.atoms.driver_atoms import DriverAtomContext
from camp_core.atoms.driver_atoms import (
    _project_onto_centerline,
    _project_point_onto_polyline,
    compute_atom_bank_vector,
)
from camp_core.integrations.diffusion_planner import (
    CAMP_ATOM_NAMES,
    DP_SCENE_FEATURE_NAMES,
    DP_CAMP_ATOM_NAMES,
    DP_CAMP_ATOM_NAMES_V8,
    DP_CAMP_ATOM_NAMES_V9,
    DP_CAMP_ATOM_NAMES_V10,
    CAMPSelectionResult,
    CAMPSelector,
    atom_schema_for_dimension,
    blend_candidate_prefix_with_reference,
    build_context_from_scene,
    compute_candidate_closed_loop_outcomes,
    compute_candidate_obstacle_clearance_diagnostics,
    compute_dp_prior_comfort_excess_costs,
    compute_dp_prior_deviation_costs,
    compute_lateral_comfort_shadow_costs,
    compute_perfect_tracker_command_diagnostics,
    compute_perfect_tracker_open_loop_rollout_diagnostics,
    compute_red_stopping_margin_costs,
    extract_dp_scene_features,
    generate_candidate_trajectories,
    install_lanelet2_projection_fallback,
    project_simplex,
    sanitize_lanelet2_map,
    select_perfect_tracker_command_dominating_candidate,
    summarize_replay_artifacts,
    summarize_selection_records,
)
from camp_core.outer_master.robust_margin_master import (
    RobustMarginConfig,
    candidate_ranking_violations,
    empirical_cvar,
    outcome_oracle_and_margins,
    project_simplex_rows,
    solve_robust_margin_cutting_plane,
    theta_weights,
)
from scripts.integrations.run_diffusion_planner_camp_replay import (
    _apply_candidate0_route_progress_guard,
    _apply_candidate0_step_reach_guard,
    _apply_lexicographic_admissible_filter,
    _apply_traffic_light_hybrid_postselection,
    _apply_underprogress_relaxation_override,
    _candidate_route_progress,
    _candidate_step_reach,
    _candidate_feasibility_from_rewards,
    _perfect_tracker_candidate_preprocessing,
    _prepare_perfect_tracker_reference_candidates,
    _prepare_reward_scoring_candidates,
)
from scripts.integrations.create_diffusion_planner_smoke_route import (
    _route_geometry,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (
    _all_pairwise_deltas,
    _mean_ci,
    _pairing_audit,
    _run_key,
    require_strict_pairing,
)
from scripts.integrations.train_diffusion_planner_theta import (
    load_scene_training_records,
    normalize_features,
    robust_feature_normalization,
    train_scene_theta,
)
from scripts.integrations.train_diffusion_planner_static_camp import (
    load_candidate_closed_loop_outcomes,
    load_candidate_reward_values,
    load_training_records,
    oracle_indices,
    reward_oracle_indices,
    robust_atom_scales,
    train_static_weights,
    validate_atom_schema,
)
from scripts.integrations.train_diffusion_planner_robust_camp import (
    grouped_train_val_indices,
    parse_atom_weight_lower_bounds,
    main as train_robust_camp_main,
    save_theta_checkpoint,
)


def test_project_simplex_returns_probability_vector() -> None:
    projected = project_simplex(np.array([-1.0, 0.5, 2.0]))
    np.testing.assert_allclose(projected.sum(), 1.0)
    assert np.all(projected >= 0.0)


def test_vectorized_centerline_projection_matches_pointwise_projection() -> None:
    centerline = np.array(
        [[0.0, 0.0], [4.0, 0.0], [7.0, 3.0], [10.0, 3.0]]
    )
    trajectory = np.array(
        [[0.5, 0.2], [3.0, -0.4], [5.0, 1.2], [8.0, 3.5]]
    )

    _, vectorized_offsets = _project_onto_centerline(trajectory, centerline)
    pointwise_offsets = np.asarray(
        [
            _project_point_onto_polyline(point, centerline)
            for point in trajectory
        ]
    )

    np.testing.assert_allclose(vectorized_offsets, pointwise_offsets, atol=1e-12)


def test_vectorized_atom_clearance_matches_hinge_definition() -> None:
    trajectory = np.array(
        [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0]]
    )
    dynamic = {0: np.array([[3.0, 0.0], [2.5, 0.0], [2.5, 0.0], [3.5, 0.0]])}
    static = np.array([[10.0, 10.0]])
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [10.0, 0.0]]),
        static_obstacles=static,
        dynamic_obstacles=dynamic,
        safety_radius=1.0,
        clearance_soft_margin=1.0,
    )

    atoms = compute_atom_bank_vector(context, trajectory)
    distances = np.linalg.norm(trajectory - dynamic[0], axis=1)
    expected = context.dt * np.sum(np.maximum(0.0, 2.0 - distances) ** 2)

    assert atoms[-1] == pytest.approx(expected)


def test_route_geometry_reports_endpoint_separation_and_repeats() -> None:
    class _Builder:
        centerlines = {
            1: np.array([[0.0, 0.0], [3.0, 0.0]]),
            2: np.array([[3.0, 0.0], [3.0, 4.0]]),
        }

        def raw_centerline(self, lanelet_id: int) -> np.ndarray:
            return self.centerlines[lanelet_id]

    length, endpoint_distance, repeats = _route_geometry(_Builder(), [1, 2, 1])

    assert length == 10.0
    assert endpoint_distance == 3.0
    assert repeats == 1


def test_comparison_reports_strict_pairing_and_pairwise_bootstrap_ci() -> None:
    rows = []
    offsets = {"top1": 0.0, "uniform": 1.0, "static": 2.0, "theta": 3.0}
    for variant, offset in offsets.items():
        for run_idx in range(3):
            rows.append(
                {
                    "variant": variant,
                    "run_key": f"run-{run_idx}",
                    "route_completion_rate": float(run_idx) + offset,
                }
            )

    audit = _pairing_audit(rows)
    pairwise = _all_pairwise_deltas(rows)
    theta_vs_static = next(
        row
        for row in pairwise
        if row["baseline"] == "static" and row["variant"] == "theta"
    )
    first_ci = _mean_ci([1.0, 2.0, 3.0], seed_key="repeatable")
    second_ci = _mean_ci([1.0, 2.0, 3.0], seed_key="repeatable")

    assert audit["strictly_paired"]
    assert audit["common_run_count"] == 3
    assert len(pairwise) == 6
    assert theta_vs_static["route_completion_rate"]["mean"] == 1.0
    assert theta_vs_static["route_completion_rate"]["n"] == 3
    assert first_ci == second_ci
    assert first_ci["ci_method"] == "bootstrap_percentile"


def test_formal_comparison_rejects_incomplete_pairing() -> None:
    audit = _pairing_audit(
        [
            {"variant": "top1", "run_key": "run-1"},
            {"variant": "top1", "run_key": "run-2"},
            {"variant": "v8", "run_key": "run-1"},
        ]
    )

    assert not audit["strictly_paired"]
    with pytest.raises(ValueError, match="identical run keys"):
        require_strict_pairing(audit)


def test_comparison_run_key_prefers_canonical_benchmark_fields() -> None:
    summary = {
        "benchmark_key": (
            "route=/tmp/route.pkl|seed=1|steps=200|max_npcs=4|"
            "spawn_probability=0.3|traffic_lights=True|advance_mode=perfect"
        ),
        "benchmark": {
            "route": "/tmp/route.pkl",
            "seed": 1,
            "steps": 200,
            "max_npcs": 4,
            "spawn_probability": 0.3,
            "traffic_lights": True,
            "advance_mode": "perfect",
        },
    }

    assert _run_key(summary, Path("/unused")) == (
        "/tmp/route.pkl|1|200|4|0.3|True|perfect"
    )


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


def test_selector_rejects_structured_scale_schema_reordering(tmp_path) -> None:
    version, names = atom_schema_for_dimension(len(CAMP_ATOM_NAMES))
    scales_path = tmp_path / "scales.json"
    scales_path.write_text(
        json.dumps(
            {
                "atom_schema_version": version,
                "atom_names": list(reversed(names)),
                "scales": [1.0] * len(names),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Atom scales schema"):
        CAMPSelector.from_files(
            atom_scales_path=scales_path,
            mode="static",
        )


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
                        {"total": 2.0, "progress": 0.5},
                        {"total": 100.0, "progress": 50.0},
                        {"total": 5.0, "progress": 1.0},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    _, feasible = load_training_records([log_path])
    rewards = load_candidate_reward_values([log_path])
    quality = load_candidate_reward_values(
        [log_path],
        reward_key="quality_without_progress",
        progress_weight=2.0,
    )
    labels = reward_oracle_indices(rewards, feasible)

    assert rewards.tolist() == [[2.0, 100.0, 5.0]]
    assert quality.tolist() == [[1.0, 0.0, 3.0]]
    assert labels.tolist() == [2]


def test_candidate_closed_loop_outcomes_capture_branch_metrics() -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=1.5,
        lane_corridor_buffer=0.5,
        speed_limit=30.0,
        safety_radius=1.0,
    )
    x = np.linspace(0.0, 5.0, 6)
    safe = np.column_stack([x, np.zeros_like(x), np.ones_like(x), np.zeros_like(x)])
    colliding = safe.copy()
    lane_bad = np.column_stack([x, np.full_like(x, 3.0), np.ones_like(x), np.zeros_like(x)])
    candidates = np.stack([safe, colliding, lane_bad])
    obstacles = np.zeros((3, 1, 6, 6), dtype=np.float64)
    obstacles[1, 0, :, 0] = x
    obstacles[1, 0, :, 1] = 0.0
    obstacles[1, 0, :, 2] = 0.0
    obstacles[1, 0, :, 3] = 4.5
    obstacles[1, 0, :, 4] = 1.9
    obstacles[1, 0, :, 5] = 2.9
    red_points = np.array([[4.0, 0.0, 1.0, 0.0]])

    outcomes = compute_candidate_closed_loop_outcomes(
        candidates,
        context,
        candidate_obstacles=obstacles,
        red_route_points=red_points,
        horizon_steps=6,
        near_miss_threshold_m=2.0,
        weights={
            "progress": 1.0,
            "collision": 100.0,
            "near_miss": 10.0,
            "lane_violation": 40.0,
            "red_light": 30.0,
            "mean_jerk": 0.0,
            "mean_lateral_acceleration": 0.0,
        },
    )

    assert outcomes[0]["progress_m"] > 4.0
    assert outcomes[0]["red_light_violation"]
    assert outcomes[1]["collision"]
    assert outcomes[1]["near_miss"]
    assert outcomes[2]["lane_violation"]
    assert outcomes[1]["value"] < outcomes[0]["value"]
    assert outcomes[2]["value"] < outcomes[0]["value"]


def test_candidate_obstacle_clearance_diagnostics_are_current_tick_hinges() -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=10.0,
        speed_limit=50.0,
        desired_speed=5.0,
        safety_radius=1.0,
        clearance_soft_margin=1.0,
    )
    x = np.linspace(0.0, 4.0, 8)
    colliding = np.column_stack([x, np.zeros_like(x)])
    clear = np.column_stack([x, np.full_like(x, 4.0)])
    candidates = np.stack([colliding, clear])
    obstacles = np.zeros((2, 1, 8, 2), dtype=np.float64)
    obstacles[:, 0, :, 0] = x

    diagnostics = compute_candidate_obstacle_clearance_diagnostics(
        candidates,
        context,
        candidate_obstacles=obstacles,
        horizon_steps=8,
        near_miss_threshold_m=2.0,
    )

    assert (
        diagnostics["schema_version"]
        == "candidate_current_tick_obstacle_clearance_v2"
    )
    assert diagnostics["selection_effect"] is False
    assert diagnostics["future_outcome_leakage"] is False
    assert diagnostics["horizon_steps"] == 8
    np.testing.assert_allclose(diagnostics["min_obstacle_clearance_m"], [0.0, 4.0])
    np.testing.assert_allclose(
        diagnostics["min_obstacle_clearance_lower_bound_m"], [0.0, 4.0]
    )
    assert diagnostics["exact_evaluated_pairs"] == [0, 0]
    assert diagnostics["exact_min_obstacle_clearance_m"] == [None, None]
    np.testing.assert_allclose(diagnostics["soft_clearance_violation_m"], [2.0, 0.0])
    np.testing.assert_allclose(diagnostics["soft_clearance_violation_cost"], [4.0, 0.0])
    np.testing.assert_allclose(diagnostics["near_miss_violation_m"], [2.0, 0.0])
    assert diagnostics["obstacle_slots"] == [1, 1]
    assert diagnostics["geometry_mode"] == ["point", "point"]


def test_candidate_obstacle_clearance_diagnostics_reports_obb_mode() -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, -10.0], [0.0, 10.0]]),
        lane_half_width=20.0,
        speed_limit=50.0,
        desired_speed=5.0,
        safety_radius=0.1,
        clearance_soft_margin=1.9,
    )
    y = np.linspace(0.0, 3.5, 8)
    colliding = np.column_stack(
        [np.zeros_like(y), y, np.ones_like(y), np.zeros_like(y)]
    )
    clear = np.column_stack(
        [np.full_like(y, 6.0), y, np.ones_like(y), np.zeros_like(y)]
    )
    candidates = np.stack([colliding, clear])
    obstacles = np.zeros((2, 1, 8, 6), dtype=np.float64)
    obstacles[:, 0, :, 0] = 0.0
    obstacles[:, 0, :, 1] = 1.0
    obstacles[:, 0, :, 2] = np.pi / 2.0
    obstacles[:, 0, :, 3] = 4.5
    obstacles[:, 0, :, 4] = 1.9
    obstacles[:, 0, :, 5] = 2.9

    diagnostics = compute_candidate_obstacle_clearance_diagnostics(
        candidates,
        context,
        candidate_obstacles=obstacles,
        horizon_steps=8,
    )

    assert diagnostics["geometry_mode"] == ["obb", "obb"]
    assert diagnostics["exact_evaluated_pairs"][0] > 0
    assert diagnostics["exact_evaluated_pairs"][1] == 0
    assert diagnostics["min_obstacle_clearance_m"][0] == pytest.approx(0.0)
    assert diagnostics["min_obstacle_clearance_m"][1] > 0.0
    assert diagnostics["min_obstacle_clearance_lower_bound_m"][0] == pytest.approx(0.0)
    assert diagnostics["exact_min_obstacle_clearance_m"][0] == pytest.approx(0.0)
    assert diagnostics["exact_min_obstacle_clearance_m"][1] is None
    assert diagnostics["soft_clearance_violation_cost"][0] > 0.0


def test_candidate_obstacle_clearance_diagnostics_can_skip_exact_obb() -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, -10.0], [0.0, 10.0]]),
        lane_half_width=20.0,
        speed_limit=50.0,
        desired_speed=5.0,
        safety_radius=0.1,
        clearance_soft_margin=1.9,
    )
    y = np.linspace(0.0, 3.5, 8)
    candidate = np.column_stack(
        [np.zeros_like(y), y, np.ones_like(y), np.zeros_like(y)]
    )
    candidates = np.stack([candidate])
    obstacles = np.zeros((1, 1, 8, 6), dtype=np.float64)
    obstacles[:, 0, :, 0] = 0.0
    obstacles[:, 0, :, 1] = 1.0
    obstacles[:, 0, :, 2] = np.pi / 2.0
    obstacles[:, 0, :, 3] = 4.5
    obstacles[:, 0, :, 4] = 1.9
    obstacles[:, 0, :, 5] = 2.9

    exact = compute_candidate_obstacle_clearance_diagnostics(
        candidates,
        context,
        candidate_obstacles=obstacles,
        horizon_steps=8,
    )
    lower_bound_only = compute_candidate_obstacle_clearance_diagnostics(
        candidates,
        context,
        candidate_obstacles=obstacles,
        horizon_steps=8,
        evaluate_exact_obb=False,
    )

    assert exact["exact_obb_enabled"] is True
    assert lower_bound_only["exact_obb_enabled"] is False
    assert exact["exact_evaluated_pairs"][0] > 0
    assert lower_bound_only["exact_evaluated_pairs"] == [0]
    assert lower_bound_only["exact_min_obstacle_clearance_m"] == [None]
    assert lower_bound_only["geometry_mode"] == ["obb"]
    np.testing.assert_allclose(
        lower_bound_only["min_obstacle_clearance_lower_bound_m"],
        exact["min_obstacle_clearance_lower_bound_m"],
    )
    np.testing.assert_allclose(
        lower_bound_only["soft_clearance_violation_cost"],
        exact["soft_clearance_violation_cost"],
    )
    np.testing.assert_allclose(
        lower_bound_only["near_miss_violation_cost"],
        exact["near_miss_violation_cost"],
    )


def test_red_stopping_margin_cost_is_continuous_before_hard_violation() -> None:
    candidates = np.array(
        [
            [[0.0, 0.0], [8.0, 0.0], [14.0, 0.0]],
            [[0.0, 0.0], [4.0, 0.0], [8.0, 0.0]],
            [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
        ]
    )
    red_points = np.array([[20.0, 0.0, 1.0, 0.0]])

    costs = compute_red_stopping_margin_costs(
        candidates,
        red_points,
        dt=1.0,
    )

    assert np.all(np.isfinite(costs))
    assert np.all(costs >= 0.0)
    assert costs[0] > costs[1]
    assert costs[0] > 0.0
    assert costs[2] == 0.0
    assert (
        np.min(
            np.linalg.norm(
                candidates[0, :, :2] - red_points[0, :2],
                axis=1,
            )
        )
        > 3.0
    )


def test_red_stopping_margin_ignores_unaligned_or_behind_red_points() -> None:
    candidates = np.array([[[0.0, 0.0], [8.0, 0.0], [14.0, 0.0]]])
    unaligned = np.array([[20.0, 0.0, 0.0, 1.0]])
    behind = np.array([[-5.0, 0.0, 1.0, 0.0]])

    np.testing.assert_array_equal(
        compute_red_stopping_margin_costs(candidates, unaligned, dt=1.0),
        np.zeros(1),
    )
    np.testing.assert_array_equal(
        compute_red_stopping_margin_costs(candidates, behind, dt=1.0),
        np.zeros(1),
    )


def test_red_stopping_margin_rejects_nonfinite_online_inputs() -> None:
    candidates = np.array([[[0.0, 0.0], [np.nan, 0.0]]])
    red_points = np.array([[20.0, 0.0, 1.0, 0.0]])

    with pytest.raises(ValueError, match="finite"):
        compute_red_stopping_margin_costs(candidates, red_points, dt=0.1)


def test_dp_prior_deviation_cost_anchors_deterministic_candidate() -> None:
    candidates = np.array(
        [
            [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]],
            [[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]],
            [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]],
        ]
    )

    costs = compute_dp_prior_deviation_costs(candidates)

    np.testing.assert_allclose(costs, np.array([0.0, 5.0 / 3.0, 0.0]))
    assert np.all(costs >= 0.0)


def test_dp_prior_deviation_rejects_nonfinite_candidates() -> None:
    candidates = np.array([[[0.0, 0.0], [np.inf, 0.0]]])

    with pytest.raises(ValueError, match="finite"):
        compute_dp_prior_deviation_costs(candidates)


def test_dp_prior_comfort_excess_costs_anchor_deterministic_candidate() -> None:
    candidates = np.array(
        [
            [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0], [4.0, 0.0]],
            [[0.0, 0.0], [1.0, 0.0], [3.0, 0.0], [6.0, 0.0], [10.0, 0.0]],
            [[0.0, 0.0], [1.0, 0.0], [2.0, 1.0], [3.0, -1.0], [4.0, 0.0]],
        ]
    )

    jerk_excess, acceleration_excess = compute_dp_prior_comfort_excess_costs(
        candidates,
        dt=1.0,
    )

    np.testing.assert_allclose(jerk_excess[0], 0.0)
    np.testing.assert_allclose(acceleration_excess[0], 0.0)
    assert np.all(jerk_excess >= 0.0)
    assert np.all(acceleration_excess >= 0.0)
    assert acceleration_excess[1] > acceleration_excess[0]
    assert jerk_excess[2] > jerk_excess[1]


def test_dp_prior_comfort_excess_rejects_nonfinite_candidates() -> None:
    candidates = np.array([[[0.0, 0.0], [np.nan, 0.0], [1.0, 0.0]]])

    with pytest.raises(ValueError, match="finite"):
        compute_dp_prior_comfort_excess_costs(candidates, dt=0.1)


def test_candidate_reference_blend_preserves_reference_and_recovers_sample() -> None:
    reference = np.array(
        [
            [1.0, 0.0, 1.0, 0.0],
            [2.0, 0.0, 1.0, 0.0],
            [3.0, 0.0, 1.0, 0.0],
            [4.0, 0.0, 1.0, 0.0],
        ]
    )
    sample = np.array(
        [
            [0.0, 1.0, 0.0, 1.0],
            [0.0, 2.0, 0.0, 1.0],
            [0.0, 3.0, 0.0, 1.0],
            [0.0, 4.0, 0.0, 1.0],
        ]
    )
    candidates = np.stack([reference, sample])

    blended = blend_candidate_prefix_with_reference(candidates, blend_steps=2)

    np.testing.assert_allclose(blended[0], reference)
    np.testing.assert_allclose(blended[1, 0], reference[0])
    np.testing.assert_allclose(blended[1, 2:], sample[2:])
    np.testing.assert_allclose(
        blended[1, 1, :2],
        0.5 * reference[1, :2] + 0.5 * sample[1, :2],
    )
    np.testing.assert_allclose(
        np.linalg.norm(blended[1, :, 2:4], axis=1),
        np.ones(4),
    )


@pytest.mark.parametrize("blend_steps", [0, -1, 4, 1.5, True])
def test_candidate_reference_blend_rejects_invalid_steps(blend_steps) -> None:
    candidates = np.zeros((2, 4, 4), dtype=np.float64)

    with pytest.raises(ValueError, match="blend_steps"):
        blend_candidate_prefix_with_reference(candidates, blend_steps)


def test_candidate_generation_disables_guidance_by_default() -> None:
    torch = pytest.importorskip("torch")

    class _Args:
        predicted_neighbor_num = 0
        future_len = 3

    guidance = object()

    class _Decoder:
        _guidance_fn = guidance

    class _Model:
        decoder = _Decoder()

        def __init__(self) -> None:
            self.calls = []

        def __call__(self, inputs):
            self.calls.append(
                {
                    "guidance": self.decoder._guidance_fn,
                    "grad_enabled": torch.is_grad_enabled(),
                }
            )
            sampled = inputs["sampled_trajectories"]
            return None, {"prediction": sampled[:, :, 1:, :]}

    model = _Model()
    inputs = {"ego_current_state": torch.zeros(1, 4)}

    candidates, neighbors, turn_logits = generate_candidate_trajectories(
        model,
        _Args(),
        inputs,
        num_candidates=2,
        noise_scale=0.0,
    )

    assert model.calls == [{"guidance": None, "grad_enabled": False}]
    assert model.decoder._guidance_fn is guidance
    assert candidates.shape == (2, 3, 4)
    assert neighbors.shape == (2, 0, 3, 4)
    assert turn_logits is None


def test_candidate_generation_preserves_guidance_when_requested() -> None:
    torch = pytest.importorskip("torch")

    class _Args:
        predicted_neighbor_num = 0
        future_len = 3

    guidance = object()

    class _Decoder:
        _guidance_fn = guidance

    class _Model:
        decoder = _Decoder()

        def __init__(self) -> None:
            self.calls = []

        def __call__(self, inputs):
            self.calls.append(
                {
                    "guidance": self.decoder._guidance_fn,
                    "grad_enabled": torch.is_grad_enabled(),
                }
            )
            sampled = inputs["sampled_trajectories"]
            return None, {"prediction": sampled[:, :, 1:, :]}

    model = _Model()
    inputs = {"ego_current_state": torch.zeros(1, 4)}

    generate_candidate_trajectories(
        model,
        _Args(),
        inputs,
        num_candidates=2,
        noise_scale=0.0,
        guidance_policy="preserve",
    )

    assert model.calls == [{"guidance": guidance, "grad_enabled": True}]
    assert model.decoder._guidance_fn is guidance


def test_candidate_generation_rejects_unknown_guidance_policy() -> None:
    torch = pytest.importorskip("torch")

    class _Args:
        predicted_neighbor_num = 0
        future_len = 3

    class _Model:
        class decoder:
            _guidance_fn = None

    with pytest.raises(ValueError, match="guidance_policy"):
        generate_candidate_trajectories(
            _Model(),
            _Args(),
            {"ego_current_state": torch.zeros(1, 4)},
            num_candidates=1,
            noise_scale=0.0,
            guidance_policy="bad",
        )


def test_candidate_generation_antithetic_noise_pairs_latents() -> None:
    torch = pytest.importorskip("torch")

    class _Args:
        predicted_neighbor_num = 0
        future_len = 2

    class _Decoder:
        _guidance_fn = None

    class _Model:
        decoder = _Decoder()

        def __init__(self) -> None:
            self.sampled = None

        def __call__(self, inputs):
            sampled = inputs["sampled_trajectories"]
            self.sampled = sampled.detach().clone()
            return None, {"prediction": sampled[:, :, 1:, :]}

    torch.manual_seed(123)
    model = _Model()
    generate_candidate_trajectories(
        model,
        _Args(),
        {"ego_current_state": torch.zeros(1, 4)},
        num_candidates=5,
        noise_scale=1.0,
        noise_strategy="antithetic",
    )

    assert model.sampled is not None
    assert torch.count_nonzero(model.sampled[0]).item() == 0
    torch.testing.assert_close(
        model.sampled[1] + model.sampled[2],
        torch.zeros_like(model.sampled[1]),
    )
    torch.testing.assert_close(
        model.sampled[3] + model.sampled[4],
        torch.zeros_like(model.sampled[3]),
    )


def test_candidate_generation_rejects_unknown_noise_strategy() -> None:
    torch = pytest.importorskip("torch")

    class _Args:
        predicted_neighbor_num = 0
        future_len = 3

    class _Model:
        class decoder:
            _guidance_fn = None

    with pytest.raises(ValueError, match="noise_strategy"):
        generate_candidate_trajectories(
            _Model(),
            _Args(),
            {"ego_current_state": torch.zeros(1, 4)},
            num_candidates=1,
            noise_scale=0.0,
            noise_strategy="bad",
        )


def test_dp_prior_comfort_excess_respects_requested_horizon() -> None:
    reference = np.column_stack(
        [np.arange(8, dtype=np.float64), np.zeros(8, dtype=np.float64)]
    )
    late_oscillation = reference.copy()
    late_oscillation[5:, 1] = [1.0, -1.0, 1.0]
    candidates = np.stack([reference, late_oscillation])

    full_jerk, full_acceleration = compute_dp_prior_comfort_excess_costs(
        candidates,
        dt=1.0,
    )
    truncated_jerk, truncated_acceleration = (
        compute_dp_prior_comfort_excess_costs(
            candidates,
            dt=1.0,
            horizon_steps=5,
        )
    )
    overlong_jerk, overlong_acceleration = (
        compute_dp_prior_comfort_excess_costs(
            candidates,
            dt=1.0,
            horizon_steps=100,
        )
    )

    assert full_jerk[1] > 0.0
    assert full_acceleration[1] > 0.0
    np.testing.assert_allclose(truncated_jerk, np.zeros(2))
    np.testing.assert_allclose(truncated_acceleration, np.zeros(2))
    np.testing.assert_allclose(overlong_jerk, full_jerk)
    np.testing.assert_allclose(overlong_acceleration, full_acceleration)


@pytest.mark.parametrize("horizon_steps", [0, -1, 2.5, True])
def test_dp_prior_comfort_excess_rejects_invalid_horizon(
    horizon_steps,
) -> None:
    candidates = np.zeros((2, 5, 2), dtype=np.float64)

    with pytest.raises(ValueError, match="positive integer"):
        compute_dp_prior_comfort_excess_costs(
            candidates,
            dt=0.1,
            horizon_steps=horizon_steps,
        )


def test_lateral_comfort_shadow_costs_are_horizon_aligned_and_anchored() -> None:
    reference = np.column_stack(
        [np.arange(8, dtype=np.float64), np.zeros(8, dtype=np.float64)]
    )
    early_turn = reference.copy()
    early_turn[2:5, 1] = [0.5, 1.0, 0.5]
    late_turn = reference.copy()
    late_turn[5:, 1] = [0.5, 1.0, 1.5]
    candidates = np.stack([reference, early_turn, late_turn])

    lateral, lateral_excess, yaw_rate, yaw_rate_excess = (
        compute_lateral_comfort_shadow_costs(
            candidates,
            dt=1.0,
            horizon_steps=5,
        )
    )

    np.testing.assert_allclose(lateral_excess[0], 0.0)
    np.testing.assert_allclose(yaw_rate_excess[0], 0.0)
    assert lateral[1] > lateral[0]
    assert yaw_rate[1] > yaw_rate[0]
    np.testing.assert_allclose(lateral[2], lateral[0])
    np.testing.assert_allclose(yaw_rate[2], yaw_rate[0])
    assert np.all(lateral >= 0.0)
    assert np.all(yaw_rate >= 0.0)


@pytest.mark.parametrize("horizon_steps", [0, -1, 2.5, True])
def test_lateral_comfort_shadow_rejects_invalid_horizon(horizon_steps) -> None:
    candidates = np.zeros((2, 5, 2), dtype=np.float64)

    with pytest.raises(ValueError, match="positive integer"):
        compute_lateral_comfort_shadow_costs(
            candidates,
            dt=0.1,
            horizon_steps=horizon_steps,
        )


def test_closed_loop_outcome_labels_prefer_best_feasible_candidate(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(
        json.dumps(
            [
                {
                    "atoms": [[0.0] * 9, [1.0] * 9, [2.0] * 9],
                    "feasible_mask": [True, True, True],
                    "candidate_closed_loop_outcomes": [
                        {"value": 1.0, "feasible": True},
                        {"value": 100.0, "feasible": False},
                        {"value": 5.0, "feasible": True},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    _, selector_feasible = load_training_records([log_path])
    values, outcome_feasible = load_candidate_closed_loop_outcomes([log_path])
    labels = reward_oracle_indices(values, outcome_feasible)

    assert selector_feasible.tolist() == [[True, True, True]]
    assert outcome_feasible.tolist() == [[True, False, True]]
    assert values.tolist() == [[1.0, 100.0, 5.0]]
    assert labels.tolist() == [2]


def test_closed_loop_outcome_labels_can_be_reweighted(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(
        json.dumps(
            [
                {
                    "atoms": [[0.0] * 9, [1.0] * 9],
                    "feasible_mask": [True, True],
                    "candidate_closed_loop_outcomes": [
                        {
                            "value": 1.0,
                            "progress_m": 10.0,
                            "collision": False,
                            "near_miss": False,
                            "lane_violation": False,
                            "red_light_violation": False,
                            "mean_jerk_mps3": 1.0,
                            "mean_lateral_acceleration_mps2": 0.1,
                            "feasible": True,
                        },
                        {
                            "value": 100.0,
                            "progress_m": 12.0,
                            "collision": False,
                            "near_miss": False,
                            "lane_violation": False,
                            "red_light_violation": True,
                            "mean_jerk_mps3": 0.1,
                            "mean_lateral_acceleration_mps2": 0.1,
                            "feasible": True,
                        },
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    stored_values, feasible = load_candidate_closed_loop_outcomes([log_path])
    stored_labels = reward_oracle_indices(stored_values, feasible)
    weighted_values, weighted_feasible = load_candidate_closed_loop_outcomes(
        [log_path],
        outcome_weights={
            "progress": 1.0,
            "collision": 100.0,
            "near_miss": 10.0,
            "lane_violation": 20.0,
            "red_light": 80.0,
            "mean_jerk": 0.75,
            "mean_lateral_acceleration": 3.0,
        },
    )
    weighted_labels = reward_oracle_indices(weighted_values, weighted_feasible)

    assert stored_labels.tolist() == [1]
    assert weighted_feasible.tolist() == feasible.tolist()
    assert weighted_labels.tolist() == [0]


def test_robust_margin_oracle_and_margins_exclude_infeasible_candidates() -> None:
    values = np.array([[10.0, 100.0, 4.0], [1.0, 3.0, 2.0]])
    feasible = np.array([[True, False, True], [True, True, False]])

    oracle, margins = outcome_oracle_and_margins(
        values,
        feasible,
        margin_scale=0.5,
        margin_clip=2.0,
    )

    assert oracle.tolist() == [0, 1]
    np.testing.assert_allclose(margins[0], [0.0, 0.0, 2.0])
    np.testing.assert_allclose(margins[1], [1.0, 0.0, 0.0])


def test_robust_margin_violation_has_correct_ranking_direction() -> None:
    atoms = np.array(
        [
            [
                [0.0, 1.0],
                [1.0, 0.0],
                [10.0, 10.0],
            ]
        ]
    )
    oracle = np.array([0])
    margins = np.array([[0.0, 0.5, 0.0]])
    feasible = np.array([[True, True, False]])

    _, safe_violation, safe_worst = candidate_ranking_violations(
        atoms,
        np.array([0.9, 0.1]),
        oracle,
        margins,
        feasible,
    )
    candidate_values, bad_violation, bad_worst = candidate_ranking_violations(
        atoms,
        np.array([0.1, 0.9]),
        oracle,
        margins,
        feasible,
    )

    assert safe_violation.tolist() == [0.0]
    assert safe_worst.tolist() == [0]
    assert bad_violation[0] > 1.0
    assert bad_worst.tolist() == [1]
    assert np.isneginf(candidate_values[0, 2])


def test_robust_margin_candidate_loss_is_convex_in_simplex_weights() -> None:
    atoms = np.array(
        [
            [
                [0.1, 0.8, 0.4],
                [0.7, 0.2, 0.3],
                [0.4, 0.6, 0.1],
            ]
        ]
    )
    oracle = np.array([0])
    margins = np.array([[0.0, 0.3, 0.6]])
    feasible = np.ones((1, 3), dtype=bool)
    left = np.array([0.8, 0.1, 0.1])
    right = np.array([0.1, 0.2, 0.7])
    interpolation = 0.37
    middle = interpolation * left + (1.0 - interpolation) * right

    _, left_loss, _ = candidate_ranking_violations(
        atoms, left, oracle, margins, feasible
    )
    _, right_loss, _ = candidate_ranking_violations(
        atoms, right, oracle, margins, feasible
    )
    _, middle_loss, _ = candidate_ranking_violations(
        atoms, middle, oracle, margins, feasible
    )

    convex_bound = interpolation * left_loss + (1.0 - interpolation) * right_loss
    assert middle_loss[0] <= convex_bound[0] + 1e-12


def test_robust_margin_master_rejects_invalid_atom_contract() -> None:
    atoms = np.array([[[0.0, -0.1], [1.0, 0.0]]])
    oracle = np.array([0])
    margins = np.zeros((1, 2))
    feasible = np.ones((1, 2), dtype=bool)

    with pytest.raises(ValueError, match="nonnegative cost features"):
        solve_robust_margin_cutting_plane(
            atoms,
            oracle,
            margins,
            feasible,
            config=RobustMarginConfig(mode="static"),
        )


def test_atom_schema_validation_rejects_same_dimension_reordering(tmp_path) -> None:
    version, names = atom_schema_for_dimension(len(DP_CAMP_ATOM_NAMES_V8))
    record = {
        "atoms": np.zeros((2, len(names))).tolist(),
        "feasible_mask": [True, True],
        "atom_schema_version": version,
        "atom_names": list(reversed(names)),
    }
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(json.dumps([record]), encoding="utf-8")

    with pytest.raises(ValueError, match="uses atom schema"):
        validate_atom_schema(
            [log_path],
            DP_CAMP_ATOM_NAMES_V8,
            require=True,
        )

    record["atom_names"] = list(names)
    log_path.write_text(json.dumps([record]), encoding="utf-8")
    summary = validate_atom_schema(
        [log_path],
        DP_CAMP_ATOM_NAMES_V8,
        require=True,
    )
    assert summary["version"] == "dp_camp_v8_12d"
    assert summary["verified_records"] == 1
    assert summary["missing_records"] == 0


def test_v9_atom_schema_names_red_stopping_margin() -> None:
    version, names = atom_schema_for_dimension(len(DP_CAMP_ATOM_NAMES_V9))

    assert version == "dp_camp_v9_13d"
    assert names == DP_CAMP_ATOM_NAMES_V9
    assert names[-1] == "red_stopping_margin_cost"


def test_v10_atom_schema_names_dp_prior_jerk_excess() -> None:
    version, names = atom_schema_for_dimension(len(DP_CAMP_ATOM_NAMES_V10))

    assert version == "dp_camp_v10_14d"
    assert names == DP_CAMP_ATOM_NAMES_V10
    assert names[-1] == "dp_prior_jerk_excess_cost"


def test_atom_schema_validation_can_require_metadata(tmp_path) -> None:
    record = {
        "atoms": np.zeros((2, len(DP_CAMP_ATOM_NAMES_V8))).tolist(),
        "feasible_mask": [True, True],
    }
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(json.dumps([record]), encoding="utf-8")

    with pytest.raises(ValueError, match="no atom schema metadata"):
        validate_atom_schema(
            [log_path],
            DP_CAMP_ATOM_NAMES_V8,
            require=True,
        )


def test_grouped_split_keeps_selection_logs_disjoint() -> None:
    groups = np.repeat(np.arange(6), 4)
    train_idx, val_idx, train_groups, val_groups = grouped_train_val_indices(
        groups,
        val_fraction=1.0 / 3.0,
        seed=7,
    )

    assert train_groups == 4
    assert val_groups == 2
    assert set(groups[train_idx]).isdisjoint(set(groups[val_idx]))
    assert sorted(np.concatenate([train_idx, val_idx]).tolist()) == list(
        range(groups.size)
    )


def test_grouped_split_rejects_invalid_validation_fraction() -> None:
    with pytest.raises(ValueError, match="val_fraction"):
        grouped_train_val_indices(
            np.array([0, 1]),
            val_fraction=1.0,
            seed=7,
        )


def test_named_atom_weight_lower_bounds_are_validated() -> None:
    lower = parse_atom_weight_lower_bounds(
        ["jerk_early=0.1", "clearance=0.2"],
        CAMP_ATOM_NAMES,
    )

    assert lower[CAMP_ATOM_NAMES.index("jerk_early")] == pytest.approx(0.1)
    assert lower[CAMP_ATOM_NAMES.index("clearance")] == pytest.approx(0.2)
    with pytest.raises(ValueError, match="Unknown atom"):
        parse_atom_weight_lower_bounds(["missing=0.1"], CAMP_ATOM_NAMES)
    with pytest.raises(ValueError, match="sum to at most one"):
        parse_atom_weight_lower_bounds(
            ["jerk_early=0.6", "clearance=0.5"],
            CAMP_ATOM_NAMES,
        )


def test_static_robust_training_uses_grouped_validation_and_train_only_scales(
    tmp_path,
    monkeypatch,
) -> None:
    pytest.importorskip("cvxpy")
    log_paths = []
    all_atoms = []
    group_ids = []
    for group_idx, atom_base in enumerate([1.0, 3.0, 100.0]):
        atoms = np.vstack(
            [
                np.full(len(CAMP_ATOM_NAMES), atom_base),
                np.full(len(CAMP_ATOM_NAMES), atom_base + 1.0),
            ]
        )
        record = {
            "atoms": atoms.tolist(),
            "feasible_mask": [True, True],
            "candidate_closed_loop_outcomes": [
                {"value": 1.0, "feasible": True},
                {"value": 0.0, "feasible": True},
            ],
        }
        log_path = tmp_path / f"group_{group_idx}" / "camp_selection_log.json"
        log_path.parent.mkdir()
        log_path.write_text(json.dumps([record]), encoding="utf-8")
        log_paths.append(log_path)
        all_atoms.append(atoms)
        group_ids.append(group_idx)

    train_idx, _, _, _ = grouped_train_val_indices(
        np.asarray(group_ids),
        val_fraction=1.0 / 3.0,
        seed=7,
    )
    expected_scales = robust_atom_scales(
        np.asarray(all_atoms)[train_idx],
        percentile=95.0,
    )
    output_dir = tmp_path / "trained"
    argv = [
        "train_diffusion_planner_robust_camp.py",
        "--output_dir",
        str(output_dir),
        "--mode",
        "static",
        "--val_fraction",
        str(1.0 / 3.0),
        "--seed",
        "7",
        "--max_iter",
        "5",
        "--min_atom_weight",
        "clearance=0.2",
    ]
    for log_path in log_paths:
        argv.extend(["--selection_log", str(log_path)])
    monkeypatch.setattr(sys, "argv", argv)

    train_robust_camp_main()

    summary = json.loads(
        (output_dir / "training_summary.json").read_text(encoding="utf-8")
    )
    saved_scale_payload = json.loads(
        (output_dir / "atom_scales_dp_static.json").read_text(encoding="utf-8")
    )
    saved_scales = np.asarray(saved_scale_payload["scales"])
    assert summary["train_groups"] == 2
    assert summary["val_groups"] == 1
    assert summary["val_metrics"]["records"] == 1.0
    assert summary["normalization_fit_scope"] == "train_groups_only"
    assert saved_scale_payload["atom_schema_version"] == "camp_legacy_v1_9d"
    assert saved_scale_payload["atom_names"] == list(CAMP_ATOM_NAMES)
    assert set(summary["train_selection_logs"]).isdisjoint(
        summary["val_selection_logs"]
    )
    assert summary["minimum_atom_weights"] == {"clearance": 0.2}
    saved_weights = np.load(output_dir / "offline_weights_dp_static.npy")
    assert saved_weights[CAMP_ATOM_NAMES.index("clearance")] >= 0.2 - 1e-8
    np.testing.assert_allclose(saved_scales, expected_scales)


def test_static_robust_training_can_target_all_infeasible_fallback(
    tmp_path,
    monkeypatch,
) -> None:
    pytest.importorskip("cvxpy")
    log_paths = []
    for group_idx in range(3):
        fallback_atoms = np.vstack(
            [
                np.arange(1.0, len(CAMP_ATOM_NAMES) + 1.0),
                np.arange(len(CAMP_ATOM_NAMES), 0.0, -1.0),
            ]
        )
        records = [
            {
                "atom_schema_version": "camp_legacy_v1_9d",
                "atom_names": list(CAMP_ATOM_NAMES),
                "atoms": fallback_atoms.tolist(),
                "feasible_mask": [False, False],
                "candidate_closed_loop_outcomes": [
                    {"value": 0.0, "feasible": False},
                    {"value": 1.0 + group_idx, "feasible": False},
                ],
            },
            {
                "atom_schema_version": "camp_legacy_v1_9d",
                "atom_names": list(CAMP_ATOM_NAMES),
                "atoms": (fallback_atoms + 1.0).tolist(),
                "feasible_mask": [True, True],
                "candidate_closed_loop_outcomes": [
                    {"value": 1.0, "feasible": True},
                    {"value": 0.0, "feasible": True},
                ],
            },
        ]
        log_path = tmp_path / f"group_{group_idx}" / "camp_selection_log.json"
        log_path.parent.mkdir()
        log_path.write_text(json.dumps(records), encoding="utf-8")
        log_paths.append(log_path)

    output_dir = tmp_path / "fallback_trained"
    argv = [
        "train_diffusion_planner_robust_camp.py",
        "--output_dir",
        str(output_dir),
        "--mode",
        "static",
        "--training_scope",
        "all_infeasible_fallback",
        "--require_atom_schema",
        "--val_fraction",
        str(1.0 / 3.0),
        "--seed",
        "7",
        "--max_iter",
        "5",
    ]
    for log_path in log_paths:
        argv.extend(["--selection_log", str(log_path)])
    monkeypatch.setattr(sys, "argv", argv)

    train_robust_camp_main()

    summary = json.loads(
        (output_dir / "training_summary.json").read_text(encoding="utf-8")
    )
    assert summary["training_scope"] == "all_infeasible_fallback"
    assert summary["input_records"] == 6
    assert summary["scope_records"] == 3
    assert summary["num_records"] == 3
    assert summary["converged"]
    assert summary["final_master_gap"] <= summary["tolerance"]
    assert (output_dir / "atom_scales_dp_fallback.json").is_file()
    assert (output_dir / "offline_weights_dp_fallback.npy").is_file()


def test_empirical_cvar_emphasizes_worst_case_loss() -> None:
    losses = np.array([0.0, 0.0, 1.0, 9.0])

    cvar, eta = empirical_cvar(losses, alpha=0.75)

    assert cvar == 9.0
    assert eta in {1.0, 9.0}
    assert cvar > float(np.mean(losses))


def test_project_simplex_rows_enforces_nonnegative_unit_sum() -> None:
    projected = project_simplex_rows(
        np.array(
            [
                [-2.0, 0.5, 3.0],
                [10.0, -1.0, -1.0],
            ]
        )
    )

    np.testing.assert_allclose(projected.sum(axis=1), 1.0)
    assert np.all(projected >= 0.0)


def test_robust_margin_master_outputs_simplex_static_and_theta() -> None:
    pytest.importorskip("cvxpy")
    atoms = np.array(
        [
            [[0.0, 1.0], [1.0, 0.0]],
            [[1.0, 0.0], [0.0, 1.0]],
            [[0.0, 1.0], [1.0, 0.0]],
            [[1.0, 0.0], [0.0, 1.0]],
        ]
    )
    oracle = np.array([0, 1, 0, 1])
    margins = np.array([[0.0, 0.2], [0.2, 0.0], [0.0, 0.2], [0.2, 0.0]])
    feasible = np.ones((4, 2), dtype=bool)

    static_result = solve_robust_margin_cutting_plane(
        atoms,
        oracle,
        margins,
        feasible,
        config=RobustMarginConfig(
            mode="static",
            risk_type="cvar",
            alpha=0.5,
            l2_reg=1e-4,
            max_iter=5,
        ),
    )
    np.testing.assert_allclose(static_result.static_weights.sum(), 1.0, atol=1e-6)
    assert np.all(static_result.static_weights >= -1e-7)
    assert static_result.converged
    assert static_result.final_master_gap <= 1e-6

    features = np.array([[-1.0], [1.0], [-1.0], [1.0]])
    theta_result = solve_robust_margin_cutting_plane(
        atoms,
        oracle,
        margins,
        feasible,
        features=features,
        config=RobustMarginConfig(
            mode="theta",
            risk_type="cvar",
            alpha=0.5,
            l2_reg=1e-4,
            max_iter=5,
        ),
    )
    weights = theta_weights(theta_result.theta, features)
    np.testing.assert_allclose(weights.sum(axis=1), 1.0, atol=1e-6)
    assert np.all(weights >= -1e-7)
    assert theta_result.converged
    assert theta_result.final_master_gap <= 1e-6


def test_static_robust_margin_master_honors_affine_weight_lower_bounds() -> None:
    pytest.importorskip("cvxpy")
    atoms = np.array(
        [
            [[0.0, 1.0], [1.0, 0.0]],
            [[0.0, 1.0], [1.0, 0.0]],
        ]
    )
    oracle = np.array([0, 0])
    margins = np.array([[0.0, 0.2], [0.0, 0.2]])
    feasible = np.ones((2, 2), dtype=bool)

    result = solve_robust_margin_cutting_plane(
        atoms,
        oracle,
        margins,
        feasible,
        config=RobustMarginConfig(
            mode="static",
            max_iter=5,
            static_weight_lower_bounds=(0.7, 0.2),
        ),
    )

    assert result.converged
    assert result.final_master_gap <= 1e-6
    assert result.static_weights[0] >= 0.7 - 1e-8
    assert result.static_weights[1] >= 0.2 - 1e-8
    np.testing.assert_allclose(result.static_weights.sum(), 1.0, atol=1e-8)


def test_static_cutting_plane_matches_full_epigraph_master() -> None:
    cp = pytest.importorskip("cvxpy")
    atoms = np.array(
        [
            [[0.1, 0.8, 0.4], [0.7, 0.2, 0.3], [0.4, 0.6, 0.1]],
            [[0.9, 0.1, 0.2], [0.2, 0.7, 0.5], [0.3, 0.4, 0.8]],
            [[0.5, 0.3, 0.9], [0.1, 0.8, 0.2], [0.7, 0.2, 0.4]],
        ]
    )
    oracle = np.array([0, 1, 2])
    margins = np.array(
        [[0.0, 0.3, 0.7], [0.4, 0.0, 0.2], [0.5, 0.6, 0.0]]
    )
    feasible = np.array(
        [[True, True, True], [True, True, False], [True, True, True]]
    )
    l2_reg = 0.03
    config = RobustMarginConfig(
        mode="static",
        risk_type="mean",
        l2_reg=l2_reg,
        max_iter=10,
        tolerance=1e-7,
    )

    result = solve_robust_margin_cutting_plane(
        atoms,
        oracle,
        margins,
        feasible,
        config=config,
    )

    weights = cp.Variable(atoms.shape[-1])
    losses = cp.Variable(atoms.shape[0], nonneg=True)
    constraints = [weights >= 0.0, cp.sum(weights) == 1.0]
    for record_idx in range(atoms.shape[0]):
        oracle_atoms = atoms[record_idx, oracle[record_idx]]
        for candidate_idx in np.flatnonzero(feasible[record_idx]):
            constraints.append(
                losses[record_idx]
                >= margins[record_idx, candidate_idx]
                + (oracle_atoms - atoms[record_idx, candidate_idx]) @ weights
            )
    uniform = np.full(atoms.shape[-1], 1.0 / atoms.shape[-1])
    objective = cp.Minimize(
        cp.sum(losses) / atoms.shape[0]
        + l2_reg * cp.sum_squares(weights - uniform)
    )
    problem = cp.Problem(objective, constraints)
    installed = set(cp.installed_solvers())
    solver = next(name for name in ("CLARABEL", "SCS") if name in installed)
    problem.solve(solver=solver)

    assert problem.status in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}
    assert result.converged
    assert result.final_master_gap <= config.tolerance
    result_objective = float(np.mean(result.train_violations)) + l2_reg * float(
        np.sum((result.static_weights - uniform) ** 2)
    )
    assert result_objective == pytest.approx(problem.value, abs=2e-5)
    np.testing.assert_allclose(
        result.static_weights,
        np.asarray(weights.value).reshape(-1),
        atol=2e-4,
    )


def test_robust_theta_checkpoint_loads_in_existing_selector(tmp_path) -> None:
    scales_path = tmp_path / "scales.json"
    scales_path.write_text(json.dumps([1.0, 1.0]), encoding="utf-8")
    checkpoint_path = tmp_path / "theta.npz"
    theta = np.array([[0.5, 0.5], [-0.5, 0.5]])
    save_theta_checkpoint(
        checkpoint_path,
        theta=theta,
        offline_weights=np.array([0.5, 0.5]),
        feature_center=np.array([0.0]),
        feature_scale=np.array([1.0]),
        feature_clip=5.0,
    )

    selector = CAMPSelector.from_files(
        atom_scales_path=scales_path,
        checkpoint_path=checkpoint_path,
        mode="linear",
    )
    weights = selector.weights_for(np.array([1.0]))

    np.testing.assert_allclose(weights.sum(), 1.0)
    assert np.all(weights >= 0.0)
    assert selector.linear_activation == "project_simplex"


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
        group_ids=np.array([0, 0, 1, 1, 2, 2]),
    )

    assert features.shape == (6, feature_dim)
    assert theta.shape == (len(CAMP_ATOM_NAMES), feature_dim + 1)
    assert history
    assert final_metrics["train_records"] > 0
    assert final_metrics["train_groups"] == 2.0
    assert final_metrics["val_groups"] == 1.0


def test_summarize_selection_records_reports_candidate_usage() -> None:
    records = [
        {
            "selected_index": 0,
            "used_fallback": False,
            "feasible_mask": [True, False],
            "latency_ms_including_candidate_generation": 10.0,
            "latency_ms_candidate_generation": 6.0,
            "latency_ms_shadow_dp_prior_deviation": 0.2,
            "latency_ms_shadow_dp_prior_comfort_excess": 0.1,
            "latency_ms_shadow_lateral_comfort": 0.2,
            "latency_ms_shadow_obstacle_clearance": 0.4,
            "latency_ms_shadow_perfect_tracker_command": 0.25,
            "latency_ms_context_and_obstacles": 1.0,
            "latency_ms_reward_scoring": 2.0,
            "latency_ms_reward_batch_compute": 0.8,
            "latency_ms_reward_full_horizon_red_light": 0.4,
            "latency_ms_reward_route_progress": 0.1,
            "latency_ms_outcome_collection": 0.0,
            "latency_ms_camp_selection": 1.0,
            "latency_ms_perfect_tracker_command_postselection": 0.05,
            "latency_ms_camp_atom_computation": 0.3,
            "latency_ms_camp_feasibility": 0.1,
            "latency_ms_camp_collision_checks": 0.4,
            "latency_ms_camp_scoring": 0.2,
        },
        {
            "selected_index": 1,
            "used_fallback": True,
            "feasible_mask": [False, False],
            "latency_ms_including_candidate_generation": 20.0,
            "latency_ms_candidate_generation": 12.0,
            "latency_ms_shadow_dp_prior_deviation": 0.4,
            "latency_ms_shadow_dp_prior_comfort_excess": 0.3,
            "latency_ms_shadow_lateral_comfort": 0.4,
            "latency_ms_shadow_obstacle_clearance": 0.6,
            "latency_ms_shadow_perfect_tracker_command": 0.35,
            "latency_ms_context_and_obstacles": 2.0,
            "latency_ms_reward_scoring": 4.0,
            "latency_ms_reward_batch_compute": 1.6,
            "latency_ms_reward_full_horizon_red_light": 0.8,
            "latency_ms_reward_route_progress": 0.2,
            "latency_ms_outcome_collection": 0.0,
            "latency_ms_camp_selection": 2.0,
            "latency_ms_perfect_tracker_command_postselection": 0.15,
            "latency_ms_camp_atom_computation": 0.6,
            "latency_ms_camp_feasibility": 0.2,
            "latency_ms_camp_collision_checks": 0.8,
            "latency_ms_camp_scoring": 0.4,
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
    assert summary["mean_candidate_generation_latency_ms"] == 9.0
    assert summary["mean_shadow_dp_prior_deviation_latency_ms"] == pytest.approx(
        0.3
    )
    assert summary["mean_shadow_dp_prior_comfort_excess_latency_ms"] == pytest.approx(
        0.2
    )
    assert summary["mean_shadow_lateral_comfort_latency_ms"] == pytest.approx(
        0.3
    )
    assert summary["mean_shadow_obstacle_clearance_latency_ms"] == pytest.approx(
        0.5
    )
    assert summary[
        "mean_shadow_perfect_tracker_command_latency_ms"
    ] == pytest.approx(0.3)
    assert summary["mean_context_and_obstacles_latency_ms"] == 1.5
    assert summary["mean_reward_scoring_latency_ms"] == 3.0
    assert summary["mean_reward_batch_compute_latency_ms"] == pytest.approx(1.2)
    assert summary[
        "mean_reward_full_horizon_red_light_latency_ms"
    ] == pytest.approx(0.6)
    assert summary["mean_reward_route_progress_latency_ms"] == pytest.approx(0.15)
    assert summary["mean_outcome_collection_latency_ms"] == 0.0
    assert summary["mean_camp_selection_latency_ms"] == 1.5
    assert summary[
        "mean_perfect_tracker_command_postselection_latency_ms"
    ] == pytest.approx(0.1)
    assert summary["mean_camp_atom_computation_latency_ms"] == pytest.approx(0.45)
    assert summary["mean_camp_feasibility_latency_ms"] == pytest.approx(0.15)
    assert summary["mean_camp_collision_checks_latency_ms"] == pytest.approx(0.6)
    assert summary["mean_camp_scoring_latency_ms"] == pytest.approx(0.3)
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


def test_dp_selector_appends_progress_shortfall_atom() -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=5.0,
        speed_limit=50.0,
    )
    x = np.linspace(0.5, 4.0, 8)
    candidates = np.stack(
        [
            np.column_stack([x, np.zeros_like(x)]),
            np.column_stack([x, np.full_like(x, 0.1)]),
        ]
    )
    weights = np.zeros(len(DP_CAMP_ATOM_NAMES))
    weights[-1] = 1.0
    selector = CAMPSelector(
        atom_scales=np.ones(len(DP_CAMP_ATOM_NAMES)),
        static_weights=weights,
        mode="static",
    )

    result = selector.select(
        candidates,
        context,
        candidate_progress=np.array([5.0, 10.0]),
    )

    assert result.atoms.shape == (2, len(DP_CAMP_ATOM_NAMES))
    np.testing.assert_allclose(result.atoms[:, -1], np.array([5.0, 0.0]))
    assert result.selected_index == 1


def test_dp_v8_selector_appends_red_light_and_lateral_atoms() -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=5.0,
        speed_limit=50.0,
    )
    x = np.linspace(0.5, 4.0, 8)
    oscillating = np.column_stack(
        [x, np.array([0.0, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5, 0.0])]
    )
    smooth = np.column_stack([x, np.zeros_like(x)])
    candidates = np.stack([oscillating, smooth])
    weights = np.zeros(len(DP_CAMP_ATOM_NAMES_V8))
    weights[-2] = 1.0
    selector = CAMPSelector(
        atom_scales=np.ones(len(DP_CAMP_ATOM_NAMES_V8)),
        static_weights=weights,
        mode="static",
        fallback_mode="learned",
    )

    result = selector.select(
        candidates,
        context,
        candidate_progress=np.array([5.0, 10.0]),
        candidate_planned_red_light_cost=np.array([5.0, 0.0]),
    )

    assert result.atoms.shape == (2, len(DP_CAMP_ATOM_NAMES_V8))
    np.testing.assert_allclose(result.atoms[:, -3], np.array([5.0, 0.0]))
    np.testing.assert_allclose(result.atoms[:, -2], np.array([5.0, 0.0]))
    assert result.atoms[1, -1] == 0.0
    assert result.selected_index == 1


def test_dp_v9_selector_appends_red_stopping_margin_atom() -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=5.0,
        speed_limit=50.0,
    )
    x = np.linspace(0.5, 4.0, 8)
    candidates = np.stack(
        [
            np.column_stack([x, np.zeros_like(x)]),
            np.column_stack([x, np.full_like(x, 0.1)]),
        ]
    )
    weights = np.zeros(len(DP_CAMP_ATOM_NAMES_V9))
    weights[-1] = 1.0
    selector = CAMPSelector(
        atom_scales=np.ones(len(DP_CAMP_ATOM_NAMES_V9)),
        static_weights=weights,
        mode="static",
    )

    result = selector.select(
        candidates,
        context,
        candidate_progress=np.array([10.0, 10.0]),
        candidate_planned_red_light_cost=np.array([0.0, 0.0]),
        candidate_red_stopping_margin_cost=np.array([4.0, 0.0]),
    )

    assert result.atoms.shape == (2, len(DP_CAMP_ATOM_NAMES_V9))
    np.testing.assert_allclose(result.atoms[:, -1], np.array([4.0, 0.0]))
    assert result.selected_index == 1


def test_dp_v9_selector_rejects_invalid_red_stopping_margin_atom() -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=5.0,
        speed_limit=50.0,
    )
    x = np.linspace(0.5, 4.0, 8)
    candidates = np.stack(
        [
            np.column_stack([x, np.zeros_like(x)]),
            np.column_stack([x, np.full_like(x, 0.1)]),
        ]
    )
    selector = CAMPSelector(
        atom_scales=np.ones(len(DP_CAMP_ATOM_NAMES_V9)),
        static_weights=np.ones(len(DP_CAMP_ATOM_NAMES_V9)),
        mode="static",
    )

    with pytest.raises(ValueError, match="finite nonnegative"):
        selector.select(
            candidates,
            context,
            candidate_progress=np.array([10.0, 10.0]),
            candidate_planned_red_light_cost=np.array([0.0, 0.0]),
            candidate_red_stopping_margin_cost=np.array([0.0, -1.0]),
        )


def test_dp_v10_selector_appends_dp_prior_jerk_excess_atom() -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=5.0,
        speed_limit=50.0,
    )
    x = np.linspace(0.5, 4.0, 8)
    candidates = np.stack(
        [
            np.column_stack([x, np.zeros_like(x)]),
            np.column_stack([x, np.full_like(x, 0.1)]),
        ]
    )
    weights = np.zeros(len(DP_CAMP_ATOM_NAMES_V10))
    weights[-1] = 1.0
    selector = CAMPSelector(
        atom_scales=np.ones(len(DP_CAMP_ATOM_NAMES_V10)),
        static_weights=weights,
        mode="static",
    )

    result = selector.select(
        candidates,
        context,
        candidate_progress=np.array([10.0, 10.0]),
        candidate_planned_red_light_cost=np.array([0.0, 0.0]),
        candidate_red_stopping_margin_cost=np.array([0.0, 0.0]),
        candidate_dp_prior_jerk_excess_cost=np.array([0.0, 3.0]),
    )

    assert result.atoms.shape == (2, len(DP_CAMP_ATOM_NAMES_V10))
    np.testing.assert_allclose(result.atoms[:, -1], np.array([0.0, 3.0]))
    assert result.selected_index == 0


def test_dp_v10_selector_rejects_invalid_dp_prior_jerk_excess_atom() -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=5.0,
        speed_limit=50.0,
    )
    x = np.linspace(0.5, 4.0, 8)
    candidates = np.stack(
        [
            np.column_stack([x, np.zeros_like(x)]),
            np.column_stack([x, np.full_like(x, 0.1)]),
        ]
    )
    selector = CAMPSelector(
        atom_scales=np.ones(len(DP_CAMP_ATOM_NAMES_V10)),
        static_weights=np.ones(len(DP_CAMP_ATOM_NAMES_V10)),
        mode="static",
    )

    with pytest.raises(ValueError, match="finite nonnegative"):
        selector.select(
            candidates,
            context,
            candidate_progress=np.array([10.0, 10.0]),
            candidate_planned_red_light_cost=np.array([0.0, 0.0]),
            candidate_red_stopping_margin_cost=np.array([0.0, 0.0]),
            candidate_dp_prior_jerk_excess_cost=np.array([0.0, np.nan]),
        )


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


def test_learned_fallback_only_changes_all_infeasible_branch() -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=0.1,
        lane_corridor_buffer=0.0,
        speed_limit=2.0,
        desired_speed=1.0,
    )
    x_fast = np.linspace(0.5, 8.0, 8)
    x_slow = np.linspace(0.5, 1.2, 8)
    candidate_fast = np.column_stack([x_fast, np.full_like(x_fast, 0.12)])
    candidate_slow = np.column_stack([x_slow, np.full_like(x_slow, 0.5)])
    candidates = np.stack([candidate_fast, candidate_slow])
    learned_weights = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0])

    uniform_selector = CAMPSelector(
        atom_scales=np.ones(9),
        static_weights=learned_weights,
        mode="static",
        fallback_mode="uniform",
    )
    learned_selector = CAMPSelector(
        atom_scales=np.ones(9),
        static_weights=learned_weights,
        mode="static",
        fallback_mode="learned",
    )

    uniform_result = uniform_selector.select(candidates, context)
    learned_result = learned_selector.select(candidates, context)

    assert uniform_result.used_fallback
    assert learned_result.used_fallback
    assert uniform_result.feasible_mask.tolist() == [False, False]
    assert learned_result.feasible_mask.tolist() == [False, False]
    assert learned_result.selected_index == 0
    assert uniform_result.selected_index == 1


def test_dedicated_fallback_model_is_used_only_for_all_infeasible_branch() -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=0.1,
        lane_corridor_buffer=0.0,
        speed_limit=2.0,
        desired_speed=1.0,
    )
    x_fast = np.linspace(0.5, 8.0, 8)
    x_slow = np.linspace(0.5, 1.2, 8)
    candidates = np.stack(
        [
            np.column_stack([x_fast, np.full_like(x_fast, 0.12)]),
            np.column_stack([x_slow, np.full_like(x_slow, 0.5)]),
        ]
    )
    primary_weights = np.eye(9)[0]
    fallback_weights = np.eye(9)[7]
    selector = CAMPSelector(
        atom_scales=np.ones(9),
        static_weights=primary_weights,
        mode="static",
        fallback_mode="learned",
        fallback_atom_scales=np.full(9, 2.0),
        fallback_static_weights=fallback_weights,
    )

    fallback_result = selector.select(candidates, context)
    feasible_result = selector.select(
        candidates,
        context,
        external_feasible_mask=np.ones(2, dtype=bool),
        apply_context_feasibility=False,
    )

    assert fallback_result.used_fallback
    np.testing.assert_allclose(
        fallback_result.selection_weights,
        fallback_weights,
    )
    np.testing.assert_allclose(
        fallback_result.selection_normalized_atoms,
        np.clip(fallback_result.atoms / 2.0, 0.0, 10.0),
    )
    assert not feasible_result.used_fallback
    np.testing.assert_allclose(
        feasible_result.selection_weights,
        primary_weights,
    )
    np.testing.assert_allclose(
        feasible_result.selection_scores,
        feasible_result.scores,
    )


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


def _traffic_light_hybrid_base_selection() -> CAMPSelectionResult:
    return CAMPSelectionResult(
        selected_index=0,
        selected_trajectory=np.zeros((4, 2), dtype=np.float64),
        atoms=np.ones((3, 2), dtype=np.float64),
        normalized_atoms=np.ones((3, 2), dtype=np.float64),
        feasible_mask=np.array([True, True, True]),
        infeasibility_reasons=((), (), ()),
        scores=np.array([0.1, 0.2, 0.0], dtype=np.float64),
        weights=np.array([0.5, 0.5], dtype=np.float64),
        selection_scores=np.array([0.1, 0.2, 0.0], dtype=np.float64),
        selection_weights=np.array([0.5, 0.5], dtype=np.float64),
        selection_normalized_atoms=np.ones((3, 2), dtype=np.float64),
        used_fallback=False,
        timings_ms={},
    )


def _traffic_light_hybrid_rollout() -> dict:
    return {
        "horizons": {
            "3": {
                "distance_m": np.array([3.0, 2.95, 2.95], dtype=np.float64),
            },
            "10": {
                "distance_m": np.array([10.0, 9.97, 9.0], dtype=np.float64),
            },
        }
    }


def test_traffic_light_hybrid_postselection_selects_admissible_candidate() -> None:
    selected, stats = _apply_traffic_light_hybrid_postselection(
        _traffic_light_hybrid_base_selection(),
        traffic_lights_enabled=True,
        mode="step_h10_guard_005",
        candidate_step_reach=np.array([1.0, 0.96, 0.96], dtype=np.float64),
        candidate_progress=np.array([5.0, 4.97, 4.8], dtype=np.float64),
        candidate_union_red_cost=np.array([2.0, 2.0, 1.5], dtype=np.float64),
        candidate_red_stopping_margin_cost=np.array(
            [1.0, 1.0, 1.0], dtype=np.float64
        ),
        candidate_dp_prior_jerk_excess_cost=np.array(
            [1.0, 0.8, 0.7], dtype=np.float64
        ),
        candidate_horizon_lateral_acceleration_cost=np.array(
            [1.0, 0.9, 0.95], dtype=np.float64
        ),
        candidate_target_speed_mps=np.array([4.0, 3.99, 3.99], dtype=np.float64),
        perfect_tracker_open_loop=_traffic_light_hybrid_rollout(),
    )

    assert selected == 1
    assert stats["changed"] is True
    assert stats["opportunity"] is True
    assert stats["selected_index"] == 1
    assert stats["admissible_indices"] == [1]
    assert stats["future_outcome_leakage"] is False
    assert stats["classical_benders_claim"] is False
    assert stats["losses"]["first_step_loss_m"] == pytest.approx(0.04)
    assert stats["losses"]["h10_distance_loss_m"] == pytest.approx(0.03)
    assert stats["delta"]["raw_jerk"] == pytest.approx(-0.2)


def test_traffic_light_hybrid_postselection_is_traffic_light_gated() -> None:
    selected, stats = _apply_traffic_light_hybrid_postselection(
        _traffic_light_hybrid_base_selection(),
        traffic_lights_enabled=False,
        mode="step_h10_guard_005",
        candidate_step_reach=np.array([1.0, 0.96, 0.96], dtype=np.float64),
        candidate_progress=np.array([5.0, 4.97, 4.8], dtype=np.float64),
        candidate_union_red_cost=np.array([2.0, 2.0, 1.5], dtype=np.float64),
        candidate_red_stopping_margin_cost=np.ones(3, dtype=np.float64),
        candidate_dp_prior_jerk_excess_cost=np.array(
            [1.0, 0.8, 0.7], dtype=np.float64
        ),
        candidate_horizon_lateral_acceleration_cost=np.array(
            [1.0, 0.9, 0.95], dtype=np.float64
        ),
        candidate_target_speed_mps=np.array([4.0, 3.99, 3.99], dtype=np.float64),
        perfect_tracker_open_loop=_traffic_light_hybrid_rollout(),
    )

    assert selected == 0
    assert stats["changed"] is False
    assert stats["reason"] == "traffic_lights_disabled"


def test_traffic_light_hybrid_postselection_requires_strict_raw_jerk() -> None:
    selected, stats = _apply_traffic_light_hybrid_postselection(
        _traffic_light_hybrid_base_selection(),
        traffic_lights_enabled=True,
        mode="step_h10_guard_005",
        candidate_step_reach=np.array([1.0, 0.96, 0.96], dtype=np.float64),
        candidate_progress=np.array([5.0, 4.97, 4.8], dtype=np.float64),
        candidate_union_red_cost=np.array([2.0, 2.0, 1.5], dtype=np.float64),
        candidate_red_stopping_margin_cost=np.ones(3, dtype=np.float64),
        candidate_dp_prior_jerk_excess_cost=np.array(
            [1.0, 1.0, 0.7], dtype=np.float64
        ),
        candidate_horizon_lateral_acceleration_cost=np.array(
            [1.0, 0.9, 0.95], dtype=np.float64
        ),
        candidate_target_speed_mps=np.array([4.0, 3.99, 3.99], dtype=np.float64),
        perfect_tracker_open_loop=_traffic_light_hybrid_rollout(),
    )

    assert selected == 0
    assert stats["changed"] is False
    assert stats["reason"] == "no_admissible_traffic_light_hybrid_candidate"


def test_traffic_light_hybrid_h3_mode_uses_h3_budget() -> None:
    selected, stats = _apply_traffic_light_hybrid_postselection(
        _traffic_light_hybrid_base_selection(),
        traffic_lights_enabled=True,
        mode="h3_h10_guard_005",
        candidate_step_reach=np.array([1.0, 0.5, 0.96], dtype=np.float64),
        candidate_progress=np.array([5.0, 4.97, 4.8], dtype=np.float64),
        candidate_union_red_cost=np.array([2.0, 2.0, 1.5], dtype=np.float64),
        candidate_red_stopping_margin_cost=np.ones(3, dtype=np.float64),
        candidate_dp_prior_jerk_excess_cost=np.array(
            [1.0, 0.8, 0.7], dtype=np.float64
        ),
        candidate_horizon_lateral_acceleration_cost=np.array(
            [1.0, 0.9, 0.95], dtype=np.float64
        ),
        candidate_target_speed_mps=np.array([4.0, 3.99, 3.99], dtype=np.float64),
        perfect_tracker_open_loop=_traffic_light_hybrid_rollout(),
    )

    assert selected == 1
    assert stats["changed"] is True
    assert "first_step_loss_m" not in stats["losses"]
    assert stats["losses"]["h3_distance_loss_m"] == pytest.approx(0.05)


def test_underprogress_relaxation_selects_only_soft_blocked_lower_red() -> None:
    candidates = np.zeros((3, 4, 2), dtype=np.float64)
    selection = CAMPSelectionResult(
        selected_index=0,
        selected_trajectory=candidates[0].copy(),
        atoms=np.ones((3, 2), dtype=np.float64),
        normalized_atoms=np.ones((3, 2), dtype=np.float64),
        feasible_mask=np.array([True, False, False]),
        infeasibility_reasons=((), ("dp_underprogress",), ("dp_kinematic",)),
        scores=np.array([0.0, 0.4, 0.1], dtype=np.float64),
        weights=np.array([0.5, 0.5], dtype=np.float64),
        selection_scores=np.array([0.0, np.inf, np.inf], dtype=np.float64),
        selection_weights=np.array([0.5, 0.5], dtype=np.float64),
        selection_normalized_atoms=np.ones((3, 2), dtype=np.float64),
        used_fallback=False,
        timings_ms={},
    )
    rollout = {
        "horizons": {
            "3": {
                "distance_m": np.array([1.0, 0.95, 1.0], dtype=np.float64),
                "max_lateral_acceleration_mps2": np.array(
                    [0.1, 0.2, 0.1], dtype=np.float64
                ),
            }
        }
    }

    relaxed, stats = _apply_underprogress_relaxation_override(
        selection,
        candidates,
        candidate_progress=np.array([5.0, 4.2, 4.9], dtype=np.float64),
        candidate_union_red_cost=np.array([10.0, 0.0, 0.0], dtype=np.float64),
        candidate_red_stopping_margin_cost=np.array(
            [5.0, 1.0, 1.0], dtype=np.float64
        ),
        perfect_tracker_open_loop=rollout,
        progress_loss_budget_m=1.0,
        h3_distance_loss_budget_m=0.1,
        lateral_limit_mps2=2.0,
    )

    assert stats["changed"] is True
    assert stats["selected_index"] == 1
    assert relaxed.selected_index == 1
    assert relaxed.feasible_mask.tolist() == [True, True, False]
    assert relaxed.infeasibility_reasons == ((), (), ("dp_kinematic",))
    assert relaxed.selection_scores[:2].tolist() == pytest.approx([0.0, 0.4])
    assert np.isinf(relaxed.selection_scores[2])


def test_underprogress_relaxation_accepts_nested_integer_horizon_key() -> None:
    candidates = np.zeros((2, 4, 2), dtype=np.float64)
    selection = CAMPSelectionResult(
        selected_index=0,
        selected_trajectory=candidates[0].copy(),
        atoms=np.ones((2, 2), dtype=np.float64),
        normalized_atoms=np.ones((2, 2), dtype=np.float64),
        feasible_mask=np.array([True, False]),
        infeasibility_reasons=((), ("dp_underprogress",)),
        scores=np.array([0.0, 0.1], dtype=np.float64),
        weights=np.array([0.5, 0.5], dtype=np.float64),
        selection_scores=np.array([0.0, np.inf], dtype=np.float64),
        selection_weights=np.array([0.5, 0.5], dtype=np.float64),
        selection_normalized_atoms=np.ones((2, 2), dtype=np.float64),
        used_fallback=False,
        timings_ms={},
    )
    rollout = {
        "horizons": {
            3: {
                "distance_m": np.array([1.0, 0.98], dtype=np.float64),
                "max_lateral_acceleration_mps2": np.array(
                    [0.1, 0.1], dtype=np.float64
                ),
            }
        }
    }

    relaxed, stats = _apply_underprogress_relaxation_override(
        selection,
        candidates,
        candidate_progress=np.array([5.0, 4.9], dtype=np.float64),
        candidate_union_red_cost=np.array([10.0, 0.0], dtype=np.float64),
        candidate_red_stopping_margin_cost=np.array([5.0, 1.0], dtype=np.float64),
        perfect_tracker_open_loop=rollout,
        progress_loss_budget_m=1.0,
        h3_distance_loss_budget_m=0.1,
        lateral_limit_mps2=2.0,
    )

    assert stats["changed"] is True
    assert relaxed.selected_index == 1


def test_underprogress_relaxation_accepts_legacy_top_level_horizon_key() -> None:
    candidates = np.zeros((2, 4, 2), dtype=np.float64)
    selection = CAMPSelectionResult(
        selected_index=0,
        selected_trajectory=candidates[0].copy(),
        atoms=np.ones((2, 2), dtype=np.float64),
        normalized_atoms=np.ones((2, 2), dtype=np.float64),
        feasible_mask=np.array([True, False]),
        infeasibility_reasons=((), ("dp_underprogress",)),
        scores=np.array([0.0, 0.1], dtype=np.float64),
        weights=np.array([0.5, 0.5], dtype=np.float64),
        selection_scores=np.array([0.0, np.inf], dtype=np.float64),
        selection_weights=np.array([0.5, 0.5], dtype=np.float64),
        selection_normalized_atoms=np.ones((2, 2), dtype=np.float64),
        used_fallback=False,
        timings_ms={},
    )
    rollout = {
        "3": {
            "distance_m": np.array([1.0, 0.95], dtype=np.float64),
            "max_lateral_acceleration_mps2": np.array(
                [0.1, 0.2], dtype=np.float64
            ),
        }
    }

    relaxed, stats = _apply_underprogress_relaxation_override(
        selection,
        candidates,
        candidate_progress=np.array([5.0, 4.9], dtype=np.float64),
        candidate_union_red_cost=np.array([10.0, 0.0], dtype=np.float64),
        candidate_red_stopping_margin_cost=np.array([5.0, 1.0], dtype=np.float64),
        perfect_tracker_open_loop=rollout,
        progress_loss_budget_m=1.0,
        h3_distance_loss_budget_m=0.1,
        lateral_limit_mps2=2.0,
    )

    assert stats["changed"] is True
    assert stats["selected_index"] == 1
    assert relaxed.selected_index == 1


def test_underprogress_relaxation_keeps_hard_blocked_candidates_infeasible() -> None:
    candidates = np.zeros((2, 4, 2), dtype=np.float64)
    selection = CAMPSelectionResult(
        selected_index=0,
        selected_trajectory=candidates[0].copy(),
        atoms=np.ones((2, 2), dtype=np.float64),
        normalized_atoms=np.ones((2, 2), dtype=np.float64),
        feasible_mask=np.array([True, False]),
        infeasibility_reasons=((), ("dp_underprogress", "dynamic_obb_collision")),
        scores=np.array([0.0, 0.1], dtype=np.float64),
        weights=np.array([0.5, 0.5], dtype=np.float64),
        selection_scores=np.array([0.0, np.inf], dtype=np.float64),
        selection_weights=np.array([0.5, 0.5], dtype=np.float64),
        selection_normalized_atoms=np.ones((2, 2), dtype=np.float64),
        used_fallback=False,
        timings_ms={},
    )
    rollout = {
        3: {
            "distance_m": np.array([1.0, 1.0], dtype=np.float64),
            "max_lateral_acceleration_mps2": np.array([0.1, 0.1], dtype=np.float64),
        }
    }

    relaxed, stats = _apply_underprogress_relaxation_override(
        selection,
        candidates,
        candidate_progress=np.array([5.0, 4.9], dtype=np.float64),
        candidate_union_red_cost=np.array([10.0, 0.0], dtype=np.float64),
        candidate_red_stopping_margin_cost=np.array([5.0, 1.0], dtype=np.float64),
        perfect_tracker_open_loop=rollout,
        progress_loss_budget_m=1.0,
        h3_distance_loss_budget_m=0.1,
        lateral_limit_mps2=2.0,
    )

    assert stats["changed"] is False
    assert stats["reason"] == "no_underprogress_relaxed_candidate"
    assert relaxed is selection


def test_dp_reward_feasibility_applies_candidate0_progress_guard() -> None:
    rewards = [
        {"progress": 10.0, "red_light": 0.0},
        {"progress": 9.8, "red_light": 0.0},
        {"progress": 9.0, "red_light": 0.0},
    ]

    feasible, reasons = _candidate_feasibility_from_rewards(
        rewards,
        min_progress_ratio=0.0,
        min_candidate0_progress_ratio=0.95,
    )

    assert feasible.tolist() == [True, True, False]
    assert reasons == ((), (), ("dp_candidate0_underprogress",))


def test_candidate0_route_progress_guard_uses_route_projection() -> None:
    route = np.array([[0.0, 0.0], [20.0, 0.0]], dtype=np.float64)
    candidates = np.array(
        [
            [[0.0, 0.0], [10.0, 0.0]],
            [[0.0, 0.0], [9.9, 0.5]],
            [[0.0, 0.0], [9.0, 0.0]],
        ],
        dtype=np.float64,
    )

    progress = _candidate_route_progress(candidates, route)
    feasible, reasons = _apply_candidate0_route_progress_guard(
        np.ones(3, dtype=bool),
        ((), (), ()),
        progress,
        min_candidate0_route_progress_ratio=0.98,
    )

    assert progress is not None
    assert progress.tolist() == pytest.approx([10.0, 9.9, 9.0])
    assert feasible.tolist() == [True, True, False]
    assert reasons == ((), (), ("route_candidate0_underprogress",))


def test_candidate0_step_reach_guard_matches_perfect_tracker_speed_target() -> None:
    candidates = np.array(
        [
            [[1.0, 0.0], [2.0, 0.0]],
            [[0.99, 0.1], [2.0, 0.0]],
            [[0.8, 0.0], [2.0, 0.0]],
        ],
        dtype=np.float64,
    )

    reach = _candidate_step_reach(candidates)
    feasible, reasons, relaxed = _apply_candidate0_step_reach_guard(
        np.ones(3, dtype=bool),
        ((), (), ()),
        reach,
        min_candidate0_step_reach_ratio=0.98,
    )

    assert reach.tolist() == pytest.approx([1.0, 0.995037, 0.8])
    assert feasible.tolist() == [True, True, False]
    assert reasons == ((), (), ("candidate0_step_reach_underprogress",))
    assert relaxed is False


def test_perfect_tracker_command_diagnostics_reproduce_normal_command() -> None:
    candidates = np.array(
        [
            [
                [0.2, 0.0, 1.0, 0.0],
                [0.4, 0.0, 1.0, 0.0],
                [0.6, 0.0, 1.0, 0.0],
            ],
            [
                [0.3, 0.0, np.cos(0.2), np.sin(0.2)],
                [0.5, 0.0, 1.0, 0.0],
                [0.7, 0.0, 1.0, 0.0],
            ],
        ],
        dtype=np.float64,
    )

    diagnostics = compute_perfect_tracker_command_diagnostics(
        candidates,
        dt=0.1,
        current_speed_mps=2.0,
        current_longitudinal_acceleration_mps2=1.0,
    )

    assert diagnostics["restart_push"].tolist() == [False, False]
    assert diagnostics["target_speed_mps"].tolist() == pytest.approx([2.0, 3.0])
    assert diagnostics["acceleration_mps2"].tolist() == pytest.approx([0.0, 10.0])
    assert diagnostics["jerk_magnitude_mps3"].tolist() == pytest.approx(
        [10.0, 90.0]
    )
    assert diagnostics["yaw_rate_magnitude_rps"].tolist() == pytest.approx(
        [0.0, 2.0]
    )
    assert diagnostics[
        "lateral_acceleration_magnitude_mps2"
    ].tolist() == pytest.approx([0.0, 6.0])


def test_tracker_reference_candidates_apply_replay_savgol_preprocessing() -> None:
    from scipy.signal import savgol_filter

    rng = np.random.default_rng(4)
    candidates = rng.normal(size=(2, 15, 4))
    heading_norm = np.linalg.norm(candidates[:, :, 2:4], axis=2)
    candidates[:, :, 2:4] /= heading_norm[:, :, np.newaxis]
    config = types.SimpleNamespace(
        sg_smooth_enabled=True,
        sg_filter_window=11,
        sg_filter_order=3,
    )

    prepared = _prepare_perfect_tracker_reference_candidates(
        candidates,
        config,
    )
    expected = candidates.copy()
    for candidate_idx, candidate in enumerate(candidates):
        for column in range(4):
            expected[candidate_idx, :, column] = savgol_filter(
                candidate[:, column],
                11,
                3,
            )
    expected_heading_norm = np.linalg.norm(expected[:, :, 2:4], axis=2)
    expected[:, :, 2:4] /= expected_heading_norm[:, :, np.newaxis]

    np.testing.assert_allclose(prepared, expected, atol=1e-12, rtol=1e-12)
    assert not np.shares_memory(prepared, candidates)
    assert _perfect_tracker_candidate_preprocessing(config) == {
        "reference_implementation": (
            "rlvr.grpo_sft_trainer._smooth_trajectory"
        ),
        "shadow_implementation": (
            "scripts.integrations.run_diffusion_planner_camp_replay."
            "_prepare_perfect_tracker_reference_candidates"
        ),
        "application_stage": (
            "replay_after_predict_before_advance_scene_mpc"
        ),
        "savgol_enabled": True,
        "savgol_window": 11,
        "savgol_order": 3,
    }


def test_reward_scoring_candidates_match_previous_per_candidate_savgol() -> None:
    from scipy.signal import savgol_filter

    rng = np.random.default_rng(14)
    candidates = rng.normal(size=(3, 15, 4))
    heading_norm = np.linalg.norm(candidates[:, :, 2:4], axis=2)
    candidates[:, :, 2:4] /= heading_norm[:, :, np.newaxis]
    config = types.SimpleNamespace(
        sg_smooth_enabled=True,
        sg_filter_window=11,
        sg_filter_order=3,
    )

    expected = np.asarray(candidates, dtype=np.float32).copy()
    expected = np.stack(
        [
            savgol_filter(
                candidate,
                config.sg_filter_window,
                config.sg_filter_order,
                axis=0,
            )
            for candidate in expected
        ]
    )
    expected_heading_norm = np.linalg.norm(expected[:, :, 2:4], axis=2)
    expected[:, :, 2:4] /= np.clip(
        expected_heading_norm,
        1e-6,
        None,
    )[:, :, np.newaxis]

    actual = _prepare_reward_scoring_candidates(candidates, config)

    assert actual.dtype == np.float32
    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=0.0)


def test_reward_scoring_candidates_preserve_disabled_copy_semantics() -> None:
    candidates = np.zeros((1, 3, 4), dtype=np.float64)
    config = types.SimpleNamespace(sg_smooth_enabled=False)

    actual = _prepare_reward_scoring_candidates(candidates, config)

    assert actual.dtype == np.float32
    assert not np.shares_memory(actual, candidates)
    np.testing.assert_array_equal(actual, candidates.astype(np.float32))


def test_tracker_reference_candidates_preserve_disabled_preprocessing() -> None:
    candidates = np.zeros((1, 3, 4), dtype=np.float64)
    config = types.SimpleNamespace(sg_smooth_enabled=False)

    prepared = _prepare_perfect_tracker_reference_candidates(
        candidates,
        config,
    )

    assert prepared is candidates
    assert _perfect_tracker_candidate_preprocessing(config) == {
        "reference_implementation": (
            "rlvr.grpo_sft_trainer._smooth_trajectory"
        ),
        "shadow_implementation": (
            "scripts.integrations.run_diffusion_planner_camp_replay."
            "_prepare_perfect_tracker_reference_candidates"
        ),
        "application_stage": (
            "replay_after_predict_before_advance_scene_mpc"
        ),
        "savgol_enabled": False,
        "savgol_window": None,
        "savgol_order": None,
    }


def test_perfect_tracker_command_diagnostics_apply_postprocess_and_restart() -> None:
    candidates = np.array(
        [
            [
                [0.0, 0.0, 1.0, 0.0],
                [0.1, 0.0, 1.0, 0.0],
                [0.1, 0.0, 1.0, 0.0],
                [5.0, 0.0, 1.0, 0.0],
            ],
            [
                [3.0, 0.0, np.cos(3.5), np.sin(3.5)],
                [4.0, 0.0, 1.0, 0.0],
                [5.0, 0.0, 1.0, 0.0],
                [6.0, 0.0, 1.0, 0.0],
            ],
        ],
        dtype=np.float64,
    )

    diagnostics = compute_perfect_tracker_command_diagnostics(
        candidates,
        dt=0.1,
        current_speed_mps=0.0,
        current_longitudinal_acceleration_mps2=0.0,
        velocity_smooth_window=1,
    )

    np.testing.assert_allclose(
        diagnostics["postprocessed_tail_reference_xy"][0],
        [0.1, 0.0],
    )
    assert diagnostics["tail_average_speed_mps"][0] == pytest.approx(0.25)
    assert diagnostics["restart_push"].tolist() == [False, True]
    assert diagnostics["target_speed_mps"].tolist() == pytest.approx([0.0, 20.0])
    assert diagnostics["yaw_rate_magnitude_rps"][1] == pytest.approx(
        abs(np.arctan2(np.sin(3.5), np.cos(3.5))) / 0.1
    )


def test_perfect_tracker_open_loop_rollout_matches_fixed_reference_dynamics() -> None:
    reference = np.array(
        [[[1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [3.0, 0.0, 0.0]]],
        dtype=np.float64,
    )

    diagnostics = compute_perfect_tracker_open_loop_rollout_diagnostics(
        reference,
        postprocessed_tail_reference_xy=np.array([[3.0, 0.0]]),
        full_horizon_steps=3,
        dt=1.0,
        current_speed_mps=0.0,
        current_acceleration_ego_xy=np.zeros(2),
        horizons=(1, 3),
    )

    np.testing.assert_allclose(
        diagnostics["target_speed_mps"],
        [[1.0, 1.0, 1.0]],
    )
    assert diagnostics["restart_push"].tolist() == [[True, False, False]]
    horizon3 = diagnostics["horizons"]["3"]
    assert horizon3["distance_m"][0] == pytest.approx(3.0)
    assert horizon3["mean_vector_jerk_mps3"][0] == pytest.approx(2.0 / 3.0)
    assert horizon3["max_vector_jerk_mps3"][0] == pytest.approx(1.0)
    assert horizon3["mean_lateral_acceleration_mps2"][0] == 0.0


def test_perfect_tracker_open_loop_rollout_uses_vector_jerk_and_heading_snap() -> None:
    reference = np.array(
        [[[1.0, 0.0, np.pi / 2], [1.0, 1.0, np.pi / 2]]],
        dtype=np.float64,
    )

    diagnostics = compute_perfect_tracker_open_loop_rollout_diagnostics(
        reference,
        postprocessed_tail_reference_xy=np.array([[1.0, 1.0]]),
        full_horizon_steps=2,
        dt=1.0,
        current_speed_mps=1.0,
        current_acceleration_ego_xy=np.zeros(2),
        horizons=(1, 2),
    )

    horizon1 = diagnostics["horizons"]["1"]
    assert horizon1["mean_vector_jerk_mps3"][0] == pytest.approx(np.sqrt(2.0))
    assert horizon1["mean_lateral_acceleration_mps2"][0] == pytest.approx(
        np.pi / 2
    )


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"dt": 0.0}, "dt must be positive"),
        ({"current_speed_mps": -1.0}, "must be nonnegative"),
        ({"velocity_smooth_window": 0}, "positive integer"),
    ],
)
def test_perfect_tracker_command_diagnostics_fail_closed(kwargs, error) -> None:
    arguments = {
        "dt": 0.1,
        "current_speed_mps": 0.0,
        "current_longitudinal_acceleration_mps2": 0.0,
    }
    arguments.update(kwargs)
    with pytest.raises(ValueError, match=error):
        compute_perfect_tracker_command_diagnostics(
            np.zeros((1, 2, 4), dtype=np.float64),
            **arguments,
        )


def test_perfect_tracker_open_loop_rollout_rejects_uncovered_horizon() -> None:
    with pytest.raises(ValueError, match="within the reference prefix"):
        compute_perfect_tracker_open_loop_rollout_diagnostics(
            np.zeros((1, 2, 3), dtype=np.float64),
            postprocessed_tail_reference_xy=np.zeros((1, 2)),
            full_horizon_steps=2,
            dt=0.1,
            current_speed_mps=0.0,
            current_acceleration_ego_xy=np.zeros(2),
            horizons=(3,),
        )


def test_tracker_command_postselection_chooses_jointly_dominating_candidate() -> None:
    selected, stats = select_perfect_tracker_command_dominating_candidate(
        baseline_selected_index=0,
        feasible_mask=np.array([True, True, True]),
        selection_scores=np.array([0.0, 0.2, 0.1]),
        candidate_progress=np.array([5.0, 5.1, 5.2]),
        candidate_planned_red_light_cost=np.array([0.0, 0.0, 0.0]),
        candidate_target_speed_mps=np.array([4.0, 4.1, 4.2]),
        candidate_jerk_magnitude_mps3=np.array([10.0, 8.0, 7.0]),
        candidate_lateral_acceleration_magnitude_mps2=np.array([0.5, 0.4, 0.6]),
    )

    assert selected == 1
    assert stats == {
        "base_feasible_count": 3,
        "admissible_count": 3,
        "weakly_dominating_count": 2,
        "strict_improvement_count": 1,
        "baseline_selected_index": 0,
        "selected_index": 1,
        "changed": True,
    }


def test_tracker_command_postselection_preserves_progress_and_fallback() -> None:
    kwargs = {
        "baseline_selected_index": 0,
        "selection_scores": np.array([0.0, 0.2]),
        "candidate_progress": np.array([5.0, 4.9]),
        "candidate_planned_red_light_cost": np.array([0.0, 0.0]),
        "candidate_target_speed_mps": np.array([4.0, 4.1]),
        "candidate_jerk_magnitude_mps3": np.array([10.0, 8.0]),
        "candidate_lateral_acceleration_magnitude_mps2": np.array([0.5, 0.4]),
    }

    selected, stats = select_perfect_tracker_command_dominating_candidate(
        feasible_mask=np.array([True, True]),
        **kwargs,
    )
    assert selected == 0
    assert stats["admissible_count"] == 1
    assert stats["changed"] is False

    fallback_selected, fallback_stats = (
        select_perfect_tracker_command_dominating_candidate(
            feasible_mask=np.array([False, False]),
            **kwargs,
        )
    )
    assert fallback_selected == 0
    assert fallback_stats["base_feasible_count"] == 0
    assert fallback_stats["changed"] is False


def test_tracker_command_postselection_uses_deterministic_tie_break() -> None:
    selected, _ = select_perfect_tracker_command_dominating_candidate(
        baseline_selected_index=0,
        feasible_mask=np.array([True, True, True]),
        selection_scores=np.array([0.0, 0.2, 0.2]),
        candidate_progress=np.array([5.0, 5.0, 5.0]),
        candidate_planned_red_light_cost=np.zeros(3),
        candidate_target_speed_mps=np.array([4.0, 4.0, 4.0]),
        candidate_jerk_magnitude_mps3=np.array([10.0, 8.0, 8.0]),
        candidate_lateral_acceleration_magnitude_mps2=np.array([0.5, 0.4, 0.4]),
    )

    assert selected == 1


def test_candidate0_step_reach_guard_can_preserve_existing_feasible_set() -> None:
    reach = np.array([1.0, 0.8, 0.7], dtype=np.float64)

    feasible, reasons, relaxed = _apply_candidate0_step_reach_guard(
        np.array([False, True, True], dtype=bool),
        (("dp_reward_underprogress",), (), ()),
        reach,
        min_candidate0_step_reach_ratio=0.99,
        preserve_any_feasible=True,
    )

    assert feasible.tolist() == [False, True, True]
    assert reasons == (("dp_reward_underprogress",), (), ())
    assert relaxed is True


def test_lexicographic_admissible_filter_is_nonempty_and_fail_closed() -> None:
    feasible, reasons, stage_counts = _apply_lexicographic_admissible_filter(
        np.array([True, True, True, False], dtype=bool),
        ((), (), (), ("dp_lane_crossing",)),
        candidate_progress=np.array([5.0, 6.0, 5.5, 9.0]),
        candidate_planned_red_light_cost=np.array([0.0, 1.0, 0.0, 0.0]),
        candidate_dp_prior_jerk_excess_cost=np.array([0.8, 0.0, 0.2, 0.0]),
        candidate_horizon_lateral_acceleration_cost=np.array(
            [0.20, 0.10, 0.15, 0.0]
        ),
        progress_epsilon_m=2.0,
        red_epsilon=0.0,
        jerk_epsilon=1.0,
        lateral_epsilon=0.05,
    )

    assert feasible.tolist() == [True, False, True, False]
    assert reasons == (
        (),
        ("lexicographic_planned_red",),
        (),
        ("dp_lane_crossing",),
    )
    assert stage_counts == {
        "base": 3,
        "progress": 3,
        "planned_red": 2,
        "jerk": 2,
        "lateral": 2,
    }


def test_lexicographic_admissible_filter_does_not_create_fallback() -> None:
    feasible, reasons, stage_counts = _apply_lexicographic_admissible_filter(
        np.array([False, True], dtype=bool),
        (("dp_collision",), ()),
        candidate_progress=np.array([10.0, 1.0]),
        candidate_planned_red_light_cost=np.array([0.0, 2.0]),
        candidate_dp_prior_jerk_excess_cost=np.array([0.0, 3.0]),
        candidate_horizon_lateral_acceleration_cost=np.array([0.0, 4.0]),
        progress_epsilon_m=0.0,
        red_epsilon=0.0,
        jerk_epsilon=0.0,
        lateral_epsilon=0.0,
    )

    assert feasible.tolist() == [False, True]
    assert reasons == (("dp_collision",), ())
    assert stage_counts == {
        "base": 1,
        "progress": 1,
        "planned_red": 1,
        "jerk": 1,
        "lateral": 1,
    }


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


def test_selector_obb_broad_phase_skips_distant_sat_checks(monkeypatch) -> None:
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [20.0, 0.0]]),
        lane_half_width=20.0,
        speed_limit=50.0,
        desired_speed=5.0,
        safety_radius=0.1,
    )
    x = np.linspace(0.5, 4.0, 8)
    candidate = np.column_stack(
        [x, np.zeros_like(x), np.ones_like(x), np.zeros_like(x)]
    )
    obstacles = np.zeros((1, 1, 8, 6), dtype=np.float64)
    obstacles[0, 0, :, 0] = 100.0
    obstacles[0, 0, :, 1] = 100.0
    obstacles[0, 0, :, 3] = 4.5
    obstacles[0, 0, :, 4] = 1.9
    obstacles[0, 0, :, 5] = 2.9

    def fail_sat(*args, **kwargs):
        raise AssertionError("Distant OBBs must not reach exact SAT.")

    monkeypatch.setattr(diffusion_planner_module, "_obb_collides", fail_sat)
    selector = CAMPSelector(
        atom_scales=np.ones(9),
        static_weights=np.ones(9),
        mode="static",
    )

    result = selector.select(
        candidate[np.newaxis],
        context,
        candidate_obstacles=obstacles,
        ego_length=4.5,
        ego_width=1.9,
        ego_wheelbase=2.9,
    )

    assert result.feasible_mask.tolist() == [True]


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
