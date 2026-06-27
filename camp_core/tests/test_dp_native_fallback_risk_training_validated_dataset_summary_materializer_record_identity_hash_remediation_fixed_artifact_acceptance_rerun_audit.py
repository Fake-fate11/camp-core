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
        "current_validator_output_matched_dataset_sha=True",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_e35f1e4_20260625T132102Z/dataset.json",
        "expected_dataset_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "source_validator_output_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_validator_acceptance_0c7eada_20260625T141534Z/validation.json",
        "expected_validator_output_sha256=4baaf581141c8fbfddede13bd04b02788276421f041d6eca9bd86c15e1d221fc",
        "source_dataset_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_e35f1e4_passed",
        "source_validator_acceptance_status=fallback_risk_training_data_validator_extension_fixed_artifact_acceptance_current_head_0c7eada_revalidated",
        "builder_commit=81b0f9a35ce18a78f33e8a22de1e06d7747ef6f5",
        "autodl_CAMP_HEAD=81b0f9a35ce18a78f33e8a22de1e06d7747ef6f5",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_acceptance_81b0f9a_20260625T162436Z",
        "validated_dataset_summary_json_sha256=0bddd80cd458ea7d63adeae44a19b9584a20fd24f429d3435f836123a6862b61",
        "validated_dataset_summary_md_sha256=e1c75b4c6bc0b9626f44fd1cbdee29be8418d4660b8acf7e0430bbc7b0a05426",
        "builder_stdout_log_sha256=f2a064276a2ddbcdac2da735e639be85f5c8b5fe153b62461f3b46c8388a0abe",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
    ]:
        assert needle in text


def test_current_head_84a5eff_summary_acceptance_rerun_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_validated_dataset_summary_materializer_current_head_84a5eff_fixed_artifact_acceptance_passed",
        "current_validator_output_matched_dataset_sha=True",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_4751222_20260625T213641Z/dataset.json",
        "expected_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "source_validator_output_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_validator_acceptance_6dc8ae6_20260625T222922Z/validation.json",
        "expected_validator_output_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "source_dataset_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_4751222_passed",
        "source_validator_acceptance_status=fallback_risk_training_data_validator_extension_fixed_artifact_acceptance_current_head_6dc8ae6_passed",
        "builder_commit=84a5eff98155b53981ae0f7b98810b1feb08d5e9",
        "autodl_CAMP_HEAD=84a5eff98155b53981ae0f7b98810b1feb08d5e9",
        "autodl_CAMP_origin_main=84a5eff98155b53981ae0f7b98810b1feb08d5e9",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_acceptance_84a5eff_20260626T015351Z",
        "validated_dataset_summary_json_sha256=6ed8c738e65a6d9190db40a042089a21a7aaa032be0a9617b22b0ba4c67314e6",
        "validated_dataset_summary_md_sha256=e1c75b4c6bc0b9626f44fd1cbdee29be8418d4660b8acf7e0430bbc7b0a05426",
        "builder_stdout_log_sha256=f2a064276a2ddbcdac2da735e639be85f5c8b5fe153b62461f3b46c8388a0abe",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
        "summary_schema_version=dp_native_fallback_risk_validated_dataset_summary_v1",
        "summary_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "summary_records=15",
        "summary_validator_status=dp_native_fallback_risk_training_data_validator_complete",
        "summary_validator_passed=True",
        "summary_training_sufficiency_claim=False",
        "summary_deployable_checkpoint_claim=False",
        "summary_source_validator_output_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "validated_dataset_summary_ready_for_preflight=True",
        "training_sufficiency_preflight_input_set_ready=True",
        "training_sufficiency_preflight_executed=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in text


def test_current_head_db0111c_summary_acceptance_rerun_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_validated_dataset_summary_materializer_current_head_db0111c_fixed_artifact_acceptance_passed",
        "current_validator_output_matched_dataset_sha=True",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_4751222_20260625T213641Z/dataset.json",
        "expected_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "source_validator_output_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_validator_acceptance_6dc8ae6_20260625T222922Z/validation.json",
        "expected_validator_output_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "source_dataset_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_4751222_passed",
        "source_validator_acceptance_status=fallback_risk_training_data_validator_extension_fixed_artifact_acceptance_current_head_6dc8ae6_passed",
        "source_master_command_sync_status=fallback_risk_training_fallback_master_config_and_command_plan_current_head_16fa482_acceptance_autodl_sync_verified",
        "builder_commit=db0111cc8144628f6dc6ab13722edf728c1ca465",
        "autodl_CAMP_HEAD=db0111cc8144628f6dc6ab13722edf728c1ca465",
        "autodl_CAMP_origin_main=db0111cc8144628f6dc6ab13722edf728c1ca465",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_acceptance_db0111c_20260626T055955Z",
        "validated_dataset_summary_json_sha256=6ed8c738e65a6d9190db40a042089a21a7aaa032be0a9617b22b0ba4c67314e6",
        "validated_dataset_summary_md_sha256=e1c75b4c6bc0b9626f44fd1cbdee29be8418d4660b8acf7e0430bbc7b0a05426",
        "builder_stdout_log_sha256=f2a064276a2ddbcdac2da735e639be85f5c8b5fe153b62461f3b46c8388a0abe",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
        "summary_schema_version=dp_native_fallback_risk_validated_dataset_summary_v1",
        "summary_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "summary_records=15",
        "summary_validator_status=dp_native_fallback_risk_training_data_validator_complete",
        "summary_validator_passed=True",
        "summary_training_sufficiency_claim=False",
        "summary_deployable_checkpoint_claim=False",
        "summary_source_validator_output_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "validated_dataset_summary_ready_for_preflight=True",
        "training_sufficiency_preflight_input_set_ready=True",
        "training_sufficiency_preflight_executed=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in text


def test_current_head_b3d216b_summary_sync_verification_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_validated_dataset_summary_materializer_current_head_b3d216b_acceptance_autodl_sync_verified",
        "source_summary_acceptance_status=fallback_risk_training_validated_dataset_summary_materializer_current_head_db0111c_fixed_artifact_acceptance_passed",
        "pushed_summary_acceptance_commit=b3d216b6709ecef15f759e39ccd639b1beb6e17b",
        "verified_local_HEAD=b3d216b6709ecef15f759e39ccd639b1beb6e17b",
        "verified_origin_main=b3d216b6709ecef15f759e39ccd639b1beb6e17b",
        "verified_github_refs_heads_main=b3d216b6709ecef15f759e39ccd639b1beb6e17b",
        "verified_autodl_CAMP_HEAD=b3d216b6709ecef15f759e39ccd639b1beb6e17b",
        "verified_autodl_CAMP_origin_main=b3d216b6709ecef15f759e39ccd639b1beb6e17b",
        "verified_autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "sync_method=autodl_bundle_fast_forward",
        "sync_bundle=F:\\t\\camp_db0111c_to_b3d216b.bundle",
        "sync_bundle_sha256=1b702ef9cdcfc0a7c5a5160500e50b00e31396f8c1661b53100916d86678d975",
        "autodl_bundle_verify_exit=0",
        "autodl_bundle_fetch_exit=0",
        "autodl_fast_forward_exit=0",
        "autodl_origin_main_update_ref_exit=0",
        "verified_autodl_py_compile_exit=0",
        "verified_autodl_target_pytest=13 passed",
        "verified_autodl_git_diff_check_exit=0",
        "verified_autodl_training_not_executed=True",
        "verified_autodl_candidate_generation_not_executed=True",
        "verified_autodl_dp_not_modified=True",
        "verified_autodl_selector_or_atom_not_promoted=True",
        "this_sync_verification_authorizes_training_replay_dp_or_claims=False",
    ]:
        assert needle in text


def test_current_head_76cfde6_summary_acceptance_rerun_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_validated_dataset_summary_materializer_current_head_76cfde6_fixed_artifact_acceptance_passed",
        "current_validator_output_matched_dataset_sha=True",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_4751222_20260625T213641Z/dataset.json",
        "expected_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "source_validator_output_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_validator_acceptance_6dc8ae6_20260625T222922Z/validation.json",
        "expected_validator_output_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "source_dataset_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_4751222_passed",
        "source_validator_acceptance_status=fallback_risk_training_data_validator_extension_fixed_artifact_acceptance_current_head_6dc8ae6_passed",
        "source_master_command_acceptance_status=fallback_risk_training_fallback_master_config_and_command_plan_current_head_acbbb77_fixed_artifact_acceptance_passed",
        "builder_commit=76cfde6e184de90d741a8c878b189251bbba1e3e",
        "autodl_CAMP_HEAD=76cfde6e184de90d741a8c878b189251bbba1e3e",
        "autodl_CAMP_origin_main=76cfde6e184de90d741a8c878b189251bbba1e3e",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_acceptance_76cfde6_20260626T132503Z",
        "validated_dataset_summary_json_sha256=6ed8c738e65a6d9190db40a042089a21a7aaa032be0a9617b22b0ba4c67314e6",
        "validated_dataset_summary_md_sha256=e1c75b4c6bc0b9626f44fd1cbdee29be8418d4660b8acf7e0430bbc7b0a05426",
        "builder_stdout_log_sha256=f2a064276a2ddbcdac2da735e639be85f5c8b5fe153b62461f3b46c8388a0abe",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
        "summary_schema_version=dp_native_fallback_risk_validated_dataset_summary_v1",
        "summary_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "summary_records=15",
        "summary_validator_status=dp_native_fallback_risk_training_data_validator_complete",
        "summary_validator_passed=True",
        "summary_training_sufficiency_claim=False",
        "summary_deployable_checkpoint_claim=False",
        "summary_source_validator_output_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "validated_dataset_summary_ready_for_preflight=True",
        "training_sufficiency_preflight_input_set_ready=True",
        "training_sufficiency_preflight_executed=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in text


def test_current_head_c2646b3_summary_acceptance_rerun_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_validated_dataset_summary_materializer_current_head_c2646b3_fixed_artifact_acceptance_passed",
        "current_validator_output_matched_dataset_sha=True",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_4751222_20260625T213641Z/dataset.json",
        "expected_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "source_validator_output_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_validator_acceptance_6dc8ae6_20260625T222922Z/validation.json",
        "expected_validator_output_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "source_dataset_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_4751222_passed",
        "source_validator_acceptance_status=fallback_risk_training_data_validator_extension_fixed_artifact_acceptance_current_head_6dc8ae6_passed",
        "source_master_command_acceptance_status=fallback_risk_training_fallback_master_config_and_command_plan_current_head_ce7a2ca_tail_authority",
        "builder_commit=c2646b394f6fb9bcc1d2d232f1d8102895271f52",
        "autodl_CAMP_HEAD=c2646b394f6fb9bcc1d2d232f1d8102895271f52",
        "autodl_CAMP_origin_main=c2646b394f6fb9bcc1d2d232f1d8102895271f52",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_acceptance_c2646b3_20260626T184436Z",
        "validated_dataset_summary_json_sha256=6ed8c738e65a6d9190db40a042089a21a7aaa032be0a9617b22b0ba4c67314e6",
        "validated_dataset_summary_md_sha256=e1c75b4c6bc0b9626f44fd1cbdee29be8418d4660b8acf7e0430bbc7b0a05426",
        "builder_stdout_log_sha256=f2a064276a2ddbcdac2da735e639be85f5c8b5fe153b62461f3b46c8388a0abe",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
        "summary_schema_version=dp_native_fallback_risk_validated_dataset_summary_v1",
        "summary_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "observed_summary_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "summary_records=15",
        "summary_validator_status=dp_native_fallback_risk_training_data_validator_complete",
        "summary_validator_passed=True",
        "summary_training_sufficiency_claim=False",
        "summary_deployable_checkpoint_claim=False",
        "summary_source_validator_output_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "validated_dataset_summary_ready_for_preflight=True",
        "training_sufficiency_preflight_input_set_ready=True",
        "training_sufficiency_preflight_executed=False",
        "training_sufficiency_preflight_execution_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "local_target_pytest=11 passed",
        "local_summary_acceptance_pytest=11 passed",
        "local_summary_materializer_pytest=5 passed",
        "local_related_target_pytest=16 passed",
        "autodl_temp_worktree=/root/autodl-tmp/camp_core_validated_summary_acceptance_c2646b3_verify_20260627T033000Z",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=11 passed",
        "autodl_related_target_pytest=16 passed",
        "autodl_git_diff_check_exit=0",
    ]:
        assert needle in text


def test_current_head_f9fc3f4_summary_acceptance_rerun_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_validated_dataset_summary_materializer_current_head_f9fc3f4_fixed_artifact_acceptance_passed",
        "current_validator_output_matched_dataset_sha=True",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_db52ac6_20260626T211859Z/dataset.json",
        "expected_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "source_validator_output_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_validator_acceptance_7f5ca75_20260626T215730Z/validation.json",
        "expected_validator_output_sha256=4f3a0be2dbf070b4d94262111e3c9b68618732efd64f54355722dbfbe61f2d40",
        "source_dataset_acceptance_status=fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_current_head_db52ac6_passed",
        "source_validator_acceptance_status=fallback_risk_training_data_validator_extension_fixed_artifact_acceptance_current_head_7f5ca75_passed",
        "source_master_command_acceptance_status=fallback_risk_training_fallback_master_config_and_command_plan_current_head_a1d1d6d_fixed_artifact_acceptance_passed",
        "builder_commit=f9fc3f4e0a253f7dc6325d5c7a506941d2567637",
        "autodl_CAMP_HEAD=f9fc3f4e0a253f7dc6325d5c7a506941d2567637",
        "autodl_CAMP_origin_main=f9fc3f4e0a253f7dc6325d5c7a506941d2567637",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_acceptance_f9fc3f4_20260627T101500CST",
        "validated_dataset_summary_json_sha256=4b6a2cc9d67d593b32e87d96fcc22c8f3cc980ab73a79b217b13274f2e3d67d9",
        "validated_dataset_summary_md_sha256=e1c75b4c6bc0b9626f44fd1cbdee29be8418d4660b8acf7e0430bbc7b0a05426",
        "builder_stdout_log_sha256=f2a064276a2ddbcdac2da735e639be85f5c8b5fe153b62461f3b46c8388a0abe",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
        "summary_schema_version=dp_native_fallback_risk_validated_dataset_summary_v1",
        "summary_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "observed_summary_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "summary_records=15",
        "summary_validator_status=dp_native_fallback_risk_training_data_validator_complete",
        "summary_validator_passed=True",
        "summary_training_sufficiency_claim=False",
        "summary_deployable_checkpoint_claim=False",
        "summary_source_validator_output_sha256=4f3a0be2dbf070b4d94262111e3c9b68618732efd64f54355722dbfbe61f2d40",
        "validated_dataset_summary_ready_for_preflight=True",
        "training_sufficiency_preflight_input_set_ready=True",
        "training_sufficiency_preflight_executed=False",
        "training_sufficiency_preflight_execution_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "local_target_pytest=12 passed",
        "local_summary_acceptance_pytest=12 passed",
        "local_summary_materializer_pytest=5 passed",
        "local_related_target_pytest=17 passed",
        "autodl_temp_worktree=/root/autodl-tmp/camp_core_validated_summary_acceptance_f9fc3f4_verify_20260627T103000CST",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=12 passed",
        "autodl_related_target_pytest=17 passed",
        "autodl_git_diff_check_exit=0",
        "autodl_dp_head_verified=7a1d33da277a1992ec474b5383a0c963c72e04e4",
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
        "summary_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "summary_records=15",
        "summary_validator_status=dp_native_fallback_risk_training_data_validator_complete",
        "summary_validator_passed=True",
        "summary_training_sufficiency_claim=False",
        "summary_deployable_checkpoint_claim=False",
        "summary_source_validator_output_sha256=4baaf581141c8fbfddede13bd04b02788276421f041d6eca9bd86c15e1d221fc",
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
        "local_target_pytest=6 passed",
        "local_summary_acceptance_pytest=6 passed",
        "local_summary_materializer_pytest=5 passed",
        "local_git_diff_check_exit=0",
        "autodl_builder_exit=0",
        "autodl_dp_head_verified=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "status=fallback_risk_training_validated_dataset_summary_materializer_current_head_81b0f9a_fixed_artifact_acceptance_passed",
        "fixed_artifact_acceptance_rerun_complete=True",
        "blocking_acceptance_findings=0",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only",
        "may only run the already implemented default-off read-only",
        "User permission to retrain CAMP is available",
        "status=fallback_risk_training_validated_dataset_summary_materializer_current_head_84a5eff_acceptance_autodl_sync_verified",
        "github_pushed_commit=0166155fa10ca228fc22949afe2d32e93e527602",
        "autodl_CAMP_HEAD_after_sync=0166155fa10ca228fc22949afe2d32e93e527602",
        "autodl_CAMP_origin_main_after_sync=0166155fa10ca228fc22949afe2d32e93e527602",
        "autodl_target_pytest=12 passed",
        "autodl_py_compile_exit=0",
        "autodl_git_diff_check_exit=0",
        "autodl_audit_tail_has_summary_acceptance=True",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_summary_rerun_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-240:])

    for needle in [
        "status=fallback_risk_training_validated_dataset_summary_materializer_current_head_f9fc3f4_fixed_artifact_acceptance_passed",
        "validated_dataset_summary_json_sha256=4b6a2cc9d67d593b32e87d96fcc22c8f3cc980ab73a79b217b13274f2e3d67d9",
        "observed_summary_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "validated_dataset_summary_ready_for_preflight=True",
        "training_sufficiency_preflight_input_set_ready=True",
        "local_target_pytest=12 passed",
        "local_summary_acceptance_pytest=12 passed",
        "local_summary_materializer_pytest=5 passed",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "source_master_command_acceptance_status=fallback_risk_training_fallback_master_config_and_command_plan_current_head_a1d1d6d_fixed_artifact_acceptance_passed",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_acceptance_f9fc3f4_20260627T101500CST",
        "autodl_builder_exit=0",
        "autodl_related_target_pytest=17 passed",
        "autodl_dp_head_verified=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only",
        "may only run the already implemented default-off read-only",
        "this materializer gate does not authorize",
    ]:
        assert needle in tail
