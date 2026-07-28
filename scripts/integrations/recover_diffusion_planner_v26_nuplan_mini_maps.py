#!/usr/bin/env python3
"""Recover official nuPlan v1.1 mini plus maps without archive overwrite prompts.

The recovery consumes immutable, already-downloaded archives from a failed
attempt.  It validates the archive bytes and HTTP identities, extracts each
archive into a separate fresh staging directory, hashes every shared member,
and explicitly assembles a new dataset tree.  It never deletes or changes the
input attempt root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCHEMA = "v26_nuplan_v11_official_mini_source_recovery_v1"
ZERO_CALLS = {"model_calls": 0, "dp_calls": 0, "gpu_calls": 0}


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    if temporary.exists():
        raise FileExistsError(temporary)
    temporary.write_bytes(canonical_json_bytes(value))
    os.replace(temporary, path)


def _fresh_directory(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"fresh staging path already exists: {path}")
    path.mkdir(parents=True, exist_ok=False)


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


def validate_archive(
    path: Path,
    *,
    expected_bytes: int,
    expected_sha256: str,
    label: str,
) -> dict[str, Any]:
    """Validate immutable archive bytes and reject ambiguous members."""

    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} archive must be a regular immutable input file")
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise ValueError(f"{label} archive byte length drifted")
    actual_sha256 = sha256_path(path)
    if actual_sha256 != expected_sha256:
        raise ValueError(f"{label} archive SHA256 drifted")
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise ValueError(f"{label} archive CRC failure: {bad_member}")
        files: set[str] = set()
        for info in archive.infolist():
            _safe_relative_member(info.filename.rstrip("/"))
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError(f"{label} archive contains symlink member")
            if info.is_dir():
                continue
            if info.filename in files:
                raise ValueError(f"{label} archive contains duplicate member")
            files.add(info.filename)
    return {
        "archive_path": str(path),
        "byte_length": actual_bytes,
        "sha256": actual_sha256,
        "file_member_count": len(files),
    }


def fetch_http_identity(url: str) -> dict[str, str]:
    request = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(request, timeout=45) as response:  # noqa: S310
        etag = response.headers.get("ETag")
        length = response.headers.get("Content-Length")
        if not etag or not length:
            raise ValueError("archive HTTP identity response is incomplete")
        return {"etag": etag, "content_length": length}


def validate_http_identity(
    url: str, *, expected_etag: str, expected_bytes: int, label: str
) -> dict[str, str]:
    observed = fetch_http_identity(url)
    if observed["etag"] != expected_etag:
        raise ValueError(f"{label} archive ETag drifted")
    if observed["content_length"] != str(expected_bytes):
        raise ValueError(f"{label} archive HTTP byte length drifted")
    return observed


def extract_archive_to_fresh_stage(archive_path: Path, stage: Path) -> None:
    """Extract a single validated archive without overwrite or stdin semantics."""

    _fresh_directory(stage)
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            relative = _safe_relative_member(info.filename.rstrip("/"))
            destination = stage / relative
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, destination.open("xb") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)


def _regular_files(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"staging tree contains symlink: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in files:
            raise ValueError("staging tree has duplicate relative paths")
        files[relative] = path
    return files


def _copy_new(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as input_stream, destination.open("xb") as output_stream:
        shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
    shutil.copystat(source, destination, follow_symlinks=False)


def assemble_staged_archives(
    maps_stage: Path, mini_stage: Path, dataset_stage: Path
) -> dict[str, Any]:
    """Explicitly assemble maps and mini files after shared-file hash checks."""

    maps_files = _regular_files(maps_stage)
    mini_files = _regular_files(mini_stage)
    shared_paths = sorted(set(maps_files).intersection(mini_files))
    shared: list[dict[str, str]] = []
    for relative in shared_paths:
        maps_sha = sha256_path(maps_files[relative])
        mini_sha = sha256_path(mini_files[relative])
        if maps_sha != mini_sha:
            raise ValueError(f"shared archive member differs: {relative}")
        shared.append({"relative_path": relative, "sha256": maps_sha})

    _fresh_directory(dataset_stage)
    for files, source_name in ((maps_files, "maps"), (mini_files, "mini")):
        for relative, source in files.items():
            destination = dataset_stage / relative
            if destination.exists():
                if source_name != "mini":
                    raise ValueError(f"unexpected duplicate while assembling: {relative}")
                if sha256_path(destination) != sha256_path(source):
                    raise ValueError(f"shared archive member differs during assembly: {relative}")
                continue
            _copy_new(source, destination)
    return {
        "maps_file_count": len(maps_files),
        "mini_file_count": len(mini_files),
        "shared_file_count": len(shared),
        "shared_files": shared,
        "assembled_file_count": len(_regular_files(dataset_stage)),
    }


def validate_official_mini_layout(dataset_root: Path) -> dict[str, Any]:
    """Validate the layout actually supplied by the official mini archive.

    nuPlan v1.1 mini stores its official mini DB membership under
    ``data/cache/mini``.  It does not ship a ``nuplan-v1.1/splits/mini``
    directory, so the archive layout itself is the source split identity.
    """

    mini_db_root = dataset_root / "data" / "cache" / "mini"
    maps_root = dataset_root / "maps"
    maps_manifest = maps_root / "nuplan-maps-v1.0.json"
    if not mini_db_root.is_dir():
        raise ValueError("official mini DB root missing: data/cache/mini")
    if not maps_root.is_dir() or not maps_manifest.is_file():
        raise ValueError("official maps root or manifest is missing")

    db_paths = sorted(mini_db_root.glob("*.db"))
    map_paths = sorted(maps_root.rglob("*.gpkg"))
    if not db_paths:
        raise ValueError("official mini DB root contains no databases")
    if not map_paths:
        raise ValueError("official maps root contains no GeoPackages")
    if not maps_manifest.read_bytes().strip():
        raise ValueError("official maps manifest is empty")
    for path in [*db_paths, *map_paths]:
        with path.open("rb") as stream:
            if stream.read(16) != b"SQLite format 3\x00":
                raise ValueError(f"official SQLite source is unreadable: {path}")

    return {
        "official_mini_db_layout": "data/cache/mini",
        "official_mini_db_count": len(db_paths),
        "map_gpkg_count": len(map_paths),
        "maps_manifest_path": "maps/nuplan-maps-v1.0.json",
    }


def _scenario_builder_check(python_executable: Path) -> None:
    if not python_executable.is_file():
        raise FileNotFoundError(f"scenario-builder Python is missing: {python_executable}")
    command = (
        "from nuplan.planning.scenario_builder.nuplan_db.nuplan_scenario_builder "
        "import NuPlanScenarioBuilder; print('scenario_builder_import_ok')"
    )
    completed = subprocess.run(
        [str(python_executable), "-c", command],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if completed.returncode != 0 or "scenario_builder_import_ok" not in completed.stdout:
        raise RuntimeError("NuPlanScenarioBuilder import failed")


def _status(status: str, reason: str) -> dict[str, Any]:
    return {"schema": SCHEMA, "status": status, "reason": reason, **ZERO_CALLS}


def recover(args: argparse.Namespace) -> dict[str, Any]:
    input_root = args.input_root.resolve(strict=True)
    output_root = args.output_root.resolve(strict=False)
    if output_root.exists() or output_root.is_symlink():
        raise FileExistsError(f"recovery output root already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    output_root.mkdir()
    try:
        _write_json_atomic(output_root / "run.status.json", _status("verifying", "immutable_archives"))
        maps_path = input_root / "archives" / "maps.zip"
        mini_path = input_root / "archives" / "mini.zip"
        maps_archive = validate_archive(
            maps_path,
            expected_bytes=args.maps_bytes,
            expected_sha256=args.maps_sha256,
            label="maps",
        )
        mini_archive = validate_archive(
            mini_path,
            expected_bytes=args.mini_bytes,
            expected_sha256=args.mini_sha256,
            label="mini",
        )
        maps_http = validate_http_identity(
            args.maps_url,
            expected_etag=args.maps_etag,
            expected_bytes=args.maps_bytes,
            label="maps",
        )
        mini_http = validate_http_identity(
            args.mini_url,
            expected_etag=args.mini_etag,
            expected_bytes=args.mini_bytes,
            label="mini",
        )
        integrity = {
            "schema": SCHEMA,
            "role": "immutable_input_archive_integrity",
            "input_root": str(input_root),
            "maps": {**maps_archive, "url": args.maps_url, **maps_http},
            "mini": {**mini_archive, "url": args.mini_url, **mini_http},
            **ZERO_CALLS,
        }
        _write_json_atomic(output_root / "archive_integrity.json", integrity)
        _write_json_atomic(
            output_root / "source_manifest.json",
            {
                "schema": SCHEMA,
                "role": "raw_source_recovery",
                "input_root": str(input_root),
                "archive_integrity_sha256": hashlib.sha256(canonical_json_bytes(integrity)).hexdigest(),
                "previous_attempt_preserved": True,
                **ZERO_CALLS,
            },
        )

        _write_json_atomic(output_root / "run.status.json", _status("unpacking", "separate_fresh_staging"))
        maps_stage = output_root / "maps.stage"
        mini_stage = output_root / "mini.stage"
        dataset_stage = output_root / "dataset.stage"
        extract_archive_to_fresh_stage(maps_path, maps_stage)
        extract_archive_to_fresh_stage(mini_path, mini_stage)
        assembly = assemble_staged_archives(maps_stage, mini_stage, dataset_stage)
        layout = validate_official_mini_layout(dataset_stage)
        _scenario_builder_check(args.scenario_builder_python)
        dataset_stage.replace(output_root / "dataset")
        raw_inventory = {
            "schema": SCHEMA,
            "role": "raw_inventory",
            "db_count": layout["official_mini_db_count"],
            "map_gpkg_count": layout["map_gpkg_count"],
            "official_mini_split_present": True,
            "official_mini_db_layout": layout["official_mini_db_layout"],
            "maps_manifest_path": layout["maps_manifest_path"],
            "scenario_builder_import": "ok",
            "assembly": assembly,
            "input_archive_integrity_sha256": hashlib.sha256(canonical_json_bytes(integrity)).hexdigest(),
            **ZERO_CALLS,
        }
        _write_json_atomic(output_root / "raw_inventory.json", raw_inventory)
        _write_json_atomic(output_root / "run.status.json", _status("source_ready", "validated_explicit_assembly"))
        terminal = {"schema": SCHEMA, "terminal_status": "source_ready", "reason": "validated_explicit_assembly", **ZERO_CALLS}
        _write_json_atomic(output_root / "run.exit", terminal)
        return raw_inventory
    except Exception as error:
        failure = _status("typed_failure", type(error).__name__)
        _write_json_atomic(output_root / "run.status.json", failure)
        _write_json_atomic(
            output_root / "run.exit",
            {"schema": SCHEMA, "terminal_status": "typed_failure", "reason": type(error).__name__, **ZERO_CALLS},
        )
        raise


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--maps-url", required=True)
    parser.add_argument("--maps-etag", required=True)
    parser.add_argument("--maps-bytes", type=int, required=True)
    parser.add_argument("--maps-sha256", required=True)
    parser.add_argument("--mini-url", required=True)
    parser.add_argument("--mini-etag", required=True)
    parser.add_argument("--mini-bytes", type=int, required=True)
    parser.add_argument("--mini-sha256", required=True)
    parser.add_argument("--scenario-builder-python", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    report = recover(args)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
