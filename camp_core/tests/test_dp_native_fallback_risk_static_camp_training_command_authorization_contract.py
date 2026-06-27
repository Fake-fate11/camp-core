from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "train_diffusion_planner_dp_native_fallback_risk_static_camp.py"
)
DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_command_authorization_and_static_trainer_implementation.md"
)
AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def test_command_authorization_doc_records_user_scope_and_next_gate() -> None:
    text = DOC.read_text(encoding="utf-8")

    for needle in [
        "user_camp_retraining_authorization_received=True",
        "authorization_scope=fallback_risk_static_camp_training_nonpromotion",
        "training_command_authorization_gate_complete=True",
        "script=scripts/integrations/train_diffusion_planner_dp_native_fallback_risk_static_camp.py",
        "default_off_reads_inputs=False",
        "training_executed_by_this_gate=False",
        "ready_for_fixed_artifact_training_execution=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_fixed_artifact_acceptance",
    ]:
        assert needle in text


def test_current_head_command_authorization_pins_current_preflight_and_next_gate() -> None:
    text = DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_training_command_authorization_current_head_48620ac_passed",
        "current_command_authorization_gate_complete=True",
        "current_preflight_status=fallback_risk_training_sufficiency_preflight_current_head_95215ab_fixed_artifact_acceptance_passed",
        "current_preflight_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_sufficiency_preflight_acceptance_95215ab_20260625T195559Z/preflight.json",
        "current_preflight_json_sha256=b1ec5b1d5e3d895d7123dc08b86656bfd1901bd0fd0e5339b503aafa13b58252",
        "current_preflight_ready_for_future_training_authorization=True",
        "current_preflight_training_authorized=False",
        "user_camp_retraining_authorization_received=True",
        "training_execution_allowed_after_current_artifact_preflight=True",
        "ready_for_fixed_artifact_training_execution=True",
        "current_static_trainer=dp_native_fallback_risk_static_camp_training_v1",
        "fixed_dp_candidate_reranking_only=True",
        "score_k(w)=a_k^T w",
        "a_k_nonnegative_benders_compatible_atoms_only=True",
        "simplex_master_convex=True",
        "cvar_master_convex=True",
        "l2_regularized_master_convex=True",
        "training_executed_by_this_gate=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_fixed_artifact_acceptance",
    ]:
        assert needle in text


def test_record_identity_current_head_command_authorization_pins_current_preflight() -> None:
    text = DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_training_command_authorization_current_head_b8e61c2_passed",
        "current_authorization_base_head=b8e61c2f5c77da19a056f50c4f13b29c4566e506",
        "current_preflight_status=fallback_risk_training_sufficiency_preflight_current_head_e0347d8_fixed_artifact_acceptance_passed",
        "current_preflight_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_sufficiency_preflight_acceptance_e0347d8_20260626T020109Z/preflight.json",
        "current_preflight_json_sha256=8f68f312188ada4661aa6cb7dc91cbb9c5537df147ac5c3f0851ee6a5d00e8c5",
        "current_preflight_ready_for_future_training_authorization=True",
        "current_preflight_training_authorized=False",
        "current_preflight_fallback_risk_training_authorized_now=False",
        "user_camp_retraining_authorization_received=True",
        "training_execution_allowed_after_current_artifact_preflight=True",
        "ready_for_fixed_artifact_training_execution=True",
        "training_executed_by_this_gate=False",
        "score_k(w)=a_k^T w",
        "a_k_fixed_before_weight_optimization=True",
        "simplex_master_convex=True",
        "cvar_master_convex=True",
        "l2_regularized_master_convex=True",
        "reference_blend_authorized=False",
        "postprocess_postselection_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_fixed_artifact_acceptance",
    ]:
        assert needle in text


def test_current_chain_command_authorization_pins_c1293b0_preflight() -> None:
    text = DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_training_command_authorization_current_head_6ee30ec_passed",
        "current_command_authorization_gate_complete=True",
        "current_authorization_base_head=6ee30ec414434830d8ae522095258d8fbd27d566",
        "current_preflight_status=fallback_risk_training_sufficiency_preflight_current_head_c1293b0_fixed_artifact_acceptance_passed",
        "current_preflight_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_sufficiency_preflight_acceptance_c1293b0_20260626T061349Z/preflight.json",
        "current_preflight_json_sha256=72ca918aa05fd92b120ef7f8631a5d6984f1dfd649d9659e84f7f9beb7fc786c",
        "current_preflight_ready_for_future_training_authorization=True",
        "current_preflight_training_authorized=False",
        "current_preflight_fallback_risk_training_authorized_now=False",
        "user_camp_retraining_authorization_received=True",
        "training_execution_allowed_after_current_artifact_preflight=True",
        "ready_for_fixed_artifact_training_execution=True",
        "training_executed_by_this_gate=False",
        "fixed_dp_candidate_reranking_only=True",
        "score_k(w)=a_k^T w",
        "a_k_fixed_before_weight_optimization=True",
        "simplex_master_convex=True",
        "cvar_master_convex=True",
        "l2_regularized_master_convex=True",
        "reference_blend_authorized=False",
        "postprocess_postselection_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_fixed_artifact_acceptance",
    ]:
        assert needle in text


def test_current_head_command_authorization_pins_bdf9b1d_preflight() -> None:
    text = DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_training_command_authorization_current_head_317ba74_passed",
        "current_command_authorization_gate_complete=True",
        "current_authorization_base_head=317ba7418c267082dc1f72fbe0fdd9efa06c3559",
        "current_preflight_status=fallback_risk_training_sufficiency_preflight_current_head_bdf9b1d_fixed_artifact_acceptance_passed",
        "current_preflight_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_sufficiency_preflight_acceptance_bdf9b1d_20260626T133105Z/preflight.json",
        "current_preflight_json_sha256=c816b04fc3171514cdef8ad3643ba138c86b5361b3e5c2ce577de9d2dd3f0809",
        "current_preflight_ready_for_future_training_authorization=True",
        "current_preflight_training_authorized=False",
        "current_preflight_fallback_risk_training_authorized_now=False",
        "user_camp_retraining_authorization_received=True",
        "training_execution_allowed_after_current_artifact_preflight=True",
        "ready_for_fixed_artifact_training_execution=True",
        "current_static_trainer=dp_native_fallback_risk_static_camp_training_v1",
        "training_executed_by_this_gate=False",
        "fixed_dp_candidate_reranking_only=True",
        "score_k(w)=a_k^T w",
        "a_k_fixed_before_weight_optimization=True",
        "a_k_nonnegative_benders_compatible_atoms_only=True",
        "simplex_master_convex=True",
        "cvar_master_convex=True",
        "l2_regularized_master_convex=True",
        "reference_blend_authorized=False",
        "postprocess_postselection_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_fixed_artifact_acceptance",
    ]:
        assert needle in text


def test_current_head_command_authorization_pins_db5b070_preflight() -> None:
    text = DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_training_command_authorization_current_head_2f9479e_passed",
        "current_command_authorization_gate_complete=True",
        "current_authorization_base_head=2f9479e687d968239199007bb265ab18bdffa7be",
        "current_preflight_status=fallback_risk_training_sufficiency_preflight_current_head_db5b070_fixed_artifact_acceptance_passed",
        "current_preflight_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_sufficiency_preflight_acceptance_db5b070_20260627T034500Z/preflight.json",
        "current_preflight_json_sha256=0c42ca3bf526e12190cc409bda5ab9ab829b17228624346bc15b291b7d22aabc",
        "current_preflight_ready_for_future_training_authorization=True",
        "current_preflight_training_authorized=False",
        "current_preflight_fallback_risk_training_authorized_now=False",
        "user_camp_retraining_authorization_received=True",
        "authorization_scope=fallback_risk_static_camp_training_nonpromotion",
        "training_execution_allowed_after_current_artifact_preflight=True",
        "ready_for_fixed_artifact_training_execution=True",
        "current_static_trainer=dp_native_fallback_risk_static_camp_training_v1",
        "training_executed_by_this_gate=False",
        "fixed_dp_candidate_reranking_only=True",
        "score_k(w)=a_k^T w",
        "a_k_fixed_before_weight_optimization=True",
        "a_k_nonnegative_benders_compatible_atoms_only=True",
        "simplex_master_convex=True",
        "cvar_master_convex=True",
        "l2_regularized_master_convex=True",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "local_command_authorization_contract_pytest=9 passed",
        "autodl_command_authorization_contract_pytest=9 passed",
        "autodl_dp_head_verified=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_fixed_artifact_acceptance",
    ]:
        assert needle in text


def test_current_head_command_authorization_pins_bf3c1ef_preflight() -> None:
    text = DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_training_command_authorization_current_head_f6a8a846_passed",
        "current_command_authorization_gate_complete=True",
        "current_authorization_base_head=f6a8a8462109122a614a631cbbbf38f09dec0603",
        "current_preflight_status=fallback_risk_training_sufficiency_preflight_current_head_bf3c1ef_fixed_artifact_acceptance_passed",
        "current_preflight_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_sufficiency_preflight_acceptance_bf3c1ef_20260627T110000CST/preflight.json",
        "current_preflight_json_sha256=94d0201a8a2a73a19fa2745ac85df4c910a417f2f9751f5c01e0507b061c799d",
        "current_preflight_ready_for_future_training_authorization=True",
        "current_preflight_training_authorized=False",
        "current_preflight_fallback_risk_training_authorized_now=False",
        "user_camp_retraining_authorization_received=True",
        "authorization_scope=fallback_risk_static_camp_training_nonpromotion",
        "training_execution_allowed_after_current_artifact_preflight=True",
        "ready_for_fixed_artifact_training_execution=True",
        "current_static_trainer=dp_native_fallback_risk_static_camp_training_v1",
        "training_executed_by_this_gate=False",
        "fixed_dp_candidate_reranking_only=True",
        "score_k(w)=a_k^T w",
        "a_k_fixed_before_weight_optimization=True",
        "a_k_nonnegative_benders_compatible_atoms_only=True",
        "simplex_master_convex=True",
        "cvar_master_convex=True",
        "l2_regularized_master_convex=True",
        "reference_blend_authorized=False",
        "guidance_authorized=False",
        "postprocess_postselection_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "local_command_authorization_contract_pytest=10 passed",
        "autodl_temp_worktree=/root/autodl-tmp/camp_core_command_authorization_f6a8a846_final_verify_20260627T125500CST",
        "autodl_command_authorization_contract_pytest=10 passed",
        "autodl_dp_head_verified=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_fixed_artifact_acceptance",
    ]:
        assert needle in text


def test_iteration_audit_records_current_head_command_authorization_history() -> None:
    audit = AUDIT.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_training_command_authorization_current_head_f6a8a846_tail_authority",
        "current_command_authorization_gate_complete=True",
        "current_authorization_base_head=f6a8a8462109122a614a631cbbbf38f09dec0603",
        "current_preflight_status=fallback_risk_training_sufficiency_preflight_current_head_bf3c1ef_fixed_artifact_acceptance_passed",
        "current_preflight_json_sha256=94d0201a8a2a73a19fa2745ac85df4c910a417f2f9751f5c01e0507b061c799d",
        "training_execution_allowed_after_current_artifact_preflight=True",
        "training_executed_by_this_gate=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "local_command_authorization_contract_pytest=10 passed",
        "autodl_temp_worktree=/root/autodl-tmp/camp_core_command_authorization_f6a8a846_final_verify_20260627T125500CST",
        "autodl_command_authorization_contract_pytest=10 passed",
        "autodl_dp_head_verified=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "this_command_authorization_gate_executes_training_replay_dp_or_claims=False",
    ]:
        assert needle in audit


def test_static_trainer_preserves_benders_compatible_reranking_contract() -> None:
    text = DOC.read_text(encoding="utf-8")
    source = SCRIPT.read_text(encoding="utf-8")

    for needle in [
        "score_k(w)=a_k^T w",
        "a_k_nonnegative_benders_compatible_atoms_only=True",
        "weights_simplex_nonnegative=True",
        "q_i(w)=max(0,max_k m_ik+(a_i,o_i-a_i,k)^T w)",
        "simplex_master_convex=True",
        "cvar_master_convex=True",
        "l2_regularized_master_convex=True",
    ]:
        assert needle in text

    for needle in [
        "project_simplex_rows",
        "empirical_cvar",
        "DRY_RUN_FORBIDDEN_FLAGS",
        "score_k(w)=a_k^T w",
        "fixed_dp_candidate_reranking_only",
    ]:
        assert needle in source


def test_static_trainer_does_not_call_dp_or_promotion_paths() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    forbidden_needles = [
        "subprocess",
        "os.system",
        "camp_core.integrations.diffusion_planner",
        "Diffusion-Planner",
        "run_diffusion_planner",
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "deployable_checkpoint_claim_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "all_infeasible_records_added_to_feasible_training=True",
        "hard_feasibility_relaxation_authorized=True",
    ]

    for needle in forbidden_needles:
        assert needle not in source
