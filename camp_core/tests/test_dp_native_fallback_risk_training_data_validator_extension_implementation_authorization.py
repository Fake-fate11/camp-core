from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_implementation_authorization.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _auth() -> str:
    return AUTH_DOC.read_text(encoding="utf-8")


def _iteration_audit() -> str:
    return ITERATION_AUDIT.read_text(encoding="utf-8")


def test_authorization_records_reviewed_evidence_and_preconditions() -> None:
    text = _auth()

    for needle in [
        "validator_extension_plan_ready=True",
        "validator_extension_static_contract_review_passed=True",
        "validator_extension_unit_tests_plan_ready=True",
        "validator_extension_contract_tests_pinned=True",
        "blocking_contract_findings=0",
        "local_validator_contract_pytest=5 passed",
        "local_fallback_risk_pytest=118 passed",
        "autodl_validator_contract_pytest=5 passed",
        "autodl_fallback_risk_pytest=118 passed",
        "dp_fixed_commit_verified=True",
        "autodl_DP_HEAD_at_authorization=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_validator_unit_tests_status=fallback_risk_training_data_validator_extension_unit_tests_current_head_revalidated",
        "autodl_target_pytest=10 passed",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_authorization_revalidation_base_head=f52b518610ff83043d9a60858ed38fad7dd6e8d8",
        "latest_autodl_CAMP_HEAD_at_revalidation=f52b518610ff83043d9a60858ed38fad7dd6e8d8",
        "latest_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_validator_unit_tests_status=fallback_risk_training_data_validator_extension_unit_tests_autodl_verification_passed",
        "latest_local_target_pytest=11 passed",
        "latest_autodl_target_pytest=11 passed",
        "current_authorization_revalidation_base_head=9260058775a9a163985b54434b774190d91cb37a",
        "current_camp_origin_main_at_revalidation=9260058775a9a163985b54434b774190d91cb37a",
        "current_github_refs_heads_main_at_revalidation=9260058775a9a163985b54434b774190d91cb37a",
        "current_autodl_CAMP_HEAD_at_revalidation=9260058775a9a163985b54434b774190d91cb37a",
        "current_autodl_CAMP_origin_main_at_revalidation=9260058775a9a163985b54434b774190d91cb37a",
        "current_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_validator_unit_tests_status=fallback_risk_training_data_validator_extension_unit_tests_autodl_verification_passed",
        "current_local_target_pytest=6 passed",
        "current_local_py_compile_exit=0",
        "current_local_git_diff_check_exit=0",
        "status=fallback_risk_training_data_validator_extension_implementation_authorization_autodl_verification_passed",
        "github_pushed_commit=5e2bbf2f934586a11d22270fe37d894066de72f6",
        "autodl_CAMP_HEAD_after_sync=5e2bbf2f934586a11d22270fe37d894066de72f6",
        "autodl_CAMP_origin_main_after_sync=5e2bbf2f934586a11d22270fe37d894066de72f6",
        "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_target_pytest_result=6 passed",
        "autodl_py_compile_exit=0",
        "autodl_git_diff_check_exit=0",
    ]:
        assert needle in text


def test_authorization_allows_only_minimal_read_only_validator() -> None:
    text = _auth()

    for needle in [
        "implementation_authorized=True",
        "fallback_risk_training_data_validator_extension_implementation_authorized=True",
        "default_off_required=True",
        "read_only_dataset_json_input_only=True",
        "read_only_source_log_readback_only=True",
        "source_log_readback_required_for_acceptance=True",
        "output_json_or_markdown_only=True",
        "synthetic_unit_tests_required=True",
        "training_authorized=False",
        "replay_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "production_selector_change_authorized=False",
        "user_broad_execution_permission_recorded=True",
        "this_authorization_gate_authorizes_validator_implementation_only=True",
        "this_authorization_gate_authorizes_training_replay_dp_or_claims=False",
    ]:
        assert needle in text


def test_authorization_requires_fail_closed_validator_contract() -> None:
    text = _auth()

    for needle in [
        "must_fail_closed_on_schema_status_count_and_hash_mismatch=True",
        "must_fail_closed_on_source_feasible_mask_any_true_or_non_bool=True",
        "must_fail_closed_on_candidate_generation_or_provenance_violation=True",
        "must_fail_closed_on_atom_schema_or_nonnegative_matrix_violation=True",
        "must_reject_training_selector_atom_promotion_or_claim_flags=True",
        "must_preserve_score_k_equals_a_k_transpose_w_boundary=True",
        "must_keep_fallback_dataset_separate_from_feasible_master=True",
    ]:
        assert needle in text


def test_authorization_forbids_training_dp_and_claims() -> None:
    text = _auth()

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
        "fallback_risk_training_authorized_now=False",
        "feasible_ranking_master_change_authorized=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
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


def test_authorization_next_gate_is_implementation_only() -> None:
    text = _auth()

    for needle in [
        "status=fallback_risk_training_data_validator_extension_implementation_authorized",
        "status=fallback_risk_training_data_validator_extension_implementation_authorization_current_head_9260058_revalidated",
        "passed=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_implementation_only",
        "may only implement the minimal default-off read-only validator",
        "targeted synthetic tests",
        "must not run replay",
        "generate\ncandidates",
        "train CAMP",
        "modify Diffusion Planner",
        "promote a selector or atom",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_current_head_implementation_authorization() -> None:
    text = _iteration_audit()

    for needle in [
        "Current Tail Confirmation After Current HEAD Fallback Risk Training Data Validator Extension Implementation Authorization",
        "status=fallback_risk_training_data_validator_extension_implementation_authorization_current_head_9260058_revalidated",
        "current_authorization_revalidation_base_head=9260058775a9a163985b54434b774190d91cb37a",
        "current_github_refs_heads_main_at_revalidation=9260058775a9a163985b54434b774190d91cb37a",
        "current_autodl_CAMP_HEAD_at_revalidation=9260058775a9a163985b54434b774190d91cb37a",
        "current_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_validator_unit_tests_status=fallback_risk_training_data_validator_extension_unit_tests_autodl_verification_passed",
        "implementation_authorized=True",
        "fallback_risk_training_data_validator_extension_implementation_authorized=True",
        "default_off_required=True",
        "read_only_dataset_json_input_only=True",
        "source_log_readback_required_for_acceptance=True",
        "Current Tail Confirmation After AutoDL Fallback Risk Training Data Validator Extension Implementation Authorization Verification",
        "status=fallback_risk_training_data_validator_extension_implementation_authorization_autodl_verification_passed",
        "github_pushed_commit=5e2bbf2f934586a11d22270fe37d894066de72f6",
        "autodl_CAMP_HEAD_after_sync=5e2bbf2f934586a11d22270fe37d894066de72f6",
        "autodl_CAMP_origin_main_after_sync=5e2bbf2f934586a11d22270fe37d894066de72f6",
        "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_target_pytest_result=6 passed",
        "autodl_py_compile_exit=0",
        "autodl_git_diff_check_exit=0",
        "camp_retraining_authorized=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_implementation_only",
    ]:
        assert needle in text
