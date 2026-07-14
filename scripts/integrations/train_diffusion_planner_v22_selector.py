#!/usr/bin/env python3
"""Train v22 static affine selectors from sealed train-only causal labels."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    DP_CAMP_ATOM_NAMES_V10,
)
from camp_core.outer_master.robust_margin_master import (  # noqa: E402
    RobustMarginConfig,
    candidate_ranking_violations,
    outcome_oracle_and_margins,
    project_simplex_rows,
    solve_robust_margin_cutting_plane,
)


FORMAL_SEEDS = frozenset({11, 12, 13})
FEATURE_FIELDS = frozenset(
    {"atom_matrix", "source_valid_mask", "candidate_row_sha256"}
)
IDENTITY_FIELDS = frozenset(
    {
        "logical_map_sha256",
        "map_id",
        "route_id",
        "route_identity_sha256",
        "route_sha256",
        "group_sha256",
        "split",
        "seed",
    }
)
LABEL_FIELDS = frozenset(
    {
        "schema_version",
        "snapshot_sha256",
        "label_source",
        "candidate_cost",
        "oracle_index",
        "source_valid_mask",
        "physical_feasible_mask",
        "all_k_high_risk",
        "physical_risk_penalty",
        "physical_risk_semantics",
        "atom_scales_sha256",
        "actual_closed_loop_outcome",
    }
)

MARGIN_SCALE = 0.1
MARGIN_CLIP = 2.0
CVAR_ALPHA = 0.9
L2_REG = 1e-4
MAX_ITER = 20
TOLERANCE = 1e-6
SOLVER = "CLARABEL"
CLARABEL_SOLVER_OPTIONS = (
    ("tol_gap_abs", 1e-10),
    ("tol_gap_rel", 1e-10),
    ("tol_feas", 1e-10),
)


def prepare_training_problem(
    atoms: np.ndarray,
    candidate_cost: np.ndarray,
    source_valid: np.ndarray,
    *,
    scales: np.ndarray,
    supported_atom_mask: np.ndarray,
    normalized_atom_clip: float,
    margin_scale: float = MARGIN_SCALE,
    margin_clip: float = MARGIN_CLIP,
) -> dict[str, np.ndarray]:
    matrix = np.asarray(atoms, dtype=np.float64)
    costs = np.asarray(candidate_cost, dtype=np.float64)
    valid = np.asarray(source_valid, dtype=bool)
    scale = np.asarray(scales, dtype=np.float64).reshape(-1)
    supported = np.asarray(supported_atom_mask, dtype=bool).reshape(-1)
    if matrix.ndim != 3 or matrix.shape[1:] != (8, 14):
        raise ValueError("atoms must have shape [N,8,14]")
    if costs.shape != matrix.shape[:2] or valid.shape != matrix.shape[:2]:
        raise ValueError("candidate costs and source-valid mask must have shape [N,8]")
    if scale.shape != (14,) or supported.shape != (14,) or not supported.any():
        raise ValueError("scales and supported atom mask must contain 14 values")
    if (
        not np.isfinite(matrix).all()
        or np.any(matrix < 0.0)
        or not np.isfinite(costs).all()
        or np.any(costs < 0.0)
        or not np.isfinite(scale).all()
        or np.any(scale <= 0.0)
        or not valid.any(axis=1).all()
        or not np.isfinite(normalized_atom_clip)
        or normalized_atom_clip <= 0.0
    ):
        raise ValueError("training atoms, costs, masks, scales, and clip are invalid")

    normalized = np.clip(
        matrix / scale.reshape(1, 1, -1),
        0.0,
        float(normalized_atom_clip),
    )[:, :, supported]
    oracle, margins = outcome_oracle_and_margins(
        -costs,
        valid,
        margin_scale=float(margin_scale),
        margin_clip=float(margin_clip),
    )
    return {
        "normalized_atoms": normalized,
        "oracle_indices": oracle,
        "margins": margins,
        "source_valid_mask": valid,
    }


def train_selector_level(
    atoms: np.ndarray,
    candidate_cost: np.ndarray,
    source_valid: np.ndarray,
    *,
    scales: np.ndarray,
    supported_atom_mask: np.ndarray,
    snapshot_sha256: list[str],
    level_name: str,
    normalized_atom_clip: float,
    solver: Callable[..., Any] = solve_robust_margin_cutting_plane,
) -> dict[str, Any]:
    digests = list(snapshot_sha256)
    if len(digests) != np.asarray(atoms).shape[0] or any(
        not _is_sha256(value) for value in digests
    ):
        raise ValueError("snapshot SHA list must match the training rows")
    order = np.argsort(np.asarray(digests), kind="stable")
    matrix = np.asarray(atoms, dtype=np.float64)[order]
    costs = np.asarray(candidate_cost, dtype=np.float64)[order]
    valid = np.asarray(source_valid, dtype=bool)[order]
    digests = [digests[int(index)] for index in order]
    supported = np.asarray(supported_atom_mask, dtype=bool).reshape(-1)
    problem = prepare_training_problem(
        matrix,
        costs,
        valid,
        scales=scales,
        supported_atom_mask=supported,
        normalized_atom_clip=normalized_atom_clip,
    )
    config = RobustMarginConfig(
        mode="static",
        risk_type="cvar",
        alpha=CVAR_ALPHA,
        l2_reg=L2_REG,
        max_iter=MAX_ITER,
        tolerance=TOLERANCE,
        solver=SOLVER,
        static_weight_lower_bounds=tuple(
            np.zeros(int(supported.sum()), dtype=np.float64).tolist()
        ),
        solver_options=CLARABEL_SOLVER_OPTIONS,
    )
    started = time.perf_counter()
    result = solver(
        problem["normalized_atoms"],
        problem["oracle_indices"],
        problem["margins"],
        problem["source_valid_mask"],
        config=config,
        features=None,
    )
    wall_clock = time.perf_counter() - started
    supported_weights, violations, projected_gap = _accepted_weights(
        result,
        problem["normalized_atoms"],
        problem["oracle_indices"],
        problem["margins"],
        problem["source_valid_mask"],
    )
    weights = np.zeros(14, dtype=np.float64)
    weights[supported] = supported_weights
    scores = np.einsum(
        "nkr,r->nk", problem["normalized_atoms"], supported_weights
    )
    selected = np.argmin(
        np.where(problem["source_valid_mask"], scores, np.inf), axis=1
    )
    row = np.arange(selected.size)
    oracle = problem["oracle_indices"]
    selected_cost = costs[row, selected]
    default_cost = costs[:, 0]
    history = list(result.history)
    return {
        "schema_version": "v22_static_affine_selector_model_v1",
        "level_name": str(level_name),
        "training_source": "v22_train_snapshots_only",
        "snapshot_count": len(digests),
        "snapshot_sha256": digests,
        "atom_schema_version": "dp_camp_v10_14d",
        "atom_names": list(DP_CAMP_ATOM_NAMES_V10),
        "atom_scales": np.asarray(scales, dtype=np.float64).tolist(),
        "supported_atom_mask": supported.tolist(),
        "weights": weights.tolist(),
        "normalized_atom_clip": float(normalized_atom_clip),
        "atom_transform": (
            f"clip(raw_atom/scale,0,{float(normalized_atom_clip)})"
        ),
        "score_contract": "score_k(w)=a_k^T w",
        "oracle_eligibility": "source_valid_mask_only",
        "unsupported_atoms_receive_zero_weight": True,
        "train_metrics": {
            "oracle_agreement_count": int(np.sum(selected == oracle)),
            "oracle_agreement_rate": float(np.mean(selected == oracle)),
            "candidate0_selection_count": int(np.sum(selected == 0)),
            "non_candidate0_selection_count": int(np.sum(selected != 0)),
            "selected_surrogate_cost_mean": float(np.mean(selected_cost)),
            "candidate0_surrogate_cost_mean": float(np.mean(default_cost)),
            "selected_minus_candidate0_surrogate_cost_mean": float(
                np.mean(selected_cost - default_cost)
            ),
            "mean_ranking_violation": float(np.mean(violations)),
            "maximum_ranking_violation": float(np.max(violations)),
        },
        "solver": {
            "name": str(result.solver_name),
            "status": str(result.solver_status),
            "iterations": len(history),
            "final_master_gap": projected_gap,
            "raw_solver_master_gap": float(result.final_master_gap),
            "total_cuts": int(sum(result.cuts_per_scene)),
            "cuts_per_scene": [int(value) for value in result.cuts_per_scene],
            "converged": bool(result.converged),
            "offline_wall_clock_s": float(wall_clock),
            "solver_options": dict(CLARABEL_SOLVER_OPTIONS),
            "history": history,
        },
        "actual_closed_loop_outcome": False,
        "calibration_executed": False,
        "holdout_executed": False,
        "claim_authorized": False,
    }


def train_learning_curve(
    *,
    snapshot_dir: Path,
    label_corpus_dir: Path,
    config: Mapping[str, Any],
    solver: Callable[..., Any] = solve_robust_margin_cutting_plane,
) -> dict[str, Any]:
    contract = _validate_config(config)
    source = config.get("source_corpus")
    expected_source_root = (
        source.get("artifact_root_sha256") if isinstance(source, Mapping) else None
    )
    corpus = load_training_corpus(
        snapshot_dir,
        label_corpus_dir,
        expected_source_artifact_root_sha256=expected_source_root,
    )
    count = len(corpus["snapshot_sha256"])
    preregistered = [int(value) for value in config["learning_curve_levels"]]
    reachable = [value for value in preregistered if value <= count]
    levels = [(str(value), value) for value in reachable]
    if bool(config["run_all_available_snapshots"]) and count not in reachable:
        levels.append((f"all_available_{count}", count))
    if not levels:
        raise ValueError("no learning-curve level is reachable")

    models: dict[str, dict[str, Any]] = {}
    for name, level_count in levels:
        models[name] = train_selector_level(
            corpus["atoms"][:level_count],
            corpus["candidate_cost"][:level_count],
            corpus["source_valid_mask"][:level_count],
            scales=corpus["atom_scales"],
            supported_atom_mask=corpus["supported_atom_mask"],
            snapshot_sha256=corpus["snapshot_sha256"][:level_count],
            level_name=name,
            normalized_atom_clip=float(contract["normalized_atom_clip"]),
            solver=solver,
        )
    return {
        "schema_version": "v22_convex_selector_training_manifest_v1",
        "status": "complete",
        "snapshot_count": count,
        "logical_map_count": corpus["logical_map_count"],
        "route_count": corpus["route_count"],
        "route_family_group_count": corpus["route_family_group_count"],
        "seed_count": corpus["seed_count"],
        "route_seed_count": corpus["route_seed_count"],
        "reachable_preregistered_levels": reachable,
        "unreachable_preregistered_levels": [
            value for value in preregistered if value > count
        ],
        "models": models,
        "primary_model_frozen": False,
        "calibration_executed": False,
        "holdout_executed": False,
        "holdout_outcomes_read": False,
        "actual_closed_loop_outcomes_read": False,
        "identity_fields_used_as_feature": False,
        "simulator_executed": False,
        "claim_authorized": False,
        "next_work_target": "v22_convex_selector_training_execution_and_review_only",
    }


def evaluate_v18_ablation(
    atoms: np.ndarray,
    candidate_cost: np.ndarray,
    source_valid: np.ndarray,
    *,
    weights: np.ndarray,
    scales: np.ndarray,
) -> dict[str, Any]:
    matrix = np.asarray(atoms, dtype=np.float64)
    costs = np.asarray(candidate_cost, dtype=np.float64)
    valid = np.asarray(source_valid, dtype=bool)
    coefficients = np.asarray(weights, dtype=np.float64).reshape(-1)
    scale = np.asarray(scales, dtype=np.float64).reshape(-1)
    if matrix.ndim != 3 or matrix.shape[1:] != (8, 14):
        raise ValueError("v18 ablation atoms must have shape [N,8,14]")
    if costs.shape != matrix.shape[:2] or valid.shape != matrix.shape[:2]:
        raise ValueError("v18 ablation costs and source mask must have shape [N,8]")
    if (
        coefficients.shape != (14,)
        or not np.isfinite(coefficients).all()
        or np.any(coefficients < 0.0)
        or not np.isclose(coefficients.sum(), 1.0, atol=1e-8, rtol=0.0)
        or scale.shape != (14,)
        or not np.isfinite(scale).all()
        or np.any(scale <= 0.0)
        or not np.isfinite(matrix).all()
        or np.any(matrix < 0.0)
        or not np.isfinite(costs).all()
        or not valid.any(axis=1).all()
    ):
        raise ValueError("v18 ablation weights, scales, or inputs are invalid")
    scores = np.einsum(
        "nkr,r->nk", matrix / scale.reshape(1, 1, -1), coefficients
    )
    selected = np.argmin(np.where(valid, scores, np.inf), axis=1)
    oracle = np.argmin(np.where(valid, costs, np.inf), axis=1)
    row = np.arange(selected.size)
    return {
        "name": "v18_frozen_corrected14d",
        "ablation_only": True,
        "primary_model": False,
        "snapshot_count": int(selected.size),
        "oracle_agreement_count": int(np.sum(selected == oracle)),
        "oracle_agreement_rate": float(np.mean(selected == oracle)),
        "candidate0_selection_count": int(np.sum(selected == 0)),
        "non_candidate0_selection_count": int(np.sum(selected != 0)),
        "selected_surrogate_cost_mean": float(np.mean(costs[row, selected])),
        "candidate0_surrogate_cost_mean": float(np.mean(costs[:, 0])),
        "actual_closed_loop_outcome": False,
        "calibration_executed": False,
        "holdout_executed": False,
        "claim_authorized": False,
    }


def load_v18_ablation_model(artifact: Path) -> tuple[np.ndarray, np.ndarray, dict[str, str]]:
    model_dir = Path(artifact) / "models"
    weights_path = model_dir / "corrected14d_weights.npy"
    scales_path = model_dir / "corrected14d_scales.json"
    weights = np.load(weights_path, allow_pickle=False)
    scale_payload = json.loads(scales_path.read_text(encoding="utf-8"))
    if (
        scale_payload.get("schema_version") != "dp_camp_v10_14d"
        or scale_payload.get("atom_names") != list(DP_CAMP_ATOM_NAMES_V10)
    ):
        raise ValueError("v18 corrected14d ablation schema mismatch")
    return (
        np.asarray(weights, dtype=np.float64),
        np.asarray(scale_payload["scales"], dtype=np.float64),
        {
            "weights_sha256": hashlib.sha256(weights_path.read_bytes()).hexdigest(),
            "scales_sha256": hashlib.sha256(scales_path.read_bytes()).hexdigest(),
        },
    )


def load_training_corpus(
    snapshot_dir: Path,
    label_corpus_dir: Path,
    *,
    expected_source_artifact_root_sha256: str | None = None,
) -> dict[str, Any]:
    paths = sorted(Path(snapshot_dir).glob("*.json"))
    if not paths:
        raise ValueError("train snapshot directory is empty")
    label_root = Path(label_corpus_dir)
    manifest = json.loads((label_root / "label_manifest.json").read_text())
    _validate_label_manifest(
        manifest,
        len(paths),
        expected_source_artifact_root_sha256=expected_source_artifact_root_sha256,
    )
    scales = np.asarray(manifest["atom_scales"], dtype=np.float64)
    supported = np.asarray(manifest["supported_atom_mask"], dtype=bool)
    label_hashes = list(manifest["label_file_sha256"])
    atoms = []
    costs = []
    source_valid = []
    digests = []
    maps = set()
    routes = set()
    groups = set()
    seeds = set()
    route_seeds = set()
    for index, path in enumerate(paths):
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if path.stem != digest:
            raise ValueError("snapshot content SHA mismatch")
        snapshot = json.loads(content)
        _validate_snapshot(snapshot)
        label_path = label_root / "labels" / path.name
        label_content = label_path.read_bytes()
        if hashlib.sha256(label_content).hexdigest() != label_hashes[index]:
            raise ValueError("label content SHA mismatch")
        label = json.loads(label_content)
        _validate_label(label, snapshot, digest, manifest["atom_scales_sha256"])
        features = snapshot["feature_payload"]
        sidecar = snapshot["sidecar"]
        atoms.append(features["atom_matrix"])
        costs.append(label["candidate_cost"])
        source_valid.append(features["source_valid_mask"])
        digests.append(digest)
        map_sha = str(sidecar["logical_map_sha256"])
        route_sha = str(sidecar["route_identity_sha256"])
        group_sha = str(sidecar["group_sha256"])
        seed = int(sidecar["seed"])
        maps.add(map_sha)
        routes.add(route_sha)
        groups.add(group_sha)
        seeds.add(seed)
        route_seeds.add((route_sha, seed))
    return {
        "atoms": np.asarray(atoms, dtype=np.float64),
        "candidate_cost": np.asarray(costs, dtype=np.float64),
        "source_valid_mask": np.asarray(source_valid, dtype=bool),
        "atom_scales": scales,
        "supported_atom_mask": supported,
        "snapshot_sha256": digests,
        "logical_map_count": len(maps),
        "route_count": len(routes),
        "route_family_group_count": len(groups),
        "seed_count": len(seeds),
        "route_seed_count": len(route_seeds),
    }


def write_training_outputs(result: Mapping[str, Any], output_dir: Path) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    model_dir = output / "models"
    model_dir.mkdir()
    model_files = {}
    for name, model in result["models"].items():
        content = _canonical_json_bytes(model)
        relative = f"models/{name}.json"
        (output / relative).write_bytes(content)
        model_files[name] = {
            "path": relative,
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    manifest = {key: value for key, value in result.items() if key != "models"}
    manifest["model_files"] = model_files
    (output / "training_manifest.json").write_bytes(_canonical_json_bytes(manifest))
    return manifest


def _accepted_weights(
    result: Any,
    normalized_atoms: np.ndarray,
    oracle: np.ndarray,
    margins: np.ndarray,
    feasible: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    if result.solver_name != SOLVER or result.solver_status != "optimal":
        raise RuntimeError("exact optimal CLARABEL solver status is required")
    if not result.converged or not result.history:
        raise RuntimeError("cutting-plane master must converge with history")
    if result.history[-1].get("new_cuts") != 0:
        raise RuntimeError("final master must have zero new cuts")
    if not np.isfinite(result.final_master_gap) or result.final_master_gap > TOLERANCE:
        raise RuntimeError("final master gap exceeds tolerance")
    raw = np.asarray(result.static_weights, dtype=np.float64).reshape(-1)
    if raw.shape != (normalized_atoms.shape[2],) or not np.isfinite(raw).all():
        raise RuntimeError("static weights have invalid shape or values")
    if np.any(raw < -1e-8) or not np.isclose(raw.sum(), 1.0, atol=1e-8, rtol=0.0):
        raise RuntimeError("static weights violate nonnegative simplex")
    weights = project_simplex_rows(raw)[0]
    _, violations, _ = candidate_ranking_violations(
        normalized_atoms, weights, oracle, margins, feasible
    )
    recorded = np.asarray(result.train_violations, dtype=np.float64).reshape(-1)
    if recorded.shape != violations.shape:
        raise RuntimeError("complete-master violation receipt has invalid shape")
    projected_gap = float(result.final_master_gap) + float(
        np.max(np.maximum(violations - recorded, 0.0))
    )
    if not np.isfinite(projected_gap) or projected_gap > TOLERANCE:
        raise RuntimeError("saved simplex projected master gap exceeds tolerance")
    return weights, violations, projected_gap


def _validate_config(config: Mapping[str, Any]) -> Mapping[str, Any]:
    if config.get("schema_version") != "camp_dp_v22_training_v1":
        raise ValueError("v22 training config schema mismatch")
    if config.get("execution_split") != "train":
        raise ValueError("selector training is train-only")
    for name in (
        "formal_seeds_authorized",
        "full36_authorized",
        "calibration_execution_authorized",
        "holdout_execution_authorized",
        "claim_authorized",
    ):
        if config.get(name) is not False:
            raise ValueError(f"{name} must remain false")
    levels = config.get("learning_curve_levels")
    if (
        not isinstance(levels, list)
        or not levels
        or any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in levels)
        or levels != sorted(set(levels))
    ):
        raise ValueError("learning curve levels must be unique increasing integers")
    if config.get("run_all_available_snapshots") is not True:
        raise ValueError("all available snapshots must run below the first level")
    contract = config.get("label_contract")
    if not isinstance(contract, Mapping) or (
        contract.get("schema_version") != "v22_causal_soft_risk_surrogate_v1"
        or contract.get("oracle_eligibility") != "source_valid_mask_only"
        or contract.get("physical_risk_semantics") != "finite_additive_cost_not_veto"
        or contract.get("actual_closed_loop_outcome") is not False
    ):
        raise ValueError("causal soft-risk label contract mismatch")
    return contract


def _validate_label_manifest(
    manifest: Mapping[str, Any],
    count: int,
    *,
    expected_source_artifact_root_sha256: str | None,
) -> None:
    if (
        manifest.get("schema_version") != "v22_causal_soft_risk_label_manifest_v1"
        or manifest.get("status") != "complete"
        or manifest.get("snapshot_count") != count
    ):
        raise ValueError("label manifest count or schema mismatch")
    if expected_source_artifact_root_sha256 is not None and (
        not _is_sha256(expected_source_artifact_root_sha256)
        or manifest.get("source_artifact_root_sha256")
        != expected_source_artifact_root_sha256
    ):
        raise ValueError("label source artifact root mismatch")
    for name in (
        "actual_closed_loop_outcomes_read",
        "future_outcome_fields_read",
        "identity_fields_used_as_label_or_feature",
        "calibration_executed",
        "holdout_executed",
        "holdout_outcomes_read",
        "model_trained",
        "simulator_executed",
        "claim_authorized",
    ):
        if manifest.get(name) is not False:
            raise ValueError(f"forbidden label manifest field {name}")
    scales = np.asarray(manifest.get("atom_scales"), dtype=np.float64)
    supported = np.asarray(manifest.get("supported_atom_mask"), dtype=bool)
    hashes = manifest.get("label_file_sha256")
    if (
        scales.shape != (14,)
        or not np.isfinite(scales).all()
        or np.any(scales <= 0.0)
        or supported.shape != (14,)
        or not supported.any()
        or not isinstance(hashes, list)
        or len(hashes) != count
        or any(not _is_sha256(value) for value in hashes)
    ):
        raise ValueError("label scales, support, or file hashes are invalid")
    scales_sha = hashlib.sha256(_canonical_json_bytes(scales.tolist())).hexdigest()
    if manifest.get("atom_scales_sha256") != scales_sha:
        raise ValueError("atom scale SHA mismatch")


def _validate_snapshot(snapshot: Mapping[str, Any]) -> None:
    if snapshot.get("schema_version") != "v22_native_decision_snapshot_v1":
        raise ValueError("decision snapshot schema mismatch")
    features = snapshot.get("feature_payload")
    sidecar = snapshot.get("sidecar")
    if (
        not isinstance(features, Mapping)
        or set(features) != FEATURE_FIELDS
        or IDENTITY_FIELDS.intersection(features)
    ):
        raise ValueError("feature payload contains forbidden identity or schema")
    if not isinstance(sidecar, Mapping) or sidecar.get("split") != "train":
        raise ValueError("selector snapshots must be train split")
    seed = sidecar.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed in FORMAL_SEEDS:
        raise ValueError("formal seed is forbidden")
    for name in ("logical_map_sha256", "route_identity_sha256", "group_sha256"):
        if not _is_sha256(sidecar.get(name)):
            raise ValueError(f"snapshot {name} is invalid")
    atoms = np.asarray(features["atom_matrix"], dtype=np.float64)
    valid = features["source_valid_mask"]
    rows = features["candidate_row_sha256"]
    if (
        atoms.shape != (8, 14)
        or not np.isfinite(atoms).all()
        or np.any(atoms < 0.0)
        or not isinstance(valid, list)
        or len(valid) != 8
        or any(not isinstance(value, bool) for value in valid)
        or not any(valid)
        or not isinstance(rows, list)
        or len(rows) != 8
        or any(not _is_sha256(value) for value in rows)
    ):
        raise ValueError("feature payload atoms, mask, or row hashes are invalid")
    if sidecar.get("candidate_tensor_sha256_before") != sidecar.get(
        "candidate_tensor_sha256_after"
    ):
        raise ValueError("candidate tensor immutability receipt failed")
    if (
        sidecar.get("default_output_sha256") != rows[0]
        or sidecar.get("candidate0_sha256") != rows[0]
        or not isinstance(sidecar.get("default_candidate0_identity"), Mapping)
        or sidecar["default_candidate0_identity"].get("elementwise_equal") is not True
    ):
        raise ValueError("candidate0/default identity receipt failed")


def _validate_label(
    label: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    digest: str,
    scales_sha256: str,
) -> None:
    if set(label) != LABEL_FIELDS:
        raise ValueError("label payload schema mismatch")
    if (
        label.get("schema_version") != "v22_causal_soft_risk_label_v1"
        or label.get("snapshot_sha256") != digest
        or label.get("label_source") != "v22_causal_soft_risk_surrogate_v1"
        or label.get("actual_closed_loop_outcome") is not False
        or label.get("physical_risk_semantics") != "finite_additive_cost_not_veto"
        or label.get("atom_scales_sha256") != scales_sha256
    ):
        raise ValueError("causal label contract mismatch")
    costs = np.asarray(label.get("candidate_cost"), dtype=np.float64)
    valid = np.asarray(snapshot["feature_payload"]["source_valid_mask"], dtype=bool)
    if (
        costs.shape != (8,)
        or not np.isfinite(costs).all()
        or np.any(costs < 0.0)
        or label.get("source_valid_mask") != valid.tolist()
    ):
        raise ValueError("causal label costs or source mask are invalid")
    oracle = int(np.argmin(np.where(valid, costs, np.inf)))
    if label.get("oracle_index") != oracle:
        raise ValueError("causal label oracle mismatch")


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value) <= set("0123456789abcdef")
    )


def _artifact_root_sha256(path: Path) -> str:
    manifest = Path(path) / "SHA256SUMS"
    if not manifest.is_file():
        raise ValueError("artifact SHA256SUMS is missing")
    return hashlib.sha256(manifest.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--label-artifact", required=True, type=Path)
    parser.add_argument("--label-artifact-root-sha256", required=True)
    parser.add_argument("--v18-ablation-artifact", required=True, type=Path)
    parser.add_argument("--v18-ablation-root-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    config_bytes = args.config.read_bytes()
    config = json.loads(config_bytes)
    source = config.get("source_corpus")
    if not isinstance(source, Mapping):
        raise ValueError("source_corpus must be a mapping")
    source_artifact = Path(str(source["artifact"]))
    source_root = _artifact_root_sha256(source_artifact)
    if source_root != source.get("artifact_root_sha256"):
        raise ValueError("source corpus root SHA mismatch")
    if not _is_sha256(args.label_artifact_root_sha256) or (
        _artifact_root_sha256(args.label_artifact)
        != args.label_artifact_root_sha256
    ):
        raise ValueError("label artifact root SHA mismatch")
    if not _is_sha256(args.v18_ablation_root_sha256) or (
        _artifact_root_sha256(args.v18_ablation_artifact)
        != args.v18_ablation_root_sha256
    ):
        raise ValueError("v18 ablation artifact root SHA mismatch")
    corpus = load_training_corpus(
        source_artifact / "corpus" / "snapshots",
        args.label_artifact / "label_corpus",
        expected_source_artifact_root_sha256=source_root,
    )
    result = train_learning_curve(
        snapshot_dir=source_artifact / "corpus" / "snapshots",
        label_corpus_dir=args.label_artifact / "label_corpus",
        config=config,
    )
    v18_weights, v18_scales, v18_hashes = load_v18_ablation_model(
        args.v18_ablation_artifact
    )
    v18_ablation = evaluate_v18_ablation(
        corpus["atoms"],
        corpus["candidate_cost"],
        corpus["source_valid_mask"],
        weights=v18_weights,
        scales=v18_scales,
    )
    v18_ablation.update(v18_hashes)
    v18_ablation["artifact_root_sha256"] = args.v18_ablation_root_sha256
    result["ablation_baselines"] = {"v18_frozen_corrected14d": v18_ablation}
    result["source_artifact_root_sha256"] = source_root
    result["label_artifact_root_sha256"] = args.label_artifact_root_sha256
    result["training_config_sha256"] = hashlib.sha256(config_bytes).hexdigest()
    manifest = write_training_outputs(result, args.output)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
