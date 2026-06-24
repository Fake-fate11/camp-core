from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_implementation_authorization.md"
)


def _auth() -> str:
    return AUTH_DOC.read_text(encoding="utf-8")


def test_authorization_records_preconditions_and_verified_tests() -> None:
    text = _auth()

    for needle in [
        "training_sufficiency_plan_ready=True",
        "training_sufficiency_static_contract_review_passed=True",
        "training_sufficiency_unit_tests_plan_ready=True",
        "training_sufficiency_contract_tests_pinned=True",
        "blocking_contract_findings=0",
        "validated_fallback_records=15",
        "local_training_sufficiency_contract_pytest=7 passed",
        "local_fallback_risk_pytest=164 passed",
        "autodl_training_sufficiency_contract_pytest=7 passed",
        "autodl_fallback_risk_pytest=164 passed",
        "dp_fixed_commit_verified=True",
        "current_training_sufficiency_plan_ready=True",
        "current_training_sufficiency_static_contract_review_passed=True",
        "current_training_sufficiency_unit_tests_plan_ready=True",
        "current_training_sufficiency_contract_tests_pinned=True",
        "current_blocking_contract_findings=0",
        "current_validated_fallback_dataset_sha256=0978687b1f7582f6644eb9598bdc5a9e03494ad227d1627bd603d54e15efb8e2",
        "current_local_training_sufficiency_contract_pytest=7 passed",
        "current_local_training_sufficiency_plan_static_pytest=19 passed",
        "current_autodl_training_sufficiency_contract_pytest=7 passed",
        "current_autodl_training_sufficiency_plan_static_pytest=19 passed",
        "current_dp_fixed_commit_verified=True",
    ]:
        assert needle in text


def test_authorization_only_allows_default_off_read_only_preflight() -> None:
    text = _auth()

    for needle in [
        "implementation_authorized=True",
        "fallback_risk_training_sufficiency_preflight_implementation_authorized=True",
        "default_off_required=True",
        "read_only_manifest_inputs_only=True",
        "reads_validated_dataset_summary_json_only=True",
        "reads_training_split_manifest_json_only=True",
        "reads_train_only_scale_manifest_json_only=True",
        "reads_fallback_master_config_json_only=True",
        "reads_training_command_plan_json_only=True",
        "output_json_or_markdown_only=True",
        "current_implementation_authorized=True",
        "current_fallback_risk_training_sufficiency_preflight_implementation_authorized=True",
        "current_default_off_required=True",
        "current_read_only_manifest_inputs_only=True",
        "current_reads_validated_dataset_summary_json_only=True",
        "current_reads_training_split_manifest_json_only=True",
        "current_reads_train_only_scale_manifest_json_only=True",
        "current_reads_fallback_master_config_json_only=True",
        "current_reads_training_command_plan_json_only=True",
        "current_output_json_or_markdown_only=True",
    ]:
        assert needle in text


def test_authorization_requires_fail_closed_contracts() -> None:
    text = _auth()

    for needle in [
        "must_return_before_reading_inputs_when_disabled=True",
        "must_fail_closed_on_missing_or_invalid_validated_dataset_summary=True",
        "must_fail_closed_on_missing_split_manifest_or_group_overlap=True",
        "must_fail_closed_on_formal_seeds_or_formal_eval_leakage=True",
        "must_fail_closed_on_validation_or_formal_scale_fit_leakage=True",
        "must_fail_closed_on_nonpositive_scales_or_atom_schema_mismatch=True",
        "must_fail_closed_on_fallback_master_feasible_branch_leakage=True",
        "must_fail_closed_on_training_command_execution_or_dp_modification_flags=True",
        "must_reject_selector_atom_promotion_or_claim_flags=True",
        "must_preserve_score_k_equals_a_k_transpose_w_boundary=True",
        "current_must_return_before_reading_inputs_when_disabled=True",
        "current_must_fail_closed_on_missing_or_invalid_validated_dataset_summary=True",
        "current_must_fail_closed_on_missing_split_manifest_or_group_overlap=True",
        "current_must_fail_closed_on_formal_seeds_or_formal_eval_leakage=True",
        "current_must_fail_closed_on_validation_or_formal_scale_fit_leakage=True",
        "current_must_fail_closed_on_nonpositive_scales_or_atom_schema_mismatch=True",
        "current_must_fail_closed_on_fallback_master_feasible_branch_leakage=True",
        "current_must_fail_closed_on_training_command_execution_or_dp_modification_flags=True",
        "current_must_reject_selector_atom_promotion_or_claim_flags=True",
        "current_must_preserve_score_k_equals_a_k_transpose_w_boundary=True",
    ]:
        assert needle in text


def test_authorization_keeps_training_dp_and_promotion_forbidden() -> None:
    text = _auth()

    for needle in [
        "training_authorized=False",
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
        "current_training_authorized=False",
        "current_camp_retraining_authorized_now=False",
        "current_replay_authorized=False",
        "current_candidate_generation_authorized=False",
        "current_dp_modification_authorized=False",
        "current_production_selector_change_authorized=False",
        "current_camp_training_authorized=False",
        "current_formal_seeds_11_12_13_authorized=False",
        "current_selector_promotion_authorized=False",
        "current_atom_promotion_authorized=False",
        "current_safety_benefit_claim_authorized=False",
        "current_camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

    for forbidden in [
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "fallback_risk_training_authorized_now=True",
    ]:
        assert forbidden not in text


def test_authorization_next_gate_is_implementation_only() -> None:
    text = _auth()

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_implementation_authorized",
        "passed=True",
        "implementation_authorized=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_implementation_only",
        "may only implement the minimal default-off read-only preflight",
        "must not train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
        "promote",
    ]:
        assert needle in text
