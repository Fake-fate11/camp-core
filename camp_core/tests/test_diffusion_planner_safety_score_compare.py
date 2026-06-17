from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.compare_diffusion_planner_camp_replays import (
    _aggregate_rows,
    _apply_safety_cost_v1,
    _load_scenario_bucket_manifest,
    _paired_deltas,
    _safety_cost_v1_components,
    _safety_gate_assessments,
    _scenario_buckets,
)


ROOT = Path(__file__).resolve().parents[2]


def test_safety_cost_v1_uses_weighted_clipped_components() -> None:
    row = {
        "route_completion_rate": 0.8,
        "obb_collision_rate": 0.01,
        "near_miss_rate": 0.02,
        "lane_violation_rate": 0.03,
        "red_light_violation_rate": 0.04,
        "planned_red_light_violation_rate": 0.05,
        "mean_jerk_magnitude_mps3": 20.0,
        "mean_lateral_acceleration_mps2": 1.0,
    }

    components = _safety_cost_v1_components(row)

    assert components["available"]
    assert components["raw_components"]["route_shortfall"] == pytest.approx(0.2)
    assert components["raw_components"]["mean_jerk"] == pytest.approx(2.0)
    assert components["raw_components"]["mean_lateral_acceleration"] == pytest.approx(
        0.5
    )
    assert components["cost"] == pytest.approx(7.15)


def test_safety_gate_requires_hard_gate_and_lower_paired_score() -> None:
    rows = []
    for variant, completion, jerk, lateral, contract in (
        ("top1", 0.80, 20.0, 2.0, False),
        ("static", 0.82, 10.0, 1.0, True),
    ):
        for seed in (1, 2):
            row = {
                "variant": variant,
                "run_key": f"run-{seed}",
                "seed": seed,
                "route_completion_rate": completion,
                "obb_collision_rate": 0.0,
                "near_miss_rate": 0.0,
                "lane_violation_rate": 0.0,
                "red_light_violation_rate": 0.0,
                "planned_red_light_violation_rate": 0.0,
                "mean_jerk_magnitude_mps3": jerk,
                "mean_lateral_acceleration_mps2": lateral,
                "p95_selection_latency_ms": 80.0,
                "finite_candidate_contract_verified": contract,
            }
            _apply_safety_cost_v1(row)
            rows.append(row)

    aggregates = _aggregate_rows(rows)
    paired = _paired_deltas(rows, baseline="top1")
    gates = _safety_gate_assessments(
        rows,
        paired,
        aggregates,
        baseline="top1",
    )

    assert len(gates) == 1
    gate = gates[0]
    assert gate["hard_gate_passed"]
    assert gate["safety_cost_claim_passed"]
    assert gate["checks"]["safety_cost_significantly_lower"]["delta"][
        "ci95_high"
    ] < 0.0


def test_scenario_bucket_manifest_is_explicit_only(tmp_path) -> None:
    manifest_path = tmp_path / "buckets.json"
    manifest_path.write_text(
        json.dumps(
            {
                "routes": {
                    "sample59_86": ["traffic_light", "red_light_turn"],
                },
                "run_keys": {
                    "custom-run": ["dense_scene"],
                },
            }
        ),
        encoding="utf-8",
    )
    manifest = _load_scenario_bucket_manifest(manifest_path)

    assert _scenario_buckets(
        {"route_name": "sample59_86", "run_key": "other"},
        manifest,
    ) == ["overall", "traffic_light", "red_light_turn"]
    assert _scenario_buckets(
        {"route_name": "unlabeled", "run_key": "custom-run"},
        manifest,
    ) == ["overall", "dense_scene"]
    assert _scenario_buckets(
        {"route_name": "unlabeled", "run_key": "other"},
        manifest,
    ) == ["overall"]


def test_scenario_bucket_manifest_filters_match_configuration_only(tmp_path) -> None:
    manifest_path = tmp_path / "buckets.json"
    manifest_path.write_text(
        json.dumps(
            {
                "routes": {
                    "sample59": ["sharp_turn"],
                },
                "filters": [
                    {
                        "name": "sample59_tl_on",
                        "match": {
                            "route_name": "sample59",
                            "traffic_lights": True,
                            "max_npcs": [0, 4],
                        },
                        "buckets": ["traffic_light", "red_light_turn"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest = _load_scenario_bucket_manifest(manifest_path)

    assert _scenario_buckets(
        {
            "route_name": "sample59",
            "run_key": "run-on",
            "traffic_lights": True,
            "max_npcs": 4,
        },
        manifest,
    ) == ["overall", "sharp_turn", "traffic_light", "red_light_turn"]
    assert _scenario_buckets(
        {
            "route_name": "sample59",
            "run_key": "run-off",
            "traffic_lights": False,
            "max_npcs": 4,
        },
        manifest,
    ) == ["overall", "sharp_turn"]


def test_scenario_bucket_manifest_rejects_outcome_filter_fields(tmp_path) -> None:
    manifest_path = tmp_path / "buckets.json"
    manifest_path.write_text(
        json.dumps(
            {
                "filters": [
                    {
                        "name": "metric_leak",
                        "match": {"red_light_violation_rate": 0.0},
                        "buckets": ["traffic_light"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported match field"):
        _load_scenario_bucket_manifest(manifest_path)


def test_committed_development_scenario_manifest_is_explicit_only() -> None:
    manifest_path = (
        ROOT
        / "configs"
        / "integrations"
        / "dp_camp_development_scenario_buckets_redstopfloor05_v1.json"
    )
    manifest = _load_scenario_bucket_manifest(manifest_path)

    assert manifest["default_buckets"] == []
    assert _scenario_buckets(
        {
            "route_name": "sample_map_tl_route_59_to_86",
            "traffic_lights": True,
            "max_npcs": 4,
            "run_key": "sample59-on",
        },
        manifest,
    ) == ["overall", "sharp_turn", "traffic_light", "red_light_turn"]
    assert _scenario_buckets(
        {
            "route_name": "sample_map_tl_route_59_to_86",
            "traffic_lights": False,
            "max_npcs": 4,
            "run_key": "sample59-off",
        },
        manifest,
    ) == ["overall", "sharp_turn"]
    assert _scenario_buckets(
        {
            "route_name": "sample_map_route_2_to_104",
            "traffic_lights": False,
            "max_npcs": 0,
            "run_key": "normal",
        },
        manifest,
    ) == ["overall", "normal"]
    assert _scenario_buckets(
        {
            "route_name": "sample_map_route_2_to_104",
            "traffic_lights": False,
            "max_npcs": 4,
            "run_key": "npc-not-yet-labeled",
        },
        manifest,
    ) == ["overall"]
