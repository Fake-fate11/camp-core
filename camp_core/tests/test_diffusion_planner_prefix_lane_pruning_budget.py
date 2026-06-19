from __future__ import annotations

from scripts.integrations.analyze_diffusion_planner_prefix_lane_pruning_budget import (
    READY_STATUS,
    SOURCE_CONFLICT_STATUS,
    build_report,
    render_markdown,
)


def _candidate(
    *,
    index: int,
    prefix: int,
    margin: float,
    offset: float,
    progress_loss: float,
    absolute_pass: bool = True,
    hard: bool = True,
    progress: bool = True,
) -> dict[str, object]:
    return {
        "snapshot_path": f"/fake/step_{index // 10}.npz",
        "selection_step": index // 10,
        "candidate_index": index,
        "candidate_meta": {
            "variant": "prefix_lane_projected_red_stop",
            "prefix_steps": prefix,
            "bridge_steps": 10,
            "red_stop_margin_m": margin,
            "backup_stop_offset_m": 1.0,
            "lateral_offset_scale": offset,
        },
        "lower_union_red": True,
        "hard_feasible": hard,
        "hard_reasons": [] if hard else ["dp_lane_crossing"],
        "progress_feasible": progress,
        "comfort_admissible": False,
        "progress_loss_m": progress_loss,
        "smoothness_loss": 1.0,
        "tracker_delta": {
            "command_jerk_worse_mps3": 0.0,
            "command_lateral_worse_mps2": 0.1,
            "rollout_distance_loss_m": 0.0,
            "rollout_jerk_worse_mps3": 0.0,
            "rollout_lateral_worse_mps2": 0.1,
        },
        "failure_classes": ["route_topology_comfort_blocked_progress_loss"],
        "_absolute_pass": absolute_pass,
    }


def _screen(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "analysis": {"name": "dp_camp_route_topology_candidate_screen_v1"},
        "config": {"generator_policy": "prefix_lane_projected_red_stop"},
        "records": {
            "generated_candidate_rows": len(rows),
            "lower_union_red_hard_feasible_rows": len(rows),
            "lower_union_red_progress_feasible_rows": len(rows),
            "lower_union_red_comfort_admissible_rows": 0,
        },
        "support_gate": {
            "hard_feasible_snapshot_support_rate": 1.0,
            "comfort_admissible_snapshot_support_rate": 0.0,
        },
        "final_decision": {
            "status": "route_topology_candidate_support_insufficient",
            "closed_loop_smoke_authorized": False,
            "online_selector_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
        },
        "rows": [
            {
                "snapshot_path": "/fake/screen_row.npz",
                "selection_step": 0,
                "candidate_rows": [
                    {key: value for key, value in row.items() if key != "_absolute_pass"}
                    for row in rows
                ],
            }
        ],
    }


def _absolute(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "analysis": {"name": "dp_camp_route_topology_absolute_lateral_guard_v1"},
        "final_decision": {
            "status": "route_topology_absolute_lateral_guard_support_present",
            "closed_loop_smoke_authorized": False,
            "online_selector_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
        },
        "records": {"absolute_lateral_guard_rows": 2},
        "support_gate": {"absolute_lateral_guard_snapshot_support_rate": 1.0},
        "rows": [
            {
                "snapshot_path": row["snapshot_path"],
                "candidate_index": row["candidate_index"],
                "absolute_lateral_guard_pass": row["_absolute_pass"],
                "candidate_tracker": {
                    "command_jerk_mps3": 5.0,
                    "command_lateral_mps2": 0.5,
                    "rollout_jerk_mps3": 10.0,
                    "rollout_lateral_mps2": 0.6,
                },
            }
            for row in rows
        ],
    }


def test_prefix_lane_pruning_budget_finds_small_supported_subset() -> None:
    rows = [
        _candidate(index=10, prefix=3, margin=2.0, offset=1.0, progress_loss=1.5),
        _candidate(index=20, prefix=3, margin=2.0, offset=0.5, progress_loss=2.5),
        _candidate(index=30, prefix=5, margin=4.0, offset=0.0, progress_loss=5.0),
    ]

    report = build_report(screen=_screen(rows), absolute=_absolute(rows), label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False
    target = next(
        row
        for row in report["budget_sensitivity"]
        if row["subset"] == "prefix3_margin2_offset1"
        and row["progress_loss_budget_m"] == 2.0
    )
    assert target["support_pass"] is True
    assert target["budget_support_snapshots"] == 1
    assert target["candidate_fraction_pass"] is True

    markdown = render_markdown(report)
    assert "read-only fixed-artifact diagnostic" in markdown
    assert "Benders master/subproblem" in markdown


def test_prefix_lane_pruning_budget_fails_closed_on_source_conflict() -> None:
    rows = [
        _candidate(index=10, prefix=3, margin=2.0, offset=1.0, progress_loss=1.5)
    ]
    screen = _screen(rows)
    screen["config"]["generator_policy"] = "lane_projected_red_stop"

    report = build_report(screen=screen, absolute=_absolute(rows))

    assert report["final_decision"]["status"] == SOURCE_CONFLICT_STATUS
    assert report["final_decision"]["source_authorization_conflicts"] == [
        "screen:not_prefix_lane_projected"
    ]
