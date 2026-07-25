"""Outcome-independent contract for the V25 fair nonholdout validation.

This module freezes architecture, denominator, latency and hard-stop semantics.
It does not load a model, execute a selector, read Fresh/B4 outcomes, or
authorize a scientific effect claim.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


CONTRACT_SCHEMA = "camp_dp_v25_fair_nonholdout_contract_v1"
GENERATOR_NAME = "new_single_invocation_batched_k8_candidate_pool"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_CAMP_HEAD = "540dca71136cd43da4bc045369e28c3d6030b232"
ROUTE_SHA256 = "63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd"
STATE_COUNT = 16
TICKS_PER_CLOSED_LOOP_ARM = 64
ARMS = ("pool_matched_candidate0", "Static14D", "Scene14D")
ATOL = 1e-5
RTOL = 1e-5

IMMUTABLE_ROOTS = {
    "target_architecture_amendment": (
        "3cfba03b2fd21cfa068610f8989f0c2b1df890cf64f6b1ac4b10eae67e291c7b"
    ),
    "target_architecture_amendment_review": (
        "202461e5045bba42cb10ad7bbdb03c36b82c00defce2df60edd6a971d1d2fd8f"
    ),
    "same_ego_k8_capability": (
        "fa94808c70ce1953d50b52497f9c4d056dabccd96e3ffdaed84faead5f2ed8e6"
    ),
    "same_ego_k8_capability_review": (
        "cb9f4efd5d72962513ea83777a68f3ffa5455fd731bc1cc5859b407cd9d25ac1"
    ),
    "b4_execution": (
        "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881"
    ),
    "b4_execution_review": (
        "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d"
    ),
    "corrected_evaluation": (
        "4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f"
    ),
    "corrected_evaluation_review": (
        "94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459"
    ),
    "evaluation_v2_second_correction": (
        "4fffc63bbeef6c2f6c0f26d8fb8b5af2842ad6e8c998a0ed04342aff73134941"
    ),
    "evaluation_v2_second_correction_review": (
        "e1df26f72402745aa68041a068b347b6fd1dad1abe9ed173baf05571c666427b"
    ),
}


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
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def fair_nonholdout_contract() -> dict[str, Any]:
    state_ordinals = list(range(STATE_COUNT))
    return {
        "schema_version": CONTRACT_SCHEMA,
        "status": "frozen_outcome_independent_fair_nonholdout_contract",
        "source_authority": {
            "camp_head": SOURCE_CAMP_HEAD,
            "fixed_dp_head": FIXED_DP_HEAD,
            "immutable_roots": dict(IMMUTABLE_ROOTS),
            "continuation_ledger_sha256": (
                "727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392"
            ),
            "fresh_or_b4_raw_outcome_read": False,
            "old_artifact_or_cas_write_allowed": False,
        },
        "generator": {
            "name": GENERATOR_NAME,
            "formal_entrypoint": "Diffusion_Planner.forward(inputs)",
            "same_ego_candidate_axis": True,
            "agent_as_ego_axis": False,
            "candidate_count": 8,
            "model_invocations_per_pool": 1,
            "latent_policy": (
                "candidate_latents(candidate_seed(24001,route_sha256,tick),"
                "noise_scale=1.0);row0_zero"
            ),
            "temperature_policy": "not_exposed_by_fixed_dp_formal_interface",
            "operational_default_batch_size": 1,
            "operational_default_natively_had_k8_claimed": False,
            "fixed_dp_source_or_checkpoint_change_allowed": False,
        },
        "state_matched_selector_replay": {
            "role": "development_nonholdout",
            "route_sha256": ROUTE_SHA256,
            "state_ordinals": state_ordinals,
            "state_count": STATE_COUNT,
            "authoritative_pool_count": STATE_COUNT,
            "pool_generated_once_per_state_for_three_selectors": True,
            "arms": list(ARMS),
            "baseline_rule": "frozen_row0",
            "static_and_scene_execute_real_canonical_selector": True,
            "required_receipts": [
                "state_and_input_sha256",
                "model_checkpoint_forward_and_pool_ids",
                "candidate_and_row_sha256",
                "candidate_neighbor_tensor_sha256",
                "atom_matrix_and_masks",
                "context_and_weights",
                "scores_and_selected_index_and_row_sha256",
                "selection_flip_vs_row0",
                "post_pool_zero_call_counts",
                "stage_latency_ms",
            ],
            "post_pool_required_counts": {
                "dp_or_model_calls": 0,
                "latent_replacements": 0,
                "candidate_generations": 0,
            },
            "candidate_tensor_immutable_required": True,
        },
        "pool_distribution_adaptation_audit": {
            "state_ordinals": state_ordinals,
            "state_count": STATE_COUNT,
            "comparison": (
                "same_state_same_latent_single_invocation_batch8_vs_"
                "eight_batch1_diagnostic_calls"
            ),
            "trajectory_atol": ATOL,
            "trajectory_rtol": RTOL,
            "neighbor_atol": ATOL,
            "neighbor_rtol": RTOL,
            "required_reports": [
                "per_state_per_row_trajectory_max_abs_error",
                "per_state_per_row_neighbor_max_abs_error",
                "trajectory_equivalence_rate",
                "neighbor_equivalence_rate",
                "k8_finiteness_and_diversity",
                "failure_taxonomy",
                "atom_mask_score_and_selected_index_differences",
            ],
            "substantive_drift_definition": {
                "any_trajectory_row_outside_tolerance": True,
                "any_neighbor_row_outside_tolerance": True,
                "any_source_or_eligibility_mask_difference": True,
                "any_static_or_scene_selected_index_flip": True,
            },
            "single_state_generalization_allowed": False,
            "training_authorized": False,
        },
        "compute_matched_closed_loop": {
            "entry_requires_contract_review_pass": True,
            "entry_requires_selector_replay_pass": True,
            "entry_requires_adaptation_audit_no_substantive_drift": True,
            "role": "development_nonholdout",
            "route_sha256": ROUTE_SHA256,
            "arms": list(ARMS),
            "arm_run_count": 3,
            "ticks_per_arm": TICKS_PER_CLOSED_LOOP_ARM,
            "planned_tick_denominator": 3 * TICKS_PER_CLOSED_LOOP_ARM,
            "each_arm_own_branched_state": True,
            "same_generator_k8_latent_policy_and_compute_budget": True,
            "post_divergence_cross_arm_tensor_identity_claimed": False,
            "retain_all_terminal_failures": True,
            "complete_case_shrinkage_allowed": False,
            "endpoint_semantics": (
                "frozen_evaluation_v2_endpoint_vector_engineering_only"
            ),
            "confirmatory_or_fresh_claim_authorized": False,
        },
        "latency_accounting": {
            "pool_matched_stages": [
                "pool_generation",
                "atoms",
                "context",
                "weights",
                "selector_incremental",
                "end_to_end",
            ],
            "baseline_includes_pool_generation": True,
            "baseline_uncalled_stages_are_na_not_zero": True,
            "operational_single_output_reference_separate": True,
            "operational_single_output_is_pool_matched_baseline": False,
        },
        "hard_stop": {
            "any_post_pool_forbidden_call": True,
            "batch8_nondeterministic_or_not_diverse": True,
            "adaptation_substantive_drift": True,
            "fixed_dp_source_checkpoint_or_head_drift": True,
            "weights_theta_atoms_or_scales_change_required": True,
            "sealed_authority_anomaly": True,
        },
        "claim_boundary": {
            "scientific_contract_status": "scientific_contract_review_required",
            "qualification_only": True,
            "fresh_authorized": False,
            "holdout_authorized": False,
            "training_or_retraining_authorized": False,
            "confirmatory_effect_claim_authorized": False,
            "promotion_deployment_or_online_activation_authorized": False,
            "legacy_claim_decision": (
                "honest_no_claim_under_frozen_preregistered_all_gate"
            ),
            "ultra_submission_authorized": False,
        },
    }


def validate_fair_nonholdout_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError("fair nonholdout contract must be a plain object")
    candidate = dict(value)
    if candidate != fair_nonholdout_contract():
        raise ValueError("fair nonholdout contract literal drifted")
    return candidate


def validate_zero_call_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError("zero-call receipt must be a plain object")
    receipt = dict(value)
    required = {
        "pool_id",
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "input_sha256",
        "model_sha256",
        "checkpoint_sha256",
        "forward_invocation_id",
        "dp_or_model_calls_after_pool",
        "latent_replacements_after_pool",
        "candidate_generations_after_pool",
    }
    if set(receipt) != required:
        raise ValueError("zero-call receipt field inventory drifted")
    for name in (
        "pool_id",
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "input_sha256",
        "model_sha256",
        "checkpoint_sha256",
        "forward_invocation_id",
    ):
        _sha(receipt[name], name)
    if (
        receipt["candidate_tensor_sha256_before"]
        != receipt["candidate_tensor_sha256_after"]
    ):
        raise ValueError("selector mutated candidate tensor")
    if any(
        receipt[name] != 0
        for name in (
            "dp_or_model_calls_after_pool",
            "latent_replacements_after_pool",
            "candidate_generations_after_pool",
        )
    ):
        raise ValueError("selector made a forbidden post-pool call")
    return receipt


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64:
        raise ValueError(f"{label} must be SHA256")
    int(value, 16)
    return value
