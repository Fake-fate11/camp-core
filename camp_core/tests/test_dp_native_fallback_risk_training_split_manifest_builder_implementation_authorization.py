from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_implementation_authorization.md"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _auth() -> str:
    return AUTH_DOC.read_text(encoding="utf-8")


def test_split_builder_authorization_records_preconditions_and_verified_tests() -> None:
    text = _auth()

    for needle in [
        "split_manifest_plan_ready=True",
        "split_manifest_static_contract_review_passed=True",
        "split_manifest_unit_tests_plan_ready=True",
        "split_manifest_contract_tests_pinned=True",
        "blocking_contract_findings=0",
        "validated_fallback_records=15",
        "validated_fallback_dataset_sha256=0978687b1f7582f6644eb9598bdc5a9e03494ad227d1627bd603d54e15efb8e2",
        "validator_output_sha256=276ed840e674733861123bde0c1fa45474fbcba6d23d7faa83e53abbacd7b078",
        "split_manifest_unit_tests_tail_status=fallback_risk_training_split_manifest_unit_tests_current_head_revalidated",
        "camp_head_at_authorization=08d133344f6937e61d0a629bdf56cb998f15fa6f",
        "local_split_manifest_contract_pytest=8 passed",
        "autodl_split_manifest_contract_pytest=8 passed",
        "broad_fallback_risk_pytest_not_claimed=True",
        "dp_fixed_commit_verified=True",
        "latest_validated_fallback_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "latest_validator_output_sha256=276ed840e674733861123bde0c1fa45474fbcba6d23d7faa83e53abbacd7b078",
        "latest_split_manifest_unit_tests_tail_status=fallback_risk_training_split_manifest_unit_tests_autodl_verification_passed",
        "camp_head_at_latest_authorization=a373d046cbb690ae6127c79a39c2fdeeedea0129",
        "autodl_DP_HEAD_at_latest_authorization=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    ]:
        assert needle in text


def test_current_head_57f775e_builder_authorization_revalidation_is_pinned() -> None:
    text = _auth()

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_implementation_authorization_head_57f775e_revalidated",
        "builder_authorization_base_head=57f775e02bc3a47a290a218e37a3ef2d641bab73",
        "camp_origin_main_at_builder_authorization=57f775e02bc3a47a290a218e37a3ef2d641bab73",
        "github_refs_heads_main_at_builder_authorization=57f775e02bc3a47a290a218e37a3ef2d641bab73",
        "autodl_CAMP_HEAD_at_builder_authorization=57f775e02bc3a47a290a218e37a3ef2d641bab73",
        "autodl_CAMP_origin_main_at_builder_authorization=57f775e02bc3a47a290a218e37a3ef2d641bab73",
        "autodl_DP_HEAD_at_builder_authorization=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_split_manifest_unit_tests_status=fallback_risk_training_split_manifest_unit_tests_head_402b9a0_revalidated",
        "head_57f775e_validated_fallback_dataset_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "head_57f775e_validated_fallback_records=15",
        "head_57f775e_split_manifest_plan_ready=True",
        "head_57f775e_split_manifest_static_contract_review_passed=True",
        "head_57f775e_split_manifest_unit_tests_plan_ready=True",
        "head_57f775e_split_manifest_contract_tests_pinned=True",
        "head_57f775e_blocking_contract_findings=0",
        "head_57f775e_implementation_authorized=True",
        "head_57f775e_training_split_manifest_builder_implementation_authorized=True",
        "head_57f775e_default_off_required=True",
        "head_57f775e_read_only_dataset_input_only=True",
        "head_57f775e_existing_validated_fallback_dataset_json_only=True",
        "head_57f775e_synthetic_unit_tests_required=True",
        "head_57f775e_fixed_artifact_manifest_generation_authorized=False",
        "head_57f775e_training_split_manifest_builder_execution_on_fixed_artifact_authorized=False",
        "head_57f775e_training_execution_authorized_now=False",
        "head_57f775e_camp_retraining_authorized_now=False",
        "head_57f775e_local_authorization_pytest=7 passed",
        "head_57f775e_local_split_manifest_contract_pytest=8 passed",
        "head_57f775e_training_not_executed=True",
        "head_57f775e_candidate_generation_not_executed=True",
        "head_57f775e_dp_not_modified=True",
        "head_57f775e_selector_or_atom_not_promoted=True",
    ]:
        assert needle in text


def test_current_head_0f00924_builder_authorization_revalidation_is_pinned() -> None:
    text = _auth()

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_implementation_authorization_head_0f00924_revalidated",
        "builder_authorization_base_head=0f009240a79139532f8df9e528987eb05b8fe268",
        "camp_origin_main_at_builder_authorization=0f009240a79139532f8df9e528987eb05b8fe268",
        "github_refs_heads_main_at_builder_authorization=0f009240a79139532f8df9e528987eb05b8fe268",
        "autodl_CAMP_HEAD_at_builder_authorization=0f009240a79139532f8df9e528987eb05b8fe268",
        "autodl_CAMP_origin_main_at_builder_authorization=0f009240a79139532f8df9e528987eb05b8fe268",
        "autodl_DP_HEAD_at_builder_authorization=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_split_manifest_unit_tests_status=fallback_risk_training_split_manifest_unit_tests_head_e1f925a_revalidated",
        "head_0f00924_validated_fallback_dataset_sha256=682d432f742d4ab68a262cf70955981bc1562cf1dbcf2ec094984a12fcd11498",
        "head_0f00924_validated_fallback_records=15",
        "head_0f00924_split_manifest_plan_ready=True",
        "head_0f00924_split_manifest_static_contract_review_passed=True",
        "head_0f00924_split_manifest_unit_tests_plan_ready=True",
        "head_0f00924_split_manifest_contract_tests_pinned=True",
        "head_0f00924_blocking_contract_findings=0",
        "head_0f00924_implementation_authorized=True",
        "head_0f00924_training_split_manifest_builder_implementation_authorized=True",
        "head_0f00924_default_off_required=True",
        "head_0f00924_read_only_dataset_input_only=True",
        "head_0f00924_existing_validated_fallback_dataset_json_only=True",
        "head_0f00924_synthetic_unit_tests_required=True",
        "head_0f00924_fixed_artifact_manifest_generation_authorized=False",
        "head_0f00924_training_split_manifest_builder_execution_on_fixed_artifact_authorized=False",
        "head_0f00924_training_execution_authorized_now=False",
        "head_0f00924_camp_retraining_authorized_now=False",
        "head_0f00924_local_authorization_pytest=8 passed",
        "head_0f00924_local_split_manifest_contract_pytest=9 passed",
        "head_0f00924_local_target_pytest=17 passed",
        "head_0f00924_training_not_executed=True",
        "head_0f00924_candidate_generation_not_executed=True",
        "head_0f00924_dp_not_modified=True",
        "head_0f00924_selector_or_atom_not_promoted=True",
    ]:
        assert needle in text


def test_current_head_d377c2a_builder_authorization_revalidation_is_pinned() -> None:
    text = _auth()

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_implementation_authorization_head_d377c2a_revalidated",
        "builder_authorization_base_head=d377c2add1d85086aa9a4b8b8cb14b3adc326627",
        "camp_origin_main_at_builder_authorization=d377c2add1d85086aa9a4b8b8cb14b3adc326627",
        "github_refs_heads_main_at_builder_authorization=d377c2add1d85086aa9a4b8b8cb14b3adc326627",
        "autodl_CAMP_HEAD_at_builder_authorization=d377c2add1d85086aa9a4b8b8cb14b3adc326627",
        "autodl_CAMP_origin_main_at_builder_authorization=d377c2add1d85086aa9a4b8b8cb14b3adc326627",
        "autodl_DP_HEAD_at_builder_authorization=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_split_manifest_unit_tests_status=fallback_risk_training_split_manifest_unit_tests_head_f8f409b_revalidated",
        "head_d377c2a_validated_fallback_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_d377c2a_validated_fallback_records=15",
        "head_d377c2a_split_manifest_plan_ready=True",
        "head_d377c2a_split_manifest_static_contract_review_passed=True",
        "head_d377c2a_split_manifest_unit_tests_plan_ready=True",
        "head_d377c2a_split_manifest_contract_tests_pinned=True",
        "head_d377c2a_blocking_contract_findings=0",
        "head_d377c2a_implementation_authorized=True",
        "head_d377c2a_training_split_manifest_builder_implementation_authorized=True",
        "head_d377c2a_default_off_required=True",
        "head_d377c2a_read_only_dataset_input_only=True",
        "head_d377c2a_existing_validated_fallback_dataset_json_only=True",
        "head_d377c2a_synthetic_unit_tests_required=True",
        "head_d377c2a_fixed_artifact_manifest_generation_authorized=False",
        "head_d377c2a_training_split_manifest_builder_execution_on_fixed_artifact_authorized=False",
        "head_d377c2a_training_execution_authorized_now=False",
        "head_d377c2a_camp_retraining_authorized_now=False",
        "head_d377c2a_local_authorization_pytest=9 passed",
        "head_d377c2a_local_split_manifest_contract_pytest=9 passed",
        "head_d377c2a_local_target_pytest=18 passed",
        "head_d377c2a_training_not_executed=True",
        "head_d377c2a_candidate_generation_not_executed=True",
        "head_d377c2a_dp_not_modified=True",
        "head_d377c2a_selector_or_atom_not_promoted=True",
    ]:
        assert needle in text


def test_split_builder_authorization_only_allows_default_off_read_only_builder() -> None:
    text = _auth()

    for needle in [
        "implementation_authorized=True",
        "training_split_manifest_builder_implementation_authorized=True",
        "default_off_required=True",
        "read_only_dataset_input_only=True",
        "existing_validated_fallback_dataset_json_only=True",
        "records_scope=records_without_feasible_candidate_only",
        "output_json_or_markdown_only=True",
        "synthetic_unit_tests_required=True",
        "fixed_artifact_manifest_generation_authorized=False",
        "training_split_manifest_builder_execution_on_fixed_artifact_authorized=False",
        "user_broad_execution_permission_recorded=True",
        "latest_implementation_authorized=True",
        "latest_training_split_manifest_builder_implementation_authorized=True",
        "latest_fixed_artifact_manifest_generation_authorized=False",
        "latest_training_split_manifest_builder_execution_on_fixed_artifact_authorized=False",
    ]:
        assert needle in text


def test_split_builder_authorization_requires_fail_closed_contracts() -> None:
    text = _auth()

    for needle in [
        "must_return_before_reading_dataset_when_disabled=True",
        "must_fail_closed_on_missing_or_invalid_dataset_sha256=True",
        "must_fail_closed_on_missing_or_invalid_validator_output_sha256=True",
        "must_fail_closed_on_records_not_without_feasible_candidate=True",
        "must_fail_closed_on_missing_group_key_or_identity_hash=True",
        "must_fail_closed_on_group_key_collision_or_duplicate_identity=True",
        "must_fail_closed_on_formal_seeds_or_formal_eval_leakage=True",
        "must_not_use_selected_index_candidate_rank_closed_loop_outcome_or_learned_weights_as_split_features=True",
        "must_use_sha256_record_identity_hash_plus_split_salt=True",
        "must_use_split_salt_fallback_risk_training_split_v1=True",
        "must_require_nonempty_training_and_validation_groups=True",
        "must_emit_preflight_compatible_top_level_fields=True",
        "must_keep_final_decision_training_authorized_false=True",
    ]:
        assert needle in text


def test_split_builder_authorization_keeps_generation_training_dp_and_claims_forbidden() -> None:
    text = _auth()

    for needle in [
        "fixed_artifact_manifest_generation_authorized=False",
        "training_split_manifest_builder_execution_on_fixed_artifact_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "training_execution_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "replay_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "production_selector_change_authorized=False",
        "camp_training_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "latest_fallback_risk_training_authorized_now=False",
        "latest_camp_retraining_authorized_now=False",
        "latest_training_execution_authorized_now=False",
        "latest_dp_modification_authorized=False",
        "latest_safety_benefit_claim_authorized=False",
        "latest_camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

    for forbidden in [
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "fixed_artifact_manifest_generation_authorized=True",
        "training_split_manifest_builder_execution_on_fixed_artifact_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "fallback_risk_training_authorized_now=True",
    ]:
        assert forbidden not in text


def test_split_builder_authorization_next_gate_is_implementation_only() -> None:
    text = _auth()

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_implementation_authorized",
        "latest_status=fallback_risk_training_split_manifest_builder_implementation_authorized",
        "passed=True",
        "implementation_authorized=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_implementation_only",
        "may only implement the minimal default-off read-only split",
        "must not generate a",
        "fixed-artifact manifest",
        "train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
        "promote",
    ]:
        assert needle in text


def test_audit_tail_records_split_manifest_builder_implementation_next_gate() -> None:
    audit = AUDIT_DOC.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-190:])

    assert (
        "status=fallback_risk_training_split_manifest_builder_implementation_authorization_head_d377c2a_revalidated"
        in audit
    )
    assert "head_d377c2a_local_authorization_pytest=9 passed" in audit
    assert "head_d377c2a_local_split_manifest_contract_pytest=9 passed" in audit
    assert (
        "status=fallback_risk_training_split_manifest_builder_implementation_autodl_sync_verified"
        in tail
    )
    assert "training_execution_authorized_now=False" in tail
    assert (
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_post_implementation_static_contract_only`"
        in tail
    )
