from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_first_step_graft_potential import (
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


def _prefix(first_x: float, slope: float) -> list[list[float]]:
    return [[first_x + slope * idx, 0.0, 0.0] for idx in range(10)]


def _record() -> dict:
    return {
        "num_candidates": 4,
        "selected_index": 0,
        "feasible_mask": [True, True, True, True],
        "candidate_closed_loop_outcomes": [
            _outcome(0, progress=10.0, jerk=5.0, lateral=2.0),
            _outcome(1, progress=9.8, jerk=4.0, lateral=1.0),
            _outcome(2, progress=9.95, jerk=4.5, lateral=1.5),
            _outcome(3, progress=10.0, jerk=3.0, lateral=1.0, red=True),
        ],
        "candidate_perfect_tracker_postprocessed_reference_prefix": [
            _prefix(1.0, 1.0),
            _prefix(0.5, 0.4),
            _prefix(0.8, 0.9),
            _prefix(1.0, 1.0),
        ],
    }


def _write_log(tmp_path, records: list[dict]):
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_first_step_graft_preserves_selected_first_step(tmp_path) -> None:
    report = analyze([_write_log(tmp_path, [_record()])], label="unit")

    assert report["records"]["with_oracle_donor"] == 1
    assert report["summary"]["outcome_progress_deficit_m"]["mean"] == pytest.approx(0.05)
    assert report["summary"]["first_step_reach_delta_m"]["mean"] == pytest.approx(0.0)
    assert report["summary"]["donor_first_step_reach_delta_m"]["mean"] == pytest.approx(-0.2)
    assert report["rates"]["first_step_exact_preservation_rate"] == 1.0
    assert report["rates"]["donor_lower_first_step_rate"] == 1.0


def test_first_step_graft_ignores_safety_regressing_donor(tmp_path) -> None:
    record = _record()
    record["candidate_closed_loop_outcomes"][2]["red_light_violation"] = True

    report = analyze([_write_log(tmp_path, [record])], label="unit")

    assert report["records"]["with_oracle_donor"] == 1
    assert report["summary"]["outcome_progress_deficit_m"]["mean"] == pytest.approx(0.2)
    assert report["summary"]["donor_first_step_reach_delta_m"]["mean"] == pytest.approx(-0.5)
