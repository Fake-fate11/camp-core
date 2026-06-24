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
        "validated_dataset_summary_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_record_identity_acceptance_e9ae842_20260624T222659Z/validated_dataset_summary.json",
        "validated_dataset_summary_json_sha256=320304655bb1433076d6269333ce7ec728ce74a04f5f04fc9e63fff5158c2188",
        "validated_dataset_summary_payload_sha256=8e7d42e2d1319dc2a479903d7b1be5a463f2d74fe733b523fdbac09bf90bd9b9",
        "training_split_manifest_json_sha256=9eb6f64a392a8ba1c6037c9dc8389ad9459615c039ad2b3426747785b75e5a78",
        "train_only_scale_manifest_json_sha256=d4205878c3af549ed86a778236500997df302272ab671bfcb60bc5f18b03b812",
        "fallback_master_config_json_sha256=3af141fa2e1374d10f7381bebeeabe0aa85bdd5b9f59fc38c91c080aec1b33d4",
        "training_command_plan_json_sha256=1d10adb5484ae286f04b008b6b6acbc18cba4ec09fdc644ebd490752b5d067ef",
        "preflight_commit=f2c4eb4a3f23b954010d2a9ecc8fa193072e62e5",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "preflight_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_sufficiency_preflight_record_identity_acceptance_f2c4eb4_20260624T224349Z",
        "preflight_exit=0",
        "preflight_json_sha256=c44b932ecf518a9ed69979bf9b2efb40020b5ec3a0e4bd221037c5eb9aaca7e3",
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
        "source_hash_validated_dataset=320304655bb1433076d6269333ce7ec728ce74a04f5f04fc9e63fff5158c2188",
        "source_hash_split_manifest=9eb6f64a392a8ba1c6037c9dc8389ad9459615c039ad2b3426747785b75e5a78",
        "source_hash_scale_manifest=d4205878c3af549ed86a778236500997df302272ab671bfcb60bc5f18b03b812",
        "source_hash_fallback_master_config=3af141fa2e1374d10f7381bebeeabe0aa85bdd5b9f59fc38c91c080aec1b33d4",
        "source_hash_training_command_plan=1d10adb5484ae286f04b008b6b6acbc18cba4ec09fdc644ebd490752b5d067ef",
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
        "local_preflight_acceptance_rerun_pytest=6 passed",
        "local_preflight_pytest=5 passed",
        "local_related_target_pytest=105 passed",
        "autodl_py_compile_exit=0",
        "autodl_preflight_acceptance_rerun_pytest=6 passed",
        "autodl_preflight_pytest=5 passed",
        "autodl_related_target_pytest=105 passed",
        "autodl_git_diff_check_exit=0",
        "status=fallback_risk_training_sufficiency_preflight_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_passed",
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
        "status=fallback_risk_training_sufficiency_preflight_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_passed",
        "training_sufficiency_preflight_passed=True",
        "ready_for_future_training_authorization=True",
        "training_authorized=False",
        "camp_retraining_authorized_now=False",
        "dp_modification_authorized=False",
    ]:
        assert needle in audit

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_unit_tests_plan_only`"
    )
