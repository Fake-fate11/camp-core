from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_static_dp_reward_training_smoke_artifact_nonpromotion_audit.md"
)
SMOKE_RESULT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_clean_training_log_minimal_static_dp_reward_training_smoke_result.md"
)
RUNTIME_SELECTOR_SOURCE = (
    REPO_ROOT / "camp_core" / "camp_core" / "integrations" / "diffusion_planner.py"
)
STATIC_TRAINER_SOURCE = (
    REPO_ROOT / "scripts" / "integrations" / "train_diffusion_planner_static_camp.py"
)

SMOKE_RUN_ROOT = (
    "/root/autodl-tmp/"
    "camp_dp_native_clean_training_log_minimal_static_dp_reward_training_smoke_"
    "b46626b4_20260624T062215Z"
)


def test_nonpromotion_audit_records_forbidden_claims_as_false() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")
    smoke_text = SMOKE_RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=static_dp_reward_training_smoke_artifact_nonpromotion_audit_passed",
        "nondeployable_training_smoke_only=True",
        "deployable_checkpoint_claimed=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "dp_modification_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "replay_executed=False",
        "candidate_generation_executed=False",
        "camp_retraining_executed=False",
        "dp_native_candidate_tensor_provenance_payload_implementation_authorization_only",
    ]:
        assert needle in text

    assert "selector_promotion_authorized=True" not in text
    assert "atom_promotion_authorized=True" not in text
    assert "safety_benefit_claim_authorized=True" not in text
    assert "camp_over_dp_top1_claim_authorized=True" not in text
    assert "nondeployable_training_smoke_only=True" in smoke_text


def test_static_trainer_writes_weights_only_to_requested_output_dir() -> None:
    source = STATIC_TRAINER_SOURCE.read_text(encoding="utf-8")

    assert 'weights_path = args.output_dir / "offline_weights_dp_static.npy"' in source
    assert 'scales_path = args.output_dir / "atom_scales_dp_static.json"' in source
    assert '"Candidate-level DP rewards are model-based preferences' in source
    assert "baselines remain required for " in source
    assert '"for final claims."' in source


def test_runtime_selector_has_no_hardcoded_smoke_artifact_path() -> None:
    source = RUNTIME_SELECTOR_SOURCE.read_text(encoding="utf-8")

    assert SMOKE_RUN_ROOT not in source
    assert "77c0276b0cebc9f6ed3c88865c1930097a5ce48e266e60b6cbaf65a9ebe849bb" not in source
    assert "8046cac7b1aa43c7c0bcb83136828a813297e598084ff4924c66526b9bb0453c" not in source
    assert "if static_weights_path is not None:" in source
    assert "static_weights = np.load(str(static_weights_path))" in source
