from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.outer_master.robust_margin_master import (
    candidate_ranking_violations,
)


def _module():
    from scripts.integrations import train_diffusion_planner_v22_selector

    return train_diffusion_planner_v22_selector


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _problem() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    atoms = np.ones((2, 8, 14), dtype=np.float64)
    atoms[:, 2, :] = 0.0
    costs = np.full((2, 8), 2.0, dtype=np.float64)
    costs[:, 2] = 0.0
    source_valid = np.ones((2, 8), dtype=bool)
    scales = np.ones(14, dtype=np.float64)
    supported = np.ones(14, dtype=bool)
    supported[[7, 10, 12]] = False
    return atoms, costs, source_valid, scales, supported


def _accepted_solver(atoms, oracle, margins, feasible, *, config, features=None):
    assert features is None
    assert config.mode == "static"
    assert config.solver == "CLARABEL"
    weights = np.full(atoms.shape[2], 1.0 / atoms.shape[2], dtype=np.float64)
    _, violations, _ = candidate_ranking_violations(
        atoms, weights, oracle, margins, feasible
    )
    return SimpleNamespace(
        static_weights=weights,
        train_violations=violations,
        final_master_gap=0.0,
        history=[{"iteration": 1, "new_cuts": 0, "total_cuts": atoms.shape[0]}],
        converged=True,
        cuts_per_scene=[1] * atoms.shape[0],
        solver_status="optimal",
        solver_name="CLARABEL",
    )


def _snapshot(*, split: str = "train", add_identity_feature: bool = False) -> dict:
    atoms, _costs, source_valid, _scales, _supported = _problem()
    rows = [_sha(f"row:{index}") for index in range(8)]
    features = {
        "atom_matrix": atoms[0].tolist(),
        "source_valid_mask": source_valid[0].tolist(),
        "candidate_row_sha256": rows,
    }
    if add_identity_feature:
        features["map_id"] = "forbidden"
    return {
        "schema_version": "v22_native_decision_snapshot_v1",
        "feature_payload": features,
        "sidecar": {
            "split": split,
            "seed": 22001,
            "logical_map_sha256": _sha("map"),
            "route_identity_sha256": _sha("route"),
            "group_sha256": _sha("group"),
            "tick_index": 5,
            "physical_feasible_mask": [True] * 8,
            "candidate_tensor_sha256_before": _sha("tensor"),
            "candidate_tensor_sha256_after": _sha("tensor"),
            "default_output_sha256": rows[0],
            "candidate0_sha256": rows[0],
            "default_candidate0_identity": {"elementwise_equal": True},
        },
    }


def _write_corpus(root: Path, payload: dict) -> tuple[Path, Path]:
    snapshot_dir = root / "snapshots"
    label_root = root / "label_corpus"
    label_dir = label_root / "labels"
    snapshot_dir.mkdir(parents=True)
    label_dir.mkdir(parents=True)
    content = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode()
    digest = hashlib.sha256(content).hexdigest()
    (snapshot_dir / f"{digest}.json").write_bytes(content)
    label = {
        "schema_version": "v22_causal_soft_risk_label_v1",
        "snapshot_sha256": digest,
        "label_source": "v22_causal_soft_risk_surrogate_v1",
        "candidate_cost": [2.0, 2.0, 0.0, 2.0, 2.0, 2.0, 2.0, 2.0],
        "oracle_index": 2,
        "source_valid_mask": [True] * 8,
        "physical_feasible_mask": [True] * 8,
        "all_k_high_risk": False,
        "physical_risk_penalty": 100.0,
        "physical_risk_semantics": "finite_additive_cost_not_veto",
        "atom_scales_sha256": hashlib.sha256(
            (json.dumps([1.0] * 14, separators=(",", ":")) + "\n").encode()
        ).hexdigest(),
        "actual_closed_loop_outcome": False,
    }
    label_content = (
        json.dumps(label, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode()
    (label_dir / f"{digest}.json").write_bytes(label_content)
    supported = [True] * 14
    for index in (7, 10, 12):
        supported[index] = False
    manifest = {
        "schema_version": "v22_causal_soft_risk_label_manifest_v1",
        "status": "complete",
        "snapshot_count": 1,
        "source_artifact_root_sha256": _sha("source-artifact"),
        "atom_scales": [1.0] * 14,
        "atom_scales_sha256": label["atom_scales_sha256"],
        "supported_atom_mask": supported,
        "label_file_sha256": [hashlib.sha256(label_content).hexdigest()],
        "actual_closed_loop_outcomes_read": False,
        "future_outcome_fields_read": False,
        "identity_fields_used_as_label_or_feature": False,
        "calibration_executed": False,
        "holdout_executed": False,
        "holdout_outcomes_read": False,
        "model_trained": False,
        "simulator_executed": False,
        "claim_authorized": False,
    }
    (label_root / "label_manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return snapshot_dir, label_root


def _config() -> dict:
    return {
        "schema_version": "camp_dp_v22_training_v1",
        "source_corpus": {"artifact_root_sha256": _sha("source-artifact")},
        "execution_split": "train",
        "learning_curve_levels": [5000, 10000, 20000, 50000],
        "run_all_available_snapshots": True,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "calibration_execution_authorized": False,
        "holdout_execution_authorized": False,
        "claim_authorized": False,
        "label_contract": {
            "schema_version": "v22_causal_soft_risk_surrogate_v1",
            "normalized_atom_clip": 10.0,
            "oracle_eligibility": "source_valid_mask_only",
            "physical_risk_semantics": "finite_additive_cost_not_veto",
            "actual_closed_loop_outcome": False,
        },
    }


def test_lower_cost_becomes_oracle_after_sign_conversion() -> None:
    module = _module()
    atoms, costs, source_valid, scales, supported = _problem()

    problem = module.prepare_training_problem(
        atoms,
        costs,
        source_valid,
        scales=scales,
        supported_atom_mask=supported,
        normalized_atom_clip=10.0,
    )

    assert problem["oracle_indices"].tolist() == [2, 2]
    assert problem["normalized_atoms"].shape == (2, 8, 11)


def test_train_level_expands_unsupported_weights_and_reports_solver_receipt() -> None:
    module = _module()
    atoms, costs, source_valid, scales, supported = _problem()

    model = module.train_selector_level(
        atoms,
        costs,
        source_valid,
        scales=scales,
        supported_atom_mask=supported,
        snapshot_sha256=[_sha("b"), _sha("a")],
        level_name="all_available_2",
        normalized_atom_clip=10.0,
        solver=_accepted_solver,
    )

    weights = np.asarray(model["weights"], dtype=np.float64)
    assert np.isfinite(weights).all()
    assert np.all(weights >= 0.0)
    assert weights.sum() == pytest.approx(1.0)
    assert weights[[7, 10, 12]].tolist() == [0.0, 0.0, 0.0]
    assert model["snapshot_sha256"] == sorted([_sha("b"), _sha("a")])
    assert model["train_metrics"]["oracle_agreement_count"] == 2
    assert model["solver"] == {
        **model["solver"],
        "name": "CLARABEL",
        "status": "optimal",
        "iterations": 1,
        "final_master_gap": 0.0,
        "total_cuts": 2,
        "converged": True,
    }
    assert model["solver"]["offline_wall_clock_s"] >= 0.0
    assert model["actual_closed_loop_outcome"] is False
    assert model["atom_transform"] == "clip(raw_atom/scale,0,10.0)"


def test_sub_5k_corpus_runs_only_honest_all_available_level(tmp_path: Path) -> None:
    module = _module()
    snapshot_dir, label_root = _write_corpus(tmp_path, _snapshot())

    result = module.train_learning_curve(
        snapshot_dir=snapshot_dir,
        label_corpus_dir=label_root,
        config=_config(),
        solver=_accepted_solver,
    )

    assert list(result["models"]) == ["all_available_1"]
    assert result["reachable_preregistered_levels"] == []
    assert result["unreachable_preregistered_levels"] == [5000, 10000, 20000, 50000]
    assert result["primary_model_frozen"] is False
    assert result["calibration_executed"] is False
    assert result["holdout_executed"] is False


def test_v18_weights_are_reported_only_as_ablation() -> None:
    module = _module()
    atoms, costs, source_valid, _scales, _supported = _problem()
    weights = np.full(14, 1.0 / 14.0, dtype=np.float64)

    result = module.evaluate_v18_ablation(
        atoms,
        costs,
        source_valid,
        weights=weights,
        scales=np.ones(14, dtype=np.float64),
    )

    assert result["name"] == "v18_frozen_corrected14d"
    assert result["ablation_only"] is True
    assert result["primary_model"] is False
    assert result["oracle_agreement_count"] == 2
    assert result["actual_closed_loop_outcome"] is False


def test_label_source_root_mismatch_fails_before_solver(tmp_path: Path) -> None:
    module = _module()
    snapshot_dir, label_root = _write_corpus(tmp_path, _snapshot())
    manifest_path = label_root / "label_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_artifact_root_sha256"] = _sha("wrong-source")
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    called = False

    def forbidden_solver(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("solver must not run")

    with pytest.raises(ValueError, match="source artifact root"):
        module.train_learning_curve(
            snapshot_dir=snapshot_dir,
            label_corpus_dir=label_root,
            config=_config(),
            solver=forbidden_solver,
        )

    assert called is False


@pytest.mark.parametrize("mutation", ("holdout", "identity_feature"))
def test_forbidden_split_or_identity_fails_before_solver(
    tmp_path: Path, mutation: str
) -> None:
    module = _module()
    payload = _snapshot(
        split="holdout" if mutation == "holdout" else "train",
        add_identity_feature=mutation == "identity_feature",
    )
    snapshot_dir, label_root = _write_corpus(tmp_path, payload)
    called = False

    def forbidden_solver(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("solver must not run")

    with pytest.raises(ValueError, match="train|feature payload"):
        module.train_learning_curve(
            snapshot_dir=snapshot_dir,
            label_corpus_dir=label_root,
            config=_config(),
            solver=forbidden_solver,
        )

    assert called is False
