from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_unit_tests_plan.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
NEXT_UNIT_TESTS_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_ranking_default_off_unit_tests_only"
)


def test_default_off_unit_tests_plan_uses_static_review_requirements() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "require_default_off_flag=True",
        "require_read_only_extractor_unit_tests=True",
        "require_missing_field_fail_closed_tests=True",
        "require_no_training_or_deployment_side_effect_tests=True",
        "fixed_candidate_boundary_passed=True",
        "affine_score_boundary_passed=True",
        "nonnegative_cost_boundary_passed=True",
        "convex_master_boundary_passed=True",
        "feasible_master_separation_passed=True",
    ]:
        assert needle in text


def test_default_off_unit_tests_plan_covers_default_off_and_scope() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "test_default_off_does_not_emit_fallback_risk_records=True",
        "test_default_off_does_not_change_training_records=True",
        "test_default_off_does_not_change_selected_index=True",
        "test_default_off_does_not_change_scores_or_atoms=True",
        "test_extracts_records_without_feasible_candidate_only=True",
        "test_skips_records_with_any_feasible_candidate=True",
        "test_preserves_all_infeasible_records_as_infeasible=True",
        "test_does_not_add_all_infeasible_records_to_feasible_master=True",
    ]:
        assert needle in text


def test_default_off_unit_tests_plan_covers_validation_and_costs() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "test_rejects_selected_index_out_of_range=True",
        "test_rejects_feasible_mask_candidate_count_mismatch=True",
        "test_rejects_dp_candidate_rewards_candidate_count_mismatch=True",
        "test_red_light_cost_uses_max_negative_reward_hinge=True",
        "test_lane_related_cost_uses_logged_lane_fields=True",
        "test_quality_cost_uses_max_negative_total_reward_hinge=True",
        "test_cost_vectors_are_nonnegative_and_finite=True",
        "test_ties_return_all_min_indices=True",
        "test_missing_red_light_field_fails_closed=True",
        "test_missing_total_field_fails_closed=True",
        "test_nonfinite_cost_field_fails_closed=True",
    ]:
        assert needle in text


def test_default_off_unit_tests_plan_covers_provenance_and_forbidden_paths() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "test_requires_candidate_tensor_provenance_payload=True",
        "test_rejects_pre_post_tensor_hash_mismatch=True",
        "test_rejects_candidate_count_changed=True",
        "test_rejects_candidate_row_append=True",
        "test_rejects_coordinate_heading_speed_rewrite=True",
        "test_rejects_candidate_tensor_mutation_effect=True",
        "test_rejects_reference_blend_present=True",
        "test_rejects_closed_loop_outcome_fields_read=True",
        "test_no_replay_execution_path=True",
        "test_no_candidate_generation_path=True",
        "test_no_camp_training_path=True",
        "test_no_dp_modification_path=True",
        "test_no_selector_promotion_path=True",
        "test_no_atom_promotion_path=True",
    ]:
        assert needle in text


def test_default_off_unit_tests_plan_forbids_implementation_and_training() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "implementation_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "Full36_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "closed_loop_outcome_online_input_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

    for forbidden in [
        "implementation_authorized=True",
        "fallback_risk_extractor_implementation_authorized=True",
        "fallback_risk_training_authorized_now=True",
        "camp_training_authorized=True",
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
    ]:
        assert forbidden not in text


def test_default_off_unit_tests_plan_next_gate_tests_only() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_ranking_default_off_unit_tests_plan_ready_tests_only_gate",
        "planned_default_off_tests=4",
        "planned_scope_filtering_tests=4",
        "planned_candidate_validation_tests=6",
        "planned_cost_extraction_tests=11",
        "planned_provenance_no_mutation_tests=8",
        "planned_forbidden_side_effect_tests=7",
        "planned_future_label_tests=4",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_unit_tests_only",
        "The next gate may only add focused default-off contract tests",
    ]:
        assert needle in text


def test_default_off_unit_tests_plan_current_head_revalidation() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "camp_head_at_revalidation=31b72358d4d40eace1c5daabc066fd7b2132551f",
        "camp_origin_main_at_revalidation=31b72358d4d40eace1c5daabc066fd7b2132551f",
        "github_refs_heads_main_at_revalidation=31b72358d4d40eace1c5daabc066fd7b2132551f",
        "autodl_CAMP_HEAD_at_revalidation=31b72358d4d40eace1c5daabc066fd7b2132551f",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_static_contract_status=fallback_risk_ranking_remediation_static_contract_review_passed_default_off_tests_plan_next",
        "blocking_contract_findings=0",
        "This revalidation remains tests-plan-only",
        NEXT_UNIT_TESTS_GATE,
    ]:
        assert needle in text


def test_iteration_audit_tail_records_default_off_unit_tests_plan_next_gate() -> None:
    text = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(text.splitlines()[-110:])

    for needle in [
        "status=fallback_risk_ranking_default_off_unit_tests_plan_ready_tests_only_gate",
        "current_head_unit_tests_plan_revalidated=True",
        "camp_head_at_revalidation=31b72358d4d40eace1c5daabc066fd7b2132551f",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_static_contract_status=fallback_risk_ranking_remediation_static_contract_review_passed_default_off_tests_plan_next",
        "planned_default_off_tests=4",
        "planned_cost_extraction_tests=11",
        "planned_provenance_no_mutation_tests=8",
        "implementation_authorized=False",
        "production_implementation_edit_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "dp_modification_authorized=False",
        NEXT_UNIT_TESTS_GATE,
    ]:
        assert needle in tail

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_unit_tests_only`"
    )
