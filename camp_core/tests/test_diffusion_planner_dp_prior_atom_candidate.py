from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_dp_prior_atom_candidate import (
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
    outcomes: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "num_candidates": 2,
        "selected_index": selected_index,
        "feasible_mask": [True, True],
        "selection_scores": scores,
        "candidate_dp_prior_deviation_cost": prior,
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0],
        "candidate_closed_loop_outcomes": outcomes,
    }


def test_dp_prior_atom_candidate_audit_replays_alpha_zero_and_scores_virtual_atom(
    tmp_path,
) -> None:
    root = tmp_path / "matrix"
    log_dir = root / "route_a" / "seed_3" / "npc_4" / "spawn_0p6" / "tl_off" / "static"
    log_dir.mkdir(parents=True)
    (log_dir / "camp_selection_log.json").write_text(
        json.dumps(
            [
                _record(
                    selected_index=1,
                    scores=[0.2, 0.0],
                    prior=[0.0, 10.0],
                    outcomes=[
                        _outcome(),
                        _outcome(lane_violation=True),
                    ],
                ),
                _record(
                    selected_index=1,
                    scores=[0.2, 0.0],
                    prior=[0.0, 0.1],
                    outcomes=[
                        _outcome(near_miss=True),
                        _outcome(),
                    ],
                ),
                _record(
                    selected_index=1,
                    scores=[float("inf"), float("inf")],
                    prior=[0.0, 0.1],
                    outcomes=[
                        _outcome(),
                        _outcome(),
                    ],
                ),
            ]
        ),
        encoding="utf-8",
    )

    report = analyze(
        [root],
        label="unit",
        scale_percentile=95.0,
        alphas=(0.0, 0.4),
        bootstrap_resamples=64,
        seed=7,
    )

    assert report["records"]["total"] == 3
    assert report["analysis"]["candidate_atom"]["nonnegative"] is True
    assert report["analysis"]["candidate_atom"]["candidate0_value"] == 0.0
    assert report["selected_vs_top1"][
        "harmful_selected_with_positive_prior_delta"
    ] == 1
    assert report["selected_vs_top1"][
        "beneficial_selected_with_positive_prior_delta"
    ] == 1

    by_alpha = {row["alpha"]: row for row in report["alphas"]}
    assert by_alpha[0.0]["changed_from_current_rate"] == 0.0
    assert by_alpha[0.0]["safety_cost_delta_vs_current"]["mean"] == pytest.approx(0.0)
    assert by_alpha[0.4]["harmful_current_changed_rate"] == pytest.approx(1.0)
    assert by_alpha[0.4]["beneficial_current_preserved_rate"] == pytest.approx(1.0)
    assert by_alpha[0.4]["safety_cost_delta_vs_current"]["mean"] < 0.0

    markdown = render_markdown(report)
    assert "DP-Prior Deviation Atom Candidate Audit" in markdown
    assert "affine scores" in markdown
    assert "Benders" in markdown
