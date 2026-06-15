#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Callable

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.atoms.driver_atoms import (  # noqa: E402
    DriverAtomContext,
    compute_atom_bank_vector,
)
from camp_core.integrations.diffusion_planner import (  # noqa: E402
    _trajectory_comfort,
    compute_dp_prior_comfort_excess_costs,
    compute_dp_prior_deviation_costs,
    compute_lateral_comfort_shadow_costs,
    compute_perfect_tracker_command_diagnostics,
    compute_perfect_tracker_open_loop_rollout_diagnostics,
    compute_red_stopping_margin_costs,
    generate_candidate_trajectories,
)
from scripts.integrations import run_diffusion_planner_camp_replay as replay_runner  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replay fixed current-tick snapshots to attribute Diffusion Planner "
            "and CAMP component latency independently from closed-loop runtime."
        )
    )
    parser.add_argument("--snapshot_dir", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_markdown", type=Path, required=True)
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--model_path", type=Path, required=True)
    parser.add_argument("--model_args", type=Path, default=None)
    parser.add_argument("--reward_config", type=Path, required=True)
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--cpu_warmups", type=int, default=20)
    parser.add_argument("--cpu_repetitions", type=int, default=100)
    parser.add_argument("--gpu_warmups", type=int, default=10)
    parser.add_argument("--gpu_repetitions", type=int, default=30)
    return parser.parse_args()


def _validate_args(args: argparse.Namespace) -> None:
    if not args.snapshot_dir.is_dir():
        raise FileNotFoundError(f"Missing snapshot directory: {args.snapshot_dir}")
    if not args.diffusion_repo.is_dir():
        raise FileNotFoundError(f"Missing Diffusion Planner repo: {args.diffusion_repo}")
    if not args.model_path.is_file():
        raise FileNotFoundError(f"Missing model checkpoint: {args.model_path}")
    if args.model_args is not None and not args.model_args.is_file():
        raise FileNotFoundError(f"Missing model args: {args.model_args}")
    if not args.reward_config.is_file():
        raise FileNotFoundError(f"Missing reward config: {args.reward_config}")
    for name in (
        "cpu_warmups",
        "cpu_repetitions",
        "gpu_warmups",
        "gpu_repetitions",
    ):
        if getattr(args, name) < 1:
            raise ValueError(f"--{name} must be >= 1")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stats(samples: list[float]) -> dict[str, float]:
    values = np.asarray(samples, dtype=np.float64)
    return {
        "count": int(values.size),
        "mean_ms": float(np.mean(values)),
        "median_ms": float(np.median(values)),
        "p95_ms": float(np.percentile(values, 95)),
        "min_ms": float(np.min(values)),
        "max_ms": float(np.max(values)),
    }


def _load_snapshot(path: Path) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    with np.load(path, allow_pickle=False) as payload:
        arrays = {key: payload[key] for key in payload.files if key != "metadata_json"}
        metadata = json.loads(str(payload["metadata_json"].item()))
    return arrays, metadata


def _context_from_snapshot(
    arrays: dict[str, np.ndarray],
    metadata: dict[str, Any],
) -> DriverAtomContext:
    static = np.asarray(arrays["static_obstacles"], dtype=np.float64)
    return DriverAtomContext(
        dt=float(metadata["dt"]),
        lane_centerline=np.asarray(arrays["lane_centerline"], dtype=np.float64),
        static_obstacles=static if static.size else None,
        dynamic_obstacles=None,
        speed_limit=metadata["speed_limit"],
        desired_speed=metadata["desired_speed"],
        lane_half_width=float(metadata["lane_half_width"]),
        lane_corridor_buffer=float(metadata["lane_corridor_buffer"]),
        safety_radius=float(metadata["safety_radius"]),
        clearance_soft_margin=float(metadata["clearance_soft_margin"]),
        map_source=str(metadata["map_source"]),
    )


def _candidate_context(
    base_context: DriverAtomContext,
    candidate_obstacles: np.ndarray,
) -> DriverAtomContext:
    dynamic = {
        obstacle_idx: obstacle[:, :2]
        for obstacle_idx, obstacle in enumerate(candidate_obstacles)
        if np.any(np.abs(obstacle[:, :2]) > 1e-8)
    }
    return replace(base_context, dynamic_obstacles=dynamic)


def _profile_atom_bank_vector(
    context: DriverAtomContext,
    trajectory: np.ndarray,
) -> tuple[np.ndarray, dict[str, float]]:
    phase_seconds: dict[str, float] = {}

    start = time.perf_counter()
    traj_xy = np.asarray(trajectory, dtype=float)
    horizon = traj_xy.shape[0]
    dt = context.dt
    velocity = np.diff(traj_xy, axis=0) / dt if horizon >= 2 else np.zeros((0, 2))
    acceleration = (
        np.diff(velocity, axis=0) / dt if velocity.shape[0] >= 2 else np.zeros((0, 2))
    )
    jerk = (
        np.diff(acceleration, axis=0) / dt
        if acceleration.shape[0] >= 2
        else np.zeros((0, 2))
    )
    phase_seconds["kinematics"] = time.perf_counter() - start

    start = time.perf_counter()
    atoms: list[float] = []
    jerk_sq = np.sum(jerk**2, axis=1) if jerk.shape[0] else np.zeros(0)
    jerk_steps = len(jerk_sq)
    split_idx = max(1, jerk_steps // 3)
    for window_start, window_end in (
        (0, split_idx),
        (split_idx, jerk_steps),
        (0, jerk_steps),
    ):
        atoms.append(
            float(dt * np.sum(jerk_sq[window_start:window_end]))
            if window_start < window_end and window_start < jerk_steps
            else 0.0
        )
    phase_seconds["jerk_atoms"] = time.perf_counter() - start

    start = time.perf_counter()
    acceleration_sq = (
        np.sum(acceleration**2, axis=1) if acceleration.shape[0] else np.zeros(0)
    )
    atoms.append(
        float(np.sqrt(np.mean(acceleration_sq))) if acceleration_sq.size else 0.0
    )
    phase_seconds["acceleration_atom"] = time.perf_counter() - start

    start = time.perf_counter()
    speeds = np.linalg.norm(velocity, axis=1) if velocity.shape[0] else np.zeros(0)
    speed_limit = context.speed_limit if context.speed_limit is not None else 100.0
    for margin in (0.0, 0.5, 1.0):
        violation = np.maximum(0.0, speeds - (speed_limit - margin))
        atoms.append(float(dt * np.sum(violation**2)) if speeds.size else 0.0)
    phase_seconds["speed_atoms"] = time.perf_counter() - start

    if context.lane_centerline is not None:
        start = time.perf_counter()
        centerline = np.asarray(context.lane_centerline, dtype=float)
        segment_vectors = centerline[1:] - centerline[:-1]
        segment_lengths = np.maximum(
            np.linalg.norm(segment_vectors, axis=1),
            1e-6,
        )
        segment_directions = segment_vectors / segment_lengths[:, None]
        cumulative_s = np.concatenate([[0.0], np.cumsum(segment_lengths)])
        phase_seconds["centerline_setup"] = time.perf_counter() - start

        start = time.perf_counter()
        relative = traj_xy[:, np.newaxis, :] - centerline[np.newaxis, :-1, :]
        along = np.einsum("hmd,md->hm", relative, segment_directions)
        along = np.clip(along, 0.0, segment_lengths[np.newaxis, :])
        projections = (
            centerline[np.newaxis, :-1, :]
            + segment_directions[np.newaxis, :, :] * along[:, :, np.newaxis]
        )
        differences = traj_xy[:, np.newaxis, :] - projections
        distance_sq = np.sum(differences**2, axis=2)
        segment_indices = np.argmin(distance_sq, axis=1)
        row_indices = np.arange(traj_xy.shape[0])
        best_differences = differences[row_indices, segment_indices]
        best_directions = segment_directions[segment_indices]
        cross = (
            best_directions[:, 0] * best_differences[:, 1]
            - best_directions[:, 1] * best_differences[:, 0]
        )
        _ = cumulative_s[segment_indices] + along[row_indices, segment_indices]
        signed_offsets = np.sign(cross) * np.sqrt(
            distance_sq[row_indices, segment_indices]
        )
        phase_seconds["centerline_projection"] = time.perf_counter() - start
        lateral_offsets = np.abs(signed_offsets)
    else:
        phase_seconds["centerline_setup"] = 0.0
        phase_seconds["centerline_projection"] = 0.0
        lateral_offsets = np.zeros(horizon, dtype=float)

    start = time.perf_counter()
    lane_violation = np.maximum(0.0, lateral_offsets - context.lane_half_width)
    atoms.append(float(dt * np.sum(lane_violation**2)))
    phase_seconds["lane_hinge"] = time.perf_counter() - start

    start = time.perf_counter()
    minimum_distances = np.full(horizon, 999.0, dtype=float)
    if context.dynamic_obstacles:
        for obstacle_trajectory in context.dynamic_obstacles.values():
            obstacle_xy = np.asarray(obstacle_trajectory, dtype=float)[:, :2]
            obstacle_horizon = min(horizon, len(obstacle_xy))
            if obstacle_horizon == 0:
                continue
            distances = np.linalg.norm(
                traj_xy[:obstacle_horizon] - obstacle_xy[:obstacle_horizon],
                axis=1,
            )
            distances = np.where(np.isfinite(distances), distances, 999.0)
            minimum_distances[:obstacle_horizon] = np.minimum(
                minimum_distances[:obstacle_horizon],
                distances,
            )
    phase_seconds["dynamic_clearance"] = time.perf_counter() - start

    start = time.perf_counter()
    if context.static_obstacles is not None and len(context.static_obstacles) > 0:
        static_distances = np.linalg.norm(
            traj_xy[:, np.newaxis, :]
            - np.asarray(context.static_obstacles, dtype=float)[np.newaxis, :, :2],
            axis=2,
        )
        closest_static = np.min(static_distances, axis=1)
        closest_static = np.where(np.isfinite(closest_static), closest_static, 999.0)
        minimum_distances = np.minimum(minimum_distances, closest_static)
    phase_seconds["static_clearance"] = time.perf_counter() - start

    start = time.perf_counter()
    has_clearance = bool(context.dynamic_obstacles) or (
        context.static_obstacles is not None and len(context.static_obstacles) > 0
    )
    clearance_cost = 0.0
    if has_clearance:
        safe_distance = context.safety_radius + context.clearance_soft_margin
        intrusions = np.maximum(0.0, safe_distance - minimum_distances)
        clearance_cost = float(np.sum(intrusions**2))
    atoms.append(clearance_cost * dt)
    phase_seconds["clearance_hinge"] = time.perf_counter() - start

    return np.asarray(atoms, dtype=float), phase_seconds


def _time_cpu(
    function: Callable[[], Any],
    *,
    warmups: int,
    repetitions: int,
) -> list[float]:
    for _ in range(warmups):
        function()
    samples = []
    for _ in range(repetitions):
        start = time.perf_counter()
        function()
        samples.append((time.perf_counter() - start) * 1000.0)
    return samples


def _synchronize(torch: Any, device: str) -> None:
    if str(device).startswith("cuda"):
        torch.cuda.synchronize()


def _time_gpu(
    function: Callable[[], Any],
    *,
    torch: Any,
    device: str,
    warmups: int,
    repetitions: int,
) -> list[float]:
    for _ in range(warmups):
        function()
    _synchronize(torch, device)
    samples = []
    for _ in range(repetitions):
        _synchronize(torch, device)
        start = time.perf_counter()
        function()
        _synchronize(torch, device)
        samples.append((time.perf_counter() - start) * 1000.0)
    return samples


def _build_reward_data(
    arrays: dict[str, np.ndarray],
    *,
    torch: Any,
    device: str,
) -> dict[str, Any]:
    reward_data = {}
    for key in (
        "lanes",
        "route_lanes",
        "line_strings",
        "ego_shape",
        "neighbor_agents_future",
        "neighbor_agents_past",
        "goal_pose",
    ):
        snapshot_key = f"reward_input__{key}"
        if snapshot_key not in arrays:
            continue
        array = np.asarray(arrays[snapshot_key])
        if key == "goal_pose" and array.shape[-1] == 3:
            yaw = array[..., 2]
            array = np.stack(
                (array[..., 0], array[..., 1], np.cos(yaw), np.sin(yaw)),
                axis=-1,
            )
        tensor = torch.from_numpy(array).float().to(device)
        reward_data[key] = tensor.unsqueeze(0) if tensor.dim() == 3 else tensor
    return reward_data


def _build_model_inputs(
    arrays: dict[str, np.ndarray],
    metadata: dict[str, Any],
    *,
    torch: Any,
    device: str,
) -> dict[str, Any]:
    inputs = {}
    for key in metadata["model_input_keys"]:
        array = np.asarray(arrays[f"model_input__{key}"])
        inputs[key] = torch.from_numpy(array).to(device)
    return inputs


def _benchmark_snapshot(
    path: Path,
    *,
    model: Any,
    model_args: Any,
    reward_config: Any,
    replay_module: Any,
    torch: Any,
    device: str,
    cpu_warmups: int,
    cpu_repetitions: int,
    gpu_warmups: int,
    gpu_repetitions: int,
) -> dict[str, Any]:
    arrays, metadata = _load_snapshot(path)
    candidates = np.asarray(arrays["candidates"], dtype=np.float64)
    candidate_obstacles = np.asarray(arrays["candidate_obstacles"], dtype=np.float64)
    base_context = _context_from_snapshot(arrays, metadata)
    contexts = [
        _candidate_context(base_context, candidate_obstacles[index])
        for index in range(candidates.shape[0])
    ]

    expected_base_atoms = np.asarray(arrays["selection_atoms"], dtype=np.float64)[:, :9]
    official_base_atoms = np.vstack(
        [
            compute_atom_bank_vector(context, candidate[:, :2])
            for context, candidate in zip(contexts, candidates)
        ]
    )
    np.testing.assert_allclose(
        official_base_atoms,
        expected_base_atoms,
        rtol=1e-12,
        atol=1e-12,
    )

    profiled_base_atoms = []
    for context, candidate in zip(contexts, candidates):
        profiled, _ = _profile_atom_bank_vector(context, candidate[:, :2])
        profiled_base_atoms.append(profiled)
    profiled_base_atoms_array = np.vstack(profiled_base_atoms)
    np.testing.assert_allclose(
        profiled_base_atoms_array,
        official_base_atoms,
        rtol=1e-12,
        atol=1e-12,
    )

    def atom_total() -> np.ndarray:
        base_atoms = np.vstack(
            [
                compute_atom_bank_vector(context, candidate[:, :2])
                for context, candidate in zip(contexts, candidates)
            ]
        )
        lateral = np.asarray(
            [
                _trajectory_comfort(candidate, base_context.dt)[1]
                for candidate in candidates
            ],
            dtype=np.float64,
        )
        return np.concatenate((base_atoms, lateral.reshape(-1, 1)), axis=1)

    atom_total_samples = _time_cpu(
        atom_total,
        warmups=cpu_warmups,
        repetitions=cpu_repetitions,
    )
    profile_samples: dict[str, list[float]] = {}
    for _ in range(cpu_warmups):
        for context, candidate in zip(contexts, candidates):
            _profile_atom_bank_vector(context, candidate[:, :2])
        for candidate in candidates:
            _trajectory_comfort(candidate, base_context.dt)
    for _ in range(cpu_repetitions):
        phase_totals: dict[str, float] = {}
        for context, candidate in zip(contexts, candidates):
            _, phases = _profile_atom_bank_vector(context, candidate[:, :2])
            for name, seconds in phases.items():
                phase_totals[name] = phase_totals.get(name, 0.0) + seconds
        start = time.perf_counter()
        for candidate in candidates:
            _trajectory_comfort(candidate, base_context.dt)
        phase_totals["extra_lateral_atom"] = time.perf_counter() - start
        for name, seconds in phase_totals.items():
            profile_samples.setdefault(name, []).append(seconds * 1000.0)

    selection_normalized = np.asarray(
        arrays["selection_normalized_atoms"],
        dtype=np.float64,
    )
    selection_weights = np.asarray(arrays["selection_weights"], dtype=np.float64)
    feasible_mask = np.asarray(arrays["feasible_mask"], dtype=bool)

    def affine_selection() -> tuple[np.ndarray, int]:
        scores = selection_normalized @ selection_weights
        if not bool(metadata["used_fallback"]):
            scores = scores.copy()
            scores[~feasible_mask] = np.inf
        return scores, int(np.argmin(scores))

    replay_scores, replay_index = affine_selection()
    np.testing.assert_allclose(
        replay_scores,
        np.asarray(arrays["selection_scores"], dtype=np.float64),
        rtol=1e-12,
        atol=1e-12,
    )
    if replay_index != int(metadata["selected_index"]):
        raise AssertionError(
            f"Affine selection mismatch for {path}: "
            f"{replay_index} != {metadata['selected_index']}"
        )
    affine_samples = _time_cpu(
        affine_selection,
        warmups=cpu_warmups,
        repetitions=cpu_repetitions,
    )

    audit_functions = {
        "audit_dp_prior_deviation": lambda: compute_dp_prior_deviation_costs(
            candidates
        ),
        "audit_dp_prior_comfort": lambda: compute_dp_prior_comfort_excess_costs(
            candidates,
            base_context.dt,
            horizon_steps=int(metadata["outcome_horizon_steps"]),
        ),
        "audit_lateral_comfort": lambda: compute_lateral_comfort_shadow_costs(
            candidates,
            base_context.dt,
            horizon_steps=int(metadata["outcome_horizon_steps"]),
        ),
        "audit_red_stopping_margin": lambda: compute_red_stopping_margin_costs(
            candidates,
            np.asarray(arrays["red_route_points"], dtype=np.float64),
            base_context.dt,
        ),
    }
    prepared_candidates = replay_runner._prepare_perfect_tracker_reference_candidates(
        candidates,
        type(
            "_SnapshotSpawnConfig",
            (),
            {
                "sg_smooth_enabled": metadata["sg_smooth_enabled"],
                "sg_filter_window": metadata["sg_filter_window"],
                "sg_filter_order": metadata["sg_filter_order"],
            },
        )(),
    )
    command_kwargs = {
        "dt": base_context.dt,
        "current_speed_mps": float(metadata["current_speed_mps"]),
        "current_longitudinal_acceleration_mps2": float(
            metadata["current_longitudinal_acceleration_mps2"]
        ),
    }
    command_result = compute_perfect_tracker_command_diagnostics(
        prepared_candidates,
        **command_kwargs,
    )
    audit_functions["audit_perfect_tracker_command"] = lambda: (
        compute_perfect_tracker_command_diagnostics(
            prepared_candidates,
            **command_kwargs,
        )
    )
    audit_functions["audit_perfect_tracker_open_loop"] = lambda: (
        compute_perfect_tracker_open_loop_rollout_diagnostics(
            command_result["postprocessed_reference"][
                :, : max(metadata["perfect_tracker_open_loop_horizons"])
            ],
            postprocessed_tail_reference_xy=command_result[
                "postprocessed_tail_reference_xy"
            ],
            full_horizon_steps=int(metadata["candidate_horizon_steps"]),
            dt=base_context.dt,
            current_speed_mps=float(metadata["current_speed_mps"]),
            current_acceleration_ego_xy=np.asarray(
                arrays["current_acceleration_ego_xy"],
                dtype=np.float64,
            ),
            horizons=tuple(metadata["perfect_tracker_open_loop_horizons"]),
        )
    )

    phases: dict[str, dict[str, Any]] = {
        "camp_atom_current_total": {
            "stats": _stats(atom_total_samples),
            "samples_ms": atom_total_samples,
        },
        "camp_affine_scoring": {
            "stats": _stats(affine_samples),
            "samples_ms": affine_samples,
        },
    }
    for name, samples in profile_samples.items():
        phases[f"camp_atom_{name}"] = {
            "stats": _stats(samples),
            "samples_ms": samples,
        }
    for name, function in audit_functions.items():
        samples = _time_cpu(
            function,
            warmups=cpu_warmups,
            repetitions=cpu_repetitions,
        )
        phases[name] = {"stats": _stats(samples), "samples_ms": samples}

    model_inputs = _build_model_inputs(
        arrays,
        metadata,
        torch=torch,
        device=device,
    )

    def generate() -> tuple[np.ndarray, np.ndarray, Any]:
        seed = int(metadata["candidate_generation_seed"])
        torch.manual_seed(seed)
        if str(device).startswith("cuda"):
            torch.cuda.manual_seed_all(seed)
        return generate_candidate_trajectories(
            model,
            model_args,
            model_inputs,
            num_candidates=int(metadata["num_candidates"]),
            noise_scale=float(metadata["candidate_noise_scale"]),
            deterministic_first=True,
            reference_blend_steps=metadata["candidate_reference_blend_steps"],
        )

    generation_a = generate()[0]
    generation_b = generate()[0]
    generation_max_abs_error = float(
        np.max(np.abs(generation_a.astype(np.float64) - generation_b.astype(np.float64)))
    )
    generation_samples = _time_gpu(
        generate,
        torch=torch,
        device=device,
        warmups=gpu_warmups,
        repetitions=gpu_repetitions,
    )
    phases["dp_candidate_generation"] = {
        "stats": _stats(generation_samples),
        "samples_ms": generation_samples,
    }

    from rlvr.reward import compute_red_light_score_batch, compute_reward_batch

    reward_data = _build_reward_data(arrays, torch=torch, device=device)
    scored_candidates = candidates.astype(np.float32).copy()
    if bool(metadata["sg_smooth_enabled"]):
        scored_candidates = np.stack(
            [
                replay_module._sg_smooth_trajectory(
                    candidate,
                    int(metadata["sg_filter_window"]),
                    int(metadata["sg_filter_order"]),
                )
                for candidate in scored_candidates
            ]
        )
    full_trajectories = torch.from_numpy(scored_candidates).float().to(device)
    reward_trajectories = full_trajectories[
        :, : int(metadata["reward_horizon_steps"])
    ]

    def near_reward() -> list[Any]:
        return compute_reward_batch(
            reward_trajectories,
            reward_data,
            reward_config,
        )

    def full_red() -> Any:
        return compute_red_light_score_batch(
            full_trajectories,
            reward_data,
            reward_config,
        )

    near_a = [asdict(value) for value in near_reward()]
    near_b = [asdict(value) for value in near_reward()]
    reward_max_abs_error = 0.0
    for first, second in zip(near_a, near_b):
        for key in first:
            reward_max_abs_error = max(
                reward_max_abs_error,
                abs(float(first[key]) - float(second[key])),
            )
    near_reward_samples = _time_gpu(
        near_reward,
        torch=torch,
        device=device,
        warmups=gpu_warmups,
        repetitions=gpu_repetitions,
    )
    full_red_samples = _time_gpu(
        full_red,
        torch=torch,
        device=device,
        warmups=gpu_warmups,
        repetitions=gpu_repetitions,
    )
    phases["dp_near_horizon_reward"] = {
        "stats": _stats(near_reward_samples),
        "samples_ms": near_reward_samples,
    }
    phases["dp_full_horizon_red"] = {
        "stats": _stats(full_red_samples),
        "samples_ms": full_red_samples,
    }

    return {
        "snapshot_path": str(path),
        "snapshot_sha256": _sha256(path),
        "metadata": metadata,
        "dimensions": {
            "candidates": list(candidates.shape),
            "candidate_obstacles": list(candidate_obstacles.shape),
            "centerline": list(np.asarray(arrays["lane_centerline"]).shape),
            "static_obstacles": list(np.asarray(arrays["static_obstacles"]).shape),
        },
        "equivalence": {
            "official_vs_snapshot_base_atom_max_abs_error": float(
                np.max(np.abs(official_base_atoms - expected_base_atoms))
            ),
            "profiled_vs_official_base_atom_max_abs_error": float(
                np.max(np.abs(profiled_base_atoms_array - official_base_atoms))
            ),
            "affine_selected_index": replay_index,
            "candidate_generation_repeat_max_abs_error": (
                generation_max_abs_error
            ),
            "reward_repeat_max_abs_error": reward_max_abs_error,
        },
        "phases": phases,
    }


def _aggregate(snapshot_reports: list[dict[str, Any]]) -> dict[str, Any]:
    phase_names = sorted(
        {
            name
            for report in snapshot_reports
            for name in report["phases"]
        }
    )
    aggregate = {}
    for phase_name in phase_names:
        medians = [
            report["phases"][phase_name]["stats"]["median_ms"]
            for report in snapshot_reports
            if phase_name in report["phases"]
        ]
        p95_values = [
            report["phases"][phase_name]["stats"]["p95_ms"]
            for report in snapshot_reports
            if phase_name in report["phases"]
        ]
        aggregate[phase_name] = {
            "snapshot_count": len(medians),
            "median_of_snapshot_medians_ms": float(np.median(medians)),
            "p95_of_snapshot_p95_ms": float(np.percentile(p95_values, 95)),
            "max_snapshot_p95_ms": float(np.max(p95_values)),
        }
    return aggregate


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# DP CAMP Component Microbenchmark",
        "",
        f"- Snapshots: `{len(report['snapshots'])}`",
        f"- Device: `{report['environment']['device']}`",
        f"- CPU repetitions: `{report['protocol']['cpu_repetitions']}`",
        f"- GPU repetitions: `{report['protocol']['gpu_repetitions']}`",
        "",
        "| Phase | Median of snapshot medians (ms) | "
        "p95 of snapshot p95 (ms) | Max snapshot p95 (ms) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, values in sorted(report["aggregate"].items()):
        lines.append(
            f"| `{name}` | "
            f"{values['median_of_snapshot_medians_ms']:.6f} | "
            f"{values['p95_of_snapshot_p95_ms']:.6f} | "
            f"{values['max_snapshot_p95_ms']:.6f} |"
        )
    lines.extend(
        [
            "",
            "Snapshot capture runs are diagnostic only and are not latency evidence.",
            "All CAMP atom and affine selection equivalence checks passed "
            "before timings were accepted.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    _validate_args(args)

    snapshot_paths = sorted(args.snapshot_dir.rglob("*.npz"))
    if not snapshot_paths:
        raise FileNotFoundError(
            f"No microbenchmark snapshots found under {args.snapshot_dir}"
        )

    replay_runner._install_diffusion_repo(args.diffusion_repo)
    import torch
    import scenario_generation.replay as replay_module
    from rlvr.autoresearch.tools.reward_config_from_json import load_reward_config

    device = args.device if torch.cuda.is_available() or args.device == "cpu" else "cpu"
    model, model_args = replay_runner._load_model(
        args.model_path,
        args.model_args,
        device,
    )
    reward_config = load_reward_config(args.reward_config)

    snapshot_reports = [
        _benchmark_snapshot(
            path,
            model=model,
            model_args=model_args,
            reward_config=reward_config,
            replay_module=replay_module,
            torch=torch,
            device=device,
            cpu_warmups=args.cpu_warmups,
            cpu_repetitions=args.cpu_repetitions,
            gpu_warmups=args.gpu_warmups,
            gpu_repetitions=args.gpu_repetitions,
        )
        for path in snapshot_paths
    ]
    report = {
        "schema_version": "dp_camp_component_microbenchmark_v1",
        "created_unix_seconds": time.time(),
        "protocol": {
            "cpu_warmups": args.cpu_warmups,
            "cpu_repetitions": args.cpu_repetitions,
            "gpu_warmups": args.gpu_warmups,
            "gpu_repetitions": args.gpu_repetitions,
            "atom_rtol": 1e-12,
            "atom_atol": 1e-12,
            "minimum_expected_online_saving_ms": 3.0,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "torch": torch.__version__,
            "device": device,
            "cuda_device": (
                torch.cuda.get_device_name(0)
                if str(device).startswith("cuda")
                else None
            ),
            "diffusion_repo": str(args.diffusion_repo),
            "model_path": str(args.model_path),
            "model_args": str(args.model_args) if args.model_args else None,
            "reward_config": str(args.reward_config),
        },
        "snapshots": snapshot_reports,
        "aggregate": _aggregate(snapshot_reports),
        "capture_runs_are_latency_evidence": False,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_markdown(args.output_markdown, report)
    print(f"Wrote {args.output_json}")
    print(f"Wrote {args.output_markdown}")


if __name__ == "__main__":
    main()
