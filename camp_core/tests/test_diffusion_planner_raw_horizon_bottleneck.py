from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_raw_horizon_bottleneck import (
    BudgetScreen,
    analyze,
    render_markdown,
)


def _prefix(end_x: float, end_y: float, steps: int = 4) -> list[list[float]]:
    rows = []
    for step in range(steps):
        ratio = float(step + 1) / float(steps)
        rows.append([end_x * ratio, end_y * ratio, 0.0, 1.0])
    return rows


def _rollout(values: list[float]) -> dict:
    return {
        str(horizon): {
            "distance_m": values,
            "mean_vector_jerk_mps3": [10.0, 8.0, 12.0],
            "max_lateral_acceleration_mps2": [0.5, 0.6, 0.7],
        }
        for horizon in (3, 10)
    }


def _record() -> dict:
    return {
        "num_candidates": 3,
        "selected_index": 0,
        "feasible_mask": [True, True, False],
        "candidate_raw_trajectory_prefix": [
            _prefix(8.0, 0.0),
            _prefix(8.0, 1.0),
            _prefix(8.0, -2.0),
        ],
        "candidate_planned_red_light_cost": [0.0, 0.0, 0.0],
        "candidate_full_horizon_planned_red_light_cost": [10.0, 5.0, 0.0],
        "candidate_horizon_union_planned_red_light_cost": [10.0, 5.0, 0.0],
        "candidate_route_progress": None,
        "dp_candidate_rewards": [
            {"progress": 10.0},
            {"progress": 9.8},
            {"progress": 9.7},
        ],
        "candidate_perfect_tracker_target_speed_mps": [4.0, 3.95, 3.90],
        "candidate_perfect_tracker_open_loop_rollout": _rollout([6.0, 5.95, 5.80]),
    }


def test_raw_horizon_bottleneck_reports_budgeted_lower_red_masks(tmp_path) -> None:
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps([_record()]), encoding="utf-8")
    report = analyze(
        [path],
        horizon=4,
        mode_threshold_m=0.5,
        screens=(
            BudgetScreen(
                name="unit",
                progress_loss_budget_m=0.25,
                target_speed_loss_budget_mps=0.1,
                h10_distance_loss_budget_m=0.1,
                h3_max_lateral_limit_mps2=2.0,
            ),
        ),
    )

    group = report["groups"]["selected_h30_safe_full_red=true"]
    assert group["records"] == 1
    assert group["masks"]["lower_red_any"]["candidate_count"]["mean"] == 2.0
    assert group["masks"]["lower_red_base_feasible"]["candidate_count"]["mean"] == 1.0
    assert group["masks"]["lower_red_base_feasible"]["selected_distance_mean_m"][
        "mean"
    ] == pytest.approx(1.0)

    budget = group["budget_masks"]["unit"]
    assert budget["lower_red_budget"]["candidate_count"]["mean"] == 1.0
    assert (
        budget["lower_red_budget_jerk_nondegrading"]["candidate_count"]["mean"]
        == 1.0
    )
    blockers = group["budget_blockers"]["unit"]
    assert blockers["with_lower_red_base_feasible"]["count"] == 1
    assert blockers["with_bounded"]["count"] == 1
    assert blockers["with_bounded_jerk_nondegrading"]["count"] == 1
    assert blockers["progress_blocks_all"]["count"] == 0
    assert blockers["min_progress_loss_m"]["median"] == pytest.approx(0.2)
    assert blockers["min_h10_distance_loss_m"]["median"] == pytest.approx(0.05)
    assert report["events"]["selected_h30_safe_full_red"] == 1
    assert not report["analysis"]["uses_outcome_labels"]

    markdown = render_markdown(report)
    assert "Raw Horizon Candidate-Set Bottleneck Audit" in markdown
    assert "selected_h30_safe_full_red=true" in markdown
    assert "Budget Blockers" in markdown


def test_raw_horizon_bottleneck_rejects_unlogged_horizon(tmp_path) -> None:
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps([_record()]), encoding="utf-8")

    with pytest.raises(ValueError, match="exceeds logged raw prefix length"):
        analyze([path], horizon=5)
