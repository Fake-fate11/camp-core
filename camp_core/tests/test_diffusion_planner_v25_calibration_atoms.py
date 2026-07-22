from __future__ import annotations

from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_causal_atoms import (
    canonical_normalize_atoms,
)
from camp_core.integrations.diffusion_planner_v25_calibration_atoms import (
    analyze_calibration_decision_evidence,
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


def _training_artifact(path: Path) -> None:
    np.savez(
        path / "model_parameters.npz",
        schema_version=np.asarray(MODEL_PARAMETER_SCHEMA_VERSION),
        context_q05=np.zeros(len(RAW_FEATURE_NAMES), dtype=np.float64),
        context_q95=np.ones(len(RAW_FEATURE_NAMES), dtype=np.float64),
        static9d_runtime_weights=np.full(9, 1.0 / 9.0, dtype=np.float64),
        scene9d_theta=np.full(
            (9, PHI_DIMENSION), 1.0 / 9.0, dtype=np.float64
        ),
    )


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


def _run(plan_arm: str, provider: V25Scene14DWeightProvider) -> dict:
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    candidates[..., 2] = 1.0
    atoms = np.arange(8 * 14, dtype=np.float64).reshape(8, 14) / 100.0
    context = _context()
    scene = provider(context)
    weights = (
        np.asarray(scene["weights"], dtype=np.float64)
        if plan_arm == "camp_scene14d_no_v2i"
        else np.full(14, 1.0 / 14.0, dtype=np.float64)
    )
    scores = canonical_normalize_atoms(
        atoms, np.ones(14, dtype=np.float64)
    ) @ weights
    selector = {key: value for key, value in scene.items() if key != "weights"}
    snapshots = []
    native = []
    for tick_index in range(64):
        snapshot = {
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
        tick = {
            "tick_index": tick_index,
            "scores": scores.tolist(),
            "selected_index": 0,
            "source_valid_mask": [True] * 8,
            "v25_context": context,
            "v25_scene_selector": (
                selector if plan_arm == "camp_scene14d_no_v2i" else None
            ),
        }
        snapshots.append(snapshot)
        native.append(tick)
    return {
        "plan_arm": plan_arm,
        "snapshots": snapshots,
        "native_ticks": native,
        "scenario_family": "red_light_phase_timing",
        "risk_tier": "borderline",
        "signal_source_class": "mapped_signal",
    }


def test_atom_calibration_recomputes_scores_ablations_and_event_support(
    tmp_path: Path,
) -> None:
    _training_artifact(tmp_path)
    theta = np.full((14, PHI_DIMENSION), 1.0 / 14.0, dtype=np.float64)
    provider = V25Scene14DWeightProvider(
        theta=theta,
        context_scaler=V25ContextScaler(
            q05=np.zeros(len(RAW_FEATURE_NAMES), dtype=np.float64),
            q95=np.ones(len(RAW_FEATURE_NAMES), dtype=np.float64),
        ),
        training_artifact=str(tmp_path),
        training_root_sha256="1" * 64,
        training_review_artifact=str(tmp_path / "review"),
        training_review_root_sha256="2" * 64,
        theta_sha256="3" * 64,
        context_scaler_sha256="4" * 64,
    )
    report = analyze_calibration_decision_evidence(
        camp_runs=[
            _run("camp_static14d", provider),
            _run("camp_scene14d_no_v2i", provider),
        ],
        atom_scales=np.ones(14, dtype=np.float64),
        static14d_weights=np.full(14, 1.0 / 14.0, dtype=np.float64),
        scene14d_provider=provider,
        training_artifact=tmp_path,
    )
    assert report["atom_count"] == 14
    assert report["decision_tick_count"] == 128
    assert report["decision_tick_count_by_arm"] == {
        "camp_scene14d_no_v2i": 64,
        "camp_static14d": 64,
    }
    assert report["event_family_support"]["red_light_phase_timing"][
        "decision_tick_count"
    ] == 128
    assert all(row["scale_changed_by_calibration"] is False for row in report["atoms"])
    assert report["producer_layout_frozen_for_formal_selection"] is True
    assert report["fresh_b2_opened"] is False
