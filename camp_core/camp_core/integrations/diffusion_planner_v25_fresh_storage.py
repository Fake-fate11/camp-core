from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "camp_dp_v25_fresh_artifact_storage_qualification_v1"
REFERENCE_SCHEMA_VERSION = "camp_dp_v25_fresh_logical_file_reference_v1"
CODEC = "gzip_rfc1952_level6_mtime0"
CHUNK_BYTES = 1024 * 1024
MINIMUM_RETAINED_FREE_BYTES = 10 * 1024**3
SEAL_REVIEW_RESERVE_BYTES = 1024**3
FRESH_ARM_COUNT = 1500


def iter_regular_files(root: Path) -> list[Path]:
    """Return an exact, non-symlink inventory without leaving ``root``."""

    base = root.resolve()
    if not base.is_dir() or root.is_symlink():
        raise ValueError("storage source must be a real directory")
    files: list[Path] = []
    for current, directories, names in os.walk(base, followlinks=False):
        current_path = Path(current)
        for name in directories:
            path = current_path / name
            if path.is_symlink():
                raise ValueError("storage source contains a directory symlink")
        for name in names:
            path = current_path / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("storage source contains a symlink or special file")
            resolved = path.resolve()
            if base not in resolved.parents:
                raise ValueError("storage source path escaped its root")
            files.append(resolved)
    return sorted(files, key=lambda item: item.relative_to(base).as_posix())


def analyze_storage_tree(
    source_root: Path,
    *,
    work_root: Path,
    retained_sample_relpaths: Sequence[str] = (),
    minimum_free_bytes: int = MINIMUM_RETAINED_FREE_BYTES,
) -> dict[str, Any]:
    """Measure the exact new-artifact layout without copying the raw tree.

    Large decision-evidence JSON is deterministically streamed through gzip.
    Every compressed stream is immediately reopened and compared byte-for-byte
    by digest and size.  Only explicitly selected regression samples are kept;
    all other temporary streams are removed after measurement.
    """

    source = source_root.resolve()
    work = work_root.resolve()
    if work.exists():
        raise FileExistsError(work)
    if type(minimum_free_bytes) is not int or minimum_free_bytes < 0:
        raise ValueError("minimum free bytes must be a native nonnegative int")
    retained = _safe_relative_set(retained_sample_relpaths)
    work.mkdir(parents=True)
    sample_root = work / "retained_regression_shards"
    sample_root.mkdir()
    references: list[dict[str, Any]] = []
    try:
        for path in iter_regular_files(source):
            relative = path.relative_to(source).as_posix()
            logical_sha, logical_nbytes = _file_digest(path)
            if path.name == "decision_evidence.json":
                reference, temporary = _measure_gzip(
                    path,
                    work_root=work,
                    logical_sha256=logical_sha,
                    logical_nbytes=logical_nbytes,
                )
                reference["relative_path"] = relative
                if relative in retained:
                    destination = sample_root / f"{reference['storage_sha256']}.json.gz"
                    if destination.exists():
                        if _file_digest(destination)[0] != reference["storage_sha256"]:
                            raise ValueError("retained storage shard collision")
                        temporary.unlink()
                    else:
                        temporary.replace(destination)
                    reference["retained_regression_shard"] = (
                        f"retained_regression_shards/{destination.name}"
                    )
                else:
                    temporary.unlink()
                    reference["retained_regression_shard"] = None
            else:
                reference = {
                    "schema_version": REFERENCE_SCHEMA_VERSION,
                    "relative_path": relative,
                    "codec": "identity",
                    "logical_sha256": logical_sha,
                    "logical_nbytes": logical_nbytes,
                    "storage_sha256": logical_sha,
                    "storage_nbytes": logical_nbytes,
                    "retained_regression_shard": None,
                }
            references.append(reference)
            if shutil.disk_usage(work).free < minimum_free_bytes:
                raise RuntimeError("storage qualification would breach the retained free-space floor")
        if {row["relative_path"] for row in references if row["retained_regression_shard"]} != retained:
            raise ValueError("retained storage sample set differs from the request")
        metrics = storage_metrics(references)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_bit_exact_storage_measurement",
            "source_root": str(source),
            "file_count": len(references),
            "logical_tree_sha256": logical_tree_sha256(references),
            "references": references,
            "metrics": metrics,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        }
        _write_json(work / "storage_manifest.json", payload)
        return payload
    except BaseException:
        if work.exists():
            for temporary in work.glob(".storage-*.tmp"):
                temporary.unlink(missing_ok=True)
        raise


def validate_storage_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "schema_version",
        "status",
        "source_root",
        "file_count",
        "logical_tree_sha256",
        "references",
        "metrics",
        "fresh_b2_opened",
        "outcome_fields_consumed",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("storage manifest field set drifted")
    references = value.get("references")
    if (
        value.get("schema_version") != SCHEMA_VERSION
        or value.get("status") != "passed_bit_exact_storage_measurement"
        or type(value.get("source_root")) is not str
        or type(value.get("file_count")) is not int
        or value.get("file_count") < 1
        or type(references) is not list
        or len(references) != value["file_count"]
        or value.get("fresh_b2_opened") is not False
        or value.get("outcome_fields_consumed") != []
    ):
        raise ValueError("storage manifest authority drifted")
    validated = [_validate_reference(row) for row in references]
    paths = [row["relative_path"] for row in validated]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ValueError("storage manifest paths are not exact and ordered")
    if value.get("logical_tree_sha256") != logical_tree_sha256(validated):
        raise ValueError("storage logical tree SHA drifted")
    expected_metrics = storage_metrics(validated)
    if not _strict_equal(value.get("metrics"), expected_metrics):
        raise ValueError("storage metrics drifted")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": value["status"],
        "source_root": value["source_root"],
        "file_count": value["file_count"],
        "logical_tree_sha256": value["logical_tree_sha256"],
        "references": validated,
        "metrics": expected_metrics,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def storage_metrics(references: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    validated = [_validate_reference(row) for row in references]
    run_bytes: dict[str, int] = {}
    top_level = 0
    for row in validated:
        parts = Path(row["relative_path"]).parts
        if len(parts) >= 3 and parts[0] == "runs":
            run_bytes.setdefault(parts[1], 0)
            run_bytes[parts[1]] += row["storage_nbytes"]
        else:
            top_level += row["storage_nbytes"]
    values = sorted(run_bytes.values())
    if not values:
        raise ValueError("storage measurement has no run directories")
    maximum = values[-1]
    # The new writer first closes the canonical logical JSON, then streams it
    # into the deterministic gzip file before removing the logical preimage.
    # Count both files at that boundary; using compressed bytes alone would
    # understate the real peak precisely where capacity is tightest.
    writer_peak = max(
        row["logical_nbytes"] + row["storage_nbytes"]
        for row in validated
        if row["codec"] == CODEC
    )
    projected = (
        maximum * FRESH_ARM_COUNT
        + top_level * 5
        + writer_peak
        + SEAL_REVIEW_RESERVE_BYTES
    )
    return {
        "run_count": len(values),
        "logical_nbytes": sum(row["logical_nbytes"] for row in validated),
        "measured_storage_nbytes": sum(row["storage_nbytes"] for row in validated),
        "decision_evidence_logical_nbytes": sum(
            row["logical_nbytes"] for row in validated if row["codec"] == CODEC
        ),
        "decision_evidence_storage_nbytes": sum(
            row["storage_nbytes"] for row in validated if row["codec"] == CODEC
        ),
        "run_storage_mean_nbytes": float(sum(values) / len(values)),
        "run_storage_p95_nbytes": _nearest_rank(values, 0.95),
        "run_storage_max_nbytes": maximum,
        "top_level_storage_nbytes": top_level,
        "writer_temporary_peak_nbytes": writer_peak,
        "seal_and_review_reserve_nbytes": SEAL_REVIEW_RESERVE_BYTES,
        "projected_1500_arm_upper_bound_nbytes": projected,
        "projection_policy": "1500_times_observed_max_arm_plus_5_times_top_level_plus_raw_and_gzip_writer_peak_plus_1GiB_seal_review",
        "fresh_arm_count": FRESH_ARM_COUNT,
    }


def verify_reference_against_source(
    *, source_root: Path, artifact_root: Path, reference: Mapping[str, Any]
) -> None:
    row = _validate_reference(reference)
    source = source_root.resolve()
    path = (source / row["relative_path"]).resolve()
    if source not in path.parents or not path.is_file() or path.is_symlink():
        raise ValueError("storage reference source path is unsafe or missing")
    logical_sha, logical_nbytes = _file_digest(path)
    if logical_sha != row["logical_sha256"] or logical_nbytes != row["logical_nbytes"]:
        raise ValueError("storage logical source bytes drifted")
    if row["codec"] == CODEC:
        storage_sha, storage_nbytes, restored_sha, restored_nbytes = _gzip_facts(path)
        if (
            storage_sha != row["storage_sha256"]
            or storage_nbytes != row["storage_nbytes"]
            or restored_sha != logical_sha
            or restored_nbytes != logical_nbytes
        ):
            raise ValueError("storage gzip reconstruction drifted")
    retained = row["retained_regression_shard"]
    if retained is not None:
        root = artifact_root.resolve()
        shard = (root / retained).resolve()
        if root not in shard.parents or not shard.is_file() or shard.is_symlink():
            raise ValueError("retained storage shard is unsafe or missing")
        storage_sha, storage_nbytes = _file_digest(shard)
        if storage_sha != row["storage_sha256"] or storage_nbytes != row["storage_nbytes"]:
            raise ValueError("retained storage shard bytes drifted")
        restored_sha, restored_nbytes = _decompressed_digest(shard)
        if restored_sha != logical_sha or restored_nbytes != logical_nbytes:
                raise ValueError("retained storage shard is not bit exact")


def compress_logical_json_file(path: Path) -> dict[str, Any]:
    """Replace one canonical JSON payload with a deterministic logical shard.

    This is intended only for newly-created artifacts.  The logical SHA and
    byte count always refer to the original JSON bytes, while the stored bytes
    are RFC1952 gzip with a frozen compressor configuration.
    """

    source = path.resolve()
    if not source.is_file() or source.is_symlink() or source.name != "decision_evidence.json":
        raise ValueError("logical compression requires a real decision_evidence.json")
    logical_sha, logical_nbytes = _file_digest(source)
    reference, temporary = _measure_gzip(
        source,
        work_root=source.parent,
        logical_sha256=logical_sha,
        logical_nbytes=logical_nbytes,
    )
    storage = source.with_suffix(source.suffix + ".gz")
    receipt = source.with_suffix(".ref.json")
    if storage.exists() or receipt.exists():
        temporary.unlink(missing_ok=True)
        raise FileExistsError("logical storage target already exists")
    reference["relative_path"] = source.name
    reference["retained_regression_shard"] = storage.name
    temporary.replace(storage)
    _write_json(receipt, reference)
    source.unlink()
    return reference


def logical_tree_sha256(references: Sequence[Mapping[str, Any]]) -> str:
    logical = [
        {
            "relative_path": row["relative_path"],
            "logical_sha256": row["logical_sha256"],
            "logical_nbytes": row["logical_nbytes"],
        }
        for row in references
    ]
    return _sha256_bytes(_canonical_bytes(logical))


def _measure_gzip(
    path: Path, *, work_root: Path, logical_sha256: str, logical_nbytes: int
) -> tuple[dict[str, Any], Path]:
    handle, name = tempfile.mkstemp(prefix=".storage-", suffix=".tmp", dir=work_root)
    os.close(handle)
    temporary = Path(name)
    try:
        with path.open("rb") as source, temporary.open("wb") as target:
            with gzip.GzipFile(
                filename="", mode="wb", fileobj=target, compresslevel=6, mtime=0
            ) as compressed:
                for chunk in iter(lambda: source.read(CHUNK_BYTES), b""):
                    compressed.write(chunk)
        storage_sha, storage_nbytes = _file_digest(temporary)
        restored_sha, restored_nbytes = _decompressed_digest(temporary)
        if restored_sha != logical_sha256 or restored_nbytes != logical_nbytes:
            raise ValueError("gzip storage round trip is not bit exact")
        return (
            {
                "schema_version": REFERENCE_SCHEMA_VERSION,
                "relative_path": path.name,
                "codec": CODEC,
                "logical_sha256": logical_sha256,
                "logical_nbytes": logical_nbytes,
                "storage_sha256": storage_sha,
                "storage_nbytes": storage_nbytes,
                "retained_regression_shard": None,
            },
            temporary,
        )
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _gzip_facts(path: Path) -> tuple[str, int, str, int]:
    with tempfile.TemporaryDirectory() as raw:
        temporary_root = Path(raw)
        reference, compressed = _measure_gzip(
            path,
            work_root=temporary_root,
            logical_sha256=_file_digest(path)[0],
            logical_nbytes=path.stat().st_size,
        )
        restored_sha, restored_nbytes = _decompressed_digest(compressed)
        return (
            reference["storage_sha256"],
            reference["storage_nbytes"],
            restored_sha,
            restored_nbytes,
        )


def _decompressed_digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with gzip.open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
            total += len(chunk)
    return digest.hexdigest(), total


def _file_digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
            total += len(chunk)
    return digest.hexdigest(), total


def _validate_reference(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "schema_version",
        "relative_path",
        "codec",
        "logical_sha256",
        "logical_nbytes",
        "storage_sha256",
        "storage_nbytes",
        "retained_regression_shard",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("storage reference field set drifted")
    relative = value.get("relative_path")
    codec = value.get("codec")
    retained = value.get("retained_regression_shard")
    if (
        value.get("schema_version") != REFERENCE_SCHEMA_VERSION
        or not _safe_relative(relative)
        or codec not in {"identity", CODEC}
        or not _sha(value.get("logical_sha256"))
        or not _sha(value.get("storage_sha256"))
        or type(value.get("logical_nbytes")) is not int
        or value["logical_nbytes"] < 0
        or type(value.get("storage_nbytes")) is not int
        or value["storage_nbytes"] < 0
        or (retained is not None and not _safe_relative(retained))
        or (codec == "identity" and retained is not None)
        or (
            codec == "identity"
            and (
                value["logical_sha256"] != value["storage_sha256"]
                or value["logical_nbytes"] != value["storage_nbytes"]
            )
        )
    ):
        raise ValueError("storage reference authority drifted")
    return dict(value)


def _safe_relative(value: Any) -> bool:
    if type(value) is not str or not value or "\\" in value:
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts and path.as_posix() == value


def _safe_relative_set(values: Sequence[str]) -> set[str]:
    result: set[str] = set()
    for value in values:
        if not _safe_relative(value) or value in result:
            raise ValueError("retained storage sample path is unsafe or duplicated")
        result.add(value)
    return result


def _nearest_rank(values: Sequence[int], quantile: float) -> int:
    if not values or not 0.0 < quantile <= 1.0:
        raise ValueError("nearest-rank input is invalid")
    return sorted(values)[max(0, math.ceil(quantile * len(values)) - 1)]


def _canonical_bytes(value: Any) -> bytes:
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
    path.write_bytes(_canonical_bytes(value))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and not (set(value) - set("0123456789abcdef"))
    )


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)
