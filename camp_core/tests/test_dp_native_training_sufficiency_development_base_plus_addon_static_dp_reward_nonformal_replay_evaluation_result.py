from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_nonformal_replay_evaluation_result.md"
)


def test_static_dp_reward_nonformal_replay_evaluation_smoke_passed() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=base_plus_addon_static_dp_reward_nonformal_replay_evaluation_smoke_passed_nonpromotion",
        "passed=True",
        "all_replay_exits_zero=True",
        'replay_exit_counts={"0": 2}',
        "run_count=2",
        "total_selection_records=6",
        "total_provenance_records=6",
        "total_prepost_equal_records=6",
        "total_records_with_feasible_candidate=3",
        "schema_version=dp_native_static_dp_reward_nonformal_eval_smoke_result_v1",
        "static_dp_reward_weights_loaded=True",
        "static_dp_reward_atom_scales_loaded=True",
        "candidate_tensor_provenance_logging_verified=True",
        "candidate_tensor_prepost_hash_equal_all_records=True",
    ]:
        assert needle in text


def test_static_dp_reward_nonformal_replay_boundaries_are_not_promoted() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "nonformal_replay_evaluation_smoke_only=True",
        "full36_executed=False",
        "formal_seeds_executed=False",
        "dp_modified=False",
        "reference_blend_enabled=False",
        "guidance_enabled=False",
        "postprocess_postselection_enabled=False",
        "closed_loop_outcome_online_input_used=False",
        "selector_promotion_executed=False",
        "atom_promotion_executed=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "new_candidate_generator_executed=False",
        "camp_retraining_for_deployment_authorized=False",
        "camp_retraining_for_deployment_executed=False",
        "online_selector_promotion_authorized=False",
    ]:
        assert needle in text

    for forbidden in [
        "full36_executed=True",
        "formal_seeds_executed=True",
        "dp_modified=True",
        "reference_blend_enabled=True",
        "guidance_enabled=True",
        "postprocess_postselection_enabled=True",
        "closed_loop_outcome_online_input_used=True",
        "selector_promotion_executed=True",
        "atom_promotion_executed=True",
        "deployable_checkpoint_claim_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in text


def test_static_dp_reward_nonformal_replay_records_remote_evidence() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "evaluation_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_nonformal_eval_2f9656f_20260624T090404Z",
        "offline_weights_dp_static.npy",
        "atom_scales_dp_static.json",
        "autodl_CAMP_HEAD=2f9656f188d027643573511fb4f8853857af122d",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "sample_normal_candidate_feasible_rate=1.0",
        "sample_tl_candidate_feasible_rate=0.0",
        "sample_tl_zero_feasible_candidate_records_observed=True",
        "nonformal_eval_summary.json` | `3e37c620ae9c545be15f2e62c13c8f1c43687990d5e9a4e84770956b6a8d647f",
        "sample_normal_seed109_tl_off_static/camp_selection_log.json` | `1fb2cce83d2a9bb08366d16e0d0d9cc8daae81b49169c26f0eeaebe940ab0ab4",
        "sample_tl_seed109_tl_on_static/camp_selection_log.json` | `3f6cf3a1d2b02ed0bc4e9a1d9f0bf3971826f837e0c13d229b35e2d34b31b978",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_user_authorization_pending",
    ]:
        assert needle in text
