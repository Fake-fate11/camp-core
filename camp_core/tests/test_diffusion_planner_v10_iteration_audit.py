from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v10_iteration_audit.md"


def test_v10_audit_is_current_short_form_authority() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "current_authoritative_audit=docs/diffusion_planner_v10_iteration_audit.md",
        "previous_short_form_audit=docs/diffusion_planner_v9_iteration_audit.md",
        "historical_audit=docs/diffusion_planner_v8_iteration_audit.md",
        "camp_local_head_at_v10_audit_start=5dd89d5b1c2846d810e9dd7702d0ea5cb9c85afe",
        "github_refs_heads_main_at_v10_audit_start=5dd89d5b1c2846d810e9dd7702d0ea5cb9c85afe",
        "autodl_camp_head_at_v10_audit_start=5dd89d5b1c2846d810e9dd7702d0ea5cb9c85afe",
        "required_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_dp_head_at_v10_audit_start=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "formal_seeds_11_12_13_frozen=True",
    ]:
        assert needle in text


def test_v10_audit_pins_expanded_dataset_and_preflight() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "selection_log_inputs=40",
        "formal_path_matches=0",
        "records_total=176",
        "records_without_feasible_candidate=32",
        "records_with_feasible_candidate=144",
        "records_built=32",
        "failed_records=0",
        "candidate_counts=4",
        "dataset_json_sha256=668b2abb81687e53395c5a8f2ed9c7f959fdadc2d083ecf1aff0030964fb8491",
        "split_accepted_records=32",
        "split_training_records=26",
        "split_validation_records=6",
        "formal_eval_artifact_included=False",
        "scale_fit_records_used=26",
        "split_manifest_json_sha256=812bf702f4edb75329527487e792133728c1dfafefa66cd85a980228e34ce209",
        "scale_manifest_json_sha256=e6543dd1fbba34376fc78f19939ccbd8523d2ff58cef457647fb9faff631cd0e",
        "preflight_passed=True",
        "preflight_ready=True",
        "preflight_training_authorized=False",
        "preflight_json_sha256=5f55a8d4bdbbc1ee3b239abc614f46b66ac996b6271e4a5767d7ed1ba69a4bc2",
    ]:
        assert needle in text


def test_v10_audit_pins_expanded_training_without_claims() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "training_output_dir=/root/autodl-tmp/camp_dp_v9_expanded_nonformal_fallback_risk_static_camp_training_5dd89d5_20260627T101424CST",
        "training_exit=0",
        "training_summary_json_sha256=13bfaea957f3f88be16da8bf0f6b2f56b893eeb7a579bde94cf1ee0bcfc1ec54",
        "camp_training_executed=True",
        "training_authorized=True",
        "training_execution_authorized=True",
        "camp_retraining_authorized_now=True",
        "fixed_dp_candidate_reranking_only=True",
        "training_records=26",
        "validation_records=6",
        "num_candidates=4",
        "num_atoms=14",
        "atom_schema_version=dp_camp_v10_14d",
        "objective=simplex_hinge_cvar_l2",
        "risk_type=cvar",
        "risk_alpha=0.8",
        "weights_sum=1.0",
        "weights_min=0.0",
        "weights_max=1.0",
        "nonzero_weight_atom=progress_shortfall",
        "validation_oracle_match_rate=0.3333333333333333",
        "candidate_generation_authorized=False",
        "trajectory_rewrite_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text


def test_v10_audit_pins_nonpromotion_and_holdout_limits() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "nonpromotion_audit_exit=0",
        "nonpromotion_audit_passed=True",
        "offline_weights_json_sha256=cb8c3ee6efb6d11cc294093ff3d0b2f8f2df027aa44535eb5afabf3d6007a218",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "weights_json_simplex_nonnegative=True",
        "weights_npy_simplex_nonnegative=True",
        "weights_json_matches_npy=True",
        "atom_scales_strictly_positive=True",
        "score_expression=score_k(w)=a_k^T w",
        "holdout_audit_exit=0",
        "holdout_audit_passed=True",
        "validation_records=6",
        "static_oracle_match_rate=0.3333333333333333",
        "uniform_oracle_match_rate=0.5",
        "candidate0_oracle_match_rate=0.16666666666666666",
        "recorded_oracle_match_rate=0.5",
        "static_mean_margin_violation=0.14442199612485307",
        "performance_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "deployment_authorized=False",
    ]:
        assert needle in text


def test_v10_audit_preserves_dp_camp_math_boundary_and_next_target() -> None:
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
        "trajectory_modification_by_camp_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "next_work_target=dp_camp_v10_expanded_training_static_contract_and_holdout_sufficiency_review",
        "requires_broader_nonformal_validation_before_performance_claim=True",
    ]:
        assert needle in text
