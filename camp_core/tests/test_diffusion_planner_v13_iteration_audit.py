from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v13_iteration_audit.md"
V12_AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v12_iteration_audit.md"


def test_v13_audit_is_current_short_form_authority() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "current_authoritative_audit=docs/diffusion_planner_v13_iteration_audit.md",
        "previous_short_form_audit=docs/diffusion_planner_v12_iteration_audit.md",
        "camp_local_head_at_v13_launch=7ee638bd53e2c5c75da0bbad75afaf750c7af2e7",
        "github_refs_heads_main_at_v13_launch=7ee638bd53e2c5c75da0bbad75afaf750c7af2e7",
        "autodl_camp_head_at_v13_launch=8babbc0dd09cedda944130ce47688a9ba2b2efde",
        "autodl_camp_runner_head_intentionally_unchanged_while_v12_running=True",
        "required_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_dp_head_at_v13_launch=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "formal_seeds_11_12_13_frozen=True",
    ]:
        assert needle in text


def test_v13_audit_pins_fixed_dp_candidate_set_data_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "user_authorized_fixed_dp_candidate_generation_now=True",
        "user_authorized_camp_retraining_after_preflight=True",
        "training_data_unit=route_state_plus_fixed_dp_candidate_set",
        "dataset_expansion_axis=more_fixed_dp_candidate_sets",
        "num_candidates_per_set_kept_fixed=8",
        "dp_role=fixed_black_box_candidate_trajectory_generator",
        "camp_role=current_tick_fixed_candidate_reranker",
        "allowed_candidate_operation=argmin_k score_k(w)",
        "score_expression=score_k(w)=a_k^T w",
        "fixed_dp_candidate_generation_authorized=True",
        "camp_candidate_generation_authorized=False",
        "candidate_generation_by_camp_authorized=False",
        "trajectory_generation_by_camp_authorized=False",
        "trajectory_modification_by_camp_authorized=False",
        "reference_blend_authorized=False",
        "guidance_authorized=False",
        "dp_modification_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
    ]:
        assert needle in text


def test_v13_audit_records_scale_reason_from_v12_probe() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v12_probe_selection_logs=39",
        "v12_probe_records_total=3900",
        "v12_probe_records_without_feasible_candidate=133",
        "v12_probe_fallback_rate=0.034102564102564105",
        "v12_full_expected_fallback_records_approx=436",
        "v13_expected_records_total=51200",
        "v13_expected_fallback_records_approx=1746",
        "fallback_risk_training_records_scope=records_without_feasible_candidate_only",
    ]:
        assert needle in text


def test_v13_audit_records_large_collection_and_training_queue() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "candidate_collection_status=queued_waiting_for_v12_collection_summary_then_running",
        "candidate_collection_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_collection_8babbc0_20260627T115139CST",
        "candidate_collection_pid=264149",
        "pipeline_status=waiting_for_v13_collection_summary_then_training_authorized",
        "pipeline_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_fallback_risk_training_8babbc0_20260627T115139CST",
        "pipeline_pid=264150",
        "expected_replay_commands=512",
        "routes=sample_normal,sample_tl,nishi_release,nishi_lane_change",
        "seeds=301,302,303,304,305,306,307,308,309,310,311,312,313,314,315,316,317,318,319,320,321,322,323,324,325,326,327,328,329,330,331,332",
        "max_npcs=0,4",
        "traffic_light_modes=on,off",
        "steps_per_replay=100",
        "num_candidates=8",
        "expected_records_total=51200",
        "candidate_tensor_provenance_logging=True",
        "camp_training_executed_by_collection=False",
        "training_execution_authorized_after_collection_preflight=True",
        "training_risk_type=cvar",
    ]:
        assert needle in text


def test_v13_audit_requires_large_collection_contract_before_training() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "must_validate_selection_log_count=512",
        "must_validate_records_total=51200",
        "must_validate_formal_seed_path_matches=0",
        "must_validate_candidate_counts=8",
        "must_validate_provenance_payload_valid_records_equals_records_total=True",
        "must_validate_provenance_prepost_equal_records_equals_records_total=True",
        "must_validate_contract_unique_values=(8,False,None,False)",
        "must_validate_camp_candidate_generation_authorized=False",
        "must_validate_candidate_generation_by_camp_authorized=False",
        "must_validate_collection_camp_training_executed=False",
        "fallback_risk_training_queued_after_v13_collection_summary=True",
    ]:
        assert needle in text


def test_v13_audit_preserves_benders_math_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "atom_inputs=current_tick_finite_candidate_features_only",
        "atom_schema_version=dp_camp_v10_14d",
        "atom_count=14",
        "atoms_nonnegative_after_normalization=True",
        "simplex_master_convex=True",
        "cvar_master_convex=True",
        "l2_master_convex=True",
        "new_atoms_require_nonnegativity_or_signed_split_or_hinge_legality_proof=True",
        "candidate_tensor_mutation_effect_allowed=False",
        "candidate_count_change_allowed=False",
        "no_candidate_row_append_required=True",
        "no_coordinate_heading_speed_rewrite_by_camp_required=True",
        "next_work_target=dp_camp_v13_large_nonformal_fixed_dp_candidate_collection_summary_training_and_nonpromotion_holdout_audits",
    ]:
        assert needle in text


def test_v12_audit_points_forward_to_v13() -> None:
    text = V12_AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "superseded_by_current_authoritative_audit=docs/diffusion_planner_v13_iteration_audit.md",
        "v13_reason=larger_fixed_dp_candidate_set_collection_authorized_for_hundreds_to_thousands_fallback_records",
        "candidate_generation_by_fixed_dp_authorized_in_v13=True",
        "candidate_generation_by_camp_authorized_in_v13=False",
    ]:
        assert needle in text
