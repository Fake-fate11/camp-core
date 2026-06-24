from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_plan.md"
)


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_plan_records_fixed_artifact_inputs_and_remaining_gap() -> None:
    text = _plan()

    for needle in [
        "validated_fallback_dataset_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_data_builder_acceptance_f632c44_20260624T133402Z/dataset.json",
        "validated_fallback_dataset_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "accepted_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_384c2b7_20260624T154419Z/split_manifest.json",
        "accepted_split_manifest_sha256=a4b33c1c14b2ea96f1994e89245cfd27209e98049808fdfd3fbe6c8a732d34fd",
        "accepted_train_only_scale_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_train_only_scale_manifest_builder_acceptance_6a069dd_20260625T000000Z/scale_manifest.json",
        "accepted_train_only_scale_manifest_sha256=9e76915d544a04bcea31380323027511293419ea98f3b24406f951e52982570b",
        "fallback_master_config_ready=False",
        "training_command_plan_ready=False",
        "training_sufficiency_preflight_ready=False",
    ]:
        assert needle in text


def test_plan_defines_fallback_only_master_config_contract() -> None:
    text = _plan()

    for needle in [
        "fallback_master_config_plan_complete=True",
        "fallback_only=True",
        "feasible_branch_records_allowed=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "all_infeasible_records_relabelled_feasible=False",
        "hard_feasibility_relaxation_authorized=False",
        "feasible_ranking_master_change_authorized=False",
        "score_expression=score_k(w)=a_k^T w",
        "atoms_fixed_nonnegative=True",
        "fallback_label_is_deployed_atom=False",
        "margins_nonnegative=True",
        "simplex_cvar_l2_convex=True",
        "new_atom_authorized_now=False",
    ]:
        assert needle in text


def test_plan_defines_dry_run_command_plan_contract() -> None:
    text = _plan()

    for needle in [
        "dry_run_training_command_plan_complete=True",
        "training_command_authorization=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "formal_seeds_11_12_13_authorized=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "reference_blend_authorized=False",
        "guidance_authorized=False",
        "postprocess_postselection_authorized=False",
        "closed_loop_outcome_online_input_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "post_training_nonpromotion_plan_required=True",
        "development_holdout_acceptance_gate_required=True",
    ]:
        assert needle in text


def test_plan_preserves_preflight_and_training_boundaries() -> None:
    text = _plan()

    for needle in [
        "current_gate_writes_fallback_master_config=False",
        "current_gate_writes_training_command_plan=False",
        "current_gate_runs_training_sufficiency_preflight=False",
        "current_gate_trains_camp=False",
        "future_preflight_inputs_required=validated_dataset_summary_json,training_split_manifest_json,train_only_scale_manifest_json,fallback_master_config_json,training_command_plan_json",
        "fallback_master_config_builder_authorized=False",
        "training_command_plan_builder_authorized=False",
        "training_execution_authorized=False",
        "checkpoint_nonpromotion_plan_required=True",
        "development_holdout_acceptance_required=True",
        "fallback_dataset_training_sufficiency_claim=False",
    ]:
        assert needle in text


def test_plan_forbids_training_dp_promotion_and_claims() -> None:
    text = _plan()

    for needle in [
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "Full36_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
    ]:
        assert needle in text

    for forbidden in [
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "training_execution_authorized=True",
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "fallback_dataset_training_sufficiency_claim=True",
    ]:
        assert forbidden not in text


def test_plan_next_gate_is_static_contract_review_only() -> None:
    text = _plan()

    for needle in [
        "status=fallback_risk_training_fallback_master_config_and_command_plan_plan_ready",
        "passed=True",
        "fallback_master_config_and_command_plan_plan_complete=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_static_contract_review_only",
        "may only statically review this fallback-only master config and dry-run command plan",
        "must not implement builders",
        "must not train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
    ]:
        assert needle in text
