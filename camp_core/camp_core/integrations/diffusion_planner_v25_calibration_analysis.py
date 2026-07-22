from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

import numpy as np

from .diffusion_planner_v25_calibration import (
    COMPONENT_REGRESSION_MARGINS,
    NONINFERIORITY_ENGINEERING_MARGINS,
    SAFETY_COMPONENT_NATIVE_FIELDS,
)
from .diffusion_planner_v25_calibration_preregistration import LATENCY_FIELDS
from .diffusion_planner_v25_signal_safety import SIGNAL_SAFETY_SCHEMA_VERSION
from .diffusion_planner_v25_statistics import (
    NONINFERIORITY_METRICS,
    SAFETY_COMPONENTS,
    clustered_paired_summary,
    noninferiority_decision,
    prospective_cluster_sensitivity,
)


SCHEMA_VERSION = "camp_dp_v25_paired_calibration_analysis_v1"
SUPPLEMENTARY_LATENCY_FIELDS = ("input_materialization",)
ARMS = (
    "candidate0_operational_default",
    "camp_static14d",
    "camp_scene14d_no_v2i",
)


def analyze_paired_calibration_outcomes(
    corpus: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive descriptive paired calibration, NI, latency, and power evidence."""

    rows = corpus.get("arm_results")
    if type(rows) is not list or len(rows) != 300:
        raise ValueError("paired calibration analysis requires 300 terminal rows")
    by_pair: dict[int, dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        if type(row) is not dict or row.get("plan_arm") not in ARMS:
            raise ValueError("paired calibration analysis arm row drifted")
        by_pair[int(row["unit_ordinal"])][str(row["plan_arm"])] = row
    eligible = [
        unit
        for unit in sorted(by_pair)
        if set(by_pair[unit]) == set(ARMS)
        and all(by_pair[unit][arm].get("status") == "complete" for arm in ARMS)
    ]
    if len(eligible) != corpus.get("paired_eligible_pair_count"):
        raise ValueError("paired calibration eligible denominator drifted")
    projected: dict[int, dict[str, dict[str, Any]]] = {}
    for unit in eligible:
        projected[unit] = {
            arm: _project_complete(by_pair[unit][arm]) for arm in ARMS
        }

    main_table = {
        arm: _arm_means([projected[unit][arm] for unit in eligible]) for arm in ARMS
    }
    comparisons: dict[str, Any] = {}
    power: dict[str, Any] = {}
    baseline = ARMS[0]
    for arm in ARMS[1:]:
        label = f"{arm}_minus_candidate0"
        clusters = [projected[unit][arm]["corridor_sha256"] for unit in eligible]
        safety_delta = np.asarray(
            [
                projected[unit][arm]["safety_cost"]
                - projected[unit][baseline]["safety_cost"]
                for unit in eligible
            ],
            dtype=np.float64,
        )
        safety_summary = clustered_paired_summary(
            safety_delta, clusters, confidence=0.95, tie_tolerance=1e-12
        )
        component_summaries = {}
        component_guardrails = {}
        for component in SAFETY_COMPONENTS:
            delta = np.asarray(
                [
                    projected[unit][arm]["components"][component]
                    - projected[unit][baseline]["components"][component]
                    for unit in eligible
                ],
                dtype=np.float64,
            )
            component_summaries[component] = clustered_paired_summary(
                delta, clusters, confidence=0.95, tie_tolerance=1e-12
            )
            component_guardrails[component] = noninferiority_decision(
                delta,
                clusters,
                margin=COMPONENT_REGRESSION_MARGINS[component],
                confidence=0.95,
            )
        ni = {}
        for metric in NONINFERIORITY_METRICS:
            if metric in {"progress", "completion"}:
                harm = np.asarray(
                    [
                        projected[unit][baseline]["performance"][metric]
                        - projected[unit][arm]["performance"][metric]
                        for unit in eligible
                    ],
                    dtype=np.float64,
                )
            else:
                harm = np.asarray(
                    [
                        projected[unit][arm]["performance"][metric]
                        - projected[unit][baseline]["performance"][metric]
                        for unit in eligible
                    ],
                    dtype=np.float64,
                )
            ni[metric] = noninferiority_decision(
                harm,
                clusters,
                margin=NONINFERIORITY_ENGINEERING_MARGINS[metric],
                confidence=0.95,
            )
        comparisons[label] = {
            "safety_cost": safety_summary,
            "components": component_summaries,
            "component_guardrails": component_guardrails,
            "all_component_guardrails_passed": all(
                item["passed"] for item in component_guardrails.values()
            ),
            "noninferiority": ni,
            "all_noninferiority_passed": all(item["passed"] for item in ni.values()),
            "calibration_is_descriptive_not_fresh_confirmation": True,
        }
        power[label] = {
            "safety_cost_total": prospective_cluster_sensitivity(
                safety_summary["cluster_standard_deviation"],
                safety_summary["independent_cluster_count"],
                confidence=0.95,
                power=0.80,
            ),
            "red_light_component": prospective_cluster_sensitivity(
                component_summaries["red_light"]["cluster_standard_deviation"],
                component_summaries["red_light"]["independent_cluster_count"],
                confidence=0.95,
                power=0.80,
            ),
        }

    strata = {}
    for stratum_name, predicate in {
        "controlled_stress": lambda item: item["benchmark_stratum"] == "controlled_stress",
        "red_light_family": lambda item: item["scenario_family"] == "red_light_phase_timing",
        "non_red_families": lambda item: item["scenario_family"] != "red_light_phase_timing",
        "mapped_signal": lambda item: item["signal_source_class"] == "mapped_signal",
        "no_signal": lambda item: item["signal_source_class"] == "no_signal",
    }.items():
        selected = [unit for unit in eligible if predicate(projected[unit][baseline])]
        strata[stratum_name] = {
            "paired_unit_count": len(selected),
            "mean_safety_cost_by_arm": {
                arm: (
                    None
                    if not selected
                    else float(
                        np.mean([projected[unit][arm]["safety_cost"] for unit in selected])
                    )
                )
                for arm in ARMS
            },
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "paired_calibration_analysis_complete",
        "paired_eligible_pair_count": len(eligible),
        "paired_eligible_rate": corpus["paired_eligible_rate"],
        "independent_unit_counts": {
            "maps": len({projected[unit][baseline]["map_sha256"] for unit in eligible}),
            "intersections": len(
                {projected[unit][baseline]["intersection_sha256"] for unit in eligible}
            ),
            "corridors": len(
                {projected[unit][baseline]["corridor_sha256"] for unit in eligible}
            ),
            "routes": len(
                {projected[unit][baseline]["route_identity_sha256"] for unit in eligible}
            ),
            "semantic_blocks": len(
                {
                    projected[unit][baseline]["semantic_parameter_block_sha256"]
                    for unit in eligible
                }
            ),
            "seeds": len({projected[unit][baseline]["seed"] for unit in eligible}),
            "ticks": len(eligible) * 3 * 64,
        },
        "cluster_level_for_primary_inference": "corridor",
        "seeds_or_ticks_counted_as_independent": False,
        "main_table": main_table,
        "paired_comparisons": comparisons,
        "strata": strata,
        "latency": _latency_summary(projected, eligible),
        "latency_field_registry": {
            "preregistered_primary_fields": list(LATENCY_FIELDS),
            "supplementary_runtime_fields": list(SUPPLEMENTARY_LATENCY_FIELDS),
            "supplementary_fields_do_not_change_claim_margins_or_models": True,
        },
        "fresh_b2_power_sensitivity": power,
        "coverage": {
            key: corpus[key]
            for key in (
                "pair_count",
                "planned_arm_run_count",
                "terminal_arm_run_count",
                "complete_arm_run_count",
                "retained_fixed_dp_capability_failure_count",
                "complete_count_by_arm",
                "failure_count_by_arm",
                "paired_eligible_pair_count",
                "paired_eligible_rate",
                "family_paired_eligible_rates",
                "source_paired_eligible_rates",
                "family_tier_paired_eligible_rates",
                "coverage_gate_passed",
            )
        },
        "calibration_result_driven_model_or_threshold_change": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
        "claim_authorized": False,
    }


def _project_complete(row: Mapping[str, Any]) -> dict[str, Any]:
    native = row.get("native_receipt")
    if type(native) is not dict:
        raise ValueError("complete calibration row lacks native receipt")
    safety = native.get("safety")
    secondary = native.get("secondary")
    ticks = native.get("ticks")
    if type(safety) is not dict or type(secondary) is not dict or type(ticks) is not list:
        raise ValueError("complete calibration summary evidence is missing")
    components_raw = safety.get("components")
    if type(components_raw) is not dict:
        raise ValueError("complete calibration safety components are missing")
    components = {
        name: _finite(components_raw[SAFETY_COMPONENT_NATIVE_FIELDS[name]], name)
        for name in SAFETY_COMPONENTS
    }
    performance = {
        "progress": _finite(secondary["route_progress_m"], "progress"),
        "completion": _finite(secondary["route_completion_rate"], "completion"),
        "mean_jerk": _finite(secondary["mean_abs_jerk_mps3"], "mean_jerk"),
        "max_jerk": _finite(secondary["max_jerk_mps3"], "max_jerk"),
        "mean_lateral_acceleration": _finite(
            secondary["mean_abs_lateral_acceleration_mps2"],
            "mean_lateral_acceleration",
        ),
        "max_lateral_acceleration": _finite(
            secondary["max_abs_lateral_acceleration_mps2"],
            "max_lateral_acceleration",
        ),
        "maximum_deceleration": _maximum_deceleration(ticks),
    }
    return {
        "plan_arm": row["plan_arm"],
        "safety_cost": _finite(safety["safety_cost"], "safety_cost"),
        "components": components,
        "performance": performance,
        "latency_ticks": [dict(tick["latency_ms"]) for tick in ticks],
        "signal_safety": dict(native["signal_safety"]),
        "selection_ticks": [
            {
                "selected_index": tick.get("selected_index"),
                "all_k_high_risk": tick.get("all_k_high_risk"),
                "physical_feasible_mask": tick.get("physical_feasible_mask"),
                "source_valid_mask": tick.get("source_valid_mask"),
            }
            for tick in ticks
        ],
        **{
            name: row[name]
            for name in (
                "map_sha256",
                "intersection_sha256",
                "corridor_sha256",
                "route_identity_sha256",
                "route_family_sha256",
                "semantic_parameter_block_sha256",
                "scenario_family",
                "risk_tier",
                "benchmark_stratum",
                "signal_source_class",
                "phase_authority_mode",
                "seed",
            )
        },
    }


def _arm_means(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("paired calibration arm has no eligible rows")
    return {
        "paired_run_count": len(rows),
        "safety_cost_mean": float(np.mean([row["safety_cost"] for row in rows])),
        "component_means": {
            name: float(np.mean([row["components"][name] for row in rows]))
            for name in SAFETY_COMPONENTS
        },
        "performance_means": {
            name: float(np.mean([row["performance"][name] for row in rows]))
            for name in NONINFERIORITY_METRICS
        },
        "certified_signal_safety": _signal_safety_summary(rows),
        "selection_and_candidate_pool": _selection_pool_summary(rows),
    }


def _latency_summary(
    projected: Mapping[int, Mapping[str, Mapping[str, Any]]], eligible: list[int]
) -> dict[str, Any]:
    result = {}
    for arm in ARMS:
        grouped: dict[str, list[float]] = defaultdict(list)
        for unit in eligible:
            for tick in projected[unit][arm]["latency_ticks"]:
                for name, value in tick.items():
                    grouped[str(name)].append(_finite(value, f"latency.{name}"))
        result[arm] = {}
        registered = (*LATENCY_FIELDS, *SUPPLEMENTARY_LATENCY_FIELDS)
        for name in registered:
            values = grouped.get(name, [])
            result[arm][name] = (
                {
                    "available": False,
                    "count": 0,
                    "mean": None,
                    "median": None,
                    "p95": None,
                    "p99": None,
                    "max": None,
                }
                if not values
                else {"available": True, **_distribution(values)}
            )
        unknown = set(grouped) - set(registered)
        if unknown:
            raise ValueError(f"unregistered calibration latency fields: {sorted(unknown)}")
    result["selector_and_k8_system_overhead_reported_separately"] = True
    return result


def _signal_safety_summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    violation_count = 0
    crossing_count = 0
    false_stop_count = 0
    red_intervals = 0
    green_intervals = 0
    green_approach_intervals = 0
    yellow_intervals = 0
    crossing_speed_mass = 0.0
    red_margins: list[float] = []
    mapped_run_count = 0
    no_signal_run_count = 0
    thresholds: dict[str, Any] | None = None
    for row in rows:
        signal = row["signal_safety"]
        if (
            type(signal) is not dict
            or signal.get("schema_version") != SIGNAL_SAFETY_SCHEMA_VERSION
            or signal.get("certified_stop_line_used")
            != (signal.get("source_class") == "mapped_signal")
            or signal.get("legacy_proximity_heuristic_used") is not False
            or signal.get("future_phase_schedule_consumed") is not False
            or signal.get("phase_remaining_consumed") is not False
        ):
            raise ValueError("calibration certified signal-safety contract drifted")
        counts = signal.get("counts")
        denominators = signal.get("denominators")
        metrics = signal.get("metrics")
        if not all(type(value) is dict for value in (counts, denominators, metrics)):
            raise ValueError("calibration signal-safety summary is malformed")
        if thresholds is None:
            thresholds = dict(signal["thresholds"])
        elif thresholds != signal["thresholds"]:
            raise ValueError("calibration signal-safety threshold drifted")
        mapped = signal["source_class"] == "mapped_signal"
        mapped_run_count += int(mapped)
        no_signal_run_count += int(not mapped)
        violation = int(counts["red_violation_intervals"])
        crossing = int(counts["red_crossing_intervals"])
        false_stop = int(counts["green_false_stop_intervals"])
        red = int(denominators["red_phase_intervals"])
        green = int(denominators["green_phase_intervals"])
        green_approach = int(denominators["green_unblocked_approach_intervals"])
        yellow = int(denominators["yellow_phase_intervals"])
        if min(violation, crossing, false_stop, red, green, green_approach, yellow) < 0:
            raise ValueError("calibration signal-safety counts must be nonnegative")
        violation_count += violation
        crossing_count += crossing
        false_stop_count += false_stop
        red_intervals += red
        green_intervals += green
        green_approach_intervals += green_approach
        yellow_intervals += yellow
        crossing_speed_mass += _finite(
            metrics["crossing_speed_mps"], "crossing_speed_mps"
        ) * crossing
        if red > 0:
            red_margins.append(
                _finite(metrics["stop_line_margin_m"], "stop_line_margin_m")
            )
    return {
        "schema_version": SIGNAL_SAFETY_SCHEMA_VERSION,
        "mapped_run_count": mapped_run_count,
        "no_signal_run_count": no_signal_run_count,
        "red_light_violation_rate": violation_count / max(red_intervals, 1),
        "stop_line_crossing_rate": crossing_count / max(red_intervals, 1),
        "minimum_stop_line_margin_m": min(red_margins) if red_margins else 0.0,
        "mean_crossing_speed_mps": crossing_speed_mass / max(crossing_count, 1),
        "false_stop_on_green_rate": false_stop_count
        / max(green_approach_intervals, 1),
        "counts": {
            "red_crossing_intervals": crossing_count,
            "red_violation_intervals": violation_count,
            "green_false_stop_intervals": false_stop_count,
        },
        "denominators": {
            "red_phase_intervals": red_intervals,
            "green_phase_intervals": green_intervals,
            "green_unblocked_approach_intervals": green_approach_intervals,
            "yellow_phase_intervals": yellow_intervals,
        },
        "thresholds": thresholds,
        "legacy_proximity_heuristic_used": False,
        "future_phase_schedule_consumed": False,
        "phase_remaining_consumed": False,
    }


def _selection_pool_summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    tick_count = 0
    nonzero = 0
    high_risk = 0
    high_risk_available = 0
    physical_pool_available = 0
    physical_safe_pool = 0
    source_pool_available = 0
    source_eligible_pool = 0
    for row in rows:
        for tick in row["selection_ticks"]:
            selected = tick["selected_index"]
            if type(selected) is not int or not 0 <= selected < 8:
                raise ValueError("calibration selected index is invalid")
            tick_count += 1
            nonzero += int(selected != 0)
            all_k = tick["all_k_high_risk"]
            if all_k is not None:
                if type(all_k) is not bool:
                    raise ValueError("calibration all-K flag is not boolean")
                high_risk_available += 1
                high_risk += int(all_k)
            physical = tick["physical_feasible_mask"]
            if physical is not None:
                if type(physical) is not list or len(physical) != 8 or any(
                    type(value) is not bool for value in physical
                ):
                    raise ValueError("calibration physical mask is invalid")
                physical_pool_available += 1
                physical_safe_pool += int(any(physical))
            source = tick["source_valid_mask"]
            if source is not None:
                if type(source) is not list or len(source) != 8 or any(
                    type(value) is not bool for value in source
                ):
                    raise ValueError("calibration source mask is invalid")
                source_pool_available += 1
                source_eligible_pool += int(any(source))
    return {
        "tick_count": tick_count,
        "candidate0_selected_count": tick_count - nonzero,
        "nonzero_candidate_selected_count": nonzero,
        "nonzero_candidate_selected_rate": nonzero / tick_count,
        "all_k_high_risk_observed_tick_count": high_risk_available,
        "all_k_high_risk_tick_count": high_risk,
        "all_k_high_risk_rate_when_available": (
            None if high_risk_available == 0 else high_risk / high_risk_available
        ),
        "physical_pool_observed_tick_count": physical_pool_available,
        "candidate_pool_at_least_one_physical_safe_rate": (
            None
            if physical_pool_available == 0
            else physical_safe_pool / physical_pool_available
        ),
        "source_pool_observed_tick_count": source_pool_available,
        "candidate_pool_at_least_one_source_eligible_rate": (
            None
            if source_pool_available == 0
            else source_eligible_pool / source_pool_available
        ),
    }


def _distribution(values: list[float]) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "count": int(array.size),
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "p95": float(np.percentile(array, 95.0)),
        "p99": float(np.percentile(array, 99.0)),
        "max": float(np.max(array)),
    }


def _maximum_deceleration(ticks: list[Mapping[str, Any]]) -> float:
    value = 0.0
    for tick in ticks:
        pre = _finite(tick["pre_decision_speed_mps"], "pre_decision_speed_mps")
        safety = tick.get("safety")
        if type(safety) is not dict:
            raise ValueError("tick safety is missing")
        post = _finite(safety["speed_mps"], "post_interval_speed_mps")
        value = max(value, max(pre - post, 0.0) / 0.1)
    return value


def _finite(value: Any, name: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{name} must be a native number")
    number = float(value)
    if not np.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number
