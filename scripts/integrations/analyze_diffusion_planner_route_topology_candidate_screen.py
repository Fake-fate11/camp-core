#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_splice_recompute_gate import (  # noqa: E402
    SNAPSHOT_GLOB,
    TOL,
    _load_runtime,
    _load_snapshot,
    _score_trajectories,
    _validate_snapshot,
    heading_features_from_xy,
    reward_hard_feasibility,
    reward_metric_vector,
    reward_progress_screen,
)
from scripts.integrations.analyze_diffusion_planner_world_frame_bridge_screen import (  # noqa: E402
    _selected_tracker_summary,
    _tracker_diagnostics,
    _tracker_metrics_for_budget,
)
from scripts.integrations.analyze_diffusion_planner_source_donor_support_gate import (  # noqa: E402
    _tracker_delta,
)


READINESS_READY = "route_topology_candidate_design_ready"
READY_STATUS = "route_topology_candidate_support_present"
REJECT_STATUS = "route_topology_candidate_support_insufficient"
SOURCE_CONFLICT_STATUS = "route_topology_candidate_screen_source_conflict"


@dataclass(frozen=True)
class RouteTopologyCandidateConfig:
    generator_policy: str = "lane_centerline_red_stop"
    red_stop_margins_m: tuple[float, ...] = (2.0, 4.0, 6.0)
    backup_stop_offsets_m: tuple[float, ...] = (0.0, 1.0)
    prefix_steps: tuple[int, ...] = (3, 5, 10)
    bridge_steps: tuple[int, ...] = (10,)
    lane_projected_offset_scales: tuple[float, ...] = (1.0, 0.5, 0.0)
    min_stop_distance_m: float = 2.0
    max_deceleration_mps2: float = 3.0
    default_speed_mps: float = 4.0
    jerk_progress_max_jerk_mps3: float = 8.0
    min_progress_ratio: float = 0.8
    progress_loss_budgets_m: tuple[float, ...] = (0.5, 1.0, 1.5)
    smoothness_loss_budgets: tuple[float, ...] = (0.0, 0.5, 1.0)
    command_jerk_worse_budget_mps3: float = 0.0
    command_lateral_worse_budget_mps2: float = 0.0
    rollout_horizon: int = 3
    rollout_distance_loss_budget_m: float = 0.10
    rollout_jerk_worse_budget_mps3: float = 0.0
    rollout_lateral_worse_budget_mps2: float = 0.0
    min_snapshot_support_rate: float = 0.25


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline route/topology-aware candidate augmentation screen over "
            "fixed DP/CAMP microbenchmark snapshots. It materializes "
            "deterministic lane-following red-stop candidates, recomputes DP "
            "reward and PerfectTracker proxies, and has no online selection "
            "effect."
        )
    )
    parser.add_argument("--snapshot_dir", type=Path, required=True)
    parser.add_argument("--route_topology_gate_json", type=Path, required=True)
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--reward_config", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--generator_policy",
        choices=(
            "lane_centerline_red_stop",
            "prefix_comfort_red_stop",
            "lane_projected_red_stop",
            "lane_projected_jerk_progress_red_stop",
            "prefix_lane_projected_red_stop",
            "prefix_lane_projected_latest_safe_red_stop",
        ),
        default="lane_centerline_red_stop",
    )
    parser.add_argument("--red_stop_margin_m", action="append", type=float)
    parser.add_argument("--backup_stop_offset_m", action="append", type=float)
    parser.add_argument("--prefix_step", action="append", type=int)
    parser.add_argument("--bridge_step", action="append", type=int)
    parser.add_argument("--lane_projected_offset_scale", action="append", type=float)
    parser.add_argument("--min_stop_distance_m", type=float, default=2.0)
    parser.add_argument("--max_deceleration_mps2", type=float, default=3.0)
    parser.add_argument("--default_speed_mps", type=float, default=4.0)
    parser.add_argument("--jerk_progress_max_jerk_mps3", type=float, default=8.0)
    parser.add_argument("--min_progress_ratio", type=float, default=0.8)
    parser.add_argument("--progress_loss_budget_m", action="append", type=float)
    parser.add_argument("--smoothness_loss_budget", action="append", type=float)
    parser.add_argument("--command_jerk_worse_budget_mps3", type=float, default=0.0)
    parser.add_argument("--command_lateral_worse_budget_mps2", type=float, default=0.0)
    parser.add_argument("--rollout_horizon", type=int, default=3)
    parser.add_argument("--rollout_distance_loss_budget_m", type=float, default=0.10)
    parser.add_argument("--rollout_jerk_worse_budget_mps3", type=float, default=0.0)
    parser.add_argument("--rollout_lateral_worse_budget_mps2", type=float, default=0.0)
    parser.add_argument("--min_snapshot_support_rate", type=float, default=0.25)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = RouteTopologyCandidateConfig(
        generator_policy=args.generator_policy,
        red_stop_margins_m=tuple(
            args.red_stop_margin_m
            if args.red_stop_margin_m is not None
            else (2.0, 4.0, 6.0)
        ),
        backup_stop_offsets_m=tuple(
            args.backup_stop_offset_m
            if args.backup_stop_offset_m is not None
            else (0.0, 1.0)
        ),
        prefix_steps=tuple(
            args.prefix_step if args.prefix_step is not None else (3, 5, 10)
        ),
        bridge_steps=tuple(args.bridge_step if args.bridge_step is not None else (10,)),
        lane_projected_offset_scales=tuple(
            args.lane_projected_offset_scale
            if args.lane_projected_offset_scale is not None
            else (1.0, 0.5, 0.0)
        ),
        min_stop_distance_m=args.min_stop_distance_m,
        max_deceleration_mps2=args.max_deceleration_mps2,
        default_speed_mps=args.default_speed_mps,
        jerk_progress_max_jerk_mps3=args.jerk_progress_max_jerk_mps3,
        min_progress_ratio=args.min_progress_ratio,
        progress_loss_budgets_m=tuple(
            args.progress_loss_budget_m
            if args.progress_loss_budget_m is not None
            else (0.5, 1.0, 1.5)
        ),
        smoothness_loss_budgets=tuple(
            args.smoothness_loss_budget
            if args.smoothness_loss_budget is not None
            else (0.0, 0.5, 1.0)
        ),
        command_jerk_worse_budget_mps3=args.command_jerk_worse_budget_mps3,
        command_lateral_worse_budget_mps2=args.command_lateral_worse_budget_mps2,
        rollout_horizon=args.rollout_horizon,
        rollout_distance_loss_budget_m=args.rollout_distance_loss_budget_m,
        rollout_jerk_worse_budget_mps3=args.rollout_jerk_worse_budget_mps3,
        rollout_lateral_worse_budget_mps2=args.rollout_lateral_worse_budget_mps2,
        min_snapshot_support_rate=args.min_snapshot_support_rate,
    )
    report = analyze(
        snapshot_dir=args.snapshot_dir,
        route_topology_gate_json=args.route_topology_gate_json,
        diffusion_repo=args.diffusion_repo,
        reward_config_path=args.reward_config,
        device=args.device,
        label=args.label,
        config=config,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def analyze(
    *,
    snapshot_dir: Path,
    route_topology_gate_json: Path,
    diffusion_repo: Path,
    reward_config_path: Path,
    device: str = "cuda",
    label: str | None = None,
    config: RouteTopologyCandidateConfig = RouteTopologyCandidateConfig(),
) -> dict[str, Any]:
    _validate_config(config)
    readiness = _load_json(route_topology_gate_json)
    if not diffusion_repo.is_dir():
        raise FileNotFoundError(f"Missing Diffusion Planner repo: {diffusion_repo}")
    if not reward_config_path.is_file():
        raise FileNotFoundError(f"Missing reward config: {reward_config_path}")
    snapshots = sorted(Path(snapshot_dir).rglob(SNAPSHOT_GLOB))
    if not snapshots:
        raise ValueError(f"No {SNAPSHOT_GLOB} files found in {snapshot_dir}.")
    replay_module, reward_config, torch = _load_runtime(
        diffusion_repo,
        reward_config_path,
    )
    rows = []
    for snapshot_path in snapshots:
        arrays, metadata = _load_snapshot(snapshot_path)
        _validate_snapshot(arrays, metadata, snapshot_path)
        rows.append(
            _analyze_snapshot(
                snapshot_path=snapshot_path,
                arrays=arrays,
                metadata=metadata,
                replay_module=replay_module,
                reward_config=reward_config,
                torch=torch,
                device=device,
                config=config,
            )
        )
    return build_report_from_rows(
        rows,
        readiness=readiness,
        label=label,
        config=config,
        paths={
            "snapshot_dir": str(snapshot_dir),
            "route_topology_gate_json": str(route_topology_gate_json),
            "diffusion_repo": str(diffusion_repo),
            "reward_config": str(reward_config_path),
        },
    )


def build_report_from_rows(
    rows: list[dict[str, Any]],
    *,
    readiness: dict[str, Any],
    label: str | None = None,
    config: RouteTopologyCandidateConfig = RouteTopologyCandidateConfig(),
    paths: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_config(config)
    readiness_summary = _readiness_summary(readiness)
    conflicts = _readiness_conflicts(readiness)
    candidate_rows = [
        candidate
        for row in rows
        for candidate in row.get("candidate_rows", [])
    ]
    lower = [row for row in candidate_rows if row["lower_union_red"]]
    hard = [row for row in lower if row["hard_feasible"]]
    progress = [row for row in lower if row["progress_feasible"]]
    comfort = [row for row in lower if row["comfort_admissible"]]
    by_snapshot = _by_snapshot(candidate_rows)
    support = _support_summary(by_snapshot, config)
    hard_reasons = Counter(
        reason for row in lower if not row["hard_feasible"] for reason in row["hard_reasons"]
    )
    failure_classes = Counter(
        klass for row in lower for klass in route_failure_classes(row)
    )
    decision = _decision(
        readiness_summary=readiness_summary,
        conflicts=conflicts,
        support=support,
    )
    return {
        "analysis": {
            "name": "dp_camp_route_topology_candidate_screen_v1",
            "label": label,
            "role": (
                "offline route/topology-aware candidate augmentation screen "
                "over fixed current-tick snapshots"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "selection_effect": False,
            "uses_outcome_labels": False,
            "future_outcome_leakage": False,
            "candidate_generation_executed": True,
            "recomputes_dp_reward_or_red_light": True,
            "recomputes_perfect_tracker_proxies": True,
            "math_boundary": (
                "Generated candidates are deterministic functions of fixed "
                "current-tick lane_centerline, red_route_points, metadata, and "
                "the selected baseline state. This screen does not modify DP, "
                "train CAMP, use future closed-loop outcomes, or construct a "
                "Benders master/subproblem, dual, or cuts. If these diagnostics "
                "are later atomized, they must be fixed finite-candidate "
                "constants so CAMP scores remain affine a_k^T w and the "
                "simplex/CVaR/L2 robust master remains convex for that fixed "
                "finite set."
            ),
            "paths": paths or {},
        },
        "config": asdict(config),
        "source_summaries": {
            "route_topology_gate": readiness_summary,
        },
        "records": {
            "snapshots": len(rows),
            "snapshots_with_generated_candidates": sum(
                1 for row in rows if row.get("generated_count", 0) > 0
            ),
            "generated_candidate_rows": len(candidate_rows),
            "lower_union_red_rows": len(lower),
            "lower_union_red_hard_feasible_rows": len(hard),
            "lower_union_red_progress_feasible_rows": len(progress),
            "lower_union_red_comfort_admissible_rows": len(comfort),
        },
        "support_gate": support,
        "latency_ms": _summarize_latency(rows),
        "hard_reason_counts": dict(sorted(hard_reasons.items())),
        "failure_class_counts": dict(sorted(failure_classes.items())),
        "red_delta": _red_delta_summary(lower),
        "progress_comfort_delta": _progress_comfort_summary(lower),
        "top_candidates": _top_candidates(lower),
        "by_snapshot": by_snapshot,
        "final_decision": decision,
        "rows": rows,
    }


def build_route_topology_candidates(
    candidates: np.ndarray,
    *,
    lane_centerline: np.ndarray,
    red_route_points: np.ndarray,
    selected_index: int,
    current_speed_mps: float,
    dt: float,
    config: RouteTopologyCandidateConfig = RouteTopologyCandidateConfig(),
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    raw = np.asarray(candidates, dtype=np.float64)
    if raw.ndim != 3 or raw.shape[0] <= 0 or raw.shape[2] < 2:
        raise ValueError("candidates must be [K,T,D>=2].")
    if selected_index < 0 or selected_index >= raw.shape[0]:
        raise ValueError("selected_index is out of range.")
    lane = _oriented_lane(
        _finite_xy(np.asarray(lane_centerline, dtype=np.float64)),
        _finite_xy(np.asarray(red_route_points, dtype=np.float64)),
    )
    if len(lane) < 2:
        return np.empty((0, raw.shape[1], raw.shape[2]), dtype=np.float64), []
    cumulative = _cumulative_distance(lane)
    current_s = _nearest_s(lane, cumulative, np.zeros(2, dtype=np.float64))
    red_s = _first_red_s_ahead(lane, cumulative, red_route_points, current_s)
    if red_s is None:
        return np.empty((0, raw.shape[1], raw.shape[2]), dtype=np.float64), []
    max_forward = float(cumulative[-1] - current_s)
    speed = _current_speed(current_speed_mps, config.default_speed_mps)
    generated: list[np.ndarray] = []
    metadata: list[dict[str, Any]] = []
    for margin in config.red_stop_margins_m:
        for backup in config.backup_stop_offsets_m:
            stop_distance = float(red_s - current_s - margin - backup)
            if stop_distance < config.min_stop_distance_m:
                continue
            stop_distance = min(stop_distance, max_forward)
            distances = _stopping_distance_profile(
                horizon=raw.shape[1],
                dt=dt,
                stop_distance=stop_distance,
                current_speed_mps=speed,
                max_deceleration_mps2=config.max_deceleration_mps2,
            )
            target_xy = _interpolate_by_s(lane, cumulative, current_s + distances)
            if config.generator_policy == "lane_centerline_red_stop":
                candidate = raw[selected_index].copy()
                candidate[:, :2] = target_xy
                if candidate.shape[1] >= 4:
                    candidate[:, 2:4] = heading_features_from_xy(
                        target_xy,
                        fallback=raw[selected_index, :, 2:4],
                    )
                generated.append(candidate)
                metadata.append(
                    {
                        "variant": "lane_centerline_red_stop",
                        "red_stop_margin_m": float(margin),
                        "backup_stop_offset_m": float(backup),
                        "stop_distance_m": float(stop_distance),
                        "red_distance_m": float(red_s - current_s),
                        "current_speed_mps": float(speed),
                    }
                )
                continue
            if config.generator_policy == "prefix_comfort_red_stop":
                for candidate, prefix, bridge in _prefix_comfort_candidates(
                    raw[selected_index],
                    target_xy,
                    prefix_steps=config.prefix_steps,
                    bridge_steps=config.bridge_steps,
                ):
                    generated.append(candidate)
                    metadata.append(
                        {
                            "variant": "prefix_comfort_red_stop",
                            "prefix_steps": int(prefix),
                            "bridge_steps": int(bridge),
                            "red_stop_margin_m": float(margin),
                            "backup_stop_offset_m": float(backup),
                            "stop_distance_m": float(stop_distance),
                            "red_distance_m": float(red_s - current_s),
                            "current_speed_mps": float(speed),
                        }
                    )
                continue
            if config.generator_policy == "lane_projected_red_stop":
                for candidate, offset_scale in _lane_projected_red_stop_candidates(
                    raw[selected_index],
                    lane=lane,
                    cumulative=cumulative,
                    current_s=current_s,
                    stop_distances=distances,
                    offset_scales=config.lane_projected_offset_scales,
                ):
                    generated.append(candidate)
                    metadata.append(
                        {
                            "variant": "lane_projected_red_stop",
                            "lateral_offset_scale": float(offset_scale),
                            "red_stop_margin_m": float(margin),
                            "backup_stop_offset_m": float(backup),
                            "stop_distance_m": float(stop_distance),
                            "red_distance_m": float(red_s - current_s),
                            "current_speed_mps": float(speed),
                        }
                    )
                continue
            if config.generator_policy == "lane_projected_jerk_progress_red_stop":
                progress_distances = _jerk_limited_stop_distance_profile(
                    horizon=raw.shape[1],
                    dt=dt,
                    stop_distance=stop_distance,
                    current_speed_mps=speed,
                    max_deceleration_mps2=config.max_deceleration_mps2,
                    max_jerk_mps3=config.jerk_progress_max_jerk_mps3,
                )
                for candidate, offset_scale in _lane_projected_red_stop_candidates(
                    raw[selected_index],
                    lane=lane,
                    cumulative=cumulative,
                    current_s=current_s,
                    stop_distances=progress_distances,
                    offset_scales=config.lane_projected_offset_scales,
                ):
                    generated.append(candidate)
                    metadata.append(
                        {
                            "variant": "lane_projected_jerk_progress_red_stop",
                            "profile": "acceleration_jerk_limited_progress",
                            "lateral_offset_scale": float(offset_scale),
                            "red_stop_margin_m": float(margin),
                            "backup_stop_offset_m": float(backup),
                            "stop_distance_m": float(stop_distance),
                            "red_distance_m": float(red_s - current_s),
                            "current_speed_mps": float(speed),
                            "max_deceleration_mps2": float(
                                config.max_deceleration_mps2
                            ),
                            "max_jerk_mps3": float(
                                config.jerk_progress_max_jerk_mps3
                            ),
                        }
                    )
                continue
            if config.generator_policy == "prefix_lane_projected_red_stop":
                for projected, offset_scale in _lane_projected_red_stop_candidates(
                    raw[selected_index],
                    lane=lane,
                    cumulative=cumulative,
                    current_s=current_s,
                    stop_distances=distances,
                    offset_scales=config.lane_projected_offset_scales,
                ):
                    for candidate, prefix, bridge in _prefix_comfort_candidates(
                        raw[selected_index],
                        projected[:, :2],
                        prefix_steps=config.prefix_steps,
                        bridge_steps=config.bridge_steps,
                    ):
                        generated.append(candidate)
                        metadata.append(
                            {
                                "variant": "prefix_lane_projected_red_stop",
                                "prefix_steps": int(prefix),
                                "bridge_steps": int(bridge),
                                "lateral_offset_scale": float(offset_scale),
                                "red_stop_margin_m": float(margin),
                                "backup_stop_offset_m": float(backup),
                                "stop_distance_m": float(stop_distance),
                                "red_distance_m": float(red_s - current_s),
                                "current_speed_mps": float(speed),
                            }
                        )
                continue
            if config.generator_policy == "prefix_lane_projected_latest_safe_red_stop":
                latest_distances = np.full(
                    raw.shape[1],
                    float(stop_distance),
                    dtype=np.float64,
                )
                for projected, offset_scale in _lane_projected_red_stop_candidates(
                    raw[selected_index],
                    lane=lane,
                    cumulative=cumulative,
                    current_s=current_s,
                    stop_distances=latest_distances,
                    offset_scales=config.lane_projected_offset_scales,
                ):
                    for candidate, prefix, bridge in _prefix_comfort_candidates(
                        raw[selected_index],
                        projected[:, :2],
                        prefix_steps=config.prefix_steps,
                        bridge_steps=config.bridge_steps,
                    ):
                        generated.append(candidate)
                        metadata.append(
                            {
                                "variant": "prefix_lane_projected_latest_safe_red_stop",
                                "prefix_steps": int(prefix),
                                "bridge_steps": int(bridge),
                                "lateral_offset_scale": float(offset_scale),
                                "red_stop_margin_m": float(margin),
                                "backup_stop_offset_m": float(backup),
                                "stop_distance_m": float(stop_distance),
                                "red_distance_m": float(red_s - current_s),
                                "current_speed_mps": float(speed),
                            }
                        )
                continue
    if not generated:
        return np.empty((0, raw.shape[1], raw.shape[2]), dtype=np.float64), []
    return np.stack(generated), metadata


def _prefix_comfort_candidates(
    selected: np.ndarray,
    target_xy: np.ndarray,
    *,
    prefix_steps: tuple[int, ...],
    bridge_steps: tuple[int, ...],
) -> list[tuple[np.ndarray, int, int]]:
    selected_arr = np.asarray(selected, dtype=np.float64)
    target = np.asarray(target_xy, dtype=np.float64)
    if selected_arr.ndim != 2 or selected_arr.shape[1] < 2:
        raise ValueError("selected candidate must be [T,D>=2].")
    if target.shape != (selected_arr.shape[0], 2):
        raise ValueError("target_xy must be [T,2] and match selected horizon.")
    result: list[tuple[np.ndarray, int, int]] = []
    horizon = selected_arr.shape[0]
    for prefix in prefix_steps:
        if prefix < 1 or prefix >= horizon:
            continue
        for bridge in bridge_steps:
            if bridge < 0:
                continue
            candidate = selected_arr.copy()
            xy = selected_arr[:, :2].copy()
            transition = min(int(bridge), horizon - int(prefix))
            if transition == 0:
                xy[int(prefix) :] = target[int(prefix) :]
            else:
                for local_step in range(transition):
                    step = int(prefix) + local_step
                    u = float(local_step + 1) / float(transition)
                    weight = _smoothstep(u)
                    xy[step] = (1.0 - weight) * selected_arr[step, :2] + weight * target[step]
                tail_start = int(prefix) + transition
                if tail_start < horizon:
                    xy[tail_start:] = target[tail_start:]
            xy[: int(prefix)] = selected_arr[: int(prefix), :2]
            candidate[:, :2] = xy
            if candidate.shape[1] >= 4:
                candidate[:, 2:4] = heading_features_from_xy(
                    xy,
                    fallback=selected_arr[:, 2:4],
                )
            result.append((candidate, int(prefix), int(bridge)))
    return result


def _lane_projected_red_stop_candidates(
    selected: np.ndarray,
    *,
    lane: np.ndarray,
    cumulative: np.ndarray,
    current_s: float,
    stop_distances: np.ndarray,
    offset_scales: tuple[float, ...],
) -> list[tuple[np.ndarray, float]]:
    selected_arr = np.asarray(selected, dtype=np.float64)
    stop = np.asarray(stop_distances, dtype=np.float64)
    if selected_arr.ndim != 2 or selected_arr.shape[1] < 2:
        raise ValueError("selected candidate must be [T,D>=2].")
    if stop.shape != (selected_arr.shape[0],):
        raise ValueError("stop_distances must match selected horizon.")
    selected_s, selected_lateral = _project_points_to_lane(
        selected_arr[:, :2],
        lane,
        cumulative,
    )
    selected_forward = np.maximum(selected_s - float(current_s), 0.0)
    selected_forward = np.maximum.accumulate(selected_forward)
    target_forward = np.minimum(selected_forward, stop)
    target_forward = np.maximum.accumulate(np.maximum(target_forward, 0.0))
    target_s = np.clip(float(current_s) + target_forward, cumulative[0], cumulative[-1])
    center_xy, _, target_normal = _lane_frame_by_s(lane, cumulative, target_s)
    lateral = np.nan_to_num(selected_lateral, nan=0.0, posinf=0.0, neginf=0.0)
    result: list[tuple[np.ndarray, float]] = []
    for scale in offset_scales:
        offset_scale = float(scale)
        candidate = selected_arr.copy()
        xy = center_xy + offset_scale * lateral[:, None] * target_normal
        candidate[:, :2] = xy
        if candidate.shape[1] >= 4:
            candidate[:, 2:4] = heading_features_from_xy(
                xy,
                fallback=selected_arr[:, 2:4],
            )
        result.append((candidate, offset_scale))
    return result


def _analyze_snapshot(
    *,
    snapshot_path: Path,
    arrays: dict[str, np.ndarray],
    metadata: dict[str, Any],
    replay_module: Any,
    reward_config: Any,
    torch: Any,
    device: str,
    config: RouteTopologyCandidateConfig,
) -> dict[str, Any]:
    candidates = np.asarray(arrays["candidates"], dtype=np.float64)
    selected = int(metadata["selected_index"])
    t0 = time.perf_counter()
    baseline_scores = _score_trajectories(
        candidates,
        arrays=arrays,
        metadata=metadata,
        replay_module=replay_module,
        reward_config=reward_config,
        torch=torch,
        device=device,
    )
    t1 = time.perf_counter()
    baseline_tracker = _tracker_diagnostics(candidates, arrays=arrays, metadata=metadata)
    t2 = time.perf_counter()
    generated, generated_meta = build_route_topology_candidates(
        candidates,
        lane_centerline=np.asarray(arrays["lane_centerline"], dtype=np.float64),
        red_route_points=np.asarray(arrays["red_route_points"], dtype=np.float64),
        selected_index=selected,
        current_speed_mps=float(metadata.get("current_speed_mps", 0.0)),
        dt=float(metadata.get("dt", 0.1)),
        config=config,
    )
    t3 = time.perf_counter()
    generated_scores = (
        _score_trajectories(
            generated,
            arrays=arrays,
            metadata=metadata,
            replay_module=replay_module,
            reward_config=reward_config,
            torch=torch,
            device=device,
        )
        if generated.size
        else None
    )
    t4 = time.perf_counter()
    generated_tracker = (
        _tracker_diagnostics(generated, arrays=arrays, metadata=metadata)
        if generated.size
        else None
    )
    t5 = time.perf_counter()
    return _snapshot_report_row(
        snapshot_path=snapshot_path,
        arrays=arrays,
        metadata=metadata,
        generated_meta=generated_meta,
        baseline_scores=baseline_scores,
        generated_scores=generated_scores,
        baseline_tracker=baseline_tracker,
        generated_tracker=generated_tracker,
        config=config,
        timings_ms={
            "baseline_reward": (t1 - t0) * 1000.0,
            "baseline_tracker": (t2 - t1) * 1000.0,
            "candidate_build": (t3 - t2) * 1000.0,
            "generated_reward": (t4 - t3) * 1000.0,
            "generated_tracker": (t5 - t4) * 1000.0,
            "total": (t5 - t0) * 1000.0,
        },
    )


def _snapshot_report_row(
    *,
    snapshot_path: Path,
    arrays: dict[str, np.ndarray],
    metadata: dict[str, Any],
    generated_meta: list[dict[str, Any]],
    baseline_scores: dict[str, Any],
    generated_scores: dict[str, Any] | None,
    baseline_tracker: dict[str, Any],
    generated_tracker: dict[str, Any] | None,
    config: RouteTopologyCandidateConfig,
    timings_ms: dict[str, float],
) -> dict[str, Any]:
    selected = int(metadata["selected_index"])
    selected_union = float(baseline_scores["union_red_cost"][selected])
    selected_progress = float(
        reward_metric_vector(baseline_scores["reward_breakdowns"], "progress")[selected]
    )
    selected_smoothness = float(
        reward_metric_vector(baseline_scores["reward_breakdowns"], "smoothness")[selected]
    )
    selected_tracker = _selected_tracker_summary(
        baseline_tracker,
        selected,
        SimpleNamespace(rollout_horizon=config.rollout_horizon),
    )
    if generated_scores is None or generated_tracker is None:
        return {
            "snapshot_path": str(snapshot_path),
            "selection_step": int(metadata["selection_step"]),
            "selected_index": selected,
            "generated_count": 0,
            "selected_union_red": selected_union,
            "candidate_rows": [],
            "timings_ms": timings_ms,
        }
    hard_feasible, hard_reasons = reward_hard_feasibility(
        generated_scores["reward_breakdowns"]
    )
    progress_feasible, progress_reasons = reward_progress_screen(
        generated_scores["reward_breakdowns"],
        hard_feasible,
        min_progress_ratio=config.min_progress_ratio,
    )
    progress = reward_metric_vector(generated_scores["reward_breakdowns"], "progress")
    smoothness = reward_metric_vector(
        generated_scores["reward_breakdowns"],
        "smoothness",
    )
    tracker_metrics = _tracker_metrics_for_budget(
        generated_tracker,
        SimpleNamespace(rollout_horizon=config.rollout_horizon),
    )
    rows = []
    for idx, meta in enumerate(generated_meta):
        lower = float(generated_scores["union_red_cost"][idx]) < selected_union - TOL
        progress_loss = float(selected_progress - progress[idx])
        smoothness_loss = float(selected_smoothness - smoothness[idx])
        tracker_delta = _tracker_delta(tracker_metrics, selected_tracker, idx)
        row = {
            "snapshot_path": str(snapshot_path),
            "selection_step": int(metadata["selection_step"]),
            "selected_index": selected,
            "candidate_index": int(idx),
            "candidate_meta": meta,
            "selected_union_red": selected_union,
            "candidate_union_red": float(generated_scores["union_red_cost"][idx]),
            "candidate_near_red": float(generated_scores["near_red_cost"][idx]),
            "candidate_full_red": float(generated_scores["full_red_cost"][idx]),
            "lower_union_red": lower,
            "hard_feasible": bool(hard_feasible[idx]),
            "hard_reasons": list(hard_reasons[idx]),
            "progress_feasible": bool(progress_feasible[idx]),
            "progress_reasons": list(progress_reasons[idx]),
            "progress_loss_m": progress_loss,
            "smoothness_loss": smoothness_loss,
            "tracker_delta": tracker_delta,
            "comfort_admissible": _comfort_admissible(
                progress_loss=progress_loss,
                smoothness_loss=smoothness_loss,
                tracker_delta=tracker_delta,
                lower_union_red=lower,
                hard_feasible=bool(hard_feasible[idx]),
                progress_feasible=bool(progress_feasible[idx]),
                config=config,
            ),
        }
        row["failure_classes"] = route_failure_classes(row)
        rows.append(row)
    return {
        "snapshot_path": str(snapshot_path),
        "selection_step": int(metadata["selection_step"]),
        "selected_index": selected,
        "generated_count": len(rows),
        "selected_union_red": selected_union,
        "candidate_rows": rows,
        "timings_ms": timings_ms,
    }


def route_failure_classes(row: dict[str, Any]) -> list[str]:
    if not row["lower_union_red"]:
        return ["not_lower_red"]
    classes: list[str] = []
    reasons = set(row["hard_reasons"])
    if "dp_lane_crossing" in reasons:
        classes.append("route_topology_lane_invalid")
    if "dp_red_light" in reasons:
        classes.append("route_topology_red_timing_invalid")
    for reason in sorted(reasons - {"dp_lane_crossing", "dp_red_light"}):
        classes.append(f"route_topology_{reason}")
    if row["hard_feasible"] and not row["progress_feasible"]:
        classes.append("route_topology_hard_feasible_but_underprogress")
    if row["progress_feasible"] and not row["comfort_admissible"]:
        classes.extend(_comfort_failure_classes(row))
    if row["comfort_admissible"]:
        classes.append("route_topology_comfort_admissible_support")
    return classes or ["route_topology_unclassified_lower_red_failure"]


def _comfort_admissible(
    *,
    progress_loss: float,
    smoothness_loss: float,
    tracker_delta: dict[str, float],
    lower_union_red: bool,
    hard_feasible: bool,
    progress_feasible: bool,
    config: RouteTopologyCandidateConfig,
) -> bool:
    if not lower_union_red or not hard_feasible or not progress_feasible:
        return False
    tracker_ok = (
        tracker_delta["command_jerk_worse_mps3"]
        <= config.command_jerk_worse_budget_mps3 + TOL
        and tracker_delta["command_lateral_worse_mps2"]
        <= config.command_lateral_worse_budget_mps2 + TOL
        and tracker_delta["rollout_distance_loss_m"]
        <= config.rollout_distance_loss_budget_m + TOL
        and tracker_delta["rollout_jerk_worse_mps3"]
        <= config.rollout_jerk_worse_budget_mps3 + TOL
        and tracker_delta["rollout_lateral_worse_mps2"]
        <= config.rollout_lateral_worse_budget_mps2 + TOL
    )
    if not tracker_ok:
        return False
    return any(
        progress_loss <= progress_budget + TOL
        and smoothness_loss <= smoothness_budget + TOL
        for progress_budget in config.progress_loss_budgets_m
        for smoothness_budget in config.smoothness_loss_budgets
    )


def _comfort_failure_classes(row: dict[str, Any]) -> list[str]:
    delta = row["tracker_delta"]
    classes: list[str] = []
    if row["progress_loss_m"] > 1.5 + TOL:
        classes.append("route_topology_comfort_blocked_progress_loss")
    if row["smoothness_loss"] > 1.0 + TOL:
        classes.append("route_topology_comfort_blocked_smoothness_loss")
    if delta["command_jerk_worse_mps3"] > TOL:
        classes.append("route_topology_comfort_blocked_command_jerk")
    if delta["command_lateral_worse_mps2"] > TOL:
        classes.append("route_topology_comfort_blocked_command_lateral")
    if delta["rollout_distance_loss_m"] > 0.10 + TOL:
        classes.append("route_topology_comfort_blocked_rollout_distance")
    if delta["rollout_jerk_worse_mps3"] > TOL:
        classes.append("route_topology_comfort_blocked_rollout_jerk")
    if delta["rollout_lateral_worse_mps2"] > TOL:
        classes.append("route_topology_comfort_blocked_rollout_lateral")
    return classes or ["route_topology_comfort_blocked_unknown_budget"]


def _oriented_lane(lane: np.ndarray, red: np.ndarray) -> np.ndarray:
    if len(lane) < 2:
        return lane
    forward = _orientation_score(lane, red)
    reverse = _orientation_score(lane[::-1], red)
    return lane if forward >= reverse else lane[::-1].copy()


def _orientation_score(lane: np.ndarray, red: np.ndarray) -> float:
    cumulative = _cumulative_distance(lane)
    current_s = _nearest_s(lane, cumulative, np.zeros(2, dtype=np.float64))
    red_s = _first_red_s_ahead(lane, cumulative, red, current_s)
    forward_span = float(cumulative[-1] - current_s)
    if red_s is None:
        return -forward_span
    return 1000.0 + float(red_s - current_s) + forward_span * 1e-3


def _first_red_s_ahead(
    lane: np.ndarray,
    cumulative: np.ndarray,
    red_route_points: np.ndarray,
    current_s: float,
) -> float | None:
    red = _finite_xy(np.asarray(red_route_points, dtype=np.float64))
    if len(red) == 0:
        return None
    values = []
    for point in red:
        s_value = _nearest_s(lane, cumulative, point)
        if s_value > current_s + TOL:
            values.append(float(s_value))
    if not values:
        return None
    return min(values)


def _stopping_distance_profile(
    *,
    horizon: int,
    dt: float,
    stop_distance: float,
    current_speed_mps: float,
    max_deceleration_mps2: float,
) -> np.ndarray:
    if horizon <= 0:
        return np.empty(0, dtype=np.float64)
    times = (np.arange(horizon, dtype=np.float64) + 1.0) * float(dt)
    speed = max(float(current_speed_mps), 0.0)
    stop_distance = max(float(stop_distance), 0.0)
    if speed <= TOL:
        return np.full(horizon, stop_distance, dtype=np.float64)
    required_deceleration = speed * speed / max(2.0 * stop_distance, TOL)
    deceleration = min(required_deceleration, float(max_deceleration_mps2))
    distances = speed * times - 0.5 * deceleration * times * times
    distances = np.maximum.accumulate(np.maximum(distances, 0.0))
    return np.minimum(distances, stop_distance)


def _jerk_limited_stop_distance_profile(
    *,
    horizon: int,
    dt: float,
    stop_distance: float,
    current_speed_mps: float,
    max_deceleration_mps2: float,
    max_jerk_mps3: float,
) -> np.ndarray:
    if horizon <= 0:
        return np.empty(0, dtype=np.float64)
    step_s = max(float(dt), TOL)
    cap = max(float(stop_distance), 0.0)
    speed = max(float(current_speed_mps), 0.0)
    max_decel = max(float(max_deceleration_mps2), 0.0)
    max_jerk = max(float(max_jerk_mps3), TOL)
    position = 0.0
    acceleration = 0.0
    distances = np.zeros(horizon, dtype=np.float64)
    for index in range(horizon):
        remaining = max(cap - position, 0.0)
        if remaining <= TOL or speed <= TOL:
            distances[index:] = position
            break
        required_decel = speed * speed / max(2.0 * remaining, TOL)
        target_acceleration = -min(required_decel, max_decel)
        max_delta_acceleration = max_jerk * step_s
        acceleration = float(
            np.clip(
                target_acceleration,
                acceleration - max_delta_acceleration,
                acceleration + max_delta_acceleration,
            )
        )
        acceleration = min(0.0, max(-max_decel, acceleration))
        next_speed = max(0.0, speed + acceleration * step_s)
        step_distance = max(0.0, 0.5 * (speed + next_speed) * step_s)
        if step_distance >= remaining:
            position = cap
            speed = 0.0
        else:
            position += step_distance
            speed = next_speed
        distances[index] = min(position, cap)
    return np.minimum(np.maximum.accumulate(distances), cap)


def _smoothstep(value: float) -> float:
    clipped = min(1.0, max(0.0, float(value)))
    return clipped * clipped * (3.0 - 2.0 * clipped)


def _interpolate_by_s(
    lane: np.ndarray,
    cumulative: np.ndarray,
    targets: np.ndarray,
) -> np.ndarray:
    target = np.clip(np.asarray(targets, dtype=np.float64), cumulative[0], cumulative[-1])
    x = np.interp(target, cumulative, lane[:, 0])
    y = np.interp(target, cumulative, lane[:, 1])
    return np.column_stack([x, y])


def _lane_frame_by_s(
    lane: np.ndarray,
    cumulative: np.ndarray,
    targets: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    target = np.clip(np.asarray(targets, dtype=np.float64), cumulative[0], cumulative[-1])
    xy = np.zeros((target.size, 2), dtype=np.float64)
    tangent = np.zeros((target.size, 2), dtype=np.float64)
    normal = np.zeros((target.size, 2), dtype=np.float64)
    for idx, value in enumerate(target):
        segment = int(np.searchsorted(cumulative, value, side="right") - 1)
        segment = max(0, min(segment, len(lane) - 2))
        start = lane[segment]
        end = lane[segment + 1]
        delta = end - start
        length = float(np.linalg.norm(delta))
        if length <= TOL:
            unit = np.array([1.0, 0.0], dtype=np.float64)
            xy[idx] = start
        else:
            unit = delta / length
            ratio = float((value - cumulative[segment]) / length)
            ratio = min(1.0, max(0.0, ratio))
            xy[idx] = start + ratio * delta
        tangent[idx] = unit
        normal[idx] = np.array([-unit[1], unit[0]], dtype=np.float64)
    return xy, tangent, normal


def _project_points_to_lane(
    points: np.ndarray,
    lane: np.ndarray,
    cumulative: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    raw = np.asarray(points, dtype=np.float64)
    if raw.ndim < 2 or raw.shape[-1] < 2:
        raise ValueError("points must be [N,D>=2].")
    pts = raw[..., :2].reshape(-1, 2)
    if not np.isfinite(pts).all():
        raise ValueError("points must be finite [N,D>=2].")
    best_dist2 = np.full(pts.shape[0], np.inf, dtype=np.float64)
    best_s = np.full(pts.shape[0], cumulative[0], dtype=np.float64)
    best_lateral = np.zeros(pts.shape[0], dtype=np.float64)
    for index in range(len(lane) - 1):
        start = lane[index]
        end = lane[index + 1]
        delta = end - start
        length2 = float(np.dot(delta, delta))
        if length2 <= TOL:
            continue
        ratio = np.clip(((pts - start) @ delta) / length2, 0.0, 1.0)
        projection = start + ratio[:, None] * delta
        residual = pts - projection
        dist2 = np.sum(residual * residual, axis=1)
        update = dist2 < best_dist2
        if not np.any(update):
            continue
        length = float(np.sqrt(length2))
        unit = delta / length
        normal = np.array([-unit[1], unit[0]], dtype=np.float64)
        best_dist2[update] = dist2[update]
        best_s[update] = cumulative[index] + ratio[update] * length
        best_lateral[update] = residual[update] @ normal
    if np.isinf(best_dist2).any():
        raise ValueError("lane must contain at least one nonzero segment.")
    return best_s, best_lateral


def _nearest_s(lane: np.ndarray, cumulative: np.ndarray, point: np.ndarray) -> float:
    distances = np.linalg.norm(lane - np.asarray(point, dtype=np.float64), axis=1)
    return float(cumulative[int(np.argmin(distances))])


def _cumulative_distance(points: np.ndarray) -> np.ndarray:
    if len(points) == 0:
        return np.empty(0, dtype=np.float64)
    if len(points) == 1:
        return np.zeros(1, dtype=np.float64)
    steps = np.linalg.norm(np.diff(points, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(steps)])


def _finite_xy(points: np.ndarray) -> np.ndarray:
    if points.ndim == 1:
        points = points.reshape(-1, points.shape[0])
    if points.ndim < 2 or points.shape[-1] < 2:
        return np.empty((0, 2), dtype=np.float64)
    xy = np.asarray(points[..., :2], dtype=np.float64).reshape(-1, 2)
    return xy[np.isfinite(xy).all(axis=1)]


def _current_speed(value: float, default: float) -> float:
    try:
        speed = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not np.isfinite(speed) or speed <= 0.0:
        return float(default)
    return speed


def _by_snapshot(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["snapshot_path"], []).append(row)
    result = []
    for path, group in sorted(grouped.items()):
        lower = [row for row in group if row["lower_union_red"]]
        result.append(
            {
                "snapshot_path": path,
                "selection_step": int(group[0]["selection_step"]),
                "candidate_rows": len(group),
                "lower_union_red": len(lower),
                "lower_union_red_hard_feasible": int(
                    sum(row["hard_feasible"] for row in lower)
                ),
                "lower_union_red_progress_feasible": int(
                    sum(row["progress_feasible"] for row in lower)
                ),
                "lower_union_red_comfort_admissible": int(
                    sum(row["comfort_admissible"] for row in lower)
                ),
                "failure_class_counts": dict(
                    sorted(
                        Counter(
                            klass
                            for row in lower
                            for klass in row["failure_classes"]
                        ).items()
                    )
                ),
            }
        )
    return result


def _support_summary(
    by_snapshot: list[dict[str, Any]],
    config: RouteTopologyCandidateConfig,
) -> dict[str, Any]:
    denominator = max(1, len(by_snapshot))
    hard_snapshots = int(
        sum(row["lower_union_red_hard_feasible"] > 0 for row in by_snapshot)
    )
    comfort_snapshots = int(
        sum(row["lower_union_red_comfort_admissible"] > 0 for row in by_snapshot)
    )
    hard_rate = hard_snapshots / denominator
    comfort_rate = comfort_snapshots / denominator
    return {
        "snapshots": len(by_snapshot),
        "snapshots_with_lower_union_red_hard_feasible": hard_snapshots,
        "snapshots_with_lower_union_red_comfort_admissible": comfort_snapshots,
        "min_snapshot_support_rate": float(config.min_snapshot_support_rate),
        "hard_feasible_snapshot_support_rate": hard_rate,
        "comfort_admissible_snapshot_support_rate": comfort_rate,
        "hard_feasible_snapshot_support_pass": (
            hard_rate >= float(config.min_snapshot_support_rate)
        ),
        "comfort_admissible_snapshot_support_pass": (
            comfort_rate >= float(config.min_snapshot_support_rate)
        ),
    }


def _decision(
    *,
    readiness_summary: dict[str, Any],
    conflicts: list[str],
    support: dict[str, Any],
) -> dict[str, Any]:
    passed = bool(
        support["hard_feasible_snapshot_support_pass"]
        and support["comfort_admissible_snapshot_support_pass"]
    )
    if conflicts or readiness_summary["status"] != READINESS_READY:
        status = SOURCE_CONFLICT_STATUS
        next_step = "Fix or rerun the route/topology readiness gate before candidate screening."
    elif passed:
        status = READY_STATUS
        next_step = (
            "Run a separate no-leak offline selector/counterfactual screen over "
            "the augmented fixed candidate set; do not run replay yet."
        )
    else:
        status = REJECT_STATUS
        next_step = (
            "Reject this route/topology candidate construction family for replay "
            "or online promotion; inspect failure classes before designing a "
            "materially different generator."
        )
    return {
        "status": status,
        "offline_selector_screen_authorized": status == READY_STATUS,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "source_authorization_conflicts": conflicts,
        "next_step": next_step,
    }


def _readiness_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    aggregate = report.get("snapshot_aggregate") or {}
    return {
        "status": decision.get("status"),
        "offline_candidate_augmentation_screen_authorized": bool(
            decision.get("offline_candidate_augmentation_screen_authorized")
        ),
        "ready_snapshot_rate": _first_number(aggregate.get("ready_snapshot_rate")),
        "candidate_lane_p95_max_m": _first_number(
            aggregate.get("candidate_lane_p95_max_m")
        ),
        "red_lane_p95_max_m": _first_number(aggregate.get("red_lane_p95_max_m")),
    }


def _readiness_conflicts(report: dict[str, Any]) -> list[str]:
    decision = report.get("final_decision") or {}
    conflicts = []
    if decision.get("status") != READINESS_READY:
        conflicts.append("route_topology_gate:not_ready")
    if not decision.get("offline_candidate_augmentation_screen_authorized"):
        conflicts.append("route_topology_gate:augmentation_not_authorized")
    for key in (
        "online_selector_authorized",
        "closed_loop_smoke_authorized",
        "full36_authorized",
        "formal_seeds_authorized",
        "camp_retraining_authorized",
        "dp_modification_authorized",
    ):
        if decision.get(key):
            conflicts.append(f"route_topology_gate:{key}")
    return conflicts


def _summarize_latency(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = (
        "baseline_reward",
        "baseline_tracker",
        "candidate_build",
        "generated_reward",
        "generated_tracker",
        "total",
    )
    return {
        key: _summary(row["timings_ms"].get(key) for row in rows)
        for key in keys
    }


def _red_delta_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "selected_union_red": _summary(row["selected_union_red"] for row in rows),
        "candidate_union_red": _summary(row["candidate_union_red"] for row in rows),
        "selected_to_candidate_reduction": _summary(
            row["selected_union_red"] - row["candidate_union_red"] for row in rows
        ),
    }


def _progress_comfort_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "progress_loss_m": _summary(row["progress_loss_m"] for row in rows),
        "smoothness_loss": _summary(row["smoothness_loss"] for row in rows),
        "command_jerk_worse_mps3": _summary(
            row["tracker_delta"]["command_jerk_worse_mps3"] for row in rows
        ),
        "command_lateral_worse_mps2": _summary(
            row["tracker_delta"]["command_lateral_worse_mps2"] for row in rows
        ),
        "rollout_distance_loss_m": _summary(
            row["tracker_delta"]["rollout_distance_loss_m"] for row in rows
        ),
        "rollout_jerk_worse_mps3": _summary(
            row["tracker_delta"]["rollout_jerk_worse_mps3"] for row in rows
        ),
        "rollout_lateral_worse_mps2": _summary(
            row["tracker_delta"]["rollout_lateral_worse_mps2"] for row in rows
        ),
    }


def _top_candidates(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            not row["comfort_admissible"],
            not row["hard_feasible"],
            row["candidate_union_red"],
            row["progress_loss_m"],
        ),
    )
    keys = (
        "snapshot_path",
        "selection_step",
        "candidate_index",
        "candidate_meta",
        "selected_union_red",
        "candidate_union_red",
        "hard_feasible",
        "hard_reasons",
        "progress_feasible",
        "progress_loss_m",
        "smoothness_loss",
        "tracker_delta",
        "comfort_admissible",
        "failure_classes",
    )
    return [{key: row[key] for key in keys} for row in sorted_rows[:limit]]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    records = report["records"]
    support = report["support_gate"]
    lines = [
        "# Route/Topology Candidate Augmentation Screen",
        "",
        "This is an offline fixed-snapshot screen. It does not run replay, train CAMP, change DP, or promote an online selector.",
        "",
        "## Verdict",
        "",
        f"- Status: `{decision['status']}`",
        f"- Next step: {decision['next_step']}",
        f"- Offline selector screen authorized: `{decision['offline_selector_screen_authorized']}`",
        f"- Closed-loop smoke authorized: `{decision['closed_loop_smoke_authorized']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        "",
        "## Counts",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in records.items():
        lines.append(f"| `{key}` | {_fmt(value)} |")
    lines.extend(
        [
            "",
            "## Snapshot Support",
            "",
            f"- Required snapshot support rate: `{support['min_snapshot_support_rate']}`",
            f"- Hard-feasible support rate: `{support['hard_feasible_snapshot_support_rate']:.6f}`",
            f"- Comfort-admissible support rate: `{support['comfort_admissible_snapshot_support_rate']:.6f}`",
            "",
            "## Failure Classes",
            "",
            "| Class | Count |",
            "| --- | ---: |",
        ]
    )
    for key, value in report["failure_class_counts"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(
        [
            "",
            "## Hard Reasons",
            "",
            f"`{report['hard_reason_counts']}`",
            "",
            "## Deltas",
            "",
            f"- Red delta summary: `{report['red_delta']}`",
            f"- Progress/comfort summary: `{report['progress_comfort_delta']}`",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _summary(values: Any) -> dict[str, float | int | None]:
    finite = [
        float(value)
        for value in values
        if value is not None and np.isfinite(float(value))
    ]
    if not finite:
        return {
            "count": 0,
            "mean": None,
            "min": None,
            "p50": None,
            "p95": None,
            "max": None,
        }
    arr = np.asarray(finite, dtype=np.float64)
    return {
        "count": int(arr.size),
        "mean": float(np.mean(arr)),
        "min": float(np.min(arr)),
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(np.max(arr)),
    }


def _first_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _fmt(value: Any) -> str:
    if value is None:
        return "`null`"
    if isinstance(value, bool):
        return f"`{str(value).lower()}`"
    if isinstance(value, float):
        return f"`{value:.6f}`"
    return f"`{value}`"


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def _validate_config(config: RouteTopologyCandidateConfig) -> None:
    if config.generator_policy not in {
        "lane_centerline_red_stop",
        "prefix_comfort_red_stop",
        "lane_projected_red_stop",
        "lane_projected_jerk_progress_red_stop",
        "prefix_lane_projected_red_stop",
        "prefix_lane_projected_latest_safe_red_stop",
    }:
        raise ValueError("invalid generator_policy.")
    for value in config.red_stop_margins_m:
        if not np.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError("red_stop_margins_m must be nonnegative.")
    for value in config.backup_stop_offsets_m:
        if not np.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError("backup_stop_offsets_m must be nonnegative.")
    for value in config.prefix_steps:
        if int(value) < 1:
            raise ValueError("prefix_steps must be positive.")
    for value in config.bridge_steps:
        if int(value) < 0:
            raise ValueError("bridge_steps must be nonnegative.")
    for value in config.lane_projected_offset_scales:
        if not np.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
            raise ValueError("lane_projected_offset_scales must be in [0,1].")
    for name in (
        "min_stop_distance_m",
        "max_deceleration_mps2",
        "default_speed_mps",
        "jerk_progress_max_jerk_mps3",
        "command_jerk_worse_budget_mps3",
        "command_lateral_worse_budget_mps2",
        "rollout_distance_loss_budget_m",
        "rollout_jerk_worse_budget_mps3",
        "rollout_lateral_worse_budget_mps2",
    ):
        value = float(getattr(config, name))
        if not np.isfinite(value) or value < 0.0:
            raise ValueError(f"{name} must be nonnegative.")
    if float(config.jerk_progress_max_jerk_mps3) <= 0.0:
        raise ValueError("jerk_progress_max_jerk_mps3 must be positive.")
    if not 0.0 <= float(config.min_progress_ratio) <= 1.0:
        raise ValueError("min_progress_ratio must be in [0,1].")
    if not 0.0 <= float(config.min_snapshot_support_rate) <= 1.0:
        raise ValueError("min_snapshot_support_rate must be in [0,1].")
    if int(config.rollout_horizon) <= 0:
        raise ValueError("rollout_horizon must be positive.")
    for value in config.progress_loss_budgets_m:
        if not np.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError("progress_loss_budgets_m must be nonnegative.")
    for value in config.smoothness_loss_budgets:
        if not np.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError("smoothness_loss_budgets must be nonnegative.")


if __name__ == "__main__":
    main()
