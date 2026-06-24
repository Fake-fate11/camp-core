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
REMEDIATION_PROFILE_OFF = "off"
REMEDIATION_PROFILE_SUPPORT_V1 = "lane_projected_jerk_progress_support_v1"
REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1 = (
    "lane_station_jerk_limited_red_stop_support_v1"
)
REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2 = (
    "lane_red_hard_feasible_jerk_lateral_support_v2"
)
REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3 = (
    "lane_red_hard_feasible_comfort_first_support_v3"
)
REMEDIATION_PROFILE_MATERIAL_SUPPORT_V4 = (
    "lane_red_hard_feasible_comfort_first_materialized_support_v4"
)
GENERATOR_POLICY_MATERIAL_SUPPORT = (
    "lane_station_jerk_limited_red_stop_material_support"
)
GENERATOR_POLICY_MATERIAL_SUPPORT_V2 = (
    "lane_red_hard_feasible_jerk_lateral_material_support"
)
GENERATOR_POLICY_MATERIAL_SUPPORT_V3 = (
    "lane_red_hard_feasible_comfort_first_material_support"
)
GENERATOR_POLICY_MATERIAL_SUPPORT_V4 = (
    "lane_red_hard_feasible_comfort_first_materialized_support"
)
MATERIAL_SUPPORT_POLICY_PROFILES = {
    GENERATOR_POLICY_MATERIAL_SUPPORT: REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1,
    GENERATOR_POLICY_MATERIAL_SUPPORT_V2: REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2,
    GENERATOR_POLICY_MATERIAL_SUPPORT_V3: REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3,
    GENERATOR_POLICY_MATERIAL_SUPPORT_V4: REMEDIATION_PROFILE_MATERIAL_SUPPORT_V4,
}


@dataclass(frozen=True)
class RouteTopologyCandidateConfig:
    generator_policy: str = "lane_centerline_red_stop"
    default_off_remediation_profile: str = REMEDIATION_PROFILE_OFF
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
    max_remediation_candidates: int = 12


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
            "comfort_first_lane_projected_red_stop",
            "negative_support_coverage_first_lane_projected_red_stop",
            GENERATOR_POLICY_MATERIAL_SUPPORT,
            GENERATOR_POLICY_MATERIAL_SUPPORT_V2,
            GENERATOR_POLICY_MATERIAL_SUPPORT_V3,
            GENERATOR_POLICY_MATERIAL_SUPPORT_V4,
            "prefix_lane_projected_red_stop",
            "prefix_lane_projected_latest_safe_red_stop",
        ),
        default="lane_centerline_red_stop",
    )
    parser.add_argument(
        "--default_off_remediation_profile",
        choices=(
            REMEDIATION_PROFILE_OFF,
            REMEDIATION_PROFILE_SUPPORT_V1,
            REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1,
            REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2,
            REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3,
            REMEDIATION_PROFILE_MATERIAL_SUPPORT_V4,
        ),
        default=REMEDIATION_PROFILE_OFF,
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
    parser.add_argument("--max_remediation_candidates", type=int, default=12)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = RouteTopologyCandidateConfig(
        generator_policy=args.generator_policy,
        default_off_remediation_profile=args.default_off_remediation_profile,
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
        max_remediation_candidates=args.max_remediation_candidates,
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
    by_snapshot = _by_snapshot(candidate_rows, config=config)
    support = _support_summary(by_snapshot, config)
    hard_reasons = Counter(
        reason for row in lower if not row["hard_feasible"] for reason in row["hard_reasons"]
    )
    failure_classes = Counter(
        klass for row in lower for klass in route_failure_classes(row, config=config)
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
        "effective_comfort_budgets": _effective_comfort_budgets(config),
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
    if _material_support_profile_failure(config) is not None:
        return np.empty((0, raw.shape[1], raw.shape[2]), dtype=np.float64), []
    if _requires_current_tick_scalar_evidence(config) and (
        _current_tick_scalar_failure_reason(current_speed_mps, dt) is not None
    ):
        return np.empty((0, raw.shape[1], raw.shape[2]), dtype=np.float64), []
    if _requires_finite_selected_candidate_evidence(config) and (
        _selected_candidate_state_failure_reason(raw, selected_index) is not None
    ):
        return np.empty((0, raw.shape[1], raw.shape[2]), dtype=np.float64), []
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
            raw_stop_distance = float(red_s - current_s - margin - backup)
            coverage_partition = "standard_min_stop_distance"
            if raw_stop_distance < config.min_stop_distance_m:
                if _requires_material_hard_precheck(config):
                    continue
                if not (
                    _is_comfort_first_remediation_policy(config)
                    or _is_negative_support_followup_policy(config)
                    or _is_material_support_policy(config)
                ):
                    continue
                if raw_stop_distance <= TOL:
                    continue
                if _is_negative_support_followup_policy(config):
                    coverage_partition = (
                        "coverage_first_close_red_current_tick_fallback"
                    )
                elif _is_material_support_policy(config):
                    coverage_partition = "material_close_red_current_tick_fallback"
                else:
                    coverage_partition = "close_red_current_tick_fallback"
            stop_distance = raw_stop_distance
            stop_distance = min(stop_distance, max_forward)
            material_hard_precheck = None
            if _requires_material_hard_precheck(config):
                material_hard_precheck = _lane_red_hard_feasibility_precheck(
                    stop_distance=stop_distance,
                    red_distance=float(red_s - current_s),
                    max_forward=max_forward,
                    current_speed_mps=speed,
                    config=config,
                )
                if not material_hard_precheck["passed"]:
                    continue
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
            if config.generator_policy == "comfort_first_lane_projected_red_stop":
                progress_distances = _jerk_limited_stop_distance_profile(
                    horizon=raw.shape[1],
                    dt=dt,
                    stop_distance=stop_distance,
                    current_speed_mps=speed,
                    max_deceleration_mps2=config.max_deceleration_mps2,
                    max_jerk_mps3=config.jerk_progress_max_jerk_mps3,
                )
                budget_reached = False
                for projected, offset_scale in _lane_projected_red_stop_candidates(
                    raw[selected_index],
                    lane=lane,
                    cumulative=cumulative,
                    current_s=current_s,
                    stop_distances=progress_distances,
                    offset_scales=config.lane_projected_offset_scales,
                ):
                    if budget_reached:
                        break
                    for candidate, prefix, bridge in _prefix_comfort_candidates(
                        raw[selected_index],
                        projected[:, :2],
                        prefix_steps=config.prefix_steps,
                        bridge_steps=config.bridge_steps,
                    ):
                        if len(generated) >= int(config.max_remediation_candidates):
                            budget_reached = True
                            break
                        candidate = _monotonic_lane_station_candidate(
                            candidate,
                            lane=lane,
                            cumulative=cumulative,
                            current_s=current_s,
                            heading_fallback=raw[selected_index, :, 2:4],
                        )
                        generated.append(candidate)
                        metadata.append(
                            {
                                "variant": "comfort_first_lane_projected_red_stop",
                                "profile": "comfort_first_jerk_limited_lane_station",
                                "red_stop_distance_partition": coverage_partition,
                                "prefix_steps": int(prefix),
                                "bridge_steps": int(bridge),
                                "lateral_offset_scale": float(offset_scale),
                                "red_stop_margin_m": float(margin),
                                "backup_stop_offset_m": float(backup),
                                "raw_stop_distance_m": float(raw_stop_distance),
                                "stop_distance_m": float(stop_distance),
                                "red_distance_m": float(red_s - current_s),
                                "current_speed_mps": float(speed),
                                "max_deceleration_mps2": float(
                                    config.max_deceleration_mps2
                                ),
                                "max_jerk_mps3": float(
                                    config.jerk_progress_max_jerk_mps3
                                ),
                                "candidate_budget_cap": int(
                                    config.max_remediation_candidates
                                ),
                                "current_tick_features_only": True,
                            }
                        )
                continue
            if (
                config.generator_policy
                == "negative_support_coverage_first_lane_projected_red_stop"
            ):
                progress_distances = _jerk_limited_stop_distance_profile(
                    horizon=raw.shape[1],
                    dt=dt,
                    stop_distance=stop_distance,
                    current_speed_mps=speed,
                    max_deceleration_mps2=config.max_deceleration_mps2,
                    max_jerk_mps3=config.jerk_progress_max_jerk_mps3,
                )
                for projected, offset_scale in _lane_projected_red_stop_candidates(
                    raw[selected_index],
                    lane=lane,
                    cumulative=cumulative,
                    current_s=current_s,
                    stop_distances=progress_distances,
                    offset_scales=_negative_support_offset_scales(config),
                ):
                    if len(generated) >= int(config.max_remediation_candidates):
                        break
                    candidate = _monotonic_lane_station_candidate(
                        projected,
                        lane=lane,
                        cumulative=cumulative,
                        current_s=current_s,
                        heading_fallback=raw[selected_index, :, 2:4],
                    )
                    generated.append(candidate)
                    metadata.append(
                        {
                            "variant": (
                                "negative_support_coverage_first_lane_projected_"
                                "red_stop"
                            ),
                            "profile": (
                                "coverage_first_hard_comfort_jerk_limited_lane_"
                                "station"
                            ),
                            "red_stop_distance_partition": coverage_partition,
                            "fail_closed_partition": (
                                "fallback_ready"
                                if coverage_partition
                                == "coverage_first_close_red_current_tick_fallback"
                                else "standard_ready"
                            ),
                            "hard_feasibility_floor_current_tick": True,
                            "comfort_after_hard_progress": True,
                            "lateral_offset_scale": float(offset_scale),
                            "red_stop_margin_m": float(margin),
                            "backup_stop_offset_m": float(backup),
                            "raw_stop_distance_m": float(raw_stop_distance),
                            "stop_distance_m": float(stop_distance),
                            "red_distance_m": float(red_s - current_s),
                            "current_speed_mps": float(speed),
                            "max_deceleration_mps2": float(
                                config.max_deceleration_mps2
                            ),
                            "max_jerk_mps3": float(
                                config.jerk_progress_max_jerk_mps3
                            ),
                            "candidate_budget_cap": int(
                                config.max_remediation_candidates
                            ),
                            "current_tick_features_only": True,
                            "remediation_descriptor_payload": (
                                _command_jerk_descriptor_payload(
                                    candidate,
                                    lane=lane,
                                    cumulative=cumulative,
                                    current_s=current_s,
                                    dt=dt,
                                    config=config,
                                )
                            ),
                        }
                    )
                continue
            if _is_material_support_policy(config):
                progress_distances = _jerk_limited_stop_distance_profile(
                    horizon=raw.shape[1],
                    dt=dt,
                    stop_distance=stop_distance,
                    current_speed_mps=speed,
                    max_deceleration_mps2=config.max_deceleration_mps2,
                    max_jerk_mps3=config.jerk_progress_max_jerk_mps3,
                )
                for (
                    candidate,
                    offset_scale,
                    prefix,
                    bridge,
                ) in _lane_station_material_support_candidates(
                    raw[selected_index],
                    lane=lane,
                    cumulative=cumulative,
                    current_s=current_s,
                    stop_distances=progress_distances,
                    offset_scales=_material_support_offset_scales(config),
                    prefix_steps=config.prefix_steps,
                    bridge_steps=config.bridge_steps,
                ):
                    if len(generated) >= int(config.max_remediation_candidates):
                        break
                    profile = _material_support_profile(config)
                    material_v2_enabled = _is_material_support_v2_policy(config)
                    material_v3_enabled = _is_material_support_v3_policy(config)
                    material_v4_enabled = _is_material_support_v4_policy(config)
                    candidate = _monotonic_lane_station_candidate(
                        candidate,
                        lane=lane,
                        cumulative=cumulative,
                        current_s=current_s,
                        heading_fallback=raw[selected_index, :, 2:4],
                    )
                    descriptor_payload = _material_support_descriptor_payload(
                        candidate,
                        selected=raw[selected_index],
                        lane=lane,
                        cumulative=cumulative,
                        current_s=current_s,
                        dt=dt,
                        config=config,
                        hard_precheck=material_hard_precheck,
                    )
                    material_v3_comfort_precheck = None
                    if material_v3_enabled:
                        material_v3_comfort_precheck = (
                            _material_support_v3_comfort_precheck(
                                descriptor_payload
                            )
                        )
                        if not material_v3_comfort_precheck["passed"]:
                            continue
                    if material_v4_enabled:
                        material_v3_comfort_precheck = (
                            _material_support_v3_comfort_precheck(
                                descriptor_payload
                            )
                        )
                    generated.append(candidate)
                    row = {
                        "variant": config.generator_policy,
                        "profile": profile,
                        "material_support_family": (
                            "lane_red_hard_feasible_comfort_first_materialized"
                            if material_v4_enabled
                            else "lane_red_hard_feasible_comfort_first"
                            if material_v3_enabled
                            else "lane_red_hard_feasible_jerk_lateral"
                            if material_v2_enabled
                            else "lane_station_jerk_limited_red_stop"
                        ),
                        "red_stop_distance_partition": coverage_partition,
                        "fail_closed_partition": (
                            "material_fallback_ready"
                            if coverage_partition
                            == "material_close_red_current_tick_fallback"
                            else "material_standard_ready"
                        ),
                        "candidate0_preserved": True,
                        "dp_rows_preserved": True,
                        "append_after_existing_candidate_count": int(raw.shape[0]),
                        "source_candidate_index": int(selected_index),
                        "hard_progress_comfort_gate_passthrough": True,
                        "lateral_heading_continuity_projection": True,
                        "red_timing_progress_guard": True,
                        "lateral_offset_scale": float(offset_scale),
                        "prefix_steps": int(prefix),
                        "bridge_steps": int(bridge),
                        "red_stop_margin_m": float(margin),
                        "backup_stop_offset_m": float(backup),
                        "raw_stop_distance_m": float(raw_stop_distance),
                        "stop_distance_m": float(stop_distance),
                        "red_distance_m": float(red_s - current_s),
                        "current_speed_mps": float(speed),
                        "max_deceleration_mps2": float(
                            config.max_deceleration_mps2
                        ),
                        "max_jerk_mps3": float(config.jerk_progress_max_jerk_mps3),
                        "candidate_budget_cap": int(
                            config.max_remediation_candidates
                        ),
                        "current_tick_features_only": True,
                        "uses_outcome_labels": False,
                        "future_outcome_leakage": False,
                        "remediation_descriptor_payload": descriptor_payload,
                    }
                    if _requires_material_hard_precheck(config):
                        row.update(
                            {
                                "lane_red_hard_feasibility_precheck": True,
                                "hard_feasibility_precheck_passed": bool(
                                    material_hard_precheck["passed"]
                                ),
                                "hard_precheck_margins": (
                                    material_hard_precheck["margins"]
                                ),
                                "no_gate_relaxation": True,
                                "jerk_limited_stop_and_creep_profiles": True,
                            }
                        )
                    if material_v3_enabled:
                        row.update(
                            {
                                "comfort_first_profile_precheck": True,
                                "comfort_first_precheck_passed": True,
                                "comfort_precheck_margins": (
                                    material_v3_comfort_precheck["margins"]
                                ),
                                "lane_corridor_continuity_tightening": True,
                                "stop_creep_progress_balance": True,
                                "diagnostic_descriptor_payload_v3_report_only": True,
                            }
                        )
                    if material_v4_enabled:
                        row.update(
                            {
                                "comfort_first_profile_precheck": True,
                                "comfort_first_precheck_report_only": True,
                                "comfort_first_precheck_passed": bool(
                                    material_v3_comfort_precheck["passed"]
                                ),
                                "comfort_precheck_margins": (
                                    material_v3_comfort_precheck["margins"]
                                ),
                                "lane_corridor_continuity_tightening": True,
                                "stop_creep_progress_balance": True,
                                "diagnostic_descriptor_payload_v4_report_only": True,
                                "candidate_materialization_v4": True,
                                "materialized_before_support_gate": True,
                                "comfort_budget_relaxation": False,
                            }
                        )
                    metadata.append(row)
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


def route_topology_candidate_construction_diagnostics(
    candidates: np.ndarray,
    *,
    lane_centerline: np.ndarray,
    red_route_points: np.ndarray,
    selected_index: int,
    current_speed_mps: float,
    dt: float,
    config: RouteTopologyCandidateConfig = RouteTopologyCandidateConfig(),
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {
        "generator_policy": str(config.generator_policy),
        "selected_index": int(selected_index),
        "current_speed_mps": _json_number(current_speed_mps),
        "dt_s": _json_number(dt),
        "min_stop_distance_m": _json_number(config.min_stop_distance_m),
        "construction_status": "fail_closed",
        "failure_reason": None,
    }
    raw = np.asarray(candidates, dtype=np.float64)
    if raw.ndim != 3 or raw.shape[0] <= 0 or raw.shape[2] < 2:
        diagnostics.update(
            {
                "failure_reason": "candidate_tensor_invalid",
                "candidate_count": int(raw.shape[0]) if raw.ndim >= 1 else 0,
                "horizon": int(raw.shape[1]) if raw.ndim >= 2 else 0,
            }
        )
        _add_negative_support_fail_closed_partition(diagnostics)
        return diagnostics
    diagnostics.update(
        {
            "candidate_count": int(raw.shape[0]),
            "horizon": int(raw.shape[1]),
            "state_dim": int(raw.shape[2]),
        }
    )
    if selected_index < 0 or selected_index >= raw.shape[0]:
        diagnostics["failure_reason"] = "selected_index_out_of_range"
        _add_negative_support_fail_closed_partition(diagnostics)
        return diagnostics
    profile_failure = _material_support_profile_failure(config)
    diagnostics["material_support_profile_required"] = (
        _is_material_support_policy(config)
        or config.default_off_remediation_profile
        in (
            REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1,
            REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2,
            REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3,
            REMEDIATION_PROFILE_MATERIAL_SUPPORT_V4,
        )
    )
    diagnostics["material_support_profile_evidence"] = profile_failure is None
    if profile_failure:
        diagnostics["failure_reason"] = profile_failure
        _add_negative_support_fail_closed_partition(diagnostics)
        return diagnostics
    scalar_failure = _current_tick_scalar_failure_reason(current_speed_mps, dt)
    diagnostics["requires_current_tick_scalar_evidence"] = (
        _requires_current_tick_scalar_evidence(config)
    )
    diagnostics["current_tick_scalar_evidence"] = scalar_failure is None
    if diagnostics["requires_current_tick_scalar_evidence"] and scalar_failure:
        diagnostics["failure_reason"] = scalar_failure
        _add_negative_support_fail_closed_partition(diagnostics)
        return diagnostics
    selected_state_failure = _selected_candidate_state_failure_reason(
        raw,
        selected_index,
    )
    diagnostics["requires_finite_selected_candidate_evidence"] = (
        _requires_finite_selected_candidate_evidence(config)
    )
    diagnostics["finite_selected_candidate_evidence"] = selected_state_failure is None
    if diagnostics["requires_finite_selected_candidate_evidence"] and selected_state_failure:
        diagnostics["failure_reason"] = selected_state_failure
        _add_negative_support_fail_closed_partition(diagnostics)
        return diagnostics
    lane = _oriented_lane(
        _finite_xy(np.asarray(lane_centerline, dtype=np.float64)),
        _finite_xy(np.asarray(red_route_points, dtype=np.float64)),
    )
    red = _finite_xy(np.asarray(red_route_points, dtype=np.float64))
    diagnostics.update(
        {
            "lane_point_count": int(len(lane)),
            "red_route_point_count": int(len(red)),
        }
    )
    if len(lane) < 2:
        diagnostics["failure_reason"] = "lane_geometry_invalid"
        _add_negative_support_fail_closed_partition(diagnostics)
        return diagnostics
    cumulative = _cumulative_distance(lane)
    current_s = _nearest_s(lane, cumulative, np.zeros(2, dtype=np.float64))
    red_s = _first_red_s_ahead(lane, cumulative, red, current_s)
    diagnostics["current_s_m"] = _json_number(current_s)
    if red_s is None:
        diagnostics["failure_reason"] = "red_route_ahead_missing"
        diagnostics["red_route_ahead"] = False
        _add_negative_support_fail_closed_partition(diagnostics)
        return diagnostics
    red_distance = float(red_s - current_s)
    max_forward = float(cumulative[-1] - current_s)
    feasible_windows = 0
    fallback_windows = 0
    hard_precheck_windows = 0
    hard_precheck_failures: Counter[str] = Counter()
    min_stop_distance = None
    max_stop_distance = None
    min_fallback_distance = None
    max_fallback_distance = None
    for margin in config.red_stop_margins_m:
        for backup in config.backup_stop_offsets_m:
            stop_distance = float(red_s - current_s - margin - backup)
            if stop_distance < config.min_stop_distance_m:
                if (
                    (
                        _is_comfort_first_remediation_policy(config)
                        or _is_negative_support_followup_policy(config)
                        or _is_material_support_v1_policy(config)
                    )
                    and stop_distance > TOL
                ):
                    fallback_windows += 1
                    min_fallback_distance = (
                        stop_distance
                        if min_fallback_distance is None
                        else min(min_fallback_distance, stop_distance)
                    )
                    max_fallback_distance = (
                        stop_distance
                        if max_fallback_distance is None
                        else max(max_fallback_distance, stop_distance)
                    )
                continue
            stop_distance = min(stop_distance, max_forward)
            feasible_windows += 1
            min_stop_distance = (
                stop_distance
                if min_stop_distance is None
                else min(min_stop_distance, stop_distance)
            )
            max_stop_distance = (
                stop_distance
                if max_stop_distance is None
                else max(max_stop_distance, stop_distance)
            )
            if _requires_material_hard_precheck(config):
                precheck = _lane_red_hard_feasibility_precheck(
                    stop_distance=stop_distance,
                    red_distance=red_distance,
                    max_forward=max_forward,
                    current_speed_mps=float(current_speed_mps),
                    config=config,
                )
                if precheck["passed"]:
                    hard_precheck_windows += 1
                else:
                    hard_precheck_failures[str(precheck["failure_reason"])] += 1
    diagnostics.update(
        {
            "red_route_ahead": True,
            "red_distance_m": _json_number(red_distance),
            "max_forward_m": _json_number(max_forward),
            "feasible_stop_windows": int(feasible_windows),
            "fallback_stop_windows": int(fallback_windows),
            "min_feasible_stop_distance_m": _json_number(min_stop_distance),
            "max_feasible_stop_distance_m": _json_number(max_stop_distance),
            "min_fallback_stop_distance_m": _json_number(min_fallback_distance),
            "max_fallback_stop_distance_m": _json_number(max_fallback_distance),
            "candidate_budget_cap": int(config.max_remediation_candidates),
        }
    )
    if _requires_material_hard_precheck(config):
        diagnostics.update(
            {
                "lane_red_hard_feasibility_precheck_required": True,
                "lane_red_hard_feasibility_precheck_passed": (
                    hard_precheck_windows > 0
                ),
                "lane_red_hard_feasible_windows": int(hard_precheck_windows),
                "lane_red_hard_precheck_failure_counts": dict(
                    sorted(hard_precheck_failures.items())
                ),
                "no_gate_relaxation": True,
            }
        )
    if _is_material_support_comfort_first_policy(config):
        diagnostics.update(
            {
                "comfort_first_profile_precheck_required": True,
                "diagnostic_descriptor_payload_v3_report_only": (
                    _is_material_support_v3_policy(config)
                ),
                "diagnostic_descriptor_payload_v4_report_only": (
                    _is_material_support_v4_policy(config)
                ),
                "lane_corridor_continuity_tightening": True,
                "stop_creep_progress_balance": True,
            }
        )
        if _is_material_support_v4_policy(config):
            diagnostics["candidate_materialization_v4"] = True
            diagnostics["comfort_first_precheck_report_only"] = True
    if feasible_windows <= 0:
        if _is_comfort_first_remediation_policy(config) and fallback_windows > 0:
            diagnostics["construction_status"] = "ready"
            diagnostics["failure_reason"] = None
            diagnostics[
                "red_stop_distance_partition"
            ] = "close_red_current_tick_fallback"
            diagnostics["current_tick_features_only"] = True
            return diagnostics
        if _is_negative_support_followup_policy(config) and fallback_windows > 0:
            diagnostics["construction_status"] = "ready"
            diagnostics["failure_reason"] = None
            diagnostics[
                "red_stop_distance_partition"
            ] = "coverage_first_close_red_current_tick_fallback"
            diagnostics["fail_closed_partition"] = "fallback_ready"
            diagnostics["current_tick_features_only"] = True
            return diagnostics
        if _is_material_support_policy(config) and fallback_windows > 0:
            diagnostics["construction_status"] = "ready"
            diagnostics["failure_reason"] = None
            diagnostics[
                "red_stop_distance_partition"
            ] = "material_close_red_current_tick_fallback"
            diagnostics["fail_closed_partition"] = "material_fallback_ready"
            diagnostics["candidate0_preserved"] = True
            diagnostics["dp_rows_preserved"] = True
            diagnostics["current_tick_features_only"] = True
            return diagnostics
        diagnostics["failure_reason"] = "red_stop_distance_window"
        _add_negative_support_fail_closed_partition(diagnostics)
        return diagnostics
    if _requires_material_hard_precheck(config) and hard_precheck_windows <= 0:
        diagnostics["failure_reason"] = (
            next(iter(hard_precheck_failures), None)
            or "lane_red_hard_feasibility_precheck_failed"
        )
        _add_negative_support_fail_closed_partition(diagnostics)
        return diagnostics
    diagnostics["construction_status"] = "ready"
    diagnostics["red_stop_distance_partition"] = "standard_min_stop_distance"
    if _is_negative_support_followup_policy(config):
        diagnostics["fail_closed_partition"] = "standard_ready"
        diagnostics["current_tick_features_only"] = True
    if _is_material_support_policy(config):
        diagnostics["fail_closed_partition"] = "material_standard_ready"
        diagnostics["candidate0_preserved"] = True
        diagnostics["dp_rows_preserved"] = True
        diagnostics["current_tick_features_only"] = True
        if _requires_material_hard_precheck(config):
            diagnostics["hard_feasibility_precheck_passed"] = True
            diagnostics["hard_progress_comfort_gate_passthrough"] = True
            diagnostics["lateral_heading_continuity_projection"] = True
        if _is_material_support_comfort_first_policy(config):
            diagnostics["comfort_first_precheck_passed"] = True
            diagnostics["diagnostic_descriptor_payload_v3_report_only"] = (
                _is_material_support_v3_policy(config)
            )
            diagnostics["diagnostic_descriptor_payload_v4_report_only"] = (
                _is_material_support_v4_policy(config)
            )
            if _is_material_support_v4_policy(config):
                diagnostics["candidate_materialization_v4"] = True
                diagnostics["comfort_first_precheck_report_only"] = True
    return diagnostics


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


def _monotonic_lane_station_candidate(
    candidate: np.ndarray,
    *,
    lane: np.ndarray,
    cumulative: np.ndarray,
    current_s: float,
    heading_fallback: np.ndarray,
) -> np.ndarray:
    result = np.asarray(candidate, dtype=np.float64).copy()
    if result.ndim != 2 or result.shape[1] < 2:
        raise ValueError("candidate must be [T,D>=2].")
    station, lateral = _project_points_to_lane(result[:, :2], lane, cumulative)
    forward = np.maximum.accumulate(np.maximum(station - float(current_s), 0.0))
    target_s = np.clip(float(current_s) + forward, cumulative[0], cumulative[-1])
    center_xy, _, normal = _lane_frame_by_s(lane, cumulative, target_s)
    result[:, :2] = center_xy + lateral[:, None] * normal
    if result.shape[1] >= 4:
        result[:, 2:4] = heading_features_from_xy(
            result[:, :2],
            fallback=heading_fallback,
        )
    return result


def _negative_support_offset_scales(
    config: RouteTopologyCandidateConfig,
) -> tuple[float, ...]:
    values = [0.0, *[float(value) for value in config.lane_projected_offset_scales]]
    unique: list[float] = []
    for value in sorted(values, key=lambda item: (abs(item), item)):
        if not any(abs(value - existing) <= TOL for existing in unique):
            unique.append(value)
    return tuple(unique)


def _material_support_offset_scales(
    config: RouteTopologyCandidateConfig,
) -> tuple[float, ...]:
    values = [0.0, *[float(value) for value in config.lane_projected_offset_scales]]
    unique: list[float] = []
    for value in sorted(values, key=lambda item: (abs(item), item)):
        if not any(abs(value - existing) <= TOL for existing in unique):
            unique.append(value)
    return tuple(unique)


def _lane_station_material_support_candidates(
    selected: np.ndarray,
    *,
    lane: np.ndarray,
    cumulative: np.ndarray,
    current_s: float,
    stop_distances: np.ndarray,
    offset_scales: tuple[float, ...],
    prefix_steps: tuple[int, ...],
    bridge_steps: tuple[int, ...],
) -> list[tuple[np.ndarray, float, int, int]]:
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
    center_xy, _, normal = _lane_frame_by_s(lane, cumulative, target_s)
    lateral = np.nan_to_num(selected_lateral, nan=0.0, posinf=0.0, neginf=0.0)
    horizon = selected_arr.shape[0]
    result: list[tuple[np.ndarray, float, int, int]] = []
    for scale in offset_scales:
        offset_scale = float(scale)
        for prefix in prefix_steps:
            if prefix < 1 or prefix >= horizon:
                continue
            for bridge in bridge_steps:
                if bridge < 0:
                    continue
                transition = min(int(bridge), horizon - int(prefix))
                envelope = np.full(horizon, offset_scale, dtype=np.float64)
                envelope[: int(prefix)] = 1.0
                if transition > 0:
                    for local_step in range(transition):
                        step = int(prefix) + local_step
                        u = float(local_step + 1) / float(transition)
                        envelope[step] = (
                            (1.0 - _smoothstep(u)) + _smoothstep(u) * offset_scale
                        )
                candidate = selected_arr.copy()
                xy = center_xy + (lateral * envelope)[:, None] * normal
                xy[: int(prefix)] = selected_arr[: int(prefix), :2]
                candidate[:, :2] = xy
                if candidate.shape[1] >= 4:
                    candidate[:, 2:4] = heading_features_from_xy(
                        xy,
                        fallback=selected_arr[:, 2:4],
                    )
                result.append((candidate, offset_scale, int(prefix), int(bridge)))
    return result


def _command_jerk_descriptor_payload(
    candidate: np.ndarray,
    *,
    lane: np.ndarray,
    cumulative: np.ndarray,
    current_s: float,
    dt: float,
    config: RouteTopologyCandidateConfig,
) -> dict[str, Any]:
    station, lateral = _project_points_to_lane(candidate[:, :2], lane, cumulative)
    forward = np.maximum.accumulate(np.maximum(station - float(current_s), 0.0))
    if forward.size < 4 or not np.isfinite(forward).all():
        command_jerk_abs_max = 0.0
    else:
        step_s = max(float(dt), TOL)
        speed = np.diff(forward, prepend=forward[0]) / step_s
        acceleration = np.diff(speed, prepend=speed[0]) / step_s
        jerk = np.diff(acceleration, prepend=acceleration[0]) / step_s
        command_jerk_abs_max = float(np.max(np.abs(jerk)))
    lateral = np.nan_to_num(lateral, nan=0.0, posinf=0.0, neginf=0.0)
    if lateral.size < 3 or not np.isfinite(lateral).all():
        rollout_lateral_abs_max = 0.0
        lateral_acceleration = np.zeros(0, dtype=np.float64)
    else:
        step_s = max(float(dt), TOL)
        lateral_velocity = np.diff(lateral, prepend=lateral[0]) / step_s
        lateral_acceleration = (
            np.diff(lateral_velocity, prepend=lateral_velocity[0]) / step_s
        )
        rollout_lateral_abs_max = float(np.max(np.abs(lateral_acceleration)))
    hinge = max(
        0.0,
        command_jerk_abs_max - float(config.command_jerk_worse_budget_mps3),
    )
    rollout_lateral_hinge = max(
        0.0,
        rollout_lateral_abs_max - float(config.rollout_lateral_worse_budget_mps2),
    )
    command_jerk_signed_pos = command_jerk_abs_max
    command_jerk_signed_neg = 0.0
    rollout_lateral_signed_pos = (
        max(float(np.max(lateral_acceleration)), 0.0)
        if lateral_acceleration.size
        else 0.0
    )
    rollout_lateral_signed_neg = (
        max(float(-np.min(lateral_acceleration)), 0.0)
        if lateral_acceleration.size
        else 0.0
    )
    return {
        "payload_role": "report_only_current_tick_descriptor",
        "descriptor_family": "command_jerk_hinge",
        "followup_payload_role": "report_only",
        "followup_descriptor_family": "command_jerk_rollout_lateral_zero_comfort_gap",
        "top_comfort_blocker": "route_topology_comfort_blocked_command_jerk",
        "secondary_comfort_blocker": "route_topology_comfort_blocked_rollout_lateral",
        "current_tick_features_only": True,
        "candidate_local": True,
        "uses_outcome_labels": False,
        "future_outcome_leakage": False,
        "nonnegative_or_hinge_signed_split_legal": True,
        "command_jerk_abs_max_mps3": _json_number(command_jerk_abs_max),
        "command_jerk_hinge_mps3": _json_number(hinge),
        "command_jerk_signed_pos_mps3": _json_number(command_jerk_signed_pos),
        "command_jerk_signed_neg_mps3": _json_number(command_jerk_signed_neg),
        "rollout_lateral_abs_max_mps2": _json_number(rollout_lateral_abs_max),
        "rollout_lateral_hinge_mps2": _json_number(rollout_lateral_hinge),
        "rollout_lateral_signed_pos_mps2": _json_number(
            rollout_lateral_signed_pos
        ),
        "rollout_lateral_signed_neg_mps2": _json_number(
            rollout_lateral_signed_neg
        ),
        "score_contract": "score_k(w)=a_k^T w",
        "convex_master_contract": "simplex/CVaR/L2 unchanged",
        "candidate_mutation": False,
        "score_mutation": False,
        "selected_index_mutation": False,
        "fallback_mutation": False,
        "online_selector_feature": False,
        "deployed_atom_schema_change": False,
        "dp_import": False,
        "reward_recompute": False,
        "tracker_recompute": False,
    }


def _material_support_descriptor_payload(
    candidate: np.ndarray,
    *,
    selected: np.ndarray,
    lane: np.ndarray,
    cumulative: np.ndarray,
    current_s: float,
    dt: float,
    config: RouteTopologyCandidateConfig,
    hard_precheck: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _command_jerk_descriptor_payload(
        candidate,
        lane=lane,
        cumulative=cumulative,
        current_s=current_s,
        dt=dt,
        config=config,
    )
    step_s = max(float(dt), TOL)
    xy = np.asarray(candidate[:, :2], dtype=np.float64)
    velocity = np.diff(xy, axis=0, prepend=xy[[0]]) / step_s
    acceleration = np.diff(velocity, axis=0, prepend=velocity[[0]]) / step_s
    jerk = np.diff(acceleration, axis=0, prepend=acceleration[[0]]) / step_s
    rollout_jerk_abs_max = (
        float(np.max(np.linalg.norm(jerk, axis=1))) if jerk.size else 0.0
    )
    station, lateral = _project_points_to_lane(xy, lane, cumulative)
    selected_station, _ = _project_points_to_lane(
        np.asarray(selected[:, :2], dtype=np.float64),
        lane,
        cumulative,
    )
    forward = np.maximum.accumulate(np.maximum(station - float(current_s), 0.0))
    selected_forward = np.maximum.accumulate(
        np.maximum(selected_station - float(current_s), 0.0)
    )
    progress_loss = max(
        0.0,
        float(selected_forward[-1] - forward[-1])
        if selected_forward.size and forward.size
        else 0.0,
    )
    progress_budget = _max_finite_budget(config.progress_loss_budgets_m)
    progress_hinge = max(0.0, progress_loss - float(progress_budget or 0.0))
    lateral = np.nan_to_num(lateral, nan=0.0, posinf=0.0, neginf=0.0)
    lateral_pos = max(float(np.max(lateral)), 0.0) if lateral.size else 0.0
    lateral_neg = max(float(-np.min(lateral)), 0.0) if lateral.size else 0.0
    lane_residual_abs_max = float(np.max(np.abs(lateral))) if lateral.size else 0.0
    material_v2_enabled = _is_material_support_v2_policy(config)
    material_v3_enabled = _is_material_support_v3_policy(config)
    material_v4_enabled = _is_material_support_v4_policy(config)
    material_hard_precheck_enabled = _requires_material_hard_precheck(config)
    profile = _material_support_profile(config)
    lane_corridor_hinge = max(0.0, lane_residual_abs_max - 0.25)
    rollout_jerk_hinge = max(
        0.0,
        rollout_jerk_abs_max - float(config.rollout_jerk_worse_budget_mps3),
    )
    smoothness_proxy_hinge = max(
        float(payload.get("command_jerk_hinge_mps3") or 0.0),
        rollout_jerk_hinge,
    )
    payload.update(
        {
            "descriptor_family": (
                "lane_red_hard_feasible_comfort_first_materialized_support"
                if material_v4_enabled
                else "lane_red_hard_feasible_comfort_first_material_support"
                if material_v3_enabled
                else "lane_red_hard_feasible_jerk_lateral_material_support"
                if material_v2_enabled
                else "lane_station_jerk_limited_red_stop_material_support"
            ),
            "material_descriptor_family": (
                "hard_feasibility_comfort_first_materialized_lane_corridor_progress_v4"
                if material_v4_enabled
                else "hard_feasibility_comfort_first_lane_corridor_progress_v3"
                if material_v3_enabled
                else "hard_feasibility_command_rollout_jerk_lateral_progress_v2"
                if material_v2_enabled
                else "command_rollout_jerk_lateral_progress_lane_projection"
            ),
            "material_support_profile": profile,
            "candidate0_preserved": True,
            "dp_rows_preserved": True,
            "runtime_atom_promotion": False,
            "rollout_jerk_abs_max_mps3": _json_number(rollout_jerk_abs_max),
            "rollout_jerk_hinge_mps3": _json_number(rollout_jerk_hinge),
            "lateral_error_signed_pos_m": _json_number(lateral_pos),
            "lateral_error_signed_neg_m": _json_number(lateral_neg),
            "lane_projection_residual_abs_max_m": _json_number(
                lane_residual_abs_max
            ),
            "lane_projection_residual_hinge_m": _json_number(
                max(0.0, lane_residual_abs_max)
            ),
            "lane_corridor_hinge_m": _json_number(lane_corridor_hinge),
            "progress_retention_loss_m": _json_number(progress_loss),
            "progress_retention_hinge_m": _json_number(progress_hinge),
            "smoothness_proxy_hinge": _json_number(smoothness_proxy_hinge),
            "nonnegative_descriptor_channels": True,
            "hinge_signed_split_channels": True,
            "affine_score_compatible": True,
        }
    )
    if material_hard_precheck_enabled:
        margins = dict((hard_precheck or {}).get("margins", {}))
        payload.update(
            {
                "diagnostic_descriptor_payload_v2": material_v2_enabled,
                "diagnostic_descriptor_payload_v3": material_v3_enabled,
                "diagnostic_descriptor_payload_v4": material_v4_enabled,
                "lane_red_hard_feasibility_precheck": True,
                "hard_feasibility_precheck_passed": bool(
                    (hard_precheck or {}).get("passed", False)
                ),
                "hard_feasibility_margin_hinges": True,
                "hard_feasibility_red_ahead_margin_m": _json_number(
                    margins.get("red_ahead_margin_m")
                ),
                "hard_feasibility_stop_distance_margin_m": _json_number(
                    margins.get("stop_distance_margin_m")
                ),
                "hard_feasibility_forward_range_margin_m": _json_number(
                    margins.get("forward_range_margin_m")
                ),
                "hard_feasibility_kinematic_deceleration_margin_mps2": (
                    _json_number(
                        margins.get("kinematic_deceleration_margin_mps2")
                    )
                ),
                "no_gate_relaxation": True,
                "positive_support_before_training_required": True,
            }
        )
    if material_v3_enabled or material_v4_enabled:
        payload.update(
            {
                "comfort_first_profile_precheck": True,
                "diagnostic_descriptor_payload_v3_report_only": material_v3_enabled,
                "diagnostic_descriptor_payload_v4_report_only": material_v4_enabled,
                "lane_corridor_continuity_tightening": True,
                "stop_creep_progress_balance": True,
                "comfort_budget_relaxation": False,
                "atom_promotion": False,
                "online_selector_promotion": False,
            }
        )
    if material_v4_enabled:
        payload.update(
            {
                "candidate_materialization_v4": True,
                "comfort_first_precheck_report_only": True,
                "materialized_before_support_gate": True,
                "generated_rows_accounting_required": True,
                "candidate_rows_accounting_required": True,
            }
        )
    return payload


def _material_support_v3_comfort_precheck(
    descriptor_payload: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "command_jerk_hinge_mps3": descriptor_payload.get(
            "command_jerk_hinge_mps3"
        ),
        "rollout_jerk_hinge_mps3": descriptor_payload.get(
            "rollout_jerk_hinge_mps3"
        ),
        "rollout_lateral_hinge_mps2": descriptor_payload.get(
            "rollout_lateral_hinge_mps2"
        ),
        "lane_corridor_hinge_m": descriptor_payload.get("lane_corridor_hinge_m"),
        "progress_retention_hinge_m": descriptor_payload.get(
            "progress_retention_hinge_m"
        ),
        "smoothness_proxy_hinge": descriptor_payload.get("smoothness_proxy_hinge"),
    }
    failures = [
        key
        for key, value in checks.items()
        if value is None or not np.isfinite(float(value)) or float(value) > TOL
    ]
    return {
        "passed": not failures,
        "failure_reason": failures[0] if failures else None,
        "failed_checks": failures,
        "margins": {key: _json_number(0.0 if value is None else value) for key, value in checks.items()},
        "current_tick_features_only": True,
        "uses_outcome_labels": False,
        "future_outcome_leakage": False,
    }


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
    construction_diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=np.asarray(arrays["lane_centerline"], dtype=np.float64),
        red_route_points=np.asarray(arrays["red_route_points"], dtype=np.float64),
        selected_index=selected,
        current_speed_mps=float(metadata.get("current_speed_mps", 0.0)),
        dt=float(metadata.get("dt", 0.1)),
        config=config,
    )
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
        construction_diagnostics=construction_diagnostics,
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
    construction_diagnostics: dict[str, Any] | None = None,
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
            "candidate_construction_diagnostics": construction_diagnostics or {},
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
        row["failure_classes"] = route_failure_classes(row, config=config)
        rows.append(row)
    return {
        "snapshot_path": str(snapshot_path),
        "selection_step": int(metadata["selection_step"]),
        "selected_index": selected,
        "generated_count": len(rows),
        "selected_union_red": selected_union,
        "candidate_construction_diagnostics": construction_diagnostics or {},
        "candidate_rows": rows,
        "timings_ms": timings_ms,
    }


def route_failure_classes(
    row: dict[str, Any],
    *,
    config: RouteTopologyCandidateConfig = RouteTopologyCandidateConfig(),
) -> list[str]:
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
        classes.extend(_comfort_failure_classes(row, config=config))
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
    budgets = _effective_comfort_budgets(config)
    tracker_ok = (
        tracker_delta["command_jerk_worse_mps3"]
        <= budgets["command_jerk_worse_budget_mps3"] + TOL
        and tracker_delta["command_lateral_worse_mps2"]
        <= budgets["command_lateral_worse_budget_mps2"] + TOL
        and tracker_delta["rollout_distance_loss_m"]
        <= budgets["rollout_distance_loss_budget_m"] + TOL
        and tracker_delta["rollout_jerk_worse_mps3"]
        <= budgets["rollout_jerk_worse_budget_mps3"] + TOL
        and tracker_delta["rollout_lateral_worse_mps2"]
        <= budgets["rollout_lateral_worse_budget_mps2"] + TOL
    )
    if not tracker_ok:
        return False
    return any(
        progress_loss <= progress_budget + TOL
        and smoothness_loss <= smoothness_budget + TOL
        for progress_budget in budgets["progress_loss_budgets_m"]
        for smoothness_budget in budgets["smoothness_loss_budgets"]
    )


def _comfort_failure_classes(
    row: dict[str, Any],
    *,
    config: RouteTopologyCandidateConfig = RouteTopologyCandidateConfig(),
) -> list[str]:
    delta = row["tracker_delta"]
    classes: list[str] = []
    budgets = _effective_comfort_budgets(config)
    progress_budget = _max_finite_budget(budgets["progress_loss_budgets_m"])
    smoothness_budget = _max_finite_budget(budgets["smoothness_loss_budgets"])
    if (
        progress_budget is not None
        and row["progress_loss_m"] > progress_budget + TOL
    ):
        classes.append("route_topology_comfort_blocked_progress_loss")
    if (
        smoothness_budget is not None
        and row["smoothness_loss"] > smoothness_budget + TOL
    ):
        classes.append("route_topology_comfort_blocked_smoothness_loss")
    if (
        delta["command_jerk_worse_mps3"]
        > budgets["command_jerk_worse_budget_mps3"] + TOL
    ):
        classes.append("route_topology_comfort_blocked_command_jerk")
    if (
        delta["command_lateral_worse_mps2"]
        > budgets["command_lateral_worse_budget_mps2"] + TOL
    ):
        classes.append("route_topology_comfort_blocked_command_lateral")
    if (
        delta["rollout_distance_loss_m"]
        > budgets["rollout_distance_loss_budget_m"] + TOL
    ):
        classes.append("route_topology_comfort_blocked_rollout_distance")
    if (
        delta["rollout_jerk_worse_mps3"]
        > budgets["rollout_jerk_worse_budget_mps3"] + TOL
    ):
        classes.append("route_topology_comfort_blocked_rollout_jerk")
    if (
        delta["rollout_lateral_worse_mps2"]
        > budgets["rollout_lateral_worse_budget_mps2"] + TOL
    ):
        classes.append("route_topology_comfort_blocked_rollout_lateral")
    return classes or ["route_topology_comfort_blocked_unknown_budget"]


def _effective_comfort_budgets(
    config: RouteTopologyCandidateConfig,
) -> dict[str, Any]:
    if config.default_off_remediation_profile == REMEDIATION_PROFILE_OFF:
        return {
            "default_off_remediation_profile": REMEDIATION_PROFILE_OFF,
            "progress_loss_budgets_m": config.progress_loss_budgets_m,
            "smoothness_loss_budgets": config.smoothness_loss_budgets,
            "command_jerk_worse_budget_mps3": config.command_jerk_worse_budget_mps3,
            "command_lateral_worse_budget_mps2": (
                config.command_lateral_worse_budget_mps2
            ),
            "rollout_distance_loss_budget_m": config.rollout_distance_loss_budget_m,
            "rollout_jerk_worse_budget_mps3": config.rollout_jerk_worse_budget_mps3,
            "rollout_lateral_worse_budget_mps2": (
                config.rollout_lateral_worse_budget_mps2
            ),
        }
    if config.default_off_remediation_profile not in {
        REMEDIATION_PROFILE_SUPPORT_V1,
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1,
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2,
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3,
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V4,
    }:
        raise ValueError("default_off_remediation_profile is invalid.")
    if config.default_off_remediation_profile in {
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3,
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V4,
    }:
        return {
            "default_off_remediation_profile": config.default_off_remediation_profile,
            "progress_loss_budgets_m": config.progress_loss_budgets_m,
            "smoothness_loss_budgets": config.smoothness_loss_budgets,
            "command_jerk_worse_budget_mps3": config.command_jerk_worse_budget_mps3,
            "command_lateral_worse_budget_mps2": (
                config.command_lateral_worse_budget_mps2
            ),
            "rollout_distance_loss_budget_m": config.rollout_distance_loss_budget_m,
            "rollout_jerk_worse_budget_mps3": config.rollout_jerk_worse_budget_mps3,
            "rollout_lateral_worse_budget_mps2": (
                config.rollout_lateral_worse_budget_mps2
            ),
        }
    return {
        "default_off_remediation_profile": config.default_off_remediation_profile,
        "progress_loss_budgets_m": _budgets_with_floor(
            config.progress_loss_budgets_m,
            2.0,
        ),
        "smoothness_loss_budgets": _budgets_with_floor(
            config.smoothness_loss_budgets,
            1.5,
        ),
        "command_jerk_worse_budget_mps3": max(
            float(config.command_jerk_worse_budget_mps3),
            0.05,
        ),
        "command_lateral_worse_budget_mps2": max(
            float(config.command_lateral_worse_budget_mps2),
            0.05,
        ),
        "rollout_distance_loss_budget_m": config.rollout_distance_loss_budget_m,
        "rollout_jerk_worse_budget_mps3": config.rollout_jerk_worse_budget_mps3,
        "rollout_lateral_worse_budget_mps2": max(
            float(config.rollout_lateral_worse_budget_mps2),
            1.0,
        ),
    }


def _budgets_with_floor(values: tuple[float, ...], floor: float) -> tuple[float, ...]:
    normalized = tuple(float(value) for value in values)
    if any(value >= float(floor) - TOL for value in normalized):
        return normalized
    return (*normalized, float(floor))


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


def _requires_current_tick_scalar_evidence(
    config: RouteTopologyCandidateConfig,
) -> bool:
    return config.generator_policy in {
        "lane_projected_jerk_progress_red_stop",
        "comfort_first_lane_projected_red_stop",
        "negative_support_coverage_first_lane_projected_red_stop",
        GENERATOR_POLICY_MATERIAL_SUPPORT,
        GENERATOR_POLICY_MATERIAL_SUPPORT_V2,
        GENERATOR_POLICY_MATERIAL_SUPPORT_V3,
        GENERATOR_POLICY_MATERIAL_SUPPORT_V4,
    }


def _requires_finite_selected_candidate_evidence(
    config: RouteTopologyCandidateConfig,
) -> bool:
    return config.generator_policy in {
        "lane_projected_jerk_progress_red_stop",
        "comfort_first_lane_projected_red_stop",
        "negative_support_coverage_first_lane_projected_red_stop",
        GENERATOR_POLICY_MATERIAL_SUPPORT,
        GENERATOR_POLICY_MATERIAL_SUPPORT_V2,
        GENERATOR_POLICY_MATERIAL_SUPPORT_V3,
        GENERATOR_POLICY_MATERIAL_SUPPORT_V4,
    }


def _is_comfort_first_remediation_policy(
    config: RouteTopologyCandidateConfig,
) -> bool:
    return config.generator_policy == "comfort_first_lane_projected_red_stop"


def _is_negative_support_followup_policy(
    config: RouteTopologyCandidateConfig,
) -> bool:
    return (
        config.generator_policy
        == "negative_support_coverage_first_lane_projected_red_stop"
    )


def _is_material_support_policy(config: RouteTopologyCandidateConfig) -> bool:
    return config.generator_policy in MATERIAL_SUPPORT_POLICY_PROFILES


def _is_material_support_v1_policy(config: RouteTopologyCandidateConfig) -> bool:
    return config.generator_policy == GENERATOR_POLICY_MATERIAL_SUPPORT


def _is_material_support_v2_policy(config: RouteTopologyCandidateConfig) -> bool:
    return config.generator_policy == GENERATOR_POLICY_MATERIAL_SUPPORT_V2


def _is_material_support_v3_policy(config: RouteTopologyCandidateConfig) -> bool:
    return config.generator_policy == GENERATOR_POLICY_MATERIAL_SUPPORT_V3


def _is_material_support_v4_policy(config: RouteTopologyCandidateConfig) -> bool:
    return config.generator_policy == GENERATOR_POLICY_MATERIAL_SUPPORT_V4


def _is_material_support_comfort_first_policy(
    config: RouteTopologyCandidateConfig,
) -> bool:
    return _is_material_support_v3_policy(config) or _is_material_support_v4_policy(
        config
    )


def _requires_material_hard_precheck(config: RouteTopologyCandidateConfig) -> bool:
    return (
        _is_material_support_v2_policy(config)
        or _is_material_support_v3_policy(config)
        or _is_material_support_v4_policy(config)
    )


def _material_support_profile(config: RouteTopologyCandidateConfig) -> str:
    return MATERIAL_SUPPORT_POLICY_PROFILES.get(
        config.generator_policy,
        str(config.default_off_remediation_profile),
    )


def _material_support_profile_failure(
    config: RouteTopologyCandidateConfig,
) -> str | None:
    required_profile = MATERIAL_SUPPORT_POLICY_PROFILES.get(config.generator_policy)
    profile_enabled = config.default_off_remediation_profile in set(
        MATERIAL_SUPPORT_POLICY_PROFILES.values()
    )
    if required_profile is None and not profile_enabled:
        return None
    if required_profile is not None:
        if config.default_off_remediation_profile == required_profile:
            return None
        return "material_support_profile_required"
    return "material_support_policy_required"


def _lane_red_hard_feasibility_precheck(
    *,
    stop_distance: float,
    red_distance: float,
    max_forward: float,
    current_speed_mps: float,
    config: RouteTopologyCandidateConfig,
) -> dict[str, Any]:
    stop = float(stop_distance)
    red = float(red_distance)
    forward = float(max_forward)
    speed = float(current_speed_mps)
    max_decel = float(config.max_deceleration_mps2)
    required_deceleration = speed * speed / max(2.0 * stop, TOL)
    margins = {
        "red_ahead_margin_m": red,
        "stop_distance_margin_m": stop - float(config.min_stop_distance_m),
        "forward_range_margin_m": forward - stop,
        "kinematic_deceleration_margin_mps2": (
            max_decel - required_deceleration
        ),
    }
    failure_reason = None
    if not all(
        np.isfinite(value)
        for value in (
            stop,
            red,
            forward,
            speed,
            max_decel,
            required_deceleration,
            *margins.values(),
        )
    ):
        failure_reason = "lane_red_hard_precheck_nonfinite"
    elif margins["red_ahead_margin_m"] <= TOL:
        failure_reason = "red_timing_margin_nonpositive"
    elif margins["stop_distance_margin_m"] < -TOL:
        failure_reason = "stop_distance_margin_negative"
    elif margins["forward_range_margin_m"] < -TOL:
        failure_reason = "lane_forward_range_margin_negative"
    elif margins["kinematic_deceleration_margin_mps2"] < -TOL:
        failure_reason = "kinematic_deceleration_margin_negative"
    return {
        "passed": failure_reason is None,
        "failure_reason": failure_reason,
        "required_deceleration_mps2": _json_number(required_deceleration),
        "margins": {
            key: _json_number(max(0.0, value))
            for key, value in margins.items()
        },
        "raw_margins": {key: _json_number(value) for key, value in margins.items()},
        "current_tick_features_only": True,
        "uses_outcome_labels": False,
    }


def _add_negative_support_fail_closed_partition(
    diagnostics: dict[str, Any],
) -> None:
    policy = diagnostics.get("generator_policy")
    if policy == "negative_support_coverage_first_lane_projected_red_stop":
        diagnostics["fail_closed_partition"] = diagnostics.get("failure_reason")
        diagnostics["current_tick_features_only"] = True
        return
    if policy not in MATERIAL_SUPPORT_POLICY_PROFILES:
        return
    diagnostics["fail_closed_partition"] = diagnostics.get("failure_reason")
    diagnostics["candidate0_preserved"] = True
    diagnostics["dp_rows_preserved"] = True
    diagnostics["current_tick_features_only"] = True


def _current_tick_scalar_failure_reason(
    current_speed_mps: float,
    dt: float,
) -> str | None:
    if _positive_finite_number(current_speed_mps) is None:
        return "current_tick_scalar_invalid"
    if _positive_finite_number(dt) is None:
        return "current_tick_scalar_invalid"
    return None


def _selected_candidate_state_failure_reason(
    candidates: np.ndarray,
    selected_index: int,
) -> str | None:
    selected = np.asarray(candidates[selected_index], dtype=np.float64)
    if not np.isfinite(selected).all():
        return "selected_candidate_state_invalid"
    return None


def _positive_finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number) or number <= 0.0:
        return None
    return number


def _max_finite_budget(values: tuple[float, ...]) -> float | None:
    finite = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(number):
            finite.append(number)
    return max(finite) if finite else None


def _by_snapshot(
    rows: list[dict[str, Any]],
    *,
    config: RouteTopologyCandidateConfig = RouteTopologyCandidateConfig(),
) -> list[dict[str, Any]]:
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
                            for klass in route_failure_classes(row, config=config)
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


def _json_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


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
        "comfort_first_lane_projected_red_stop",
        "negative_support_coverage_first_lane_projected_red_stop",
        GENERATOR_POLICY_MATERIAL_SUPPORT,
        GENERATOR_POLICY_MATERIAL_SUPPORT_V2,
        GENERATOR_POLICY_MATERIAL_SUPPORT_V3,
        GENERATOR_POLICY_MATERIAL_SUPPORT_V4,
        "prefix_lane_projected_red_stop",
        "prefix_lane_projected_latest_safe_red_stop",
    }:
        raise ValueError("invalid generator_policy.")
    if config.default_off_remediation_profile not in {
        REMEDIATION_PROFILE_OFF,
        REMEDIATION_PROFILE_SUPPORT_V1,
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1,
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2,
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3,
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V4,
    }:
        raise ValueError("default_off_remediation_profile is invalid.")
    if _material_support_profile_failure(config) is not None:
        raise ValueError(_material_support_profile_failure(config))
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
    if int(config.max_remediation_candidates) <= 0:
        raise ValueError("max_remediation_candidates must be positive.")
    for value in config.progress_loss_budgets_m:
        if not np.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError("progress_loss_budgets_m must be nonnegative.")
    for value in config.smoothness_loss_budgets:
        if not np.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError("smoothness_loss_budgets must be nonnegative.")


if __name__ == "__main__":
    main()
