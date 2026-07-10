#!/usr/bin/env python3
from __future__ import annotations

from typing import Mapping

import numpy as np


TRAINING_SEED = 3408
TIE_SEED = 3409
BOOTSTRAP_SEED = 3410
FORBIDDEN_SEEDS = (11, 12, 13)

SCALE_PERCENTILE = 95.0
MARGIN_SCALE = 0.1
MARGIN_CLIP = 2.0
CVAR_ALPHA = 0.9
L2_REG = 1e-4
MAX_ITER = 20
TOLERANCE = 1e-6
SOLVER = "CLARABEL"

MISS_THRESHOLD_M = 2.0
ADE_TIE_TOLERANCE_M = 1e-9
SCORE_TIE_TOLERANCE = 1e-12
BOOTSTRAP_REPLICATES = 10_000

BASELINE_INDEX = 0
BASELINE_SEMANTICS = "fixed_dp_deterministic_map_baseline"
NATIVE_RANKED_TOP1 = False


def tie_priority(candidate_count: int, *, seed: int = TIE_SEED) -> np.ndarray:
    if candidate_count <= 0:
        raise ValueError("candidate_count must be positive")
    if seed in FORBIDDEN_SEEDS:
        raise ValueError("formal seeds 11/12/13 are forbidden")
    order = np.random.default_rng(seed).permutation(candidate_count)
    priority = np.empty(candidate_count, dtype=np.int64)
    priority[order] = np.arange(candidate_count, dtype=np.int64)
    return priority


def candidate_ade_fde(
    candidates: np.ndarray, expert_future_xyh: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    trajectories = np.asarray(candidates, dtype=np.float64)
    expert = np.asarray(expert_future_xyh, dtype=np.float64)
    if trajectories.ndim != 3 or trajectories.shape[2] < 2:
        raise ValueError("candidates must have shape [K,T,D>=2]")
    if expert.shape != (trajectories.shape[1], 3):
        raise ValueError("expert future must have shape [T,3]")
    if not np.all(np.isfinite(trajectories)) or not np.all(np.isfinite(expert)):
        raise ValueError("candidate and expert trajectories must be finite")
    distances = np.linalg.norm(
        trajectories[:, :, :2] - expert[None, :, :2], axis=2
    )
    return distances.mean(axis=1), distances[:, -1]


def _validate_metric_matrices(
    ade: np.ndarray, fde: np.ndarray, feasible_mask: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ade_values = np.asarray(ade, dtype=np.float64)
    fde_values = np.asarray(fde, dtype=np.float64)
    feasible = np.asarray(feasible_mask, dtype=bool)
    if ade_values.ndim != 2 or fde_values.shape != ade_values.shape:
        raise ValueError("ADE and FDE must have matching shape [N,K]")
    if feasible.shape != ade_values.shape:
        raise ValueError("feasible mask must match ADE/FDE [N,K]")
    finite_feasible = feasible & np.isfinite(ade_values) & np.isfinite(fde_values)
    if not finite_feasible.any(axis=1).all():
        raise ValueError("each record must contain a finite feasible candidate")
    return ade_values, fde_values, finite_feasible


def oracle_indices(
    ade: np.ndarray,
    fde: np.ndarray,
    feasible_mask: np.ndarray,
    *,
    priority: np.ndarray,
    ade_tolerance_m: float = ADE_TIE_TOLERANCE_M,
) -> np.ndarray:
    ade_values, fde_values, feasible = _validate_metric_matrices(
        ade, fde, feasible_mask
    )
    priority_values = np.asarray(priority, dtype=np.int64).reshape(-1)
    if priority_values.shape != (ade_values.shape[1],):
        raise ValueError("priority must match candidate count")
    if ade_tolerance_m < 0.0:
        raise ValueError("ADE tie tolerance must be nonnegative")
    result = np.empty(ade_values.shape[0], dtype=np.int64)
    for row_index in range(ade_values.shape[0]):
        indices = np.flatnonzero(feasible[row_index])
        minimum_ade = float(np.min(ade_values[row_index, indices]))
        indices = indices[
            ade_values[row_index, indices] <= minimum_ade + ade_tolerance_m
        ]
        minimum_fde = float(np.min(fde_values[row_index, indices]))
        indices = indices[
            fde_values[row_index, indices] <= minimum_fde + ade_tolerance_m
        ]
        result[row_index] = min(indices, key=lambda item: priority_values[item])
    return result


def train_atom_scales(
    atoms: np.ndarray,
    feasible_mask: np.ndarray,
    *,
    percentile: float = SCALE_PERCENTILE,
) -> np.ndarray:
    atom_values = np.asarray(atoms, dtype=np.float64)
    feasible = np.asarray(feasible_mask, dtype=bool)
    if atom_values.ndim != 3 or feasible.shape != atom_values.shape[:2]:
        raise ValueError("atoms [N,K,R] and feasible mask [N,K] must match")
    if not 0.0 <= percentile <= 100.0:
        raise ValueError("percentile must be in [0,100]")
    rows = atom_values[feasible]
    if rows.size == 0 or not np.all(np.isfinite(rows)) or np.any(rows < 0.0):
        raise ValueError("feasible train atoms must be finite and nonnegative")
    scales = np.percentile(rows, percentile, axis=0)
    return np.maximum(scales, 1e-6)


def select_indices(
    scaled_atoms: np.ndarray,
    weights: np.ndarray,
    feasible_mask: np.ndarray,
    *,
    priority: np.ndarray,
    score_tolerance: float = SCORE_TIE_TOLERANCE,
) -> tuple[np.ndarray, np.ndarray]:
    atoms = np.asarray(scaled_atoms, dtype=np.float64)
    weight_values = np.asarray(weights, dtype=np.float64).reshape(-1)
    feasible = np.asarray(feasible_mask, dtype=bool)
    priority_values = np.asarray(priority, dtype=np.int64).reshape(-1)
    if atoms.ndim != 3 or feasible.shape != atoms.shape[:2]:
        raise ValueError("scaled atoms [N,K,R] and feasible mask [N,K] must match")
    if weight_values.shape != (atoms.shape[2],):
        raise ValueError("weights must match atom dimension")
    if priority_values.shape != (atoms.shape[1],):
        raise ValueError("priority must match candidate count")
    if not np.all(np.isfinite(atoms)) or not np.all(np.isfinite(weight_values)):
        raise ValueError("atoms and weights must be finite")
    if np.any(atoms < 0.0) or np.any(weight_values < 0.0):
        raise ValueError("atoms and weights must be nonnegative")
    if not np.isclose(weight_values.sum(), 1.0, atol=1e-8, rtol=0.0):
        raise ValueError("weights must sum to one")
    if not feasible.any(axis=1).all():
        raise ValueError("each record must contain a finite feasible candidate")
    if score_tolerance < 0.0:
        raise ValueError("score tolerance must be nonnegative")
    scores = np.einsum("nkr,r->nk", atoms, weight_values)
    scores = np.where(feasible, scores, np.inf)
    selected = np.empty(atoms.shape[0], dtype=np.int64)
    for row_index in range(atoms.shape[0]):
        minimum = float(np.min(scores[row_index]))
        indices = np.flatnonzero(
            feasible[row_index]
            & (scores[row_index] <= minimum + score_tolerance)
        )
        selected[row_index] = min(
            indices, key=lambda item: priority_values[item]
        )
    return selected, scores


def ade_margins(
    ade: np.ndarray,
    oracle: np.ndarray,
    feasible_mask: np.ndarray,
    *,
    margin_scale: float = MARGIN_SCALE,
    margin_clip: float = MARGIN_CLIP,
) -> np.ndarray:
    ade_values = np.asarray(ade, dtype=np.float64)
    feasible = np.asarray(feasible_mask, dtype=bool)
    oracle_values = np.asarray(oracle, dtype=np.int64).reshape(-1)
    if ade_values.ndim != 2 or feasible.shape != ade_values.shape:
        raise ValueError("ADE and feasible mask must have shape [N,K]")
    if oracle_values.shape != (ade_values.shape[0],):
        raise ValueError("oracle must match record count")
    if margin_scale < 0.0 or margin_clip < 0.0:
        raise ValueError("margin scale and clip must be nonnegative")
    if not feasible[np.arange(ade_values.shape[0]), oracle_values].all():
        raise ValueError("each oracle candidate must be feasible")
    oracle_ade = ade_values[np.arange(ade_values.shape[0]), oracle_values]
    margins = np.clip(
        margin_scale * np.maximum(ade_values - oracle_ade[:, None], 0.0),
        0.0,
        margin_clip,
    )
    margins[~feasible] = 0.0
    margins[np.arange(ade_values.shape[0]), oracle_values] = 0.0
    return margins


def _bootstrap_intervals(
    deltas: Mapping[str, np.ndarray],
    groups: np.ndarray,
    *,
    replicates: int,
    rng: np.random.Generator,
) -> dict[str, list[float]]:
    group_values = np.asarray(groups)
    unique_groups = np.unique(group_values)
    if unique_groups.size == 0 or replicates <= 0:
        raise ValueError("bootstrap requires groups and positive replicates")
    samples = {name: np.empty(replicates, dtype=np.float64) for name in deltas}
    group_indices = {
        group: np.flatnonzero(group_values == group) for group in unique_groups
    }
    for replicate in range(replicates):
        drawn = rng.choice(unique_groups, size=unique_groups.size, replace=True)
        indices = np.concatenate([group_indices[group] for group in drawn])
        for name, values in deltas.items():
            samples[name][replicate] = float(np.mean(values[indices]))
    return {
        name: [
            float(np.percentile(values, 2.5)),
            float(np.percentile(values, 97.5)),
        ]
        for name, values in samples.items()
    }


def paired_cluster_bootstrap(
    deltas: Mapping[str, np.ndarray],
    *,
    log_ids: np.ndarray,
    scene_ids: np.ndarray,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, dict[str, list[float]]]:
    if seed in FORBIDDEN_SEEDS:
        raise ValueError("formal seeds 11/12/13 are forbidden")
    arrays = {
        name: np.asarray(values, dtype=np.float64).reshape(-1)
        for name, values in deltas.items()
    }
    if set(arrays) != {"ade", "fde", "miss"}:
        raise ValueError("paired deltas must contain ADE, FDE, and miss")
    size = next(iter(arrays.values())).size
    if any(values.size != size or not np.all(np.isfinite(values)) for values in arrays.values()):
        raise ValueError("paired deltas must be finite and share one length")
    logs = np.asarray(log_ids).reshape(-1)
    scenes = np.asarray(scene_ids).reshape(-1)
    if logs.size != size or scenes.size != size:
        raise ValueError("cluster ids must match paired deltas")
    log_seed, scene_seed = np.random.SeedSequence(seed).spawn(2)
    return {
        "log_cluster": _bootstrap_intervals(
            arrays,
            logs,
            replicates=replicates,
            rng=np.random.default_rng(log_seed),
        ),
        "scene_cluster": _bootstrap_intervals(
            arrays,
            scenes,
            replicates=replicates,
            rng=np.random.default_rng(scene_seed),
        ),
    }
