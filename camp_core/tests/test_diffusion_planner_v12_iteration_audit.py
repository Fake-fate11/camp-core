from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v12_iteration_audit.md"


def test_v12_audit_is_current_short_form_authority() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "current_authoritative_audit=docs/diffusion_planner_v12_iteration_audit.md",
        "previous_short_form_audit=docs/diffusion_planner_v11_iteration_audit.md",
        "camp_local_head_at_v12_audit_start=8babbc0dd09cedda944130ce47688a9ba2b2efde",
        "autodl_camp_head_at_v12_launch=8babbc0dd09cedda944130ce47688a9ba2b2efde",
        "required_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_dp_head_at_v12_launch=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "formal_seeds_11_12_13_frozen=True",
    ]:
        assert needle in text


def test_v12_audit_pins_user_authorized_fixed_dp_collection_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "user_authorized_fixed_dp_candidate_generation_now=True",
        "training_data_unit=route_state_plus_fixed_dp_candidate_set",
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


def test_v12_audit_records_broader_running_collection_scope() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "candidate_collection_status=running",
        "candidate_collection_output_dir=/root/autodl-tmp/camp_dp_v12_nonformal_k8_provenance_candidate_collection_8babbc0_20260627T113316CST",
        "initial_remote_probe_selection_log_count=2",
        "expected_replay_commands=128",
        "routes=sample_normal,sample_tl,nishi_release,nishi_lane_change",
        "seeds=201,202,203,204,205,206,207,208",
        "max_npcs=0,4",
        "traffic_light_modes=on,off",
        "steps_per_replay=100",
        "num_candidates=8",
        "expected_records_total=12800",
        "candidate_noise_strategy=iid",
        "candidate_tensor_provenance_logging=True",
        "camp_training_executed=False",
        "training_execution_authorized_by_this_collection_gate=False",
    ]:
        assert needle in text


def test_v12_audit_requires_collection_contract_before_training() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "must_validate_selection_log_count=128",
        "must_validate_records_total=12800",
        "must_validate_formal_seed_path_matches=0",
        "must_validate_candidate_counts=8",
        "must_validate_provenance_payload_valid_records_equals_records_total=True",
        "must_validate_provenance_prepost_equal_records_equals_records_total=True",
        "must_validate_contract_unique_values=(8,False,None,False)",
        "must_validate_camp_training_executed=False",
        "fallback_risk_training_next_after_collection_summary=True",
        "camp_retraining_not_started_by_v12_launch_gate=True",
    ]:
        assert needle in text


def test_v12_audit_preserves_benders_math_boundary() -> None:
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
        "next_work_target=dp_camp_v12_broader_nonformal_fixed_dp_candidate_collection_summary_and_large_fallback_risk_preflight",
    ]:
        assert needle in text
