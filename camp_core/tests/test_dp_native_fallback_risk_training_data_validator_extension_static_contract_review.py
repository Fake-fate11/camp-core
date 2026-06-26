from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_static_contract_review.md"
)
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_plan.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _review() -> str:
    return REVIEW_DOC.read_text(encoding="utf-8")


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def _iteration_audit() -> str:
    return ITERATION_AUDIT.read_text(encoding="utf-8")


def test_static_review_passes_source_isolation_contract() -> None:
    text = _review()
    plan = _plan()

    for needle in [
        "source_isolation_passed=True",
    ]:
        assert needle in text

    for needle in [
        "validator_input=existing_fallback_risk_training_dataset_json_only",
        "source_log_readback_required_for_acceptance=True",
        "source_log_readback_mode=read_only_source_log_sha256_and_record_index_check",
        "output_json_or_markdown_only=True",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "training_execution_authorized=False",
        "dp_modification_authorized=False",
    ]:
        assert needle in text
        assert needle in plan

    for needle in [
        "current_validator_extension_plan_status=fallback_risk_training_data_validator_extension_plan_current_head_revalidated",
        "current_accepted_dataset_sha256=0978687b1f7582f6644eb9598bdc5a9e03494ad227d1627bd603d54e15efb8e2",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_static_review_revalidation_base_head=4526a198338d7780c67261a96b35b1f8649c7b2a",
        "latest_autodl_CAMP_HEAD_at_revalidation=4526a198338d7780c67261a96b35b1f8649c7b2a",
        "latest_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_validator_extension_plan_status=fallback_risk_training_data_validator_extension_plan_autodl_verification_passed",
        "latest_accepted_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "latest_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_6adb800_20260625T020016Z/dataset.json",
        "current_static_review_revalidation_base_head=8f25fe4fc0940c031f628569bcf69a3d154da306",
        "current_camp_origin_main_at_revalidation=8f25fe4fc0940c031f628569bcf69a3d154da306",
        "current_github_refs_heads_main_at_revalidation=8f25fe4fc0940c031f628569bcf69a3d154da306",
        "current_autodl_CAMP_HEAD_at_revalidation=8f25fe4fc0940c031f628569bcf69a3d154da306",
        "current_autodl_CAMP_origin_main_at_revalidation=8f25fe4fc0940c031f628569bcf69a3d154da306",
        "current_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_validator_extension_plan_status=fallback_risk_training_data_validator_extension_plan_autodl_verification_passed",
        "current_accepted_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "current_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_da0e617_20260625T080225Z/dataset.json",
        "b45e849_static_review_revalidation_base_head=b45e84966e75edc667e7911279b6806bc0944a8e",
        "b45e849_camp_origin_main_at_revalidation=b45e84966e75edc667e7911279b6806bc0944a8e",
        "b45e849_github_refs_heads_main_at_revalidation=b45e84966e75edc667e7911279b6806bc0944a8e",
        "b45e849_autodl_CAMP_HEAD_at_revalidation=b45e84966e75edc667e7911279b6806bc0944a8e",
        "b45e849_autodl_CAMP_origin_main_at_revalidation=b45e84966e75edc667e7911279b6806bc0944a8e",
        "b45e849_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "b45e849_validator_extension_plan_status=fallback_risk_training_data_validator_extension_plan_current_head_f0fc2dc_revalidated",
        "b45e849_accepted_dataset_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "b45e849_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_e35f1e4_20260625T132102Z/dataset.json",
        "current_d529235_static_review_revalidation_base_head=d529235d620df5cf4c7aa5559a073b8f4d48ca44",
        "current_d529235_camp_origin_main_at_revalidation=d529235d620df5cf4c7aa5559a073b8f4d48ca44",
        "current_d529235_github_refs_heads_main_at_revalidation=d529235d620df5cf4c7aa5559a073b8f4d48ca44",
        "current_d529235_autodl_CAMP_HEAD_at_revalidation=d529235d620df5cf4c7aa5559a073b8f4d48ca44",
        "current_d529235_autodl_CAMP_origin_main_at_revalidation=d529235d620df5cf4c7aa5559a073b8f4d48ca44",
        "current_d529235_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_d529235_validator_extension_plan_status=fallback_risk_training_data_validator_extension_plan_current_head_8635158_revalidated",
        "current_d529235_accepted_dataset_sha256=682d432f742d4ab68a262cf70955981bc1562cf1dbcf2ec094984a12fcd11498",
        "current_d529235_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_bbba35b_20260625T174901Z/dataset.json",
        "head_8268b98_static_review_revalidation_base_head=8268b9892423a0feccd838c90a915b86a9d480a8",
        "head_8268b98_camp_origin_main_at_revalidation=8268b9892423a0feccd838c90a915b86a9d480a8",
        "head_8268b98_github_refs_heads_main_at_revalidation=8268b9892423a0feccd838c90a915b86a9d480a8",
        "head_8268b98_autodl_CAMP_HEAD_at_revalidation=8268b9892423a0feccd838c90a915b86a9d480a8",
        "head_8268b98_autodl_CAMP_origin_main_at_revalidation=8268b9892423a0feccd838c90a915b86a9d480a8",
        "head_8268b98_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "head_8268b98_validator_extension_plan_status=fallback_risk_training_data_validator_extension_plan_current_head_94f224b_revalidated",
        "head_8268b98_accepted_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_8268b98_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_4751222_20260625T213641Z/dataset.json",
        "head_56600ab_static_review_revalidation_base_head=56600ab8ec958311397948c21e7a549927b4265a",
        "head_56600ab_camp_origin_main_at_revalidation=56600ab8ec958311397948c21e7a549927b4265a",
        "head_56600ab_github_refs_heads_main_at_revalidation=56600ab8ec958311397948c21e7a549927b4265a",
        "head_56600ab_autodl_CAMP_HEAD_at_revalidation=56600ab8ec958311397948c21e7a549927b4265a",
        "head_56600ab_autodl_CAMP_origin_main_at_revalidation=56600ab8ec958311397948c21e7a549927b4265a",
        "head_56600ab_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "head_56600ab_validator_extension_plan_status=fallback_risk_training_data_validator_extension_plan_current_head_ea68e5b_revalidated",
        "head_56600ab_accepted_dataset_sha256=aff45e48340741ed976eaeaadc383fa794d7a0a769fcaebde3a90a20cae9caa6",
        "head_56600ab_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_8e50989_20260626T084333Z/dataset.json",
        "head_7862caa_static_review_revalidation_base_head=7862caaf1edc4dd5ca83e7fbd468aafd631703b7",
        "head_7862caa_camp_origin_main_at_revalidation=7862caaf1edc4dd5ca83e7fbd468aafd631703b7",
        "head_7862caa_github_refs_heads_main_at_revalidation=7862caaf1edc4dd5ca83e7fbd468aafd631703b7",
        "head_7862caa_autodl_CAMP_HEAD_at_revalidation=7862caaf1edc4dd5ca83e7fbd468aafd631703b7",
        "head_7862caa_autodl_CAMP_origin_main_at_revalidation=7862caaf1edc4dd5ca83e7fbd468aafd631703b7",
        "head_7862caa_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "head_7862caa_validator_extension_plan_status=fallback_risk_training_data_validator_extension_plan_current_head_2aec4e8_revalidated",
        "head_7862caa_accepted_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_7862caa_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f99da50_20260626T153546Z/dataset.json",
    ]:
        assert needle in text


def test_static_review_passes_dataset_and_record_contract() -> None:
    text = _review()
    plan = _plan()

    for needle in [
        "dataset_contract_passed=True",
        "require_schema_version=dp_native_fallback_risk_training_data_v1",
        "require_final_decision_status=dp_native_fallback_risk_training_data_builder_complete",
        "require_records_built_equals_records_without_feasible_candidate=True",
        "require_failed_records_zero=True",
        "per_record_contract_passed=True",
        "require_selected_index_in_range=True",
        "require_oracle_index_in_range=True",
        "allowed_oracle_policies=red/lane/quality,lane/red/quality,quality/red/lane",
        "require_margins_finite_nonnegative=True",
        "require_atom_schema_version_approved=True",
        "require_normalized_atoms_shape_matches_atoms=True",
        "require_training_authorized_false=True",
        "require_fallback_label_is_not_a_deployed_atom_true=True",
    ]:
        assert needle in text

    for needle in [
        "require_records_built_equals_records_without_feasible_candidate=True",
        "require_selected_index_in_range=True",
        "require_margins_finite_nonnegative=True",
        "require_normalized_atoms_shape_matches_atoms=True",
    ]:
        assert needle in plan


def test_static_review_requires_source_log_readback_fail_closed() -> None:
    text = _review()
    plan = _plan()

    for needle in [
        "source_log_readback_contract_passed=True",
    ]:
        assert needle in text

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
        assert needle in plan


def test_static_review_preserves_mathematical_and_nonpromotion_boundary() -> None:
    text = _review()

    for needle in [
        "score_k(w)=a_k^T w",
        "mathematical_boundary_passed=True",
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


def test_static_review_forbids_execution_training_and_claims() -> None:
    text = _review()

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
        "validator_extension_implementation_authorized=False",
        "user_broad_execution_permission_recorded=True",
        "this_static_review_gate_authorizes_broad_execution=False",
        "validator_extension_unit_tests_plan_authorized_next=True",
        "current_local_target_pytest=7 passed",
        "current_local_py_compile_exit=0",
        "current_local_git_diff_check_exit=0",
        "b45e849_local_target_pytest=51 passed",
        "b45e849_local_py_compile_exit=0",
        "b45e849_local_git_diff_check_exit=0",
        "current_d529235_local_target_pytest=7 passed",
        "current_d529235_local_py_compile_exit=0",
        "current_d529235_local_git_diff_check_exit=0",
        "head_8268b98_local_target_pytest=145 passed",
        "head_8268b98_local_py_compile_exit=0",
        "head_8268b98_local_git_diff_check_exit=0",
        "head_8268b98_autodl_target_pytest=145 passed",
        "head_8268b98_autodl_py_compile_exit=0",
        "head_8268b98_autodl_git_diff_check_exit=0",
        "head_56600ab_local_target_pytest=7 passed",
        "head_56600ab_local_py_compile_exit=0",
        "head_56600ab_local_git_diff_check_exit=0",
        "head_56600ab_autodl_target_pytest=7 passed",
        "head_56600ab_autodl_py_compile_exit=0",
        "head_56600ab_autodl_git_diff_check_exit=0",
        "head_7862caa_local_target_pytest=9 passed",
        "head_7862caa_local_py_compile_exit=0",
        "head_7862caa_local_git_diff_check_exit=0",
        "latest_local_target_pytest=13 passed",
        "latest_autodl_target_pytest=13 passed",
        "status=fallback_risk_training_data_validator_extension_static_contract_autodl_verification_passed",
        "github_pushed_commit=392fed1dac2b20d51bf7afd070c14ac1c3a69083",
        "autodl_CAMP_HEAD_after_sync=392fed1dac2b20d51bf7afd070c14ac1c3a69083",
        "autodl_CAMP_origin_main_after_sync=392fed1dac2b20d51bf7afd070c14ac1c3a69083",
        "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_target_pytest_result=7 passed",
        "autodl_target_pytest_exit=0",
        "autodl_py_compile_exit=0",
        "autodl_git_diff_check_exit=0",
        "validator_extension_static_contract_current_head_complete=True",
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


def test_static_review_next_gate_unit_tests_plan_only() -> None:
    text = _review()

    for needle in [
        "status=fallback_risk_training_data_validator_extension_static_contract_review_passed",
        "status=fallback_risk_training_data_validator_extension_static_contract_current_head_8f25fe4_revalidated",
        "status=fallback_risk_training_data_validator_extension_static_contract_current_head_b45e849_revalidated",
        "status=fallback_risk_training_data_validator_extension_static_contract_current_head_d529235_revalidated",
        "status=fallback_risk_training_data_validator_extension_static_contract_current_head_8268b98_revalidated",
        "status=fallback_risk_training_data_validator_extension_static_contract_current_head_56600ab_revalidated",
        "status=fallback_risk_training_data_validator_extension_static_contract_current_head_7862caa_revalidated",
        "blocking_contract_findings=0",
        "require_validator_unit_tests_plan=True",
        "require_validator_synthetic_unit_tests=True",
        "require_implementation_authorization_after_tests=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_unit_tests_plan_only",
        "may only plan synthetic unit tests",
        "must not implement the validator",
        "run replay",
        "generate\ncandidates",
        "train CAMP",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_current_head_static_contract_review() -> None:
    text = _iteration_audit()
    tail = text

    for needle in [
        "Current Tail Confirmation After Current HEAD Fallback Risk Training Data Validator Extension Static Contract Review",
        "status=fallback_risk_training_data_validator_extension_static_contract_current_head_56600ab_revalidated",
        "head_56600ab_static_review_revalidation_base_head=56600ab8ec958311397948c21e7a549927b4265a",
        "head_56600ab_github_refs_heads_main_at_revalidation=56600ab8ec958311397948c21e7a549927b4265a",
        "head_56600ab_autodl_CAMP_HEAD_at_revalidation=56600ab8ec958311397948c21e7a549927b4265a",
        "head_56600ab_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "head_56600ab_validator_extension_plan_status=fallback_risk_training_data_validator_extension_plan_current_head_ea68e5b_revalidated",
        "head_56600ab_accepted_dataset_sha256=aff45e48340741ed976eaeaadc383fa794d7a0a769fcaebde3a90a20cae9caa6",
        "head_56600ab_local_target_pytest=7 passed",
        "static_contract_review_complete=True",
        "blocking_contract_findings=0",
        "validator_extension_implementation_authorized=False",
        "validator_extension_unit_tests_plan_authorized_next=True",
        "camp_retraining_authorized=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_unit_tests_plan_only",
    ]:
        assert needle in tail


def test_static_review_eof_records_current_head_7862caa_review() -> None:
    tail = "\n".join(_review().splitlines()[-100:])

    for needle in [
        "Current-Head Static Contract Revalidation After 2aec4e8 Validator Plan Sync",
        "status=fallback_risk_training_data_validator_extension_static_contract_current_head_7862caa_revalidated",
        "head_7862caa_static_review_revalidation_base_head=7862caaf1edc4dd5ca83e7fbd468aafd631703b7",
        "head_7862caa_validator_extension_plan_status=fallback_risk_training_data_validator_extension_plan_current_head_2aec4e8_revalidated",
        "head_7862caa_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f99da50_20260626T153546Z/dataset.json",
        "head_7862caa_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "blocking_contract_findings=0",
        "validator_extension_implementation_authorized=False",
        "validator_extension_unit_tests_plan_authorized_next=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_unit_tests_plan_only",
    ]:
        assert needle in tail


def test_iteration_audit_eof_records_current_head_7862caa_static_review() -> None:
    tail = _iteration_audit()

    for needle in [
        "Current Tail Confirmation After Current HEAD Fallback Risk Training Data Validator Extension Static Contract Review",
        "status=fallback_risk_training_data_validator_extension_static_contract_current_head_7862caa_revalidated",
        "head_7862caa_static_review_revalidation_base_head=7862caaf1edc4dd5ca83e7fbd468aafd631703b7",
        "head_7862caa_validator_extension_plan_status=fallback_risk_training_data_validator_extension_plan_current_head_2aec4e8_revalidated",
        "head_7862caa_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f99da50_20260626T153546Z/dataset.json",
        "head_7862caa_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "blocking_contract_findings=0",
        "validator_extension_implementation_authorized=False",
        "validator_extension_unit_tests_plan_authorized_next=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_unit_tests_plan_only",
    ]:
        assert needle in tail
