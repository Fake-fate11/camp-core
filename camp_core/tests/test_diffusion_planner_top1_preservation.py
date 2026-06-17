from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_top1_preservation import (
    analyze,
    render_markdown,
)


def test_top1_preservation_attributes_candidate0_feasible_override(tmp_path) -> None:
    root = tmp_path / "labeled"
    run_dir = root / "sample_route" / "seed_1" / "npc_0" / "spawn_0p3" / "tl_on" / "static"
    _write_summary(run_dir)
    _write_log(
        run_dir,
        [
            _record(
                selected=1,
                feasible=[True, True, True],
                atoms=[
                    [1.0, 0.0, 0.0, 1.0],
                    [0.2, 0.0, 0.0, 0.1],
                    [0.8, 0.0, 0.0, 0.8],
                ],
                outcomes=[
                    _outcome(0, progress=10.0, jerk=6.0, lateral=1.0),
                    _outcome(1, progress=9.98, jerk=4.0, lateral=0.5),
                    _outcome(2, progress=9.0, jerk=7.0, lateral=1.2),
                ],
                proxy_jerk=[1.0, 0.1, 0.8],
                proxy_lateral=[0.6, 0.2, 0.7],
            ),
            _record(
                selected=2,
                feasible=[False, False, True],
                atoms=[
                    [0.1, 0.0, 0.0, 0.1],
                    [0.2, 0.0, 0.0, 0.2],
                    [0.3, 0.0, 0.0, 0.3],
                ],
                outcomes=[
                    _outcome(0, progress=10.0, jerk=4.0, lateral=0.5),
                    _outcome(1, progress=9.5, jerk=4.5, lateral=0.6),
                    _outcome(2, progress=9.0, jerk=5.0, lateral=0.7),
                ],
                proxy_jerk=[0.1, 0.2, 0.3],
                proxy_lateral=[0.1, 0.2, 0.3],
            ),
        ],
    )

    report = analyze([root], progress_budgets_m=(0.05,), label="unit")

    assert report["records"]["logs"] == 1
    assert report["records"]["total"] == 2
    assert report["preservation_categories"] == {
        "candidate0_feasible_selected_nonzero": 1,
        "candidate0_infeasible_selected_nonzero": 1,
    }

    active = report["candidate0_feasible_active_override"]
    assert active["records"] == 1
    assert active["selection_score_delta_selected_minus_candidate0"]["mean"] < 0.0
    assert active["outcome_delta_selected_minus_candidate0"]["progress_m"][
        "mean"
    ] == pytest.approx(-0.02)

    attractive_atoms = active["top_attractive_atoms"]
    assert attractive_atoms[0]["atom"] == "dp_prior_jerk_excess_cost"
    assert attractive_atoms[0]["sum_contribution"] < 0.0

    oracle = report["candidate_availability_oracle"][0]
    assert oracle["candidate0_feasible_records"] == 1
    assert oracle["outcome_override_available_records"] == 1
    assert oracle["proxy_override_available_records"] == 1
    assert oracle["selected_matches_outcome_records"] == 1
    assert oracle["selected_nonzero_without_outcome_records"] == 0

    markdown = render_markdown(report)
    assert "Top-1 Preservation Attribution" in markdown
    assert "dp_prior_jerk_excess_cost" in markdown


def test_top1_preservation_rejects_missing_outcome_labels(tmp_path) -> None:
    root = tmp_path / "labeled"
    run_dir = root / "sample_route" / "seed_1" / "npc_0" / "spawn_0p3" / "tl_on" / "static"
    _write_summary(run_dir)
    record = _record(
        selected=1,
        feasible=[True, True],
        atoms=[[1.0, 0.0, 0.0, 1.0], [0.2, 0.0, 0.0, 0.1]],
        outcomes=[
            _outcome(0, progress=10.0, jerk=6.0, lateral=1.0),
            _outcome(1, progress=9.98, jerk=4.0, lateral=0.5),
        ],
        proxy_jerk=[1.0, 0.1],
        proxy_lateral=[0.6, 0.2],
    )
    record["candidate_closed_loop_outcomes"] = None
    _write_log(run_dir, [record])

    with pytest.raises(ValueError, match="candidate outcomes"):
        analyze([root])


def _write_summary(run_dir) -> None:
    run_dir.mkdir(parents=True)
    summary = {
        "benchmark": {
            "route": "/tmp/sample_route.pkl",
            "seed": 1,
            "steps": 2,
            "max_npcs": 0,
            "spawn_probability": 0.3,
            "traffic_lights": True,
            "advance_mode": "perfect",
        }
    }
    (run_dir / "camp_validation_summary.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )


def _write_log(run_dir, records: list[dict]) -> None:
    (run_dir / "camp_selection_log.json").write_text(
        json.dumps(records),
        encoding="utf-8",
    )


def _record(
    *,
    selected: int,
    feasible: list[bool],
    atoms: list[list[float]],
    outcomes: list[dict],
    proxy_jerk: list[float],
    proxy_lateral: list[float],
) -> dict:
    weights = [0.1, 0.0, 0.0, 1.0]
    scores = [
        sum(value * weight for value, weight in zip(row, weights, strict=True))
        for row in atoms
    ]
    masked_scores = [
        score if is_feasible else float("inf")
        for score, is_feasible in zip(scores, feasible, strict=True)
    ]
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
        "atoms": atoms,
        "normalized_atoms": atoms,
        "selection_normalized_atoms": atoms,
        "weights": weights,
        "selection_weights": weights,
        "scores": scores,
        "selection_scores": masked_scores,
        "feasible_mask": feasible,
        "candidate_closed_loop_outcomes": outcomes,
        "candidate_dp_prior_jerk_excess_cost": proxy_jerk,
        "candidate_horizon_lateral_acceleration_cost": proxy_lateral,
        "candidate_horizon_union_planned_red_light_cost": [0.0] * len(feasible),
        "candidate_red_stopping_margin_cost": [0.0] * len(feasible),
    }


def _outcome(index: int, *, progress: float, jerk: float, lateral: float) -> dict:
    return {
        "candidate_index": index,
        "horizon_steps": 30,
        "progress_m": progress,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
        "feasible": True,
        "value": progress - jerk - lateral,
    }
