#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence
from urllib.parse import quote


SCENARIO_REPOSITORY = "https://github.com/tier4/scenario_simulator_v2.git"
SCENARIO_COMMIT = "e22f01093fa6516c0552549ada302270329c59a4"
SOURCE_ID = "scenario_simulator_v2"
COORDINATE_QUANTIZATION_DEGREES = 1e-8
ROUTE_MIN_LENGTH_M = 80.0
TRAFFIC_CONTROL_SUBTYPES = frozenset(
    {
        "all_way_stop",
        "detection_area",
        "right_of_way",
        "speed_limit",
        "stop_sign",
        "traffic_light",
        "traffic_sign",
        "virtual_traffic_light",
    }
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return _sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    )


def _tags(element: ET.Element) -> dict[str, str]:
    return {
        tag.attrib.get("k", ""): tag.attrib.get("v", "")
        for tag in element.findall("tag")
    }


def _safe_relative_path(value: str) -> Path:
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or not parsed.parts or ".." in parsed.parts:
        raise ValueError(f"Unsafe source path: {value!r}")
    return Path(*parsed.parts)


def _validate_source(
    manifest_path: Path,
    manifest: Mapping[str, Any],
) -> tuple[Mapping[str, Any], list[Mapping[str, Any]]]:
    if manifest.get("schema") != "diffusion_planner_v23_source_freeze_v1":
        raise ValueError("Unsupported frozen source manifest schema.")
    if manifest.get("original_source_bytes_modified") is not False:
        raise ValueError("Frozen source manifest reports modified bytes.")
    sources = [
        row for row in manifest.get("sources", []) if row.get("source_id") == SOURCE_ID
    ]
    if len(sources) != 1:
        raise ValueError("Frozen manifest must contain one scenario source.")
    source = sources[0]
    if source.get("commit") != SCENARIO_COMMIT:
        raise ValueError("Manifest does not use the frozen scenario commit.")
    if source.get("repository_url") != SCENARIO_REPOSITORY:
        raise ValueError("Manifest does not use the frozen scenario repository.")
    if source.get("license_identifier") != "Apache-2.0":
        raise ValueError("Frozen scenario source is not Apache-2.0.")
    if source.get("notice_status") != "absent_at_commit":
        raise ValueError("Unexpected scenario NOTICE state at frozen commit.")

    rows = [
        row for row in manifest.get("files", []) if row.get("source_id") == SOURCE_ID
    ]
    license_rows = [row for row in rows if row.get("role") == "license"]
    if len(license_rows) != 1:
        raise ValueError("Frozen scenario source must contain one license receipt.")
    license_row = license_rows[0]
    license_path = (
        manifest_path.parent
        / "sources"
        / SOURCE_ID
        / _safe_relative_path(str(license_row["relative_path"]))
    )
    if not license_path.is_file():
        raise ValueError("Frozen scenario LICENSE payload is missing.")
    license_bytes = license_path.read_bytes()
    if (
        _sha256(license_bytes) != source.get("license_file_sha256")
        or _sha256(license_bytes) != license_row.get("file_sha256")
        or b"Apache License" not in license_bytes
        or b"Version 2.0" not in license_bytes
    ):
        raise ValueError("Frozen scenario LICENSE receipt does not match payload.")
    map_rows = [row for row in rows if row.get("role") == "map"]
    map_paths = sorted(str(row.get("relative_path", "")) for row in map_rows)
    if len(map_paths) != len(set(map_paths)):
        raise ValueError("Frozen scenario source repeats a map path receipt.")
    if source.get("map_paths") != map_paths or source.get("map_path_count") != len(
        map_paths
    ):
        raise ValueError("Frozen scenario map-path inventory does not match receipts.")
    unique_blobs = len({str(row.get("file_sha256", "")) for row in map_rows})
    if source.get("unique_map_file_sha256_count") != unique_blobs:
        raise ValueError("Frozen scenario unique-blob count does not match receipts.")
    return source, map_rows


def _geometry_and_topology(
    nodes: Mapping[str, tuple[float, float]],
    ways: Mapping[str, list[str]],
    relations: Sequence[ET.Element],
    regulatory_subtypes: Mapping[str, str],
) -> tuple[str | None, str | None]:
    if not nodes or not ways:
        return None, None
    if any(reference not in nodes for references in ways.values() for reference in references):
        return None, None

    min_lat = min(value[0] for value in nodes.values())
    min_lon = min(value[1] for value in nodes.values())
    scale = 1.0 / COORDINATE_QUANTIZATION_DEGREES
    normalized = {
        node_id: (
            round((lat - min_lat) * scale),
            round((lon - min_lon) * scale),
        )
        for node_id, (lat, lon) in nodes.items()
    }
    canonical_ways: dict[str, tuple[tuple[int, int], ...]] = {}
    for way_id, references in ways.items():
        sequence = tuple(normalized[reference] for reference in references)
        reversed_sequence = tuple(reversed(sequence))
        canonical_ways[way_id] = min(sequence, reversed_sequence)
    geometry_payload = sorted(canonical_ways.values())
    geometry_fingerprint = _canonical_sha256(geometry_payload)
    way_tokens = {
        way_id: _canonical_sha256(sequence)
        for way_id, sequence in canonical_ways.items()
    }

    lanelet_signatures = []
    for relation in relations:
        tags = _tags(relation)
        if tags.get("type") != "lanelet":
            continue
        members = []
        for member in relation.findall("member"):
            member_type = member.attrib.get("type", "")
            reference = member.attrib.get("ref", "")
            role = member.attrib.get("role", "")
            if member_type == "way":
                token = way_tokens.get(reference, "missing_way")
            elif member_type == "relation":
                token = regulatory_subtypes.get(reference, "other_relation")
            else:
                token = member_type
            members.append((member_type, role, token))
        lanelet_signatures.append(
            {
                "members": sorted(members),
                "tags": {
                    key: tags[key]
                    for key in ("location", "one_way", "subtype")
                    if key in tags
                },
            }
        )
    topology_fingerprint = _canonical_sha256(sorted(
        lanelet_signatures,
        key=lambda row: json.dumps(row, sort_keys=True),
    ))
    return geometry_fingerprint, topology_fingerprint


def _empty_map_row(source_row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "relative_path": source_row.get("relative_path"),
        "file_sha256_receipt": source_row.get("file_sha256"),
        "file_sha256_observed": None,
        "size_bytes_receipt": source_row.get("size_bytes"),
        "size_bytes_observed": None,
        "git_blob_oid": source_row.get("git_blob_oid"),
        "git_blob_sha256": source_row.get("git_blob_sha256"),
        "raw_url": source_row.get("raw_url"),
        "license_identifier": "Apache-2.0",
        "source_contract_valid": False,
        "xml_valid": False,
        "failure_reasons": [],
        "bbox": None,
        "geometry_fingerprint": None,
        "topology_fingerprint": None,
        "geometry_topology_cluster_key": None,
        "regulatory_subtype_counts": {},
        "lanelet_topology": {
            "node_count": 0,
            "way_count": 0,
            "relation_count": 0,
            "lanelet_count": 0,
            "missing_way_node_reference_count": 0,
            "missing_relation_member_reference_count": 0,
        },
        "speed_source": {
            "explicit": False,
            "lanelet_tag_values": [],
            "regulatory_element_count": 0,
            "traffic_sign_values": [],
        },
        "traffic_control_source": {
            "subtype_counts": {},
            "lanelet_attachment_count": 0,
            "attached_subtype_counts": {},
        },
        "static_map_eligible": False,
        "builder_smoke_status": "pending_fixed_builder_execution",
        "route_support_status": "pending_outcome_blind_route_census",
    }


def _census_map(
    payload_root: Path,
    source_row: Mapping[str, Any],
) -> dict[str, Any]:
    row = _empty_map_row(source_row)
    relative_path = str(source_row.get("relative_path", ""))
    source_path = payload_root / "sources" / SOURCE_ID / _safe_relative_path(
        relative_path
    )
    if not source_path.is_file():
        row["failure_reasons"].append("source_file_missing")
        return row

    payload = source_path.read_bytes()
    observed_sha = _sha256(payload)
    row["file_sha256_observed"] = observed_sha
    row["size_bytes_observed"] = len(payload)
    if observed_sha != source_row.get("file_sha256"):
        row["failure_reasons"].append("file_sha256_mismatch")
    if len(payload) != source_row.get("size_bytes"):
        row["failure_reasons"].append("size_bytes_mismatch")
    if source_row.get("commit") != SCENARIO_COMMIT:
        row["failure_reasons"].append("source_commit_mismatch")
    expected_raw_url = (
        "https://raw.githubusercontent.com/tier4/scenario_simulator_v2/"
        f"{SCENARIO_COMMIT}/{quote(relative_path)}"
    )
    if source_row.get("raw_url") != expected_raw_url:
        row["failure_reasons"].append("raw_url_mismatch")
    if len(str(source_row.get("git_blob_oid", ""))) != 40:
        row["failure_reasons"].append("git_blob_oid_invalid")
    if len(str(source_row.get("git_blob_sha256", ""))) != 64:
        row["failure_reasons"].append("git_blob_sha256_invalid")
    row["source_contract_valid"] = not row["failure_reasons"]

    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        row["failure_reasons"].append("xml_parse_error")
        return row
    row["xml_valid"] = True

    nodes: dict[str, tuple[float, float]] = {}
    coordinate_errors = 0
    for node in root.findall("node"):
        try:
            nodes[node.attrib["id"]] = (
                float(node.attrib["lat"]),
                float(node.attrib["lon"]),
            )
        except (KeyError, ValueError):
            coordinate_errors += 1
    if coordinate_errors:
        row["failure_reasons"].append("node_coordinate_missing_or_invalid")

    ways = {
        way.attrib.get("id", ""): [
            reference.attrib.get("ref", "") for reference in way.findall("nd")
        ]
        for way in root.findall("way")
    }
    relations = list(root.findall("relation"))
    relation_ids = {relation.attrib.get("id", "") for relation in relations}
    regulatory_subtypes: dict[str, str] = {}
    regulatory_counts: Counter[str] = Counter()
    for relation in relations:
        tags = _tags(relation)
        relation_id = relation.attrib.get("id", "")
        if tags.get("type") == "regulatory_element":
            subtype = tags.get("subtype", "")
            regulatory_subtypes[relation_id] = subtype
            regulatory_counts[subtype] += 1

    missing_way_refs = sum(
        reference not in nodes
        for references in ways.values()
        for reference in references
    )
    missing_relation_refs = 0
    lanelets = []
    attached_subtypes: Counter[str] = Counter()
    attachment_count = 0
    lanelet_speed_values = []
    for relation in relations:
        tags = _tags(relation)
        if tags.get("type") == "lanelet":
            lanelets.append(relation)
            for key in ("speed_limit", "speed_limit_mandatory"):
                if key in tags:
                    lanelet_speed_values.append(tags[key])
        for member in relation.findall("member"):
            if member.attrib.get("type") == "relation":
                reference = member.attrib.get("ref", "")
                if reference not in relation_ids:
                    missing_relation_refs += 1
                if (
                    tags.get("type") == "lanelet"
                    and member.attrib.get("role") == "regulatory_element"
                    and reference in regulatory_subtypes
                ):
                    attachment_count += 1
                    attached_subtypes[regulatory_subtypes[reference]] += 1

    if missing_way_refs:
        row["failure_reasons"].append("missing_way_node_reference")
    if missing_relation_refs:
        row["failure_reasons"].append("missing_relation_member_reference")
    if not lanelets:
        row["failure_reasons"].append("no_lanelets")

    if nodes:
        latitudes = [value[0] for value in nodes.values()]
        longitudes = [value[1] for value in nodes.values()]
        row["bbox"] = {
            "min_lat": min(latitudes),
            "min_lon": min(longitudes),
            "max_lat": max(latitudes),
            "max_lon": max(longitudes),
        }

    geometry, topology = _geometry_and_topology(
        nodes,
        ways,
        relations,
        regulatory_subtypes,
    )
    row["geometry_fingerprint"] = geometry
    row["topology_fingerprint"] = topology
    if geometry and topology:
        row["geometry_topology_cluster_key"] = _canonical_sha256(
            [geometry, topology]
        )
    row["regulatory_subtype_counts"] = dict(sorted(regulatory_counts.items()))
    row["lanelet_topology"] = {
        "node_count": len(root.findall("node")),
        "way_count": len(ways),
        "relation_count": len(relations),
        "lanelet_count": len(lanelets),
        "missing_way_node_reference_count": missing_way_refs,
        "missing_relation_member_reference_count": missing_relation_refs,
    }

    traffic_sign_values = []
    for relation in relations:
        tags = _tags(relation)
        if tags.get("subtype") == "traffic_sign":
            for key in ("sign_type", "traffic_sign_type"):
                if key in tags:
                    traffic_sign_values.append(tags[key])
    speed_regulatory_count = regulatory_counts.get("speed_limit", 0)
    row["speed_source"] = {
        "explicit": bool(
            lanelet_speed_values or speed_regulatory_count or traffic_sign_values
        ),
        "lanelet_tag_values": sorted(lanelet_speed_values),
        "regulatory_element_count": speed_regulatory_count,
        "traffic_sign_values": sorted(traffic_sign_values),
    }
    control_counts = {
        subtype: count
        for subtype, count in sorted(regulatory_counts.items())
        if subtype in TRAFFIC_CONTROL_SUBTYPES
    }
    row["traffic_control_source"] = {
        "subtype_counts": control_counts,
        "lanelet_attachment_count": attachment_count,
        "attached_subtype_counts": dict(sorted(attached_subtypes.items())),
    }
    row["static_map_eligible"] = bool(
        row["source_contract_valid"]
        and row["xml_valid"]
        and row["bbox"]
        and lanelets
        and not coordinate_errors
        and not missing_way_refs
        and not missing_relation_refs
        and geometry
        and topology
    )
    return row


def _clusters(
    rows: Sequence[Mapping[str, Any]],
    key: str,
) -> list[dict[str, Any]]:
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for row in rows:
        value = row.get(key)
        if value:
            grouped[str(value)].append(str(row["relative_path"]))
    return [
        {"fingerprint": fingerprint, "paths": sorted(paths)}
        for fingerprint, paths in sorted(grouped.items())
    ]


def build_static_census(
    manifest_path: Path,
    output_dir: Path,
    *,
    expected_path_count: int = 14,
    expected_unique_blob_count: int = 12,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"Output already exists: {output_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source, map_rows = _validate_source(manifest_path, manifest)
    map_rows = sorted(map_rows, key=lambda row: str(row["relative_path"]))
    unique_blob_count = len({str(row["file_sha256"]) for row in map_rows})
    if len(map_rows) != expected_path_count:
        raise ValueError(
            f"Expected {expected_path_count} map paths, found {len(map_rows)}."
        )
    if unique_blob_count != expected_unique_blob_count:
        raise ValueError(
            "Expected "
            f"{expected_unique_blob_count} unique blobs, found {unique_blob_count}."
        )

    rows = [_census_map(manifest_path.parent, row) for row in map_rows]
    geometry_clusters = _clusters(rows, "geometry_fingerprint")
    geometry_topology_clusters = _clusters(
        rows, "geometry_topology_cluster_key"
    )
    byte_blob_groups = defaultdict(list)
    for row in map_rows:
        byte_blob_groups[str(row["file_sha256"])].append(
            str(row["relative_path"])
        )
    report: dict[str, Any] = {
        "schema": "diffusion_planner_v24_lanelet2_static_census_v1",
        "source_id": SOURCE_ID,
        "repository_url": source["repository_url"],
        "commit": source["commit"],
        "license_identifier": source["license_identifier"],
        "notice_status": source["notice_status"],
        "source_manifest_path": str(manifest_path),
        "source_manifest_sha256": _sha256(manifest_path.read_bytes()),
        "map_path_count": len(rows),
        "denominator_path_count": len(rows),
        "unique_map_file_sha256_count": unique_blob_count,
        "source_valid_path_count": sum(
            bool(row["source_contract_valid"]) for row in rows
        ),
        "xml_valid_path_count": sum(bool(row["xml_valid"]) for row in rows),
        "static_map_eligible_path_count": sum(
            bool(row["static_map_eligible"]) for row in rows
        ),
        "byte_blob_groups": [
            {"file_sha256": digest, "paths": sorted(paths)}
            for digest, paths in sorted(byte_blob_groups.items())
        ],
        "coordinate_quantization_degrees": COORDINATE_QUANTIZATION_DEGREES,
        "geometry_cluster_candidates": geometry_clusters,
        "geometry_cluster_candidate_count": len(geometry_clusters),
        "geometry_topology_cluster_candidates": geometry_topology_clusters,
        "geometry_topology_cluster_candidate_count": len(
            geometry_topology_clusters
        ),
        "map_family_count": None,
        "map_family_status": "pending_reviewed_family_adjudication",
        "route_min_length_m": ROUTE_MIN_LENGTH_M,
        "maps": rows,
        "builder_smoke_started": False,
        "route_census_started": False,
        "outcome_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
    }
    output_dir.mkdir(parents=True)
    (output_dir / "census.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the outcome-blind v24 TIER IV Lanelet2 static census."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-path-count", type=int, default=14)
    parser.add_argument("--expected-unique-blob-count", type=int, default=12)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = build_static_census(
        args.manifest,
        args.output_dir,
        expected_path_count=args.expected_path_count,
        expected_unique_blob_count=args.expected_unique_blob_count,
    )
    print(
        json.dumps(
            {
                "map_path_count": report["map_path_count"],
                "unique_map_file_sha256_count": report[
                    "unique_map_file_sha256_count"
                ],
                "source_valid_path_count": report["source_valid_path_count"],
                "xml_valid_path_count": report["xml_valid_path_count"],
                "static_map_eligible_path_count": report[
                    "static_map_eligible_path_count"
                ],
                "map_family_count": report["map_family_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
