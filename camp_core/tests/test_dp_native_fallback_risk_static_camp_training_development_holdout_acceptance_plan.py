from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_development_holdout_acceptance_plan.md"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _plan_text() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_development_holdout_acceptance_plan_is_plan_only() -> None:
    text = _plan_text()

    for needle in [
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_development_holdout_acceptance_plan_only",
        "plan_only=True",
        "audit_only_next=True",
        "records_scope=validation_groups_only",
        "fallback_branch_only=True",
        "records_without_feasible_candidate_only=True",
        "development_holdout_acceptance_audit_authorized_next=True",
    ]:
        assert needle in text


def test_development_holdout_plan_preserves_fixed_candidate_benders_boundary() -> None:
    text = _plan_text()

    for needle in [
        "required_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "require_atom_schema_version=dp_camp_v10_14d",
        "require_num_atoms=14",
        "require_weights_simplex_nonnegative=True",
        "require_atom_scales_strictly_positive=True",
        "score_expression=score_k(w)=a_k^T w",
        "selection_rule=argmin_k score_k(w)",
        "selected_index_in_range=True",
        "candidate_count_unchanged=True",
        "candidate_tensor_unchanged=True",
        "pre_post_candidate_provenance_hashes_equal_if_present=True",
        "recomputed_selected_index_matches_argmin=True",
    ]:
        assert needle in text


def test_development_holdout_plan_forbids_execution_training_and_promotion() -> None:
    text = _plan_text()

    for needle in [
        "training_authorized=False",
        "training_execution_authorized=False",
        "camp_retraining_authorized_now=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "Full36_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "reference_blend_authorized=False",
        "guidance_authorized=False",
        "postprocess_postselection_authorized=False",
        "closed_loop_outcome_online_input_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
        "deployment_authorized=False",
    ]:
        assert needle in text

    forbidden_true = [
        "training_authorized=True",
        "training_execution_authorized=True",
        "camp_retraining_authorized_now=True",
        "replay_execution_authorized=True",
        "candidate_generation_authorized=True",
        "Full36_authorized=True",
        "formal_seeds_11_12_13_authorized=True",
        "dp_modification_authorized=True",
        "reference_blend_authorized=True",
        "guidance_authorized=True",
        "postprocess_postselection_authorized=True",
        "closed_loop_outcome_online_input_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "deployable_checkpoint_claim_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "production_selector_change_authorized=True",
        "online_selector_change_authorized=True",
        "deployment_authorized=True",
    ]
    for needle in forbidden_true:
        assert needle not in text


def test_development_holdout_plan_handles_missing_provenance_without_overclaim() -> None:
    text = _plan_text()

    for needle in [
        "If provenance hashes are absent from an older artifact",
        "must not use their absence as positive proof of",
        "fixed-artifact evidence for a development-holdout consistency check",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text


def test_iteration_audit_records_development_holdout_plan_and_next_gate() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_static_camp_training_development_holdout_acceptance_plan_only_passed",
        "development_holdout_acceptance_audit_authorized_next=True",
        "records_scope=validation_groups_only",
        "score_expression=score_k(w)=a_k^T w",
        "candidate_tensor_unchanged=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_development_holdout_acceptance_audit_only",
    ]:
        assert needle in text


def test_current_head_722875d_development_holdout_plan_is_pinned() -> None:
    text = _plan_text()
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "training_commit=adab72980bfad5fa13172d183feda672d766eba9",
        "plan_start_head=722875db6f0ccb2f0afb37d75f412577e0033def",
        "training_summary_json_sha256=5b362f29f3737a1015ea977401c5fdafe2cff8e87426555d1ab7140c3ecc8761",
        "offline_weights_json_sha256=75e879d5f9345e49d2ccf4b477ba26863016fe6bcf6adb05c9c48a7cdd772b03",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "atom_scales_json_sha256=69f3618f21687e08793bf766a57747fa121321be9de3e5a71f5a75b5407cfa88",
        "dataset_json_sha256=682d432f742d4ab68a262cf70955981bc1562cf1dbcf2ec094984a12fcd11498",
        "training_split_manifest_json_sha256=e0a4ec0623f5db0b868465249ce9615b06b86f6c91067702af3bee9fd700db1d",
        "train_only_scale_manifest_json_sha256=92059b9c60e66c96db836821cb0060072402089b915e0bbd87240fc24c602567",
        "fallback_master_config_json_sha256=c513fd6da7768a7444cdecea25797649c131efaa5b548335b10e07c24758c95b",
        "preflight_json_sha256=b1ec5b1d5e3d895d7123dc08b86656bfd1901bd0fd0e5339b503aafa13b58252",
        "plan_only=True",
        "development_holdout_acceptance_audit_authorized_next=True",
        "local_target_pytest=12 passed",
        "autodl_target_pytest=12 passed",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "training_authorized=False",
        "selector_promotion_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

    assert (
        "status=fallback_risk_static_camp_training_development_holdout_acceptance_plan_only_current_head_722875d_passed"
        in audit
    )


def test_current_head_0fb6736_development_holdout_plan_is_pinned() -> None:
    text = _plan_text()
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "training_commit=5c913aea29d821dbfb8bf47313309e9a7dafd305",
        "plan_start_head=0fb6736bebc0992effb02c22cd4cedd859b9c215",
        "nonpromotion_audit_execution_head=fc21a130eb346e94b8a8fba8f1515e27e866ad7d",
        "training_summary_json_sha256=a82d2403276e2aaf3e151271426bfca91e113b4e79735a8ead7a359ee8f24fb4",
        "offline_weights_json_sha256=08fe4290defde501f03e99dc752c95432778b9fb973262255e9cf98ec097d0a3",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "atom_scales_json_sha256=10360c02c3deb38a6504781497b4fb5f082e59e63d3aee961f691f4e853a1b21",
        "nonpromotion_audit_json_sha256=2f9f9c163bb14a0b058d33d051d32d0c153a422429260c1ebea6527e5a556bea",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "dataset_json_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "train_only_scale_manifest_json_sha256=8ec568461fb0887143b28899388544091aa613500673a2ffe7b1891316e62759",
        "fallback_master_config_json_sha256=ea9d8ddf4bbf6a4fdebca9685c6cc1b625c3803837114301bb3537982a030364",
        "preflight_json_sha256=8f68f312188ada4661aa6cb7dc91cbb9c5537df147ac5c3f0851ee6a5d00e8c5",
        "plan_only=True",
        "development_holdout_acceptance_audit_authorized_next=True",
        "training_authorized=False",
        "selector_promotion_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

    assert (
        "status=fallback_risk_static_camp_training_development_holdout_acceptance_plan_only_current_head_0fb6736_passed"
        in audit
    )


def test_current_head_a29a0f5_development_holdout_plan_is_pinned() -> None:
    text = _plan_text()
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "training_commit=ca07b6acd82ebb1c195d15b95584fc3ce613d758",
        "plan_start_head=a29a0f5c58fbf67329f9a4b4905050f8e0f1f04d",
        "nonpromotion_audit_execution_head=fa5eeaf601c051dde2e30b6647b5f9eabb991952",
        "training_summary_json_sha256=22aec7885c32fc8b514184fd0eb25f1d177be1f41419a62178607f4a26e5ca11",
        "offline_weights_json_sha256=d05f35bb83ed160f98f498a6d7d80483d2da3f396af8a73cbdbaab31db7e5b5e",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "atom_scales_json_sha256=a1dd6249c59290a7b345d377512fa074a1a4c019d45d30a40637bdbfb8b141d5",
        "nonpromotion_audit_json_sha256=c2c746b557f300720fd2e146d38899cb2574501aa1fe4b17d89c721d517e5cf0",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "dataset_json_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "train_only_scale_manifest_json_sha256=013db2348319ad5a959c33bc2a078b8b7162969bbd3f5633ca34d1b7ce2ef04b",
        "fallback_master_config_json_sha256=10ebf96545e244b4e3fcf657c0897a5f6f3eb72357ea9259b53de19dd2f6dc3a",
        "preflight_json_sha256=72ca918aa05fd92b120ef7f8631a5d6984f1dfd649d9659e84f7f9beb7fc786c",
        "plan_only=True",
        "development_holdout_acceptance_audit_authorized_next=True",
        "training_authorized=False",
        "selector_promotion_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

    assert (
        "status=fallback_risk_static_camp_training_development_holdout_acceptance_plan_only_current_head_a29a0f5_passed"
        in audit
    )


def test_current_head_440f390_development_holdout_plan_is_pinned() -> None:
    text = _plan_text()
    audit_tail = "\n".join(AUDIT_DOC.read_text(encoding="utf-8").splitlines()[-240:])

    for needle in [
        "training_commit=34bdb4b3ac115700568f989c74a54706a0250e09",
        "plan_start_head=440f3904fe428591fada8605776bb3200c8489b6",
        "nonpromotion_audit_execution_head=ecc4a6ed5a54c04fafb6b9bf396eed3e6f6841e8",
        "training_summary_json_sha256=c37307b62210204bbd2a26730f9b4c2f209deb1c3d921eabb7214bb168f5c5ce",
        "offline_weights_json_sha256=d5be3af9de82f2032145915e0ce2947248850dc3643a9b0a526a625232bce3fb",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "atom_scales_json_sha256=ff6a513c25d5dd4ac10672c54751023b2ca400b3fd202fcb42bc95d4e24ee7c2",
        "nonpromotion_audit_json_sha256=4acb0ae9405b52479eebeeb63a6fb7fca3e0b66a819a82112f1a47e1880a4fb9",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "dataset_json_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "train_only_scale_manifest_json_sha256=b11cba57efc5761417c539cfbf009866fc8c5f1466a1f041073ea88f6a3b618d",
        "fallback_master_config_json_sha256=fdef70d470721fdf9dabb2c44f3ae2656da177aa2345fbaf6b225b00e7576200",
        "preflight_json_sha256=c816b04fc3171514cdef8ad3643ba138c86b5361b3e5c2ce577de9d2dd3f0809",
        "plan_only=True",
        "development_holdout_acceptance_audit_authorized_next=True",
        "training_authorized=False",
        "selector_promotion_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

    for needle in [
        "status=fallback_risk_static_camp_training_development_holdout_acceptance_plan_only_current_head_440f390_passed",
        "development_holdout_acceptance_audit_authorized_next=True",
        "records_scope=validation_groups_only",
        "candidate_tensor_unchanged=True",
    ]:
        assert needle in audit_tail

    assert audit_tail.rstrip().endswith(
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_development_holdout_acceptance_audit_only\n```"
    )
