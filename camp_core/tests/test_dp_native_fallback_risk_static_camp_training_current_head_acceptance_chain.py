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
        "training_commit=e3e7c2265f6362cc63229153c521acff2014dc1c",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "dataset_json_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "training_split_manifest_json_sha256=13fa6b86d2fcebbb3ecbb675daefa7409f1f427900896307474d2d1dc4f6e773",
        "train_only_scale_manifest_json_sha256=452828bf134fb4d5d74d8a491597ee4c50f82893622e283546ea69f2b16da934",
        "fallback_master_config_json_sha256=081a31214f18d1608a440b8826cd4cd4febaa6760284e8f01cbd0749b502e1b9",
        "training_command_plan_json_sha256=a56c86337d5576811d866a7b080a629cadb2f692a02fed7675be20e1810aec3a",
        "preflight_json_sha256=22ad4437d0cfa2eea0884d340c9c0fd6073824ce86bbf263d6f4e3e4bff6d51b",
        "training_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_acceptance_e3e7c22_20260625T163942Z",
        "training_exit=0",
        "training_summary_json_sha256=0afa8fa4a59586294099ec8e8390e21e72539ac36163cf63f5515aa8cd52eb67",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "offline_weights_json_sha256=0944dd48fdf64dd79e3a4bbdef46b9b82af9604c44569c7b2109732f24ff8b95",
        "atom_scales_json_sha256=b2e0b3b4b2e2b3e5bf30ea546483c65e7f201b333d9eb1299763a89d19cc88bc",
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
        "nonpromotion_audit_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_e3e7c22_20260625T164050Z",
        "nonpromotion_audit_json_sha256=4275f076cd308dd07d6d79ae0716dd52a7e15b226ecb7eab9c2798f8542260b6",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "training_artifacts_nonpromotion=True",
        "weights_json_simplex_nonnegative=True",
        "weights_npy_simplex_nonnegative=True",
        "weights_json_matches_npy=True",
        "holdout_audit_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_development_holdout_acceptance_audit_e3e7c22_20260625T164050Z",
        "holdout_audit_json_sha256=2e83de4d8283ea31683527a68322e0744d7c152ecf4d7548cfe5cecb1d0b5bcf",
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


def test_iteration_audit_records_current_head_training_chain_and_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    recent_audit = audit[-20000:]

    for needle in [
        "status=fallback_risk_static_camp_training_current_head_acceptance_chain_passed",
        "acceptance_doc=docs/dp_native_fallback_risk_static_camp_training_current_head_acceptance_chain.md",
        "training_commit=e3e7c2265f6362cc63229153c521acff2014dc1c",
        "training_summary_json_sha256=0afa8fa4a59586294099ec8e8390e21e72539ac36163cf63f5515aa8cd52eb67",
        "nonpromotion_audit_json_sha256=4275f076cd308dd07d6d79ae0716dd52a7e15b226ecb7eab9c2798f8542260b6",
        "holdout_audit_json_sha256=2e83de4d8283ea31683527a68322e0744d7c152ecf4d7548cfe5cecb1d0b5bcf",
        "camp_retraining_completed=True",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "development_holdout_acceptance_audit_passed=True",
        "holdout_static_underperforms_uniform=True",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in recent_audit

    assert recent_audit.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fixed_artifact_fallback_risk_ranking_audit_only`"
    )
