from __future__ import annotations

import json

from scripts.integrations.analyze_diffusion_planner_feasible_top1_shadow_sweep import (
    analyze,
    render_markdown,
)


def _record(
    *,
    selected: int,
    feasible: list[bool],
    prior_deviation: list[float],
    target_speed: list[float],
    route_progress: list[float],
) -> dict:
    return {
        "num_candidates": 2,
        "selected_index": selected,
        "feasible_mask": feasible,
        "candidate_route_progress": route_progress,
        "candidate_perfect_tracker_target_speed_mps": target_speed,
        "candidate_perfect_tracker_tail_average_speed_mps": target_speed,
        "candidate_dp_prior_deviation_cost": prior_deviation,
        "candidate_dp_prior_jerk_excess_cost": [1.0, 0.5],
        "candidate_dp_prior_lateral_acceleration_excess_cost": [1.0, 0.5],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [2.0, 1.0],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [2.0, 1.0],
        "selection_scores": [1.0, 0.2],
    }


def test_feasible_top1_shadow_sweep_ranks_bounded_prior_rules(tmp_path) -> None:
    root = tmp_path / "matrix"
    static_dir = root / "route_a" / "seed_3" / "npc_8" / "spawn_0p6" / "tl_off" / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "camp_selection_log.json").write_text(
        json.dumps(
            [
                _record(
                    selected=1,
                    feasible=[True, True],
                    prior_deviation=[0.0, 1.0],
                    target_speed=[5.0, 4.9],
                    route_progress=[10.0, 10.1],
                ),
                _record(
                    selected=1,
                    feasible=[True, True],
                    prior_deviation=[0.0, 0.1],
                    target_speed=[5.0, 5.0],
                    route_progress=[10.0, 10.5],
                ),
                _record(
                    selected=0,
                    feasible=[True, True],
                    prior_deviation=[0.0, 1.0],
                    target_speed=[5.0, 4.9],
                    route_progress=[10.0, 10.1],
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
                "safety_cost_v1": 1.2,
                "route_completion_rate": 0.8,
                "near_miss_rate": 0.0,
                "lane_violation_rate": 0.0,
                "mean_jerk_magnitude_mps3": 4.5,
            },
        ]
    }
    comparison_path = root / "benchmark_comparison.json"
    comparison_path.write_text(json.dumps(comparison), encoding="utf-8")

    report = analyze(
        root,
        comparison=comparison_path,
        label="unit",
        max_change_rate=0.4,
        max_top1_selected_rate=0.7,
        min_bad_run_changed_rate=0.3,
    )
    ranked = report["ranked_candidates"]

    assert ranked[0]["passed_shadow_screen"] is True
    assert ranked[0]["bad_run_changed_rate"] >= 1.0 / 3.0
    baseline = next(rule for rule in report["rules"] if rule["name"] == "static_baseline")
    assert baseline["overall"]["changed_from_static_rate"] == 0.0

    markdown = render_markdown(report)
    assert "Feasible Top-1 Shadow Sweep" in markdown
    assert "Ranked Candidates" in markdown
