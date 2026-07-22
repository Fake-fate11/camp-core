from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact
from camp_core.integrations.diffusion_planner_v21_native import array_sha256
from camp_core.integrations.diffusion_planner_v25_context import (
    CONTEXT_SCHEMA_VERSION,
    PHI_DIMENSION,
    RAW_FEATURE_COUNT,
    RAW_FEATURE_NAMES,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (
    FIXED_DP_HEAD,
    MODEL_NAME,
    SCENE_RECEIPT_SCHEMA_VERSION,
    load_v25_runtime_selector_assets,
    load_v25_scene14d_weight_provider,
)
from camp_core.integrations.diffusion_planner_v25_train_atom_audit import ATOM_NAMES


def _write_json(path: Path, value) -> None:
    path.write_bytes(
        (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    )


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _training_authority(tmp_path: Path):
    training = tmp_path / "training"
    training.mkdir()
    theta = np.zeros((14, PHI_DIMENSION), dtype=np.float64)
    for column in range(PHI_DIMENSION):
        theta[column % 14, column] = 1.0
    static_theta = np.full((14, PHI_DIMENSION), 1.0 / 14.0, dtype=np.float64)
    model_reports = {
        "CAMP-Static14D": {
            "mode": "static",
            "active_atom_indices": list(range(14)),
            "theta_column_simplex": True,
            "runtime_projection": False,
            "softmax": False,
            "outcome_or_fresh_consumed": False,
            "theta_sha256": array_sha256(static_theta),
        },
        "CAMP-Scene14D": {
            "mode": "scene",
            "active_atom_indices": list(range(14)),
            "theta_column_simplex": True,
            "runtime_projection": False,
            "softmax": False,
            "outcome_or_fresh_consumed": False,
            "theta_sha256": array_sha256(theta),
        },
        "CAMP-Static9D": {},
        "CAMP-Scene9D": {},
    }
    entries = [
        ("CAMP-Static14D", "static14d", "static", 14, True, False),
        ("CAMP-Scene14D", "scene14d", "scene", 14, True, False),
        ("CAMP-Static9D", "static9d", "static", 9, False, True),
        ("CAMP-Scene9D", "scene9d", "scene", 9, False, True),
    ]
    parameters = {
        "schema_version": np.asarray("camp_dp_v25_trained_model_parameters_v1"),
        "context_feature_names": np.asarray(RAW_FEATURE_NAMES),
        "context_q05": np.zeros(RAW_FEATURE_COUNT, dtype=np.float64),
        "context_q95": np.ones(RAW_FEATURE_COUNT, dtype=np.float64),
        "training_scales_14d": np.ones(14, dtype=np.float64),
    }
    for name, prefix, mode, atom_count, _primary, _ablation in entries:
        parameters[f"{prefix}_theta"] = (
            theta
            if name == MODEL_NAME
            else (
                static_theta
                if name == "CAMP-Static14D"
                else np.full(
                    (atom_count, PHI_DIMENSION),
                    1.0 / atom_count,
                    dtype=np.float64,
                )
            )
        )
        parameters[f"{prefix}_selected_indices"] = np.zeros(1, dtype=np.int64)
        parameters[f"{prefix}_selection_margins"] = np.zeros(1, dtype=np.float64)
        parameters[f"{prefix}_train_violations"] = np.zeros(
            (1, 8), dtype=np.float64
        )
        parameters[f"{prefix}_cut_mask"] = np.ones((1, 1), dtype=np.bool_)
        if mode == "static":
            parameters[f"{prefix}_runtime_weights"] = parameters[
                f"{prefix}_theta"
            ][:, 0]
    np.savez_compressed(training / "model_parameters.npz", **parameters)
    runtime_scales = {
        "schema_version": "camp_dp_v25_runtime_atom_scales_v1",
        "atom_schema_version": "dp_camp_v10_14d",
        "atom_names": list(ATOM_NAMES),
        "scales": np.ones(14, dtype=np.float64).tolist(),
        "scale_source": "sealed_train_only_block_weighted_positive_support",
        "calibration_or_fresh_consumed": False,
    }
    _write_json(training / "runtime_atom_scales.json", runtime_scales)
    np.save(
        training / "static14d_runtime_weights.npy",
        parameters["static14d_theta"][:, 0],
    )
    registry = {
        "schema_version": "camp_dp_v25_model_registry_v1",
        "models": [
            {
                "name": name,
                "parameter_prefix": prefix,
                "mode": mode,
                "active_atom_indices": list(range(atom_count)),
                "primary_method": primary,
                "paper_subset_ablation": ablation,
            }
            for name, prefix, mode, atom_count, primary, ablation in entries
        ],
        "candidate0_semantics": "operational_default_alias_from_same_forward",
        "fresh_or_outcome_consumed": False,
    }
    report = {
        "schema_version": "camp_dp_v25_strict_convex_training_artifact_v1",
        "status": "passed_strict_convex_training",
        "camp_head": "a" * 40,
        "fixed_dp_head": FIXED_DP_HEAD,
        "model_parameters_sha256": _file_sha(training / "model_parameters.npz"),
        "runtime_assets": {
            "atom_scales": {
                "relative_path": "runtime_atom_scales.json",
                "sha256": _file_sha(training / "runtime_atom_scales.json"),
                "model_scope": ["CAMP-Static14D", "CAMP-Scene14D"],
            },
            "static14d_weights": {
                "relative_path": "static14d_runtime_weights.npy",
                "sha256": _file_sha(
                    training / "static14d_runtime_weights.npy"
                ),
                "model_scope": ["CAMP-Static14D"],
            },
        },
        "model_reports": model_reports,
        "all_models_converged": True,
        "all_solver_status_optimal": True,
        "same_rows_labels_scales_and_block_weights": True,
        "selection_eligibility": "source_valid_candidate_set",
        "physical_feasible_mask_consumed_by_training": False,
        "calibration_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    _write_json(training / "model_registry.json", registry)
    _write_json(training / "model_reports.json", model_reports)
    _write_json(training / "report.json", report)
    (training / "HEADS").write_bytes(
        ("camp_head=" + "a" * 40 + f"\nfixed_dp_head={FIXED_DP_HEAD}\n").encode(
            "ascii"
        )
    )
    (training / "COMMAND").write_text("test\n", encoding="utf-8")
    (training / "run.exit").write_bytes(b"0\n")
    training_root = seal_artifact(training, label="test V25 training")

    review = tmp_path / "review"
    review.mkdir()
    review_report = {
        "schema_version": "camp_dp_v25_strict_convex_training_review_v1",
        "status": "passed_independent_strict_convex_training_review",
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(training.resolve()),
        "reviewed_root_sha256": training_root,
        "models": {name: {} for name, *_rest in entries},
        "phase_remaining_available_count": 0,
        "selection_eligibility": "source_valid_candidate_set",
        "physical_feasible_mask_consumed_by_training": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    _write_json(review / "report.json", review_report)
    (review / "HEADS").write_bytes(
        ("camp_head=" + "a" * 40 + f"\nfixed_dp_head={FIXED_DP_HEAD}\n").encode(
            "ascii"
        )
    )
    (review / "COMMAND").write_text("test\n", encoding="utf-8")
    (review / "run.exit").write_bytes(b"0\n")
    review_root = seal_artifact(review, label="test V25 training review")
    return training, training_root, review, review_root, theta


def _context_payload() -> dict:
    raw = {name: 0.25 for name in RAW_FEATURE_NAMES}
    source = {name: True for name in RAW_FEATURE_NAMES}
    raw["traffic_signal_phase_remaining_s"] = 0.0
    source["traffic_signal_phase_remaining_s"] = False
    return {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "raw_context": raw,
        "source_complete": source,
        "source_receipt": {
            "mode": "no_v2i",
            "phase_remaining_available": False,
            "regulatory_signal_mapped": True,
        },
    }


def test_sealed_scene14d_provider_evaluates_affine_simplex_without_projection(
    tmp_path: Path,
) -> None:
    training, training_root, review, review_root, theta = _training_authority(tmp_path)
    provider = load_v25_scene14d_weight_provider(
        training_artifact=training,
        training_root_sha256=training_root,
        training_review_artifact=review,
        training_review_root_sha256=review_root,
    )
    receipt = provider(_context_payload())
    assert receipt["schema_version"] == SCENE_RECEIPT_SCHEMA_VERSION
    assert receipt["model_name"] == MODEL_NAME
    assert receipt["fixed_dp_head"] == FIXED_DP_HEAD
    assert receipt["theta_sha256"] == array_sha256(theta)
    assert receipt["training_root_sha256"] == training_root
    assert receipt["training_review_root_sha256"] == review_root
    assert receipt["runtime_projection"] is False
    assert receipt["softmax"] is False
    weights = np.asarray(receipt["weights"], dtype=np.float64)
    assert np.all(weights >= 0.0)
    assert weights.sum() == pytest.approx(1.0, abs=1e-12)
    assert receipt["weights_sha256"] == array_sha256(weights)


def test_sealed_runtime_assets_bind_static_and_scene_to_same_authority(
    tmp_path: Path,
) -> None:
    training, training_root, review, review_root, _theta = _training_authority(tmp_path)
    assets = load_v25_runtime_selector_assets(
        training_artifact=training,
        training_root_sha256=training_root,
        training_review_artifact=review,
        training_review_root_sha256=review_root,
    )
    assert assets.training_root_sha256 == training_root
    assert assets.training_review_root_sha256 == review_root
    np.testing.assert_array_equal(
        assets.static14d_weights,
        np.load(training / "static14d_runtime_weights.npy", allow_pickle=False),
    )
    np.testing.assert_array_equal(assets.atom_scales, np.ones(14, dtype=np.float64))
    assert assets.scene14d_weight_provider.training_root_sha256 == training_root


@pytest.mark.parametrize("artifact_role", ("training", "review"))
def test_runtime_assets_reject_physical_feasibility_as_training_eligibility(
    tmp_path: Path, artifact_role: str
) -> None:
    training, training_root, review, review_root, _theta = _training_authority(tmp_path)
    target = training if artifact_role == "training" else review
    report = json.loads((target / "report.json").read_text(encoding="utf-8"))
    report["physical_feasible_mask_consumed_by_training"] = True
    (target / "SHA256SUMS").unlink()
    (target / "ROOT_SHA256SUMS").unlink()
    _write_json(target / "report.json", report)
    mutated_root = seal_artifact(target, label=f"mutated {artifact_role}")
    if artifact_role == "training":
        training_root = mutated_root
    else:
        review_root = mutated_root
    with pytest.raises(ValueError, match="training/review authority drifted"):
        load_v25_runtime_selector_assets(
            training_artifact=training,
            training_root_sha256=training_root,
            training_review_artifact=review,
            training_review_root_sha256=review_root,
        )


@pytest.mark.parametrize(
    "mutation",
    (
        "phase_remaining_available",
        "phase_remaining_source",
        "extra_context",
        "numeric_string",
    ),
)
def test_scene14d_provider_fails_closed_on_noncausal_or_type_drift(
    tmp_path: Path, mutation: str
) -> None:
    training, training_root, review, review_root, _theta = _training_authority(tmp_path)
    provider = load_v25_scene14d_weight_provider(
        training_artifact=training,
        training_root_sha256=training_root,
        training_review_artifact=review,
        training_review_root_sha256=review_root,
    )
    payload = _context_payload()
    if mutation == "phase_remaining_available":
        payload["source_receipt"]["phase_remaining_available"] = True
    elif mutation == "phase_remaining_source":
        payload["source_complete"]["traffic_signal_phase_remaining_s"] = True
    elif mutation == "extra_context":
        payload["raw_context"]["route_id"] = 1.0
    else:
        payload["raw_context"]["ego_speed_mps"] = "1.0"
    with pytest.raises(ValueError):
        provider(payload)
