"""Executable, outcome-independent V25 fair-pool adaptation contract v2."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import beta


SCHEMA_VERSION = "camp_dp_v25_fair_pool_adaptation_contract_v2"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SAMPLER_MODULE_PATH = (
    "camp_core/camp_core/integrations/"
    "diffusion_planner_v25_fair_pool_input_manifest.py"
)
SAMPLER_MODULE_SHA256 = (
    "33f5ea5eb6d92757fbb408e318eccd04048265a295871c9862f1ca539a98bfb6"
)
ROUTE_ASSET_SHA256 = (
    "63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd"
)
MAP_SHA256 = "c13a9234727186c77c019766c3358c30faf10af61503a566f0fff0963be53bbd"
TRAINING_ROOT = "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
TRAINING_SCALE_SHA256 = (
    "72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb"
)
V1_CONTRACT_ROOT = "b2de5b71509526407e102b3ba3aec74000290f13ab75918d0008596a6b52f824"
V1_REVIEW_ROOT = "a16a523766493826d6b5b3f4e0a8188a1019571e4491a53e3149af2bb408aa37"
B4_PREOPEN_PATH = (
    "/root/autodl-tmp/"
    "camp_dp_v25_fresh_b4_preopen_authority_7be93df2_20260724TconsumerFinalCST"
)
B4_PREOPEN_ROOT = "bfb6727983cbb43a3612ea00d274b249277ed4abfa4f63219c5aaba4420b2829"
B4_PLAN_SHA256 = "41442dd7d71552972d737d9a9e3d56e9827f864e0c06e11c57487f651206dee0"
B4_IDENTITY_SUBPAYLOAD_SHA256 = (
    "12cc3cc788f2a50bcd761191cb63ff24bf320af0b81c2051ce4efac3e9b81e9e"
)
B4_PREPARED_RUNTIME_CASES_SHA256 = (
    "e67fee3309f822c80605b3e9b00009d2ae3e27139e36396d009b9a2b306535a2"
)

ATOM_NAMES = (
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
ATOM_SCALES = (
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


def canonical_bytes(value: Any) -> bytes:
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


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def empirical_quantile_higher(values: Sequence[float], q: float) -> float:
    array = _finite_vector(values, "quantile values")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be in [0,1]")
    ordered = np.sort(array, kind="mergesort")
    index = int(math.ceil(q * (len(ordered) - 1)))
    return float(ordered[index])


def bootstrap_upper_threshold(
    state_statistics: Sequence[float],
    *,
    resolution_floor: float,
    state_quantile: float = 0.99,
    confidence_quantile: float = 0.95,
    resamples: int = 10000,
    seed: int = 825071,
) -> float:
    values = _finite_vector(state_statistics, "state statistics")
    if len(values) != 64:
        raise ValueError("calibration requires exactly 64 state statistics")
    if (
        type(resamples) is not int
        or resamples != 10000
        or type(seed) is not int
        or seed != 825071
    ):
        raise ValueError("bootstrap topology drifted")
    floor = _positive(resolution_floor, "resolution floor")
    generator = np.random.Generator(np.random.PCG64DXSM(seed))
    indices = generator.integers(
        0, 64, size=(resamples, 64), endpoint=False, dtype=np.int64
    )
    resampled = values[indices]
    state_index = int(math.ceil(state_quantile * 63))
    bootstrap_statistics = np.sort(resampled, axis=1, kind="mergesort")[
        :, state_index
    ]
    upper_index = int(
        math.ceil(confidence_quantile * (resamples - 1))
    )
    upper = float(
        np.sort(bootstrap_statistics, kind="mergesort")[upper_index]
    )
    return max(floor, upper)


def clopper_pearson_upper(k: int, n: int, confidence: float = 0.95) -> float:
    if (
        type(k) is not int
        or type(n) is not int
        or n <= 0
        or k < 0
        or k > n
    ):
        raise ValueError("invalid binomial counts")
    if confidence != 0.95:
        raise ValueError("confidence must be exactly 0.95")
    alpha = 1.0 - confidence
    if k == 0:
        return 1.0 - alpha ** (1.0 / n)
    if k == n:
        return 1.0
    return float(beta.ppf(1.0 - alpha, k + 1, n - k))


def spearman_rank_error(
    left_scores: Sequence[float],
    right_scores: Sequence[float],
    left_mask: Sequence[bool],
    right_mask: Sequence[bool],
) -> dict[str, Any]:
    left = _finite_vector(left_scores, "left scores")
    right = _finite_vector(right_scores, "right scores")
    if left.shape != (8,) or right.shape != (8,):
        raise ValueError("score vectors must have shape [8]")
    lmask = _bool_vector(left_mask, "left mask")
    rmask = _bool_vector(right_mask, "right mask")
    if lmask.shape != (8,) or rmask.shape != (8,):
        raise ValueError("mask vectors must have shape [8]")
    shared = np.flatnonzero(lmask & rmask)
    if len(shared) < 2:
        return {"status": "ambiguous_evidence_missing", "rank_error": None}
    lvalues = left[shared]
    rvalues = right[shared]
    lranks = _average_ranks(lvalues)
    rranks = _average_ranks(rvalues)
    lconstant = bool(np.all(lranks == lranks[0]))
    rconstant = bool(np.all(rranks == rranks[0]))
    if lconstant or rconstant:
        if lconstant and rconstant and np.array_equal(lvalues, rvalues):
            return {"status": "computed", "rank_error": 0.0}
        return {"status": "ambiguous_evidence_missing", "rank_error": None}
    rho = float(np.corrcoef(lranks, rranks)[0, 1])
    if not math.isfinite(rho):
        return {"status": "ambiguous_evidence_missing", "rank_error": None}
    return {"status": "computed", "rank_error": 1.0 - rho}


def action_equivalent(
    left: Sequence[Sequence[float]],
    right: Sequence[Sequence[float]],
    *,
    left_executable: str,
    right_executable: str,
    left_terminal: str,
    right_terminal: str,
) -> dict[str, Any]:
    allowed_executable = {"executable", "non_executable_retained"}
    allowed_terminal = {"complete", "terminal_failure_retained"}
    if left_executable not in allowed_executable or right_executable not in allowed_executable:
        raise ValueError("executable status enum drifted")
    if left_terminal not in allowed_terminal or right_terminal not in allowed_terminal:
        raise ValueError("terminal status enum drifted")
    left_array = np.asarray(left, dtype=np.float64)
    right_array = np.asarray(right, dtype=np.float64)
    if left_array.shape != (80, 4) or right_array.shape != (80, 4):
        raise ValueError("actions must be [80,4]=[x_m,y_m,heading_rad,speed_mps]")
    if not np.isfinite(left_array).all() or not np.isfinite(right_array).all():
        raise ValueError("action values must be finite")
    position = np.linalg.norm(left_array[:, :2] - right_array[:, :2], axis=1)
    heading = np.abs(
        (left_array[:, 2] - right_array[:, 2] + np.pi) % (2 * np.pi) - np.pi
    )
    speed = np.abs(left_array[:, 3] - right_array[:, 3])
    errors = {
        "position_max_m": float(np.max(position)),
        "heading_max_rad": float(np.max(heading)),
        "speed_max_mps": float(np.max(speed)),
        "executable_equal": left_executable == right_executable,
        "terminal_equal": left_terminal == right_terminal,
    }
    passed = (
        errors["position_max_m"] <= 0.05
        and errors["heading_max_rad"] <= 0.01
        and errors["speed_max_mps"] <= 0.05
        and errors["executable_equal"]
        and errors["terminal_equal"]
    )
    return {"status": "pass" if passed else "cross_mode_functional_drift", **errors}


def endpoint_registry() -> list[dict[str, Any]]:
    registry: list[dict[str, Any]] = []
    for index, name in enumerate(ATOM_NAMES):
        registry.append(
            _endpoint(
                f"atom.normalized_delta.{index:02d}.{name}",
                "numeric_threshold",
                "[8,14]_float64_pair",
                f"max_row_abs((a[:,{index}]-b[:,{index}])/scale[{index}])",
                "all_8_candidate_rows_present_and_finite",
            )
        )
    for endpoint_id, shape, formula in (
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
    ):
        registry.append(
            _endpoint(
                endpoint_id,
                "numeric_threshold",
                shape,
                formula,
                "exact_shape_actor_roster_and_all_values_finite",
            )
        )
    for arm in ("static14d", "scene14d"):
        registry.extend(
            [
                _endpoint(
                    f"score.{arm}.abs_delta",
                    "numeric_threshold",
                    "[8]_float64_pair",
                    "max_shared_eligible_abs_score_delta",
                    "masks_equal_and_at_least_1_eligible_and_finite",
                ),
                _endpoint(
                    f"score.{arm}.within_mode_normalized_delta",
                    "numeric_threshold",
                    "[8]_float64_pair_plus_mode_thresholds",
                    (
                        "cross_abs_delta/max(seq_within_threshold,"
                        "batch8_within_threshold,1e-9)"
                    ),
                    "both_mode_thresholds_finite_positive",
                ),
                _endpoint(
                    f"score.{arm}.margin_ratio",
                    "numeric_threshold",
                    "[8]_float64_pair_plus_equal_masks",
                    (
                        "abs((runner_up-best)_a-(runner_up-best)_b)/"
                        "max(abs(margin_a),abs(margin_b),1e-9)"
                    ),
                    "at_least_2_shared_eligible_else_ambiguous_evidence_missing",
                ),
                _endpoint(
                    f"score.{arm}.rank_error",
                    "numeric_threshold",
                    "[8]_float64_pair_plus_equal_masks",
                    "1-spearman_average_tie_ranks",
                    (
                        "at_least_2_shared_eligible;both_constant_equal_is_zero;"
                        "one_constant_or_unequal_constants_is_ambiguous_evidence_missing"
                    ),
                ),
                _endpoint(
                    f"functional.{arm}.mask_eligibility",
                    "hard_exact",
                    "[8]_bool_pair",
                    "array_equal",
                    "exact_shape",
                ),
                _endpoint(
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
        )
    registry.extend(
        [
            _endpoint(
                "neighbor.relative_within_mode_inflation",
                "numeric_threshold",
                "three_state_q99_float64",
                (
                    "cross_q99/max(seq_q99,batch8_q99,"
                    "neighbor_resolution_floor)"
                ),
                "all_three_finite_nonnegative",
            ),
            _endpoint(
                "k8.finite_and_diverse",
                "hard_exact",
                "[8,80,4]_float32_each_mode_repeat",
                "all_finite_and_unique_row_sha256_count_eq_8",
                "every_state_mode_repeat",
            ),
            _endpoint(
                "authority.fingerprint",
                "hard_exact",
                "typed_authority_receipt",
                "all_literal_fingerprints_equal_contract",
                "all_fields_present",
            ),
            _endpoint(
                "pool.tensor_immutability_and_zero_calls",
                "hard_exact",
                "pre_post_sha_and_call_counters",
                "tensor_sha_equal_and_all_post_pool_call_counts_eq_0",
                "every_selector_receipt",
            ),
            _endpoint(
                "split.input_only_clone_nonoverlap",
                "hard_exact",
                "128_input_only_manifests_plus_b4_clone_keys",
                "within_calibration_cross_split_and_b4_intersections_all_empty",
                "receipt_formed_before_any_model_pool_selector_call",
            ),
        ]
    )
    return registry


def adaptation_contract_v2() -> dict[str, Any]:
    specs = {
        "development_calibration": _state_specs("development_calibration"),
        "independent_validation": _state_specs("independent_validation"),
    }
    registry = endpoint_registry()
    contract: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "frozen_executable_design_only_acquisition_unauthorized",
        "superseded_preacquisition_diagnostic": {
            "schema": "camp_dp_v25_fair_pool_adaptation_contract_v1",
            "root_sha256": V1_CONTRACT_ROOT,
            "review_root_sha256": V1_REVIEW_ROOT,
        },
        "scope": {
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
        },
        "source_and_sampler_authority": {
            "fixed_dp_head": FIXED_DP_HEAD,
            "sampler_module_path": SAMPLER_MODULE_PATH,
            "sampler_module_sha256": SAMPLER_MODULE_SHA256,
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
                "sha256": ROUTE_ASSET_SHA256,
            },
            "map_asset": {
                "path": (
                    "/root/autodl-tmp/"
                    "camp_dp_v23_source_license_freeze_retry2_51c97eb2_"
                    "20260715T172832CST/payload/sources/scenario_simulator_v2/"
                    "simulation/traffic_simulator/test/map/four_track_highway/"
                    "lanelet2_map.osm"
                ),
                "sha256": MAP_SHA256,
            },
            "b4_input_only_forbidden_manifest": {
                "artifact_path": B4_PREOPEN_PATH,
                "artifact_root_sha256": B4_PREOPEN_ROOT,
                "identity_source": {
                    "file_relative_path": "fresh_b4_execution_plan.json",
                    "file_sha256": B4_PLAN_SHA256,
                    "identity_json_pointer": "/identities",
                    "identity_subpayload_sha256": (
                        B4_IDENTITY_SUBPAYLOAD_SHA256
                    ),
                },
                "prepared_input_source": {
                    "file_relative_path": (
                        "fresh_b4_prepared_runtime_cases.json"
                    ),
                    "file_sha256": B4_PREPARED_RUNTIME_CASES_SHA256,
                    "case_count": 100,
                    "model_loaded": False,
                    "candidate_generation_executed": False,
                    "outcome_fields_consumed": [],
                },
                "derived_schema": (
                    "camp_dp_v25_fresh_b4_input_only_forbidden_clone_"
                    "manifest_v1"
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
                "heading_wrap": "((theta+pi) mod 2pi)-pi_with_plus_pi_to_minus_pi",
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
                "actor_missing_rule": "no_actors_is_empty_list;missing_actor_field_blocks",
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
        },
        "state_specifications": {
            **specs,
            "development_calibration_sha256": sha256_json(
                specs["development_calibration"]
            ),
            "independent_validation_sha256": sha256_json(
                specs["independent_validation"]
            ),
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
            },
        "repeat_authority": {
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
        },
        "threshold_algorithm": {
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
                "per_resample_statistic": "q99_higher_index_ceil_0.99_times_63_eq_63",
                "upper_confidence_quantile": 0.95,
                "upper_index": 9500,
                "final": "max(endpoint_resolution_floor,sorted_bootstrap[9500])",
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
                    "zero_lt_k_lt_n": (
                        "scipy.stats.beta.ppf(0.95,k+1,n-k)"
                    ),
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
        },
        "training_scale_authority": {
            "artifact_root_sha256": TRAINING_ROOT,
            "relative_path": "runtime_atom_scales.json",
            "file_sha256": TRAINING_SCALE_SHA256,
            "names_json_pointer": "/atom_names",
            "scales_json_pointer": "/scales",
            "index": [
                {"index": i, "name": name, "scale": scale}
                for i, (name, scale) in enumerate(zip(ATOM_NAMES, ATOM_SCALES))
            ],
            "zero_or_nonfinite": "authority_failure",
        },
        "endpoint_registry": registry,
        "endpoint_registry_sha256": sha256_json(registry),
        "score_margin_rank": {
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
        },
        "action_equivalence": {
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
        },
        "decision_table": {
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
        },
        "run_and_claim_boundary": {
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
        },
    }
    contract["contract_payload_sha256"] = sha256_json(contract)
    return contract


def validate_contract_v2(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("contract must be object")
    expected = adaptation_contract_v2()
    if value != expected:
        raise ValueError("v2 contract literal drifted")
    registry = value["endpoint_registry"]
    ids = [entry["id"] for entry in registry]
    if len(ids) != len(set(ids)) or ids != value["decision_table"][
        "required_endpoint_ids"
    ]:
        raise ValueError("endpoint registry is not exhaustive and unique")
    payload = copy.deepcopy(dict(value))
    supplied = payload.pop("contract_payload_sha256")
    if supplied != sha256_json(payload):
        raise ValueError("contract payload SHA drifted")
    return copy.deepcopy(dict(value))


def decide_endpoint_statuses(
    contract: Mapping[str, Any],
    statuses: Mapping[str, str],
    *,
    both_within_modes_pass: bool,
) -> dict[str, Any]:
    validated = validate_contract_v2(contract)
    required = validated["decision_table"]["required_endpoint_ids"]
    if type(statuses) is not dict or set(statuses) != set(required):
        raise ValueError("endpoint status keyset must exactly match registry")
    allowed = {
        "pass",
        "authority_failure",
        "evidence_missing",
        "ambiguous_evidence_missing",
        "within_mode_generator_instability",
        "cross_mode_functional_drift",
    }
    if any(status not in allowed for status in statuses.values()):
        raise ValueError("unknown endpoint status")
    if not both_within_modes_pass:
        return {
            "status": "BLOCK",
            "classification": "within_mode_generator_instability",
        }
    precedence = validated["decision_table"]["block_precedence"]
    for classification in precedence:
        if classification == "evidence_missing":
            if any(
                status in {"evidence_missing", "ambiguous_evidence_missing"}
                for status in statuses.values()
            ):
                return {"status": "BLOCK", "classification": classification}
        elif classification in statuses.values():
            return {"status": "BLOCK", "classification": classification}
    if all(status == "pass" for status in statuses.values()):
        return {
            "status": "PASS",
            "classification": (
                "single_route_bounded_scope_current_evidence_does_not_"
                "trigger_retraining"
            ),
        }
    raise ValueError("unclassified decision state")


def numeric_endpoint_result(
    contract: Mapping[str, Any],
    endpoint_id: str,
    state_errors: Sequence[float],
    *,
    threshold: float,
) -> dict[str, Any]:
    validated = validate_contract_v2(contract)
    registry = {
        item["id"]: item for item in validated["endpoint_registry"]
    }
    endpoint = registry.get(endpoint_id)
    if endpoint is None or endpoint["kind"] != "numeric_threshold":
        raise ValueError("numeric endpoint is absent from registry")
    limit = _positive(threshold, "endpoint threshold")
    try:
        errors = _finite_vector(state_errors, "validation state errors")
    except (TypeError, ValueError):
        return {
            "endpoint_id": endpoint_id,
            "applicable": True,
            "state_denominator": (
                len(state_errors) if hasattr(state_errors, "__len__") else 0
            ),
            "missing_state_count": 1,
            "threshold": limit,
            "exceedance_count": None,
            "clopper_pearson_upper_95": None,
            "status": "evidence_missing",
        }
    if len(errors) != 64:
        return {
            "endpoint_id": endpoint_id,
            "applicable": True,
            "state_denominator": len(errors),
            "missing_state_count": abs(64 - len(errors)),
            "threshold": limit,
            "exceedance_count": None,
            "clopper_pearson_upper_95": None,
            "status": "evidence_missing",
        }
    exceedance_count = int(np.count_nonzero(errors > limit))
    cp_upper = clopper_pearson_upper(exceedance_count, 64)
    status = (
        "pass"
        if exceedance_count <= 2 and cp_upper <= 0.10
        else "cross_mode_functional_drift"
    )
    return {
        "endpoint_id": endpoint_id,
        "applicable": True,
        "state_denominator": 64,
        "missing_state_count": 0,
        "threshold": limit,
        "exceedance_count": exceedance_count,
        "clopper_pearson_upper_95": cp_upper,
        "status": status,
    }


def validate_endpoint_result_keyset(
    contract: Mapping[str, Any],
    results: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    validated = validate_contract_v2(contract)
    fields = set(validated["decision_table"]["endpoint_result_exact_fields"])
    if type(results) is not list:
        raise ValueError("endpoint results must be list")
    statuses: dict[str, str] = {}
    for result in results:
        if type(result) is not dict or set(result) != fields:
            raise ValueError("endpoint result schema drifted")
        endpoint_id = result["endpoint_id"]
        if endpoint_id in statuses:
            raise ValueError("endpoint result duplicated")
        statuses[endpoint_id] = result["status"]
    required = set(validated["decision_table"]["required_endpoint_ids"])
    if set(statuses) != required:
        raise ValueError("required endpoint result omitted or unknown")
    return statuses


def _endpoint(
    endpoint_id: str,
    kind: str,
    input_shape: str,
    formula: str,
    applicability: str,
) -> dict[str, Any]:
    numeric = kind == "numeric_threshold"
    return {
        "id": endpoint_id,
        "kind": kind,
        "input_shape": input_shape,
        "formula": formula,
        "units": _units(endpoint_id),
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
            _resolution_floor(endpoint_id) if numeric else None
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


def _units(endpoint_id: str) -> str:
    if "position" in endpoint_id:
        return "m"
    if "heading" in endpoint_id:
        return "rad"
    if "speed" in endpoint_id:
        return "m/s"
    if endpoint_id.startswith("atom."):
        return "training_scale_normalized"
    return "dimensionless"


def _resolution_floor(endpoint_id: str) -> float:
    if endpoint_id.startswith("atom."):
        return 1e-8
    if "position_max_m" in endpoint_id:
        return 1e-4
    if "heading_max_rad" in endpoint_id:
        return 1e-5
    if "speed_max_mps" in endpoint_id:
        return 1e-4
    if endpoint_id.startswith("score.") and endpoint_id.endswith(".abs_delta"):
        return 1e-9
    if endpoint_id.startswith("score."):
        return 1e-9
    if endpoint_id == "neighbor.relative_within_mode_inflation":
        return 1e-9
    raise ValueError(f"numeric endpoint resolution floor is undefined: {endpoint_id}")


def _state_specs(split: str) -> list[dict[str, Any]]:
    if split not in {"development_calibration", "independent_validation"}:
        raise ValueError(split)
    base = 0 if split == "development_calibration" else 64
    scenario_base = 41000 if split == "development_calibration" else 51000
    latent_base = 61000 if split == "development_calibration" else 71000
    tiers = ("no_npc", "low_density", "medium_density", "high_density")
    result: list[dict[str, Any]] = []
    for index in range(64):
        payload = {
            "split": split,
            "state_spec_id": f"{split}:{index:03d}",
            "state_index": index,
            "source_state_ordinal": base + index,
            "source_role": "development_nonholdout",
            "source_sampler_module_sha256": SAMPLER_MODULE_SHA256,
            "route_asset_sha256": ROUTE_ASSET_SHA256,
            "map_geometry_sha256": MAP_SHA256,
            "family": "four_track_highway",
            "tier": tiers[index % 4],
            "scenario_seed": scenario_base + index,
            "latent_seed": latent_base + index,
            "latent_policy": "row0_zero_rows1_7_philox_normal_float32_v1",
            "candidate_k": 8,
            "independent_statistical_unit": "state",
        }
        payload["state_spec_sha256"] = sha256_json(payload)
        result.append(payload)
    return result


def _average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    index = 0
    while index < len(values):
        end = index + 1
        while end < len(values) and values[order[end]] == values[order[index]]:
            end += 1
        average = (index + 1 + end) / 2.0
        ranks[order[index:end]] = average
        index = end
    return ranks


def _finite_vector(values: Sequence[float], label: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or len(array) == 0 or not np.isfinite(array).all():
        raise ValueError(f"{label} must be finite nonempty vector")
    return array


def _bool_vector(values: Sequence[bool], label: str) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1 or array.dtype != np.bool_:
        raise ValueError(f"{label} must be boolean vector")
    return array


def _positive(value: float, label: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{label} must be finite positive")
    return value
