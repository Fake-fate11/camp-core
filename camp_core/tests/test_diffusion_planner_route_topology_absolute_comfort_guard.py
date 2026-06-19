from __future__ import annotations

from scripts.integrations.analyze_diffusion_planner_route_topology_absolute_comfort_guard import (
    READY_STATUS,
    REJECT_STATUS,
    SOURCE_CONFLICT_STATUS,
    AbsoluteComfortGuardConfig,
    build_report_from_rows,
    render_markdown,
)


def _screen_report(*, full36_authorized: bool = False) -> dict[str, object]:
    return {
        "analysis": {"name": "dp_camp_route_topology_candidate_screen_v1"},
        "support_gate": {
            "hard_feasible_snapshot_support_rate": 0.1,
            "comfort_admissible_snapshot_support_rate": 0.0,
        },
        "final_decision": {
            "status": "route_topology_candidate_support_insufficient",
            "offline_selector_screen_authorized": False,
            "closed_loop_smoke_authorized": False,
            "online_selector_authorized": False,
            "full36_authorized": full36_authorized,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
        },
    }


def _row(
    *,
    command_lateral: float = 1.2,
    rollout_lateral: float = 1.4,
    lower: bool = True,
    hard: bool = True,
    progress: bool = True,
    relative_comfort: bool = False,
) -> dict[str, object]:
    return {
        "snapshot_path": "/fake/camp_microbenchmark_step_0001.npz",
        "selection_step": 1,
        "candidate_index": 0,
        "candidate_meta": {"variant": "prefix_comfort_red_stop"},
        "lower_union_red": lower,
        "hard_feasible": hard,
        "hard_reasons": [] if hard else ["dp_lane_crossing"],
        "progress_feasible": progress,
        "progress_loss_m": 1.2,
        "smoothness_loss": 0.2,
        "relative_comfort_admissible": relative_comfort,
        "selected_tracker": {
            "command_jerk_mps3": 0.5,
            "command_lateral_mps2": 0.4,
            "rollout_distance_m": 3.0,
            "rollout_jerk_mps3": 1.0,
            "rollout_lateral_mps2": 0.5,
        },
        "candidate_tracker": {
            "command_jerk_mps3": 4.0,
            "command_lateral_mps2": command_lateral,
            "rollout_distance_m": 2.9,
            "rollout_jerk_mps3": 5.0,
            "rollout_lateral_mps2": rollout_lateral,
        },
        "absolute_lateral_guard_pass": bool(
            lower and hard and progress and command_lateral <= 2.0 and rollout_lateral <= 2.0
        ),
        "failure_classes": (
            ["absolute_lateral_guard_support"]
            if command_lateral <= 2.0 and rollout_lateral <= 2.0
            else ["absolute_rollout_lateral_guard_failed"]
        ),
    }


def test_absolute_guard_audit_finds_support_despite_relative_reject() -> None:
    report = build_report_from_rows(
        [_row(relative_comfort=False)],
        screen=_screen_report(),
        config=AbsoluteComfortGuardConfig(
            max_command_lateral_mps2=2.0,
            max_rollout_lateral_mps2=2.0,
            min_snapshot_support_rate=1.0,
        ),
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["closed_loop_smoke_authorized"] is False
    assert report["records"]["absolute_lateral_guard_rows"] == 1
    assert report["support_gate"]["absolute_lateral_guard_snapshot_support_rate"] == 1.0

    markdown = render_markdown(report)
    assert "Absolute Lateral Guard" in markdown
    assert "does not run DP reward" in markdown
    assert "Benders" in markdown


def test_absolute_guard_audit_rejects_when_absolute_lateral_fails() -> None:
    report = build_report_from_rows(
        [_row(command_lateral=1.0, rollout_lateral=2.5)],
        screen=_screen_report(),
        config=AbsoluteComfortGuardConfig(
            max_command_lateral_mps2=2.0,
            max_rollout_lateral_mps2=2.0,
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["records"]["absolute_lateral_guard_rows"] == 0
    assert report["failure_class_counts"] == {
        "absolute_rollout_lateral_guard_failed": 1
    }


def test_absolute_guard_audit_fails_closed_on_source_conflict() -> None:
    report = build_report_from_rows(
        [_row()],
        screen=_screen_report(full36_authorized=True),
        config=AbsoluteComfortGuardConfig(
            max_command_lateral_mps2=2.0,
            max_rollout_lateral_mps2=2.0,
        ),
    )

    decision = report["final_decision"]
    assert decision["status"] == SOURCE_CONFLICT_STATUS
    assert decision["source_authorization_conflicts"] == [
        "source_screen:full36_authorized"
    ]
