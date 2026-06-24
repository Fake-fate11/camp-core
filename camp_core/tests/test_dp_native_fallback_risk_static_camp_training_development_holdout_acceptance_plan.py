from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_development_holdout_acceptance_plan.md"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _plan_text() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_development_holdout_acceptance_plan_is_plan_only() -> None:
    text = _plan_text()

    for needle in [
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_development_holdout_acceptance_plan_only",
        "plan_only=True",
        "audit_only_next=True",
        "records_scope=validation_groups_only",
        "fallback_branch_only=True",
        "records_without_feasible_candidate_only=True",
        "development_holdout_acceptance_audit_authorized_next=True",
    ]:
        assert needle in text


def test_development_holdout_plan_preserves_fixed_candidate_benders_boundary() -> None:
    text = _plan_text()

    for needle in [
        "required_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "require_atom_schema_version=dp_camp_v10_14d",
        "require_num_atoms=14",
        "require_weights_simplex_nonnegative=True",
        "require_atom_scales_strictly_positive=True",
        "score_expression=score_k(w)=a_k^T w",
        "selection_rule=argmin_k score_k(w)",
        "selected_index_in_range=True",
        "candidate_count_unchanged=True",
        "candidate_tensor_unchanged=True",
        "pre_post_candidate_provenance_hashes_equal_if_present=True",
        "recomputed_selected_index_matches_argmin=True",
    ]:
        assert needle in text


def test_development_holdout_plan_forbids_execution_training_and_promotion() -> None:
    text = _plan_text()

    for needle in [
        "training_authorized=False",
        "training_execution_authorized=False",
        "camp_retraining_authorized_now=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
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
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
        "deployment_authorized=False",
    ]:
        assert needle in text

    forbidden_true = [
        "training_authorized=True",
        "training_execution_authorized=True",
        "camp_retraining_authorized_now=True",
        "replay_execution_authorized=True",
        "candidate_generation_authorized=True",
        "Full36_authorized=True",
        "formal_seeds_11_12_13_authorized=True",
        "dp_modification_authorized=True",
        "reference_blend_authorized=True",
        "guidance_authorized=True",
        "postprocess_postselection_authorized=True",
        "closed_loop_outcome_online_input_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "deployable_checkpoint_claim_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "production_selector_change_authorized=True",
        "online_selector_change_authorized=True",
        "deployment_authorized=True",
    ]
    for needle in forbidden_true:
        assert needle not in text


def test_development_holdout_plan_handles_missing_provenance_without_overclaim() -> None:
    text = _plan_text()

    for needle in [
        "If provenance hashes are absent from an older artifact",
        "must not use their absence as positive proof of",
        "fixed-artifact evidence for a development-holdout consistency check",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text


def test_iteration_audit_records_development_holdout_plan_and_next_gate() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_static_camp_training_development_holdout_acceptance_plan_only_passed",
        "development_holdout_acceptance_audit_authorized_next=True",
        "records_scope=validation_groups_only",
        "score_expression=score_k(w)=a_k^T w",
        "candidate_tensor_unchanged=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_development_holdout_acceptance_audit_only",
    ]:
        assert needle in text
