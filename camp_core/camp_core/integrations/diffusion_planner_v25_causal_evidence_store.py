from __future__ import annotations

import hashlib
import json
import lzma
import os
import struct
from pathlib import Path
from typing import Any, Mapping

import numpy as np


LOGICAL_SCHEMA_VERSION = "camp_dp_v25_bounded_causal_evidence_v1"
REFERENCE_SCHEMA_VERSION = "camp_dp_v25_causal_evidence_shard_reference_v1"
ARRAY_SCHEMA_VERSION = "camp_dp_v25_causal_evidence_array_v1"
ARRAY_CODEC = "canonical-metadata-plus-bitexact-array-bytes-xz6-v2"
SHARD_DIRECTORY = "causal_evidence_shards"
SHARD_SUFFIX = ".bin.xz"
_MAGIC = b"CAMP-DP-V25-ARRAY-V1\x00"


ARRAY_CONTRACT: dict[str, tuple[tuple[int, ...], np.dtype[Any]]] = {
    "ego_current_state": ((10,), np.dtype("<f4")),
    "ego_shape": ((3,), np.dtype("<f4")),
    "neighbor_agents_past": ((32, 31, 11), np.dtype("<f4")),
    "neighbor_valid_mask": ((32,), np.dtype("|b1")),
    "candidate_neighbor_predictions": ((8, 32, 80, 4), np.dtype("<f4")),
    "static_objects": ((5, 10), np.dtype("<f4")),
    "route_lanes": ((25, 20, 33), np.dtype("<f4")),
    "route_lanes_speed_limit": ((25, 1), np.dtype("<f4")),
    "route_lanes_has_speed_limit": ((25, 1), np.dtype("|b1")),
    "signal_mask": ((8,), np.dtype("|b1")),
    "fixed_dp_planned_red_light_cost": ((8,), np.dtype("<f8")),
}

REFERENCE_FIELDS = frozenset(
    {
        "schema_version",
        "logical_schema_version",
        "logical_sha256",
        "arrays",
    }
)
ARRAY_REFERENCE_FIELDS = frozenset(
    {
        "schema_version",
        "codec",
        "relative_path",
        "storage_sha256",
        "array_sha256",
        "dtype",
        "shape",
        "uncompressed_nbytes",
        "transform",
    }
)

_XOR_TIME_AXES = {
    "neighbor_agents_past": 1,
    "candidate_neighbor_predictions": 2,
    "route_lanes": 1,
}


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


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _strict_array(value: Any, *, name: str) -> np.ndarray:
    shape, dtype = ARRAY_CONTRACT[name]
    if type(value) is not list:
        raise ValueError(f"causal evidence {name} must be a JSON list")
    if dtype == np.dtype("|b1"):
        raw = np.asarray(value)
        if raw.shape != shape or raw.dtype != np.bool_:
            raise ValueError(f"causal evidence {name} must be native bool{shape}")
        array = np.ascontiguousarray(raw, dtype=dtype)
    else:
        raw = np.asarray(value)
        if (
            raw.shape != shape
            or raw.dtype.kind not in "iuIf"
            or raw.dtype.kind == "b"
            or not np.isfinite(raw).all()
        ):
            raise ValueError(f"causal evidence {name} must be finite numeric{shape}")
        array = np.ascontiguousarray(raw, dtype=dtype)
        if not np.isfinite(array).all():
            raise ValueError(f"causal evidence {name} overflows its frozen dtype")
    return array


def _array_metadata(name: str, array: np.ndarray) -> dict[str, Any]:
    raw = array.tobytes(order="C")
    return {
        "schema_version": ARRAY_SCHEMA_VERSION,
        "name": name,
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "order": "C",
        "array_sha256": _sha256(raw),
        "uncompressed_nbytes": len(raw),
        "transform": (
            f"uint32-xor-axis-{_XOR_TIME_AXES[name]}"
            if name in _XOR_TIME_AXES
            else "identity"
        ),
    }


def _encode_array(name: str, array: np.ndarray) -> tuple[bytes, dict[str, Any]]:
    metadata = _array_metadata(name, array)
    metadata_bytes = _canonical_json_bytes(metadata)
    raw = array.tobytes(order="C")
    stored_raw = raw
    if name in _XOR_TIME_AXES:
        axis = _XOR_TIME_AXES[name]
        bits = array.view(np.uint32)
        transformed = bits.copy()
        current = [slice(None)] * bits.ndim
        previous = current.copy()
        current[axis] = slice(1, None)
        previous[axis] = slice(None, -1)
        transformed[tuple(current)] ^= bits[tuple(previous)]
        stored_raw = np.ascontiguousarray(transformed).tobytes(order="C")
    preimage = (
        _MAGIC
        + struct.pack("<Q", len(metadata_bytes))
        + metadata_bytes
        + stored_raw
    )
    return (
        lzma.compress(
            preimage,
            format=lzma.FORMAT_XZ,
            check=lzma.CHECK_SHA256,
            preset=6,
        ),
        metadata,
    )


def _logical_payload(arrays: Mapping[str, np.ndarray]) -> dict[str, Any]:
    return {
        "schema_version": LOGICAL_SCHEMA_VERSION,
        **{name: arrays[name].tolist() for name in ARRAY_CONTRACT},
    }


def externalize_causal_evidence(
    *, output_dir: Path, causal_evidence: Mapping[str, Any]
) -> dict[str, Any]:
    """Persist exact causal arrays without changing their logical JSON digest."""

    if (
        type(causal_evidence) is not dict
        or set(causal_evidence) != {"schema_version", *ARRAY_CONTRACT}
        or causal_evidence.get("schema_version") != LOGICAL_SCHEMA_VERSION
    ):
        raise ValueError("causal evidence exact logical schema drifted")
    arrays = {
        name: _strict_array(causal_evidence[name], name=name)
        for name in ARRAY_CONTRACT
    }
    logical = _logical_payload(arrays)
    input_logical_sha = _sha256(_canonical_json_bytes(causal_evidence))
    logical_sha = _sha256(_canonical_json_bytes(logical))
    if logical_sha != input_logical_sha:
        raise ValueError("causal evidence frozen dtype round-trip changed its digest")

    shard_dir = output_dir / SHARD_DIRECTORY
    shard_dir.mkdir(parents=True, exist_ok=True)
    references: dict[str, Any] = {}
    for name, array in arrays.items():
        encoded, metadata = _encode_array(name, array)
        storage_sha = _sha256(encoded)
        relative = Path(SHARD_DIRECTORY) / f"{storage_sha}{SHARD_SUFFIX}"
        target = output_dir / relative
        if target.exists():
            if target.is_symlink() or not target.is_file() or target.read_bytes() != encoded:
                raise ValueError("causal evidence content-addressed shard collision")
        else:
            temporary = target.with_name(f".{storage_sha}.tmp")
            if temporary.exists():
                raise ValueError("causal evidence temporary shard already exists")
            temporary.write_bytes(encoded)
            os.replace(temporary, target)
        references[name] = {
            "schema_version": ARRAY_SCHEMA_VERSION,
            "codec": ARRAY_CODEC,
            "relative_path": relative.as_posix(),
            "storage_sha256": storage_sha,
            "array_sha256": metadata["array_sha256"],
            "dtype": metadata["dtype"],
            "shape": metadata["shape"],
            "uncompressed_nbytes": metadata["uncompressed_nbytes"],
            "transform": metadata["transform"],
        }
    return {
        "schema_version": REFERENCE_SCHEMA_VERSION,
        "logical_schema_version": LOGICAL_SCHEMA_VERSION,
        "logical_sha256": logical_sha,
        "arrays": references,
    }


def decode_array_shard(data: bytes) -> tuple[dict[str, Any], np.ndarray]:
    """Decode a shard for producer-side round-trip tests and diagnostics."""

    try:
        preimage = lzma.decompress(data, format=lzma.FORMAT_XZ)
    except lzma.LZMAError as exc:
        raise ValueError("causal evidence shard compression is invalid") from exc
    prefix = len(_MAGIC) + 8
    if len(preimage) < prefix or preimage[: len(_MAGIC)] != _MAGIC:
        raise ValueError("causal evidence shard magic is invalid")
    metadata_size = struct.unpack("<Q", preimage[len(_MAGIC) : prefix])[0]
    metadata_end = prefix + metadata_size
    if metadata_end > len(preimage):
        raise ValueError("causal evidence shard metadata is truncated")
    metadata_bytes = preimage[prefix:metadata_end]
    try:
        metadata = json.loads(metadata_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("causal evidence shard metadata is invalid") from exc
    if _canonical_json_bytes(metadata) != metadata_bytes:
        raise ValueError("causal evidence shard metadata is noncanonical")
    if (
        type(metadata) is not dict
        or set(metadata)
        != {
            "schema_version",
            "name",
            "dtype",
            "shape",
            "order",
            "array_sha256",
            "uncompressed_nbytes",
            "transform",
        }
        or metadata.get("schema_version") != ARRAY_SCHEMA_VERSION
        or metadata.get("order") != "C"
        or metadata.get("name") not in ARRAY_CONTRACT
    ):
        raise ValueError("causal evidence shard metadata schema drifted")
    name = str(metadata["name"])
    expected_shape, expected_dtype = ARRAY_CONTRACT[name]
    if (
        metadata.get("dtype") != expected_dtype.str
        or metadata.get("shape") != list(expected_shape)
        or type(metadata.get("uncompressed_nbytes")) is not int
    ):
        raise ValueError("causal evidence shard dtype or shape drifted")
    raw = preimage[metadata_end:]
    if (
        len(raw) != metadata["uncompressed_nbytes"]
    ):
        raise ValueError("causal evidence shard raw bytes drifted")
    transform = metadata.get("transform")
    expected_transform = (
        f"uint32-xor-axis-{_XOR_TIME_AXES[name]}"
        if name in _XOR_TIME_AXES
        else "identity"
    )
    if transform != expected_transform:
        raise ValueError("causal evidence shard transform drifted")
    if name in _XOR_TIME_AXES:
        encoded = np.frombuffer(raw, dtype=np.uint32).reshape(expected_shape)
        restored = np.bitwise_xor.accumulate(
            encoded, axis=_XOR_TIME_AXES[name]
        )
        array = np.ascontiguousarray(restored).view(expected_dtype).copy()
    else:
        array = np.frombuffer(raw, dtype=expected_dtype).reshape(expected_shape).copy()
    if _sha256(array.tobytes(order="C")) != metadata.get("array_sha256"):
        raise ValueError("causal evidence shard restored array SHA drifted")
    return metadata, array


def materialize_causal_evidence(
    *, artifact_root: Path, reference: Mapping[str, Any]
) -> dict[str, Any]:
    """Strictly reopen a producer reference; reviewers keep a separate oracle."""

    if (
        type(reference) is not dict
        or set(reference) != REFERENCE_FIELDS
        or reference.get("schema_version") != REFERENCE_SCHEMA_VERSION
        or reference.get("logical_schema_version") != LOGICAL_SCHEMA_VERSION
        or type(reference.get("logical_sha256")) is not str
        or type(reference.get("arrays")) is not dict
        or set(reference["arrays"]) != set(ARRAY_CONTRACT)
    ):
        raise ValueError("causal evidence shard reference schema drifted")
    arrays: dict[str, np.ndarray] = {}
    for name in ARRAY_CONTRACT:
        item = reference["arrays"][name]
        if type(item) is not dict or set(item) != ARRAY_REFERENCE_FIELDS:
            raise ValueError("causal evidence array reference schema drifted")
        relative = item.get("relative_path")
        storage_sha = item.get("storage_sha256")
        if (
            item.get("schema_version") != ARRAY_SCHEMA_VERSION
            or item.get("codec") != ARRAY_CODEC
            or type(relative) is not str
            or relative != f"{SHARD_DIRECTORY}/{storage_sha}{SHARD_SUFFIX}"
            or type(storage_sha) is not str
            or len(storage_sha) != 64
            or set(storage_sha) - set("0123456789abcdef")
        ):
            raise ValueError("causal evidence array reference value drifted")
        path = artifact_root / relative
        if (
            path.is_symlink()
            or not path.is_file()
            or path.resolve().parent != (artifact_root / SHARD_DIRECTORY).resolve()
        ):
            raise ValueError("causal evidence shard path is unsafe")
        data = path.read_bytes()
        if _sha256(data) != storage_sha:
            raise ValueError("causal evidence shard storage SHA drifted")
        metadata, array = decode_array_shard(data)
        if (
            metadata["name"] != name
            or item.get("array_sha256") != metadata["array_sha256"]
            or item.get("dtype") != metadata["dtype"]
            or item.get("shape") != metadata["shape"]
            or item.get("uncompressed_nbytes") != metadata["uncompressed_nbytes"]
            or item.get("transform") != metadata["transform"]
        ):
            raise ValueError("causal evidence reference/shard metadata drifted")
        arrays[name] = array
    logical = _logical_payload(arrays)
    if _sha256(_canonical_json_bytes(logical)) != reference["logical_sha256"]:
        raise ValueError("causal evidence logical SHA drifted")
    return logical
