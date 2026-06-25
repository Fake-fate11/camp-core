from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CHAIN_DOC = REPO_ROOT / "docs" / "dp_native_fallback_risk_static_camp_training_current_head_acceptance_chain.md"
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _chain() -> str:
    return CHAIN_DOC.read_text(encoding="utf-8")


def test_current_head_training_chain_records_fixed_inputs_and_training_outputs() -> None:
    text = _chain()

    for needle in [
        "training_commit=b2ced479ac2d6c6f9fc7fafd5acd3a9005dcbe69",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "dataset_json_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "training_split_manifest_json_sha256=b6f8cdcc0e353e1efdc81c62d0e81aa1f4b0679270f1bb211879ac03adce8079",
        "train_only_scale_manifest_json_sha256=5ad58c9fee35d8e21922385993edb28d4934b8066a2cf683af28f12384a976cf",
        "fallback_master_config_json_sha256=6dbd94ea34e8374ac616817d64d6f93baa0d9da4828e3af6c32474a91cf3a7f3",
        "training_command_plan_json_sha256=f5128aca1566783ef02a464970f2e1623abf9f69d2d724cae2d6995176c89e82",
        "preflight_json_sha256=3f17ecd558e7f18da2c8a10c39df52533d18ead5f8444e38553fd784bb8f62dd",
        "training_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_acceptance_b2ced47_20260625T051316Z",
        "training_exit=0",
        "training_summary_json_sha256=11205caf602bfdc72f91c80ca4dc24a15b18c63087bb457e00424c78a6b85a9b",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "offline_weights_json_sha256=4db438a6ea34b12d30d067b45aa8f110c8ab98dcbb8230e4309b9d05123e584c",
        "atom_scales_json_sha256=8f9b5843e245364498ffa6041fa8302f95e45126ec3a84217e8f6c3b25bdecf8",
    ]:
        assert needle in text


def test_current_head_training_chain_records_camp_only_training_boundary() -> None:
    text = _chain()

    for needle in [
        "status=dp_native_fallback_risk_static_camp_training_complete",
        "training_authorized=True",
        "training_execution_authorized=True",
        "training_executed=True",
        "camp_retraining_authorized_now=True",
        "fallback_risk_training_authorized_now=True",
        "fixed_dp_candidate_reranking_only=True",
        "fallback_only_training=True",
        "training_records=13",
        "validation_records=2",
        "num_candidates=4",
        "num_atoms=14",
        "atom_schema_version=dp_camp_v10_14d",
        "score_k(w)=a_k^T w",
        "weights_sum=1.0",
        "weights_min=0.0",
        "weights_max=1.0",
    ]:
        assert needle in text


def test_current_head_chain_records_nonpromotion_and_holdout_diagnostics() -> None:
    text = _chain()

    for needle in [
        "nonpromotion_audit_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_b2ced47_20260625T051403Z",
        "nonpromotion_audit_json_sha256=cc66e9143b5ba1806a3bb0a1a8687c4ed8632726f167e13abc2dbbfa550d1532",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "training_artifacts_nonpromotion=True",
        "weights_json_simplex_nonnegative=True",
        "weights_npy_simplex_nonnegative=True",
        "weights_json_matches_npy=True",
        "holdout_audit_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_development_holdout_acceptance_audit_b2ced47_20260625T051442Z",
        "holdout_audit_json_sha256=71858712dd1479c43332965778f251787a6033c730e0178b6aad599ef36774c3",
        "development_holdout_acceptance_audit_passed=True",
        "records_scope=validation_groups_only",
        "static_oracle_match_rate=0.5",
        "uniform_oracle_match_rate=1.0",
        "recorded_oracle_match_rate=1.0",
        "holdout_static_underperforms_uniform=True",
    ]:
        assert needle in text


def test_current_head_chain_forbids_promotion_deployment_dp_changes_and_claims() -> None:
    text = _chain()

    for needle in [
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "Full36_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "reference_blend_authorized=False",
        "guidance_authorized=False",
        "postprocess_postselection_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "deployment_authorized=False",
        "promotion_authorized=False",
    ]:
        assert needle in text

    for forbidden in [
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "deployable_checkpoint_claim_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "deployment_authorized=True",
        "promotion_authorized=True",
    ]:
        assert forbidden not in text


def test_iteration_audit_tail_records_current_head_training_chain_and_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-170:])

    for needle in [
        "status=fallback_risk_static_camp_training_current_head_acceptance_chain_passed",
        "acceptance_doc=docs/dp_native_fallback_risk_static_camp_training_current_head_acceptance_chain.md",
        "camp_retraining_completed=True",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "development_holdout_acceptance_audit_passed=True",
        "holdout_static_underperforms_uniform=True",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in tail

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fixed_artifact_fallback_risk_ranking_audit_only`"
    )
