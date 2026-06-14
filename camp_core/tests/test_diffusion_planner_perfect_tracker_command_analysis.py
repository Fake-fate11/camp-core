from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_perfect_tracker_commands import (
    compute_perfect_tracker_command_report,
)


def test_command_shadow_analysis_finds_joint_strict_opportunity(tmp_path) -> None:
    log_path = _write_log(tmp_path, [_record()])

    report = compute_perfect_tracker_command_report([log_path])

    assert report["records"] == {
        "logs": 1,
        "total": 1,
        "nonfallback": 1,
        "fallback": 0,
    }
    assert report["opportunities"]["dominance_records"] == 1
    assert report["opportunities"]["joint_strict_records"] == 1
    assert report["counterfactual_postselection"]["changed_records"] == 1
    assert report["counterfactual_postselection"][
        "mean_deltas_on_changed_records"
    ]["progress"] == 0.0
    assert report["selection_behavior"][
        "selected_target_below_candidate0_rate"
    ] == 0.0
    assert report["latency_ms"]["p95"] == pytest.approx(0.25)


def test_command_shadow_analysis_excludes_fallback_from_opportunities(
    tmp_path,
) -> None:
    record = _record()
    record["feasible_mask"] = [False, False, False]
    log_path = _write_log(tmp_path, [record])

    report = compute_perfect_tracker_command_report([log_path])

    assert report["records"]["fallback"] == 1
    assert report["records"]["nonfallback"] == 0
    assert report["opportunities"]["joint_strict_records"] == 0


def test_command_shadow_analysis_rejects_outcome_labels(tmp_path) -> None:
    record = _record()
    record["candidate_closed_loop_outcomes"] = [{}, {}, {}]
    log_path = _write_log(tmp_path, [record])

    with pytest.raises(ValueError, match="outcome-free"):
        compute_perfect_tracker_command_report([log_path])


def test_command_shadow_analysis_rejects_uncertified_summary(tmp_path) -> None:
    log_path = _write_log(tmp_path, [_record()])
    summary_path = log_path.with_name("camp_validation_summary.json")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["camp_shadow_perfect_tracker_command"]["selection_effect"] = True
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    with pytest.raises(ValueError, match="does not certify"):
        compute_perfect_tracker_command_report([log_path])


def _write_log(tmp_path, records):
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(json.dumps(records), encoding="utf-8")
    log_path.with_name("camp_validation_summary.json").write_text(
        json.dumps(
            {
                "advance_mode": "perfect",
                "camp_shadow_perfect_tracker_command": {
                    "enabled": True,
                    "selection_effect": False,
                    "tracker_class": (
                        "scenario_generation.mpc_tracker.PerfectTracker"
                    ),
                },
            }
        ),
        encoding="utf-8",
    )
    return log_path


def _record() -> dict:
    return {
        "selected_index": 0,
        "used_fallback": False,
        "feasible_mask": [True, True, True],
        "candidate_closed_loop_outcomes": None,
        "selection_scores": [0.0, 1.0, float("inf")],
        "dp_candidate_rewards": [
            {"progress": 5.0, "red_light": 0.0},
            {"progress": 5.0, "red_light": 0.0},
            {"progress": 5.0, "red_light": 0.0},
        ],
        "candidate_perfect_tracker_target_speed_mps": [4.0, 4.0, 3.0],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [10.0, 8.0, 5.0],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [
            0.5,
            0.4,
            0.2,
        ],
        "candidate_perfect_tracker_yaw_rate_magnitude_rps": [0.1, 0.08, 0.05],
        "candidate_perfect_tracker_restart_push": [False, False, False],
        "candidate_dp_prior_jerk_excess_cost": [0.0, 1.0, 2.0],
        "candidate_horizon_lateral_acceleration_cost": [0.5, 0.4, 0.3],
        "latency_ms_shadow_perfect_tracker_command": 0.25,
    }
