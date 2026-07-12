#!/usr/bin/env python3
"""Exhaustive, source-only v19 route-speed support census and review."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_causal_atoms import (
    CANDIDATE_LOCAL_EXACT_SPEED,
    project_candidates_to_route,
)
from camp_core.integrations.diffusion_planner_v19_nuplan_bridge import (
    array_sha256,
    build_request_metadata,
    read_response,
    write_request,
)


SELECTION_SEED = 3411
NORMAL_TAGS = (
    "following_lane_without_lead",
    "medium_magnitude_speed",
)
INTERACTION_TAGS = (
    "waiting_for_pedestrian_to_cross",
    "near_pedestrian_on_crosswalk_with_ego",
    "near_multiple_vehicles",
    "high_magnitude_jerk",
    "near_pedestrian_on_crosswalk",
)
NORMAL_EXCLUDED_PREFIXES = (
    "near_",
    "waiting_",
    "changing_lane",
    "high_lateral",
    "high_magnitude_jerk",
    "starting_",
    "stopping_",
    "accelerating_",
)
PROTOCOL_RUNGS = (
    "full_window_exact_speed",
    "candidate_local_exact_speed",
    "interaction_only_candidate_local_exact_speed",
)
ACCESS_COUNTERS = {
    "expert_future_value_reads": 0,
    "simulator_advances": 0,
    "metric_computations": 0,
    "outcome_reads": 0,
}


def selection_sha256(bucket: str, row: Mapping[str, Any]) -> str:
    payload = "|".join(
        (
            str(SELECTION_SEED),
            bucket,
            str(row["log_token"]),
            str(row["scene_token"]),
            str(row["scenario_token"]),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def choose_protocol(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    prepared = []
    for value in rows:
        row = dict(value)
        row["selection_sha256"] = selection_sha256(str(row["bucket"]), row)
        prepared.append(row)

    def supported(row: Mapping[str, Any], rung: str) -> bool:
        if row.get("failure_reason") is not None:
            return False
        if row.get("v18_log_overlap") or row.get("v18_scene_overlap"):
            return False
        if rung == PROTOCOL_RUNGS[0]:
            return bool(row.get("full_window_source_complete"))
        return bool(
            row.get("candidate_local_any")
            and row.get("dp_default_source_complete")
        )

    def ordered(bucket: str, rung: str) -> list[dict[str, Any]]:
        return sorted(
            [
                row
                for row in prepared
                if row.get("bucket") == bucket and supported(row, rung)
            ],
            key=lambda row: row["selection_sha256"],
        )

    def distinct_pair(
        first: Sequence[dict[str, Any]],
        second: Sequence[dict[str, Any]],
        *,
        distinct_tags: bool = False,
    ) -> list[dict[str, Any]] | None:
        for left in first:
            for right in second:
                if left is right:
                    continue
                if left["log_token"] == right["log_token"]:
                    continue
                if left["scene_token"] == right["scene_token"]:
                    continue
                if distinct_tags and left["selection_tag"] == right["selection_tag"]:
                    continue
                return [left, right]
        return None

    selected = None
    rung = None
    for candidate_rung in PROTOCOL_RUNGS[:2]:
        selected = distinct_pair(
            ordered("normal", candidate_rung),
            ordered("interaction", candidate_rung),
        )
        if selected is not None:
            rung = candidate_rung
            break
    if selected is None:
        interaction = ordered("interaction", PROTOCOL_RUNGS[2])
        selected = distinct_pair(interaction, interaction, distinct_tags=True)
        if selected is not None:
            rung = PROTOCOL_RUNGS[2]

    support_counts = {
        candidate_rung: sum(supported(row, candidate_rung) for row in prepared)
        for candidate_rung in PROTOCOL_RUNGS
    }
    support_by_tag: dict[str, dict[str, int]] = {}
    support_by_location: dict[str, dict[str, int]] = {}
    for row in prepared:
        for key, target in (
            (str(row.get("selection_tag", "unknown")), support_by_tag),
            (str(row.get("location", "unknown")), support_by_location),
        ):
            counts = target.setdefault(
                key, {candidate_rung: 0 for candidate_rung in PROTOCOL_RUNGS}
            )
            for candidate_rung in PROTOCOL_RUNGS:
                counts[candidate_rung] += int(supported(row, candidate_rung))
    rejection_counts = collections.Counter(
        str(row.get("failure_class") or "source_rejection")
        for row in prepared
        if row.get("failure_reason") is not None
    )
    selected_rows = [] if selected is None else [dict(row) for row in selected]
    return {
        "schema_version": "dp_camp_v19_source_protocol_selection_v1",
        "selected": selected is not None,
        "exhausted": selected is None,
        "rung": rung,
        "speed_source_policy": (
            None
            if rung is None
            else (
                "full_window_exact_speed"
                if rung == PROTOCOL_RUNGS[0]
                else "candidate_local_exact_speed"
            )
        ),
        "selection_seed": SELECTION_SEED,
        "selected_scenarios": selected_rows,
        "support_counts": support_counts,
        "support_by_tag": dict(sorted(support_by_tag.items())),
        "support_by_location": dict(sorted(support_by_location.items())),
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "selection_uses_outcomes": False,
    }


def _support_matrix(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, collections.Counter[str]]] = {
        "by_tag": {},
        "by_location": {},
        "by_log": {},
        "by_scene": {},
    }
    rejections: collections.Counter[str] = collections.Counter()
    for row in rows:
        fields = {
            "total": 1,
            "full_window": int(bool(row.get("full_window_source_complete"))),
            "candidate_local": int(bool(row.get("candidate_local_any"))),
            "dp_default": int(bool(row.get("dp_default_source_complete"))),
        }
        for group, key in (
            ("by_tag", str(row.get("selection_tag", "unknown"))),
            ("by_location", str(row.get("location", "unknown"))),
            ("by_log", str(row.get("log_token", "unknown"))),
            ("by_scene", str(row.get("scene_token", "unknown"))),
        ):
            target = grouped[group]
            target.setdefault(key, collections.Counter()).update(fields)
        if row.get("failure_reason") is not None:
            rejections[str(row.get("failure_class") or "source_rejection")] += 1
    protocol = choose_protocol(rows)
    return {
        "schema_version": "dp_camp_v19_source_support_matrix_v1",
        "row_count": len(rows),
        **{
            group: {key: dict(value) for key, value in sorted(target.items())}
            for group, target in grouped.items()
        },
        "rung_support_counts": protocol["support_counts"],
        "rejection_counts": dict(sorted(rejections.items())),
        "access_counters": dict(ACCESS_COUNTERS),
    }


def write_census_artifact(
    *,
    rows: Sequence[Mapping[str, Any]],
    output_root: str | Path,
    source_loader: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    source_probe: Callable[
        [Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]
    ],
    base_smoke_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=False)
    ordered = sorted(
        (dict(row) for row in rows),
        key=lambda row: (
            selection_sha256(str(row["bucket"]), row),
            str(row["bucket"]),
        ),
    )
    persisted = []
    candidate_tensors = []
    probe_count = 0
    rejection_counts: collections.Counter[str] = collections.Counter()

    def write_progress() -> None:
        _write_json(
            root / "progress.json",
            {
                "processed_identities": len(persisted),
                "total_identities": len(ordered),
                "source_probe_count": probe_count,
                "rejection_counts": dict(sorted(rejection_counts.items())),
                "candidate_tensor_bytes": sum(
                    candidate.nbytes for candidate in candidate_tensors
                ),
                "disk_free_bytes": shutil.disk_usage(root).free,
            },
        )

    def persist(row: dict[str, Any]) -> None:
        persisted.append(row)
        if row.get("failure_reason") is not None:
            rejection_counts[str(row.get("failure_class") or "source_rejection")] += 1
        write_progress()

    for original in ordered:
        row = dict(original)
        row["selection_sha256"] = selection_sha256(str(row["bucket"]), row)
        row["candidate_tensor_index"] = None
        row["candidate_tensor_sha256"] = None
        if row.get("v18_log_overlap") or row.get("v18_scene_overlap"):
            row["failure_class"] = "V18Overlap"
            row["failure_reason"] = (
                "v18_log_overlap"
                if row.get("v18_log_overlap")
                else "v18_scene_overlap"
            )
            persist(row)
            continue
        try:
            source = dict(source_loader(row))
            causal_input = source.pop("causal_input", None)
            row.update(_jsonable(source))
            probe_source = {**source, "causal_input": causal_input}
            probe_count += 1
            probe = dict(source_probe(row, probe_source))
            candidates = np.asarray(probe["candidates"])
            mask = np.asarray(
                probe["route_speed_source_eligible_mask"], dtype=bool
            )
            if candidates.shape != (8, 80, 4) or candidates.dtype != np.float32:
                raise ValueError("source probe candidates must be float32 [8,80,4]")
            if not np.isfinite(candidates).all() or mask.shape != (8,):
                raise ValueError("source probe candidate evidence is invalid")
            row.update(
                {
                    "candidate_local_any": bool(mask.any()),
                    "candidate_local_eligible_count": int(mask.sum()),
                    "dp_default_source_complete": bool(mask[0]),
                    "route_speed_source_eligible_mask": mask.tolist(),
                    "candidate_tensor_index": len(candidate_tensors),
                    "candidate_tensor_sha256": array_sha256(candidates),
                    "failure_class": None,
                    "failure_reason": None,
                }
            )
            candidate_tensors.append(np.ascontiguousarray(candidates))
        except Exception as error:
            row.update(
                {
                    "candidate_local_any": False,
                    "candidate_local_eligible_count": 0,
                    "dp_default_source_complete": False,
                    "failure_class": type(error).__name__,
                    "failure_reason": str(error).replace("\n", " "),
                }
            )
        persist(row)

    if not persisted:
        write_progress()

    tensor_array = (
        np.stack(candidate_tensors)
        if candidate_tensors
        else np.empty((0, 8, 80, 4), dtype=np.float32)
    )
    np.save(root / "candidate_tensors.npy", tensor_array, allow_pickle=False)
    _write_jsonl(root / "census_rows.jsonl", persisted)
    matrix = _support_matrix(persisted)
    protocol = choose_protocol(persisted)
    _write_json(root / "support_matrix.json", matrix)
    _write_json(root / "selected_protocol.json", protocol)
    if protocol["selected"] and base_smoke_config is not None:
        smoke = json.loads(json.dumps(base_smoke_config))
        _write_json(root / "base_smoke_config.json", smoke)
        smoke["selected_scenarios"] = protocol["selected_scenarios"]
        smoke["selected_scenario_count"] = 2
        _write_json(root / "smoke_config.json", smoke)
    report = {
        "schema_version": "dp_camp_v19_source_support_census_v1",
        "passed": True,
        "row_count": len(persisted),
        "source_probe_count": probe_count,
        "selected": protocol["selected"],
        "exhausted": protocol["exhausted"],
        "access_counters": dict(ACCESS_COUNTERS),
        "native_ranked_top1": False,
        "baseline_name": "DP-default deterministic/MAP baseline",
    }
    _write_json(root / "OUTCOME.json", report)
    report["artifact_root_sha256"] = _seal(root)
    return report


def write_review_artifact(
    *,
    source_root: str | Path,
    output_root: str | Path,
    source_reviewer: Callable[
        [Mapping[str, Any], np.ndarray | None], Mapping[str, Any]
    ],
) -> dict[str, Any]:
    source = Path(source_root)
    _verify_seal(source)
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=False)
    rows = _read_jsonl(source / "census_rows.jsonl")
    tensors = np.load(source / "candidate_tensors.npy", allow_pickle=False)
    reviewed = []
    for persisted in rows:
        row = dict(persisted)
        index = row.get("candidate_tensor_index")
        candidates = None if index is None else np.asarray(tensors[int(index)])
        recomputed = dict(source_reviewer(row, candidates))
        if "failure_reason" in recomputed:
            if recomputed["failure_reason"] != row.get("failure_reason"):
                raise ValueError("independent failure reason mismatch")
        elif candidates is not None:
            mask = np.asarray(
                recomputed["route_speed_source_eligible_mask"], dtype=bool
            )
            if mask.shape != (8,):
                raise ValueError("independent source mask shape mismatch")
            if mask.tolist() != row.get("route_speed_source_eligible_mask"):
                raise ValueError("independent candidate-local mask mismatch")
            if bool(recomputed["full_window_source_complete"]) != bool(
                row.get("full_window_source_complete")
            ):
                raise ValueError("independent full-window support mismatch")
            row.update(
                {
                    "candidate_local_any": bool(mask.any()),
                    "candidate_local_eligible_count": int(mask.sum()),
                    "dp_default_source_complete": bool(mask[0]),
                    "full_window_source_complete": bool(
                        recomputed["full_window_source_complete"]
                    ),
                }
            )
        reviewed.append(row)
    expected_protocol = json.loads(
        (source / "selected_protocol.json").read_text(encoding="utf-8")
    )
    actual_protocol = choose_protocol(reviewed)
    if actual_protocol != expected_protocol:
        raise ValueError("independent protocol selection mismatch")
    smoke_equal = None
    if (source / "smoke_config.json").is_file():
        base_path = source / "base_smoke_config.json"
        if not base_path.is_file():
            raise ValueError("independent smoke config base is missing")
        smoke = json.loads(base_path.read_text(encoding="utf-8"))
        smoke["selected_scenarios"] = actual_protocol["selected_scenarios"]
        smoke["selected_scenario_count"] = 2
        _write_json(root / "smoke_config.json", smoke)
        source_smoke = (source / "smoke_config.json").read_bytes()
        smoke_equal = (root / "smoke_config.json").read_bytes() == source_smoke
        if not smoke_equal:
            raise ValueError("independent smoke config byte mismatch")
    _write_jsonl(root / "reviewed_rows.jsonl", reviewed)
    _write_json(root / "support_matrix.json", _support_matrix(reviewed))
    _write_json(root / "selected_protocol.json", actual_protocol)
    report = {
        "schema_version": "dp_camp_v19_source_support_review_v1",
        "passed": True,
        "reviewed_row_count": len(reviewed),
        "worker_calls": 0,
        "simulator_advances": 0,
        "metric_computations": 0,
        "outcome_reads": 0,
        "smoke_config_byte_equal": smoke_equal,
        "source_root_sha256": (source / "ROOT_SHA256").read_text().strip(),
    }
    _write_json(root / "OUTCOME.json", report)
    (root / "review.md").write_text(
        "\n".join(
            (
                "# V19 Source-Support Independent Review",
                "",
                "This review recomputed source support without fixed-DP or simulator execution.",
                "",
                f"- passed: `{report['passed']}`",
                f"- reviewed rows: `{report['reviewed_row_count']}`",
                f"- worker calls: `{report['worker_calls']}`",
                f"- simulator advances: `{report['simulator_advances']}`",
                f"- metric computations: `{report['metric_computations']}`",
                f"- selected rung: `{actual_protocol['rung']}`",
                "",
            )
        ),
        encoding="utf-8",
    )
    report["artifact_root_sha256"] = _seal(root)
    return report


def enumerate_candidate_rows(
    data_root: str | Path,
    *,
    excluded_logs: set[str],
    excluded_scenes: set[str],
) -> list[dict[str, Any]]:
    root = Path(data_root)
    rows = []
    for db_path in sorted((root / "data/cache/mini").glob("*.db")):
        uri = f"file:{db_path.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            log = db.execute(
                "SELECT lower(hex(token)), logfile, location, map_version FROM log"
            ).fetchone()
            if log is None:
                raise ValueError(f"log metadata missing: {db_path}")
            log_token, logfile, location, map_version = map(str, log)
            if log_token in excluded_logs:
                continue
            scenes = db.execute(
                "SELECT token,name,goal_ego_pose_token,roadblock_ids FROM scene "
                "ORDER BY hex(token)"
            ).fetchall()
            for scene_blob, scene_name, goal_token, raw_route in scenes:
                scene_token = bytes(scene_blob).hex()
                if scene_token in excluded_scenes:
                    continue
                route = _route_ids(raw_route)
                bounds = db.execute(
                    "SELECT min(timestamp),max(timestamp) FROM lidar_pc "
                    "WHERE scene_token=?",
                    (scene_blob,),
                ).fetchone()
                if not bounds or bounds[0] is None or bounds[1] is None:
                    continue
                start_us, end_us = map(int, bounds)
                anchors = db.execute(
                    "SELECT l.token,l.timestamp FROM scenario_tag t "
                    "JOIN lidar_pc l ON l.token=t.lidar_pc_token "
                    "WHERE l.scene_token=? AND l.timestamp>=? AND l.timestamp<=? "
                    "GROUP BY l.token,l.timestamp ORDER BY l.timestamp,hex(l.token)",
                    (scene_blob, start_us + 3_000_000, end_us - 8_000_000),
                ).fetchall()
                for lidar_blob, timestamp in anchors:
                    tags = [
                        str(item[0])
                        for item in db.execute(
                            "SELECT DISTINCT type FROM scenario_tag "
                            "WHERE lidar_pc_token=? ORDER BY type",
                            (lidar_blob,),
                        )
                    ]
                    for bucket, tag in _buckets(tags):
                        rows.append(
                            {
                                "bucket": bucket,
                                "selection_tag": tag,
                                "tags": tags,
                                "db_path": str(db_path),
                                "location": location,
                                "map_version": map_version,
                                "log_token": log_token,
                                "logfile": logfile,
                                "scene_token": scene_token,
                                "scene_name": str(scene_name),
                                "scenario_token": bytes(lidar_blob).hex(),
                                "timestamp_us": int(timestamp),
                                "past_span_s": (int(timestamp) - start_us) / 1e6,
                                "future_span_s": (end_us - int(timestamp)) / 1e6,
                                "mission_goal_available": goal_token is not None,
                                "route_roadblock_count": len(route),
                                "route_unique": len(route) == len(set(route)),
                                "route_connected": None,
                                "valid_route_slot_count": 0,
                                "finite_positive_speed_slot_count": 0,
                                "full_window_source_complete": False,
                                "candidate_local_any": False,
                                "candidate_local_eligible_count": 0,
                                "dp_default_source_complete": False,
                                "v18_log_overlap": False,
                                "v18_scene_overlap": False,
                                "failure_class": None,
                                "failure_reason": None,
                            }
                        )
    return rows


def _buckets(tags: Sequence[str]) -> list[tuple[str, str]]:
    result = []
    interaction = next((tag for tag in INTERACTION_TAGS if tag in tags), None)
    if interaction is not None:
        result.append(("interaction", interaction))
    normal = next((tag for tag in NORMAL_TAGS if tag in tags), None)
    if normal is not None and not any(
        tag.startswith(prefix) for tag in tags for prefix in NORMAL_EXCLUDED_PREFIXES
    ):
        result.append(("normal", normal))
    return result


def _route_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return [item for item in str(value).split() if item]


def load_exclusions(path: str | Path, expected_sha256: str) -> tuple[set[str], set[str]]:
    manifest = Path(path)
    if _file_sha256(manifest) != expected_sha256:
        raise ValueError("v18 exclusion manifest SHA256 mismatch")
    logs = set()
    scenes = set()
    for row in _read_jsonl(manifest):
        logs.add(str(row["log_token"]))
        scenes.add(str(row["scene_token"]))
    return logs, scenes


def _source_loader(data_root: Path, map_root: Path):
    from camp_core.integrations.nuplan_causal_adapter import (
        materialize_nuplan_planner_input,
    )
    from scripts.integrations.run_diffusion_planner_dp_camp_v19_closed_loop_smoke import (
        construct_nuplan_scenario,
        construct_simulation,
    )

    def load(row: Mapping[str, Any]) -> Mapping[str, Any]:
        scenario = construct_nuplan_scenario(
            row, data_root=data_root, map_root=map_root
        )
        simulation = construct_simulation(scenario)
        initialization = simulation.initialize()
        current_input = simulation.get_planner_input()
        materialized = materialize_nuplan_planner_input(
            current_input,
            initialization,
            speed_source_policy=CANDIDATE_LOCAL_EXACT_SPEED,
        )
        route = np.asarray(materialized.dp_input["route_lanes"])
        valid = (route[:, :, 13] > 0.5).any(axis=1)
        has_speed = np.asarray(
            materialized.dp_input["route_lanes_has_speed_limit"], dtype=bool
        ).reshape(-1)
        route_ids = tuple(str(value) for value in initialization.route_roadblock_ids)
        return {
            "causal_input": materialized.dp_input,
            "mission_goal_available": True,
            "route_roadblock_count": len(route_ids),
            "route_unique": len(route_ids) == len(set(route_ids)),
            "route_connected": True,
            "valid_route_slot_count": int(valid.sum()),
            "finite_positive_speed_slot_count": int((valid & has_speed).sum()),
            "full_window_source_complete": bool(valid.any() and has_speed[valid].all()),
        }

    return load


def _source_probe(
    *,
    probe_root: Path,
    worker_command: Sequence[str],
    camp_head: str,
    dp_head: str,
    nuplan_head: str,
    selector_hashes: tuple[str, str, str],
):
    command_template = tuple(worker_command)
    if sum("{request_dir}" in item for item in command_template) != 1:
        raise ValueError("worker command must contain one {request_dir} placeholder")
    if not any("source_probe" in item for item in command_template):
        raise ValueError("worker command must freeze the source_probe operation")
    probe_root.mkdir(parents=True, exist_ok=False)

    def probe(row: Mapping[str, Any], source: Mapping[str, Any]) -> Mapping[str, Any]:
        for name in ("request.npz", "request.json", "response.npz", "response.json"):
            path = probe_root / name
            if path.exists():
                path.unlink()
        causal_input = source["causal_input"]
        metadata = build_request_metadata(
            arm="camp",
            log_name=str(row["logfile"]),
            scenario_token=str(row["scenario_token"]),
            iteration_index=0,
            simulation_time_us=int(row["timestamp_us"]),
            scenario_seed=SELECTION_SEED,
            dp_seed_root=3412,
            camp_head=camp_head,
            dp_head=dp_head,
            nuplan_head=nuplan_head,
            causal_input=causal_input,
            selector_hashes=selector_hashes,
            speed_source_policy=CANDIDATE_LOCAL_EXACT_SPEED,
        )
        write_request(probe_root, causal_input, metadata)
        command = [item.replace("{request_dir}", str(probe_root)) for item in command_template]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            tail = (completed.stderr or completed.stdout)[-4000:]
            raise RuntimeError(f"source probe exited {completed.returncode}: {tail}")
        response = read_response(
            probe_root,
            expected_run_key=str(metadata["run_key"]),
            expected_iteration_index=0,
        )
        if response.metadata.get("operation") != "source_probe":
            raise ValueError("worker response is not a source probe")
        return response.arrays

    return probe


def _source_reviewer(
    candidates_by_identity: Mapping[tuple[str, str, str, str], Mapping[str, Any]],
    source_loader: Callable[[Mapping[str, Any]], Mapping[str, Any]],
):
    def review(row: Mapping[str, Any], candidates: np.ndarray | None) -> Mapping[str, Any]:
        identity = _identity(row)
        if identity not in candidates_by_identity:
            raise ValueError("census identity missing from independent enumeration")
        try:
            source = dict(source_loader(candidates_by_identity[identity]))
            causal_input = source.pop("causal_input")
            if candidates is None:
                raise ValueError("candidate tensor missing for source-constructible row")
            projection = project_candidates_to_route(
                candidates,
                causal_input["route_lanes"],
                causal_input["route_lanes_speed_limit"],
                causal_input["route_lanes_has_speed_limit"],
                speed_source_policy=CANDIDATE_LOCAL_EXACT_SPEED,
            )
            return {
                **source,
                "route_speed_source_eligible_mask": projection[
                    "route_speed_source_eligible_mask"
                ],
            }
        except Exception as error:
            return {
                "failure_class": type(error).__name__,
                "failure_reason": str(error).replace("\n", " "),
            }

    return review


def _identity(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row["bucket"]),
        str(row["log_token"]),
        str(row["scene_token"]),
        str(row["scenario_token"]),
    )


def _seal(root: Path) -> str:
    names = sorted(
        path.name
        for path in root.iterdir()
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256"}
    )
    manifest = "".join(f"{_file_sha256(root / name)}  {name}\n" for name in names)
    manifest_bytes = manifest.encode("utf-8")
    (root / "SHA256SUMS").write_bytes(manifest_bytes)
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    (root / "ROOT_SHA256").write_text(digest + "\n", encoding="utf-8")
    return digest


def _verify_seal(root: Path, expected: str | None = None) -> str:
    manifest = (root / "SHA256SUMS").read_bytes()
    digest = hashlib.sha256(manifest).hexdigest()
    recorded = (root / "ROOT_SHA256").read_text(encoding="utf-8").strip()
    if digest != recorded or (expected is not None and digest != expected):
        raise ValueError("artifact root SHA256 mismatch")
    for line in manifest.decode("utf-8").splitlines():
        item_sha, name = line.split("  ", 1)
        if _file_sha256(root / name) != item_sha:
            raise ValueError(f"artifact file SHA256 mismatch: {name}")
    return digest


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(_jsonable(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(_jsonable(row), sort_keys=True, allow_nan=False) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    return value


def _json_value(value: str) -> Any:
    path = Path(value)
    return json.loads(path.read_text(encoding="utf-8") if path.is_file() else value)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("census", "review"), required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--map-root", type=Path, required=True)
    parser.add_argument("--v18-manifest", type=Path, required=True)
    parser.add_argument("--v18-manifest-sha256", required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--source-root-sha256")
    parser.add_argument("--worker-command-json")
    parser.add_argument("--camp-head")
    parser.add_argument("--dp-head")
    parser.add_argument("--nuplan-head")
    parser.add_argument("--selector-hashes-json")
    parser.add_argument("--base-smoke-config", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.output_root.exists() or args.staging_root.exists():
        raise FileExistsError("staging or output root already exists")
    logs, scenes = load_exclusions(
        args.v18_manifest, args.v18_manifest_sha256
    )
    enumerated = enumerate_candidate_rows(
        args.data_root,
        excluded_logs=logs,
        excluded_scenes=scenes,
    )
    loader = _source_loader(args.data_root, args.map_root)
    if args.mode == "census":
        required = (
            args.worker_command_json,
            args.camp_head,
            args.dp_head,
            args.nuplan_head,
            args.selector_hashes_json,
        )
        if any(value is None for value in required):
            raise ValueError("census worker/head/hash inputs are required")
        selector_hashes = tuple(_json_value(args.selector_hashes_json))
        if len(selector_hashes) != 3:
            raise ValueError("selector hashes must contain three SHA256 values")
        probe_root = args.staging_root.parent / (args.staging_root.name + ".probe")
        probe = _source_probe(
            probe_root=probe_root,
            worker_command=tuple(_json_value(args.worker_command_json)),
            camp_head=str(args.camp_head),
            dp_head=str(args.dp_head),
            nuplan_head=str(args.nuplan_head),
            selector_hashes=selector_hashes,  # type: ignore[arg-type]
        )
        base = (
            None
            if args.base_smoke_config is None
            else json.loads(args.base_smoke_config.read_text(encoding="utf-8"))
        )
        write_census_artifact(
            rows=enumerated,
            output_root=args.staging_root,
            source_loader=loader,
            source_probe=probe,
            base_smoke_config=base,
        )
        for name in ("request.npz", "request.json", "response.npz", "response.json"):
            path = probe_root / name
            if path.exists():
                path.unlink()
        probe_root.rmdir()
    else:
        if args.source_root is None or args.source_root_sha256 is None:
            raise ValueError("review source root and SHA256 are required")
        _verify_seal(args.source_root, args.source_root_sha256)
        index = {_identity(row): row for row in enumerated}
        write_review_artifact(
            source_root=args.source_root,
            output_root=args.staging_root,
            source_reviewer=_source_reviewer(index, loader),
        )
    args.staging_root.replace(args.output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
