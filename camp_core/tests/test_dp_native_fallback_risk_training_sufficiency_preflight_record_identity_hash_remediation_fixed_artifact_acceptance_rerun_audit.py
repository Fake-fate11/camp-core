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
        "status=fallback_risk_training_sufficiency_preflight_current_head_9abb833_fixed_artifact_acceptance_passed",
        "preflight_json_sha256=22ad4437d0cfa2eea0884d340c9c0fd6073824ce86bbf263d6f4e3e4bff6d51b",
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
