from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_result.md"
)


def test_broader_nonformal_static_dp_reward_eval_passed() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_passed_fallback_feasibility_diagnostic_nonpromotion",
        "passed=True",
        "all_replay_exits_zero=True",
        'replay_exit_counts={"0": 12}',
        "run_count=12",
        "total_selection_records=60",
        "expected_selection_records=60",
        "total_provenance_records=60",
        "total_payload_valid_records=60",
        "total_prepost_equal_records=60",
        "total_no_candidate_row_append_records=60",
        "total_no_coordinate_heading_speed_rewrite_records=60",
        "total_selected_index_in_range_records=60",
        "schema_version=dp_native_static_dp_reward_broader_nonformal_eval_development_result_v1",
        "candidate_tensor_provenance_logging_verified=True",
        "candidate_tensor_prepost_hash_equal_all_records=True",
    ]:
        assert needle in text


def test_broader_nonformal_fallback_feasibility_diagnostic_is_recorded() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "total_records_with_feasible_candidate=45",
        "total_records_without_feasible_candidate=15",
        "total_records_with_selected_feasible_candidate=45",
        '| `sample_normal` | 20 | 20 | 0 | 1.0 | 0.0 |',
        '| `sample_tl` | 20 | 9 | 11 | 0.3625 | 0.55 |',
        '| `nishishinjuku_lane_change` | 20 | 16 | 4 | 0.7375 | 0.2 |',
        "sample_normal_clean_feasible_support_observed=True",
        "sample_tl_fallback_feasibility_blocker_observed=True",
        "nishishinjuku_lane_change_partial_fallback_feasibility_blocker_observed=True",
    ]:
        assert needle in text


def test_broader_nonformal_boundaries_are_not_promoted() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "nonformal_replay_evaluation_development_smoke_only=True",
        "full36_executed=False",
        "formal_seeds_executed=False",
        "dp_modified=False",
        "reference_blend_enabled=False",
        "guidance_enabled=False",
        "postprocess_postselection_enabled=False",
        "closed_loop_outcome_online_input_used=False",
        "selector_promotion_executed=False",
        "atom_promotion_executed=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "new_candidate_generator_executed=False",
        "camp_retraining_for_deployment_authorized=False",
        "camp_retraining_for_deployment_executed=False",
        "online_selector_promotion_authorized=False",
        "remote_total_closed_loop_outcome_online_input_records=0",
    ]:
        assert needle in text

    for forbidden in [
        "full36_executed=True",
        "formal_seeds_executed=True",
        "dp_modified=True",
        "reference_blend_enabled=True",
        "guidance_enabled=True",
        "postprocess_postselection_enabled=True",
        "closed_loop_outcome_online_input_used=True",
        "selector_promotion_executed=True",
        "atom_promotion_executed=True",
        "deployable_checkpoint_claim_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in text


def test_broader_nonformal_records_remote_artifact_and_next_gate() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "evaluation_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_broader_nonformal_eval_1c235eb_20260624T092550Z",
        "autodl_CAMP_HEAD=1c235ebcad52143297852d4873d345710be31680",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "broader_nonformal_eval_summary.json` | `c39fa6278431e08ee16b7b45f6645e43fa46f9951981c1fff8fa1809778aea07",
        "run_broader_nonformal_eval.py` | `66cfb0479b7b6e050f22e4d2f96323048464bd2cf63cd3eb58a684d978d2025d",
        "sample_tl_seed109_tl_on_static` | 0 | 5 | 0 | 5 | 0.0 | 1.0",
        "sample_tl_seed110_tl_on_static` | 0 | 5 | 0 | 5 | 0.0 | 1.0",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fallback_feasibility_attribution_only",
    ]:
        assert needle in text
