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
    DEFAULT_CLOSED_LOOP_OUTCOME_WEIGHTS,
    atom_schema_for_dimension,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SAFETY_COST_V1_CLIP,
    SAFETY_COST_V1_NORMALIZATION,
    SAFETY_COST_V1_WEIGHTS,
)
from scripts.integrations.validate_dp_native_training_data_contract import (  # noqa: E402
    validate_logs as validate_dp_native_training_data_contract,
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
        4.00,
        1.50,
    ],
    dtype=np.float64,
)

OUTCOME_WEIGHT_TO_FIELD = {
    "progress": "progress_m",
    "collision": "collision",
    "near_miss": "near_miss",
    "lane_violation": "lane_violation",
    "red_light": "red_light_violation",
    "mean_jerk": "mean_jerk_mps3",
    "mean_lateral_acceleration": "mean_lateral_acceleration_mps2",
}
SAFETY_COST_V1_BOOL_FIELDS = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
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
    progress_weight: float = 2.0,
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
                if reward_key == "quality_without_progress":
                    if "total" not in reward or "progress" not in reward:
                        raise ValueError(
                            f"Candidate reward in {path} needs total and progress "
                            "for quality_without_progress."
                        )
                    value = float(reward["total"]) - float(progress_weight) * float(
                        reward["progress"]
                    )
                elif reward_key in reward:
                    value = float(reward[reward_key])
                else:
                    raise ValueError(
                        f"Candidate reward in {path} has no {reward_key!r} field."
                    )
                record_values.append(value)
            values.append(record_values)
    if not values:
        raise ValueError("No candidate reward records were loaded.")
    return np.asarray(values, dtype=np.float64)


def load_candidate_closed_loop_outcomes(
    paths: list[Path],
    outcome_key: str = "value",
    outcome_weights: dict[str, float] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    values = []
    feasible = []
    for path in paths:
        for record in _records_from_path(path):
            outcomes = record.get("candidate_closed_loop_outcomes")
            if not isinstance(outcomes, list):
                raise ValueError(
                    f"{path} contains records without candidate_closed_loop_outcomes. "
                    "Collect logs with --camp_collect_closed_loop_outcomes."
                )
            record_values = []
            record_feasible = []
            for outcome in outcomes:
                if outcome_weights is None:
                    if outcome_key not in outcome:
                        raise ValueError(
                            f"Candidate outcome in {path} has no {outcome_key!r} field."
                        )
                    value = float(outcome[outcome_key])
                else:
                    value = weighted_closed_loop_outcome_value(outcome, outcome_weights)
                record_values.append(value)
                record_feasible.append(bool(outcome.get("feasible", True)))
            values.append(record_values)
            feasible.append(record_feasible)
    if not values:
        raise ValueError("No candidate closed-loop outcome records were loaded.")
    return np.asarray(values, dtype=np.float64), np.asarray(feasible, dtype=bool)


def load_candidate_safety_cost_v1_values(
    paths: list[Path],
) -> tuple[np.ndarray, np.ndarray]:
    values = []
    feasible = []
    for path in paths:
        for record in _records_from_path(path):
            outcomes = record.get("candidate_closed_loop_outcomes")
            if not isinstance(outcomes, list):
                raise ValueError(
                    f"{path} contains records without candidate_closed_loop_outcomes. "
                    "Collect logs with --camp_collect_closed_loop_outcomes."
                )
            candidate_count = len(outcomes)
            record_feasible = np.asarray(
                record.get("feasible_mask"),
                dtype=bool,
            ).reshape(-1)
            if record_feasible.shape != (candidate_count,):
                raise ValueError(
                    "feasible_mask must match candidate outcomes, got "
                    f"{record_feasible.shape} and {candidate_count}."
                )
            branch_feasible = (
                record_feasible
                if bool(record_feasible.any())
                else np.ones(candidate_count, dtype=bool)
            )
            planned_red = _candidate_planned_red_values(record, candidate_count)
            progress = np.asarray(
                [
                    _outcome_nonnegative_float(outcome, "progress_m")
                    for outcome in outcomes
                ],
                dtype=np.float64,
            )
            progress_ref = (
                float(np.max(progress[branch_feasible]))
                if branch_feasible.any()
                else float(np.max(progress))
            )
            progress_denom = max(progress_ref, 1.0)
            top1 = outcomes[0]
            record_values = []
            record_feasible_mask = []
            for index, outcome in enumerate(outcomes):
                cost = _candidate_safety_cost_v1(
                    outcome,
                    planned_red=float(planned_red[index]),
                    progress_ref=progress_ref,
                    progress_denom=progress_denom,
                )
                record_values.append(-cost)
                outcome_feasible = bool(outcome.get("feasible", True))
                hard_nonworse = all(
                    float(bool(outcome[field])) <= float(bool(top1[field]))
                    for field in SAFETY_COST_V1_BOOL_FIELDS
                )
                record_feasible_mask.append(
                    bool(branch_feasible[index] and outcome_feasible and hard_nonworse)
                )
            values.append(record_values)
            feasible.append(record_feasible_mask)
    if not values:
        raise ValueError("No candidate SafetyCost v1 records were loaded.")
    return np.asarray(values, dtype=np.float64), np.asarray(feasible, dtype=bool)


def _candidate_safety_cost_v1(
    outcome: dict[str, Any],
    *,
    planned_red: float,
    progress_ref: float,
    progress_denom: float,
) -> float:
    raw_components = {
        "collision": float(bool(outcome["collision"])),
        "near_miss": float(bool(outcome["near_miss"])),
        "lane_violation": float(bool(outcome["lane_violation"])),
        "realized_red_light": float(bool(outcome["red_light_violation"])),
        "planned_red_light": min(max(float(planned_red), 0.0), 1.0),
        "mean_jerk": min(
            _outcome_nonnegative_float(outcome, "mean_jerk_mps3")
            / SAFETY_COST_V1_NORMALIZATION["mean_jerk_magnitude_mps3"],
            SAFETY_COST_V1_CLIP,
        ),
        "mean_lateral_acceleration": min(
            _outcome_nonnegative_float(outcome, "mean_lateral_acceleration_mps2")
            / SAFETY_COST_V1_NORMALIZATION["mean_lateral_acceleration_mps2"],
            SAFETY_COST_V1_CLIP,
        ),
        "route_shortfall": min(
            max(
                (
                    float(progress_ref)
                    - _outcome_nonnegative_float(outcome, "progress_m")
                )
                / float(progress_denom),
                0.0,
            ),
            1.0,
        ),
    }
    return float(
        sum(
            float(raw_components[key]) * SAFETY_COST_V1_WEIGHTS[key]
            for key in raw_components
        )
    )


def _candidate_planned_red_values(record: dict[str, Any], size: int) -> np.ndarray:
    for key in (
        "candidate_horizon_union_planned_red_light_cost",
        "candidate_full_horizon_planned_red_light_cost",
    ):
        values = record.get(key)
        if values is not None:
            vector = np.asarray(values, dtype=np.float64).reshape(-1)
            if vector.shape != (size,):
                raise ValueError(f"{key} must have shape [{size}].")
            if not np.all(np.isfinite(vector)) or np.any(vector < 0.0):
                raise ValueError(f"{key} must contain finite nonnegative values.")
            return vector
    return np.zeros(size, dtype=np.float64)


def _outcome_nonnegative_float(outcome: dict[str, Any], field: str) -> float:
    try:
        value = float(outcome[field])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"Candidate outcome field {field!r} must be numeric.") from None
    if not np.isfinite(value) or value < 0.0:
        raise ValueError(
            f"Candidate outcome field {field!r} must be finite and nonnegative."
        )
    return value


def load_outcome_weights(path: Path | None) -> dict[str, float] | None:
    if path is None:
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    weights = dict(DEFAULT_CLOSED_LOOP_OUTCOME_WEIGHTS)
    for key, value in raw.items():
        if key not in weights:
            raise ValueError(
                f"Unknown outcome weight {key!r}; expected one of "
                f"{sorted(weights)}."
            )
        weights[key] = float(value)
    return {key: float(value) for key, value in weights.items()}


def weighted_closed_loop_outcome_value(
    outcome: dict[str, Any],
    weights: dict[str, float],
) -> float:
    missing = [
        field
        for key, field in OUTCOME_WEIGHT_TO_FIELD.items()
        if key in weights and field not in outcome
    ]
    if missing:
        raise ValueError(f"Candidate outcome is missing fields: {missing}.")
    return (
        weights["progress"] * float(outcome["progress_m"])
        - weights["collision"] * float(bool(outcome["collision"]))
        - weights["near_miss"] * float(bool(outcome["near_miss"]))
        - weights["lane_violation"] * float(bool(outcome["lane_violation"]))
        - weights["red_light"] * float(bool(outcome["red_light_violation"]))
        - weights["mean_jerk"] * float(outcome["mean_jerk_mps3"])
        - weights["mean_lateral_acceleration"]
        * float(outcome["mean_lateral_acceleration_mps2"])
    )


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
    return atom_schema_for_dimension(num_atoms)[1]


def validate_atom_schema(
    paths: list[Path],
    expected_atom_names: tuple[str, ...],
    *,
    require: bool,
) -> dict[str, Any]:
    expected_version, canonical_names = atom_schema_for_dimension(
        len(expected_atom_names)
    )
    if tuple(expected_atom_names) != canonical_names:
        raise ValueError("Expected atom names do not match the canonical schema.")

    verified_records = 0
    missing_records = 0
    for path in paths:
        for record_idx, record in enumerate(_records_from_path(path)):
            version = record.get("atom_schema_version")
            names = record.get("atom_names")
            if version is None and names is None:
                missing_records += 1
                if require:
                    raise ValueError(
                        f"{path} record {record_idx} has no atom schema metadata."
                    )
                continue
            if version is None or names is None:
                raise ValueError(
                    f"{path} record {record_idx} has incomplete atom schema metadata."
                )
            if str(version) != expected_version or tuple(names) != canonical_names:
                raise ValueError(
                    f"{path} record {record_idx} uses atom schema "
                    f"{version!r} with names {tuple(names)!r}; expected "
                    f"{expected_version!r} with names {canonical_names!r}."
                )
            verified_records += 1

    return {
        "version": expected_version,
        "atom_names": list(canonical_names),
        "required": bool(require),
        "verified_records": verified_records,
        "missing_records": missing_records,
    }


def _run_dp_native_training_data_contract_preflight(
    selection_logs: list[Path],
    *,
    required: bool,
) -> dict[str, Any] | None:
    if not required:
        return None
    report = validate_dp_native_training_data_contract(selection_logs)
    if not bool(report.get("passed")):
        failed_count = len(report.get("failed_records", []))
        raise ValueError(
            "DP-native training data contract validation failed before "
            f"training; failed_records={failed_count}."
        )
    return report


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
        choices=(
            "dp_reward",
            "closed_loop_outcome",
            "safety_cost_v1_hard_guarded",
            "proxy",
        ),
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
        "--outcome_weights",
        type=Path,
        default=None,
        help=(
            "Optional JSON outcome-weight object. When set with "
            "--label_source closed_loop_outcome, recomputes labels from "
            "candidate_closed_loop_outcomes components instead of using "
            "--outcome_key."
        ),
    )
    parser.add_argument(
        "--proxy_weights",
        type=str,
        default="",
        help="Optional JSON list of 9 proxy weights before simplex projection.",
    )
    parser.add_argument(
        "--require_atom_schema",
        action="store_true",
        help="Reject selection records without the exact ordered atom schema.",
    )
    parser.add_argument(
        "--require_dp_native_training_data_contract",
        action="store_true",
        help=(
            "Fail closed before training unless every selection log passes the "
            "read-only DP-native candidate provenance training-data contract."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dp_native_training_data_contract = _run_dp_native_training_data_contract_preflight(
        args.selection_log,
        required=bool(args.require_dp_native_training_data_contract),
    )
    atoms, feasible = load_training_records(args.selection_log)
    atom_names = atom_names_for_dimension(atoms.shape[-1])
    atom_schema = validate_atom_schema(
        args.selection_log,
        atom_names,
        require=args.require_atom_schema,
    )

    proxy_weights = None
    candidate_rewards = None
    closed_loop_outcomes = None
    outcome_weights = load_outcome_weights(args.outcome_weights)
    if outcome_weights is not None and args.label_source != "closed_loop_outcome":
        raise ValueError("--outcome_weights requires --label_source closed_loop_outcome.")
    dropped_records = 0
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
        atoms = atoms[valid]
        feasible = feasible[valid]
        candidate_rewards = candidate_rewards[valid]
        if not atoms.shape[0]:
            raise ValueError("No reward-labeled records contain a feasible candidate.")
    elif args.label_source == "closed_loop_outcome":
        closed_loop_outcomes, outcome_feasible = load_candidate_closed_loop_outcomes(
            args.selection_log,
            outcome_key=args.outcome_key,
            outcome_weights=outcome_weights,
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
        atoms = atoms[valid]
        feasible = outcome_feasible[valid]
        closed_loop_outcomes = closed_loop_outcomes[valid]
        if not atoms.shape[0]:
            raise ValueError("No closed-loop outcome records contain a feasible candidate.")
    elif args.label_source == "safety_cost_v1_hard_guarded":
        closed_loop_outcomes, outcome_feasible = load_candidate_safety_cost_v1_values(
            args.selection_log,
        )
        if closed_loop_outcomes.shape != feasible.shape:
            raise ValueError(
                "Candidate SafetyCost shape must match feasible_mask, "
                f"got {closed_loop_outcomes.shape} and {feasible.shape}."
            )
        if outcome_feasible.shape != feasible.shape:
            raise ValueError(
                "Candidate SafetyCost feasible shape must match feasible_mask, "
                f"got {outcome_feasible.shape} and {feasible.shape}."
            )
        finite_feasible = np.isfinite(closed_loop_outcomes) & outcome_feasible
        valid = finite_feasible.any(axis=1)
        dropped_records = int(np.sum(~valid))
        atoms = atoms[valid]
        feasible = outcome_feasible[valid]
        closed_loop_outcomes = closed_loop_outcomes[valid]
        if not atoms.shape[0]:
            raise ValueError(
                "No SafetyCost v1 records contain a hard-guarded feasible candidate."
            )
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

    scales = robust_atom_scales(atoms, args.scale_percentile)
    normalized = np.clip(
        np.nan_to_num(atoms / scales.reshape(1, 1, -1)),
        0.0,
        10.0,
    )
    labels = (
        reward_oracle_indices(candidate_rewards, feasible)
        if candidate_rewards is not None
        else (
            reward_oracle_indices(closed_loop_outcomes, feasible)
            if closed_loop_outcomes is not None
            else oracle_indices(normalized, feasible, proxy_weights)
        )
    )
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
    atom_schema_version, canonical_atom_names = atom_schema_for_dimension(
        len(atom_names)
    )
    scales_path.write_text(
        json.dumps(
            {
                "atom_schema_version": atom_schema_version,
                "atom_names": list(canonical_atom_names),
                "scales": scales.tolist(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    costs = normalized @ weights
    masked_costs = costs.copy()
    masked_costs[~feasible] = np.inf
    selected = np.argmin(masked_costs, axis=1)
    summary = {
        "training_type": "diffusion_planner_static_candidate_preference",
        "label_source": args.label_source,
        "reward_key": args.reward_key if args.label_source == "dp_reward" else None,
        "outcome_key": (
            (
                args.outcome_key
                if args.label_source == "closed_loop_outcome"
                and outcome_weights is None
                else None
            )
        ),
        "outcome_weights_path": (
            str(args.outcome_weights)
            if args.label_source == "closed_loop_outcome" and outcome_weights is not None
            else None
        ),
        "outcome_weights": (
            outcome_weights
            if args.label_source == "closed_loop_outcome" and outcome_weights is not None
            else None
        ),
        "reward_progress_weight": (
            args.reward_progress_weight
            if args.label_source == "dp_reward"
            and args.reward_key == "quality_without_progress"
            else None
        ),
        "selection_logs": [str(path) for path in args.selection_log],
        "num_records": int(normalized.shape[0]),
        "dropped_records_without_feasible_candidate": dropped_records,
        "num_candidates": int(normalized.shape[1]),
        "num_atoms": int(normalized.shape[2]),
        "atom_schema_version": atom_schema_version,
        "atom_names": list(atom_names),
        "atom_schema": atom_schema,
        "dp_native_training_data_contract": dp_native_training_data_contract,
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
            "Closed-loop outcome labels are short-horizon candidate-branch "
            "evaluations. Matched closed-loop baselines remain required for "
            "final claims."
            if args.label_source == "closed_loop_outcome"
            else (
                "Hard-guarded SafetyCost v1 labels are offline candidate-branch "
                "training targets. Runtime CAMP atoms must not use future "
                "outcomes, and matched closed-loop baselines remain required "
                "for final claims."
                if args.label_source == "safety_cost_v1_hard_guarded"
                else (
                    "Candidate-level DP rewards are model-based preferences, not "
                    "counterfactual closed-loop outcomes. Closed-loop matched "
                    "baselines remain required for final claims."
                )
            )
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
