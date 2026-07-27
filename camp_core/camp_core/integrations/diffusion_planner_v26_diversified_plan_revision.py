"""Forward-only Stage 8b route-plan revisions from immutable qualification evidence.

This module is intentionally zero-model: it only reads the frozen 1786-route
plan and its atomically written pre-model qualification units, then constructs
the explicitly authorized 1783-route successor plan.  It cannot repair a map,
infer a stop line, reorder routes, or select an alternate route.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from camp_core.integrations.diffusion_planner_v26_diversified_route_plan import (
    FROZEN_FIXED_DP_HEAD,
    canonical_json_sha256,
    validate_diversified_route_plan,
)


PLAN_REVISION_SCHEMA_VERSION = "camp_dp_v26_diversified_route_plan_revision_v1"
PLAN_REVISION_EVIDENCE_ROLE = "development_nonholdout_diversified_training_route_plan_revision"
PLAN_REVISION_REVIEW_SCHEMA_VERSION = "camp_dp_v26_diversified_route_plan_revision_review_v1"
PLAN_REVISION_REVIEW_EVIDENCE_ROLE = (
    "development_nonholdout_diversified_training_route_plan_revision_review"
)
PLAN_REVISION_MANIFEST_SCHEMA_VERSION = "camp_dp_v26_diversified_route_plan_revision_manifest_v1"
PLAN_REVISION_ID = "lanelet423_upstream_map_missing_ref_line_exclusion_v1"

ORIGINAL_PLAN_SHA256 = "83aca15f323c97dab396952be5a7f40d95585e919c744b72f10f67e692d06b20"
ORIGINAL_DENOMINATOR = {"planned": 1786, "complete": 0, "failed": 0, "unattempted": 1786}
ORIGINAL_QUALIFICATION_DENOMINATOR = {
    "planned": 1786,
    "complete": 1783,
    "failed": 3,
    "unattempted": 0,
}
REVISED_DENOMINATOR = {"planned": 1783, "complete": 0, "failed": 0, "unattempted": 1783}
ZERO_MODEL_CALLS = {
    "model_forward_count": 0,
    "dp_forward_count": 0,
    "gpu_invocation_count": 0,
    "latent_generation_count": 0,
    "candidate_generation_count": 0,
    "sequential_forward_count": 0,
}
UPSTREAM_FAILURE_REASON = "V26 sidecar traffic light has no unique stop line"
UPSTREAM_SOURCE_QUALITY_FINDING = "upstream_map_missing_ref_line"

# This is the explicit scientific-design decision.  The route identities make
# an ordinal-only edit impossible; all fields are rechecked against the parent
# plan and immutable qualification units before a successor plan is emitted.
EXCLUSION_SPECS: dict[int, dict[str, Any]] = {
    1185: {
        "route_id": "nishishinjuku_plus_four_track_highway/95360eeff9945b05/3002114/e781fcfb9b47338f",
        "route_identity_sha256": "e781fcfb9b47338fa177f2227b81c6b0f03a6d346b922a39e20d5903de43ac8d",
        "corridor_id": "731da17235e5152569dcc61f603609021ac7c978a7b79abac1e47e07c2dd7692",
        "route_lanelet_ids": [3002114, 3002116, 423],
    },
    1187: {
        "route_id": "nishishinjuku_plus_four_track_highway/95360eeff9945b05/3002116/56bb9716bf8d5adb",
        "route_identity_sha256": "56bb9716bf8d5adbd13056044e1d4b0f69161c4b19c83f70f67495ef493f649c",
        "corridor_id": "731da17235e5152569dcc61f603609021ac7c978a7b79abac1e47e07c2dd7692",
        "route_lanelet_ids": [3002116, 423, 49],
    },
    1454: {
        "route_id": "nishishinjuku_plus_four_track_highway/95360eeff9945b05/423/41d19e594d6adf50",
        "route_identity_sha256": "41d19e594d6adf50f69e1c3c114a61d1a13692e09066b14cbf22133973ed6ff4",
        "corridor_id": "731da17235e5152569dcc61f603609021ac7c978a7b79abac1e47e07c2dd7692",
        "route_lanelet_ids": [423, 49, 54],
    },
}
COMMON_LANELET_ID = 423
COMMON_REGULATORY_ELEMENT_ID = 1391
_SHA_CHARS = frozenset("0123456789abcdef")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or set(value) - _SHA_CHARS:
        raise ValueError(f"{label} must be a lowercase SHA256")
    return value


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        staging.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)


def _exact_mapping(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise ValueError(f"{label} field set drifted")
    return dict(value)


def _strict_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be bool")
    return value


def _strict_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return value


def _strict_string(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _revision_hash_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": value["schema_version"],
        "evidence_role": value["evidence_role"],
        "fixed_dp_head": value["fixed_dp_head"],
        "split": value["split"],
        "holdout_accessed": value["holdout_accessed"],
        "outcome_fields_consumed": value["outcome_fields_consumed"],
        "parent_plan": value["parent_plan"],
        "revision": value["revision"],
        "family_projections": value["family_projections"],
        "routes": value["routes"],
        "identity": value["identity"],
        "denominator": value["denominator"],
    }


def _expected_exclusion_rows(parent_plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    routes = list(parent_plan["routes"])
    for ordinal, spec in sorted(EXCLUSION_SPECS.items()):
        schedule = dict(routes[ordinal])
        record = dict(schedule["route_record"])
        if (
            schedule.get("family_id") != "nishishinjuku_plus_four_track_highway"
            or schedule.get("route_id") != spec["route_id"]
            or schedule.get("corridor_id") != spec["corridor_id"]
            or record.get("identity_sha256") != spec["route_identity_sha256"]
            or record.get("lanelet_ids") != spec["route_lanelet_ids"]
            or COMMON_LANELET_ID not in record.get("lanelet_ids", [])
        ):
            raise ValueError("V26 Stage8b exclusion route identity drifted")
        rows.append(
            {
                "parent_ordinal": ordinal,
                "route_id": spec["route_id"],
                "route_identity_sha256": spec["route_identity_sha256"],
                "corridor_id": spec["corridor_id"],
                "route_lanelet_ids": list(spec["route_lanelet_ids"]),
                "common_lanelet_id": COMMON_LANELET_ID,
                "regulatory_element_id": COMMON_REGULATORY_ELEMENT_ID,
                "failure_class": "ValueError",
                "failure_reason": UPSTREAM_FAILURE_REASON,
                "source_quality_finding": UPSTREAM_SOURCE_QUALITY_FINDING,
            }
        )
    return rows


def _verify_unit_route(unit: Mapping[str, Any], schedule: Mapping[str, Any], ordinal: int) -> None:
    route = dict(unit.get("route", {}))
    record = dict(schedule["route_record"])
    if (
        unit.get("unit_index") != ordinal
        or route.get("route_id") != schedule["route_id"]
        or route.get("corridor_id") != schedule["corridor_id"]
        or route.get("route_identity_sha256") != record["identity_sha256"]
        or route.get("source_map_sha256") != record["source_map_sha256"]
        or route.get("route_lanelet_ids") != record["lanelet_ids"]
        or unit.get("forward_calls") != ZERO_MODEL_CALLS
    ):
        raise ValueError("V26 Stage8b immutable qualification unit route binding drifted")


def _verify_common_upstream_gap(parent_plan: Mapping[str, Any]) -> dict[str, Any]:
    family = next(
        (
            item
            for item in parent_plan["family_projections"]
            if item.get("family_id") == "nishishinjuku_plus_four_track_highway"
        ),
        None,
    )
    if type(family) is not dict or type(family.get("sidecar")) is not dict:
        raise ValueError("V26 Stage8b Nishi sidecar provenance is missing")
    sidecar = dict(family["sidecar"])
    path = Path(_strict_string(sidecar.get("manifest_path"), "V26 Stage8b Nishi sidecar path"))
    expected_sha = _sha256(sidecar.get("manifest_sha256"), "V26 Stage8b Nishi sidecar SHA")
    if not path.is_file() or _file_sha256(path) != expected_sha:
        raise ValueError("V26 Stage8b Nishi sidecar manifest drifted")
    payload = json.loads(path.read_text(encoding="utf-8"))
    lanelets = {int(item["id"]): item for item in payload.get("lanelets", [])}
    regulations = {int(item["id"]): item for item in payload.get("regulatory_elements", [])}
    lanelet = lanelets.get(COMMON_LANELET_ID)
    regulation = regulations.get(COMMON_REGULATORY_ELEMENT_ID)
    if type(lanelet) is not dict or type(regulation) is not dict:
        raise ValueError("V26 Stage8b common Nishi signal authority is missing")
    if COMMON_REGULATORY_ELEMENT_ID not in lanelet.get("regulatory_element_ids", []):
        raise ValueError("V26 Stage8b lanelet423 regulatory binding drifted")
    roles = [str(item.get("role")) for item in regulation.get("roles", [])]
    if regulation.get("runtime_type") != "AutowareTrafficLight" or "ref_line" in roles:
        raise ValueError("V26 Stage8b upstream missing-ref-line finding drifted")
    if sorted(roles) != ["light_bulbs", "refers"]:
        raise ValueError("V26 Stage8b common traffic-light roles are not the reviewed upstream gap")
    return {
        "sidecar_manifest_path": str(path),
        "sidecar_manifest_sha256": expected_sha,
        "lanelet_id": COMMON_LANELET_ID,
        "regulatory_element_id": COMMON_REGULATORY_ELEMENT_ID,
        "runtime_type": "AutowareTrafficLight",
        "roles": sorted(roles),
        "source_quality_finding": UPSTREAM_SOURCE_QUALITY_FINDING,
    }


def load_immutable_qualification(
    *, parent_plan: Mapping[str, Any], qualification_receipt_path: Path
) -> dict[str, Any]:
    """Read and verify the existing failed 1786-unit qualification evidence.

    This is an evidence projection, not a rerun.  Every included source ordinal
    must already have a successful zero-model terminal receipt.
    """

    receipt_path = qualification_receipt_path.resolve()
    root = receipt_path.parent
    if not receipt_path.is_file():
        raise FileNotFoundError(receipt_path)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("V26 Stage8b original qualification manifest is missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        receipt.get("schema_version")
        != "camp_dp_v26_stage8b_pre_model_qualification_receipt_v1"
        or receipt.get("evidence_role")
        != "development_training_same_ego_b8_pre_model_qualification"
        or receipt.get("status") != "failed"
        or receipt.get("route_plan_sha256") != parent_plan["route_plan_sha256"]
        or receipt.get("denominator") != ORIGINAL_QUALIFICATION_DENOMINATOR
        or receipt.get("identity") != {"family_count": 6, "corridor_count": 155, "route_count": 1786}
        or receipt.get("zero_model_totals") != ZERO_MODEL_CALLS
        or receipt.get("acquisition_authorized") is not False
        or manifest.get("route_plan_sha256") != parent_plan["route_plan_sha256"]
        or manifest.get("fixed_dp_head") != FROZEN_FIXED_DP_HEAD
        or receipt.get("manifest_sha256") != canonical_json_sha256(manifest)
    ):
        raise ValueError("V26 Stage8b original qualification evidence is not admissible")
    expected_names = {f"{index:04d}.json" for index in range(len(parent_plan["routes"]))}
    unit_dir = root / "units"
    if not unit_dir.is_dir() or {item.name for item in unit_dir.glob("*.json")} != expected_names:
        raise ValueError("V26 Stage8b original qualification unit inventory drifted")
    units: dict[int, dict[str, Any]] = {}
    unit_sha256: dict[str, str] = {}
    excluded = set(EXCLUSION_SPECS)
    failures: set[int] = set()
    for ordinal, schedule in enumerate(parent_plan["routes"]):
        unit_path = unit_dir / f"{ordinal:04d}.json"
        unit = json.loads(unit_path.read_text(encoding="utf-8"))
        _verify_unit_route(unit, schedule, ordinal)
        status = unit.get("terminal", {}).get("status")
        if ordinal in excluded:
            spec = EXCLUSION_SPECS[ordinal]
            if (
                status != "failed"
                or unit.get("terminal", {}).get("failure_class") != "ValueError"
                or unit.get("terminal", {}).get("failure_reason") != UPSTREAM_FAILURE_REASON
                or dict(unit["route"]).get("lanelet_ids", unit["route"].get("route_lanelet_ids"))
                != spec["route_lanelet_ids"]
            ):
                raise ValueError("V26 Stage8b exclusion is not the reviewed upstream missing-ref-line group")
            failures.add(ordinal)
        else:
            if (
                status != "qualified"
                or not isinstance(unit.get("source_projection"), dict)
                or not isinstance(unit.get("parsed_geometry"), dict)
                or not isinstance(unit.get("signal"), dict)
                or not isinstance(unit.get("scene14d_reference"), dict)
                or not isinstance(unit.get("generator_topology"), dict)
            ):
                raise ValueError("V26 Stage8b included parent ordinal was not qualified")
        units[ordinal] = unit
        unit_sha256[str(ordinal)] = _file_sha256(unit_path)
    if failures != excluded:
        raise ValueError("V26 Stage8b original qualification failed-ordinal inventory drifted")
    return {
        "root": str(root),
        "receipt_path": str(receipt_path),
        "receipt_sha256": _file_sha256(receipt_path),
        "manifest_path": str(manifest_path),
        "manifest_sha256": _file_sha256(manifest_path),
        "camp_head": _strict_string(manifest.get("camp_head"), "V26 Stage8b original qualification CAMP head"),
        "units": units,
        "unit_sha256": unit_sha256,
    }


def _source_strata_counts(routes: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    names = ("traffic_light", "branch_intersection", "tight_corridor", "short_progress_opportunity")
    return {
        name: sum(bool(dict(item["route_record"])["source_stratum"][name]) for item in routes)
        for name in names
    }


def build_revised_plan(
    *,
    parent_plan: Mapping[str, Any],
    parent_plan_file_sha256: str,
    qualification: Mapping[str, Any],
    source_quality: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive the only permitted successor plan from immutable source units."""

    parent = validate_diversified_route_plan(parent_plan)
    if parent["route_plan_sha256"] != ORIGINAL_PLAN_SHA256 or parent["denominator"] != ORIGINAL_DENOMINATOR:
        raise ValueError("V26 Stage8b parent plan is not the frozen 1786-route plan")
    parent_file_sha = _sha256(parent_plan_file_sha256, "V26 Stage8b parent plan file SHA")
    exclusions = _expected_exclusion_rows(parent)
    excluded_ordinals = [item["parent_ordinal"] for item in exclusions]
    units = dict(qualification["units"])
    if set(units) != set(range(1786)):
        raise ValueError("V26 Stage8b original qualification units are incomplete")
    included_ordinals = [index for index in range(1786) if index not in set(excluded_ordinals)]
    if any(units[index]["terminal"]["status"] != "qualified" for index in included_ordinals):
        raise ValueError("V26 Stage8b successor includes a non-qualified parent unit")
    routes = [
        {**copy.deepcopy(parent["routes"][ordinal]), "parent_ordinal": ordinal}
        for ordinal in included_ordinals
    ]
    if [item["parent_ordinal"] for item in routes] != included_ordinals:
        raise ValueError("V26 Stage8b successor route order drifted")
    parent_corridors = {item["corridor_id"] for item in parent["routes"]}
    revised_corridors = {item["corridor_id"] for item in routes}
    if parent_corridors != revised_corridors or len(revised_corridors) != 155:
        raise ValueError("V26 Stage8b exclusion changed a corridor inventory")
    parent_strata = _source_strata_counts(parent["routes"])
    revised_strata = _source_strata_counts(routes)
    excluded_strata = _source_strata_counts([parent["routes"][index] for index in excluded_ordinals])
    if revised_strata != {
        key: parent_strata[key] - excluded_strata[key] for key in parent_strata
    }:
        raise ValueError("V26 Stage8b successor changed source strata beyond the exclusions")
    family_counts = {
        family_id: sum(route["family_id"] == family_id for route in routes)
        for family_id in sorted({route["family_id"] for route in parent["routes"]})
    }
    revision = {
        "revision_id": PLAN_REVISION_ID,
        "basis": "explicit_user_scientific_design_decision",
        "pre_model_only": True,
        "zero_outcome": True,
        "not_result_driven": True,
        "excluded_parent_ordinals": excluded_ordinals,
        "exclusions": exclusions,
        "source_quality": dict(source_quality),
    }
    result: dict[str, Any] = {
        "schema_version": PLAN_REVISION_SCHEMA_VERSION,
        "evidence_role": PLAN_REVISION_EVIDENCE_ROLE,
        "fixed_dp_head": FROZEN_FIXED_DP_HEAD,
        "split": "development_nonholdout",
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "parent_plan": {
            "route_plan_sha256": parent["route_plan_sha256"],
            "file_sha256": parent_file_sha,
            "denominator": copy.deepcopy(parent["denominator"]),
        },
        "revision": revision,
        "family_projections": copy.deepcopy(parent["family_projections"]),
        "routes": routes,
        "identity": {
            "family_count": 6,
            "corridor_count": 155,
            "route_count": len(routes),
            "family_route_counts": family_counts,
            "source_strata_counts": revised_strata,
        },
        "denominator": copy.deepcopy(REVISED_DENOMINATOR),
    }
    result["route_plan_sha256"] = canonical_json_sha256(_revision_hash_payload(result))
    result = validate_revised_plan(result, parent_plan=parent)
    included_unit_sha256 = {
        str(index): str(qualification["unit_sha256"][str(index)]) for index in included_ordinals
    }
    review = {
        "schema_version": PLAN_REVISION_REVIEW_SCHEMA_VERSION,
        "evidence_role": PLAN_REVISION_REVIEW_EVIDENCE_ROLE,
        "status": "passed",
        "original_plan": {
            "route_plan_sha256": parent["route_plan_sha256"],
            "file_sha256": parent_file_sha,
            "denominator": copy.deepcopy(parent["denominator"]),
        },
        "original_qualification": {
            "root": str(qualification["root"]),
            "receipt_path": str(qualification["receipt_path"]),
            "receipt_sha256": str(qualification["receipt_sha256"]),
            "manifest_path": str(qualification["manifest_path"]),
            "manifest_sha256": str(qualification["manifest_sha256"]),
            "camp_head": str(qualification["camp_head"]),
            "denominator": copy.deepcopy(ORIGINAL_QUALIFICATION_DENOMINATOR),
            "zero_model_totals": copy.deepcopy(ZERO_MODEL_CALLS),
        },
        "revision": copy.deepcopy(revision),
        "included": {
            "count": len(included_ordinals),
            "parent_ordinals_sha256": canonical_json_sha256(included_ordinals),
            "route_identities_sha256": canonical_json_sha256(
                [
                    {
                        "parent_ordinal": index,
                        "route_id": parent["routes"][index]["route_id"],
                        "route_identity_sha256": parent["routes"][index]["route_record"]["identity_sha256"],
                        "corridor_id": parent["routes"][index]["corridor_id"],
                        "source_stratum": parent["routes"][index]["route_record"]["source_stratum"],
                    }
                    for index in included_ordinals
                ]
            ),
            "unit_file_sha256_by_parent_ordinal": included_unit_sha256,
        },
        "assertions": {
            "all_included_parent_ordinals_qualified": True,
            "excluded_ordinals_are_exact_typed_upstream_missing_ref_line_group": True,
            "route_order_preserved": True,
            "route_identity_preserved": True,
            "corridor_inventory_preserved": True,
            "source_strata_only_changed_by_exclusions": True,
            "pre_model": True,
            "zero_outcome": True,
            "not_result_driven": True,
        },
        "new_plan": {
            "route_plan_sha256": result["route_plan_sha256"],
            "denominator": copy.deepcopy(result["denominator"]),
            "identity": copy.deepcopy(result["identity"]),
            "file_sha256": None,
        },
    }
    return result, review


def validate_revised_plan(value: Mapping[str, Any], *, parent_plan: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed unless a successor is exactly the allowed 1783-route subset."""

    parent = validate_diversified_route_plan(parent_plan)
    row = _exact_mapping(
        value,
        {
            "schema_version",
            "evidence_role",
            "fixed_dp_head",
            "split",
            "holdout_accessed",
            "outcome_fields_consumed",
            "parent_plan",
            "revision",
            "family_projections",
            "routes",
            "identity",
            "denominator",
            "route_plan_sha256",
        },
        "V26 Stage8b revised route plan",
    )
    if (
        row["schema_version"] != PLAN_REVISION_SCHEMA_VERSION
        or row["evidence_role"] != PLAN_REVISION_EVIDENCE_ROLE
        or row["fixed_dp_head"] != FROZEN_FIXED_DP_HEAD
        or row["split"] != "development_nonholdout"
        or row["holdout_accessed"] is not False
        or row["outcome_fields_consumed"] != []
    ):
        raise ValueError("V26 Stage8b revised plan identity drifted")
    parent_binding = _exact_mapping(
        row["parent_plan"], {"route_plan_sha256", "file_sha256", "denominator"}, "V26 Stage8b parent-plan binding"
    )
    if (
        parent_binding["route_plan_sha256"] != parent["route_plan_sha256"]
        or _sha256(parent_binding["file_sha256"], "V26 Stage8b parent plan file SHA")
        != parent_binding["file_sha256"]
        or parent_binding["denominator"] != ORIGINAL_DENOMINATOR
    ):
        raise ValueError("V26 Stage8b revised plan parent binding drifted")
    if row["family_projections"] != parent["family_projections"]:
        raise ValueError("V26 Stage8b revised plan changed family provenance")
    expected_exclusions = _expected_exclusion_rows(parent)
    expected_ordinals = [item["parent_ordinal"] for item in expected_exclusions]
    revision = _exact_mapping(
        row["revision"],
        {
            "revision_id",
            "basis",
            "pre_model_only",
            "zero_outcome",
            "not_result_driven",
            "excluded_parent_ordinals",
            "exclusions",
            "source_quality",
        },
        "V26 Stage8b revision declaration",
    )
    if (
        revision["revision_id"] != PLAN_REVISION_ID
        or revision["basis"] != "explicit_user_scientific_design_decision"
        or _strict_bool(revision["pre_model_only"], "V26 revision pre-model flag") is not True
        or _strict_bool(revision["zero_outcome"], "V26 revision zero-outcome flag") is not True
        or _strict_bool(revision["not_result_driven"], "V26 revision no-result flag") is not True
        or revision["excluded_parent_ordinals"] != expected_ordinals
        or revision["exclusions"] != expected_exclusions
    ):
        raise ValueError("V26 Stage8b revised plan exclusion declaration drifted")
    source_quality = dict(revision["source_quality"])
    if (
        source_quality.get("lanelet_id") != COMMON_LANELET_ID
        or source_quality.get("regulatory_element_id") != COMMON_REGULATORY_ELEMENT_ID
        or source_quality.get("source_quality_finding") != UPSTREAM_SOURCE_QUALITY_FINDING
        or source_quality.get("runtime_type") != "AutowareTrafficLight"
        or source_quality.get("roles") != ["light_bulbs", "refers"]
        or _sha256(source_quality.get("sidecar_manifest_sha256"), "V26 Stage8b revision sidecar SHA")
        != source_quality.get("sidecar_manifest_sha256")
        or not isinstance(source_quality.get("sidecar_manifest_path"), str)
    ):
        raise ValueError("V26 Stage8b revised plan source-quality binding drifted")
    routes = row["routes"]
    expected_ordinals_included = [index for index in range(1786) if index not in set(expected_ordinals)]
    if type(routes) is not list or len(routes) != len(expected_ordinals_included):
        raise ValueError("V26 Stage8b revised plan route denominator drifted")
    normalized_routes: list[dict[str, Any]] = []
    for position, (item, parent_ordinal) in enumerate(zip(routes, expected_ordinals_included, strict=True)):
        if type(item) is not dict or set(item) != {
            "family_id", "route_id", "corridor_id", "route_record", "source_artifact_sha256", "event_manifest_sha256", "parent_ordinal"
        }:
            raise ValueError("V26 Stage8b revised planned-route fields drifted")
        if item["parent_ordinal"] != parent_ordinal or item != {
            **parent["routes"][parent_ordinal],
            "parent_ordinal": parent_ordinal,
        }:
            raise ValueError(f"V26 Stage8b revised route {position} was reordered or substituted")
        normalized_routes.append(copy.deepcopy(item))
    if row["denominator"] != REVISED_DENOMINATOR:
        raise ValueError("V26 Stage8b revised plan denominator drifted")
    identity = _exact_mapping(
        row["identity"],
        {"family_count", "corridor_count", "route_count", "family_route_counts", "source_strata_counts"},
        "V26 Stage8b revised plan identity",
    )
    expected_identity = {
        "family_count": 6,
        "corridor_count": 155,
        "route_count": 1783,
        "family_route_counts": {
            family_id: sum(route["family_id"] == family_id for route in normalized_routes)
            for family_id in sorted({route["family_id"] for route in parent["routes"]})
        },
        "source_strata_counts": _source_strata_counts(normalized_routes),
    }
    if identity != expected_identity:
        raise ValueError("V26 Stage8b revised plan identity inventory drifted")
    result = {
        "schema_version": PLAN_REVISION_SCHEMA_VERSION,
        "evidence_role": PLAN_REVISION_EVIDENCE_ROLE,
        "fixed_dp_head": FROZEN_FIXED_DP_HEAD,
        "split": "development_nonholdout",
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "parent_plan": copy.deepcopy(parent_binding),
        "revision": copy.deepcopy(revision),
        "family_projections": copy.deepcopy(parent["family_projections"]),
        "routes": normalized_routes,
        "identity": copy.deepcopy(expected_identity),
        "denominator": copy.deepcopy(REVISED_DENOMINATOR),
    }
    route_plan_sha = _sha256(row["route_plan_sha256"], "V26 Stage8b revised plan SHA")
    if route_plan_sha != canonical_json_sha256(_revision_hash_payload(result)):
        raise ValueError("V26 Stage8b revised plan SHA drifted")
    result["route_plan_sha256"] = route_plan_sha
    return result


def _finalize_review(review: Mapping[str, Any], *, revised_plan_file_sha256: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(review))
    result["new_plan"]["file_sha256"] = _sha256(
        revised_plan_file_sha256, "V26 Stage8b revised plan file SHA"
    )
    return result


def materialize_revised_plan(
    *, parent_plan_path: Path, qualification_receipt_path: Path, output_dir: Path
) -> dict[str, Path]:
    """Write a new revision root without touching the parent roots."""

    parent_path = parent_plan_path.resolve()
    if not parent_path.is_file():
        raise FileNotFoundError(parent_path)
    parent_plan = validate_diversified_route_plan(json.loads(parent_path.read_text(encoding="utf-8")))
    qualification = load_immutable_qualification(
        parent_plan=parent_plan, qualification_receipt_path=qualification_receipt_path
    )
    source_quality = _verify_common_upstream_gap(parent_plan)
    plan, review = build_revised_plan(
        parent_plan=parent_plan,
        parent_plan_file_sha256=_file_sha256(parent_path),
        qualification=qualification,
        source_quality=source_quality,
    )
    root = output_dir.resolve()
    if root.exists():
        raise FileExistsError(f"V26 Stage8b revision output already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    plan_path = root / "route_plan_revision.json"
    review_path = root / "revision_review.json"
    manifest_path = root / "manifest.json"
    _atomic_write_json(plan_path, plan)
    review = _finalize_review(review, revised_plan_file_sha256=_file_sha256(plan_path))
    _atomic_write_json(review_path, review)
    manifest = {
        "schema_version": PLAN_REVISION_MANIFEST_SCHEMA_VERSION,
        "evidence_role": PLAN_REVISION_EVIDENCE_ROLE,
        "parent_route_plan_path": str(parent_path),
        "parent_route_plan_file_sha256": _file_sha256(parent_path),
        "original_qualification_receipt_path": str(qualification_receipt_path.resolve()),
        "original_qualification_receipt_sha256": qualification["receipt_sha256"],
        "revision_plan_path": str(plan_path),
        "revision_plan_file_sha256": _file_sha256(plan_path),
        "revision_review_path": str(review_path),
        "revision_review_file_sha256": _file_sha256(review_path),
        "route_plan_sha256": plan["route_plan_sha256"],
        "denominator": copy.deepcopy(REVISED_DENOMINATOR),
        "pre_model": True,
        "outcome_fields_consumed": [],
        "not_result_driven": True,
    }
    _atomic_write_json(manifest_path, manifest)
    _atomic_write_json(
        root / "run.status.json",
        {
            "evidence_role": PLAN_REVISION_EVIDENCE_ROLE,
            "status": "terminal",
            "revision_admissible_for_acquisition": True,
            "route_plan_sha256": plan["route_plan_sha256"],
            "denominator": copy.deepcopy(REVISED_DENOMINATOR),
        },
    )
    (root / "run.exit").write_text("0\n", encoding="utf-8")
    return {"root": root, "plan": plan_path, "review": review_path, "manifest": manifest_path}


def load_verified_revised_plan(
    *,
    parent_plan_path: Path,
    revised_plan_path: Path,
    revision_review_path: Path,
    qualification_receipt_path: Path,
) -> dict[str, Any]:
    """Re-derive the revision before CUDA import and return qualified source units."""

    parent_path = parent_plan_path.resolve()
    plan_path = revised_plan_path.resolve()
    review_path = revision_review_path.resolve()
    if not parent_path.is_file() or not plan_path.is_file() or not review_path.is_file():
        raise FileNotFoundError("V26 Stage8b revised plan authority input is missing")
    parent = validate_diversified_route_plan(json.loads(parent_path.read_text(encoding="utf-8")))
    qualification = load_immutable_qualification(
        parent_plan=parent, qualification_receipt_path=qualification_receipt_path
    )
    source_quality = _verify_common_upstream_gap(parent)
    expected_plan, expected_review = build_revised_plan(
        parent_plan=parent,
        parent_plan_file_sha256=_file_sha256(parent_path),
        qualification=qualification,
        source_quality=source_quality,
    )
    actual_plan = validate_revised_plan(
        json.loads(plan_path.read_text(encoding="utf-8")), parent_plan=parent
    )
    if actual_plan != expected_plan:
        raise ValueError("V26 Stage8b revised plan is not the exact evidence-derived successor")
    actual_review = json.loads(review_path.read_text(encoding="utf-8"))
    expected_review = _finalize_review(
        expected_review, revised_plan_file_sha256=_file_sha256(plan_path)
    )
    if actual_review != expected_review:
        raise ValueError("V26 Stage8b revised-plan review receipt drifted")
    qualified_by_revised_index = {
        index: qualification["units"][int(schedule["parent_ordinal"])]
        for index, schedule in enumerate(actual_plan["routes"])
    }
    return {
        "route_plan": actual_plan,
        "qualification": {
            "path": str(qualification["receipt_path"]),
            "sha256": str(qualification["receipt_sha256"]),
            "manifest_sha256": str(qualification["manifest_sha256"]),
            "review_path": str(review_path),
            "review_sha256": _file_sha256(review_path),
            "parent_plan_path": str(parent_path),
            "parent_plan_sha256": parent["route_plan_sha256"],
            "status": "1783_immutable_parent_units_qualified_zero_model",
            "units": qualified_by_revised_index,
        },
    }
