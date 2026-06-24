from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_clean_collection_scope_plan.md"
)


def test_collection_scope_plan_requires_user_authorization() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=development_clean_collection_scope_plan_ready_user_authorization_required",
        "collection_replay_authorized_now=False",
        "candidate_generation_authorized_now=False",
        "training_execution_authorized=False",
        "camp_retraining_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_collection_user_authorization_pending",
    ]:
        assert needle in text

    assert "collection_replay_authorized_now=True" not in text
    assert "candidate_generation_authorized_now=True" not in text
    assert "training_execution_authorized=True" not in text
    assert "safety_benefit_claim_authorized=True" not in text


def test_collection_scope_plan_matches_development_profile_gaps() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "raw_record_gap=64",
        "usable_feasible_record_gap=69",
        "route_gap=1",
        "seed_gap=1",
        "routes=sample_normal,sample_tl,nishishinjuku_lane_change",
        "seeds=101,102,103,104",
        "traffic_lights=on,off",
        "steps=5",
        "num_candidates=4",
        "candidate_noise_strategy=iid",
        "expected_run_count=24",
        "expected_max_selection_records=120",
        "must_pass_profile=dp_native_feasible_ranking_development_minimal_v1",
        "required_usable_feasible_records_at_least=100",
        "--camp_candidate_tensor_provenance_logging",
        "--candidate_reference_blend_steps",
        "--candidate_guidance_config",
        "formal seeds 11/12/13",
    ]:
        assert needle in text
