from __future__ import annotations

import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys

import pytest

from camp_core.integrations.diffusion_planner_v26_diversified_route_plan import (
    FAMILY_PROJECTION_SCHEMA_VERSION,
    FROZEN_FIXED_DP_HEAD,
    build_diversified_route_plan,
    canonical_json_sha256,
    frozen_family_specs,
    validate_diversified_route_plan,
)


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _projection(spec: dict[str, object]) -> dict[str, object]:
    family = str(spec["family_id"])
    count = int(spec["record_count"])
    strata_counts = dict(spec["source_strata_counts"])
    records = []
    for index in range(count):
        key = f"{family}/route-{index:04d}"
        records.append(
            {
                "record_key": key,
                "identity_sha256": _sha(f"identity/{key}"),
                "map_family_id": spec["map_family_ids"][0],
                "source_map_path": f"/root/autodl-tmp/maps/{family}.osm",
                "source_map_sha256": spec["map_sha256s"][0],
                "lanelet_ids": [index * 2 + 1, index * 2 + 2],
                "source_stratum": {
                    name: index < int(strata_counts[name]) for name in strata_counts
                },
                "holdout_forbidden": False,
                "route_spec": {
                    "map_path": f"/root/autodl-tmp/maps/{family}.osm",
                    "lanelet_ids": [index * 2 + 1, index * 2 + 2],
                    "start_pose": [float(index), 0.0, 0.0],
                    "goal_pose": [float(index) + 1.0, 0.0, 0.0],
                    "route_length_m": 20.0,
                },
                "route_serialization_sha256": _sha(f"serialization/{key}"),
                "source_geometry_sha256": _sha(f"geometry/{key}"),
            }
        )
    corridor_count = int(spec["corridor_count"])
    groups = []
    for group_index in range(corridor_count):
        route_keys = [
            record["record_key"]
            for record_index, record in enumerate(records)
            if record_index % corridor_count == group_index
        ]
        groups.append(
            {
                "group_sha256": _sha(f"group/{family}/{group_index}"),
                "route_record_keys": route_keys,
            }
        )
    return {
        "schema_version": FAMILY_PROJECTION_SCHEMA_VERSION,
        "family_id": family,
        "source_kind": "v26_sidecar_and_census_bounded_projection",
        "fixed_dp_head": FROZEN_FIXED_DP_HEAD,
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "source_bytes_unchanged": True,
        "source_artifact_sha256": spec["source_artifact_sha256"],
        "map_sha256s": list(spec["map_sha256s"]),
        "route_ids_sha256": spec["route_ids_sha256"],
        "route_manifest_sha256": spec["route_manifest_sha256"],
        "corridor_manifest_sha256": spec["corridor_manifest_sha256"],
        "event_strata_sha256": spec["event_strata_sha256"],
        "materialized_route_records_sha256": canonical_json_sha256(records),
        "materialized_corridor_groups_sha256": canonical_json_sha256(
            sorted(groups, key=lambda item: item["group_sha256"])
        ),
        "route_records": records,
        "corridor_groups": groups,
    }


def _projections() -> list[dict[str, object]]:
    return [_projection(spec) for spec in frozen_family_specs()]


def test_six_bounded_projections_reconcile_to_the_frozen_route_plan() -> None:
    plan = build_diversified_route_plan(_projections())

    assert plan["denominator"] == {
        "planned": 1786,
        "complete": 0,
        "failed": 0,
        "unattempted": 1786,
    }
    assert len(plan["routes"]) == 1786
    assert len({route["corridor_id"] for route in plan["routes"]}) == 155
    assert validate_diversified_route_plan(plan) == plan


def test_route_plan_rejects_one_family_event_stratum_drift() -> None:
    projections = _projections()
    projections[0]["route_records"][0]["source_stratum"]["traffic_light"] = False

    with pytest.raises(ValueError, match="event-strata identity"):
        build_diversified_route_plan(projections)


def test_route_plan_rejects_v25_training_directory_as_a_route_input() -> None:
    projections = _projections()
    projections[0]["route_records"][0]["source_map_path"] = (
        "/root/autodl-tmp/camp_dp_v25_camp_training_legacy/map.osm"
    )
    projections[0]["route_records"][0]["route_spec"]["map_path"] = (
        "/root/autodl-tmp/camp_dp_v25_camp_training_legacy/map.osm"
    )

    with pytest.raises(ValueError, match="V25 training directories"):
        build_diversified_route_plan(projections)


def test_route_plan_sha_rejects_tampering_after_assembly() -> None:
    plan = build_diversified_route_plan(_projections())
    changed = copy.deepcopy(plan)
    changed["routes"][0]["event_manifest_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="event manifest"):
        validate_diversified_route_plan(changed)


def test_route_projection_cli_is_family_bounded_and_zero_model() -> None:
    runner = importlib.import_module(
        "scripts.integrations.prepare_diffusion_planner_v26_diversified_route_plan"
    )
    project = runner.parse_args(
        [
            "project",
            "--family-id", "legacy_simple_cross",
            "--output", "family.json",
            "--fixed-dp-repo", "fixed-dp",
            "--legacy-census", "route_census.json",
        ]
    )
    assert project.mode == "project"
    assemble = runner.parse_args(
        ["assemble", "--projection", "a.json", "--projection", "b.json", "--output", "plan.json"]
    )
    assert assemble.mode == "assemble"
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert "route_census_one_map" in source
    assert "run_v26_native_same_ego_b8_replay" not in source
    assert "validate_diffusion_planner_v25_fair_nonholdout" not in source


def test_census_projection_reads_nested_source_only_corridor_groups(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = importlib.import_module(
        "scripts.integrations.prepare_diffusion_planner_v26_diversified_route_plan"
    )
    family_id = "legacy_simple_cross"
    route_keys = [f"{family_id}/route-{index}" for index in range(2)]
    census_path = tmp_path / "route_census.json"
    census_path.write_text(
        json.dumps(
            {
                "retained_routes": [
                    {
                        "record_key": key,
                        "map_family_id": "map_family_f62e06cd1303",
                    }
                    for key in route_keys
                ],
                "corridor_groups": {
                    "source_only": True,
                    "outcome_fields_consumed": [],
                    "groups": [
                        {
                            "group_sha256": _sha("nested-corridor"),
                            "route_record_keys": route_keys,
                            "route_record_count": 2,
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "FROZEN_ROUTE_CENSUS_SHA256", runner._file_sha256(census_path))

    records, groups, source_unchanged = runner._from_frozen_census(
        family_id=family_id, census_path=census_path
    )

    assert [record["record_key"] for record in records] == route_keys
    assert groups == [{"group_sha256": _sha("nested-corridor"), "route_record_keys": route_keys}]
    assert source_unchanged is True
