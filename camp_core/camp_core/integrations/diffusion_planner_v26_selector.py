"""One-call CAMP candidate selector for a Diffusion Planner planning tick."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import time
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_v26_atom_sources import (
    build_observable_obbs,
)
from camp_core.integrations.diffusion_planner_v26_camp_reranker import (
    CAMPDPRerankingPipeline,
    CAMPRerankResult,
    V26_CAMP_ATOM_NAMES,
    V26_CAMP_CANDIDATE_COUNT,
    V26_DP_MASKED_TOKEN_TYPES,
    V26_TRANSITION_ATOM_NAME,
    build_camp_atom_artifact,
    masked_mean_scene_embedding,
)
from camp_core.integrations.diffusion_planner_v26_expert_atom_pair import (
    materialize_v26_same_tick_full_atom_bank_pair,
)


_HORIZON_STEPS = 80
_DT_SECONDS = 0.1
_DP_ACTOR_COUNT = 32
_TRANSITION_SCALE_NAMES = (
    "position_m",
    "yaw_rad",
    "longitudinal_velocity_mps",
)


def _as_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    return np.asarray(value)


def _load_transition_scales(path: str | Path) -> dict[str, float]:
    payload = json.loads(Path(path).resolve(strict=True).read_text(encoding="utf-8"))
    source = payload.get("transition_component_positive_q95", payload)
    scales = {name: float(source[name]) for name in _TRANSITION_SCALE_NAMES}
    values = np.asarray(tuple(scales.values()), dtype=np.float64)
    if not np.all(np.isfinite(values)) or np.any(values <= 0.0):
        raise ValueError("CAMP transition component scales must be finite and positive")
    return scales


def _wrapped_angle(value: np.ndarray) -> np.ndarray:
    return np.arctan2(np.sin(value), np.cos(value))


def _candidate_world_trajectories(
    candidates: np.ndarray,
    *,
    ego_x: float,
    ego_y: float,
    ego_yaw: float,
    current_speed_mps: float,
    wheel_base_m: float,
) -> np.ndarray:
    """Convert DP local ``x,y,cos,sin`` candidates to world ``xyhvas``."""

    values = np.asarray(candidates, dtype=np.float64)
    if values.shape != (V26_CAMP_CANDIDATE_COUNT, _HORIZON_STEPS, 4):
        raise ValueError("DP ego candidates must have shape [8,80,4]")
    if not np.all(np.isfinite(values)):
        raise ValueError("DP ego candidates must be finite")
    local_heading = np.unwrap(np.arctan2(values[:, :, 3], values[:, :, 2]), axis=1)
    local_xy = values[:, :, :2]
    previous_xy = np.concatenate(
        (np.zeros((values.shape[0], 1, 2)), local_xy[:, :-1]), axis=1
    )
    displacement = local_xy - previous_xy
    velocity = (
        displacement[:, :, 0] * np.cos(local_heading)
        + displacement[:, :, 1] * np.sin(local_heading)
    ) / _DT_SECONDS
    previous_velocity = np.concatenate(
        (
            np.full((values.shape[0], 1), float(current_speed_mps)),
            velocity[:, :-1],
        ),
        axis=1,
    )
    acceleration = (velocity - previous_velocity) / _DT_SECONDS
    previous_heading = np.concatenate(
        (np.zeros((values.shape[0], 1)), local_heading[:, :-1]), axis=1
    )
    yaw_rate = _wrapped_angle(local_heading - previous_heading) / _DT_SECONDS
    curvature = np.divide(
        yaw_rate,
        velocity,
        out=np.zeros_like(yaw_rate),
        where=np.abs(velocity) > 1e-6,
    )
    steering = np.arctan(float(wheel_base_m) * curvature)

    cosine = math.cos(float(ego_yaw))
    sine = math.sin(float(ego_yaw))
    world_x = float(ego_x) + cosine * local_xy[:, :, 0] - sine * local_xy[:, :, 1]
    world_y = float(ego_y) + sine * local_xy[:, :, 0] + cosine * local_xy[:, :, 1]
    world_heading = np.unwrap(local_heading + float(ego_yaw), axis=1)
    return np.stack(
        (world_x, world_y, world_heading, velocity, acceleration, steering), axis=2
    )


def _interpolate_world_plan(
    values: np.ndarray, source_times: np.ndarray, target_times: np.ndarray
) -> np.ndarray:
    result = np.empty((target_times.size, 6), dtype=np.float64)
    for column in (0, 1, 3, 4, 5):
        result[:, column] = np.interp(target_times, source_times, values[:, column])
    result[:, 2] = np.interp(target_times, source_times, np.unwrap(values[:, 2]))
    return result


def _transition_values(
    candidates_world: np.ndarray,
    *,
    current_origin_seconds: float,
    previous_plan_world: np.ndarray | None,
    previous_origin_seconds: float | None,
    scales: Mapping[str, float],
) -> tuple[np.ndarray | None, int]:
    if previous_plan_world is None or previous_origin_seconds is None:
        return None, 0
    current_times = float(current_origin_seconds) + _DT_SECONDS * np.arange(1, 81)
    previous_times = float(previous_origin_seconds) + _DT_SECONDS * np.arange(1, 81)
    common = current_times[
        (current_times >= previous_times[0] - 1e-9)
        & (current_times <= previous_times[-1] + 1e-9)
    ]
    if common.size == 0:
        return None, 0
    candidate_common = np.stack(
        [
            _interpolate_world_plan(row, current_times, common)
            for row in candidates_world
        ]
    )
    previous_common = _interpolate_world_plan(
        np.asarray(previous_plan_world, dtype=np.float64), previous_times, common
    )
    delta = candidate_common[:, :, :4] - previous_common[None, :, :4]
    delta[:, :, 2] = _wrapped_angle(delta[:, :, 2])
    position = np.sqrt(np.mean(np.sum(delta[:, :, :2] ** 2, axis=2), axis=1))
    yaw = np.sqrt(np.mean(delta[:, :, 2] ** 2, axis=1))
    velocity = np.sqrt(np.mean(delta[:, :, 3] ** 2, axis=1))
    component_scales = np.asarray(
        [scales[name] for name in _TRANSITION_SCALE_NAMES], dtype=np.float64
    )
    coefficient = np.sqrt(
        np.mean(
            (np.column_stack((position, yaw, velocity)) / component_scales) ** 2,
            axis=1,
        )
    )
    return coefficient, int(common.size)


@dataclass(frozen=True)
class DiffusionPlannerCAMPTick:
    """Decision-time DP tensors and map state consumed by CAMP."""

    identity: Mapping[str, str | int | float | bool]
    prediction: Any
    neighbor_history: Any
    static_objects: Any
    ego_shape: Any
    route_lanes: Any
    route_speed_limits: Any
    route_has_speed_limits: Any
    route_atom_context: Mapping[str, Any]
    signal_authority: Mapping[str, Any]
    origin_seconds: float
    ego_x: float
    ego_y: float
    ego_yaw: float
    current_speed_mps: float
    encoder_tokens: Any | None = None
    token_masks: Mapping[str, Any] | Sequence[Any] | None = None
    neighbor_valid_mask: Any | None = None
    drivable_area_geometry: Any | None = None
    drivable_area_source_authority: str | None = None
    wheel_base_m: float = 2.79


@dataclass(frozen=True)
class DiffusionPlannerCAMPDecision:
    selected_trajectory: np.ndarray
    selected_row: int
    rerank: CAMPRerankResult
    atom_artifact: Mapping[str, Any]
    selector_elapsed_ms: float

    def as_dict(self) -> dict[str, Any]:
        result = self.rerank.as_dict()
        result.update(
            selected_trajectory=self.selected_trajectory.copy(),
            selector_elapsed_ms=self.selector_elapsed_ms,
        )
        return result


class DiffusionPlannerCAMPSelector:
    """Materialize CAMP inputs and select one unchanged DP candidate per tick."""

    def __init__(
        self,
        *,
        deployment_bundle: str | Path,
    ) -> None:
        root = Path(deployment_bundle).resolve(strict=True)
        self.pipeline = CAMPDPRerankingPipeline.from_directory(root)
        self.transition_scales = _load_transition_scales(
            root / "transition_scales.json"
        )
        self._previous_plan_world: np.ndarray | None = None
        self._previous_origin_seconds: float | None = None

    @classmethod
    def from_directory(
        cls, directory: str | Path
    ) -> "DiffusionPlannerCAMPSelector":
        return cls(deployment_bundle=directory)

    def reset(self) -> None:
        """Clear receding-horizon continuity state, for example on a new route."""

        self._previous_plan_world = None
        self._previous_origin_seconds = None

    def select(
        self,
        tick: DiffusionPlannerCAMPTick,
        *,
        mode: str = "fixed",
    ) -> DiffusionPlannerCAMPDecision:
        started = time.perf_counter()
        prediction = np.asarray(_as_numpy(tick.prediction), dtype=np.float64)
        if (
            prediction.ndim != 4
            or prediction.shape[0] != V26_CAMP_CANDIDATE_COUNT
            or prediction.shape[1] < _DP_ACTOR_COUNT + 1
            or prediction.shape[2:] != (_HORIZON_STEPS, 4)
        ):
            raise ValueError("DP prediction must have shape [8,1+N,80,4], N>=32")
        candidates = prediction[:, 0]

        history = np.asarray(_as_numpy(tick.neighbor_history), dtype=np.float64)
        if history.ndim != 3 or history.shape[0] < _DP_ACTOR_COUNT or history.shape[1:] != (31, 11):
            raise ValueError("DP neighbor history must have shape [N,31,11], N>=32")
        history = history[:_DP_ACTOR_COUNT]
        if tick.neighbor_valid_mask is None:
            valid = np.any(np.abs(history) > 1e-8, axis=(1, 2))
        else:
            valid = np.asarray(_as_numpy(tick.neighbor_valid_mask), dtype=bool).reshape(-1)
            if valid.size < _DP_ACTOR_COUNT:
                raise ValueError("DP neighbor validity must contain at least 32 rows")
            valid = valid[:_DP_ACTOR_COUNT]

        static_objects = np.asarray(_as_numpy(tick.static_objects), dtype=np.float64)
        obstacle_obbs = build_observable_obbs(
            prediction[:, 1 : _DP_ACTOR_COUNT + 1],
            valid,
            history,
            static_objects,
        )
        dynamic_obbs = build_observable_obbs(
            prediction[:, 1 : _DP_ACTOR_COUNT + 1],
            valid,
            history,
            static_objects,
            include_static_objects=False,
        )
        base_artifact = materialize_v26_same_tick_full_atom_bank_pair(
            identity=tick.identity,
            candidates=candidates,
            expert_future_xyh=None,
            obstacle_obbs=obstacle_obbs,
            dynamic_obbs=dynamic_obbs,
            ego_shape=np.asarray(_as_numpy(tick.ego_shape), dtype=np.float64),
            route_lanes=np.asarray(_as_numpy(tick.route_lanes), dtype=np.float64),
            route_speed_limits=np.asarray(
                _as_numpy(tick.route_speed_limits), dtype=np.float64
            ),
            route_has_speed_limits=np.asarray(
                _as_numpy(tick.route_has_speed_limits), dtype=bool
            ),
            signal_authority=tick.signal_authority,
            actor_source_complete=True,
            route_atom_context=tick.route_atom_context,
            drivable_area_geometry=tick.drivable_area_geometry,
            drivable_area_source_authority=tick.drivable_area_source_authority,
            scenario_reference={
                "runtime": "diffusion_planner_online",
                "actor_source": "fixed_dp_candidate_aligned_prediction",
                "actual_future_read": False,
            },
        )

        candidates_world = _candidate_world_trajectories(
            candidates,
            ego_x=tick.ego_x,
            ego_y=tick.ego_y,
            ego_yaw=tick.ego_yaw,
            current_speed_mps=tick.current_speed_mps,
            wheel_base_m=tick.wheel_base_m,
        )
        transition, overlap = _transition_values(
            candidates_world,
            current_origin_seconds=tick.origin_seconds,
            previous_plan_world=self._previous_plan_world,
            previous_origin_seconds=self._previous_origin_seconds,
            scales=self.transition_scales,
        )

        observed_names = tuple(str(name) for name in base_artifact["observed_atom_names"])
        raw = np.asarray(base_artifact["candidate_atoms_raw"], dtype=np.float64)
        values = {name: raw[:, index] for index, name in enumerate(observed_names)}
        statuses = {
            str(row["name"]): str(row["status"])
            for row in base_artifact["atom_states"]
        }
        if transition is None:
            statuses[V26_TRANSITION_ATOM_NAME] = "not_applicable"
        else:
            statuses[V26_TRANSITION_ATOM_NAME] = "observed"
            values[V26_TRANSITION_ATOM_NAME] = transition
        artifact = build_camp_atom_artifact(values, statuses)
        artifact["transition_overlap_sample_count"] = overlap

        scene_embedding = None
        if mode == "scene":
            if tick.encoder_tokens is None or tick.token_masks is None:
                raise ValueError(
                    "scene-conditioned CAMP requires DP encoder tokens and masks"
                )
            if isinstance(tick.token_masks, Mapping):
                missing = set(V26_DP_MASKED_TOKEN_TYPES).difference(tick.token_masks)
                if missing:
                    raise ValueError("DP token masks omit frozen encoder token types")
            scene_embedding = masked_mean_scene_embedding(
                tick.encoder_tokens, tick.token_masks
            )
        elif mode != "fixed":
            raise ValueError("CAMP mode must be 'fixed' or 'scene'")

        selected, rerank = self.pipeline.select(
            mode=mode,
            candidates=candidates,
            artifact=artifact,
            scene_embedding=scene_embedding,
        )
        self._previous_plan_world = candidates_world[rerank.selected_row].copy()
        self._previous_origin_seconds = float(tick.origin_seconds)
        return DiffusionPlannerCAMPDecision(
            selected_trajectory=selected,
            selected_row=rerank.selected_row,
            rerank=rerank,
            atom_artifact=artifact,
            selector_elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )


__all__ = [
    "DiffusionPlannerCAMPDecision",
    "DiffusionPlannerCAMPSelector",
    "DiffusionPlannerCAMPTick",
]
