from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_deployable_static_failure import (
    analyze,
    render_markdown,
)


def _record(
    *,
    selected_index: int,
    feasible_mask: list[bool],
    route_progress: list[float],
    tracker_jerk: list[float],
    reasons: list[list[str]],
) -> dict:
    return {
        "num_candidates": 2,
        "selected_index": selected_index,
        "used_fallback": not any(feasible_mask),
        "feasible_mask": feasible_mask,
        "infeasibility_reasons": reasons,
        "candidate_route_progress": route_progress,
        "candidate_step_reach": route_progress,
        "candidate_perfect_tracker_target_speed_mps": route_progress,
        "candidate_perfect_tracker_tail_average_speed_mps": route_progress,
        "candidate_perfect_tracker_jerk_magnitude_mps3": tracker_jerk,
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [1.0, 0.5],
        "candidate_horizon_lateral_acceleration_cost": [1.0, 0.5],
        "candidate_dp_prior_jerk_excess_cost": tracker_jerk,
        "candidate_dp_prior_lateral_acceleration_excess_cost": [1.0, 0.5],
        "candidate_dp_prior_deviation_cost": [1.0, 0.5],
        "candidate_horizon_yaw_rate_cost": [1.0, 0.5],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0],
        "candidate_full_horizon_planned_red_light_cost": [0.0, 0.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.0],
        "selection_scores": [1.0, 0.2],
    }


def test_deployable_static_failure_diagnosis_joins_comparison_and_logs(tmp_path) -> None:
    root = tmp_path / "matrix"
    static_dir = root / "route_a" / "seed_3" / "npc_8" / "spawn_0p6" / "tl_off" / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "camp_selection_log.json").write_text(
        json.dumps(
            [
                _record(
                    selected_index=1,
                    feasible_mask=[True, True],
                    route_progress=[10.0, 9.5],
                    tracker_jerk=[5.0, 3.0],
                    reasons=[[], []],
                ),
                _record(
                    selected_index=1,
                    feasible_mask=[False, False],
                    route_progress=[10.0, 8.0],
                    tracker_jerk=[5.0, 4.0],
                    reasons=[["lane_corridor"], ["low_progress"]],
                ),
            ]
        ),
        encoding="utf-8",
    )
    comparison = {
        "runs": [
            {
                "variant": "top1",
                "run_key": "route_a|3|8|off",
                "route_name": "route_a",
                "max_npcs": 8,
                "traffic_lights": False,
                "safety_cost_v1": 1.0,
                "route_completion_rate": 0.9,
                "near_miss_rate": 0.0,
                "lane_violation_rate": 0.0,
                "red_light_violation_rate": 0.0,
                "planned_red_light_violation_rate": 0.0,
                "mean_jerk_magnitude_mps3": 5.0,
                "mean_lateral_acceleration_mps2": 1.0,
                "distance_traveled_m": 100.0,
                "final_goal_distance_m": 10.0,
            },
            {
                "variant": "static",
                "run_key": "route_a|3|8|off",
                "route_name": "route_a",
                "max_npcs": 8,
                "traffic_lights": False,
                "output_dir": str(static_dir),
                "safety_cost_v1": 1.4,
                "route_completion_rate": 0.8,
                "near_miss_rate": 0.1,
                "lane_violation_rate": 0.2,
                "red_light_violation_rate": 0.0,
                "planned_red_light_violation_rate": 0.0,
                "mean_jerk_magnitude_mps3": 6.0,
                "mean_lateral_acceleration_mps2": 1.2,
                "distance_traveled_m": 90.0,
                "final_goal_distance_m": 20.0,
                "p95_selection_latency_ms": 101.0,
                "fallback_rate": 0.5,
                "candidate_feasible_rate": 0.5,
            },
        ],
        "safety_gate_assessments": [
            {
                "hard_gate_passed": False,
                "safety_cost_claim_passed": False,
                "claim_rule": "unit rule",
            }
        ],
    }
    comparison_path = root / "benchmark_comparison.json"
    comparison_path.write_text(json.dumps(comparison), encoding="utf-8")

    report = analyze(root, comparison=comparison_path, label="unit")
    run = report["runs"][0]

    assert run["benchmark"]["delta_static_minus_top1"]["safety_cost_v1"] == pytest.approx(0.4)
    assert run["benchmark"]["delta_static_minus_top1"]["route_completion_rate"] == pytest.approx(-0.1)
    assert run["selection"]["fallback_rate"] == pytest.approx(0.5)
    assert run["selection"]["candidate_feasible_rate"] == pytest.approx(0.5)
    assert run["selection"]["selected_non_top1_rate"] == pytest.approx(1.0)
    assert run["feature_deltas_selected_minus_top1"]["route_progress"]["delta"]["mean"] == pytest.approx(-1.25)
    assert run["feature_deltas_selected_minus_top1"]["tracker_jerk"]["selected_better_or_equal_rate"] == pytest.approx(1.0)
    assert run["top_infeasibility_reasons"] == [
        {"reason": "lane_corridor", "count": 1},
        {"reason": "low_progress", "count": 1},
    ]

    markdown = render_markdown(report)
    assert "DP-CAMP Deployable Static Failure Diagnosis" in markdown
    assert "route_a" in markdown
    assert "unit rule" in markdown
