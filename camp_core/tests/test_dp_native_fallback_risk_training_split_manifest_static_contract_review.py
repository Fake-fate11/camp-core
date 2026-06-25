from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_static_contract_review.md"
)
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_plan.md"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _review() -> str:
    return REVIEW_DOC.read_text(encoding="utf-8")


def test_split_static_review_records_source_scope_and_no_execution() -> None:
    text = _review()

    for needle in [
        "source_scope_passed=True",
        "manifest_input=existing_validated_fallback_risk_training_dataset_json_only",
        "validated_fallback_dataset_sha256=0978687b1f7582f6644eb9598bdc5a9e03494ad227d1627bd603d54e15efb8e2",
        "split_manifest_plan_tail_status=fallback_risk_training_split_manifest_plan_current_head_revalidated",
        "camp_head_at_review=f1406c4d676260f6a499c3fbf35a1d9c60cc72bd",
        "validated_fallback_records=15",
        "records_scope=records_without_feasible_candidate_only",
        "candidate_generation_authorized=False",
        "replay_execution_authorized=False",
        "training_execution_authorized=False",
        "latest_source_scope_passed=True",
        "latest_validated_fallback_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "latest_split_manifest_plan_tail_status=fallback_risk_training_split_manifest_plan_autodl_verification_passed",
        "camp_head_at_latest_revalidation=50fe49eb3e5967e589884371cbe2676614102e9b",
        "autodl_DP_HEAD_at_latest_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_manifest_input=existing_validated_fallback_risk_training_dataset_json_only",
        "latest_validated_fallback_records=15",
        "latest_records_scope=records_without_feasible_candidate_only",
        "latest_candidate_generation_authorized=False",
        "latest_replay_execution_authorized=False",
        "latest_training_execution_authorized=False",
    ]:
        assert needle in text


def test_split_static_review_records_identity_and_forbidden_features() -> None:
    text = _review()

    for needle in [
        "split_identity_passed=True",
        "group_key_fields=source_log,run_id,record_index",
        "split_units=record_identity_groups",
        "record_identity_hash_required=True",
        "dataset_sha256_required=True",
        "validator_output_sha256_required=True",
        "selected_index_used_as_split_feature=False",
        "candidate_rank_used_as_split_feature=False",
        "closed_loop_outcome_used_as_split_feature=False",
        "latest_split_identity_passed=True",
        "latest_group_key_fields=source_log,run_id,record_index",
        "latest_split_units=record_identity_groups",
        "latest_record_identity_hash_required=True",
        "latest_dataset_sha256_required=True",
        "latest_validator_output_sha256_required=True",
        "latest_selected_index_used_as_split_feature=False",
        "latest_candidate_rank_used_as_split_feature=False",
        "latest_closed_loop_outcome_used_as_split_feature=False",
    ]:
        assert needle in text


def test_split_static_review_records_deterministic_policy() -> None:
    text = _review()

    for needle in [
        "deterministic_policy_passed=True",
        "split_policy=sha256(record_identity_hash + split_salt)",
        "split_salt=fallback_risk_training_split_v1",
        "validation_fraction_target=0.2",
        "min_validation_groups=1",
        "min_training_groups=1",
        "group_collision_fails_closed=True",
        "empty_train_or_validation_fails_closed=True",
        "training_groups_disjoint_from_validation_groups=True",
        "latest_deterministic_policy_passed=True",
        "latest_split_policy=sha256(record_identity_hash + split_salt)",
        "latest_split_salt=fallback_risk_training_split_v1",
        "latest_validation_fraction_target=0.2",
        "latest_min_validation_groups=1",
        "latest_min_training_groups=1",
        "latest_group_collision_fails_closed=True",
        "latest_empty_train_or_validation_fails_closed=True",
        "latest_training_groups_disjoint_from_validation_groups=True",
    ]:
        assert needle in text


def test_split_static_review_records_formal_and_training_boundary() -> None:
    text = _review()
    plan = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_training_split_manifest_plan_ready",
        "training_split_manifest_builder_authorized=False",
    ]:
        assert needle in plan

    for needle in [
        "formal_and_training_boundary_passed=True",
        "formal_seeds_11_12_13_excluded=True",
        "formal_eval_artifact_excluded=True",
        "fixed_15_record_artifact_training_sufficiency_claim=False",
        "training_split_manifest_builder_authorized=False",
        "user_camp_retraining_permission_available=True",
        "training_command_authorization_required_before_training=True",
        "formal_evaluation_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "latest_formal_and_training_boundary_passed=True",
        "latest_formal_seeds_11_12_13_excluded=True",
        "latest_formal_eval_artifact_excluded=True",
        "latest_fixed_15_record_artifact_training_sufficiency_claim=False",
        "latest_training_split_manifest_builder_authorized=False",
    ]:
        assert needle in text


def test_split_static_review_forbids_training_dp_and_claims() -> None:
    text = _review()

    for needle in [
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "user_broad_execution_permission_recorded=True",
        "this_split_manifest_static_review_gate_authorizes_builder_training_replay_dp_or_claims=False",
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
        "latest_fallback_dataset_training_sufficiency_claim=False",
        "latest_all_infeasible_records_added_to_feasible_training=False",
    ]:
        assert needle in text


def test_split_static_review_next_gate_is_unit_tests_plan_only() -> None:
    text = _review()

    for needle in [
        "status=fallback_risk_training_split_manifest_static_contract_review_passed",
        "status=fallback_risk_training_split_manifest_static_contract_review_latest_head_revalidated",
        "static_contract_review_complete=True",
        "blocking_contract_findings=0",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_unit_tests_plan_only",
        "may only plan synthetic/static unit tests",
        "must not generate the manifest",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text


def test_audit_tail_records_split_manifest_unit_tests_plan_next_gate() -> None:
    tail = "\n".join(AUDIT_DOC.read_text(encoding="utf-8").splitlines()[-120:])

    assert (
        "status=fallback_risk_training_split_manifest_unit_tests_autodl_verification_passed"
        in tail
    )
    assert "local_split_manifest_contract_pytest=8 passed" in tail
    assert "training_execution_authorized_now=False" in tail
    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_implementation_authorization_only`"
    )
