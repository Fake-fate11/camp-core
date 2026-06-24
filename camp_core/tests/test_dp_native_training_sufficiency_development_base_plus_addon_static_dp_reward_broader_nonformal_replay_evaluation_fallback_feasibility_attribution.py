from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ATTRIBUTION_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fallback_feasibility_attribution.md"
)


def test_fallback_feasibility_attribution_counts() -> None:
    text = ATTRIBUTION_DOC.read_text(encoding="utf-8")

    for needle in [
        "records_total=60",
        "records_with_feasible_total=45",
        "records_without_feasible_total=15",
        'route_records_without_feasible={"nishishinjuku_lane_change": 4, "sample_tl": 11}',
        'route_tl_records_without_feasible={"nishishinjuku_lane_change|off": 2, "nishishinjuku_lane_change|on": 2, "sample_tl|off": 1, "sample_tl|on": 10}',
        "sample_normal_records_without_feasible=0",
        "sample_tl_on_no_feasible_records=10/10",
        "sample_tl_off_no_feasible_records=1/10",
        "nishishinjuku_lane_change_no_feasible_records=4/20",
        "sample_normal_no_feasible_records=0/20",
    ]:
        assert needle in text


def test_fallback_feasibility_reason_attribution() -> None:
    text = ATTRIBUTION_DOC.read_text(encoding="utf-8")

    for needle in [
        "record_union_reason_counts={\"['dp_lane_crossing', 'dp_red_light']\": 2, \"['dp_lane_crossing']\": 5, \"['dp_red_light']\": 8}",
        "record_all_candidate_reason_counts={\"['dp_lane_crossing']\": 5, \"['dp_red_light']\": 10}",
        'candidate_reason_counts_in_no_feasible_records={"dp_lane_crossing": 25, "dp_red_light": 40}',
        "candidate_reason_signature_counts_in_no_feasible_records={\"['dp_lane_crossing', 'dp_red_light']\": 5, \"['dp_lane_crossing']\": 20, \"['dp_red_light']\": 35}",
        "primary_failure_class=sample_tl_traffic_light_on_all_candidates_dp_red_light",
        "secondary_failure_class=lane_crossing_all_candidate_no_feasible_tail",
        "sample_tl_on_all_candidate_blocker=dp_red_light",
        "sample_tl_off_all_candidate_blocker=dp_lane_crossing",
        "nishishinjuku_lane_change_all_candidate_blocker=dp_lane_crossing",
    ]:
        assert needle in text


def test_fallback_feasibility_red_light_separation() -> None:
    text = ATTRIBUTION_DOC.read_text(encoding="utf-8")

    for needle in [
        '"sample_tl|on": {"max": 50.0, "mean": 41.2625, "min": 20.5}',
        '"sample_tl|off": {"max": 0.0, "mean": 0.0, "min": 0.0}',
        '"nishishinjuku_lane_change|on": {"max": 0.0, "mean": 0.0, "min": 0.0}',
        "`sample_tl|on`: 10/10 records have no feasible candidate",
        "`sample_tl|off`: 1/10 records has no feasible candidate",
        "`nishishinjuku_lane_change`: 4/20 records have no feasible candidate",
        "`sample_normal`: 0/20 records without a feasible candidate",
    ]:
        assert needle in text


def test_fallback_feasibility_attribution_boundaries_and_next_gate() -> None:
    text = ATTRIBUTION_DOC.read_text(encoding="utf-8")

    for needle in [
        "attribution_only=True",
        "fixed_source_artifact_only=True",
        "replay_executed=False",
        "candidate_generation_executed=False",
        "camp_training_executed=False",
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
        "source_summary_sha256=c39fa6278431e08ee16b7b45f6645e43fa46f9951981c1fff8fa1809778aea07",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fallback_feasibility_remediation_plan_only",
    ]:
        assert needle in text

    for forbidden in [
        "replay_executed=True",
        "candidate_generation_executed=True",
        "camp_training_executed=True",
        "dp_modified=True",
        "reference_blend_enabled=True",
        "guidance_enabled=True",
        "postprocess_postselection_enabled=True",
        "selector_promotion_executed=True",
        "atom_promotion_executed=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in text
