from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_collection_result.md"
)


def test_development_collection_result_records_fail_closed_profile_result() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=development_collection_clean_contract_passed_profile_failed_fail_closed",
        "run_count=24",
        "selection_log_count=24",
        "total_records=120",
        "clean_contract_validator_exit=0",
        "clean_contract_validator_passed=True",
        "development_profile_exit=1",
        "development_profile_exit_expected=True",
        "development_profile_passed=False",
        "development_profile_usable_feasible_records=72",
        "development_profile_required_usable_feasible_records=100",
        "development_profile_usable_feasible_record_gap=28",
        'development_profile_failed_checks=["usable_feasible_records_at_least_min"]',
        'hard_blocking_reasons=["usable_feasible_records_at_least_min"]',
        "failure_class=usable_feasible_record_shortfall",
        "usable_feasible_records_sufficient=False",
        "dp_native_training_sufficiency_development_collection_usable_feasible_shortfall_attribution_only",
    ]:
        assert needle in text


def test_development_collection_result_preserves_forbidden_boundaries() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "training_execution_authorized=False",
        "camp_retraining_authorized=False",
        "collection_replay_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "online_selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "--camp_collect_closed_loop_outcomes",
        "--candidate_reference_blend_steps",
        "--candidate_guidance_config",
        "--camp_perfect_tracker_command_postselection",
        "formal seeds 11/12/13",
    ]:
        assert needle in text

    assert "training_execution_authorized=True" not in text
    assert "camp_retraining_authorized=True" not in text
    assert "dp_modification_authorized=True" not in text
    assert "safety_benefit_claim_authorized=True" not in text
    assert "camp_over_dp_top1_claim_authorized=True" not in text


def test_development_collection_result_records_remote_evidence() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "autodl_CAMP_HEAD=73aec557ff32e69c4735a38eee29f372da6a4f6c",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "collection_summary.json` | `363dcc3a81cc737e6962c983d77425f59e56f4acccd56200bb15397edbe05dc8",
        "clean_validator_stdout_stderr.log` | `019e2bda9b896e978314b142dc1ba13a62a10b17988c6a190366e3c7d2eb6573",
        "development_profile_stdout_stderr.log` | `d6b6e9d726f6efaaf1fef91c0f1955c84613b9a0544a876ce2af1534d33f9f39",
        "| `nishishinjuku_lane_change` | 101 | off | 0 |",
        "| `sample_normal` | 104 | on | 0 |",
        "| `sample_tl` | 104 | on | 0 |",
    ]:
        assert needle in text
