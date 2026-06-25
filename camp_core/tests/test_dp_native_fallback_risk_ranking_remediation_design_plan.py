from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_remediation_design_plan.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
NEXT_STATIC_REVIEW_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_ranking_remediation_static_contract_review_only"
)
NEXT_UNIT_TESTS_PLAN_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_ranking_default_off_unit_tests_plan_only"
)


def test_fallback_risk_remediation_design_uses_fixed_artifact_evidence() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "records_without_feasible_candidate=15",
        "dp_red_light_cost_selected_min_count=14/15",
        "dp_red_light_cost_lower_cost_fixed_candidate_available_count=1/15",
        "lane_related_cost_selected_min_count=4/15",
        "lane_related_cost_lower_cost_fixed_candidate_available_count=11/15",
        "dp_reward_quality_cost_selected_min_count=15/15",
        "lower_risk_fixed_candidate_exists_under_logged_costs=True",
        "status=fallback_risk_ranking_remediation_design_plan_ready_static_contract_review",
    ]:
        assert needle in text


def test_fallback_risk_remediation_design_is_default_off_and_separate() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "default_off=True",
        "nondeployable_diagnostic_only=True",
        "fixed_candidate_set_only=True",
        "records_scope=records_without_feasible_candidate_only",
        "all_infeasible_records_relabelled_feasible=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "feasible_ranking_master_change_authorized=False",
        "hard_feasibility_relaxation_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
    ]:
        assert needle in text

    for forbidden in [
        "default_off=False",
        "nondeployable_diagnostic_only=False",
        "all_infeasible_records_relabelled_feasible=True",
        "all_infeasible_records_added_to_feasible_training=True",
        "feasible_ranking_master_change_authorized=True",
        "fallback_risk_training_authorized_now=True",
    ]:
        assert forbidden not in text


def test_fallback_risk_remediation_design_preserves_math_contract() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "score_k(w)=a_k^T w",
        "candidate_features_fixed_before_weight_optimization=True",
        "candidate_features_independent_of_w_rank_and_selected_index=True",
        "fallback_cost_targets_nonnegative=True",
        "simplex_master_convex_if_later_authorized=True",
        "cvar_master_convex_if_later_authorized=True",
        "l2_regularized_master_convex_if_later_authorized=True",
        "new_atom_authorized_now=False",
        "training_authorized_now=False",
        "alpha_values_authorized_now=False",
    ]:
        assert needle in text


def test_fallback_risk_remediation_design_forbids_nonpaper_routes() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

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
    ]:
        assert needle in text

    for forbidden in [
        "candidate_generation_authorized=True",
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "dp_modification_authorized=True",
        "reference_blend_authorized=True",
        "guidance_authorized=True",
        "postprocess_postselection_authorized=True",
        "closed_loop_outcome_online_input_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in text


def test_fallback_risk_remediation_design_next_gate_static_review_only() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    assert NEXT_STATIC_REVIEW_GATE in text
    assert "It must not implement the extractor" in text
    assert "train CAMP" in text


def test_fallback_risk_remediation_design_current_head_revalidation() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "camp_head_at_revalidation=30e16f3e132064366720ff58af9549de10f5d9d1",
        "camp_origin_main_at_revalidation=30e16f3e132064366720ff58af9549de10f5d9d1",
        "github_refs_heads_main_at_revalidation=30e16f3e132064366720ff58af9549de10f5d9d1",
        "autodl_CAMP_HEAD_at_revalidation=30e16f3e132064366720ff58af9549de10f5d9d1",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_ranking_revalidation_status=dp_native_fixed_artifact_fallback_risk_ranking_audit_complete",
        "prior_ranking_revalidation_failed_checks=[]",
        "prior_ranking_revalidation_json_sha256=52bb6f5168483cf6843a98214a21f1d597e31030eb1dbb47387a827e87732fcc",
        "This remains a plan-only gate",
        NEXT_STATIC_REVIEW_GATE,
    ]:
        assert needle in text


def test_iteration_audit_records_remediation_design_plan_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_ranking_remediation_design_plan_ready_static_contract_review",
        "current_head_design_plan_revalidated=True",
        "camp_head_at_revalidation=30e16f3e132064366720ff58af9549de10f5d9d1",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "score_expression=score_k(w)=a_k^T w",
        "fallback_cost_targets_nonnegative=True",
        "simplex_master_convex_if_later_authorized=True",
        "fallback_risk_training_authorized_now=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "dp_modification_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_STATIC_REVIEW_GATE,
    ]:
        assert needle in audit
