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
    ]:
        assert needle in text


def test_split_static_review_next_gate_is_unit_tests_plan_only() -> None:
    text = _review()

    for needle in [
        "status=fallback_risk_training_split_manifest_static_contract_review_passed",
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
        "status=fallback_risk_training_split_manifest_static_contract_review_current_head_revalidated"
        in tail
    )
    assert "local_target_pytest=7 passed" in tail
    assert "training_execution_authorized_now=False" in tail
    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_unit_tests_plan_only`"
    )
