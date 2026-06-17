from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_progress_mapping_guard import (
    analyze,
    render_markdown,
)


def test_progress_mapping_guard_reports_false_feasible_route_replacement(
    tmp_path,
) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(
        json.dumps(
            [
                _record(
                    rewards=[
                        _reward(progress=10.0),
                        _reward(progress=7.0),
                        _reward(progress=9.0),
                    ],
                    route_progress=[10.0, 9.0, 9.0],
                    selected_index=1,
                ),
                _record(
                    rewards=[
                        _reward(progress=10.0),
                        _reward(progress=9.0),
                        _reward(progress=8.5, red_light=-1.0),
                    ],
                    route_progress=[10.0, 9.0, 8.5],
                    selected_index=0,
                ),
            ]
        ),
        encoding="utf-8",
    )

    report = analyze(
        [log_path],
        label="unit",
        route_best_ratios=(0.8,),
        route_best_loss_budgets_m=(0.0,),
        candidate0_ratios=(0.95,),
        candidate0_loss_budgets_m=(0.0,),
        max_examples=4,
    )
    plans = {plan["name"]: plan for plan in report["guard_plans"]}

    route_ratio = plans["route_best_ratio_0p8"]
    assert route_ratio["false_feasible_vs_dp_reward"] == 1
    assert route_ratio["false_infeasible_vs_dp_reward"] == 0
    assert route_ratio["selected_candidate_mask_changes"] == 1
    assert route_ratio["acceptability_hint"] == "reject_false_feasible_vs_dp_reward"

    strict_best = plans["route_best_loss_m_0"]
    assert strict_best["false_feasible_vs_dp_reward"] == 0
    assert strict_best["false_infeasible_vs_dp_reward"] == 2
    assert (
        strict_best["acceptability_hint"]
        == "conservative_zero_false_feasible_not_equivalent"
    )

    strict_candidate0 = plans["candidate0_route_ratio_0p95"]
    assert strict_candidate0["false_feasible_vs_dp_reward"] == 0
    assert strict_candidate0["false_infeasible_vs_dp_reward"] == 2

    alignment = report["progress_alignment"]
    assert alignment["route_minus_dp_progress_m"]["max"] == pytest.approx(2.0)
    assert alignment["best_hard_feasible_index_overlap_rate"] == pytest.approx(1.0)
    assert "only_conservative_zero_false_feasible" in report["decision_hint"]

    markdown = render_markdown(report)
    assert "Progress Mapping Guard Audit" in markdown
    assert "route_best_ratio_0p8" in markdown


def _record(
    *,
    rewards: list[dict],
    route_progress: list[float],
    selected_index: int,
) -> dict:
    return {
        "num_candidates": len(rewards),
        "selected_index": selected_index,
        "dp_candidate_rewards": rewards,
        "candidate_route_progress": route_progress,
    }


def _reward(
    *,
    progress: float,
    red_light: float = 0.0,
    lane_crossing: bool = False,
) -> dict:
    return {
        "progress": progress,
        "red_light": red_light,
        "collision_step": None,
        "rb_crossing": False,
        "lane_crossing": lane_crossing,
        "static_crossing": False,
        "kinematic_violated": False,
    }
