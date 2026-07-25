"""Independent literal and pure-function oracle for fair-pool contract v2.

This module intentionally imports neither v1/v2 producer contract nor the
input-manifest materializer.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import beta


EXPECTED_SCHEMA = "camp_dp_v25_fair_pool_adaptation_contract_v2"
EXPECTED_PAYLOAD_SHA256 = (
    "338b33ef7fc62ac014bcabf81ad2f349c370bbf4a5924ad72c9445e27bfeacad"
)
EXPECTED_SAMPLER_SHA256 = (
    "33f5ea5eb6d92757fbb408e318eccd04048265a295871c9862f1ca539a98bfb6"
)
EXPECTED_ROUTE_SHA256 = (
    "63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd"
)
EXPECTED_MAP_SHA256 = (
    "c13a9234727186c77c019766c3358c30faf10af61503a566f0fff0963be53bbd"
)
EXPECTED_NAMES = (
    "jerk_early",
    "jerk_late",
    "jerk_full",
    "rms_acceleration",
    "speed_limit_margin_0_0",
    "speed_limit_margin_0_5",
    "speed_limit_margin_1_0",
    "lane_deviation",
    "clearance",
    "progress_shortfall",
    "planned_red_light_cost",
    "planned_lateral_acceleration_cost",
    "red_stopping_margin_cost",
    "dp_prior_jerk_excess_cost",
)


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def literal_quantile_higher(values: Sequence[float], q: float) -> float:
    array = _finite_vector(values)
    if not 0 <= q <= 1:
        raise ValueError("invalid q")
    ordered = sorted(float(value) for value in array)
    return ordered[int(math.ceil(q * (len(ordered) - 1)))]


def literal_bootstrap_upper(
    state_statistics: Sequence[float], resolution_floor: float
) -> float:
    values = _finite_vector(state_statistics)
    if len(values) != 64 or not math.isfinite(resolution_floor) or resolution_floor <= 0:
        raise ValueError("bootstrap inputs drifted")
    rng = np.random.Generator(np.random.PCG64DXSM(825071))
    indices = rng.integers(
        0, 64, size=(10000, 64), endpoint=False, dtype=np.int64
    )
    statistics: list[float] = []
    for row in indices:
        sample = [float(values[int(index)]) for index in row]
        statistics.append(literal_quantile_higher(sample, 0.99))
    upper = literal_quantile_higher(statistics, 0.95)
    return max(float(resolution_floor), upper)


def literal_cp_upper(k: int, n: int) -> float:
    if type(k) is not int or type(n) is not int or n <= 0 or not 0 <= k <= n:
        raise ValueError("invalid counts")
    if k == 0:
        return 1.0 - 0.05 ** (1.0 / n)
    if k == n:
        return 1.0
    return float(beta.ppf(0.95, k + 1, n - k))


def literal_numeric_endpoint_result(
    endpoint_id: str,
    state_errors: Sequence[float],
    threshold: float,
) -> dict[str, Any]:
    if type(endpoint_id) is not str or not endpoint_id:
        raise ValueError("endpoint id invalid")
    if not math.isfinite(float(threshold)) or float(threshold) <= 0:
        raise ValueError("threshold invalid")
    try:
        values = _finite_vector(state_errors)
    except (TypeError, ValueError):
        return {
            "endpoint_id": endpoint_id,
            "applicable": True,
            "state_denominator": (
                len(state_errors) if hasattr(state_errors, "__len__") else 0
            ),
            "missing_state_count": 1,
            "threshold": float(threshold),
            "exceedance_count": None,
            "clopper_pearson_upper_95": None,
            "status": "evidence_missing",
        }
    if len(values) != 64:
        return {
            "endpoint_id": endpoint_id,
            "applicable": True,
            "state_denominator": len(values),
            "missing_state_count": abs(64 - len(values)),
            "threshold": float(threshold),
            "exceedance_count": None,
            "clopper_pearson_upper_95": None,
            "status": "evidence_missing",
        }
    k = sum(float(value) > float(threshold) for value in values)
    upper = literal_cp_upper(k, 64)
    return {
        "endpoint_id": endpoint_id,
        "applicable": True,
        "state_denominator": 64,
        "missing_state_count": 0,
        "threshold": float(threshold),
        "exceedance_count": k,
        "clopper_pearson_upper_95": upper,
        "status": (
            "pass"
            if k <= 2 and upper <= 0.10
            else "cross_mode_functional_drift"
        ),
    }


def literal_rank_error(
    left: Sequence[float],
    right: Sequence[float],
    left_mask: Sequence[bool],
    right_mask: Sequence[bool],
) -> dict[str, Any]:
    a = _finite_vector(left)
    b = _finite_vector(right)
    lm = np.asarray(left_mask)
    rm = np.asarray(right_mask)
    if a.shape != (8,) or b.shape != (8,) or lm.shape != (8,) or rm.shape != (8,):
        raise ValueError("rank shapes drifted")
    if lm.dtype != np.bool_ or rm.dtype != np.bool_:
        raise ValueError("rank masks must be bool")
    shared = [i for i in range(8) if bool(lm[i] and rm[i])]
    if len(shared) < 2:
        return {"status": "ambiguous_evidence_missing", "rank_error": None}
    av = [float(a[i]) for i in shared]
    bv = [float(b[i]) for i in shared]
    ar = _literal_average_ranks(av)
    br = _literal_average_ranks(bv)
    ac = len(set(ar)) == 1
    bc = len(set(br)) == 1
    if ac or bc:
        if ac and bc and av == bv:
            return {"status": "computed", "rank_error": 0.0}
        return {"status": "ambiguous_evidence_missing", "rank_error": None}
    rho = float(np.corrcoef(np.asarray(ar), np.asarray(br))[0, 1])
    return {"status": "computed", "rank_error": 1.0 - rho}


def literal_action_equivalent(
    left: Sequence[Sequence[float]],
    right: Sequence[Sequence[float]],
    left_executable: str,
    right_executable: str,
    left_terminal: str,
    right_terminal: str,
) -> dict[str, Any]:
    executable_enum = {"executable", "non_executable_retained"}
    terminal_enum = {"complete", "terminal_failure_retained"}
    if left_executable not in executable_enum or right_executable not in executable_enum:
        raise ValueError("executable enum drifted")
    if left_terminal not in terminal_enum or right_terminal not in terminal_enum:
        raise ValueError("terminal enum drifted")
    a = np.asarray(left, dtype=np.float64)
    b = np.asarray(right, dtype=np.float64)
    if a.shape != (80, 4) or b.shape != (80, 4):
        raise ValueError("action shape drifted")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("action nonfinite")
    pos = max(math.hypot(*(a[i, :2] - b[i, :2])) for i in range(80))
    heading = max(
        abs((float(a[i, 2] - b[i, 2]) + math.pi) % (2 * math.pi) - math.pi)
        for i in range(80)
    )
    speed = max(abs(float(a[i, 3] - b[i, 3])) for i in range(80))
    executable_equal = left_executable == right_executable
    terminal_equal = left_terminal == right_terminal
    passed = (
        pos <= 0.05
        and heading <= 0.01
        and speed <= 0.05
        and executable_equal
        and terminal_equal
    )
    return {
        "status": "pass" if passed else "cross_mode_functional_drift",
        "position_max_m": pos,
        "heading_max_rad": heading,
        "speed_max_mps": speed,
        "executable_equal": executable_equal,
        "terminal_equal": terminal_equal,
    }


def literal_clone_payload(source_record: Mapping[str, Any]) -> dict[str, Any]:
    spawn = _literal_pose(source_record["spawn_pose"])
    goal = _literal_pose(source_record["goal_pose"])
    route = _literal_resample(source_record["ordered_route_polyline_xy_m"])
    actors = _literal_actors(source_record["dynamic_actors_initial"])
    return {
        "schema_version": "camp_dp_v25_id_free_clone_key_payload_v1",
        "units": {
            "position": "integer_millimetres",
            "heading": "integer_1e-4_radians_wrapped_minus_pi_inclusive",
            "speed": "integer_millimetres_per_second",
            "dimensions": "integer_millimetres",
            "route_resample_spacing": "0.5_m_with_exact_final_endpoint",
        },
        "map_geometry_sha256": source_record["map_geometry_sha256"],
        "ordered_route_geometry_sha256": _sha(route),
        "spawn_pose_quantized": spawn,
        "goal_pose_quantized": goal,
        "route_polyline_resampled_0_5m_quantized": route,
        "dynamic_actor_initial_state_sorted": actors,
        "scenario_source_content_sha256": source_record[
            "scenario_source_content_sha256"
        ],
    }


def literal_b4_case_clone_payload(
    prepared: Mapping[str, Any],
) -> dict[str, Any]:
    if type(prepared) is not dict or set(prepared) != {
        "calibration_outcomes_consumed",
        "candidate_generation_executed",
        "case",
        "fresh_b2_opened",
        "identity_ordinal",
        "map_artifact",
        "mapped_signal_authority",
        "model_loaded",
        "outcome_fields_consumed",
        "route_polyline_world_m",
        "scenario_identity_sha256",
        "schema_version",
        "status",
        "training_executed",
    }:
        raise ValueError("B4 prepared top-level schema drifted")
    if (
        prepared["model_loaded"] is not False
        or prepared["candidate_generation_executed"] is not False
        or prepared["training_executed"] is not False
        or prepared["calibration_outcomes_consumed"] is not False
        or prepared["outcome_fields_consumed"] != []
    ):
        raise ValueError("B4 input-only boundary drifted")
    case = prepared["case"]
    if type(case) is not dict or case.get("split") != "fresh_b4":
        raise ValueError("B4 case role drifted")
    if (
        case.get("outcome_blind") is not True
        or case.get("holdout_outcome_consumed") is not False
        or case.get("outcome_fields_consumed") != []
    ):
        raise ValueError("B4 case outcome boundary drifted")
    route_spec = case.get("route_spec")
    if type(route_spec) is not dict or set(route_spec) != {
        "goal_pose",
        "lanelet_ids",
        "start_pose",
    }:
        raise ValueError("B4 route spec drifted")
    authority = case.get("mapped_signal_authority")
    if type(authority) is not dict:
        raise ValueError("B4 source authority missing")
    semantic = authority.get("semantic_clone_payload")
    semantic_sha = authority.get("semantic_clone_sha256")
    if type(semantic) is not dict or _sha(semantic) != semantic_sha:
        raise ValueError("B4 semantic clone SHA drifted")
    actors = []
    actor_keys = {
        "agent_type",
        "id",
        "initial_heading_rad",
        "initial_xy",
        "lateral_offset_m",
        "lateral_speed_mps",
        "lateral_target_m",
        "length_m",
        "longitudinal_acceleration_mps2",
        "longitudinal_speed_mps",
        "route_normal",
        "route_tangent",
        "trigger_time_s",
        "wheelbase_m",
        "width_m",
    }
    for actor in case.get("actors", []):
        if type(actor) is not dict or set(actor) != actor_keys:
            raise ValueError("B4 actor schema drifted")
        actors.append(
            {
                "class": actor["agent_type"],
                "length_m": actor["length_m"],
                "width_m": actor["width_m"],
                "x_m": actor["initial_xy"][0],
                "y_m": actor["initial_xy"][1],
                "heading_rad": actor["initial_heading_rad"],
                "speed_mps": math.hypot(
                    float(actor["longitudinal_speed_mps"]),
                    float(actor["lateral_speed_mps"]),
                ),
            }
        )
    start = route_spec["start_pose"]
    goal = route_spec["goal_pose"]
    source_record = {
        "map_geometry_sha256": case["source_map_sha256"],
        "scenario_source_content_sha256": semantic_sha,
        "spawn_pose": {
            "x_m": start[0],
            "y_m": start[1],
            "z_m": 0.0,
            "heading_rad": start[2],
        },
        "goal_pose": {
            "x_m": goal[0],
            "y_m": goal[1],
            "z_m": 0.0,
            "heading_rad": goal[2],
        },
        "ordered_route_polyline_xy_m": prepared["route_polyline_world_m"],
        "dynamic_actors_initial": actors,
    }
    return literal_clone_payload(source_record)


def review_contract_literal_v2(contract: Mapping[str, Any]) -> dict[str, Any]:
    if type(contract) is not dict or contract.get("schema_version") != EXPECTED_SCHEMA:
        raise ValueError("schema drifted")
    if contract.get("status") != (
        "frozen_executable_design_only_acquisition_unauthorized"
    ):
        raise ValueError("status drifted")
    scope = _obj(contract, "scope")
    if scope != {
        "generator": "new_single_invocation_batched_k8_candidate_pool",
        "coverage": (
            "single_route_single_map_bounded_development_nonholdout_"
            "four_density_tiers_only"
        ),
        "pass_interpretation": (
            "within_this_single_route_bounded_scope_current_evidence_does_"
            "not_trigger_retraining"
        ),
        "general_ood_or_architecture_equivalence_claim": False,
    }:
        raise ValueError("scope drifted")
    source = _obj(contract, "source_and_sampler_authority")
    if source != _expected_source_authority():
        raise ValueError("source/sampler/B4 manifest semantics drifted")
    specs = _obj(contract, "state_specifications")
    cal = _literal_specs("development_calibration")
    val = _literal_specs("independent_validation")
    if specs != _expected_state_specifications(cal, val):
        raise ValueError("state manifests/preflight topology drifted")
    repeat = _obj(contract, "repeat_authority")
    if repeat != _expected_repeat_authority():
        raise ValueError("repeat/runtime topology drifted")
    threshold = _obj(contract, "threshold_algorithm")
    if threshold != _expected_threshold_algorithm():
        raise ValueError("threshold algorithm drifted")
    if _obj(contract, "training_scale_authority") != (
        _expected_training_scale_authority()
    ):
        raise ValueError("training scale authority drifted")
    registry = _literal_registry()
    if contract.get("endpoint_registry") != registry:
        raise ValueError("endpoint registry semantics drifted")
    if contract.get("endpoint_registry_sha256") != _sha(registry):
        raise ValueError("endpoint registry SHA drifted")
    score = _obj(contract, "score_margin_rank")
    if score != _expected_score_margin_rank():
        raise ValueError("score/margin/rank semantics drifted")
    action = _obj(contract, "action_equivalence")
    if action != _expected_action_contract():
        raise ValueError("action semantics drifted")
    decision = _obj(contract, "decision_table")
    if decision != _expected_decision_table(registry):
        raise ValueError("decision table semantics drifted")
    boundary = _obj(contract, "run_and_claim_boundary")
    if boundary != _expected_run_boundary():
        raise ValueError("run/claim boundary drifted")
    payload = dict(contract)
    supplied = payload.pop("contract_payload_sha256", None)
    if supplied != _sha(payload):
        raise ValueError("payload SHA inconsistent")
    if supplied != EXPECTED_PAYLOAD_SHA256:
        raise ValueError("reviewer-local payload pin drifted")
    return {
        "status": "passed_independent_executable_semantic_review",
        "state_spec_count": 128,
        "endpoint_count": len(registry),
        "pure_functions_rebuilt": [
            "clone_payload",
            "q99_higher",
            "bootstrap_upper",
            "clopper_pearson_upper",
            "spearman_rank_error",
            "action_equivalence",
            "decision_topology",
        ],
        "acquisition_authorized": False,
    }


def _expected_source_authority() -> dict[str, Any]:
    return {
        "fixed_dp_head": (
            "7a1d33da277a1992ec474b5383a0c963c72e04e4"
        ),
        "sampler_module_path": (
            "camp_core/camp_core/integrations/"
            "diffusion_planner_v25_fair_pool_input_manifest.py"
        ),
        "sampler_module_sha256": EXPECTED_SAMPLER_SHA256,
        "sampler_entrypoint": "materialize_input_only_manifest",
        "b4_forbidden_entrypoint": (
            "materialize_b4_forbidden_clone_manifest"
        ),
        "preflight_entrypoint": "validate_preflight_receipt",
        "input_only_manifest_schema": (
            "camp_dp_v25_fair_pool_input_only_manifest_v1"
        ),
        "preflight_receipt_schema": (
            "camp_dp_v25_fair_pool_input_only_preflight_receipt_v1"
        ),
        "source_record_schema": {
            "exact_fields": [
                "source_state_ordinal",
                "map_geometry_sha256",
                "route_asset_sha256",
                "scenario_source_content_sha256",
                "spawn_pose",
                "goal_pose",
                "ordered_route_polyline_xy_m",
                "dynamic_actors_initial",
                "actual_input_sha256",
                "actual_state_sha256",
                "actual_latent_tensor_sha256",
            ],
            "spawn_goal_pose_fields_and_units": {
                "x_m": "metres_float64_finite",
                "y_m": "metres_float64_finite",
                "z_m": "metres_float64_finite",
                "heading_rad": "radians_float64_finite",
            },
            "ordered_route_polyline": (
                "source_route_order_xy_metres_float64_min_two_points"
            ),
            "dynamic_actor_exact_fields_and_units": {
                "class": "nonempty_utf8_string",
                "length_m": "metres_positive_float64",
                "width_m": "metres_positive_float64",
                "x_m": "metres_float64_finite",
                "y_m": "metres_float64_finite",
                "heading_rad": "radians_float64_finite",
                "speed_mps": "metres_per_second_float64_finite",
            },
            "missing_rules": (
                "actors_may_be_exact_empty_list;all_other_fields_required;"
                "unknown_fields_or_nonfinite_values_block"
            ),
        },
        "future_input_only_materialization_algorithm": {
            "authorization": "not_authorized_in_this_design_stage",
            "state_order": (
                "ascending_source_state_ordinal_0_through_127_exactly;"
                "calibration_0_63_validation_64_127"
            ),
            "input_authority": (
                "exact_route_and_map_assets_below_plus_state_spec_"
                "scenario_seed_and_four_density_tier"
            ),
            "steps": [
                "verify_fixed_dp_map_route_and_sampler_fingerprints",
                "load_ordered_route_geometry_without_model_or_selector",
                (
                    "materialize_exact_input_only_native_scene_for_"
                    "source_state_ordinal_and_scenario_seed"
                ),
                (
                    "serialize_source_record_exact_schema_and_compute_"
                    "actual_input_state_latent_sha256"
                ),
                (
                    "call_materialize_input_only_manifest_and_reject_"
                    "drop_replacement_or_unknown_field"
                ),
                (
                    "materialize_exact_b4_forbidden_manifest_from_"
                    "sealed_preopen_prepared_runtime_cases_bytes"
                ),
                (
                    "validate_64_plus_64_plus_b4_zero_overlap_receipt_"
                    "before_first_model_pool_selector_call"
                ),
            ],
            "no_drop_replacement_or_suffix": True,
        },
        "route_asset": {
            "path": (
                "/root/autodl-tmp/"
                "camp_dp_v24_fixed_dp_single_record_source_probe_"
                "preflight_retry_a53d6ee3_20260715T204719CST/"
                "prepared/probe_route.pkl"
            ),
            "sha256": EXPECTED_ROUTE_SHA256,
        },
        "map_asset": {
            "path": (
                "/root/autodl-tmp/"
                "camp_dp_v23_source_license_freeze_retry2_51c97eb2_"
                "20260715T172832CST/payload/sources/scenario_simulator_v2/"
                "simulation/traffic_simulator/test/map/four_track_highway/"
                "lanelet2_map.osm"
            ),
            "sha256": EXPECTED_MAP_SHA256,
        },
        "b4_input_only_forbidden_manifest": {
            "artifact_path": (
                "/root/autodl-tmp/"
                "camp_dp_v25_fresh_b4_preopen_authority_7be93df2_"
                "20260724TconsumerFinalCST"
            ),
            "artifact_root_sha256": (
                "bfb6727983cbb43a3612ea00d274b249277ed4abfa4f63219c5aaba4420b2829"
            ),
            "identity_source": {
                "file_relative_path": "fresh_b4_execution_plan.json",
                "file_sha256": (
                    "41442dd7d71552972d737d9a9e3d56e9827f864e0c06e11c57487f651206dee0"
                ),
                "identity_json_pointer": "/identities",
                "identity_subpayload_sha256": (
                    "12cc3cc788f2a50bcd761191cb63ff24bf320af0b81c2051ce4efac3e9b81e9e"
                ),
            },
            "prepared_input_source": {
                "file_relative_path": "fresh_b4_prepared_runtime_cases.json",
                "file_sha256": (
                    "e67fee3309f822c80605b3e9b00009d2ae3e27139e36396d009b9a2b306535a2"
                ),
                "case_count": 100,
                "model_loaded": False,
                "candidate_generation_executed": False,
                "outcome_fields_consumed": [],
            },
            "derived_schema": (
                "camp_dp_v25_fresh_b4_input_only_forbidden_clone_manifest_v1"
            ),
            "extractor": "materialize_b4_forbidden_clone_manifest",
            "required_derived_clone_key_count": 100,
            "derived_manifest_sha256": (
                "formed_and_bound_in_future_preflight_receipt_before_"
                "any_model_pool_selector_call"
            ),
            "outcome_fields_read": [],
        },
        "clone_materialization": {
            "canonical_bytes": (
                "json_sort_keys_ascii_compact_allow_nan_false_single_lf"
            ),
            "position_and_dimension_quantization": (
                "decimal_from_shortest_roundtrip_string_divide_0.001_"
                "round_half_away_from_zero_to_integer"
            ),
            "heading_wrap": (
                "((theta+pi) mod 2pi)-pi_with_plus_pi_to_minus_pi"
            ),
            "heading_quantization": (
                "decimal_from_wrapped_shortest_roundtrip_string_divide_"
                "0.0001_round_half_away_from_zero_to_integer"
            ),
            "speed_quantization": "0.001_mps_round_half_away_from_zero",
            "route_resample": (
                "ordered_piecewise_linear_arc_length_samples_j_times_0.5m_"
                "including_s0_and_exact_final_endpoint_no_padding;"
                "reject_segment_length_le_1e-12m"
            ),
            "actor_missing_rule": (
                "no_actors_is_empty_list;missing_actor_field_blocks"
            ),
            "actor_sort": (
                "class_utf8_bytes,length_mm,width_mm,x_mm,y_mm,"
                "heading_1e4rad,speed_mmps"
            ),
            "clone_payload_fields": [
                "map_geometry_sha256",
                "ordered_route_geometry_sha256",
                "spawn_pose_quantized",
                "goal_pose_quantized",
                "route_polyline_resampled_0_5m_quantized",
                "dynamic_actor_initial_state_sorted",
                "scenario_source_content_sha256",
            ],
            "id_fields_forbidden": [
                "state_id",
                "scenario_id",
                "route_id",
                "database_row_id",
            ],
        },
    }


def _expected_state_specifications(
    calibration: list[dict[str, Any]],
    validation: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "development_calibration": calibration,
        "independent_validation": validation,
        "development_calibration_sha256": _sha(calibration),
        "independent_validation_sha256": _sha(validation),
        "state_count_per_split": 64,
        "independent_statistical_unit": "state",
        "rows_ticks_role": "within_state_observations_only",
        "materialization_before_any_model_pool_selector_call": True,
        "required_empty_intersections": [
            "within_development_calibration",
            "within_independent_validation",
            "development_calibration_vs_independent_validation",
            "both_splits_vs_b4_input_only_forbidden_clone_keys",
        ],
        "conflict_policy": "abort_no_drop_no_replacement_no_suffix",
        "actual_manifest_count_now": 0,
        "actual_clone_key_count_now": 0,
        "required_preflight_receipt_exact_fields": [
            "schema_version",
            "contract_root_sha256",
            "b4_forbidden_manifest_authority",
            "calibration_manifests",
            "validation_manifests",
            "model_pool_selector_call_count_before_receipt",
            "within_calibration_overlap_count",
            "within_validation_overlap_count",
            "cross_split_overlap_count",
            "b4_overlap_count",
            "status",
        ],
        "b4_forbidden_manifest_authority_receipt_fields": [
            "preopen_path",
            "preopen_root_sha256",
            "prepared_runtime_cases_sha256",
            "forbidden_manifest_sha256",
            "forbidden_clone_key_count",
        ],
    }


def _expected_repeat_authority() -> dict[str, Any]:
    return {
        "acquisition_authorized": False,
        "repeat_count_per_state_per_mode": 5,
        "modes": ["sequential_batch1_x8", "single_invocation_batch8"],
        "within_mode_pairs": [
            [0, 1],
            [0, 2],
            [0, 3],
            [0, 4],
            [1, 2],
            [1, 3],
            [1, 4],
            [2, 3],
            [2, 4],
            [3, 4],
        ],
        "cross_mode_pairs": [[i, i] for i in range(5)],
        "cross_mode_entry": (
            "all_required_within_mode_endpoints_pass_for_both_modes"
        ),
        "runtime": {
            "gpu_name": "NVIDIA GeForce RTX 5090",
            "gpu_uuid": "GPU-c82677a4-21d3-a44c-5195-e41c150e086c",
            "driver": "595.71.05",
            "python": "3.12",
            "numpy": "1.26.4",
            "scipy": "1.14.1",
            "torch": "2.8.0+cu128",
            "cuda": "12.8",
            "cudnn": 91002,
            "dtype": "float32",
            "deterministic_algorithms": True,
            "tf32": False,
            "cudnn_benchmark": False,
            "global_rng_unchanged": True,
        },
    }


def _expected_training_scale_authority() -> dict[str, Any]:
    scales = (
        1315.8699005569194,
        5202.799211059529,
        6271.815530966072,
        1.8198095597643642,
        93.9868956456402,
        118.0999680225589,
        147.7588020436164,
        2902.5946193744476,
        56.41673006314134,
        8.752781754669478,
        40.5,
        1.0534432082550127,
        28.22741708820042,
        2.608169233773669,
    )
    return {
        "artifact_root_sha256": (
            "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
        ),
        "relative_path": "runtime_atom_scales.json",
        "file_sha256": (
            "72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb"
        ),
        "names_json_pointer": "/atom_names",
        "scales_json_pointer": "/scales",
        "index": [
            {"index": index, "name": name, "scale": scale}
            for index, (name, scale) in enumerate(zip(EXPECTED_NAMES, scales))
        ],
        "zero_or_nonfinite": "authority_failure",
    }


def _expected_run_boundary() -> dict[str, Any]:
    return {
        "acquisition_authorized": False,
        "actual_input_manifest_materialization_count": 0,
        "calibration_run_count": 0,
        "repeat_model_run_count": 0,
        "pool_run_count": 0,
        "selector_run_count": 0,
        "closed_loop_run_count": 0,
        "fresh_run_count": 0,
        "holdout_run_count": 0,
        "training_run_count": 0,
        "claim_authorized": False,
        "promotion_deployment_authorized": False,
    }


def _literal_registry() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, name in enumerate(EXPECTED_NAMES):
        result.append(
            _literal_endpoint(
                f"atom.normalized_delta.{index:02d}.{name}",
                "numeric_threshold",
                "[8,14]_float64_pair",
                f"max_row_abs((a[:,{index}]-b[:,{index}])/scale[{index}])",
                "all_8_candidate_rows_present_and_finite",
            )
        )
    values = (
        ("trajectory.ego.position_max_m", "[8,80,2]_float64_pair", "max_row_t_l2_xy"),
        (
            "trajectory.ego.heading_max_rad",
            "[8,80]_float64_pair",
            "max_row_t_abs_wrap_to_pi_delta",
        ),
        ("trajectory.ego.speed_max_mps", "[8,80]_float64_pair", "max_row_t_abs_delta"),
        (
            "trajectory.neighbor.position_max_m",
            "[8,A,80,2]_float64_pair",
            "max_row_actor_t_l2_xy_after_exact_actor_slot_fingerprint",
        ),
        (
            "trajectory.neighbor.heading_max_rad",
            "[8,A,80]_float64_pair",
            "max_row_actor_t_abs_wrap_to_pi_delta",
        ),
        (
            "trajectory.neighbor.speed_max_mps",
            "[8,A,80]_float64_pair",
            "max_row_actor_t_abs_delta",
        ),
    )
    for endpoint_id, shape, formula in values:
        result.append(
            _literal_endpoint(
                endpoint_id,
                "numeric_threshold",
                shape,
                formula,
                "exact_shape_actor_roster_and_all_values_finite",
            )
        )
    for arm in ("static14d", "scene14d"):
        result += [
            _literal_endpoint(
                f"score.{arm}.abs_delta",
                "numeric_threshold",
                "[8]_float64_pair",
                "max_shared_eligible_abs_score_delta",
                "masks_equal_and_at_least_1_eligible_and_finite",
            ),
            _literal_endpoint(
                f"score.{arm}.within_mode_normalized_delta",
                "numeric_threshold",
                "[8]_float64_pair_plus_mode_thresholds",
                (
                    "cross_abs_delta/max(seq_within_threshold,"
                    "batch8_within_threshold,1e-9)"
                ),
                "both_mode_thresholds_finite_positive",
            ),
            _literal_endpoint(
                f"score.{arm}.margin_ratio",
                "numeric_threshold",
                "[8]_float64_pair_plus_equal_masks",
                (
                    "abs((runner_up-best)_a-(runner_up-best)_b)/"
                    "max(abs(margin_a),abs(margin_b),1e-9)"
                ),
                "at_least_2_shared_eligible_else_ambiguous_evidence_missing",
            ),
            _literal_endpoint(
                f"score.{arm}.rank_error",
                "numeric_threshold",
                "[8]_float64_pair_plus_equal_masks",
                "1-spearman_average_tie_ranks",
                (
                    "at_least_2_shared_eligible;both_constant_equal_is_zero;"
                    "one_constant_or_unequal_constants_is_ambiguous_evidence_missing"
                ),
            ),
            _literal_endpoint(
                f"functional.{arm}.mask_eligibility",
                "hard_exact",
                "[8]_bool_pair",
                "array_equal",
                "exact_shape",
            ),
            _literal_endpoint(
                f"functional.{arm}.selected_index_action",
                "action_gate",
                "[80,4]_float64_pair_plus_status_enums",
                (
                    "same_index_pass_else_action_equivalence_all_of_"
                    "xy_heading_speed_executable_terminal"
                ),
                "selected_rows_present_finite_and_status_enums_valid",
            ),
        ]
    result += [
        _literal_endpoint(
            "neighbor.relative_within_mode_inflation",
            "numeric_threshold",
            "three_state_q99_float64",
            (
                "cross_q99/max(seq_q99,batch8_q99,"
                "neighbor_resolution_floor)"
            ),
            "all_three_finite_nonnegative",
        ),
        _literal_endpoint(
            "k8.finite_and_diverse",
            "hard_exact",
            "[8,80,4]_float32_each_mode_repeat",
            "all_finite_and_unique_row_sha256_count_eq_8",
            "every_state_mode_repeat",
        ),
        _literal_endpoint(
            "authority.fingerprint",
            "hard_exact",
            "typed_authority_receipt",
            "all_literal_fingerprints_equal_contract",
            "all_fields_present",
        ),
        _literal_endpoint(
            "pool.tensor_immutability_and_zero_calls",
            "hard_exact",
            "pre_post_sha_and_call_counters",
            "tensor_sha_equal_and_all_post_pool_call_counts_eq_0",
            "every_selector_receipt",
        ),
        _literal_endpoint(
            "split.input_only_clone_nonoverlap",
            "hard_exact",
            "128_input_only_manifests_plus_b4_clone_keys",
            "within_calibration_cross_split_and_b4_intersections_all_empty",
            "receipt_formed_before_any_model_pool_selector_call",
        ),
    ]
    return result


def _literal_endpoint(
    endpoint_id: str, kind: str, shape: str, formula: str, applicability: str
) -> dict[str, Any]:
    if "position" in endpoint_id:
        units = "m"
    elif "heading" in endpoint_id:
        units = "rad"
    elif "speed" in endpoint_id:
        units = "m/s"
    elif endpoint_id.startswith("atom."):
        units = "training_scale_normalized"
    else:
        units = "dimensionless"
    numeric = kind == "numeric_threshold"
    return {
        "id": endpoint_id,
        "kind": kind,
        "input_shape": shape,
        "formula": formula,
        "units": units,
        "applicability": applicability,
        "finite_policy": (
            "nonfinite_is_authority_failure"
            if kind == "hard_exact"
            else "nonfinite_is_evidence_missing"
        ),
        "missing_policy": "BLOCK_evidence_missing",
        "within_mode_required": True,
        "cross_mode_required": True,
        "per_state_first": True,
        "threshold_source": (
            "hard_literal"
            if kind in {"hard_exact", "action_gate"}
            else "calibration_q99_bootstrap_upper"
        ),
        "resolution_floor": (
            _literal_resolution_floor(endpoint_id) if numeric else None
        ),
        "modes": ["sequential_batch1_x8", "single_invocation_batch8"],
        "within_mode_pair_topology": (
            "all_10_unordered_pairs_repeat_indices_0_1_2_3_4"
        ),
        "cross_mode_pair_topology": (
            "matched_repeat_indices_0_to_0_through_4_to_4"
        ),
        "state_error_reduction": (
            "q99_higher_of_applicable_pair_errors"
            if numeric
            else "exact_boolean_all_receipts"
        ),
        "calibration_and_validation_denominator": (
            "64_states_each_no_complete_case_drop"
        ),
    }


def _literal_resolution_floor(endpoint_id: str) -> float:
    if endpoint_id.startswith("atom."):
        return 1e-8
    if "position_max_m" in endpoint_id:
        return 1e-4
    if "heading_max_rad" in endpoint_id:
        return 1e-5
    if "speed_max_mps" in endpoint_id:
        return 1e-4
    if endpoint_id.startswith("score."):
        return 1e-9
    if endpoint_id == "neighbor.relative_within_mode_inflation":
        return 1e-9
    raise ValueError("unknown numeric endpoint resolution floor")


def _expected_decision_table(
    registry: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "required_endpoint_ids": [item["id"] for item in registry],
        "required_endpoint_count": len(registry),
        "endpoint_result_exact_fields": [
            "endpoint_id",
            "applicable",
            "state_denominator",
            "missing_state_count",
            "threshold",
            "exceedance_count",
            "clopper_pearson_upper_95",
            "status",
        ],
        "numeric_endpoint_pass": (
            "applicable_true AND state_denominator_eq_64 AND "
            "missing_state_count_eq_0 AND threshold_finite AND "
            "every_state_error_finite AND exceedance_count_le_2 AND "
            "clopper_pearson_upper_95_le_0.10"
        ),
        "hard_endpoint_pass": (
            "all_required_receipts_present AND literal_hard_condition_true"
        ),
        "action_endpoint_pass": (
            "selected_index_same OR "
            "(selected_index_flip AND action_equivalence_status_pass);"
            "missing_nonfinite_or_status_drift_blocks"
        ),
        "within_mode_pass_boolean": (
            "for_each_mode_exact_required_within_endpoint_keyset_and_"
            "every_applicable_endpoint_status_pass"
        ),
        "cross_mode_entry_boolean": (
            "sequential_batch1_x8_within_pass AND "
            "single_invocation_batch8_within_pass"
        ),
        "cross_mode_pass_boolean": (
            "cross_mode_entry_true AND exact_required_endpoint_keyset_"
            "AND_every_endpoint_status_pass"
        ),
        "accepted_endpoint_status": ["pass"],
        "missing_statuses": [
            "evidence_missing",
            "ambiguous_evidence_missing",
        ],
        "hard_fail_ids": [
            "functional.static14d.mask_eligibility",
            "functional.scene14d.mask_eligibility",
            "k8.finite_and_diverse",
            "authority.fingerprint",
            "pool.tensor_immutability_and_zero_calls",
            "split.input_only_clone_nonoverlap",
        ],
        "pass_boolean": (
            "exact_required_endpoint_keyset AND every_status_pass AND "
            "both_within_modes_pass_before_cross_mode"
        ),
        "block_precedence": [
            "authority_failure",
            "evidence_missing",
            "within_mode_generator_instability",
            "cross_mode_functional_drift",
        ],
        "weighted_total": False,
        "benefit_claim": False,
        "general_ood_equivalence_claim": False,
        "fail_does_not_equal_retraining_required": True,
    }


def _expected_threshold_algorithm() -> dict[str, Any]:
    return {
        "within_state": (
            "endpoint_error_for_each_predeclared_pair_then_q99_higher"
        ),
        "across_calibration_states": "q99_higher_of_exactly_64_state_values",
        "quantile_formula": "sorted_values[ceil(q*(n-1))]",
        "q": 0.99,
        "bootstrap": {
            "sample_size": 64,
            "with_replacement": True,
            "resamples": 10000,
            "rng": "numpy.random.Generator(PCG64DXSM(825071))",
            "index_generation": (
                "integers(0,64,size=(10000,64),endpoint=False,dtype=int64)"
            ),
            "per_resample_statistic": (
                "q99_higher_index_ceil_0.99_times_63_eq_63"
            ),
            "upper_confidence_quantile": 0.95,
            "upper_index": 9500,
            "final": (
                "max(endpoint_resolution_floor,sorted_bootstrap[9500])"
            ),
        },
        "validation": {
            "pass_equality": "error <= threshold",
            "exceedance": "error > threshold",
            "n": 64,
            "max_k": 2,
            "max_rate": 0.05,
            "cp_confidence": 0.95,
            "cp_upper": {
                "k_eq_0": "1-(1-0.95)**(1/n)",
                "zero_lt_k_lt_n": "scipy.stats.beta.ppf(0.95,k+1,n-k)",
                "k_eq_n": "1.0",
                "pass": "cp_upper <= 0.10",
            },
        },
        "numeric_policy": (
            "all_inputs_and_intermediates_finite;nonfinite_is_evidence_"
            "missing_except_authority_and_hard_gate_nonfinite_is_authority_failure"
        ),
        "observed_prior_values_forbidden": [
            1.2076,
            "114/128",
            "9/16",
            "0_selection_flips",
        ],
    }


def _expected_score_margin_rank() -> dict[str, Any]:
    return {
        "best_direction": "lower",
        "eligible": "mask_true_rows_only",
        "within_score_threshold_ownership": {
            "static14d.sequential_batch1_x8": (
                "calibrated_from_score.static14d.abs_delta_within_"
                "sequential_batch1_x8_only"
            ),
            "static14d.single_invocation_batch8": (
                "calibrated_from_score.static14d.abs_delta_within_"
                "single_invocation_batch8_only"
            ),
            "scene14d.sequential_batch1_x8": (
                "calibrated_from_score.scene14d.abs_delta_within_"
                "sequential_batch1_x8_only"
            ),
            "scene14d.single_invocation_batch8": (
                "calibrated_from_score.scene14d.abs_delta_within_"
                "single_invocation_batch8_only"
            ),
        },
        "margin": "runner_up_score_minus_best_score",
        "margin_ratio_denominator": (
            "max(abs(margin_a),abs(margin_b),1e-9)"
        ),
        "within_mode_normalized_score_denominator": (
            "max(same_arm_sequential_within_threshold,"
            "same_arm_batch8_within_threshold,1e-9)"
        ),
        "relative_inflation_denominator": (
            "max(sequential_state_q99,batch8_state_q99,"
            "endpoint_resolution_floor)"
        ),
        "zero_denominator": "prevented_by_positive_literal_floor",
        "nan_or_inf": "BLOCK_evidence_missing",
        "fewer_than_two_shared_eligible": "ambiguous_evidence_missing",
        "exact_tie": "float64_exact_equality",
        "tie_break": "smallest_eligible_row_index",
        "near_tie_threshold_per_arm": (
            "2*max(static_or_scene_same_arm_seq_within_score_threshold,"
            "same_arm_batch8_within_score_threshold,1e-9)"
        ),
        "near_tie_equality": "margin <= near_tie_threshold",
        "spearman": {
            "shared_eligible_minimum": 2,
            "tie_rank": "average_1_based_rank_of_exactly_equal_float64_values",
            "both_constant_and_elementwise_equal": "rank_error_0",
            "one_constant_or_unequal_constant_vectors": (
                "ambiguous_evidence_missing"
            ),
            "otherwise": "rank_error=1-pearson_corr(average_ranks)",
        },
    }


def _expected_action_contract() -> dict[str, Any]:
    return {
        "shape": [80, 4],
        "field_order": ["x_m", "y_m", "heading_rad", "speed_mps"],
        "dt_s": 0.1,
        "time_alignment": "exact_index_no_interpolation",
        "all_values_finite": True,
        "heading_wrap": "((delta+pi) mod 2pi)-pi",
        "position_max_m_pass": "<=0.05",
        "heading_max_rad_pass": "<=0.01",
        "speed_max_mps_pass": "<=0.05",
        "executable_enum": ["executable", "non_executable_retained"],
        "terminal_enum": ["complete", "terminal_failure_retained"],
        "status_equality_required": True,
        "selected_index_same": "pass_if_all_other_hard_gates_pass",
        "selected_index_flip_and_action_equivalent": (
            "pass_with_descriptive_action_equivalent_flip"
        ),
        "selected_index_flip_and_action_not_equivalent": (
            "BLOCK_cross_mode_functional_drift"
        ),
        "missing_or_nonfinite": "BLOCK_evidence_missing",
    }


def _literal_specs(split: str) -> list[dict[str, Any]]:
    base = 0 if split == "development_calibration" else 64
    scenario = 41000 if split == "development_calibration" else 51000
    latent = 61000 if split == "development_calibration" else 71000
    tiers = ("no_npc", "low_density", "medium_density", "high_density")
    result = []
    for index in range(64):
        item = {
            "split": split,
            "state_spec_id": f"{split}:{index:03d}",
            "state_index": index,
            "source_state_ordinal": base + index,
            "source_role": "development_nonholdout",
            "source_sampler_module_sha256": EXPECTED_SAMPLER_SHA256,
            "route_asset_sha256": EXPECTED_ROUTE_SHA256,
            "map_geometry_sha256": EXPECTED_MAP_SHA256,
            "family": "four_track_highway",
            "tier": tiers[index % 4],
            "scenario_seed": scenario + index,
            "latent_seed": latent + index,
            "latent_policy": "row0_zero_rows1_7_philox_normal_float32_v1",
            "candidate_k": 8,
            "independent_statistical_unit": "state",
        }
        item["state_spec_sha256"] = _sha(item)
        result.append(item)
    return result


def _literal_average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2.0
        for index in order[start:end]:
            ranks[index] = rank
        start = end
    return ranks


def _literal_quantize(value: float, quantum: str) -> int:
    if not math.isfinite(float(value)):
        raise ValueError("nonfinite quantization")
    return int(
        (Decimal(str(float(value))) / Decimal(quantum)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def _literal_wrap(value: float) -> float:
    wrapped = (float(value) + math.pi) % (2 * math.pi) - math.pi
    return -math.pi if wrapped == math.pi else wrapped


def _literal_pose(value: Mapping[str, float]) -> dict[str, int]:
    if set(value) != {"x_m", "y_m", "z_m", "heading_rad"}:
        raise ValueError("pose fields drifted")
    return {
        "x_mm": _literal_quantize(value["x_m"], "0.001"),
        "y_mm": _literal_quantize(value["y_m"], "0.001"),
        "z_mm": _literal_quantize(value["z_m"], "0.001"),
        "heading_1e4rad": _literal_quantize(
            _literal_wrap(value["heading_rad"]), "0.0001"
        ),
    }


def _literal_resample(points: Sequence[Sequence[float]]) -> list[list[int]]:
    if len(points) < 2:
        raise ValueError("route too short")
    xy = [(float(p[0]), float(p[1])) for p in points]
    lengths = []
    cumulative = [0.0]
    for a, b in zip(xy, xy[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if not math.isfinite(length) or length <= 1e-12:
            raise ValueError("invalid route segment")
        lengths.append(length)
        cumulative.append(cumulative[-1] + length)
    total = cumulative[-1]
    samples = [0.5 * i for i in range(math.floor(total / 0.5) + 1)]
    if total - samples[-1] > 1e-12:
        samples.append(total)
    else:
        samples[-1] = total
    output = []
    segment = 0
    for distance in samples:
        while segment + 1 < len(cumulative) and distance > cumulative[segment + 1] + 1e-12:
            segment += 1
        ratio = (distance - cumulative[segment]) / lengths[segment]
        x = xy[segment][0] + ratio * (xy[segment + 1][0] - xy[segment][0])
        y = xy[segment][1] + ratio * (xy[segment + 1][1] - xy[segment][1])
        output.append([_literal_quantize(x, "0.001"), _literal_quantize(y, "0.001")])
    return output


def _literal_actors(actors: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for actor in actors:
        result.append(
            {
                "class": actor["class"],
                "length_mm": _literal_quantize(actor["length_m"], "0.001"),
                "width_mm": _literal_quantize(actor["width_m"], "0.001"),
                "x_mm": _literal_quantize(actor["x_m"], "0.001"),
                "y_mm": _literal_quantize(actor["y_m"], "0.001"),
                "heading_1e4rad": _literal_quantize(
                    _literal_wrap(actor["heading_rad"]), "0.0001"
                ),
                "speed_mmps": _literal_quantize(actor["speed_mps"], "0.001"),
            }
        )
    return sorted(
        result,
        key=lambda x: (
            x["class"].encode(),
            x["length_mm"],
            x["width_mm"],
            x["x_mm"],
            x["y_mm"],
            x["heading_1e4rad"],
            x["speed_mmps"],
        ),
    )


def _finite_vector(values: Sequence[float]) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or len(array) == 0 or not np.isfinite(array).all():
        raise ValueError("finite vector required")
    return array


def _obj(parent: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if type(value) is not dict:
        raise ValueError(f"{key} must be object")
    return value
