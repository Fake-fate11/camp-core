from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_rerun_audit.md"
)


def _audit() -> str:
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_acceptance_rerun_audit_records_inputs_and_output_hashes() -> None:
    text = _audit()

    for needle in [
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f632c44_20260624T133402Z/dataset.json",
        "expected_dataset_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "validator_output_json_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "builder_commit=384c2b7998864594a97b900be3e687bfaf03a2a1",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_384c2b7_20260624T154419Z",
        "split_manifest_json_sha256=a4b33c1c14b2ea96f1994e89245cfd27209e98049808fdfd3fbe6c8a732d34fd",
        "split_manifest_md_sha256=60ef091344704d9edeec48820d2d1888cb0110ba6b9a35e6de6ad49ee9fe2aeb",
    ]:
        assert needle in text


def test_acceptance_rerun_audit_records_complete_split_manifest() -> None:
    text = _audit()

    for needle in [
        "schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "split_policy=sha256(record_identity_hash + split_salt)",
        "split_salt=fallback_risk_training_split_v1",
        "status=dp_native_fallback_risk_training_split_manifest_builder_complete",
        "passed=True",
        "accepted_records=15",
        "training_records=13",
        "validation_records=2",
        "training_groups_disjoint_validation=True",
        "record_assignments=15",
        "errors=[]",
    ]:
        assert needle in text


def test_acceptance_rerun_audit_records_scope_and_no_training_claim() -> None:
    text = _audit()

    for needle in [
        "fixed_artifact_acceptance_passed=True",
        "blocking_acceptance_findings=0",
        "legacy_final_decision_flag_compatibility_issue_resolved=True",
        "training_split_manifest_ready_for_preflight=True",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "fixed_15_record_artifact_training_sufficiency_claim=False",
        "local_target_pytest=5 passed",
        "local_fallback_risk_related_pytest=240 passed",
    ]:
        assert needle in text


def test_acceptance_rerun_audit_keeps_forbidden_boundaries() -> None:
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
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
    ]:
        assert needle in text


def test_acceptance_rerun_audit_next_gate_is_train_only_scale_manifest_plan() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_passed_after_legacy_decision_flag_remediation",
        "fixed_artifact_acceptance_audit_complete=True",
        "fixed_artifact_acceptance_passed=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_plan_only",
        "may only plan the train-only atom scale manifest",
        "must not train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
    ]:
        assert needle in text
