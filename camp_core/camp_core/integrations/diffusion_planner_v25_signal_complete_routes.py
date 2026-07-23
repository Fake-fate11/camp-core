from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence, Type

import numpy as np

from .diffusion_planner_v25_holdout_plan_dispatch import (
    validate_holdout_execution_plan,
)


SCHEMA_VERSION = "camp_dp_v25_signal_complete_route_assets_v1"


def materialize_signal_complete_route_assets(
    *,
    plan: Mapping[str, Any],
    map_artifact: Path,
    output_dir: Path,
    route_class: Type[Any],
) -> dict[str, Any]:
    """Materialize exact fixed-DP ``Route`` assets from a frozen V25 plan."""

    validated = validate_holdout_execution_plan(plan)
    map_root = Path(map_artifact).resolve()
    output = Path(output_dir).resolve()
    if not map_root.is_dir():
        raise ValueError("signal-complete map artifact is missing")
    output.mkdir(parents=True, exist_ok=False)
    route_dir = output / "routes"
    route_dir.mkdir()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for identity in validated["identities"]:
        route_identity = identity["route_identity_sha256"]
        if route_identity in seen:
            raise ValueError("signal-complete route identity repeated")
        seen.add(route_identity)
        source_map = (map_root / identity["map_relative_path"]).resolve()
        if map_root not in source_map.parents or not source_map.is_file():
            raise ValueError("signal-complete route map path escaped the artifact")
        if _sha256(source_map) != identity["map_sha256"]:
            raise ValueError("signal-complete route map SHA drifted")
        spec = identity["route_spec"]
        lanelet_ids = _lanelet_ids(spec.get("lanelet_ids"))
        start = _pose(spec.get("start_pose"), "start_pose")
        goal = _pose(spec.get("goal_pose"), "goal_pose")
        route = route_class(
            map_path=str(source_map),
            start_pose=start,
            goal_pose=goal,
            start_lanelet_id=lanelet_ids[0],
            goal_lanelet_id=lanelet_ids[-1],
            waypoint_poses=[],
            waypoint_lanelet_ids=[],
            route_lanelet_ids=list(lanelet_ids),
        )
        path = route_dir / f"{route_identity}.pkl"
        route.save(path)
        loaded = route_class.load(path)
        _validate_loaded_route(
            loaded,
            source_map=source_map,
            start=start,
            goal=goal,
            lanelet_ids=lanelet_ids,
        )
        rows.append(
            {
                "route_identity_sha256": route_identity,
                "scenario_identity_sha256": identity[
                    "scenario_identity_sha256"
                ],
                "map_sha256": identity["map_sha256"],
                "map_geometry_sha256": identity["map_geometry_sha256"],
                "corridor_sha256": identity["corridor_sha256"],
                "source_chain_sha256": identity["source_chain_sha256"],
                "route_asset": {
                    "name": route_identity,
                    "path": str(path),
                    "sha256": _sha256(path),
                },
                "route_lanelet_ids": list(lanelet_ids),
                "start_pose_float32": start.astype(np.float64).tolist(),
                "goal_pose_float32": goal.astype(np.float64).tolist(),
                "waypoint_count": 0,
                "fixed_dp_route_source": "scenario_generation/route.py",
                "fresh_b2_opened": False,
                "outcome_fields_consumed": [],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "materialized_signal_complete_fixed_dp_routes",
        "split": validated["split"],
        "route_count": len(rows),
        "map_count": validated["map_count"],
        "route_assets": rows,
        "route_asset_sha256": _canonical_rows_sha(rows),
        "fixed_dp_modified": False,
        "map_semantics_modified": False,
        "model_loaded": False,
        "candidate_generation_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def validate_signal_complete_route_assets(
    value: Mapping[str, Any],
    *,
    plan: Mapping[str, Any],
    map_artifact: Path,
    route_class: Type[Any],
) -> dict[str, Any]:
    validated_plan = validate_holdout_execution_plan(plan)
    fields = {
        "schema_version",
        "status",
        "split",
        "route_count",
        "map_count",
        "route_assets",
        "route_asset_sha256",
        "fixed_dp_modified",
        "map_semantics_modified",
        "model_loaded",
        "candidate_generation_executed",
        "fresh_b2_opened",
        "outcome_fields_consumed",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("signal-complete route asset manifest fields drifted")
    exact = {
        "schema_version": SCHEMA_VERSION,
        "status": "materialized_signal_complete_fixed_dp_routes",
        "split": validated_plan["split"],
        "route_count": validated_plan["route_count"],
        "map_count": validated_plan["map_count"],
        "fixed_dp_modified": False,
        "map_semantics_modified": False,
        "model_loaded": False,
        "candidate_generation_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    if any(not _strict_equal(value.get(name), expected) for name, expected in exact.items()):
        raise ValueError("signal-complete route asset manifest contract drifted")
    rows = value["route_assets"]
    if type(rows) is not list or len(rows) != validated_plan["route_count"]:
        raise ValueError("signal-complete route asset denominator drifted")
    if value["route_asset_sha256"] != _canonical_rows_sha(rows):
        raise ValueError("signal-complete route asset row root drifted")
    identities = validated_plan["identities"]
    map_root = Path(map_artifact).resolve()
    seen: set[str] = set()
    for expected, row in zip(identities, rows, strict=True):
        _validate_route_row(
            row,
            identity=expected,
            map_root=map_root,
            route_class=route_class,
        )
        identity = row["route_identity_sha256"]
        if identity in seen:
            raise ValueError("signal-complete route asset identity repeated")
        seen.add(identity)
    return dict(value)


def _validate_route_row(
    row: Any,
    *,
    identity: Mapping[str, Any],
    map_root: Path,
    route_class: Type[Any],
) -> None:
    fields = {
        "route_identity_sha256",
        "scenario_identity_sha256",
        "map_sha256",
        "map_geometry_sha256",
        "corridor_sha256",
        "source_chain_sha256",
        "route_asset",
        "route_lanelet_ids",
        "start_pose_float32",
        "goal_pose_float32",
        "waypoint_count",
        "fixed_dp_route_source",
        "fresh_b2_opened",
        "outcome_fields_consumed",
    }
    if type(row) is not dict or set(row) != fields:
        raise ValueError("signal-complete route asset row fields drifted")
    expected_values = {
        "route_identity_sha256": identity["route_identity_sha256"],
        "scenario_identity_sha256": identity["scenario_identity_sha256"],
        "map_sha256": identity["map_sha256"],
        "map_geometry_sha256": identity["map_geometry_sha256"],
        "corridor_sha256": identity["corridor_sha256"],
        "source_chain_sha256": identity["source_chain_sha256"],
        "route_lanelet_ids": identity["route_spec"]["lanelet_ids"],
        "waypoint_count": 0,
        "fixed_dp_route_source": "scenario_generation/route.py",
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    if any(
        not _strict_equal(row.get(name), expected)
        for name, expected in expected_values.items()
    ):
        raise ValueError("signal-complete route asset row authority drifted")
    start = _pose(identity["route_spec"]["start_pose"], "start_pose")
    goal = _pose(identity["route_spec"]["goal_pose"], "goal_pose")
    if (
        not _strict_equal(row["start_pose_float32"], start.astype(np.float64).tolist())
        or not _strict_equal(row["goal_pose_float32"], goal.astype(np.float64).tolist())
    ):
        raise ValueError("signal-complete route float32 pose receipt drifted")
    asset = row["route_asset"]
    if type(asset) is not dict or set(asset) != {"name", "path", "sha256"}:
        raise ValueError("signal-complete route asset binding drifted")
    if asset["name"] != identity["route_identity_sha256"]:
        raise ValueError("signal-complete route asset name drifted")
    path = Path(asset["path"]).resolve()
    if not path.is_file() or _sha256(path) != asset["sha256"]:
        raise ValueError("signal-complete route asset bytes drifted")
    source_map = (map_root / identity["map_relative_path"]).resolve()
    _validate_loaded_route(
        route_class.load(path),
        source_map=source_map,
        start=start,
        goal=goal,
        lanelet_ids=tuple(identity["route_spec"]["lanelet_ids"]),
    )


def _validate_loaded_route(
    route: Any,
    *,
    source_map: Path,
    start: np.ndarray,
    goal: np.ndarray,
    lanelet_ids: Sequence[int],
) -> None:
    if (
        Path(route.map_path).resolve() != source_map
        or np.asarray(route.start_pose).dtype != np.float32
        or np.asarray(route.goal_pose).dtype != np.float32
        or not np.array_equal(route.start_pose, start)
        or not np.array_equal(route.goal_pose, goal)
        or route.start_lanelet_id != lanelet_ids[0]
        or route.goal_lanelet_id != lanelet_ids[-1]
        or list(route.route_lanelet_ids or []) != list(lanelet_ids)
        or list(route.waypoint_poses) != []
        or list(route.waypoint_lanelet_ids) != []
    ):
        raise ValueError("materialized fixed-DP Route content drifted")


def _pose(value: Any, name: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != (3,) or raw.dtype.kind not in "fiu" or raw.dtype.kind == "b":
        raise ValueError(f"signal-complete {name} must be native numeric [3]")
    result = raw.astype(np.float32)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"signal-complete {name} must be finite")
    return result


def _lanelet_ids(value: Any) -> tuple[int, ...]:
    if (
        type(value) is not list
        or not value
        or any(type(item) is not int or item <= 0 for item in value)
        or len(set(value)) != len(value)
    ):
        raise ValueError("signal-complete route lanelet IDs are invalid")
    return tuple(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_rows_sha(rows: Any) -> str:
    import json

    return hashlib.sha256(
        (
            json.dumps(
                rows,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()


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
