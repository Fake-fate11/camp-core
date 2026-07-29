#!/usr/bin/env python3
"""Build a V26 identity-only inventory from verified three-city nuPlan DBs.

This source pass reads only SQLite identity/route/tag metadata.  It never
opens candidates, expert futures, labels, trajectories, or endpoint values.
The output is deliberately bounded: a deterministic identity-only prefix of
officially ScenarioBuilder-eligible tagged states per scene, plus capacity
counts for the complete tagged-state source universe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_v26_nuplan import (  # noqa: E402
    canonical_json_bytes,
    canonical_json_sha256,
    validate_v26_nuplan_source_record,
)


SCHEMA_VERSION = "camp_dp_v26_nuplan_three_city_identity_inventory_v1"
EVIDENCE_ROLE = "development_nonholdout_nuplan_identity_inventory"
CITY_ORDER = ("boston", "pittsburgh", "singapore")


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
    by_city: dict[str, dict[str, str]] = {}
    for item in archives:
        if not isinstance(item, Mapping):
            raise ValueError("three-city source config archive entry is invalid")
        city = str(item.get("city", ""))
        map_family = str(item.get("map_family", ""))
        role = str(item.get("academic_role", ""))
        if city not in CITY_ORDER or not map_family or not role:
            raise ValueError("three-city source config city identity drifted")
        if city in by_city:
            raise ValueError("three-city source config has duplicate city")
        by_city[city] = {"map_family": map_family, "academic_role": role}
    if tuple(sorted(by_city)) != tuple(sorted(CITY_ORDER)):
        raise ValueError("three-city source config city set drifted")
    return by_city


def _completed_city_receipts(
    source_manifest: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    if source_manifest.get("terminal_status") != "complete":
        raise ValueError("three-city raw source manifest is not terminal complete")
    completed = source_manifest.get("completed_cities")
    if not isinstance(completed, list):
        raise ValueError("three-city raw source manifest lacks completed cities")
    receipts: dict[str, dict[str, Any]] = {}
    for item in completed:
        if not isinstance(item, Mapping):
            raise ValueError("three-city completed city receipt entry is invalid")
        city = str(item.get("city", ""))
        path = Path(str(item.get("receipt_path", "")))
        expected_sha = str(item.get("receipt_sha256", ""))
        if city not in CITY_ORDER or not path.is_file() or len(expected_sha) != 64:
            raise ValueError("three-city completed city receipt binding is invalid")
        receipt = _read_json(path, f"{city} city receipt")
        if receipt.get("receipt_sha256") != expected_sha:
            raise ValueError("three-city completed city canonical receipt hash drifted")
        if receipt.get("terminal_status") != "complete" or receipt.get("city") != city:
            raise ValueError("three-city completed city receipt terminal identity drifted")
        archive = receipt.get("archive_verification")
        if not isinstance(archive, Mapping) or not isinstance(archive.get("archive_sha256"), str):
            raise ValueError("three-city completed city archive identity is missing")
        receipts[city] = {
            "receipt_path": str(path),
            "receipt_sha256": expected_sha,
            "archive_sha256": str(archive["archive_sha256"]),
            "archive_bytes": int(archive.get("archive_bytes", 0)),
        }
    if tuple(sorted(receipts)) != tuple(sorted(CITY_ORDER)):
        raise ValueError("three-city completed receipt set drifted")
    return receipts


def _maps_catalog(maps_root: Path, maps_archive_integrity: Path) -> dict[str, Any]:
    maps_root = maps_root.resolve(strict=True)
    manifest_path = maps_root / "nuplan-maps-v1.0.json"
    manifest = _read_json(manifest_path, "nuPlan maps manifest")
    if not isinstance(manifest, Mapping):
        raise ValueError("nuPlan maps manifest is invalid")
    integrity = _read_json(maps_archive_integrity, "nuPlan maps archive integrity")
    maps_receipt = integrity.get("maps", {}) if isinstance(integrity, Mapping) else {}
    archive = maps_receipt.get("archive", {}) if isinstance(maps_receipt, Mapping) else {}
    archive_sha = (
        maps_receipt.get("sha256")
        if isinstance(maps_receipt, Mapping)
        else None
    ) or (archive.get("sha256") if isinstance(archive, Mapping) else None)
    if not isinstance(archive_sha, str) or len(archive_sha) != 64:
        raise ValueError("nuPlan maps archive integrity hash is missing")
    paths: dict[tuple[str, str], Path] = {}
    for location, value in manifest.items():
        if not isinstance(location, str) or not isinstance(value, Mapping):
            continue
        version = value.get("version")
        if not isinstance(version, str) or not version:
            continue
        path = maps_root / location / version / "map.gpkg"
        if path.is_file():
            paths[(location, version)] = path
    return {
        "root": maps_root,
        "manifest_sha256": _sha256_file(manifest_path),
        "archive_sha256": archive_sha,
        "paths": paths,
    }


def _db_scene_rows(db_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    """Read only log/scene/scenario-tag identity metadata from one DB."""

    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as database:
        logs = database.execute(
            "SELECT token, location, map_version FROM log ORDER BY token"
        ).fetchall()
        if len(logs) != 1:
            raise ValueError("nuPlan DB must bind exactly one log")
        log_token, location, map_version = logs[0]
        if not isinstance(location, str) or not isinstance(map_version, str):
            raise ValueError("nuPlan DB log location/map version is invalid")
        scenes = database.execute(
            """
            SELECT scene.token, scene.name, scene.roadblock_ids, goal.token
            FROM scene
            LEFT JOIN ego_pose AS goal ON goal.token = scene.goal_ego_pose_token
            ORDER BY scene.name ASC, scene.token ASC
            """
        ).fetchall()
        tags = database.execute(
            """
            SELECT lidar_pc.scene_token, scenario_tag.token, scenario_tag.lidar_pc_token,
                   scenario_tag.type,
                   COUNT(traffic_light_status.token)
            FROM scenario_tag
            JOIN lidar_pc ON lidar_pc.token = scenario_tag.lidar_pc_token
            LEFT JOIN traffic_light_status
              ON traffic_light_status.lidar_pc_token = scenario_tag.lidar_pc_token
            GROUP BY scenario_tag.token, scenario_tag.lidar_pc_token, scenario_tag.type,
                     lidar_pc.scene_token
            ORDER BY scenario_tag.lidar_pc_token, scenario_tag.token
            """
        ).fetchall()
    by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for scene_token, scenario_token, state_token, scenario_type, signal_count in tags:
        by_scene[_hex_token(scene_token)].append(
            {
                "scenario_token": _hex_token(scenario_token),
                "state_token": _hex_token(state_token),
                "scenario_type": str(scenario_type or "unlabeled"),
                "traffic_light_status_count": int(signal_count),
            }
        )
    rows = []
    for position, (scene_token, name, roadblocks, goal_token) in enumerate(scenes, start=1):
        # This mirrors nuPlan's official ScenarioBuilder query: only a scene
        # with two predecessors and two successors can be materialized as a
        # planning scenario.  It is source context, not an outcome filter.
        scenario_builder_eligible = (
            position >= 3 and position < len(scenes) - 1 and goal_token is not None
        )
        rows.append(
            {
                "scene_token": _hex_token(scene_token),
                "scene_name": str(name or ""),
                "roadblock_ids": str(roadblocks or ""),
                "scenario_builder_eligible": scenario_builder_eligible,
                "mission_goal_available": goal_token is not None,
                "tagged_states": sorted(
                    by_scene.get(_hex_token(scene_token), []),
                    key=lambda row: (row["state_token"], row["scenario_token"]),
                ),
            }
        )
    return (
        {
            "log_token": _hex_token(log_token),
            "location": location,
            "map_version": map_version,
        },
        rows,
        len(tags),
    )


def _deterministic_stratified_states(
    tagged_states: Sequence[Mapping[str, Any]], max_states: int
) -> list[dict[str, Any]]:
    """Take a bounded, source-label-stratified state sample without outcomes."""

    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for state in tagged_states:
        by_type[str(state["scenario_type"])].append(dict(state))
    for rows in by_type.values():
        rows.sort(key=lambda row: (str(row["state_token"]), str(row["scenario_token"])))
    selected: list[dict[str, Any]] = []
    while len(selected) < max_states and any(by_type.values()):
        for scenario_type in sorted(by_type):
            if by_type[scenario_type] and len(selected) < max_states:
                selected.append(by_type[scenario_type].pop(0))
    return selected


def _records_for_scene(
    *,
    city: str,
    city_config: Mapping[str, str],
    city_receipt: Mapping[str, Any],
    db_path: Path,
    db_relative_path: str,
    log: Mapping[str, str],
    scene: Mapping[str, Any],
    maps: Mapping[str, Any],
    max_states_per_scene: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None]:
    if not bool(scene["scenario_builder_eligible"]):
        return [], [], {
            "reason": "official_scenario_builder_context_ineligible",
            "scene_token": scene["scene_token"],
        }
    tagged = list(scene["tagged_states"])
    if not tagged:
        return [], [], {"reason": "no_scenario_tag", "scene_token": scene["scene_token"]}
    roadblocks = str(scene["roadblock_ids"])
    if not roadblocks:
        return [], [], {"reason": "missing_roadblock_chain", "scene_token": scene["scene_token"]}
    map_path = maps["paths"].get((log["location"], log["map_version"]))
    if map_path is None:
        return [], [], {
            "reason": "missing_verified_map_asset",
            "scene_token": scene["scene_token"],
            "location": log["location"],
            "map_version": log["map_version"],
        }
    if log["location"] != city_config["map_family"]:
        return [], [], {
            "reason": "city_map_family_drift",
            "scene_token": scene["scene_token"],
            "location": log["location"],
        }
    route_sha = hashlib.sha256(roadblocks.encode("utf-8")).hexdigest()
    source_db_sha = canonical_json_sha256(
        {
            "kind": "verified_archive_member_identity_v1",
            "city_archive_sha256": city_receipt["archive_sha256"],
            "city_receipt_sha256": city_receipt["receipt_sha256"],
            "relative_path": db_relative_path,
            "bytes": db_path.stat().st_size,
        }
    )
    map_sha = canonical_json_sha256(
        {
            "kind": "verified_maps_archive_member_identity_v1",
            "maps_archive_sha256": maps["archive_sha256"],
            "maps_manifest_sha256": maps["manifest_sha256"],
            "location": log["location"],
            "map_version": log["map_version"],
            "relative_path": str(map_path.relative_to(maps["root"])),
            "bytes": map_path.stat().st_size,
        }
    )
    records: list[dict[str, Any]] = []
    metadata: list[dict[str, Any]] = []
    for state in _deterministic_stratified_states(tagged, max_states_per_scene):
        record = {
            "record_id": f"{city}:{db_relative_path}:{scene['scene_token']}:{state['state_token']}",
            "official_split": "train",
            "log_token": log["log_token"],
            "scenario_token": state["state_token"],
            "scene_token": scene["scene_token"],
            "state_token": state["state_token"],
            "mission_route_roadblock_chain_sha256": route_sha,
            "corridor_id": f"{log['location']}:{route_sha[:20]}",
            "geometry_clone_group_sha256": canonical_json_sha256(
                {
                    "location": log["location"],
                    "map_version": log["map_version"],
                    "roadblock_chain": roadblocks,
                }
            ),
            "city": city,
            "map_family": city_config["map_family"],
            "source_db_sha256": source_db_sha,
            "map_sha256": map_sha,
            "event_strata": [f"scenario_type:{state['scenario_type']}"],
        }
        validated = validate_v26_nuplan_source_record(record)
        records.append(validated)
        metadata.append(
            {
                "record_id": validated["record_id"],
                "source_db_relative_path": db_relative_path,
                "source_db_identity_kind": "verified_archive_member_identity_v1",
                "map_relative_path": str(map_path.relative_to(maps["root"])),
                "map_identity_kind": "verified_maps_archive_member_identity_v1",
                "scene_name": str(scene["scene_name"]),
                "traffic_light_status_count": int(state["traffic_light_status_count"]),
                "tagged_state_count_in_scene": len(tagged),
            }
        )
    return records, metadata, None


def build_inventory(args: argparse.Namespace) -> dict[str, Any]:
    raw_root = args.raw_root.resolve(strict=True)
    source_manifest_path = args.source_manifest.resolve(strict=True)
    source_manifest = _read_json(source_manifest_path, "three-city raw source manifest")
    city_receipts = _completed_city_receipts(source_manifest)
    city_config = _city_config(_read_json(args.source_config, "three-city source config"))
    maps = _maps_catalog(args.maps_root, args.maps_archive_integrity)

    records: list[dict[str, Any]] = []
    metadata_by_record: list[dict[str, Any]] = []
    db_failures: list[dict[str, Any]] = []
    scene_failures: list[dict[str, Any]] = []
    city_counts: dict[str, dict[str, int]] = {}
    data_members: list[dict[str, Any]] = []
    total_tagged_states = 0
    eligible_tagged_states = 0
    planned_dbs = 0
    completed_dbs = 0
    planned_scenes = 0
    eligible_scenes = 0
    completed_scenes = 0

    for city in CITY_ORDER:
        db_root = raw_root / "raw_cities" / city / "data" / "cache" / f"train_{city}"
        if not db_root.is_dir():
            raise FileNotFoundError(f"verified {city} DB directory is missing: {db_root}")
        db_paths = sorted(path for path in db_root.glob("*.db") if path.is_file())
        if not db_paths:
            raise ValueError(f"verified {city} DB directory is empty")
        city_start = len(records)
        city_planned_scenes = 0
        city_tagged_states = 0
        for db_path in db_paths:
            planned_dbs += 1
            db_relative = str(db_path.relative_to(raw_root))
            try:
                log, scenes, tagged_count = _db_scene_rows(db_path)
                completed_dbs += 1
                city_planned_scenes += len(scenes)
                city_tagged_states += tagged_count
                total_tagged_states += tagged_count
                data_members.append(
                    {
                        "city": city,
                        "relative_path": db_relative,
                        "bytes": db_path.stat().st_size,
                        "archive_sha256": city_receipts[city]["archive_sha256"],
                    }
                )
                for scene in scenes:
                    planned_scenes += 1
                    if bool(scene["scenario_builder_eligible"]):
                        eligible_scenes += 1
                        eligible_tagged_states += len(scene["tagged_states"])
                    scene_records, scene_metadata, failure = _records_for_scene(
                        city=city,
                        city_config=city_config[city],
                        city_receipt=city_receipts[city],
                        db_path=db_path,
                        db_relative_path=db_relative,
                        log=log,
                        scene=scene,
                        maps=maps,
                        max_states_per_scene=args.max_states_per_scene,
                    )
                    if failure is not None:
                        scene_failures.append(
                            {"city": city, "db_relative_path": db_relative, **dict(failure)}
                        )
                    else:
                        records.extend(scene_records)
                        metadata_by_record.extend(scene_metadata)
                        completed_scenes += 1
            except Exception as error:
                db_failures.append(
                    {
                        "city": city,
                        "db_relative_path": db_relative,
                        "failure_class": type(error).__name__,
                    }
                )
        city_counts[city] = {
            "db_planned": len(db_paths),
            "scene_planned": city_planned_scenes,
            "tagged_state_capacity": city_tagged_states,
            "source_record_count": len(records) - city_start,
        }

    records.sort(key=lambda record: record["record_id"])
    metadata_by_record.sort(key=lambda value: str(value["record_id"]))
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
                "available_map_paths": sorted(
                    str(path.relative_to(maps["root"])) for path in maps["paths"].values()
                ),
            }
        ),
    }
    no_signal = [
        item["record_id"]
        for item in metadata_by_record
        if item["record_id"].startswith("boston:")
        and item["traffic_light_status_count"] == 0
    ]
    inventory = {
        "schema_version": SCHEMA_VERSION,
        "evidence_role": EVIDENCE_ROLE,
        "outcome_fields_consumed": [],
        "raw_acquisition_manifest_path": str(source_manifest_path),
        "raw_acquisition_manifest_sha256": raw_acquisition_sha,
        "maps_archive_sha256": maps["archive_sha256"],
        "raw_source": raw_source,
        "records": records,
        "record_metadata": metadata_by_record,
        "denominator": {
            "db": {
                "planned": planned_dbs,
                "complete": completed_dbs,
                "typed_failure": len(db_failures),
                "unattempted": 0,
            },
            "scene": {
                "planned": planned_scenes,
                "complete": completed_scenes,
                "typed_failure": len(scene_failures),
                "unattempted": 0,
            },
        },
        "capacity": {
            "tagged_state_capacity": total_tagged_states,
            "official_scenario_builder_eligible_tagged_state_capacity": eligible_tagged_states,
            "scene_source_record_capacity": len(records),
            "max_states_per_eligible_scene": args.max_states_per_scene,
            "identity_selection_policy": "round_robin_sorted_scenario_type_then_state_token",
            "city_counts": city_counts,
        },
        "representative_smoke_selection": {
            "algorithm": "lexicographically_first_boston_scene_record_with_empty_current_traffic_light_status",
            "record_id": no_signal[0] if no_signal else None,
            "status": "selected" if no_signal else "no_no_signal_boston_record",
        },
        "typed_failures": {"db": db_failures, "scene": scene_failures},
    }
    inventory["identity_inventory_sha256"] = canonical_json_sha256(inventory)
    return inventory


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--maps-root", type=Path, required=True)
    parser.add_argument("--maps-archive-integrity", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--source-config", type=Path, required=True)
    parser.add_argument("--max-states-per-scene", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.max_states_per_scene <= 0:
        parser.error("--max-states-per-scene must be positive")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    inventory = build_inventory(args)
    _write_json_atomic(args.output, inventory)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "identity_inventory_sha256": inventory["identity_inventory_sha256"],
                "source_record_capacity": inventory["capacity"]["scene_source_record_capacity"],
                "tagged_state_capacity": inventory["capacity"]["tagged_state_capacity"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
