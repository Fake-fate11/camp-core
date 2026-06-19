from __future__ import annotations

import numpy as np

from scripts.integrations.analyze_diffusion_planner_route_topology_candidate_screen import (
    READY_STATUS,
    REJECT_STATUS,
    SOURCE_CONFLICT_STATUS,
    RouteTopologyCandidateConfig,
    build_report_from_rows,
    build_route_topology_candidates,
    render_markdown,
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
