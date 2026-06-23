from __future__ import annotations

from scripts.integrations.analyze_diffusion_planner_route_topology_absolute_comfort_guard import (
    AbsoluteComfortGuardConfig,
    READY_STATUS as ABSOLUTE_GUARD_READY_STATUS,
    SOURCE_CONFLICT_STATUS as ABSOLUTE_GUARD_SOURCE_CONFLICT_STATUS,
    build_report_from_rows as build_absolute_guard_report,
)
from scripts.integrations.analyze_diffusion_planner_route_topology_candidate_screen import (
    READINESS_READY,
    READY_STATUS as SCREEN_READY_STATUS,
    REJECT_STATUS as SCREEN_REJECT_STATUS,
    RouteTopologyCandidateConfig,
    _comfort_admissible,
    _comfort_failure_classes,
    _summarize_latency,
    _validate_config,
    build_report_from_rows as build_screen_report,
    render_markdown as render_screen_markdown,
    route_failure_classes,
)


def _zero_tracker_delta() -> dict[str, float]:
    return {
        "command_jerk_worse_mps3": 0.0,
        "command_lateral_worse_mps2": 0.0,
        "rollout_distance_loss_m": 0.0,
        "rollout_jerk_worse_mps3": 0.0,
        "rollout_lateral_worse_mps2": 0.0,
    }


def _readiness_report() -> dict[str, object]:
    return {
        "snapshot_aggregate": {
            "ready_snapshot_rate": 1.0,
            "candidate_lane_p95_max_m": 1.0,
            "red_lane_p95_max_m": 0.0,
        },
        "final_decision": {
            "status": READINESS_READY,
            "offline_candidate_augmentation_screen_authorized": True,
            "online_selector_authorized": False,
            "closed_loop_smoke_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
        },
    }


def _candidate_row(
    *,
    snapshot: int = 1,
    index: int = 0,
    lower: bool = True,
    hard: bool = True,
    progress: bool = True,
    comfort: bool = True,
    hard_reasons: list[str] | None = None,
    progress_loss: float = 0.2,
    smoothness_loss: float = 0.0,
    tracker_delta: dict[str, float] | None = None,
) -> dict[str, object]:
    selected_union = 10.0
    row = {
        "snapshot_path": f"/fake/camp_microbenchmark_step_{snapshot:04d}.npz",
        "selection_step": snapshot,
        "selected_index": 0,
        "candidate_index": index,
        "candidate_meta": {"variant": "lane_projected_jerk_progress_red_stop"},
        "selected_union_red": selected_union,
        "candidate_union_red": 5.0 if lower else 12.0,
        "candidate_near_red": 2.0 if lower else 9.0,
        "candidate_full_red": 3.0 if lower else 10.0,
        "lower_union_red": lower,
        "hard_feasible": hard,
        "hard_reasons": [] if hard else list(hard_reasons or ["dp_red_light"]),
        "progress_feasible": progress,
        "progress_reasons": [] if progress else ["dp_underprogress"],
        "progress_loss_m": progress_loss,
        "smoothness_loss": smoothness_loss,
        "tracker_delta": tracker_delta or _zero_tracker_delta(),
        "comfort_admissible": comfort,
    }
    row["failure_classes"] = route_failure_classes(row)
    return row


def _screen_row(
    snapshot: int,
    candidates: list[dict[str, object]],
    *,
    timings: dict[str, float] | None = None,
) -> dict[str, object]:
    return {
        "snapshot_path": f"/fake/camp_microbenchmark_step_{snapshot:04d}.npz",
        "selection_step": snapshot,
        "selected_index": 0,
        "generated_count": len(candidates),
        "selected_union_red": 10.0,
        "candidate_construction_diagnostics": {},
        "candidate_rows": candidates,
        "timings_ms": timings
        or {
            "baseline_reward": 1.0,
            "baseline_tracker": 2.0,
            "candidate_build": 3.0,
            "generated_reward": 4.0,
            "generated_tracker": 5.0,
            "total": 6.0,
        },
    }


def _source_screen_for_absolute_guard(
    *,
    status: str = SCREEN_REJECT_STATUS,
    offline_selector_screen_authorized: bool = False,
) -> dict[str, object]:
    return {
        "analysis": {"name": "dp_camp_route_topology_candidate_screen_v1"},
        "support_gate": {
            "hard_feasible_snapshot_support_rate": 0.0,
            "comfort_admissible_snapshot_support_rate": 0.0,
        },
        "final_decision": {
            "status": status,
            "offline_selector_screen_authorized": offline_selector_screen_authorized,
            "closed_loop_smoke_authorized": False,
            "online_selector_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
        },
    }


def _absolute_guard_row(
    *,
    pass_guard: bool = True,
    relative_comfort: bool = False,
) -> dict[str, object]:
    command_lateral = 1.0 if pass_guard else 3.0
    rollout_lateral = 1.0 if pass_guard else 3.0
    return {
        "snapshot_path": "/fake/camp_microbenchmark_step_0001.npz",
        "selection_step": 1,
        "candidate_index": 0,
        "candidate_meta": {"variant": "lane_projected_jerk_progress_red_stop"},
        "lower_union_red": True,
        "hard_feasible": True,
        "hard_reasons": [],
        "progress_feasible": True,
        "progress_loss_m": 0.2,
        "smoothness_loss": 0.0,
        "relative_comfort_admissible": relative_comfort,
        "selected_tracker": {
            "command_lateral_mps2": 1.0,
            "rollout_lateral_mps2": 1.0,
        },
        "candidate_tracker": {
            "command_jerk_mps3": 12.0,
            "command_lateral_mps2": command_lateral,
            "rollout_distance_m": 2.0,
            "rollout_jerk_mps3": 12.0,
            "rollout_lateral_mps2": rollout_lateral,
        },
        "absolute_lateral_guard_pass": pass_guard,
        "failure_classes": (
            ["absolute_lateral_guard_support"]
            if pass_guard
            else ["absolute_command_lateral_guard_failed"]
        ),
    }


def test_fixed_snapshot_relative_comfort_requires_prereqs_and_current_budgets() -> None:
    config = RouteTopologyCandidateConfig()

    assert _comfort_admissible(
        progress_loss=0.2,
        smoothness_loss=0.0,
        tracker_delta=_zero_tracker_delta(),
        lower_union_red=True,
        hard_feasible=True,
        progress_feasible=True,
        config=config,
    )

    for kwargs in (
        {"lower_union_red": False, "hard_feasible": True, "progress_feasible": True},
        {"lower_union_red": True, "hard_feasible": False, "progress_feasible": True},
        {"lower_union_red": True, "hard_feasible": True, "progress_feasible": False},
    ):
        assert not _comfort_admissible(
            progress_loss=0.2,
            smoothness_loss=0.0,
            tracker_delta=_zero_tracker_delta(),
            config=config,
            **kwargs,
        )

    tracker_delta = _zero_tracker_delta()
    tracker_delta["rollout_distance_loss_m"] = config.rollout_distance_loss_budget_m + 0.1
    assert not _comfort_admissible(
        progress_loss=0.2,
        smoothness_loss=0.0,
        tracker_delta=tracker_delta,
        lower_union_red=True,
        hard_feasible=True,
        progress_feasible=True,
        config=config,
    )


def test_fixed_snapshot_comfort_failure_labels_cover_budget_families() -> None:
    row = {
        "progress_loss_m": 2.0,
        "smoothness_loss": 1.5,
        "tracker_delta": {
            "command_jerk_worse_mps3": 0.2,
            "command_lateral_worse_mps2": 0.2,
            "rollout_distance_loss_m": 0.2,
            "rollout_jerk_worse_mps3": 0.2,
            "rollout_lateral_worse_mps2": 0.2,
        },
    }

    assert _comfort_failure_classes(row) == [
        "route_topology_comfort_blocked_progress_loss",
        "route_topology_comfort_blocked_smoothness_loss",
        "route_topology_comfort_blocked_command_jerk",
        "route_topology_comfort_blocked_command_lateral",
        "route_topology_comfort_blocked_rollout_distance",
        "route_topology_comfort_blocked_rollout_jerk",
        "route_topology_comfort_blocked_rollout_lateral",
    ]


def test_fixed_snapshot_report_separates_hard_underprogress_and_comfort() -> None:
    rows = [
        _screen_row(
            1,
            [
                _candidate_row(
                    index=0,
                    hard=False,
                    progress=False,
                    comfort=False,
                    hard_reasons=["dp_lane_crossing", "dp_red_light"],
                ),
                _candidate_row(index=1, progress=False, comfort=False),
                _candidate_row(
                    index=2,
                    comfort=False,
                    progress_loss=2.0,
                ),
                _candidate_row(index=3, comfort=True),
            ],
        )
    ]

    report = build_screen_report(
        rows,
        readiness=_readiness_report(),
        config=RouteTopologyCandidateConfig(min_snapshot_support_rate=1.0),
    )

    assert report["records"]["lower_union_red_rows"] == 4
    assert report["records"]["lower_union_red_hard_feasible_rows"] == 3
    assert report["records"]["lower_union_red_progress_feasible_rows"] == 2
    assert report["records"]["lower_union_red_comfort_admissible_rows"] == 1
    assert report["hard_reason_counts"] == {
        "dp_lane_crossing": 1,
        "dp_red_light": 1,
    }
    assert report["failure_class_counts"][
        "route_topology_hard_feasible_but_underprogress"
    ] == 1
    assert report["failure_class_counts"][
        "route_topology_comfort_blocked_progress_loss"
    ] == 1
    assert report["final_decision"]["status"] == SCREEN_READY_STATUS
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False
    assert report["final_decision"]["online_selector_authorized"] is False


def test_fixed_snapshot_latency_remains_diagnostic_with_candidate_build_and_total() -> None:
    rows = [
        _screen_row(
            1,
            [_candidate_row(snapshot=1)],
            timings={
                "baseline_reward": 1.0,
                "baseline_tracker": 2.0,
                "candidate_build": 3.0,
                "generated_reward": 4.0,
                "generated_tracker": 5.0,
                "total": 6.0,
            },
        ),
        _screen_row(
            2,
            [_candidate_row(snapshot=2)],
            timings={
                "baseline_reward": 2.0,
                "baseline_tracker": 3.0,
                "candidate_build": 5.0,
                "generated_reward": 6.0,
                "generated_tracker": 7.0,
                "total": 10.0,
            },
        ),
    ]

    latency = _summarize_latency(rows)

    assert latency["candidate_build"]["count"] == 2
    assert latency["candidate_build"]["p50"] == 4.0
    assert latency["total"]["count"] == 2
    assert latency["total"]["p50"] == 8.0


def test_fixed_snapshot_absolute_guard_subset_is_diagnostic_not_promotion() -> None:
    report = build_absolute_guard_report(
        [_absolute_guard_row(pass_guard=True, relative_comfort=False)],
        screen=_source_screen_for_absolute_guard(),
        config=AbsoluteComfortGuardConfig(
            max_command_lateral_mps2=2.0,
            max_rollout_lateral_mps2=2.0,
            min_snapshot_support_rate=1.0,
        ),
    )

    assert report["records"]["absolute_lateral_guard_rows"] == 1
    assert report["support_gate"]["absolute_lateral_guard_snapshot_support_pass"]
    assert report["final_decision"]["status"] == ABSOLUTE_GUARD_READY_STATUS
    assert report["analysis"]["diffusion_planner_execution"] is False
    assert report["analysis"]["selection_effect"] is False
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False
    assert report["final_decision"]["dp_modification_authorized"] is False


def test_fixed_snapshot_absolute_guard_rejects_source_authorization_leak() -> None:
    report = build_absolute_guard_report(
        [_absolute_guard_row(pass_guard=True)],
        screen=_source_screen_for_absolute_guard(
            status=SCREEN_READY_STATUS,
            offline_selector_screen_authorized=True,
        ),
        config=AbsoluteComfortGuardConfig(
            max_command_lateral_mps2=2.0,
            max_rollout_lateral_mps2=2.0,
            min_snapshot_support_rate=1.0,
        ),
    )

    assert report["final_decision"]["status"] == ABSOLUTE_GUARD_SOURCE_CONFLICT_STATUS
    assert "source_screen:not_rejected" in report["source_authorization_conflicts"]
    assert (
        "source_screen:offline_selector_screen_authorized"
        in report["source_authorization_conflicts"]
    )
    assert report["final_decision"]["online_selector_authorized"] is False


def test_fixed_snapshot_default_policy_remains_default_off_and_opt_in_validates() -> None:
    default = RouteTopologyCandidateConfig()
    opt_in = RouteTopologyCandidateConfig(
        generator_policy="lane_projected_jerk_progress_red_stop",
        jerk_progress_max_jerk_mps3=8.0,
    )

    assert default.generator_policy == "lane_centerline_red_stop"
    assert default.generator_policy != opt_in.generator_policy
    _validate_config(default)
    _validate_config(opt_in)


def test_fixed_snapshot_math_boundary_keeps_fixed_affine_candidate_contract() -> None:
    report = build_screen_report(
        [_screen_row(1, [_candidate_row()])],
        readiness=_readiness_report(),
        config=RouteTopologyCandidateConfig(min_snapshot_support_rate=1.0),
    )
    boundary = report["analysis"]["math_boundary"]

    assert report["analysis"]["training"] is False
    assert report["analysis"]["online_selector_change"] is False
    assert report["analysis"]["uses_outcome_labels"] is False
    assert report["analysis"]["future_outcome_leakage"] is False
    assert "a_k^T w" in boundary
    assert "simplex/CVaR/L2 robust master remains convex" in boundary
    assert "does not modify DP" in boundary
    assert "Benders master/subproblem" in boundary


def test_fixed_snapshot_markdown_keeps_no_replay_and_no_training_boundaries() -> None:
    report = build_screen_report(
        [_screen_row(1, [_candidate_row()])],
        readiness=_readiness_report(),
        config=RouteTopologyCandidateConfig(min_snapshot_support_rate=1.0),
    )
    markdown = render_screen_markdown(report)

    assert "Closed-loop smoke authorized: `False`" in markdown
    assert "CAMP retraining authorized: `False`" in markdown
    assert "Mathematical Boundary" in markdown
    assert "does not modify DP" in markdown
