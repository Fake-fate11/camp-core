from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_reward_replacement_plan import (
    analyze,
    render_markdown,
)


def test_reward_replacement_plan_reports_mask_and_latency_tradeoffs(tmp_path) -> None:
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
                    full_red=[0.0, 0.0, 0.0],
                    union_red=[0.0, 0.0, 0.0],
                    total_latency=100.0,
                    reward_batch=14.0,
                    route_latency=6.0,
                    sg_latency=5.0,
                ),
                _record(
                    rewards=[
                        _reward(progress=10.0),
                        _reward(progress=9.0, red_light=-1.0),
                        _reward(progress=8.5),
                    ],
                    route_progress=[10.0, 9.0, 8.5],
                    full_red=[0.0, 0.0, 0.0],
                    union_red=[0.0, 1.0, 0.0],
                    total_latency=120.0,
                    reward_batch=20.0,
                    route_latency=8.0,
                    sg_latency=6.0,
                ),
            ]
        ),
        encoding="utf-8",
    )

    report = analyze([log_path], label="unit", max_examples=4)
    plans = {plan["name"]: plan for plan in report["mask_plans"]}

    route_plan = plans["route_progress_underprogress"]
    assert route_plan["false_feasible_vs_dp_reward"] == 1
    assert route_plan["false_infeasible_vs_dp_reward"] == 0
    assert route_plan["acceptability_hint"] == "not_equivalent_to_dp_reward_baseline"

    full_red_plan = plans["full_red_hard_dp_progress"]
    assert full_red_plan["false_feasible_vs_dp_reward"] == 1
    assert full_red_plan["candidate_mismatches"] == 1

    union_plan = plans["union_red_route_progress_diagnostic"]
    assert union_plan["false_feasible_vs_dp_reward"] == 1
    assert union_plan["false_infeasible_vs_dp_reward"] == 0

    latency_plan = report["latency"]["hypothetical_plans"][
        "batch_plus_route_progress_plus_sg"
    ]
    assert latency_plan["p95_if_removed_ms"] == pytest.approx(85.45)
    assert latency_plan["p95_reduction_ms"] == pytest.approx(33.55)

    progress_delta = report["progress_alignment"]["route_minus_dp_progress_m"]
    assert progress_delta["max"] == pytest.approx(2.0)
    assert "reject_direct_reward_replacement" in report["decision_hint"]

    markdown = render_markdown(report)
    assert "Reward Replacement Plan Audit" in markdown
    assert "route_progress_underprogress" in markdown


def _record(
    *,
    rewards: list[dict],
    route_progress: list[float],
    full_red: list[float],
    union_red: list[float],
    total_latency: float,
    reward_batch: float,
    route_latency: float,
    sg_latency: float,
) -> dict:
    return {
        "num_candidates": len(rewards),
        "selected_index": 0,
        "feasible_mask": [True] * len(rewards),
        "dp_candidate_rewards": rewards,
        "candidate_route_progress": route_progress,
        "candidate_full_horizon_planned_red_light_cost": full_red,
        "candidate_horizon_union_planned_red_light_cost": union_red,
        "latency_ms_including_candidate_generation": total_latency,
        "latency_ms_reward_scoring": 30.0,
        "latency_ms_reward_batch_compute": reward_batch,
        "latency_ms_reward_route_progress": route_latency,
        "latency_ms_reward_sg_smoothing": sg_latency,
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
