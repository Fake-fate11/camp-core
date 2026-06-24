from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_fixed_artifact_acceptance.md"
)


def test_fallback_risk_static_camp_training_completed_with_fixed_artifacts() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "training_commit=0e3b7f3397adecdac559027856efcdb918269496",
        "autodl_CAMP_HEAD=0e3b7f3397adecdac559027856efcdb918269496",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "training_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_acceptance_0e3b7f3_20260624T180109Z",
        "status=dp_native_fallback_risk_static_camp_training_complete",
        "training_exit=0",
        "training_authorized=True",
        "training_execution_authorized=True",
        "training_executed=True",
        "camp_retraining_started=True",
        "camp_retraining_completed=True",
        "training_records=13",
        "validation_records=2",
        "num_candidates=4",
        "num_atoms=14",
        "atom_schema_version=dp_camp_v10_14d",
        "weights_sum=1.0",
        "weights_min=0.0",
        "weights_max=1.0",
    ]:
        assert needle in text


def test_fallback_risk_static_camp_training_is_fixed_candidate_reranking_only() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "score_k(w)=a_k^T w",
        "fixed_dp_candidate_reranking_only=True",
        "fallback_only_training=True",
        "trajectory_generation_executed=False",
        "trajectory_rewrite_executed=False",
        "postprocess_postselection_executed=False",
        "formal_seeds_11_12_13_used=False",
        "remote_weights_simplex_nonnegative=True",
        "remote_dp_head_unchanged=True",
    ]:
        assert needle in text


def test_fallback_risk_static_camp_training_does_not_authorize_promotion_or_claims() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "deployment_authorized=False",
        "training_artifacts_nonpromotion=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_post_training_nonpromotion_artifact_audit",
    ]:
        assert needle in text

    forbidden_true = [
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "deployable_checkpoint_claim_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "deployment_authorized=True",
    ]
    for needle in forbidden_true:
        assert needle not in text
