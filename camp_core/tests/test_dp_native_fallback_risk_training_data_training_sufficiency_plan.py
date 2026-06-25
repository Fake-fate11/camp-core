from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_plan.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_training_sufficiency_plan_records_validated_dataset_but_no_sufficiency_claim() -> None:
    text = _plan()

    for needle in [
        "validated_fallback_records=15",
        "validated_fallback_dataset_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "validator_output_json_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "fixed_artifact_training_sufficiency_claim=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "fallback_risk_training_authorized_now=False",
        "current_validated_fallback_records=15",
        "current_validated_fallback_dataset_sha256=0978687b1f7582f6644eb9598bdc5a9e03494ad227d1627bd603d54e15efb8e2",
        "current_validator_output_json_sha256=276ed840e674733861123bde0c1fa45474fbcba6d23d7faa83e53abbacd7b078",
        "current_strict_formal_seed_path_matches=0",
        "current_fixed_artifact_training_sufficiency_claim=False",
        "current_fallback_dataset_training_sufficiency_claim=False",
        "current_fallback_risk_training_authorized_now=False",
        "latest_validated_fallback_records=15",
        "latest_validated_fallback_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "latest_validator_output_json_sha256=039b3e41f866434e187a9f679cbc964d6fe35d5406896e53ec38d8f70db40c52",
        "latest_validator_output_md_sha256=e57c15b6772e0202fe76fec20d220e435c1010aab7bc410fb45230277fc9ab6a",
        "latest_strict_formal_seed_path_matches=0",
        "latest_fixed_artifact_training_sufficiency_claim=False",
        "latest_fallback_dataset_training_sufficiency_claim=False",
        "latest_fallback_risk_training_authorized_now=False",
        "camp_head_at_latest_revalidation=e5f306255adf458a7185d6f3be23df20d3a41bb0",
        "autodl_DP_HEAD_at_latest_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_head_validated_fallback_records=15",
        "current_head_validated_fallback_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "current_head_validator_output_json_sha256=039b3e41f866434e187a9f679cbc964d6fe35d5406896e53ec38d8f70db40c52",
        "current_head_validator_output_md_sha256=e57c15b6772e0202fe76fec20d220e435c1010aab7bc410fb45230277fc9ab6a",
        "current_head_strict_formal_seed_path_matches=0",
        "current_head_fixed_artifact_training_sufficiency_claim=False",
        "current_head_fallback_dataset_training_sufficiency_claim=False",
        "current_head_fallback_risk_training_authorized_now=False",
        "camp_head_at_current_head_revalidation=2097b588ace2d3ef197b5311e30e4fcbe379fcb7",
        "autodl_DP_HEAD_at_current_head_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    ]:
        assert needle in text


def test_training_sufficiency_plan_isolates_fallback_master() -> None:
    text = _plan()

    for needle in [
        "fallback_master_isolated_from_feasible_master_required=True",
        "feasible_branch_records_allowed_in_fallback_master=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "all_infeasible_records_relabelled_feasible=False",
        "hard_feasibility_relaxation_authorized=False",
        "feasible_ranking_master_change_authorized=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
        "current_fallback_master_isolated_from_feasible_master_required=True",
        "current_feasible_branch_records_allowed_in_fallback_master=False",
        "current_all_infeasible_records_added_to_feasible_training=False",
        "current_all_infeasible_records_relabelled_feasible=False",
        "current_hard_feasibility_relaxation_authorized=False",
        "current_feasible_ranking_master_change_authorized=False",
        "current_production_selector_change_authorized=False",
        "current_online_selector_change_authorized=False",
        "latest_fallback_master_isolated_from_feasible_master_required=True",
        "latest_feasible_branch_records_allowed_in_fallback_master=False",
        "latest_all_infeasible_records_added_to_feasible_training=False",
        "latest_all_infeasible_records_relabelled_feasible=False",
        "latest_hard_feasibility_relaxation_authorized=False",
        "latest_feasible_ranking_master_change_authorized=False",
        "latest_production_selector_change_authorized=False",
        "latest_online_selector_change_authorized=False",
        "current_head_fallback_master_isolated_from_feasible_master_required=True",
        "current_head_feasible_branch_records_allowed_in_fallback_master=False",
        "current_head_all_infeasible_records_added_to_feasible_training=False",
        "current_head_all_infeasible_records_relabelled_feasible=False",
        "current_head_hard_feasibility_relaxation_authorized=False",
        "current_head_feasible_ranking_master_change_authorized=False",
        "current_head_production_selector_change_authorized=False",
        "current_head_online_selector_change_authorized=False",
    ]:
        assert needle in text


def test_training_sufficiency_plan_preserves_convex_fixed_candidate_boundary() -> None:
    text = _plan()

    for needle in [
        "score_k(w)=a_k^T w",
        "a_k_fixed_before_weight_optimization=True",
        "a_k_nonnegative_benders_compatible_atoms_only=True",
        "fallback_label_is_not_a_deployed_atom=True",
        "new_atom_authorized_now=False",
        "q_i(w)=max(0,max_k m_ik+(a_i,o_i-a_i,k)^T w)",
        "margin_ik_nonnegative=True",
        "simplex_master_convex_if_later_authorized=True",
        "cvar_master_convex_if_later_authorized=True",
        "l2_regularized_master_convex_if_later_authorized=True",
        "current_score_k(w)=a_k^T w",
        "current_a_k_fixed_before_weight_optimization=True",
        "current_a_k_nonnegative_benders_compatible_atoms_only=True",
        "current_fallback_label_is_not_a_deployed_atom=True",
        "current_simplex_master_convex_if_later_authorized=True",
        "current_cvar_master_convex_if_later_authorized=True",
        "current_l2_regularized_master_convex_if_later_authorized=True",
        "latest_score_k(w)=a_k^T w",
        "latest_a_k_fixed_before_weight_optimization=True",
        "latest_a_k_nonnegative_benders_compatible_atoms_only=True",
        "latest_fallback_label_is_not_a_deployed_atom=True",
        "latest_simplex_master_convex_if_later_authorized=True",
        "latest_cvar_master_convex_if_later_authorized=True",
        "latest_l2_regularized_master_convex_if_later_authorized=True",
        "current_head_score_k(w)=a_k^T w",
        "current_head_a_k_fixed_before_weight_optimization=True",
        "current_head_a_k_nonnegative_benders_compatible_atoms_only=True",
        "current_head_fallback_label_is_not_a_deployed_atom=True",
        "current_head_simplex_master_convex_if_later_authorized=True",
        "current_head_cvar_master_convex_if_later_authorized=True",
        "current_head_l2_regularized_master_convex_if_later_authorized=True",
    ]:
        assert needle in text


def test_training_sufficiency_plan_requires_split_scale_and_formal_seed_exclusion() -> None:
    text = _plan()

    for needle in [
        "training_validation_split_predeclaration_required=True",
        "validation_groups_disjoint_from_training_groups_required=True",
        "formal_seeds_11_12_13_excluded_required=True",
        "formal_eval_data_excluded_from_scale_fit_required=True",
        "scale_fit_training_groups_only_required=True",
        "strict_positive_atom_scales_required=True",
        "current_gate_predeclares_split=False",
        "current_gate_fits_scales=False",
        "current_gate_trains_weights=False",
        "current_training_validation_split_predeclaration_required=True",
        "current_validation_groups_disjoint_from_training_groups_required=True",
        "current_formal_seeds_11_12_13_excluded_required=True",
        "current_formal_eval_data_excluded_from_scale_fit_required=True",
        "current_scale_fit_training_groups_only_required=True",
        "current_strict_positive_atom_scales_required=True",
        "latest_training_validation_split_predeclaration_required=True",
        "latest_validation_groups_disjoint_from_training_groups_required=True",
        "latest_formal_seeds_11_12_13_excluded_required=True",
        "latest_formal_eval_data_excluded_from_scale_fit_required=True",
        "latest_scale_fit_training_groups_only_required=True",
        "latest_strict_positive_atom_scales_required=True",
        "latest_gate_predeclares_split=False",
        "latest_gate_fits_scales=False",
        "latest_gate_trains_weights=False",
        "latest_gate_claims_deployable_checkpoint=False",
        "current_head_training_validation_split_predeclaration_required=True",
        "current_head_validation_groups_disjoint_from_training_groups_required=True",
        "current_head_formal_seeds_11_12_13_excluded_required=True",
        "current_head_formal_eval_data_excluded_from_scale_fit_required=True",
        "current_head_scale_fit_training_groups_only_required=True",
        "current_head_strict_positive_atom_scales_required=True",
        "current_head_gate_predeclares_split=False",
        "current_head_gate_fits_scales=False",
        "current_head_gate_trains_weights=False",
        "current_head_gate_claims_deployable_checkpoint=False",
    ]:
        assert needle in text


def test_training_sufficiency_plan_lists_missing_retraining_prerequisites() -> None:
    text = _plan()

    for needle in [
        "missing_training_split_manifest=True",
        "missing_train_only_scale_manifest=True",
        "missing_fallback_only_master_config=True",
        "missing_training_command_authorization=True",
        "missing_checkpoint_nonpromotion_plan=True",
        "missing_development_holdout_acceptance_gate=True",
        "camp_retraining_authorized_now=False",
        "current_missing_training_split_manifest=True",
        "current_missing_train_only_scale_manifest=True",
        "current_missing_fallback_only_master_config=True",
        "current_missing_training_command_authorization=True",
        "current_missing_checkpoint_nonpromotion_plan=True",
        "current_missing_development_holdout_acceptance_gate=True",
        "current_camp_retraining_authorized_now=False",
        "latest_missing_training_split_manifest=True",
        "latest_missing_train_only_scale_manifest=True",
        "latest_missing_fallback_only_master_config=True",
        "latest_missing_training_command_authorization=True",
        "latest_missing_checkpoint_nonpromotion_plan=True",
        "latest_missing_development_holdout_acceptance_gate=True",
        "latest_camp_retraining_authorized_now=False",
        "current_head_missing_training_split_manifest=True",
        "current_head_missing_train_only_scale_manifest=True",
        "current_head_missing_fallback_only_master_config=True",
        "current_head_missing_training_command_authorization=True",
        "current_head_missing_checkpoint_nonpromotion_plan=True",
        "current_head_missing_development_holdout_acceptance_gate=True",
        "current_head_camp_retraining_authorized_now=False",
    ]:
        assert needle in text


def test_training_sufficiency_plan_forbids_execution_and_sets_static_review_next() -> None:
    text = _plan()
    iteration_audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    combined = text + iteration_audit

    for needle in [
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
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
        "user_broad_execution_permission_recorded=True",
        "this_plan_gate_authorizes_training_replay_dp_or_claims=False",
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
        "current_head_replay_execution_authorized=False",
        "current_head_candidate_generation_authorized=False",
        "current_head_camp_training_authorized=False",
        "current_head_camp_retraining_authorized=False",
        "current_head_formal_seeds_11_12_13_authorized=False",
        "current_head_dp_modification_authorized=False",
        "current_head_selector_promotion_authorized=False",
        "current_head_atom_promotion_authorized=False",
        "current_head_safety_benefit_claim_authorized=False",
        "current_head_camp_over_dp_top1_claim_authorized=False",
        "status=fallback_risk_training_data_training_sufficiency_plan_ready",
        "status=fallback_risk_training_data_training_sufficiency_plan_latest_head_revalidated",
        "status=fallback_risk_training_data_training_sufficiency_plan_current_head_2097b58_revalidated",
        "status=fallback_risk_training_data_training_sufficiency_plan_autodl_verification_passed_current_head",
        "github_pushed_commit=9fb115f2c326312cbe603f8031b4d53b826d3f57",
        "autodl_CAMP_HEAD_after_sync=9fb115f2c326312cbe603f8031b4d53b826d3f57",
        "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_target_pytest_result=13 passed",
        "autodl_py_compile_exit=0",
        "autodl_git_diff_check_exit=0",
        "training_sufficiency_plan_complete=True",
        "local_target_pytest=13 passed",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_static_contract_review_only",
        "may only statically review",
        "must not train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
        "promote a selector or atom",
    ]:
        assert needle in combined
