from __future__ import annotations

import json

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner import (
    atom_schema_for_dimension,
)
from scripts.integrations.analyze_diffusion_planner_guarded_safety_selector import (
    GuardConfig,
    analyze,
)


def _write_selector(tmp_path):
    version, names = atom_schema_for_dimension(14)
    scales_path = tmp_path / "atom_scales_dp_static.json"
    weights_path = tmp_path / "offline_weights_dp_static.npy"
    scales_path.write_text(
        json.dumps(
            {
                "atom_schema_version": version,
                "atom_names": list(names),
                "scales": [1.0] * len(names),
            }
        ),
        encoding="utf-8",
    )
    weights = np.zeros(len(names), dtype=np.float64)
    weights[names.index("jerk_early")] = 1.0
    np.save(weights_path, weights)
    return scales_path, weights_path, names


def _outcome(index: int, *, collision: bool = False) -> dict[str, object]:
    return {
        "candidate_index": index,
        "progress_m": 10.0 - 0.1 * index,
        "collision": collision,
        "near_miss": collision,
        "lane_violation": False,
        "red_light_violation": False,
        "mean_jerk_mps3": 1.0,
        "mean_lateral_acceleration_mps2": 0.5,
    }


def _atoms(names: tuple[str, ...], *, jerk0: float, jerk1: float) -> list[list[float]]:
    rows = []
    for jerk, progress in ((jerk0, 0.0), (jerk1, 0.02)):
        row = [0.0] * len(names)
        row[names.index("jerk_early")] = jerk
        row[names.index("progress_shortfall")] = progress
        rows.append(row)
    return rows


def _write_log(tmp_path, names: tuple[str, ...], *, bad_clearance: bool) -> object:
    root = (
        tmp_path
        / "dev_root"
        / "nishishinjuku_lane_change"
        / "seed_3"
        / "npc_4"
        / "spawn_0p3"
        / "tl_off"
        / "static"
    )
    root.mkdir(parents=True)
    log_path = root / "camp_selection_log.json"
    soft = [0.0, 1.0 if bad_clearance else 0.0]
    near = [0.0, 1.0 if bad_clearance else 0.0]
    min_bound = [3.0, 1.0 if bad_clearance else 3.0]
    record = {
        "num_candidates": 2,
        "selected_index": 0,
        "feasible_mask": [True, True],
        "atom_names": list(names),
        "atoms": _atoms(names, jerk0=5.0, jerk1=0.1),
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.0],
        "candidate_horizon_lateral_acceleration_cost": [0.5, 0.5],
        "candidate_dp_prior_jerk_excess_cost": [1.0, 0.5],
        "candidate_perfect_tracker_target_speed_mps": [5.0, 5.0],
        "candidate_perfect_tracker_open_loop_rollout": {
            "10": {"distance_m": [10.0, 9.95]},
        },
        "candidate_obstacle_clearance": {
            "schema_version": "candidate_current_tick_obstacle_clearance_v2",
            "soft_clearance_violation_cost": soft,
            "near_miss_violation_cost": near,
            "min_obstacle_clearance_lower_bound_m": min_bound,
        },
        "candidate_closed_loop_outcomes": [
            _outcome(0),
            _outcome(1, collision=True),
        ],
    }
    log_path.write_text(json.dumps([record]), encoding="utf-8")
    return log_path


def test_guard_rejects_clearance_regressing_raw_selector(tmp_path) -> None:
    scales_path, weights_path, names = _write_selector(tmp_path)
    log_path = _write_log(tmp_path, names, bad_clearance=True)

    report = analyze(
        [log_path],
        atom_scales=scales_path,
        static_weights=weights_path,
        selector_name="unit_guarded",
        guard=GuardConfig(),
        required_buckets=(),
    )

    assert report["guard_summary"]["attempted_overrides"] == 1
    assert report["guard_summary"]["accepted_overrides"] == 0
    assert report["guard_summary"]["raw_worse_blocked"] == 1
    assert report["raw_vs_logged"]["evaluated_minus_logged_cost_mean"] > 0.0
    assert report["guarded_vs_logged"]["evaluated_minus_logged_cost_mean"] == pytest.approx(0.0)
    assert report["guard_summary"]["fail_reason_counts"]["soft_clearance"] == 1
    assert report["guard_summary"]["fail_reason_counts"]["near_miss_clearance"] == 1


def test_guard_allows_current_tick_nonworse_override(tmp_path) -> None:
    scales_path, weights_path, names = _write_selector(tmp_path)
    log_path = _write_log(tmp_path, names, bad_clearance=False)

    report = analyze(
        [log_path],
        atom_scales=scales_path,
        static_weights=weights_path,
        selector_name="unit_guarded",
        guard=GuardConfig(),
        required_buckets=(),
    )

    assert report["guard_summary"]["attempted_overrides"] == 1
    assert report["guard_summary"]["accepted_overrides"] == 1
    assert report["guard_summary"]["accepted_worse_overrides"] == 1
