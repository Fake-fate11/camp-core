from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_builder_implementation_authorization.md"
)


def _auth() -> str:
    return AUTH_DOC.read_text(encoding="utf-8")


def test_authorization_records_preconditions_and_verified_tests() -> None:
    text = _auth()

    for needle in [
        "fallback_master_config_and_command_plan_plan_ready=True",
        "fallback_master_config_and_command_plan_static_contract_review_passed=True",
        "scale_manifest_acceptance_passed=True",
        "blocking_contract_findings=0",
        "validated_dataset_split_and_scale_ready=True",
        "fallback_master_config_ready=False",
        "training_command_plan_ready=False",
        "training_sufficiency_preflight_ready=False",
        "accepted_train_only_scale_manifest_sha256=9e76915d544a04bcea31380323027511293419ea98f3b24406f951e52982570b",
        "local_static_contract_pytest=6 passed",
        "local_fallback_risk_related_pytest=298 passed",
        "autodl_static_contract_pytest=6 passed",
        "autodl_fallback_risk_related_pytest=298 passed",
        "dp_fixed_commit_verified=True",
    ]:
        assert needle in text


def test_authorization_only_allows_default_off_read_only_builder() -> None:
    text = _auth()

    for needle in [
        "implementation_authorized=True",
        "fallback_master_config_and_command_plan_builder_implementation_authorized=True",
        "default_off_required=True",
        "read_only_manifest_inputs_only=True",
        "reads_validated_dataset_json_only=True",
        "reads_training_split_manifest_json_only=True",
        "reads_train_only_scale_manifest_json_only=True",
        "output_json_or_markdown_only=True",
        "synthetic_unit_tests_required=True",
        "existing_contract_tests_must_continue_to_pass=True",
        "fixed_artifact_master_command_manifest_generation_authorized=False",
        "master_command_builder_execution_on_fixed_artifact_authorized=False",
        "training_sufficiency_preflight_execution_authorized=False",
    ]:
        assert needle in text


def test_authorization_requires_fail_closed_and_affine_contracts() -> None:
    text = _auth()

    for needle in [
        "must_return_before_reading_inputs_when_disabled=True",
        "must_fail_closed_on_missing_or_invalid_dataset_sha256=True",
        "must_fail_closed_on_missing_or_invalid_split_manifest_sha256=True",
        "must_fail_closed_on_missing_or_invalid_scale_manifest_sha256=True",
        "must_fail_closed_on_split_training_validation_overlap=True",
        "must_fail_closed_on_scale_fit_not_training_only=True",
        "must_fail_closed_on_formal_seed_or_formal_eval_leakage=True",
        "must_require_dp_camp_v10_14d_atom_schema=True",
        "must_require_exact_14d_atom_names=True",
        "must_require_strictly_positive_atom_scales=True",
        "must_emit_fallback_only_master_config=True",
        "must_emit_dry_run_training_command_plan=True",
        "must_preserve_score_k_equals_a_k_transpose_w_boundary=True",
        "must_keep_final_decision_training_authorized_false=True",
    ]:
        assert needle in text


def test_authorization_keeps_training_dp_preflight_and_claims_forbidden() -> None:
    text = _auth()

    for needle in [
        "training_authorized=False",
        "training_execution_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "replay_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
        "camp_training_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

    for forbidden in [
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "training_execution_authorized=True",
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "training_sufficiency_preflight_execution_authorized=True",
        "master_command_builder_execution_on_fixed_artifact_authorized=True",
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
        "status=fallback_risk_training_fallback_master_config_and_command_plan_builder_implementation_authorized",
        "passed=True",
        "implementation_authorized=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_builder_implementation_only",
        "may only implement the minimal default-off read-only builder",
        "must not run the builder on the fixed AutoDL artifact",
        "must not run the sufficiency preflight",
        "must not train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
        "promote",
    ]:
        assert needle in text
