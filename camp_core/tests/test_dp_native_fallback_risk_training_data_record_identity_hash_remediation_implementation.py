from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
IMPL_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_record_identity_hash_remediation_implementation.md"
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
BUILDER_TEST = (
    REPO_ROOT
    / "camp_core"
    / "tests"
    / "test_dp_native_fallback_risk_training_data_default_off_builder.py"
)
VALIDATOR_TEST = (
    REPO_ROOT
    / "camp_core"
    / "tests"
    / "test_dp_native_fallback_risk_training_data_validator_extension.py"
)
REFERENCE_CONTRACT_TEST = (
    REPO_ROOT
    / "camp_core"
    / "tests"
    / "test_dp_native_fallback_risk_training_data_validator_extension_contract.py"
)


def _doc() -> str:
    return IMPL_DOC.read_text(encoding="utf-8")


def test_implementation_doc_records_scope_and_changed_artifacts() -> None:
    text = _doc()

    for needle in [
        "implementation_start_head=e910585d310cbd2610afaa01a2a9dda040e35304",
        "training_data_builder=scripts/integrations/build_diffusion_planner_dp_native_fallback_risk_training_data.py",
        "training_data_validator=scripts/integrations/validate_dp_native_fallback_risk_training_data_contract.py",
        "builder_unit_test=camp_core/tests/test_dp_native_fallback_risk_training_data_default_off_builder.py",
        "validator_unit_test=camp_core/tests/test_dp_native_fallback_risk_training_data_validator_extension.py",
        "validator_reference_contract_test=camp_core/tests/test_dp_native_fallback_risk_training_data_validator_extension_contract.py",
    ]:
        assert needle in text


def test_builder_emits_record_identity_hash_with_split_manifest_formula() -> None:
    text = _doc()
    builder = TRAINING_DATA_BUILDER.read_text(encoding="utf-8")
    builder_test = BUILDER_TEST.read_text(encoding="utf-8")

    for needle in [
        "builder_emits_record_identity_hash=True",
        "record_identity_hash_formula_matches_split_manifest_builder=True",
        "record_identity_hash_inputs=source_log,source_log_sha256,run_id,record_index",
    ]:
        assert needle in text

    for needle in [
        '"record_identity_hash": _record_identity_hash(',
        "def _record_identity_hash(",
        'json.dumps(identity, sort_keys=True, separators=(",", ":"))',
    ]:
        assert needle in builder

    assert 'built["record_identity_hash"] == _record_identity_hash(built)' in builder_test


def test_validator_requires_and_recomputes_record_identity_hash() -> None:
    text = _doc()
    validator = TRAINING_DATA_VALIDATOR.read_text(encoding="utf-8")
    validator_test = VALIDATOR_TEST.read_text(encoding="utf-8")
    reference_test = REFERENCE_CONTRACT_TEST.read_text(encoding="utf-8")

    for needle in [
        "validator_requires_record_identity_hash=True",
        "validator_recomputes_record_identity_hash=True",
        "validator_rejects_missing_record_identity_hash=True",
        "validator_rejects_invalid_record_identity_hash=True",
        "validator_rejects_mismatched_record_identity_hash=True",
    ]:
        assert needle in text

    for needle in [
        "record_identity_hash_missing",
        "record_identity_hash_invalid",
        "record_identity_hash_mismatch",
        "def _record_identity_hash(record: dict[str, Any]) -> str:",
    ]:
        assert needle in validator

    assert "test_validator_rejects_missing_or_mismatched_record_identity_hash" in validator_test
    assert "test_reference_contract_rejects_missing_or_mismatched_record_identity_hash" in reference_test
    for needle in [
        "record_identity_hash_missing",
        "record_identity_hash_mismatch",
    ]:
        assert needle in validator_test
        assert needle in reference_test


def test_implementation_keeps_training_dp_and_artifact_rebuild_forbidden() -> None:
    text = _doc()

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


def test_implementation_decision_and_next_gate_are_static_contract_only() -> None:
    text = _doc()

    for needle in [
        "status=fallback_risk_training_data_record_identity_hash_remediation_implemented",
        "passed=True",
        "implementation_complete=True",
        "record_identity_hash_remediation_implemented=True",
        "local_implementation_target_pytest=48 passed",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_record_identity_hash_remediation_post_implementation_static_contract_only",
        "may only perform a post-implementation static contract review",
        "must not rebuild fixed artifacts",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_record_identity_implementation_next_gate() -> None:
    tail = "\n".join(ITERATION_AUDIT.read_text(encoding="utf-8").splitlines()[-160:])

    for needle in [
        "status=fallback_risk_training_data_record_identity_hash_remediation_implemented",
        "record_identity_hash_remediation_implemented=True",
        "local_implementation_target_pytest=48 passed",
        "fixed_artifact_rebuild_authorized_now=False",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in tail

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_record_identity_hash_remediation_post_implementation_static_contract_only`"
    )
