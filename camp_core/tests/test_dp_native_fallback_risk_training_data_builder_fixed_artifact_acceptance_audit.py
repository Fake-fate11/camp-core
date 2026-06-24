from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_audit.md"
)


def _audit() -> str:
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_acceptance_audit_records_fixed_nonformal_artifact_identity() -> None:
    text = _audit()

    for needle in [
        "artifact_scope=broader_nonformal_fixed_evaluation_artifact",
        "formal_seeds_11_12_13_used=False",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f632c44_20260624T133402Z",
        "builder_output_json_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "builder_output_md_sha256=e32a7a0fcbbfae6c971dca0f0b04bca59f9111b3cffa57e9ce2dc046481d2823",
        "autodl_DP_HEAD_at_acceptance=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_artifact_scope=broader_nonformal_fixed_evaluation_artifact",
        "current_selection_logs=12",
        "current_formal_seed_path_matches=0",
        "current_builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_52f8d20_20260624T195018Z",
        "current_builder_output_json_sha256=0978687b1f7582f6644eb9598bdc5a9e03494ad227d1627bd603d54e15efb8e2",
        "current_builder_output_md_sha256=e32a7a0fcbbfae6c971dca0f0b04bca59f9111b3cffa57e9ce2dc046481d2823",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    ]:
        assert needle in text


def test_acceptance_audit_records_dataset_counts_and_status() -> None:
    text = _audit()

    for needle in [
        "schema_version=dp_native_fallback_risk_training_data_v1",
        "status=dp_native_fallback_risk_training_data_builder_complete",
        "passed=True",
        "enabled=True",
        "selection_logs=12",
        "records_total=60",
        "records_without_feasible_candidate=15",
        "records_with_feasible_candidate=45",
        "records_built=15",
        "failed_records=0",
        "errors=0",
        "record_candidate_counts=4",
        "oracle_policies=lane/red/quality,red/lane/quality",
        "current_schema_version=dp_native_fallback_risk_training_data_v1",
        "current_status=dp_native_fallback_risk_training_data_builder_complete",
        "current_passed=True",
        "current_enabled=True",
        "current_records_total=60",
        "current_records_without_feasible_candidate=15",
        "current_records_with_feasible_candidate=45",
        "current_records_built=15",
        "current_failed_records=0",
        "current_errors=0",
        "current_record_candidate_counts=4",
        "current_oracle_policies=lane/red/quality,red/lane/quality",
    ]:
        assert needle in text


def test_acceptance_audit_records_validated_fixed_candidate_contract() -> None:
    text = _audit()

    for needle in [
        "selected_index_range_validated_by_builder=True",
        "candidate_count_unchanged_validated_by_builder=True",
        "pre_post_tensor_hash_equal_validated_by_builder=True",
        "no_candidate_row_append_validated_by_builder=True",
        "no_coordinate_heading_speed_rewrite_by_camp_validated_by_builder=True",
        "candidate_generation_contract_validated_by_builder=True",
        "atom_schema_and_nonnegative_atoms_validated_by_builder=True",
        "normalized_atoms_validated_by_builder=True",
        "margin_ik_nonnegative_and_clipped=True",
        "fallback_dataset_training_sufficiency_claim=False",
    ]:
        assert needle in text


def test_acceptance_audit_forbids_training_replay_dp_and_claims() -> None:
    text = _audit()

    for needle in [
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "Full36_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "reference_blend_authorized=False",
        "guidance_authorized=False",
        "postprocess_postselection_authorized=False",
        "closed_loop_outcome_online_input_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "feasible_ranking_master_change_authorized=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
        "current_replay_execution_authorized=False",
        "current_candidate_generation_authorized=False",
        "current_camp_training_authorized=False",
        "current_camp_retraining_authorized=False",
        "current_formal_seeds_11_12_13_authorized=False",
        "current_dp_modification_authorized=False",
        "current_selector_promotion_authorized=False",
        "current_atom_promotion_authorized=False",
        "current_safety_benefit_claim_authorized=False",
        "current_camp_over_dp_top1_claim_authorized=False",
        "current_fallback_risk_training_authorized_now=False",
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
        "fallback_risk_training_authorized_now=True",
    ]:
        assert forbidden not in text


def test_acceptance_audit_next_gate_is_validator_extension_plan_only() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_passed",
        "fixed_artifact_acceptance_audit_complete=True",
        "accepted_fallback_records=15",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_plan_only",
        "may only plan a validator extension",
        "must not implement training",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
        "promote a selector or atom",
    ]:
        assert needle in text
