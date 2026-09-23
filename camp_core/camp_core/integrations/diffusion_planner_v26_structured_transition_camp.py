"""Human-demonstration CAMP with one receding-horizon transition atom.

Training compares every fixed DP candidate with the logged human ego future
using the same decision-time, deployable atom definitions.  Actual-future actor
states are not an input to this module or to the learned score.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_v26_scene_camp_math import (
    V26_NORMALIZED_ATOM_CLIP,
)
from camp_core.integrations.diffusion_planner_v26_sequential_camp import (
    interpolate_world_xyhvas,
)
from camp_core.integrations.diffusion_planner_v26_sparse_schema import (
    V26_ATOM_STATUS_VOCABULARY,
    V26_GLOBAL_ATOM_NAMES,
    validate_v26_sparse_pool_artifact,
)


V26_TRANSITION_ATOM_NAME = "previous_plan_execution_transition_rms"
V26_STRUCTURED_ATOM_NAMES = V26_GLOBAL_ATOM_NAMES + (V26_TRANSITION_ATOM_NAME,)
V26_STRUCTURED_ATOM_INDEX = {
    name: index for index, name in enumerate(V26_STRUCTURED_ATOM_NAMES)
}
def positive_q95(values: np.ndarray) -> float | None:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    positive = array[np.isfinite(array) & (array > 0.0)]
    if positive.size == 0:
        return None
    return float(np.quantile(positive, 0.95))


def transition_residual_components(
    candidate_world_xyhvas: np.ndarray,
    *,
    current_origin_seconds: float,
    previous_plan_world_xyhvas: np.ndarray | None,
    previous_origin_seconds: float | None,
) -> np.ndarray | None:
    """Return absolute [dx,dy,wrapped-dyaw,dv] on the common 0.1 s timeline."""

    candidates = np.asarray(candidate_world_xyhvas, dtype=np.float64)
    if candidates.ndim != 3 or candidates.shape[1:] != (80, 6):
        raise ValueError("candidate world trajectories must have shape [K,80,6]")
    if previous_plan_world_xyhvas is None or previous_origin_seconds is None:
        return None
    previous = np.asarray(previous_plan_world_xyhvas, dtype=np.float64)
    if previous.shape != (80, 6):
        raise ValueError("previous selected world trajectory must have shape [80,6]")
    current_times = float(current_origin_seconds) + 0.1 * np.arange(1, 81, dtype=np.float64)
    previous_times = float(previous_origin_seconds) + 0.1 * np.arange(1, 81, dtype=np.float64)
    common = current_times[
        (current_times >= previous_times[0] - 1e-9)
        & (current_times <= previous_times[-1] + 1e-9)
    ]
    if common.size == 0:
        return None
    candidate_common = np.stack(
        [interpolate_world_xyhvas(row, current_times, common) for row in candidates]
    )
    previous_common = interpolate_world_xyhvas(previous, previous_times, common)
    delta = candidate_common[:, :, :4] - previous_common[None, :, :4]
    delta[:, :, 2] = (delta[:, :, 2] + np.pi) % (2.0 * np.pi) - np.pi
    return np.abs(delta)


def fit_transition_component_scales(
    residual_rows: Sequence[np.ndarray],
) -> dict[str, float]:
    rows = [transition_component_rms(row) for row in residual_rows]
    if not rows:
        raise ValueError("transition scale fitting requires at least one applicable row")
    combined = np.concatenate(rows, axis=0)
    position = positive_q95(combined[:, 0])
    yaw = positive_q95(combined[:, 1])
    velocity = positive_q95(combined[:, 2])
    if position is None or yaw is None or velocity is None:
        raise ValueError("each transition component needs positive B/P train-fit support")
    return {
        "position_m": position,
        "yaw_rad": yaw,
        "longitudinal_velocity_mps": velocity,
    }


def transition_component_rms(residual_components: np.ndarray) -> np.ndarray:
    residual = np.asarray(residual_components, dtype=np.float64)
    if residual.ndim != 3 or residual.shape[2] != 4:
        raise ValueError("transition residuals must have shape [K,T,4]")
    position = np.sqrt(np.mean(np.sum(residual[:, :, :2] ** 2, axis=2), axis=1))
    yaw = np.sqrt(np.mean(residual[:, :, 2] ** 2, axis=1))
    velocity = np.sqrt(np.mean(residual[:, :, 3] ** 2, axis=1))
    return np.column_stack((position, yaw, velocity))


def transition_coefficient(
    residual_components: np.ndarray,
    *,
    scales: Mapping[str, float],
) -> np.ndarray:
    """Equal-component RMS of q95-normalized position, yaw, and velocity."""

    residual = np.asarray(residual_components, dtype=np.float64)
    if residual.ndim != 3 or residual.shape[2] != 4:
        raise ValueError("transition residuals must have shape [K,T,4]")
    component = transition_component_rms(residual)
    scale = np.asarray(
        [
            scales["position_m"],
            scales["yaw_rad"],
            scales["longitudinal_velocity_mps"],
        ],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(scale)) or np.any(scale <= 0.0):
        raise ValueError("transition component scales must be finite and positive")
    return np.sqrt(np.mean((component / scale[None, :]) ** 2, axis=1))


def validate_structured_sparse_pool_artifact(
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    if tuple(artifact.get("bank_atom_names", ())) != V26_STRUCTURED_ATOM_NAMES:
        raise ValueError("structured artifact bank order differs from the 16-atom main path")
    states = artifact.get("atom_states")
    if not isinstance(states, Sequence) or len(states) != len(V26_STRUCTURED_ATOM_NAMES):
        raise ValueError("structured artifact must retain all 16 endpoint states")
    names = tuple(str(row.get("name")) for row in states)
    statuses = tuple(str(row.get("status")) for row in states)
    if names != V26_STRUCTURED_ATOM_NAMES or any(
        status not in V26_ATOM_STATUS_VOCABULARY for status in statuses
    ):
        raise ValueError("structured endpoint names or statuses are invalid")
    observed = tuple(str(name) for name in artifact.get("observed_atom_names", ()))
    expected_observed = tuple(
        name for name, status in zip(names, statuses) if status == "observed"
    )
    if observed != expected_observed:
        raise ValueError("structured observed endpoints do not match endpoint states")
    indices = tuple(int(value) for value in artifact.get("observed_global_atom_indices", ()))
    expected_indices = tuple(V26_STRUCTURED_ATOM_INDEX[name] for name in observed)
    if indices != expected_indices:
        raise ValueError("structured observed endpoint indices changed")
    candidate = np.asarray(artifact.get("candidate_atoms_raw"), dtype=np.float64)
    expert = np.asarray(artifact.get("human_atoms_raw"), dtype=np.float64)
    candidate_count = int(artifact.get("K", 0))
    expert_names = tuple(str(name) for name in artifact.get("human_observed_atom_names", ()))
    if candidate.shape != (candidate_count, len(observed)):
        raise ValueError("structured candidate atom matrix must have shape [K,Q_observed]")
    if expert_names != observed or expert.shape != (len(observed),):
        raise ValueError("human atom row must cover the same observed endpoints as candidates")
    if not np.all(np.isfinite(candidate)) or np.any(candidate < 0.0):
        raise ValueError("structured candidate atoms must be finite and nonnegative")
    if not np.all(np.isfinite(expert)) or np.any(expert < 0.0):
        raise ValueError("human atoms must be finite and nonnegative")
    if float(artifact.get("human_margin_delta", np.nan)) != 1.0:
        raise ValueError("human demonstration margin must be exactly one")
    return {
        "identity": dict(artifact["identity"]),
        "status_pattern": statuses,
        "observed_atom_names": observed,
        "observed_global_atom_indices": indices,
        "atom_status_by_name": dict(zip(names, statuses, strict=True)),
        "candidate_atoms_raw": candidate,
        "expert_atoms_raw": expert,
        "human_atoms_raw": expert,
        "human_observed_atom_names": expert_names,
        "human_margin_delta": 1.0,
    }


def normalize_structured_sparse_pool(
    artifact: Mapping[str, Any], *, atom_scales: Mapping[str, float]
) -> dict[str, Any]:
    validated = validate_structured_sparse_pool_artifact(artifact)
    names = validated["observed_atom_names"]
    scales = np.asarray([atom_scales[name] for name in names], dtype=np.float64)
    if not np.all(np.isfinite(scales)) or np.any(scales <= 0.0):
        raise ValueError("structured scorer scales must be finite and positive")
    return {
        **validated,
        "active_atom_names": names,
        "active_global_atom_indices": validated["observed_global_atom_indices"],
        "candidate_atoms": np.clip(
            validated["candidate_atoms_raw"] / scales,
            0.0,
            V26_NORMALIZED_ATOM_CLIP,
        ),
        "expert_atoms": np.clip(
            validated["human_atoms_raw"] / scales,
            0.0,
            V26_NORMALIZED_ATOM_CLIP,
        ),
    }


@dataclass(frozen=True)
class _PatternHead:
    status_pattern: tuple[str, ...]
    active_global_indices: tuple[int, ...]
    theta: np.ndarray


class FrozenStructuredTransitionSelector:
    """Argmin deployment selector for a frozen 16-atom structured checkpoint."""

    def __init__(self, checkpoint_path: str | Path, *, atom_scales: Mapping[str, float]):
        self.checkpoint_path = Path(checkpoint_path).resolve()
        self._atom_scales = {name: float(atom_scales[name]) for name in V26_STRUCTURED_ATOM_NAMES}
        heads: list[_PatternHead] = []
        with np.load(self.checkpoint_path, allow_pickle=False) as payload:
            for key in sorted(name for name in payload.files if name.startswith("theta_")):
                suffix = key.removeprefix("theta_")
                pattern = tuple(str(value) for value in payload[f"status_pattern_{suffix}"])
                active = tuple(int(value) for value in payload[f"active_global_indices_{suffix}"])
                theta = np.asarray(payload[key], dtype=np.float64)
                if theta.shape != (len(active), 257):
                    raise ValueError("structured checkpoint head has the wrong shape")
                heads.append(_PatternHead(pattern, active, theta.copy()))
        self._heads = {head.status_pattern: head for head in heads}
        if not self._heads or len(self._heads) != len(heads):
            raise ValueError("structured checkpoint pattern heads are missing or duplicated")

    def select(self, artifact: Mapping[str, Any], phi: np.ndarray) -> dict[str, Any]:
        view = validate_structured_sparse_pool_artifact(artifact)
        head = self._heads.get(view["status_pattern"])
        if head is None or head.active_global_indices != view["observed_global_atom_indices"]:
            raise ValueError("structured checkpoint has no matching endpoint pattern")
        feature = np.asarray(phi, dtype=np.float64)
        if feature.shape != (256,) or not np.all(np.isfinite(feature)):
            raise ValueError("structured selector phi must be finite [256]")
        z = np.concatenate((feature, np.ones(1, dtype=np.float64)))
        affine = head.theta @ z
        if (
            not np.all(np.isfinite(affine))
            or float(np.min(affine)) < -1e-8
            or not np.isclose(np.sum(affine), 1.0, rtol=0.0, atol=1e-8)
        ):
            raise ValueError("unprojected structured score weights violate the simplex")
        weights = affine
        scales = np.asarray(
            [self._atom_scales[name] for name in view["observed_atom_names"]],
            dtype=np.float64,
        )
        atoms = np.clip(
            view["candidate_atoms_raw"] / scales,
            0.0,
            V26_NORMALIZED_ATOM_CLIP,
        )
        scores = atoms @ weights
        selected = int(np.argmin(scores))
        return {
            "selected_row": selected,
            "candidate_scores": scores,
            "scene_weights": weights,
            "raw_affine_weights": affine,
            "actual_future_read": False,
        }


__all__ = [
    "FrozenStructuredTransitionSelector",
    "V26_STRUCTURED_ATOM_INDEX",
    "V26_STRUCTURED_ATOM_NAMES",
    "V26_TRANSITION_ATOM_NAME",
    "fit_transition_component_scales",
    "normalize_structured_sparse_pool",
    "positive_q95",
    "transition_coefficient",
    "transition_component_rms",
    "transition_residual_components",
    "validate_structured_sparse_pool_artifact",
]
