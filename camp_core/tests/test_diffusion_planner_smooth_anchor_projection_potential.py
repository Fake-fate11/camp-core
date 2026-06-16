from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_smooth_anchor_projection_potential import (
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


def _prefix(*, wiggle: float = 0.0) -> list[list[float]]:
    points = []
    for idx in range(10):
        y = 0.0 if idx in (0, 2, 4, 9) else wiggle * ((-1.0) ** idx)
        points.append([1.0 + idx, y, 0.0])
    return points


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
            _prefix(wiggle=0.3),
            _prefix(wiggle=0.1),
            _prefix(wiggle=0.0),
            _prefix(wiggle=0.0),
        ],
    }


def _write_log(tmp_path, records: list[dict]):
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_smooth_anchor_projection_preserves_anchors_and_improves_proxy(tmp_path) -> None:
    report = analyze(
        [_write_log(tmp_path, [_record()])],
        label="unit",
        ridge_values=(0.0,),
    )
    ridge_report = report["ridge_reports"][0]

    assert report["records"]["with_oracle_donor"] == 1
    assert ridge_report["rates"]["anchor_exact_preservation_rate"] == 1.0
    assert ridge_report["rates"]["projection_h3_displacement_nonloss_rate"] == 1.0
    assert ridge_report["rates"]["projection_h5_displacement_nonloss_rate"] == 1.0
    assert ridge_report["rates"]["projection_h10_displacement_nonloss_rate"] == 1.0
    assert ridge_report["summary"]["max_anchor_xy_error_m"]["mean"] == pytest.approx(0.0)
    assert ridge_report["summary"]["prefix_jerk_proxy_delta"]["mean"] < 0.0


def test_smooth_anchor_projection_ignores_safety_regressing_donor(tmp_path) -> None:
    record = _record()
    record["candidate_closed_loop_outcomes"][2]["red_light_violation"] = True

    report = analyze(
        [_write_log(tmp_path, [record])],
        label="unit",
        ridge_values=(0.0,),
    )
    ridge_report = report["ridge_reports"][0]

    assert report["records"]["with_oracle_donor"] == 1
    assert ridge_report["summary"]["outcome_progress_deficit_m"]["mean"] == pytest.approx(0.2)


def test_smooth_anchor_projection_rejects_negative_ridge(tmp_path) -> None:
    with pytest.raises(ValueError, match="Ridge values"):
        analyze([_write_log(tmp_path, [_record()])], ridge_values=(-1.0,))
