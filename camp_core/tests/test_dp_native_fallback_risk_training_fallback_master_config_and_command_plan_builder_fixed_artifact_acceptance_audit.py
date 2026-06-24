from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_builder_fixed_artifact_acceptance_audit.md"
)


def _audit() -> str:
    return AUDIT_DOC.read_text(encoding="utf-8")


def test_acceptance_audit_records_fixed_artifact_inputs_and_output_hashes() -> None:
    text = _audit()

    for needle in [
        "source_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f632c44_20260624T133402Z/dataset.json",
        "expected_dataset_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "accepted_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_384c2b7_20260624T154419Z/split_manifest.json",
        "expected_split_manifest_sha256=a4b33c1c14b2ea96f1994e89245cfd27209e98049808fdfd3fbe6c8a732d34fd",
        "accepted_train_only_scale_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_builder_acceptance_6a069dd_20260625T000000Z/scale_manifest.json",
        "expected_scale_manifest_sha256=9e76915d544a04bcea31380323027511293419ea98f3b24406f951e52982570b",
        "builder_commit=3b919f19e04a8c11d288944a7e8527c139cca4e0",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "builder_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_training_fallback_master_config_and_command_plan_builder_acceptance_3b919f1_20260624T170753Z",
        "fallback_master_config_json_sha256=92f8273b814fd120be2d3cac5eca94dbd6be5403cf5045c3aa73eabb2e1e49c1",
        "training_command_plan_json_sha256=f7a2cbef8705d0a8bf0b2c6c7ef1e6c9a193c65bde31f22ed8db6368b5de0e13",
        "master_command_plan_md_sha256=a14244b6719d8d5942c9cfa2c9d763a9d4967fa5967b622dfc176757072f232e",
    ]:
        assert needle in text


def test_acceptance_audit_records_fallback_master_benders_contract() -> None:
    text = _audit()

    for needle in [
        "master_schema_version=dp_native_fallback_risk_fallback_master_config_v1",
        "master_fallback_only=True",
        "master_feasible_branch_records_allowed=False",
        "master_all_infeasible_records_added_to_feasible_training=False",
        "master_all_infeasible_records_relabelled_feasible=False",
        "master_hard_feasibility_relaxation_authorized=False",
        "master_feasible_ranking_master_change_authorized=False",
        "master_score_expression=score_k(w)=a_k^T w",
        "master_atoms_fixed_nonnegative=True",
        "master_fallback_label_is_deployed_atom=False",
        "master_margins_nonnegative=True",
        "master_simplex_cvar_l2_convex=True",
        "master_atom_schema_version=dp_camp_v10_14d",
        "master_atom_count=14",
        "master_source_dataset_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "master_source_split_manifest_sha256=a4b33c1c14b2ea96f1994e89245cfd27209e98049808fdfd3fbe6c8a732d34fd",
        "master_source_scale_manifest_sha256=9e76915d544a04bcea31380323027511293419ea98f3b24406f951e52982570b",
    ]:
        assert needle in text


def test_acceptance_audit_records_dry_run_command_plan_boundaries() -> None:
    text = _audit()

    for needle in [
        "command_schema_version=dp_native_fallback_risk_training_command_plan_v1",
        "command_training_command_authorization=False",
        "command_training_execution_authorized=False",
        "command_training_authorized=False",
        "command_post_training_nonpromotion_plan_required=True",
        "command_development_holdout_acceptance_gate_required=True",
        "command_camp_retraining_authorized=False",
        "command_camp_training_authorized=False",
        "command_fallback_risk_training_authorized_now=False",
        "command_candidate_generation_authorized=False",
        "command_dp_modification_authorized=False",
        "command_selector_promotion_authorized=False",
        "command_atom_promotion_authorized=False",
        "command_safety_benefit_claim_authorized=False",
        "command_camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text


def test_acceptance_audit_marks_outputs_ready_for_preflight_without_running_it() -> None:
    text = _audit()

    for needle in [
        "fixed_artifact_acceptance_passed=True",
        "blocking_acceptance_findings=0",
        "fallback_master_config_ready=True",
        "training_command_plan_ready=True",
        "training_sufficiency_preflight_input_set_ready=True",
        "training_sufficiency_preflight_executed=False",
        "training_sufficiency_preflight_ready=False",
        "training_sufficiency_preflight_execution_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "fixed_15_record_artifact_training_sufficiency_claim=False",
        "local_target_pytest=5 passed",
        "local_fallback_risk_related_pytest=320 passed",
        "autodl_target_pytest=5 passed",
        "autodl_fallback_risk_related_pytest=320 passed",
    ]:
        assert needle in text


def test_acceptance_audit_keeps_forbidden_boundaries_and_next_gate() -> None:
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
        "status=fallback_risk_training_fallback_master_config_and_command_plan_builder_fixed_artifact_acceptance_passed",
        "fixed_artifact_acceptance_audit_complete=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_fixed_artifact_acceptance_audit_only",
        "may only run the already implemented default-off read-only preflight",
        "must not train CAMP",
        "generate candidates",
        "modify Diffusion Planner",
        "promote a selector or atom",
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
