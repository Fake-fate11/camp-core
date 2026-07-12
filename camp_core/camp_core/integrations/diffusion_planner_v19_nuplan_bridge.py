from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
    validate_causal_dp_input,
)


BRIDGE_SCHEMA_VERSION = "dp_camp_v19_nuplan_bridge_v1"
_ARMS = frozenset({"dp_default", "camp"})
_FORMAL_SEEDS = frozenset({11, 12, 13})
_FORBIDDEN_KEY_PARTS = (
    "expert_future",
    "holdout",
    "label",
    "closed_loop_outcome",
    "safety_cost",
    "metric_result",
)


@dataclass(frozen=True)
class BridgeMessage:
    arrays: dict[str, np.ndarray]
    metadata: dict[str, Any]


def array_sha256(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def causal_input_sha256(data: Mapping[str, Any]) -> str:
    digest = hashlib.sha256()
    for key in sorted(data):
        array = np.ascontiguousarray(data[key])
        digest.update(key.encode("utf-8"))
        digest.update(b"\0")
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(b"\0")
        digest.update(json.dumps(list(array.shape), separators=(",", ":")).encode())
        digest.update(b"\0")
        digest.update(array.tobytes())
    return digest.hexdigest()


def paired_run_key(log_name: str, scenario_token: str, scenario_seed: int) -> str:
    if scenario_seed in _FORMAL_SEEDS:
        raise ValueError("formal seed is forbidden")
    if not log_name or not scenario_token:
        raise ValueError("log_name and scenario_token must be nonempty")
    payload = f"{log_name}\0{scenario_token}\0{int(scenario_seed)}".encode()
    return hashlib.sha256(payload).hexdigest()


def arm_run_key(pair_key: str, arm: str) -> str:
    _require_arm(arm)
    if len(pair_key) != 64:
        raise ValueError("pair_key must be a SHA256 digest")
    return f"{pair_key}:{arm}"


def build_request_metadata(
    *,
    arm: str,
    log_name: str,
    scenario_token: str,
    iteration_index: int,
    simulation_time_us: int,
    scenario_seed: int,
    dp_seed_root: int,
    camp_head: str,
    dp_head: str,
    nuplan_head: str,
    causal_input: Mapping[str, Any],
    selector_hashes: tuple[str, str, str] | None = None,
) -> dict[str, object]:
    _require_arm(arm)
    pair_key = paired_run_key(log_name, scenario_token, scenario_seed)
    if iteration_index < 0 or simulation_time_us < 0:
        raise ValueError("iteration and simulation time must be nonnegative")
    if dp_seed_root in _FORMAL_SEEDS:
        raise ValueError("formal seed is forbidden")
    seed_payload = f"{pair_key}\0{iteration_index}\0{dp_seed_root}".encode()
    tick_seed = int.from_bytes(hashlib.sha256(seed_payload).digest()[:4], "big")
    metadata: dict[str, object] = {
        "schema_version": BRIDGE_SCHEMA_VERSION,
        "arm": arm,
        "pair_run_key": pair_key,
        "run_key": arm_run_key(pair_key, arm),
        "log_name": log_name,
        "scenario_token": scenario_token,
        "iteration_index": int(iteration_index),
        "simulation_time_us": int(simulation_time_us),
        "scenario_seed": int(scenario_seed),
        "dp_seed_root": int(dp_seed_root),
        "tick_seed": tick_seed,
        "camp_head": camp_head,
        "dp_head": dp_head,
        "nuplan_head": nuplan_head,
        "causal_input_sha256": causal_input_sha256(causal_input),
        "native_ranked_top1": False,
    }
    if arm == "camp":
        if selector_hashes is None or len(selector_hashes) != 3:
            raise ValueError("CAMP requests require three selector hashes")
        metadata["selector_hashes"] = list(selector_hashes)
    elif selector_hashes is not None:
        raise ValueError("DP-default requests must not carry selector hashes")
    return metadata


def write_request(
    directory: str | Path,
    arrays: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> None:
    prepared = _validate_request(arrays, metadata)
    _write_message(Path(directory), "request", prepared, metadata)


def read_request(
    directory: str | Path,
    *,
    expected_run_key: str,
    expected_iteration_index: int,
) -> BridgeMessage:
    message = _read_message(Path(directory), "request")
    _require_identity(message.metadata, expected_run_key, expected_iteration_index)
    prepared = _validate_request(message.arrays, message.metadata)
    return BridgeMessage(prepared, message.metadata)


def write_response(
    directory: str | Path,
    arrays: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> None:
    prepared = _validate_response(arrays, metadata)
    _write_message(Path(directory), "response", prepared, metadata)


def read_response(
    directory: str | Path,
    *,
    expected_run_key: str,
    expected_iteration_index: int,
) -> BridgeMessage:
    message = _read_message(Path(directory), "response")
    _require_identity(message.metadata, expected_run_key, expected_iteration_index)
    prepared = _validate_response(message.arrays, message.metadata)
    return BridgeMessage(prepared, message.metadata)


def _validate_request(
    arrays: Mapping[str, Any], metadata: Mapping[str, Any]
) -> dict[str, np.ndarray]:
    _reject_forbidden_fields(metadata)
    prepared = {key: np.asarray(value) for key, value in arrays.items()}
    errors = validate_causal_dp_input(prepared)
    if errors:
        raise ValueError("invalid causal request: " + "; ".join(errors))
    _validate_common_metadata(metadata)
    if metadata.get("causal_input_sha256") != causal_input_sha256(prepared):
        raise ValueError("causal input SHA mismatch")
    arm = str(metadata["arm"])
    if arm == "camp" and len(metadata.get("selector_hashes", [])) != 3:
        raise ValueError("CAMP requests require three selector hashes")
    if arm == "dp_default" and "selector_hashes" in metadata:
        raise ValueError("DP-default requests must not carry selector hashes")
    return {key: _contiguous(value) for key, value in prepared.items()}


def _validate_response(
    arrays: Mapping[str, Any], metadata: Mapping[str, Any]
) -> dict[str, np.ndarray]:
    _reject_forbidden_fields(metadata)
    _validate_common_metadata(metadata)
    if metadata.get("native_ranked_top1") is not False:
        raise ValueError("native_ranked_top1 must remain false")
    status = metadata.get("status")
    if status not in {"ok", "failed"}:
        raise ValueError("response status must be ok or failed")
    prepared = {key: _contiguous(value) for key, value in arrays.items()}
    arm = str(metadata["arm"])
    if arm == "dp_default":
        _validate_default_response(prepared, metadata, status)
    else:
        _validate_camp_response(prepared, metadata, status)
    return prepared


def _validate_default_response(
    arrays: Mapping[str, np.ndarray], metadata: Mapping[str, Any], status: str
) -> None:
    allowed = {
        "selected_trajectory",
        "default_trajectory",
        "independent_reference_trajectory",
    }
    if set(arrays) - allowed:
        raise ValueError("unexpected DP-default response arrays")
    if status == "failed":
        if arrays:
            raise ValueError("failed DP-default response must contain no trajectory")
        return
    if "selected_trajectory" not in arrays:
        raise ValueError("DP-default response is missing selected trajectory")
    _validate_trajectory(arrays["selected_trajectory"])
    if metadata.get("baseline_name") != "DP-default deterministic/MAP baseline":
        raise ValueError("DP-default baseline name mismatch")
    _require_selected_sha(arrays["selected_trajectory"], metadata)


def _validate_camp_response(
    arrays: Mapping[str, np.ndarray], metadata: Mapping[str, Any], status: str
) -> None:
    required_evidence = {"candidates", "physical_feasible_mask"}
    if not required_evidence.issubset(arrays):
        raise ValueError("CAMP response is missing candidate evidence")
    candidates = arrays["candidates"]
    physical = arrays["physical_feasible_mask"]
    _require_array(candidates, (8, 80, 4), np.float32, "candidates")
    _require_array(physical, (8,), np.bool_, "physical_feasible_mask")
    before = metadata.get("candidate_sha256_before")
    after = metadata.get("candidate_sha256_after")
    actual = array_sha256(candidates)
    if before != after or before != actual:
        raise ValueError("candidate tensor mutated")
    reasons = metadata.get("candidate_reasons")
    if not isinstance(reasons, list) or len(reasons) != 8:
        raise ValueError("candidate reasons must contain all K records")
    if status == "failed":
        if "selected_trajectory" in arrays or "selected_index" in arrays:
            raise ValueError("failed CAMP response must not select a trajectory")
        if physical.any():
            raise ValueError("failed all-K response contains feasible candidates")
        return
    required = {
        "neighbor_predictions",
        "neighbor_valid_mask",
        "signal_mask",
        "atom_matrix",
        "selected_index",
        "selected_trajectory",
    }
    if not required.issubset(arrays):
        raise ValueError("successful CAMP response is incomplete")
    _require_array(arrays["neighbor_predictions"], (8, 32, 80, 4), np.float32, "neighbor_predictions")
    _require_array(arrays["neighbor_valid_mask"], (32,), np.bool_, "neighbor_valid_mask")
    _require_array(arrays["signal_mask"], (8,), np.bool_, "signal_mask")
    _require_array(arrays["atom_matrix"], (8, 14), np.float64, "atom_matrix")
    selected = arrays["selected_index"]
    if selected.shape != () or selected.dtype != np.int64:
        raise ValueError("selected_index must be scalar int64")
    index = int(selected)
    if not 0 <= index < 8 or not bool(physical[index]):
        raise ValueError("selected_index must identify a feasible candidate")
    trajectory = arrays["selected_trajectory"]
    _validate_trajectory(trajectory)
    if not np.array_equal(trajectory, candidates[index]):
        raise ValueError("selected trajectory is not the unchanged candidate")
    _require_selected_sha(trajectory, metadata)


def _validate_trajectory(array: np.ndarray) -> None:
    _require_array(array, (80, 4), np.float32, "selected_trajectory")


def _require_array(
    array: np.ndarray, shape: tuple[int, ...], dtype: Any, name: str
) -> None:
    if array.shape != shape or array.dtype != np.dtype(dtype):
        raise ValueError(f"{name} must have shape {shape} and dtype {np.dtype(dtype)}")
    if array.dtype.kind in "fc" and not np.isfinite(array).all():
        raise ValueError(f"{name} must be finite")


def _contiguous(value: Any) -> np.ndarray:
    array = np.asarray(value)
    return array.copy() if array.ndim == 0 else np.ascontiguousarray(array)


def _require_selected_sha(
    trajectory: np.ndarray, metadata: Mapping[str, Any]
) -> None:
    if metadata.get("selected_trajectory_sha256") != array_sha256(trajectory):
        raise ValueError("selected trajectory SHA mismatch")


def _validate_common_metadata(metadata: Mapping[str, Any]) -> None:
    if metadata.get("schema_version") != BRIDGE_SCHEMA_VERSION:
        raise ValueError("bridge schema version mismatch")
    _require_arm(str(metadata.get("arm")))
    if not isinstance(metadata.get("run_key"), str) or not metadata["run_key"]:
        raise ValueError("run_key must be nonempty")
    index = metadata.get("iteration_index")
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise ValueError("iteration_index must be a nonnegative integer")


def _require_identity(
    metadata: Mapping[str, Any], expected_run_key: str, expected_iteration_index: int
) -> None:
    if metadata.get("run_key") != expected_run_key:
        raise ValueError("run key mismatch")
    if metadata.get("iteration_index") != expected_iteration_index:
        raise ValueError("iteration mismatch")


def _reject_forbidden_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in _FORBIDDEN_KEY_PARTS):
                raise ValueError(f"forbidden online field: {key}")
            _reject_forbidden_fields(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_forbidden_fields(item)


def _require_arm(arm: str) -> None:
    if arm not in _ARMS:
        raise ValueError(f"arm must be one of {sorted(_ARMS)}")


def _write_message(
    directory: Path,
    stem: str,
    arrays: Mapping[str, np.ndarray],
    metadata: Mapping[str, Any],
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    npz_path = directory / f"{stem}.npz"
    json_path = directory / f"{stem}.json"
    if npz_path.exists() or json_path.exists():
        raise FileExistsError(f"{stem} bridge message already exists")
    npz_tmp = directory / f"{stem}.npz.tmp"
    json_tmp = directory / f"{stem}.json.tmp"
    with npz_tmp.open("wb") as stream:
        np.savez(stream, **arrays)
        stream.flush()
        os.fsync(stream.fileno())
    npz_tmp.replace(npz_path)
    with json_tmp.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(dict(metadata), stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    json_tmp.replace(json_path)


def _read_message(directory: Path, stem: str) -> BridgeMessage:
    json_path = directory / f"{stem}.json"
    npz_path = directory / f"{stem}.npz"
    if not json_path.is_file():
        raise FileNotFoundError(f"{stem}.json readiness marker is missing")
    if not npz_path.is_file():
        raise FileNotFoundError(f"{stem}.npz payload is missing")
    metadata = json.loads(json_path.read_text(encoding="utf-8"))
    with np.load(npz_path, allow_pickle=False) as payload:
        arrays = {key: _contiguous(payload[key]) for key in payload.files}
    return BridgeMessage(arrays, metadata)
