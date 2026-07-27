"""Frozen, nonholdout route-plan contracts for V26 Stage 8b.

This module contains only route-input provenance and deterministic plan
assembly.  It never loads a model, calls Diffusion Planner, or reads a V25
training directory.  The six source projections are deliberately retained as
separate family records so a failed transport of one projection cannot be
mistaken for a completed aggregate census.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any, Mapping, Sequence


ROUTE_PLAN_SCHEMA_VERSION = "camp_dp_v26_diversified_route_plan_v1"
FAMILY_PROJECTION_SCHEMA_VERSION = "camp_dp_v26_diversified_family_projection_v1"
ROUTE_PLAN_EVIDENCE_ROLE = "development_nonholdout_diversified_training_route_plan"
FROZEN_FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FROZEN_ROUTE_CENSUS_SHA256 = (
    "72dcf8abce37793432b8a1b7c4cec43378860ee9b8f09f1717d38c7b93ea2ccd"
)
FROZEN_SIDECAR_INDEX_SHA256 = (
    "a16e1a753089c71924f3bd8724f87e3dc2a583cd52e73d42d25439d38b0240d5"
)
FROZEN_SIDECAR_INDEX_PATH = "/root/autodl-tmp/camp_autoware_lanelet2_sidecar_v2_20260727/index.json"

_SHA_CHARS = frozenset("0123456789abcdef")


def canonical_json_sha256(value: Any) -> str:
    """Hash a JSON-compatible value using the V26 deterministic encoding."""

    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or set(value) - _SHA_CHARS:
        raise ValueError(f"{label} must be a lowercase SHA256")
    return value


def _exact_mapping(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise ValueError(f"{label} field set drifted")
    return dict(value)


def _strict_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be bool")
    return value


def _strict_string(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _strict_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return value


def _finite_pose(value: Any, label: str) -> list[float]:
    if (
        type(value) is not list
        or len(value) != 3
        or any(type(item) not in (int, float) or not math.isfinite(float(item)) for item in value)
    ):
        raise ValueError(f"{label} must be a finite [x, y, heading] pose")
    return [float(item) for item in value]


# The route-id and corridor manifests were produced by six independent,
# bounded source projections.  A plan has to match every one, not merely the
# aggregate 1786 count.
_FAMILY_SPECS: tuple[dict[str, Any], ...] = (
    {
        "family_id": "legacy_kashiwanoha_cluster",
        "map_family_ids": ["map_family_d7f16a17d3eb"],
        "record_count": 375,
        "corridor_count": 1,
        "route_ids_sha256": "4ee9cc4adceb9794b698bef33888d79206d90c419d442ccdd80fec7acbfee62a",
        "route_manifest_sha256": "41f542c239d796ed092e914b75285f34c4abde1c67261a19ab2ff27aee9d1e39",
        "corridor_manifest_sha256": "2878a3f0109da771025e66672125256ba02861326d6638519c274b728eb12805",
        "source_strata_counts": {
            "traffic_light": 32,
            "branch_intersection": 345,
            "tight_corridor": 375,
            "short_progress_opportunity": 248,
        },
        "map_sha256s": [
            "088606ec43f52b6881a87b835acf965a3503cb454b944e18d772d8dc8d81ce64",
            "14f3e85c6739c28d3257a4835f0a1dccb076b74931f9ed45ad54817e9522e160",
            "5417803a1627a50e01a2e28dcf6b7516e0f129f13479f7ab3c0211051f0adda5",
            "73009cae81609f97294e59ba1ce3b707861fe75a6e3a2d2266d482704e51c331",
            "91a9126e561783c1dc833e4de84f4d667888cc0466eb5983660cff6c70dd316f",
            "b7f42a10e4fb4478c1c6749ac642cef946f5cfd77841202124f951289f978243",
        ],
        "source_artifact_sha256": FROZEN_ROUTE_CENSUS_SHA256,
        "sidecar": None,
    },
    {
        "family_id": "legacy_simple_cross",
        "map_family_ids": ["map_family_f62e06cd1303"],
        "record_count": 2,
        "corridor_count": 1,
        "route_ids_sha256": "60ca4e7ba367cf6fcf87bd28e4114cb982feadaf8e235fc4912176106cb432a4",
        "route_manifest_sha256": "8c678ae60fc5ea12c507d94a6ac0fcb5e9197fa357e26132c5f83db2ac02d4e1",
        "corridor_manifest_sha256": "bfddb2e2a2da708c36dcacf69c21723c3d52de350eef05fb009b323dc4468f77",
        "source_strata_counts": {
            "traffic_light": 0,
            "branch_intersection": 0,
            "tight_corridor": 2,
            "short_progress_opportunity": 0,
        },
        "map_sha256s": ["1893ae5154af1ee7ee20fcf9e154f86bc2a5debf5980d5621d43e2a9cecfd48c"],
        "source_artifact_sha256": FROZEN_ROUTE_CENSUS_SHA256,
        "sidecar": None,
    },
    {
        "family_id": "nishishinjuku_plus_four_track_highway",
        "map_family_ids": ["nishishinjuku_plus_four_track_highway"],
        "record_count": 770,
        "corridor_count": 15,
        "route_ids_sha256": "3852c2dfcef49d9f0a262d5d9f55861358b65c3f83e04018ef3b4ad4bceceeb9",
        "route_manifest_sha256": "b2943b57f76173966be8181756a67a46c4b416b85d4d3d8e777942193b7637ce",
        "corridor_manifest_sha256": "3520965dbdbfa8ced6eb4b9aebcd7fa19daa4a59fe2ee3c2ba78fc4c47003fc8",
        "source_strata_counts": {
            "traffic_light": 468,
            "branch_intersection": 278,
            "tight_corridor": 763,
            "short_progress_opportunity": 285,
        },
        "map_sha256s": ["95360eeff9945b0512788412485fbf400c249292112e9590488f0d6eb9d99736"],
        "source_artifact_sha256": "595979ec13d65afd6c33ac085dd93eb6496510aeebbc472f6042abc7b53f3fda",
        "sidecar": {
            "index_path": FROZEN_SIDECAR_INDEX_PATH,
            "index_sha256": FROZEN_SIDECAR_INDEX_SHA256,
            "manifest_path": "/root/autodl-tmp/camp_autoware_lanelet2_sidecar_v2_20260727/nishishinjuku.json",
            "manifest_sha256": "621b75e4f78b88a7ec3d9537b4951e8d1a659b4511a6bb0e15842390bb24d160",
            "source_sha256": "595979ec13d65afd6c33ac085dd93eb6496510aeebbc472f6042abc7b53f3fda",
        },
    },
    {
        "family_id": "sample_map_planning",
        "map_family_ids": ["sample_map_planning"],
        "record_count": 156,
        "corridor_count": 2,
        "route_ids_sha256": "03eba4ab4bcb1010292adb584baabfba2686fed1ebb76779acf6739fbfb60e54",
        "route_manifest_sha256": "e53f3e5c65e3bff381bb85337637eef54d9d10875c6857b12dcc2dc0321ae129",
        "corridor_manifest_sha256": "1079f9ea480414d294117c58cbdbbd52617640b053ef2ab4bf905f6d3062a0fe",
        "source_strata_counts": {
            "traffic_light": 69,
            "branch_intersection": 147,
            "tight_corridor": 156,
            "short_progress_opportunity": 88,
        },
        "map_sha256s": ["a81f937c00158324c83688adc5459e90478f5b3c69a51225ad7f965b80d58036"],
        "source_artifact_sha256": "4fe358f2d1e182dc76de296e5619086f8d8ad2fcab3e6d8f99f6e3d724a84e6d",
        "sidecar": {
            "index_path": FROZEN_SIDECAR_INDEX_PATH,
            "index_sha256": FROZEN_SIDECAR_INDEX_SHA256,
            "manifest_path": "/root/autodl-tmp/camp_autoware_lanelet2_sidecar_v2_20260727/sample.json",
            "manifest_sha256": "6b275385749ac806193631c000d75210e2423f0841555da5c913e3f897bca214",
            "source_sha256": "4fe358f2d1e182dc76de296e5619086f8d8ad2fcab3e6d8f99f6e3d724a84e6d",
        },
    },
    {
        "family_id": "autoware_bidirectional_traffic",
        "map_family_ids": ["autoware_bidirectional_traffic"],
        "record_count": 438,
        "corridor_count": 135,
        "route_ids_sha256": "e7c442e3261c48dfa25a68c66ffaa9ab5489f5d4bc3d2347155e6a9e70dd8255",
        "route_manifest_sha256": "daa66ec409a0bf0bf43435d001448d93864b9191bb1391e252c96129c9be65bf",
        "corridor_manifest_sha256": "09e11023fd067c3c34c12540cc1f2d5dc6d5e18c918a4357ea9ceb04f26c9f58",
        "source_strata_counts": {
            "traffic_light": 0,
            "branch_intersection": 75,
            "tight_corridor": 167,
            "short_progress_opportunity": 89,
        },
        "map_sha256s": ["cc636ade751c882cb226762c142bbbefbc977f64ca81a9b76d662e69bd6b91a4"],
        "source_artifact_sha256": "cda848e3d440aaf48e532f8ab33afdff0bf8b8f1a45abd3d7724637a287ed660",
        "sidecar": {
            "index_path": FROZEN_SIDECAR_INDEX_PATH,
            "index_sha256": FROZEN_SIDECAR_INDEX_SHA256,
            "manifest_path": "/root/autodl-tmp/camp_autoware_lanelet2_sidecar_v2_20260727/bidirectional.json",
            "manifest_sha256": "ea3a20fdaa73a89c579141369e77f6393e40572c2ec5a2d223063274fe930826",
            "source_sha256": "cda848e3d440aaf48e532f8ab33afdff0bf8b8f1a45abd3d7724637a287ed660",
        },
    },
    {
        "family_id": "legacy_intersection",
        "map_family_ids": ["legacy_intersection"],
        "record_count": 45,
        "corridor_count": 1,
        "route_ids_sha256": "5c0385ae56495d6ab2dcc31452e72d4c9f587d7797e1507c4ff4b6fd96052244",
        "route_manifest_sha256": "e4df333e0e5a88837c104fd5ffbe1015586911c7a7ad202d81c7e2fd99000a93",
        "corridor_manifest_sha256": "a3843950df12692a5fd34754a85feff7ac7b95ba482a524d4cde67de6cc87df0",
        "source_strata_counts": {
            "traffic_light": 26,
            "branch_intersection": 13,
            "tight_corridor": 45,
            "short_progress_opportunity": 29,
        },
        "map_sha256s": ["64e3f67fe7dae7e73d91731543c5fcf89ae127a99399b843b013d3c17e653229"],
        "source_artifact_sha256": "a0b4fc35116edf5b24a11585b76d4740d375a3935f34fe1b36d34f7cfadce331",
        "sidecar": {
            "index_path": FROZEN_SIDECAR_INDEX_PATH,
            "index_sha256": FROZEN_SIDECAR_INDEX_SHA256,
            "manifest_path": "/root/autodl-tmp/camp_autoware_lanelet2_sidecar_v2_20260727/intersection.json",
            "manifest_sha256": "e9b0b6a011b94ce1a3ce498c6dbb49e40c9f299c85035bd0f91117ab7b61ca04",
            "source_sha256": "a0b4fc35116edf5b24a11585b76d4740d375a3935f34fe1b36d34f7cfadce331",
        },
    },
)


def frozen_family_specs() -> list[dict[str, Any]]:
    """Return a copy of the six audit-bound source-family specifications."""

    result = copy.deepcopy(list(_FAMILY_SPECS))
    for item in result:
        item["event_strata_sha256"] = _event_strata_sha256(item)
    return result


def _event_strata_sha256(spec: Mapping[str, Any]) -> str:
    """Freeze the source-only event strata without any outcome data."""

    return canonical_json_sha256(
        {
            "schema_version": "camp_dp_v26_route_event_strata_manifest_v1",
            "family_id": spec["family_id"],
            "source_artifact_sha256": spec["source_artifact_sha256"],
            "map_sha256s": sorted(spec["map_sha256s"]),
            "source_strata_counts": spec["source_strata_counts"],
        }
    )


def _validate_source_stratum(value: Any) -> dict[str, bool]:
    row = _exact_mapping(
        value,
        {"traffic_light", "branch_intersection", "tight_corridor", "short_progress_opportunity"},
        "V26 route source stratum",
    )
    return {key: _strict_bool(item, f"V26 source stratum.{key}") for key, item in row.items()}


def _validate_route_record(value: Any, spec: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(value)
    required = {
        "record_key",
        "identity_sha256",
        "map_family_id",
        "source_map_path",
        "source_map_sha256",
        "lanelet_ids",
        "source_stratum",
        "holdout_forbidden",
        "route_spec",
        "route_serialization_sha256",
        "source_geometry_sha256",
    }
    missing = required - set(row)
    if missing:
        raise ValueError(f"V26 route record fields are missing: {sorted(missing)}")
    result = {key: copy.deepcopy(row[key]) for key in row}
    result["record_key"] = _strict_string(result["record_key"], "V26 route record key")
    result["identity_sha256"] = _sha256(result["identity_sha256"], "V26 route identity")
    result["map_family_id"] = _strict_string(result["map_family_id"], "V26 route map family")
    if result["map_family_id"] not in spec["map_family_ids"]:
        raise ValueError("V26 route escaped its frozen family")
    result["source_map_path"] = _strict_string(result["source_map_path"], "V26 route map path")
    if "/camp_dp_v25_" in result["source_map_path"] and "training" in result["source_map_path"]:
        raise ValueError("V25 training directories cannot be V26 route-plan inputs")
    result["source_map_sha256"] = _sha256(result["source_map_sha256"], "V26 route map SHA")
    if result["source_map_sha256"] not in spec["map_sha256s"]:
        raise ValueError("V26 route map SHA escaped its frozen family")
    lanelet_ids = result["lanelet_ids"]
    if (
        type(lanelet_ids) is not list
        or not lanelet_ids
        or any(type(item) is not int for item in lanelet_ids)
        or len(set(lanelet_ids)) != len(lanelet_ids)
    ):
        raise ValueError("V26 route lanelet IDs must be a nonempty unique integer list")
    result["lanelet_ids"] = list(lanelet_ids)
    result["source_stratum"] = _validate_source_stratum(result["source_stratum"])
    if result["holdout_forbidden"] is not False:
        raise ValueError("V26 diversified plan rejects holdout-forbidden route records")
    route_spec = _exact_mapping(
        result["route_spec"],
        {"map_path", "lanelet_ids", "start_pose", "goal_pose", "route_length_m"},
        "V26 route spec",
    )
    if route_spec["map_path"] != result["source_map_path"]:
        raise ValueError("V26 route spec map path drifted")
    if route_spec["lanelet_ids"] != result["lanelet_ids"]:
        raise ValueError("V26 route spec lanelet binding drifted")
    route_spec["map_path"] = _strict_string(route_spec["map_path"], "V26 route spec map path")
    route_spec["lanelet_ids"] = list(result["lanelet_ids"])
    route_spec["start_pose"] = _finite_pose(route_spec["start_pose"], "V26 route start pose")
    route_spec["goal_pose"] = _finite_pose(route_spec["goal_pose"], "V26 route goal pose")
    if type(route_spec["route_length_m"]) not in (int, float) or not math.isfinite(
        float(route_spec["route_length_m"])
    ) or float(route_spec["route_length_m"]) <= 0.0:
        raise ValueError("V26 route length must be finite positive")
    route_spec["route_length_m"] = float(route_spec["route_length_m"])
    result["route_spec"] = route_spec
    result["route_serialization_sha256"] = _sha256(
        result["route_serialization_sha256"], "V26 route serialization"
    )
    result["source_geometry_sha256"] = _sha256(
        result["source_geometry_sha256"], "V26 route geometry"
    )
    return result


def _validate_corridor_groups(
    value: Any, records: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]
) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) != int(spec["corridor_count"]):
        raise ValueError("V26 family corridor count drifted")
    expected_keys = {str(record["record_key"]) for record in records}
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in value:
        row = _exact_mapping(
            item,
            {"group_sha256", "route_record_keys"},
            "V26 route corridor group",
        )
        group_sha = _sha256(row["group_sha256"], "V26 corridor group")
        keys = row["route_record_keys"]
        if (
            type(keys) is not list
            or not keys
            or any(type(key) is not str for key in keys)
            or len(set(keys)) != len(keys)
            or not set(keys).issubset(expected_keys)
            or seen.intersection(keys)
        ):
            raise ValueError("V26 corridor groups must be a unique partition of route keys")
        seen.update(keys)
        result.append({"group_sha256": group_sha, "route_record_keys": sorted(keys)})
    if seen != expected_keys or len({row["group_sha256"] for row in result}) != len(result):
        raise ValueError("V26 corridor groups do not cover every route exactly once")
    return sorted(result, key=lambda row: row["group_sha256"])


def _spec_for_family(family_id: str) -> dict[str, Any]:
    for item in _FAMILY_SPECS:
        if item["family_id"] == family_id:
            return copy.deepcopy(item)
    raise ValueError("V26 route family is not part of the fixed six-family design")


def validate_family_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one bounded, zero-model family projection."""

    row = _exact_mapping(
        value,
        {
            "schema_version",
            "family_id",
            "source_kind",
            "fixed_dp_head",
            "holdout_accessed",
            "outcome_fields_consumed",
            "source_bytes_unchanged",
            "source_artifact_sha256",
            "map_sha256s",
            "route_ids_sha256",
            "route_manifest_sha256",
            "corridor_manifest_sha256",
            "event_strata_sha256",
            "materialized_route_records_sha256",
            "materialized_corridor_groups_sha256",
            "route_records",
            "corridor_groups",
        },
        "V26 bounded family projection",
    )
    family_id = _strict_string(row["family_id"], "V26 route family ID")
    spec = _spec_for_family(family_id)
    if (
        row["schema_version"] != FAMILY_PROJECTION_SCHEMA_VERSION
        or row["source_kind"] != "v26_sidecar_and_census_bounded_projection"
        or row["fixed_dp_head"] != FROZEN_FIXED_DP_HEAD
        or row["holdout_accessed"] is not False
        or row["outcome_fields_consumed"] != []
        or row["source_bytes_unchanged"] is not True
    ):
        raise ValueError("V26 bounded family projection identity drifted")
    expected_hashes = {
        "source_artifact_sha256": spec["source_artifact_sha256"],
        "route_ids_sha256": spec["route_ids_sha256"],
        "route_manifest_sha256": spec["route_manifest_sha256"],
        "corridor_manifest_sha256": spec["corridor_manifest_sha256"],
        "event_strata_sha256": _event_strata_sha256(spec),
    }
    for field in (
        "source_artifact_sha256",
        "route_ids_sha256",
        "route_manifest_sha256",
        "corridor_manifest_sha256",
        "event_strata_sha256",
    ):
        row[field] = _sha256(row[field], f"V26 family {field}")
        if row[field] != expected_hashes[field]:
            raise ValueError(f"V26 family {field} does not match its frozen projection")
    map_shas = row["map_sha256s"]
    if (
        type(map_shas) is not list
        or any(type(item) is not str for item in map_shas)
        or sorted(map_shas) != sorted(spec["map_sha256s"])
    ):
        raise ValueError("V26 family map SHA inventory drifted")
    records = row["route_records"]
    if type(records) is not list or len(records) != int(spec["record_count"]):
        raise ValueError("V26 family route count drifted")
    normalized_records = [_validate_route_record(item, spec) for item in records]
    if len({item["record_key"] for item in normalized_records}) != len(normalized_records):
        raise ValueError("V26 family route keys must be unique")
    observed_strata = {
        name: sum(bool(item["source_stratum"][name]) for item in normalized_records)
        for name in (
            "traffic_light",
            "branch_intersection",
            "tight_corridor",
            "short_progress_opportunity",
        )
    }
    if observed_strata != spec["source_strata_counts"]:
        raise ValueError("V26 family event-strata identity drifted")
    groups = _validate_corridor_groups(row["corridor_groups"], normalized_records, spec)
    records_sha = _sha256(
        row["materialized_route_records_sha256"], "V26 materialized family routes"
    )
    groups_sha = _sha256(
        row["materialized_corridor_groups_sha256"], "V26 materialized family corridors"
    )
    if records_sha != canonical_json_sha256(
        sorted(normalized_records, key=lambda item: item["record_key"])
    ) or groups_sha != canonical_json_sha256(groups):
        raise ValueError("V26 bounded family materialized-record hash drifted")
    return {
        "schema_version": FAMILY_PROJECTION_SCHEMA_VERSION,
        "family_id": family_id,
        "source_kind": "v26_sidecar_and_census_bounded_projection",
        "fixed_dp_head": FROZEN_FIXED_DP_HEAD,
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "source_bytes_unchanged": True,
        "source_artifact_sha256": row["source_artifact_sha256"],
        "map_sha256s": sorted(map_shas),
        "route_ids_sha256": row["route_ids_sha256"],
        "route_manifest_sha256": row["route_manifest_sha256"],
        "corridor_manifest_sha256": row["corridor_manifest_sha256"],
        "event_strata_sha256": row["event_strata_sha256"],
        "materialized_route_records_sha256": records_sha,
        "materialized_corridor_groups_sha256": groups_sha,
        "route_records": sorted(normalized_records, key=lambda item: item["record_key"]),
        "corridor_groups": groups,
    }


def _projection_summary(projection: Mapping[str, Any]) -> dict[str, Any]:
    spec = _spec_for_family(str(projection["family_id"]))
    return {
        "family_id": projection["family_id"],
        "map_family_ids": list(spec["map_family_ids"]),
        "record_count": len(projection["route_records"]),
        "corridor_count": len(projection["corridor_groups"]),
        "route_ids_sha256": projection["route_ids_sha256"],
        "route_manifest_sha256": projection["route_manifest_sha256"],
        "corridor_manifest_sha256": projection["corridor_manifest_sha256"],
        "event_strata_sha256": projection["event_strata_sha256"],
        "materialized_route_records_sha256": projection["materialized_route_records_sha256"],
        "materialized_corridor_groups_sha256": projection["materialized_corridor_groups_sha256"],
        "source_strata_counts": copy.deepcopy(spec["source_strata_counts"]),
        "map_sha256s": list(projection["map_sha256s"]),
        "source_artifact_sha256": projection["source_artifact_sha256"],
        "sidecar": copy.deepcopy(spec["sidecar"]),
    }


def _schedule_rows(projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    family_id = str(projection["family_id"])
    group_by_route = {
        key: str(group["group_sha256"])
        for group in projection["corridor_groups"]
        for key in group["route_record_keys"]
    }
    return [
        {
            "family_id": family_id,
            "route_id": str(record["record_key"]),
            "corridor_id": group_by_route[str(record["record_key"])],
            "route_record": copy.deepcopy(record),
            "source_artifact_sha256": str(projection["source_artifact_sha256"]),
            "event_manifest_sha256": str(projection["event_strata_sha256"]),
        }
        for record in projection["route_records"]
    ]


def _plan_hash_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": value["schema_version"],
        "evidence_role": value["evidence_role"],
        "fixed_dp_head": value["fixed_dp_head"],
        "split": value["split"],
        "holdout_accessed": value["holdout_accessed"],
        "outcome_fields_consumed": value["outcome_fields_consumed"],
        "family_projections": value["family_projections"],
        "routes": value["routes"],
        "denominator": value["denominator"],
    }


def build_diversified_route_plan(
    projections: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Merge six independent projections only if every frozen identity agrees."""

    if type(projections) not in (list, tuple) or len(projections) != len(_FAMILY_SPECS):
        raise ValueError("V26 route plan requires exactly six bounded family projections")
    normalized = [validate_family_projection(item) for item in projections]
    normalized.sort(key=lambda item: str(item["family_id"]))
    expected_ids = sorted(item["family_id"] for item in _FAMILY_SPECS)
    if [item["family_id"] for item in normalized] != expected_ids:
        raise ValueError("V26 route plan family inventory drifted")
    routes = [row for projection in normalized for row in _schedule_rows(projection)]
    routes.sort(key=lambda row: (row["family_id"], row["route_id"]))
    if len(routes) != 1786 or len({row["route_id"] for row in routes}) != len(routes):
        raise ValueError("V26 route plan must retain the exact 1786 unique routes")
    corridors = {row["corridor_id"] for row in routes}
    if len(corridors) != 155:
        raise ValueError("V26 route plan must retain the exact 155 independent corridors")
    payload: dict[str, Any] = {
        "schema_version": ROUTE_PLAN_SCHEMA_VERSION,
        "evidence_role": ROUTE_PLAN_EVIDENCE_ROLE,
        "fixed_dp_head": FROZEN_FIXED_DP_HEAD,
        "split": "development_nonholdout",
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "family_projections": [_projection_summary(item) for item in normalized],
        "routes": routes,
        "denominator": {
            "planned": 1786,
            "complete": 0,
            "failed": 0,
            "unattempted": 1786,
        },
    }
    payload["route_plan_sha256"] = canonical_json_sha256(_plan_hash_payload(payload))
    return validate_diversified_route_plan(payload)


def validate_diversified_route_plan(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the finished plan before any model or fixed-DP import."""

    row = _exact_mapping(
        value,
        {
            "schema_version",
            "evidence_role",
            "fixed_dp_head",
            "split",
            "holdout_accessed",
            "outcome_fields_consumed",
            "family_projections",
            "routes",
            "denominator",
            "route_plan_sha256",
        },
        "V26 diversified route plan",
    )
    if (
        row["schema_version"] != ROUTE_PLAN_SCHEMA_VERSION
        or row["evidence_role"] != ROUTE_PLAN_EVIDENCE_ROLE
        or row["fixed_dp_head"] != FROZEN_FIXED_DP_HEAD
        or row["split"] != "development_nonholdout"
        or row["holdout_accessed"] is not False
        or row["outcome_fields_consumed"] != []
    ):
        raise ValueError("V26 diversified route plan identity drifted")
    projection_summaries = row["family_projections"]
    if type(projection_summaries) is not list or len(projection_summaries) != len(_FAMILY_SPECS):
        raise ValueError("V26 diversified route plan projection summary drifted")
    expected_summaries = {
        item["family_id"]: _projection_summary(
            {
                "family_id": item["family_id"],
                "route_records": [None] * int(item["record_count"]),
                "corridor_groups": [None] * int(item["corridor_count"]),
                "route_ids_sha256": item["route_ids_sha256"],
                "route_manifest_sha256": item["route_manifest_sha256"],
                "corridor_manifest_sha256": item["corridor_manifest_sha256"],
                "event_strata_sha256": _event_strata_sha256(item),
                "materialized_route_records_sha256": "0" * 64,
                "materialized_corridor_groups_sha256": "0" * 64,
                "map_sha256s": item["map_sha256s"],
                "source_artifact_sha256": item["source_artifact_sha256"],
            }
        )
        for item in _FAMILY_SPECS
    }
    actual_summaries: dict[str, dict[str, Any]] = {}
    for item in projection_summaries:
        if type(item) is not dict or type(item.get("family_id")) is not str:
            raise ValueError("V26 diversified projection summary is malformed")
        family_id = str(item["family_id"])
        if family_id in actual_summaries or family_id not in expected_summaries:
            raise ValueError("V26 diversified projection summary family drifted")
        actual_summaries[family_id] = dict(item)
    for family_id, actual in actual_summaries.items():
        expected = dict(expected_summaries[family_id])
        actual_records_sha = _sha256(
            actual.pop("materialized_route_records_sha256", None),
            "V26 summarized materialized family routes",
        )
        actual_groups_sha = _sha256(
            actual.pop("materialized_corridor_groups_sha256", None),
            "V26 summarized materialized family corridors",
        )
        expected.pop("materialized_route_records_sha256")
        expected.pop("materialized_corridor_groups_sha256")
        if actual != expected:
            raise ValueError("V26 diversified projection summary does not match frozen provenance")
        actual["materialized_route_records_sha256"] = actual_records_sha
        actual["materialized_corridor_groups_sha256"] = actual_groups_sha
    routes = row["routes"]
    if type(routes) is not list or len(routes) != 1786:
        raise ValueError("V26 diversified route plan count drifted")
    seen_route_ids: set[str] = set()
    seen_corridors: set[str] = set()
    normalized_routes: list[dict[str, Any]] = []
    family_route_counts = {item["family_id"]: 0 for item in _FAMILY_SPECS}
    for item in routes:
        route = _exact_mapping(
            item,
            {
                "family_id",
                "route_id",
                "corridor_id",
                "route_record",
                "source_artifact_sha256",
                "event_manifest_sha256",
            },
            "V26 diversified planned route",
        )
        family_id = _strict_string(route["family_id"], "V26 planned route family")
        spec = _spec_for_family(family_id)
        route_id = _strict_string(route["route_id"], "V26 planned route ID")
        corridor_id = _sha256(route["corridor_id"], "V26 planned corridor ID")
        record = _validate_route_record(route["route_record"], spec)
        if route_id != record["record_key"] or route_id in seen_route_ids:
            raise ValueError("V26 planned route ID binding drifted")
        if route["source_artifact_sha256"] != spec["source_artifact_sha256"]:
            raise ValueError("V26 planned route source artifact drifted")
        if route["event_manifest_sha256"] != _event_strata_sha256(spec):
            raise ValueError("V26 planned route event manifest drifted")
        seen_route_ids.add(route_id)
        seen_corridors.add(corridor_id)
        family_route_counts[family_id] += 1
        normalized_routes.append(
            {
                "family_id": family_id,
                "route_id": route_id,
                "corridor_id": corridor_id,
                "route_record": record,
                "source_artifact_sha256": str(route["source_artifact_sha256"]),
                "event_manifest_sha256": str(route["event_manifest_sha256"]),
            }
        )
    if len(seen_corridors) != 155 or family_route_counts != {
        item["family_id"]: int(item["record_count"]) for item in _FAMILY_SPECS
    }:
        raise ValueError("V26 diversified route/corridor denominator drifted")
    for family_id, summary in actual_summaries.items():
        family_routes = [
            item["route_record"] for item in normalized_routes if item["family_id"] == family_id
        ]
        reconstructed_groups: dict[str, list[str]] = {}
        for item in normalized_routes:
            if item["family_id"] == family_id:
                reconstructed_groups.setdefault(item["corridor_id"], []).append(item["route_id"])
        groups = sorted(
            [
                {"group_sha256": group_sha, "route_record_keys": sorted(keys)}
                for group_sha, keys in reconstructed_groups.items()
            ],
            key=lambda item: item["group_sha256"],
        )
        if (
            summary["materialized_route_records_sha256"]
            != canonical_json_sha256(sorted(family_routes, key=lambda item: item["record_key"]))
            or summary["materialized_corridor_groups_sha256"] != canonical_json_sha256(groups)
        ):
            raise ValueError("V26 diversified plan materialized family provenance drifted")
    denominator = _exact_mapping(
        row["denominator"], {"planned", "complete", "failed", "unattempted"}, "V26 route plan denominator"
    )
    if denominator != {"planned": 1786, "complete": 0, "failed": 0, "unattempted": 1786}:
        raise ValueError("V26 route plan must remain pre-execution")
    result = {
        "schema_version": ROUTE_PLAN_SCHEMA_VERSION,
        "evidence_role": ROUTE_PLAN_EVIDENCE_ROLE,
        "fixed_dp_head": FROZEN_FIXED_DP_HEAD,
        "split": "development_nonholdout",
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "family_projections": [actual_summaries[key] for key in sorted(actual_summaries)],
        "routes": sorted(normalized_routes, key=lambda item: (item["family_id"], item["route_id"])),
        "denominator": {key: int(value) for key, value in denominator.items()},
    }
    route_plan_sha = _sha256(row["route_plan_sha256"], "V26 route plan SHA")
    if route_plan_sha != canonical_json_sha256(_plan_hash_payload(result)):
        raise ValueError("V26 diversified route plan SHA drifted")
    result["route_plan_sha256"] = route_plan_sha
    return result
