#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


SCHEMA = "diffusion_planner_v24_map_family_adjudication_v1"
SOURCE_ID = "scenario_simulator_v2"
BBOX_CONTAINMENT_THRESHOLD = 0.98
SEGMENT_CONTAINMENT_THRESHOLD = 0.80
COORDINATE_SCALE = 100_000_000


def _safe_relative_path(value: str) -> Path:
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or not parsed.parts or ".." in parsed.parts:
        raise ValueError(f"Unsafe source path: {value!r}")
    return Path(*parsed.parts)


def _sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _bbox_containment(
    left: Mapping[str, float],
    right: Mapping[str, float],
) -> float:
    intersection_lat = max(
        0.0,
        min(left["max_lat"], right["max_lat"])
        - max(left["min_lat"], right["min_lat"]),
    )
    intersection_lon = max(
        0.0,
        min(left["max_lon"], right["max_lon"])
        - max(left["min_lon"], right["min_lon"]),
    )
    intersection = intersection_lat * intersection_lon
    left_area = (left["max_lat"] - left["min_lat"]) * (
        left["max_lon"] - left["min_lon"]
    )
    right_area = (right["max_lat"] - right["min_lat"]) * (
        right["max_lon"] - right["min_lon"]
    )
    denominator = min(left_area, right_area)
    return intersection / denominator if denominator > 0 else 0.0


def _absolute_segments(map_path: Path) -> set[tuple[tuple[int, int], tuple[int, int]]]:
    root = ET.fromstring(map_path.read_bytes())
    nodes: dict[str, tuple[int, int]] = {}
    for node in root.findall("node"):
        try:
            nodes[node.attrib["id"]] = (
                round(float(node.attrib["lat"]) * COORDINATE_SCALE),
                round(float(node.attrib["lon"]) * COORDINATE_SCALE),
            )
        except (KeyError, ValueError):
            continue

    segments: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    for way in root.findall("way"):
        coordinates = [
            nodes.get(reference.attrib.get("ref", ""))
            for reference in way.findall("nd")
        ]
        for start, end in zip(coordinates, coordinates[1:]):
            if start is not None and end is not None and start != end:
                segments.add(tuple(sorted((start, end))))
    return segments


def _segment_containment(
    left: set[tuple[tuple[int, int], tuple[int, int]]],
    right: set[tuple[tuple[int, int], tuple[int, int]]],
) -> float:
    denominator = min(len(left), len(right))
    return len(left & right) / denominator if denominator else 0.0


def _connected_components(
    nodes: Sequence[str],
    edges: Sequence[tuple[str, str]],
) -> list[list[str]]:
    neighbours = {node: set() for node in nodes}
    for left, right in edges:
        neighbours[left].add(right)
        neighbours[right].add(left)

    components = []
    unseen = set(nodes)
    while unseen:
        start = min(unseen)
        stack = [start]
        component = []
        unseen.remove(start)
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbour in sorted(neighbours[node], reverse=True):
                if neighbour in unseen:
                    unseen.remove(neighbour)
                    stack.append(neighbour)
        components.append(sorted(component))
    return sorted(components, key=lambda component: component[0])


def _split_regime(loadable_family_count: int) -> str:
    if loadable_family_count >= 3:
        return "map_family_level_train_calibration_holdout"
    if loadable_family_count == 2:
        return "unseen_map_holdout_plus_corridor_train_calibration"
    if loadable_family_count == 1:
        return "corridor_group_within_family_no_unseen_map_claim"
    return "no_loadable_map_family"


def adjudicate_map_families(
    census_path: Path,
    builder_smoke_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    census_path = Path(census_path)
    builder_smoke_path = Path(builder_smoke_path)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"Output already exists: {output_dir}")

    census = json.loads(census_path.read_text(encoding="utf-8"))
    builder = json.loads(builder_smoke_path.read_text(encoding="utf-8"))
    if census.get("schema") != "diffusion_planner_v24_lanelet2_static_census_v1":
        raise ValueError("Unsupported v24 static census schema.")
    if builder.get("schema") != "diffusion_planner_v24_lanelet2_builder_smoke_v1":
        raise ValueError("Unsupported v24 builder-smoke schema.")

    maps = list(census.get("maps", []))
    map_by_path = {str(row["relative_path"]): row for row in maps}
    if len(map_by_path) != len(maps):
        raise ValueError("Static census contains duplicate map paths.")
    builder_by_path = {
        str(row["relative_path"]): row for row in builder.get("path_receipts", [])
    }
    if set(builder_by_path) != set(map_by_path):
        raise ValueError("Builder-smoke denominator differs from static census.")
    if any(row.get("source_bytes_unchanged") is not True for row in builder_by_path.values()):
        raise ValueError("Builder smoke did not preserve every source map.")

    manifest_path = Path(str(census["source_manifest_path"]))
    source_root = manifest_path.parent / "sources" / SOURCE_ID
    paths_by_blob: defaultdict[str, list[str]] = defaultdict(list)
    for relative_path, row in map_by_path.items():
        paths_by_blob[str(row["file_sha256_receipt"])].append(relative_path)

    blob_data: dict[str, dict[str, Any]] = {}
    unassigned_paths = []
    for digest, relative_paths in sorted(paths_by_blob.items()):
        representative = sorted(relative_paths)[0]
        row = map_by_path[representative]
        bbox = row.get("bbox")
        map_path = source_root / _safe_relative_path(representative)
        segments = _absolute_segments(map_path) if bbox and map_path.is_file() else set()
        if not bbox or not segments:
            unassigned_paths.extend(
                {
                    "relative_path": relative_path,
                    "reason": "no_geometry_or_bbox",
                }
                for relative_path in sorted(relative_paths)
            )
            continue
        blob_data[digest] = {
            "bbox": bbox,
            "paths": sorted(relative_paths),
            "segments": segments,
        }

    edge_pairs: list[tuple[str, str]] = []
    pairwise_receipts = []
    digests = sorted(blob_data)
    for index, left_digest in enumerate(digests):
        for right_digest in digests[index + 1 :]:
            left = blob_data[left_digest]
            right = blob_data[right_digest]
            bbox_score = _bbox_containment(left["bbox"], right["bbox"])
            segment_score = _segment_containment(
                left["segments"], right["segments"]
            )
            edge = bool(
                bbox_score >= BBOX_CONTAINMENT_THRESHOLD
                and segment_score >= SEGMENT_CONTAINMENT_THRESHOLD
            )
            if edge:
                edge_pairs.append((left_digest, right_digest))
            pairwise_receipts.append(
                {
                    "left_blob_sha256": left_digest,
                    "right_blob_sha256": right_digest,
                    "bbox_containment": bbox_score,
                    "absolute_segment_containment": segment_score,
                    "family_edge": edge,
                }
            )

    families = []
    for component in _connected_components(digests, edge_pairs):
        paths = sorted(
            path for digest in component for path in blob_data[digest]["paths"]
        )
        loadable_paths = sorted(
            path for path in paths if builder_by_path[path].get("status") == "loaded"
        )
        failed_paths = sorted(set(paths) - set(loadable_paths))
        families.append(
            {
                "family_id": f"map_family_{_sha256(component)[:12]}",
                "blob_sha256s": component,
                "paths": paths,
                "loadable": bool(loadable_paths),
                "loadable_paths": loadable_paths,
                "failed_paths": failed_paths,
            }
        )
    families.sort(key=lambda family: family["paths"])
    loadable_family_count = sum(bool(family["loadable"]) for family in families)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "source_id": census.get("source_id"),
        "source_commit": census.get("commit"),
        "census_path": str(census_path),
        "builder_smoke_path": str(builder_smoke_path),
        "map_path_count": len(maps),
        "unique_map_file_sha256_count": len(paths_by_blob),
        "assigned_path_count": sum(len(family["paths"]) for family in families),
        "unassigned_path_count": len(unassigned_paths),
        "map_family_count": len(families),
        "loadable_map_family_count": loadable_family_count,
        "loadable_path_count": sum(
            builder_by_path[path].get("status") == "loaded" for path in map_by_path
        ),
        "thresholds": {
            "bbox_containment_min": BBOX_CONTAINMENT_THRESHOLD,
            "absolute_segment_containment_min": SEGMENT_CONTAINMENT_THRESHOLD,
            "coordinate_quantization_degrees": 1 / COORDINATE_SCALE,
        },
        "edge_inputs": "absolute_map_geometry_only",
        "builder_status_role": "loadability_label_only_never_family_edge",
        "families": families,
        "unassigned_paths": sorted(
            unassigned_paths, key=lambda row: row["relative_path"]
        ),
        "pairwise_receipts": pairwise_receipts,
        "split_regime": _split_regime(loadable_family_count),
        "route_census_started": False,
        "outcome_accessed": False,
        "holdout_opened": False,
        "claim_decision_made": False,
    }
    output_dir.mkdir(parents=True)
    (output_dir / "map_families.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Adjudicate outcome-blind v24 Lanelet2 map families."
    )
    parser.add_argument("--census", type=Path, required=True)
    parser.add_argument("--builder-smoke", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = adjudicate_map_families(
        args.census,
        args.builder_smoke,
        args.output_dir,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
