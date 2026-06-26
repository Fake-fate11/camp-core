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
        "latest_source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_e35f1e4_20260625T132102Z/dataset.json",
        "latest_expected_dataset_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "latest_training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_def7dde_20260625T160330Z/split_manifest.json",
        "latest_expected_split_manifest_sha256=13fa6b86d2fcebbb3ecbb675daefa7409f1f427900896307474d2d1dc4f6e773",
        "latest_builder_commit=0d49e68b6529e21f77782f37971825b85338fa5f",
        "latest_autodl_CAMP_HEAD=0d49e68b6529e21f77782f37971825b85338fa5f",
        "latest_builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_acceptance_0d49e68_20260625T161036Z",
        "latest_scale_manifest_json_sha256=452828bf134fb4d5d74d8a491597ee4c50f82893622e283546ea69f2b16da934",
        "latest_scale_manifest_md_sha256=bafe15c581eb48e8a02908989f38a97cf1fa11db1a120e18c440338e76479ac7",
        "latest_builder_exit=0",
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
        "latest_schema_version=dp_native_fallback_risk_training_train_only_scale_manifest_v1",
        "latest_status=dp_native_fallback_risk_training_train_only_scale_manifest_builder_complete",
        "latest_passed=True",
        "latest_scale_policy=train_only_positive_finite_p95_or_one_v1",
        "latest_source_dataset_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "latest_source_split_manifest_sha256=13fa6b86d2fcebbb3ecbb675daefa7409f1f427900896307474d2d1dc4f6e773",
        "latest_atom_schema_version=dp_camp_v10_14d",
        "latest_atom_count=14",
        "latest_fit_records_used=13",
        "latest_training_records_seen=13",
        "latest_validation_records_seen=2",
        "latest_fit_groups=13",
        "latest_excluded_validation_groups=2",
        "latest_fit_seeds=[]",
        "latest_errors=[]",
    ]:
        assert needle in text


def test_current_head_9d30a2d_scale_acceptance_rerun_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_train_only_scale_manifest_current_head_9d30a2d_fixed_artifact_acceptance_passed",
        "acceptance_base_head=9d30a2d61a550702e2e114e4a228fab53b1355a1",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_4751222_20260625T213641Z/dataset.json",
        "expected_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_e4f3831_20260626T012252Z/split_manifest.json",
        "expected_split_manifest_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "validator_output_json_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "source_split_manifest_acceptance_status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_head_e4f3831_passed",
        "builder_commit=9d30a2d61a550702e2e114e4a228fab53b1355a1",
        "autodl_CAMP_HEAD=9d30a2d61a550702e2e114e4a228fab53b1355a1",
        "autodl_CAMP_origin_main=9d30a2d61a550702e2e114e4a228fab53b1355a1",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_acceptance_9d30a2d_20260626T013333Z",
        "scale_manifest_json_sha256=8ec568461fb0887143b28899388544091aa613500673a2ffe7b1891316e62759",
        "scale_manifest_md_sha256=bafe15c581eb48e8a02908989f38a97cf1fa11db1a120e18c440338e76479ac7",
        "builder_stdout_log_sha256=d1d769d60560869f1abc0147d385b5f83a81c2ad21af940527703b08d02bc9d4",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
        "schema_version=dp_native_fallback_risk_training_train_only_scale_manifest_v1",
        "status=dp_native_fallback_risk_training_train_only_scale_manifest_builder_complete",
        "passed=True",
        "scale_policy=train_only_positive_finite_p95_or_one_v1",
        "source_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "source_split_manifest_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "validator_output_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "fit_records_used=13",
        "training_records_seen=13",
        "validation_records_seen=2",
        "fit_groups=13",
        "excluded_validation_groups=2",
        "errors=[]",
        "training_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "fixed_artifact_acceptance_rerun_passed=True",
        "blocking_acceptance_findings=0",
        "train_only_scale_manifest_ready_for_preflight=True",
        "local_target_pytest=7 passed",
    ]:
        assert needle in text


def test_current_head_20fd1a9_scale_acceptance_rerun_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_train_only_scale_manifest_current_head_20fd1a9_fixed_artifact_acceptance_passed",
        "acceptance_base_head=20fd1a98196e385d249c3d04a85f9b16ddbba70d",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_4751222_20260625T213641Z/dataset.json",
        "expected_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_6b43925_20260626T051552Z/split_manifest.json",
        "expected_split_manifest_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "validator_output_json_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "source_split_manifest_acceptance_status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_current_head_a92a0e1_autodl_sync_verified",
        "builder_commit=20fd1a98196e385d249c3d04a85f9b16ddbba70d",
        "autodl_CAMP_HEAD=20fd1a98196e385d249c3d04a85f9b16ddbba70d",
        "autodl_CAMP_origin_main=20fd1a98196e385d249c3d04a85f9b16ddbba70d",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_acceptance_20fd1a9_20260626T052920Z",
        "scale_manifest_json_sha256=013db2348319ad5a959c33bc2a078b8b7162969bbd3f5633ca34d1b7ce2ef04b",
        "scale_manifest_md_sha256=bafe15c581eb48e8a02908989f38a97cf1fa11db1a120e18c440338e76479ac7",
        "builder_stdout_log_sha256=d1d769d60560869f1abc0147d385b5f83a81c2ad21af940527703b08d02bc9d4",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
        "schema_version=dp_native_fallback_risk_training_train_only_scale_manifest_v1",
        "status=dp_native_fallback_risk_training_train_only_scale_manifest_builder_complete",
        "passed=True",
        "scale_policy=train_only_positive_finite_p95_or_one_v1",
        "source_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "source_split_manifest_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "validator_output_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "fit_records_used=13",
        "training_records_seen=13",
        "validation_records_seen=2",
        "fit_groups=13",
        "excluded_validation_groups=2",
        "errors=[]",
        "training_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "fixed_artifact_acceptance_rerun_passed=True",
        "blocking_acceptance_findings=0",
        "train_only_scale_manifest_ready_for_preflight=True",
        "local_target_pytest=8 passed",
        "local_scale_builder_pytest=5 passed",
        "local_related_target_pytest=13 passed",
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
        "latest_fixed_artifact_acceptance_rerun_passed=True",
        "latest_blocking_acceptance_findings=0",
        "latest_train_only_scale_manifest_ready_for_preflight=True",
        "latest_fallback_master_config_ready=False",
        "latest_training_command_plan_ready=False",
        "latest_validated_dataset_summary_ready_for_preflight=False",
        "latest_training_sufficiency_preflight_ready=False",
        "latest_fallback_risk_training_authorized_now=False",
        "latest_camp_retraining_authorized_now=False",
        "latest_fallback_dataset_training_sufficiency_claim=False",
        "latest_fixed_15_record_artifact_training_sufficiency_claim=False",
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
        "latest_local_target_pytest=6 passed",
        "latest_local_scale_builder_pytest=5 passed",
        "latest_autodl_builder_exit=0",
        "latest_training_not_executed=True",
        "latest_candidate_generation_not_executed=True",
        "latest_dp_not_modified=True",
        "latest_selector_or_atom_not_promoted=True",
        "status=fallback_risk_training_train_only_scale_manifest_current_head_9d30a2d_acceptance_autodl_sync_verified",
        "github_pushed_commit=d569c2b98c113efceeee457d1735552332de579e",
        "autodl_CAMP_HEAD_after_sync=d569c2b98c113efceeee457d1735552332de579e",
        "autodl_CAMP_origin_main_after_sync=d569c2b98c113efceeee457d1735552332de579e",
        "autodl_target_pytest=12 passed",
        "autodl_py_compile_exit=0",
        "autodl_git_diff_check_exit=0",
        "autodl_audit_tail_has_scale_acceptance=True",
        "status=fallback_risk_training_train_only_scale_manifest_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_passed",
        "latest_status=fallback_risk_training_train_only_scale_manifest_current_head_fixed_artifact_acceptance_passed",
        "fixed_artifact_acceptance_rerun_complete=True",
        "latest_fixed_artifact_acceptance_rerun_complete=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only",
        "may only rerun the default-off fallback master config",
        "must not execute training",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
        "status=fallback_risk_training_train_only_scale_manifest_current_head_53df201_autodl_sync_verified",
        "pushed_scale_acceptance_commit=53df2012b8ab9dc83ad4f57e7077680d642ff7f1",
        "verified_autodl_target_pytest=13 passed",
        "verified_autodl_py_compile_exit=0",
        "verified_autodl_git_diff_check_exit=0",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_scale_rerun_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-190:])

    for needle in [
        "status=fallback_risk_training_train_only_scale_manifest_current_head_ad223a1_fixed_artifact_acceptance_passed",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_4751222_20260625T213641Z/dataset.json",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_0e302e1_20260626T130030Z/split_manifest.json",
        "scale_manifest_json_sha256=b11cba57efc5761417c539cfbf009866fc8c5f1466a1f041073ea88f6a3b618d",
        "train_only_scale_manifest_ready_for_preflight=True",
        "local_target_pytest=8 passed",
        "local_scale_builder_pytest=5 passed",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "local_related_target_pytest=13 passed",
    ]:
        assert needle in audit

    assert (
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only"
        in tail
    )
    assert (
        "this_acceptance_gate_authorizes_training_replay_dp_or_claims=False"
        in tail
    )
    assert "autodl_builder_exit=0" in tail
