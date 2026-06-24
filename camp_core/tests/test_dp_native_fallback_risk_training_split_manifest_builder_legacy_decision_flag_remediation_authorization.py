from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_legacy_decision_flag_remediation_authorization.md"
)


def _auth() -> str:
    return AUTH_DOC.read_text(encoding="utf-8")


def test_remediation_authorization_records_failed_acceptance_evidence() -> None:
    text = _auth()

    for needle in [
        "fixed_artifact_acceptance_audit_complete=True",
        "fixed_artifact_acceptance_passed=False",
        "blocking_acceptance_findings=1",
        "legacy_final_decision_flag_compatibility_issue=True",
        "single_error=final_decision_fallback_risk_training_authorized_now_not_false",
        "dataset_sha256_matched=True",
        "validator_output_sha256_recorded=True",
        "builder_failed_closed=True",
        "local_acceptance_audit_pytest=5 passed",
        "local_fallback_risk_pytest=224 passed",
        "autodl_acceptance_audit_pytest=5 passed",
        "autodl_fallback_risk_pytest=224 passed",
        "dp_fixed_commit_verified=True",
        "local_target_pytest=4 passed",
        "local_fallback_risk_related_pytest=228 passed",
    ]:
        assert needle in text


def test_remediation_authorization_scope_is_missing_legacy_flags_only() -> None:
    text = _auth()

    for needle in [
        "implementation_authorized=True",
        "legacy_decision_flag_remediation_implementation_authorized=True",
        "may_treat_absent_legacy_final_decision_forbidden_flags_as_false=True",
        "must_reject_explicit_true_forbidden_flags=True",
        "must_reject_present_non_false_forbidden_flags=True",
        "must_scope_to_input_dataset_final_decision_validation_only=True",
        "must_preserve_output_final_decision_forbidden_flags_false=True",
        "must_add_synthetic_missing_legacy_flag_test=True",
        "must_add_synthetic_explicit_true_flag_rejection_test=True",
    ]:
        assert needle in text


def test_remediation_authorization_keeps_fixed_artifact_rerun_and_training_forbidden() -> None:
    text = _auth()

    for needle in [
        "fixed_artifact_acceptance_rerun_authorized=False",
        "training_split_manifest_ready_for_preflight=False",
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
        "fixed_artifact_acceptance_rerun_authorized=True",
        "camp_training_authorized=True",
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in text


def test_remediation_authorization_next_gate_is_implementation_only() -> None:
    text = _auth()

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_legacy_decision_flag_remediation_authorized",
        "passed=True",
        "legacy_decision_flag_remediation_implementation_authorized=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_legacy_decision_flag_remediation_implementation_only",
        "may only implement this minimal compatibility remediation",
        "must not rerun fixed-artifact acceptance",
        "train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
    ]:
        assert needle in text
