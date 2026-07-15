from __future__ import annotations

import inspect
from pathlib import Path

from scripts.integrations.census_diffusion_planner_v24_routes import (
    build_route_execution_plan,
    deduplicate_route_records,
    enumerate_route_sequences,
    route_census_one_map,
)


ROOT = Path(__file__).resolve().parents[2]
PLAN = (
    ROOT
    / "docs"
    / "superpowers"
    / "plans"
    / "2026-07-15-v24-outcome-blind-route-census.md"
)


def test_route_sequence_census_is_deterministic_and_keeps_every_start() -> None:
    result = enumerate_route_sequences(
        drivable_ids=[4, 3, 2, 1],
        following_by_id={1: [3, 2], 2: [4], 3: [4], 4: []},
        length_by_id={1: 30.0, 2: 30.0, 3: 30.0, 4: 30.0},
        min_route_length_m=80.0,
        max_hops=100,
    )

    assert result == [
        {
            "start_lanelet_id": 1,
            "lanelet_ids": [1, 2, 4],
            "source_arc_length_m": 90.0,
            "status": "qualifying",
            "failure_reason": None,
        },
        {
            "start_lanelet_id": 2,
            "lanelet_ids": [2, 4],
            "source_arc_length_m": 60.0,
            "status": "below_minimum_length",
            "failure_reason": "dead_end_before_80m",
        },
        {
            "start_lanelet_id": 3,
            "lanelet_ids": [3, 4],
            "source_arc_length_m": 60.0,
            "status": "below_minimum_length",
            "failure_reason": "dead_end_before_80m",
        },
        {
            "start_lanelet_id": 4,
            "lanelet_ids": [4],
            "source_arc_length_m": 30.0,
            "status": "below_minimum_length",
            "failure_reason": "dead_end_before_80m",
        },
    ]


def test_route_sequence_census_breaks_cycles_without_redrawing() -> None:
    result = enumerate_route_sequences(
        drivable_ids=[1, 2],
        following_by_id={1: [2], 2: [1]},
        length_by_id={1: 30.0, 2: 30.0},
        min_route_length_m=80.0,
        max_hops=100,
    )

    assert [row["failure_reason"] for row in result] == [
        "cycle_before_80m",
        "cycle_before_80m",
    ]
    assert [row["lanelet_ids"] for row in result] == [[1, 2], [2, 1]]


def test_exact_route_dedup_keeps_all_raw_receipts() -> None:
    records = [
        {
            "record_key": "a/1",
            "identity_sha256": "1" * 64,
            "map_family_id": "family-a",
            "source_map_path": "maps/a.osm",
        },
        {
            "record_key": "b/9",
            "identity_sha256": "1" * 64,
            "map_family_id": "family-a",
            "source_map_path": "maps/b.osm",
        },
        {
            "record_key": "a/2",
            "identity_sha256": "2" * 64,
            "map_family_id": "family-a",
            "source_map_path": "maps/a.osm",
        },
    ]

    result = deduplicate_route_records(records)

    assert [row["record_key"] for row in result["retained_routes"]] == [
        "a/1",
        "a/2",
    ]
    assert result["raw_route_count"] == 3
    assert result["deduplicated_route_count"] == 2
    assert result["duplicate_route_count"] == 1
    assert result["receipts"] == [
        {
            "record_key": "a/1",
            "retained_record_key": "a/1",
            "status": "retained",
        },
        {
            "record_key": "a/2",
            "retained_record_key": "a/2",
            "status": "retained",
        },
        {
            "record_key": "b/9",
            "retained_record_key": "a/1",
            "status": "exact_identity_duplicate",
        },
    ]


def test_route_execution_plan_runs_only_loaded_blobs_and_keeps_family() -> None:
    census = {
        "maps": [
            {"relative_path": "maps/a.osm", "file_sha256_receipt": "a" * 64},
            {"relative_path": "maps/b.osm", "file_sha256_receipt": "b" * 64},
            {"relative_path": "maps/c.osm", "file_sha256_receipt": "c" * 64},
        ]
    }
    families = {
        "families": [
            {
                "family_id": "family-one",
                "blob_sha256s": ["a" * 64, "b" * 64],
                "paths": ["maps/a.osm", "maps/b.osm"],
            },
            {
                "family_id": "family-two",
                "blob_sha256s": ["c" * 64],
                "paths": ["maps/c.osm"],
            },
        ]
    }
    builder = {
        "worker_results": {
            "a" * 64: {"status": "loaded"},
            "b" * 64: {"status": "failed"},
            "c" * 64: {"status": "loaded"},
        }
    }

    assert build_route_execution_plan(census, families, builder) == [
        {
            "file_sha256": "a" * 64,
            "map_family_id": "family-one",
            "representative_path": "maps/a.osm",
            "paths": ["maps/a.osm"],
        },
        {
            "file_sha256": "c" * 64,
            "map_family_id": "family-two",
            "representative_path": "maps/c.osm",
            "paths": ["maps/c.osm"],
        },
    ]


def test_route_worker_preserves_loader_order_and_never_loads_model() -> None:
    source = inspect.getsource(route_census_one_map)
    regulatory = source.index(
        "require_source_preserving_lanelet2_regulatory_adapter(map_path)"
    )
    projection = source.index("install_lanelet2_projection_fallback(map_path)")
    builder = source.index("LaneletSceneBuilder(str(map_path))")

    assert regulatory < projection < builder
    assert "_load_model" not in source
    assert "Route(" not in source
    assert "outcome" not in source.lower()


def test_route_census_plan_freezes_source_only_denominator() -> None:
    text = " ".join(PLAN.read_text(encoding="utf-8").split())
    for phrase in (
        "one deterministic route attempt per fixed-builder drivable start lanelet",
        "smallest numeric successor",
        "first prefix whose accumulated source arc length is >=80m",
        "100 hops",
        "Exact route identity duplicates collapse",
        "corridor-overlap connected components remain indivisible",
        "every start-lanelet attempt remains in the denominator",
        "model, candidate, outcome, and holdout stay unopened",
    ):
        assert phrase in text
