#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


SCHEMA = "diffusion_planner_v24_lanelet2_builder_smoke_v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative_path(value: str) -> Path:
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or not parsed.parts or ".." in parsed.parts:
        raise ValueError(f"Unsafe source path: {value!r}")
    return Path(*parsed.parts)


def build_blob_execution_plan(
    census: Mapping[str, Any],
) -> list[dict[str, Any]]:
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for row in census.get("maps", []):
        digest = str(row.get("file_sha256_receipt", ""))
        relative_path = str(row.get("relative_path", ""))
        if len(digest) != 64 or not relative_path:
            raise ValueError("Census map row lacks a frozen blob/path receipt.")
        grouped[digest].append(relative_path)
    return [
        {
            "file_sha256": digest,
            "representative_path": sorted(paths)[0],
            "paths": sorted(paths),
        }
        for digest, paths in sorted(grouped.items())
    ]


def merge_path_receipts(
    census: Mapping[str, Any],
    worker_results: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    receipts = []
    for group in build_blob_execution_plan(census):
        digest = group["file_sha256"]
        if digest not in worker_results:
            raise ValueError(f"Missing worker result for blob {digest}.")
        result = worker_results[digest]
        representative = group["representative_path"]
        for relative_path in group["paths"]:
            receipts.append(
                {
                    "relative_path": relative_path,
                    "file_sha256": digest,
                    "representative_path": representative,
                    "executed": relative_path == representative,
                    "reused_from": (
                        None if relative_path == representative else representative
                    ),
                    "status": result.get("status"),
                    "failure_category": result.get("failure_category"),
                    "source_bytes_unchanged": result.get(
                        "source_bytes_unchanged"
                    ),
                }
            )
    return sorted(receipts, key=lambda row: row["relative_path"])


def _failure_category(exc: Exception) -> str:
    message = str(exc).lower()
    if "requires the official autoware lanelet2 extension" in message:
        return "unsupported_autoware_regulatory_element"
    if "no regulatory element found" in message:
        return "unsupported_regulatory_element"
    if "project" in message or "georeferenced node" in message:
        return "projection_failure"
    return "builder_load_failure"


def _layer_counts(builder: Any) -> dict[str, int | None]:
    lanelet_map = getattr(builder, "_lanelet_map", None)

    def count(name: str) -> int | None:
        layer = getattr(lanelet_map, name, None)
        try:
            return len(layer) if layer is not None else None
        except TypeError:
            return sum(1 for _ in layer) if layer is not None else None

    return {
        "point_layer": count("pointLayer"),
        "line_string_layer": count("lineStringLayer"),
        "polygon_layer": count("polygonLayer"),
        "lanelet_layer": count("laneletLayer"),
        "regulatory_element_layer": count("regulatoryElementLayer"),
        "cached_lanelet_count": len(getattr(builder, "_cache", {})),
        "vehicle_lanelet_count": len(
            getattr(builder, "_vehicle_ll_ids", ())
        ),
    }


def smoke_one_map(map_path: Path, dp_repo: Path) -> dict[str, Any]:
    map_path = Path(map_path)
    dp_repo = Path(dp_repo)
    before = _sha256(map_path)
    result: dict[str, Any] = {
        "map_path": str(map_path),
        "dp_repo": str(dp_repo),
        "worker_pid": os.getpid(),
        "status": "failed",
        "failure_category": None,
        "error_type": None,
        "error_message": None,
        "source_sha256_before": before,
        "source_sha256_after": None,
        "source_bytes_unchanged": None,
        "regulatory_mode": None,
        "required_extended_subtypes": [],
        "projection_fallback_installed": None,
        "builder_module": None,
        "map_layer_counts": None,
        "route_loaded": False,
        "model_loaded": False,
        "candidate_generation_started": False,
        "outcome_accessed": False,
    }
    try:
        repo_root = Path(__file__).resolve().parents[2]
        for path in (repo_root, repo_root / "camp_core", dp_repo, dp_repo / "diffusion_planner"):
            value = str(path)
            if value not in sys.path:
                sys.path.insert(0, value)
        from scenario_generation.gui.lanelet_scene_builder import (
            LaneletSceneBuilder,
        )

        from camp_core.integrations.diffusion_planner import (
            install_lanelet2_projection_fallback,
            require_source_preserving_lanelet2_regulatory_adapter,
        )

        regulatory_receipt = require_source_preserving_lanelet2_regulatory_adapter(map_path)
        projection_fallback_installed = install_lanelet2_projection_fallback(map_path)
        builder = LaneletSceneBuilder(str(map_path))
        result.update(
            {
                "status": "loaded",
                "regulatory_mode": regulatory_receipt["mode"],
                "required_extended_subtypes": regulatory_receipt[
                    "required_extended_subtypes"
                ],
                "projection_fallback_installed": projection_fallback_installed,
                "builder_module": LaneletSceneBuilder.__module__,
                "map_layer_counts": _layer_counts(builder),
            }
        )
    except Exception as exc:
        result.update(
            {
                "status": "failed",
                "failure_category": _failure_category(exc),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
        )
    finally:
        after = _sha256(map_path)
        result["source_sha256_after"] = after
        result["source_bytes_unchanged"] = before == after
        if before != after:
            result.update(
                {
                    "status": "execution_invalid",
                    "failure_category": "source_bytes_changed",
                }
            )
    return result


def _parse_worker_stdout(stdout: str) -> Mapping[str, Any] | None:
    for line in reversed(stdout.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "status" in value:
            return value
    return None


def execute_builder_smokes(
    census_path: Path,
    output_dir: Path,
    dp_repo: Path,
    *,
    python_executable: str | None = None,
    worker_timeout_seconds: int = 120,
) -> dict[str, Any]:
    census_path = Path(census_path)
    output_dir = Path(output_dir)
    dp_repo = Path(dp_repo)
    if output_dir.exists():
        raise FileExistsError(f"Output already exists: {output_dir}")
    census = json.loads(census_path.read_text(encoding="utf-8"))
    if census.get("schema") != "diffusion_planner_v24_lanelet2_static_census_v1":
        raise ValueError("Unsupported v24 map census schema.")
    if census.get("builder_smoke_started") is not False:
        raise ValueError("Input census already reports builder execution.")
    manifest_path = Path(str(census["source_manifest_path"]))
    source_root = manifest_path.parent / "sources" / str(census["source_id"])
    plan = build_blob_execution_plan(census)
    output_dir.mkdir(parents=True)
    workers_dir = output_dir / "workers"
    workers_dir.mkdir()
    executable = python_executable or sys.executable
    script = Path(__file__).resolve()
    worker_results: dict[str, Mapping[str, Any]] = {}
    commands = []

    for group in plan:
        digest = group["file_sha256"]
        map_path = source_root / _safe_relative_path(group["representative_path"])
        command = [
            executable,
            str(script),
            "--worker",
            "--map-path",
            str(map_path),
            "--dp-repo",
            str(dp_repo),
        ]
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=worker_timeout_seconds,
                check=False,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            returncode = completed.returncode
            parsed = _parse_worker_stdout(stdout)
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", "replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", "replace")
            returncode = 124
            parsed = None
        elapsed = time.perf_counter() - started
        stem = digest[:16]
        stdout_path = workers_dir / f"{stem}.stdout.txt"
        stderr_path = workers_dir / f"{stem}.stderr.txt"
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        if parsed is None:
            parsed = {
                "status": "execution_invalid",
                "failure_category": (
                    "worker_timeout" if returncode == 124 else "worker_no_receipt"
                ),
                "source_bytes_unchanged": (
                    _sha256(map_path) == digest if map_path.is_file() else False
                ),
            }
        worker_result = dict(parsed)
        worker_result.update(
            {
                "file_sha256": digest,
                "representative_path": group["representative_path"],
                "paths": group["paths"],
                "worker_returncode": returncode,
                "worker_elapsed_seconds": elapsed,
                "worker_stdout": str(stdout_path.relative_to(output_dir)),
                "worker_stderr": str(stderr_path.relative_to(output_dir)),
            }
        )
        worker_results[digest] = worker_result
        commands.append(command)

    path_receipts = merge_path_receipts(census, worker_results)
    status_counts = Counter(
        str(result.get("status")) for result in worker_results.values()
    )
    failure_counts = Counter(
        str(result.get("failure_category"))
        for result in worker_results.values()
        if result.get("failure_category")
    )
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "source_census_path": str(census_path),
        "source_census_sha256": _sha256(census_path),
        "dp_repo": str(dp_repo),
        "map_path_count": len(path_receipts),
        "unique_blob_count": len(plan),
        "executed_blob_count": len(plan),
        "loaded_blob_count": status_counts.get("loaded", 0),
        "failed_blob_count": status_counts.get("failed", 0),
        "execution_invalid_blob_count": status_counts.get(
            "execution_invalid", 0
        ),
        "loaded_path_count": sum(
            receipt["status"] == "loaded" for receipt in path_receipts
        ),
        "failure_category_counts": dict(sorted(failure_counts.items())),
        "commands": commands,
        "blob_plan": plan,
        "worker_results": worker_results,
        "path_receipts": path_receipts,
        "source_bytes_unchanged": all(
            receipt["source_bytes_unchanged"] for receipt in path_receipts
        ),
        "builder_smoke_started": True,
        "builder_smoke_completed": True,
        "route_census_started": False,
        "model_loaded": False,
        "candidate_generation_started": False,
        "outcome_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
    }
    (output_dir / "builder_smoke.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run isolated v24 fixed-DP Lanelet2 builder smokes."
    )
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--map-path", type=Path)
    parser.add_argument("--census", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--worker-timeout-seconds", type=int, default=120)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.worker:
        if args.map_path is None:
            raise ValueError("--worker requires --map-path.")
        receipt = smoke_one_map(args.map_path, args.dp_repo)
        if receipt["status"] != "loaded":
            print(
                f"{receipt['error_type']}: {receipt['error_message']}",
                file=sys.stderr,
            )
        print(json.dumps(receipt, sort_keys=True))
        return 0
    if args.census is None or args.output_dir is None:
        raise ValueError("Controller mode requires --census and --output-dir.")
    report = execute_builder_smokes(
        args.census,
        args.output_dir,
        args.dp_repo,
        worker_timeout_seconds=args.worker_timeout_seconds,
    )
    print(
        json.dumps(
            {
                "map_path_count": report["map_path_count"],
                "unique_blob_count": report["unique_blob_count"],
                "loaded_blob_count": report["loaded_blob_count"],
                "failed_blob_count": report["failed_blob_count"],
                "execution_invalid_blob_count": report[
                    "execution_invalid_blob_count"
                ],
                "loaded_path_count": report["loaded_path_count"],
                "failure_category_counts": report[
                    "failure_category_counts"
                ],
                "source_bytes_unchanged": report[
                    "source_bytes_unchanged"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
