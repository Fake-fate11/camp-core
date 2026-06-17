from __future__ import annotations

import json

from scripts.integrations.analyze_diffusion_planner_top1_preserving_failure_attribution import (
    analyze,
    render_markdown,
)


def test_top1_preserving_failure_attribution_splits_false_and_hidden(tmp_path) -> None:
    root = tmp_path / "labeled"
    run_dir = root / "sample_route" / "seed_1" / "npc_0" / "spawn_0p3" / "tl_on" / "static"
    _write_summary(run_dir)
    _write_log(
        run_dir,
        [
            _record(
                selected=1,
                feasible=[True, True],
                proxy_jerk=[1.0, 0.1],
                proxy_lateral=[0.8, 0.2],
                progress_shortfall=[0.2, 0.19],
                outcomes=[
                    _outcome(0, progress=10.0, jerk=5.0, lateral=1.0),
                    _outcome(
                        1,
                        progress=9.99,
                        jerk=3.0,
                        lateral=0.5,
                        near_miss=True,
                    ),
                ],
            ),
            _record(
                selected=0,
                feasible=[True, True],
                proxy_jerk=[1.0, 1.2],
                proxy_lateral=[0.8, 0.9],
                progress_shortfall=[0.2, 0.19],
                outcomes=[
                    _outcome(0, progress=10.0, jerk=5.0, lateral=1.0),
                    _outcome(1, progress=9.99, jerk=3.0, lateral=0.5),
                ],
            ),
            _record(
                selected=1,
                feasible=[True, True],
                proxy_jerk=[1.0, 0.1],
                proxy_lateral=[0.8, 0.2],
                progress_shortfall=[0.2, 0.19],
                outcomes=[
                    _outcome(0, progress=10.0, jerk=5.0, lateral=1.0),
                    _outcome(1, progress=9.99, jerk=3.0, lateral=0.5),
                ],
            ),
        ],
    )

    report = analyze([root], label="unit", max_examples=3)

    assert report["records"]["candidate0_feasible"] == 3
    assert report["records"]["override"] == 2
    assert report["records"]["true_override"] == 1
    assert report["records"]["false_override"] == 1
    assert report["records"]["hidden_outcome"] == 1

    false = report["false_override"]
    assert false["reason_counts"]["outcome_near_miss_worse"] == 1
    assert false["event_summary"]["bool_worse_counts"]["near_miss"] == 1
    assert false["examples"][0]["false_reasons"] == ["outcome_near_miss_worse"]

    hidden = report["hidden_outcome"]
    assert hidden["blocker_counts"]["proxy_jerk_worse"] == 1
    assert hidden["blocker_counts"]["proxy_lateral_worse"] == 1
    assert hidden["blocker_counts"]["no_strict_proxy_comfort_gain"] == 1
    assert hidden["event_summary"]["candidate_label_safety_delta"]["mean"] < 0.0

    markdown = render_markdown(report)
    assert "Top-1-Preserving Failure Attribution" in markdown
    assert "outcome_near_miss_worse" in markdown
    assert "proxy_jerk_worse" in markdown


def _write_summary(run_dir) -> None:
    run_dir.mkdir(parents=True)
    summary = {
        "benchmark": {
            "route": "/tmp/sample_route.pkl",
            "seed": 1,
            "steps": 3,
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
    proxy_jerk: list[float],
    proxy_lateral: list[float],
    progress_shortfall: list[float],
    outcomes: list[dict],
) -> dict:
    weights = [1.0, 0.0, 0.0, 0.0]
    scores = list(progress_shortfall)
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
            [progress, 0.0, 0.0, jerk]
            for progress, jerk in zip(progress_shortfall, proxy_jerk, strict=True)
        ],
        "normalized_atoms": [
            [progress, 0.0, 0.0, jerk]
            for progress, jerk in zip(progress_shortfall, proxy_jerk, strict=True)
        ],
        "selection_normalized_atoms": [
            [progress, 0.0, 0.0, jerk]
            for progress, jerk in zip(progress_shortfall, proxy_jerk, strict=True)
        ],
        "weights": weights,
        "selection_weights": weights,
        "scores": scores,
        "selection_scores": [
            score if is_feasible else float("inf")
            for score, is_feasible in zip(scores, feasible, strict=True)
        ],
        "feasible_mask": feasible,
        "candidate_closed_loop_outcomes": outcomes,
        "candidate_dp_prior_jerk_excess_cost": proxy_jerk,
        "candidate_horizon_lateral_acceleration_cost": proxy_lateral,
        "candidate_horizon_union_planned_red_light_cost": [0.0] * len(feasible),
        "candidate_red_stopping_margin_cost": [0.0] * len(feasible),
    }


def _outcome(
    index: int,
    *,
    progress: float,
    jerk: float,
    lateral: float,
    near_miss: bool = False,
) -> dict:
    return {
        "candidate_index": index,
        "horizon_steps": 30,
        "progress_m": progress,
        "collision": False,
        "near_miss": near_miss,
        "lane_violation": False,
        "red_light_violation": False,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
        "feasible": True,
        "value": progress - jerk - lateral,
    }
