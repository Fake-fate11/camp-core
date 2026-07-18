from __future__ import annotations

import hashlib
import json
import lzma
import struct
from pathlib import Path
from typing import Any, Mapping

import numpy as np


LOGICAL_SCHEMA_VERSION = "camp_dp_v25_bounded_causal_evidence_v1"
REFERENCE_SCHEMA_VERSION = "camp_dp_v25_causal_evidence_shard_reference_v1"
ARRAY_SCHEMA_VERSION = "camp_dp_v25_causal_evidence_array_v1"
ARRAY_CODEC = "canonical-metadata-plus-bitexact-array-bytes-xz6-v3"
SHARD_DIRECTORY = "causal_evidence_shards"
SHARD_SUFFIX = ".bin.xz"
_MAGIC = b"CAMP-DP-V25-ARRAY-V1\x00"

_ARRAY_CONTRACT: dict[str, tuple[tuple[int, ...], np.dtype[Any]]] = {
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
_REFERENCE_FIELDS = {
    "schema_version",
    "logical_schema_version",
    "logical_sha256",
    "arrays",
}
_ARRAY_REFERENCE_FIELDS = {
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
_METADATA_FIELDS = {
    "schema_version",
    "name",
    "dtype",
    "shape",
    "order",
    "array_sha256",
    "uncompressed_nbytes",
    "transform",
}

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


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and not (set(value) - set("0123456789abcdef"))
    )


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("causal evidence shard metadata has a duplicate key")
        result[key] = value
    return result


def _strict_metadata(data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_no_duplicate_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"nonfinite JSON token: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("causal evidence shard metadata is invalid") from exc
    if type(value) is not dict or _canonical_json_bytes(value) != data:
        raise ValueError("causal evidence shard metadata is noncanonical")
    return value


def _decode_array_shard(
    *, name: str, data: bytes, reference: Mapping[str, Any]
) -> np.ndarray:
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
    metadata = _strict_metadata(preimage[prefix:metadata_end])
    shape, dtype = _ARRAY_CONTRACT[name]
    raw = preimage[metadata_end:]
    expected_transform = (
        f"uint32-xor-axis-{_XOR_TIME_AXES[name]}-byte-shuffle4"
        if name in _XOR_TIME_AXES
        else "identity"
    )
    if (
        set(metadata) != _METADATA_FIELDS
        or metadata.get("schema_version") != ARRAY_SCHEMA_VERSION
        or metadata.get("name") != name
        or metadata.get("dtype") != dtype.str
        or metadata.get("shape") != list(shape)
        or metadata.get("order") != "C"
        or not _is_sha256(metadata.get("array_sha256"))
        or type(metadata.get("uncompressed_nbytes")) is not int
        or metadata["uncompressed_nbytes"] != len(raw)
        or metadata["uncompressed_nbytes"] != int(np.prod(shape)) * dtype.itemsize
        or metadata.get("transform") != expected_transform
        or reference.get("array_sha256") != metadata["array_sha256"]
        or reference.get("dtype") != metadata["dtype"]
        or reference.get("shape") != metadata["shape"]
        or reference.get("uncompressed_nbytes") != metadata["uncompressed_nbytes"]
        or reference.get("transform") != metadata["transform"]
    ):
        raise ValueError("causal evidence shard metadata or raw bytes drifted")
    if name in _XOR_TIME_AXES:
        shuffled = np.frombuffer(raw, dtype=np.uint8).reshape(4, -1)
        encoded = np.ascontiguousarray(shuffled.T).reshape(-1).view(
            np.uint32
        ).reshape(shape)
        restored = np.bitwise_xor.accumulate(
            encoded, axis=_XOR_TIME_AXES[name]
        )
        array = np.ascontiguousarray(restored).view(dtype).copy()
    else:
        array = np.frombuffer(raw, dtype=dtype).reshape(shape).copy()
    if _sha256(array.tobytes(order="C")) != metadata["array_sha256"]:
        raise ValueError("causal evidence shard restored array SHA drifted")
    if dtype.kind == "f" and not np.isfinite(array).all():
        raise ValueError("causal evidence shard contains nonfinite values")
    return array


def independently_materialize_causal_evidence(
    *, artifact_root: Path, reference: Mapping[str, Any]
) -> tuple[dict[str, Any], set[str]]:
    if (
        type(reference) is not dict
        or set(reference) != _REFERENCE_FIELDS
        or reference.get("schema_version") != REFERENCE_SCHEMA_VERSION
        or reference.get("logical_schema_version") != LOGICAL_SCHEMA_VERSION
        or not _is_sha256(reference.get("logical_sha256"))
        or type(reference.get("arrays")) is not dict
        or set(reference["arrays"]) != set(_ARRAY_CONTRACT)
    ):
        raise ValueError("causal evidence shard reference schema drifted")
    root = artifact_root.resolve()
    shard_root = (root / SHARD_DIRECTORY).resolve()
    arrays: dict[str, np.ndarray] = {}
    referenced: set[str] = set()
    for name, (shape, dtype) in _ARRAY_CONTRACT.items():
        item = reference["arrays"][name]
        storage_sha = item.get("storage_sha256") if type(item) is dict else None
        relative = item.get("relative_path") if type(item) is dict else None
        if (
            type(item) is not dict
            or set(item) != _ARRAY_REFERENCE_FIELDS
            or item.get("schema_version") != ARRAY_SCHEMA_VERSION
            or item.get("codec") != ARRAY_CODEC
            or not _is_sha256(storage_sha)
            or relative != f"{SHARD_DIRECTORY}/{storage_sha}{SHARD_SUFFIX}"
            or not _is_sha256(item.get("array_sha256"))
            or item.get("dtype") != dtype.str
            or item.get("shape") != list(shape)
            or type(item.get("uncompressed_nbytes")) is not int
            or item.get("transform")
            != (
                f"uint32-xor-axis-{_XOR_TIME_AXES[name]}-byte-shuffle4"
                if name in _XOR_TIME_AXES
                else "identity"
            )
        ):
            raise ValueError("causal evidence array reference value drifted")
        path = root / str(relative)
        if (
            path.is_symlink()
            or not path.is_file()
            or path.resolve().parent != shard_root
        ):
            raise ValueError("causal evidence shard path is unsafe")
        data = path.read_bytes()
        if _sha256(data) != storage_sha:
            raise ValueError("causal evidence shard storage SHA drifted")
        arrays[name] = _decode_array_shard(name=name, data=data, reference=item)
        referenced.add(str(relative))
    logical = {
        "schema_version": LOGICAL_SCHEMA_VERSION,
        **{name: arrays[name].tolist() for name in _ARRAY_CONTRACT},
    }
    if _sha256(_canonical_json_bytes(logical)) != reference["logical_sha256"]:
        raise ValueError("causal evidence logical SHA drifted")
    return logical, referenced


def expected_shard_manifest_paths(paths: list[str]) -> set[str]:
    suffix = SHARD_SUFFIX
    prefix = SHARD_DIRECTORY + "/"
    return {
        path
        for path in paths
        if path.startswith(prefix) and path.endswith(suffix)
    }
