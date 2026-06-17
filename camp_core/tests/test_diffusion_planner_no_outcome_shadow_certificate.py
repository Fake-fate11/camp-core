from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_no_outcome_shadow_certificate import (
    analyze,
    render_markdown,
)


def test_no_outcome_shadow_certificate_combines_route_h10_and_clearance(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(
        json.dumps(
            [
                _record(
                    selected=0,
                    feasible=[True, True, True],
                    score=[0.20, 0.10, 0.05],
                    progress_shortfall=[1.0, 0.8, 0.7],
                    route_progress=[10.0, 10.0, 10.0],
                    h10_distance=[10.0, 10.10, 10.12],
                    soft_clearance=[0.0, 0.0, 1.0],
                    near_clearance=[0.0, 0.0, 0.0],
                    lateral=[1.0, 0.8, 0.7],
                    jerk=[1.0, 0.9, 0.8],
                ),
                _record(
                    selected=1,
                    feasible=[True, True],
                    score=[0.20, 0.10],
                    progress_shortfall=[1.0, 0.8],
                    route_progress=[10.0, 10.0],
                    h10_distance=[10.0, 10.10],
                    soft_clearance=[0.0, 1.0],
                    near_clearance=[0.0, 0.0],
                    lateral=[1.0, 0.8],
                    jerk=[1.0, 0.9],
                ),
            ]
        ),
        encoding="utf-8",
    )

    report = analyze([log_path], label="unit")

    assert report["records"]["total"] == 2
    assert report["records"]["closed_loop_outcome_records"] == 0
    assert report["descriptor_coverage"]["all_required_records"] == 2

    route_only = _screen(report, "route_h10_score0")
    clearance = _screen(report, "route_h10_clearance_nonworse")

    assert route_only["records"]["shadow_changes_candidate0"] == 2
    assert route_only["records"]["shadow_differs_from_logged"] == 1
    assert clearance["records"]["shadow_changes_candidate0"] == 1
    assert clearance["records"]["shadow_differs_from_logged"] == 2
    assert clearance["selected_delta_summary"]["soft_clearance_cost"]["max"] == pytest.approx(
        0.0
    )
    assert clearance["stage_counts"]["candidate0_retain_empty_mask"] == 1

    markdown = render_markdown(report)
    assert "No-Outcome Shadow Certificate Audit" in markdown
    assert "route_h10_clearance_nonworse" in markdown
    assert "Candidate outcomes are forbidden" in report["analysis"]["math_boundary"]


def test_no_outcome_shadow_certificate_rejects_outcome_labels(tmp_path) -> None:
    record = _record(
        selected=0,
        feasible=[True],
        score=[0.0],
        progress_shortfall=[1.0],
        route_progress=[10.0],
        h10_distance=[10.0],
        soft_clearance=[0.0],
        near_clearance=[0.0],
        lateral=[1.0],
        jerk=[1.0],
    )
    record["candidate_closed_loop_outcomes"] = [{"candidate_index": 0}]
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(json.dumps([record]), encoding="utf-8")

    with pytest.raises(ValueError, match="no-outcome audit"):
        analyze([log_path])


def _screen(report: dict, name: str) -> dict:
    for screen in report["screens"]:
        if screen["name"] == name:
            return screen
    raise AssertionError(f"missing screen {name}")


def _record(
    *,
    selected: int,
    feasible: list[bool],
    score: list[float],
    progress_shortfall: list[float],
    route_progress: list[float],
    h10_distance: list[float],
    soft_clearance: list[float],
    near_clearance: list[float],
    lateral: list[float],
    jerk: list[float],
) -> dict:
    return {
        "num_candidates": len(feasible),
        "selected_index": selected,
        "used_fallback": not any(feasible),
        "atom_names": [
            "progress_shortfall",
            "planned_red_light_cost",
            "red_stopping_margin_cost",
            "dp_prior_jerk_excess_cost",
        ],
        "atoms": [
            [progress, 0.0, 0.0, jerk_value]
            for progress, jerk_value in zip(progress_shortfall, jerk, strict=True)
        ],
        "feasible_mask": feasible,
        "selection_scores": score,
        "candidate_horizon_union_planned_red_light_cost": [0.0] * len(feasible),
        "candidate_red_stopping_margin_cost": [0.0] * len(feasible),
        "candidate_dp_prior_jerk_excess_cost": jerk,
        "candidate_horizon_lateral_acceleration_cost": lateral,
        "candidate_route_progress": route_progress,
        "candidate_perfect_tracker_open_loop_rollout": {
            "10": {"distance_m": h10_distance}
        },
        "candidate_obstacle_clearance": {
            "schema_version": "candidate_current_tick_obstacle_clearance_v2",
            "soft_clearance_violation_cost": soft_clearance,
            "near_miss_violation_cost": near_clearance,
            "min_obstacle_clearance_lower_bound_m": [10.0] * len(feasible),
            "exact_evaluated_pairs": [0] * len(feasible),
        },
        "candidate_closed_loop_outcomes": None,
        "latency_ms_shadow_obstacle_clearance": 1.0,
        "latency_ms_shadow_perfect_tracker_open_loop": 1.0,
        "latency_ms_camp_selection": 5.0,
        "latency_ms_including_candidate_generation": 90.0,
    }
