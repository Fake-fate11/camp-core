from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _audit() -> str:
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_acceptance_rerun_records_fixed_inputs_and_outputs() -> None:
    text = _audit()

    for needle in [
        "source_artifact_root=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_broader_nonformal_eval_1c235eb_20260624T092550Z",
        "selection_logs=12",
        "formal_seed_path_matches=0",
        "selection_log_seed_set=109,110",
        "builder_commit=7ef98c9f2db624eac3d220882ce1c9a4b8161ea2",
        "autodl_CAMP_HEAD=7ef98c9f2db624eac3d220882ce1c9a4b8161ea2",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "post_static_contract_status=fallback_risk_training_data_record_identity_hash_remediation_post_implementation_static_contract_passed",
        "output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_record_identity_acceptance_7ef98c9_20260624T215739Z",
        "dataset_json_sha256=8e7d42e2d1319dc2a479903d7b1be5a463f2d74fe733b523fdbac09bf90bd9b9",
        "validation_json_sha256=c5eb4c618476342efee3d3c4f64fd8c2aba918e22d209c004aea7e256a83e073",
        "builder_exit=0",
        "validator_exit=0",
    ]:
        assert needle in text


def test_acceptance_rerun_records_builder_and_validator_success() -> None:
    text = _audit()

    for needle in [
        "builder_status=dp_native_fallback_risk_training_data_builder_complete",
        "builder_passed=True",
        "records_total=60",
        "records_with_feasible_candidate=45",
        "records_without_feasible_candidate=15",
        "records_built=15",
        "failed_records=0",
        "records_with_identity_hash=15",
        "records_total_with_identity_check=15",
        "unique_source_logs_for_built_records=7",
        "validator_status=dp_native_fallback_risk_training_data_validator_complete",
        "validator_passed=True",
        "validator_records_checked=15",
        "validator_failed_records=0",
        "source_log_readback_enabled=True",
    ]:
        assert needle in text


def test_acceptance_rerun_accepts_record_identity_remediation_but_not_training() -> None:
    text = _audit()

    for needle in [
        "fixed_artifact_acceptance_rerun_passed=True",
        "blocking_acceptance_findings=0",
        "record_identity_hash_remediation_accepted=True",
        "all_records_with_record_identity_hash=True",
        "validator_recomputed_record_identity_hashes=True",
        "training_data_fixed_artifact_ready_for_split_manifest_rerun=True",
        "training_split_manifest_ready_for_preflight=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "fallback_dataset_training_sufficiency_claim=False",
    ]:
        assert needle in text


def test_acceptance_rerun_keeps_training_dp_and_claims_forbidden() -> None:
    text = _audit()

    for needle in [
        "user_camp_retraining_permission_available=True",
        "training_execution_authorized_now=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

    for forbidden in [
        "candidate_generation_authorized=True",
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "dp_modification_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in text


def test_acceptance_rerun_records_local_verification_and_next_gate() -> None:
    text = _audit()

    for needle in [
        "local_py_compile_exit=0",
        "local_target_pytest=6 passed",
        "local_related_target_pytest=60 passed",
        "autodl_verified_camp_head=bffccd55874d9c69f0da79ee90b8c3acbc4aeba8",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=60 passed",
        "autodl_git_diff_check_exit=0",
        "status=fallback_risk_training_data_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_passed",
        "fixed_artifact_acceptance_rerun_complete=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only",
        "may only rerun the default-off split manifest builder",
        "must not run replay",
        "generate candidates",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_acceptance_rerun_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-190:])

    for needle in [
        "status=fallback_risk_training_data_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_passed",
        "record_identity_hash_remediation_accepted=True",
        "records_with_identity_hash=15",
        "training_data_fixed_artifact_ready_for_split_manifest_rerun=True",
        "training_split_manifest_ready_for_preflight=False",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in audit

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_record_identity_hash_remediation_implemented",
        "old_expected_validated_dataset_sha_rejected=True",
        "new_expected_validated_dataset_sha_accepted_by_unit_contract=True",
    ]:
        assert needle in tail

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fixed_artifact_fallback_risk_ranking_audit_only`"
    )
