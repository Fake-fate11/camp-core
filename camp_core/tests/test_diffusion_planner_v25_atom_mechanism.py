from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_atoms import canonical_normalize_atoms
from camp_core.integrations.diffusion_planner_v25_atom_mechanism import (
    BINDING_SCHEMA_VERSION,
    GROUPS,
    analyze_atom_mechanisms,
    mechanism_names,
    validate_atom_mechanism_binding,
    validate_atom_mechanism_contract,
)
from camp_core.integrations.diffusion_planner_v25_context import (
    CONTEXT_SCHEMA_VERSION,
    PHI_DIMENSION,
    RAW_FEATURE_NAMES,
    V25ContextScaler,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (
    MODEL_PARAMETER_SCHEMA_VERSION,
    V25Scene14DWeightProvider,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "configs" / "integrations" / "diffusion_planner_v25_atom_mechanism_v1.json"


def _context() -> dict:
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


def _training(path: Path) -> None:
    static9 = np.zeros(9, dtype=np.float64)
    static9[1] = 1.0
    scene9 = np.zeros((9, PHI_DIMENSION), dtype=np.float64)
    scene9[1, :] = 1.0
    np.savez(
        path / "model_parameters.npz",
        schema_version=np.asarray(MODEL_PARAMETER_SCHEMA_VERSION),
        context_q05=np.zeros(len(RAW_FEATURE_NAMES), dtype=np.float64),
        context_q95=np.ones(len(RAW_FEATURE_NAMES), dtype=np.float64),
        static9d_runtime_weights=static9,
        scene9d_theta=scene9,
    )


def _provider(path: Path, weights: np.ndarray) -> V25Scene14DWeightProvider:
    theta = np.repeat(weights[:, None], PHI_DIMENSION, axis=1)
    return V25Scene14DWeightProvider(
        theta=theta,
        context_scaler=V25ContextScaler(
            q05=np.zeros(len(RAW_FEATURE_NAMES), dtype=np.float64),
            q95=np.ones(len(RAW_FEATURE_NAMES), dtype=np.float64),
        ),
        training_artifact=str(path),
        training_root_sha256="1" * 64,
        training_review_artifact=str(path / "review"),
        training_review_root_sha256="2" * 64,
        theta_sha256="3" * 64,
        context_scaler_sha256="4" * 64,
    )


def _run(arm: str, provider: V25Scene14DWeightProvider, weights: np.ndarray) -> dict:
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    candidates[..., 2] = 1.0
    atoms = np.full((8, 14), 10.0, dtype=np.float64)
    atoms[0] = 0.0
    atoms[0, 1] = 1.0
    atoms[1] = 0.0
    atoms[1, 0] = 10.0
    context = _context()
    scene = provider(context)
    official_weights = (
        np.asarray(scene["weights"], dtype=np.float64)
        if arm == "camp_scene14d_no_v2i"
        else weights
    )
    scores = (
        canonical_normalize_atoms(atoms, np.ones(14, dtype=np.float64))
        @ official_weights
    )
    assert int(np.argmin(scores)) == 0
    selector = {key: value for key, value in scene.items() if key != "weights"}
    snapshots = []
    native_ticks = []
    for tick_index in range(64):
        snapshots.append(
            {
                "schema_version": "v22_native_decision_snapshot_v1",
                "feature_payload": {
                    "candidate_tensor": candidates.tolist(),
                    "atom_matrix": atoms.tolist(),
                    "atom_source_valid_mask": np.ones((8, 14), dtype=bool).tolist(),
                    "atom_applicable_mask": np.ones((8, 14), dtype=bool).tolist(),
                    "source_valid_mask": [True] * 8,
                },
                "sidecar": {
                    "tick_index": tick_index,
                    "scores": scores.tolist(),
                    "selected_index": 0,
                    "source_valid_mask": [True] * 8,
                    "score_contract": "score_k=clip(a_k/s,0,10)^T w",
                    "tie_break_contract": "lowest_eligible_candidate_index",
                },
            }
        )
        native_ticks.append(
            {
                "tick_index": tick_index,
                "scores": scores.tolist(),
                "selected_index": 0,
                "source_valid_mask": [True] * 8,
                "all_k_high_risk": False,
                "v25_context": context,
                "v25_scene_selector": selector if arm == "camp_scene14d_no_v2i" else None,
            }
        )
    return {
        "plan_arm": arm,
        "unit_ordinal": 0,
        "corridor_sha256": "a" * 64,
        "scenario_family": "red_light_phase_timing",
        "risk_tier": "borderline",
        "signal_source_class": "mapped_signal",
        "phase_authority_mode": "controlled_same_tick_override",
        "snapshots": snapshots,
        "native_ticks": native_ticks,
    }


def _outcome(arm: str) -> dict:
    return {
        "plan_arm": arm,
        "corridor_sha256": "a" * 64,
        "safety_cost": 1.0 if arm == "candidate0_operational_default" else 0.9,
        "components": {
            "collision": 0.0,
            "near_miss": 0.1,
            "offroad": 0.0,
            "red_light": 0.0,
            "speed": 0.0,
            "wrong_way": 0.0,
        },
        "performance": {
            "progress": 10.0,
            "completion": 1.0,
            "mean_jerk": 0.2,
            "max_jerk": 0.3,
            "mean_lateral_acceleration": 0.1,
            "max_lateral_acceleration": 0.2,
        },
    }


def test_contract_freezes_groups_nonrenormalized_removal_and_no_causal_claim() -> None:
    value = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert validate_atom_mechanism_contract(value) == value
    assert set(index for indices in GROUPS.values() for index in indices) == set(range(14))
    assert value["runtime_projection_or_renormalization_used"] is False
    assert value["single_atom_closed_loop_causal_effect_claimed"] is False
    mutated = copy.deepcopy(value)
    mutated["runtime_projection_or_renormalization_used"] = True
    with pytest.raises(ValueError, match="value drifted"):
        validate_atom_mechanism_contract(mutated)


def test_preopen_binding_is_exact_capacity_passed_and_fresh_closed(tmp_path: Path) -> None:
    artifact = (tmp_path / "mechanism").resolve()
    review = (tmp_path / "mechanism-review").resolve()
    value = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "status": "passed_independent_atom_mechanism_preopen_review",
        "artifact_path": str(artifact),
        "artifact_root_sha256": "1" * 64,
        "review_artifact_path": str(review),
        "review_root_sha256": "2" * 64,
        "contract_sha256": "3" * 64,
        "analysis_sha256": "4" * 64,
        "decision_tick_count": 12_800,
        "mechanism_names": mechanism_names(),
        "raw_k8_payload_copied": False,
        "primary_fresh_design_changed": False,
        "model_or_weight_changed": False,
        "single_atom_closed_loop_causal_effect_claimed": False,
        "fresh_storage_capacity_gate_passed": True,
        "storage_projected_1500_arm_upper_bound_nbytes_with_mechanism": 70_000_000_000,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    assert validate_atom_mechanism_binding(value) == value
    for field, replacement in (
        ("fresh_storage_capacity_gate_passed", False),
        ("raw_k8_payload_copied", True),
        ("fresh_b2_opened", True),
        ("decision_tick_count", 12_800.0),
    ):
        mutated = copy.deepcopy(value)
        mutated[field] = replacement
        with pytest.raises(ValueError, match="binding value drifted"):
            validate_atom_mechanism_binding(mutated)


def test_same_pool_mechanism_reports_9d_leave_one_groups_flips_and_association(tmp_path: Path) -> None:
    _training(tmp_path)
    weights = np.zeros(14, dtype=np.float64)
    weights[0] = 0.2
    weights[1] = 0.8
    provider = _provider(tmp_path, weights)
    report = analyze_atom_mechanisms(
        decision_runs=[
            _run("camp_static14d", provider, weights),
            _run("camp_scene14d_no_v2i", provider, weights),
        ],
        outcomes_by_unit={
            0: {
                arm: _outcome(arm)
                for arm in (
                    "candidate0_operational_default",
                    "camp_static14d",
                    "camp_scene14d_no_v2i",
                )
            }
        },
        atom_scales=np.ones(14, dtype=np.float64),
        static14d_weights=weights,
        scene14d_provider=provider,
        training_artifact=tmp_path,
    )
    static = report["arm_reports"]["camp_static14d"]
    assert static["mechanisms"]["atom:jerk_early"]["selected_flip_rate"] == 1.0
    assert static["mechanisms"]["group:jerk_full_early_late"]["selected_flip_rate"] == 1.0
    assert static["mechanisms"]["paper_9d_vs_14d"]["selected_flip_rate"] == 1.0
    assert report["runtime_projection_or_renormalization_used"] is False
    assert report["counterfactual_closed_loop_executed"] is False
    association = report["corridor_cluster_associations"]["camp_static14d"]["atom:jerk_early"]["selected_flip_rate"]["safety_cost_total"]
    assert association == {
        "corridor_cluster_count": 1,
        "spearman_rho": None,
        "status": "insufficient_cluster_variation",
    }


def test_empty_eligibility_and_outcome_pair_drift_fail_closed(tmp_path: Path) -> None:
    _training(tmp_path)
    weights = np.zeros(14, dtype=np.float64)
    weights[0] = 0.2
    weights[1] = 0.8
    provider = _provider(tmp_path, weights)
    runs = [
        _run("camp_static14d", provider, weights),
        _run("camp_scene14d_no_v2i", provider, weights),
    ]
    runs[0]["snapshots"][0]["feature_payload"]["source_valid_mask"] = [False] * 8
    with pytest.raises(ValueError, match="eligibility is empty|source/applicability"):
        analyze_atom_mechanisms(
            decision_runs=runs,
            outcomes_by_unit={0: {"candidate0_operational_default": _outcome("candidate0_operational_default")}},
            atom_scales=np.ones(14),
            static14d_weights=weights,
            scene14d_provider=provider,
            training_artifact=tmp_path,
        )
