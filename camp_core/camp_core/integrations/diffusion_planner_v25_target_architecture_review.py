"""Reviewer-local literal oracles for the V25 target architecture.

This module intentionally does not import
``diffusion_planner_v25_target_architecture``.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


AMENDMENT_SCHEMA = "camp_dp_v25_target_architecture_amendment_v1"
CAPABILITY_SCHEMA = "camp_dp_v25_same_ego_single_invocation_k8_capability_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
LEGACY_DECISION = "honest_no_claim_under_frozen_preregistered_all_gate"
EXPECTED_ROOTS = {
    "b4_execution": "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881",
    "b4_execution_review": "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d",
    "corrected_evaluation": "4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f",
    "corrected_evaluation_review": "94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459",
    "evaluation_v2_second_correction": "4fffc63bbeef6c2f6c0f26d8fb8b5af2842ad6e8c998a0ed04342aff73134941",
    "evaluation_v2_second_correction_review": "e1df26f72402745aa68041a068b347b6fd1dad1abe9ed173baf05571c666427b",
}
CONTINUATION_SHA = (
    "727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392"
)


def independently_review_amendment(value: Mapping[str, Any]) -> dict[str, Any]:
    report = _object(value, "amendment")
    _exact_keys(
        report,
        {
            "schema_version",
            "status",
            "outcome_independent",
            "superseding_additive_classification",
            "immutable_evidence",
            "capability_contract",
            "selector_after_pool_contract",
            "fairness_contract_draft",
            "training_decision",
            "claim_boundary",
        },
        "amendment",
    )
    if (
        report["schema_version"] != AMENDMENT_SCHEMA
        or report["status"] != "scientific_contract_review_required"
        or report["outcome_independent"] is not True
    ):
        raise ValueError("amendment identity drifted")
    classification = _object(
        report["superseding_additive_classification"], "classification"
    )
    if (
        classification.get("existing_b4_architecture_class")
        != "compute_augmented_candidate_expansion_plus_reranking"
        or classification.get("existing_b4_target_architecture_evidence") is not False
        or classification.get("existing_b4_preserved_as_exploratory_diagnostic")
        is not True
        or classification.get("target_architecture_class")
        != "single_model_invocation_same_ego_k8_pool_then_camp_rerank_select"
        or classification.get("selector_may_generate_candidates") is not False
        or classification.get("selector_model_call_count_required") != 0
        or classification.get("operational_default_batch_size") != 1
        or classification.get("operational_default_previously_had_k8") is not False
    ):
        raise ValueError("architecture classification literal oracle failed")
    immutable = _object(report["immutable_evidence"], "immutable evidence")
    if (
        immutable.get("roots") != EXPECTED_ROOTS
        or immutable.get("continuation_ledger_sha256") != CONTINUATION_SHA
        or immutable.get("fixed_dp_head") != FIXED_DP_HEAD
        or immutable.get("legacy_claim_decision") != LEGACY_DECISION
        or immutable.get("legacy_values_mutated") is not False
        or immutable.get("sealed_artifacts_or_cas_written") is not False
    ):
        raise ValueError("immutable evidence literal oracle failed")
    capability = _object(report["capability_contract"], "capability contract")
    if (
        capability.get("development_nonholdout_only") is not True
        or capability.get("same_ego_source_batch_size") != 1
        or capability.get("candidate_axis")
        != "expanded_same_ego_model_batch_axis"
        or capability.get("candidate_count") != 8
        or capability.get("primary_pool_model_invocation_count") != 1
        or capability.get("diagnostic_repeat_model_invocation_count") != 1
        or capability.get("diagnostic_sequential_model_invocation_count") != 8
        or capability.get("fixed_dp_source_or_weights_modification_allowed")
        is not False
    ):
        raise ValueError("capability contract literal oracle failed")
    selector = _object(
        report["selector_after_pool_contract"], "selector contract"
    )
    if (
        selector.get("arms")
        != ["pool_baseline", "Static14D", "Scene14D"]
        or selector.get("all_arms_same_pool_sha_required") is not True
        or selector.get("selector_model_call_count_required") != 0
        or selector.get("latent_replacement_allowed") is not False
        or selector.get("model_callback_allowed") is not False
        or selector.get("trajectory_generation_allowed") is not False
        or selector.get("baseline_rule")
        != "row0_outcome_independent_qualification_rule"
        or selector.get("outcome_selected_rule") is not False
    ):
        raise ValueError("selector contract literal oracle failed")
    fairness = _object(report["fairness_contract_draft"], "fairness draft")
    if (
        fairness.get("status") != "draft_frozen_not_executed"
        or fairness.get("state_matched_offline_selector_replay", {}).get(
            "same_k8_tensor"
        )
        is not True
        or fairness.get("compute_matched_closed_loop", {}).get(
            "post_divergence_cross_arm_tensor_identity_claimed"
        )
        is not False
        or fairness.get("latency_accounting", {}).get(
            "baseline_includes_pool_generation_cost"
        )
        is not True
        or fairness.get("statistics_endpoints_claim", {}).get("authorized")
        is not False
    ):
        raise ValueError("fairness draft literal oracle failed")
    claim = _object(report["claim_boundary"], "claim boundary")
    if (
        claim.get("new_scientific_effect_claim_authorized") is not False
        or claim.get("fresh_authorized") is not False
        or claim.get("closed_loop_authorized") is not False
        or claim.get("training_authorized") is not False
        or claim.get("promotion_or_deployment_authorized") is not False
    ):
        raise ValueError("amendment claim boundary failed")
    return report


def independently_review_capability(value: Mapping[str, Any]) -> dict[str, Any]:
    report = _object(value, "capability")
    _exact_keys(
        report,
        {
            "schema_version",
            "status",
            "authority",
            "fixed_dp",
            "source_state",
            "candidate_axis",
            "latent",
            "temperature",
            "primary_pool_invocation",
            "determinism",
            "batch_vs_sequential",
            "selector_after_pool",
            "rng_boundary",
            "training_decision",
            "claim_boundary",
        },
        "capability",
    )
    if (
        report["schema_version"] != CAPABILITY_SCHEMA
        or report["status"]
        != "passed_same_ego_single_invocation_k8_capability"
    ):
        raise ValueError("capability did not pass")
    fixed = _object(report["fixed_dp"], "fixed_dp")
    for field in (
        "head",
        "repo",
        "checkpoint_path",
        "checkpoint_sha256",
        "args_path",
        "args_sha256",
        "model_source_sha256",
        "decoder_source_sha256",
        "encoder_source_sha256",
    ):
        if field not in fixed:
            raise ValueError(f"fixed DP field missing: {field}")
    if (
        fixed["head"] != FIXED_DP_HEAD
        or fixed.get("source_modified") is not False
        or fixed.get("checkpoint_modified") is not False
    ):
        raise ValueError("fixed DP provenance drifted")
    state = _object(report["source_state"], "source_state")
    if (
        state.get("role") != "development_nonholdout"
        or state.get("route_role") != "v24_source_only_single_record_probe"
        or state.get("simulator_steps_advanced") != 0
        or state.get("source_batch_size") != 1
        or state.get("holdout_or_fresh_accessed") is not False
    ):
        raise ValueError("source state role drifted")
    axis = _object(report["candidate_axis"], "candidate_axis")
    if (
        axis.get("semantics") != "same_ego_candidate_batch"
        or axis.get("candidate_count") != 8
        or axis.get("agent_as_ego_batch") is not False
        or axis.get("source_agent_ids") != ["ego"]
        or axis.get("all_nonlatent_rows_identical") is not True
    ):
        raise ValueError("candidate axis is not same-ego K8")
    latent = _object(report["latent"], "latent")
    if (
        latent.get("shape", [None])[0] != 8
        or latent.get("row0_zero") is not True
        or latent.get("finite") is not True
        or not _sha(latent.get("sha256"))
    ):
        raise ValueError("latent evidence drifted")
    temperature = _object(report["temperature"], "temperature")
    if temperature != {
        "status": "not_exposed_by_fixed_dp_formal_interface",
        "tensor": None,
        "sha256": None,
    }:
        raise ValueError("temperature evidence drifted")
    primary = _object(report["primary_pool_invocation"], "primary")
    if (
        primary.get("model_call_count") != 1
        or primary.get("input_batch_size") != 8
        or primary.get("output_shape", [None])[0] != 8
        or primary.get("dtype") != "float32"
        or primary.get("finite") is not True
        or primary.get("unique_row_sha256_count") != 8
        or len(primary.get("row_sha256", [])) != 8
        or not _sha(primary.get("candidate_tensor_sha256"))
        or not _sha(primary.get("pool_id"))
    ):
        raise ValueError("primary single-call K8 evidence drifted")
    deterministic = _object(report["determinism"], "determinism")
    if (
        deterministic.get("repeat_model_call_count") != 1
        or deterministic.get("exact_equal") is not True
        or deterministic.get("repeat_tensor_sha256")
        != primary.get("candidate_tensor_sha256")
    ):
        raise ValueError("determinism evidence drifted")
    relation = _object(report["batch_vs_sequential"], "batch relation")
    if (
        relation.get("sequential_model_call_count") != 8
        or relation.get("atol") != 1e-5
        or relation.get("rtol") != 1e-5
        or relation.get("within_frozen_tolerance") is not True
        or len(relation.get("per_row_max_abs_error", [])) != 8
        or relation.get("all_sequential_row_sha256", []) == []
    ):
        raise ValueError("batch/sequential evidence drifted")
    selector = _object(report["selector_after_pool"], "selector")
    arms = selector.get("arms")
    if type(arms) is not list or len(arms) != 3:
        raise ValueError("selector arm count drifted")
    expected_arms = ["pool_baseline", "Static14D", "Scene14D"]
    if [row.get("arm") for row in arms] != expected_arms:
        raise ValueError("selector arm order drifted")
    for field in (
        "pool_id",
        "candidate_tensor_sha256",
        "input_sha256",
        "model_sha256",
        "forward_invocation_id",
    ):
        if len({row.get(field) for row in arms}) != 1:
            raise ValueError(f"selector {field} drifted across arms")
    if any(
        row.get("model_call_count_after_pool") != 0
        or row.get("latent_replacement_count_after_pool") != 0
        or row.get("trajectory_generation_count_after_pool") != 0
        or row.get("candidate_tensor_immutable") is not True
        for row in arms
    ):
        raise ValueError("selector-after-pool forbidden operation detected")
    if arms[0].get("selected_index") != 0:
        raise ValueError("pool baseline did not select row0")
    if report["rng_boundary"] != {
        "unchanged": True,
        "before_sha256": report["rng_boundary"].get("before_sha256"),
        "after_sha256": report["rng_boundary"].get("after_sha256"),
    } or report["rng_boundary"]["before_sha256"] != report["rng_boundary"][
        "after_sha256"
    ]:
        raise ValueError("RNG boundary drifted")
    training = _object(report["training_decision"], "training")
    if training.get("training_executed") is not False:
        raise ValueError("training was executed")
    claim = _object(report["claim_boundary"], "claim")
    if (
        claim.get("fresh_or_closed_loop_executed") is not False
        or claim.get("scientific_effect_claim_authorized") is not False
        or claim.get("legacy_claim_decision") != LEGACY_DECISION
    ):
        raise ValueError("capability claim boundary drifted")
    return report


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()


def _object(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError(f"{label} must be a plain object")
    return dict(value)


def _exact_keys(value: Mapping[str, Any], keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise ValueError(f"{label} fields drifted")


def _sha(value: Any) -> bool:
    if type(value) is not str or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True
