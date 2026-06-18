#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    install_lanelet2_projection_fallback,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect fixed Tier4 Diffusion Planner Route files for scenario "
            "bucket evidence. This is read-only evidence collection; it does "
            "not label buckets, run replay, train CAMP, or modify DP."
        )
    )
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument(
        "--route",
        action="append",
        type=_parse_named_path,
        required=True,
        help="NAME=/path/to/route.pkl. Repeat for each route.",
    )
    parser.add_argument(
        "--comparison_json",
        type=Path,
        default=None,
        help="Optional SafetyCost comparison JSON for run-key coverage context.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_markdown", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _install_diffusion_repo(args.diffusion_repo)
    comparison = _read_json(args.comparison_json) if args.comparison_json else None
    report = inspect_routes(
        routes=args.route,
        comparison=comparison,
        diffusion_repo=args.diffusion_repo,
        comparison_path=args.comparison_json,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_markdown.write_text(render_markdown(report), encoding="utf-8")


def inspect_routes(
    *,
    routes: list[tuple[str, Path]],
    comparison: Optional[dict[str, Any]] = None,
    diffusion_repo: Optional[Path] = None,
    comparison_path: Optional[Path] = None,
) -> dict[str, Any]:
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder
    from scenario_generation.route import Route

    comparison_by_route = (
        _comparison_context_by_route(comparison) if comparison is not None else {}
    )
    route_reports = []
    for name, route_path in routes:
        route = Route.load(route_path)
        if not route.is_resolved():
            raise ValueError(f"Route is not resolved: {route_path}")
        map_path = Path(route.map_path)
        projection_fallback = install_lanelet2_projection_fallback(map_path)
        builder = LaneletSceneBuilder(str(map_path))
        lanelet_ids = [int(lanelet_id) for lanelet_id in route.route_lanelet_ids]
        centerlines = [
            np.asarray(builder.raw_centerline(lanelet_id), dtype=np.float64)[:, :2]
            for lanelet_id in lanelet_ids
        ]
        traffic_light_groups = _traffic_light_groups(builder)
        geometry = inspect_route_geometry(
            lanelet_ids=lanelet_ids,
            centerlines=centerlines,
            traffic_light_groups=traffic_light_groups,
            transition_relations=_route_transition_relations(builder, lanelet_ids),
        )
        route_name = name or route_path.stem
        route_reports.append(
            {
                "name": route_name,
                "route_path": str(route_path),
                "map_path": str(map_path),
                "using_no_ros_projection_fallback": projection_fallback,
                "start_lanelet_id": route.start_lanelet_id,
                "goal_lanelet_id": route.goal_lanelet_id,
                "waypoint_lanelet_ids": list(route.waypoint_lanelet_ids),
                "route_lanelet_ids": lanelet_ids,
                "geometry": geometry,
                "comparison_context": comparison_by_route.get(route_name, {}),
                "labeling_guidance": _labeling_guidance(geometry),
            }
        )
    return {
        "analysis": {
            "name": "dp_camp_route_scenario_inspection_v1",
            "role": "route and scenario-definition evidence for explicit bucket labels",
            "diffusion_repo": None if diffusion_repo is None else str(diffusion_repo),
            "comparison_json": None if comparison_path is None else str(comparison_path),
            "online_selector_change": False,
            "training": False,
            "replay_run": False,
            "labels_are_not_applied": True,
            "labels_are_not_inferred_from_metrics": True,
        },
        "routes": route_reports,
        "next_step": (
            "review_route_evidence_then_fill_explicit_manifest_labels"
        ),
    }


def inspect_route_geometry(
    *,
    lanelet_ids: list[int],
    centerlines: list[np.ndarray],
    traffic_light_groups: dict[int, int],
    transition_relations: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    if not lanelet_ids:
        raise ValueError("Route must contain at least one lanelet.")
    if len(lanelet_ids) != len(centerlines):
        raise ValueError("lanelet_ids and centerlines must have the same length.")
    route_points = _concatenate_centerlines(centerlines)
    lanelet_geometry = _lanelet_geometry(lanelet_ids, centerlines, traffic_light_groups)
    segment_vectors = np.diff(route_points, axis=0)
    segment_lengths = np.linalg.norm(segment_vectors, axis=1)
    valid = segment_lengths > 1e-6
    if not np.any(valid):
        raise ValueError("Route centerline has no positive-length segments.")
    route_length = float(np.sum(segment_lengths[valid]))
    endpoint_distance = float(np.linalg.norm(route_points[-1] - route_points[0]))
    headings = np.arctan2(segment_vectors[valid, 1], segment_vectors[valid, 0])
    heading_deltas = _wrapped_diffs(headings)
    abs_heading_deltas = np.abs(heading_deltas)
    max_single = float(np.rad2deg(np.max(abs_heading_deltas))) if heading_deltas.size else 0.0
    total_abs = float(np.rad2deg(np.sum(abs_heading_deltas)))
    net_heading = float(np.rad2deg(abs(_wrap_angle(float(headings[-1] - headings[0])))))
    sampled = _sample_polyline(route_points, spacing_m=1.0)
    window_10 = _max_window_heading_change(sampled, window_m=10.0)
    window_25 = _max_window_heading_change(sampled, window_m=25.0)
    tl_lanelets = [
        lanelet_id for lanelet_id in lanelet_ids if lanelet_id in traffic_light_groups
    ]
    tl_groups = sorted({int(traffic_light_groups[lanelet_id]) for lanelet_id in tl_lanelets})
    transition_summary = _transition_relation_summary(transition_relations or [])
    return {
        "route_length_m": route_length,
        "endpoint_distance_m": endpoint_distance,
        "route_lanelet_count": len(lanelet_ids),
        "repeated_lanelet_count": len(lanelet_ids) - len(set(lanelet_ids)),
        "max_single_step_heading_change_deg": max_single,
        "total_abs_heading_change_deg": total_abs,
        "net_heading_change_deg": net_heading,
        "max_10m_net_heading_change_deg": window_10,
        "max_25m_net_heading_change_deg": window_25,
        "traffic_light_lanelet_ids": tl_lanelets,
        "traffic_light_group_ids": tl_groups,
        "traffic_light_lanelet_count": len(tl_lanelets),
        "traffic_light_group_count": len(tl_groups),
        "map_traffic_light_lanelet_count": len(traffic_light_groups),
        "map_traffic_light_group_count": len(set(traffic_light_groups.values())),
        "transition_relations": transition_relations or [],
        "transition_relation_counts": transition_summary["counts"],
        "lateral_transition_count": transition_summary["lateral_transition_count"],
        "has_lane_change_or_merge_evidence": transition_summary[
            "has_lane_change_or_merge_evidence"
        ],
        "lanelet_geometry": lanelet_geometry,
        "traffic_light_lanelet_geometry": [
            row for row in lanelet_geometry if row["traffic_light_group_id"] is not None
        ],
    }


def _lanelet_geometry(
    lanelet_ids: list[int],
    centerlines: list[np.ndarray],
    traffic_light_groups: dict[int, int],
) -> list[dict[str, Any]]:
    rows = []
    cumulative = 0.0
    for index, (lanelet_id, centerline) in enumerate(zip(lanelet_ids, centerlines)):
        points = np.asarray(centerline, dtype=np.float64)[:, :2]
        vectors = np.diff(points, axis=0)
        lengths = np.linalg.norm(vectors, axis=1)
        valid = lengths > 1e-6
        lanelet_length = float(np.sum(lengths[valid]))
        if np.any(valid):
            headings = np.arctan2(vectors[valid, 1], vectors[valid, 0])
            heading_deltas = _wrapped_diffs(headings)
            max_single = (
                float(np.rad2deg(np.max(np.abs(heading_deltas))))
                if heading_deltas.size
                else 0.0
            )
            net_heading = float(
                np.rad2deg(abs(_wrap_angle(float(headings[-1] - headings[0]))))
            )
        else:
            max_single = 0.0
            net_heading = 0.0
        group_id = traffic_light_groups.get(lanelet_id)
        rows.append(
            {
                "route_index": index,
                "lanelet_id": lanelet_id,
                "length_m": lanelet_length,
                "cumulative_start_m": cumulative,
                "cumulative_end_m": cumulative + lanelet_length,
                "net_heading_change_deg": net_heading,
                "max_single_step_heading_change_deg": max_single,
                "traffic_light_group_id": None if group_id is None else int(group_id),
            }
        )
        cumulative += lanelet_length
    return rows


def _install_diffusion_repo(diffusion_repo: Path) -> None:
    repo = diffusion_repo.resolve()
    required = [
        repo / "scenario_generation" / "route.py",
        repo / "scenario_generation" / "gui" / "lanelet_scene_builder.py",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            f"{repo} is not a tier4/Diffusion-Planner checkout; missing: {missing}"
        )
    for path in (repo, repo / "diffusion_planner"):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


def _parse_named_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("route must have the form NAME=/path/route.pkl")
    name, path = value.split("=", 1)
    name = name.strip()
    if not name:
        raise argparse.ArgumentTypeError("route name must not be empty")
    return name, Path(path)


def _traffic_light_groups(builder: Any) -> dict[int, int]:
    method = getattr(builder, "get_traffic_light_groups", None)
    if method is None:
        return {}
    groups = method()
    return {int(lanelet_id): int(group_id) for lanelet_id, group_id in groups.items()}


def _route_transition_relations(
    builder: Any,
    lanelet_ids: list[int],
) -> list[dict[str, Any]]:
    graph = getattr(builder, "_routing_graph", None)
    lanelets = getattr(builder, "_ll_by_id", {})
    if graph is None or not isinstance(lanelets, dict):
        return []
    rows = []
    for from_id, to_id in zip(lanelet_ids[:-1], lanelet_ids[1:]):
        relation = "unknown"
        if from_id in lanelets and to_id in lanelets:
            try:
                relation = str(graph.routingRelation(lanelets[from_id], lanelets[to_id]))
            except Exception:
                relation = "unavailable"
        rows.append(
            {
                "from_lanelet_id": int(from_id),
                "to_lanelet_id": int(to_id),
                "relation": relation,
                "is_lateral": _is_lateral_transition(relation),
            }
        )
    return rows


def _transition_relation_summary(
    transition_relations: list[dict[str, Any]],
) -> dict[str, Any]:
    counts: dict[str, int] = {}
    lateral = 0
    for row in transition_relations:
        relation = str(row.get("relation", "unknown"))
        counts[relation] = counts.get(relation, 0) + 1
        lateral += int(bool(row.get("is_lateral", _is_lateral_transition(relation))))
    return {
        "counts": dict(sorted(counts.items())),
        "lateral_transition_count": lateral,
        "has_lane_change_or_merge_evidence": lateral > 0,
    }


def _is_lateral_transition(relation: str) -> bool:
    normalized = relation.replace("_", "").replace(" ", "").lower()
    return normalized in {
        "left",
        "right",
        "adjacentleft",
        "adjacentright",
    }


def _concatenate_centerlines(centerlines: list[np.ndarray]) -> np.ndarray:
    points: list[np.ndarray] = []
    for centerline in centerlines:
        arr = np.asarray(centerline, dtype=np.float64)
        if arr.ndim != 2 or arr.shape[0] < 2 or arr.shape[1] < 2:
            raise ValueError(f"Invalid centerline shape {arr.shape}.")
        xy = arr[:, :2]
        if points and np.linalg.norm(points[-1] - xy[0]) <= 1e-6:
            points.extend(point for point in xy[1:])
        else:
            points.extend(point for point in xy)
    return np.asarray(points, dtype=np.float64)


def _wrapped_diffs(headings: np.ndarray) -> np.ndarray:
    if headings.size < 2:
        return np.asarray([], dtype=np.float64)
    return np.asarray(
        [_wrap_angle(float(curr - prev)) for prev, curr in zip(headings[:-1], headings[1:])],
        dtype=np.float64,
    )


def _wrap_angle(value: float) -> float:
    return math.atan2(math.sin(value), math.cos(value))


def _sample_polyline(points: np.ndarray, *, spacing_m: float) -> np.ndarray:
    segment_vectors = np.diff(points, axis=0)
    segment_lengths = np.linalg.norm(segment_vectors, axis=1)
    cumulative = np.concatenate([[0.0], np.cumsum(segment_lengths)])
    total = cumulative[-1]
    if total <= spacing_m:
        return points.copy()
    distances = np.arange(0.0, total, spacing_m)
    if distances[-1] < total:
        distances = np.concatenate([distances, [total]])
    sampled = []
    for distance in distances:
        index = int(np.searchsorted(cumulative, distance, side="right") - 1)
        index = min(index, len(segment_lengths) - 1)
        length = segment_lengths[index]
        if length <= 1e-9:
            sampled.append(points[index])
            continue
        ratio = (distance - cumulative[index]) / length
        sampled.append(points[index] + ratio * segment_vectors[index])
    return np.asarray(sampled, dtype=np.float64)


def _max_window_heading_change(points: np.ndarray, *, window_m: float) -> float:
    segment_vectors = np.diff(points, axis=0)
    segment_lengths = np.linalg.norm(segment_vectors, axis=1)
    valid = segment_lengths > 1e-6
    if np.sum(valid) < 2:
        return 0.0
    headings = np.arctan2(segment_vectors[valid, 1], segment_vectors[valid, 0])
    valid_lengths = segment_lengths[valid]
    cumulative = np.concatenate([[0.0], np.cumsum(valid_lengths)])
    max_change = 0.0
    for start_idx, start_distance in enumerate(cumulative[:-1]):
        target = start_distance + window_m
        end_idx = int(np.searchsorted(cumulative, target, side="right") - 1)
        end_idx = min(max(end_idx, start_idx), len(headings) - 1)
        change = abs(_wrap_angle(float(headings[end_idx] - headings[start_idx])))
        max_change = max(max_change, change)
    return float(np.rad2deg(max_change))


def _comparison_context_by_route(
    comparison: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    rows = comparison.get("runs")
    if not isinstance(rows, list):
        raise ValueError("comparison JSON must contain a runs list.")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict):
            continue
        route_name = row.get("route_name")
        if route_name is None and row.get("route") is not None:
            route_name = Path(str(row["route"])).stem
        if route_name is not None:
            grouped[str(route_name)].append(row)
    context = {}
    for route_name, group in grouped.items():
        unique_run_keys = sorted({str(row.get("run_key")) for row in group})
        context[route_name] = {
            "row_count": len(group),
            "run_key_count": len(unique_run_keys),
            "variants": sorted({str(row.get("variant")) for row in group}),
            "seeds": sorted(_unique_values(group, "seed")),
            "steps": sorted(_unique_values(group, "steps")),
            "max_npcs": sorted(_unique_values(group, "max_npcs")),
            "spawn_probabilities": sorted(_unique_values(group, "spawn_probability")),
            "traffic_lights": sorted(_unique_values(group, "traffic_lights")),
            "advance_modes": sorted(_unique_values(group, "advance_mode")),
            "run_keys": unique_run_keys,
        }
    return context


def _unique_values(rows: list[dict[str, Any]], key: str) -> set[Any]:
    return {row.get(key) for row in rows if row.get(key) is not None}


def _labeling_guidance(geometry: dict[str, Any]) -> dict[str, Any]:
    return {
        "traffic_light_infrastructure_present": (
            geometry["traffic_light_lanelet_count"] > 0
        ),
        "turn_geometry_evidence": {
            "max_10m_net_heading_change_deg": geometry[
                "max_10m_net_heading_change_deg"
            ],
            "max_25m_net_heading_change_deg": geometry[
                "max_25m_net_heading_change_deg"
            ],
            "total_abs_heading_change_deg": geometry[
                "total_abs_heading_change_deg"
            ],
        },
        "lane_change_or_merge_route_evidence": {
            "has_lateral_transition": geometry[
                "has_lane_change_or_merge_evidence"
            ],
            "lateral_transition_count": geometry["lateral_transition_count"],
            "transition_relation_counts": geometry["transition_relation_counts"],
        },
        "candidate_buckets_supported_by_route_evidence": (
            ["lane_change_or_merge"]
            if geometry["has_lane_change_or_merge_evidence"]
            else []
        ),
        "labels_to_apply": [],
        "reason": (
            "This tool records route/scenario evidence only. Apply bucket labels "
            "in a manifest after reviewing this evidence and the run-level "
            "traffic_lights/NPC configuration."
        ),
    }


def _read_json(path: Optional[Path]) -> dict[str, Any]:
    if path is None:
        raise ValueError("JSON path is required.")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP-CAMP Route Scenario Inspection",
        "",
        "This report records route and scenario-definition evidence for explicit "
        "bucket labeling. It does not apply bucket labels and does not infer "
        "labels from replay outcomes.",
        "",
        "| Route | Length m | Endpoint m | TL lanelets | TL groups | Lateral transitions | Max 10m turn | Max 25m turn | Run keys | TL modes | NPC counts |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for route in report["routes"]:
        geom = route["geometry"]
        context = route.get("comparison_context", {})
        lines.append(
            f"| `{route['name']}` | "
            f"{geom['route_length_m']:.3f} | "
            f"{geom['endpoint_distance_m']:.3f} | "
            f"{geom['traffic_light_lanelet_count']} | "
            f"{geom['traffic_light_group_count']} | "
            f"{geom['lateral_transition_count']} | "
            f"{geom['max_10m_net_heading_change_deg']:.3f} | "
            f"{geom['max_25m_net_heading_change_deg']:.3f} | "
            f"{context.get('run_key_count', 'n/a')} | "
            f"{context.get('traffic_lights', 'n/a')} | "
            f"{context.get('max_npcs', 'n/a')} |"
        )
    lines.extend(
        [
            "",
            "Next step: review the geometry and run-level traffic/NPC settings, "
            "then fill the scenario bucket manifest explicitly. Mixed on/off "
            "traffic-light matrices should generally use run-key labels rather "
            "than route-level traffic-light labels.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
