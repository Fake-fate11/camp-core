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
    tail = "\n".join(AUDIT_DOC.read_text(encoding="utf-8").splitlines()[-120:])

    assert (
        "status=fallback_risk_training_train_only_scale_manifest_current_head_fixed_artifact_acceptance_passed"
        in tail
    )
    assert "local_target_pytest=111 passed" in tail
    assert "local_train_only_scale_acceptance_pytest=6 passed" in tail
    assert (
        "this_train_only_scale_acceptance_gate_authorizes_training_replay_dp_or_claims=False"
        in tail
    )
    assert "training_execution_authorized_now=False" in tail
    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only`"
    )
