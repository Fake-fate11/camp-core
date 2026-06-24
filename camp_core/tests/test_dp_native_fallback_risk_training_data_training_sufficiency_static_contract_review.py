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


def _review() -> str:
    return REVIEW_DOC.read_text(encoding="utf-8")


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
    ]:
        assert needle in text


def test_static_review_next_gate_is_unit_tests_plan_only() -> None:
    text = _review()

    for needle in [
        "status=fallback_risk_training_data_training_sufficiency_static_contract_review_passed",
        "static_contract_review_complete=True",
        "blocking_contract_findings=0",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_unit_tests_plan_only",
        "may only plan static and synthetic unit tests",
        "must not train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
        "promote",
    ]:
        assert needle in text
