from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_builder_implementation_authorization.md"
)


def _auth() -> str:
    return AUTH_DOC.read_text(encoding="utf-8")


def test_scale_builder_authorization_records_preconditions_and_verified_tests() -> None:
    text = _auth()

    for needle in [
        "scale_manifest_plan_ready=True",
        "scale_manifest_static_contract_review_passed=True",
        "scale_manifest_unit_tests_plan_ready=True",
        "scale_manifest_unit_tests_complete=True",
        "scale_manifest_contract_tests_pinned=True",
        "blocking_contract_findings=0",
        "accepted_split_training_records=13",
        "accepted_split_validation_records=2",
        "training_groups_disjoint_validation=True",
        "local_scale_manifest_contract_pytest=6 passed",
        "local_fallback_risk_pytest=265 passed",
        "autodl_scale_manifest_contract_pytest=6 passed",
        "autodl_fallback_risk_pytest=265 passed",
        "dp_fixed_commit_verified=True",
    ]:
        assert needle in text


def test_scale_builder_authorization_only_allows_default_off_read_only_builder() -> None:
    text = _auth()

    for needle in [
        "implementation_authorized=True",
        "train_only_scale_manifest_builder_implementation_authorized=True",
        "default_off_required=True",
        "read_only_dataset_and_split_input_only=True",
        "existing_validated_fallback_dataset_json_only=True",
        "existing_accepted_split_manifest_json_only=True",
        "records_scope=split_manifest_training_groups_only=True",
        "validation_groups_excluded_from_fit=True",
        "output_json_or_markdown_only=True",
        "synthetic_unit_tests_required=True",
        "existing_contract_tests_must_continue_to_pass=True",
        "fixed_artifact_scale_manifest_generation_authorized=False",
        "scale_manifest_builder_execution_on_fixed_artifact_authorized=False",
        "scale_fitting_on_fixed_artifact_authorized=False",
    ]:
        assert needle in text


def test_scale_builder_authorization_requires_fail_closed_contracts() -> None:
    text = _auth()

    for needle in [
        "must_return_before_reading_dataset_or_split_when_disabled=True",
        "must_fail_closed_on_missing_or_invalid_dataset_sha256=True",
        "must_fail_closed_on_missing_or_invalid_split_manifest_sha256=True",
        "must_fail_closed_on_missing_or_invalid_validator_output_sha256=True",
        "must_fail_closed_on_split_training_validation_overlap=True",
        "must_fail_closed_on_missing_training_or_validation_groups=True",
        "must_fail_closed_on_dataset_record_not_in_split_manifest=True",
        "must_fail_closed_on_formal_seeds_or_formal_eval_leakage=True",
        "must_not_use_selected_index_candidate_rank_closed_loop_outcome_or_learned_weights_as_scale_features=True",
        "must_require_dp_camp_v10_14d_atom_schema=True",
        "must_require_exact_14d_atom_names=True",
        "must_compute_train_only_positive_finite_p95_or_one_scales=True",
        "must_emit_preflight_compatible_top_level_fields=True",
        "must_keep_final_decision_training_authorized_false=True",
    ]:
        assert needle in text


def test_scale_builder_authorization_keeps_training_dp_and_claims_forbidden() -> None:
    text = _auth()

    for needle in [
        "fixed_artifact_scale_manifest_generation_authorized=False",
        "scale_manifest_builder_execution_on_fixed_artifact_authorized=False",
        "scale_fitting_on_fixed_artifact_authorized=False",
        "fallback_risk_training_authorized_now=False",
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
    ]:
        assert needle in text

    for forbidden in [
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "fixed_artifact_scale_manifest_generation_authorized=True",
        "scale_manifest_builder_execution_on_fixed_artifact_authorized=True",
        "scale_fitting_on_fixed_artifact_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "fallback_risk_training_authorized_now=True",
    ]:
        assert forbidden not in text


def test_scale_builder_authorization_next_gate_is_implementation_only() -> None:
    text = _auth()

    for needle in [
        "status=fallback_risk_training_train_only_scale_manifest_builder_implementation_authorized",
        "passed=True",
        "implementation_authorized=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_builder_implementation_only",
        "may only implement the minimal default-off read-only train-only",
        "must not run the",
        "fixed AutoDL artifact",
        "train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
        "promote",
    ]:
        assert needle in text
