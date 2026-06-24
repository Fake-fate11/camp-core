from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_validated_dataset_summary_materializer_fixed_artifact_acceptance_audit.md"
)


def _audit() -> str:
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_acceptance_audit_records_fixed_inputs_and_output_hashes() -> None:
    text = _audit()

    for needle in [
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f632c44_20260624T133402Z/dataset.json",
        "expected_dataset_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "source_validator_output_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_validator_acceptance_f4ea755_20260624T142300Z/validation.json",
        "expected_validator_output_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "builder_commit=8c68458e2ca48d62c75e6bc8d28f6ca2b719e701",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_materializer_acceptance_8c68458_20260624T173456Z",
        "validated_dataset_summary_json_sha256=efb1f2c8c8629c81e48b68ff9ea543082e915aba54a4e772598ac4340b97fd57",
        "validated_dataset_summary_md_sha256=e1c75b4c6bc0b9626f44fd1cbdee29be8418d4660b8acf7e0430bbc7b0a05426",
    ]:
        assert needle in text


def test_acceptance_audit_records_complete_materializer_result() -> None:
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


def test_acceptance_audit_records_preflight_summary_shape() -> None:
    text = _audit()

    for needle in [
        "summary_schema_version=dp_native_fallback_risk_validated_dataset_summary_v1",
        "summary_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "summary_records=15",
        "summary_validator_status=dp_native_fallback_risk_training_data_validator_complete",
        "summary_validator_passed=True",
        "summary_training_sufficiency_claim=False",
        "summary_deployable_checkpoint_claim=False",
        "summary_source_validator_output_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "validated_dataset_summary_ready_for_preflight=True",
        "training_sufficiency_preflight_input_set_ready=True",
        "training_sufficiency_preflight_executed=False",
        "training_sufficiency_preflight_ready=False",
        "fixed_15_record_artifact_training_sufficiency_claim=False",
        "local_target_pytest=5 passed",
        "local_fallback_risk_related_pytest=339 passed",
        "autodl_target_pytest=5 passed",
        "autodl_fallback_risk_related_pytest=339 passed",
    ]:
        assert needle in text


def test_acceptance_audit_keeps_forbidden_boundaries() -> None:
    text = _audit()

    for needle in [
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "Full36_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "reference_blend_authorized=False",
        "guidance_authorized=False",
        "postprocess_postselection_authorized=False",
        "closed_loop_outcome_online_input_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "feasible_ranking_master_change_authorized=False",
        "hard_feasibility_relaxation_authorized=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
    ]:
        assert needle in text

    for forbidden in [
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


def test_acceptance_audit_next_gate_is_preflight_acceptance_only() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_validated_dataset_summary_materializer_fixed_artifact_acceptance_passed",
        "fixed_artifact_acceptance_audit_complete=True",
        "fixed_artifact_acceptance_passed=True",
        "blocking_acceptance_findings=0",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_fixed_artifact_acceptance_audit_only",
        "may only run the already implemented default-off read-only preflight",
        "must not train CAMP",
        "generate candidates",
        "modify Diffusion Planner",
        "promote a selector or atom",
    ]:
        assert needle in text
