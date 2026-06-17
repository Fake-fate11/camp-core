from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_latency_budget import (
    analyze,
    render_markdown,
)


def test_latency_budget_reports_tail_and_removal_sensitivity(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(
        json.dumps(
            [
                _record(total=100.0, candidate=50.0, reward=30.0, camp=10.0),
                _record(total=120.0, candidate=60.0, reward=40.0, camp=10.0),
            ]
        ),
        encoding="utf-8",
    )

    report = analyze([log_path], label="unit", tail_percentile=50.0)

    assert report["records"]["logs"] == 1
    assert report["records"]["total"] == 2
    assert report["records"]["tail"] == 1
    assert report["overall_latency_ms"][
        "latency_ms_including_candidate_generation"
    ]["p95"] == pytest.approx(119.0)
    assert report["tail_mean_latency_ms"][
        "latency_ms_reward_scoring"
    ]["mean"] == pytest.approx(40.0)
    reward_removed = report["removal_sensitivity"]["latency_ms_reward_scoring"]
    assert reward_removed["p95_if_removed_ms"] == pytest.approx(79.5)
    assert reward_removed["p95_reduction_ms"] == pytest.approx(39.5)
    assert report["derived_latency_ms"]["non_candidate_generation"][
        "p95"
    ] == pytest.approx(59.5)
    assert report["overall_latency_ms"]["latency_ms_reward_batch_compute"][
        "p95"
    ] == pytest.approx(28.5)
    assert report["derived_latency_ms"]["reward_breakdown_sum"][
        "p95"
    ] == pytest.approx(39.5)
    assert report["derived_latency_ms"]["reward_unattributed_residual"][
        "p95"
    ] == pytest.approx(0.0)

    markdown = render_markdown(report)
    assert "DP-CAMP Latency Budget Attribution" in markdown
    assert "Removal Sensitivity" in markdown
    assert "Latency attribution is a read-only engineering diagnostic" in markdown


def _record(
    *,
    total: float,
    candidate: float,
    reward: float,
    camp: float,
) -> dict:
    return {
        "num_candidates": 8,
        "selected_index": 0,
        "used_fallback": False,
        "latency_ms_including_candidate_generation": total,
        "latency_ms_candidate_generation": candidate,
        "latency_ms_shadow_dp_prior_deviation": 1.0,
        "latency_ms_shadow_dp_prior_comfort_excess": 1.0,
        "latency_ms_shadow_lateral_comfort": 1.0,
        "latency_ms_context_and_obstacles": 1.0,
        "latency_ms_shadow_obstacle_clearance": 5.0,
        "latency_ms_shadow_perfect_tracker_command": 1.0,
        "latency_ms_shadow_perfect_tracker_open_loop": 1.0,
        "latency_ms_reward_scoring": reward,
        "latency_ms_outcome_collection": 0.0,
        "latency_ms_red_stopping_margin_atom": 1.0,
        "latency_ms_camp_selection": camp,
        "latency_ms_underprogress_relaxation": 0.0,
        "latency_ms_splice_shadow_rule": 0.0,
        "latency_ms_traffic_light_hybrid_postselection": 0.0,
        "latency_ms_perfect_tracker_command_postselection": 0.0,
        "latency_ms_shadow_full_horizon_red_light": 1.0,
        "latency_ms_reward_npz_dump": 1.0,
        "latency_ms_reward_tensor_setup": 2.0,
        "latency_ms_reward_sg_smoothing": 0.0,
        "latency_ms_reward_candidate_tensor_transfer": 1.0,
        "latency_ms_reward_batch_compute": reward - 11.0,
        "latency_ms_reward_postprocess": 1.0,
        "latency_ms_reward_full_horizon_red_light": 4.0,
        "latency_ms_reward_red_route_points": 0.5,
        "latency_ms_reward_feasibility": 0.5,
        "latency_ms_reward_field_extraction": 0.5,
        "latency_ms_reward_step_reach_guard": 0.0,
        "latency_ms_reward_route_progress": 0.5,
        "latency_ms_reward_route_progress_guard": 0.0,
        "latency_ms_reward_lexicographic_filter": 0.0,
        "latency_ms_camp_atom_computation": 2.0,
        "latency_ms_camp_feasibility": 1.0,
        "latency_ms_camp_collision_checks": 4.0,
        "latency_ms_camp_scoring": 3.0,
    }
