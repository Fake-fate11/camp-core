from __future__ import annotations

import json

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner import DP_CAMP_ATOM_NAMES_V8
from scripts.integrations.analyze_diffusion_planner_camp_fallback import (
    compute_fallback_ablation_report,
)


def test_fallback_ablation_is_paired_and_all_infeasible_only(tmp_path) -> None:
    records = [
        _record(
            feasible=[True, False],
            atoms=[[0.0] * 12, [1.0] * 12],
            values=[1.0, 0.0],
        ),
        _record(
            feasible=[False, False],
            atoms=[
                [2.0, 0.0] + [0.0] * 10,
                [0.0, 10.0] + [0.0] * 10,
            ],
            values=[0.0, 4.0],
            red_light=[1.0, 0.0],
            lateral=[2.0, 0.2],
        ),
    ]
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(json.dumps(records), encoding="utf-8")
    learned = np.zeros(12)
    learned[0] = 1.0

    report = compute_fallback_ablation_report(
        [log_path],
        atom_scales=np.ones(12),
        learned_weights=learned,
        require_atom_schema=True,
    )

    assert report["records"] == {
        "total": 2,
        "all_infeasible": 1,
        "schema_verified": 2,
    }
    assert report["uniform"]["mean_outcome_value"] == 0.0
    assert report["learned"]["mean_outcome_value"] == 4.0
    assert report["learned"]["oracle_match_rate"] == 1.0
    assert report["paired"]["selection_disagreement_rate"] == 1.0
    assert report["paired"]["learned_minus_uniform_outcome_value"] == 4.0
    assert report["paired"]["learned_minus_uniform_red_light_violation"] == -1.0
    assert (
        report["paired"]["learned_minus_uniform_mean_lateral_acceleration_mps2"]
        == pytest.approx(-1.8)
    )


def test_fallback_ablation_rejects_non_simplex_weights(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(
        json.dumps(
            [
                _record(
                    feasible=[False, False],
                    atoms=[[0.0] * 12, [1.0] * 12],
                    values=[1.0, 0.0],
                )
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unit-sum"):
        compute_fallback_ablation_report(
            [log_path],
            atom_scales=np.ones(12),
            learned_weights=np.ones(12),
            require_atom_schema=True,
        )


def _record(
    *,
    feasible: list[bool],
    atoms: list[list[float]],
    values: list[float],
    red_light: list[float] | None = None,
    lateral: list[float] | None = None,
) -> dict:
    count = len(atoms)
    red_light = red_light or [0.0] * count
    lateral = lateral or [0.0] * count
    return {
        "atom_schema_version": "dp_camp_v8_12d",
        "atom_names": list(DP_CAMP_ATOM_NAMES_V8),
        "atoms": atoms,
        "feasible_mask": feasible,
        "candidate_closed_loop_outcomes": [
            {
                "value": values[idx],
                "collision": False,
                "near_miss": False,
                "lane_violation": False,
                "red_light_violation": red_light[idx],
                "mean_jerk_mps3": 0.1,
                "mean_lateral_acceleration_mps2": lateral[idx],
            }
            for idx in range(count)
        ],
    }
