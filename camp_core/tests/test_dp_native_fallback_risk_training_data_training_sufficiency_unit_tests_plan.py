from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_unit_tests_plan.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_unit_tests_plan_records_preconditions_and_no_training_authorization() -> None:
    text = _plan()

    for needle in [
        "training_sufficiency_plan_ready=True",
        "training_sufficiency_static_contract_review_passed=True",
        "blocking_contract_findings=0",
        "validated_fallback_records=15",
        "fallback_dataset_training_sufficiency_claim=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "current_training_sufficiency_plan_ready=True",
        "current_training_sufficiency_static_contract_review_passed=True",
        "current_blocking_contract_findings=0",
        "current_validated_fallback_records=15",
        "current_validated_fallback_dataset_sha256=0978687b1f7582f6644eb9598bdc5a9e03494ad227d1627bd603d54e15efb8e2",
        "current_fallback_dataset_training_sufficiency_claim=False",
        "current_fallback_risk_training_authorized_now=False",
        "current_camp_retraining_authorized_now=False",
        "latest_training_sufficiency_plan_ready=True",
        "latest_training_sufficiency_static_contract_review_passed=True",
        "latest_blocking_contract_findings=0",
        "latest_validated_fallback_records=15",
        "latest_validated_fallback_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "latest_fallback_dataset_training_sufficiency_claim=False",
        "latest_fallback_risk_training_authorized_now=False",
        "latest_camp_retraining_authorized_now=False",
        "camp_head_at_latest_revalidation=2c640f63fe1a9cce08372c758b5c1558b777015a",
        "autodl_DP_HEAD_at_latest_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_head_training_sufficiency_plan_ready=True",
        "current_head_training_sufficiency_static_contract_review_passed=True",
        "current_head_blocking_contract_findings=0",
        "current_head_validated_fallback_records=15",
        "current_head_validated_fallback_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "current_head_fallback_dataset_training_sufficiency_claim=False",
        "current_head_fallback_risk_training_authorized_now=False",
        "current_head_camp_retraining_authorized_now=False",
        "camp_head_at_current_head_revalidation=30b0dc75930288c043ce892a1df6ec1969127790",
        "autodl_DP_HEAD_at_current_head_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    ]:
        assert needle in text


def test_unit_tests_plan_covers_evidence_split_and_scale_fail_closed_cases() -> None:
    text = _plan()

    for needle in [
        "test_validated_fallback_dataset_is_required=True",
        "test_15_record_artifact_does_not_authorize_training=True",
        "test_rejects_training_sufficiency_claim_without_split=True",
        "test_requires_training_validation_split_manifest=True",
        "test_rejects_train_validation_group_overlap=True",
        "test_rejects_formal_seeds_11_12_13_in_train_or_validation=True",
        "test_requires_train_only_scale_manifest=True",
        "test_rejects_scale_fit_on_validation_groups=True",
        "test_rejects_nonpositive_atom_scales=True",
        "current_test_validated_fallback_dataset_is_required=True",
        "current_test_15_record_artifact_does_not_authorize_training=True",
        "current_test_rejects_training_sufficiency_claim_without_split=True",
        "current_test_rejects_deployable_checkpoint_claim=True",
        "current_test_requires_training_validation_split_manifest=True",
        "current_test_rejects_train_validation_group_overlap=True",
        "current_test_rejects_formal_seeds_11_12_13_in_train_or_validation=True",
        "current_test_requires_train_only_scale_manifest=True",
        "current_test_rejects_scale_fit_on_validation_groups=True",
        "current_test_rejects_nonpositive_atom_scales=True",
        "latest_test_validated_fallback_dataset_is_required=True",
        "latest_test_15_record_artifact_does_not_authorize_training=True",
        "latest_test_rejects_training_sufficiency_claim_without_split=True",
        "latest_test_rejects_deployable_checkpoint_claim=True",
        "latest_test_requires_training_validation_split_manifest=True",
        "latest_test_rejects_train_validation_group_overlap=True",
        "latest_test_rejects_formal_seeds_11_12_13_in_train_or_validation=True",
        "latest_test_requires_train_only_scale_manifest=True",
        "latest_test_rejects_scale_fit_on_validation_groups=True",
        "latest_test_rejects_nonpositive_atom_scales=True",
        "current_head_test_validated_fallback_dataset_is_required=True",
        "current_head_test_15_record_artifact_does_not_authorize_training=True",
        "current_head_test_rejects_training_sufficiency_claim_without_split=True",
        "current_head_test_rejects_deployable_checkpoint_claim=True",
        "current_head_test_requires_training_validation_split_manifest=True",
        "current_head_test_rejects_train_validation_group_overlap=True",
        "current_head_test_rejects_formal_seeds_11_12_13_in_train_or_validation=True",
        "current_head_test_requires_train_only_scale_manifest=True",
        "current_head_test_rejects_scale_fit_on_validation_groups=True",
        "current_head_test_rejects_nonpositive_atom_scales=True",
    ]:
        assert needle in text


def test_unit_tests_plan_covers_fallback_master_and_convex_contract() -> None:
    text = _plan()

    for needle in [
        "test_requires_fallback_only_master_config=True",
        "test_rejects_feasible_branch_records_in_fallback_master=True",
        "test_rejects_all_infeasible_records_added_to_feasible_training=True",
        "test_rejects_hard_feasibility_relaxation=True",
        "test_requires_score_equals_a_transpose_w=True",
        "test_requires_nonnegative_fixed_atoms=True",
        "test_requires_fallback_label_not_deployed_atom=True",
        "test_requires_simplex_cvar_l2_convex_boundary=True",
        "current_test_requires_fallback_only_master_config=True",
        "current_test_rejects_feasible_branch_records_in_fallback_master=True",
        "current_test_rejects_all_infeasible_records_added_to_feasible_training=True",
        "current_test_rejects_hard_feasibility_relaxation=True",
        "current_test_requires_score_equals_a_transpose_w=True",
        "current_test_requires_nonnegative_fixed_atoms=True",
        "current_test_requires_fallback_label_not_deployed_atom=True",
        "current_test_requires_simplex_cvar_l2_convex_boundary=True",
        "latest_test_requires_fallback_only_master_config=True",
        "latest_test_rejects_feasible_branch_records_in_fallback_master=True",
        "latest_test_rejects_all_infeasible_records_added_to_feasible_training=True",
        "latest_test_rejects_hard_feasibility_relaxation=True",
        "latest_test_requires_score_equals_a_transpose_w=True",
        "latest_test_requires_nonnegative_fixed_atoms=True",
        "latest_test_requires_fallback_label_not_deployed_atom=True",
        "latest_test_requires_simplex_cvar_l2_convex_boundary=True",
        "current_head_test_requires_fallback_only_master_config=True",
        "current_head_test_rejects_feasible_branch_records_in_fallback_master=True",
        "current_head_test_rejects_all_infeasible_records_added_to_feasible_training=True",
        "current_head_test_rejects_hard_feasibility_relaxation=True",
        "current_head_test_requires_score_equals_a_transpose_w=True",
        "current_head_test_requires_nonnegative_fixed_atoms=True",
        "current_head_test_requires_fallback_label_not_deployed_atom=True",
        "current_head_test_requires_simplex_cvar_l2_convex_boundary=True",
    ]:
        assert needle in text


def test_unit_tests_plan_covers_training_command_and_nonpromotion_rejections() -> None:
    text = _plan()

    for needle in [
        "test_rejects_training_command_without_prior_authorization=True",
        "test_rejects_replay_or_candidate_generation_commands=True",
        "test_rejects_dp_weight_or_config_changes=True",
        "test_rejects_reference_blend_guidance_or_postselection=True",
        "test_rejects_online_selector_or_atom_promotion=True",
        "test_requires_post_training_nonpromotion_plan=True",
        "test_requires_development_holdout_acceptance_gate=True",
        "current_test_rejects_training_command_without_prior_authorization=True",
        "current_test_rejects_replay_or_candidate_generation_commands=True",
        "current_test_rejects_dp_weight_or_config_changes=True",
        "current_test_rejects_reference_blend_guidance_or_postselection=True",
        "current_test_rejects_online_selector_or_atom_promotion=True",
        "current_test_requires_post_training_nonpromotion_plan=True",
        "current_test_requires_development_holdout_acceptance_gate=True",
        "latest_test_rejects_training_command_without_prior_authorization=True",
        "latest_test_rejects_replay_or_candidate_generation_commands=True",
        "latest_test_rejects_dp_weight_or_config_changes=True",
        "latest_test_rejects_reference_blend_guidance_or_postselection=True",
        "latest_test_rejects_online_selector_or_atom_promotion=True",
        "latest_test_requires_post_training_nonpromotion_plan=True",
        "latest_test_requires_development_holdout_acceptance_gate=True",
        "current_head_test_rejects_training_command_without_prior_authorization=True",
        "current_head_test_rejects_replay_or_candidate_generation_commands=True",
        "current_head_test_rejects_dp_weight_or_config_changes=True",
        "current_head_test_rejects_reference_blend_guidance_or_postselection=True",
        "current_head_test_rejects_online_selector_or_atom_promotion=True",
        "current_head_test_requires_post_training_nonpromotion_plan=True",
        "current_head_test_requires_development_holdout_acceptance_gate=True",
    ]:
        assert needle in text


def test_unit_tests_plan_uses_synthetic_fixtures_only() -> None:
    text = _plan()

    for needle in [
        "synthetic_manifest_fixtures_only=True",
        "synthetic_dataset_summary_fixtures_only=True",
        "fixed_autodl_artifact_required_for_unit_tests=False",
        "formal_seeds_11_12_13_used=False",
        "replay_required_for_unit_tests=False",
        "candidate_generation_required_for_unit_tests=False",
        "training_required_for_unit_tests=False",
        "dp_required_for_unit_tests=False",
        "current_synthetic_manifest_fixtures_only=True",
        "current_synthetic_dataset_summary_fixtures_only=True",
        "current_fixed_autodl_artifact_required_for_unit_tests=False",
        "current_formal_seeds_11_12_13_used=False",
        "current_replay_required_for_unit_tests=False",
        "current_candidate_generation_required_for_unit_tests=False",
        "current_training_required_for_unit_tests=False",
        "current_dp_required_for_unit_tests=False",
        "latest_synthetic_manifest_fixtures_only=True",
        "latest_synthetic_dataset_summary_fixtures_only=True",
        "latest_fixed_autodl_artifact_required_for_unit_tests=False",
        "latest_formal_seeds_11_12_13_used=False",
        "latest_replay_required_for_unit_tests=False",
        "latest_candidate_generation_required_for_unit_tests=False",
        "latest_training_required_for_unit_tests=False",
        "latest_dp_required_for_unit_tests=False",
        "current_head_synthetic_manifest_fixtures_only=True",
        "current_head_synthetic_dataset_summary_fixtures_only=True",
        "current_head_fixed_autodl_artifact_required_for_unit_tests=False",
        "current_head_formal_seeds_11_12_13_used=False",
        "current_head_replay_required_for_unit_tests=False",
        "current_head_candidate_generation_required_for_unit_tests=False",
        "current_head_training_required_for_unit_tests=False",
        "current_head_dp_required_for_unit_tests=False",
    ]:
        assert needle in text


def test_unit_tests_plan_forbids_execution_and_sets_unit_tests_next() -> None:
    text = _plan()
    iteration_tail = ITERATION_AUDIT.read_text(encoding="utf-8")[-12000:]
    combined = text + iteration_tail

    for needle in [
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "status=fallback_risk_training_data_training_sufficiency_unit_tests_plan_ready",
        "training_sufficiency_unit_tests_authorized=True",
        "fallback_risk_training_authorized_now=False",
        "current_status=fallback_risk_training_data_training_sufficiency_unit_tests_plan_ready",
        "current_training_sufficiency_unit_tests_plan_complete=True",
        "current_training_sufficiency_unit_tests_authorized=True",
        "current_fallback_risk_training_authorized_now=False",
        "current_camp_retraining_authorized_now=False",
        "current_fallback_dataset_training_sufficiency_claim=False",
        "user_broad_execution_permission_recorded=True",
        "this_unit_tests_plan_gate_authorizes_training_replay_dp_or_claims=False",
        "latest_replay_execution_authorized=False",
        "latest_candidate_generation_authorized=False",
        "latest_camp_training_authorized=False",
        "latest_camp_retraining_authorized=False",
        "latest_formal_seeds_11_12_13_authorized=False",
        "latest_dp_modification_authorized=False",
        "latest_selector_promotion_authorized=False",
        "latest_atom_promotion_authorized=False",
        "latest_safety_benefit_claim_authorized=False",
        "latest_camp_over_dp_top1_claim_authorized=False",
        "latest_status=fallback_risk_training_data_training_sufficiency_unit_tests_plan_ready",
        "current_head_status=fallback_risk_training_data_training_sufficiency_unit_tests_plan_ready",
        "status=fallback_risk_training_data_training_sufficiency_unit_tests_plan_current_head_30b0dc7_revalidated",
        "latest_training_sufficiency_unit_tests_plan_complete=True",
        "latest_training_sufficiency_unit_tests_authorized=True",
        "latest_fallback_risk_training_authorized_now=False",
        "latest_camp_retraining_authorized_now=False",
        "latest_fallback_dataset_training_sufficiency_claim=False",
        "current_head_training_sufficiency_unit_tests_plan_complete=True",
        "current_head_training_sufficiency_unit_tests_authorized=True",
        "current_head_fallback_risk_training_authorized_now=False",
        "current_head_camp_retraining_authorized_now=False",
        "current_head_fallback_dataset_training_sufficiency_claim=False",
        "local_target_pytest=25 passed",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_unit_tests_only",
        "may only add synthetic/static unit tests",
        "must not implement training execution",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
    ]:
        assert needle in combined
