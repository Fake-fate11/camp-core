#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
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


TOL = 1e-12
SNAPSHOT_GLOB = "camp_microbenchmark_step_*.npz"
REQUIRED_REWARD_KEYS = (
    "lanes",
    "route_lanes",
    "line_strings",
    "ego_shape",
    "neighbor_agents_future",
    "neighbor_agents_past",
    "goal_pose",
)


@dataclass(frozen=True)
class SpliceConfig:
    anchor_steps: int = 10
    blend_steps: int = 10
    heading_mode: str = "finite_difference"
    donor_pool: str = "lower_logged_union_red"
    min_progress_ratio: float = 0.8
    progress_loss_budgets_m: tuple[float, ...] = (0.5, 1.0, 1.5)
    smoothness_loss_budgets: tuple[float, ...] = (0.0, 0.5, 1.0)
    shadow_rule_enabled: bool = False
    shadow_progress_loss_budget_m: float = 1.0
    shadow_smoothness_loss_budget: float = 0.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline transformed-candidate recompute gate for fixed DP/CAMP "
            "microbenchmark snapshots. The gate constructs H10-preserving "
            "splice candidates and recomputes DP near-horizon reward and "
            "full-horizon red-light cost. It is not an online selector."
        )
    )
    parser.add_argument("--snapshot_dir", type=Path, required=True)
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--reward_config", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--label", default=None)
    parser.add_argument("--anchor_steps", type=int, default=10)
    parser.add_argument("--blend_steps", type=int, default=10)
    parser.add_argument(
        "--heading_mode",
        choices=("finite_difference", "donor_offset"),
        default="finite_difference",
    )
    parser.add_argument(
        "--donor_pool",
        choices=("lower_logged_union_red", "all_nonselected"),
        default="lower_logged_union_red",
    )
    parser.add_argument("--min_progress_ratio", type=float, default=0.8)
    parser.add_argument(
        "--progress_loss_budget_m",
        action="append",
        type=float,
        default=None,
        help=(
            "Absolute DP reward-progress loss budgets for offline sensitivity. "
            "May be repeated. Defaults to 0.5, 1.0, 1.5."
        ),
    )
    parser.add_argument(
        "--smoothness_loss_budget",
        action="append",
        type=float,
        default=None,
        help=(
            "DP smoothness reward loss budgets for offline comfort-proxy "
            "sensitivity. May be repeated. Defaults to 0.0, 0.5, 1.0."
        ),
    )
    parser.add_argument(
        "--enable_shadow_rule",
        action="store_true",
        help=(
            "Enable default-off fixed-snapshot shadow selection over transformed "
            "candidates. This is offline analysis only and has no selection effect."
        ),
    )
    parser.add_argument("--shadow_progress_loss_budget_m", type=float, default=1.0)
    parser.add_argument("--shadow_smoothness_loss_budget", type=float, default=0.5)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        snapshot_dir=args.snapshot_dir,
        diffusion_repo=args.diffusion_repo,
        reward_config_path=args.reward_config,
        device=args.device,
        label=args.label,
        config=SpliceConfig(
            anchor_steps=args.anchor_steps,
            blend_steps=args.blend_steps,
            heading_mode=args.heading_mode,
            donor_pool=args.donor_pool,
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
            shadow_rule_enabled=bool(args.enable_shadow_rule),
            shadow_progress_loss_budget_m=args.shadow_progress_loss_budget_m,
            shadow_smoothness_loss_budget=args.shadow_smoothness_loss_budget,
        ),
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
    config: SpliceConfig = SpliceConfig(),
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
        candidates = np.asarray(arrays["candidates"], dtype=np.float64)
        baseline_scores = _score_trajectories(
            candidates,
            arrays=arrays,
            metadata=metadata,
            replay_module=replay_module,
            reward_config=reward_config,
            torch=torch,
            device=device,
        )
        donor_indices = _donor_indices(
            arrays,
            metadata,
            config.donor_pool,
            candidates.shape[0],
        )
        transformed_candidates = build_splice_candidates(
            candidates,
            selected_index=int(metadata["selected_index"]),
            donor_indices=donor_indices,
            anchor_steps=config.anchor_steps,
            blend_steps=config.blend_steps,
            heading_mode=config.heading_mode,
        )
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
        rows.append(
            _snapshot_report_row(
                snapshot_path,
                arrays,
                metadata,
                donor_indices,
                baseline_scores,
                transformed_scores,
                config,
            )
        )

    return {
        "analysis": {
            "name": "dp_camp_splice_recompute_gate_v1",
            "role": (
                "offline transformed-candidate DP reward/full-red recompute "
                "gate over fixed microbenchmark snapshots"
            ),
            "label": label,
            "training": False,
            "online_selector_change": False,
            "selection_effect": False,
            "uses_outcome_labels": False,
            "future_outcome_leakage": False,
            "recomputes_dp_reward_or_red_light": True,
            "convexity_boundary": (
                "This gate constructs deterministic transformed candidates "
                "from fixed current-tick snapshot constants, then recomputes "
                "DP reward/red-light diagnostics for those fixed candidates. "
                "It is not Benders and provides no dual cuts. If the resulting "
                "fixed per-candidate diagnostics are later atomized, CAMP "
                "scoring remains affine in w and the simplex/CVaR/L2 master "
                "remains convex only for that fixed finite candidate set."
            ),
        },
        "config": asdict(config),
        "snapshots": {
            "count": len(rows),
            "with_donors": sum(1 for row in rows if row["donor_count"] > 0),
            "with_recomputed_lower_union_red": sum(
                1 for row in rows if row["transformed"]["has_lower_union_red"]
            ),
            "with_recomputed_lower_full_red": sum(
                1 for row in rows if row["transformed"]["has_lower_full_red"]
            ),
            "selected_h30_safe_full_red": sum(
                1 for row in rows if row["selected_h30_safe_full_red"]
            ),
        },
        "baseline_recompute": _summarize_baseline(rows),
        "transformed": _summarize_transformed(rows),
        "shadow_rule": _summarize_shadow_rule(rows, config),
        "rows": rows,
    }


def build_splice_candidates(
    candidates: np.ndarray,
    *,
    selected_index: int,
    donor_indices: np.ndarray,
    anchor_steps: int,
    blend_steps: int,
    heading_mode: str = "finite_difference",
) -> np.ndarray:
    raw = np.asarray(candidates, dtype=np.float64)
    if raw.ndim != 3 or raw.shape[0] <= 0 or raw.shape[2] < 2:
        raise ValueError("candidates must be [K,T,D>=2].")
    if selected_index < 0 or selected_index >= raw.shape[0]:
        raise ValueError("selected_index is out of range.")
    if raw.shape[1] <= anchor_steps:
        raise ValueError("candidate horizon must exceed anchor_steps.")
    selected = raw[selected_index]
    splices = []
    for donor_index in np.asarray(donor_indices, dtype=np.int64).tolist():
        if donor_index < 0 or donor_index >= raw.shape[0]:
            raise ValueError("donor index is out of range.")
        if donor_index == selected_index:
            continue
        splice = selected.copy()
        splice[:, :2] = h10_preserving_tail_splice_xy(
            selected[:, :2],
            raw[donor_index, :, :2],
            anchor_steps=anchor_steps,
            blend_steps=blend_steps,
        )
        if splice.shape[1] >= 4:
            if heading_mode == "finite_difference":
                heading = heading_features_from_xy(
                    splice[:, :2],
                    fallback=selected[:, 2:4],
                )
            elif heading_mode == "donor_offset":
                heading = h10_preserving_heading_splice(
                    selected[:, 2:4],
                    raw[donor_index, :, 2:4],
                    anchor_steps=anchor_steps,
                    blend_steps=blend_steps,
                )
            else:
                raise ValueError("invalid heading_mode.")
            splice[:, 2:4] = heading
        splices.append(splice)
    if not splices:
        return np.empty((0, raw.shape[1], raw.shape[2]), dtype=np.float64)
    return np.stack(splices)


def h10_preserving_tail_splice_xy(
    selected_xy: np.ndarray,
    donor_xy: np.ndarray,
    *,
    anchor_steps: int,
    blend_steps: int,
) -> np.ndarray:
    selected = np.asarray(selected_xy, dtype=np.float64)
    donor = np.asarray(donor_xy, dtype=np.float64)
    if selected.shape != donor.shape or selected.ndim != 2 or selected.shape[1] != 2:
        raise ValueError("selected_xy and donor_xy must both be [T,2].")
    if anchor_steps < 2:
        raise ValueError("anchor_steps must be at least 2.")
    if blend_steps < 0:
        raise ValueError("blend_steps must be nonnegative.")
    if selected.shape[0] <= anchor_steps:
        raise ValueError("trajectory length must exceed anchor_steps.")
    anchor_index = anchor_steps - 1
    tail = selected[anchor_index] + (donor - donor[anchor_index])
    splice = selected.copy()
    for step in range(anchor_index + 1, selected.shape[0]):
        if blend_steps == 0:
            weight = 1.0
        else:
            u = min(max((step - anchor_index) / float(blend_steps), 0.0), 1.0)
            weight = u * u * (3.0 - 2.0 * u)
        splice[step] = (1.0 - weight) * selected[step] + weight * tail[step]
    splice[:anchor_steps] = selected[:anchor_steps]
    return splice


def h10_preserving_heading_splice(
    selected_heading: np.ndarray,
    donor_heading: np.ndarray,
    *,
    anchor_steps: int,
    blend_steps: int,
) -> np.ndarray:
    selected_angle = _unwrap_heading_features(selected_heading)
    donor_angle = _unwrap_heading_features(donor_heading)
    if selected_angle.shape != donor_angle.shape:
        raise ValueError("selected_heading and donor_heading must both be [T,2].")
    if anchor_steps < 2:
        raise ValueError("anchor_steps must be at least 2.")
    if blend_steps < 0:
        raise ValueError("blend_steps must be nonnegative.")
    if selected_angle.shape[0] <= anchor_steps:
        raise ValueError("trajectory length must exceed anchor_steps.")

    anchor_index = anchor_steps - 1
    tail = selected_angle[anchor_index] + (
        donor_angle - donor_angle[anchor_index]
    )
    splice_angle = selected_angle.copy()
    for step in range(anchor_index + 1, selected_angle.shape[0]):
        if blend_steps == 0:
            weight = 1.0
        else:
            u = min(max((step - anchor_index) / float(blend_steps), 0.0), 1.0)
            weight = u * u * (3.0 - 2.0 * u)
        splice_angle[step] = (
            (1.0 - weight) * selected_angle[step] + weight * tail[step]
        )
    splice_angle[:anchor_steps] = selected_angle[:anchor_steps]
    return np.stack((np.cos(splice_angle), np.sin(splice_angle)), axis=1)


def _unwrap_heading_features(heading: np.ndarray) -> np.ndarray:
    raw = np.asarray(heading, dtype=np.float64)
    if raw.ndim != 2 or raw.shape[1] != 2:
        raise ValueError("heading must be [T,2].")
    norm = np.linalg.norm(raw, axis=1)
    if np.any(norm <= TOL):
        raise ValueError("heading vectors must have nonzero norm.")
    unit = raw / norm[:, None]
    return np.unwrap(np.arctan2(unit[:, 1], unit[:, 0]))


def heading_features_from_xy(
    xy: np.ndarray,
    *,
    fallback: np.ndarray | None = None,
) -> np.ndarray:
    points = np.asarray(xy, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("xy must be [T,2].")
    if points.shape[0] < 2:
        raise ValueError("xy must contain at least two points.")
    delta = np.empty_like(points)
    delta[:-1] = points[1:] - points[:-1]
    delta[-1] = points[-1] - points[-2]
    norm = np.linalg.norm(delta, axis=1, keepdims=True)
    headings = np.zeros((points.shape[0], 2), dtype=np.float64)
    valid = norm[:, 0] > TOL
    headings[valid] = delta[valid] / norm[valid]
    if fallback is not None:
        fb = np.asarray(fallback, dtype=np.float64)
        if fb.shape != headings.shape:
            raise ValueError("fallback heading must be [T,2].")
        headings[~valid] = fb[~valid]
    else:
        headings[~valid, 0] = 1.0
    return headings


def _load_runtime(
    diffusion_repo: Path,
    reward_config_path: Path,
) -> tuple[Any, Any, Any]:
    repo = Path(diffusion_repo).resolve()
    for path in (repo, repo / "diffusion_planner"):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
    import torch
    import scenario_generation.replay as replay_module
    from rlvr.autoresearch.tools.reward_config_from_json import load_reward_config

    return replay_module, load_reward_config(reward_config_path), torch


def _load_snapshot(path: Path) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    with np.load(path, allow_pickle=False) as payload:
        if "metadata_json" not in payload.files:
            raise ValueError(f"{path} missing metadata_json.")
        arrays = {key: payload[key] for key in payload.files if key != "metadata_json"}
        metadata = json.loads(str(payload["metadata_json"].item()))
    return arrays, metadata


def _validate_config(config: SpliceConfig) -> None:
    if config.anchor_steps < 2:
        raise ValueError("anchor_steps must be at least 2.")
    if config.blend_steps < 0:
        raise ValueError("blend_steps must be nonnegative.")
    if config.heading_mode not in {"finite_difference", "donor_offset"}:
        raise ValueError("invalid heading_mode.")
    if config.donor_pool not in {"lower_logged_union_red", "all_nonselected"}:
        raise ValueError("invalid donor_pool.")
    if not np.isfinite(config.min_progress_ratio) or not (
        0.0 <= config.min_progress_ratio <= 1.0
    ):
        raise ValueError("min_progress_ratio must be in [0,1].")
    for value in config.progress_loss_budgets_m:
        if not np.isfinite(value) or value < 0.0:
            raise ValueError("progress_loss_budgets_m must be nonnegative.")
    for value in config.smoothness_loss_budgets:
        if not np.isfinite(value) or value < 0.0:
            raise ValueError("smoothness_loss_budgets must be nonnegative.")
    if (
        not np.isfinite(config.shadow_progress_loss_budget_m)
        or config.shadow_progress_loss_budget_m < 0.0
    ):
        raise ValueError("shadow_progress_loss_budget_m must be nonnegative.")
    if (
        not np.isfinite(config.shadow_smoothness_loss_budget)
        or config.shadow_smoothness_loss_budget < 0.0
    ):
        raise ValueError("shadow_smoothness_loss_budget must be nonnegative.")


def _validate_snapshot(
    arrays: dict[str, np.ndarray],
    metadata: dict[str, Any],
    snapshot_path: Path,
) -> None:
    if "candidates" not in arrays:
        raise ValueError(f"{snapshot_path} missing candidates.")
    candidates = np.asarray(arrays["candidates"])
    if candidates.ndim != 3 or candidates.shape[0] <= 0 or candidates.shape[2] < 2:
        raise ValueError(f"{snapshot_path} candidates must be [K,T,D>=2].")
    selected = int(metadata.get("selected_index", -1))
    if selected < 0 or selected >= candidates.shape[0]:
        raise ValueError(f"{snapshot_path} selected_index is out of range.")
    missing = [
        f"reward_input__{key}"
        for key in REQUIRED_REWARD_KEYS
        if f"reward_input__{key}" not in arrays
    ]
    if missing:
        raise ValueError(f"{snapshot_path} missing required reward arrays: {missing}")


def _build_reward_data(
    arrays: dict[str, np.ndarray],
    *,
    torch: Any,
    device: str,
) -> dict[str, Any]:
    reward_data = {}
    for key in REQUIRED_REWARD_KEYS:
        array = np.asarray(arrays[f"reward_input__{key}"])
        if key == "goal_pose" and array.shape[-1] == 3:
            yaw = array[..., 2]
            array = np.stack(
                (array[..., 0], array[..., 1], np.cos(yaw), np.sin(yaw)),
                axis=-1,
            )
        tensor = torch.from_numpy(array).float().to(device)
        reward_data[key] = tensor.unsqueeze(0) if tensor.dim() == 3 else tensor
    return reward_data


def _score_trajectories(
    trajectories: np.ndarray,
    *,
    arrays: dict[str, np.ndarray],
    metadata: dict[str, Any],
    replay_module: Any,
    reward_config: Any,
    torch: Any,
    device: str,
) -> dict[str, Any]:
    from rlvr.reward import compute_red_light_score_batch, compute_reward_batch

    raw = np.asarray(trajectories, dtype=np.float32)
    if raw.ndim != 3:
        raise ValueError("trajectories must be [K,T,D].")
    scored = raw.copy()
    if bool(metadata["sg_smooth_enabled"]):
        scored = np.stack(
            [
                replay_module._sg_smooth_trajectory(
                    candidate,
                    int(metadata["sg_filter_window"]),
                    int(metadata["sg_filter_order"]),
                )
                for candidate in scored
            ]
        )
    reward_data = _build_reward_data(arrays, torch=torch, device=device)
    full_trajectories = torch.from_numpy(scored).float().to(device)
    reward_horizon = min(int(metadata["reward_horizon_steps"]), scored.shape[1])
    reward_trajectories = full_trajectories[:, :reward_horizon]
    reward_breakdowns = [
        _reward_to_dict(value)
        for value in compute_reward_batch(
            reward_trajectories,
            reward_data,
            reward_config,
        )
    ]
    full_red_scores = compute_red_light_score_batch(
        full_trajectories,
        reward_data,
        reward_config,
    )
    full_red_cost = np.maximum(
        -full_red_scores.detach().cpu().numpy().astype(np.float64),
        0.0,
    )
    near_red_cost = np.asarray(
        [max(-float(row.get("red_light", 0.0)), 0.0) for row in reward_breakdowns],
        dtype=np.float64,
    )
    return {
        "reward_breakdowns": reward_breakdowns,
        "near_red_cost": near_red_cost,
        "full_red_cost": full_red_cost,
        "union_red_cost": np.maximum(near_red_cost, full_red_cost),
        "reward_horizon_steps": reward_horizon,
    }


def reward_hard_feasibility(
    rewards: list[dict[str, Any]],
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
    return feasible, tuple(tuple(row) for row in reasons)


def reward_progress_screen(
    rewards: list[dict[str, Any]],
    hard_feasible: np.ndarray,
    *,
    min_progress_ratio: float,
) -> tuple[np.ndarray, tuple[tuple[str, ...], ...]]:
    feasible = np.asarray(hard_feasible, dtype=bool).copy()
    reasons: list[list[str]] = [[] for _ in rewards]
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
    return feasible, tuple(tuple(row) for row in reasons)


def reason_counts(
    reasons: tuple[tuple[str, ...], ...],
    mask: np.ndarray | None = None,
) -> dict[str, int]:
    if mask is None:
        active = np.ones(len(reasons), dtype=bool)
    else:
        active = np.asarray(mask, dtype=bool)
        if active.shape != (len(reasons),):
            raise ValueError("reason mask length must match reasons.")
    counts: dict[str, int] = {}
    for enabled, row in zip(active, reasons):
        if not enabled:
            continue
        for reason in row:
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _reward_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        return asdict(value)
    except TypeError:
        return dict(value)


def _donor_indices(
    arrays: dict[str, np.ndarray],
    metadata: dict[str, Any],
    donor_pool: str,
    count: int,
) -> np.ndarray:
    selected = int(metadata["selected_index"])
    indices = np.arange(count, dtype=np.int64)
    nonselected = indices[indices != selected]
    if donor_pool == "all_nonselected":
        return nonselected
    near = _optional_vector(arrays.get("candidate_planned_red_light_cost"), count)
    full = _optional_vector(
        arrays.get("candidate_full_horizon_planned_red_light_cost"),
        count,
    )
    if near is None or full is None:
        return np.empty(0, dtype=np.int64)
    union = np.maximum(near, full)
    return nonselected[union[nonselected] < union[selected] - TOL]


def _snapshot_report_row(
    snapshot_path: Path,
    arrays: dict[str, np.ndarray],
    metadata: dict[str, Any],
    donor_indices: np.ndarray,
    baseline_scores: dict[str, Any],
    transformed_scores: dict[str, Any] | None,
    config: SpliceConfig,
) -> dict[str, Any]:
    count = int(np.asarray(arrays["candidates"]).shape[0])
    selected = int(metadata["selected_index"])
    logged_near = _optional_vector(arrays.get("candidate_planned_red_light_cost"), count)
    logged_full = _optional_vector(
        arrays.get("candidate_full_horizon_planned_red_light_cost"),
        count,
    )
    selected_h30_safe_full_red = (
        logged_near is not None
        and logged_full is not None
        and logged_near[selected] <= TOL
        and logged_full[selected] > TOL
    )
    selected_full = float(baseline_scores["full_red_cost"][selected])
    selected_union = float(baseline_scores["union_red_cost"][selected])
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
    transformed = _transformed_summary(
        transformed_scores,
        selected_union_red=selected_union,
        selected_full_red=selected_full,
        selected_progress=selected_progress,
        selected_smoothness=selected_smoothness,
        config=config,
    )
    return {
        "snapshot_path": str(snapshot_path),
        "selection_step": int(metadata["selection_step"]),
        "selected_index": selected,
        "candidate_count": count,
        "donor_indices": [int(index) for index in donor_indices.tolist()],
        "donor_count": int(donor_indices.size),
        "selected_h30_safe_full_red": bool(selected_h30_safe_full_red),
        "baseline": {
            "reward_horizon_steps": int(baseline_scores["reward_horizon_steps"]),
            "selected_near_red": float(baseline_scores["near_red_cost"][selected]),
            "selected_full_red": selected_full,
            "selected_union_red": selected_union,
            "selected_progress": selected_progress,
            "selected_smoothness": selected_smoothness,
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
    }


def _transformed_summary(
    scores: dict[str, Any] | None,
    *,
    selected_union_red: float,
    selected_full_red: float,
    selected_progress: float,
    selected_smoothness: float,
    config: SpliceConfig,
) -> dict[str, Any]:
    if scores is None:
        return {
            "count": 0,
            "has_lower_union_red": False,
            "has_lower_full_red": False,
            "hard_feasible_count": 0,
            "progress_feasible_count": 0,
            "lower_union_red_hard_feasible_count": 0,
            "lower_union_red_progress_feasible_count": 0,
            "hard_infeasibility_reason_counts": {},
            "progress_infeasibility_reason_counts": {},
            "lower_union_red_hard_infeasibility_reason_counts": {},
            "lower_union_red_progress_infeasibility_reason_counts": {},
            "min_near_red": None,
            "min_full_red": None,
            "min_union_red": None,
            "lower_union_red_count": 0,
            "lower_full_red_count": 0,
            "budget_sensitivity": [],
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
    near = np.asarray(scores["near_red_cost"], dtype=np.float64)
    full = np.asarray(scores["full_red_cost"], dtype=np.float64)
    union = np.asarray(scores["union_red_cost"], dtype=np.float64)
    hard_feasible, hard_reasons = reward_hard_feasibility(scores["reward_breakdowns"])
    progress_feasible, progress_reasons = reward_progress_screen(
        scores["reward_breakdowns"],
        hard_feasible,
        min_progress_ratio=config.min_progress_ratio,
    )
    lower_union = union < selected_union_red - TOL
    progress = reward_metric_vector(scores["reward_breakdowns"], "progress")
    smoothness = reward_metric_vector(scores["reward_breakdowns"], "smoothness")
    budget_sensitivity = reward_budget_sensitivity(
        progress=progress,
        smoothness=smoothness,
        lower_union=lower_union,
        hard_feasible=hard_feasible,
        selected_progress=selected_progress,
        selected_smoothness=selected_smoothness,
        progress_loss_budgets_m=config.progress_loss_budgets_m,
        smoothness_loss_budgets=config.smoothness_loss_budgets,
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
        "has_lower_full_red": bool(np.any(full < selected_full_red - TOL)),
        "hard_feasible_count": int(np.sum(hard_feasible)),
        "progress_feasible_count": int(np.sum(progress_feasible)),
        "lower_union_red_hard_feasible_count": int(
            np.sum(lower_union & hard_feasible)
        ),
        "lower_union_red_progress_feasible_count": int(
            np.sum(lower_union & progress_feasible)
        ),
        "hard_infeasibility_reason_counts": reason_counts(
            hard_reasons,
            ~hard_feasible,
        ),
        "progress_infeasibility_reason_counts": reason_counts(
            progress_reasons,
            hard_feasible & ~progress_feasible,
        ),
        "lower_union_red_hard_infeasibility_reason_counts": reason_counts(
            hard_reasons,
            lower_union & ~hard_feasible,
        ),
        "lower_union_red_progress_infeasibility_reason_counts": reason_counts(
            progress_reasons,
            lower_union & hard_feasible & ~progress_feasible,
        ),
        "min_near_red": float(np.min(near)) if near.size else None,
        "min_full_red": float(np.min(full)) if full.size else None,
        "min_union_red": float(np.min(union)) if union.size else None,
        "lower_union_red_count": int(np.sum(lower_union)),
        "lower_full_red_count": int(np.sum(full < selected_full_red - TOL)),
        "budget_sensitivity": budget_sensitivity,
        "shadow_rule": shadow_rule,
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
        "lower_union_red_hard_feasible_count": int(
            sum(row["lower_union_red_hard_feasible_count"] for row in active)
        ),
        "lower_union_red_progress_feasible_count": int(
            sum(row["lower_union_red_progress_feasible_count"] for row in active)
        ),
        "hard_infeasibility_reason_counts": _sum_reason_counts(
            row["hard_infeasibility_reason_counts"] for row in active
        ),
        "progress_infeasibility_reason_counts": _sum_reason_counts(
            row["progress_infeasibility_reason_counts"] for row in active
        ),
        "lower_union_red_hard_infeasibility_reason_counts": _sum_reason_counts(
            row["lower_union_red_hard_infeasibility_reason_counts"]
            for row in active
        ),
        "lower_union_red_progress_infeasibility_reason_counts": _sum_reason_counts(
            row["lower_union_red_progress_infeasibility_reason_counts"]
            for row in active
        ),
        "min_union_red": _summary(
            [row["min_union_red"] for row in active if row["min_union_red"] is not None]
        ),
        "lower_union_red_count": int(
            sum(row["lower_union_red_count"] for row in active)
        ),
        "budget_sensitivity": _summarize_budget_sensitivity(active),
    }


def reward_metric_vector(rewards: list[dict[str, Any]], key: str) -> np.ndarray:
    values = np.asarray(
        [float(row.get(key, np.nan)) for row in rewards],
        dtype=np.float64,
    )
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ValueError(f"Reward metric {key!r} must be finite for every row.")
    return values


def reward_budget_sensitivity(
    *,
    progress: np.ndarray,
    smoothness: np.ndarray,
    lower_union: np.ndarray,
    hard_feasible: np.ndarray,
    selected_progress: float,
    selected_smoothness: float,
    progress_loss_budgets_m: tuple[float, ...],
    smoothness_loss_budgets: tuple[float, ...],
) -> list[dict[str, Any]]:
    progress_arr = np.asarray(progress, dtype=np.float64).reshape(-1)
    smoothness_arr = np.asarray(smoothness, dtype=np.float64).reshape(-1)
    lower_arr = np.asarray(lower_union, dtype=bool).reshape(-1)
    hard_arr = np.asarray(hard_feasible, dtype=bool).reshape(-1)
    if not (
        progress_arr.shape
        == smoothness_arr.shape
        == lower_arr.shape
        == hard_arr.shape
    ):
        raise ValueError("Budget sensitivity masks and metrics must align.")
    if not np.all(np.isfinite(progress_arr)) or not np.all(np.isfinite(smoothness_arr)):
        raise ValueError("Budget sensitivity metrics must be finite.")
    if not np.isfinite(selected_progress) or not np.isfinite(selected_smoothness):
        raise ValueError("Selected budget sensitivity metrics must be finite.")

    progress_loss = float(selected_progress) - progress_arr
    smoothness_loss = float(selected_smoothness) - smoothness_arr
    base = lower_arr & hard_arr
    rows: list[dict[str, Any]] = []
    for progress_budget in progress_loss_budgets_m:
        for smoothness_budget in smoothness_loss_budgets:
            if not np.isfinite(progress_budget) or progress_budget < 0.0:
                raise ValueError("progress_loss_budgets_m must be nonnegative.")
            if not np.isfinite(smoothness_budget) or smoothness_budget < 0.0:
                raise ValueError("smoothness_loss_budgets must be nonnegative.")
            mask = (
                base
                & (progress_loss <= float(progress_budget) + TOL)
                & (smoothness_loss <= float(smoothness_budget) + TOL)
            )
            rows.append(
                {
                    "progress_loss_budget_m": float(progress_budget),
                    "smoothness_loss_budget": float(smoothness_budget),
                    "count": int(np.sum(mask)),
                    "has_candidate": bool(np.any(mask)),
                    "min_progress_loss_m": _masked_min(progress_loss, mask),
                    "min_smoothness_loss": _masked_min(smoothness_loss, mask),
                }
            )
    return rows


def fixed_candidate_shadow_rule(
    *,
    union_red: np.ndarray,
    progress: np.ndarray,
    smoothness: np.ndarray,
    hard_feasible: np.ndarray,
    selected_union_red: float,
    selected_progress: float,
    selected_smoothness: float,
    enabled: bool,
    progress_loss_budget_m: float,
    smoothness_loss_budget: float,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "enabled": bool(enabled),
        "default_off": True,
        "selection_effect": False,
        "changed": False,
        "reason": "disabled",
        "budget": {
            "progress_loss_m": float(progress_loss_budget_m),
            "smoothness_loss": float(smoothness_loss_budget),
        },
        "admissible_count": 0,
        "chosen_transformed_index": None,
        "chosen_union_red": None,
        "chosen_progress_loss_m": None,
        "chosen_smoothness_loss": None,
    }
    if not enabled:
        return result
    if not np.isfinite(progress_loss_budget_m) or progress_loss_budget_m < 0.0:
        raise ValueError("shadow_progress_loss_budget_m must be nonnegative.")
    if not np.isfinite(smoothness_loss_budget) or smoothness_loss_budget < 0.0:
        raise ValueError("shadow_smoothness_loss_budget must be nonnegative.")
    union = np.asarray(union_red, dtype=np.float64).reshape(-1)
    progress_arr = np.asarray(progress, dtype=np.float64).reshape(-1)
    smoothness_arr = np.asarray(smoothness, dtype=np.float64).reshape(-1)
    hard_arr = np.asarray(hard_feasible, dtype=bool).reshape(-1)
    if not (union.shape == progress_arr.shape == smoothness_arr.shape == hard_arr.shape):
        raise ValueError("Shadow rule arrays must align.")
    if not (
        np.all(np.isfinite(union))
        and np.all(np.isfinite(progress_arr))
        and np.all(np.isfinite(smoothness_arr))
    ):
        raise ValueError("Shadow rule metrics must be finite.")
    if not (
        np.isfinite(selected_union_red)
        and np.isfinite(selected_progress)
        and np.isfinite(selected_smoothness)
    ):
        raise ValueError("Selected shadow rule metrics must be finite.")
    if np.any(union < 0.0) or float(selected_union_red) < 0.0:
        raise ValueError("Shadow rule red costs must be nonnegative.")

    result["reason"] = "no_transformed_candidates"
    if not union.size:
        return result

    progress_loss = float(selected_progress) - progress_arr
    smoothness_loss = float(selected_smoothness) - smoothness_arr
    lower_red = union < float(selected_union_red) - TOL
    lower_red_hard = lower_red & hard_arr
    admissible = (
        lower_red_hard
        & (progress_loss <= float(progress_loss_budget_m) + TOL)
        & (smoothness_loss <= float(smoothness_loss_budget) + TOL)
    )
    result["lower_red_hard_feasible_count"] = int(np.sum(lower_red_hard))
    result["admissible_count"] = int(np.sum(admissible))
    if not np.any(admissible):
        result["reason"] = "no_budget_admissible_lower_red_candidate"
        return result

    indices = np.flatnonzero(admissible)
    chosen = min(
        indices.tolist(),
        key=lambda idx: (
            float(union[idx]),
            float(smoothness_loss[idx]),
            float(progress_loss[idx]),
            int(idx),
        ),
    )
    result.update(
        {
            "changed": True,
            "reason": "budget_admissible_lower_red_candidate",
            "chosen_transformed_index": int(chosen),
            "chosen_union_red": float(union[chosen]),
            "chosen_progress_loss_m": float(progress_loss[chosen]),
            "chosen_smoothness_loss": float(smoothness_loss[chosen]),
        }
    )
    return result


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
    config: SpliceConfig,
) -> dict[str, Any]:
    cells = [row["transformed"]["shadow_rule"] for row in rows]
    summary: dict[str, Any] = {
        "enabled": bool(config.shadow_rule_enabled),
        "default_off": True,
        "selection_effect": False,
        "online_selector_change": False,
        "budget": {
            "progress_loss_m": float(config.shadow_progress_loss_budget_m),
            "smoothness_loss": float(config.shadow_smoothness_loss_budget),
        },
        "snapshots": len(cells),
        "changed_snapshots": int(sum(int(cell["changed"]) for cell in cells)),
        "admissible_count": int(sum(int(cell["admissible_count"]) for cell in cells)),
        "reason_counts": _sum_reason_counts(
            {cell["reason"]: 1} for cell in cells
        ),
    }
    chosen_union = [
        float(cell["chosen_union_red"])
        for cell in cells
        if cell["chosen_union_red"] is not None
    ]
    chosen_progress_loss = [
        float(cell["chosen_progress_loss_m"])
        for cell in cells
        if cell["chosen_progress_loss_m"] is not None
    ]
    chosen_smoothness_loss = [
        float(cell["chosen_smoothness_loss"])
        for cell in cells
        if cell["chosen_smoothness_loss"] is not None
    ]
    summary["chosen_union_red"] = _summary(chosen_union)
    summary["chosen_progress_loss_m"] = _summary(chosen_progress_loss)
    summary["chosen_smoothness_loss"] = _summary(chosen_smoothness_loss)
    return summary


def _masked_min(values: np.ndarray, mask: np.ndarray) -> float | None:
    active = np.asarray(values, dtype=np.float64)[np.asarray(mask, dtype=bool)]
    if not active.size:
        return None
    return float(np.min(active))


def _optional_vector(value: Any, count: int) -> np.ndarray | None:
    if value is None:
        return None
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != (count,) or not np.all(np.isfinite(arr)):
        return None
    return arr


def _max_abs_error(left: np.ndarray | None, right: np.ndarray) -> float | None:
    if left is None:
        return None
    return float(np.max(np.abs(np.asarray(left, dtype=np.float64) - right)))


def _summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "max": None}
    arr = np.asarray(values, dtype=np.float64)
    return {"mean": float(np.mean(arr)), "max": float(np.max(arr))}


def _sum_reason_counts(rows: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for reason, count in row.items():
            counts[reason] = counts.get(reason, 0) + int(count)
    return dict(sorted(counts.items()))


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Stop-Aware Splice Recompute Gate",
        "",
        "This is an offline fixed-snapshot recompute audit. It is not an online selector, replay result, or formal-seed experiment.",
        "",
        "## Inputs",
        "",
        f"- Snapshots: `{report['snapshots']['count']}`",
        f"- Donor pool: `{report['config']['donor_pool']}`",
        f"- Heading mode: `{report['config']['heading_mode']}`",
        f"- Anchor steps: `{report['config']['anchor_steps']}`",
        f"- Blend steps: `{report['config']['blend_steps']}`",
        f"- Progress loss budgets: `{report['config']['progress_loss_budgets_m']}`",
        f"- Smoothness loss budgets: `{report['config']['smoothness_loss_budgets']}`",
        f"- Shadow rule enabled: `{report['shadow_rule']['enabled']}`",
        f"- Shadow rule budget: `{report['shadow_rule']['budget']}`",
        "",
        "## Gate Summary",
        "",
        f"- Snapshots with donors: `{report['snapshots']['with_donors']}`",
        f"- Snapshots with selected h30-safe/full-red: `{report['snapshots']['selected_h30_safe_full_red']}`",
        f"- Snapshots with recomputed lower union-red transform: `{report['snapshots']['with_recomputed_lower_union_red']}`",
        f"- Transform count: `{report['transformed']['transform_count']}`",
        f"- Hard-feasible transforms: `{report['transformed']['hard_feasible_count']}`",
        f"- Progress-screen feasible transforms: `{report['transformed']['progress_feasible_count']}`",
        f"- Lower union-red hard-feasible transforms: `{report['transformed']['lower_union_red_hard_feasible_count']}`",
        f"- Lower union-red progress-feasible transforms: `{report['transformed']['lower_union_red_progress_feasible_count']}`",
        f"- Lower union-red hard infeasibility reasons: `{report['transformed']['lower_union_red_hard_infeasibility_reason_counts']}`",
        f"- Lower union-red progress infeasibility reasons: `{report['transformed']['lower_union_red_progress_infeasibility_reason_counts']}`",
        "",
        "## Budget Sensitivity",
        "",
        "The budget screen is posterior diagnostic evidence over fixed transformed candidates: lower union-red, DP hard-feasible, within absolute DP progress loss budget, and within DP smoothness reward loss budget.",
        "",
        "| Progress loss budget (m) | Smoothness loss budget | Candidate count | Snapshots with candidate |",
        "| ---: | ---: | ---: | ---: |",
    ]
    for cell in report["transformed"]["budget_sensitivity"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _fmt(cell["progress_loss_budget_m"]),
                    _fmt(cell["smoothness_loss_budget"]),
                    str(cell["count"]),
                    str(cell["snapshots_with_candidate"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Fixed-Candidate Shadow Rule",
            "",
            "This rule is default-off, offline-only, deterministic, and fail-closed. It does not change DP/CAMP selection.",
            "",
            f"- Enabled: `{report['shadow_rule']['enabled']}`",
            f"- Selection effect: `{report['shadow_rule']['selection_effect']}`",
            f"- Changed snapshots: `{report['shadow_rule']['changed_snapshots']}` / `{report['shadow_rule']['snapshots']}`",
            f"- Admissible transformed candidates: `{report['shadow_rule']['admissible_count']}`",
            f"- Reason counts: `{report['shadow_rule']['reason_counts']}`",
            f"- Chosen union-red max: `{_fmt(report['shadow_rule']['chosen_union_red']['max'])}`",
            f"- Chosen progress loss max: `{_fmt(report['shadow_rule']['chosen_progress_loss_m']['max'])}`",
            f"- Chosen smoothness loss max: `{_fmt(report['shadow_rule']['chosen_smoothness_loss']['max'])}`",
            "",
            "## Baseline Recompute Check",
            "",
            f"- Logged near-red max error: `{_fmt(report['baseline_recompute']['logged_near_red_max_abs_error']['max'])}`",
            f"- Logged full-red max error: `{_fmt(report['baseline_recompute']['logged_full_red_max_abs_error']['max'])}`",
            "",
            "## Rows",
            "",
            "| Step | Selected | Donors | Selected union-red | Min transformed union-red | Lower union-red | Lower union-red hard-feasible | Lower union-red progress-feasible |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["selection_step"]),
                    str(row["selected_index"]),
                    str(row["donor_count"]),
                    _fmt(row["baseline"]["selected_union_red"]),
                    _fmt(row["transformed"]["min_union_red"]),
                    str(row["transformed"]["lower_union_red_count"]),
                    str(row["transformed"]["lower_union_red_hard_feasible_count"]),
                    str(row["transformed"]["lower_union_red_progress_feasible_count"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["convexity_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.6g}"


if __name__ == "__main__":
    main()
