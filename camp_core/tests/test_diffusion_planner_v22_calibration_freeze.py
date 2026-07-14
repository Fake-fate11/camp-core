from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
CONFIG = (
    ROOT
    / "configs"
    / "integrations"
    / "diffusion_planner_v22_calibration_freeze.json"
)


def _module():
    from scripts.integrations import train_diffusion_planner_v22_selector

    return train_diffusion_planner_v22_selector


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _model(weight_index: int, *, name: str = "all_available_2") -> dict:
    weights = np.zeros(14, dtype=np.float64)
    weights[weight_index] = 1.0
    return {
        "schema_version": "v22_static_affine_selector_model_v1",
        "level_name": name,
        "training_source": "v22_train_snapshots_only",
        "snapshot_count": 2,
        "atom_schema_version": "dp_camp_v10_14d",
        "atom_names": list(_module().DP_CAMP_ATOM_NAMES_V10),
        "atom_scales": [1.0] * 14,
        "supported_atom_mask": [True] * 14,
        "weights": weights.tolist(),
        "normalized_atom_clip": 10.0,
        "score_contract": "score_k(w)=a_k^T w",
        "oracle_eligibility": "source_valid_mask_only",
        "unsupported_atoms_receive_zero_weight": True,
        "solver": {"name": "CLARABEL", "status": "optimal", "converged": True},
        "actual_closed_loop_outcome": False,
        "calibration_executed": False,
        "holdout_executed": False,
        "claim_authorized": False,
        "model_sha256": _sha(name),
    }


def _config() -> dict:
    return {
        "schema_version": "camp_dp_v22_calibration_freeze_v1",
        "execution_split": "calibration",
        "expected_snapshot_count": 2,
        "expected_route_count": 1,
        "expected_seed_count": 1,
        "expected_route_seed_count": 1,
        "model_selection_metric": "mean_causal_soft_risk_surrogate_cost",
        "model_selection_tie_break": "level_name_lexicographic",
        "retraining_authorized": False,
        "solver_authorized": False,
        "formal_seeds_authorized": False,
        "holdout_execution_authorized": False,
        "claim_authorized": False,
        "speed_protocol": {
            "primary_operational_tolerance_mps": 0.1,
            "calibration_sensitivity_tolerances_mps": [0.0, 0.05, 0.1, 0.2],
            "sensitivity_source": "pilot_closed_loop_outcomes_not_snapshot_surrogate",
        },
        "label_contract": {
            "schema_version": "v22_causal_soft_risk_surrogate_v1",
            "physical_risk_penalty": 100.0,
            "normalized_atom_clip": 10.0,
            "atom_severity_weights": [1.0] + [0.0] * 13,
            "oracle_eligibility": "source_valid_mask_only",
            "physical_risk_semantics": "finite_additive_cost_not_veto",
            "actual_closed_loop_outcome": False,
        },
        "claim_contract": {
            "overall_mean_delta_strictly_below_zero": True,
            "cluster_ci95_upper_strictly_below_zero": True,
            "better_pairs_must_exceed_worse_pairs": True,
            "additional_collision_pairs_max": 0,
            "additional_red_light_pairs_max": 0,
            "offroad_wrong_way_mean_delta_max": 0.0,
            "offroad_wrong_way_ci95_upper_max": 0.005,
        },
    }


def _arrays() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    atoms = np.ones((2, 8, 14), dtype=np.float64)
    atoms[:, 2, 0] = 0.0
    valid = np.ones((2, 8), dtype=bool)
    physical = np.ones((2, 8), dtype=bool)
    return atoms, valid, physical


def _snapshot(
    *, split: str = "calibration", provenance: str | None = None,
    add_identity_feature: bool = False,
) -> dict:
    atoms, valid, physical = _arrays()
    rows = [_sha(f"row:{index}") for index in range(8)]
    features = {
        "atom_matrix": atoms[0].tolist(),
        "source_valid_mask": valid[0].tolist(),
        "candidate_row_sha256": rows,
    }
    if add_identity_feature:
        features["route_id"] = "forbidden"
    return {
        "schema_version": "v22_native_decision_snapshot_v1",
        "feature_payload": features,
        "sidecar": {
            "split": split,
            "seed": 22101,
            "logical_map_sha256": _sha("map"),
            "route_identity_sha256": _sha("route"),
            "group_sha256": _sha("group"),
            "tick_index": 5,
            "physical_feasible_mask": physical[0].tolist(),
            "all_k_high_risk": False,
            "offline_label_provenance": provenance or (
                "calibration_causal_candidate_cost_sidecar_only_not_selector_feature"
            ),
            "candidate_tensor_sha256_before": _sha("tensor"),
            "candidate_tensor_sha256_after": _sha("tensor"),
            "default_output_sha256": rows[0],
            "candidate0_sha256": rows[0],
            "default_candidate0_identity": {"elementwise_equal": True},
        },
    }


def _write_calibration_artifact(root: Path, payload: dict) -> Path:
    snapshot_dir = root / "corpus" / "snapshots"
    snapshot_dir.mkdir(parents=True)
    content = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode()
    digest = hashlib.sha256(content).hexdigest()
    (snapshot_dir / f"{digest}.json").write_bytes(content)
    summary = {
        "execution_split": "calibration",
        "planned_route_seed_runs": 1,
        "retained_route_seed_runs": 1,
        "complete_route_seed_runs": 1,
        "failed_route_seed_runs": 0,
        "route_coverage": 1.0,
        "all_k_high_risk_snapshot_count": 0,
        "calibration_executed": True,
        "holdout_executed": False,
        "holdout_outcomes_read": False,
        "claim_authorized": False,
        "failures": [],
    }
    (root / "corpus" / "corpus_summary.json").write_text(
        json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return root


def _loader_config() -> dict:
    config = _config()
    config.update(
        {
            "expected_snapshot_count": 1,
            "expected_retained_route_seed_count": 1,
            "expected_complete_route_seed_count": 1,
            "expected_hard_source_failure_count": 0,
        }
    )
    return config


def test_tracked_freeze_config_seals_roots_tolerance_and_no_holdout() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))

    assert config["execution_split"] == "calibration"
    assert config["expected_snapshot_count"] == 1170
    assert config["expected_route_count"] == 30
    assert config["expected_seed_count"] == 3
    assert config["expected_route_seed_count"] == 90
    assert config["training_candidate"]["model_sha256"] == (
        "33d4d9b23e7cc505e546a8bf33ca7477f072118ea1fda6dad9744969fc00956a"
    )
    assert config["calibration_corpus"]["artifact_root_sha256"] == (
        "07255ae24e1038860c22227822787c63f39e21cdde7e8f91d6829a716b8a8335"
    )
    assert config["speed_protocol"] == {
        "primary_operational_tolerance_mps": 0.1,
        "calibration_sensitivity_tolerances_mps": [0.0, 0.05, 0.1, 0.2],
        "sensitivity_source": "pilot_closed_loop_outcomes_not_snapshot_surrogate",
    }
    assert config["retraining_authorized"] is False
    assert config["solver_authorized"] is False
    assert config["holdout_execution_authorized"] is False


def test_calibration_selects_train_model_without_solver_or_retraining() -> None:
    module = _module()
    atoms, valid, physical = _arrays()

    result = module.calibrate_selector_models(
        atoms,
        valid,
        physical,
        models={"all_available_2": _model(0)},
        v18_weights=np.full(14, 1.0 / 14.0),
        v18_scales=np.ones(14),
        config=_config(),
    )

    assert result["selected_level"] == "all_available_2"
    assert result["primary_model_frozen"] is True
    assert result["model_retrained"] is False
    assert result["solver_invoked"] is False
    assert result["selected_model"]["metrics"]["oracle_agreement_count"] == 2
    assert result["selected_model"]["metrics"]["non_candidate0_selection_count"] == 2
    assert result["v18_ablation"]["ablation_only"] is True
    assert result["v18_ablation"]["primary_model"] is False
    assert result["primary_operational_tolerance_mps"] == 0.1
    assert result["holdout_executed"] is False


def test_write_freeze_outputs_materializes_runtime_assets(tmp_path: Path) -> None:
    module = _module()
    atoms, valid, physical = _arrays()
    result = module.calibrate_selector_models(
        atoms,
        valid,
        physical,
        models={"all_available_2": _model(0)},
        v18_weights=np.full(14, 1.0 / 14.0),
        v18_scales=np.ones(14),
        config=_config(),
    )

    manifest = module.write_calibration_freeze_outputs(result, tmp_path / "freeze")
    weights = np.load(tmp_path / "freeze" / "runtime" / "weights.npy")
    scales = json.loads(
        (tmp_path / "freeze" / "runtime" / "atom_scales.json").read_text()
    )

    assert weights.shape == (14,)
    assert weights.sum() == pytest.approx(1.0)
    assert scales["schema_version"] == "dp_camp_v10_14d"
    assert scales["scales"] == [1.0] * 14
    assert manifest["runtime_assets"]["weights"]["sha256"] == hashlib.sha256(
        (tmp_path / "freeze" / "runtime" / "weights.npy").read_bytes()
    ).hexdigest()
    assert manifest["pilot_execution_authorized"] is False


def test_calibration_loader_accepts_only_sealed_causal_snapshot_contract(
    tmp_path: Path,
) -> None:
    module = _module()
    artifact = _write_calibration_artifact(tmp_path / "artifact", _snapshot())
    config = _loader_config()

    corpus = module.load_calibration_corpus(artifact, config=config)

    assert corpus["atoms"].shape == (1, 8, 14)
    assert corpus["route_count"] == 1
    assert corpus["seed_count"] == 1
    assert corpus["complete_route_seed_count"] == 1
    assert corpus["retained_route_seed_count"] == 1
    assert corpus["hard_source_failure_count"] == 0
    assert corpus["all_k_high_risk_snapshot_count"] == 0


@pytest.mark.parametrize(
    ("mutation", "match"),
    (
        ("holdout", "calibration"),
        ("wrong_provenance", "provenance"),
        ("identity_feature", "feature payload"),
    ),
)
def test_calibration_loader_rejects_split_provenance_or_identity_leakage(
    tmp_path: Path, mutation: str, match: str,
) -> None:
    module = _module()
    payload = _snapshot(
        split="holdout" if mutation == "holdout" else "calibration",
        provenance=(
            "train_causal_candidate_cost_sidecar_only_not_selector_feature"
            if mutation == "wrong_provenance"
            else None
        ),
        add_identity_feature=mutation == "identity_feature",
    )
    artifact = _write_calibration_artifact(tmp_path / "artifact", payload)

    with pytest.raises(ValueError, match=match):
        module.load_calibration_corpus(artifact, config=_loader_config())
