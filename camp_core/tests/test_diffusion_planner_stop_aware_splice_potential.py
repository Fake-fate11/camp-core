from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_stop_aware_splice_potential import (
    SpliceConfig,
    analyze,
    render_markdown,
)


def _prefix(end_x: float, end_y: float, *, steps: int = 12) -> list[list[float]]:
    rows = []
    for step in range(steps):
        ratio = float(step + 1) / float(steps)
        rows.append([end_x * ratio, end_y * ratio, 0.0, 1.0])
    return rows


def _record() -> dict:
    return {
        "num_candidates": 3,
        "selected_index": 0,
        "feasible_mask": [True, True, False],
        "candidate_raw_trajectory_prefix": [
            _prefix(12.0, 0.0),
            _prefix(10.0, -4.0),
            _prefix(8.0, -6.0),
        ],
        "candidate_planned_red_light_cost": [0.0, 0.0, 0.0],
        "candidate_full_horizon_planned_red_light_cost": [10.0, 5.0, 0.0],
        "candidate_horizon_union_planned_red_light_cost": [10.0, 5.0, 0.0],
    }


def test_stop_aware_splice_reports_lower_red_donor_potential(tmp_path) -> None:
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps([_record()]), encoding="utf-8")

    report = analyze(
        [path],
        config=SpliceConfig(
            anchor_steps=4,
            blend_steps=2,
            material_endpoint_threshold_m=0.5,
        ),
    )

    assert report["records"]["selected_h30_safe_full_red"] == 1
    any_pool = report["donor_pools"]["lower_red_any"]
    feasible_pool = report["donor_pools"]["lower_red_base_feasible"]
    assert any_pool["with_donor"]["count"] == 1
    assert any_pool["candidate_count"]["mean"] == 2.0
    assert feasible_pool["with_donor"]["count"] == 1
    assert feasible_pool["candidate_count"]["mean"] == 1.0
    assert feasible_pool["with_material_splice"]["count"] == 1
    assert (
        feasible_pool["best_splice"]["h10_max_deviation_m"]["max"]
        == pytest.approx(0.0)
    )
    assert not report["analysis"]["uses_outcome_labels"]
    assert not report["analysis"]["red_or_feasibility_recomputed_for_splice"]

    markdown = render_markdown(report)
    assert "Stop-Aware Splice Potential Audit" in markdown
    assert "lower_red_base_feasible" in markdown


def test_stop_aware_splice_rejects_short_raw_prefix(tmp_path) -> None:
    record = _record()
    record["candidate_raw_trajectory_prefix"] = [
        _prefix(1.0, 0.0, steps=3),
        _prefix(1.0, 1.0, steps=3),
        _prefix(1.0, -1.0, steps=3),
    ]
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps([record]), encoding="utf-8")

    with pytest.raises(ValueError, match="raw prefix length must exceed"):
        analyze([path], config=SpliceConfig(anchor_steps=3))
