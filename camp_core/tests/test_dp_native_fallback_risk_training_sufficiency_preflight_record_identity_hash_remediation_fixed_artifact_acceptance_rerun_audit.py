from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _audit() -> str:
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_preflight_acceptance_rerun_records_inputs_and_outputs() -> None:
    text = _audit()

    for needle in [
        "validated_dataset_summary_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_acceptance_81b0f9a_20260625T162436Z/validated_dataset_summary.json",
        "validated_dataset_summary_json_sha256=0bddd80cd458ea7d63adeae44a19b9584a20fd24f429d3435f836123a6862b61",
        "validated_dataset_summary_payload_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_def7dde_20260625T160330Z/split_manifest.json",
        "training_split_manifest_json_sha256=13fa6b86d2fcebbb3ecbb675daefa7409f1f427900896307474d2d1dc4f6e773",
        "train_only_scale_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_acceptance_0d49e68_20260625T161036Z/scale_manifest.json",
        "train_only_scale_manifest_json_sha256=452828bf134fb4d5d74d8a491597ee4c50f82893622e283546ea69f2b16da934",
        "fallback_master_config_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_f6568d8_20260625T161735Z/fallback_master_config.json",
        "fallback_master_config_json_sha256=081a31214f18d1608a440b8826cd4cd4febaa6760284e8f01cbd0749b502e1b9",
        "training_command_plan_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_f6568d8_20260625T161735Z/training_command_plan.json",
        "training_command_plan_json_sha256=a56c86337d5576811d866a7b080a629cadb2f692a02fed7675be20e1810aec3a",
        "source_summary_acceptance_status=fallback_risk_training_validated_dataset_summary_materializer_current_head_81b0f9a_fixed_artifact_acceptance_passed",
        "preflight_commit=9abb83395dff2094128c0deecafd017a85c5a990",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "preflight_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_sufficiency_preflight_acceptance_9abb833_20260625T162958Z",
        "preflight_exit=0",
        "preflight_json_sha256=22ad4437d0cfa2eea0884d340c9c0fd6073824ce86bbf263d6f4e3e4bff6d51b",
        "preflight_md_sha256=e596460039c684007b81ca61787eb5969378d2c238e25d4cc3ed8e740e4178f9",
    ]:
        assert needle in text


def test_current_head_e0347d8_preflight_acceptance_rerun_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_current_head_e0347d8_fixed_artifact_acceptance_passed",
        "validated_dataset_summary_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_acceptance_84a5eff_20260626T015351Z/validated_dataset_summary.json",
        "validated_dataset_summary_json_sha256=6ed8c738e65a6d9190db40a042089a21a7aaa032be0a9617b22b0ba4c67314e6",
        "validated_dataset_summary_payload_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_e4f3831_20260626T012252Z/split_manifest.json",
        "training_split_manifest_json_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "train_only_scale_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_acceptance_9d30a2d_20260626T013333Z/scale_manifest.json",
        "train_only_scale_manifest_json_sha256=8ec568461fb0887143b28899388544091aa613500673a2ffe7b1891316e62759",
        "fallback_master_config_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_ee0ea6b_20260626T014601Z/fallback_master_config.json",
        "fallback_master_config_json_sha256=ea9d8ddf4bbf6a4fdebca9685c6cc1b625c3803837114301bb3537982a030364",
        "training_command_plan_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_ee0ea6b_20260626T014601Z/training_command_plan.json",
        "training_command_plan_json_sha256=8a04ecb86b195bb472acbaf684ef6d0c942055345b3e1f5738326403a5b1e12d",
        "source_summary_acceptance_status=fallback_risk_training_validated_dataset_summary_materializer_current_head_84a5eff_fixed_artifact_acceptance_passed",
        "source_summary_sync_status=fallback_risk_training_validated_dataset_summary_materializer_current_head_84a5eff_acceptance_autodl_sync_verified",
        "preflight_commit=e0347d8c3e70d8b733a5cd6fb1ff156e9dd6b1fa",
        "autodl_CAMP_HEAD=e0347d8c3e70d8b733a5cd6fb1ff156e9dd6b1fa",
        "autodl_CAMP_origin_main=e0347d8c3e70d8b733a5cd6fb1ff156e9dd6b1fa",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "preflight_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_sufficiency_preflight_acceptance_e0347d8_20260626T020109Z",
        "preflight_exit=0",
        "preflight_json_sha256=8f68f312188ada4661aa6cb7dc91cbb9c5537df147ac5c3f0851ee6a5d00e8c5",
        "preflight_md_sha256=e596460039c684007b81ca61787eb5969378d2c238e25d4cc3ed8e740e4178f9",
        "preflight_stdout_log_sha256=618e87de3bee239f9fbcd5a101543fdd879383547486fbbd9b46791c4ff821b6",
        "preflight_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "schema_version=dp_native_fallback_risk_training_sufficiency_preflight_v1",
        "status=dp_native_fallback_risk_training_sufficiency_preflight_complete",
        "passed=True",
        "ready_for_future_training_authorization=True",
        "training_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "camp_retraining_authorized_now=False",
        "source_hash_validated_dataset=6ed8c738e65a6d9190db40a042089a21a7aaa032be0a9617b22b0ba4c67314e6",
        "source_hash_split_manifest=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "source_hash_scale_manifest=8ec568461fb0887143b28899388544091aa613500673a2ffe7b1891316e62759",
        "source_hash_fallback_master_config=ea9d8ddf4bbf6a4fdebca9685c6cc1b625c3803837114301bb3537982a030364",
        "source_hash_training_command_plan=8a04ecb86b195bb472acbaf684ef6d0c942055345b3e1f5738326403a5b1e12d",
        "fallback_only_master_verified=True",
        "score_k(w)=a_k^T w",
        "simplex_cvar_l2_convex=True",
        "training_sufficiency_preflight_passed=True",
        "training_command_authorization_required=True",
    ]:
        assert needle in text


def test_current_head_c1293b0_preflight_acceptance_rerun_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_current_head_c1293b0_fixed_artifact_acceptance_passed",
        "validated_dataset_summary_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_acceptance_db0111c_20260626T055955Z/validated_dataset_summary.json",
        "validated_dataset_summary_json_sha256=6ed8c738e65a6d9190db40a042089a21a7aaa032be0a9617b22b0ba4c67314e6",
        "validated_dataset_summary_payload_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_6b43925_20260626T051552Z/split_manifest.json",
        "training_split_manifest_json_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "train_only_scale_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_acceptance_20fd1a9_20260626T052920Z/scale_manifest.json",
        "train_only_scale_manifest_json_sha256=013db2348319ad5a959c33bc2a078b8b7162969bbd3f5633ca34d1b7ce2ef04b",
        "fallback_master_config_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_1927603_20260626T054437Z/fallback_master_config.json",
        "fallback_master_config_json_sha256=10ebf96545e244b4e3fcf657c0897a5f6f3eb72357ea9259b53de19dd2f6dc3a",
        "training_command_plan_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_1927603_20260626T054437Z/training_command_plan.json",
        "training_command_plan_json_sha256=6bb97f7346d11039cd3f218ec06e110f92a69bcbddddac036a5301123230116c",
        "source_summary_acceptance_status=fallback_risk_training_validated_dataset_summary_materializer_current_head_db0111c_fixed_artifact_acceptance_passed",
        "source_summary_sync_status=fallback_risk_training_validated_dataset_summary_materializer_current_head_b3d216b_acceptance_autodl_sync_verified",
        "preflight_commit=c1293b056b1b88e1f6cdd341c7160ce626bc1635",
        "autodl_CAMP_HEAD=c1293b056b1b88e1f6cdd341c7160ce626bc1635",
        "autodl_CAMP_origin_main=c1293b056b1b88e1f6cdd341c7160ce626bc1635",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "preflight_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_sufficiency_preflight_acceptance_c1293b0_20260626T061349Z",
        "preflight_exit=0",
        "preflight_json_sha256=72ca918aa05fd92b120ef7f8631a5d6984f1dfd649d9659e84f7f9beb7fc786c",
        "preflight_md_sha256=e596460039c684007b81ca61787eb5969378d2c238e25d4cc3ed8e740e4178f9",
        "preflight_stdout_log_sha256=618e87de3bee239f9fbcd5a101543fdd879383547486fbbd9b46791c4ff821b6",
        "preflight_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "source_hash_validated_dataset=6ed8c738e65a6d9190db40a042089a21a7aaa032be0a9617b22b0ba4c67314e6",
        "source_hash_split_manifest=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "source_hash_scale_manifest=013db2348319ad5a959c33bc2a078b8b7162969bbd3f5633ca34d1b7ce2ef04b",
        "source_hash_fallback_master_config=10ebf96545e244b4e3fcf657c0897a5f6f3eb72357ea9259b53de19dd2f6dc3a",
        "source_hash_training_command_plan=6bb97f7346d11039cd3f218ec06e110f92a69bcbddddac036a5301123230116c",
        "training_sufficiency_preflight_passed=True",
        "ready_for_future_training_authorization=True",
        "training_command_authorization_required=True",
    ]:
        assert needle in text


def test_current_head_bdf9b1d_preflight_acceptance_rerun_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_current_head_bdf9b1d_fixed_artifact_acceptance_passed",
        "validated_dataset_summary_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_acceptance_76cfde6_20260626T132503Z/validated_dataset_summary.json",
        "validated_dataset_summary_json_sha256=6ed8c738e65a6d9190db40a042089a21a7aaa032be0a9617b22b0ba4c67314e6",
        "validated_dataset_summary_payload_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_0e302e1_20260626T130030Z/split_manifest.json",
        "training_split_manifest_json_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "train_only_scale_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_acceptance_ad223a1_20260626T130628Z/scale_manifest.json",
        "train_only_scale_manifest_json_sha256=b11cba57efc5761417c539cfbf009866fc8c5f1466a1f041073ea88f6a3b618d",
        "fallback_master_config_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_acbbb77_20260626T131312Z/fallback_master_config.json",
        "fallback_master_config_json_sha256=fdef70d470721fdf9dabb2c44f3ae2656da177aa2345fbaf6b225b00e7576200",
        "training_command_plan_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_acbbb77_20260626T131312Z/training_command_plan.json",
        "training_command_plan_json_sha256=7fc2904a4d49a853c8c29833ab2d4724342df74ad53cc561322455d09dd40b18",
        "source_summary_acceptance_status=fallback_risk_training_validated_dataset_summary_materializer_current_head_76cfde6_fixed_artifact_acceptance_passed",
        "preflight_commit=bdf9b1d612e18db282e9c9065e078776d6a69054",
        "autodl_CAMP_HEAD=bdf9b1d612e18db282e9c9065e078776d6a69054",
        "autodl_CAMP_origin_main=bdf9b1d612e18db282e9c9065e078776d6a69054",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "preflight_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_sufficiency_preflight_acceptance_bdf9b1d_20260626T133105Z",
        "preflight_exit=0",
        "preflight_json_sha256=c816b04fc3171514cdef8ad3643ba138c86b5361b3e5c2ce577de9d2dd3f0809",
        "preflight_md_sha256=e596460039c684007b81ca61787eb5969378d2c238e25d4cc3ed8e740e4178f9",
        "preflight_stdout_log_sha256=618e87de3bee239f9fbcd5a101543fdd879383547486fbbd9b46791c4ff821b6",
        "preflight_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "source_hash_validated_dataset=6ed8c738e65a6d9190db40a042089a21a7aaa032be0a9617b22b0ba4c67314e6",
        "source_hash_split_manifest=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "source_hash_scale_manifest=b11cba57efc5761417c539cfbf009866fc8c5f1466a1f041073ea88f6a3b618d",
        "source_hash_fallback_master_config=fdef70d470721fdf9dabb2c44f3ae2656da177aa2345fbaf6b225b00e7576200",
        "source_hash_training_command_plan=7fc2904a4d49a853c8c29833ab2d4724342df74ad53cc561322455d09dd40b18",
        "training_sufficiency_preflight_passed=True",
        "ready_for_future_training_authorization=True",
        "training_command_authorization_required=True",
    ]:
        assert needle in text


def test_current_head_db5b070_preflight_acceptance_rerun_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_current_head_db5b070_fixed_artifact_acceptance_passed",
        "validated_dataset_summary_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_acceptance_c2646b3_20260626T184436Z/validated_dataset_summary.json",
        "validated_dataset_summary_json_sha256=6ed8c738e65a6d9190db40a042089a21a7aaa032be0a9617b22b0ba4c67314e6",
        "validated_dataset_summary_payload_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_094a2b4_20260626T182031Z/split_manifest.json",
        "training_split_manifest_json_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "train_only_scale_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_acceptance_fc3f224_20260626T182842Z/scale_manifest.json",
        "train_only_scale_manifest_json_sha256=6d4f691a6eeae0324406af959ddcff996b36441eb4d839b41143ef48bbc802f5",
        "fallback_master_config_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_ce7a2ca_20260626T183841Z/fallback_master_config.json",
        "fallback_master_config_json_sha256=e8e6425ee7fd5371af597fc97cacc16593817cc19c35c1f64bc5c684c7cb37fb",
        "training_command_plan_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_ce7a2ca_20260626T183841Z/training_command_plan.json",
        "training_command_plan_json_sha256=65bae87cde199c9c3b0a2d94104849bb47f3a753215642110ea9d4efe40f1384",
        "source_summary_acceptance_status=fallback_risk_training_validated_dataset_summary_materializer_current_head_c2646b3_tail_authority",
        "source_master_command_acceptance_status=fallback_risk_training_fallback_master_config_and_command_plan_current_head_ce7a2ca_tail_authority",
        "preflight_commit=db5b07084d2e7919c8e4c0ff04eae44a32417dec",
        "autodl_CAMP_HEAD=db5b07084d2e7919c8e4c0ff04eae44a32417dec",
        "autodl_CAMP_origin_main=db5b07084d2e7919c8e4c0ff04eae44a32417dec",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "preflight_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_sufficiency_preflight_acceptance_db5b070_20260627T034500Z",
        "preflight_exit=0",
        "preflight_json_sha256=0c42ca3bf526e12190cc409bda5ab9ab829b17228624346bc15b291b7d22aabc",
        "preflight_md_sha256=e596460039c684007b81ca61787eb5969378d2c238e25d4cc3ed8e740e4178f9",
        "preflight_stdout_log_sha256=618e87de3bee239f9fbcd5a101543fdd879383547486fbbd9b46791c4ff821b6",
        "preflight_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "source_hash_validated_dataset=6ed8c738e65a6d9190db40a042089a21a7aaa032be0a9617b22b0ba4c67314e6",
        "source_hash_split_manifest=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "source_hash_scale_manifest=6d4f691a6eeae0324406af959ddcff996b36441eb4d839b41143ef48bbc802f5",
        "source_hash_fallback_master_config=e8e6425ee7fd5371af597fc97cacc16593817cc19c35c1f64bc5c684c7cb37fb",
        "source_hash_training_command_plan=65bae87cde199c9c3b0a2d94104849bb47f3a753215642110ea9d4efe40f1384",
        "analysis_read_only=True",
        "candidate_generation_executed=False",
        "camp_training_executed=False",
        "diffusion_planner_executed=False",
        "diffusion_planner_modified=False",
        "training_sufficiency_preflight_passed=True",
        "ready_for_future_training_authorization=True",
        "training_command_authorization_required=True",
        "training_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in text


def test_preflight_acceptance_rerun_records_complete_result() -> None:
    text = _audit()

    for needle in [
        "schema_version=dp_native_fallback_risk_training_sufficiency_preflight_v1",
        "status=dp_native_fallback_risk_training_sufficiency_preflight_complete",
        "passed=True",
        "enabled=True",
        "errors=[]",
        "preflight_output_written=True",
        "ready_for_future_training_authorization=True",
        "training_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "camp_retraining_authorized_now=False",
        "fallback_risk_training_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
    ]:
        assert needle in text


def test_preflight_acceptance_rerun_records_source_hashes_and_convex_contract() -> None:
    text = _audit()

    for needle in [
        "source_hash_validated_dataset=0bddd80cd458ea7d63adeae44a19b9584a20fd24f429d3435f836123a6862b61",
        "source_hash_split_manifest=13fa6b86d2fcebbb3ecbb675daefa7409f1f427900896307474d2d1dc4f6e773",
        "source_hash_scale_manifest=452828bf134fb4d5d74d8a491597ee4c50f82893622e283546ea69f2b16da934",
        "source_hash_fallback_master_config=081a31214f18d1608a440b8826cd4cd4febaa6760284e8f01cbd0749b502e1b9",
        "source_hash_training_command_plan=a56c86337d5576811d866a7b080a629cadb2f692a02fed7675be20e1810aec3a",
        "fallback_only_master_verified=True",
        "score_k(w)=a_k^T w",
        "simplex_cvar_l2_convex=True",
        "fixed_15_record_artifact_training_sufficiency_claim=False",
    ]:
        assert needle in text


def test_preflight_acceptance_rerun_keeps_training_dp_and_claims_forbidden() -> None:
    text = _audit()

    for needle in [
        "user_camp_retraining_permission_available=True",
        "training_execution_authorized_now=False",
        "training_authorized=False",
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
        "training_authorized=True",
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in text


def test_preflight_acceptance_rerun_records_verification_and_next_gate() -> None:
    text = _audit()

    for needle in [
        "local_py_compile_exit=0",
        "local_target_pytest=6 passed",
        "local_preflight_acceptance_rerun_pytest=6 passed",
        "local_preflight_pytest=6 passed",
        "local_git_diff_check_exit=0",
        "autodl_preflight_exit=0",
        "autodl_dp_head_verified=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "status=fallback_risk_training_sufficiency_preflight_current_head_9abb833_fixed_artifact_acceptance_passed",
        "training_sufficiency_preflight_passed=True",
        "ready_for_future_training_authorization=True",
        "training_command_authorization_required=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_command_authorization_only",
        "must not modify DP",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_preflight_rerun_command_authorization_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-260:])

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_current_head_db5b070_tail_authority",
        "source_preflight_acceptance_status=fallback_risk_training_sufficiency_preflight_current_head_db5b070_fixed_artifact_acceptance_passed",
        "preflight_json_sha256=0c42ca3bf526e12190cc409bda5ab9ab829b17228624346bc15b291b7d22aabc",
        "source_hash_scale_manifest=6d4f691a6eeae0324406af959ddcff996b36441eb4d839b41143ef48bbc802f5",
        "training_sufficiency_preflight_passed=True",
        "ready_for_future_training_authorization=True",
        "training_command_authorization_required=True",
        "training_authorized=False",
        "camp_retraining_authorized_now=False",
        "dp_modification_authorized=False",
        "autodl_temp_worktree=/root/autodl-tmp/camp_core_preflight_acceptance_db5b070_verify_20260627T040000Z",
        "autodl_related_target_pytest=18 passed",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_command_authorization_only",
        "must not modify DP",
    ]:
        assert needle in tail
