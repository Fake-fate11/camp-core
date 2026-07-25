"""Reviewer-local literal oracle for the V25 fair nonholdout contract."""

from __future__ import annotations

from typing import Any, Mapping


CONTRACT_SCHEMA = "camp_dp_v25_fair_nonholdout_contract_v1"
GENERATOR_NAME = "new_single_invocation_batched_k8_candidate_pool"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_CAMP_HEAD = "540dca71136cd43da4bc045369e28c3d6030b232"
ROUTE_SHA256 = "63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd"
EXPECTED_ARMS = ["pool_matched_candidate0", "Static14D", "Scene14D"]
EXPECTED_IMMUTABLE_ROOTS = {
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
CONTINUATION_SHA256 = (
    "727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392"
)


def review_contract_literal(value: Mapping[str, Any]) -> dict[str, Any]:
    """Independently check semantics without importing the producer module."""

    if type(value) is not dict:
        raise TypeError("reviewed fair contract must be a plain object")
    report = dict(value)
    if set(report) != {
        "schema_version",
        "status",
        "source_authority",
        "generator",
        "state_matched_selector_replay",
        "pool_distribution_adaptation_audit",
        "compute_matched_closed_loop",
        "latency_accounting",
        "hard_stop",
        "claim_boundary",
    }:
        raise ValueError("reviewed fair contract field inventory drifted")
    source = _object(report["source_authority"], "source authority")
    generator = _object(report["generator"], "generator")
    replay = _object(report["state_matched_selector_replay"], "selector replay")
    audit = _object(
        report["pool_distribution_adaptation_audit"], "adaptation audit"
    )
    closed = _object(report["compute_matched_closed_loop"], "closed loop")
    latency = _object(report["latency_accounting"], "latency")
    stop = _object(report["hard_stop"], "hard stop")
    claim = _object(report["claim_boundary"], "claim")
    if (
        report["schema_version"] != CONTRACT_SCHEMA
        or report["status"] != "frozen_outcome_independent_fair_nonholdout_contract"
        or source.get("camp_head") != SOURCE_CAMP_HEAD
        or source.get("fixed_dp_head") != FIXED_DP_HEAD
        or source.get("immutable_roots") != EXPECTED_IMMUTABLE_ROOTS
        or source.get("continuation_ledger_sha256") != CONTINUATION_SHA256
        or source.get("fresh_or_b4_raw_outcome_read") is not False
        or source.get("old_artifact_or_cas_write_allowed") is not False
        or generator.get("name") != GENERATOR_NAME
        or generator.get("candidate_count") != 8
        or generator.get("model_invocations_per_pool") != 1
        or generator.get("same_ego_candidate_axis") is not True
        or generator.get("agent_as_ego_axis") is not False
        or generator.get("operational_default_batch_size") != 1
        or generator.get("operational_default_natively_had_k8_claimed") is not False
    ):
        raise ValueError("fair generator/source literal oracle failed")
    ordinals = list(range(16))
    if (
        replay.get("route_sha256") != ROUTE_SHA256
        or replay.get("state_ordinals") != ordinals
        or replay.get("state_count") != 16
        or replay.get("authoritative_pool_count") != 16
        or replay.get("pool_generated_once_per_state_for_three_selectors") is not True
        or replay.get("arms") != EXPECTED_ARMS
        or replay.get("baseline_rule") != "frozen_row0"
        or replay.get("static_and_scene_execute_real_canonical_selector") is not True
        or replay.get("candidate_tensor_immutable_required") is not True
        or replay.get("post_pool_required_counts")
        != {
            "dp_or_model_calls": 0,
            "latent_replacements": 0,
            "candidate_generations": 0,
        }
    ):
        raise ValueError("fair selector replay literal oracle failed")
    drift = _object(audit.get("substantive_drift_definition"), "drift")
    if (
        audit.get("state_ordinals") != ordinals
        or audit.get("trajectory_atol") != 1e-5
        or audit.get("trajectory_rtol") != 1e-5
        or audit.get("neighbor_atol") != 1e-5
        or audit.get("neighbor_rtol") != 1e-5
        or set(drift)
        != {
            "any_trajectory_row_outside_tolerance",
            "any_neighbor_row_outside_tolerance",
            "any_source_or_eligibility_mask_difference",
            "any_static_or_scene_selected_index_flip",
        }
        or not all(value is True for value in drift.values())
        or audit.get("single_state_generalization_allowed") is not False
        or audit.get("training_authorized") is not False
    ):
        raise ValueError("fair adaptation literal oracle failed")
    if (
        closed.get("arms") != EXPECTED_ARMS
        or closed.get("arm_run_count") != 3
        or closed.get("ticks_per_arm") != 64
        or closed.get("planned_tick_denominator") != 192
        or closed.get("each_arm_own_branched_state") is not True
        or closed.get("post_divergence_cross_arm_tensor_identity_claimed") is not False
        or closed.get("retain_all_terminal_failures") is not True
        or closed.get("complete_case_shrinkage_allowed") is not False
        or closed.get("confirmatory_or_fresh_claim_authorized") is not False
    ):
        raise ValueError("fair closed-loop literal oracle failed")
    if (
        latency.get("baseline_includes_pool_generation") is not True
        or latency.get("baseline_uncalled_stages_are_na_not_zero") is not True
        or latency.get("operational_single_output_reference_separate") is not True
        or latency.get("operational_single_output_is_pool_matched_baseline") is not False
        or set(stop)
        != {
            "any_post_pool_forbidden_call",
            "batch8_nondeterministic_or_not_diverse",
            "adaptation_substantive_drift",
            "fixed_dp_source_checkpoint_or_head_drift",
            "weights_theta_atoms_or_scales_change_required",
            "sealed_authority_anomaly",
        }
        or not all(value is True for value in stop.values())
        or claim.get("scientific_contract_status")
        != "scientific_contract_review_required"
        or claim.get("qualification_only") is not True
        or claim.get("fresh_authorized") is not False
        or claim.get("holdout_authorized") is not False
        or claim.get("training_or_retraining_authorized") is not False
        or claim.get("confirmatory_effect_claim_authorized") is not False
        or claim.get("ultra_submission_authorized") is not False
    ):
        raise ValueError("fair latency/stop/claim literal oracle failed")
    return report


def _object(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError(f"{label} must be a plain object")
    return dict(value)
