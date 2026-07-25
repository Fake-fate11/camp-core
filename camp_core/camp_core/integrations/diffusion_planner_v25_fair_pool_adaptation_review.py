"""Independent literal oracle for the fair-pool adaptation contract.

This module intentionally does not import the producer contract module.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping


EXPECTED_SCHEMA = "camp_dp_v25_fair_pool_adaptation_contract_v1"
EXPECTED_FIXED_DP = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_TRAINING_ROOT = (
    "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
)
EXPECTED_SCALE_SHA = "72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb"
EXPECTED_CONTRACT_PAYLOAD_SHA256 = (
    "8cc5510f72a1697e2a2f258e061b32f57342eb6387b7dfcabf53f50df740e0a1"
)
EXPECTED_ROUTE_SHA = "63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd"
EXPECTED_MAP_SHA = "c13a9234727186c77c019766c3358c30faf10af61503a566f0fff0963be53bbd"
EXPECTED_SCALE_NAMES = [
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
]
EXPECTED_SCALES = [
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
]


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


def review_contract_literal(contract: Mapping[str, Any]) -> dict[str, Any]:
    if type(contract) is not dict:
        raise ValueError("contract must be object")
    if contract.get("schema_version") != EXPECTED_SCHEMA:
        raise ValueError("schema drifted")
    if contract.get("status") != "frozen_outcome_independent_design_only":
        raise ValueError("status drifted")
    authority = _obj(contract, "authority")
    if authority.get("generator_name") != (
        "new_single_invocation_batched_k8_candidate_pool"
    ):
        raise ValueError("generator drifted")
    if authority.get("fixed_dp_head") != EXPECTED_FIXED_DP:
        raise ValueError("fixed DP drifted")
    runtime = _obj(authority, "runtime")
    expected_runtime = {
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
    }
    if runtime != expected_runtime:
        raise ValueError("runtime policy drifted")
    scale_source = _obj(authority, "atom_scale_source")
    if (
        authority.get("training_artifact_root_sha256") != EXPECTED_TRAINING_ROOT
        or scale_source.get("sha256") != EXPECTED_SCALE_SHA
        or scale_source.get("scale_field_json_pointer") != "/scales"
        or scale_source.get("atom_name_field_json_pointer") != "/atom_names"
        or scale_source.get("zero_or_nonfinite_policy")
        != "authority_failure_fail_closed"
    ):
        raise ValueError("training scale authority drifted")
    index = scale_source.get("index")
    if type(index) is not list or len(index) != 14:
        raise ValueError("scale index drifted")
    for i, entry in enumerate(index):
        if entry != {
            "index": i,
            "name": EXPECTED_SCALE_NAMES[i],
            "scale": EXPECTED_SCALES[i],
        }:
            raise ValueError("scale value or index drifted")
        if not math.isfinite(entry["scale"]) or entry["scale"] <= 0:
            raise ValueError("invalid scale")
    manifests = _obj(contract, "manifests")
    _review_manifest(manifests, "development_calibration", 0, 41000, 61000)
    _review_manifest(manifests, "independent_validation", 64, 51000, 71000)
    if manifests.get("state_count_per_split") != 64:
        raise ValueError("state count drifted")
    cal = manifests["development_calibration"]
    val = manifests["independent_validation"]
    if manifests.get("development_calibration_sha256") != _sha(cal):
        raise ValueError("calibration manifest SHA drifted")
    if manifests.get("independent_validation_sha256") != _sha(val):
        raise ValueError("validation manifest SHA drifted")
    all_hashes = [x["state_spec_sha256"] for x in cal + val]
    if len(all_hashes) != 128 or len(set(all_hashes)) != 128:
        raise ValueError("state split overlap")
    overlap = _obj(contract, "split_nonoverlap")
    formula = _obj(overlap, "id_free_clone_key_formula")
    if formula.get("hash") != "sha256" or formula.get("id_fields_forbidden") != [
        "state_id",
        "scenario_id",
        "route_id",
        "database_row_id",
    ]:
        raise ValueError("ID-free clone formula drifted")
    if overlap.get("conflict_policy") != (
        "any_duplicate_within_split_or_across_splits_or_against_"
        "forbidden_b4_clone_manifest_aborts_before_first_run;"
        "no_drop_no_replacement_no_suffix"
    ):
        raise ValueError("overlap conflict policy drifted")
    if overlap.get("b4_outcome_read_for_sampling_or_dedup_forbidden") is not True:
        raise ValueError("B4 sampling boundary drifted")
    repeat = _obj(contract, "repeat_design")
    if repeat.get("acquisition_authorized") is not False:
        raise ValueError("acquisition became authorized")
    if repeat.get("within_mode_repeat_count_per_state") != 5:
        raise ValueError("repeat count drifted")
    if repeat.get("within_mode_pair_topology") != (
        "all_10_unordered_pairs_from_repeat_indices_0_1_2_3_4"
    ):
        raise ValueError("pair topology drifted")
    if repeat.get("cross_mode_pair_topology") != (
        "repeat_index_matched_0_to_0_through_4_to_4_only"
    ):
        raise ValueError("cross-mode topology drifted")
    threshold = _obj(contract, "threshold_generation")
    expected_threshold_literals = {
        "calibration_state_count": 64,
        "minimum_calibration_state_count": 64,
        "validation_state_count": 64,
        "minimum_validation_state_count": 64,
        "quantile": 0.99,
        "quantile_method": "higher",
        "confidence_method": (
            "deterministic_nonparametric_state_bootstrap_percentile_upper"
        ),
        "confidence_level": 0.95,
        "bootstrap_resamples": 10000,
        "bootstrap_seed": 825071,
    }
    for key, expected in expected_threshold_literals.items():
        if threshold.get(key) != expected:
            raise ValueError(f"threshold literal {key} drifted")
    if threshold.get("threshold_formula") != (
        "max(endpoint_resolution_floor,bootstrap_upper_95pct_of_state_q99)"
    ):
        raise ValueError("threshold formula drifted")
    exceedance = _obj(threshold, "validation_exceedance")
    if exceedance != {
        "comparison": "error <= frozen_threshold_is_pass",
        "exceedance_definition": "error > frozen_threshold",
        "maximum_observed_rate": 0.05,
        "maximum_exceedance_count_at_n64": 2,
        "one_sided_binomial_ci": "clopper_pearson_exact",
        "ci_level": 0.95,
        "ci_upper_comparison": "<= 0.10",
    }:
        raise ValueError("validation exceedance rule drifted")
    score = _obj(threshold, "score_and_margin")
    if score != {
        "eligible_candidate_set": "mask_true_rows_only",
        "best_score_direction": "lower",
        "margin": "runner_up_score_minus_best_score",
        "fewer_than_two_eligible": "ambiguous_evidence_missing",
        "exact_score_tie": "margin_zero_and_smallest_row_index_tie_break",
        "near_tie_threshold": (
            "2*max(frozen_score_abs_delta_threshold,score_resolution_floor)"
        ),
        "near_tie_comparison": "margin <= near_tie_threshold",
        "selected_index_tie_break": "smallest_eligible_row_index",
        "rank": "spearman_average_ranks_on_shared_eligible_rows",
    }:
        raise ValueError("margin/tie/rank rule drifted")
    action = _obj(_obj(contract, "functional_action_gate"), "action_equivalence")
    if action != {
        "time_alignment": "exact_same_80_samples_at_dt_0_1s_no_interpolation",
        "position_error": "max_t_l2_xy <= 0.05_m",
        "heading_error": "max_t_abs_wrap_to_pi_delta <= 0.01_rad",
        "speed_error": "max_t_abs_delta <= 0.05_mps",
        "executable_state": "must_be_identical",
        "terminal_state": "must_be_identical",
        "all_conditions_required": True,
        "threshold_source": (
            "prospective_project_action_equivalence_design_2026_07_25"
        ),
    }:
        raise ValueError("action-equivalence rule drifted")
    topology = _obj(contract, "validation_topology")
    if topology.get("multiendpoint_policy") != (
        "all_required_endpoints_must_pass_no_weighted_total"
    ):
        raise ValueError("multiendpoint topology drifted")
    if topology.get("pass_boolean") != (
        "authority_pass AND split_pass AND both_within_mode_pass AND "
        "cross_mode_all_endpoints_pass AND hard_fail_count_eq_0"
    ):
        raise ValueError("PASS topology drifted")
    if topology.get("block_classification_precedence") != [
        "authority_failure",
        "evidence_missing",
        "within_mode_generator_instability",
        "cross_mode_functional_drift",
    ]:
        raise ValueError("block classification drifted")
    boundary = _obj(contract, "claim_and_run_boundary")
    expected_zero = [
        "calibration_run_count",
        "repeat_model_run_count",
        "pool_run_count",
        "selector_run_count",
        "closed_loop_run_count",
        "fresh_run_count",
        "holdout_run_count",
        "training_run_count",
    ]
    if boundary.get("acquisition_authorized") is not False:
        raise ValueError("acquisition boundary drifted")
    if any(boundary.get(key) != 0 for key in expected_zero):
        raise ValueError("a prohibited run count is nonzero")
    for key in ("fresh", "holdout", "training", "closed_loop"):
        if boundary.get(key) is not False:
            raise ValueError(f"{key} boundary drifted")
    if boundary.get("claim_authorized") is not False:
        raise ValueError("claim boundary drifted")
    payload = dict(contract)
    supplied = payload.pop("contract_payload_sha256", None)
    if supplied != _sha(payload):
        raise ValueError("contract payload SHA drifted")
    if supplied != EXPECTED_CONTRACT_PAYLOAD_SHA256:
        raise ValueError("reviewer-local expected contract SHA drifted")
    return {
        "status": "passed_independent_literal_contract_review",
        "calibration_state_count": 64,
        "validation_state_count": 64,
        "repeat_count_per_mode_per_state": 5,
        "threshold_and_decision_literals_rebuilt": True,
        "manifest_and_split_literals_rebuilt": True,
        "training_scale_binding_rebuilt": True,
        "claim_and_zero_run_boundary_rebuilt": True,
    }


def _review_manifest(
    manifests: Mapping[str, Any],
    split: str,
    base_ordinal: int,
    scenario_seed_base: int,
    latent_seed_base: int,
) -> None:
    entries = manifests.get(split)
    if type(entries) is not list or len(entries) != 64:
        raise ValueError(f"{split} manifest count drifted")
    tiers = ("no_npc", "low_density", "medium_density", "high_density")
    for i, entry in enumerate(entries):
        if type(entry) is not dict:
            raise ValueError("manifest entry must be object")
        expected = {
            "split": split,
            "state_index": i,
            "state_spec_id": f"{split}:{i:03d}",
            "independent_statistical_unit": "state",
            "rows_and_ticks_role": "within_state_observations_only",
            "source_role": "development_nonholdout",
            "source_sampler": "predeclared_chronological_route_state_sampler_v1",
            "source_state_ordinal": base_ordinal + i,
            "family": "four_track_highway",
            "tier": tiers[i % 4],
            "route_id": (
                "1962e44a5dd0ace089aeb9011d5b70e05dfa6ae5adeec4450a6c20e3e09776b2"
            ),
            "route_sha256": EXPECTED_ROUTE_SHA,
            "map_geometry_sha256": EXPECTED_MAP_SHA,
            "scenario_seed": scenario_seed_base + i,
            "latent_policy": "row0_zero_rows1_7_philox_normal_float32_v1",
            "latent_seed": latent_seed_base + i,
            "candidate_k": 8,
        }
        if entry.get("state_spec_sha256") != _sha(expected):
            raise ValueError("manifest entry SHA drifted")
        expected["state_spec_sha256"] = _sha(expected)
        if entry != expected:
            raise ValueError("manifest entry literal drifted")


def _obj(parent: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if type(value) is not dict:
        raise ValueError(f"{key} must be object")
    return value
