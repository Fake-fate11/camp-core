from __future__ import annotations

import hashlib
import json
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


def _as_c_array(value: Any) -> np.ndarray:
    array = np.asarray(value)
    if array.ndim and not array.flags.c_contiguous:
        return np.ascontiguousarray(array)
    return array
