from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_fixed_artifact_acceptance_audit.md"
)


def _audit() -> str:
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_preflight_acceptance_records_fixed_inputs_and_output_hashes() -> None:
    text = _audit()

    for needle in [
        "validated_dataset_summary_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_validated_dataset_summary_materializer_acceptance_8c68458_20260624T173456Z/validated_dataset_summary.json",
        "validated_dataset_summary_json_sha256=efb1f2c8c8629c81e48b68ff9ea543082e915aba54a4e772598ac4340b97fd57",
        "training_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_384c2b7_20260624T154419Z/split_manifest.json",
        "training_split_manifest_json_sha256=a4b33c1c14b2ea96f1994e89245cfd27209e98049808fdfd3fbe6c8a732d34fd",
        "train_only_scale_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_builder_acceptance_6a069dd_20260625T000000Z/scale_manifest.json",
        "train_only_scale_manifest_json_sha256=9e76915d544a04bcea31380323027511293419ea98f3b24406f951e52982570b",
        "fallback_master_config_json_sha256=92f8273b814fd120be2d3cac5eca94dbd6be5403cf5045c3aa73eabb2e1e49c1",
        "training_command_plan_json_sha256=f7a2cbef8705d0a8bf0b2c6c7ef1e6c9a193c65bde31f22ed8db6368b5de0e13",
        "preflight_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_sufficiency_preflight_acceptance_d0ae79c_20260624T173944Z",
        "preflight_json_sha256=04ada84f0bfe97108049c491016a62718152f2ce8cd94f92734732d6c1a2e568",
        "preflight_md_sha256=e596460039c684007b81ca61787eb5969378d2c238e25d4cc3ed8e740e4178f9",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    ]:
        assert needle in text


def test_preflight_acceptance_records_complete_ready_result() -> None:
    text = _audit()

    for needle in [
        "schema_version=dp_native_fallback_risk_training_sufficiency_preflight_v1",
        "status=dp_native_fallback_risk_training_sufficiency_preflight_complete",
        "passed=True",
        "enabled=True",
        "errors=[]",
        "preflight_output_written=True",
        "ready_for_future_training_authorization=True",
        "training_sufficiency_preflight_passed=True",
        "training_sufficiency_preflight_acceptance_passed=True",
        "training_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "camp_retraining_authorized_now=False",
        "fallback_risk_training_authorized_now=False",
    ]:
        assert needle in text


def test_preflight_acceptance_records_source_hash_integrity() -> None:
    text = _audit()

    for needle in [
        "source_hash_validated_dataset=efb1f2c8c8629c81e48b68ff9ea543082e915aba54a4e772598ac4340b97fd57",
        "source_hash_split_manifest=a4b33c1c14b2ea96f1994e89245cfd27209e98049808fdfd3fbe6c8a732d34fd",
        "source_hash_scale_manifest=9e76915d544a04bcea31380323027511293419ea98f3b24406f951e52982570b",
        "source_hash_fallback_master_config=92f8273b814fd120be2d3cac5eca94dbd6be5403cf5045c3aa73eabb2e1e49c1",
        "source_hash_training_command_plan=f7a2cbef8705d0a8bf0b2c6c7ef1e6c9a193c65bde31f22ed8db6368b5de0e13",
        "fallback_only_master_verified=True",
        "score_k(w)=a_k^T w",
        "simplex_cvar_l2_convex=True",
        "fixed_15_record_artifact_training_sufficiency_claim=False",
    ]:
        assert needle in text


def test_preflight_acceptance_keeps_forbidden_boundaries() -> None:
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


def test_preflight_acceptance_next_gate_is_training_command_authorization() -> None:
    text = _audit()

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_fixed_artifact_acceptance_passed",
        "fixed_artifact_acceptance_audit_complete=True",
        "blocking_acceptance_findings=0",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_command_authorization_only",
        "may only decide whether to authorize a non-promotion fallback-risk CAMP training command",
        "must not execute training",
        "modify Diffusion Planner",
        "promote a selector or atom",
    ]:
        assert needle in text
