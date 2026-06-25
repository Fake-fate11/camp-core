from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_remediation_static_contract_review.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
NEXT_UNIT_TESTS_PLAN_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_ranking_default_off_unit_tests_plan_only"
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


def test_static_contract_review_current_head_revalidation() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")
    recent_review = text.split(
        "## Current-Head Revalidation After 1027a6b Design Plan Revalidation"
    )[-1]

    for needle in [
        "camp_head_at_revalidation=f4f076ab9d85a35d6d2bb3343405fddc8648f9fa",
        "camp_origin_main_at_revalidation=f4f076ab9d85a35d6d2bb3343405fddc8648f9fa",
        "github_refs_heads_main_at_revalidation=f4f076ab9d85a35d6d2bb3343405fddc8648f9fa",
        "autodl_CAMP_HEAD_at_revalidation=f4f076ab9d85a35d6d2bb3343405fddc8648f9fa",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_design_status=fallback_risk_ranking_remediation_design_plan_ready_static_contract_review",
        "prior_design_current_head_revalidated=True",
        "blocking_contract_findings=0",
        "camp_head_at_revalidation=86ec080aa632ddf994d75da8bef83ff89203bc5c",
        "camp_origin_main_at_revalidation=86ec080aa632ddf994d75da8bef83ff89203bc5c",
        "github_refs_heads_main_at_revalidation=86ec080aa632ddf994d75da8bef83ff89203bc5c",
        "autodl_CAMP_HEAD_at_revalidation=86ec080aa632ddf994d75da8bef83ff89203bc5c",
        "camp_head_at_revalidation=7e3e65700c2bf910958788ac6cc5d7bf7ddf961a",
        "camp_origin_main_at_revalidation=7e3e65700c2bf910958788ac6cc5d7bf7ddf961a",
        "github_refs_heads_main_at_revalidation=7e3e65700c2bf910958788ac6cc5d7bf7ddf961a",
        "autodl_CAMP_HEAD_at_revalidation=7e3e65700c2bf910958788ac6cc5d7bf7ddf961a",
        "prior_design_head_at_revalidation=e7315c42398ed095a7df3e2e7ba5bdcbb4b8a0bc",
        "camp_head_at_revalidation=e73f9ea0b30f9619d2f56dea208c78c2b1c79901",
        "camp_origin_main_at_revalidation=e73f9ea0b30f9619d2f56dea208c78c2b1c79901",
        "github_refs_heads_main_at_revalidation=e73f9ea0b30f9619d2f56dea208c78c2b1c79901",
        "autodl_CAMP_HEAD_at_revalidation=e73f9ea0b30f9619d2f56dea208c78c2b1c79901",
        "prior_design_head_at_revalidation=1027a6b223c7a0ac75c7cbec56639841819bf475",
        NEXT_UNIT_TESTS_PLAN_GATE,
    ]:
        assert needle in text

    for needle in [
        "camp_head_at_revalidation=e73f9ea0b30f9619d2f56dea208c78c2b1c79901",
        "autodl_CAMP_HEAD_at_revalidation=e73f9ea0b30f9619d2f56dea208c78c2b1c79901",
        "prior_design_head_at_revalidation=1027a6b223c7a0ac75c7cbec56639841819bf475",
        "blocking_contract_findings=0",
        "score_expression=score_k(w)=a_k^T w",
        "fallback_cost_targets_nonnegative=True",
        "fixed_dp_candidate_reranking_only=True",
        "candidate_trajectory_rewrite_authorized=False",
        "local_target_pytest=24 passed",
        "autodl_target_pytest=24 passed",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        NEXT_UNIT_TESTS_PLAN_GATE,
    ]:
        assert needle in recent_review


def test_iteration_audit_records_static_contract_review_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    current_head_marker = (
        "## Current Tail Confirmation After Current HEAD e73f9ea Fallback Risk "
        "Ranking Remediation Static Contract Review"
    )
    current_head_audit = current_head_marker + audit.split(current_head_marker)[-1]

    for needle in [
        "status=fallback_risk_ranking_remediation_static_contract_review_passed_default_off_tests_plan_next",
        "current_head_static_contract_revalidated=True",
        "camp_head_at_revalidation=f4f076ab9d85a35d6d2bb3343405fddc8648f9fa",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "blocking_contract_findings=0",
        "fixed_candidate_boundary_passed=True",
        "affine_score_boundary_passed=True",
        "score_expression=score_k(w)=a_k^T w",
        "nonnegative_cost_boundary_passed=True",
        "fallback_cost_targets_nonnegative=True",
        "convex_master_boundary_passed=True",
        "feasible_master_separation_passed=True",
        "fallback_risk_training_authorized_now=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "dp_modification_authorized=False",
        NEXT_UNIT_TESTS_PLAN_GATE,
    ]:
        assert needle in audit

    for needle in [
        "status=fallback_risk_ranking_remediation_static_contract_review_passed_default_off_tests_plan_next",
        "static_contract_review=docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_remediation_static_contract_review.md",
        "camp_head_at_revalidation=e73f9ea0b30f9619d2f56dea208c78c2b1c79901",
        "autodl_CAMP_HEAD_at_revalidation=e73f9ea0b30f9619d2f56dea208c78c2b1c79901",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_design_head_at_revalidation=1027a6b223c7a0ac75c7cbec56639841819bf475",
        "blocking_contract_findings=0",
        "current_head_static_contract_revalidated=True",
        "fixed_candidate_boundary_passed=True",
        "affine_score_boundary_passed=True",
        "score_expression=score_k(w)=a_k^T w",
        "nonnegative_cost_boundary_passed=True",
        "fallback_cost_targets_nonnegative=True",
        "convex_master_boundary_passed=True",
        "feasible_master_separation_passed=True",
        "implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "local_target_pytest=24 passed",
        "autodl_target_pytest=24 passed",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in current_head_audit
