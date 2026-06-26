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
    recent_plan = text.split(
        "## Current-Head Revalidation After e73f9ea Static Contract Review"
    )[-1]

    for needle in [
        "camp_head_at_revalidation=31b72358d4d40eace1c5daabc066fd7b2132551f",
        "camp_origin_main_at_revalidation=31b72358d4d40eace1c5daabc066fd7b2132551f",
        "github_refs_heads_main_at_revalidation=31b72358d4d40eace1c5daabc066fd7b2132551f",
        "autodl_CAMP_HEAD_at_revalidation=31b72358d4d40eace1c5daabc066fd7b2132551f",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_static_contract_status=fallback_risk_ranking_remediation_static_contract_review_passed_default_off_tests_plan_next",
        "blocking_contract_findings=0",
        "This revalidation remains tests-plan-only",
        "camp_head_at_revalidation=b9d939a97bcd811d92c33f98e2f3edeed3b14876",
        "camp_origin_main_at_revalidation=b9d939a97bcd811d92c33f98e2f3edeed3b14876",
        "github_refs_heads_main_at_revalidation=b9d939a97bcd811d92c33f98e2f3edeed3b14876",
        "autodl_CAMP_HEAD_at_revalidation=b9d939a97bcd811d92c33f98e2f3edeed3b14876",
        "camp_head_at_revalidation=bfa29bd54f3d5a6aa52fa87350f7fe2845b79597",
        "camp_origin_main_at_revalidation=bfa29bd54f3d5a6aa52fa87350f7fe2845b79597",
        "github_refs_heads_main_at_revalidation=bfa29bd54f3d5a6aa52fa87350f7fe2845b79597",
        "autodl_CAMP_HEAD_at_revalidation=bfa29bd54f3d5a6aa52fa87350f7fe2845b79597",
        "prior_static_contract_head_at_revalidation=7e3e65700c2bf910958788ac6cc5d7bf7ddf961a",
        "camp_head_at_revalidation=a9fbf1c00f2f9fea6847b88cf25d527b2cc6d0cc",
        "camp_origin_main_at_revalidation=a9fbf1c00f2f9fea6847b88cf25d527b2cc6d0cc",
        "github_refs_heads_main_at_revalidation=a9fbf1c00f2f9fea6847b88cf25d527b2cc6d0cc",
        "autodl_CAMP_HEAD_at_revalidation=a9fbf1c00f2f9fea6847b88cf25d527b2cc6d0cc",
        "prior_static_contract_head_at_revalidation=e73f9ea0b30f9619d2f56dea208c78c2b1c79901",
        NEXT_UNIT_TESTS_GATE,
    ]:
        assert needle in text

    for needle in [
        "camp_head_at_revalidation=a9fbf1c00f2f9fea6847b88cf25d527b2cc6d0cc",
        "autodl_CAMP_HEAD_at_revalidation=a9fbf1c00f2f9fea6847b88cf25d527b2cc6d0cc",
        "prior_static_contract_head_at_revalidation=e73f9ea0b30f9619d2f56dea208c78c2b1c79901",
        "current_head_unit_tests_plan_revalidated=True",
        "planned_default_off_tests=4",
        "implementation_authorized=False",
        "production_implementation_edit_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "local_target_pytest=32 passed",
        "autodl_target_pytest=32 passed",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        NEXT_UNIT_TESTS_GATE,
    ]:
        assert needle in recent_plan


def test_iteration_audit_tail_records_default_off_unit_tests_plan_next_gate() -> None:
    text = ITERATION_AUDIT.read_text(encoding="utf-8")
    current_head_marker = (
        "## Current Tail Confirmation After Current HEAD a9fbf1c Fallback Risk "
        "Ranking Default-Off Unit Tests Plan"
    )
    current_head_audit = current_head_marker + text.split(current_head_marker)[-1]

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
        assert needle in text

    for needle in [
        "status=fallback_risk_ranking_default_off_unit_tests_plan_ready_tests_only_gate",
        "unit_tests_plan=docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_unit_tests_plan.md",
        "camp_head_at_revalidation=a9fbf1c00f2f9fea6847b88cf25d527b2cc6d0cc",
        "autodl_CAMP_HEAD_at_revalidation=a9fbf1c00f2f9fea6847b88cf25d527b2cc6d0cc",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_static_contract_status=fallback_risk_ranking_remediation_static_contract_review_passed_default_off_tests_plan_next",
        "prior_static_contract_head_at_revalidation=e73f9ea0b30f9619d2f56dea208c78c2b1c79901",
        "current_head_unit_tests_plan_revalidated=True",
        "planned_default_off_tests=4",
        "planned_cost_extraction_tests=11",
        "planned_provenance_no_mutation_tests=8",
        "implementation_authorized=False",
        "production_implementation_edit_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "local_target_pytest=32 passed",
        "autodl_target_pytest=32 passed",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in current_head_audit


def test_current_head_40cb9a6_default_off_unit_tests_plan_is_pinned() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")

    for needle in [
        "camp_head_at_revalidation=40cb9a6cd0918192e0bcb7555a3204618f492584",
        "camp_origin_main_at_revalidation=40cb9a6cd0918192e0bcb7555a3204618f492584",
        "github_refs_heads_main_at_revalidation=40cb9a6cd0918192e0bcb7555a3204618f492584",
        "autodl_CAMP_HEAD_at_revalidation=40cb9a6cd0918192e0bcb7555a3204618f492584",
        "autodl_CAMP_origin_main_at_revalidation=40cb9a6cd0918192e0bcb7555a3204618f492584",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_static_contract_status=fallback_risk_ranking_remediation_static_contract_review_current_head_e96fcc7_passed_default_off_tests_plan_next",
        "prior_static_contract_head_at_revalidation=e96fcc7eddffb952ade6af5679ac699fc351d5a9",
        "status=fallback_risk_ranking_default_off_unit_tests_plan_current_head_40cb9a6_ready_tests_only_gate",
        "current_head_unit_tests_plan_revalidated=True",
        "planned_default_off_tests=4",
        "planned_scope_filtering_tests=4",
        "planned_candidate_validation_tests=6",
        "planned_cost_extraction_tests=11",
        "planned_provenance_no_mutation_tests=8",
        "planned_forbidden_side_effect_tests=7",
        "planned_future_label_tests=4",
        "implementation_authorized=False",
        "production_implementation_edit_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_UNIT_TESTS_GATE,
    ]:
        assert needle in text

    for needle in [
        "status=fallback_risk_ranking_default_off_unit_tests_plan_current_head_40cb9a6_ready_tests_only_gate",
        "current_head_unit_tests_plan_revalidated=True",
        "prior_static_contract_head_at_revalidation=e96fcc7eddffb952ade6af5679ac699fc351d5a9",
        "planned_default_off_tests=4",
        "planned_scope_filtering_tests=4",
        "planned_candidate_validation_tests=6",
        "planned_cost_extraction_tests=11",
        "planned_provenance_no_mutation_tests=8",
        "planned_forbidden_side_effect_tests=7",
        "implementation_authorized=False",
        "production_implementation_edit_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_UNIT_TESTS_GATE,
    ]:
        assert needle in audit


def test_current_head_af2f6e9_default_off_unit_tests_plan_is_pinned() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")

    for needle in [
        "camp_head_at_revalidation=af2f6e9231f76206e593a6f9b2aa23d0a1c9d023",
        "camp_origin_main_at_revalidation=af2f6e9231f76206e593a6f9b2aa23d0a1c9d023",
        "github_refs_heads_main_at_revalidation=af2f6e9231f76206e593a6f9b2aa23d0a1c9d023",
        "autodl_CAMP_HEAD_at_revalidation=af2f6e9231f76206e593a6f9b2aa23d0a1c9d023",
        "autodl_CAMP_origin_main_at_revalidation=af2f6e9231f76206e593a6f9b2aa23d0a1c9d023",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_static_contract_status=fallback_risk_ranking_remediation_static_contract_review_current_head_08b1a6f_passed_default_off_tests_plan_next",
        "prior_static_contract_head_at_revalidation=08b1a6f365f8c3f6915b1a0f8c1565cae215a5ab",
        "status=fallback_risk_ranking_default_off_unit_tests_plan_current_head_af2f6e9_ready_tests_only_gate",
        "current_head_unit_tests_plan_revalidated=True",
        "planned_default_off_tests=4",
        "planned_scope_filtering_tests=4",
        "planned_candidate_validation_tests=6",
        "planned_cost_extraction_tests=11",
        "planned_provenance_no_mutation_tests=8",
        "planned_forbidden_side_effect_tests=7",
        "planned_future_label_tests=4",
        "implementation_authorized=False",
        "production_implementation_edit_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_UNIT_TESTS_GATE,
    ]:
        assert needle in text

    for needle in [
        "status=fallback_risk_ranking_default_off_unit_tests_plan_current_head_af2f6e9_ready_tests_only_gate",
        "current_camp_head=af2f6e9231f76206e593a6f9b2aa23d0a1c9d023",
        "github_refs_heads_main=af2f6e9231f76206e593a6f9b2aa23d0a1c9d023",
        "autodl_CAMP_HEAD=af2f6e9231f76206e593a6f9b2aa23d0a1c9d023",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_static_contract_status=fallback_risk_ranking_remediation_static_contract_review_current_head_08b1a6f_passed_default_off_tests_plan_next",
        "prior_static_contract_head_at_revalidation=08b1a6f365f8c3f6915b1a0f8c1565cae215a5ab",
        "current_head_unit_tests_plan_revalidated=True",
        "planned_default_off_tests=4",
        "planned_scope_filtering_tests=4",
        "planned_candidate_validation_tests=6",
        "planned_cost_extraction_tests=11",
        "planned_provenance_no_mutation_tests=8",
        "planned_forbidden_side_effect_tests=7",
        "implementation_authorized=False",
        "production_implementation_edit_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_UNIT_TESTS_GATE,
    ]:
        assert needle in audit


def test_current_head_1921ccc_default_off_unit_tests_plan_is_pinned() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")

    for needle in [
        "camp_head_at_revalidation=1921ccca4feef7c9ccfaab5416a920913b3cbaaa",
        "camp_origin_main_at_revalidation=1921ccca4feef7c9ccfaab5416a920913b3cbaaa",
        "github_refs_heads_main_at_revalidation=1921ccca4feef7c9ccfaab5416a920913b3cbaaa",
        "autodl_CAMP_HEAD_at_revalidation=1921ccca4feef7c9ccfaab5416a920913b3cbaaa",
        "autodl_CAMP_origin_main_at_revalidation=1921ccca4feef7c9ccfaab5416a920913b3cbaaa",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_static_contract_status=fallback_risk_ranking_remediation_static_contract_review_current_head_013378c_passed_default_off_tests_plan_next",
        "prior_static_contract_head_at_revalidation=013378cbd94d001ce7657163342d92d805cb2da6",
        "status=fallback_risk_ranking_default_off_unit_tests_plan_current_head_1921ccc_ready_tests_only_gate",
        "current_head_unit_tests_plan_revalidated=True",
        "planned_default_off_tests=4",
        "planned_scope_filtering_tests=4",
        "planned_candidate_validation_tests=6",
        "planned_cost_extraction_tests=11",
        "planned_provenance_no_mutation_tests=8",
        "planned_forbidden_side_effect_tests=7",
        "planned_future_label_tests=4",
        "implementation_authorized=False",
        "production_implementation_edit_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_UNIT_TESTS_GATE,
    ]:
        assert needle in text

    for needle in [
        "status=fallback_risk_ranking_default_off_unit_tests_plan_current_head_1921ccc_ready_tests_only_gate",
        "current_camp_head=1921ccca4feef7c9ccfaab5416a920913b3cbaaa",
        "github_refs_heads_main=1921ccca4feef7c9ccfaab5416a920913b3cbaaa",
        "autodl_CAMP_HEAD=1921ccca4feef7c9ccfaab5416a920913b3cbaaa",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_static_contract_status=fallback_risk_ranking_remediation_static_contract_review_current_head_013378c_passed_default_off_tests_plan_next",
        "prior_static_contract_head_at_revalidation=013378cbd94d001ce7657163342d92d805cb2da6",
        "current_head_unit_tests_plan_revalidated=True",
        "planned_default_off_tests=4",
        "planned_scope_filtering_tests=4",
        "planned_candidate_validation_tests=6",
        "planned_cost_extraction_tests=11",
        "planned_provenance_no_mutation_tests=8",
        "planned_forbidden_side_effect_tests=7",
        "implementation_authorized=False",
        "production_implementation_edit_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "local_target_pytest=11 passed",
        "autodl_target_pytest=11 passed",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_UNIT_TESTS_GATE,
    ]:
        assert needle in audit


def test_current_head_b328539_default_off_unit_tests_plan_is_pinned() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")
    audit_tail = "\n".join(ITERATION_AUDIT.read_text(encoding="utf-8").splitlines()[-240:])

    for needle in [
        "camp_head_at_revalidation=b328539a6dd6ffac1f14d67f1af9e8e042622f82",
        "camp_origin_main_at_revalidation=b328539a6dd6ffac1f14d67f1af9e8e042622f82",
        "github_refs_heads_main_at_revalidation=b328539a6dd6ffac1f14d67f1af9e8e042622f82",
        "autodl_CAMP_HEAD_at_revalidation=b328539a6dd6ffac1f14d67f1af9e8e042622f82",
        "autodl_CAMP_origin_main_at_revalidation=b328539a6dd6ffac1f14d67f1af9e8e042622f82",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_static_contract_status=fallback_risk_ranking_remediation_static_contract_review_current_head_4995778_passed_default_off_tests_plan_next",
        "prior_static_contract_head_at_revalidation=49957782ca737b2370b82f5b4f725dcaf031989b",
        "status=fallback_risk_ranking_default_off_unit_tests_plan_current_head_b328539_ready_tests_only_gate",
        "current_head_unit_tests_plan_revalidated=True",
        "planned_default_off_tests=4",
        "planned_scope_filtering_tests=4",
        "planned_candidate_validation_tests=6",
        "planned_cost_extraction_tests=11",
        "planned_provenance_no_mutation_tests=8",
        "planned_forbidden_side_effect_tests=7",
        "planned_future_label_tests=4",
        "implementation_authorized=False",
        "production_implementation_edit_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "local_target_pytest=12 passed",
        "local_related_target_pytest=48 passed",
        "autodl_related_target_pytest=48 passed",
        NEXT_UNIT_TESTS_GATE,
    ]:
        assert needle in text

    assert audit_tail.rstrip().endswith(NEXT_UNIT_TESTS_GATE + "\n```")

    for needle in [
        "status=fallback_risk_ranking_default_off_unit_tests_plan_current_head_b328539_ready_tests_only_gate",
        "current_camp_head=b328539a6dd6ffac1f14d67f1af9e8e042622f82",
        "github_refs_heads_main=b328539a6dd6ffac1f14d67f1af9e8e042622f82",
        "autodl_CAMP_HEAD=b328539a6dd6ffac1f14d67f1af9e8e042622f82",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_static_contract_status=fallback_risk_ranking_remediation_static_contract_review_current_head_4995778_passed_default_off_tests_plan_next",
        "prior_static_contract_head_at_revalidation=49957782ca737b2370b82f5b4f725dcaf031989b",
        "current_head_unit_tests_plan_revalidated=True",
        "planned_default_off_tests=4",
        "planned_scope_filtering_tests=4",
        "planned_candidate_validation_tests=6",
        "planned_cost_extraction_tests=11",
        "planned_provenance_no_mutation_tests=8",
        "planned_forbidden_side_effect_tests=7",
        "implementation_authorized=False",
        "production_implementation_edit_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "local_target_pytest=12 passed",
        "autodl_related_target_pytest=48 passed",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_UNIT_TESTS_GATE,
    ]:
        assert needle in audit_tail
