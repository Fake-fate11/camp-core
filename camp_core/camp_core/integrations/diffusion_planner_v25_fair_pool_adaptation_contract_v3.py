"""Executable pre-acquisition V25 fair-pool adaptation contract v3.

v3 is an additive correction to the sealed v2 diagnostic.  It makes the
input-only authority reconstructive and makes the qualification decision
phase-aware.  It does not authorize acquisition or any model execution.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_contract_v2 import (
    action_equivalent,
    adaptation_contract_v2,
    clopper_pearson_upper,
    sha256_json,
)


SCHEMA_VERSION = "camp_dp_v25_fair_pool_adaptation_contract_v3"
QUALIFICATION_RECEIPT_SCHEMA_VERSION = (
    "camp_dp_v25_fair_pool_adaptation_qualification_receipt_v3"
)
V2_CONTRACT_ROOT = (
    "f2314088f25c601ae80fa022dd0b4a513c29d07a54b7008c17be6644c078e9e1"
)
V2_REVIEW_ROOT = (
    "ca0bd63c057f0e58dc88d278c4f45b713f93b408b22ab33c122dfa4567ecab6b"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
GENERATOR_NAME = "new_single_invocation_batched_k8_candidate_pool"
INPUT_MANIFEST_MODULE = (
    Path(__file__).resolve().with_name(
        "diffusion_planner_v25_fair_pool_input_manifest_v2.py"
    )
)
PHASES = ("sequential_within", "batch8_within", "cross_mode")
MODE_BY_PHASE = {
    "sequential_within": "sequential_batch1_x8",
    "batch8_within": "single_invocation_batch8",
    "cross_mode": "matched_repeat_cross_mode",
}
WITHIN_NUMERIC_IDS = (
    *(f"atom.normalized_delta.{index:02d}.{name}" for index, name in enumerate(
        (
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
    )),
    "trajectory.ego.position_max_m",
    "trajectory.ego.heading_max_rad",
    "trajectory.ego.speed_max_mps",
    "trajectory.neighbor.position_max_m",
    "trajectory.neighbor.heading_max_rad",
    "trajectory.neighbor.speed_max_mps",
    "score.static14d.abs_delta",
    "score.scene14d.abs_delta",
)
CROSS_ONLY_NUMERIC_IDS = (
    "score.static14d.within_mode_normalized_delta",
    "score.static14d.margin_ratio",
    "score.static14d.rank_error",
    "score.scene14d.within_mode_normalized_delta",
    "score.scene14d.margin_ratio",
    "score.scene14d.rank_error",
    "neighbor.relative_within_mode_inflation",
)
CROSS_NUMERIC_IDS = (*WITHIN_NUMERIC_IDS, *CROSS_ONLY_NUMERIC_IDS)
HARD_RESULT_KEYS = (
    ("sequential_within", "sequential_batch1_x8", "k8.finite_and_diverse"),
    ("sequential_within", "sequential_batch1_x8", "authority.fingerprint"),
    ("batch8_within", "single_invocation_batch8", "k8.finite_and_diverse"),
    ("batch8_within", "single_invocation_batch8", "authority.fingerprint"),
    ("global", "none", "split.input_only_clone_nonoverlap"),
    ("cross_mode", "matched_repeat_cross_mode", "pool.tensor_immutability_and_zero_calls"),
    ("cross_mode", "matched_repeat_cross_mode", "functional.static14d.mask_eligibility"),
    ("cross_mode", "matched_repeat_cross_mode", "functional.scene14d.mask_eligibility"),
    ("cross_mode", "matched_repeat_cross_mode", "functional.static14d.selected_index_action"),
    ("cross_mode", "matched_repeat_cross_mode", "functional.scene14d.selected_index_action"),
)


def adaptation_contract_v3() -> dict[str, Any]:
    inherited = adaptation_contract_v2()
    registry = _phase_registry(inherited["endpoint_registry"])
    sampler_sha = hashlib.sha256(INPUT_MANIFEST_MODULE.read_bytes()).hexdigest()
    specs = {
        split: _state_specs(split, sampler_sha)
        for split in ("development_calibration", "independent_validation")
    }
    contract = {
        "schema_version": SCHEMA_VERSION,
        "status": "frozen_executable_design_only_acquisition_unauthorized",
        "superseded_preacquisition_diagnostics": {
            "v1_contract_root_sha256": inherited[
                "superseded_preacquisition_diagnostic"
            ]["root_sha256"],
            "v1_review_root_sha256": inherited[
                "superseded_preacquisition_diagnostic"
            ]["review_root_sha256"],
            "v2_contract_root_sha256": V2_CONTRACT_ROOT,
            "v2_review_root_sha256": V2_REVIEW_ROOT,
        },
        "inherited_v2_payload_sha256": inherited["contract_payload_sha256"],
        "scope": {
            "generator": GENERATOR_NAME,
            "coverage": (
                "single_route_single_map_bounded_development_nonholdout_"
                "four_density_tiers_only"
            ),
            "pass_interpretation": (
                "within_this_single_route_bounded_scope_only_current_"
                "evidence_does_not_trigger_retraining"
            ),
            "general_ood_or_architecture_equivalence_claim": False,
        },
        "input_authority": {
            "module_path": (
                "camp_core/camp_core/integrations/"
                "diffusion_planner_v25_fair_pool_input_manifest_v2.py"
            ),
            "module_sha256": sampler_sha,
            "source_scene_entrypoint": "materialize_exact_source_scene",
            "manifest_entrypoint": "materialize_input_only_manifest",
            "preflight_entrypoint": "validate_preflight_receipt",
            "source_scene_schema": (
                "camp_dp_v25_fair_pool_deterministic_source_scene_v1"
            ),
            "manifest_schema": (
                "camp_dp_v25_fair_pool_input_only_manifest_v2"
            ),
            "preflight_schema": (
                "camp_dp_v25_fair_pool_input_only_preflight_receipt_v2"
            ),
            "authorized_contract_binding": (
                "receipt_contract_root_equals_separately_authorized_exact_"
                "contract_root_and_review_root"
            ),
            "b4_forbidden_inventory": (
                "rederived_inside_validator_from_exact_sealed_prepared_"
                "runtime_cases_bytes"
            ),
            "source_scene_algorithm": {
                "route_asset_sha256": (
                    "63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd"
                ),
                "map_asset_sha256": (
                    "c13a9234727186c77c019766c3358c30faf10af61503a566f0fff0963be53bbd"
                ),
                "route_lanelet_ids": [3002178, 3002181, 3002185],
                "ordered_route_point_count": 26,
                "spawn_goal": "exact_float64_literals_from_sealed_route_asset",
                "actor_rng": "numpy_Generator_PCG64DXSM_scenario_seed",
                "actor_count_by_tier": {
                    "no_npc": 0,
                    "low_density": 2,
                    "medium_density": 4,
                    "high_density": 6,
                },
                "actor_position": (
                    "even_route_arc_slots_plus_uniform_closed_open_"
                    "minus_0_01_plus_0_01_then_lateral_choice_minus_1_5_"
                    "or_plus_1_5"
                ),
                "actor_speed": "uniform_closed_open_3_0_12_0_mps",
                "actor_dimensions": "vehicle_length_4_5m_width_2_0m",
                "caller_supplied_source_record_allowed": False,
            },
            "actual_preimages": {
                "input_tensor_bundle": (
                    "sorted_name_dtype_shape_raw_c_bytes_sha256_and_bundle_"
                    "sha256_bound_to_source_scene_sha256"
                ),
                "tensor_converter_path": (
                    "scenario_generation/tensor_converter.py"
                ),
                "tensor_converter_sha256": (
                    "af0a087dcfa910e5f0ad4732c5d1ebabb2fe5c41d2d61a4aa7aaf0f4351d36a7"
                ),
                "tensor_converter_entrypoint": "to_model_tensors",
                "state_sha256": "canonical_source_scene_sha256",
                "latent_shape": [8, 321, 81, 4],
                "latent_dtype": "<f4",
                "latent_policy": (
                    "row0_zero_rows1_7_numpy_default_rng_pcg64_"
                    "standard_normal_float32_v1"
                ),
                "latent_bytes": "C_order_little_endian_float32",
            },
            "manifest_validation": (
                "exact_schema_then_recompute_source_scene_tensor_bundle_"
                "latent_clone_payload_clone_key_and_outer_manifest_sha"
            ),
            "preflight_no_drop_replacement_or_suffix": True,
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
            "actual_manifest_count_now": 0,
            "independent_statistical_unit": "state",
            "rows_ticks_role": "within_state_observations_only",
        },
        "repeat_and_threshold_authority": deepcopy(
            inherited["repeat_authority"]
        ),
        "model_fingerprint_authority": {
            "fixed_dp_head": FIXED_DP_HEAD,
            "checkpoint_sha256": (
                "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75"
            ),
            "model_source_sha256": (
                "341c8f5798cae83fdee3ae7203243ab129458d8eab362e0c3a1c7daee08d502d"
            ),
            "decoder_source_sha256": (
                "8e81d1e9aa879dd0c0762d623dbe7480786e2618ccb261d10fd72cc00192e7dd"
            ),
            "encoder_source_sha256": (
                "360b3632cc0f9d65ffb25ed4adc906b498d824df0d4b6e37f5c59eb252f8daab"
            ),
            "formal_entrypoint": "Diffusion_Planner.forward(inputs)",
        },
        "threshold_algorithm": deepcopy(inherited["threshold_algorithm"]),
        "training_scale_authority": deepcopy(
            inherited["training_scale_authority"]
        ),
        "endpoint_registry": registry,
        "result_topology": {
            "key_fields": ["phase", "mode", "endpoint_id"],
            "numeric_evidence_exact_fields": [
                "phase",
                "mode",
                "endpoint_id",
                "state_values",
                "threshold",
                "threshold_authority",
            ],
            "sequential_within_numeric_ids": list(WITHIN_NUMERIC_IDS),
            "batch8_within_numeric_ids": list(WITHIN_NUMERIC_IDS),
            "cross_mode_numeric_ids": list(CROSS_NUMERIC_IDS),
            "cross_only_ids_forbidden_in_within": list(
                CROSS_ONLY_NUMERIC_IDS
            ),
            "hard_result_keys": [list(key) for key in HARD_RESULT_KEYS],
            "state_denominator": 64,
            "missing_or_nonfinite": "evidence_missing_no_complete_case",
            "unknown_duplicate_or_omitted_key": "fail_closed",
        },
        "typed_hard_evidence": {
            "fingerprints": (
                "expected_literal_mapping_plus_observed_mapping_per_mode;"
                "exact_equality_required"
            ),
            "k8": (
                "64_state_receipts_per_mode_each_finite_true_and_exactly_"
                "8_unique_lowercase_row_sha256"
            ),
            "pool": (
                "64_state_receipts_pre_tensor_sha_equals_post_tensor_sha_"
                "and_dp_model_latent_generation_calls_all_zero"
            ),
            "mask": (
                "64_state_receipts_per_arm_two_boolean_length8_vectors;"
                "array_equal"
            ),
            "action": (
                "64_state_receipts_per_arm_selected_indices_plus_two_80x4_"
                "finite_arrays_and_executable_terminal_enums;"
                "same_index_pass_else_frozen_action_equivalence"
            ),
            "split": (
                "validated_preflight_status_and_receipt_sha_bound_to_exact_"
                "contract_review_and_future_authority_roots"
            ),
            "caller_status_or_within_boolean_accepted": False,
        },
        "decision_table": {
            "derive_within_modes": (
                "all_required_phase_numeric_and_hard_statuses_computed_"
                "pass_for_each_mode"
            ),
            "cross_entry": (
                "derived_sequential_within_pass_and_derived_batch8_"
                "within_pass"
            ),
            "precedence": [
                "authority_failure",
                "evidence_missing",
                "within_mode_generator_instability",
                "cross_mode_functional_drift",
                "PASS",
            ],
            "weighted_total": False,
            "benefit_or_retraining_claim": False,
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
            "fresh_or_b4_outcome_read": False,
            "old_artifact_or_cas_written": False,
            "claim_authorized": False,
            "legacy_claim": (
                "honest_no_claim_under_frozen_preregistered_all_gate"
            ),
        },
    }
    contract["contract_payload_sha256"] = sha256_json(contract)
    return contract


def validate_contract_v3(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("contract v3 must be object")
    candidate = dict(value)
    supplied = candidate.pop("contract_payload_sha256", None)
    if supplied != sha256_json(candidate):
        raise ValueError("contract v3 payload SHA drifted")
    expected = adaptation_contract_v3()
    if dict(value) != expected:
        raise ValueError("contract v3 semantic reconstruction drifted")
    if inspect.signature(decide_qualification_v3).parameters.keys() != {
        "contract",
        "receipt",
    }:
        raise ValueError("decision API accepts caller trust parameter")
    return dict(value)


def expected_result_keys(
    contract: Mapping[str, Any],
) -> tuple[tuple[str, str, str], ...]:
    validate_contract_v3(contract)
    keys: list[tuple[str, str, str]] = []
    for endpoint_id in WITHIN_NUMERIC_IDS:
        keys.append(
            (
                "sequential_within",
                MODE_BY_PHASE["sequential_within"],
                endpoint_id,
            )
        )
        keys.append(
            (
                "batch8_within",
                MODE_BY_PHASE["batch8_within"],
                endpoint_id,
            )
        )
    for endpoint_id in CROSS_NUMERIC_IDS:
        keys.append(("cross_mode", MODE_BY_PHASE["cross_mode"], endpoint_id))
    keys.extend(HARD_RESULT_KEYS)
    if len(keys) != len(set(keys)):
        raise ValueError("phase result keys are not unique")
    return tuple(keys)


def decide_qualification_v3(
    contract: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    frozen = validate_contract_v3(contract)
    if type(receipt) is not dict or set(receipt) != {
        "schema_version",
        "contract_payload_sha256",
        "contract_root_sha256",
        "contract_review_root_sha256",
        "acquisition_authority_root_sha256",
        "numeric_evidence",
        "hard_evidence",
    }:
        raise ValueError("qualification receipt exact schema drifted")
    if receipt["schema_version"] != QUALIFICATION_RECEIPT_SCHEMA_VERSION:
        raise ValueError("qualification receipt schema drifted")
    if receipt["contract_payload_sha256"] != frozen[
        "contract_payload_sha256"
    ]:
        raise ValueError("qualification contract payload drifted")
    for field in (
        "contract_root_sha256",
        "contract_review_root_sha256",
        "acquisition_authority_root_sha256",
    ):
        _sha256(receipt[field], field)
    numeric = _derive_numeric_statuses(frozen, receipt["numeric_evidence"])
    hard = _derive_hard_statuses(frozen, receipt)
    derived = {**numeric, **hard}
    expected = set(expected_result_keys(frozen))
    if set(derived) != expected:
        missing = sorted(expected - set(derived))
        unknown = sorted(set(derived) - expected)
        raise ValueError(
            f"qualification result keyset drifted missing={missing} "
            f"unknown={unknown}"
        )
    status_values = set(derived.values())
    if "authority_failure" in status_values:
        return _decision("BLOCK", "authority_failure", derived)
    if "evidence_missing" in status_values:
        return _decision("BLOCK", "evidence_missing", derived)
    sequential_pass = all(
        status == "pass"
        for (phase, _mode, _endpoint), status in derived.items()
        if phase == "sequential_within"
    )
    batch8_pass = all(
        status == "pass"
        for (phase, _mode, _endpoint), status in derived.items()
        if phase == "batch8_within"
    )
    if not sequential_pass or not batch8_pass:
        return _decision(
            "BLOCK",
            "within_mode_generator_instability",
            derived,
        )
    cross_pass = all(
        status == "pass"
        for (phase, _mode, _endpoint), status in derived.items()
        if phase in {"cross_mode", "global"}
    )
    if not cross_pass:
        return _decision("BLOCK", "cross_mode_functional_drift", derived)
    return _decision("PASS", "bounded_scope_no_trigger", derived)


def _derive_numeric_statuses(
    contract: Mapping[str, Any],
    value: Any,
) -> dict[tuple[str, str, str], str]:
    expected_keys = {
        key
        for key in expected_result_keys(contract)
        if key[2]
        in set(WITHIN_NUMERIC_IDS).union(CROSS_ONLY_NUMERIC_IDS)
    }
    if type(value) is not list or len(value) != len(expected_keys):
        raise ValueError("numeric evidence denominator drifted")
    result: dict[tuple[str, str, str], str] = {}
    validation_ids = [
        row["state_spec_id"]
        for row in contract["state_specifications"][
            "independent_validation"
        ]
    ]
    for row in value:
        if type(row) is not dict or set(row) != {
            "phase",
            "mode",
            "endpoint_id",
            "state_values",
            "threshold",
            "threshold_authority",
        }:
            raise ValueError("numeric evidence exact fields drifted")
        key = (row["phase"], row["mode"], row["endpoint_id"])
        if key not in expected_keys or key in result:
            raise ValueError("numeric evidence key unknown or duplicate")
        expected_mode = MODE_BY_PHASE.get(row["phase"])
        if row["mode"] != expected_mode:
            raise ValueError("numeric evidence phase/mode drifted")
        state_values = row["state_values"]
        if type(state_values) is not list or len(state_values) != 64:
            raise ValueError("numeric state denominator drifted")
        if [
            item.get("state_spec_id") if type(item) is dict else None
            for item in state_values
        ] != validation_ids:
            raise ValueError("numeric state identity/order drifted")
        threshold = float(row["threshold"])
        if not math.isfinite(threshold) or threshold < 0.0:
            raise ValueError("numeric threshold drifted")
        authority = row["threshold_authority"]
        expected_authority = {
            "schema_version": (
                "camp_dp_v25_fair_pool_threshold_authority_v1"
            ),
            "phase": row["phase"],
            "mode": row["mode"],
            "endpoint_id": row["endpoint_id"],
            "calibration_state_count": 64,
            "threshold": threshold,
            "algorithm": (
                "q99_higher_then_10000_state_bootstrap_pcg64dxsm_"
                "seed825071_one_sided95_index9500_max_resolution_floor"
            ),
        }
        expected_authority["authority_sha256"] = sha256_json(
            expected_authority
        )
        if authority != expected_authority:
            raise ValueError("numeric threshold authority drifted")
        values: list[float] = []
        missing = False
        for item in state_values:
            if set(item) != {"state_spec_id", "value"}:
                raise ValueError("numeric state evidence schema drifted")
            if item["value"] is None:
                missing = True
                continue
            observed = float(item["value"])
            if not math.isfinite(observed):
                missing = True
                continue
            values.append(observed)
        if missing or len(values) != 64:
            result[key] = "evidence_missing"
            continue
        exceedance = sum(observed > threshold for observed in values)
        upper = clopper_pearson_upper(exceedance, 64)
        if exceedance <= 2 and upper <= 0.10:
            result[key] = "pass"
        elif row["phase"] in {
            "sequential_within",
            "batch8_within",
        }:
            result[key] = "within_mode_generator_instability"
        else:
            result[key] = "cross_mode_functional_drift"
    if set(result) != expected_keys:
        raise ValueError("numeric evidence required key omitted")
    return result


def _derive_hard_statuses(
    contract: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[tuple[str, str, str], str]:
    value = receipt["hard_evidence"]
    if type(value) is not dict or set(value) != {
        "fingerprints",
        "k8",
        "pool",
        "masks",
        "actions",
        "split_preflight",
    }:
        raise ValueError("typed hard evidence exact schema drifted")
    validation_ids = [
        row["state_spec_id"]
        for row in contract["state_specifications"][
            "independent_validation"
        ]
    ]
    result: dict[tuple[str, str, str], str] = {}
    expected_fingerprint = {
        "fixed_dp_head": FIXED_DP_HEAD,
        "generator": GENERATOR_NAME,
        "candidate_k": 8,
        "checkpoint_sha256": (
            "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75"
        ),
        "model_source_sha256": (
            "341c8f5798cae83fdee3ae7203243ab129458d8eab362e0c3a1c7daee08d502d"
        ),
        "decoder_source_sha256": (
            "8e81d1e9aa879dd0c0762d623dbe7480786e2618ccb261d10fd72cc00192e7dd"
        ),
        "encoder_source_sha256": (
            "360b3632cc0f9d65ffb25ed4adc906b498d824df0d4b6e37f5c59eb252f8daab"
        ),
        "route_asset_sha256": contract["input_authority"][
            "source_scene_algorithm"
        ]["route_asset_sha256"],
        "map_geometry_sha256": contract["input_authority"][
            "source_scene_algorithm"
        ]["map_asset_sha256"],
        "dtype": "float32",
    }
    fingerprints = value["fingerprints"]
    if type(fingerprints) is not dict or set(fingerprints) != {
        "expected",
        "observed_by_mode",
    }:
        raise ValueError("fingerprint evidence schema drifted")
    fingerprint_ok = fingerprints["expected"] == expected_fingerprint
    observed = fingerprints["observed_by_mode"]
    if type(observed) is not dict or set(observed) != {
        "sequential_batch1_x8",
        "single_invocation_batch8",
    }:
        raise ValueError("fingerprint mode evidence drifted")
    for phase in ("sequential_within", "batch8_within"):
        mode = MODE_BY_PHASE[phase]
        status = (
            "pass"
            if fingerprint_ok and observed[mode] == expected_fingerprint
            else "authority_failure"
        )
        result[(phase, mode, "authority.fingerprint")] = status
    k8 = value["k8"]
    if type(k8) is not dict or set(k8) != set(observed):
        raise ValueError("K8 mode evidence drifted")
    for phase in ("sequential_within", "batch8_within"):
        mode = MODE_BY_PHASE[phase]
        rows = k8[mode]
        if type(rows) is not list or len(rows) != 64:
            raise ValueError("K8 state denominator drifted")
        good = True
        for state_id, row in zip(validation_ids, rows):
            if type(row) is not dict or set(row) != {
                "state_spec_id",
                "all_finite",
                "row_sha256",
            }:
                raise ValueError("K8 typed evidence schema drifted")
            shas = row["row_sha256"]
            if (
                row["state_spec_id"] != state_id
                or row["all_finite"] is not True
                or type(shas) is not list
                or len(shas) != 8
                or len(set(shas)) != 8
            ):
                good = False
            else:
                for digest in shas:
                    _sha256(digest, "K8 row")
        result[(phase, mode, "k8.finite_and_diverse")] = (
            "pass" if good else "within_mode_generator_instability"
        )
    pool_rows = value["pool"]
    if type(pool_rows) is not list or len(pool_rows) != 64:
        raise ValueError("pool hard evidence denominator drifted")
    pool_good = True
    for state_id, row in zip(validation_ids, pool_rows):
        if type(row) is not dict or set(row) != {
            "state_spec_id",
            "pre_tensor_sha256",
            "post_tensor_sha256",
            "dp_model_call_count_after_pool",
            "latent_replacement_count_after_pool",
            "candidate_generation_count_after_pool",
        }:
            raise ValueError("pool typed evidence schema drifted")
        if row["state_spec_id"] != state_id:
            raise ValueError("pool state identity/order drifted")
        pre = _sha256(row["pre_tensor_sha256"], "pre-pool tensor")
        post = _sha256(row["post_tensor_sha256"], "post-pool tensor")
        pool_good &= (
            pre == post
            and row["dp_model_call_count_after_pool"] == 0
            and row["latent_replacement_count_after_pool"] == 0
            and row["candidate_generation_count_after_pool"] == 0
        )
    result[
        (
            "cross_mode",
            MODE_BY_PHASE["cross_mode"],
            "pool.tensor_immutability_and_zero_calls",
        )
    ] = "pass" if pool_good else "authority_failure"
    masks = value["masks"]
    actions = value["actions"]
    if type(masks) is not dict or set(masks) != {"static14d", "scene14d"}:
        raise ValueError("mask arm evidence drifted")
    if type(actions) is not dict or set(actions) != {"static14d", "scene14d"}:
        raise ValueError("action arm evidence drifted")
    for arm in ("static14d", "scene14d"):
        mask_rows = masks[arm]
        if type(mask_rows) is not list or len(mask_rows) != 64:
            raise ValueError("mask state denominator drifted")
        mask_good = True
        for state_id, row in zip(validation_ids, mask_rows):
            if type(row) is not dict or set(row) != {
                "state_spec_id",
                "sequential_mask",
                "batch8_mask",
            }:
                raise ValueError("mask typed evidence schema drifted")
            left = np.asarray(row["sequential_mask"])
            right = np.asarray(row["batch8_mask"])
            if (
                row["state_spec_id"] != state_id
                or left.shape != (8,)
                or right.shape != (8,)
                or left.dtype != np.bool_
                or right.dtype != np.bool_
                or not np.array_equal(left, right)
            ):
                mask_good = False
        result[
            (
                "cross_mode",
                MODE_BY_PHASE["cross_mode"],
                f"functional.{arm}.mask_eligibility",
            )
        ] = "pass" if mask_good else "cross_mode_functional_drift"
        action_rows = actions[arm]
        if type(action_rows) is not list or len(action_rows) != 64:
            raise ValueError("action state denominator drifted")
        action_good = True
        for state_id, row in zip(validation_ids, action_rows):
            if type(row) is not dict or set(row) != {
                "state_spec_id",
                "sequential_selected_index",
                "batch8_selected_index",
                "sequential_action_80x4",
                "batch8_action_80x4",
                "sequential_executable",
                "batch8_executable",
                "sequential_terminal",
                "batch8_terminal",
            }:
                raise ValueError("action typed evidence schema drifted")
            if row["state_spec_id"] != state_id:
                raise ValueError("action state identity/order drifted")
            left_index = row["sequential_selected_index"]
            right_index = row["batch8_selected_index"]
            if (
                type(left_index) is not int
                or type(right_index) is not int
                or not 0 <= left_index < 8
                or not 0 <= right_index < 8
            ):
                raise ValueError("selected index drifted")
            comparison = action_equivalent(
                np.asarray(row["sequential_action_80x4"], dtype=np.float64),
                np.asarray(row["batch8_action_80x4"], dtype=np.float64),
                left_executable=row["sequential_executable"],
                right_executable=row["batch8_executable"],
                left_terminal=row["sequential_terminal"],
                right_terminal=row["batch8_terminal"],
            )
            action_good &= (
                left_index == right_index or comparison["status"] == "pass"
            )
        result[
            (
                "cross_mode",
                MODE_BY_PHASE["cross_mode"],
                f"functional.{arm}.selected_index_action",
            )
        ] = "pass" if action_good else "cross_mode_functional_drift"
    split = value["split_preflight"]
    if type(split) is not dict or set(split) != {
        "status",
        "receipt_sha256",
        "contract_root_sha256",
        "contract_review_root_sha256",
        "acquisition_authority_root_sha256",
    }:
        raise ValueError("split preflight typed evidence schema drifted")
    split_good = (
        split["status"] == "passed_before_first_model_pool_selector_call"
        and _sha256(split["receipt_sha256"], "preflight receipt")
        == split["receipt_sha256"]
        and split["contract_root_sha256"]
        == receipt["contract_root_sha256"]
        and split["contract_review_root_sha256"]
        == receipt["contract_review_root_sha256"]
        and split["acquisition_authority_root_sha256"]
        == receipt["acquisition_authority_root_sha256"]
    )
    result[("global", "none", "split.input_only_clone_nonoverlap")] = (
        "pass" if split_good else "authority_failure"
    )
    return result


def _decision(
    status: str,
    classification: str,
    derived: Mapping[tuple[str, str, str], str],
) -> dict[str, Any]:
    return {
        "status": status,
        "classification": classification,
        "derived_within_mode_pass": {
            "sequential_batch1_x8": all(
                value == "pass"
                for (phase, _mode, _endpoint), value in derived.items()
                if phase == "sequential_within"
            ),
            "single_invocation_batch8": all(
                value == "pass"
                for (phase, _mode, _endpoint), value in derived.items()
                if phase == "batch8_within"
            ),
        },
        "cross_mode_entered": (
            all(
                value == "pass"
                for (phase, _mode, _endpoint), value in derived.items()
                if phase == "sequential_within"
            )
            and all(
                value == "pass"
                for (phase, _mode, _endpoint), value in derived.items()
                if phase == "batch8_within"
            )
        ),
        "derived_result_count": len(derived),
        "caller_supplied_status_or_within_boolean_used": False,
    }


def _phase_registry(
    inherited_registry: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    for inherited in inherited_registry:
        row = {
            key: deepcopy(value)
            for key, value in inherited.items()
            if key not in {"within_mode_required", "cross_mode_required"}
        }
        endpoint_id = row["id"]
        if endpoint_id in CROSS_ONLY_NUMERIC_IDS or endpoint_id.startswith(
            "functional."
        ) or endpoint_id == "pool.tensor_immutability_and_zero_calls":
            phases = [["cross_mode", MODE_BY_PHASE["cross_mode"]]]
        elif endpoint_id == "split.input_only_clone_nonoverlap":
            phases = [["global", "none"]]
        elif endpoint_id in {
            "k8.finite_and_diverse",
            "authority.fingerprint",
        }:
            phases = [
                ["sequential_within", MODE_BY_PHASE["sequential_within"]],
                ["batch8_within", MODE_BY_PHASE["batch8_within"]],
            ]
        else:
            phases = [
                ["sequential_within", MODE_BY_PHASE["sequential_within"]],
                ["batch8_within", MODE_BY_PHASE["batch8_within"]],
                ["cross_mode", MODE_BY_PHASE["cross_mode"]],
            ]
        row["applicable_phase_mode"] = phases
        row["caller_status_accepted"] = False
        row["inherited_v2_row_sha256"] = sha256_json(inherited)
        result.append(row)
    return result


def _state_specs(split: str, sampler_sha: str) -> list[dict[str, Any]]:
    if split not in {"development_calibration", "independent_validation"}:
        raise ValueError(split)
    base = 0 if split == "development_calibration" else 64
    scenario_base = 41000 if split == "development_calibration" else 51000
    latent_base = 61000 if split == "development_calibration" else 71000
    tiers = ("no_npc", "low_density", "medium_density", "high_density")
    result = []
    for index in range(64):
        payload = {
            "split": split,
            "state_spec_id": f"{split}:{index:03d}",
            "state_index": index,
            "source_state_ordinal": base + index,
            "source_role": "development_nonholdout",
            "source_sampler_module_sha256": sampler_sha,
            "route_asset_sha256": (
                "63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd"
            ),
            "map_geometry_sha256": (
                "c13a9234727186c77c019766c3358c30faf10af61503a566f0fff0963be53bbd"
            ),
            "family": "four_track_highway",
            "tier": tiers[index % 4],
            "scenario_seed": scenario_base + index,
            "latent_seed": latent_base + index,
            "latent_policy": (
                "row0_zero_rows1_7_numpy_default_rng_pcg64_"
                "standard_normal_float32_v1"
            ),
            "candidate_k": 8,
            "independent_statistical_unit": "state",
        }
        payload["state_spec_sha256"] = sha256_json(payload)
        result.append(payload)
    return result


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be lowercase SHA256")
    return value
