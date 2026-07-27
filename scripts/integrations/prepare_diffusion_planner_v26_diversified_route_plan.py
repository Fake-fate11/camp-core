"""Materialize six bounded, zero-model V26 Stage 8b route projections.

The command intentionally has two modes.  ``project`` produces exactly one
family projection at a time; ``assemble`` accepts exactly those six immutable
projections and builds the 1786-route/155-corridor execution plan.  It never
loads a model, calls DP inference, or reads a V25 training directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v25_scene_runtime import FIXED_DP_HEAD  # noqa: E402
from camp_core.integrations.diffusion_planner_v26_diversified_route_plan import (  # noqa: E402
    FAMILY_PROJECTION_SCHEMA_VERSION,
    FROZEN_ROUTE_CENSUS_SHA256,
    build_diversified_route_plan,
    canonical_json_sha256,
    frozen_family_specs,
    validate_family_projection,
)
from camp_core.integrations.diffusion_planner_v26_integration_boundary import (  # noqa: E402
    enforce_v26_dp312_lanelet2_precedence,
)


_DERIVED_MAP_PATHS = {
    "nishishinjuku_plus_four_track_highway": "/root/autodl-tmp/camp_dp_assets/nishishinjuku_autoware_map/nishishinjuku_autoware_map/lanelet2_map_no_ros.osm",
    "sample_map_planning": "/root/autodl-tmp/camp_dp_assets/sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm",
    "autoware_bidirectional_traffic": "/root/autodl-tmp/camp_dp_zero_model_map_route_supply_census_20260727/derived_geometry/autoware_bidirectional_no_ros.osm",
    "legacy_intersection": "/root/autodl-tmp/camp_dp_zero_model_map_route_supply_census_20260727/derived_geometry/intersection_route_geometry_only.osm",
}
_CENSUS_FAMILY_IDS = frozenset({"legacy_kashiwanoha_cluster", "legacy_simple_cross"})


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=path, text=True, encoding="utf-8"
    ).strip()


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        staging.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)


def _spec(family_id: str) -> dict[str, Any]:
    for item in frozen_family_specs():
        if item["family_id"] == family_id:
            return item
    raise ValueError("V26 route projection family is not part of the fixed six")


def _minimal_groups(groups: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "group_sha256": str(group["group_sha256"]),
                "route_record_keys": sorted(str(item) for item in group["route_record_keys"]),
            }
            for group in groups
        ],
        key=lambda item: item["group_sha256"],
    )


def _from_frozen_census(*, family_id: str, census_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    spec = _spec(family_id)
    before = _file_sha256(census_path)
    if before != FROZEN_ROUTE_CENSUS_SHA256:
        raise ValueError("V26 legacy route-census SHA drifted")
    census = json.loads(census_path.read_text(encoding="utf-8"))
    rows = [
        dict(item)
        for item in census.get("retained_routes", [])
        if item.get("map_family_id") in set(spec["map_family_ids"])
    ]
    keys = {str(item["record_key"]) for item in rows}
    groups = [
        item
        for item in census.get("corridor_groups", [])
        if set(str(key) for key in item.get("route_record_keys", [])) and set(
            str(key) for key in item.get("route_record_keys", [])
        ).issubset(keys)
    ]
    after = _file_sha256(census_path)
    return rows, _minimal_groups(groups), before == after


def _from_derived_map(
    *, family_id: str, fixed_dp_repo: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    spec = _spec(family_id)
    map_path = Path(_DERIVED_MAP_PATHS[family_id])
    if not map_path.is_file() or _file_sha256(map_path) != spec["map_sha256s"][0]:
        raise ValueError("V26 derived map identity drifted")
    enforce_v26_dp312_lanelet2_precedence()
    from camp_core.integrations.diffusion_planner_v22_split import build_leakage_groups
    from scripts.integrations.census_diffusion_planner_v24_routes import route_census_one_map

    receipt = route_census_one_map(
        map_path,
        fixed_dp_repo,
        map_family_id=family_id,
        expected_sha256=spec["map_sha256s"][0],
    )
    if receipt.get("status") != "completed" or receipt.get("source_bytes_unchanged") is not True:
        raise RuntimeError(
            "V26 bounded route projection failed: "
            f"{receipt.get('error_type')}: {receipt.get('error_message')}"
        )
    rows = [dict(item) for item in receipt["route_records"]]
    grouping = build_leakage_groups(rows)
    return rows, _minimal_groups(grouping["groups"]), True


def project_family(
    *, family_id: str, output_path: Path, fixed_dp_repo: Path, legacy_census: Path
) -> Path:
    """Build one bounded source projection and stop before aggregate assembly."""

    if output_path.exists():
        raise FileExistsError(f"V26 family projection already exists: {output_path}")
    if _git_head(fixed_dp_repo) != FIXED_DP_HEAD:
        raise ValueError("V26 route projection fixed-DP head drifted")
    spec = _spec(family_id)
    if family_id in _CENSUS_FAMILY_IDS:
        records, groups, source_unchanged = _from_frozen_census(
            family_id=family_id, census_path=legacy_census
        )
    else:
        records, groups, source_unchanged = _from_derived_map(
            family_id=family_id, fixed_dp_repo=fixed_dp_repo
        )
    value = {
        "schema_version": FAMILY_PROJECTION_SCHEMA_VERSION,
        "family_id": family_id,
        "source_kind": "v26_sidecar_and_census_bounded_projection",
        "fixed_dp_head": FIXED_DP_HEAD,
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "source_bytes_unchanged": source_unchanged,
        "source_artifact_sha256": spec["source_artifact_sha256"],
        "map_sha256s": list(spec["map_sha256s"]),
        "route_ids_sha256": spec["route_ids_sha256"],
        "route_manifest_sha256": spec["route_manifest_sha256"],
        "corridor_manifest_sha256": spec["corridor_manifest_sha256"],
        "event_strata_sha256": spec["event_strata_sha256"],
        "materialized_route_records_sha256": canonical_json_sha256(
            sorted(records, key=lambda item: item["record_key"])
        ),
        "materialized_corridor_groups_sha256": canonical_json_sha256(groups),
        "route_records": records,
        "corridor_groups": groups,
    }
    validated = validate_family_projection(value)
    _atomic_write_json(output_path, validated)
    return output_path


def assemble_plan(*, projection_paths: Sequence[Path], output_path: Path) -> Path:
    if output_path.exists():
        raise FileExistsError(f"V26 diversified route plan already exists: {output_path}")
    projections = []
    for path in projection_paths:
        source = Path(path).resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        projections.append(json.loads(source.read_text(encoding="utf-8")))
    plan = build_diversified_route_plan(projections)
    _atomic_write_json(output_path, plan)
    return output_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    project = subparsers.add_parser("project")
    project.add_argument("--family-id", required=True)
    project.add_argument("--output", type=Path, required=True)
    project.add_argument("--fixed-dp-repo", type=Path, required=True)
    project.add_argument("--legacy-census", type=Path, required=True)
    assemble = subparsers.add_parser("assemble")
    assemble.add_argument("--projection", type=Path, action="append", required=True)
    assemble.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.mode == "project":
        print(
            project_family(
                family_id=args.family_id,
                output_path=args.output,
                fixed_dp_repo=args.fixed_dp_repo,
                legacy_census=args.legacy_census,
            )
        )
    elif args.mode == "assemble":
        print(assemble_plan(projection_paths=args.projection, output_path=args.output))
    else:
        raise AssertionError(f"unknown mode {args.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
