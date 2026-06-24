from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ATTRIBUTION_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_collection_usable_feasible_shortfall_attribution.md"
)


def test_shortfall_attribution_records_exact_profile_gap() -> None:
    text = ATTRIBUTION_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=usable_feasible_shortfall_attributed_fail_closed",
        "records=120",
        "usable_feasible_records=72",
        "required_usable_feasible_records=100",
        "usable_feasible_record_gap=28",
        "unusable_records=48",
        "(False, False, False, False)=48",
        'development_profile_failed_checks=["usable_feasible_records_at_least_min"]',
        "clean_contract_validator_passed=True",
        "label_source_records_present=True",
    ]:
        assert needle in text


def test_shortfall_attribution_records_route_and_reason_breakdown() -> None:
    text = ATTRIBUTION_DOC.read_text(encoding="utf-8")

    for needle in [
        "nishishinjuku_lane_change_records=40",
        "nishishinjuku_lane_change_usable_records=0",
        "nishishinjuku_lane_change_unusable_records=40",
        "nishishinjuku_lane_change_false_candidates=160/160",
        'nishishinjuku_lane_change_record_reasons={"dp_road_border": 40, "dp_lane_crossing": 40}',
        "sample_normal_usable_records=40",
        "sample_tl_unusable_records=8",
        'sample_tl_record_reasons={"dp_red_light": 5, "dp_lane_crossing": 4}',
        "dp_underprogress` appears only on false candidates inside otherwise usable",
        "primary_blocker=nishishinjuku_lane_change_all_candidates_dp_road_border_and_dp_lane_crossing",
        "secondary_blocker=sample_tl_red_light_and_lane_crossing_all_false_records",
    ]:
        assert needle in text


def test_shortfall_attribution_preserves_no_execution_boundaries() -> None:
    text = ATTRIBUTION_DOC.read_text(encoding="utf-8")

    for needle in [
        "remote_shortfall_attribution_analysis_exit=0",
        "remote_replay_executed_now=False",
        "remote_candidate_generation_executed_now=False",
        "remote_training_executed_now=False",
        "training_execution_authorized=False",
        "camp_retraining_authorized=False",
        "replay_authorized_now=False",
        "candidate_generation_authorized_now=False",
        "dp_modification_authorized=False",
        "online_selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_collection_usable_feasible_shortfall_remediation_scope_plan_only",
    ]:
        assert needle in text

    assert "training_execution_authorized=True" not in text
    assert "camp_retraining_authorized=True" not in text
    assert "dp_modification_authorized=True" not in text
    assert "safety_benefit_claim_authorized=True" not in text
    assert "camp_over_dp_top1_claim_authorized=True" not in text


def test_shortfall_attribution_records_fixed_artifact_hashes() -> None:
    text = ATTRIBUTION_DOC.read_text(encoding="utf-8")

    for needle in [
        "autodl_CAMP_HEAD=b19452b44e4d3ee87c1ba086ac13c3e174c28d26",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "collection_summary.json=363dcc3a81cc737e6962c983d77425f59e56f4acccd56200bb15397edbe05dc8",
        "clean_dp_native_training_data_contract_validation.json=056262e969d4084e5ecd971c2c9bddafd0d9b63c0049744069aacffde5773014",
        "development_profile_validation.json=2f62ab3575f5264faed34d6110fbba9ff8d552ea1b76585b0b488f5c61ce0259",
    ]:
        assert needle in text
