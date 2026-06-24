from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT / "docs" / "dp_native_training_sufficiency_preflight_artifact_audit.md"
)
VALIDATOR_SOURCE = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "validate_dp_native_training_sufficiency_preflight.py"
)


def test_preflight_artifact_audit_records_fail_closed_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=training_sufficiency_preflight_artifact_audit_passed_fail_closed",
        "validator_exit=1",
        "validator_exit_expected=True",
        "report_passed=False",
        "clean_contract_passed=True",
        "label_source_records_present=True",
        'failed_checks=["records_at_least_min", "routes_at_least_min", "seeds_at_least_min"]',
        "development_training_profile_passed=False",
        "industrial_retraining_sufficient=False",
        "training_execution_authorized=False",
        "camp_retraining_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_profile_plan_only",
    ]:
        assert needle in text

    assert "training_execution_authorized=True" not in text
    assert "camp_retraining_authorized=True" not in text
    assert "safety_benefit_claim_authorized=True" not in text
    assert "camp_over_dp_top1_claim_authorized=True" not in text


def test_preflight_validator_source_remains_read_only() -> None:
    source = VALIDATOR_SOURCE.read_text(encoding="utf-8")

    for needle in [
        "It does not run replay",
        '"read_only": True',
        '"default_off_preflight": True',
        '"replay_executed": False',
        '"candidate_generation_executed": False',
        '"training_execution_authorized": False',
        '"camp_retraining_authorized": False',
        '"deployable_checkpoint_claim_authorized": False',
    ]:
        assert needle in source
