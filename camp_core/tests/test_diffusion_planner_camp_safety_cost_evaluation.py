from __future__ import annotations

import json
import sys

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner import (
    CAMP_ATOM_NAMES,
    atom_schema_for_dimension,
)
from scripts.integrations.evaluate_diffusion_planner_camp_safety_cost import (
    analyze,
    main,
    render_markdown,
)


def _outcome(
    index: int,
    *,
    progress: float,
    jerk: float,
    lateral: float,
    collision: bool = False,
    near_miss: bool = False,
    lane_violation: bool = False,
    red_light_violation: bool = False,
) -> dict[str, object]:
    return {
        "candidate_index": index,
        "progress_m": progress,
        "collision": collision,
        "near_miss": near_miss,
        "lane_violation": lane_violation,
        "red_light_violation": red_light_violation,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
    }


def _write_selector(tmp_path):
    version, names = atom_schema_for_dimension(len(CAMP_ATOM_NAMES))
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
    weights[0] = 1.0
    np.save(weights_path, weights)
    return scales_path, weights_path


def _write_log(tmp_path):
    root = (
        tmp_path
        / "dev_root"
        / "sample_normal"
        / "seed_1"
        / "npc_0"
        / "spawn_0p3"
        / "tl_off"
        / "static"
    )
    root.mkdir(parents=True)
    log_path = root / "camp_selection_log.json"
    record = {
        "num_candidates": 3,
        "selected_index": 0,
        "feasible_mask": [True, True, True],
        "atoms": [
            [5.0] + [0.0] * (len(CAMP_ATOM_NAMES) - 1),
            [1.0] + [0.0] * (len(CAMP_ATOM_NAMES) - 1),
            [2.0] + [0.0] * (len(CAMP_ATOM_NAMES) - 1),
        ],
        "candidate_horizon_union_planned_red_light_cost": [1.0, 0.0, 0.0],
        "candidate_closed_loop_outcomes": [
            _outcome(
                0,
                progress=10.0,
                jerk=8.0,
                lateral=2.0,
                red_light_violation=True,
            ),
            _outcome(1, progress=9.9, jerk=3.0, lateral=1.0),
            _outcome(2, progress=9.9, jerk=0.5, lateral=0.2, collision=True),
        ],
    }
    log_path.write_text(json.dumps([record]), encoding="utf-8")
    (root / "camp_validation_summary.json").write_text(
        json.dumps(
            {
                "benchmark": {
                    "route": "/routes/sample_normal.pkl",
                    "seed": 1,
                    "steps": 200,
                    "max_npcs": 0,
                    "spawn_probability": 0.3,
                    "traffic_lights": False,
                    "advance_mode": "perfect",
                }
            }
        ),
        encoding="utf-8",
    )
    return log_path


def test_camp_safety_cost_evaluation_reselects_saved_selector(tmp_path) -> None:
    scales_path, weights_path = _write_selector(tmp_path)
    log_path = _write_log(tmp_path)

    report = analyze(
        [log_path],
        atom_scales=scales_path,
        static_weights=weights_path,
        selector_name="unit_selector",
        required_buckets=(),
    )

    evaluated = report["evaluated_selector"]["overall"]
    logged = report["logged_selector"]["overall"]
    comparison = report["selector_comparison"]

    assert evaluated["record_rates"]["camp_matches_hard_guarded_oracle"] == 1.0
    assert evaluated["run_level_delta_ci"]["camp_minus_top1"]["mean"] < 0.0
    assert logged["run_level_delta_ci"]["camp_minus_top1"]["mean"] == 0.0
    assert comparison["changed_record_rate"] == 1.0
    assert comparison["evaluated_minus_logged_cost_mean"] < 0.0
    assert report["analysis"]["future_outcome_leakage"].startswith(
        "candidate_closed_loop_outcomes are used only for offline evaluation"
    )

    markdown = render_markdown(report)
    assert "Selector-vs-Logged" in markdown
    assert "unit_selector" in markdown


def test_camp_safety_cost_evaluation_cli_writes_outputs(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scales_path, weights_path = _write_selector(tmp_path)
    log_path = _write_log(tmp_path)
    output_json = tmp_path / "eval.json"
    output_md = tmp_path / "eval.md"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluate_diffusion_planner_camp_safety_cost.py",
            "--selection_log",
            str(log_path),
            "--atom_scales",
            str(scales_path),
            "--static_weights",
            str(weights_path),
            "--selector_name",
            "cli_selector",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["selector_name"] == "cli_selector"
    assert "Candidate-Branch SafetyCost v1 Selector Evaluation" in output_md.read_text(
        encoding="utf-8"
    )
