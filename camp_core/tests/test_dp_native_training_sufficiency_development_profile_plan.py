from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT / "docs" / "dp_native_training_sufficiency_development_profile_plan.md"
)


def test_development_profile_plan_blocks_training_and_claims() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=development_profile_plan_ready",
        "profile_name=dp_native_feasible_ranking_development_minimal_v1",
        "current_artifact_passes_profile=False",
        "failure_class=coverage_and_split_profile_gap",
        "direct_camp_retraining_blocked=True",
        "training_execution_authorized=False",
        "camp_retraining_authorized=False",
        "collection_replay_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_profile_default_off_implementation",
    ]:
        assert needle in text

    assert "training_execution_authorized=True" not in text
    assert "camp_retraining_authorized=True" not in text
    assert "collection_replay_authorized=True" not in text
    assert "safety_benefit_claim_authorized=True" not in text
    assert "camp_over_dp_top1_claim_authorized=True" not in text


def test_development_profile_plan_preserves_paper_boundary() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "fixed 36-record artifact",
        "mode=static",
        "training_scope=feasible_ranking",
        "require_candidate_tensor_provenance=True",
        "require_pre_post_tensor_hash_equal=True",
        "require_no_coordinate_heading_speed_rewrite_by_camp=True",
        "require_no_online_outcome_label_input=True",
        "allowed_atom_schemas=[",
        '"dp_camp_v10_14d"',
        "min_raw_records=100",
        "min_usable_feasible_records=100",
        "min_routes=3",
        "min_seeds=4",
        "min_candidate_count=4",
        "require_heldout_split=True",
        "reference_blend=False",
        "guidance=False",
        "postprocess_mainline=False",
        "postselection_mainline=False",
        "splice_or_materialized_generator=False",
        "dp_code_config_or_weight_change=False",
    ]:
        assert needle in text
