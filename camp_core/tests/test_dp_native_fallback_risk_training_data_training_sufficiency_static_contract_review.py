from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_static_contract_review.md"
)
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_plan.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _review() -> str:
    return REVIEW_DOC.read_text(encoding="utf-8")


def test_current_head_f2658fb_static_review_revalidation_is_pinned() -> None:
    text = _review()
    plan = PLAN_DOC.read_text(encoding="utf-8")
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    combined = text + plan + audit
    status = "status=fallback_risk_training_data_training_sufficiency_static_contract_review_current_head_f2658fb_revalidated"

    assert status in audit
    assert (
        "status=fallback_risk_training_data_training_sufficiency_plan_current_head_2d9a19d_revalidated"
        in plan
    )

    for needle in [
        status,
        "review_validation_base_head=f2658fb41156c8714d3437709cbfb0ecc563baf8",
        "camp_origin_main_at_static_review=f2658fb41156c8714d3437709cbfb0ecc563baf8",
        "github_refs_heads_main_at_static_review=f2658fb41156c8714d3437709cbfb0ecc563baf8",
        "autodl_CAMP_HEAD_at_static_review=f2658fb41156c8714d3437709cbfb0ecc563baf8",
        "autodl_CAMP_origin_main_at_static_review=f2658fb41156c8714d3437709cbfb0ecc563baf8",
        "autodl_DP_HEAD_at_static_review=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "source_plan_status=fallback_risk_training_data_training_sufficiency_plan_current_head_2d9a19d_revalidated",
        "source_validator_acceptance_status=fallback_risk_training_data_validator_extension_fixed_artifact_acceptance_current_head_92ce703_passed",
        "head_f2658fb_validated_fallback_records=15",
        "head_f2658fb_validated_fallback_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_f2658fb_validator_output_json_sha256=d719e3b01d17be91ab68ba42cc9349400cc73fa9624fb7fdff0e539fcb6344e2",
        "head_f2658fb_validator_output_md_sha256=e57c15b6772e0202fe76fec20d220e435c1010aab7bc410fb45230277fc9ab6a",
        "head_f2658fb_strict_formal_seed_path_matches=0",
        "head_f2658fb_evidence_boundary_passed=True",
        "head_f2658fb_fixed_artifact_training_sufficiency_claim=False",
        "head_f2658fb_fallback_dataset_training_sufficiency_claim=False",
        "head_f2658fb_fallback_risk_training_authorized_now=False",
        "head_f2658fb_master_isolation_passed=True",
        "head_f2658fb_fallback_master_isolated_from_feasible_master_required=True",
        "head_f2658fb_feasible_branch_records_allowed_in_fallback_master=False",
        "head_f2658fb_all_infeasible_records_added_to_feasible_training=False",
        "head_f2658fb_hard_feasibility_relaxation_authorized=False",
        "head_f2658fb_convex_fixed_candidate_boundary_passed=True",
        "head_f2658fb_score_k(w)=a_k^T w",
        "head_f2658fb_candidate_features_fixed_at_current_tick=True",
        "head_f2658fb_no_trajectory_generation_modification_snap_blend_guidance_or_postprocess=True",
        "head_f2658fb_a_k_nonnegative_benders_compatible_atoms_only=True",
        "head_f2658fb_simplex_cvar_l2_master_convex_if_later_authorized=True",
        "head_f2658fb_split_scale_boundary_passed=True",
        "head_f2658fb_split_boundary_predeclared=True",
        "head_f2658fb_scale_fitting_boundary_predeclared=True",
        "head_f2658fb_scale_fit_training_groups_only_required=True",
        "head_f2658fb_formal_seed_exclusion_predeclared=True",
        "head_f2658fb_formal_seeds_11_12_13_excluded_required=True",
        "head_f2658fb_nonpromotion_checks_predeclared=True",
        "head_f2658fb_current_downstream_artifacts_not_reused_without_revalidation=True",
        "head_f2658fb_blocking_contract_findings=0",
        "head_f2658fb_local_py_compile_exit=0",
        "head_f2658fb_local_target_pytest=15 passed",
        "head_f2658fb_local_git_diff_check_exit=0",
        "head_f2658fb_autodl_temp_worktree=/root/autodl-tmp/camp_core_static_review_f2658fb_verify_20260626T164335Z",
        "head_f2658fb_autodl_py_compile_exit=0",
        "head_f2658fb_autodl_target_pytest=15 passed",
        "head_f2658fb_autodl_git_diff_check_exit=0",
        "this_static_review_gate_authorizes_training_replay_dp_or_claims=False",
        "fallback_risk_training_authorized_now=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "training_not_executed=True",
        "candidate_generation_not_executed=True",
        "dp_not_modified=True",
        "selector_or_atom_not_promoted=True",
        "formal_seeds_11_12_13_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "static_contract_review_complete=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_unit_tests_plan_only",
    ]:
        assert needle in combined


def test_static_review_records_evidence_boundary_without_training_claim() -> None:
    text = _review()

    for needle in [
        "evidence_boundary_passed=True",
        "validated_fallback_records=15",
        "fixed_artifact_training_sufficiency_claim=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "deployable_checkpoint_claim_authorized=False",
        "current_evidence_boundary_passed=True",
        "current_validated_fallback_records=15",
        "current_validated_fallback_dataset_sha256=0978687b1f7582f6644eb9598bdc5a9e03494ad227d1627bd603d54e15efb8e2",
        "current_validator_output_json_sha256=276ed840e674733861123bde0c1fa45474fbcba6d23d7faa83e53abbacd7b078",
        "current_strict_formal_seed_path_matches=0",
        "current_fixed_artifact_training_sufficiency_claim=False",
        "current_fallback_dataset_training_sufficiency_claim=False",
        "current_fallback_risk_training_authorized_now=False",
        "current_camp_retraining_authorized_now=False",
        "current_deployable_checkpoint_claim_authorized=False",
        "latest_evidence_boundary_passed=True",
        "latest_validated_fallback_records=15",
        "latest_validated_fallback_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "latest_validator_output_json_sha256=039b3e41f866434e187a9f679cbc964d6fe35d5406896e53ec38d8f70db40c52",
        "latest_validator_output_md_sha256=e57c15b6772e0202fe76fec20d220e435c1010aab7bc410fb45230277fc9ab6a",
        "latest_strict_formal_seed_path_matches=0",
        "latest_fixed_artifact_training_sufficiency_claim=False",
        "latest_fallback_dataset_training_sufficiency_claim=False",
        "latest_fallback_risk_training_authorized_now=False",
        "latest_camp_retraining_authorized_now=False",
        "latest_deployable_checkpoint_claim_authorized=False",
        "camp_head_at_latest_revalidation=181591a21972b7b666f0593150665d40fb1edb7a",
        "autodl_DP_HEAD_at_latest_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "current_head_evidence_boundary_passed=True",
        "current_head_validated_fallback_records=15",
        "current_head_validated_fallback_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "current_head_validator_output_json_sha256=039b3e41f866434e187a9f679cbc964d6fe35d5406896e53ec38d8f70db40c52",
        "current_head_validator_output_md_sha256=e57c15b6772e0202fe76fec20d220e435c1010aab7bc410fb45230277fc9ab6a",
        "current_head_strict_formal_seed_path_matches=0",
        "current_head_fixed_artifact_training_sufficiency_claim=False",
        "current_head_fallback_dataset_training_sufficiency_claim=False",
        "current_head_fallback_risk_training_authorized_now=False",
        "current_head_camp_retraining_authorized_now=False",
        "current_head_deployable_checkpoint_claim_authorized=False",
        "camp_head_at_current_head_revalidation=d331cb5851defa45ac3f2a80cebccfa6ae765e23",
        "autodl_DP_HEAD_at_current_head_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "head_ac14588_evidence_boundary_passed=True",
        "head_ac14588_validated_fallback_records=15",
        "head_ac14588_validated_fallback_dataset_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "head_ac14588_validator_output_json_sha256=4baaf581141c8fbfddede13bd04b02788276421f041d6eca9bd86c15e1d221fc",
        "head_ac14588_validator_output_md_sha256=e57c15b6772e0202fe76fec20d220e435c1010aab7bc410fb45230277fc9ab6a",
        "head_ac14588_strict_formal_seed_path_matches=0",
        "head_ac14588_fixed_artifact_training_sufficiency_claim=False",
        "head_ac14588_fallback_dataset_training_sufficiency_claim=False",
        "head_ac14588_fallback_risk_training_authorized_now=False",
        "head_ac14588_camp_retraining_authorized_now=False",
        "head_ac14588_deployable_checkpoint_claim_authorized=False",
        "camp_head_at_head_ac14588_revalidation=ac145882ec195ba64e83c2405025f2bce39c605c",
        "autodl_DP_HEAD_at_head_ac14588_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "head_af2a81c_evidence_boundary_passed=True",
        "head_af2a81c_validated_fallback_records=15",
        "head_af2a81c_validated_fallback_dataset_sha256=682d432f742d4ab68a262cf70955981bc1562cf1dbcf2ec094984a12fcd11498",
        "head_af2a81c_validator_output_json_sha256=bfe5d031be232c13188e19ae19692a560bb424090fc446253edf015c50c821c9",
        "head_af2a81c_validator_output_md_sha256=e57c15b6772e0202fe76fec20d220e435c1010aab7bc410fb45230277fc9ab6a",
        "head_af2a81c_strict_formal_seed_path_matches=0",
        "head_af2a81c_fixed_artifact_training_sufficiency_claim=False",
        "head_af2a81c_fallback_dataset_training_sufficiency_claim=False",
        "head_af2a81c_fallback_risk_training_authorized_now=False",
        "head_af2a81c_camp_retraining_authorized_now=False",
        "head_af2a81c_deployable_checkpoint_claim_authorized=False",
        "camp_head_at_head_af2a81c_revalidation=af2a81cf1b008ed9a6590486c70d0ffaaf371497",
        "autodl_DP_HEAD_at_head_af2a81c_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    ]:
        assert needle in text


def test_static_review_preserves_master_isolation() -> None:
    text = _review()

    for needle in [
        "master_isolation_passed=True",
        "fallback_master_isolated_from_feasible_master_required=True",
        "feasible_branch_records_allowed_in_fallback_master=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "all_infeasible_records_relabelled_feasible=False",
        "hard_feasibility_relaxation_authorized=False",
        "feasible_ranking_master_change_authorized=False",
        "current_master_isolation_passed=True",
        "current_fallback_master_isolated_from_feasible_master_required=True",
        "current_feasible_branch_records_allowed_in_fallback_master=False",
        "current_all_infeasible_records_added_to_feasible_training=False",
        "current_all_infeasible_records_relabelled_feasible=False",
        "current_hard_feasibility_relaxation_authorized=False",
        "current_feasible_ranking_master_change_authorized=False",
        "latest_master_isolation_passed=True",
        "latest_fallback_master_isolated_from_feasible_master_required=True",
        "latest_feasible_branch_records_allowed_in_fallback_master=False",
        "latest_all_infeasible_records_added_to_feasible_training=False",
        "latest_all_infeasible_records_relabelled_feasible=False",
        "latest_hard_feasibility_relaxation_authorized=False",
        "latest_feasible_ranking_master_change_authorized=False",
        "current_head_master_isolation_passed=True",
        "current_head_fallback_master_isolated_from_feasible_master_required=True",
        "current_head_feasible_branch_records_allowed_in_fallback_master=False",
        "current_head_all_infeasible_records_added_to_feasible_training=False",
        "current_head_all_infeasible_records_relabelled_feasible=False",
        "current_head_hard_feasibility_relaxation_authorized=False",
        "current_head_feasible_ranking_master_change_authorized=False",
        "head_ac14588_master_isolation_passed=True",
        "head_ac14588_fallback_master_isolated_from_feasible_master_required=True",
        "head_ac14588_feasible_branch_records_allowed_in_fallback_master=False",
        "head_ac14588_all_infeasible_records_added_to_feasible_training=False",
        "head_ac14588_all_infeasible_records_relabelled_feasible=False",
        "head_ac14588_hard_feasibility_relaxation_authorized=False",
        "head_ac14588_feasible_ranking_master_change_authorized=False",
        "head_af2a81c_master_isolation_passed=True",
        "head_af2a81c_fallback_master_isolated_from_feasible_master_required=True",
        "head_af2a81c_feasible_branch_records_allowed_in_fallback_master=False",
        "head_af2a81c_all_infeasible_records_added_to_feasible_training=False",
        "head_af2a81c_all_infeasible_records_relabelled_feasible=False",
        "head_af2a81c_hard_feasibility_relaxation_authorized=False",
        "head_af2a81c_feasible_ranking_master_change_authorized=False",
    ]:
        assert needle in text


def test_static_review_preserves_convex_fixed_candidate_boundary() -> None:
    text = _review()

    for needle in [
        "convex_fixed_candidate_boundary_passed=True",
        "score_k(w)=a_k^T w",
        "a_k_fixed_before_weight_optimization=True",
        "a_k_nonnegative_benders_compatible_atoms_only=True",
        "fallback_label_is_not_a_deployed_atom=True",
        "new_atom_authorized_now=False",
        "q_i(w)=max(0,max_k m_ik+(a_i,o_i-a_i,k)^T w)",
        "simplex_master_convex_if_later_authorized=True",
        "cvar_master_convex_if_later_authorized=True",
        "l2_regularized_master_convex_if_later_authorized=True",
        "current_convex_fixed_candidate_boundary_passed=True",
        "current_score_k(w)=a_k^T w",
        "current_a_k_fixed_before_weight_optimization=True",
        "current_a_k_nonnegative_benders_compatible_atoms_only=True",
        "current_fallback_label_is_not_a_deployed_atom=True",
        "latest_convex_fixed_candidate_boundary_passed=True",
        "latest_score_k(w)=a_k^T w",
        "latest_a_k_fixed_before_weight_optimization=True",
        "latest_a_k_nonnegative_benders_compatible_atoms_only=True",
        "latest_fallback_label_is_not_a_deployed_atom=True",
        "current_head_convex_fixed_candidate_boundary_passed=True",
        "current_head_score_k(w)=a_k^T w",
        "current_head_a_k_fixed_before_weight_optimization=True",
        "current_head_a_k_nonnegative_benders_compatible_atoms_only=True",
        "current_head_fallback_label_is_not_a_deployed_atom=True",
        "head_ac14588_convex_fixed_candidate_boundary_passed=True",
        "head_ac14588_score_k(w)=a_k^T w",
        "head_ac14588_a_k_fixed_before_weight_optimization=True",
        "head_ac14588_a_k_nonnegative_benders_compatible_atoms_only=True",
        "head_ac14588_fallback_label_is_not_a_deployed_atom=True",
        "head_af2a81c_convex_fixed_candidate_boundary_passed=True",
        "head_af2a81c_score_k(w)=a_k^T w",
        "head_af2a81c_a_k_fixed_before_weight_optimization=True",
        "head_af2a81c_a_k_nonnegative_benders_compatible_atoms_only=True",
        "head_af2a81c_fallback_label_is_not_a_deployed_atom=True",
    ]:
        assert needle in text


def test_static_review_requires_split_scale_and_lists_missing_retraining_inputs() -> None:
    text = _review()

    for needle in [
        "split_scale_boundary_passed=True",
        "training_validation_split_predeclaration_required=True",
        "validation_groups_disjoint_from_training_groups_required=True",
        "formal_seeds_11_12_13_excluded_required=True",
        "formal_eval_data_excluded_from_scale_fit_required=True",
        "scale_fit_training_groups_only_required=True",
        "current_gate_trains_weights=False",
        "retraining_prerequisite_boundary_passed=True",
        "missing_training_split_manifest=True",
        "missing_train_only_scale_manifest=True",
        "missing_training_command_authorization=True",
        "current_split_scale_boundary_passed=True",
        "current_training_validation_split_predeclaration_required=True",
        "current_validation_groups_disjoint_from_training_groups_required=True",
        "current_formal_seeds_11_12_13_excluded_required=True",
        "current_formal_eval_data_excluded_from_scale_fit_required=True",
        "current_scale_fit_training_groups_only_required=True",
        "current_retraining_prerequisite_boundary_passed=True",
        "current_missing_training_split_manifest=True",
        "current_missing_train_only_scale_manifest=True",
        "current_missing_training_command_authorization=True",
        "current_missing_development_holdout_acceptance_gate=True",
        "current_blocking_contract_findings=0",
        "latest_split_scale_boundary_passed=True",
        "latest_training_validation_split_predeclaration_required=True",
        "latest_validation_groups_disjoint_from_training_groups_required=True",
        "latest_formal_seeds_11_12_13_excluded_required=True",
        "latest_formal_eval_data_excluded_from_scale_fit_required=True",
        "latest_scale_fit_training_groups_only_required=True",
        "latest_retraining_prerequisite_boundary_passed=True",
        "latest_missing_training_split_manifest=True",
        "latest_missing_train_only_scale_manifest=True",
        "latest_missing_fallback_only_master_config=True",
        "latest_missing_training_command_authorization=True",
        "latest_missing_checkpoint_nonpromotion_plan=True",
        "latest_missing_development_holdout_acceptance_gate=True",
        "latest_blocking_contract_findings=0",
        "current_head_split_scale_boundary_passed=True",
        "current_head_training_validation_split_predeclaration_required=True",
        "current_head_validation_groups_disjoint_from_training_groups_required=True",
        "current_head_formal_seeds_11_12_13_excluded_required=True",
        "current_head_formal_eval_data_excluded_from_scale_fit_required=True",
        "current_head_scale_fit_training_groups_only_required=True",
        "current_head_retraining_prerequisite_boundary_passed=True",
        "current_head_missing_training_split_manifest=True",
        "current_head_missing_train_only_scale_manifest=True",
        "current_head_missing_fallback_only_master_config=True",
        "current_head_missing_training_command_authorization=True",
        "current_head_missing_checkpoint_nonpromotion_plan=True",
        "current_head_missing_development_holdout_acceptance_gate=True",
        "current_head_blocking_contract_findings=0",
        "head_ac14588_split_scale_boundary_passed=True",
        "head_ac14588_training_validation_split_predeclaration_required=True",
        "head_ac14588_validation_groups_disjoint_from_training_groups_required=True",
        "head_ac14588_formal_seeds_11_12_13_excluded_required=True",
        "head_ac14588_formal_eval_data_excluded_from_scale_fit_required=True",
        "head_ac14588_scale_fit_training_groups_only_required=True",
        "head_ac14588_retraining_prerequisite_boundary_passed=True",
        "head_ac14588_missing_training_split_manifest=True",
        "head_ac14588_missing_train_only_scale_manifest=True",
        "head_ac14588_missing_fallback_only_master_config=True",
        "head_ac14588_missing_training_command_authorization=True",
        "head_ac14588_missing_checkpoint_nonpromotion_plan=True",
        "head_ac14588_missing_development_holdout_acceptance_gate=True",
        "head_ac14588_blocking_contract_findings=0",
        "head_af2a81c_split_scale_boundary_passed=True",
        "head_af2a81c_training_validation_split_predeclaration_required=True",
        "head_af2a81c_validation_groups_disjoint_from_training_groups_required=True",
        "head_af2a81c_formal_seeds_11_12_13_excluded_required=True",
        "head_af2a81c_formal_eval_data_excluded_from_scale_fit_required=True",
        "head_af2a81c_scale_fit_training_groups_only_required=True",
        "head_af2a81c_retraining_prerequisite_boundary_passed=True",
        "head_af2a81c_missing_training_split_manifest=True",
        "head_af2a81c_missing_train_only_scale_manifest=True",
        "head_af2a81c_missing_fallback_only_master_config=True",
        "head_af2a81c_missing_training_command_authorization=True",
        "head_af2a81c_missing_checkpoint_nonpromotion_plan=True",
        "head_af2a81c_missing_development_holdout_acceptance_gate=True",
        "head_af2a81c_blocking_contract_findings=0",
    ]:
        assert needle in text


def test_static_review_matches_plan_and_forbids_execution() -> None:
    text = _review()
    plan = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_training_data_training_sufficiency_plan_ready",
        "camp_retraining_authorized_now=False",
        "fallback_dataset_training_sufficiency_claim=False",
    ]:
        assert needle in plan

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
        "this_static_review_gate_authorizes_training_replay_dp_or_claims=False",
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
        "head_ac14588_replay_execution_authorized=False",
        "head_ac14588_candidate_generation_authorized=False",
        "head_ac14588_camp_training_authorized=False",
        "head_ac14588_camp_retraining_authorized=False",
        "head_ac14588_formal_seeds_11_12_13_authorized=False",
        "head_ac14588_dp_modification_authorized=False",
        "head_ac14588_selector_promotion_authorized=False",
        "head_ac14588_atom_promotion_authorized=False",
        "head_ac14588_safety_benefit_claim_authorized=False",
        "head_ac14588_camp_over_dp_top1_claim_authorized=False",
        "head_af2a81c_replay_execution_authorized=False",
        "head_af2a81c_candidate_generation_authorized=False",
        "head_af2a81c_camp_training_authorized=False",
        "head_af2a81c_camp_retraining_authorized=False",
        "head_af2a81c_formal_seeds_11_12_13_authorized=False",
        "head_af2a81c_dp_modification_authorized=False",
        "head_af2a81c_selector_promotion_authorized=False",
        "head_af2a81c_atom_promotion_authorized=False",
        "head_af2a81c_safety_benefit_claim_authorized=False",
        "head_af2a81c_camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text


def test_static_review_next_gate_is_unit_tests_plan_only() -> None:
    text = _review()
    iteration_tail = ITERATION_AUDIT.read_text(encoding="utf-8")[-12000:]
    combined = text + iteration_tail

    for needle in [
        "status=fallback_risk_training_data_training_sufficiency_static_contract_review_passed",
        "status=fallback_risk_training_data_training_sufficiency_static_contract_review_latest_head_revalidated",
        "status=fallback_risk_training_data_training_sufficiency_static_contract_review_current_head_d331cb5_revalidated",
        "status=fallback_risk_training_data_training_sufficiency_static_contract_review_current_head_ac14588_revalidated",
        "status=fallback_risk_training_data_training_sufficiency_static_contract_review_current_head_af2a81c_revalidated",
        "status=fallback_risk_training_data_training_sufficiency_static_contract_review_autodl_verification_passed_current_head",
        "github_pushed_commit=bc3fafeb4afc597df7528b1d544fac72e2cfdf44",
        "autodl_CAMP_HEAD_after_sync=bc3fafeb4afc597df7528b1d544fac72e2cfdf44",
        "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_target_pytest_result=19 passed",
        "autodl_py_compile_exit=0",
        "autodl_git_diff_check_exit=0",
        "static_contract_review_complete=True",
        "blocking_contract_findings=0",
        "head_ac14588_local_target_pytest=6 passed",
        "head_af2a81c_local_py_compile_exit=0",
        "head_af2a81c_local_target_pytest=29 passed",
        "head_af2a81c_local_git_diff_check_exit=0",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_unit_tests_plan_only",
        "may only plan static and synthetic unit tests",
        "must not train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
        "promote",
    ]:
        assert needle in combined


def test_static_review_current_head_476a8e0_revalidation_is_pinned() -> None:
    text = _review()
    iteration_audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    combined = text + iteration_audit

    for needle in [
        "status=fallback_risk_training_data_training_sufficiency_static_contract_review_current_head_476a8e0_revalidated",
        "head_476a8e0_training_sufficiency_plan=docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_plan.md",
        "head_476a8e0_validator_acceptance=docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_fixed_artifact_acceptance_audit.md",
        "head_476a8e0_training_sufficiency_plan_status=fallback_risk_training_data_training_sufficiency_plan_current_head_94f0e6d_revalidated",
        "head_476a8e0_validated_fallback_records=15",
        "head_476a8e0_validated_fallback_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_476a8e0_validator_output_json_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "head_476a8e0_validator_output_md_sha256=e57c15b6772e0202fe76fec20d220e435c1010aab7bc410fb45230277fc9ab6a",
        "head_476a8e0_strict_formal_seed_path_matches=0",
        "camp_head_at_head_476a8e0_revalidation=476a8e0e2773d7512d96b6f8dc536dd110305da0",
        "camp_origin_main_at_head_476a8e0_revalidation=476a8e0e2773d7512d96b6f8dc536dd110305da0",
        "github_refs_heads_main_at_head_476a8e0_revalidation=476a8e0e2773d7512d96b6f8dc536dd110305da0",
        "autodl_CAMP_HEAD_at_head_476a8e0_revalidation=476a8e0e2773d7512d96b6f8dc536dd110305da0",
        "autodl_CAMP_origin_main_at_head_476a8e0_revalidation=476a8e0e2773d7512d96b6f8dc536dd110305da0",
        "autodl_DP_HEAD_at_head_476a8e0_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "head_476a8e0_evidence_boundary_passed=True",
        "head_476a8e0_fixed_artifact_training_sufficiency_claim=False",
        "head_476a8e0_fallback_dataset_training_sufficiency_claim=False",
        "head_476a8e0_fallback_risk_training_authorized_now=False",
        "head_476a8e0_camp_retraining_authorized_now=False",
        "head_476a8e0_master_isolation_passed=True",
        "head_476a8e0_fallback_master_isolated_from_feasible_master_required=True",
        "head_476a8e0_feasible_branch_records_allowed_in_fallback_master=False",
        "head_476a8e0_convex_fixed_candidate_boundary_passed=True",
        "head_476a8e0_score_k(w)=a_k^T w",
        "head_476a8e0_a_k_fixed_before_weight_optimization=True",
        "head_476a8e0_a_k_nonnegative_benders_compatible_atoms_only=True",
        "head_476a8e0_fallback_label_is_not_a_deployed_atom=True",
        "head_476a8e0_simplex_master_convex_if_later_authorized=True",
        "head_476a8e0_cvar_master_convex_if_later_authorized=True",
        "head_476a8e0_l2_regularized_master_convex_if_later_authorized=True",
        "head_476a8e0_split_scale_boundary_passed=True",
        "head_476a8e0_training_validation_split_predeclaration_required=True",
        "head_476a8e0_validation_groups_disjoint_from_training_groups_required=True",
        "head_476a8e0_formal_seeds_11_12_13_excluded_required=True",
        "head_476a8e0_scale_fit_training_groups_only_required=True",
        "head_476a8e0_retraining_prerequisite_boundary_passed=True",
        "head_476a8e0_missing_training_split_manifest=True",
        "head_476a8e0_missing_train_only_scale_manifest=True",
        "head_476a8e0_missing_fallback_only_master_config=True",
        "head_476a8e0_missing_training_command_authorization=True",
        "head_476a8e0_missing_checkpoint_nonpromotion_plan=True",
        "head_476a8e0_missing_development_holdout_acceptance_gate=True",
        "head_476a8e0_blocking_contract_findings=0",
        "head_476a8e0_replay_execution_authorized=False",
        "head_476a8e0_candidate_generation_authorized=False",
        "head_476a8e0_camp_training_authorized=False",
        "head_476a8e0_camp_retraining_authorized=False",
        "head_476a8e0_formal_seeds_11_12_13_authorized=False",
        "head_476a8e0_dp_modification_authorized=False",
        "head_476a8e0_selector_promotion_authorized=False",
        "head_476a8e0_atom_promotion_authorized=False",
        "head_476a8e0_safety_benefit_claim_authorized=False",
        "head_476a8e0_camp_over_dp_top1_claim_authorized=False",
        "head_476a8e0_local_py_compile_exit=0",
        "head_476a8e0_local_target_pytest=7 passed",
        "head_476a8e0_local_git_diff_check_exit=0",
        "head_476a8e0_autodl_py_compile_exit=0",
        "head_476a8e0_autodl_training_group_pytest=30 passed",
        "head_476a8e0_autodl_cumulative_pytest=218 passed",
        "head_476a8e0_autodl_git_diff_check_exit=0",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_unit_tests_plan_only",
    ]:
        assert needle in combined


def test_static_review_eof_records_current_head_721bac9_review() -> None:
    marker = "\n## Current-Head Static Contract Revalidation After 0c4e795 Plan Sync\n\n"
    review = _review()
    assert marker in review
    section = review.rsplit(marker, maxsplit=1)[-1].split("\n## ", maxsplit=1)[0]

    for needle in [
        "status=fallback_risk_training_data_training_sufficiency_static_contract_review_current_head_721bac9_revalidated",
        "review_validation_base_head=721bac940559daa11821f2ad81f94c788103791f",
        "github_refs_heads_main_at_static_review=721bac940559daa11821f2ad81f94c788103791f",
        "autodl_CAMP_HEAD_at_static_review=721bac940559daa11821f2ad81f94c788103791f",
        "autodl_DP_HEAD_at_static_review=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "source_plan_status=fallback_risk_training_data_training_sufficiency_plan_current_head_0c4e795_revalidated",
        "source_validator_acceptance_status=fallback_risk_training_data_validator_extension_fixed_artifact_acceptance_current_head_7f5ca75_passed",
        "head_721bac9_validated_fallback_records=15",
        "head_721bac9_validator_output_json_sha256=4f3a0be2dbf070b4d94262111e3c9b68618732efd64f54355722dbfbe61f2d40",
        "head_721bac9_strict_formal_seed_path_matches=0",
        "head_721bac9_evidence_boundary_passed=True",
        "head_721bac9_fallback_dataset_training_sufficiency_claim=False",
        "head_721bac9_fallback_risk_training_authorized_now=False",
        "head_721bac9_camp_retraining_authorized_now=False",
        "head_721bac9_master_isolation_passed=True",
        "head_721bac9_fallback_master_isolated_from_feasible_master_required=True",
        "head_721bac9_all_infeasible_records_added_to_feasible_training=False",
        "head_721bac9_convex_fixed_candidate_boundary_passed=True",
        "head_721bac9_score_k(w)=a_k^T w",
        "head_721bac9_candidate_features_fixed_at_current_tick=True",
        "head_721bac9_no_trajectory_generation_modification_snap_blend_guidance_or_postprocess=True",
        "head_721bac9_a_k_nonnegative_benders_compatible_atoms_only=True",
        "head_721bac9_simplex_cvar_l2_master_convex_if_later_authorized=True",
        "head_721bac9_split_scale_boundary_passed=True",
        "head_721bac9_training_validation_split_predeclaration_required=True",
        "head_721bac9_scale_fit_training_groups_only_required=True",
        "head_721bac9_formal_seeds_11_12_13_excluded_required=True",
        "head_721bac9_current_downstream_artifacts_not_reused_without_revalidation=True",
        "head_721bac9_retraining_prerequisite_boundary_passed=True",
        "head_721bac9_missing_training_split_manifest=True",
        "head_721bac9_missing_train_only_scale_manifest=True",
        "head_721bac9_missing_fallback_only_master_config=True",
        "head_721bac9_missing_training_command_authorization=True",
        "head_721bac9_blocking_contract_findings=0",
        "head_721bac9_local_target_pytest=10 passed",
        "head_721bac9_autodl_target_pytest=10 passed",
        "static_contract_review_complete=True",
        "training_not_executed=True",
        "candidate_generation_not_executed=True",
        "dp_not_modified=True",
        "selector_or_atom_not_promoted=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_unit_tests_plan_only",
    ]:
        assert needle in section


def test_iteration_audit_eof_records_current_head_721bac9_review() -> None:
    marker = (
        "\n## Current Tail Confirmation After 721bac9 Fallback Risk Training Data "
        "Training Sufficiency Static Contract Review\n\n"
    )
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    assert marker in audit
    section = audit.rsplit(marker, maxsplit=1)[-1].split("\n## ", maxsplit=1)[0]

    for needle in [
        "status=fallback_risk_training_data_training_sufficiency_static_contract_review_current_head_721bac9_revalidated",
        "review_validation_base_head=721bac940559daa11821f2ad81f94c788103791f",
        "source_plan_status=fallback_risk_training_data_training_sufficiency_plan_current_head_0c4e795_revalidated",
        "source_validator_acceptance_status=fallback_risk_training_data_validator_extension_fixed_artifact_acceptance_current_head_7f5ca75_passed",
        "head_721bac9_validator_output_json_sha256=4f3a0be2dbf070b4d94262111e3c9b68618732efd64f54355722dbfbe61f2d40",
        "head_721bac9_evidence_boundary_passed=True",
        "head_721bac9_master_isolation_passed=True",
        "head_721bac9_convex_fixed_candidate_boundary_passed=True",
        "head_721bac9_score_k(w)=a_k^T w",
        "head_721bac9_no_trajectory_generation_modification_snap_blend_guidance_or_postprocess=True",
        "head_721bac9_training_validation_split_predeclaration_required=True",
        "head_721bac9_formal_seeds_11_12_13_excluded_required=True",
        "head_721bac9_missing_training_split_manifest=True",
        "head_721bac9_missing_train_only_scale_manifest=True",
        "head_721bac9_missing_fallback_only_master_config=True",
        "head_721bac9_missing_training_command_authorization=True",
        "head_721bac9_local_target_pytest=10 passed",
        "head_721bac9_autodl_target_pytest=10 passed",
        "this_static_review_gate_authorizes_training_replay_dp_or_claims=False",
        "head_721bac9_replay_execution_authorized=False",
        "head_721bac9_candidate_generation_authorized=False",
        "head_721bac9_camp_training_authorized=False",
        "head_721bac9_camp_retraining_authorized=False",
        "head_721bac9_dp_modification_authorized=False",
        "head_721bac9_selector_promotion_authorized=False",
        "head_721bac9_atom_promotion_authorized=False",
        "head_721bac9_safety_benefit_claim_authorized=False",
        "head_721bac9_camp_over_dp_top1_claim_authorized=False",
        "static_contract_review_complete=True",
        "blocking_contract_findings=0",
        "training_not_executed=True",
        "dp_not_modified=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_unit_tests_plan_only",
    ]:
        assert needle in section
