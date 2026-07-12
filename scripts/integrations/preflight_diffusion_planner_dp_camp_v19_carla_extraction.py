#!/usr/bin/env python3
"""Python 3.9-only, read-only CARLA extraction preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Tuple


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_os_release(path: Path) -> str:
    values: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw or raw.lstrip().startswith("#"):
            continue
        key, value = raw.split("=", 1)
        values[key] = value.strip().strip('"').strip("'")
    return "%s-%s" % (values.get("ID", "unknown"), values.get("VERSION_ID", "unknown"))


def _last_header(path: Path, name: str) -> Optional[str]:
    prefix = name.lower() + ":"
    matches = [
        line.split(":", 1)[1].strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.lower().startswith(prefix)
    ]
    return matches[-1] if matches else None


def _listening_ports(proc_root: Path) -> List[int]:
    ports = set()
    for name in ("tcp", "tcp6"):
        path = proc_root / "net" / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="ascii", errors="replace").splitlines()[1:]:
            fields = line.split()
            if len(fields) >= 4 and fields[3] == "0A":
                ports.add(int(fields[1].split(":")[1], 16))
    return sorted(port for port in ports if port in (2000, 2001))


def _conflicting_processes(proc_root: Path, archive: Path, root: Path) -> List[int]:
    conflicts = []
    needles = (str(archive).encode(), str(root).encode())
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        argv = [part for part in raw.split(b"\0") if part]
        if not argv:
            continue
        executable = Path(os.fsdecode(argv[0])).name.lower()
        carla = executable in {"carlaue4.sh", "carlaue4-linux-shipping"}
        archive_tool = executable in {"tar", "gzip", "pigz"} and any(
            needle in raw for needle in needles
        )
        if carla or archive_tool:
            conflicts.append(int(entry.name))
    return sorted(conflicts)


def _check(
    checks: List[Dict[str, Any]], name: str, passed: bool, reason: str, detail: Any
) -> None:
    checks.append(
        {"name": name, "passed": bool(passed), "reason": reason, "detail": detail}
    )


def run_preflight(args: argparse.Namespace) -> Dict[str, Any]:
    archive = args.archive.resolve()
    inventory_path = args.archive_inventory.resolve()
    extraction_root = args.extraction_root.resolve()
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    free_bytes = shutil.disk_usage(args.disk_root).free
    projected_free = free_bytes - int(inventory["regular_file_bytes"]) - args.reserve_bytes
    ports = _listening_ports(args.proc_root)
    processes = _conflicting_processes(args.proc_root, archive, extraction_root)
    os_name = parse_os_release(args.os_release)
    checks: List[Dict[str, Any]] = []

    _check(checks, "archive_size", archive.stat().st_size == args.expected_archive_size,
           "archive size differs from frozen download", archive.stat().st_size)
    archive_sha = _sha256(archive)
    _check(checks, "archive_sha256", archive_sha == args.expected_archive_sha256,
           "archive SHA256 differs from frozen download", archive_sha)
    inventory_sha = _sha256(inventory_path)
    _check(checks, "inventory_sha256", inventory_sha == args.expected_inventory_sha256,
           "archive inventory SHA256 changed", inventory_sha)
    _check(checks, "member_count", inventory.get("member_count") == args.expected_member_count,
           "archive member count changed", inventory.get("member_count"))
    _check(checks, "regular_file_count",
           inventory.get("regular_file_count") == args.expected_regular_file_count,
           "archive regular-file count changed", inventory.get("regular_file_count"))
    _check(checks, "regular_file_bytes",
           inventory.get("regular_file_bytes") == args.expected_regular_file_bytes,
           "archive extracted byte count changed", inventory.get("regular_file_bytes"))
    _check(checks, "unsafe_paths", inventory.get("unsafe_paths") == [],
           "archive contains unsafe absolute or parent paths", inventory.get("unsafe_paths"))
    required = inventory.get("required_members", {})
    _check(checks, "required_members", bool(required) and all(required.values()),
           "launcher, PythonAPI, or maps are missing", required)
    _check(checks, "response_content_length",
           _last_header(args.response_headers, "Content-Length") == str(args.expected_archive_size),
           "download response Content-Length changed",
           _last_header(args.response_headers, "Content-Length"))
    _check(checks, "response_etag", _last_header(args.response_headers, "ETag") == args.expected_etag,
           "download response ETag changed", _last_header(args.response_headers, "ETag"))
    _check(checks, "disk_floor", projected_free >= args.floor_bytes,
           "projected free bytes after extraction and reserve are below floor", projected_free)
    _check(checks, "ports_free", not ports, "CARLA ports 2000/2001 are already listening", ports)
    _check(checks, "no_conflicting_processes", not processes,
           "CARLA or archive extraction process is already running", processes)
    _check(checks, "extraction_root_absent", not extraction_root.exists(),
           "extraction root already exists: %s" % extraction_root, str(extraction_root))
    _check(checks, "supported_os", os_name in {"ubuntu-20.04", "ubuntu-22.04"},
           "CARLA 0.9.16 packaged runtime requires supported Ubuntu", os_name)
    _check(checks, "gpu_device_present", args.gpu_device.exists(),
           "GPU device is unavailable", str(args.gpu_device))

    failed = [item for item in checks if not item["passed"]]
    return {
        "schema_version": "dp_camp_v19_carla_extraction_preflight_v1",
        "passed": not failed,
        "checks": checks,
        "failed_checks": [item["name"] for item in failed],
        "reasons": [item["reason"] for item in failed],
        "measurements": {
            "free_bytes": free_bytes,
            "regular_file_bytes": inventory["regular_file_bytes"],
            "reserve_bytes": args.reserve_bytes,
            "projected_free_after_extraction_bytes": projected_free,
            "floor_bytes": args.floor_bytes,
            "os": os_name,
        },
        "data_access": {
            "archive_rescanned": False,
            "archive_downloaded": False,
            "extraction_calls": 0,
            "simulator_calls": 0,
            "metric_calls": 0,
            "holdout_reads": 0,
        },
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# V19 CARLA Extraction Preflight",
        "",
        "- Passed: `%s`" % report["passed"],
        "- Failed checks: `%s`" % report["failed_checks"],
        "- Reasons: `%s`" % report["reasons"],
        "",
    ]
    return "\n".join(lines)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "archive_inventory", "response_headers", "extraction_root",
                 "disk_root", "proc_root", "os_release", "gpu_device", "output_json", "output_md"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("expected_archive_size", "expected_member_count",
                 "expected_regular_file_count", "expected_regular_file_bytes",
                 "floor_bytes", "reserve_bytes"):
        parser.add_argument("--" + name, type=int, required=True)
    parser.add_argument("--expected_archive_sha256", required=True)
    parser.add_argument("--expected_inventory_sha256", required=True)
    parser.add_argument("--expected_etag", required=True)
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        report = run_preflight(args)
    except Exception as exc:  # trust-boundary diagnostics must survive harness errors
        report = {
            "schema_version": "dp_camp_v19_carla_extraction_preflight_v1",
            "passed": False,
            "checks": [],
            "failed_checks": ["harness_exception"],
            "reasons": ["%s: %s" % (type(exc).__name__, exc)],
            "data_access": {"extraction_calls": 0, "simulator_calls": 0},
        }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
