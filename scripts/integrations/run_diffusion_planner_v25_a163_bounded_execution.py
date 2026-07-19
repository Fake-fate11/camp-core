#!/usr/bin/env python3
"""Execute only a sealed A1.6.10 bounded plan after an Ultra one-shot release."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Iterator, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
)
from camp_core.integrations.diffusion_planner_v21_native import (  # noqa: E402
    array_sha256,
)
from camp_core.integrations.diffusion_planner_v25_a162_bounded_execution import (  # noqa: E402
    RUN_EVIDENCE_SCHEMA_VERSION,
    TICKS_PER_RUN,
    canonical_sha256,
    validate_bounded_terminal_acceptance,
)
from camp_core.integrations.diffusion_planner_v25_a163_bounded_authority import (  # noqa: E402
    A17_DIAGNOSTIC_RELEASE_GATE,
    EXPECTED_DEVICE,
    EXPECTED_RUNS,
    EXPECTED_TICKS,
    EXPECTED_UNIQUE_IDENTITIES,
    FIXED_DP_HEAD,
    verify_a17_diagnostic_release,
    verify_bounded_release,
)
from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (  # noqa: E402
    V25ControlledSceneAdapter,
)
from camp_core.integrations.diffusion_planner_v25_causal_evidence_store import (  # noqa: E402
    externalize_causal_evidence,
)
from camp_core.integrations.diffusion_planner_v25_snapshot_store import (  # noqa: E402
    SNAPSHOT_SUFFIX,
    encode_snapshot,
)
from scripts.integrations import (  # noqa: E402
    run_diffusion_planner_v25_controlled_training_corpus as corpus,
)


SCHEMA_VERSION = "camp_dp_v25_a1610_bounded_execution_v8"
SNAPSHOT_SCHEMA_VERSION = "camp_dp_v25_a17_bounded_snapshot_v7"
INDEX_SCHEMA_VERSION = "camp_dp_v25_a163_bounded_snapshot_index_row_v1"
RESULT_SCHEMA_VERSION = "camp_dp_v25_a163_bounded_result_v1"
FAILURE_SCHEMA_VERSION = "camp_dp_v25_a163_bounded_failure_v1"
A17_DIAGNOSTIC_EXECUTION_SCHEMA_VERSION = (
    "camp_dp_v25_a17_preprojection_diagnostic_execution_v1"
)
A17_DIAGNOSTIC_FAILURE_SCHEMA_VERSION = (
    "camp_dp_v25_a17_preprojection_diagnostic_failure_v1"
)
TRAIN_LOCK = Path("/root/autodl-tmp/.camp_dp_v25_controlled_train_corpus.lock")
MINIMUM_FREE_BYTES = 10 * 1024**3

PUBLIC_TICK_FIELDS = {
    "tick_index", "status", "scene_materialization_sha256", "padding", "tracker", "safety",
    "latency_ms", "pre_decision_speed_mps", "default_output_sha256", "candidate_tensor_sha256_before",
    "candidate_tensor_sha256_after", "candidate_neighbor_sha256",
    "selected_trajectory_sha256", "global_rng_sha256_before",
    "global_rng_sha256_after", "causal_evidence_sha256", "route_lanes_sha256",
    "route_lanes_speed_limit_sha256", "route_lanes_has_speed_limit_sha256",
    "candidate_row_sha256", "selection_policy", "score_contract",
    "tie_break_contract", "eligibility_mask_name", "selected_index",
    "default_candidate0_identity", "atom_matrix_sha256",
    "normalized_atom_matrix_sha256", "npc_operational_outputs_unchanged",
    "scores", "physical_feasible_mask", "source_valid_mask",
    "source_complete_mask", "candidate_reasons", "all_k_high_risk",
    "controlled_scene", "v25_context",
}
SAFETY_FIELDS = {
    "tick_index", "position_xy", "speed_mps", "ego_heading_rad",
    "route_heading_rad", "route_progress_m", "five_point_drivable_coverage",
    "min_obb_clearance_m", "red_light_at_interval_start",
    "front_center_prev_xy", "front_center_xy", "red_stop_lines",
    "speed_limit_mps", "constant_velocity_circle_ttc_diagnostic_s",
    "source_complete",
}
LATENCY_FIELDS = {
    "input_materialization", "default_inference", "candidate_inference",
    "atom_materialization", "selector", "hook_total", "tracker", "total_planning",
}
NATIVE_RECEIPT_FIELDS = {
    "schema_version", "status", "route_name", "route_sha256",
    "logical_map_sha256", "fixed_dp_head", "checkpoint_sha256", "args_sha256",
    "arm", "scenario_seed", "spawn_config_sha256", "initial_world_state_sha256",
    "initial_scene_materialization_sha256", "ticks", "native_result", "claim_authorized",
    "selector_scale_contract", "runtime_annotation_compatibility",
    "causal_scene_materialization_evidence",
}
SCENE_MATERIALIZATION_EVIDENCE_SCHEMA_VERSION = (
    "camp_dp_v25_a1610_causal_scene_materialization_evidence_v2"
)
SCENE_MATERIALIZATION_EVIDENCE_FIELDS = {
    "schema_version", "relative_path", "sha256", "tick_count", "arrays",
}
PREPROJECTION_EVIDENCE_SCHEMA_VERSION = (
    "camp_dp_v25_a17_preprojection_digest_evidence_v1"
)
PREPROJECTION_EVIDENCE_FIELDS = {
    "schema_version", "run_ordinal", "occurrence", "native_tick_indices",
    "native_causal_receipts", "native_input_sha256_sequence",
    "materialization_sha256_sequence", "materialization_evidence",
    "mismatch_indices", "first_mismatch",
    "accepted_as_scientific_evidence", "full_r_execute_authorized",
    "training_executed", "calibration_executed", "fresh_b2_opened",
    "outcome_fields_consumed",
}
PREPROJECTION_NATIVE_TICK_FIELDS = {
    "tick_index", "input_sha256", "arrays", "padding",
}
PREPROJECTION_PADDING_FIELDS = {
    "source_observed_frames", "observed_frames", "padded_frames",
    "truncated_frames", "padding_policy",
}
PREPROJECTION_FIRST_MISMATCH_FIELDS = {
    "tick_index", "native_input_sha256", "materialization_sha256",
    "first_different_array",
}
PREPROJECTION_ARRAY_DIFFERENCE_FIELDS = {
    "name", "native", "materialization",
}
CANDIDATE_PREMATERIALIZATION_SCHEMA_VERSION = (
    "camp_dp_v25_a17_candidate_prematerialization_evidence_v1"
)
CANDIDATE_PREMATERIALIZATION_FIELDS = {
    "schema_version", "run_ordinal", "occurrence", "tick_index",
    "candidate_tensor_relative_path", "candidate_tensor_file_sha256",
    "candidate_tensor_sha256", "candidate_row_sha256",
    "default_output_sha256", "default_candidate0_identity", "shape", "dtype",
    "all_finite", "heading_norm_min", "heading_norm_max",
    "heading_norm_below_half_count", "accepted_as_scientific_evidence",
    "full_r_execute_authorized", "training_executed", "calibration_executed",
    "fresh_b2_opened", "outcome_fields_consumed",
}
CANDIDATE_PREMATERIALIZATION_METADATA_FIELDS = {
    "candidate_tensor_sha256", "candidate_row_sha256", "default_output_sha256",
    "default_candidate0_identity",
}
DEFAULT_CANDIDATE0_IDENTITY_FIELDS = {
    "elementwise_equal", "max_abs_difference", "default_output_sha256",
    "candidate0_sha256", "native_ranked_k8",
}
CAUSAL_RECEIPT_FIELDS = {
    "source_observed_frames", "observed_frames", "padded_frames",
    "truncated_frames", "padding_policy", "arrays", "input_sha256",
}
CAUSAL_ARRAY_RECEIPT_FIELDS = {"shape", "dtype", "sha256"}
SCENE_MATERIALIZATION_ARRAY_SCHEMA = {
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
INITIAL_WORLD_STATE_SCHEMA_VERSION = "camp_dp_v25_a1610_initial_world_state_v2"
EXPECTED_SELECTOR_SCALE_CONTRACT = {
    "declared_atom_schema_version": "dp_camp_v10_14d",
    "effective_atom_schema_version": "dp_camp_v10_14d",
    "compatibility_policy": "exact_atom_names_on_frozen_sha_v1",
}
EXPECTED_RUNTIME_ANNOTATION_COMPATIBILITY = "not_required_python310_or_newer"
EXPECTED_FIXED_DP_CHECKPOINT_SHA256 = (
    "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75"
)
EXPECTED_FIXED_DP_ARGS_SHA256 = (
    "42c1174de7db49d20343d9ff155093ee206ea9fb31bf0fa7185b108e36c66caa"
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_json_bytes(value))


def _write_json_atomic(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    _write_json(temporary, value)
    temporary.replace(path)


def _write_jsonl_row(handle: Any, value: Any) -> None:
    handle.write(
        (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        )
    )


def _deterministic_array_mapping_sha256(data: Mapping[str, Any]) -> str:
    """Producer-side digest for the saved causal scene materialization."""

    digest = hashlib.sha256()
    for key in sorted(data):
        if type(key) is not str:
            raise ValueError("scene materialization array keys must be strings")
        array = np.asarray(data[key])
        # Match the native boundary exactly: a 0-D scalar remains shape [],
        # while only non-contiguous arrays with at least one dimension are
        # copied into C order.  np.ascontiguousarray() would promote a scalar
        # to shape [1] and change the mapping digest despite identical bytes.
        if array.ndim and not array.flags.c_contiguous:
            array = np.ascontiguousarray(array)
        if array.dtype.hasobject:
            raise ValueError(
                f"scene materialization object dtype is forbidden for {key}"
            )
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


def _validated_scene_materialization(
    value: Mapping[str, Any], *, tick_index: int
) -> dict[str, np.ndarray]:
    if type(value) is not dict or set(value) != set(SCENE_MATERIALIZATION_ARRAY_SCHEMA):
        raise ValueError("bounded scene materialization exact array set drifted")
    result: dict[str, np.ndarray] = {}
    for name, (shape, dtype_name) in SCENE_MATERIALIZATION_ARRAY_SCHEMA.items():
        array = np.asarray(value[name])
        expected_dtype = np.dtype(dtype_name)
        if array.shape != shape or array.dtype != expected_dtype:
            raise ValueError(
                f"bounded scene materialization {name} dtype/shape drifted at tick {tick_index}"
            )
        if not np.isfinite(array).all():
            raise ValueError(
                f"bounded scene materialization {name} is nonfinite at tick {tick_index}"
            )
        result[name] = np.array(array, copy=True, order="C")
    return result


def _write_scene_materialization_evidence(
    *, output_dir: Path, run: Mapping[str, Any], rows: list[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[str]]:
    if len(rows) != TICKS_PER_RUN:
        raise ValueError("bounded scene materialization evidence must contain exactly 64 ticks")
    validated = [
        _validated_scene_materialization(row, tick_index=index)
        for index, row in enumerate(rows)
    ]
    stacked = {
        name: np.stack([row[name] for row in validated], axis=0)
        for name in sorted(SCENE_MATERIALIZATION_ARRAY_SCHEMA)
    }
    evidence_dir = output_dir / "causal_scene_materializations"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    temporary = evidence_dir / (
        f"run_{int(run['run_ordinal']):03d}_{run['occurrence']}.tmp.npz"
    )
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **stacked)
        handle.flush()
    data = temporary.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    target = evidence_dir / f"{digest}.npz"
    if target.exists():
        if target.is_symlink() or target.read_bytes() != data:
            raise ValueError("bounded scene materialization content-address collision")
        temporary.unlink()
    else:
        temporary.replace(target)
    hashes = [_deterministic_array_mapping_sha256(row) for row in validated]
    arrays = {
        name: {
            "dtype": array.dtype.str,
            "shape": list(array.shape),
            "sha256": hashlib.sha256(
                np.ascontiguousarray(array).tobytes()
            ).hexdigest(),
        }
        for name, array in stacked.items()
    }
    return (
        {
            "schema_version": SCENE_MATERIALIZATION_EVIDENCE_SCHEMA_VERSION,
            "relative_path": target.relative_to(output_dir).as_posix(),
            "sha256": digest,
            "tick_count": TICKS_PER_RUN,
            "arrays": arrays,
        },
        hashes,
    )


def _strict_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate native JSON key is forbidden: {key}")
        result[key] = value
    return result


def _load_native_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"nonfinite native JSON constant is forbidden: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"bounded native JSON is not strict: {path}") from exc


def _load_canonical_json(path: Path) -> Any:
    raw = path.read_bytes()
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_object_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"nonfinite canonical JSON constant is forbidden: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"bounded canonical JSON is not strict: {path}") from exc
    if raw != _canonical_json_bytes(value):
        raise ValueError(f"bounded canonical JSON bytes drifted: {path}")
    return value


def _write_candidate_prematerialization_evidence(
    *,
    output_dir: Path,
    run: Mapping[str, Any],
    tick_index: int,
    candidates: np.ndarray,
    metadata: Mapping[str, Any],
) -> Path:
    """Persist exact fixed-K8 preimage before atom materialization can fail."""

    run_ordinal = _require_plain_int(
        run.get("run_ordinal"), label="candidate evidence run ordinal"
    )
    occurrence = run.get("occurrence")
    if type(occurrence) is not str or not occurrence:
        raise ValueError("candidate evidence occurrence must be a nonempty string")
    tick = _require_plain_int(tick_index, label="candidate evidence tick index")
    if tick >= TICKS_PER_RUN:
        raise ValueError("candidate evidence tick index exceeds the 64-tick contract")
    if type(metadata) is not dict or set(metadata) != CANDIDATE_PREMATERIALIZATION_METADATA_FIELDS:
        raise ValueError("candidate evidence metadata exact schema drifted")

    tensor = np.asarray(candidates)
    if tensor.shape != (8, 80, 4) or tensor.dtype != np.float32:
        raise ValueError("candidate evidence tensor must be float32 [8,80,4]")
    tensor = np.array(tensor, dtype=np.float32, copy=True, order="C")
    tensor_sha = array_sha256(tensor)
    row_sha = metadata.get("candidate_row_sha256")
    default_sha = metadata.get("default_output_sha256")
    identity = metadata.get("default_candidate0_identity")
    if (
        metadata.get("candidate_tensor_sha256") != tensor_sha
        or type(row_sha) is not list
        or len(row_sha) != 8
        or any(type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value) for value in row_sha)
        or row_sha != [array_sha256(tensor[index]) for index in range(8)]
        or type(default_sha) is not str
        or re.fullmatch(r"[0-9a-f]{64}", default_sha) is None
        or type(identity) is not dict
        or set(identity) != DEFAULT_CANDIDATE0_IDENTITY_FIELDS
        or identity.get("elementwise_equal") is not True
        or type(identity.get("max_abs_difference")) is not float
        or identity.get("max_abs_difference") != 0.0
        or identity.get("native_ranked_k8") is not False
        or identity.get("default_output_sha256") != default_sha
        or identity.get("candidate0_sha256") != row_sha[0]
        or default_sha != row_sha[0]
    ):
        raise ValueError("candidate evidence same-forward metadata drifted")

    directory = (
        output_dir
        / "candidate_prematerialization"
        / f"run_{run_ordinal:03d}_{occurrence}"
    )
    directory.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    np.save(buffer, tensor, allow_pickle=False)
    tensor_bytes = buffer.getvalue()
    file_sha = hashlib.sha256(tensor_bytes).hexdigest()
    tensor_path = directory / f"tick_{tick:02d}_{file_sha}.npy"
    temporary_tensor = tensor_path.with_name(tensor_path.name + ".tmp")
    temporary_tensor.write_bytes(tensor_bytes)
    temporary_tensor.replace(tensor_path)

    finite = bool(np.isfinite(tensor).all())
    if finite:
        heading_norms = np.linalg.norm(tensor[:, :, 2:4].astype(np.float64), axis=2)
        heading_min: float | None = float(np.min(heading_norms))
        heading_max: float | None = float(np.max(heading_norms))
        below_half: int | None = int(np.count_nonzero(heading_norms < 0.5))
    else:
        heading_min = None
        heading_max = None
        below_half = None
    record = {
        "schema_version": CANDIDATE_PREMATERIALIZATION_SCHEMA_VERSION,
        "run_ordinal": run_ordinal,
        "occurrence": occurrence,
        "tick_index": tick,
        "candidate_tensor_relative_path": tensor_path.relative_to(output_dir).as_posix(),
        "candidate_tensor_file_sha256": file_sha,
        "candidate_tensor_sha256": tensor_sha,
        "candidate_row_sha256": list(row_sha),
        "default_output_sha256": default_sha,
        "default_candidate0_identity": json.loads(json.dumps(identity)),
        "shape": [8, 80, 4],
        "dtype": tensor.dtype.str,
        "all_finite": finite,
        "heading_norm_min": heading_min,
        "heading_norm_max": heading_max,
        "heading_norm_below_half_count": below_half,
        "accepted_as_scientific_evidence": False,
        "full_r_execute_authorized": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    record_path = directory / f"tick_{tick:02d}.json"
    _write_json_atomic(record_path, record)

    reopened = _load_canonical_json(record_path)
    if type(reopened) is not dict or set(reopened) != CANDIDATE_PREMATERIALIZATION_FIELDS:
        raise ValueError("candidate prematerialization evidence exact schema drifted")
    reopened_tensor = np.load(tensor_path, allow_pickle=False)
    if (
        tensor_path.read_bytes() != tensor_bytes
        or hashlib.sha256(tensor_path.read_bytes()).hexdigest() != reopened["candidate_tensor_file_sha256"]
        or reopened_tensor.shape != (8, 80, 4)
        or reopened_tensor.dtype != np.float32
        or not np.array_equal(reopened_tensor, tensor, equal_nan=True)
        or array_sha256(reopened_tensor) != reopened["candidate_tensor_sha256"]
        or reopened != record
    ):
        raise ValueError("candidate prematerialization evidence reopen drifted")
    return record_path


def _require_plain_int(value: Any, *, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be a native integer >= {minimum}")
    return value


def _require_sha256(value: Any, *, label: str) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{label} must be a lowercase SHA256 digest")
    return value


def _validated_causal_receipt_metadata(
    value: Mapping[str, Any], *, tick_index: int
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != CAUSAL_RECEIPT_FIELDS:
        raise ValueError(
            f"bounded native causal receipt schema drifted at tick {tick_index}"
        )
    source_frames = _require_plain_int(
        value.get("source_observed_frames"),
        label="native causal source_observed_frames",
        minimum=1,
    )
    observed = _require_plain_int(
        value.get("observed_frames"), label="native causal observed_frames"
    )
    padded = _require_plain_int(
        value.get("padded_frames"), label="native causal padded_frames"
    )
    truncated = _require_plain_int(
        value.get("truncated_frames"), label="native causal truncated_frames"
    )
    if (
        observed != min(source_frames, 31)
        or padded != 31 - observed
        or truncated != max(source_frames - 31, 0)
        or value.get("padding_policy") != "native_zero_left_pad_to_31_v1"
    ):
        raise ValueError(
            f"bounded native causal padding contract drifted at tick {tick_index}"
        )
    arrays = value.get("arrays")
    if type(arrays) is not dict or set(arrays) != set(
        SCENE_MATERIALIZATION_ARRAY_SCHEMA
    ):
        raise ValueError(
            f"bounded native causal array key set drifted at tick {tick_index}"
        )
    normalized_arrays: dict[str, dict[str, Any]] = {}
    for name, (shape, dtype_name) in SCENE_MATERIALIZATION_ARRAY_SCHEMA.items():
        receipt = arrays.get(name)
        if (
            type(receipt) is not dict
            or set(receipt) != CAUSAL_ARRAY_RECEIPT_FIELDS
            or receipt.get("shape") != list(shape)
            or receipt.get("dtype") != np.dtype(dtype_name).str
        ):
            raise ValueError(
                f"bounded native causal array metadata drifted for {name} "
                f"at tick {tick_index}"
            )
        normalized_arrays[name] = {
            "shape": list(shape),
            "dtype": np.dtype(dtype_name).str,
            "sha256": _require_sha256(
                receipt.get("sha256"),
                label=f"native causal {name} bytes SHA256",
            ),
        }
    return {
        "source_observed_frames": source_frames,
        "observed_frames": observed,
        "padded_frames": padded,
        "truncated_frames": truncated,
        "padding_policy": "native_zero_left_pad_to_31_v1",
        "arrays": normalized_arrays,
        "input_sha256": _require_sha256(
            value.get("input_sha256"), label="native causal input SHA256"
        ),
    }


def _validated_scene_materialization_reference(
    value: Mapping[str, Any], *, output_dir: Path
) -> tuple[dict[str, Any], list[str], list[dict[str, dict[str, Any]]]]:
    if (
        type(value) is not dict
        or set(value) != SCENE_MATERIALIZATION_EVIDENCE_FIELDS
        or value.get("schema_version")
        != SCENE_MATERIALIZATION_EVIDENCE_SCHEMA_VERSION
        or value.get("tick_count") != TICKS_PER_RUN
        or type(value.get("tick_count")) is not int
    ):
        raise ValueError("bounded scene materialization reference schema drifted")
    digest = _require_sha256(
        value.get("sha256"), label="scene materialization NPZ SHA256"
    )
    relative = value.get("relative_path")
    expected_relative = f"causal_scene_materializations/{digest}.npz"
    if type(relative) is not str or relative != expected_relative:
        raise ValueError("bounded scene materialization reference path drifted")
    arrays = value.get("arrays")
    if type(arrays) is not dict or set(arrays) != set(
        SCENE_MATERIALIZATION_ARRAY_SCHEMA
    ):
        raise ValueError("bounded scene materialization reference arrays drifted")
    normalized_arrays: dict[str, dict[str, Any]] = {}
    for name, (shape, dtype_name) in SCENE_MATERIALIZATION_ARRAY_SCHEMA.items():
        receipt = arrays.get(name)
        expected_shape = [TICKS_PER_RUN, *shape]
        if (
            type(receipt) is not dict
            or set(receipt) != CAUSAL_ARRAY_RECEIPT_FIELDS
            or receipt.get("shape") != expected_shape
            or receipt.get("dtype") != np.dtype(dtype_name).str
        ):
            raise ValueError(
                f"bounded scene materialization reference metadata drifted for {name}"
            )
        normalized_arrays[name] = {
            "shape": expected_shape,
            "dtype": np.dtype(dtype_name).str,
            "sha256": _require_sha256(
                receipt.get("sha256"),
                label=f"scene materialization {name} stack SHA256",
            ),
        }
    path = output_dir / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("bounded scene materialization NPZ is unavailable")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("bounded scene materialization NPZ digest drifted")
    try:
        with np.load(path, allow_pickle=False) as archive:
            if set(archive.files) != set(SCENE_MATERIALIZATION_ARRAY_SCHEMA):
                raise ValueError("bounded scene materialization NPZ key set drifted")
            stacked = {
                name: np.array(archive[name], copy=True)
                for name in SCENE_MATERIALIZATION_ARRAY_SCHEMA
            }
    except (OSError, ValueError) as exc:
        raise ValueError("bounded scene materialization NPZ is invalid") from exc
    for name, (shape, dtype_name) in SCENE_MATERIALIZATION_ARRAY_SCHEMA.items():
        array = stacked[name]
        if (
            array.shape != (TICKS_PER_RUN, *shape)
            or array.dtype != np.dtype(dtype_name)
            or not np.isfinite(array).all()
            or hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()
            != normalized_arrays[name]["sha256"]
        ):
            raise ValueError(
                f"bounded scene materialization NPZ array drifted for {name}"
            )
    tick_hashes: list[str] = []
    tick_arrays: list[dict[str, dict[str, Any]]] = []
    for tick_index in range(TICKS_PER_RUN):
        row = {name: stacked[name][tick_index] for name in stacked}
        tick_hashes.append(_deterministic_array_mapping_sha256(row))
        tick_arrays.append(
            {
                name: {
                    "shape": list(row[name].shape),
                    "dtype": row[name].dtype.str,
                    "sha256": hashlib.sha256(
                        np.ascontiguousarray(row[name]).tobytes()
                    ).hexdigest(),
                }
                for name in sorted(row)
            }
        )
    normalized = {
        "schema_version": SCENE_MATERIALIZATION_EVIDENCE_SCHEMA_VERSION,
        "relative_path": relative,
        "sha256": digest,
        "tick_count": TICKS_PER_RUN,
        "arrays": normalized_arrays,
    }
    return normalized, tick_hashes, tick_arrays


def _first_array_difference(
    native_arrays: Mapping[str, Any], materialization_arrays: Mapping[str, Any]
) -> dict[str, Any] | None:
    for name in sorted(SCENE_MATERIALIZATION_ARRAY_SCHEMA):
        if native_arrays[name] != materialization_arrays[name]:
            return {
                "name": name,
                "native": dict(native_arrays[name]),
                "materialization": dict(materialization_arrays[name]),
            }
    return None


def _expected_preprojection_mismatch(
    *,
    native_receipts: list[Mapping[str, Any]],
    materialization_hashes: list[str],
    materialization_arrays: list[Mapping[str, Any]],
) -> tuple[list[int], dict[str, Any] | None]:
    mismatches: list[int] = []
    first: dict[str, Any] | None = None
    for tick_index in range(TICKS_PER_RUN):
        native = native_receipts[tick_index]
        different_array = _first_array_difference(
            native["arrays"], materialization_arrays[tick_index]
        )
        if (
            native["input_sha256"] != materialization_hashes[tick_index]
            or different_array is not None
        ):
            mismatches.append(tick_index)
            if first is None:
                first = {
                    "tick_index": tick_index,
                    "native_input_sha256": native["input_sha256"],
                    "materialization_sha256": materialization_hashes[tick_index],
                    "first_different_array": different_array,
                }
    return mismatches, first


def _validate_preprojection_digest_evidence(
    value: Mapping[str, Any], *, output_dir: Path
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != PREPROJECTION_EVIDENCE_FIELDS:
        raise ValueError("bounded preprojection evidence exact schema drifted")
    if value.get("schema_version") != PREPROJECTION_EVIDENCE_SCHEMA_VERSION:
        raise ValueError("bounded preprojection evidence version drifted")
    run_ordinal = _require_plain_int(
        value.get("run_ordinal"), label="preprojection run ordinal"
    )
    occurrence = value.get("occurrence")
    if (
        type(occurrence) is not str
        or re.fullmatch(r"[a-z0-9_]+", occurrence) is None
    ):
        raise ValueError("bounded preprojection occurrence drifted")
    tick_indices = value.get("native_tick_indices")
    if (
        type(tick_indices) is not list
        or any(type(item) is not int for item in tick_indices)
        or tick_indices != list(range(TICKS_PER_RUN))
    ):
        raise ValueError("bounded preprojection native tick order drifted")
    receipts = value.get("native_causal_receipts")
    if type(receipts) is not list or len(receipts) != TICKS_PER_RUN:
        raise ValueError("bounded preprojection native receipt count drifted")
    normalized_receipts: list[dict[str, Any]] = []
    for tick_index, record in enumerate(receipts):
        if (
            type(record) is not dict
            or set(record) != PREPROJECTION_NATIVE_TICK_FIELDS
            or record.get("tick_index") != tick_index
            or type(record.get("tick_index")) is not int
            or type(record.get("padding")) is not dict
            or set(record["padding"]) != PREPROJECTION_PADDING_FIELDS
        ):
            raise ValueError(
                f"bounded preprojection native tick schema drifted at {tick_index}"
            )
        flat = {
            **record["padding"],
            "arrays": record.get("arrays"),
            "input_sha256": record.get("input_sha256"),
        }
        validated = _validated_causal_receipt_metadata(flat, tick_index=tick_index)
        normalized_receipts.append(validated)
    native_sequence = value.get("native_input_sha256_sequence")
    if (
        type(native_sequence) is not list
        or len(native_sequence) != TICKS_PER_RUN
        or any(type(item) is not str for item in native_sequence)
        or native_sequence
        != [receipt["input_sha256"] for receipt in normalized_receipts]
    ):
        raise ValueError("bounded preprojection native SHA sequence drifted")
    reference, materialization_hashes, materialization_arrays = (
        _validated_scene_materialization_reference(
            value.get("materialization_evidence"), output_dir=output_dir
        )
    )
    if value.get("materialization_sha256_sequence") != materialization_hashes:
        raise ValueError("bounded preprojection materialization SHA sequence drifted")
    mismatches, first = _expected_preprojection_mismatch(
        native_receipts=normalized_receipts,
        materialization_hashes=materialization_hashes,
        materialization_arrays=materialization_arrays,
    )
    if (
        value.get("mismatch_indices") != mismatches
        or value.get("first_mismatch") != first
    ):
        raise ValueError("bounded preprojection mismatch localization drifted")
    if first is not None:
        if set(first) != PREPROJECTION_FIRST_MISMATCH_FIELDS:
            raise ValueError("bounded preprojection first mismatch schema drifted")
        different = first["first_different_array"]
        if different is not None and (
            type(different) is not dict
            or set(different) != PREPROJECTION_ARRAY_DIFFERENCE_FIELDS
        ):
            raise ValueError("bounded preprojection array difference schema drifted")
    expected_gates = {
        "accepted_as_scientific_evidence": False,
        "full_r_execute_authorized": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    for name, expected in expected_gates.items():
        if type(value.get(name)) is not type(expected) or value.get(name) != expected:
            raise ValueError(f"bounded preprojection gate drifted: {name}")
    return {
        "schema_version": PREPROJECTION_EVIDENCE_SCHEMA_VERSION,
        "run_ordinal": run_ordinal,
        "occurrence": occurrence,
        "native_tick_indices": list(range(TICKS_PER_RUN)),
        "native_causal_receipts": [
            {
                "tick_index": tick_index,
                "input_sha256": receipt["input_sha256"],
                "arrays": receipt["arrays"],
                "padding": {
                    name: receipt[name]
                    for name in PREPROJECTION_PADDING_FIELDS
                },
            }
            for tick_index, receipt in enumerate(normalized_receipts)
        ],
        "native_input_sha256_sequence": list(native_sequence),
        "materialization_sha256_sequence": materialization_hashes,
        "materialization_evidence": reference,
        "mismatch_indices": mismatches,
        "first_mismatch": first,
        **expected_gates,
    }


def _write_preprojection_digest_evidence(
    *,
    output_dir: Path,
    run: Mapping[str, Any],
    native_receipts: list[Mapping[str, Any]],
    materialization_hashes: list[str],
    materialization_evidence: Mapping[str, Any],
) -> tuple[Path, dict[str, Any]]:
    if len(native_receipts) != TICKS_PER_RUN:
        raise ValueError("bounded preprojection native receipt count must be 64")
    normalized = [
        _validated_causal_receipt_metadata(value, tick_index=tick_index)
        for tick_index, value in enumerate(native_receipts)
    ]
    reference, reopened_hashes, materialization_arrays = (
        _validated_scene_materialization_reference(
            materialization_evidence, output_dir=output_dir
        )
    )
    if materialization_hashes != reopened_hashes:
        raise ValueError("bounded preprojection producer/reopened hashes drifted")
    mismatches, first = _expected_preprojection_mismatch(
        native_receipts=normalized,
        materialization_hashes=reopened_hashes,
        materialization_arrays=materialization_arrays,
    )
    run_ordinal = _require_plain_int(
        run.get("run_ordinal"), label="preprojection run ordinal"
    )
    occurrence = run.get("occurrence")
    if (
        type(occurrence) is not str
        or re.fullmatch(r"[a-z0-9_]+", occurrence) is None
    ):
        raise ValueError("bounded preprojection run occurrence is invalid")
    value = {
        "schema_version": PREPROJECTION_EVIDENCE_SCHEMA_VERSION,
        "run_ordinal": run_ordinal,
        "occurrence": occurrence,
        "native_tick_indices": list(range(TICKS_PER_RUN)),
        "native_causal_receipts": [
            {
                "tick_index": tick_index,
                "input_sha256": receipt["input_sha256"],
                "arrays": receipt["arrays"],
                "padding": {
                    name: receipt[name]
                    for name in PREPROJECTION_PADDING_FIELDS
                },
            }
            for tick_index, receipt in enumerate(normalized)
        ],
        "native_input_sha256_sequence": [
            receipt["input_sha256"] for receipt in normalized
        ],
        "materialization_sha256_sequence": reopened_hashes,
        "materialization_evidence": reference,
        "mismatch_indices": mismatches,
        "first_mismatch": first,
        "accepted_as_scientific_evidence": False,
        "full_r_execute_authorized": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    directory = output_dir / "preprojection_evidence"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"run_{run_ordinal:03d}_{occurrence}.json"
    if path.exists():
        raise FileExistsError(path)
    _write_json_atomic(path, value)
    reopened = _load_canonical_json(path)
    validated = _validate_preprojection_digest_evidence(
        reopened, output_dir=output_dir
    )
    if reopened != validated:
        raise ValueError("bounded preprojection canonical projection drifted")
    return path, validated


def _require_preprojection_digest_equality(value: Mapping[str, Any]) -> None:
    mismatches = value.get("mismatch_indices")
    if type(mismatches) is not list:
        raise ValueError("bounded preprojection mismatch indices are unavailable")
    if mismatches:
        first = mismatches[0]
        raise ValueError(f"bounded preprojection digest mismatch at tick {first}")


def _discard_equal_preprojection_evidence(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError("bounded equal preprojection evidence is unavailable")
    path.unlink()
    path.parent.rmdir()


def _initial_world_state_payload(trajectory_row: Mapping[str, Any]) -> dict[str, Any]:
    if (
        type(trajectory_row) is not dict
        or set(trajectory_row) != {"step", "x", "y", "heading", "speed", "goal_d"}
        or type(trajectory_row.get("step")) is not int
        or trajectory_row["step"] != 0
    ):
        raise ValueError("bounded initial trajectory row schema drifted")
    return {
        "schema_version": INITIAL_WORLD_STATE_SCHEMA_VERSION,
        "position_xy": [
            _native_number(trajectory_row.get("x"), label="initial world x"),
            _native_number(trajectory_row.get("y"), label="initial world y"),
        ],
        "heading_rad": _native_number(
            trajectory_row.get("heading"), label="initial world heading"
        ),
        "speed_mps": _native_number(
            trajectory_row.get("speed"), label="initial world speed"
        ),
    }


def _project_bounded_scientific_receipt(
    receipt: Mapping[str, Any],
    *,
    scene_materialization_hashes: list[str],
    scene_materialization_evidence: Mapping[str, Any],
    native_dir: Path,
) -> dict[str, Any]:
    projected = dict(receipt)
    ticks = []
    for index, source_tick in enumerate(receipt.get("ticks", [])):
        if type(source_tick) is not dict or type(source_tick.get("input_sha256")) is not str:
            raise ValueError("bounded legacy native scene-materialization digest is missing")
        tick = dict(source_tick)
        legacy_digest = tick.pop("input_sha256")
        if legacy_digest != scene_materialization_hashes[index]:
            raise ValueError("bounded scene materialization digest drifted before projection")
        tick["scene_materialization_sha256"] = legacy_digest
        ticks.append(tick)
    projected["ticks"] = ticks
    legacy_initial_input = projected.pop("initial_input_sha256", None)
    projected.pop("initial_state_sha256", None)
    if legacy_initial_input != scene_materialization_hashes[0]:
        raise ValueError("bounded initial scene materialization digest drifted")
    trajectory = _load_native_json(native_dir / "trajectory_log.json")
    if type(trajectory) is not list or len(trajectory) != TICKS_PER_RUN:
        raise ValueError("bounded initial world-state trajectory source drifted")
    initial_world = _initial_world_state_payload(trajectory[0])
    projected["schema_version"] = "camp_dp_v25_a1610_bounded_native_receipt_v2"
    projected["initial_scene_materialization_sha256"] = scene_materialization_hashes[0]
    projected["initial_world_state_sha256"] = hashlib.sha256(
        (
            json.dumps(
                initial_world,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()
    projected["causal_scene_materialization_evidence"] = dict(
        scene_materialization_evidence
    )
    return projected


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _native_number(value: Any, *, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be a finite native number")
    return float(value)


def _strict_pair(value: Any, *, label: str) -> None:
    if type(value) is not list or len(value) != 2:
        raise ValueError(f"{label} must be an exact numeric pair")
    for item in value:
        _native_number(item, label=label)


def _validate_public_success_tick(tick: Any, *, tick_index: int) -> None:
    if type(tick) is not dict or set(tick) != PUBLIC_TICK_FIELDS:
        raise ValueError("bounded native public tick exact field set drifted")
    if type(tick.get("tick_index")) is not int or tick["tick_index"] != tick_index:
        raise ValueError("bounded native public tick index drifted")
    if tick.get("status") != "ok":
        raise ValueError("bounded native public tick status is not ok")
    padding = tick.get("padding")
    tracker = tick.get("tracker")
    safety = tick.get("safety")
    latency = tick.get("latency_ms")
    if (
        type(padding) is not dict
        or set(padding) != {"observed_frames", "padded_frames", "padding_policy"}
        or type(padding.get("observed_frames")) is not int
        or type(padding.get("padded_frames")) is not int
        or padding["observed_frames"] < 1
        or padding["observed_frames"] > 31
        or padding["padded_frames"] != 31 - padding["observed_frames"]
        or padding.get("padding_policy") != "native_zero_left_pad_to_31_v1"
        or type(tracker) is not dict
        or tracker != {"status": "ok"}
        or type(safety) is not dict
        or set(safety) != SAFETY_FIELDS
        or type(latency) is not dict
        or set(latency) != LATENCY_FIELDS
    ):
        raise ValueError("bounded native padding/tracker/safety/latency schema drifted")
    if type(safety.get("tick_index")) is not int or safety["tick_index"] != tick_index:
        raise ValueError("bounded native safety tick index drifted")
    for name in ("position_xy", "front_center_prev_xy", "front_center_xy"):
        _strict_pair(safety.get(name), label=f"safety.{name}")
    for name in (
        "speed_mps", "ego_heading_rad", "route_heading_rad", "route_progress_m",
        "min_obb_clearance_m", "speed_limit_mps",
    ):
        _native_number(safety.get(name), label=f"safety.{name}")
    optional_ttc = safety.get("constant_velocity_circle_ttc_diagnostic_s")
    if optional_ttc is not None:
        _native_number(optional_ttc, label="safety.constant_velocity_circle_ttc_diagnostic_s")
    if (
        type(safety.get("five_point_drivable_coverage")) is not bool
        or type(safety.get("red_light_at_interval_start")) is not bool
        or safety.get("source_complete") is not True
        or type(safety.get("red_stop_lines")) is not list
    ):
        raise ValueError("bounded native safety exact type/value contract drifted")
    for name, value in latency.items():
        number = _native_number(value, label=f"latency_ms.{name}")
        if number < 0.0:
            raise ValueError("bounded native latency must be nonnegative")
    if _native_number(
        tick.get("pre_decision_speed_mps"), label="pre-decision speed"
    ) < 0.0:
        raise ValueError("bounded native pre-decision speed must be nonnegative")
    for name in ("physical_feasible_mask", "source_valid_mask", "source_complete_mask"):
        value = tick.get(name)
        if type(value) is not list or len(value) != 8 or any(type(item) is not bool for item in value):
            raise ValueError(f"bounded native {name} must be exact bool[8]")
    reasons = tick.get("candidate_reasons")
    if (
        type(reasons) is not list
        or len(reasons) != 8
        or any(type(row) is not list or any(type(item) is not str for item in row) for row in reasons)
    ):
        raise ValueError("bounded native candidate reasons schema drifted")


def _validate_success_native_receipt(
    native_receipt: Any,
    *,
    config: Mapping[str, Any] | None = None,
    route: Mapping[str, Any] | None = None,
    native_dir: Path | None = None,
    scene_materialization_hashes: list[str] | None = None,
) -> None:
    if type(native_receipt) is not dict or set(native_receipt) != NATIVE_RECEIPT_FIELDS:
        raise ValueError("bounded native receipt exact field set drifted")
    if (
        native_receipt.get("schema_version")
        != "camp_dp_v25_a1610_bounded_native_receipt_v2"
        or native_receipt.get("arm") != "camp"
        or native_receipt.get("claim_authorized") is not False
        or native_receipt.get("status") != "ok"
        or native_receipt.get("fixed_dp_head") != FIXED_DP_HEAD
        or native_receipt.get("checkpoint_sha256")
        != EXPECTED_FIXED_DP_CHECKPOINT_SHA256
        or native_receipt.get("args_sha256") != EXPECTED_FIXED_DP_ARGS_SHA256
        or type(native_receipt.get("scenario_seed")) is not int
        or native_receipt.get("scenario_seed") != 25001
        or native_receipt.get("selector_scale_contract")
        != EXPECTED_SELECTOR_SCALE_CONTRACT
        or native_receipt.get("runtime_annotation_compatibility")
        != EXPECTED_RUNTIME_ANNOTATION_COMPATIBILITY
    ):
        raise ValueError("bounded native receipt exact value/type contract drifted")
    ticks = native_receipt.get("ticks")
    if type(ticks) is not list or len(ticks) != TICKS_PER_RUN:
        raise ValueError("bounded native tick denominator is invalid")
    for index, tick in enumerate(ticks):
        _validate_public_success_tick(tick, tick_index=index)
    if (
        type(scene_materialization_hashes) is not list
        or len(scene_materialization_hashes) != TICKS_PER_RUN
        or any(
            type(value) is not str
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for value in scene_materialization_hashes
        )
        or any(
            ticks[index].get("scene_materialization_sha256")
            != scene_materialization_hashes[index]
            for index in range(TICKS_PER_RUN)
        )
    ):
        raise ValueError("bounded native scene materialization binding drifted")
    initial_materialization = scene_materialization_hashes[0]
    for name in (
        "route_name",
        "route_sha256",
        "logical_map_sha256",
        "spawn_config_sha256",
        "initial_world_state_sha256",
        "initial_scene_materialization_sha256",
    ):
        value = native_receipt.get(name)
        if type(value) is not str or len(value) != 64 or any(
            character not in "0123456789abcdef" for character in value
        ):
            raise ValueError(f"bounded native {name} must be a lowercase SHA256")
    if (
        native_receipt["initial_scene_materialization_sha256"]
        != initial_materialization
    ):
        raise ValueError("bounded native initial materialization binding drifted")
    if native_dir is None:
        raise ValueError("bounded native directory is required for initial world state")
    trajectory = _load_native_json(native_dir / "trajectory_log.json")
    if type(trajectory) is not list or len(trajectory) != TICKS_PER_RUN:
        raise ValueError("bounded initial world-state trajectory source drifted")
    expected_initial_world_sha = hashlib.sha256(
        (
            json.dumps(
                _initial_world_state_payload(trajectory[0]),
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()
    if native_receipt["initial_world_state_sha256"] != expected_initial_world_sha:
        raise ValueError("bounded native initial world-state binding drifted")
    evidence = native_receipt.get("causal_scene_materialization_evidence")
    if (
        type(evidence) is not dict
        or set(evidence) != SCENE_MATERIALIZATION_EVIDENCE_FIELDS
        or evidence.get("schema_version")
        != SCENE_MATERIALIZATION_EVIDENCE_SCHEMA_VERSION
        or type(evidence.get("relative_path")) is not str
        or not re.fullmatch(
            r"causal_scene_materializations/[0-9a-f]{64}\.npz",
            evidence["relative_path"],
        )
        or type(evidence.get("sha256")) is not str
        or evidence["relative_path"]
        != f"causal_scene_materializations/{evidence['sha256']}.npz"
        or type(evidence.get("tick_count")) is not int
        or evidence["tick_count"] != TICKS_PER_RUN
        or type(evidence.get("arrays")) is not dict
        or set(evidence["arrays"]) != set(SCENE_MATERIALIZATION_ARRAY_SCHEMA)
    ):
        raise ValueError("bounded native scene materialization evidence receipt drifted")
    for name, (shape, dtype_name) in SCENE_MATERIALIZATION_ARRAY_SCHEMA.items():
        metadata = evidence["arrays"].get(name)
        if (
            type(metadata) is not dict
            or set(metadata) != {"dtype", "shape", "sha256"}
            or metadata.get("dtype") != np.dtype(dtype_name).str
            or metadata.get("shape") != [TICKS_PER_RUN, *shape]
            or type(metadata.get("sha256")) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"])
        ):
            raise ValueError(
                f"bounded native scene materialization metadata drifted for {name}"
            )
    native_result = native_receipt.get("native_result")
    if (
        type(native_result) is not dict
        or set(native_result)
        != {"final_step", "goal_reached", "reason", "n_npc_spawned", "trajectory_log_path", "clearance_log_path"}
        or type(native_result.get("final_step")) is not int
        or type(native_result.get("goal_reached")) is not bool
        or type(native_result.get("reason")) is not str
        or type(native_result.get("n_npc_spawned")) is not int
        or type(native_result.get("trajectory_log_path")) is not str
        or type(native_result.get("clearance_log_path")) is not str
        or native_result.get("final_step") != 63
        or native_result.get("reason") != "max_steps"
        or native_result.get("goal_reached") is not False
        or native_result.get("n_npc_spawned") != 0
    ):
        raise ValueError("bounded native result exact schema drifted")
    trajectory_path = Path(native_result["trajectory_log_path"])
    clearance_path = Path(native_result["clearance_log_path"])
    if (
        not trajectory_path.is_absolute()
        or not clearance_path.is_absolute()
        or str(trajectory_path.resolve()) != str(trajectory_path)
        or str(clearance_path.resolve()) != str(clearance_path)
        or trajectory_path.name != "trajectory_log.json"
        or clearance_path.name != "clearance_log.json"
        or trajectory_path.parent != clearance_path.parent
    ):
        raise ValueError("bounded native result path authority drifted")
    if config is not None or route is not None or native_dir is not None:
        if (
            type(config) is not dict
            or type(route) is not dict
            or not isinstance(native_dir, Path)
        ):
            raise ValueError("bounded native producer authority inputs are incomplete")
        spawn_payload = {**config["spawn_config"], "max_steps": TICKS_PER_RUN}
        expected_spawn_sha = hashlib.sha256(
            json.dumps(spawn_payload, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        expected = {
            "route_name": str(route["name"]),
            "route_sha256": str(route["sha256"]),
            "logical_map_sha256": str(config["map"]["sha256"]),
            "fixed_dp_head": FIXED_DP_HEAD,
            "checkpoint_sha256": EXPECTED_FIXED_DP_CHECKPOINT_SHA256,
            "args_sha256": EXPECTED_FIXED_DP_ARGS_SHA256,
            "scenario_seed": 25001,
            "spawn_config_sha256": expected_spawn_sha,
            "initial_scene_materialization_sha256": initial_materialization,
            "initial_world_state_sha256": expected_initial_world_sha,
        }
        if any(native_receipt.get(key) != value for key, value in expected.items()):
            raise ValueError("bounded native producer header authority drifted")
        expected_result = {
            "final_step": 63,
            "trajectory_log_path": str(native_dir / "trajectory_log.json"),
            "clearance_log_path": str(native_dir / "clearance_log.json"),
        }
        if any(native_result.get(key) != value for key, value in expected_result.items()):
            raise ValueError("bounded native producer terminal authority drifted")


def _repeat_context_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    feature = payload.get("feature_payload")
    sidecar = payload.get("sidecar")
    if type(feature) is not dict or type(sidecar) is not dict:
        raise ValueError("bounded snapshot feature/sidecar is malformed")
    return {
        "raw_context": feature.get("raw_context"),
        "context_source_complete": feature.get("context_source_complete"),
        "context_source_receipt": sidecar.get("context_source_receipt"),
        "signal_source_class": sidecar.get("signal_source_class"),
        "phase_authority_mode": sidecar.get("phase_authority_mode"),
        "controlled_signal_source_receipt": sidecar.get(
            "controlled_signal_source_receipt"
        ),
        "controlled_signal_tensor_evidence": sidecar.get(
            "controlled_signal_tensor_evidence"
        ),
        "controlled_model_input_cache_receipt": sidecar.get(
            "controlled_model_input_cache_receipt"
        ),
        "causal_signal_atom_input": sidecar.get("causal_signal_atom_input"),
    }


def _reject_native_forbidden_fields(value: Any, *, path: str = "native") -> None:
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("bounded native evidence has a non-string key")
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if (
                any(token in normalized for token in ("error", "exception", "failure"))
                or normalized
                in {"fault", "success", "aborted", "crash", "exitcode", "statuscode"}
            ):
                raise ValueError(f"bounded native evidence has an unknown failure field: {path}.{key}")
            if "outcome" in normalized and key != "outcome_fields_consumed":
                raise ValueError(f"bounded native evidence has an unknown outcome field: {path}.{key}")
            if "future" in normalized and key != "future_schedule_consumed":
                raise ValueError(f"bounded native evidence has an unknown future field: {path}.{key}")
            if key == "outcome_fields_consumed" and item != []:
                raise ValueError("bounded native evidence consumed outcome fields")
            if key == "future_schedule_consumed" and item is not False:
                raise ValueError("bounded native evidence consumed a future schedule")
            _reject_native_forbidden_fields(item, path=f"{path}.{key}")
    elif type(value) is list:
        for index, item in enumerate(value):
            _reject_native_forbidden_fields(item, path=f"{path}[{index}]")


def _derive_native_failure_class(
    native_receipt: Mapping[str, Any],
    *,
    scene_materialization_hashes: list[str] | None = None,
    config: Mapping[str, Any] | None = None,
    route: Mapping[str, Any] | None = None,
    native_dir: Path | None = None,
) -> str:
    """Derive completion from persisted native evidence, never caller input."""

    if type(native_receipt) is not dict:
        return "native_receipt_malformed"
    try:
        _reject_native_forbidden_fields(native_receipt)
        _validate_success_native_receipt(
            native_receipt,
            config=config,
            route=route,
            native_dir=native_dir,
            scene_materialization_hashes=scene_materialization_hashes,
        )
    except ValueError:
        return "native_evidence_schema_invalid"
    return "none"


def build_run_evidence(
    *,
    run: Mapping[str, Any],
    payloads: list[Mapping[str, Any]],
    native_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Build evidence values, never caller-supplied repeat-pass booleans."""

    ticks = native_receipt.get("ticks")
    if type(ticks) is not list or len(ticks) != TICKS_PER_RUN:
        raise ValueError("bounded native receipt must contain exactly 64 ticks")
    if len(payloads) != TICKS_PER_RUN:
        raise ValueError("bounded run must contain exactly 64 paired snapshots")
    candidate0: list[str] = []
    rows: list[list[str]] = []
    atoms: list[str] = []
    contexts: list[str] = []
    selected: list[int] = []
    trajectory: list[dict[str, Any]] = []
    speeds: list[float] = []
    for index, (payload, tick) in enumerate(zip(payloads, ticks)):
        feature = payload.get("feature_payload")
        sidecar = payload.get("sidecar")
        safety = tick.get("safety") if type(tick) is dict else None
        if type(feature) is not dict or type(sidecar) is not dict or type(safety) is not dict:
            raise ValueError("bounded repeat evidence lacks raw snapshot/native safety")
        candidate0_sha = sidecar.get("candidate0_sha256")
        row_sha = feature.get("candidate_row_sha256")
        selected_index = sidecar.get("selected_index")
        position = safety.get("position_xy")
        if (
            type(candidate0_sha) is not str
            or len(candidate0_sha) != 64
            or type(row_sha) is not list
            or len(row_sha) != 8
            or any(type(value) is not str or len(value) != 64 for value in row_sha)
            or type(selected_index) is not int
            or selected_index < 0
            or selected_index >= 8
            or type(position) is not list
            or len(position) != 2
        ):
            raise ValueError("bounded repeat candidate/trajectory evidence drifted")
        candidate0.append(candidate0_sha)
        rows.append(list(row_sha))
        atoms.append(canonical_sha256(feature.get("atom_matrix")))
        contexts.append(canonical_sha256(_repeat_context_payload(payload)))
        selected.append(selected_index)
        trajectory.append(
            {
                "tick_index": index,
                "position_xy": [
                    _native_number(position[0], label="position x"),
                    _native_number(position[1], label="position y"),
                ],
                "ego_heading_rad": _native_number(
                    safety.get("ego_heading_rad"), label="ego heading"
                ),
                "route_progress_m": _native_number(
                    safety.get("route_progress_m"), label="route progress"
                ),
            }
        )
        speeds.append(_native_number(safety.get("speed_mps"), label="speed probe"))
    return {
        "schema_version": RUN_EVIDENCE_SCHEMA_VERSION,
        "run_ordinal": run["run_ordinal"],
        "scenario_id": run["scenario_id"],
        "occurrence": run["occurrence"],
        "tick_count": TICKS_PER_RUN,
        "candidate0_sha256_sequence": candidate0,
        "k8_row_sha256_sequence": rows,
        "atom_matrix_sha256_sequence": atoms,
        "context_sha256_sequence": contexts,
        "selected_index_sequence": selected,
        "failure_class": _derive_native_failure_class(native_receipt),
        "closed_loop_trajectory_sha256": canonical_sha256(trajectory),
        "speed_probe_sha256": canonical_sha256(speeds),
    }


def _write_snapshot(
    *,
    output_dir: Path,
    index_file: Any,
    run: Mapping[str, Any],
    tick_index: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    sidecar = payload.get("sidecar")
    if type(sidecar) is not dict:
        raise ValueError("bounded snapshot sidecar is missing")
    feature = payload.get("feature_payload")
    if type(feature) is not dict:
        raise ValueError("bounded snapshot feature payload is missing")
    payload["schema_version"] = SNAPSHOT_SCHEMA_VERSION
    sidecar["run_ordinal"] = run["run_ordinal"]
    sidecar["occurrence"] = run["occurrence"]
    feature["causal_evidence"] = externalize_causal_evidence(
        output_dir=output_dir,
        causal_evidence=feature.get("causal_evidence"),
    )
    data = encode_snapshot(payload)
    digest = hashlib.sha256(data).hexdigest()
    relative = Path("snapshots") / f"{digest}{SNAPSHOT_SUFFIX}"
    target = output_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() != data:
        raise ValueError("bounded content-addressed snapshot collision")
    if not target.exists():
        target.write_bytes(data)
    row = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "run_ordinal": run["run_ordinal"],
        "occurrence": run["occurrence"],
        "scenario_id": run["scenario_id"],
        "tick_index": tick_index,
        "relative_path": relative.as_posix(),
        "sha256": digest,
    }
    _write_jsonl_row(index_file, row)
    return row


def _execute(
    *,
    args: argparse.Namespace,
    plan: Mapping[str, Any],
    cases: Mapping[str, Mapping[str, Any]],
    template: Mapping[str, Any],
    route_assets: Mapping[str, Mapping[str, str]],
    diagnostic_only: bool = False,
) -> dict[str, Any]:
    runs = plan["runs"]
    expected_runs = 1 if diagnostic_only else EXPECTED_RUNS
    expected_unique_identities = 1 if diagnostic_only else EXPECTED_UNIQUE_IDENTITIES
    expected_ticks = TICKS_PER_RUN if diagnostic_only else EXPECTED_TICKS
    if len(runs) != expected_runs:
        raise ValueError("execution plan denominator does not match its authority mode")
    first_case = cases[str(runs[0]["scenario_id"])]
    first_config = corpus.build_controlled_train_config(
        template,
        first_case,
        route_assets[str(first_case["route_identity_sha256"])],
    )
    # This is the first model/simulator/candidate-capable operation.  The
    # caller reaches here only after verify_bounded_release consumed authority.
    runner = corpus.build_native_arm_runner(first_config, device=args.device)
    results: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    snapshot_count = 0
    started = time.perf_counter()
    with (args.output_dir / "results.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as result_file, (args.output_dir / "snapshot_index.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as index_file, (args.output_dir / "run_evidence.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as evidence_file:
        for run in runs:
            if shutil.disk_usage(args.output_dir.parent).free < MINIMUM_FREE_BYTES:
                raise RuntimeError("free disk fell below the 10 GiB floor")
            case = cases[str(run["scenario_id"])]
            identity = str(case["route_identity_sha256"])
            config = corpus.build_controlled_train_config(
                template, case, route_assets[identity]
            )
            adapter = V25ControlledSceneAdapter(
                case,
                mapped_signal_authority=case.get("mapped_signal_authority"),
                no_signal_authority=case.get("no_signal_authority"),
            )
            snapshots: list[Mapping[str, Any]] = []
            contexts: list[Mapping[str, Any]] = []
            scene_materializations: list[Mapping[str, Any]] = []
            native_causal_receipts: list[Mapping[str, Any]] = []
            candidate_evidence_count = 0

            def capture_causal_input(
                tick_index: int, value: Mapping[str, Any]
            ) -> None:
                if (
                    type(tick_index) is not int
                    or tick_index != len(scene_materializations)
                ):
                    raise ValueError(
                        "bounded scene materialization sink tick order drifted"
                    )
                scene_materializations.append(value)

            def capture_causal_receipt(
                tick_index: int, value: Mapping[str, Any]
            ) -> None:
                if (
                    type(tick_index) is not int
                    or tick_index != len(native_causal_receipts)
                ):
                    raise ValueError(
                        "bounded native causal receipt sink tick order drifted"
                    )
                native_causal_receipts.append(
                    _validated_causal_receipt_metadata(
                        value, tick_index=tick_index
                    )
                )

            def capture_candidate_tensor(
                tick_index: int,
                candidates: np.ndarray,
                metadata: Mapping[str, Any],
            ) -> None:
                nonlocal candidate_evidence_count
                if type(tick_index) is not int or tick_index != candidate_evidence_count:
                    raise ValueError(
                        "diagnostic candidate evidence sink tick order drifted"
                    )
                _write_candidate_prematerialization_evidence(
                    output_dir=args.output_dir,
                    run=run,
                    tick_index=tick_index,
                    candidates=candidates,
                    metadata=metadata,
                )
                candidate_evidence_count += 1
            native_dir = (
                args.output_dir
                / "native_runs"
                / (
                    f"run_{int(run['run_ordinal']):03d}_"
                    f"{run['occurrence']}_{run['scenario_id']}"
                )
            )
            runner_kwargs: dict[str, Any] = {
                "route": config["routes"][0],
                "arm": "camp",
                "config": config,
                "output_dir": native_dir,
                "max_steps": TICKS_PER_RUN,
                "decision_sink": snapshots.append,
                "scene_adapter": adapter,
                "v25_context_sink": contexts.append,
                "causal_input_sink": capture_causal_input,
                "causal_input_receipt_sink": capture_causal_receipt,
            }
            if diagnostic_only:
                runner_kwargs["candidate_tensor_sink"] = capture_candidate_tensor
            receipt = runner(
                **runner_kwargs,
            )
            if (
                type(receipt) is not dict
                or len(receipt.get("ticks", [])) != TICKS_PER_RUN
                or len(snapshots) != TICKS_PER_RUN
                or len(contexts) != TICKS_PER_RUN
                or len(adapter.receipts) != TICKS_PER_RUN
                or len(scene_materializations) != TICKS_PER_RUN
                or len(native_causal_receipts) != TICKS_PER_RUN
                or (diagnostic_only and candidate_evidence_count != TICKS_PER_RUN)
            ):
                raise RuntimeError("bounded run was partial or lacked exact tick evidence")
            corpus.validate_native_arm_receipt(
                receipt,
                "camp",
                expected_ticks=TICKS_PER_RUN,
                require_summary=False,
                expected_selection_policy="v22_source_valid",
                expected_safety_schema="safety_cost_native_v22",
            )
            # Fixed DP writes a broad diagnostic SpawnConfig JSON that is not
            # part of the bounded scientific receipt.  Do not seal arbitrary
            # JSON: the exact spawn authority is independently reconstructed
            # from the formal case/template instead.
            native_spawn_config = native_dir / "spawn_config.json"
            if native_spawn_config.is_symlink() or not native_spawn_config.is_file():
                raise RuntimeError("bounded native SpawnConfig diagnostic is unavailable")
            native_spawn_config.unlink()
            receipt = dict(receipt)
            for derived_summary in ("safety", "secondary", "latency"):
                if derived_summary in receipt:
                    raise RuntimeError(
                        f"bounded native {derived_summary} summary was unexpectedly "
                        "materialized"
                    )
            scene_reference, scene_materialization_hashes = (
                _write_scene_materialization_evidence(
                output_dir=args.output_dir,
                run=run,
                rows=scene_materializations,
                )
            )
            preprojection_path, preprojection = (
                _write_preprojection_digest_evidence(
                    output_dir=args.output_dir,
                    run=run,
                    native_receipts=native_causal_receipts,
                    materialization_hashes=scene_materialization_hashes,
                    materialization_evidence=scene_reference,
                )
            )
            # Equality is decided only from the canonical evidence that was
            # atomically persisted and strictly reopened above.  Mismatch keeps
            # that file for the fail-closed seal; equality removes the
            # diagnostic-only file so the established success inventory and
            # scientific receipt remain byte-semantically unchanged.
            _require_preprojection_digest_equality(preprojection)
            _discard_equal_preprojection_evidence(preprojection_path)
            receipt = _project_bounded_scientific_receipt(
                receipt,
                scene_materialization_hashes=scene_materialization_hashes,
                scene_materialization_evidence=scene_reference,
                native_dir=native_dir,
            )
            _validate_success_native_receipt(
                receipt,
                config=config,
                route=config["routes"][0],
                native_dir=native_dir,
                scene_materialization_hashes=scene_materialization_hashes,
            )
            failure_class = _derive_native_failure_class(
                receipt,
                scene_materialization_hashes=scene_materialization_hashes,
                config=config,
                route=config["routes"][0],
                native_dir=native_dir,
            )
            if failure_class != "none":
                raise RuntimeError(
                    f"bounded native run failed closed: {failure_class}"
                )
            payloads: list[dict[str, Any]] = []
            for tick_index in range(TICKS_PER_RUN):
                payload = corpus.combine_snapshot_context(
                    snapshot=snapshots[tick_index],
                    context=contexts[tick_index],
                    case=case,
                    tick_index=tick_index,
                    controlled_scene_receipt=adapter.receipts[tick_index],
                )
                # The full-corpus projection validates the canonical scores
                # before returning but intentionally omits them.  Bounded
                # independent review needs the actual finite affine values,
                # so preserve that already-validated sequence explicitly.
                payload["sidecar"]["scores"] = list(
                    snapshots[tick_index]["sidecar"]["scores"]
                )
                payload["sidecar"]["scene_materialization_sha256"] = (
                    payload["sidecar"].pop("causal_input_sha256")
                )
                _write_snapshot(
                    output_dir=args.output_dir,
                    index_file=index_file,
                    run=run,
                    tick_index=tick_index,
                    payload=payload,
                )
                payloads.append(payload)
            _write_json(native_dir / "bounded_native_receipt.json", receipt)
            evidence = build_run_evidence(
                run=run,
                payloads=payloads,
                native_receipt=receipt,
            )
            result = {
                "schema_version": RESULT_SCHEMA_VERSION,
                "run_ordinal": run["run_ordinal"],
                "scenario_id": run["scenario_id"],
                "occurrence": run["occurrence"],
                "status": "complete",
                "tick_count": TICKS_PER_RUN,
                "retained_capability_failure": None,
                "failure_class": failure_class,
                "fresh_b2_opened": False,
                "outcome_fields_consumed": [],
            }
            results.append(result)
            evidence_rows.append(evidence)
            _write_jsonl_row(result_file, result)
            _write_jsonl_row(evidence_file, evidence)
            result_file.flush()
            evidence_file.flush()
            index_file.flush()
            snapshot_count += TICKS_PER_RUN
            _write_json_atomic(
                args.output_dir / "progress.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "running",
                    "completed_runs": len(results),
                    "total_runs": expected_runs,
                    "snapshot_count": snapshot_count,
                    "fresh_b2_opened": False,
                    "outcome_fields_consumed": [],
                },
            )
    if diagnostic_only:
        if (
            len(results) != 1
            or snapshot_count != TICKS_PER_RUN
            or len(evidence_rows) != 1
            or results[0].get("status") != "complete"
            or results[0].get("failure_class") != "none"
        ):
            raise RuntimeError("A1.7 diagnostic terminal evidence was incomplete")
        terminal = {
            "diagnostic_only": True,
            "completed_runs": 1,
            "snapshot_count": TICKS_PER_RUN,
            "accepted_as_scientific_evidence": False,
        }
    else:
        terminal = validate_bounded_terminal_acceptance(
            plan, results, run_evidence=evidence_rows
        )
    _write_json_atomic(
        args.output_dir / "progress.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "complete",
            "completed_runs": len(results),
            "total_runs": expected_runs,
            "snapshot_count": snapshot_count,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        },
    )
    report = {
        "schema_version": (
            A17_DIAGNOSTIC_EXECUTION_SCHEMA_VERSION
            if diagnostic_only
            else SCHEMA_VERSION
        ),
        "status": (
            "passed_diagnostic_only_preprojection_1x64"
            if diagnostic_only
            else "passed_exact_bounded_execution"
        ),
        "unique_identity_count": expected_unique_identities,
        "run_count": len(results),
        "snapshot_count": snapshot_count,
        "snapshot_capacity": expected_ticks,
        "device": EXPECTED_DEVICE,
        "terminal": terminal,
        "wall_seconds": time.perf_counter() - started,
        "retained_capability_failure_count": 0,
        "mapped_runtime_source_failure_count": 0,
        "candidate0_semantics": "operational_default_alias_from_same_forward",
        "sequential_fixed_k8": True,
        "candidate_tensors_modified": False,
        "full_r_execute_authorized": False,
        "training_executed": False,
        "calibration_executed": False,
        "scene_runtime_enabled": False,
        "v2i_enabled": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    if diagnostic_only:
        report.update(
            {
                "diagnostic_execute_authorized": True,
                "bounded_execute_authorized": False,
                "accepted_as_scientific_evidence": False,
            }
        )
    return report


def _run(args: argparse.Namespace) -> dict[str, Any]:
    if type(args.output_dir) is not str or not args.output_dir:
        raise ValueError("bounded requested output must retain its raw CLI string")
    raw_output_dir = args.output_dir
    output_dir = Path(raw_output_dir)
    resolved_output = output_dir.resolve()
    if (
        not output_dir.is_absolute()
        or raw_output_dir != str(resolved_output)
        or output_dir.is_symlink()
    ):
        raise ValueError("bounded requested output must be one exact canonical path")
    if output_dir.exists():
        raise FileExistsError(output_dir)
    camp_head = _git(ROOT, "rev-parse", "HEAD")
    if _git(ROOT, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("CAMP tracked worktree is dirty")
    if (
        _git(args.dp_repo, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(args.dp_repo, "status", "--porcelain")
    ):
        raise ValueError("fixed DP drifted or is not fully clean")
    if shutil.disk_usage(output_dir.parent).free < MINIMUM_FREE_BYTES:
        raise RuntimeError("free disk is below the 10 GiB floor")

    # Fail closed and consume the one-shot authority before loading the formal
    # universe, materializing routes, building the model, simulator or K8.
    diagnostic_only = getattr(args, "a17_diagnostic", False) is True
    verifier = (
        verify_a17_diagnostic_release if diagnostic_only else verify_bounded_release
    )
    authority = verifier(
        repo=ROOT,
        release_artifact=args.release_artifact,
        release_root_sha256=args.release_root_sha256,
        requested_output_dir=raw_output_dir,
        current_pointer_head=camp_head,
        dp_repo=args.dp_repo,
        probe_template=args.probe_template,
        requested_device=args.device,
        consume=True,
    )
    args.output_dir = output_dir
    args.authority_consumed = True
    plan = authority["plan"]
    formal, formal_root = corpus._load_formal_plan()
    template = corpus._load_json(args.probe_template)
    formal_cases = {
        str(case["scenario_id"]): case
        for case in formal["train"]
        if case.get("runner_eligible") is True
    }
    selected_ids = {str(run["scenario_id"]) for run in plan["runs"]}
    expected_selected = 1 if diagnostic_only else EXPECTED_UNIQUE_IDENTITIES
    if len(selected_ids) != expected_selected or not selected_ids <= set(
        formal_cases
    ):
        raise ValueError("execution plan/formal selected identity universe drifted")
    source_binding = authority["decision"]["root_artifacts"]["source"]
    selected = [formal_cases[scenario_id] for scenario_id in sorted(selected_ids)]
    attached = corpus._attach_semantic_clone_authority(
        selected,
        dp_repo=args.dp_repo,
        r0_source_artifact=Path(source_binding["path"]),
        expected_camp_source_head=authority["decision"]["implementation_source_head"],
        r0_source_root_sha256=source_binding["root_sha256"],
    )
    cases = {str(case["scenario_id"]): case for case in attached}
    args.output_dir.mkdir(parents=True)
    route_assets = corpus._materialize_routes(
        attached, args.output_dir / "routes", args.dp_repo
    )
    (args.output_dir / "HEADS").write_text(
        f"camp_source_head={authority['decision']['implementation_source_head']}\n"
        f"camp_pointer_head={camp_head}\n"
        f"fixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        " ".join(sys.argv) + "\n", encoding="utf-8"
    )
    source_receipt = {
            "schema_version": SCHEMA_VERSION,
            "release_artifact": authority["release_artifact"],
            "release_root_sha256": authority["release_root_sha256"],
            "release_run_nonce": authority["decision"]["run_nonce"],
            "nonce_marker": authority["nonce_marker"],
            "root_artifacts": authority["decision"]["root_artifacts"],
            "formal_root_sha256": formal_root,
            "critical_implementation_manifest": authority["decision"][
                "critical_implementation_manifest"
            ],
            "unique_identity_count": expected_selected,
            "run_count": 1 if diagnostic_only else EXPECTED_RUNS,
            "snapshot_capacity": TICKS_PER_RUN if diagnostic_only else EXPECTED_TICKS,
            "device": EXPECTED_DEVICE,
            "full_r_execute_authorized": False,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        }
    if diagnostic_only:
        source_receipt.update(
            {
                "schema_version": A17_DIAGNOSTIC_EXECUTION_SCHEMA_VERSION,
                "diagnostic_execute_authorized": True,
                "bounded_execute_authorized": False,
                "accepted_as_scientific_evidence": False,
            }
        )
    _write_json(args.output_dir / "source_receipt.json", source_receipt)
    return _execute(
        args=args,
        plan=plan,
        cases=cases,
        template=template,
        route_assets=route_assets,
        diagnostic_only=diagnostic_only,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--release-artifact", type=Path, required=True)
    parser.add_argument("--release-root-sha256", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--device", choices=(EXPECTED_DEVICE,), default=EXPECTED_DEVICE)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--bounded-execute", action="store_true")
    mode.add_argument("--a17-diagnostic", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    with _exclusive_lock(TRAIN_LOCK):
        try:
            report = _run(args)
            _write_json(args.output_dir / "report.json", report)
            (args.output_dir / "run.exit").write_bytes(b"0\n")
            label = (
                "V25 A1.7 preprojection diagnostic execution"
                if getattr(args, "a17_diagnostic", False)
                else "V25 A1.6.10 bounded execution"
            )
            root = seal_artifact(args.output_dir, label=label)
            print(json.dumps({**report, "artifact_root_sha256": root}, sort_keys=True))
        except BaseException as exc:
            if getattr(args, "authority_consumed", False) is not True:
                raise
            args.output_dir.mkdir(parents=True, exist_ok=True)
            failure = {
                    "schema_version": (
                        A17_DIAGNOSTIC_FAILURE_SCHEMA_VERSION
                        if getattr(args, "a17_diagnostic", False)
                        else FAILURE_SCHEMA_VERSION
                    ),
                    "status": (
                        "failed_closed_a17_preprojection_diagnostic"
                        if getattr(args, "a17_diagnostic", False)
                        else "failed_closed_bounded_execution"
                    ),
                    "failure_type": type(exc).__name__,
                    "failure_reason": str(exc),
                    "full_r_execute_authorized": False,
                    "fresh_b2_opened": False,
                    "outcome_fields_consumed": [],
                }
            if getattr(args, "a17_diagnostic", False):
                failure.update(
                    {
                        "diagnostic_execute_authorized": True,
                        "bounded_execute_authorized": False,
                        "accepted_as_scientific_evidence": False,
                    }
                )
            _write_json(args.output_dir / "failure.json", failure)
            (args.output_dir / "run.exit").write_bytes(b"1\n")
            label = (
                "failed V25 A1.7 preprojection diagnostic execution"
                if getattr(args, "a17_diagnostic", False)
                else "failed V25 A1.6.10 bounded execution"
            )
            seal_artifact(args.output_dir, label=label)
            raise


if __name__ == "__main__":
    main()
