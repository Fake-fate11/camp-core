from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_top1_failsafe_shadow import (
    analyze,
    render_markdown,
)


def _record(
    *,
    selected: int,
    feasible: list[bool],
    prior_deviation: list[float],
    target_speed: list[float],
    scores: list[float],
) -> dict:
    return {
        "num_candidates": 2,
        "selected_index": selected,
        "used_fallback": not any(feasible),
        "feasible_mask": feasible,
        "candidate_route_progress": [10.0, 9.0],
        "candidate_perfect_tracker_target_speed_mps": target_speed,
        "candidate_perfect_tracker_tail_average_speed_mps": target_speed,
        "candidate_dp_prior_deviation_cost": prior_deviation,
        "candidate_dp_prior_jerk_excess_cost": [1.0, 0.5],
        "candidate_dp_prior_lateral_acceleration_excess_cost": [1.0, 0.5],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [2.0, 1.0],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [2.0, 1.0],
        "selection_scores": scores,
    }


def test_top1_failsafe_shadow_reports_rule_coverage(tmp_path) -> None:
    root = tmp_path / "matrix"
    static_dir = root / "route_a" / "seed_3" / "npc_8" / "spawn_0p6" / "tl_off" / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "camp_selection_log.json").write_text(
        json.dumps(
            [
                _record(
                    selected=1,
                    feasible=[False, False],
                    prior_deviation=[0.0, 5.0],
                    target_speed=[5.0, 4.0],
                    scores=[1.0, 0.2],
                ),
                _record(
                    selected=1,
                    feasible=[True, True],
                    prior_deviation=[0.0, 3.0],
                    target_speed=[5.0, 4.95],
                    scores=[1.0, 0.1],
                ),
                _record(
                    selected=1,
                    feasible=[True, True],
                    prior_deviation=[3.0, 0.0],
                    target_speed=[5.0, 4.95],
                    scores=[1.0, 0.1],
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
                "mean_jerk_magnitude_mps3": 4.0,
            },
            {
                "variant": "static",
                "run_key": "route_a|3|8|off",
                "route_name": "route_a",
                "max_npcs": 8,
                "traffic_lights": False,
                "output_dir": str(static_dir),
                "safety_cost_v1": 1.5,
                "route_completion_rate": 0.8,
                "near_miss_rate": 0.1,
                "lane_violation_rate": 0.2,
                "mean_jerk_magnitude_mps3": 5.0,
                "p95_selection_latency_ms": 101.0,
            },
        ]
    }
    comparison_path = root / "benchmark_comparison.json"
    comparison_path.write_text(json.dumps(comparison), encoding="utf-8")

    report = analyze(root, comparison=comparison_path, label="unit")
    by_name = {rule["name"]: rule for rule in report["rules"]}

    baseline = by_name["static_baseline"]["overall"]
    assert baseline["top1_selected_rate"] == pytest.approx(0.0)
    assert baseline["changed_from_static_rate"] == pytest.approx(0.0)

    fallback = by_name["top1_on_all_infeasible"]["overall"]
    assert fallback["changed_from_static_rate"] == pytest.approx(1.0 / 3.0)
    assert fallback["top1_selected_rate"] == pytest.approx(1.0 / 3.0)
    assert fallback["all_infeasible_top1_restored_rate"] == pytest.approx(1.0)

    combined = by_name["top1_on_all_infeasible_or_dp_prior_deviation_worse"]["overall"]
    assert combined["changed_from_static_rate"] == pytest.approx(2.0 / 3.0)
    assert combined["top1_selected_rate"] == pytest.approx(2.0 / 3.0)
    assert combined["dp_prior_deviation_trigger_rate"] == pytest.approx(1.0 / 3.0)
    prior_delta = combined["feature_delta_shadow_minus_top1"]["dp_prior_deviation"]
    assert prior_delta["mean_of_run_mean_delta"] == pytest.approx(-1.0)

    markdown = render_markdown(report)
    assert "Top-1 Failsafe Shadow" in markdown
    assert "top1_on_all_infeasible_or_dp_prior_deviation_worse" in markdown
