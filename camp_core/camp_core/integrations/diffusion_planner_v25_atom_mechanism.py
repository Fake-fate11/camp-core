from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner_causal_atoms import canonical_normalize_atoms
from .diffusion_planner_v25_calibration_atoms import (
    _decision_snapshot,
    _load_ablation_assets,
    _scene9_weights,
    _simplex,
)
from .diffusion_planner_v25_scene_runtime import V25Scene14DWeightProvider
from .diffusion_planner_v25_statistics import SAFETY_COMPONENTS
from .diffusion_planner_v25_train_atom_audit import ATOM_NAMES


SCHEMA_VERSION = "camp_dp_v25_atom_mechanism_analysis_v1"
CONTRACT_SCHEMA_VERSION = "camp_dp_v25_atom_mechanism_contract_v1"
BINDING_SCHEMA_VERSION = "camp_dp_v25_atom_mechanism_preopen_binding_v1"
ARMS = ("camp_static14d", "camp_scene14d_no_v2i")
GROUPS = {
    "jerk_full_early_late": (0, 1, 2),
    "speed_margin_three_thresholds": (4, 5, 6),
    "red_signal": (10, 12),
    "geometry_lane_clearance": (7, 8),
    "progress_default_prior": (9, 13),
    "lateral_dynamics": (3, 11),
}
OUTCOME_METRICS = (
    "safety_cost_total",
    *(f"safety_component.{name}" for name in SAFETY_COMPONENTS),
    "progress",
    "mean_jerk",
    "max_jerk",
    "mean_lateral_acceleration",
    "max_lateral_acceleration",
)
MECHANISM_SUMMARY_STORAGE_UPPER_BOUND_BYTES = 64 * 1024**2


def mechanism_names() -> list[str]:
    return list(_mechanism_names())


def validate_atom_mechanism_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "schema_version",
        "status",
        "artifact_path",
        "artifact_root_sha256",
        "review_artifact_path",
        "review_root_sha256",
        "contract_sha256",
        "analysis_sha256",
        "decision_tick_count",
        "mechanism_names",
        "raw_k8_payload_copied",
        "primary_fresh_design_changed",
        "model_or_weight_changed",
        "single_atom_closed_loop_causal_effect_claimed",
        "fresh_storage_capacity_gate_passed",
        "storage_projected_1500_arm_upper_bound_nbytes_with_mechanism",
        "fresh_b2_opened",
        "fresh_outcome_fields_consumed",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("atom-mechanism pre-open binding field set drifted")
    exact = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "status": "passed_independent_atom_mechanism_preopen_review",
        "decision_tick_count": 12_800,
        "mechanism_names": list(_mechanism_names()),
        "raw_k8_payload_copied": False,
        "primary_fresh_design_changed": False,
        "model_or_weight_changed": False,
        "single_atom_closed_loop_causal_effect_claimed": False,
        "fresh_storage_capacity_gate_passed": True,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    if any(not _strict_equal(value.get(name), expected) for name, expected in exact.items()):
        raise ValueError("atom-mechanism pre-open binding value drifted")
    for name in ("artifact_root_sha256", "review_root_sha256", "contract_sha256", "analysis_sha256"):
        item = value.get(name)
        if type(item) is not str or len(item) != 64 or any(ch not in "0123456789abcdef" for ch in item):
            raise ValueError(f"atom-mechanism pre-open binding {name} is invalid")
    for name in ("artifact_path", "review_artifact_path"):
        item = value.get(name)
        if type(item) is not str or not item or str(Path(item).resolve()) != item:
            raise ValueError(f"atom-mechanism pre-open binding {name} is not canonical")
    projected = value.get("storage_projected_1500_arm_upper_bound_nbytes_with_mechanism")
    if type(projected) is not int or isinstance(projected, bool) or projected <= MECHANISM_SUMMARY_STORAGE_UPPER_BOUND_BYTES:
        raise ValueError("atom-mechanism storage projection is invalid")
    return dict(value)


def validate_atom_mechanism_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("atom-mechanism contract must be an object")
    expected_keys = {
        "schema_version",
        "status",
        "atom_names",
        "paper_9d_indices",
        "groups",
        "primary_fresh_arms_unchanged",
        "paper_9d_definition",
        "contribution_removal_definition",
        "runtime_projection_or_renormalization_used",
        "independent_retraining_or_model_change_used",
        "selection_contract",
        "association_contract",
        "scene_interpretation",
        "fresh_repeat_contract",
        "single_atom_closed_loop_causal_effect_claimed",
        "single_atom_closed_loop_benchmark_disposition",
        "evidence_storage_contract",
        "fresh_b2_opened",
        "fresh_outcome_fields_consumed",
    }
    if set(value) != expected_keys:
        raise ValueError("atom-mechanism contract field set drifted")
    expected_values = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "status": "frozen_before_fresh_b2_opening",
        "atom_names": list(ATOM_NAMES),
        "paper_9d_indices": list(range(9)),
        "groups": {name: list(indices) for name, indices in GROUPS.items()},
        "primary_fresh_arms_unchanged": [
            "candidate0_operational_default",
            "camp_static14d",
            "camp_scene14d_no_v2i",
        ],
        "paper_9d_definition": (
            "accepted_independently_trained_static9d_and_scene9d_models_"
            "rescored_on_the_same_saved_fixed_k8_candidate_pool"
        ),
        "contribution_removal_definition": (
            "diagnostic_score_without_atom_or_group_equals_official_affine_score_"
            "minus_sum_j_of_clip_atom_over_scale_0_10_times_frozen_weight_j"
        ),
        "runtime_projection_or_renormalization_used": False,
        "independent_retraining_or_model_change_used": False,
        "selection_contract": (
            "same_source_valid_eligibility_argmin_with_lowest_index_tie_break"
        ),
        "association_contract": {
            "level": "corridor_cluster",
            "statistic": "spearman_rho_over_equal_mass_corridor_means",
            "outcome_delta": "camp_minus_candidate0",
            "interpretation": "mechanism_association_not_single_atom_causal_effect",
            "metrics": list(OUTCOME_METRICS),
        },
        "scene_interpretation": (
            "report_context_specific_w_x_and_atom_times_weight_contributions_"
            "without_causal_interpretation_of_redundant_theta_coefficients"
        ),
        "fresh_repeat_contract": (
            "repeat_the_identical_frozen_mechanism_analysis_after_fresh_"
            "without_changing_groups_thresholds_or_models"
        ),
        "single_atom_closed_loop_causal_effect_claimed": False,
        "single_atom_closed_loop_benchmark_disposition": (
            "separate_preregistered_ablation_benchmark_or_v26_not_fresh_b2_extra_arms"
        ),
        "evidence_storage_contract": {
            "raw_k8_payload_copied": False,
            "reuse_content_addressed_shard_references": True,
            "summary_upper_bound_bytes": MECHANISM_SUMMARY_STORAGE_UPPER_BOUND_BYTES,
        },
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    if not _strict_equal(value, expected_values):
        raise ValueError("atom-mechanism contract value drifted")
    return dict(value)


def analyze_atom_mechanisms(
    *,
    decision_runs: Sequence[Mapping[str, Any]],
    outcomes_by_unit: Mapping[int, Mapping[str, Mapping[str, Any]]],
    atom_scales: np.ndarray,
    static14d_weights: np.ndarray,
    scene14d_provider: V25Scene14DWeightProvider,
    training_artifact: Path,
) -> dict[str, Any]:
    scales = _finite_array(atom_scales, (14,), "atom_scales")
    if np.any(scales <= 0.0):
        raise ValueError("atom scales must be finite positive")
    static14 = _simplex(static14d_weights, 14, "Static14D weights")
    ablations = _load_ablation_assets(Path(training_artifact))
    accumulator = {
        arm: _arm_accumulator() for arm in ARMS
    }
    run_rows: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for run in decision_runs:
        arm = run.get("plan_arm")
        unit = run.get("unit_ordinal")
        if arm not in ARMS or type(unit) is not int or unit < 0:
            raise ValueError("atom-mechanism decision-run authority drifted")
        key = (unit, arm)
        if key in seen:
            raise ValueError("duplicate atom-mechanism decision run")
        seen.add(key)
        run_rows.append(
            _analyze_run(
                run=run,
                arm=arm,
                unit=unit,
                scales=scales,
                static14=static14,
                scene14d_provider=scene14d_provider,
                ablations=ablations,
                arm_accumulator=accumulator[arm],
            )
        )
    if not run_rows or any(not any(row["plan_arm"] == arm for row in run_rows) for arm in ARMS):
        raise ValueError("atom-mechanism analysis requires both CAMP arms")
    outcomes = _validate_outcomes(outcomes_by_unit, seen)
    associations = _associations(run_rows, outcomes)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "completed_frozen_calibration_atom_mechanism_association",
        "analysis_kind": "offline_same_saved_k8_mechanism_association",
        "atom_names": list(ATOM_NAMES),
        "groups": {name: list(indices) for name, indices in GROUPS.items()},
        "arm_reports": {
            arm: _finalize_arm(accumulator[arm]) for arm in ARMS
        },
        "corridor_cluster_associations": associations,
        "outcome_delta_definition": "camp_minus_candidate0",
        "association_is_causal_effect": False,
        "counterfactual_closed_loop_executed": False,
        "runtime_projection_or_renormalization_used": False,
        "model_or_weight_changed": False,
        "primary_fresh_design_changed": False,
        "fresh_repeat_required_on_identical_frozen_code": True,
        "raw_k8_payload_copied": False,
        "summary_storage_upper_bound_bytes": MECHANISM_SUMMARY_STORAGE_UPPER_BOUND_BYTES,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }


def _analyze_run(
    *,
    run: Mapping[str, Any],
    arm: str,
    unit: int,
    scales: np.ndarray,
    static14: np.ndarray,
    scene14d_provider: V25Scene14DWeightProvider,
    ablations: Mapping[str, Any],
    arm_accumulator: dict[str, Any],
) -> dict[str, Any]:
    required_text = (
        "corridor_sha256",
        "scenario_family",
        "risk_tier",
        "signal_source_class",
        "phase_authority_mode",
    )
    if any(type(run.get(name)) is not str or not run[name] for name in required_text):
        raise ValueError("atom-mechanism run stratum metadata drifted")
    snapshots = run.get("snapshots")
    native_ticks = run.get("native_ticks")
    if type(snapshots) is not list or len(snapshots) != 64 or type(native_ticks) is not list or len(native_ticks) != 64:
        raise ValueError("atom-mechanism run must contain exactly 64 ticks")
    per_run = {
        name: {"trigger": 0, "flip": 0} for name in _mechanism_names()
    }
    for tick_index, (snapshot, native_tick) in enumerate(zip(snapshots, native_ticks, strict=True)):
        atoms, source, applicable, eligible, stored_scores, stored_index = _decision_snapshot(snapshot, tick_index=tick_index)
        if native_tick.get("tick_index") != tick_index or native_tick.get("scores") != snapshot["sidecar"]["scores"] or native_tick.get("selected_index") != stored_index:
            raise ValueError("atom-mechanism native/snapshot binding drifted")
        normalized = canonical_normalize_atoms(atoms, scales)
        if arm == "camp_static14d":
            weights = static14
            weights9 = ablations["static9d_weights"]
        else:
            context = native_tick.get("v25_context")
            if type(context) is not dict:
                raise ValueError("Scene14D mechanism context is missing")
            provided = scene14d_provider(context)
            weights = _simplex(provided["weights"], 14, "Scene14D weights")
            if native_tick.get("v25_scene_selector") != {key: value for key, value in provided.items() if key != "weights"}:
                raise ValueError("Scene14D mechanism weight receipt drifted")
            weights9 = _scene9_weights(context, ablations)
        official = normalized @ weights
        if not np.array_equal(official, stored_scores):
            raise ValueError("atom-mechanism official affine scores drifted")
        selected = _eligible_argmin(official, eligible)
        if selected != stored_index:
            raise ValueError("atom-mechanism official selected index drifted")
        official_margin = _margin(official, eligible)
        all_k_high_risk = native_tick.get("all_k_high_risk")
        if type(all_k_high_risk) is not bool:
            raise ValueError("atom-mechanism all-K-high-risk evidence drifted")
        mechanisms: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        scores9 = normalized[:, :9] @ weights9
        mechanisms["paper_9d_vs_14d"] = (scores9, np.zeros(8, dtype=np.float64))
        for index, name in enumerate(ATOM_NAMES):
            contribution = normalized[:, index] * weights[index]
            mechanisms[f"atom:{name}"] = (official - contribution, contribution)
        for name, indices in GROUPS.items():
            contribution = np.sum(normalized[:, list(indices)] * weights[list(indices)], axis=1)
            mechanisms[f"group:{name}"] = (official - contribution, contribution)
        strata = {
            "family": run["scenario_family"],
            "tier": run["risk_tier"],
            "source_mode": f"{run['signal_source_class']}|{run['phase_authority_mode']}",
        }
        for name, (diagnostic_scores, contribution) in mechanisms.items():
            diagnostic_selected = _eligible_argmin(diagnostic_scores, eligible)
            trigger = bool(np.any(contribution[eligible] > 0.0)) if name != "paper_9d_vs_14d" else True
            flip = diagnostic_selected != selected
            row = arm_accumulator["mechanisms"][name]
            row["tick_count"] += 1
            row["trigger_count"] += int(trigger)
            row["selected_flip_count"] += int(flip)
            row["candidate0_to_non0_count"] += int(selected == 0 and diagnostic_selected != 0)
            row["non0_to_candidate0_count"] += int(selected != 0 and diagnostic_selected == 0)
            row["margin_delta_sum"] += _margin(diagnostic_scores, eligible) - official_margin
            row["selected_contribution_sum"] += float(contribution[selected])
            row["all_k_high_risk_tick_count"] += int(all_k_high_risk)
            row["all_k_high_risk_flip_count"] += int(all_k_high_risk and flip)
            for dimension, value in strata.items():
                cell = row["strata"][dimension][value]
                cell["tick_count"] += 1
                cell["trigger_count"] += int(trigger)
                cell["selected_flip_count"] += int(flip)
            per_run[name]["trigger"] += int(trigger)
            per_run[name]["flip"] += int(flip)
        valid = source & applicable
        arm_accumulator["source_count"] += valid.sum(axis=0)
        arm_accumulator["positive_count"] += ((atoms > 0.0) & valid).sum(axis=0)
        arm_accumulator["candidate_atom_row_count"] += 8
    return {
        "unit_ordinal": unit,
        "plan_arm": arm,
        "corridor_sha256": run["corridor_sha256"],
        "mechanisms": {
            name: {
                "trigger_rate": values["trigger"] / 64.0,
                "selected_flip_rate": values["flip"] / 64.0,
            }
            for name, values in per_run.items()
        },
    }


def _arm_accumulator() -> dict[str, Any]:
    def mechanism() -> dict[str, Any]:
        return {
            "tick_count": 0,
            "trigger_count": 0,
            "selected_flip_count": 0,
            "candidate0_to_non0_count": 0,
            "non0_to_candidate0_count": 0,
            "margin_delta_sum": 0.0,
            "selected_contribution_sum": 0.0,
            "all_k_high_risk_tick_count": 0,
            "all_k_high_risk_flip_count": 0,
            "strata": {
                name: defaultdict(lambda: {"tick_count": 0, "trigger_count": 0, "selected_flip_count": 0})
                for name in ("family", "tier", "source_mode")
            },
        }
    return {
        "mechanisms": defaultdict(mechanism),
        "source_count": np.zeros(14, dtype=np.int64),
        "positive_count": np.zeros(14, dtype=np.int64),
        "candidate_atom_row_count": 0,
    }


def _finalize_arm(value: Mapping[str, Any]) -> dict[str, Any]:
    mechanisms = {}
    for name in _mechanism_names():
        row = value["mechanisms"][name]
        ticks = row["tick_count"]
        if ticks <= 0:
            raise ValueError("atom-mechanism arm has no ticks")
        mechanisms[name] = {
            "tick_count": ticks,
            "trigger_rate": row["trigger_count"] / ticks,
            "selected_flip_rate": row["selected_flip_count"] / ticks,
            "candidate0_to_non0_rate": row["candidate0_to_non0_count"] / ticks,
            "non0_to_candidate0_rate": row["non0_to_candidate0_count"] / ticks,
            "mean_margin_change_after_diagnostic_removal": row["margin_delta_sum"] / ticks,
            "mean_official_selected_contribution": row["selected_contribution_sum"] / ticks,
            "all_k_high_risk_tick_count": row["all_k_high_risk_tick_count"],
            "all_k_high_risk_selected_flip_count": row["all_k_high_risk_flip_count"],
            "strata": {
                dimension: {
                    cell: {
                        "tick_count": counts["tick_count"],
                        "trigger_rate": counts["trigger_count"] / counts["tick_count"],
                        "selected_flip_rate": counts["selected_flip_count"] / counts["tick_count"],
                    }
                    for cell, counts in sorted(rows.items())
                }
                for dimension, rows in row["strata"].items()
            },
        }
    candidate_rows = int(value["candidate_atom_row_count"])
    atom_status = []
    for index, name in enumerate(ATOM_NAMES):
        source = int(value["source_count"][index])
        positive = int(value["positive_count"][index])
        atom_status.append({
            "index": index,
            "name": name,
            "status": "PASS" if source > 0 and positive > 0 else "WARN",
            "warning": None if source > 0 and positive > 0 else "source_or_positive_support_limited",
            "source_activation_rate": 0.0 if candidate_rows == 0 else source / candidate_rows,
            "positive_activation_rate": 0.0 if source == 0 else positive / source,
            "primary_14d_member": True,
            "paper_9d_subset_member": index < 9,
            "source_unavailable_is_masked": True,
        })
    return {
        "decision_tick_count": mechanisms["paper_9d_vs_14d"]["tick_count"],
        "candidate_atom_row_count": candidate_rows,
        "atom_status": atom_status,
        "mechanisms": mechanisms,
        "scene_theta_coefficients_given_causal_interpretation": False,
    }


def _validate_outcomes(value: Mapping[int, Mapping[str, Mapping[str, Any]]], seen: set[tuple[int, str]]) -> dict[int, dict[str, Mapping[str, Any]]]:
    result: dict[int, dict[str, Mapping[str, Any]]] = {}
    units = {unit for unit, _arm in seen}
    for unit in units:
        rows = value.get(unit)
        if type(rows) is not dict or set(rows) != {"candidate0_operational_default", *ARMS}:
            raise ValueError("atom-mechanism paired outcome denominator drifted")
        corridor = None
        normalized = {}
        for arm, row in rows.items():
            if type(row) is not dict:
                raise ValueError("atom-mechanism outcome row drifted")
            current = row.get("corridor_sha256")
            if type(current) is not str or not current or (corridor is not None and current != corridor):
                raise ValueError("atom-mechanism corridor pairing drifted")
            corridor = current
            normalized[arm] = row
        result[unit] = normalized
    return result


def _associations(run_rows: Sequence[Mapping[str, Any]], outcomes: Mapping[int, Mapping[str, Mapping[str, Any]]]) -> dict[str, Any]:
    result = {}
    for arm in ARMS:
        selected = [row for row in run_rows if row["plan_arm"] == arm]
        arm_result = {}
        for mechanism in _mechanism_names():
            exposures = {"trigger_rate": defaultdict(list), "selected_flip_rate": defaultdict(list)}
            outcomes_by_corridor: defaultdict[str, list[dict[str, float]]] = defaultdict(list)
            for run in selected:
                unit = run["unit_ordinal"]
                rows = outcomes[unit]
                baseline = rows["candidate0_operational_default"]
                method = rows[arm]
                corridor = run["corridor_sha256"]
                if corridor != method["corridor_sha256"]:
                    raise ValueError("atom-mechanism decision/outcome corridor drifted")
                for exposure in exposures:
                    exposures[exposure][corridor].append(run["mechanisms"][mechanism][exposure])
                outcomes_by_corridor[corridor].append(_outcome_delta(method, baseline))
            mechanism_result = {}
            for exposure, by_corridor in exposures.items():
                corridors = sorted(by_corridor)
                x = np.asarray([np.mean(by_corridor[corridor]) for corridor in corridors], dtype=np.float64)
                mechanism_result[exposure] = {}
                for metric in OUTCOME_METRICS:
                    y = np.asarray([np.mean([row[metric] for row in outcomes_by_corridor[corridor]]) for corridor in corridors], dtype=np.float64)
                    mechanism_result[exposure][metric] = _spearman_summary(x, y)
            arm_result[mechanism] = mechanism_result
        result[arm] = arm_result
    return result


def _outcome_delta(method: Mapping[str, Any], baseline: Mapping[str, Any]) -> dict[str, float]:
    result = {"safety_cost_total": _finite(method["safety_cost"], "method.safety_cost") - _finite(baseline["safety_cost"], "baseline.safety_cost")}
    for name in SAFETY_COMPONENTS:
        result[f"safety_component.{name}"] = _finite(method["components"][name], name) - _finite(baseline["components"][name], name)
    for name in ("progress", "mean_jerk", "max_jerk", "mean_lateral_acceleration", "max_lateral_acceleration"):
        result[name] = _finite(method["performance"][name], name) - _finite(baseline["performance"][name], name)
    return result


def _spearman_summary(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    if x.shape != y.shape or x.ndim != 1 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("atom-mechanism association inputs drifted")
    count = int(x.size)
    if count < 3 or np.all(x == x[0]) or np.all(y == y[0]):
        return {"corridor_cluster_count": count, "spearman_rho": None, "status": "insufficient_cluster_variation"}
    rx = _average_ranks(x)
    ry = _average_ranks(y)
    rho = float(np.corrcoef(rx, ry)[0, 1])
    if not np.isfinite(rho):
        raise ValueError("atom-mechanism correlation is nonfinite")
    return {"corridor_cluster_count": count, "spearman_rho": rho, "status": "descriptive_association_only"}


def _average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1) + 1.0
        start = end
    return ranks


def _mechanism_names() -> tuple[str, ...]:
    return (
        "paper_9d_vs_14d",
        *(f"atom:{name}" for name in ATOM_NAMES),
        *(f"group:{name}" for name in GROUPS),
    )


def _eligible_argmin(scores: np.ndarray, eligible: np.ndarray) -> int:
    if not eligible.any():
        raise ValueError("atom-mechanism eligibility is empty")
    return int(np.argmin(np.where(eligible, scores, np.inf)))


def _margin(scores: np.ndarray, eligible: np.ndarray) -> float:
    ordered = np.sort(scores[eligible])
    return 0.0 if ordered.size < 2 else float(ordered[1] - ordered[0])


def _finite_array(value: Any, shape: tuple[int, ...], name: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != shape or raw.dtype.kind not in "fiu" or raw.dtype.kind == "b":
        raise ValueError(f"{name} shape/type drifted")
    result = raw.astype(np.float64, copy=False)
    if not np.isfinite(result).all():
        raise ValueError(f"{name} must be finite")
    return result


def _finite(value: Any, name: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool) or not np.isfinite(float(value)):
        raise ValueError(f"{name} must be finite native numeric")
    return float(value)


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_strict_equal(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_strict_equal(a, b) for a, b in zip(left, right, strict=True))
    return bool(left == right)
