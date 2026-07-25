from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner_v21_native import segments_intersect_2d
from .diffusion_planner_v22_native import summarize_speed_protocol
from .diffusion_planner_v25_statistics import clustered_paired_summary


SCHEMA_VERSION = "camp_dp_v25_metric_semantics_amendment_v1"
STATUS = "sealed_read_only_metric_semantics_amendment"
CONTRACT_SCHEMA_VERSION = "camp_dp_v25_metric_semantics_amendment_contract_v1"
CONTRACT_STATUS = "frozen_outcome_independent_metric_semantics_contract"
REVIEW_SCHEMA_VERSION = "camp_dp_v25_metric_semantics_amendment_review_v1"

ARMS = ("candidate0", "static14d", "scene14d")
METHOD_ARMS = ("static14d", "scene14d")
DT_S = 0.1
TICK_COUNT = 64
RAW_ACCELERATION_COUNT = 62
FILTER_WIDTH = 11
FILTERED_SAMPLE_COUNT = 52
SENSITIVITY_THRESHOLDS_MPS2 = (0.5, 1.0, 2.0, 3.0)
CLEARANCE_THRESHOLDS_M = (0.0, 0.5, 1.0, 2.0)

SAFETY_COST_FORMULA = (
    "100*collision_any + 10*near_tick_rate + 20*offroad_tick_rate + "
    "20*wrongway_tick_rate + 30*red_any + 10*speed_tick_rate"
)

METRIC_CLASSIFICATIONS = {
    "safety_cost": "benchmark-only",
    "collision": "benchmark-only",
    "near_miss": "FAIL-industrial",
    "offroad": "FAIL-industrial",
    "wrong_way": "FAIL-industrial",
    "red_light_source_authority": "PASS",
    "red_light_outcome_aggregate": "benchmark-only",
    "speed": "benchmark-only",
    "progress_completion": "benchmark-only",
    "jerk": "FAIL-industrial",
    "lateral_acceleration": "FAIL-industrial",
    "maximum_deceleration": "FAIL-industrial",
    "latency_measurement": "benchmark-only",
    "online_production_readiness": "FAIL-industrial",
    "clustered_statistics": "PASS",
    "full_polygon_offroad": "evidence-missing",
    "occupant_seat_vertical_comfort": "evidence-missing",
}

LEGACY_ALIASES = {
    "safety.total": "legacy_project_defined_controlled_benchmark_safetycost",
    "safety.collision": "simulation_obb_overlap_any",
    "safety.near_miss": "noncollision_obb_clearance_le_2m_tick_rate",
    "safety.offroad": "five_point_drivable_coverage_failure_tick_rate",
    "safety.wrong_way": (
        "nearest_route_segment_heading_opposition_moving_onroad_tick_rate"
    ),
    "safety.red_light": (
        "certified_red_phase_stopline_crossing_gt_0_5mps_any"
    ),
    "safety.speed": "onroad_speed_excess_gt_0_1mps_tick_rate",
    "performance.progress": "final_nearest_route_polyline_projection_m",
    "performance.completion": "clipped_final_route_projection_fraction",
    "performance.mean_jerk": (
        "raw_longitudinal_speed_second_difference_chatter_diagnostic_mean_abs"
    ),
    "performance.max_jerk": (
        "raw_longitudinal_speed_second_difference_chatter_diagnostic_max_abs"
    ),
    "performance.mean_lateral_acceleration": (
        "raw_speed_times_heading_rate_lateral_kinematic_diagnostic_mean_abs"
    ),
    "performance.max_lateral_acceleration": (
        "raw_speed_times_heading_rate_lateral_kinematic_diagnostic_max_abs"
    ),
    "performance.maximum_deceleration": (
        "raw_same_tick_scalar_speed_drop_peak_deceleration_diagnostic"
    ),
}

LEGACY_FORMULAS = {
    "safety.total": SAFETY_COST_FORMULA,
    "safety.collision": "any(min_obb_clearance_m <= 1e-6)",
    "safety.near_miss": (
        "count(1e-6 < min_obb_clearance_m <= 2.0m) / 64"
    ),
    "safety.offroad": "count(not five_point_drivable_coverage) / 64",
    "safety.wrong_way": (
        "count(coverage and speed>0.5 and cos(ego_heading-route_heading)<0) / "
        "count(coverage and speed>0.5)"
    ),
    "safety.red_light": (
        "any(certified red phase stop-line crossing and post speed > 0.5m/s)"
    ),
    "safety.speed": (
        "count(onroad speed excess > 0.1m/s + 1e-6) / count(onroad ticks)"
    ),
    "performance.progress": "final nearest-route-segment polyline projection",
    "performance.completion": "clip(final route projection / route length,0,1)",
    "performance.mean_jerk": (
        "mean(abs(diff(diff(scalar_speed)/0.1)/0.1))"
    ),
    "performance.max_jerk": (
        "max(abs(diff(diff(scalar_speed)/0.1)/0.1))"
    ),
    "performance.mean_lateral_acceleration": (
        "mean(abs(speed[1:]*wrapped_diff(heading)/0.1))"
    ),
    "performance.max_lateral_acceleration": (
        "max(abs(speed[1:]*wrapped_diff(heading)/0.1))"
    ),
    "performance.maximum_deceleration": (
        "max(max(pre_decision_speed-post_speed,0)/0.1)"
    ),
}


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode(
            "utf-8"
        )
    ).hexdigest()


def metric_semantics_contract() -> dict[str, Any]:
    legacy = {
        name: {
            "legacy_field": name,
            "accurate_alias": LEGACY_ALIASES[name],
            "formula": LEGACY_FORMULAS[name],
            "deprecated_industrial_interpretation": True,
        }
        for name in sorted(LEGACY_ALIASES)
    }
    result = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "status": CONTRACT_STATUS,
        "benchmark": "fresh_b4",
        "amendment_schema_version": SCHEMA_VERSION,
        "outcome_independent": True,
        "legacy_namespace": legacy,
        "metric_classifications": dict(METRIC_CLASSIFICATIONS),
        "body_proxy": {
            "name": "vehicle_body_kinematic_comfort_proxy",
            "signal_name": "filtered_vehicle_body_acceleration",
            "source_fields": ["position_xy", "ego_heading_rad"],
            "dt_s": DT_S,
            "tick_count": TICK_COUNT,
            "interval_velocity_count": 63,
            "raw_acceleration_count": RAW_ACCELERATION_COUNT,
            "raw_acceleration_tick_indices": [1, 62],
            "rotation": (
                "long=ax*cos(heading_i)+ay*sin(heading_i);"
                "lateral=-ax*sin(heading_i)+ay*cos(heading_i)"
            ),
            "filter": {
                "kind": "centered_equal_weight_boxcar",
                "zero_phase": True,
                "width_samples": FILTER_WIDTH,
                "window_s": 1.0,
                "valid_only": True,
                "padding": False,
                "extrapolation": False,
                "filtered_sample_count": FILTERED_SAMPLE_COUNT,
            },
            "summary_statistics": [
                "signed_mean",
                "rms",
                "min",
                "max",
                "peak_abs",
                "abs_p50",
                "abs_p90",
                "abs_p95",
                "abs_p99",
            ],
            "duration_thresholds_mps2": list(SENSITIVITY_THRESHOLDS_MPS2),
            "duration_grid_is_project_sensitivity_not_industrial_threshold": True,
            "per_run_before_pair_and_cluster": True,
            "pooled_ticks_as_independent": False,
            "new_ni_or_claim_gate": False,
        },
        "extensions": {
            "clearance_thresholds_m": list(CLEARANCE_THRESHOLDS_M),
            "clearance_outputs": ["minimum_m", "duration_s", "episode_count"],
            "red_outputs": [
                "certified_phase_line_binding",
                "unthresholded_crossing_count",
                "red_phase_interval_count",
                "crossing_rate_per_red_phase_interval",
                "crossing_speed_mps",
                "minimum_stop_line_margin_m",
                "gt_0_5mps_violation_count",
            ],
            "speed_protocol": {
                "schema_version": "speed_protocol_v22",
                "strict_and_sensitivity_tolerances_mps": [0.0, 0.05, 0.1, 0.2],
                "continuous": [
                    "maximum_excess_mps",
                    "mean_excess_mps",
                    "excess_duration_s",
                    "magnitude_duration_m",
                ],
            },
            "route_outputs": [
                "final_nearest_route_polyline_projection_m",
                "clipped_final_route_projection_fraction",
                "net_route_projection_m",
                "maximum_route_projection_gain_m",
                "backtracking_duration_s",
                "backtracking_distance_m",
                "distance_traveled_m",
            ],
        },
        "missing_evidence": {
            "full_polygon_offroad": "evidence_missing",
            "suspension_response": "not_modeled",
            "seat_response": "not_modeled",
            "human_body_transfer": "not_modeled",
            "vertical_acceleration": "not_modeled",
            "roll_pitch_yaw_rotational_coupling": "not_modeled",
            "iso_2631_conformity": "not_assessed",
            "sae_j2834_conformity": "not_assessed",
            "industrial_occupant_comfort": "evidence_missing_not_assessed",
        },
        "claim_invariance": {
            "frozen_claim_recomputed": False,
            "new_confirmatory_claim_authorized": False,
            "final_claim_decision": (
                "honest_no_claim_under_frozen_preregistered_all_gate"
            ),
            "industrial_comfort_decision_claimed": False,
            "fresh_benefit_claim_authorized": False,
            "real_road_safety_claim_authorized": False,
            "broad_unseen_map_claim_authorized": False,
            "native_ranked_top1_claim_authorized": False,
            "promotion_or_deployment_authorized": False,
        },
    }
    result["contract_sha256"] = canonical_sha256(result)
    return result


def validate_metric_semantics_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = metric_semantics_contract()
    if type(value) is not dict or value != expected:
        raise ValueError("metric-semantics contract drifted")
    return dict(value)


def summarize_run(
    native_receipt: Mapping[str, Any],
    evaluation_row: Mapping[str, Any],
) -> dict[str, Any]:
    if type(native_receipt) is not dict or type(evaluation_row) is not dict:
        raise ValueError("metric amendment run inputs must be objects")
    ticks = native_receipt.get("ticks")
    if type(ticks) is not list or len(ticks) != TICK_COUNT:
        raise ValueError("metric amendment requires exactly 64 sealed ticks")
    if evaluation_row.get("status") != "complete":
        raise ValueError("metric amendment only accepts complete frozen rows")
    arm = evaluation_row.get("arm")
    if arm not in ARMS:
        raise ValueError("metric amendment arm drifted")
    safety = _mapping(native_receipt, "safety")
    secondary = _mapping(native_receipt, "secondary")
    signal = _mapping(native_receipt, "signal_safety")
    legacy_values = _legacy_values(evaluation_row)
    _require_legacy_equality(legacy_values, safety, secondary, ticks)

    body = _body_proxy(ticks)
    clearance = _clearance_extension(ticks)
    red = _red_extension(ticks, signal)
    speed = _speed_extension(ticks, safety)
    route = _route_extension(ticks, secondary)
    return {
        "pair_key": _nonempty(evaluation_row.get("pair_key"), "pair_key"),
        "arm": arm,
        "inference_cluster_id": _nonempty(
            evaluation_row.get("inference_cluster_id"), "inference_cluster_id"
        ),
        "benchmark_stratum": _nonempty(
            evaluation_row.get("benchmark_stratum"), "benchmark_stratum"
        ),
        "scenario_family": _nonempty(
            evaluation_row.get("scenario_family"), "scenario_family"
        ),
        "source_class": _nonempty(
            evaluation_row.get("source_class"), "source_class"
        ),
        "legacy_namespace": {
            name: {
                "legacy_field": name,
                "original_value": legacy_values[name],
                "accurate_alias": LEGACY_ALIASES[name],
                "formula": LEGACY_FORMULAS[name],
                "source_root_role": "sealed_fresh_b4_execution",
                "deprecated_industrial_interpretation": True,
            }
            for name in sorted(legacy_values)
        },
        "vehicle_body_kinematic_comfort_proxy": body,
        "clearance_descriptive": clearance,
        "certified_signal_descriptive": red,
        "speed_protocol_descriptive": speed,
        "route_descriptive": route,
        "full_polygon_offroad": {
            "status": "evidence_missing",
            "five_point_proxy_used_as_polygon_substitute": False,
        },
        "occupant_comfort": {
            "status": "evidence_missing_not_assessed",
            "vehicle_body_proxy_is_seat_or_human_response": False,
        },
    }


def build_amendment(
    run_summaries: Sequence[Mapping[str, Any]],
    *,
    bindings: Mapping[str, Any],
    contract_root_sha256: str,
    contract_review_root_sha256: str,
    source_file_sha256: str,
) -> dict[str, Any]:
    runs = [dict(row) for row in run_summaries]
    if len(runs) != 1500:
        raise ValueError("metric amendment requires 1500 complete arms")
    keys: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in runs:
        pair = _nonempty(row.get("pair_key"), "pair_key")
        arm = row.get("arm")
        if arm not in ARMS or arm in keys[pair]:
            raise ValueError("metric amendment pair/arm denominator drifted")
        keys[pair][arm] = row
    if len(keys) != 500 or any(set(row) != set(ARMS) for row in keys.values()):
        raise ValueError("metric amendment requires 500 complete three-arm pairs")
    pairs = [keys[key] for key in sorted(keys)]
    flat_metrics = _descriptive_scalar_paths(runs[0])
    arm_summaries = {
        arm: {
            path: float(np.mean([_path_float(pair[arm], path) for pair in pairs]))
            for path in flat_metrics
        }
        for arm in ARMS
    }
    paired = {
        method: {
            path: clustered_paired_summary(
                np.asarray(
                    [
                        _path_float(pair[method], path)
                        - _path_float(pair["candidate0"], path)
                        for pair in pairs
                    ],
                    dtype=np.float64,
                ),
                [pair[method]["inference_cluster_id"] for pair in pairs],
            )
            for path in flat_metrics
        }
        for method in METHOD_ARMS
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "benchmark": "fresh_b4",
        "bindings": dict(bindings),
        "contract_root_sha256": _sha(contract_root_sha256, "contract root"),
        "contract_review_root_sha256": _sha(
            contract_review_root_sha256, "contract review root"
        ),
        "source_execution_payload_sha256": _sha(
            source_file_sha256, "source execution payload"
        ),
        "denominator": {
            "pair_count": 500,
            "complete_arm_count": 1500,
            "tick_count": 96000,
            "full_denominator_reused": True,
            "fresh_execution_rerun": False,
        },
        "metric_classifications": dict(METRIC_CLASSIFICATIONS),
        "legacy_namespace_contract": metric_semantics_contract()[
            "legacy_namespace"
        ],
        "run_summaries": runs,
        "descriptive_arm_means": arm_summaries,
        "descriptive_paired_cluster_summaries": paired,
        "descriptive_scalar_paths": flat_metrics,
        "sample_accounting": {
            "ticks_per_run": TICK_COUNT,
            "interval_velocities_per_run": 63,
            "raw_body_accelerations_per_run": RAW_ACCELERATION_COUNT,
            "filtered_body_accelerations_per_run": FILTERED_SAMPLE_COUNT,
            "per_run_summarized_before_pairing_and_clustering": True,
            "ticks_pooled_as_independent": False,
        },
        "missing_evidence": metric_semantics_contract()["missing_evidence"],
        "claim_invariance": metric_semantics_contract()["claim_invariance"],
        "legacy_values_mutated": False,
        "sealed_execution_written": False,
        "scientific_or_continuation_cas_written": False,
    }
    return result


def validate_amendment_shape(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("metric amendment must be an object")
    required = {
        "schema_version",
        "status",
        "benchmark",
        "bindings",
        "contract_root_sha256",
        "contract_review_root_sha256",
        "source_execution_payload_sha256",
        "denominator",
        "metric_classifications",
        "legacy_namespace_contract",
        "run_summaries",
        "descriptive_arm_means",
        "descriptive_paired_cluster_summaries",
        "descriptive_scalar_paths",
        "sample_accounting",
        "missing_evidence",
        "claim_invariance",
        "legacy_values_mutated",
        "sealed_execution_written",
        "scientific_or_continuation_cas_written",
    }
    if set(value) != required:
        raise ValueError("metric amendment field set drifted")
    if (
        value["schema_version"] != SCHEMA_VERSION
        or value["status"] != STATUS
        or value["benchmark"] != "fresh_b4"
        or value["metric_classifications"] != METRIC_CLASSIFICATIONS
        or value["legacy_namespace_contract"]
        != metric_semantics_contract()["legacy_namespace"]
        or value["missing_evidence"] != metric_semantics_contract()["missing_evidence"]
        or value["claim_invariance"] != metric_semantics_contract()["claim_invariance"]
        or value["legacy_values_mutated"] is not False
        or value["sealed_execution_written"] is not False
        or value["scientific_or_continuation_cas_written"] is not False
    ):
        raise ValueError("metric amendment invariant drifted")
    denominator = value["denominator"]
    if denominator != {
        "pair_count": 500,
        "complete_arm_count": 1500,
        "tick_count": 96000,
        "full_denominator_reused": True,
        "fresh_execution_rerun": False,
    }:
        raise ValueError("metric amendment denominator drifted")
    if type(value["run_summaries"]) is not list or len(value["run_summaries"]) != 1500:
        raise ValueError("metric amendment run summaries drifted")
    return dict(value)


def _legacy_values(row: Mapping[str, Any]) -> dict[str, float]:
    safety = _mapping(row, "safety")
    performance = _mapping(row, "performance")
    return {
        **{
            f"safety.{name}": _finite(safety.get(name), f"safety.{name}")
            for name in ("total", "collision", "near_miss", "offroad", "wrong_way", "red_light", "speed")
        },
        **{
            f"performance.{name}": _finite(
                performance.get(name), f"performance.{name}"
            )
            for name in (
                "progress",
                "completion",
                "mean_jerk",
                "max_jerk",
                "mean_lateral_acceleration",
                "max_lateral_acceleration",
                "maximum_deceleration",
            )
        },
    }


def _require_legacy_equality(
    legacy: Mapping[str, float],
    safety: Mapping[str, Any],
    secondary: Mapping[str, Any],
    ticks: Sequence[Mapping[str, Any]],
) -> None:
    components = _mapping(safety, "components")
    sources = {
        "safety.total": safety.get("safety_cost"),
        "safety.collision": components.get("collision_any"),
        "safety.near_miss": components.get("near_miss_noncollision_rate"),
        "safety.offroad": components.get("offroad_rate"),
        "safety.wrong_way": components.get("wrong_way_rate"),
        "safety.red_light": components.get("red_light_violation_any"),
        "safety.speed": components.get("speed_limit_violation_rate"),
        "performance.progress": secondary.get("route_progress_m"),
        "performance.completion": secondary.get("route_completion_rate"),
        "performance.mean_jerk": secondary.get("mean_abs_jerk_mps3"),
        "performance.max_jerk": secondary.get("max_jerk_mps3"),
        "performance.mean_lateral_acceleration": secondary.get(
            "mean_abs_lateral_acceleration_mps2"
        ),
        "performance.max_lateral_acceleration": secondary.get(
            "max_abs_lateral_acceleration_mps2"
        ),
        "performance.maximum_deceleration": max(
            max(
                _finite(tick.get("pre_decision_speed_mps"), "pre speed")
                - _finite(_mapping(tick, "safety").get("speed_mps"), "post speed"),
                0.0,
            )
            / DT_S
            for tick in ticks
        ),
    }
    for name, expected in legacy.items():
        actual = _finite(sources[name], name)
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"legacy value drifted: {name}")


def _body_proxy(ticks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    positions = np.asarray(
        [_finite_xy(_mapping(tick, "safety").get("position_xy"), "position_xy") for tick in ticks],
        dtype=np.float64,
    )
    headings = np.asarray(
        [
            _finite(_mapping(tick, "safety").get("ego_heading_rad"), "heading")
            for tick in ticks
        ],
        dtype=np.float64,
    )
    velocities = np.diff(positions, axis=0) / DT_S
    world_acceleration = np.diff(velocities, axis=0) / DT_S
    aligned_heading = headings[1:-1]
    longitudinal = (
        world_acceleration[:, 0] * np.cos(aligned_heading)
        + world_acceleration[:, 1] * np.sin(aligned_heading)
    )
    lateral = (
        -world_acceleration[:, 0] * np.sin(aligned_heading)
        + world_acceleration[:, 1] * np.cos(aligned_heading)
    )
    kernel = np.full(FILTER_WIDTH, 1.0 / FILTER_WIDTH, dtype=np.float64)
    filtered_longitudinal = np.convolve(longitudinal, kernel, mode="valid")
    filtered_lateral = np.convolve(lateral, kernel, mode="valid")
    if (
        velocities.shape != (63, 2)
        or world_acceleration.shape != (RAW_ACCELERATION_COUNT, 2)
        or filtered_longitudinal.shape != (FILTERED_SAMPLE_COUNT,)
        or filtered_lateral.shape != (FILTERED_SAMPLE_COUNT,)
    ):
        raise AssertionError("body proxy sample accounting drifted")
    return {
        "schema_version": "vehicle_body_kinematic_comfort_proxy_v1",
        "signal_name": "filtered_vehicle_body_acceleration",
        "dt_s": DT_S,
        "filter": {
            "kind": "centered_equal_weight_boxcar",
            "width_samples": FILTER_WIDTH,
            "window_s": 1.0,
            "zero_phase": True,
            "valid_only": True,
            "padding": False,
            "extrapolation": False,
        },
        "sample_count": FILTERED_SAMPLE_COUNT,
        "discarded_boundary_raw_samples": RAW_ACCELERATION_COUNT - FILTERED_SAMPLE_COUNT,
        "longitudinal_mps2": _signed_summary(filtered_longitudinal),
        "lateral_mps2": _signed_summary(filtered_lateral),
        "duration_s": {
            "longitudinal_abs_gt": _duration_grid(
                np.abs(filtered_longitudinal), mode="gt"
            ),
            "lateral_abs_gt": _duration_grid(np.abs(filtered_lateral), mode="gt"),
            "signed_deceleration_lt_negative": _duration_grid(
                filtered_longitudinal, mode="lt_negative"
            ),
        },
        "duration_grid_is_project_sensitivity_not_industrial_threshold": True,
        "occupant_or_seat_response_claimed": False,
        "iso_2631_or_sae_j2834_conformity_claimed": False,
    }


def _signed_summary(values: np.ndarray) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.shape != (FILTERED_SAMPLE_COUNT,) or not np.isfinite(array).all():
        raise ValueError("filtered body proxy values drifted")
    absolute = np.abs(array)
    return {
        "signed_mean": float(np.mean(array)),
        "rms": float(np.sqrt(np.mean(array**2))),
        "min": float(np.min(array)),
        "max": float(np.max(array)),
        "peak_abs": float(np.max(absolute)),
        "abs_p50": float(np.percentile(absolute, 50)),
        "abs_p90": float(np.percentile(absolute, 90)),
        "abs_p95": float(np.percentile(absolute, 95)),
        "abs_p99": float(np.percentile(absolute, 99)),
    }


def _duration_grid(values: np.ndarray, *, mode: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for threshold in SENSITIVITY_THRESHOLDS_MPS2:
        count = (
            int(np.sum(values > threshold))
            if mode == "gt"
            else int(np.sum(values < -threshold))
        )
        result[_number_key(threshold)] = count * DT_S
    return result


def _clearance_extension(ticks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = np.asarray(
        [
            _finite(_mapping(tick, "safety").get("min_obb_clearance_m"), "clearance")
            for tick in ticks
        ],
        dtype=np.float64,
    )
    if np.any(values < 0.0):
        raise ValueError("clearance values must be nonnegative")
    thresholds: dict[str, Any] = {}
    for threshold in CLEARANCE_THRESHOLDS_M:
        mask = values <= threshold
        thresholds[_number_key(threshold)] = {
            "sample_count": int(np.sum(mask)),
            "duration_s": int(np.sum(mask)) * DT_S,
            "episode_count": _episode_count(mask),
        }
    return {
        "minimum_m": float(np.min(values)),
        "thresholds_le_m": thresholds,
        "threshold_grid_is_descriptive": True,
        "clearance_le_2m_named_near_miss": False,
    }


def _red_extension(
    ticks: Sequence[Mapping[str, Any]], signal: Mapping[str, Any]
) -> dict[str, Any]:
    red_exposure = 0
    crossings: list[float] = []
    violation_count = 0
    margins: list[float] = []
    for tick in ticks:
        safety = _mapping(tick, "safety")
        phase = safety.get("signal_phase_at_interval_start")
        if phase != "red":
            continue
        red_exposure += 1
        lines = safety.get("certified_signal_stop_lines")
        if type(lines) is not list or len(lines) != 1:
            raise ValueError("red tick lacks one certified stop line")
        line = np.asarray(lines[0], dtype=np.float64)
        previous = _finite_xy(safety.get("front_center_prev_xy"), "front previous")
        current = _finite_xy(safety.get("front_center_xy"), "front current")
        heading = _finite(safety.get("route_heading_rad"), "route heading")
        margins.append(_signed_stop_line_margin(current, line, heading))
        if segments_intersect_2d(previous, current, line[0], line[1]):
            speed = _finite(safety.get("speed_mps"), "crossing speed")
            crossings.append(speed)
            violation_count += int(speed > 0.5)
    metrics = _mapping(signal, "metrics")
    counts = _mapping(signal, "counts")
    denominators = _mapping(signal, "denominators")
    expected = {
        "crossings": int(counts.get("red_crossing_intervals")),
        "violations": int(counts.get("red_violation_intervals")),
        "red_exposure": int(denominators.get("red_phase_intervals")),
    }
    actual = {
        "crossings": len(crossings),
        "violations": violation_count,
        "red_exposure": red_exposure,
    }
    if actual != expected:
        raise ValueError("certified red-light accounting drifted")
    rate = len(crossings) / max(red_exposure, 1)
    if not math.isclose(
        rate, _finite(metrics.get("stop_line_crossing_rate"), "crossing rate"),
        rel_tol=0.0, abs_tol=1e-12
    ):
        raise ValueError("certified red crossing rate drifted")
    return {
        "certified_phase_line_binding": True,
        "future_phase_consumed": False,
        "red_phase_interval_count": red_exposure,
        "unthresholded_crossing_count": len(crossings),
        "crossing_rate_per_red_phase_interval": rate,
        "crossing_speed_mps": {
            "mean": float(np.mean(crossings)) if crossings else 0.0,
            "min": float(np.min(crossings)) if crossings else 0.0,
            "max": float(np.max(crossings)) if crossings else 0.0,
        },
        "minimum_stop_line_margin_m": min(margins) if margins else 0.0,
        "gt_0_5mps_violation_count": violation_count,
        "gt_0_5mps_violation_any": bool(violation_count),
        "legal_or_type_approval_violation_rate_claimed": False,
    }


def _speed_extension(
    ticks: Sequence[Mapping[str, Any]], safety: Mapping[str, Any]
) -> dict[str, Any]:
    records = [_mapping(tick, "safety") for tick in ticks]
    rebuilt = summarize_speed_protocol(records, dt=DT_S)
    recorded = safety.get("speed_protocol")
    if recorded != rebuilt:
        raise ValueError("sealed speed protocol does not match exact tick reconstruction")
    result = json.loads(json.dumps(rebuilt))
    result["descriptive_event_rates_by_tolerance_mps"] = {
        _number_key(tolerance): float(
            rebuilt["sensitivity"]["0.0" if tolerance == 0.0 else str(tolerance)][
                "event_rate"
            ]
        )
        for tolerance in (0.0, 0.05, 0.1, 0.2)
    }
    result["operational_tolerance_is_project_defined_not_legal"] = True
    result["eu_isa_or_type_approval_conformity_claimed"] = False
    return result


def _route_extension(
    ticks: Sequence[Mapping[str, Any]], secondary: Mapping[str, Any]
) -> dict[str, Any]:
    progress = np.asarray(
        [
            _finite(_mapping(tick, "safety").get("route_progress_m"), "route progress")
            for tick in ticks
        ],
        dtype=np.float64,
    )
    positions = np.asarray(
        [_finite_xy(_mapping(tick, "safety").get("position_xy"), "position") for tick in ticks],
        dtype=np.float64,
    )
    final = float(progress[-1])
    route_length = _finite(secondary.get("route_length_m"), "route length")
    if route_length <= 0.0:
        raise ValueError("route length must be positive")
    differences = np.diff(progress)
    negative = np.minimum(differences, 0.0)
    distance = float(np.linalg.norm(np.diff(positions, axis=0), axis=1).sum())
    if not math.isclose(
        final,
        _finite(secondary.get("route_progress_m"), "secondary route progress"),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("final route projection drifted from sealed legacy value")
    if not math.isclose(
        distance,
        _finite(secondary.get("distance_traveled_m"), "distance traveled"),
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("distance-traveled reconstruction drifted")
    return {
        "final_nearest_route_polyline_projection_m": final,
        "clipped_final_route_projection_fraction": min(
            max(final / route_length, 0.0), 1.0
        ),
        "net_route_projection_m": final - float(progress[0]),
        "maximum_route_projection_gain_m": float(np.max(progress)) - float(progress[0]),
        "backtracking_duration_s": int(np.sum(differences < 0.0)) * DT_S,
        "backtracking_distance_m": float(-np.sum(negative)),
        "distance_traveled_m": distance,
        "nearest_segment_projection_is_route_order_state": False,
    }


def _descriptive_scalar_paths(run: Mapping[str, Any]) -> list[str]:
    paths: list[str] = []
    body = _mapping(run, "vehicle_body_kinematic_comfort_proxy")
    for axis in ("longitudinal_mps2", "lateral_mps2"):
        for statistic in (
            "signed_mean", "rms", "min", "max", "peak_abs",
            "abs_p50", "abs_p90", "abs_p95", "abs_p99",
        ):
            paths.append(f"vehicle_body_kinematic_comfort_proxy.{axis}.{statistic}")
    for family in (
        "longitudinal_abs_gt",
        "lateral_abs_gt",
        "signed_deceleration_lt_negative",
    ):
        for threshold in map(_number_key, SENSITIVITY_THRESHOLDS_MPS2):
            paths.append(
                f"vehicle_body_kinematic_comfort_proxy.duration_s.{family}.{threshold}"
            )
    for threshold in map(_number_key, CLEARANCE_THRESHOLDS_M):
        for field in ("duration_s", "episode_count"):
            paths.append(f"clearance_descriptive.thresholds_le_m.{threshold}.{field}")
    paths.append("clearance_descriptive.minimum_m")
    for field in (
        "red_phase_interval_count",
        "unthresholded_crossing_count",
        "crossing_rate_per_red_phase_interval",
        "minimum_stop_line_margin_m",
        "gt_0_5mps_violation_count",
    ):
        paths.append(f"certified_signal_descriptive.{field}")
    for field in ("mean", "min", "max"):
        paths.append(f"certified_signal_descriptive.crossing_speed_mps.{field}")
    for tolerance in ("0", "0_05", "0_1", "0_2"):
        paths.append(
            "speed_protocol_descriptive."
            f"descriptive_event_rates_by_tolerance_mps.{tolerance}"
        )
    for field in (
        "maximum_excess_mps",
        "mean_excess_mps",
        "excess_duration_s",
        "magnitude_duration_m",
    ):
        paths.append(f"speed_protocol_descriptive.continuous.{field}")
    for field in (
        "final_nearest_route_polyline_projection_m",
        "clipped_final_route_projection_fraction",
        "net_route_projection_m",
        "maximum_route_projection_gain_m",
        "backtracking_duration_s",
        "backtracking_distance_m",
        "distance_traveled_m",
    ):
        paths.append(f"route_descriptive.{field}")
    for path in paths:
        _path_float(run, path)
    return paths


def _path_float(value: Mapping[str, Any], path: str) -> float:
    current: Any = value
    for part in path.split("."):
        if type(current) is not dict or part not in current:
            raise ValueError(f"descriptive scalar path missing: {path}")
        current = current[part]
    return _finite(current, path)


def _episode_count(mask: np.ndarray) -> int:
    values = np.asarray(mask, dtype=np.bool_)
    if values.ndim != 1:
        raise ValueError("episode mask must be one-dimensional")
    return int(np.sum(values & np.concatenate(([True], ~values[:-1]))))


def _signed_stop_line_margin(
    point_xy: np.ndarray, stop_line: np.ndarray, route_heading_rad: float
) -> float:
    tangent = np.asarray(stop_line[1] - stop_line[0], dtype=np.float64)
    length = float(np.linalg.norm(tangent))
    if not math.isfinite(length) or length <= 1e-9:
        raise ValueError("certified stop line is degenerate")
    tangent /= length
    normal = np.asarray([-tangent[1], tangent[0]], dtype=np.float64)
    direction = np.asarray(
        [math.cos(route_heading_rad), math.sin(route_heading_rad)], dtype=np.float64
    )
    alignment = float(normal @ direction)
    if abs(alignment) <= 1e-6:
        raise ValueError("certified stop line is parallel to route direction")
    if alignment < 0.0:
        normal = -normal
    midpoint = np.asarray(stop_line, dtype=np.float64).mean(axis=0)
    return float((midpoint - point_xy) @ normal)


def _mapping(value: Mapping[str, Any], name: str) -> dict[str, Any]:
    item = value.get(name)
    if type(item) is not dict:
        raise ValueError(f"{name} must be an object")
    return dict(item)


def _finite(value: Any, label: str) -> float:
    if type(value) not in {int, float} or type(value) is bool:
        raise ValueError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _finite_xy(value: Any, label: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (2,) or not np.isfinite(array).all():
        raise ValueError(f"{label} must be finite xy")
    return array


def _nonempty(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{label} must be nonempty")
    return value


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{label} must be a lowercase SHA256")
    return value


def _number_key(value: float) -> str:
    return f"{value:g}".replace(".", "_")
