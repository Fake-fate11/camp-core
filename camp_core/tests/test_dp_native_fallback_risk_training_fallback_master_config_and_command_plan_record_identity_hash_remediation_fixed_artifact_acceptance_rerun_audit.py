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
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_e35f1e4_20260625T132102Z/dataset.json",
        "expected_dataset_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_def7dde_20260625T160330Z/split_manifest.json",
        "expected_split_manifest_sha256=13fa6b86d2fcebbb3ecbb675daefa7409f1f427900896307474d2d1dc4f6e773",
        "train_only_scale_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_acceptance_0d49e68_20260625T161036Z/scale_manifest.json",
        "expected_scale_manifest_sha256=452828bf134fb4d5d74d8a491597ee4c50f82893622e283546ea69f2b16da934",
        "source_scale_manifest_acceptance_status=fallback_risk_training_train_only_scale_manifest_current_head_0d49e68_fixed_artifact_acceptance_passed",
        "builder_commit=f6568d852ced61319bee2739eabd327bcc14be51",
        "autodl_CAMP_HEAD=f6568d852ced61319bee2739eabd327bcc14be51",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_f6568d8_20260625T161735Z",
        "fallback_master_config_json_sha256=081a31214f18d1608a440b8826cd4cd4febaa6760284e8f01cbd0749b502e1b9",
        "training_command_plan_json_sha256=a56c86337d5576811d866a7b080a629cadb2f692a02fed7675be20e1810aec3a",
        "master_command_md_sha256=a14244b6719d8d5942c9cfa2c9d763a9d4967fa5967b622dfc176757072f232e",
        "builder_stdout_log_sha256=194b56ed5ebb16374b8f48e02b6194912f3b9b3261b86cd86bdd83c33f52a405",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
    ]:
        assert needle in text


def test_current_head_ee0ea6b_master_command_acceptance_rerun_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_fallback_master_config_and_command_plan_current_head_ee0ea6b_fixed_artifact_acceptance_passed",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_4751222_20260625T213641Z/dataset.json",
        "expected_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_e4f3831_20260626T012252Z/split_manifest.json",
        "expected_split_manifest_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "train_only_scale_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_acceptance_9d30a2d_20260626T013333Z/scale_manifest.json",
        "expected_scale_manifest_sha256=8ec568461fb0887143b28899388544091aa613500673a2ffe7b1891316e62759",
        "source_scale_manifest_acceptance_status=fallback_risk_training_train_only_scale_manifest_current_head_9d30a2d_fixed_artifact_acceptance_passed",
        "source_scale_manifest_sync_status=fallback_risk_training_train_only_scale_manifest_current_head_9d30a2d_acceptance_autodl_sync_verified",
        "builder_commit=ee0ea6b2dfa81575b6446f831f23448e85fd0b09",
        "autodl_CAMP_HEAD=ee0ea6b2dfa81575b6446f831f23448e85fd0b09",
        "autodl_CAMP_origin_main=ee0ea6b2dfa81575b6446f831f23448e85fd0b09",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_ee0ea6b_20260626T014601Z",
        "fallback_master_config_json_sha256=ea9d8ddf4bbf6a4fdebca9685c6cc1b625c3803837114301bb3537982a030364",
        "training_command_plan_json_sha256=8a04ecb86b195bb472acbaf684ef6d0c942055345b3e1f5738326403a5b1e12d",
        "master_command_md_sha256=a14244b6719d8d5942c9cfa2c9d763a9d4967fa5967b622dfc176757072f232e",
        "builder_stdout_log_sha256=194b56ed5ebb16374b8f48e02b6194912f3b9b3261b86cd86bdd83c33f52a405",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
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
        "fallback_master_config_ready=True",
        "training_command_plan_ready=True",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in text


def test_current_head_1927603_master_command_acceptance_rerun_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_fallback_master_config_and_command_plan_current_head_1927603_fixed_artifact_acceptance_passed",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_4751222_20260625T213641Z/dataset.json",
        "expected_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_6b43925_20260626T051552Z/split_manifest.json",
        "expected_split_manifest_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "train_only_scale_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_acceptance_20fd1a9_20260626T052920Z/scale_manifest.json",
        "expected_scale_manifest_sha256=013db2348319ad5a959c33bc2a078b8b7162969bbd3f5633ca34d1b7ce2ef04b",
        "source_scale_manifest_acceptance_status=fallback_risk_training_train_only_scale_manifest_current_head_20fd1a9_fixed_artifact_acceptance_passed",
        "source_scale_manifest_sync_status=fallback_risk_training_train_only_scale_manifest_current_head_53df201_autodl_sync_verified",
        "builder_commit=1927603f634731e6b2a300f4b3450e0276ac343c",
        "autodl_CAMP_HEAD=1927603f634731e6b2a300f4b3450e0276ac343c",
        "autodl_CAMP_origin_main=1927603f634731e6b2a300f4b3450e0276ac343c",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_1927603_20260626T054437Z",
        "fallback_master_config_json_sha256=10ebf96545e244b4e3fcf657c0897a5f6f3eb72357ea9259b53de19dd2f6dc3a",
        "training_command_plan_json_sha256=6bb97f7346d11039cd3f218ec06e110f92a69bcbddddac036a5301123230116c",
        "master_command_md_sha256=a14244b6719d8d5942c9cfa2c9d763a9d4967fa5967b622dfc176757072f232e",
        "builder_stdout_log_sha256=194b56ed5ebb16374b8f48e02b6194912f3b9b3261b86cd86bdd83c33f52a405",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
        "master_schema_version=dp_native_fallback_risk_fallback_master_config_v1",
        "training_command_schema_version=dp_native_fallback_risk_training_command_plan_v1",
        "fallback_only=True",
        "score_expression=score_k(w)=a_k^T w",
        "atoms_fixed_nonnegative=True",
        "simplex_cvar_l2_convex=True",
        "fallback_label_is_deployed_atom=False",
        "margins_nonnegative=True",
        "feasible_branch_records_allowed=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "hard_feasibility_relaxation_authorized=False",
        "feasible_ranking_master_change_authorized=False",
        "training_command_authorization=False",
        "training_execution_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "fallback_master_config_ready=True",
        "training_command_plan_ready=True",
        "validated_dataset_summary_ready_for_preflight=False",
        "training_sufficiency_preflight_ready=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
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
        "local_target_pytest=6 passed",
        "local_master_command_acceptance_pytest=6 passed",
        "local_master_command_builder_pytest=6 passed",
        "local_git_diff_check_exit=0",
        "autodl_builder_exit=0",
        "autodl_dp_head_verified=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "status=fallback_risk_training_fallback_master_config_and_command_plan_current_head_f6568d8_fixed_artifact_acceptance_passed",
        "fixed_artifact_acceptance_rerun_complete=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_validated_dataset_summary_materializer_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only",
        "may only rerun the default-off validated dataset summary",
        "must not execute training",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
        "status=fallback_risk_training_fallback_master_config_and_command_plan_current_head_ee0ea6b_acceptance_autodl_sync_verified",
        "github_pushed_commit=8993631abfce73785c7fc6396e121c9faaa7995a",
        "autodl_CAMP_HEAD_after_sync=8993631abfce73785c7fc6396e121c9faaa7995a",
        "autodl_CAMP_origin_main_after_sync=8993631abfce73785c7fc6396e121c9faaa7995a",
        "autodl_target_pytest=13 passed",
        "autodl_py_compile_exit=0",
        "autodl_git_diff_check_exit=0",
        "autodl_audit_tail_has_master_command_acceptance=True",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_master_command_rerun_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-210:])

    for needle in [
        "status=fallback_risk_training_fallback_master_config_and_command_plan_current_head_1927603_fixed_artifact_acceptance_passed",
        "fallback_master_config_json_sha256=10ebf96545e244b4e3fcf657c0897a5f6f3eb72357ea9259b53de19dd2f6dc3a",
        "training_command_plan_json_sha256=6bb97f7346d11039cd3f218ec06e110f92a69bcbddddac036a5301123230116c",
        "fallback_master_config_ready=True",
        "training_command_plan_ready=True",
        "local_target_pytest=14 passed",
        "local_master_command_builder_pytest=6 passed",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in tail

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_validated_dataset_summary_materializer_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only`"
    )
