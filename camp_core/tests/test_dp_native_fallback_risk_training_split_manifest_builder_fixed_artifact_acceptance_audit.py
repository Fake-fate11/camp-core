from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_audit.md"
)


def _audit() -> str:
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_acceptance_audit_records_fixed_artifact_inputs_and_outputs() -> None:
    text = _audit()

    for needle in [
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f632c44_20260624T133402Z/dataset.json",
        "expected_dataset_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "validator_output_json_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "builder_commit=f00a2d4e3bf7576ad8f6ecd79dad1e3d09255c10",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_f00a2d4_20260624T153229Z",
        "split_manifest_json_sha256=141b1213ac5c0ca7bf701bcc01d03d7245e23801af830613e48ef07bdd948ae2",
        "split_manifest_md_sha256=3bd8c173c0745673aa6f3a6ce3a39524631450b9535c1904d919b38cbe5c82f9",
    ]:
        assert needle in text


def test_acceptance_audit_records_rejection_and_single_error() -> None:
    text = _audit()

    for needle in [
        "schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "status=dp_native_fallback_risk_training_split_manifest_builder_rejected",
        "passed=False",
        "errors=['final_decision_fallback_risk_training_authorized_now_not_false']",
        "accepted_records=0",
        "training_records=0",
        "validation_records=0",
        "training_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
    ]:
        assert needle in text


def test_acceptance_audit_identifies_legacy_flag_compatibility_issue() -> None:
    text = _audit()

    for needle in [
        "fixed_artifact_acceptance_passed=False",
        "blocking_acceptance_findings=1",
        "legacy_final_decision_flag_compatibility_issue=True",
        "missing_flag=fallback_risk_training_authorized_now",
        "dataset_sha256_matched=True",
        "validator_output_sha256_recorded=True",
        "builder_failed_closed=True",
        "manifest_accepted_for_preflight=False",
        "This is a compatibility rejection",
        "local_target_pytest=5 passed",
        "local_fallback_risk_related_pytest=224 passed",
    ]:
        assert needle in text


def test_acceptance_audit_keeps_training_dp_and_claims_forbidden() -> None:
    text = _audit()

    for needle in [
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_dataset_training_sufficiency_claim=False",
    ]:
        assert needle in text

    for forbidden in [
        "candidate_generation_authorized=True",
        "camp_training_authorized=True",
        "dp_modification_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in text


def test_acceptance_audit_next_gate_is_remediation_authorization_only() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_rejected_legacy_decision_flag",
        "fixed_artifact_acceptance_audit_complete=True",
        "training_split_manifest_ready_for_preflight=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_legacy_decision_flag_remediation_authorization_only",
        "may only decide whether to authorize a minimal compatibility",
        "must not run",
        "replay",
        "generate candidates",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text
