from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_unit_tests_plan.md"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_split_unit_tests_plan_records_preconditions_and_no_builder_authorization() -> None:
    text = _plan()

    for needle in [
        "split_manifest_plan_ready=True",
        "split_manifest_static_contract_review_passed=True",
        "blocking_contract_findings=0",
        "manifest_schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "records_scope=records_without_feasible_candidate_only",
        "validated_fallback_dataset_sha256=0978687b1f7582f6644eb9598bdc5a9e03494ad227d1627bd603d54e15efb8e2",
        "validated_fallback_records=15",
        "split_manifest_static_contract_tail_status=fallback_risk_training_split_manifest_static_contract_review_current_head_revalidated",
        "training_split_manifest_builder_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "user_camp_retraining_permission_available=True",
        "training_command_authorization_required_before_training=True",
        "camp_head_at_plan=6ea1a40de4fe895825d2f87e1bec851fa222994b",
        "latest_validated_fallback_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "latest_validated_fallback_records=15",
        "latest_split_manifest_static_contract_tail_status=fallback_risk_training_split_manifest_static_contract_review_autodl_verification_passed",
        "camp_head_at_latest_revalidation=6189214cacfa196515cfd4a5fa579eac30824c3e",
        "camp_origin_main_at_latest_revalidation=6189214cacfa196515cfd4a5fa579eac30824c3e",
        "github_refs_heads_main_at_latest_revalidation=6189214cacfa196515cfd4a5fa579eac30824c3e",
        "autodl_CAMP_HEAD_at_latest_revalidation=6189214cacfa196515cfd4a5fa579eac30824c3e",
        "autodl_CAMP_origin_main_at_latest_revalidation=6189214cacfa196515cfd4a5fa579eac30824c3e",
        "autodl_DP_HEAD_at_latest_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    ]:
        assert needle in text


def test_current_head_5753703_unit_tests_plan_revalidation_is_pinned() -> None:
    text = _plan()

    for needle in [
        "status=fallback_risk_training_split_manifest_unit_tests_plan_head_5753703_revalidated",
        "unit_tests_plan_base_head=57537031147c41abb6b811be8f932c1d3ec951ac",
        "camp_origin_main_at_unit_tests_plan=57537031147c41abb6b811be8f932c1d3ec951ac",
        "github_refs_heads_main_at_unit_tests_plan=57537031147c41abb6b811be8f932c1d3ec951ac",
        "autodl_CAMP_HEAD_at_unit_tests_plan=57537031147c41abb6b811be8f932c1d3ec951ac",
        "autodl_CAMP_origin_main_at_unit_tests_plan=57537031147c41abb6b811be8f932c1d3ec951ac",
        "autodl_DP_HEAD_at_unit_tests_plan=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_split_manifest_static_contract_status=fallback_risk_training_split_manifest_static_contract_review_head_1e1e8f1_revalidated",
        "head_5753703_validated_fallback_dataset_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "head_5753703_validated_fallback_records=15",
        "head_5753703_split_manifest_plan_ready=True",
        "head_5753703_split_manifest_static_contract_review_passed=True",
        "head_5753703_blocking_contract_findings=0",
        "head_5753703_manifest_schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "head_5753703_records_scope=records_without_feasible_candidate_only",
        "head_5753703_test_disabled_mode_does_not_read_dataset=True",
        "head_5753703_test_enabled_mode_reads_existing_validated_dataset_json_only=True",
        "head_5753703_test_requires_group_key_source_log_run_id_record_index=True",
        "head_5753703_test_does_not_use_selected_index_as_split_feature=True",
        "head_5753703_test_does_not_use_candidate_rank_as_split_feature=True",
        "head_5753703_test_does_not_use_closed_loop_outcome_as_split_feature=True",
        "head_5753703_test_training_and_validation_groups_are_disjoint=True",
        "head_5753703_test_final_decision_never_authorizes_training=True",
        "head_5753703_synthetic_dataset_fixtures_only=True",
        "head_5753703_synthetic_split_manifest_fixtures_only=True",
        "head_5753703_split_manifest_unit_tests_authorized=True",
        "head_5753703_training_split_manifest_builder_authorized=False",
        "head_5753703_local_unit_tests_plan_pytest=9 passed",
        "head_5753703_training_not_executed=True",
        "head_5753703_candidate_generation_not_executed=True",
        "head_5753703_dp_not_modified=True",
        "head_5753703_selector_or_atom_not_promoted=True",
        "this_split_manifest_unit_tests_plan_gate_authorizes_builder_training_replay_dp_or_claims=False",
    ]:
        assert needle in text


def test_current_head_7756feb_unit_tests_plan_revalidation_is_pinned() -> None:
    text = _plan()

    for needle in [
        "status=fallback_risk_training_split_manifest_unit_tests_plan_head_7756feb_revalidated",
        "unit_tests_plan_base_head=7756feb39b4492cda559dae261ebd6bb0fa2beb0",
        "camp_origin_main_at_unit_tests_plan=7756feb39b4492cda559dae261ebd6bb0fa2beb0",
        "github_refs_heads_main_at_unit_tests_plan=7756feb39b4492cda559dae261ebd6bb0fa2beb0",
        "autodl_CAMP_HEAD_at_unit_tests_plan=7756feb39b4492cda559dae261ebd6bb0fa2beb0",
        "autodl_CAMP_origin_main_at_unit_tests_plan=7756feb39b4492cda559dae261ebd6bb0fa2beb0",
        "autodl_DP_HEAD_at_unit_tests_plan=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_split_manifest_static_contract_status=fallback_risk_training_split_manifest_static_contract_review_head_2c8adc8_revalidated",
        "head_7756feb_validated_fallback_dataset_sha256=682d432f742d4ab68a262cf70955981bc1562cf1dbcf2ec094984a12fcd11498",
        "head_7756feb_validated_fallback_records=15",
        "head_7756feb_split_manifest_plan_ready=True",
        "head_7756feb_split_manifest_static_contract_review_passed=True",
        "head_7756feb_blocking_contract_findings=0",
        "head_7756feb_manifest_schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "head_7756feb_records_scope=records_without_feasible_candidate_only",
        "head_7756feb_test_disabled_mode_does_not_read_dataset=True",
        "head_7756feb_test_enabled_mode_reads_existing_validated_dataset_json_only=True",
        "head_7756feb_test_requires_group_key_source_log_run_id_record_index=True",
        "head_7756feb_test_does_not_use_selected_index_as_split_feature=True",
        "head_7756feb_test_does_not_use_candidate_rank_as_split_feature=True",
        "head_7756feb_test_does_not_use_closed_loop_outcome_as_split_feature=True",
        "head_7756feb_test_training_and_validation_groups_are_disjoint=True",
        "head_7756feb_test_final_decision_never_authorizes_training=True",
        "head_7756feb_synthetic_dataset_fixtures_only=True",
        "head_7756feb_synthetic_split_manifest_fixtures_only=True",
        "head_7756feb_split_manifest_unit_tests_authorized=True",
        "head_7756feb_training_split_manifest_builder_authorized=False",
        "head_7756feb_local_unit_tests_plan_pytest=10 passed",
        "head_7756feb_local_static_contract_review_pytest=9 passed",
        "head_7756feb_local_target_pytest=19 passed",
        "head_7756feb_training_not_executed=True",
        "head_7756feb_candidate_generation_not_executed=True",
        "head_7756feb_dp_not_modified=True",
        "head_7756feb_selector_or_atom_not_promoted=True",
        "this_split_manifest_unit_tests_plan_gate_authorizes_builder_training_replay_dp_or_claims=False",
    ]:
        assert needle in text


def test_current_head_84f24a1_unit_tests_plan_revalidation_is_pinned() -> None:
    text = _plan()
    audit = AUDIT_DOC.read_text(encoding="utf-8")
    audit_tail = audit[-16000:]
    combined = text + audit
    status = "status=fallback_risk_training_split_manifest_unit_tests_plan_head_84f24a1_revalidated"

    assert status in audit

    for needle in [
        status,
        "unit_tests_plan_base_head=84f24a1185845bf034f270aa85b9800ba9f31a62",
        "camp_origin_main_at_unit_tests_plan=84f24a1185845bf034f270aa85b9800ba9f31a62",
        "github_refs_heads_main_at_unit_tests_plan=84f24a1185845bf034f270aa85b9800ba9f31a62",
        "autodl_CAMP_HEAD_at_unit_tests_plan=84f24a1185845bf034f270aa85b9800ba9f31a62",
        "autodl_CAMP_origin_main_at_unit_tests_plan=84f24a1185845bf034f270aa85b9800ba9f31a62",
        "autodl_DP_HEAD_at_unit_tests_plan=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_split_manifest_static_contract_status=fallback_risk_training_split_manifest_static_contract_review_head_e5e292b_revalidated",
        "head_84f24a1_validated_fallback_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_84f24a1_validated_fallback_records=15",
        "head_84f24a1_split_manifest_plan_ready=True",
        "head_84f24a1_split_manifest_static_contract_review_passed=True",
        "head_84f24a1_blocking_contract_findings=0",
        "head_84f24a1_manifest_schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "head_84f24a1_records_scope=records_without_feasible_candidate_only",
        "head_84f24a1_test_disabled_mode_does_not_read_dataset=True",
        "head_84f24a1_test_enabled_mode_reads_existing_validated_dataset_json_only=True",
        "head_84f24a1_test_requires_group_key_source_log_run_id_record_index=True",
        "head_84f24a1_test_does_not_use_selected_index_as_split_feature=True",
        "head_84f24a1_test_does_not_use_candidate_rank_as_split_feature=True",
        "head_84f24a1_test_does_not_use_closed_loop_outcome_as_split_feature=True",
        "head_84f24a1_test_training_and_validation_groups_are_disjoint=True",
        "head_84f24a1_test_final_decision_never_authorizes_training=True",
        "head_84f24a1_synthetic_dataset_fixtures_only=True",
        "head_84f24a1_synthetic_split_manifest_fixtures_only=True",
        "head_84f24a1_split_manifest_unit_tests_authorized=True",
        "head_84f24a1_training_split_manifest_builder_authorized=False",
        "head_84f24a1_local_unit_tests_plan_pytest=11 passed",
        "head_84f24a1_local_static_contract_review_pytest=10 passed",
        "head_84f24a1_local_target_pytest=21 passed",
        "head_84f24a1_autodl_unit_tests_plan_pytest=11 passed",
        "head_84f24a1_autodl_static_contract_review_pytest=10 passed",
        "head_84f24a1_autodl_target_pytest=21 passed",
        "head_84f24a1_training_not_executed=True",
        "head_84f24a1_candidate_generation_not_executed=True",
        "head_84f24a1_dp_not_modified=True",
        "head_84f24a1_selector_or_atom_not_promoted=True",
        "this_split_manifest_unit_tests_plan_gate_authorizes_builder_training_replay_dp_or_claims=False",
        "head_84f24a1_camp_training_authorized=False",
        "head_84f24a1_camp_retraining_authorized=False",
        "head_84f24a1_formal_seeds_11_12_13_authorized=False",
        "head_84f24a1_safety_benefit_claim_authorized=False",
        "head_84f24a1_camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_unit_tests_only",
    ]:
        assert needle in combined


def test_current_head_350b666_unit_tests_plan_revalidation_is_pinned() -> None:
    text = _plan()
    audit_tail = AUDIT_DOC.read_text(encoding="utf-8")[-18000:]
    combined = text + audit_tail
    status = "status=fallback_risk_training_split_manifest_unit_tests_plan_head_350b666_revalidated"

    assert status in combined

    for needle in [
        status,
        "unit_tests_plan_base_head=350b666b5cfdb3505e080adccf350d2f0e256385",
        "camp_origin_main_at_unit_tests_plan=350b666b5cfdb3505e080adccf350d2f0e256385",
        "github_refs_heads_main_at_unit_tests_plan=350b666b5cfdb3505e080adccf350d2f0e256385",
        "autodl_CAMP_HEAD_at_unit_tests_plan=350b666b5cfdb3505e080adccf350d2f0e256385",
        "autodl_CAMP_origin_main_at_unit_tests_plan=350b666b5cfdb3505e080adccf350d2f0e256385",
        "autodl_DP_HEAD_at_unit_tests_plan=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_split_manifest_static_contract_status=fallback_risk_training_split_manifest_static_contract_review_head_7f72f61_revalidated",
        "head_350b666_validated_fallback_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_350b666_validated_fallback_records=15",
        "head_350b666_split_manifest_plan_ready=True",
        "head_350b666_split_manifest_static_contract_review_passed=True",
        "head_350b666_blocking_contract_findings=0",
        "head_350b666_manifest_schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "head_350b666_records_scope=records_without_feasible_candidate_only",
        "head_350b666_test_default_off_split_builder_requires_enable_flag=True",
        "head_350b666_test_disabled_mode_does_not_read_dataset=True",
        "head_350b666_test_enabled_mode_reads_existing_validated_dataset_json_only=True",
        "head_350b666_test_requires_validated_fallback_dataset_sha256=True",
        "head_350b666_test_requires_15_validated_fallback_records=True",
        "head_350b666_test_requires_records_without_feasible_candidate_only=True",
        "head_350b666_test_rejects_formal_seeds_11_12_13=True",
        "head_350b666_test_requires_group_key_source_log_run_id_record_index=True",
        "head_350b666_test_requires_record_identity_hash=True",
        "head_350b666_test_rejects_group_key_collision=True",
        "head_350b666_test_does_not_use_selected_index_as_split_feature=True",
        "head_350b666_test_does_not_use_candidate_rank_as_split_feature=True",
        "head_350b666_test_does_not_use_closed_loop_outcome_as_split_feature=True",
        "head_350b666_test_training_and_validation_groups_are_disjoint=True",
        "head_350b666_test_does_not_use_random_seed_python_hash_or_wall_clock=True",
        "head_350b666_test_manifest_top_level_fields_match_preflight_contract=True",
        "head_350b666_test_final_decision_never_authorizes_training=True",
        "head_350b666_test_final_decision_never_claims_training_sufficiency=True",
        "head_350b666_test_rejects_safety_or_camp_over_dp_claim=True",
        "head_350b666_synthetic_dataset_fixtures_only=True",
        "head_350b666_synthetic_split_manifest_fixtures_only=True",
        "head_350b666_split_manifest_unit_tests_plan_complete=True",
        "head_350b666_split_manifest_unit_tests_authorized=True",
        "head_350b666_training_split_manifest_builder_authorized=False",
        "head_350b666_local_unit_tests_plan_pytest=12 passed",
        "head_350b666_local_static_contract_review_pytest=11 passed",
        "head_350b666_local_target_pytest=23 passed",
        "head_350b666_autodl_unit_tests_plan_pytest=12 passed",
        "head_350b666_autodl_static_contract_review_pytest=11 passed",
        "head_350b666_autodl_target_pytest=23 passed",
        "head_350b666_training_not_executed=True",
        "head_350b666_candidate_generation_not_executed=True",
        "head_350b666_dp_not_modified=True",
        "head_350b666_selector_or_atom_not_promoted=True",
        "this_split_manifest_unit_tests_plan_gate_authorizes_builder_training_replay_dp_or_claims=False",
        "head_350b666_camp_training_authorized=False",
        "head_350b666_camp_retraining_authorized=False",
        "head_350b666_formal_seeds_11_12_13_authorized=False",
        "head_350b666_safety_benefit_claim_authorized=False",
        "head_350b666_camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_unit_tests_only",
    ]:
        assert needle in combined


def test_current_head_9c0a160_unit_tests_plan_revalidation_is_pinned() -> None:
    text = _plan()
    audit_tail = AUDIT_DOC.read_text(encoding="utf-8")[-18000:]
    combined = text + audit_tail
    status = "status=fallback_risk_training_split_manifest_unit_tests_plan_head_9c0a160_revalidated"

    assert status in audit_tail

    for needle in [
        status,
        "unit_tests_plan_base_head=9c0a160ca87bf6818de7bc6eb36c357f10f04ca2",
        "camp_origin_main_at_unit_tests_plan=9c0a160ca87bf6818de7bc6eb36c357f10f04ca2",
        "github_refs_heads_main_at_unit_tests_plan=9c0a160ca87bf6818de7bc6eb36c357f10f04ca2",
        "autodl_CAMP_HEAD_at_unit_tests_plan=9c0a160ca87bf6818de7bc6eb36c357f10f04ca2",
        "autodl_CAMP_origin_main_at_unit_tests_plan=9c0a160ca87bf6818de7bc6eb36c357f10f04ca2",
        "autodl_DP_HEAD_at_unit_tests_plan=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_split_manifest_static_contract_status=fallback_risk_training_split_manifest_static_contract_review_head_82800d9_revalidated",
        "head_9c0a160_validated_fallback_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_9c0a160_validated_fallback_records=15",
        "head_9c0a160_split_manifest_plan_ready=True",
        "head_9c0a160_split_manifest_static_contract_review_passed=True",
        "head_9c0a160_blocking_contract_findings=0",
        "head_9c0a160_manifest_schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "head_9c0a160_records_scope=records_without_feasible_candidate_only",
        "head_9c0a160_test_default_off_split_builder_requires_enable_flag=True",
        "head_9c0a160_test_disabled_mode_does_not_read_dataset=True",
        "head_9c0a160_test_enabled_mode_reads_existing_validated_dataset_json_only=True",
        "head_9c0a160_test_requires_validated_fallback_dataset_sha256=True",
        "head_9c0a160_test_requires_15_validated_fallback_records=True",
        "head_9c0a160_test_requires_records_without_feasible_candidate_only=True",
        "head_9c0a160_test_rejects_formal_seeds_11_12_13=True",
        "head_9c0a160_test_requires_group_key_source_log_run_id_record_index=True",
        "head_9c0a160_test_requires_record_identity_hash=True",
        "head_9c0a160_test_rejects_group_key_collision=True",
        "head_9c0a160_test_does_not_use_selected_index_as_split_feature=True",
        "head_9c0a160_test_does_not_use_candidate_rank_as_split_feature=True",
        "head_9c0a160_test_does_not_use_closed_loop_outcome_as_split_feature=True",
        "head_9c0a160_test_training_and_validation_groups_are_disjoint=True",
        "head_9c0a160_test_does_not_use_random_seed_python_hash_or_wall_clock=True",
        "head_9c0a160_test_rejects_validation_or_formal_scale_fit=True",
        "head_9c0a160_test_requires_fallback_master_isolation=True",
        "head_9c0a160_test_preserves_fixed_candidate_affine_reranking_boundary=True",
        "head_9c0a160_test_rejects_trajectory_generation_or_modification=True",
        "head_9c0a160_test_manifest_top_level_fields_match_preflight_contract=True",
        "head_9c0a160_test_final_decision_never_authorizes_training=True",
        "head_9c0a160_test_final_decision_never_claims_training_sufficiency=True",
        "head_9c0a160_test_rejects_safety_or_camp_over_dp_claim=True",
        "head_9c0a160_synthetic_dataset_fixtures_only=True",
        "head_9c0a160_synthetic_split_manifest_fixtures_only=True",
        "head_9c0a160_fixed_autodl_artifact_required_for_unit_tests=False",
        "head_9c0a160_formal_seeds_11_12_13_used=False",
        "head_9c0a160_replay_required_for_unit_tests=False",
        "head_9c0a160_candidate_generation_required_for_unit_tests=False",
        "head_9c0a160_training_required_for_unit_tests=False",
        "head_9c0a160_dp_required_for_unit_tests=False",
        "head_9c0a160_split_manifest_unit_tests_plan_complete=True",
        "head_9c0a160_split_manifest_unit_tests_authorized=True",
        "head_9c0a160_training_split_manifest_builder_authorized=False",
        "head_9c0a160_local_unit_tests_plan_pytest=13 passed",
        "head_9c0a160_local_static_contract_review_pytest=12 passed",
        "head_9c0a160_local_target_pytest=25 passed",
        "head_9c0a160_autodl_unit_tests_plan_pytest=13 passed",
        "head_9c0a160_autodl_static_contract_review_pytest=12 passed",
        "head_9c0a160_autodl_target_pytest=25 passed",
        "head_9c0a160_training_not_executed=True",
        "head_9c0a160_candidate_generation_not_executed=True",
        "head_9c0a160_dp_not_modified=True",
        "head_9c0a160_selector_or_atom_not_promoted=True",
        "this_split_manifest_unit_tests_plan_gate_authorizes_builder_training_replay_dp_or_claims=False",
        "head_9c0a160_camp_training_authorized=False",
        "head_9c0a160_camp_retraining_authorized=False",
        "head_9c0a160_formal_seeds_11_12_13_authorized=False",
        "head_9c0a160_safety_benefit_claim_authorized=False",
        "head_9c0a160_camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_unit_tests_only",
    ]:
        assert needle in combined


def test_split_unit_tests_plan_covers_default_off_and_dataset_scope() -> None:
    text = _plan()

    for needle in [
        "test_default_off_split_builder_requires_enable_flag=True",
        "test_disabled_mode_does_not_read_dataset=True",
        "test_enabled_mode_reads_existing_validated_dataset_json_only=True",
        "test_output_is_json_and_markdown_only=True",
        "test_requires_validated_fallback_dataset_sha256=True",
        "test_requires_validator_output_sha256=True",
        "test_requires_15_validated_fallback_records=True",
        "test_requires_records_without_feasible_candidate_only=True",
        "test_rejects_feasible_candidate_records=True",
        "test_rejects_formal_seeds_11_12_13=True",
        "test_rejects_formal_eval_artifact=True",
    ]:
        assert needle in text


def test_split_unit_tests_plan_covers_identity_and_forbidden_split_features() -> None:
    text = _plan()

    for needle in [
        "test_requires_group_key_source_log_run_id_record_index=True",
        "test_requires_source_log_sha256=True",
        "test_requires_candidate_count_and_oracle_index=True",
        "test_requires_record_identity_hash=True",
        "test_rejects_group_key_collision=True",
        "test_rejects_duplicate_record_identity=True",
        "test_does_not_use_selected_index_as_split_feature=True",
        "test_does_not_use_candidate_rank_as_split_feature=True",
        "test_does_not_use_closed_loop_outcome_as_split_feature=True",
        "test_does_not_use_learned_weights_as_split_feature=True",
    ]:
        assert needle in text


def test_split_unit_tests_plan_covers_deterministic_policy() -> None:
    text = _plan()

    for needle in [
        "test_uses_sha256_record_identity_hash_plus_split_salt=True",
        "test_uses_fixed_split_salt_fallback_risk_training_split_v1=True",
        "test_split_assignments_are_stable_across_input_order=True",
        "test_training_and_validation_groups_are_disjoint=True",
        "test_rejects_empty_training_or_validation_groups=True",
        "test_requires_minimum_one_training_group=True",
        "test_requires_minimum_one_validation_group=True",
        "test_validation_fraction_target_is_point_two=True",
        "test_does_not_use_random_seed_python_hash_or_wall_clock=True",
    ]:
        assert needle in text


def test_split_unit_tests_plan_covers_preflight_compatibility_and_claim_rejections() -> None:
    text = _plan()

    for needle in [
        "test_manifest_top_level_fields_match_preflight_contract=True",
        "test_record_assignments_cover_every_accepted_record_once=True",
        "test_record_counts_match_training_plus_validation=True",
        "test_final_decision_never_authorizes_training=True",
        "test_final_decision_never_claims_training_sufficiency=True",
        "test_final_decision_never_claims_deployable_checkpoint=True",
        "test_preflight_accepts_clean_synthetic_split_manifest=True",
        "test_rejects_safety_or_camp_over_dp_claim=True",
    ]:
        assert needle in text


def test_split_unit_tests_plan_uses_synthetic_fixtures_only() -> None:
    text = _plan()

    for needle in [
        "synthetic_dataset_fixtures_only=True",
        "synthetic_split_manifest_fixtures_only=True",
        "fixed_autodl_artifact_required_for_unit_tests=False",
        "formal_seeds_11_12_13_used=False",
        "replay_required_for_unit_tests=False",
        "candidate_generation_required_for_unit_tests=False",
        "training_required_for_unit_tests=False",
        "dp_required_for_unit_tests=False",
        "latest_synthetic_dataset_fixtures_only=True",
        "latest_synthetic_split_manifest_fixtures_only=True",
        "latest_fixed_autodl_artifact_required_for_unit_tests=False",
        "latest_formal_seeds_11_12_13_used=False",
        "latest_replay_required_for_unit_tests=False",
        "latest_candidate_generation_required_for_unit_tests=False",
        "latest_training_required_for_unit_tests=False",
        "latest_dp_required_for_unit_tests=False",
    ]:
        assert needle in text


def test_split_unit_tests_plan_forbids_execution_and_sets_unit_tests_next() -> None:
    text = _plan()

    for needle in [
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "status=fallback_risk_training_split_manifest_unit_tests_plan_ready",
        "split_manifest_unit_tests_plan_complete=True",
        "split_manifest_unit_tests_authorized=True",
        "training_split_manifest_builder_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "user_broad_execution_permission_recorded=True",
        "this_split_manifest_unit_tests_plan_gate_authorizes_builder_training_replay_dp_or_claims=False",
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
        "latest_status=fallback_risk_training_split_manifest_unit_tests_plan_ready",
        "latest_split_manifest_unit_tests_plan_complete=True",
        "latest_split_manifest_unit_tests_authorized=True",
        "latest_training_split_manifest_builder_authorized=False",
        "latest_fallback_risk_training_authorized_now=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_unit_tests_only",
        "may only add synthetic/static unit tests",
        "must not implement the builder",
        "generate the manifest",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text


def test_audit_tail_records_split_manifest_unit_tests_only_next_gate() -> None:
    tail = AUDIT_DOC.read_text(encoding="utf-8")[-16000:]

    assert (
        "status=fallback_risk_training_split_manifest_unit_tests_plan_head_9c0a160_revalidated"
        in tail
    )
    assert (
        "head_9c0a160_validated_fallback_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36"
        in tail
    )
    assert "head_9c0a160_local_unit_tests_plan_pytest=13 passed" in tail
    assert (
        "this_split_manifest_unit_tests_plan_gate_authorizes_builder_training_replay_dp_or_claims=False"
        in tail
    )
    assert "prior_split_manifest_static_contract_status=fallback_risk_training_split_manifest_static_contract_review_head_82800d9_revalidated" in tail
    assert "training_execution_authorized_now=False" in tail
    assert (
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_unit_tests_only"
        in tail
    )
