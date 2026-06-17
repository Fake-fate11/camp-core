from __future__ import annotations

import json

from scripts.integrations.analyze_diffusion_planner_hidden_outcome_gap import (
    analyze,
)


def _outcome(
    index: int,
    *,
    progress: float,
    jerk: float,
    lateral: float,
) -> dict:
    return {
        "candidate_index": index,
        "progress_m": progress,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
        "feasible": True,
    }


def _record(*, proxy_visible: bool = False) -> dict:
    proxy_jerk = [4.0, 3.0 if proxy_visible else 5.0]
    proxy_lateral = [2.0, 1.0 if proxy_visible else 3.0]
    return {
        "num_candidates": 2,
        "selected_index": 0,
        "selection_step": 63,
        "feasible_mask": [True, True],
        "atom_names": ["progress_shortfall"],
        "atoms": [[0.0], [0.0]],
        "candidate_horizon_lateral_acceleration_cost": proxy_lateral,
        "candidate_dp_prior_jerk_excess_cost": proxy_jerk,
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.0],
        "candidate_closed_loop_outcomes": [
            _outcome(0, progress=10.0, jerk=4.0, lateral=2.0),
            _outcome(1, progress=10.0, jerk=3.0, lateral=1.0),
        ],
    }


def _write_run(tmp_path, record: dict):
    run_dir = (
        tmp_path
        / "sample_map_tl_route_59_to_86"
        / "seed_1"
        / "npc_4"
        / "spawn_0p3"
        / "tl_on"
        / "static"
    )
    run_dir.mkdir(parents=True)
    log_path = run_dir / "camp_selection_log.json"
    log_path.write_text(json.dumps([record]), encoding="utf-8")
    (run_dir / "camp_validation_summary.json").write_text(
        json.dumps(
            {
                "benchmark": {
                    "route": "/tmp/sample_map_tl_route_59_to_86.pkl",
                    "seed": 1,
                    "steps": 200,
                    "max_npcs": 4,
                    "spawn_probability": 0.3,
                    "traffic_lights": True,
                    "advance_mode": "perfect",
                },
                "advance_mode": "perfect",
            }
        ),
        encoding="utf-8",
    )
    return log_path


def _write_manifest(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "routes": {
                    "sample_map_tl_route_59_to_86": ["sharp_turn"],
                },
                "filters": [
                    {
                        "name": "red_light_turn",
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
    return manifest


def test_hidden_outcome_gap_is_attributed_by_bucket_and_tick(tmp_path) -> None:
    log_path = _write_run(tmp_path, _record(proxy_visible=False))
    manifest = _write_manifest(tmp_path)

    report = analyze(
        [log_path],
        scenario_bucket_manifest=manifest,
        progress_budgets_m=(0.0,),
        tick_bin_size=50,
    )

    budget = report["budgets"][0]
    assert report["records"]["nonfallback"] == 1
    assert budget["overall"]["outcome_joint_records"] == 1
    assert budget["overall"]["proxy_joint_records"] == 0
    assert budget["overall"]["hidden_joint_records"] == 1
    assert budget["hidden_proxy_blockers"]["proxy_comfort_nonworse_blocked"] == 1
    assert budget["hidden_proxy_blockers"]["proxy_joint_comfort_not_strict"] == 1
    assert budget["by_bucket"][0]["group"] in {
        "overall",
        "red_light_turn",
        "sharp_turn",
        "traffic_light",
    }
    bucket_rows = {row["group"]: row for row in budget["by_bucket"]}
    assert bucket_rows["red_light_turn"]["hidden_joint_records"] == 1
    assert budget["by_tick_bin"][0]["group"] == "0050-0099"
    assert budget["top_hidden_examples"][0]["selection_step"] == 63
    assert "closed-loop candidate outcomes are labels" in report["analysis"][
        "math_boundary"
    ].lower()


def test_proxy_visible_outcome_candidate_is_not_hidden(tmp_path) -> None:
    log_path = _write_run(tmp_path, _record(proxy_visible=True))

    report = analyze([log_path], progress_budgets_m=(0.0,))

    budget = report["budgets"][0]
    assert budget["overall"]["outcome_joint_records"] == 1
    assert budget["overall"]["proxy_joint_records"] == 1
    assert budget["overall"]["hidden_joint_records"] == 0
    assert budget["hidden_proxy_blockers"] == {}
