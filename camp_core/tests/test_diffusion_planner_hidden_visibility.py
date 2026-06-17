from __future__ import annotations

import json

from scripts.integrations.analyze_diffusion_planner_hidden_visibility import (
    analyze,
    render_markdown,
)


def test_hidden_visibility_reports_escape_recovery_and_missing_route(tmp_path) -> None:
    root = tmp_path / "labeled"
    run_dir = root / "sample_route" / "seed_1" / "npc_0" / "spawn_0p3" / "tl_on" / "static"
    _write_summary(run_dir)
    _write_log(
        run_dir,
        [
            _record(
                selected=0,
                feasible=[True, True],
                progress_shortfall=[0.20, 0.28],
                proxy_lateral=[0.8, 0.7],
                h10_distance=[10.0, 9.98],
                score=[0.2, 0.1],
                outcomes=[
                    _outcome(0, progress=10.0, jerk=5.0, lateral=1.0),
                    _outcome(1, progress=10.0, jerk=3.0, lateral=0.5),
                ],
            ),
            _record(
                selected=0,
                feasible=[True, True],
                progress_shortfall=[0.20, 0.40],
                proxy_lateral=[0.8, 0.7],
                h10_distance=[10.0, 9.98],
                score=[0.2, 0.1],
                outcomes=[
                    _outcome(0, progress=10.0, jerk=5.0, lateral=1.0),
                    _outcome(1, progress=9.0, jerk=3.0, lateral=0.5),
                ],
            ),
        ],
    )

    report = analyze([root], label="unit", max_examples=2)

    base = report["base_rule"]
    assert base["hidden_outcome_records"] == 1
    assert base["hidden_blocker_counts"]["progress_delta_exceeds_budget"] == 1

    screens = {row["name"]: row for row in report["screens"]}
    h10 = screens["escape_p010_h10_p005_score0"]["summary"]
    assert h10["base_hidden_context_records"] == 1
    assert h10["escape_override_records"] == 1
    assert h10["true_recovery_records"] == 1
    assert h10["false_escape_records"] == 0
    assert h10["hidden_remaining_records"] == 0

    route = screens["escape_p010_route_p005_score0"]["summary"]
    assert route["descriptor_missing_records"] == 1
    assert route["escape_override_records"] == 0
    assert route["hidden_remaining_records"] == 1

    markdown = render_markdown(report)
    assert "Hidden Visibility Audit" in markdown
    assert "escape_p010_h10_p005_score0" in markdown


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
    progress_shortfall: list[float],
    proxy_lateral: list[float],
    h10_distance: list[float],
    score: list[float],
    outcomes: list[dict],
) -> dict:
    weights = [1.0, 0.0, 0.0, 0.0]
    proxy_jerk = [1.0] * len(feasible)
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
        "scores": score,
        "selection_scores": [
            value if is_feasible else float("inf")
            for value, is_feasible in zip(score, feasible, strict=True)
        ],
        "feasible_mask": feasible,
        "candidate_closed_loop_outcomes": outcomes,
        "candidate_dp_prior_jerk_excess_cost": proxy_jerk,
        "candidate_horizon_lateral_acceleration_cost": proxy_lateral,
        "candidate_horizon_union_planned_red_light_cost": [0.0] * len(feasible),
        "candidate_red_stopping_margin_cost": [0.0] * len(feasible),
        "candidate_step_reach": h10_distance,
        "candidate_perfect_tracker_first_step_reach_m": h10_distance,
        "candidate_perfect_tracker_target_speed_mps": h10_distance,
        "candidate_perfect_tracker_open_loop_rollout": {
            "3": {"distance_m": h10_distance},
            "5": {"distance_m": h10_distance},
            "10": {"distance_m": h10_distance},
        },
    }


def _outcome(
    index: int,
    *,
    progress: float,
    jerk: float,
    lateral: float,
) -> dict:
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
