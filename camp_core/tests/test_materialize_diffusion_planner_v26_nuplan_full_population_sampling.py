from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


CITY_MAPS = {
    "boston": "us-ma-boston",
    "pittsburgh": "us-pa-pittsburgh-hazelwood",
    "singapore": "sg-one-north",
}


def _module():
    path = ROOT / "scripts/integrations/materialize_diffusion_planner_v26_nuplan_full_population_sampling.py"
    spec = importlib.util.spec_from_file_location("v26_nuplan_full_population_sampling", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_db(path: Path, *, city: str, index: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    log_token = bytes([index]) * 8
    lidar_token = bytes([index + 1]) * 8
    with sqlite3.connect(path) as database:
        database.executescript(
            """
            CREATE TABLE log (token BLOB, location TEXT, map_version TEXT);
            CREATE TABLE scene (token BLOB, log_token BLOB, name TEXT, roadblock_ids TEXT, goal_ego_pose_token BLOB);
            CREATE TABLE ego_pose (
                token BLOB, timestamp INTEGER, x FLOAT, y FLOAT, z FLOAT,
                qw FLOAT, qx FLOAT, qy FLOAT, qz FLOAT,
                vx FLOAT, vy FLOAT, vz FLOAT,
                acceleration_x FLOAT, acceleration_y FLOAT, acceleration_z FLOAT,
                angular_rate_x FLOAT, angular_rate_y FLOAT, angular_rate_z FLOAT,
                epsg INTEGER, log_token BLOB
            );
            CREATE TABLE lidar (token BLOB, log_token BLOB);
            CREATE TABLE lidar_pc (
                token BLOB, next_token BLOB, prev_token BLOB, ego_pose_token BLOB,
                lidar_token BLOB, scene_token BLOB, filename TEXT, timestamp INTEGER
            );
            CREATE TABLE scenario_tag (token BLOB, lidar_pc_token BLOB, type TEXT, agent_track_token BLOB);
            CREATE TABLE traffic_light_status (token BLOB, lidar_pc_token BLOB, lane_connector_id INTEGER, status TEXT);
            """
        )
        database.execute("INSERT INTO log VALUES (?, ?, ?)", (log_token, CITY_MAPS[city], CITY_MAPS[city]))
        database.execute("INSERT INTO lidar VALUES (?, ?)", (lidar_token, log_token))
        for scene_index in range(5):
            scene_token = bytes([index * 20 + scene_index]) * 8
            goal_token = bytes([index * 20 + scene_index + 50]) * 8
            database.execute(
                "INSERT INTO scene VALUES (?, ?, ?, ?, ?)",
                (scene_token, log_token, f"scene-{scene_index:02d}", f"route-{city}-{scene_index}", goal_token),
            )
            database.execute(
                "INSERT INTO ego_pose VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (goal_token, 0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, log_token),
            )
            if scene_index != 2:
                continue
            for anchor_index in range(4):
                state_token = bytes([index * 20 + scene_index + anchor_index + 80]) * 8
                pose_token = bytes([index * 20 + scene_index + anchor_index + 100]) * 8
                database.execute(
                    "INSERT INTO ego_pose VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        pose_token,
                        anchor_index,
                        0.0,
                        0.0,
                        0.0,
                        1.0,
                        0.0,
                        0.0,
                        0.0,
                        float(anchor_index),
                        0.0,
                        0.0,
                        1.0 if anchor_index == 1 else 0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.2 if anchor_index == 2 else 0.0,
                        0,
                        log_token,
                    ),
                )
                database.execute(
                    "INSERT INTO lidar_pc VALUES (?, NULL, NULL, ?, ?, ?, ?, ?)",
                    (state_token, pose_token, lidar_token, scene_token, f"{anchor_index}.pcd", anchor_index),
                )
                if anchor_index == 1:
                    database.execute(
                        "INSERT INTO scenario_tag VALUES (?, ?, ?, NULL)",
                        (bytes([index * 20 + 140]) * 8, state_token, "on_intersection"),
                    )
                    database.execute(
                        "INSERT INTO scenario_tag VALUES (?, ?, ?, NULL)",
                        (bytes([index * 20 + 141]) * 8, state_token, "stationary"),
                    )
                    database.execute(
                        "INSERT INTO traffic_light_status VALUES (?, ?, ?, ?)",
                        (bytes([index * 20 + 142]) * 8, state_token, 1, "RED"),
                    )


def _inputs(tmp_path: Path) -> dict[str, Path]:
    raw_root = tmp_path / "raw"
    maps_root = tmp_path / "maps"
    receipts = []
    archives = []
    for index, (city, map_family) in enumerate(CITY_MAPS.items(), start=1):
        _write_db(
            raw_root / "raw_cities" / city / "data/cache" / f"train_{city}" / "one.db",
            city=city,
            index=index,
        )
        map_path = maps_root / map_family / "v1" / "map.gpkg"
        map_path.parent.mkdir(parents=True, exist_ok=True)
        map_path.write_bytes(f"map-{city}".encode())
        receipt_path = tmp_path / f"{city}.json"
        receipt_sha = (city * 64)[:64]
        receipt_path.write_text(
            json.dumps(
                {
                    "terminal_status": "complete",
                    "city": city,
                    "receipt_sha256": receipt_sha,
                    "archive_verification": {"archive_sha256": ("a" + city[0]) * 32, "archive_bytes": 1},
                }
            ),
            encoding="utf-8",
        )
        receipts.append({"city": city, "receipt_path": str(receipt_path), "receipt_sha256": receipt_sha})
        archives.append(
            {
                "city": city,
                "map_family": map_family,
                "academic_role": "city_held_out_ood" if city == "singapore" else "iid_grouped_source",
            }
        )
    (maps_root / "nuplan-maps-v1.0.json").write_text(
        json.dumps({map_family: {"version": "v1"} for map_family in CITY_MAPS.values()}),
        encoding="utf-8",
    )
    maps_integrity = tmp_path / "maps_integrity.json"
    maps_integrity.write_text(json.dumps({"maps": {"sha256": "f" * 64}}), encoding="utf-8")
    source_manifest = tmp_path / "source_manifest.json"
    source_manifest.write_text(
        json.dumps({"terminal_status": "complete", "source_manifest_sha256": "c" * 64, "completed_cities": receipts}),
        encoding="utf-8",
    )
    source_config = tmp_path / "source_config.json"
    source_config.write_text(json.dumps({"city_archives": archives}), encoding="utf-8")
    binding = tmp_path / "fixed_dp.json"
    binding.write_text(
        json.dumps({"head": "7a1d33da277a1992ec474b5383a0c963c72e04e4", "checkpoint_sha256": "d" * 64, "args_sha256": "e" * 64}),
        encoding="utf-8",
    )
    return {
        "raw_root": raw_root,
        "maps_root": maps_root,
        "maps_integrity": maps_integrity,
        "source_manifest": source_manifest,
        "source_config": source_config,
        "binding": binding,
    }


def test_full_population_sampling_splits_before_source_event_sampling_and_merges_tags(tmp_path: Path) -> None:
    paths = _inputs(tmp_path)
    module = _module()
    args = module.parse_args(
        [
            "--raw-root", str(paths["raw_root"]),
            "--maps-root", str(paths["maps_root"]),
            "--maps-archive-integrity", str(paths["maps_integrity"]),
            "--source-manifest", str(paths["source_manifest"]),
            "--source-config", str(paths["source_config"]),
            "--fixed-dp-binding", str(paths["binding"]),
            "--camp-source-head", "a" * 40,
            "--output", str(tmp_path / "manifest.json"),
        ]
    )

    manifest = module.build_manifest(args)

    assert manifest["outcome_fields_consumed"] == []
    assert manifest["denominator"]["anchor"]["eligible_population"] == 12
    assert len(manifest["population_groups"]) == 3
    assert all(value == 0 for value in manifest["zero_overlap"].values())
    assert len({row["anchor_id"] for row in manifest["selected_anchors"]}) == len(manifest["selected_anchors"])
    duplicate_tag_anchor = next(
        row
        for row in manifest["selected_anchors"]
        if {"scenario_tag:on_intersection", "scenario_tag:stationary"}
        <= {entry["stratum"] for entry in row["event_memberships"]}
    )
    assert duplicate_tag_anchor["anchor_id"].count(":") >= 3
    assert any(
        row["city"] == "singapore" and row["partition"] == "test_ood"
        for row in manifest["coverage"]
    )
    assert all(
        row["sampling_probability"] == 1.0
        for row in manifest["city_partition_tag_phase"]
    )
    assert "max_states_per_scene" not in manifest["sampling_contract"]
