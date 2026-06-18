#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    CAMPSelector,
    DP_SCENE_FEATURE_NAMES,
)
from camp_core.outer_master.robust_margin_master import (  # noqa: E402
    RobustMarginConfig,
    candidate_ranking_violations,
    empirical_cvar,
    outcome_oracle_and_margins,
    project_simplex_rows,
    solve_robust_margin_cutting_plane,
    theta_weights,
)
from scripts.integrations.train_diffusion_planner_static_camp import (  # noqa: E402
    atom_names_for_dimension,
    load_candidate_closed_loop_outcomes,
    load_candidate_safety_cost_v1_values,
    load_outcome_weights,
    load_training_records,
    robust_atom_scales,
    validate_atom_schema,
)
from scripts.integrations.train_diffusion_planner_theta import (  # noqa: E402
    load_scene_training_groups,
    load_scene_training_records,
    normalize_features,
    robust_feature_normalization,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train DP-compatible Static or scene-conditioned CAMP with "
            "outcome-margin cutting planes and a mean/CVaR outer master."
        )
    )
    parser.add_argument("--selection_log", type=Path, action="append", required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("static", "theta"), required=True)
    parser.add_argument(
        "--training_scope",
        choices=("feasible_ranking", "all_infeasible_fallback"),
        default="feasible_ranking",
    )
    parser.add_argument(
        "--label_source",
        choices=("closed_loop_outcome", "safety_cost_v1_hard_guarded"),
        default="closed_loop_outcome",
        help=(
            "Offline candidate-branch target source. SafetyCost v1 labels are "
            "lower-is-better costs converted to values and hard-guarded against "
            "Top-1 collision, near-miss, lane, and red-light regressions."
        ),
    )
    parser.add_argument(
        "--objective",
        choices=("robust_margin_cvar",),
        default="robust_margin_cvar",
    )
    parser.add_argument("--risk_type", choices=("mean", "cvar"), default="cvar")
    parser.add_argument("--alpha", type=float, default=0.9)
    parser.add_argument("--margin_scale", type=float, default=0.1)
    parser.add_argument("--margin_clip", type=float, default=2.0)
    parser.add_argument("--l2_reg", type=float, default=1e-4)
    parser.add_argument("--max_iter", type=int, default=20)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    parser.add_argument("--solver", type=str, default="CLARABEL")
    parser.add_argument("--solver_verbose", action="store_true")
    parser.add_argument("--scale_percentile", type=float, default=95.0)
    parser.add_argument("--feature_clip", type=float, default=5.0)
    parser.add_argument("--val_fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--min_atom_weight",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help=(
            "Static-mode simplex lower bound for a named atom. "
            "Can be passed more than once."
        ),
    )
    parser.add_argument("--outcome_key", type=str, default="value")
    parser.add_argument("--outcome_weights", type=Path, default=None)
    parser.add_argument(
        "--require_atom_schema",
        action="store_true",
        help="Reject selection records without the exact ordered atom schema.",
    )
    return parser.parse_args()


def grouped_train_val_indices(
    group_ids: np.ndarray,
    *,
    val_fraction: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, int, int]:
    groups = np.asarray(group_ids, dtype=np.int64).reshape(-1)
    if not 0.0 <= float(val_fraction) < 1.0:
        raise ValueError("val_fraction must be in [0, 1).")
    unique_groups = np.unique(groups)
    if unique_groups.size == 0:
        raise ValueError("At least one training group is required.")
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(unique_groups)
    val_count = int(round(unique_groups.size * float(val_fraction)))
    if unique_groups.size > 1:
        val_count = min(max(val_count, 1), unique_groups.size - 1)
    else:
        val_count = 0
    val_groups = shuffled[:val_count]
    val_mask = np.isin(groups, val_groups)
    return (
        np.flatnonzero(~val_mask),
        np.flatnonzero(val_mask),
        int(unique_groups.size - val_count),
        int(val_count),
    )


def parse_atom_weight_lower_bounds(
    specifications: list[str],
    atom_names: tuple[str, ...],
) -> np.ndarray:
    lower = np.zeros(len(atom_names), dtype=np.float64)
    seen: set[str] = set()
    name_to_index = {name: idx for idx, name in enumerate(atom_names)}
    for specification in specifications:
        name, separator, raw_value = specification.partition("=")
        if not separator or not name or not raw_value:
            raise ValueError(
                "Each --min_atom_weight must use NAME=VALUE syntax."
            )
        if name not in name_to_index:
            raise ValueError(f"Unknown atom in --min_atom_weight: {name!r}.")
        if name in seen:
            raise ValueError(f"Duplicate --min_atom_weight for {name!r}.")
        try:
            value = float(raw_value)
        except ValueError as exc:
            raise ValueError(
                f"Invalid minimum weight for atom {name!r}: {raw_value!r}."
            ) from exc
        if not np.isfinite(value) or value < 0.0 or value > 1.0:
            raise ValueError(
                f"Minimum weight for atom {name!r} must be in [0, 1]."
            )
        lower[name_to_index[name]] = value
        seen.add(name)
    if float(np.sum(lower)) > 1.0 + 1e-12:
        raise ValueError("Minimum atom weights must sum to at most one.")
    return lower


def _selection_metrics(
    normalized_atoms: np.ndarray,
    feasible_mask: np.ndarray,
    oracle_indices: np.ndarray,
    margins: np.ndarray,
    weights: np.ndarray,
    *,
    risk_type: str,
    alpha: float,
) -> dict[str, float]:
    costs = np.einsum("nkr,nr->nk", normalized_atoms, weights)
    masked_costs = np.where(feasible_mask, costs, np.inf)
    selected = np.argmin(masked_costs, axis=1)
    _, violations, _ = candidate_ranking_violations(
        normalized_atoms,
        weights,
        oracle_indices,
        margins,
        feasible_mask,
    )
    cvar, eta = empirical_cvar(violations, alpha)
    risk = float(np.mean(violations)) if risk_type == "mean" else cvar
    return {
        "records": float(normalized_atoms.shape[0]),
        "oracle_match_rate": float(np.mean(selected == oracle_indices)),
        "mean_violation": float(np.mean(violations)),
        "cvar_violation": float(cvar),
        "cvar_eta": float(eta),
        "max_violation": float(np.max(violations)),
        "configured_risk": float(risk),
        "minimum_weight": float(np.min(weights)),
        "maximum_simplex_error": float(
            np.max(np.abs(np.sum(weights, axis=1) - 1.0))
        ),
    }


def save_theta_checkpoint(
    path: Path,
    *,
    theta: np.ndarray,
    offline_weights: np.ndarray,
    feature_center: np.ndarray,
    feature_scale: np.ndarray,
    feature_clip: float,
) -> None:
    np.savez(
        path,
        Theta=np.asarray(theta, dtype=np.float64),
        offline_weights=np.asarray(offline_weights, dtype=np.float64),
        feature_center=np.asarray(feature_center, dtype=np.float64),
        feature_scale=np.asarray(feature_scale, dtype=np.float64),
        feature_clip=np.asarray(float(feature_clip), dtype=np.float64),
        linear_activation=np.asarray("project_simplex"),
    )


def _verify_selector_artifact(
    *,
    mode: str,
    scales_path: Path,
    weights_path: Path | None = None,
    checkpoint_path: Path | None = None,
    feature_dim: int | None = None,
) -> None:
    selector = CAMPSelector.from_files(
        atom_scales_path=scales_path,
        static_weights_path=weights_path,
        checkpoint_path=checkpoint_path,
        mode="static" if mode == "static" else "linear",
    )
    if mode == "static":
        weights = selector.weights_for()
    else:
        weights = selector.weights_for(np.zeros(int(feature_dim), dtype=np.float64))
    if np.min(weights) < -1e-9 or not np.isclose(np.sum(weights), 1.0, atol=1e-8):
        raise RuntimeError("Saved CAMP artifact does not produce simplex weights.")


def main() -> None:
    args = parse_args()
    if args.training_scope == "all_infeasible_fallback" and args.mode != "static":
        raise ValueError("All-infeasible fallback training currently requires static mode.")
    outcome_weights = load_outcome_weights(args.outcome_weights)
    if outcome_weights is not None and args.label_source != "closed_loop_outcome":
        raise ValueError("--outcome_weights requires --label_source closed_loop_outcome.")
    if args.mode == "theta":
        features, atoms, selector_feasible = load_scene_training_records(
            args.selection_log
        )
    else:
        atoms, selector_feasible = load_training_records(args.selection_log)
        features = None
    group_ids = load_scene_training_groups(args.selection_log)

    if args.label_source == "closed_loop_outcome":
        outcome_values, outcome_feasible = load_candidate_closed_loop_outcomes(
            args.selection_log,
            outcome_key=args.outcome_key,
            outcome_weights=outcome_weights,
        )
    else:
        outcome_values, outcome_feasible = load_candidate_safety_cost_v1_values(
            args.selection_log,
        )
    if outcome_values.shape != selector_feasible.shape:
        raise ValueError(
            "Outcome values must match selector feasibility, "
            f"got {outcome_values.shape} and {selector_feasible.shape}."
        )
    input_records = int(atoms.shape[0])
    if args.training_scope == "feasible_ranking":
        scope_mask = np.ones(input_records, dtype=bool)
        combined_feasible = (
            selector_feasible & outcome_feasible & np.isfinite(outcome_values)
        )
    else:
        scope_mask = ~selector_feasible.any(axis=1)
        combined_feasible = outcome_feasible & np.isfinite(outcome_values)
    atoms = atoms[scope_mask]
    combined_feasible = combined_feasible[scope_mask]
    outcome_values = outcome_values[scope_mask]
    if features is not None:
        features = features[scope_mask]
    group_ids = group_ids[scope_mask]
    scope_records = int(atoms.shape[0])
    valid = combined_feasible.any(axis=1)
    dropped_records = int(np.sum(~valid))
    atoms = atoms[valid]
    combined_feasible = combined_feasible[valid]
    outcome_values = outcome_values[valid]
    if features is not None:
        features = features[valid]
    group_ids = group_ids[valid]
    if atoms.shape[0] == 0:
        raise ValueError("No records contain a finite feasible candidate.")

    train_idx, val_idx, train_groups, val_groups = grouped_train_val_indices(
        group_ids,
        val_fraction=args.val_fraction,
        seed=args.seed,
    )
    if train_idx.size == 0:
        raise ValueError("Grouped split produced no training records.")

    atom_names = atom_names_for_dimension(atoms.shape[-1])
    if args.min_atom_weight and args.mode != "static":
        raise ValueError("--min_atom_weight currently requires static mode.")
    minimum_atom_weights = parse_atom_weight_lower_bounds(
        args.min_atom_weight,
        atom_names,
    )
    atom_schema = validate_atom_schema(
        args.selection_log,
        atom_names,
        require=args.require_atom_schema,
    )
    atom_scales = robust_atom_scales(atoms[train_idx], args.scale_percentile)
    normalized_atoms = np.clip(
        np.nan_to_num(atoms / atom_scales.reshape(1, 1, -1)),
        0.0,
        10.0,
    )
    oracle, margins = outcome_oracle_and_margins(
        outcome_values,
        combined_feasible,
        margin_scale=args.margin_scale,
        margin_clip=args.margin_clip,
    )
    config = RobustMarginConfig(
        mode=args.mode,
        risk_type=args.risk_type,
        alpha=args.alpha,
        l2_reg=args.l2_reg,
        max_iter=args.max_iter,
        tolerance=args.tolerance,
        solver=args.solver,
        verbose=args.solver_verbose,
        static_weight_lower_bounds=tuple(minimum_atom_weights.tolist()),
    )

    feature_center = None
    feature_scale = None
    normalized_features = None
    if args.mode == "theta":
        feature_center, feature_scale = robust_feature_normalization(
            features[train_idx]
        )
        normalized_features = normalize_features(
            features,
            feature_center,
            feature_scale,
            clip=args.feature_clip,
        )

    result = solve_robust_margin_cutting_plane(
        normalized_atoms[train_idx],
        oracle[train_idx],
        margins[train_idx],
        combined_feasible[train_idx],
        config=config,
        features=(
            None if normalized_features is None else normalized_features[train_idx]
        ),
    )
    if not result.converged or result.final_master_gap > args.tolerance:
        raise RuntimeError(
            "Robust CAMP master did not satisfy the declared cutting-plane "
            "tolerance; refusing to save a deployable checkpoint. "
            f"final_master_gap={result.final_master_gap:.6g}, "
            f"tolerance={args.tolerance:.6g}."
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.training_scope == "all_infeasible_fallback":
        scales_name = "atom_scales_dp_fallback.json"
    else:
        scales_name = (
            "atom_scales_dp_static.json"
            if args.mode == "static"
            else "atom_scales_dp_scene_theta.json"
        )
    scales_path = args.output_dir / scales_name
    scales_path.write_text(
        json.dumps(
            {
                "atom_schema_version": atom_schema["version"],
                "atom_names": atom_schema["atom_names"],
                "scales": atom_scales.tolist(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    artifact_paths: dict[str, str] = {"atom_scales_path": str(scales_path)}
    if args.mode == "static":
        weights_path = args.output_dir / (
            "offline_weights_dp_fallback.npy"
            if args.training_scope == "all_infeasible_fallback"
            else "offline_weights_dp_static.npy"
        )
        static_weights = project_simplex_rows(result.static_weights)[0]
        if np.any(static_weights + 1e-8 < minimum_atom_weights):
            raise RuntimeError(
                "Saved static weights violate a configured atom lower bound."
            )
        np.save(weights_path, static_weights.astype(np.float64))
        all_weights = np.broadcast_to(
            static_weights, (atoms.shape[0], atoms.shape[-1])
        ).copy()
        artifact_paths["weights_path"] = str(weights_path)
        _verify_selector_artifact(
            mode="static",
            scales_path=scales_path,
            weights_path=weights_path,
        )
    else:
        checkpoint_path = args.output_dir / "camp_dp_scene_theta.npz"
        normalization_path = (
            args.output_dir / "feature_normalization_dp_scene_theta.json"
        )
        all_weights = theta_weights(result.theta, normalized_features)
        offline_weights = project_simplex_rows(np.mean(all_weights, axis=0))[0]
        save_theta_checkpoint(
            checkpoint_path,
            theta=result.theta,
            offline_weights=offline_weights,
            feature_center=feature_center,
            feature_scale=feature_scale,
            feature_clip=args.feature_clip,
        )
        normalization_path.write_text(
            json.dumps(
                {
                    "feature_names": list(DP_SCENE_FEATURE_NAMES),
                    "feature_center": feature_center.tolist(),
                    "feature_scale": feature_scale.tolist(),
                    "feature_clip": float(args.feature_clip),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        artifact_paths.update(
            {
                "checkpoint_path": str(checkpoint_path),
                "feature_normalization_path": str(normalization_path),
            }
        )
        _verify_selector_artifact(
            mode="theta",
            scales_path=scales_path,
            checkpoint_path=checkpoint_path,
            feature_dim=normalized_features.shape[1],
        )

    train_metrics = _selection_metrics(
        normalized_atoms[train_idx],
        combined_feasible[train_idx],
        oracle[train_idx],
        margins[train_idx],
        all_weights[train_idx],
        risk_type=args.risk_type,
        alpha=args.alpha,
    )
    val_metrics = (
        None
        if val_idx.size == 0
        else _selection_metrics(
            normalized_atoms[val_idx],
            combined_feasible[val_idx],
            oracle[val_idx],
            margins[val_idx],
            all_weights[val_idx],
            risk_type=args.risk_type,
            alpha=args.alpha,
        )
    )
    summary: dict[str, Any] = {
        "training_type": "diffusion_planner_robust_margin_camp",
        "mode": args.mode,
        "training_scope": args.training_scope,
        "label_source": args.label_source,
        "objective": args.objective,
        "risk_type": args.risk_type,
        "alpha": float(args.alpha),
        "margin_scale": float(args.margin_scale),
        "margin_clip": float(args.margin_clip),
        "l2_reg": float(args.l2_reg),
        "max_iter": int(args.max_iter),
        "tolerance": float(args.tolerance),
        "solver": args.solver,
        "solver_status": result.solver_status,
        "converged": bool(result.converged),
        "final_master_gap": float(result.final_master_gap),
        "selection_logs": [str(path) for path in args.selection_log],
        "outcome_key": (
            args.outcome_key
            if args.label_source == "closed_loop_outcome" and outcome_weights is None
            else None
        ),
        "outcome_weights_path": (
            str(args.outcome_weights)
            if args.label_source == "closed_loop_outcome"
            and args.outcome_weights is not None
            else None
        ),
        "outcome_weights": (
            outcome_weights if args.label_source == "closed_loop_outcome" else None
        ),
        "input_records": input_records,
        "scope_records": scope_records,
        "num_records": int(atoms.shape[0]),
        "dropped_records_without_feasible_candidate": dropped_records,
        "dropped_records_without_eligible_candidate": dropped_records,
        "num_candidates": int(atoms.shape[1]),
        "num_atoms": int(atoms.shape[2]),
        "atom_names": list(atom_names),
        "minimum_atom_weights": {
            name: float(minimum_atom_weights[idx])
            for idx, name in enumerate(atom_names)
            if minimum_atom_weights[idx] > 0.0
        },
        "atom_schema": atom_schema,
        "scale_percentile": float(args.scale_percentile),
        "feature_dim": None if features is None else int(features.shape[1]),
        "feature_clip": None if features is None else float(args.feature_clip),
        "train_groups": train_groups,
        "val_groups": val_groups,
        "train_selection_logs": [
            str(args.selection_log[group_idx])
            for group_idx in sorted(np.unique(group_ids[train_idx]).tolist())
        ],
        "val_selection_logs": [
            str(args.selection_log[group_idx])
            for group_idx in sorted(np.unique(group_ids[val_idx]).tolist())
        ],
        "normalization_fit_scope": "train_groups_only",
        "train_metrics": train_metrics,
        "val_metrics": val_metrics,
        "cuts_per_scene": result.cuts_per_scene,
        "history": result.history,
        "artifacts": artifact_paths,
        "caveat": (
            (
                "This checkpoint minimizes mean/CVaR robust margin violations "
                "against hard-guarded offline SafetyCost v1 candidate-branch "
                f"labels for scope={args.training_scope!r}. Runtime CAMP atoms "
                "must not use future outcomes, and matched closed-loop "
                "evaluation remains required for performance claims."
            )
            if args.label_source == "safety_cost_v1_hard_guarded"
            else (
                "This checkpoint minimizes mean/CVaR robust outcome-margin "
                f"violations for scope={args.training_scope!r} over short-horizon "
                "candidate branches. Matched closed-loop evaluation remains "
                "required for performance claims."
            )
        ),
    }
    summary_path = args.output_dir / "training_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
