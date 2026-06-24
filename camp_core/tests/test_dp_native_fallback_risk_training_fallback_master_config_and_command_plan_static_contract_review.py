from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_static_contract_review.md"
)
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_plan.md"
)


def _review() -> str:
    return REVIEW_DOC.read_text(encoding="utf-8")


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_static_review_records_inputs_and_plan_scope() -> None:
    review = _review()
    plan = _plan()

    for needle in [
        "fallback_master_config_and_command_plan_plan=docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_plan.md",
        "accepted_train_only_scale_manifest_sha256=9e76915d544a04bcea31380323027511293419ea98f3b24406f951e52982570b",
        "camp_head_at_review=06cd8c9ba317f231203743342c6b9d46bac21acf",
        "autodl_DP_HEAD_at_review=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "plan_scope_boundary_passed=True",
        "current_gate_writes_fallback_master_config=False",
        "current_gate_writes_training_command_plan=False",
        "current_gate_runs_training_sufficiency_preflight=False",
        "current_gate_trains_camp=False",
    ]:
        assert needle in review
        if needle in plan:
            assert needle in plan


def test_static_review_records_master_isolation_and_convex_boundary() -> None:
    text = _review()

    for needle in [
        "master_isolation_boundary_passed=True",
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
        "blocking_master_contract_findings=0",
    ]:
        assert needle in text


def test_static_review_records_dry_run_command_boundary() -> None:
    text = _review()

    for needle in [
        "dry_run_command_boundary_passed=True",
        "training_command_authorization=False",
        "training_execution_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "formal_seeds_11_12_13_authorized=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "post_training_nonpromotion_plan_required=True",
        "development_holdout_acceptance_gate_required=True",
        "blocking_command_contract_findings=0",
    ]:
        assert needle in text


def test_static_review_records_preflight_gap_and_non_training_decision() -> None:
    text = _review()

    for needle in [
        "preflight_gap_boundary_passed=True",
        "future_preflight_inputs_required=validated_dataset_summary_json,training_split_manifest_json,train_only_scale_manifest_json,fallback_master_config_json,training_command_plan_json",
        "validated_dataset_split_and_scale_ready=True",
        "fallback_master_config_ready=False",
        "training_command_plan_ready=False",
        "training_sufficiency_preflight_ready=False",
        "fallback_master_config_builder_authorized=False",
        "training_command_plan_builder_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "camp_retraining_authorized_now=False",
        "blocking_contract_findings=0",
    ]:
        assert needle in text


def test_static_review_forbids_training_dp_promotion_and_claims() -> None:
    text = _review()

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


def test_static_review_next_gate_is_implementation_authorization_only() -> None:
    text = _review()

    for needle in [
        "status=fallback_risk_training_fallback_master_config_and_command_plan_static_contract_review_passed",
        "passed=True",
        "static_contract_review_complete=True",
        "blocking_contract_findings=0",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_builder_implementation_authorization_only",
        "may only decide whether to authorize a minimal default-off builder",
        "must not implement builders",
        "must not run the sufficiency preflight",
        "must not train CAMP",
        "generate candidates",
        "modify Diffusion Planner",
    ]:
        assert needle in text
