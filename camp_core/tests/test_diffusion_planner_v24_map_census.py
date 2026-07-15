from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

from scripts.integrations.census_diffusion_planner_v24_lanelet2_maps import (
    SCENARIO_COMMIT,
    SCENARIO_REPOSITORY,
    build_static_census,
)
from scripts.integrations.adjudicate_diffusion_planner_v24_map_families import (
    adjudicate_map_families,
)
from scripts.integrations.smoke_diffusion_planner_v24_lanelet2_builders import (
    build_blob_execution_plan,
    merge_path_receipts,
    smoke_one_map,
)


PLAN = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "superpowers"
    / "plans"
    / "2026-07-15-v24-tier4-lanelet2-map-census.md"
)
FAMILY_PLAN = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "superpowers"
    / "plans"
    / "2026-07-15-v24-map-family-adjudication.md"
)
LICENSE = b"Apache License\nVersion 2.0, January 2004\n"


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _map(*, shift: float = 0.0, id_offset: int = 0) -> bytes:
    node_a = 1 + id_offset
    node_b = 2 + id_offset
    node_c = 3 + id_offset
    node_d = 4 + id_offset
    left = 10 + id_offset
    right = 11 + id_offset
    lanelet = 20 + id_offset
    control = 30 + id_offset
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">
  <node id="{node_a}" lat="{35.0 + shift:.7f}" lon="{139.0 + shift:.7f}"/>
  <node id="{node_b}" lat="{35.001 + shift:.7f}" lon="{139.0 + shift:.7f}"/>
  <node id="{node_c}" lat="{35.0 + shift:.7f}" lon="{139.0001 + shift:.7f}"/>
  <node id="{node_d}" lat="{35.001 + shift:.7f}" lon="{139.0001 + shift:.7f}"/>
  <way id="{left}"><nd ref="{node_a}"/><nd ref="{node_b}"/></way>
  <way id="{right}"><nd ref="{node_c}"/><nd ref="{node_d}"/></way>
  <relation id="{lanelet}">
    <member type="way" ref="{left}" role="left"/>
    <member type="way" ref="{right}" role="right"/>
    <member type="relation" ref="{control}" role="regulatory_element"/>
    <tag k="type" v="lanelet"/>
    <tag k="subtype" v="road"/>
    <tag k="location" v="urban"/>
    <tag k="speed_limit" v="10 m/s"/>
  </relation>
  <relation id="{control}">
    <tag k="type" v="regulatory_element"/>
    <tag k="subtype" v="traffic_light"/>
  </relation>
</osm>
""".encode()


def _write_source(
    root: Path,
    maps: dict[str, bytes],
    *,
    receipt_sha_overrides: dict[str, str] | None = None,
    commit: str = SCENARIO_COMMIT,
) -> Path:
    source_root = root / "sources" / "scenario_simulator_v2"
    source_root.mkdir(parents=True)
    (source_root / "LICENSE").write_bytes(LICENSE)
    rows = []
    for relative_path, payload in maps.items():
        destination = source_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        rows.append(
            {
                "commit": commit,
                "file_sha256": (receipt_sha_overrides or {}).get(
                    relative_path, _sha(payload)
                ),
                "git_blob_oid": "a" * 40,
                "git_blob_sha256": "b" * 64,
                "raw_url": (
                    "https://raw.githubusercontent.com/tier4/"
                    f"scenario_simulator_v2/{commit}/{relative_path}"
                ),
                "relative_path": relative_path,
                "retrieved_at": "2026-07-15T09:28:32Z",
                "role": "map",
                "size_bytes": len(payload),
                "source_id": "scenario_simulator_v2",
            }
        )
    rows.append(
        {
            "commit": commit,
            "file_sha256": _sha(LICENSE),
            "git_blob_oid": "c" * 40,
            "git_blob_sha256": "d" * 64,
            "raw_url": "https://example.invalid/LICENSE",
            "relative_path": "LICENSE",
            "retrieved_at": "2026-07-15T09:28:32Z",
            "role": "license",
            "size_bytes": len(LICENSE),
            "source_id": "scenario_simulator_v2",
        }
    )
    manifest = {
        "schema": "diffusion_planner_v23_source_freeze_v1",
        "map_path_count": len(maps),
        "unique_map_file_sha256_count": len(
            {row["file_sha256"] for row in rows if row["role"] == "map"}
        ),
        "original_source_bytes_modified": False,
        "excluded_sources": [
            "INTERACTION",
            "inD",
            "rounD",
            "exiD",
            "CARLA",
            "nuPlan",
            "nuScenes",
        ],
        "files": rows,
        "sources": [
            {
                "commit": commit,
                "license_file_sha256": _sha(LICENSE),
                "license_identifier": "Apache-2.0",
                "license_path": "LICENSE",
                "map_path_count": len(maps),
                "map_paths": sorted(maps),
                "notice_path": None,
                "notice_status": "absent_at_commit",
                "repository_url": SCENARIO_REPOSITORY,
                "selection": "all_osm",
                "source_id": "scenario_simulator_v2",
                "unique_map_file_sha256_count": len(
                    {row["file_sha256"] for row in rows if row["role"] == "map"}
                ),
            }
        ],
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_census_keeps_paths_deduplicates_blobs_and_normalizes_geometry(
    tmp_path: Path,
) -> None:
    base = _map()
    manifest = _write_source(
        tmp_path / "payload",
        {
            "maps/base.osm": base,
            "maps/copy.osm": base,
            "maps/translated.osm": _map(shift=1.0, id_offset=100),
        },
    )

    result = build_static_census(
        manifest,
        tmp_path / "census",
        expected_path_count=3,
        expected_unique_blob_count=2,
    )

    assert result["map_path_count"] == 3
    assert result["unique_map_file_sha256_count"] == 2
    assert result["denominator_path_count"] == 3
    assert result["map_family_count"] is None
    assert result["geometry_cluster_candidate_count"] == 1
    assert result["geometry_topology_cluster_candidate_count"] == 1
    assert len({row["geometry_fingerprint"] for row in result["maps"]}) == 1
    assert len({row["topology_fingerprint"] for row in result["maps"]}) == 1
    for row in result["maps"]:
        assert row["source_contract_valid"] is True
        assert row["xml_valid"] is True
        assert row["lanelet_topology"]["lanelet_count"] == 1
        assert row["regulatory_subtype_counts"] == {"traffic_light": 1}
        assert row["speed_source"]["explicit"] is True
        assert row["traffic_control_source"]["lanelet_attachment_count"] == 1
        assert row["builder_smoke_status"] == "pending_fixed_builder_execution"
    assert result["builder_smoke_started"] is False
    assert result["route_census_started"] is False
    assert result["outcome_accessed"] is False


def test_census_records_per_map_failures_without_dropping_denominator(
    tmp_path: Path,
) -> None:
    malformed = b"<osm><node>"
    manifest = _write_source(
        tmp_path / "payload",
        {
            "maps/valid.osm": _map(),
            "maps/malformed.osm": malformed,
            "maps/hash_mismatch.osm": _map(shift=0.5),
        },
        receipt_sha_overrides={"maps/hash_mismatch.osm": "0" * 64},
    )

    result = build_static_census(
        manifest,
        tmp_path / "census",
        expected_path_count=3,
        expected_unique_blob_count=3,
    )
    rows = {row["relative_path"]: row for row in result["maps"]}

    assert len(rows) == result["denominator_path_count"] == 3
    assert rows["maps/malformed.osm"]["xml_valid"] is False
    assert "xml_parse_error" in rows["maps/malformed.osm"]["failure_reasons"]
    assert rows["maps/hash_mismatch.osm"]["source_contract_valid"] is False
    assert "file_sha256_mismatch" in rows["maps/hash_mismatch.osm"][
        "failure_reasons"
    ]
    assert result["source_valid_path_count"] == 2
    assert result["xml_valid_path_count"] == 2


def test_census_rejects_unfrozen_source_and_existing_output(tmp_path: Path) -> None:
    manifest = _write_source(
        tmp_path / "payload",
        {"maps/map.osm": _map()},
        commit="f" * 40,
    )

    with pytest.raises(ValueError, match="frozen scenario commit"):
        build_static_census(
            manifest,
            tmp_path / "census",
            expected_path_count=1,
            expected_unique_blob_count=1,
        )

    valid_manifest = _write_source(
        tmp_path / "valid_payload",
        {"maps/map.osm": _map()},
    )
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        build_static_census(
            valid_manifest,
            output,
            expected_path_count=1,
            expected_unique_blob_count=1,
        )


def test_branch_b_plan_preserves_denominator_and_isolates_builder_processes() -> None:
    text = " ".join(PLAN.read_text(encoding="utf-8").split())
    for phrase in (
        "14 path receipts / 12 unique byte blobs",
        "Map-family count remains unset",
        "one isolated process per unique byte blob",
        "all 14 paths remain in the denominator",
        "unsupported element excludes only that map",
        "No relation or subtype is rewritten",
        "outcome-blind",
        ">=80m",
    ):
        assert phrase in text


def test_builder_smoke_plan_executes_once_per_blob_and_keeps_every_path() -> None:
    census = {
        "maps": [
            {
                "relative_path": "maps/a.osm",
                "file_sha256_receipt": "a" * 64,
                "source_contract_valid": True,
            },
            {
                "relative_path": "maps/a_copy.osm",
                "file_sha256_receipt": "a" * 64,
                "source_contract_valid": True,
            },
            {
                "relative_path": "maps/b.osm",
                "file_sha256_receipt": "b" * 64,
                "source_contract_valid": True,
            },
        ]
    }

    plan = build_blob_execution_plan(census)

    assert len(plan) == 2
    assert plan[0] == {
        "file_sha256": "a" * 64,
        "representative_path": "maps/a.osm",
        "paths": ["maps/a.osm", "maps/a_copy.osm"],
    }
    assert plan[1]["representative_path"] == "maps/b.osm"


def test_builder_smoke_maps_blob_failure_to_paths_without_global_stop() -> None:
    census = {
        "maps": [
            {
                "relative_path": "maps/a.osm",
                "file_sha256_receipt": "a" * 64,
                "source_contract_valid": True,
            },
            {
                "relative_path": "maps/a_copy.osm",
                "file_sha256_receipt": "a" * 64,
                "source_contract_valid": True,
            },
            {
                "relative_path": "maps/b.osm",
                "file_sha256_receipt": "b" * 64,
                "source_contract_valid": True,
            },
        ]
    }
    results = {
        "a" * 64: {
            "status": "loaded",
            "failure_category": None,
            "source_bytes_unchanged": True,
        },
        "b" * 64: {
            "status": "failed",
            "failure_category": "unsupported_regulatory_element",
            "source_bytes_unchanged": True,
        },
    }

    receipts = merge_path_receipts(census, results)
    by_path = {row["relative_path"]: row for row in receipts}

    assert len(receipts) == 3
    assert by_path["maps/a.osm"]["executed"] is True
    assert by_path["maps/a_copy.osm"]["executed"] is False
    assert by_path["maps/a_copy.osm"]["reused_from"] == "maps/a.osm"
    assert by_path["maps/b.osm"]["status"] == "failed"
    assert by_path["maps/b.osm"]["failure_category"] == (
        "unsupported_regulatory_element"
    )
    assert all(row["source_bytes_unchanged"] for row in receipts)


def test_builder_worker_prepares_regulatory_before_projection_and_load() -> None:
    source = inspect.getsource(smoke_one_map)
    regulatory = source.index(
        "regulatory_receipt = require_source_preserving_lanelet2_regulatory_adapter"
    )
    projection = source.index(
        "projection_fallback_installed = install_lanelet2_projection_fallback"
    )
    builder = source.index("builder = LaneletSceneBuilder")

    assert regulatory < projection < builder
    assert "_load_model" not in source
    assert "Route(" not in source


def test_map_family_adjudication_uses_geography_and_segments_not_names(
    tmp_path: Path,
) -> None:
    base = _map()
    manifest = _write_source(
        tmp_path / "payload",
        {
            "maps/base.osm": base,
            "copies/renamed.osm": base,
            "configs/id_variant.osm": _map(id_offset=100),
            "elsewhere/same_shape.osm": _map(shift=1.0, id_offset=200),
            "empty/no_geometry.osm": b'<osm version="0.6"/>\n',
        },
    )
    census_dir = tmp_path / "census"
    build_static_census(
        manifest,
        census_dir,
        expected_path_count=5,
        expected_unique_blob_count=4,
    )
    builder = {
        "schema": "diffusion_planner_v24_lanelet2_builder_smoke_v1",
        "path_receipts": [
            {
                "relative_path": path,
                "status": (
                    "loaded"
                    if path
                    in {
                        "maps/base.osm",
                        "copies/renamed.osm",
                        "configs/id_variant.osm",
                    }
                    else "failed"
                ),
                "failure_category": (
                    None
                    if path
                    in {
                        "maps/base.osm",
                        "copies/renamed.osm",
                        "configs/id_variant.osm",
                    }
                    else "builder_load_failure"
                ),
                "source_bytes_unchanged": True,
            }
            for path in (
                "maps/base.osm",
                "copies/renamed.osm",
                "configs/id_variant.osm",
                "elsewhere/same_shape.osm",
                "empty/no_geometry.osm",
            )
        ],
    }
    builder_path = tmp_path / "builder.json"
    builder_path.write_text(json.dumps(builder), encoding="utf-8")

    result = adjudicate_map_families(
        census_dir / "census.json",
        builder_path,
        tmp_path / "families",
    )

    assert result["map_family_count"] == 2
    assert result["loadable_map_family_count"] == 1
    assert result["unassigned_path_count"] == 1
    assert result["split_regime"] == (
        "corridor_group_within_family_no_unseen_map_claim"
    )
    base_family = next(
        family
        for family in result["families"]
        if "maps/base.osm" in family["paths"]
    )
    assert base_family["paths"] == [
        "configs/id_variant.osm",
        "copies/renamed.osm",
        "maps/base.osm",
    ]
    elsewhere_family = next(
        family
        for family in result["families"]
        if "elsewhere/same_shape.osm" in family["paths"]
    )
    assert elsewhere_family["loadable"] is False
    assert result["unassigned_paths"] == [
        {
            "relative_path": "empty/no_geometry.osm",
            "reason": "no_geometry_or_bbox",
        }
    ]
    assert result["route_census_started"] is False
    assert result["outcome_accessed"] is False


def test_map_family_plan_freezes_outcome_blind_graph_rule() -> None:
    text = " ".join(FAMILY_PLAN.read_text(encoding="utf-8").split())
    for phrase in (
        "bbox containment >= 0.98",
        "absolute segment containment >= 0.80",
        "connected components",
        "Builder status never creates a family edge",
        "Exact byte duplicates remain one blob node",
        "No geometry is an unassigned source receipt",
        "route census remains unopened",
    ):
        assert phrase in text
