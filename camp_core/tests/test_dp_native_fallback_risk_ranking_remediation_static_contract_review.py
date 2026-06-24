from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_remediation_static_contract_review.md"
)


def test_static_contract_review_passes_fixed_candidate_boundary() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "fixed_candidate_boundary_passed=True",
        "candidate_count_must_match=True",
        "selected_index_must_be_in_range=True",
        "provenance_payload_must_be_valid=True",
        "pre_post_tensor_hash_equal_required=True",
        "no_candidate_row_append_required=True",
        "no_coordinate_heading_speed_rewrite_required=True",
        "candidate_mutation_path_found=False",
        "candidate_generation_path_found=False",
        "dp_modification_path_found=False",
    ]:
        assert needle in text


def test_static_contract_review_preserves_affine_nonnegative_convex_bounds() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "score_k(w)=a_k^T w",
        "affine_score_boundary_passed=True",
        "fallback_cost_targets_used_as_labels_not_deployed_atoms=True",
        "new_atom_authorized_now=False",
        "nonnegative_cost_boundary_passed=True",
        "fallback_cost_targets_nonnegative=True",
        "alpha_values_authorized_now=False",
        "alpha_values_must_be_fixed_nonnegative_if_later_authorized=True",
        "missing_cost_fields_fail_closed=True",
        "convex_master_boundary_passed=True",
        "simplex_master_convex_if_later_authorized=True",
        "cvar_master_convex_if_later_authorized=True",
        "l2_regularized_master_convex_if_later_authorized=True",
        "joint_alpha_and_w_optimization_authorized=False",
        "rank_dependent_feature_authorized=False",
        "selected_index_dependent_feature_authorized=False",
    ]:
        assert needle in text


def test_static_contract_review_keeps_feasible_master_separate() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "feasible_master_separation_passed=True",
        "records_scope=records_without_feasible_candidate_only",
        "all_infeasible_records_relabelled_feasible=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "feasible_ranking_master_change_authorized=False",
        "hard_feasibility_relaxation_authorized=False",
        "fallback_risk_diagnostic_track_separate=True",
    ]:
        assert needle in text


def test_static_contract_review_forbids_execution_and_promotion() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

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
        "implementation_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
    ]:
        assert needle in text

    for forbidden in [
        "candidate_generation_authorized=True",
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "implementation_authorized=True",
    ]:
        assert forbidden not in text


def test_static_contract_review_next_gate_unit_tests_plan_only() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_ranking_remediation_static_contract_review_passed_default_off_tests_plan_next",
        "blocking_contract_findings=0",
        "require_default_off_flag=True",
        "require_read_only_extractor_unit_tests=True",
        "require_missing_field_fail_closed_tests=True",
        "require_no_training_or_deployment_side_effect_tests=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_unit_tests_plan_only",
        "It must not implement",
        "the extractor, train CAMP",
    ]:
        assert needle in text
