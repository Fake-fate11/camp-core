from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_design_plan.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
NEXT_STATIC_REVIEW_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_training_data_design_static_contract_review_only"
)


def _text() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_training_data_design_plan_keeps_fallback_track_separate() -> None:
    text = _text()

    for needle in [
        "dataset_schema_version=dp_native_fallback_risk_training_data_v1",
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


def test_training_data_design_plan_declares_fixed_current_tick_labels() -> None:
    text = _text()

    for needle in [
        "closed_loop_outcome_label_source_authorized=False",
        "future_replanning_label_source_authorized=False",
        "replay_label_generation_authorized=False",
        "hand_authored_label_fill_authorized=False",
        "red_cost_k=max(-dp_candidate_rewards[k].red_light, 0)",
        "lane_cost_k=lane_crossing + static_crossing + off_road_fraction + lane_near_frac + lane_wide_frac + max(-centerline, 0)",
        "quality_cost_k=max(-dp_candidate_rewards[k].total, 0)",
        "oracle_order=lexicographic(red_cost,lane_cost,quality_cost,candidate_index)",
        "oracle_order=lexicographic(lane_cost,red_cost,quality_cost,candidate_index)",
        "oracle_order=lexicographic(quality_cost,red_cost,lane_cost,candidate_index)",
        "tie_breaker=candidate_index",
        "selected_index_used_as_feature=False",
        "candidate_rank_used_as_feature=False",
    ]:
        assert needle in text


def test_training_data_design_plan_preserves_convex_benders_boundary() -> None:
    text = _text()

    for needle in [
        "score_k(w)=a_k^T w",
        "a_k_fixed_before_weight_optimization=True",
        "a_k_nonnegative_benders_compatible_atoms_only=True",
        "new_atom_authorized_now=False",
        "fallback_label_is_not_a_deployed_atom=True",
        "simplex_master_convex_if_later_authorized=True",
        "cvar_master_convex_if_later_authorized=True",
        "l2_regularized_master_convex_if_later_authorized=True",
        "q_i(w)=max(0, max_k m_ik + (a_i,o_i - a_i,k)^T w)",
        "margin_ik_nonnegative=True",
    ]:
        assert needle in text


def test_training_data_design_plan_lists_required_work_before_training() -> None:
    text = _text()

    for needle in [
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
        "dataset_builder_implementation_authorized=False",
    ]:
        assert needle in text


def test_training_data_design_plan_forbids_execution_training_and_claims() -> None:
    text = _text()

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
    ]:
        assert needle in text

    for forbidden in [
        "replay_execution_authorized=True",
        "candidate_generation_authorized=True",
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "formal_seeds_11_12_13_authorized=True",
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "fallback_risk_training_authorized_now=True",
        "fallback_risk_smoke_authorized_now=True",
    ]:
        assert forbidden not in text


def test_training_data_design_plan_next_gate_static_review_only() -> None:
    text = _text()

    for needle in [
        "status=fallback_risk_training_data_design_plan_ready_static_contract_review",
        "fallback_training_data_design_complete=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_design_static_contract_review_only",
        "may only statically review this training-data design plan",
        "must not implement a dataset builder",
        "train CAMP",
        "modify Diffusion Planner",
        "promote",
    ]:
        assert needle in text


def test_training_data_design_plan_records_current_head_revalidation() -> None:
    text = _text()
    tail = "\n".join(text.splitlines()[-90:])

    current_head = "23a965ebc3c602082c396a63fb4ad178b70070f0"
    for needle in [
        "status=fallback_risk_training_data_design_plan_current_head_revalidated_latest",
        f"camp_head_at_revalidation={current_head}",
        f"camp_origin_main_at_revalidation={current_head}",
        f"github_refs_heads_main_at_revalidation={current_head}",
        f"autodl_CAMP_HEAD_at_revalidation={current_head}",
        f"autodl_CAMP_origin_main_at_revalidation={current_head}",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_extractor_contract_status=fallback_risk_ranking_default_off_extractor_post_implementation_static_contract_current_head_revalidated_latest",
        "prior_extractor_contract_tail_verified=True",
        "prior_extractor_contract_autodl_verified=True",
        "fallback_training_data_design_complete=True",
        "blocking_contract_findings=0",
        "local_py_compile_exit=0",
        "local_target_pytest=45 passed",
        "local_git_diff_check_exit=0",
        "dataset_builder_implementation_authorized=False",
        "validator_extension_implementation_authorized=False",
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
        NEXT_STATIC_REVIEW_GATE,
    ]:
        assert needle in tail

    assert tail.rstrip().endswith(f"```text\n{NEXT_STATIC_REVIEW_GATE}\n```")


def test_iteration_audit_records_training_data_design_plan() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_training_data_design_plan_current_head_revalidated_latest",
        "design_doc=docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_design_plan.md",
        "design_test=camp_core/tests/test_dp_native_fallback_risk_training_data_design_plan.py",
        "camp_head_at_revalidation=23a965ebc3c602082c396a63fb4ad178b70070f0",
        "camp_origin_main_at_revalidation=23a965ebc3c602082c396a63fb4ad178b70070f0",
        "github_refs_heads_main_at_revalidation=23a965ebc3c602082c396a63fb4ad178b70070f0",
        "autodl_CAMP_HEAD_at_revalidation=23a965ebc3c602082c396a63fb4ad178b70070f0",
        "autodl_CAMP_origin_main_at_revalidation=23a965ebc3c602082c396a63fb4ad178b70070f0",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_extractor_contract_status=fallback_risk_ranking_default_off_extractor_post_implementation_static_contract_current_head_revalidated_latest",
        "prior_extractor_contract_tail_verified=True",
        "prior_extractor_contract_autodl_verified=True",
        "fallback_training_data_design_complete=True",
        "blocking_contract_findings=0",
        "local_py_compile_exit=0",
        "local_target_pytest=45 passed",
        "local_git_diff_check_exit=0",
        "dataset_builder_implementation_authorized=False",
        "validator_extension_implementation_authorized=False",
        "fallback_risk_smoke_authorized_now=False",
        "fallback_risk_training_authorized_now=False",
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
        NEXT_STATIC_REVIEW_GATE,
    ]:
        assert needle in audit

    assert f"`{NEXT_STATIC_REVIEW_GATE}`" in audit
