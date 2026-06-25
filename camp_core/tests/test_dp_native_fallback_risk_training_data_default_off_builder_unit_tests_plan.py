from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_unit_tests_plan.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
NEXT_UNIT_TESTS_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_training_data_default_off_builder_unit_tests_only"
)


def _text() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_builder_unit_tests_plan_preconditions() -> None:
    text = _text()

    for needle in [
        "training_data_design_plan_passed=True",
        "training_data_design_static_contract_review_passed=True",
        "blocking_contract_findings=0",
        "dataset_builder_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
    ]:
        assert needle in text


def test_builder_unit_tests_plan_covers_default_off_read_only_scope() -> None:
    text = _text()

    for needle in [
        "test_builder_disabled_does_not_read_missing_root=True",
        "test_builder_requires_enable_flag_before_reading_logs=True",
        "test_builder_reports_default_off_status=True",
        "test_builder_writes_only_explicit_output_paths=True",
        "test_builder_does_not_run_replay_or_candidate_generation=True",
        "test_builder_does_not_train_or_modify_dp=True",
        "test_builder_accepts_existing_selection_logs_only=True",
        "test_builder_filters_records_without_feasible_candidate_only=True",
        "test_builder_rejects_feasible_branch_records=True",
    ]:
        assert needle in text


def test_builder_unit_tests_plan_covers_provenance_and_atoms() -> None:
    text = _text()

    for needle in [
        "test_builder_requires_candidate_tensor_provenance=True",
        "test_builder_rejects_pre_post_tensor_hash_mismatch=True",
        "test_builder_rejects_candidate_row_append=True",
        "test_builder_rejects_coordinate_heading_speed_rewrite=True",
        "test_builder_requires_candidate_generation_contract=True",
        "test_builder_rejects_reference_blend_guidance_or_dp_weight_changes=True",
        "test_builder_requires_approved_atom_schema_and_names=True",
        "test_builder_rejects_negative_or_nonfinite_atoms=True",
    ]:
        assert needle in text


def test_builder_unit_tests_plan_covers_label_margin_and_dataset_output() -> None:
    text = _text()

    for needle in [
        "test_red_light_reason_uses_red_lane_quality_index_order=True",
        "test_lane_reason_uses_lane_red_quality_index_order=True",
        "test_other_reason_uses_quality_red_lane_index_order=True",
        "test_ties_break_by_candidate_index=True",
        "test_margin_is_fixed_nonnegative_and_clipped=True",
        "test_selected_index_not_used_as_feature=True",
        "test_candidate_rank_not_used_as_feature=True",
        "test_closed_loop_or_future_replanning_labels_rejected=True",
        "test_missing_required_cost_field_fails_closed=True",
        "test_dataset_schema_version_is_dp_native_fallback_risk_training_data_v1=True",
        "test_dataset_records_store_oracle_index_and_margin_vector=True",
        "test_dataset_summary_reports_training_not_authorized=True",
    ]:
        assert needle in text


def test_builder_unit_tests_plan_covers_validator_extension() -> None:
    text = _text()

    for needle in [
        "test_validator_extension_accepts_clean_fallback_dataset=True",
        "test_validator_extension_rejects_missing_source_identity=True",
        "test_validator_extension_rejects_feasible_record_leakage=True",
        "test_validator_extension_rejects_training_execution_flags=True",
        "test_validator_extension_rejects_online_selector_promotion_flags=True",
        "synthetic_records_only=True",
        "fixed_autodl_artifact_required_for_unit_tests=False",
    ]:
        assert needle in text


def test_builder_unit_tests_plan_forbids_execution_training_and_claims() -> None:
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
        "dataset_builder_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
    ]:
        assert needle in text

    for forbidden in [
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "candidate_generation_authorized=True",
        "formal_seeds_11_12_13_authorized=True",
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "dataset_builder_implementation_authorized=True",
        "fallback_risk_training_authorized_now=True",
    ]:
        assert forbidden not in text


def test_builder_unit_tests_plan_next_gate_tests_only() -> None:
    text = _text()

    for needle in [
        "status=fallback_risk_training_data_default_off_builder_unit_tests_plan_ready",
        "default_off_builder_unit_tests_plan_complete=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_unit_tests_only",
        "may only add default-off unit tests",
        "must not implement the builder",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text


def test_builder_unit_tests_plan_records_current_head_revalidation() -> None:
    text = _text()

    current_head = "07b95a6b129a3532f50e64cfde9c67801ac328b6"
    for needle in [
        f"camp_head_at_revalidation={current_head}",
        f"camp_origin_main_at_revalidation={current_head}",
        f"github_refs_heads_main_at_revalidation={current_head}",
        f"autodl_CAMP_HEAD_at_revalidation={current_head}",
        f"autodl_CAMP_origin_main_at_revalidation={current_head}",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_design_static_contract_status=fallback_risk_training_data_design_static_contract_review_current_head_revalidated_latest",
        "prior_design_static_contract_autodl_verified=True",
        "default_off_builder_unit_tests_plan_complete=True",
        "blocking_contract_findings=0",
        "local_py_compile_exit=0",
        "local_target_pytest=93 passed",
        "local_git_diff_check_exit=0",
        "autodl_CAMP_HEAD_after_sync=709984c588074e3424ca57339181a4a79ce7993b",
        "autodl_CAMP_origin_main_after_sync=709984c588074e3424ca57339181a4a79ce7993b",
        "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=93 passed",
        "autodl_git_diff_check_exit=0",
        "autodl_audit_tail_gate=dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_unit_tests_only",
        "dataset_builder_implementation_authorized=False",
        "validator_extension_implementation_authorized=False",
        "training_execution_authorized_now=False",
        NEXT_UNIT_TESTS_GATE,
    ]:
        assert needle in text


def test_iteration_audit_tail_records_builder_unit_tests_plan() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-120:])

    for needle in [
        "status=fallback_risk_training_data_default_off_builder_unit_tests_plan_current_head_revalidated_latest",
        "camp_head_at_revalidation=07b95a6b129a3532f50e64cfde9c67801ac328b6",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_design_static_contract_status=fallback_risk_training_data_design_static_contract_review_current_head_revalidated_latest",
        "prior_design_static_contract_autodl_verified=True",
        "default_off_builder_unit_tests_plan_complete=True",
        "blocking_contract_findings=0",
        "local_py_compile_exit=0",
        "local_target_pytest=93 passed",
        "local_git_diff_check_exit=0",
        "autodl_CAMP_HEAD_after_sync=709984c588074e3424ca57339181a4a79ce7993b",
        "autodl_CAMP_origin_main_after_sync=709984c588074e3424ca57339181a4a79ce7993b",
        "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=93 passed",
        "autodl_git_diff_check_exit=0",
        "autodl_audit_tail_gate=dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_unit_tests_only",
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
        NEXT_UNIT_TESTS_GATE,
    ]:
        assert needle in tail

    assert tail.rstrip().endswith(f"`{NEXT_UNIT_TESTS_GATE}`")
