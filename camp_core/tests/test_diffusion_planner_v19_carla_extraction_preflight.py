from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys


MODULE = (
    "scripts.integrations."
    "preflight_diffusion_planner_dp_camp_v19_carla_extraction"
)


def _fixture(tmp_path: Path, *, target_exists: bool = False) -> list[str]:
    archive = tmp_path / "CARLA_0.9.16.tar.gz"
    archive.write_bytes(b"fixed-archive")
    inventory = tmp_path / "archive_inventory.json"
    inventory.write_text(
        json.dumps(
            {
                "member_count": 32857,
                "regular_file_count": 31437,
                "regular_file_bytes": 1,
                "unsafe_paths": [],
                "required_members": {
                    "launcher": True,
                    "maps": True,
                    "python_api": True,
                },
            }
        ),
        encoding="utf-8",
    )
    headers = tmp_path / "response_headers.txt"
    headers.write_text(
        "HTTP/1.1 200 OK\nContent-Length: 13\n"
        'ETag: "fixed-etag"\n',
        encoding="utf-8",
    )
    proc = tmp_path / "proc"
    (proc / "net").mkdir(parents=True)
    (proc / "net" / "tcp").write_text(
        "  sl  local_address rem_address st\n", encoding="utf-8"
    )
    (proc / "net" / "tcp6").write_text(
        "  sl  local_address rem_address st\n", encoding="utf-8"
    )
    os_release = tmp_path / "os-release"
    os_release.write_text('ID=ubuntu\nVERSION_ID="22.04"\n', encoding="utf-8")
    gpu = tmp_path / "nvidia0"
    gpu.touch()
    target = tmp_path / "runtime"
    if target_exists:
        target.mkdir()
    output_json = tmp_path / "result.json"
    output_md = tmp_path / "result.md"
    return [
        "--archive",
        str(archive),
        "--archive_inventory",
        str(inventory),
        "--response_headers",
        str(headers),
        "--extraction_root",
        str(target),
        "--disk_root",
        str(tmp_path),
        "--proc_root",
        str(proc),
        "--os_release",
        str(os_release),
        "--gpu_device",
        str(gpu),
        "--expected_archive_size",
        "13",
        "--expected_archive_sha256",
        hashlib.sha256(b"fixed-archive").hexdigest(),
        "--expected_inventory_sha256",
        hashlib.sha256(inventory.read_bytes()).hexdigest(),
        "--expected_member_count",
        "32857",
        "--expected_regular_file_count",
        "31437",
        "--expected_regular_file_bytes",
        "1",
        "--expected_etag",
        '"fixed-etag"',
        "--floor_bytes",
        "0",
        "--reserve_bytes",
        "0",
        "--output_json",
        str(output_json),
        "--output_md",
        str(output_md),
    ]


def test_cli_passes_without_path_python3_or_ss(tmp_path: Path) -> None:
    script = Path("scripts/integrations") / (
        "preflight_diffusion_planner_dp_camp_v19_carla_extraction.py"
    )
    result = subprocess.run(
        [sys.executable, str(script), *_fixture(tmp_path)],
        env={**os.environ, "PATH": ""},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert report["failed_checks"] == []


def test_failure_is_diagnostic_instead_of_assertion(tmp_path: Path) -> None:
    module = importlib.import_module(MODULE)
    result = module.main(_fixture(tmp_path, target_exists=True))

    assert result == 2
    report = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert report["passed"] is False
    assert report["failed_checks"] == ["extraction_root_absent"]
    assert report["reasons"] == [
        f"extraction root already exists: {tmp_path / 'runtime'}"
    ]


def test_os_release_parser_is_python39_compatible(tmp_path: Path) -> None:
    module = importlib.import_module(MODULE)
    path = tmp_path / "os-release"
    path.write_text('ID=ubuntu\nVERSION_ID="22.04"\n', encoding="utf-8")

    assert module.parse_os_release(path) == "ubuntu-22.04"
