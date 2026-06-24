from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _audit() -> str:
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_acceptance_rerun_records_inputs_and_outputs() -> None:
    text = _audit()

    for needle in [
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_record_identity_acceptance_7ef98c9_20260624T215739Z/dataset.json",
        "expected_dataset_sha256=8e7d42e2d1319dc2a479903d7b1be5a463f2d74fe733b523fdbac09bf90bd9b9",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_record_identity_acceptance_7891f2e_20260624T220443Z/split_manifest.json",
        "expected_split_manifest_sha256=9eb6f64a392a8ba1c6037c9dc8389ad9459615c039ad2b3426747785b75e5a78",
        "validator_output_json_sha256=c5eb4c618476342efee3d3c4f64fd8c2aba918e22d209c004aea7e256a83e073",
        "source_split_manifest_acceptance_status=fallback_risk_training_split_manifest_builder_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_passed",
        "builder_commit=201c872762a10786e0d14e406ea29ef603ce9a37",
        "autodl_CAMP_HEAD=201c872762a10786e0d14e406ea29ef603ce9a37",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_record_identity_acceptance_201c872_20260624T221156Z",
        "scale_manifest_json_sha256=d4205878c3af549ed86a778236500997df302272ab671bfcb60bc5f18b03b812",
        "scale_manifest_md_sha256=bafe15c581eb48e8a02908989f38a97cf1fa11db1a120e18c440338e76479ac7",
        "builder_exit=0",
    ]:
        assert needle in text


def test_acceptance_rerun_records_train_only_scale_result() -> None:
    text = _audit()

    for needle in [
        "schema_version=dp_native_fallback_risk_training_train_only_scale_manifest_v1",
        "status=dp_native_fallback_risk_training_train_only_scale_manifest_builder_complete",
        "passed=True",
        "scale_policy=train_only_positive_finite_p95_or_one_v1",
        "fit_scope=split_manifest_training_groups_only",
        "validation_groups_excluded=True",
        "atom_schema_version=dp_camp_v10_14d",
        "atom_count=14",
        "fit_records_used=13",
        "training_records_seen=13",
        "validation_records_seen=2",
        "fit_groups=13",
        "excluded_validation_groups=2",
        "fit_seeds=[]",
        "formal_eval_artifact_included=False",
        "errors=[]",
    ]:
        assert needle in text


def test_acceptance_rerun_marks_scale_ready_but_not_training_authorized() -> None:
    text = _audit()

    for needle in [
        "fixed_artifact_acceptance_rerun_passed=True",
        "blocking_acceptance_findings=0",
        "train_only_scale_manifest_ready_for_preflight=True",
        "fallback_master_config_ready=False",
        "training_command_plan_ready=False",
        "validated_dataset_summary_ready_for_preflight=False",
        "training_sufficiency_preflight_ready=False",
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


def test_acceptance_rerun_records_local_verification_and_next_gate() -> None:
    text = _audit()

    for needle in [
        "local_py_compile_exit=0",
        "local_target_pytest=6 passed",
        "local_scale_builder_pytest=5 passed",
        "local_related_target_pytest=77 passed",
        "autodl_verification_pending=True",
        "status=fallback_risk_training_train_only_scale_manifest_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_passed",
        "fixed_artifact_acceptance_rerun_complete=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only",
        "may only rerun the default-off fallback master config",
        "must not execute training",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_scale_rerun_next_gate() -> None:
    tail = "\n".join(ITERATION_AUDIT.read_text(encoding="utf-8").splitlines()[-190:])

    for needle in [
        "status=fallback_risk_training_train_only_scale_manifest_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_passed",
        "train_only_scale_manifest_ready_for_preflight=True",
        "fallback_master_config_ready=False",
        "training_command_plan_ready=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in tail

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only`"
    )
