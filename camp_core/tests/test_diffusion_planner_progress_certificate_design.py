from __future__ import annotations

import json

from scripts.integrations.analyze_diffusion_planner_progress_certificate_design import (
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


def _record(*, route_progress=True) -> dict:
    return {
        "num_candidates": 3,
        "selected_index": 0,
        "feasible_mask": [True, True, True],
        "atom_names": ["progress_shortfall"],
        "atoms": [[0.0], [1.0], [0.0]],
        "candidate_horizon_lateral_acceleration_cost": [2.0, 1.0, 2.5],
        "candidate_dp_prior_jerk_excess_cost": [4.0, 3.0, 5.0],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0, 0.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.0, 0.0],
        "candidate_route_progress": [10.0, 10.0, 9.0] if route_progress else None,
        "candidate_step_reach": [1.0, 0.5, 0.9],
        "candidate_perfect_tracker_first_step_reach_m": [1.0, 0.5, 0.9],
        "candidate_perfect_tracker_target_speed_mps": [5.0, 4.5, 4.9],
        "candidate_perfect_tracker_open_loop_rollout": {
            "3": {"distance_m": [3.0, 2.0, 2.5]},
            "5": {"distance_m": [5.0, 4.0, 4.5]},
            "10": {"distance_m": [10.0, 10.0, 9.0]},
        },
        "candidate_closed_loop_outcomes": [
            _outcome(0, progress=10.0, jerk=4.0, lateral=2.0),
            _outcome(1, progress=10.0, jerk=3.0, lateral=1.0),
            _outcome(2, progress=9.0, jerk=3.0, lateral=1.0),
        ],
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


def _descriptor(report: dict, name: str) -> dict:
    descriptors = report["budgets"][0]["descriptors"]
    for row in descriptors:
        if row["descriptor"] == name:
            return row
    raise AssertionError(name)


def _bucket_descriptor(report: dict, bucket_name: str, descriptor_name: str) -> dict:
    for bucket in report["budgets"][0]["by_bucket"]:
        if bucket["bucket"] != bucket_name:
            continue
        for row in bucket["descriptors"]:
            if row["descriptor"] == descriptor_name:
                return row
    raise AssertionError(f"{bucket_name}:{descriptor_name}")


def test_route_progress_certificate_exposes_hidden_outcome_candidate(tmp_path) -> None:
    report = analyze([_write_log(tmp_path, _record())], progress_budgets_m=(0.1,))

    progress_shortfall = _descriptor(report, "progress_shortfall_atom")
    route_progress = _descriptor(report, "route_progress")
    h10 = _descriptor(report, "rollout_h10_distance")

    assert report["budgets"][0]["outcome_joint_records"] == 1
    assert report["budgets"][0]["current_proxy_joint_records"] == 0
    assert progress_shortfall["certificate_hidden_joint_records"] == 0
    assert route_progress["certificate_hidden_joint_records"] == 1
    assert route_progress["certificate_proxy_comfort_hidden_joint_records"] == 1
    assert h10["certificate_hidden_joint_records"] == 1
    assert route_progress["covered_hidden_loss_summary"]["mean"] == 0.0


def test_certificate_design_reports_explicit_bucket_capture(tmp_path) -> None:
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

    report = analyze(
        [log_path],
        scenario_bucket_manifest=manifest_path,
        progress_budgets_m=(0.1,),
    )
    traffic_route_progress = _bucket_descriptor(
        report,
        "traffic_light",
        "route_progress",
    )

    assert report["analysis"]["explicit_bucket_labels_only"] is True
    assert sorted(bucket["bucket"] for bucket in report["budgets"][0]["by_bucket"]) == [
        "overall",
        "red_light_turn",
        "traffic_light",
    ]
    assert report["records"]["scenario_bucket_counts"]["traffic_light"]["records"] == 1
    assert traffic_route_progress["certificate_hidden_joint_records"] == 1
    assert (
        traffic_route_progress["certificate_proxy_comfort_hidden_joint_records"] == 1
    )


def test_missing_route_progress_is_reported_unavailable(tmp_path) -> None:
    report = analyze(
        [_write_log(tmp_path, _record(route_progress=False))],
        progress_budgets_m=(0.1,),
    )

    route_progress = _descriptor(report, "route_progress")
    step_reach = _descriptor(report, "step_reach")

    assert route_progress["available_records"] == 0
    assert route_progress["certificate_hidden_joint_records"] == 0
    assert step_reach["available_records"] == 1
    assert step_reach["certificate_hidden_joint_records"] == 0
