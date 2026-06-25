from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _audit() -> str:
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_acceptance_rerun_records_inputs_and_outputs() -> None:
    text = _audit()

    for needle in [
        "current_head_fixed_artifact_acceptance_rerun_passed=True",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_6adb800_20260625T020016Z/dataset.json",
        "expected_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_b10a5b6_20260625T040200Z/split_manifest.json",
        "expected_split_manifest_sha256=b6f8cdcc0e353e1efdc81c62d0e81aa1f4b0679270f1bb211879ac03adce8079",
        "train_only_scale_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_acceptance_015058d_20260625T041048Z/scale_manifest.json",
        "expected_scale_manifest_sha256=5ad58c9fee35d8e21922385993edb28d4934b8066a2cf683af28f12384a976cf",
        "source_scale_manifest_acceptance_status=fallback_risk_training_train_only_scale_manifest_current_head_fixed_artifact_acceptance_passed",
        "builder_commit=113d9592ff50134ed11a73e241d57e0aefcd1d83",
        "autodl_CAMP_HEAD=113d9592ff50134ed11a73e241d57e0aefcd1d83",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_113d959_20260625T042600Z",
        "fallback_master_config_json_sha256=6dbd94ea34e8374ac616817d64d6f93baa0d9da4828e3af6c32474a91cf3a7f3",
        "training_command_plan_json_sha256=f5128aca1566783ef02a464970f2e1623abf9f69d2d724cae2d6995176c89e82",
        "master_command_md_sha256=a14244b6719d8d5942c9cfa2c9d763a9d4967fa5967b622dfc176757072f232e",
        "builder_stdout_log_sha256=194b56ed5ebb16374b8f48e02b6194912f3b9b3261b86cd86bdd83c33f52a405",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
    ]:
        assert needle in text


def test_acceptance_rerun_records_master_and_command_contract() -> None:
    text = _audit()

    for needle in [
        "status=dp_native_fallback_risk_training_fallback_master_config_and_command_plan_builder_complete",
        "passed=True",
        "master_config_output_written=True",
        "training_command_plan_output_written=True",
        "master_schema_version=dp_native_fallback_risk_fallback_master_config_v1",
        "training_command_schema_version=dp_native_fallback_risk_training_command_plan_v1",
        "fallback_only=True",
        "score_expression=score_k(w)=a_k^T w",
        "atoms_fixed_nonnegative=True",
        "simplex_cvar_l2_convex=True",
        "training_command_authorization=False",
        "training_execution_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "post_training_nonpromotion_plan_required=True",
        "development_holdout_acceptance_gate_required=True",
        "errors=[]",
    ]:
        assert needle in text


def test_acceptance_rerun_marks_master_and_command_ready_but_not_training_authorized() -> None:
    text = _audit()

    for needle in [
        "fixed_artifact_acceptance_rerun_passed=True",
        "blocking_acceptance_findings=0",
        "fallback_master_config_ready=True",
        "latest_fallback_master_config_ready=True",
        "training_command_plan_ready=True",
        "latest_training_command_plan_ready=True",
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
        "training_execution_authorized=False",
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
        "local_target_pytest=123 passed",
        "local_master_command_acceptance_pytest=6 passed",
        "local_master_command_builder_pytest=6 passed",
        "local_related_target_pytest=111 passed",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=123 passed",
        "autodl_master_command_acceptance_pytest=6 passed",
        "autodl_master_command_builder_pytest=6 passed",
        "autodl_git_diff_check_exit=0",
        "status=fallback_risk_training_fallback_master_config_and_command_plan_current_head_fixed_artifact_acceptance_passed",
        "fixed_artifact_acceptance_rerun_complete=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_validated_dataset_summary_materializer_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only",
        "may only rerun the default-off validated dataset summary",
        "must not execute training",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_master_command_rerun_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-190:])

    for needle in [
        "status=fallback_risk_training_validated_dataset_summary_materializer_current_head_fixed_artifact_acceptance_passed",
        "source_master_command_acceptance_status=fallback_risk_training_fallback_master_config_and_command_plan_current_head_fixed_artifact_acceptance_passed",
        "validated_dataset_summary_json_sha256=e5dc69273795be41f1d48ea702a55fac63733d462c030c1595e42ef4d5d78c5f",
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
