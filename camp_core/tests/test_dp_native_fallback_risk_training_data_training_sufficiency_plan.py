from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_plan.md"
)


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_training_sufficiency_plan_records_validated_dataset_but_no_sufficiency_claim() -> None:
    text = _plan()

    for needle in [
        "validated_fallback_records=15",
        "validated_fallback_dataset_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "validator_output_json_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "fixed_artifact_training_sufficiency_claim=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "fallback_risk_training_authorized_now=False",
    ]:
        assert needle in text


def test_training_sufficiency_plan_isolates_fallback_master() -> None:
    text = _plan()

    for needle in [
        "fallback_master_isolated_from_feasible_master_required=True",
        "feasible_branch_records_allowed_in_fallback_master=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "all_infeasible_records_relabelled_feasible=False",
        "hard_feasibility_relaxation_authorized=False",
        "feasible_ranking_master_change_authorized=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
    ]:
        assert needle in text


def test_training_sufficiency_plan_preserves_convex_fixed_candidate_boundary() -> None:
    text = _plan()

    for needle in [
        "score_k(w)=a_k^T w",
        "a_k_fixed_before_weight_optimization=True",
        "a_k_nonnegative_benders_compatible_atoms_only=True",
        "fallback_label_is_not_a_deployed_atom=True",
        "new_atom_authorized_now=False",
        "q_i(w)=max(0,max_k m_ik+(a_i,o_i-a_i,k)^T w)",
        "margin_ik_nonnegative=True",
        "simplex_master_convex_if_later_authorized=True",
        "cvar_master_convex_if_later_authorized=True",
        "l2_regularized_master_convex_if_later_authorized=True",
    ]:
        assert needle in text


def test_training_sufficiency_plan_requires_split_scale_and_formal_seed_exclusion() -> None:
    text = _plan()

    for needle in [
        "training_validation_split_predeclaration_required=True",
        "validation_groups_disjoint_from_training_groups_required=True",
        "formal_seeds_11_12_13_excluded_required=True",
        "formal_eval_data_excluded_from_scale_fit_required=True",
        "scale_fit_training_groups_only_required=True",
        "strict_positive_atom_scales_required=True",
        "current_gate_predeclares_split=False",
        "current_gate_fits_scales=False",
        "current_gate_trains_weights=False",
    ]:
        assert needle in text


def test_training_sufficiency_plan_lists_missing_retraining_prerequisites() -> None:
    text = _plan()

    for needle in [
        "missing_training_split_manifest=True",
        "missing_train_only_scale_manifest=True",
        "missing_fallback_only_master_config=True",
        "missing_training_command_authorization=True",
        "missing_checkpoint_nonpromotion_plan=True",
        "missing_development_holdout_acceptance_gate=True",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in text


def test_training_sufficiency_plan_forbids_execution_and_sets_static_review_next() -> None:
    text = _plan()

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
        "status=fallback_risk_training_data_training_sufficiency_plan_ready",
        "training_sufficiency_plan_complete=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_static_contract_review_only",
        "may only statically review",
        "must not train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
        "promote a selector or atom",
    ]:
        assert needle in text
