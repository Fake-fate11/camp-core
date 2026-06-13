from __future__ import annotations

import json

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner import (
    DP_CAMP_ATOM_NAMES_V8,
    DP_CAMP_ATOM_NAMES_V9,
    DP_CAMP_ATOM_NAMES_V10,
)
from scripts.integrations.augment_diffusion_planner_camp_v9_red_stopping import (
    augment_logs as augment_v9_logs,
)
from scripts.integrations.augment_diffusion_planner_camp_v10_jerk_excess import (
    augment_logs as augment_v10_logs,
)
from scripts.integrations.audit_diffusion_planner_camp_dataset import (
    audit_training_dataset,
    main as audit_dataset_main,
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
        required_candidate_fields=(
            "candidate_dp_prior_jerk_excess_cost",
            "candidate_dp_prior_acceleration_excess_cost",
        ),
        reference_zero_candidate_fields=(
            "candidate_dp_prior_jerk_excess_cost",
            "candidate_dp_prior_acceleration_excess_cost",
        ),
        forbidden_seeds=frozenset({11, 12, 13}),
        expected_comfort_shadow_horizon_steps=30,
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
    assert report["checks"]["forbidden_seed_check"]
    assert report["checks"]["summary_seed_provenance_verified"]
    assert report["checks"]["comfort_shadow_horizon_verified"]
    assert report["checks"]["expected_comfort_shadow_horizon_steps"] == 30
    assert report["candidate_fields"][
        "candidate_dp_prior_jerk_excess_cost"
    ] == {
        "records": 1,
        "candidates": 2,
        "records_with_variation": 1,
        "reference_zero_records": 1,
    }
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


def test_dataset_audit_default_requires_closed_loop_outcomes(tmp_path) -> None:
    log_path = _write_completed_log(tmp_path)
    records = json.loads(log_path.read_text(encoding="utf-8"))
    del records[0]["candidate_closed_loop_outcomes"]
    log_path.write_text(json.dumps(records), encoding="utf-8")

    with pytest.raises(ValueError, match="incomplete outcomes"):
        audit_training_dataset(
            [log_path],
            atom_scales=np.ones(12),
            expected_logs=1,
            expected_candidates=2,
            expected_advance_mode="perfect",
        )


def test_dataset_audit_forbidden_outcomes_certifies_deployable_logs(
    tmp_path,
) -> None:
    log_path = _write_completed_log(tmp_path)
    records = json.loads(log_path.read_text(encoding="utf-8"))
    del records[0]["candidate_closed_loop_outcomes"]
    log_path.write_text(json.dumps(records), encoding="utf-8")

    report = audit_training_dataset(
        [log_path],
        atom_scales=np.ones(12),
        expected_logs=1,
        expected_candidates=2,
        expected_advance_mode="perfect",
        closed_loop_outcome_policy="forbidden",
        required_candidate_fields=("candidate_dp_prior_jerk_excess_cost",),
        reference_zero_candidate_fields=("candidate_dp_prior_jerk_excess_cost",),
        expected_comfort_shadow_horizon_steps=30,
    )

    assert report["passed"]
    assert report["checks"]["closed_loop_outcome_policy"] == "forbidden"
    assert not report["checks"]["complete_closed_loop_outcomes"]
    assert report["checks"]["closed_loop_outcomes_forbidden"]
    assert report["checks"]["closed_loop_outcome_records"] == 0
    assert report["checks"]["outcome_candidate_coverage"] == 0.0


def test_dataset_audit_forbidden_outcomes_rejects_collected_outcomes(
    tmp_path,
) -> None:
    log_path = _write_completed_log(tmp_path)

    with pytest.raises(ValueError, match="forbidden"):
        audit_training_dataset(
            [log_path],
            atom_scales=np.ones(12),
            expected_logs=1,
            expected_candidates=2,
            closed_loop_outcome_policy="forbidden",
        )


def test_dataset_audit_forbidden_outcomes_allows_null_sentinel(
    tmp_path,
) -> None:
    log_path = _write_completed_log(tmp_path)
    records = json.loads(log_path.read_text(encoding="utf-8"))
    records[0]["candidate_closed_loop_outcomes"] = None
    log_path.write_text(json.dumps(records), encoding="utf-8")

    report = audit_training_dataset(
        [log_path],
        atom_scales=np.ones(12),
        expected_logs=1,
        expected_candidates=2,
        closed_loop_outcome_policy="forbidden",
    )

    assert report["passed"]
    assert not report["checks"]["complete_closed_loop_outcomes"]
    assert report["checks"]["closed_loop_outcome_records"] == 0
    assert report["checks"]["outcome_candidate_coverage"] == 0.0


def test_dataset_audit_cli_passes_closed_loop_outcome_policy(
    tmp_path,
    monkeypatch,
) -> None:
    log_path = _write_completed_log(tmp_path)
    records = json.loads(log_path.read_text(encoding="utf-8"))
    del records[0]["candidate_closed_loop_outcomes"]
    log_path.write_text(json.dumps(records), encoding="utf-8")
    scales_path = tmp_path / "atom_scales.json"
    scales_path.write_text(
        json.dumps(
            {
                "atom_schema_version": "dp_camp_v8_12d",
                "atom_names": list(DP_CAMP_ATOM_NAMES_V8),
                "scales": [1.0] * len(DP_CAMP_ATOM_NAMES_V8),
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "audit.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "audit_diffusion_planner_camp_dataset.py",
            "--selection_log",
            str(log_path),
            "--atom_scales",
            str(scales_path),
            "--expected_logs",
            "1",
            "--expected_candidates",
            "2",
            "--expected_advance_mode",
            "perfect",
            "--closed_loop_outcome_policy",
            "forbidden",
            "--output_json",
            str(output_path),
        ],
    )

    audit_dataset_main()

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["passed"]
    assert report["checks"]["closed_loop_outcome_policy"] == "forbidden"
    assert report["checks"]["outcome_candidate_coverage"] == 0.0


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
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["advance_mode"] = "mpc"
    summary_path.write_text(
        json.dumps(summary),
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


def test_dataset_audit_rejects_nonzero_candidate_reference(tmp_path) -> None:
    log_path = _write_completed_log(tmp_path)
    records = json.loads(log_path.read_text(encoding="utf-8"))
    records[0]["candidate_dp_prior_jerk_excess_cost"][0] = 0.1
    log_path.write_text(json.dumps(records), encoding="utf-8")

    with pytest.raises(ValueError, match="candidate 0 must be zero"):
        audit_training_dataset(
            [log_path],
            atom_scales=np.ones(12),
            expected_logs=1,
            expected_candidates=2,
            required_candidate_fields=(
                "candidate_dp_prior_jerk_excess_cost",
            ),
            reference_zero_candidate_fields=(
                "candidate_dp_prior_jerk_excess_cost",
            ),
        )


def test_dataset_audit_rejects_forbidden_seed(tmp_path) -> None:
    log_path = _write_completed_log(
        tmp_path
        / "run"
        / "route"
        / "seed_11"
        / "npc_0"
        / "spawn_0p3"
        / "tl_on"
        / "static",
        seed=11,
    )

    with pytest.raises(ValueError, match="forbidden seed 11"):
        audit_training_dataset(
            [log_path],
            atom_scales=np.ones(12),
            expected_logs=1,
            expected_candidates=2,
            forbidden_seeds=frozenset({11, 12, 13}),
        )


def test_dataset_audit_rejects_seed_provenance_mismatch(tmp_path) -> None:
    log_path = _write_completed_log(
        tmp_path
        / "run"
        / "route"
        / "seed_2"
        / "npc_0"
        / "spawn_0p3"
        / "tl_on"
        / "static",
        seed=1,
    )

    with pytest.raises(ValueError, match="does not match"):
        audit_training_dataset(
            [log_path],
            atom_scales=np.ones(12),
            expected_logs=1,
            expected_candidates=2,
        )


@pytest.mark.parametrize("invalid_horizon", [80, 30.0, True, None])
def test_dataset_audit_rejects_wrong_comfort_shadow_horizon(
    tmp_path,
    invalid_horizon,
) -> None:
    log_path = _write_completed_log(tmp_path)
    records = json.loads(log_path.read_text(encoding="utf-8"))
    records[0]["candidate_dp_prior_comfort_excess_horizon_steps"] = invalid_horizon
    log_path.write_text(json.dumps(records), encoding="utf-8")

    with pytest.raises(ValueError, match="comfort-shadow horizon"):
        audit_training_dataset(
            [log_path],
            atom_scales=np.ones(12),
            expected_logs=1,
            expected_candidates=2,
            expected_comfort_shadow_horizon_steps=30,
        )


def test_dataset_audit_rejects_wrong_summary_comfort_shadow_horizon(
    tmp_path,
) -> None:
    log_path = _write_completed_log(tmp_path)
    summary_path = log_path.with_name("camp_validation_summary.json")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["camp_shadow_dp_prior_comfort_excess"][
        "effective_horizon_steps"
    ] = 80
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    with pytest.raises(ValueError, match="does not certify"):
        audit_training_dataset(
            [log_path],
            atom_scales=np.ones(12),
            expected_logs=1,
            expected_candidates=2,
            expected_comfort_shadow_horizon_steps=30,
        )


def test_v9_red_stopping_augmentation_outputs_auditable_dataset(tmp_path) -> None:
    log_path = _write_completed_log(tmp_path / "source")
    output_root = tmp_path / "v9"

    manifest = augment_v9_logs(
        [(log_path, log_path.parent)],
        output_root=output_root,
    )
    augmented_log = output_root / "camp_selection_log.json"
    records = json.loads(augmented_log.read_text(encoding="utf-8"))

    assert manifest["schema"]["version"] == "dp_camp_v9_13d"
    assert records[0]["atom_schema_version"] == "dp_camp_v9_13d"
    assert records[0]["atom_names"] == list(DP_CAMP_ATOM_NAMES_V9)
    assert records[0]["source_atom_schema_version"] == "dp_camp_v8_12d"
    assert records[0]["atoms"][0][-1] == 1.5
    assert "normalized_atoms" not in records[0]

    report = audit_training_dataset(
        [augmented_log],
        atom_scales=np.ones(len(DP_CAMP_ATOM_NAMES_V9)),
        expected_logs=1,
        expected_candidates=2,
        expected_advance_mode="perfect",
    )

    assert report["passed"]
    assert report["schema"]["version"] == "dp_camp_v9_13d"
    assert report["counts"]["records"] == 1


def test_v10_jerk_excess_augmentation_outputs_auditable_dataset(
    tmp_path,
) -> None:
    source_log = _write_completed_log(tmp_path / "source")
    v9_root = tmp_path / "v9"
    augment_v9_logs(
        [(source_log, source_log.parent)],
        output_root=v9_root,
    )
    v9_log = v9_root / "camp_selection_log.json"
    v10_root = tmp_path / "v10"

    manifest = augment_v10_logs(
        [(v9_log, v9_root)],
        output_root=v10_root,
        expected_horizon_steps=30,
    )
    augmented_log = v10_root / "camp_selection_log.json"
    records = json.loads(augmented_log.read_text(encoding="utf-8"))

    assert manifest["schema"]["version"] == "dp_camp_v10_14d"
    assert manifest["contract"]["horizon_steps"] == 30
    assert records[0]["atom_schema_version"] == "dp_camp_v10_14d"
    assert records[0]["atom_names"] == list(DP_CAMP_ATOM_NAMES_V10)
    assert records[0]["source_atom_schema_version"] == "dp_camp_v9_13d"
    assert records[0]["atoms"][0][-1] == 0.0
    assert records[0]["atoms"][1][-1] == 1.5
    assert "normalized_atoms" not in records[0]

    report = audit_training_dataset(
        [augmented_log],
        atom_scales=np.ones(len(DP_CAMP_ATOM_NAMES_V10)),
        expected_logs=1,
        expected_candidates=2,
        expected_advance_mode="perfect",
        required_candidate_fields=(
            "candidate_dp_prior_jerk_excess_cost",
        ),
        reference_zero_candidate_fields=(
            "candidate_dp_prior_jerk_excess_cost",
        ),
        expected_comfort_shadow_horizon_steps=30,
    )

    assert report["passed"]
    assert report["schema"]["version"] == "dp_camp_v10_14d"
    assert report["counts"]["records"] == 1


def _write_completed_log(tmp_path, *, seed=1):
    tmp_path.mkdir(parents=True, exist_ok=True)
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
        "selection_scores": [0.0, float("inf")],
        "dp_candidate_rewards": [{"red_light": -3.0}, {"red_light": 0.0}],
        "candidate_closed_loop_outcomes": outcomes,
        "candidate_red_stopping_margin_cost": [1.5, 0.0],
        "candidate_dp_prior_jerk_excess_cost": [0.0, 1.5],
        "candidate_dp_prior_acceleration_excess_cost": [0.0, 0.2],
        "candidate_dp_prior_comfort_excess_horizon_steps": 30,
    }
    log_path.write_text(json.dumps([record]), encoding="utf-8")
    log_path.with_name("camp_validation_summary.json").write_text(
        json.dumps(
            {
                "selection_steps": 1,
                "advance_mode": "perfect",
                "camp_shadow_dp_prior_comfort_excess": {
                    "effective_horizon_steps": 30,
                },
                "benchmark": {"seed": seed},
            }
        ),
        encoding="utf-8",
    )
    return log_path
