from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_state_conditioned_progress_rules import (
    analyze,
    render_markdown,
)


def _outcome(
    *,
    lane_violation: bool = False,
    progress_m: float = 10.0,
) -> dict[str, object]:
    return {
        "progress_m": progress_m,
        "collision": False,
        "near_miss": False,
        "lane_violation": lane_violation,
        "red_light_violation": False,
        "mean_jerk_mps3": 1.0,
        "mean_lateral_acceleration_mps2": 1.0,
        "feasible": True,
    }


def _record(
    *,
    selected_index: int = 1,
    planned_progress: list[float],
    jerk: list[float],
    lateral: list[float],
    outcomes: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "num_candidates": 2,
        "selected_index": selected_index,
        "feasible_mask": [True, True],
        "selection_scores": [0.01, 0.0],
        "candidate_dp_prior_deviation_cost": [0.0, 0.0],
        "candidate_route_progress": planned_progress,
        "candidate_perfect_tracker_jerk_magnitude_mps3": jerk,
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": lateral,
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0],
        "candidate_closed_loop_outcomes": outcomes,
    }


def test_state_conditioned_progress_rule_requires_comfort_nonworse(tmp_path) -> None:
    root = tmp_path / "matrix"
    log_dir = (
        root
        / "sample_map_tl_route_59_to_86"
        / "seed_3"
        / "npc_4"
        / "spawn_0p6"
        / "tl_on"
        / "static"
    )
    log_dir.mkdir(parents=True)
    (log_dir / "camp_selection_log.json").write_text(
        json.dumps(
            [
                _record(
                    planned_progress=[10.0, 5.0],
                    jerk=[1.0, 1.0],
                    lateral=[1.0, 1.0],
                    outcomes=[
                        _outcome(progress_m=10.0),
                        _outcome(lane_violation=True, progress_m=5.0),
                    ],
                ),
                _record(
                    planned_progress=[10.0, 5.0],
                    jerk=[2.0, 1.0],
                    lateral=[2.0, 1.0],
                    outcomes=[
                        _outcome(lane_violation=True, progress_m=10.0),
                        _outcome(progress_m=5.0),
                    ],
                ),
                _record(
                    planned_progress=[10.0, 5.0],
                    jerk=[1.0, 1.0],
                    lateral=[1.0, 1.0],
                    outcomes=[
                        _outcome(progress_m=10.0),
                        _outcome(progress_m=5.0),
                    ],
                ),
            ]
        ),
        encoding="utf-8",
    )

    report = analyze(
        [root],
        label="unit",
        target_buckets=("red_light_turn",),
        progress_gain_thresholds=(1.0,),
        jerk_tolerances=(0.0,),
        lateral_tolerances=(0.0,),
        score_margins=(0.05,),
        bootstrap_resamples=64,
        seed=7,
    )

    rule = report["rules"][0]
    metrics = rule["by_bucket"]["red_light_turn"]
    assert metrics["records"] == 3
    assert metrics["changed_from_current_rate"] == pytest.approx(2.0 / 3.0)
    assert metrics["hard_nonworse_vs_current"] == pytest.approx(1.0)
    assert metrics["safety_cost_delta_vs_current"]["mean"] < 0.0
    assert report["decision"]["online_selector_change_authorized"] is False

    markdown = render_markdown(report)
    assert "State-Conditioned Material Progress Rule Audit" in markdown
    assert "not classical Benders decomposition" in markdown
    assert "red_light_turn" in markdown
