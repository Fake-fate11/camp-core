"""Shared, outcome-blind CAMP label, scale, and snapshot-weight arithmetic."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner import CAMP_ATOM_NAMES, DP_CAMP_ATOM_NAMES_V10
from camp_core.integrations.diffusion_planner_causal_atoms import CANONICAL_NORMALIZED_ATOM_CLIP


ATOM_NAMES = tuple(DP_CAMP_ATOM_NAMES_V10)
PAPER_9D_INDICES = tuple(range(len(CAMP_ATOM_NAMES)))
ATOM_COUNT = len(ATOM_NAMES)
CANDIDATE_COUNT = 8
DEFAULT_LABEL_SEVERITY = np.asarray(
    (0.0, 0.0, 0.25, 0.25, 10.0, 0.0, 0.0, 20.0, 10.0, 1.0,
     15.0, 1.0, 15.0, 0.25),
    dtype=np.float64,
)


def hierarchical_snapshot_weights(
    route_ids: Sequence[str], semantic_block_ids: Sequence[str],
    seeds: Sequence[int], ticks: Sequence[int],
) -> np.ndarray:
    """Give equal mass route -> semantic block -> seed -> tick."""
    size = len(route_ids)
    if not (len(semantic_block_ids) == size and len(seeds) == size and len(ticks) == size and size > 0):
        raise ValueError("hierarchical weight columns must have equal nonzero length")
    routes = _strict_strings(route_ids, "route_ids")
    blocks = _strict_strings(semantic_block_ids, "semantic_block_ids")
    seed_values = _strict_ints(seeds, "seeds")
    tick_values = _strict_ints(ticks, "ticks")
    weights = np.zeros(size, dtype=np.float64)
    columns: tuple[Sequence[Any], ...] = (routes, blocks, seed_values, tick_values)

    def distribute(indices: list[int], level: int, mass: float) -> None:
        if level == 4:
            weights[indices] = mass / float(len(indices))
            return
        groups: dict[Any, list[int]] = defaultdict(list)
        for index in indices:
            groups[columns[level][index]].append(index)
        share = mass / float(len(groups))
        for key in sorted(groups, key=lambda value: (str(type(value)), str(value))):
            distribute(groups[key], level + 1, share)

    distribute(list(range(size)), 0, 1.0)
    if not np.all(np.isfinite(weights)) or np.any(weights <= 0.0):
        raise RuntimeError("hierarchical weights must be finite and strictly positive")
    if not np.isclose(weights.sum(), 1.0, rtol=0.0, atol=1e-12):
        raise RuntimeError("hierarchical weights do not sum to one")
    return weights


def weighted_quantile(values: np.ndarray, weights: np.ndarray, quantile: float) -> float:
    """Return the inverse weighted empirical CDF quantile with a stable sort."""
    x, w = _finite_values_and_weights(values, weights)
    if not 0.0 <= float(quantile) <= 1.0:
        raise ValueError("quantile must lie in [0,1]")
    order = np.argsort(x, kind="mergesort")
    ordered = x[order]
    cumulative = np.cumsum(w[order])
    threshold = float(quantile) * float(cumulative[-1])
    index = int(np.searchsorted(cumulative, threshold, side="left"))
    return float(ordered[min(index, ordered.size - 1)])


def fit_train_only_atom_scales(
    raw_atoms: np.ndarray, source_valid_mask: np.ndarray,
    atom_source_valid_mask: np.ndarray, atom_applicable_mask: np.ndarray,
    snapshot_weights: np.ndarray, semantic_block_ids: Sequence[str], *,
    quantile: float = 0.95, minimum_positive_rows: int = 128,
    minimum_positive_blocks: int = 20,
) -> dict[str, Any]:
    """Fit per-atom train-only scales from positive applicable support only."""
    raw, source, atom_source, applicable, _physical, weights = _validate_atom_inputs(
        raw_atoms, source_valid_mask, atom_source_valid_mask, atom_applicable_mask,
        physical_feasible_mask=None, snapshot_weights=snapshot_weights,
    )
    blocks = _strict_strings(semantic_block_ids, "semantic_block_ids")
    if len(blocks) != raw.shape[0]:
        raise ValueError("semantic_block_ids must have one value per snapshot")
    rows: list[dict[str, Any]] = []
    scales = np.empty(ATOM_COUNT, dtype=np.float64)
    for atom_index, atom_name in enumerate(ATOM_NAMES):
        eligible = source & atom_source[:, :, atom_index] & applicable[:, :, atom_index]
        positive = eligible & (raw[:, :, atom_index] > 0.0)
        positive_rows = int(np.sum(positive))
        positive_blocks = len({blocks[index] for index in range(raw.shape[0]) if np.any(positive[index])})
        candidate_weights = _candidate_weights(weights, eligible)
        support_ok = positive_rows >= int(minimum_positive_rows) and positive_blocks >= int(minimum_positive_blocks)
        positive_quantile_scale: float | None = None
        if positive_rows:
            positive_quantile_scale = weighted_quantile(
                raw[:, :, atom_index][positive], candidate_weights[positive], quantile
            )
            if not np.isfinite(positive_quantile_scale) or positive_quantile_scale <= 0.0:
                raise ValueError("positive-support atom scale must be finite and positive")
        red_atom = atom_name in {"planned_red_light_cost", "red_stopping_margin_cost"}
        if positive_quantile_scale is None:
            scale, estimator, empirical = 1.0, "masked_zero_support_neutral_unit_scale", False
        elif red_atom and not support_ok:
            scale, estimator, empirical = 1.0, "support_limited_red_binary_scale", False
        else:
            scale, estimator, empirical = positive_quantile_scale, "positive_support_weighted_q95", True
        scales[atom_index] = scale
        rows.append({
            "atom_index": atom_index, "atom_name": atom_name,
            "positive_candidate_row_count": positive_rows,
            "positive_semantic_block_count": positive_blocks,
            "minimum_positive_candidate_rows": int(minimum_positive_rows),
            "minimum_positive_semantic_blocks": int(minimum_positive_blocks),
            "quantile": float(quantile), "training_scale": scale,
            "positive_quantile_scale": positive_quantile_scale,
            "training_scale_estimator": estimator, "training_scale_is_empirical": empirical,
            "status": "PASS" if support_ok else "WARN",
            "warning": None if support_ok else "support_limited",
            "generation_floor_used_as_training_scale": False,
            "red_binary_alternative_scale": 1.0 if red_atom else None,
        })
    return {
        "schema_version": "camp_dp_v25_train_only_atom_scales_v2",
        "quantile_definition": "inverse_weighted_empirical_cdf_left_closed",
        "candidate_weighting": "route_then_semantic_block_then_seed_then_tick_equal_mass_eligible_candidates_share_tick_mass",
        "scales": scales, "atom_rows": rows,
        "zero_support_policy": "keep_14d_dimension_masked_and_use_neutral_unit_scale_not_generation_floor",
        "support_limited_red_policy": "binary_scale_1_not_degenerate_continuous_floor",
    }


def build_train_only_causal_labels(
    raw_atoms: np.ndarray, source_valid_mask: np.ndarray,
    atom_source_valid_mask: np.ndarray, atom_applicable_mask: np.ndarray,
    physical_feasible_mask: np.ndarray, training_scales: np.ndarray, *,
    severity: np.ndarray = DEFAULT_LABEL_SEVERITY, physical_penalty: float = 100.0,
    margin_multiplier: float = 0.1, margin_clip: float = 2.0,
) -> dict[str, np.ndarray]:
    """Build frozen outcome-blind causal-policy-distillation labels."""
    raw, source, atom_source, applicable, physical, _weights = _validate_atom_inputs(
        raw_atoms, source_valid_mask, atom_source_valid_mask, atom_applicable_mask,
        physical_feasible_mask=physical_feasible_mask,
        snapshot_weights=np.full(np.asarray(raw_atoms).shape[0], 1.0),
    )
    scales = _positive_vector(training_scales, ATOM_COUNT, "training_scales")
    severity_values = _nonnegative_vector(severity, ATOM_COUNT, "severity")
    if not np.isfinite(physical_penalty) or physical_penalty < 0.0:
        raise ValueError("physical_penalty must be finite nonnegative")
    if not (np.isfinite(margin_multiplier) and margin_multiplier >= 0.0 and np.isfinite(margin_clip) and margin_clip > 0.0):
        raise ValueError("margin parameters are invalid")
    atom_usable = atom_source & applicable
    normalized = np.clip(raw / scales.reshape(1, 1, -1), 0.0, CANONICAL_NORMALIZED_ATOM_CLIP)
    contributions = np.where(atom_usable, normalized * severity_values.reshape(1, 1, -1), 0.0)
    costs = contributions.sum(axis=2) + float(physical_penalty) * (~physical)
    costs = np.where(source, costs, np.inf)
    if np.any(~np.any(source, axis=1)):
        raise ValueError("train labels require a nonempty source-valid candidate set")
    oracle = np.argmin(costs, axis=1).astype(np.int64)
    oracle_cost = costs[np.arange(costs.shape[0]), oracle]
    margins = np.clip(float(margin_multiplier) * (costs - oracle_cost[:, None]), 0.0, float(margin_clip))
    margins[~source] = 0.0
    return {"normalized_atoms": normalized, "atom_contributions": contributions,
            "candidate_costs": costs, "oracle_indices": oracle, "margins": margins}


def _validate_atom_inputs(
    raw_atoms: np.ndarray, source_valid_mask: np.ndarray,
    atom_source_valid_mask: np.ndarray, atom_applicable_mask: np.ndarray, *,
    physical_feasible_mask: np.ndarray | None, snapshot_weights: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    raw = np.asarray(raw_atoms)
    if raw.ndim != 3 or raw.shape[1:] != (CANDIDATE_COUNT, ATOM_COUNT) or raw.dtype.kind not in "fiu" or raw.dtype.kind == "b":
        raise ValueError("raw_atoms must be native numeric [N,8,14]")
    raw = raw.astype(np.float64, copy=False)
    if not np.all(np.isfinite(raw)) or np.any(raw < 0.0):
        raise ValueError("raw_atoms must be finite nonnegative")
    source = _strict_bool_array(source_valid_mask, raw.shape[:2], "source_valid_mask")
    atom_source = _strict_bool_array(atom_source_valid_mask, raw.shape, "atom_source_valid_mask")
    applicable = _strict_bool_array(atom_applicable_mask, raw.shape, "atom_applicable_mask")
    if np.any(applicable & ~atom_source):
        raise ValueError("atom applicability requires atom source validity")
    if np.any(source != np.all(atom_source, axis=2)):
        raise ValueError("source_valid_mask must equal per-candidate atom-source conjunction")
    if np.any(~np.any(source, axis=1)):
        raise ValueError("every snapshot requires a nonempty source-valid set")
    if physical_feasible_mask is None:
        physical = np.zeros(raw.shape[:2], dtype=np.bool_)
    else:
        physical = _strict_bool_array(physical_feasible_mask, raw.shape[:2], "physical_feasible_mask")
        if np.any(physical & ~source):
            raise ValueError("physical feasibility must be a subset of source validity")
    weights = np.asarray(snapshot_weights)
    if weights.shape != (raw.shape[0],) or weights.dtype.kind not in "fiu" or weights.dtype.kind == "b":
        raise ValueError("snapshot_weights must be native numeric [N]")
    weights = weights.astype(np.float64, copy=False)
    if not np.all(np.isfinite(weights)) or np.any(weights <= 0.0):
        raise ValueError("snapshot_weights must be finite strictly positive")
    return raw, source, atom_source, applicable, physical, weights / weights.sum()


def _candidate_weights(snapshot_weights: np.ndarray, mask: np.ndarray) -> np.ndarray:
    counts = np.sum(mask, axis=1)
    result = np.zeros(mask.shape, dtype=np.float64)
    valid_rows = counts > 0
    result[valid_rows] = (snapshot_weights[valid_rows, None] / counts[valid_rows, None]) * mask[valid_rows]
    total = float(result.sum())
    if total > 0.0:
        result /= total
    return result


def _strict_bool_array(value: Any, shape: tuple[int, ...], name: str) -> np.ndarray:
    array = np.asarray(value)
    if array.shape != shape or array.dtype != np.bool_:
        raise ValueError(f"{name} must be native bool with shape {shape}")
    return array


def _positive_vector(value: Any, size: int, name: str) -> np.ndarray:
    result = np.asarray(value)
    if result.shape != (size,) or result.dtype.kind not in "fiu" or result.dtype.kind == "b":
        raise ValueError(f"{name} must be native numeric [{size}]")
    result = result.astype(np.float64, copy=False)
    if not np.all(np.isfinite(result)) or np.any(result <= 0.0):
        raise ValueError(f"{name} must be finite strictly positive")
    return result


def _nonnegative_vector(value: Any, size: int, name: str) -> np.ndarray:
    result = np.asarray(value)
    if result.shape != (size,) or result.dtype.kind not in "fiu" or result.dtype.kind == "b":
        raise ValueError(f"{name} must be native numeric [{size}]")
    result = result.astype(np.float64, copy=False)
    if not np.all(np.isfinite(result)) or np.any(result < 0.0):
        raise ValueError(f"{name} must be finite nonnegative")
    return result


def _finite_values_and_weights(values: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(values, dtype=np.float64).reshape(-1)
    w = np.asarray(weights, dtype=np.float64).reshape(-1)
    if x.shape != w.shape or x.size == 0:
        raise ValueError("values and weights must be aligned nonempty vectors")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(w)) or np.any(w < 0.0):
        raise ValueError("values/weights must be finite and weights nonnegative")
    if float(w.sum()) <= 0.0:
        raise ValueError("weights must have positive total mass")
    return x, w


def _strict_strings(values: Sequence[str], name: str) -> tuple[str, ...]:
    if any(type(value) is not str or not value for value in values):
        raise ValueError(f"{name} must contain nonempty native strings")
    return tuple(values)


def _strict_ints(values: Sequence[int], name: str) -> tuple[int, ...]:
    if any(type(value) is not int for value in values):
        raise ValueError(f"{name} must contain native integers")
    return tuple(values)
