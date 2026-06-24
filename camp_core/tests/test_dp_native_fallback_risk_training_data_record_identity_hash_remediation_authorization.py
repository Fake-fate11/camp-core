from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_record_identity_hash_remediation_authorization.md"
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
SPLIT_MANIFEST_BUILDER = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "build_diffusion_planner_dp_native_fallback_risk_training_split_manifest.py"
)


def _auth() -> str:
    return AUTH_DOC.read_text(encoding="utf-8")


def test_authorization_records_acceptance_failure_and_current_heads() -> None:
    text = _auth()

    for needle in [
        "current_camp_head=4f950ed8403274623963310de93b8c848ef75494",
        "github_refs_heads_main=4f950ed8403274623963310de93b8c848ef75494",
        "autodl_CAMP_HEAD=4f950ed8403274623963310de93b8c848ef75494",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "acceptance_status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_rejected_missing_record_identity_hash",
        "current_fixed_dataset_records_missing_record_identity_hash=15",
        "training_split_manifest_ready_for_preflight=False",
    ]:
        assert needle in text


def test_authorization_is_grounded_in_current_static_contract_gap() -> None:
    text = _auth()
    data_builder = TRAINING_DATA_BUILDER.read_text(encoding="utf-8")
    validator = TRAINING_DATA_VALIDATOR.read_text(encoding="utf-8")
    split_builder = SPLIT_MANIFEST_BUILDER.read_text(encoding="utf-8")

    for needle in [
        "split_manifest_builder_requires_record_identity_hash=True",
        "split_manifest_builder_hash_formula=sha256(json({source_log,source_log_sha256,run_id,record_index}))",
        "split_manifest_builder_missing_record_identity_hash_fails_closed=True",
        "training_data_builder_currently_omits_record_identity_hash=True",
        "training_data_validator_currently_does_not_require_record_identity_hash=True",
    ]:
        assert needle in text

    assert '"record_identity_hash",' in split_builder
    assert "def _record_identity_hash(record: dict[str, Any]) -> str:" in split_builder
    assert '"record_identity_hash": _record_identity_hash(' in data_builder
    assert "def _record_identity_hash(record: dict[str, Any]) -> str:" in validator


def test_authorization_allows_only_minimal_builder_and_validator_remediation() -> None:
    text = _auth()

    for needle in [
        "record_identity_hash_remediation_authorized=True",
        "implementation_scope=training_data_builder_and_training_data_validator_only",
        "record_identity_hash_required_on_every_built_record=True",
        "record_identity_hash_formula_must_match_split_manifest_builder=True",
        "record_identity_hash_inputs=source_log,source_log_sha256,run_id,record_index",
        "validator_must_require_record_identity_hash=True",
        "validator_must_recompute_record_identity_hash=True",
        "validator_must_fail_closed_on_missing_or_mismatch=True",
        "unit_tests_required=True",
        "post_implementation_static_contract_required=True",
        "fixed_artifact_acceptance_rerun_required=True",
    ]:
        assert needle in text


def test_authorization_records_local_verification() -> None:
    text = _auth()

    for needle in [
        "local_py_compile_exit=0",
        "local_target_pytest=7 passed",
        "local_related_target_pytest=29 passed",
        "autodl_verified_camp_head=1e10ca1402ba4e2a28c5e3e67f3b6887bde177a3",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=29 passed",
        "autodl_git_diff_check_exit=0",
    ]:
        assert needle in text


def test_authorization_keeps_training_dp_and_artifact_rebuild_forbidden_now() -> None:
    text = _auth()

    for needle in [
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "training_execution_authorized_now=False",
        "fixed_artifact_rebuild_authorized_now=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
    ]:
        assert needle in text


def test_authorization_decision_and_next_gate_are_implementation_only() -> None:
    text = _auth()

    for needle in [
        "status=fallback_risk_training_data_record_identity_hash_remediation_authorized",
        "passed=True",
        "implementation_scope_limited_to_training_data_builder_and_validator=True",
        "fixed_artifact_rebuild_authorized_now=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_record_identity_hash_remediation_implementation_only",
        "may only implement the minimal default-off",
        "must not rebuild fixed artifacts",
        "generate candidates",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_record_identity_authorization_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-180:])

    for needle in [
        "status=fallback_risk_training_data_record_identity_hash_remediation_authorized",
        "record_identity_hash_remediation_authorized=True",
        "fixed_artifact_rebuild_authorized_now=False",
        "training_execution_authorized_now=False",
        "autodl_target_pytest=29 passed",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in audit

    for needle in [
        "status=fallback_risk_training_data_record_identity_hash_remediation_implemented",
        "record_identity_hash_remediation_implemented=True",
        "fixed_artifact_rebuild_authorized_now=False",
    ]:
        assert needle in audit

    assert (
        "status=fallback_risk_training_data_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_passed"
        in tail
    )

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only`"
    )
