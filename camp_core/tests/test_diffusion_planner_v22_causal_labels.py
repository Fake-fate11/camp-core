import hashlib
import json
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "integrations" / "diffusion_planner_v22_training.json"


def _module():
    from scripts.integrations import materialize_diffusion_planner_v22_labels

    return materialize_diffusion_planner_v22_labels


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _snapshot(*, split: str = "train", seed: int = 22001) -> dict:
    atoms = np.zeros((8, 14), dtype=np.float64)
    atoms[:, 2] = np.arange(8, dtype=np.float64)
    atoms[:, 8] = np.arange(8, 0, -1, dtype=np.float64)
    rows = [_sha(f"row:{index}") for index in range(8)]
    return {
        "schema_version": "v22_native_decision_snapshot_v1",
        "feature_payload": {
            "atom_matrix": atoms.tolist(),
            "source_valid_mask": [True] * 8,
            "candidate_row_sha256": rows,
        },
        "sidecar": {
            "tick_index": 5,
            "default_output_sha256": rows[0],
            "candidate0_sha256": rows[0],
            "default_candidate0_identity": {
                "elementwise_equal": True,
                "max_abs_difference": 0.0,
                "default_output_sha256": rows[0],
                "candidate0_sha256": rows[0],
                "native_ranked_k8": False,
            },
            "candidate_tensor_sha256_before": _sha("tensor"),
            "candidate_tensor_sha256_after": _sha("tensor"),
            "causal_input_sha256": _sha("causal"),
            "physical_feasible_mask": [False] * 8,
            "all_k_high_risk": True,
            "offline_label_provenance": (
                "pending_train_only_offline_supervision_sidecar"
            ),
            "split": split,
            "seed": seed,
        },
    }


def _write_snapshot(directory: Path, payload: dict) -> str:
    content = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode()
    digest = hashlib.sha256(content).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{digest}.json").write_bytes(content)
    return digest


def _config() -> dict:
    return {
        "schema_version": "camp_dp_v22_training_v1",
        "label_contract": {
            "schema_version": "v22_causal_soft_risk_surrogate_v1",
            "physical_risk_penalty": 100.0,
            "scale_percentile": 95.0,
            "scale_floor": 1e-6,
            "normalized_atom_clip": 10.0,
            "atom_severity_weights": [
                0.0,
                0.0,
                0.25,
                0.25,
                10.0,
                0.0,
                0.0,
                20.0,
                10.0,
                1.0,
                15.0,
                1.0,
                15.0,
                0.25,
            ],
            "oracle_eligibility": "source_valid_mask_only",
            "physical_risk_semantics": "finite_additive_cost_not_veto",
            "actual_closed_loop_outcome": False,
        },
        "execution_split": "train",
        "formal_seeds_authorized": False,
        "calibration_execution_authorized": False,
        "holdout_execution_authorized": False,
        "claim_authorized": False,
    }


def test_tracked_label_contract_is_train_only_and_not_an_outcome_claim() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    contract = config["label_contract"]

    assert config["execution_split"] == "train"
    assert contract["oracle_eligibility"] == "source_valid_mask_only"
    assert contract["physical_risk_semantics"] == "finite_additive_cost_not_veto"
    assert contract["actual_closed_loop_outcome"] is False
    assert contract["physical_risk_penalty"] == 100.0
    assert len(contract["atom_severity_weights"]) == 14
    assert config["calibration_execution_authorized"] is False
    assert config["holdout_execution_authorized"] is False
    assert config["claim_authorized"] is False


def test_all_k_high_risk_keeps_finite_costs_and_chooses_relative_minimum() -> None:
    module = _module()
    atoms = np.zeros((1, 8, 14), dtype=np.float64)
    atoms[0, :, 8] = np.arange(8, dtype=np.float64)
    physical = np.zeros((1, 8), dtype=bool)
    valid = np.ones((1, 8), dtype=bool)
    scales = np.ones(14, dtype=np.float64)
    weights = np.zeros(14, dtype=np.float64)
    weights[8] = 10.0

    costs, oracle = module.causal_soft_risk_labels(
        atoms,
        source_valid=valid,
        physical_feasible=physical,
        scales=scales,
        atom_severity_weights=weights,
        physical_risk_penalty=100.0,
        normalized_atom_clip=10.0,
    )

    assert np.isfinite(costs).all()
    np.testing.assert_allclose(costs[0], 100.0 + 10.0 * np.arange(8))
    assert oracle.tolist() == [0]


def test_label_materialization_is_content_linked_and_identity_free(
    tmp_path: Path,
) -> None:
    module = _module()
    snapshot_dir = tmp_path / "snapshots"
    digest = _write_snapshot(snapshot_dir, _snapshot())

    summary = module.materialize_train_labels(
        snapshot_dir=snapshot_dir,
        output_dir=tmp_path / "labels",
        config=_config(),
        source_artifact_root_sha256=_sha("source-artifact"),
    )

    assert summary["status"] == "complete"
    assert summary["snapshot_count"] == 1
    assert summary["all_k_high_risk_count"] == 1
    assert summary["actual_closed_loop_outcomes_read"] is False
    label = json.loads((tmp_path / "labels" / "labels" / f"{digest}.json").read_text())
    assert label["snapshot_sha256"] == digest
    assert len(label["candidate_cost"]) == 8
    assert label["oracle_index"] in range(8)
    assert label["physical_risk_semantics"] == "finite_additive_cost_not_veto"
    assert not set(label).intersection(
        {"logical_map_sha256", "route_identity_sha256", "group_sha256", "seed"}
    )


@pytest.mark.parametrize("mutation", ("holdout", "formal_seed", "hash"))
def test_label_materialization_rejects_forbidden_split_seed_or_hash(
    tmp_path: Path, mutation: str
) -> None:
    module = _module()
    snapshot_dir = tmp_path / "snapshots"
    payload = _snapshot(
        split="holdout" if mutation == "holdout" else "train",
        seed=11 if mutation == "formal_seed" else 22001,
    )
    digest = _write_snapshot(snapshot_dir, payload)
    if mutation == "hash":
        (snapshot_dir / f"{digest}.json").rename(snapshot_dir / f"{_sha('bad')}.json")

    with pytest.raises(ValueError, match="train|formal|content SHA"):
        module.materialize_train_labels(
            snapshot_dir=snapshot_dir,
            output_dir=tmp_path / "labels",
            config=_config(),
            source_artifact_root_sha256=_sha("source-artifact"),
        )
