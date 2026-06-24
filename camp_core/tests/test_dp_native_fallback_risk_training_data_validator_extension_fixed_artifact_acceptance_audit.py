from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_fixed_artifact_acceptance_audit.md"
)


def _audit() -> str:
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_validator_acceptance_records_fixed_nonformal_dataset_identity() -> None:
    text = _audit()

    for needle in [
        "source_artifact_scope=broader_nonformal_fixed_evaluation_artifact",
        "formal_seeds_11_12_13_used=False",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f632c44_20260624T133402Z/dataset.json",
        "source_dataset_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "validator_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_validator_acceptance_f4ea755_20260624T142300Z",
        "validator_output_json_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "validator_output_md_sha256=e57c15b6772e0202fe76fec20d220e435c1010aab7bc410fb45230277fc9ab6a",
        "autodl_DP_HEAD_at_acceptance=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_source_artifact_scope=broader_nonformal_fixed_evaluation_artifact",
        "current_source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_52f8d20_20260624T195018Z/dataset.json",
        "current_source_dataset_sha256=0978687b1f7582f6644eb9598bdc5a9e03494ad227d1627bd603d54e15efb8e2",
        "current_unique_source_logs=7",
        "current_strict_formal_seed_path_matches=0",
        "current_formal_seeds_11_12_13_used=False",
        "current_validator_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_validator_acceptance_0ed8c92_20260624T201719Z",
        "current_validator_output_json_sha256=276ed840e674733861123bde0c1fa45474fbcba6d23d7faa83e53abbacd7b078",
        "current_validator_output_md_sha256=e57c15b6772e0202fe76fec20d220e435c1010aab7bc410fb45230277fc9ab6a",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    ]:
        assert needle in text


def test_validator_acceptance_records_status_counts_and_readback() -> None:
    text = _audit()

    for needle in [
        "schema_version=dp_native_fallback_risk_training_data_validator_v1",
        "status=dp_native_fallback_risk_training_data_validator_complete",
        "passed=True",
        "enabled=True",
        "validator_enable_flag_used=True",
        "records_checked=15",
        "failed_records=0",
        "errors=0",
        "source_log_readback_required_for_acceptance=True",
        "source_log_readback_enabled=True",
        "read_only_source_log_readback_only=True",
        "current_schema_version=dp_native_fallback_risk_training_data_validator_v1",
        "current_status=dp_native_fallback_risk_training_data_validator_complete",
        "current_passed=True",
        "current_enabled=True",
        "current_records_checked=15",
        "current_failed_records=0",
        "current_errors=0",
        "current_source_log_readback_enabled=True",
        "current_dataset_records_total=60",
        "current_dataset_records_without_feasible_candidate=15",
        "current_dataset_records_with_feasible_candidate=45",
        "current_dataset_records_built=15",
        "current_dataset_failed_records=0",
        "current_dataset_candidate_counts=4",
        "current_dataset_oracle_policies=lane/red/quality,red/lane/quality",
    ]:
        assert needle in text


def test_validator_acceptance_records_validated_dataset_contract() -> None:
    text = _audit()

    for needle in [
        "dataset_schema_validated_by_validator=True",
        "builder_complete_status_validated_by_validator=True",
        "record_counts_validated_by_validator=True",
        "source_log_hashes_validated_by_validator=True",
        "source_feasible_mask_all_false_validated_by_validator=True",
        "source_candidate_generation_contract_validated_by_validator=True",
        "source_candidate_tensor_provenance_validated_by_validator=True",
        "atom_schema_and_nonnegative_atoms_validated_by_validator=True",
        "normalized_atoms_validated_by_validator=True",
        "fallback_dataset_training_sufficiency_claim=False",
    ]:
        assert needle in text


def test_validator_acceptance_forbids_training_replay_dp_and_claims() -> None:
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
        "hard_feasibility_relaxation_authorized=False",
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
        "current_fallback_dataset_training_sufficiency_claim=False",
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


def test_validator_acceptance_next_gate_is_training_sufficiency_plan_only() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_data_validator_extension_fixed_artifact_acceptance_passed",
        "fixed_artifact_acceptance_audit_complete=True",
        "validated_fallback_records=15",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_plan_only",
        "may only plan the training-sufficiency boundary",
        "must predeclare any split",
        "scale-fitting",
        "formal-seed exclusion",
        "must not train CAMP",
        "run replay",
        "generate",
        "modify Diffusion Planner",
        "promote a selector or atom",
    ]:
        assert needle in text
