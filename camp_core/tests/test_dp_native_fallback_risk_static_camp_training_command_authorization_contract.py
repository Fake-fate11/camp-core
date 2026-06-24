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
