from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.integrations.run_diffusion_planner_camp_replay import (
    _validate_paper_faithful_boundary,
)


def _make_args() -> SimpleNamespace:
    return SimpleNamespace(
        candidate_noise_strategy="iid",
        candidate_reference_blend_steps=None,
        candidate_guidance_config=None,
        candidate_guidance_scale=None,
        camp_microbenchmark_snapshot_dir=None,
        camp_log_raw_candidate_prefix_steps=0,
        camp_observable_state_logging=False,
        camp_red_route_vector_logging=False,
        camp_progress_support_logging=False,
        camp_lane_hard_violation_support_logging=False,
        camp_progress_lane_hard_context_logging=False,
        camp_turn_logit_payload_logging=False,
        camp_non_turn_logit_interaction_payload_logging=False,
        camp_external_context_payload_logging=False,
        camp_temporal_consistency_payload_logging=False,
        camp_candidate_set_consensus_payload_logging=False,
        camp_min_candidate0_progress_ratio=None,
        camp_min_candidate0_route_progress_ratio=None,
        camp_shadow_route_progress=False,
        camp_shadow_obstacle_clearance=False,
        camp_shadow_obstacle_clearance_exact_obb=False,
        camp_min_candidate0_step_reach_ratio=None,
        camp_candidate0_step_reach_preserve_feasible=False,
        camp_lexicographic_progress_epsilon_m=None,
        camp_lexicographic_red_epsilon=0.0,
        camp_lexicographic_jerk_epsilon=0.0,
        camp_lexicographic_lateral_epsilon=0.0,
        camp_perfect_tracker_command_postselection=False,
        camp_traffic_light_hybrid_postselection="off",
        camp_underprogress_relaxation=False,
        camp_collect_closed_loop_outcomes=False,
        camp_splice_shadow_rule=False,
    )


def test_replay_paper_boundary_accepts_default_off_options() -> None:
    _validate_paper_faithful_boundary(_make_args())


@pytest.mark.parametrize(
    ("attr", "value", "flag"),
    [
        ("candidate_noise_strategy", "antithetic", "candidate_noise_strategy"),
        ("candidate_reference_blend_steps", 5, "candidate_reference_blend_steps"),
        ("candidate_guidance_config", Path("guidance.json"), "candidate_guidance_config"),
        ("candidate_guidance_scale", 2.0, "candidate_guidance_scale"),
        (
            "camp_microbenchmark_snapshot_dir",
            Path("snapshots"),
            "camp_microbenchmark_snapshot_dir",
        ),
        (
            "camp_log_raw_candidate_prefix_steps",
            10,
            "camp_log_raw_candidate_prefix_steps",
        ),
        ("camp_observable_state_logging", True, "camp_observable_state_logging"),
        ("camp_red_route_vector_logging", True, "camp_red_route_vector_logging"),
        ("camp_progress_support_logging", True, "camp_progress_support_logging"),
        (
            "camp_lane_hard_violation_support_logging",
            True,
            "camp_lane_hard_violation_support_logging",
        ),
        (
            "camp_progress_lane_hard_context_logging",
            True,
            "camp_progress_lane_hard_context_logging",
        ),
        ("camp_turn_logit_payload_logging", True, "camp_turn_logit_payload_logging"),
        (
            "camp_non_turn_logit_interaction_payload_logging",
            True,
            "camp_non_turn_logit_interaction_payload_logging",
        ),
        (
            "camp_external_context_payload_logging",
            True,
            "camp_external_context_payload_logging",
        ),
        (
            "camp_temporal_consistency_payload_logging",
            True,
            "camp_temporal_consistency_payload_logging",
        ),
        (
            "camp_candidate_set_consensus_payload_logging",
            True,
            "camp_candidate_set_consensus_payload_logging",
        ),
        (
            "camp_min_candidate0_progress_ratio",
            0.95,
            "camp_min_candidate0_progress_ratio",
        ),
        (
            "camp_min_candidate0_route_progress_ratio",
            0.98,
            "camp_min_candidate0_route_progress_ratio",
        ),
        ("camp_shadow_route_progress", True, "camp_shadow_route_progress"),
        ("camp_shadow_obstacle_clearance", True, "camp_shadow_obstacle_clearance"),
        (
            "camp_shadow_obstacle_clearance_exact_obb",
            True,
            "camp_shadow_obstacle_clearance_exact_obb",
        ),
        (
            "camp_min_candidate0_step_reach_ratio",
            0.99,
            "camp_min_candidate0_step_reach_ratio",
        ),
        (
            "camp_candidate0_step_reach_preserve_feasible",
            True,
            "camp_candidate0_step_reach_preserve_feasible",
        ),
        (
            "camp_lexicographic_progress_epsilon_m",
            2.0,
            "camp_lexicographic_progress_epsilon_m",
        ),
        (
            "camp_perfect_tracker_command_postselection",
            True,
            "camp_perfect_tracker_command_postselection",
        ),
        (
            "camp_traffic_light_hybrid_postselection",
            "step_h10_guard_005",
            "camp_traffic_light_hybrid_postselection",
        ),
        ("camp_underprogress_relaxation", True, "camp_underprogress_relaxation"),
        ("camp_collect_closed_loop_outcomes", True, "camp_collect_closed_loop_outcomes"),
        ("camp_splice_shadow_rule", True, "camp_splice_shadow_rule"),
    ],
)
def test_replay_paper_boundary_rejects_non_atom_options(
    attr: str,
    value: object,
    flag: str,
) -> None:
    args = _make_args()
    setattr(args, attr, value)

    with pytest.raises(ValueError, match=flag):
        _validate_paper_faithful_boundary(args)
