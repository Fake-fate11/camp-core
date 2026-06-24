from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fallback_feasibility_remediation_plan.md"
)


def test_fallback_feasibility_remediation_plan_targets_observed_blockers() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "records_total=60",
        "records_with_feasible_total=45",
        "records_without_feasible_total=15",
        'route_records_without_feasible={"nishishinjuku_lane_change": 4, "sample_tl": 11}',
        "sample_tl_on_no_feasible_records=10/10",
        "sample_tl_on_all_candidate_blocker=dp_red_light",
        "nishishinjuku_lane_change_no_feasible_records=4/20",
        "nishishinjuku_lane_change_all_candidate_blocker=dp_lane_crossing",
        "sample_normal_no_feasible_records=0/20",
        "primary_remediation_strategy=fixed_artifact_fallback_risk_ranking_audit_first",
    ]:
        assert needle in text


def test_fallback_feasibility_remediation_plan_preserves_math_boundary() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "hard_feasibility_relaxation_authorized=False",
        "dp_red_light_is_hard_reason=True",
        "dp_lane_crossing_is_hard_reason=True",
        "all_infeasible_records_admissible_for_current_feasible_ranking_master=False",
        "fallback_records_may_not_be_relabelled_feasible=True",
        "all_infeasible_records_added_to_feasible_training=False",
        "if_no_lower_risk_fixed_candidate_exists_then_selector_only_remediation_impossible=True",
        "camp_selector_improvement_claim_allowed=False",
    ]:
        assert needle in text

    for forbidden in [
        "hard_feasibility_relaxation_authorized=True",
        "all_infeasible_records_added_to_feasible_training=True",
        "camp_selector_improvement_claim_allowed=True",
    ]:
        assert forbidden not in text


def test_fallback_feasibility_remediation_plan_forbids_nonpaper_routes() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "Full36_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "reference_blend_authorized=False",
        "guidance_authorized=False",
        "postprocess_postselection_authorized=False",
        "closed_loop_outcome_online_input_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "--candidate_reference_blend_steps",
        "--candidate_guidance_config",
        "--camp_perfect_tracker_command_postselection",
        "--camp_traffic_light_hybrid_postselection",
        "--camp_underprogress_relaxation",
        "--camp_splice_shadow_rule",
    ]:
        assert needle in text

    for forbidden in [
        "candidate_generation_authorized=True",
        "camp_training_authorized=True",
        "dp_modification_authorized=True",
        "reference_blend_authorized=True",
        "guidance_authorized=True",
        "postprocess_postselection_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in text


def test_fallback_feasibility_remediation_plan_next_gate_is_read_only() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "audit_only=True",
        "source=evaluation_artifact",
        "records_scope=records_without_feasible_candidate_only",
        "required_no_feasible_records=15",
        "compare_selected_index_to_min_dp_red_light_cost=True",
        "compare_selected_index_to_min_lane_related_cost=True",
        "compare_selected_index_to_min_dp_reward_cost=True",
        "training_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fixed_artifact_fallback_risk_ranking_audit_only",
    ]:
        assert needle in text
