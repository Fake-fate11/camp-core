from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_training_result.md"
)


def test_base_plus_addon_static_dp_reward_training_smoke_passed() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=base_plus_addon_static_dp_reward_training_smoke_passed_nonpromotion",
        "training_exit=0",
        "artifact_static_audit_passed=True",
        "artifact_static_audit_errors=[]",
        "training_type=diffusion_planner_static_candidate_preference",
        "mode=static",
        "training_scope=feasible_ranking",
        "label_source=dp_reward",
        "reward_key=quality_without_progress",
        "reward_progress_weight=2.0",
        "selection_log_count=40",
        "training_num_records=140",
        "dropped_records_without_feasible_candidate=60",
        "num_candidates=4",
        "num_atoms=14",
        "atom_schema_version=dp_camp_v10_14d",
        "dp_native_training_data_contract_passed=True",
        "dp_native_training_data_contract_records=200",
        "weights_sum=1.0",
        "oracle_match_rate=0.3142857142857143",
    ]:
        assert needle in text


def test_base_plus_addon_static_dp_reward_training_boundaries_are_not_promoted() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "closed_loop_outcome_label_source_used=False",
        "safety_cost_v1_label_source_used=False",
        "replay_executed=False",
        "candidate_generation_executed=False",
        "full36_executed=False",
        "formal_seeds_executed=False",
        "dp_modified=False",
        "selector_promotion_executed=False",
        "atom_promotion_executed=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "camp_retraining_for_deployment_authorized=False",
        "camp_retraining_for_deployment_executed=False",
        "online_selector_promotion_authorized=False",
    ]:
        assert needle in text

    assert "deployable_checkpoint_claim_authorized=True" not in text
    assert "safety_benefit_claim_authorized=True" not in text
    assert "camp_over_dp_top1_claim_authorized=True" not in text
    assert "selector_promotion_executed=True" not in text
    assert "dp_modified=True" not in text


def test_base_plus_addon_static_dp_reward_training_records_remote_evidence() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "training_smoke_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_training_e15feaa_20260624T084652Z",
        "autodl_CAMP_HEAD=e15feaa8f45f9dac5b2c012eccb6997ffbe8df0d",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        'combined_counts_by_route={"nishishinjuku_lane_change": 40, "sample_normal": 80, "sample_tl": 80}',
        'combined_usable_by_route={"sample_normal": 80, "sample_tl": 60}',
        "training_smoke_summary.json` | `632b4012db653f9c71cfdcd8731e14fe75cc06c91de75d41af03636f772f1cb8",
        "training/training_summary.json` | `9f1b7031d97d769f8e9e75d31ed9883c089eb28781d9f65d7e6d5f195fd2d92f",
        "training/offline_weights_dp_static.npy` | `01d80d8ccdfd68b23f86b2ed376a2f2dbd5c8ae986b5cebe8f8a59b0c2bdb5c5",
        "training/atom_scales_dp_static.json` | `7c0327ea6f1f534ca4f4d69d423ecc68def14d5498748f803e644818d4e17e7c",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_nonformal_replay_evaluation_user_authorization_pending",
    ]:
        assert needle in text
