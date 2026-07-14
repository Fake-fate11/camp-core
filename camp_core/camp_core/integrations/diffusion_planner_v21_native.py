from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
    validate_causal_dp_input,
)


HISTORY_STEPS = 31
PADDING_POLICY = "native_zero_left_pad_to_31_v1"
_LATENT_SHAPE = (321, 81, 4)
_FUTURE_PLACEHOLDERS = frozenset(
    {"ego_agent_future", "neighbor_agents_future"}
)
_FORBIDDEN_KEY_PARTS = (
    "future",
    "label",
    "outcome",
    "holdout",
    "safety_cost",
    "metric_result",
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_SAFETY_COMPONENT_WEIGHTS = {
    "collision_any": 100.0,
    "near_miss_noncollision_rate": 10.0,
    "offroad_rate": 20.0,
    "wrong_way_rate": 20.0,
    "red_light_violation_any": 30.0,
    "speed_limit_violation_rate": 10.0,
}


@dataclass(frozen=True)
class CausalInputBoundary:
    causal_input: dict[str, np.ndarray]
    receipt: dict[str, Any]


def array_sha256(array: np.ndarray) -> str:
    value = _as_c_array(array)
    return hashlib.sha256(value.tobytes()).hexdigest()


def deterministic_array_mapping_sha256(data: Mapping[str, Any]) -> str:
    digest = hashlib.sha256()
    for key in sorted(data):
        if not isinstance(key, str):
            raise ValueError("array mapping keys must be strings")
        array = _as_c_array(data[key])
        if array.dtype.hasobject:
            raise ValueError(f"object dtype is forbidden for {key}")
        digest.update(key.encode("utf-8"))
        digest.update(b"\0")
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(b"\0")
        digest.update(
            json.dumps(list(array.shape), separators=(",", ":")).encode("ascii")
        )
        digest.update(b"\0")
        digest.update(array.tobytes())
    return digest.hexdigest()


def causal_input_receipt(
    data: Mapping[str, Any], *, source_observed_frames: int
) -> CausalInputBoundary:
    if (
        isinstance(source_observed_frames, bool)
        or not isinstance(source_observed_frames, (int, np.integer))
        or source_observed_frames < 1
    ):
        raise ValueError("source_observed_frames must be a positive integer")

    copied = {key: value for key, value in data.items()}
    for key in _FUTURE_PLACEHOLDERS:
        copied.pop(key, None)
    forbidden = sorted(
        key
        for key in copied
        if any(part in key.lower() for part in _FORBIDDEN_KEY_PARTS)
    )
    if forbidden:
        raise ValueError(f"forbidden causal input key: {','.join(forbidden)}")

    if "neighbor_agents_past" in copied:
        neighbors = np.asarray(copied["neighbor_agents_past"])
        if neighbors.ndim != 3 or neighbors.shape[0] < 32:
            raise ValueError("neighbor_agents_past must contain at least 32 slots")
        copied["neighbor_agents_past"] = neighbors[:32]

    causal_input = {
        key: np.array(value, copy=True, order="C") for key, value in copied.items()
    }
    errors = validate_causal_dp_input(causal_input)
    if errors:
        raise ValueError("; ".join(errors))
    for key, array in causal_input.items():
        if not np.isfinite(array).all():
            raise ValueError(f"nonfinite causal input: {key}")

    observed_frames = min(int(source_observed_frames), HISTORY_STEPS)
    padded_frames = HISTORY_STEPS - observed_frames
    if padded_frames:
        for key in ("ego_agent_past", "neighbor_agents_past"):
            array = causal_input[key]
            history_axis = 0 if key == "ego_agent_past" else 1
            prefix = np.take(array, range(padded_frames), axis=history_axis)
            if np.any(prefix != 0.0):
                raise ValueError(f"{key} violates native zero left padding")

    arrays = {
        key: {
            "shape": list(causal_input[key].shape),
            "dtype": causal_input[key].dtype.str,
            "sha256": array_sha256(causal_input[key]),
        }
        for key in sorted(causal_input)
    }
    receipt = {
        "source_observed_frames": int(source_observed_frames),
        "observed_frames": observed_frames,
        "padded_frames": padded_frames,
        "truncated_frames": max(int(source_observed_frames) - HISTORY_STEPS, 0),
        "padding_policy": PADDING_POLICY,
        "arrays": arrays,
        "input_sha256": deterministic_array_mapping_sha256(causal_input),
    }
    return CausalInputBoundary(causal_input=causal_input, receipt=receipt)


def candidate_seed(root_seed: int, route_sha256: str, tick_index: int) -> int:
    if not isinstance(route_sha256, str) or not _SHA256_RE.fullmatch(route_sha256):
        raise ValueError("route_sha256 must be a lowercase SHA256 digest")
    if isinstance(root_seed, bool) or not isinstance(root_seed, (int, np.integer)):
        raise ValueError("root_seed must be a nonnegative integer")
    if root_seed < 0:
        raise ValueError("root_seed must be a nonnegative integer")
    if isinstance(tick_index, bool) or not isinstance(tick_index, (int, np.integer)):
        raise ValueError("tick_index must be a nonnegative integer")
    if tick_index < 0:
        raise ValueError("tick_index must be a nonnegative integer")
    payload = f"{int(root_seed)}\0{route_sha256}\0{int(tick_index)}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % 2**63


def candidate_latents(seed: int, *, noise_scale: float) -> np.ndarray:
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if not np.isfinite(noise_scale) or noise_scale <= 0.0:
        raise ValueError("noise_scale must be finite and positive")
    rng = np.random.default_rng(int(seed))
    latents = np.zeros((8, *_LATENT_SHAPE), dtype=np.float32)
    latents[1:] = (
        rng.standard_normal((7, *_LATENT_SHAPE)).astype(np.float32)
        * np.float32(noise_scale)
    )
    return latents


def verify_default_candidate0_identity(
    default_output: np.ndarray, candidate0: np.ndarray
) -> dict[str, Any]:
    default = np.asarray(default_output)
    candidate = np.asarray(candidate0)
    if (
        default.shape != (80, 4)
        or candidate.shape != default.shape
        or default.dtype != np.float32
        or candidate.dtype != default.dtype
    ):
        raise ValueError("default and candidate 0 must have equal shape and dtype")
    if not np.isfinite(default).all() or not np.isfinite(candidate).all():
        raise ValueError("default and candidate 0 must be finite")
    default_sha = array_sha256(default)
    candidate_sha = array_sha256(candidate)
    if not np.array_equal(default, candidate) or default_sha != candidate_sha:
        raise ValueError("DP default/candidate 0 identity failed")
    return {
        "elementwise_equal": True,
        "max_abs_difference": 0.0,
        "default_output_sha256": default_sha,
        "candidate0_sha256": candidate_sha,
        "native_ranked_k8": False,
    }


def verify_candidate_tensor_immutable(
    candidates: np.ndarray, before_sha256: str
) -> dict[str, Any]:
    tensor = np.asarray(candidates)
    if tensor.shape != (8, 80, 4) or tensor.dtype != np.float32:
        raise ValueError("candidate tensor must be float32 [8,80,4]")
    if not np.isfinite(tensor).all():
        raise ValueError("candidate tensor must be finite")
    if not isinstance(before_sha256, str) or not _SHA256_RE.fullmatch(before_sha256):
        raise ValueError("before_sha256 must be a lowercase SHA256 digest")
    after_sha256 = array_sha256(tensor)
    if after_sha256 != before_sha256:
        raise ValueError("candidate tensor mutated")
    return {
        "candidate_tensor_sha256_before": before_sha256,
        "candidate_tensor_sha256_after": after_sha256,
        "candidate_tensor_immutable": True,
    }


def five_point_drivable_coverage(
    points_xy: Any,
    drivable_lanelets: Any,
    point_inside: Any,
) -> bool:
    points = np.asarray(points_xy, dtype=np.float64)
    if points.shape != (5, 2) or not np.isfinite(points).all():
        raise ValueError("drivable proxy requires exactly five finite 2D points")
    lanelets = tuple(drivable_lanelets)
    return all(
        any(bool(point_inside(lanelet, point)) for lanelet in lanelets)
        for point in points
    )


def segments_intersect_2d(a: Any, b: Any, c: Any, d: Any) -> bool:
    first = _finite_xy(a, "segment point a")
    second = _finite_xy(b, "segment point b")
    third = _finite_xy(c, "segment point c")
    fourth = _finite_xy(d, "segment point d")
    o1 = _orientation(first, second, third)
    o2 = _orientation(first, second, fourth)
    o3 = _orientation(third, fourth, first)
    o4 = _orientation(third, fourth, second)
    epsilon = 1e-12
    if (o1 > epsilon and o2 < -epsilon or o1 < -epsilon and o2 > epsilon) and (
        o3 > epsilon and o4 < -epsilon or o3 < -epsilon and o4 > epsilon
    ):
        return True
    return bool(
        (abs(o1) <= epsilon and _on_segment(first, second, third, epsilon))
        or (abs(o2) <= epsilon and _on_segment(first, second, fourth, epsilon))
        or (abs(o3) <= epsilon and _on_segment(third, fourth, first, epsilon))
        or (abs(o4) <= epsilon and _on_segment(third, fourth, second, epsilon))
    )


def diagnostic_constant_velocity_circle_ttc_s(
    *,
    ego_position_xy: Any,
    ego_velocity_xy: Any,
    ego_radius_m: float,
    other_position_xy: Any,
    other_velocity_xy: Any,
    other_radius_m: float,
) -> dict[str, Any]:
    ego_position = _finite_xy(ego_position_xy, "ego_position_xy")
    ego_velocity = _finite_xy(ego_velocity_xy, "ego_velocity_xy")
    other_position = _finite_xy(other_position_xy, "other_position_xy")
    other_velocity = _finite_xy(other_velocity_xy, "other_velocity_xy")
    radii = np.asarray([ego_radius_m, other_radius_m], dtype=np.float64)
    if not np.isfinite(radii).all() or np.any(radii <= 0.0):
        raise ValueError("diagnostic radii must be finite and positive")
    position = other_position - ego_position
    velocity = other_velocity - ego_velocity
    combined_radius = float(radii.sum())
    a = float(velocity @ velocity)
    b = 2.0 * float(position @ velocity)
    c = float(position @ position) - combined_radius**2
    ttc: float | None
    if c <= 0.0:
        ttc = 0.0
    elif a <= 1e-15:
        ttc = None
    else:
        discriminant = b * b - 4.0 * a * c
        if discriminant < 0.0:
            ttc = None
        else:
            root = math.sqrt(max(discriminant, 0.0))
            candidates = [
                value
                for value in ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a))
                if value >= 0.0 and math.isfinite(value)
            ]
            ttc = min(candidates) if candidates else None
    return {
        "name": "constant_velocity_circle_ttc_diagnostic_s",
        "ttc_s": ttc,
        "observed_future_collision_claim": False,
    }


def safety_cost_native_v1(components: Mapping[str, Any]) -> float:
    if set(components) != set(_SAFETY_COMPONENT_WEIGHTS):
        raise ValueError("SafetyCost Native v1 components are incomplete")
    total = 0.0
    for name, weight in _SAFETY_COMPONENT_WEIGHTS.items():
        value = float(components[name])
        if not math.isfinite(value) or value < 0.0 or value > 1.0:
            raise ValueError(f"invalid SafetyCost component: {name}")
        total += weight * value
    return total


def summarize_safety_cost_native_v1(
    records: Any,
) -> dict[str, Any]:
    ticks = list(records)
    if not ticks:
        raise ValueError("SafetyCost requires at least one evaluated tick")
    seen_indices: set[int] = set()
    clearances: list[float] = []
    collision_ticks: list[int] = []
    near_ticks: list[int] = []
    offroad_ticks: list[int] = []
    wrong_way_ticks: list[int] = []
    red_ticks: list[int] = []
    speed_ticks: list[int] = []
    moving_onroad_ticks = 0
    speed_limit_ticks = 0
    maximum_speed_excess = 0.0

    for record in ticks:
        index = _tick_index(record)
        if index in seen_indices:
            raise ValueError(f"duplicate tick_index: {index}")
        seen_indices.add(index)
        clearance = _finite_field(record, "min_obb_clearance_m")
        clearances.append(clearance)
        if clearance <= 1e-6:
            collision_ticks.append(index)
        elif clearance <= 2.0:
            near_ticks.append(index)

        coverage = _bool_field(record, "five_point_drivable_coverage")
        if not coverage:
            offroad_ticks.append(index)
        speed = _finite_field(record, "speed_mps")
        if speed < 0.0:
            raise ValueError("speed_mps must be nonnegative")
        ego_heading = _finite_field(record, "ego_heading_rad")
        route_heading = _finite_field(record, "route_heading_rad")
        if coverage and speed > 0.5:
            moving_onroad_ticks += 1
            heading_error = math.atan2(
                math.sin(ego_heading - route_heading),
                math.cos(ego_heading - route_heading),
            )
            if math.cos(heading_error) < 0.0:
                wrong_way_ticks.append(index)

        red_at_start = _bool_field(record, "red_light_at_interval_start")
        previous_front = _finite_xy(
            _field(record, "front_center_prev_xy"), "front_center_prev_xy"
        )
        current_front = _finite_xy(
            _field(record, "front_center_xy"), "front_center_xy"
        )
        stop_lines = np.asarray(_field(record, "red_stop_lines"), dtype=np.float64)
        if stop_lines.size == 0:
            stop_lines = np.empty((0, 2, 2), dtype=np.float64)
        if stop_lines.ndim != 3 or stop_lines.shape[1:] != (2, 2):
            raise ValueError("red_stop_lines must have shape [N,2,2]")
        if not np.isfinite(stop_lines).all():
            raise ValueError("red_stop_lines must be finite")
        if red_at_start and speed > 0.5 and any(
            segments_intersect_2d(previous_front, current_front, line[0], line[1])
            for line in stop_lines
        ):
            red_ticks.append(index)

        speed_limit = record.get("speed_limit_mps")
        if coverage:
            if speed_limit is None:
                raise ValueError("on-road tick is missing speed_limit_mps")
            limit = float(speed_limit)
            if not math.isfinite(limit) or limit <= 0.0:
                raise ValueError("speed_limit_mps must be finite and positive")
            speed_limit_ticks += 1
            excess = max(speed - limit, 0.0)
            maximum_speed_excess = max(maximum_speed_excess, excess)
            if speed > limit + 1e-6:
                speed_ticks.append(index)

    if moving_onroad_ticks == 0:
        raise ValueError("moving_onroad_ticks denominator is zero")
    if speed_limit_ticks == 0:
        raise ValueError("speed_limit_ticks denominator is zero")
    count = len(ticks)
    components = {
        "collision_any": float(bool(collision_ticks)),
        "near_miss_noncollision_rate": len(near_ticks) / count,
        "offroad_rate": len(offroad_ticks) / count,
        "wrong_way_rate": len(wrong_way_ticks) / moving_onroad_ticks,
        "red_light_violation_any": float(bool(red_ticks)),
        "speed_limit_violation_rate": len(speed_ticks) / speed_limit_ticks,
    }
    return {
        "schema_version": "safety_cost_native_v1",
        "safety_cost": safety_cost_native_v1(components),
        "components": components,
        "raw_counts": {
            "collision_ticks": len(collision_ticks),
            "near_miss_noncollision_ticks": len(near_ticks),
            "offroad_ticks": len(offroad_ticks),
            "wrong_way_ticks": len(wrong_way_ticks),
            "red_light_violation_intervals": len(red_ticks),
            "speed_limit_violation_ticks": len(speed_ticks),
        },
        "denominators": {
            "clearance_ticks": count,
            "drivable_area_ticks": count,
            "moving_onroad_ticks": moving_onroad_ticks,
            "speed_limit_ticks": speed_limit_ticks,
        },
        "minimum_clearance_m": min(clearances),
        "maximum_speed_excess_mps": maximum_speed_excess,
        "event_ticks": {
            "collision": collision_ticks,
            "near_miss_noncollision": near_ticks,
            "offroad": offroad_ticks,
            "wrong_way": wrong_way_ticks,
            "red_light_violation": red_ticks,
            "speed_limit_violation": speed_ticks,
        },
        "five_point_proxy_not_polygon_union": True,
    }


def summarize_route_comfort_native(
    records: Any,
    *,
    dt: float,
    route_progress_m: float,
    route_length_m: float,
    termination_reason: str,
) -> dict[str, Any]:
    ticks = list(records)
    if not ticks:
        raise ValueError("route/comfort summary requires records")
    if not math.isfinite(dt) or not math.isclose(dt, 0.1, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("native route/comfort dt must equal 0.1 seconds")
    progress = float(route_progress_m)
    length = float(route_length_m)
    if not math.isfinite(progress) or progress < 0.0:
        raise ValueError("route_progress_m must be finite and nonnegative")
    if not math.isfinite(length) or length <= 0.0:
        raise ValueError("route_length_m must be finite and positive")
    if not isinstance(termination_reason, str) or not termination_reason:
        raise ValueError("termination_reason must be nonempty")
    positions = np.stack(
        [_finite_xy(_field(record, "position_xy"), "position_xy") for record in ticks]
    )
    speeds = np.asarray(
        [_finite_field(record, "speed_mps") for record in ticks],
        dtype=np.float64,
    )
    headings = np.asarray(
        [_finite_field(record, "ego_heading_rad") for record in ticks],
        dtype=np.float64,
    )
    if np.any(speeds < 0.0):
        raise ValueError("speed_mps must be nonnegative")
    acceleration = np.diff(speeds) / dt
    jerk = np.diff(acceleration) / dt
    yaw_rate = np.arctan2(
        np.sin(np.diff(headings)), np.cos(np.diff(headings))
    ) / dt
    lateral_acceleration = speeds[1:] * yaw_rate
    return {
        "dt_s": dt,
        "route_progress_m": progress,
        "route_length_m": length,
        "route_completion_rate": min(max(progress / length, 0.0), 1.0),
        "termination_reason": termination_reason,
        "distance_traveled_m": float(
            np.linalg.norm(np.diff(positions, axis=0), axis=1).sum()
        ),
        "stopped_fraction": float(np.mean(speeds <= 0.5)),
        "mean_speed_mps": float(np.mean(speeds)),
        "max_speed_mps": float(np.max(speeds)),
        "mean_abs_acceleration_mps2": _mean_abs(acceleration),
        "max_acceleration_mps2": _max_abs(acceleration),
        "mean_abs_jerk_mps3": _mean_abs(jerk),
        "max_jerk_mps3": _max_abs(jerk),
        "mean_abs_yaw_rate_radps": _mean_abs(yaw_rate),
        "max_abs_yaw_rate_radps": _max_abs(yaw_rate),
        "mean_abs_lateral_acceleration_mps2": _mean_abs(lateral_acceleration),
        "max_abs_lateral_acceleration_mps2": _max_abs(lateral_acceleration),
    }


def paired_safety_delta(
    dp_safety_cost: float,
    camp_safety_cost: float,
    *,
    tolerance: float = 1e-12,
) -> dict[str, Any]:
    dp = float(dp_safety_cost)
    camp = float(camp_safety_cost)
    if not math.isfinite(dp) or not math.isfinite(camp) or dp < 0.0 or camp < 0.0:
        raise ValueError("paired safety costs must be finite and nonnegative")
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("paired tolerance must be finite and nonnegative")
    delta = camp - dp
    rounding = np.finfo(np.float64).eps * max(1.0, abs(dp), abs(camp))
    if abs(delta) <= tolerance + rounding:
        result = "tie"
    elif delta < 0.0:
        result = "better"
    else:
        result = "worse"
    return {"dp": dp, "camp": camp, "delta": delta, "result": result}


def aggregate_paired_safety(pairs: Any) -> dict[str, Any]:
    records = list(pairs)
    if not records:
        raise ValueError("paired aggregation requires at least one pair")
    outcomes = {"better": 0, "tie": 0, "worse": 0}
    deltas = []
    for record in records:
        result = record.get("result")
        if result not in outcomes:
            raise ValueError("paired result must be better, tie, or worse")
        delta = float(record.get("delta"))
        if not math.isfinite(delta):
            raise ValueError("paired delta must be finite")
        outcomes[result] += 1
        deltas.append(delta)
    return {
        "pair_count": len(records),
        "better_tie_worse": outcomes,
        "mean_delta": float(np.mean(deltas)),
        "median_delta": float(np.median(deltas)),
    }


def _as_c_array(value: Any) -> np.ndarray:
    array = np.asarray(value)
    if array.ndim and not array.flags.c_contiguous:
        return np.ascontiguousarray(array)
    return array


def _finite_xy(value: Any, name: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (2,) or not np.isfinite(array).all():
        raise ValueError(f"{name} must be a finite 2D point")
    return array


def _orientation(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    return float((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))


def _on_segment(
    a: np.ndarray, b: np.ndarray, point: np.ndarray, epsilon: float
) -> bool:
    return bool(
        min(a[0], b[0]) - epsilon <= point[0] <= max(a[0], b[0]) + epsilon
        and min(a[1], b[1]) - epsilon
        <= point[1]
        <= max(a[1], b[1]) + epsilon
    )


def _field(record: Mapping[str, Any], name: str) -> Any:
    if name not in record:
        raise ValueError(f"missing metric source: {name}")
    return record[name]


def _finite_field(record: Mapping[str, Any], name: str) -> float:
    value = float(_field(record, name))
    if not math.isfinite(value):
        raise ValueError(f"metric source must be finite: {name}")
    return value


def _bool_field(record: Mapping[str, Any], name: str) -> bool:
    value = _field(record, name)
    if not isinstance(value, (bool, np.bool_)):
        raise ValueError(f"metric source must be boolean: {name}")
    return bool(value)


def _tick_index(record: Mapping[str, Any]) -> int:
    value = _field(record, "tick_index")
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 0:
        raise ValueError("tick_index must be a nonnegative integer")
    return int(value)


def _mean_abs(values: np.ndarray) -> float:
    return float(np.mean(np.abs(values))) if values.size else 0.0


def _max_abs(values: np.ndarray) -> float:
    return float(np.max(np.abs(values))) if values.size else 0.0
