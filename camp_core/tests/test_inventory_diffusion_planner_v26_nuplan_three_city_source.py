from __future__ import annotations

import hashlib
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


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module():
    path = ROOT / "scripts/integrations/inventory_diffusion_planner_v26_nuplan_three_city_source.py"
    spec = importlib.util.spec_from_file_location("v26_nuplan_three_city_inventory", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_db(path: Path, *, location: str, index: int, signal_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    log_token = bytes([index]) * 8
    with sqlite3.connect(path) as database:
        database.executescript(
            """
            CREATE TABLE log (token BLOB, location TEXT, map_version TEXT);
            CREATE TABLE scene (token BLOB, log_token BLOB, name TEXT, roadblock_ids TEXT, goal_ego_pose_token BLOB);
            CREATE TABLE ego_pose (token BLOB);
            CREATE TABLE lidar_pc (token BLOB, scene_token BLOB);
            CREATE TABLE scenario_tag (token BLOB, lidar_pc_token BLOB, type TEXT);
            CREATE TABLE traffic_light_status (token BLOB, lidar_pc_token BLOB);
            """
        )
        database.execute("INSERT INTO log VALUES (?, ?, ?)", (log_token, location, "v1"))
        for scene_index in range(5):
            token_base = index * 32 + scene_index
            scene_token = bytes([token_base]) * 8
            lidar_token = bytes([token_base + 1]) * 8
            tag_token = bytes([token_base + 2]) * 8
            goal_token = bytes([token_base + 10]) * 8
            database.execute(
                "INSERT INTO scene VALUES (?, ?, ?, ?, ?)",
                (scene_token, log_token, f"scene-{scene_index:02d}", f"route-{index}-{scene_index}", goal_token),
            )
            database.execute("INSERT INTO ego_pose VALUES (?)", (goal_token,))
            database.execute("INSERT INTO lidar_pc VALUES (?, ?)", (lidar_token, scene_token))
            database.execute(
                "INSERT INTO scenario_tag VALUES (?, ?, ?)",
                (tag_token, lidar_token, "intersection"),
            )
            for light_index in range(signal_count if scene_index == 2 else 0):
                database.execute(
                    "INSERT INTO traffic_light_status VALUES (?, ?)",
                    (bytes([token_base + 3 + light_index]) * 8, lidar_token),
                )


def test_inventory_reads_only_three_city_identity_metadata_and_selects_no_signal_boston(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    maps_root = tmp_path / "maps"
    city_receipts = []
    archives = []
    for index, (city, map_family) in enumerate(CITY_MAPS.items(), start=1):
        _write_db(
            raw_root / "raw_cities" / city / "data/cache" / f"train_{city}" / "one.db",
            location=map_family,
            index=index,
            signal_count=0 if city == "boston" else 1,
        )
        map_path = maps_root / map_family / "v1" / "map.gpkg"
        map_path.parent.mkdir(parents=True, exist_ok=True)
        map_path.write_bytes(f"official-{city}-map".encode("utf-8"))
        receipt = tmp_path / f"{city}.receipt.json"
        receipt.write_text(
            json.dumps(
                {
                    "terminal_status": "complete",
                    "city": city,
                    "archive_verification": {"archive_sha256": hashlib.sha256(city.encode()).hexdigest(), "archive_bytes": 1},
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        city_receipts.append(
            {"city": city, "receipt_path": str(receipt), "receipt_sha256": _sha_file(receipt)}
        )
        archives.append(
            {"city": city, "map_family": map_family, "academic_role": "city_held_out_ood" if city == "singapore" else "iid_grouped_source"}
        )
    (maps_root / "nuplan-maps-v1.0.json").write_text(
        json.dumps({family: {"version": "v1"} for family in CITY_MAPS.values()}),
        encoding="utf-8",
    )
    maps_integrity = tmp_path / "maps_integrity.json"
    maps_integrity.write_text(
        json.dumps({"maps": {"archive": {"sha256": "a" * 64}}}), encoding="utf-8"
    )
    source_manifest = tmp_path / "source_manifest.json"
    source_manifest.write_text(
        json.dumps(
            {
                "terminal_status": "complete",
                "source_manifest_sha256": "b" * 64,
                "completed_cities": city_receipts,
            }
        ),
        encoding="utf-8",
    )
    source_config = tmp_path / "source_config.json"
    source_config.write_text(json.dumps({"city_archives": archives}), encoding="utf-8")

    module = _module()
    args = module.parse_args(
        [
            "--raw-root",
            str(raw_root),
            "--maps-root",
            str(maps_root),
            "--maps-archive-integrity",
            str(maps_integrity),
            "--source-manifest",
            str(source_manifest),
            "--source-config",
            str(source_config),
            "--output",
            str(tmp_path / "inventory.json"),
        ]
    )
    inventory = module.build_inventory(args)

    assert inventory["outcome_fields_consumed"] == []
    assert inventory["denominator"]["db"] == {
        "planned": 3,
        "complete": 3,
        "typed_failure": 0,
        "unattempted": 0,
    }
    assert inventory["capacity"]["scene_source_record_capacity"] == 3
    assert inventory["representative_smoke_selection"]["status"] == "selected"
    assert inventory["representative_smoke_selection"]["record_id"].startswith("boston:")
    assert all(record["official_split"] == "train" for record in inventory["records"])
