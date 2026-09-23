"""Mathematical primitives for the V26 scene-conditioned CAMP experiment.

The functions in this module keep sparse endpoint semantics explicit.  An
unobserved atom is never expanded to a numeric column.  Candidate filtering is
not part of the objective: every configured candidate participates in the
scene-wise maximum.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from camp_core.integrations.diffusion_planner_v26_sparse_schema import (
    V26_GLOBAL_ATOM_NAMES,
    validate_v26_sparse_pool_artifact,
)


V26_COMFORT_ATOM_NAMES = frozenset(V26_GLOBAL_ATOM_NAMES[9:15])
V26_NORMALIZED_ATOM_CLIP = 10.0
V26_CVAR_ALPHA = 0.9
V26_FIXED_PHYSICAL_ATOM_SCALES = dict(
    zip(
        V26_GLOBAL_ATOM_NAMES,
        (
            1.0,
            0.857375,
            0.857375,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
        ),
        strict=True,
    )
)
V26_FIXED_PHYSICAL_ATOM_SCALE_UNITS = (
    "dimensionless",
    "seconds_cubed",
    "metres_squared_seconds",
    "metres_squared_per_second",
    "seconds",
    "metres",
    "seconds",
    "metres_squared_seconds",
    "metres",
    "seconds",
    "seconds",
    "seconds",
    "seconds",
    "seconds",
    "seconds",
)


def fixed_v26_scene_camp_atom_scales() -> dict[str, Any]:
    """Return the user-authorized paper-style fixed positive physical scales."""

    rows = [
        {
            "global_atom_index": index,
            "atom_name": name,
            "scale": V26_FIXED_PHYSICAL_ATOM_SCALES[name],
            "unit": V26_FIXED_PHYSICAL_ATOM_SCALE_UNITS[index],
            "status": "identified",
        }
        for index, name in enumerate(V26_GLOBAL_ATOM_NAMES)
    ]
    return {
        "global_atom_names": list(V26_GLOBAL_ATOM_NAMES),
        "scale_source": "paper_style_fixed_positive_physical_reference",
        "normalization": "clip(observed_raw_atom/scale,0,10)",
        "runner_q95_role": "descriptive_only_not_a_training_input_or_scale",
        "atom_rows": rows,
    }


def scales_by_global_name(scale_document: Mapping[str, Any]) -> dict[str, float]:
    """Read a complete scale document in the global atom order."""

    if tuple(scale_document.get("global_atom_names", ())) != V26_GLOBAL_ATOM_NAMES:
        raise ValueError("scale global atom order differs from the V26 atom bank")
    rows = scale_document.get("atom_rows")
    if not isinstance(rows, Sequence) or len(rows) != len(V26_GLOBAL_ATOM_NAMES):
        raise ValueError("scale document must contain one row per V26 atom")
    result: dict[str, float] = {}
    for index, (name, row) in enumerate(zip(V26_GLOBAL_ATOM_NAMES, rows)):
        if not isinstance(row, Mapping):
            raise ValueError("scale rows must be mappings")
        value = row.get("scale")
        if (
            row.get("global_atom_index") != index
            or row.get("atom_name") != name
            or row.get("status") != "identified"
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not np.isfinite(float(value))
            or float(value) <= 0.0
        ):
            raise ValueError(f"atom scale is not identified: {name}")
        result[name] = float(value)
    return result


def normalize_v26_sparse_pool(
    artifact: Mapping[str, Any],
    *,
    atom_scales: Mapping[str, float],
    clip: float = V26_NORMALIZED_ATOM_CLIP,
) -> dict[str, Any]:
    """Normalize only the columns actually observed in one sparse pool."""

    validated = validate_v26_sparse_pool_artifact(artifact)
    names = tuple(validated["observed_atom_names"])
    scales = np.asarray([atom_scales[name] for name in names], dtype=np.float64)
    if not np.all(np.isfinite(scales)) or np.any(scales <= 0.0):
        raise ValueError("observed atom scales must be finite and positive")
    limit = float(clip)
    if not np.isfinite(limit) or limit <= 0.0:
        raise ValueError("normalized atom clip must be finite and positive")
    candidates = np.clip(
        np.asarray(validated["candidate_atoms_raw"], dtype=np.float64) / scales,
        0.0,
        limit,
    )
    experts = np.clip(
        np.asarray(validated["expert_atoms_raw"], dtype=np.float64) / scales,
        0.0,
        limit,
    )
    return {
        "identity": validated["identity"],
        "active_atom_names": names,
        "active_global_atom_indices": tuple(validated["observed_global_atom_indices"]),
        "atom_status_by_name": dict(validated["atom_status_by_name"]),
        "candidate_atoms": candidates,
        "expert_atoms": experts,
    }


def exact_all_candidate_costs(
    candidate_atoms: np.ndarray,
    scene_weights: np.ndarray,
) -> np.ndarray:
    """Return ``max_k w_i^T A_ik`` for every scene, with no candidate mask."""

    atoms = np.asarray(candidate_atoms, dtype=np.float64)
    weights = np.asarray(scene_weights, dtype=np.float64)
    one_scene = atoms.ndim == 2
    if one_scene:
        atoms = atoms[None, ...]
    if weights.ndim == 1:
        weights = weights[None, ...]
    if (
        atoms.ndim != 3
        or weights.ndim != 2
        or atoms.shape[0] != weights.shape[0]
        or atoms.shape[2] != weights.shape[1]
    ):
        raise ValueError("candidate atoms and scene weights must be [N,K,Q] and [N,Q]")
    if not np.all(np.isfinite(atoms)) or not np.all(np.isfinite(weights)):
        raise ValueError("candidate atoms and scene weights must be finite")
    if np.any(weights < 0.0) or not np.allclose(
        np.sum(weights, axis=1), 1.0, rtol=0.0, atol=1e-10
    ):
        raise ValueError("each scene weight row must lie on its active simplex")
    costs = np.max(np.einsum("nkr,nr->nk", atoms, weights), axis=1)
    return costs[0] if one_scene else costs


def restricted_candidate_costs(
    candidate_atoms: np.ndarray,
    scene_weights: np.ndarray,
    candidate_cuts: Sequence[Sequence[int]],
) -> np.ndarray:
    """Evaluate the current per-scene Benders candidate subsets."""

    atoms = np.asarray(candidate_atoms, dtype=np.float64)
    weights = np.asarray(scene_weights, dtype=np.float64)
    if atoms.ndim != 3 or weights.shape != (atoms.shape[0], atoms.shape[2]):
        raise ValueError("candidate atoms and scene weights must be [N,K,Q] and [N,Q]")
    if len(candidate_cuts) != atoms.shape[0]:
        raise ValueError("candidate cuts must contain one nonempty subset per scene")
    scores = np.einsum("nkr,nr->nk", atoms, weights)
    result = np.empty(atoms.shape[0], dtype=np.float64)
    for scene_index, cuts in enumerate(candidate_cuts):
        indices = np.asarray(tuple(cuts), dtype=np.int64)
        if indices.size == 0 or np.any(indices < 0) or np.any(indices >= atoms.shape[1]):
            raise ValueError("each candidate-cut subset must be nonempty and in range")
        result[scene_index] = float(np.max(scores[scene_index, indices]))
    return result


def full_candidate_cut_gap(
    candidate_atoms: np.ndarray,
    scene_weights: np.ndarray,
    candidate_cuts: Sequence[Sequence[int]],
) -> tuple[float, np.ndarray, np.ndarray]:
    """Return the exact full-K minus restricted-K gap."""

    exact = exact_all_candidate_costs(candidate_atoms, scene_weights)
    restricted = restricted_candidate_costs(candidate_atoms, scene_weights, candidate_cuts)
    per_scene = np.maximum(exact - restricted, 0.0)
    return float(np.max(per_scene)), per_scene, exact


def empirical_cvar(costs: np.ndarray, *, alpha: float = V26_CVAR_ALPHA) -> float:
    """Evaluate the equal-scene empirical Rockafellar--Uryasev CVaR."""

    values = np.asarray(costs, dtype=np.float64).reshape(-1)
    if values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("CVaR costs must be a nonempty finite vector")
    level = float(alpha)
    if not 0.0 <= level < 1.0:
        raise ValueError("CVaR alpha must lie in [0,1)")
    ordered = np.sort(values)
    quantile_index = max(int(np.ceil(level * values.size)) - 1, 0)
    eta = float(ordered[quantile_index])
    return eta + float(np.sum(np.maximum(values - eta, 0.0))) / (
        (1.0 - level) * values.size
    )


def project_rows_to_simplex(values: np.ndarray) -> np.ndarray:
    """Euclidean projection used only for new-scene inference."""

    raw = np.asarray(values, dtype=np.float64)
    one_row = raw.ndim == 1
    matrix = raw.reshape(1, -1) if one_row else raw
    if matrix.ndim != 2 or matrix.shape[1] == 0 or not np.all(np.isfinite(matrix)):
        raise ValueError("simplex projection expects a finite nonempty vector or matrix")
    ordered = np.sort(matrix, axis=1)[:, ::-1]
    cumulative = np.cumsum(ordered, axis=1) - 1.0
    ranks = np.arange(1, matrix.shape[1] + 1, dtype=np.float64)
    positive = ordered - cumulative / ranks > 0.0
    rho = np.sum(positive, axis=1) - 1
    thresholds = cumulative[np.arange(matrix.shape[0]), rho] / (rho + 1.0)
    projected = np.maximum(matrix - thresholds[:, None], 0.0)
    return projected[0] if one_row else projected
