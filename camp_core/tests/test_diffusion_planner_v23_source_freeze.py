from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts.integrations.freeze_diffusion_planner_v23_sources import (
    SourceSpec,
    freeze_sources,
)


APACHE_LICENSE = "Apache License\nVersion 2.0, January 2004\n"


@dataclass(frozen=True)
class _Repo:
    path: Path
    remote: str
    commit: str


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def _make_git_repo(path: Path, files: dict[str, str], remote: str) -> _Repo:
    path.mkdir()
    subprocess.run(
        ["git", "init", "-q", str(path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _git(path, "config", "user.email", "v23-test@example.invalid")
    _git(path, "config", "user.name", "V23 Test")
    for relative_path, content in files.items():
        destination = path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="")
    _git(path, "add", "--all")
    _git(path, "commit", "-q", "-m", "fixture")
    _git(path, "remote", "add", "origin", remote)
    return _Repo(path, remote, _git(path, "rev-parse", "HEAD"))


def test_freeze_sources_preserves_git_objects_and_notice_state(
    tmp_path: Path,
) -> None:
    autoware = _make_git_repo(
        tmp_path / "autoware",
        {
            "LICENSE": APACHE_LICENSE,
            "NOTICE": "Autoware notice\n",
            "map/lanelet2_map.osm": (
                "<osm version='0.6'><relation id='9'/></osm>\n"
            ),
        },
        "https://github.com/example/autoware.git",
    )
    scenario = _make_git_repo(
        tmp_path / "scenario",
        {
            "LICENSE": APACHE_LICENSE,
            "maps/a.osm": "<osm version='0.6'/>\n",
            "maps/copy.osm": "<osm version='0.6'/>\n",
            "maps/b.osm": "<osm version='0.6'><node id='1'/></osm>\n",
            "maps/not-a-map.txt": "ignored\n",
        },
        "https://github.com/example/scenario.git",
    )
    output = tmp_path / "out"

    manifest = freeze_sources(
        (
            SourceSpec.exact(
                "autoware",
                autoware.path,
                autoware.remote,
                autoware.commit,
                ("map/lanelet2_map.osm",),
            ),
            SourceSpec.all_osm(
                "scenario",
                scenario.path,
                scenario.remote,
                scenario.commit,
            ),
        ),
        output,
        "2026-07-15T09:00:00Z",
    )

    assert manifest["map_path_count"] == 4
    assert manifest["unique_map_file_sha256_count"] == 3
    assert manifest["sources"][0]["notice_status"] == "present"
    assert manifest["sources"][1]["notice_status"] == "absent_at_commit"
    assert (
        output / "sources" / "autoware" / "map" / "lanelet2_map.osm"
    ).read_bytes() == b"<osm version='0.6'><relation id='9'/></osm>\n"
    assert all(row["git_blob_oid"] for row in manifest["files"])
    assert all(len(row["git_blob_sha256"]) == 64 for row in manifest["files"])
    assert all(len(row["file_sha256"]) == 64 for row in manifest["files"])
    assert json.loads((output / "manifest.json").read_text(encoding="utf-8")) == manifest


def test_freeze_sources_rejects_non_apache_license(tmp_path: Path) -> None:
    repo = _make_git_repo(
        tmp_path / "repo",
        {"LICENSE": "not Apache\n", "map.osm": "<osm/>\n"},
        "https://github.com/example/repo.git",
    )

    with pytest.raises(ValueError, match="Apache-2.0"):
        freeze_sources(
            (
                SourceSpec.exact(
                    "bad",
                    repo.path,
                    repo.remote,
                    repo.commit,
                    ("map.osm",),
                ),
            ),
            tmp_path / "out",
            "2026-07-15T09:00:00Z",
        )
