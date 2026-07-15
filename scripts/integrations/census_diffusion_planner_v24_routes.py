#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

SCHEMA = "diffusion_planner_v24_outcome_blind_route_census_v1"
MIN_ROUTE_LENGTH_M = 80.0
MAX_HOPS = 100
SAMPLE_SPACING_M = 1.0
OVERLAP_DISTANCE_M = 3.0
MIN_OVERLAP_SAMPLES = 20
MAX_HEADING_DELTA_DEG = 15.0
TIGHT_CORRIDOR_WIDTH_M = 3.5
SHORT_PROGRESS_OPPORTUNITY_M = 100.0
FORBIDDEN_ROUTE_FIELDS = frozenset(
    {
        "collision",
        "completion",
        "near_miss",
        "safety_cost",
        "selected_index",
        "split",
    }
)


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
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


def enumerate_route_sequences(
    *,
    drivable_ids: Sequence[int],
    following_by_id: Mapping[int, Sequence[int]],
    length_by_id: Mapping[int, float],
    min_route_length_m: float = MIN_ROUTE_LENGTH_M,
    max_hops: int = MAX_HOPS,
) -> list[dict[str, Any]]:
    if not math.isfinite(min_route_length_m) or min_route_length_m <= 0:
        raise ValueError("Minimum route length must be finite and positive.")
    if isinstance(max_hops, bool) or max_hops <= 0:
        raise ValueError("Maximum route hops must be positive.")
    drivable = sorted({int(value) for value in drivable_ids})
    if any(
        lanelet_id not in length_by_id
        or not math.isfinite(float(length_by_id[lanelet_id]))
        or float(length_by_id[lanelet_id]) <= 0
        for lanelet_id in drivable
    ):
        raise ValueError("Drivable lanelet has no finite positive source length.")

    receipts = []
    for start in drivable:
        sequence = [start]
        visited = {start}
        total = float(length_by_id[start])
        current = start
        failure_reason = None
        for _ in range(max_hops):
            if total >= min_route_length_m:
                break
            following = sorted(
                {
                    int(value)
                    for value in following_by_id.get(current, ())
                    if int(value) in length_by_id
                }
            )
            if not following:
                failure_reason = "dead_end_before_80m"
                break
            unvisited = [value for value in following if value not in visited]
            if not unvisited:
                failure_reason = "cycle_before_80m"
                break
            current = unvisited[0]
            sequence.append(current)
            visited.add(current)
            total += float(length_by_id[current])
        else:
            failure_reason = "max_hops_before_80m"

        qualifying = total >= min_route_length_m
        receipts.append(
            {
                "start_lanelet_id": start,
                "lanelet_ids": sequence,
                "source_arc_length_m": total,
                "status": "qualifying" if qualifying else "below_minimum_length",
                "failure_reason": None if qualifying else failure_reason,
            }
        )
    return receipts


def deduplicate_route_records(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted((dict(record) for record in records), key=lambda row: row["record_key"])
    groups: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in ordered:
        forbidden = sorted(set(record).intersection(FORBIDDEN_ROUTE_FIELDS))
        if forbidden:
            raise ValueError(f"Route record contains forbidden fields: {forbidden}")
        family = str(record.get("map_family_id", ""))
        identity = str(record.get("identity_sha256", ""))
        if not family or len(identity) != 64:
            raise ValueError("Route record lacks family or exact identity.")
        groups[(family, identity)].append(record)

    retained = []
    receipts = []
    for members in groups.values():
        members.sort(key=lambda row: row["record_key"])
        representative = members[0]
        retained.append(representative)
        for index, member in enumerate(members):
            receipts.append(
                {
                    "record_key": member["record_key"],
                    "retained_record_key": representative["record_key"],
                    "status": (
                        "retained" if index == 0 else "exact_identity_duplicate"
                    ),
                }
            )
    retained.sort(key=lambda row: row["record_key"])
    receipts.sort(key=lambda row: row["record_key"])
    return {
        "raw_route_count": len(ordered),
        "deduplicated_route_count": len(retained),
        "duplicate_route_count": len(ordered) - len(retained),
        "retained_routes": retained,
        "receipts": receipts,
    }


def build_route_execution_plan(
    census: Mapping[str, Any],
    families: Mapping[str, Any],
    builder: Mapping[str, Any],
) -> list[dict[str, Any]]:
    paths_by_blob: defaultdict[str, list[str]] = defaultdict(list)
    for row in census.get("maps", []):
        paths_by_blob[str(row["file_sha256_receipt"])].append(
            str(row["relative_path"])
        )
    family_by_blob: dict[str, str] = {}
    for family in families.get("families", []):
        family_id = str(family["family_id"])
        for digest in family.get("blob_sha256s", []):
            digest = str(digest)
            if digest in family_by_blob:
                raise ValueError("One source blob appears in multiple map families.")
            family_by_blob[digest] = family_id

    plan = []
    for digest, result in sorted(builder.get("worker_results", {}).items()):
        if result.get("status") != "loaded":
            continue
        if digest not in paths_by_blob or digest not in family_by_blob:
            raise ValueError("Loaded builder blob has no adjudicated map family.")
        paths = sorted(paths_by_blob[digest])
        plan.append(
            {
                "file_sha256": digest,
                "map_family_id": family_by_blob[digest],
                "representative_path": paths[0],
                "paths": paths,
            }
        )
    return plan


def _route_polyline(builder: Any, lanelet_ids: Sequence[int]) -> np.ndarray:
    points: list[np.ndarray] = []
    for lanelet_id in lanelet_ids:
        centerline = np.asarray(
            builder.raw_centerline(lanelet_id), dtype=np.float64
        )[:, :2]
        if centerline.ndim != 2 or centerline.shape[0] < 2:
            raise ValueError("Lanelet centerline has insufficient source geometry.")
        if points and np.linalg.norm(points[-1] - centerline[0]) <= 1e-6:
            centerline = centerline[1:]
        points.extend(centerline)
    result = np.asarray(points, dtype=np.float64)
    if result.shape[0] < 2 or not np.isfinite(result).all():
        raise ValueError("Route centerline is empty or non-finite.")
    return result


def _sample_polyline(polyline: np.ndarray) -> tuple[list[list[float]], list[float], float]:
    segment_lengths = np.linalg.norm(np.diff(polyline, axis=0), axis=1)
    keep = np.concatenate(([True], segment_lengths > 1e-9))
    points = polyline[keep]
    segment_lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    arc = np.concatenate(([0.0], np.cumsum(segment_lengths)))
    total = float(arc[-1])
    if total <= 0:
        raise ValueError("Route centerline has zero geometric length.")
    targets = np.arange(0.0, total, SAMPLE_SPACING_M)
    if targets.size == 0 or not math.isclose(float(targets[-1]), total):
        targets = np.append(targets, total)
    sampled = np.column_stack(
        (
            np.interp(targets, arc, points[:, 0]),
            np.interp(targets, arc, points[:, 1]),
        )
    )
    derivatives = np.gradient(sampled, axis=0)
    headings = np.arctan2(derivatives[:, 1], derivatives[:, 0])
    return sampled.tolist(), headings.tolist(), total


def _route_record(
    builder: Any,
    *,
    lanelet_ids: Sequence[int],
    source_arc_length_m: float,
    map_path: Path,
    map_sha256: str,
    map_family_id: str,
) -> dict[str, Any]:
    samples, headings, geometry_length = _sample_polyline(
        _route_polyline(builder, lanelet_ids)
    )
    geometry_sha = _canonical_sha256(
        [[round(x, 3), round(y, 3)] for x, y in samples]
    )
    logical_map_sha = hashlib.sha256(map_family_id.encode("utf-8")).hexdigest()
    identity = _canonical_sha256(
        {
            "logical_map_sha256": logical_map_sha,
            "source_geometry_sha256": geometry_sha,
        }
    )
    boundary_ids = sorted(
        {
            int(boundary.id)
            for lanelet_id in lanelet_ids
            for boundary in (
                builder._ll_by_id[lanelet_id].leftBound,
                builder._ll_by_id[lanelet_id].rightBound,
            )
        }
    )
    widths = np.concatenate(
        [
            np.linalg.norm(
                builder._cache[lanelet_id].interp_left
                - builder._cache[lanelet_id].interp_right,
                axis=1,
            )
            for lanelet_id in lanelet_ids
        ]
    )
    traffic_lights = set(builder.get_traffic_light_groups())
    route_spec = {
        "map_path": str(map_path),
        "lanelet_ids": list(lanelet_ids),
        "start_pose": [*samples[0], headings[0]],
        "goal_pose": [*samples[-1], headings[-1]],
        "route_length_m": geometry_length,
    }
    route_serialization_sha = _canonical_sha256(route_spec)
    return {
        "record_key": (
            f"{map_family_id}/{map_sha256[:16]}/{lanelet_ids[0]}/"
            f"{identity[:16]}"
        ),
        "identity_sha256": identity,
        "logical_map_sha256": logical_map_sha,
        "logical_map_name": map_family_id,
        "map_family_id": map_family_id,
        "source_map_path": str(map_path),
        "source_map_sha256": map_sha256,
        "lanelet_ids": list(lanelet_ids),
        "boundary_ids": boundary_ids,
        "centerline_samples_m": samples,
        "centerline_headings_rad": headings,
        "topology_complex": None,
        "entry_arm": None,
        "exit_arm": None,
        "source_stratum": {
            "traffic_light": bool(set(lanelet_ids).intersection(traffic_lights)),
            "branch_intersection": any(
                len(builder._routing_graph.following(builder._ll_by_id[value])) > 1
                for value in lanelet_ids
            ),
            "tight_corridor": float(widths.min()) <= TIGHT_CORRIDOR_WIDTH_M,
            "short_progress_opportunity": (
                geometry_length <= SHORT_PROGRESS_OPPORTUNITY_M
            ),
        },
        "holdout_forbidden": False,
        "route_spec": route_spec,
        "route_serialization_sha256": route_serialization_sha,
        "source_geometry_sha256": geometry_sha,
        "minimum_source_corridor_width_m": float(widths.min()),
        "source_arc_length_m": source_arc_length_m,
        "source_route_length_m": geometry_length,
    }


def route_census_one_map(
    map_path: Path,
    dp_repo: Path,
    *,
    map_family_id: str,
    expected_sha256: str,
) -> dict[str, Any]:
    map_path = Path(map_path)
    dp_repo = Path(dp_repo)
    before = _file_sha256(map_path)
    result: dict[str, Any] = {
        "status": "failed",
        "failure_category": None,
        "error_type": None,
        "error_message": None,
        "worker_pid": os.getpid(),
        "source_sha256_before": before,
        "source_sha256_after": None,
        "source_bytes_unchanged": None,
        "drivable_start_lanelet_count": 0,
        "attempt_receipts": [],
        "route_records": [],
    }
    try:
        if before != expected_sha256:
            raise ValueError("Frozen map SHA does not match worker input.")
        for path in (ROOT, PACKAGE_ROOT, dp_repo, dp_repo / "diffusion_planner"):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        from scenario_generation.gui.lanelet_scene_builder import (
            LaneletSceneBuilder,
        )
        from camp_core.integrations.diffusion_planner import (
            install_lanelet2_projection_fallback,
            require_source_preserving_lanelet2_regulatory_adapter,
        )

        require_source_preserving_lanelet2_regulatory_adapter(map_path)
        install_lanelet2_projection_fallback(map_path)
        builder = LaneletSceneBuilder(str(map_path))
        drivable = sorted(int(value) for value in builder._vehicle_ll_ids)
        length_by_id = {
            lanelet_id: float(builder._cache[lanelet_id].arc_length)
            for lanelet_id in drivable
            if lanelet_id in builder._cache
        }
        following_by_id = {
            lanelet_id: sorted(
                int(item.id)
                for item in builder._routing_graph.following(
                    builder._ll_by_id[lanelet_id]
                )
                if int(item.id) in length_by_id
            )
            for lanelet_id in length_by_id
        }
        attempts = enumerate_route_sequences(
            drivable_ids=sorted(length_by_id),
            following_by_id=following_by_id,
            length_by_id=length_by_id,
        )
        records = [
            _route_record(
                builder,
                lanelet_ids=receipt["lanelet_ids"],
                source_arc_length_m=receipt["source_arc_length_m"],
                map_path=map_path,
                map_sha256=expected_sha256,
                map_family_id=map_family_id,
            )
            for receipt in attempts
            if receipt["status"] == "qualifying"
        ]
        result.update(
            {
                "status": "completed",
                "drivable_start_lanelet_count": len(attempts),
                "attempt_receipts": attempts,
                "route_records": records,
            }
        )
    except Exception as exc:
        result.update(
            {
                "failure_category": "route_census_worker_failure",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
        )
    finally:
        after = _file_sha256(map_path)
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


def execute_route_census(
    census_path: Path,
    families_path: Path,
    builder_smoke_path: Path,
    output_dir: Path,
    dp_repo: Path,
    *,
    python_executable: str | None = None,
    worker_timeout_seconds: int = 600,
) -> dict[str, Any]:
    census_path = Path(census_path)
    families_path = Path(families_path)
    builder_smoke_path = Path(builder_smoke_path)
    output_dir = Path(output_dir)
    dp_repo = Path(dp_repo)
    if output_dir.exists():
        raise FileExistsError(f"Output already exists: {output_dir}")
    census = json.loads(census_path.read_text(encoding="utf-8"))
    families = json.loads(families_path.read_text(encoding="utf-8"))
    builder = json.loads(builder_smoke_path.read_text(encoding="utf-8"))
    if census.get("schema") != "diffusion_planner_v24_lanelet2_static_census_v1":
        raise ValueError("Unsupported v24 static census schema.")
    if families.get("schema") != "diffusion_planner_v24_map_family_adjudication_v1":
        raise ValueError("Unsupported v24 map-family schema.")
    if builder.get("schema") != "diffusion_planner_v24_lanelet2_builder_smoke_v1":
        raise ValueError("Unsupported v24 builder-smoke schema.")
    if any(
        source.get(field) is not False
        for source, field in (
            (census, "route_census_started"),
            (families, "route_census_started"),
            (families, "outcome_accessed"),
            (builder, "route_census_started"),
            (builder, "model_loaded"),
            (builder, "candidate_generation_started"),
            (builder, "outcome_accessed"),
        )
    ):
        raise ValueError("An input crossed the frozen route-census boundary.")

    plan = build_route_execution_plan(census, families, builder)
    manifest_path = Path(str(census["source_manifest_path"]))
    source_root = manifest_path.parent / "sources" / str(census["source_id"])
    output_dir.mkdir(parents=True)
    workers_dir = output_dir / "workers"
    workers_dir.mkdir()
    executable = python_executable or sys.executable
    script = Path(__file__).resolve()
    worker_results: dict[str, dict[str, Any]] = {}
    commands = []

    for item in plan:
        digest = item["file_sha256"]
        map_path = source_root / _safe_relative_path(item["representative_path"])
        command = [
            executable,
            str(script),
            "--worker",
            "--map-path",
            str(map_path),
            "--map-family-id",
            item["map_family_id"],
            "--expected-sha256",
            digest,
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
                    map_path.is_file() and _file_sha256(map_path) == digest
                ),
                "drivable_start_lanelet_count": 0,
                "attempt_receipts": [],
                "route_records": [],
            }
        worker = dict(parsed)
        worker.update(
            {
                "file_sha256": digest,
                "map_family_id": item["map_family_id"],
                "representative_path": item["representative_path"],
                "paths": item["paths"],
                "worker_returncode": returncode,
                "worker_elapsed_seconds": elapsed,
                "worker_stdout": str(stdout_path.relative_to(output_dir)),
                "worker_stderr": str(stderr_path.relative_to(output_dir)),
            }
        )
        worker_results[digest] = worker
        commands.append(command)

    raw_routes = [
        route
        for worker in worker_results.values()
        if worker.get("status") == "completed"
        for route in worker.get("route_records", [])
    ]
    deduplication = deduplicate_route_records(raw_routes)
    retained_routes = deduplication["retained_routes"]
    if retained_routes:
        from camp_core.integrations.diffusion_planner_v22_split import (
            build_leakage_groups,
        )

        grouping = build_leakage_groups(
            retained_routes,
            overlap_distance_m=OVERLAP_DISTANCE_M,
            min_overlap_samples=MIN_OVERLAP_SAMPLES,
            max_heading_delta_deg=MAX_HEADING_DELTA_DEG,
        )
    else:
        grouping = {
            "schema_version": "v22_route_leakage_groups_v1",
            "source_only": True,
            "outcome_fields_consumed": [],
            "thresholds": {
                "sample_spacing_m": SAMPLE_SPACING_M,
                "overlap_distance_m": OVERLAP_DISTANCE_M,
                "min_overlap_samples": MIN_OVERLAP_SAMPLES,
                "max_heading_delta_deg": MAX_HEADING_DELTA_DEG,
            },
            "route_records": [],
            "edges": [],
            "groups": [],
        }

    census_by_path = {
        str(row["relative_path"]): row for row in census.get("maps", [])
    }
    builder_by_path = {
        str(row["relative_path"]): row for row in builder.get("path_receipts", [])
    }
    worker_by_path = {
        path: worker
        for worker in worker_results.values()
        for path in worker["paths"]
    }
    map_receipts = []
    for path in sorted(census_by_path):
        worker = worker_by_path.get(path)
        builder_receipt = builder_by_path[path]
        map_receipts.append(
            {
                "relative_path": path,
                "file_sha256": census_by_path[path]["file_sha256_receipt"],
                "builder_status": builder_receipt["status"],
                "route_census_status": (
                    worker["status"] if worker else "excluded_before_route_census"
                ),
                "route_census_failure_category": (
                    worker.get("failure_category")
                    if worker
                    else builder_receipt.get("failure_category")
                ),
                "executed": bool(
                    worker and path == worker["representative_path"]
                ),
                "reused_from": (
                    None
                    if not worker or path == worker["representative_path"]
                    else worker["representative_path"]
                ),
                "source_bytes_unchanged": (
                    worker.get("source_bytes_unchanged")
                    if worker
                    else builder_receipt.get("source_bytes_unchanged")
                ),
            }
        )

    status_counts = Counter(worker["status"] for worker in worker_results.values())
    attempts = [
        receipt
        for worker in worker_results.values()
        for receipt in worker.get("attempt_receipts", [])
    ]
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "source_census_path": str(census_path),
        "source_map_families_path": str(families_path),
        "source_builder_smoke_path": str(builder_smoke_path),
        "dp_repo": str(dp_repo),
        "thresholds": {
            "minimum_route_length_m": MIN_ROUTE_LENGTH_M,
            "maximum_hops": MAX_HOPS,
            "sample_spacing_m": SAMPLE_SPACING_M,
            "overlap_distance_m": OVERLAP_DISTANCE_M,
            "minimum_overlap_samples": MIN_OVERLAP_SAMPLES,
            "maximum_heading_delta_deg": MAX_HEADING_DELTA_DEG,
        },
        "route_selection_rule": "smallest_numeric_unvisited_successor",
        "map_path_count": len(map_receipts),
        "eligible_blob_count": len(plan),
        "completed_blob_count": status_counts.get("completed", 0),
        "failed_blob_count": status_counts.get("failed", 0),
        "execution_invalid_blob_count": status_counts.get("execution_invalid", 0),
        "start_lanelet_attempt_count": len(attempts),
        "qualifying_start_lanelet_count": sum(
            receipt["status"] == "qualifying" for receipt in attempts
        ),
        "below_minimum_start_lanelet_count": sum(
            receipt["status"] == "below_minimum_length" for receipt in attempts
        ),
        "raw_route_count": deduplication["raw_route_count"],
        "deduplicated_route_count": deduplication["deduplicated_route_count"],
        "duplicate_route_count": deduplication["duplicate_route_count"],
        "corridor_group_count": len(grouping["groups"]),
        "commands": commands,
        "execution_plan": plan,
        "worker_results": worker_results,
        "map_receipts": map_receipts,
        "exact_deduplication_receipts": deduplication["receipts"],
        "retained_routes": retained_routes,
        "corridor_groups": grouping,
        "source_bytes_unchanged": all(
            receipt["source_bytes_unchanged"] is True for receipt in map_receipts
        ),
        "route_census_started": True,
        "route_census_completed": True,
        "model_loaded": False,
        "candidate_generation_started": False,
        "outcome_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
    }
    (output_dir / "route_census.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the outcome-blind v24 Lanelet2 route census."
    )
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--map-path", type=Path)
    parser.add_argument("--map-family-id")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--census", type=Path)
    parser.add_argument("--map-families", type=Path)
    parser.add_argument("--builder-smoke", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--worker-timeout-seconds", type=int, default=600)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.worker:
        if not all((args.map_path, args.map_family_id, args.expected_sha256)):
            raise ValueError("Worker mode requires map, family, and SHA inputs.")
        receipt = route_census_one_map(
            args.map_path,
            args.dp_repo,
            map_family_id=args.map_family_id,
            expected_sha256=args.expected_sha256,
        )
        if receipt["status"] != "completed":
            print(
                f"{receipt['error_type']}: {receipt['error_message']}",
                file=sys.stderr,
            )
        print(json.dumps(receipt, sort_keys=True))
        return 0
    if not all(
        (args.census, args.map_families, args.builder_smoke, args.output_dir)
    ):
        raise ValueError("Controller mode requires every source and output path.")
    report = execute_route_census(
        args.census,
        args.map_families,
        args.builder_smoke,
        args.output_dir,
        args.dp_repo,
        worker_timeout_seconds=args.worker_timeout_seconds,
    )
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "map_path_count",
                    "eligible_blob_count",
                    "completed_blob_count",
                    "failed_blob_count",
                    "execution_invalid_blob_count",
                    "start_lanelet_attempt_count",
                    "qualifying_start_lanelet_count",
                    "raw_route_count",
                    "deduplicated_route_count",
                    "duplicate_route_count",
                    "corridor_group_count",
                    "source_bytes_unchanged",
                )
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
