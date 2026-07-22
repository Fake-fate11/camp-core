from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence


SPLIT_ROLES = ("train", "calibration", "fresh_b2")
REQUIRED_FIELDS = frozenset(
    {
        "split",
        "source_family",
        "map_geometry_sha256",
        "intersection_sha256",
        "corridor_sha256",
        "route_family_sha256",
        "semantic_parameter_block_sha256",
        "seed_namespace",
        "route_identity_sha256",
        "scenario_family",
    }
)


def validate_v25_zero_overlap(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Validate the preregistered source/map/route/parameter split hierarchy."""

    if not rows:
        raise ValueError("split manifest must be nonempty")
    normalized = [_validate_row(row, index) for index, row in enumerate(rows)]
    by_split = {
        split: [row for row in normalized if row["split"] == split]
        for split in SPLIT_ROLES
    }
    if any(not values for values in by_split.values()):
        raise ValueError("train, calibration, and fresh_b2 must all be nonempty")

    key_contracts = {
        # Geometry and semantic clone identities deliberately exclude source
        # labels and filesystem/export provenance.  A copied map or scenario
        # block cannot escape zero-overlap by changing source_family.
        "map": lambda row: row["map_geometry_sha256"],
        "intersection": lambda row: (
            row["map_geometry_sha256"],
            row["intersection_sha256"],
        ),
        "corridor": lambda row: (
            row["map_geometry_sha256"],
            row["corridor_sha256"],
        ),
        "route_family": lambda row: (
            row["map_geometry_sha256"],
            row["route_family_sha256"],
        ),
        "semantic_parameter_block": lambda row: row[
            "semantic_parameter_block_sha256"
        ],
        "seed_namespace": lambda row: row["seed_namespace"],
        "route_identity": lambda row: row["route_identity_sha256"],
    }
    overlaps: dict[str, dict[str, list[Any]]] = {}
    counts: dict[str, dict[str, int]] = {}
    for name, key_function in key_contracts.items():
        sets: dict[str, set[Any]] = {}
        for split, split_rows in by_split.items():
            values = {
                key_function(row)
                for row in split_rows
                if not (
                    name == "intersection"
                    and row["intersection_sha256"] is None
                )
            }
            sets[split] = values
        counts[name] = {split: len(values) for split, values in sets.items()}
        pair_rows: dict[str, list[Any]] = {}
        for left_index, left in enumerate(SPLIT_ROLES):
            for right in SPLIT_ROLES[left_index + 1 :]:
                shared = sets[left] & sets[right]
                if shared:
                    pair_rows[f"{left}__{right}"] = sorted(shared, key=str)
        if pair_rows:
            overlaps[name] = pair_rows
    if overlaps:
        raise ValueError(f"V25 split zero-overlap failed: {overlaps}")

    route_splits: dict[str, set[str]] = defaultdict(set)
    for row in normalized:
        route_splits[row["route_identity_sha256"]].add(row["split"])
    leaked_routes = {
        route: sorted(splits)
        for route, splits in route_splits.items()
        if len(splits) != 1
    }
    if leaked_routes:
        raise ValueError(f"same route appears in multiple splits: {leaked_routes}")
    return {
        "schema_version": "camp_dp_v25_zero_overlap_receipt_v1",
        "status": "passed",
        "row_count": len(normalized),
        "split_row_counts": {
            split: len(split_rows) for split, split_rows in by_split.items()
        },
        "independent_unit_counts": counts,
        "source_family_strata": {
            split: sorted({row["source_family"] for row in split_rows})
            for split, split_rows in by_split.items()
        },
        "same_route_all_seeds_one_split": True,
        "map_export_clones_deduplicated_by_geometry_sha": True,
        "semantic_clones_deduplicated_independent_of_source": True,
        "identity_fields_used_as_model_features": False,
        "fresh_outcome_consumed": False,
    }


def validate_signal_complete_map_license(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Qualify versioned map sources without inferring an absent license."""

    if not rows:
        raise ValueError("map license inventory must be nonempty")
    source_geometry: dict[str, str] = {}
    counts: dict[str, int] = defaultdict(int)
    for index, row in enumerate(rows):
        if type(row) is not dict or set(row) != {
            "map_path",
            "map_file_sha256",
            "map_geometry_sha256",
            "source_kind",
            "source_reference",
            "license_spdx",
            "license_evidence_sha256",
            "project_authored",
        }:
            raise ValueError(f"map license row {index} field set drifted")
        for field in (
            "map_path",
            "map_file_sha256",
            "map_geometry_sha256",
            "source_kind",
            "source_reference",
            "license_spdx",
            "license_evidence_sha256",
        ):
            if type(row[field]) is not str or not row[field]:
                raise ValueError(f"map license row {index} {field} is invalid")
        for field in (
            "map_file_sha256",
            "map_geometry_sha256",
            "license_evidence_sha256",
        ):
            _require_sha(row[field], field)
        if type(row["project_authored"]) is not bool:
            raise ValueError("project_authored must be a native boolean")
        if row["project_authored"]:
            if row["source_kind"] != "project_authored_synthetic" or row["license_spdx"] != "MIT":
                raise ValueError("project-authored synthetic maps must use the repo MIT license")
        elif row["license_spdx"] in {"UNKNOWN", "NONE", "NOASSERTION"}:
            raise ValueError("external map license is not affirmative")
        path = row["map_path"]
        previous = source_geometry.setdefault(path, row["map_geometry_sha256"])
        if previous != row["map_geometry_sha256"]:
            raise ValueError("one map path is bound to multiple geometry SHAs")
        counts[row["source_kind"]] += 1
    return {
        "schema_version": "camp_dp_v25_signal_complete_map_license_receipt_v1",
        "status": "passed",
        "map_file_count": len(rows),
        "unique_geometry_count": len(
            {row["map_geometry_sha256"] for row in rows}
        ),
        "source_kind_counts": dict(sorted(counts.items())),
        "all_licenses_affirmative": True,
        "fresh_outcome_consumed": False,
    }


def _validate_row(row: Mapping[str, Any], index: int) -> dict[str, Any]:
    if type(row) is not dict or set(row) != REQUIRED_FIELDS:
        raise ValueError(f"split row {index} exact field set drifted")
    result = dict(row)
    if result["split"] not in SPLIT_ROLES:
        raise ValueError(f"split row {index} has an invalid role")
    for field in (
        "source_family",
        "seed_namespace",
        "scenario_family",
    ):
        if type(result[field]) is not str or not result[field]:
            raise ValueError(f"split row {index} {field} must be nonempty string")
    for field in (
        "map_geometry_sha256",
        "corridor_sha256",
        "route_family_sha256",
        "semantic_parameter_block_sha256",
        "route_identity_sha256",
    ):
        _require_sha(result[field], field)
    if result["intersection_sha256"] is not None:
        _require_sha(result["intersection_sha256"], "intersection_sha256")
    return result


def _require_sha(value: Any, name: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")
