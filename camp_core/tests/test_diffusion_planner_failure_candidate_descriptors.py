from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_failure_candidate_descriptors import (
    analyze,
    render_markdown,
)


def _outcome(
    index: int,
    *,
    progress: float,
    jerk: float,
    lateral: float,
    value: float = 0.0,
) -> dict:
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
        "value": value,
    }


def _prefix(h10: float) -> list[list[float]]:
    return [[1.0 + (h10 - 1.0) * idx / 9.0, 0.0, 0.0] for idx in range(10)]


def _rollout() -> dict:
    return {
        str(horizon): {
            "mean_vector_jerk_mps3": [2.0, 3.0, 1.0],
            "distance_m": [10.0, 9.95, 9.96],
        }
        for horizon in (3, 5, 10)
    }


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
            _prefix(10.0),
            _prefix(9.95),
            _prefix(9.96),
        ],
        "candidate_horizon_lateral_acceleration_cost": [2.0, 0.5, 0.8],
        "candidate_dp_prior_jerk_excess_cost": [1.0, 0.5, 0.5],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [2.0, 3.0, 1.0],
        "candidate_perfect_tracker_open_loop_rollout": _rollout(),
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


def test_failure_descriptor_audit_summarizes_current_tick_features(tmp_path) -> None:
    report = analyze(
        [_write_log(tmp_path, [_record()])],
        label="unit",
        screen_names=("balanced_lateral_jerk_nondegrading",),
    )
    screen = _screen(report, "balanced_lateral_jerk_nondegrading")

    assert screen["records"]["failure_ticks"] == 1
    assert screen["records"]["with_any_admissible_success"] == 1
    assert screen["candidate_counts"]["with_any_success"]["admissible_success"][
        "mean"
    ] == pytest.approx(1.0)
    assert screen["feature_best_delta_summary"]["raw_lateral"]["with_any_success"][
        "mean"
    ] == pytest.approx(-1.5)
    guards = screen["guard_summary"]
    assert guards["prefix_tracker_jerk_nonworse"]["all"][
        "guarded_success_rate"
    ] == pytest.approx(1.0)

    markdown = render_markdown(report)
    assert "Failure Candidate Descriptor Audit" in markdown
    assert "raw_lateral" in markdown
