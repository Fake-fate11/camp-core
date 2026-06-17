from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_candidate_availability import (
    analyze,
)


def _record() -> dict:
    outcomes = [
        {
            "candidate_index": 0,
            "progress_m": 10.0,
            "mean_jerk_mps3": 4.0,
            "mean_lateral_acceleration_mps2": 2.0,
            "collision": False,
            "near_miss": False,
            "lane_violation": False,
            "red_light_violation": False,
            "feasible": True,
        },
        {
            "candidate_index": 1,
            "progress_m": 10.0,
            "mean_jerk_mps3": 3.0,
            "mean_lateral_acceleration_mps2": 1.0,
            "collision": False,
            "near_miss": False,
            "lane_violation": False,
            "red_light_violation": False,
            "feasible": True,
        },
        {
            "candidate_index": 2,
            "progress_m": 9.0,
            "mean_jerk_mps3": 1.0,
            "mean_lateral_acceleration_mps2": 0.5,
            "collision": False,
            "near_miss": False,
            "lane_violation": False,
            "red_light_violation": False,
            "feasible": True,
        },
    ]
    return {
        "num_candidates": 3,
        "selected_index": 0,
        "feasible_mask": [True, True, True],
        "atom_names": ["progress_shortfall"],
        "atoms": [[0.0], [0.0], [0.2]],
        "candidate_horizon_lateral_acceleration_cost": [2.0, 3.0, 0.5],
        "candidate_dp_prior_jerk_excess_cost": [4.0, 5.0, 1.0],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0, 0.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.0, 0.0],
        "candidate_closed_loop_outcomes": outcomes,
    }


def _write_log(tmp_path, record: dict):
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps([record]), encoding="utf-8")
    return path


def _write_log_with_summary(tmp_path, record: dict):
    path = _write_log(tmp_path, record)
    summary = {
        "benchmark": {
            "route": "/assets/sample_map_tl_route_59_to_86.pkl",
            "seed": 1,
            "steps": 200,
            "max_npcs": 4,
            "spawn_probability": 0.3,
            "traffic_lights": True,
            "advance_mode": "perfect",
        }
    }
    (tmp_path / "camp_validation_summary.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )
    return path


def test_candidate_availability_finds_hidden_outcome_pareto(tmp_path) -> None:
    report = analyze([_write_log(tmp_path, _record())])
    zero_budget = report["budgets"][0]

    assert report["records"]["nonfallback"] == 1
    assert report["records"]["scenario_bucket_counts"]["overall"]["records"] == 1
    assert zero_budget["outcome_weak_records"] == 1
    assert zero_budget["outcome_joint_records"] == 1
    assert zero_budget["proxy_weak_records"] == 0
    assert zero_budget["hidden_outcome_weak_records"] == 1
    assert zero_budget["by_bucket"][0]["bucket"] == "overall"
    assert zero_budget["best_outcome_delta_mean"]["progress_m"] == 0.0
    assert zero_budget["best_outcome_delta_mean"]["mean_jerk_mps3"] == -1.0
    assert zero_budget["best_outcome_delta_mean"][
        "mean_lateral_acceleration_mps2"
    ] == -1.0


def test_candidate_availability_proxy_finds_budgeted_branch(tmp_path) -> None:
    report = analyze([_write_log(tmp_path, _record())])
    wide_budget = report["budgets"][-1]

    assert wide_budget["proxy_weak_records"] == 1
    assert wide_budget["best_proxy_delta_mean"]["progress_shortfall"] == 0.2
    assert wide_budget["best_proxy_delta_mean"]["proxy_jerk"] == -3.0
    assert wide_budget["best_proxy_delta_mean"]["proxy_lateral"] == -1.5


def test_candidate_availability_reports_explicit_scenario_buckets(tmp_path) -> None:
    log_path = _write_log_with_summary(tmp_path, _record())
    manifest_path = tmp_path / "scenario_buckets.json"
    manifest_path.write_text(
        json.dumps(
            {
                "filters": [
                    {
                        "name": "sample_tl_on",
                        "match": {
                            "route_name": "sample_map_tl_route_59_to_86",
                            "traffic_lights": True,
                        },
                        "buckets": ["traffic_light", "red_light_turn"],
                    }
                ],
                "routes": {},
                "run_keys": {},
                "default_buckets": [],
            }
        ),
        encoding="utf-8",
    )

    report = analyze([log_path], scenario_bucket_manifest=manifest_path)
    zero_budget = report["budgets"][0]
    by_bucket = {bucket["bucket"]: bucket for bucket in zero_budget["by_bucket"]}

    assert sorted(by_bucket) == ["overall", "red_light_turn", "traffic_light"]
    assert by_bucket["traffic_light"]["outcome_joint_records"] == 1
    assert by_bucket["red_light_turn"]["hidden_outcome_weak_records"] == 1
    assert report["analysis"]["explicit_bucket_labels_only"] is True


def test_candidate_availability_requires_outcomes(tmp_path) -> None:
    record = _record()
    record["candidate_closed_loop_outcomes"] = None

    with pytest.raises(ValueError, match="candidate outcomes"):
        analyze([_write_log(tmp_path, record)])
