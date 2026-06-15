from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.atoms.driver_atoms import DriverAtomContext, compute_atom_bank_vector
from camp_core.integrations.diffusion_planner import CAMPSelectionResult
from scripts.integrations.benchmark_diffusion_planner_camp_components import (
    _exact_centerline_slice,
    _exact_centerline_slice_kdtree,
    _max_abs_numeric_difference,
    _profile_atom_bank_vector,
)
from scripts.integrations.run_diffusion_planner_camp_replay import (
    _parse_step_list,
    _write_microbenchmark_snapshot,
)


def test_profiled_atom_vector_matches_production_definition() -> None:
    trajectory = np.array(
        [[0.0, 0.0], [0.5, 0.1], [1.1, 0.2], [1.8, 0.2], [2.6, 0.3]],
        dtype=np.float64,
    )
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array(
            [[0.0, 0.0], [1.5, 0.0], [3.0, 0.5]],
            dtype=np.float64,
        ),
        static_obstacles=np.array([[2.4, 0.2], [10.0, 10.0]], dtype=np.float64),
        dynamic_obstacles={
            0: np.array(
                [[3.0, 0.0], [2.5, 0.0], [2.5, 0.0], [3.5, 0.0], [4.0, 0.0]],
                dtype=np.float64,
            )
        },
        safety_radius=1.0,
        clearance_soft_margin=1.0,
        speed_limit=7.0,
        lane_half_width=0.5,
    )

    expected = compute_atom_bank_vector(context, trajectory)
    actual, phases = _profile_atom_bank_vector(context, trajectory)

    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)
    assert {
        "kinematics",
        "jerk_atoms",
        "acceleration_atom",
        "speed_atoms",
        "centerline_setup",
        "centerline_projection",
        "lane_hinge",
        "dynamic_clearance",
        "static_clearance",
        "clearance_hinge",
    } == set(phases)
    assert all(value >= 0.0 for value in phases.values())


def test_parse_microbenchmark_steps_rejects_invalid_lists() -> None:
    assert _parse_step_list("10,20,30,39") == (10, 20, 30, 39)
    with pytest.raises(Exception, match="must not be empty"):
        _parse_step_list("")
    with pytest.raises(Exception, match="nonnegative"):
        _parse_step_list("-1,2")
    with pytest.raises(Exception, match="unique"):
        _parse_step_list("2,2")


def test_numeric_difference_handles_optional_reward_fields() -> None:
    first = [{"score": 1.0, "optional": None, "nested": [2.0, True]}]
    second = [{"score": 1.25, "optional": None, "nested": [2.0, True]}]
    assert _max_abs_numeric_difference(first, second) == pytest.approx(0.25)
    with pytest.raises(AssertionError, match="Optional values differ"):
        _max_abs_numeric_difference(None, 0.0)


def test_exact_centerline_slice_preserves_atom_projection() -> None:
    centerline = np.column_stack(
        (
            np.linspace(0.0, 100.0, 201),
            np.zeros(201),
        )
    )
    trajectory = np.column_stack(
        (
            np.linspace(0.0, 8.0, 80),
            np.full(80, 0.25),
        )
    )
    sliced, stats = _exact_centerline_slice(
        centerline,
        trajectory[np.newaxis],
    )
    assert stats["fail_closed"] is False
    assert stats["retained_segment_count"] < stats["original_segment_count"]

    full_context = DriverAtomContext(dt=0.1, lane_centerline=centerline)
    sliced_context = DriverAtomContext(dt=0.1, lane_centerline=sliced)
    np.testing.assert_allclose(
        compute_atom_bank_vector(sliced_context, trajectory),
        compute_atom_bank_vector(full_context, trajectory),
        rtol=1e-12,
        atol=1e-12,
    )
    kdtree_sliced, kdtree_stats = _exact_centerline_slice_kdtree(
        centerline,
        trajectory[np.newaxis],
    )
    assert kdtree_stats["fail_closed"] is False
    assert (
        kdtree_stats["retained_segment_count"]
        < kdtree_stats["original_segment_count"]
    )
    np.testing.assert_allclose(
        compute_atom_bank_vector(
            DriverAtomContext(dt=0.1, lane_centerline=kdtree_sliced),
            trajectory,
        ),
        compute_atom_bank_vector(full_context, trajectory),
        rtol=1e-12,
        atol=1e-12,
    )


def test_write_microbenchmark_snapshot_records_current_tick_inputs(tmp_path) -> None:
    candidates = np.zeros((2, 5, 4), dtype=np.float64)
    candidates[:, :, 2] = 1.0
    obstacles = np.zeros((2, 1, 5, 5), dtype=np.float64)
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.array([[0.0, 0.0], [5.0, 0.0]], dtype=np.float64),
        static_obstacles=np.array([[8.0, 0.0]], dtype=np.float64),
        speed_limit=10.0,
    )
    atoms = np.zeros((2, 9), dtype=np.float64)
    selection = CAMPSelectionResult(
        selected_index=0,
        selected_trajectory=candidates[0],
        atoms=atoms,
        normalized_atoms=atoms,
        feasible_mask=np.array([True, False]),
        infeasibility_reasons=((), ("external_gate",)),
        scores=np.array([0.0, 1.0]),
        weights=np.full(9, 1.0 / 9.0),
        selection_scores=np.array([0.0, np.inf]),
        selection_weights=np.full(9, 1.0 / 9.0),
        selection_normalized_atoms=atoms,
        used_fallback=False,
        timings_ms={},
    )
    selector = SimpleNamespace(
        atom_scales=np.ones(9),
        atom_clip=10.0,
        fallback_mode="uniform",
    )

    class _TensorConverter:
        @staticmethod
        def dump_step_npz(*_args, **_kwargs):
            return {
                "lanes": np.zeros((2, 3, 4), dtype=np.float32),
                "goal_pose": np.zeros((1, 3), dtype=np.float32),
            }

    output = _write_microbenchmark_snapshot(
        output_dir=tmp_path,
        selection_step=10,
        normalized_inputs={"ego_current_state": np.zeros((1, 10))},
        tensor_converter_module=_TensorConverter,
        scene=object(),
        map_cache=object(),
        model_args=SimpleNamespace(future_len=5, predicted_neighbor_num=1),
        candidates=candidates,
        neighbor_predictions=np.zeros((2, 1, 5, 4)),
        candidate_obstacles=obstacles,
        context=context,
        selector=selector,
        selection=selection,
        scene_features=np.zeros(3),
        external_feasible_mask=np.array([True, False]),
        external_infeasibility_reasons=((), ("external_gate",)),
        candidate_progress=np.array([1.0, 0.5]),
        candidate_planned_red_light_cost=np.zeros(2),
        candidate_full_horizon_planned_red_light_cost=np.zeros(2),
        candidate_red_stopping_margin_cost=np.zeros(2),
        candidate_dp_prior_jerk_excess_cost=np.zeros(2),
        red_route_points=np.zeros((0, 2)),
        perfect_tracker_current_speed_mps=0.0,
        perfect_tracker_current_longitudinal_acceleration_mps2=0.0,
        perfect_tracker_current_acceleration_ego_xy=np.zeros(2),
        num_candidates=2,
        noise_scale=1.0,
        reference_blend_steps=None,
        reward_horizon_steps=5,
        outcome_horizon_steps=5,
        spawn_config=SimpleNamespace(
            sg_smooth_enabled=False,
            sg_filter_window=0,
            sg_filter_order=0,
        ),
    )

    with np.load(output, allow_pickle=False) as payload:
        metadata = json.loads(str(payload["metadata_json"].item()))
        assert metadata["selection_step"] == 10
        assert metadata["capture_has_no_selection_effect"] is True
        assert "model_input__ego_current_state" in payload
        assert "reward_input__lanes" in payload
