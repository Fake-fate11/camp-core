"""Native TIER IV NPZ observations for the existing frozen CAMP selector.

Read the original observation arrays directly: the scenario editor's loader
may correct a stationary actor's past heading using its future trajectory.
Neither that correction nor GT-derived route/goal assignment belongs online.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np

from camp_core.integrations.diffusion_planner_v21_native import (
    candidate_latents,
    candidate_seed,
)
from camp_core.integrations.diffusion_planner_v26_selector import DiffusionPlannerCAMPTick


OBSERVATION_KEYS = (
    "ego_agent_past", "ego_current_state", "neighbor_agents_past",
    "static_objects", "lanes", "lanes_speed_limit", "lanes_has_speed_limit",
    "route_lanes", "route_lanes_speed_limit", "route_lanes_has_speed_limit",
    "polygons", "line_strings", "goal_pose", "turn_indicators", "ego_shape",
)


def load_native_observation(path: str | Path) -> dict[str, np.ndarray]:
    """Return only decision-time fields; absent inputs are not synthesized."""
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key].copy() for key in OBSERVATION_KEYS}


def native_model_inputs(observation, config, *, device, route_identity, tick_index=0, root_seed=3407, noise_scale=1.0, candidate_count=8):
    """Use DP's existing normalization and ordered latent sampler.

    Appended empty actor slots are native model padding, not atom zero filling.
    Original actor order and all original observations remain unchanged.
    """
    import torch

    if config.time_len != 31 or config.future_len != 80 or config.predicted_neighbor_num != 320:
        raise ValueError("This CAMP bundle requires the frozen 31/80/320 DP configuration")
    arrays = dict(observation)
    history = arrays["neighbor_agents_past"]
    if history.ndim != 3 or history.shape[1:] != (31, 11) or not 32 <= len(history) <= 320:
        raise ValueError("Native neighbor rows must be [N,31,11], 32 <= N <= 320")
    arrays["neighbor_agents_past"] = np.pad(history, ((0, 320-len(history)), (0, 0), (0, 0)))
    inputs = {key: torch.as_tensor(value, device=device).unsqueeze(0) for key, value in arrays.items()}
    for key in ("ego_agent_past", "goal_pose"):
        if inputs[key].shape[-1] == 3:
            # Exact train_epoch.heading_to_cos_sin operation, without importing
            # training augmentation (which is unnecessary at inference time).
            value = inputs[key]
            inputs[key] = torch.cat((value[..., :2], torch.cos(value[..., 2:3]),
                                     torch.sin(value[..., 2:3])), dim=-1)
    normalized = config.observation_normalizer(inputs)
    if not isinstance(candidate_count, int) or candidate_count < 1:
        raise ValueError("candidate_count must be a positive integer")
    expanded = {key: value.expand(candidate_count, *value.shape[1:]).contiguous() for key, value in normalized.items()}
    seed = candidate_seed(root_seed, route_identity, tick_index)
    expanded["sampled_trajectories"] = torch.as_tensor(
        candidate_latents(seed, noise_scale=noise_scale, candidate_count=candidate_count), device=device)
    expanded["delay"] = torch.zeros(candidate_count, dtype=torch.float32, device=device)
    return expanded


def native_camp_tick(
    observation: Mapping[str, np.ndarray], prediction: Any, *, identity,
    encoder_tokens=None, token_masks=None, map_context: Mapping[str, Any] | None = None,
    origin_seconds=0.0, ego_x=0.0, ego_y=0.0, ego_yaw=0.0,
) -> DiffusionPlannerCAMPTick:
    """Bind native arrays without pretending cropped vectors are a full road map.

    Official lane rows retain individual lanelet boundaries; polygons carry
    the intersection_area one-hot. These support the geometric TTC relevance
    test without nuPlan IDs. They do not supply authoritative future signals
    or a source-complete drivable-area map. A host may pass map_context here.
    For unrelated NPZ frames reset the selector; cross-frame continuity requires
    logged decision-time world pose/time, not a transform derived from GT future.
    """
    context = dict(map_context or {})
    missing_signal = {
        "source_state": "typed_missing",
        "reason": "native_npz_has_no_authoritative_8s_signal_phase_sequence",
    }
    route = context.get("route_atom_context")
    if route is None:
        route = {
            "route_objects": _native_route_objects(observation), "red_movements": (),
            "signal_source_state": "typed_missing",
            "signal_reason": missing_signal["reason"],
            "source_authority": "tier4_npz_lanelet_boundaries_and_intersection_area",
        }
    return DiffusionPlannerCAMPTick(
        identity=identity, prediction=prediction, encoder_tokens=encoder_tokens,
        token_masks=token_masks, neighbor_history=observation["neighbor_agents_past"],
        static_objects=observation["static_objects"], ego_shape=observation["ego_shape"],
        route_lanes=observation["route_lanes"],
        route_speed_limits=observation["route_lanes_speed_limit"],
        route_has_speed_limits=observation["route_lanes_has_speed_limit"],
        route_atom_context=route, signal_authority=context.get("signal_authority", missing_signal),
        drivable_area_geometry=context.get("drivable_area_geometry"),
        drivable_area_source_authority=context.get("drivable_area_source_authority"),
        origin_seconds=origin_seconds, ego_x=ego_x, ego_y=ego_y, ego_yaw=ego_yaw,
        current_speed_mps=float(observation["ego_current_state"][4]),
        wheel_base_m=float(observation["ego_shape"][0]),
    )


def _native_route_objects(observation: Mapping[str, np.ndarray]) -> tuple[dict, ...]:
    """Restore official exporter geometry, retaining its per-lanelet grouping.

    lanelet_converter interpolates each original lanelet's three polylines to
    20 points, then stores boundary-minus-center offsets (it does not split
    one lanelet into several rows). Intersection channel 2 is the one-hot
    for intersection_area, not a nuPlan connector ID/type. No buffers/unions.
    """
    from shapely.geometry import Polygon

    lanes = np.asarray(observation['route_lanes'], dtype=np.float64)
    intersections = np.asarray(observation['polygons'], dtype=np.float64)
    if lanes.ndim != 3 or lanes.shape[1:] != (20, 33):
        raise ValueError('Native route lanes must have shape [N,20,33]')
    if intersections.ndim != 3 or intersections.shape[1:] != (40, 3):
        raise ValueError('Native intersection polygons must have shape [N,40,3]')
    objects = []
    for slot, lane in enumerate(lanes):
        if not np.any(lane[:, :8]):  # Whole unused native slot; keep every point of real lanelets.
            continue
        left = lane[:, :2] + lane[:, 4:6]
        right = lane[:, :2] + lane[:, 6:8]
        geometry = Polygon(np.concatenate((left, right[::-1])))
        if not np.isfinite(np.concatenate((left, right))).all() or not geometry.is_valid or geometry.area <= 0:
            raise ValueError(f'Native route lanelet slot {slot} has invalid boundary geometry')
        objects.append({'kind': 'lane', 'slot': slot, 'geometry': geometry})
    for slot, row in enumerate(intersections):
        if not np.any(row):
            continue
        if not np.all(np.isin(row[:, 2], (0., 1.))):
            raise ValueError('Native intersection_area channel must be the official one-hot')
        ring = row[row[:, 2] == 1., :2]
        if len(ring) < 3 or not np.isfinite(ring).all():
            raise ValueError(f'Native intersection slot {slot} lacks a finite polygon ring')
        geometry = Polygon(ring)
        if not geometry.is_valid or geometry.area <= 0:
            raise ValueError(f'Native intersection slot {slot} has invalid geometry')
        objects.append({'kind': 'intersection_area', 'slot': slot, 'geometry': geometry})
    return tuple(objects)
