from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_fixed_artifact_acceptance.md"
)
AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


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


def test_record_identity_current_head_5c913ae_training_acceptance_is_pinned() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_static_camp_training_current_head_5c913ae_fixed_artifact_acceptance_passed",
        "training_commit=5c913aea29d821dbfb8bf47313309e9a7dafd305",
        "autodl_CAMP_HEAD=5c913aea29d821dbfb8bf47313309e9a7dafd305",
        "autodl_CAMP_origin_main=5c913aea29d821dbfb8bf47313309e9a7dafd305",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "dataset_json_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "train_only_scale_manifest_json_sha256=8ec568461fb0887143b28899388544091aa613500673a2ffe7b1891316e62759",
        "fallback_master_config_json_sha256=ea9d8ddf4bbf6a4fdebca9685c6cc1b625c3803837114301bb3537982a030364",
        "training_command_plan_json_sha256=8a04ecb86b195bb472acbaf684ef6d0c942055345b3e1f5738326403a5b1e12d",
        "preflight_json_sha256=8f68f312188ada4661aa6cb7dc91cbb9c5537df147ac5c3f0851ee6a5d00e8c5",
        "training_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_acceptance_5c913ae_20260626T000000Z",
        "training_summary_json_sha256=a82d2403276e2aaf3e151271426bfca91e113b4e79735a8ead7a359ee8f24fb4",
        "training_summary_md_sha256=18c8352bca1e0a590370a2ef3a6cdc7c52ef90d31941fe3e37c91b8a84cfc76a",
        "training_stdout_log_sha256=8ecea2e780da35cbf920cc4ca7a0686ded429585ae564c8772312100e1a2a860",
        "training_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "offline_weights_json_sha256=08fe4290defde501f03e99dc752c95432778b9fb973262255e9cf98ec097d0a3",
        "atom_scales_json_sha256=10360c02c3deb38a6504781497b4fb5f082e59e63d3aee961f691f4e853a1b21",
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
        "deployment_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "dp_modification_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text


def test_current_head_ca07b6a_training_acceptance_is_pinned() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_static_camp_training_current_head_ca07b6a_fixed_artifact_acceptance_passed",
        "training_commit=ca07b6acd82ebb1c195d15b95584fc3ce613d758",
        "autodl_CAMP_HEAD=ca07b6acd82ebb1c195d15b95584fc3ce613d758",
        "autodl_CAMP_origin_main=ca07b6acd82ebb1c195d15b95584fc3ce613d758",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "dataset_json_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "train_only_scale_manifest_json_sha256=013db2348319ad5a959c33bc2a078b8b7162969bbd3f5633ca34d1b7ce2ef04b",
        "fallback_master_config_json_sha256=10ebf96545e244b4e3fcf657c0897a5f6f3eb72357ea9259b53de19dd2f6dc3a",
        "training_command_plan_json_sha256=6bb97f7346d11039cd3f218ec06e110f92a69bcbddddac036a5301123230116c",
        "preflight_json_sha256=72ca918aa05fd92b120ef7f8631a5d6984f1dfd649d9659e84f7f9beb7fc786c",
        "training_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_acceptance_ca07b6a_20260626T062914Z",
        "training_summary_json_sha256=22aec7885c32fc8b514184fd0eb25f1d177be1f41419a62178607f4a26e5ca11",
        "training_summary_md_sha256=18c8352bca1e0a590370a2ef3a6cdc7c52ef90d31941fe3e37c91b8a84cfc76a",
        "training_stdout_log_sha256=8ecea2e780da35cbf920cc4ca7a0686ded429585ae564c8772312100e1a2a860",
        "training_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "offline_weights_json_sha256=d05f35bb83ed160f98f498a6d7d80483d2da3f396af8a73cbdbaab31db7e5b5e",
        "atom_scales_json_sha256=a1dd6249c59290a7b345d377512fa074a1a4c019d45d30a40637bdbfb8b141d5",
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
        "deployment_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "dp_modification_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text


def test_current_head_34bdb4b_training_acceptance_is_pinned() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_static_camp_training_current_head_34bdb4b_fixed_artifact_acceptance_passed",
        "training_commit=34bdb4b3ac115700568f989c74a54706a0250e09",
        "autodl_CAMP_HEAD=34bdb4b3ac115700568f989c74a54706a0250e09",
        "autodl_CAMP_origin_main=34bdb4b3ac115700568f989c74a54706a0250e09",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "dataset_json_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "train_only_scale_manifest_json_sha256=b11cba57efc5761417c539cfbf009866fc8c5f1466a1f041073ea88f6a3b618d",
        "fallback_master_config_json_sha256=fdef70d470721fdf9dabb2c44f3ae2656da177aa2345fbaf6b225b00e7576200",
        "training_command_plan_json_sha256=7fc2904a4d49a853c8c29833ab2d4724342df74ad53cc561322455d09dd40b18",
        "preflight_json_sha256=c816b04fc3171514cdef8ad3643ba138c86b5361b3e5c2ce577de9d2dd3f0809",
        "training_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_acceptance_34bdb4b_20260626T134118Z",
        "training_summary_json_sha256=c37307b62210204bbd2a26730f9b4c2f209deb1c3d921eabb7214bb168f5c5ce",
        "training_summary_md_sha256=18c8352bca1e0a590370a2ef3a6cdc7c52ef90d31941fe3e37c91b8a84cfc76a",
        "training_stdout_log_sha256=8ecea2e780da35cbf920cc4ca7a0686ded429585ae564c8772312100e1a2a860",
        "training_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "offline_weights_json_sha256=d5be3af9de82f2032145915e0ce2947248850dc3643a9b0a526a625232bce3fb",
        "atom_scales_json_sha256=ff6a513c25d5dd4ac10672c54751023b2ca400b3fd202fcb42bc95d4e24ee7c2",
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
        "remote_weights_simplex_nonnegative=True",
        "remote_dp_head_unchanged=True",
        "deployment_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "dp_modification_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text


def test_current_head_6ca391d_training_acceptance_is_pinned() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_static_camp_training_current_head_6ca391d_fixed_artifact_acceptance_passed",
        "training_commit=6ca391d1b6f09e6f0a557c8824809032dd50311d",
        "autodl_CAMP_HEAD=6ca391d1b6f09e6f0a557c8824809032dd50311d",
        "autodl_CAMP_origin_main=6ca391d1b6f09e6f0a557c8824809032dd50311d",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "dataset_json_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "train_only_scale_manifest_json_sha256=6d4f691a6eeae0324406af959ddcff996b36441eb4d839b41143ef48bbc802f5",
        "fallback_master_config_json_sha256=e8e6425ee7fd5371af597fc97cacc16593817cc19c35c1f64bc5c684c7cb37fb",
        "training_command_plan_json_sha256=65bae87cde199c9c3b0a2d94104849bb47f3a753215642110ea9d4efe40f1384",
        "preflight_json_sha256=0c42ca3bf526e12190cc409bda5ab9ab829b17228624346bc15b291b7d22aabc",
        "training_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_acceptance_6ca391d_20260627T042000Z",
        "training_summary_json_sha256=b7ea56145b3a4a8d50f8e5e12bc2f23c6c2c963f14d1907aa4be31a18dd7b4e3",
        "training_summary_md_sha256=18c8352bca1e0a590370a2ef3a6cdc7c52ef90d31941fe3e37c91b8a84cfc76a",
        "training_stdout_log_sha256=8ecea2e780da35cbf920cc4ca7a0686ded429585ae564c8772312100e1a2a860",
        "training_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "offline_weights_json_sha256=c53d59509c8d338ad3993b9d8a079d9420ab48df05548d3be75fd29235fa0634",
        "atom_scales_json_sha256=85fe39a375f59117459d3d4104d589c6dacb12c70add01b878142be23d327aa5",
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
        "trained_weight_progress_shortfall=1.0",
        "train_oracle_match_rate=0.3076923076923077",
        "validation_oracle_match_rate=0.5",
        "remote_weights_simplex_nonnegative=True",
        "remote_dp_head_unchanged=True",
        "deployment_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "dp_modification_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text


def test_current_head_75dbff5_training_acceptance_is_pinned() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_static_camp_training_current_head_75dbff5_fixed_artifact_acceptance_passed",
        "training_commit=75dbff5316fd76b7fd842865249edbd7472fc0f5",
        "autodl_CAMP_HEAD=75dbff5316fd76b7fd842865249edbd7472fc0f5",
        "autodl_CAMP_origin_main=75dbff5316fd76b7fd842865249edbd7472fc0f5",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "dataset_json_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json_sha256=beac0fa7d2c425fd5d2cc0b45c6cd8c446c56e1b3bc3c3210b464376589bee89",
        "train_only_scale_manifest_json_sha256=168b07220db17aa1c800da8c63911388962cbef2d5f2a91d9f93186971ea6890",
        "fallback_master_config_json_sha256=a967851582b5b038700486520b48dc22d3c0ccbc3b44aca34f11ce2eb4781183",
        "training_command_plan_json_sha256=5c179f4628ce7875419edfbfede90bd455a015d147558bdfd47f554533e8277b",
        "preflight_json_sha256=94d0201a8a2a73a19fa2745ac85df4c910a417f2f9751f5c01e0507b061c799d",
        "training_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_acceptance_75dbff5_20260627T130500CST",
        "training_summary_json_sha256=55d046173592f25e0935b8afbec1c41b81dca589c962eda6e6f8f8119abf9100",
        "training_summary_md_sha256=18c8352bca1e0a590370a2ef3a6cdc7c52ef90d31941fe3e37c91b8a84cfc76a",
        "training_stdout_log_sha256=8ecea2e780da35cbf920cc4ca7a0686ded429585ae564c8772312100e1a2a860",
        "training_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "offline_weights_json_sha256=6718721393726de47ff7137c6287821bade63dea5e66b9ae0fdff725bbb90896",
        "atom_scales_json_sha256=a3815169bb734d1039df3527faa9961007a948d30ff757398d9c8b1bc1cef631",
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
        "atom_schema_version=dp_camp_v10_14d",
        "weights_sum=1.0",
        "weights_min=0.0",
        "weights_max=1.0",
        "trained_weight_progress_shortfall=1.0",
        "train_oracle_match_rate=0.3076923076923077",
        "validation_oracle_match_rate=0.5",
        "remote_summary_readback_passed=True",
        "remote_weights_simplex_nonnegative=True",
        "remote_dp_head_unchanged=True",
        "local_related_target_pytest=24 passed",
        "autodl_temp_worktree=/root/autodl-tmp/camp_core_static_training_acceptance_75dbff5_verify_20260627T133500CST",
        "autodl_related_target_pytest=24 passed",
        "autodl_dp_head_verified=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "training_artifacts_nonpromotion=True",
        "deployment_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "dp_modification_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_post_training_nonpromotion_artifact_audit",
    ]:
        assert needle in text


def test_iteration_audit_records_current_training_acceptance_history() -> None:
    audit = AUDIT.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_static_camp_training_current_head_75dbff5_tail_authority",
        "training_commit=75dbff5316fd76b7fd842865249edbd7472fc0f5",
        "training_summary_json_sha256=55d046173592f25e0935b8afbec1c41b81dca589c962eda6e6f8f8119abf9100",
        "offline_weights_json_sha256=6718721393726de47ff7137c6287821bade63dea5e66b9ae0fdff725bbb90896",
        "atom_scales_json_sha256=a3815169bb734d1039df3527faa9961007a948d30ff757398d9c8b1bc1cef631",
        "trained_weight_progress_shortfall=1.0",
        "remote_training_exit=0",
        "remote_summary_readback_passed=True",
        "remote_weights_simplex_nonnegative=True",
        "local_related_target_pytest=24 passed",
        "autodl_temp_worktree=/root/autodl-tmp/camp_core_static_training_acceptance_75dbff5_verify_20260627T133500CST",
        "autodl_related_target_pytest=24 passed",
        "autodl_dp_head_verified=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in audit


def test_current_head_0867cc8_manual_training_rerun_is_pinned() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")
    audit = AUDIT.read_text(encoding="utf-8")

    needles = [
        "status=fallback_risk_static_camp_training_current_head_0867cc8_manual_authorized_acceptance_passed",
        "manual_user_authorized_current_head_rerun=True",
        "training_commit=0867cc8b468320b7aaef94ce12e6272ca1d362c4",
        "autodl_CAMP_HEAD=0867cc8b468320b7aaef94ce12e6272ca1d362c4",
        "autodl_CAMP_origin_main=0867cc8b468320b7aaef94ce12e6272ca1d362c4",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "dataset_json_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json_sha256=beac0fa7d2c425fd5d2cc0b45c6cd8c446c56e1b3bc3c3210b464376589bee89",
        "train_only_scale_manifest_json_sha256=168b07220db17aa1c800da8c63911388962cbef2d5f2a91d9f93186971ea6890",
        "fallback_master_config_json_sha256=a967851582b5b038700486520b48dc22d3c0ccbc3b44aca34f11ce2eb4781183",
        "training_command_plan_json_sha256=5c179f4628ce7875419edfbfede90bd455a015d147558bdfd47f554533e8277b",
        "preflight_json_sha256=94d0201a8a2a73a19fa2745ac85df4c910a417f2f9751f5c01e0507b061c799d",
        "training_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_manual_authorized_0867cc8b_20260627T092951CST",
        "training_summary_json_sha256=ebcae6f710fe8f46387de7c383ca934ac28a22d48b2accc6ccb066f392c47246",
        "training_summary_md_sha256=18c8352bca1e0a590370a2ef3a6cdc7c52ef90d31941fe3e37c91b8a84cfc76a",
        "training_stdout_log_sha256=8ecea2e780da35cbf920cc4ca7a0686ded429585ae564c8772312100e1a2a860",
        "training_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "offline_weights_json_sha256=6718721393726de47ff7137c6287821bade63dea5e66b9ae0fdff725bbb90896",
        "atom_scales_json_sha256=a3815169bb734d1039df3527faa9961007a948d30ff757398d9c8b1bc1cef631",
        "training_exit=0",
        "status=dp_native_fallback_risk_static_camp_training_complete",
        "training_authorized=True",
        "training_execution_authorized=True",
        "training_executed=True",
        "camp_retraining_authorized_now=True",
        "fallback_risk_training_authorized_now=True",
        "camp_retraining_started=True",
        "camp_retraining_completed=True",
        "fixed_dp_candidate_reranking_only=True",
        "fallback_only_training=True",
        "training_records=13",
        "validation_records=2",
        "num_candidates=4",
        "num_atoms=14",
        "atom_schema_version=dp_camp_v10_14d",
        "score_k(w)=a_k^T w",
        "simplex_master_convex=True",
        "cvar_master_convex=True",
        "l2_regularized_master_convex=True",
        "weights_sum=1.0",
        "weights_min=0.0",
        "weights_max=1.0",
        "trained_weight_progress_shortfall=1.0",
        "train_oracle_match_rate=0.3076923076923077",
        "validation_oracle_match_rate=0.5",
        "training_seed=23",
        "training_seed_is_formal_seed=False",
        "remote_training_exit=0",
        "remote_summary_readback_passed=True",
        "remote_weights_simplex_nonnegative=True",
        "remote_dp_head_unchanged=True",
        "candidate_generation_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "training_artifacts_nonpromotion=True",
        "deployment_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_post_training_nonpromotion_artifact_audit",
    ]
    for needle in needles:
        assert needle in text
        assert needle in audit
