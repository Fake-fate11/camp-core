from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_safety_cost_oracle import (
    analyze,
    render_markdown,
)


def _outcome(
    index: int,
    *,
    progress: float,
    jerk: float,
    lateral: float,
    collision: bool = False,
    near_miss: bool = False,
    lane_violation: bool = False,
    red_light_violation: bool = False,
) -> dict[str, object]:
    return {
        "candidate_index": index,
        "progress_m": progress,
        "collision": collision,
        "near_miss": near_miss,
        "lane_violation": lane_violation,
        "red_light_violation": red_light_violation,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
    }


def _record(
    *,
    selected_index: int = 0,
    feasible_mask: list[bool] | None = None,
) -> dict[str, object]:
    return {
        "num_candidates": 3,
        "selected_index": selected_index,
        "feasible_mask": feasible_mask or [True, True, True],
        "candidate_horizon_union_planned_red_light_cost": [1.0, 0.0, 0.0],
        "candidate_closed_loop_outcomes": [
            _outcome(
                0,
                progress=10.0,
                jerk=8.0,
                lateral=2.0,
                red_light_violation=True,
            ),
            _outcome(1, progress=9.9, jerk=3.0, lateral=1.0),
            _outcome(2, progress=4.0, jerk=0.5, lateral=0.2),
        ],
    }


def _write_log(tmp_path, record: dict[str, object]):
    root = (
        tmp_path
        / "dev_root"
        / "sample_map_tl_route_59_to_86"
        / "seed_1"
        / "npc_4"
        / "spawn_0p3"
        / "tl_on"
        / "static"
    )
    root.mkdir(parents=True)
    log_path = root / "camp_selection_log.json"
    log_path.write_text(json.dumps([record]), encoding="utf-8")
    (root / "camp_validation_summary.json").write_text(
        json.dumps(
            {
                "benchmark": {
                    "route": "/routes/sample_map_tl_route_59_to_86.pkl",
                    "seed": 1,
                    "steps": 200,
                    "max_npcs": 4,
                    "spawn_probability": 0.3,
                    "traffic_lights": True,
                    "advance_mode": "perfect",
                }
            }
        ),
        encoding="utf-8",
    )
    return log_path


def test_safety_cost_oracle_reports_candidate_pool_opportunity(tmp_path) -> None:
    report = analyze([_write_log(tmp_path, _record())])
    overall = report["overall"]

    assert report["records"]["base_feasible"] == 1
    assert overall["record_rates"]["oracle_beats_top1"] == 1.0
    assert overall["record_rates"]["camp_matches_top1"] == 1.0
    assert overall["record_rates"]["camp_matches_oracle"] == 0.0
    assert overall["run_level_delta_ci"]["oracle_minus_top1"]["mean"] < 0.0
    assert overall["run_level_delta_ci"]["camp_minus_top1"]["mean"] == 0.0
    assert overall["hard_component_nonworse_rate"][
        "oracle_realized_red_light_vs_top1"
    ] == 1.0
    assert overall["planned_red_sources"] == {
        "candidate_horizon_union_planned_red_light_cost": 1
    }

    markdown = render_markdown(report)
    assert "Candidate-Branch SafetyCost v1 Oracle Audit" in markdown
    assert "does not change the online selector" in markdown


def test_safety_cost_oracle_keeps_fallback_branch_separate(tmp_path) -> None:
    report = analyze(
        [_write_log(tmp_path, _record(selected_index=2, feasible_mask=[False, False, False]))]
    )

    assert report["records"]["base_feasible"] == 0
    assert report["records"]["fallback_all_infeasible"] == 1
    assert report["overall"]["fallback_all_infeasible_records"] == 1
    assert report["overall"]["record_rates"]["oracle_beats_top1"] == 1.0


def test_safety_cost_oracle_reports_explicit_scenario_buckets(tmp_path) -> None:
    log_path = _write_log(tmp_path, _record())
    manifest_path = tmp_path / "scenario_buckets.json"
    manifest_path.write_text(
        json.dumps(
            {
                "routes": {},
                "run_keys": {},
                "filters": [
                    {
                        "name": "tl_on_turn",
                        "match": {
                            "route_name": "sample_map_tl_route_59_to_86",
                            "traffic_lights": True,
                        },
                        "buckets": ["traffic_light", "red_light_turn"],
                    }
                ],
                "default_buckets": [],
            }
        ),
        encoding="utf-8",
    )

    report = analyze([log_path], scenario_bucket_manifest=manifest_path)
    buckets = {row["bucket"]: row for row in report["by_bucket"]}

    assert sorted(buckets) == ["overall", "red_light_turn", "traffic_light"]
    assert buckets["traffic_light"]["record_rates"]["oracle_beats_top1"] == 1.0
    assert report["records"]["scenario_bucket_counts"]["red_light_turn"] == 1


def test_safety_cost_oracle_requires_candidate_outcomes(tmp_path) -> None:
    record = _record()
    record["candidate_closed_loop_outcomes"] = None

    with pytest.raises(ValueError, match="candidate outcomes"):
        analyze([_write_log(tmp_path, record)])
