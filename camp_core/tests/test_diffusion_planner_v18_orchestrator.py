from __future__ import annotations

import argparse
import importlib
import json
import sqlite3

import numpy as np
import pytest

from camp_core.integrations import diffusion_planner_causal_atoms as causal_atoms
from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
)


def _orchestrator():
    try:
        return importlib.import_module(
            "scripts.integrations.run_diffusion_planner_dp_camp_v18"
        )
    except ModuleNotFoundError:
        pytest.fail("the thin v18 orchestrator is missing")


def _causal_input() -> dict[str, np.ndarray]:
    data = {
        key: np.zeros(shape, dtype=dtype)
        for key, (shape, dtype) in CAUSAL_DP_INPUT_SCHEMA.items()
    }
    data["neighbor_agents_past"][0, 0, 0] = 7.0
    return data


def _route_projection_fixture():
    candidates = np.zeros((8, 80, 4), dtype=np.float64)
    candidates[:, :, 2] = 1.0
    candidates[:, :40, 0] = np.linspace(0.25, 19.25, 40)
    candidates[:, 40:, 0] = np.linspace(20.25, 39.25, 40)
    route = np.zeros((25, 20, 33), dtype=np.float64)
    route[0, :, 0] = np.linspace(0.0, 19.5, 20)
    route[1, :, 0] = np.linspace(20.0, 39.5, 20)
    route[:2, :, 2] = 1.0
    route[0, :, 5] = 2.0
    route[0, :, 7] = -1.5
    route[1, :, 5] = 3.0
    route[1, :, 7] = -1.0
    route[:2, :, 13] = 1.0
    speed = np.zeros((25, 1), dtype=np.float64)
    speed[:2, 0] = [5.0, 12.0]
    has_speed = np.zeros((25, 1), dtype=bool)
    has_speed[:2, 0] = True
    return candidates, route, speed, has_speed


def test_route_projection_uses_per_segment_speed_and_side_boundaries() -> None:
    candidates, route, speed, has_speed = _route_projection_fixture()

    projection = causal_atoms.project_candidates_to_route(
        candidates,
        route,
        speed,
        has_speed,
    )

    assert projection["lateral_offset"].shape == (8, 80)
    np.testing.assert_allclose(projection["speed_limit"][:, 10], 5.0)
    np.testing.assert_allclose(projection["speed_limit"][:, 60], 12.0)
    np.testing.assert_allclose(projection["left_width"][:, 10], 2.0)
    np.testing.assert_allclose(projection["right_width"][:, 10], 1.5)
    np.testing.assert_allclose(projection["left_width"][:, 60], 3.0)
    np.testing.assert_allclose(projection["right_width"][:, 60], 1.0)
    assert np.all(projection["route_progress"] > 39.0)


def test_candidate_local_speed_rejects_only_candidates_using_unknown_segments() -> None:
    candidates, route, speed, has_speed = _route_projection_fixture()
    candidates[:4, :, 0] = np.linspace(0.25, 10.0, 80)
    candidates[4:, :, 0] = np.linspace(25.0, 35.0, 80)
    has_speed[1, 0] = False
    speed[1, 0] = 0.0

    with pytest.raises(ValueError, match="route slot 1"):
        causal_atoms.project_candidates_to_route(candidates, route, speed, has_speed)

    projection = causal_atoms.project_candidates_to_route(
        candidates,
        route,
        speed,
        has_speed,
        speed_source_policy=causal_atoms.CANDIDATE_LOCAL_EXACT_SPEED,
    )

    expected = np.array([True] * 4 + [False] * 4)
    np.testing.assert_array_equal(
        projection["route_speed_source_eligible_mask"], expected
    )
    assert projection["route_speed_source_eligible_mask"].dtype == np.bool_
    assert np.isfinite(projection["speed_limit"][expected]).all()
    assert np.isnan(projection["speed_limit"][~expected]).all()


def test_candidate_local_speed_never_uses_zero_as_a_speed_source() -> None:
    candidates, route, speed, has_speed = _route_projection_fixture()
    has_speed[:] = False
    speed[:] = 0.0

    projection = causal_atoms.project_candidates_to_route(
        candidates,
        route,
        speed,
        has_speed,
        speed_source_policy=causal_atoms.CANDIDATE_LOCAL_EXACT_SPEED,
    )

    assert not projection["route_speed_source_eligible_mask"].any()


def test_route_projection_accepts_one_candidate_for_baseline_source_check() -> None:
    candidates, route, speed, has_speed = _route_projection_fixture()

    projection = causal_atoms.project_candidates_to_route(
        candidates[:1],
        route,
        speed,
        has_speed,
        speed_source_policy=causal_atoms.CANDIDATE_LOCAL_EXACT_SPEED,
    )

    assert projection["route_speed_source_eligible_mask"].shape == (1,)
    assert projection["route_speed_source_eligible_mask"].all()


def test_route_projection_rejects_unknown_speed_source_policy() -> None:
    candidates, route, speed, has_speed = _route_projection_fixture()

    with pytest.raises(ValueError, match="unsupported route speed-source policy"):
        causal_atoms.project_candidates_to_route(
            candidates,
            route,
            speed,
            has_speed,
            speed_source_policy="invented_speed_fallback",
        )


def test_route_projection_is_global_se2_invariant() -> None:
    candidates, route, speed, has_speed = _route_projection_fixture()
    expected = causal_atoms.project_candidates_to_route(
        candidates,
        route,
        speed,
        has_speed,
    )
    angle = 0.8
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]
    )
    translation = np.array([100.0, -45.0])
    moved_candidates = candidates.copy()
    moved_candidates[..., :2] = candidates[..., :2] @ rotation.T + translation
    moved_candidates[..., 2:4] = candidates[..., 2:4] @ rotation.T
    moved_route = route.copy()
    valid = moved_route[..., 13] > 0.5
    moved_route[..., :2][valid] = route[..., :2][valid] @ rotation.T + translation
    for start in (2, 4, 6):
        moved_route[..., start : start + 2][valid] = (
            route[..., start : start + 2][valid] @ rotation.T
        )

    actual = causal_atoms.project_candidates_to_route(
        moved_candidates,
        moved_route,
        speed,
        has_speed,
    )

    for name in (
        "lateral_offset",
        "left_width",
        "right_width",
        "speed_limit",
        "route_progress",
    ):
        np.testing.assert_allclose(actual[name], expected[name], atol=1e-10)


def _observable_obb_fixture():
    candidates = np.zeros((8, 80, 4), dtype=np.float64)
    candidates[:, :, 0] = np.linspace(0.0, 10.0, 80)
    candidates[:, :, 1] = np.arange(8, dtype=np.float64)[:, None] * 5.0
    candidates[:, :, 2] = 1.0
    neighbors = np.zeros((8, 32, 80, 4), dtype=np.float64)
    neighbors[..., 0] = 100.0
    neighbors[..., 1] = 100.0
    neighbors[..., 2] = 1.0
    neighbors[0, 0, :, :2] = candidates[0, :, :2]
    valid = np.zeros(32, dtype=bool)
    valid[0] = True
    history = np.zeros((32, 31, 11), dtype=np.float64)
    history[0, -1, 6:8] = [2.0, 4.0]
    static = np.zeros((5, 10), dtype=np.float64)
    static[0, :6] = [5.0, 5.0, 1.0, 0.0, 2.0, 4.0]
    projection = {
        "lateral_offset": np.zeros((8, 80), dtype=np.float64),
        "left_width": np.full((8, 80), 50.0, dtype=np.float64),
        "right_width": np.full((8, 80), 50.0, dtype=np.float64),
    }
    return candidates, neighbors, valid, history, static, projection


def test_observable_obb_masks_dynamic_static_and_padding() -> None:
    module = _orchestrator()
    candidates, neighbors, valid, history, static, projection = (
        _observable_obb_fixture()
    )

    obbs = causal_atoms.build_observable_obbs(
        neighbors,
        valid,
        history,
        static,
    )
    result = causal_atoms.observable_feasibility(
        candidates,
        np.ones(8, dtype=bool),
        projection,
        obbs,
        np.array([2.925, 4.5, 1.9]),
    )

    assert obbs.shape == (8, 37, 80, 5)
    assert not obbs[:, 1:32].any()
    np.testing.assert_array_equal(
        result["physical_feasible_mask"],
        result["signal_mask"]
        & result["lane_feasible_mask"]
        & result["obb_collision_free_mask"],
    )
    np.testing.assert_array_equal(
        result["obb_collision_free_mask"],
        [False, False, True, True, True, True, True, True],
    )
    assert result["candidate_reasons"][0] == ("obb_collision",)
    assert result["candidate_reasons"][1] == ("obb_collision",)
    assert result["feasibility_scope"] == module.FEASIBILITY_SCOPE
    assert result["closed_loop_safety_claim"] is False


def test_observable_obb_accepts_nonunit_heading_but_rejects_zero() -> None:
    _candidates, neighbors, valid, history, static, _projection = (
        _observable_obb_fixture()
    )
    neighbors[:, 0, :, 2:4] = [0.01, 0.0]

    obbs = causal_atoms.build_observable_obbs(
        neighbors,
        valid,
        history,
        static,
    )

    np.testing.assert_allclose(obbs[:, 0, :, 2], 0.0)
    neighbors[0, 0, 10, 2:4] = 0.0
    with pytest.raises(ValueError, match="invalid heading"):
        causal_atoms.build_observable_obbs(
            neighbors,
            valid,
            history,
            static,
        )


def test_all_candidates_can_fail_obb_without_forcing_candidate_zero() -> None:
    candidates, neighbors, valid, history, static, projection = (
        _observable_obb_fixture()
    )
    for candidate_index in range(8):
        neighbors[candidate_index, 0, :, :2] = candidates[candidate_index, :, :2]
    obbs = causal_atoms.build_observable_obbs(
        neighbors,
        valid,
        history,
        static,
    )

    result = causal_atoms.observable_feasibility(
        candidates,
        np.ones(8, dtype=bool),
        projection,
        obbs,
        np.array([2.925, 4.5, 1.9]),
    )

    assert not result["physical_feasible_mask"].any()
    assert not bool(result["physical_feasible_mask"][0])
    assert all(
        "obb_collision" in reasons
        for reasons in result["candidate_reasons"]
    )


def test_observable_obb_prunes_only_pairs_beyond_clearance_hinge(monkeypatch) -> None:
    candidates, neighbors, valid, history, static, projection = (
        _observable_obb_fixture()
    )
    neighbors[0, 0, :, :2] = [100.0, 100.0]
    static[:] = 0.0
    obbs = causal_atoms.build_observable_obbs(
        neighbors,
        valid,
        history,
        static,
    )
    calls = 0
    exact_distance = causal_atoms._obb_distance

    def counted_distance(*args):
        nonlocal calls
        calls += 1
        return exact_distance(*args)

    monkeypatch.setattr(causal_atoms, "_obb_distance", counted_distance)
    result = causal_atoms.observable_feasibility(
        candidates,
        np.ones(8, dtype=bool),
        projection,
        obbs,
        np.array([2.925, 4.5, 1.9]),
    )

    assert calls == 0
    np.testing.assert_allclose(result["minimum_obb_clearance"], 3.0)
    assert result["minimum_obb_clearance_clip_m"] == 3.0
    assert result["physical_feasible_mask"].all()


def _canonical_14d_fixture():
    candidates, route, speed, has_speed = _route_projection_fixture()
    time = np.linspace(0.0, 1.0, 80)
    for candidate_index in range(8):
        end = 32.0 + candidate_index
        candidates[candidate_index, :, 0] = 0.25 + (end - 0.25) * time
    candidates[2, :, 1] = 2.5
    candidates[3, :, 0] = 0.25 + (35.0 - 0.25) * time**3
    route[1, 10:, 10] = 1.0

    causal_input = _causal_input()
    causal_input["route_lanes"] = route.astype(np.float32)
    causal_input["route_lanes_speed_limit"] = speed.astype(np.float32)
    causal_input["route_lanes_has_speed_limit"] = has_speed
    causal_input["ego_shape"] = np.array(
        [2.925, 4.5, 1.9], dtype=np.float32
    )
    causal_input["neighbor_agents_past"][0, -1, 6:8] = [2.0, 4.0]

    neighbors = np.zeros((8, 32, 80, 4), dtype=np.float64)
    neighbors[:, 0, :, 0] = candidates[:, :, 0]
    neighbors[:, 0, :, 1] = 4.0
    neighbors[:, 0, :, 2] = 1.0
    valid = np.zeros(32, dtype=bool)
    valid[0] = True
    return candidates, causal_input, neighbors, valid


def test_materialize_canonical_14d_uses_real_sources_and_feasible_progress() -> None:
    candidates, causal_input, neighbors, valid = _canonical_14d_fixture()

    result = causal_atoms.materialize_canonical_14d(
        candidates=candidates,
        causal_input=causal_input,
        neighbor_predictions=neighbors,
        neighbor_valid_mask=valid,
        signal_mask=np.ones(8, dtype=bool),
        planned_red_light_cost=np.arange(8, dtype=np.float64),
        dt=np.float32(0.1),
    )

    atoms = result["atom_matrix"]
    assert result["canonical_eligible"] is True
    assert result["baseline_semantics"] == "fixed_dp_deterministic_map_baseline"
    assert result["baseline_equivalence_verified"] is False
    assert result["native_ranked_top1"] is False
    assert result["atom_names"] == tuple(causal_atoms.DP_CAMP_ATOM_NAMES_V10)
    assert atoms.shape == (8, 14)
    assert np.all(np.isfinite(atoms))
    assert np.all(atoms >= 0.0)
    used_dt = float(np.float32(0.1))
    xy = candidates[:, :, :2]
    velocity = np.diff(xy, axis=1) / used_dt
    acceleration = np.diff(velocity, axis=1) / used_dt
    jerk_squared = np.sum(
        (np.diff(acceleration, axis=1) / used_dt) ** 2,
        axis=2,
    )
    split = max(1, jerk_squared.shape[1] // 3)
    np.testing.assert_allclose(
        atoms[:, :4],
        np.column_stack(
            [
                used_dt * jerk_squared[:, :split].sum(axis=1),
                used_dt * jerk_squared[:, split:].sum(axis=1),
                used_dt * jerk_squared.sum(axis=1),
                np.sqrt(np.mean(np.sum(acceleration**2, axis=2), axis=1)),
            ]
        ),
    )
    projection = causal_atoms.project_candidates_to_route(
        candidates,
        causal_input["route_lanes"],
        causal_input["route_lanes_speed_limit"],
        causal_input["route_lanes_has_speed_limit"],
    )
    speeds = np.linalg.norm(velocity, axis=2)
    limits = projection["speed_limit"][:, 1:]
    for atom_index, margin in zip((4, 5, 6), (0.0, 0.5, 1.0)):
        np.testing.assert_allclose(
            atoms[:, atom_index],
            used_dt
            * (np.maximum(speeds - (limits - margin), 0.0) ** 2).sum(axis=1),
        )
    assert atoms[2, 7] > 0.0
    assert atoms[3, 4] > 0.0
    assert np.all(atoms[:, 4] <= atoms[:, 5])
    assert np.all(atoms[:, 5] <= atoms[:, 6])
    expected_clearance = used_dt * np.sum(
        np.maximum(3.0 - result["minimum_obb_clearance"], 0.0) ** 2,
        axis=1,
    )
    np.testing.assert_allclose(atoms[:, 8], expected_clearance)
    feasible = result["physical_feasible_mask"]
    assert feasible.any()
    assert not bool(feasible[2])
    expected_progress = np.maximum(
        result["route_progress"][feasible].max()
        - result["route_progress"],
        0.0,
    )
    np.testing.assert_allclose(atoms[:, 9], expected_progress)
    np.testing.assert_allclose(atoms[:, 10], np.arange(8, dtype=np.float64))
    np.testing.assert_allclose(
        atoms[:, 11],
        causal_atoms.compute_lateral_comfort_shadow_costs(candidates, used_dt)[0],
    )
    np.testing.assert_allclose(
        atoms[:, 12],
        causal_atoms.compute_red_stopping_margin_costs(
            candidates,
            causal_atoms._red_route_points_from_lanes(
                causal_input["route_lanes"]
            ),
            used_dt,
        ),
    )
    np.testing.assert_allclose(
        atoms[:, 13],
        causal_atoms.compute_dp_prior_comfort_excess_costs(
            candidates, used_dt
        )[0],
    )
    assert atoms[0, 13] == 0.0
    assert atoms[3, 13] > 0.0
    assert result["progress_reference"] == pytest.approx(
        result["route_progress"][feasible].max()
    )


def test_materialization_phase_receipt_is_telemetry_only_for_atom_and_selection_fixture() -> None:
    from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
        build_no_signal_causal_atom_input,
        build_runtime_no_signal_receipt,
    )
    from scripts.integrations.run_diffusion_planner_dp_camp_v19_worker import (
        select_camp_candidate,
    )
    from scripts.integrations.validate_diffusion_planner_v25_fair_nonholdout import (
        _build_no_signal_chain,
    )

    class _Lanelet:
        @staticmethod
        def trafficLights():
            return []

    class _CachedLanelet:
        raw_centerline = np.asarray([[0.0, 0.0], [40.0, 0.0]])

    class _Builder:
        _ll_by_id = {1: _Lanelet()}
        _cache = {1: _CachedLanelet()}

    candidates, causal_input, neighbors, valid = _canonical_14d_fixture()
    candidates = candidates.astype(np.float32)
    chain = _build_no_signal_chain(
        builder=_Builder(),
        route_ids=[1],
        map_sha256="a" * 64,
        route_sha256="b" * 64,
    )
    runtime_signal = build_runtime_no_signal_receipt(
        chain,
        scenario_id=chain["scenario_id"],
        tick_index=0,
        decision_time_s=0.0,
    )
    kwargs = {
        "candidates": candidates,
        "causal_input": causal_input,
        "neighbor_predictions": neighbors,
        "neighbor_valid_mask": valid,
        "signal_mask": np.ones(8, dtype=bool),
        "planned_red_light_cost": np.zeros(8, dtype=np.float64),
        "causal_signal_atom_input": build_no_signal_causal_atom_input(
            chain, runtime_signal
        ),
        "dt": np.float32(0.1),
        "eligibility_policy": "v22_source_valid",
    }
    baseline = causal_atoms.materialize_canonical_14d(**kwargs)
    phase_receipt: dict[str, object] = {}
    instrumented = causal_atoms.materialize_canonical_14d(
        **kwargs,
        phase_receipt=phase_receipt,
    )
    assert causal_atoms.validate_materialization_phase_receipt(phase_receipt) == phase_receipt
    assert all(row["status"] == "measured" for row in phase_receipt.values())
    assert all(type(row["elapsed_ns"]) is int for row in phase_receipt.values())
    assert all(row["elapsed_ns"] >= 0 for row in phase_receipt.values())
    assert baseline["atom_matrix"].tobytes() == instrumented["atom_matrix"].tobytes()
    np.testing.assert_array_equal(
        baseline["physical_feasible_mask"], instrumented["physical_feasible_mask"]
    )
    np.testing.assert_array_equal(
        baseline["source_valid_mask"], instrumented["source_valid_mask"]
    )
    scales = np.maximum(
        np.max(np.asarray(baseline["atom_matrix"], dtype=np.float64), axis=0),
        1.0,
    )
    weights = np.full(14, 1.0 / 14.0, dtype=np.float64)
    baseline_selection = select_camp_candidate(
        candidates=candidates,
        materialized=baseline,
        atom_scales=scales,
        weights=weights,
        eligibility_mask_name="source_valid_mask",
        simplex_nonnegative_atol=1e-9,
    )
    instrumented_selection = select_camp_candidate(
        candidates=candidates,
        materialized=instrumented,
        atom_scales=scales,
        weights=weights,
        eligibility_mask_name="source_valid_mask",
        simplex_nonnegative_atol=1e-9,
    )
    assert baseline_selection["selected_index"] == instrumented_selection["selected_index"]
    assert baseline_selection["scores"].tobytes() == instrumented_selection["scores"].tobytes()
    assert (
        baseline_selection["selected_trajectory"].tobytes()
        == instrumented_selection["selected_trajectory"].tobytes()
    )


def test_materialize_canonical_14d_rejects_expert_future_at_causal_boundary() -> None:
    candidates, causal_input, neighbors, valid = _canonical_14d_fixture()
    causal_input["expert_ego_future"] = np.full((80, 3), 999.0)

    with pytest.raises(ValueError, match="extra:expert_ego_future"):
        causal_atoms.materialize_canonical_14d(
            candidates=candidates,
            causal_input=causal_input,
            neighbor_predictions=neighbors,
            neighbor_valid_mask=valid,
            signal_mask=np.ones(8, dtype=bool),
            planned_red_light_cost=np.arange(8, dtype=np.float64),
            dt=0.1,
        )


def test_materialize_canonical_14d_rejects_source_incomplete_record() -> None:
    candidates, causal_input, neighbors, valid = _canonical_14d_fixture()
    signal = np.ones(8, dtype=bool)
    signal[7] = False

    result = causal_atoms.materialize_canonical_14d(
        candidates=candidates,
        causal_input=causal_input,
        neighbor_predictions=neighbors,
        neighbor_valid_mask=valid,
        signal_mask=signal,
        planned_red_light_cost=np.arange(8, dtype=np.float64),
        dt=0.1,
    )

    assert result["canonical_eligible"] is False
    assert result["atom_matrix"] is None
    assert result["exclusion_reason"] == "signal_source_incomplete"
    assert result["progress_reference"] is None


def test_materialize_candidate_local_speed_excludes_ineligible_candidates() -> None:
    candidates, causal_input, neighbors, valid = _canonical_14d_fixture()
    candidates[:4, :, 0] = np.linspace(0.25, 10.0, 80)
    neighbors[:4, 0, :, 0] = candidates[:4, :, 0]
    causal_input["route_lanes_has_speed_limit"][1, 0] = False
    causal_input["route_lanes_speed_limit"][1, 0] = 0.0

    result = causal_atoms.materialize_canonical_14d(
        candidates=candidates,
        causal_input=causal_input,
        neighbor_predictions=neighbors,
        neighbor_valid_mask=valid,
        signal_mask=np.ones(8, dtype=bool),
        planned_red_light_cost=np.arange(8, dtype=np.float64),
        dt=0.1,
        speed_source_policy=causal_atoms.CANDIDATE_LOCAL_EXACT_SPEED,
    )

    expected = np.array([True] * 4 + [False] * 4)
    assert result["canonical_eligible"] is True
    np.testing.assert_array_equal(
        result["route_speed_source_eligible_mask"], expected
    )
    assert not result["physical_feasible_mask"][~expected].any()
    assert all(
        "route_speed_source_unavailable" in result["candidate_reasons"][index]
        for index in range(4, 8)
    )
    np.testing.assert_array_equal(result["atom_matrix"][~expected, 4:7], 0.0)
    assert result["progress_reference"] == pytest.approx(
        result["route_progress"][result["physical_feasible_mask"]].max()
    )


def test_materialize_candidate_local_speed_excludes_all_source_ineligible() -> None:
    candidates, causal_input, neighbors, valid = _canonical_14d_fixture()
    causal_input["route_lanes_has_speed_limit"][:] = False
    causal_input["route_lanes_speed_limit"][:] = 0.0

    result = causal_atoms.materialize_canonical_14d(
        candidates=candidates,
        causal_input=causal_input,
        neighbor_predictions=neighbors,
        neighbor_valid_mask=valid,
        signal_mask=np.ones(8, dtype=bool),
        planned_red_light_cost=np.arange(8, dtype=np.float64),
        dt=0.1,
        speed_source_policy=causal_atoms.CANDIDATE_LOCAL_EXACT_SPEED,
    )

    assert result["canonical_eligible"] is False
    assert result["atom_matrix"] is None
    assert result["exclusion_reason"] == "all_candidates_route_speed_source_ineligible"
    assert not result["route_speed_source_eligible_mask"].any()
    assert not result["physical_feasible_mask"].any()
    assert result["progress_reference"] is None


def test_materialize_canonical_14d_excludes_all_k_infeasible_without_fallback() -> None:
    candidates, causal_input, neighbors, valid = _canonical_14d_fixture()
    neighbors[:, 0, :, :2] = candidates[:, None, :, :2][:, 0]

    result = causal_atoms.materialize_canonical_14d(
        candidates=candidates,
        causal_input=causal_input,
        neighbor_predictions=neighbors,
        neighbor_valid_mask=valid,
        signal_mask=np.ones(8, dtype=bool),
        planned_red_light_cost=np.arange(8, dtype=np.float64),
        dt=0.1,
    )

    assert result["canonical_eligible"] is False
    assert result["atom_matrix"] is None
    assert result["exclusion_reason"] == "all_candidates_physically_infeasible"
    assert not result["physical_feasible_mask"].any()
    assert not bool(result["physical_feasible_mask"][0])
    assert result["progress_reference"] is None


def test_materialize_v22_keeps_source_valid_all_k_high_risk() -> None:
    candidates, causal_input, neighbors, valid = _canonical_14d_fixture()
    neighbors[:, 0, :, :2] = candidates[:, None, :, :2][:, 0]

    result = causal_atoms.materialize_canonical_14d(
        candidates=candidates,
        causal_input=causal_input,
        neighbor_predictions=neighbors,
        neighbor_valid_mask=valid,
        signal_mask=np.ones(8, dtype=bool),
        planned_red_light_cost=np.arange(8, dtype=np.float64),
        dt=0.1,
        eligibility_policy="v22_source_valid",
    )

    assert result["canonical_eligible"] is True
    assert result["source_valid_mask"].tolist() == [True] * 8
    assert result["physical_feasible_mask"].tolist() == [False] * 8
    assert result["all_k_high_risk"] is True
    assert result["atom_matrix"].shape == (8, 14)
    assert np.isfinite(result["atom_matrix"]).all()
    assert result["progress_reference"] == pytest.approx(
        result["route_progress"][result["source_valid_mask"]].max()
    )


def _materialization_output_fixture(tmp_path, module):
    candidate_root = tmp_path / "candidates"
    candidate_root.mkdir()
    causal_input = _causal_input()
    input_hash = module.causal_input_sha256(causal_input)
    splits = ("calibration", "holdout", "train")
    source_rows = []
    candidate_rows = []
    sha_lines = []
    for index, split in enumerate(splits):
        source = {
            "split": split,
            "log_token": f"log_{index}",
            "scene_token": f"scene_{index}",
            "decision_token": f"decision_{index}",
            "db_path": f"db_{index}",
            "map_path": f"map_{index}",
            "causal_input_sha256": input_hash,
            "causal_source_schema_version": module.CAUSAL_SOURCE_SCHEMA_VERSION,
        }
        source_rows.append(source)
        relative = f"{split}/log_{index}/scene_{index}.npz"
        path = candidate_root / relative
        path.parent.mkdir(parents=True)
        candidates = np.zeros((8, 80, 4), dtype=np.float32)
        candidates[..., 0] = index
        candidates[..., 2] = 1.0
        neighbors = np.zeros((8, 32, 80, 4), dtype=np.float32)
        neighbors[..., 2] = 1.0
        valid = np.zeros(32, dtype=bool)
        signal = np.ones(8, dtype=bool)
        np.savez(
            path,
            candidate_tensor=candidates,
            neighbor_prediction_tensor=neighbors,
            neighbor_valid_mask=valid,
            candidate_signal_source_available_mask=signal,
            eligible_for_canonical_14d=np.array(True),
            dp_top1_index=np.array(0, dtype=np.int64),
            candidate_count=np.array(8, dtype=np.int64),
            causal_input_sha256=np.array(input_hash),
            causal_source_schema_version=np.array(
                module.CAUSAL_SOURCE_SCHEMA_VERSION
            ),
        )
        file_hash = module._sha256(path)
        sha_lines.append(f"{file_hash}  ./{relative}")
        candidate_rows.append(
            {
                **{
                    key: source[key]
                    for key in (
                        "split",
                        "log_token",
                        "scene_token",
                        "decision_token",
                    )
                },
                "DP_HEAD": module.FIXED_DP_HEAD,
                "K": 8,
                "candidate_count": 8,
                "dp_top1_index": 0,
                "causal_input_sha256": input_hash,
                "causal_source_schema_version": module.CAUSAL_SOURCE_SCHEMA_VERSION,
                "candidate_tensor_sha256": module._array_sha256(candidates),
                "neighbor_prediction_tensor_sha256": module._array_sha256(
                    neighbors
                ),
                "neighbor_valid_mask_sha256": module._array_sha256(valid),
                "candidate_signal_source_available_mask_sha256": (
                    module._array_sha256(signal)
                ),
                "output_npz": relative,
                "output_npz_sha256": file_hash,
            }
        )
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in source_rows),
        encoding="utf-8",
    )
    records_path = candidate_root / "records.jsonl"
    records_path.write_text(
        "".join(
            json.dumps(row, sort_keys=True) + "\n" for row in candidate_rows
        ),
        encoding="utf-8",
    )
    summary_path = candidate_root / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "manifest": str(manifest),
                "manifest_sha256": module._sha256(manifest),
                "record_count": len(source_rows),
                "candidate_generation_executed": True,
                "dp_head": module.FIXED_DP_HEAD,
                "k": 8,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    sha_lines.extend(
        [
            f"{module._sha256(records_path)}  ./records.jsonl",
            f"{module._sha256(summary_path)}  ./summary.json",
        ]
    )
    (candidate_root / "SHA256SUMS").write_text(
        "\n".join(sha_lines) + "\n", encoding="utf-8"
    )
    root_hash = module._sha256(candidate_root / "SHA256SUMS")
    (candidate_root / "ROOT_SHA256SUMS").write_text(
        f"{root_hash}  SHA256SUMS\n", encoding="utf-8"
    )
    args = argparse.Namespace(
        candidate_root=candidate_root,
        expected_candidate_root_sha256=root_hash,
        materialize_output_dir=tmp_path / "canonical",
        current_status=tmp_path / "status.md",
        v18_audit=tmp_path / "audit.md",
        dp_repo=tmp_path / "dp",
    )
    return args, causal_input


def test_run_materialization_seals_holdout_and_excludes_all_k(
    tmp_path, monkeypatch
) -> None:
    module = _orchestrator()
    args, causal_input = _materialization_output_fixture(tmp_path, module)
    pointer_calls = []
    monkeypatch.setattr(
        module,
        "read_v18_status_pointer",
        lambda status, audit: pointer_calls.append((status, audit)) or {"gate": "ok"},
    )
    monkeypatch.setattr(
        module,
        "_verify_fixed_dp_repo",
        lambda _path: module.FIXED_DP_HEAD,
    )
    monkeypatch.setattr(
        module,
        "materialize_nuplan_decision",
        lambda *_args: type("Result", (), {"dp_input": causal_input})(),
    )
    monkeypatch.setattr(
        module,
        "_fixed_dp_red_cost",
        lambda *_args, **_kwargs: np.arange(8, dtype=np.float64),
    )

    def fake_canonical(*, candidates, **_kwargs):
        index = int(candidates[0, 0, 0])
        eligible = index < 2
        physical = np.full(8, eligible, dtype=bool)
        reasons = tuple(() if eligible else ("obb_collision",) for _ in range(8))
        return {
            "atom_names": tuple(causal_atoms.DP_CAMP_ATOM_NAMES_V10),
            "atom_matrix": (
                np.full((8, 14), index, dtype=np.float64)
                if eligible
                else None
            ),
            "canonical_eligible": eligible,
            "exclusion_reason": (
                None if eligible else "all_candidates_physically_infeasible"
            ),
            "signal_mask": np.ones(8, dtype=bool),
            "lane_feasible_mask": np.ones(8, dtype=bool),
            "obb_collision_free_mask": physical,
            "physical_feasible_mask": physical,
            "candidate_reasons": reasons,
            "route_progress": np.arange(8, dtype=np.float64),
            "minimum_obb_clearance": np.full((8, 80), 3.0),
            "minimum_obb_clearance_clip_m": 3.0,
            "progress_reference": (7.0 if eligible else None),
            "baseline_semantics": module.BASELINE_SEMANTICS,
            "baseline_equivalence_verified": False,
            "native_ranked_top1": False,
            "feasibility_scope": module.FEASIBILITY_SCOPE,
            "closed_loop_safety_claim": False,
        }

    monkeypatch.setattr(module, "materialize_canonical_14d", fake_canonical)
    label_calls = []

    def fake_label(_db_path, decision_token, **_kwargs):
        label_calls.append(decision_token)
        return np.full((80, 3), len(label_calls), dtype=np.float64)

    monkeypatch.setattr(module, "load_nuplan_expert_ego_future", fake_label)
    source_paths = sorted(path for path in args.candidate_root.rglob("*") if path.is_file())
    source_before = {str(path.relative_to(args.candidate_root)): module._sha256(path) for path in source_paths}
    real_snapshot = module._candidate_source_snapshot
    promotion_state = []

    def tracked_snapshot(*snapshot_args, **snapshot_kwargs):
        promotion_state.append(args.materialize_output_dir.exists())
        return real_snapshot(*snapshot_args, **snapshot_kwargs)

    monkeypatch.setattr(module, "_candidate_source_snapshot", tracked_snapshot)

    report = module.run_materialization(args)

    source_after = {str(path.relative_to(args.candidate_root)): module._sha256(path) for path in source_paths}
    assert source_after == source_before
    assert report["model_calls"] == 0
    assert report["candidate_generation_executed"] is False
    assert report["baseline_semantics"] == module.BASELINE_SEMANTICS
    assert report["native_ranked_top1"] is False
    assert report["feasibility_scope"] == module.FEASIBILITY_SCOPE
    assert report["closed_loop_safety_claim"] is False
    assert report["holdout_labels_read"] == 0
    assert label_calls == ["decision_0"]
    assert pointer_calls == [(args.current_status, args.v18_audit)]
    assert promotion_state == [False, False]

    rows = [
        json.loads(line)
        for line in (args.materialize_output_dir / "records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 3
    assert rows[0]["label_read"] is True
    assert rows[1]["label_read"] is False
    assert rows[2]["canonical_output_npz"] is None
    assert rows[2]["exclusion_reason"] == "all_candidates_physically_infeasible"
    assert rows[2]["physical_feasible_mask"] == [False] * 8
    assert rows[2]["candidate_reasons"] == [["obb_collision"]] * 8
    summary = json.loads(
        (args.materialize_output_dir / "summary.json").read_text(encoding="utf-8")
    )
    assert summary["counts"]["overall"]["materialized"] == 2
    assert summary["counts"]["overall"]["labelled"] == 1
    assert summary["counts"]["overall"]["all_k_infeasible"] == 1
    assert summary["counts"]["by_split"]["holdout"]["holdout_sealed"] == 1
    with np.load(
        args.materialize_output_dir / rows[0]["canonical_output_npz"],
        allow_pickle=False,
    ) as calibration:
        assert "expert_ego_future_xyh" in calibration.files
    with np.load(
        args.materialize_output_dir / rows[1]["canonical_output_npz"],
        allow_pickle=False,
    ) as holdout:
        assert "expert_ego_future_xyh" not in holdout.files
        assert holdout["atom_matrix"].shape == (8, 14)

    with pytest.raises(FileExistsError):
        module.run_materialization(args)
    assert label_calls == ["decision_0"]


def test_run_materialization_rejects_candidate_root_sha_mismatch(
    tmp_path, monkeypatch
) -> None:
    module = _orchestrator()
    args, _ = _materialization_output_fixture(tmp_path, module)
    args.expected_candidate_root_sha256 = "0" * 64
    monkeypatch.setattr(
        module, "read_v18_status_pointer", lambda *_args: {"gate": "ok"}
    )

    with pytest.raises(ValueError, match="candidate root SHA256 mismatch"):
        module.run_materialization(args)


def test_materialization_cli_mode_is_mutually_exclusive() -> None:
    module = _orchestrator()
    args = module.parse_args(
        [
            "--dp_repo",
            "dp",
            "--candidate_root",
            "candidates",
            "--expected_candidate_root_sha256",
            "a" * 64,
            "--materialize_output_dir",
            "canonical",
            "--current_status",
            "status.md",
            "--v18_audit",
            "audit.md",
        ]
    )

    assert args.candidate_root.name == "candidates"
    with pytest.raises(SystemExit):
        module.parse_args(
            [
                "--dp_repo",
                "dp",
                "--candidate_root",
                "candidates",
                "--expected_candidate_root_sha256",
                "a" * 64,
                "--materialize_output_dir",
                "canonical",
                "--current_status",
                "status.md",
                "--v18_audit",
                "audit.md",
                "--manifest",
                "manifest.jsonl",
            ]
        )


def test_v18_pointer_reader_ignores_historical_file_tail(tmp_path) -> None:
    module = _orchestrator()
    pointer = {
        "current_v18_status": "ready",
        "current_v18_artifact_scope": "scope",
        "current_v18_artifact": "/artifact",
        "current_v18_artifact_root_sha256": "a" * 64,
        "next_work_target": "implementation_only",
    }
    lines = "\n".join(f"{key}={value}" for key, value in pointer.items())
    status = tmp_path / "status.md"
    status.write_text(
        "## Current V18 Status\n"
        + lines
        + "\n## Historical V14\nnext_work_target=wrong\n",
        encoding="utf-8",
    )
    audit = tmp_path / "audit.md"
    audit.write_text(lines + "\n", encoding="utf-8")

    assert module.read_v18_status_pointer(status, audit) == pointer


def test_checked_in_current_v18_pointer_matches_v18_audit_eof() -> None:
    module = _orchestrator()

    pointer = module.read_v18_status_pointer(
        module.ROOT / "docs" / "diffusion_planner_current_status.md",
        module.ROOT / "docs" / "diffusion_planner_v18_iteration_audit.md",
    )

    assert "v18_nuplan_" in pointer["next_work_target"]


def test_candidate_zero_metadata_is_deterministic_map_not_native_ranking() -> None:
    module = _orchestrator()

    assert module.BASELINE_INDEX == 0
    assert module.BASELINE_SEMANTICS == "fixed_dp_deterministic_map_baseline"
    assert module.NATIVE_RANKED_TOP1 is False
    assert (
        module.FEASIBILITY_SCOPE
        == "frozen_observable_32_dynamic_plus_5_static_only"
    )
    assert module.CLOSED_LOOP_SAFETY_CLAIM is False


def test_fixed_dp_python_paths_include_nested_package_root(tmp_path) -> None:
    module = _orchestrator()
    dp_repo = tmp_path / "Diffusion-Planner"
    package_root = dp_repo / "diffusion_planner"
    package_root.mkdir(parents=True)

    assert module._fixed_dp_python_paths(dp_repo) == (
        package_root,
        dp_repo,
    )


def test_prepare_causal_arrays_pads_only_neighbor_history() -> None:
    module = _orchestrator()

    prepared = module.prepare_causal_arrays(_causal_input())

    assert set(prepared) == set(CAUSAL_DP_INPUT_SCHEMA)
    assert prepared["neighbor_agents_past"].shape == (320, 31, 11)
    assert prepared["neighbor_agents_past"][0, 0, 0] == 7.0
    assert not prepared["neighbor_agents_past"][32:].any()
    assert not any("future" in key for key in prepared)


def test_prepare_causal_arrays_rejects_future_fields() -> None:
    module = _orchestrator()
    data = _causal_input()
    data["ego_agent_future"] = np.zeros((80, 3), dtype=np.float32)

    with pytest.raises(ValueError, match="future|extra"):
        module.prepare_causal_arrays(data)


def test_same_calls_return_paired_ego_and_first_32_neighbors() -> None:
    torch = pytest.importorskip("torch")
    module = _orchestrator()

    class Decoder:
        _guidance_fn = "original"
        _guidance_scale = 9.0

    class Model:
        decoder = Decoder()

        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, _data):
            prediction = torch.zeros((1, 321, 80, 4), dtype=torch.float32)
            prediction[:, :, :, 0] = self.calls
            prediction[:, :, :, 1] = torch.arange(321).reshape(1, 321, 1)
            self.calls += 1
            return None, {"prediction": prediction}

    model = Model()
    latent_scales = []

    def make_initial_latent(batch, agents, horizon, device, scale):
        latent_scales.append(scale)
        return torch.zeros((batch, agents, horizon, 4), device=device)

    context = {
        "torch": torch,
        "device": torch.device("cpu"),
        "model": model,
        "config": type(
            "Config",
            (),
            {
                "predicted_neighbor_num": 320,
                "future_len": 80,
                "observation_normalizer": staticmethod(lambda value: value),
            },
        )(),
        "heading_to_cos_sin": lambda value: value,
        "make_initial_latent": make_initial_latent,
    }
    data = _causal_input()
    data["neighbor_agents_past"][:3, 0, 0] = 1.0

    candidates, neighbors, valid = module.sample_fixed_dp_sources(data, context)

    assert model.calls == 8
    assert latent_scales == [0.0] + [1.0] * 7
    assert candidates.shape == (8, 80, 4)
    assert neighbors.shape == (8, 32, 80, 4)
    np.testing.assert_array_equal(candidates[:, 0, 0], np.arange(8))
    np.testing.assert_array_equal(neighbors[0, :, 0, 1], np.arange(1, 33))
    np.testing.assert_array_equal(valid[:3], np.ones(3, dtype=bool))
    assert not valid[3:].any()
    assert model.decoder._guidance_fn == "original"
    assert model.decoder._guidance_scale == 9.0


def test_white_signal_mask_is_fail_closed_only_when_reachable() -> None:
    module = _orchestrator()
    candidates = np.zeros((2, 80, 4), dtype=np.float32)
    candidates[:, :, 2] = 1.0
    candidates[0, :, 0] = np.linspace(0.0, 20.0, 80)
    candidates[1, :, 0] = np.linspace(0.0, 2.0, 80)
    route = np.zeros((25, 20, 33), dtype=np.float32)
    route[0, :, 0] = np.linspace(10.0, 15.0, 20)
    route[0, :, 2] = 1.0
    route[0, :, 11] = 1.0

    available = module.candidate_signal_source_available_mask(candidates, route)

    np.testing.assert_array_equal(available, [False, True])


def test_refresh_manifest_preserves_identity_and_replaces_causal_provenance(
    tmp_path, monkeypatch
) -> None:
    module = _orchestrator()
    old = tmp_path / "old.jsonl"
    row = {
        "split": "train",
        "log_token": "log",
        "scene_token": "scene",
        "decision_token": "decision",
        "db_path": "db",
        "map_path": "map",
        "causal_input_sha256": "old",
    }
    old.write_text(json.dumps(row) + "\n", encoding="utf-8")
    output = tmp_path / "new.jsonl"
    data = _causal_input()
    data["static_objects"][0, :6] = [1.0, 0.0, 1.0, 0.0, 1.0, 2.0]
    data["neighbor_agents_past"][:3, 0, 0] = 1.0
    monkeypatch.setattr(
        module,
        "materialize_nuplan_decision",
        lambda *_args: type("Result", (), {"dp_input": data})(),
    )
    args = type(
        "Args",
        (),
        {
            "manifest": old,
            "expected_manifest_sha256": module._sha256(old),
            "refresh_manifest_output": output,
        },
    )()

    report = module.refresh_manifest(args)
    refreshed = json.loads(output.read_text(encoding="utf-8"))

    assert report["record_count"] == 1
    assert refreshed["split"] == "train"
    assert refreshed["scene_token"] == "scene"
    assert refreshed["causal_input_sha256"] != "old"
    assert refreshed["causal_source_schema_version"] == module.CAUSAL_SOURCE_SCHEMA_VERSION
    assert refreshed["parent_manifest_sha256"] == args.expected_manifest_sha256
    assert refreshed["static_object_count"] == 1
    assert refreshed["neighbor_valid_count"] == 3
    with pytest.raises(FileExistsError):
        module.refresh_manifest(args)


def test_record_npz_path_is_unique_per_decision() -> None:
    module = _orchestrator()
    common = {
        "split": "train",
        "log_token": "log",
        "scene_token": "scene",
    }

    first = module._record_npz_relative(
        {**common, "decision_token": "decision_a"}
    )
    second = module._record_npz_relative(
        {**common, "decision_token": "decision_b"}
    )

    assert first.as_posix() == "train/log/scene__decision_a.npz"
    assert second.as_posix() == "train/log/scene__decision_b.npz"
    assert first != second


def test_causal_10k_selection_excludes_parent_decisions_and_inherits_split(
    tmp_path, monkeypatch
) -> None:
    module = _orchestrator()
    parent_rows = []
    new_decisions = {}
    for index, split in enumerate(("train", "calibration", "holdout"), 1):
        scene_token = f"{index:032x}"
        parent_decision = f"{index + 10:032x}"
        new_decision = f"{index + 20:032x}"
        later_parent_decision = f"{index + 50:032x}"
        db_path = tmp_path / f"{split}.db"
        with sqlite3.connect(db_path) as db:
            db.execute(
                "CREATE TABLE lidar_pc ("
                "token BLOB PRIMARY KEY, scene_token BLOB, timestamp INTEGER)"
            )
            db.execute(
                "CREATE TABLE scenario_tag (lidar_pc_token BLOB, type TEXT)"
            )
            rows = [
                (bytes.fromhex(f"{index + 30:032x}"), 0),
                (bytes.fromhex(parent_decision), 3_500_000),
                (bytes.fromhex(new_decision), 4_000_000),
                (bytes.fromhex(f"{index + 40:032x}"), 12_000_000),
            ]
            if split == "train":
                rows.insert(
                    2, (bytes.fromhex(later_parent_decision), 3_750_000)
                )
            db.executemany(
                "INSERT INTO lidar_pc VALUES (?, ?, ?)",
                [(token, bytes.fromhex(scene_token), timestamp) for token, timestamp in rows],
            )
            db.executemany(
                "INSERT INTO scenario_tag VALUES (?, ?)",
                [
                    (bytes.fromhex(parent_decision), "parent"),
                    *(
                        [(bytes.fromhex(later_parent_decision), "parent_later")]
                        if split == "train"
                        else []
                    ),
                    (bytes.fromhex(new_decision), "new"),
                ],
            )
        parent_row = {
            "split": split,
            "log_token": f"log_{split}",
            "scene_token": scene_token,
            "decision_token": parent_decision,
            "db_path": str(db_path),
            "map_path": str(tmp_path / "map.gpkg"),
            "causal_input_sha256": "parent",
            "causal_source_schema_version": module.CAUSAL_SOURCE_SCHEMA_VERSION,
        }
        parent_rows.append(parent_row)
        if split == "train":
            parent_rows.append(
                {**parent_row, "decision_token": later_parent_decision}
            )
        new_decisions[split] = new_decision

    parent = tmp_path / "parent.jsonl"
    parent.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in parent_rows),
        encoding="utf-8",
    )
    output = tmp_path / "causal_10k.jsonl"
    causal_input = _causal_input()
    monkeypatch.setattr(module, "CAUSAL_10K_PARENT_MANIFEST_SHA256", module._sha256(parent))
    monkeypatch.setattr(module, "CAUSAL_10K_PARENT_RECORD_COUNT", len(parent_rows))
    monkeypatch.setattr(
        module,
        "CAUSAL_10K_SPLIT_TARGETS",
        {"train": 1, "calibration": 1, "holdout": 1},
    )
    monkeypatch.setattr(module, "CAUSAL_10K_MAX_PER_LOG", 1)
    monkeypatch.setattr(module, "CAUSAL_10K_MAX_PER_SCENE", 1)
    monkeypatch.setattr(module, "CAUSAL_10K_MIN_LOGS", 3)
    monkeypatch.setattr(module, "CAUSAL_10K_MIN_SCENES", 3)
    monkeypatch.setattr(
        module,
        "read_v18_status_pointer",
        lambda *_args: {"next_work_target": "authorized"},
    )
    dp_checks = []
    monkeypatch.setattr(
        module,
        "_verify_fixed_dp_repo",
        lambda *_args: dp_checks.append(module.FIXED_DP_HEAD) or module.FIXED_DP_HEAD,
    )
    monkeypatch.setattr(
        module,
        "materialize_nuplan_decision",
        lambda *_args: type(
            "Result",
            (),
            {"dp_input": causal_input, "metadata": {"source_dt_s": 0.05}},
        )(),
    )
    monkeypatch.setattr(
        module,
        "load_nuplan_expert_ego_future",
        lambda *_args, **_kwargs: pytest.fail("selection read an expert label"),
    )
    args = argparse.Namespace(
        manifest=parent,
        expected_manifest_sha256=module._sha256(parent),
        causal_10k_manifest_output=output,
        current_status=tmp_path / "status.md",
        v18_audit=tmp_path / "audit.md",
        dp_repo=tmp_path / "dp",
    )

    report = module.run_causal_10k_selection(args)

    selected = [json.loads(line) for line in output.read_text().splitlines()]
    assert report["record_count"] == 3
    assert report["split_counts"] == {
        "train": 1,
        "calibration": 1,
        "holdout": 1,
    }
    assert {row["split"]: row["decision_token"] for row in selected} == new_decisions
    assert all(row["causal_input_sha256"] == module.causal_input_sha256(causal_input) for row in selected)
    assert all(row["parent_manifest_sha256"] == module._sha256(parent) for row in selected)
    assert all(row["decision_token"] != row["parent_decision_token"] for row in selected)
    assert not {
        row["decision_token"] for row in selected
    } & {row["decision_token"] for row in parent_rows}
    assert report["expert_future_value_reads"] == 0
    assert report["model_calls"] == 0
    assert report["source_verified_after_run"] is True
    assert dp_checks == [module.FIXED_DP_HEAD, module.FIXED_DP_HEAD]


def test_run_manifest_writes_single_record_v2_source_provenance(
    tmp_path, monkeypatch
) -> None:
    module = _orchestrator()
    data = _causal_input()
    data["neighbor_agents_past"][:3, 0, 0] = 1.0
    data["route_lanes"][0, :, 0] = np.linspace(10.0, 15.0, 20)
    data["route_lanes"][0, :, 2] = 1.0
    data["route_lanes"][0, :, 11] = 1.0
    manifest = tmp_path / "manifest.jsonl"
    row = {
        "split": "train",
        "log_token": "log",
        "scene_token": "scene",
        "decision_token": "decision",
        "db_path": "db",
        "map_path": "map",
        "causal_input_sha256": module.causal_input_sha256(data),
        "causal_source_schema_version": module.CAUSAL_SOURCE_SCHEMA_VERSION,
    }
    manifest.write_text(json.dumps(row) + "\n", encoding="utf-8")
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    candidates[:, :, 2] = 1.0
    candidates[0, :, 0] = np.linspace(0.0, 20.0, 80)
    neighbors = np.zeros((8, 32, 80, 4), dtype=np.float32)
    valid = np.zeros(32, dtype=bool)
    valid[:3] = True
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Completed", (), {"stdout": module.FIXED_DP_HEAD + "\n"}
        )(),
    )
    monkeypatch.setattr(
        module,
        "_load_context",
        lambda *_args: {
            "torch": type("Torch", (), {"manual_seed": staticmethod(lambda _seed: None)})
        },
    )
    monkeypatch.setattr(
        module,
        "materialize_nuplan_decision",
        lambda *_args: type("Result", (), {"dp_input": data})(),
    )
    monkeypatch.setattr(
        module,
        "sample_fixed_dp_sources",
        lambda *_args, **_kwargs: (candidates, neighbors, valid),
    )
    args = type(
        "Args",
        (),
        {
            "manifest": manifest,
            "expected_manifest_sha256": module._sha256(manifest),
            "refresh_manifest_output": None,
            "output_dir": tmp_path / "output",
            "dp_repo": tmp_path,
            "checkpoint": tmp_path / "model.ckpt",
            "args_json": tmp_path / "args.json",
            "k": 8,
            "seed": 3407,
            "noise_scale": 1.0,
            "device": "cpu",
            "max_records": 0,
            "execute": True,
        },
    )()

    report = module.run_manifest(args)
    output_npz = args.output_dir / "train" / "log" / "scene__decision.npz"
    with np.load(output_npz, allow_pickle=False) as payload:
        assert set(payload.files) == {
            "candidate_tensor",
            "neighbor_prediction_tensor",
            "neighbor_valid_mask",
            "candidate_signal_source_available_mask",
            "eligible_for_canonical_14d",
            "causal_input_sha256",
            "causal_source_schema_version",
            "dp_top1_index",
            "candidate_count",
        }
        assert payload["neighbor_prediction_tensor"].shape == (8, 32, 80, 4)
        assert payload["neighbor_valid_mask"].shape == (32,)
        assert payload["candidate_signal_source_available_mask"].shape == (8,)
        assert not bool(payload["eligible_for_canonical_14d"])
    record = json.loads((args.output_dir / "records.jsonl").read_text().strip())
    assert report["schema_version"] == "dp_camp_v18_causal_fixed_dp_export_v2"
    assert record["physical_feasibility_mask_materialized"] is False
    assert record["eligible_for_canonical_14d"] is False
    with pytest.raises(FileExistsError):
        module.run_manifest(args)
