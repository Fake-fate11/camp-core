from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner_v21_native import safety_cost_native_v1
from .diffusion_planner_v25_statistics import (
    NONINFERIORITY_METRICS,
    SAFETY_COMPONENTS,
)
from .diffusion_planner_v25_signal_safety import (
    FALSE_STOP_GREEN_APPROACH_DISTANCE_M,
    FALSE_STOP_GREEN_MAXIMUM_SPEED_MPS,
    FALSE_STOP_GREEN_MINIMUM_OBB_CLEARANCE_M,
    RED_CROSSING_MINIMUM_SPEED_MPS,
    SIGNAL_SAFETY_SCHEMA_VERSION,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CALIBRATION_ROOT_BINDINGS = frozenset(
    {
        "atom_audit_root",
        "atom_audit_review_root",
        "training_root",
        "training_review_root",
        "calibration_corpus_root",
        "calibration_review_root",
        "zero_overlap_root",
    }
)
CALIBRATION_INVENTORY_FIELDS = frozenset(
    {
        "map_count",
        "intersection_count",
        "corridor_count",
        "route_count",
        "planned_paired_run_count",
        "paired_eligible_run_count",
        "retained_failure_run_count",
        "paired_eligible_rate",
    }
)
SAFETY_COST_COMPONENT_WEIGHTS = {
    "collision": 100.0,
    "near_miss": 10.0,
    "offroad": 20.0,
    "red_light": 30.0,
    "speed": 10.0,
    "wrong_way": 20.0,
}
SAFETY_COMPONENT_NATIVE_FIELDS = {
    "collision": "collision_any",
    "near_miss": "near_miss_noncollision_rate",
    "offroad": "offroad_rate",
    "red_light": "red_light_violation_any",
    "speed": "speed_limit_violation_rate",
    "wrong_way": "wrong_way_rate",
}
NONINFERIORITY_ENGINEERING_MARGINS = {
    "progress": 1.0,
    "completion": 0.02,
    "mean_jerk": 0.2,
    "max_jerk": 1.0,
    "mean_lateral_acceleration": 0.1,
    "max_lateral_acceleration": 0.3,
    "maximum_deceleration": 0.5,
}
NONINFERIORITY_MARGIN_UNITS = {
    "progress": "m",
    "completion": "fraction",
    "mean_jerk": "m_per_s3",
    "max_jerk": "m_per_s3",
    "mean_lateral_acceleration": "m_per_s2",
    "max_lateral_acceleration": "m_per_s2",
    "maximum_deceleration": "m_per_s2",
}
COMPONENT_REGRESSION_MARGINS = {name: 0.0 for name in SAFETY_COMPONENTS}
NI_CALIBRATION_ROW_FIELDS = frozenset(
    {
        "schema_version",
        "arm",
        "cluster_id",
        "measurement_sha256",
        "performance",
        "fresh_b2_opened",
        "fresh_outcome_fields_consumed",
    }
)
NI_RESOLVABILITY_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "calibration_arm",
        "margin_source",
        "residual_estimator",
        "residual_quantile",
        "minimum_independent_clusters",
        "minimum_measurements_per_cluster",
        "independent_cluster_count",
        "measurement_count",
        "cluster_measurement_counts",
        "margins",
        "margin_units",
        "q95_absolute_repeat_variability",
        "margin_resolvable",
        "all_margins_resolvable",
        "camp_method_outcomes_consumed",
        "fresh_b2_opened",
        "fresh_outcome_fields_consumed",
    }
)
_NATIVE_PERFORMANCE_FIELDS = {
    "progress": "route_progress_m",
    "completion": "route_completion_rate",
    "mean_jerk": "mean_abs_jerk_mps3",
    "max_jerk": "max_jerk_mps3",
    "mean_lateral_acceleration": "mean_abs_lateral_acceleration_mps2",
    "max_lateral_acceleration": "max_abs_lateral_acceleration_mps2",
}


def project_candidate0_ni_calibration_row(
    *,
    cluster_id: str,
    native_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Project one reviewed fixed-DP candidate0 run into an NI calibration row."""

    if type(cluster_id) is not str or not cluster_id:
        raise ValueError("candidate0 NI calibration cluster must be a nonempty string")
    if type(native_receipt) is not dict:
        raise ValueError("candidate0 native receipt must be a native mapping")
    if (
        native_receipt.get("schema_version") != "v21_native_arm_receipt_v1"
        or native_receipt.get("status") != "ok"
        or native_receipt.get("arm") != "dp"
        or native_receipt.get("fixed_dp_head") != FIXED_DP_HEAD
        or native_receipt.get("claim_authorized") is not False
    ):
        raise ValueError("candidate0 native receipt authority drifted")
    for name in (
        "route_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
    ):
        _require_sha(native_receipt.get(name), f"native_receipt.{name}")
    seed = native_receipt.get("scenario_seed")
    if type(seed) is not int:
        raise ValueError("candidate0 native scenario seed must be a native integer")
    ticks = native_receipt.get("ticks")
    if type(ticks) is not list or len(ticks) != 64:
        raise ValueError("candidate0 NI calibration requires exactly 64 ticks")
    tick_evidence: list[dict[str, Any]] = []
    maximum_deceleration = 0.0
    for index, tick in enumerate(ticks):
        if type(tick) is not dict or tick.get("tick_index") != index:
            raise ValueError("candidate0 NI calibration tick order drifted")
        if tick.get("selected_index") != 0:
            raise ValueError("candidate0 NI calibration must select candidate zero")
        before = tick.get("candidate_tensor_sha256_before")
        after = tick.get("candidate_tensor_sha256_after")
        _require_sha(before, "candidate_tensor_sha256_before")
        if after != before:
            raise ValueError("candidate0 NI calibration candidate tensor was modified")
        input_sha = tick.get("input_sha256")
        output_sha = tick.get("default_output_sha256")
        _require_sha(input_sha, "input_sha256")
        _require_sha(output_sha, "default_output_sha256")
        pre_speed = _native_nonnegative_number(
            tick.get("pre_decision_speed_mps"), "pre_decision_speed_mps"
        )
        safety = tick.get("safety")
        if type(safety) is not dict:
            raise ValueError("candidate0 NI calibration tick safety evidence is missing")
        post_speed = _native_nonnegative_number(
            safety.get("speed_mps"), "safety.speed_mps"
        )
        maximum_deceleration = max(
            maximum_deceleration,
            max(pre_speed - post_speed, 0.0) / 0.1,
        )
        tick_evidence.append(
            {
                "tick_index": index,
                "input_sha256": input_sha,
                "default_output_sha256": output_sha,
                "candidate_tensor_sha256": before,
                "pre_decision_speed_mps": pre_speed,
                "post_interval_speed_mps": post_speed,
            }
        )
    if native_receipt["initial_input_sha256"] != tick_evidence[0]["input_sha256"]:
        raise ValueError("candidate0 NI calibration initial input binding drifted")
    secondary = native_receipt.get("secondary")
    if type(secondary) is not dict:
        raise ValueError("candidate0 NI calibration secondary summary is missing")
    performance = {
        name: _native_nonnegative_number(secondary.get(source), f"secondary.{source}")
        for name, source in _NATIVE_PERFORMANCE_FIELDS.items()
    }
    performance["maximum_deceleration"] = maximum_deceleration
    if set(performance) != set(NONINFERIORITY_METRICS):
        raise AssertionError("candidate0 NI performance projection drifted")
    measurement_preimage = {
        "schema_version": "camp_dp_v25_candidate0_ni_measurement_preimage_v1",
        "fixed_dp_head": FIXED_DP_HEAD,
        "route_sha256": native_receipt["route_sha256"],
        "scenario_seed": seed,
        "initial_state_sha256": native_receipt["initial_state_sha256"],
        "initial_input_sha256": native_receipt["initial_input_sha256"],
        "tick_evidence": tick_evidence,
        "performance": performance,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    measurement_sha256 = hashlib.sha256(
        (
            json.dumps(
                measurement_preimage,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "camp_dp_v25_candidate0_ni_calibration_row_v1",
        "arm": "candidate0_operational_default",
        "cluster_id": cluster_id,
        "measurement_sha256": measurement_sha256,
        "performance": performance,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }


def estimate_v25_noninferiority_margin_resolvability(
    candidate0_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Assess fixed NI margins using candidate0 calibration repeats only.

    The calibration data never enlarges the margins.  It only establishes
    whether the preregistered engineering tolerances are resolvable under
    equal cluster mass.  CAMP method rows and Fresh outcomes are forbidden.
    """

    rows = tuple(_ni_calibration_row(row) for row in candidate0_rows)
    if not rows:
        raise ValueError("candidate0 NI calibration rows must be nonempty")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    measurement_hashes: set[str] = set()
    for row in rows:
        digest = row["measurement_sha256"]
        if digest in measurement_hashes:
            raise ValueError("candidate0 NI calibration measurement SHA repeated")
        measurement_hashes.add(digest)
        grouped[row["cluster_id"]].append(row)
    if len(grouped) < 5:
        raise ValueError("NI margin resolvability requires at least five clusters")
    if any(len(cluster_rows) < 2 for cluster_rows in grouped.values()):
        raise ValueError("NI margin resolvability requires two repeats per cluster")

    variability: dict[str, float] = {}
    resolvable: dict[str, bool] = {}
    for metric in NONINFERIORITY_METRICS:
        residuals: list[float] = []
        weights: list[float] = []
        cluster_mass = 1.0 / len(grouped)
        for cluster_rows in grouped.values():
            values = np.asarray(
                [row["performance"][metric] for row in cluster_rows],
                dtype=np.float64,
            )
            center = float(np.median(values))
            residuals.extend(np.abs(values - center).tolist())
            weights.extend([cluster_mass / len(cluster_rows)] * len(cluster_rows))
        q95 = _weighted_quantile(
            np.asarray(residuals, dtype=np.float64),
            np.asarray(weights, dtype=np.float64),
            0.95,
        )
        variability[metric] = q95
        resolvable[metric] = bool(q95 <= NONINFERIORITY_ENGINEERING_MARGINS[metric])

    all_resolvable = all(resolvable.values())
    return {
        "schema_version": "camp_dp_v25_noninferiority_margin_resolvability_v1",
        "status": (
            "noninferiority_margins_resolvable"
            if all_resolvable
            else "noninferiority_margins_not_resolvable"
        ),
        "calibration_arm": "candidate0_operational_default",
        "margin_source": (
            "preregistered_engineering_acceptability_not_calibration_outcome_tuned"
        ),
        "residual_estimator": (
            "equal_cluster_equal_within_cluster_absolute_deviation_from_cluster_median"
        ),
        "residual_quantile": 0.95,
        "minimum_independent_clusters": 5,
        "minimum_measurements_per_cluster": 2,
        "independent_cluster_count": len(grouped),
        "measurement_count": len(rows),
        "cluster_measurement_counts": {
            name: len(grouped[name]) for name in sorted(grouped)
        },
        "margins": dict(NONINFERIORITY_ENGINEERING_MARGINS),
        "margin_units": dict(NONINFERIORITY_MARGIN_UNITS),
        "q95_absolute_repeat_variability": variability,
        "margin_resolvable": resolvable,
        "all_margins_resolvable": all_resolvable,
        "camp_method_outcomes_consumed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }


def freeze_v25_calibration_contract(
    *,
    root_bindings: Mapping[str, str],
    inventory: Mapping[str, Any],
    noninferiority_resolvability: Mapping[str, Any],
    frozen_model_registry_sha256: str,
    training_scale_sha256: str,
    context_scaler_sha256: str,
) -> dict[str, Any]:
    """Freeze calibration-only thresholds and margins before Fresh opens."""

    roots = _root_map(root_bindings)
    _validate_native_safety_cost_weights()
    counts = _inventory(inventory)
    ni_resolution = _ni_resolvability(noninferiority_resolvability)
    if ni_resolution["measurement_count"] != counts["paired_eligible_run_count"]:
        raise ValueError(
            "candidate0 NI calibration measurements must equal paired-eligible runs"
        )
    if ni_resolution["independent_cluster_count"] > (
        counts["intersection_count"] + counts["corridor_count"]
    ):
        raise ValueError(
            "candidate0 NI calibration clusters exceed the frozen cluster inventory"
        )
    ni = dict(NONINFERIORITY_ENGINEERING_MARGINS)
    component = dict(COMPONENT_REGRESSION_MARGINS)
    for name, value in (
        ("frozen_model_registry_sha256", frozen_model_registry_sha256),
        ("training_scale_sha256", training_scale_sha256),
        ("context_scaler_sha256", context_scaler_sha256),
    ):
        _require_sha(value, name)
    independent_target_passed = bool(
        counts["corridor_count"] >= 5 and counts["route_count"] >= 50
    )
    coverage_passed = bool(counts["paired_eligible_rate"] >= 0.95)
    ni_resolvability_passed = bool(ni_resolution["all_margins_resolvable"])
    freeze_passed = bool(
        independent_target_passed and coverage_passed and ni_resolvability_passed
    )
    return {
        "schema_version": "camp_dp_v25_calibration_freeze_v1",
        "status": (
            "calibration_freeze_passed"
            if freeze_passed
            else "calibration_freeze_scientifically_ineligible"
        ),
        "fixed_dp_head": FIXED_DP_HEAD,
        "root_bindings": roots,
        "inventory": counts,
        "minimum_calibration_corridors": 5,
        "minimum_calibration_routes": 50,
        "minimum_paired_eligible_rate": 0.95,
        "independent_unit_target_passed": independent_target_passed,
        "coverage_gate_passed": coverage_passed,
        "noninferiority_resolvability_gate_passed": ni_resolvability_passed,
        "operational_overspeed_tolerance_mps": 0.1,
        "strict_speed_epsilon_mps": 1e-6,
        "safety_cost_contract": {
            "schema_version": "safety_cost_native_v22",
            "component_weights": dict(SAFETY_COST_COMPONENT_WEIGHTS),
            "native_component_fields": dict(SAFETY_COMPONENT_NATIVE_FIELDS),
            "collision_clearance_threshold_m": 1e-6,
            "near_miss_clearance_threshold_m": 2.0,
            "wrong_way_minimum_speed_mps": 0.5,
            "red_crossing_minimum_speed_mps": RED_CROSSING_MINIMUM_SPEED_MPS,
            "certified_signal_stop_line_required": True,
            "legacy_10m_stop_line_proximity_allowed": False,
        },
        "signal_safety_contract": {
            "schema_version": SIGNAL_SAFETY_SCHEMA_VERSION,
            "same_tick_phase_only": True,
            "future_phase_schedule_consumed": False,
            "phase_remaining_consumed": False,
            "certified_stop_line_required_for_all_mapped_phases": True,
            "red_crossing_minimum_speed_mps": RED_CROSSING_MINIMUM_SPEED_MPS,
            "false_stop_green_maximum_speed_mps": (
                FALSE_STOP_GREEN_MAXIMUM_SPEED_MPS
            ),
            "false_stop_green_approach_distance_m": (
                FALSE_STOP_GREEN_APPROACH_DISTANCE_M
            ),
            "false_stop_green_minimum_obb_clearance_m": (
                FALSE_STOP_GREEN_MINIMUM_OBB_CLEARANCE_M
            ),
            "red_margin_definition": (
                "minimum_post_interval_front_bumper_signed_normal_distance_m"
            ),
            "crossing_definition": "exact_front_bumper_motion_segment_intersection",
            "crossing_speed_definition": "post_interval_ego_speed_mps",
            "green_false_stop_denominator": (
                "green_same_tick_intervals_with_pre_front_signed_margin_in_[0,5]m_"
                "and_observable_minimum_obb_clearance_gt_3m"
            ),
            "obstruction_proxy_disclosed": "same_tick_minimum_obb_surface_clearance",
        },
        "noninferiority": {
            "estimator": "one_sided_95_percent_upper_equal_mass_cluster_mean_student_t",
            "harm_delta_contract": "method_minus_candidate0_positive_is_worse",
            "margins": ni,
            "margin_units": dict(NONINFERIORITY_MARGIN_UNITS),
            "margin_source": (
                "preregistered_engineering_acceptability_not_outcome_tuned"
            ),
            "calibration_resolvability": ni_resolution,
            "all_metrics_must_pass": True,
            "multiplicity": "intersection_union_no_adjustment",
        },
        "component_guardrails": {
            "estimator": "one_sided_95_percent_upper_equal_mass_cluster_mean_student_t",
            "margins": component,
            "all_components_must_pass": True,
        },
        "claim_rule_schema": "camp_dp_v25_fresh_b2_claim_decision_v1",
        "cluster_estimator": "equal_mass_cluster_mean_student_t",
        "seeds_or_ticks_counted_as_independent": False,
        "frozen_model_registry_sha256": frozen_model_registry_sha256,
        "training_scale_sha256": training_scale_sha256,
        "context_scaler_sha256": context_scaler_sha256,
        "atom_scale_changed_by_calibration": False,
        "model_parameters_changed_by_calibration": False,
        "noninferiority_margin_changed_by_calibration": False,
        "threshold_or_margin_changed_after_fresh": False,
        "calibration_closed_loop_outcomes_consumed": True,
        "calibration_candidate0_outcomes_consumed": True,
        "calibration_camp_method_outcomes_consumed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
        "fresh_preopen_qualification_allowed": freeze_passed,
        "fresh_open_authorized": False,
        "one_time_opening_release_required": True,
    }


def validate_v25_calibration_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild and type-exactly validate a frozen calibration contract."""

    if type(value) is not dict:
        raise ValueError("calibration contract must be a native mapping")
    try:
        expected = freeze_v25_calibration_contract(
            root_bindings=value["root_bindings"],
            inventory=value["inventory"],
            noninferiority_resolvability=value["noninferiority"][
                "calibration_resolvability"
            ],
            frozen_model_registry_sha256=value["frozen_model_registry_sha256"],
            training_scale_sha256=value["training_scale_sha256"],
            context_scaler_sha256=value["context_scaler_sha256"],
        )
    except (KeyError, TypeError) as exc:
        raise ValueError("calibration contract field structure drifted") from exc
    if not _strict_json_equal(value, expected):
        raise ValueError("calibration contract differs from the frozen reconstruction")
    return expected


def _ni_calibration_row(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != NI_CALIBRATION_ROW_FIELDS:
        raise ValueError("candidate0 NI calibration row field set drifted")
    row = dict(value)
    if row["schema_version"] != "camp_dp_v25_candidate0_ni_calibration_row_v1":
        raise ValueError("candidate0 NI calibration row schema drifted")
    if row["arm"] != "candidate0_operational_default":
        raise ValueError("NI margin calibration may consume candidate0 rows only")
    if type(row["cluster_id"]) is not str or not row["cluster_id"]:
        raise ValueError("candidate0 NI calibration cluster must be a native string")
    _require_sha(row["measurement_sha256"], "measurement_sha256")
    if row["fresh_b2_opened"] is not False or row["fresh_outcome_fields_consumed"] != []:
        raise ValueError("candidate0 NI calibration must not consume Fresh outcomes")
    row["performance"] = _metric_map(row["performance"], "calibration performance")
    if not 0.0 <= row["performance"]["completion"] <= 1.0:
        raise ValueError("candidate0 NI calibration completion must lie in [0,1]")
    return row


def _ni_resolvability(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != NI_RESOLVABILITY_FIELDS:
        raise ValueError("noninferiority resolvability field set drifted")
    result = dict(value)
    exact = {
        "schema_version": "camp_dp_v25_noninferiority_margin_resolvability_v1",
        "calibration_arm": "candidate0_operational_default",
        "margin_source": (
            "preregistered_engineering_acceptability_not_calibration_outcome_tuned"
        ),
        "residual_estimator": (
            "equal_cluster_equal_within_cluster_absolute_deviation_from_cluster_median"
        ),
        "residual_quantile": 0.95,
        "minimum_independent_clusters": 5,
        "minimum_measurements_per_cluster": 2,
        "margins": NONINFERIORITY_ENGINEERING_MARGINS,
        "margin_units": NONINFERIORITY_MARGIN_UNITS,
        "camp_method_outcomes_consumed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    for name, expected in exact.items():
        if type(result[name]) is not type(expected) or result[name] != expected:
            raise ValueError(f"noninferiority resolvability {name} drifted")
    for name in ("independent_cluster_count", "measurement_count"):
        if type(result[name]) is not int or result[name] < 0:
            raise ValueError(f"noninferiority resolvability {name} is invalid")
    if result["independent_cluster_count"] < 5:
        raise ValueError("noninferiority resolvability cluster count is below five")
    counts = result["cluster_measurement_counts"]
    if (
        type(counts) is not dict
        or len(counts) != result["independent_cluster_count"]
        or any(type(key) is not str or not key for key in counts)
        or any(type(count) is not int or count < 2 for count in counts.values())
        or sum(counts.values()) != result["measurement_count"]
    ):
        raise ValueError("noninferiority resolvability cluster accounting drifted")
    variability = _metric_map(
        result["q95_absolute_repeat_variability"], "repeat variability"
    )
    flags = result["margin_resolvable"]
    if (
        type(flags) is not dict
        or set(flags) != set(NONINFERIORITY_METRICS)
        or any(type(flag) is not bool for flag in flags.values())
    ):
        raise ValueError("noninferiority resolvability flags drifted")
    expected_flags = {
        name: bool(variability[name] <= NONINFERIORITY_ENGINEERING_MARGINS[name])
        for name in NONINFERIORITY_METRICS
    }
    if flags != expected_flags:
        raise ValueError("noninferiority resolvability flags are inconsistent")
    expected_all = all(expected_flags.values())
    if result["all_margins_resolvable"] is not expected_all:
        raise ValueError("noninferiority resolvability aggregate drifted")
    expected_status = (
        "noninferiority_margins_resolvable"
        if expected_all
        else "noninferiority_margins_not_resolvable"
    )
    if result["status"] != expected_status:
        raise ValueError("noninferiority resolvability status drifted")
    result["q95_absolute_repeat_variability"] = variability
    return result


def _inventory(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != CALIBRATION_INVENTORY_FIELDS:
        raise ValueError("calibration inventory field set drifted")
    result = dict(value)
    for field in (
        "map_count",
        "intersection_count",
        "corridor_count",
        "route_count",
        "planned_paired_run_count",
        "paired_eligible_run_count",
        "retained_failure_run_count",
    ):
        if type(result[field]) is not int or result[field] < 0:
            raise ValueError(f"calibration {field} must be a native nonnegative integer")
    planned = result["planned_paired_run_count"]
    eligible = result["paired_eligible_run_count"]
    retained = result["retained_failure_run_count"]
    if planned < 1 or eligible + retained != planned:
        raise ValueError("calibration paired denominator accounting is inconsistent")
    rate = result["paired_eligible_rate"]
    if (
        type(rate) not in (int, float)
        or not np.isfinite(float(rate))
        or not np.isclose(float(rate), eligible / planned, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("calibration paired eligible rate is inconsistent")
    result["paired_eligible_rate"] = float(rate)
    return result


def _margin_map(
    value: Mapping[str, float], expected: tuple[str, ...], label: str
) -> dict[str, float]:
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(f"{label} margin keyset drifted")
    result: dict[str, float] = {}
    for name in expected:
        margin = value[name]
        if (
            type(margin) not in (int, float)
            or not np.isfinite(float(margin))
            or float(margin) < 0.0
        ):
            raise ValueError(f"{label} margin {name} is invalid")
        result[name] = float(margin)
    return result


def _metric_map(value: Mapping[str, float], label: str) -> dict[str, float]:
    return _margin_map(value, NONINFERIORITY_METRICS, label)


def _native_nonnegative_number(value: Any, name: str) -> float:
    if (
        type(value) not in (int, float)
        or not np.isfinite(float(value))
        or float(value) < 0.0
    ):
        raise ValueError(f"{name} must be a finite native nonnegative number")
    return float(value)


def _weighted_quantile(
    values: np.ndarray,
    weights: np.ndarray,
    quantile: float,
) -> float:
    if (
        values.ndim != 1
        or weights.shape != values.shape
        or values.size < 1
        or not np.all(np.isfinite(values))
        or not np.all(np.isfinite(weights))
        or np.any(weights <= 0.0)
        or not 0.0 <= quantile <= 1.0
    ):
        raise ValueError("weighted quantile input is invalid")
    order = np.argsort(values, kind="stable")
    ordered = values[order]
    cumulative = np.cumsum(weights[order], dtype=np.float64)
    target = quantile * float(cumulative[-1])
    index = int(np.searchsorted(cumulative, target, side="left"))
    return float(ordered[min(index, ordered.size - 1)])


def _strict_json_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_json_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_json_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _root_map(value: Mapping[str, str]) -> dict[str, str]:
    if type(value) is not dict or set(value) != CALIBRATION_ROOT_BINDINGS:
        raise ValueError("calibration root binding keyset drifted")
    result = dict(value)
    for name, digest in result.items():
        _require_sha(digest, name)
    return result


def _require_sha(value: Any, name: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")


def _validate_native_safety_cost_weights() -> None:
    native_fields = tuple(SAFETY_COMPONENT_NATIVE_FIELDS.values())
    for name, field in SAFETY_COMPONENT_NATIVE_FIELDS.items():
        components = {key: 0.0 for key in native_fields}
        components[field] = 1.0
        if safety_cost_native_v1(components) != SAFETY_COST_COMPONENT_WEIGHTS[name]:
            raise ValueError("SafetyCost native component weight contract drifted")
