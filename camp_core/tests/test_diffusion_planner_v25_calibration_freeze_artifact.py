from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact


ROOT = Path(__file__).resolve().parents[2]


def _module(relative: str, name: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRODUCER = _module(
    "scripts/integrations/freeze_diffusion_planner_v25_calibration.py",
    "v25_calibration_freeze_producer",
)
REVIEWER = _module(
    "scripts/integrations/review_diffusion_planner_v25_calibration_freeze.py",
    "v25_calibration_freeze_reviewer",
)


def _write(path: Path, value: object) -> None:
    path.write_bytes(
        (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    )


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(
        (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()


def _inputs(tmp_path: Path) -> tuple[Path, Path, str, Path, str]:
    roots = {
        "atom_audit_root": "1" * 64,
        "atom_audit_review_root": "2" * 64,
        "training_root": "3" * 64,
        "training_review_root": "4" * 64,
        "calibration_corpus_root": "5" * 64,
        "calibration_review_root": "6" * 64,
        "zero_overlap_root": "7" * 64,
    }
    rows = []
    for cluster in range(50):
        for repeat in range(2):
            index = cluster * 2 + repeat
            identity = {
                "schema_version": "camp_dp_v25_exact_candidate0_repeatability_identity_v1",
                "route_identity_sha256": f"{index + 1000:064x}",
                "scenario_identity_sha256": f"{index + 2000:064x}",
                "semantic_parameter_block_sha256": f"{index + 3000:064x}",
                "scenario_seed": 25001 + index,
                "spawn_config_sha256": f"{index + 4000:064x}",
                "initial_state_sha256": f"{index + 5000:064x}",
                "initial_input_sha256": f"{index + 6000:064x}",
                "same_initial_state_and_exogenous_schedule_per_pair": True,
            }
            rows.append(
                {
                    "schema_version": "camp_dp_v25_candidate0_ni_calibration_row_v2",
                    "arm": "candidate0_operational_default",
                    "heterogeneity_cluster_id": f"map-{cluster % 5:02d}",
                    "run_instance_sha256": f"{index + 7000:064x}",
                    "repeatability_identity": identity,
                    "repeatability_identity_sha256": _canonical_sha(identity),
                    "measurement_sha256": f"{index + 8000:064x}",
                    "performance": {
                        "progress": 80.0 + repeat * 0.01,
                        "completion": 0.8 + repeat * 0.001,
                        "mean_jerk": 0.5 + repeat * 0.01,
                        "max_jerk": 2.0 + repeat * 0.01,
                        "mean_lateral_acceleration": 0.3 + repeat * 0.01,
                        "max_lateral_acceleration": 1.0 + repeat * 0.01,
                        "maximum_deceleration": 2.0 + repeat * 0.01,
                    },
                    "fresh_b2_opened": False,
                    "fresh_outcome_fields_consumed": [],
                }
            )
    input_path = tmp_path / "inputs.json"
    calibration = tmp_path / "calibration"
    calibration.mkdir()
    corpus = {
        "schema_version": "camp_dp_v25_candidate0_calibration_corpus_projection_v2",
        "status": "passed_candidate0_calibration_corpus_projection",
        "fixed_dp_head": "7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "planned_run_count": 100,
        "complete_run_count": 100,
        "retained_fixed_dp_capability_failure_count": 0,
        "paired_eligible_rate": 1.0,
        "minimum_paired_eligible_rate": 0.95,
        "map_count": 5,
        "intersection_count": 50,
        "corridor_count": 50,
        "route_count": 50,
        "heterogeneity_diagnostic_cluster_definition": (
            "map_geometry_sha256_with_cross_scenario_route_seed_variation"
        ),
        "heterogeneity_diagnostic_cluster_count": 5,
        "repeatability_identity_definition": (
            "same_route_scenario_semantic_block_seed_initial_state_and_"
            "exogenous_schedule_binding"
        ),
        "exact_duplicate_repeatability_group_count": 0,
        "exact_duplicate_repeatability_measurement_count": 0,
        "candidate0_rows": rows,
        "candidate0_rows_sha256": _canonical_sha(rows),
        "retained_failures": [],
        "retained_failures_sha256": _canonical_sha([]),
        "candidate0_same_forward_operational_default": True,
        "candidate_tensor_modified": False,
        "camp_method_outcomes_consumed": False,
        "training_eligible_failure_count": 0,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    _write(calibration / "calibration_corpus.json", corpus)
    (calibration / "run.exit").write_bytes(b"0\n")
    calibration_root = seal_artifact(calibration, label="test calibration execution")
    calibration_review = tmp_path / "calibration_review"
    calibration_review.mkdir()
    _write(
        calibration_review / "report.json",
        {
            "status": "passed_independent_candidate0_calibration_execution_review",
            "reviewed_root_sha256": calibration_root,
            "fresh_b2_opened": False,
            "fresh_outcome_fields_consumed": [],
        },
    )
    (calibration_review / "run.exit").write_bytes(b"0\n")
    calibration_review_root = seal_artifact(
        calibration_review, label="test calibration execution review"
    )
    roots["calibration_corpus_root"] = calibration_root
    roots["calibration_review_root"] = calibration_review_root
    inputs = {
        "schema_version": "camp_dp_v25_calibration_freeze_inputs_v1",
        "root_bindings": roots,
        "inventory": {
            "map_count": 5,
            "intersection_count": 50,
            "corridor_count": 50,
            "route_count": 50,
            "planned_paired_run_count": 100,
            "paired_eligible_run_count": 100,
            "retained_failure_run_count": 0,
            "paired_eligible_rate": 1.0,
        },
        "frozen_model_registry_sha256": "8" * 64,
        "training_scale_sha256": "9" * 64,
        "context_scaler_sha256": "a" * 64,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    _write(input_path, inputs)
    return (
        input_path,
        calibration,
        calibration_root,
        calibration_review,
        calibration_review_root,
    )


def test_calibration_freeze_artifact_and_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(PRODUCER, "_tracked_dirty", lambda: False)
    monkeypatch.setattr(PRODUCER, "_git_head", lambda: "b" * 40)
    inputs, calibration, calibration_root, calibration_review, review_root = _inputs(
        tmp_path
    )
    artifact = tmp_path / "freeze"
    root = PRODUCER.build(
        inputs_path=inputs,
        calibration_artifact=calibration,
        calibration_root_sha256=calibration_root,
        calibration_review_artifact=calibration_review,
        calibration_review_root_sha256=review_root,
        output_dir=artifact,
    )
    report = REVIEWER.review(artifact, root)
    assert report["status"] == "passed_independent_calibration_freeze_review"
    assert report["calibration_status"] == "calibration_freeze_passed"
    assert report["candidate0_row_count"] == 100
    assert report["heterogeneity_cluster_count"] == 5
    assert report["repeatability_status"] == (
        "not_estimable_no_exact_candidate0_duplicates"
    )
    assert report["exact_duplicate_repeatability_group_count"] == 0
    assert report["operational_overspeed_tolerance_mps"] == 0.1
    assert report["fresh_open_authorized"] is False


def test_noncanonical_inputs_fail_before_artifact_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(PRODUCER, "_tracked_dirty", lambda: False)
    inputs, calibration, calibration_root, calibration_review, review_root = _inputs(
        tmp_path
    )
    value = json.loads(inputs.read_text(encoding="utf-8"))
    inputs.write_text(json.dumps(value, indent=2), encoding="utf-8")
    artifact = tmp_path / "freeze"
    with pytest.raises(ValueError, match="canonical"):
        PRODUCER.build(
            inputs_path=inputs,
            calibration_artifact=calibration,
            calibration_root_sha256=calibration_root,
            calibration_review_artifact=calibration_review,
            calibration_review_root_sha256=review_root,
            output_dir=artifact,
        )
    assert not artifact.exists()
