#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

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


def _pose_at(centerline: np.ndarray, *, at_end: bool) -> np.ndarray:
    points = np.asarray(centerline, dtype=np.float64)
    if points.ndim != 2 or len(points) < 2 or points.shape[1] < 2:
        raise ValueError(f"Invalid lanelet centerline shape {points.shape}.")
    if at_end:
        position = points[-1, :2]
        direction = points[-1, :2] - points[-2, :2]
    else:
        position = points[0, :2]
        direction = points[1, :2] - points[0, :2]
    heading = math.atan2(float(direction[1]), float(direction[0]))
    return np.array([position[0], position[1], heading], dtype=np.float32)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a deterministic smoke-test Route from a Lanelet2 map."
    )
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--map_path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min_length_m", type=float, default=120.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start_lanelet_id", type=int, default=None)
    parser.add_argument("--goal_lanelet_id", type=int, default=None)
    parser.add_argument(
        "--via_lanelet_id",
        type=int,
        action="append",
        default=[],
        help="Optional ordered waypoint lanelet; may be passed more than once.",
    )
    args = parser.parse_args()
    if (args.start_lanelet_id is None) != (args.goal_lanelet_id is None):
        parser.error(
            "--start_lanelet_id and --goal_lanelet_id must be provided together."
        )
    if args.via_lanelet_id and args.start_lanelet_id is None:
        parser.error("--via_lanelet_id requires explicit start and goal lanelets.")

    _install_diffusion_repo(args.diffusion_repo)
    using_projection_fallback = install_lanelet2_projection_fallback(args.map_path)

    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder
    from scenario_generation.route import Route

    random.seed(args.seed)
    builder = LaneletSceneBuilder(str(args.map_path.resolve()))
    if args.start_lanelet_id is not None:
        best_ids = builder.route_with_waypoints(
            args.start_lanelet_id,
            args.via_lanelet_id,
            args.goal_lanelet_id,
        )
        if best_ids is None:
            raise RuntimeError(
                "No route exists through the requested lanelets: "
                f"{[args.start_lanelet_id, *args.via_lanelet_id, args.goal_lanelet_id]}"
            )
        route_mode = "explicit"
    else:
        best_ids = None
        best_length = 0.0
        for start_id in builder.lanelet_ids():
            route_ids = builder.find_route(start_id, min_length_m=args.min_length_m)
            if len(route_ids) < 2:
                continue
            route_length = sum(
                float(
                    np.linalg.norm(
                        np.diff(builder.raw_centerline(lanelet_id)[:, :2], axis=0),
                        axis=1,
                    ).sum()
                )
                for lanelet_id in route_ids
            )
            if route_length > best_length:
                best_ids = route_ids
                best_length = route_length
        route_mode = "automatic"

    if best_ids is None:
        raise RuntimeError(f"No route was found in {args.map_path}.")
    best_length = sum(
        float(
            np.linalg.norm(
                np.diff(builder.raw_centerline(lanelet_id)[:, :2], axis=0),
                axis=1,
            ).sum()
        )
        for lanelet_id in best_ids
    )
    if best_length < args.min_length_m:
        raise RuntimeError(
            f"Resolved route is {best_length:.1f} m, shorter than "
            f"--min_length_m={args.min_length_m:.1f}."
        )

    start_pose = _pose_at(builder.raw_centerline(best_ids[0]), at_end=False)
    goal_pose = _pose_at(builder.raw_centerline(best_ids[-1]), at_end=True)
    route = Route(
        map_path=str(args.map_path.resolve()),
        start_pose=start_pose,
        goal_pose=goal_pose,
        start_lanelet_id=int(best_ids[0]),
        goal_lanelet_id=int(best_ids[-1]),
        route_lanelet_ids=[int(lanelet_id) for lanelet_id in best_ids],
    )
    route.save(args.output)
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "map_path": route.map_path,
                "route_length_m": best_length,
                "route_lanelet_count": len(best_ids),
                "start_lanelet_id": route.start_lanelet_id,
                "goal_lanelet_id": route.goal_lanelet_id,
                "via_lanelet_ids": args.via_lanelet_id,
                "route_mode": route_mode,
                "using_no_ros_projection_fallback": using_projection_fallback,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
