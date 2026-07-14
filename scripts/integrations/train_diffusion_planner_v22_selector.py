#!/usr/bin/env python3
"""Train and calibration-freeze v22 static affine selectors."""

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


def calibrate_selector_models(
    atoms: np.ndarray,
    source_valid: np.ndarray,
    physical_feasible: np.ndarray,
    *,
    models: Mapping[str, Mapping[str, Any]],
    v18_weights: np.ndarray,
    v18_scales: np.ndarray,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    contract = _validate_calibration_freeze_config(config)
    matrix = np.asarray(atoms, dtype=np.float64)
    valid = np.asarray(source_valid, dtype=bool)
    physical = np.asarray(physical_feasible, dtype=bool)
    if (
        matrix.ndim != 3
        or matrix.shape[1:] != (8, 14)
        or valid.shape != matrix.shape[:2]
        or physical.shape != matrix.shape[:2]
        or matrix.shape[0] != int(config["expected_snapshot_count"])
        or not np.isfinite(matrix).all()
        or np.any(matrix < 0.0)
        or not valid.any(axis=1).all()
        or not models
    ):
        raise ValueError("calibration atoms, masks, count, or model set are invalid")

    ordered_models = {
        str(name): _validate_calibration_model(model, str(name))
        for name, model in sorted(models.items())
    }
    first = next(iter(ordered_models.values()))
    label_scales = np.asarray(first["atom_scales"], dtype=np.float64)
    for name, model in ordered_models.items():
        if not np.array_equal(
            np.asarray(model["atom_scales"], dtype=np.float64), label_scales
        ):
            raise ValueError(f"calibration candidate {name} changed train-only scales")

    from scripts.integrations.materialize_diffusion_planner_v22_labels import (
        causal_soft_risk_labels,
    )

    costs, oracle = causal_soft_risk_labels(
        matrix,
        source_valid=valid,
        physical_feasible=physical,
        scales=label_scales,
        atom_severity_weights=np.asarray(
            contract["atom_severity_weights"], dtype=np.float64
        ),
        physical_risk_penalty=float(contract["physical_risk_penalty"]),
        normalized_atom_clip=float(contract["normalized_atom_clip"]),
    )
    evaluations = {}
    for name, model in ordered_models.items():
        normalized = np.clip(
            matrix / label_scales.reshape(1, 1, -1),
            0.0,
            float(model["normalized_atom_clip"]),
        )
        scores = np.einsum(
            "nkr,r->nk", normalized, np.asarray(model["weights"], dtype=np.float64)
        )
        evaluations[name] = {
            "level_name": name,
            "model_sha256": model.get("model_sha256"),
            "metrics": _calibration_metrics(scores, costs, valid, oracle),
        }
    selected_level = min(
        evaluations,
        key=lambda name: (
            evaluations[name]["metrics"]["selected_surrogate_cost_mean"],
            name,
        ),
    )
    selected_source = ordered_models[selected_level]
    selected = dict(evaluations[selected_level])
    selected.update(
        {
            "weights": list(selected_source["weights"]),
            "atom_scales": list(selected_source["atom_scales"]),
            "atom_names": list(selected_source["atom_names"]),
            "atom_schema_version": selected_source["atom_schema_version"],
            "supported_atom_mask": list(selected_source["supported_atom_mask"]),
            "normalized_atom_clip": float(
                selected_source["normalized_atom_clip"]
            ),
            "score_contract": selected_source["score_contract"],
            "oracle_eligibility": selected_source["oracle_eligibility"],
        }
    )
    v18 = evaluate_v18_ablation(
        matrix,
        costs,
        valid,
        weights=v18_weights,
        scales=v18_scales,
    )
    v18["calibration_executed"] = True
    speed = config["speed_protocol"]
    return {
        "schema_version": "v22_calibrated_selector_freeze_v1",
        "status": "complete",
        "selected_level": selected_level,
        "selected_model": selected,
        "candidate_model_metrics": evaluations,
        "v18_ablation": v18,
        "snapshot_count": int(matrix.shape[0]),
        "surrogate_oracle_candidate0_count": int(np.sum(oracle == 0)),
        "surrogate_oracle_non_candidate0_count": int(np.sum(oracle != 0)),
        "all_k_high_risk_snapshot_count": int(
            np.sum(valid.all(axis=1) & ~physical.any(axis=1))
        ),
        "primary_model_frozen": True,
        "model_retrained": False,
        "solver_invoked": False,
        "calibration_executed": True,
        "actual_closed_loop_outcomes_read": False,
        "primary_operational_tolerance_mps": float(
            speed["primary_operational_tolerance_mps"]
        ),
        "speed_sensitivity_tolerances_mps": list(
            speed["calibration_sensitivity_tolerances_mps"]
        ),
        "speed_sensitivity_pending_pilot_closed_loop": True,
        "claim_contract": dict(config["claim_contract"]),
        "holdout_executed": False,
        "holdout_outcomes_read": False,
        "claim_authorized": False,
        "pilot_execution_authorized": False,
        "next_work_target": "v22_native_paired_protocol_and_pilot_preflight_tdd_only",
    }


def write_calibration_freeze_outputs(
    result: Mapping[str, Any], output_dir: Path
) -> dict[str, Any]:
    if result.get("primary_model_frozen") is not True:
        raise ValueError("calibration result did not freeze a primary model")
    selected = result.get("selected_model")
    if not isinstance(selected, Mapping):
        raise ValueError("selected calibration model is missing")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    runtime = output / "runtime"
    runtime.mkdir()
    weights_path = runtime / "weights.npy"
    scales_path = runtime / "atom_scales.json"
    weights = np.asarray(selected["weights"], dtype=np.float64)
    np.save(weights_path, weights, allow_pickle=False)
    scales_payload = {
        "schema_version": "dp_camp_v10_14d",
        "atom_schema_version": selected["atom_schema_version"],
        "atom_names": list(selected["atom_names"]),
        "scales": list(selected["atom_scales"]),
        "fit_scope": "v22_train_snapshots_only",
        "frozen_by": "v22_calibration_model_selection",
    }
    scales_path.write_bytes(_canonical_json_bytes(scales_payload))
    manifest = json.loads(json.dumps(result, allow_nan=False))
    manifest["runtime_assets"] = {
        "weights": {
            "path": "runtime/weights.npy",
            "sha256": hashlib.sha256(weights_path.read_bytes()).hexdigest(),
        },
        "atom_scales": {
            "path": "runtime/atom_scales.json",
            "sha256": hashlib.sha256(scales_path.read_bytes()).hexdigest(),
        },
    }
    (output / "freeze_manifest.json").write_bytes(_canonical_json_bytes(manifest))
    return manifest


def _calibration_metrics(
    scores: np.ndarray,
    costs: np.ndarray,
    source_valid: np.ndarray,
    oracle: np.ndarray,
) -> dict[str, Any]:
    selected = np.argmin(np.where(source_valid, scores, np.inf), axis=1)
    row = np.arange(selected.size)
    selected_cost = costs[row, selected]
    return {
        "oracle_agreement_count": int(np.sum(selected == oracle)),
        "oracle_agreement_rate": float(np.mean(selected == oracle)),
        "candidate0_selection_count": int(np.sum(selected == 0)),
        "non_candidate0_selection_count": int(np.sum(selected != 0)),
        "selected_surrogate_cost_mean": float(np.mean(selected_cost)),
        "candidate0_surrogate_cost_mean": float(np.mean(costs[:, 0])),
        "selected_minus_candidate0_surrogate_cost_mean": float(
            np.mean(selected_cost - costs[:, 0])
        ),
    }


def _validate_calibration_model(
    model: Mapping[str, Any], level_name: str
) -> dict[str, Any]:
    result = dict(model)
    weights = np.asarray(result.get("weights"), dtype=np.float64)
    scales = np.asarray(result.get("atom_scales"), dtype=np.float64)
    supported = np.asarray(result.get("supported_atom_mask"), dtype=bool)
    solver = result.get("solver")
    if (
        result.get("schema_version") != "v22_static_affine_selector_model_v1"
        or result.get("level_name") != level_name
        or result.get("training_source") != "v22_train_snapshots_only"
        or result.get("atom_schema_version") != "dp_camp_v10_14d"
        or result.get("atom_names") != list(DP_CAMP_ATOM_NAMES_V10)
        or result.get("score_contract") != "score_k(w)=a_k^T w"
        or result.get("oracle_eligibility") != "source_valid_mask_only"
        or weights.shape != (14,)
        or not np.isfinite(weights).all()
        or np.any(weights < 0.0)
        or not np.isclose(weights.sum(), 1.0, atol=1e-8, rtol=0.0)
        or scales.shape != (14,)
        or not np.isfinite(scales).all()
        or np.any(scales <= 0.0)
        or supported.shape != (14,)
        or np.any(weights[~supported] != 0.0)
        or not isinstance(solver, Mapping)
        or solver.get("name") != "CLARABEL"
        or solver.get("status") != "optimal"
        or solver.get("converged") is not True
        or result.get("actual_closed_loop_outcome") is not False
        or result.get("calibration_executed") is not False
        or result.get("holdout_executed") is not False
        or result.get("claim_authorized") is not False
    ):
        raise ValueError(f"calibration candidate model {level_name} is invalid")
    return result


def _validate_calibration_freeze_config(
    config: Mapping[str, Any],
) -> Mapping[str, Any]:
    if (
        config.get("schema_version") != "camp_dp_v22_calibration_freeze_v1"
        or config.get("execution_split") != "calibration"
        or config.get("model_selection_metric")
        != "mean_causal_soft_risk_surrogate_cost"
        or config.get("model_selection_tie_break")
        != "level_name_lexicographic"
    ):
        raise ValueError("calibration freeze config schema or selection mismatch")
    for name in (
        "retraining_authorized",
        "solver_authorized",
        "formal_seeds_authorized",
        "holdout_execution_authorized",
        "claim_authorized",
    ):
        if config.get(name) is not False:
            raise ValueError(f"{name} must remain false during calibration freeze")
    for name in (
        "expected_snapshot_count",
        "expected_route_count",
        "expected_seed_count",
        "expected_route_seed_count",
    ):
        value = config.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    speed = config.get("speed_protocol")
    if not isinstance(speed, Mapping) or (
        float(speed.get("primary_operational_tolerance_mps", -1.0)) != 0.1
        or speed.get("calibration_sensitivity_tolerances_mps")
        != [0.0, 0.05, 0.1, 0.2]
        or speed.get("sensitivity_source")
        != "pilot_closed_loop_outcomes_not_snapshot_surrogate"
    ):
        raise ValueError("calibration speed protocol mismatch")
    contract = config.get("label_contract")
    if not isinstance(contract, Mapping) or (
        contract.get("schema_version") != "v22_causal_soft_risk_surrogate_v1"
        or contract.get("oracle_eligibility") != "source_valid_mask_only"
        or contract.get("physical_risk_semantics")
        != "finite_additive_cost_not_veto"
        or contract.get("actual_closed_loop_outcome") is not False
    ):
        raise ValueError("calibration causal label contract mismatch")
    weights = np.asarray(contract.get("atom_severity_weights"), dtype=np.float64)
    if weights.shape != (14,) or not np.isfinite(weights).all() or np.any(weights < 0):
        raise ValueError("calibration severity weights must be finite nonnegative 14D")
    claim = config.get("claim_contract")
    if not isinstance(claim, Mapping) or claim != {
        "overall_mean_delta_strictly_below_zero": True,
        "cluster_ci95_upper_strictly_below_zero": True,
        "better_pairs_must_exceed_worse_pairs": True,
        "additional_collision_pairs_max": 0,
        "additional_red_light_pairs_max": 0,
        "offroad_wrong_way_mean_delta_max": 0.0,
        "offroad_wrong_way_ci95_upper_max": 0.005,
    }:
        raise ValueError("calibration claim contract mismatch")
    return contract


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


def load_calibration_corpus(
    artifact: Path,
    *,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_calibration_freeze_config(config)
    root = Path(artifact)
    snapshot_dir = root / "corpus" / "snapshots"
    paths = sorted(snapshot_dir.glob("*.json"))
    expected_snapshots = int(config["expected_snapshot_count"])
    if len(paths) != expected_snapshots:
        raise ValueError("calibration snapshot count mismatch")
    summary = json.loads(
        (root / "corpus" / "corpus_summary.json").read_text(encoding="utf-8")
    )
    _validate_calibration_corpus_summary(summary, config)

    atoms = []
    source_valid = []
    physical_feasible = []
    digests = []
    maps = set()
    routes = set()
    groups = set()
    seeds = set()
    route_seeds = set()
    all_k_high_risk = 0
    for path in paths:
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if path.stem != digest:
            raise ValueError("calibration snapshot content SHA mismatch")
        snapshot = json.loads(content)
        _validate_calibration_snapshot(snapshot)
        features = snapshot["feature_payload"]
        sidecar = snapshot["sidecar"]
        atoms.append(features["atom_matrix"])
        source_valid.append(features["source_valid_mask"])
        physical_feasible.append(sidecar["physical_feasible_mask"])
        digests.append(digest)
        maps.add(str(sidecar["logical_map_sha256"]))
        route = str(sidecar["route_identity_sha256"])
        seed = int(sidecar["seed"])
        routes.add(route)
        groups.add(str(sidecar["group_sha256"]))
        seeds.add(seed)
        route_seeds.add((route, seed))
        all_k_high_risk += int(sidecar["all_k_high_risk"])

    complete = int(summary["complete_route_seed_runs"])
    retained = int(summary["retained_route_seed_runs"])
    if (
        len(routes) != int(config["expected_route_count"])
        or len(seeds) != int(config["expected_seed_count"])
        or len(route_seeds) != retained
        or all_k_high_risk != int(summary["all_k_high_risk_snapshot_count"])
    ):
        raise ValueError("calibration route, seed, or stratum count mismatch")
    return {
        "atoms": np.asarray(atoms, dtype=np.float64),
        "source_valid_mask": np.asarray(source_valid, dtype=bool),
        "physical_feasible_mask": np.asarray(physical_feasible, dtype=bool),
        "snapshot_sha256": digests,
        "logical_map_count": len(maps),
        "route_count": len(routes),
        "route_family_group_count": len(groups),
        "seed_count": len(seeds),
        "complete_route_seed_count": complete,
        "retained_route_seed_count": retained,
        "hard_source_failure_count": int(summary["failed_route_seed_runs"]),
        "all_k_high_risk_snapshot_count": all_k_high_risk,
        "route_coverage": float(summary["route_coverage"]),
        "failures": list(summary["failures"]),
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
    _validate_snapshot_for_split(snapshot, "train")


def _validate_calibration_snapshot(snapshot: Mapping[str, Any]) -> None:
    _validate_snapshot_for_split(snapshot, "calibration")
    features = snapshot["feature_payload"]
    sidecar = snapshot["sidecar"]
    if sidecar.get("offline_label_provenance") != (
        "calibration_causal_candidate_cost_sidecar_only_not_selector_feature"
    ):
        raise ValueError("calibration offline-label provenance mismatch")
    physical = sidecar.get("physical_feasible_mask")
    if (
        not isinstance(physical, list)
        or len(physical) != 8
        or any(not isinstance(value, bool) for value in physical)
        or not isinstance(sidecar.get("all_k_high_risk"), bool)
    ):
        raise ValueError("calibration physical-risk receipt is invalid")
    valid = np.asarray(features["source_valid_mask"], dtype=bool)
    expected_high_risk = bool(valid.all() and not np.asarray(physical).any())
    if sidecar["all_k_high_risk"] != expected_high_risk:
        raise ValueError("calibration all-K-high-risk receipt mismatch")


def _validate_snapshot_for_split(
    snapshot: Mapping[str, Any], expected_split: str
) -> None:
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
    if not isinstance(sidecar, Mapping) or sidecar.get("split") != expected_split:
        raise ValueError(f"selector snapshots must be {expected_split} split")
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


def _validate_calibration_corpus_summary(
    summary: Mapping[str, Any], config: Mapping[str, Any]
) -> None:
    planned = int(config["expected_route_seed_count"])
    retained = int(config.get("expected_retained_route_seed_count", planned))
    complete = int(config.get("expected_complete_route_seed_count", planned))
    failed = int(config.get("expected_hard_source_failure_count", 0))
    failures = summary.get("failures")
    if (
        summary.get("execution_split") != "calibration"
        or summary.get("planned_route_seed_runs") != planned
        or summary.get("retained_route_seed_runs") != retained
        or summary.get("complete_route_seed_runs") != complete
        or summary.get("failed_route_seed_runs") != failed
        or retained != planned
        or complete + failed != planned
        or float(summary.get("route_coverage", -1.0)) != 1.0
        or summary.get("calibration_executed") is not True
        or summary.get("holdout_executed") is not False
        or summary.get("holdout_outcomes_read") is not False
        or summary.get("claim_authorized") is not False
        or not isinstance(failures, list)
        or len(failures) != failed
        or isinstance(summary.get("all_k_high_risk_snapshot_count"), bool)
        or not isinstance(summary.get("all_k_high_risk_snapshot_count"), int)
        or int(summary["all_k_high_risk_snapshot_count"]) < 0
    ):
        raise ValueError("calibration corpus retention or failure summary mismatch")


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


def execute_calibration_freeze(config_path: Path, output: Path) -> dict[str, Any]:
    config_bytes = Path(config_path).read_bytes()
    config = json.loads(config_bytes)
    _validate_calibration_freeze_config(config)
    training = config.get("training_candidate")
    calibration = config.get("calibration_corpus")
    v18 = config.get("v18_ablation")
    if not all(isinstance(value, Mapping) for value in (training, calibration, v18)):
        raise ValueError("calibration freeze artifact config is incomplete")

    training_artifact = _verify_configured_artifact(
        training["artifact"], training["artifact_root_sha256"], "training"
    )
    _verify_configured_artifact(
        training["independent_review_artifact"],
        training["independent_review_root_sha256"],
        "training independent review",
    )
    calibration_artifact = _verify_configured_artifact(
        calibration["artifact"],
        calibration["artifact_root_sha256"],
        "calibration corpus",
    )
    _verify_configured_artifact(
        calibration["independent_review_artifact"],
        calibration["independent_review_root_sha256"],
        "calibration corpus independent review",
    )
    v18_artifact = _verify_configured_artifact(
        v18["artifact"], v18["artifact_root_sha256"], "v18 ablation"
    )

    model_path = Path(str(training["model_path"]))
    if not model_path.resolve().is_relative_to(training_artifact.resolve()):
        raise ValueError("training model must stay inside the sealed artifact")
    model_content = model_path.read_bytes()
    model_sha256 = hashlib.sha256(model_content).hexdigest()
    if model_sha256 != training.get("model_sha256"):
        raise ValueError("training model SHA mismatch")
    model = json.loads(model_content)
    model["model_sha256"] = model_sha256
    scale_sha256 = hashlib.sha256(
        _canonical_json_bytes(model.get("atom_scales"))
    ).hexdigest()
    if scale_sha256 != training.get("train_atom_scales_sha256"):
        raise ValueError("training atom-scale SHA mismatch")

    corpus = load_calibration_corpus(calibration_artifact, config=config)
    v18_weights, v18_scales, v18_hashes = load_v18_ablation_model(v18_artifact)
    result = calibrate_selector_models(
        corpus["atoms"],
        corpus["source_valid_mask"],
        corpus["physical_feasible_mask"],
        models={str(model["level_name"]): model},
        v18_weights=v18_weights,
        v18_scales=v18_scales,
        config=config,
    )
    result.update(
        {
            "calibration_config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            "training_artifact_root_sha256": training["artifact_root_sha256"],
            "training_independent_review_root_sha256": training[
                "independent_review_root_sha256"
            ],
            "calibration_corpus_root_sha256": calibration[
                "artifact_root_sha256"
            ],
            "calibration_corpus_independent_review_root_sha256": calibration[
                "independent_review_root_sha256"
            ],
            "v18_ablation_artifact_root_sha256": v18["artifact_root_sha256"],
            "v18_ablation_model_hashes": v18_hashes,
            "calibration_corpus_receipt": {
                key: corpus[key]
                for key in (
                    "logical_map_count",
                    "route_count",
                    "route_family_group_count",
                    "seed_count",
                    "complete_route_seed_count",
                    "retained_route_seed_count",
                    "hard_source_failure_count",
                    "all_k_high_risk_snapshot_count",
                    "route_coverage",
                    "failures",
                )
            },
        }
    )
    return write_calibration_freeze_outputs(result, Path(output))


def _verify_configured_artifact(
    path_value: Any, expected_root_sha256: Any, label: str
) -> Path:
    path = Path(str(path_value))
    if not _is_sha256(expected_root_sha256) or (
        _artifact_root_sha256(path) != expected_root_sha256
    ):
        raise ValueError(f"{label} artifact root SHA mismatch")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=("train", "calibration-freeze"), default="train"
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--label-artifact", type=Path)
    parser.add_argument("--label-artifact-root-sha256")
    parser.add_argument("--v18-ablation-artifact", type=Path)
    parser.add_argument("--v18-ablation-root-sha256")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.mode == "calibration-freeze":
        manifest = execute_calibration_freeze(args.config, args.output)
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    for name in (
        "label_artifact",
        "label_artifact_root_sha256",
        "v18_ablation_artifact",
        "v18_ablation_root_sha256",
    ):
        if getattr(args, name) is None:
            parser.error(f"--{name.replace('_', '-')} is required in train mode")
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
