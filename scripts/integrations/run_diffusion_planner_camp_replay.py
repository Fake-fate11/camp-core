#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    DP_SCENE_FEATURE_NAMES,
    CAMPSelectionResult,
    CAMPSelector,
    atom_schema_for_dimension,
    build_context_from_scene,
    compute_candidate_closed_loop_outcomes,
    compute_dp_prior_comfort_excess_costs,
    compute_dp_prior_deviation_costs,
    compute_lateral_comfort_shadow_costs,
    compute_perfect_tracker_command_diagnostics,
    compute_perfect_tracker_open_loop_rollout_diagnostics,
    compute_red_stopping_margin_costs,
    extract_dp_scene_features,
    generate_candidate_trajectories,
    install_lanelet2_projection_fallback,
    load_dp_camp_atom_scales,
    red_route_points_from_scene,
    select_perfect_tracker_command_dominating_candidate,
    summarize_replay_artifacts,
)


PERFECT_TRACKER_OPEN_LOOP_HORIZONS = (3, 5, 10)


def _parse_step_list(value: str) -> tuple[int, ...]:
    steps = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not steps:
        raise argparse.ArgumentTypeError("step list must not be empty")
    if any(step < 0 for step in steps):
        raise argparse.ArgumentTypeError("snapshot steps must be nonnegative")
    if len(set(steps)) != len(steps):
        raise argparse.ArgumentTypeError("snapshot steps must be unique")
    return steps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run tier4/Diffusion-Planner route replay with CAMP selecting "
            "one ego trajectory from a stochastic candidate pool."
        )
    )
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--map_path", type=str, default=None)
    parser.add_argument("--route", type=Path, required=True)
    parser.add_argument("--model_path", type=Path, required=True)
    parser.add_argument(
        "--model_args",
        type=Path,
        default=None,
        help=(
            "Optional Diffusion Planner parameter JSON. Use this for official "
            "artifacts such as diffusion_planner.param.json; otherwise the "
            "upstream loader expects args.json next to the checkpoint."
        ),
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max_npcs", type=int, default=None)
    parser.add_argument("--spawn_probability", type=float, default=None)
    parser.add_argument(
        "--advance_mode",
        choices=("config", "perfect", "mpc", "teleport"),
        default="config",
        help="Override SpawnConfig.advance_mode for an auditable tracker choice.",
    )
    parser.add_argument(
        "--traffic_lights",
        choices=("config", "on", "off"),
        default="config",
        help="Override SpawnConfig.enable_traffic_lights for matched experiments.",
    )
    parser.add_argument(
        "--reward_config",
        type=Path,
        default=None,
        help=(
            "Optional full GRPO/reward JSON. When provided, the runner calls "
            "the upstream replay reward scorer in memory without dumping NPZs."
        ),
    )

    weights = parser.add_mutually_exclusive_group(required=False)
    weights.add_argument(
        "--camp_checkpoint",
        type=Path,
        help="CAMP-Select .pt checkpoint containing offline_weights.",
    )
    weights.add_argument(
        "--camp_static_weights",
        type=Path,
        help="Standalone offline_weights.npy.",
    )
    parser.add_argument("--camp_atom_scales", type=Path, default=None)
    parser.add_argument("--camp_fallback_atom_scales", type=Path, default=None)
    parser.add_argument("--camp_fallback_static_weights", type=Path, default=None)
    parser.add_argument(
        "--camp_selector_mode",
        choices=("top1", "uniform", "static", "linear"),
        default="static",
        help=(
            "top1 runs upstream Diffusion Planner unchanged; uniform generates "
            "K candidates and scores CAMP atoms with equal weights; static uses "
            "offline_weights; linear uses Theta from --camp_checkpoint and "
            "per-step Diffusion Planner scene features."
        ),
    )
    parser.add_argument(
        "--camp_fallback_mode",
        choices=("uniform", "learned"),
        default="uniform",
        help=(
            "Fallback policy when all candidates are infeasible. uniform keeps "
            "the legacy average-atom fallback; learned reuses selector scores."
        ),
    )
    parser.add_argument("--camp_atom_clip", type=float, default=10.0)
    parser.add_argument("--camp_safety_radius", type=float, default=2.0)
    parser.add_argument("--camp_clearance_margin", type=float, default=1.0)
    parser.add_argument("--camp_lane_corridor_buffer", type=float, default=1.0)
    parser.add_argument(
        "--camp_feasibility_source",
        choices=("context", "dp_reward"),
        default="context",
        help=(
            "Use legacy CAMP route/speed gates or authoritative Diffusion Planner "
            "candidate reward gates before CAMP scoring."
        ),
    )
    parser.add_argument(
        "--camp_min_progress_ratio",
        type=float,
        default=0.8,
        help=(
            "For dp_reward feasibility, retain safe candidates whose progress is "
            "at least this fraction of the best safe candidate."
        ),
    )
    parser.add_argument(
        "--camp_min_candidate0_progress_ratio",
        type=float,
        default=None,
        help=(
            "For dp_reward feasibility, optionally require each safe candidate "
            "to retain at least this fraction of candidate 0 progress. This is "
            "a candidate0-relative deployment guard and does not affect CAMP "
            "atom scores or weights."
        ),
    )
    parser.add_argument(
        "--camp_min_candidate0_route_progress_ratio",
        type=float,
        default=None,
        help=(
            "For candidate selection, optionally require each candidate to "
            "retain at least this fraction of candidate 0 route-centerline "
            "progress over the current horizon. This guard is computed before "
            "CAMP scoring and does not affect atom scores or weights."
        ),
    )
    parser.add_argument(
        "--camp_min_candidate0_step_reach_ratio",
        type=float,
        default=None,
        help=(
            "For perfect-tracking replay, optionally require each candidate's "
            "first reference point to be at least this fraction of candidate "
            "0 reach. This directly preserves the target speed used by the "
            "perfect tracker and does not affect CAMP atom scores or weights."
        ),
    )
    parser.add_argument(
        "--camp_candidate0_step_reach_preserve_feasible",
        action="store_true",
        help=(
            "When --camp_min_candidate0_step_reach_ratio is enabled, relax the "
            "step-reach guard for a tick if applying it would remove every "
            "candidate that was feasible before the guard. This keeps the guard "
            "from creating new all-infeasible fallback ticks and does not affect "
            "CAMP atom scores or weights."
        ),
    )
    parser.add_argument(
        "--camp_lexicographic_progress_epsilon_m",
        type=float,
        default=None,
        help=(
            "Enable a nonempty finite-candidate preselection that first keeps "
            "candidates within this many meters of the best feasible DP progress."
        ),
    )
    parser.add_argument(
        "--camp_lexicographic_red_epsilon",
        type=float,
        default=0.0,
        help="Planned-red cost tolerance for lexicographic preselection.",
    )
    parser.add_argument(
        "--camp_lexicographic_jerk_epsilon",
        type=float,
        default=0.0,
        help="DP-prior jerk-excess tolerance for lexicographic preselection.",
    )
    parser.add_argument(
        "--camp_lexicographic_lateral_epsilon",
        type=float,
        default=0.0,
        help="Horizon lateral-acceleration tolerance for lexicographic preselection.",
    )
    parser.add_argument(
        "--camp_perfect_tracker_command_postselection",
        action="store_true",
        help=(
            "After the normal CAMP selection, choose a base-feasible candidate "
            "only when it preserves target speed, DP progress, and planned-red "
            "cost while strictly improving PerfectTracker command comfort."
        ),
    )
    parser.add_argument(
        "--camp_underprogress_relaxation",
        action="store_true",
        help=(
            "Default-off safety relaxation for red-light approach states. "
            "Only candidates blocked solely by dp_underprogress can be "
            "admitted, and hard feasibility reasons remain hard."
        ),
    )
    parser.add_argument(
        "--camp_underprogress_progress_loss_budget_m",
        type=float,
        default=1.5,
        help="Maximum DP progress loss for --camp_underprogress_relaxation.",
    )
    parser.add_argument(
        "--camp_underprogress_h3_distance_loss_budget_m",
        type=float,
        default=0.1,
        help="Maximum H3 PerfectTracker distance loss for underprogress relaxation.",
    )
    parser.add_argument(
        "--camp_underprogress_lateral_limit_mps2",
        type=float,
        default=2.0,
        help="Absolute H3 max lateral acceleration limit for underprogress relaxation.",
    )
    parser.add_argument(
        "--camp_reward_horizon_steps",
        type=int,
        default=30,
        help=(
            "Near-term trajectory steps used for DP candidate reward gates. "
            "Full selected trajectories are still evaluated separately."
        ),
    )
    parser.add_argument(
        "--camp_collect_closed_loop_outcomes",
        action="store_true",
        help=(
            "Log short-horizon candidate outcome labels computed from perfect "
            "tracking, predicted NPC futures, route progress, red lights, and "
            "comfort. Used for v5 closed_loop_outcome training."
        ),
    )
    parser.add_argument("--camp_outcome_horizon_steps", type=int, default=30)
    parser.add_argument("--camp_outcome_progress_weight", type=float, default=1.0)
    parser.add_argument("--camp_outcome_collision_penalty", type=float, default=100.0)
    parser.add_argument("--camp_outcome_near_miss_penalty", type=float, default=10.0)
    parser.add_argument("--camp_outcome_lane_penalty", type=float, default=20.0)
    parser.add_argument("--camp_outcome_red_light_penalty", type=float, default=30.0)
    parser.add_argument("--camp_outcome_jerk_penalty", type=float, default=0.25)
    parser.add_argument(
        "--camp_outcome_lateral_acceleration_penalty",
        type=float,
        default=1.0,
    )
    parser.add_argument("--num_candidates", type=int, default=8)
    parser.add_argument("--candidate_noise_scale", type=float, default=1.0)
    parser.add_argument(
        "--candidate_noise_strategy",
        choices=("iid", "antithetic"),
        default="iid",
        help=(
            "Default iid keeps historical latent sampling. Antithetic pairs "
            "stochastic latents as +z/-z in the same batched forward pass and "
            "changes only the finite candidate set."
        ),
    )
    parser.add_argument(
        "--candidate_reference_blend_steps",
        type=int,
        default=None,
        help=(
            "Blend stochastic candidates from candidate 0 at t=0 to their "
            "original trajectories after this many fixed steps."
        ),
    )
    parser.add_argument(
        "--candidate_guidance_config",
        type=Path,
        default=None,
        help=(
            "Default-off diagnostic: install official Diffusion Planner "
            "GuidanceComposer for candidate generation. This changes only the "
            "finite candidate set and must not be used for formal seeds before "
            "passing the predeclared gate."
        ),
    )
    parser.add_argument(
        "--candidate_guidance_scale",
        type=float,
        default=None,
        help=(
            "Optional decoder guidance scale override used only with "
            "--candidate_guidance_config."
        ),
    )
    parser.add_argument(
        "--camp_microbenchmark_snapshot_dir",
        type=Path,
        default=None,
        help=(
            "Default-off diagnostic export of current-tick DP/CAMP inputs. "
            "Snapshot runs are not latency evidence."
        ),
    )
    parser.add_argument(
        "--camp_microbenchmark_snapshot_steps",
        type=_parse_step_list,
        default=(10, 20, 30, 39),
        help="Comma-separated completed selection steps to export.",
    )
    parser.add_argument("--near_miss_threshold_m", type=float, default=2.0)
    return parser.parse_args()


def _validate_args(args: argparse.Namespace) -> None:
    if args.camp_selector_mode != "top1" and args.camp_atom_scales is None:
        raise ValueError(
            "--camp_atom_scales is required for uniform/static/linear CAMP modes."
        )
    if args.camp_selector_mode == "static" and (
        args.camp_checkpoint is None and args.camp_static_weights is None
    ):
        raise ValueError(
            "static CAMP selection requires --camp_checkpoint or "
            "--camp_static_weights."
        )
    if args.camp_selector_mode == "linear" and args.camp_checkpoint is None:
        raise ValueError("linear CAMP selection requires --camp_checkpoint.")
    if (args.camp_fallback_atom_scales is None) != (
        args.camp_fallback_static_weights is None
    ):
        raise ValueError(
            "--camp_fallback_atom_scales and --camp_fallback_static_weights "
            "must be provided together."
        )
    if (
        args.camp_fallback_static_weights is not None
        and args.camp_fallback_mode != "learned"
    ):
        raise ValueError(
            "Dedicated fallback artifacts require --camp_fallback_mode learned."
        )
    if args.camp_selector_mode != "top1" and args.num_candidates < 2:
        raise ValueError("--num_candidates must be >= 2 for CAMP candidate selection.")
    if args.candidate_noise_scale <= 0:
        raise ValueError("--candidate_noise_scale must be > 0.")
    if (
        args.candidate_reference_blend_steps is not None
        and args.candidate_reference_blend_steps < 1
    ):
        raise ValueError("--candidate_reference_blend_steps must be >= 1.")
    if args.candidate_guidance_scale is not None:
        if args.candidate_guidance_config is None:
            raise ValueError(
                "--candidate_guidance_scale requires --candidate_guidance_config."
            )
        if not np.isfinite(args.candidate_guidance_scale):
            raise ValueError("--candidate_guidance_scale must be finite.")
    if args.camp_lane_corridor_buffer < 0:
        raise ValueError("--camp_lane_corridor_buffer must be non-negative.")
    if not 0.0 <= args.camp_min_progress_ratio <= 1.0:
        raise ValueError("--camp_min_progress_ratio must be in [0, 1].")
    if args.camp_min_candidate0_progress_ratio is not None and not (
        0.0 <= args.camp_min_candidate0_progress_ratio <= 1.0
    ):
        raise ValueError("--camp_min_candidate0_progress_ratio must be in [0, 1].")
    if args.camp_min_candidate0_route_progress_ratio is not None and not (
        0.0 <= args.camp_min_candidate0_route_progress_ratio <= 1.0
    ):
        raise ValueError(
            "--camp_min_candidate0_route_progress_ratio must be in [0, 1]."
        )
    if args.camp_min_candidate0_step_reach_ratio is not None and not (
        0.0 <= args.camp_min_candidate0_step_reach_ratio <= 1.0
    ):
        raise ValueError("--camp_min_candidate0_step_reach_ratio must be in [0, 1].")
    lexicographic_epsilons = (
        args.camp_lexicographic_progress_epsilon_m,
        args.camp_lexicographic_red_epsilon,
        args.camp_lexicographic_jerk_epsilon,
        args.camp_lexicographic_lateral_epsilon,
    )
    if any(
        value is not None and (not np.isfinite(value) or value < 0.0)
        for value in lexicographic_epsilons
    ):
        raise ValueError(
            "CAMP lexicographic epsilons must be finite and nonnegative."
        )
    if (
        args.camp_lexicographic_progress_epsilon_m is not None
        and args.camp_feasibility_source != "dp_reward"
    ):
        raise ValueError(
            "CAMP lexicographic preselection requires "
            "--camp_feasibility_source dp_reward."
        )
    if (
        args.camp_perfect_tracker_command_postselection
        and args.camp_feasibility_source != "dp_reward"
    ):
        raise ValueError(
            "PerfectTracker command postselection requires "
            "--camp_feasibility_source dp_reward."
        )
    underprogress_budgets = (
        args.camp_underprogress_progress_loss_budget_m,
        args.camp_underprogress_h3_distance_loss_budget_m,
        args.camp_underprogress_lateral_limit_mps2,
    )
    if any(not np.isfinite(value) or value < 0.0 for value in underprogress_budgets):
        raise ValueError(
            "CAMP underprogress relaxation budgets must be finite and nonnegative."
        )
    if (
        args.camp_underprogress_relaxation
        and args.camp_feasibility_source != "dp_reward"
    ):
        raise ValueError(
            "CAMP underprogress relaxation requires "
            "--camp_feasibility_source dp_reward."
        )
    if (
        args.camp_underprogress_relaxation
        and args.camp_lexicographic_progress_epsilon_m is not None
    ):
        raise ValueError(
            "CAMP underprogress relaxation cannot be combined with "
            "lexicographic preselection in the same run."
        )
    if (
        args.camp_underprogress_relaxation
        and args.camp_perfect_tracker_command_postselection
    ):
        raise ValueError(
            "CAMP underprogress relaxation cannot be combined with "
            "PerfectTracker command postselection in the same run."
        )
    if args.camp_reward_horizon_steps < 2:
        raise ValueError("--camp_reward_horizon_steps must be >= 2.")
    if args.camp_outcome_horizon_steps < 2:
        raise ValueError("--camp_outcome_horizon_steps must be >= 2.")
    if args.camp_feasibility_source == "dp_reward" and args.reward_config is None:
        raise ValueError(
            "--camp_feasibility_source dp_reward requires --reward_config."
        )
    if args.near_miss_threshold_m < 0:
        raise ValueError("--near_miss_threshold_m must be non-negative.")
    if args.reward_config is not None and not args.reward_config.is_file():
        raise FileNotFoundError(f"Missing reward config: {args.reward_config}")
    if (
        args.camp_microbenchmark_snapshot_dir is not None
        and args.camp_selector_mode == "top1"
    ):
        raise ValueError(
            "CAMP microbenchmark snapshots require a CAMP selector mode."
        )
    if (
        args.steps is not None
        and args.camp_microbenchmark_snapshot_dir is not None
        and max(args.camp_microbenchmark_snapshot_steps) >= args.steps
    ):
        raise ValueError(
            "Every CAMP microbenchmark snapshot step must be smaller than "
            "--steps."
        )


def _build_selector(args: argparse.Namespace) -> CAMPSelector | None:
    if args.camp_selector_mode == "top1":
        return None
    if args.camp_selector_mode == "uniform":
        atom_scales = load_dp_camp_atom_scales(args.camp_atom_scales)
        fallback_atom_scales = (
            None
            if args.camp_fallback_atom_scales is None
            else load_dp_camp_atom_scales(args.camp_fallback_atom_scales)
        )
        fallback_static_weights = (
            None
            if args.camp_fallback_static_weights is None
            else np.load(args.camp_fallback_static_weights)
        )
        return CAMPSelector(
            atom_scales,
            static_weights=np.ones_like(atom_scales, dtype=np.float64),
            mode="static",
            fallback_mode=args.camp_fallback_mode,
            fallback_atom_scales=fallback_atom_scales,
            fallback_static_weights=fallback_static_weights,
            atom_clip=args.camp_atom_clip,
        )
    return CAMPSelector.from_files(
        atom_scales_path=args.camp_atom_scales,
        checkpoint_path=args.camp_checkpoint,
        static_weights_path=args.camp_static_weights,
        fallback_atom_scales_path=args.camp_fallback_atom_scales,
        fallback_static_weights_path=args.camp_fallback_static_weights,
        mode=args.camp_selector_mode,
        fallback_mode=args.camp_fallback_mode,
        atom_clip=args.camp_atom_clip,
    )


def _install_diffusion_repo(diffusion_repo: Path) -> None:
    repo = diffusion_repo.resolve()
    required = [
        repo / "scenario_generation" / "replay.py",
        repo / "diffusion_planner" / "diffusion_planner" / "model",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"{repo} is not a tier4/Diffusion-Planner checkout; missing: {missing}"
        )
    for path in (repo, repo / "diffusion_planner"):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


def _load_model(model_path: Path, model_args_path: Path | None, device: str):
    if model_args_path is None:
        import scenario_generation.replay as replay

        return replay.load_model(model_path, device)

    import torch
    from diffusion_planner.model.diffusion_planner import Diffusion_Planner
    from diffusion_planner.utils.config import Config

    args = Config(str(model_args_path))
    model = Diffusion_Planner(args)
    checkpoint = torch.load(str(model_path), map_location=device, weights_only=False)
    state = checkpoint.get("model", checkpoint)
    state = {key.replace("module.", ""): value for key, value in state.items()}
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    return model, args


def _configure_candidate_guidance(
    model: Any,
    *,
    guidance_config_path: Path | None,
    guidance_scale: float | None,
) -> dict[str, Any]:
    if guidance_config_path is None:
        return {
            "enabled": False,
            "policy": "disabled_for_camp_candidate_generation",
            "config_path": None,
            "config_sha256": None,
            "functions": [],
            "guidance_scale": None,
        }

    if not guidance_config_path.is_file():
        raise FileNotFoundError(
            f"candidate guidance config not found: {guidance_config_path}"
        )

    from diffusion_planner.model.guidance.composer import GuidanceComposer
    from diffusion_planner.model.guidance.config import GuidanceSetConfig

    set_config = GuidanceSetConfig.from_file(str(guidance_config_path))
    functions = []
    for fn in set_config.functions:
        functions.append(
            {
                "name": str(fn.name),
                "enabled": bool(fn.enabled),
                "scale": float(fn.scale),
                "params": dict(fn.params),
            }
        )
    active = [fn for fn in functions if fn["enabled"]]
    if not active:
        raise ValueError(
            "--candidate_guidance_config must contain at least one enabled "
            "guidance function."
        )

    model.decoder._guidance_fn = GuidanceComposer(set_config)
    configured_global_scale = float(getattr(set_config, "global_scale", 0.0))
    if not np.isfinite(configured_global_scale):
        raise ValueError("--candidate_guidance_config global_scale must be finite.")
    if guidance_scale is not None:
        if not np.isfinite(guidance_scale):
            raise ValueError("--candidate_guidance_scale must be finite.")
        model.decoder._guidance_scale = float(guidance_scale)
        guidance_scale_source = "cli_override"
    else:
        model.decoder._guidance_scale = configured_global_scale
        guidance_scale_source = "config_global_scale"
    effective_scale = float(getattr(model.decoder, "_guidance_scale"))
    if not np.isfinite(effective_scale):
        raise ValueError("effective candidate guidance scale must be finite.")
    return {
        "enabled": True,
        "policy": "preserve_official_dp_guidance_for_candidate_generation",
        "config_path": str(guidance_config_path),
        "config_sha256": _sha256_file(guidance_config_path),
        "functions": functions,
        "active_function_names": [fn["name"] for fn in active],
        "guidance_scale": effective_scale,
        "guidance_scale_source": guidance_scale_source,
        "global_scale": configured_global_scale,
        "composer": "diffusion_planner.model.guidance.composer.GuidanceComposer",
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ego_frame_xy(world_xy: np.ndarray, ego_xy: np.ndarray, ego_heading: float) -> np.ndarray:
    relative = np.asarray(world_xy, dtype=np.float64) - ego_xy.reshape(1, 2)
    c = math.cos(ego_heading)
    s = math.sin(ego_heading)
    rotation = np.array([[c, s], [-s, c]], dtype=np.float64)
    return relative @ rotation.T


def _candidate_obstacles(
    scene: Any,
    ego_agent_id: str,
    neighbor_predictions: np.ndarray,
    is_static_npc,
) -> np.ndarray:
    """Match tensor_converter's distance-sorted neighbor slot order.

    Returns ``[K, M, T, 6]`` as x, y, heading, length, width, wheelbase in
    the ego frame. Older CAMP code only consumed x/y; the extra columns enable
    oriented bounding-box collision checks without changing DP internals.
    """
    ego = scene.get_agent(ego_agent_id)
    ego_xy = np.asarray(ego.current_position, dtype=np.float64)
    ego_heading = float(ego.current_heading)

    neighbors = [agent for agent in scene.agents if agent.id != ego_agent_id]
    neighbors.sort(
        key=lambda agent: float(
            np.linalg.norm(np.asarray(agent.current_position) - ego_xy)
        )
    )

    count = min(len(neighbors), neighbor_predictions.shape[1])
    obstacles = np.zeros(
        (neighbor_predictions.shape[0], count, neighbor_predictions.shape[2], 6),
        dtype=np.float64,
    )
    obstacles[:, :, :, :2] = neighbor_predictions[:, :count, :, :2]
    if neighbor_predictions.shape[-1] >= 4:
        obstacles[:, :, :, 2] = np.arctan2(
            neighbor_predictions[:, :count, :, 3],
            neighbor_predictions[:, :count, :, 2],
        )
    for neighbor_idx, agent in enumerate(neighbors[:count]):
        obstacles[:, neighbor_idx, :, 3] = float(getattr(agent, "length", 4.5))
        obstacles[:, neighbor_idx, :, 4] = float(getattr(agent, "width", 1.9))
        obstacles[:, neighbor_idx, :, 5] = float(
            getattr(agent, "wheelbase", 0.65 * getattr(agent, "length", 4.5))
        )
        if not is_static_npc(agent.id):
            continue
        static_xy = _ego_frame_xy(
            np.asarray(agent.current_position, dtype=np.float64).reshape(1, 2),
            ego_xy,
            ego_heading,
        )[0]
        obstacles[:, neighbor_idx, :, 0] = static_xy[0]
        obstacles[:, neighbor_idx, :, 1] = static_xy[1]
        obstacles[:, neighbor_idx, :, 2] = (
            float(agent.current_heading) - ego_heading
        )
    return obstacles


def _route_centerline_world(builder: Any, route: Any) -> np.ndarray:
    points: list[np.ndarray] = []
    for lanelet_id in route.route_lanelet_ids or []:
        cached = builder._cache.get(lanelet_id)
        if cached is None:
            continue
        centerline = np.asarray(cached.raw_centerline, dtype=np.float64)[:, :2]
        if centerline.shape[0] < 2:
            continue
        if points and np.linalg.norm(points[-1][-1] - centerline[0]) < 1e-3:
            centerline = centerline[1:]
        if centerline.size:
            points.append(centerline)
    if not points:
        return np.zeros((0, 2), dtype=np.float64)
    return np.concatenate(points, axis=0)


def _candidate_route_progress(
    candidates: np.ndarray,
    route_centerline: np.ndarray,
) -> np.ndarray | None:
    centerline = np.asarray(route_centerline, dtype=np.float64)
    if centerline.ndim != 2 or centerline.shape[0] < 2 or centerline.shape[1] < 2:
        return None
    candidate_xy = np.asarray(candidates, dtype=np.float64)[..., :2]
    if candidate_xy.ndim != 3 or candidate_xy.shape[1] < 1:
        return None

    starts = centerline[:-1, :2]
    ends = centerline[1:, :2]
    segments = ends - starts
    lengths = np.linalg.norm(segments, axis=1)
    valid = lengths > 1e-6
    if not np.any(valid):
        return None
    starts = starts[valid]
    segments = segments[valid]
    lengths = lengths[valid]
    cumulative = np.concatenate([[0.0], np.cumsum(lengths)])

    flat = candidate_xy.reshape(-1, 2)
    point_arcs = np.zeros(flat.shape[0], dtype=np.float64)
    for point_idx, point in enumerate(flat):
        rel = point.reshape(1, 2) - starts
        t = np.sum(rel * segments, axis=1) / np.maximum(lengths * lengths, 1e-12)
        t = np.clip(t, 0.0, 1.0)
        projections = starts + t.reshape(-1, 1) * segments
        distances = np.linalg.norm(projections - point.reshape(1, 2), axis=1)
        best = int(np.argmin(distances))
        point_arcs[point_idx] = cumulative[best] + t[best] * lengths[best]
    return np.max(point_arcs.reshape(candidate_xy.shape[:2]), axis=1)


def _apply_candidate0_route_progress_guard(
    feasible: np.ndarray | None,
    reasons: tuple[tuple[str, ...], ...] | None,
    candidate_route_progress: np.ndarray | None,
    min_candidate0_route_progress_ratio: float | None,
) -> tuple[np.ndarray | None, tuple[tuple[str, ...], ...] | None]:
    if (
        min_candidate0_route_progress_ratio is None
        or candidate_route_progress is None
    ):
        return feasible, reasons
    progress = np.asarray(candidate_route_progress, dtype=np.float64).reshape(-1)
    if progress.size == 0:
        return feasible, reasons
    if feasible is None:
        feasible_arr = np.ones(progress.shape[0], dtype=bool)
    else:
        feasible_arr = np.asarray(feasible, dtype=bool).reshape(-1).copy()
    if feasible_arr.shape != progress.shape:
        raise ValueError(
            "candidate_route_progress must match feasible candidate count."
        )
    reason_rows = (
        [[] for _ in range(progress.shape[0])]
        if reasons is None
        else [list(row) for row in reasons]
    )
    candidate0_progress = float(progress[0])
    if candidate0_progress <= 0.0 or not np.isfinite(candidate0_progress):
        return feasible_arr, tuple(tuple(row) for row in reason_rows)
    threshold = candidate0_progress * float(min_candidate0_route_progress_ratio)
    for idx, value in enumerate(progress):
        if idx == 0 or not feasible_arr[idx]:
            continue
        if not np.isfinite(value) or float(value) < threshold:
            feasible_arr[idx] = False
            reason_rows[idx].append("route_candidate0_underprogress")
    return feasible_arr, tuple(tuple(row) for row in reason_rows)


def _candidate_step_reach(candidates: np.ndarray) -> np.ndarray:
    candidate_xy = np.asarray(candidates, dtype=np.float64)[..., :2]
    if candidate_xy.ndim != 3 or candidate_xy.shape[1] < 1:
        raise ValueError("candidates must have shape [K, T, >=2].")
    reach = np.linalg.norm(candidate_xy[:, 0, :], axis=1)
    return np.nan_to_num(reach, nan=0.0, posinf=0.0, neginf=0.0)


def _current_perfect_tracker_state(agent: Any) -> tuple[float, float]:
    heading = float(agent.current_heading)
    forward = np.array([math.cos(heading), math.sin(heading)], dtype=np.float64)
    velocity = np.asarray(agent.current_velocity, dtype=np.float64).reshape(-1)
    acceleration = np.asarray(agent.acceleration, dtype=np.float64).reshape(-1)
    if velocity.size < 2 or acceleration.size < 2:
        raise ValueError("Agent velocity and acceleration must contain xy values.")
    speed = max(float(np.dot(velocity[:2], forward)), 0.0)
    longitudinal_acceleration = float(np.dot(acceleration[:2], forward))
    if not np.isfinite(speed) or not np.isfinite(longitudinal_acceleration):
        raise ValueError("Perfect-tracker state must be finite.")
    return speed, longitudinal_acceleration


def _current_acceleration_ego_xy(agent: Any, dt: float) -> np.ndarray:
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("PerfectTracker dt must be finite and positive.")
    heading = float(agent.current_heading)
    acceleration = None
    velocities = np.asarray(
        getattr(agent, "past_velocities", []),
        dtype=np.float64,
    )
    if (
        velocities.ndim == 2
        and velocities.shape[0] >= 2
        and velocities.shape[1] >= 2
        and np.all(np.isfinite(velocities[-2:, :2]))
    ):
        acceleration = (velocities[-1, :2] - velocities[-2, :2]) / float(dt)
    if acceleration is None:
        acceleration = np.asarray(
            agent.acceleration,
            dtype=np.float64,
        ).reshape(-1)
    if acceleration.size < 2 or not np.all(np.isfinite(acceleration[:2])):
        raise ValueError("Agent acceleration must contain finite xy values.")
    forward = np.array([math.cos(heading), math.sin(heading)], dtype=np.float64)
    lateral = np.array([-math.sin(heading), math.cos(heading)], dtype=np.float64)
    return np.array(
        [
            float(np.dot(acceleration[:2], forward)),
            float(np.dot(acceleration[:2], lateral)),
        ],
        dtype=np.float64,
    )


def _apply_candidate0_step_reach_guard(
    feasible: np.ndarray | None,
    reasons: tuple[tuple[str, ...], ...] | None,
    candidate_step_reach: np.ndarray,
    min_candidate0_step_reach_ratio: float | None,
    preserve_any_feasible: bool = False,
) -> tuple[np.ndarray | None, tuple[tuple[str, ...], ...] | None, bool]:
    if min_candidate0_step_reach_ratio is None:
        return feasible, reasons, False
    reach = np.asarray(candidate_step_reach, dtype=np.float64).reshape(-1)
    if reach.size == 0:
        return feasible, reasons, False
    if feasible is None:
        feasible_arr = np.ones(reach.shape[0], dtype=bool)
    else:
        feasible_arr = np.asarray(feasible, dtype=bool).reshape(-1).copy()
    if feasible_arr.shape != reach.shape:
        raise ValueError("candidate_step_reach must match feasible candidate count.")
    original_feasible_arr = feasible_arr.copy()
    reason_rows = (
        [[] for _ in range(reach.shape[0])]
        if reasons is None
        else [list(row) for row in reasons]
    )
    original_reason_rows = [list(row) for row in reason_rows]
    candidate0_reach = float(reach[0])
    if candidate0_reach <= 0.0 or not np.isfinite(candidate0_reach):
        return feasible_arr, tuple(tuple(row) for row in reason_rows), False
    threshold = candidate0_reach * float(min_candidate0_step_reach_ratio)
    for idx, value in enumerate(reach):
        if idx == 0 or not feasible_arr[idx]:
            continue
        if not np.isfinite(value) or float(value) < threshold:
            feasible_arr[idx] = False
            reason_rows[idx].append("candidate0_step_reach_underprogress")
    relaxed = bool(
        preserve_any_feasible and original_feasible_arr.any() and not feasible_arr.any()
    )
    if relaxed:
        return (
            original_feasible_arr,
            tuple(tuple(row) for row in original_reason_rows),
            True,
        )
    return feasible_arr, tuple(tuple(row) for row in reason_rows), False


def _apply_lexicographic_admissible_filter(
    feasible: np.ndarray | None,
    reasons: tuple[tuple[str, ...], ...] | None,
    *,
    candidate_progress: np.ndarray,
    candidate_planned_red_light_cost: np.ndarray,
    candidate_dp_prior_jerk_excess_cost: np.ndarray,
    candidate_horizon_lateral_acceleration_cost: np.ndarray,
    progress_epsilon_m: float | None,
    red_epsilon: float,
    jerk_epsilon: float,
    lateral_epsilon: float,
) -> tuple[
    np.ndarray | None,
    tuple[tuple[str, ...], ...] | None,
    dict[str, int] | None,
]:
    if progress_epsilon_m is None:
        return feasible, reasons, None
    epsilons = (
        progress_epsilon_m,
        red_epsilon,
        jerk_epsilon,
        lateral_epsilon,
    )
    if any(not np.isfinite(value) or value < 0.0 for value in epsilons):
        raise ValueError(
            "Lexicographic epsilons must be finite and nonnegative."
        )
    arrays = {
        "progress": np.asarray(candidate_progress, dtype=np.float64).reshape(-1),
        "planned_red": np.asarray(
            candidate_planned_red_light_cost, dtype=np.float64
        ).reshape(-1),
        "jerk": np.asarray(
            candidate_dp_prior_jerk_excess_cost, dtype=np.float64
        ).reshape(-1),
        "lateral": np.asarray(
            candidate_horizon_lateral_acceleration_cost, dtype=np.float64
        ).reshape(-1),
    }
    candidate_count = arrays["progress"].size
    if candidate_count == 0:
        raise ValueError("Lexicographic preselection requires candidates.")
    if any(values.shape != (candidate_count,) for values in arrays.values()):
        raise ValueError(
            "Lexicographic preselection fields must have equal candidate count."
        )
    if any(not np.all(np.isfinite(values)) for values in arrays.values()):
        raise ValueError("Lexicographic preselection fields must be finite.")
    if np.any(arrays["planned_red"] < 0.0):
        raise ValueError("Lexicographic planned-red costs must be nonnegative.")
    if np.any(arrays["jerk"] < 0.0):
        raise ValueError("Lexicographic jerk costs must be nonnegative.")
    if np.any(arrays["lateral"] < 0.0):
        raise ValueError("Lexicographic lateral costs must be nonnegative.")
    if feasible is None:
        feasible_arr = np.ones(candidate_count, dtype=bool)
    else:
        feasible_arr = np.asarray(feasible, dtype=bool).reshape(-1).copy()
    if feasible_arr.shape != (candidate_count,):
        raise ValueError(
            "Lexicographic fields must match feasible candidate count."
        )
    reason_rows = (
        [[] for _ in range(candidate_count)]
        if reasons is None
        else [list(row) for row in reasons]
    )
    if len(reason_rows) != candidate_count:
        raise ValueError(
            "Lexicographic reasons must match feasible candidate count."
        )
    stage_counts = {"base": int(feasible_arr.sum())}
    if not feasible_arr.any():
        stage_counts.update({"progress": 0, "planned_red": 0, "jerk": 0, "lateral": 0})
        return feasible_arr, tuple(tuple(row) for row in reason_rows), stage_counts

    stages = (
        (
            "progress",
            arrays["progress"],
            float(np.max(arrays["progress"][feasible_arr]))
            - float(progress_epsilon_m),
            "min",
            "lexicographic_progress",
        ),
        (
            "planned_red",
            arrays["planned_red"],
            None,
            "max",
            "lexicographic_planned_red",
        ),
        (
            "jerk",
            arrays["jerk"],
            None,
            "max",
            "lexicographic_jerk",
        ),
        (
            "lateral",
            arrays["lateral"],
            None,
            "max",
            "lexicographic_lateral",
        ),
    )
    tolerances = {
        "planned_red": float(red_epsilon),
        "jerk": float(jerk_epsilon),
        "lateral": float(lateral_epsilon),
    }
    for stage_name, values, threshold, comparison, reason in stages:
        active = feasible_arr.copy()
        if threshold is None:
            threshold = float(np.min(values[active])) + tolerances[stage_name]
        if comparison == "min":
            keep = values >= threshold - 1e-12
        else:
            keep = values <= threshold + 1e-12
        removed = active & ~keep
        feasible_arr[removed] = False
        for idx in np.flatnonzero(removed):
            reason_rows[int(idx)].append(reason)
        if not feasible_arr.any():
            raise RuntimeError(
                f"Lexicographic stage {stage_name} unexpectedly removed all candidates."
            )
        stage_counts[stage_name] = int(feasible_arr.sum())
    return feasible_arr, tuple(tuple(row) for row in reason_rows), stage_counts


def _apply_underprogress_relaxation_override(
    selection: CAMPSelectionResult,
    candidates: np.ndarray,
    *,
    candidate_progress: np.ndarray,
    candidate_union_red_cost: np.ndarray,
    candidate_red_stopping_margin_cost: np.ndarray,
    perfect_tracker_open_loop: dict[Any, Any],
    progress_loss_budget_m: float,
    h3_distance_loss_budget_m: float,
    lateral_limit_mps2: float,
) -> tuple[CAMPSelectionResult, dict[str, Any]]:
    selected = int(selection.selected_index)
    feasible = np.asarray(selection.feasible_mask, dtype=bool).reshape(-1)
    candidate_count = feasible.size
    reasons = [tuple(row) for row in selection.infeasibility_reasons]
    if len(reasons) != candidate_count:
        raise ValueError("Underprogress relaxation reasons must match candidates.")
    progress = np.asarray(candidate_progress, dtype=np.float64).reshape(-1)
    union_red = np.asarray(candidate_union_red_cost, dtype=np.float64).reshape(-1)
    stopping_margin = np.asarray(
        candidate_red_stopping_margin_cost,
        dtype=np.float64,
    ).reshape(-1)
    horizons = perfect_tracker_open_loop.get("horizons")
    h3 = None
    if isinstance(horizons, dict):
        h3 = horizons.get("3")
        if h3 is None:
            h3 = horizons.get(3)
    if h3 is None:
        h3 = perfect_tracker_open_loop.get("3")
    if h3 is None:
        h3 = perfect_tracker_open_loop.get(3)
    if not isinstance(h3, dict):
        raise ValueError("Underprogress relaxation requires H3 rollout metrics.")
    distance = np.asarray(h3["distance_m"], dtype=np.float64).reshape(-1)
    h3_lateral = np.asarray(
        h3["max_lateral_acceleration_mps2"],
        dtype=np.float64,
    ).reshape(-1)
    arrays = (progress, union_red, stopping_margin, distance, h3_lateral)
    if any(array.shape != (candidate_count,) for array in arrays):
        raise ValueError("Underprogress relaxation fields must match candidates.")
    if any(not np.all(np.isfinite(array)) for array in arrays):
        raise ValueError("Underprogress relaxation fields must be finite.")
    if np.any(union_red < 0.0) or np.any(stopping_margin < 0.0):
        raise ValueError("Underprogress relaxation costs must be nonnegative.")

    stats: dict[str, Any] = {
        "enabled": True,
        "changed": False,
        "baseline_selected_index": selected,
        "selected_index": selected,
        "candidate_count": candidate_count,
        "budget": {
            "progress_loss_m": float(progress_loss_budget_m),
            "h3_distance_loss_m": float(h3_distance_loss_budget_m),
            "h3_max_lateral_limit_mps2": float(lateral_limit_mps2),
            "requires_stopping_margin_nonworse": True,
            "ignored_reason": "dp_underprogress",
        },
        "reason": "not_evaluated",
    }
    if selection.used_fallback or not feasible.any():
        stats["reason"] = "fallback_or_no_base_feasible_candidate"
        return selection, stats
    if union_red[selected] <= 0.0:
        stats["reason"] = "baseline_union_red_zero"
        return selection, stats

    lower_base_feasible = feasible & (union_red < union_red[selected])
    lower_base_feasible[selected] = False
    if lower_base_feasible.any():
        stats["reason"] = "lower_red_base_feasible_candidate_exists"
        stats["lower_red_base_feasible_candidates"] = int(
            lower_base_feasible.sum()
        )
        return selection, stats

    only_underprogress = np.asarray(
        [row == ("dp_underprogress",) for row in reasons],
        dtype=bool,
    )
    admissible = (
        only_underprogress
        & (union_red < union_red[selected])
        & (progress >= progress[selected] - float(progress_loss_budget_m))
        & (distance >= distance[selected] - float(h3_distance_loss_budget_m))
        & (stopping_margin <= stopping_margin[selected] + 1e-12)
        & (h3_lateral <= float(lateral_limit_mps2))
    )
    admissible[selected] = False
    indices = np.flatnonzero(admissible)
    stats["admissible_candidates"] = int(indices.size)
    if not indices.size:
        stats["reason"] = "no_underprogress_relaxed_candidate"
        return selection, stats

    chosen = min(
        indices.tolist(),
        key=lambda idx: (
            float(union_red[idx]),
            float(stopping_margin[idx]),
            float(selection.scores[idx]),
            int(idx),
        ),
    )
    effective_feasible = feasible.copy()
    effective_feasible[indices] = True
    effective_reasons = [list(row) for row in reasons]
    for idx in indices.tolist():
        effective_reasons[idx] = []
    effective_selection_scores = np.asarray(
        selection.selection_scores,
        dtype=np.float64,
    ).copy()
    effective_selection_scores[indices] = selection.scores[indices]
    stats.update(
        {
            "changed": True,
            "reason": "underprogress_relaxed_lower_red_candidate",
            "selected_index": int(chosen),
            "admissible_indices": [int(idx) for idx in indices.tolist()],
            "delta": {
                "union_red": float(union_red[chosen] - union_red[selected]),
                "progress_m": float(progress[chosen] - progress[selected]),
                "h3_distance_m": float(distance[chosen] - distance[selected]),
                "red_stopping_margin": float(
                    stopping_margin[chosen] - stopping_margin[selected]
                ),
                "h3_max_lateral_mps2": float(
                    h3_lateral[chosen] - h3_lateral[selected]
                ),
            },
        }
    )
    return (
        replace(
            selection,
            selected_index=int(chosen),
            selected_trajectory=candidates[chosen].copy(),
            feasible_mask=effective_feasible,
            infeasibility_reasons=tuple(
                tuple(row) for row in effective_reasons
            ),
            selection_scores=effective_selection_scores,
            used_fallback=False,
        ),
        stats,
    )


def _evaluation_state(scene: Any, ego_id: str) -> dict[str, Any]:
    ego = scene.get_agent(ego_id)
    route_lanes = np.asarray(ego.route_lanes, dtype=np.float64)
    if route_lanes.ndim == 4 and route_lanes.shape[0] == 1:
        route_lanes = route_lanes[0]
    red_points: list[list[float]] = []
    if route_lanes.ndim == 3 and route_lanes.shape[-1] > 10:
        red_mask = route_lanes[:, :, 10] > 0.5
        valid = np.linalg.norm(route_lanes[:, :, :2], axis=-1) > 0.1
        for point in route_lanes[red_mask & valid]:
            red_points.append(
                [
                    float(point[0]),
                    float(point[1]),
                    float(point[2]),
                    float(point[3]),
                ]
            )
    return {
        "step": None,
        "x": float(ego.current_position[0]),
        "y": float(ego.current_position[1]),
        "heading": float(ego.current_heading),
        "red_route_points": red_points,
    }


def _perfect_tracker_candidate_preprocessing(spawn_config: Any) -> dict[str, Any]:
    enabled = bool(getattr(spawn_config, "sg_smooth_enabled", False))
    return {
        "reference_implementation": (
            "rlvr.grpo_sft_trainer._smooth_trajectory"
        ),
        "shadow_implementation": (
            "scripts.integrations.run_diffusion_planner_camp_replay."
            "_prepare_perfect_tracker_reference_candidates"
        ),
        "application_stage": (
            "replay_after_predict_before_advance_scene_mpc"
        ),
        "savgol_enabled": enabled,
        "savgol_window": (
            int(getattr(spawn_config, "sg_filter_window"))
            if enabled
            else None
        ),
        "savgol_order": (
            int(getattr(spawn_config, "sg_filter_order"))
            if enabled
            else None
        ),
    }


def _prepare_perfect_tracker_reference_candidates(
    candidates: np.ndarray,
    spawn_config: Any,
) -> np.ndarray:
    """Vectorize DP's per-trajectory Savitzky-Golay preprocessing."""
    trajectories = np.asarray(candidates)
    if not bool(getattr(spawn_config, "sg_smooth_enabled", False)):
        return trajectories
    from scipy.signal import savgol_filter

    horizon_steps = int(trajectories.shape[1])
    window = min(int(spawn_config.sg_filter_window), horizon_steps)
    if window % 2 == 0:
        window -= 1
    order = int(spawn_config.sg_filter_order)
    if window < order + 2:
        return trajectories
    smoothed = np.copy(trajectories)
    smoothed[:, :, :4] = savgol_filter(
        trajectories[:, :, :4],
        window,
        order,
        axis=1,
    )
    heading_norm = np.linalg.norm(smoothed[:, :, 2:4], axis=2)
    heading_norm = np.clip(heading_norm, 1e-6, None)
    smoothed[:, :, 2:4] /= heading_norm[:, :, np.newaxis]
    if smoothed.shape != trajectories.shape or not np.all(np.isfinite(smoothed)):
        raise RuntimeError(
            "Diffusion Planner trajectory smoothing returned invalid candidates."
        )
    return smoothed


def _append_metric_record(
    *,
    replay_module: Any,
    tensor_converter_module: Any,
    scene: Any,
    map_cache: Any,
    model_args: Any,
    prediction: np.ndarray,
    device: str,
    reward_config: Any,
    spawn_config: Any,
    records: list[dict[str, Any]],
) -> None:
    if reward_config is None:
        return
    if map_cache is None:
        raise RuntimeError("Reward scoring requires Diffusion Planner map_cache.")
    data = tensor_converter_module.dump_step_npz(
        scene,
        map_cache,
        future_len=int(model_args.future_len),
        predicted_neighbor_num=int(model_args.predicted_neighbor_num),
    )
    scored_prediction = np.asarray(prediction).copy()
    if bool(getattr(spawn_config, "sg_smooth_enabled", False)):
        scored_prediction = replay_module._sg_smooth_trajectory(
            scored_prediction,
            int(spawn_config.sg_filter_window),
            int(spawn_config.sg_filter_order),
        )
    records.append(
        replay_module._score_step(
            data,
            len(records),
            device,
            reward_config,
            spawn_config,
            prediction=scored_prediction,
        )
    )


def _score_candidate_batch(
    *,
    replay_module: Any,
    tensor_converter_module: Any,
    scene: Any,
    map_cache: Any,
    model_args: Any,
    candidates: np.ndarray,
    device: str,
    reward_config: Any,
    spawn_config: Any,
    reward_horizon_steps: int,
) -> tuple[list[dict[str, Any]], np.ndarray, float]:
    if map_cache is None:
        raise RuntimeError("Candidate reward scoring requires Diffusion Planner map_cache.")

    import torch
    from rlvr.reward import compute_red_light_score_batch, compute_reward_batch

    npz_data = tensor_converter_module.dump_step_npz(
        scene,
        map_cache,
        future_len=int(model_args.future_len),
        predicted_neighbor_num=int(model_args.predicted_neighbor_num),
    )

    def _to_tensor(array: np.ndarray) -> torch.Tensor:
        tensor = torch.from_numpy(np.asarray(array)).float().to(device)
        return tensor.unsqueeze(0) if tensor.dim() == 3 else tensor

    reward_data: dict[str, torch.Tensor] = {}
    keys = (
        "lanes",
        "route_lanes",
        "line_strings",
        "ego_shape",
        "neighbor_agents_future",
        "neighbor_agents_past",
        "goal_pose",
    )
    for key in keys:
        if key not in npz_data:
            continue
        array = np.asarray(npz_data[key])
        if key == "goal_pose" and array.shape[-1] == 3:
            yaw = array[..., 2]
            array = np.stack(
                (array[..., 0], array[..., 1], np.cos(yaw), np.sin(yaw)),
                axis=-1,
            )
        reward_data[key] = _to_tensor(array)

    scored_candidates = np.asarray(candidates, dtype=np.float32).copy()
    if bool(getattr(spawn_config, "sg_smooth_enabled", False)):
        scored_candidates = np.stack(
            [
                replay_module._sg_smooth_trajectory(
                    candidate,
                    int(spawn_config.sg_filter_window),
                    int(spawn_config.sg_filter_order),
                )
                for candidate in scored_candidates
            ]
        )
    full_trajectories = torch.from_numpy(scored_candidates).float().to(device)
    reward_trajectories = full_trajectories[:, :reward_horizon_steps]
    reward_breakdowns = [
        asdict(breakdown)
        for breakdown in compute_reward_batch(
            reward_trajectories,
            reward_data,
            reward_config,
        )
    ]
    full_red_start = time.perf_counter()
    full_red_scores = compute_red_light_score_batch(
        full_trajectories,
        reward_data,
        reward_config,
    )
    full_red_cost = np.maximum(
        -full_red_scores.detach().cpu().numpy().astype(np.float64),
        0.0,
    )
    full_red_latency_ms = (time.perf_counter() - full_red_start) * 1000.0
    return reward_breakdowns, full_red_cost, full_red_latency_ms


def _candidate_feasibility_from_rewards(
    rewards: list[dict[str, Any]],
    min_progress_ratio: float,
    min_candidate0_progress_ratio: float | None = None,
) -> tuple[np.ndarray, tuple[tuple[str, ...], ...]]:
    feasible = np.ones(len(rewards), dtype=bool)
    reasons: list[list[str]] = [[] for _ in rewards]

    for idx, reward in enumerate(rewards):
        checks = (
            ("dp_collision", reward.get("collision_step") is not None),
            ("dp_road_border", bool(reward.get("rb_crossing", False))),
            ("dp_lane_crossing", bool(reward.get("lane_crossing", False))),
            ("dp_static_collision", bool(reward.get("static_crossing", False))),
            ("dp_kinematic", bool(reward.get("kinematic_violated", False))),
            ("dp_red_light", float(reward.get("red_light", 0.0)) < -0.5),
        )
        for reason, failed in checks:
            if failed:
                reasons[idx].append(reason)
        feasible[idx] = not reasons[idx]

    safe_indices = np.flatnonzero(feasible)
    if safe_indices.size:
        safe_progress = np.asarray(
            [float(rewards[idx].get("progress", 0.0)) for idx in safe_indices],
            dtype=np.float64,
        )
        best_progress = float(np.max(safe_progress))
        if best_progress > 0.0:
            minimum_progress = best_progress * float(min_progress_ratio)
            for idx in safe_indices:
                if float(rewards[idx].get("progress", 0.0)) < minimum_progress:
                    feasible[idx] = False
                    reasons[idx].append("dp_underprogress")
        if min_candidate0_progress_ratio is not None and rewards:
            candidate0_progress = float(rewards[0].get("progress", 0.0))
            if candidate0_progress > 0.0:
                minimum_candidate0_progress = (
                    candidate0_progress * float(min_candidate0_progress_ratio)
                )
                for idx in safe_indices:
                    if idx == 0:
                        continue
                    if (
                        float(rewards[idx].get("progress", 0.0))
                        < minimum_candidate0_progress
                    ):
                        feasible[idx] = False
                        reasons[idx].append("dp_candidate0_underprogress")

    return feasible, tuple(tuple(row) for row in reasons)


def _install_top1_observer(
    replay_module: Any,
    tensor_converter_module: Any,
    *,
    reward_config: Any,
    spawn_config: Any,
) -> tuple[Any, list[dict[str, Any]], list[dict[str, Any]]]:
    original_predict = replay_module._predict_batch
    metric_records: list[dict[str, Any]] = []
    evaluation_records: list[dict[str, Any]] = []

    def observed_predict(
        model,
        model_args,
        scene,
        agent_ids,
        device,
        map_cache=None,
        return_turn_indicators=False,
        inference_delay=0,
        turn_indicator_keep_bias=0.25,
    ):
        base = original_predict(
            model,
            model_args,
            scene,
            agent_ids,
            device,
            map_cache=map_cache,
            return_turn_indicators=return_turn_indicators,
            inference_delay=inference_delay,
            turn_indicator_keep_bias=turn_indicator_keep_bias,
        )
        ego_id = scene.ego_agent_id
        if ego_id not in agent_ids:
            return base
        predictions = base[0] if return_turn_indicators else base
        state = _evaluation_state(scene, ego_id)
        state["step"] = len(evaluation_records)
        evaluation_records.append(state)
        _append_metric_record(
            replay_module=replay_module,
            tensor_converter_module=tensor_converter_module,
            scene=scene,
            map_cache=map_cache,
            model_args=model_args,
            prediction=predictions[ego_id],
            device=device,
            reward_config=reward_config,
            spawn_config=spawn_config,
            records=metric_records,
        )
        return base

    replay_module._predict_batch = observed_predict
    return original_predict, metric_records, evaluation_records


def _write_microbenchmark_snapshot(
    *,
    output_dir: Path,
    selection_step: int,
    normalized_inputs: dict[str, Any],
    tensor_converter_module: Any,
    scene: Any,
    map_cache: Any,
    model_args: Any,
    candidates: np.ndarray,
    neighbor_predictions: np.ndarray,
    candidate_obstacles: np.ndarray | None,
    context: Any,
    selector: CAMPSelector,
    selection: CAMPSelectionResult,
    scene_features: np.ndarray,
    external_feasible_mask: np.ndarray | None,
    external_infeasibility_reasons: Any,
    candidate_progress: np.ndarray | None,
    candidate_planned_red_light_cost: np.ndarray | None,
    candidate_full_horizon_planned_red_light_cost: np.ndarray | None,
    candidate_red_stopping_margin_cost: np.ndarray,
    candidate_dp_prior_jerk_excess_cost: np.ndarray,
    candidate_generation_contract: dict[str, Any],
    red_route_points: np.ndarray,
    perfect_tracker_current_speed_mps: float,
    perfect_tracker_current_longitudinal_acceleration_mps2: float,
    perfect_tracker_current_acceleration_ego_xy: np.ndarray,
    num_candidates: int,
    noise_scale: float,
    reference_blend_steps: int | None,
    reward_horizon_steps: int,
    outcome_horizon_steps: int,
    spawn_config: Any,
) -> Path:
    """Write a default-off current-tick snapshot for independent profiling."""
    arrays: dict[str, np.ndarray] = {
        "candidates": np.asarray(candidates),
        "neighbor_predictions": np.asarray(neighbor_predictions),
        "candidate_obstacles": (
            np.asarray(candidate_obstacles)
            if candidate_obstacles is not None
            else np.empty((num_candidates, 0, candidates.shape[1], 2))
        ),
        "lane_centerline": np.asarray(context.lane_centerline),
        "static_obstacles": (
            np.asarray(context.static_obstacles)
            if context.static_obstacles is not None
            else np.empty((0, 2))
        ),
        "atom_scales": np.asarray(selector.atom_scales),
        "selection_atoms": np.asarray(selection.atoms),
        "selection_normalized_atoms": np.asarray(selection.normalized_atoms),
        "selection_weights": np.asarray(selection.selection_weights),
        "selection_scores": np.asarray(selection.selection_scores),
        "feasible_mask": np.asarray(selection.feasible_mask),
        "scene_features": np.asarray(scene_features),
        "red_route_points": np.asarray(red_route_points),
        "current_acceleration_ego_xy": np.asarray(
            perfect_tracker_current_acceleration_ego_xy
        ),
        "candidate_red_stopping_margin_cost": np.asarray(
            candidate_red_stopping_margin_cost
        ),
        "candidate_dp_prior_jerk_excess_cost": np.asarray(
            candidate_dp_prior_jerk_excess_cost
        ),
    }
    optional_arrays = {
        "external_feasible_mask": external_feasible_mask,
        "candidate_progress": candidate_progress,
        "candidate_planned_red_light_cost": candidate_planned_red_light_cost,
        "candidate_full_horizon_planned_red_light_cost": (
            candidate_full_horizon_planned_red_light_cost
        ),
    }
    for key, value in optional_arrays.items():
        if value is not None:
            arrays[key] = np.asarray(value)

    model_input_keys = []
    for key, value in normalized_inputs.items():
        if hasattr(value, "detach") and hasattr(value, "cpu"):
            tensor = value.detach().cpu()
            try:
                array = tensor.numpy()
            except TypeError:
                tensor = tensor.float()
                array = tensor.numpy()
            arrays[f"model_input__{key}"] = array
            model_input_keys.append(key)
        elif isinstance(value, np.ndarray):
            arrays[f"model_input__{key}"] = value
            model_input_keys.append(key)

    reward_input_keys = []
    if map_cache is not None:
        reward_inputs = tensor_converter_module.dump_step_npz(
            scene,
            map_cache,
            future_len=int(model_args.future_len),
            predicted_neighbor_num=int(model_args.predicted_neighbor_num),
        )
        for key, value in reward_inputs.items():
            if isinstance(value, np.ndarray):
                arrays[f"reward_input__{key}"] = value
                reward_input_keys.append(key)

    metadata = {
        "format_version": 1,
        "selection_step": int(selection_step),
        "num_candidates": int(num_candidates),
        "candidate_horizon_steps": int(candidates.shape[1]),
        "candidate_dimension": int(candidates.shape[2]),
        "candidate_noise_scale": float(noise_scale),
        "candidate_reference_blend_steps": reference_blend_steps,
        "candidate_generation_contract": candidate_generation_contract,
        "candidate_generation_seed": int(1729 + selection_step),
        "candidate_generation_seed_scope": (
            "microbenchmark_replay_only_not_original_tick_rng"
        ),
        "reward_horizon_steps": int(reward_horizon_steps),
        "outcome_horizon_steps": int(outcome_horizon_steps),
        "dt": float(context.dt),
        "speed_limit": context.speed_limit,
        "desired_speed": context.desired_speed,
        "lane_half_width": float(context.lane_half_width),
        "lane_corridor_buffer": float(context.lane_corridor_buffer),
        "safety_radius": float(context.safety_radius),
        "clearance_soft_margin": float(context.clearance_soft_margin),
        "map_source": str(context.map_source),
        "atom_clip": float(selector.atom_clip),
        "fallback_mode": str(selector.fallback_mode),
        "used_fallback": bool(selection.used_fallback),
        "selected_index": int(selection.selected_index),
        "infeasibility_reasons": [
            list(reasons) for reasons in selection.infeasibility_reasons
        ],
        "external_infeasibility_reasons": (
            None
            if external_infeasibility_reasons is None
            else [
                list(reasons) for reasons in external_infeasibility_reasons
            ]
        ),
        "current_speed_mps": float(perfect_tracker_current_speed_mps),
        "current_longitudinal_acceleration_mps2": float(
            perfect_tracker_current_longitudinal_acceleration_mps2
        ),
        "perfect_tracker_open_loop_horizons": list(
            PERFECT_TRACKER_OPEN_LOOP_HORIZONS
        ),
        "sg_smooth_enabled": bool(
            getattr(spawn_config, "sg_smooth_enabled", False)
        ),
        "sg_filter_window": int(getattr(spawn_config, "sg_filter_window", 0)),
        "sg_filter_order": int(getattr(spawn_config, "sg_filter_order", 0)),
        "model_input_keys": sorted(model_input_keys),
        "reward_input_keys": sorted(reward_input_keys),
        "capture_has_no_selection_effect": True,
    }
    arrays["metadata_json"] = np.asarray(json.dumps(metadata, sort_keys=True))

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"camp_microbenchmark_step_{selection_step:04d}.npz"
    np.savez_compressed(output_path, **arrays)
    return output_path


def _candidate_generation_contract(
    model_args: Any,
    *,
    num_candidates: int,
    noise_scale: float,
    noise_strategy: str,
    reference_blend_steps: int | None,
    guidance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if noise_strategy not in {"iid", "antithetic"}:
        raise ValueError("noise_strategy must be 'iid' or 'antithetic'.")
    future_len = int(model_args.future_len)
    predicted_neighbor_num = int(model_args.predicted_neighbor_num)
    guidance_payload = guidance or {
        "enabled": False,
        "policy": "disabled_for_camp_candidate_generation",
        "config_path": None,
        "config_sha256": None,
        "functions": [],
        "guidance_scale": None,
    }
    return {
        "schema_version": "dp_candidate_generation_contract_v1",
        "model_type": str(getattr(model_args, "diffusion_model_type", "unknown")),
        "future_len": future_len,
        "predicted_neighbor_num": predicted_neighbor_num,
        "num_candidates": int(num_candidates),
        "latent_shape": [
            int(num_candidates),
            1 + predicted_neighbor_num,
            future_len + 1,
            4,
        ],
        "latent_distribution": "standard_normal_scaled",
        "noise_strategy": noise_strategy,
        "latent_pairing": (
            "+z/-z antithetic pairs after deterministic candidate 0; "
            "one unpaired iid draw if stochastic count is odd"
            if noise_strategy == "antithetic"
            else "independent iid draws after deterministic candidate 0"
        ),
        "noise_scale": float(noise_scale),
        "deterministic_first": True,
        "candidate0_latent": "zeros",
        "random_seed_scope": "process_global_torch_rng",
        "recorded_tick_seed": None,
        "guidance_enabled": bool(guidance_payload.get("enabled", False)),
        "guidance_policy": str(
            guidance_payload.get("policy", "disabled_for_camp_candidate_generation")
        ),
        "guidance": guidance_payload,
        "dpm_solver_steps": 10,
        "dpm_skip_type": "logSNR",
        "reference_blend_steps": reference_blend_steps,
        "changes_candidate_set": True,
        "changes_camp_score": False,
        "changes_diffusion_planner_weights": False,
    }


def _install_camp_predictor(
    replay_module: Any,
    tensor_converter_module: Any,
    selector: CAMPSelector,
    *,
    num_candidates: int,
    noise_scale: float,
    reference_blend_steps: int | None,
    candidate_generation_contract: dict[str, Any],
    safety_radius: float,
    clearance_margin: float,
    lane_corridor_buffer: float,
    feasibility_source: str,
    min_progress_ratio: float,
    min_candidate0_progress_ratio: float | None,
    min_candidate0_route_progress_ratio: float | None,
    min_candidate0_step_reach_ratio: float | None,
    candidate0_step_reach_preserve_feasible: bool,
    lexicographic_progress_epsilon_m: float | None,
    lexicographic_red_epsilon: float,
    lexicographic_jerk_epsilon: float,
    lexicographic_lateral_epsilon: float,
    perfect_tracker_command_postselection: bool,
    underprogress_relaxation: bool,
    underprogress_progress_loss_budget_m: float,
    underprogress_h3_distance_loss_budget_m: float,
    underprogress_lateral_limit_mps2: float,
    reward_horizon_steps: int,
    collect_closed_loop_outcomes: bool,
    outcome_horizon_steps: int,
    outcome_weights: dict[str, float],
    near_miss_threshold_m: float,
    ego_length: float,
    ego_width: float,
    ego_wheelbase: float,
    reward_config: Any,
    spawn_config: Any,
    route_centerline: np.ndarray,
    microbenchmark_snapshot_dir: Path | None,
    microbenchmark_snapshot_steps: tuple[int, ...],
) -> tuple[
    Any,
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    original_predict = replay_module._predict_batch
    records: list[dict[str, Any]] = []
    metric_records: list[dict[str, Any]] = []
    evaluation_records: list[dict[str, Any]] = []

    def camp_predict(
        model,
        model_args,
        scene,
        agent_ids,
        device,
        map_cache=None,
        return_turn_indicators=False,
        inference_delay=0,
        turn_indicator_keep_bias=0.25,
    ):
        base = original_predict(
            model,
            model_args,
            scene,
            agent_ids,
            device,
            map_cache=map_cache,
            return_turn_indicators=return_turn_indicators,
            inference_delay=inference_delay,
            turn_indicator_keep_bias=turn_indicator_keep_bias,
        )
        if return_turn_indicators:
            predictions, turn_indicators = base
        else:
            predictions = base
            turn_indicators = None

        ego_id = scene.ego_agent_id
        if ego_id not in agent_ids:
            return base

        inputs = tensor_converter_module.to_model_tensors(
            scene,
            ego_id,
            model_args,
            device,
            map_cache=map_cache,
            inference_delay=inference_delay,
        )
        scene_features = extract_dp_scene_features(inputs)
        start = time.perf_counter()
        candidates, neighbor_predictions, turn_logits = generate_candidate_trajectories(
            model,
            model_args,
            inputs,
            num_candidates=num_candidates,
            noise_scale=noise_scale,
            deterministic_first=True,
            reference_blend_steps=reference_blend_steps,
            guidance_policy=(
                "preserve"
                if candidate_generation_contract.get("guidance_enabled")
                else "disabled"
            ),
            noise_strategy=str(candidate_generation_contract["noise_strategy"]),
        )
        candidate_generation_done = time.perf_counter()
        dp_prior_deviation_start = time.perf_counter()
        candidate_dp_prior_deviation_cost = compute_dp_prior_deviation_costs(
            candidates
        )
        dp_prior_deviation_done = time.perf_counter()
        shadow_dp_prior_deviation_latency_ms = (
            dp_prior_deviation_done - dp_prior_deviation_start
        ) * 1000.0
        dp_prior_comfort_start = time.perf_counter()
        (
            candidate_dp_prior_jerk_excess_cost,
            candidate_dp_prior_acceleration_excess_cost,
        ) = compute_dp_prior_comfort_excess_costs(
            candidates,
            float(getattr(scene, "dt", 0.1)),
            horizon_steps=outcome_horizon_steps,
        )
        dp_prior_comfort_horizon_steps = min(
            outcome_horizon_steps,
            int(candidates.shape[1]),
        )
        dp_prior_comfort_done = time.perf_counter()
        shadow_dp_prior_comfort_excess_latency_ms = (
            dp_prior_comfort_done - dp_prior_comfort_start
        ) * 1000.0
        lateral_comfort_start = time.perf_counter()
        (
            candidate_horizon_lateral_acceleration_cost,
            candidate_dp_prior_lateral_acceleration_excess_cost,
            candidate_horizon_yaw_rate_cost,
            candidate_dp_prior_yaw_rate_excess_cost,
        ) = compute_lateral_comfort_shadow_costs(
            candidates,
            float(getattr(scene, "dt", 0.1)),
            horizon_steps=outcome_horizon_steps,
        )
        lateral_comfort_horizon_steps = min(
            outcome_horizon_steps,
            int(candidates.shape[1]),
        )
        lateral_comfort_done = time.perf_counter()
        shadow_lateral_comfort_latency_ms = (
            lateral_comfort_done - lateral_comfort_start
        ) * 1000.0
        context = build_context_from_scene(
            scene,
            ego_id,
            safety_radius=safety_radius,
            clearance_soft_margin=clearance_margin,
            lane_corridor_buffer=lane_corridor_buffer,
        )
        obstacles = _candidate_obstacles(
            scene,
            ego_id,
            neighbor_predictions,
            replay_module.SceneNPCManager.is_static_npc,
        )
        context_and_obstacles_done = time.perf_counter()
        candidate_rewards = None
        candidate_outcomes = None
        candidate_progress = None
        candidate_full_horizon_planned_red_light_cost = None
        candidate_horizon_union_planned_red_light_cost = None
        full_horizon_red_light_latency_ms = 0.0
        candidate_route_progress = None
        candidate_step_reach = _candidate_step_reach(candidates)
        perfect_tracker_command_start = time.perf_counter()
        ego_agent = scene.get_agent(ego_id)
        (
            perfect_tracker_current_speed_mps,
            perfect_tracker_current_longitudinal_acceleration_mps2,
        ) = _current_perfect_tracker_state(ego_agent)
        perfect_tracker_current_acceleration_ego_xy = (
            _current_acceleration_ego_xy(
                ego_agent,
                float(getattr(scene, "dt", 0.1)),
            )
        )
        perfect_tracker_reference_candidates = (
            _prepare_perfect_tracker_reference_candidates(
                candidates,
                spawn_config,
            )
        )
        perfect_tracker_command = compute_perfect_tracker_command_diagnostics(
            perfect_tracker_reference_candidates,
            dt=float(getattr(scene, "dt", 0.1)),
            current_speed_mps=perfect_tracker_current_speed_mps,
            current_longitudinal_acceleration_mps2=(
                perfect_tracker_current_longitudinal_acceleration_mps2
            ),
        )
        perfect_tracker_command_done = time.perf_counter()
        shadow_perfect_tracker_command_latency_ms = (
            perfect_tracker_command_done - perfect_tracker_command_start
        ) * 1000.0
        if candidates.shape[1] < PERFECT_TRACKER_OPEN_LOOP_HORIZONS[-1]:
            raise RuntimeError(
                "PerfectTracker open-loop shadow requires at least "
                f"{PERFECT_TRACKER_OPEN_LOOP_HORIZONS[-1]} candidate steps."
            )
        perfect_tracker_open_loop_start = time.perf_counter()
        perfect_tracker_open_loop = (
            compute_perfect_tracker_open_loop_rollout_diagnostics(
                perfect_tracker_command["postprocessed_reference"][
                    :, : PERFECT_TRACKER_OPEN_LOOP_HORIZONS[-1]
                ],
                postprocessed_tail_reference_xy=perfect_tracker_command[
                    "postprocessed_tail_reference_xy"
                ],
                full_horizon_steps=int(candidates.shape[1]),
                dt=float(getattr(scene, "dt", 0.1)),
                current_speed_mps=perfect_tracker_current_speed_mps,
                current_acceleration_ego_xy=(
                    perfect_tracker_current_acceleration_ego_xy
                ),
                horizons=PERFECT_TRACKER_OPEN_LOOP_HORIZONS,
            )
        )
        perfect_tracker_open_loop_done = time.perf_counter()
        shadow_perfect_tracker_open_loop_latency_ms = (
            perfect_tracker_open_loop_done - perfect_tracker_open_loop_start
        ) * 1000.0
        candidate_step_reach_guard_relaxed = False
        lexicographic_stage_counts = None
        candidate_planned_red_light_cost = None
        red_route_points = red_route_points_from_scene(scene, ego_id)
        external_feasible_mask = None
        external_infeasibility_reasons = None
        if feasibility_source == "dp_reward":
            (
                candidate_rewards,
                candidate_full_horizon_planned_red_light_cost,
                full_horizon_red_light_latency_ms,
            ) = _score_candidate_batch(
                replay_module=replay_module,
                tensor_converter_module=tensor_converter_module,
                scene=scene,
                map_cache=map_cache,
                model_args=model_args,
                candidates=candidates,
                device=device,
                reward_config=reward_config,
                spawn_config=spawn_config,
                reward_horizon_steps=reward_horizon_steps,
            )
            (
                external_feasible_mask,
                external_infeasibility_reasons,
            ) = _candidate_feasibility_from_rewards(
                candidate_rewards,
                min_progress_ratio,
                min_candidate0_progress_ratio,
            )
            candidate_progress = np.asarray(
                [reward["progress"] for reward in candidate_rewards],
                dtype=np.float64,
            )
            candidate_planned_red_light_cost = np.asarray(
                [max(-float(reward.get("red_light", 0.0)), 0.0) for reward in candidate_rewards],
                dtype=np.float64,
            )
            candidate_horizon_union_planned_red_light_cost = np.maximum(
                candidate_planned_red_light_cost,
                candidate_full_horizon_planned_red_light_cost,
            )
        if min_candidate0_step_reach_ratio is not None:
            (
                external_feasible_mask,
                external_infeasibility_reasons,
                candidate_step_reach_guard_relaxed,
            ) = _apply_candidate0_step_reach_guard(
                external_feasible_mask,
                external_infeasibility_reasons,
                candidate_step_reach,
                min_candidate0_step_reach_ratio,
                preserve_any_feasible=candidate0_step_reach_preserve_feasible,
            )
        if min_candidate0_route_progress_ratio is not None:
            route_centerline_ego = _ego_frame_xy(
                route_centerline,
                np.asarray(ego_agent.current_position, dtype=np.float64),
                float(ego_agent.current_heading),
            )
            route_horizon = min(reward_horizon_steps, int(candidates.shape[1]))
            candidate_route_progress = _candidate_route_progress(
                candidates[:, :route_horizon],
                route_centerline_ego,
            )
            (
                external_feasible_mask,
                external_infeasibility_reasons,
            ) = _apply_candidate0_route_progress_guard(
                external_feasible_mask,
                external_infeasibility_reasons,
                candidate_route_progress,
                min_candidate0_route_progress_ratio,
            )
        if lexicographic_progress_epsilon_m is not None:
            if candidate_progress is None or candidate_planned_red_light_cost is None:
                raise RuntimeError(
                    "Lexicographic preselection requires DP reward candidate fields."
                )
            (
                external_feasible_mask,
                external_infeasibility_reasons,
                lexicographic_stage_counts,
            ) = _apply_lexicographic_admissible_filter(
                external_feasible_mask,
                external_infeasibility_reasons,
                candidate_progress=candidate_progress,
                candidate_planned_red_light_cost=(
                    candidate_planned_red_light_cost
                ),
                candidate_dp_prior_jerk_excess_cost=(
                    candidate_dp_prior_jerk_excess_cost
                ),
                candidate_horizon_lateral_acceleration_cost=(
                    candidate_horizon_lateral_acceleration_cost
                ),
                progress_epsilon_m=lexicographic_progress_epsilon_m,
                red_epsilon=lexicographic_red_epsilon,
                jerk_epsilon=lexicographic_jerk_epsilon,
                lateral_epsilon=lexicographic_lateral_epsilon,
            )
        reward_scoring_done = time.perf_counter()
        if collect_closed_loop_outcomes:
            candidate_outcomes = compute_candidate_closed_loop_outcomes(
                candidates,
                context,
                candidate_obstacles=obstacles,
                red_route_points=red_route_points,
                horizon_steps=outcome_horizon_steps,
                near_miss_threshold_m=near_miss_threshold_m,
                ego_length=ego_length,
                ego_width=ego_width,
                ego_wheelbase=ego_wheelbase,
                weights=outcome_weights,
            )
        outcome_collection_done = time.perf_counter()
        red_stopping_margin_start = time.perf_counter()
        candidate_red_stopping_margin_cost = compute_red_stopping_margin_costs(
            candidates,
            red_route_points,
            context.dt,
        )
        red_stopping_margin_done = time.perf_counter()
        shadow_red_stopping_margin_latency_ms = (
            red_stopping_margin_done - red_stopping_margin_start
        ) * 1000.0
        selection = selector.select(
            candidates,
            context,
            scene_embedding=scene_features if selector.mode == "linear" else None,
            candidate_obstacles=obstacles,
            candidate_progress=candidate_progress,
            candidate_planned_red_light_cost=candidate_planned_red_light_cost,
            candidate_red_stopping_margin_cost=candidate_red_stopping_margin_cost,
            candidate_dp_prior_jerk_excess_cost=(
                candidate_dp_prior_jerk_excess_cost
            ),
            external_feasible_mask=external_feasible_mask,
            external_infeasibility_reasons=external_infeasibility_reasons,
            apply_context_feasibility=feasibility_source == "context",
            ego_length=ego_length,
            ego_width=ego_width,
            ego_wheelbase=ego_wheelbase,
        )
        camp_selection_done = time.perf_counter()
        underprogress_relaxation_stats = None
        if underprogress_relaxation:
            if (
                candidate_progress is None
                or candidate_horizon_union_planned_red_light_cost is None
            ):
                raise RuntimeError(
                    "Underprogress relaxation requires DP reward candidate fields."
                )
            (
                selection,
                underprogress_relaxation_stats,
            ) = _apply_underprogress_relaxation_override(
                selection,
                candidates,
                candidate_progress=candidate_progress,
                candidate_union_red_cost=(
                    candidate_horizon_union_planned_red_light_cost
                ),
                candidate_red_stopping_margin_cost=(
                    candidate_red_stopping_margin_cost
                ),
                perfect_tracker_open_loop=perfect_tracker_open_loop,
                progress_loss_budget_m=underprogress_progress_loss_budget_m,
                h3_distance_loss_budget_m=(
                    underprogress_h3_distance_loss_budget_m
                ),
                lateral_limit_mps2=underprogress_lateral_limit_mps2,
            )
        underprogress_relaxation_done = time.perf_counter()
        baseline_selected_index = int(selection.selected_index)
        selected_index = baseline_selected_index
        perfect_tracker_command_postselection_stats = None
        if perfect_tracker_command_postselection:
            if candidate_progress is None or candidate_planned_red_light_cost is None:
                raise RuntimeError(
                    "PerfectTracker command postselection requires DP reward "
                    "candidate fields."
                )
            (
                selected_index,
                perfect_tracker_command_postselection_stats,
            ) = select_perfect_tracker_command_dominating_candidate(
                baseline_selected_index=baseline_selected_index,
                feasible_mask=selection.feasible_mask,
                selection_scores=selection.selection_scores,
                candidate_progress=candidate_progress,
                candidate_planned_red_light_cost=(
                    candidate_planned_red_light_cost
                ),
                candidate_target_speed_mps=perfect_tracker_command[
                    "target_speed_mps"
                ],
                candidate_jerk_magnitude_mps3=perfect_tracker_command[
                    "jerk_magnitude_mps3"
                ],
                candidate_lateral_acceleration_magnitude_mps2=(
                    perfect_tracker_command[
                        "lateral_acceleration_magnitude_mps2"
                    ]
                ),
            )
        selection_done = time.perf_counter()
        elapsed_ms = (selection_done - start) * 1000.0
        phase_latencies_ms = {
            "latency_ms_candidate_generation": (
                candidate_generation_done - start
            )
            * 1000.0,
            "latency_ms_shadow_dp_prior_deviation": (
                shadow_dp_prior_deviation_latency_ms
            ),
            "latency_ms_context_and_obstacles": (
                context_and_obstacles_done - lateral_comfort_done
            )
            * 1000.0,
            "latency_ms_reward_scoring": (
                reward_scoring_done - perfect_tracker_open_loop_done
            )
            * 1000.0,
            "latency_ms_shadow_perfect_tracker_command": (
                shadow_perfect_tracker_command_latency_ms
            ),
            "latency_ms_shadow_perfect_tracker_open_loop": (
                shadow_perfect_tracker_open_loop_latency_ms
            ),
            "latency_ms_shadow_full_horizon_red_light": (
                full_horizon_red_light_latency_ms
            ),
            "latency_ms_outcome_collection": (
                outcome_collection_done - reward_scoring_done
            )
            * 1000.0,
            "latency_ms_red_stopping_margin_atom": (
                red_stopping_margin_done - outcome_collection_done
            )
            * 1000.0,
            "latency_ms_camp_selection": (
                camp_selection_done - red_stopping_margin_done
            )
            * 1000.0,
            "latency_ms_underprogress_relaxation": (
                underprogress_relaxation_done - camp_selection_done
            )
            * 1000.0,
            "latency_ms_perfect_tracker_command_postselection": (
                selection_done - underprogress_relaxation_done
            )
            * 1000.0,
            "latency_ms_camp_atom_computation": selection.timings_ms[
                "atom_computation"
            ],
            "latency_ms_camp_feasibility": selection.timings_ms["feasibility"],
            "latency_ms_camp_collision_checks": selection.timings_ms[
                "collision_checks"
            ],
            "latency_ms_camp_scoring": selection.timings_ms["scoring"],
        }

        selection_step = len(records)
        if (
            microbenchmark_snapshot_dir is not None
            and selection_step in microbenchmark_snapshot_steps
        ):
            _write_microbenchmark_snapshot(
                output_dir=microbenchmark_snapshot_dir,
                selection_step=selection_step,
                normalized_inputs=inputs,
                tensor_converter_module=tensor_converter_module,
                scene=scene,
                map_cache=map_cache,
                model_args=model_args,
                candidates=candidates,
                neighbor_predictions=neighbor_predictions,
                candidate_obstacles=obstacles,
                context=context,
                selector=selector,
                selection=selection,
                scene_features=scene_features,
                external_feasible_mask=external_feasible_mask,
                external_infeasibility_reasons=external_infeasibility_reasons,
                candidate_progress=candidate_progress,
                candidate_planned_red_light_cost=candidate_planned_red_light_cost,
                candidate_full_horizon_planned_red_light_cost=(
                    candidate_full_horizon_planned_red_light_cost
                ),
                candidate_red_stopping_margin_cost=(
                    candidate_red_stopping_margin_cost
                ),
                candidate_dp_prior_jerk_excess_cost=(
                    candidate_dp_prior_jerk_excess_cost
                ),
                candidate_generation_contract=candidate_generation_contract,
                red_route_points=red_route_points,
                perfect_tracker_current_speed_mps=(
                    perfect_tracker_current_speed_mps
                ),
                perfect_tracker_current_longitudinal_acceleration_mps2=(
                    perfect_tracker_current_longitudinal_acceleration_mps2
                ),
                perfect_tracker_current_acceleration_ego_xy=(
                    perfect_tracker_current_acceleration_ego_xy
                ),
                num_candidates=num_candidates,
                noise_scale=noise_scale,
                reference_blend_steps=reference_blend_steps,
                reward_horizon_steps=reward_horizon_steps,
                outcome_horizon_steps=outcome_horizon_steps,
                spawn_config=spawn_config,
            )

        selected_trajectory = candidates[selected_index]
        predictions[ego_id] = selected_trajectory
        state = _evaluation_state(scene, ego_id)
        state["step"] = len(evaluation_records)
        evaluation_records.append(state)
        _append_metric_record(
            replay_module=replay_module,
            tensor_converter_module=tensor_converter_module,
            scene=scene,
            map_cache=map_cache,
            model_args=model_args,
            prediction=selected_trajectory,
            device=device,
            reward_config=reward_config,
            spawn_config=spawn_config,
            records=metric_records,
        )
        if return_turn_indicators and turn_logits is not None:
            chosen_logits = turn_logits[selected_index].copy()
            if turn_indicator_keep_bias != 0.0 and chosen_logits.shape[-1] > 4:
                chosen_logits[4] -= turn_indicator_keep_bias
            turn_indicators[ego_id] = int(np.argmax(chosen_logits))

        records.append(
            {
                "selection_step": len(records),
                "selected_index": selected_index,
                "camp_selected_index_before_tracker_postselection": (
                    baseline_selected_index
                    if perfect_tracker_command_postselection
                    else None
                ),
                "perfect_tracker_command_postselection": (
                    perfect_tracker_command_postselection_stats
                ),
                "underprogress_relaxation": underprogress_relaxation_stats,
                "num_candidates": int(num_candidates),
                "candidate_noise_scale": float(noise_scale),
                "candidate_reference_blend_steps": reference_blend_steps,
                "candidate_generation_contract": candidate_generation_contract,
                "candidate_trajectory_horizon_steps": int(candidates.shape[1]),
                "candidate_first_reference_xy": (
                    candidates[:, 0, :2].tolist()
                ),
                "candidate_perfect_tracker_reference_first_xy": (
                    perfect_tracker_command[
                        "first_reference_xy"
                    ].tolist()
                ),
                "candidate_perfect_tracker_reference_first_heading_rad": (
                    perfect_tracker_command[
                        "first_reference_heading_rad"
                    ].tolist()
                ),
                "candidate_perfect_tracker_first_step_reach_m": (
                    perfect_tracker_command["first_step_reach_m"].tolist()
                ),
                "candidate_perfect_tracker_postprocessed_tail_xy": (
                    perfect_tracker_command[
                        "postprocessed_tail_reference_xy"
                    ].tolist()
                ),
                "candidate_perfect_tracker_postprocessed_reference_prefix": (
                    perfect_tracker_command["postprocessed_reference"][
                        :, : PERFECT_TRACKER_OPEN_LOOP_HORIZONS[-1]
                    ].tolist()
                ),
                "perfect_tracker_command_inputs": {
                    "dt": float(getattr(scene, "dt", 0.1)),
                    "current_speed_mps": perfect_tracker_current_speed_mps,
                    "current_longitudinal_acceleration_mps2": (
                        perfect_tracker_current_longitudinal_acceleration_mps2
                    ),
                    "max_speed_mps": 20.0,
                    "velocity_smooth_window": 8,
                    "stop_threshold_mps": 0.3,
                    "restart_speed_threshold_mps": 0.1,
                    "restart_plan_speed_threshold_mps": 0.5,
                },
                "perfect_tracker_open_loop_rollout_inputs": {
                    "full_horizon_steps": int(candidates.shape[1]),
                    "horizons": list(PERFECT_TRACKER_OPEN_LOOP_HORIZONS),
                    "dt": float(getattr(scene, "dt", 0.1)),
                    "current_speed_mps": perfect_tracker_current_speed_mps,
                    "current_acceleration_ego_xy": (
                        perfect_tracker_current_acceleration_ego_xy.tolist()
                    ),
                    "max_speed_mps": 20.0,
                    "restart_speed_threshold_mps": 0.1,
                    "restart_plan_speed_threshold_mps": 0.5,
                },
                "candidate_perfect_tracker_open_loop_rollout": {
                    horizon: {
                        metric: values.tolist()
                        for metric, values in metrics.items()
                    }
                    for horizon, metrics in perfect_tracker_open_loop[
                        "horizons"
                    ].items()
                },
                "perfect_tracker_candidate_preprocessing": (
                    _perfect_tracker_candidate_preprocessing(spawn_config)
                ),
                "candidate_perfect_tracker_tail_average_speed_mps": (
                    perfect_tracker_command["tail_average_speed_mps"].tolist()
                ),
                "candidate_perfect_tracker_restart_push": (
                    perfect_tracker_command["restart_push"].tolist()
                ),
                "candidate_perfect_tracker_target_speed_mps": (
                    perfect_tracker_command["target_speed_mps"].tolist()
                ),
                "candidate_perfect_tracker_acceleration_mps2": (
                    perfect_tracker_command["acceleration_mps2"].tolist()
                ),
                "candidate_perfect_tracker_jerk_magnitude_mps3": (
                    perfect_tracker_command[
                        "jerk_magnitude_mps3"
                    ].tolist()
                ),
                "candidate_perfect_tracker_yaw_rate_magnitude_rps": (
                    perfect_tracker_command[
                        "yaw_rate_magnitude_rps"
                    ].tolist()
                ),
                "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": (
                    perfect_tracker_command[
                        "lateral_acceleration_magnitude_mps2"
                    ].tolist()
                ),
                "used_fallback": selection.used_fallback,
                "camp_fallback_mode": getattr(selector, "fallback_mode", "uniform")
                if selector is not None
                else None,
                "feasible_mask": selection.feasible_mask.tolist(),
                "infeasibility_reasons": [
                    list(reasons) for reasons in selection.infeasibility_reasons
                ],
                "scores": selection.scores.tolist(),
                "weights": selection.weights.tolist(),
                "selection_scores": selection.selection_scores.tolist(),
                "selection_weights": selection.selection_weights.tolist(),
                "atoms": selection.atoms.tolist(),
                "normalized_atoms": selection.normalized_atoms.tolist(),
                "selection_normalized_atoms": (
                    selection.selection_normalized_atoms.tolist()
                ),
                "atom_schema_version": atom_schema_for_dimension(
                    selection.atoms.shape[1]
                )[0],
                "atom_names": list(
                    atom_schema_for_dimension(selection.atoms.shape[1])[1]
                ),
                "dp_candidate_rewards": candidate_rewards,
                "dp_candidate_reward_horizon_steps": (
                    min(reward_horizon_steps, int(candidates.shape[1]))
                    if candidate_rewards is not None
                    else None
                ),
                "candidate_full_horizon_planned_red_light_cost": (
                    candidate_full_horizon_planned_red_light_cost.tolist()
                    if candidate_full_horizon_planned_red_light_cost is not None
                    else None
                ),
                "candidate_full_horizon_red_light_horizon_steps": (
                    int(candidates.shape[1])
                    if candidate_full_horizon_planned_red_light_cost is not None
                    else None
                ),
                "candidate_horizon_union_planned_red_light_cost": (
                    candidate_horizon_union_planned_red_light_cost.tolist()
                    if candidate_horizon_union_planned_red_light_cost is not None
                    else None
                ),
                "candidate_route_progress": (
                    candidate_route_progress.tolist()
                    if candidate_route_progress is not None
                    else None
                ),
                "candidate_step_reach": (
                    candidate_step_reach.tolist()
                    if candidate_step_reach is not None
                    else None
                ),
                "candidate_step_reach_guard_relaxed": (
                    bool(candidate_step_reach_guard_relaxed)
                    if min_candidate0_step_reach_ratio is not None
                    else None
                ),
                "lexicographic_stage_counts": lexicographic_stage_counts,
                "candidate_closed_loop_outcomes": candidate_outcomes,
                "candidate_red_stopping_margin_cost": (
                    candidate_red_stopping_margin_cost.tolist()
                ),
                "candidate_dp_prior_deviation_cost": (
                    candidate_dp_prior_deviation_cost.tolist()
                ),
                "candidate_dp_prior_jerk_excess_cost": (
                    candidate_dp_prior_jerk_excess_cost.tolist()
                ),
                "candidate_dp_prior_acceleration_excess_cost": (
                    candidate_dp_prior_acceleration_excess_cost.tolist()
                ),
                "candidate_dp_prior_comfort_excess_horizon_steps": (
                    dp_prior_comfort_horizon_steps
                ),
                "candidate_horizon_lateral_acceleration_cost": (
                    candidate_horizon_lateral_acceleration_cost.tolist()
                ),
                "candidate_dp_prior_lateral_acceleration_excess_cost": (
                    candidate_dp_prior_lateral_acceleration_excess_cost.tolist()
                ),
                "candidate_horizon_yaw_rate_cost": (
                    candidate_horizon_yaw_rate_cost.tolist()
                ),
                "candidate_dp_prior_yaw_rate_excess_cost": (
                    candidate_dp_prior_yaw_rate_excess_cost.tolist()
                ),
                "candidate_lateral_comfort_horizon_steps": (
                    lateral_comfort_horizon_steps
                ),
                "red_route_point_count": int(red_route_points.shape[0]),
                "latency_ms_shadow_red_stopping_margin": (
                    shadow_red_stopping_margin_latency_ms
                ),
                "latency_ms_shadow_dp_prior_comfort_excess": (
                    shadow_dp_prior_comfort_excess_latency_ms
                ),
                "latency_ms_shadow_lateral_comfort": (
                    shadow_lateral_comfort_latency_ms
                ),
                "red_stopping_margin_used_as_atom": (
                    "red_stopping_margin_cost"
                    in atom_schema_for_dimension(selection.atoms.shape[1])[1]
                ),
                "dp_prior_jerk_excess_used_as_atom": (
                    "dp_prior_jerk_excess_cost"
                    in atom_schema_for_dimension(selection.atoms.shape[1])[1]
                ),
                "candidate_closed_loop_outcome_horizon_steps": (
                    min(outcome_horizon_steps, int(candidates.shape[1]))
                    if candidate_outcomes is not None
                    else None
                ),
                "candidate_closed_loop_outcome_weights": (
                    outcome_weights if candidate_outcomes is not None else None
                ),
                "dp_scene_features": scene_features.tolist(),
                "dp_scene_feature_names": list(DP_SCENE_FEATURE_NAMES),
                "latency_ms_including_candidate_generation": elapsed_ms,
                **phase_latencies_ms,
            }
        )
        if return_turn_indicators:
            return predictions, turn_indicators
        return predictions

    replay_module._predict_batch = camp_predict
    return original_predict, records, metric_records, evaluation_records


def main() -> None:
    args = parse_args()
    _validate_args(args)

    _install_diffusion_repo(args.diffusion_repo)

    import torch
    import scenario_generation.replay as replay
    import scenario_generation.tensor_converter as tensor_converter
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder
    from scenario_generation.route import Route
    from rlvr.autoresearch.tools.reward_config_from_json import load_reward_config

    route = Route.load(args.route)
    map_path = args.map_path or route.map_path
    using_projection_fallback = install_lanelet2_projection_fallback(map_path)
    builder = LaneletSceneBuilder(map_path)
    config = replay.SpawnConfig.from_json(args.config)
    if args.steps is not None:
        config.max_steps = args.steps
    if args.seed is not None:
        config.seed = args.seed
    if args.max_npcs is not None:
        config.max_active_npcs = args.max_npcs
    if args.spawn_probability is not None:
        config.spawn_probability = args.spawn_probability
    if args.advance_mode != "config":
        config.advance_mode = args.advance_mode
    if args.traffic_lights != "config":
        config.enable_traffic_lights = args.traffic_lights == "on"
    config.validate()
    if (
        args.camp_perfect_tracker_command_postselection
        and config.advance_mode != "perfect"
    ):
        raise ValueError(
            "PerfectTracker command postselection requires "
            "advance_mode='perfect'."
        )

    device = args.device if torch.cuda.is_available() or args.device == "cpu" else "cpu"
    model, model_args = _load_model(args.model_path, args.model_args, device)
    candidate_guidance = _configure_candidate_guidance(
        model,
        guidance_config_path=args.candidate_guidance_config,
        guidance_scale=args.candidate_guidance_scale,
    )
    candidate_generation_contract = _candidate_generation_contract(
        model_args,
        num_candidates=args.num_candidates,
        noise_scale=args.candidate_noise_scale,
        noise_strategy=args.candidate_noise_strategy,
        reference_blend_steps=args.candidate_reference_blend_steps,
        guidance=candidate_guidance,
    )
    reward_config = (
        load_reward_config(args.reward_config)
        if args.reward_config is not None
        else None
    )
    selector = _build_selector(args)
    records: list[dict[str, Any]] | None = None
    metric_records: list[dict[str, Any]] = []
    evaluation_records: list[dict[str, Any]] = []
    original_predict = None
    if selector is not None:
        route_centerline = _route_centerline_world(builder, route)
        (
            original_predict,
            records,
            metric_records,
            evaluation_records,
        ) = _install_camp_predictor(
            replay,
            tensor_converter,
            selector,
            num_candidates=args.num_candidates,
            noise_scale=args.candidate_noise_scale,
            reference_blend_steps=args.candidate_reference_blend_steps,
            candidate_generation_contract=candidate_generation_contract,
            safety_radius=args.camp_safety_radius,
            clearance_margin=args.camp_clearance_margin,
            lane_corridor_buffer=args.camp_lane_corridor_buffer,
            feasibility_source=args.camp_feasibility_source,
            min_progress_ratio=args.camp_min_progress_ratio,
            min_candidate0_progress_ratio=args.camp_min_candidate0_progress_ratio,
            min_candidate0_route_progress_ratio=(
                args.camp_min_candidate0_route_progress_ratio
            ),
            min_candidate0_step_reach_ratio=(
                args.camp_min_candidate0_step_reach_ratio
            ),
            candidate0_step_reach_preserve_feasible=(
                bool(args.camp_candidate0_step_reach_preserve_feasible)
            ),
            lexicographic_progress_epsilon_m=(
                args.camp_lexicographic_progress_epsilon_m
            ),
            lexicographic_red_epsilon=args.camp_lexicographic_red_epsilon,
            lexicographic_jerk_epsilon=args.camp_lexicographic_jerk_epsilon,
            lexicographic_lateral_epsilon=(
                args.camp_lexicographic_lateral_epsilon
            ),
            perfect_tracker_command_postselection=(
                bool(args.camp_perfect_tracker_command_postselection)
            ),
            underprogress_relaxation=bool(args.camp_underprogress_relaxation),
            underprogress_progress_loss_budget_m=(
                args.camp_underprogress_progress_loss_budget_m
            ),
            underprogress_h3_distance_loss_budget_m=(
                args.camp_underprogress_h3_distance_loss_budget_m
            ),
            underprogress_lateral_limit_mps2=(
                args.camp_underprogress_lateral_limit_mps2
            ),
            reward_horizon_steps=args.camp_reward_horizon_steps,
            collect_closed_loop_outcomes=args.camp_collect_closed_loop_outcomes,
            outcome_horizon_steps=args.camp_outcome_horizon_steps,
            outcome_weights={
                "progress": args.camp_outcome_progress_weight,
                "collision": args.camp_outcome_collision_penalty,
                "near_miss": args.camp_outcome_near_miss_penalty,
                "lane_violation": args.camp_outcome_lane_penalty,
                "red_light": args.camp_outcome_red_light_penalty,
                "mean_jerk": args.camp_outcome_jerk_penalty,
                "mean_lateral_acceleration": (
                    args.camp_outcome_lateral_acceleration_penalty
                ),
            },
            near_miss_threshold_m=args.near_miss_threshold_m,
            ego_length=float(config.ego_length),
            ego_width=float(config.ego_width),
            ego_wheelbase=float(config.ego_wheelbase),
            reward_config=reward_config,
            spawn_config=config,
            route_centerline=route_centerline,
            microbenchmark_snapshot_dir=(
                args.camp_microbenchmark_snapshot_dir
            ),
            microbenchmark_snapshot_steps=(
                args.camp_microbenchmark_snapshot_steps
            ),
        )
    else:
        (
            original_predict,
            metric_records,
            evaluation_records,
        ) = _install_top1_observer(
            replay,
            tensor_converter,
            reward_config=reward_config,
            spawn_config=config,
        )

    try:
        result = replay.run_route_replay(
            model=model,
            model_args=model_args,
            builder=builder,
            route=route,
            output_dir=args.output_dir,
            spawn_config=config,
            device=device,
        )
    finally:
        if original_predict is not None:
            replay._predict_batch = original_predict

    args.output_dir.mkdir(parents=True, exist_ok=True)
    selection_log = None
    if records is not None:
        selection_log = args.output_dir / "camp_selection_log.json"
        selection_log.write_text(json.dumps(records, indent=2), encoding="utf-8")
    metric_log = args.output_dir / "camp_metric_log.json"
    metric_log.write_text(json.dumps(metric_records, indent=2), encoding="utf-8")
    evaluation_log = args.output_dir / "camp_evaluation_state_log.json"
    evaluation_log.write_text(
        json.dumps(evaluation_records, indent=2),
        encoding="utf-8",
    )
    effective_num_candidates = args.num_candidates if records is not None else 1
    effective_noise_scale = args.candidate_noise_scale if records is not None else None
    effective_reference_blend = (
        {
            "enabled": True,
            "steps": int(args.candidate_reference_blend_steps),
            "reference_candidate_index": 0,
            "weight_definition": "min(t / steps, 1)",
            "first_reference_xy_preserved": True,
            "selection_effect": True,
        }
        if records is not None
        and args.candidate_reference_blend_steps is not None
        else None
    )
    effective_lane_buffer = (
        args.camp_lane_corridor_buffer if records is not None else None
    )
    effective_feasibility_source = (
        args.camp_feasibility_source if records is not None else None
    )
    effective_min_progress_ratio = (
        args.camp_min_progress_ratio
        if records is not None and args.camp_feasibility_source == "dp_reward"
        else None
    )
    effective_min_candidate0_progress_ratio = (
        args.camp_min_candidate0_progress_ratio
        if records is not None
        and args.camp_feasibility_source == "dp_reward"
        else None
    )
    effective_min_candidate0_route_progress_ratio = (
        args.camp_min_candidate0_route_progress_ratio
        if records is not None
        else None
    )
    effective_min_candidate0_step_reach_ratio = (
        args.camp_min_candidate0_step_reach_ratio
        if records is not None
        else None
    )
    effective_candidate0_step_reach_preserve_feasible = (
        bool(args.camp_candidate0_step_reach_preserve_feasible)
        if records is not None and args.camp_min_candidate0_step_reach_ratio is not None
        else None
    )
    effective_lexicographic_preselection = (
        {
            "enabled": True,
            "order": ["progress", "planned_red", "jerk", "lateral"],
            "progress_epsilon_m": float(
                args.camp_lexicographic_progress_epsilon_m
            ),
            "planned_red_epsilon": float(args.camp_lexicographic_red_epsilon),
            "jerk_epsilon": float(args.camp_lexicographic_jerk_epsilon),
            "lateral_epsilon": float(args.camp_lexicographic_lateral_epsilon),
            "selection_effect": True,
        }
        if records is not None
        and args.camp_lexicographic_progress_epsilon_m is not None
        else None
    )
    effective_perfect_tracker_command_postselection = (
        {
            "enabled": True,
            "selection_effect": True,
            "baseline": "camp_selected_index",
            "required_nonworse": [
                "base_feasibility",
                "perfect_tracker_target_speed",
                "dp_progress",
                "planned_red",
                "perfect_tracker_command_jerk",
                "perfect_tracker_command_lateral_acceleration",
            ],
            "required_strict_improvement": [
                "perfect_tracker_command_jerk",
                "perfect_tracker_command_lateral_acceleration",
            ],
            "order": [
                "perfect_tracker_command_jerk",
                "perfect_tracker_command_lateral_acceleration",
                "camp_score",
                "candidate_index",
            ],
            "epsilons": {
                "target_speed_mps": 0.0,
                "progress_m": 0.0,
                "planned_red": 0.0,
                "jerk_mps3": 0.0,
                "lateral_acceleration_mps2": 0.0,
            },
            "new_fallback_possible": False,
        }
        if records is not None
        and args.camp_perfect_tracker_command_postselection
        else None
    )
    effective_underprogress_relaxation = (
        {
            "enabled": True,
            "selection_effect": True,
            "ignored_reason": "dp_underprogress",
            "requires_stopping_margin_nonworse": True,
            "hard_reasons_remain_hard": True,
            "order": [
                "union_red",
                "red_stopping_margin",
                "camp_score",
                "candidate_index",
            ],
            "progress_loss_budget_m": float(
                args.camp_underprogress_progress_loss_budget_m
            ),
            "h3_distance_loss_budget_m": float(
                args.camp_underprogress_h3_distance_loss_budget_m
            ),
            "h3_max_lateral_limit_mps2": float(
                args.camp_underprogress_lateral_limit_mps2
            ),
        }
        if records is not None and args.camp_underprogress_relaxation
        else None
    )
    effective_reward_horizon_steps = (
        args.camp_reward_horizon_steps
        if records is not None and args.camp_feasibility_source == "dp_reward"
        else None
    )
    effective_comfort_shadow_horizon_steps = (
        records[0]["candidate_dp_prior_comfort_excess_horizon_steps"]
        if records
        else None
    )
    effective_lateral_comfort_horizon_steps = (
        records[0]["candidate_lateral_comfort_horizon_steps"]
        if records
        else None
    )
    microbenchmark_snapshot_paths = (
        sorted(args.camp_microbenchmark_snapshot_dir.glob("*.npz"))
        if args.camp_microbenchmark_snapshot_dir is not None
        else []
    )
    summary = {
        "replay_result": result,
        "camp_selection_log": str(selection_log) if selection_log is not None else None,
        "camp_metric_log": str(metric_log),
        "camp_evaluation_state_log": str(evaluation_log),
        "num_candidates": effective_num_candidates,
        "candidate_noise_scale": effective_noise_scale,
        "candidate_reference_blend": effective_reference_blend,
        "candidate_generation_contract": (
            candidate_generation_contract
            if records is not None
            else None
        ),
        "camp_microbenchmark_snapshots": (
            {
                "enabled": True,
                "selection_effect": False,
                "latency_evidence": False,
                "directory": str(args.camp_microbenchmark_snapshot_dir),
                "requested_steps": list(
                    args.camp_microbenchmark_snapshot_steps
                ),
                "files": [str(path) for path in microbenchmark_snapshot_paths],
            }
            if args.camp_microbenchmark_snapshot_dir is not None
            else None
        ),
        "camp_lane_corridor_buffer": effective_lane_buffer,
        "camp_feasibility_source": effective_feasibility_source,
        "camp_min_progress_ratio": effective_min_progress_ratio,
        "camp_min_candidate0_progress_ratio": (
            effective_min_candidate0_progress_ratio
        ),
        "camp_min_candidate0_route_progress_ratio": (
            effective_min_candidate0_route_progress_ratio
        ),
        "camp_min_candidate0_step_reach_ratio": (
            effective_min_candidate0_step_reach_ratio
        ),
        "camp_candidate0_step_reach_preserve_feasible": (
            effective_candidate0_step_reach_preserve_feasible
        ),
        "camp_lexicographic_preselection": effective_lexicographic_preselection,
        "camp_perfect_tracker_command_postselection": (
            effective_perfect_tracker_command_postselection
        ),
        "camp_underprogress_relaxation": effective_underprogress_relaxation,
        "camp_reward_horizon_steps": effective_reward_horizon_steps,
        "camp_collect_closed_loop_outcomes": (
            bool(args.camp_collect_closed_loop_outcomes)
            if records is not None
            else None
        ),
        "camp_outcome_horizon_steps": (
            args.camp_outcome_horizon_steps
            if records is not None and args.camp_collect_closed_loop_outcomes
            else None
        ),
        "camp_shadow_red_stopping_margin": (
            {
                "enabled": True,
                "selection_effect": False,
                "comfort_deceleration_mps2": 2.0,
                "stop_buffer_m": 3.0,
                "lookahead_m": 40.0,
                "heading_alignment_threshold": 0.5,
                "unit": "m^2/s",
            }
            if records is not None
            else None
        ),
        "camp_shadow_dp_prior_comfort_excess": (
            {
                "enabled": True,
                "selection_effect": False,
                "reference_candidate_index": 0,
                "requested_horizon_steps": args.camp_outcome_horizon_steps,
                "effective_horizon_steps": (
                    effective_comfort_shadow_horizon_steps
                ),
                "definition": (
                    "positive mean finite-difference jerk/acceleration "
                    "norm excess over candidate 0"
                ),
            }
            if records is not None
            else None
        ),
        "camp_shadow_lateral_comfort": (
            {
                "enabled": True,
                "selection_effect": False,
                "reference_candidate_index": 0,
                "requested_horizon_steps": args.camp_outcome_horizon_steps,
                "effective_horizon_steps": (
                    effective_lateral_comfort_horizon_steps
                ),
                "fields": [
                    "candidate_horizon_lateral_acceleration_cost",
                    "candidate_dp_prior_lateral_acceleration_excess_cost",
                    "candidate_horizon_yaw_rate_cost",
                    "candidate_dp_prior_yaw_rate_excess_cost",
                ],
            }
            if records is not None
            else None
        ),
        "camp_shadow_perfect_tracker_command": (
            {
                "schema_version": "perfect_tracker_command_shadow_v2",
                "enabled": True,
                "selection_effect": False,
                "tracker_class": (
                    "scenario_generation.mpc_tracker.PerfectTracker"
                ),
                "reference_postprocessing": (
                    "scenario_generation.mpc_tracker.postprocess_reference"
                ),
                "candidate_frame": "ego",
                "candidate_preprocessing": (
                    _perfect_tracker_candidate_preprocessing(config)
                ),
                "max_speed_mps": 20.0,
                "velocity_smooth_window": 8,
                "stop_threshold_mps": 0.3,
                "restart_speed_threshold_mps": 0.1,
                "restart_plan_speed_threshold_mps": 0.5,
                "fields": [
                    "candidate_perfect_tracker_reference_first_xy",
                    (
                        "candidate_perfect_tracker_"
                        "reference_first_heading_rad"
                    ),
                    "candidate_perfect_tracker_first_step_reach_m",
                    "candidate_perfect_tracker_tail_average_speed_mps",
                    "candidate_perfect_tracker_restart_push",
                    "candidate_perfect_tracker_target_speed_mps",
                    "candidate_perfect_tracker_acceleration_mps2",
                    "candidate_perfect_tracker_jerk_magnitude_mps3",
                    "candidate_perfect_tracker_yaw_rate_magnitude_rps",
                    (
                        "candidate_perfect_tracker_"
                        "lateral_acceleration_magnitude_mps2"
                    ),
                ],
            }
            if records is not None
            else None
        ),
        "camp_shadow_perfect_tracker_open_loop_rollout": (
            {
                "schema_version": "perfect_tracker_open_loop_rollout_v1",
                "enabled": True,
                "selection_effect": False,
                "online_feature_eligible": True,
                "closed_loop_guarantee": False,
                "tracker_class": (
                    "scenario_generation.mpc_tracker.PerfectTracker"
                ),
                "reference_postprocessing": (
                    "scenario_generation.mpc_tracker.postprocess_reference"
                ),
                "candidate_preprocessing": (
                    _perfect_tracker_candidate_preprocessing(config)
                ),
                "candidate_frame": "ego",
                "horizons": list(PERFECT_TRACKER_OPEN_LOOP_HORIZONS),
                "definition": (
                    "fixed-candidate PerfectTracker commit rollout without "
                    "Diffusion Planner replanning"
                ),
                "metrics": [
                    "distance_m",
                    "mean_vector_jerk_mps3",
                    "max_vector_jerk_mps3",
                    "mean_lateral_acceleration_mps2",
                    "max_lateral_acceleration_mps2",
                ],
            }
            if records is not None
            else None
        ),
        "camp_shadow_full_horizon_red_light": (
            {
                "schema_version": "full_horizon_red_light_shadow_v1",
                "enabled": True,
                "selection_effect": False,
                "online_feature_eligible": True,
                "source": "rlvr.reward.compute_red_light_score_batch",
                "candidate_preprocessing": (
                    _perfect_tracker_candidate_preprocessing(config)
                ),
                "candidate_frame": "ego",
                "horizon_steps": (
                    records[0][
                        "candidate_full_horizon_red_light_horizon_steps"
                    ]
                    if records
                    else None
                ),
                "raw_full_horizon_field": (
                    "candidate_full_horizon_planned_red_light_cost"
                ),
                "horizon_union_certificate_field": (
                    "candidate_horizon_union_planned_red_light_cost"
                ),
            }
            if records is not None
            and args.camp_feasibility_source == "dp_reward"
            else None
        ),
        "selector_mode": args.camp_selector_mode,
        "camp_fallback_mode": args.camp_fallback_mode,
        "advance_mode": config.advance_mode,
        "dp_scene_feature_names": list(DP_SCENE_FEATURE_NAMES),
        "model_args": str(args.model_args) if args.model_args is not None else None,
        "using_no_ros_projection_fallback": using_projection_fallback,
        "benchmark": {
            "variant": args.camp_selector_mode,
            "fallback_mode": args.camp_fallback_mode,
            "route": str(args.route),
            "map_path": str(map_path),
            "model_path": str(args.model_path),
            "config": str(args.config),
            "seed": args.seed,
            "steps": args.steps,
            "max_npcs": args.max_npcs,
            "spawn_probability": args.spawn_probability,
            "traffic_lights": bool(config.enable_traffic_lights),
            "advance_mode": config.advance_mode,
            "reward_config": (
                str(args.reward_config) if args.reward_config is not None else None
            ),
        },
    }
    (args.output_dir / "camp_replay_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    validation = summarize_replay_artifacts(
        args.output_dir,
        selection_records=records,
        replay_result=result,
        metric_records=metric_records,
        evaluation_records=evaluation_records,
        route_centerline=_route_centerline_world(builder, route),
        near_miss_threshold_m=args.near_miss_threshold_m,
    )
    validation["selector_mode"] = args.camp_selector_mode
    validation["num_candidates"] = effective_num_candidates
    validation["candidate_noise_scale"] = effective_noise_scale
    validation["candidate_reference_blend"] = effective_reference_blend
    validation["camp_lane_corridor_buffer"] = effective_lane_buffer
    validation["camp_feasibility_source"] = effective_feasibility_source
    validation["camp_min_progress_ratio"] = effective_min_progress_ratio
    validation["camp_min_candidate0_progress_ratio"] = (
        effective_min_candidate0_progress_ratio
    )
    validation["camp_min_candidate0_route_progress_ratio"] = (
        effective_min_candidate0_route_progress_ratio
    )
    validation["camp_min_candidate0_step_reach_ratio"] = (
        effective_min_candidate0_step_reach_ratio
    )
    validation["camp_candidate0_step_reach_preserve_feasible"] = (
        effective_candidate0_step_reach_preserve_feasible
    )
    validation["camp_lexicographic_preselection"] = (
        effective_lexicographic_preselection
    )
    validation["camp_perfect_tracker_command_postselection"] = (
        effective_perfect_tracker_command_postselection
    )
    validation["camp_underprogress_relaxation"] = effective_underprogress_relaxation
    validation["camp_reward_horizon_steps"] = effective_reward_horizon_steps
    validation["camp_collect_closed_loop_outcomes"] = (
        bool(args.camp_collect_closed_loop_outcomes) if records is not None else None
    )
    validation["camp_outcome_horizon_steps"] = (
        args.camp_outcome_horizon_steps
        if records is not None and args.camp_collect_closed_loop_outcomes
        else None
    )
    validation["camp_shadow_dp_prior_comfort_excess"] = summary[
        "camp_shadow_dp_prior_comfort_excess"
    ]
    validation["camp_shadow_lateral_comfort"] = summary[
        "camp_shadow_lateral_comfort"
    ]
    validation["camp_shadow_perfect_tracker_command"] = summary[
        "camp_shadow_perfect_tracker_command"
    ]
    validation["camp_shadow_perfect_tracker_open_loop_rollout"] = summary[
        "camp_shadow_perfect_tracker_open_loop_rollout"
    ]
    validation["camp_shadow_full_horizon_red_light"] = summary[
        "camp_shadow_full_horizon_red_light"
    ]
    validation["benchmark"] = summary["benchmark"]
    validation["benchmark_key"] = (
        f"route={args.route}|seed={args.seed}|steps={args.steps}|"
        f"max_npcs={args.max_npcs}|spawn_probability={args.spawn_probability}|"
        f"traffic_lights={bool(config.enable_traffic_lights)}|"
        f"advance_mode={config.advance_mode}"
    )
    validation["camp_fallback_mode"] = args.camp_fallback_mode
    validation["advance_mode"] = config.advance_mode
    (args.output_dir / "camp_validation_summary.json").write_text(
        json.dumps(validation, indent=2), encoding="utf-8"
    )
    print(json.dumps({"replay": summary, "validation": validation}, indent=2))


if __name__ == "__main__":
    main()
