from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_route_h10_shadow_selector import (
    analyze,
    render_markdown,
)


def test_route_h10_shadow_selector_is_fail_closed_and_reports_logged_delta(tmp_path) -> None:
    root = tmp_path / "labeled"
    run_dir = root / "sample_route" / "seed_1" / "npc_4" / "spawn_0p3" / "tl_on" / "static"
    _write_summary(run_dir)
    _write_log(
        run_dir,
        [
            _record(
                selected=1,
                feasible=[True, True],
                progress_shortfall=[0.20, 0.22],
                proxy_lateral=[0.8, 0.7],
                h10_distance=[10.0, 10.0],
                route_progress=None,
                score=[0.2, 0.1],
                outcomes=[
                    _outcome(0, progress=10.0, jerk=5.0, lateral=1.0),
                    _outcome(1, progress=10.0, jerk=3.0, lateral=0.5),
                ],
            ),
            _record(
                selected=0,
                feasible=[True, True],
                progress_shortfall=[1.00, 0.70],
                proxy_lateral=[0.8, 0.7],
                h10_distance=[10.0, 10.14],
                route_progress=[10.0, 10.0],
                score=[0.2, 0.1],
                outcomes=[
                    _outcome(0, progress=10.0, jerk=5.0, lateral=1.0),
                    _outcome(1, progress=10.0, jerk=3.0, lateral=0.5),
                ],
            ),
            _record(
                selected=1,
                feasible=[True, True],
                progress_shortfall=[1.00, 0.70],
                proxy_lateral=[0.8, 0.7],
                h10_distance=[10.0, 10.20],
                route_progress=[10.0, 10.0],
                score=[0.2, 0.1],
                outcomes=[
                    _outcome(0, progress=10.0, jerk=5.0, lateral=1.0),
                    _outcome(1, progress=10.0, jerk=3.0, lateral=0.5, near_miss=True),
                ],
            ),
            _record(
                selected=0,
                feasible=[True, True],
                progress_shortfall=[1.00, 0.70],
                proxy_lateral=[0.8, 0.7],
                h10_distance=[10.0, 10.10],
                route_progress=None,
                score=[0.2, 0.1],
                outcomes=[
                    _outcome(0, progress=10.0, jerk=5.0, lateral=1.0),
                    _outcome(1, progress=10.0, jerk=3.0, lateral=0.5),
                ],
            ),
            _record(
                selected=1,
                feasible=[False, True],
                progress_shortfall=[1.00, 0.70],
                proxy_lateral=[0.8, 0.7],
                h10_distance=[10.0, 10.10],
                route_progress=[10.0, 10.0],
                score=[0.2, 0.1],
                outcomes=[
                    _outcome(0, progress=10.0, jerk=5.0, lateral=1.0),
                    _outcome(1, progress=10.0, jerk=3.0, lateral=0.5),
                ],
            ),
        ],
    )

    report = analyze([root], label="unit", max_examples=4)

    assert report["records"]["total"] == 5
    assert report["records"]["candidate0_feasible"] == 4
    assert report["records"]["candidate0_infeasible"] == 1
    assert report["records"]["descriptor_missing_when_escape_needed"] == 1
    assert report["candidate0_feasible_stage_counts"] == {
        "base": 1,
        "candidate0_retain_descriptor_missing": 1,
        "candidate0_retain_empty_mask": 1,
        "route_h10_escape": 1,
    }

    shadow = report["shadow_vs_candidate0"]
    assert shadow["override_records"] == 2
    assert shadow["true_override_records"] == 2
    assert shadow["false_override_records"] == 0
    assert all(value == 0 for value in shadow["hard_gate_bool_worse_records"].values())

    logged = report["logged_vs_candidate0"]
    assert logged["override_records"] == 2
    assert logged["true_override_records"] == 1
    assert logged["false_override_records"] == 1
    assert logged["hard_gate_bool_worse_records"]["near_miss"] == 1
    assert logged["false_reason_counts"]["outcome_near_miss_worse"] == 1

    assert report["shadow_vs_logged"]["different_records"] == 2
    assert report["shadow_vs_logged"]["shadow_removes_logged_override_records"] == 1
    assert report["shadow_vs_logged"]["shadow_adds_override_records"] == 1

    route_examples = report["examples"]["route_h10_escape"]
    assert len(route_examples) == 1
    assert route_examples[0]["selected"] == 1
    assert route_examples[0]["logged_selected"] == 0
    assert route_examples[0]["selected_candidate"]["h10_distance_loss"] == pytest.approx(-0.14)

    markdown = render_markdown(report)
    assert "Route-H10 Shadow Selector Audit" in markdown
    assert "base_then_route_nonworse_h10_lower_m015_score0" in markdown
    assert "| `shadow` | 2 | 2 | 0 |" in markdown


def _write_summary(run_dir) -> None:
    run_dir.mkdir(parents=True)
    summary = {
        "benchmark": {
            "route": "/tmp/sample_route.pkl",
            "seed": 1,
            "steps": 5,
            "max_npcs": 4,
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
    route_progress: list[float] | None,
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
        "candidate_route_progress": route_progress,
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
