from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner import (
    CAMP_ATOM_NAMES,
    DP_CAMP_ATOM_NAMES_V10,
)
from camp_core.integrations.diffusion_planner_causal_atoms import (
    CANONICAL_NORMALIZED_ATOM_CLIP,
)


ATOM_NAMES = tuple(DP_CAMP_ATOM_NAMES_V10)
PAPER_9D_INDICES = tuple(range(len(CAMP_ATOM_NAMES)))
ATOM_COUNT = len(ATOM_NAMES)
CANDIDATE_COUNT = 8
DEFAULT_LABEL_SEVERITY = np.asarray(
    (0.0, 0.0, 0.25, 0.25, 10.0, 0.0, 0.0, 20.0, 10.0, 1.0,
     15.0, 1.0, 15.0, 0.25),
    dtype=np.float64,
)
DEFAULT_ABLATION_GROUPS: Mapping[str, tuple[int, ...]] = {
    "jerk3": (0, 1, 2),
    "rms_acceleration": (3,),
    "speed3": (4, 5, 6),
    "lane_clearance": (7, 8),
    "progress": (9,),
    "signal2": (10, 12),
    "lateral_acceleration": (11,),
    "dp_prior": (13,),
}
CORRECTNESS_ATOL = 1e-9
CORRECTNESS_RTOL = 1e-9


def hierarchical_snapshot_weights(
    route_ids: Sequence[str],
    semantic_block_ids: Sequence[str],
    seeds: Sequence[int],
    ticks: Sequence[int],
) -> np.ndarray:
    """Give equal mass route -> semantic block -> seed -> tick.

    Duplicate rows at the same terminal leaf share that leaf's mass.  The
    identifiers are used only offline for weighting and are never model inputs.
    """

    size = len(route_ids)
    if not (
        len(semantic_block_ids) == size
        and len(seeds) == size
        and len(ticks) == size
        and size > 0
    ):
        raise ValueError("hierarchical weight columns must have equal nonzero length")
    routes = _strict_strings(route_ids, "route_ids")
    blocks = _strict_strings(semantic_block_ids, "semantic_block_ids")
    seed_values = _strict_ints(seeds, "seeds")
    tick_values = _strict_ints(ticks, "ticks")
    rows = list(range(size))
    weights = np.zeros(size, dtype=np.float64)

    def distribute(indices: list[int], level: int, mass: float) -> None:
        if level == 4:
            share = mass / float(len(indices))
            weights[indices] = share
            return
        columns: tuple[Sequence[Any], ...] = (
            routes,
            blocks,
            seed_values,
            tick_values,
        )
        groups: dict[Any, list[int]] = defaultdict(list)
        for index in indices:
            groups[columns[level][index]].append(index)
        share = mass / float(len(groups))
        for key in sorted(groups, key=lambda value: (str(type(value)), str(value))):
            distribute(groups[key], level + 1, share)

    distribute(rows, 0, 1.0)
    if not np.all(np.isfinite(weights)) or np.any(weights <= 0.0):
        raise RuntimeError("hierarchical weights must be finite and strictly positive")
    if not np.isclose(weights.sum(), 1.0, rtol=0.0, atol=1e-12):
        raise RuntimeError("hierarchical weights do not sum to one")
    return weights


def weighted_quantile(
    values: np.ndarray,
    weights: np.ndarray,
    quantile: float,
) -> float:
    """Return the inverse weighted empirical CDF quantile.

    The result is ``min(x): cumulative_weight(x) >= q * total_weight`` with a
    stable sort.  This deliberately avoids an implementation-dependent
    interpolation convention in the train-only scale contract.
    """

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
    raw_atoms: np.ndarray,
    source_valid_mask: np.ndarray,
    atom_source_valid_mask: np.ndarray,
    atom_applicable_mask: np.ndarray,
    snapshot_weights: np.ndarray,
    semantic_block_ids: Sequence[str],
    *,
    quantile: float = 0.95,
    minimum_positive_rows: int = 128,
    minimum_positive_blocks: int = 20,
) -> dict[str, Any]:
    """Fit per-atom train-only scales from positive applicable support only."""

    arrays = _validate_atom_inputs(
        raw_atoms,
        source_valid_mask,
        atom_source_valid_mask,
        atom_applicable_mask,
        physical_feasible_mask=None,
        snapshot_weights=snapshot_weights,
    )
    raw, source, atom_source, applicable, _physical, weights = arrays
    blocks = _strict_strings(semantic_block_ids, "semantic_block_ids")
    if len(blocks) != raw.shape[0]:
        raise ValueError("semantic_block_ids must have one value per snapshot")
    rows: list[dict[str, Any]] = []
    scales = np.empty(ATOM_COUNT, dtype=np.float64)
    for atom_index, atom_name in enumerate(ATOM_NAMES):
        eligible = source & atom_source[:, :, atom_index] & applicable[:, :, atom_index]
        positive = eligible & (raw[:, :, atom_index] > 0.0)
        positive_rows = int(np.sum(positive))
        positive_blocks = len(
            {
                blocks[snapshot_index]
                for snapshot_index in range(raw.shape[0])
                if np.any(positive[snapshot_index])
            }
        )
        candidate_weights = _candidate_weights(weights, eligible)
        support_ok = (
            positive_rows >= int(minimum_positive_rows)
            and positive_blocks >= int(minimum_positive_blocks)
        )
        positive_quantile_scale: float | None = None
        if positive_rows:
            positive_quantile_scale = weighted_quantile(
                raw[:, :, atom_index][positive],
                candidate_weights[positive],
                quantile,
            )
            if not np.isfinite(positive_quantile_scale) or positive_quantile_scale <= 0.0:
                raise ValueError("positive-support atom scale must be finite and positive")
        red_atom = atom_name in {
            "planned_red_light_cost",
            "red_stopping_margin_cost",
        }
        if positive_quantile_scale is None:
            scale = 1.0
            estimator = "masked_zero_support_neutral_unit_scale"
            empirical = False
        elif red_atom and not support_ok:
            scale = 1.0
            estimator = "support_limited_red_binary_scale"
            empirical = False
        else:
            scale = positive_quantile_scale
            estimator = "positive_support_weighted_q95"
            empirical = True
        scales[atom_index] = scale
        rows.append(
            {
                "atom_index": atom_index,
                "atom_name": atom_name,
                "positive_candidate_row_count": positive_rows,
                "positive_semantic_block_count": positive_blocks,
                "minimum_positive_candidate_rows": int(minimum_positive_rows),
                "minimum_positive_semantic_blocks": int(minimum_positive_blocks),
                "quantile": float(quantile),
                "training_scale": scale,
                "positive_quantile_scale": positive_quantile_scale,
                "training_scale_estimator": estimator,
                "training_scale_is_empirical": empirical,
                "status": "PASS" if support_ok else "WARN",
                "warning": None if support_ok else "support_limited",
                "generation_floor_used_as_training_scale": False,
                "red_binary_alternative_scale": (
                    1.0 if red_atom else None
                ),
            }
        )
    return {
        "schema_version": "camp_dp_v25_train_only_atom_scales_v2",
        "quantile_definition": "inverse_weighted_empirical_cdf_left_closed",
        "candidate_weighting": (
            "route_then_semantic_block_then_seed_then_tick_equal_mass_"
            "eligible_candidates_share_tick_mass"
        ),
        "scales": scales,
        "atom_rows": rows,
        "zero_support_policy": (
            "keep_14d_dimension_masked_and_use_neutral_unit_scale_not_generation_floor"
        ),
        "support_limited_red_policy": "binary_scale_1_not_degenerate_continuous_floor",
    }


def build_train_only_causal_labels(
    raw_atoms: np.ndarray,
    source_valid_mask: np.ndarray,
    atom_source_valid_mask: np.ndarray,
    atom_applicable_mask: np.ndarray,
    physical_feasible_mask: np.ndarray,
    training_scales: np.ndarray,
    *,
    severity: np.ndarray = DEFAULT_LABEL_SEVERITY,
    physical_penalty: float = 100.0,
    margin_multiplier: float = 0.1,
    margin_clip: float = 2.0,
) -> dict[str, np.ndarray]:
    """Build the frozen outcome-blind causal-policy-distillation labels."""

    raw, source, atom_source, applicable, physical, _weights = _validate_atom_inputs(
        raw_atoms,
        source_valid_mask,
        atom_source_valid_mask,
        atom_applicable_mask,
        physical_feasible_mask=physical_feasible_mask,
        snapshot_weights=np.full(np.asarray(raw_atoms).shape[0], 1.0),
    )
    scales = _positive_vector(training_scales, ATOM_COUNT, "training_scales")
    severity_values = _nonnegative_vector(severity, ATOM_COUNT, "severity")
    if not np.isfinite(physical_penalty) or physical_penalty < 0.0:
        raise ValueError("physical_penalty must be finite nonnegative")
    if (
        not np.isfinite(margin_multiplier)
        or margin_multiplier < 0.0
        or not np.isfinite(margin_clip)
        or margin_clip <= 0.0
    ):
        raise ValueError("margin parameters are invalid")
    atom_usable = atom_source & applicable
    normalized = np.clip(
        raw / scales.reshape(1, 1, -1),
        0.0,
        CANONICAL_NORMALIZED_ATOM_CLIP,
    )
    contributions = np.where(
        atom_usable,
        normalized * severity_values.reshape(1, 1, -1),
        0.0,
    )
    costs = contributions.sum(axis=2) + float(physical_penalty) * (~physical)
    costs = np.where(source, costs, np.inf)
    if np.any(~np.any(source, axis=1)):
        raise ValueError("train labels require a nonempty source-valid candidate set")
    oracle = np.argmin(costs, axis=1).astype(np.int64)
    oracle_cost = costs[np.arange(costs.shape[0]), oracle]
    margins = np.clip(
        float(margin_multiplier) * (costs - oracle_cost[:, None]),
        0.0,
        float(margin_clip),
    )
    margins[~source] = 0.0
    return {
        "normalized_atoms": normalized,
        "atom_contributions": contributions,
        "candidate_costs": costs,
        "oracle_indices": oracle,
        "margins": margins,
    }


def compute_train_atom_audit(
    raw_atoms: np.ndarray,
    source_valid_mask: np.ndarray,
    atom_source_valid_mask: np.ndarray,
    atom_applicable_mask: np.ndarray,
    physical_feasible_mask: np.ndarray,
    snapshot_weights: np.ndarray,
    semantic_block_ids: Sequence[str],
    route_ids: Sequence[str],
    family_tier: Sequence[str],
    training_scales: np.ndarray,
    *,
    severity: np.ndarray = DEFAULT_LABEL_SEVERITY,
    generation_scales: np.ndarray | None = None,
    minimum_positive_rows: int = 128,
    minimum_positive_blocks: int = 20,
) -> dict[str, Any]:
    """Compute the sealed-train-only 14D empirical audit and ablations.

    This routine consumes no closed-loop outcome, calibration, Fresh, future,
    or identifier-derived model feature.  Route/block/stratum identifiers are
    used only for offline weighting and grouped diagnostics.
    """

    raw, source, atom_source, applicable, physical, weights = _validate_atom_inputs(
        raw_atoms,
        source_valid_mask,
        atom_source_valid_mask,
        atom_applicable_mask,
        physical_feasible_mask=physical_feasible_mask,
        snapshot_weights=snapshot_weights,
    )
    blocks = _strict_strings(semantic_block_ids, "semantic_block_ids")
    routes = _strict_strings(route_ids, "route_ids")
    strata = _strict_strings(family_tier, "family_tier")
    if not (len(blocks) == len(routes) == len(strata) == raw.shape[0]):
        raise ValueError("audit grouping columns must match snapshot count")
    scales = _positive_vector(training_scales, ATOM_COUNT, "training_scales")
    generation = (
        _positive_vector(generation_scales, ATOM_COUNT, "generation_scales")
        if generation_scales is not None
        else None
    )
    labels = build_train_only_causal_labels(
        raw,
        source,
        atom_source,
        applicable,
        physical,
        scales,
        severity=severity,
    )
    normalized = labels["normalized_atoms"]
    candidate_costs = labels["candidate_costs"]
    direct = labels["atom_contributions"]
    correctness_checks, correctness_failures = _independent_row_correctness_checks(
        raw, source, atom_source, applicable
    )
    atom_rows: list[dict[str, Any]] = []
    for atom_index, atom_name in enumerate(ATOM_NAMES):
        source_mask = source & atom_source[:, :, atom_index]
        eligible = source_mask & applicable[:, :, atom_index]
        values = raw[:, :, atom_index]
        candidate_weights = _candidate_weights(weights, source_mask)
        applicable_weights = _candidate_weights(weights, eligible)
        positive = eligible & (values > 0.0)
        positive_rows = int(np.sum(positive))
        positive_blocks = len(
            {
                blocks[i]
                for i in range(raw.shape[0])
                if np.any(positive[i])
            }
        )
        support_ok = (
            positive_rows >= int(minimum_positive_rows)
            and positive_blocks >= int(minimum_positive_blocks)
        )
        quantile_values = values[source_mask]
        quantile_weights = candidate_weights[source_mask]
        quantiles = {
            name: weighted_quantile(quantile_values, quantile_weights, q)
            for name, q in (("q05", 0.05), ("q50", 0.50), ("q95", 0.95), ("q99", 0.99))
        }
        label_minus_atom = candidate_costs - direct[:, :, atom_index]
        finite_common = eligible & np.isfinite(label_minus_atom)
        full_label_spearman = _weighted_spearman(
            normalized[:, :, atom_index][finite_common],
            candidate_costs[finite_common],
            applicable_weights[finite_common],
        )
        spearman = _weighted_spearman(
            normalized[:, :, atom_index][finite_common],
            label_minus_atom[finite_common],
            applicable_weights[finite_common],
        )
        conditional = _stratum_residual_spearman(
            normalized[:, :, atom_index],
            label_minus_atom,
            applicable_weights,
            finite_common,
            strata,
        )
        range_stats = _candidate_distinction_stats(
            values,
            eligible,
            weights,
        )
        warning_reasons: list[str] = []
        remediation_classes: list[str] = []
        failure_reasons = list(correctness_failures[atom_index])
        if failure_reasons:
            remediation_classes.append("implementation_correctness")
        if not support_ok:
            warning_reasons.append("support_limited")
            remediation_classes.append("evidence_support")
        if (
            range_stats["eligible_snapshot_count"] > 0
            and range_stats["positive_range_weight"] == 0.0
        ):
            warning_reasons.append("candidate_indistinguishable")
            remediation_classes.append("expected_redundancy")
        status = "FAIL" if failure_reasons else "WARN" if warning_reasons else "PASS"
        drift = _atom_group_drift(
            values,
            source_mask,
            weights,
            family_tier=strata,
            route_ids=routes,
        )
        training_saturation = float(
            np.sum(
                applicable_weights[eligible]
                * (normalized[:, :, atom_index][eligible] >= CANONICAL_NORMALIZED_ATOM_CLIP)
            )
        ) if np.any(eligible) else 0.0
        generation_saturation: float | None = None
        if generation is not None and np.any(eligible):
            generation_saturation = float(
                np.sum(
                    applicable_weights[eligible]
                    * (
                        values[eligible] / generation[atom_index]
                        >= CANONICAL_NORMALIZED_ATOM_CLIP
                    )
                )
            )
        atom_rows.append(
            {
                "atom_index": atom_index,
                "atom_name": atom_name,
                "paper_9d": atom_index in PAPER_9D_INDICES,
                "source_available_weight": float(np.sum(weights[np.any(source_mask, axis=1)])),
                "applicable_weight": float(np.sum(weights[np.any(eligible, axis=1)])),
                "source_valid_candidate_fraction_weighted": float(
                    np.sum(weights * np.mean(source_mask, axis=1))
                ),
                "applicable_candidate_fraction_weighted": float(
                    np.sum(weights * np.mean(eligible, axis=1))
                ),
                "source_candidate_count": int(np.sum(source_mask)),
                "applicable_candidate_count": int(np.sum(eligible)),
                "zero_candidate_count": int(np.sum(eligible & (values == 0.0))),
                "positive_candidate_count": positive_rows,
                "positive_semantic_block_count": positive_blocks,
                "raw_quantiles": quantiles,
                "raw_tail_max": float(np.max(quantile_values)),
                "training_scale": float(scales[atom_index]),
                "generation_scale": (
                    float(generation[atom_index]) if generation is not None else None
                ),
                "training_clip_saturation_weight": training_saturation,
                "generation_clip_saturation_weight": generation_saturation,
                "candidate_distinction": range_stats,
                "family_tier_route_drift": drift,
                "spearman_with_full_label_disclosed_direct_component": full_label_spearman,
                "spearman_with_label_minus_atom": spearman,
                "conditional_spearman_family_tier": conditional,
                "direct_label_component_positive_weight": float(
                    np.sum(applicable_weights[direct[:, :, atom_index] > 0.0])
                ),
                "status": status,
                "status_scope": (
                    "sealed_train_only_empirical_support_and_candidate_distinction_"
                    "not_static_formula_or_source_correctness"
                ),
                "warning": warning_reasons[0] if warning_reasons else None,
                "warning_reasons": warning_reasons,
                "failure_reasons": failure_reasons,
                "remediation_class": (
                    remediation_classes[0] if remediation_classes else None
                ),
                "remediation_classes": remediation_classes,
            }
        )
    correlation = _atom_correlation(normalized, source, atom_source, applicable, weights)
    delta_rank = _atom_delta_rank(normalized, source, atom_source, applicable, weights)
    ablations = _ablation_report(
        normalized,
        source,
        physical,
        weights,
        severity=np.asarray(severity, dtype=np.float64),
    )
    all_k_high_risk = np.all(source, axis=1) & ~np.any(physical, axis=1)
    return {
        "schema_version": "camp_dp_v25_train_only_atom_empirical_audit_v1",
        "atom_schema": "dp_camp_v10_14d",
        "paper_9d_prefix_indices": list(PAPER_9D_INDICES),
        "snapshot_count": int(raw.shape[0]),
        "candidate_count": int(raw.shape[0] * CANDIDATE_COUNT),
        "unique_route_count": len(set(routes)),
        "unique_semantic_block_count": len(set(blocks)),
        "all_k_high_risk_snapshot_count": int(np.sum(all_k_high_risk)),
        "weighting_contract": (
            "route_then_semantic_block_then_seed_then_tick_equal_mass_"
            "eligible_candidates_share_tick_mass"
        ),
        "label_contract": "train_only_causal_policy_distillation_no_outcome",
        "status_scope": (
            "sealed_train_only_empirical_support_and_candidate_distinction_"
            "not_static_formula_or_source_correctness"
        ),
        "static_correctness_prerequisite": (
            "formula_source_schema_clip_and_mask_failures_must_be_rejected_upstream"
        ),
        "correctness_checks": correctness_checks,
        "atom_rows": atom_rows,
        "weighted_spearman_correlation_matrix": correlation.tolist(),
        "atom_delta_effective_rank": delta_rank,
        "ablations": ablations,
        "status_counts": {
            status: sum(row["status"] == status for row in atom_rows)
            for status in ("PASS", "WARN", "FAIL")
        },
        "fresh_or_outcome_consumed": False,
    }


def _independent_row_correctness_checks(
    raw: np.ndarray,
    source: np.ndarray,
    atom_source: np.ndarray,
    applicable: np.ndarray,
) -> tuple[dict[str, Any], tuple[tuple[str, ...], ...]]:
    failures: list[list[str]] = [[] for _ in range(ATOM_COUNT)]

    jerk_mask = source & np.all(atom_source[:, :, :3], axis=2) & np.all(
        applicable[:, :, :3], axis=2
    )
    jerk_error = np.abs(raw[:, :, 2] - (raw[:, :, 0] + raw[:, :, 1]))
    jerk_tolerance = CORRECTNESS_ATOL + CORRECTNESS_RTOL * np.abs(raw[:, :, 2])
    jerk_violations = jerk_mask & (jerk_error > jerk_tolerance)
    if np.any(jerk_violations):
        for atom_index in (0, 1, 2):
            failures[atom_index].append("jerk_full_not_equal_early_plus_late")

    speed_mask = source & np.all(atom_source[:, :, 4:7], axis=2) & np.all(
        applicable[:, :, 4:7], axis=2
    )
    speed_violations = speed_mask & (
        (raw[:, :, 4] > raw[:, :, 5] + CORRECTNESS_ATOL)
        | (raw[:, :, 5] > raw[:, :, 6] + CORRECTNESS_ATOL)
    )
    if np.any(speed_violations):
        for atom_index in (4, 5, 6):
            failures[atom_index].append("speed_margin_costs_not_monotone_0_0_le_0_5_le_1_0")

    nonapplicable_counts: list[int] = []
    for atom_index in range(ATOM_COUNT):
        invalid = (
            atom_source[:, :, atom_index]
            & ~applicable[:, :, atom_index]
            & (np.abs(raw[:, :, atom_index]) > CORRECTNESS_ATOL)
        )
        count = int(np.sum(invalid))
        nonapplicable_counts.append(count)
        if count:
            failures[atom_index].append("nonapplicable_atom_must_be_exact_zero")

    progress_violation_count = 0
    for record_index in range(raw.shape[0]):
        eligible = (
            source[record_index]
            & atom_source[record_index, :, 9]
            & applicable[record_index, :, 9]
        )
        if not np.any(eligible) or float(np.min(raw[record_index, eligible, 9])) > CORRECTNESS_ATOL:
            progress_violation_count += 1
    if progress_violation_count:
        failures[9].append("progress_shortfall_source_valid_reference_has_no_zero_cost_candidate")

    dp_prior_mask = source[:, 0] & atom_source[:, 0, 13] & applicable[:, 0, 13]
    dp_prior_violations = dp_prior_mask & (np.abs(raw[:, 0, 13]) > CORRECTNESS_ATOL)
    if np.any(dp_prior_violations):
        failures[13].append("candidate0_dp_prior_jerk_excess_must_be_zero")

    checks = {
        "jerk_full_equals_early_plus_late": {
            "checked_candidate_count": int(np.sum(jerk_mask)),
            "violation_count": int(np.sum(jerk_violations)),
            "maximum_absolute_error": (
                float(np.max(jerk_error[jerk_mask])) if np.any(jerk_mask) else None
            ),
            "status": "FAIL" if np.any(jerk_violations) else "PASS",
        },
        "speed_margin_cost_monotonicity": {
            "formula_order": "margin_0_0_le_margin_0_5_le_margin_1_0",
            "checked_candidate_count": int(np.sum(speed_mask)),
            "violation_count": int(np.sum(speed_violations)),
            "status": "FAIL" if np.any(speed_violations) else "PASS",
        },
        "nonapplicable_atoms_are_zero": {
            "per_atom_violation_count": nonapplicable_counts,
            "violation_count": int(sum(nonapplicable_counts)),
            "status": "FAIL" if any(nonapplicable_counts) else "PASS",
        },
        "progress_source_valid_reference": {
            "checked_snapshot_count": int(raw.shape[0]),
            "violation_count": progress_violation_count,
            "status": "FAIL" if progress_violation_count else "PASS",
        },
        "candidate0_dp_prior_anchor": {
            "checked_snapshot_count": int(np.sum(dp_prior_mask)),
            "violation_count": int(np.sum(dp_prior_violations)),
            "status": "FAIL" if np.any(dp_prior_violations) else "PASS",
        },
    }
    return checks, tuple(tuple(items) for items in failures)


def _validate_atom_inputs(
    raw_atoms: np.ndarray,
    source_valid_mask: np.ndarray,
    atom_source_valid_mask: np.ndarray,
    atom_applicable_mask: np.ndarray,
    *,
    physical_feasible_mask: np.ndarray | None,
    snapshot_weights: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    raw = np.asarray(raw_atoms)
    if (
        raw.ndim != 3
        or raw.shape[1:] != (CANDIDATE_COUNT, ATOM_COUNT)
        or raw.dtype.kind not in "fiu"
        or raw.dtype.kind == "b"
    ):
        raise ValueError("raw_atoms must be native numeric [N,8,14]")
    raw = raw.astype(np.float64, copy=False)
    if not np.all(np.isfinite(raw)) or np.any(raw < 0.0):
        raise ValueError("raw_atoms must be finite nonnegative")
    source = _strict_bool_array(source_valid_mask, raw.shape[:2], "source_valid_mask")
    atom_source = _strict_bool_array(
        atom_source_valid_mask, raw.shape, "atom_source_valid_mask"
    )
    applicable = _strict_bool_array(
        atom_applicable_mask, raw.shape, "atom_applicable_mask"
    )
    if np.any(applicable & ~atom_source):
        raise ValueError("atom applicability requires atom source validity")
    if np.any(source != np.all(atom_source, axis=2)):
        raise ValueError("source_valid_mask must equal per-candidate atom-source conjunction")
    if np.any(~np.any(source, axis=1)):
        raise ValueError("every snapshot requires a nonempty source-valid set")
    if physical_feasible_mask is None:
        physical = np.zeros(raw.shape[:2], dtype=np.bool_)
    else:
        physical = _strict_bool_array(
            physical_feasible_mask, raw.shape[:2], "physical_feasible_mask"
        )
        if np.any(physical & ~source):
            raise ValueError("physical feasibility must be a subset of source validity")
    weights = np.asarray(snapshot_weights)
    if (
        weights.shape != (raw.shape[0],)
        or weights.dtype.kind not in "fiu"
        or weights.dtype.kind == "b"
    ):
        raise ValueError("snapshot_weights must be native numeric [N]")
    weights = weights.astype(np.float64, copy=False)
    if not np.all(np.isfinite(weights)) or np.any(weights <= 0.0):
        raise ValueError("snapshot_weights must be finite strictly positive")
    weights = weights / weights.sum()
    return raw, source, atom_source, applicable, physical, weights


def _candidate_weights(snapshot_weights: np.ndarray, mask: np.ndarray) -> np.ndarray:
    counts = np.sum(mask, axis=1)
    result = np.zeros(mask.shape, dtype=np.float64)
    valid_rows = counts > 0
    result[valid_rows] = (
        snapshot_weights[valid_rows, None] / counts[valid_rows, None]
    ) * mask[valid_rows]
    total = float(result.sum())
    if total > 0.0:
        result /= total
    return result


def _weighted_spearman(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float | None:
    if np.asarray(x).size < 2:
        return None
    values_x, w = _finite_values_and_weights(x, weights)
    values_y = np.asarray(y, dtype=np.float64).reshape(-1)
    if values_y.shape != values_x.shape or not np.all(np.isfinite(values_y)):
        raise ValueError("Spearman inputs must be aligned finite vectors")
    rank_x = _weighted_midrank(values_x, w)
    rank_y = _weighted_midrank(values_y, w)
    return _weighted_pearson(rank_x, rank_y, w)


def _weighted_midrank(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    result = np.empty(values.size, dtype=np.float64)
    cumulative = 0.0
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and values[order[end]] == values[order[start]]:
            end += 1
        group_weight = float(np.sum(weights[order[start:end]]))
        rank = cumulative + 0.5 * group_weight
        result[order[start:end]] = rank
        cumulative += group_weight
        start = end
    return result


def _weighted_pearson(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float | None:
    w = np.asarray(weights, dtype=np.float64).reshape(-1)
    w = w / w.sum()
    mean_x = float(np.sum(w * x))
    mean_y = float(np.sum(w * y))
    left = x - mean_x
    right = y - mean_y
    denominator = float(
        np.sqrt(np.sum(w * left * left) * np.sum(w * right * right))
    )
    if denominator <= 1e-15:
        return None
    return float(np.sum(w * left * right) / denominator)


def _stratum_residual_spearman(
    x_matrix: np.ndarray,
    y_matrix: np.ndarray,
    weight_matrix: np.ndarray,
    mask: np.ndarray,
    snapshot_strata: Sequence[str],
) -> float | None:
    if not np.any(mask):
        return None
    x = x_matrix[mask]
    y = y_matrix[mask]
    w = weight_matrix[mask]
    repeated = np.repeat(np.asarray(snapshot_strata, dtype=object), CANDIDATE_COUNT)
    labels = repeated[mask.reshape(-1)]
    rank_x = _weighted_midrank(x, w)
    rank_y = _weighted_midrank(y, w)
    for label in sorted(set(labels)):
        group = labels == label
        local = w[group] / np.sum(w[group])
        rank_x[group] -= float(np.sum(local * rank_x[group]))
        rank_y[group] -= float(np.sum(local * rank_y[group]))
    return _weighted_pearson(rank_x, rank_y, w)


def _atom_correlation(
    normalized: np.ndarray,
    source: np.ndarray,
    atom_source: np.ndarray,
    applicable: np.ndarray,
    snapshot_weights: np.ndarray,
) -> np.ndarray:
    result = np.eye(ATOM_COUNT, dtype=np.float64)
    for left in range(ATOM_COUNT):
        for right in range(left + 1, ATOM_COUNT):
            mask = (
                source
                & atom_source[:, :, left]
                & atom_source[:, :, right]
                & applicable[:, :, left]
                & applicable[:, :, right]
            )
            weights = _candidate_weights(snapshot_weights, mask)
            value = _weighted_spearman(
                normalized[:, :, left][mask],
                normalized[:, :, right][mask],
                weights[mask],
            )
            result[left, right] = result[right, left] = 0.0 if value is None else value
    return result


def _candidate_distinction_stats(
    values: np.ndarray,
    eligible: np.ndarray,
    snapshot_weights: np.ndarray,
) -> dict[str, Any]:
    ranges: list[float] = []
    variances: list[float] = []
    weights: list[float] = []
    for index in range(values.shape[0]):
        row = values[index, eligible[index]]
        if row.size < 2:
            continue
        ranges.append(float(np.max(row) - np.min(row)))
        variances.append(float(np.var(row)))
        weights.append(float(snapshot_weights[index]))
    if not ranges:
        return {
            "eligible_snapshot_count": 0,
            "positive_range_weight": 0.0,
            "range_q05_q50_q95_q99": [None, None, None, None],
            "variance_q05_q50_q95_q99": [None, None, None, None],
        }
    range_values = np.asarray(ranges, dtype=np.float64)
    variance_values = np.asarray(variances, dtype=np.float64)
    weight_values = np.asarray(weights, dtype=np.float64)
    weight_values /= weight_values.sum()
    points = (0.05, 0.50, 0.95, 0.99)
    return {
        "eligible_snapshot_count": len(ranges),
        "positive_range_weight": float(np.sum(weight_values[range_values > 0.0])),
        "range_q05_q50_q95_q99": [
            weighted_quantile(range_values, weight_values, point) for point in points
        ],
        "variance_q05_q50_q95_q99": [
            weighted_quantile(variance_values, weight_values, point) for point in points
        ],
    }


def _atom_group_drift(
    values: np.ndarray,
    source_mask: np.ndarray,
    snapshot_weights: np.ndarray,
    *,
    family_tier: Sequence[str],
    route_ids: Sequence[str],
) -> dict[str, Any]:
    family_rows = _group_q95_rows(
        values,
        source_mask,
        snapshot_weights,
        family_tier,
    )
    route_rows = _group_q95_rows(
        values,
        source_mask,
        snapshot_weights,
        route_ids,
    )
    route_q95 = np.asarray(
        [row["raw_q95"] for row in route_rows], dtype=np.float64
    )
    return {
        "family_tier_rows": family_rows,
        "route_group_count": len(route_rows),
        "route_q95_q10_q50_q90": (
            np.quantile(route_q95, (0.10, 0.50, 0.90)).tolist()
            if route_q95.size
            else [None, None, None]
        ),
        "route_q95_min_max": (
            [float(np.min(route_q95)), float(np.max(route_q95))]
            if route_q95.size
            else [None, None]
        ),
    }


def _group_q95_rows(
    values: np.ndarray,
    source_mask: np.ndarray,
    snapshot_weights: np.ndarray,
    groups: Sequence[str],
) -> list[dict[str, Any]]:
    group_values = np.asarray(groups, dtype=object)
    rows: list[dict[str, Any]] = []
    for group in sorted(set(groups)):
        snapshot_mask = group_values == group
        mask = source_mask & snapshot_mask[:, None]
        candidate_weights = _candidate_weights(snapshot_weights, mask)
        rows.append(
            {
                "group": group,
                "snapshot_count": int(np.sum(snapshot_mask)),
                "source_candidate_count": int(np.sum(mask)),
                "raw_q95": weighted_quantile(
                    values[mask], candidate_weights[mask], 0.95
                ),
                "zero_candidate_fraction": float(np.mean(values[mask] == 0.0)),
                "positive_candidate_fraction": float(np.mean(values[mask] > 0.0)),
            }
        )
    return rows


def _atom_delta_rank(
    normalized: np.ndarray,
    source: np.ndarray,
    atom_source: np.ndarray,
    applicable: np.ndarray,
    snapshot_weights: np.ndarray,
) -> dict[str, Any]:
    rows: list[np.ndarray] = []
    row_weights: list[float] = []
    usable_atoms = np.where(atom_source & applicable, normalized, 0.0)
    for index in range(normalized.shape[0]):
        candidates = source[index] & np.all(atom_source[index], axis=1)
        candidate_indices = np.flatnonzero(candidates)
        if candidate_indices.size < 2:
            continue
        matrix = usable_atoms[index, candidate_indices]
        centered = matrix - np.mean(matrix, axis=0, keepdims=True)
        rows.extend(centered)
        row_weights.extend(
            [float(snapshot_weights[index]) / candidate_indices.size] * candidate_indices.size
        )
    if not rows:
        return {
            "candidate_delta_row_count": 0,
            "numerical_rank": 0,
            "effective_rank": 0.0,
            "condition_number": None,
            "singular_values": [],
        }
    matrix = np.asarray(rows, dtype=np.float64)
    weights = np.asarray(row_weights, dtype=np.float64)
    weighted = matrix * np.sqrt(weights[:, None] / weights.sum())
    singular = np.linalg.svd(weighted, full_matrices=False, compute_uv=False)
    tolerance = max(weighted.shape) * np.finfo(np.float64).eps * singular[0]
    nonzero = singular[singular > tolerance]
    energy = singular * singular
    probabilities = energy / energy.sum() if energy.sum() > 0.0 else energy
    effective = (
        float(np.exp(-np.sum(probabilities[probabilities > 0.0] * np.log(probabilities[probabilities > 0.0]))))
        if np.any(probabilities > 0.0)
        else 0.0
    )
    return {
        "candidate_delta_row_count": int(matrix.shape[0]),
        "numerical_rank": int(nonzero.size),
        "effective_rank": effective,
        "condition_number": (
            float(nonzero[0] / nonzero[-1]) if nonzero.size > 1 else None
        ),
        "singular_values": singular.tolist(),
    }


def _ablation_report(
    normalized: np.ndarray,
    source: np.ndarray,
    physical: np.ndarray,
    weights: np.ndarray,
    *,
    severity: np.ndarray,
) -> dict[str, Any]:
    severity_values = _nonnegative_vector(severity, ATOM_COUNT, "severity")
    full = _select_with_atom_mask(
        normalized,
        source,
        physical,
        severity_values,
        np.ones(ATOM_COUNT, dtype=bool),
    )
    reports: dict[str, Any] = {}
    masks: dict[str, np.ndarray] = {
        "paper_9d_vs_14d": np.asarray([index in PAPER_9D_INDICES for index in range(ATOM_COUNT)]),
    }
    for index, name in enumerate(ATOM_NAMES):
        mask = np.ones(ATOM_COUNT, dtype=bool)
        mask[index] = False
        masks[f"14d_minus_{name}"] = mask
    for group, indices in DEFAULT_ABLATION_GROUPS.items():
        mask = np.ones(ATOM_COUNT, dtype=bool)
        mask[list(indices)] = False
        masks[f"14d_minus_group_{group}"] = mask
    for name, active in masks.items():
        selected = _select_with_atom_mask(
            normalized, source, physical, severity_values, active
        )
        flip = selected["indices"] != full["indices"]
        selected_physical = physical[np.arange(physical.shape[0]), selected["indices"]]
        reports[name] = {
            "active_atom_indices": np.flatnonzero(active).tolist(),
            "selected_index_flip_weight": float(np.sum(weights[flip])),
            "selected_index_flip_count": int(np.sum(flip)),
            "nonzero_selected_weight": float(np.sum(weights[selected["indices"] != 0])),
            "selected_physical_feasible_weight": float(np.sum(weights[selected_physical])),
            "two_or_more_source_valid_weight": float(
                np.sum(weights[selected["eligible_counts"] >= 2])
            ),
            "selection_margin_q50": weighted_quantile(selected["margins"], weights, 0.5),
            "selection_margin_q95": weighted_quantile(selected["margins"], weights, 0.95),
        }
    return {
        "reference": {
            "name": "causal_label_severity_14d",
            "nonzero_selected_weight": float(np.sum(weights[full["indices"] != 0])),
            "selected_physical_feasible_weight": float(
                np.sum(weights[physical[np.arange(physical.shape[0]), full["indices"]]])
            ),
            "two_or_more_source_valid_weight": float(
                np.sum(weights[full["eligible_counts"] >= 2])
            ),
            "selection_margin_q50": weighted_quantile(full["margins"], weights, 0.5),
            "selection_margin_q95": weighted_quantile(full["margins"], weights, 0.95),
        },
        "comparisons": reports,
    }


def _select_with_atom_mask(
    normalized: np.ndarray,
    source: np.ndarray,
    physical: np.ndarray,
    severity: np.ndarray,
    active: np.ndarray,
) -> dict[str, np.ndarray]:
    scores = (
        normalized[:, :, active] @ severity[active]
        + 100.0 * (~physical)
    )
    scores = np.where(source, scores, np.inf)
    indices = np.argmin(scores, axis=1).astype(np.int64)
    sorted_scores = np.sort(scores, axis=1)
    margins = sorted_scores[:, 1] - sorted_scores[:, 0]
    eligible_counts = np.sum(source, axis=1)
    margins[eligible_counts < 2] = 0.0
    return {
        "indices": indices,
        "margins": margins,
        "eligible_counts": eligible_counts,
    }


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


def _finite_values_and_weights(
    values: np.ndarray, weights: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
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
