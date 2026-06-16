from __future__ import annotations

import json

from scripts.integrations.analyze_diffusion_planner_raw_prefix_materiality_by_state import (
    analyze,
    render_markdown,
)


def _prefix(end_x: float, end_y: float, *, dim4: bool = False) -> list[list[float]]:
    rows = []
    for step in range(4):
        ratio = float(step + 1) / 4.0
        if dim4:
            rows.append([end_x * ratio, end_y * ratio, 1.0, 0.0])
        else:
            rows.append([end_x * ratio, end_y * ratio, 0.0])
    return rows


def _record(
    *,
    selected_index: int,
    used_fallback: bool,
    feasible_mask: list[bool],
    selected_union_red: float,
    progress_shortfall: float,
) -> dict:
    atom_names = [
        "progress_shortfall",
        "planned_lateral_acceleration_cost",
        "dp_prior_jerk_excess_cost",
    ]
    atoms = [[0.0, 0.0, 0.0] for _ in range(3)]
    atoms[selected_index] = [progress_shortfall, 0.5, 0.2]
    union_red = [0.0, 0.0, 0.0]
    union_red[selected_index] = selected_union_red
    full_red = [0.0, 0.0, 0.0]
    full_red[selected_index] = selected_union_red + 1.0 if selected_union_red else 0.0
    return {
        "num_candidates": 3,
        "selected_index": selected_index,
        "used_fallback": used_fallback,
        "feasible_mask": feasible_mask,
        "atom_names": atom_names,
        "atoms": atoms,
        "candidate_horizon_union_planned_red_light_cost": union_red,
        "candidate_full_horizon_planned_red_light_cost": full_red,
        "candidate_red_stopping_margin_cost": [0.0, 0.0, 0.0],
        "candidate_raw_trajectory_prefix": [
            _prefix(4.0, 0.0, dim4=True),
            _prefix(4.0, 1.0, dim4=True),
            _prefix(4.0, -1.0, dim4=True),
        ],
        "candidate_perfect_tracker_postprocessed_reference_prefix": [
            _prefix(4.0, 0.0),
            _prefix(4.0, 0.1),
            _prefix(4.0, -0.1),
        ],
    }


def test_raw_prefix_materiality_groups_by_state(tmp_path) -> None:
    log_dir = (
        tmp_path
        / "sample59_86"
        / "seed_1"
        / "npc_0"
        / "spawn_0p3"
        / "tl_on"
        / "static"
    )
    log_dir.mkdir(parents=True)
    log_path = log_dir / "camp_selection_log.json"
    log_path.write_text(
        json.dumps(
            [
                _record(
                    selected_index=1,
                    used_fallback=False,
                    feasible_mask=[True, True, True],
                    selected_union_red=2.0,
                    progress_shortfall=4.0,
                ),
                _record(
                    selected_index=0,
                    used_fallback=True,
                    feasible_mask=[False, False, False],
                    selected_union_red=0.0,
                    progress_shortfall=0.0,
                ),
            ]
        ),
        encoding="utf-8",
    )

    report = analyze([tmp_path], label="unit")

    assert report["records"] == {"logs": 1, "total": 2}
    assert report["groups"]["all"]["count"] == 2
    assert report["groups"]["traffic_lights=on"]["count"] == 2
    assert report["groups"]["npc=0"]["count"] == 2
    assert report["groups"]["fallback=true"]["count"] == 1
    assert report["groups"]["fallback=false"]["count"] == 1
    assert report["groups"]["selected_union_red_positive=true"]["count"] == 1
    assert (
        report["groups"]["selected_union_red_positive=true"]["state_values"][
            "selected_union_red"
        ]["mean"]
        == 2.0
    )
    assert (
        report["groups"]["selected_progress_shortfall_positive=true"]["state_values"][
            "selected_progress_shortfall_atom"
        ]["mean"]
        == 4.0
    )
    assert not report["analysis"]["uses_outcome_labels"]

    markdown = render_markdown(report)
    assert "Raw Prefix Materiality By State" in markdown
    assert "selected_union_red_positive=true" in markdown
