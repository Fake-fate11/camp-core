from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_bounded_tradeoff import analyze


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
        "feasible": not red,
    }


def _prefix(h10: float) -> list[list[float]]:
    return [[1.0 + (h10 - 1.0) * idx / 9.0, 0.0, 0.0] for idx in range(10)]


def _record() -> dict:
    return {
        "num_candidates": 4,
        "selected_index": 0,
        "feasible_mask": [True, True, True, True],
        "candidate_closed_loop_outcomes": [
            _outcome(0, progress=10.0, jerk=5.0, lateral=2.0),
            _outcome(1, progress=9.8, jerk=3.0, lateral=1.0),
            _outcome(2, progress=9.95, jerk=2.0, lateral=0.5, red=True),
            _outcome(3, progress=9.0, jerk=4.0, lateral=1.5),
        ],
        "candidate_perfect_tracker_postprocessed_reference_prefix": [
            _prefix(10.0),
            _prefix(9.95),
            _prefix(10.0),
            _prefix(9.0),
        ],
        "candidate_perfect_tracker_target_speed_mps": [5.0, 4.95, 5.0, 4.0],
        "candidate_horizon_lateral_acceleration_cost": [2.0, 1.0, 0.5, 1.5],
        "candidate_dp_prior_jerk_excess_cost": [4.0, 2.0, 1.0, 3.0],
    }


def _write_log(tmp_path, records: list[dict]):
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def _find_grid(report: dict, progress: float, target: float, h10: float) -> dict:
    for row in report["budget_grid"]:
        if (
            row["progress_budget_m"] == pytest.approx(progress)
            and row["target_speed_loss_budget_mps"] == pytest.approx(target)
            and row["h10_displacement_loss_budget_m"] == pytest.approx(h10)
        ):
            return row
    raise AssertionError("budget row not found")


def test_bounded_tradeoff_requires_all_budgets(tmp_path) -> None:
    report = analyze([_write_log(tmp_path, [_record()])], label="unit")

    assert report["records"]["with_oracle_donor"] == 1
    assert report["oracle_donor_summary"]["progress_loss_m"]["mean"] == pytest.approx(0.2)
    blocked = _find_grid(report, progress=0.1, target=0.1, h10=0.1)
    assert blocked["available_records"] == 0
    available = _find_grid(report, progress=0.25, target=0.1, h10=0.1)
    assert available["available_records"] == 1
    assert available["chosen_summary"]["outcome_jerk_delta_mps3"]["mean"] == pytest.approx(-2.0)


def test_bounded_tradeoff_ignores_safety_regressing_donor(tmp_path) -> None:
    record = _record()
    record["candidate_closed_loop_outcomes"][1]["red_light_violation"] = True
    record["candidate_closed_loop_outcomes"][1]["feasible"] = False

    report = analyze([_write_log(tmp_path, [record])], label="unit")

    assert report["records"]["with_oracle_donor"] == 1
    assert report["oracle_donor_summary"]["progress_loss_m"]["mean"] == pytest.approx(1.0)
