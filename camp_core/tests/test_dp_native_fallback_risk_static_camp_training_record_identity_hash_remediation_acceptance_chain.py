from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_record_identity_hash_remediation_acceptance_chain.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _doc() -> str:
    return DOC.read_text(encoding="utf-8")


def test_training_chain_records_fixed_inputs_and_training_outputs() -> None:
    text = _doc()

    for needle in [
        "dataset_json_sha256=8e7d42e2d1319dc2a479903d7b1be5a463f2d74fe733b523fdbac09bf90bd9b9",
        "training_split_manifest_json_sha256=9eb6f64a392a8ba1c6037c9dc8389ad9459615c039ad2b3426747785b75e5a78",
        "train_only_scale_manifest_json_sha256=d4205878c3af549ed86a778236500997df302272ab671bfcb60bc5f18b03b812",
        "fallback_master_config_json_sha256=3af141fa2e1374d10f7381bebeeabe0aa85bdd5b9f59fc38c91c080aec1b33d4",
        "training_command_plan_json_sha256=1d10adb5484ae286f04b008b6b6acbc18cba4ec09fdc644ebd490752b5d067ef",
        "preflight_json_sha256=c44b932ecf518a9ed69979bf9b2efb40020b5ec3a0e4bd221037c5eb9aaca7e3",
        "training_commit=5cc2ce29caab5ebeec41a96f66daf4118700b0b6",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "training_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_record_identity_acceptance_5cc2ce2_20260624T225031Z",
        "training_summary_json_sha256=c5dff5d4b7ab7f7e0bcba22bc90e55701306ed6b87f56436533dc45528eff4cd",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "offline_weights_json_sha256=c663380af7540bca8482f2fed600858057057856e2e55e7233c844b6c5463f06",
        "atom_scales_json_sha256=49d9ae6642f7f980e023f97b1879df06338672d746fda871d2d05b35787654bc",
    ]:
        assert needle in text


def test_training_chain_records_training_scope_weights_and_metrics() -> None:
    text = _doc()

    for needle in [
        "status=dp_native_fallback_risk_static_camp_training_complete",
        "training_authorized=True",
        "training_execution_authorized=True",
        "training_executed=True",
        "camp_retraining_started=True",
        "camp_retraining_completed=True",
        "fixed_dp_candidate_reranking_only=True",
        "fallback_only_training=True",
        "score_k(w)=a_k^T w",
        "objective=simplex_hinge_cvar_l2",
        "training_seed_recorded=23",
        "formal_seeds_11_12_13_used=False",
        "training_records=13",
        "validation_records=2",
        "num_candidates=4",
        "num_atoms=14",
        "weights_sum=1.0",
        "weights_min=0.0",
        "weights_max=1.0",
        "trained_weights=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]",
        "train_oracle_match_rate=0.3076923076923077",
        "validation_oracle_match_rate=0.5",
    ]:
        assert needle in text


def test_training_chain_records_nonpromotion_artifact_audit() -> None:
    text = _doc()

    for needle in [
        "nonpromotion_audit_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_record_identity_5cc2ce2_20260624T225134Z",
        "nonpromotion_audit_json_sha256=bafc45ef3667ce749a4620342611d5075617fac5f1c696ba0373e62805d24e85",
        "status=dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_complete",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "training_artifacts_nonpromotion=True",
        "weights_json_simplex_nonnegative=True",
        "weights_npy_simplex_nonnegative=True",
        "weights_json_matches_npy=True",
        "atom_scales_strictly_positive=True",
        "deployment_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
    ]:
        assert needle in text


def test_training_chain_records_development_holdout_without_overclaim() -> None:
    text = _doc()

    for needle in [
        "holdout_audit_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_development_holdout_acceptance_audit_record_identity_5cc2ce2_20260624T225217Z",
        "holdout_audit_json_sha256=67eb36360f356aee86a51b96188b79e91850cd8a80dc51233518ffb74afc2d77",
        "status=dp_native_fallback_risk_static_camp_training_development_holdout_acceptance_audit_complete",
        "development_holdout_acceptance_audit_passed=True",
        "records_scope=validation_groups_only",
        "records_without_feasible_candidate_only=True",
        "selection_rule=argmin_k score_k(w)",
        "static_oracle_match_rate=0.5",
        "uniform_oracle_match_rate=1.0",
        "recorded_oracle_match_rate=1.0",
        "candidate_tensor_unchanged=True",
        "candidate_count_unchanged=True",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "does not authorize promotion or claim performance improvement",
    ]:
        assert needle in text


def test_training_chain_records_verification_and_forbidden_boundaries() -> None:
    text = _doc()

    for needle in [
        "local_record_identity_training_chain_pytest=6 passed",
        "local_record_identity_related_pytest=111 passed",
        "local_static_camp_training_related_pytest=37 passed",
        "autodl_record_identity_training_chain_pytest=6 passed",
        "autodl_record_identity_related_pytest=111 passed",
        "autodl_static_camp_training_related_pytest=37 passed",
        "autodl_git_diff_check_exit=0",
        "status=fallback_risk_static_camp_training_record_identity_hash_remediation_acceptance_chain_passed",
        "training_artifacts_created=True",
        "deployment_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "dp_modification_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_holdout_acceptance_static_contract_review",
    ]:
        assert needle in text

    for forbidden in [
        "deployment_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "dp_modification_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in text


def test_iteration_audit_tail_records_training_chain_next_gate() -> None:
    tail = "\n".join(ITERATION_AUDIT.read_text(encoding="utf-8").splitlines()[-190:])

    for needle in [
        "status=fallback_risk_static_camp_training_record_identity_hash_remediation_acceptance_chain_passed",
        "camp_retraining_completed=True",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "development_holdout_acceptance_audit_passed=True",
        "deployment_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in tail

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_holdout_acceptance_static_contract_review`"
    )
