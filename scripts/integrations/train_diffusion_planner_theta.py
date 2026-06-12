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
    DP_SCENE_FEATURE_NAMES,
)
from scripts.integrations.train_diffusion_planner_static_camp import (  # noqa: E402
    DEFAULT_PROXY_WEIGHTS,
    atom_names_for_dimension,
    load_candidate_closed_loop_outcomes,
    load_candidate_reward_values,
    normalize_nonnegative,
    oracle_indices,
    reward_oracle_indices,
    robust_atom_scales,
)


def _records_from_path(path: Path) -> list[dict[str, Any]]:
    log_path = path / "camp_selection_log.json" if path.is_dir() else path
    if not log_path.is_file():
        raise FileNotFoundError(f"Selection log not found: {log_path}")
    records = json.loads(log_path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"{log_path} must contain a JSON list.")
    return records


def load_scene_training_records(
    paths: list[Path],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    features = []
    atoms = []
    feasible = []
    for path in paths:
        for record in _records_from_path(path):
            if "dp_scene_features" not in record:
                raise ValueError(
                    f"{path} contains records without dp_scene_features. "
                    "Rerun run_diffusion_planner_camp_replay.py from the "
                    "current checkout to collect scene-conditioned logs."
                )
            record_features = np.asarray(record["dp_scene_features"], dtype=np.float64)
            record_atoms = np.asarray(record["atoms"], dtype=np.float64)
            record_feasible = np.asarray(record["feasible_mask"], dtype=bool)
            if record_features.ndim != 1:
                raise ValueError(
                    f"dp_scene_features must be 1-D, got {record_features.shape}."
                )
            if record_atoms.ndim != 2:
                raise ValueError(f"atoms must be [K,R], got {record_atoms.shape}.")
            if record_feasible.shape != (record_atoms.shape[0],):
                raise ValueError(
                    "feasible_mask must match candidate count, got "
                    f"{record_feasible.shape} for atoms {record_atoms.shape}."
                )
            features.append(record_features)
            atoms.append(record_atoms)
            feasible.append(record_feasible)
    if not atoms:
        raise ValueError("No selection records were loaded.")
    return np.stack(features), np.stack(atoms), np.stack(feasible)


def load_scene_training_groups(paths: list[Path]) -> np.ndarray:
    groups = []
    for group_idx, path in enumerate(paths):
        groups.extend([group_idx] * len(_records_from_path(path)))
    if not groups:
        raise ValueError("No selection record groups were loaded.")
    return np.asarray(groups, dtype=np.int64)


def robust_feature_normalization(
    features: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    center = np.median(features, axis=0)
    q25 = np.percentile(features, 25.0, axis=0)
    q75 = np.percentile(features, 75.0, axis=0)
    scale = q75 - q25
    scale = np.nan_to_num(scale, nan=1.0, posinf=1.0, neginf=1.0)
    return center, np.maximum(scale, 1e-6)


def normalize_features(
    features: np.ndarray,
    center: np.ndarray,
    scale: np.ndarray,
    *,
    clip: float,
) -> np.ndarray:
    normalized = (features - center.reshape(1, -1)) / scale.reshape(1, -1)
    normalized = np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0)
    if clip > 0:
        normalized = np.clip(normalized, -float(clip), float(clip))
    return normalized


def _softmax(values: np.ndarray, axis: int) -> np.ndarray:
    shifted = values - np.max(values, axis=axis, keepdims=True)
    exp_values = np.exp(shifted)
    return exp_values / np.sum(exp_values, axis=axis, keepdims=True)


def _candidate_probabilities(costs: np.ndarray, feasible_mask: np.ndarray) -> np.ndarray:
    masked_costs = costs.copy()
    masked_costs[~feasible_mask] = np.inf
    all_bad = ~np.isfinite(masked_costs).any(axis=1)
    if all_bad.any():
        masked_costs[all_bad] = costs[all_bad]
    logits = -masked_costs
    logits[~np.isfinite(logits)] = -1.0e9
    return _softmax(logits, axis=1)


def train_scene_theta(
    features: np.ndarray,
    normalized_atoms: np.ndarray,
    feasible_mask: np.ndarray,
    labels: np.ndarray,
    *,
    epochs: int,
    lr: float,
    l2_reg: float,
    seed: int,
    val_fraction: float,
    group_ids: np.ndarray | None = None,
) -> tuple[np.ndarray, list[dict[str, float]], dict[str, float]]:
    rng = np.random.default_rng(seed)
    num_records, feature_dim = features.shape
    num_atoms = normalized_atoms.shape[-1]
    x_aug = np.concatenate(
        [features, np.ones((num_records, 1), dtype=np.float64)],
        axis=1,
    )

    train_group_count = 0
    val_group_count = 0
    if group_ids is not None:
        groups = np.asarray(group_ids).reshape(-1)
        if groups.shape != (num_records,):
            raise ValueError(
                f"group_ids must have shape ({num_records},), got {groups.shape}."
            )
        unique_groups = rng.permutation(np.unique(groups))
        val_group_count = int(round(unique_groups.size * float(val_fraction)))
        if unique_groups.size > 1:
            val_group_count = min(max(val_group_count, 1), unique_groups.size - 1)
        else:
            val_group_count = 0
        val_groups = unique_groups[:val_group_count]
        val_mask = np.isin(groups, val_groups)
        val_idx = np.flatnonzero(val_mask)
        train_idx = np.flatnonzero(~val_mask)
        train_group_count = int(unique_groups.size - val_group_count)
    else:
        order = rng.permutation(num_records)
        val_count = int(round(num_records * float(val_fraction)))
        if num_records > 1:
            val_count = min(max(val_count, 1), num_records - 1)
        else:
            val_count = 0
        val_idx = order[:val_count]
        train_idx = order[val_count:] if val_count else order

    theta = np.zeros((num_atoms, feature_dim + 1), dtype=np.float64)
    m = np.zeros_like(theta)
    v = np.zeros_like(theta)
    beta1 = 0.9
    beta2 = 0.999
    eps = 1e-8
    history: list[dict[str, float]] = []

    def metrics(indices: np.ndarray) -> tuple[float, float]:
        if indices.size == 0:
            return float("nan"), float("nan")
        logits = x_aug[indices] @ theta.T
        weights = _softmax(logits, axis=1)
        costs = np.einsum("nr,nkr->nk", weights, normalized_atoms[indices])
        selected = np.argmin(costs, axis=1)
        masked = costs.copy()
        masked[~feasible_mask[indices]] = np.inf
        all_bad = ~np.isfinite(masked).any(axis=1)
        if all_bad.any():
            masked[all_bad] = costs[all_bad]
        selected_masked = np.argmin(masked, axis=1)
        return (
            float(np.mean(selected == labels[indices])),
            float(np.mean(selected_masked == labels[indices])),
        )

    rows_all = np.arange(num_records)
    for epoch in range(1, int(epochs) + 1):
        logits = x_aug @ theta.T
        weights = _softmax(logits, axis=1)
        costs = np.einsum("nr,nkr->nk", weights, normalized_atoms)
        probs = _candidate_probabilities(costs, feasible_mask)

        row_probs = probs[rows_all, labels]
        loss = -np.log(row_probs[train_idx] + 1e-12).mean()
        loss += float(l2_reg) * float(np.sum(theta[:, :-1] * theta[:, :-1]))

        dcost = -probs
        dcost[rows_all, labels] += 1.0
        train_mask = np.zeros(num_records, dtype=np.float64)
        train_mask[train_idx] = 1.0 / max(train_idx.size, 1)
        dcost *= train_mask.reshape(-1, 1)

        grad_weights = np.einsum("nk,nkr->nr", dcost, normalized_atoms)
        grad_logits = weights * (
            grad_weights - np.sum(grad_weights * weights, axis=1, keepdims=True)
        )
        grad_theta = grad_logits.T @ x_aug
        grad_theta[:, :-1] += 2.0 * float(l2_reg) * theta[:, :-1]

        m = beta1 * m + (1.0 - beta1) * grad_theta
        v = beta2 * v + (1.0 - beta2) * (grad_theta * grad_theta)
        m_hat = m / (1.0 - beta1**epoch)
        v_hat = v / (1.0 - beta2**epoch)
        theta -= float(lr) * m_hat / (np.sqrt(v_hat) + eps)

        if epoch == 1 or epoch == epochs or epoch % 100 == 0:
            train_match, train_masked_match = metrics(train_idx)
            val_match, val_masked_match = metrics(val_idx)
            history.append(
                {
                    "epoch": float(epoch),
                    "loss": float(loss),
                    "train_oracle_match_rate": train_match,
                    "train_masked_oracle_match_rate": train_masked_match,
                    "val_oracle_match_rate": val_match,
                    "val_masked_oracle_match_rate": val_masked_match,
                }
            )

    train_match, train_masked_match = metrics(train_idx)
    val_match, val_masked_match = metrics(val_idx)
    final = {
        "train_records": float(train_idx.size),
        "val_records": float(val_idx.size),
        "train_groups": float(train_group_count),
        "val_groups": float(val_group_count),
        "train_oracle_match_rate": train_match,
        "train_masked_oracle_match_rate": train_masked_match,
        "val_oracle_match_rate": val_match,
        "val_masked_oracle_match_rate": val_masked_match,
    }
    return theta, history, final


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train a Diffusion-Planner-compatible scene-conditioned CAMP Theta "
            "from replay candidate atoms and logged DP input features."
        )
    )
    parser.add_argument("--selection_log", type=Path, action="append", required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=1000)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--l2_reg", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--val_fraction", type=float, default=0.2)
    parser.add_argument("--scale_percentile", type=float, default=95.0)
    parser.add_argument("--feature_clip", type=float, default=5.0)
    parser.add_argument(
        "--label_source",
        choices=("dp_reward", "closed_loop_outcome", "proxy"),
        default="dp_reward",
    )
    parser.add_argument(
        "--reward_key",
        type=str,
        default="quality_without_progress",
    )
    parser.add_argument("--reward_progress_weight", type=float, default=2.0)
    parser.add_argument(
        "--outcome_key",
        type=str,
        default="value",
        help="Candidate closed-loop outcome field to maximize.",
    )
    parser.add_argument(
        "--proxy_weights",
        type=str,
        default="",
        help="Optional JSON list of 9 proxy weights before simplex projection.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    features, atoms, feasible = load_scene_training_records(args.selection_log)
    group_ids = load_scene_training_groups(args.selection_log)
    atom_names = atom_names_for_dimension(atoms.shape[-1])

    proxy_weights = None
    dropped_records = 0
    candidate_rewards = None
    closed_loop_outcomes = None
    if args.label_source == "dp_reward":
        candidate_rewards = load_candidate_reward_values(
            args.selection_log,
            reward_key=args.reward_key,
            progress_weight=args.reward_progress_weight,
        )
        if candidate_rewards.shape != feasible.shape:
            raise ValueError(
                "Candidate reward shape must match feasible_mask, "
                f"got {candidate_rewards.shape} and {feasible.shape}."
            )
        valid = feasible.any(axis=1) & np.isfinite(candidate_rewards).any(axis=1)
        dropped_records = int(np.sum(~valid))
        features = features[valid]
        atoms = atoms[valid]
        feasible = feasible[valid]
        group_ids = group_ids[valid]
        candidate_rewards = candidate_rewards[valid]
        if not atoms.shape[0]:
            raise ValueError("No reward-labeled records contain a feasible candidate.")
    elif args.label_source == "closed_loop_outcome":
        closed_loop_outcomes, outcome_feasible = load_candidate_closed_loop_outcomes(
            args.selection_log,
            outcome_key=args.outcome_key,
        )
        if closed_loop_outcomes.shape != feasible.shape:
            raise ValueError(
                "Candidate outcome shape must match feasible_mask, "
                f"got {closed_loop_outcomes.shape} and {feasible.shape}."
            )
        if outcome_feasible.shape != feasible.shape:
            raise ValueError(
                "Candidate outcome feasible shape must match feasible_mask, "
                f"got {outcome_feasible.shape} and {feasible.shape}."
            )
        finite_feasible = np.isfinite(closed_loop_outcomes) & outcome_feasible
        valid = outcome_feasible.any(axis=1) & finite_feasible.any(axis=1)
        dropped_records = int(np.sum(~valid))
        features = features[valid]
        atoms = atoms[valid]
        feasible = outcome_feasible[valid]
        group_ids = group_ids[valid]
        closed_loop_outcomes = closed_loop_outcomes[valid]
        if not atoms.shape[0]:
            raise ValueError("No closed-loop outcome records contain a feasible candidate.")
    else:
        if args.proxy_weights:
            proxy_weights = np.asarray(json.loads(args.proxy_weights), dtype=np.float64)
        else:
            proxy_weights = DEFAULT_PROXY_WEIGHTS[: len(atom_names)]
        if proxy_weights.shape != (len(atom_names),):
            raise ValueError(
                f"proxy_weights must have {len(atom_names)} entries, "
                f"got {proxy_weights.shape}."
            )

    atom_scales = robust_atom_scales(atoms, args.scale_percentile)
    normalized_atoms = np.clip(
        np.nan_to_num(atoms / atom_scales.reshape(1, 1, -1)),
        0.0,
        10.0,
    )
    labels = (
        reward_oracle_indices(candidate_rewards, feasible)
        if candidate_rewards is not None
        else (
            reward_oracle_indices(closed_loop_outcomes, feasible)
            if closed_loop_outcomes is not None
            else oracle_indices(normalized_atoms, feasible, proxy_weights)
        )
    )

    feature_center, feature_scale = robust_feature_normalization(features)
    normalized_features = normalize_features(
        features,
        feature_center,
        feature_scale,
        clip=args.feature_clip,
    )
    theta, history, final_metrics = train_scene_theta(
        normalized_features,
        normalized_atoms,
        feasible,
        labels,
        epochs=args.epochs,
        lr=args.lr,
        l2_reg=args.l2_reg,
        seed=args.seed,
        val_fraction=args.val_fraction,
        group_ids=group_ids,
    )

    logits = np.concatenate(
        [normalized_features, np.ones((normalized_features.shape[0], 1))],
        axis=1,
    ) @ theta.T
    offline_weights = _softmax(logits, axis=1).mean(axis=0)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "camp_dp_scene_theta.npz"
    scales_path = args.output_dir / "atom_scales_dp_scene_theta.json"
    normalization_path = args.output_dir / "feature_normalization_dp_scene_theta.json"
    summary_path = args.output_dir / "training_summary.json"

    np.savez(
        checkpoint_path,
        Theta=theta.astype(np.float64),
        offline_weights=offline_weights.astype(np.float64),
        feature_center=feature_center.astype(np.float64),
        feature_scale=feature_scale.astype(np.float64),
        feature_clip=np.asarray(float(args.feature_clip), dtype=np.float64),
        linear_activation=np.asarray("softmax"),
    )
    scales_path.write_text(
        json.dumps(atom_scales.tolist(), indent=2) + "\n",
        encoding="utf-8",
    )
    normalization = {
        "feature_names": list(DP_SCENE_FEATURE_NAMES),
        "feature_center": feature_center.tolist(),
        "feature_scale": feature_scale.tolist(),
        "feature_clip": float(args.feature_clip),
    }
    normalization_path.write_text(
        json.dumps(normalization, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = {
        "training_type": "diffusion_planner_scene_conditioned_theta_preference",
        "label_source": args.label_source,
        "reward_key": args.reward_key if args.label_source == "dp_reward" else None,
        "outcome_key": (
            args.outcome_key if args.label_source == "closed_loop_outcome" else None
        ),
        "reward_progress_weight": (
            args.reward_progress_weight
            if args.label_source == "dp_reward"
            and args.reward_key == "quality_without_progress"
            else None
        ),
        "selection_logs": [str(path) for path in args.selection_log],
        "num_records": int(features.shape[0]),
        "dropped_records_without_feasible_candidate": dropped_records,
        "num_candidates": int(atoms.shape[1]),
        "num_atoms": int(atoms.shape[2]),
        "feature_dim": int(features.shape[1]),
        "atom_names": list(atom_names),
        "feature_names": list(DP_SCENE_FEATURE_NAMES),
        "scale_percentile": float(args.scale_percentile),
        "feature_clip": float(args.feature_clip),
        "proxy_weights_normalized": (
            normalize_nonnegative(proxy_weights).tolist()
            if proxy_weights is not None
            else None
        ),
        "offline_weights_mean": offline_weights.tolist(),
        "checkpoint_path": str(checkpoint_path),
        "atom_scales_path": str(scales_path),
        "feature_normalization_path": str(normalization_path),
        "history": history,
        "final_metrics": final_metrics,
        "caveat": (
            "Theta is trained from short-horizon candidate-branch closed-loop "
            "outcomes. Matched closed-loop baselines remain required for final "
            "claims."
            if args.label_source == "closed_loop_outcome"
            else (
                "Theta is trained from candidate-level DP reward preferences, not "
                "counterfactual closed-loop outcomes. Matched closed-loop baselines "
                "remain required for final claims."
            )
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
