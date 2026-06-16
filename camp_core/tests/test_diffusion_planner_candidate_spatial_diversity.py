from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_candidate_spatial_diversity import (
    analyze,
    render_markdown,
)


def _outcome(index: int, *, progress: float, jerk: float, lateral: float) -> dict:
    return {
        "candidate_index": index,
        "progress_m": progress,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
        "feasible": True,
        "value": 0.0,
    }


def _prefix(end_x: float, end_y: float) -> list[list[float]]:
    return [
        [end_x * idx / 9.0, end_y * idx / 9.0, 0.0]
        for idx in range(10)
    ]


def _record() -> dict:
    return {
        "num_candidates": 3,
        "selected_index": 0,
        "feasible_mask": [True, True, True],
        "candidate_closed_loop_outcomes": [
            _outcome(0, progress=10.0, jerk=5.0, lateral=2.0),
            _outcome(1, progress=9.95, jerk=6.0, lateral=1.0),
            _outcome(2, progress=9.96, jerk=4.0, lateral=1.2),
        ],
        "selection_scores": [0.0, 1.0, 2.0],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0, 0.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.0, 0.0],
        "candidate_route_progress": None,
        "dp_candidate_rewards": [
            {"progress": 10.0},
            {"progress": 9.95},
            {"progress": 9.96},
        ],
        "candidate_step_reach": [1.0, 0.95, 0.96],
        "candidate_perfect_tracker_target_speed_mps": [5.0, 4.95, 4.96],
        "candidate_perfect_tracker_postprocessed_reference_prefix": [
            _prefix(10.0, 0.0),
            _prefix(9.95, -0.30),
            _prefix(9.96, 0.80),
        ],
        "candidate_horizon_lateral_acceleration_cost": [2.0, 0.5, 0.8],
        "candidate_dp_prior_jerk_excess_cost": [1.0, 0.5, 0.5],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [2.0, 3.0, 1.0],
        "candidate_perfect_tracker_open_loop_rollout": {
            str(horizon): {
                "mean_vector_jerk_mps3": [2.0, 3.0, 1.0],
                "distance_m": [10.0, 9.95, 9.96],
            }
            for horizon in (3, 5, 10)
        },
    }


def _write_log(tmp_path, records: list[dict]):
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def _screen(report: dict, name: str) -> dict:
    for screen in report["screens"]:
        if screen["name"] == name:
            return screen
    raise AssertionError(f"missing screen {name}")


def test_spatial_diversity_audit_summarizes_failure_tick_modes(tmp_path) -> None:
    report = analyze(
        [_write_log(tmp_path, [_record()])],
        label="unit",
        screen_names=("balanced_lateral_jerk_nondegrading",),
    )
    screen = _screen(report, "balanced_lateral_jerk_nondegrading")

    assert screen["records"]["failure_ticks"] == 1
    assert screen["records"]["with_any_admissible_success"] == 1
    all_summary = screen["group_summaries"]["all"]
    assert all_summary["admissible_count"]["mean"] == pytest.approx(2.0)
    assert all_summary["mode_count"]["mean"] == pytest.approx(2.0)
    assert all_summary["lateral_range_m"]["mean"] == pytest.approx(1.1)
    assert all_summary["endpoint_pairwise_mean_m"]["mean"] > 1.0

    success = screen["success_candidate_summaries"]
    assert success["admissible_count"]["mean"] == pytest.approx(1.0)

    markdown = render_markdown(report)
    assert "Candidate Spatial Diversity Audit" in markdown
    assert "balanced_lateral_jerk_nondegrading" in markdown
