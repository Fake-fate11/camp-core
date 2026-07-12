from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from shapely.ops import unary_union

from camp_core.integrations.diffusion_planner import (
    _project_route_progress,
    _summarize_clearance_log,
    _summarize_realized_red_lights,
    _summarize_trajectory_log,
)
from camp_core.integrations.nuplan_causal_adapter import (
    NuPlanCausalSourceError,
    _connected_live_lane_path,
    _map_roadblock,
    _polyline,
    _state_time_us,
)


_SAFETY_FIELDS = (
    "obb_collision_rate",
    "near_miss_rate",
    "lane_violation_rate",
    "red_light_violation_rate",
    "planned_red_light_violation_rate",
    "mean_jerk_magnitude_mps3",
    "mean_lateral_acceleration_mps2",
    "route_completion_rate",
)


def materialize_closed_loop_evidence(
    history: Any,
    scenario: Any,
    tick_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    samples = list(history.data)
    if len(samples) < 4:
        raise ValueError("closed-loop history is too short")
    timestamps = np.asarray(
        [_state_time_us(sample.ego_state) for sample in samples], dtype=np.int64
    )
    deltas = np.diff(timestamps) / 1_000_000.0
    dt = float(np.median(deltas))
    if not np.isfinite(dt) or dt <= 0.0 or not np.allclose(
        deltas, dt, rtol=0.0, atol=1e-3
    ):
        raise ValueError("closed-loop timestamps must be uniformly sampled")

    first_pose = samples[0].ego_state.rear_axle
    route_centerline, route_corridor = _route_geometry(
        scenario, np.asarray([first_pose.x, first_pose.y], dtype=np.float64)
    )
    goal = scenario.get_mission_goal()
    if goal is None:
        raise ValueError("mission goal is missing")

    trajectory_records = []
    clearance_records = []
    lane_violations = 0
    for sample in samples:
        state = sample.ego_state
        pose = state.rear_axle
        ego_geometry = _geometry(state.car_footprint)
        objects = list(sample.observation.tracked_objects.tracked_objects)
        distances = [ego_geometry.distance(_geometry(item.box)) for item in objects]
        clearance_records.append(
            {
                "moving_dist": min(distances) if distances else None,
                "stopped_dist": None,
                "rb_dist": None,
            }
        )
        lane_violations += int(not route_corridor.covers(ego_geometry))
        trajectory_records.append(
            {
                "x": float(pose.x),
                "y": float(pose.y),
                "heading": float(pose.heading),
                "speed": float(state.dynamic_car_state.speed),
                "goal_d": float(math.hypot(pose.x - goal.x, pose.y - goal.y)),
                "red_route_points": _red_route_points(
                    scenario.map_api, sample.traffic_light_status
                ),
            }
        )

    planned_costs = _planned_red_costs(tick_receipts, len(samples) - 1)
    summary: dict[str, Any] = {}
    summary.update(_summarize_trajectory_log(trajectory_records, dt=dt))
    summary.update(_project_route_progress(trajectory_records, route_centerline))
    summary.update(_summarize_realized_red_lights(trajectory_records, dt=dt))
    summary.update(
        _summarize_clearance_log(
            {"records": clearance_records}, near_miss_threshold_m=2.0
        )
    )
    summary.update(
        {
            "lane_violation_steps": lane_violations,
            "lane_violation_rate": lane_violations / len(samples),
            "planned_red_light_violation_steps": sum(
                cost > 1e-12 for cost in planned_costs
            ),
            "planned_red_light_violation_rate": sum(
                cost > 1e-12 for cost in planned_costs
            )
            / len(planned_costs),
            "source_scope": "official_full_posterior_observation",
            "online_feasibility_scope": (
                "frozen_32_dynamic_plus_5_static_observable_only"
            ),
            "observed_dt_s": dt,
        }
    )
    missing = [name for name in _SAFETY_FIELDS if not np.isfinite(summary.get(name))]
    if missing:
        raise ValueError(f"closed-loop SafetyCost fields are missing: {missing}")
    return summary


def _route_geometry(scenario: Any, current_xy: np.ndarray):
    route_ids = [str(value) for value in scenario.get_route_roadblock_ids()]
    if not route_ids:
        raise ValueError("mission route is missing")
    roadblocks = [_map_roadblock(scenario.map_api, value) for value in route_ids]
    lanes = _connected_live_lane_path(roadblocks, current_xy)
    centerline = []
    polygons = []
    for lane in lanes:
        points = _polyline(lane.baseline_path.discrete_path)
        if centerline and np.allclose(centerline[-1], points[0]):
            points = points[1:]
        centerline.extend(points)
        polygons.append(_geometry(lane))
    route_centerline = np.asarray(centerline, dtype=np.float64)
    corridor = unary_union(polygons)
    if route_centerline.shape[0] < 2 or corridor.is_empty or not corridor.is_valid:
        raise ValueError("route geometry is invalid")
    return route_centerline, corridor


def _red_route_points(map_api: Any, traffic_light_status: Any) -> np.ndarray:
    rows = []
    for item in list(traffic_light_status or []):
        status = str(getattr(item.status, "name", item.status)).upper()
        if status != "RED":
            continue
        connector = _map_connector(map_api, str(item.lane_connector_id))
        points = _polyline(connector.baseline_path.discrete_path)
        directions = np.diff(points, axis=0)
        norms = np.linalg.norm(directions, axis=1)
        if np.any(norms <= 1e-6):
            raise ValueError("red lane connector direction is invalid")
        directions = directions / norms[:, None]
        directions = np.vstack([directions, directions[-1]])
        rows.extend(np.column_stack([points, directions]))
    return np.asarray(rows, dtype=np.float64).reshape(-1, 4)


def _map_connector(map_api: Any, connector_id: str) -> Any:
    try:
        from nuplan.common.maps.maps_datatypes import SemanticMapLayer

        layer = SemanticMapLayer.LANE_CONNECTOR
    except ImportError:
        layer = "LANE_CONNECTOR"
    value = map_api.get_map_object(connector_id, layer)
    if value is None:
        raise NuPlanCausalSourceError(
            f"red lane connector {connector_id} is missing"
        )
    return value


def _geometry(value: Any):
    geometry = getattr(value, "geometry", None)
    if geometry is None:
        geometry = getattr(value, "polygon", None)
    if geometry is None or geometry.is_empty or not geometry.is_valid:
        raise ValueError("closed-loop geometry is missing or invalid")
    return geometry


def _planned_red_costs(
    receipts: Sequence[Mapping[str, Any]], expected_count: int
) -> list[float]:
    if len(receipts) != expected_count:
        raise ValueError("planned-red receipt count does not match planner ticks")
    ordered = sorted(receipts, key=lambda item: int(item["iteration_index"]))
    if [int(item["iteration_index"]) for item in ordered] != list(
        range(expected_count)
    ):
        raise ValueError("planned-red receipt iterations are incomplete")
    costs = []
    for receipt in ordered:
        if receipt.get("planned_red_source") != "fixed_dp_red_cost_v18":
            raise ValueError("planned-red receipt source mismatch")
        cost = float(receipt["selected_planned_red_light_cost"])
        if not np.isfinite(cost) or cost < 0.0:
            raise ValueError("planned-red receipt cost must be finite and nonnegative")
        costs.append(cost)
    return costs
