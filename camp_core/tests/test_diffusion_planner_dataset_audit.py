from __future__ import annotations

import json

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner import DP_CAMP_ATOM_NAMES_V8
from scripts.integrations.audit_diffusion_planner_camp_dataset import (
    audit_training_dataset,
)


def test_dataset_audit_checks_schema_outcomes_and_red_light_provenance(
    tmp_path,
) -> None:
    log_path = _write_completed_log(tmp_path)

    report = audit_training_dataset(
        [log_path],
        atom_scales=np.ones(12),
        expected_logs=1,
        expected_candidates=2,
        expected_advance_mode="perfect",
    )

    assert report["passed"]
    assert report["schema"]["version"] == "dp_camp_v8_12d"
    assert report["counts"] == {
        "logs": 1,
        "records": 1,
        "candidates": 2,
        "all_infeasible_records": 1,
    }
    assert report["checks"]["outcome_candidate_coverage"] == 1.0
    assert report["checks"]["red_light_atom_matches_online_dp_reward"]
    assert report["checks"]["advance_mode_verified"]
    assert len(report["logs"][0]["selection_log_sha256"]) == 64


def test_dataset_audit_rejects_red_light_atom_mismatch(tmp_path) -> None:
    log_path = _write_completed_log(tmp_path)
    records = json.loads(log_path.read_text(encoding="utf-8"))
    records[0]["atoms"][0][10] = 9.0
    log_path.write_text(json.dumps(records), encoding="utf-8")

    with pytest.raises(ValueError, match="provenance mismatch"):
        audit_training_dataset(
            [log_path],
            atom_scales=np.ones(12),
            expected_logs=1,
            expected_candidates=2,
            expected_advance_mode="perfect",
        )


def test_dataset_audit_requires_completed_run_summary(tmp_path) -> None:
    log_path = _write_completed_log(tmp_path)
    log_path.with_name("camp_validation_summary.json").unlink()

    with pytest.raises(ValueError, match="completed-run summary"):
        audit_training_dataset(
            [log_path],
            atom_scales=np.ones(12),
            expected_logs=1,
            expected_candidates=2,
            expected_advance_mode="perfect",
        )


def test_dataset_audit_rejects_wrong_advance_mode(tmp_path) -> None:
    log_path = _write_completed_log(tmp_path)
    summary_path = log_path.with_name("camp_validation_summary.json")
    summary_path.write_text(
        json.dumps({"selection_steps": 1, "advance_mode": "mpc"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="advance_mode"):
        audit_training_dataset(
            [log_path],
            atom_scales=np.ones(12),
            expected_logs=1,
            expected_candidates=2,
            expected_advance_mode="perfect",
        )


def _write_completed_log(tmp_path):
    log_path = tmp_path / "camp_selection_log.json"
    atoms = np.zeros((2, 12), dtype=float)
    atoms[:, 10] = [3.0, 0.0]
    outcomes = []
    for idx in range(2):
        outcomes.append(
            {
                "value": float(idx),
                "feasible": True,
                "collision": False,
                "near_miss": False,
                "lane_violation": False,
                "red_light_violation": idx == 0,
                "mean_jerk_mps3": 0.1,
                "mean_lateral_acceleration_mps2": 0.2,
            }
        )
    record = {
        "atom_schema_version": "dp_camp_v8_12d",
        "atom_names": list(DP_CAMP_ATOM_NAMES_V8),
        "atoms": atoms.tolist(),
        "feasible_mask": [False, False],
        "dp_candidate_rewards": [{"red_light": -3.0}, {"red_light": 0.0}],
        "candidate_closed_loop_outcomes": outcomes,
    }
    log_path.write_text(json.dumps([record]), encoding="utf-8")
    log_path.with_name("camp_validation_summary.json").write_text(
        json.dumps({"selection_steps": 1, "advance_mode": "perfect"}),
        encoding="utf-8",
    )
    return log_path
