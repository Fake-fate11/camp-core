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


def test_current_head_adab729_training_acceptance_is_pinned() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_static_camp_training_current_head_adab729_fixed_artifact_acceptance_passed",
        "training_commit=adab72980bfad5fa13172d183feda672d766eba9",
        "autodl_CAMP_HEAD=adab72980bfad5fa13172d183feda672d766eba9",
        "autodl_CAMP_origin_main=adab72980bfad5fa13172d183feda672d766eba9",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "dataset_json_sha256=682d432f742d4ab68a262cf70955981bc1562cf1dbcf2ec094984a12fcd11498",
        "training_split_manifest_json_sha256=e0a4ec0623f5db0b868465249ce9615b06b86f6c91067702af3bee9fd700db1d",
        "train_only_scale_manifest_json_sha256=92059b9c60e66c96db836821cb0060072402089b915e0bbd87240fc24c602567",
        "fallback_master_config_json_sha256=c513fd6da7768a7444cdecea25797649c131efaa5b548335b10e07c24758c95b",
        "training_command_plan_json_sha256=8051af1f8932c60b90a7f60686e7d127429e36b7a5acf67f2840d7044b805fd0",
        "preflight_json_sha256=b1ec5b1d5e3d895d7123dc08b86656bfd1901bd0fd0e5339b503aafa13b58252",
        "training_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_acceptance_adab729_20260625T200231Z",
        "training_summary_json_sha256=5b362f29f3737a1015ea977401c5fdafe2cff8e87426555d1ab7140c3ecc8761",
        "training_summary_md_sha256=18c8352bca1e0a590370a2ef3a6cdc7c52ef90d31941fe3e37c91b8a84cfc76a",
        "training_stdout_log_sha256=8ecea2e780da35cbf920cc4ca7a0686ded429585ae564c8772312100e1a2a860",
        "training_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "offline_weights_json_sha256=75e879d5f9345e49d2ccf4b477ba26863016fe6bcf6adb05c9c48a7cdd772b03",
        "atom_scales_json_sha256=69f3618f21687e08793bf766a57747fa121321be9de3e5a71f5a75b5407cfa88",
        "training_exit=0",
        "status=dp_native_fallback_risk_static_camp_training_complete",
        "training_authorized=True",
        "training_execution_authorized=True",
        "training_executed=True",
        "camp_retraining_completed=True",
        "fixed_dp_candidate_reranking_only=True",
        "fallback_only_training=True",
        "training_records=13",
        "validation_records=2",
        "num_candidates=4",
        "num_atoms=14",
        "weights_sum=1.0",
        "weights_min=0.0",
        "weights_max=1.0",
        "train_oracle_match_rate=0.3076923076923077",
        "validation_oracle_match_rate=0.5",
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
