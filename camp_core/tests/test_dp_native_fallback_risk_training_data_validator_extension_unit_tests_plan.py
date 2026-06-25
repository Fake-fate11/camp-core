from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_unit_tests_plan.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def _iteration_audit() -> str:
    return ITERATION_AUDIT.read_text(encoding="utf-8")


def test_unit_tests_plan_records_preconditions() -> None:
    text = _plan()

    for needle in [
        "validator_extension_plan_ready=True",
        "validator_extension_static_contract_review_passed=True",
        "blocking_contract_findings=0",
        "accepted_fallback_records=15",
        "fallback_dataset_artifact_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "validator_extension_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "autodl_DP_HEAD_at_plan=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_static_contract_status=fallback_risk_training_data_validator_extension_static_contract_current_head_revalidated",
        "current_accepted_dataset_sha256=0978687b1f7582f6644eb9598bdc5a9e03494ad227d1627bd603d54e15efb8e2",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_unit_tests_plan_revalidation_base_head=3e9a002dc1099afe6846cdf6e3a44830e15f6a6a",
        "latest_autodl_CAMP_HEAD_at_revalidation=3e9a002dc1099afe6846cdf6e3a44830e15f6a6a",
        "latest_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_static_contract_status=fallback_risk_training_data_validator_extension_static_contract_autodl_verification_passed",
        "latest_accepted_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "current_unit_tests_plan_revalidation_base_head=4af52fa851c930486d23dbbf2edd3dd4bd27ead5",
        "current_camp_origin_main_at_revalidation=4af52fa851c930486d23dbbf2edd3dd4bd27ead5",
        "current_github_refs_heads_main_at_revalidation=4af52fa851c930486d23dbbf2edd3dd4bd27ead5",
        "current_autodl_CAMP_HEAD_at_revalidation=4af52fa851c930486d23dbbf2edd3dd4bd27ead5",
        "current_autodl_CAMP_origin_main_at_revalidation=4af52fa851c930486d23dbbf2edd3dd4bd27ead5",
        "current_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_static_contract_status=fallback_risk_training_data_validator_extension_static_contract_autodl_verification_passed",
        "current_accepted_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_432fd2b_unit_tests_plan_revalidation_base_head=432fd2b2c5aa3b2d7563d00476481eaae448153c",
        "head_432fd2b_camp_origin_main_at_revalidation=432fd2b2c5aa3b2d7563d00476481eaae448153c",
        "head_432fd2b_github_refs_heads_main_at_revalidation=432fd2b2c5aa3b2d7563d00476481eaae448153c",
        "head_432fd2b_autodl_CAMP_HEAD_at_revalidation=432fd2b2c5aa3b2d7563d00476481eaae448153c",
        "head_432fd2b_autodl_CAMP_origin_main_at_revalidation=432fd2b2c5aa3b2d7563d00476481eaae448153c",
        "head_432fd2b_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "head_432fd2b_static_contract_status=fallback_risk_training_data_validator_extension_static_contract_current_head_b45e849_revalidated",
        "head_432fd2b_accepted_dataset_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "current_f0ad5c5_unit_tests_plan_revalidation_base_head=f0ad5c57e6a438f1878f73ab4dc8258bc3fa748e",
        "current_f0ad5c5_camp_origin_main_at_revalidation=f0ad5c57e6a438f1878f73ab4dc8258bc3fa748e",
        "current_f0ad5c5_github_refs_heads_main_at_revalidation=f0ad5c57e6a438f1878f73ab4dc8258bc3fa748e",
        "current_f0ad5c5_autodl_CAMP_HEAD_at_revalidation=f0ad5c57e6a438f1878f73ab4dc8258bc3fa748e",
        "current_f0ad5c5_autodl_CAMP_origin_main_at_revalidation=f0ad5c57e6a438f1878f73ab4dc8258bc3fa748e",
        "current_f0ad5c5_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_f0ad5c5_static_contract_status=fallback_risk_training_data_validator_extension_static_contract_current_head_d529235_revalidated",
        "current_f0ad5c5_accepted_dataset_sha256=682d432f742d4ab68a262cf70955981bc1562cf1dbcf2ec094984a12fcd11498",
        "head_fe4bb4a_unit_tests_plan_revalidation_base_head=fe4bb4a5f4cb42726e2f966a25d73350e8e1d6ea",
        "head_fe4bb4a_camp_origin_main_at_revalidation=fe4bb4a5f4cb42726e2f966a25d73350e8e1d6ea",
        "head_fe4bb4a_github_refs_heads_main_at_revalidation=fe4bb4a5f4cb42726e2f966a25d73350e8e1d6ea",
        "head_fe4bb4a_autodl_CAMP_HEAD_at_revalidation=fe4bb4a5f4cb42726e2f966a25d73350e8e1d6ea",
        "head_fe4bb4a_autodl_CAMP_origin_main_at_revalidation=fe4bb4a5f4cb42726e2f966a25d73350e8e1d6ea",
        "head_fe4bb4a_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "head_fe4bb4a_static_contract_status=fallback_risk_training_data_validator_extension_static_contract_current_head_8268b98_revalidated",
        "head_fe4bb4a_accepted_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
    ]:
        assert needle in text


def test_unit_tests_plan_covers_read_only_and_dataset_summary_tests() -> None:
    text = _plan()

    for needle in [
        "test_validator_reads_existing_dataset_json_only=True",
        "test_validator_writes_only_explicit_output_json_and_md=True",
        "test_validator_does_not_run_replay_or_candidate_generation=True",
        "test_validator_does_not_train_or_modify_dp=True",
        "test_validator_reports_training_not_authorized=True",
        "test_accepts_clean_builder_complete_dataset=True",
        "test_rejects_schema_version_mismatch=True",
        "test_rejects_disabled_or_failed_builder_decision=True",
        "test_rejects_records_built_count_mismatch=True",
        "test_rejects_records_built_not_equal_records_without_feasible_candidate=True",
        "test_rejects_failed_records_nonzero=True",
        "test_rejects_final_decision_errors=True",
        "test_requires_source_hashes_for_every_source_log=True",
    ]:
        assert needle in text


def test_unit_tests_plan_covers_source_log_readback_tests() -> None:
    text = _plan()

    for needle in [
        "test_accepts_matching_source_log_sha_and_all_false_feasible_mask=True",
        "test_rejects_source_log_hash_mismatch=True",
        "test_rejects_missing_source_log_when_acceptance_readback_required=True",
        "test_rejects_missing_source_record_index=True",
        "test_rejects_non_bool_source_feasible_mask=True",
        "test_rejects_any_true_source_feasible_mask=True",
        "test_rejects_source_candidate_count_mismatch=True",
        "test_rejects_source_selected_index_mismatch=True",
        "test_rechecks_source_candidate_generation_contract=True",
        "test_rechecks_source_candidate_tensor_provenance=True",
        "test_rechecks_source_atom_schema_names_atoms_and_normalized_atoms=True",
    ]:
        assert needle in text


def test_unit_tests_plan_covers_per_record_and_nonpromotion_tests() -> None:
    text = _plan()

    for needle in [
        "test_requires_source_log_and_source_sha=True",
        "test_requires_source_artifact_sha=True",
        "test_requires_run_id_and_record_index=True",
        "test_rejects_candidate_count_non_int_or_empty=True",
        "test_rejects_selected_or_oracle_index_out_of_range=True",
        "test_rejects_unknown_oracle_policy=True",
        "test_rejects_negative_or_nonfinite_costs=True",
        "test_rejects_negative_or_nonfinite_margins=True",
        "test_rejects_atom_schema_or_names_mismatch=True",
        "test_rejects_atom_shape_mismatch=True",
        "test_rejects_negative_or_nonfinite_atoms=True",
        "test_rejects_normalized_atom_shape_mismatch=True",
        "test_rejects_training_authorized_true=True",
        "test_rejects_selected_index_used_as_feature_true=True",
        "test_rejects_candidate_rank_used_as_feature_true=True",
        "test_rejects_fallback_label_promoted_as_deployed_atom=True",
        "test_rejects_selector_or_atom_promotion_flags=True",
        "test_rejects_safety_or_camp_over_dp_claim_flags=True",
    ]:
        assert needle in text


def test_unit_tests_plan_requires_synthetic_fixtures_only() -> None:
    text = _plan()

    for needle in [
        "synthetic_dataset_fixtures_only=True",
        "synthetic_source_logs_only=True",
        "formal_seeds_11_12_13_used=False",
        "fixed_autodl_artifact_required_for_unit_tests=False",
        "replay_required_for_unit_tests=False",
        "candidate_generation_required_for_unit_tests=False",
        "training_required_for_unit_tests=False",
    ]:
        assert needle in text


def test_unit_tests_plan_forbids_execution_training_and_claims() -> None:
    text = _plan()

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
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "validator_extension_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "user_broad_execution_permission_recorded=True",
        "this_unit_tests_plan_gate_authorizes_broad_execution=False",
        "validator_extension_unit_tests_authorized_next=True",
        "current_local_target_pytest=8 passed",
        "current_local_py_compile_exit=0",
        "current_local_git_diff_check_exit=0",
        "head_432fd2b_local_target_pytest=59 passed",
        "head_432fd2b_local_py_compile_exit=0",
        "head_432fd2b_local_git_diff_check_exit=0",
        "current_f0ad5c5_local_target_pytest=8 passed",
        "current_f0ad5c5_local_py_compile_exit=0",
        "current_f0ad5c5_local_git_diff_check_exit=0",
        "head_fe4bb4a_local_target_pytest=153 passed",
        "head_fe4bb4a_local_py_compile_exit=0",
        "head_fe4bb4a_local_git_diff_check_exit=0",
        "head_fe4bb4a_autodl_target_pytest=153 passed",
        "head_fe4bb4a_autodl_py_compile_exit=0",
        "head_fe4bb4a_autodl_git_diff_check_exit=0",
        "latest_local_target_pytest=13 passed",
        "latest_autodl_target_pytest=13 passed",
        "status=fallback_risk_training_data_validator_extension_unit_tests_plan_autodl_verification_passed",
        "github_pushed_commit=3f52f2ad89febf326c5aa0b7fc80025e5f42f6f2",
        "autodl_CAMP_HEAD_after_sync=3f52f2ad89febf326c5aa0b7fc80025e5f42f6f2",
        "autodl_CAMP_origin_main_after_sync=3f52f2ad89febf326c5aa0b7fc80025e5f42f6f2",
        "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_target_pytest_result=8 passed",
        "autodl_target_pytest_exit=0",
        "autodl_py_compile_exit=0",
        "autodl_git_diff_check_exit=0",
        "validator_extension_unit_tests_plan_current_head_complete=True",
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


def test_unit_tests_plan_next_gate_tests_only() -> None:
    text = _plan()

    for needle in [
        "status=fallback_risk_training_data_validator_extension_unit_tests_plan_ready",
        "status=fallback_risk_training_data_validator_extension_unit_tests_plan_current_head_4af52fa_revalidated",
        "status=fallback_risk_training_data_validator_extension_unit_tests_plan_current_head_432fd2b_revalidated",
        "status=fallback_risk_training_data_validator_extension_unit_tests_plan_current_head_f0ad5c5_revalidated",
        "status=fallback_risk_training_data_validator_extension_unit_tests_plan_current_head_fe4bb4a_revalidated",
        "validator_extension_unit_tests_plan_complete=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_unit_tests_only",
        "may only add synthetic unit tests",
        "must not implement the validator",
        "run replay",
        "generate\ncandidates",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_current_head_unit_tests_plan() -> None:
    text = _iteration_audit()
    tail = text[-12000:]

    for needle in [
        "Current Tail Confirmation After Current HEAD Fallback Risk Training Data Validator Extension Unit Tests Plan",
        "status=fallback_risk_training_data_validator_extension_unit_tests_plan_current_head_fe4bb4a_revalidated",
        "head_fe4bb4a_unit_tests_plan_revalidation_base_head=fe4bb4a5f4cb42726e2f966a25d73350e8e1d6ea",
        "head_fe4bb4a_github_refs_heads_main_at_revalidation=fe4bb4a5f4cb42726e2f966a25d73350e8e1d6ea",
        "head_fe4bb4a_autodl_CAMP_HEAD_at_revalidation=fe4bb4a5f4cb42726e2f966a25d73350e8e1d6ea",
        "head_fe4bb4a_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "head_fe4bb4a_static_contract_status=fallback_risk_training_data_validator_extension_static_contract_current_head_8268b98_revalidated",
        "head_fe4bb4a_accepted_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_fe4bb4a_local_target_pytest=153 passed",
        "validator_extension_unit_tests_plan_complete=True",
        "validator_extension_unit_tests_authorized_next=True",
        "validator_extension_implementation_authorized=False",
        "camp_retraining_authorized=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_unit_tests_only",
    ]:
        assert needle in tail
