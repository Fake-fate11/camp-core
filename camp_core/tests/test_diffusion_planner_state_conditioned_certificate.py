from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_state_conditioned_certificate import (
    analyze,
)


def _outcome(
    index: int,
    *,
    progress: float,
    jerk: float,
    lateral: float,
    value: float = 0.0,
    red: bool = False,
) -> dict:
    return {
        "candidate_index": index,
        "progress_m": progress,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": red,
        "feasible": not red,
        "value": value,
    }


def _record() -> dict:
    return {
        "num_candidates": 3,
        "selected_index": 0,
        "selection_step": 72,
        "feasible_mask": [True, True, True],
        "candidate_closed_loop_outcomes": [
            _outcome(0, progress=10.0, jerk=5.0, lateral=2.0),
            _outcome(1, progress=9.95, jerk=3.0, lateral=1.0),
            _outcome(2, progress=9.90, jerk=4.0, lateral=0.8),
        ],
        "selection_scores": [0.0, 2.0, 1.0],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0, 0.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.0, 0.0],
        "candidate_perfect_tracker_first_step_reach_m": [1.00, 0.93, 0.94],
        "candidate_perfect_tracker_target_speed_mps": [5.00, 4.93, 4.94],
        "candidate_perfect_tracker_open_loop_rollout": {
            "3": {"distance_m": [3.00, 2.93, 2.94]},
            "10": {"distance_m": [10.00, 9.93, 9.94]},
        },
        "dp_candidate_rewards": [
            {"progress": 10.00},
            {"progress": 9.93},
            {"progress": 9.94},
        ],
        "candidate_route_progress": None,
        "candidate_horizon_lateral_acceleration_cost": [2.0, 1.0, 0.8],
        "candidate_dp_prior_jerk_excess_cost": [1.0, 0.5, 0.2],
    }


def _traffic_light_hybrid_record(*, raw_jerk_delta: float = -0.1) -> dict:
    record = _record()
    record["candidate_closed_loop_outcomes"] = [
        _outcome(0, progress=10.0, jerk=5.0, lateral=2.0),
        _outcome(1, progress=9.98, jerk=3.0, lateral=1.0),
        _outcome(2, progress=9.90, jerk=4.0, lateral=0.8),
    ]
    record["candidate_perfect_tracker_first_step_reach_m"] = [1.00, 0.92, 0.94]
    record["candidate_perfect_tracker_target_speed_mps"] = [5.00, 4.96, 4.94]
    record["candidate_perfect_tracker_open_loop_rollout"] = {
        "3": {"distance_m": [3.00, 2.92, 2.94]},
        "10": {"distance_m": [10.00, 9.96, 9.94]},
    }
    record["dp_candidate_rewards"] = [
        {"progress": 10.00},
        {"progress": 9.96},
        {"progress": 9.94},
    ]
    record["candidate_horizon_lateral_acceleration_cost"] = [2.0, 1.0, 0.8]
    record["candidate_dp_prior_jerk_excess_cost"] = [
        1.0,
        1.0 + raw_jerk_delta,
        0.2,
    ]
    record["selection_scores"] = [0.0, 1.0, 2.0]
    return record


def _manifest() -> dict:
    return {
        "routes": {},
        "filters": [
            {
                "name": "critical_tl",
                "match": {"traffic_lights": True},
                "buckets": ["traffic_light", "red_light_turn"],
            }
        ],
        "default_buckets": [],
    }


def _write_log(tmp_path, records: list[dict], *, traffic_lights: bool):
    tl_dir = "tl_on" if traffic_lights else "tl_off"
    path = (
        tmp_path
        / "root"
        / "route_a"
        / "seed_1"
        / "npc_0"
        / "spawn_0p3"
        / tl_dir
        / "static"
        / "camp_selection_log.json"
    )
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(records), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    return path, manifest_path


def _screen(report: dict, name: str) -> dict:
    for screen in report["screens"]:
        if screen["name"] == name:
            return screen
    raise AssertionError(f"missing screen {name}")


def test_balanced_screen_uses_default_budget_for_noncritical_log(tmp_path) -> None:
    log_path, manifest_path = _write_log(tmp_path, [_record()], traffic_lights=False)

    report = analyze([log_path], scenario_bucket_manifest=manifest_path, label="unit")
    screen = _screen(report, "state_guard_balanced_010")

    assert screen["overall"]["changed"] == 1
    assert screen["overall"]["posterior_joint_comfort_improvements"] == 1
    assert screen["changed_delta_summary"]["first_step_loss_m"]["mean"] == pytest.approx(
        0.06
    )


def test_balanced_screen_applies_critical_bucket_budget(tmp_path) -> None:
    log_path, manifest_path = _write_log(tmp_path, [_record()], traffic_lights=True)

    report = analyze([log_path], scenario_bucket_manifest=manifest_path, label="unit")
    screen = _screen(report, "state_guard_balanced_010")

    assert screen["overall"]["changed"] == 0
    traffic_bucket = {
        row["group"]: row for row in screen["by_bucket"]
    }["traffic_light"]
    assert traffic_bucket["records"] == 1
    assert traffic_bucket["changed"] == 0


def test_reward_h10_screen_uses_long_horizon_progress_budget(tmp_path) -> None:
    log_path, manifest_path = _write_log(tmp_path, [_record()], traffic_lights=False)

    report = analyze([log_path], scenario_bucket_manifest=manifest_path, label="unit")
    screen = _screen(report, "reward_h10_guard_balanced_010")

    assert screen["overall"]["changed"] == 1
    assert screen["overall"]["posterior_joint_comfort_improvements"] == 1
    assert screen["changed_delta_summary"]["dp_reward_progress_loss_m"][
        "mean"
    ] == pytest.approx(0.06)
    assert screen["changed_delta_summary"]["h10_distance_loss_m"]["mean"] == pytest.approx(
        0.06
    )


def test_reward_h10_screen_applies_critical_bucket_budget(tmp_path) -> None:
    log_path, manifest_path = _write_log(tmp_path, [_record()], traffic_lights=True)

    report = analyze([log_path], scenario_bucket_manifest=manifest_path, label="unit")
    screen = _screen(report, "reward_h10_guard_balanced_010")

    assert screen["overall"]["changed"] == 0


def test_traffic_light_hybrid_screen_is_bucket_gated(tmp_path) -> None:
    record = _traffic_light_hybrid_record()
    log_path, manifest_path = _write_log(tmp_path, [record], traffic_lights=False)

    report = analyze([log_path], scenario_bucket_manifest=manifest_path, label="unit")

    assert _screen(report, "traffic_light_hybrid_step_h10_guard_005")["overall"][
        "changed"
    ] == 0
    assert _screen(report, "traffic_light_hybrid_h3_h10_guard_005")["overall"][
        "changed"
    ] == 0

    log_path, manifest_path = _write_log(tmp_path / "tl", [record], traffic_lights=True)
    report = analyze([log_path], scenario_bucket_manifest=manifest_path, label="unit")

    step = _screen(report, "traffic_light_hybrid_step_h10_guard_005")
    h3 = _screen(report, "traffic_light_hybrid_h3_h10_guard_005")
    assert step["overall"]["changed"] == 1
    assert h3["overall"]["changed"] == 1
    assert step["overall"]["posterior_joint_comfort_improvements"] == 1
    assert h3["overall"]["posterior_joint_comfort_improvements"] == 1


def test_traffic_light_hybrid_screen_requires_strict_raw_jerk(tmp_path) -> None:
    record = _traffic_light_hybrid_record(raw_jerk_delta=0.0)
    log_path, manifest_path = _write_log(tmp_path, [record], traffic_lights=True)

    report = analyze([log_path], scenario_bucket_manifest=manifest_path, label="unit")

    assert _screen(report, "traffic_light_hybrid_step_h10_guard_005")["overall"][
        "changed"
    ] == 0
    assert _screen(report, "traffic_light_hybrid_h3_h10_guard_005")["overall"][
        "changed"
    ] == 0


def test_screen_reports_posterior_safety_regression(tmp_path) -> None:
    record = _record()
    record["candidate_closed_loop_outcomes"][2]["red_light_violation"] = True
    log_path, manifest_path = _write_log(tmp_path, [record], traffic_lights=False)

    report = analyze([log_path], scenario_bucket_manifest=manifest_path, label="unit")
    screen = _screen(report, "state_guard_balanced_010")

    assert screen["overall"]["changed"] == 1
    assert screen["overall"]["outcome_safety_regressions"] == 1
    assert screen["overall"]["outcome_safety_regression_fields"] == {
        "red_light_violation": 1
    }
    assert screen["safety_regression_examples"][0]["outcome_safety_regression_fields"] == [
        "red_light_violation"
    ]
    assert screen["safety_regression_examples"][0]["deltas"]["first_step_loss_m"] == pytest.approx(
        0.06
    )
