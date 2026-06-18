from __future__ import annotations

import json

import numpy as np

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension
from scripts.integrations.analyze_diffusion_planner_guarded_top1_floor_counterfactual import (
    analyze,
)


def test_top1_red_floor_falls_back_when_guarded_red_proxy_is_worse(tmp_path) -> None:
    scales_path, weights_path, names = _write_selector(tmp_path)
    log_path = _write_log(tmp_path, names)

    report = analyze(
        [log_path],
        atom_scales=scales_path,
        static_weights=weights_path,
        selector_name="unit_floor",
        required_buckets=(),
    )
    rules = {rule["name"]: rule for rule in report["rules"]}

    no_floor = rules["guarded_no_top1_floor"]
    red_floor = rules["top1_red_floor"]

    assert no_floor["floor_summary"]["top1_fallbacks"] == 0
    assert no_floor["overall"]["run_level_delta_ci"]["camp_minus_top1"]["mean"] > 0.0
    assert red_floor["floor_summary"]["top1_fallbacks"] == 1
    assert red_floor["floor_summary"]["trigger_reason_counts"] == {
        "union_red": 1
    }
    assert red_floor["overall"]["run_level_delta_ci"]["camp_minus_top1"]["mean"] == 0.0


def test_unconditional_top1_red_floor_can_ignore_feasible_mask(tmp_path) -> None:
    scales_path, weights_path, names = _write_selector(tmp_path)
    log_path = _write_log(tmp_path, names, candidate0_feasible=False)

    report = analyze(
        [log_path],
        atom_scales=scales_path,
        static_weights=weights_path,
        selector_name="unit_floor",
        required_buckets=(),
    )
    rules = {rule["name"]: rule for rule in report["rules"]}

    red_floor = rules["top1_red_floor"]
    unconditional = rules["top1_red_floor_unconditional"]

    assert red_floor["floor_summary"]["top1_fallbacks"] == 0
    assert red_floor["floor_summary"]["candidate0_infeasible_records"] == 1
    assert unconditional["floor_summary"]["top1_fallbacks"] == 1
    assert unconditional["floor_summary"]["candidate0_infeasible_top1_fallbacks"] == 1
    assert unconditional["floor_summary"]["trigger_reason_counts"] == {
        "union_red": 1
    }


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
    weights[names.index("progress_shortfall")] = 1.0
    np.save(weights_path, weights)
    return scales_path, weights_path, names


def _write_log(
    tmp_path,
    names: tuple[str, ...],
    *,
    candidate0_feasible: bool = True,
):
    root = (
        tmp_path
        / "dev_root"
        / "sample_tl_turn"
        / "seed_1"
        / "npc_0"
        / "spawn_0p3"
        / "tl_on"
        / "static"
    )
    root.mkdir(parents=True)
    (root / "camp_validation_summary.json").write_text(
        json.dumps(
            {
                "benchmark": {
                    "route": "/tmp/sample_tl_turn.pkl",
                    "seed": 1,
                    "steps": 1,
                    "max_npcs": 0,
                    "spawn_probability": 0.3,
                    "traffic_lights": True,
                    "advance_mode": "perfect",
                }
            }
        ),
        encoding="utf-8",
    )
    log_path = root / "camp_selection_log.json"
    record = {
        "num_candidates": 2,
        "selected_index": 1,
        "feasible_mask": [candidate0_feasible, True],
        "atom_names": list(names),
        "atoms": _atoms(names),
        "normalized_atoms": _atoms(names),
        "selection_normalized_atoms": _atoms(names),
        "scores": [0.5, 0.1],
        "selection_scores": [0.5, 0.1],
        "weights": [1.0] * len(names),
        "selection_weights": [1.0] * len(names),
        "candidate_horizon_union_planned_red_light_cost": [0.0, 1.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.0],
        "candidate_horizon_lateral_acceleration_cost": [0.0, 0.0],
        "candidate_dp_prior_jerk_excess_cost": [0.0, 0.0],
        "candidate_closed_loop_outcomes": [
            _outcome(0),
            _outcome(1),
        ],
    }
    log_path.write_text(json.dumps([record]), encoding="utf-8")
    return log_path


def _atoms(names: tuple[str, ...]) -> list[list[float]]:
    rows = []
    for progress in (0.5, 0.1):
        row = [0.0] * len(names)
        row[names.index("progress_shortfall")] = progress
        rows.append(row)
    return rows


def _outcome(index: int) -> dict[str, object]:
    return {
        "candidate_index": index,
        "horizon_steps": 30,
        "progress_m": 10.0,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
        "mean_jerk_mps3": 0.0,
        "mean_lateral_acceleration_mps2": 0.0,
    }
