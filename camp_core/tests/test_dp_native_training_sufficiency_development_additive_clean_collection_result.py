from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_additive_clean_collection_result.md"
)


def test_additive_collection_result_records_profile_pass() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=development_additive_collection_clean_contract_and_profile_passed_training_still_blocked",
        "addon_run_count=16",
        "addon_selection_log_count=16",
        "addon_records=80",
        "addon_usable_feasible_records=68",
        "combined_selection_log_count=40",
        "combined_records=200",
        "combined_usable_feasible_records=140",
        "combined_required_usable_feasible_records=100",
        "combined_usable_feasible_margin=40",
        "clean_contract_validator_exit=0",
        "clean_contract_validator_passed=True",
        "clean_contract_validator_failed_records=0",
        "development_profile_exit=0",
        "development_profile_passed=True",
        "development_profile_failed_checks=[]",
        "usable_feasible_records_sufficient=True",
    ]:
        assert needle in text


def test_additive_collection_result_preserves_forbidden_boundaries() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "forbidden_flags_present_in_commands=[]",
        "closed_loop_outcome_collection_enabled=False",
        "reference_blend_enabled=False",
        "guidance_enabled=False",
        "postprocess_postselection_enabled=False",
        "camp_training_executed=False",
        "dp_modified=False",
        "selector_promotion_executed=False",
        "atom_promotion_executed=False",
        "training_execution_authorized=False",
        "camp_retraining_authorized=False",
        "dp_modification_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "--camp_collect_closed_loop_outcomes",
        "--candidate_reference_blend_steps",
        "--candidate_guidance_config",
        "--camp_perfect_tracker_command_postselection",
        "--camp_traffic_light_hybrid_postselection",
        "formal seeds 11/12/13",
    ]:
        assert needle in text

    assert "training_execution_authorized=True" not in text
    assert "camp_retraining_authorized=True" not in text
    assert "dp_modification_authorized=True" not in text
    assert "safety_benefit_claim_authorized=True" not in text
    assert "camp_over_dp_top1_claim_authorized=True" not in text


def test_additive_collection_result_records_remote_evidence_and_next_gate() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "additive_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_additive_clean_collection_79343f9_20260624T082432Z",
        "autodl_CAMP_HEAD=79343f9f50299849d1d3ebc5b6a49cab86752096",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "collection_summary.json` | `4247b91acd9a6af8db83b8ad55f31e13a4f0c708f80c8ecfbd8cfdfdfc9b1eb3",
        "combined_clean_validator_stdout_stderr.log` | `f481a26294a30f2c2bea74349857fe388151f721a6172fa192a41bf2f4f96755",
        "combined_development_profile_stdout_stderr.log` | `227f4e7580e229377ecd711b2e3b5ea3648017d4f0d94aed055a0ff2a89a87d1",
        'combined_counts_by_route={"nishishinjuku_lane_change": 40, "sample_normal": 80, "sample_tl": 80}',
        'combined_usable_by_route={"sample_normal": 80, "sample_tl": 60}',
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_training_user_authorization_pending",
        "--require_dp_native_training_data_contract",
        "--require_atom_schema",
    ]:
        assert needle in text
