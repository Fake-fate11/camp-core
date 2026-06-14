from __future__ import annotations

import json

from scripts.integrations.analyze_diffusion_planner_tracker_rollout_shadows import (
    analyze,
    render_markdown,
)


def test_rollout_shadow_analysis_screens_full_red_and_pareto_candidates(
    tmp_path,
) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(json.dumps([_record()]), encoding="utf-8")

    report = analyze([log_path])

    assert report["records"]["nonfallback"] == 1
    assert report["full_horizon_red_light"][
        "short_safe_full_red_candidates"
    ] == 2
    assert report["full_horizon_red_light"][
        "selected_short_safe_full_red_records"
    ] == 1
    for horizon in ("3", "5", "10"):
        assert report["horizons"][horizon]["rollout_pareto"][
            "changed_records"
        ] == 1
        assert report["horizons"][horizon][
            "command_and_rollout_pareto"
        ]["changed_records"] == 1
        assert report["horizons"][horizon][
            "red_improving_progress_distance"
        ]["changed_records"] == 1
        assert report["horizons"][horizon][
            "red_improving_rollout_pareto"
        ]["changed_records"] == 1
        assert report["horizons"][horizon][
            "red_minimum_best_progress"
        ]["changed_records"] == 1
        deltas = report["horizons"][horizon]["rollout_pareto"][
            "mean_deltas_on_changed_records"
        ]
        assert deltas["progress"] > 0.0
        assert deltas["full_red"] < 0.0
        assert deltas["distance"] > 0.0
        assert deltas["jerk"] < 0.0
        assert deltas["lateral"] < 0.0
        assert report["horizons"][horizon]["red_minimum_best_progress"][
            "delta_quantiles_on_changed_records"
        ]["full_red"]["p50"] < 0.0
    assert "not a guarantee" in render_markdown(report)


def test_rollout_shadow_analysis_rejects_missing_full_red(tmp_path) -> None:
    record = _record()
    del record["candidate_full_horizon_planned_red_light_cost"]
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(json.dumps([record]), encoding="utf-8")

    try:
        analyze([log_path])
    except ValueError as exc:
        assert "full red is invalid" in str(exc)
    else:
        raise AssertionError("Expected missing full-red shadow to fail.")


def _record() -> dict:
    rollout = {}
    for horizon in (3, 5, 10):
        rollout[str(horizon)] = {
            "distance_m": [3.0, 3.1, 3.1],
            "mean_vector_jerk_mps3": [3.0, 2.0, 1.5],
            "max_vector_jerk_mps3": [4.0, 3.0, 2.5],
            "mean_lateral_acceleration_mps2": [1.0, 0.8, 0.7],
            "max_lateral_acceleration_mps2": [1.2, 1.0, 0.9],
        }
    return {
        "selected_index": 0,
        "used_fallback": False,
        "feasible_mask": [True, True, False],
        "selection_scores": [0.0, 0.2, float("inf")],
        "dp_candidate_rewards": [
            {"progress": 5.0, "red_light": 0.0},
            {"progress": 5.2, "red_light": 0.0},
            {"progress": 5.1, "red_light": 0.0},
        ],
        "candidate_full_horizon_planned_red_light_cost": [2.0, 0.0, 2.0],
        "candidate_horizon_union_planned_red_light_cost": [2.0, 0.0, 2.0],
        "candidate_perfect_tracker_target_speed_mps": [1.0, 1.1, 1.1],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [3.0, 2.5, 2.0],
        (
            "candidate_perfect_tracker_"
            "lateral_acceleration_magnitude_mps2"
        ): [1.0, 0.9, 0.8],
        "candidate_perfect_tracker_open_loop_rollout": rollout,
    }
