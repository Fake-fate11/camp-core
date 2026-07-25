"""Outcome-independent fair-pool adaptation qualification contract.

This module contains data and validation only.  It must not import or call the
Diffusion Planner, a pool generator, a selector, or any Fresh/holdout reader.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any, Mapping


SCHEMA_VERSION = "camp_dp_v25_fair_pool_adaptation_contract_v1"
GENERATOR_NAME = "new_single_invocation_batched_k8_candidate_pool"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CAPABILITY_ROOT = "fa94808c70ce1953d50b52497f9c4d056dabccd96e3ffdaed84faead5f2ed8e6"
TRAINING_ROOT = "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
TRAINING_SCALE_SHA256 = (
    "72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb"
)
ROUTE_SHA256 = "63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd"
MAP_SHA256 = "c13a9234727186c77c019766c3358c30faf10af61503a566f0fff0963be53bbd"
B4_IDENTITY_SHA256 = (
    "5f2f8e2c2eb90927ec485a8d0baa3935b155e82d90b04fa3d456fc845cd8464a"
)
B4_PROTOCOL_SHA256 = (
    "aa79576f8ac487e2ce197c481d57f9c5d350a41d9522096975786207ef76785f"
)
B4_PLAN_SHA256 = (
    "41442dd7d71552972d737d9a9e3d56e9827f864e0c06e11c57487f651206dee0"
)
B4_NONCE = "8680c1b19ce0620b7dc2ec9453ffde0da024d3443e6d6307fc41e87f3dad3b42"

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


def _state_specs(split: str) -> list[dict[str, Any]]:
    if split not in {"development_calibration", "independent_validation"}:
        raise ValueError(split)
    base_ordinal = 0 if split == "development_calibration" else 64
    scenario_seed_base = 41000 if split == "development_calibration" else 51000
    latent_seed_base = 61000 if split == "development_calibration" else 71000
    tiers = ("no_npc", "low_density", "medium_density", "high_density")
    specs: list[dict[str, Any]] = []
    for local_index in range(64):
        ordinal = base_ordinal + local_index
        tier = tiers[local_index % len(tiers)]
        spec = {
            "split": split,
            "state_index": local_index,
            "state_spec_id": f"{split}:{local_index:03d}",
            "independent_statistical_unit": "state",
            "rows_and_ticks_role": "within_state_observations_only",
            "source_role": "development_nonholdout",
            "source_sampler": "predeclared_chronological_route_state_sampler_v1",
            "source_state_ordinal": ordinal,
            "family": "four_track_highway",
            "tier": tier,
            "route_id": (
                "1962e44a5dd0ace089aeb9011d5b70e05dfa6ae5adeec4450a6c20e3e09776b2"
            ),
            "route_sha256": ROUTE_SHA256,
            "map_geometry_sha256": MAP_SHA256,
            "scenario_seed": scenario_seed_base + local_index,
            "latent_policy": "row0_zero_rows1_7_philox_normal_float32_v1",
            "latent_seed": latent_seed_base + local_index,
            "candidate_k": 8,
        }
        spec["state_spec_sha256"] = sha256_json(spec)
        specs.append(spec)
    return specs


def fair_pool_adaptation_contract() -> dict[str, Any]:
    calibration = _state_specs("development_calibration")
    validation = _state_specs("independent_validation")
    calibration_sha = sha256_json(calibration)
    validation_sha = sha256_json(validation)
    atom_scale_index = [
        {"index": index, "name": name, "scale": scale}
        for index, (name, scale) in enumerate(zip(ATOM_NAMES, ATOM_SCALES))
    ]
    contract: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "frozen_outcome_independent_design_only",
        "supersedes_for_future_qualification": (
            "overconservative_any_neighbor_float_outside_1e_5_hard_stop"
        ),
        "preserved_prior_classification": (
            "overconservative_equivalence_contract_triggered; "
            "functional adaptation risk unresolved"
        ),
        "authority": {
            "generator_name": GENERATOR_NAME,
            "fixed_dp_head": FIXED_DP_HEAD,
            "model_checkpoint": {
                "path": "/root/autodl-tmp/camp_dp_assets/diffusion_planner.pth",
                "sha256": (
                    "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75"
                ),
            },
            "model_source_sha256": (
                "341c8f5798cae83fdee3ae7203243ab129458d8eab362e0c3a1c7daee08d502d"
            ),
            "encoder_source_sha256": (
                "360b3632cc0f9d65ffb25ed4adc906b498d824df0d4b6e37f5c59eb252f8daab"
            ),
            "decoder_source_sha256": (
                "8e81d1e9aa879dd0c0762d623dbe7480786e2618ccb261d10fd72cc00192e7dd"
            ),
            "capability_artifact_root_sha256": CAPABILITY_ROOT,
            "training_artifact_root_sha256": TRAINING_ROOT,
            "atom_scale_source": {
                "relative_path": "runtime_atom_scales.json",
                "sha256": TRAINING_SCALE_SHA256,
                "schema_version": "camp_dp_v25_runtime_atom_scales_v1",
                "atom_schema_version": "dp_camp_v10_14d",
                "scale_field_json_pointer": "/scales",
                "atom_name_field_json_pointer": "/atom_names",
                "index": atom_scale_index,
                "zero_or_nonfinite_policy": "authority_failure_fail_closed",
            },
            "runtime": {
                "gpu_name": "NVIDIA GeForce RTX 5090",
                "gpu_uuid": "GPU-c82677a4-21d3-a44c-5195-e41c150e086c",
                "driver_version": "595.71.05",
                "torch_version": "2.8.0+cu128",
                "torch_cuda_version": "12.8",
                "cudnn_version": 91002,
                "dtype": "float32",
                "model_eval_mode": True,
                "deterministic_algorithms": True,
                "tf32_allowed": False,
                "cudnn_benchmark": False,
                "global_rng_state_must_be_unchanged": True,
            },
        },
        "manifests": {
            "development_calibration": calibration,
            "development_calibration_sha256": calibration_sha,
            "independent_validation": validation,
            "independent_validation_sha256": validation_sha,
            "state_count_per_split": 64,
            "total_state_count": 128,
            "family_counts_per_split": {"four_track_highway": 64},
            "tier_counts_per_split": {
                "no_npc": 16,
                "low_density": 16,
                "medium_density": 16,
                "high_density": 16,
            },
            "route_counts_per_split": {ROUTE_SHA256: 64},
            "source_counts_per_split": {"development_nonholdout": 64},
            "independent_statistical_unit": "state",
            "rows_and_ticks_role": "within_state_observations_only",
            "actual_state_input_and_latent_tensor_sha_required_at_acquisition": True,
            "actual_state_input_and_latent_tensor_sha_present_now": False,
        },
        "split_nonoverlap": {
            "id_free_clone_key_formula": {
                "hash": "sha256",
                "serialization": "canonical_json_utf8_sorted_keys_no_nan",
                "fields": [
                    "map_geometry_sha256",
                    "ordered_route_geometry_sha256",
                    "spawn_pose_xyz_quantized_1mm",
                    "spawn_heading_wrapped_quantized_1e-4rad",
                    "goal_pose_xyz_quantized_1mm",
                    "goal_heading_wrapped_quantized_1e-4rad",
                    "route_polyline_resampled_0_5m_quantized_1mm",
                    (
                        "dynamic_actor_initial_state_sorted_by_"
                        "class_dimensions_pose_heading_speed"
                    ),
                    "scenario_source_content_sha256",
                ],
                "id_fields_forbidden": [
                    "state_id",
                    "scenario_id",
                    "route_id",
                    "database_row_id",
                ],
            },
            "conflict_policy": (
                "any_duplicate_within_split_or_across_splits_or_against_"
                "forbidden_b4_clone_manifest_aborts_before_first_run;"
                "no_drop_no_replacement_no_suffix"
            ),
            "b4_forbidden_identity": {
                "identity_sha256": B4_IDENTITY_SHA256,
                "protocol_sha256": B4_PROTOCOL_SHA256,
                "plan_sha256": B4_PLAN_SHA256,
                "nonce": B4_NONCE,
                "source_role": "fresh_holdout",
            },
            "b4_outcome_read_for_sampling_or_dedup_forbidden": True,
            "required_before_acquisition": [
                "calibration_vs_validation_clone_key_intersection_empty",
                "calibration_vs_b4_input_only_clone_key_intersection_empty",
                "validation_vs_b4_input_only_clone_key_intersection_empty",
                "all_state_spec_sha256_unique",
            ],
            "current_design_manifest_overlap_status": (
                "specification_disjoint; actual_input_clone_check_pending_"
                "future_separately_authorized_acquisition_preflight"
            ),
        },
        "repeat_design": {
            "acquisition_authorized": False,
            "within_mode_repeat_count_per_state": 5,
            "modes": ["sequential_batch1_x8", "single_invocation_batch8"],
            "within_mode_pair_topology": (
                "all_10_unordered_pairs_from_repeat_indices_0_1_2_3_4"
            ),
            "cross_mode_pair_topology": (
                "repeat_index_matched_0_to_0_through_4_to_4_only"
            ),
            "cross_mode_entry_condition": (
                "both_modes_pass_all_within_mode_repeatability_and_authority_gates"
            ),
            "forward_fingerprint_fields": [
                "state_spec_sha256",
                "actual_input_sha256",
                "actual_state_sha256",
                "latent_tensor_sha256",
                "latent_seed",
                "model_checkpoint_sha256",
                "model_source_sha256",
                "fixed_dp_head",
                "runtime_fingerprint_sha256",
                "mode",
                "repeat_index",
                "forward_invocation_id",
            ],
            "sequential_mode_model_calls_per_repeat": 8,
            "batch8_mode_model_calls_per_repeat": 1,
            "k8_finite_rule": "all_candidate_tensor_values_finite",
            "k8_diverse_rule": "eight_row_sha256_values_are_unique",
            "fail_closed": [
                "repeat_count_or_pair_topology_drift",
                "runtime_or_dtype_or_determinism_policy_drift",
                "input_state_latent_model_checkpoint_or_source_fingerprint_drift",
                "any_k8_nonfinite",
                "any_k8_nondiverse",
                "global_rng_boundary_changed",
            ],
        },
        "threshold_generation": {
            "calibration_state_count": 64,
            "minimum_calibration_state_count": 64,
            "validation_state_count": 64,
            "minimum_validation_state_count": 64,
            "within_state_aggregation": (
                "endpoint_error_per_predeclared_pair_then_empirical_q99_higher"
            ),
            "across_state_aggregation": (
                "empirical_q99_higher_of_64_state_statistics"
            ),
            "quantile": 0.99,
            "quantile_method": "higher",
            "confidence_method": (
                "deterministic_nonparametric_state_bootstrap_percentile_upper"
            ),
            "confidence_level": 0.95,
            "bootstrap_resamples": 10000,
            "bootstrap_seed": 825071,
            "threshold_formula": (
                "max(endpoint_resolution_floor,bootstrap_upper_95pct_of_"
                "state_q99)"
            ),
            "validation_exceedance": {
                "comparison": "error <= frozen_threshold_is_pass",
                "exceedance_definition": "error > frozen_threshold",
                "maximum_observed_rate": 0.05,
                "maximum_exceedance_count_at_n64": 2,
                "one_sided_binomial_ci": "clopper_pearson_exact",
                "ci_level": 0.95,
                "ci_upper_comparison": "<= 0.10",
            },
            "endpoint_error_functions": {
                "trajectory_position_m": "max_t_l2_xy",
                "trajectory_heading_rad": "max_t_abs_wrap_to_pi_delta",
                "trajectory_speed_mps": "max_t_abs_delta",
                "neighbor_position_m": "max_actor_t_l2_xy_after_literal_actor_slot",
                "neighbor_heading_rad": "max_actor_t_abs_wrap_to_pi_delta",
                "neighbor_speed_mps": "max_actor_t_abs_delta",
                "atom_normalized_delta": (
                    "max_row_abs((atom_a-atom_b)/training_scale_by_index)"
                ),
                "score_abs_delta": "max_eligible_row_abs_score_delta",
                "score_within_mode_normalized_delta": (
                    "cross_mode_abs_delta/max(seq_threshold,batch8_threshold,"
                    "score_resolution_floor)"
                ),
                "margin_ratio": (
                    "abs(margin_a-margin_b)/max(abs(margin_a),abs(margin_b),"
                    "margin_resolution_floor)"
                ),
                "rank_error": "1-spearman_rho_average_ranks_on_shared_eligible_rows",
                "neighbor_relative_within_mode_inflation": (
                    "cross_mode_state_q99/max(seq_state_q99,batch8_state_q99,"
                    "endpoint_resolution_floor)"
                ),
            },
            "resolution_floors": {
                "trajectory_position_m": 0.0001,
                "trajectory_heading_rad": 0.00001,
                "trajectory_speed_mps": 0.0001,
                "neighbor_position_m": 0.0001,
                "neighbor_heading_rad": 0.00001,
                "neighbor_speed_mps": 0.0001,
                "atom_normalized_delta": 1e-08,
                "score_abs_delta": 1e-09,
                "score_within_mode_normalized_delta": 1e-09,
                "margin_ratio": 1e-09,
                "rank_error": 1e-09,
                "neighbor_relative_within_mode_inflation": 1e-09,
            },
            "atom_scale_binding": {
                "artifact_root_sha256": TRAINING_ROOT,
                "relative_path": "runtime_atom_scales.json",
                "file_sha256": TRAINING_SCALE_SHA256,
                "json_pointer": "/scales",
                "index": atom_scale_index,
                "zero_or_nonfinite_policy": "authority_failure_fail_closed",
            },
            "score_and_margin": {
                "eligible_candidate_set": "mask_true_rows_only",
                "best_score_direction": "lower",
                "margin": "runner_up_score_minus_best_score",
                "fewer_than_two_eligible": "ambiguous_evidence_missing",
                "exact_score_tie": "margin_zero_and_smallest_row_index_tie_break",
                "near_tie_threshold": (
                    "2*max(frozen_score_abs_delta_threshold,"
                    "score_resolution_floor)"
                ),
                "near_tie_comparison": "margin <= near_tie_threshold",
                "selected_index_tie_break": "smallest_eligible_row_index",
                "rank": "spearman_average_ranks_on_shared_eligible_rows",
            },
            "observed_prior_values_forbidden_from_threshold_generation": [
                1.2076,
                "114/128",
                "9/16",
                "0_selection_flips",
            ],
        },
        "functional_action_gate": {
            "hard_fail": [
                "mask_or_eligibility_changed",
                "post_pool_dp_model_latent_or_candidate_generation_call_nonzero",
                "candidate_tensor_mutated",
                "k8_nonfinite_or_nondiverse",
                "authority_or_fingerprint_drift",
            ],
            "selected_index_flip_policy": (
                "neither_automatic_fail_nor_automatic_exemption;"
                "evaluate_predeclared_action_equivalence"
            ),
            "action_equivalence": {
                "time_alignment": (
                    "exact_same_80_samples_at_dt_0_1s_no_interpolation"
                ),
                "position_error": "max_t_l2_xy <= 0.05_m",
                "heading_error": "max_t_abs_wrap_to_pi_delta <= 0.01_rad",
                "speed_error": "max_t_abs_delta <= 0.05_mps",
                "executable_state": "must_be_identical",
                "terminal_state": "must_be_identical",
                "all_conditions_required": True,
                "threshold_source": (
                    "prospective_project_action_equivalence_design_2026_07_25"
                ),
            },
            "neighbor_gate": {
                "unit": "state_then_row",
                "single_float_1e_5_veto_forbidden": True,
                "conditions": [
                    "state_row_exceedance_rate_and_count_within_validation_limit",
                    "state_quantile_coverage_within_validation_limit",
                    (
                        "relative_within_mode_inflation_within_its_"
                        "calibration_frozen_threshold"
                    ),
                ],
            },
        },
        "validation_topology": {
            "per_state_first": True,
            "qualification_vector": [
                "per_atom_normalized_delta",
                "score_delta_and_within_mode_ratio",
                "margin_ratio",
                "rank_correlation",
                "mask_and_eligibility",
                "selected_index_and_action_flip",
                "neighbor_and_trajectory_coverage",
                "k8_failure_taxonomy",
            ],
            "multiendpoint_policy": "all_required_endpoints_must_pass_no_weighted_total",
            "missing_policy": "BLOCK_evidence_missing",
            "ambiguous_policy": "BLOCK_evidence_missing",
            "pass_boolean": (
                "authority_pass AND split_pass AND both_within_mode_pass AND "
                "cross_mode_all_endpoints_pass AND hard_fail_count_eq_0"
            ),
            "block_classification_precedence": [
                "authority_failure",
                "evidence_missing",
                "within_mode_generator_instability",
                "cross_mode_functional_drift",
            ],
            "pass_interpretation": (
                "current_evidence_does_not_trigger_retraining;"
                "not_general_ood_equivalence_and_not_benefit"
            ),
            "fail_interpretation": (
                "classified_block_only;does_not_directly_mean_retraining_required"
            ),
            "weighted_total_forbidden": True,
            "benefit_claim_forbidden": True,
            "general_ood_equivalence_claim_forbidden": True,
        },
        "claim_and_run_boundary": {
            "acquisition_authorized": False,
            "calibration_run_count": 0,
            "repeat_model_run_count": 0,
            "pool_run_count": 0,
            "selector_run_count": 0,
            "closed_loop_run_count": 0,
            "fresh_run_count": 0,
            "holdout_run_count": 0,
            "training_run_count": 0,
            "fresh": False,
            "holdout": False,
            "training": False,
            "closed_loop": False,
            "legacy_hard_stop_preserved": True,
            "legacy_reverse_functional_evidence_preserved": True,
            "claim_authorized": False,
            "promotion_or_deployment_authorized": False,
        },
    }
    contract["contract_payload_sha256"] = sha256_json(contract)
    return contract


def _expect_exact_keys(value: Mapping[str, Any], keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise ValueError(f"{label} keys drifted")


def validate_fair_pool_adaptation_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("contract must be object")
    expected = fair_pool_adaptation_contract()
    if value != expected:
        raise ValueError("fair-pool adaptation contract literal drifted")
    _expect_exact_keys(value, set(expected), "contract")
    manifests = value["manifests"]
    if len(manifests["development_calibration"]) != 64:
        raise ValueError("calibration state count drifted")
    if len(manifests["independent_validation"]) != 64:
        raise ValueError("validation state count drifted")
    state_specs = (
        manifests["development_calibration"] + manifests["independent_validation"]
    )
    spec_hashes = [item["state_spec_sha256"] for item in state_specs]
    if len(set(spec_hashes)) != 128:
        raise ValueError("state manifests overlap")
    for item in state_specs:
        payload = dict(item)
        digest = payload.pop("state_spec_sha256")
        if sha256_json(payload) != digest:
            raise ValueError("state manifest digest drifted")
    if manifests["development_calibration_sha256"] != sha256_json(
        manifests["development_calibration"]
    ):
        raise ValueError("calibration manifest digest drifted")
    if manifests["independent_validation_sha256"] != sha256_json(
        manifests["independent_validation"]
    ):
        raise ValueError("validation manifest digest drifted")
    scales = value["authority"]["atom_scale_source"]["index"]
    if len(scales) != 14 or any(
        not math.isfinite(item["scale"]) or item["scale"] <= 0.0 for item in scales
    ):
        raise ValueError("atom scale source invalid")
    payload = copy.deepcopy(dict(value))
    digest = payload.pop("contract_payload_sha256")
    if sha256_json(payload) != digest:
        raise ValueError("contract payload digest drifted")
    return copy.deepcopy(dict(value))

