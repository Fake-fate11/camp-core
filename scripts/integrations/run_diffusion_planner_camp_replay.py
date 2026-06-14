#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict
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
    CAMPSelector,
    atom_schema_for_dimension,
    build_context_from_scene,
    compute_candidate_closed_loop_outcomes,
    compute_dp_prior_comfort_excess_costs,
    compute_dp_prior_deviation_costs,
    compute_lateral_comfort_shadow_costs,
    compute_red_stopping_margin_costs,
    extract_dp_scene_features,
    generate_candidate_trajectories,
    install_lanelet2_projection_fallback,
    load_dp_camp_atom_scales,
    red_route_points_from_scene,
    summarize_replay_artifacts,
)


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
) -> list[dict[str, Any]]:
    if map_cache is None:
        raise RuntimeError("Candidate reward scoring requires Diffusion Planner map_cache.")

    import torch
    from rlvr.reward import compute_reward_batch

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
    scored_candidates = scored_candidates[:, :reward_horizon_steps]
    trajectories = torch.from_numpy(scored_candidates).float().to(device)
    return [
        asdict(breakdown)
        for breakdown in compute_reward_batch(
            trajectories,
            reward_data,
            reward_config,
        )
    ]


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


def _install_camp_predictor(
    replay_module: Any,
    tensor_converter_module: Any,
    selector: CAMPSelector,
    *,
    num_candidates: int,
    noise_scale: float,
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
        candidate_route_progress = None
        candidate_step_reach = None
        candidate_step_reach_guard_relaxed = False
        lexicographic_stage_counts = None
        candidate_planned_red_light_cost = None
        red_route_points = red_route_points_from_scene(scene, ego_id)
        external_feasible_mask = None
        external_infeasibility_reasons = None
        if feasibility_source == "dp_reward":
            candidate_rewards = _score_candidate_batch(
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
        if min_candidate0_step_reach_ratio is not None:
            candidate_step_reach = _candidate_step_reach(candidates)
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
            ego_agent = scene.get_agent(ego_id)
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
                reward_scoring_done - context_and_obstacles_done
            )
            * 1000.0,
            "latency_ms_outcome_collection": (
                outcome_collection_done - reward_scoring_done
            )
            * 1000.0,
            "latency_ms_red_stopping_margin_atom": (
                red_stopping_margin_done - outcome_collection_done
            )
            * 1000.0,
            "latency_ms_camp_selection": (
                selection_done - red_stopping_margin_done
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

        predictions[ego_id] = selection.selected_trajectory
        state = _evaluation_state(scene, ego_id)
        state["step"] = len(evaluation_records)
        evaluation_records.append(state)
        _append_metric_record(
            replay_module=replay_module,
            tensor_converter_module=tensor_converter_module,
            scene=scene,
            map_cache=map_cache,
            model_args=model_args,
            prediction=selection.selected_trajectory,
            device=device,
            reward_config=reward_config,
            spawn_config=spawn_config,
            records=metric_records,
        )
        if return_turn_indicators and turn_logits is not None:
            chosen_logits = turn_logits[selection.selected_index].copy()
            if turn_indicator_keep_bias != 0.0 and chosen_logits.shape[-1] > 4:
                chosen_logits[4] -= turn_indicator_keep_bias
            turn_indicators[ego_id] = int(np.argmax(chosen_logits))

        records.append(
            {
                "selection_step": len(records),
                "selected_index": selection.selected_index,
                "num_candidates": int(num_candidates),
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
                    if candidate_step_reach is not None
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

    device = args.device if torch.cuda.is_available() or args.device == "cpu" else "cpu"
    model, model_args = _load_model(args.model_path, args.model_args, device)
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
    summary = {
        "replay_result": result,
        "camp_selection_log": str(selection_log) if selection_log is not None else None,
        "camp_metric_log": str(metric_log),
        "camp_evaluation_state_log": str(evaluation_log),
        "num_candidates": effective_num_candidates,
        "candidate_noise_scale": effective_noise_scale,
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
