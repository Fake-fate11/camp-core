from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _audit() -> str:
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_acceptance_rerun_records_remediated_inputs_and_outputs() -> None:
    text = _audit()

    for needle in [
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_record_identity_acceptance_7ef98c9_20260624T215739Z/dataset.json",
        "expected_dataset_sha256=8e7d42e2d1319dc2a479903d7b1be5a463f2d74fe733b523fdbac09bf90bd9b9",
        "validator_output_json_sha256=c5eb4c618476342efee3d3c4f64fd8c2aba918e22d209c004aea7e256a83e073",
        "source_data_acceptance_status=fallback_risk_training_data_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_passed",
        "builder_commit=7891f2eaf1d80a22f283ae43f05323260e8238da",
        "autodl_CAMP_HEAD=7891f2eaf1d80a22f283ae43f05323260e8238da",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_record_identity_acceptance_7891f2e_20260624T220443Z",
        "split_manifest_json_sha256=9eb6f64a392a8ba1c6037c9dc8389ad9459615c039ad2b3426747785b75e5a78",
        "split_manifest_md_sha256=60ef091344704d9edeec48820d2d1888cb0110ba6b9a35e6de6ad49ee9fe2aeb",
        "builder_exit=0",
    ]:
        assert needle in text


def test_acceptance_rerun_records_complete_split_manifest_result() -> None:
    text = _audit()

    for needle in [
        "schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "split_policy=sha256(record_identity_hash + split_salt)",
        "split_salt=fallback_risk_training_split_v1",
        "status=dp_native_fallback_risk_training_split_manifest_builder_complete",
        "passed=True",
        "ready_for_future_preflight=True",
        "accepted_records=15",
        "training_records=13",
        "validation_records=2",
        "training_groups=13",
        "validation_groups=2",
        "training_groups_disjoint_validation=True",
        "record_assignments=15",
        "formal_eval_artifact_included=False",
        "errors=[]",
    ]:
        assert needle in text


def test_acceptance_rerun_marks_preflight_ready_but_not_training_authorized() -> None:
    text = _audit()

    for needle in [
        "fixed_artifact_acceptance_rerun_passed=True",
        "blocking_acceptance_findings=0",
        "record_identity_hash_remediated_dataset_accepted_by_split_manifest=True",
        "training_split_manifest_ready_for_preflight=True",
        "train_only_scale_manifest_ready_for_preflight=False",
        "validated_dataset_summary_ready_for_preflight=False",
        "fallback_master_config_ready=False",
        "training_command_plan_ready=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "fixed_15_record_artifact_training_sufficiency_claim=False",
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
        "local_related_target_pytest=66 passed",
        "autodl_verified_camp_head=51630aad81da6cd5defa69ebb0b75b3db482e1aa",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=66 passed",
        "autodl_git_diff_check_exit=0",
        "status=fallback_risk_training_split_manifest_builder_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_passed",
        "fixed_artifact_acceptance_rerun_complete=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only",
        "may only rerun the default-off train-only scale manifest builder",
        "must not train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_split_manifest_rerun_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-190:])

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_passed",
        "training_split_manifest_ready_for_preflight=True",
        "train_only_scale_manifest_ready_for_preflight=False",
        "fallback_risk_training_authorized_now=False",
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
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only`"
    )
