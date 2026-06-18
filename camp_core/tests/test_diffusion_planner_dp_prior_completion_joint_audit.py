from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_dp_prior_completion_joint_audit import (
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
    selected_index: int,
    scores: list[float],
    prior: list[float],
    planned_progress: list[float],
    outcomes: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "num_candidates": 2,
        "selected_index": selected_index,
        "feasible_mask": [True, True],
        "selection_scores": scores,
        "candidate_dp_prior_deviation_cost": prior,
        "candidate_route_progress": planned_progress,
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0],
        "candidate_closed_loop_outcomes": outcomes,
    }


def test_joint_dp_prior_progress_audit_preserves_progress_benefit(tmp_path) -> None:
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
                    selected_index=1,
                    scores=[0.2, 0.0],
                    prior=[0.0, 10.0],
                    planned_progress=[10.0, 10.0],
                    outcomes=[
                        _outcome(),
                        _outcome(lane_violation=True, progress_m=5.0),
                    ],
                ),
                _record(
                    selected_index=1,
                    scores=[0.2, 0.0],
                    prior=[0.0, 10.0],
                    planned_progress=[5.0, 10.0],
                    outcomes=[
                        _outcome(near_miss=True, progress_m=5.0),
                        _outcome(progress_m=10.0),
                    ],
                ),
                _record(
                    selected_index=1,
                    scores=[float("inf"), float("inf")],
                    prior=[0.0, 0.1],
                    planned_progress=[10.0, 10.0],
                    outcomes=[
                        _outcome(progress_m=10.0),
                        _outcome(progress_m=10.0),
                    ],
                ),
            ]
        ),
        encoding="utf-8",
    )

    report = analyze(
        [root],
        label="unit",
        alphas=(0.0, 0.4),
        betas=(0.0, 0.4),
        bootstrap_resamples=64,
        seed=7,
        min_progress_delta_ci_low=-0.1,
        required_buckets=("red_light_turn",),
    )

    assert report["records"]["total"] == 3
    assert report["records"]["bucket_record_counts"]["red_light_turn"] == 3
    assert report["opportunity_coverage"]["overall"]["harmful_current_records"] == 1
    assert report["opportunity_coverage"]["overall"]["beneficial_current_records"] == 1

    joint = _grid(report, alpha=0.4, beta=0.4)
    alpha_only = _grid(report, alpha=0.4, beta=0.0)
    beta_only = _grid(report, alpha=0.0, beta=0.4)
    assert joint["overall"]["beneficial_current_preserved_rate"] == pytest.approx(1.0)
    assert joint["overall"]["safety_cost_delta_vs_current"]["mean"] < 0.0
    assert joint["overall"]["hard_nonworse_vs_current"] == pytest.approx(1.0)
    assert alpha_only["overall"]["beneficial_current_preserved_rate"] < 1.0
    assert beta_only["overall"]["safety_cost_delta_vs_current"]["mean"] == pytest.approx(
        0.0
    )

    markdown = render_markdown(report)
    assert "DP-Prior Completion Joint Audit" in markdown
    assert "not classical Benders decomposition" in markdown
    assert "red_light_turn" in markdown


def _grid(report: dict, *, alpha: float, beta: float) -> dict:
    for row in report["grid"]:
        if row["alpha"] == pytest.approx(alpha) and row["beta"] == pytest.approx(beta):
            return row
    raise AssertionError(f"missing grid row alpha={alpha}, beta={beta}")
