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
    summary_path = tmp_path / "camp_replay_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "benchmark": {
                    "route": "sample59_86",
                    "seed": 1,
                    "max_npcs": 0,
                    "traffic_lights": True,
                    "advance_mode": "perfect",
                }
            }
        ),
        encoding="utf-8",
    )
    log_path.write_text(json.dumps([_record()]), encoding="utf-8")

    report = analyze([log_path])

    assert report["records"]["nonfallback"] == 1
    assert report["full_horizon_red_light"][
        "short_safe_full_red_candidates"
    ] == 2
    assert report["full_horizon_red_light"][
        "selected_short_safe_full_red_records"
    ] == 1
    breakdown = report["full_horizon_red_light"][
        "selected_short_safe_full_red_breakdown"
    ]
    assert breakdown["nonfallback"] == 1
    assert breakdown["fallback"] == 0
    assert breakdown["with_lower_union_red_feasible_candidate"] == 1
    diagnosis = report["full_horizon_red_light"][
        "no_lower_union_red_feasible_diagnosis"
    ]
    assert diagnosis["events"] == 0
    event = report["full_horizon_red_light"][
        "selected_short_safe_full_red_events"
    ][0]
    assert event["context"]["traffic_lights"] is True
    assert event["current_speed_mps"] == 1.5
    assert event["selected"]["full_horizon_red"] == 2.0
    assert event["selected"]["red_stopping_margin_cost"] == 3.0
    assert event["selected"]["h3_max_lateral_mps2"] == 1.2
    assert event["best_lower_union_red_feasible_candidate"][
        "candidate_index"
    ] == 1
    assert event["best_lower_union_red_candidate_any_feasibility"][
        "feasible"
    ] is True
    assert event["best_lower_union_red_feasible_candidate"]["delta"][
        "full_red"
    ] < 0.0
    budget = report["full_horizon_red_light"][
        "predeclared_budget_sensitivity_h3"
    ]
    assert budget["event_denominator"] == 1
    assert budget["jerk_guard"] is None
    assert len(budget["cells"]) == 6
    assert all(cell["changed_records"] == 1 for cell in budget["cells"])
    assert all(
        cell["selection_rule"] == "min_union_red_then_camp_score_then_index"
        for cell in budget["cells"]
    )
    stopping_budget = report["full_horizon_red_light"][
        "stopping_margin_nonworse_budget_sensitivity_h3"
    ]
    assert len(stopping_budget["cells"]) == 6
    assert stopping_budget["requires_stopping_margin_nonworse"] is True
    assert all(
        cell["changed_records"] == 1 for cell in stopping_budget["cells"]
    )
    assert all(
        cell["mean_deltas_on_changed_records"]["stopping_margin"] < 0.0
        for cell in stopping_budget["cells"]
    )
    assert all(
        cell["selection_rule"]
        == "min_union_red_then_stopping_margin_then_camp_score_then_index"
        for cell in stopping_budget["cells"]
    )
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


def test_rollout_shadow_analysis_attributes_infeasible_lower_red_candidates(
    tmp_path,
) -> None:
    record = _record()
    record["feasible_mask"] = [True, False, True]
    record["selection_scores"] = [0.0, float("inf"), 0.3]
    record["candidate_full_horizon_planned_red_light_cost"] = [2.0, 0.5, 3.0]
    record["candidate_horizon_union_planned_red_light_cost"] = [2.0, 0.5, 3.0]
    record["candidate_red_stopping_margin_cost"] = [3.0, 1.0, 4.0]
    record["infeasibility_reasons"] = [
        [],
        ["unit_route_progress_gate", "unit_lateral_gate"],
        [],
    ]
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(json.dumps([record]), encoding="utf-8")

    report = analyze([log_path])

    red = report["full_horizon_red_light"]
    assert red["selected_short_safe_full_red_records"] == 1
    assert red["selected_short_safe_full_red_breakdown"][
        "without_lower_union_red_feasible_candidate"
    ] == 1
    diagnosis = red["no_lower_union_red_feasible_diagnosis"]
    assert diagnosis["events"] == 1
    assert diagnosis["with_lower_union_red_infeasible_candidate"] == 1
    assert diagnosis["with_no_lower_union_red_candidate_anywhere"] == 0
    assert diagnosis["infeasible_lower_union_red_reason_counts"] == {
        "unit_lateral_gate": 1,
        "unit_route_progress_gate": 1,
    }
    event = red["selected_short_safe_full_red_events"][0]
    assert event["lower_union_red_feasible_candidates"] == 0
    assert event["lower_union_red_candidate_count"] == 1
    assert event["lower_union_red_infeasible_candidates"] == 1
    assert event["best_lower_union_red_feasible_candidate"] is None
    assert event["best_lower_union_red_candidate_any_feasibility"][
        "candidate_index"
    ] == 1
    assert event["best_lower_union_red_candidate_any_feasibility"][
        "feasible"
    ] is False


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
        "infeasibility_reasons": [[], [], ["unit_infeasible"]],
        "selection_scores": [0.0, 0.2, float("inf")],
        "dp_candidate_rewards": [
            {"progress": 5.0, "red_light": 0.0},
            {"progress": 5.2, "red_light": 0.0},
            {"progress": 5.1, "red_light": 0.0},
        ],
        "candidate_full_horizon_planned_red_light_cost": [2.0, 0.0, 2.0],
        "candidate_horizon_union_planned_red_light_cost": [2.0, 0.0, 2.0],
        "candidate_red_stopping_margin_cost": [3.0, 1.0, 4.0],
        "candidate_perfect_tracker_target_speed_mps": [1.0, 1.1, 1.1],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [3.0, 2.5, 2.0],
        (
            "candidate_perfect_tracker_"
            "lateral_acceleration_magnitude_mps2"
        ): [1.0, 0.9, 0.8],
        "candidate_perfect_tracker_open_loop_rollout": rollout,
        "perfect_tracker_command_inputs": {
            "current_speed_mps": 1.5,
        },
    }
