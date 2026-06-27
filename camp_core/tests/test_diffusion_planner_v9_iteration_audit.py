from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v9_iteration_audit.md"


def test_v9_audit_is_current_short_form_authority() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "current_authoritative_audit=docs/diffusion_planner_v9_iteration_audit.md",
        "historical_audit=docs/diffusion_planner_v8_iteration_audit.md",
        "handoff_base_camp_head=2b4d76c78e72b681675a837e5f36ba2c18efe5ef",
        "required_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    ]:
        assert needle in text


def test_v9_audit_pins_training_fact_without_performance_claim() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "camp_training_executed=True",
        "training_command_exit=0",
        "training_commit=0867cc8b468320b7aaef94ce12e6272ca1d362c4",
        "training_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_manual_authorized_0867cc8b_20260627T092951CST",
        "training_records=13",
        "validation_records=2",
        "validation_records_are_insufficient_for_generalization=True",
        "development_holdout_is_smoke_and_contract_only=True",
        "holdout_static_underperforms_uniform=True",
        "performance_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
    ]:
        assert needle in text


def test_v9_audit_preserves_dp_camp_math_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "dp_role=fixed_black_box_candidate_trajectory_generator",
        "camp_role=current_tick_fixed_candidate_reranker",
        "allowed_candidate_operation=argmin_k score_k(w)",
        "candidate_tensor_unchanged=True",
        "score_expression=score_k(w)=a_k^T w",
        "atom_inputs=current_tick_finite_candidate_features_only",
        "simplex_master_convex=True",
        "cvar_master_convex=True",
        "l2_master_convex=True",
        "new_atoms_require_nonnegativity_or_signed_split_or_hinge_legality_proof=True",
        "candidate_generation_by_camp_authorized=False",
        "dp_modification_authorized=False",
    ]:
        assert needle in text


def test_v9_next_target_is_broader_nonformal_data_before_claims() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "next_work_target=dp_camp_v9_expand_nonformal_development_dataset_and_retrain_static_reranker",
        "manual_retraining_authorization_present=True",
        "formal_seeds_11_12_13_authorized=False",
        "dp_retraining_authorized=False",
        "dp_tuning_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text
