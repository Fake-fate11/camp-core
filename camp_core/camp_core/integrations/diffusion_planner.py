from __future__ import annotations

import json
import math
import sys
import time
import types
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Optional, Sequence, Union

import numpy as np

from camp_core.atoms.driver_atoms import (
    DriverAtomContext,
    compute_atom_bank_vector,
    compute_feasibility_mask,
)


AUTOWARE_UNSUPPORTED_REGULATORY_SUBTYPES = frozenset(
    {
        "detection_area",
        "no_stopping_area",
        "road_marking",
        "virtual_traffic_light",
    }
)

CAMP_ATOM_NAMES = (
    "jerk_early",
    "jerk_late",
    "jerk_full",
    "rms_acceleration",
    "speed_limit_margin_0_0",
    "speed_limit_margin_0_5",
    "speed_limit_margin_1_0",
    "lane_deviation",
    "clearance",
)
DP_CAMP_ATOM_NAMES = CAMP_ATOM_NAMES + ("progress_shortfall",)
DP_CAMP_ATOM_NAMES_V8 = DP_CAMP_ATOM_NAMES + (
    "planned_red_light_cost",
    "planned_lateral_acceleration_cost",
)
DP_CAMP_ATOM_NAMES_V9 = DP_CAMP_ATOM_NAMES_V8 + (
    "red_stopping_margin_cost",
)
DP_CAMP_ATOM_NAMES_V10 = DP_CAMP_ATOM_NAMES_V9 + (
    "dp_prior_jerk_excess_cost",
)

DP_CAMP_ATOM_SCHEMAS = {
    len(CAMP_ATOM_NAMES): ("camp_legacy_v1_9d", CAMP_ATOM_NAMES),
    len(DP_CAMP_ATOM_NAMES): ("dp_camp_v7_10d", DP_CAMP_ATOM_NAMES),
    len(DP_CAMP_ATOM_NAMES_V8): ("dp_camp_v8_12d", DP_CAMP_ATOM_NAMES_V8),
    len(DP_CAMP_ATOM_NAMES_V9): ("dp_camp_v9_13d", DP_CAMP_ATOM_NAMES_V9),
    len(DP_CAMP_ATOM_NAMES_V10): ("dp_camp_v10_14d", DP_CAMP_ATOM_NAMES_V10),
}


def atom_schema_for_dimension(num_atoms: int) -> tuple[str, tuple[str, ...]]:
    try:
        version, names = DP_CAMP_ATOM_SCHEMAS[int(num_atoms)]
    except KeyError as exc:
        raise ValueError(
            f"No DP CAMP atom schema is defined for {num_atoms} atoms."
        ) from exc
    return version, tuple(names)


def load_dp_camp_atom_scales(path: Union[str, Path]) -> np.ndarray:
    scales_path = Path(path)
    with scales_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        return np.asarray(payload, dtype=np.float64)
    if "scales" not in payload:
        raise ValueError(
            f"Structured atom scales in {scales_path} need a 'scales' field."
        )
    atom_scales = np.asarray(payload["scales"], dtype=np.float64)
    expected_version, expected_names = atom_schema_for_dimension(atom_scales.size)
    declared_version = payload.get("atom_schema_version")
    declared_names = payload.get("atom_names")
    if (
        declared_version != expected_version
        or tuple(declared_names or ()) != expected_names
    ):
        raise ValueError(
            f"Atom scales schema in {scales_path} does not match "
            f"{expected_version!r} with names {expected_names!r}."
        )
    return atom_scales


DEFAULT_CLOSED_LOOP_OUTCOME_WEIGHTS = {
    "progress": 1.0,
    "collision": 100.0,
    "near_miss": 10.0,
    "lane_violation": 20.0,
    "red_light": 30.0,
    "mean_jerk": 0.25,
    "mean_lateral_acceleration": 1.0,
}

DP_SCENE_FEATURE_KEYS = (
    "ego_current_state",
    "neighbor_agents_past",
    "neighbors_past",
    "neighbor_agents_current_state",
    "neighbors_current_state",
    "route_lanes",
    "route_lanes_speed_limit",
    "route_lanes_has_speed_limit",
    "map_lanes",
    "map_lane_boundaries",
    "traffic_lights",
    "static_objects",
)

DP_SCENE_FEATURE_STATS = (
    "present",
    "finite_fraction",
    "mean",
    "std",
    "min",
    "max",
    "abs_mean",
    "rms",
)

DP_SCENE_FEATURE_NAMES = tuple(
    f"{key}.{stat}"
    for key in DP_SCENE_FEATURE_KEYS
    for stat in DP_SCENE_FEATURE_STATS
)


def install_lanelet2_projection_fallback(map_path: Union[str, Path]) -> bool:
    """Provide a no-ROS MGRSProjector fallback backed by Lanelet2 UTM.

    The upstream simulator imports Autoware's Python ``MGRSProjector`` even
    though the rest of the replay path does not require ROS. When that module
    is unavailable, install a process-local compatibility module whose factory
    returns a standard Lanelet2 UTM projector centered on the map.
    """
    try:
        from autoware_lanelet2_extension_python.projection import MGRSProjector  # noqa: F401

        return False
    except ImportError:
        pass

    try:
        import lanelet2
    except ImportError as exc:
        raise RuntimeError(
            "The no-ROS map path requires the lanelet2 Python package. "
            "Use Python 3.12 with `pip install lanelet2==1.2.2`."
        ) from exc

    node = next(
        (
            element
            for _, element in ET.iterparse(str(map_path), events=("start",))
            if element.tag == "node"
        ),
        None,
    )
    if node is None or "lat" not in node.attrib or "lon" not in node.attrib:
        raise ValueError(f"Lanelet2 map {map_path} has no georeferenced node.")

    origin = lanelet2.io.Origin(
        float(node.attrib["lat"]),
        float(node.attrib["lon"]),
    )
    try:
        projector = lanelet2.projection.UtmProjector(origin, True, False)
    except TypeError:
        projector = lanelet2.projection.UtmProjector(origin)

    package = types.ModuleType("autoware_lanelet2_extension_python")
    projection = types.ModuleType("autoware_lanelet2_extension_python.projection")

    def mgrs_projector(_origin):
        return projector

    projection.MGRSProjector = mgrs_projector
    package.projection = projection
    sys.modules["autoware_lanelet2_extension_python"] = package
    sys.modules["autoware_lanelet2_extension_python.projection"] = projection
    return True


def sanitize_lanelet2_map(
    source: Union[str, Path],
    destination: Union[str, Path],
    *,
    unsupported_subtypes: Sequence[str] = tuple(
        sorted(AUTOWARE_UNSUPPORTED_REGULATORY_SUBTYPES)
    ),
) -> dict[str, Any]:
    """Write a map copy without Autoware-only regulatory elements."""
    source_path = Path(source)
    destination_path = Path(destination)
    if source_path.resolve() == destination_path.resolve():
        raise ValueError("Source and destination maps must be different files.")
    if destination_path.exists():
        raise FileExistsError(f"Destination map already exists: {destination_path}")

    tree = ET.parse(source_path)
    root = tree.getroot()
    unsupported = set(unsupported_subtypes)
    removed_relations: dict[str, str] = {}

    for relation in root.findall("relation"):
        tags = {
            tag.attrib.get("k"): tag.attrib.get("v")
            for tag in relation.findall("tag")
        }
        subtype = tags.get("subtype")
        if tags.get("type") == "regulatory_element" and subtype in unsupported:
            removed_relations[relation.attrib["id"]] = subtype
            root.remove(relation)

    removed_references = 0
    for element in root.iter():
        for member in list(element.findall("member")):
            if (
                member.attrib.get("type") == "relation"
                and member.attrib.get("ref") in removed_relations
            ):
                element.remove(member)
                removed_references += 1

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(destination_path, encoding="utf-8", xml_declaration=True)

    subtype_counts: dict[str, int] = {}
    for subtype in removed_relations.values():
        subtype_counts[subtype] = subtype_counts.get(subtype, 0) + 1
    return {
        "source": str(source_path.resolve()),
        "destination": str(destination_path.resolve()),
        "removed_regulatory_relations": len(removed_relations),
        "removed_references": removed_references,
        "removed_by_subtype": dict(sorted(subtype_counts.items())),
    }


def project_simplex(values: np.ndarray) -> np.ndarray:
    """Project a vector onto the probability simplex."""
    values = np.asarray(values, dtype=np.float64).reshape(-1)
    if values.size == 0:
        raise ValueError("Cannot project an empty vector.")
    if not np.all(np.isfinite(values)):
        raise ValueError("Simplex input must contain only finite values.")

    ordered = np.sort(values)[::-1]
    cumulative = np.cumsum(ordered) - 1.0
    indices = np.arange(1, values.size + 1)
    positive = ordered - cumulative / indices > 0
    if not positive.any():
        return np.full(values.size, 1.0 / values.size, dtype=np.float64)
    rho = indices[positive][-1]
    theta = cumulative[rho - 1] / rho
    return np.maximum(values - theta, 0.0)


def _normalized_weights(weights: np.ndarray, num_atoms: int) -> np.ndarray:
    weights = np.asarray(weights, dtype=np.float64).reshape(-1)
    if weights.shape != (num_atoms,):
        raise ValueError(
            f"Expected {num_atoms} CAMP weights, got shape {weights.shape}."
        )
    weights = np.nan_to_num(weights, nan=0.0, posinf=0.0, neginf=0.0)
    weights = np.maximum(weights, 0.0)
    total = float(weights.sum())
    if total <= 0.0:
        return np.full(num_atoms, 1.0 / num_atoms, dtype=np.float64)
    return weights / total


def _load_checkpoint_payload(path: Path) -> dict[str, Any]:
    if path.suffix == ".npz":
        with np.load(str(path), allow_pickle=False) as payload:
            return {key: payload[key] for key in payload.files}

    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "Loading a CAMP .pt checkpoint requires torch. "
            "Use static_weights_path with a .npy file in a NumPy-only environment."
        ) from exc

    try:
        payload = torch.load(str(path), map_location="cpu", weights_only=False)
    except TypeError:
        payload = torch.load(str(path), map_location="cpu")
    if not isinstance(payload, dict):
        raise ValueError(f"CAMP checkpoint {path} must contain a dictionary.")
    return payload


def _payload_string(payload: dict[str, Any], key: str, default: str) -> str:
    value = payload.get(key)
    if value is None:
        return default
    if isinstance(value, str):
        return value
    arr = np.asarray(value)
    if arr.shape == ():
        return str(arr.item())
    return str(arr.reshape(-1)[0])


def _to_numpy_array(value: Any) -> Optional[np.ndarray]:
    if value is None:
        return None
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    try:
        return np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError):
        return None


def _summary_stats(value: Any, *, clip: float) -> list[float]:
    arr = _to_numpy_array(value)
    if arr is None or arr.size == 0:
        return [0.0] * len(DP_SCENE_FEATURE_STATS)

    flat = arr.reshape(-1)
    finite = np.isfinite(flat)
    finite_fraction = float(np.mean(finite)) if flat.size else 0.0
    if not finite.any():
        return [1.0, finite_fraction, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    values = flat[finite]
    if clip > 0:
        values = np.clip(values, -float(clip), float(clip))
    rms = float(np.sqrt(np.mean(values * values)))
    return [
        1.0,
        finite_fraction,
        float(np.mean(values)),
        float(np.std(values)),
        float(np.min(values)),
        float(np.max(values)),
        float(np.mean(np.abs(values))),
        rms,
    ]


def extract_dp_scene_features(
    model_inputs: dict[str, Any],
    *,
    feature_keys: Sequence[str] = DP_SCENE_FEATURE_KEYS,
    value_clip: float = 1.0e4,
) -> np.ndarray:
    """Extract stable scene features from Diffusion Planner model inputs.

    The bridge intentionally uses the public tensor-converter inputs instead
    of hooking private encoder layers. This keeps the training log compatible
    with upstream Diffusion Planner changes as long as the standard input keys
    are still present.
    """
    features: list[float] = []
    for key in feature_keys:
        features.extend(_summary_stats(model_inputs.get(key), clip=value_clip))
    return np.asarray(features, dtype=np.float64)


def _finite_values(values: Sequence[Any]) -> list[float]:
    finite = []
    for value in values:
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(number):
            finite.append(number)
    return finite


def _min_or_none(values: Sequence[Any]) -> Optional[float]:
    finite = _finite_values(values)
    return float(min(finite)) if finite else None


def _max_or_none(values: Sequence[Any]) -> Optional[float]:
    finite = _finite_values(values)
    return float(max(finite)) if finite else None


def _mean_or_none(values: Sequence[Any]) -> Optional[float]:
    finite = _finite_values(values)
    return float(np.mean(finite)) if finite else None


def _summarize_trajectory_log(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "closed_loop_steps": 0,
            "distance_traveled_m": None,
            "final_goal_distance_m": None,
            "min_goal_distance_m": None,
            "goal_distance_reduction_m": None,
            "goal_distance_reduction_rate": None,
            "mean_speed_mps": None,
            "max_speed_mps": None,
            "mean_abs_acceleration_mps2": None,
            "max_abs_acceleration_mps2": None,
            "mean_abs_jerk_mps3": None,
            "max_abs_jerk_mps3": None,
            "mean_acceleration_magnitude_mps2": None,
            "max_acceleration_magnitude_mps2": None,
            "mean_jerk_magnitude_mps3": None,
            "max_jerk_magnitude_mps3": None,
            "mean_abs_yaw_rate_rps": None,
            "max_abs_yaw_rate_rps": None,
            "mean_lateral_acceleration_mps2": None,
            "max_lateral_acceleration_mps2": None,
        }

    xy = np.asarray(
        [[record.get("x", np.nan), record.get("y", np.nan)] for record in records],
        dtype=np.float64,
    )
    valid_xy = np.all(np.isfinite(xy), axis=1)
    distance = None
    if valid_xy.sum() >= 2:
        diffs = np.diff(xy[valid_xy], axis=0)
        distance = float(np.sum(np.linalg.norm(diffs, axis=1)))

    speeds = np.asarray(_finite_values([record.get("speed") for record in records]))
    headings = np.asarray(
        _finite_values([record.get("heading") for record in records]),
        dtype=np.float64,
    )
    accel = np.diff(speeds) / 0.1 if speeds.size >= 2 else np.asarray([])
    jerk = np.diff(accel) / 0.1 if accel.size >= 2 else np.asarray([])
    acceleration_magnitude = np.asarray([])
    jerk_magnitude = np.asarray([])
    yaw_rate = np.asarray([])
    lateral_acceleration = np.asarray([])
    if speeds.size == headings.size and speeds.size >= 2:
        velocity = np.column_stack(
            [speeds * np.cos(headings), speeds * np.sin(headings)]
        )
        acceleration_vectors = np.diff(velocity, axis=0) / 0.1
        acceleration_magnitude = np.linalg.norm(acceleration_vectors, axis=1)
        if acceleration_vectors.shape[0] >= 2:
            jerk_vectors = np.diff(acceleration_vectors, axis=0) / 0.1
            jerk_magnitude = np.linalg.norm(jerk_vectors, axis=1)
        heading_delta = np.arctan2(
            np.sin(np.diff(headings)),
            np.cos(np.diff(headings)),
        )
        yaw_rate = heading_delta / 0.1
        lateral_acceleration = np.abs(speeds[1:] * yaw_rate)
    goal_distances = _finite_values([record.get("goal_d") for record in records])
    final_goal = goal_distances[-1] if goal_distances else None
    min_goal = min(goal_distances) if goal_distances else None
    reduction = None
    reduction_rate = None
    if len(goal_distances) >= 2:
        reduction = float(goal_distances[0] - goal_distances[-1])
        if goal_distances[0] > 1e-6:
            reduction_rate = float(reduction / goal_distances[0])

    return {
        "closed_loop_steps": len(records),
        "distance_traveled_m": distance,
        "final_goal_distance_m": final_goal,
        "min_goal_distance_m": min_goal,
        "goal_distance_reduction_m": reduction,
        "goal_distance_reduction_rate": reduction_rate,
        "mean_speed_mps": float(np.mean(speeds)) if speeds.size else None,
        "max_speed_mps": float(np.max(speeds)) if speeds.size else None,
        "mean_abs_acceleration_mps2": (
            float(np.mean(np.abs(accel))) if accel.size else None
        ),
        "max_abs_acceleration_mps2": (
            float(np.max(np.abs(accel))) if accel.size else None
        ),
        "mean_abs_jerk_mps3": float(np.mean(np.abs(jerk))) if jerk.size else None,
        "max_abs_jerk_mps3": float(np.max(np.abs(jerk))) if jerk.size else None,
        "mean_acceleration_magnitude_mps2": (
            float(np.mean(acceleration_magnitude))
            if acceleration_magnitude.size
            else None
        ),
        "max_acceleration_magnitude_mps2": (
            float(np.max(acceleration_magnitude))
            if acceleration_magnitude.size
            else None
        ),
        "mean_jerk_magnitude_mps3": (
            float(np.mean(jerk_magnitude)) if jerk_magnitude.size else None
        ),
        "max_jerk_magnitude_mps3": (
            float(np.max(jerk_magnitude)) if jerk_magnitude.size else None
        ),
        "mean_abs_yaw_rate_rps": (
            float(np.mean(np.abs(yaw_rate))) if yaw_rate.size else None
        ),
        "max_abs_yaw_rate_rps": (
            float(np.max(np.abs(yaw_rate))) if yaw_rate.size else None
        ),
        "mean_lateral_acceleration_mps2": (
            float(np.mean(lateral_acceleration))
            if lateral_acceleration.size
            else None
        ),
        "max_lateral_acceleration_mps2": (
            float(np.max(lateral_acceleration))
            if lateral_acceleration.size
            else None
        ),
    }


def _project_route_progress(
    records: list[dict[str, Any]],
    route_centerline: np.ndarray,
) -> dict[str, Any]:
    centerline = np.asarray(route_centerline, dtype=np.float64)
    if len(records) < 1 or centerline.ndim != 2 or centerline.shape[0] < 2:
        return {}

    segments = centerline[1:, :2] - centerline[:-1, :2]
    segment_lengths = np.linalg.norm(segments, axis=1)
    valid = segment_lengths > 1e-6
    if not valid.any():
        return {}
    segment_lengths = np.maximum(segment_lengths, 1e-6)
    directions = segments / segment_lengths[:, np.newaxis]
    arc_starts = np.concatenate([[0.0], np.cumsum(segment_lengths)])[:-1]
    route_length = float(np.sum(segment_lengths))

    progress = 0.0
    max_progress = 0.0
    previous_xy = None
    for record_idx, record in enumerate(records):
        point = np.asarray(
            [record.get("x", np.nan), record.get("y", np.nan)],
            dtype=np.float64,
        )
        if not np.all(np.isfinite(point)):
            continue
        if record_idx == 0:
            previous_xy = point
            continue

        relative = point - centerline[:-1, :2]
        along = np.einsum("ij,ij->i", relative, directions)
        along = np.clip(along, 0.0, segment_lengths)
        projections = centerline[:-1, :2] + directions * along[:, np.newaxis]
        distances = np.linalg.norm(projections - point, axis=1)
        candidate_arcs = arc_starts + along

        step_distance = (
            float(np.linalg.norm(point - previous_xy))
            if previous_xy is not None
            else 0.0
        )
        max_forward_jump = max(15.0, step_distance * 5.0 + 5.0)
        allowed = (
            (candidate_arcs >= progress - 5.0)
            & (candidate_arcs <= progress + max_forward_jump)
        )
        if allowed.any():
            allowed_indices = np.flatnonzero(allowed)
            best_idx = int(allowed_indices[np.argmin(distances[allowed])])
        else:
            best_idx = int(np.argmin(distances))
        progress = max(progress, float(candidate_arcs[best_idx]))
        max_progress = max(max_progress, progress)
        previous_xy = point

    completion = min(max_progress / route_length, 1.0) if route_length > 0 else None
    return {
        "route_length_m": route_length,
        "route_progress_m": max_progress,
        "route_completion_rate": completion,
    }


def _summarize_realized_red_lights(
    records: list[dict[str, Any]],
    *,
    dt: float = 0.1,
) -> dict[str, Any]:
    if len(records) < 2:
        return {}

    violations = 0
    exposure_steps = 0
    evaluated_steps = 0
    for previous, current in zip(records[:-1], records[1:]):
        red_points = np.asarray(previous.get("red_route_points", []), dtype=np.float64)
        if red_points.ndim != 2 or red_points.shape[1] < 4:
            red_points = np.zeros((0, 4), dtype=np.float64)
        if red_points.size:
            exposure_steps += 1

        previous_xy = np.asarray(
            [previous.get("x", np.nan), previous.get("y", np.nan)],
            dtype=np.float64,
        )
        current_xy = np.asarray(
            [current.get("x", np.nan), current.get("y", np.nan)],
            dtype=np.float64,
        )
        heading = float(current.get("heading", np.nan))
        if not (
            np.all(np.isfinite(previous_xy))
            and np.all(np.isfinite(current_xy))
            and np.isfinite(heading)
        ):
            continue
        evaluated_steps += 1
        speed = float(np.linalg.norm(current_xy - previous_xy) / max(dt, 1e-6))
        if speed <= 0.5 or not red_points.size:
            continue

        red_xy = red_points[:, :2]
        red_directions = red_points[:, 2:4]
        direction_norms = np.linalg.norm(red_directions, axis=1)
        valid = direction_norms > 1e-6
        if not valid.any():
            continue
        red_xy = red_xy[valid]
        red_directions = red_directions[valid] / direction_norms[valid, np.newaxis]
        distances = np.linalg.norm(red_xy - current_xy, axis=1)
        ego_direction = np.array([math.cos(heading), math.sin(heading)])
        aligned = red_directions @ ego_direction > 0.5
        if np.any((distances < 3.0) & aligned):
            violations += 1

    denominator = max(evaluated_steps, 1)
    return {
        "red_light_evaluated_steps": evaluated_steps,
        "red_light_exposure_steps": exposure_steps,
        "realized_red_light_violation_steps": violations,
        "realized_red_light_violation_rate": violations / denominator,
        "red_light_violation_steps": violations,
        "red_light_violation_rate": violations / denominator,
        "red_light_metric_source": "closed_loop_state_transition",
    }


def _summarize_clearance_log(
    payload: dict[str, Any],
    *,
    near_miss_threshold_m: float,
) -> dict[str, Any]:
    records = list(payload.get("records", []))
    moving = [record.get("moving_dist") for record in records]
    stopped = [record.get("stopped_dist") for record in records]
    road_border = [record.get("rb_dist") for record in records]

    collision_steps = 0
    near_miss_steps = 0
    for record in records:
        obstacle_distances = _finite_values(
            [record.get("moving_dist"), record.get("stopped_dist")]
        )
        if not obstacle_distances:
            continue
        min_obstacle = min(obstacle_distances)
        if min_obstacle <= 1e-6:
            collision_steps += 1
        if min_obstacle <= near_miss_threshold_m:
            near_miss_steps += 1

    denominator = max(len(records), 1)
    return {
        "clearance_log_steps": len(records),
        "near_miss_threshold_m": float(near_miss_threshold_m),
        "obb_collision_steps": collision_steps,
        "obb_collision_rate": collision_steps / denominator,
        "near_miss_steps": near_miss_steps,
        "near_miss_rate": near_miss_steps / denominator,
        "min_moving_clearance_m": _min_or_none(moving),
        "min_stopped_clearance_m": _min_or_none(stopped),
        "min_obstacle_clearance_m": _min_or_none([*moving, *stopped]),
        "min_road_border_clearance_m": _min_or_none(road_border),
    }


def _truthy_count(records: list[dict[str, Any]], keys: Sequence[str]) -> int:
    count = 0
    for record in records:
        if any(bool(record.get(key)) for key in keys):
            count += 1
    return count


def _summarize_metrics_log(payload: dict[str, Any]) -> dict[str, Any]:
    steps = list(payload.get("steps", []))
    denominator = max(len(steps), 1)
    lane_crossings = _truthy_count(steps, ("lane_crossing",))
    planned_lane_crossings = _truthy_count(steps, ("pred_lane_crossing",))
    collisions = _truthy_count(steps, ("collision",))
    planned_collisions = _truthy_count(steps, ("pred_collision",))
    planned_red_light_violations = sum(
        1
        for record in steps
        if (_finite_values([record.get("pred_red_light")]) or [0.0])[0] < -0.5
    )
    return {
        "metrics_log_steps": len(steps),
        "metrics_collision_steps": collisions,
        "metrics_collision_rate": collisions / denominator,
        "planned_collision_steps": planned_collisions,
        "planned_collision_rate": planned_collisions / denominator,
        "lane_violation_steps": lane_crossings,
        "lane_violation_rate": lane_crossings / denominator,
        "planned_lane_violation_steps": planned_lane_crossings,
        "planned_lane_violation_rate": planned_lane_crossings / denominator,
        "planned_red_light_violation_steps": planned_red_light_violations,
        "planned_red_light_violation_rate": (
            planned_red_light_violations / denominator
        ),
        "min_reward_road_border_distance_m": _min_or_none(
            [record.get("rb_min_dist") for record in steps]
        ),
        "mean_lane_near_fraction": _mean_or_none(
            [record.get("lane_near_frac") for record in steps]
        ),
        "min_lane_gate": _min_or_none([record.get("lane_gate") for record in steps]),
        "min_pred_lane_gate": _min_or_none(
            [record.get("pred_lane_gate") for record in steps]
        ),
    }


def summarize_replay_artifacts(
    output_dir: Union[str, Path],
    *,
    selection_records: Optional[list[dict[str, Any]]] = None,
    replay_result: Optional[dict[str, Any]] = None,
    metric_records: Optional[list[dict[str, Any]]] = None,
    evaluation_records: Optional[list[dict[str, Any]]] = None,
    route_centerline: Optional[np.ndarray] = None,
    near_miss_threshold_m: float = 2.0,
) -> dict[str, Any]:
    """Build a comparable closed-loop summary from Diffusion-Planner outputs."""
    output_path = Path(output_dir)
    summary: dict[str, Any] = {}
    if selection_records is not None:
        summary.update(summarize_selection_records(selection_records, replay_result))
    elif replay_result is not None:
        summary.update(
            {
                "selection_steps": None,
                "selected_index_counts": None,
                "nonzero_selection_rate": None,
                "fallback_rate": None,
                "candidate_feasible_rate": None,
                "mean_feasible_candidates": None,
                "mean_selection_latency_ms": None,
                "p95_selection_latency_ms": None,
                "replay_reason": replay_result.get("reason"),
                "replay_final_step": replay_result.get("final_step"),
                "goal_reached": replay_result.get("goal_reached"),
                "n_npc_spawned": replay_result.get("n_npc_spawned"),
            }
        )

    trajectory_log_path = output_path / "trajectory_log.json"
    if replay_result and replay_result.get("trajectory_log_path"):
        trajectory_log_path = Path(str(replay_result["trajectory_log_path"]))
    trajectory_records: list[dict[str, Any]] = []
    if trajectory_log_path.is_file():
        trajectory_records = json.loads(
            trajectory_log_path.read_text(encoding="utf-8-sig")
        )
        summary.update(_summarize_trajectory_log(trajectory_records))
        if route_centerline is not None:
            summary.update(_project_route_progress(trajectory_records, route_centerline))

    clearance_log_path = output_path / "clearance_log.json"
    if replay_result and replay_result.get("clearance_log_path"):
        clearance_log_path = Path(str(replay_result["clearance_log_path"]))
    if clearance_log_path.is_file():
        summary.update(
            _summarize_clearance_log(
                json.loads(clearance_log_path.read_text(encoding="utf-8-sig")),
                near_miss_threshold_m=near_miss_threshold_m,
            )
        )

    if metric_records is not None:
        summary.update(_summarize_metrics_log({"steps": metric_records}))
    else:
        metrics_log_path = output_path / "metrics_log.json"
        if replay_result and replay_result.get("metrics_log_path"):
            metrics_log_path = Path(str(replay_result["metrics_log_path"]))
        if metrics_log_path.is_file():
            summary.update(
                _summarize_metrics_log(
                    json.loads(metrics_log_path.read_text(encoding="utf-8-sig"))
                )
            )

    if evaluation_records is not None:
        summary.update(_summarize_realized_red_lights(evaluation_records))
    elif "red_light_violation_rate" not in summary and (
        "planned_red_light_violation_rate" in summary
    ):
        summary["red_light_violation_steps"] = summary.get(
            "planned_red_light_violation_steps"
        )
        summary["red_light_violation_rate"] = summary.get(
            "planned_red_light_violation_rate"
        )
        summary["red_light_metric_source"] = "selected_trajectory_plan"

    return summary


def _trajectory_headings(trajectory: np.ndarray) -> np.ndarray:
    trajectory = np.asarray(trajectory, dtype=np.float64)
    if trajectory.shape[1] >= 4:
        headings = np.arctan2(trajectory[:, 3], trajectory[:, 2])
        if np.all(np.isfinite(headings)):
            return headings
    if trajectory.shape[0] < 2:
        return np.zeros(trajectory.shape[0], dtype=np.float64)
    deltas = np.diff(trajectory[:, :2], axis=0)
    headings = np.arctan2(deltas[:, 1], deltas[:, 0])
    return np.concatenate([headings[:1], headings])


def _obb_corners(
    x: float,
    y: float,
    heading: float,
    length: float,
    width: float,
    wheelbase: Optional[float] = None,
) -> np.ndarray:
    cos_h, sin_h = math.cos(heading), math.sin(heading)
    if wheelbase is not None and np.isfinite(wheelbase) and wheelbase > 0:
        rear_overhang = (length - wheelbase) / 2.0
        dx_lo, dx_hi = -rear_overhang, length - rear_overhang
    else:
        dx_lo, dx_hi = -length / 2.0, length / 2.0
    dy_lo, dy_hi = -width / 2.0, width / 2.0
    local = np.array(
        [[dx_lo, dy_lo], [dx_hi, dy_lo], [dx_hi, dy_hi], [dx_lo, dy_hi]],
        dtype=np.float64,
    )
    rotation = np.array([[cos_h, -sin_h], [sin_h, cos_h]], dtype=np.float64)
    return local @ rotation.T + np.array([x, y], dtype=np.float64)


def _obb_center_and_radius(
    x: float,
    y: float,
    heading: float,
    length: float,
    width: float,
    wheelbase: Optional[float] = None,
) -> tuple[np.ndarray, float]:
    offset = (
        float(wheelbase) / 2.0
        if wheelbase is not None and np.isfinite(wheelbase) and wheelbase > 0
        else 0.0
    )
    center = np.array(
        [
            float(x) + offset * math.cos(float(heading)),
            float(y) + offset * math.sin(float(heading)),
        ],
        dtype=np.float64,
    )
    radius = math.hypot(float(length) / 2.0, float(width) / 2.0)
    return center, radius


def _obb_collides(corners_a: np.ndarray, corners_b: np.ndarray) -> bool:
    for corners in (corners_a, corners_b):
        for idx in range(4):
            edge = corners[(idx + 1) % 4] - corners[idx]
            axis = np.array([-edge[1], edge[0]], dtype=np.float64)
            norm = float(np.linalg.norm(axis))
            if norm < 1e-9:
                continue
            axis /= norm
            proj_a = corners_a @ axis
            proj_b = corners_b @ axis
            if float(proj_a.max()) < float(proj_b.min()):
                return False
            if float(proj_b.max()) < float(proj_a.min()):
                return False
    return True


def _point_to_segment_distance(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> float:
    segment = end - start
    denom = float(np.dot(segment, segment))
    if denom <= 1e-12:
        return float(np.linalg.norm(point - start))
    t = float(np.clip(np.dot(point - start, segment) / denom, 0.0, 1.0))
    closest = start + t * segment
    return float(np.linalg.norm(point - closest))


def _obb_distance(corners_a: np.ndarray, corners_b: np.ndarray) -> float:
    if _obb_collides(corners_a, corners_b):
        return 0.0
    distances: list[float] = []
    for corners, other in ((corners_a, corners_b), (corners_b, corners_a)):
        for point in corners:
            for idx in range(4):
                distances.append(
                    _point_to_segment_distance(
                        point,
                        other[idx],
                        other[(idx + 1) % 4],
                    )
                )
    return float(min(distances)) if distances else float("inf")


def _polyline_projection_s(polyline: np.ndarray, point: np.ndarray) -> float:
    line = np.asarray(polyline, dtype=np.float64)
    if line.ndim != 2 or line.shape[0] < 2 or line.shape[1] < 2:
        return 0.0
    point = np.asarray(point, dtype=np.float64).reshape(2)
    deltas = np.diff(line[:, :2], axis=0)
    lengths = np.linalg.norm(deltas, axis=1)
    cumulative = np.concatenate([[0.0], np.cumsum(lengths)])
    best_distance = float("inf")
    best_s = 0.0
    for idx, (start, delta, length) in enumerate(zip(line[:-1, :2], deltas, lengths)):
        if length <= 1e-9:
            continue
        t = float(np.clip(np.dot(point - start, delta) / (length * length), 0.0, 1.0))
        closest = start + t * delta
        distance = float(np.linalg.norm(point - closest))
        if distance < best_distance:
            best_distance = distance
            best_s = float(cumulative[idx] + t * length)
    return best_s


def _red_route_points_from_lanes(route_lanes: Any) -> np.ndarray:
    lanes = np.asarray(route_lanes, dtype=np.float64)
    if lanes.ndim == 4 and lanes.shape[0] == 1:
        lanes = lanes[0]
    if lanes.ndim != 3 or lanes.shape[-1] <= 10:
        return np.zeros((0, 4), dtype=np.float64)
    red_mask = lanes[:, :, 10] > 0.5
    valid = np.linalg.norm(lanes[:, :, :2], axis=-1) > 0.1
    points = lanes[red_mask & valid][:, :4]
    if points.size == 0:
        return np.zeros((0, 4), dtype=np.float64)
    return np.asarray(points, dtype=np.float64)


def red_route_points_from_scene(scene: Any, ego_agent_id: str) -> np.ndarray:
    """Return red route-lane points in the current ego frame."""
    ego = scene.get_agent(ego_agent_id)
    if ego.route_lanes is None:
        return np.zeros((0, 4), dtype=np.float64)
    points = _red_route_points_from_lanes(ego.route_lanes)
    if points.size == 0:
        return points
    ego_xy = np.asarray(ego.current_position, dtype=np.float64)
    ego_heading = float(ego.current_heading)
    xy = _to_ego_frame(points[:, :2], ego_xy, ego_heading)
    directions = points[:, 2:4]
    c = math.cos(-ego_heading)
    s = math.sin(-ego_heading)
    rotation = np.array([[c, -s], [s, c]], dtype=np.float64)
    dirs = directions @ rotation.T
    return np.column_stack([xy, dirs])


def compute_red_stopping_margin_costs(
    candidates: np.ndarray,
    red_route_points: np.ndarray,
    dt: float,
    *,
    comfort_deceleration_mps2: float = 2.0,
    stop_buffer_m: float = 3.0,
    lookahead_m: float = 40.0,
    heading_alignment_threshold: float = 0.5,
) -> np.ndarray:
    """Return a continuous red-light stopping-envelope cost per candidate.

    This is a shadow diagnostic, not part of the deployed v8 atom schema. For
    each future step it measures squared speed above the comfortable stopping
    envelope for the nearest aligned red route point ahead of the candidate:

        v_safe(d) = sqrt(2 * a_comfort * max(d - d_buffer, 0)).

    The excess is proximity-weighted and integrated over time. The resulting
    cost is finite, deterministic, nonnegative, and uses only current-tick
    route-light state and candidate geometry.
    """
    trajectories = np.asarray(candidates, dtype=np.float64)
    if trajectories.ndim != 3 or trajectories.shape[2] < 2:
        raise ValueError(
            "candidates must have shape [K,T,>=2], "
            f"got {trajectories.shape}."
        )
    if not np.all(np.isfinite(trajectories)):
        raise ValueError("candidates must contain only finite values.")
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("dt must be finite and positive.")
    if (
        not np.isfinite(comfort_deceleration_mps2)
        or comfort_deceleration_mps2 <= 0.0
    ):
        raise ValueError("comfort_deceleration_mps2 must be finite and positive.")
    if not np.isfinite(stop_buffer_m) or stop_buffer_m < 0.0:
        raise ValueError("stop_buffer_m must be finite and nonnegative.")
    if not np.isfinite(lookahead_m) or lookahead_m <= stop_buffer_m:
        raise ValueError("lookahead_m must be finite and greater than stop_buffer_m.")
    if (
        not np.isfinite(heading_alignment_threshold)
        or not -1.0 <= heading_alignment_threshold <= 1.0
    ):
        raise ValueError("heading_alignment_threshold must be in [-1, 1].")

    red = np.asarray(red_route_points, dtype=np.float64)
    if red.size == 0:
        return np.zeros(trajectories.shape[0], dtype=np.float64)
    if red.ndim != 2 or red.shape[1] < 4:
        raise ValueError(
            "red_route_points must have shape [R,>=4], "
            f"got {red.shape}."
        )
    if not np.all(np.isfinite(red)):
        raise ValueError("red_route_points must contain only finite values.")
    if trajectories.shape[1] < 2:
        return np.zeros(trajectories.shape[0], dtype=np.float64)

    red_directions = red[:, 2:4]
    red_direction_norms = np.linalg.norm(red_directions, axis=1)
    valid_red = red_direction_norms > 1e-6
    if not valid_red.any():
        return np.zeros(trajectories.shape[0], dtype=np.float64)
    red_xy = red[valid_red, :2]
    red_directions = (
        red_directions[valid_red]
        / red_direction_norms[valid_red, np.newaxis]
    )

    costs = np.zeros(trajectories.shape[0], dtype=np.float64)
    for candidate_index, trajectory in enumerate(trajectories):
        xy = trajectory[:, :2]
        speeds = np.linalg.norm(np.diff(xy, axis=0), axis=1) / float(dt)
        headings = _trajectory_headings(trajectory)[1:]
        heading_vectors = np.column_stack(
            [np.cos(headings), np.sin(headings)]
        )
        relative = (
            red_xy[np.newaxis, :, :]
            - xy[1:, np.newaxis, :]
        )
        distances = np.linalg.norm(relative, axis=2)
        aligned = (
            heading_vectors @ red_directions.T
            > float(heading_alignment_threshold)
        )
        ahead = np.einsum(
            "trd,td->tr",
            relative,
            heading_vectors,
        ) > 0.0
        eligible = aligned & ahead & (distances <= float(lookahead_m))
        nearest = np.min(
            np.where(eligible, distances, np.inf),
            axis=1,
        )
        active = np.isfinite(nearest)
        if not active.any():
            continue
        stopping_distance = np.maximum(
            nearest[active] - float(stop_buffer_m),
            0.0,
        )
        safe_speed = np.sqrt(
            2.0 * float(comfort_deceleration_mps2) * stopping_distance
        )
        speed_excess = np.maximum(speeds[active] - safe_speed, 0.0)
        proximity_weight = np.maximum(
            1.0 - nearest[active] / float(lookahead_m),
            0.0,
        )
        costs[candidate_index] = float(
            float(dt) * np.sum(proximity_weight * speed_excess**2)
        )
    if not np.all(np.isfinite(costs)) or np.any(costs < 0.0):
        raise RuntimeError("Red stopping-margin costs violated the atom contract.")
    return costs


def compute_dp_prior_deviation_costs(candidates: np.ndarray) -> np.ndarray:
    """Return each candidate's mean squared xy deviation from DP Top-1.

    Diffusion-Planner's deterministic simulator prediction uses a zero latent
    trajectory. CAMP candidate generation keeps candidate 0 at the same zero
    latent and samples only the remaining candidates, so candidate 0 is the
    DP-prior reference for the current tick. For a fixed reference trajectory,
    this nonnegative quadratic cost is convex in a candidate trajectory and can
    be audited as a potential Benders-compatible atom.
    """
    trajectories = np.asarray(candidates, dtype=np.float64)
    if (
        trajectories.ndim != 3
        or trajectories.shape[0] < 1
        or trajectories.shape[2] < 2
    ):
        raise ValueError(
            "candidates must have shape [K,T,>=2], "
            f"got {trajectories.shape}."
        )
    if not np.all(np.isfinite(trajectories)):
        raise ValueError("candidates must contain only finite values.")
    reference_xy = trajectories[0:1, :, :2]
    squared_deviation = np.sum(
        (trajectories[:, :, :2] - reference_xy) ** 2,
        axis=2,
    )
    costs = np.mean(squared_deviation, axis=1)
    costs = np.maximum(costs, 0.0)
    if not np.all(np.isfinite(costs)):
        raise RuntimeError("DP-prior deviation costs must be finite.")
    return costs


def compute_dp_prior_comfort_excess_costs(
    candidates: np.ndarray,
    dt: float,
    *,
    horizon_steps: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return jerk and acceleration-norm excess over DP Top-1.

    Candidate 0 is the audited DP-prior reference. For each candidate this
    shadow diagnostic computes mean finite-difference jerk norm and mean
    finite-difference acceleration norm, then clips only the excess over the
    reference to zero. For a fixed reference value, ``max(mean_norm(D y)-c, 0)``
    is nonnegative and convex in the candidate coordinates, so these costs can
    be audited before any schema promotion. When provided, ``horizon_steps``
    restricts the online diagnostic to the first requested candidate steps.
    """
    trajectories = np.asarray(candidates, dtype=np.float64)
    if (
        trajectories.ndim != 3
        or trajectories.shape[0] < 1
        or trajectories.shape[2] < 2
    ):
        raise ValueError(
            "candidates must have shape [K,T,>=2], "
            f"got {trajectories.shape}."
        )
    if not np.all(np.isfinite(trajectories)):
        raise ValueError("candidates must contain only finite values.")
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("dt must be finite and positive.")
    if horizon_steps is not None:
        if isinstance(horizon_steps, bool) or not isinstance(
            horizon_steps,
            (int, np.integer),
        ):
            raise ValueError("horizon_steps must be a positive integer.")
        if int(horizon_steps) <= 0:
            raise ValueError("horizon_steps must be a positive integer.")
        trajectories = trajectories[:, : int(horizon_steps), :]

    xy = trajectories[:, :, :2]
    candidate_count = xy.shape[0]
    if xy.shape[1] < 3:
        zeros = np.zeros(candidate_count, dtype=np.float64)
        return zeros, zeros

    velocity = np.diff(xy, axis=1) / float(dt)
    acceleration = np.diff(velocity, axis=1) / float(dt)
    acceleration_norm = np.linalg.norm(acceleration, axis=2)
    mean_acceleration_norm = np.mean(acceleration_norm, axis=1)

    if acceleration.shape[1] < 2:
        mean_jerk_norm = np.zeros(candidate_count, dtype=np.float64)
    else:
        jerk = np.diff(acceleration, axis=1) / float(dt)
        mean_jerk_norm = np.mean(np.linalg.norm(jerk, axis=2), axis=1)

    jerk_excess = np.maximum(mean_jerk_norm - float(mean_jerk_norm[0]), 0.0)
    acceleration_excess = np.maximum(
        mean_acceleration_norm - float(mean_acceleration_norm[0]),
        0.0,
    )
    if (
        not np.all(np.isfinite(jerk_excess))
        or not np.all(np.isfinite(acceleration_excess))
    ):
        raise RuntimeError("DP-prior comfort excess costs must be finite.")
    return jerk_excess, acceleration_excess


def _trajectory_comfort(trajectory: np.ndarray, dt: float) -> tuple[float, float]:
    xy = np.asarray(trajectory, dtype=np.float64)[:, :2]
    if xy.shape[0] < 3:
        return 0.0, 0.0
    velocity = np.diff(xy, axis=0) / max(float(dt), 1e-6)
    acceleration = np.diff(velocity, axis=0) / max(float(dt), 1e-6)
    mean_lateral = 0.0
    if acceleration.size:
        headings = _trajectory_headings(trajectory)[2:]
        lateral_axes = np.column_stack([-np.sin(headings), np.cos(headings)])
        mean_lateral = float(np.mean(np.abs(np.sum(acceleration * lateral_axes, axis=1))))
    if acceleration.shape[0] < 2:
        return 0.0, mean_lateral
    jerk = np.diff(acceleration, axis=0) / max(float(dt), 1e-6)
    return float(np.mean(np.linalg.norm(jerk, axis=1))), mean_lateral


def _trajectory_lane_violation(
    trajectory: np.ndarray,
    context: DriverAtomContext,
) -> bool:
    line = np.asarray(context.lane_centerline, dtype=np.float64)
    if line.ndim != 2 or line.shape[0] < 2:
        return False
    threshold = float(context.lane_half_width) + float(context.lane_corridor_buffer)
    for point in np.asarray(trajectory, dtype=np.float64)[:, :2]:
        min_distance = float("inf")
        for start, end in zip(line[:-1, :2], line[1:, :2]):
            min_distance = min(min_distance, _point_to_segment_distance(point, start, end))
        if min_distance > threshold:
            return True
    return False


def _trajectory_red_light_violation(
    trajectory: np.ndarray,
    red_points: np.ndarray,
    dt: float,
) -> bool:
    red = np.asarray(red_points, dtype=np.float64)
    if red.ndim != 2 or red.shape[1] < 4 or red.size == 0:
        return False
    headings = _trajectory_headings(trajectory)
    xy = np.asarray(trajectory, dtype=np.float64)[:, :2]
    for previous_xy, current_xy, heading in zip(xy[:-1], xy[1:], headings[1:]):
        speed = float(np.linalg.norm(current_xy - previous_xy) / max(float(dt), 1e-6))
        if speed <= 0.5:
            continue
        red_xy = red[:, :2]
        red_directions = red[:, 2:4]
        norms = np.linalg.norm(red_directions, axis=1)
        valid = norms > 1e-6
        if not valid.any():
            continue
        directions = red_directions[valid] / norms[valid, np.newaxis]
        ego_direction = np.array([math.cos(float(heading)), math.sin(float(heading))])
        aligned = directions @ ego_direction > 0.5
        distances = np.linalg.norm(red_xy[valid] - current_xy, axis=1)
        if np.any((distances < 3.0) & aligned):
            return True
    return False


def compute_candidate_closed_loop_outcomes(
    candidates: np.ndarray,
    context: DriverAtomContext,
    *,
    candidate_obstacles: Optional[np.ndarray] = None,
    red_route_points: Optional[np.ndarray] = None,
    horizon_steps: int = 30,
    near_miss_threshold_m: float = 2.0,
    ego_length: float = 4.5,
    ego_width: float = 1.9,
    ego_wheelbase: float = 2.925,
    weights: Optional[dict[str, float]] = None,
) -> list[dict[str, Any]]:
    """Evaluate short-horizon branch outcomes for each DP ego candidate.

    This intentionally uses realized geometric outcomes over the candidate's
    perfect-tracking branch, not Diffusion Planner's scalar reward. Candidates
    and obstacles are in the current ego frame.
    """
    trajectories = np.asarray(candidates, dtype=np.float64)
    if trajectories.ndim != 3 or trajectories.shape[2] < 2:
        raise ValueError(f"candidates must have shape [K,T,>=2], got {trajectories.shape}.")
    horizon = min(max(int(horizon_steps), 2), trajectories.shape[1])
    dt = float(context.dt)
    score_weights = dict(DEFAULT_CLOSED_LOOP_OUTCOME_WEIGHTS)
    if weights:
        score_weights.update({key: float(value) for key, value in weights.items()})

    obstacles = None
    if candidate_obstacles is not None:
        obstacles = np.asarray(candidate_obstacles, dtype=np.float64)
        if obstacles.ndim == 3:
            obstacles = np.broadcast_to(
                obstacles[np.newaxis],
                (trajectories.shape[0],) + obstacles.shape,
            )
        if obstacles.ndim != 4 or obstacles.shape[0] != trajectories.shape[0]:
            raise ValueError(
                "candidate_obstacles must have shape [K,M,T,D] or [M,T,D], "
                f"got {obstacles.shape}."
            )
    red_points = (
        np.zeros((0, 4), dtype=np.float64)
        if red_route_points is None
        else np.asarray(red_route_points, dtype=np.float64)
    )

    outcomes: list[dict[str, Any]] = []
    for candidate_idx, candidate in enumerate(trajectories):
        branch = candidate[:horizon]
        headings = _trajectory_headings(branch)
        progress = max(
            0.0,
            _polyline_projection_s(context.lane_centerline, branch[-1, :2])
            - _polyline_projection_s(context.lane_centerline, branch[0, :2]),
        )
        lane_violation = _trajectory_lane_violation(branch, context)
        red_light_violation = _trajectory_red_light_violation(branch, red_points, dt)
        mean_jerk, mean_lateral_acc = _trajectory_comfort(branch, dt)

        collision = False
        near_miss = False
        min_clearance = float("inf")
        if context.static_obstacles is not None and len(context.static_obstacles) > 0:
            static_xy = np.asarray(context.static_obstacles, dtype=np.float64)[:, :2]
            distances = np.linalg.norm(
                branch[:, np.newaxis, :2] - static_xy[np.newaxis, :, :],
                axis=-1,
            )
            if distances.size:
                min_static = float(np.min(distances))
                min_clearance = min(min_clearance, min_static)
                if min_static < float(context.safety_radius):
                    collision = True
                if min_static <= float(near_miss_threshold_m):
                    near_miss = True

        if obstacles is not None:
            candidate_obstacle = obstacles[candidate_idx]
            for obstacle in candidate_obstacle:
                obstacle_horizon = min(horizon, obstacle.shape[0])
                for step_idx in range(obstacle_horizon):
                    row = obstacle[step_idx]
                    if row.shape[0] < 2 or not np.all(np.isfinite(row[:2])):
                        continue
                    if np.linalg.norm(row[:2]) < 1e-8:
                        continue
                    if row.shape[0] >= 5 and np.all(np.isfinite(row[:5])):
                        obs_heading = float(row[2])
                        obs_length = max(float(row[3]), 1e-3)
                        obs_width = max(float(row[4]), 1e-3)
                        obs_wheelbase = (
                            float(row[5])
                            if row.shape[0] >= 6 and np.isfinite(row[5]) and row[5] > 0
                            else None
                        )
                        ego_box = _obb_corners(
                            float(branch[step_idx, 0]),
                            float(branch[step_idx, 1]),
                            float(headings[step_idx]),
                            float(ego_length),
                            float(ego_width),
                            float(ego_wheelbase),
                        )
                        obs_box = _obb_corners(
                            float(row[0]),
                            float(row[1]),
                            obs_heading,
                            obs_length,
                            obs_width,
                            obs_wheelbase,
                        )
                        clearance = _obb_distance(ego_box, obs_box)
                    else:
                        clearance = float(
                            np.linalg.norm(branch[step_idx, :2] - row[:2])
                        )
                    min_clearance = min(min_clearance, clearance)
                    if clearance <= 1e-6:
                        collision = True
                    if clearance <= float(near_miss_threshold_m):
                        near_miss = True

        feasible = not (collision or lane_violation or red_light_violation)
        value = (
            score_weights["progress"] * progress
            - score_weights["collision"] * float(collision)
            - score_weights["near_miss"] * float(near_miss)
            - score_weights["lane_violation"] * float(lane_violation)
            - score_weights["red_light"] * float(red_light_violation)
            - score_weights["mean_jerk"] * mean_jerk
            - score_weights["mean_lateral_acceleration"] * mean_lateral_acc
        )
        outcomes.append(
            {
                "candidate_index": int(candidate_idx),
                "horizon_steps": int(horizon),
                "progress_m": float(progress),
                "collision": bool(collision),
                "near_miss": bool(near_miss),
                "lane_violation": bool(lane_violation),
                "red_light_violation": bool(red_light_violation),
                "mean_jerk_mps3": float(mean_jerk),
                "mean_lateral_acceleration_mps2": float(mean_lateral_acc),
                "min_obstacle_clearance_m": (
                    None if not np.isfinite(min_clearance) else float(min_clearance)
                ),
                "feasible": bool(feasible),
                "value": float(value),
            }
        )
    return outcomes


@dataclass(frozen=True)
class CAMPSelectionResult:
    selected_index: int
    selected_trajectory: np.ndarray
    atoms: np.ndarray
    normalized_atoms: np.ndarray
    feasible_mask: np.ndarray
    infeasibility_reasons: tuple[tuple[str, ...], ...]
    scores: np.ndarray
    weights: np.ndarray
    selection_scores: np.ndarray
    selection_weights: np.ndarray
    selection_normalized_atoms: np.ndarray
    used_fallback: bool
    timings_ms: dict[str, float]


def summarize_selection_records(
    records: list[dict[str, Any]],
    replay_result: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Summarize CAMP selection behavior for one closed-loop replay."""
    num_steps = len(records)
    selected_counts: dict[str, int] = {}
    selected_nonzero = 0
    fallback_count = 0
    feasible_candidates = 0
    total_candidates = 0
    latency_fields = {
        "latency_ms_including_candidate_generation": "selection_latency_ms",
        "latency_ms_candidate_generation": "candidate_generation_latency_ms",
        "latency_ms_shadow_dp_prior_deviation": (
            "shadow_dp_prior_deviation_latency_ms"
        ),
        "latency_ms_shadow_dp_prior_comfort_excess": (
            "shadow_dp_prior_comfort_excess_latency_ms"
        ),
        "latency_ms_context_and_obstacles": "context_and_obstacles_latency_ms",
        "latency_ms_reward_scoring": "reward_scoring_latency_ms",
        "latency_ms_outcome_collection": "outcome_collection_latency_ms",
        "latency_ms_red_stopping_margin_atom": (
            "red_stopping_margin_atom_latency_ms"
        ),
        "latency_ms_camp_selection": "camp_selection_latency_ms",
        "latency_ms_camp_atom_computation": "camp_atom_computation_latency_ms",
        "latency_ms_camp_feasibility": "camp_feasibility_latency_ms",
        "latency_ms_camp_collision_checks": "camp_collision_checks_latency_ms",
        "latency_ms_camp_scoring": "camp_scoring_latency_ms",
    }
    latencies: dict[str, list[float]] = {
        record_key: [] for record_key in latency_fields
    }
    infeasibility_reason_counts: dict[str, int] = {}

    for record in records:
        selected_index = int(record["selected_index"])
        key = str(selected_index)
        selected_counts[key] = selected_counts.get(key, 0) + 1
        selected_nonzero += int(selected_index != 0)
        fallback_count += int(bool(record.get("used_fallback", False)))

        feasible_mask = np.asarray(record.get("feasible_mask", []), dtype=bool)
        feasible_candidates += int(feasible_mask.sum())
        total_candidates += int(feasible_mask.size)
        for candidate_reasons in record.get("infeasibility_reasons", []):
            for reason in candidate_reasons:
                key = str(reason)
                infeasibility_reason_counts[key] = (
                    infeasibility_reason_counts.get(key, 0) + 1
                )

        for record_key in latency_fields:
            latency = record.get(record_key)
            if latency is not None and np.isfinite(latency):
                latencies[record_key].append(float(latency))

    denominator = max(num_steps, 1)
    summary: dict[str, Any] = {
        "selection_steps": num_steps,
        "selected_index_counts": selected_counts,
        "nonzero_selection_rate": selected_nonzero / denominator,
        "fallback_rate": fallback_count / denominator,
        "candidate_feasible_rate": (
            feasible_candidates / total_candidates if total_candidates else 0.0
        ),
        "mean_feasible_candidates": (
            feasible_candidates / denominator if num_steps else 0.0
        ),
        "candidate_infeasibility_reason_counts": infeasibility_reason_counts,
    }
    for record_key, summary_stem in latency_fields.items():
        values = latencies[record_key]
        summary[f"mean_{summary_stem}"] = (
            float(np.mean(values)) if values else None
        )
        summary[f"p95_{summary_stem}"] = (
            float(np.percentile(values, 95)) if values else None
        )
    if replay_result is not None:
        summary.update(
            {
                "replay_reason": replay_result.get("reason"),
                "replay_final_step": replay_result.get("final_step"),
                "goal_reached": replay_result.get("goal_reached"),
                "n_npc_spawned": replay_result.get("n_npc_spawned"),
            }
        )
    return summary


class CAMPSelector:
    """Score Diffusion-Planner trajectory candidates with CAMP atoms.

    ``mode="static"`` uses the learned offline CAMP weights and is the
    deployable bridge for the current Diffusion-Planner simulator.
    ``mode="linear"`` uses the CAMP ``Theta`` matrix and requires a compatible
    per-step scene embedding. A Diffusion-Planner encoder feature is not
    considered compatible without a separately trained adapter.
    """

    def __init__(
        self,
        atom_scales: np.ndarray,
        *,
        static_weights: Optional[np.ndarray] = None,
        theta: Optional[np.ndarray] = None,
        feature_center: Optional[np.ndarray] = None,
        feature_scale: Optional[np.ndarray] = None,
        feature_clip: float = 5.0,
        linear_activation: str = "project_simplex",
        mode: str = "static",
        fallback_mode: str = "uniform",
        fallback_atom_scales: Optional[np.ndarray] = None,
        fallback_static_weights: Optional[np.ndarray] = None,
        atom_clip: float = 10.0,
    ) -> None:
        self.atom_scales = np.asarray(atom_scales, dtype=np.float64).reshape(-1)
        if self.atom_scales.size == 0:
            raise ValueError("atom_scales must not be empty.")
        if not np.all(np.isfinite(self.atom_scales)):
            raise ValueError("atom_scales must contain only finite values.")
        self.atom_scales = np.maximum(self.atom_scales, 1e-6)
        self.num_atoms = int(self.atom_scales.size)

        if mode not in {"static", "linear"}:
            raise ValueError(f"Unknown CAMP selector mode {mode!r}.")
        self.mode = mode
        self.atom_clip = float(atom_clip)
        if linear_activation not in {"project_simplex", "softmax"}:
            raise ValueError(
                "linear_activation must be 'project_simplex' or 'softmax', "
                f"got {linear_activation!r}."
            )
        self.linear_activation = linear_activation
        self.feature_clip = float(feature_clip)
        if fallback_mode not in {"uniform", "learned"}:
            raise ValueError(
                "fallback_mode must be 'uniform' or 'learned', "
                f"got {fallback_mode!r}."
            )
        self.fallback_mode = fallback_mode
        if (fallback_atom_scales is None) != (fallback_static_weights is None):
            raise ValueError(
                "fallback_atom_scales and fallback_static_weights must be "
                "provided together."
            )
        self.fallback_atom_scales = None
        self.fallback_static_weights = None
        if fallback_atom_scales is not None:
            fallback_scales = np.asarray(
                fallback_atom_scales, dtype=np.float64
            ).reshape(-1)
            if fallback_scales.shape != (self.num_atoms,):
                raise ValueError(
                    "fallback_atom_scales must match the primary atom dimension."
                )
            if not np.all(np.isfinite(fallback_scales)):
                raise ValueError(
                    "fallback_atom_scales must contain only finite values."
                )
            self.fallback_atom_scales = np.maximum(fallback_scales, 1e-6)
            self.fallback_static_weights = _normalized_weights(
                fallback_static_weights,
                self.num_atoms,
            )

        self.static_weights = None
        if static_weights is not None:
            self.static_weights = _normalized_weights(static_weights, self.num_atoms)

        self.theta = None
        if theta is not None:
            theta_arr = np.asarray(theta, dtype=np.float64)
            if theta_arr.ndim != 2 or theta_arr.shape[0] != self.num_atoms:
                raise ValueError(
                    "Theta must have shape [num_atoms, embedding_dim + 1], "
                    f"got {theta_arr.shape}."
                )
            self.theta = theta_arr

        self.feature_center = None
        self.feature_scale = None
        if self.theta is not None:
            expected_dim = self.theta.shape[1] - 1
            if feature_center is not None:
                center = np.asarray(feature_center, dtype=np.float64).reshape(-1)
                if center.shape != (expected_dim,):
                    raise ValueError(
                        "feature_center must match Theta embedding dimension, "
                        f"got {center.shape}, expected ({expected_dim},)."
                    )
                self.feature_center = center
            if feature_scale is not None:
                scale = np.asarray(feature_scale, dtype=np.float64).reshape(-1)
                if scale.shape != (expected_dim,):
                    raise ValueError(
                        "feature_scale must match Theta embedding dimension, "
                        f"got {scale.shape}, expected ({expected_dim},)."
                    )
                self.feature_scale = np.maximum(scale, 1e-6)

        if self.mode == "static" and self.static_weights is None:
            raise ValueError("Static CAMP selection requires static_weights.")
        if self.mode == "linear" and self.theta is None:
            raise ValueError("Linear CAMP selection requires Theta.")

    @classmethod
    def from_files(
        cls,
        *,
        atom_scales_path: Union[str, Path],
        checkpoint_path: Optional[Union[str, Path]] = None,
        static_weights_path: Optional[Union[str, Path]] = None,
        fallback_atom_scales_path: Optional[Union[str, Path]] = None,
        fallback_static_weights_path: Optional[Union[str, Path]] = None,
        mode: str = "static",
        fallback_mode: str = "uniform",
        atom_clip: float = 10.0,
    ) -> "CAMPSelector":
        scales_path = Path(atom_scales_path)
        atom_scales = load_dp_camp_atom_scales(scales_path)

        static_weights = None
        theta = None
        feature_center = None
        feature_scale = None
        feature_clip = 5.0
        linear_activation = "project_simplex"
        if checkpoint_path is not None:
            payload = _load_checkpoint_payload(Path(checkpoint_path))
            if "offline_weights" in payload:
                static_weights = np.asarray(payload["offline_weights"], dtype=np.float64)
            if "Theta" in payload:
                theta = np.asarray(payload["Theta"], dtype=np.float64)
            if "feature_center" in payload:
                feature_center = np.asarray(payload["feature_center"], dtype=np.float64)
            if "feature_scale" in payload:
                feature_scale = np.asarray(payload["feature_scale"], dtype=np.float64)
            if "feature_clip" in payload:
                feature_clip = float(np.asarray(payload["feature_clip"]).reshape(-1)[0])
            linear_activation = _payload_string(
                payload,
                "linear_activation",
                linear_activation,
            )
        if static_weights_path is not None:
            static_weights = np.load(str(static_weights_path))
        fallback_atom_scales = (
            None
            if fallback_atom_scales_path is None
            else load_dp_camp_atom_scales(fallback_atom_scales_path)
        )
        fallback_static_weights = (
            None
            if fallback_static_weights_path is None
            else np.load(str(fallback_static_weights_path))
        )

        return cls(
            atom_scales,
            static_weights=static_weights,
            theta=theta,
            feature_center=feature_center,
            feature_scale=feature_scale,
            feature_clip=feature_clip,
            linear_activation=linear_activation,
            mode=mode,
            fallback_mode=fallback_mode,
            fallback_atom_scales=fallback_atom_scales,
            fallback_static_weights=fallback_static_weights,
            atom_clip=atom_clip,
        )

    def weights_for(self, scene_embedding: Optional[np.ndarray] = None) -> np.ndarray:
        if self.mode == "static":
            return self.static_weights.copy()

        if scene_embedding is None:
            raise ValueError(
                "Linear CAMP selection requires a compatible scene_embedding. "
                "Do not pass raw Diffusion-Planner encoder features without a trained adapter."
            )
        embedding = np.asarray(scene_embedding, dtype=np.float64).reshape(-1)
        expected_dim = self.theta.shape[1] - 1
        if embedding.shape != (expected_dim,):
            raise ValueError(
                f"Theta expects embedding_dim={expected_dim}, got {embedding.shape}."
            )
        if self.feature_center is not None:
            embedding = embedding - self.feature_center
        if self.feature_scale is not None:
            embedding = embedding / self.feature_scale
        if self.feature_clip > 0:
            embedding = np.clip(embedding, -self.feature_clip, self.feature_clip)
        raw = self.theta @ np.append(embedding, 1.0)
        if self.linear_activation == "softmax":
            shifted = raw - float(np.max(raw))
            weights = np.exp(shifted)
            total = float(np.sum(weights))
            if total <= 0.0 or not np.isfinite(total):
                return np.full(self.num_atoms, 1.0 / self.num_atoms, dtype=np.float64)
            return weights / total
        return project_simplex(raw)

    def select(
        self,
        candidates: np.ndarray,
        context: DriverAtomContext,
        *,
        scene_embedding: Optional[np.ndarray] = None,
        candidate_obstacles: Optional[np.ndarray] = None,
        candidate_progress: Optional[np.ndarray] = None,
        candidate_planned_red_light_cost: Optional[np.ndarray] = None,
        candidate_red_stopping_margin_cost: Optional[np.ndarray] = None,
        candidate_dp_prior_jerk_excess_cost: Optional[np.ndarray] = None,
        external_feasible_mask: Optional[np.ndarray] = None,
        external_infeasibility_reasons: Optional[Sequence[Sequence[str]]] = None,
        apply_context_feasibility: bool = True,
        ego_length: float = 4.5,
        ego_width: float = 1.9,
        ego_wheelbase: float = 2.925,
    ) -> CAMPSelectionResult:
        """Select one trajectory from ``[K, T, >=2]`` candidates.

        ``candidate_obstacles`` may be ``[K, M, T, D]`` for candidate-specific
        neighbor predictions or ``[M, T, D]`` for one shared obstacle forecast.
        ``D >= 2`` uses point-distance collision. ``D >= 5`` is interpreted as
        ``x, y, heading, length, width[, wheelbase]`` and enables OBB checks.
        """
        select_start = time.perf_counter()
        candidates = np.asarray(candidates, dtype=np.float64)
        if candidates.ndim != 3 or candidates.shape[0] < 1 or candidates.shape[2] < 2:
            raise ValueError(
                "candidates must have shape [K, T, >=2], "
                f"got {candidates.shape}."
            )
        if candidates.shape[1] < 2:
            raise ValueError("Each candidate must contain at least two timesteps.")

        obstacles = None
        if candidate_obstacles is not None:
            obstacles = np.asarray(candidate_obstacles, dtype=np.float64)
            if obstacles.ndim == 3:
                obstacles = np.broadcast_to(
                    obstacles[np.newaxis],
                    (candidates.shape[0],) + obstacles.shape,
                )
            expected_prefix = (candidates.shape[0],)
            if obstacles.ndim != 4 or obstacles.shape[:1] != expected_prefix:
                raise ValueError(
                    "candidate_obstacles must have shape [K, M, T, 2] "
                    f"or [M, T, 2], got {obstacles.shape}."
                )
            if obstacles.shape[-1] < 2:
                raise ValueError("Obstacle trajectories need at least x/y coordinates.")

        external_mask = None
        if external_feasible_mask is not None:
            external_mask = np.asarray(external_feasible_mask, dtype=bool).reshape(-1)
            if external_mask.shape != (candidates.shape[0],):
                raise ValueError(
                    "external_feasible_mask must match candidate count, "
                    f"got {external_mask.shape}, expected ({candidates.shape[0]},)."
                )
        external_reasons = external_infeasibility_reasons
        if external_reasons is not None and len(external_reasons) != candidates.shape[0]:
            raise ValueError(
                "external_infeasibility_reasons must match candidate count, "
                f"got {len(external_reasons)}, expected {candidates.shape[0]}."
            )
        progress = None
        if candidate_progress is not None:
            progress = np.asarray(candidate_progress, dtype=np.float64).reshape(-1)
            if progress.shape != (candidates.shape[0],):
                raise ValueError(
                    "candidate_progress must match candidate count, "
                    f"got {progress.shape}, expected ({candidates.shape[0]},)."
                )

        atoms = []
        feasible = []
        infeasibility_reasons = []
        atom_computation_seconds = 0.0
        feasibility_seconds = 0.0
        collision_seconds = 0.0
        for candidate_idx, trajectory in enumerate(candidates):
            local_context = context
            if obstacles is not None:
                dynamic = {
                    obstacle_idx: obstacle[:, :2]
                    for obstacle_idx, obstacle in enumerate(obstacles[candidate_idx])
                    if np.any(np.abs(obstacle[:, :2]) > 1e-8)
                }
                local_context = replace(context, dynamic_obstacles=dynamic)

            trajectory_xy = trajectory[:, :2]
            phase_start = time.perf_counter()
            atom_vector = compute_atom_bank_vector(local_context, trajectory_xy)
            atom_computation_seconds += time.perf_counter() - phase_start
            if atom_vector.shape != (len(CAMP_ATOM_NAMES),):
                raise ValueError(
                    f"Base CAMP atom dimension is {atom_vector.shape}, "
                    f"expected ({len(CAMP_ATOM_NAMES)},)."
                )
            atoms.append(atom_vector)
            reasons = []
            phase_start = time.perf_counter()
            if apply_context_feasibility:
                if not compute_feasibility_mask(
                    local_context,
                    trajectory_xy,
                    check_speed=False,
                    check_lane=True,
                ):
                    reasons.append("lane_corridor")
                if not compute_feasibility_mask(
                    local_context,
                    trajectory_xy,
                    check_speed=True,
                    check_lane=False,
                ):
                    reasons.append("speed_cap")
            if external_mask is not None and not external_mask[candidate_idx]:
                if external_reasons is None:
                    reasons.append("external_gate")
                else:
                    reasons.extend(
                        str(reason) for reason in external_reasons[candidate_idx]
                    )
            feasibility_seconds += time.perf_counter() - phase_start
            phase_start = time.perf_counter()
            collision_reason = self._collision_failure_reason(
                local_context,
                trajectory,
                candidate_obstacles=(
                    obstacles[candidate_idx] if obstacles is not None else None
                ),
                ego_length=ego_length,
                ego_width=ego_width,
                ego_wheelbase=ego_wheelbase,
            )
            collision_seconds += time.perf_counter() - phase_start
            if collision_reason is not None:
                reasons.append(collision_reason)
            reasons = list(dict.fromkeys(reasons))
            feasible.append(not reasons)
            infeasibility_reasons.append(tuple(reasons))

        atoms_arr = np.asarray(atoms, dtype=np.float64)
        feasible_mask = np.asarray(feasible, dtype=bool)
        if self.num_atoms in (
            len(DP_CAMP_ATOM_NAMES),
            len(DP_CAMP_ATOM_NAMES_V8),
            len(DP_CAMP_ATOM_NAMES_V9),
            len(DP_CAMP_ATOM_NAMES_V10),
        ):
            if progress is None:
                progress = np.linalg.norm(
                    np.diff(candidates[:, :, :2], axis=1),
                    axis=-1,
                ).sum(axis=1)
            progress = np.nan_to_num(progress, nan=0.0, posinf=0.0, neginf=0.0)
            reference_progress = float(
                np.max(progress[feasible_mask])
                if feasible_mask.any()
                else np.max(progress)
            )
            progress_shortfall = np.maximum(reference_progress - progress, 0.0)
            extra_atoms = [progress_shortfall.reshape(-1, 1)]
            if self.num_atoms in (
                len(DP_CAMP_ATOM_NAMES_V8),
                len(DP_CAMP_ATOM_NAMES_V9),
                len(DP_CAMP_ATOM_NAMES_V10),
            ):
                if candidate_planned_red_light_cost is None:
                    raise ValueError(
                        "DP v8/v9/v10 CAMP selection requires "
                        "candidate_planned_red_light_cost."
                    )
                red_light_cost = np.asarray(
                    candidate_planned_red_light_cost,
                    dtype=np.float64,
                ).reshape(-1)
                if red_light_cost.shape != (candidates.shape[0],):
                    raise ValueError(
                        "candidate_planned_red_light_cost must match candidate "
                        "count, "
                        f"got {red_light_cost.shape}, expected "
                        f"({candidates.shape[0]},)."
                    )
                red_light_cost = np.nan_to_num(
                    red_light_cost, nan=0.0, posinf=0.0, neginf=0.0
                )
                red_light_cost = np.maximum(red_light_cost, 0.0)
                phase_start = time.perf_counter()
                lateral_acceleration_cost = np.asarray(
                    [
                        _trajectory_comfort(candidate, context.dt)[1]
                        for candidate in candidates
                    ],
                    dtype=np.float64,
                )
                atom_computation_seconds += time.perf_counter() - phase_start
                lateral_acceleration_cost = np.nan_to_num(
                    lateral_acceleration_cost, nan=0.0, posinf=0.0, neginf=0.0
                )
                lateral_acceleration_cost = np.maximum(
                    lateral_acceleration_cost, 0.0
                )
                extra_atoms.extend(
                    [
                        red_light_cost.reshape(-1, 1),
                        lateral_acceleration_cost.reshape(-1, 1),
                    ]
                )
            if self.num_atoms in (
                len(DP_CAMP_ATOM_NAMES_V9),
                len(DP_CAMP_ATOM_NAMES_V10),
            ):
                if candidate_red_stopping_margin_cost is None:
                    raise ValueError(
                        "DP v9/v10 CAMP selection requires "
                        "candidate_red_stopping_margin_cost."
                    )
                red_stopping_margin_cost = np.asarray(
                    candidate_red_stopping_margin_cost,
                    dtype=np.float64,
                ).reshape(-1)
                if red_stopping_margin_cost.shape != (candidates.shape[0],):
                    raise ValueError(
                        "candidate_red_stopping_margin_cost must match candidate "
                        "count, "
                        f"got {red_stopping_margin_cost.shape}, expected "
                        f"({candidates.shape[0]},)."
                    )
                if (
                    not np.all(np.isfinite(red_stopping_margin_cost))
                    or np.any(red_stopping_margin_cost < 0.0)
                ):
                    raise ValueError(
                        "candidate_red_stopping_margin_cost must contain finite "
                        "nonnegative costs."
                    )
                extra_atoms.append(red_stopping_margin_cost.reshape(-1, 1))
            if self.num_atoms == len(DP_CAMP_ATOM_NAMES_V10):
                if candidate_dp_prior_jerk_excess_cost is None:
                    raise ValueError(
                        "DP v10 CAMP selection requires "
                        "candidate_dp_prior_jerk_excess_cost."
                    )
                dp_prior_jerk_excess_cost = np.asarray(
                    candidate_dp_prior_jerk_excess_cost,
                    dtype=np.float64,
                ).reshape(-1)
                if dp_prior_jerk_excess_cost.shape != (candidates.shape[0],):
                    raise ValueError(
                        "candidate_dp_prior_jerk_excess_cost must match "
                        "candidate count, "
                        f"got {dp_prior_jerk_excess_cost.shape}, expected "
                        f"({candidates.shape[0]},)."
                    )
                if (
                    not np.all(np.isfinite(dp_prior_jerk_excess_cost))
                    or np.any(dp_prior_jerk_excess_cost < 0.0)
                ):
                    raise ValueError(
                        "candidate_dp_prior_jerk_excess_cost must contain "
                        "finite nonnegative costs."
                    )
                extra_atoms.append(
                    dp_prior_jerk_excess_cost.reshape(-1, 1)
                )
            atoms_arr = np.concatenate(
                [atoms_arr, *extra_atoms],
                axis=1,
            )
        elif self.num_atoms != len(CAMP_ATOM_NAMES):
            raise ValueError(
                "Diffusion Planner CAMP scales must contain either "
                f"{len(CAMP_ATOM_NAMES)} legacy atoms or "
                f"{len(DP_CAMP_ATOM_NAMES)} atoms with progress_shortfall or "
                f"{len(DP_CAMP_ATOM_NAMES_V8)} atoms with planned_red_light_cost "
                f"and planned_lateral_acceleration_cost or "
                f"{len(DP_CAMP_ATOM_NAMES_V9)} atoms with red_stopping_margin_cost, "
                f"{len(DP_CAMP_ATOM_NAMES_V10)} atoms with "
                "dp_prior_jerk_excess_cost, "
                f"got {self.num_atoms}."
            )
        normalized = atoms_arr / self.atom_scales.reshape(1, -1)
        positive_inf = self.atom_clip if self.atom_clip > 0 else np.finfo(np.float64).max
        normalized = np.nan_to_num(
            normalized, nan=0.0, posinf=positive_inf, neginf=0.0
        )
        normalized = np.maximum(normalized, 0.0)
        if self.atom_clip > 0:
            normalized = np.clip(normalized, 0.0, self.atom_clip)

        weights = self.weights_for(scene_embedding)
        scores = normalized @ weights
        used_fallback = not feasible_mask.any()
        selection_weights = weights
        selection_normalized = normalized
        if used_fallback:
            if self.fallback_mode == "learned":
                if self.fallback_static_weights is None:
                    selection_scores = scores.copy()
                else:
                    selection_weights = self.fallback_static_weights
                    selection_normalized = atoms_arr / (
                        self.fallback_atom_scales.reshape(1, -1)
                    )
                    selection_normalized = np.nan_to_num(
                        selection_normalized,
                        nan=0.0,
                        posinf=positive_inf,
                        neginf=0.0,
                    )
                    selection_normalized = np.maximum(selection_normalized, 0.0)
                    if self.atom_clip > 0:
                        selection_normalized = np.clip(
                            selection_normalized,
                            0.0,
                            self.atom_clip,
                        )
                    selection_scores = selection_normalized @ selection_weights
            else:
                selection_weights = np.full(
                    self.num_atoms, 1.0 / self.num_atoms
                )
                selection_scores = normalized @ selection_weights
        else:
            selection_scores = scores.copy()
            selection_scores[~feasible_mask] = np.inf

        selected_index = int(np.argmin(selection_scores))
        select_done = time.perf_counter()
        scoring_seconds = max(
            (select_done - select_start)
            - atom_computation_seconds
            - feasibility_seconds
            - collision_seconds,
            0.0,
        )
        return CAMPSelectionResult(
            selected_index=selected_index,
            selected_trajectory=candidates[selected_index].copy(),
            atoms=atoms_arr,
            normalized_atoms=normalized,
            feasible_mask=feasible_mask,
            infeasibility_reasons=tuple(infeasibility_reasons),
            scores=scores,
            weights=weights,
            selection_scores=selection_scores,
            selection_weights=selection_weights,
            selection_normalized_atoms=selection_normalized,
            used_fallback=used_fallback,
            timings_ms={
                "atom_computation": atom_computation_seconds * 1000.0,
                "feasibility": feasibility_seconds * 1000.0,
                "collision_checks": collision_seconds * 1000.0,
                "scoring": scoring_seconds * 1000.0,
            },
        )

    @staticmethod
    def _collision_free(
        context: DriverAtomContext,
        trajectory: np.ndarray,
        *,
        candidate_obstacles: Optional[np.ndarray] = None,
        ego_length: float = 4.5,
        ego_width: float = 1.9,
        ego_wheelbase: float = 2.925,
    ) -> bool:
        return (
            CAMPSelector._collision_failure_reason(
                context,
                trajectory,
                candidate_obstacles=candidate_obstacles,
                ego_length=ego_length,
                ego_width=ego_width,
                ego_wheelbase=ego_wheelbase,
            )
            is None
        )

    @staticmethod
    def _collision_failure_reason(
        context: DriverAtomContext,
        trajectory: np.ndarray,
        *,
        candidate_obstacles: Optional[np.ndarray] = None,
        ego_length: float = 4.5,
        ego_width: float = 1.9,
        ego_wheelbase: float = 2.925,
    ) -> Optional[str]:
        trajectory = np.asarray(trajectory, dtype=np.float64)
        trajectory_xy = trajectory[:, :2]
        threshold = float(context.safety_radius)
        if context.static_obstacles is not None and len(context.static_obstacles) > 0:
            static_xy = np.asarray(context.static_obstacles, dtype=np.float64)[:, :2]
            distances = np.linalg.norm(
                trajectory_xy[:, np.newaxis, :] - static_xy[np.newaxis, :, :],
                axis=-1,
            )
            if float(distances.min()) < threshold:
                return "static_point_clearance"

        if candidate_obstacles is not None:
            obstacles = np.asarray(candidate_obstacles, dtype=np.float64)
            if obstacles.ndim != 3 or obstacles.shape[-1] < 2:
                raise ValueError(
                    "candidate_obstacles for collision checks must have shape "
                    f"[M, T, D>=2], got {obstacles.shape}."
                )
            if obstacles.shape[-1] >= 5:
                ego_headings = _trajectory_headings(trajectory)
                ego_centers = np.asarray(
                    [
                        _obb_center_and_radius(
                            float(trajectory_xy[t, 0]),
                            float(trajectory_xy[t, 1]),
                            float(ego_headings[t]),
                            float(ego_length),
                            float(ego_width),
                            float(ego_wheelbase),
                        )[0]
                        for t in range(len(trajectory_xy))
                    ],
                    dtype=np.float64,
                )
                _, ego_radius = _obb_center_and_radius(
                    0.0,
                    0.0,
                    0.0,
                    float(ego_length),
                    float(ego_width),
                    float(ego_wheelbase),
                )
                ego_boxes: dict[int, np.ndarray] = {}
                for obstacle in obstacles:
                    horizon = min(len(trajectory_xy), len(obstacle))
                    rows = obstacle[:horizon]
                    valid = np.all(np.isfinite(rows[:, :5]), axis=1)
                    valid &= np.linalg.norm(rows[:, :2], axis=1) >= 1e-8
                    if not valid.any():
                        continue
                    obs_lengths = np.maximum(rows[:, 3], 1e-3)
                    obs_widths = np.maximum(rows[:, 4], 1e-3)
                    if rows.shape[1] >= 6:
                        obs_wheelbases = np.where(
                            np.isfinite(rows[:, 5]) & (rows[:, 5] > 0.0),
                            rows[:, 5],
                            0.0,
                        )
                    else:
                        obs_wheelbases = np.zeros(horizon, dtype=np.float64)
                    obs_centers = rows[:, :2] + np.column_stack(
                        [
                            np.cos(rows[:, 2]),
                            np.sin(rows[:, 2]),
                        ]
                    ) * (obs_wheelbases / 2.0)[:, np.newaxis]
                    obs_radii = np.hypot(obs_lengths / 2.0, obs_widths / 2.0)
                    center_distances = np.linalg.norm(
                        ego_centers[:horizon] - obs_centers,
                        axis=1,
                    )
                    possible = valid & (
                        center_distances <= ego_radius + obs_radii + 1e-12
                    )
                    for t in np.flatnonzero(possible):
                        row = rows[t]
                        obs_wheelbase = (
                            float(obs_wheelbases[t])
                            if obs_wheelbases[t] > 0.0
                            else None
                        )
                        ego_box = ego_boxes.get(int(t))
                        if ego_box is None:
                            ego_box = _obb_corners(
                                float(trajectory_xy[t, 0]),
                                float(trajectory_xy[t, 1]),
                                float(ego_headings[t]),
                                float(ego_length),
                                float(ego_width),
                                float(ego_wheelbase),
                            )
                            ego_boxes[int(t)] = ego_box
                        obs_box = _obb_corners(
                            float(row[0]),
                            float(row[1]),
                            float(row[2]),
                            float(obs_lengths[t]),
                            float(obs_widths[t]),
                            obs_wheelbase,
                        )
                        if _obb_collides(ego_box, obs_box):
                            return "dynamic_obb_collision"
                return None

        if context.dynamic_obstacles:
            for obstacle in context.dynamic_obstacles.values():
                obstacle_xy = np.asarray(obstacle, dtype=np.float64)[:, :2]
                horizon = min(len(trajectory_xy), len(obstacle_xy))
                if horizon == 0:
                    continue
                distances = np.linalg.norm(
                    trajectory_xy[:horizon] - obstacle_xy[:horizon], axis=-1
                )
                if float(distances.min()) < threshold:
                    return "dynamic_point_clearance"
        return None


def _route_centerline(route_lanes: np.ndarray) -> np.ndarray:
    lanes = np.asarray(route_lanes, dtype=np.float64)
    if lanes.ndim == 4 and lanes.shape[0] == 1:
        lanes = lanes[0]
    if lanes.ndim != 3 or lanes.shape[-1] < 4:
        raise ValueError(
            "route_lanes must have shape [N, P, >=4] or [1, N, P, >=4], "
            f"got {lanes.shape}."
        )

    points = []
    for lane in lanes:
        valid = np.sum(np.abs(lane[:, :4]), axis=-1) > 1e-8
        for point in lane[valid, :2]:
            if not points or np.linalg.norm(point - points[-1]) > 1e-4:
                points.append(point.copy())
    if len(points) < 2:
        raise ValueError("route_lanes do not contain a usable centerline.")
    return np.asarray(points, dtype=np.float64)


def _to_ego_frame(points: np.ndarray, ego_xy: np.ndarray, ego_heading: float) -> np.ndarray:
    relative = np.asarray(points, dtype=np.float64) - ego_xy.reshape(1, 2)
    c = math.cos(ego_heading)
    s = math.sin(ego_heading)
    rotation = np.array([[c, s], [-s, c]], dtype=np.float64)
    return relative @ rotation.T


def build_context_from_scene(
    scene: Any,
    ego_agent_id: str,
    *,
    safety_radius: float = 2.0,
    clearance_soft_margin: float = 1.0,
    lane_corridor_buffer: float = 1.0,
) -> DriverAtomContext:
    """Build CAMP atom context from a Diffusion-Planner ``SceneContext``.

    The implementation uses duck typing so CAMP does not import or depend on
    the upstream ``scenario_generation`` package.
    """
    ego = scene.get_agent(ego_agent_id)
    if ego.route_lanes is None:
        raise ValueError(f"Agent {ego_agent_id!r} has no route_lanes.")

    route_world = _route_centerline(ego.route_lanes)
    ego_xy = np.asarray(ego.current_position, dtype=np.float64)
    ego_heading = float(ego.current_heading)
    lane_centerline = _to_ego_frame(route_world, ego_xy, ego_heading)

    route_lanes = np.asarray(ego.route_lanes, dtype=np.float64)
    if route_lanes.ndim == 4 and route_lanes.shape[0] == 1:
        route_lanes = route_lanes[0]
    boundary_norms = []
    if route_lanes.shape[-1] >= 8:
        for boundary_slice in (slice(4, 6), slice(6, 8)):
            offsets = route_lanes[..., boundary_slice]
            norms = np.linalg.norm(offsets, axis=-1)
            valid = norms > 0.2
            if valid.any():
                boundary_norms.extend(norms[valid].tolist())
    lane_half_width = float(np.median(boundary_norms)) if boundary_norms else 1.8

    speed_limit = None
    if ego.route_speed_limit is not None:
        limits = np.asarray(ego.route_speed_limit, dtype=np.float64).reshape(-1)
        if ego.route_has_speed_limit is not None:
            has_limit = np.asarray(ego.route_has_speed_limit, dtype=bool).reshape(-1)
            valid_limits = limits[has_limit[: limits.shape[0]]]
        else:
            valid_limits = limits[limits > 0]
        valid_limits = valid_limits[np.isfinite(valid_limits) & (valid_limits > 0)]
        if valid_limits.size:
            speed_limit = float(valid_limits[0])

    desired_speed = float(np.linalg.norm(np.asarray(ego.current_velocity, dtype=np.float64)))

    static_obstacles = []
    map_static = getattr(scene.map_data, "static_objects", None)
    if map_static is not None:
        static = np.asarray(map_static, dtype=np.float64)
        if static.ndim == 2 and static.shape[1] >= 2:
            valid = np.sum(np.abs(static[:, :2]), axis=-1) > 1e-8
            if valid.any():
                static_obstacles.extend(
                    _to_ego_frame(static[valid, :2], ego_xy, ego_heading).tolist()
                )

    return DriverAtomContext(
        dt=float(getattr(scene, "dt", 0.1)),
        lane_centerline=lane_centerline,
        static_obstacles=(
            np.asarray(static_obstacles, dtype=np.float64)
            if static_obstacles
            else None
        ),
        dynamic_obstacles=None,
        speed_limit=speed_limit,
        desired_speed=desired_speed,
        lane_half_width=lane_half_width,
        lane_corridor_buffer=lane_corridor_buffer,
        safety_radius=safety_radius,
        clearance_soft_margin=clearance_soft_margin,
        map_source="diffusion_planner_route",
    )


def generate_candidate_trajectories(
    model: Any,
    model_args: Any,
    normalized_inputs: dict[str, Any],
    *,
    num_candidates: int,
    noise_scale: float,
    deterministic_first: bool = True,
) -> tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    """Generate K Diffusion-Planner candidates in one batched forward pass.

    Returns ego candidates ``[K,T,4]``, predicted neighbor trajectories
    ``[K,Pn,T,4]``, and optional turn-indicator logits ``[K,C]``.
    """
    if num_candidates < 1:
        raise ValueError("num_candidates must be >= 1.")
    if noise_scale < 0:
        raise ValueError("noise_scale must be non-negative.")

    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "Diffusion-Planner candidate generation requires torch."
        ) from exc

    expanded: dict[str, Any] = {}
    for key, value in normalized_inputs.items():
        if isinstance(value, torch.Tensor):
            if value.shape[0] != 1:
                raise ValueError(
                    f"Expected batch size 1 for {key}, got {value.shape[0]}."
                )
            expanded[key] = value.expand(
                num_candidates, *value.shape[1:]
            ).contiguous()
        else:
            expanded[key] = value

    device = expanded["ego_current_state"].device
    num_agents = 1 + int(model_args.predicted_neighbor_num)
    future_len = int(model_args.future_len)
    latent = torch.randn(
        num_candidates,
        num_agents,
        future_len + 1,
        4,
        device=device,
        dtype=expanded["ego_current_state"].dtype,
    ) * float(noise_scale)
    if deterministic_first:
        latent[0].zero_()
    expanded["sampled_trajectories"] = latent

    decoder = model.decoder
    original_guidance = getattr(decoder, "_guidance_fn", None)
    decoder._guidance_fn = None
    try:
        with torch.no_grad():
            _, outputs = model(expanded)
    finally:
        decoder._guidance_fn = original_guidance

    predictions = outputs["prediction"].detach().cpu().numpy()
    turn_logits = outputs.get("turn_indicator_logit")
    if turn_logits is not None:
        turn_logits = turn_logits.detach().cpu().numpy()
    return predictions[:, 0], predictions[:, 1:], turn_logits
