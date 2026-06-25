from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_audit.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _audit() -> str:
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_acceptance_audit_records_current_fixed_artifact_inputs_and_outputs() -> None:
    text = _audit()

    for needle in [
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f632c44_20260624T133402Z/dataset.json",
        "expected_dataset_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "validator_output_json_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "builder_commit=cdeef56a6502504aded815866d2a95d248fe2cc6",
        "autodl_CAMP_HEAD=cdeef56a6502504aded815866d2a95d248fe2cc6",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "record_identity_hash_required_input_field=True",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_cdeef56_20260624T212247Z",
        "split_manifest_json_sha256=35fc5a3d3f648177c9da0db24f6c9205ad9bfa0ecbe4fcd3dc5008d12e27f8c3",
        "split_manifest_md_sha256=3bd8c173c0745673aa6f3a6ce3a39524631450b9535c1904d919b38cbe5c82f9",
        "builder_exit=1",
        "latest_source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_6adb800_20260625T020016Z/dataset.json",
        "latest_expected_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "latest_validator_output_json_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "latest_builder_commit=b10a5b6fca6aa82b70dfe0710e295ea9ed445457",
        "latest_autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_b10a5b6_20260625T040200Z",
        "latest_split_manifest_json_sha256=b6f8cdcc0e353e1efdc81c62d0e81aa1f4b0679270f1bb211879ac03adce8079",
        "latest_split_manifest_md_sha256=60ef091344704d9edeec48820d2d1888cb0110ba6b9a35e6de6ad49ee9fe2aeb",
        "latest_builder_exit=0",
    ]:
        assert needle in text


def test_acceptance_audit_records_missing_record_identity_rejection() -> None:
    text = _audit()

    for needle in [
        "schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "split_policy=sha256(record_identity_hash + split_salt)",
        "status=dp_native_fallback_risk_training_split_manifest_builder_rejected",
        "passed=False",
        "errors_count=15",
        "errors_all_record_identity_hash_missing=True",
        "first_error=record_0:record_identity_hash_missing",
        "last_error=record_9:record_identity_hash_missing",
        "accepted_records=0",
        "training_records=0",
        "validation_records=0",
        "record_assignments=0",
        "split_manifest_written=False",
        "ready_for_future_preflight=False",
        "latest_schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "latest_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "latest_validator_output_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "latest_status=dp_native_fallback_risk_training_split_manifest_builder_complete",
        "latest_passed=True",
        "latest_errors=[]",
        "latest_accepted_records=15",
        "latest_training_records=13",
        "latest_validation_records=2",
        "latest_record_assignments=15",
        "latest_training_authorized=False",
        "latest_fallback_dataset_training_sufficiency_claim=False",
        "latest_candidate_generation_authorized=False",
        "latest_dp_modification_authorized=False",
    ]:
        assert needle in text


def test_acceptance_audit_identifies_upstream_record_identity_remediation() -> None:
    text = _audit()

    for needle in [
        "fixed_artifact_acceptance_passed=False",
        "blocking_acceptance_findings=1",
        "legacy_final_decision_flag_compatibility_issue=False",
        "record_identity_hash_compatibility_issue=True",
        "source_training_dataset_missing_record_identity_hash=True",
        "missing_record_identity_hash_records=15",
        "dataset_sha256_matched=True",
        "builder_failed_closed=True",
        "identity_hardening_effective=True",
        "manifest_accepted_for_preflight=False",
        "training_split_manifest_ready_for_preflight=False",
        "upstream_training_data_record_identity_remediation_required=True",
        "local_target_pytest=6 passed",
        "local_related_target_pytest=22 passed",
        "autodl_verified_camp_head=22ccb10bbd8aeaf94e7c62c1a83c16ce4f633524",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=22 passed",
        "autodl_git_diff_check_exit=0",
        "latest_fixed_artifact_acceptance_passed=True",
        "latest_blocking_acceptance_findings=0",
        "latest_record_identity_hash_compatibility_issue=False",
        "latest_missing_record_identity_hash_records=0",
        "latest_manifest_accepted_for_preflight=True",
        "latest_training_split_manifest_ready_for_preflight=True",
        "latest_fixed_15_record_artifact_training_sufficiency_claim=False",
        "latest_fallback_risk_training_authorized_now=False",
        "latest_camp_retraining_authorized_now=False",
        "latest_fallback_dataset_training_sufficiency_claim=False",
        "latest_autodl_builder_exit=0",
        "latest_autodl_output_json_sha256=b6f8cdcc0e353e1efdc81c62d0e81aa1f4b0679270f1bb211879ac03adce8079",
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


def test_acceptance_audit_next_gate_is_record_identity_authorization_only() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_rejected_missing_record_identity_hash",
        "latest_status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_current_head_passed",
        "fixed_artifact_acceptance_audit_complete=True",
        "latest_fixed_artifact_acceptance_audit_complete=True",
        "training_split_manifest_ready_for_preflight=False",
        "latest_training_split_manifest_ready_for_preflight=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_record_identity_hash_remediation_authorization_only",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only",
        "may only decide whether to authorize a minimal default-off",
        "must not run",
        "replay",
        "generate candidates",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_current_acceptance_audit_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-190:])

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_current_head_fixed_artifact_acceptance_passed",
        "ready_for_future_training_authorization=True",
        "local_target_pytest=140 passed",
        "local_preflight_acceptance_rerun_pytest=6 passed",
        "local_preflight_pytest=5 passed",
        "autodl_target_pytest=140 passed",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in tail

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_command_authorization_only`"
    )
