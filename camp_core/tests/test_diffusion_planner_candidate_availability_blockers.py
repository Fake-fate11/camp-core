from __future__ import annotations

import json

from scripts.integrations.analyze_diffusion_planner_candidate_availability_blockers import (
    analyze,
)


def _outcome(
    index: int,
    *,
    progress: float,
    jerk: float,
    lateral: float,
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
        "feasible": True,
    }


def _record(outcomes: list[dict]) -> dict:
    return {
        "num_candidates": len(outcomes),
        "selected_index": 0,
        "feasible_mask": [True] * len(outcomes),
        "candidate_closed_loop_outcomes": outcomes,
    }


def _write_log(tmp_path, records: list[dict]):
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_blocker_audit_marks_progress_blocked_joint_candidate(tmp_path) -> None:
    record = _record(
        [
            _outcome(0, progress=10.0, jerk=5.0, lateral=2.0),
            _outcome(1, progress=9.97, jerk=4.0, lateral=1.0),
        ]
    )

    report = analyze([_write_log(tmp_path, [record])], progress_budgets_m=(0.0, 0.05))

    zero = report["budgets"][0]
    wide = report["budgets"][1]
    assert zero["outcome_joint_records"] == 0
    assert zero["blockers_among_failed"]["joint_comfort_progress_blocked"][
        "records"
    ] == 1
    assert wide["outcome_joint_records"] == 1
    assert report["safety_joint_progress_deficit_m"]["within_budget"]["0.05"][
        "records"
    ] == 1


def test_blocker_audit_marks_safety_blocked_joint_candidate(tmp_path) -> None:
    record = _record(
        [
            _outcome(0, progress=10.0, jerk=5.0, lateral=2.0, red=False),
            _outcome(1, progress=10.0, jerk=4.0, lateral=1.0, red=True),
        ]
    )

    report = analyze([_write_log(tmp_path, [record])], progress_budgets_m=(0.0,))

    zero = report["budgets"][0]
    assert zero["outcome_joint_records"] == 0
    assert zero["blockers_among_failed"]["joint_comfort_safety_blocked"][
        "records"
    ] == 1
    assert report["funnel"]["joint_comfort_records"]["records"] == 1
    assert report["funnel"]["safety_joint_comfort_records"]["records"] == 0


def test_blocker_audit_marks_missing_joint_comfort_after_constraints(tmp_path) -> None:
    record = _record(
        [
            _outcome(0, progress=10.0, jerk=5.0, lateral=2.0),
            _outcome(1, progress=10.0, jerk=4.0, lateral=2.5),
            _outcome(2, progress=10.0, jerk=5.5, lateral=1.0),
        ]
    )

    report = analyze([_write_log(tmp_path, [record])], progress_budgets_m=(0.0,))

    zero = report["budgets"][0]
    assert zero["outcome_joint_records"] == 0
    assert zero["blockers_among_failed"]["no_joint_comfort_alternative"][
        "records"
    ] == 1
    assert zero["blockers_among_failed"][
        "progress_safety_available_but_no_joint_comfort"
    ]["records"] == 1
