from __future__ import annotations

"""Offline, map-only CARLA route-corridor contact-tolerance census."""

import argparse
import hashlib
import importlib
import json
import math
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from importlib.metadata import version as distribution_version
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from camp_core.integrations.carla_causal_adapter import (
    _lane_surface_sample_payload,
    _opendrive_driving_lane_direction,
    _waypoint_identity,
    build_pre_generation_route_corridor,
)
from camp_core.integrations.carla_exact_speed_source import (
    canonical_json_sha256,
    freeze_lifting_tolerances,
    parse_opendrive_lane_section_bounds,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe import (
    FIXED_DP_HEAD,
    FROZEN_LIFTING_TOLERANCES,
    _deterministic_route,
    _write_json_atomic,
)


SCHEMA = "dp_camp_v20_carla_route_corridor_contact_tolerance_census_v1"
PREFLIGHT_SCHEMA = "v20_production_import_runtime_v1"
TOPOLOGY_DIAGNOSIS_SCHEMA = "dp_camp_v20_carla_predecessor_topology_diagnosis_v1"
CAMP_GATE_START_HEAD = "9537f1998100a32b74cdb6cc6dc36db4837c77f4"
EXPECTED_FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CARLA_VERSION = "0.9.16"
NUMPY_VERSION = "2.3.2"
MAP_NAME = "Carla/Maps/Town10HD_Opt"

TEST_PYTHON = "/root/autodl-tmp/camp_v19_nuplan_env/bin/python"
TEST_PYTHON_RESOLVED = "/root/autodl-tmp/camp_v19_nuplan_env/bin/python3.9"
TEST_PYTHON_VERSION = "Python 3.9.23"
TEST_PYTHON_SHA256 = (
    "d3f0bc59e0eb9c8ea292b68fcb2f0f2711491ec8a5176200494919ca7c7a0e6c"
)
CARLA_PYTHON = "/root/miniconda3/bin/python3.12"
CARLA_PYTHON_RESOLVED = CARLA_PYTHON
CARLA_PYTHON_VERSION = "Python 3.12.3"
CARLA_PYTHON_SHA256 = (
    "0c05a22b0b180580a76437114a95cf138f67c8f46245acad26017c803b42b8c1"
)
PRODUCTION_PYTHONPATH = (
    "/root/autodl-tmp/camp_v19_carla_client",
    "/root/autodl-tmp/camp_core/camp_core",
    "/root/autodl-tmp/camp_core",
)
RUNNER_MODULE = (
    "scripts.integrations."
    "census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance"
)
RUNNER_PATH = Path(
    "/root/autodl-tmp/camp_core/scripts/integrations/"
    "census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py"
)
XODR_PATH = Path(
    "/root/autodl-tmp/carla_0.9.16/runtime/CarlaUE4/Content/Carla/Maps/"
    "OpenDrive/Town10HD_Opt.xodr"
)
XODR_SHA256 = "5d883b799f634030af92be1e9d79d107845540ba04338e8c60e095be1aef7be7"
CARLA_SOURCE_ROOT_SHA256 = (
    "2d9df1315e941f60caf650fb7c8b9ea72b960bb880066355081b71eaedf912ce"
)
CARLA_SOURCE_ROOT_RECEIPT = Path(
    "/root/autodl-tmp/camp_dp_v19_carla_extraction_626cd5ae11_"
    "20260713T000320CST/ROOT_SHA256"
)
CLIENT_ROOT = Path("/root/autodl-tmp/camp_v19_carla_client")
CLIENT_MANIFEST_PATH = CLIENT_ROOT / "CLIENT_SHA256SUMS"
CLIENT_MANIFEST_SHA256 = (
    "ba3b3d97783a16211f1ed855b0c2640e58ed97fd5258cf17ff99a00037683f3e"
)
CARLA_INIT_SHA256_PREFIX = "19a6125c"
LIBCARLA_SHA256 = (
    "c99a3754561a4ac910a584cc31952a10cbc21cbe1e8b14c032c1b31d5afbb6e2"
)
BOUNDARY_KEYS = (
    "identity",
    "direction",
    "exact_entry_s",
    "exact_exit_s",
    "lookup_entry_s",
    "lookup_exit_s",
    "entry_xyz",
    "exit_xyz",
    "contact_to_next_m",
    "identity_verified",
)
EVIDENCE_KEYS = (
    "schema_version",
    "map_sha256",
    "route_sample_step_m",
    "station_allowance_m",
    "route_samples",
    "directed_edges",
    "identity_directions",
    "predecessor_receipt",
    "boundary_receipts",
    "max_contact_gap_m",
)
FORBIDDEN_COUNTERS = {
    "server_connections": 0,
    "server_launches": 0,
    "world_gets": 0,
    "actor_spawns": 0,
    "world_ticks": 0,
    "candidate_reads": 0,
    "dp_request_reads": 0,
    "dp_worker_calls": 0,
    "outcome_reads": 0,
    "metric_calls": 0,
    "future_label_reads": 0,
    "holdout_reads": 0,
    "selector_calls": 0,
    "eligibility_calls": 0,
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _route_records(route: Sequence[Any]) -> list[dict[str, object]]:
    records = []
    for waypoint in route:
        location = waypoint.transform.location
        values = (waypoint.s, location.x, location.y, location.z)
        if any(not math.isfinite(float(value)) for value in values):
            raise ValueError("route waypoint geometry must be finite")
        records.append(
            {
                "road_id": str(waypoint.road_id),
                "section_id": int(waypoint.section_id),
                "lane_id": int(waypoint.lane_id),
                "s": float(waypoint.s),
                "xyz": [float(location.x), float(location.y), float(location.z)],
            }
        )
    return records


def diagnose_route_predecessor_topology(
    *, map_api: Any, opendrive_xml: str, camp_execution_head: str
) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", camp_execution_head):
        raise ValueError("CAMP execution head must be 40 lowercase hex")
    if getattr(map_api, "name", None) != MAP_NAME:
        raise ValueError("map name mismatch")
    if _sha256_bytes(opendrive_xml.encode("utf-8")) != XODR_SHA256:
        raise ValueError("XODR SHA mismatch")

    route = _deterministic_route(
        map_api, 5.0, 81, require_unique_predecessor=False
    )
    first = route[0]
    first_identity = _waypoint_identity(first)
    first_sample = _lane_surface_sample_payload(first)
    predecessors = list(first.previous(5.0))
    predecessor_records = []
    for waypoint in predecessors:
        sample = _lane_surface_sample_payload(waypoint)
        predecessor_records.append(
            {
                "identity": [sample["road_id"], sample["section_id"], sample["lane_id"]],
                "s": sample["s"],
                "xyz": [sample[axis] for axis in ("x", "y", "z")],
                "is_junction": sample["is_junction"],
            }
        )
    predecessor_records.sort(key=_canonical_bytes)

    root = ET.fromstring(opendrive_xml)
    roads = [item for item in root.findall("road") if item.get("id") == first_identity[0]]
    if len(roads) != 1:
        raise ValueError("route-start OpenDRIVE road evidence is not unique")
    road = roads[0]
    sections = road.findall("./lanes/laneSection")
    if not 0 <= first_identity[1] < len(sections):
        raise ValueError("route-start OpenDRIVE lane-section evidence is missing")
    side = "left" if first_identity[2] > 0 else "right"
    lanes = [
        lane
        for lane in sections[first_identity[1]].findall(f"./{side}/lane")
        if lane.get("id") == str(first_identity[2])
    ]
    if len(lanes) != 1 or lanes[0].get("type") != "driving":
        raise ValueError("route-start OpenDRIVE driving-lane evidence is not unique")
    lane = lanes[0]
    direction, road_rule, lane_direction = _opendrive_driving_lane_direction(
        opendrive_xml, first_identity
    )
    entry_link_kind = "predecessor" if direction == 1 else "successor"
    at_entry_section = (
        first_identity[1] == 0
        if direction == 1
        else first_identity[1] == len(sections) - 1
    )

    def link_receipts(parent: ET.Element) -> dict[str, list[dict[str, str]]]:
        return {
            kind: [dict(sorted(node.attrib.items())) for node in parent.findall(f"./link/{kind}")]
            for kind in ("predecessor", "successor")
        }

    road_links = link_receipts(road)
    lane_links = link_receipts(lane)
    road_junction_raw = road.get("junction", "-1")
    road_junction_id = None if road_junction_raw in {"", "-1"} else road_junction_raw
    junction_connections = []
    for junction in root.findall("junction"):
        for connection in junction.findall("connection"):
            roles = [
                role
                for role in ("connectingRoad", "incomingRoad", "linkedRoad")
                if connection.get(role) == first_identity[0]
            ]
            if roles:
                junction_connections.append(
                    {
                        "junction_id": junction.get("id"),
                        "route_start_roles": roles,
                        "attributes": dict(sorted(connection.attrib.items())),
                        "lane_links": [
                            dict(sorted(item.attrib.items()))
                            for item in connection.findall("laneLink")
                        ],
                    }
                )
    junction_connections.sort(key=lambda item: _canonical_bytes(item))

    road_index: dict[str, list[ET.Element]] = {}
    for item in root.findall("road"):
        road_index.setdefault(str(item.get("id")), []).append(item)

    def boundary_driving_lane_exists(
        road_id: str, contact: str, lane_id: str
    ) -> bool:
        linked_roads = road_index.get(road_id, [])
        if len(linked_roads) != 1 or contact not in {"start", "end"}:
            return False
        linked_sections = linked_roads[0].findall("./lanes/laneSection")
        if not linked_sections:
            return False
        linked_section = linked_sections[0 if contact == "start" else -1]
        linked_side = "left" if int(lane_id) > 0 else "right"
        return (
            len(
                [
                    item
                    for item in linked_section.findall(f"./{linked_side}/lane")
                    if item.get("id") == lane_id and item.get("type") == "driving"
                ]
            )
            == 1
        )

    proofs = []
    uncertainties = []
    entry_road_nodes = road.findall(f"./link/{entry_link_kind}")
    entry_lane_nodes = lane.findall(f"./link/{entry_link_kind}")
    if not at_entry_section:
        adjacent_index = first_identity[1] - direction
        if not 0 <= adjacent_index < len(sections):
            uncertainties.append("adjacent_lane_section_missing")
        for lane_link in entry_lane_nodes:
            target_lane_id = lane_link.get("id", "")
            target_side = "left" if target_lane_id.startswith("-") is False else "right"
            target_lanes = [
                item
                for item in sections[adjacent_index].findall(f"./{target_side}/lane")
                if item.get("id") == target_lane_id and item.get("type") == "driving"
            ] if 0 <= adjacent_index < len(sections) else []
            if len(target_lanes) == 1:
                proofs.append(
                    {
                        "source": "same_road_adjacent_lane_section",
                        "road_id": first_identity[0],
                        "lane_id": target_lane_id,
                    }
                )
            else:
                uncertainties.append("adjacent_lane_link_target_not_unique_driving")
    elif len(entry_road_nodes) == 1 and entry_road_nodes[0].get("elementType") == "road":
        road_link = entry_road_nodes[0]
        target_road_id = road_link.get("elementId", "")
        contact = road_link.get("contactPoint", "")
        if not entry_lane_nodes:
            uncertainties.append("road_link_without_route_lane_link")
        for lane_link in entry_lane_nodes:
            target_lane_id = lane_link.get("id", "")
            if boundary_driving_lane_exists(target_road_id, contact, target_lane_id):
                proofs.append(
                    {
                        "source": "direct_road_and_lane_link",
                        "road_id": target_road_id,
                        "lane_id": target_lane_id,
                        "contact_point": contact,
                    }
                )
            else:
                uncertainties.append("direct_lane_link_target_not_unique_driving")
    elif entry_road_nodes or entry_lane_nodes:
        uncertainties.append("route_entry_link_not_directly_lane_resolved")

    if junction_connections:
        uncertainties.append("junction_lane_specific_predecessor_not_proven")
    proofs.sort(key=_canonical_bytes)
    uncertainties = sorted(set(uncertainties))

    bounds = next(
        (
            item
            for item in parse_opendrive_lane_section_bounds(opendrive_xml)
            if (item.road_id, item.section_id) == first_identity[:2]
        ),
        None,
    )
    if bounds is None:
        raise ValueError("route-start OpenDRIVE lane-section bounds are missing")
    entry_boundary_s = bounds.start_s if direction == 1 else bounds.end_s
    at_entry_boundary = (
        abs(first_sample["s"] - entry_boundary_s)
        <= FROZEN_LIFTING_TOLERANCES.station_epsilon_m
    )
    topology_evidence_present = bool(
        entry_road_nodes
        or entry_lane_nodes
        or junction_connections
        or road_junction_id is not None
        or not at_entry_section
    )
    explicit_predecessor = bool(proofs)
    true_root = bool(
        at_entry_boundary
        and at_entry_section
        and road_junction_id is None
        and not topology_evidence_present
    )
    cardinality = len(predecessors)
    if cardinality:
        lookup_omission = "no"
    elif explicit_predecessor:
        lookup_omission = "yes"
    elif true_root:
        lookup_omission = "no"
    else:
        lookup_omission = "undetermined"
    if cardinality == 1:
        branch = "cardinality_one_builder_implementation_check"
    elif cardinality > 1:
        branch = "ambiguity_fail_closed"
    elif true_root:
        branch = "root_boundary_no_predecessor"
    else:
        branch = "candidate_free_map_level_route_selection_only"

    route_records = _route_records(route)
    payload = {
        "schema_version": TOPOLOGY_DIAGNOSIS_SCHEMA,
        "provenance": {
            "camp_execution_head": camp_execution_head,
            "fixed_dp_head": FIXED_DP_HEAD,
            "carla_version": CARLA_VERSION,
            "map_name": MAP_NAME,
            "xodr_sha256": XODR_SHA256,
        },
        "route": {
            "point_count": len(route_records),
            "sample_step_m": 5.0,
            "sha256": canonical_json_sha256(route_records),
        },
        "route_start": {
            "identity": list(first_identity),
            "s": first_sample["s"],
            "xyz": [first_sample[axis] for axis in ("x", "y", "z")],
            "is_junction": first_sample["is_junction"],
        },
        "predecessor": {
            "cardinality": cardinality,
            "route_step_m": 5.0,
            "records": predecessor_records,
        },
        "topology": {
            "station_direction": direction,
            "road_rule": road_rule,
            "lane_direction": lane_direction,
            "road_junction_id": road_junction_id,
            "entry_link_kind": entry_link_kind,
            "entry_boundary_s": entry_boundary_s,
            "at_entry_boundary": at_entry_boundary,
            "at_entry_section": at_entry_section,
            "road_links": road_links,
            "lane_links": lane_links,
            "junction_connections": junction_connections,
            "legal_predecessor_proofs": proofs,
            "topology_uncertainties": uncertainties,
            "explicit_legal_predecessor_link": explicit_predecessor,
            "true_opendrive_topology_root": true_root,
            "lookup_omitted_legal_predecessor": lookup_omission,
        },
        "branch": branch,
        "call_counters": {"_deterministic_route": 1, "waypoint.previous": 1},
        "forbidden_access_counters": dict(FORBIDDEN_COUNTERS),
    }
    payload["receipt_sha256"] = canonical_json_sha256(payload)
    return payload


def _boundary_projection(
    corridor: Mapping[str, Any],
) -> tuple[list[dict[str, object]], list[float], float]:
    raw = corridor.get("boundary_receipts")
    if not isinstance(raw, list) or len(raw) < 2:
        raise ValueError("census requires at least two boundary identities")
    receipts = [{key: item[key] for key in BOUNDARY_KEYS} for item in raw]
    gaps = []
    for index, receipt in enumerate(receipts):
        coordinates = [*receipt["entry_xyz"], *receipt["exit_xyz"]]
        if any(not math.isfinite(float(value)) for value in coordinates):
            raise ValueError("boundary coordinates must be finite")
        gap = receipt["contact_to_next_m"]
        if index < len(receipts) - 1:
            if gap is None or not math.isfinite(float(gap)) or float(gap) < 0.0:
                raise ValueError("boundary contact is missing or nonfinite")
            gaps.append(float(gap))
        elif gap is not None:
            raise ValueError("last boundary contact must be null")
    maximum = max(gaps)
    if maximum != float(corridor["max_contact_gap_m"]):
        raise ValueError("boundary maximum does not match raw contacts")
    return receipts, gaps, maximum


def _evidence(corridor: Mapping[str, Any]) -> dict[str, object]:
    if set(corridor) != {*EVIDENCE_KEYS, "contact_tolerance_m", "corridor_sha256"}:
        raise ValueError("corridor schema changed")
    return {key: corridor[key] for key in EVIDENCE_KEYS}


def census_route_corridor_contact_tolerance(
    *,
    map_api: Any,
    opendrive_xml: str,
    camp_execution_head: str,
    carla_version: str,
    carla_module_path: str,
    carla_module_sha256: str,
    client_manifest_sha256: str,
    carla_source_root_sha256: str,
) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", camp_execution_head):
        raise ValueError("CAMP execution head must be 40 lowercase hex")
    expected = (
        (FIXED_DP_HEAD, EXPECTED_FIXED_DP_HEAD, "fixed DP head"),
        (carla_version, CARLA_VERSION, "CARLA version"),
        (carla_module_sha256, LIBCARLA_SHA256, "libcarla SHA"),
        (client_manifest_sha256, CLIENT_MANIFEST_SHA256, "client manifest SHA"),
        (carla_source_root_sha256, CARLA_SOURCE_ROOT_SHA256, "CARLA source root"),
        (getattr(map_api, "name", None), MAP_NAME, "map name"),
        (_sha256_bytes(opendrive_xml.encode("utf-8")), XODR_SHA256, "XODR SHA"),
    )
    for actual, frozen, name in expected:
        if actual != frozen:
            raise ValueError(f"{name} mismatch")

    route = _deterministic_route(map_api, 5.0, 81)
    if len(route) != 81:
        raise ValueError("deterministic route must contain 81 points")
    route_records = _route_records(route)
    measurement_ceiling = FROZEN_LIFTING_TOLERANCES.geometry_epsilon_m
    builder_kwargs = {
        "route": route,
        "map_api": map_api,
        "opendrive_xml": opendrive_xml,
        "route_sample_step_m": 5.0,
        "station_allowance_m": FROZEN_LIFTING_TOLERANCES.station_epsilon_m,
    }
    measurement = build_pre_generation_route_corridor(
        **builder_kwargs, contact_tolerance_m=measurement_ceiling
    )
    boundary_receipts, raw_gaps, maximum = _boundary_projection(measurement)
    coordinate_scale = max(
        abs(float(value))
        for receipt in boundary_receipts
        for key in ("entry_xyz", "exit_xyz")
        for value in receipt[key]
    )
    if coordinate_scale <= 0.0:
        raise ValueError("boundary coordinate scale must be positive")
    frozen = freeze_lifting_tolerances(
        max_chord_error_m=maximum,
        max_station_roundtrip_error_m=0.0,
        max_z_roundtrip_error_m=0.0,
        coordinate_scale_m=coordinate_scale,
    )
    final_tolerance = frozen.geometry_epsilon_m
    final = build_pre_generation_route_corridor(
        **builder_kwargs, contact_tolerance_m=final_tolerance
    )
    final_receipts, final_gaps, final_maximum = _boundary_projection(final)
    measurement_evidence = _evidence(measurement)
    final_evidence = _evidence(final)
    if _canonical_bytes(measurement_evidence) != _canonical_bytes(final_evidence):
        raise ValueError("corridor evidence changed between passes")
    if final_receipts != boundary_receipts or final_gaps != raw_gaps:
        raise ValueError("boundary evidence changed between passes")
    if final_maximum != maximum or final_maximum > final_tolerance:
        raise ValueError("final contact maximum is invalid")

    payload = {
        "schema_version": SCHEMA,
        "provenance": {
            "camp_gate_start_head": CAMP_GATE_START_HEAD,
            "camp_execution_head": camp_execution_head,
            "fixed_dp_head": FIXED_DP_HEAD,
            "carla_version": carla_version,
            "carla_source_root_sha256": carla_source_root_sha256,
            "carla_module_path": carla_module_path,
            "carla_module_sha256": carla_module_sha256,
            "client_manifest_sha256": client_manifest_sha256,
            "map_name": MAP_NAME,
            "xodr_sha256": XODR_SHA256,
        },
        "route": {
            "point_count": 81,
            "sample_step_m": 5.0,
            "records": route_records,
            "sha256": canonical_json_sha256(route_records),
        },
        "corridor": {
            "measurement_sha256": measurement["corridor_sha256"],
            "final_sha256": final["corridor_sha256"],
            "evidence": measurement_evidence,
            "evidence_sha256": canonical_json_sha256(measurement_evidence),
            "boundary_identity_receipts": boundary_receipts,
            "boundary_identity_receipts_sha256": canonical_json_sha256(
                boundary_receipts
            ),
            "raw_contact_gaps_m": raw_gaps,
            "max_contact_gap_m": maximum,
        },
        "tolerance": {
            "measurement_ceiling_m": measurement_ceiling,
            "coordinate_scale_m": coordinate_scale,
            "allowance_formula": "max(1e-9, 64*ulp(coordinate_scale_m))",
            "allowance_m": final_tolerance - maximum,
            "frozen_contact_tolerance_m": final_tolerance,
            "builder_contact_tolerances_m": [measurement_ceiling, final_tolerance],
        },
        "call_counters": {
            "_deterministic_route": 1,
            "build_pre_generation_route_corridor": 2,
            "freeze_lifting_tolerances": 1,
        },
        "forbidden_access_counters": dict(FORBIDDEN_COUNTERS),
    }
    payload["receipt_sha256"] = canonical_json_sha256(payload)
    return payload


def _ensure_output_absent(path: Path) -> None:
    if path.exists() or path.with_suffix(path.suffix + ".tmp").exists():
        raise FileExistsError(f"output already exists: {path}")


def _verified_runtime_identity() -> dict[str, Any]:
    if sys.executable != CARLA_PYTHON:
        raise ValueError("production runner must use exact CARLA_PYTHON")
    if os.environ.get("PYTHONPATH") != os.pathsep.join(PRODUCTION_PYTHONPATH):
        raise ValueError("exact production PYTHONPATH is not active")
    expected = (
        (
            "TEST_PYTHON",
            Path(TEST_PYTHON),
            Path(TEST_PYTHON_RESOLVED),
            TEST_PYTHON_VERSION,
            TEST_PYTHON_SHA256,
        ),
        (
            "CARLA_PYTHON",
            Path(CARLA_PYTHON),
            Path(CARLA_PYTHON_RESOLVED),
            CARLA_PYTHON_VERSION,
            CARLA_PYTHON_SHA256,
        ),
    )
    receipts = {}
    for name, path, resolved, version, sha256 in expected:
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError(f"{name} is not executable")
        if path.resolve(strict=True) != resolved:
            raise ValueError(f"{name} resolved path mismatch")
        if _sha256_path(resolved) != sha256:
            raise ValueError(f"{name} SHA256 mismatch")
        if name == "CARLA_PYTHON":
            actual_version = (
                f"Python {sys.version_info.major}.{sys.version_info.minor}."
                f"{sys.version_info.micro}"
            )
        else:
            completed = subprocess.run(
                [str(path), "--version"],
                check=True,
                capture_output=True,
                text=True,
            )
            actual_version = (completed.stdout or completed.stderr).strip()
        if actual_version != version:
            raise ValueError(f"{name} version mismatch")
        receipts[name.lower()] = {
            "path": str(path),
            "resolved": str(resolved),
            "version": actual_version,
            "sha256": sha256,
        }
    resolved_sys_path = {
        str(Path(entry).resolve()) for entry in sys.path if entry
    }
    if not set(PRODUCTION_PYTHONPATH).issubset(resolved_sys_path):
        raise ValueError("exact production PYTHONPATH is not active")
    return receipts


def _verified_client_manifest() -> dict[str, str]:
    entries = {}
    for line in CLIENT_MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        if match is None:
            raise ValueError("malformed client manifest line")
        sha256, relative_text = match.groups()
        relative = PurePosixPath(relative_text)
        if (
            relative.is_absolute()
            or relative.as_posix() != relative_text
            or not relative.parts
            or any(part in {"", ".", ".."} for part in relative.parts)
            or "\\" in relative_text
        ):
            raise ValueError("client manifest path must be normalized and relative")
        if relative_text in entries:
            raise ValueError("duplicate client manifest path")
        entries[relative_text] = sha256
    if len(entries) != 16:
        raise ValueError("client manifest must contain exactly 16 entries")

    actual_files = set()
    for path in CLIENT_ROOT.rglob("*"):
        if path.is_symlink():
            raise ValueError("sealed client must not contain symlinks")
        if path.is_file() and path != CLIENT_MANIFEST_PATH:
            actual_files.add(path.relative_to(CLIENT_ROOT).as_posix())
    if set(entries) != actual_files:
        raise ValueError("client manifest file set mismatch")
    for relative_text, expected_sha256 in entries.items():
        path = CLIENT_ROOT.joinpath(*PurePosixPath(relative_text).parts)
        if _sha256_path(path) != expected_sha256:
            raise ValueError(f"client file SHA256 mismatch: {relative_text}")
    return dict(sorted(entries.items()))


def _verified_provenance() -> dict[str, Any]:
    opendrive_xml = XODR_PATH.read_text(encoding="utf-8")
    if _sha256_bytes(opendrive_xml.encode("utf-8")) != XODR_SHA256:
        raise ValueError("official XODR SHA mismatch")
    if _sha256_path(CLIENT_MANIFEST_PATH) != CLIENT_MANIFEST_SHA256:
        raise ValueError("CARLA client manifest SHA mismatch")
    client_manifest_entries = _verified_client_manifest()
    source_root = CARLA_SOURCE_ROOT_RECEIPT.read_text(encoding="utf-8").split()[0]
    if source_root != CARLA_SOURCE_ROOT_SHA256:
        raise ValueError("CARLA source-root receipt mismatch")
    modules = sorted(CLIENT_ROOT.rglob("libcarla.cpython-312-x86_64-linux-gnu.so"))
    if len(modules) != 1:
        raise ValueError("sealed client must contain exactly one cp312 libcarla")
    module_path = modules[0].resolve()
    if _sha256_path(module_path) != LIBCARLA_SHA256:
        raise ValueError("libcarla SHA mismatch")
    module_relative = module_path.relative_to(CLIENT_ROOT.resolve()).as_posix()
    if client_manifest_entries.get(module_relative) != LIBCARLA_SHA256:
        raise ValueError("libcarla manifest entry mismatch")
    init_path = (CLIENT_ROOT / "carla/__init__.py").resolve()
    init_relative = init_path.relative_to(CLIENT_ROOT.resolve()).as_posix()
    init_sha256 = client_manifest_entries.get(init_relative)
    if init_sha256 is None:
        raise ValueError("carla/__init__.py missing from client manifest")
    if not init_sha256.startswith(CARLA_INIT_SHA256_PREFIX):
        raise ValueError("carla/__init__.py manifest SHA prefix mismatch")
    return {
        "opendrive_xml": opendrive_xml,
        "carla_version": CARLA_VERSION,
        "carla_init_path": str(init_path),
        "carla_init_sha256": init_sha256,
        "carla_module_path": str(module_path),
        "carla_module_sha256": LIBCARLA_SHA256,
        "client_manifest_sha256": CLIENT_MANIFEST_SHA256,
        "client_manifest_entries": client_manifest_entries,
        "carla_source_root_sha256": source_root,
        "xodr_sha256": XODR_SHA256,
    }


def _load_sealed_carla(provenance: Mapping[str, Any]):
    carla = importlib.import_module("carla")
    libcarla = importlib.import_module("carla.libcarla")
    if distribution_version("carla") != CARLA_VERSION:
        raise ValueError("CARLA distribution version mismatch")
    init_path = Path(carla.__file__).resolve()
    sealed_init_path = Path(provenance["carla_init_path"])
    if init_path != sealed_init_path:
        raise ValueError("imported carla init path mismatch")
    if _sha256_path(init_path) != provenance["carla_init_sha256"]:
        raise ValueError("imported carla init SHA256 mismatch")
    package_paths = [Path(path).resolve() for path in carla.__path__]
    if package_paths != [sealed_init_path.parent]:
        raise ValueError("imported carla package path mismatch")
    module_path = Path(libcarla.__file__).resolve()
    if module_path != Path(provenance["carla_module_path"]):
        raise ValueError("imported libcarla path mismatch")
    if _sha256_path(module_path) != provenance["carla_module_sha256"]:
        raise ValueError("imported libcarla SHA256 mismatch")
    if carla.Map is not libcarla.Map:
        raise ValueError("carla.Map identity mismatch")
    return carla


def _production_import_evidence() -> dict[str, Any]:
    if "carla" in sys.modules:
        raise ValueError("carla imported before sealed production check")
    runner = importlib.import_module(RUNNER_MODULE)
    numpy = importlib.import_module("numpy")
    builder = importlib.import_module("camp_core.integrations.carla_causal_adapter")
    freezer = importlib.import_module("camp_core.integrations.carla_exact_speed_source")
    probe = importlib.import_module(
        "scripts.integrations."
        "run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe"
    )
    if "carla" in sys.modules:
        raise ValueError("production dependency import pulled in carla")
    modules = {
        "runner": runner,
        "numpy": numpy,
        "builder": builder,
        "freezer": freezer,
        "probe": probe,
    }
    module_paths = {
        name: str(Path(module.__file__).resolve()) for name, module in modules.items()
    }
    expected_paths = {
        "runner": str(RUNNER_PATH),
        "builder": (
            "/root/autodl-tmp/camp_core/camp_core/camp_core/integrations/"
            "carla_causal_adapter.py"
        ),
        "freezer": (
            "/root/autodl-tmp/camp_core/camp_core/camp_core/integrations/"
            "carla_exact_speed_source.py"
        ),
        "probe": (
            "/root/autodl-tmp/camp_core/scripts/integrations/"
            "run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe.py"
        ),
    }
    if {name: module_paths[name] for name in expected_paths} != expected_paths:
        raise ValueError("production module path mismatch")
    if numpy.__version__ != NUMPY_VERSION:
        raise ValueError("NumPy version mismatch")
    callables = {
        "census": callable(runner.census_route_corridor_contact_tolerance),
        "diagnosis": callable(runner.diagnose_route_predecessor_topology),
        "main": callable(runner.main),
        "builder": callable(builder.build_pre_generation_route_corridor),
        "freezer": callable(freezer.freeze_lifting_tolerances),
        "route": callable(probe._deterministic_route),
        "atomic_writer": callable(probe._write_json_atomic),
    }
    if not all(callables.values()):
        raise ValueError("production callable contract mismatch")
    return {
        "module_paths": module_paths,
        "module_sha256": {
            name: _sha256_path(Path(path)) for name, path in module_paths.items()
        },
        "versions": {"numpy": numpy.__version__},
        "callables": callables,
        "carla_absent_until_sealed_libcarla_check": True,
    }


def _production_preflight_receipt() -> dict[str, Any]:
    runtime = _verified_runtime_identity()
    provenance = _verified_provenance()
    production_import = _production_import_evidence()
    _load_sealed_carla(provenance)
    return {
        "schema_version": PREFLIGHT_SCHEMA,
        "runtime": runtime,
        "provenance": _public_provenance(provenance),
        "production_import": production_import,
        "no_map": True,
        "no_census": True,
        "no_server": True,
    }


def _public_provenance(provenance: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in provenance.items() if key != "opendrive_xml"}


def _verified_preflight_receipt(path: Path) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    expected_keys = {
        "schema_version",
        "runtime",
        "provenance",
        "production_import",
        "no_map",
        "no_census",
        "no_server",
    }
    if not isinstance(receipt, dict) or set(receipt) != expected_keys:
        raise ValueError("preflight receipt schema mismatch")
    if receipt["schema_version"] != PREFLIGHT_SCHEMA:
        raise ValueError("preflight receipt schema version mismatch")
    for key in ("runtime", "provenance", "production_import"):
        if not isinstance(receipt[key], dict):
            raise ValueError(f"preflight {key} must be an object")
    for key in ("no_map", "no_census", "no_server"):
        if receipt[key] is not True:
            raise ValueError(f"preflight {key} must be true")
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--diagnose-predecessor-topology-only", action="store_true")
    parser.add_argument("--preflight-json", type=Path)
    parser.add_argument("--camp-head")
    parser.add_argument("--output-json", required=True, type=Path)
    args = parser.parse_args(argv)
    _ensure_output_absent(args.output_json)
    if args.preflight_only and args.diagnose_predecessor_topology_only:
        raise ValueError("preflight and topology diagnosis modes are exclusive")

    if args.preflight_only:
        receipt = _production_preflight_receipt()
    else:
        if args.camp_head is None:
            raise ValueError("--camp-head is required for census execution")
        if args.preflight_json is None:
            raise ValueError("--preflight-json is required for census execution")
        preflight = _verified_preflight_receipt(args.preflight_json)
        runtime = _verified_runtime_identity()
        provenance = _verified_provenance()
        production_import = _production_import_evidence()
        current = {
            "runtime": runtime,
            "provenance": _public_provenance(provenance),
            "production_import": production_import,
        }
        for key, value in current.items():
            if preflight[key] != value:
                raise ValueError(f"preflight {key} mismatch")
        carla = _load_sealed_carla(provenance)
        map_api = carla.Map(MAP_NAME, provenance["opendrive_xml"])
        if args.diagnose_predecessor_topology_only:
            receipt = diagnose_route_predecessor_topology(
                map_api=map_api,
                opendrive_xml=provenance["opendrive_xml"],
                camp_execution_head=args.camp_head,
            )
        else:
            receipt = census_route_corridor_contact_tolerance(
                map_api=map_api,
                opendrive_xml=provenance["opendrive_xml"],
                camp_execution_head=args.camp_head,
                carla_version=provenance["carla_version"],
                carla_module_path=provenance["carla_module_path"],
                carla_module_sha256=provenance["carla_module_sha256"],
                client_manifest_sha256=provenance["client_manifest_sha256"],
                carla_source_root_sha256=provenance["carla_source_root_sha256"],
            )
    _write_json_atomic(args.output_json, receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
