#!/usr/bin/env python3
"""Independently review a sealed V25 signal-complete map artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)


SCHEMA_VERSION = "camp_dp_v25_signal_complete_map_review_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PLAN = {
    "calibration": {"map_count": 5, "routes_per_map": 10},
    "fresh_b2": {"map_count": 25, "routes_per_map": 4},
    "fresh_b3": {"map_count": 25, "routes_per_map": 4},
}
GENERATOR_SOURCE = (
    PACKAGE_ROOT
    / "camp_core"
    / "integrations"
    / "diffusion_planner_v25_signal_complete_maps.py"
)


def review(artifact: Path, expected_root: str) -> dict[str, Any]:
    root = artifact.resolve()
    seal = verify_complete_seal(root, expected_root, label="signal-complete maps")
    if (root / "run.exit").read_bytes() != b"0\n":
        raise ValueError("signal-complete map artifact exit drifted")
    report = _canonical_json(root / "report.json")
    suite = _canonical_json(root / "signal_complete_suite.json")
    license_receipt = _canonical_json(root / "LICENSE_RECEIPT.json")
    split = suite.get("split")
    if split not in PLAN:
        raise ValueError("signal-complete suite split drifted")
    plan = PLAN[split]
    exact_paths = {
        "COMMAND",
        "HEADS",
        "LICENSE_RECEIPT.json",
        "report.json",
        "run.exit",
        "signal_complete_suite.json",
    }
    expected_map_paths = {
        f"project_authored_signal_complete/{split}/map_{index:02d}/lanelet2_map.osm"
        for index in range(plan["map_count"])
    }
    if set(seal["manifest_paths"]) != exact_paths | expected_map_paths:
        raise ValueError("signal-complete map artifact inventory drifted")
    expected_heads = (
        f"camp_head={report.get('camp_head')}\nfixed_dp_head={FIXED_DP_HEAD}\n"
    ).encode("ascii")
    if (root / "HEADS").read_bytes() != expected_heads:
        raise ValueError("signal-complete map HEADS drifted")
    expected_report = {
        "schema_version": "camp_dp_v25_signal_complete_map_artifact_v1",
        "status": "passed_signal_complete_map_materialization",
        "camp_head": report.get("camp_head"),
        "fixed_dp_head": FIXED_DP_HEAD,
        "split": split,
        "suite_schema_version": "camp_dp_v25_project_authored_signal_complete_suite_v3",
        "suite_sha256": _sha256(root / "signal_complete_suite.json"),
        "map_count": plan["map_count"],
        "corridor_count": plan["map_count"] * plan["routes_per_map"],
        "route_count": plan["map_count"] * plan["routes_per_map"],
        "generator_source": str(GENERATOR_SOURCE.resolve()),
        "generator_source_sha256": _sha256(GENERATOR_SOURCE),
        "license_receipt_sha256": _sha256(root / "LICENSE_RECEIPT.json"),
        "fixed_dp_modified": False,
        "candidate_tensor_modified": False,
        "model_loaded": False,
        "candidate_generation_executed": False,
        "training_executed": False,
        "calibration_outcomes_consumed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    if not _strict_equal(report, expected_report):
        raise ValueError("signal-complete map report drifted")
    expected_license = {
        "schema_version": "camp_dp_v25_project_authored_map_license_receipt_v1",
        "spdx": "MIT",
        "repository_license_path": str((ROOT / "LICENSE").resolve()),
        "repository_license_sha256": _sha256(ROOT / "LICENSE"),
        "third_party_map_payload_derived": False,
    }
    if not _strict_equal(license_receipt, expected_license):
        raise ValueError("signal-complete map license receipt drifted")
    _review_suite(root, suite, plan)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_signal_complete_map_review",
        "reviewed_artifact": str(root),
        "reviewed_root_sha256": seal["root_sha256"],
        "camp_head": report["camp_head"],
        "fixed_dp_head": FIXED_DP_HEAD,
        "split": split,
        "map_count": report["map_count"],
        "corridor_count": report["corridor_count"],
        "route_count": report["route_count"],
        "all_regulatory_chains_recomputed": True,
        "source_independent_geometry_clone_count": 0,
        "same_tick_phase_required": True,
        "phase_authority_modes_supported": [
            "controlled_same_tick_override",
            "observe_same_tick_request",
        ],
        "phase_remaining_available": False,
        "future_phase_schedule_consumed": False,
        "outcome_fields_consumed": [],
        "fresh_b2_opened": False,
    }


def _review_suite(root: Path, suite: dict[str, Any], plan: dict[str, int]) -> None:
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
    if set(suite) != expected_fields:
        raise ValueError("signal-complete suite receipt field set drifted")
    exact = {
        "schema_version": "camp_dp_v25_project_authored_signal_complete_suite_v3",
        "status": "outcome_blind_signal_complete_suite_materialized",
        "source_family": "project_authored_mit_deterministic_lanelet2",
        "map_count": plan["map_count"],
        "corridor_count": plan["map_count"] * plan["routes_per_map"],
        "route_count": plan["map_count"] * plan["routes_per_map"],
        "same_tick_phase_required": True,
        "phase_authority_modes_supported": [
            "controlled_same_tick_override",
            "observe_same_tick_request",
        ],
        "phase_remaining_available": False,
        "future_phase_schedule_consumed": False,
        "outcome_fields_consumed": [],
        "fresh_b2_opened": False,
        "fixed_dp_modified": False,
        "candidate_tensor_modified": False,
    }
    for name, expected in exact.items():
        if type(suite.get(name)) is not type(expected) or suite.get(name) != expected:
            raise ValueError(f"signal-complete suite {name} drifted")
    if suite.get("license") != {
        "spdx": "MIT",
        "provenance": "project_authored_from_first_principles",
        "repository_license_path": "LICENSE",
        "third_party_map_payload_derived": False,
    }:
        raise ValueError("signal-complete suite license drifted")
    maps = suite.get("maps")
    if type(maps) is not list or len(maps) != plan["map_count"]:
        raise ValueError("signal-complete suite map count drifted")
    geometry_hashes: list[str] = []
    corridor_hashes: set[str] = set()
    route_hashes: set[str] = set()
    for map_index, map_receipt in enumerate(maps):
        if type(map_receipt) is not dict:
            raise ValueError("signal-complete map receipt must be a mapping")
        path = root / str(map_receipt.get("relative_path"))
        if (
            map_receipt.get("schema_version")
            != "camp_dp_v25_project_authored_lanelet2_signal_map_v3"
            or map_receipt.get("map_index") != map_index
            or map_receipt.get("split") != suite["split"]
            or map_receipt.get("map_sha256") != _sha256(path)
            or map_receipt.get("map_geometry_sha256")
            != _canonical_sha(
                sorted(
                    row.get("source_independent_geometry_sha256")
                    for row in map_receipt.get("routes", [])
                )
            )
            or map_receipt.get("route_count") != plan["routes_per_map"]
            or map_receipt.get("runtime_phase_embedded") is not False
            or map_receipt.get("future_schedule_embedded") is not False
            or map_receipt.get("outcome_fields_consumed") != []
        ):
            raise ValueError("signal-complete map receipt drifted")
        xml_root = _strict_xml(path)
        ways = {int(way.attrib["id"]): way for way in xml_root.findall("way")}
        relations = {
            int(relation.attrib["id"]): relation
            for relation in xml_root.findall("relation")
        }
        routes = map_receipt.get("routes")
        if type(routes) is not list or len(routes) != plan["routes_per_map"]:
            raise ValueError("signal-complete map route count drifted")
        for route_index, row in enumerate(routes):
            geometry = _canonical_sha(row.get("physical_payload"))
            if row.get("source_independent_geometry_sha256") != geometry:
                raise ValueError("signal-complete route physical signature drifted")
            chain = row.get("source_chain")
            if type(chain) is not dict or row.get("source_chain_sha256") != _canonical_sha(chain):
                raise ValueError("signal-complete route chain SHA drifted")
            route_identity = _canonical_sha(
                {
                    "geometry": geometry,
                    "split": suite["split"],
                    "map_index": map_index,
                    "route_index": route_index,
                }
            )
            corridor = _canonical_sha(
                {"geometry": geometry, "corridor_kind": "single_signal_route_chain"}
            )
            intersection = _canonical_sha(
                {"geometry": geometry, "intersection_kind": "single_signal_stop_line"}
            )
            if (
                row.get("route_identity_sha256") != route_identity
                or row.get("corridor_sha256") != corridor
                or row.get("intersection_sha256") != intersection
                or route_identity in route_hashes
                or corridor in corridor_hashes
                or geometry in geometry_hashes
            ):
                raise ValueError("signal-complete route/corridor/clone identity drifted")
            geometry_hashes.append(geometry)
            route_hashes.add(route_identity)
            corridor_hashes.add(corridor)
            _review_chain(row, chain, ways, relations)
    if suite["source_independent_geometry_sha256"] != sorted(geometry_hashes):
        raise ValueError("signal-complete geometry inventory drifted")


def _review_chain(
    row: dict[str, Any],
    chain: dict[str, Any],
    ways: dict[int, ET.Element],
    relations: dict[int, ET.Element],
) -> None:
    if (
        row.get("phase_authority_modes_supported")
        != ["controlled_same_tick_override", "observe_same_tick_request"]
        or row.get("runtime_phase_authority_frozen_in_execution_plan") is not False
        or row.get("phase_remaining_available") is not False
        or row.get("future_phase_schedule_consumed") is not False
        or row.get("outcome_fields_consumed") != []
        or type(row.get("route_length_m")) not in (int, float)
        or float(row["route_length_m"]) < 100.0
    ):
        raise ValueError("signal-complete route runtime-source contract drifted")
    lanelets = chain.get("route_lanelet_ids")
    if type(lanelets) is not list or len(lanelets) != 3:
        raise ValueError("signal-complete route lanelet chain drifted")
    regulatory_id = chain.get("traffic_light_regulatory_element_id")
    approach = relations.get(lanelets[0])
    regulatory = relations.get(regulatory_id)
    if approach is None or regulatory is None:
        raise ValueError("signal-complete route relation is missing")
    if (
        "relation",
        regulatory_id,
        "regulatory_element",
    ) not in _members(approach):
        raise ValueError("signal-complete regulatory relation is unattached")
    required = {
        ("way", chain.get("certified_stop_line_id"), "ref_line"),
        ("way", chain.get("physical_traffic_light_id"), "refers"),
        ("way", chain.get("light_bulb_linestring_id"), "light_bulbs"),
    }
    if _members(regulatory) != required:
        raise ValueError("signal-complete regulatory member roles drifted")
    stop = ways.get(chain.get("certified_stop_line_id"))
    light = ways.get(chain.get("physical_traffic_light_id"))
    bulbs = ways.get(chain.get("light_bulb_linestring_id"))
    if (
        _tags(stop).get("type") != "stop_line"
        or _tags(light).get("type") != "traffic_light"
        or _tags(bulbs).get("type") != "light_bulbs"
        or _tags(bulbs).get("traffic_light_id")
        != str(chain.get("physical_traffic_light_id"))
    ):
        raise ValueError("signal-complete physical signal chain drifted")


def _canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"authority JSON is not UTF-8: {path}") from exc
    def no_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        value = json.loads(
            text,
            object_pairs_hook=no_duplicate,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"nonfinite JSON token: {token}")
            ),
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"authority JSON is invalid: {path}") from exc
    if type(value) is not dict:
        raise ValueError(f"authority JSON must be a mapping: {path}")
    expected = (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    if raw != expected:
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


def _strict_xml(path: Path) -> ET.Element:
    data = path.read_bytes()
    if not data.endswith(b"\n") or data.endswith(b"\n\n"):
        raise ValueError("signal-complete OSM byte ending drifted")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError("signal-complete OSM XML is invalid") from exc
    if root.tag != "osm" or root.attrib.get("version") != "0.6":
        raise ValueError("signal-complete OSM root drifted")
    return root


def _members(element: ET.Element) -> set[tuple[str, int, str]]:
    return {
        (member.attrib["type"], int(member.attrib["ref"]), member.attrib["role"])
        for member in element.findall("member")
    }


def _tags(element: ET.Element | None) -> dict[str, str]:
    if element is None:
        return {}
    return {tag.attrib["k"]: tag.attrib["v"] for tag in element.findall("tag")}


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(
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
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = review(args.artifact, args.root_sha256)
        _write_json(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_bytes(
            f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n".encode(
                "ascii"
            )
        )
        (args.output_dir / "COMMAND").write_bytes(
            (" ".join(sys.argv) + "\n").encode("utf-8")
        )
        (args.output_dir / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(args.output_dir, label="V25 signal-complete map review")
        print(json.dumps({"status": report["status"], "root_sha256": root}, sort_keys=True))
    except BaseException as exc:
        _write_json(
            args.output_dir / "failure.json",
            {"schema_version": SCHEMA_VERSION, "status": "failed", "reason": str(exc)},
        )
        (args.output_dir / "run.exit").write_bytes(b"1\n")
        seal_artifact(args.output_dir, label="failed V25 signal-complete map review")
        raise


if __name__ == "__main__":
    main()
