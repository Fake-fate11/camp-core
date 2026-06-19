from __future__ import annotations

from scripts.integrations.analyze_diffusion_planner_source_donor_support_gate import (
    READY_STATUS,
    REJECT_STATUS,
    SourceDonorSupportConfig,
    build_report_from_source_rows,
    render_markdown,
    source_failure_classes,
)


def _row(
    *,
    snapshot: str,
    lower: bool = True,
    hard: bool = False,
    progress: bool = False,
    comfort: bool = False,
    reasons: list[str] | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "snapshot_path": snapshot,
        "selection_step": 1,
        "selected_index": 0,
        "candidate_index": 1,
        "selected_union_red": 10.0,
        "candidate_union_red": 0.0 if lower else 12.0,
        "candidate_near_red": 0.0,
        "candidate_full_red": 0.0 if lower else 12.0,
        "lower_union_red": lower,
        "hard_feasible": hard,
        "hard_reasons": [] if reasons is None else reasons,
        "progress_feasible": progress,
        "progress_reasons": [] if progress else ["dp_underprogress"],
        "progress_loss_m": 0.0,
        "smoothness_loss": 0.0,
        "tracker_delta": {
            "command_jerk_worse_mps3": 0.0,
            "command_lateral_worse_mps2": 0.0,
            "rollout_distance_loss_m": 0.0,
            "rollout_jerk_worse_mps3": 0.0,
            "rollout_lateral_worse_mps2": 0.0,
        },
        "comfort_admissible": comfort,
    }
    row["failure_classes"] = source_failure_classes(row)
    return row


def test_source_failure_classes_identify_lane_and_red_invalidity() -> None:
    row = _row(
        snapshot="s1",
        reasons=["dp_lane_crossing", "dp_red_light", "dp_kinematic"],
    )

    assert row["failure_classes"] == [
        "source_lane_invalid",
        "source_red_timing_invalid",
        "source_dp_kinematic",
    ]


def test_report_rejects_when_existing_pool_lacks_source_support() -> None:
    report = build_report_from_source_rows(
        [
            _row(snapshot="s1", reasons=["dp_lane_crossing"]),
            _row(snapshot="s2", reasons=["dp_red_light"]),
            _row(snapshot="s3", lower=False),
        ],
        config=SourceDonorSupportConfig(min_snapshot_support_rate=0.25),
        label="unit",
    )

    assert report["records"]["lower_union_red_rows"] == 2
    assert report["support_gate"]["hard_feasible_snapshot_support_rate"] == 0.0
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["online_selector_authorized"] is False
    assert "candidate-generation support" in report["final_decision"]["next_step"]


def test_report_accepts_only_when_hard_and_comfort_snapshot_support_pass() -> None:
    report = build_report_from_source_rows(
        [
            _row(snapshot="s1", hard=True, progress=True, comfort=True),
            _row(snapshot="s2", hard=True, progress=True, comfort=True),
            _row(snapshot="s3", reasons=["dp_red_light"]),
            _row(snapshot="s4", reasons=["dp_lane_crossing"]),
        ],
        config=SourceDonorSupportConfig(min_snapshot_support_rate=0.50),
        label="unit",
    )

    assert report["support_gate"]["hard_feasible_snapshot_support_rate"] == 0.5
    assert report["support_gate"]["comfort_admissible_snapshot_support_rate"] == 0.5
    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["full36_authorized"] is False


def test_render_markdown_preserves_math_boundary_and_blocks_replay() -> None:
    report = build_report_from_source_rows(
        [_row(snapshot="s1", reasons=["dp_red_light"])],
        label="markdown",
    )

    markdown = render_markdown(report)

    assert "does not run replay" in markdown
    assert "Online selector authorized: `False`" in markdown
    assert "Benders" in markdown
