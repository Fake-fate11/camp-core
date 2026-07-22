from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_causal_atoms import (
    CANONICAL_NORMALIZED_ATOM_CLIP,
)
from camp_core.integrations.diffusion_planner_v25_context import (
    PHI_DIMENSION,
    RAW_FEATURE_COUNT,
    RAW_FEATURE_NAMES,
    V25ContextScaler,
    fit_train_context_scaler,
)
from camp_core.outer_master.parametric_cvxpy_master import (
    V25ParametricMasterConfig,
    V25ParametricMasterResult,
    solve_v25_parametric_cutting_plane,
)


MODEL_REGISTRY: Mapping[str, tuple[str, tuple[int, ...]]] = {
    "CAMP-Static14D": ("static", tuple(range(14))),
    "CAMP-Scene14D": ("scene", tuple(range(14))),
    "CAMP-Static9D": ("static", tuple(range(9))),
    "CAMP-Scene9D": ("scene", tuple(range(9))),
}
CANDIDATE_COUNT = 8


@dataclass(frozen=True)
class V25TrainedSelector:
    name: str
    mode: str
    active_atom_indices: tuple[int, ...]
    theta: np.ndarray
    context_scaler: V25ContextScaler
    result: V25ParametricMasterResult
    selected_indices: np.ndarray
    selection_margins: np.ndarray
    report: dict[str, Any]


def train_v25_selector_suite(
    normalized_atoms_14d: np.ndarray,
    raw_context: np.ndarray,
    context_source_complete: np.ndarray,
    oracle_indices: np.ndarray,
    margins: np.ndarray,
    source_valid_mask: np.ndarray,
    record_weights: np.ndarray,
    *,
    stability_cluster_ids: Sequence[str],
    config: V25ParametricMasterConfig = V25ParametricMasterConfig(),
) -> dict[str, V25TrainedSelector]:
    """Train the frozen V25 fair 2x2 selector suite.

    Every model consumes the same train rows, causal-policy-distillation labels,
    record weights, and the corresponding prefix of the same 14D training-scale
    normalization.  The two 9D models are paper-subset ablations; only the 14D
    models are final methods.
    """

    atoms = _strict_numeric_matrix(
        normalized_atoms_14d, ndim=3, trailing_shape=(8, 14), name="normalized_atoms_14d"
    )
    if np.any(atoms < 0.0) or np.any(
        atoms > CANONICAL_NORMALIZED_ATOM_CLIP + 1e-12
    ):
        raise ValueError("normalized_atoms_14d must lie in canonical [0,10]")
    contexts = _strict_numeric_matrix(
        raw_context,
        ndim=2,
        trailing_shape=(RAW_FEATURE_COUNT,),
        name="raw_context",
    )
    if contexts.shape[0] != atoms.shape[0]:
        raise ValueError("raw_context must have one row per training snapshot")
    context_sources = _strict_bool(
        context_source_complete,
        (atoms.shape[0], RAW_FEATURE_COUNT),
        "context_source_complete",
    )
    source = _strict_bool(
        source_valid_mask, atoms.shape[:2], "source_valid_mask"
    )
    if np.any(~np.any(source, axis=1)):
        raise ValueError("source_valid_mask must be nonempty for every snapshot")
    oracle = _strict_int(oracle_indices, (atoms.shape[0],), "oracle_indices")
    margin_values = _strict_numeric_matrix(
        margins, ndim=2, trailing_shape=(8,), name="margins"
    )
    if margin_values.shape[0] != atoms.shape[0] or np.any(margin_values < 0.0):
        raise ValueError("margins must be finite nonnegative [N,8]")
    weights = _strict_positive_weights(record_weights, atoms.shape[0])
    cluster_ids = _strict_cluster_ids(stability_cluster_ids, atoms.shape[0])
    if np.any(oracle < 0) or np.any(oracle >= 8) or not np.all(
        source[np.arange(atoms.shape[0]), oracle]
    ):
        raise ValueError("oracle_indices must identify source-valid candidates")

    scaler = fit_train_context_scaler(
        contexts,
        source_complete=context_sources,
        record_weights=weights,
    )
    scene_phi = scaler.lift(contexts, source_complete=context_sources)
    static_phi = np.zeros((atoms.shape[0], PHI_DIMENSION), dtype=np.float64)
    static_phi[:, 0] = 1.0
    phi_by_mode = {"static": static_phi, "scene": scene_phi}

    trained: dict[str, V25TrainedSelector] = {}
    for name, (mode, active_indices) in MODEL_REGISTRY.items():
        active = np.asarray(active_indices, dtype=np.int64)
        model_atoms = atoms[:, :, active]
        phi = phi_by_mode[mode]
        result = solve_v25_parametric_cutting_plane(
            model_atoms,
            phi,
            oracle,
            margin_values,
            source,
            record_weights=weights,
            config=config,
        )
        if not result.converged:
            raise RuntimeError(f"{name} strict master did not converge")
        if (
            np.any(result.theta < -1e-9)
            or not np.allclose(
                result.theta.sum(axis=0), 1.0, rtol=0.0, atol=1e-8
            )
            or np.any(result.train_weights < -1e-9)
            or not np.allclose(
                result.train_weights.sum(axis=1), 1.0, rtol=0.0, atol=1e-8
            )
        ):
            raise RuntimeError(
                f"{name} stored solver output violates the no-projection simplex"
            )
        scores = np.einsum("nkr,nr->nk", model_atoms, result.train_weights)
        eligible_scores = np.where(source, scores, np.inf)
        selected = np.argmin(eligible_scores, axis=1).astype(np.int64)
        sorted_scores = np.sort(eligible_scores, axis=1)
        selection_margins = sorted_scores[:, 1] - sorted_scores[:, 0]
        selection_margins[np.sum(source, axis=1) < 2] = 0.0
        report = _model_report(
            name=name,
            mode=mode,
            active_indices=active_indices,
            result=result,
            selected=selected,
            selection_margins=selection_margins,
            record_weights=weights,
            context_sources=context_sources,
            source_valid_mask=source,
            stability_cluster_ids=cluster_ids,
        )
        trained[name] = V25TrainedSelector(
            name=name,
            mode=mode,
            active_atom_indices=active_indices,
            theta=result.theta.copy(),
            context_scaler=scaler,
            result=result,
            selected_indices=selected,
            selection_margins=selection_margins,
            report=report,
        )
    return trained


def _model_report(
    *,
    name: str,
    mode: str,
    active_indices: tuple[int, ...],
    result: V25ParametricMasterResult,
    selected: np.ndarray,
    selection_margins: np.ndarray,
    record_weights: np.ndarray,
    context_sources: np.ndarray,
    source_valid_mask: np.ndarray,
    stability_cluster_ids: tuple[str, ...],
) -> dict[str, Any]:
    train_weights = np.asarray(result.train_weights, dtype=np.float64)
    per_atom = []
    for atom_index in range(train_weights.shape[1]):
        values = train_weights[:, atom_index]
        per_atom.append(
            {
                "active_atom_index": int(active_indices[atom_index]),
                "mean": float(np.sum(record_weights * values)),
                "minimum": float(np.min(values)),
                "maximum": float(np.max(values)),
                "q05_q50_q95": [
                    _weighted_quantile(values, record_weights, q)
                    for q in (0.05, 0.50, 0.95)
                ],
            }
        )
    return {
        "schema_version": "camp_dp_v25_trained_selector_report_v1",
        "model_name": name,
        "mode": mode,
        "active_atom_indices": list(active_indices),
        "final_primary_method": len(active_indices) == 14,
        "paper_9d_subset_ablation": len(active_indices) == 9,
        "same_rows_labels_scales_and_block_weights": True,
        "selection_eligibility": "source_valid_candidate_set",
        "physical_feasible_mask_consumed_by_training": False,
        "v24_rows_consumed_by_main_2x2": False,
        "v24_without_raw_context_excluded_from_main_fair_comparison": True,
        "static14d_full_v24_augmented_role": "auxiliary_only_not_primary_method",
        "score_contract": "score_k=a_k^T*w(x)",
        "theta_column_simplex": True,
        "theta_column_interpretation_limited_by_redundant_context_lift": True,
        "runtime_projection": False,
        "softmax": False,
        "solver_name": result.solver_name,
        "solver_status": result.solver_status,
        "converged": result.converged,
        "iterations": result.iterations,
        "total_cuts": int(sum(result.cuts_per_scene)),
        "cut_index_sha256": _array_sha256(
            _cut_mask(result.cut_indices_per_scene, selected.size)
        ),
        "cuts_per_scene_min_median_max": [
            int(np.min(result.cuts_per_scene)),
            float(np.median(result.cuts_per_scene)),
            int(np.max(result.cuts_per_scene)),
        ],
        "final_master_gap": float(result.final_master_gap),
        "offline_training_wall_seconds": float(result.wall_seconds),
        "bt_pair_count_available": result.bt_warmup.pair_count_available,
        "bt_pair_count_used": result.bt_warmup.pair_count_used,
        "bt_initial_loss": float(result.bt_warmup.initial_loss),
        "bt_final_loss": float(result.bt_warmup.final_loss),
        "bt_learning_curve": list(result.bt_warmup.history),
        "master_learning_curve": list(result.history),
        "theta_sha256": _array_sha256(result.theta),
        "train_weight_sha256": _array_sha256(train_weights),
        "selected_index_sha256": _array_sha256(selected),
        "selected_nonzero_weight": float(np.sum(record_weights[selected != 0])),
        "two_or_more_source_valid_weight": float(
            np.sum(record_weights[np.sum(source_valid_mask, axis=1) >= 2])
        ),
        "selection_margin_q05_q50_q95": [
            _weighted_quantile(selection_margins, record_weights, q)
            for q in (0.05, 0.50, 0.95)
        ],
        "weight_stability": per_atom,
        "leave_one_corridor_stability": _leave_one_cluster_stability(
            train_weights,
            selected,
            record_weights,
            stability_cluster_ids,
        ),
        "cluster_ids_used_as_model_features": False,
        "context_source_complete_weighted_fraction": (
            np.sum(record_weights[:, None] * context_sources, axis=0).tolist()
        ),
        "outcome_or_fresh_consumed": False,
    }


def _strict_numeric_matrix(
    value: np.ndarray,
    *,
    ndim: int,
    trailing_shape: tuple[int, ...],
    name: str,
) -> np.ndarray:
    raw = np.asarray(value)
    if (
        raw.ndim != ndim
        or raw.shape[-len(trailing_shape) :] != trailing_shape
        or raw.dtype.kind not in "fiu"
        or raw.dtype.kind == "b"
    ):
        raise ValueError(f"{name} must be native numeric with trailing shape {trailing_shape}")
    result = raw.astype(np.float64, copy=False)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be finite")
    return result


def _strict_bool(value: np.ndarray, shape: tuple[int, ...], name: str) -> np.ndarray:
    result = np.asarray(value)
    if result.shape != shape or result.dtype != np.bool_:
        raise ValueError(f"{name} must be native bool with shape {shape}")
    return result


def _strict_int(value: np.ndarray, shape: tuple[int, ...], name: str) -> np.ndarray:
    result = np.asarray(value)
    if (
        result.shape != shape
        or result.dtype.kind not in "iu"
        or result.dtype.kind == "b"
    ):
        raise ValueError(f"{name} must be native integers with shape {shape}")
    return result.astype(np.int64, copy=False)


def _strict_positive_weights(value: np.ndarray, size: int) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != (size,) or raw.dtype.kind not in "fiu" or raw.dtype.kind == "b":
        raise ValueError("record_weights must be native numeric [N]")
    weights = raw.astype(np.float64, copy=False)
    if not np.all(np.isfinite(weights)) or np.any(weights <= 0.0):
        raise ValueError("record_weights must be finite strictly positive")
    total = float(np.sum(weights))
    if not np.isfinite(total) or total <= 0.0:
        raise ValueError("record_weights must have finite positive total")
    return weights / total


def _strict_cluster_ids(value: Sequence[str], size: int) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or len(value) != size:
        raise ValueError("stability_cluster_ids must contain one string per row")
    result = tuple(value)
    if any(type(item) is not str or not item for item in result):
        raise ValueError("stability_cluster_ids must contain nonempty native strings")
    return result


def _leave_one_cluster_stability(
    train_weights: np.ndarray,
    selected: np.ndarray,
    record_weights: np.ndarray,
    cluster_ids: tuple[str, ...],
) -> dict[str, Any]:
    global_weight = np.sum(record_weights[:, None] * train_weights, axis=0)
    global_selection = np.bincount(
        selected, weights=record_weights, minlength=CANDIDATE_COUNT
    ).astype(np.float64)
    rows: list[dict[str, Any]] = []
    weight_shifts: list[float] = []
    selection_shifts: list[float] = []
    cluster_array = np.asarray(cluster_ids)
    for cluster_id in sorted(set(cluster_ids)):
        keep = cluster_array != cluster_id
        excluded_mass = float(np.sum(record_weights[~keep]))
        remaining_mass = float(np.sum(record_weights[keep]))
        if remaining_mass <= 0.0:
            rows.append(
                {
                    "cluster_id": cluster_id,
                    "excluded_record_weight": excluded_mass,
                    "remaining_record_weight": remaining_mass,
                    "status": "descriptive_only_single_cluster",
                    "mean_weight_l1_shift": None,
                    "selection_distribution_l1_shift": None,
                }
            )
            continue
        local_weights = record_weights[keep] / remaining_mass
        leave_weight = np.sum(local_weights[:, None] * train_weights[keep], axis=0)
        leave_selection = np.bincount(
            selected[keep], weights=local_weights, minlength=CANDIDATE_COUNT
        ).astype(np.float64)
        weight_shift = float(np.sum(np.abs(leave_weight - global_weight)))
        selection_shift = float(np.sum(np.abs(leave_selection - global_selection)))
        weight_shifts.append(weight_shift)
        selection_shifts.append(selection_shift)
        rows.append(
            {
                "cluster_id": cluster_id,
                "excluded_record_weight": excluded_mass,
                "remaining_record_weight": remaining_mass,
                "status": "computed",
                "mean_weight_l1_shift": weight_shift,
                "selection_distribution_l1_shift": selection_shift,
            }
        )
    return {
        "analysis_kind": "postfit_cluster_exclusion_descriptive",
        "model_refit_performed": False,
        "interpretation": (
            "descriptive reweighting of fixed fitted outputs; "
            "not leave-cluster-out retraining stability"
        ),
        "cluster_unit": "corridor",
        "cluster_count": len(set(cluster_ids)),
        "record_count": len(cluster_ids),
        "rows": rows,
        "mean_weight_l1_shift_max": max(weight_shifts) if weight_shifts else None,
        "mean_weight_l1_shift_median": (
            float(np.median(weight_shifts)) if weight_shifts else None
        ),
        "selection_distribution_l1_shift_max": (
            max(selection_shifts) if selection_shifts else None
        ),
        "selection_distribution_l1_shift_median": (
            float(np.median(selection_shifts)) if selection_shifts else None
        ),
        "ticks_or_seeds_treated_as_independent_clusters": False,
    }


def _weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values, kind="mergesort")
    ordered = np.asarray(values, dtype=np.float64)[order]
    mass = np.asarray(weights, dtype=np.float64)[order]
    index = int(np.searchsorted(np.cumsum(mass), q * float(np.sum(mass)), side="left"))
    return float(ordered[min(index, ordered.size - 1)])


def _array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(b"\0")
    digest.update(",".join(str(item) for item in array.shape).encode("ascii"))
    digest.update(b"\0")
    digest.update(array.tobytes())
    return digest.hexdigest()


def _cut_mask(
    cut_indices_per_scene: tuple[tuple[int, ...], ...],
    record_count: int,
) -> np.ndarray:
    if len(cut_indices_per_scene) != record_count:
        raise ValueError("cut index rows must match training record count")
    result = np.zeros((record_count, 8), dtype=np.bool_)
    for record_index, candidates in enumerate(cut_indices_per_scene):
        for candidate_index in candidates:
            if not 0 <= int(candidate_index) < 8:
                raise ValueError("cut candidate index is outside fixed K=8")
            result[record_index, int(candidate_index)] = True
    return result
