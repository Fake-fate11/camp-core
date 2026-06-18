from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_joint_bucket_failures import (
    analyze,
    render_markdown,
)


def _outcome(
    *,
    near_miss: bool = False,
    lane_violation: bool = False,
    progress_m: float = 10.0,
) -> dict[str, object]:
    return {
        "progress_m": progress_m,
        "collision": False,
        "near_miss": near_miss,
        "lane_violation": lane_violation,
        "red_light_violation": False,
        "mean_jerk_mps3": 1.0,
        "mean_lateral_acceleration_mps2": 1.0,
        "feasible": True,
    }


def _record(
    *,
    outcomes: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "num_candidates": 2,
        "selected_index": 1,
        "feasible_mask": [True, True],
        "selection_scores": [0.01, 0.0],
        "candidate_dp_prior_deviation_cost": [0.0, 0.0],
        "candidate_route_progress": [10.0, 5.0],
        "candidate_horizon_union_planned_red_light_cost": [0.5, 0.0],
        "candidate_closed_loop_outcomes": outcomes,
    }


def test_joint_bucket_failure_attribution_reports_components_and_worst_records(
    tmp_path,
) -> None:
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
                    outcomes=[
                        _outcome(progress_m=10.0),
                        _outcome(lane_violation=True, progress_m=5.0),
                    ],
                ),
                _record(
                    outcomes=[
                        _outcome(near_miss=True, progress_m=10.0),
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
        alpha=0.0,
        beta=0.02,
        prior_scale=1.0,
        progress_scale=1.0,
        buckets=("red_light_turn",),
        bootstrap_resamples=64,
        seed=7,
    )

    bucket = report["bucket_reports"]["red_light_turn"]
    assert bucket["records"] == 2
    assert bucket["changed_records"] == 2
    assert bucket["harmful_changed_records"] == 1
    assert bucket["beneficial_changed_records"] == 1
    assert bucket["component_deltas_chosen_minus_current"]["planned_red_light"][
        "mean"
    ] == pytest.approx(7.5)
    assert bucket["worst_changed_records"][0]["delta"] > 0.0
    assert report["decision"]["training_authorized"] is False
    assert report["decision"]["online_selector_change_authorized"] is False

    markdown = render_markdown(report)
    assert "DP-Prior Completion Joint Bucket Failure Attribution" in markdown
    assert "planned_red_light" in markdown
    assert "red_light_turn" in markdown
