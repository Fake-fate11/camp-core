from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_validated_dataset_summary_materialization_authorization.md"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _auth() -> str:
    return AUTH_DOC.read_text(encoding="utf-8")


def test_authorization_records_missing_preflight_summary_and_sources() -> None:
    text = _auth()

    for needle in [
        "validated_dataset_summary_json_found=False",
        "validator_validation_json_is_preflight_summary_shape=False",
        "summary_materialization_required=True",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f632c44_20260624T133402Z/dataset.json",
        "expected_dataset_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "source_validator_output_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_validator_acceptance_f4ea755_20260624T142300Z/validation.json",
        "expected_validator_output_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "validator_record_counts_records_checked=15",
        "validator_record_counts_failed_records=0",
        "validator_source_hashes_dataset_json=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "validator_final_decision_status=dp_native_fallback_risk_training_data_validator_complete",
        "validator_final_decision_passed=True",
    ]:
        assert needle in text


def test_authorization_allows_only_default_off_read_only_materializer() -> None:
    text = _auth()

    for needle in [
        "implementation_authorized=True",
        "validated_dataset_summary_materializer_implementation_authorized=True",
        "default_off_required=True",
        "read_only_existing_artifacts_only=True",
        "reads_dataset_json_only=True",
        "reads_validator_output_json_only=True",
        "output_json_or_markdown_only=True",
        "must_return_before_reading_inputs_when_disabled=True",
        "must_fail_closed_on_dataset_sha_mismatch=True",
        "must_fail_closed_on_validator_output_sha_mismatch=True",
        "must_fail_closed_on_validator_not_complete_or_not_passed=True",
        "must_fail_closed_on_failed_records_nonzero=True",
        "must_fail_closed_on_training_or_dp_flags=True",
        "must_emit_preflight_summary_shape=True",
        "summary_sha256_field=accepted_dataset_sha256",
        "summary_records_field=15",
        "summary_validator_status_field=dp_native_fallback_risk_training_data_validator_complete",
        "summary_validator_passed_field=True",
        "summary_training_sufficiency_claim=False",
        "summary_deployable_checkpoint_claim=False",
    ]:
        assert needle in text


def test_authorization_keeps_training_dp_and_claims_forbidden() -> None:
    text = _auth()

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
        "fallback_risk_training_authorized_now=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "feasible_ranking_master_change_authorized=False",
        "hard_feasibility_relaxation_authorized=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
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


def test_authorization_next_gate_is_summary_materializer_implementation_only() -> None:
    text = _auth()
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_training_validated_dataset_summary_materialization_authorized",
        "passed=True",
        "implementation_authorized=True",
        "camp_retraining_authorized_now=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_validated_dataset_summary_materializer_implementation_only",
        "may only implement the minimal default-off read-only summary materializer",
        "must not run preflight",
        "train CAMP",
        "generate candidates",
        "modify Diffusion Planner",
    ]:
        assert needle in text
        assert needle in audit
