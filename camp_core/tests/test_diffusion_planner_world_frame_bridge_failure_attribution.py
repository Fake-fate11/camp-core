from __future__ import annotations

from scripts.integrations.analyze_diffusion_planner_world_frame_bridge_failure_attribution import (
    STATUS_REJECTED,
    build_report_from_candidate_rows,
    candidate_failure_classes,
    render_markdown,
    sg_effect_classes,
)


def _row(**updates: object) -> dict[str, object]:
    row: dict[str, object] = {
        "snapshot_path": "/tmp/camp_microbenchmark_step_0001.npz",
        "selection_step": 1,
        "selected_index": 0,
        "donor_index": 1,
        "transformed_index": 0,
        "selected_union_red": 10.0,
        "source_donor_union_red": 0.0,
        "transformed_union_red": 0.0,
        "transformed_near_red": 0.0,
        "transformed_full_red": 0.0,
        "transformed_no_sg_union_red": 0.0,
        "lower_union_red": True,
        "source_donor_hard_feasible": False,
        "source_donor_hard_reasons": ["dp_lane_crossing"],
        "transformed_hard_feasible": False,
        "transformed_hard_reasons": ["dp_lane_crossing"],
        "transformed_no_sg_hard_feasible": False,
        "transformed_no_sg_hard_reasons": ["dp_lane_crossing"],
        "progress_feasible": False,
        "progress_reasons": [],
        "progress_loss_m": 0.0,
        "smoothness_loss": 0.0,
        "tracker_delta": {
            "command_jerk_worse_mps3": 0.0,
            "command_lateral_worse_mps2": 0.0,
            "rollout_distance_loss_m": 0.0,
            "rollout_jerk_worse_mps3": 0.0,
            "rollout_lateral_worse_mps2": 0.0,
        },
        "comfort_admissible": False,
    }
    row.update(updates)
    row["failure_classes"] = candidate_failure_classes(row)
    row["sg_effect_classes"] = sg_effect_classes(row)
    return row


def test_candidate_failure_classes_separate_source_and_introduced_lane_red() -> None:
    source = _row(
        source_donor_hard_reasons=["dp_lane_crossing", "dp_red_light"],
        transformed_hard_reasons=["dp_lane_crossing", "dp_red_light"],
    )
    introduced = _row(
        source_donor_hard_feasible=True,
        source_donor_hard_reasons=[],
        transformed_hard_reasons=["dp_lane_crossing", "dp_red_light"],
    )

    assert source["failure_classes"] == [
        "source_donor_lane_invalid",
        "source_donor_red_timing_invalid",
    ]
    assert introduced["failure_classes"] == [
        "bridge_or_sg_introduced_lane_invalid",
        "bridge_or_sg_introduced_red_invalid",
    ]


def test_sg_effect_classes_detect_sg_introduced_hard_failure() -> None:
    row = _row(
        source_donor_hard_feasible=True,
        source_donor_hard_reasons=[],
        transformed_hard_reasons=["dp_red_light"],
        transformed_no_sg_hard_feasible=True,
        transformed_no_sg_hard_reasons=[],
    )

    assert row["sg_effect_classes"] == [
        "sg_introduced_dp_red_light",
        "sg_changed_hard_feasible_to_infeasible",
    ]


def test_build_report_rejects_when_source_donor_invalid_dominates() -> None:
    rows = [
        _row(selection_step=1, donor_index=1),
        _row(selection_step=2, donor_index=2),
        _row(
            selection_step=3,
            donor_index=3,
            source_donor_hard_feasible=True,
            source_donor_hard_reasons=[],
            transformed_hard_reasons=["dp_red_light"],
        ),
    ]

    report = build_report_from_candidate_rows(
        rows,
        screen={
            "final_decision": {
                "status": "world_frame_bridge_offline_support_insufficient",
            },
            "support_gate": {
                "hard_feasible_snapshot_support_rate": 0.01,
                "comfort_admissible_snapshot_support_rate": 0.0,
                "min_snapshot_support_rate": 0.25,
            },
        },
        label="unit",
    )

    assert report["records"]["lower_union_red_rows"] == 3
    assert report["failure_class_counts"]["source_donor_lane_invalid"] == 2
    assert report["failure_class_counts"]["bridge_or_sg_introduced_red_invalid"] == 1
    assert report["final_decision"]["status"] == STATUS_REJECTED
    assert report["final_decision"]["online_selector_authorized"] is False
    assert "lane-constrained donor search" in report["final_decision"]["next_step"]


def test_render_markdown_reports_boundary_and_blocked_actions() -> None:
    report = build_report_from_candidate_rows([_row()], label="markdown")

    markdown = render_markdown(report)

    assert "not replay" in markdown
    assert "Online selector authorized: `False`" in markdown
    assert "Benders" in markdown
