from __future__ import annotations

import json
import math
import sys
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


@dataclass(frozen=True)
class CAMPSelectionResult:
    selected_index: int
    selected_trajectory: np.ndarray
    atoms: np.ndarray
    normalized_atoms: np.ndarray
    feasible_mask: np.ndarray
    scores: np.ndarray
    weights: np.ndarray
    used_fallback: bool


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
    latencies = []

    for record in records:
        selected_index = int(record["selected_index"])
        key = str(selected_index)
        selected_counts[key] = selected_counts.get(key, 0) + 1
        selected_nonzero += int(selected_index != 0)
        fallback_count += int(bool(record.get("used_fallback", False)))

        feasible_mask = np.asarray(record.get("feasible_mask", []), dtype=bool)
        feasible_candidates += int(feasible_mask.sum())
        total_candidates += int(feasible_mask.size)

        latency = record.get("latency_ms_including_candidate_generation")
        if latency is not None and np.isfinite(latency):
            latencies.append(float(latency))

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
        "mean_selection_latency_ms": (
            float(np.mean(latencies)) if latencies else None
        ),
        "p95_selection_latency_ms": (
            float(np.percentile(latencies, 95)) if latencies else None
        ),
    }
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
        mode: str = "static",
        atom_clip: float = 10.0,
    ) -> "CAMPSelector":
        scales_path = Path(atom_scales_path)
        with scales_path.open("r", encoding="utf-8") as f:
            atom_scales = np.asarray(json.load(f), dtype=np.float64)

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

        return cls(
            atom_scales,
            static_weights=static_weights,
            theta=theta,
            feature_center=feature_center,
            feature_scale=feature_scale,
            feature_clip=feature_clip,
            linear_activation=linear_activation,
            mode=mode,
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
    ) -> CAMPSelectionResult:
        """Select one trajectory from ``[K, T, >=2]`` candidates.

        ``candidate_obstacles`` may be ``[K, M, T, 2]`` for candidate-specific
        neighbor predictions or ``[M, T, 2]`` for one shared obstacle forecast.
        """
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

        atoms = []
        feasible = []
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
            atom_vector = compute_atom_bank_vector(local_context, trajectory_xy)
            if atom_vector.shape != (self.num_atoms,):
                raise ValueError(
                    f"CAMP atom dimension is {atom_vector.shape}, "
                    f"but scales expect ({self.num_atoms},)."
                )
            atoms.append(atom_vector)
            feasible.append(
                compute_feasibility_mask(local_context, trajectory_xy)
                and self._collision_free(local_context, trajectory_xy)
            )

        atoms_arr = np.asarray(atoms, dtype=np.float64)
        normalized = atoms_arr / self.atom_scales.reshape(1, -1)
        positive_inf = self.atom_clip if self.atom_clip > 0 else np.finfo(np.float64).max
        normalized = np.nan_to_num(
            normalized, nan=0.0, posinf=positive_inf, neginf=0.0
        )
        normalized = np.maximum(normalized, 0.0)
        if self.atom_clip > 0:
            normalized = np.clip(normalized, 0.0, self.atom_clip)

        weights = self.weights_for(scene_embedding)
        feasible_mask = np.asarray(feasible, dtype=bool)
        scores = normalized @ weights
        used_fallback = not feasible_mask.any()
        if used_fallback:
            fallback_weights = np.full(self.num_atoms, 1.0 / self.num_atoms)
            selection_scores = normalized @ fallback_weights
        else:
            selection_scores = scores.copy()
            selection_scores[~feasible_mask] = np.inf

        selected_index = int(np.argmin(selection_scores))
        return CAMPSelectionResult(
            selected_index=selected_index,
            selected_trajectory=candidates[selected_index].copy(),
            atoms=atoms_arr,
            normalized_atoms=normalized,
            feasible_mask=feasible_mask,
            scores=scores,
            weights=weights,
            used_fallback=used_fallback,
        )

    @staticmethod
    def _collision_free(context: DriverAtomContext, trajectory_xy: np.ndarray) -> bool:
        threshold = float(context.safety_radius)
        if context.static_obstacles is not None and len(context.static_obstacles) > 0:
            static_xy = np.asarray(context.static_obstacles, dtype=np.float64)[:, :2]
            distances = np.linalg.norm(
                trajectory_xy[:, np.newaxis, :] - static_xy[np.newaxis, :, :],
                axis=-1,
            )
            if float(distances.min()) < threshold:
                return False

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
                    return False
        return True


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
