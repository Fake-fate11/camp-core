"""Deploy frozen CAMP weights on an unchanged Diffusion Planner candidate pool.

The reranker consumes only decision-time candidate atoms and, for the
scene-conditioned model, the frozen Diffusion Planner encoder representation.
Teacher labels and actual-future trajectories are training/evaluation inputs
and are deliberately absent from this inference interface.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_v26_sparse_schema import (
    V26_ATOM_STATUS_VOCABULARY,
    V26_GLOBAL_ATOM_NAMES,
)


V26_TRANSITION_ATOM_NAME = "previous_plan_execution_transition_rms"
V26_CAMP_ATOM_NAMES = V26_GLOBAL_ATOM_NAMES + (V26_TRANSITION_ATOM_NAME,)
V26_CAMP_CANDIDATE_COUNT = 8
V26_CAMP_STATUS_PATTERN_COUNT = 24
V26_CAMP_NORMALIZED_ATOM_CLIP = 10.0
V26_DP_MASKED_TOKEN_TYPES = (
    "ego",
    "neighbor",
    "static",
    "lane",
    "route",
    "polygon",
    "line_string",
    "goal_pose",
    "ego_shape",
    "turn_indicator",
)


def load_camp_atom_scales(path: str | Path) -> dict[str, float]:
    """Load the frozen scales in the final 16-atom deployment order."""

    payload = json.loads(Path(path).resolve(strict=True).read_text(encoding="utf-8"))
    names = tuple(str(value) for value in payload.get("global_atom_names", ()))
    rows = tuple(payload.get("atom_rows", ()))
    if names != V26_CAMP_ATOM_NAMES or len(rows) != len(names):
        raise ValueError("CAMP scale file must use the frozen 16-atom order")
    scales = {str(row["atom_name"]): float(row["scale"]) for row in rows}
    if tuple(scales) != names:
        raise ValueError("CAMP scale rows must retain the frozen atom order")
    values = np.asarray(tuple(scales.values()), dtype=np.float64)
    if not np.all(np.isfinite(values)) or np.any(values <= 0.0):
        raise ValueError("CAMP atom scales must be finite and positive")
    return scales


def _as_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    return np.asarray(value)


def masked_mean_scene_embedding(
    encoder_tokens: Any,
    token_masks: Mapping[str, Any] | Sequence[Any],
) -> np.ndarray:
    """Pool the valid frozen-DP encoder tokens used by scene-conditioned CAMP."""

    tokens = np.asarray(_as_numpy(encoder_tokens), dtype=np.float64)
    if tokens.ndim == 3 and tokens.shape[0] == 1:
        tokens = tokens[0]
    if isinstance(token_masks, Mapping):
        masks = [token_masks[name] for name in V26_DP_MASKED_TOKEN_TYPES]
    else:
        masks = list(token_masks)
    mask = np.concatenate(
        [np.asarray(_as_numpy(value), dtype=bool).reshape(-1) for value in masks]
    )
    if tokens.ndim != 2 or tokens.shape[0] != mask.size:
        raise ValueError("Diffusion Planner token and mask layouts do not match")
    valid = ~mask
    if not np.any(valid):
        raise ValueError("Diffusion Planner scene representation has no valid token")
    pooled = np.asarray(tokens[valid].mean(axis=0), dtype=np.float64)
    if not np.all(np.isfinite(pooled)):
        raise ValueError("Diffusion Planner scene representation is non-finite")
    return pooled


def build_camp_atom_artifact(
    candidate_atom_values: Mapping[str, np.ndarray],
    endpoint_status: Mapping[str, str],
) -> dict[str, Any]:
    """Pack per-atom DP outputs without assigning numbers to unavailable atoms."""

    statuses = tuple(str(endpoint_status[name]) for name in V26_CAMP_ATOM_NAMES)
    if any(status not in V26_ATOM_STATUS_VOCABULARY for status in statuses):
        raise ValueError("CAMP endpoint status is invalid")
    observed_indices = tuple(
        index for index, status in enumerate(statuses) if status == "observed"
    )
    observed_names = tuple(V26_CAMP_ATOM_NAMES[index] for index in observed_indices)
    if set(candidate_atom_values) != set(observed_names):
        raise ValueError("CAMP atom values must be supplied exactly for observed endpoints")
    columns = [
        np.asarray(candidate_atom_values[name], dtype=np.float64).reshape(-1)
        for name in observed_names
    ]
    if any(column.shape != (V26_CAMP_CANDIDATE_COUNT,) for column in columns):
        raise ValueError("each observed CAMP atom must contain eight candidate values")
    raw = (
        np.column_stack(columns)
        if columns
        else np.empty((V26_CAMP_CANDIDATE_COUNT, 0), dtype=np.float64)
    )
    if not np.all(np.isfinite(raw)) or np.any(raw < 0.0):
        raise ValueError("observed CAMP atom values must be finite and nonnegative")
    return {
        "K": V26_CAMP_CANDIDATE_COUNT,
        "bank_atom_names": list(V26_CAMP_ATOM_NAMES),
        "atom_states": [
            {"name": name, "status": status}
            for name, status in zip(V26_CAMP_ATOM_NAMES, statuses)
        ],
        "observed_atom_names": list(observed_names),
        "observed_global_atom_indices": list(observed_indices),
        "candidate_atoms_raw": raw,
    }


@dataclass(frozen=True)
class CAMPRerankResult:
    """One CAMP decision over the original ordered candidate pool."""

    selected_row: int
    candidate_scores: np.ndarray
    active_weights: np.ndarray
    active_atom_names: tuple[str, ...]
    status_pattern: tuple[str, ...]
    pattern_index: int
    candidate_atoms_scaled: np.ndarray
    continuous_scene_representation_read: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "selected_row": self.selected_row,
            "candidate_scores": self.candidate_scores.copy(),
            "active_weights": self.active_weights.copy(),
            "active_atom_names": self.active_atom_names,
            "status_pattern": self.status_pattern,
            "pattern_index": self.pattern_index,
            "candidate_atoms_scaled": self.candidate_atoms_scaled.copy(),
            "continuous_scene_representation_read": (
                self.continuous_scene_representation_read
            ),
            "actual_future_read": False,
            "candidate_modified": False,
        }


@dataclass(frozen=True)
class _PatternHead:
    active_global_indices: tuple[int, ...]
    theta: np.ndarray
    pattern_index: int


class CAMPReranker:
    """Load one fixed-weight or scene-conditioned CAMP checkpoint and rerank K8."""

    def __init__(
        self,
        checkpoint_path: str | Path,
        atom_scales: Mapping[str, float] | str | Path,
    ) -> None:
        if isinstance(atom_scales, (str, Path)):
            scales = load_camp_atom_scales(atom_scales)
        else:
            scales = {name: float(atom_scales[name]) for name in V26_CAMP_ATOM_NAMES}
            values = np.asarray(tuple(scales.values()), dtype=np.float64)
            if not np.all(np.isfinite(values)) or np.any(values <= 0.0):
                raise ValueError("CAMP atom scales must be finite and positive")
        self.atom_scales = scales
        self.checkpoint_path = Path(checkpoint_path).resolve(strict=True)
        heads: dict[tuple[str, ...], _PatternHead] = {}
        feature_dimensions: set[int] = set()
        with np.load(self.checkpoint_path, allow_pickle=False) as payload:
            for key in sorted(name for name in payload.files if name.startswith("theta_")):
                suffix = key.removeprefix("theta_")
                pattern = tuple(str(value) for value in payload[f"status_pattern_{suffix}"])
                active = tuple(
                    int(value)
                    for value in payload[f"active_global_indices_{suffix}"]
                )
                theta = np.asarray(payload[key], dtype=np.float64)
                if len(pattern) != len(V26_CAMP_ATOM_NAMES):
                    raise ValueError("CAMP checkpoint status-pattern width changed")
                if active != tuple(
                    index for index, status in enumerate(pattern) if status == "observed"
                ):
                    raise ValueError("CAMP checkpoint active atom rows changed")
                if theta.ndim != 2 or theta.shape[0] != len(active):
                    raise ValueError("CAMP checkpoint head shape changed")
                if not np.all(np.isfinite(theta)):
                    raise ValueError("CAMP checkpoint contains non-finite weights")
                heads[pattern] = _PatternHead(active, theta.copy(), int(suffix))
                feature_dimensions.add(int(theta.shape[1]))
        if len(heads) != V26_CAMP_STATUS_PATTERN_COUNT:
            raise ValueError("CAMP checkpoint must contain the frozen 24 status heads")
        if len(feature_dimensions) != 1:
            raise ValueError("CAMP checkpoint heads disagree on feature dimension")
        self._heads = heads
        self._theta_width = feature_dimensions.pop()
        if self._theta_width in (1, 2):
            self.model_kind = "fixed"
            self.scene_embedding_dimension = None
        elif self._theta_width > 2:
            self.model_kind = "scene"
            self.scene_embedding_dimension = self._theta_width - 1
        else:
            raise ValueError("CAMP checkpoint has no affine intercept")

    def rerank_artifact(
        self,
        artifact: Mapping[str, Any],
        scene_embedding: np.ndarray | None = None,
    ) -> CAMPRerankResult:
        """Score and select one unchanged row from a deployable sparse atom artifact."""

        if tuple(artifact.get("bank_atom_names", ())) != V26_CAMP_ATOM_NAMES:
            raise ValueError("CAMP artifact must use the frozen 16-atom order")
        states = tuple(artifact.get("atom_states", ()))
        if len(states) != len(V26_CAMP_ATOM_NAMES):
            raise ValueError("CAMP artifact must retain all 16 endpoint states")
        state_names = tuple(str(row.get("name")) for row in states)
        pattern = tuple(str(row.get("status")) for row in states)
        if state_names != V26_CAMP_ATOM_NAMES or any(
            status not in V26_ATOM_STATUS_VOCABULARY for status in pattern
        ):
            raise ValueError("CAMP artifact endpoint names or statuses changed")
        active = tuple(int(value) for value in artifact.get("observed_global_atom_indices", ()))
        expected_active = tuple(
            index for index, status in enumerate(pattern) if status == "observed"
        )
        if active != expected_active:
            raise ValueError("CAMP artifact observed atom indices changed")
        names = tuple(str(value) for value in artifact.get("observed_atom_names", ()))
        expected_names = tuple(V26_CAMP_ATOM_NAMES[index] for index in active)
        if names != expected_names:
            raise ValueError("CAMP artifact observed atom names changed")
        raw = np.asarray(artifact.get("candidate_atoms_raw"), dtype=np.float64)
        if raw.shape != (V26_CAMP_CANDIDATE_COUNT, len(active)):
            raise ValueError("CAMP candidate atoms must have shape [8,Q_observed]")
        if not np.all(np.isfinite(raw)) or np.any(raw < 0.0):
            raise ValueError("CAMP candidate atoms must be finite and nonnegative")
        head = self._heads.get(pattern)
        if head is None or head.active_global_indices != active:
            raise ValueError("CAMP checkpoint has no head for this status pattern")

        if self.model_kind == "fixed":
            z = (
                np.ones(1, dtype=np.float64)
                if self._theta_width == 1
                else np.asarray([0.0, 1.0], dtype=np.float64)
            )
            continuous_read = False
        else:
            if scene_embedding is None:
                raise ValueError("scene-conditioned CAMP requires a scene embedding")
            vector = np.asarray(scene_embedding, dtype=np.float64).reshape(-1)
            if vector.shape != (self.scene_embedding_dimension,) or not np.all(
                np.isfinite(vector)
            ):
                raise ValueError(
                    "scene-conditioned CAMP embedding dimension or values changed"
                )
            z = np.concatenate((vector, np.ones(1, dtype=np.float64)))
            continuous_read = True

        weights = head.theta @ z
        if not np.all(np.isfinite(weights)):
            raise ValueError("CAMP produced non-finite raw affine weights")
        scale = np.asarray([self.atom_scales[name] for name in names], dtype=np.float64)
        atoms = np.clip(
            raw / scale[None, :],
            0.0,
            V26_CAMP_NORMALIZED_ATOM_CLIP,
        )
        scores = atoms @ weights
        selected = int(np.argmin(scores))
        return CAMPRerankResult(
            selected_row=selected,
            candidate_scores=scores,
            active_weights=weights,
            active_atom_names=names,
            status_pattern=pattern,
            pattern_index=head.pattern_index,
            candidate_atoms_scaled=atoms,
            continuous_scene_representation_read=continuous_read,
        )

    def select_candidates(
        self,
        candidates: np.ndarray,
        artifact: Mapping[str, Any],
        scene_embedding: np.ndarray | None = None,
    ) -> tuple[np.ndarray, CAMPRerankResult]:
        """Return an untouched copy of the selected DP candidate and its diagnostics."""

        values = np.asarray(candidates)
        if values.ndim < 1 or values.shape[0] != V26_CAMP_CANDIDATE_COUNT:
            raise ValueError("Diffusion Planner candidates must have K=8 on axis zero")
        result = self.rerank_artifact(artifact, scene_embedding)
        return values[result.selected_row].copy(), result


class CAMPDPRerankingPipeline:
    """Expose the final 50k fixed and scene CAMP checkpoints through one DP API."""

    def __init__(
        self,
        *,
        fixed_checkpoint_path: str | Path,
        scene_checkpoint_path: str | Path,
        atom_scales_path: str | Path,
    ) -> None:
        scales = load_camp_atom_scales(atom_scales_path)
        self.fixed = CAMPReranker(fixed_checkpoint_path, scales)
        self.scene = CAMPReranker(scene_checkpoint_path, scales)
        if self.fixed.model_kind != "fixed" or self.scene.model_kind != "scene":
            raise ValueError("CAMP deployment bundle has fixed/scene checkpoints swapped")

    @classmethod
    def from_directory(cls, directory: str | Path) -> "CAMPDPRerankingPipeline":
        root = Path(directory).resolve(strict=True)
        return cls(
            fixed_checkpoint_path=root / "fixed_weight_camp.npz",
            scene_checkpoint_path=root / "scene_conditioned_camp.npz",
            atom_scales_path=root / "atom_scales.json",
        )

    def select(
        self,
        *,
        mode: str,
        candidates: np.ndarray,
        artifact: Mapping[str, Any],
        scene_embedding: np.ndarray | None = None,
    ) -> tuple[np.ndarray, CAMPRerankResult]:
        if mode == "fixed":
            return self.fixed.select_candidates(candidates, artifact)
        if mode == "scene":
            return self.scene.select_candidates(candidates, artifact, scene_embedding)
        raise ValueError("CAMP mode must be 'fixed' or 'scene'")


__all__ = [
    "CAMPDPRerankingPipeline",
    "CAMPReranker",
    "CAMPRerankResult",
    "V26_CAMP_ATOM_NAMES",
    "V26_DP_MASKED_TOKEN_TYPES",
    "build_camp_atom_artifact",
    "load_camp_atom_scales",
    "masked_mean_scene_embedding",
]
