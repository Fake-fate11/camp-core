"""V26-owned source-map projection and signal authority bindings.

This module is intentionally narrow: it derives every projection and signal
decision from the immutable Lanelet2 source map and the frozen route record.
It never changes route order, map bytes, selector weights, or fixed-DP state.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import types
from typing import Any, Iterator, Mapping, Sequence
import xml.etree.ElementTree as ET

import numpy as np

from .diffusion_planner_v26_autoware_sidecar_signal import (
    V26AutowareSidecarSignalAdapter,
)


V26_SOURCE_PROJECTION_SCHEMA_VERSION = "camp_dp_v26_source_bound_projection_v1"
V26_SOURCE_INVENTORY_BINDING_SCHEMA_VERSION = (
    "camp_dp_v26_source_inventory_binding_v1"
)
V26_SOURCE_SIGNAL_AUTHORITY_SCHEMA_VERSION = "camp_dp_v26_source_signal_authority_v1"
V26_SOURCE_TRAFFIC_SIGNAL_MODE = "source_map_traffic_light"
V26_SOURCE_TRAFFIC_SIGNAL_ADAPTER_ID = "camp_dp_v26_source_map_signal_adapter_v1"
V26_SOURCE_NO_SIGNAL_PROVENANCE_SCHEMA_VERSION = (
    "camp_dp_v26_source_certified_no_signal_provenance_v1"
)

_SHA_CHARS = frozenset("0123456789abcdef")


def canonical_json_sha256(value: Any) -> str:
    """Canonical V26 receipt hash; this is not a model or map transformation."""

    return hashlib.sha256(
        (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or set(value) - _SHA_CHARS:
        raise ValueError(f"{label} must be a lowercase SHA256")
    return value


def _require_route_lanelets(value: Any, label: str) -> list[int]:
    if (
        type(value) is not list
        or not value
        or any(type(item) is not int for item in value)
        or len(set(value)) != len(value)
    ):
        raise ValueError(f"{label} must be a nonempty unique integer list")
    return list(value)


def _tag_map(element: ET.Element) -> dict[str, str]:
    return {
        str(tag.attrib["k"]): str(tag.attrib["v"])
        for tag in element.findall("tag")
        if "k" in tag.attrib and "v" in tag.attrib
    }


def _source_xml_inventory(source_map: Path, expected_sha256: str) -> dict[str, Any]:
    """Parse the authoritative source only and retain its traffic inventory."""

    source = source_map.resolve()
    if not source.is_file() or _file_sha256(source) != _require_sha256(
        expected_sha256, "V26 source map SHA"
    ):
        raise ValueError("V26 source map identity drifted")
    root = ET.parse(source).getroot()
    first_node = next(iter(root.findall("node")), None)
    if first_node is None or "lat" not in first_node.attrib or "lon" not in first_node.attrib:
        raise ValueError("V26 source map has no authoritative georeferenced origin")
    try:
        latitude = float(first_node.attrib["lat"])
        longitude = float(first_node.attrib["lon"])
    except ValueError as exc:
        raise ValueError("V26 source map origin is not numeric") from exc
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise ValueError("V26 source map origin is not finite")
    if not -90.0 <= latitude <= 90.0 or not -180.0 <= longitude <= 180.0:
        raise ValueError("V26 source map origin is outside geographic bounds")

    ways: dict[int, list[int]] = {}
    for way in root.findall("way"):
        if "id" not in way.attrib:
            continue
        try:
            way_id = int(way.attrib["id"])
            refs = [int(node.attrib["ref"]) for node in way.findall("nd")]
        except (KeyError, ValueError) as exc:
            raise ValueError("V26 source map has an invalid way primitive") from exc
        if not refs:
            raise ValueError("V26 source map way primitive is empty")
        ways[way_id] = refs

    traffic_by_id: dict[int, dict[str, Any]] = {}
    lanelet_members: dict[int, list[dict[str, str]]] = {}
    for relation in root.findall("relation"):
        if "id" not in relation.attrib:
            continue
        try:
            relation_id = int(relation.attrib["id"])
        except ValueError as exc:
            raise ValueError("V26 source map relation ID is invalid") from exc
        tags = _tag_map(relation)
        members = [dict(member.attrib) for member in relation.findall("member")]
        if tags.get("type") == "regulatory_element" and tags.get("subtype") == "traffic_light":
            roles: list[dict[str, Any]] = []
            missing_roles: list[str] = []
            for role in ("refers", "ref_line", "light_bulbs"):
                primitives: list[dict[str, Any]] = []
                for member in members:
                    if member.get("role") != role or member.get("type") != "way":
                        continue
                    try:
                        primitive_id = int(str(member["ref"]))
                    except (KeyError, ValueError) as exc:
                        raise ValueError("V26 source traffic primitive ID is invalid") from exc
                    if primitive_id not in ways:
                        raise ValueError("V26 source traffic primitive is absent from the map")
                    primitive: dict[str, Any] = {"id": primitive_id}
                    if role == "light_bulbs":
                        primitive["points"] = [{"id": node_id} for node_id in ways[primitive_id]]
                    primitives.append(primitive)
                if not primitives:
                    missing_roles.append(role)
                roles.append({"role": role, "primitives": primitives})
            # A sidecar may be the authoritative traffic representation for a
            # different route on the same map.  Retain an incomplete unrelated
            # source relation for census purposes; only a route that elects the
            # source-map adapter may be rejected for its missing primitive.
            traffic_by_id[relation_id] = {
                "id": relation_id,
                "roles": roles,
                "missing_roles": missing_roles,
            }
        if tags.get("type") == "lanelet":
            lanelet_members[relation_id] = members

    lanelet_to_traffic: dict[int, list[int]] = {}
    for lanelet_id, members in lanelet_members.items():
        mapped: list[int] = []
        for member in members:
            if member.get("role") != "regulatory_element" or member.get("type") != "relation":
                continue
            try:
                candidate = int(str(member["ref"]))
            except (KeyError, ValueError) as exc:
                raise ValueError("V26 source lanelet regulatory ID is invalid") from exc
            if candidate in traffic_by_id:
                mapped.append(candidate)
        if mapped:
            lanelet_to_traffic[lanelet_id] = sorted(set(mapped))

    projection = {
        "schema_version": V26_SOURCE_PROJECTION_SCHEMA_VERSION,
        "source_map_path": str(source),
        "source_map_sha256": expected_sha256,
        "origin_latitude_deg": latitude,
        "origin_longitude_deg": longitude,
        "utm_zone": int((longitude + 180.0) // 6.0) + 1,
        "northern_hemisphere": latitude >= 0.0,
        "projection_definition": "lanelet2.UtmProjector(source_origin, True, False)",
    }
    projection["projection_sha256"] = canonical_json_sha256(projection)
    inventory = {
        "source_map_sha256": expected_sha256,
        "traffic_regulatory_elements": [traffic_by_id[key] for key in sorted(traffic_by_id)],
        "lanelet_to_traffic_regulatory_ids": {
            str(key): value for key, value in sorted(lanelet_to_traffic.items())
        },
    }
    inventory["inventory_sha256"] = canonical_json_sha256(inventory)
    return {"projection": projection, "inventory": inventory}


def v26_source_inventory_binding(source_map: Path, expected_sha256: str) -> dict[str, Any]:
    """Read one authoritative map snapshot for a bounded V26 source pass.

    The binding intentionally contains only source-map projection and traffic
    inventory metadata.  It is not a route cache, does not construct a model,
    and may be shared by multiple route eligibility checks only while callers
    retain the source-byte before/after check for their bounded pass.
    """

    parsed = _source_xml_inventory(source_map, expected_sha256)
    result = {
        "schema_version": V26_SOURCE_INVENTORY_BINDING_SCHEMA_VERSION,
        "source_map_path": str(parsed["projection"]["source_map_path"]),
        "source_map_sha256": str(parsed["projection"]["source_map_sha256"]),
        "source_projection": dict(parsed["projection"]),
        "source_inventory": dict(parsed["inventory"]),
        "binding_sha256": "",
    }
    result["binding_sha256"] = canonical_json_sha256(
        {key: value for key, value in result.items() if key != "binding_sha256"}
    )
    return result


def validate_v26_source_inventory_binding(
    value: Mapping[str, Any], *, source_map: Path, expected_sha256: str
) -> dict[str, Any]:
    """Validate a source snapshot before reusing it for a route authority."""

    result = dict(value)
    expected = {
        "schema_version",
        "source_map_path",
        "source_map_sha256",
        "source_projection",
        "source_inventory",
        "binding_sha256",
    }
    if set(result) != expected or result["schema_version"] != V26_SOURCE_INVENTORY_BINDING_SCHEMA_VERSION:
        raise ValueError("V26 source inventory binding schema drifted")
    expected_path = str(Path(source_map).resolve())
    expected_hash = _require_sha256(expected_sha256, "V26 source inventory map SHA")
    if result["source_map_path"] != expected_path or result["source_map_sha256"] != expected_hash:
        raise ValueError("V26 source inventory binding map identity drifted")
    if result["binding_sha256"] != canonical_json_sha256(
        {key: item for key, item in result.items() if key != "binding_sha256"}
    ):
        raise ValueError("V26 source inventory binding hash drifted")
    projection = dict(result["source_projection"])
    inventory = dict(result["source_inventory"])
    if (
        projection.get("schema_version") != V26_SOURCE_PROJECTION_SCHEMA_VERSION
        or projection.get("source_map_path") != expected_path
        or projection.get("source_map_sha256") != expected_hash
        or projection.get("projection_sha256")
        != canonical_json_sha256(
            {key: item for key, item in projection.items() if key != "projection_sha256"}
        )
        or inventory.get("source_map_sha256") != expected_hash
        or inventory.get("inventory_sha256")
        != canonical_json_sha256(
            {key: item for key, item in inventory.items() if key != "inventory_sha256"}
        )
    ):
        raise ValueError("V26 source inventory binding content drifted")
    return {
        "schema_version": V26_SOURCE_INVENTORY_BINDING_SCHEMA_VERSION,
        "source_map_path": expected_path,
        "source_map_sha256": expected_hash,
        "source_projection": projection,
        "source_inventory": inventory,
        "binding_sha256": result["binding_sha256"],
    }


def v26_source_projection_binding(source_map: Path, expected_sha256: str) -> dict[str, Any]:
    """Return a read-only, source-derived projection binding."""

    return dict(
        v26_source_inventory_binding(source_map, expected_sha256)["source_projection"]
    )


@contextmanager
def v26_source_bound_projection(binding: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
    """Temporarily bind fixed-DP's importer to this exact source-map origin.

    The official Autoware module, when present, remains imported so its
    regulatory-element registration is preserved.  Only the projector factory
    is scoped to the current source map and restored after the builder returns.
    """

    row = dict(binding)
    expected = {
        "schema_version",
        "source_map_path",
        "source_map_sha256",
        "origin_latitude_deg",
        "origin_longitude_deg",
        "utm_zone",
        "northern_hemisphere",
        "projection_definition",
        "projection_sha256",
    }
    if set(row) != expected or row.get("schema_version") != V26_SOURCE_PROJECTION_SCHEMA_VERSION:
        raise ValueError("V26 source projection binding schema drifted")
    if row["projection_sha256"] != canonical_json_sha256(
        {key: row[key] for key in row if key != "projection_sha256"}
    ):
        raise ValueError("V26 source projection binding hash drifted")
    source = Path(str(row["source_map_path"])).resolve()
    if not source.is_file() or _file_sha256(source) != row["source_map_sha256"]:
        raise ValueError("V26 source projection map identity drifted")
    if int((float(row["origin_longitude_deg"]) + 180.0) // 6.0) + 1 != int(
        row["utm_zone"]
    ):
        raise ValueError("V26 source projection UTM zone drifted")

    lanelet2 = importlib.import_module("lanelet2")
    origin = lanelet2.io.Origin(
        float(row["origin_latitude_deg"]), float(row["origin_longitude_deg"])
    )
    try:
        projector = lanelet2.projection.UtmProjector(origin, True, False)
    except TypeError:
        projector = lanelet2.projection.UtmProjector(origin)

    package_name = "autoware_lanelet2_extension_python"
    module_name = f"{package_name}.projection"
    package_before = sys.modules.get(package_name)
    module_before = sys.modules.get(module_name)
    created_package = package_before is None
    created_module = module_before is None
    if module_before is None:
        package = package_before or types.ModuleType(package_name)
        module = types.ModuleType(module_name)
        setattr(package, "projection", module)
        sys.modules[package_name] = package
        sys.modules[module_name] = module
    else:
        module = module_before
    prior_factory = getattr(module, "MGRSProjector", None)
    prior_binding = getattr(module, "__camp_v26_source_projection_binding_sha256__", None)

    def mgrs_projector(_ignored_origin: Any) -> Any:
        return projector

    setattr(module, "MGRSProjector", mgrs_projector)
    setattr(module, "__camp_v26_source_projection_binding_sha256__", row["projection_sha256"])
    try:
        yield row
    finally:
        if prior_factory is None:
            try:
                delattr(module, "MGRSProjector")
            except AttributeError:
                pass
        else:
            setattr(module, "MGRSProjector", prior_factory)
        if prior_binding is None:
            try:
                delattr(module, "__camp_v26_source_projection_binding_sha256__")
            except AttributeError:
                pass
        else:
            setattr(module, "__camp_v26_source_projection_binding_sha256__", prior_binding)
        if created_module:
            sys.modules.pop(module_name, None)
        if created_package:
            sys.modules.pop(package_name, None)


def v26_route_geometry_receipt(builder: Any, route_lanelet_ids: Sequence[int], projection: Mapping[str, Any]) -> dict[str, Any]:
    """Bind live parsed geometry to the declared source projection without edits."""

    lanelets = _require_route_lanelets(list(route_lanelet_ids), "V26 route lanelets")
    pieces: list[list[list[float]]] = []
    for lanelet_id in lanelets:
        cached = getattr(builder, "_cache", {}).get(int(lanelet_id))
        if cached is None:
            raise ValueError("V26 route lanelet is absent from parsed source geometry")
        points = np.asarray(getattr(cached, "raw_centerline", None), dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 2 or len(points) < 2 or not np.isfinite(points).all():
            raise ValueError("V26 parsed route centerline is invalid")
        if not math.isfinite(float(getattr(cached, "arc_length", float("nan")))) or float(
            getattr(cached, "arc_length", 0.0)
        ) <= 0.0:
            raise ValueError("V26 parsed route primitive has invalid arc length")
        pieces.append(points.tolist())
    payload = {
        "schema_version": "camp_dp_v26_parsed_route_geometry_v1",
        "projection_sha256": str(projection["projection_sha256"]),
        "route_lanelet_ids": lanelets,
        "centerline_pieces": pieces,
    }
    return {
        "schema_version": payload["schema_version"],
        "projection_sha256": payload["projection_sha256"],
        "route_lanelet_ids": lanelets,
        "derived_geometry_sha256": canonical_json_sha256(payload),
        "primitive_count": len(pieces),
    }


def require_v26_route_connectivity(builder: Any, route_lanelet_ids: Sequence[int]) -> None:
    """Require the frozen ordered route to be exactly routable; never replace it."""

    lanelets = _require_route_lanelets(list(route_lanelet_ids), "V26 route connectivity lanelets")
    if any(item not in getattr(builder, "_ll_by_id", {}) for item in lanelets):
        raise ValueError("V26 route connectivity references a missing lanelet")
    resolved = builder.route_with_waypoints(lanelets[0], lanelets[1:-1], lanelets[-1])
    if resolved is None or tuple(int(item) for item in resolved) != tuple(lanelets):
        raise ValueError("V26 frozen route connectivity is not exact")


def _source_signal_identity(
    *, record: Mapping[str, Any], inventory: Mapping[str, Any], projection: Mapping[str, Any]
) -> str:
    return canonical_json_sha256(
        {
            "schema_version": V26_SOURCE_SIGNAL_AUTHORITY_SCHEMA_VERSION,
            "route_identity_sha256": str(record["identity_sha256"]),
            "source_map_sha256": str(record["source_map_sha256"]),
            "route_lanelet_ids": list(record["lanelet_ids"]),
            "source_geometry_sha256": str(record["source_geometry_sha256"]),
            "source_stratum": dict(record["source_stratum"]),
            "projection_sha256": str(projection["projection_sha256"]),
            "inventory_sha256": str(inventory["inventory_sha256"]),
        }
    )


def build_v26_source_signal_config(
    *,
    schedule: Mapping[str, Any],
    family: Mapping[str, Any],
    route_sha256: str,
    source_inventory_binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve V26 signal authority from a frozen route and its source map.

    A no-signal result is certified only after the authoritative map inventory
    proves absence for the declared lanelets.  Traffic routes either bind their
    frozen Autoware sidecar or a source-derived traffic relation; missing or
    ambiguous authority is an error, never a fallback.
    """

    record = dict(schedule["route_record"])
    source = Path(str(record["source_map_path"])).resolve()
    source_sha256 = str(record["source_map_sha256"])
    if source_inventory_binding is None:
        parsed = _source_xml_inventory(source, source_sha256)
        projection = dict(parsed["projection"])
        inventory = dict(parsed["inventory"])
    else:
        binding = validate_v26_source_inventory_binding(
            source_inventory_binding,
            source_map=source,
            expected_sha256=source_sha256,
        )
        projection = dict(binding["source_projection"])
        inventory = dict(binding["source_inventory"])
    lanelets = _require_route_lanelets(record["lanelet_ids"], "V26 source signal route lanelets")
    lanelet_mapping = {
        int(key): list(value)
        for key, value in dict(inventory["lanelet_to_traffic_regulatory_ids"]).items()
    }
    traffic_ids = sorted(
        {
            int(regulatory_id)
            for lanelet_id in lanelets
            for regulatory_id in lanelet_mapping.get(int(lanelet_id), [])
        }
    )
    stratum = dict(record["source_stratum"])
    if type(stratum.get("traffic_light")) is not bool:
        raise ValueError("V26 source traffic stratum is invalid")
    identity = _source_signal_identity(
        record=record, inventory=inventory, projection=projection
    )
    provenance = {
        "schema_version": V26_SOURCE_SIGNAL_AUTHORITY_SCHEMA_VERSION,
        "source_signal_authority_identity_sha256": identity,
        "source_projection_sha256": projection["projection_sha256"],
        "source_inventory_sha256": inventory["inventory_sha256"],
        "route_identity_sha256": record["identity_sha256"],
        "source_map_sha256": record["source_map_sha256"],
        "route_lanelet_ids": lanelets,
        "traffic_light_regulatory_element_ids": traffic_ids,
    }
    if not stratum["traffic_light"]:
        if traffic_ids:
            raise ValueError("V26 no-signal stratum conflicts with source traffic authority")
        authority = {
            "schema_version": "camp_dp_v26_certified_no_signal_authority_v1",
            "route_sha256": _require_sha256(route_sha256, "V26 route SHA"),
            "map_sha256": str(record["source_map_sha256"]),
            "route_lanelet_ids": lanelets,
            "route_geometry_sha256": str(record["source_geometry_sha256"]),
            "source_chain_sha256": canonical_json_sha256(
                {
                    "schema_version": V26_SOURCE_NO_SIGNAL_PROVENANCE_SCHEMA_VERSION,
                    "provenance": provenance,
                    "source_artifact_sha256": str(schedule["source_artifact_sha256"]),
                    "event_manifest_sha256": str(schedule["event_manifest_sha256"]),
                }
            ),
            "certification_sha256": "",
            "traffic_light_regulatory_element_ids": [],
        }
        authority["certification_sha256"] = canonical_json_sha256(
            {key: value for key, value in authority.items() if key != "certification_sha256"}
        )
        return {
            "signal_authority_mode": "certified_no_signal",
            "certified_no_signal_authority": authority,
            "source_signal_authority": provenance,
        }

    sidecar = family.get("sidecar")
    if type(sidecar) is dict:
        required = {
            "index_path",
            "index_sha256",
            "manifest_path",
            "manifest_sha256",
            "source_sha256",
        }
        if not required.issubset(sidecar):
            raise ValueError("V26 traffic sidecar binding is incomplete")
        return {
            "signal_authority_mode": "autoware_traffic_light_sidecar",
            "regulatory_sidecar": {
                "geometry_copy_sha256": record["source_map_sha256"],
                **{key: sidecar[key] for key in required},
            },
            "source_signal_authority": provenance,
        }
    if len(traffic_ids) != 1:
        raise ValueError("V26 traffic route has unknown or ambiguous source authority")
    records = {
        int(item["id"]): dict(item)
        for item in inventory["traffic_regulatory_elements"]
    }
    regulatory = records.get(traffic_ids[0])
    if regulatory is None:
        raise ValueError("V26 source traffic authority inventory is incomplete")
    if regulatory.get("missing_roles"):
        raise ValueError(
            "V26 source traffic authority lacks "
            + ",".join(str(value) for value in regulatory["missing_roles"])
        )
    regulatory = {**regulatory, "runtime_type": "AutowareTrafficLight"}
    authority = {
        "schema_version": V26_SOURCE_SIGNAL_AUTHORITY_SCHEMA_VERSION,
        "route_sha256": _require_sha256(route_sha256, "V26 route SHA"),
        "map_sha256": str(record["source_map_sha256"]),
        "route_lanelet_ids": lanelets,
        "route_geometry_sha256": str(record["source_geometry_sha256"]),
        "source_projection_sha256": projection["projection_sha256"],
        "source_inventory_sha256": inventory["inventory_sha256"],
        "traffic_light_regulatory_element_ids": traffic_ids,
        "lanelets": [
            {
                "id": lanelet_id,
                "regulatory_element_ids": lanelet_mapping.get(lanelet_id, []),
            }
            for lanelet_id in lanelets
        ],
        "regulatory_elements": [regulatory],
        "source_authority_sha256": "",
    }
    authority["source_authority_sha256"] = canonical_json_sha256(
        {key: value for key, value in authority.items() if key != "source_authority_sha256"}
    )
    return {
        "signal_authority_mode": V26_SOURCE_TRAFFIC_SIGNAL_MODE,
        "source_map_traffic_authority": authority,
        "source_signal_authority": provenance,
    }


class V26SourceMapTrafficSignalAdapter(V26AutowareSidecarSignalAdapter):
    """V26 source-XML traffic adapter with observed same-tick phase only."""

    def __init__(self, authority: Mapping[str, Any]) -> None:
        row = dict(authority)
        required = {
            "schema_version",
            "route_sha256",
            "map_sha256",
            "route_lanelet_ids",
            "route_geometry_sha256",
            "source_projection_sha256",
            "source_inventory_sha256",
            "traffic_light_regulatory_element_ids",
            "lanelets",
            "regulatory_elements",
            "source_authority_sha256",
        }
        if set(row) != required or row["schema_version"] != V26_SOURCE_SIGNAL_AUTHORITY_SCHEMA_VERSION:
            raise ValueError("V26 source traffic authority schema drifted")
        for key in (
            "route_sha256",
            "map_sha256",
            "route_geometry_sha256",
            "source_projection_sha256",
            "source_inventory_sha256",
            "source_authority_sha256",
        ):
            row[key] = _require_sha256(row[key], f"V26 source traffic {key}")
        if row["source_authority_sha256"] != canonical_json_sha256(
            {key: value for key, value in row.items() if key != "source_authority_sha256"}
        ):
            raise ValueError("V26 source traffic authority hash drifted")
        route = _require_route_lanelets(row["route_lanelet_ids"], "V26 source traffic route")
        traffic_ids = _require_route_lanelets(
            row["traffic_light_regulatory_element_ids"], "V26 source traffic regulatory IDs"
        )
        if len(traffic_ids) != 1:
            raise ValueError("V26 source traffic adapter requires one authority per route")
        lanelets = row["lanelets"]
        regulatory = row["regulatory_elements"]
        if type(lanelets) is not list or type(regulatory) is not list or len(regulatory) != 1:
            raise ValueError("V26 source traffic inventory is incomplete")
        source_manifest = {
            "geometry_copy_sha256": row["map_sha256"],
            "source_sha256": row["map_sha256"],
            "lanelets": lanelets,
            "regulatory_elements": regulatory,
        }
        bridge_binding = {
            "schema_version": "camp_dp_v26_autoware_sidecar_binding_v1",
            "route_sha256": row["route_sha256"],
            "map_sha256": row["map_sha256"],
            "geometry_copy_sha256": row["map_sha256"],
            "sidecar_index_sha256": row["source_inventory_sha256"],
            "sidecar_manifest_sha256": row["source_authority_sha256"],
            "sidecar_source_sha256": row["map_sha256"],
        }
        self.source_authority = row
        super().__init__(binding=bridge_binding, sidecar_manifest=source_manifest)

    def _stop_line(self, record: Mapping[str, Any]) -> tuple[int, np.ndarray]:
        rows = [
            primitive
            for role in record.get("roles", [])
            if type(role) is dict and role.get("role") == "ref_line"
            for primitive in role.get("primitives", [])
            if type(primitive) is dict
        ]
        if len(rows) != 1 or type(rows[0].get("id")) is not int or self._builder is None:
            raise ValueError("V26 source traffic light has no unique live stop line")
        layer = getattr(self._builder._lanelet_map, "lineStringLayer", None)
        if layer is None:
            raise ValueError("V26 source traffic map has no line-string layer")
        try:
            line = layer.get(int(rows[0]["id"]))
        except AttributeError:
            try:
                line = layer[int(rows[0]["id"])]
            except Exception as exc:  # pragma: no cover - lanelet binding variants
                raise ValueError("V26 source traffic stop line is absent from live map") from exc
        except Exception as exc:
            raise ValueError("V26 source traffic stop line is absent from live map") from exc
        points = np.asarray([(point.x, point.y) for point in line], dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 2 or len(points) < 2 or not np.isfinite(points).all():
            raise ValueError("V26 source traffic stop-line geometry is invalid")
        return int(rows[0]["id"]), points

    def _signal_receipt(self, runtime: Mapping[str, Any]) -> dict[str, Any]:
        record = self._require_signal_record()
        return {
            "schema_version": "camp_dp_v26_source_map_signal_receipt_v1",
            "signal_authority_mode": V26_SOURCE_TRAFFIC_SIGNAL_MODE,
            "signal_adapter_id": V26_SOURCE_TRAFFIC_SIGNAL_ADAPTER_ID,
            "source_authority_sha256": self.source_authority["source_authority_sha256"],
            "source_projection_sha256": self.source_authority["source_projection_sha256"],
            "route_lanelet_ids": list(self._route_lanelet_ids),
            "controlled_lanelet_ids": list(self._controlled_lanelet_ids),
            "route_traffic_authority_ids": list(self._route_traffic_authority_ids),
            "authority_selection_rule": "first_controlled_lanelet_in_frozen_route_order",
            "regulatory_element_id": record["regulatory_element_id"],
            "physical_light_ids": list(record["physical_light_ids"]),
            "bulb_ids": list(record["bulb_ids"]),
            "stop_line_id": record["stop_line_id"],
            "stop_line_geometry_sha256": canonical_json_sha256(record["stop_line_world"].tolist()),
            "route_graph_sha256": record["route_graph_sha256"],
            "signal_chain_sha256": str(runtime["signal_chain_sha256"]),
            "runtime_receipt_sha256": canonical_json_sha256(runtime),
            "phase_authority_mode": "observe_same_tick_request",
            "current_phase": str(runtime["current_phase"]),
            "source_valid": True,
            "future_schedule_consumed": False,
            "candidate_tensor_consumed": False,
            "selected_trajectory_consumed": False,
        }

    def sync_model_input_map_cache(
        self, scene: Any, map_cache: Any, tick_index: int
    ) -> Mapping[str, Any]:
        receipt = dict(super().sync_model_input_map_cache(scene, map_cache, tick_index))
        receipt["schema_version"] = "camp_dp_v26_source_map_model_cache_v1"
        receipt["source_authority_sha256"] = self.source_authority["source_authority_sha256"]
        return receipt

    def receipt(self) -> dict[str, Any]:
        return {
            "schema_version": "camp_dp_v26_source_map_signal_adapter_binding_v1",
            "signal_authority_mode": V26_SOURCE_TRAFFIC_SIGNAL_MODE,
            "signal_adapter_id": V26_SOURCE_TRAFFIC_SIGNAL_ADAPTER_ID,
            "source_authority": dict(self.source_authority),
        }
