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


def test_current_head_95215ab_preflight_acceptance_rerun_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_current_head_95215ab_fixed_artifact_acceptance_passed",
        "validated_dataset_summary_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_acceptance_1b093c3_20260625T195215Z/validated_dataset_summary.json",
        "validated_dataset_summary_json_sha256=f2ff69df6286b5242b7b510263a5dcc194b8c3bbd43db22253688813eddd79fe",
        "validated_dataset_summary_payload_sha256=682d432f742d4ab68a262cf70955981bc1562cf1dbcf2ec094984a12fcd11498",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_6d1fa5e_20260625T193828Z/split_manifest.json",
        "training_split_manifest_json_sha256=e0a4ec0623f5db0b868465249ce9615b06b86f6c91067702af3bee9fd700db1d",
        "train_only_scale_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_acceptance_cb12988_20260625T194220Z/scale_manifest.json",
        "train_only_scale_manifest_json_sha256=92059b9c60e66c96db836821cb0060072402089b915e0bbd87240fc24c602567",
        "fallback_master_config_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_9270485_20260625T194804Z/fallback_master_config.json",
        "fallback_master_config_json_sha256=c513fd6da7768a7444cdecea25797649c131efaa5b548335b10e07c24758c95b",
        "training_command_plan_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_acceptance_9270485_20260625T194804Z/training_command_plan.json",
        "training_command_plan_json_sha256=8051af1f8932c60b90a7f60686e7d127429e36b7a5acf67f2840d7044b805fd0",
        "source_summary_acceptance_status=fallback_risk_training_validated_dataset_summary_materializer_current_head_1b093c3_fixed_artifact_acceptance_passed",
        "preflight_commit=95215aba5bf2ce0eeb374d2e1d4e55e42d640fe6",
        "autodl_CAMP_HEAD=95215aba5bf2ce0eeb374d2e1d4e55e42d640fe6",
        "autodl_CAMP_origin_main=95215aba5bf2ce0eeb374d2e1d4e55e42d640fe6",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "preflight_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_sufficiency_preflight_acceptance_95215ab_20260625T195559Z",
        "preflight_exit=0",
        "preflight_json_sha256=b1ec5b1d5e3d895d7123dc08b86656bfd1901bd0fd0e5339b503aafa13b58252",
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
        "source_hash_validated_dataset=f2ff69df6286b5242b7b510263a5dcc194b8c3bbd43db22253688813eddd79fe",
        "source_hash_split_manifest=e0a4ec0623f5db0b868465249ce9615b06b86f6c91067702af3bee9fd700db1d",
        "source_hash_scale_manifest=92059b9c60e66c96db836821cb0060072402089b915e0bbd87240fc24c602567",
        "source_hash_fallback_master_config=c513fd6da7768a7444cdecea25797649c131efaa5b548335b10e07c24758c95b",
        "source_hash_training_command_plan=8051af1f8932c60b90a7f60686e7d127429e36b7a5acf67f2840d7044b805fd0",
        "fallback_only_master_verified=True",
        "score_k(w)=a_k^T w",
        "simplex_cvar_l2_convex=True",
        "training_sufficiency_preflight_passed=True",
        "training_command_authorization_required=True",
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
    tail = "\n".join(audit.splitlines()[-190:])

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_current_head_95215ab_fixed_artifact_acceptance_passed",
        "preflight_json_sha256=b1ec5b1d5e3d895d7123dc08b86656bfd1901bd0fd0e5339b503aafa13b58252",
        "training_sufficiency_preflight_passed=True",
        "ready_for_future_training_authorization=True",
        "training_authorized=False",
        "camp_retraining_authorized_now=False",
        "dp_modification_authorized=False",
    ]:
        assert needle in audit

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_command_authorization_only`"
    )
