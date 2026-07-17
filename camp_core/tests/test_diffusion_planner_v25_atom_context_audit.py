from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_atoms import (
    CANONICAL_ATOM_CONTRACTS,
)
from scripts.integrations.audit_diffusion_planner_v25_atoms_context import (
    EXPECTED_ATOMS,
    compute_atom_audit,
    validate_config,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG = (
    ROOT
    / "configs"
    / "integrations"
    / "diffusion_planner_v25_atom_context_freeze.json"
)


def _config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_v25_atom_context_freeze_is_exact_and_causal() -> None:
    config = validate_config(_config())
    atoms = config["atom_contract"]
    context = config["causal_context_contract"]
    assert tuple(atoms["atom_names"]) == EXPECTED_ATOMS
    assert atoms["paper_consistent_9d_subset_indices"] == list(range(9))
    assert atoms["dp_extension_indices"] == list(range(9, 14))
    assert config["corpus_contract"]["snapshot_schema_version"] == (
        "v22_native_decision_snapshot_v1"
    )
    assert context["phi_dimension"] == 53
    assert context["theta_constraint"] == (
        "every_theta_column_nonnegative_simplex"
    )
    assert context["softmax_allowed"] is False
    assert context["private_dp_latent_allowed"] is False


def test_v25_context_freeze_rejects_identity_and_outcome_features() -> None:
    for forbidden in ("route_identity_sha256", "closed_loop_outcome_cost"):
        config = copy.deepcopy(_config())
        config["causal_context_contract"]["raw_features"][0]["name"] = forbidden
        with pytest.raises(ValueError, match="forbidden"):
            validate_config(config)


def test_candidate0_contract_uses_operational_default_not_native_rank_language() -> None:
    contract = next(
        item
        for item in CANONICAL_ATOM_CONTRACTS
        if item.name == "dp_prior_jerk_excess_cost"
    )
    text = " ".join(
        (
            *contract.inputs,
            contract.decision_time_availability,
            contract.nuscenes_availability,
            contract.candidate_index_dependency,
        )
    )
    assert "operational-default" in text
    assert "native-ranked Top-1 is not claimed" in text
    assert "DP Top-1 semantic" not in text


def test_v25_atom_audit_reports_variation_redundancy_and_train_label_alignment() -> None:
    config = validate_config(_config())
    snapshots = 12
    base = np.linspace(0.0, 1.0, 8, dtype=np.float64)
    atoms = np.empty((snapshots, 8, 14), dtype=np.float64)
    for snapshot in range(snapshots):
        for atom in range(14):
            atoms[snapshot, :, atom] = (
                base * (atom + 1) + 0.01 * snapshot + 0.001 * atom
            )
    atoms[:, :, 2] = 2.0 * atoms[:, :, 1]
    scales = np.quantile(atoms.reshape(-1, 14), 0.95, axis=0)
    valid = np.ones((snapshots, 8), dtype=bool)
    severity = np.asarray(
        config["train_only_label_contract"]["atom_severity_weights"],
        dtype=np.float64,
    )
    costs = np.sum(
        np.clip(atoms / scales.reshape(1, 1, 14), 0.0, 10.0)
        * severity.reshape(1, 1, 14),
        axis=2,
    )
    oracle = np.argmin(costs, axis=1)
    route_groups = [f"route-{index // 4}" for index in range(snapshots)]
    strata = {
        "traffic_light": np.asarray([index % 2 == 0 for index in range(snapshots)]),
        "tight_corridor": np.asarray([index % 3 == 0 for index in range(snapshots)]),
    }
    result = compute_atom_audit(
        atoms=atoms,
        costs=costs,
        oracle=oracle,
        source_valid=valid,
        scales=scales,
        route_groups=route_groups,
        source_strata=strata,
        config=config,
    )
    assert result["snapshot_count"] == snapshots
    assert result["candidate_count"] == snapshots * 8
    assert result["route_group_count"] == 3
    assert len(result["atom_rows"]) == 14
    assert result["atom_rows"][0]["candidate_variable_snapshot_rate"] == 1.0
    assert result["atom_rows"][0]["spearman_with_causal_cost"] > 0.99
    assert any(
        {pair["left"], pair["right"]} == {"jerk_late", "jerk_full"}
        for pair in result["redundant_pairs"]
    )


def test_v25_atom_audit_rejects_nonfinite_or_negative_atoms() -> None:
    config = validate_config(_config())
    atoms = np.ones((2, 8, 14), dtype=np.float64)
    costs = np.ones((2, 8), dtype=np.float64)
    valid = np.ones((2, 8), dtype=bool)
    common = dict(
        costs=costs,
        oracle=np.zeros(2, dtype=np.uint8),
        source_valid=valid,
        scales=np.ones(14, dtype=np.float64),
        route_groups=["a", "b"],
        source_strata={"traffic_light": np.ones(2, dtype=bool)},
        config=config,
    )
    atoms[0, 0, 0] = -1.0
    with pytest.raises(ValueError, match="invalid"):
        compute_atom_audit(atoms=atoms, **common)
    atoms[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="invalid"):
        compute_atom_audit(atoms=atoms, **common)
