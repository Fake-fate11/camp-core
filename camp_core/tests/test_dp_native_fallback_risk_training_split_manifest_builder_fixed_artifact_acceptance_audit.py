from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_audit.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _audit() -> str:
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_acceptance_audit_records_current_fixed_artifact_inputs_and_outputs() -> None:
    text = _audit()

    for needle in [
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f632c44_20260624T133402Z/dataset.json",
        "expected_dataset_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "validator_output_json_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "builder_commit=cdeef56a6502504aded815866d2a95d248fe2cc6",
        "autodl_CAMP_HEAD=cdeef56a6502504aded815866d2a95d248fe2cc6",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "record_identity_hash_required_input_field=True",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_cdeef56_20260624T212247Z",
        "split_manifest_json_sha256=35fc5a3d3f648177c9da0db24f6c9205ad9bfa0ecbe4fcd3dc5008d12e27f8c3",
        "split_manifest_md_sha256=3bd8c173c0745673aa6f3a6ce3a39524631450b9535c1904d919b38cbe5c82f9",
        "builder_exit=1",
        "latest_source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_6adb800_20260625T020016Z/dataset.json",
        "latest_expected_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "latest_validator_output_json_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "latest_builder_commit=b10a5b6fca6aa82b70dfe0710e295ea9ed445457",
        "latest_autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_b10a5b6_20260625T040200Z",
        "latest_split_manifest_json_sha256=b6f8cdcc0e353e1efdc81c62d0e81aa1f4b0679270f1bb211879ac03adce8079",
        "latest_split_manifest_md_sha256=60ef091344704d9edeec48820d2d1888cb0110ba6b9a35e6de6ad49ee9fe2aeb",
        "latest_builder_exit=0",
    ]:
        assert needle in text


def test_current_head_def7dde_fixed_artifact_acceptance_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_head_def7dde_passed",
        "acceptance_base_head=def7dde5f8f3ae157c9b2e82415f4cd1c75a0ba5",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_e35f1e4_20260625T132102Z/dataset.json",
        "expected_dataset_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "validator_output_json_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "builder_commit=def7dde5f8f3ae157c9b2e82415f4cd1c75a0ba5",
        "autodl_CAMP_HEAD=def7dde5f8f3ae157c9b2e82415f4cd1c75a0ba5",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "post_static_contract_status=fallback_risk_training_split_manifest_builder_post_implementation_static_contract_head_5455e4d_revalidated",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_def7dde_20260625T160330Z",
        "split_manifest_json_sha256=13fa6b86d2fcebbb3ecbb675daefa7409f1f427900896307474d2d1dc4f6e773",
        "split_manifest_md_sha256=60ef091344704d9edeec48820d2d1888cb0110ba6b9a35e6de6ad49ee9fe2aeb",
        "builder_stdout_log_sha256=c825f1298c9660dafbe2fdad70f118575ee2a072b66cf44371332d0090c99d47",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
        "observed_status=dp_native_fallback_risk_training_split_manifest_builder_complete",
        "observed_passed=True",
        "observed_errors=[]",
        "observed_accepted_records=15",
        "observed_training_records=13",
        "observed_validation_records=2",
        "observed_record_assignments=15",
        "observed_training_authorized=False",
        "observed_fallback_dataset_training_sufficiency_claim=False",
        "observed_candidate_generation_authorized=False",
        "observed_dp_modification_authorized=False",
        "fixed_artifact_acceptance_passed=True",
        "blocking_acceptance_findings=0",
        "training_split_manifest_ready_for_preflight=True",
        "local_acceptance_target_pytest=7 passed",
    ]:
        assert needle in text


def test_current_head_6d1fa5e_fixed_artifact_acceptance_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_head_6d1fa5e_passed",
        "acceptance_base_head=6d1fa5e1bc106153cb413bc9c80cdf6f0d03bb04",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_bbba35b_20260625T174901Z/dataset.json",
        "expected_dataset_sha256=682d432f742d4ab68a262cf70955981bc1562cf1dbcf2ec094984a12fcd11498",
        "validator_output_json_sha256=bfe5d031be232c13188e19ae19692a560bb424090fc446253edf015c50c821c9",
        "builder_commit=6d1fa5e1bc106153cb413bc9c80cdf6f0d03bb04",
        "autodl_CAMP_HEAD=6d1fa5e1bc106153cb413bc9c80cdf6f0d03bb04",
        "autodl_CAMP_origin_main=6d1fa5e1bc106153cb413bc9c80cdf6f0d03bb04",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "post_static_contract_status=fallback_risk_training_split_manifest_builder_post_implementation_static_contract_head_fabbd5d_revalidated",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_6d1fa5e_20260625T193828Z",
        "split_manifest_json_sha256=e0a4ec0623f5db0b868465249ce9615b06b86f6c91067702af3bee9fd700db1d",
        "split_manifest_md_sha256=60ef091344704d9edeec48820d2d1888cb0110ba6b9a35e6de6ad49ee9fe2aeb",
        "builder_stdout_log_sha256=c825f1298c9660dafbe2fdad70f118575ee2a072b66cf44371332d0090c99d47",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
        "observed_status=dp_native_fallback_risk_training_split_manifest_builder_complete",
        "observed_passed=True",
        "observed_errors=[]",
        "observed_accepted_records=15",
        "observed_training_records=13",
        "observed_validation_records=2",
        "observed_record_assignments=15",
        "observed_training_authorized=False",
        "observed_fallback_dataset_training_sufficiency_claim=False",
        "observed_candidate_generation_authorized=False",
        "observed_dp_modification_authorized=False",
        "fixed_artifact_acceptance_passed=True",
        "blocking_acceptance_findings=0",
        "training_split_manifest_ready_for_preflight=True",
        "local_acceptance_target_pytest=8 passed",
    ]:
        assert needle in text


def test_current_head_e4f3831_fixed_artifact_acceptance_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_head_e4f3831_passed",
        "acceptance_base_head=e4f3831b6031c726723075bc2eaa59fb728c6746",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_4751222_20260625T213641Z/dataset.json",
        "expected_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "validator_output_json_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "builder_commit=e4f3831b6031c726723075bc2eaa59fb728c6746",
        "autodl_CAMP_HEAD=e4f3831b6031c726723075bc2eaa59fb728c6746",
        "autodl_CAMP_origin_main=e4f3831b6031c726723075bc2eaa59fb728c6746",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "post_static_contract_status=fallback_risk_training_split_manifest_builder_post_implementation_static_contract_autodl_sync_verified",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_e4f3831_20260626T012252Z",
        "split_manifest_json_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "split_manifest_md_sha256=60ef091344704d9edeec48820d2d1888cb0110ba6b9a35e6de6ad49ee9fe2aeb",
        "builder_stdout_log_sha256=c825f1298c9660dafbe2fdad70f118575ee2a072b66cf44371332d0090c99d47",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
        "observed_status=dp_native_fallback_risk_training_split_manifest_builder_complete",
        "observed_passed=True",
        "observed_errors=[]",
        "observed_accepted_records=15",
        "observed_training_records=13",
        "observed_validation_records=2",
        "observed_record_assignments=15",
        "observed_training_authorized=False",
        "observed_fallback_dataset_training_sufficiency_claim=False",
        "observed_candidate_generation_authorized=False",
        "observed_dp_modification_authorized=False",
        "fixed_artifact_acceptance_passed=True",
        "blocking_acceptance_findings=0",
        "training_split_manifest_ready_for_preflight=True",
        "local_acceptance_target_pytest=9 passed",
        "local_related_target_pytest=46 passed",
    ]:
        assert needle in text


def test_current_head_6b43925_fixed_artifact_acceptance_is_pinned() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_current_head_6b43925_passed",
        "acceptance_base_head=6b43925fea4b5966d9a5f8893d064f072c9b7d17",
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_4751222_20260625T213641Z/dataset.json",
        "expected_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "validator_output_json_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "builder_commit=6b43925fea4b5966d9a5f8893d064f072c9b7d17",
        "autodl_CAMP_HEAD=6b43925fea4b5966d9a5f8893d064f072c9b7d17",
        "autodl_CAMP_origin_main=6b43925fea4b5966d9a5f8893d064f072c9b7d17",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "post_static_contract_status=fallback_risk_training_split_manifest_builder_post_implementation_static_contract_current_head_ffb3695_autodl_sync_verified",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_6b43925_20260626T051552Z",
        "split_manifest_json_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "split_manifest_md_sha256=60ef091344704d9edeec48820d2d1888cb0110ba6b9a35e6de6ad49ee9fe2aeb",
        "builder_stdout_log_sha256=c825f1298c9660dafbe2fdad70f118575ee2a072b66cf44371332d0090c99d47",
        "builder_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "builder_exit=0",
        "observed_status=dp_native_fallback_risk_training_split_manifest_builder_complete",
        "observed_passed=True",
        "observed_errors=[]",
        "observed_accepted_records=15",
        "observed_training_records=13",
        "observed_validation_records=2",
        "observed_record_assignments=15",
        "observed_training_authorized=False",
        "observed_fallback_dataset_training_sufficiency_claim=False",
        "observed_candidate_generation_authorized=False",
        "observed_dp_modification_authorized=False",
        "fixed_artifact_acceptance_passed=True",
        "blocking_acceptance_findings=0",
        "manifest_accepted_for_preflight=True",
        "training_split_manifest_ready_for_preflight=True",
        "fixed_15_record_artifact_training_sufficiency_claim=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "local_acceptance_target_pytest=10 passed",
        "local_related_target_pytest=49 passed",
    ]:
        assert needle in text


def test_acceptance_audit_records_missing_record_identity_rejection() -> None:
    text = _audit()

    for needle in [
        "schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "split_policy=sha256(record_identity_hash + split_salt)",
        "status=dp_native_fallback_risk_training_split_manifest_builder_rejected",
        "passed=False",
        "errors_count=15",
        "errors_all_record_identity_hash_missing=True",
        "first_error=record_0:record_identity_hash_missing",
        "last_error=record_9:record_identity_hash_missing",
        "accepted_records=0",
        "training_records=0",
        "validation_records=0",
        "record_assignments=0",
        "split_manifest_written=False",
        "ready_for_future_preflight=False",
        "latest_schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "latest_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "latest_validator_output_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "latest_status=dp_native_fallback_risk_training_split_manifest_builder_complete",
        "latest_passed=True",
        "latest_errors=[]",
        "latest_accepted_records=15",
        "latest_training_records=13",
        "latest_validation_records=2",
        "latest_record_assignments=15",
        "latest_training_authorized=False",
        "latest_fallback_dataset_training_sufficiency_claim=False",
        "latest_candidate_generation_authorized=False",
        "latest_dp_modification_authorized=False",
    ]:
        assert needle in text


def test_acceptance_audit_identifies_upstream_record_identity_remediation() -> None:
    text = _audit()

    for needle in [
        "fixed_artifact_acceptance_passed=False",
        "blocking_acceptance_findings=1",
        "legacy_final_decision_flag_compatibility_issue=False",
        "record_identity_hash_compatibility_issue=True",
        "source_training_dataset_missing_record_identity_hash=True",
        "missing_record_identity_hash_records=15",
        "dataset_sha256_matched=True",
        "builder_failed_closed=True",
        "identity_hardening_effective=True",
        "manifest_accepted_for_preflight=False",
        "training_split_manifest_ready_for_preflight=False",
        "upstream_training_data_record_identity_remediation_required=True",
        "local_target_pytest=6 passed",
        "local_related_target_pytest=22 passed",
        "autodl_verified_camp_head=22ccb10bbd8aeaf94e7c62c1a83c16ce4f633524",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=22 passed",
        "autodl_git_diff_check_exit=0",
        "latest_fixed_artifact_acceptance_passed=True",
        "latest_blocking_acceptance_findings=0",
        "latest_record_identity_hash_compatibility_issue=False",
        "latest_missing_record_identity_hash_records=0",
        "latest_manifest_accepted_for_preflight=True",
        "latest_training_split_manifest_ready_for_preflight=True",
        "latest_fixed_15_record_artifact_training_sufficiency_claim=False",
        "latest_fallback_risk_training_authorized_now=False",
        "latest_camp_retraining_authorized_now=False",
        "latest_fallback_dataset_training_sufficiency_claim=False",
        "latest_autodl_builder_exit=0",
        "latest_autodl_output_json_sha256=b6f8cdcc0e353e1efdc81c62d0e81aa1f4b0679270f1bb211879ac03adce8079",
    ]:
        assert needle in text


def test_acceptance_audit_keeps_training_dp_and_claims_forbidden() -> None:
    text = _audit()

    for needle in [
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_dataset_training_sufficiency_claim=False",
    ]:
        assert needle in text

    for forbidden in [
        "candidate_generation_authorized=True",
        "camp_training_authorized=True",
        "dp_modification_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in text


def test_acceptance_audit_next_gate_is_record_identity_authorization_only() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_rejected_missing_record_identity_hash",
        "latest_status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_current_head_passed",
        "fixed_artifact_acceptance_audit_complete=True",
        "latest_fixed_artifact_acceptance_audit_complete=True",
        "training_split_manifest_ready_for_preflight=False",
        "latest_training_split_manifest_ready_for_preflight=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_record_identity_hash_remediation_authorization_only",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only",
        "may only decide whether to authorize a minimal default-off",
        "must not run",
        "replay",
        "generate candidates",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text


def test_iteration_audit_tail_records_current_acceptance_audit_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-190:])

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_head_0e302e1_tail_authority",
        "source_acceptance_status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_head_0e302e1_passed",
        "source_split_manifest_json_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "source_observed_training_records=13",
        "source_observed_validation_records=2",
        "camp_retraining_authorized_now=False",
        "local_related_target_pytest=30 passed",
    ]:
        assert needle in tail

    assert (
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_audit_only"
        in tail
    )
