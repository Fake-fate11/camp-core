from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_design_static_contract_review.md"
)
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_design_plan.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
NEXT_UNIT_TESTS_PLAN_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_training_data_default_off_builder_unit_tests_"
    "plan_only"
)


def _review() -> str:
    return REVIEW_DOC.read_text(encoding="utf-8")


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_static_review_passes_source_isolation_boundary() -> None:
    text = _review()

    for needle in [
        "source_isolation_passed=True",
        "records_scope=records_without_feasible_candidate_only",
        "source_logs=existing_camp_selection_log_json_only",
        "source_extractor_records=default_off_fallback_risk_extractor_output_only",
        "fixed_candidate_set_only=True",
        "feasible_branch_records_allowed=False",
        "all_infeasible_records_relabelled_feasible=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "feasible_ranking_master_change_authorized=False",
        "hard_feasibility_relaxation_authorized=False",
    ]:
        assert needle in text


def test_static_review_passes_label_legality_boundary() -> None:
    text = _review()
    plan = _plan()

    for needle in [
        "label_legality_passed=True",
        "closed_loop_outcome_label_source_authorized=False",
        "future_replanning_label_source_authorized=False",
        "replay_label_generation_authorized=False",
        "hand_authored_label_fill_authorized=False",
        "red_cost_nonnegative=True",
        "lane_cost_nonnegative=True",
        "quality_cost_nonnegative=True",
        "oracle_policy_predeclared=True",
        "oracle_tie_breaker_deterministic=True",
        "selected_index_used_as_feature=False",
        "candidate_rank_used_as_feature=False",
    ]:
        assert needle in text

    for needle in [
        "red_cost_k=max(-dp_candidate_rewards[k].red_light, 0)",
        "lane_cost_k=lane_crossing + static_crossing",
        "quality_cost_k=max(-dp_candidate_rewards[k].total, 0)",
        "tie_breaker=candidate_index",
    ]:
        assert needle in plan


def test_static_review_preserves_convex_master_boundary() -> None:
    text = _review()
    plan = _plan()

    for needle in [
        "score_k(w)=a_k^T w",
        "convex_master_boundary_passed=True",
        "a_k_fixed_before_weight_optimization=True",
        "a_k_nonnegative_benders_compatible_atoms_only=True",
        "new_atom_authorized_now=False",
        "fallback_label_is_not_a_deployed_atom=True",
        "margin_ik_nonnegative=True",
        "simplex_master_convex_if_later_authorized=True",
        "cvar_master_convex_if_later_authorized=True",
        "l2_regularized_master_convex_if_later_authorized=True",
    ]:
        assert needle in text

    assert "q_i(w)=max(0, max_k m_ik + (a_i,o_i - a_i,k)^T w)" in plan


def test_static_review_rejects_training_sufficiency_shortcut() -> None:
    text = _review()

    for needle in [
        "training_sufficiency_boundary_passed=True",
        "fixed_artifact_training_sufficiency_claim=False",
        "default_off_dataset_builder_implemented=False",
        "dataset_builder_unit_tests_required=True",
        "clean_training_data_validator_extension_required=True",
        "fallback_dataset_static_contract_review_required=True",
        "training_validation_split_predeclaration_required=True",
        "formal_seeds_11_12_13_excluded_required=True",
        "scale_fit_training_groups_only_required=True",
        "fallback_master_isolated_from_feasible_master_required=True",
        "nonpromotion_boundary_required=True",
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
        "fallback_risk_smoke_authorized_now=False",
        "dataset_builder_implementation_authorized=False",
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
        "fallback_risk_smoke_authorized_now=True",
        "dataset_builder_implementation_authorized=True",
    ]:
        assert forbidden not in text


def test_static_review_next_gate_unit_tests_plan_only() -> None:
    text = _review()

    for needle in [
        "status=fallback_risk_training_data_design_static_contract_review_passed_default_off_builder_unit_tests_plan_next",
        "blocking_contract_findings=0",
        "require_default_off_builder=True",
        "require_synthetic_unit_tests=True",
        "require_missing_field_fail_closed_tests=True",
        "require_validator_extension_plan=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_unit_tests_plan_only",
        "may only plan unit tests",
        "must not implement the builder",
        "train CAMP",
    ]:
        assert needle in text


def test_static_review_records_current_head_revalidation() -> None:
    text = _review()

    current_head = "86f2e145eca229ae466cb201a9d3cc58347b61b6"
    for needle in [
        f"camp_head_at_revalidation={current_head}",
        f"camp_origin_main_at_revalidation={current_head}",
        f"github_refs_heads_main_at_revalidation={current_head}",
        f"autodl_CAMP_HEAD_at_revalidation={current_head}",
        f"autodl_CAMP_origin_main_at_revalidation={current_head}",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_design_status=fallback_risk_training_data_design_plan_current_head_revalidated_latest",
        "prior_design_autodl_verified=True",
        "source_isolation_passed=True",
        "label_legality_passed=True",
        "convex_master_boundary_passed=True",
        "training_sufficiency_boundary_passed=True",
        "blocking_contract_findings=0",
        "local_py_compile_exit=0",
        "local_target_pytest=84 passed",
        "local_git_diff_check_exit=0",
        "autodl_CAMP_HEAD_after_sync=5c4058d79bfbdd0a26cfae43cd33aa6fe47cefd0",
        "autodl_CAMP_origin_main_after_sync=5c4058d79bfbdd0a26cfae43cd33aa6fe47cefd0",
        "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=84 passed",
        "autodl_git_diff_check_exit=0",
        "autodl_audit_tail_gate=dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_unit_tests_plan_only",
        "validator_extension_implementation_authorized=False",
        "training_execution_authorized_now=False",
        NEXT_UNIT_TESTS_PLAN_GATE,
    ]:
        assert needle in text


def test_iteration_audit_tail_records_design_static_contract_review() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-120:])

    for needle in [
        "status=fallback_risk_training_data_design_static_contract_review_current_head_revalidated_latest",
        "camp_head_at_revalidation=86f2e145eca229ae466cb201a9d3cc58347b61b6",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_design_status=fallback_risk_training_data_design_plan_current_head_revalidated_latest",
        "prior_design_autodl_verified=True",
        "source_isolation_passed=True",
        "label_legality_passed=True",
        "convex_master_boundary_passed=True",
        "training_sufficiency_boundary_passed=True",
        "blocking_contract_findings=0",
        "local_py_compile_exit=0",
        "local_target_pytest=84 passed",
        "local_git_diff_check_exit=0",
        "autodl_CAMP_HEAD_after_sync=5c4058d79bfbdd0a26cfae43cd33aa6fe47cefd0",
        "autodl_CAMP_origin_main_after_sync=5c4058d79bfbdd0a26cfae43cd33aa6fe47cefd0",
        "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=84 passed",
        "autodl_git_diff_check_exit=0",
        "autodl_audit_tail_gate=dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_unit_tests_plan_only",
        "dataset_builder_implementation_authorized=False",
        "validator_extension_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
        "training_execution_authorized_now=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_UNIT_TESTS_PLAN_GATE,
    ]:
        assert needle in tail

    assert tail.rstrip().endswith(f"`{NEXT_UNIT_TESTS_PLAN_GATE}`")
