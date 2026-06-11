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
    CAMP_ATOM_NAMES,
    DP_CAMP_ATOM_NAMES,
)


DEFAULT_PROXY_WEIGHTS = np.array(
    [
        0.75,
        0.75,
        0.75,
        0.50,
        1.50,
        1.00,
        0.75,
        2.00,
        3.00,
        2.00,
    ],
    dtype=np.float64,
)


def _records_from_path(path: Path) -> list[dict[str, Any]]:
    log_path = path / "camp_selection_log.json" if path.is_dir() else path
    if not log_path.is_file():
        raise FileNotFoundError(f"Selection log not found: {log_path}")
    records = json.loads(log_path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"{log_path} must contain a JSON list.")
    return records


def load_training_records(paths: list[Path]) -> tuple[np.ndarray, np.ndarray]:
    atoms = []
    feasible = []
    for path in paths:
        for record in _records_from_path(path):
            record_atoms = np.asarray(record["atoms"], dtype=np.float64)
            record_feasible = np.asarray(record["feasible_mask"], dtype=bool)
            if record_atoms.ndim != 2:
                raise ValueError(f"atoms must be [K,R], got {record_atoms.shape}.")
            if record_feasible.shape != (record_atoms.shape[0],):
                raise ValueError(
                    "feasible_mask must match candidate count, got "
                    f"{record_feasible.shape} for atoms {record_atoms.shape}."
                )
            atoms.append(record_atoms)
            feasible.append(record_feasible)
    if not atoms:
        raise ValueError("No selection records were loaded.")
    return np.stack(atoms), np.stack(feasible)


def load_candidate_reward_values(
    paths: list[Path],
    reward_key: str = "total",
) -> np.ndarray:
    values = []
    for path in paths:
        for record in _records_from_path(path):
            candidate_rewards = record.get("dp_candidate_rewards")
            if not isinstance(candidate_rewards, list):
                raise ValueError(
                    f"{path} contains records without dp_candidate_rewards. "
                    "Collect logs with --camp_feasibility_source dp_reward."
                )
            record_values = []
            for reward in candidate_rewards:
                if reward_key not in reward:
                    raise ValueError(
                        f"Candidate reward in {path} has no {reward_key!r} field."
                    )
                record_values.append(float(reward[reward_key]))
            values.append(record_values)
    if not values:
        raise ValueError("No candidate reward records were loaded.")
    return np.asarray(values, dtype=np.float64)


def robust_atom_scales(atoms: np.ndarray, percentile: float) -> np.ndarray:
    scales = np.percentile(np.reshape(atoms, (-1, atoms.shape[-1])), percentile, axis=0)
    scales = np.nan_to_num(scales, nan=1.0, posinf=1.0, neginf=1.0)
    return np.maximum(scales, 1e-6)


def normalize_nonnegative(values: np.ndarray) -> np.ndarray:
    weights = np.asarray(values, dtype=np.float64).reshape(-1)
    weights = np.nan_to_num(weights, nan=0.0, posinf=0.0, neginf=0.0)
    weights = np.maximum(weights, 0.0)
    total = float(weights.sum())
    if total <= 0.0:
        return np.full(weights.shape[0], 1.0 / weights.shape[0], dtype=np.float64)
    return weights / total


def atom_names_for_dimension(num_atoms: int) -> tuple[str, ...]:
    if num_atoms == len(CAMP_ATOM_NAMES):
        return CAMP_ATOM_NAMES
    if num_atoms == len(DP_CAMP_ATOM_NAMES):
        return DP_CAMP_ATOM_NAMES
    raise ValueError(
        f"Expected {len(CAMP_ATOM_NAMES)} legacy atoms or "
        f"{len(DP_CAMP_ATOM_NAMES)} DP atoms, got {num_atoms}."
    )


def oracle_indices(
    normalized_atoms: np.ndarray,
    feasible_mask: np.ndarray,
    proxy_weights: np.ndarray,
) -> np.ndarray:
    proxy = normalize_nonnegative(proxy_weights)
    costs = normalized_atoms @ proxy
    masked = costs.copy()
    masked[~feasible_mask] = np.inf
    all_bad = ~np.isfinite(masked).any(axis=1)
    if all_bad.any():
        masked[all_bad] = costs[all_bad]
    return np.argmin(masked, axis=1)


def reward_oracle_indices(
    candidate_rewards: np.ndarray,
    feasible_mask: np.ndarray,
) -> np.ndarray:
    rewards = np.asarray(candidate_rewards, dtype=np.float64)
    feasible = np.asarray(feasible_mask, dtype=bool)
    if rewards.shape != feasible.shape:
        raise ValueError(
            "candidate_rewards and feasible_mask must have the same shape, "
            f"got {rewards.shape} and {feasible.shape}."
        )
    masked = rewards.copy()
    masked[~feasible] = -np.inf
    all_bad = ~np.isfinite(masked).any(axis=1)
    if all_bad.any():
        masked[all_bad] = rewards[all_bad]
    return np.argmax(masked, axis=1)


def train_static_weights(
    normalized_atoms: np.ndarray,
    labels: np.ndarray,
    *,
    epochs: int,
    lr: float,
    l2_reg: float,
    feasible_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, list[dict[str, float]]]:
    logits = np.zeros(normalized_atoms.shape[-1], dtype=np.float64)
    history = []
    num_records = normalized_atoms.shape[0]
    rows = np.arange(num_records)
    feasible = (
        np.ones(normalized_atoms.shape[:2], dtype=bool)
        if feasible_mask is None
        else np.asarray(feasible_mask, dtype=bool)
    )
    if feasible.shape != normalized_atoms.shape[:2]:
        raise ValueError(
            "feasible_mask must match [N,K], "
            f"got {feasible.shape} for atoms {normalized_atoms.shape}."
        )
    if not feasible.any(axis=1).all():
        raise ValueError("Each training record must contain a feasible candidate.")

    for epoch in range(epochs):
        shifted = logits - np.max(logits)
        exp_logits = np.exp(shifted)
        weights = exp_logits / np.sum(exp_logits)

        costs = normalized_atoms @ weights
        masked_logits = -costs
        masked_logits[~feasible] = -np.inf
        shifted_logits = masked_logits - np.max(masked_logits, axis=1, keepdims=True)
        pred_probs = np.exp(shifted_logits)
        pred_probs /= np.sum(pred_probs, axis=1, keepdims=True)
        loss = -np.log(pred_probs[rows, labels] + 1e-12).mean()
        loss += float(l2_reg) * float(np.sum((weights - 1.0 / len(weights)) ** 2))

        expected_atoms = np.einsum("nk,nkr->nr", pred_probs, normalized_atoms)
        chosen_atoms = normalized_atoms[rows, labels]
        grad_weights = (chosen_atoms - expected_atoms).mean(axis=0)
        grad_weights += 2.0 * float(l2_reg) * (weights - 1.0 / len(weights))
        grad_logits = weights * (grad_weights - float(np.dot(grad_weights, weights)))
        logits -= float(lr) * grad_logits

        if epoch == 0 or epoch == epochs - 1 or (epoch + 1) % 100 == 0:
            masked_costs = costs.copy()
            masked_costs[~feasible] = np.inf
            selected = np.argmin(masked_costs, axis=1)
            accuracy = float(np.mean(selected == labels))
            history.append(
                {
                    "epoch": float(epoch + 1),
                    "loss": float(loss),
                    "oracle_match_rate": accuracy,
                }
            )

    shifted = logits - np.max(logits)
    weights = np.exp(shifted)
    weights /= np.sum(weights)
    return weights, history


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Calibrate static CAMP weights from Diffusion Planner replay "
            "candidate atoms and candidate-level DP rewards."
        )
    )
    parser.add_argument("--selection_log", type=Path, action="append", required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=1000)
    parser.add_argument("--lr", type=float, default=0.2)
    parser.add_argument("--l2_reg", type=float, default=0.01)
    parser.add_argument("--scale_percentile", type=float, default=95.0)
    parser.add_argument(
        "--label_source",
        choices=("dp_reward", "proxy"),
        default="dp_reward",
    )
    parser.add_argument("--reward_key", type=str, default="total")
    parser.add_argument(
        "--proxy_weights",
        type=str,
        default="",
        help="Optional JSON list of 9 proxy weights before simplex projection.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    atoms, feasible = load_training_records(args.selection_log)
    atom_names = atom_names_for_dimension(atoms.shape[-1])
    scales = robust_atom_scales(atoms, args.scale_percentile)
    normalized = np.clip(np.nan_to_num(atoms / scales.reshape(1, 1, -1)), 0.0, 10.0)

    proxy_weights = None
    dropped_records = 0
    if args.label_source == "dp_reward":
        candidate_rewards = load_candidate_reward_values(
            args.selection_log,
            reward_key=args.reward_key,
        )
        if candidate_rewards.shape != feasible.shape:
            raise ValueError(
                "Candidate reward shape must match feasible_mask, "
                f"got {candidate_rewards.shape} and {feasible.shape}."
            )
        valid = feasible.any(axis=1) & np.isfinite(candidate_rewards).any(axis=1)
        dropped_records = int(np.sum(~valid))
        normalized = normalized[valid]
        feasible = feasible[valid]
        candidate_rewards = candidate_rewards[valid]
        if not normalized.shape[0]:
            raise ValueError("No reward-labeled records contain a feasible candidate.")
        labels = reward_oracle_indices(candidate_rewards, feasible)
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
        labels = oracle_indices(normalized, feasible, proxy_weights)
    weights, history = train_static_weights(
        normalized,
        labels,
        epochs=args.epochs,
        lr=args.lr,
        l2_reg=args.l2_reg,
        feasible_mask=feasible,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    weights_path = args.output_dir / "offline_weights_dp_static.npy"
    scales_path = args.output_dir / "atom_scales_dp_static.json"
    summary_path = args.output_dir / "training_summary.json"

    np.save(weights_path, weights.astype(np.float64))
    scales_path.write_text(json.dumps(scales.tolist(), indent=2) + "\n", encoding="utf-8")
    costs = normalized @ weights
    masked_costs = costs.copy()
    masked_costs[~feasible] = np.inf
    selected = np.argmin(masked_costs, axis=1)
    summary = {
        "training_type": "diffusion_planner_static_candidate_preference",
        "label_source": args.label_source,
        "reward_key": args.reward_key if args.label_source == "dp_reward" else None,
        "selection_logs": [str(path) for path in args.selection_log],
        "num_records": int(normalized.shape[0]),
        "dropped_records_without_feasible_candidate": dropped_records,
        "num_candidates": int(normalized.shape[1]),
        "num_atoms": int(normalized.shape[2]),
        "atom_names": list(atom_names),
        "scale_percentile": float(args.scale_percentile),
        "proxy_weights_normalized": (
            normalize_nonnegative(proxy_weights).tolist()
            if proxy_weights is not None
            else None
        ),
        "trained_weights": weights.tolist(),
        "oracle_match_rate": float(np.mean(selected == labels)),
        "feasible_candidate_rate": float(np.mean(feasible)),
        "records_with_any_infeasible": int(np.sum(~feasible.all(axis=1))),
        "weights_path": str(weights_path),
        "atom_scales_path": str(scales_path),
        "history": history,
        "caveat": (
            "Candidate-level DP rewards are model-based preferences, not "
            "counterfactual closed-loop outcomes. Closed-loop matched baselines "
            "remain required for final claims."
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
