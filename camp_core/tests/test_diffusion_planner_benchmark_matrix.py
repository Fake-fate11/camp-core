from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.integrations.run_diffusion_planner_camp_benchmark_matrix import (
    _compare_command,
    _validate_args,
    _variant_command,
)


def _make_args() -> SimpleNamespace:
    return SimpleNamespace(
        diffusion_repo=Path("F:/diffusion_planner"),
        map_path=None,
        model_path=Path("F:/diffusion_planner/diffusion_planner.pth"),
        model_args=Path("F:/diffusion_planner/diffusion_planner.param.json"),
        config=Path("F:/diffusion_planner/scenario_generation/configs/replay_default.json"),
        device="cuda",
        advance_mode="perfect",
        near_miss_threshold_m=2.0,
        steps=200,
        reward_config=Path("F:/camp_core-main/configs/integrations/dp_camp_reward_eval.json"),
        camp_atom_scales=Path("F:/camp_core-main/models/atom_scales.json"),
        camp_static_weights=Path("F:/camp_core-main/models/offline_weights.npy"),
        camp_theta_checkpoint=Path("F:/camp_core-main/models/theta.npz"),
        camp_fallback_atom_scales=Path(
            "F:/camp_core-main/models/fallback_scales.json"
        ),
        camp_fallback_static_weights=Path(
            "F:/camp_core-main/models/fallback_weights.npy"
        ),
        num_candidates=8,
        candidate_noise_scale=1.0,
        camp_log_raw_candidate_prefix_steps=0,
        camp_splice_shadow_rule=False,
        camp_splice_shadow_anchor_steps=10,
        camp_splice_shadow_blend_steps=40,
        camp_splice_shadow_heading_mode="donor_offset",
        camp_splice_shadow_progress_loss_budget_m=1.0,
        camp_splice_shadow_smoothness_loss_budget=0.5,
        candidate_reference_blend_steps=None,
        camp_lane_corridor_buffer=1.0,
        camp_feasibility_source="dp_reward",
        camp_fallback_mode="learned",
        camp_min_progress_ratio=0.8,
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
        camp_underprogress_progress_loss_budget_m=1.5,
        camp_underprogress_h3_distance_loss_budget_m=0.1,
        camp_underprogress_lateral_limit_mps2=2.0,
        camp_reward_horizon_steps=30,
        camp_collect_closed_loop_outcomes=False,
        camp_outcome_horizon_steps=30,
        camp_outcome_progress_weight=1.0,
        camp_outcome_collision_penalty=100.0,
        camp_outcome_near_miss_penalty=10.0,
        camp_outcome_lane_penalty=20.0,
        camp_outcome_red_light_penalty=30.0,
        camp_outcome_jerk_penalty=0.25,
        camp_outcome_lateral_acceleration_penalty=1.0,
        variants=("top1", "uniform", "static", "theta"),
        output_root=Path("F:/out/matrix"),
        scenario_bucket_manifest=None,
        require_strict_pairing=False,
    )


def test_variant_command_threads_fallback_mode_into_camp_variants() -> None:
    args = _make_args()
    static_cmd = _variant_command(
        variant="static",
        output_dir=Path("F:/out/static"),
        route=Path("F:/routes/route.pkl"),
        seed=11,
        max_npcs=4,
        spawn_probability=0.2,
        traffic_lights="on",
        args=args,
    )
    assert "--camp_fallback_mode" in static_cmd
    idx = static_cmd.index("--camp_fallback_mode")
    assert static_cmd[idx + 1] == "learned"
    assert "--camp_min_candidate0_progress_ratio" not in static_cmd
    assert "--camp_min_candidate0_route_progress_ratio" not in static_cmd
    assert "--camp_shadow_route_progress" not in static_cmd
    assert "--camp_shadow_obstacle_clearance" not in static_cmd
    assert "--camp_shadow_obstacle_clearance_exact_obb" not in static_cmd
    assert "--camp_min_candidate0_step_reach_ratio" not in static_cmd
    assert "--camp_candidate0_step_reach_preserve_feasible" not in static_cmd
    assert "--candidate_reference_blend_steps" not in static_cmd
    assert "--camp_lexicographic_progress_epsilon_m" not in static_cmd
    assert "--camp_perfect_tracker_command_postselection" not in static_cmd
    assert "--camp_fallback_atom_scales" in static_cmd
    assert "--camp_fallback_static_weights" in static_cmd
    assert static_cmd[static_cmd.index("--advance_mode") + 1] == "perfect"

    top1_cmd = _variant_command(
        variant="top1",
        output_dir=Path("F:/out/top1"),
        route=Path("F:/routes/route.pkl"),
        seed=11,
        max_npcs=4,
        spawn_probability=0.2,
        traffic_lights="on",
        args=args,
    )
    assert "--camp_fallback_mode" not in top1_cmd
    assert "--camp_min_candidate0_progress_ratio" not in top1_cmd
    assert "--camp_min_candidate0_route_progress_ratio" not in top1_cmd
    assert "--camp_shadow_route_progress" not in top1_cmd
    assert "--camp_shadow_obstacle_clearance" not in top1_cmd
    assert "--camp_shadow_obstacle_clearance_exact_obb" not in top1_cmd
    assert "--camp_min_candidate0_step_reach_ratio" not in top1_cmd
    assert "--camp_candidate0_step_reach_preserve_feasible" not in top1_cmd
    assert "--candidate_reference_blend_steps" not in top1_cmd
    assert "--camp_lexicographic_progress_epsilon_m" not in top1_cmd
    assert "--camp_perfect_tracker_command_postselection" not in top1_cmd
    assert "--camp_underprogress_relaxation" not in top1_cmd
    assert "--camp_fallback_atom_scales" not in top1_cmd


@pytest.mark.parametrize(
    ("attr", "value", "flag"),
    [
        ("camp_log_raw_candidate_prefix_steps", 10, "camp_log_raw_candidate_prefix_steps"),
        ("camp_splice_shadow_rule", True, "camp_splice_shadow_rule"),
        ("candidate_reference_blend_steps", 5, "candidate_reference_blend_steps"),
        ("camp_min_candidate0_progress_ratio", 0.95, "camp_min_candidate0_progress_ratio"),
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
        ("camp_min_candidate0_step_reach_ratio", 0.99, "camp_min_candidate0_step_reach_ratio"),
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
    ],
)
def test_validate_args_rejects_non_atom_options(
    attr: str,
    value: object,
    flag: str,
) -> None:
    args = _make_args()
    setattr(args, attr, value)

    with pytest.raises(ValueError, match=flag):
        _validate_args(args)


def test_compare_command_threads_bucket_manifest_and_strict_pairing() -> None:
    args = _make_args()
    args.scenario_bucket_manifest = Path(
        "F:/camp_core-main/configs/integrations/buckets.json"
    )
    args.require_strict_pairing = True
    runs = [
        ("top1", Path("F:/out/matrix/route/seed_1/top1")),
        ("static", Path("F:/out/matrix/route/seed_1/static")),
    ]

    cmd = _compare_command(runs, args)

    manifest_idx = cmd.index("--scenario_bucket_manifest")
    assert cmd[manifest_idx + 1] == str(args.scenario_bucket_manifest)
    assert "--require_strict_pairing" in cmd
    assert "--output_json" in cmd
    output_idx = cmd.index("--output_json")
    assert cmd[output_idx + 1] == str(
        args.output_root / "benchmark_comparison.json"
    )
