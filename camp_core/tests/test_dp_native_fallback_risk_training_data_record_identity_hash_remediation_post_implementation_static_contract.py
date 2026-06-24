from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_record_identity_hash_remediation_post_implementation_static_contract_review.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
TRAINING_DATA_BUILDER = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "build_diffusion_planner_dp_native_fallback_risk_training_data.py"
)
TRAINING_DATA_VALIDATOR = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "validate_dp_native_fallback_risk_training_data_contract.py"
)


def _review() -> str:
    return REVIEW_DOC.read_text(encoding="utf-8")


def test_post_static_review_records_artifacts_and_contract_status() -> None:
    text = _review()

    for needle in [
        "implementation_status=fallback_risk_training_data_record_identity_hash_remediation_implemented",
        "training_data_builder=scripts/integrations/build_diffusion_planner_dp_native_fallback_risk_training_data.py",
        "training_data_validator=scripts/integrations/validate_dp_native_fallback_risk_training_data_contract.py",
        "builder_unit_test=camp_core/tests/test_dp_native_fallback_risk_training_data_default_off_builder.py",
        "validator_unit_test=camp_core/tests/test_dp_native_fallback_risk_training_data_validator_extension.py",
    ]:
        assert needle in text


def test_post_static_review_matches_builder_and_validator_code() -> None:
    text = _review()
    builder = TRAINING_DATA_BUILDER.read_text(encoding="utf-8")
    validator = TRAINING_DATA_VALIDATOR.read_text(encoding="utf-8")

    for needle in [
        "builder_emits_record_identity_hash=True",
        "builder_hash_formula_matches_split_manifest_builder=True",
        "validator_requires_record_identity_hash=True",
        "validator_recomputes_record_identity_hash=True",
        "validator_rejects_missing_record_identity_hash=True",
        "validator_rejects_invalid_record_identity_hash=True",
        "validator_rejects_mismatched_record_identity_hash=True",
        "default_off_boundaries_preserved=True",
    ]:
        assert needle in text

    assert '"record_identity_hash": _record_identity_hash(' in builder
    assert "record_identity_hash_missing" in validator
    assert "record_identity_hash_invalid" in validator
    assert "record_identity_hash_mismatch" in validator


def test_post_static_review_records_local_verification() -> None:
    text = _review()

    for needle in [
        "local_py_compile_exit=0",
        "local_post_static_target_pytest=6 passed",
        "local_related_target_pytest=54 passed",
        "autodl_verified_camp_head=fdbbdc622c349b452747491eaf685cd008e1e11e",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=54 passed",
        "autodl_git_diff_check_exit=0",
    ]:
        assert needle in text


def test_post_static_review_keeps_forbidden_boundaries() -> None:
    text = _review()

    for needle in [
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "training_execution_authorized_now=False",
        "fixed_artifact_rebuild_authorized_now=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text


def test_post_static_review_decision_and_next_gate() -> None:
    text = _review()

    for needle in [
        "status=fallback_risk_training_data_record_identity_hash_remediation_post_implementation_static_contract_passed",
        "passed=True",
        "static_contract_review_complete=True",
        "blocking_contract_findings=0",
        "record_identity_hash_remediation_implemented=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only",
        "may only rerun the default-off fixed-artifact acceptance audit",
        "must not run replay",
        "generate new candidates",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_post_static_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-180:])

    for needle in [
        "status=fallback_risk_training_data_record_identity_hash_remediation_post_implementation_static_contract_passed",
        "static_contract_review_complete=True",
        "local_post_static_target_pytest=6 passed",
        "local_related_target_pytest=54 passed",
        "autodl_target_pytest=54 passed",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in audit

    assert (
        "status=fallback_risk_training_fallback_master_config_and_command_plan_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_passed"
        in tail
    )

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only`"
    )
