from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_plan.md"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_split_manifest_plan_records_validated_dataset_and_no_generation() -> None:
    text = _plan()

    for needle in [
        "validated_fallback_dataset_sha256=0978687b1f7582f6644eb9598bdc5a9e03494ad227d1627bd603d54e15efb8e2",
        "validated_fallback_records=15",
        "preflight_tail_authority_status=fallback_risk_training_sufficiency_preflight_post_implementation_static_contract_tail_revalidated",
        "camp_head_at_plan=b80f5e55b5d6e2124905bacef5ee554c47419954",
        "manifest_input=existing_validated_fallback_risk_training_dataset_json_only",
        "records_scope=records_without_feasible_candidate_only",
        "candidate_generation_authorized=False",
        "replay_execution_authorized=False",
        "training_execution_authorized=False",
        "latest_validated_fallback_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "latest_validated_fallback_records=15",
        "latest_preflight_tail_authority_status=fallback_risk_training_sufficiency_preflight_post_implementation_static_contract_autodl_verification_passed",
        "camp_head_at_latest_revalidation=ccd925be133c5e776d1314a8e6ac138b5cbb9cb3",
        "autodl_DP_HEAD_at_latest_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_manifest_input=existing_validated_fallback_risk_training_dataset_json_only",
        "latest_records_scope=records_without_feasible_candidate_only",
        "latest_candidate_generation_authorized=False",
        "latest_replay_execution_authorized=False",
        "latest_training_execution_authorized=False",
    ]:
        assert needle in text


def test_split_manifest_plan_defines_group_identity_and_forbidden_split_features() -> None:
    text = _plan()

    for needle in [
        "group_key_fields=source_log,run_id,record_index",
        "split_units=record_identity_groups",
        "training_groups_disjoint_from_validation_groups=True",
        "required_record_fields=source_log,source_log_sha256,run_id,record_index,candidate_count,oracle_index",
        "record_identity_hash_required=True",
        "selected_index_used_as_split_feature=False",
        "candidate_rank_used_as_split_feature=False",
        "closed_loop_outcome_used_as_split_feature=False",
        "latest_group_key_fields=source_log,run_id,record_index",
        "latest_split_units=record_identity_groups",
        "latest_training_groups_disjoint_from_validation_groups=True",
        "latest_required_record_fields=source_log,source_log_sha256,run_id,record_index,candidate_count,oracle_index",
        "latest_record_identity_hash_required=True",
        "latest_selected_index_used_as_split_feature=False",
        "latest_candidate_rank_used_as_split_feature=False",
        "latest_closed_loop_outcome_used_as_split_feature=False",
    ]:
        assert needle in text


def test_split_manifest_plan_predeclares_deterministic_policy_and_small_data_boundary() -> None:
    text = _plan()

    for needle in [
        "split_policy=sha256(record_identity_hash + split_salt)",
        "split_salt=fallback_risk_training_split_v1",
        "validation_fraction_target=0.2",
        "min_validation_groups=1",
        "min_training_groups=1",
        "group_collision_fails_closed=True",
        "empty_train_or_validation_fails_closed=True",
        "fixed_15_record_artifact_training_sufficiency_claim=False",
        "latest_split_policy=sha256(record_identity_hash + split_salt)",
        "latest_split_salt=fallback_risk_training_split_v1",
        "latest_validation_fraction_target=0.2",
        "latest_min_validation_groups=1",
        "latest_min_training_groups=1",
        "latest_group_collision_fails_closed=True",
        "latest_empty_train_or_validation_fails_closed=True",
    ]:
        assert needle in text


def test_split_manifest_plan_requires_default_off_builder_and_preflight_fields() -> None:
    text = _plan()

    for needle in [
        "default_off_builder_required=True",
        "enable_flag_required=True",
        "disabled_mode_reads_dataset=False",
        "output_json_or_markdown_only=True",
        "training_split_manifest_json_required=True",
        "preflight_compatible_fields_required=True",
        "user_camp_retraining_permission_available=True",
        "training_command_authorization_required_before_training=True",
        "top_level_fields=schema_version,dataset_sha256,validator_output_sha256,split_policy,split_salt,group_key_fields,training_groups,validation_groups,record_assignments,record_counts,final_decision",
        "latest_default_off_builder_required=True",
        "latest_enable_flag_required=True",
        "latest_disabled_mode_reads_dataset=False",
        "latest_output_json_or_markdown_only=True",
        "latest_training_split_manifest_json_required=True",
        "latest_preflight_compatible_fields_required=True",
        "latest_training_split_manifest_builder_authorized=False",
    ]:
        assert needle in text


def test_split_manifest_plan_forbids_training_dp_and_claims() -> None:
    text = _plan()

    for needle in [
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "user_broad_execution_permission_recorded=True",
        "this_split_manifest_plan_gate_authorizes_builder_training_replay_dp_or_claims=False",
        "latest_camp_training_authorized=False",
        "latest_camp_retraining_authorized=False",
        "latest_formal_seeds_11_12_13_authorized=False",
        "latest_dp_modification_authorized=False",
        "latest_selector_promotion_authorized=False",
        "latest_atom_promotion_authorized=False",
        "latest_safety_benefit_claim_authorized=False",
        "latest_camp_over_dp_top1_claim_authorized=False",
        "latest_fallback_dataset_training_sufficiency_claim=False",
        "latest_all_infeasible_records_added_to_feasible_training=False",
    ]:
        assert needle in text


def test_split_manifest_plan_next_gate_is_static_review_only() -> None:
    text = _plan()

    for needle in [
        "status=fallback_risk_training_split_manifest_plan_ready",
        "status=fallback_risk_training_split_manifest_plan_latest_head_revalidated",
        "training_split_manifest_plan_complete=True",
        "training_split_manifest_builder_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_static_contract_review_only",
        "may only statically review this split manifest plan",
        "must not",
        "generate the manifest",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text


def test_audit_tail_records_split_manifest_static_review_next_gate() -> None:
    tail = "\n".join(AUDIT_DOC.read_text(encoding="utf-8").splitlines()[-190:])

    assert (
        "status=fallback_risk_training_fallback_master_config_and_command_plan_current_head_fixed_artifact_acceptance_passed"
        in tail
    )
    assert "local_master_command_acceptance_pytest=6 passed" in tail
    assert "training_execution_authorized_now=False" in tail
    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_validated_dataset_summary_materializer_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only`"
    )
