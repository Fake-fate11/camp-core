from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_raw_prefix_horizon_materiality import (
    analyze,
    render_markdown,
)


def _prefix(end_x: float, end_y: float) -> list[list[float]]:
    rows = []
    for step in range(4):
        ratio = float(step + 1) / 4.0
        rows.append([end_x * ratio, end_y * ratio, 1.0, 0.0])
    return rows


def _record(*, selected_union_red: float = 0.0) -> dict:
    return {
        "num_candidates": 3,
        "selected_index": 1,
        "used_fallback": False,
        "feasible_mask": [True, True, True],
        "atom_names": ["progress_shortfall", "planned_lateral_acceleration_cost"],
        "atoms": [[0.0, 0.0], [2.0, 0.5], [0.0, 0.0]],
        "candidate_horizon_union_planned_red_light_cost": [
            0.0,
            selected_union_red,
            0.0,
        ],
        "candidate_full_horizon_planned_red_light_cost": [
            0.0,
            selected_union_red,
            0.0,
        ],
        "candidate_raw_trajectory_prefix": [
            _prefix(4.0, 0.0),
            _prefix(4.0, 1.0),
            _prefix(4.0, -1.0),
        ],
    }


def test_raw_prefix_horizon_materiality_reports_requested_horizons(tmp_path) -> None:
    log_dir = (
        tmp_path
        / "sample59_86"
        / "seed_1"
        / "npc_4"
        / "spawn_0p3"
        / "tl_on"
        / "static"
    )
    log_dir.mkdir(parents=True)
    (log_dir / "camp_selection_log.json").write_text(
        json.dumps([_record(selected_union_red=3.0), _record(selected_union_red=0.0)]),
        encoding="utf-8",
    )

    report = analyze([tmp_path], horizons=(2, 4), label="unit")

    assert report["records"] == {"logs": 1, "total": 2}
    assert report["summary"]["horizons"]["h2"]["raw_endpoint_pairwise_mean_m"][
        "mean"
    ] < report["summary"]["horizons"]["h4"]["raw_endpoint_pairwise_mean_m"][
        "mean"
    ]
    assert report["groups"]["traffic_lights=on"]["count"] == 2
    assert report["groups"]["npc=4"]["count"] == 2
    assert report["groups"]["selected_union_red_positive=true"]["count"] == 1
    assert (
        report["groups"]["selected_union_red_positive=true"]["state_values"][
            "selected_union_red"
        ]["mean"]
        == 3.0
    )
    assert not report["analysis"]["uses_outcome_labels"]

    markdown = render_markdown(report)
    assert "Raw Prefix Horizon Materiality Audit" in markdown
    assert "h4" in markdown


def test_raw_prefix_horizon_materiality_rejects_unlogged_horizon(tmp_path) -> None:
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps([_record()]), encoding="utf-8")

    with pytest.raises(ValueError, match="exceeds logged raw prefix length"):
        analyze([path], horizons=(5,), label="unit")
