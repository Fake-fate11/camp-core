from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_profile_artifact_audit.md"
)


def test_development_profile_artifact_audit_records_expected_fail_closed() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=development_profile_artifact_audit_passed_fail_closed",
        "profile=dp_native_feasible_ranking_development_minimal_v1",
        "profile_exit=1",
        "profile_exit_expected=True",
        "passed=False",
        "records=36",
        "usable_feasible_records=31",
        'failed_checks=["records_at_least_min", "usable_feasible_records_at_least_min", "routes_at_least_min", "seeds_at_least_min"]',
        "raw_record_gap=64",
        "usable_feasible_record_gap=69",
        "route_gap=1",
        "seed_gap=1",
        "training_execution_authorized=False",
        "camp_retraining_authorized=False",
        "collection_replay_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_clean_collection_scope_plan_only",
    ]:
        assert needle in text

    assert "training_execution_authorized=True" not in text
    assert "camp_retraining_authorized=True" not in text
    assert "collection_replay_authorized=True" not in text
    assert "safety_benefit_claim_authorized=True" not in text
    assert "camp_over_dp_top1_claim_authorized=True" not in text


def test_development_profile_artifact_audit_records_remote_evidence() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "autodl_CAMP_HEAD=f4f0a9cfc597de052a48804de2a146396380fbbe",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "remote_target_pytest=7 passed in 0.35s",
        "profile_report.json=00795d3afcc16b284acf0ff6de01f960e16c3d75c1704c4cfc1e9608ce10714b",
        "profile_report.md=9c091157c5fc45d26042f2c476d9f4aabc3aea61c040a42360810e516aa6d8f6",
    ]:
        assert needle in text
