from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_camp_candidate_pool import (
    compute_candidate_pool_opportunity_report,
)


def test_candidate_pool_audit_finds_expanded_only_pareto_opportunity(
    tmp_path,
) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    record = _record()
    log_path.write_text(json.dumps([record]), encoding="utf-8")

    report = compute_candidate_pool_opportunity_report(
        [log_path],
        reference_candidate_count=8,
    )

    assert report["records"] == {
        "logs": 1,
        "total": 1,
        "feasible": 1,
        "fallback": 0,
    }
    assert report["selection"]["selected_extra_rate"] == 0.0
    opportunities = report["opportunities"]
    assert opportunities["weak_records"] == 1
    assert opportunities["joint_strict_records"] == 1
    assert opportunities["extra_weak_records"] == 1
    assert opportunities["extra_only_weak_records"] == 1
    assert opportunities["extra_joint_strict_records"] == 1


def test_candidate_pool_audit_rejects_closed_loop_outcomes(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    record = _record()
    record["candidate_closed_loop_outcomes"] = [{}] * 9
    log_path.write_text(json.dumps([record]), encoding="utf-8")

    with pytest.raises(ValueError, match="outcome-free"):
        compute_candidate_pool_opportunity_report(
            [log_path],
            reference_candidate_count=8,
        )


def test_candidate_pool_audit_rejects_missing_step_reach(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    record = _record()
    record["candidate_step_reach"] = None
    log_path.write_text(json.dumps([record]), encoding="utf-8")

    with pytest.raises(ValueError, match="candidate_step_reach"):
        compute_candidate_pool_opportunity_report(
            [log_path],
            reference_candidate_count=8,
        )


def test_candidate_pool_audit_accepts_reference_sized_pool(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    record = _record()
    for key, value in tuple(record.items()):
        if isinstance(value, list) and len(value) == 9:
            record[key] = value[:8]
    log_path.write_text(json.dumps([record]), encoding="utf-8")

    report = compute_candidate_pool_opportunity_report(
        [log_path],
        reference_candidate_count=8,
    )

    assert report["records"]["feasible"] == 1
    assert report["selection"]["selected_extra_records"] == 0
    assert report["opportunities"]["extra_weak_records"] == 0


def _record() -> dict:
    candidate_count = 9
    rewards = [
        {"progress": 5.0, "red_light": 0.0}
        for _ in range(candidate_count)
    ]
    jerk = [1.0] + [1.5] * 7 + [0.5]
    lateral = [1.0] + [1.5] * 7 + [0.5]
    return {
        "selected_index": 0,
        "feasible_mask": [True] * candidate_count,
        "candidate_closed_loop_outcomes": None,
        "candidate_step_reach": [0.5] * candidate_count,
        "dp_candidate_rewards": rewards,
        "candidate_dp_prior_jerk_excess_cost": jerk,
        "candidate_horizon_lateral_acceleration_cost": lateral,
    }
