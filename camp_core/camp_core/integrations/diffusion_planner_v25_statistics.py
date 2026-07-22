from __future__ import annotations

from collections import defaultdict
from statistics import NormalDist
from typing import Any, Sequence

import numpy as np
from scipy.stats import t as student_t


SAFETY_COMPONENTS = (
    "collision",
    "near_miss",
    "offroad",
    "red_light",
    "speed",
    "wrong_way",
)
NONINFERIORITY_METRICS = (
    "progress",
    "completion",
    "mean_jerk",
    "max_jerk",
    "mean_lateral_acceleration",
    "max_lateral_acceleration",
    "maximum_deceleration",
)
REQUIRED_CONTROLLED_EVENT_FAMILIES = (
    "lead_vehicle_hard_brake",
    "cut_in_merge",
    "pedestrian_cyclist_crossing",
    "unprotected_turn_oncoming_conflict",
    "red_light_phase_timing",
    "blocked_lane_static_obstacle",
    "narrow_encounter",
)


def clustered_paired_summary(
    paired_deltas: np.ndarray,
    cluster_ids: Sequence[str],
    *,
    confidence: float = 0.95,
    tie_tolerance: float = 0.0,
) -> dict[str, Any]:
    """Summarize paired deltas with equal-mass independent cluster means.

    ``paired_deltas`` is method minus candidate0, so negative is safer for
    SafetyCost and other harm metrics. Seeds/ticks inside a cluster are repeated
    measurements, never independent sample units.
    """

    deltas = _finite_vector(paired_deltas, "paired_deltas")
    clusters = _cluster_strings(cluster_ids, deltas.size)
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie in (0,1)")
    if not np.isfinite(tie_tolerance) or tie_tolerance < 0.0:
        raise ValueError("tie_tolerance must be finite nonnegative")
    grouped: dict[str, list[float]] = defaultdict(list)
    for cluster, value in zip(clusters, deltas, strict=True):
        grouped[cluster].append(float(value))
    cluster_means = np.asarray(
        [np.mean(grouped[key]) for key in sorted(grouped)], dtype=np.float64
    )
    if cluster_means.size < 2:
        raise ValueError("clustered inference requires at least two clusters")
    mean = float(np.mean(cluster_means))
    standard_deviation = float(np.std(cluster_means, ddof=1))
    standard_error = standard_deviation / np.sqrt(cluster_means.size)
    two_sided_critical = float(
        student_t.ppf(0.5 + confidence / 2.0, df=cluster_means.size - 1)
    )
    one_sided_critical = float(
        student_t.ppf(confidence, df=cluster_means.size - 1)
    )
    half_width = two_sided_critical * standard_error
    upper_one_sided = mean + one_sided_critical * standard_error
    better = int(np.sum(deltas < -tie_tolerance))
    worse = int(np.sum(deltas > tie_tolerance))
    tie = int(deltas.size - better - worse)
    return {
        "schema_version": "camp_dp_v25_clustered_paired_summary_v1",
        "estimator": "equal_mass_cluster_mean_student_t",
        "confidence": float(confidence),
        "observation_count": int(deltas.size),
        "independent_cluster_count": int(cluster_means.size),
        "cluster_measurement_counts": {
            key: len(grouped[key]) for key in sorted(grouped)
        },
        "mean_delta": mean,
        "cluster_standard_deviation": standard_deviation,
        "cluster_standard_error": standard_error,
        "two_sided_ci": [mean - half_width, mean + half_width],
        "one_sided_upper": upper_one_sided,
        "better_tie_worse": [better, tie, worse],
        "tie_tolerance": float(tie_tolerance),
    }


def noninferiority_decision(
    paired_harm_deltas: np.ndarray,
    cluster_ids: Sequence[str],
    *,
    margin: float,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Evaluate a preregistered one-sided upper harm noninferiority bound."""

    if not np.isfinite(margin) or margin < 0.0:
        raise ValueError("noninferiority margin must be finite nonnegative")
    summary = clustered_paired_summary(
        paired_harm_deltas,
        cluster_ids,
        confidence=confidence,
    )
    return {
        "schema_version": "camp_dp_v25_noninferiority_decision_v1",
        "harm_delta_contract": "method_minus_candidate0_positive_is_worse",
        "margin": float(margin),
        "confidence": float(confidence),
        "one_sided_upper": summary["one_sided_upper"],
        "passed": bool(summary["one_sided_upper"] <= float(margin)),
        "cluster_summary": summary,
    }


def prospective_cluster_sensitivity(
    cluster_standard_deviation: float,
    independent_cluster_count: int,
    *,
    confidence: float = 0.95,
    power: float = 0.80,
    target_effect: float | None = None,
) -> dict[str, Any]:
    """Freeze pre-open CI width/MDE sensitivity from train/cal pilot clusters."""

    sigma = float(cluster_standard_deviation)
    if not np.isfinite(sigma) or sigma < 0.0:
        raise ValueError("cluster standard deviation must be finite nonnegative")
    if type(independent_cluster_count) is not int or independent_cluster_count < 2:
        raise ValueError("independent_cluster_count must be an integer >=2")
    if not 0.0 < confidence < 1.0 or not 0.0 < power < 1.0:
        raise ValueError("confidence and power must lie in (0,1)")
    critical = float(
        student_t.ppf(
            0.5 + confidence / 2.0,
            df=independent_cluster_count - 1,
        )
    )
    expected_half_width = float(
        critical * sigma / np.sqrt(independent_cluster_count)
    )
    normal = NormalDist()
    z_alpha = normal.inv_cdf(0.5 + confidence / 2.0)
    z_power = normal.inv_cdf(power)
    mde = float(
        (z_alpha + z_power) * sigma / np.sqrt(independent_cluster_count)
    )
    required_clusters: int | None = None
    if target_effect is not None:
        effect = float(target_effect)
        if not np.isfinite(effect) or effect <= 0.0:
            raise ValueError("target_effect must be finite positive")
        required_clusters = max(
            2,
            int(np.ceil(((z_alpha + z_power) * sigma / effect) ** 2)),
        )
    return {
        "schema_version": "camp_dp_v25_prospective_cluster_sensitivity_v1",
        "variance_source": "train_or_calibration_pilot_clusters_only",
        "confidence": float(confidence),
        "power": float(power),
        "independent_cluster_count": independent_cluster_count,
        "cluster_standard_deviation": sigma,
        "expected_two_sided_ci_half_width": expected_half_width,
        "normal_approximation_mde": mde,
        "target_effect": target_effect,
        "normal_approximation_required_clusters": required_clusters,
        "seeds_or_ticks_counted_as_independent": False,
    }


def evaluate_fresh_b2_claim(
    safety_total_deltas: np.ndarray,
    safety_component_deltas: dict[str, np.ndarray],
    performance_harm_deltas: dict[str, np.ndarray],
    cluster_ids: Sequence[str],
    *,
    component_regression_margins: dict[str, float],
    noninferiority_margins: dict[str, float],
    coverage: dict[str, Any],
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Apply the frozen Fresh-B2 total-safety, guardrail, and NI claim rule.

    All deltas are method minus candidate0. Safety/component and comfort deltas
    are harms (positive is worse); progress/completion inputs must already be
    sign-oriented so positive is harm.  The routine never drops failed pairs:
    the caller must provide the separately frozen full-plan coverage receipt.
    """

    if type(safety_component_deltas) is not dict or set(
        safety_component_deltas
    ) != set(SAFETY_COMPONENTS):
        raise ValueError("safety component delta keyset drifted")
    if type(component_regression_margins) is not dict or set(
        component_regression_margins
    ) != set(SAFETY_COMPONENTS):
        raise ValueError("safety component margin keyset drifted")
    if type(performance_harm_deltas) is not dict or set(
        performance_harm_deltas
    ) != set(NONINFERIORITY_METRICS):
        raise ValueError("performance harm delta keyset drifted")
    if type(noninferiority_margins) is not dict or set(
        noninferiority_margins
    ) != set(NONINFERIORITY_METRICS):
        raise ValueError("noninferiority margin keyset drifted")
    coverage_receipt = _validate_claim_coverage(coverage)
    total = clustered_paired_summary(
        safety_total_deltas,
        cluster_ids,
        confidence=confidence,
    )
    components: dict[str, dict[str, Any]] = {}
    component_guards: dict[str, dict[str, Any]] = {}
    for name in SAFETY_COMPONENTS:
        values = _finite_vector(safety_component_deltas[name], name)
        if values.size != total["observation_count"]:
            raise ValueError(f"{name} delta count does not match SafetyCost")
        components[name] = clustered_paired_summary(
            values,
            cluster_ids,
            confidence=confidence,
        )
        component_guards[name] = noninferiority_decision(
            values,
            cluster_ids,
            margin=_native_nonnegative_margin(
                component_regression_margins[name], f"{name} component margin"
            ),
            confidence=confidence,
        )
    performance: dict[str, dict[str, Any]] = {}
    for name in NONINFERIORITY_METRICS:
        values = _finite_vector(performance_harm_deltas[name], name)
        if values.size != total["observation_count"]:
            raise ValueError(f"{name} delta count does not match SafetyCost")
        performance[name] = noninferiority_decision(
            values,
            cluster_ids,
            margin=_native_nonnegative_margin(
                noninferiority_margins[name], f"{name} noninferiority margin"
            ),
            confidence=confidence,
        )
    better, _tie, worse = total["better_tie_worse"]
    total_gate = {
        "mean_delta_lt_zero": bool(total["mean_delta"] < 0.0),
        "two_sided_cluster_ci_upper_lt_zero": bool(total["two_sided_ci"][1] < 0.0),
        "better_gt_worse": bool(better > worse),
        "component_guardrails_pass": bool(
            all(item["passed"] for item in component_guards.values())
        ),
        "performance_comfort_noninferiority_pass": bool(
            all(item["passed"] for item in performance.values())
        ),
        "coverage_immutability_zero_overlap_pass": bool(
            coverage_receipt["passed"]
        ),
    }
    safety_claim = bool(all(total_gate.values()))
    red_gate = bool(
        safety_claim and components["red_light"]["two_sided_ci"][1] < 0.0
    )
    return {
        "schema_version": "camp_dp_v25_fresh_b2_claim_decision_v1",
        "delta_contract": "method_minus_candidate0_negative_is_safer_or_better",
        "confidence": float(confidence),
        "total_safety": total,
        "components": components,
        "component_guardrails": component_guards,
        "performance_comfort_noninferiority": performance,
        "coverage": coverage_receipt,
        "total_safety_claim_gate": total_gate,
        "safety_improvement_claim_passed": safety_claim,
        "red_light_improvement_additional_gate": (
            "total_safety_claim_and_red_component_two_sided_ci_upper_lt_zero"
        ),
        "red_light_improvement_claim_passed": red_gate,
        "claim_scope": "unchanged_fixed_dp_valid_k8_preregistered_support_domain",
        "real_world_or_all_map_claim_authorized": False,
    }


def _finite_vector(value: np.ndarray, name: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.ndim != 1 or raw.dtype.kind not in "fiu" or raw.dtype.kind == "b":
        raise ValueError(f"{name} must be a native numeric vector")
    result = raw.astype(np.float64, copy=False)
    if result.size == 0 or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be nonempty finite")
    return result


def _cluster_strings(values: Sequence[str], size: int) -> tuple[str, ...]:
    if len(values) != size or any(type(value) is not str or not value for value in values):
        raise ValueError("cluster_ids must be aligned nonempty native strings")
    return tuple(values)


def _native_nonnegative_margin(value: Any, name: str) -> float:
    if type(value) not in (int, float) or not np.isfinite(float(value)) or value < 0:
        raise ValueError(f"{name} must be native finite nonnegative")
    return float(value)


def _validate_claim_coverage(value: dict[str, Any]) -> dict[str, Any]:
    required = {
        "full_plan_pair_count",
        "paired_eligible_count",
        "overall_eligible_rate",
        "planned_scenario_families",
        "planned_family_source_strata",
        "planned_family_tier_strata",
        "family_source_eligible_rates",
        "family_tier_eligible_rates",
        "failure_denominator_complete",
        "immutability_passed",
        "zero_overlap_passed",
    }
    if type(value) is not dict or set(value) != required:
        raise ValueError("Fresh B2 coverage field set drifted")
    total = value["full_plan_pair_count"]
    eligible = value["paired_eligible_count"]
    if (
        type(total) is not int
        or type(eligible) is not int
        or total < 1
        or eligible < 0
        or eligible > total
    ):
        raise ValueError("Fresh B2 coverage counts are invalid")
    rate = value["overall_eligible_rate"]
    if (
        type(rate) not in (int, float)
        or not np.isfinite(float(rate))
        or not np.isclose(float(rate), eligible / total, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("Fresh B2 overall coverage rate is inconsistent")
    families = value["planned_scenario_families"]
    if (
        type(families) is not list
        or len(families) != len(REQUIRED_CONTROLLED_EVENT_FAMILIES)
        or set(families) != set(REQUIRED_CONTROLLED_EVENT_FAMILIES)
        or any(type(item) is not str for item in families)
    ):
        raise ValueError("Fresh B2 planned scenario family coverage drifted")
    strata: dict[str, dict[str, float]] = {}
    strata_contract = {
        "family_source_eligible_rates": "planned_family_source_strata",
        "family_tier_eligible_rates": "planned_family_tier_strata",
    }
    for field, planned_field in strata_contract.items():
        raw = value[field]
        planned = value[planned_field]
        if (
            type(raw) is not dict
            or not raw
            or type(planned) is not list
            or not planned
            or any(type(item) is not str or not item for item in planned)
            or len(set(planned)) != len(planned)
            or set(planned) != set(raw)
        ):
            raise ValueError(f"{field} must be a nonempty mapping")
        normalized: dict[str, float] = {}
        for key, item in raw.items():
            if (
                type(key) is not str
                or not key
                or type(item) not in (int, float)
                or not np.isfinite(float(item))
                or not 0.0 <= float(item) <= 1.0
            ):
                raise ValueError(f"{field} contains an invalid rate")
            normalized[key] = float(item)
        strata[field] = normalized
    for family in REQUIRED_CONTROLLED_EVENT_FAMILIES:
        if not any(
            key.startswith(f"{family}/")
            for key in strata["family_source_eligible_rates"]
        ) or not any(
            key.startswith(f"{family}/")
            for key in strata["family_tier_eligible_rates"]
        ):
            raise ValueError(f"Fresh B2 planned strata omit family {family}")
    for key in strata["family_source_eligible_rates"]:
        parts = key.split("/")
        if (
            len(parts) != 3
            or parts[0]
            not in {*REQUIRED_CONTROLLED_EVENT_FAMILIES, "naturalistic_background"}
            or (
                parts[1] == "mapped_signal"
                and parts[2]
                not in {
                    "controlled_same_tick_override",
                    "observe_same_tick_request",
                }
            )
            or (parts[1] == "no_signal" and parts[2] != "none")
            or parts[1] not in {"mapped_signal", "no_signal"}
        ):
            raise ValueError("Fresh B2 family/source/mode stratum drifted")
    if not any(
        key.startswith("red_light_phase_timing/mapped_signal")
        for key in strata["family_source_eligible_rates"]
    ):
        raise ValueError("Fresh B2 red-light stratum lacks mapped signal source")
    for field in (
        "failure_denominator_complete",
        "immutability_passed",
        "zero_overlap_passed",
    ):
        if type(value[field]) is not bool:
            raise ValueError(f"{field} must be a native boolean")
    passed = bool(
        float(rate) >= 0.95
        and min(strata["family_source_eligible_rates"].values()) >= 0.90
        and min(strata["family_tier_eligible_rates"].values()) >= 0.80
        and value["failure_denominator_complete"]
        and value["immutability_passed"]
        and value["zero_overlap_passed"]
    )
    return {
        "schema_version": "camp_dp_v25_fresh_b2_claim_coverage_v1",
        **value,
        "minimum_overall_eligible_rate": 0.95,
        "minimum_family_source_eligible_rate": 0.90,
        "minimum_family_tier_eligible_rate": 0.80,
        "all_planned_strata_reported": True,
        "passed": passed,
    }
