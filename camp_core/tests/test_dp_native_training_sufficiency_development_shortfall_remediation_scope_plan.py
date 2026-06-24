from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_shortfall_remediation_scope_plan.md"
)


def test_remediation_scope_plan_requires_user_authorization() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=usable_feasible_shortfall_remediation_scope_plan_ready_user_authorization_required",
        "collection_replay_authorized_now=False",
        "candidate_generation_authorized_now=False",
        "training_execution_authorized=False",
        "camp_retraining_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_additive_clean_collection_user_authorization_pending",
    ]:
        assert needle in text

    assert "collection_replay_authorized_now=True" not in text
    assert "candidate_generation_authorized_now=True" not in text
    assert "training_execution_authorized=True" not in text
    assert "camp_retraining_authorized=True" not in text


def test_remediation_scope_plan_targets_observed_shortfall() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "base_usable_feasible_records=72",
        "base_required_usable_feasible_records=100",
        "base_usable_feasible_record_gap=28",
        'base_usable_by_route={"nishishinjuku_lane_change": 0, "sample_normal": 40, "sample_tl": 32}',
        "nishishinjuku_lane_change_unusable_records=40/40",
        "reuse_zero_support_lane_change_route_for_remediation=False",
        "addon_routes=sample_normal,sample_tl",
        "addon_seeds=105,106,107,108",
        "addon_expected_run_count=16",
        "addon_expected_max_selection_records=80",
        "addon_min_usable_needed_to_pass=28/80",
        "combined_expected_usable_if_observed_rate_repeats=144/200",
    ]:
        assert needle in text


def test_remediation_scope_plan_preserves_clean_dp_native_boundary() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "--camp_candidate_tensor_provenance_logging",
        "camp_feasibility_source=dp_reward",
        "candidate_noise_strategy=iid",
        "--camp_collect_closed_loop_outcomes",
        "--candidate_reference_blend_steps",
        "--candidate_guidance_config",
        "--camp_perfect_tracker_command_postselection",
        "--camp_traffic_light_hybrid_postselection",
        "--camp_underprogress_relaxation",
        "--camp_splice_shadow_rule",
        "formal seeds 11/12/13",
        "required_usable_feasible_records_at_least=100",
        "must_validate_base_plus_addon=True",
        "must_record_per_route_usable_counts=True",
        "must_record_all_false_reason_counts=True",
    ]:
        assert needle in text
