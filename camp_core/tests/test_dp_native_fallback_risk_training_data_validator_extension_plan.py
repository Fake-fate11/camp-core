from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_plan.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def _iteration_audit() -> str:
    return ITERATION_AUDIT.read_text(encoding="utf-8")


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
        "latest_plan_revalidation_base_head=02417e1b5783b5f2f1ffc9f095d3fe4ddd32d06d",
        "latest_autodl_CAMP_HEAD_at_revalidation=02417e1b5783b5f2f1ffc9f095d3fe4ddd32d06d",
        "latest_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_fixed_artifact_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_autodl_verification_passed",
        "latest_accepted_fallback_records=15",
        "latest_accepted_dataset_schema_version=dp_native_fallback_risk_training_data_v1",
        "latest_accepted_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "latest_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_6adb800_20260625T020016Z/dataset.json",
        "current_plan_revalidation_base_head=0cc51ce7b323e207f5282c040c3d8c10062f27a9",
        "current_camp_origin_main_at_revalidation=0cc51ce7b323e207f5282c040c3d8c10062f27a9",
        "current_github_refs_heads_main_at_revalidation=0cc51ce7b323e207f5282c040c3d8c10062f27a9",
        "current_autodl_CAMP_HEAD_at_revalidation=0cc51ce7b323e207f5282c040c3d8c10062f27a9",
        "current_autodl_CAMP_origin_main_at_revalidation=0cc51ce7b323e207f5282c040c3d8c10062f27a9",
        "current_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_fixed_artifact_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_autodl_verification_passed",
        "current_accepted_fallback_records=15",
        "current_accepted_dataset_schema_version=dp_native_fallback_risk_training_data_v1",
        "current_accepted_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "current_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_da0e617_20260625T080225Z/dataset.json",
        "f0fc2dc_plan_revalidation_base_head=f0fc2dcc13bb46d2ed62bd00a747703c287c3f03",
        "f0fc2dc_camp_origin_main_at_revalidation=f0fc2dcc13bb46d2ed62bd00a747703c287c3f03",
        "f0fc2dc_github_refs_heads_main_at_revalidation=f0fc2dcc13bb46d2ed62bd00a747703c287c3f03",
        "f0fc2dc_autodl_CAMP_HEAD_at_revalidation=f0fc2dcc13bb46d2ed62bd00a747703c287c3f03",
        "f0fc2dc_autodl_CAMP_origin_main_at_revalidation=f0fc2dcc13bb46d2ed62bd00a747703c287c3f03",
        "f0fc2dc_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "f0fc2dc_fixed_artifact_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_e35f1e4_passed",
        "f0fc2dc_accepted_fallback_records=15",
        "f0fc2dc_accepted_dataset_schema_version=dp_native_fallback_risk_training_data_v1",
        "f0fc2dc_accepted_dataset_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "f0fc2dc_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_e35f1e4_20260625T132102Z/dataset.json",
        "current_8635158_plan_revalidation_base_head=863515890cd6e5124aac17c7df1e27448c121b4f",
        "current_8635158_camp_origin_main_at_revalidation=863515890cd6e5124aac17c7df1e27448c121b4f",
        "current_8635158_github_refs_heads_main_at_revalidation=863515890cd6e5124aac17c7df1e27448c121b4f",
        "current_8635158_autodl_CAMP_HEAD_at_revalidation=863515890cd6e5124aac17c7df1e27448c121b4f",
        "current_8635158_autodl_CAMP_origin_main_at_revalidation=863515890cd6e5124aac17c7df1e27448c121b4f",
        "current_8635158_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_8635158_fixed_artifact_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_bbba35b_passed",
        "current_8635158_accepted_fallback_records=15",
        "current_8635158_accepted_dataset_schema_version=dp_native_fallback_risk_training_data_v1",
        "current_8635158_accepted_dataset_sha256=682d432f742d4ab68a262cf70955981bc1562cf1dbcf2ec094984a12fcd11498",
        "current_8635158_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_bbba35b_20260625T174901Z/dataset.json",
        "head_94f224b_plan_revalidation_base_head=94f224b02315911b8829684b1a006644f452b907",
        "head_94f224b_camp_origin_main_at_revalidation=94f224b02315911b8829684b1a006644f452b907",
        "head_94f224b_github_refs_heads_main_at_revalidation=94f224b02315911b8829684b1a006644f452b907",
        "head_94f224b_autodl_CAMP_HEAD_at_revalidation=94f224b02315911b8829684b1a006644f452b907",
        "head_94f224b_autodl_CAMP_origin_main_at_revalidation=94f224b02315911b8829684b1a006644f452b907",
        "head_94f224b_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "head_94f224b_fixed_artifact_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_4751222_passed",
        "head_94f224b_accepted_fallback_records=15",
        "head_94f224b_accepted_dataset_schema_version=dp_native_fallback_risk_training_data_v1",
        "head_94f224b_accepted_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_94f224b_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_4751222_20260625T213641Z/dataset.json",
        "head_ea68e5b_plan_revalidation_base_head=ea68e5b70b2e91e1c92267b54692a145d5bdfb3c",
        "head_ea68e5b_camp_origin_main_at_revalidation=ea68e5b70b2e91e1c92267b54692a145d5bdfb3c",
        "head_ea68e5b_github_refs_heads_main_at_revalidation=ea68e5b70b2e91e1c92267b54692a145d5bdfb3c",
        "head_ea68e5b_autodl_CAMP_HEAD_at_revalidation=ea68e5b70b2e91e1c92267b54692a145d5bdfb3c",
        "head_ea68e5b_autodl_CAMP_origin_main_at_revalidation=ea68e5b70b2e91e1c92267b54692a145d5bdfb3c",
        "head_ea68e5b_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "head_ea68e5b_fixed_artifact_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_8e50989_passed",
        "head_ea68e5b_accepted_fallback_records=15",
        "head_ea68e5b_accepted_dataset_schema_version=dp_native_fallback_risk_training_data_v1",
        "head_ea68e5b_accepted_dataset_sha256=aff45e48340741ed976eaeaadc383fa794d7a0a769fcaebde3a90a20cae9caa6",
        "head_ea68e5b_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_8e50989_20260626T084333Z/dataset.json",
        "head_2aec4e8_plan_revalidation_base_head=2aec4e859169a72ad8bcc8b308936ae59cfa4d8c",
        "head_2aec4e8_camp_origin_main_at_revalidation=2aec4e859169a72ad8bcc8b308936ae59cfa4d8c",
        "head_2aec4e8_github_refs_heads_main_at_revalidation=2aec4e859169a72ad8bcc8b308936ae59cfa4d8c",
        "head_2aec4e8_autodl_CAMP_HEAD_at_revalidation=2aec4e859169a72ad8bcc8b308936ae59cfa4d8c",
        "head_2aec4e8_autodl_CAMP_origin_main_at_revalidation=2aec4e859169a72ad8bcc8b308936ae59cfa4d8c",
        "head_2aec4e8_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "head_2aec4e8_fixed_artifact_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_f99da50_passed",
        "head_2aec4e8_accepted_fallback_records=15",
        "head_2aec4e8_accepted_dataset_schema_version=dp_native_fallback_risk_training_data_v1",
        "head_2aec4e8_accepted_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_2aec4e8_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f99da50_20260626T153546Z/dataset.json",
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
        "user_broad_execution_permission_recorded=True",
        "this_plan_gate_authorizes_broad_execution=False",
        "validator_extension_static_contract_review_authorized_next=True",
        "current_local_target_pytest=8 passed",
        "current_local_py_compile_exit=0",
        "current_local_git_diff_check_exit=0",
        "f0fc2dc_local_target_pytest=44 passed",
        "f0fc2dc_local_py_compile_exit=0",
        "f0fc2dc_local_git_diff_check_exit=0",
        "current_8635158_local_target_pytest=8 passed",
        "current_8635158_local_py_compile_exit=0",
        "current_8635158_local_git_diff_check_exit=0",
        "head_94f224b_local_target_pytest=138 passed",
        "head_94f224b_local_py_compile_exit=0",
        "head_94f224b_local_git_diff_check_exit=0",
        "head_94f224b_autodl_target_pytest=138 passed",
        "head_94f224b_autodl_py_compile_exit=0",
        "head_94f224b_autodl_git_diff_check_exit=0",
        "head_ea68e5b_local_target_pytest=8 passed",
        "head_ea68e5b_local_py_compile_exit=0",
        "head_ea68e5b_local_git_diff_check_exit=0",
        "head_ea68e5b_autodl_target_pytest=8 passed",
        "head_ea68e5b_autodl_py_compile_exit=0",
        "head_ea68e5b_autodl_git_diff_check_exit=0",
        "head_2aec4e8_local_target_pytest=10 passed",
        "head_2aec4e8_local_py_compile_exit=0",
        "head_2aec4e8_local_git_diff_check_exit=0",
        "latest_local_target_pytest=7 passed",
        "latest_autodl_target_pytest=7 passed",
        "status=fallback_risk_training_data_validator_extension_plan_autodl_verification_passed",
        "github_pushed_commit=175b75d8bd32d220b3b0dc6b4d40c8aa94c3be5a",
        "autodl_CAMP_HEAD_after_sync=175b75d8bd32d220b3b0dc6b4d40c8aa94c3be5a",
        "autodl_CAMP_origin_main_after_sync=175b75d8bd32d220b3b0dc6b4d40c8aa94c3be5a",
        "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_target_pytest_result=8 passed",
        "autodl_target_pytest_exit=0",
        "autodl_py_compile_exit=0",
        "autodl_git_diff_check_exit=0",
        "validator_extension_plan_current_head_complete=True",
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
        "status=fallback_risk_training_data_validator_extension_plan_current_head_0cc51ce_revalidated",
        "status=fallback_risk_training_data_validator_extension_plan_current_head_f0fc2dc_revalidated",
        "status=fallback_risk_training_data_validator_extension_plan_current_head_8635158_revalidated",
        "status=fallback_risk_training_data_validator_extension_plan_current_head_94f224b_revalidated",
        "status=fallback_risk_training_data_validator_extension_plan_current_head_ea68e5b_revalidated",
        "status=fallback_risk_training_data_validator_extension_plan_current_head_2aec4e8_revalidated",
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


def test_iteration_audit_tail_records_current_head_plan_revalidation() -> None:
    text = _iteration_audit()
    tail = text

    for needle in [
        "Current Tail Confirmation After Current HEAD Fallback Risk Training Data Validator Extension Plan",
        "status=fallback_risk_training_data_validator_extension_plan_current_head_ea68e5b_revalidated",
        "head_ea68e5b_plan_revalidation_base_head=ea68e5b70b2e91e1c92267b54692a145d5bdfb3c",
        "head_ea68e5b_github_refs_heads_main_at_revalidation=ea68e5b70b2e91e1c92267b54692a145d5bdfb3c",
        "head_ea68e5b_autodl_CAMP_HEAD_at_revalidation=ea68e5b70b2e91e1c92267b54692a145d5bdfb3c",
        "head_ea68e5b_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "head_ea68e5b_fixed_artifact_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_8e50989_passed",
        "head_ea68e5b_accepted_dataset_sha256=aff45e48340741ed976eaeaadc383fa794d7a0a769fcaebde3a90a20cae9caa6",
        "head_ea68e5b_local_target_pytest=8 passed",
        "validator_extension_implementation_authorized=False",
        "validator_extension_static_contract_review_authorized_next=True",
        "camp_retraining_authorized=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_static_contract_review_only",
    ]:
        assert needle in tail


def test_validator_extension_plan_eof_records_current_head_2aec4e8_plan() -> None:
    tail = "\n".join(_plan().splitlines()[-100:])

    for needle in [
        "Current-Head Plan Revalidation After f99da50 Builder Acceptance",
        "status=fallback_risk_training_data_validator_extension_plan_current_head_2aec4e8_revalidated",
        "head_2aec4e8_plan_revalidation_base_head=2aec4e859169a72ad8bcc8b308936ae59cfa4d8c",
        "head_2aec4e8_fixed_artifact_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_f99da50_passed",
        "head_2aec4e8_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f99da50_20260626T153546Z/dataset.json",
        "head_2aec4e8_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "validator_extension_implementation_authorized=False",
        "validator_extension_static_contract_review_authorized_next=True",
        "fallback_dataset_training_sufficiency_claim=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_static_contract_review_only",
    ]:
        assert needle in tail


def test_iteration_audit_eof_records_current_head_2aec4e8_plan() -> None:
    tail = "\n".join(_iteration_audit().splitlines()[-100:])

    for needle in [
        "Current Tail Confirmation After Current HEAD Fallback Risk Training Data Validator Extension Plan",
        "status=fallback_risk_training_data_validator_extension_plan_current_head_2aec4e8_revalidated",
        "head_2aec4e8_plan_revalidation_base_head=2aec4e859169a72ad8bcc8b308936ae59cfa4d8c",
        "head_2aec4e8_fixed_artifact_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_f99da50_passed",
        "head_2aec4e8_accepted_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f99da50_20260626T153546Z/dataset.json",
        "head_2aec4e8_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "validator_extension_implementation_authorized=False",
        "validator_extension_static_contract_review_authorized_next=True",
        "fallback_dataset_training_sufficiency_claim=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_static_contract_review_only",
    ]:
        assert needle in tail
