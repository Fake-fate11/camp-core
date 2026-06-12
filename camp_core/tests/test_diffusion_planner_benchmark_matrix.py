from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scripts.integrations.run_diffusion_planner_camp_benchmark_matrix import (
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
        camp_lane_corridor_buffer=1.0,
        camp_feasibility_source="dp_reward",
        camp_fallback_mode="learned",
        camp_min_progress_ratio=0.8,
        camp_reward_horizon_steps=30,
        camp_collect_closed_loop_outcomes=True,
        camp_outcome_horizon_steps=30,
        camp_outcome_progress_weight=1.0,
        camp_outcome_collision_penalty=100.0,
        camp_outcome_near_miss_penalty=10.0,
        camp_outcome_lane_penalty=20.0,
        camp_outcome_red_light_penalty=30.0,
        camp_outcome_jerk_penalty=0.25,
        camp_outcome_lateral_acceleration_penalty=1.0,
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
    assert "--camp_fallback_atom_scales" in static_cmd
    assert "--camp_fallback_static_weights" in static_cmd

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
    assert "--camp_fallback_atom_scales" not in top1_cmd
