from __future__ import annotations

import numpy as np

from scripts.integrations.analyze_diffusion_planner_route_topology_candidate_screen import (
    GENERATOR_POLICY_MATERIAL_SUPPORT_V3,
    READY_STATUS,
    REJECT_STATUS,
    REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3,
    SOURCE_CONFLICT_STATUS,
    RouteTopologyCandidateConfig,
    _comfort_failure_classes,
    _snapshot_report_row,
    build_report_from_rows,
    build_route_topology_candidates,
    render_markdown,
    route_topology_candidate_construction_diagnostics,
)


def _readiness_report(
    *,
    status: str = "route_topology_candidate_design_ready",
    online_selector_authorized: bool = False,
) -> dict[str, object]:
    return {
        "snapshot_aggregate": {
            "ready_snapshot_rate": 1.0,
            "candidate_lane_p95_max_m": 1.0,
            "red_lane_p95_max_m": 0.0,
        },
        "final_decision": {
            "status": status,
            "offline_candidate_augmentation_screen_authorized": True,
            "online_selector_authorized": online_selector_authorized,
            "closed_loop_smoke_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
        },
    }


def _candidate_row(
    *,
    lower: bool = True,
    hard: bool = True,
    progress: bool = True,
    comfort: bool = True,
) -> dict[str, object]:
    return {
        "snapshot_path": "/fake/camp_microbenchmark_step_0001.npz",
        "selection_step": 1,
        "selected_index": 0,
        "candidate_index": 0,
        "candidate_meta": {"variant": "lane_centerline_red_stop"},
        "selected_union_red": 10.0,
        "candidate_union_red": 0.0 if lower else 11.0,
        "candidate_near_red": 0.0,
        "candidate_full_red": 0.0,
        "lower_union_red": lower,
        "hard_feasible": hard,
        "hard_reasons": [] if hard else ["dp_red_light"],
        "progress_feasible": progress,
        "progress_reasons": [] if progress else ["dp_underprogress"],
        "progress_loss_m": 0.2,
        "smoothness_loss": 0.0,
        "tracker_delta": {
            "command_jerk_worse_mps3": 0.0,
            "command_lateral_worse_mps2": 0.0,
            "rollout_distance_loss_m": 0.0,
            "rollout_jerk_worse_mps3": 0.0,
            "rollout_lateral_worse_mps2": 0.0,
        },
        "comfort_admissible": comfort,
        "failure_classes": (
            ["route_topology_comfort_admissible_support"]
            if comfort
            else ["route_topology_comfort_blocked_unknown_budget"]
        ),
    }


def test_route_topology_generator_builds_red_stop_candidates() -> None:
    horizon = 80
    candidates = np.zeros((2, horizon, 4), dtype=float)
    candidates[:, :, 0] = np.linspace(0.5, 40.0, horizon)
    candidates[:, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 60.0, 66)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red_x = np.linspace(20.0, 24.0, 5)
    red = np.column_stack([red_x, np.zeros_like(red_x)])

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=5.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            red_stop_margins_m=(2.0, 4.0),
            backup_stop_offsets_m=(0.0,),
        ),
    )

    assert generated.shape == (2, horizon, 4)
    assert len(meta) == 2
    assert np.all(np.isfinite(generated))
    for candidate, row in zip(generated, meta):
        assert candidate[0, 0] > 0.0
        assert candidate[-1, 0] <= row["stop_distance_m"] + 1e-9
        assert row["red_distance_m"] > row["stop_distance_m"]


def test_route_topology_generator_preserves_prefix_for_comfort_policy() -> None:
    horizon = 80
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.5, 40.0, horizon)
    candidates[0, :, 1] = np.linspace(0.0, -5.0, horizon)
    candidates[0, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 60.0, 66)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red_x = np.linspace(20.0, 24.0, 5)
    red = np.column_stack([red_x, np.zeros_like(red_x)])

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=5.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="prefix_comfort_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            prefix_steps=(5,),
            bridge_steps=(10,),
        ),
    )

    assert generated.shape == (1, horizon, 4)
    assert len(meta) == 1
    assert meta[0]["variant"] == "prefix_comfort_red_stop"
    assert meta[0]["prefix_steps"] == 5
    assert meta[0]["bridge_steps"] == 10
    np.testing.assert_allclose(generated[0, :5, :2], candidates[0, :5, :2])
    assert generated[0, -1, 0] <= meta[0]["stop_distance_m"] + 1e-9


def test_route_topology_generator_builds_lane_projected_red_stop_candidates() -> None:
    horizon = 80
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.5, 40.0, horizon)
    candidates[0, :, 1] = 1.0
    candidates[0, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 60.0, 66)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red_x = np.linspace(20.0, 24.0, 5)
    red = np.column_stack([red_x, np.zeros_like(red_x)])

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=5.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="lane_projected_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            lane_projected_offset_scales=(1.0, 0.0),
        ),
    )

    assert generated.shape == (2, horizon, 4)
    assert [row["variant"] for row in meta] == [
        "lane_projected_red_stop",
        "lane_projected_red_stop",
    ]
    assert [row["lateral_offset_scale"] for row in meta] == [1.0, 0.0]
    assert np.all(generated[:, :, 0] <= candidates[0, :, 0] + 1e-9)
    assert np.all(generated[:, :, 0] <= meta[0]["stop_distance_m"] + 1e-9)
    np.testing.assert_allclose(generated[0, :, 1], 1.0, atol=1e-9)
    np.testing.assert_allclose(generated[1, :, 1], 0.0, atol=1e-9)


def test_route_topology_generator_preserves_prefix_for_lane_projected_policy() -> None:
    horizon = 80
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.5, 40.0, horizon)
    candidates[0, :, 1] = np.linspace(1.0, 2.0, horizon)
    candidates[0, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 60.0, 66)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red_x = np.linspace(20.0, 24.0, 5)
    red = np.column_stack([red_x, np.zeros_like(red_x)])

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=5.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="prefix_lane_projected_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            lane_projected_offset_scales=(0.5,),
            prefix_steps=(5,),
            bridge_steps=(10,),
        ),
    )

    assert generated.shape == (1, horizon, 4)
    assert meta[0]["variant"] == "prefix_lane_projected_red_stop"
    assert meta[0]["prefix_steps"] == 5
    assert meta[0]["bridge_steps"] == 10
    assert meta[0]["lateral_offset_scale"] == 0.5
    np.testing.assert_allclose(generated[0, :5, :2], candidates[0, :5, :2])
    assert generated[0, -1, 0] <= meta[0]["stop_distance_m"] + 1e-9


def test_route_topology_generator_latest_safe_delays_stop_boundary() -> None:
    horizon = 80
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.5, 40.0, horizon)
    candidates[0, :, 1] = 1.0
    candidates[0, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 60.0, 66)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red_x = np.linspace(20.0, 24.0, 5)
    red = np.column_stack([red_x, np.zeros_like(red_x)])

    common = dict(
        red_stop_margins_m=(2.0,),
        backup_stop_offsets_m=(0.0,),
        lane_projected_offset_scales=(0.5,),
        prefix_steps=(5,),
        bridge_steps=(10,),
    )
    latest, latest_meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=5.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="prefix_lane_projected_latest_safe_red_stop",
            **common,
        ),
    )
    decel, _ = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=5.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="prefix_lane_projected_red_stop",
            **common,
        ),
    )

    assert latest.shape == (1, horizon, 4)
    assert latest_meta[0]["variant"] == "prefix_lane_projected_latest_safe_red_stop"
    assert latest_meta[0]["prefix_steps"] == 5
    assert latest_meta[0]["lateral_offset_scale"] == 0.5
    np.testing.assert_allclose(latest[0, :5, :2], candidates[0, :5, :2])
    assert latest[0, -1, 0] <= latest_meta[0]["stop_distance_m"] + 1e-9
    assert latest[0, 20, 0] >= decel[0, 20, 0] + 1.0


def test_route_topology_generator_builds_default_off_jerk_progress_policy() -> None:
    horizon = 80
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.8, 80.0, horizon)
    candidates[0, :, 1] = 0.8
    candidates[0, :, 2] = 1.0
    original = candidates.copy()
    lane_x = np.linspace(-5.0, 100.0, 106)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red_x = np.linspace(80.0, 84.0, 5)
    red = np.column_stack([red_x, np.zeros_like(red_x)])

    default_generated, default_meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=8.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            lane_projected_offset_scales=(0.0,),
        ),
    )
    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=8.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="lane_projected_jerk_progress_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            lane_projected_offset_scales=(0.0,),
            max_deceleration_mps2=3.0,
            jerk_progress_max_jerk_mps3=6.0,
        ),
    )

    assert default_meta[0]["variant"] == "lane_centerline_red_stop"
    assert generated.shape == (1, horizon, 4)
    assert meta[0]["variant"] == "lane_projected_jerk_progress_red_stop"
    assert meta[0]["profile"] == "acceleration_jerk_limited_progress"
    assert meta[0]["max_deceleration_mps2"] == 3.0
    assert meta[0]["max_jerk_mps3"] == 6.0
    np.testing.assert_allclose(candidates, original)
    assert np.all(np.isfinite(generated))
    assert np.all(generated[0, :, 0] <= meta[0]["stop_distance_m"] + 1e-9)
    assert np.all(np.diff(generated[0, :, 0]) >= -1e-9)
    assert default_generated.shape == (1, horizon, 4)


def test_route_topology_generator_jerk_progress_synthetic_bounds() -> None:
    horizon = 80
    dt = 0.1
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.8, 80.0, horizon)
    candidates[0, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 100.0, 106)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red_x = np.linspace(80.0, 84.0, 5)
    red = np.column_stack([red_x, np.zeros_like(red_x)])

    generated, _ = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=8.0,
        dt=dt,
        config=RouteTopologyCandidateConfig(
            generator_policy="lane_projected_jerk_progress_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            lane_projected_offset_scales=(0.0,),
            max_deceleration_mps2=3.0,
            jerk_progress_max_jerk_mps3=6.0,
        ),
    )

    progress = generated[0, :, 0]
    velocity = np.diff(np.concatenate([[0.0], progress])) / dt
    acceleration = np.diff(velocity) / dt
    jerk = np.diff(acceleration) / dt
    assert np.min(acceleration) >= -3.0 - 1e-6
    assert np.max(acceleration) <= 1e-6
    assert np.max(np.abs(jerk)) <= 6.0 + 1e-6


def test_route_topology_generator_builds_comfort_first_remediation_policy() -> None:
    horizon = 40
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.5, 16.0, horizon)
    candidates[0, :, 1] = 0.4
    candidates[0, :, 2] = 1.0
    original = candidates.copy()
    lane_x = np.linspace(-5.0, 25.0, 31)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([np.linspace(3.0, 3.5, 3), np.zeros(3)])

    baseline, baseline_meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="lane_projected_jerk_progress_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            min_stop_distance_m=2.0,
        ),
    )
    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="comfort_first_lane_projected_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            prefix_steps=(1,),
            bridge_steps=(3,),
            lane_projected_offset_scales=(0.0,),
            min_stop_distance_m=2.0,
            max_remediation_candidates=4,
        ),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="comfort_first_lane_projected_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            prefix_steps=(1,),
            bridge_steps=(3,),
            lane_projected_offset_scales=(0.0,),
            min_stop_distance_m=2.0,
            max_remediation_candidates=4,
        ),
    )

    assert baseline.shape == (0, horizon, 4)
    assert baseline_meta == []
    assert generated.shape == (1, horizon, 4)
    assert meta[0]["variant"] == "comfort_first_lane_projected_red_stop"
    assert meta[0]["profile"] == "comfort_first_jerk_limited_lane_station"
    assert meta[0]["red_stop_distance_partition"] == "close_red_current_tick_fallback"
    assert meta[0]["current_tick_features_only"] is True
    assert meta[0]["candidate_budget_cap"] == 4
    assert meta[0]["prefix_steps"] == 1
    assert meta[0]["bridge_steps"] == 3
    np.testing.assert_allclose(candidates, original)
    assert np.all(np.isfinite(generated))
    assert np.all(np.diff(generated[0, :, 0]) >= -1e-9)
    assert diagnostics["construction_status"] == "ready"
    assert diagnostics["failure_reason"] is None
    assert diagnostics["feasible_stop_windows"] == 0
    assert diagnostics["fallback_stop_windows"] == 1
    assert diagnostics["red_stop_distance_partition"] == "close_red_current_tick_fallback"
    assert diagnostics["current_tick_features_only"] is True


def test_route_topology_comfort_first_remediation_candidate_budget_cap() -> None:
    horizon = 40
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.5, 16.0, horizon)
    candidates[0, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 25.0, 31)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([np.linspace(10.0, 12.0, 3), np.zeros(3)])

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="comfort_first_lane_projected_red_stop",
            red_stop_margins_m=(1.0, 2.0),
            backup_stop_offsets_m=(0.0, 1.0),
            prefix_steps=(1, 3),
            bridge_steps=(2, 4),
            lane_projected_offset_scales=(1.0, 0.5, 0.0),
            max_remediation_candidates=3,
        ),
    )

    assert generated.shape == (3, horizon, 4)
    assert len(meta) == 3
    assert all(row["candidate_budget_cap"] == 3 for row in meta)
    assert {row["variant"] for row in meta} == {
        "comfort_first_lane_projected_red_stop"
    }


def test_route_topology_generator_builds_negative_support_followup_policy() -> None:
    horizon = 40
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.5, 16.0, horizon)
    candidates[0, :, 1] = 0.6
    candidates[0, :, 2] = 1.0
    original = candidates.copy()
    lane_x = np.linspace(-5.0, 25.0, 31)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([np.linspace(3.0, 3.5, 3), np.zeros(3)])

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="negative_support_coverage_first_lane_projected_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            lane_projected_offset_scales=(1.0, 0.0),
            min_stop_distance_m=2.0,
            max_remediation_candidates=2,
        ),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="negative_support_coverage_first_lane_projected_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            lane_projected_offset_scales=(1.0, 0.0),
            min_stop_distance_m=2.0,
            max_remediation_candidates=2,
        ),
    )

    assert generated.shape == (2, horizon, 4)
    assert len(meta) == 2
    assert meta[0]["variant"] == "negative_support_coverage_first_lane_projected_red_stop"
    assert meta[0]["profile"] == (
        "coverage_first_hard_comfort_jerk_limited_lane_station"
    )
    assert meta[0]["red_stop_distance_partition"] == (
        "coverage_first_close_red_current_tick_fallback"
    )
    assert meta[0]["fail_closed_partition"] == "fallback_ready"
    assert meta[0]["hard_feasibility_floor_current_tick"] is True
    assert meta[0]["comfort_after_hard_progress"] is True
    assert meta[0]["current_tick_features_only"] is True
    assert meta[0]["candidate_budget_cap"] == 2
    assert meta[0]["lateral_offset_scale"] == 0.0
    np.testing.assert_allclose(candidates, original)
    assert np.all(np.isfinite(generated))
    assert np.all(np.diff(generated[0, :, 0]) >= -1e-9)
    assert diagnostics["construction_status"] == "ready"
    assert diagnostics["failure_reason"] is None
    assert diagnostics["fallback_stop_windows"] == 1
    assert diagnostics["fail_closed_partition"] == "fallback_ready"
    assert diagnostics["current_tick_features_only"] is True


def test_route_topology_negative_support_followup_preserves_default_policy() -> None:
    horizon = 30
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.0, 20.0, horizon)
    candidates[0, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 35.0, 41)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([np.linspace(18.0, 20.0, 3), np.zeros(3)])

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(),
    )

    assert generated.shape[1:] == (horizon, 4)
    assert len(meta) == generated.shape[0]
    assert {row["variant"] for row in meta} == {"lane_centerline_red_stop"}
    assert all("fail_closed_partition" not in row for row in meta)
    assert all("hard_feasibility_floor_current_tick" not in row for row in meta)


def test_route_topology_negative_support_followup_partitions_fail_closed_snapshots() -> None:
    horizon = 20
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[:, :, 2] = 1.0
    lane_x = np.linspace(0.0, 30.0, 31)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([[-5.0, 0.0]])

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="negative_support_coverage_first_lane_projected_red_stop"
        ),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="negative_support_coverage_first_lane_projected_red_stop"
        ),
    )

    assert generated.shape == (0, horizon, 4)
    assert meta == []
    assert diagnostics["construction_status"] == "fail_closed"
    assert diagnostics["failure_reason"] == "red_route_ahead_missing"
    assert diagnostics["fail_closed_partition"] == "red_route_ahead_missing"
    assert diagnostics["current_tick_features_only"] is True


def test_route_topology_negative_support_followup_rejects_nonfinite_current_tick_inputs() -> None:
    horizon = 30
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.0, 20.0, horizon)
    candidates[0, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 35.0, 41)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([np.linspace(18.0, 20.0, 3), np.zeros(3)])

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=np.nan,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="negative_support_coverage_first_lane_projected_red_stop"
        ),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=np.nan,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="negative_support_coverage_first_lane_projected_red_stop"
        ),
    )

    assert generated.shape == (0, horizon, 4)
    assert meta == []
    assert diagnostics["construction_status"] == "fail_closed"
    assert diagnostics["failure_reason"] == "current_tick_scalar_invalid"
    assert diagnostics["fail_closed_partition"] == "current_tick_scalar_invalid"
    assert diagnostics["current_tick_features_only"] is True


def test_route_topology_negative_support_followup_candidate_budget_cap() -> None:
    horizon = 40
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.5, 16.0, horizon)
    candidates[0, :, 1] = 0.5
    candidates[0, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 25.0, 31)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([np.linspace(10.0, 12.0, 3), np.zeros(3)])

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="negative_support_coverage_first_lane_projected_red_stop",
            red_stop_margins_m=(1.0, 2.0),
            backup_stop_offsets_m=(0.0, 1.0),
            lane_projected_offset_scales=(1.0, 0.5, 0.0),
            max_remediation_candidates=2,
        ),
    )

    assert generated.shape == (2, horizon, 4)
    assert len(meta) == 2
    assert all(row["candidate_budget_cap"] == 2 for row in meta)
    assert {row["variant"] for row in meta} == {
        "negative_support_coverage_first_lane_projected_red_stop"
    }


def test_route_topology_material_v3_builds_explicit_comfort_first_support() -> None:
    horizon = 40
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.0, 8.0, horizon)
    candidates[0, :, 2] = 1.0
    original = candidates.copy()
    lane_x = np.linspace(-5.0, 25.0, 31)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([np.linspace(14.0, 15.0, 3), np.zeros(3)])

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy=GENERATOR_POLICY_MATERIAL_SUPPORT_V3,
            default_off_remediation_profile=REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3,
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            prefix_steps=(1,),
            bridge_steps=(0,),
            lane_projected_offset_scales=(0.0,),
            max_remediation_candidates=2,
            command_jerk_worse_budget_mps3=1e6,
            rollout_jerk_worse_budget_mps3=1e6,
            rollout_lateral_worse_budget_mps2=1e6,
            progress_loss_budgets_m=(1000.0,),
            smoothness_loss_budgets=(1000.0,),
        ),
    )

    assert generated.shape == (1, horizon, 4)
    assert len(meta) == 1
    np.testing.assert_allclose(candidates, original)
    assert meta[0]["variant"] == GENERATOR_POLICY_MATERIAL_SUPPORT_V3
    assert meta[0]["profile"] == REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3
    assert meta[0]["candidate0_preserved"] is True
    assert meta[0]["dp_rows_preserved"] is True
    assert meta[0]["append_after_existing_candidate_count"] == 1
    assert meta[0]["comfort_first_profile_precheck"] is True
    assert meta[0]["comfort_first_precheck_passed"] is True
    descriptor = meta[0]["remediation_descriptor_payload"]
    assert descriptor["diagnostic_descriptor_payload_v3"] is True
    assert descriptor["diagnostic_descriptor_payload_v3_report_only"] is True
    assert descriptor["nonnegative_descriptor_channels"] is True
    assert descriptor["hinge_signed_split_channels"] is True
    assert descriptor["affine_score_compatible"] is True
    assert descriptor["score_contract"] == "score_k(w)=a_k^T w"
    assert descriptor["convex_master_contract"] == "simplex/CVaR/L2 unchanged"
    assert descriptor["score_mutation"] is False
    assert descriptor["selected_index_mutation"] is False
    assert descriptor["fallback_mutation"] is False
    assert descriptor["online_selector_feature"] is False
    assert descriptor["future_outcome_leakage"] is False


def test_route_topology_jerk_progress_requires_current_tick_scalars() -> None:
    horizon = 80
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.8, 80.0, horizon)
    candidates[0, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 100.0, 106)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red_x = np.linspace(80.0, 84.0, 5)
    red = np.column_stack([red_x, np.zeros_like(red_x)])

    default_generated, default_meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=np.nan,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
        ),
    )
    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=np.nan,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="lane_projected_jerk_progress_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
        ),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=np.nan,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="lane_projected_jerk_progress_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
        ),
    )

    assert default_generated.shape == (1, horizon, 4)
    assert default_meta[0]["variant"] == "lane_centerline_red_stop"
    assert generated.shape == (0, horizon, 4)
    assert meta == []
    assert diagnostics["construction_status"] == "fail_closed"
    assert diagnostics["failure_reason"] == "current_tick_scalar_invalid"
    assert diagnostics["requires_current_tick_scalar_evidence"] is True
    assert diagnostics["current_tick_scalar_evidence"] is False


def test_route_topology_comfort_first_requires_current_tick_scalars() -> None:
    horizon = 40
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.5, 16.0, horizon)
    candidates[0, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 25.0, 31)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([np.linspace(10.0, 12.0, 3), np.zeros(3)])

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=np.nan,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="comfort_first_lane_projected_red_stop"
        ),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=np.nan,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="comfort_first_lane_projected_red_stop"
        ),
    )

    assert generated.shape == (0, horizon, 4)
    assert meta == []
    assert diagnostics["construction_status"] == "fail_closed"
    assert diagnostics["failure_reason"] == "current_tick_scalar_invalid"
    assert diagnostics["requires_current_tick_scalar_evidence"] is True
    assert diagnostics["current_tick_scalar_evidence"] is False


def test_route_topology_jerk_progress_fails_closed_on_nonfinite_selected_state() -> None:
    horizon = 80
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.8, 80.0, horizon)
    candidates[0, :, 2] = 1.0
    candidates[0, 10, 1] = np.nan
    lane_x = np.linspace(-5.0, 100.0, 106)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red_x = np.linspace(80.0, 84.0, 5)
    red = np.column_stack([red_x, np.zeros_like(red_x)])

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=8.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="lane_projected_jerk_progress_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
        ),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=8.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="lane_projected_jerk_progress_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
        ),
    )

    assert generated.shape == (0, horizon, 4)
    assert meta == []
    assert diagnostics["construction_status"] == "fail_closed"
    assert diagnostics["failure_reason"] == "selected_candidate_state_invalid"
    assert diagnostics["requires_finite_selected_candidate_evidence"] is True
    assert diagnostics["finite_selected_candidate_evidence"] is False


def test_route_topology_generator_returns_empty_without_red_ahead() -> None:
    candidates = np.zeros((1, 20, 4), dtype=float)
    candidates[:, :, 2] = 1.0
    lane_x = np.linspace(0.0, 30.0, 31)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([[-5.0, 0.0]])

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
    )

    assert generated.shape == (0, 20, 4)
    assert meta == []


def test_route_topology_generator_jerk_progress_returns_empty_without_red_ahead() -> None:
    candidates = np.zeros((1, 20, 4), dtype=float)
    candidates[:, :, 2] = 1.0
    lane_x = np.linspace(0.0, 30.0, 31)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([[-5.0, 0.0]])

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="lane_projected_jerk_progress_red_stop"
        ),
    )

    assert generated.shape == (0, 20, 4)
    assert meta == []


def test_route_topology_report_rejects_invalid_lane_projected_offset_scale() -> None:
    with np.testing.assert_raises_regex(
        ValueError,
        "lane_projected_offset_scales must be in \\[0,1\\]",
    ):
        build_report_from_rows(
            [],
            readiness=_readiness_report(),
            config=RouteTopologyCandidateConfig(
                generator_policy="lane_projected_red_stop",
                lane_projected_offset_scales=(1.2,),
            ),
        )


def test_route_topology_report_rejects_invalid_jerk_progress_jerk_limit() -> None:
    with np.testing.assert_raises_regex(
        ValueError,
        "jerk_progress_max_jerk_mps3 must be positive",
    ):
        build_report_from_rows(
            [],
            readiness=_readiness_report(),
            config=RouteTopologyCandidateConfig(
                generator_policy="lane_projected_jerk_progress_red_stop",
                jerk_progress_max_jerk_mps3=0.0,
            ),
        )


def test_route_topology_report_rejects_invalid_remediation_candidate_cap() -> None:
    with np.testing.assert_raises_regex(
        ValueError,
        "max_remediation_candidates must be positive",
    ):
        build_report_from_rows(
            [],
            readiness=_readiness_report(),
            config=RouteTopologyCandidateConfig(
                generator_policy="comfort_first_lane_projected_red_stop",
                max_remediation_candidates=0,
            ),
        )


def test_route_topology_comfort_failure_labels_follow_config_budgets() -> None:
    config = RouteTopologyCandidateConfig(
        progress_loss_budgets_m=(0.25,),
        smoothness_loss_budgets=(0.10,),
        command_jerk_worse_budget_mps3=0.30,
        command_lateral_worse_budget_mps2=0.20,
        rollout_distance_loss_budget_m=0.30,
        rollout_jerk_worse_budget_mps3=0.25,
        rollout_lateral_worse_budget_mps2=0.15,
    )
    tracker_delta = {
        "command_jerk_worse_mps3": 0.31,
        "command_lateral_worse_mps2": 0.21,
        "rollout_distance_loss_m": 0.31,
        "rollout_jerk_worse_mps3": 0.26,
        "rollout_lateral_worse_mps2": 0.16,
    }
    row = {
        "progress_loss_m": 0.30,
        "smoothness_loss": 0.11,
        "tracker_delta": tracker_delta,
    }
    expected = [
        "route_topology_comfort_blocked_progress_loss",
        "route_topology_comfort_blocked_smoothness_loss",
        "route_topology_comfort_blocked_command_jerk",
        "route_topology_comfort_blocked_command_lateral",
        "route_topology_comfort_blocked_rollout_distance",
        "route_topology_comfort_blocked_rollout_jerk",
        "route_topology_comfort_blocked_rollout_lateral",
    ]

    assert _comfort_failure_classes(row, config=config) == expected
    report_row = _candidate_row(comfort=False)
    report_row["progress_loss_m"] = 0.30
    report_row["smoothness_loss"] = 0.11
    report_row["tracker_delta"] = tracker_delta

    report = build_report_from_rows(
        [
            {
                "snapshot_path": "/fake/camp_microbenchmark_step_0001.npz",
                "selection_step": 1,
                "generated_count": 1,
                "timings_ms": {"total": 1.0},
                "candidate_rows": [report_row],
            }
        ],
        readiness=_readiness_report(),
        config=config,
    )

    for failure_class in expected:
        assert report["failure_class_counts"][failure_class] == 1
        assert report["by_snapshot"][0]["failure_class_counts"][failure_class] == 1


def test_route_topology_report_accepts_supported_offline_screen() -> None:
    report = build_report_from_rows(
        [
            {
                "snapshot_path": "/fake/camp_microbenchmark_step_0001.npz",
                "selection_step": 1,
                "generated_count": 1,
                "timings_ms": {"total": 1.0},
                "candidate_rows": [_candidate_row()],
            }
        ],
        readiness=_readiness_report(),
        config=RouteTopologyCandidateConfig(min_snapshot_support_rate=1.0),
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["offline_selector_screen_authorized"] is True
    assert decision["closed_loop_smoke_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert report["records"]["lower_union_red_comfort_admissible_rows"] == 1

    markdown = render_markdown(report)
    assert "Route/Topology Candidate Augmentation Screen" in markdown
    assert "does not run replay" in markdown
    assert "Benders master/subproblem" in markdown


def test_route_topology_report_rejects_without_comfort_support() -> None:
    report = build_report_from_rows(
        [
            {
                "snapshot_path": "/fake/camp_microbenchmark_step_0001.npz",
                "selection_step": 1,
                "generated_count": 1,
                "timings_ms": {"total": 1.0},
                "candidate_rows": [_candidate_row(comfort=False)],
            }
        ],
        readiness=_readiness_report(),
    )

    decision = report["final_decision"]
    assert decision["status"] == REJECT_STATUS
    assert decision["offline_selector_screen_authorized"] is False


def test_route_topology_report_fails_closed_on_readiness_conflict() -> None:
    report = build_report_from_rows(
        [
            {
                "snapshot_path": "/fake/camp_microbenchmark_step_0001.npz",
                "selection_step": 1,
                "generated_count": 1,
                "timings_ms": {"total": 1.0},
                "candidate_rows": [_candidate_row()],
            }
        ],
        readiness=_readiness_report(online_selector_authorized=True),
    )

    decision = report["final_decision"]
    assert decision["status"] == SOURCE_CONFLICT_STATUS
    assert decision["offline_selector_screen_authorized"] is False
    assert decision["source_authorization_conflicts"] == [
        "route_topology_gate:online_selector_authorized"
    ]


def test_route_topology_construction_diagnostics_fail_closed_without_red_ahead() -> None:
    candidates = np.zeros((1, 20, 4), dtype=float)
    candidates[:, :, 2] = 1.0
    lane_x = np.linspace(0.0, 30.0, 31)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([[-5.0, 0.0]])

    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="lane_projected_jerk_progress_red_stop"
        ),
    )
    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="lane_projected_jerk_progress_red_stop"
        ),
    )

    assert diagnostics["construction_status"] == "fail_closed"
    assert diagnostics["failure_reason"] == "red_route_ahead_missing"
    assert diagnostics["red_route_ahead"] is False
    assert diagnostics["candidate_count"] == 1
    assert diagnostics["horizon"] == 20
    assert generated.shape == (0, 20, 4)
    assert meta == []
    for value in diagnostics.values():
        assert value is None or isinstance(value, (str, bool, int, float))


def test_route_topology_zero_candidate_row_carries_construction_diagnostics() -> None:
    diagnostics = {
        "generator_policy": "lane_projected_jerk_progress_red_stop",
        "construction_status": "fail_closed",
        "failure_reason": "red_stop_distance_window",
        "candidate_count": 1,
        "horizon": 20,
        "red_route_ahead": True,
        "feasible_stop_windows": 0,
    }
    row = _snapshot_report_row(
        snapshot_path=__file__,
        arrays={},
        metadata={"selected_index": 0, "selection_step": 1},
        generated_meta=[],
        baseline_scores={
            "union_red_cost": np.asarray([10.0]),
            "reward_breakdowns": [{"progress": 1.0, "smoothness": 0.0}],
        },
        generated_scores=None,
        baseline_tracker={
            "command": {
                "jerk_magnitude_mps3": np.asarray([0.0]),
                "lateral_acceleration_magnitude_mps2": np.asarray([0.0]),
            },
            "open_loop": {
                "horizons": {
                    "3": {
                        "distance_m": np.asarray([1.0]),
                        "max_vector_jerk_mps3": np.asarray([0.0]),
                        "max_lateral_acceleration_mps2": np.asarray([0.0]),
                    }
                }
            },
        },
        generated_tracker=None,
        config=RouteTopologyCandidateConfig(),
        timings_ms={"candidate_build": 0.1, "total": 0.2},
        construction_diagnostics=diagnostics,
    )

    assert row["generated_count"] == 0
    assert row["candidate_rows"] == []
    assert row["candidate_construction_diagnostics"] == diagnostics
    assert "generated_scores" not in row
