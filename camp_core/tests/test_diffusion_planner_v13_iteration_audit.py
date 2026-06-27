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


def test_v13_audit_records_promotion_decision_planning_gate() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_promotion_decision_plan_status=dp_camp_v13_promotion_decision_plan_ready",
        "v13_promotion_decision_plan_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_promotion_decision_plan_8babbc0_5dd1515_20260627T174906CST",
        "v13_promotion_decision_plan_json_sha256=2ce44397b699d22a353e00ef5646e71b4e0345a3bc838dc5a58f375b22b768c8",
        "v13_promotion_decision_plan_md_sha256=0b03572d5875daf076e26272beb01eacbcaa9c61e13b33e9ac8ad030715ea033",
        "v13_promotion_decision_plan_script_sha256=afba9d059ce9778dda0cfb4471c9e2b69468bd2ce8f8cd73c113568aeaee7b5f",
        "v13_promotion_decision_plan_source_result_review_sha256=dd3f2ab6c94ab9535710dc7dc848d560d29ebec99878fe2c8f4b9658651eac50",
        "v13_promotion_decision_plan_exit=0",
        "v13_promotion_decision_plan_execution_camp_head=5dd1515575e7ab8fb50a9be137e8fec0153b5590",
        "v13_promotion_decision_plan_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_promotion_decision_plan_passed=True",
        "v13_promotion_decision_plan_failed_checks=[]",
        "v13_promotion_decision_plan_recommendation=do_not_promote_from_current_evidence_alone",
        "v13_promotion_class_under_consideration=future_default_off_shadow_or_development_reranker_candidate",
        "v13_promotion_decision_plan_immediate_action=build_evidence_package_preflight_only",
        "v13_promotion_decision_plan_authorized_next_work=dp_camp_v13_promotion_evidence_package_preflight_only",
        "v13_evidence_package_preflight_authorized_by_plan=True",
        "v13_evidence_package_preflight_execution_authorized_now=False",
    ]:
        assert needle in text


def test_v13_audit_promotion_decision_plan_preserves_no_promotion_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_selector_promotion_authorized_by_plan=False",
        "v13_atom_promotion_authorized_by_plan=False",
        "v13_deployment_authorized_by_plan=False",
        "v13_training_authorized_by_plan=False",
        "v13_training_execution_authorized_by_plan=False",
        "v13_replay_execution_authorized_by_plan=False",
        "v13_candidate_generation_authorized_by_plan=False",
        "v13_dp_modification_authorized_by_plan=False",
        "v13_online_selector_change_authorized_by_plan=False",
        "v13_production_selector_change_authorized_by_plan=False",
        "v13_deployable_checkpoint_claim_authorized_by_plan=False",
        "v13_safety_benefit_claim_authorized_by_plan=False",
        "v13_camp_over_dp_top1_claim_authorized_by_plan=False",
        "v13_required_evidence_before_promotion=immutable_artifact_manifest_for_weights_scales_training_and_audits",
        "v13_promotion_no_go_conditions=dp_head_differs_from_fixed_tieriv_commit,candidate_tensor_contract_changes_or_k_not_8,camp_generates_or_modifies_trajectories",
        "current_v13_status=promotion_decision_planning_complete",
        "current_v13_next_scope=evidence_package_preflight_only",
        "next_work_target=dp_camp_v13_promotion_evidence_package_preflight_only",
    ]:
        assert needle in text


def test_v13_audit_records_promotion_evidence_package_preflight() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_promotion_evidence_package_preflight_status=dp_camp_v13_promotion_evidence_package_preflight_ready",
        "v13_promotion_evidence_package_preflight_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_promotion_evidence_package_preflight_8babbc0_c3a57b1_20260627T180636CST",
        "v13_promotion_evidence_package_preflight_json_sha256=15d8f3ee9452625325e614cbd4161dc715dcaf6cc7931534e860cea096c59722",
        "v13_promotion_evidence_package_preflight_md_sha256=f4027408ff2ccc19d7e122d23abfa8fcae5aa7317a8e118e567f5b74626c86c8",
        "v13_promotion_evidence_package_preflight_script_sha256=29ecdf331cabec915e70c3c5b8da72dab619f5b4c8a4a2c38194f7ca0552cfb9",
        "v13_promotion_evidence_package_preflight_source_plan_sha256=2ce44397b699d22a353e00ef5646e71b4e0345a3bc838dc5a58f375b22b768c8",
        "v13_promotion_evidence_package_preflight_exit=0",
        "v13_promotion_evidence_package_preflight_execution_camp_head=c3a57b1a512ce1ba77ae0ebae1996835f46b0c7c",
        "v13_promotion_evidence_package_preflight_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_promotion_evidence_package_preflight_passed=True",
        "v13_promotion_evidence_package_preflight_failed_checks=[]",
        "v13_promotion_evidence_package_preflight_manifest_count=10",
        "v13_immutable_artifact_manifest_ready=True",
        "v13_static_integration_contract_pinned=True",
        "v13_static_integration_contract_status=preflight_ready_contract_pinned",
        "v13_default_off_shadow_selector_wiring_status=future_static_contract_plan_required_before_implementation",
        "v13_promotion_evidence_package_authorized_next_work=dp_camp_v13_default_off_shadow_selector_static_integration_contract_plan_only",
        "v13_default_off_shadow_selector_contract_plan_authorized=True",
    ]:
        assert needle in text


def test_v13_audit_evidence_package_preflight_preserves_no_action_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_selector_promotion_authorized_by_evidence_package_preflight=False",
        "v13_atom_promotion_authorized_by_evidence_package_preflight=False",
        "v13_deployment_authorized_by_evidence_package_preflight=False",
        "v13_training_authorized_by_evidence_package_preflight=False",
        "v13_training_execution_authorized_by_evidence_package_preflight=False",
        "v13_replay_execution_authorized_by_evidence_package_preflight=False",
        "v13_candidate_generation_authorized_by_evidence_package_preflight=False",
        "v13_dp_modification_authorized_by_evidence_package_preflight=False",
        "v13_online_selector_change_authorized_by_evidence_package_preflight=False",
        "v13_production_selector_change_authorized_by_evidence_package_preflight=False",
        "v13_deployable_checkpoint_claim_authorized_by_evidence_package_preflight=False",
        "v13_safety_benefit_claim_authorized_by_evidence_package_preflight=False",
        "v13_camp_over_dp_top1_claim_authorized_by_evidence_package_preflight=False",
        "current_v13_status=promotion_evidence_package_preflight_complete",
        "current_v13_next_scope=default_off_shadow_selector_static_integration_contract_plan_only",
        "training_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_static_integration_contract_plan_only",
    ]:
        assert needle in text


def test_v13_audit_records_default_off_shadow_selector_static_contract_plan() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_static_contract_plan_status=dp_camp_v13_default_off_shadow_selector_static_contract_plan_ready",
        "v13_default_off_shadow_selector_static_contract_plan_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_static_contract_plan_8babbc0_fec07cb_20260627T181409CST",
        "v13_default_off_shadow_selector_static_contract_plan_json_sha256=1891102c382a077659b23dc9d01fcd552c55fa84606ec3407e12220f43a0bd8e",
        "v13_default_off_shadow_selector_static_contract_plan_md_sha256=10a0dadf274269dde8309d6095fa191c585beae51ed51dc683fe545bfde63e7e",
        "v13_default_off_shadow_selector_static_contract_plan_script_sha256=8994e08fdd02e0237df38866524334cc52a4c1f6338d782305413783f90e366d",
        "v13_default_off_shadow_selector_static_contract_plan_source_preflight_sha256=15d8f3ee9452625325e614cbd4161dc715dcaf6cc7931534e860cea096c59722",
        "v13_default_off_shadow_selector_static_contract_plan_exit=0",
        "v13_default_off_shadow_selector_static_contract_plan_execution_camp_head=fec07cb7ec9719c335507f70566aac750a1f4c66",
        "v13_default_off_shadow_selector_static_contract_plan_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_static_contract_plan_passed=True",
        "v13_default_off_shadow_selector_static_contract_plan_failed_checks=[]",
        "v13_static_contract_plan_surface_keys=camp_selector_surface,contract_tests,runner_surface",
        "v13_static_contract_plan_status=plan_ready_no_implementation",
        "v13_static_contract_plan_runtime_effect=must_log_shadow_decision_without changing DP top1 output",
        "v13_static_contract_plan_score_expression=score_k(w)=a_k^T w",
        "v13_static_contract_plan_fail_closed_policy=on any missing artifact, K drift, nonfinite value, or source mismatch, emit DP top1 and log no shadow selection",
        "v13_default_off_shadow_selector_static_contract_plan_authorized_next_work=dp_camp_v13_default_off_shadow_selector_implementation_plan_only",
        "v13_default_off_shadow_selector_implementation_plan_authorized=True",
        "v13_default_off_shadow_selector_implementation_authorized=False",
    ]:
        assert needle in text


def test_v13_audit_static_contract_plan_preserves_no_action_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_selector_promotion_authorized_by_static_contract_plan=False",
        "v13_atom_promotion_authorized_by_static_contract_plan=False",
        "v13_deployment_authorized_by_static_contract_plan=False",
        "v13_training_authorized_by_static_contract_plan=False",
        "v13_training_execution_authorized_by_static_contract_plan=False",
        "v13_replay_execution_authorized_by_static_contract_plan=False",
        "v13_candidate_generation_authorized_by_static_contract_plan=False",
        "v13_dp_modification_authorized_by_static_contract_plan=False",
        "v13_online_selector_change_authorized_by_static_contract_plan=False",
        "v13_production_selector_change_authorized_by_static_contract_plan=False",
        "v13_deployable_checkpoint_claim_authorized_by_static_contract_plan=False",
        "v13_safety_benefit_claim_authorized_by_static_contract_plan=False",
        "v13_camp_over_dp_top1_claim_authorized_by_static_contract_plan=False",
        "current_v13_status=default_off_shadow_selector_static_contract_plan_complete",
        "current_v13_next_scope=default_off_shadow_selector_implementation_plan_only",
        "training_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_implementation_plan_only",
    ]:
        assert needle in text


def test_v13_audit_records_default_off_shadow_selector_implementation_plan() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_implementation_plan_status=dp_camp_v13_default_off_shadow_selector_implementation_plan_ready",
        "v13_default_off_shadow_selector_implementation_plan_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_implementation_plan_8babbc0_3c10183_20260627T183239CST",
        "v13_default_off_shadow_selector_implementation_plan_json_sha256=f4d83e2ceb686910ad4f34b79609c545d15e0133ccc4708d8871d00483d9c25c",
        "v13_default_off_shadow_selector_implementation_plan_md_sha256=7179345897b661e4b5fe8f234f3d00a7464259d0d36643f7ae31684021df2e32",
        "v13_default_off_shadow_selector_implementation_plan_script_sha256=cda9a146de786c0859d4a777385f83635b99c2d09e8d0bbc0c0596bc8f367cb9",
        "v13_default_off_shadow_selector_implementation_plan_source_static_contract_sha256=1891102c382a077659b23dc9d01fcd552c55fa84606ec3407e12220f43a0bd8e",
        "v13_default_off_shadow_selector_implementation_plan_exit=0",
        "v13_default_off_shadow_selector_implementation_plan_execution_camp_head=3c101838f73d4e143ce6fc4357b3241a1e4a2034",
        "v13_default_off_shadow_selector_implementation_plan_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_implementation_plan_passed=True",
        "v13_default_off_shadow_selector_implementation_plan_failed_checks=[]",
        "v13_shadow_selector_implementation_plan_status=plan_ready_no_implementation",
        "v13_shadow_selector_implementation_plan_runtime_effect=log shadow decision while executed output remains DP top1",
        "v13_shadow_selector_implementation_plan_selection_rule=shadow_selected_index = argmin_k score_k(w)",
        "v13_shadow_selector_implementation_plan_score_expression=score_k(w)=a_k^T w",
        "v13_default_off_shadow_selector_implementation_plan_authorized_next_work=dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review_only",
        "v13_default_off_shadow_selector_implementation_static_contract_review_authorized=True",
        "v13_default_off_shadow_selector_implementation_authorized=False",
    ]:
        assert needle in text


def test_v13_audit_implementation_plan_preserves_no_action_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_selector_promotion_authorized_by_implementation_plan=False",
        "v13_atom_promotion_authorized_by_implementation_plan=False",
        "v13_deployment_authorized_by_implementation_plan=False",
        "v13_training_authorized_by_implementation_plan=False",
        "v13_training_execution_authorized_by_implementation_plan=False",
        "v13_replay_execution_authorized_by_implementation_plan=False",
        "v13_candidate_generation_authorized_by_implementation_plan=False",
        "v13_dp_modification_authorized_by_implementation_plan=False",
        "v13_online_selector_change_authorized_by_implementation_plan=False",
        "v13_production_selector_change_authorized_by_implementation_plan=False",
        "v13_deployable_checkpoint_claim_authorized_by_implementation_plan=False",
        "v13_safety_benefit_claim_authorized_by_implementation_plan=False",
        "v13_camp_over_dp_top1_claim_authorized_by_implementation_plan=False",
        "current_v13_status=default_off_shadow_selector_implementation_plan_complete",
        "current_v13_next_scope=default_off_shadow_selector_implementation_static_contract_review_only",
        "default_off_shadow_selector_implementation_authorized_by_current_boundary=False",
        "training_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review_only",
    ]:
        assert needle in text


def test_v13_audit_records_default_off_shadow_selector_implementation_static_contract_review() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_implementation_static_contract_review_status=dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review_ready",
        "v13_default_off_shadow_selector_implementation_static_contract_review_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_implementation_static_contract_review_8babbc0_418f952_20260627T184154CST",
        "v13_default_off_shadow_selector_implementation_static_contract_review_json_sha256=7d3e9c1dc032da3edaa08318b84981ca84a747f4d22e82c61e0be93403596662",
        "v13_default_off_shadow_selector_implementation_static_contract_review_md_sha256=5fc7f070d5e468729f7c05594f0181e960e2d4fd64f3f5ae6d74b5bb7c74f54d",
        "v13_default_off_shadow_selector_implementation_static_contract_review_script_sha256=88e9d683e9b7b7523990c7aa28dec931ae470fb6508659e75a0746b728f8d2ce",
        "v13_default_off_shadow_selector_implementation_static_contract_review_source_plan_sha256=f4d83e2ceb686910ad4f34b79609c545d15e0133ccc4708d8871d00483d9c25c",
        "v13_default_off_shadow_selector_implementation_static_contract_review_exit=0",
        "v13_default_off_shadow_selector_implementation_static_contract_review_execution_camp_head=418f952af2b1eebacb0478f6bf3a0f33fa419327",
        "v13_default_off_shadow_selector_implementation_static_contract_review_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_implementation_static_contract_review_passed=True",
        "v13_default_off_shadow_selector_implementation_static_contract_review_failed_checks=[]",
        "v13_shadow_selector_static_contract_review_status=review_ready_no_implementation",
        "v13_shadow_selector_static_contract_review_runtime_effect=executed output remains DP top1 during shadow phase",
        "v13_shadow_selector_static_contract_review_candidate_operation=fixed DP candidate reranking only",
        "v13_shadow_selector_static_contract_review_score_expression=score_k(w)=a_k^T w",
        "v13_shadow_selector_static_contract_review_contracts=default_off_flag_contract,immutable_artifact_hash_contract,fixed_candidate_tensor_contract,affine_benders_atom_score_contract,dp_top1_runtime_output_contract,fail_closed_observability_contract,no_promotion_no_claims_contract",
        "v13_default_off_shadow_selector_implementation_static_contract_review_authorized_next_work=dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_plan_only",
        "v13_default_off_shadow_selector_implementation_unit_tests_plan_authorized=True",
        "v13_default_off_shadow_selector_implementation_authorized_by_static_contract_review=False",
    ]:
        assert needle in text


def test_v13_audit_implementation_static_contract_review_preserves_no_action_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_selector_promotion_authorized_by_implementation_static_contract_review=False",
        "v13_atom_promotion_authorized_by_implementation_static_contract_review=False",
        "v13_deployment_authorized_by_implementation_static_contract_review=False",
        "v13_training_authorized_by_implementation_static_contract_review=False",
        "v13_training_execution_authorized_by_implementation_static_contract_review=False",
        "v13_replay_execution_authorized_by_implementation_static_contract_review=False",
        "v13_candidate_generation_authorized_by_implementation_static_contract_review=False",
        "v13_dp_modification_authorized_by_implementation_static_contract_review=False",
        "v13_online_selector_change_authorized_by_implementation_static_contract_review=False",
        "v13_production_selector_change_authorized_by_implementation_static_contract_review=False",
        "v13_deployable_checkpoint_claim_authorized_by_implementation_static_contract_review=False",
        "v13_safety_benefit_claim_authorized_by_implementation_static_contract_review=False",
        "v13_camp_over_dp_top1_claim_authorized_by_implementation_static_contract_review=False",
        "current_v13_status=default_off_shadow_selector_implementation_static_contract_review_complete",
        "current_v13_next_scope=default_off_shadow_selector_implementation_unit_tests_plan_only",
        "default_off_shadow_selector_implementation_authorized_by_current_boundary=False",
        "training_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_plan_only",
    ]:
        assert needle in text


def test_v13_audit_records_default_off_shadow_selector_implementation_unit_tests_plan() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_implementation_unit_tests_plan_status=dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_plan_ready",
        "v13_default_off_shadow_selector_implementation_unit_tests_plan_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_implementation_unit_tests_plan_8babbc0_6bebda3_20260627T185102CST",
        "v13_default_off_shadow_selector_implementation_unit_tests_plan_json_sha256=b6b77d5134c934debd307b78048edc7667fcff30327127e7941caeb80ce4513b",
        "v13_default_off_shadow_selector_implementation_unit_tests_plan_md_sha256=5a5b0290562b3440e85e5efc14ae0ff3af3237c66c4db79fefd17fcc536a4a4c",
        "v13_default_off_shadow_selector_implementation_unit_tests_plan_script_sha256=132e2cb3d820c31e2b56f866d821d05f2892dae23968defb16a351cad7b48781",
        "v13_default_off_shadow_selector_implementation_unit_tests_plan_source_review_sha256=7d3e9c1dc032da3edaa08318b84981ca84a747f4d22e82c61e0be93403596662",
        "v13_default_off_shadow_selector_implementation_unit_tests_plan_exit=0",
        "v13_default_off_shadow_selector_implementation_unit_tests_plan_execution_camp_head=6bebda393adb20980b63c0725d36532627e9222f",
        "v13_default_off_shadow_selector_implementation_unit_tests_plan_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_implementation_unit_tests_plan_passed=True",
        "v13_default_off_shadow_selector_implementation_unit_tests_plan_failed_checks=[]",
        "v13_shadow_selector_unit_tests_plan_status=plan_ready_no_unit_test_code",
        "v13_shadow_selector_unit_tests_plan_target_test_file=camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_implementation_unit_tests.py",
        "v13_shadow_selector_unit_tests_plan_groups=default_off_disabled_contract,immutable_artifact_hash_contract,fixed_candidate_affine_score_contract,dp_top1_shadow_runtime_contract,no_candidate_mutation_contract,benders_and_seed_boundary_contract",
        "v13_shadow_selector_unit_tests_plan_score_expression=score_k(w)=a_k^T w",
        "v13_default_off_shadow_selector_implementation_unit_tests_plan_authorized_next_work=dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_only",
        "v13_default_off_shadow_selector_implementation_unit_tests_only_authorized=True",
        "v13_default_off_shadow_selector_implementation_authorized_by_unit_tests_plan=False",
    ]:
        assert needle in text


def test_v13_audit_implementation_unit_tests_plan_preserves_no_action_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_selector_promotion_authorized_by_unit_tests_plan=False",
        "v13_atom_promotion_authorized_by_unit_tests_plan=False",
        "v13_deployment_authorized_by_unit_tests_plan=False",
        "v13_training_authorized_by_unit_tests_plan=False",
        "v13_training_execution_authorized_by_unit_tests_plan=False",
        "v13_replay_execution_authorized_by_unit_tests_plan=False",
        "v13_candidate_generation_authorized_by_unit_tests_plan=False",
        "v13_dp_modification_authorized_by_unit_tests_plan=False",
        "v13_online_selector_change_authorized_by_unit_tests_plan=False",
        "v13_production_selector_change_authorized_by_unit_tests_plan=False",
        "v13_deployable_checkpoint_claim_authorized_by_unit_tests_plan=False",
        "v13_safety_benefit_claim_authorized_by_unit_tests_plan=False",
        "v13_camp_over_dp_top1_claim_authorized_by_unit_tests_plan=False",
        "current_v13_status=default_off_shadow_selector_implementation_unit_tests_plan_complete",
        "current_v13_next_scope=default_off_shadow_selector_implementation_unit_tests_only",
        "default_off_shadow_selector_implementation_authorized_by_current_boundary=False",
        "training_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_only",
    ]:
        assert needle in text


def test_v13_audit_records_default_off_shadow_selector_implementation_unit_tests_only() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_implementation_unit_tests_only_status=dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_only_complete",
        "v13_default_off_shadow_selector_implementation_unit_tests_only_test_file=camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_implementation_unit_tests.py",
        "v13_default_off_shadow_selector_implementation_unit_tests_only_test_file_sha256=c88fdd88a21e5daab75bf4c5b71a9b43372a80d4ae2141df3b23178fb5c43fd7",
        "v13_default_off_shadow_selector_implementation_unit_tests_only_local_pytest=10 passed in 0.47s",
        "v13_default_off_shadow_selector_implementation_unit_tests_only_execution_camp_head=1558a576701bcc0f62b924f5019cf58c058bf763",
        "v13_default_off_shadow_selector_implementation_unit_tests_only_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_implementation_unit_tests_only_commit=53fabd8299f7d2195612eb99bf30050c3f3bbac0",
        "v13_default_off_shadow_selector_implementation_unit_tests_only_github_refs_heads_main_after_push=53fabd8299f7d2195612eb99bf30050c3f3bbac0",
        "v13_default_off_shadow_selector_implementation_unit_tests_only_autodl_camp_head_after_sync=53fabd8299f7d2195612eb99bf30050c3f3bbac0",
        "v13_default_off_shadow_selector_implementation_unit_tests_only_autodl_dp_head_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_implementation_unit_tests_only_autodl_pytest=88 passed in 1.15s",
        "v13_shadow_selector_unit_tests_status=unit_tests_complete_no_production_implementation",
        "v13_shadow_selector_unit_tests_groups=default_off_disabled_contract,immutable_artifact_hash_contract,fixed_candidate_affine_score_contract,dp_top1_shadow_runtime_contract,no_candidate_mutation_contract,benders_and_seed_boundary_contract,current_static_source_surface_contract",
        "v13_shadow_selector_unit_tests_score_expression=score_k(w)=a_k^T w",
        "v13_shadow_selector_unit_tests_candidate_count=8",
        "v13_shadow_selector_unit_tests_runtime_effect=shadow selected index may be logged but executed output remains DP top1",
        "v13_shadow_selector_unit_tests_candidate_operation=fixed DP candidate reranking only",
        "v13_shadow_selector_unit_tests_candidate_mutation_allowed=False",
        "v13_shadow_selector_unit_tests_formal_seed_11_12_13_execution_allowed=False",
        "v13_default_off_shadow_selector_implementation_unit_tests_only_authorized_next_work=dp_camp_v13_default_off_shadow_selector_implementation_only_after_explicit_user_authorization",
        "v13_default_off_shadow_selector_implementation_ready_for_explicit_authorization=True",
        "v13_default_off_shadow_selector_implementation_authorized_by_unit_tests_only=False",
    ]:
        assert needle in text


def test_v13_audit_implementation_unit_tests_only_preserves_no_action_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_selector_promotion_authorized_by_unit_tests_only=False",
        "v13_atom_promotion_authorized_by_unit_tests_only=False",
        "v13_deployment_authorized_by_unit_tests_only=False",
        "v13_training_authorized_by_unit_tests_only=False",
        "v13_training_execution_authorized_by_unit_tests_only=False",
        "v13_replay_execution_authorized_by_unit_tests_only=False",
        "v13_candidate_generation_authorized_by_unit_tests_only=False",
        "v13_dp_modification_authorized_by_unit_tests_only=False",
        "v13_online_selector_change_authorized_by_unit_tests_only=False",
        "v13_production_selector_change_authorized_by_unit_tests_only=False",
        "v13_deployable_checkpoint_claim_authorized_by_unit_tests_only=False",
        "v13_safety_benefit_claim_authorized_by_unit_tests_only=False",
        "v13_camp_over_dp_top1_claim_authorized_by_unit_tests_only=False",
        "current_v13_status=default_off_shadow_selector_implementation_unit_tests_only_complete",
        "current_v13_next_scope=default_off_shadow_selector_implementation_only_after_explicit_user_authorization",
        "default_off_shadow_selector_implementation_authorized_by_current_boundary=False",
        "training_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_implementation_only_after_explicit_user_authorization",
    ]:
        assert needle in text


def test_v13_audit_records_default_off_shadow_selector_implementation() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_implementation_status=dp_camp_v13_default_off_shadow_selector_implementation_complete",
        "v13_default_off_shadow_selector_implementation_user_authorized=True",
        "v13_default_off_shadow_selector_implementation_runner_file=scripts/integrations/run_diffusion_planner_camp_replay.py",
        "v13_default_off_shadow_selector_implementation_runner_file_sha256=1d5e116cb2c7c473b9c79906a17bc01683dc9b7595a6006c129cc135dedf4813",
        "v13_default_off_shadow_selector_implementation_test_file=camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_implementation_unit_tests.py",
        "v13_default_off_shadow_selector_implementation_test_file_sha256=ca87f7b69b4bd51969b94583cd1fddf41efe75185bb953b508cfbf81d3c34457",
        "v13_default_off_shadow_selector_implementation_local_py_compile=passed",
        "v13_default_off_shadow_selector_implementation_local_pytest=20 passed in 0.90s",
        "v13_default_off_shadow_selector_implementation_local_related_pytest=100 passed in 1.21s",
        "v13_default_off_shadow_selector_implementation_execution_camp_head=1c0a5b8ea9720d6e10077b6766a1f45d224eaabe",
        "v13_default_off_shadow_selector_implementation_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_implementation_commit=73412e5f7a861fc232fb34d192faeaa433f4df94",
        "v13_default_off_shadow_selector_implementation_github_refs_heads_main_after_push=73412e5f7a861fc232fb34d192faeaa433f4df94",
        "v13_default_off_shadow_selector_implementation_autodl_sync_method=ssh_bundle_from_verified_github_ref_after_autodl_github_fetch_tls_timeout",
        "v13_default_off_shadow_selector_implementation_autodl_camp_head_after_sync=73412e5f7a861fc232fb34d192faeaa433f4df94",
        "v13_default_off_shadow_selector_implementation_autodl_camp_origin_main_after_sync=73412e5f7a861fc232fb34d192faeaa433f4df94",
        "v13_default_off_shadow_selector_implementation_autodl_dp_head_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_implementation_autodl_pytest=100 passed in 1.39s",
        "v13_default_off_shadow_selector_runtime_flag=--camp_default_off_shadow_selector",
        "v13_default_off_shadow_selector_runtime_default_off=True",
        "v13_default_off_shadow_selector_runtime_schema=dp_camp_v13_default_off_shadow_selector_runtime_v1",
        "v13_default_off_shadow_selector_runtime_effect=records shadow_selected_index while selected_index and executed_index remain DP candidate 0",
        "v13_default_off_shadow_selector_runtime_incompatible_flags_rejected=camp_perfect_tracker_command_postselection,camp_traffic_light_hybrid_postselection,camp_underprogress_relaxation,camp_splice_shadow_rule",
        "v13_default_off_shadow_selector_artifact_contract=manifest_or_explicit_sha256_required_for_atom_scales_and_static_weights_or_checkpoint",
        "v13_default_off_shadow_selector_candidate_count=8",
        "v13_default_off_shadow_selector_score_expression=score_k(w)=a_k^T w",
        "v13_default_off_shadow_selector_candidate_operation=fixed DP candidate reranking only",
        "v13_default_off_shadow_selector_execution_effect=False",
        "v13_default_off_shadow_selector_online_selector_change=False",
        "v13_default_off_shadow_selector_candidate_mutation_allowed=False",
        "v13_default_off_shadow_selector_formal_seed_11_12_13_execution_allowed=False",
        "v13_default_off_shadow_selector_implementation_authorized_next_work=dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract_review_only",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_authorized=True",
    ]:
        assert needle in text


def test_v13_audit_implementation_preserves_no_action_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_selector_promotion_authorized_by_implementation=False",
        "v13_atom_promotion_authorized_by_implementation=False",
        "v13_deployment_authorized_by_implementation=False",
        "v13_training_authorized_by_implementation=False",
        "v13_training_execution_authorized_by_implementation=False",
        "v13_replay_execution_authorized_by_implementation=False",
        "v13_candidate_generation_authorized_by_implementation=False",
        "v13_dp_modification_authorized_by_implementation=False",
        "v13_online_selector_change_authorized_by_implementation=False",
        "v13_executed_trajectory_change_authorized_by_implementation=False",
        "v13_deployable_checkpoint_claim_authorized_by_implementation=False",
        "v13_safety_benefit_claim_authorized_by_implementation=False",
        "v13_camp_over_dp_top1_claim_authorized_by_implementation=False",
        "current_v13_status=default_off_shadow_selector_implementation_complete",
        "current_v13_next_scope=default_off_shadow_selector_post_implementation_static_contract_review_only",
        "production_shadow_selector_implementation_complete=True",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
        "executed_trajectory_change_authorized=False",
        "training_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract_review_only",
    ]:
        assert needle in text


def test_v13_audit_records_training_authorization_update() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_training_authorization_update_status=user_authorized_subsequent_camp_training_tasks",
        "v13_training_authorization_update_user_authorized=True",
        "v13_training_authorization_update_camp_head=46add5d7633587ad75cab9140a4285abbfd9aac6",
        "v13_training_authorization_update_github_refs_heads_main=46add5d7633587ad75cab9140a4285abbfd9aac6",
        "v13_training_authorization_update_autodl_camp_head=46add5d7633587ad75cab9140a4285abbfd9aac6",
        "v13_training_authorization_update_autodl_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_training_authorization_update_training_authorized=True",
        "v13_training_authorization_update_training_execution_authorized=True",
        "v13_training_authorization_update_camp_retraining_authorized=True",
        "v13_training_authorization_update_no_further_training_authorization_prompt_required=True",
        "v13_training_authorization_update_fixed_dp_candidate_reranking_boundary_required=True",
        "v13_training_authorization_update_score_expression_required=score_k(w)=a_k^T w",
        "current_v13_training_authorized_by_user=True",
        "current_v13_training_execution_authorized_by_user=True",
        "current_v13_camp_retraining_authorized_by_user=True",
        "current_v13_no_further_training_authorization_prompt_required=True",
        "next_training_work_may_start_without_extra_user_authorization=True",
    ]:
        assert needle in text


def test_v13_training_authorization_update_preserves_nontraining_boundaries() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_training_authorization_update_formal_seed_11_12_13_authorized=False",
        "v13_training_authorization_update_dp_modification_authorized=False",
        "v13_training_authorization_update_replay_execution_authorized=False",
        "v13_training_authorization_update_candidate_generation_authorized=False",
        "v13_training_authorization_update_selector_promotion_authorized=False",
        "v13_training_authorization_update_atom_promotion_authorized=False",
        "v13_training_authorization_update_deployment_authorized=False",
        "v13_training_authorization_update_online_selector_change_authorized=False",
        "v13_training_authorization_update_safety_benefit_claim_authorized=False",
        "v13_training_authorization_update_camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text


def test_v13_audit_records_shadow_selector_post_implementation_static_review() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_status=dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract_review_complete",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_post_implementation_static_contract_review_8babbc0_7988936_20260628CST",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_json_sha256=0684772d8017a4c249c39c9fcbe87588947d7328cfeb521c36ad4d673312fdbb",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_md_sha256=0687a44d830733f4548456776423359581f4bb8e5d5fb9642352541faadc7180",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_script=scripts/integrations/review_diffusion_planner_dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract.py",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_script_sha256=59fb248099e260533b8ade3c839606e3cb8c04cbbc537fc6f3c46b975cd852e7",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_test=camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract.py",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_test_sha256=2e905e96d101440ec5b53fc59f9d89c284f0e730f6d301f57ab769d3f8747baa",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_commit=79889369f122a0bfca0634a6bc2f0da26dcf1971",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_github_refs_heads_main_after_push=79889369f122a0bfca0634a6bc2f0da26dcf1971",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_autodl_camp_head_after_sync=79889369f122a0bfca0634a6bc2f0da26dcf1971",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_autodl_dp_head_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_local_pytest=112 passed in 1.33s",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_autodl_pytest=64 passed in 0.78s",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_passed=True",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_failed_checks=[]",
        "v13_default_off_shadow_selector_post_implementation_static_contract_review_authorized_next_work=dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_only",
        "v13_default_off_shadow_selector_artifact_manifest_plan_authorized=True",
    ]:
        assert needle in text


def test_v13_shadow_selector_post_static_review_preserves_no_action_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_artifact_manifest_materialization_authorized=False",
        "v13_default_off_shadow_selector_runtime_execution_authorized_by_post_static_review=False",
        "v13_default_off_shadow_selector_selector_promotion_authorized_by_post_static_review=False",
        "v13_default_off_shadow_selector_atom_promotion_authorized_by_post_static_review=False",
        "v13_default_off_shadow_selector_deployment_authorized_by_post_static_review=False",
        "v13_default_off_shadow_selector_replay_execution_authorized_by_post_static_review=False",
        "v13_default_off_shadow_selector_candidate_generation_authorized_by_post_static_review=False",
        "v13_default_off_shadow_selector_dp_modification_authorized_by_post_static_review=False",
        "v13_default_off_shadow_selector_online_selector_change_authorized_by_post_static_review=False",
        "v13_default_off_shadow_selector_safety_benefit_claim_authorized_by_post_static_review=False",
        "v13_default_off_shadow_selector_camp_over_dp_top1_claim_authorized_by_post_static_review=False",
        "v13_default_off_shadow_selector_training_authorization_changed_by_post_static_review=False",
        "v13_default_off_shadow_selector_training_executed_by_post_static_review=False",
        "current_v13_status=default_off_shadow_selector_post_implementation_static_contract_review_complete",
        "current_v13_next_scope=default_off_shadow_selector_artifact_manifest_plan_only",
        "artifact_manifest_plan_authorized=True",
        "artifact_manifest_materialization_authorized=False",
        "runtime_shadow_selector_execution_authorized=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_only",
    ]:
        assert needle in text


def test_v13_audit_records_shadow_selector_artifact_manifest_materialization_plan() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_status=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_ready",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_artifact_manifest_materialization_plan_8babbc0_d1cc73d_20260628T031722CST",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_json_sha256=f2c089fe41d5f2a03c0004fecd3b862bd2cd4dbd884c39b8f5b2546b6ef6f425",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_md_sha256=948131fa19efc3c65cabce2f9ed0853f94555fc75021f77daf8d072ce6e28020",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_script=scripts/integrations/plan_diffusion_planner_dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization.py",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_script_sha256=6f41fe7472b3e7589f371ffa5e9461eb5d6c7113c4a4bd8c82b16cbdbd4e3e91",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_test=camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan.py",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_test_sha256=6c31d529397d0ab5d6878fd398753ff2291ea74334a5e12ae8cfd4efec1c7188",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_execution_camp_head=d1cc73dede0b0f974fbcb96fa4799d7c360e5360",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_runtime_manifest_exists_after_run=False",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_passed=True",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_failed_checks=[]",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_local_pytest=50 passed in 0.83s",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_autodl_pytest=50 passed in 0.36s",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_plan_authorized_next_work=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_only",
    ]:
        assert needle in text


def test_v13_shadow_selector_materialization_plan_preserves_no_action_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_authorized=True",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_authorized=False",
        "v13_default_off_shadow_selector_runtime_execution_authorized_by_artifact_manifest_materialization_plan=False",
        "v13_default_off_shadow_selector_selector_promotion_authorized_by_artifact_manifest_materialization_plan=False",
        "v13_default_off_shadow_selector_atom_promotion_authorized_by_artifact_manifest_materialization_plan=False",
        "v13_default_off_shadow_selector_deployment_authorized_by_artifact_manifest_materialization_plan=False",
        "v13_default_off_shadow_selector_replay_execution_authorized_by_artifact_manifest_materialization_plan=False",
        "v13_default_off_shadow_selector_candidate_generation_authorized_by_artifact_manifest_materialization_plan=False",
        "v13_default_off_shadow_selector_dp_modification_authorized_by_artifact_manifest_materialization_plan=False",
        "v13_default_off_shadow_selector_online_selector_change_authorized_by_artifact_manifest_materialization_plan=False",
        "v13_default_off_shadow_selector_safety_benefit_claim_authorized_by_artifact_manifest_materialization_plan=False",
        "v13_default_off_shadow_selector_camp_over_dp_top1_claim_authorized_by_artifact_manifest_materialization_plan=False",
        "v13_default_off_shadow_selector_training_authorization_changed_by_artifact_manifest_materialization_plan=False",
        "v13_default_off_shadow_selector_training_executed_by_artifact_manifest_materialization_plan=False",
        "current_v13_status=default_off_shadow_selector_artifact_manifest_materialization_plan_complete",
        "current_v13_next_scope=default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_only",
        "artifact_manifest_materialization_static_contract_review_authorized=True",
        "artifact_manifest_materialization_authorized=False",
        "runtime_shadow_selector_execution_authorized=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_only",
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
