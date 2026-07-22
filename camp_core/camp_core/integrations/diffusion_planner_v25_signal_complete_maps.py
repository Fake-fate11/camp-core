from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Mapping
import xml.etree.ElementTree as ET

import lanelet2

SCHEMA_VERSION = "camp_dp_v25_project_authored_signal_complete_suite_v3"
MAP_SCHEMA_VERSION = "camp_dp_v25_project_authored_lanelet2_signal_map_v3"
SOURCE_FAMILY = "project_authored_mit_deterministic_lanelet2"
LICENSE_SPDX = "MIT"
_GEO_ORIGIN_LAT = 35.0
_GEO_ORIGIN_LON = 139.0
_UTM_PROJECTOR = lanelet2.projection.UtmProjector(
    lanelet2.io.Origin(_GEO_ORIGIN_LAT, _GEO_ORIGIN_LON), True, False
)
SUPPORTED_PHASE_AUTHORITY_MODES = (
    "controlled_same_tick_override",
    "observe_same_tick_request",
)
SPLIT_PLAN = {
    "calibration": {"map_count": 5, "routes_per_map": 10},
    "fresh_b2": {"map_count": 25, "routes_per_map": 4},
}


@dataclass(frozen=True)
class SignalCompleteMap:
    relative_path: str
    osm_bytes: bytes
    receipt: dict[str, Any]


def build_signal_complete_suite(split: str) -> dict[str, Any]:
    """Build an outcome-blind, split-specific signal-complete map suite.

    These maps are authored from first principles for the controlled V25
    benchmark.  They do not derive from, rewrite, or replace any fixed-DP or
    TIER IV map.  Every route has a unique route-local physical signature, a
    TrafficLight regulatory element, physical light and bulbs, a certified
    stop line, and an explicit route-arc binding.  Runtime phase is deliberately
    absent: it must still come from the same-tick request receipt.
    """

    if split not in SPLIT_PLAN:
        raise ValueError(f"unknown signal-complete split: {split}")
    plan = SPLIT_PLAN[split]
    maps: list[SignalCompleteMap] = []
    global_offset = 0 if split == "calibration" else 10_000
    for map_index in range(plan["map_count"]):
        maps.append(
            _build_map(
                split=split,
                map_index=map_index,
                route_count=plan["routes_per_map"],
                global_offset=global_offset,
            )
        )
    rows = [row for item in maps for row in item.receipt["routes"]]
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "outcome_blind_signal_complete_suite_materialized",
        "source_family": SOURCE_FAMILY,
        "license": {
            "spdx": LICENSE_SPDX,
            "provenance": "project_authored_from_first_principles",
            "repository_license_path": "LICENSE",
            "third_party_map_payload_derived": False,
        },
        "split": split,
        "map_count": len(maps),
        "corridor_count": len(rows),
        "route_count": len(rows),
        "maps": [item.receipt for item in maps],
        "map_payloads": {
            item.relative_path: item.osm_bytes for item in maps
        },
        "source_independent_geometry_sha256": sorted(
            row["source_independent_geometry_sha256"] for row in rows
        ),
        "same_tick_phase_required": True,
        "phase_authority_modes_supported": list(SUPPORTED_PHASE_AUTHORITY_MODES),
        "phase_remaining_available": False,
        "future_phase_schedule_consumed": False,
        "outcome_fields_consumed": [],
        "fresh_b2_opened": False,
        "fixed_dp_modified": False,
        "candidate_tensor_modified": False,
    }
    validate_signal_complete_suite(result)
    return result


def validate_signal_complete_suite(value: Mapping[str, Any]) -> dict[str, Any]:
    """Independently rebuild structural and clone-separation invariants."""

    if type(value) is not dict:
        raise ValueError("signal-complete suite must be a native mapping")
    expected_fields = {
        "schema_version",
        "status",
        "source_family",
        "license",
        "split",
        "map_count",
        "corridor_count",
        "route_count",
        "maps",
        "map_payloads",
        "source_independent_geometry_sha256",
        "same_tick_phase_required",
        "phase_authority_modes_supported",
        "phase_remaining_available",
        "future_phase_schedule_consumed",
        "outcome_fields_consumed",
        "fresh_b2_opened",
        "fixed_dp_modified",
        "candidate_tensor_modified",
    }
    if set(value) != expected_fields:
        raise ValueError("signal-complete suite field set drifted")
    split = value["split"]
    if split not in SPLIT_PLAN:
        raise ValueError("signal-complete suite split drifted")
    plan = SPLIT_PLAN[split]
    exact = {
        "schema_version": SCHEMA_VERSION,
        "status": "outcome_blind_signal_complete_suite_materialized",
        "source_family": SOURCE_FAMILY,
        "map_count": plan["map_count"],
        "corridor_count": plan["map_count"] * plan["routes_per_map"],
        "route_count": plan["map_count"] * plan["routes_per_map"],
        "same_tick_phase_required": True,
        "phase_authority_modes_supported": list(SUPPORTED_PHASE_AUTHORITY_MODES),
        "phase_remaining_available": False,
        "future_phase_schedule_consumed": False,
        "outcome_fields_consumed": [],
        "fresh_b2_opened": False,
        "fixed_dp_modified": False,
        "candidate_tensor_modified": False,
    }
    for name, expected in exact.items():
        if type(value[name]) is not type(expected) or value[name] != expected:
            raise ValueError(f"signal-complete suite {name} drifted")
    license_receipt = value["license"]
    if license_receipt != {
        "spdx": LICENSE_SPDX,
        "provenance": "project_authored_from_first_principles",
        "repository_license_path": "LICENSE",
        "third_party_map_payload_derived": False,
    }:
        raise ValueError("signal-complete map license receipt drifted")
    maps = value["maps"]
    payloads = value["map_payloads"]
    if (
        type(maps) is not list
        or len(maps) != plan["map_count"]
        or type(payloads) is not dict
        or len(payloads) != len(maps)
        or any(type(path) is not str or type(data) is not bytes for path, data in payloads.items())
    ):
        raise ValueError("signal-complete map inventory drifted")
    all_geometry: list[str] = []
    all_corridors: set[str] = set()
    all_routes: set[str] = set()
    for map_index, receipt in enumerate(maps):
        if type(receipt) is not dict:
            raise ValueError("signal-complete map receipt must be a mapping")
        path = receipt.get("relative_path")
        if path not in payloads:
            raise ValueError("signal-complete map payload is missing")
        data = payloads[path]
        if (
            receipt.get("schema_version") != MAP_SCHEMA_VERSION
            or receipt.get("split") != split
            or receipt.get("map_index") != map_index
            or receipt.get("map_sha256") != _sha256(data)
            or receipt.get("map_geometry_sha256")
            != _canonical_sha(
                sorted(
                    row["source_independent_geometry_sha256"]
                    for row in receipt.get("routes", [])
                )
            )
            or receipt.get("runtime_phase_embedded") is not False
            or receipt.get("future_schedule_embedded") is not False
        ):
            raise ValueError("signal-complete map receipt authority drifted")
        root = _strict_osm(data)
        routes = receipt.get("routes")
        if type(routes) is not list or len(routes) != plan["routes_per_map"]:
            raise ValueError("signal-complete map route denominator drifted")
        _validate_osm_routes(root, routes)
        for row in routes:
            geometry = _sha(row.get("source_independent_geometry_sha256"), "geometry")
            corridor = _sha(row.get("corridor_sha256"), "corridor")
            route = _sha(row.get("route_identity_sha256"), "route")
            if corridor in all_corridors or route in all_routes:
                raise ValueError("signal-complete corridor/route identity repeated")
            all_geometry.append(geometry)
            all_corridors.add(corridor)
            all_routes.add(route)
    if len(set(all_geometry)) != len(all_geometry):
        raise ValueError("signal-complete suite contains a geometry/semantic clone")
    if value["source_independent_geometry_sha256"] != sorted(all_geometry):
        raise ValueError("signal-complete geometry inventory drifted")
    result = dict(value)
    result.pop("map_payloads")
    return result


def _build_map(
    *, split: str, map_index: int, route_count: int, global_offset: int
) -> SignalCompleteMap:
    root = _element(
        "osm",
        {"generator": "camp-v25-signal-complete-materializer", "version": "0.7"},
    )
    _element(
        "MetaInfo",
        {"format_version": "1.0", "map_version": f"v25-{split}-{map_index:02d}"},
        parent=root,
    )
    rows: list[dict[str, Any]] = []
    first_physical_index = global_offset + map_index * route_count
    first_half_width = (3.10 + 0.035 * (first_physical_index % 11)) / 2.0
    for local_index in range(route_count):
        physical_index = global_offset + map_index * route_count + local_index
        # The no-ROS fixed-DP loader creates its UTM offset from the first OSM
        # node.  Keep that first boundary point at local (0, 0), then encode
        # every point geodetically so the DP consumes the intended metric map.
        placement = (0.0, local_index * 240.0 - first_half_width)
        row = _append_corridor(
            root,
            split=split,
            map_index=map_index,
            local_index=local_index,
            physical_index=physical_index,
            placement=placement,
        )
        rows.append(row)
    ET.indent(root, space="  ")
    data = ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"
    relative = (
        f"project_authored_signal_complete/{split}/map_{map_index:02d}/"
        "lanelet2_map.osm"
    )
    map_sha = _sha256(data)
    map_geometry_sha = _canonical_sha(
        sorted(row["source_independent_geometry_sha256"] for row in rows)
    )
    for row in rows:
        row["map_sha256"] = map_sha
        row["map_geometry_sha256"] = map_geometry_sha
        row["map_relative_path"] = relative
    receipt = {
        "schema_version": MAP_SCHEMA_VERSION,
        "split": split,
        "map_index": map_index,
        "relative_path": relative,
        "map_sha256": map_sha,
        "map_geometry_sha256": map_geometry_sha,
        "route_count": route_count,
        "routes": rows,
        "runtime_phase_embedded": False,
        "future_schedule_embedded": False,
        "outcome_fields_consumed": [],
    }
    return SignalCompleteMap(relative_path=relative, osm_bytes=data, receipt=receipt)


def _append_corridor(
    root: ET.Element,
    *,
    split: str,
    map_index: int,
    local_index: int,
    physical_index: int,
    placement: tuple[float, float],
) -> dict[str, Any]:
    base = 1_000_000 + (0 if split == "calibration" else 50_000_000)
    base += map_index * 100_000 + local_index * 1_000
    lengths = (
        36.0 + 0.37 * (physical_index % 17),
        34.0 + 0.41 * (physical_index % 19),
        46.0 + 0.43 * (physical_index % 23),
    )
    sign = -1.0 if physical_index % 2 else 1.0
    turn_1 = sign * (0.055 + 0.0065 * (physical_index % 29))
    turn_2 = -sign * (0.018 + 0.0035 * (physical_index % 13))
    headings = (0.0, turn_1, turn_1 + turn_2)
    centers = [placement]
    for length, heading in zip(lengths, headings, strict=True):
        previous = centers[-1]
        centers.append(
            (
                previous[0] + length * math.cos(heading),
                previous[1] + length * math.sin(heading),
            )
        )
    width = 3.10 + 0.035 * (physical_index % 11)
    speed_kph = (30.0, 40.0, 50.0)[physical_index % 3]
    left, right = _offset_polyline(tuple(centers), width)
    serialized_left = [
        (round(float(point[0]), 6), round(float(point[1]), 6)) for point in left
    ]
    serialized_right = [
        (round(float(point[0]), 6), round(float(point[1]), 6)) for point in right
    ]
    serialized_centers = [
        (
            0.5 * (left_point[0] + right_point[0]),
            0.5 * (left_point[1] + right_point[1]),
        )
        for left_point, right_point in zip(
            serialized_left, serialized_right, strict=True
        )
    ]
    left_nodes = [base + 1 + index for index in range(4)]
    right_nodes = [base + 11 + index for index in range(4)]
    for node_id, point in zip(left_nodes, left, strict=True):
        _append_node(root, node_id, point, ele=0.0)
    for node_id, point in zip(right_nodes, right, strict=True):
        _append_node(root, node_id, point, ele=0.0)
    boundary_ways: list[tuple[int, int]] = []
    for segment in range(3):
        left_way = base + 101 + segment * 2
        right_way = base + 102 + segment * 2
        _append_way(
            root,
            left_way,
            (left_nodes[segment], left_nodes[segment + 1]),
            {"subtype": "solid", "type": "line_thin"},
        )
        _append_way(
            root,
            right_way,
            (right_nodes[segment], right_nodes[segment + 1]),
            {"subtype": "solid", "type": "line_thin"},
        )
        boundary_ways.append((left_way, right_way))

    stop_center = _lerp(centers[0], centers[1], 0.88)
    stop_normal = (-math.sin(headings[0]), math.cos(headings[0]))
    stop_half = width * 0.54
    stop_points = (
        (stop_center[0] + stop_normal[0] * stop_half, stop_center[1] + stop_normal[1] * stop_half),
        (stop_center[0] - stop_normal[0] * stop_half, stop_center[1] - stop_normal[1] * stop_half),
    )
    stop_nodes = (base + 31, base + 32)
    for node_id, point in zip(stop_nodes, stop_points, strict=True):
        _append_node(root, node_id, point, ele=0.0)
    stop_way = base + 201
    _append_way(root, stop_way, stop_nodes, {"subtype": "solid", "type": "stop_line"})

    light_center = (
        stop_center[0] + 2.0 * math.cos(headings[0]) + (width + 1.0) * stop_normal[0],
        stop_center[1] + 2.0 * math.sin(headings[0]) + (width + 1.0) * stop_normal[1],
    )
    light_nodes = (base + 41, base + 42)
    _append_node(root, light_nodes[0], light_center, ele=4.0)
    _append_node(
        root,
        light_nodes[1],
        (light_center[0] + 0.8 * stop_normal[0], light_center[1] + 0.8 * stop_normal[1]),
        ele=4.0,
    )
    light_way = base + 202
    _append_way(
        root,
        light_way,
        light_nodes,
        {"height": "0.5", "subtype": "red_yellow_green", "type": "traffic_light"},
    )
    bulb_nodes = (base + 51, base + 52, base + 53)
    for offset, (node_id, color) in enumerate(
        zip(bulb_nodes, ("red", "yellow", "green"), strict=True)
    ):
        point = (
            light_center[0] + 0.18 * offset * stop_normal[0],
            light_center[1] + 0.18 * offset * stop_normal[1],
        )
        _append_node(root, node_id, point, ele=4.25, tags={"color": color})
    bulb_way = base + 203
    _append_way(
        root,
        bulb_way,
        bulb_nodes,
        {"traffic_light_id": str(light_way), "type": "light_bulbs"},
    )
    regulatory_id = base + 301
    _append_relation(
        root,
        regulatory_id,
        (
            ("way", stop_way, "ref_line"),
            ("way", light_way, "refers"),
            ("way", bulb_way, "light_bulbs"),
        ),
        {"subtype": "traffic_light", "type": "regulatory_element"},
    )
    lanelet_ids: list[int] = []
    for segment, (left_way, right_way) in enumerate(boundary_ways):
        lanelet_id = base + 401 + segment
        members: list[tuple[str, int, str]] = [
            ("way", left_way, "left"),
            ("way", right_way, "right"),
        ]
        if segment == 0:
            members.append(("relation", regulatory_id, "regulatory_element"))
        direction = "straight"
        if segment == 1 and abs(turn_1) >= 0.08:
            direction = "left" if turn_1 > 0.0 else "right"
        _append_relation(
            root,
            lanelet_id,
            tuple(members),
            {
                "location": "urban",
                "one_way": "yes",
                "participant:vehicle": "yes",
                "speed_limit": _float(speed_kph),
                "subtype": "road",
                "turn_direction": direction,
                "type": "lanelet",
            },
        )
        lanelet_ids.append(lanelet_id)

    serialized_initial_heading = round(
        math.atan2(
            serialized_centers[1][1] - serialized_centers[0][1],
            serialized_centers[1][0] - serialized_centers[0][0],
        ),
        6,
    )
    initial_cos = math.cos(serialized_initial_heading)
    initial_sin = math.sin(serialized_initial_heading)
    route_local = []
    for point in serialized_centers:
        dx = point[0] - serialized_centers[0][0]
        dy = point[1] - serialized_centers[0][1]
        route_local.append(
            (
                round(dx * initial_cos + dy * initial_sin, 6),
                round(-dx * initial_sin + dy * initial_cos, 6),
            )
        )
    serialized_lengths = [
        math.hypot(end[0] - start[0], end[1] - start[1])
        for start, end in zip(
            serialized_centers[:-1], serialized_centers[1:], strict=True
        )
    ]
    physical_payload = {
        "schema_version": "camp_dp_v25_signal_route_physical_payload_v1",
        "centerline_route_local_m": [list(point) for point in route_local],
        "segment_lengths_m": [round(value, 6) for value in serialized_lengths],
        "lane_width_m": round(width, 6),
        "speed_limit_kph": speed_kph,
        "turn_angles_rad": [round(turn_1, 6), round(turn_2, 6)],
        "stop_line_fraction_of_approach": 0.88,
        "signal_chain_roles": ["ref_line", "refers", "light_bulbs"],
    }
    geometry_sha = _canonical_sha(physical_payload)
    stop_geometry = [[round(x, 6), round(y, 6)] for x, y in stop_points]
    stop_midpoint = (
        0.5 * (stop_geometry[0][0] + stop_geometry[1][0]),
        0.5 * (stop_geometry[0][1] + stop_geometry[1][1]),
    )
    first_start = serialized_centers[0]
    first_end = serialized_centers[1]
    first_delta = (
        first_end[0] - first_start[0],
        first_end[1] - first_start[1],
    )
    first_sq = first_delta[0] ** 2 + first_delta[1] ** 2
    route_arc = (
        (
            (stop_midpoint[0] - first_start[0]) * first_delta[0]
            + (stop_midpoint[1] - first_start[1]) * first_delta[1]
        )
        / first_sq
        * serialized_lengths[0]
    )
    route_identity = _canonical_sha(
        {"geometry": geometry_sha, "split": split, "map_index": map_index, "route_index": local_index}
    )
    corridor_sha = _canonical_sha(
        {"geometry": geometry_sha, "corridor_kind": "single_signal_route_chain"}
    )
    intersection_sha = _canonical_sha(
        {"geometry": geometry_sha, "intersection_kind": "single_signal_stop_line"}
    )
    source_chain = {
        "traffic_light_regulatory_element_id": regulatory_id,
        "physical_traffic_light_id": light_way,
        "light_bulb_linestring_id": bulb_way,
        "controlled_lanelet_id": lanelet_ids[0],
        "certified_stop_line_id": stop_way,
        "certified_stop_line_geometry_m": stop_geometry,
        "route_lanelet_ids": lanelet_ids,
        "stop_line_route_arc_m": round(route_arc, 6),
    }
    return {
        "split": split,
        "map_index": map_index,
        "corridor_index": local_index,
        "route_identity_sha256": route_identity,
        "corridor_sha256": corridor_sha,
        "intersection_sha256": intersection_sha,
        "route_family_sha256": _canonical_sha(
            {"geometry": geometry_sha, "route_role": "signal_controlled_chain"}
        ),
        "source_independent_geometry_sha256": geometry_sha,
        "physical_payload": physical_payload,
        "source_chain": source_chain,
        "source_chain_sha256": _canonical_sha(source_chain),
        "route_length_m": round(sum(serialized_lengths), 6),
        "initial_pose": [
            round(serialized_centers[0][0], 6),
            round(serialized_centers[0][1], 6),
            round(serialized_initial_heading, 6),
        ],
        "goal_pose": [
            round(serialized_centers[-1][0], 6),
            round(serialized_centers[-1][1], 6),
            round(
                math.atan2(
                    serialized_centers[-1][1] - serialized_centers[-2][1],
                    serialized_centers[-1][0] - serialized_centers[-2][0],
                ),
                6,
            ),
        ],
        "phase_authority_modes_supported": list(SUPPORTED_PHASE_AUTHORITY_MODES),
        "runtime_phase_authority_frozen_in_execution_plan": False,
        "phase_remaining_available": False,
        "future_phase_schedule_consumed": False,
        "outcome_fields_consumed": [],
    }


def _validate_osm_routes(root: ET.Element, routes: list[dict[str, Any]]) -> None:
    ways = {int(element.attrib["id"]): element for element in root.findall("way")}
    relations = {
        int(element.attrib["id"]): element for element in root.findall("relation")
    }
    for row in routes:
        if (
            type(row) is not dict
            or row.get("phase_authority_modes_supported")
            != list(SUPPORTED_PHASE_AUTHORITY_MODES)
            or row.get("runtime_phase_authority_frozen_in_execution_plan") is not False
        ):
            raise ValueError("signal-complete route phase authority support drifted")
        if (
            row.get("phase_remaining_available") is not False
            or row.get("future_phase_schedule_consumed") is not False
            or row.get("outcome_fields_consumed") != []
        ):
            raise ValueError("signal-complete route contains future/outcome authority")
        chain = row.get("source_chain")
        if type(chain) is not dict or row.get("source_chain_sha256") != _canonical_sha(chain):
            raise ValueError("signal-complete route source chain drifted")
        lanelets = chain.get("route_lanelet_ids")
        if type(lanelets) is not list or len(lanelets) != 3:
            raise ValueError("signal-complete route must contain three lanelets")
        approach = relations.get(lanelets[0])
        regulatory_id = chain.get("traffic_light_regulatory_element_id")
        regulatory = relations.get(regulatory_id)
        if approach is None or regulatory is None:
            raise ValueError("signal-complete lanelet/regulatory relation missing")
        approach_members = _member_set(approach)
        if ("relation", regulatory_id, "regulatory_element") not in approach_members:
            raise ValueError("signal-complete regulatory element is not attached")
        members = _member_set(regulatory)
        required = {
            ("way", chain["certified_stop_line_id"], "ref_line"),
            ("way", chain["physical_traffic_light_id"], "refers"),
            ("way", chain["light_bulb_linestring_id"], "light_bulbs"),
        }
        if members != required:
            raise ValueError("signal-complete regulatory member chain drifted")
        stop = ways.get(chain["certified_stop_line_id"])
        light = ways.get(chain["physical_traffic_light_id"])
        bulbs = ways.get(chain["light_bulb_linestring_id"])
        if (
            _tags(stop).get("type") != "stop_line"
            or _tags(light) != {
                "height": "0.5",
                "subtype": "red_yellow_green",
                "type": "traffic_light",
            }
            or _tags(bulbs).get("type") != "light_bulbs"
            or _tags(bulbs).get("traffic_light_id") != str(chain["physical_traffic_light_id"])
        ):
            raise ValueError("signal-complete physical signal objects drifted")
        if float(row.get("route_length_m", 0.0)) < 100.0:
            raise ValueError("signal-complete route is below fixed-DP route length floor")
        if row.get("source_independent_geometry_sha256") != _canonical_sha(
            row.get("physical_payload")
        ):
            raise ValueError("signal-complete physical signature drifted")


def _strict_osm(data: bytes) -> ET.Element:
    if type(data) is not bytes or not data.endswith(b"\n"):
        raise ValueError("signal-complete OSM bytes must end in one LF")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError("signal-complete OSM is invalid XML") from exc
    if root.tag != "osm" or root.attrib.get("version") != "0.6":
        raise ValueError("signal-complete OSM root drifted")
    return root


def _offset_polyline(
    centers: tuple[tuple[float, float], ...], width: float
) -> tuple[tuple[tuple[float, float], ...], tuple[tuple[float, float], ...]]:
    edge_normals: list[tuple[float, float]] = []
    for start, end in zip(centers[:-1], centers[1:], strict=True):
        dx, dy = end[0] - start[0], end[1] - start[1]
        norm = math.hypot(dx, dy)
        if norm <= 0.0:
            raise ValueError("signal-complete route contains a zero-length edge")
        edge_normals.append((-dy / norm, dx / norm))
    normals = [edge_normals[0]]
    for previous, following in zip(edge_normals[:-1], edge_normals[1:], strict=True):
        x, y = previous[0] + following[0], previous[1] + following[1]
        norm = math.hypot(x, y)
        normals.append((x / norm, y / norm))
    normals.append(edge_normals[-1])
    half = width / 2.0
    left = tuple(
        (point[0] + normal[0] * half, point[1] + normal[1] * half)
        for point, normal in zip(centers, normals, strict=True)
    )
    right = tuple(
        (point[0] - normal[0] * half, point[1] - normal[1] * half)
        for point, normal in zip(centers, normals, strict=True)
    )
    return left, right


def _append_node(
    root: ET.Element,
    node_id: int,
    point: tuple[float, float],
    *,
    ele: float,
    tags: Mapping[str, str] | None = None,
) -> None:
    gps = _UTM_PROJECTOR.reverse(
        lanelet2.core.BasicPoint3d(float(point[0]), float(point[1]), float(ele))
    )
    node = _element(
        "node",
        {
            "id": str(node_id),
            "lat": _geo_float(gps.lat),
            "lon": _geo_float(gps.lon),
            "version": "1",
            "visible": "true",
        },
        parent=root,
    )
    merged = {"ele": _float(ele), "local_x": _float(point[0]), "local_y": _float(point[1])}
    if tags:
        merged.update(tags)
    for key in sorted(merged):
        _element("tag", {"k": key, "v": merged[key]}, parent=node)


def _append_way(
    root: ET.Element,
    way_id: int,
    node_ids: tuple[int, ...],
    tags: Mapping[str, str],
) -> None:
    way = _element(
        "way",
        {"id": str(way_id), "version": "1", "visible": "true"},
        parent=root,
    )
    for node_id in node_ids:
        _element("nd", {"ref": str(node_id)}, parent=way)
    for key in sorted(tags):
        _element("tag", {"k": key, "v": tags[key]}, parent=way)


def _append_relation(
    root: ET.Element,
    relation_id: int,
    members: tuple[tuple[str, int, str], ...],
    tags: Mapping[str, str],
) -> None:
    relation = _element(
        "relation",
        {"id": str(relation_id), "version": "1", "visible": "true"},
        parent=root,
    )
    for member_type, ref, role in members:
        _element(
            "member",
            {"ref": str(ref), "role": role, "type": member_type},
            parent=relation,
        )
    for key in sorted(tags):
        _element("tag", {"k": key, "v": tags[key]}, parent=relation)


def _element(
    tag: str,
    attributes: Mapping[str, str],
    *,
    parent: ET.Element | None = None,
) -> ET.Element:
    element = ET.Element(tag, {key: attributes[key] for key in sorted(attributes)})
    if parent is not None:
        parent.append(element)
    return element


def _member_set(element: ET.Element) -> set[tuple[str, int, str]]:
    return {
        (member.attrib["type"], int(member.attrib["ref"]), member.attrib["role"])
        for member in element.findall("member")
    }


def _tags(element: ET.Element | None) -> dict[str, str]:
    if element is None:
        return {}
    return {tag.attrib["k"]: tag.attrib["v"] for tag in element.findall("tag")}


def _lerp(
    start: tuple[float, float], end: tuple[float, float], fraction: float
) -> tuple[float, float]:
    return (
        start[0] + fraction * (end[0] - start[0]),
        start[1] + fraction * (end[1] - start[1]),
    )


def _float(value: float) -> str:
    rendered = f"{float(value):.6f}"
    if rendered == "-0.000000":
        return "0.000000"
    return rendered


def _geo_float(value: float) -> str:
    rendered = f"{float(value):.12f}"
    if rendered == "-0.000000000000":
        return "0.000000000000"
    return rendered


def _canonical_sha(value: Any) -> str:
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


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA256")
    return value
