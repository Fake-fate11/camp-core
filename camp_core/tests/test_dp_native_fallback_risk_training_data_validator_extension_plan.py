from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_plan.md"
)


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_validator_extension_plan_records_preconditions() -> None:
    text = _plan()

    for needle in [
        "builder_post_implementation_static_contract_passed=True",
        "fixed_artifact_acceptance_audit_passed=True",
        "accepted_fallback_records=15",
        "accepted_dataset_schema_version=dp_native_fallback_risk_training_data_v1",
        "accepted_dataset_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "formal_seeds_11_12_13_used=False",
        "autodl_DP_HEAD_at_plan=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_fixed_artifact_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_revalidated",
        "current_accepted_fallback_records=15",
        "current_accepted_dataset_schema_version=dp_native_fallback_risk_training_data_v1",
        "current_accepted_dataset_sha256=0978687b1f7582f6644eb9598bdc5a9e03494ad227d1627bd603d54e15efb8e2",
        "current_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_52f8d20_20260624T195018Z/dataset.json",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    ]:
        assert needle in text


def test_validator_extension_plan_is_read_only_and_source_backed() -> None:
    text = _plan()

    for needle in [
        "validator_input=existing_fallback_risk_training_dataset_json_only",
        "optional_source_log_readback=True",
        "source_log_readback_required_for_acceptance=True",
        "source_log_readback_mode=read_only_source_log_sha256_and_record_index_check",
        "output_json_or_markdown_only=True",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "training_execution_authorized=False",
        "dp_modification_authorized=False",
    ]:
        assert needle in text


def test_validator_extension_plan_checks_top_level_and_record_contracts() -> None:
    text = _plan()

    for needle in [
        "require_schema_version=dp_native_fallback_risk_training_data_v1",
        "require_final_decision_status=dp_native_fallback_risk_training_data_builder_complete",
        "require_records_built_equals_records_without_feasible_candidate=True",
        "require_failed_records_zero=True",
        "require_source_hashes_for_every_source_log=True",
        "require_selected_index_in_range=True",
        "require_oracle_index_in_range=True",
        "allowed_oracle_policies=red/lane/quality,lane/red/quality,quality/red/lane",
        "require_margins_finite_nonnegative=True",
        "require_atom_schema_version_approved=True",
        "require_atoms_shape_candidate_by_schema_dim=True",
        "require_normalized_atoms_shape_matches_atoms=True",
        "require_training_authorized_false=True",
        "require_fallback_label_is_not_a_deployed_atom_true=True",
    ]:
        assert needle in text


def test_validator_extension_plan_requires_source_log_all_infeasible_readback() -> None:
    text = _plan()

    for needle in [
        "source_log_hash_mismatch_fails_closed=True",
        "source_record_missing_fails_closed=True",
        "source_feasible_mask_non_bool_fails_closed=True",
        "source_feasible_mask_any_true_fails_closed=True",
        "source_candidate_count_mismatch_fails_closed=True",
        "source_selected_index_mismatch_fails_closed=True",
        "source_candidate_generation_contract_rechecked=True",
        "source_candidate_tensor_provenance_rechecked=True",
        "source_atom_schema_and_names_rechecked=True",
        "source_atoms_and_normalized_atoms_rechecked=True",
    ]:
        assert needle in text


def test_validator_extension_plan_preserves_master_and_nonpromotion_boundary() -> None:
    text = _plan()

    for needle in [
        "score_k(w)=a_k^T w",
        "fallback_dataset_validator_does_not_add_atoms=True",
        "fallback_dataset_validator_does_not_change_weights=True",
        "fallback_dataset_validator_does_not_change_feasible_master=True",
        "fallback_dataset_validator_does_not_relax_hard_feasibility=True",
        "fallback_dataset_validator_does_not_train=True",
        "fallback_dataset_training_sufficiency_claim=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "feasible_ranking_master_change_authorized=False",
        "hard_feasibility_relaxation_authorized=False",
        "simplex_master_unchanged=True",
        "cvar_master_unchanged=True",
        "l2_regularized_master_unchanged=True",
    ]:
        assert needle in text


def test_validator_extension_plan_negative_tests_and_forbidden_flags() -> None:
    text = _plan()

    for needle in [
        "test_rejects_schema_mismatch=True",
        "test_rejects_failed_or_disabled_builder_decision=True",
        "test_rejects_record_count_mismatch=True",
        "test_rejects_missing_source_identity=True",
        "test_rejects_source_hash_mismatch=True",
        "test_rejects_source_record_with_any_feasible_candidate=True",
        "test_rejects_non_bool_source_feasible_mask=True",
        "test_rejects_training_or_promotion_flags=True",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "validator_extension_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
    ]:
        assert needle in text

    for forbidden in [
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "validator_extension_implementation_authorized=True",
        "fallback_risk_training_authorized_now=True",
    ]:
        assert forbidden not in text


def test_validator_extension_plan_next_gate_is_static_review_only() -> None:
    text = _plan()

    for needle in [
        "status=fallback_risk_training_data_validator_extension_plan_ready",
        "validator_extension_plan_complete=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_static_contract_review_only",
        "may only perform a static contract review",
        "must not implement the validator",
        "run replay",
        "generate candidates",
        "train CAMP",
        "modify Diffusion Planner",
        "promote a selector or atom",
    ]:
        assert needle in text
