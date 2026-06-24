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
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_record_identity_acceptance_7ef98c9_20260624T215739Z/dataset.json",
        "expected_dataset_sha256=8e7d42e2d1319dc2a479903d7b1be5a463f2d74fe733b523fdbac09bf90bd9b9",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_record_identity_acceptance_7891f2e_20260624T220443Z/split_manifest.json",
        "expected_split_manifest_sha256=9eb6f64a392a8ba1c6037c9dc8389ad9459615c039ad2b3426747785b75e5a78",
        "train_only_scale_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_record_identity_acceptance_201c872_20260624T221156Z/scale_manifest.json",
        "expected_scale_manifest_sha256=d4205878c3af549ed86a778236500997df302272ab671bfcb60bc5f18b03b812",
        "source_scale_manifest_acceptance_status=fallback_risk_training_train_only_scale_manifest_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_passed",
        "builder_commit=b363750a032a865c34d0faf1074bdb2cb4bbf656",
        "autodl_CAMP_HEAD=b363750a032a865c34d0faf1074bdb2cb4bbf656",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_master_command_record_identity_acceptance_b363750_20260624T222029Z",
        "fallback_master_config_json_sha256=3af141fa2e1374d10f7381bebeeabe0aa85bdd5b9f59fc38c91c080aec1b33d4",
        "training_command_plan_json_sha256=1d10adb5484ae286f04b008b6b6acbc18cba4ec09fdc644ebd490752b5d067ef",
        "master_command_md_sha256=a14244b6719d8d5942c9cfa2c9d763a9d4967fa5967b622dfc176757072f232e",
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
        "training_command_plan_ready=True",
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
        "local_master_command_builder_pytest=6 passed",
        "local_related_target_pytest=89 passed",
        "autodl_verified_camp_head=e2d8afffffdf0594d20c48b506d9651b2d585d37",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=89 passed",
        "autodl_git_diff_check_exit=0",
        "status=fallback_risk_training_fallback_master_config_and_command_plan_record_identity_hash_remediation_fixed_artifact_acceptance_rerun_passed",
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
        "status=fallback_risk_training_sufficiency_preflight_record_identity_hash_remediation_implemented",
        "old_expected_validated_dataset_sha_rejected=True",
        "new_expected_validated_dataset_sha_accepted_by_unit_contract=True",
        "training_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in audit

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_unit_tests_plan_only`"
    )
