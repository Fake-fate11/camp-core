from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_safety_cost_oracle import (
    analyze,
    main,
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


def _write_log(
    tmp_path,
    record: dict[str, object],
    *,
    route_dir: str = "sample_map_tl_route_59_to_86",
    route_path: str = "/routes/sample_map_tl_route_59_to_86.pkl",
):
    root = (
        tmp_path
        / "dev_root"
        / route_dir
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
                    "route": route_path,
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
    assert overall["record_rates"]["hard_guarded_oracle_available"] == 1.0
    assert overall["record_rates"]["hard_guarded_oracle_beats_top1"] == 1.0
    assert overall["record_rates"]["camp_matches_top1"] == 1.0
    assert overall["record_rates"]["camp_matches_oracle"] == 0.0
    assert overall["record_rates"]["camp_matches_hard_guarded_oracle"] == 0.0
    assert overall["run_level_delta_ci"]["oracle_minus_top1"]["mean"] < 0.0
    assert (
        overall["run_level_delta_ci"]["hard_guarded_oracle_minus_top1"]["mean"]
        < 0.0
    )
    assert overall["run_level_delta_ci"]["camp_minus_top1"]["mean"] == 0.0
    assert overall["hard_component_nonworse_rate"][
        "oracle_realized_red_light_vs_top1"
    ] == 1.0
    assert overall["hard_component_nonworse_rate"][
        "hard_guarded_oracle_lane_violation_vs_top1"
    ] == 1.0
    assert overall["planned_red_sources"] == {
        "candidate_horizon_union_planned_red_light_cost": 1
    }
    assert "normal" in report["coverage_gaps"]["missing_required_buckets"]
    assert report["opportunity_gate"]["passed"] is False
    diagnostics = report["opportunity_diagnostics"]
    assert diagnostics["candidate_pool_coverage"]["mean_candidate_count"] == 3.0
    assert diagnostics["candidate_pool_coverage"][
        "eligible_candidate_count_distribution"
    ] == {"3": 1}
    assert diagnostics["failure_mode_counts"][
        "camp_not_oracle_when_oracle_beats_top1"
    ] == 1
    assert diagnostics["failure_mode_rates"]["camp_worse_than_top1"] == 0.0

    markdown = render_markdown(report)
    assert "Candidate-Branch SafetyCost v1 Oracle Audit" in markdown
    assert "Hard-guarded oracle" in markdown
    assert "Candidate Pool Coverage" in markdown
    assert "Failure Modes" in markdown
    assert "does not change the online selector" in markdown


def test_safety_cost_oracle_reports_hard_guarded_tradeoff(tmp_path) -> None:
    record = {
        "num_candidates": 3,
        "selected_index": 0,
        "feasible_mask": [True, True, True],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0, 0.0],
        "candidate_closed_loop_outcomes": [
            _outcome(0, progress=10.0, jerk=150.0, lateral=20.0),
            _outcome(
                1,
                progress=10.0,
                jerk=0.0,
                lateral=0.0,
                lane_violation=True,
            ),
            _outcome(2, progress=10.0, jerk=150.0, lateral=15.0),
        ],
    }

    report = analyze([_write_log(tmp_path, record)], required_buckets=())
    overall = report["overall"]

    assert overall["record_rates"]["oracle_beats_top1"] == 1.0
    assert overall["record_rates"]["hard_guarded_oracle_beats_top1"] == 1.0
    assert overall["hard_component_nonworse_rate"]["oracle_lane_violation_vs_top1"] == 0.0
    assert overall["hard_component_nonworse_rate"][
        "hard_guarded_oracle_lane_violation_vs_top1"
    ] == 1.0
    assert overall["cost_mean"]["oracle"] < overall["cost_mean"][
        "hard_guarded_oracle"
    ] < overall["cost_mean"]["top1"]
    assert report["opportunity_gate"]["passed"] is True


def test_safety_cost_oracle_reports_unavailable_hard_guarded_oracle(
    tmp_path,
) -> None:
    record = {
        "num_candidates": 3,
        "selected_index": 1,
        "feasible_mask": [False, True, True],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0, 0.0],
        "candidate_closed_loop_outcomes": [
            _outcome(0, progress=10.0, jerk=2.0, lateral=0.5),
            _outcome(1, progress=10.0, jerk=1.0, lateral=0.5, lane_violation=True),
            _outcome(
                2,
                progress=10.0,
                jerk=1.0,
                lateral=0.5,
                red_light_violation=True,
            ),
        ],
    }

    report = analyze([_write_log(tmp_path, record)], required_buckets=())
    overall = report["overall"]

    assert overall["record_rates"]["hard_guarded_oracle_available"] == 0.0
    assert overall["failure_mode_counts"]["hard_guarded_oracle_unavailable"] == 1
    assert overall["candidate_pool_coverage"]["top1_eligible_rate"] == 0.0
    assert report["opportunity_diagnostics"]["failure_mode_rates"][
        "hard_guarded_oracle_not_better_than_top1"
    ] == 1.0


def test_safety_cost_oracle_keeps_fallback_branch_separate(tmp_path) -> None:
    report = analyze(
        [_write_log(tmp_path, _record(selected_index=2, feasible_mask=[False, False, False]))]
    )

    assert report["records"]["base_feasible"] == 0
    assert report["records"]["fallback_all_infeasible"] == 1
    assert report["overall"]["fallback_all_infeasible_records"] == 1
    assert report["overall"]["record_rates"]["oracle_beats_top1"] == 1.0
    assert (
        report["overall"]["record_rates"]["hard_guarded_oracle_beats_top1"]
        == 1.0
    )


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
    assert report["coverage_gaps"]["missing_required_buckets"] == [
        "normal",
        "sharp_turn",
        "npc_interaction",
        "dense_scene",
        "lane_change_or_merge",
    ]


def test_safety_cost_oracle_matches_matrix_route_alias(tmp_path) -> None:
    log_path = _write_log(
        tmp_path,
        _record(),
        route_dir="sample_tl_turn",
        route_path="/routes/sample_map_tl_route_59_to_86.pkl",
    )
    manifest_path = tmp_path / "scenario_buckets.json"
    manifest_path.write_text(
        json.dumps(
            {
                "routes": {"sample_tl_turn": ["sharp_turn"]},
                "run_keys": {},
                "filters": [
                    {
                        "name": "tl_alias_on",
                        "match": {
                            "route_name": "sample_tl_turn",
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

    assert sorted(buckets) == [
        "overall",
        "red_light_turn",
        "sharp_turn",
        "traffic_light",
    ]
    assert report["records"]["scenario_bucket_counts"]["sharp_turn"] == 1
    assert report["records"]["scenario_bucket_counts"]["traffic_light"] == 1


def test_safety_cost_oracle_requires_candidate_outcomes(tmp_path) -> None:
    record = _record()
    record["candidate_closed_loop_outcomes"] = None

    with pytest.raises(ValueError, match="candidate outcomes"):
        analyze([_write_log(tmp_path, record)])


def test_safety_cost_oracle_cli_fails_on_missing_required_bucket(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = _write_log(tmp_path, _record())
    output_json = tmp_path / "oracle.json"
    output_md = tmp_path / "oracle.md"

    monkeypatch.setattr(
        "sys.argv",
        [
            "analyze_diffusion_planner_safety_cost_oracle.py",
            "--selection_log",
            str(log_path),
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--fail_on_missing_required",
        ],
    )

    with pytest.raises(SystemExit, match="Missing required scenario bucket"):
        main()
    assert output_json.is_file()
    assert output_md.is_file()
