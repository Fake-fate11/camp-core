from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.carla_causal_adapter import (
    _reject_forbidden_source_fields,
    build_carla_history_batch,
    build_route_lifting_context,
    materialize_carla_snapshot,
)
from camp_core.integrations.carla_exact_speed_source import (
    LaneSurfaceSample,
    LiftingTolerances,
    RouteLiftingContext,
    canonical_json_sha256,
    lift_k8_route_receipt,
)
from camp_core.integrations.diffusion_planner_causal_atoms import (
    CANDIDATE_LOCAL_EXACT_SPEED,
)
from camp_core.integrations.diffusion_planner_v19_nuplan_bridge import (
    DP_OPERATIONAL_TOP1_NAME,
    DP_OPERATIONAL_TOP1_PROVENANCE,
    array_sha256,
    build_request_metadata,
    read_response,
    write_request,
)
from camp_core.integrations.nuplan_causal_adapter import encode_route_lane


CAPTURE_SCHEMA = "dp_camp_v19_carla_source_capture_v1"
SELECTION_SEED = 3411
DP_SEED_ROOT = 3412
FROZEN_LIFTING_TOLERANCES = LiftingTolerances(
    1.5273609989704584,
    3.0518578125e-05,
    1e-9,
    3.0518578125e-05,
)


def build_probe_materialization(
    capture: Mapping[str, Any],
    *,
    tolerances: LiftingTolerances,
):
    """Build the existing causal DP input and route-lifting sidecar."""
    _reject_forbidden_source_fields(capture)
    if capture.get("schema_version") != CAPTURE_SCHEMA:
        raise ValueError("CARLA source capture schema mismatch")
    if capture.get("selection_seed") != SELECTION_SEED:
        raise ValueError("CARLA source capture seed must remain 3411")
    if capture.get("route_source") != "current_map_topology_successors":
        raise ValueError("CARLA route source mismatch")
    for name in ("map_sha256", "source_head"):
        _require_sha256(capture.get(name), name)

    route_sources = capture.get("route_lanes")
    if not isinstance(route_sources, list) or not 1 <= len(route_sources) <= 25:
        raise ValueError("CARLA source capture needs one to 25 route lanes")
    route = np.zeros((25, 20, 33), dtype=np.float64)
    route_speed = np.zeros((25, 1), dtype=np.float32)
    route_has_speed = np.zeros((25, 1), dtype=bool)
    for index, source in enumerate(route_sources):
        if not isinstance(source, Mapping) or set(source) != {
            "centerline",
            "left_boundary",
            "right_boundary",
        }:
            raise ValueError("CARLA route lane source fields are invalid")
        encoded = encode_route_lane(
            centerline=np.asarray(source["centerline"], dtype=np.float64),
            left_boundary=np.asarray(source["left_boundary"], dtype=np.float64),
            right_boundary=np.asarray(source["right_boundary"], dtype=np.float64),
            speed_limit_mps=None,
            require_speed_limit=False,
        )
        route[index] = encoded.tensor

    lanes = np.zeros((140, 20, 33), dtype=np.float64)
    lane_speed = np.zeros((140, 1), dtype=np.float32)
    lane_has_speed = np.zeros((140, 1), dtype=bool)
    lanes[: len(route_sources)] = route[: len(route_sources)]
    timestamps, batch = build_carla_history_batch(capture["frames"])
    traffic_available = capture.get("traffic_light_state_available")
    if traffic_available is not False:
        raise ValueError("source probe requires explicit unavailable traffic state")
    decision_context = {
        "map_frame": "world",
        "decision_id": canonical_json_sha256(
            {
                "map": capture["map_name"],
                "timestamp": capture["decision_timestamp_us"],
                "route": capture["route_samples"],
            }
        ),
        "route_source": capture["route_source"],
        "lanes": lanes,
        "lanes_has_speed_limit": lane_has_speed,
        "lanes_speed_limit": lane_speed,
        "route_lanes": route,
        "route_lanes_has_speed_limit": route_has_speed,
        "route_lanes_speed_limit": route_speed,
        "line_strings": np.zeros((60, 20, 4), dtype=np.float32),
        "polygons": np.zeros((10, 40, 3), dtype=np.float32),
        "static_objects": np.zeros((5, 10), dtype=np.float32),
        "turn_indicators": np.zeros(31, dtype=np.int32),
        "turn_indicators_available": False,
        "traffic_light_state_available": False,
        "ego_wheelbase_m": 2.875,
        "mission_goal_pose": np.asarray(capture["mission_goal_pose"], dtype=np.float64),
    }
    materialized = materialize_carla_snapshot(
        timestamps_us=timestamps,
        decision_timestamp_us=int(capture["decision_timestamp_us"]),
        traffic_timestamp_us=capture.get("traffic_timestamp_us"),
        batch=batch,
        decision_context=decision_context,
        source_metadata={
            "map_name": capture["map_name"],
            "map_sha256": capture["map_sha256"],
            "source_head": capture["source_head"],
            "selection_seed": SELECTION_SEED,
        },
    )
    context = build_route_lifting_context(
        route_source=str(capture["route_source"]),
        route_samples=capture["route_samples"],
        directed_edges=capture["directed_edges"],
        route_sample_step_m=float(capture["route_sample_step_m"]),
        tolerances=tolerances,
        map_sha256=str(capture["map_sha256"]),
    )
    return materialized, context, np.asarray(batch.agents_from_world_tf[0]).copy()


def write_probe_requests(
    capture: Mapping[str, Any],
    *,
    tolerances: LiftingTolerances,
    camp_request_dir: Path,
    default_request_dir: Path,
    context_path: Path,
    camp_head: str,
    dp_head: str,
    selector_hashes: Sequence[str],
) -> None:
    if any(path.exists() for path in (camp_request_dir, default_request_dir, context_path)):
        raise FileExistsError("probe request or context output already exists")
    _require_git_head(camp_head, "CAMP head")
    _require_git_head(dp_head, "DP head")
    if len(selector_hashes) != 3:
        raise ValueError("source probe requires three selector hashes")
    for digest in selector_hashes:
        _require_sha256(digest, "selector")
    materialized, context, transform = build_probe_materialization(
        capture, tolerances=tolerances
    )
    common = {
        "log_name": str(capture["map_name"]),
        "scenario_token": context.source_sha256,
        "iteration_index": 0,
        "simulation_time_us": int(capture["decision_timestamp_us"]),
        "scenario_seed": SELECTION_SEED,
        "dp_seed_root": DP_SEED_ROOT,
        "camp_head": camp_head,
        "dp_head": dp_head,
        "nuplan_head": str(capture["source_head"]),
        "causal_input": materialized.dp_input,
        "speed_source_policy": CANDIDATE_LOCAL_EXACT_SPEED,
    }
    camp_metadata = build_request_metadata(
        arm="camp", selector_hashes=tuple(selector_hashes), **common
    )
    default_metadata = build_request_metadata(arm="dp_default", **common)
    write_request(camp_request_dir, materialized.dp_input, camp_metadata)
    write_request(default_request_dir, materialized.dp_input, default_metadata)
    _write_json_atomic(
        context_path,
        {
            "capture_sha256": canonical_json_sha256(capture),
            "agents_from_world_tf": transform.tolist(),
            "context": asdict(context),
        },
    )


def collect_carla_source_bundle(
    world: Any,
    *,
    source_head: str,
    route_sample_step_m: float = 5.0,
    route_point_count: int = 81,
) -> dict[str, Any]:
    """Collect one outcome-free stationary source tick bundle from CARLA."""
    _require_sha256(source_head, "source head")
    map_api = world.get_map()
    route = _deterministic_route(map_api, route_sample_step_m, route_point_count)
    samples, edges, route_lanes = _route_source(route)
    blueprint = sorted(
        world.get_blueprint_library().filter("vehicle.*"), key=lambda item: item.id
    )[0]
    if blueprint.has_attribute("role_name"):
        blueprint.set_attribute("role_name", "hero")
    transform = route[0].transform
    transform.location.z += 0.5
    ego = world.try_spawn_actor(blueprint, transform)
    if ego is None:
        raise RuntimeError("CARLA source probe could not spawn the ego actor")
    settings = world.get_settings()
    original = (settings.synchronous_mode, settings.fixed_delta_seconds)
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 0.1
    world.apply_settings(settings)
    frames = []
    try:
        if hasattr(ego, "apply_control"):
            import carla

            ego.apply_control(carla.VehicleControl(hand_brake=True))
        for _ in range(31):
            world.tick()
            snapshot = world.get_snapshot()
            frames.append(_frame(world, ego, snapshot))
    finally:
        ego.destroy()
        settings.synchronous_mode, settings.fixed_delta_seconds = original
        world.apply_settings(settings)
    timestamps = [frame["timestamp_us"] for frame in frames]
    if any(right - left != 100_000 for left, right in zip(timestamps, timestamps[1:])):
        raise ValueError("CARLA source ticks are not uniformly spaced at 0.1 s")
    xodr = map_api.to_opendrive()
    goal = route[-1].transform
    return {
        "schema_version": CAPTURE_SCHEMA,
        "selection_seed": SELECTION_SEED,
        "map_name": str(map_api.name),
        "map_sha256": hashlib.sha256(xodr.encode("utf-8")).hexdigest(),
        "source_head": source_head,
        "decision_timestamp_us": timestamps[-1],
        "traffic_timestamp_us": None,
        "traffic_light_state_available": False,
        "route_source": "current_map_topology_successors",
        "route_sample_step_m": float(route_sample_step_m),
        "route_samples": samples,
        "directed_edges": edges,
        "route_lanes": route_lanes,
        "mission_goal_pose": [
            float(goal.location.x),
            float(goal.location.y),
            math.radians(float(goal.rotation.yaw)),
        ],
        "frames": frames,
    }


def write_lifting_receipt(
    *,
    capture: Mapping[str, Any],
    context_path: Path,
    camp_request_dir: Path,
    default_request_dir: Path,
    map_api: Any,
    output_path: Path,
) -> None:
    payload = json.loads(context_path.read_text(encoding="utf-8"))
    if payload["capture_sha256"] != canonical_json_sha256(capture):
        raise ValueError("capture/context SHA256 mismatch")
    context = _context(payload["context"])
    if hashlib.sha256(map_api.to_opendrive().encode("utf-8")).hexdigest() != context.map_sha256:
        raise ValueError("live CARLA map SHA256 mismatch")
    camp_raw = json.loads((camp_request_dir / "request.json").read_text("utf-8"))
    default_raw = json.loads((default_request_dir / "request.json").read_text("utf-8"))
    camp = read_response(
        camp_request_dir,
        expected_run_key=str(camp_raw["run_key"]),
        expected_iteration_index=0,
    )
    default = read_response(
        default_request_dir,
        expected_run_key=str(default_raw["run_key"]),
        expected_iteration_index=0,
    )
    receipt = lift_k8_route_receipt(
        candidates=camp.arrays["candidates"],
        operational_top1=default.arrays["selected_trajectory"],
        agents_from_world_tf=payload["agents_from_world_tf"],
        context=context,
        map_api=map_api,
        candidate_tensor_sha256=str(camp.metadata["candidate_sha256_before"]),
        operational_top1_sha256=str(default.metadata["selected_trajectory_sha256"]),
        provenance={
            "scenario_token": context.source_sha256,
            "agents_from_world_tf_sha256": array_sha256(
                np.asarray(payload["agents_from_world_tf"], dtype=np.float64)
            ),
            "baseline_name": DP_OPERATIONAL_TOP1_NAME,
            "baseline_provenance": DP_OPERATIONAL_TOP1_PROVENANCE,
            "native_ranked_top1": False,
        },
    )
    _write_json_atomic(
        output_path,
        {
            "schema_version": "dp_camp_v19_carla_source_probe_receipt_v1",
            "lifting_receipt": receipt,
            "access_counters": {
                "simulator_arm_advances": 0,
                "outcome_reads": 0,
                "metric_calls": 0,
                "holdout_reads": 0,
            },
        },
    )


def _deterministic_route(map_api: Any, step: float, count: int) -> list[Any]:
    if not math.isfinite(step) or step <= 0 or count < 2:
        raise ValueError("route sampling contract is invalid")
    for start in sorted(map_api.generate_waypoints(step), key=_waypoint_key):
        route = [start]
        seen = {_waypoint_key(start)}
        while len(route) < count:
            successors = [item for item in route[-1].next(step) if _waypoint_key(item) not in seen]
            if not successors:
                break
            current = sorted(successors, key=_waypoint_key)[0]
            route.append(current)
            seen.add(_waypoint_key(current))
        if len(route) == count:
            return route
    raise ValueError("no deterministic CARLA route satisfies the frozen window")


def _waypoint_key(waypoint: Any) -> tuple[int, int, int, float]:
    return (
        int(waypoint.road_id),
        int(waypoint.section_id),
        int(waypoint.lane_id),
        round(float(waypoint.s), 9),
    )


def _route_source(route: Sequence[Any]):
    samples = []
    groups: list[list[tuple[list[float], list[float], list[float]]]] = []
    identities = []
    for waypoint in route:
        transform = waypoint.transform
        yaw = math.radians(float(transform.rotation.yaw))
        left = (-math.sin(yaw), math.cos(yaw))
        half_width = float(waypoint.lane_width) / 2.0
        center = [float(transform.location.x), float(transform.location.y)]
        row = (
            center,
            [center[0] + half_width * left[0], center[1] + half_width * left[1]],
            [center[0] - half_width * left[0], center[1] - half_width * left[1]],
        )
        identity = (str(waypoint.road_id), int(waypoint.section_id), int(waypoint.lane_id))
        if not identities or identity != identities[-1]:
            identities.append(identity)
            groups.append([])
        groups[-1].append(row)
        samples.append(
            {
                "road_id": identity[0],
                "section_id": identity[1],
                "lane_id": identity[2],
                "s": float(waypoint.s),
                "x": center[0],
                "y": center[1],
                "z": float(transform.location.z),
                "lane_width": float(waypoint.lane_width),
                "is_junction": bool(waypoint.is_junction),
            }
        )
    if len(groups) > 25 or any(len(group) < 2 for group in groups):
        raise ValueError("CARLA route cannot be encoded in the fixed 25-lane contract")
    edges = [(identities[index], identities[index + 1]) for index in range(len(identities) - 1)]
    lanes = [
        {
            "centerline": [row[0] for row in group],
            "left_boundary": [row[1] for row in group],
            "right_boundary": [row[2] for row in group],
        }
        for group in groups
    ]
    return samples, edges, lanes


def _frame(world: Any, ego: Any, snapshot: Any) -> dict[str, Any]:
    actors = []
    for actor in world.get_actors():
        if int(actor.id) == int(ego.id):
            continue
        if actor.type_id.startswith("vehicle."):
            type_id = 1
        elif actor.type_id.startswith("walker."):
            type_id = 2
        else:
            continue
        actors.append(_actor(actor, type_id))
    actors.sort(key=lambda item: item["track_id"])
    extent = ego.bounding_box.extent
    return {
        "timestamp_us": int(round(float(snapshot.timestamp.elapsed_seconds) * 1e6)),
        "ego_state": _actor_state(ego),
        "ego_extent": [2.0 * extent.x, 2.0 * extent.y, 2.0 * extent.z],
        "actors": actors,
    }


def _actor(actor: Any, type_id: int) -> dict[str, Any]:
    extent = actor.bounding_box.extent
    return {
        "track_id": str(actor.id),
        "type_id": type_id,
        "state": _actor_state(actor),
        "extent": [2.0 * extent.x, 2.0 * extent.y, 2.0 * extent.z],
    }


def _actor_state(actor: Any) -> list[float]:
    transform = actor.get_transform()
    velocity = actor.get_velocity()
    acceleration = actor.get_acceleration()
    return [
        float(transform.location.x),
        float(transform.location.y),
        float(velocity.x),
        float(velocity.y),
        float(acceleration.x),
        float(acceleration.y),
        math.radians(float(transform.rotation.yaw)),
    ]


def _context(raw: Mapping[str, Any]) -> RouteLiftingContext:
    tolerances = LiftingTolerances(**raw["tolerances"])
    return RouteLiftingContext(
        samples=tuple(LaneSurfaceSample(**item) for item in raw["samples"]),
        edges=tuple((tuple(source), tuple(target)) for source, target in raw["edges"]),
        route_sample_step_m=float(raw["route_sample_step_m"]),
        tolerances=tolerances,
        map_sha256=str(raw["map_sha256"]),
        source_sha256=str(raw["source_sha256"]),
        route_graph_sha256=str(raw["route_graph_sha256"]),
    )


def _require_sha256(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError(f"{name} SHA256 is invalid")


def _require_git_head(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError(f"{name} Git commit is invalid")


def _write_json_atomic(path: Path, value: Any) -> None:
    if path.exists() or path.with_suffix(path.suffix + ".tmp").exists():
        raise FileExistsError(f"output already exists: {path}")
    staging = path.with_suffix(path.suffix + ".tmp")
    staging.parent.mkdir(parents=True, exist_ok=True)
    staging.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    staging.replace(path)


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("capture", "materialize", "receipt"), required=True)
    parser.add_argument("--capture-json", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--source-head")
    parser.add_argument("--camp-request-dir", type=Path)
    parser.add_argument("--default-request-dir", type=Path)
    parser.add_argument("--context-json", type=Path)
    parser.add_argument("--camp-head")
    parser.add_argument("--dp-head")
    parser.add_argument("--selector-hashes-json")
    parser.add_argument("--receipt-json", type=Path)
    args = parser.parse_args(argv)
    if args.mode == "capture":
        import carla

        client = carla.Client(args.host, args.port)
        client.set_timeout(20.0)
        _write_json_atomic(
            args.capture_json,
            collect_carla_source_bundle(client.get_world(), source_head=args.source_head),
        )
        return 0
    if args.context_json is None or args.camp_request_dir is None or args.default_request_dir is None:
        raise ValueError("request roots and context JSON are required")
    capture = _json(args.capture_json)
    if args.mode == "materialize":
        write_probe_requests(
            capture,
            tolerances=FROZEN_LIFTING_TOLERANCES,
            camp_request_dir=args.camp_request_dir,
            default_request_dir=args.default_request_dir,
            context_path=args.context_json,
            camp_head=args.camp_head,
            dp_head=args.dp_head,
            selector_hashes=_json(Path(args.selector_hashes_json)),
        )
        return 0
    if args.receipt_json is None:
        raise ValueError("receipt JSON is required")
    import carla

    client = carla.Client(args.host, args.port)
    client.set_timeout(20.0)
    write_lifting_receipt(
        capture=capture,
        context_path=args.context_json,
        camp_request_dir=args.camp_request_dir,
        default_request_dir=args.default_request_dir,
        map_api=client.get_world().get_map(),
        output_path=args.receipt_json,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
