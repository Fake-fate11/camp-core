from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_validated_dataset_summary_materializer_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _audit() -> str:
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_acceptance_rerun_records_inputs_and_outputs() -> None:
    text = _audit()

    for needle in [
        "current_head_fixed_artifact_acceptance_rerun_passed=True",
        "stale_validator_output_rejected=True",
        "stale_validator_reject_error=validator_dataset_sha256_mismatch",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_6adb800_20260625T020016Z/dataset.json",
        "expected_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "source_validator_output_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_validator_acceptance_4aeb061_20260625T022753Z/validation.json",
        "expected_validator_output_sha256=039b3e41f866434e187a9f679cbc964d6fe35d5406896e53ec38d8f70db40c52",
        "source_dataset_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_rerun_passed",
        "builder_commit=18b8a7bef7239820395e92a4ac720c85bab8ceb8",
        "autodl_CAMP_HEAD=18b8a7bef7239820395e92a4ac720c85bab8ceb8",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_acceptance_18b8a7b_20260625T044200Z",
        "validated_dataset_summary_json_sha256=e5dc69273795be41f1d48ea702a55fac63733d462c030c1595e42ef4d5d78c5f",
        "validated_dataset_summary_md_sha256=e1c75b4c6bc0b9626f44fd1cbdee29be8418d4660b8acf7e0430bbc7b0a05426",
        "builder_stdout_log_sha256=f2a064276a2ddbcdac2da735e639be85f5c8b5fe153b62461f3b46c8388a0abe",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
    ]:
        assert needle in text


def test_acceptance_rerun_records_complete_materializer_result() -> None:
    text = _audit()

    for needle in [
        "status=dp_native_fallback_risk_validated_dataset_summary_materializer_complete",
        "passed=True",
        "enabled=True",
        "errors=[]",
        "summary_output_written=True",
        "training_sufficiency_preflight_executed=False",
        "training_sufficiency_preflight_execution_authorized=False",
        "training_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
    ]:
        assert needle in text


def test_acceptance_rerun_records_summary_shape_and_readiness() -> None:
    text = _audit()

    for needle in [
        "summary_schema_version=dp_native_fallback_risk_validated_dataset_summary_v1",
        "summary_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "summary_records=15",
        "summary_validator_status=dp_native_fallback_risk_training_data_validator_complete",
        "summary_validator_passed=True",
        "summary_training_sufficiency_claim=False",
        "summary_deployable_checkpoint_claim=False",
        "summary_source_validator_output_sha256=039b3e41f866434e187a9f679cbc964d6fe35d5406896e53ec38d8f70db40c52",
        "fixed_artifact_acceptance_rerun_passed=True",
        "validated_dataset_summary_ready_for_preflight=True",
        "latest_validated_dataset_summary_ready_for_preflight=True",
        "training_sufficiency_preflight_input_set_ready=True",
        "training_sufficiency_preflight_ready=False",
        "fixed_15_record_artifact_training_sufficiency_claim=False",
    ]:
        assert needle in text


def test_acceptance_rerun_keeps_training_dp_and_claims_forbidden() -> None:
    text = _audit()

    for needle in [
        "user_camp_retraining_permission_available=True",
        "training_execution_authorized_now=False",
        "training_execution_authorized=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
    ]:
        assert needle in text

    for forbidden in [
        "training_execution_authorized_now=True",
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


def test_acceptance_rerun_records_verification_and_next_gate() -> None:
    text = _audit()

    for needle in [
        "local_py_compile_exit=0",
        "local_target_pytest=134 passed",
        "local_summary_acceptance_pytest=6 passed",
        "local_summary_materializer_pytest=5 passed",
        "local_related_target_pytest=123 passed",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=134 passed",
        "autodl_summary_acceptance_pytest=6 passed",
        "autodl_summary_materializer_pytest=5 passed",
        "autodl_git_diff_check_exit=0",
        "status=fallback_risk_training_validated_dataset_summary_materializer_current_head_fixed_artifact_acceptance_passed",
        "fixed_artifact_acceptance_rerun_complete=True",
        "blocking_acceptance_findings=0",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only",
        "may only run the already implemented default-off read-only",
        "User permission to retrain CAMP is available",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_summary_rerun_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-190:])

    for needle in [
        "status=fallback_risk_training_validated_dataset_summary_materializer_current_head_fixed_artifact_acceptance_passed",
        "stale_validator_output_rejected=True",
        "summary_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "summary_source_validator_output_sha256=039b3e41f866434e187a9f679cbc964d6fe35d5406896e53ec38d8f70db40c52",
        "latest_validated_dataset_summary_ready_for_preflight=True",
        "local_target_pytest=134 passed",
        "autodl_target_pytest=134 passed",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in tail

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only`"
    )
