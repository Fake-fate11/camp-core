#!/usr/bin/env python3
"""Build the outcome-blind V26 three-city full-population sampling manifest.

This is a source-metadata pass only.  It never constructs a DP input, pool,
candidate, trajectory, label, endpoint, or selector result.  It first assigns
every ScenarioBuilder-context-eligible scene to a leakage-safe partition, then
selects deterministic time baselines and source-side event windows inside that
partition.  ``max_states_per_scene`` is deliberately absent: two baseline
anchors per scene are one sampling rule, not a final population cap.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_v26_nuplan import (  # noqa: E402
    FIXED_DP_HEAD,
    _academic_connected_components,
    _allocate_academic_group_partitions,
    _validate_fixed_dp_binding,
    canonical_json_bytes,
    canonical_json_sha256,
)


SCHEMA_VERSION = "camp_dp_v26_nuplan_full_population_sampling_manifest_v1"
EVIDENCE_ROLE = "development_nonholdout_nuplan_full_population_sampling"
CITY_ORDER = ("boston", "pittsburgh", "singapore")
CITY_SPEC = {
    "boston": ("us-ma-boston", "iid_grouped_source"),
    "pittsburgh": ("us-pa-pittsburgh-hazelwood", "iid_grouped_source"),
    "singapore": ("sg-one-north", "city_held_out_ood"),
}
GROUP_FIELDS = (
    "log_token",
    "scenario_scene_token",
    "mission_route_roadblock_chain_sha256",
    "corridor_id",
    "geometry_clone_group_sha256",
)
KINEMATIC_POLICY = {
    "speed_stationary_mps_lte": 0.1,
    "longitudinal_acceleration_event_mps2_abs_gte": 0.5,
    "yaw_rate_turning_radps_abs_gte": 0.1,
    "event_rule": "retain the first anchor entering each source-side kinematic regime",
}
B8_CANDIDATE_SHAPE = (8, 80, 4)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, label: str) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json_bytes(value))
    temporary.replace(path)


def _hex_token(value: Any) -> str:
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, str):
        return value.lower()
    raise ValueError("nuPlan token is not bytes or text")


def _city_config(value: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    archives = value.get("city_archives")
    if not isinstance(archives, list):
        raise ValueError("three-city source config is missing city_archives")
    result: dict[str, dict[str, str]] = {}
    for item in archives:
        if not isinstance(item, Mapping):
            raise ValueError("three-city source config archive entry is invalid")
        city = str(item.get("city", ""))
        map_family = str(item.get("map_family", ""))
        role = str(item.get("academic_role", ""))
        if city not in CITY_SPEC or CITY_SPEC[city] != (map_family, role):
            raise ValueError("three-city source config city identity drifted")
        if city in result:
            raise ValueError("three-city source config has duplicate city")
        result[city] = {"map_family": map_family, "academic_role": role}
    if tuple(sorted(result)) != tuple(sorted(CITY_ORDER)):
        raise ValueError("three-city source config city set drifted")
    return result


def _completed_city_receipts(source_manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if source_manifest.get("terminal_status") != "complete":
        raise ValueError("three-city raw source manifest is not terminal complete")
    completed = source_manifest.get("completed_cities")
    if not isinstance(completed, list):
        raise ValueError("three-city raw source manifest lacks completed cities")
    result: dict[str, dict[str, Any]] = {}
    for item in completed:
        if not isinstance(item, Mapping):
            raise ValueError("three-city completed city receipt entry is invalid")
        city = str(item.get("city", ""))
        receipt_path = Path(str(item.get("receipt_path", "")))
        expected_sha = str(item.get("receipt_sha256", ""))
        if city not in CITY_SPEC or not receipt_path.is_file() or len(expected_sha) != 64:
            raise ValueError("three-city completed city receipt binding is invalid")
        receipt = _read_json(receipt_path, f"{city} city receipt")
        archive = receipt.get("archive_verification")
        if (
            receipt.get("terminal_status") != "complete"
            or receipt.get("city") != city
            or receipt.get("receipt_sha256") != expected_sha
            or not isinstance(archive, Mapping)
            or not isinstance(archive.get("archive_sha256"), str)
        ):
            raise ValueError("three-city completed city receipt identity drifted")
        result[city] = {
            "receipt_sha256": expected_sha,
            "archive_sha256": str(archive["archive_sha256"]),
            "archive_bytes": int(archive.get("archive_bytes", 0)),
        }
    if tuple(sorted(result)) != tuple(sorted(CITY_ORDER)):
        raise ValueError("three-city completed receipt set drifted")
    return result


def _maps_catalog(maps_root: Path, maps_archive_integrity: Path) -> dict[str, Any]:
    root = maps_root.resolve(strict=True)
    manifest_path = root / "nuplan-maps-v1.0.json"
    manifest = _read_json(manifest_path, "nuPlan maps manifest")
    integrity = _read_json(maps_archive_integrity, "nuPlan maps archive integrity")
    maps_receipt = integrity.get("maps", {}) if isinstance(integrity, Mapping) else {}
    archive = maps_receipt.get("archive", {}) if isinstance(maps_receipt, Mapping) else {}
    archive_sha = maps_receipt.get("sha256") or (
        archive.get("sha256") if isinstance(archive, Mapping) else None
    )
    if not isinstance(archive_sha, str) or len(archive_sha) != 64:
        raise ValueError("nuPlan maps archive integrity hash is missing")
    paths_by_location: dict[str, Path] = {}
    if not isinstance(manifest, Mapping):
        raise ValueError("nuPlan maps manifest is invalid")
    for location, item in manifest.items():
        if not isinstance(location, str) or not isinstance(item, Mapping):
            continue
        version = item.get("version")
        if not isinstance(version, str) or not version:
            continue
        map_path = root / location / version / "map.gpkg"
        if map_path.is_file():
            if location in paths_by_location:
                raise ValueError("nuPlan maps manifest has multiple revisions per location")
            paths_by_location[location] = map_path
    return {
        "root": root,
        "archive_sha256": archive_sha,
        "manifest_sha256": _sha256_file(manifest_path),
        "paths_by_location": paths_by_location,
    }


def _finite_float(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _kinematic_regimes(anchor: Mapping[str, Any]) -> set[str]:
    vx = _finite_float(anchor["vx"])
    vy = _finite_float(anchor["vy"])
    ax = _finite_float(anchor["acceleration_x"])
    ay = _finite_float(anchor["acceleration_y"])
    yaw_rate = _finite_float(anchor["angular_rate_z"])
    if None in (vx, vy, ax, ay, yaw_rate):
        return set()
    speed = math.hypot(vx, vy)
    labels = {
        "kinematic:stationary"
        if speed <= KINEMATIC_POLICY["speed_stationary_mps_lte"]
        else "kinematic:moving"
    }
    if speed > KINEMATIC_POLICY["speed_stationary_mps_lte"]:
        longitudinal_acceleration = (vx * ax + vy * ay) / speed
        threshold = KINEMATIC_POLICY["longitudinal_acceleration_event_mps2_abs_gte"]
        if longitudinal_acceleration >= threshold:
            labels.add("kinematic:accelerating")
        elif longitudinal_acceleration <= -threshold:
            labels.add("kinematic:braking")
    if abs(yaw_rate) >= KINEMATIC_POLICY["yaw_rate_turning_radps_abs_gte"]:
        labels.add("kinematic:turning")
    return labels


def _add_membership(
    selected: dict[str, dict[str, Any]],
    anchor: Mapping[str, Any],
    *,
    population_id: str,
    stratum: str,
    phase: str,
) -> None:
    state_token = str(anchor["state_token"])
    item = selected.setdefault(
        state_token,
        {
            "anchor_id": f"{population_id}:{state_token}",
            "population_id": population_id,
            "state_token": state_token,
            "timestamp": int(anchor["timestamp"]),
            "event_memberships": set(),
            "membership_requests": 0,
        },
    )
    item["membership_requests"] += 1
    item["event_memberships"].add((stratum, phase))


def _add_event_window(
    selected: dict[str, dict[str, Any]],
    anchors: Sequence[Mapping[str, Any]],
    index: int,
    *,
    population_id: str,
    stratum: str,
) -> None:
    for offset, phase in ((-1, "pre"), (0, "core"), (1, "post")):
        target = index + offset
        if 0 <= target < len(anchors):
            _add_membership(
                selected,
                anchors[target],
                population_id=population_id,
                stratum=stratum,
                phase=phase,
            )


def _source_db_identity(
    *, city: str, receipt: Mapping[str, Any], relative_path: str, byte_count: int
) -> str:
    return canonical_json_sha256(
        {
            "kind": "verified_archive_member_identity_v1",
            "city": city,
            "city_archive_sha256": receipt["archive_sha256"],
            "city_receipt_sha256": receipt["receipt_sha256"],
            "relative_path": relative_path,
            "bytes": byte_count,
        }
    )


def _map_identity(maps: Mapping[str, Any], map_path: Path, location: str) -> str:
    return canonical_json_sha256(
        {
            "kind": "verified_maps_archive_member_identity_v1",
            "maps_archive_sha256": maps["archive_sha256"],
            "maps_manifest_sha256": maps["manifest_sha256"],
            "location": location,
            "relative_path": str(map_path.relative_to(maps["root"])),
            "bytes": map_path.stat().st_size,
        }
    )


def _database_scene_population(
    *,
    database_path: Path,
    city: str,
    city_config: Mapping[str, str],
    city_receipt: Mapping[str, Any],
    db_relative_path: str,
    maps: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Read identity/current-state metadata for one DB without outcomes."""

    uri = f"file:{database_path.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        connection.execute("PRAGMA query_only = ON")
        logs = connection.execute(
            "SELECT token, location, map_version FROM log ORDER BY token"
        ).fetchall()
        if len(logs) != 1:
            raise ValueError("nuPlan DB must bind exactly one log")
        log_token, location, map_version = logs[0]
        if not isinstance(location, str) or not isinstance(map_version, str):
            raise ValueError("nuPlan DB log location/map version is invalid")
        if location != city_config["map_family"]:
            raise ValueError("city map-family identity drifted")
        map_path = maps["paths_by_location"].get(location)
        if map_path is None:
            raise ValueError("verified map asset is unavailable")

        scenes = connection.execute(
            """
            SELECT scene.token, scene.name, scene.roadblock_ids, goal.token
            FROM scene
            LEFT JOIN ego_pose AS goal ON goal.token = scene.goal_ego_pose_token
            ORDER BY scene.name ASC, scene.token ASC
            """
        ).fetchall()
        tag_rows = connection.execute(
            "SELECT lidar_pc_token, type FROM scenario_tag ORDER BY lidar_pc_token, token"
        ).fetchall()
        signal_rows = connection.execute(
            "SELECT lidar_pc_token, status FROM traffic_light_status ORDER BY lidar_pc_token, token"
        ).fetchall()

        tags_by_state: dict[str, set[str]] = defaultdict(set)
        for state_token, event_type in tag_rows:
            tags_by_state[_hex_token(state_token)].add(
                f"scenario_tag:{str(event_type or 'unlabeled')}"
            )
        signals_by_state: dict[str, set[str]] = defaultdict(set)
        for state_token, status in signal_rows:
            signals_by_state[_hex_token(state_token)].add(
                f"signal:{str(status or 'unknown').lower()}"
            )

        source_db_sha = _source_db_identity(
            city=city,
            receipt=city_receipt,
            relative_path=db_relative_path,
            byte_count=database_path.stat().st_size,
        )
        map_sha = _map_identity(maps, map_path, location)
        log_token_hex = _hex_token(log_token)
        groups: list[dict[str, Any]] = []
        selected_anchors: list[dict[str, Any]] = []
        counters = Counter(
            scene_total=len(scenes),
            scene_context_eligible=0,
            scene_with_eligible_anchor=0,
            eligible_anchor_population=0,
            anchor_membership_requests=0,
        )

        for position, (scene_token, scene_name, roadblocks, goal_token) in enumerate(
            scenes, start=1
        ):
            route = str(roadblocks or "")
            context_eligible = (
                position >= 3
                and position < len(scenes) - 1
                and goal_token is not None
                and bool(route)
            )
            if not context_eligible:
                continue
            counters["scene_context_eligible"] += 1
            anchor_rows = connection.execute(
                """
                SELECT lidar_pc.token, lidar_pc.timestamp,
                       ego_pose.vx, ego_pose.vy,
                       ego_pose.acceleration_x, ego_pose.acceleration_y,
                       ego_pose.angular_rate_z
                FROM lidar_pc
                INNER JOIN lidar ON lidar.token = lidar_pc.lidar_token
                INNER JOIN log ON log.token = lidar.log_token
                LEFT JOIN ego_pose ON ego_pose.token = lidar_pc.ego_pose_token
                WHERE lidar_pc.scene_token = ?
                ORDER BY lidar_pc.timestamp ASC, lidar_pc.token ASC
                """,
                (scene_token,),
            ).fetchall()
            if not anchor_rows:
                continue
            anchors = [
                {
                    "state_token": _hex_token(token),
                    "timestamp": int(timestamp),
                    "vx": vx,
                    "vy": vy,
                    "acceleration_x": acceleration_x,
                    "acceleration_y": acceleration_y,
                    "angular_rate_z": angular_rate_z,
                }
                for token, timestamp, vx, vy, acceleration_x, acceleration_y, angular_rate_z in anchor_rows
            ]
            scene_token_hex = _hex_token(scene_token)
            route_sha = hashlib.sha256(route.encode("utf-8")).hexdigest()
            population_id = f"{city}:{db_relative_path}:{scene_token_hex}"
            group = {
                "population_id": population_id,
                "official_split": "train",
                "city": city,
                "map_family": city_config["map_family"],
                "log_token": log_token_hex,
                "scenario_scene_token": scene_token_hex,
                "scene_token": scene_token_hex,
                "mission_route_roadblock_chain_sha256": route_sha,
                "corridor_id": f"{location}:{route_sha[:20]}",
                "geometry_clone_group_sha256": canonical_json_sha256(
                    {
                        "location": location,
                        "map_version": map_version,
                        "roadblock_chain": route,
                    }
                ),
                "source_db_sha256": source_db_sha,
                "map_sha256": map_sha,
                "raw_db_relative_path": db_relative_path,
                "scene_name": str(scene_name or ""),
                "eligible_anchor_count": len(anchors),
            }
            group["population_identity_sha256"] = canonical_json_sha256(
                {
                    key: group[key]
                    for key in (
                        "population_id",
                        "log_token",
                        "scenario_scene_token",
                        "mission_route_roadblock_chain_sha256",
                        "corridor_id",
                        "geometry_clone_group_sha256",
                        "source_db_sha256",
                        "map_sha256",
                    )
                }
            )
            groups.append(group)
            counters["scene_with_eligible_anchor"] += 1
            counters["eligible_anchor_population"] += len(anchors)

            selected: dict[str, dict[str, Any]] = {}
            _add_membership(
                selected,
                anchors[0],
                population_id=population_id,
                stratum="baseline:deterministic_time",
                phase="time_start",
            )
            _add_membership(
                selected,
                anchors[-1],
                population_id=population_id,
                stratum="baseline:deterministic_time",
                phase="time_end",
            )
            for anchor in (anchors[0], anchors[-1]):
                _add_membership(
                    selected,
                    anchor,
                    population_id=population_id,
                    stratum="route:roadblock_chain_present",
                    phase="context",
                )

            prior_kinematic: set[str] = set()
            for index, anchor in enumerate(anchors):
                state_token_hex = str(anchor["state_token"])
                for stratum in sorted(tags_by_state.get(state_token_hex, ())):
                    _add_event_window(
                        selected,
                        anchors,
                        index,
                        population_id=population_id,
                        stratum=stratum,
                    )
                for stratum in sorted(signals_by_state.get(state_token_hex, ())):
                    _add_event_window(
                        selected,
                        anchors,
                        index,
                        population_id=population_id,
                        stratum=stratum,
                    )
                current_kinematic = _kinematic_regimes(anchor)
                for stratum in sorted(current_kinematic - prior_kinematic):
                    _add_event_window(
                        selected,
                        anchors,
                        index,
                        population_id=population_id,
                        stratum=stratum,
                    )
                prior_kinematic = current_kinematic

            for item in selected.values():
                item["event_memberships"] = [
                    {"stratum": stratum, "phase": phase}
                    for stratum, phase in sorted(item["event_memberships"])
                ]
                counters["anchor_membership_requests"] += int(item["membership_requests"])
                selected_anchors.append(item)
    return groups, selected_anchors, dict(counters)


def _group_assignments(groups: Sequence[Mapping[str, Any]], allocation_seed: int, fraction: float) -> dict[str, str]:
    if not groups:
        raise ValueError("full eligible population is empty")
    working = []
    for group in groups:
        working.append(
            {
                "record_id": group["population_id"],
                "source_identity_sha256": group["population_identity_sha256"],
                "city": group["city"],
                "log_token": group["log_token"],
                "scenario_token": group["scenario_scene_token"],
                "scene_token": group["scene_token"],
                "mission_route_roadblock_chain_sha256": group[
                    "mission_route_roadblock_chain_sha256"
                ],
                "corridor_id": group["corridor_id"],
                "geometry_clone_group_sha256": group["geometry_clone_group_sha256"],
            }
        )
    components = _academic_connected_components(working)
    by_index = _allocate_academic_group_partitions(
        working,
        components,
        allocation_seed=allocation_seed,
        iid_validation_fraction=fraction,
    )
    return {str(groups[index]["population_id"]): partition for index, partition in by_index.items()}


def _zero_overlap(groups: Sequence[Mapping[str, Any]], assignments: Mapping[str, str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for field in GROUP_FIELDS:
        memberships: dict[str, set[str]] = defaultdict(set)
        for group in groups:
            memberships[str(group[field])].add(assignments[str(group["population_id"])])
        result[field] = sum(1 for parts in memberships.values() if len(parts) > 1)
    if any(result.values()):
        raise ValueError(f"full population grouped split has overlap: {result}")
    return result


def _coverage_rows(
    groups: Sequence[Mapping[str, Any]],
    selected: Sequence[Mapping[str, Any]],
    assignments: Mapping[str, str],
) -> list[dict[str, Any]]:
    group_by_id = {str(group["population_id"]): group for group in groups}
    selected_groups = {str(item["population_id"]) for item in selected}
    counts: dict[tuple[str, str], dict[str, Any]] = {}
    for group in groups:
        partition = assignments[str(group["population_id"])]
        key = (str(group["city"]), partition)
        row = counts.setdefault(
            key,
            {
                "city": key[0],
                "partition": key[1],
                "population_scene_count": 0,
                "population_anchor_count": 0,
                "population_log_tokens": set(),
                "population_corridors": set(),
                "population_geometry_groups": set(),
                "sampled_scene_count": 0,
                "sampled_log_tokens": set(),
                "sampled_corridors": set(),
                "sampled_geometry_groups": set(),
            },
        )
        row["population_scene_count"] += 1
        row["population_anchor_count"] += int(group["eligible_anchor_count"])
        row["population_log_tokens"].add(str(group["log_token"]))
        row["population_corridors"].add(str(group["corridor_id"]))
        row["population_geometry_groups"].add(str(group["geometry_clone_group_sha256"]))
        if str(group["population_id"]) in selected_groups:
            row["sampled_scene_count"] += 1
            row["sampled_log_tokens"].add(str(group["log_token"]))
            row["sampled_corridors"].add(str(group["corridor_id"]))
            row["sampled_geometry_groups"].add(str(group["geometry_clone_group_sha256"]))
    result = []
    for row in counts.values():
        result.append(
            {
                "city": row["city"],
                "partition": row["partition"],
                "population_scene_count": row["population_scene_count"],
                "population_anchor_count": row["population_anchor_count"],
                "population_log_count": len(row["population_log_tokens"]),
                "population_corridor_count": len(row["population_corridors"]),
                "population_geometry_clone_count": len(row["population_geometry_groups"]),
                "sampled_scene_count": row["sampled_scene_count"],
                "sampled_log_count": len(row["sampled_log_tokens"]),
                "sampled_corridor_count": len(row["sampled_corridors"]),
                "sampled_geometry_clone_count": len(row["sampled_geometry_groups"]),
            }
        )
    return sorted(result, key=lambda row: (row["city"], row["partition"]))


def _stratum_rows(
    selected: Sequence[Mapping[str, Any]],
    groups: Mapping[str, Mapping[str, Any]],
    assignments: Mapping[str, str],
) -> list[dict[str, Any]]:
    members: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for item in selected:
        group = groups[str(item["population_id"])]
        partition = assignments[str(item["population_id"])]
        for membership in item["event_memberships"]:
            key = (
                str(group["city"]),
                partition,
                str(membership["stratum"]),
                str(membership["phase"]),
            )
            members[key].add(str(item["anchor_id"]))
    return [
        {
            "city": city,
            "partition": partition,
            "tag": stratum,
            "phase": phase,
            "population_count": len(anchor_ids),
            "sample_count": len(anchor_ids),
            "sampling_probability": 1.0,
            "sampling_policy": "all source event memberships retained; no common-event thinning applied",
        }
        for (city, partition, stratum, phase), anchor_ids in sorted(members.items())
    ]


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    raw_root = args.raw_root.resolve(strict=True)
    source_manifest_path = args.source_manifest.resolve(strict=True)
    source_manifest = _read_json(source_manifest_path, "three-city raw source manifest")
    city_receipts = _completed_city_receipts(source_manifest)
    city_config = _city_config(_read_json(args.source_config, "three-city source config"))
    maps = _maps_catalog(args.maps_root, args.maps_archive_integrity)
    fixed_dp = _validate_fixed_dp_binding(_read_json(args.fixed_dp_binding, "fixed-DP binding"))
    if fixed_dp["head"] != FIXED_DP_HEAD:
        raise ValueError("fixed DP head drifted")
    if not isinstance(args.allocation_seed, int) or isinstance(args.allocation_seed, bool):
        raise ValueError("allocation seed must be an integer")
    if not 0.0 < args.iid_validation_fraction < 0.5:
        raise ValueError("iid validation fraction must be in (0, 0.5)")
    if len(args.camp_source_head) != 40:
        raise ValueError("CAMP source head must be a full commit")

    groups: list[dict[str, Any]] = []
    selected: list[dict[str, Any]] = []
    db_denominator = Counter(planned=0, complete=0, typed_failure=0, unattempted=0)
    scene_counters = Counter()
    data_members: list[dict[str, Any]] = []
    for city in CITY_ORDER:
        db_root = raw_root / "raw_cities" / city / "data" / "cache" / f"train_{city}"
        db_paths = sorted(path for path in db_root.glob("*.db") if path.is_file())
        if not db_paths:
            raise FileNotFoundError(f"verified {city} DB directory is missing or empty")
        for database_path in db_paths:
            db_denominator["planned"] += 1
            relative_path = str(database_path.relative_to(raw_root))
            try:
                db_groups, db_selected, db_counts = _database_scene_population(
                    database_path=database_path,
                    city=city,
                    city_config=city_config[city],
                    city_receipt=city_receipts[city],
                    db_relative_path=relative_path,
                    maps=maps,
                )
            except Exception as error:
                db_denominator["typed_failure"] += 1
                raise RuntimeError(f"{city} source DB failed: {relative_path}: {type(error).__name__}") from error
            db_denominator["complete"] += 1
            groups.extend(db_groups)
            selected.extend(db_selected)
            scene_counters.update(db_counts)
            data_members.append(
                {
                    "city": city,
                    "relative_path": relative_path,
                    "bytes": database_path.stat().st_size,
                    "archive_sha256": city_receipts[city]["archive_sha256"],
                }
            )

    groups.sort(key=lambda group: str(group["population_id"]))
    if len({str(group["population_id"]) for group in groups}) != len(groups):
        raise ValueError("full population has duplicate scene identity")
    if len({str(group["population_identity_sha256"]) for group in groups}) != len(groups):
        raise ValueError("full population has duplicate scene identity hash")
    selected.sort(key=lambda item: str(item["anchor_id"]))
    if len({str(item["anchor_id"]) for item in selected}) != len(selected):
        raise ValueError("same lidar_pc was not merged before source record materialization")
    population_ids = {str(group["population_id"]) for group in groups}
    if any(str(item["population_id"]) not in population_ids for item in selected):
        raise ValueError("selected anchor is not bound to the full eligible population")

    assignments = _group_assignments(groups, args.allocation_seed, args.iid_validation_fraction)
    overlap = _zero_overlap(groups, assignments)
    groups_by_id = {str(group["population_id"]): group for group in groups}
    for item in selected:
        item["partition"] = assignments[str(item["population_id"])]
    selected.sort(key=lambda item: str(item["anchor_id"]))
    coverage = _coverage_rows(groups, selected, assignments)
    strata = _stratum_rows(selected, groups_by_id, assignments)
    selected_by_partition = Counter(item["partition"] for item in selected)
    group_by_partition = Counter(assignments[str(group["population_id"])] for group in groups)
    anchors_by_partition = Counter()
    for group in groups:
        anchors_by_partition[assignments[str(group["population_id"])]] += int(
            group["eligible_anchor_count"]
        )
    membership_requests = sum(int(item["membership_requests"]) for item in selected)
    raw_acquisition_sha = str(source_manifest.get("source_manifest_sha256", ""))
    if len(raw_acquisition_sha) != 64:
        raise ValueError("three-city raw source manifest hash is missing")
    raw_source = {
        "nuplan_dataset_version": "v1.1",
        "official_split_entrypoint": "official_nuplan_v11_train_city_archives_custom_academic_group_split",
        "official_split_metadata_sha256": raw_acquisition_sha,
        "data_root_identity_sha256": canonical_json_sha256(data_members),
        "maps_root_identity_sha256": canonical_json_sha256(
            {
                "maps_archive_sha256": maps["archive_sha256"],
                "maps_manifest_sha256": maps["manifest_sha256"],
                "locations": sorted(maps["paths_by_location"]),
            }
        ),
    }
    pool_count = len(selected)
    candidate_tensor_bytes = pool_count * math.prod(B8_CANDIDATE_SHAPE) * 4
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "evidence_role": EVIDENCE_ROLE,
        "outcome_fields_consumed": [],
        "raw_acquisition_manifest_sha256": raw_acquisition_sha,
        "input_bindings": {
            "source_manifest_sha256": _sha256_file(source_manifest_path),
            "fixed_dp_binding_sha256": _sha256_file(args.fixed_dp_binding),
            "maps_archive_integrity_sha256": _sha256_file(args.maps_archive_integrity),
        },
        "raw_source": raw_source,
        "fixed_dp": fixed_dp,
        "camp_source_head": args.camp_source_head,
        "sampling_contract": {
            "status": "identity_only_pre_pool_not_arbitrary_cap",
            "group_split_order": "full eligible population before within-partition sampling",
            "group_keys": list(GROUP_FIELDS),
            "iid_source_cities": ["boston", "pittsburgh"],
            "city_held_out_ood": "singapore",
            "allocation_seed": args.allocation_seed,
            "iid_validation_fraction": args.iid_validation_fraction,
            "baseline": "two deterministic temporal anchors per eligible scene: earliest and latest lidar_pc",
            "event_windows": "official scenario_tag, source traffic signal status, and source kinematic-regime onsets; retain available pre/core/post anchors",
            "route_context": "roadblock-chain context is attached to both temporal baselines",
            "deduplication_key": ["population_id", "lidar_pc_token"],
            "event_policy": "all event memberships retained; no rare/common thinning applied",
            "kinematic_policy": KINEMATIC_POLICY,
            "forbidden_selection_inputs": [
                "candidate",
                "trajectory",
                "label",
                "outcome",
                "endpoint",
                "SafetyCost",
                "selector_result",
            ],
        },
        "denominator": {
            "db": dict(db_denominator),
            "scene": {
                "total": int(scene_counters["scene_total"]),
                "context_eligible": int(scene_counters["scene_context_eligible"]),
                "eligible_with_anchor": int(scene_counters["scene_with_eligible_anchor"]),
            },
            "anchor": {
                "eligible_population": int(scene_counters["eligible_anchor_population"]),
                "selected_unique": pool_count,
                "membership_requests": membership_requests,
                "merged_duplicate_requests": membership_requests - pool_count,
                "merged_duplicate_request_rate": 0.0
                if membership_requests == 0
                else (membership_requests - pool_count) / membership_requests,
            },
        },
        "zero_overlap": overlap,
        "partition_population": [
            {
                "partition": partition,
                "population_group_count": group_by_partition[partition],
                "eligible_anchor_count": anchors_by_partition[partition],
                "selected_anchor_count": selected_by_partition[partition],
                "selected_over_eligible_anchor_ratio": 0.0
                if anchors_by_partition[partition] == 0
                else selected_by_partition[partition] / anchors_by_partition[partition],
            }
            for partition in ("train_iid", "val_iid", "test_ood")
        ],
        "coverage": coverage,
        "city_partition_tag_phase": strata,
        "capacity_estimate": {
            "projected_pool_count": pool_count,
            "same_ego_b8_candidate_rows": pool_count * B8_CANDIDATE_SHAPE[0],
            "candidate_tensor_shape_per_pool": list(B8_CANDIDATE_SHAPE),
            "candidate_tensor_bytes_lower_bound": candidate_tensor_bytes,
            "gpu_runtime": "not_estimated_before_representative_b8_smoke",
            "disk_execution_receipt": "not_estimated_before_materialized_pool schema is fixed",
        },
        "population_groups": groups,
        "selected_anchors": selected,
    }
    manifest["sampling_manifest_sha256"] = canonical_json_sha256(manifest)
    return manifest


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--maps-root", type=Path, required=True)
    parser.add_argument("--maps-archive-integrity", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--source-config", type=Path, required=True)
    parser.add_argument("--fixed-dp-binding", type=Path, required=True)
    parser.add_argument("--camp-source-head", required=True)
    parser.add_argument("--allocation-seed", type=int, default=3407)
    parser.add_argument("--iid-validation-fraction", type=float, default=0.2)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build_manifest(args)
    _write_json_atomic(args.output, manifest)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sampling_manifest_sha256": manifest["sampling_manifest_sha256"],
                "eligible_anchor_population": manifest["denominator"]["anchor"][
                    "eligible_population"
                ],
                "selected_unique": manifest["denominator"]["anchor"]["selected_unique"],
                "zero_overlap": manifest["zero_overlap"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
