from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_traffic_light_hybrid_failure_attribution import (
    analyze,
    render_markdown,
)


def test_traffic_light_hybrid_failure_attribution_reports_changed_event(
    tmp_path,
) -> None:
    root = tmp_path / "hybrid"
    baseline_root = tmp_path / "baseline"
    run = "sample/seed_1/npc_0/spawn_0p3/tl_on/static"
    _write_run(root / run, changed=True)
    _write_run(baseline_root / run, changed=False, safety_offset=-0.5)

    report = analyze(root, baseline_root=baseline_root, label="unit")

    assert report["records"]["runs"] == 1
    assert report["records"]["total"] == 2
    assert report["records"]["changed"] == 1
    assert report["change_types"] == {"nonzero_to_nonzero": 1}
    assert report["pairing"]["paired_baseline_runs"] == 1

    event = report["changed_events"][0]
    assert event["selection_step"] == 0
    assert event["before_hybrid_index"] == 1
    assert event["selected_index"] == 2
    assert "raw_jerk" in event["attractive_vs_original_camp"]
    assert "raw_lateral" in event["attractive_vs_original_camp"]
    assert "camp_score" in event["worse_vs_candidate0"]

    raw_jerk = report["feature_deltas_vs_original_camp"]["raw_jerk"]
    assert raw_jerk["n"] == 1
    assert raw_jerk["negative"] == 1

    run_report = report["run_reports"][0]
    assert run_report["baseline_delta"]["safety_cost_v1"] == pytest.approx(0.5)

    markdown = render_markdown(report)
    assert "Traffic-Light Hybrid Failure Attribution" in markdown
    assert "nonzero_to_nonzero" in markdown


def test_traffic_light_hybrid_failure_attribution_rejects_outcome_labels(
    tmp_path,
) -> None:
    root = tmp_path / "hybrid"
    run = "sample/seed_1/npc_0/spawn_0p3/tl_on/static"
    log_path = _write_run(root / run, changed=True)
    records = json.loads(log_path.read_text(encoding="utf-8"))
    records[0]["candidate_closed_loop_outcomes"] = [{"candidate_index": 0}]
    log_path.write_text(json.dumps(records), encoding="utf-8")

    with pytest.raises(ValueError, match="closed-loop outcomes"):
        analyze(root)


def _write_run(
    run_dir,
    *,
    changed: bool,
    safety_offset: float = 0.0,
):
    run_dir.mkdir(parents=True)
    benchmark = {
        "route": "/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
        "seed": 1,
        "steps": 2,
        "max_npcs": 0,
        "spawn_probability": 0.3,
        "traffic_lights": True,
        "advance_mode": "perfect",
    }
    summary = {
        "benchmark": benchmark,
        "route_completion_rate": 0.5,
        "obb_collision_rate": 0.0,
        "near_miss_rate": 0.0,
        "lane_violation_rate": 0.0,
        "red_light_violation_rate": 0.0,
        "planned_red_light_violation_rate": 0.0,
        "mean_jerk_magnitude_mps3": 5.0 + 10.0 * safety_offset,
        "mean_lateral_acceleration_mps2": 0.5,
        "p95_selection_latency_ms": 90.0,
    }
    (run_dir / "camp_validation_summary.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )
    records = [
        _record(changed=changed),
        {
            **_record(changed=False),
            "selected_index": 0,
            "camp_selected_index_before_traffic_light_hybrid_postselection": 0,
            "traffic_light_hybrid_postselection": {
                "reason": "no_admissible_traffic_light_hybrid_candidate",
                "changed": False,
            },
        },
    ]
    log_path = run_dir / "camp_selection_log.json"
    log_path.write_text(json.dumps(records), encoding="utf-8")
    return log_path


def _record(*, changed: bool) -> dict:
    selected = 2 if changed else 1
    return {
        "selected_index": selected,
        "camp_selected_index_before_traffic_light_hybrid_postselection": 1,
        "candidate_closed_loop_outcomes": None,
        "selection_scores": [0.1, 0.2, 0.3],
        "dp_candidate_rewards": [
            {"total": 10.0, "progress": 5.0, "smoothness": -0.1},
            {"total": 9.0, "progress": 4.9, "smoothness": -0.2},
            {"total": 8.8, "progress": 4.87, "smoothness": -0.1},
        ],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0, 0.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.0, 0.0],
        "candidate_dp_prior_jerk_excess_cost": [0.0, 0.4, 0.2],
        "candidate_horizon_lateral_acceleration_cost": [0.1, 0.5, 0.3],
        "candidate_perfect_tracker_target_speed_mps": [2.0, 1.9, 1.9],
        "candidate_step_reach": [1.0, 0.99, 0.99],
        "candidate_perfect_tracker_open_loop_rollout": {
            "3": {"distance_m": [1.0, 0.99, 0.98]},
            "10": {"distance_m": [3.0, 2.98, 2.97]},
        },
        "traffic_light_hybrid_postselection": {
            "reason": (
                "selected_admissible_traffic_light_hybrid_candidate"
                if changed
                else "no_admissible_traffic_light_hybrid_candidate"
            ),
            "changed": changed,
            "admissible_candidates": 1 if changed else 0,
            "admissible_indices": [2] if changed else [],
            "delta": {
                "raw_jerk": -0.2,
                "raw_lateral": -0.2,
                "dp_reward_progress_m": -0.03,
                "h10_distance_m": -0.01,
                "target_speed_mps": 0.0,
                "union_red": 0.0,
                "red_stopping": 0.0,
            },
            "losses": {
                "dp_reward_progress_loss_m": 0.03,
                "h10_distance_loss_m": 0.01,
                "target_speed_loss_mps": 0.0,
            },
        },
    }
