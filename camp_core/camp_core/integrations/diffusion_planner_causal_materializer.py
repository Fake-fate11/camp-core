from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np


MATERIALIZER_SCHEMA_VERSION = "dp_camp_v17_causal_materializer_v1"
TARGET_DT_S = 0.1
HISTORY_STEPS = 31
CANDIDATE_HORIZON_STEPS = 80

CAUSAL_DP_INPUT_SCHEMA = {
    "ego_agent_past": ((31, 3), "float32"),
    "ego_current_state": ((10,), "float32"),
    "ego_shape": ((3,), "float32"),
    "goal_pose": ((3,), "float32"),
    "lanes": ((140, 20, 33), "float32"),
    "lanes_has_speed_limit": ((140, 1), "bool"),
    "lanes_speed_limit": ((140, 1), "float32"),
    "line_strings": ((60, 20, 4), "float32"),
    "neighbor_agents_past": ((32, 31, 11), "float32"),
    "polygons": ((10, 40, 3), "float32"),
    "route_lanes": ((25, 20, 33), "float32"),
    "route_lanes_has_speed_limit": ((25, 1), "bool"),
    "route_lanes_speed_limit": ((25, 1), "float32"),
    "static_objects": ((5, 10), "float32"),
    "turn_indicators": ((31,), "int32"),
    "version": ((), "int64"),
}

_CONTEXT_FIELDS = frozenset(
    {
        "map_frame",
        "decision_id",
        "route_source",
        "lanes",
        "lanes_has_speed_limit",
        "lanes_speed_limit",
        "route_lanes",
        "route_lanes_has_speed_limit",
        "route_lanes_speed_limit",
        "line_strings",
        "polygons",
        "static_objects",
        "turn_indicators",
        "turn_indicators_available",
        "traffic_light_state_available",
        "ego_wheelbase_m",
    }
)
_OPTIONAL_CONTEXT_FIELDS = frozenset({"mission_goal_pose"})
_ROUTE_SOURCES = frozenset(
    {
        "current_map_topology_successors",
        "nuplan_mission_route_current_roadblock_successors",
    }
)


@dataclass(frozen=True)
class CausalDPMaterialization:
    dp_input: dict[str, np.ndarray]
    metadata: dict[str, object]


def materialize_causal_dp_input(
    batch: Any,
    decision_context: Mapping[str, Any],
    *,
    index: int = 0,
) -> CausalDPMaterialization:
    """Build the fixed-DP inference input from current-tick information only.

    ``decision_context`` contains world-frame map tensors and explicit
    availability flags. GT futures and evaluation labels are deliberately not
    accepted by this boundary.
    """
    _validate_context_keys(decision_context)
    if decision_context["map_frame"] != "world":
        raise ValueError("decision_context.map_frame must be 'world'")
    decision_id = decision_context["decision_id"]
    if not isinstance(decision_id, str) or not decision_id.strip():
        raise ValueError("decision_context.decision_id must be a nonempty string")
    route_source = decision_context["route_source"]
    if route_source not in _ROUTE_SOURCES:
        raise ValueError(
            f"decision_context.route_source must be one of {sorted(_ROUTE_SOURCES)}"
        )
    if (
        route_source == "nuplan_mission_route_current_roadblock_successors"
        and "mission_goal_pose" not in decision_context
    ):
        raise ValueError(
            "nuPlan mission route requires decision_context.mission_goal_pose"
        )

    source_dt = _positive_scalar(_batch_item(batch, "dt", index), "batch.dt")
    history_pad_dir = _integer_scalar(
        _batch_item(batch, "history_pad_dir", index), "batch.history_pad_dir"
    )
    if history_pad_dir != 1:
        raise ValueError("batch.history_pad_dir must be right padding (1)")
    transform = _world_to_ego_transform(batch, index)
    traffic_available = _required_bool(
        decision_context, "traffic_light_state_available"
    )
    turn_available = _required_bool(decision_context, "turn_indicators_available")

    ego_history_raw = _batch_item(batch, "agent_hist", index)
    ego_history_len = _required_length(batch, "agent_hist_len", index)
    ego_states = _valid_history(ego_history_raw, ego_history_len, "agent_hist")
    ego_xyh = _ego_local_xyh(_states_to_xyh(ego_states, "agent_hist"))
    ego_history, _ = _resample_xyh(
        ego_xyh,
        source_dt,
        require_full_history=True,
        name="ego history",
    )

    current_state = np.asarray(
        _batch_item(batch, "curr_agent_state", index), dtype=np.float64
    ).reshape(-1)
    if current_state.size < 7 or not np.isfinite(current_state[:7]).all():
        raise ValueError("curr_agent_state must contain finite x,y,vx,vy,ax,ay,heading")
    current_ego_xy = _transform_positions(current_state[None, :2], transform)[0]
    if float(np.linalg.norm(current_ego_xy)) > 1e-3:
        raise ValueError("agents_from_world_tf does not place the current ego at the origin")
    heading_vector = np.array(
        [[math.cos(float(current_state[6])), math.sin(float(current_state[6]))]]
    )
    ego_heading_vector = _transform_directions(heading_vector, transform)[0]
    if not np.allclose(ego_heading_vector, [1.0, 0.0], atol=1e-3):
        raise ValueError("agents_from_world_tf rotation does not match current heading")

    wheelbase = _positive_scalar(
        decision_context["ego_wheelbase_m"], "ego_wheelbase_m"
    )
    ego_shape = _ego_shape(batch, index, ego_history_len, wheelbase)
    ego_current_state = _ego_current_state(current_state, ego_xyh, source_dt, wheelbase)
    neighbors = _neighbor_history(batch, index, source_dt)

    lanes = _context_array(decision_context, "lanes", (140, 20, 33), np.float64)
    route = _context_array(
        decision_context, "route_lanes", (25, 20, 33), np.float64
    )
    lanes = _transform_lanes(lanes, transform)
    route = _transform_lanes(route, transform)
    _validate_lane_geometry(lanes, traffic_available, "lanes")
    _validate_lane_geometry(route, traffic_available, "route_lanes")
    _validate_connected_route(route)

    lane_limits, lane_has_limits = _speed_limit_fields(
        decision_context, "lanes", (140, 1)
    )
    route_limits, route_has_limits = _speed_limit_fields(
        decision_context, "route_lanes", (25, 1)
    )
    _validate_route_speed_alignment(route, route_has_limits)

    turn_indicators = _context_array(
        decision_context, "turn_indicators", (31,), np.int32
    )
    if np.any((turn_indicators < 0) | (turn_indicators > 4)):
        raise ValueError("turn_indicators must use fixed-DP classes 0 through 4")
    if not turn_available and np.any(turn_indicators != 0):
        raise ValueError("unavailable turn indicators must not contain asserted states")

    dp_input = {
        "ego_agent_past": ego_history,
        "ego_current_state": ego_current_state,
        "ego_shape": ego_shape,
        "goal_pose": _goal_pose(decision_context, route, transform),
        "lanes": lanes,
        "lanes_has_speed_limit": lane_has_limits,
        "lanes_speed_limit": lane_limits,
        "line_strings": _transform_points_tensor(
            _context_array(
                decision_context, "line_strings", (60, 20, 4), np.float64
            ),
            transform,
        ),
        "neighbor_agents_past": neighbors,
        "polygons": _transform_points_tensor(
            _context_array(decision_context, "polygons", (10, 40, 3), np.float64),
            transform,
        ),
        "route_lanes": route,
        "route_lanes_has_speed_limit": route_has_limits,
        "route_lanes_speed_limit": route_limits,
        "static_objects": _transform_static_objects(
            _context_array(
                decision_context, "static_objects", (5, 10), np.float64
            ),
            transform,
        ),
        "turn_indicators": turn_indicators,
        "version": np.array(1, dtype=np.int64),
    }
    errors = validate_causal_dp_input(dp_input)
    if errors:
        raise ValueError("; ".join(errors))

    metadata: dict[str, object] = {
        "schema_version": MATERIALIZER_SCHEMA_VERSION,
        "source_dt_s": float(source_dt),
        "target_dt_s": TARGET_DT_S,
        "history_steps": HISTORY_STEPS,
        "candidate_horizon_steps": CANDIDATE_HORIZON_STEPS,
        "candidate_horizon_s": CANDIDATE_HORIZON_STEPS * TARGET_DT_S,
        "coordinate_frame": "ego_base_link",
        "heading_unit": "radian",
        "distance_unit": "meter",
        "speed_unit": "meter_per_second",
        "traffic_light_state_available": traffic_available,
        "turn_indicators_available": turn_available,
        "decision_id": decision_id,
        "route_source": route_source,
    }
    return CausalDPMaterialization(dp_input=dp_input, metadata=metadata)


def validate_causal_dp_input(data: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = set(CAUSAL_DP_INPUT_SCHEMA) - set(data)
    extra = set(data) - set(CAUSAL_DP_INPUT_SCHEMA)
    if missing:
        errors.append(f"missing:{','.join(sorted(missing))}")
    if extra:
        errors.append(f"extra:{','.join(sorted(extra))}")
    for key, (shape, dtype) in CAUSAL_DP_INPUT_SCHEMA.items():
        if key not in data:
            continue
        array = np.asarray(data[key])
        if array.shape != shape:
            errors.append(f"shape:{key}:{array.shape}!={shape}")
        if array.dtype != np.dtype(dtype):
            errors.append(f"dtype:{key}:{array.dtype}!={dtype}")
        if array.dtype.kind in "fc" and not np.isfinite(array).all():
            errors.append(f"finite:{key}")
    return errors


def _validate_context_keys(context: Mapping[str, Any]) -> None:
    missing = _CONTEXT_FIELDS - set(context)
    extra = set(context) - _CONTEXT_FIELDS - _OPTIONAL_CONTEXT_FIELDS
    if missing:
        raise ValueError(f"missing decision_context fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"unexpected decision_context fields: {sorted(extra)}")


def _required_bool(context: Mapping[str, Any], key: str) -> bool:
    value = context[key]
    if not isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{key} must be bool")
    return bool(value)


def _as_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    return np.asarray(value)


def _batch_item(batch: Any, name: str, index: int) -> np.ndarray:
    try:
        array = _as_numpy(getattr(batch, name))
    except AttributeError as exc:
        raise ValueError(f"batch is missing required current-tick field {name}") from exc
    if array.ndim == 0:
        return array
    if index < 0 or index >= array.shape[0]:
        raise IndexError(f"batch index {index} is outside {name} shape {array.shape}")
    return np.asarray(array[index])


def _required_length(batch: Any, name: str, index: int) -> int:
    length = _integer_scalar(_batch_item(batch, name, index), name)
    if length < 1:
        raise ValueError(f"{name} must be positive")
    return length


def _integer_scalar(value: Any, name: str) -> int:
    array = np.asarray(value).reshape(-1)
    if array.size != 1 or array.dtype.kind not in "iu":
        raise ValueError(f"{name} must be one integer scalar")
    return int(array[0])


def _positive_scalar(value: Any, name: str) -> float:
    array = np.asarray(value, dtype=np.float64).reshape(-1)
    if array.size != 1 or not np.isfinite(array[0]) or array[0] <= 0.0:
        raise ValueError(f"{name} must be one finite positive scalar")
    return float(array[0])


def _valid_history(history: Any, length: int, name: str) -> np.ndarray:
    array = np.asarray(history, dtype=np.float64)
    if array.ndim != 2 or length > array.shape[0]:
        raise ValueError(f"{name} length {length} is incompatible with shape {array.shape}")
    valid = array[:length]
    if valid.shape[1] < 8 or not np.isfinite(valid[:, :8]).all():
        raise ValueError(f"{name} valid rows must contain finite x,y,v,a,sin,cos")
    return valid


def _states_to_xyh(states: np.ndarray, name: str) -> np.ndarray:
    heading_norm = np.linalg.norm(states[:, 6:8], axis=1)
    if np.any(heading_norm < 0.5):
        raise ValueError(f"{name} has invalid sin/cos heading")
    heading = np.arctan2(states[:, 6], states[:, 7])
    return np.column_stack([states[:, :2], heading])


def _ego_local_xyh(xyh: np.ndarray) -> np.ndarray:
    current_xy = xyh[-1, :2]
    current_heading = float(xyh[-1, 2])
    c = math.cos(current_heading)
    s = math.sin(current_heading)
    rotation = np.array([[c, s], [-s, c]], dtype=np.float64)
    local_xy = (xyh[:, :2] - current_xy) @ rotation.T
    local_heading = _wrap_to_pi(xyh[:, 2] - current_heading)
    return np.column_stack([local_xy, local_heading])


def _resample_xyh(
    xyh: np.ndarray,
    source_dt: float,
    *,
    require_full_history: bool,
    name: str,
) -> tuple[np.ndarray, np.ndarray]:
    count = xyh.shape[0]
    source_times = (np.arange(count, dtype=np.float64) - (count - 1)) * source_dt
    target_times = (
        np.arange(HISTORY_STEPS, dtype=np.float64) - (HISTORY_STEPS - 1)
    ) * TARGET_DT_S
    coverage = float(-source_times[0])
    required = float(-target_times[0])
    if require_full_history and coverage + 1e-6 < required:
        raise ValueError(
            f"{name} covers {coverage:.6g}s but fixed DP requires {required:.6g}s"
        )
    mask = target_times >= source_times[0] - 1e-9
    if require_full_history:
        mask[:] = True
    output = np.zeros((HISTORY_STEPS, 3), dtype=np.float64)
    output[mask, 0] = np.interp(target_times[mask], source_times, xyh[:, 0])
    output[mask, 1] = np.interp(target_times[mask], source_times, xyh[:, 1])
    unwrapped = np.unwrap(xyh[:, 2])
    output[mask, 2] = _wrap_to_pi(
        np.interp(target_times[mask], source_times, unwrapped)
    )
    return output.astype(np.float32), mask


def _wrap_to_pi(angle: Any) -> np.ndarray:
    values = np.asarray(angle, dtype=np.float64)
    return np.arctan2(np.sin(values), np.cos(values))


def _ego_shape(batch: Any, index: int, history_len: int, wheelbase: float) -> np.ndarray:
    extents = np.asarray(
        _batch_item(batch, "agent_hist_extent", index), dtype=np.float64
    )
    if extents.ndim != 2 or extents.shape[0] < history_len or extents.shape[1] < 2:
        raise ValueError("agent_hist_extent must align with agent_hist")
    length, width = extents[history_len - 1, :2]
    if not np.isfinite([length, width]).all() or min(length, width) <= 0.0:
        raise ValueError("ego length and width must be finite positive meters")
    return np.array([wheelbase, length, width], dtype=np.float32)


def _ego_current_state(
    current: np.ndarray,
    ego_xyh: np.ndarray,
    source_dt: float,
    wheelbase: float,
) -> np.ndarray:
    velocity = current[2:4]
    acceleration = current[4:6]
    speed = float(np.linalg.norm(velocity))
    if speed > 1e-6:
        longitudinal_acceleration = float(np.dot(velocity, acceleration) / speed)
    else:
        heading = float(current[6])
        longitudinal_acceleration = float(
            np.dot(acceleration, [math.cos(heading), math.sin(heading)])
        )
    yaw_rate = 0.0
    if ego_xyh.shape[0] >= 2:
        yaw_rate = float(
            _wrap_to_pi(ego_xyh[-1, 2] - ego_xyh[-2, 2]) / source_dt
        )
    steering = math.atan(wheelbase * yaw_rate / speed) if speed > 1e-3 else 0.0
    return np.array(
        [
            0.0,
            0.0,
            1.0,
            0.0,
            speed,
            0.0,
            longitudinal_acceleration,
            0.0,
            steering,
            yaw_rate,
        ],
        dtype=np.float32,
    )


def _neighbor_history(batch: Any, index: int, source_dt: float) -> np.ndarray:
    histories = np.asarray(_batch_item(batch, "neigh_hist", index), dtype=np.float64)
    lengths = np.asarray(_batch_item(batch, "neigh_hist_len", index))
    if lengths.dtype.kind not in "iu":
        raise ValueError("neigh_hist_len must have integer dtype")
    lengths = lengths.reshape(-1)
    extents = np.asarray(
        _batch_item(batch, "neigh_hist_extents", index), dtype=np.float64
    )
    types = np.asarray(_batch_item(batch, "neigh_types", index)).reshape(-1)
    if histories.ndim != 3 or histories.shape[2] < 8:
        raise ValueError("neigh_hist must have shape [N,T,>=8]")
    if lengths.size != histories.shape[0] or types.size != histories.shape[0]:
        raise ValueError("neighbor lengths/types must align with neigh_hist")
    if extents.ndim != 3 or extents.shape[:2] != histories.shape[:2]:
        raise ValueError("neigh_hist_extents must align with neigh_hist")

    order: list[tuple[float, int, int]] = []
    for neighbor_index, raw_length in enumerate(lengths):
        length = int(raw_length)
        if length < 1:
            continue
        if length > histories.shape[1]:
            raise ValueError("neigh_hist_len exceeds the padded history length")
        current_xy = histories[neighbor_index, length - 1, :2]
        if not np.isfinite(current_xy).all():
            raise ValueError("neighbor current position must be finite")
        order.append((float(np.linalg.norm(current_xy)), neighbor_index, length))
    order.sort(key=lambda item: (item[0], item[1]))

    output = np.zeros((32, HISTORY_STEPS, 11), dtype=np.float32)
    target_times = (
        np.arange(HISTORY_STEPS, dtype=np.float64) - (HISTORY_STEPS - 1)
    ) * TARGET_DT_S
    for slot, (_, neighbor_index, length) in enumerate(order[:32]):
        states = _valid_history(
            histories[neighbor_index], length, f"neigh_hist[{neighbor_index}]"
        )
        xyh = _states_to_xyh(states, f"neigh_hist[{neighbor_index}]")
        resampled, mask = _resample_xyh(
            xyh,
            source_dt,
            require_full_history=False,
            name=f"neighbor history {neighbor_index}",
        )
        source_times = (
            np.arange(length, dtype=np.float64) - (length - 1)
        ) * source_dt
        speed = np.linalg.norm(states[:, 2:4], axis=1)
        speed_profile = np.zeros(HISTORY_STEPS, dtype=np.float64)
        speed_profile[mask] = np.interp(target_times[mask], source_times, speed)
        current_extent = extents[neighbor_index, length - 1]
        if current_extent.size < 2 or not np.isfinite(current_extent[:2]).all():
            raise ValueError("neighbor extent must contain finite length and width")
        length_m, width_m = current_extent[:2]
        if min(length_m, width_m) <= 0.0:
            raise ValueError("neighbor length and width must be positive")
        type_vector = _neighbor_type(types[neighbor_index])

        output[slot, mask, :2] = resampled[mask, :2]
        output[slot, mask, 2] = np.cos(resampled[mask, 2])
        output[slot, mask, 3] = np.sin(resampled[mask, 2])
        output[slot, mask, 4] = speed_profile[mask] * output[slot, mask, 2]
        output[slot, mask, 5] = speed_profile[mask] * output[slot, mask, 3]
        output[slot, mask, 6] = float(width_m)
        output[slot, mask, 7] = float(length_m)
        output[slot, mask, 8:11] = type_vector
    return output


def _neighbor_type(value: Any) -> np.ndarray:
    name = getattr(value, "name", None)
    if name is not None:
        name = str(name).upper()
        mapping = {"VEHICLE": 0, "PEDESTRIAN": 1, "BICYCLE": 2, "MOTORCYCLE": 2}
        if name not in mapping:
            raise ValueError(f"unsupported neighbor type {name}")
        index = mapping[name]
    else:
        numeric = float(value)
        integer = int(round(numeric))
        if not np.isfinite(numeric) or abs(numeric - integer) > 1e-6:
            raise ValueError(f"invalid neighbor type {value}")
        mapping = {1: 0, 2: 1, 3: 2, 4: 2}
        if integer not in mapping:
            raise ValueError(f"unsupported neighbor type {integer}")
        index = mapping[integer]
    result = np.zeros(3, dtype=np.float32)
    result[index] = 1.0
    return result


def _world_to_ego_transform(batch: Any, index: int) -> np.ndarray:
    transform = np.asarray(
        _batch_item(batch, "agents_from_world_tf", index), dtype=np.float64
    )
    if transform.shape != (3, 3) or not np.isfinite(transform).all():
        raise ValueError("agents_from_world_tf must be one finite 3x3 transform")
    if not np.allclose(transform[2], [0.0, 0.0, 1.0], atol=1e-5):
        raise ValueError("agents_from_world_tf must be a planar homogeneous transform")
    rotation = transform[:2, :2]
    if not np.allclose(rotation @ rotation.T, np.eye(2), atol=1e-5):
        raise ValueError("agents_from_world_tf rotation must be orthonormal")
    if float(np.linalg.det(rotation)) < 0.999:
        raise ValueError("agents_from_world_tf must preserve orientation")
    return transform


def _context_array(
    context: Mapping[str, Any],
    key: str,
    shape: tuple[int, ...],
    dtype: Any,
) -> np.ndarray:
    array = np.asarray(context[key])
    if array.shape != shape:
        raise ValueError(f"{key} must have shape {shape}, got {array.shape}")
    target_dtype = np.dtype(dtype)
    if target_dtype.kind == "b" and array.dtype.kind != "b":
        raise ValueError(f"{key} must have bool dtype")
    if target_dtype.kind in "iu" and array.dtype.kind not in "iu":
        raise ValueError(f"{key} must have integer dtype")
    if array.dtype.kind in "fc" and not np.isfinite(array).all():
        raise ValueError(f"{key} must be finite")
    return np.asarray(array, dtype=target_dtype).copy()


def _transform_positions(points: np.ndarray, transform: np.ndarray) -> np.ndarray:
    homogeneous = np.concatenate(
        [np.asarray(points, dtype=np.float64), np.ones((len(points), 1))], axis=1
    )
    return (homogeneous @ transform.T)[:, :2]


def _transform_directions(vectors: np.ndarray, transform: np.ndarray) -> np.ndarray:
    return np.asarray(vectors, dtype=np.float64) @ transform[:2, :2].T


def _transform_lanes(lanes: np.ndarray, transform: np.ndarray) -> np.ndarray:
    result = lanes.copy()
    valid = np.sum(np.abs(result[..., :8]), axis=-1) > 1e-8
    result[..., :2][valid] = _transform_positions(result[..., :2][valid], transform)
    for start in (2, 4, 6):
        result[..., start : start + 2][valid] = _transform_directions(
            result[..., start : start + 2][valid], transform
        )
    result[~valid] = 0.0
    return result.astype(np.float32)


def _transform_points_tensor(array: np.ndarray, transform: np.ndarray) -> np.ndarray:
    result = array.copy()
    valid = np.sum(np.abs(result), axis=-1) > 1e-8
    result[..., :2][valid] = _transform_positions(result[..., :2][valid], transform)
    result[~valid] = 0.0
    return result.astype(np.float32)


def _transform_static_objects(array: np.ndarray, transform: np.ndarray) -> np.ndarray:
    result = array.copy()
    valid = np.sum(np.abs(result), axis=-1) > 1e-8
    result[:, :2][valid] = _transform_positions(result[:, :2][valid], transform)
    result[:, 2:4][valid] = _transform_directions(result[:, 2:4][valid], transform)
    result[~valid] = 0.0
    return result.astype(np.float32)


def _validate_lane_geometry(
    lanes: np.ndarray, traffic_available: bool, name: str
) -> None:
    valid = np.sum(np.abs(lanes[..., :8]), axis=-1) > 1e-8
    if not valid.any():
        raise ValueError(f"{name} contains no real lane geometry")
    direction_norm = np.linalg.norm(lanes[..., 2:4], axis=-1)
    left_norm = np.linalg.norm(lanes[..., 4:6], axis=-1)
    right_norm = np.linalg.norm(lanes[..., 6:8], axis=-1)
    if np.any(direction_norm[valid] < 1e-4):
        raise ValueError(f"{name} contains valid points without direction vectors")
    if np.any(left_norm[valid] < 0.2) or np.any(right_norm[valid] < 0.2):
        raise ValueError(f"{name} requires explicit left/right boundary offsets")
    direction = lanes[..., 2:4][valid]
    left = lanes[..., 4:6][valid]
    right = lanes[..., 6:8][valid]
    left_sine = (
        direction[:, 0] * left[:, 1] - direction[:, 1] * left[:, 0]
    ) / (direction_norm[valid] * left_norm[valid])
    right_sine = (
        direction[:, 0] * right[:, 1] - direction[:, 1] * right[:, 0]
    ) / (direction_norm[valid] * right_norm[valid])
    if np.any(left_sine <= 0.2) or np.any(right_sine >= -0.2):
        raise ValueError(f"{name} boundary offsets must be lateral on opposite sides")
    traffic = lanes[..., 8:13][valid]
    if np.any(~(np.isclose(traffic, 0.0) | np.isclose(traffic, 1.0))):
        raise ValueError(f"{name} traffic channels must be binary")
    if traffic_available:
        if not np.allclose(np.sum(traffic, axis=1), 1.0, atol=1e-5):
            raise ValueError(f"{name} traffic state must be one-hot when available")
    elif np.any(np.abs(traffic[:, :4]) > 1e-8):
        raise ValueError(f"{name} asserts traffic-light state while availability is false")


def _validate_connected_route(route: np.ndarray) -> None:
    point_valid = np.sum(np.abs(route[..., :8]), axis=-1) > 1e-8
    lane_indices = np.flatnonzero(point_valid.any(axis=1))
    if lane_indices.size == 0:
        raise ValueError("route_lanes contains no route")
    if not np.array_equal(lane_indices, np.arange(lane_indices.size)):
        raise ValueError("route lane slots must be contiguous and ordered from slot zero")
    previous_end = None
    previous_direction = None
    for lane_index in lane_indices:
        lane_mask = point_valid[lane_index]
        points = route[lane_index, lane_mask, :2]
        directions = route[lane_index, lane_mask, 2:4]
        if points.shape[0] < 2:
            raise ValueError("each route lane must contain at least two points")
        if previous_end is not None:
            gap = float(np.linalg.norm(points[0] - previous_end))
            if gap > 8.0:
                raise ValueError(f"route is disconnected at slot {lane_index}: gap={gap:.3f}m")
            cosine = float(
                np.dot(previous_direction, directions[0])
                / (np.linalg.norm(previous_direction) * np.linalg.norm(directions[0]))
            )
            if cosine < -0.5:
                raise ValueError(f"route heading discontinuity at slot {lane_index}")
        previous_end = points[-1]
        previous_direction = directions[-1]


def _speed_limit_fields(
    context: Mapping[str, Any], prefix: str, shape: tuple[int, int]
) -> tuple[np.ndarray, np.ndarray]:
    limits = _context_array(context, f"{prefix}_speed_limit", shape, np.float32)
    has_limits = _context_array(
        context, f"{prefix}_has_speed_limit", shape, np.bool_
    )
    if np.any(limits < 0.0):
        raise ValueError(f"{prefix}_speed_limit must be nonnegative")
    if np.any(has_limits & (limits <= 0.0)):
        raise ValueError(f"{prefix} available speed limits must be positive")
    if np.any((~has_limits) & (limits != 0.0)):
        raise ValueError(f"{prefix} unavailable speed-limit slots must be zero")
    return limits, has_limits


def _validate_route_speed_alignment(
    route: np.ndarray, has_limits: np.ndarray
) -> None:
    valid_lanes = (np.sum(np.abs(route[..., :8]), axis=-1) > 1e-8).any(axis=1)
    if np.any(has_limits[:, 0] & ~valid_lanes):
        raise ValueError("route speed limit is attached to an empty route slot")


def _goal_from_route(route: np.ndarray) -> np.ndarray:
    valid = np.sum(np.abs(route[..., :8]), axis=-1) > 1e-8
    lane_index = int(np.flatnonzero(valid.any(axis=1))[-1])
    point_index = int(np.flatnonzero(valid[lane_index])[-1])
    point = route[lane_index, point_index]
    heading = math.atan2(float(point[3]), float(point[2]))
    return np.array([point[0], point[1], heading], dtype=np.float32)


def _goal_pose(
    context: Mapping[str, Any], route: np.ndarray, transform: np.ndarray
) -> np.ndarray:
    if "mission_goal_pose" not in context:
        return _goal_from_route(route)
    pose = np.asarray(context["mission_goal_pose"], dtype=np.float64)
    if pose.shape != (3,) or not np.isfinite(pose).all():
        raise ValueError("mission_goal_pose must be finite with shape (3,)")
    position = _transform_positions(pose[None, :2], transform)[0]
    heading_vector = _transform_directions(
        np.array([[math.cos(float(pose[2])), math.sin(float(pose[2]))]]),
        transform,
    )[0]
    heading = math.atan2(float(heading_vector[1]), float(heading_vector[0]))
    return np.array([position[0], position[1], heading], dtype=np.float32)
