#!/usr/bin/env python3
"""Acquire the frozen V26 three-city nuPlan DB-only source set recoverably.

The command operates only on the official Boston, Singapore, and Pittsburgh
archives named in the checked-in academic source configuration.  It obtains
only one archive at a time, resumes an existing ``.part`` file, validates the
frozen HTTP identity and ZIP structure, extracts into a fresh staging tree,
atomically promotes the verified city tree, then removes that city's ZIP.

It deliberately does not inspect scenario payloads, build candidate pools, or
invoke a model, DP, GPU, or selector.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import shutil
import stat
import struct
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "v26_nuplan_v11_three_city_raw_acquisition_v1"
DEFAULT_CITY_ORDER = ("boston", "singapore", "pittsburgh")
EXPECTED_CITIES = frozenset(DEFAULT_CITY_ORDER)
CHUNK_BYTES = 4 * 1024 * 1024
PROGRESS_BYTES = 512 * 1024 * 1024
TAIL_RANGE_BYTES = 1024 * 1024
ZERO_CALLS = {
    "model_calls": 0,
    "dp_calls": 0,
    "gpu_calls": 0,
    "latent_calls": 0,
    "generation_calls": 0,
}


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    if temporary.exists():
        raise FileExistsError(f"temporary receipt path exists: {temporary}")
    temporary.write_bytes(canonical_json_bytes(dict(value)))
    os.replace(temporary, path)


def _read_json(path: Path, label: str) -> Any:
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(f"{label} must be a regular file: {path}")
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _safe_relative_member(name: str) -> Path:
    value = PurePosixPath(name)
    if (
        not name
        or value.is_absolute()
        or any(part in {"", ".", ".."} for part in value.parts)
        or "\x00" in name
    ):
        raise ValueError(f"unsafe ZIP member path: {name!r}")
    return Path(*value.parts)


def _validate_archive_config(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping) or set(value) != {"city_archives"}:
        raise ValueError("source config must contain exactly city_archives")
    records = value["city_archives"]
    if not isinstance(records, list):
        raise ValueError("source config city_archives must be a list")
    by_city: dict[str, dict[str, Any]] = {}
    required = {
        "city",
        "map_family",
        "academic_role",
        "archive_status",
        "archive_url",
        "archive_filename",
        "content_length",
        "etag",
        "last_modified",
        "accept_ranges",
        "content_type",
    }
    for raw in records:
        if not isinstance(raw, Mapping) or set(raw) != required:
            raise ValueError("city archive fields drifted")
        item = dict(raw)
        city = _nonempty_string(item["city"], "city")
        if city in by_city:
            raise ValueError(f"duplicate city: {city}")
        for field in required - {"content_length"}:
            _nonempty_string(item[field], field)
        if not isinstance(item["content_length"], int) or item["content_length"] <= 0:
            raise ValueError("content_length must be a positive integer")
        if item["archive_status"] != "official_identity_verified":
            raise ValueError("archive identity must be frozen and verified")
        if item["accept_ranges"].lower() != "bytes":
            raise ValueError("archive must support byte-range resume")
        if item["content_type"] != "application/zip":
            raise ValueError("archive content type must be application/zip")
        if "?" in item["archive_url"] or "#" in item["archive_url"]:
            raise ValueError("archive URL must not contain a signed/query component")
        if not item["archive_url"].endswith("/" + item["archive_filename"]):
            raise ValueError("archive filename must bind URL")
        by_city[city] = item
    if frozenset(by_city) != EXPECTED_CITIES:
        raise ValueError("source config must contain exactly Boston, Singapore, Pittsburgh")
    return by_city


def _http_open(url: str, *, method: str = "GET", headers: Mapping[str, str] | None = None):
    request_headers = {"User-Agent": "camp-v26-nuplan-raw-acquisition/1"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, method=method, headers=request_headers)
    return urllib.request.urlopen(request, timeout=90)  # noqa: S310 - frozen official URL


def _verify_http_identity(spec: Mapping[str, Any]) -> dict[str, str]:
    with _http_open(str(spec["archive_url"]), method="HEAD") as response:
        headers = dict(response.headers.items())
        observed = {
            "status": str(response.status),
            "content_length": headers.get("Content-Length", ""),
            "etag": headers.get("ETag", ""),
            "accept_ranges": headers.get("Accept-Ranges", ""),
            "content_type": headers.get("Content-Type", "").split(";", 1)[0],
        }
    expected = {
        "content_length": str(spec["content_length"]),
        "etag": str(spec["etag"]),
        "accept_ranges": "bytes",
        "content_type": "application/zip",
    }
    for key, expected_value in expected.items():
        actual = observed[key]
        if key == "accept_ranges":
            actual = actual.lower()
        if actual != expected_value:
            raise ValueError(
                f"{spec['city']} HTTP identity drifted for {key}: {actual!r} != {expected_value!r}"
            )
    if observed["status"] != "200":
        raise ValueError(f"{spec['city']} HEAD status drifted: {observed['status']}")
    return observed


def _read_range(url: str, start: int, end: int) -> bytes:
    if start < 0 or end < start:
        raise ValueError("invalid HTTP byte range")
    with _http_open(url, headers={"Range": f"bytes={start}-{end}"}) as response:
        if response.status != 206:
            raise ValueError(f"range request was not honored: HTTP {response.status}")
        expected = end - start + 1
        content_range = response.headers.get("Content-Range", "")
        content_length = int(response.headers.get("Content-Length", "-1"))
        if (
            content_length != expected
            or not content_range.startswith(f"bytes {start}-{end}/")
        ):
            raise ValueError("HTTP range response identity drifted")
        data = response.read()
    if len(data) != expected:
        raise ValueError("HTTP range body length drifted")
    return data


def _zip64_extra_values(
    extra: bytes,
    *,
    need_unpacked: bool,
    need_packed: bool,
    need_offset: bool,
) -> list[int]:
    position = 0
    while position + 4 <= len(extra):
        tag, length = struct.unpack_from("<HH", extra, position)
        position += 4
        payload = extra[position : position + length]
        position += length
        if tag != 0x0001:
            continue
        cursor = 0
        values: list[int] = []

        def take_u64() -> int:
            nonlocal cursor
            if cursor + 8 > len(payload):
                raise ValueError("truncated ZIP64 extra field")
            result = struct.unpack_from("<Q", payload, cursor)[0]
            cursor += 8
            return result

        if need_unpacked:
            values.append(take_u64())
        if need_packed:
            values.append(take_u64())
        if need_offset:
            values.append(take_u64())
        return values
    raise ValueError("missing ZIP64 extra field")


def inspect_zip_central_directory(spec: Mapping[str, Any]) -> dict[str, int | bool]:
    """Read only ZIP metadata ranges and return exact extraction capacity."""

    total = int(spec["content_length"])
    tail_start = max(0, total - TAIL_RANGE_BYTES)
    tail = _read_range(str(spec["archive_url"]), tail_start, total - 1)
    eocd_at = tail.rfind(b"PK\x05\x06")
    if eocd_at < 0 or eocd_at + 22 > len(tail):
        raise ValueError("ZIP end-of-central-directory not found")
    _, _, _, _, entry_count16, cd_size32, cd_offset32, comment_len = struct.unpack_from(
        "<4s4H2LH", tail, eocd_at
    )
    if eocd_at + 22 + comment_len > len(tail):
        raise ValueError("truncated ZIP end-of-central-directory comment")
    zip64 = (
        entry_count16 == 0xFFFF
        or cd_size32 == 0xFFFFFFFF
        or cd_offset32 == 0xFFFFFFFF
    )
    if zip64:
        locator_at = eocd_at - 20
        if locator_at < 0 or tail[locator_at : locator_at + 4] != b"PK\x06\x07":
            raise ValueError("ZIP64 locator not found")
        _, _, zip64_eocd_offset, _ = struct.unpack_from("<4sIQI", tail, locator_at)
        if tail_start <= zip64_eocd_offset and zip64_eocd_offset + 56 <= total:
            local_at = zip64_eocd_offset - tail_start
            record = tail[local_at : local_at + 56]
        else:
            record = _read_range(
                str(spec["archive_url"]), zip64_eocd_offset, zip64_eocd_offset + 55
            )
        if record[:4] != b"PK\x06\x06":
            raise ValueError("ZIP64 end-of-central-directory not found")
        _, record_size, _, _, _, _, _, entry_count, cd_size, cd_offset = struct.unpack_from(
            "<4sQHHIIQQQQ", record
        )
        if record_size < 44:
            raise ValueError("invalid ZIP64 end-of-central-directory")
    else:
        entry_count, cd_size, cd_offset = entry_count16, cd_size32, cd_offset32
    if cd_size <= 0 or cd_offset + cd_size > total:
        raise ValueError("invalid ZIP central-directory bounds")
    central = _read_range(str(spec["archive_url"]), cd_offset, cd_offset + cd_size - 1)
    position = 0
    parsed_entries = 0
    file_entries = 0
    directory_entries = 0
    packed_total = 0
    unpacked_total = 0
    while position < len(central):
        if position + 46 > len(central) or central[position : position + 4] != b"PK\x01\x02":
            raise ValueError("invalid central-directory member")
        packed = struct.unpack_from("<I", central, position + 20)[0]
        unpacked = struct.unpack_from("<I", central, position + 24)[0]
        name_len, extra_len, comment_len = struct.unpack_from("<HHH", central, position + 28)
        offset = struct.unpack_from("<I", central, position + 42)[0]
        end = position + 46 + name_len + extra_len + comment_len
        if end > len(central):
            raise ValueError("truncated central-directory member")
        extra = central[position + 46 + name_len : position + 46 + name_len + extra_len]
        name = central[position + 46 : position + 46 + name_len]
        values = _zip64_extra_values(
            extra,
            need_unpacked=unpacked == 0xFFFFFFFF,
            need_packed=packed == 0xFFFFFFFF,
            need_offset=offset == 0xFFFFFFFF,
        ) if (
            unpacked == 0xFFFFFFFF or packed == 0xFFFFFFFF or offset == 0xFFFFFFFF
        ) else []
        cursor = 0
        if unpacked == 0xFFFFFFFF:
            unpacked = values[cursor]
            cursor += 1
        if packed == 0xFFFFFFFF:
            packed = values[cursor]
        parsed_entries += 1
        if name.endswith(b"/"):
            directory_entries += 1
        else:
            file_entries += 1
        packed_total += packed
        unpacked_total += unpacked
        position = end
    if parsed_entries != entry_count:
        raise ValueError(
            f"ZIP member count mismatch: parsed={parsed_entries} expected={entry_count}"
        )
    return {
        "zip64": zip64,
        "archive_bytes": total,
        "member_count": entry_count,
        "file_member_count": file_entries,
        "directory_member_count": directory_entries,
        "central_directory_offset": cd_offset,
        "central_directory_bytes": cd_size,
        "compressed_member_total_bytes": packed_total,
        "unpacked_total_bytes": unpacked_total,
    }


def _order_peak(order: Iterable[str], metadata: Mapping[str, Mapping[str, Any]]) -> int:
    retained = 0
    peak = 0
    for city in order:
        item = metadata[city]
        peak = max(peak, retained + int(item["archive_bytes"]) + int(item["unpacked_total_bytes"]))
        retained += int(item["unpacked_total_bytes"])
    return peak


def capacity_projection(
    metadata: Mapping[str, Mapping[str, Any]], order: Sequence[str]
) -> dict[str, Any]:
    if frozenset(order) != EXPECTED_CITIES or len(order) != len(EXPECTED_CITIES):
        raise ValueError("city order must list each frozen city exactly once")
    choices = [
        (tuple(candidate), _order_peak(candidate, metadata))
        for candidate in itertools.permutations(sorted(EXPECTED_CITIES))
    ]
    minimum_peak = min(value for _, value in choices)
    return {
        "chosen_order": list(order),
        "chosen_serial_peak_bytes": _order_peak(order, metadata),
        "minimum_serial_peak_bytes": minimum_peak,
        "minimum_peak_orders": [
            list(candidate) for candidate, value in choices if value == minimum_peak
        ],
        "archive_total_bytes": sum(int(item["archive_bytes"]) for item in metadata.values()),
        "unpacked_total_bytes": sum(
            int(item["unpacked_total_bytes"]) for item in metadata.values()
        ),
        "all_archives_retained_and_unpacked_peak_bytes": sum(
            int(item["archive_bytes"]) + int(item["unpacked_total_bytes"])
            for item in metadata.values()
        ),
    }


def _archive_regular(path: Path) -> None:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"archive must be a regular file: {path}")


def _validate_downloaded_archive(path: Path, spec: Mapping[str, Any]) -> dict[str, Any]:
    _archive_regular(path)
    actual_size = path.stat().st_size
    if actual_size != int(spec["content_length"]):
        raise ValueError(
            f"{spec['city']} archive length mismatch: {actual_size} != {spec['content_length']}"
        )
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise ValueError(f"{spec['city']} ZIP CRC failure: {bad_member}")
    return {"archive_sha256": sha256_file(path), "archive_bytes": actual_size}


def _download_archive(
    spec: Mapping[str, Any],
    part_path: Path,
    final_path: Path,
    progress: callable,
) -> dict[str, Any]:
    """Resume exactly one verified official object into a same-filesystem part."""

    if final_path.exists():
        _archive_regular(final_path)
        return {
            "resumed_from_bytes": final_path.stat().st_size,
            "downloaded_bytes": 0,
            "already_atomically_promoted": True,
        }
    part_path.parent.mkdir(parents=True, exist_ok=True)
    existing = part_path.stat().st_size if part_path.exists() else 0
    if part_path.exists() and (not part_path.is_file() or part_path.is_symlink()):
        raise ValueError(f"archive part path is not a regular file: {part_path}")
    expected = int(spec["content_length"])
    if existing > expected:
        raise ValueError("archive part exceeds frozen content length")
    if existing == expected:
        os.replace(part_path, final_path)
        return {"resumed_from_bytes": existing, "downloaded_bytes": 0}
    headers = {"Range": f"bytes={existing}-"} if existing else {}
    try:
        response = _http_open(str(spec["archive_url"]), headers=headers)
    except urllib.error.URLError as exc:
        raise RuntimeError(f"transport_pending: {exc.reason}") from exc
    with response:
        if existing:
            expected_status = 206
            expected_range = f"bytes {existing}-{expected - 1}/{expected}"
            if response.status != expected_status or response.headers.get("Content-Range") != expected_range:
                raise ValueError("resume range response identity drifted")
        elif response.status != 200:
            raise ValueError(f"initial archive download status drifted: {response.status}")
        content_length = int(response.headers.get("Content-Length", "-1"))
        if content_length != expected - existing:
            raise ValueError("archive response length drifted")
        observed_etag = response.headers.get("ETag", "")
        if observed_etag != str(spec["etag"]):
            raise ValueError("archive response ETag drifted")
        written = existing
        next_progress = ((written // PROGRESS_BYTES) + 1) * PROGRESS_BYTES
        with part_path.open("ab") as stream:
            while True:
                block = response.read(CHUNK_BYTES)
                if not block:
                    break
                stream.write(block)
                written += len(block)
                if written >= next_progress:
                    progress(written, expected)
                    next_progress += PROGRESS_BYTES
            stream.flush()
            os.fsync(stream.fileno())
    if written != expected:
        raise RuntimeError(
            f"transport_pending: downloaded {written} of frozen {expected} bytes"
        )
    os.replace(part_path, final_path)
    return {"resumed_from_bytes": existing, "downloaded_bytes": written - existing}


def _fresh_directory(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"fresh directory already exists: {path}")
    path.mkdir(parents=True, exist_ok=False)


def _next_fresh_stage(run_root: Path, city: str) -> Path:
    """Do not overwrite a partial extraction if a recovery process resumes."""

    base = run_root / "staging" / f"{city}.extract"
    if not base.exists() and not base.is_symlink():
        return base
    suffix = 1
    while True:
        candidate = run_root / "staging" / f"{city}.extract.resume-{suffix}"
        if not candidate.exists() and not candidate.is_symlink():
            return candidate
        suffix += 1


def _extract_verified_archive(
    archive_path: Path, stage: Path, metadata: Mapping[str, Any]
) -> dict[str, int]:
    _fresh_directory(stage)
    file_count = 0
    byte_count = 0
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            relative = _safe_relative_member(info.filename.rstrip("/"))
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError(f"archive contains symlink member: {info.filename}")
            destination = stage / relative
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, destination.open("xb") as target:
                shutil.copyfileobj(source, target, length=CHUNK_BYTES)
            actual = destination.stat().st_size
            if actual != info.file_size:
                raise ValueError(f"extracted member size drifted: {info.filename}")
            file_count += 1
            byte_count += actual
    if file_count != int(metadata.get("file_member_count", metadata["member_count"])):
        raise ValueError("extracted file count drifted from central directory")
    if byte_count != int(metadata["unpacked_total_bytes"]):
        raise ValueError("extracted byte count drifted from central directory")
    return {"file_count": file_count, "unpacked_bytes": byte_count}


def _acquire_lock(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, canonical_json_bytes({"pid": os.getpid(), "created_at": int(time.time())}))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _release_own_lock(path: Path) -> None:
    if path.is_file() and not path.is_symlink():
        path.unlink()


def _load_completed_cities(run_root: Path, order: Sequence[str]) -> list[dict[str, Any]]:
    """Recover only completed city roots, never recreating their receipts."""

    completed: list[dict[str, Any]] = []
    receipts_root = run_root / "city_receipts"
    gap_seen = False
    for city in order:
        receipt_path = receipts_root / f"{city}.json"
        city_root = run_root / "raw_cities" / city
        if not receipt_path.exists():
            gap_seen = True
            continue
        if gap_seen:
            raise ValueError("city completion receipts are not a prefix of the frozen order")
        receipt = _read_json(receipt_path, f"{city} completion receipt")
        if (
            not isinstance(receipt, Mapping)
            or receipt.get("city") != city
            or receipt.get("terminal_status") != "complete"
            or not city_root.is_dir()
            or city_root.is_symlink()
        ):
            raise ValueError(f"{city} completed receipt/root drifted")
        completed.append(
            {
                "city": city,
                "receipt_path": str(receipt_path),
                "receipt_sha256": _nonempty_string(receipt.get("receipt_sha256"), "receipt_sha256"),
            }
        )
    return completed


def _remaining_peak(order: Sequence[str], metadata: Mapping[str, Mapping[str, Any]], completed: int) -> int:
    retained = 0
    peak = 0
    for city in order[completed:]:
        item = metadata[city]
        peak = max(peak, retained + int(item["archive_bytes"]) + int(item["unpacked_total_bytes"]))
        retained += int(item["unpacked_total_bytes"])
    return peak


def _status_base(
    *,
    run_root: Path,
    source_config: Path,
    source_config_sha256: str,
    camp_source_head: str,
    capacity: Mapping[str, Any],
    calls: Mapping[str, int] = ZERO_CALLS,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_role": "development_nonholdout_official_nuplan_raw_acquisition",
        "run_root": str(run_root),
        "source_config": str(source_config),
        "source_config_sha256": source_config_sha256,
        "camp_source_head": camp_source_head,
        "calls": dict(calls),
        "capacity_projection": dict(capacity),
        "outcome_fields_consumed": [],
    }


def acquire(args: argparse.Namespace) -> dict[str, Any]:
    source_config = args.source_config.resolve()
    config = _read_json(source_config, "source config")
    by_city = _validate_archive_config(config)
    order = tuple(args.city_order)
    if frozenset(order) != EXPECTED_CITIES or len(order) != 3:
        raise ValueError("--city-order must contain Boston, Singapore, Pittsburgh exactly once")
    run_root = args.run_root.resolve()
    if run_root.is_symlink():
        raise ValueError(f"run root must not be a symlink: {run_root}")
    existing_root = run_root.exists()
    if existing_root and not args.resume:
        raise FileExistsError(f"run root exists; pass --resume only for this exact root: {run_root}")
    if existing_root and not run_root.is_dir():
        raise ValueError(f"run root must be a directory: {run_root}")
    lock_path = args.lock_path.resolve()
    _acquire_lock(lock_path)
    try:
        if not existing_root:
            run_root.mkdir(parents=True, exist_ok=False)
        status_path = run_root / "run.status.json"
        exit_path = run_root / "run.exit.json"
        city_receipts = run_root / "city_receipts"
        launch_path = run_root / "launch.json"
        source_config_sha256 = sha256_file(source_config)
        if existing_root:
            launch = _read_json(launch_path, "existing launch receipt")
            expected_launch = {
                "schema_version": SCHEMA_VERSION,
                "run_root": str(run_root),
                "source_config": str(source_config),
                "source_config_sha256": source_config_sha256,
                "camp_source_head": args.camp_source_head,
                "city_order": list(order),
                "calls": dict(ZERO_CALLS),
            }
            if launch != expected_launch:
                raise ValueError("existing launch receipt does not bind this exact recovery")
            if not city_receipts.is_dir() or city_receipts.is_symlink():
                raise ValueError("existing city receipt root drifted")
        else:
            city_receipts.mkdir()
            _write_json_atomic(
                launch_path,
                {
                    "schema_version": SCHEMA_VERSION,
                    "run_root": str(run_root),
                    "source_config": str(source_config),
                    "source_config_sha256": source_config_sha256,
                    "camp_source_head": args.camp_source_head,
                    "city_order": list(order),
                    "calls": dict(ZERO_CALLS),
                },
            )
        http_identity = {city: _verify_http_identity(by_city[city]) for city in order}
        zip_metadata = {city: inspect_zip_central_directory(by_city[city]) for city in order}
        capacity = capacity_projection(zip_metadata, order)
        completed = _load_completed_cities(run_root, order) if existing_root else []
        free_bytes = shutil.disk_usage(run_root.parent).free
        capacity["free_bytes_before_download"] = free_bytes
        capacity["completed_city_count_before_run"] = len(completed)
        capacity["remaining_serial_peak_bytes"] = _remaining_peak(order, zip_metadata, len(completed))
        capacity["chosen_peak_deficit_bytes"] = max(0, int(capacity["remaining_serial_peak_bytes"]) - free_bytes)
        _write_json_atomic(
            run_root / "capacity_preflight.json",
            {
                "schema_version": SCHEMA_VERSION,
                "http_identity": http_identity,
                "zip_metadata": zip_metadata,
                "capacity_projection": capacity,
                "calls": dict(ZERO_CALLS),
            },
        )
        if capacity["chosen_peak_deficit_bytes"]:
            raise RuntimeError(
                "capacity_insufficient: "
                f"need {capacity['chosen_peak_deficit_bytes']} additional bytes"
            )
        base = _status_base(
            run_root=run_root,
            source_config=source_config,
            source_config_sha256=source_config_sha256,
            camp_source_head=args.camp_source_head,
            capacity=capacity,
        )
        completed_cities = {item["city"] for item in completed}
        for city in order:
            if city in completed_cities:
                continue
            spec = by_city[city]
            city_root = run_root / "raw_cities" / city
            archive_root = run_root / "archives" / city
            part_path = archive_root / f"{spec['archive_filename']}.part"
            archive_path = archive_root / str(spec["archive_filename"])
            stage = _next_fresh_stage(run_root, city)
            if city_root.exists() or city_root.is_symlink():
                raise FileExistsError(f"unexpected pre-existing city output for {city}")
            current: dict[str, Any] = {**base, "status": "running", "current_city": city, "completed_cities": completed}
            _write_json_atomic(status_path, current)

            def progress(written: int, expected: int, *, city_name: str = city) -> None:
                _write_json_atomic(
                    status_path,
                    {
                        **base,
                        "status": "running",
                        "current_city": city_name,
                        "download_progress": {"written_bytes": written, "expected_bytes": expected},
                        "completed_cities": completed,
                    },
                )

            transfer = _download_archive(spec, part_path, archive_path, progress)
            archive_verification = _validate_downloaded_archive(archive_path, spec)
            extracted = _extract_verified_archive(archive_path, stage, zip_metadata[city])
            city_root.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage, city_root)
            archive_path.unlink()
            receipt = {
                "schema_version": SCHEMA_VERSION,
                "city": city,
                "source": spec,
                "http_identity": http_identity[city],
                "zip_metadata": zip_metadata[city],
                "transfer": transfer,
                "archive_verification": archive_verification,
                "extraction_verification": extracted,
                "raw_city_root": str(city_root),
                "archive_deleted_after_verified_extraction": True,
                "calls": dict(ZERO_CALLS),
                "outcome_fields_consumed": [],
                "terminal_status": "complete",
            }
            receipt["receipt_sha256"] = canonical_json_sha256(receipt)
            _write_json_atomic(city_receipts / f"{city}.json", receipt)
            completed.append(
                {
                    "city": city,
                    "receipt_path": str(city_receipts / f"{city}.json"),
                    "receipt_sha256": receipt["receipt_sha256"],
                }
            )

        source_manifest = {
            **base,
            "terminal_status": "complete",
            "city_order": list(order),
            "completed_cities": completed,
            "raw_city_count": len(completed),
            "next_stage": "v26_nuplan_source_inventory_then_grouped_split",
        }
        source_manifest["source_manifest_sha256"] = canonical_json_sha256(source_manifest)
        _write_json_atomic(run_root / "source_manifest.json", source_manifest)
        terminal = {
            **base,
            "terminal_status": "complete",
            "completed_cities": completed,
            "source_manifest_path": str(run_root / "source_manifest.json"),
            "source_manifest_sha256": source_manifest["source_manifest_sha256"],
            "calls": dict(ZERO_CALLS),
        }
        _write_json_atomic(exit_path, terminal)
        _write_json_atomic(status_path, terminal)
        return terminal
    except Exception as exc:
        if run_root.exists():
            failure = {
                "schema_version": SCHEMA_VERSION,
                "terminal_status": "typed_failure",
                "failure_class": type(exc).__name__,
                "failure_reason": str(exc),
                "calls": dict(ZERO_CALLS),
                "outcome_fields_consumed": [],
            }
            _write_json_atomic(run_root / "run.exit.json", failure)
            _write_json_atomic(run_root / "run.status.json", failure)
        raise
    finally:
        _release_own_lock(lock_path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-config", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--lock-path", type=Path, required=True)
    parser.add_argument("--camp-source-head", required=True)
    parser.add_argument("--city-order", nargs=3, default=list(DEFAULT_CITY_ORDER))
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    terminal = acquire(args)
    print(json.dumps(terminal, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
