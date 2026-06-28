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


def test_v13_audit_records_shadow_selector_artifact_manifest_materialization_static_review() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_status=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_complete",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_8babbc0_cd58f2c_20260628T032524CST",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_json_sha256=563a719753ec7a998a0314d851a4f625bfefc9753d7d3665024ca5b54189cbcd",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_md_sha256=057c6c7b0fc3fde8a8ead8cf0d0f809f66bf37801dad6bf99b21270c4be5df32",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_script=scripts/integrations/review_diffusion_planner_dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract.py",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_script_sha256=586c462bc04365030780670234273712e60d85d002988be1d23211d421c856da",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_test=camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract.py",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_test_sha256=8c940bc6cbb97e4a537167127ee3375a93282355a1ab07217c587ffec4000c74",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_execution_camp_head=cd58f2c9af54375cada7350b6328ab14785182a9",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_planned_runtime_manifest_exists=False",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_passed=True",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_failed_checks=[]",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_local_pytest=93 passed in 1.03s",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_autodl_pytest=93 passed in 0.41s",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_authorized_next_work=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_only",
    ]:
        assert needle in text


def test_v13_shadow_selector_materialization_static_review_preserves_no_action_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_authorized=True",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_authorized=False",
        "v13_default_off_shadow_selector_runtime_execution_authorized_by_artifact_manifest_materialization_static_review=False",
        "v13_default_off_shadow_selector_selector_promotion_authorized_by_artifact_manifest_materialization_static_review=False",
        "v13_default_off_shadow_selector_atom_promotion_authorized_by_artifact_manifest_materialization_static_review=False",
        "v13_default_off_shadow_selector_deployment_authorized_by_artifact_manifest_materialization_static_review=False",
        "v13_default_off_shadow_selector_replay_execution_authorized_by_artifact_manifest_materialization_static_review=False",
        "v13_default_off_shadow_selector_candidate_generation_authorized_by_artifact_manifest_materialization_static_review=False",
        "v13_default_off_shadow_selector_dp_modification_authorized_by_artifact_manifest_materialization_static_review=False",
        "v13_default_off_shadow_selector_online_selector_change_authorized_by_artifact_manifest_materialization_static_review=False",
        "v13_default_off_shadow_selector_safety_benefit_claim_authorized_by_artifact_manifest_materialization_static_review=False",
        "v13_default_off_shadow_selector_camp_over_dp_top1_claim_authorized_by_artifact_manifest_materialization_static_review=False",
        "v13_default_off_shadow_selector_training_authorization_changed_by_artifact_manifest_materialization_static_review=False",
        "v13_default_off_shadow_selector_training_executed_by_artifact_manifest_materialization_static_review=False",
        "current_v13_status=default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_complete",
        "current_v13_next_scope=default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_only",
        "artifact_manifest_materialization_implementation_plan_authorized=True",
        "artifact_manifest_materialization_authorized=False",
        "runtime_shadow_selector_execution_authorized=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_only",
    ]:
        assert needle in text


def test_v13_audit_records_shadow_selector_artifact_manifest_materialization_implementation_plan() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_status=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_ready",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_8babbc0_fab6344_20260628T033752CST",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_json_sha256=ac0b0af7ee78a7d697f394bebc7f5344f4bc943bb8f112c39ac53c0cf4b51123",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_md_sha256=2c6e579531444a53519ab866d2cb63404cc39106b35139a22969e68089f0eafa",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_stdout_log_sha256=2ba80e26bd75e5fef639f2b3c86318152e58bf1917d44e5602a261818de1b19f",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_exit_code_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_script=scripts/integrations/plan_diffusion_planner_dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation.py",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_script_sha256=7daa0b4b7b0176f376a23f59eff374fe8e0734137e363150ee1ce1a8ed4b44ea",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_test=camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan.py",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_test_sha256=dcf16f73363c21beac525c31624a5dba1cdb814742124bdb4cd71b369b4ba4eb",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_execution_camp_head=fab63440a2e224d53e1fa273aa43f2745dcee78c",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_passed=True",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_failed_checks=[]",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_local_pytest=103 passed in 1.12s",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_autodl_pytest=103 passed in 0.30s",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_authorized_next_work=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_only",
    ]:
        assert needle in text


def test_v13_shadow_selector_materialization_implementation_plan_preserves_no_action_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_authorized=True",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_authorized=False",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_authorized=False",
        "v13_default_off_shadow_selector_runtime_execution_authorized_by_artifact_manifest_materialization_implementation_plan=False",
        "v13_default_off_shadow_selector_selector_promotion_authorized_by_artifact_manifest_materialization_implementation_plan=False",
        "v13_default_off_shadow_selector_atom_promotion_authorized_by_artifact_manifest_materialization_implementation_plan=False",
        "v13_default_off_shadow_selector_deployment_authorized_by_artifact_manifest_materialization_implementation_plan=False",
        "v13_default_off_shadow_selector_replay_execution_authorized_by_artifact_manifest_materialization_implementation_plan=False",
        "v13_default_off_shadow_selector_candidate_generation_authorized_by_artifact_manifest_materialization_implementation_plan=False",
        "v13_default_off_shadow_selector_dp_modification_authorized_by_artifact_manifest_materialization_implementation_plan=False",
        "v13_default_off_shadow_selector_online_selector_change_authorized_by_artifact_manifest_materialization_implementation_plan=False",
        "v13_default_off_shadow_selector_safety_benefit_claim_authorized_by_artifact_manifest_materialization_implementation_plan=False",
        "v13_default_off_shadow_selector_camp_over_dp_top1_claim_authorized_by_artifact_manifest_materialization_implementation_plan=False",
        "v13_default_off_shadow_selector_training_authorization_changed_by_artifact_manifest_materialization_implementation_plan=False",
        "v13_default_off_shadow_selector_training_executed_by_artifact_manifest_materialization_implementation_plan=False",
        "current_v13_status=default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_complete",
        "current_v13_next_scope=default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_only",
        "artifact_manifest_materialization_implementation_static_contract_review_authorized=True",
        "artifact_manifest_materialization_implementation_authorized=False",
        "artifact_manifest_materialization_authorized=False",
        "runtime_shadow_selector_execution_authorized=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_only",
    ]:
        assert needle in text


def test_v13_audit_records_shadow_selector_artifact_manifest_materialization_implementation_static_review() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_status=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_complete",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_8babbc0_5d68094_20260628T035221CST",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_json_sha256=ac2415882ae667024f3b018468b8f4b819e01754b1044c8f21891a74a66b248b",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_md_sha256=c2ab832f710b15e580159dc5c1d7c29e598ea5550877846939f074ab958c99f5",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_stdout_log_sha256=72db81ff7cd3b192001e24f93d13ac257b741d298102a466083402f78056915b",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_exit_code_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_script=scripts/integrations/review_diffusion_planner_dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract.py",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_script_sha256=719fde47c997b1742f106a45b08b6e17d1085b1bb77a8961a7131ff046fb295b",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_test=camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract.py",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_test_sha256=08fd594dd2a69e80679c5c4927612fcb0eff757c65dd330a7f869172dedf913d",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_execution_camp_head=5d68094a9867d4275b7a2b0634ea503bf53a9eb3",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_passed=True",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_failed_checks=[]",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_local_pytest=115 passed in 1.35s",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_autodl_pytest=115 passed in 0.45s",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_authorized_next_work=dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_only",
    ]:
        assert needle in text


def test_v13_shadow_selector_materialization_implementation_static_review_preserves_no_action_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_authorized=True",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_authorized=False",
        "v13_default_off_shadow_selector_runtime_execution_authorized_by_artifact_manifest_materialization_implementation_static_review=False",
        "v13_default_off_shadow_selector_selector_promotion_authorized_by_artifact_manifest_materialization_implementation_static_review=False",
        "v13_default_off_shadow_selector_atom_promotion_authorized_by_artifact_manifest_materialization_implementation_static_review=False",
        "v13_default_off_shadow_selector_deployment_authorized_by_artifact_manifest_materialization_implementation_static_review=False",
        "v13_default_off_shadow_selector_replay_execution_authorized_by_artifact_manifest_materialization_implementation_static_review=False",
        "v13_default_off_shadow_selector_candidate_generation_authorized_by_artifact_manifest_materialization_implementation_static_review=False",
        "v13_default_off_shadow_selector_dp_modification_authorized_by_artifact_manifest_materialization_implementation_static_review=False",
        "v13_default_off_shadow_selector_online_selector_change_authorized_by_artifact_manifest_materialization_implementation_static_review=False",
        "v13_default_off_shadow_selector_safety_benefit_claim_authorized_by_artifact_manifest_materialization_implementation_static_review=False",
        "v13_default_off_shadow_selector_camp_over_dp_top1_claim_authorized_by_artifact_manifest_materialization_implementation_static_review=False",
        "v13_default_off_shadow_selector_training_authorization_changed_by_artifact_manifest_materialization_implementation_static_review=False",
        "v13_default_off_shadow_selector_training_executed_by_artifact_manifest_materialization_implementation_static_review=False",
        "current_v13_status=default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_complete",
        "current_v13_next_scope=default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_only",
        "artifact_manifest_materialization_implementation_authorized=True",
        "artifact_manifest_materialization_authorized=False",
        "runtime_shadow_selector_execution_authorized=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_only",
    ]:
        assert needle in text


def test_v13_audit_records_shadow_selector_runtime_artifact_manifest_materializer_implementation() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_status=implemented_tests_passed_no_real_manifest_materialized",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_script=scripts/integrations/build_diffusion_planner_dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest.py",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_script_sha256=8ebfd1ac024a5e537d280b64c28775a3809f78f20179135933f750379b9c3088",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_test=camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer.py",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_test_sha256=56ae8b746fb2cf0de246ea0df7e5e464a821305c6ae0baece90ba3f7bde4e0b8",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_commit=08b482bb3ab13d59f46fa7db9d83669c2e0f10ee",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_github_refs_heads_main_after_push=08b482bb3ab13d59f46fa7db9d83669c2e0f10ee",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_autodl_camp_head_after_sync=08b482bb3ab13d59f46fa7db9d83669c2e0f10ee",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_autodl_dp_head_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_local_pytest=128 passed in 1.43s",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_autodl_pytest=128 passed in 0.50s",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_default_off_before_reading_inputs=True",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_fail_closed_without_output=True",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_verifies_plan_sha256=True",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_verifies_fixed_dp_head=True",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_verifies_output_path_equals_plan=True",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_verifies_atom_scales_sha256=True",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_verifies_static_weights_sha256=True",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_writes_exactly_one_manifest_when_enabled=True",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_no_replay_or_dp_source_touch=True",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_real_runtime_manifest_materialized=False",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_real_replay_executed=False",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_training_executed=False",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_authorized_next_work=dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_only",
    ]:
        assert needle in text


def test_v13_shadow_selector_runtime_artifact_manifest_materializer_implementation_preserves_no_action_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_authorized=True",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_authorized=False",
        "v13_default_off_shadow_selector_runtime_execution_authorized_by_runtime_artifact_manifest_materializer_implementation=False",
        "v13_default_off_shadow_selector_selector_promotion_authorized_by_runtime_artifact_manifest_materializer_implementation=False",
        "v13_default_off_shadow_selector_atom_promotion_authorized_by_runtime_artifact_manifest_materializer_implementation=False",
        "v13_default_off_shadow_selector_deployment_authorized_by_runtime_artifact_manifest_materializer_implementation=False",
        "v13_default_off_shadow_selector_replay_execution_authorized_by_runtime_artifact_manifest_materializer_implementation=False",
        "v13_default_off_shadow_selector_candidate_generation_authorized_by_runtime_artifact_manifest_materializer_implementation=False",
        "v13_default_off_shadow_selector_dp_modification_authorized_by_runtime_artifact_manifest_materializer_implementation=False",
        "v13_default_off_shadow_selector_online_selector_change_authorized_by_runtime_artifact_manifest_materializer_implementation=False",
        "v13_default_off_shadow_selector_safety_benefit_claim_authorized_by_runtime_artifact_manifest_materializer_implementation=False",
        "v13_default_off_shadow_selector_camp_over_dp_top1_claim_authorized_by_runtime_artifact_manifest_materializer_implementation=False",
        "v13_default_off_shadow_selector_training_authorization_changed_by_runtime_artifact_manifest_materializer_implementation=False",
        "v13_default_off_shadow_selector_training_executed_by_runtime_artifact_manifest_materializer_implementation=False",
        "current_v13_status=default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_complete",
        "current_v13_next_scope=default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_only",
        "artifact_manifest_materializer_post_implementation_static_contract_review_authorized=True",
        "artifact_manifest_materialization_authorized=False",
        "runtime_shadow_selector_execution_authorized=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_only",
    ]:
        assert needle in text


def test_v13_audit_records_shadow_selector_runtime_artifact_manifest_materializer_post_static_review() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_status=dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_complete",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_8babbc0_8b16bbf_20260628T041807CST",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_json_sha256=8df61046497d572de5c2c455f3476a139cf8889a5dd9a8ed6a3dcbc877522946",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_md_sha256=9418c4d147e4c49250b0f46f26508b832808efe1108990ff740b5a7aa4f29386",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_stdout_log_sha256=d6f574d6812c1acf7431b2b722069002841f4215b11c05b8adc39ab0e7bd9996",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_exit_code_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_script=scripts/integrations/review_diffusion_planner_dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract.py",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_script_sha256=2e6320e18d12603eedd02e841d3309e187fa1aa388f17e4f9487451888577939",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_test=camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract.py",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_test_sha256=b68b2503f4c5bf60ee743457472f53be38b8f1fe0874291db01b55a0ea7c5688",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_execution_camp_head=8b16bbf0e6748090e1c05f74c199e21488fb8964",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_planned_runtime_manifest_exists=False",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_runtime_manifest_schema=dp_camp_v13_default_off_shadow_selector_runtime_v1",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_runtime_entries=atom_scales,static_weights",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_materialization_plan_sha256=f2c089fe41d5f2a03c0004fecd3b862bd2cd4dbd884c39b8f5b2546b6ef6f425",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_materializer_script_sha256=8ebfd1ac024a5e537d280b64c28775a3809f78f20179135933f750379b9c3088",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_materializer_test_sha256=56ae8b746fb2cf0de246ea0df7e5e464a821305c6ae0baece90ba3f7bde4e0b8",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_replay_runner_sha256=1d5e116cb2c7c473b9c79906a17bc01683dc9b7595a6006c129cc135dedf4813",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_initial_e15b221_attempt_rejected_fail_closed=True",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_initial_e15b221_failed_checks=materializer_artifact_hash_checks,materializer_static_weights_hash_checks",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_initial_e15b221_real_runtime_manifest_materialized=False",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_passed=True",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_failed_checks=[]",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_local_pytest=140 passed in 1.61s",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_autodl_pytest=140 passed in 0.49s",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_authorized_next_work=dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_only",
    ]:
        assert needle in text


def test_v13_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_authorizes_only_materialization() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_complete=True",
        "v13_default_off_shadow_selector_artifact_manifest_materialization_authorized=True",
        "v13_default_off_shadow_selector_runtime_execution_authorized_by_runtime_artifact_manifest_materializer_post_implementation_static_review=False",
        "v13_default_off_shadow_selector_selector_promotion_authorized_by_runtime_artifact_manifest_materializer_post_implementation_static_review=False",
        "v13_default_off_shadow_selector_atom_promotion_authorized_by_runtime_artifact_manifest_materializer_post_implementation_static_review=False",
        "v13_default_off_shadow_selector_deployment_authorized_by_runtime_artifact_manifest_materializer_post_implementation_static_review=False",
        "v13_default_off_shadow_selector_replay_execution_authorized_by_runtime_artifact_manifest_materializer_post_implementation_static_review=False",
        "v13_default_off_shadow_selector_candidate_generation_authorized_by_runtime_artifact_manifest_materializer_post_implementation_static_review=False",
        "v13_default_off_shadow_selector_dp_modification_authorized_by_runtime_artifact_manifest_materializer_post_implementation_static_review=False",
        "v13_default_off_shadow_selector_online_selector_change_authorized_by_runtime_artifact_manifest_materializer_post_implementation_static_review=False",
        "v13_default_off_shadow_selector_safety_benefit_claim_authorized_by_runtime_artifact_manifest_materializer_post_implementation_static_review=False",
        "v13_default_off_shadow_selector_camp_over_dp_top1_claim_authorized_by_runtime_artifact_manifest_materializer_post_implementation_static_review=False",
        "v13_default_off_shadow_selector_training_authorization_changed_by_runtime_artifact_manifest_materializer_post_implementation_static_review=False",
        "v13_default_off_shadow_selector_training_executed_by_runtime_artifact_manifest_materializer_post_implementation_static_review=False",
        "current_v13_status=default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_complete",
        "current_v13_next_scope=default_off_shadow_selector_runtime_artifact_manifest_materialization_only",
        "artifact_manifest_materialization_authorized=True",
        "runtime_shadow_selector_execution_authorized=False",
        "training_execution_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_only",
    ]:
        assert needle in text


def test_v13_audit_records_shadow_selector_runtime_artifact_manifest_materialization() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_status=dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materialized",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_runtime_artifact_manifest_materialization_8babbc0_e10a8cb_20260628T042542CST",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_stdout_log_sha256=0494199d08e52a55c63a37950dcf9af9586881dc119088d80831aac1156bc3c2",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_exit_code_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_exit_code=0",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_artifact_manifest_materialization_plan_8babbc0_d1cc73d_20260628T031722CST/artifact_manifest_materialization_plan.json",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_sha256=f2c089fe41d5f2a03c0004fecd3b862bd2cd4dbd884c39b8f5b2546b6ef6f425",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_manifest_path=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_runtime_manifest_8babbc0_future/dp_camp_v13_default_off_shadow_selector_runtime_manifest.json",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_manifest_preexisted=False",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_manifest_exists_after=True",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_manifest_sha256=bec2e74ae8ea8db314aeffccf518592706d703294a60c129cd24ae1ef7083bf8",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_materializer_script=scripts/integrations/build_diffusion_planner_dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest.py",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_materializer_script_sha256=8ebfd1ac024a5e537d280b64c28775a3809f78f20179135933f750379b9c3088",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_materializer_test=camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer.py",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_materializer_test_sha256=56ae8b746fb2cf0de246ea0df7e5e464a821305c6ae0baece90ba3f7bde4e0b8",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_execution_camp_head=e10a8cb7afed8900683c7629f2becaf4003a2963",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_passed=True",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_failed_checks=[]",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_runtime_manifest_written=True",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_schema=dp_camp_v13_default_off_shadow_selector_runtime_v1",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_manifest_role=default_off_shadow_selector_runtime_artifact_manifest",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_default_off=True",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_selection_effect=False",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_selector_mode=static",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_candidate_operation=fixed DP candidate reranking only",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_executed_output_policy=dp_top1",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_required_candidate_count=8",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_atom_count=14",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_atom_schema_version=dp_camp_v10_14d",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_score_expression=score_k(w)=a_k^T w",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_required_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_current_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_current_camp_head=e10a8cb7afed8900683c7629f2becaf4003a2963",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_artifact_logical_names=atom_scales,static_weights",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_atom_scales_sha256=24ee58d5c4dd0c37f46ed9195e584458675496d8a3a34d1d2883d09bdf1d7d7e",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_weights_sha256=751fbc3a333af0aae483ed50fcfa1abe02361f7bb3d18d8264bf0425019a4752",
        "v13_default_off_shadow_selector_runtime_artifact_manifest_materialization_authorized_next_work=dp_camp_v13_default_off_shadow_selector_runtime_shadow_replay_preflight_only",
    ]:
        assert needle in text


def test_v13_shadow_selector_runtime_artifact_manifest_materialization_preserves_no_action_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_runtime_execution_authorized_by_runtime_artifact_manifest_materialization=False",
        "v13_default_off_shadow_selector_selector_promotion_authorized_by_runtime_artifact_manifest_materialization=False",
        "v13_default_off_shadow_selector_atom_promotion_authorized_by_runtime_artifact_manifest_materialization=False",
        "v13_default_off_shadow_selector_deployment_authorized_by_runtime_artifact_manifest_materialization=False",
        "v13_default_off_shadow_selector_replay_execution_authorized_by_runtime_artifact_manifest_materialization=False",
        "v13_default_off_shadow_selector_candidate_generation_authorized_by_runtime_artifact_manifest_materialization=False",
        "v13_default_off_shadow_selector_dp_modification_authorized_by_runtime_artifact_manifest_materialization=False",
        "v13_default_off_shadow_selector_online_selector_change_authorized_by_runtime_artifact_manifest_materialization=False",
        "v13_default_off_shadow_selector_safety_benefit_claim_authorized_by_runtime_artifact_manifest_materialization=False",
        "v13_default_off_shadow_selector_camp_over_dp_top1_claim_authorized_by_runtime_artifact_manifest_materialization=False",
        "v13_default_off_shadow_selector_training_authorization_changed_by_runtime_artifact_manifest_materialization=False",
        "v13_default_off_shadow_selector_training_executed_by_runtime_artifact_manifest_materialization=False",
        "current_v13_status=default_off_shadow_selector_runtime_artifact_manifest_materialized",
        "current_v13_next_scope=default_off_shadow_selector_runtime_shadow_replay_preflight_only",
        "runtime_artifact_manifest_materialized=True",
        "runtime_shadow_replay_preflight_authorized=True",
        "runtime_shadow_selector_execution_authorized=False",
        "training_execution_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "candidate_generation_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_runtime_shadow_replay_preflight_only",
    ]:
        assert needle in text


def test_v13_audit_records_shadow_selector_runtime_shadow_replay_preflight() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_status=dp_camp_v13_default_off_shadow_selector_runtime_shadow_replay_preflight_ready",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_runtime_shadow_replay_preflight_8babbc0_27013cf_20260628T043224CST",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_json_sha256=2f4e5bb33dab425461e087200c4d1dc620ddd59a508dc03c804f37e4059efd28",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_md_sha256=ab70d8e8b0ef67ea628b943f0bba6187b66d405a7da111a46c883c6709a48f28",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_stdout_log_sha256=557946e09e46cce368e1d4ff54fc772f9e1a7aa5873da44c4c8eb40f1bcef4e8",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_exit_code_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_execution_camp_head=27013cf19f1382343a66ab28ed88ff51f00d1a78",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_runner=scripts/integrations/run_diffusion_planner_camp_replay.py",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_runner_sha256=1d5e116cb2c7c473b9c79906a17bc01683dc9b7595a6006c129cc135dedf4813",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_runtime_manifest_sha256=bec2e74ae8ea8db314aeffccf518592706d703294a60c129cd24ae1ef7083bf8",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_route_name=sample_normal",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_seed=301",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_seed_is_formal=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_formal_seeds=11,12,13",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_max_npcs=0",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_traffic_lights=off",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_steps=100",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_num_candidates=8",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_planned_replay_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_shadow_replay_smoke_8babbc0_27013cf_20260628T043224CST/sample_normal/seed_301/npc_0/spawn_0p3/tl_off/static_shadow",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_planned_output_absent=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_command_uses_shadow_selector=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_command_uses_shadow_manifest=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_command_selector_mode=static",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_command_fallback_mode=learned",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_command_feasibility_source=dp_reward",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_command_has_no_guidance_or_reference_blend=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_command_has_no_postselection_relaxation_or_splice=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_manifest_default_off=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_manifest_selection_effect=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_manifest_candidate_operation=fixed DP candidate reranking only",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_manifest_executed_output_policy=dp_top1",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_manifest_score_expression=score_k(w)=a_k^T w",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_atom_scales_sha256=24ee58d5c4dd0c37f46ed9195e584458675496d8a3a34d1d2883d09bdf1d7d7e",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_static_weights_sha256=751fbc3a333af0aae483ed50fcfa1abe02361f7bb3d18d8264bf0425019a4752",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_runner_shadow_forces_dp_top1=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_runner_records_shadow_selected_index=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_runner_rejects_incompatible_shadow_flags=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_passed=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_failed_checks=[]",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_authorized_next_work=dp_camp_v13_default_off_shadow_selector_runtime_shadow_replay_execution_only",
    ]:
        assert needle in text


def test_v13_shadow_selector_runtime_shadow_replay_preflight_authorizes_only_nonformal_shadow_execution() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_shadow_replay_execution_authorized_next=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_formal_seeds_authorized=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_candidate_generation_by_camp_authorized=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_dp_modification_authorized=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_training_executed=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_selector_promotion_authorized=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_deployment_authorized=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_safety_benefit_claim_authorized=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_preflight_camp_over_dp_top1_claim_authorized=False",
        "current_v13_status=default_off_shadow_selector_runtime_shadow_replay_preflight_complete",
        "current_v13_next_scope=default_off_shadow_selector_runtime_shadow_replay_execution_only",
        "runtime_shadow_selector_execution_authorized=True",
        "replay_execution_authorized_by_current_boundary=True",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=True",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "training_execution_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_runtime_shadow_replay_execution_only",
    ]:
        assert needle in text


def test_v13_audit_records_shadow_selector_runtime_shadow_replay_smoke_execution() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_status=dp_camp_v13_default_off_shadow_selector_runtime_shadow_replay_execution_smoke_passed",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_runtime_shadow_replay_execution_8babbc0_84b696d_20260628T043607CST",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_replay_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_shadow_replay_smoke_8babbc0_27013cf_20260628T043224CST/sample_normal/seed_301/npc_0/spawn_0p3/tl_off/static_shadow",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_command_sha256=b2d8a8cf4d159eadc0c856c02f757a96cda3207ec588c87c52a515c6738eb30e",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_stdout_log_sha256=d9d3199328b30fc0192cd7d952e458ceda28670cdbd94b75d1f7090fc9278cb9",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_stderr_log_sha256=b45b6516d6e65b6029bf1ed3d8a985ef9546be6079f71da16a9db5a5e944b298",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_exit_code_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_exit_code=0",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_validation_json_sha256=d7c5bdcc132b7a5d4c6abc265e9169b0b88e378727a7848eb50e231651c6b017",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_validation_md_sha256=b68d0707c20552160a3ebcfa978b4193057a0fb9f4222f294cd05ebf56ee7be1",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_preflight_json_sha256=2f4e5bb33dab425461e087200c4d1dc620ddd59a508dc03c804f37e4059efd28",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_runner_sha256=1d5e116cb2c7c473b9c79906a17bc01683dc9b7595a6006c129cc135dedf4813",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_camp_replay_summary_sha256=a8a67051c4d128aa36d152752fc59afe9ed07e46d1b8ba5c81ddce4357f6ea75",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_camp_validation_summary_sha256=ea4ea0446c55d23ccb2d46091f8b9a0940de60e8cba9dadddf616b6d80ffcca4",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_camp_selection_log_sha256=29a63041d506fee646d06594bb627ba28ca214538ee2c12dad38d50fdaa1acbc",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_camp_head=84b696d0ad56458d1d09871319ffc169e4f53a2f",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_route_name=sample_normal",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_seed=301",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_seed_is_formal=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_steps=100",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_num_candidates=8",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_selector_mode=static",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_candidate_reference_blend=None",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_records=100",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_shadow_records=100",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_failed_shadow_records=0",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_executed_indices=[0]",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_selected_indices_in_records=[0]",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_shadow_selected_index_counts={\"0\":4,\"1\":18,\"2\":13,\"3\":16,\"4\":6,\"5\":13,\"6\":19,\"7\":11}",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_nonzero_shadow_selection_count=96",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_all_shadow_artifact_contract_ready=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_all_shadow_selection_effect_false=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_all_shadow_executed_policy_dp_top1=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_all_shadow_candidate_operation_fixed=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_all_shadow_score_affine=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_summary_shadow_scores_routed_to_execution=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_summary_executed_top1_all=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_manifest_sha256=bec2e74ae8ea8db314aeffccf518592706d703294a60c129cd24ae1ef7083bf8",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_validation_passed=True",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_validation_failed_checks=[]",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_authorized_next_work=dp_camp_v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_only",
    ]:
        assert needle in text


def test_v13_shadow_selector_runtime_shadow_replay_smoke_keeps_claims_and_training_closed() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_formal_seeds_executed=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_training_executed=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_dp_modified=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_selector_promoted=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_deployed=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_safety_benefit_claim_authorized=False",
        "v13_default_off_shadow_selector_runtime_shadow_replay_execution_camp_over_dp_top1_claim_authorized=False",
        "current_v13_status=default_off_shadow_selector_runtime_shadow_replay_smoke_execution_passed",
        "current_v13_next_scope=default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_only",
        "broader_nonformal_shadow_replay_batch_preflight_authorized=True",
        "runtime_shadow_selector_execution_authorized=False",
        "replay_execution_authorized_by_current_boundary=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "training_execution_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_only",
    ]:
        assert needle in text


def test_v13_audit_records_broader_nonformal_shadow_replay_batch_preflight() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_status=dp_camp_v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_ready",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_8babbc0_72baf98_20260628T044649CST",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_json_sha256=463ca11600f53e788056b2ccef950a312e44a5fb9c181cd46037b2eb22f09646",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_md_sha256=421e5b3e6231ab3727eeec1a7732b11d8ffac626f4507cdece3069ef2b0ebc6e",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_runbook_sha256=21eea733783bb3151e8ea50ddb01660f64c7a697183cd2a6a3ffcb35b0500909",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_stdout_log_sha256=223adde7dd90b816d0acace3e00ec4fcc49900be0cb92e440115e406bc3cc716",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_exit_code_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_execution_camp_head=72baf9855178adc04665dbfbf3e3c3c57b9b2a22",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_runner_sha256=1d5e116cb2c7c473b9c79906a17bc01683dc9b7595a6006c129cc135dedf4813",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_runtime_manifest_sha256=bec2e74ae8ea8db314aeffccf518592706d703294a60c129cd24ae1ef7083bf8",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_base_replay_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_8babbc0_72baf98_20260628T044649CST",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_command_count=32",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_routes=nishi_lane_change,nishi_release,sample_normal,sample_tl",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_seeds=301,302",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_formal_seeds=11,12,13",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_formal_seeds_excluded=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_max_npcs_values=0,4",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_traffic_light_modes=on,off",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_steps_per_command=100",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_num_candidates=8",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_all_planned_outputs_absent=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_manifest_default_off=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_manifest_selection_effect=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_manifest_candidate_operation=fixed DP candidate reranking only",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_manifest_executed_output_policy=dp_top1",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_manifest_score_expression=score_k(w)=a_k^T w",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_atom_scales_sha256=24ee58d5c4dd0c37f46ed9195e584458675496d8a3a34d1d2883d09bdf1d7d7e",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_static_weights_sha256=751fbc3a333af0aae483ed50fcfa1abe02361f7bb3d18d8264bf0425019a4752",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_all_commands_use_shadow_selector=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_all_commands_use_shadow_manifest=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_all_commands_selector_mode_static=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_all_commands_num_candidates_8=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_all_commands_no_guidance_or_reference_blend=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_all_commands_no_postselection_relaxation_or_splice=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_runner_shadow_forces_dp_top1=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_runner_records_shadow_selected_index=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_expected_completed_commands=32",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_expected_records=3200",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_expected_shadow_records=3200",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_executed_indices_allowed=[0]",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_shadow_scores_routed_to_execution_required=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_passed=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_failed_checks=[]",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_authorized_next_work=dp_camp_v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_only",
    ]:
        assert needle in text


def test_v13_broader_nonformal_shadow_replay_batch_preflight_authorizes_only_batch_execution() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_batch_execution_authorized_next=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_formal_seeds_authorized=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_candidate_generation_by_camp_authorized=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_dp_modification_authorized=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_training_executed=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_selector_promotion_authorized=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_deployment_authorized=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_safety_benefit_claim_authorized=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_camp_over_dp_top1_claim_authorized=False",
        "current_v13_status=default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight_complete",
        "current_v13_next_scope=default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_only",
        "broader_nonformal_shadow_replay_batch_execution_authorized=True",
        "runtime_shadow_selector_execution_authorized=True",
        "replay_execution_authorized_by_current_boundary=True",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=True",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "training_execution_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_only",
    ]:
        assert needle in text


def test_v13_audit_records_broader_nonformal_shadow_replay_batch_execution() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_status=dp_camp_v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_passed",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_8babbc0_aa04ff6_20260628T045051CST",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_validation_json_sha256=3ef1127d8cc8f273a1cdda5e53862cbee2b8951d02bd96e2f4a7321c5d66cca6",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_validation_md_sha256=2dabda44135c27324368a5f4b6e15fd226cdad09b5787d231ff5db59ab290845",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_replay_output_hash_manifest_sha256=a1e686086779a3070aba2683b9ad1540f7fd1fa6c03aa9322f9b410341115c3b",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_raw_summary_sha256=8c5c181f5de34819fb9b22ad61e19d7564c299f25463bd8d2927a5563a341b20",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_progress_jsonl_sha256=6bc1a67a3c33faf1bf1f43842923f094142800cf677085fa0d248275af58570f",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_failures_txt_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_run_batch_py_sha256=a06dde6f543b231ebbe4a7a0c8e4ce08dffbcdbd248b2d039d2c0f68ce589d6e",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_run_batch_sh_sha256=10553d602df9ea3dffe6c00ad90bff0413208dac341a5ee676ddbee1bd7006a3",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_head_txt_sha256=0ce2299fa58e09791c773fc7a3163c4acc3a229255922fa0eb5af37b4c21f18e",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_schema_version=dp_camp_v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_validation_v1",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_camp_head=aa04ff6cc818d3f2fc44a285a1848ca89d62a355",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_command_count=32",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_completed_commands=32",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_failed_commands=0",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_records=3200",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_shadow_records=3200",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_failed_shadow_records=0",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_executed_indices=[0]",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_selected_indices_in_records=[0]",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_shadow_selected_index_counts={\"0\":695,\"1\":358,\"2\":312,\"3\":371,\"4\":391,\"5\":382,\"6\":393,\"7\":298}",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_nonzero_shadow_selection_count=2505",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_route_records={\"nishi_lane_change\":800,\"nishi_release\":800,\"sample_normal\":800,\"sample_tl\":800}",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_seed_records={\"301\":1600,\"302\":1600}",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_npc_records={\"0\":1600,\"4\":1600}",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_traffic_light_records={\"off\":1600,\"on\":1600}",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_all_shadow_artifact_contract_ready=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_all_shadow_selection_effect_false=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_all_shadow_executed_policy_dp_top1=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_all_shadow_candidate_operation_fixed=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_all_shadow_score_affine=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_all_shadow_scores_not_routed=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_all_executed_top1_all=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_passed=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_failed_checks=[]",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_authorized_next_work=dp_camp_v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_only",
    ]:
        assert needle in text


def test_v13_broader_nonformal_shadow_replay_batch_execution_keeps_training_and_claims_closed() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_formal_seeds_executed=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_training_executed=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_dp_modified=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_selector_promoted=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_deployed=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_safety_benefit_claim_authorized=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_camp_over_dp_top1_claim_authorized=False",
        "current_v13_status=default_off_shadow_selector_broader_nonformal_shadow_replay_batch_execution_complete",
        "current_v13_next_scope=default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_only",
        "current_v13_all_subsequent_training_tasks_authorized_by_user=True",
        "current_v13_no_further_training_authorization_prompt_required=True",
        "broader_nonformal_shadow_replay_batch_result_review_authorized=True",
        "runtime_shadow_selector_execution_authorized=False",
        "replay_execution_authorized_by_current_boundary=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "training_execution_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_only",
    ]:
        assert needle in text


def test_v13_audit_records_broader_nonformal_shadow_replay_batch_result_review() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_status=dp_camp_v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_ready",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_8babbc0_df09abf_20260628T051522CST",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_json_sha256=d57c313cf88d3606dd440b6a82f2885d8ad489ffdb2e11f19ea07b2f0d03d4a5",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_md_sha256=70b3f47de10016dadf85dc151025cde9ac05801e1ababe5528970fa6255d37e5",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_script_sha256=e53e7d023a802aeaa7b52d7ed0dd84bb166275a413831ddffb4c9317e52f3d97",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_stdout_log_sha256=bc89ead73c4db20e00435e3724fcfa09833bf6e834292125dd1cf59232341821",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_exit_code_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_schema_version=dp_camp_v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_v1",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_source_execution_validation_json_sha256=3ef1127d8cc8f273a1cdda5e53862cbee2b8951d02bd96e2f4a7321c5d66cca6",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_source_replay_output_hash_manifest_sha256=a1e686086779a3070aba2683b9ad1540f7fd1fa6c03aa9322f9b410341115c3b",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_camp_head=df09abf213e8500a4e7e42e68ad9e345ec795ada",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_command_count=32",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_records=3200",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_shadow_records=3200",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_executed_indices=[0]",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_selected_indices_in_records=[0]",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_nonzero_shadow_selection_count=2505",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_shadow_nonzero_selection_rate=0.7828125",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_review_conclusion=shadow_selector_live_execution_invariant_hold_nonpromotion_evidence_only",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_camp_role_confirmed=current_tick_fixed_dp_candidate_reranker_only",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_dp_role_confirmed=fixed_black_box_candidate_trajectory_generator",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_candidate_operation_confirmed=fixed DP candidate reranking only",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_score_expression_confirmed=score_k(w)=a_k^T w",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_executed_output_policy_confirmed=dp_top1",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_training_data_interpretation=runtime_shadow_replay_evidence_not_new_training_dataset",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_additional_training_data_need=larger_nonformal_fixed_dp_candidate_sets_if_retraining_or_selector_revision_is_pursued",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_passed=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_failed_checks=[]",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_authorized_next_work=dp_camp_v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_only",
    ]:
        assert needle in text


def test_v13_broader_nonformal_shadow_replay_batch_result_review_authorizes_only_training_preflight() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_candidate_expansion_retraining_preflight_authorized_by_review=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_fixed_dp_candidate_generation_execution_authorized_by_review=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_training_execution_authorized_by_review=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_replay_execution_authorized_by_review=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_candidate_generation_by_camp_authorized_by_review=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_dp_modification_authorized_by_review=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_selector_promotion_authorized_by_review=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_deployment_authorized_by_review=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_safety_benefit_claim_authorized_by_review=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_camp_over_dp_top1_claim_authorized_by_review=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_formal_seeds_11_12_13_authorized_by_review=False",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_current_user_training_authorization_recorded=True",
        "v13_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_no_further_training_authorization_prompt_required=True",
        "current_v13_status=default_off_shadow_selector_broader_nonformal_shadow_replay_batch_result_review_complete",
        "current_v13_next_scope=nonformal_fixed_dp_candidate_expansion_retraining_preflight_only",
        "nonformal_fixed_dp_candidate_expansion_retraining_preflight_authorized=True",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_only",
    ]:
        assert needle in text


def test_v13_audit_records_candidate_expansion_retraining_preflight() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_status=dp_camp_v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_ready",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_retraining_preflight_8babbc0_d070690_20260628T052201CST",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_json_sha256=a1baa7e02b49d5b805ccd4cf3309923a8c1f4a13064f28e4fa34f6a01c50c0c1",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_md_sha256=941736254129bcb4205df71fc140457d92ddded4048b0b57fe5de1eab81ebd0c",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_script_sha256=22222c500e247e5c45c907189f44f8b0b3de11346054ac4231688a6c95a78aa1",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_stdout_log_sha256=548df99d554b883133156891167947dc0e7d9c3ea791d6bbb9f6f6133227fd5b",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_command_plan_json_sha256=4e5927c1eb6f8d021d3daf67cd6f1226b0d133668476ec11b032d71f76572598",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_collection_runbook_sha256=114d46f23ff73cc7765f4a29e146b5421fea9267fe39e516417b12feac797129",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_pipeline_runbook_sha256=3acca91a8ef5f7bf87acad70f0fdec8e5333307bfddf2846763555877e6bac5c",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_schema_version=dp_camp_v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_v1",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_source_result_review_json_sha256=d57c313cf88d3606dd440b6a82f2885d8ad489ffdb2e11f19ea07b2f0d03d4a5",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_base_collection_summary_json_sha256=5ce2e4066a0652f994b21b5f6c24696cfc114be0bb1b38b783fb8d21c22d23e4",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_base_pipeline_summary_json_sha256=bde0f4396017422888b99a9c731a54d6cb007cae7aaab3012cd08cf67bca6b0d",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_camp_head=d0706908e9d13d28040854776c62fd1885a9c68a",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_addon_collection_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_addon_collection_8babbc0_d070690_20260628T052201CST",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_combined_retraining_pipeline_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_combined_retraining_8babbc0_d070690_20260628T052201CST",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_routes=sample_normal,sample_tl,nishi_release,nishi_lane_change",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_seeds=333,334,335,336,337,338,339,340,341,342,343,344,345,346,347,348,349,350,351,352,353,354,355,356,357,358,359,360,361,362,363,364",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_formal_seeds_excluded=True",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_expected_addon_replay_commands=512",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_expected_addon_records_total=51200",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_expected_combined_selection_logs=1024",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_expected_combined_records_total=102400",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_planned_outputs_absent=True",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_planned_output_paths_unique=True",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_candidate_operation=fixed DP candidate generation for addon, then CAMP fixed-candidate reranking training only",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_dp_role=fixed_black_box_candidate_trajectory_generator",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_camp_role=current_tick_fixed_dp_candidate_reranker_only",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_score_expression=score_k(w)=a_k^T w",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_training_objective=simplex_hinge_cvar_l2",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_training_seed=29",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_training_seed_is_formal_seed=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_passed=True",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_failed_checks=[]",
    ]:
        assert needle in text


def test_v13_candidate_expansion_retraining_preflight_authorizes_only_execution_gate() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_fixed_dp_candidate_generation_execution_authorized_next=True",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_replay_execution_authorized_next=True",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_training_execution_authorized_next=True",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_no_further_training_authorization_prompt_required=True",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_authorized_next_work=dp_camp_v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_only",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_candidate_generation_by_camp_authorized=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_trajectory_generation_by_camp_authorized=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_trajectory_modification_by_camp_authorized=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_reference_blend_authorized=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_guidance_authorized=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_dp_modification_authorized=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_formal_seeds_11_12_13_authorized=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_selector_promotion_authorized=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_deployment_authorized=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_safety_benefit_claim_authorized=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_preflight_camp_over_dp_top1_claim_authorized=False",
        "current_v13_status=nonformal_fixed_dp_candidate_expansion_retraining_preflight_complete",
        "current_v13_next_scope=nonformal_fixed_dp_candidate_expansion_retraining_execution_only",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=True",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=True",
        "replay_execution_authorized_by_current_boundary=True",
        "training_execution_authorized_by_current_boundary=True",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_only",
    ]:
        assert needle in text


def test_v13_audit_records_candidate_expansion_retraining_execution() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_status=dp_camp_v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_complete",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_retraining_execution_8babbc0_24d4a54_20260628T052700CST",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_addon_collection_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_addon_collection_8babbc0_d070690_20260628T052201CST",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_combined_retraining_pipeline_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_combined_retraining_8babbc0_d070690_20260628T052201CST",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_validation_json_sha256=6a1a024e65955eb77be0c11cd0f9f705ddae57c063f984b9491401af34dfa550",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_pipeline_summary_json_sha256=a5f9b2651413987d63eee94329af1eedcd6346d27fb97d3b3709ac68f1799e79",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_training_summary_json_sha256=b23427d33438216eccb51e79c3c901bb81df13abc1e722c9f18d2b5c8030e876",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_weights_json_sha256=490c8ecee1a8981e73888f63217a85b48f8fd7134bccf3f8c4519fdc227c4e30",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_weights_npy_sha256=b7981a9740cc3cfb6354726833997009a4f2da1914dd764a5dfb6b008b48a182",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_atom_scales_json_sha256=3b9abfaaa98e80a1a1b93635cd9ced1f7e8cbe910539549f4722e04b92a6c498",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_camp_head=24d4a5465cf11f0014de92465d3211d4bfc872cc",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_addon_selection_log_count=512",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_addon_failed_replay_commands=0",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_addon_records_total=51200",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_addon_formal_seed_path_matches=0",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_addon_candidate_counts=[8]",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_pipeline_status=complete",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_expected_combined_selection_logs=1024",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_expected_combined_records_total=102400",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_dataset_records_total=102400",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_dataset_records_built=28468",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_split_training_records=22836",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_split_validation_records=5632",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_training_type=dp_native_fallback_risk_static_candidate_reranking",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_training_executed=True",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_fixed_dp_candidate_reranking_only=True",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_fallback_only_training=True",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_score_expression=score_k(w)=a_k^T w",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_objective=simplex_hinge_cvar_l2",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_training_seed=29",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_training_seed_is_formal_seed=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_training_records=22836",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_validation_records=5632",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_weights_sum=1.0",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_weights_min=0.0",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_weights_max=0.22686531780689087",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_train_oracle_match_rate=0.3148099492030128",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_validation_oracle_match_rate=0.3146306818181818",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_passed=True",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_failed_checks=[]",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_authorized_next_work=dp_camp_v13_candidate_expansion_retraining_post_training_nonpromotion_and_holdout_audits_only",
    ]:
        assert needle in text


def test_v13_candidate_expansion_retraining_execution_authorizes_only_post_training_audits() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_candidate_generation_by_camp_executed=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_trajectory_generation_executed=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_trajectory_rewrite_executed=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_diffusion_planner_modified=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_selector_promotion_executed=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_atom_promotion_executed=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_online_selector_change_executed=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_safety_benefit_claim_executed=False",
        "v13_nonformal_fixed_dp_candidate_expansion_retraining_execution_camp_over_dp_top1_claim_executed=False",
        "current_v13_status=nonformal_fixed_dp_candidate_expansion_retraining_execution_complete",
        "current_v13_next_scope=candidate_expansion_retraining_post_training_nonpromotion_and_holdout_audits_only",
        "current_v13_true_camp_training_has_executed=True",
        "current_v13_all_subsequent_training_tasks_authorized_by_user=True",
        "current_v13_no_further_training_authorization_prompt_required=True",
        "candidate_expansion_retraining_post_training_nonpromotion_audit_authorized=True",
        "candidate_expansion_retraining_development_holdout_audit_authorized=True",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "next_work_target=dp_camp_v13_candidate_expansion_retraining_post_training_nonpromotion_and_holdout_audits_only",
    ]:
        assert needle in text


def test_v13_audit_records_candidate_expansion_retraining_post_training_audits() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_retraining_post_training_audits_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_retraining_post_training_audits_8babbc0_4c522f6_20260628T092831CST",
        "v13_candidate_expansion_retraining_post_training_audits_heads_sha256=5663c0ee57337af6aa6aaa064b5cd3ea611b93f23ec0bdbea3bb6d854628b16e",
        "v13_candidate_expansion_retraining_post_training_audits_execution_camp_head=4c522f61f4a2101bf81a3fda002f0d624ad70db7",
        "v13_candidate_expansion_retraining_post_training_audits_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_audit_json_sha256=97c8403278e0aef7612e2819da5435dcd16ddc37de3705d2d67eff900559b38d",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_audit_md_sha256=bf0bad06027edbbf7ae53fc599055957269189dd6c883f56f8c6f95fb5d3cd5e",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_audit_script_sha256=be1ed115248de058b98050035e6022fe03459c5d7f2a2993b85b40b4a463ca47",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_audit_status=dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_complete",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_audit_passed=True",
        "v13_candidate_expansion_retraining_post_training_training_artifacts_nonpromotion=True",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_fixed_dp_candidate_reranking_only=True",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_fallback_only_training_artifact=True",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_score_expression=score_k(w)=a_k^T w",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_training_commit=24d4a5465cf11f0014de92465d3211d4bfc872cc",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_training_summary_sha256_match=True",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_weights_json_sha256_match=True",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_weights_npy_sha256_match=True",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_weights_json_simplex_nonnegative=True",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_weights_npy_simplex_nonnegative=True",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_weights_json_matches_npy=True",
        "v13_candidate_expansion_retraining_post_training_nonpromotion_atom_scales_strictly_positive=True",
        "v13_candidate_expansion_retraining_post_training_holdout_audit_json_sha256=ed0d7c907e1bc18d11f2d2ca3827f0430ac5ada1ac13b0e7b4c3cef31e976d9a",
        "v13_candidate_expansion_retraining_post_training_holdout_audit_md_sha256=2a45beb176decbad837b7cdc50ffaddb5fd4d0ea450144fd32597672deac6f4b",
        "v13_candidate_expansion_retraining_post_training_holdout_audit_script_sha256=c3d58672a41512e412fea5b3a5d4e977a037b4d3d6b43878e348dcc142b7fae4",
        "v13_candidate_expansion_retraining_post_training_holdout_audit_status=dp_native_fallback_risk_static_camp_training_development_holdout_acceptance_audit_complete",
        "v13_candidate_expansion_retraining_post_training_holdout_audit_passed=True",
        "v13_candidate_expansion_retraining_post_training_holdout_records_scope=validation_groups_only",
        "v13_candidate_expansion_retraining_post_training_holdout_fallback_branch_only=True",
        "v13_candidate_expansion_retraining_post_training_holdout_records_without_feasible_candidate_only=True",
        "v13_candidate_expansion_retraining_post_training_holdout_selection_rule=argmin_k score_k(w)",
        "v13_candidate_expansion_retraining_post_training_holdout_validation_records=5632",
        "v13_candidate_expansion_retraining_post_training_holdout_candidate_count_unchanged=True",
        "v13_candidate_expansion_retraining_post_training_holdout_candidate_tensor_unchanged=True",
        "v13_candidate_expansion_retraining_post_training_holdout_selected_index_in_range=True",
        "v13_candidate_expansion_retraining_post_training_holdout_source_hashes_present=True",
        "v13_candidate_expansion_retraining_post_training_holdout_static_oracle_match_rate=0.3146306818181818",
        "v13_candidate_expansion_retraining_post_training_holdout_static_mean_margin_violation=1.802658601813674",
        "v13_candidate_expansion_retraining_post_training_holdout_recorded_oracle_match_rate=0.12855113636363635",
        "v13_candidate_expansion_retraining_post_training_holdout_candidate0_oracle_match_rate=0.34144176136363635",
    ]:
        assert needle in text


def test_v13_candidate_expansion_retraining_post_training_audits_authorize_only_result_review() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_retraining_post_training_training_execution_authorized=False",
        "v13_candidate_expansion_retraining_post_training_replay_execution_authorized=False",
        "v13_candidate_expansion_retraining_post_training_candidate_generation_authorized=False",
        "v13_candidate_expansion_retraining_post_training_dp_modification_authorized=False",
        "v13_candidate_expansion_retraining_post_training_selector_promotion_authorized=False",
        "v13_candidate_expansion_retraining_post_training_atom_promotion_authorized=False",
        "v13_candidate_expansion_retraining_post_training_deployment_authorized=False",
        "v13_candidate_expansion_retraining_post_training_safety_benefit_claim_authorized=False",
        "v13_candidate_expansion_retraining_post_training_camp_over_dp_top1_claim_authorized=False",
        "current_v13_status=candidate_expansion_retraining_post_training_audits_complete",
        "current_v13_next_scope=candidate_expansion_retraining_result_review_before_any_promotion_decision_only",
        "current_v13_true_camp_training_has_executed=True",
        "current_v13_all_subsequent_training_tasks_authorized_by_user=True",
        "candidate_expansion_retraining_post_training_audits_complete=True",
        "candidate_expansion_retraining_result_review_authorized=True",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "next_work_target=dp_camp_v13_candidate_expansion_retraining_result_review_before_any_promotion_decision_only",
    ]:
        assert needle in text


def test_v13_audit_records_candidate_expansion_retraining_result_review() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_retraining_result_review_status=dp_camp_v13_offline_nonpromotion_static_reranker_result_review_ready",
        "v13_candidate_expansion_retraining_result_review_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_retraining_result_review_8babbc0_e4e2ad8_20260628T094006CST",
        "v13_candidate_expansion_retraining_result_review_json_sha256=4a349342ad3514e7d2ec9e8dba565c0fd231163710a0b1812e28eb5576872574",
        "v13_candidate_expansion_retraining_result_review_md_sha256=187a41b026cdef53535a426a2fb49ef758d1850d94f9a0ecdfd9fd5d1c27f0ee",
        "v13_candidate_expansion_retraining_result_review_heads_sha256=112ed36e52f481317ba0e912c3de24fab885012249ea2ea402be3513d2ebbb79",
        "v13_candidate_expansion_retraining_result_review_script_sha256=44162cb30f314f5995b181461c7e4023edba2e4305f28e50e0289cbae70eeeae",
        "v13_candidate_expansion_retraining_result_review_execution_camp_head=e4e2ad86f1070b754e3d04627d7c54349a123824",
        "v13_candidate_expansion_retraining_result_review_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_candidate_expansion_retraining_result_review_passed=True",
        "v13_candidate_expansion_retraining_result_review_failed_checks=[]",
        "v13_candidate_expansion_retraining_result_review_ready=True",
        "v13_candidate_expansion_retraining_result_review_authorized_next_work=dp_camp_v13_promotion_decision_plan_only_after_explicit_user_authorization",
        "v13_candidate_expansion_retraining_result_review_collection_summary_sha256=4addd267d8bf14c73945610cf3b7196db874c5f6994a9725967ea0a07dfd231c",
        "v13_candidate_expansion_retraining_result_review_pipeline_summary_sha256=a5f9b2651413987d63eee94329af1eedcd6346d27fb97d3b3709ac68f1799e79",
        "v13_candidate_expansion_retraining_result_review_training_summary_sha256=b23427d33438216eccb51e79c3c901bb81df13abc1e722c9f18d2b5c8030e876",
        "v13_candidate_expansion_retraining_result_review_nonpromotion_audit_sha256=97c8403278e0aef7612e2819da5435dcd16ddc37de3705d2d67eff900559b38d",
        "v13_candidate_expansion_retraining_result_review_holdout_audit_sha256=ed0d7c907e1bc18d11f2d2ca3827f0430ac5ada1ac13b0e7b4c3cef31e976d9a",
        "v13_candidate_expansion_retraining_result_review_records_total=102400",
        "v13_candidate_expansion_retraining_result_review_records_without_feasible_candidate=28468",
        "v13_candidate_expansion_retraining_result_review_records_with_feasible_candidate=73932",
        "v13_candidate_expansion_retraining_result_review_training_records=22836",
        "v13_candidate_expansion_retraining_result_review_validation_records=5632",
        "v13_candidate_expansion_retraining_result_review_num_candidates=8",
        "v13_candidate_expansion_retraining_result_review_num_atoms=14",
        "v13_candidate_expansion_retraining_result_review_atom_schema_version=dp_camp_v10_14d",
        "v13_candidate_expansion_retraining_result_review_score_expression=score_k(w)=a_k^T w",
    ]:
        assert needle in text


def test_v13_candidate_expansion_retraining_result_review_authorizes_only_promotion_decision_plan() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_retraining_result_review_promotion_decision_plan_authorized=True",
        "v13_candidate_expansion_retraining_result_review_selector_promotion_authorized=False",
        "v13_candidate_expansion_retraining_result_review_atom_promotion_authorized=False",
        "v13_candidate_expansion_retraining_result_review_deployment_authorized=False",
        "v13_candidate_expansion_retraining_result_review_safety_benefit_claim_authorized=False",
        "v13_candidate_expansion_retraining_result_review_camp_over_dp_top1_claim_authorized=False",
        "v13_candidate_expansion_retraining_result_review_training_authorized=False",
        "v13_candidate_expansion_retraining_result_review_training_execution_authorized=False",
        "v13_candidate_expansion_retraining_result_review_candidate_generation_authorized=False",
        "v13_candidate_expansion_retraining_result_review_replay_execution_authorized=False",
        "v13_candidate_expansion_retraining_result_review_dp_modification_authorized=False",
        "current_v13_status=candidate_expansion_retraining_result_review_complete",
        "current_v13_next_scope=promotion_decision_plan_only_after_explicit_user_authorization",
        "candidate_expansion_retraining_result_review_complete=True",
        "promotion_decision_plan_authorized_by_result_review=True",
        "promotion_decision_plan_only_authorized=True",
        "actual_selector_promotion_authorized=False",
        "actual_atom_promotion_authorized=False",
        "actual_deployment_authorized=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "next_work_target=dp_camp_v13_promotion_decision_plan_only_after_explicit_user_authorization",
    ]:
        assert needle in text


def test_v13_audit_records_candidate_expansion_promotion_decision_plan() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_promotion_decision_plan_status=dp_camp_v13_promotion_decision_plan_ready",
        "v13_candidate_expansion_promotion_decision_plan_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_promotion_decision_plan_8babbc0_f3eb7d1_20260628T094558CST",
        "v13_candidate_expansion_promotion_decision_plan_json_sha256=96abd24962490c473db9c6121d2230a668fbdc8a3be7a63476278964021bc4d3",
        "v13_candidate_expansion_promotion_decision_plan_md_sha256=bcf4a2aa8c31d06687019eb4b6ed07e976c56ffca35dd1e8309d17d0cddffde5",
        "v13_candidate_expansion_promotion_decision_plan_heads_sha256=2ace3cc4deb127b89d67fffbababbf18dcc5075aade71fc1c3b4af6cbda0732a",
        "v13_candidate_expansion_promotion_decision_plan_script_sha256=790bd33533ab300ced0539514002ed68a1f7b11be7102bede4f266928721bd8e",
        "v13_candidate_expansion_promotion_decision_plan_execution_camp_head=f3eb7d10614c9ab28b38388ba7c150a01ed3aa48",
        "v13_candidate_expansion_promotion_decision_plan_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_candidate_expansion_promotion_decision_plan_passed=True",
        "v13_candidate_expansion_promotion_decision_plan_failed_checks=[]",
        "v13_candidate_expansion_promotion_decision_plan_ready=True",
        "v13_candidate_expansion_promotion_decision_plan_authorized_next_work=dp_camp_v13_promotion_evidence_package_preflight_only",
        "v13_candidate_expansion_promotion_decision_plan_evidence_package_preflight_authorized=True",
        "v13_candidate_expansion_promotion_decision_plan_recommendation=do_not_promote_from_current_evidence_alone",
        "v13_candidate_expansion_promotion_decision_plan_immediate_action=build_evidence_package_preflight_only",
        "v13_candidate_expansion_promotion_decision_plan_promotion_class_under_consideration=future_default_off_shadow_or_development_reranker_candidate",
        "v13_candidate_expansion_promotion_decision_plan_source_records_total=102400",
        "v13_candidate_expansion_promotion_decision_plan_source_records_without_feasible_candidate=28468",
        "v13_candidate_expansion_promotion_decision_plan_source_records_with_feasible_candidate=73932",
        "v13_candidate_expansion_promotion_decision_plan_source_training_records=22836",
        "v13_candidate_expansion_promotion_decision_plan_source_validation_records=5632",
        "v13_candidate_expansion_promotion_decision_plan_source_num_candidates=8",
        "v13_candidate_expansion_promotion_decision_plan_source_num_atoms=14",
        "v13_candidate_expansion_promotion_decision_plan_source_atom_schema_version=dp_camp_v10_14d",
        "v13_candidate_expansion_promotion_decision_plan_source_score_expression=score_k(w)=a_k^T w",
    ]:
        assert needle in text


def test_v13_candidate_expansion_promotion_decision_plan_authorizes_only_evidence_preflight() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_promotion_decision_plan_selector_promotion_authorized=False",
        "v13_candidate_expansion_promotion_decision_plan_atom_promotion_authorized=False",
        "v13_candidate_expansion_promotion_decision_plan_deployment_authorized=False",
        "v13_candidate_expansion_promotion_decision_plan_safety_benefit_claim_authorized=False",
        "v13_candidate_expansion_promotion_decision_plan_camp_over_dp_top1_claim_authorized=False",
        "v13_candidate_expansion_promotion_decision_plan_training_authorized=False",
        "v13_candidate_expansion_promotion_decision_plan_training_execution_authorized=False",
        "v13_candidate_expansion_promotion_decision_plan_candidate_generation_authorized=False",
        "v13_candidate_expansion_promotion_decision_plan_replay_execution_authorized=False",
        "v13_candidate_expansion_promotion_decision_plan_dp_modification_authorized=False",
        "v13_candidate_expansion_promotion_decision_plan_online_selector_change_authorized=False",
        "current_v13_status=candidate_expansion_promotion_decision_plan_complete",
        "current_v13_next_scope=promotion_evidence_package_preflight_only",
        "candidate_expansion_promotion_decision_plan_complete=True",
        "promotion_evidence_package_preflight_authorized=True",
        "actual_selector_promotion_authorized=False",
        "actual_atom_promotion_authorized=False",
        "actual_deployment_authorized=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "next_work_target=dp_camp_v13_promotion_evidence_package_preflight_only",
    ]:
        assert needle in text


def test_v13_audit_records_candidate_expansion_promotion_evidence_preflight() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_promotion_evidence_package_preflight_status=dp_camp_v13_promotion_evidence_package_preflight_ready",
        "v13_candidate_expansion_promotion_evidence_package_preflight_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_promotion_evidence_package_preflight_8babbc0_ce1cd14_20260628T100315CST",
        "v13_candidate_expansion_promotion_evidence_package_preflight_json_sha256=add6e31291b5fb99c6a753c1384cb98fdfd4a8e00d8f506c70c2889b568a1ed7",
        "v13_candidate_expansion_promotion_evidence_package_preflight_md_sha256=0cf1c1b5ac4dbceefc0da1301fa0b6ceef956437418a03ac4a431e71675c2fbe",
        "v13_candidate_expansion_promotion_evidence_package_preflight_heads_sha256=9036d98e86459403221d8c0c08cec93739d78f9254002f023e3a4cece5b890cc",
        "v13_candidate_expansion_promotion_evidence_package_preflight_script_sha256=c0222d1de8ec18fb90868cacc09d7a7df5b26992971eb3eb4a232e09b1af52d7",
        "v13_candidate_expansion_promotion_evidence_package_preflight_execution_camp_head=ce1cd14e59a03aa278a5c13a7d722a923dfef7a8",
        "v13_candidate_expansion_promotion_evidence_package_preflight_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_candidate_expansion_promotion_evidence_package_preflight_passed=True",
        "v13_candidate_expansion_promotion_evidence_package_preflight_failed_checks=[]",
        "v13_candidate_expansion_promotion_evidence_package_preflight_ready=True",
        "v13_candidate_expansion_promotion_evidence_package_preflight_manifest_count=10",
        "v13_candidate_expansion_promotion_evidence_package_preflight_static_integration_contract_status=preflight_ready_contract_pinned",
        "v13_candidate_expansion_promotion_evidence_package_preflight_default_off_shadow_selector_wiring_status=future_static_contract_plan_required_before_implementation",
        "v13_candidate_expansion_promotion_evidence_package_preflight_collection_summary_sha256=4addd267d8bf14c73945610cf3b7196db874c5f6994a9725967ea0a07dfd231c",
        "v13_candidate_expansion_promotion_evidence_package_preflight_pipeline_summary_sha256=a5f9b2651413987d63eee94329af1eedcd6346d27fb97d3b3709ac68f1799e79",
        "v13_candidate_expansion_promotion_evidence_package_preflight_training_summary_sha256=b23427d33438216eccb51e79c3c901bb81df13abc1e722c9f18d2b5c8030e876",
        "v13_candidate_expansion_promotion_evidence_package_preflight_weights_json_sha256=490c8ecee1a8981e73888f63217a85b48f8fd7134bccf3f8c4519fdc227c4e30",
        "v13_candidate_expansion_promotion_evidence_package_preflight_weights_npy_sha256=b7981a9740cc3cfb6354726833997009a4f2da1914dd764a5dfb6b008b48a182",
        "v13_candidate_expansion_promotion_evidence_package_preflight_atom_scales_json_sha256=3b9abfaaa98e80a1a1b93635cd9ced1f7e8cbe910539549f4722e04b92a6c498",
        "v13_candidate_expansion_promotion_evidence_package_preflight_collection_records_total=51200",
        "v13_candidate_expansion_promotion_evidence_package_preflight_collection_records_without_feasible_candidate=14410",
        "v13_candidate_expansion_promotion_evidence_package_preflight_collection_records_with_feasible_candidate=36790",
        "v13_candidate_expansion_promotion_evidence_package_preflight_pipeline_records_total=102400",
        "v13_candidate_expansion_promotion_evidence_package_preflight_pipeline_records_built=28468",
        "v13_candidate_expansion_promotion_evidence_package_preflight_training_records=22836",
        "v13_candidate_expansion_promotion_evidence_package_preflight_validation_records=5632",
        "v13_candidate_expansion_promotion_evidence_package_preflight_score_expression=score_k(w)=a_k^T w",
        "v13_candidate_expansion_promotion_evidence_package_preflight_static_allowed_operation=argmin_k score_k(w)",
        "v13_candidate_expansion_promotion_evidence_package_preflight_simplex_master_convex=True",
        "v13_candidate_expansion_promotion_evidence_package_preflight_cvar_master_convex=True",
        "v13_candidate_expansion_promotion_evidence_package_preflight_l2_master_convex=True",
    ]:
        assert needle in text


def test_v13_candidate_expansion_promotion_evidence_preflight_authorizes_only_contract_plan() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_promotion_evidence_package_preflight_authorized_next_work=dp_camp_v13_default_off_shadow_selector_static_integration_contract_plan_only",
        "v13_candidate_expansion_promotion_evidence_package_preflight_default_off_shadow_selector_contract_plan_authorized=True",
        "v13_candidate_expansion_promotion_evidence_package_preflight_selector_promotion_authorized=False",
        "v13_candidate_expansion_promotion_evidence_package_preflight_atom_promotion_authorized=False",
        "v13_candidate_expansion_promotion_evidence_package_preflight_deployment_authorized=False",
        "v13_candidate_expansion_promotion_evidence_package_preflight_safety_benefit_claim_authorized=False",
        "v13_candidate_expansion_promotion_evidence_package_preflight_camp_over_dp_top1_claim_authorized=False",
        "v13_candidate_expansion_promotion_evidence_package_preflight_training_authorized=False",
        "v13_candidate_expansion_promotion_evidence_package_preflight_training_execution_authorized=False",
        "v13_candidate_expansion_promotion_evidence_package_preflight_candidate_generation_authorized=False",
        "v13_candidate_expansion_promotion_evidence_package_preflight_replay_execution_authorized=False",
        "v13_candidate_expansion_promotion_evidence_package_preflight_dp_modification_authorized=False",
        "v13_candidate_expansion_promotion_evidence_package_preflight_online_selector_change_authorized=False",
        "current_v13_status=candidate_expansion_promotion_evidence_package_preflight_complete",
        "current_v13_next_scope=default_off_shadow_selector_static_integration_contract_plan_only",
        "candidate_expansion_promotion_evidence_package_preflight_complete=True",
        "default_off_shadow_selector_static_contract_plan_authorized=True",
        "default_off_shadow_selector_static_contract_plan_only_authorized=True",
        "default_off_shadow_selector_implementation_authorized=False",
        "actual_selector_promotion_authorized=False",
        "actual_atom_promotion_authorized=False",
        "actual_deployment_authorized=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_static_integration_contract_plan_only",
    ]:
        assert needle in text


def test_v13_audit_records_candidate_expansion_default_off_shadow_selector_static_contract_plan() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_status=dp_camp_v13_default_off_shadow_selector_static_contract_plan_ready",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_default_off_shadow_selector_static_contract_plan_8babbc0_03830b4_20260628T100954CST",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_json_sha256=3dce55d1635e4a235717ba433f2ce69ea7d7613c7e95a584e6c85d4bb193fa0d",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_md_sha256=bf6a2407e420400bb724769d3231aadf954e8608541d8da8f17d44600c6e1379",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_heads_sha256=8e45cec13fcbb0fd9f59bf542b12d18991cdf934992c1756704ff62f0bcc48a4",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_script_sha256=8994e08fdd02e0237df38866524334cc52a4c1f6338d782305413783f90e366d",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_execution_camp_head=03830b4bce2899c8857e2ad7735ac64256187838",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_passed=True",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_failed_checks=[]",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_ready=True",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_evidence_package_preflight_sha256=add6e31291b5fb99c6a753c1384cb98fdfd4a8e00d8f506c70c2889b568a1ed7",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_camp_integration_py_sha256=6b964595bcd50cf10e5edfbdebef2a8cc6b1494990103f6f66bc76d6498fcde7",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_replay_runner_py_sha256=1d5e116cb2c7c473b9c79906a17bc01683dc9b7595a6006c129cc135dedf4813",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_benders_contract_test_py_sha256=bbed165a710f91087b963c6df235764e4ad9c553ff43eed26f4263d51545d301",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_source_preflight_status=dp_camp_v13_promotion_evidence_package_preflight_ready",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_source_manifest_count=10",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_source_static_contract_status=preflight_ready_contract_pinned",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_camp_selector_surface_present=True",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_runner_selector_mode_present=True",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_runner_finite_candidate_contract_present=True",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_benders_affine_score_test_present=True",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_benders_negative_atom_rejection_test_present=True",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_selector_phase=default_off_shadow_only",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_runtime_effect=must_log_shadow_decision_without changing DP top1 output",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_candidate_source=fixed current-tick DP candidate tensor before CAMP scoring",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_candidate_count=8",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_score_expression=score_k(w)=a_k^T w",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_selection_rule=argmin_k score_k(w) over finite candidate rows",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_default_off_required=True",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_kill_switch_required=True",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_trajectory_mutation_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_postselection_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_formal_seed_usage_authorized=False",
    ]:
        assert needle in text


def test_v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_authorizes_only_implementation_plan() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_authorized_next_work=dp_camp_v13_default_off_shadow_selector_implementation_plan_only",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_implementation_plan_authorized=True",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_implementation_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_selector_promotion_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_atom_promotion_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_deployment_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_safety_benefit_claim_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_camp_over_dp_top1_claim_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_training_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_training_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_candidate_generation_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_replay_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_dp_modification_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_static_contract_plan_online_selector_change_authorized=False",
        "current_v13_status=candidate_expansion_default_off_shadow_selector_static_contract_plan_complete",
        "current_v13_next_scope=default_off_shadow_selector_implementation_plan_only",
        "candidate_expansion_default_off_shadow_selector_static_contract_plan_complete=True",
        "default_off_shadow_selector_implementation_plan_authorized=True",
        "default_off_shadow_selector_implementation_plan_only_authorized=True",
        "default_off_shadow_selector_implementation_authorized=False",
        "actual_selector_promotion_authorized=False",
        "actual_atom_promotion_authorized=False",
        "actual_deployment_authorized=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_implementation_plan_only",
    ]:
        assert needle in text


def test_v13_audit_records_candidate_expansion_default_off_shadow_selector_implementation_plan() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_status=dp_camp_v13_default_off_shadow_selector_implementation_plan_ready",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_default_off_shadow_selector_implementation_plan_8babbc0_9e33f21_20260628T102111CST",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_json_sha256=84c08882b948faa8f195715ce52ef5fba9b751d3e3853c4177fe9e5e83d1857b",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_md_sha256=e7d5ae676dc73422f6c29620e630bd5c4a3e34a9e3c020148d5d9420ca2c316a",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_heads_sha256=61e19e12904cbdfb6e080928bd311881f0fc8fc581debe6e717ab27d0287779f",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_script_sha256=cda9a146de786c0859d4a777385f83635b99c2d09e8d0bbc0c0596bc8f367cb9",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_execution_camp_head=9e33f21e56f09644d5bf1e10b162176d2cd88c6a",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_passed=True",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_failed_checks=[]",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_ready=True",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_static_contract_plan_sha256=3dce55d1635e4a235717ba433f2ce69ea7d7613c7e95a584e6c85d4bb193fa0d",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_camp_integration_py_sha256=6b964595bcd50cf10e5edfbdebef2a8cc6b1494990103f6f66bc76d6498fcde7",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_replay_runner_py_sha256=1d5e116cb2c7c473b9c79906a17bc01683dc9b7595a6006c129cc135dedf4813",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_benders_contract_test_py_sha256=bbed165a710f91087b963c6df235764e4ad9c553ff43eed26f4263d51545d301",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_source_status=dp_camp_v13_default_off_shadow_selector_static_contract_plan_ready",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_source_authorized_next_work=dp_camp_v13_default_off_shadow_selector_implementation_plan_only",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_source_candidate_count=8",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_source_score_expression=score_k(w)=a_k^T w",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_source_selection_rule=argmin_k score_k(w) over finite candidate rows",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_status_detail=plan_ready_no_implementation",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_selector_phase=future_default_off_shadow_only",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_runtime_effect=log shadow decision while executed output remains DP top1",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_selection_rule=shadow_selected_index = argmin_k score_k(w)",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_score_expression=score_k(w)=a_k^T w",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_candidate_count=8",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_future_target_files=camp_core/camp_core/integrations/diffusion_planner.py,scripts/integrations/run_diffusion_planner_camp_replay.py,camp_core/tests/test_diffusion_planner_default_off_shadow_selector.py,camp_core/tests/test_diffusion_planner_v13_iteration_audit.py",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_static_review_requirements=default_false,no_shadow_index_routed_to_executed_trajectory,no_candidate_mutation,affine_fixed_candidate_scoring,formal_seeds_forbidden,dp_unmodified,no_claims",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_forbidden_paths=change_default_selector_mode,route_shadow_index_to_executed_trajectory,generate_or_modify_trajectories,use_future_or_label_inputs,use_formal_seeds,modify_or_retrain_dp,claim_promotion_deployment_safety_or_superiority",
    ]:
        assert needle in text


def test_v13_candidate_expansion_default_off_shadow_selector_implementation_plan_authorizes_only_static_review() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_authorized_next_work=dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review_only",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_static_contract_review_authorized=True",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_implementation_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_selector_promotion_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_atom_promotion_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_deployment_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_safety_benefit_claim_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_camp_over_dp_top1_claim_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_training_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_training_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_candidate_generation_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_replay_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_dp_modification_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_plan_online_selector_change_authorized=False",
        "current_v13_status=candidate_expansion_default_off_shadow_selector_implementation_plan_complete",
        "current_v13_next_scope=default_off_shadow_selector_implementation_static_contract_review_only",
        "candidate_expansion_default_off_shadow_selector_implementation_plan_complete=True",
        "default_off_shadow_selector_implementation_static_contract_review_authorized=True",
        "default_off_shadow_selector_implementation_static_contract_review_only_authorized=True",
        "default_off_shadow_selector_implementation_authorized=False",
        "actual_selector_promotion_authorized=False",
        "actual_atom_promotion_authorized=False",
        "actual_deployment_authorized=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review_only",
    ]:
        assert needle in text


def test_v13_audit_records_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_status=dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review_ready",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_8babbc0_82586b9_20260628T103245CST",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_json_sha256=b2281dbc101c09e6e4fb46b26d5be60e8b6519ef5958d584d4ef446cb50fd082",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_md_sha256=85ef0b22bd6c9eacfcc938332dd73dcaec1c3141678b98da24d4e3c51fbeee22",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_stdout_log_sha256=3e718ea6a056236b0eeb45ec297bcdd3da7bbf0c7dbdbc9b40e348787662a5c6",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_heads_sha256=d791e4bf9aaa369a54a79e8857d9730ef927725ef3fbee4278fe74b2c1840cc1",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_script_sha256=88e9d683e9b7b7523990c7aa28dec931ae470fb6508659e75a0746b728f8d2ce",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_execution_camp_head=82586b925b0d5a937967a806e89623950ba57885",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_passed=True",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_failed_checks=[]",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_ready=True",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_source_plan_sha256=84c08882b948faa8f195715ce52ef5fba9b751d3e3853c4177fe9e5e83d1857b",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_camp_integration_py_sha256=6b964595bcd50cf10e5edfbdebef2a8cc6b1494990103f6f66bc76d6498fcde7",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_replay_runner_py_sha256=1d5e116cb2c7c473b9c79906a17bc01683dc9b7595a6006c129cc135dedf4813",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_benders_contract_test_py_sha256=bbed165a710f91087b963c6df235764e4ad9c553ff43eed26f4263d51545d301",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_source_status=dp_camp_v13_default_off_shadow_selector_implementation_plan_ready",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_source_authorized_next_work=dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review_only",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_source_candidate_count=8",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_source_score_expression=score_k(w)=a_k^T w",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_source_selection_rule=shadow_selected_index = argmin_k score_k(w)",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_status_detail=review_ready_no_implementation",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_runtime_effect=executed output remains DP top1 during shadow phase",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_candidate_operation=fixed DP candidate reranking only",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_score_expression=score_k(w)=a_k^T w",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_contracts=default_off_flag_contract,immutable_artifact_hash_contract,fixed_candidate_tensor_contract,affine_benders_atom_score_contract,dp_top1_runtime_output_contract,fail_closed_observability_contract,no_promotion_no_claims_contract",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_unit_tests_plan_requirements=default_off_before_artifacts,shadow_selection_does_not_change_dp_top1,k_drift_hash_mismatch_nonfinite_fail_closed,no_candidate_generation_mutation_blend_guidance_postselection,affine_score_in_simplex_weights,formal_seeds_absent_or_rejected",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_forbidden_paths=actual_implementation_code_edits,route_shadow_selected_index_into_trajectory,training_replay_or_candidate_generation,dp_code_weight_config_or_invocation_modification,selector_or_atom_promotion,deployable_checkpoint_safety_or_camp_over_dp_claim",
    ]:
        assert needle in text


def test_v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_authorizes_only_unit_tests_plan() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_authorized_next_work=dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_plan_only",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_unit_tests_plan_authorized=True",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_implementation_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_selector_promotion_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_atom_promotion_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_deployment_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_safety_benefit_claim_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_camp_over_dp_top1_claim_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_training_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_training_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_candidate_generation_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_replay_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_dp_modification_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_online_selector_change_authorized=False",
        "current_v13_status=candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_complete",
        "current_v13_next_scope=default_off_shadow_selector_implementation_unit_tests_plan_only",
        "candidate_expansion_default_off_shadow_selector_implementation_static_contract_review_complete=True",
        "default_off_shadow_selector_implementation_unit_tests_plan_authorized=True",
        "default_off_shadow_selector_implementation_unit_tests_plan_only_authorized=True",
        "default_off_shadow_selector_implementation_authorized=False",
        "actual_selector_promotion_authorized=False",
        "actual_atom_promotion_authorized=False",
        "actual_deployment_authorized=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_plan_only",
    ]:
        assert needle in text


def test_v13_audit_records_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_status=dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_plan_ready",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_8babbc0_98edf5b_20260628T103950CST",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_json_sha256=c1e86a363ee901a3d76aa65053a1862b243abc45065c338a714447dd7842b0c5",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_md_sha256=ed929bec73c28396e3980940107246d438eca89b4cfe7c867fd195e60f0d05c5",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_stdout_log_sha256=06da1d5e9b0f6d4596a12eb775680e93947f14f87a9c0138f9ae9828422b6d92",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_heads_sha256=42482b6c9952145f1d0e10ae53fd83430bfaec351fae8c58870a41274342fa7d",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_script_sha256=132e2cb3d820c31e2b56f866d821d05f2892dae23968defb16a351cad7b48781",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_execution_camp_head=98edf5b90b311ac6e60fa045b59d465e4ced597f",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_passed=True",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_failed_checks=[]",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_ready=True",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_static_contract_review_sha256=b2281dbc101c09e6e4fb46b26d5be60e8b6519ef5958d584d4ef446cb50fd082",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_camp_integration_py_sha256=6b964595bcd50cf10e5edfbdebef2a8cc6b1494990103f6f66bc76d6498fcde7",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_replay_runner_py_sha256=1d5e116cb2c7c473b9c79906a17bc01683dc9b7595a6006c129cc135dedf4813",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_benders_contract_test_py_sha256=bbed165a710f91087b963c6df235764e4ad9c553ff43eed26f4263d51545d301",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_source_status=dp_camp_v13_default_off_shadow_selector_implementation_static_contract_review_ready",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_source_authorized_next_work=dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_plan_only",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_source_candidate_operation=fixed DP candidate reranking only",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_source_score_expression=score_k(w)=a_k^T w",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_source_contracts=default_off_flag_contract,immutable_artifact_hash_contract,fixed_candidate_tensor_contract,affine_benders_atom_score_contract,dp_top1_runtime_output_contract,fail_closed_observability_contract,no_promotion_no_claims_contract",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_status_detail=plan_ready_no_unit_test_code",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_target_test_file=camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_implementation_unit_tests.py",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_test_groups=default_off_disabled_contract,immutable_artifact_hash_contract,fixed_candidate_affine_score_contract,dp_top1_shadow_runtime_contract,no_candidate_mutation_contract,benders_and_seed_boundary_contract",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_acceptance_criteria=unit_tests_only_no_production_implementation,deterministic_no_formal_seeds,fail_on_shadow_to_executed_output,fail_on_candidate_generation_mutation_blend_guidance_postselection,pin_affine_score_and_k8",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_forbidden_paths=production_implementation_code_edits,selector_wiring_or_default_changes,training_replay_or_candidate_generation,dp_code_weight_config_or_invocation_modification,selector_or_atom_promotion,deployable_checkpoint_safety_or_camp_over_dp_claim",
    ]:
        assert needle in text


def test_v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_authorizes_only_unit_tests() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_authorized_next_work=dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_only",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_unit_tests_only_authorized=True",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_implementation_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_selector_promotion_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_atom_promotion_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_deployment_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_safety_benefit_claim_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_camp_over_dp_top1_claim_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_training_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_training_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_candidate_generation_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_replay_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_dp_modification_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_online_selector_change_authorized=False",
        "current_v13_status=candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_complete",
        "current_v13_next_scope=default_off_shadow_selector_implementation_unit_tests_only",
        "candidate_expansion_default_off_shadow_selector_implementation_unit_tests_plan_complete=True",
        "default_off_shadow_selector_implementation_unit_tests_only_authorized=True",
        "default_off_shadow_selector_implementation_authorized=False",
        "actual_selector_promotion_authorized=False",
        "actual_atom_promotion_authorized=False",
        "actual_deployment_authorized=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_only",
    ]:
        assert needle in text


def test_v13_audit_records_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_only() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_only_status=dp_camp_v13_default_off_shadow_selector_implementation_unit_tests_only_complete",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_only_test_file=camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_implementation_unit_tests.py",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_only_test_file_sha256=ca87f7b69b4bd51969b94583cd1fddf41efe75185bb953b508cfbf81d3c34457",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_only_local_pytest=27 passed in 2.95s",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_only_autodl_pytest=104 passed in 0.49s",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_only_execution_camp_head=438bd6764f5b7a54798cac3b011a727cc10f30fb",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_only_execution_camp_origin_main=438bd6764f5b7a54798cac3b011a727cc10f30fb",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_only_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_candidate_expansion_shadow_selector_unit_tests_status=unit_tests_complete_no_production_implementation_edits",
        "v13_candidate_expansion_shadow_selector_unit_tests_groups=default_off_disabled_contract,immutable_artifact_hash_contract,fixed_candidate_affine_score_contract,dp_top1_shadow_runtime_contract,no_candidate_mutation_contract,benders_and_seed_boundary_contract,current_static_source_surface_contract",
        "v13_candidate_expansion_shadow_selector_unit_tests_score_expression=score_k(w)=a_k^T w",
        "v13_candidate_expansion_shadow_selector_unit_tests_candidate_count=8",
        "v13_candidate_expansion_shadow_selector_unit_tests_runtime_effect=shadow selected index may be logged but executed output remains DP top1",
        "v13_candidate_expansion_shadow_selector_unit_tests_candidate_operation=fixed DP candidate reranking only",
        "v13_candidate_expansion_shadow_selector_unit_tests_candidate_mutation_allowed=False",
        "v13_candidate_expansion_shadow_selector_unit_tests_formal_seed_11_12_13_execution_allowed=False",
    ]:
        assert needle in text


def test_v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_only_reaches_authorized_implementation_boundary() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_implementation_unit_tests_only_authorized_next_work=dp_camp_v13_default_off_shadow_selector_implementation_only_after_explicit_user_authorization",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_ready_for_explicit_authorization=True",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_explicit_user_authorization_present=True",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_authorized_by_unit_tests_only=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_authorized_by_user=True",
        "v13_candidate_expansion_selector_promotion_authorized_by_unit_tests_only=False",
        "v13_candidate_expansion_atom_promotion_authorized_by_unit_tests_only=False",
        "v13_candidate_expansion_deployment_authorized_by_unit_tests_only=False",
        "v13_candidate_expansion_training_authorized_by_unit_tests_only=False",
        "v13_candidate_expansion_training_execution_authorized_by_unit_tests_only=False",
        "v13_candidate_expansion_replay_execution_authorized_by_unit_tests_only=False",
        "v13_candidate_expansion_candidate_generation_authorized_by_unit_tests_only=False",
        "v13_candidate_expansion_dp_modification_authorized_by_unit_tests_only=False",
        "v13_candidate_expansion_online_selector_change_authorized_by_unit_tests_only=False",
        "current_v13_status=candidate_expansion_default_off_shadow_selector_implementation_unit_tests_only_complete",
        "current_v13_next_scope=default_off_shadow_selector_implementation_only_after_explicit_user_authorization",
        "current_v13_default_off_shadow_selector_implementation_explicit_user_authorization_present=True",
        "candidate_expansion_default_off_shadow_selector_implementation_unit_tests_only_complete=True",
        "default_off_shadow_selector_implementation_authorized_by_unit_tests_only=False",
        "default_off_shadow_selector_implementation_authorized_by_user=True",
        "default_off_shadow_selector_implementation_authorized_by_current_boundary=True",
        "actual_selector_promotion_authorized=False",
        "actual_atom_promotion_authorized=False",
        "actual_deployment_authorized=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_implementation_only_after_explicit_user_authorization",
    ]:
        assert needle in text


def test_v13_audit_records_candidate_expansion_default_off_shadow_selector_implementation() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_implementation_status=dp_camp_v13_default_off_shadow_selector_implementation_complete",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_user_authorized=True",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_production_diff_required=False",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_runner_file=scripts/integrations/run_diffusion_planner_camp_replay.py",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_runner_file_sha256=1d5e116cb2c7c473b9c79906a17bc01683dc9b7595a6006c129cc135dedf4813",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_integration_file=camp_core/camp_core/integrations/diffusion_planner.py",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_integration_file_sha256=6b964595bcd50cf10e5edfbdebef2a8cc6b1494990103f6f66bc76d6498fcde7",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_test_file=camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_implementation_unit_tests.py",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_test_file_sha256=ca87f7b69b4bd51969b94583cd1fddf41efe75185bb953b508cfbf81d3c34457",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_local_py_compile=passed",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_local_pytest=107 passed in 0.79s",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_autodl_py_compile=passed",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_autodl_pytest=107 passed in 0.50s",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_execution_camp_head=9957b5b508e30ec0c653b500e8072958eb6caa37",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_execution_camp_origin_main=9957b5b508e30ec0c653b500e8072958eb6caa37",
        "v13_candidate_expansion_default_off_shadow_selector_implementation_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_candidate_expansion_default_off_shadow_selector_runtime_flag=--camp_default_off_shadow_selector",
        "v13_candidate_expansion_default_off_shadow_selector_runtime_default_off=True",
        "v13_candidate_expansion_default_off_shadow_selector_runtime_schema=dp_camp_v13_default_off_shadow_selector_runtime_v1",
        "v13_candidate_expansion_default_off_shadow_selector_runtime_effect=records shadow_selected_index while selected_index and executed_index remain DP candidate 0",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_contract=manifest_or_explicit_sha256_required_for_atom_scales_and_static_weights_or_checkpoint",
        "v13_candidate_expansion_default_off_shadow_selector_candidate_count=8",
        "v13_candidate_expansion_default_off_shadow_selector_score_expression=score_k(w)=a_k^T w",
        "v13_candidate_expansion_default_off_shadow_selector_candidate_operation=fixed DP candidate reranking only",
        "v13_candidate_expansion_default_off_shadow_selector_execution_effect=False",
        "v13_candidate_expansion_default_off_shadow_selector_online_selector_change=False",
        "v13_candidate_expansion_default_off_shadow_selector_candidate_mutation_allowed=False",
        "v13_candidate_expansion_default_off_shadow_selector_formal_seed_11_12_13_execution_allowed=False",
    ]:
        assert needle in text


def test_v13_candidate_expansion_default_off_shadow_selector_implementation_authorizes_only_post_static_review() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_implementation_authorized_next_work=dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract_review_only",
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_authorized=True",
        "v13_candidate_expansion_selector_promotion_authorized_by_implementation=False",
        "v13_candidate_expansion_atom_promotion_authorized_by_implementation=False",
        "v13_candidate_expansion_deployment_authorized_by_implementation=False",
        "v13_candidate_expansion_training_authorized_by_implementation=False",
        "v13_candidate_expansion_training_execution_authorized_by_implementation=False",
        "v13_candidate_expansion_replay_execution_authorized_by_implementation=False",
        "v13_candidate_expansion_candidate_generation_authorized_by_implementation=False",
        "v13_candidate_expansion_dp_modification_authorized_by_implementation=False",
        "v13_candidate_expansion_online_selector_change_authorized_by_implementation=False",
        "v13_candidate_expansion_executed_trajectory_change_authorized_by_implementation=False",
        "v13_candidate_expansion_safety_benefit_claim_authorized_by_implementation=False",
        "v13_candidate_expansion_camp_over_dp_top1_claim_authorized_by_implementation=False",
        "current_v13_status=candidate_expansion_default_off_shadow_selector_implementation_complete",
        "current_v13_next_scope=default_off_shadow_selector_post_implementation_static_contract_review_only",
        "candidate_expansion_default_off_shadow_selector_implementation_complete=True",
        "default_off_shadow_selector_post_implementation_static_contract_review_authorized=True",
        "default_off_shadow_selector_post_implementation_static_contract_review_only_authorized=True",
        "actual_selector_promotion_authorized=False",
        "actual_atom_promotion_authorized=False",
        "actual_deployment_authorized=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "executed_trajectory_change_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract_review_only",
    ]:
        assert needle in text


def test_v13_audit_records_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_status=dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract_review_complete",
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_8babbc0_bd1aa9d_20260628T105314CST",
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_json_sha256=acf5fbbb419249db77bb41f710c16267f7d382b53e5401e4007622e702e2d998",
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_md_sha256=a10c3f352d583dbb21c3cc9fe23b72ca71488a1a2546699762a36b94a8bb5bfb",
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_stdout_log_sha256=183d221d0f7115b3aa76efc979bc09b009f6bdf13ec2252f23ce7221a1a00b40",
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_heads_sha256=c8a18dc12b034e27dd3b46b8a0ac912eb5af9262e8d22e649e1dc2b2002efee8",
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_script_sha256=59fb248099e260533b8ade3c839606e3cb8c04cbbc537fc6f3c46b975cd852e7",
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_execution_camp_head=bd1aa9dfc9d0e119a6d553948909c9fe832916c9",
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_execution_camp_origin_main=bd1aa9dfc9d0e119a6d553948909c9fe832916c9",
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_passed=True",
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_failed_checks=[]",
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_schema=dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract_review_v1",
        "v13_candidate_expansion_default_off_shadow_selector_replay_runner_sha256=1d5e116cb2c7c473b9c79906a17bc01683dc9b7595a6006c129cc135dedf4813",
        "v13_candidate_expansion_default_off_shadow_selector_shadow_unit_test_sha256=ca87f7b69b4bd51969b94583cd1fddf41efe75185bb953b508cfbf81d3c34457",
        "v13_candidate_expansion_default_off_shadow_selector_benders_contract_test_sha256=bbed165a710f91087b963c6df235764e4ad9c553ff43eed26f4263d51545d301",
        "v13_candidate_expansion_default_off_shadow_selector_runtime_flag_present=True",
        "v13_candidate_expansion_default_off_shadow_selector_default_off_fail_closed_present=True",
        "v13_candidate_expansion_default_off_shadow_selector_dp_top1_override_present=True",
        "v13_candidate_expansion_default_off_shadow_selector_shadow_index_logging_present=True",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_hash_contract_present=True",
        "v13_candidate_expansion_default_off_shadow_selector_focused_tests_present=True",
    ]:
        assert needle in text


def test_v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_authorizes_only_manifest_plan() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_authorized_next_work=dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_only",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_authorized=True",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_runtime_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_replay_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_candidate_generation_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_dp_modification_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_online_selector_change_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_training_executed=False",
        "current_v13_status=candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_complete",
        "current_v13_next_scope=default_off_shadow_selector_artifact_manifest_plan_only",
        "current_v13_training_authorized_by_user=True",
        "candidate_expansion_default_off_shadow_selector_post_implementation_static_contract_review_complete=True",
        "default_off_shadow_selector_artifact_manifest_plan_authorized=True",
        "default_off_shadow_selector_artifact_manifest_plan_only_authorized=True",
        "artifact_manifest_materialization_authorized=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "actual_selector_promotion_authorized=False",
        "actual_atom_promotion_authorized=False",
        "actual_deployment_authorized=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "executed_trajectory_change_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_only",
    ]:
        assert needle in text


def test_v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_authorizes_only_static_review() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_status=dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_ready",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_8babbc0_93aa645_20260628T110931CST",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_json_sha256=5c593a51530bce6d295a39a188e469c85af8f57ccb609a18b0e973f8fc5ee3d2",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_md_sha256=865cdcde85d0ef1bf876b0cf6281ef2aefb2ad8bf977277a47255aadf0fdf6b1",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_execution_camp_head=93aa6451ea0d926d5fcd6b349396648c2cc79a05",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_passed=True",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_failed_checks=[]",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_schema=dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_v1",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_runtime_manifest_schema=dp_camp_v13_default_off_shadow_selector_runtime_v1",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_materialized_by_this_gate=False",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_authorized_next_work=dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_only",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_authorized=True",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_runtime_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_replay_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_candidate_generation_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_dp_modification_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_training_executed=False",
        "v13_candidate_expansion_default_off_shadow_selector_training_execution_authorized_by_user=True",
        "v13_candidate_expansion_default_off_shadow_selector_training_task_may_start_without_extra_user_authorization=True",
        "v13_candidate_expansion_default_off_shadow_selector_training_summary_sha256=b23427d33438216eccb51e79c3c901bb81df13abc1e722c9f18d2b5c8030e876",
        "v13_candidate_expansion_default_off_shadow_selector_atom_scales_sha256=3b9abfaaa98e80a1a1b93635cd9ced1f7e8cbe910539549f4722e04b92a6c498",
        "v13_candidate_expansion_default_off_shadow_selector_static_weights_npy_sha256=b7981a9740cc3cfb6354726833997009a4f2da1914dd764a5dfb6b008b48a182",
        "v13_candidate_expansion_default_off_shadow_selector_candidate_count=8",
        "v13_candidate_expansion_default_off_shadow_selector_atom_count=14",
        "v13_candidate_expansion_default_off_shadow_selector_score_expression=score_k(w)=a_k^T w",
        "v13_candidate_expansion_default_off_shadow_selector_candidate_operation=fixed DP candidate reranking only",
        "v13_candidate_expansion_default_off_shadow_selector_candidate_mutation_allowed=False",
        "v13_candidate_expansion_default_off_shadow_selector_trajectory_generation_by_camp_allowed=False",
        "v13_candidate_expansion_default_off_shadow_selector_trajectory_modification_by_camp_allowed=False",
        "v13_candidate_expansion_default_off_shadow_selector_safety_benefit_claim_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_camp_over_dp_top1_claim_authorized=False",
        "current_v13_status=candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_complete",
        "current_v13_next_scope=default_off_shadow_selector_artifact_manifest_static_contract_review_only",
        "current_v13_all_subsequent_training_tasks_authorized_by_user=True",
        "current_v13_training_authorized_by_user=True",
        "candidate_expansion_default_off_shadow_selector_artifact_manifest_plan_complete=True",
        "default_off_shadow_selector_artifact_manifest_static_contract_review_authorized=True",
        "default_off_shadow_selector_artifact_manifest_static_contract_review_only_authorized=True",
        "artifact_manifest_materialization_authorized=False",
        "runtime_shadow_selector_execution_authorized=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "executed_trajectory_change_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_only",
    ]:
        assert needle in text


def test_v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_authorizes_only_materialization_plan() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_status=dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_complete",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_8babbc0_fa129aa_20260628T111419CST",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_json_sha256=8079927e991b6dd9940cd502d025ca04883095c35d98f2f55f9b00c95c45ff7d",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_md_sha256=84c8646b0d6e056fa36b52774e29a04ae97c1fdd72b79a92a9aa017503884d6d",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_script_sha256=1d75a961995e7229881f860b6552341714e9912748db6010d913c57f42ca332b",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_source_plan_json_sha256=5c593a51530bce6d295a39a188e469c85af8f57ccb609a18b0e973f8fc5ee3d2",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_replay_runner_sha256=1d5e116cb2c7c473b9c79906a17bc01683dc9b7595a6006c129cc135dedf4813",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_execution_camp_head=fa129aaa82071809573d86dad8bb0b1e9a42f290",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_passed=True",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_failed_checks=[]",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_schema=dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_v1",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_authorized_next_work=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_only",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_authorized=True",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_runtime_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_replay_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_candidate_generation_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_dp_modification_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_training_executed=False",
        "v13_candidate_expansion_default_off_shadow_selector_training_authorization_changed_by_review=False",
        "v13_candidate_expansion_default_off_shadow_selector_selector_promotion_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_atom_promotion_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_deployment_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_safety_benefit_claim_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_camp_over_dp_top1_claim_authorized=False",
        "current_v13_status=candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_complete",
        "current_v13_next_scope=default_off_shadow_selector_artifact_manifest_materialization_plan_only",
        "current_v13_all_subsequent_training_tasks_authorized_by_user=True",
        "current_v13_training_authorized_by_user=True",
        "candidate_expansion_default_off_shadow_selector_artifact_manifest_static_contract_review_complete=True",
        "default_off_shadow_selector_artifact_manifest_materialization_plan_authorized=True",
        "default_off_shadow_selector_artifact_manifest_materialization_plan_only_authorized=True",
        "artifact_manifest_materialization_authorized=False",
        "runtime_shadow_selector_execution_authorized=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "executed_trajectory_change_authorized_by_current_boundary=False",
        "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_only",
    ]:
        assert needle in text


def test_v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_authorizes_only_static_review() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_status=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_ready",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_output_dir=/root/autodl-tmp/camp_dp_v13_nonformal_k8_provenance_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_8babbc0_e11edef_20260628T111824CST",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_json_sha256=b9e48c0e8273b3013ce0208c93601bad8fbf68ae125e9fd8d46f310211800f1c",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_md_sha256=668e0856d00c77978b1a119801ad542fe1f04eeecca945ec233dc31cddd456b0",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_script_sha256=6f41fe7472b3e7589f371ffa5e9461eb5d6c7113c4a4bd8c82b16cbdbd4e3e91",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_test_sha256=6c31d529397d0ab5d6878fd398753ff2291ea74334a5e12ae8cfd4efec1c7188",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_source_static_review_json_sha256=8079927e991b6dd9940cd502d025ca04883095c35d98f2f55f9b00c95c45ff7d",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_source_plan_json_sha256=5c593a51530bce6d295a39a188e469c85af8f57ccb609a18b0e973f8fc5ee3d2",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_execution_camp_head=e11edef7bd59bd34beef907fdd3755d01c2ddd64",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_runtime_manifest_exists_after_gate=False",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_passed=True",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_failed_checks=[]",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_schema=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_v1",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_authorized_next_work=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_only",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_authorized=True",
        "v13_candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_runtime_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_replay_execution_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_candidate_generation_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_dp_modification_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_training_executed=False",
        "v13_candidate_expansion_default_off_shadow_selector_training_authorization_changed_by_plan=False",
        "v13_candidate_expansion_default_off_shadow_selector_selector_promotion_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_atom_promotion_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_deployment_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_safety_benefit_claim_authorized=False",
        "v13_candidate_expansion_default_off_shadow_selector_camp_over_dp_top1_claim_authorized=False",
        "current_v13_status=candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_complete",
        "current_v13_next_scope=default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_only",
        "current_v13_all_subsequent_training_tasks_authorized_by_user=True",
        "current_v13_training_authorized_by_user=True",
        "candidate_expansion_default_off_shadow_selector_artifact_manifest_materialization_plan_complete=True",
        "default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_authorized=True",
        "default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_only_authorized=True",
        "artifact_manifest_materialization_authorized=False",
        "runtime_shadow_selector_execution_authorized=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
        "candidate_generation_by_fixed_dp_authorized_by_current_boundary=False",
        "replay_execution_authorized_by_current_boundary=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "executed_trajectory_change_authorized_by_current_boundary=False",
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
