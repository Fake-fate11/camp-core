from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v11_iteration_audit.md"


def test_v11_audit_is_current_short_form_authority() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "current_authoritative_audit=docs/diffusion_planner_v11_iteration_audit.md",
        "previous_short_form_audit=docs/diffusion_planner_v10_iteration_audit.md",
        "historical_audit=docs/diffusion_planner_v8_iteration_audit.md",
        "camp_local_head_at_v11_audit_start=84ad70de23871cdc6782f6c8130c9fb54ace6b03",
        "github_refs_heads_main_at_v11_audit_start=84ad70de23871cdc6782f6c8130c9fb54ace6b03",
        "autodl_camp_head_at_v11_audit_start=84ad70de23871cdc6782f6c8130c9fb54ace6b03",
        "required_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_dp_head_at_v11_audit_start=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "formal_seeds_11_12_13_frozen=True",
    ]:
        assert needle in text


def test_v11_audit_pins_fixed_dp_candidate_collection_not_camp_generation() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "candidate_collection_output_dir=/root/autodl-tmp/camp_dp_v11_nonformal_k8_provenance_candidate_collection_84ad70d_20260627T105702CST",
        "replay_commands_completed=32",
        "selection_log_count=32",
        "records_total=3200",
        "records_without_feasible_candidate=942",
        "records_with_feasible_candidate=2258",
        "num_candidates=8",
        "formal_seed_path_matches=0",
        "candidate_tensor_provenance_logging=True",
        "provenance_present_records=3200",
        "provenance_payload_valid_records=3200",
        "provenance_prepost_equal_records=3200",
        "fixed_dp_candidate_generation_authorized=True",
        "camp_candidate_generation_authorized=False",
        "candidate_generation_by_camp_authorized=False",
        "guidance_authorized=False",
        "reference_blend_authorized=False",
        "dp_modification_authorized=False",
    ]:
        assert needle in text


def test_v11_audit_pins_dataset_preflight_and_training_scale() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "pipeline_output_dir=/root/autodl-tmp/camp_dp_v11_nonformal_k8_provenance_fallback_risk_training_84ad70d_20260627T111657CST",
        "dataset_records_built=942",
        "dataset_failed_records=0",
        "validator_passed=True",
        "validator_failed_records=0",
        "split_accepted_records=942",
        "split_training_records=747",
        "split_validation_records=195",
        "scale_fit_records_used=747",
        "preflight_passed=True",
        "preflight_ready=True",
        "preflight_training_authorized=False",
        "dataset_json_sha256=3203f3c7cc5c41e96502738c901f873cac11b756f4d9a43ce9694057fb9b9f38",
        "preflight_json_sha256=f38d200e12fe0b6e6b6036e387eded91c37f049d90be55e6f265ec69338d0cf2",
    ]:
        assert needle in text


def test_v11_audit_pins_retraining_as_offline_nonpromotion_artifact() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "training_exit=0",
        "training_summary_json_sha256=abb568916004f04df08dbc4822f673d6e3bde763193c6fd8539837d5da58d9bf",
        "camp_training_executed=True",
        "training_authorized=True",
        "training_execution_authorized=True",
        "camp_retraining_authorized_now=True",
        "fixed_dp_candidate_reranking_only=True",
        "training_records=747",
        "validation_records=195",
        "num_candidates=8",
        "num_atoms=14",
        "atom_schema_version=dp_camp_v10_14d",
        "objective=simplex_hinge_cvar_l2",
        "risk_type=cvar",
        "weights_sum=0.9999999999999999",
        "weights_min=0.0",
        "weights_max=0.19428605160443777",
        "validation_oracle_match_rate=0.37435897435897436",
        "offline_weights_json_sha256=9fa0ebe8c51df511a711faa8780cc932df4d289cb7aaaf6afcffe58283ad7f90",
        "offline_weights_npy_sha256=baec5549c99aed54a8489fdd0b9dbf68d36a509eb6ee2449ddc846a6ec26a281",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text


def test_v11_audit_pins_nonpromotion_holdout_and_math_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "nonpromotion_audit_passed=True",
        "weights_json_simplex_nonnegative=True",
        "weights_npy_simplex_nonnegative=True",
        "weights_json_matches_npy=True",
        "atom_scales_strictly_positive=True",
        "score_expression=score_k(w)=a_k^T w",
        "holdout_audit_passed=True",
        "validation_records=195",
        "static_oracle_match_rate=0.37435897435897436",
        "uniform_oracle_match_rate=0.09230769230769231",
        "candidate0_oracle_match_rate=0.38974358974358975",
        "candidate_tensor_unchanged=True",
        "candidate_count_unchanged=True",
        "training_data_unit=route_state_plus_fixed_dp_candidate_set",
        "camp_role=current_tick_fixed_candidate_reranker",
        "atom_inputs=current_tick_finite_candidate_features_only",
        "simplex_master_convex=True",
        "cvar_master_convex=True",
        "l2_master_convex=True",
        "new_atoms_require_nonnegativity_or_signed_split_or_hinge_legality_proof=True",
        "candidate_generation_by_camp_authorized=False",
        "trajectory_modification_by_camp_authorized=False",
        "next_work_target=dp_camp_v11_nonformal_k8_provenance_static_reranker_holdout_review_and_broader_replay_before_any_promotion",
    ]:
        assert needle in text
