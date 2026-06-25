from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_implementation_authorization.md"
)


def _auth() -> str:
    return AUTH_DOC.read_text(encoding="utf-8")


def test_current_head_e5cc047_authorization_revalidation_is_pinned() -> None:
    text = _auth()

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_implementation_authorization_head_e5cc047_revalidated",
        "authorization_base_head=e5cc047a3f4c9e7a7d2b51ad77686ef8631895ce",
        "camp_origin_main_at_head_e5cc047_authorization=e5cc047a3f4c9e7a7d2b51ad77686ef8631895ce",
        "github_refs_heads_main_at_head_e5cc047_authorization=e5cc047a3f4c9e7a7d2b51ad77686ef8631895ce",
        "autodl_CAMP_HEAD_at_head_e5cc047_authorization=e5cc047a3f4c9e7a7d2b51ad77686ef8631895ce",
        "autodl_CAMP_origin_main_at_head_e5cc047_authorization=e5cc047a3f4c9e7a7d2b51ad77686ef8631895ce",
        "autodl_DP_HEAD_at_head_e5cc047_authorization=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "audit_eof_prior_status=fallback_risk_training_data_training_sufficiency_unit_tests_current_head_0976c15_revalidated",
        "head_e5cc047_validated_fallback_dataset_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "head_e5cc047_implementation_authorized=True",
        "head_e5cc047_fallback_risk_training_sufficiency_preflight_implementation_authorized=True",
        "head_e5cc047_default_off_required=True",
        "head_e5cc047_read_only_manifest_inputs_only=True",
        "head_e5cc047_must_return_before_reading_inputs_when_disabled=True",
        "head_e5cc047_must_fail_closed_on_formal_seeds_or_formal_eval_leakage=True",
        "head_e5cc047_must_preserve_score_k_equals_a_k_transpose_w_boundary=True",
        "head_e5cc047_score_k(w)=a_k^T w",
        "head_e5cc047_a_k_nonnegative_benders_compatible_atoms_only=True",
        "head_e5cc047_simplex_master_convex_if_later_authorized=True",
        "head_e5cc047_cvar_master_convex_if_later_authorized=True",
        "head_e5cc047_l2_regularized_master_convex_if_later_authorized=True",
        "head_e5cc047_local_target_pytest=23 passed",
        "head_e5cc047_training_not_executed=True",
        "head_e5cc047_candidate_generation_not_executed=True",
        "head_e5cc047_dp_not_modified=True",
        "head_e5cc047_selector_or_atom_not_promoted=True",
        "head_e5cc047_camp_training_authorized=False",
        "head_e5cc047_camp_retraining_authorized=False",
        "head_e5cc047_formal_seeds_11_12_13_authorized=False",
        "head_e5cc047_safety_benefit_claim_authorized=False",
        "head_e5cc047_camp_over_dp_top1_claim_authorized=False",
        "this_authorization_gate_authorizes_preflight_implementation_only=True",
        "this_authorization_gate_authorizes_training_replay_dp_or_claims=False",
    ]:
        assert needle in text


def test_current_head_dd18260_authorization_revalidation_is_pinned() -> None:
    text = _auth()

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_implementation_authorization_head_dd18260_revalidated",
        "authorization_base_head=dd18260f89691f94387ecaaacdba9011a676ebb6",
        "camp_origin_main_at_head_dd18260_authorization=dd18260f89691f94387ecaaacdba9011a676ebb6",
        "github_refs_heads_main_at_head_dd18260_authorization=dd18260f89691f94387ecaaacdba9011a676ebb6",
        "autodl_CAMP_HEAD_at_head_dd18260_authorization=dd18260f89691f94387ecaaacdba9011a676ebb6",
        "autodl_CAMP_origin_main_at_head_dd18260_authorization=dd18260f89691f94387ecaaacdba9011a676ebb6",
        "autodl_DP_HEAD_at_head_dd18260_authorization=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "audit_eof_prior_status=fallback_risk_training_data_training_sufficiency_unit_tests_current_head_8413ae4_revalidated",
        "head_dd18260_validated_fallback_dataset_sha256=682d432f742d4ab68a262cf70955981bc1562cf1dbcf2ec094984a12fcd11498",
        "head_dd18260_implementation_authorized=True",
        "head_dd18260_fallback_risk_training_sufficiency_preflight_implementation_authorized=True",
        "head_dd18260_default_off_required=True",
        "head_dd18260_read_only_manifest_inputs_only=True",
        "head_dd18260_may_add_read_only_preflight_script=True",
        "head_dd18260_may_add_targeted_synthetic_tests=True",
        "head_dd18260_must_return_before_reading_inputs_when_disabled=True",
        "head_dd18260_must_fail_closed_on_formal_seeds_or_formal_eval_leakage=True",
        "head_dd18260_must_preserve_score_k_equals_a_k_transpose_w_boundary=True",
        "head_dd18260_score_k(w)=a_k^T w",
        "head_dd18260_a_k_nonnegative_benders_compatible_atoms_only=True",
        "head_dd18260_simplex_master_convex_if_later_authorized=True",
        "head_dd18260_cvar_master_convex_if_later_authorized=True",
        "head_dd18260_l2_regularized_master_convex_if_later_authorized=True",
        "head_dd18260_local_authorization_pytest=7 passed",
        "head_dd18260_local_training_sufficiency_contract_pytest=17 passed",
        "head_dd18260_local_unit_tests_plan_pytest=6 passed",
        "head_dd18260_local_target_pytest=30 passed",
        "head_dd18260_training_not_executed=True",
        "head_dd18260_candidate_generation_not_executed=True",
        "head_dd18260_dp_not_modified=True",
        "head_dd18260_selector_or_atom_not_promoted=True",
        "head_dd18260_camp_training_authorized=False",
        "head_dd18260_camp_retraining_authorized=False",
        "head_dd18260_formal_seeds_11_12_13_authorized=False",
        "head_dd18260_safety_benefit_claim_authorized=False",
        "head_dd18260_camp_over_dp_top1_claim_authorized=False",
        "this_authorization_gate_authorizes_preflight_implementation_only=True",
        "this_authorization_gate_authorizes_training_replay_dp_or_claims=False",
    ]:
        assert needle in text


def test_authorization_records_preconditions_and_verified_tests() -> None:
    text = _auth()

    for needle in [
        "training_sufficiency_plan_ready=True",
        "training_sufficiency_static_contract_review_passed=True",
        "training_sufficiency_unit_tests_plan_ready=True",
        "training_sufficiency_contract_tests_pinned=True",
        "blocking_contract_findings=0",
        "validated_fallback_records=15",
        "local_training_sufficiency_contract_pytest=7 passed",
        "local_fallback_risk_pytest=164 passed",
        "autodl_training_sufficiency_contract_pytest=7 passed",
        "autodl_fallback_risk_pytest=164 passed",
        "dp_fixed_commit_verified=True",
        "current_training_sufficiency_plan_ready=True",
        "current_training_sufficiency_static_contract_review_passed=True",
        "current_training_sufficiency_unit_tests_plan_ready=True",
        "current_training_sufficiency_contract_tests_pinned=True",
        "current_blocking_contract_findings=0",
        "current_validated_fallback_dataset_sha256=0978687b1f7582f6644eb9598bdc5a9e03494ad227d1627bd603d54e15efb8e2",
        "current_local_training_sufficiency_contract_pytest=7 passed",
        "current_local_training_sufficiency_plan_static_pytest=19 passed",
        "current_autodl_training_sufficiency_contract_pytest=7 passed",
        "current_autodl_training_sufficiency_plan_static_pytest=19 passed",
        "current_dp_fixed_commit_verified=True",
        "latest_training_sufficiency_plan_ready=True",
        "latest_training_sufficiency_static_contract_review_passed=True",
        "latest_training_sufficiency_unit_tests_plan_ready=True",
        "latest_training_sufficiency_contract_tests_pinned=True",
        "latest_blocking_contract_findings=0",
        "latest_validated_fallback_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "latest_local_training_sufficiency_contract_pytest=7 passed",
        "latest_local_training_sufficiency_plan_static_pytest=25 passed",
        "latest_autodl_training_sufficiency_contract_pytest=7 passed",
        "latest_autodl_training_sufficiency_plan_static_pytest=25 passed",
        "latest_dp_fixed_commit_verified=True",
        "camp_head_at_latest_revalidation=ba8c50ec6baeff9319ccb458bac0a8dcd277903b",
        "autodl_DP_HEAD_at_latest_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    ]:
        assert needle in text


def test_authorization_only_allows_default_off_read_only_preflight() -> None:
    text = _auth()

    for needle in [
        "implementation_authorized=True",
        "fallback_risk_training_sufficiency_preflight_implementation_authorized=True",
        "default_off_required=True",
        "read_only_manifest_inputs_only=True",
        "reads_validated_dataset_summary_json_only=True",
        "reads_training_split_manifest_json_only=True",
        "reads_train_only_scale_manifest_json_only=True",
        "reads_fallback_master_config_json_only=True",
        "reads_training_command_plan_json_only=True",
        "output_json_or_markdown_only=True",
        "current_implementation_authorized=True",
        "current_fallback_risk_training_sufficiency_preflight_implementation_authorized=True",
        "current_default_off_required=True",
        "current_read_only_manifest_inputs_only=True",
        "current_reads_validated_dataset_summary_json_only=True",
        "current_reads_training_split_manifest_json_only=True",
        "current_reads_train_only_scale_manifest_json_only=True",
        "current_reads_fallback_master_config_json_only=True",
        "current_reads_training_command_plan_json_only=True",
        "current_output_json_or_markdown_only=True",
        "latest_implementation_authorized=True",
        "latest_fallback_risk_training_sufficiency_preflight_implementation_authorized=True",
        "latest_default_off_required=True",
        "latest_read_only_manifest_inputs_only=True",
        "latest_reads_validated_dataset_summary_json_only=True",
        "latest_reads_training_split_manifest_json_only=True",
        "latest_reads_train_only_scale_manifest_json_only=True",
        "latest_reads_fallback_master_config_json_only=True",
        "latest_reads_training_command_plan_json_only=True",
        "latest_output_json_or_markdown_only=True",
        "latest_synthetic_unit_tests_required=True",
        "latest_existing_contract_tests_must_continue_to_pass=True",
    ]:
        assert needle in text


def test_authorization_requires_fail_closed_contracts() -> None:
    text = _auth()

    for needle in [
        "must_return_before_reading_inputs_when_disabled=True",
        "must_fail_closed_on_missing_or_invalid_validated_dataset_summary=True",
        "must_fail_closed_on_missing_split_manifest_or_group_overlap=True",
        "must_fail_closed_on_formal_seeds_or_formal_eval_leakage=True",
        "must_fail_closed_on_validation_or_formal_scale_fit_leakage=True",
        "must_fail_closed_on_nonpositive_scales_or_atom_schema_mismatch=True",
        "must_fail_closed_on_fallback_master_feasible_branch_leakage=True",
        "must_fail_closed_on_training_command_execution_or_dp_modification_flags=True",
        "must_reject_selector_atom_promotion_or_claim_flags=True",
        "must_preserve_score_k_equals_a_k_transpose_w_boundary=True",
        "current_must_return_before_reading_inputs_when_disabled=True",
        "current_must_fail_closed_on_missing_or_invalid_validated_dataset_summary=True",
        "current_must_fail_closed_on_missing_split_manifest_or_group_overlap=True",
        "current_must_fail_closed_on_formal_seeds_or_formal_eval_leakage=True",
        "current_must_fail_closed_on_validation_or_formal_scale_fit_leakage=True",
        "current_must_fail_closed_on_nonpositive_scales_or_atom_schema_mismatch=True",
        "current_must_fail_closed_on_fallback_master_feasible_branch_leakage=True",
        "current_must_fail_closed_on_training_command_execution_or_dp_modification_flags=True",
        "current_must_reject_selector_atom_promotion_or_claim_flags=True",
        "current_must_preserve_score_k_equals_a_k_transpose_w_boundary=True",
        "latest_must_return_before_reading_inputs_when_disabled=True",
        "latest_must_fail_closed_on_missing_or_invalid_validated_dataset_summary=True",
        "latest_must_fail_closed_on_missing_split_manifest_or_group_overlap=True",
        "latest_must_fail_closed_on_formal_seeds_or_formal_eval_leakage=True",
        "latest_must_fail_closed_on_validation_or_formal_scale_fit_leakage=True",
        "latest_must_fail_closed_on_nonpositive_scales_or_atom_schema_mismatch=True",
        "latest_must_fail_closed_on_fallback_master_feasible_branch_leakage=True",
        "latest_must_fail_closed_on_training_command_execution_or_dp_modification_flags=True",
        "latest_must_reject_selector_atom_promotion_or_claim_flags=True",
        "latest_must_preserve_score_k_equals_a_k_transpose_w_boundary=True",
    ]:
        assert needle in text


def test_authorization_keeps_training_dp_and_promotion_forbidden() -> None:
    text = _auth()

    for needle in [
        "training_authorized=False",
        "camp_retraining_authorized_now=False",
        "replay_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "production_selector_change_authorized=False",
        "camp_training_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "current_training_authorized=False",
        "current_camp_retraining_authorized_now=False",
        "current_replay_authorized=False",
        "current_candidate_generation_authorized=False",
        "current_dp_modification_authorized=False",
        "current_production_selector_change_authorized=False",
        "current_camp_training_authorized=False",
        "current_formal_seeds_11_12_13_authorized=False",
        "current_selector_promotion_authorized=False",
        "current_atom_promotion_authorized=False",
        "current_safety_benefit_claim_authorized=False",
        "current_camp_over_dp_top1_claim_authorized=False",
        "user_broad_execution_permission_recorded=True",
        "this_authorization_gate_authorizes_preflight_implementation_only=True",
        "this_authorization_gate_authorizes_training_replay_dp_or_claims=False",
        "latest_training_authorized=False",
        "latest_camp_retraining_authorized_now=False",
        "latest_replay_authorized=False",
        "latest_candidate_generation_authorized=False",
        "latest_dp_modification_authorized=False",
        "latest_production_selector_change_authorized=False",
        "latest_camp_training_authorized=False",
        "latest_formal_seeds_11_12_13_authorized=False",
        "latest_selector_promotion_authorized=False",
        "latest_atom_promotion_authorized=False",
        "latest_safety_benefit_claim_authorized=False",
        "latest_camp_over_dp_top1_claim_authorized=False",
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
        "status=fallback_risk_training_sufficiency_preflight_implementation_authorized",
        "status=fallback_risk_training_sufficiency_preflight_implementation_authorization_latest_head_revalidated",
        "passed=True",
        "implementation_authorized=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_implementation_only",
        "may only implement the minimal default-off read-only preflight",
        "must not train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
        "promote",
    ]:
        assert needle in text
