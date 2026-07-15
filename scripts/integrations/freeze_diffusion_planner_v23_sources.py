#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from time import sleep
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Sequence
from urllib.parse import quote


AUTOWARE_REPOSITORY = (
    "https://github.com/autowarefoundation/autoware_universe.git"
)
AUTOWARE_COMMIT = "b8d441c59293e34289cd7bca1ba5e5a33e9189d9"
AUTOWARE_MAP_PATH = (
    "planning/behavior_path_planner/"
    "autoware_behavior_path_bidirectional_traffic_module/"
    "test_map/lanelet2_map.osm"
)
SCENARIO_REPOSITORY = "https://github.com/tier4/scenario_simulator_v2.git"
SCENARIO_COMMIT = "e22f01093fa6516c0552549ada302270329c59a4"

APACHE_2_0_OBLIGATIONS = (
    "provide recipients a copy of Apache License 2.0",
    "mark modified files with prominent change notices",
    "retain applicable copyright, patent, trademark, and attribution notices",
    "include readable upstream NOTICE attributions when NOTICE is present",
    "do not imply trademark permission beyond origin description and NOTICE reproduction",
)


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    repository: Path
    repository_url: str
    commit: str
    selection: str
    map_paths: tuple[str, ...] = ()

    @classmethod
    def exact(
        cls,
        source_id: str,
        repository: Path,
        repository_url: str,
        commit: str,
        map_paths: Sequence[str],
    ) -> "SourceSpec":
        return cls(
            source_id,
            Path(repository),
            repository_url,
            commit,
            "exact",
            tuple(map_paths),
        )

    @classmethod
    def all_osm(
        cls,
        source_id: str,
        repository: Path,
        repository_url: str,
        commit: str,
    ) -> "SourceSpec":
        return cls(
            source_id,
            Path(repository),
            repository_url,
            commit,
            "all_osm",
        )


def _git(repository: Path, *args: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def _tree(repository: Path, commit: str) -> dict[str, str]:
    raw = _git(
        repository,
        "ls-tree",
        "-r",
        "--full-tree",
        "-z",
        commit,
        binary=True,
    )
    rows: dict[str, str] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        _mode, kind, oid = metadata.decode("ascii").split()
        if kind == "blob":
            rows[path.decode("utf-8")] = oid
    return rows


def _blob(repository: Path, commit: str, path: str) -> bytes:
    for attempt in range(3):
        try:
            return _git(repository, "show", f"{commit}:{path}", binary=True)
        except subprocess.CalledProcessError as exc:
            if attempt == 2:
                detail = (exc.stderr or b"").decode("utf-8", "replace").strip()
                raise RuntimeError(
                    f"Git blob read failed for {path!r}: {detail}"
                ) from exc
            sleep(2)
    raise AssertionError("unreachable")


def _normalize_remote(url: str) -> str:
    normalized = url.strip().replace("git@github.com:", "https://github.com/")
    return normalized.removesuffix("/").removesuffix(".git").lower()


def _raw_url(repository_url: str, commit: str, path: str) -> str:
    repository = _normalize_remote(repository_url)
    prefix = "https://github.com/"
    if not repository.startswith(prefix):
        return f"{repository}/blob/{commit}/{quote(path)}"
    slug = repository[len(prefix) :]
    return f"https://raw.githubusercontent.com/{slug}/{commit}/{quote(path)}"


def _safe_path(path: str) -> PurePosixPath:
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or ".." in parsed.parts or not parsed.parts:
        raise ValueError(f"Unsafe source path: {path!r}")
    return parsed


def _validate_retrieval_time(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Retrieval time must include a timezone.")
    return value


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _git_blob_sha256(content: bytes) -> str:
    return _sha256(f"blob {len(content)}\0".encode("ascii") + content)


def freeze_sources(
    specs: Sequence[SourceSpec],
    output_dir: Path,
    retrieved_at: str,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"Output already exists: {output_dir}")
    retrieved_at = _validate_retrieval_time(retrieved_at)
    if not specs:
        raise ValueError("At least one source is required.")

    sources: list[dict[str, Any]] = []
    materials: list[tuple[dict[str, Any], bytes]] = []

    for spec in specs:
        if not re.fullmatch(r"[a-z0-9_]+", spec.source_id):
            raise ValueError(f"Invalid source ID: {spec.source_id!r}")
        commit = str(
            _git(spec.repository, "rev-parse", "--verify", f"{spec.commit}^{{commit}}")
        )
        if commit != spec.commit:
            raise ValueError(
                f"Commit mismatch for {spec.source_id}: {commit} != {spec.commit}"
            )
        actual_remote = str(_git(spec.repository, "remote", "get-url", "origin"))
        if _normalize_remote(actual_remote) != _normalize_remote(spec.repository_url):
            raise ValueError(
                f"Remote mismatch for {spec.source_id}: {actual_remote!r}"
            )

        tree = _tree(spec.repository, commit)
        if "LICENSE" not in tree:
            raise ValueError(f"{spec.source_id} has no root LICENSE at {commit}.")
        license_bytes = _blob(spec.repository, commit, "LICENSE")
        if b"Apache License" not in license_bytes or b"Version 2.0" not in license_bytes:
            raise ValueError(f"{spec.source_id} LICENSE is not Apache-2.0.")

        if spec.selection == "exact":
            map_paths = tuple(sorted(spec.map_paths))
        elif spec.selection == "all_osm":
            map_paths = tuple(sorted(path for path in tree if path.lower().endswith(".osm")))
        else:
            raise ValueError(f"Unknown selection mode: {spec.selection!r}")
        if not map_paths:
            raise ValueError(f"{spec.source_id} selected no OSM paths.")
        for path in map_paths:
            _safe_path(path)
            if not path.lower().endswith(".osm") or path not in tree:
                raise ValueError(f"Invalid or missing OSM path: {path}")

        roles = [("map", path) for path in map_paths]
        roles.append(("license", "LICENSE"))
        notice_status = "present" if "NOTICE" in tree else "absent_at_commit"
        if notice_status == "present":
            roles.append(("notice", "NOTICE"))

        source_file_hashes: list[str] = []
        source_rows: list[dict[str, Any]] = []
        for role, path in roles:
            content = _blob(spec.repository, commit, path)
            row = {
                "commit": commit,
                "file_sha256": _sha256(content),
                "git_blob_oid": tree[path],
                "git_blob_sha256": _git_blob_sha256(content),
                "raw_url": _raw_url(spec.repository_url, commit, path),
                "relative_path": path,
                "retrieved_at": retrieved_at,
                "role": role,
                "size_bytes": len(content),
                "source_id": spec.source_id,
            }
            if role == "map":
                source_file_hashes.append(row["file_sha256"])
            source_rows.append(row)
            materials.append((row, content))

        sources.append(
            {
                "commit": commit,
                "license_file_sha256": _sha256(license_bytes),
                "license_identifier": "Apache-2.0",
                "license_path": "LICENSE",
                "map_path_count": len(map_paths),
                "map_paths": list(map_paths),
                "notice_path": "NOTICE" if notice_status == "present" else None,
                "notice_status": notice_status,
                "repository_url": spec.repository_url,
                "selection": spec.selection,
                "source_id": spec.source_id,
                "unique_map_file_sha256_count": len(set(source_file_hashes)),
            }
        )

    file_rows = sorted(
        (row for row, _content in materials),
        key=lambda row: (row["source_id"], row["role"], row["relative_path"]),
    )
    map_rows = [row for row in file_rows if row["role"] == "map"]
    manifest: dict[str, Any] = {
        "apache_2_0_redistribution_obligations": list(APACHE_2_0_OBLIGATIONS),
        "excluded_sources": [
            "INTERACTION",
            "inD",
            "rounD",
            "exiD",
            "CARLA",
            "nuPlan",
            "nuScenes",
        ],
        "files": file_rows,
        "map_family_count": None,
        "map_path_count": len(map_rows),
        "original_source_bytes_modified": False,
        "retrieved_at": retrieved_at,
        "schema": "diffusion_planner_v23_source_freeze_v1",
        "sources": sources,
        "unique_map_file_sha256_count": len(
            {row["file_sha256"] for row in map_rows}
        ),
    }

    output_dir.mkdir(parents=True)
    for row, content in materials:
        relative_path = _safe_path(row["relative_path"])
        destination = output_dir / "sources" / row["source_id"] / Path(*relative_path.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freeze exact v23 Lanelet2 source and license receipts."
    )
    parser.add_argument("--autoware-repo", type=Path, required=True)
    parser.add_argument("--scenario-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--retrieved-at", required=True)
    args = parser.parse_args()

    manifest = freeze_sources(
        (
            SourceSpec.exact(
                "autoware_universe",
                args.autoware_repo,
                AUTOWARE_REPOSITORY,
                AUTOWARE_COMMIT,
                (AUTOWARE_MAP_PATH,),
            ),
            SourceSpec.all_osm(
                "scenario_simulator_v2",
                args.scenario_repo,
                SCENARIO_REPOSITORY,
                SCENARIO_COMMIT,
            ),
        ),
        args.output_dir,
        args.retrieved_at,
    )
    print(
        json.dumps(
            {
                "map_path_count": manifest["map_path_count"],
                "status": "passed",
                "unique_map_file_sha256_count": manifest[
                    "unique_map_file_sha256_count"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
