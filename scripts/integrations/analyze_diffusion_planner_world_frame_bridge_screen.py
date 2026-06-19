#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
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
    compute_perfect_tracker_command_diagnostics,
    compute_perfect_tracker_open_loop_rollout_diagnostics,
)
from scripts.integrations.analyze_diffusion_planner_splice_recompute_gate import (  # noqa: E402
    SNAPSHOT_GLOB,
    TOL,
    _donor_indices,
    _load_runtime,
    _load_snapshot,
    _optional_vector,
    _score_trajectories,
    _sum_reason_counts,
    _validate_snapshot,
    fixed_candidate_shadow_rule,
    heading_features_from_xy,
    reason_counts,
    reward_hard_feasibility,
    reward_metric_vector,
    reward_progress_screen,
)


READY_STATUS = "world_frame_bridge_offline_support_present"
REJECT_STATUS = "world_frame_bridge_offline_support_insufficient"


@dataclass(frozen=True)
class WorldFrameBridgeConfig:
    preserve_steps: int = 1
    bridge_steps: int = 10
    donor_pool: str = "lower_logged_union_red"
    heading_mode: str = "world_donor_tail"
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
    shadow_rule_enabled: bool = False
    shadow_progress_loss_budget_m: float = 1.0
    shadow_smoothness_loss_budget: float = 0.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline world-frame donor-tail bridge recompute screen over fixed "
            "DP/CAMP microbenchmark snapshots. It materializes deterministic "
            "transformed candidates, recomputes DP reward/full-red and "
            "PerfectTracker proxies, and has no online selection effect."
        )
    )
    parser.add_argument("--snapshot_dir", type=Path, required=True)
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--reward_config", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--label", default=None)
    parser.add_argument("--preserve_steps", type=int, default=1)
    parser.add_argument("--bridge_steps", type=int, default=10)
    parser.add_argument(
        "--donor_pool",
        choices=("lower_logged_union_red", "all_nonselected"),
        default="lower_logged_union_red",
    )
    parser.add_argument(
        "--heading_mode",
        choices=("world_donor_tail", "finite_difference"),
        default="world_donor_tail",
    )
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
    parser.add_argument("--enable_shadow_rule", action="store_true")
    parser.add_argument("--shadow_progress_loss_budget_m", type=float, default=1.0)
    parser.add_argument("--shadow_smoothness_loss_budget", type=float, default=0.5)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = WorldFrameBridgeConfig(
        preserve_steps=args.preserve_steps,
        bridge_steps=args.bridge_steps,
        donor_pool=args.donor_pool,
        heading_mode=args.heading_mode,
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
        shadow_rule_enabled=bool(args.enable_shadow_rule),
        shadow_progress_loss_budget_m=args.shadow_progress_loss_budget_m,
        shadow_smoothness_loss_budget=args.shadow_smoothness_loss_budget,
    )
    report = analyze(
        snapshot_dir=args.snapshot_dir,
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
    diffusion_repo: Path,
    reward_config_path: Path,
    device: str = "cuda",
    label: str | None = None,
    config: WorldFrameBridgeConfig = WorldFrameBridgeConfig(),
) -> dict[str, Any]:
    _validate_config(config)
    snapshots = sorted(Path(snapshot_dir).rglob(SNAPSHOT_GLOB))
    if not snapshots:
        raise ValueError(f"No {SNAPSHOT_GLOB} files found in {snapshot_dir}.")
    if not diffusion_repo.is_dir():
        raise FileNotFoundError(f"Missing Diffusion Planner repo: {diffusion_repo}")
    if not reward_config_path.is_file():
        raise FileNotFoundError(f"Missing reward config: {reward_config_path}")

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

    transformed = _summarize_transformed(rows)
    support = _support_summary(rows, transformed, config)
    return {
        "analysis": {
            "name": "dp_camp_world_frame_donor_tail_bridge_screen_v1",
            "role": (
                "offline recompute screen for deterministic world-frame "
                "donor-tail bridge candidates over fixed current-tick snapshots"
            ),
            "label": label,
            "training": False,
            "online_selector_change": False,
            "selection_effect": False,
            "uses_outcome_labels": False,
            "future_outcome_leakage": False,
            "recomputes_dp_reward_or_red_light": True,
            "recomputes_perfect_tracker_proxies": True,
            "math_boundary": (
                "The bridge is a deterministic finite-candidate transform over "
                "fixed current-tick snapshot tensors. It does not modify DP, "
                "does not train CAMP, does not use future closed-loop outcomes, "
                "and does not construct a DP-side Benders master/subproblem, "
                "dual, or cuts. If the recomputed fixed diagnostics are later "
                "atomized, CAMP scores remain affine a_k^T w and the "
                "simplex/CVaR/L2 master remains convex for that fixed finite "
                "candidate set only."
            ),
        },
        "config": asdict(config),
        "snapshots": {
            "count": len(rows),
            "with_donors": sum(1 for row in rows if row["donor_count"] > 0),
            "with_transforms": sum(
                1 for row in rows if row["transformed"]["count"] > 0
            ),
            "with_lower_union_red": sum(
                1 for row in rows if row["transformed"]["has_lower_union_red"]
            ),
            "with_lower_union_red_hard_feasible": sum(
                1
                for row in rows
                if row["transformed"]["lower_union_red_hard_feasible_count"] > 0
            ),
            "with_lower_union_red_admissible": sum(
                1
                for row in rows
                if row["transformed"]["comfort_admissible_count"] > 0
            ),
        },
        "baseline_recompute": _summarize_baseline(rows),
        "transformed": transformed,
        "support_gate": support,
        "latency_ms": _summarize_latency(rows),
        "shadow_rule": _summarize_shadow_rule(rows, config),
        "final_decision": _decision(support),
        "rows": rows,
    }


def build_world_frame_bridge_candidates(
    candidates: np.ndarray,
    *,
    selected_index: int,
    donor_indices: np.ndarray,
    preserve_steps: int,
    bridge_steps: int,
    heading_mode: str = "world_donor_tail",
) -> np.ndarray:
    raw = np.asarray(candidates, dtype=np.float64)
    if raw.ndim != 3 or raw.shape[0] <= 0 or raw.shape[2] < 2:
        raise ValueError("candidates must be [K,T,D>=2].")
    if selected_index < 0 or selected_index >= raw.shape[0]:
        raise ValueError("selected_index is out of range.")
    if heading_mode not in {"world_donor_tail", "finite_difference"}:
        raise ValueError("invalid heading_mode.")
    selected = raw[selected_index]
    bridges = []
    for donor_index in np.asarray(donor_indices, dtype=np.int64).reshape(-1).tolist():
        if donor_index < 0 or donor_index >= raw.shape[0]:
            raise ValueError("donor index is out of range.")
        if donor_index == selected_index:
            continue
        donor = raw[donor_index]
        bridge = selected.copy()
        bridge[:, :2] = world_frame_donor_tail_bridge_xy(
            selected[:, :2],
            donor[:, :2],
            preserve_steps=preserve_steps,
            bridge_steps=bridge_steps,
        )
        if bridge.shape[1] >= 4:
            if heading_mode == "world_donor_tail":
                bridge[:, 2:4] = world_frame_donor_tail_bridge_heading(
                    selected[:, 2:4],
                    donor[:, 2:4],
                    preserve_steps=preserve_steps,
                    bridge_steps=bridge_steps,
                )
            else:
                bridge[:, 2:4] = heading_features_from_xy(
                    bridge[:, :2],
                    fallback=selected[:, 2:4],
                )
        bridges.append(bridge)
    if not bridges:
        return np.empty((0, raw.shape[1], raw.shape[2]), dtype=np.float64)
    return np.stack(bridges)


def world_frame_donor_tail_bridge_xy(
    selected_xy: np.ndarray,
    donor_xy: np.ndarray,
    *,
    preserve_steps: int,
    bridge_steps: int,
) -> np.ndarray:
    selected = np.asarray(selected_xy, dtype=np.float64)
    donor = np.asarray(donor_xy, dtype=np.float64)
    if selected.shape != donor.shape or selected.ndim != 2 or selected.shape[1] != 2:
        raise ValueError("selected_xy and donor_xy must both be [T,2].")
    if not np.all(np.isfinite(selected)) or not np.all(np.isfinite(donor)):
        raise ValueError("bridge coordinates must be finite.")
    _validate_bridge_shape(selected.shape[0], preserve_steps, bridge_steps)

    bridge = selected.copy()
    preserve = int(preserve_steps)
    transition = min(int(bridge_steps), selected.shape[0] - preserve)
    if transition == 0:
        bridge[preserve:] = donor[preserve:]
        return bridge

    for local_step in range(transition):
        step = preserve + local_step
        u = float(local_step + 1) / float(transition)
        weight = _smoothstep(u)
        bridge[step] = (1.0 - weight) * selected[step] + weight * donor[step]
    tail_start = preserve + transition
    if tail_start < selected.shape[0]:
        bridge[tail_start:] = donor[tail_start:]
    bridge[:preserve] = selected[:preserve]
    return bridge


def world_frame_donor_tail_bridge_heading(
    selected_heading: np.ndarray,
    donor_heading: np.ndarray,
    *,
    preserve_steps: int,
    bridge_steps: int,
) -> np.ndarray:
    selected_angle = _unwrap_heading_features(selected_heading)
    donor_angle = _unwrap_heading_features(donor_heading)
    if selected_angle.shape != donor_angle.shape:
        raise ValueError("selected_heading and donor_heading must both be [T,2].")
    _validate_bridge_shape(selected_angle.shape[0], preserve_steps, bridge_steps)

    bridge_angle = selected_angle.copy()
    preserve = int(preserve_steps)
    transition = min(int(bridge_steps), selected_angle.shape[0] - preserve)
    if transition == 0:
        bridge_angle[preserve:] = donor_angle[preserve:]
    else:
        for local_step in range(transition):
            step = preserve + local_step
            u = float(local_step + 1) / float(transition)
            weight = _smoothstep(u)
            bridge_angle[step] = (
                (1.0 - weight) * selected_angle[step]
                + weight * donor_angle[step]
            )
        tail_start = preserve + transition
        if tail_start < selected_angle.shape[0]:
            bridge_angle[tail_start:] = donor_angle[tail_start:]
    bridge_angle[:preserve] = selected_angle[:preserve]
    return np.stack((np.cos(bridge_angle), np.sin(bridge_angle)), axis=1)


def tracker_budget_sensitivity(
    *,
    union_red: np.ndarray,
    progress: np.ndarray,
    smoothness: np.ndarray,
    hard_feasible: np.ndarray,
    tracker: dict[str, np.ndarray],
    selected_union_red: float,
    selected_progress: float,
    selected_smoothness: float,
    selected_tracker: dict[str, float],
    config: WorldFrameBridgeConfig,
) -> list[dict[str, Any]]:
    union = np.asarray(union_red, dtype=np.float64).reshape(-1)
    progress_arr = np.asarray(progress, dtype=np.float64).reshape(-1)
    smoothness_arr = np.asarray(smoothness, dtype=np.float64).reshape(-1)
    hard = np.asarray(hard_feasible, dtype=bool).reshape(-1)
    expected_shape = union.shape
    if not (
        progress_arr.shape == smoothness_arr.shape == hard.shape == expected_shape
    ):
        raise ValueError("budget arrays must align.")
    command_jerk = _tracker_vector(tracker, "command_jerk_mps3", expected_shape)
    command_lateral = _tracker_vector(
        tracker,
        "command_lateral_mps2",
        expected_shape,
    )
    rollout_distance = _tracker_vector(
        tracker,
        "rollout_distance_m",
        expected_shape,
    )
    rollout_jerk = _tracker_vector(tracker, "rollout_jerk_mps3", expected_shape)
    rollout_lateral = _tracker_vector(
        tracker,
        "rollout_lateral_mps2",
        expected_shape,
    )
    if not (
        np.all(np.isfinite(union))
        and np.all(np.isfinite(progress_arr))
        and np.all(np.isfinite(smoothness_arr))
    ):
        raise ValueError("budget metrics must be finite.")

    progress_loss = float(selected_progress) - progress_arr
    smoothness_loss = float(selected_smoothness) - smoothness_arr
    command_jerk_worse = command_jerk - float(selected_tracker["command_jerk_mps3"])
    command_lateral_worse = (
        command_lateral - float(selected_tracker["command_lateral_mps2"])
    )
    rollout_distance_loss = (
        float(selected_tracker["rollout_distance_m"]) - rollout_distance
    )
    rollout_jerk_worse = rollout_jerk - float(selected_tracker["rollout_jerk_mps3"])
    rollout_lateral_worse = (
        rollout_lateral - float(selected_tracker["rollout_lateral_mps2"])
    )
    lower_red_hard = (union < float(selected_union_red) - TOL) & hard

    rows = []
    for progress_budget in config.progress_loss_budgets_m:
        for smoothness_budget in config.smoothness_loss_budgets:
            mask = (
                lower_red_hard
                & (progress_loss <= float(progress_budget) + TOL)
                & (smoothness_loss <= float(smoothness_budget) + TOL)
                & (
                    command_jerk_worse
                    <= float(config.command_jerk_worse_budget_mps3) + TOL
                )
                & (
                    command_lateral_worse
                    <= float(config.command_lateral_worse_budget_mps2) + TOL
                )
                & (
                    rollout_distance_loss
                    <= float(config.rollout_distance_loss_budget_m) + TOL
                )
                & (
                    rollout_jerk_worse
                    <= float(config.rollout_jerk_worse_budget_mps3) + TOL
                )
                & (
                    rollout_lateral_worse
                    <= float(config.rollout_lateral_worse_budget_mps2) + TOL
                )
            )
            rows.append(
                {
                    "progress_loss_budget_m": float(progress_budget),
                    "smoothness_loss_budget": float(smoothness_budget),
                    "count": int(np.sum(mask)),
                    "has_candidate": bool(np.any(mask)),
                    "min_union_red": _masked_min(union, mask),
                    "min_progress_loss_m": _masked_min(progress_loss, mask),
                    "min_smoothness_loss": _masked_min(smoothness_loss, mask),
                    "max_command_jerk_worse_mps3": _masked_max(
                        command_jerk_worse,
                        mask,
                    ),
                    "max_command_lateral_worse_mps2": _masked_max(
                        command_lateral_worse,
                        mask,
                    ),
                    "max_rollout_distance_loss_m": _masked_max(
                        rollout_distance_loss,
                        mask,
                    ),
                    "max_rollout_jerk_worse_mps3": _masked_max(
                        rollout_jerk_worse,
                        mask,
                    ),
                    "max_rollout_lateral_worse_mps2": _masked_max(
                        rollout_lateral_worse,
                        mask,
                    ),
                }
            )
    return rows


def _analyze_snapshot(
    *,
    snapshot_path: Path,
    arrays: dict[str, np.ndarray],
    metadata: dict[str, Any],
    replay_module: Any,
    reward_config: Any,
    torch: Any,
    device: str,
    config: WorldFrameBridgeConfig,
) -> dict[str, Any]:
    candidates = np.asarray(arrays["candidates"], dtype=np.float64)
    selected = int(metadata["selected_index"])
    donor_indices = _donor_indices(arrays, metadata, config.donor_pool, candidates.shape[0])

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
    transformed_candidates = build_world_frame_bridge_candidates(
        candidates,
        selected_index=selected,
        donor_indices=donor_indices,
        preserve_steps=config.preserve_steps,
        bridge_steps=config.bridge_steps,
        heading_mode=config.heading_mode,
    )
    t3 = time.perf_counter()
    transformed_scores = (
        _score_trajectories(
            transformed_candidates,
            arrays=arrays,
            metadata=metadata,
            replay_module=replay_module,
            reward_config=reward_config,
            torch=torch,
            device=device,
        )
        if transformed_candidates.size
        else None
    )
    t4 = time.perf_counter()
    transformed_tracker = (
        _tracker_diagnostics(
            transformed_candidates,
            arrays=arrays,
            metadata=metadata,
        )
        if transformed_candidates.size
        else None
    )
    t5 = time.perf_counter()

    return _snapshot_report_row(
        snapshot_path=snapshot_path,
        arrays=arrays,
        metadata=metadata,
        donor_indices=donor_indices,
        baseline_scores=baseline_scores,
        transformed_scores=transformed_scores,
        baseline_tracker=baseline_tracker,
        transformed_tracker=transformed_tracker,
        config=config,
        timings_ms={
            "baseline_reward": (t1 - t0) * 1000.0,
            "baseline_tracker": (t2 - t1) * 1000.0,
            "transform_build": (t3 - t2) * 1000.0,
            "transformed_reward": (t4 - t3) * 1000.0,
            "transformed_tracker": (t5 - t4) * 1000.0,
            "total": (t5 - t0) * 1000.0,
        },
    )


def _snapshot_report_row(
    *,
    snapshot_path: Path,
    arrays: dict[str, np.ndarray],
    metadata: dict[str, Any],
    donor_indices: np.ndarray,
    baseline_scores: dict[str, Any],
    transformed_scores: dict[str, Any] | None,
    baseline_tracker: dict[str, Any],
    transformed_tracker: dict[str, Any] | None,
    config: WorldFrameBridgeConfig,
    timings_ms: dict[str, float],
) -> dict[str, Any]:
    count = int(np.asarray(arrays["candidates"]).shape[0])
    selected = int(metadata["selected_index"])
    logged_near = _optional_vector(arrays.get("candidate_planned_red_light_cost"), count)
    logged_full = _optional_vector(
        arrays.get("candidate_full_horizon_planned_red_light_cost"),
        count,
    )
    selected_progress = float(
        reward_metric_vector(baseline_scores["reward_breakdowns"], "progress")[
            selected
        ]
    )
    selected_smoothness = float(
        reward_metric_vector(baseline_scores["reward_breakdowns"], "smoothness")[
            selected
        ]
    )
    selected_union = float(baseline_scores["union_red_cost"][selected])
    selected_tracker = _selected_tracker_summary(baseline_tracker, selected, config)
    transformed = _transformed_summary(
        transformed_scores,
        transformed_tracker,
        selected_union_red=selected_union,
        selected_progress=selected_progress,
        selected_smoothness=selected_smoothness,
        selected_tracker=selected_tracker,
        config=config,
    )
    return {
        "snapshot_path": str(snapshot_path),
        "selection_step": int(metadata["selection_step"]),
        "selected_index": selected,
        "candidate_count": count,
        "donor_indices": [int(index) for index in donor_indices.tolist()],
        "donor_count": int(donor_indices.size),
        "baseline": {
            "reward_horizon_steps": int(baseline_scores["reward_horizon_steps"]),
            "selected_near_red": float(baseline_scores["near_red_cost"][selected]),
            "selected_full_red": float(baseline_scores["full_red_cost"][selected]),
            "selected_union_red": selected_union,
            "selected_progress": selected_progress,
            "selected_smoothness": selected_smoothness,
            "selected_tracker": selected_tracker,
            "logged_near_red_max_abs_error": _max_abs_error(
                logged_near,
                baseline_scores["near_red_cost"],
            ),
            "logged_full_red_max_abs_error": _max_abs_error(
                logged_full,
                baseline_scores["full_red_cost"],
            ),
        },
        "transformed": transformed,
        "latency_ms": {key: float(value) for key, value in timings_ms.items()},
    }


def _transformed_summary(
    scores: dict[str, Any] | None,
    tracker: dict[str, Any] | None,
    *,
    selected_union_red: float,
    selected_progress: float,
    selected_smoothness: float,
    selected_tracker: dict[str, float],
    config: WorldFrameBridgeConfig,
) -> dict[str, Any]:
    if scores is None or tracker is None:
        return _empty_transformed_summary(
            selected_union_red=selected_union_red,
            selected_progress=selected_progress,
            selected_smoothness=selected_smoothness,
            config=config,
        )

    union = np.asarray(scores["union_red_cost"], dtype=np.float64)
    near = np.asarray(scores["near_red_cost"], dtype=np.float64)
    full = np.asarray(scores["full_red_cost"], dtype=np.float64)
    hard_feasible, hard_reasons = reward_hard_feasibility(scores["reward_breakdowns"])
    progress_feasible, progress_reasons = reward_progress_screen(
        scores["reward_breakdowns"],
        hard_feasible,
        min_progress_ratio=config.min_progress_ratio,
    )
    progress = reward_metric_vector(scores["reward_breakdowns"], "progress")
    smoothness = reward_metric_vector(scores["reward_breakdowns"], "smoothness")
    lower_union = union < selected_union_red - TOL
    tracker_metrics = _tracker_metrics_for_budget(tracker, config)
    budget_rows = tracker_budget_sensitivity(
        union_red=union,
        progress=progress,
        smoothness=smoothness,
        hard_feasible=hard_feasible,
        tracker=tracker_metrics,
        selected_union_red=selected_union_red,
        selected_progress=selected_progress,
        selected_smoothness=selected_smoothness,
        selected_tracker=selected_tracker,
        config=config,
    )
    comfort_admissible_count = int(
        max((int(row["count"]) for row in budget_rows), default=0)
    )
    shadow_rule = fixed_candidate_shadow_rule(
        union_red=union,
        progress=progress,
        smoothness=smoothness,
        hard_feasible=hard_feasible,
        selected_union_red=selected_union_red,
        selected_progress=selected_progress,
        selected_smoothness=selected_smoothness,
        enabled=config.shadow_rule_enabled,
        progress_loss_budget_m=config.shadow_progress_loss_budget_m,
        smoothness_loss_budget=config.shadow_smoothness_loss_budget,
    )
    return {
        "count": int(union.size),
        "has_lower_union_red": bool(np.any(lower_union)),
        "hard_feasible_count": int(np.sum(hard_feasible)),
        "progress_feasible_count": int(np.sum(progress_feasible)),
        "lower_union_red_count": int(np.sum(lower_union)),
        "lower_union_red_hard_feasible_count": int(
            np.sum(lower_union & hard_feasible)
        ),
        "lower_union_red_progress_feasible_count": int(
            np.sum(lower_union & progress_feasible)
        ),
        "comfort_admissible_count": comfort_admissible_count,
        "hard_infeasibility_reason_counts": reason_counts(
            hard_reasons,
            ~hard_feasible,
        ),
        "lower_union_red_hard_infeasibility_reason_counts": reason_counts(
            hard_reasons,
            lower_union & ~hard_feasible,
        ),
        "progress_infeasibility_reason_counts": reason_counts(
            progress_reasons,
            hard_feasible & ~progress_feasible,
        ),
        "min_near_red": float(np.min(near)) if near.size else None,
        "min_full_red": float(np.min(full)) if full.size else None,
        "min_union_red": float(np.min(union)) if union.size else None,
        "budget_sensitivity": budget_rows,
        "tracker": _tracker_summary(tracker),
        "shadow_rule": shadow_rule,
    }


def _empty_transformed_summary(
    *,
    selected_union_red: float,
    selected_progress: float,
    selected_smoothness: float,
    config: WorldFrameBridgeConfig,
) -> dict[str, Any]:
    return {
        "count": 0,
        "has_lower_union_red": False,
        "hard_feasible_count": 0,
        "progress_feasible_count": 0,
        "lower_union_red_count": 0,
        "lower_union_red_hard_feasible_count": 0,
        "lower_union_red_progress_feasible_count": 0,
        "comfort_admissible_count": 0,
        "hard_infeasibility_reason_counts": {},
        "lower_union_red_hard_infeasibility_reason_counts": {},
        "progress_infeasibility_reason_counts": {},
        "min_near_red": None,
        "min_full_red": None,
        "min_union_red": None,
        "budget_sensitivity": [],
        "tracker": {},
        "shadow_rule": fixed_candidate_shadow_rule(
            union_red=np.empty(0, dtype=np.float64),
            progress=np.empty(0, dtype=np.float64),
            smoothness=np.empty(0, dtype=np.float64),
            hard_feasible=np.empty(0, dtype=bool),
            selected_union_red=selected_union_red,
            selected_progress=selected_progress,
            selected_smoothness=selected_smoothness,
            enabled=config.shadow_rule_enabled,
            progress_loss_budget_m=config.shadow_progress_loss_budget_m,
            smoothness_loss_budget=config.shadow_smoothness_loss_budget,
        ),
    }


def _tracker_diagnostics(
    candidates: np.ndarray,
    *,
    arrays: dict[str, np.ndarray],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    dt = float(metadata.get("dt", 0.1))
    command = compute_perfect_tracker_command_diagnostics(
        candidates,
        dt=dt,
        current_speed_mps=float(metadata.get("current_speed_mps", 0.0)),
        current_longitudinal_acceleration_mps2=float(
            metadata.get("current_longitudinal_acceleration_mps2", 0.0)
        ),
    )
    horizons = _normalized_horizons(
        metadata.get("perfect_tracker_open_loop_horizons", (3, 5, 10)),
        command["postprocessed_reference"].shape[1],
    )
    open_loop = compute_perfect_tracker_open_loop_rollout_diagnostics(
        command["postprocessed_reference"][:, : max(horizons)],
        postprocessed_tail_reference_xy=command["postprocessed_tail_reference_xy"],
        full_horizon_steps=int(candidates.shape[1]),
        dt=dt,
        current_speed_mps=float(metadata.get("current_speed_mps", 0.0)),
        current_acceleration_ego_xy=np.asarray(
            arrays.get("current_acceleration_ego_xy", np.zeros(2)),
            dtype=np.float64,
        ),
        horizons=horizons,
    )
    return {"command": command, "open_loop": open_loop}


def _selected_tracker_summary(
    tracker: dict[str, Any],
    selected: int,
    config: WorldFrameBridgeConfig,
) -> dict[str, float]:
    command = tracker["command"]
    horizon = str(config.rollout_horizon)
    rollout = tracker["open_loop"]["horizons"][horizon]
    return {
        "command_jerk_mps3": float(command["jerk_magnitude_mps3"][selected]),
        "command_lateral_mps2": float(
            command["lateral_acceleration_magnitude_mps2"][selected]
        ),
        "rollout_distance_m": float(rollout["distance_m"][selected]),
        "rollout_jerk_mps3": float(rollout["max_vector_jerk_mps3"][selected]),
        "rollout_lateral_mps2": float(
            rollout["max_lateral_acceleration_mps2"][selected]
        ),
    }


def _tracker_summary(tracker: dict[str, Any]) -> dict[str, Any]:
    command = tracker["command"]
    horizons = tracker["open_loop"]["horizons"]
    return {
        "command_jerk_mps3": _summary(command["jerk_magnitude_mps3"]),
        "command_lateral_mps2": _summary(
            command["lateral_acceleration_magnitude_mps2"]
        ),
        "open_loop": {
            horizon: {
                "distance_m": _summary(metrics["distance_m"]),
                "max_vector_jerk_mps3": _summary(metrics["max_vector_jerk_mps3"]),
                "max_lateral_acceleration_mps2": _summary(
                    metrics["max_lateral_acceleration_mps2"]
                ),
            }
            for horizon, metrics in horizons.items()
        },
    }


def _summarize_baseline(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "logged_near_red_max_abs_error": _summary(
            [
                row["baseline"]["logged_near_red_max_abs_error"]
                for row in rows
                if row["baseline"]["logged_near_red_max_abs_error"] is not None
            ]
        ),
        "logged_full_red_max_abs_error": _summary(
            [
                row["baseline"]["logged_full_red_max_abs_error"]
                for row in rows
                if row["baseline"]["logged_full_red_max_abs_error"] is not None
            ]
        ),
    }


def _summarize_transformed(rows: list[dict[str, Any]]) -> dict[str, Any]:
    active = [row["transformed"] for row in rows if row["transformed"]["count"] > 0]
    return {
        "snapshots_with_transforms": len(active),
        "transform_count": int(sum(row["count"] for row in active)),
        "hard_feasible_count": int(sum(row["hard_feasible_count"] for row in active)),
        "progress_feasible_count": int(
            sum(row["progress_feasible_count"] for row in active)
        ),
        "lower_union_red_count": int(sum(row["lower_union_red_count"] for row in active)),
        "lower_union_red_hard_feasible_count": int(
            sum(row["lower_union_red_hard_feasible_count"] for row in active)
        ),
        "lower_union_red_progress_feasible_count": int(
            sum(row["lower_union_red_progress_feasible_count"] for row in active)
        ),
        "comfort_admissible_count": int(
            sum(row["comfort_admissible_count"] for row in active)
        ),
        "hard_infeasibility_reason_counts": _sum_reason_counts(
            row["hard_infeasibility_reason_counts"] for row in active
        ),
        "lower_union_red_hard_infeasibility_reason_counts": _sum_reason_counts(
            row["lower_union_red_hard_infeasibility_reason_counts"]
            for row in active
        ),
        "budget_sensitivity": _summarize_budget_sensitivity(active),
        "min_union_red": _summary(
            [row["min_union_red"] for row in active if row["min_union_red"] is not None]
        ),
    }


def _support_summary(
    rows: list[dict[str, Any]],
    transformed: dict[str, Any],
    config: WorldFrameBridgeConfig,
) -> dict[str, Any]:
    denominator = max(1, len(rows))
    hard_supported = sum(
        1 for row in rows if row["transformed"]["lower_union_red_hard_feasible_count"] > 0
    )
    admissible_supported = sum(
        1 for row in rows if row["transformed"]["comfort_admissible_count"] > 0
    )
    return {
        "min_snapshot_support_rate": float(config.min_snapshot_support_rate),
        "hard_feasible_snapshot_support_rate": hard_supported / denominator,
        "comfort_admissible_snapshot_support_rate": admissible_supported / denominator,
        "hard_feasible_snapshot_support_pass": (
            hard_supported / denominator >= float(config.min_snapshot_support_rate)
        ),
        "comfort_admissible_snapshot_support_pass": (
            admissible_supported / denominator
            >= float(config.min_snapshot_support_rate)
        ),
        "has_lower_union_red_hard_feasible_candidates": (
            int(transformed["lower_union_red_hard_feasible_count"]) > 0
        ),
        "has_comfort_admissible_candidates": (
            int(transformed["comfort_admissible_count"]) > 0
        ),
    }


def _summarize_budget_sensitivity(active: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not active:
        return []
    keys = [
        (
            float(row["progress_loss_budget_m"]),
            float(row["smoothness_loss_budget"]),
        )
        for row in active[0]["budget_sensitivity"]
    ]
    rows = []
    for progress_budget, smoothness_budget in keys:
        cells = [
            cell
            for row in active
            for cell in row["budget_sensitivity"]
            if (
                float(cell["progress_loss_budget_m"]) == progress_budget
                and float(cell["smoothness_loss_budget"]) == smoothness_budget
            )
        ]
        rows.append(
            {
                "progress_loss_budget_m": progress_budget,
                "smoothness_loss_budget": smoothness_budget,
                "count": int(sum(int(cell["count"]) for cell in cells)),
                "snapshots_with_candidate": int(
                    sum(int(bool(cell["has_candidate"])) for cell in cells)
                ),
            }
        )
    return rows


def _summarize_shadow_rule(
    rows: list[dict[str, Any]],
    config: WorldFrameBridgeConfig,
) -> dict[str, Any]:
    cells = [row["transformed"]["shadow_rule"] for row in rows]
    return {
        "enabled": bool(config.shadow_rule_enabled),
        "default_off": True,
        "selection_effect": False,
        "online_selector_change": False,
        "changed_snapshots": int(sum(int(cell["changed"]) for cell in cells)),
        "admissible_count": int(sum(int(cell["admissible_count"]) for cell in cells)),
        "reason_counts": _sum_reason_counts({cell["reason"]: 1} for cell in cells),
    }


def _summarize_latency(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = (
        "baseline_reward",
        "baseline_tracker",
        "transform_build",
        "transformed_reward",
        "transformed_tracker",
        "total",
    )
    return {key: _summary(row["latency_ms"][key] for row in rows) for key in keys}


def _decision(support: dict[str, Any]) -> dict[str, Any]:
    passed = bool(
        support["hard_feasible_snapshot_support_pass"]
        and support["comfort_admissible_snapshot_support_pass"]
        and support["has_lower_union_red_hard_feasible_candidates"]
        and support["has_comfort_admissible_candidates"]
    )
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "next_step": (
            "Use this offline evidence to design a default-off selector screen; "
            "do not run replay yet."
            if passed
            else "Reject or revise this transform before replay; evidence is insufficient."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    transformed = report["transformed"]
    support = report["support_gate"]
    lines = [
        "# World-Frame Donor-Tail Bridge Offline Screen",
        "",
        "This is an offline fixed-snapshot recompute screen. It is not replay, not an online selector, and not a formal-seed experiment.",
        "",
        "## Verdict",
        "",
        f"- Status: `{decision['status']}`",
        f"- Online selector authorized: `{decision['online_selector_authorized']}`",
        f"- Full36 authorized: `{decision['full36_authorized']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        "",
        "## Config",
        "",
        f"- Preserve steps: `{report['config']['preserve_steps']}`",
        f"- Bridge steps: `{report['config']['bridge_steps']}`",
        f"- Heading mode: `{report['config']['heading_mode']}`",
        f"- Donor pool: `{report['config']['donor_pool']}`",
        f"- Tracker comfort horizon: `{report['config']['rollout_horizon']}`",
        "",
        "## Support",
        "",
        f"- Snapshots: `{report['snapshots']['count']}`",
        f"- Snapshots with donors: `{report['snapshots']['with_donors']}`",
        f"- Lower union-red transforms: `{transformed['lower_union_red_count']}`",
        f"- Lower union-red hard-feasible transforms: `{transformed['lower_union_red_hard_feasible_count']}`",
        f"- Lower union-red progress-feasible transforms: `{transformed['lower_union_red_progress_feasible_count']}`",
        f"- Comfort-admissible lower-red transforms: `{transformed['comfort_admissible_count']}`",
        f"- Hard-feasible snapshot support rate: `{support['hard_feasible_snapshot_support_rate']:.6f}`",
        f"- Comfort-admissible snapshot support rate: `{support['comfort_admissible_snapshot_support_rate']:.6f}`",
        f"- Lower-red hard infeasibility reasons: `{transformed['lower_union_red_hard_infeasibility_reason_counts']}`",
        "",
        "## Budget Sensitivity",
        "",
        "| Progress loss budget (m) | Smoothness loss budget | Candidate count | Snapshots with candidate |",
        "| ---: | ---: | ---: | ---: |",
    ]
    for cell in transformed["budget_sensitivity"]:
        lines.append(
            f"| {_fmt(cell['progress_loss_budget_m'])} | "
            f"{_fmt(cell['smoothness_loss_budget'])} | "
            f"{cell['count']} | {cell['snapshots_with_candidate']} |"
        )
    lines.extend(
        [
            "",
            "## Latency Projection",
            "",
            "| Component | Mean ms | P95 ms | Max ms |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for key, summary in report["latency_ms"].items():
        lines.append(
            f"| `{key}` | {_fmt(summary['mean'])} | {_fmt(summary['p95'])} | {_fmt(summary['max'])} |"
        )
    lines.extend(
        [
            "",
            "## Shadow Rule",
            "",
            "The shadow rule remains default-off and has no selection effect.",
            "",
            f"- Enabled: `{report['shadow_rule']['enabled']}`",
            f"- Selection effect: `{report['shadow_rule']['selection_effect']}`",
            f"- Changed snapshots: `{report['shadow_rule']['changed_snapshots']}`",
            f"- Reason counts: `{report['shadow_rule']['reason_counts']}`",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            f"Next step: {decision['next_step']}",
            "",
        ]
    )
    return "\n".join(lines)


def _validate_config(config: WorldFrameBridgeConfig) -> None:
    if config.preserve_steps < 1:
        raise ValueError("preserve_steps must be at least 1.")
    if config.bridge_steps < 0:
        raise ValueError("bridge_steps must be nonnegative.")
    if config.donor_pool not in {"lower_logged_union_red", "all_nonselected"}:
        raise ValueError("invalid donor_pool.")
    if config.heading_mode not in {"world_donor_tail", "finite_difference"}:
        raise ValueError("invalid heading_mode.")
    if not 0.0 <= float(config.min_progress_ratio) <= 1.0:
        raise ValueError("min_progress_ratio must be in [0,1].")
    if not 0.0 <= float(config.min_snapshot_support_rate) <= 1.0:
        raise ValueError("min_snapshot_support_rate must be in [0,1].")
    for name in (
        "command_jerk_worse_budget_mps3",
        "command_lateral_worse_budget_mps2",
        "rollout_distance_loss_budget_m",
        "rollout_jerk_worse_budget_mps3",
        "rollout_lateral_worse_budget_mps2",
        "shadow_progress_loss_budget_m",
        "shadow_smoothness_loss_budget",
    ):
        value = float(getattr(config, name))
        if not np.isfinite(value) or value < 0.0:
            raise ValueError(f"{name} must be nonnegative.")
    for value in config.progress_loss_budgets_m:
        if not np.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError("progress_loss_budgets_m must be nonnegative.")
    for value in config.smoothness_loss_budgets:
        if not np.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError("smoothness_loss_budgets must be nonnegative.")


def _validate_bridge_shape(
    horizon_steps: int,
    preserve_steps: int,
    bridge_steps: int,
) -> None:
    if preserve_steps < 1:
        raise ValueError("preserve_steps must be at least 1.")
    if bridge_steps < 0:
        raise ValueError("bridge_steps must be nonnegative.")
    if horizon_steps <= preserve_steps:
        raise ValueError("trajectory horizon must exceed preserve_steps.")


def _unwrap_heading_features(heading: np.ndarray) -> np.ndarray:
    raw = np.asarray(heading, dtype=np.float64)
    if raw.ndim != 2 or raw.shape[1] != 2:
        raise ValueError("heading must be [T,2].")
    norm = np.linalg.norm(raw, axis=1)
    if np.any(norm <= TOL):
        raise ValueError("heading vectors must have nonzero norm.")
    unit = raw / norm[:, None]
    return np.unwrap(np.arctan2(unit[:, 1], unit[:, 0]))


def _normalized_horizons(raw_horizons: Any, reference_steps: int) -> tuple[int, ...]:
    try:
        values = sorted(set(int(value) for value in raw_horizons))
    except TypeError:
        values = [3, 5, 10]
    horizons = tuple(value for value in values if 1 <= value <= int(reference_steps))
    if not horizons:
        raise ValueError("No valid PerfectTracker rollout horizons.")
    return horizons


def _tracker_vector(
    tracker: dict[str, np.ndarray],
    key: str,
    shape: tuple[int, ...],
) -> np.ndarray:
    value = np.asarray(tracker[key], dtype=np.float64).reshape(-1)
    if value.shape != shape or not np.all(np.isfinite(value)):
        raise ValueError(f"tracker metric {key!r} must be finite with shape {shape}.")
    return value


def _tracker_metrics_for_budget(
    tracker: dict[str, Any],
    config: WorldFrameBridgeConfig,
) -> dict[str, np.ndarray]:
    command = tracker["command"]
    horizon = str(config.rollout_horizon)
    if horizon not in tracker["open_loop"]["horizons"]:
        raise ValueError(f"Missing PerfectTracker rollout horizon {horizon}.")
    rollout = tracker["open_loop"]["horizons"][horizon]
    return {
        "command_jerk_mps3": np.asarray(
            command["jerk_magnitude_mps3"],
            dtype=np.float64,
        ),
        "command_lateral_mps2": np.asarray(
            command["lateral_acceleration_magnitude_mps2"],
            dtype=np.float64,
        ),
        "rollout_distance_m": np.asarray(rollout["distance_m"], dtype=np.float64),
        "rollout_jerk_mps3": np.asarray(
            rollout["max_vector_jerk_mps3"],
            dtype=np.float64,
        ),
        "rollout_lateral_mps2": np.asarray(
            rollout["max_lateral_acceleration_mps2"],
            dtype=np.float64,
        ),
    }


def _masked_min(values: np.ndarray, mask: np.ndarray) -> float | None:
    active = np.asarray(values, dtype=np.float64)[np.asarray(mask, dtype=bool)]
    if active.size == 0:
        return None
    return float(np.min(active))


def _masked_max(values: np.ndarray, mask: np.ndarray) -> float | None:
    active = np.asarray(values, dtype=np.float64)[np.asarray(mask, dtype=bool)]
    if active.size == 0:
        return None
    return float(np.max(active))


def _max_abs_error(left: np.ndarray | None, right: np.ndarray) -> float | None:
    if left is None:
        return None
    return float(np.max(np.abs(np.asarray(left, dtype=np.float64) - right)))


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
        "p50": float(np.percentile(arr, 50.0)),
        "p95": float(np.percentile(arr, 95.0)),
        "max": float(np.max(arr)),
    }


def _smoothstep(value: float) -> float:
    u = min(max(float(value), 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.6g}"


if __name__ == "__main__":
    main()
