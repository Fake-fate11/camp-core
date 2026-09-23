"""Frozen features and atoms for continuity-aware scene-conditioned CAMP.

The previous selected trajectory is an input produced by a fixed offline
behaviour rollout.  It is never recomputed from the Theta being optimized.
All candidate atoms below are therefore fixed before the convex master starts.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_v26_scene_camp_math import (
    V26_NORMALIZED_ATOM_CLIP,
    project_rows_to_simplex,
)
from camp_core.integrations.diffusion_planner_v26_sparse_schema import (
    V26_ATOM_STATUS_VOCABULARY,
    V26_GLOBAL_ATOM_NAMES,
    validate_v26_sparse_pool_artifact,
)


V26_SEQUENTIAL_ATOM_NAMES = V26_GLOBAL_ATOM_NAMES + (
    "previous_plan_position_rms_m",
    "previous_plan_circular_heading_mean_abs_rad",
    "previous_plan_velocity_mean_abs_mps",
    "previous_plan_longitudinal_acceleration_mean_abs_mps2",
    "ego_onset_longitudinal_acceleration_mismatch_mps2",
    "ego_onset_steering_mismatch_rad",
)
V26_SEQUENTIAL_NEW_ATOM_NAMES = V26_SEQUENTIAL_ATOM_NAMES[len(V26_GLOBAL_ATOM_NAMES) :]
V26_SEQUENTIAL_ATOM_INDEX = {
    name: index for index, name in enumerate(V26_SEQUENTIAL_ATOM_NAMES)
}

V26_SEQUENTIAL_CONTEXT_ROWS = (
    ("ego_longitudinal_velocity_mps", 1.0, "metres_per_second", False),
    ("ego_longitudinal_acceleration_mps2", 1.0, "metres_per_second_squared", False),
    ("ego_yaw_rate_rps", 1.0, "radians_per_second", False),
    ("ego_kinematic_steering_rad", 1.0, "radians", False),
    ("previous_plan_available", 1.0, "indicator", False),
    ("previous_plan_age_s", 1.0, "seconds", True),
    ("previous_target_longitudinal_offset_m", 1.0, "metres", True),
    ("previous_target_lateral_offset_m", 1.0, "metres", True),
    ("previous_target_heading_delta_rad", 1.0, "radians", True),
    ("previous_target_velocity_mps", 1.0, "metres_per_second", True),
    ("previous_target_acceleration_mps2", 1.0, "metres_per_second_squared", True),
    ("previous_target_steering_rad", 1.0, "radians", True),
    ("previous_plan_remaining_horizon_s", 1.0, "seconds", True),
)
V26_SEQUENTIAL_CONTEXT_NAMES = tuple(row[0] for row in V26_SEQUENTIAL_CONTEXT_ROWS)
V26_SEQUENTIAL_CONTEXT_DIMENSION = len(V26_SEQUENTIAL_CONTEXT_ROWS)
V26_SEQUENTIAL_CONTEXT_CLIP = 10.0
V26_SEQUENTIAL_WHEEL_BASE_M = 2.79
V26_SEQUENTIAL_DT_SECONDS = 0.1
V26_SEQUENTIAL_HORIZON_STEPS = 80


def _wrapped_angle(value: np.ndarray | float) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    return np.arctan2(np.sin(array), np.cos(array))


def quaternion_yaw(qw: float, qx: float, qy: float, qz: float) -> float:
    return float(
        math.atan2(
            2.0 * (float(qw) * float(qz) + float(qx) * float(qy)),
            1.0 - 2.0 * (float(qy) ** 2 + float(qz) ** 2),
        )
    )


def ego_longitudinal_state(metadata: Mapping[str, float]) -> dict[str, float]:
    """Project official nuPlan ego vectors into the current heading frame."""

    yaw = float(metadata["yaw"])
    cosine = math.cos(yaw)
    sine = math.sin(yaw)
    speed = float(metadata["vx"]) * cosine + float(metadata["vy"]) * sine
    acceleration = (
        float(metadata["acceleration_x"]) * cosine
        + float(metadata["acceleration_y"]) * sine
    )
    yaw_rate = float(metadata["yaw_rate"])
    steering = (
        math.atan(V26_SEQUENTIAL_WHEEL_BASE_M * yaw_rate / speed)
        if abs(speed) > 0.2
        else 0.0
    )
    return {
        "speed": speed,
        "acceleration": acceleration,
        "yaw_rate": yaw_rate,
        "steering": steering,
    }


def trajectory_world_xyhvas(
    trajectory: np.ndarray,
    *,
    ego_x: float,
    ego_y: float,
    ego_yaw: float,
    current_speed: float,
    dt_seconds: float = V26_SEQUENTIAL_DT_SECONDS,
    wheel_base_m: float = V26_SEQUENTIAL_WHEEL_BASE_M,
) -> np.ndarray:
    """Match the repaired Autoware message kinematics for one or more plans.

    Candidate input is ``[...,T,4]`` with ``x,y,cos,sin``.  Expert input may be
    ``[...,T,3]`` with ``x,y,heading``.  Output is ``[...,T,6]`` ordered as
    world ``x,y,heading,longitudinal_velocity,acceleration,steering``.
    """

    values = np.asarray(trajectory, dtype=np.float64)
    one = values.ndim == 2
    if one:
        values = values[None, ...]
    if values.ndim != 3 or values.shape[1] != V26_SEQUENTIAL_HORIZON_STEPS:
        raise ValueError("trajectory must be [T,C] or [K,T,C] with T=80")
    if values.shape[2] == 4:
        local_heading = np.unwrap(np.arctan2(values[:, :, 3], values[:, :, 2]), axis=1)
    elif values.shape[2] == 3:
        local_heading = np.unwrap(values[:, :, 2], axis=1)
    else:
        raise ValueError("trajectory coordinates must be xycs or xyh")
    if not np.all(np.isfinite(values)):
        raise ValueError("trajectory coordinates must be finite")

    local_xy = values[:, :, :2]
    previous_xy = np.concatenate(
        (np.zeros((values.shape[0], 1, 2), dtype=np.float64), local_xy[:, :-1]),
        axis=1,
    )
    displacement = local_xy - previous_xy
    longitudinal_velocity = (
        displacement[:, :, 0] * np.cos(local_heading)
        + displacement[:, :, 1] * np.sin(local_heading)
    ) / float(dt_seconds)
    previous_velocity = np.concatenate(
        (
            np.full((values.shape[0], 1), float(current_speed), dtype=np.float64),
            longitudinal_velocity[:, :-1],
        ),
        axis=1,
    )
    acceleration = (longitudinal_velocity - previous_velocity) / float(dt_seconds)
    previous_heading = np.concatenate(
        (np.zeros((values.shape[0], 1), dtype=np.float64), local_heading[:, :-1]),
        axis=1,
    )
    heading_rate = _wrapped_angle(local_heading - previous_heading) / float(dt_seconds)
    curvature = np.divide(
        heading_rate,
        longitudinal_velocity,
        out=np.zeros_like(heading_rate),
        where=np.abs(longitudinal_velocity) > 1e-6,
    )
    steering = np.arctan(float(wheel_base_m) * curvature)

    cosine = math.cos(float(ego_yaw))
    sine = math.sin(float(ego_yaw))
    world_x = float(ego_x) + cosine * local_xy[:, :, 0] - sine * local_xy[:, :, 1]
    world_y = float(ego_y) + sine * local_xy[:, :, 0] + cosine * local_xy[:, :, 1]
    world_heading = np.unwrap(local_heading + float(ego_yaw), axis=1)
    result = np.stack(
        (world_x, world_y, world_heading, longitudinal_velocity, acceleration, steering),
        axis=2,
    )
    return result[0] if one else result


def interpolate_world_xyhvas(
    values: np.ndarray, source_times: np.ndarray, target_times: np.ndarray
) -> np.ndarray:
    states = np.asarray(values, dtype=np.float64)
    source = np.asarray(source_times, dtype=np.float64)
    target = np.asarray(target_times, dtype=np.float64)
    if states.ndim != 2 or states.shape[1] != 6 or source.shape != (states.shape[0],):
        raise ValueError("world plan must be [T,6] with matching source times")
    if target.size == 0:
        return np.empty((0, 6), dtype=np.float64)
    result = np.empty((target.size, 6), dtype=np.float64)
    for column in (0, 1, 3, 4, 5):
        result[:, column] = np.interp(target, source, states[:, column])
    result[:, 2] = np.interp(target, source, np.unwrap(states[:, 2]))
    return result


def sequential_context(
    metadata: Mapping[str, float],
    *,
    previous_plan: np.ndarray | None,
    previous_plan_origin_seconds: float | None,
) -> np.ndarray:
    state = ego_longitudinal_state(metadata)
    base = [state["speed"], state["acceleration"], state["yaw_rate"], state["steering"]]
    current_seconds = float(metadata["timestamp_us"]) * 1e-6
    if previous_plan is None or previous_plan_origin_seconds is None:
        raw = np.asarray([*base, 0.0, *([0.0] * 8)], dtype=np.float64)
    else:
        source_times = float(previous_plan_origin_seconds) + V26_SEQUENTIAL_DT_SECONDS * np.arange(
            1, V26_SEQUENTIAL_HORIZON_STEPS + 1, dtype=np.float64
        )
        target_seconds = float(np.clip(current_seconds, source_times[0], source_times[-1]))
        target = interpolate_world_xyhvas(
            previous_plan, source_times, np.asarray([target_seconds], dtype=np.float64)
        )[0]
        dx = float(target[0]) - float(metadata["x"])
        dy = float(target[1]) - float(metadata["y"])
        cosine = math.cos(float(metadata["yaw"]))
        sine = math.sin(float(metadata["yaw"]))
        longitudinal = cosine * dx + sine * dy
        lateral = -sine * dx + cosine * dy
        age = current_seconds - float(previous_plan_origin_seconds)
        raw = np.asarray(
            [
                *base,
                1.0,
                age,
                longitudinal,
                lateral,
                float(_wrapped_angle(target[2] - float(metadata["yaw"]))),
                float(target[3]),
                float(target[4]),
                float(target[5]),
                max(8.0 - age, 0.0),
            ],
            dtype=np.float64,
        )
    scales = np.asarray([row[1] for row in V26_SEQUENTIAL_CONTEXT_ROWS], dtype=np.float64)
    normalized = np.clip(raw / scales, -V26_SEQUENTIAL_CONTEXT_CLIP, V26_SEQUENTIAL_CONTEXT_CLIP)
    if normalized.shape != (V26_SEQUENTIAL_CONTEXT_DIMENSION,) or not np.all(
        np.isfinite(normalized)
    ):
        raise ValueError("sequential context must be a finite fixed-length vector")
    return normalized


def sequential_atom_values(
    candidates_world: np.ndarray,
    expert_world: np.ndarray,
    *,
    current_origin_seconds: float,
    current_ego_acceleration: float,
    current_ego_steering: float,
    previous_plan: np.ndarray | None,
    previous_plan_origin_seconds: float | None,
) -> tuple[np.ndarray | None, np.ndarray | None, int]:
    """Return six raw candidate/expert atoms and the overlap sample count."""

    candidates = np.asarray(candidates_world, dtype=np.float64)
    expert = np.asarray(expert_world, dtype=np.float64)
    if candidates.ndim != 3 or candidates.shape[1:] != (80, 6):
        raise ValueError("candidate world trajectories must be [K,80,6]")
    if expert.shape != (80, 6):
        raise ValueError("expert world trajectory must be [80,6]")
    if previous_plan is None or previous_plan_origin_seconds is None:
        return None, None, 0
    current_times = float(current_origin_seconds) + 0.1 * np.arange(1, 81, dtype=np.float64)
    previous_times = float(previous_plan_origin_seconds) + 0.1 * np.arange(1, 81, dtype=np.float64)
    mask = (current_times >= previous_times[0] - 1e-9) & (
        current_times <= previous_times[-1] + 1e-9
    )
    common = current_times[mask]
    if common.size == 0:
        return None, None, 0
    previous = interpolate_world_xyhvas(previous_plan, previous_times, common)

    def continuity(values: np.ndarray) -> np.ndarray:
        position_delta = np.linalg.norm(values[:, :, :2] - previous[None, :, :2], axis=2)
        heading_delta = np.abs(_wrapped_angle(values[:, :, 2] - previous[None, :, 2]))
        velocity_delta = np.abs(values[:, :, 3] - previous[None, :, 3])
        acceleration_delta = np.abs(values[:, :, 4] - previous[None, :, 4])
        return np.column_stack(
            (
                np.sqrt(np.mean(position_delta * position_delta, axis=1)),
                np.mean(heading_delta, axis=1),
                np.mean(velocity_delta, axis=1),
                np.mean(acceleration_delta, axis=1),
            )
        )

    candidate_common = candidates[:, mask, :]
    expert_common = expert[None, mask, :]
    candidate_continuity = continuity(candidate_common)
    expert_continuity = continuity(expert_common)[0]
    candidate_onset = np.column_stack(
        (
            np.abs(candidates[:, 0, 4] - float(current_ego_acceleration)),
            np.abs(candidates[:, 0, 5] - float(current_ego_steering)),
        )
    )
    expert_onset = np.asarray(
        [
            abs(float(expert[0, 4]) - float(current_ego_acceleration)),
            abs(float(expert[0, 5]) - float(current_ego_steering)),
        ],
        dtype=np.float64,
    )
    candidate = np.column_stack((candidate_continuity, candidate_onset))
    expert_row = np.concatenate((expert_continuity, expert_onset))
    expert_matrix = np.broadcast_to(expert_row, candidate.shape).copy()
    if not np.all(np.isfinite(candidate)) or np.any(candidate < 0.0):
        raise ValueError("sequential candidate atoms must be finite and nonnegative")
    if not np.all(np.isfinite(expert_matrix)) or np.any(expert_matrix < 0.0):
        raise ValueError("sequential expert atoms must be finite and nonnegative")
    return candidate, expert_matrix, int(common.size)


def online_sequential_candidate_atom_values(
    candidates_world: np.ndarray,
    *,
    current_origin_seconds: float,
    current_ego_acceleration: float,
    current_ego_steering: float,
    previous_plan: np.ndarray | None,
    previous_plan_origin_seconds: float | None,
) -> tuple[np.ndarray | None, int]:
    """Compute only decision-time candidate atoms; no expert or actual future is read."""

    candidate, _, overlap = sequential_atom_values(
        candidates_world,
        np.asarray(candidates_world, dtype=np.float64)[0],
        current_origin_seconds=current_origin_seconds,
        current_ego_acceleration=current_ego_acceleration,
        current_ego_steering=current_ego_steering,
        previous_plan=previous_plan,
        previous_plan_origin_seconds=previous_plan_origin_seconds,
    )
    return candidate, overlap


def validate_sequential_sparse_pool_artifact(
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    if tuple(artifact.get("bank_atom_names", ())) != V26_SEQUENTIAL_ATOM_NAMES:
        raise ValueError("sequential artifact bank order differs from the fixed 21-bank")
    states = artifact.get("atom_states")
    if not isinstance(states, Sequence) or isinstance(states, (str, bytes)):
        raise ValueError("sequential atom states must be a sequence")
    if len(states) != len(V26_SEQUENTIAL_ATOM_NAMES):
        raise ValueError("sequential artifact must retain all 21 endpoint states")
    names = tuple(str(row.get("name")) for row in states)
    statuses = tuple(str(row.get("status")) for row in states)
    if names != V26_SEQUENTIAL_ATOM_NAMES or any(
        status not in V26_ATOM_STATUS_VOCABULARY for status in statuses
    ):
        raise ValueError("sequential endpoint identities or statuses are invalid")
    observed = tuple(str(name) for name in artifact.get("observed_atom_names", ()))
    expected_observed = tuple(
        name for name, status in zip(names, statuses) if status == "observed"
    )
    if observed != expected_observed:
        raise ValueError("sequential observed columns do not match endpoint states")
    indices = tuple(int(value) for value in artifact.get("observed_global_atom_indices", ()))
    expected_indices = tuple(V26_SEQUENTIAL_ATOM_INDEX[name] for name in observed)
    if indices != expected_indices:
        raise ValueError("sequential observed columns do not retain global order")
    candidate_count = artifact.get("K")
    if type(candidate_count) is not int or candidate_count < 1:
        raise ValueError("sequential artifact K must be a positive integer")
    candidate = np.asarray(artifact.get("candidate_atoms_raw"), dtype=np.float64)
    expert = np.asarray(artifact.get("expert_atoms_raw"), dtype=np.float64)
    shape = (candidate_count, len(observed))
    if candidate.shape != shape or expert.shape != shape:
        raise ValueError("sequential raw matrices must be [K,Q_pool]")
    if (
        not np.all(np.isfinite(candidate))
        or not np.all(np.isfinite(expert))
        or np.any(candidate < 0.0)
        or np.any(expert < 0.0)
    ):
        raise ValueError("sequential raw atoms must be finite and nonnegative")
    if artifact.get("T") != 80 or not np.isclose(
        float(artifact.get("dt_seconds", -1.0)), 0.1
    ):
        raise ValueError("sequential artifact must retain T80 and dt=0.1")
    if artifact.get("candidate0_row") != 0:
        raise ValueError("sequential artifact must retain candidate0=row0")
    identity = artifact.get("identity")
    if not isinstance(identity, Mapping):
        raise ValueError("sequential artifact identity must be a mapping")
    return {
        "identity": dict(identity),
        "status_pattern": statuses,
        "observed_atom_names": observed,
        "observed_global_atom_indices": indices,
        "candidate_atoms_raw": candidate,
        "expert_atoms_raw": expert,
    }


def scales_by_sequential_name(scale_document: Mapping[str, Any]) -> dict[str, float]:
    if tuple(scale_document.get("global_atom_names", ())) != V26_SEQUENTIAL_ATOM_NAMES:
        raise ValueError("scale document does not match the sequential atom bank")
    rows = scale_document.get("atom_rows")
    if not isinstance(rows, Sequence) or len(rows) != len(V26_SEQUENTIAL_ATOM_NAMES):
        raise ValueError("scale document must contain one row per sequential atom")
    result: dict[str, float] = {}
    for index, (name, row) in enumerate(zip(V26_SEQUENTIAL_ATOM_NAMES, rows)):
        value = row.get("scale") if isinstance(row, Mapping) else None
        if (
            row.get("global_atom_index") != index
            or row.get("atom_name") != name
            or row.get("status") != "identified"
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not np.isfinite(float(value))
            or float(value) <= 0.0
        ):
            raise ValueError(f"sequential atom scale is invalid: {name}")
        result[name] = float(value)
    return result


def normalize_sequential_sparse_pool(
    artifact: Mapping[str, Any], *, atom_scales: Mapping[str, float]
) -> dict[str, Any]:
    validated = validate_sequential_sparse_pool_artifact(artifact)
    names = validated["observed_atom_names"]
    scales = np.asarray([atom_scales[name] for name in names], dtype=np.float64)
    return {
        "identity": validated["identity"],
        "active_atom_names": names,
        "active_global_atom_indices": validated["observed_global_atom_indices"],
        "atom_status_by_name": dict(
            zip(V26_SEQUENTIAL_ATOM_NAMES, validated["status_pattern"], strict=True)
        ),
        "candidate_atoms": np.clip(
            validated["candidate_atoms_raw"] / scales,
            0.0,
            V26_NORMALIZED_ATOM_CLIP,
        ),
        "expert_atoms": np.clip(
            validated["expert_atoms_raw"] / scales,
            0.0,
            V26_NORMALIZED_ATOM_CLIP,
        ),
    }


@dataclass(frozen=True)
class _SequentialHead:
    pattern_index: int
    status_pattern: tuple[str, ...]
    active_global_indices: tuple[int, ...]
    theta: np.ndarray


class FrozenSequentialSceneSelector:
    """Apply a trained continuity-aware checkpoint to one fixed candidate pool."""

    def __init__(self, checkpoint_path: str | Path, scale_path: str | Path) -> None:
        scale_document = json.loads(Path(scale_path).read_text(encoding="utf-8"))
        self._scales = scales_by_sequential_name(scale_document)
        heads: list[_SequentialHead] = []
        with np.load(Path(checkpoint_path), allow_pickle=False) as checkpoint:
            theta_keys = sorted(key for key in checkpoint.files if key.startswith("theta_"))
            for theta_key in theta_keys:
                suffix = theta_key.removeprefix("theta_")
                theta = np.asarray(checkpoint[theta_key], dtype=np.float64)
                active = tuple(
                    int(value) for value in checkpoint[f"active_global_indices_{suffix}"]
                )
                pattern = tuple(
                    str(value) for value in checkpoint[f"status_pattern_{suffix}"]
                )
                if len(pattern) != len(V26_SEQUENTIAL_ATOM_NAMES):
                    raise ValueError("sequential checkpoint pattern width differs from 21")
                if active != tuple(
                    index for index, status in enumerate(pattern) if status == "observed"
                ):
                    raise ValueError("sequential checkpoint active rows differ from pattern")
                if theta.shape != (
                    len(active),
                    256 + V26_SEQUENTIAL_CONTEXT_DIMENSION + 1,
                ) or not np.all(np.isfinite(theta)):
                    raise ValueError("sequential checkpoint Theta has the wrong shape")
                heads.append(_SequentialHead(int(suffix), pattern, active, theta.copy()))
        if not heads or len({head.status_pattern for head in heads}) != len(heads):
            raise ValueError("sequential checkpoint heads are empty or duplicated")
        self._heads = {head.status_pattern: head for head in heads}

    def select(
        self, artifact: Mapping[str, Any], phi: np.ndarray, context: np.ndarray
    ) -> dict[str, Any]:
        view = validate_sequential_sparse_pool_artifact(artifact)
        feature = np.asarray(phi, dtype=np.float64)
        context_value = np.asarray(context, dtype=np.float64)
        if feature.shape != (256,) or not np.all(np.isfinite(feature)):
            raise ValueError("sequential selector phi must be finite [256]")
        if context_value.shape != (V26_SEQUENTIAL_CONTEXT_DIMENSION,) or not np.all(
            np.isfinite(context_value)
        ):
            raise ValueError("sequential selector context has the wrong shape")
        head = self._heads.get(view["status_pattern"])
        if head is None or head.active_global_indices != view["observed_global_atom_indices"]:
            raise ValueError("sequential checkpoint has no matching endpoint pattern")
        names = view["observed_atom_names"]
        scales = np.asarray([self._scales[name] for name in names], dtype=np.float64)
        normalized = np.clip(
            view["candidate_atoms_raw"] / scales, 0.0, V26_NORMALIZED_ATOM_CLIP
        )
        z = np.concatenate((feature, context_value, np.ones(1, dtype=np.float64)))
        affine = head.theta @ z
        weights = project_rows_to_simplex(affine)
        scores = normalized @ weights
        return {
            "selected_row": int(np.argmin(scores)),
            "candidate_scores": scores.tolist(),
            "active_weights": weights.tolist(),
            "raw_affine_weights": affine.tolist(),
            "pattern_index": head.pattern_index,
            "status_pattern": list(head.status_pattern),
            "active_global_atom_indices": list(head.active_global_indices),
            "active_atom_names": list(names),
            "context_names": list(V26_SEQUENTIAL_CONTEXT_NAMES),
            "candidate_modified": False,
        }

    def select_online(
        self,
        base_artifact: Mapping[str, Any],
        phi: np.ndarray,
        context: np.ndarray,
        *,
        sequential_candidate_atoms: np.ndarray | None,
        sequential_status: str,
    ) -> dict[str, Any]:
        """Apply the 21-atom checkpoint to candidate-only online evidence."""

        if sequential_status not in V26_ATOM_STATUS_VOCABULARY:
            raise ValueError("online sequential status is invalid")
        base = validate_v26_sparse_pool_artifact(base_artifact)
        base_names = tuple(str(name) for name in base["observed_atom_names"])
        candidate = np.asarray(base["candidate_atoms_raw"], dtype=np.float64)
        statuses = tuple(str(row["status"]) for row in base_artifact["atom_states"]) + (
            sequential_status,
        ) * len(V26_SEQUENTIAL_NEW_ATOM_NAMES)
        names = base_names
        indices = tuple(int(value) for value in base["observed_global_atom_indices"])
        if sequential_status == "observed":
            extra = np.asarray(sequential_candidate_atoms, dtype=np.float64)
            if extra.shape != (candidate.shape[0], len(V26_SEQUENTIAL_NEW_ATOM_NAMES)):
                raise ValueError("online sequential candidate atoms have the wrong shape")
            if not np.all(np.isfinite(extra)) or np.any(extra < 0.0):
                raise ValueError("online sequential candidate atoms must be finite and nonnegative")
            candidate = np.column_stack((candidate, extra))
            names = base_names + V26_SEQUENTIAL_NEW_ATOM_NAMES
            indices = indices + tuple(
                V26_SEQUENTIAL_ATOM_INDEX[name]
                for name in V26_SEQUENTIAL_NEW_ATOM_NAMES
            )
        feature = np.asarray(phi, dtype=np.float64)
        context_value = np.asarray(context, dtype=np.float64)
        if feature.shape != (256,) or not np.all(np.isfinite(feature)):
            raise ValueError("sequential selector phi must be finite [256]")
        if context_value.shape != (V26_SEQUENTIAL_CONTEXT_DIMENSION,) or not np.all(
            np.isfinite(context_value)
        ):
            raise ValueError("sequential selector context has the wrong shape")
        head = self._heads.get(statuses)
        if head is None or head.active_global_indices != indices:
            raise ValueError("sequential checkpoint has no matching online endpoint pattern")
        scales = np.asarray([self._scales[name] for name in names], dtype=np.float64)
        normalized = np.clip(candidate / scales, 0.0, V26_NORMALIZED_ATOM_CLIP)
        z = np.concatenate((feature, context_value, np.ones(1, dtype=np.float64)))
        affine = head.theta @ z
        weights = project_rows_to_simplex(affine)
        scores = normalized @ weights
        return {
            "selected_row": int(np.argmin(scores)),
            "candidate_scores": scores.tolist(),
            "active_weights": weights.tolist(),
            "raw_affine_weights": affine.tolist(),
            "pattern_index": head.pattern_index,
            "status_pattern": list(statuses),
            "active_global_atom_indices": list(indices),
            "active_atom_names": list(names),
            "candidate_atoms_raw": candidate,
            "candidate_atoms_scaled": normalized,
            "context_names": list(V26_SEQUENTIAL_CONTEXT_NAMES),
            "candidate_modified": False,
        }


__all__ = [
    "FrozenSequentialSceneSelector",
    "V26_SEQUENTIAL_ATOM_NAMES",
    "V26_SEQUENTIAL_ATOM_INDEX",
    "V26_SEQUENTIAL_CONTEXT_DIMENSION",
    "V26_SEQUENTIAL_CONTEXT_NAMES",
    "V26_SEQUENTIAL_CONTEXT_ROWS",
    "V26_SEQUENTIAL_NEW_ATOM_NAMES",
    "ego_longitudinal_state",
    "interpolate_world_xyhvas",
    "normalize_sequential_sparse_pool",
    "online_sequential_candidate_atom_values",
    "quaternion_yaw",
    "scales_by_sequential_name",
    "sequential_atom_values",
    "sequential_context",
    "trajectory_world_xyhvas",
    "validate_sequential_sparse_pool_artifact",
]
