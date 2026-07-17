from __future__ import annotations

import hashlib
import importlib
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
    exact_centerline_slice_for_candidates,
)
from camp_core.integrations.diffusion_planner_candidate_set_consensus_payload import (
    CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS,
    CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
    build_candidate_set_consensus_payload,
)
from camp_core.integrations.diffusion_planner_progress_support import (
    PROGRESS_SUPPORT_LATENCY_KEYS,
    PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
    build_progress_support_logging_payload,
)
from camp_core.integrations.diffusion_planner_v25_context import (
    CONTEXT_SCHEMA_VERSION as V25_CONTEXT_SCHEMA_VERSION,
    PHI_DIMENSION as V25_PHI_DIMENSION,
    RAW_FEATURE_NAMES as V25_RAW_FEATURE_NAMES,
    V25ContextScaler,
    context_weights as v25_context_weights,
    validate_column_simplex_theta,
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


def inspect_lanelet2_extended_regulatory_elements(
    map_path: Union[str, Path],
) -> dict[str, Any]:
    """Census Autoware-only regulatory elements without changing the map."""
    source = Path(map_path)
    payload = source.read_bytes()
    root = ET.fromstring(payload)
    regulatory: dict[str, str] = {}
    subtype_counts: dict[str, int] = {}
    for relation in root.findall("relation"):
        tags = {
            tag.attrib.get("k"): tag.attrib.get("v")
            for tag in relation.findall("tag")
        }
        if tags.get("type") != "regulatory_element":
            continue
        subtype = tags.get("subtype", "")
        regulatory[relation.attrib["id"]] = subtype
        subtype_counts[subtype] = subtype_counts.get(subtype, 0) + 1

    extended = {
        relation_id: subtype
        for relation_id, subtype in regulatory.items()
        if subtype in AUTOWARE_UNSUPPORTED_REGULATORY_SUBTYPES
    }
    extended_counts: dict[str, int] = {}
    for subtype in extended.values():
        extended_counts[subtype] = extended_counts.get(subtype, 0) + 1
    lanelet_reference_counts: dict[str, int] = {}
    for relation in root.findall("relation"):
        tags = {
            tag.attrib.get("k"): tag.attrib.get("v")
            for tag in relation.findall("tag")
        }
        if tags.get("type") != "lanelet":
            continue
        for member in relation.findall("member"):
            if member.attrib.get("type") != "relation":
                continue
            subtype = extended.get(member.attrib.get("ref", ""))
            if subtype is not None:
                lanelet_reference_counts[subtype] = (
                    lanelet_reference_counts.get(subtype, 0) + 1
                )

    return {
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "regulatory_relation_count": len(regulatory),
        "regulatory_subtype_counts": dict(sorted(subtype_counts.items())),
        "extended_relation_ids": sorted(extended),
        "extended_subtype_counts": dict(sorted(extended_counts.items())),
        "extended_lanelet_reference_counts": dict(
            sorted(lanelet_reference_counts.items())
        ),
    }


def require_source_preserving_lanelet2_regulatory_adapter(
    map_path: Union[str, Path],
) -> dict[str, Any]:
    """Require the official extension when original map semantics need it.

    Python Lanelet2 exposes no regulatory-element factory hook. This gate must
    therefore run before the no-ROS projection fallback can create a similarly
    named process-local module. The later unmodified-map loader smoke is the
    proof that the installed official extension actually registered its C++
    regulatory elements.
    """
    source = Path(map_path)
    census = inspect_lanelet2_extended_regulatory_elements(source)
    required = sorted(census["extended_subtype_counts"])
    before = census["source_sha256"]
    if not required:
        return {
            "mode": "stock_lanelet2",
            "required_extended_subtypes": [],
            "official_module": None,
            "source_sha256_before": before,
            "source_sha256_after": hashlib.sha256(source.read_bytes()).hexdigest(),
            "census": census,
        }

    try:
        projection = importlib.import_module(
            "autoware_lanelet2_extension_python.projection"
        )
    except ImportError as exc:
        raise RuntimeError(
            "The original map requires the official Autoware Lanelet2 "
            f"extension for {required}; no source-preserving regulatory "
            "adapter is installed."
        ) from exc
    origin = getattr(projection, "__file__", None)
    if not origin:
        raise RuntimeError(
            "A process-local projection fallback cannot register the original "
            f"map's regulatory elements {required}."
        )
    if not hasattr(projection, "MGRSProjector"):
        raise RuntimeError(
            "The installed official Autoware Lanelet2 extension has no "
            "MGRSProjector entry point."
        )
    after = hashlib.sha256(source.read_bytes()).hexdigest()
    if after != before:
        raise RuntimeError("Lanelet2 regulatory adapter changed source map bytes.")
    return {
        "mode": "official_autoware_lanelet2_extension",
        "required_extended_subtypes": required,
        "official_module": str(origin),
        "source_sha256_before": before,
        "source_sha256_after": after,
        "census": census,
    }


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


def _strict_normalized_simplex_weights(
    weights: np.ndarray,
    num_atoms: int,
    *,
    label: str = "CAMP weights",
) -> np.ndarray:
    weights = np.asarray(weights, dtype=np.float64).reshape(-1)
    if weights.shape != (num_atoms,):
        raise ValueError(
            f"Expected {num_atoms} {label}, got shape {weights.shape}."
        )
    if not np.all(np.isfinite(weights)):
        raise ValueError(f"{label} must contain only finite values.")
    if np.any(weights < 0.0):
        raise ValueError(f"{label} must contain only nonnegative values.")
    with np.errstate(over="ignore", invalid="ignore"):
        total = float(np.sum(weights, dtype=np.float64))
    if not np.isfinite(total) or total <= 0.0:
        raise ValueError(f"{label} must have a finite positive total mass.")
    normalized = weights / total
    normalized_total = float(np.sum(normalized, dtype=np.float64))
    if (
        not np.all(np.isfinite(normalized))
        or np.any(normalized < 0.0)
        or not np.isfinite(normalized_total)
        or not np.isclose(normalized_total, 1.0, rtol=0.0, atol=1e-12)
    ):
        raise ValueError(f"{label} could not be normalized to a finite simplex.")
    return normalized


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


def _summarize_trajectory_log(
    records: list[dict[str, Any]], *, dt: float = 0.1
) -> dict[str, Any]:
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("dt must be finite and positive")
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
    accel = np.diff(speeds) / dt if speeds.size >= 2 else np.asarray([])
    jerk = np.diff(accel) / dt if accel.size >= 2 else np.asarray([])
    acceleration_magnitude = np.asarray([])
    jerk_magnitude = np.asarray([])
    yaw_rate = np.asarray([])
    lateral_acceleration = np.asarray([])
    if speeds.size == headings.size and speeds.size >= 2:
        velocity = np.column_stack(
            [speeds * np.cos(headings), speeds * np.sin(headings)]
        )
        acceleration_vectors = np.diff(velocity, axis=0) / dt
        acceleration_magnitude = np.linalg.norm(acceleration_vectors, axis=1)
        if acceleration_vectors.shape[0] >= 2:
            jerk_vectors = np.diff(acceleration_vectors, axis=0) / dt
            jerk_magnitude = np.linalg.norm(jerk_vectors, axis=1)
        heading_delta = np.arctan2(
            np.sin(np.diff(headings)),
            np.cos(np.diff(headings)),
        )
        yaw_rate = heading_delta / dt
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


def _postprocess_perfect_tracker_reference_candidates(
    candidates: np.ndarray,
    *,
    dt: float,
    velocity_smooth_window: int,
    stop_threshold_mps: float,
) -> np.ndarray:
    """Vectorize DP's PerfectTracker reference postprocessing over candidates."""
    trajectories = np.asarray(candidates, dtype=np.float64)
    candidate_count, horizon_steps = trajectories.shape[:2]
    headings = np.arctan2(trajectories[:, :, 3], trajectories[:, :, 2])
    references = np.concatenate(
        [trajectories[:, :, :2], headings[:, :, np.newaxis]],
        axis=2,
    )
    if horizon_steps < 2:
        return references

    differences = np.diff(trajectories[:, :, :2], axis=1)
    velocities = np.linalg.norm(differences, axis=2) / float(dt)
    velocities = np.concatenate([velocities[:, :1], velocities], axis=1)
    smoothed = velocities.copy()
    window = int(velocity_smooth_window)
    if horizon_steps >= window:
        cumulative = np.pad(
            np.cumsum(velocities, axis=1),
            ((0, 0), (1, 0)),
        )
        smoothed[:, : horizon_steps - window + 1] = (
            cumulative[:, window:] - cumulative[:, :-window]
        ) / window

    crossings = (
        (smoothed[:, :-1] > float(stop_threshold_mps))
        & (smoothed[:, 1:] <= float(stop_threshold_mps))
    )
    for candidate_index in range(candidate_count):
        crossing_steps = np.flatnonzero(crossings[candidate_index])
        if crossing_steps.size:
            stop_step = int(crossing_steps[0]) + 1
            references[candidate_index, stop_step:] = references[
                candidate_index,
                stop_step - 1,
            ]
    return references


def compute_perfect_tracker_open_loop_rollout_diagnostics(
    reference_prefix: np.ndarray,
    *,
    postprocessed_tail_reference_xy: np.ndarray,
    full_horizon_steps: int,
    dt: float,
    current_speed_mps: float,
    current_acceleration_ego_xy: np.ndarray,
    horizons: Sequence[int] = (3, 5, 10),
    max_speed_mps: float = 20.0,
    restart_speed_threshold_mps: float = 0.1,
    restart_plan_speed_threshold_mps: float = 0.5,
) -> dict[str, Any]:
    """Roll out a fixed reference through PerfectTracker without replanning.

    This is an outcome-free open-loop proxy. It intentionally does not claim
    to reproduce the future candidate pools or state transitions produced by
    closed-loop Diffusion Planner replanning.
    """
    references = np.asarray(reference_prefix, dtype=np.float64)
    tails = np.asarray(postprocessed_tail_reference_xy, dtype=np.float64)
    acceleration0 = np.asarray(
        current_acceleration_ego_xy,
        dtype=np.float64,
    ).reshape(-1)
    if (
        references.ndim != 3
        or references.shape[0] < 1
        or references.shape[1] < 1
        or references.shape[2] != 3
    ):
        raise ValueError("reference_prefix must have shape [K, H, 3].")
    if not np.all(np.isfinite(references)):
        raise ValueError("reference_prefix must contain only finite values.")
    if tails.shape != (references.shape[0], 2) or not np.all(np.isfinite(tails)):
        raise ValueError(
            "postprocessed_tail_reference_xy must have shape [K, 2] "
            "with finite values."
        )
    if acceleration0.shape != (2,) or not np.all(np.isfinite(acceleration0)):
        raise ValueError(
            "current_acceleration_ego_xy must contain two finite values."
        )
    scalar_values = (
        dt,
        current_speed_mps,
        max_speed_mps,
        restart_speed_threshold_mps,
        restart_plan_speed_threshold_mps,
    )
    if any(not np.isfinite(float(value)) for value in scalar_values):
        raise ValueError("PerfectTracker rollout inputs must be finite.")
    if dt <= 0.0:
        raise ValueError("dt must be positive.")
    if current_speed_mps < 0.0:
        raise ValueError("current_speed_mps must be nonnegative.")
    if max_speed_mps <= 0.0:
        raise ValueError("max_speed_mps must be positive.")
    if (
        restart_speed_threshold_mps < 0.0
        or restart_plan_speed_threshold_mps < 0.0
    ):
        raise ValueError("PerfectTracker restart thresholds must be nonnegative.")
    if (
        isinstance(full_horizon_steps, bool)
        or not isinstance(full_horizon_steps, (int, np.integer))
        or int(full_horizon_steps) < references.shape[1]
    ):
        raise ValueError(
            "full_horizon_steps must be an integer no smaller than the "
            "reference prefix."
        )

    normalized_horizons = tuple(int(value) for value in horizons)
    if (
        not normalized_horizons
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, np.integer))
            or int(value) < 1
            for value in horizons
        )
        or tuple(sorted(set(normalized_horizons))) != normalized_horizons
        or normalized_horizons[-1] > references.shape[1]
    ):
        raise ValueError(
            "horizons must be unique increasing positive integers within "
            "the reference prefix."
        )

    candidate_count = references.shape[0]
    rollout_steps = normalized_horizons[-1]
    target_speeds = np.zeros((candidate_count, rollout_steps), dtype=np.float64)
    restart_pushes = np.zeros((candidate_count, rollout_steps), dtype=bool)
    vector_jerks = np.zeros((candidate_count, rollout_steps), dtype=np.float64)
    lateral_accelerations = np.zeros(
        (candidate_count, rollout_steps),
        dtype=np.float64,
    )
    distance_increments = np.zeros(
        (candidate_count, rollout_steps),
        dtype=np.float64,
    )

    for candidate_index in range(candidate_count):
        position = np.zeros(2, dtype=np.float64)
        heading = 0.0
        speed = float(current_speed_mps)
        velocity = np.array([speed, 0.0], dtype=np.float64)
        previous_acceleration = acceleration0.copy()
        tail_xy = tails[candidate_index]
        for step in range(rollout_steps):
            target_xy = references[candidate_index, step, :2]
            target_heading = float(references[candidate_index, step, 2])
            target_speed = min(
                float(np.linalg.norm(target_xy - position)) / float(dt),
                float(max_speed_mps),
            )
            remaining_steps = int(full_horizon_steps) - step
            tail_average_speed = (
                float(np.linalg.norm(tail_xy - position))
                / (remaining_steps * float(dt))
            )
            restart_push = (
                speed < float(restart_speed_threshold_mps)
                and tail_average_speed > float(restart_plan_speed_threshold_mps)
            )
            if restart_push:
                target_speed = max(
                    target_speed,
                    min(float(max_speed_mps), tail_average_speed),
                )

            heading_delta = math.atan2(
                math.sin(target_heading - heading),
                math.cos(target_heading - heading),
            )
            position = position + target_speed * np.array(
                [math.cos(heading), math.sin(heading)],
                dtype=np.float64,
            ) * float(dt)
            new_velocity = target_speed * np.array(
                [math.cos(target_heading), math.sin(target_heading)],
                dtype=np.float64,
            )
            acceleration = (new_velocity - velocity) / float(dt)
            vector_jerk = float(
                np.linalg.norm(acceleration - previous_acceleration) / float(dt)
            )

            target_speeds[candidate_index, step] = target_speed
            restart_pushes[candidate_index, step] = restart_push
            vector_jerks[candidate_index, step] = vector_jerk
            lateral_accelerations[candidate_index, step] = (
                abs(target_speed * heading_delta / float(dt))
            )
            distance_increments[candidate_index, step] = target_speed * float(dt)

            heading = target_heading
            speed = target_speed
            velocity = new_velocity
            previous_acceleration = acceleration

    horizon_metrics = {}
    for horizon in normalized_horizons:
        horizon_metrics[str(horizon)] = {
            "distance_m": np.sum(distance_increments[:, :horizon], axis=1),
            "mean_vector_jerk_mps3": np.mean(
                vector_jerks[:, :horizon],
                axis=1,
            ),
            "max_vector_jerk_mps3": np.max(
                vector_jerks[:, :horizon],
                axis=1,
            ),
            "mean_lateral_acceleration_mps2": np.mean(
                lateral_accelerations[:, :horizon],
                axis=1,
            ),
            "max_lateral_acceleration_mps2": np.max(
                lateral_accelerations[:, :horizon],
                axis=1,
            ),
        }
    return {
        "horizons": horizon_metrics,
        "target_speed_mps": target_speeds,
        "restart_push": restart_pushes,
    }


def compute_perfect_tracker_command_diagnostics(
    candidates: np.ndarray,
    *,
    dt: float,
    current_speed_mps: float,
    current_longitudinal_acceleration_mps2: float,
    max_speed_mps: float = 20.0,
    velocity_smooth_window: int = 8,
    stop_threshold_mps: float = 0.3,
    restart_speed_threshold_mps: float = 0.1,
    restart_plan_speed_threshold_mps: float = 0.5,
) -> dict[str, np.ndarray]:
    """Reproduce the command issued by DP's perfect tracker for each candidate.

    Candidate trajectories are in the current ego frame. Rigid transforms do
    not change the displacement norms used by ``postprocess_reference`` and
    ``PerfectTracker.track``; the first relative heading is exactly the wrapped
    world-frame heading change used by the tracker.

    These values are fixed candidate diagnostics. They are not CAMP atoms and
    do not affect candidate feasibility, scores, or selection.
    """
    trajectories = np.asarray(candidates, dtype=np.float64)
    if (
        trajectories.ndim != 3
        or trajectories.shape[0] < 1
        or trajectories.shape[1] < 1
        or trajectories.shape[2] < 4
    ):
        raise ValueError("candidates must have shape [K, T, D>=4].")
    if not np.all(np.isfinite(trajectories)):
        raise ValueError("candidates must contain only finite values.")
    scalar_values = {
        "dt": dt,
        "current_speed_mps": current_speed_mps,
        "current_longitudinal_acceleration_mps2": (
            current_longitudinal_acceleration_mps2
        ),
        "max_speed_mps": max_speed_mps,
        "stop_threshold_mps": stop_threshold_mps,
        "restart_speed_threshold_mps": restart_speed_threshold_mps,
        "restart_plan_speed_threshold_mps": (
            restart_plan_speed_threshold_mps
        ),
    }
    if any(not np.isfinite(float(value)) for value in scalar_values.values()):
        raise ValueError("Perfect-tracker diagnostic inputs must be finite.")
    if dt <= 0.0:
        raise ValueError("dt must be positive.")
    if current_speed_mps < 0.0:
        raise ValueError("current_speed_mps must be nonnegative.")
    if max_speed_mps <= 0.0:
        raise ValueError("max_speed_mps must be positive.")
    if (
        stop_threshold_mps < 0.0
        or restart_speed_threshold_mps < 0.0
        or restart_plan_speed_threshold_mps < 0.0
    ):
        raise ValueError("Perfect-tracker thresholds must be nonnegative.")
    if (
        isinstance(velocity_smooth_window, bool)
        or not isinstance(velocity_smooth_window, (int, np.integer))
        or int(velocity_smooth_window) < 1
    ):
        raise ValueError("velocity_smooth_window must be a positive integer.")

    candidate_count, horizon_steps = trajectories.shape[:2]
    postprocessed_references = _postprocess_perfect_tracker_reference_candidates(
        trajectories,
        dt=float(dt),
        velocity_smooth_window=int(velocity_smooth_window),
        stop_threshold_mps=float(stop_threshold_mps),
    )
    postprocessed_tail_xy = postprocessed_references[:, -1, :2]

    first_reference_xy = trajectories[:, 0, :2]
    first_step_reach_m = np.linalg.norm(first_reference_xy, axis=1)
    first_target_speed_mps = np.minimum(
        first_step_reach_m / float(dt),
        float(max_speed_mps),
    )
    tail_reach_m = np.linalg.norm(postprocessed_tail_xy, axis=1)
    tail_average_speed_mps = tail_reach_m / (horizon_steps * float(dt))
    restart_push = (
        float(current_speed_mps) < float(restart_speed_threshold_mps)
    ) & (
        tail_average_speed_mps > float(restart_plan_speed_threshold_mps)
    )
    target_speed_mps = first_target_speed_mps.copy()
    target_speed_mps[restart_push] = np.maximum(
        target_speed_mps[restart_push],
        np.minimum(
            float(max_speed_mps),
            tail_average_speed_mps[restart_push],
        ),
    )

    acceleration_mps2 = (
        target_speed_mps - float(current_speed_mps)
    ) / float(dt)
    jerk_magnitude_mps3 = np.abs(
        acceleration_mps2 - float(current_longitudinal_acceleration_mps2)
    ) / float(dt)
    first_heading_rad = np.arctan2(
        trajectories[:, 0, 3],
        trajectories[:, 0, 2],
    )
    wrapped_first_heading_rad = np.arctan2(
        np.sin(first_heading_rad),
        np.cos(first_heading_rad),
    )
    yaw_rate_magnitude_rps = np.abs(wrapped_first_heading_rad) / float(dt)
    lateral_acceleration_magnitude_mps2 = (
        target_speed_mps * yaw_rate_magnitude_rps
    )

    return {
        "first_reference_xy": first_reference_xy.copy(),
        "first_reference_heading_rad": first_heading_rad,
        "postprocessed_tail_reference_xy": postprocessed_tail_xy,
        "postprocessed_reference": postprocessed_references,
        "first_step_reach_m": first_step_reach_m,
        "tail_average_speed_mps": tail_average_speed_mps,
        "restart_push": restart_push,
        "target_speed_mps": target_speed_mps,
        "acceleration_mps2": acceleration_mps2,
        "jerk_magnitude_mps3": jerk_magnitude_mps3,
        "yaw_rate_magnitude_rps": yaw_rate_magnitude_rps,
        "lateral_acceleration_magnitude_mps2": (
            lateral_acceleration_magnitude_mps2
        ),
    }


def select_perfect_tracker_command_dominating_candidate(
    *,
    baseline_selected_index: int,
    feasible_mask: np.ndarray,
    selection_scores: np.ndarray,
    candidate_progress: np.ndarray,
    candidate_planned_red_light_cost: np.ndarray,
    candidate_target_speed_mps: np.ndarray,
    candidate_jerk_magnitude_mps3: np.ndarray,
    candidate_lateral_acceleration_magnitude_mps2: np.ndarray,
) -> tuple[int, dict[str, int | bool]]:
    """Choose a command-dominating candidate without shrinking feasibility.

    The baseline CAMP selection is always retained in the weakly dominating
    set. A different candidate is considered only when it is base-feasible,
    preserves DP progress and planned-red cost, preserves PerfectTracker target
    speed, and does not worsen command jerk or lateral acceleration. At least
    one command-comfort quantity must improve strictly.
    """
    feasible = np.asarray(feasible_mask, dtype=bool).reshape(-1)
    candidate_count = feasible.size
    if candidate_count == 0:
        raise ValueError("PerfectTracker postselection requires candidates.")
    if (
        isinstance(baseline_selected_index, bool)
        or not isinstance(baseline_selected_index, (int, np.integer))
        or not 0 <= int(baseline_selected_index) < candidate_count
    ):
        raise ValueError("baseline_selected_index is invalid.")
    baseline = int(baseline_selected_index)
    arrays = {
        "selection_scores": np.asarray(
            selection_scores, dtype=np.float64
        ).reshape(-1),
        "progress": np.asarray(
            candidate_progress, dtype=np.float64
        ).reshape(-1),
        "planned_red": np.asarray(
            candidate_planned_red_light_cost, dtype=np.float64
        ).reshape(-1),
        "target_speed": np.asarray(
            candidate_target_speed_mps, dtype=np.float64
        ).reshape(-1),
        "jerk": np.asarray(
            candidate_jerk_magnitude_mps3, dtype=np.float64
        ).reshape(-1),
        "lateral": np.asarray(
            candidate_lateral_acceleration_magnitude_mps2,
            dtype=np.float64,
        ).reshape(-1),
    }
    if any(values.shape != (candidate_count,) for values in arrays.values()):
        raise ValueError(
            "PerfectTracker postselection fields must match candidate count."
        )
    for name in ("progress", "planned_red", "target_speed", "jerk", "lateral"):
        if not np.all(np.isfinite(arrays[name])):
            raise ValueError(
                f"PerfectTracker postselection {name} values must be finite."
            )
    for name in ("planned_red", "target_speed", "jerk", "lateral"):
        if np.any(arrays[name] < 0.0):
            raise ValueError(
                f"PerfectTracker postselection {name} values must be nonnegative."
            )

    base_feasible_count = int(feasible.sum())
    empty_stats: dict[str, int | bool] = {
        "base_feasible_count": base_feasible_count,
        "admissible_count": 0,
        "weakly_dominating_count": 0,
        "strict_improvement_count": 0,
        "baseline_selected_index": baseline,
        "selected_index": baseline,
        "changed": False,
    }
    if not feasible.any():
        return baseline, empty_stats
    if not feasible[baseline]:
        raise ValueError(
            "Baseline CAMP selection must be feasible outside fallback."
        )
    if not np.all(np.isfinite(arrays["selection_scores"][feasible])):
        raise ValueError(
            "PerfectTracker postselection scores must be finite for "
            "feasible candidates."
        )

    admissible = feasible.copy()
    admissible &= arrays["target_speed"] >= arrays["target_speed"][baseline] - 1e-12
    admissible &= arrays["progress"] >= arrays["progress"][baseline] - 1e-12
    admissible &= arrays["planned_red"] <= arrays["planned_red"][baseline] + 1e-12
    weakly_dominating = admissible.copy()
    weakly_dominating &= arrays["jerk"] <= arrays["jerk"][baseline] + 1e-12
    weakly_dominating &= arrays["lateral"] <= arrays["lateral"][baseline] + 1e-12
    strict_improvement = weakly_dominating & (
        (arrays["jerk"] < arrays["jerk"][baseline] - 1e-12)
        | (arrays["lateral"] < arrays["lateral"][baseline] - 1e-12)
    )
    if not weakly_dominating[baseline]:
        raise RuntimeError(
            "PerfectTracker postselection unexpectedly removed the baseline."
        )

    selected = baseline
    if strict_improvement.any():
        indices = np.flatnonzero(weakly_dominating)
        order = np.lexsort(
            (
                indices,
                arrays["selection_scores"][indices],
                arrays["lateral"][indices],
                arrays["jerk"][indices],
            )
        )
        selected = int(indices[order[0]])
    stats = {
        "base_feasible_count": base_feasible_count,
        "admissible_count": int(admissible.sum()),
        "weakly_dominating_count": int(weakly_dominating.sum()),
        "strict_improvement_count": int(strict_improvement.sum()),
        "baseline_selected_index": baseline,
        "selected_index": selected,
        "changed": selected != baseline,
    }
    return selected, stats


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


def _obb_centers_and_radii(
    xy: np.ndarray,
    headings: np.ndarray,
    lengths: np.ndarray,
    widths: np.ndarray,
    wheelbases: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    xy_values = np.asarray(xy, dtype=np.float64)
    heading_values = np.asarray(headings, dtype=np.float64).reshape(-1)
    length_values = np.asarray(lengths, dtype=np.float64).reshape(-1)
    width_values = np.asarray(widths, dtype=np.float64).reshape(-1)
    if xy_values.shape != (heading_values.size, 2):
        raise ValueError("xy must have shape [N,2].")
    if (
        length_values.shape != heading_values.shape
        or width_values.shape != heading_values.shape
    ):
        raise ValueError("lengths and widths must match headings.")
    if wheelbases is None:
        offsets = np.zeros_like(heading_values)
    else:
        wheelbase_values = np.asarray(wheelbases, dtype=np.float64).reshape(-1)
        if wheelbase_values.shape != heading_values.shape:
            raise ValueError("wheelbases must match headings.")
        offsets = np.where(
            np.isfinite(wheelbase_values) & (wheelbase_values > 0.0),
            wheelbase_values / 2.0,
            0.0,
        )
    directions = np.column_stack((np.cos(heading_values), np.sin(heading_values)))
    centers = xy_values + offsets[:, np.newaxis] * directions
    radii = np.hypot(length_values / 2.0, width_values / 2.0)
    return centers, radii


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


def compute_lateral_comfort_shadow_costs(
    candidates: np.ndarray,
    dt: float,
    *,
    horizon_steps: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return horizon-aligned lateral acceleration and yaw-rate diagnostics.

    The absolute costs are computed only from the current candidate
    trajectories. The relative costs clip each candidate's excess over
    deterministic candidate 0 to zero. These values are fixed before CAMP
    selection and remain shadow-only until dataset evidence justifies a schema
    change.
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

    candidate_count = trajectories.shape[0]
    lateral_acceleration = np.asarray(
        [
            _trajectory_comfort(trajectory, float(dt))[1]
            for trajectory in trajectories
        ],
        dtype=np.float64,
    )
    mean_abs_yaw_rate = np.zeros(candidate_count, dtype=np.float64)
    if trajectories.shape[1] >= 2:
        for candidate_idx, trajectory in enumerate(trajectories):
            headings = np.unwrap(_trajectory_headings(trajectory))
            yaw_rate = np.diff(headings) / float(dt)
            if yaw_rate.size:
                mean_abs_yaw_rate[candidate_idx] = float(
                    np.mean(np.abs(yaw_rate))
                )

    lateral_excess = np.maximum(
        lateral_acceleration - float(lateral_acceleration[0]),
        0.0,
    )
    yaw_rate_excess = np.maximum(
        mean_abs_yaw_rate - float(mean_abs_yaw_rate[0]),
        0.0,
    )
    diagnostics = (
        lateral_acceleration,
        lateral_excess,
        mean_abs_yaw_rate,
        yaw_rate_excess,
    )
    if any(
        not np.all(np.isfinite(values)) or np.any(values < 0.0)
        for values in diagnostics
    ):
        raise RuntimeError(
            "Lateral comfort shadow costs must be finite and nonnegative."
        )
    return diagnostics


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
        raise ValueError(
            f"candidates must have shape [K,T,>=2], got {trajectories.shape}."
        )
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
                            if (
                                row.shape[0] >= 6
                                and np.isfinite(row[5])
                                and row[5] > 0
                            )
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


def compute_candidate_obstacle_clearance_diagnostics(
    candidates: np.ndarray,
    context: DriverAtomContext,
    *,
    candidate_obstacles: Optional[np.ndarray] = None,
    horizon_steps: int = 30,
    soft_clearance_threshold_m: Optional[float] = None,
    near_miss_threshold_m: float = 2.0,
    evaluate_exact_obb: bool = True,
    ego_length: float = 4.5,
    ego_width: float = 1.9,
    ego_wheelbase: float = 2.925,
) -> dict[str, Any]:
    """Current-tick candidate obstacle-clearance diagnostics.

    This uses the fixed candidate trajectories and fixed obstacle predictions
    available at the current planning tick. It is a shadow descriptor for
    offline audits, not a realized closed-loop outcome label. Dynamic obstacle
    OBB checks use a bounding-circle lower bound for the hinge costs. Optional
    exact OBB distance is diagnostic only and does not change the hinge costs.
    """
    trajectories = np.asarray(candidates, dtype=np.float64)
    if trajectories.ndim != 3 or trajectories.shape[2] < 2:
        raise ValueError(f"candidates must have shape [K,T,>=2], got {trajectories.shape}.")
    horizon = min(max(int(horizon_steps), 2), trajectories.shape[1])
    soft_threshold = (
        float(context.safety_radius) + float(context.clearance_soft_margin)
        if soft_clearance_threshold_m is None
        else float(soft_clearance_threshold_m)
    )
    if not np.isfinite(soft_threshold) or soft_threshold < 0.0:
        raise ValueError("soft_clearance_threshold_m must be finite and nonnegative.")
    near_miss_threshold = float(near_miss_threshold_m)
    if not np.isfinite(near_miss_threshold) or near_miss_threshold < 0.0:
        raise ValueError("near_miss_threshold_m must be finite and nonnegative.")
    exact_trigger = max(soft_threshold, near_miss_threshold)

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
        if obstacles.shape[-1] < 2:
            raise ValueError("Obstacle trajectories need at least x/y coordinates.")

    min_clearance_lower_bounds: list[float | None] = []
    exact_obb_min_clearances: list[float | None] = []
    exact_obb_evaluated_pairs: list[int] = []
    soft_violations: list[float] = []
    near_miss_violations: list[float] = []
    obstacle_slots: list[int] = []
    geometry_modes: list[str] = []

    for candidate_idx, candidate in enumerate(trajectories):
        branch = candidate[:horizon]
        headings = _trajectory_headings(branch)
        min_lower_bound = float("inf")
        exact_obb_min_clearance = float("inf")
        exact_obb_pairs = 0
        slots = 0
        used_obb = False

        if context.static_obstacles is not None and len(context.static_obstacles) > 0:
            static_xy = np.asarray(context.static_obstacles, dtype=np.float64)[:, :2]
            distances = np.linalg.norm(
                branch[:, np.newaxis, :2] - static_xy[np.newaxis, :, :],
                axis=-1,
            )
            if distances.size:
                slots += int(static_xy.shape[0])
                min_lower_bound = min(min_lower_bound, float(np.min(distances)))

        if obstacles is not None:
            candidate_obstacle = obstacles[candidate_idx]
            obstacle_horizon = min(horizon, candidate_obstacle.shape[1])
            rows = candidate_obstacle[:, :obstacle_horizon]
            valid = np.all(np.isfinite(rows[:, :, :2]), axis=2)
            valid &= np.linalg.norm(rows[:, :, :2], axis=2) >= 1e-8
            if valid.any():
                slots += int(np.count_nonzero(valid.any(axis=1)))
                if rows.shape[2] >= 5:
                    obb_valid = valid & np.all(np.isfinite(rows[:, :, :5]), axis=2)
                else:
                    obb_valid = np.zeros_like(valid, dtype=bool)
                if obb_valid.any():
                    obstacle_indices, step_indices = np.nonzero(obb_valid)
                    obb_rows = rows[obstacle_indices, step_indices]
                    obs_lengths = np.maximum(obb_rows[:, 3], 1e-3)
                    obs_widths = np.maximum(obb_rows[:, 4], 1e-3)
                    obs_wheelbases = (
                        obb_rows[:, 5]
                        if rows.shape[2] >= 6
                        else np.full(obb_rows.shape[0], np.nan)
                    )
                    ego_centers, ego_radii = _obb_centers_and_radii(
                        branch[step_indices, :2],
                        headings[step_indices],
                        np.full(step_indices.size, float(ego_length)),
                        np.full(step_indices.size, float(ego_width)),
                        np.full(step_indices.size, float(ego_wheelbase)),
                    )
                    obs_centers, obs_radii = _obb_centers_and_radii(
                        obb_rows[:, :2],
                        obb_rows[:, 2],
                        obs_lengths,
                        obs_widths,
                        obs_wheelbases,
                    )
                    clearances = np.maximum(
                        0.0,
                        np.linalg.norm(ego_centers - obs_centers, axis=1)
                        - ego_radii
                        - obs_radii,
                    )
                    if clearances.size:
                        min_lower_bound = min(
                            min_lower_bound,
                            float(np.min(clearances)),
                        )
                    used_obb = True
                    if evaluate_exact_obb:
                        for row, step_idx, clearance in zip(
                            obb_rows,
                            step_indices,
                            clearances,
                        ):
                            if float(clearance) > exact_trigger:
                                continue
                            obs_wheelbase = (
                                float(row[5])
                                if row.shape[0] >= 6
                                and np.isfinite(row[5])
                                and row[5] > 0
                                else None
                            )
                            ego_box = _obb_corners(
                                float(branch[int(step_idx), 0]),
                                float(branch[int(step_idx), 1]),
                                float(headings[int(step_idx)]),
                                float(ego_length),
                                float(ego_width),
                                float(ego_wheelbase),
                            )
                            obs_box = _obb_corners(
                                float(row[0]),
                                float(row[1]),
                                float(row[2]),
                                max(float(row[3]), 1e-3),
                                max(float(row[4]), 1e-3),
                                obs_wheelbase,
                            )
                            exact_clearance = _obb_distance(ego_box, obs_box)
                            exact_obb_min_clearance = min(
                                exact_obb_min_clearance,
                                exact_clearance,
                            )
                            exact_obb_pairs += 1
                point_valid = valid & ~obb_valid
                if point_valid.any():
                    _, step_indices = np.nonzero(point_valid)
                    point_rows = rows[point_valid]
                    point_clearances = np.linalg.norm(
                        branch[step_indices, :2] - point_rows[:, :2],
                        axis=1,
                    )
                    if point_clearances.size:
                        min_lower_bound = min(
                            min_lower_bound,
                            float(np.min(point_clearances)),
                        )

        finite_lower_bound = (
            float(min_lower_bound) if np.isfinite(min_lower_bound) else None
        )
        finite_exact_obb_clearance = (
            float(exact_obb_min_clearance)
            if np.isfinite(exact_obb_min_clearance)
            else None
        )
        soft_violation = (
            max(0.0, soft_threshold - float(min_lower_bound))
            if finite_lower_bound is not None
            else 0.0
        )
        near_miss_violation = (
            max(0.0, near_miss_threshold - float(min_lower_bound))
            if finite_lower_bound is not None
            else 0.0
        )
        min_clearance_lower_bounds.append(finite_lower_bound)
        exact_obb_min_clearances.append(finite_exact_obb_clearance)
        exact_obb_evaluated_pairs.append(int(exact_obb_pairs))
        soft_violations.append(float(soft_violation))
        near_miss_violations.append(float(near_miss_violation))
        obstacle_slots.append(slots)
        geometry_modes.append("obb" if used_obb else "point")

    return {
        "schema_version": "candidate_current_tick_obstacle_clearance_v2",
        "selection_effect": False,
        "future_outcome_leakage": False,
        "definition": (
            "conservative current-tick obstacle-clearance lower bound; exact OBB "
            "distance is an optional diagnostic evaluated only when the "
            "bounding-circle lower bound is within the configured hinge thresholds"
        ),
        "horizon_steps": int(horizon),
        "soft_clearance_threshold_m": float(soft_threshold),
        "near_miss_threshold_m": float(near_miss_threshold),
        "exact_evaluation_trigger_m": float(exact_trigger),
        "exact_obb_enabled": bool(evaluate_exact_obb),
        "min_obstacle_clearance_m": min_clearance_lower_bounds,
        "min_obstacle_clearance_lower_bound_m": min_clearance_lower_bounds,
        "exact_min_obstacle_clearance_m": exact_obb_min_clearances,
        "exact_evaluated_pairs": exact_obb_evaluated_pairs,
        "exact_obb_min_obstacle_clearance_m": exact_obb_min_clearances,
        "exact_obb_evaluated_pairs": exact_obb_evaluated_pairs,
        "soft_clearance_violation_m": soft_violations,
        "soft_clearance_violation_cost": [
            float(value * value) for value in soft_violations
        ],
        "near_miss_violation_m": near_miss_violations,
        "near_miss_violation_cost": [
            float(value * value) for value in near_miss_violations
        ],
        "obstacle_slots": obstacle_slots,
        "geometry_mode": geometry_modes,
    }


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
    diagnostic_payloads: Optional[dict[str, Any]] = None
    source_valid_mask: Optional[np.ndarray] = None
    physical_feasible_mask: Optional[np.ndarray] = None


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
        "latency_ms_shadow_lateral_comfort": (
            "shadow_lateral_comfort_latency_ms"
        ),
        "latency_ms_shadow_obstacle_clearance": (
            "shadow_obstacle_clearance_latency_ms"
        ),
        "latency_ms_shadow_perfect_tracker_command": (
            "shadow_perfect_tracker_command_latency_ms"
        ),
        "latency_ms_shadow_perfect_tracker_open_loop": (
            "shadow_perfect_tracker_open_loop_latency_ms"
        ),
        "latency_ms_shadow_full_horizon_red_light": (
            "shadow_full_horizon_red_light_latency_ms"
        ),
        "latency_ms_context_and_obstacles": "context_and_obstacles_latency_ms",
        "latency_ms_reward_scoring": "reward_scoring_latency_ms",
        "latency_ms_reward_npz_dump": "reward_npz_dump_latency_ms",
        "latency_ms_reward_tensor_setup": "reward_tensor_setup_latency_ms",
        "latency_ms_reward_sg_smoothing": "reward_sg_smoothing_latency_ms",
        "latency_ms_reward_candidate_tensor_transfer": (
            "reward_candidate_tensor_transfer_latency_ms"
        ),
        "latency_ms_reward_batch_compute": "reward_batch_compute_latency_ms",
        "latency_ms_reward_postprocess": "reward_postprocess_latency_ms",
        "latency_ms_reward_full_horizon_red_light": (
            "reward_full_horizon_red_light_latency_ms"
        ),
        "latency_ms_reward_red_route_points": (
            "reward_red_route_points_latency_ms"
        ),
        "latency_ms_reward_feasibility": "reward_feasibility_latency_ms",
        "latency_ms_reward_field_extraction": (
            "reward_field_extraction_latency_ms"
        ),
        "latency_ms_reward_step_reach_guard": (
            "reward_step_reach_guard_latency_ms"
        ),
        "latency_ms_reward_route_progress": "reward_route_progress_latency_ms",
        "latency_ms_reward_route_progress_guard": (
            "reward_route_progress_guard_latency_ms"
        ),
        "latency_ms_reward_lexicographic_filter": (
            "reward_lexicographic_filter_latency_ms"
        ),
        "latency_ms_outcome_collection": "outcome_collection_latency_ms",
        "latency_ms_red_stopping_margin_atom": (
            "red_stopping_margin_atom_latency_ms"
        ),
        "latency_ms_camp_selection": "camp_selection_latency_ms",
        "latency_ms_underprogress_relaxation": (
            "underprogress_relaxation_latency_ms"
        ),
        "latency_ms_perfect_tracker_command_postselection": (
            "perfect_tracker_command_postselection_latency_ms"
        ),
        "latency_ms_traffic_light_hybrid_postselection": (
            "traffic_light_hybrid_postselection_latency_ms"
        ),
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


def _default_off_diagnostic_payloads(
    *,
    candidates: np.ndarray,
    candidate_set_consensus_payload_logging: bool,
    candidate_set_consensus_payload_steps: int,
    progress_support_logging: bool,
    progress_support_route_centerline_ego: Optional[np.ndarray],
    progress_support_steps: int,
    progress_support_dt_s: float,
) -> tuple[Optional[dict[str, Any]], dict[str, float]]:
    payloads: dict[str, Any] = {}
    latency_ms: dict[str, float] = {}

    if candidate_set_consensus_payload_logging:
        start = time.perf_counter()
        try:
            payload = build_candidate_set_consensus_payload(
                candidates=candidates,
                support_steps=candidate_set_consensus_payload_steps,
            )
        except ValueError as exc:
            payload = _unavailable_candidate_set_consensus_payload(
                reason="candidate_set_consensus_payload_invalid_input",
                error=str(exc),
                elapsed_ms=(time.perf_counter() - start) * 1000.0,
            )
        payloads["candidate_set_consensus_payload_logging"] = payload
        latency_ms.update(
            {
                key: float(value)
                for key, value in payload.get("latency_ms", {}).items()
            }
        )

    if progress_support_logging:
        start = time.perf_counter()
        if progress_support_route_centerline_ego is None:
            payload = _unavailable_progress_support_payload(
                reason="route_centerline_ego_missing",
                error=None,
                elapsed_ms=(time.perf_counter() - start) * 1000.0,
            )
        else:
            try:
                payload = build_progress_support_logging_payload(
                    candidates=candidates,
                    route_centerline_ego=progress_support_route_centerline_ego,
                    support_steps=progress_support_steps,
                    dt_s=progress_support_dt_s,
                )
            except ValueError as exc:
                payload = _unavailable_progress_support_payload(
                    reason="progress_support_payload_invalid_input",
                    error=str(exc),
                    elapsed_ms=(time.perf_counter() - start) * 1000.0,
                )
        payloads["progress_support_logging"] = payload
        latency_ms.update(
            {
                key: float(value)
                for key, value in payload.get("latency_ms", {}).items()
            }
        )

    if not payloads:
        return None, {}
    return payloads, latency_ms


def _unavailable_candidate_set_consensus_payload(
    *,
    reason: str,
    error: Optional[str],
    elapsed_ms: float,
) -> dict[str, Any]:
    return _unavailable_default_off_payload(
        schema_version=CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
        reason=reason,
        error=error,
        latency_keys=CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS,
        elapsed_ms=elapsed_ms,
        definition=(
            "default-off current-tick candidate-set consensus diagnostics "
            "failed closed before affecting selection"
        ),
    )


def _unavailable_progress_support_payload(
    *,
    reason: str,
    error: Optional[str],
    elapsed_ms: float,
) -> dict[str, Any]:
    return _unavailable_default_off_payload(
        schema_version=PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
        reason=reason,
        error=error,
        latency_keys=PROGRESS_SUPPORT_LATENCY_KEYS,
        elapsed_ms=elapsed_ms,
        definition=(
            "default-off current-tick progress-support diagnostics failed "
            "closed before affecting selection"
        ),
    )


def _unavailable_default_off_payload(
    *,
    schema_version: str,
    reason: str,
    error: Optional[str],
    latency_keys: Sequence[str],
    elapsed_ms: float,
    definition: str,
) -> dict[str, Any]:
    latency = {key: 0.0 for key in latency_keys}
    if latency_keys:
        latency[latency_keys[0]] = float(max(elapsed_ms, 0.0))
    payload = {
        "schema_version": schema_version,
        "enabled": True,
        "default_off": True,
        "available": False,
        "availability_reason": reason,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "deployed_atom_vector_change": False,
        "definition": definition,
        "latency_ms": latency,
        "fail_closed": True,
        "math_boundary": (
            "Unavailable diagnostic payloads do not alter candidates, "
            "feasibility, atoms, weights, scores, or selection. CAMP scoring "
            "remains affine in weights: score_k(w)=a_k^T w."
        ),
        "classical_benders_claim": False,
    }
    if error is not None:
        payload["error"] = error
    return payload


class CAMPSelector:
    """Score Diffusion-Planner trajectory candidates with CAMP atoms.

    ``mode="static"`` uses the learned offline CAMP weights and is the
    deployable bridge for the current Diffusion-Planner simulator.
    ``mode="linear"`` uses the legacy CAMP ``Theta`` matrix and requires a compatible
    per-step scene embedding. A Diffusion-Planner encoder feature is not
    considered compatible without a separately trained adapter.
    ``mode="context_simplex"`` is the strict V25 path: it accepts only the
    frozen 26D causal raw context, applies train-only q05/q95 complement lifting,
    and multiplies a column-simplex ``Theta`` without softmax or projection.
    """

    def __init__(
        self,
        atom_scales: np.ndarray,
        *,
        static_weights: Optional[np.ndarray] = None,
        theta: Optional[np.ndarray] = None,
        feature_center: Optional[np.ndarray] = None,
        feature_scale: Optional[np.ndarray] = None,
        context_q05: Optional[np.ndarray] = None,
        context_q95: Optional[np.ndarray] = None,
        context_feature_names: Optional[Sequence[str]] = None,
        context_schema_version: str = V25_CONTEXT_SCHEMA_VERSION,
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
        if np.any(self.atom_scales <= 0.0):
            raise ValueError("atom_scales must be strictly positive.")
        self.num_atoms = int(self.atom_scales.size)

        if mode not in {"static", "linear", "context_simplex"}:
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
        if fallback_mode not in {"uniform", "learned", "top1"}:
            raise ValueError(
                "fallback_mode must be 'uniform', 'learned', or 'top1', "
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
            if (
                not np.all(np.isfinite(fallback_scales))
                or np.any(fallback_scales <= 0.0)
            ):
                raise ValueError(
                    "fallback_atom_scales must contain only finite positive values."
                )
            self.fallback_atom_scales = fallback_scales
            self.fallback_static_weights = _strict_normalized_simplex_weights(
                fallback_static_weights,
                self.num_atoms,
                label="fallback_static_weights",
            )

        self.static_weights = None
        if static_weights is not None:
            self.static_weights = _strict_normalized_simplex_weights(
                static_weights,
                self.num_atoms,
                label="static_weights",
            )

        self.theta = None
        if theta is not None:
            theta_arr = np.asarray(theta, dtype=np.float64)
            if theta_arr.ndim != 2 or theta_arr.shape[0] != self.num_atoms:
                raise ValueError(
                    "Theta must be a matrix with one row per atom, "
                    f"got {theta_arr.shape}."
                )
            if mode == "context_simplex":
                validate_column_simplex_theta(
                    theta_arr, num_atoms=self.num_atoms
                )
            self.theta = theta_arr

        self.feature_center = None
        self.feature_scale = None
        if self.theta is not None and self.mode == "linear":
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

        self.context_scaler = None
        self.context_feature_names = None
        self.context_schema_version = None
        if self.mode == "context_simplex":
            if self.theta is None:
                raise ValueError("V25 context-simplex CAMP selection requires Theta.")
            if self.theta.shape[1] != V25_PHI_DIMENSION:
                raise ValueError(
                    f"V25 context Theta requires {V25_PHI_DIMENSION} columns."
                )
            if context_q05 is None or context_q95 is None:
                raise ValueError("V25 context mode requires train-only context_q05/q95.")
            names = tuple(
                str(name)
                for name in (() if context_feature_names is None else context_feature_names)
            )
            if names != tuple(V25_RAW_FEATURE_NAMES):
                raise ValueError("V25 context feature names/order must match the freeze.")
            if str(context_schema_version) != V25_CONTEXT_SCHEMA_VERSION:
                raise ValueError("V25 context schema version does not match the freeze.")
            if feature_center is not None or feature_scale is not None:
                raise ValueError(
                    "V25 context mode forbids legacy embedding center/scale fields."
                )
            self.context_scaler = V25ContextScaler(
                q05=np.asarray(context_q05, dtype=np.float64),
                q95=np.asarray(context_q95, dtype=np.float64),
            )
            self.context_feature_names = names
            self.context_schema_version = str(context_schema_version)

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
        context_q05 = None
        context_q95 = None
        context_feature_names = None
        context_schema_version = V25_CONTEXT_SCHEMA_VERSION
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
            if "context_q05" in payload:
                context_q05 = np.asarray(payload["context_q05"], dtype=np.float64)
            if "context_q95" in payload:
                context_q95 = np.asarray(payload["context_q95"], dtype=np.float64)
            if "context_feature_names" in payload:
                context_feature_names = tuple(
                    str(value) for value in np.asarray(payload["context_feature_names"]).reshape(-1)
                )
            context_schema_version = _payload_string(
                payload,
                "context_schema_version",
                context_schema_version,
            )
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
            context_q05=context_q05,
            context_q95=context_q95,
            context_feature_names=context_feature_names,
            context_schema_version=context_schema_version,
            feature_clip=feature_clip,
            linear_activation=linear_activation,
            mode=mode,
            fallback_mode=fallback_mode,
            fallback_atom_scales=fallback_atom_scales,
            fallback_static_weights=fallback_static_weights,
            atom_clip=atom_clip,
        )

    def weights_for(
        self,
        scene_embedding: Optional[np.ndarray] = None,
        *,
        raw_context: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        if self.mode == "static":
            return self.static_weights.copy()

        if self.mode == "context_simplex":
            if scene_embedding is not None:
                raise ValueError(
                    "V25 context mode rejects scene_embedding/private latent; "
                    "pass the frozen 26D raw_context."
                )
            if raw_context is None:
                raise ValueError("V25 context-simplex selection requires raw_context.")
            phi = self.context_scaler.lift(
                np.asarray(raw_context, dtype=np.float64).reshape(-1)
            )
            return v25_context_weights(self.theta, phi)

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
        raw_context: Optional[np.ndarray] = None,
        candidate_obstacles: Optional[np.ndarray] = None,
        candidate_progress: Optional[np.ndarray] = None,
        candidate_planned_red_light_cost: Optional[np.ndarray] = None,
        candidate_red_stopping_margin_cost: Optional[np.ndarray] = None,
        candidate_dp_prior_jerk_excess_cost: Optional[np.ndarray] = None,
        candidate_source_valid_mask: Optional[np.ndarray] = None,
        external_feasible_mask: Optional[np.ndarray] = None,
        external_infeasibility_reasons: Optional[Sequence[Sequence[str]]] = None,
        apply_context_feasibility: bool = True,
        candidate_set_consensus_payload_logging: bool = False,
        candidate_set_consensus_payload_steps: int = 10,
        progress_support_logging: bool = False,
        progress_support_route_centerline_ego: Optional[np.ndarray] = None,
        progress_support_steps: int = 10,
        progress_support_dt_s: Optional[float] = None,
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
        source_valid_mask = np.ones(candidates.shape[0], dtype=bool)
        if candidate_source_valid_mask is not None:
            raw_source_valid = np.asarray(candidate_source_valid_mask)
            if raw_source_valid.dtype != np.bool_:
                raise ValueError(
                    "candidate_source_valid_mask must contain strict booleans."
                )
            source_valid_mask = raw_source_valid.reshape(-1)
            if source_valid_mask.shape != (candidates.shape[0],):
                raise ValueError(
                    "candidate_source_valid_mask must match candidate count, "
                    f"got {source_valid_mask.shape}, expected ({candidates.shape[0]},)."
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
        atom_context = context
        if context.lane_centerline is not None:
            phase_start = time.perf_counter()
            lane_centerline, _ = exact_centerline_slice_for_candidates(
                context.lane_centerline,
                candidates[:, :, :2],
            )
            atom_context = replace(
                context,
                lane_centerline=lane_centerline,
            )
            atom_computation_seconds += time.perf_counter() - phase_start
        for candidate_idx, trajectory in enumerate(candidates):
            local_context = atom_context
            if obstacles is not None:
                dynamic = {
                    obstacle_idx: obstacle[:, :2]
                    for obstacle_idx, obstacle in enumerate(obstacles[candidate_idx])
                    if np.any(np.abs(obstacle[:, :2]) > 1e-8)
                }
                local_context = replace(
                    atom_context,
                    dynamic_obstacles=dynamic,
                )

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
        if self.num_atoms == len(DP_CAMP_ATOM_NAMES_V10):
            invalid_source = ~source_valid_mask
            feasible_mask &= source_valid_mask
            for index in np.flatnonzero(invalid_source):
                infeasibility_reasons[index] = tuple(
                    dict.fromkeys((*infeasibility_reasons[index], "source_invalid"))
                )
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
            if not np.all(np.isfinite(progress)) or np.any(progress < 0.0):
                raise ValueError(
                    "candidate_progress must contain finite nonnegative values."
                )
            if self.num_atoms == len(DP_CAMP_ATOM_NAMES_V10):
                from camp_core.integrations.diffusion_planner_causal_atoms import (
                    source_valid_progress_shortfall,
                )

                reference_progress, progress_shortfall = (
                    source_valid_progress_shortfall(progress, source_valid_mask)
                )
            else:
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
                if (
                    not np.all(np.isfinite(red_light_cost))
                    or np.any(red_light_cost < 0.0)
                ):
                    raise ValueError(
                        "candidate_planned_red_light_cost must contain finite "
                        "nonnegative values."
                    )
                phase_start = time.perf_counter()
                lateral_acceleration_cost = np.asarray(
                    [
                        _trajectory_comfort(candidate, context.dt)[1]
                        for candidate in candidates
                    ],
                    dtype=np.float64,
                )
                atom_computation_seconds += time.perf_counter() - phase_start
                if (
                    not np.all(np.isfinite(lateral_acceleration_cost))
                    or np.any(lateral_acceleration_cost < 0.0)
                ):
                    raise ValueError(
                        "candidate lateral-acceleration cost must contain finite "
                        "nonnegative values."
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
        if not np.all(np.isfinite(atoms_arr)) or np.any(atoms_arr < 0.0):
            raise ValueError("CAMP atoms must be finite nonnegative costs.")
        if self.num_atoms == 14:
            from camp_core.integrations.diffusion_planner_causal_atoms import (
                CANONICAL_NORMALIZED_ATOM_CLIP,
                canonical_normalize_atoms,
            )

            if self.atom_clip != CANONICAL_NORMALIZED_ATOM_CLIP:
                raise ValueError("14D CAMP atom clip drifted from the canonical contract.")
            normalized = canonical_normalize_atoms(atoms_arr, self.atom_scales)
        else:
            normalized = atoms_arr / self.atom_scales.reshape(1, -1)
            if not np.all(np.isfinite(normalized)):
                raise ValueError("normalized CAMP atoms must be finite.")
            normalized = np.maximum(normalized, 0.0)
            if self.atom_clip > 0:
                normalized = np.clip(normalized, 0.0, self.atom_clip)

        weights = self.weights_for(scene_embedding, raw_context=raw_context)
        scores = normalized @ weights
        eligibility_mask = (
            source_valid_mask if self.num_atoms == len(DP_CAMP_ATOM_NAMES_V10)
            else feasible_mask
        )
        if self.num_atoms == len(DP_CAMP_ATOM_NAMES_V10) and not eligibility_mask.any():
            raise ValueError(
                "source_valid candidate set is empty; candidate0/all-K fallback is forbidden"
            )
        used_fallback = not eligibility_mask.any()
        selection_weights = weights
        selection_normalized = normalized
        if used_fallback:
            if self.fallback_mode == "top1":
                selection_scores = np.full(candidates.shape[0], np.inf)
                selection_scores[0] = 0.0
            elif self.fallback_mode == "learned":
                if self.fallback_static_weights is None:
                    selection_scores = scores.copy()
                else:
                    selection_weights = self.fallback_static_weights
                    if self.num_atoms == 14:
                        selection_normalized = canonical_normalize_atoms(
                            atoms_arr,
                            self.fallback_atom_scales,
                        )
                    else:
                        selection_normalized = atoms_arr / (
                            self.fallback_atom_scales.reshape(1, -1)
                        )
                        if not np.all(np.isfinite(selection_normalized)):
                            raise ValueError(
                                "fallback normalized CAMP atoms must be finite."
                            )
                        selection_normalized = np.maximum(
                            selection_normalized, 0.0
                        )
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
            selection_scores[~eligibility_mask] = np.inf

        selected_index = int(np.argmin(selection_scores))
        select_done = time.perf_counter()
        diagnostic_payloads, diagnostic_latency_ms = _default_off_diagnostic_payloads(
            candidates=candidates,
            candidate_set_consensus_payload_logging=(
                candidate_set_consensus_payload_logging
            ),
            candidate_set_consensus_payload_steps=(
                candidate_set_consensus_payload_steps
            ),
            progress_support_logging=progress_support_logging,
            progress_support_route_centerline_ego=progress_support_route_centerline_ego,
            progress_support_steps=progress_support_steps,
            progress_support_dt_s=(
                context.dt if progress_support_dt_s is None else progress_support_dt_s
            ),
        )
        scoring_seconds = max(
            (select_done - select_start)
            - atom_computation_seconds
            - feasibility_seconds
            - collision_seconds,
            0.0,
        )
        timings_ms = {
            "atom_computation": atom_computation_seconds * 1000.0,
            "feasibility": feasibility_seconds * 1000.0,
            "collision_checks": collision_seconds * 1000.0,
            "scoring": scoring_seconds * 1000.0,
        }
        timings_ms.update(diagnostic_latency_ms)
        return CAMPSelectionResult(
            selected_index=selected_index,
            selected_trajectory=candidates[selected_index].copy(),
            atoms=atoms_arr,
            normalized_atoms=normalized,
            feasible_mask=feasible_mask,
            source_valid_mask=source_valid_mask,
            physical_feasible_mask=feasible_mask,
            infeasibility_reasons=tuple(infeasibility_reasons),
            scores=scores,
            weights=weights,
            selection_scores=selection_scores,
            selection_weights=selection_weights,
            selection_normalized_atoms=selection_normalized,
            used_fallback=used_fallback,
            timings_ms=timings_ms,
            diagnostic_payloads=diagnostic_payloads,
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
    reference_blend_steps: int | None = None,
    guidance_policy: str = "disabled",
    noise_strategy: str = "iid",
) -> tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    """Generate K Diffusion-Planner candidates in one batched forward pass.

    Returns ego candidates ``[K,T,4]``, predicted neighbor trajectories
    ``[K,Pn,T,4]``, and optional turn-indicator logits ``[K,C]``.
    """
    if num_candidates < 1:
        raise ValueError("num_candidates must be >= 1.")
    if noise_scale < 0:
        raise ValueError("noise_scale must be non-negative.")
    if guidance_policy not in {"disabled", "preserve", "preserve_candidate0"}:
        raise ValueError(
            "guidance_policy must be 'disabled', 'preserve', or "
            "'preserve_candidate0'."
        )
    if noise_strategy not in {"iid", "antithetic"}:
        raise ValueError("noise_strategy must be 'iid' or 'antithetic'.")

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
    latent_shape = (
        num_candidates,
        num_agents,
        future_len + 1,
        4,
    )
    if noise_strategy == "iid":
        latent = torch.randn(
            *latent_shape,
            device=device,
            dtype=expanded["ego_current_state"].dtype,
        ) * float(noise_scale)
    else:
        latent = torch.empty(
            *latent_shape,
            device=device,
            dtype=expanded["ego_current_state"].dtype,
        )
        first_stochastic = 1 if deterministic_first else 0
        stochastic_count = num_candidates - first_stochastic
        pair_count = stochastic_count // 2
        if pair_count:
            paired = torch.randn(
                pair_count,
                num_agents,
                future_len + 1,
                4,
                device=device,
                dtype=expanded["ego_current_state"].dtype,
            ) * float(noise_scale)
            pair_start = first_stochastic
            pair_stop = pair_start + 2 * pair_count
            latent[pair_start:pair_stop:2] = paired
            latent[pair_start + 1:pair_stop:2] = -paired
        if stochastic_count % 2:
            latent[-1] = torch.randn(
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
    if guidance_policy == "preserve_candidate0" and original_guidance is not None:
        if not deterministic_first:
            raise ValueError(
                "guidance_policy='preserve_candidate0' requires "
                "deterministic_first=True."
            )
        try:
            decoder._guidance_fn = None
            with torch.no_grad():
                _, unguided_outputs = model(expanded)
            candidate0_outputs = _slice_model_outputs(
                unguided_outputs,
                start=0,
                stop=1,
            )
            if num_candidates > 1:
                decoder._guidance_fn = original_guidance
                with torch.enable_grad():
                    _, guided_outputs = model(
                        _slice_batch_inputs(expanded, start=1, stop=None)
                    )
                outputs = _concat_model_outputs(candidate0_outputs, guided_outputs)
            else:
                outputs = candidate0_outputs
        finally:
            decoder._guidance_fn = original_guidance
    else:
        if guidance_policy == "disabled":
            decoder._guidance_fn = None
        guidance_enabled = (
            guidance_policy == "preserve" and original_guidance is not None
        )
        context = torch.enable_grad() if guidance_enabled else torch.no_grad()
        try:
            with context:
                _, outputs = model(expanded)
        finally:
            decoder._guidance_fn = original_guidance

    predictions = outputs["prediction"].detach().cpu().numpy()
    turn_logits = outputs.get("turn_indicator_logit")
    if turn_logits is not None:
        turn_logits = turn_logits.detach().cpu().numpy()
    ego_candidates = predictions[:, 0]
    if reference_blend_steps is not None:
        ego_candidates = blend_candidate_prefix_with_reference(
            ego_candidates,
            reference_blend_steps,
        )
    return ego_candidates, predictions[:, 1:], turn_logits


def _slice_batch_inputs(
    inputs: dict[str, Any],
    *,
    start: int,
    stop: int | None,
) -> dict[str, Any]:
    """Slice batched tensor inputs while leaving scalar metadata untouched."""
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("Diffusion-Planner candidate generation requires torch.") from exc

    sliced: dict[str, Any] = {}
    batch_size = int(inputs["sampled_trajectories"].shape[0])
    for key, value in inputs.items():
        if isinstance(value, torch.Tensor) and value.shape[:1] == (batch_size,):
            sliced[key] = value[start:stop].contiguous()
        else:
            sliced[key] = value
    return sliced


def _concat_model_outputs(
    first: dict[str, Any],
    second: dict[str, Any],
) -> dict[str, Any]:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("Diffusion-Planner candidate generation requires torch.") from exc

    outputs = dict(first)
    for key, first_value in first.items():
        second_value = second.get(key)
        if (
            isinstance(first_value, torch.Tensor)
            and isinstance(second_value, torch.Tensor)
            and first_value.ndim >= 1
            and second_value.ndim >= 1
        ):
            outputs[key] = torch.cat([first_value, second_value], dim=0)
    return outputs


def _slice_model_outputs(
    outputs: dict[str, Any],
    *,
    start: int,
    stop: int | None,
) -> dict[str, Any]:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("Diffusion-Planner candidate generation requires torch.") from exc

    sliced = dict(outputs)
    prediction = outputs.get("prediction")
    if not isinstance(prediction, torch.Tensor) or prediction.ndim < 1:
        raise ValueError("Diffusion-Planner outputs must contain batched prediction.")
    batch_size = int(prediction.shape[0])
    for key, value in outputs.items():
        if isinstance(value, torch.Tensor) and value.shape[:1] == (batch_size,):
            sliced[key] = value[start:stop].contiguous()
    return sliced


def blend_candidate_prefix_with_reference(
    candidates: np.ndarray,
    blend_steps: int,
) -> np.ndarray:
    """Blend stochastic candidate prefixes toward deterministic candidate 0.

    The fixed schedule is ``lambda_t = min(t / blend_steps, 1)``. Candidate 0
    is unchanged, every other candidate has exactly the same first reference
    pose as candidate 0, and the original sample is recovered from
    ``t >= blend_steps``. This transforms only the finite candidate set; all
    downstream reward, safety, atom, and CAMP checks remain unchanged.
    """
    trajectories = np.asarray(candidates)
    if (
        trajectories.ndim != 3
        or trajectories.shape[0] < 1
        or trajectories.shape[1] < 2
        or trajectories.shape[2] < 2
    ):
        raise ValueError(
            "candidates must have shape [K,T,D>=2] with T>=2, "
            f"got {trajectories.shape}."
        )
    if not np.all(np.isfinite(trajectories)):
        raise ValueError("candidates must contain only finite values.")
    if (
        isinstance(blend_steps, bool)
        or not isinstance(blend_steps, (int, np.integer))
        or not 1 <= int(blend_steps) < trajectories.shape[1]
    ):
        raise ValueError(
            "blend_steps must be an integer in [1, trajectory_length - 1]."
        )

    blended = trajectories.copy()
    weights = np.minimum(
        np.arange(trajectories.shape[1], dtype=np.float64)
        / float(blend_steps),
        1.0,
    )
    reference = trajectories[0:1]
    blended[1:] = (
        reference
        + weights[np.newaxis, :, np.newaxis]
        * (trajectories[1:] - reference)
    )
    if trajectories.shape[2] >= 4:
        orientation = blended[1:, :, 2:4]
        norms = np.linalg.norm(orientation, axis=2, keepdims=True)
        reference_orientation = np.broadcast_to(
            reference[:, :, 2:4],
            orientation.shape,
        )
        orientation = np.where(
            norms > 1e-12,
            orientation / np.maximum(norms, 1e-12),
            reference_orientation,
        )
        blended[1:, :, 2:4] = orientation
    blended[1:, 0] = reference[0, 0]
    blended[1:, int(blend_steps) :] = trajectories[
        1:,
        int(blend_steps) :,
    ]
    if not np.all(np.isfinite(blended)):
        raise RuntimeError("Reference-prefix blend produced nonfinite candidates.")
    return blended
