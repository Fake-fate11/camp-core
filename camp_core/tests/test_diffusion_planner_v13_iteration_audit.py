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


def test_v13_audit_records_completed_collection_and_sync_evidence() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "autodl_camp_head_after_v13_completion_sync=a6c04788aea809c24f45fcd97669466718c29663",
        "autodl_camp_sync_method=verified_local_git_bundle_fetch_plus_ff_only_merge",
        "autodl_dp_head_after_v13_completion_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v12_collection_status=complete",
        "v12_records_without_feasible_candidate=3735",
        "v12_training_records=2972",
        "v12_validation_records=763",
        "v13_collection_status=complete",
        "v13_selection_log_count=512",
        "v13_failed_replay_commands=0",
        "v13_records_total=51200",
        "v13_records_without_feasible_candidate=14058",
        "v13_records_with_feasible_candidate=37142",
        "v13_records_bad_feasible_mask=0",
        "v13_candidate_counts=8",
        "v13_formal_seed_path_matches=0",
        "v13_provenance_payload_valid_records=51200",
        "v13_contract_unique_values=(8,False,None,False)",
        "v13_candidate_generation_by_camp_authorized=False",
        "v13_dp_modification_authorized=False",
        "v13_camp_training_executed_by_collection=False",
    ]:
        assert needle in text


def test_v13_audit_records_large_training_artifact_contract() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_pipeline_status=complete",
        "v13_dataset_json_sha256=2f41d07adedd28ded0869ec0f13a5e13beabe2f7e5f07a54e97b220df928113b",
        "v13_training_summary_json_sha256=01234264e01aa7e8bdb4df1aa7aa818af8643a691f7427adc4e3639e104f77cd",
        "v13_weights_json_sha256=4979901f489f20eb6b9fd6ea122300d3b390c5d6d0d72490a0b84148ba68b489",
        "v13_weights_npy_sha256=751fbc3a333af0aae483ed50fcfa1abe02361f7bb3d18d8264bf0425019a4752",
        "v13_dataset_records_built=14058",
        "v13_training_records=11262",
        "v13_validation_records=2796",
        "v13_scale_fit_records_used=11262",
        "v13_preflight_passed=True",
        "v13_training_passed=True",
        "v13_training_commit=8babbc0dd09cedda944130ce47688a9ba2b2efde",
        "v13_fallback_only_training=True",
        "v13_fixed_dp_candidate_reranking_only=True",
        "v13_training_seed=23",
        "v13_training_seed_is_formal_seed=False",
        "v13_num_candidates=8",
        "v13_num_atoms=14",
        "v13_atom_schema_version=dp_camp_v10_14d",
        "v13_training_objective=simplex_hinge_cvar_l2",
        "v13_score_expression=score_k(w)=a_k^T w",
        "v13_weights_sum=1.0",
        "v13_weights_min=0.0",
        "training_metrics_are_diagnostic_not_safety_claim=True",
    ]:
        assert needle in text


def test_v13_audit_records_post_training_nonpromotion_and_holdout_audits() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_nonpromotion_audit_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_nonpromotion_artifact_audit_8babbc0_a6c0478_20260627T164235CST",
        "v13_nonpromotion_audit_json_sha256=866c248f246ec9b2e6dc44c9bd41fb2fb47b280f61059a3337af64d4d031c3a6",
        "v13_nonpromotion_audit_exit=0",
        "v13_nonpromotion_audit_passed=True",
        "v13_training_artifacts_nonpromotion=True",
        "v13_nonpromotion_fixed_dp_candidate_reranking_only=True",
        "v13_development_holdout_audit_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_development_holdout_acceptance_audit_8babbc0_a6c0478_20260627T164235CST",
        "v13_development_holdout_audit_json_sha256=816fa4dbfac8e7cf47a4f3f86b64545374e5b29e263351c30150c42881ebeda2",
        "v13_development_holdout_audit_exit=0",
        "v13_development_holdout_acceptance_audit_passed=True",
        "v13_development_holdout_records_scope=validation_groups_only",
        "v13_development_holdout_fallback_branch_only=True",
        "v13_development_holdout_selection_rule=argmin_k score_k(w)",
        "training_authorized_by_post_training_audits=False",
        "replay_execution_authorized_by_post_training_audits=False",
        "candidate_generation_authorized_by_post_training_audits=False",
        "dp_modification_authorized_by_post_training_audits=False",
        "selector_promotion_authorized_by_post_training_audits=False",
        "deployable_checkpoint_claim_authorized_by_post_training_audits=False",
        "safety_benefit_claim_authorized_by_post_training_audits=False",
        "camp_over_dp_top1_claim_authorized_by_post_training_audits=False",
    ]:
        assert needle in text


def test_v13_audit_records_current_result_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "current_v13_status=large_fixed_dp_candidate_collection_training_and_post_training_audits_complete",
        "current_v13_artifact_scope=offline_nonpromotion_static_camp_reranker",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=dp_camp_v13_offline_nonpromotion_static_reranker_result_review_before_any_promotion_decision",
    ]:
        assert needle in text


def test_v13_audit_records_result_review_before_promotion_decision() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_result_review_status=dp_camp_v13_offline_nonpromotion_static_reranker_result_review_ready",
        "v13_result_review_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_offline_nonpromotion_static_reranker_result_review_8babbc0_378adc3_20260627T165838CST",
        "v13_result_review_schema_version=dp_camp_v13_offline_nonpromotion_static_reranker_result_review_v1",
        "v13_result_review_json_sha256=dd3f2ab6c94ab9535710dc7dc848d560d29ebec99878fe2c8f4b9658651eac50",
        "v13_result_review_md_sha256=17366f66a15abfbf25ad3265ab16d9d8c2b47811cbf70df8bcd91c17e16df1e5",
        "v13_result_review_exit=0",
        "v13_result_review_execution_camp_head=378adc3518490f9b8ebdecfde0d7ee7b557d986a",
        "v13_result_review_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_result_review_passed=True",
        "v13_result_review_failed_checks=[]",
        "v13_result_review_records_total=51200",
        "v13_result_review_records_without_feasible_candidate=14058",
        "v13_result_review_training_records=11262",
        "v13_result_review_validation_records=2796",
        "v13_result_review_num_candidates=8",
        "v13_result_review_num_atoms=14",
        "v13_result_review_atom_schema_version=dp_camp_v10_14d",
        "v13_result_review_score_expression=score_k(w)=a_k^T w",
        "v13_result_review_ready=True",
        "v13_result_review_authorized_next_work=dp_camp_v13_promotion_decision_plan_only_after_explicit_user_authorization",
    ]:
        assert needle in text


def test_v13_audit_result_review_does_not_authorize_promotion_or_claims() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_promotion_decision_plan_authorized_by_result_review=True",
        "v13_selector_promotion_authorized_by_result_review=False",
        "v13_atom_promotion_authorized_by_result_review=False",
        "v13_deployment_authorized_by_result_review=False",
        "v13_training_authorized_by_result_review=False",
        "v13_training_execution_authorized_by_result_review=False",
        "v13_replay_execution_authorized_by_result_review=False",
        "v13_candidate_generation_authorized_by_result_review=False",
        "v13_dp_modification_authorized_by_result_review=False",
        "v13_deployable_checkpoint_claim_authorized_by_result_review=False",
        "v13_safety_benefit_claim_authorized_by_result_review=False",
        "v13_camp_over_dp_top1_claim_authorized_by_result_review=False",
        "current_v13_status=offline_nonpromotion_static_reranker_result_review_complete",
        "training_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_promotion_decision_plan_only_after_explicit_user_authorization",
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
