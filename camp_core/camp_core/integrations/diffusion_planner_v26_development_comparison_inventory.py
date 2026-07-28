"""V26-native, zero-model source inventory for the development comparison.

This module deliberately begins from authoritative Lanelet source maps rather
than a V25 runner, route census, or saved training rows.  It materializes only
route/map/source identity and eligibility metadata.  No model, DP forward,
GPU, latent, candidate, trajectory, label, or outcome payload is touched.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner_v26_diversified_route_plan import (
    FROZEN_FIXED_DP_HEAD,
    canonical_json_sha256,
    frozen_family_specs,
)
from .diffusion_planner_v26_integration_boundary import (
    V26_FUTURE_EFFECT_SCHEMA,
    V26_LEGACY_SAFETYCOST_ROLE,
    enforce_v26_dp312_lanelet2_precedence,
    resolve_v26_signal_adapter,
    v26_generator_topology,
)
from .diffusion_planner_v26_source_authority import (
    build_v26_source_signal_config,
    require_v26_route_connectivity,
    v26_route_geometry_receipt,
    v26_source_bound_projection,
    v26_source_inventory_binding,
)


SCHEMA_VERSION = "camp_dp_v26_source_authoritative_development_inventory_v1"
EVIDENCE_ROLE = "development_nonholdout_source_authoritative_route_disjoint_inventory"
SOURCE_CANDIDATE_SCHEMA_VERSION = "camp_dp_v26_source_authoritative_candidate_v1"
ELIGIBILITY_SCHEMA_VERSION = "camp_dp_v26_source_authoritative_eligibility_v1"
CORRIDOR_SCHEMA_VERSION = "camp_dp_v26_source_authoritative_corridor_v1"
SELECTION_ALGORITHM_ID = "v26_identity_only_stratified_round_robin_corridor_v1"
SELECTION_TARGET_CLUSTERS = 100
MIN_ROUTE_LENGTH_M = 80.0
MAX_ROUTE_HOPS = 100
OVERLAP_DISTANCE_M = 3.0
MIN_OVERLAP_SAMPLES = 20
MAX_HEADING_DELTA_DEG = 15.0
TIGHT_CORRIDOR_WIDTH_M = 3.5
SHORT_PROGRESS_OPPORTUNITY_M = 100.0

_SHA_CHARS = frozenset("0123456789abcdef")

# The four paths are the source-authoritative V26 map copies.  The two legacy
# families deliberately have no V26-native source-map path and remain typed
# zero-capacity family rows; they are never replaced by another map or V25 data.
V26_NATIVE_SOURCE_MAPS: Mapping[str, str] = {
    "nishishinjuku_plus_four_track_highway": (
        "/root/autodl-tmp/camp_dp_assets/nishishinjuku_autoware_map/"
        "nishishinjuku_autoware_map/lanelet2_map_no_ros.osm"
    ),
    "sample_map_planning": (
        "/root/autodl-tmp/camp_dp_assets/sample-map-planning/"
        "sample-map-planning/lanelet2_map_no_ros.osm"
    ),
    "autoware_bidirectional_traffic": (
        "/root/autodl-tmp/camp_dp_zero_model_map_route_supply_census_20260727/"
        "derived_geometry/autoware_bidirectional_no_ros.osm"
    ),
    "legacy_intersection": (
        "/root/autodl-tmp/camp_dp_zero_model_map_route_supply_census_20260727/"
        "derived_geometry/intersection_route_geometry_only.osm"
    ),
}


def _require_sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or set(value) - _SHA_CHARS:
        raise ValueError(f"{label} must be a lowercase SHA256")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=path, text=True, encoding="utf-8"
    ).strip()


def _zero_calls() -> dict[str, int]:
    return {
        "model_forward_count": 0,
        "dp_forward_count": 0,
        "gpu_invocation_count": 0,
        "latent_generation_count": 0,
        "candidate_generation_count": 0,
        "selector_invocation_count": 0,
        "simulator_invocation_count": 0,
        "sequential_forward_count": 0,
    }


def _source_specs() -> dict[str, dict[str, Any]]:
    return {str(item["family_id"]): dict(item) for item in frozen_family_specs()}


def _require_training_population(
    population: Mapping[str, Any], revision_plan: Mapping[str, Any]
) -> dict[int, dict[str, Any]]:
    """Bind only final-population identities to their original route records."""

    if (
        population.get("artifact_role") != "partial-source"
        or population.get("split") != "development_nonholdout"
        or population.get("holdout_accessed") is not False
        or population.get("outcome_fields_consumed") != []
        or population.get("read_scope", {}).get("candidate_payloads_read") is not False
        or population.get("read_scope", {}).get("label_payloads_read") is not False
        or population.get("read_scope", {}).get("trajectory_payloads_read") is not False
        or population.get("read_scope", {}).get("outcome_payloads_read") is not False
    ):
        raise ValueError("V26 final training population identity contract drifted")
    denominator = dict(population.get("denominator", {}))
    if denominator != {
        "planned": 1783,
        "trainable_population": 1623,
        "actual_selected": 1623,
        "typed_failure_excluded": 160,
        "unattempted": 0,
    }:
        raise ValueError("V26 final training population denominator drifted")
    members = population.get("selected_members")
    routes = revision_plan.get("routes")
    if type(members) is not list or type(routes) is not list or len(routes) != 1783:
        raise ValueError("V26 final training population routes are unavailable")
    selected: dict[int, dict[str, Any]] = {}
    for member in members:
        if type(member) is not dict or set(member) != {
            "revised_plan_ordinal",
            "planned_unit_id_sha256",
            "unit_file_sha256",
        }:
            raise ValueError("V26 final training population member schema drifted")
        ordinal = member["revised_plan_ordinal"]
        if type(ordinal) is not int or not 0 <= ordinal < len(routes) or ordinal in selected:
            raise ValueError("V26 final training population ordinal drifted")
        _require_sha256(member["planned_unit_id_sha256"], "V26 training planned unit")
        _require_sha256(member["unit_file_sha256"], "V26 training unit file")
        schedule = dict(routes[ordinal])
        if type(schedule.get("route_record")) is not dict:
            raise ValueError("V26 training route record is unavailable")
        selected[ordinal] = schedule
    if len(selected) != 1623:
        raise ValueError("V26 final training population count drifted")
    return selected


def _enumerate_all_source_routes(builder: Any) -> tuple[list[tuple[tuple[int, ...], float]], dict[int, list[int]]]:
    """Enumerate all bounded source-graph branches, never a legacy route census."""

    drivable = sorted(
        int(value)
        for value in getattr(builder, "_vehicle_ll_ids", ())
        if int(value) in getattr(builder, "_cache", {})
        and math.isfinite(float(builder._cache[int(value)].arc_length))
        and float(builder._cache[int(value)].arc_length) > 0.0
    )
    if not drivable:
        raise ValueError("V26 source map has no drivable lanelets")
    lengths = {lanelet: float(builder._cache[lanelet].arc_length) for lanelet in drivable}
    following = {
        lanelet: sorted(
            int(item.id)
            for item in builder._routing_graph.following(builder._ll_by_id[lanelet])
            if int(item.id) in lengths
        )
        for lanelet in drivable
    }
    routes: list[tuple[tuple[int, ...], float]] = []
    for start in drivable:
        pending = [((start,), lengths[start])]
        while pending:
            lanelets, source_arc_length = pending.pop()
            if source_arc_length >= MIN_ROUTE_LENGTH_M:
                routes.append((lanelets, source_arc_length))
                continue
            if len(lanelets) >= MAX_ROUTE_HOPS:
                continue
            successors = [value for value in following[lanelets[-1]] if value not in lanelets]
            for successor in reversed(successors):
                pending.append((lanelets + (successor,), source_arc_length + lengths[successor]))
    return routes, following


def _route_polyline(builder: Any, lanelets: Sequence[int]) -> np.ndarray:
    pieces: list[np.ndarray] = []
    for lanelet in lanelets:
        points = np.asarray(builder._cache[int(lanelet)].raw_centerline, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 2 or len(points) < 2 or not np.isfinite(points).all():
            raise ValueError("V26 source route centerline is invalid")
        if pieces and np.linalg.norm(pieces[-1][-1] - points[0]) <= 1e-6:
            points = points[1:]
        pieces.append(points)
    result = np.concatenate(pieces, axis=0)
    if len(result) < 2 or not np.isfinite(result).all():
        raise ValueError("V26 source route polyline is invalid")
    return result


def _sample_polyline(points: np.ndarray) -> tuple[list[list[float]], list[float], float]:
    segments = np.linalg.norm(np.diff(points, axis=0), axis=1)
    keep = np.concatenate(([True], segments > 1e-9))
    points = points[keep]
    segments = np.linalg.norm(np.diff(points, axis=0), axis=1)
    arc = np.concatenate(([0.0], np.cumsum(segments)))
    length = float(arc[-1])
    if not math.isfinite(length) or length <= 0.0:
        raise ValueError("V26 source route geometry has no finite length")
    targets = np.arange(0.0, length, 1.0)
    if targets.size == 0 or not math.isclose(float(targets[-1]), length):
        targets = np.append(targets, length)
    samples = np.column_stack(
        (np.interp(targets, arc, points[:, 0]), np.interp(targets, arc, points[:, 1]))
    )
    headings = np.arctan2(np.gradient(samples, axis=0)[:, 1], np.gradient(samples, axis=0)[:, 0])
    if not np.isfinite(samples).all() or not np.isfinite(headings).all():
        raise ValueError("V26 source route sample is invalid")
    return samples.tolist(), headings.tolist(), length


def _source_stratum(
    *, builder: Any, lanelets: Sequence[int], following: Mapping[int, Sequence[int]], length_m: float,
    traffic_lanelets: set[int],
) -> tuple[dict[str, bool], float, list[int]]:
    widths = np.concatenate(
        [
            np.linalg.norm(
                builder._cache[int(lanelet)].interp_left
                - builder._cache[int(lanelet)].interp_right,
                axis=1,
            )
            for lanelet in lanelets
        ]
    )
    if widths.size == 0 or not np.isfinite(widths).all():
        raise ValueError("V26 source corridor width is invalid")
    boundary_ids = sorted(
        {
            int(boundary.id)
            for lanelet in lanelets
            for boundary in (
                builder._ll_by_id[int(lanelet)].leftBound,
                builder._ll_by_id[int(lanelet)].rightBound,
            )
        }
    )
    return (
        {
            "traffic_light": bool(set(int(value) for value in lanelets).intersection(traffic_lanelets)),
            "branch_intersection": any(len(following[int(value)]) > 1 for value in lanelets),
            "tight_corridor": float(widths.min()) <= TIGHT_CORRIDOR_WIDTH_M,
            "short_progress_opportunity": length_m <= SHORT_PROGRESS_OPPORTUNITY_M,
        },
        float(widths.min()),
        boundary_ids,
    )


def _risk_stratum(source_stratum: Mapping[str, bool]) -> str:
    return canonical_json_sha256(
        {
            "schema_version": "camp_dp_v26_source_risk_stratum_v1",
            "traffic_light": bool(source_stratum["traffic_light"]),
            "branch_intersection": bool(source_stratum["branch_intersection"]),
            "tight_corridor": bool(source_stratum["tight_corridor"]),
            "short_progress_opportunity": bool(source_stratum["short_progress_opportunity"]),
        }
    )


def _geometry_stratum(length_m: float) -> str:
    if length_m <= 100.0:
        return "short_le_100m"
    if length_m <= 200.0:
        return "medium_100_to_200m"
    return "long_gt_200m"


def _identity_only_route_sha256(route_spec: Mapping[str, Any]) -> str:
    return canonical_json_sha256(
        {
            "schema_version": "camp_dp_v26_identity_only_route_serialization_v1",
            "route_spec": dict(route_spec),
        }
    )


def _candidate_record(
    *,
    family_id: str,
    family: Mapping[str, Any],
    source_binding: Mapping[str, Any],
    builder: Any,
    lanelets: Sequence[int],
    following: Mapping[int, Sequence[int]],
    source_arc_length_m: float,
) -> dict[str, Any]:
    projection = dict(source_binding["source_projection"])
    inventory = dict(source_binding["source_inventory"])
    map_path = str(projection["source_map_path"])
    map_sha = str(projection["source_map_sha256"])
    require_v26_route_connectivity(builder, lanelets)
    geometry = v26_route_geometry_receipt(builder, lanelets, projection)
    samples, headings, length_m = _sample_polyline(_route_polyline(builder, lanelets))
    traffic_lanelets = {
        int(key)
        for key in dict(inventory["lanelet_to_traffic_regulatory_ids"])
    }
    source_stratum, minimum_width_m, boundary_ids = _source_stratum(
        builder=builder,
        lanelets=lanelets,
        following=following,
        length_m=length_m,
        traffic_lanelets=traffic_lanelets,
    )
    geometry_sha = str(geometry["derived_geometry_sha256"])
    route_identity = canonical_json_sha256(
        {
            "schema_version": SOURCE_CANDIDATE_SCHEMA_VERSION,
            "family_id": family_id,
            "map_sha256": map_sha,
            "route_lanelet_ids": list(lanelets),
            "derived_geometry_sha256": geometry_sha,
        }
    )
    route_id = f"v26-source-authoritative/{family_id}/{geometry_sha}"
    provisional_corridor = canonical_json_sha256(
        {
            "schema_version": CORRIDOR_SCHEMA_VERSION,
            "family_id": family_id,
            "map_sha256": map_sha,
            "route_lanelet_ids": list(lanelets),
        }
    )
    route_spec = {
        "map_path": map_path,
        "lanelet_ids": list(lanelets),
        "start_pose": [*samples[0], headings[0]],
        "goal_pose": [*samples[-1], headings[-1]],
        "route_length_m": length_m,
    }
    event_manifest = canonical_json_sha256(
        {
            "schema_version": "camp_dp_v26_source_event_manifest_v1",
            "family_id": family_id,
            "map_sha256": map_sha,
            "projection_sha256": projection["projection_sha256"],
            "inventory_sha256": inventory["inventory_sha256"],
            "source_stratum": source_stratum,
        }
    )
    schedule = {
        "family_id": family_id,
        "route_id": route_id,
        "corridor_id": provisional_corridor,
        "source_artifact_sha256": str(family["source_artifact_sha256"]),
        "event_manifest_sha256": event_manifest,
        "route_record": {
            "identity_sha256": route_identity,
            "source_map_path": map_path,
            "source_map_sha256": map_sha,
            "source_geometry_sha256": geometry_sha,
            "lanelet_ids": list(lanelets),
            "source_stratum": source_stratum,
        },
    }
    route_sha = _identity_only_route_sha256(route_spec)
    signal = build_v26_source_signal_config(
        schedule=schedule,
        family=family,
        route_sha256=route_sha,
        source_inventory_binding=source_binding,
    )
    probe = {
        "routes": [{"path": "identity_only_no_serialization", "sha256": route_sha}],
        "map": {"path": map_path, "sha256": map_sha},
        **signal,
    }
    adapter = resolve_v26_signal_adapter(probe)
    adapter.adapter.bind_builder(builder)
    adapter.adapter.bind_runtime_lanelet_ids(
        route_lanelet_ids=lanelets, map_lanelet_ids=lanelets
    )
    source_event_identity = str(
        signal["source_signal_authority"]["source_signal_authority_identity_sha256"]
    )
    physical_identity = canonical_json_sha256(
        {
            "schema_version": "camp_dp_v26_source_physical_route_identity_v1",
            "map_sha256": map_sha,
            "derived_geometry_sha256": geometry_sha,
        }
    )
    return {
        "schema_version": SOURCE_CANDIDATE_SCHEMA_VERSION,
        "family_id": family_id,
        "route_id": route_id,
        "route_identity_sha256": route_identity,
        "provisional_corridor_id": provisional_corridor,
        "physical_route_identity_sha256": physical_identity,
        "source_map_sha256": map_sha,
        "derived_geometry_sha256": geometry_sha,
        "source_artifact_sha256": str(family["source_artifact_sha256"]),
        "source_projection_sha256": str(projection["projection_sha256"]),
        "source_inventory_sha256": str(inventory["inventory_sha256"]),
        "source_event_identity_sha256": source_event_identity,
        "event_manifest_sha256": event_manifest,
        "risk_stratum_sha256": _risk_stratum(source_stratum),
        "geometry_stratum": _geometry_stratum(length_m),
        "source_stratum": source_stratum,
        "route_lanelet_ids": list(lanelets),
        "boundary_ids": boundary_ids,
        "minimum_source_corridor_width_m": minimum_width_m,
        "source_arc_length_m": float(source_arc_length_m),
        "route_length_m": length_m,
        "route_spec": route_spec,
        "identity_only_route_sha256": route_sha,
        "signal_authority_mode": adapter.mode,
        "signal_adapter_id": adapter.adapter_id,
        "eligibility": {
            "schema_version": ELIGIBILITY_SCHEMA_VERSION,
            "status": "passed_v26_native_source_preflight",
            "failure_class": None,
            "failure_reason": None,
            "exact_route_connectivity": True,
            "source_signal_adapter_bound": True,
            "model_dp_gpu_latent_candidate_calls": _zero_calls(),
        },
        # Internal geometry is deliberately removed before serialization.
        "_centerline_samples_m": samples,
        "_centerline_headings_rad": headings,
    }


def _typed_candidate_failure(
    *, family_id: str, lanelets: Sequence[int], exc: Exception
) -> dict[str, Any]:
    return {
        "schema_version": SOURCE_CANDIDATE_SCHEMA_VERSION,
        "family_id": family_id,
        "route_lanelet_ids": list(lanelets),
        "eligibility": {
            "schema_version": ELIGIBILITY_SCHEMA_VERSION,
            "status": "typed_failure",
            "failure_class": type(exc).__name__,
            "failure_reason": str(exc),
            "exact_route_connectivity": False,
            "source_signal_adapter_bound": False,
            "model_dp_gpu_latent_candidate_calls": _zero_calls(),
        },
    }


def _training_identity_record(
    *,
    schedule: Mapping[str, Any],
    family: Mapping[str, Any],
    source_binding: Mapping[str, Any],
    builder: Any,
) -> dict[str, Any]:
    record = dict(schedule["route_record"])
    lanelets = list(record["lanelet_ids"])
    require_v26_route_connectivity(builder, lanelets)
    geometry_sha = str(
        v26_route_geometry_receipt(
            builder, lanelets, source_binding["source_projection"]
        )["derived_geometry_sha256"]
    )
    signal = build_v26_source_signal_config(
        schedule=schedule,
        family=family,
        route_sha256=str(record["route_serialization_sha256"]),
        source_inventory_binding=source_binding,
    )
    source_event = str(
        signal["source_signal_authority"]["source_signal_authority_identity_sha256"]
    )
    physical = canonical_json_sha256(
        {
            "schema_version": "camp_dp_v26_source_physical_route_identity_v1",
            "map_sha256": record["source_map_sha256"],
            "derived_geometry_sha256": geometry_sha,
        }
    )
    return {
        "route_id": str(schedule["route_id"]),
        "corridor_id": str(schedule["corridor_id"]),
        "source_map_sha256": str(record["source_map_sha256"]),
        "derived_geometry_sha256": geometry_sha,
        "source_event_identity_sha256": source_event,
        "physical_route_identity_sha256": physical,
    }


def collect_v26_source_authoritative_candidates(
    *,
    training_population: Mapping[str, Any],
    revision_plan: Mapping[str, Any],
    fixed_dp_repo: Path,
) -> dict[str, Any]:
    """Collect all route identities from the V26-native source generator.

    The caller is responsible for serializing the resulting manifest.  This
    function only reads source map and identity metadata and imports the fixed
    DP Lanelet parser after verifying its frozen head.
    """

    fixed_dp_repo = Path(fixed_dp_repo).resolve()
    if _git_head(fixed_dp_repo) != FROZEN_FIXED_DP_HEAD:
        raise ValueError("V26 development inventory fixed-DP head drifted")
    selected = _require_training_population(training_population, revision_plan)
    specs = _source_specs()
    for path in (fixed_dp_repo, fixed_dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    enforce_v26_dp312_lanelet2_precedence()
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder  # noqa: PLC0415

    candidates: list[dict[str, Any]] = []
    training_identities: list[dict[str, Any]] = []
    families: list[dict[str, Any]] = []
    for family_id in sorted(specs):
        family = specs[family_id]
        selected_schedules = [
            selected[index]
            for index in sorted(selected)
            if str(selected[index]["family_id"]) == family_id
        ]
        source_path = V26_NATIVE_SOURCE_MAPS.get(family_id)
        if source_path is None:
            families.append(
                {
                    "family_id": family_id,
                    "source_status": "typed_source_map_unavailable_no_v26_native_path",
                    "training_selected_count": len(selected_schedules),
                    "candidate_universe_count": 0,
                    "eligible_preflight_count": 0,
                    "typed_failure_count": 0,
                }
            )
            continue
        expected_map_sha = str(family["map_sha256s"][0])
        map_path = Path(source_path)
        before = _sha256_file(map_path)
        if before != expected_map_sha:
            raise ValueError("V26 development inventory source map identity drifted")
        source_binding = v26_source_inventory_binding(map_path, expected_map_sha)
        family_candidates: list[dict[str, Any]] = []
        family_training: list[dict[str, Any]] = []
        with v26_source_bound_projection(source_binding["source_projection"]):
            builder = LaneletSceneBuilder(str(map_path))
            for schedule in selected_schedules:
                family_training.append(
                    _training_identity_record(
                        schedule=schedule,
                        family=family,
                        source_binding=source_binding,
                        builder=builder,
                    )
                )
            sequences, following = _enumerate_all_source_routes(builder)
            seen_geometry: set[str] = set()
            for lanelets, source_arc_length in sequences:
                try:
                    candidate = _candidate_record(
                        family_id=family_id,
                        family=family,
                        source_binding=source_binding,
                        builder=builder,
                        lanelets=lanelets,
                        following=following,
                        source_arc_length_m=source_arc_length,
                    )
                    geometry_sha = str(candidate["physical_route_identity_sha256"])
                    if geometry_sha in seen_geometry:
                        continue
                    seen_geometry.add(geometry_sha)
                    family_candidates.append(candidate)
                except Exception as exc:
                    family_candidates.append(
                        _typed_candidate_failure(
                            family_id=family_id, lanelets=lanelets, exc=exc
                        )
                    )
        after = _sha256_file(map_path)
        if after != before:
            raise RuntimeError("V26 development inventory source bytes changed during parse")
        candidates.extend(family_candidates)
        training_identities.extend(family_training)
        families.append(
            {
                "family_id": family_id,
                "source_status": "available_v26_native_source_bound",
                "source_map_path": str(map_path),
                "source_map_sha256": expected_map_sha,
                "source_inventory_binding_sha256": source_binding["binding_sha256"],
                "source_projection_sha256": source_binding["source_projection"]["projection_sha256"],
                "source_inventory_sha256": source_binding["source_inventory"]["inventory_sha256"],
                "training_selected_count": len(selected_schedules),
                "candidate_universe_count": len(family_candidates),
                "eligible_preflight_count": sum(
                    item["eligibility"]["status"] == "passed_v26_native_source_preflight"
                    for item in family_candidates
                ),
                "typed_failure_count": sum(
                    item["eligibility"]["status"] == "typed_failure"
                    for item in family_candidates
                ),
                "source_bytes_unchanged": True,
            }
        )
    return {
        "families": families,
        "training_identities": training_identities,
        "candidates": candidates,
        "zero_model_calls": _zero_calls(),
    }


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1


def _corridors_overlap(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if left["source_map_sha256"] != right["source_map_sha256"]:
        return False
    left_points = np.asarray(left["_centerline_samples_m"], dtype=np.float64)
    right_points = np.asarray(right["_centerline_samples_m"], dtype=np.float64)
    if not len(left_points) or not len(right_points):
        return False
    delta = left_points[:, None, :] - right_points[None, :, :]
    distance = np.linalg.norm(delta, axis=2)
    left_heading = np.asarray(left["_centerline_headings_rad"], dtype=np.float64)
    right_heading = np.asarray(right["_centerline_headings_rad"], dtype=np.float64)
    heading_delta = np.abs(np.arctan2(
        np.sin(left_heading[:, None] - right_heading[None, :]),
        np.cos(left_heading[:, None] - right_heading[None, :]),
    ))
    aligned = np.minimum(heading_delta, np.abs(np.pi - heading_delta)) <= math.radians(MAX_HEADING_DELTA_DEG)
    return int(np.count_nonzero((distance <= OVERLAP_DISTANCE_M) & aligned)) >= MIN_OVERLAP_SAMPLES


def _assign_native_corridors(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Group source geometry without importing the V22/V25 leakage implementation."""

    records = [dict(item) for item in candidates]
    records.sort(key=lambda item: str(item["route_id"]))
    union = _UnionFind(len(records))
    indexed: dict[tuple[str, int], list[int]] = defaultdict(list)
    boundary_index: dict[tuple[str, int], list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        map_sha = str(record["source_map_sha256"])
        for lanelet in set(int(value) for value in record["route_lanelet_ids"]):
            indexed[(map_sha, lanelet)].append(index)
        for boundary in set(int(value) for value in record["boundary_ids"]):
            boundary_index[(map_sha, boundary)].append(index)
    for groups in (indexed.values(), boundary_index.values()):
        for members in groups:
            for value in members[1:]:
                union.union(members[0], value)

    # A spatial index avoids an all-pairs geometry scan while retaining a
    # stricter check for nearby but non-identical Lanelet primitives.
    cells: dict[tuple[str, int, int], set[int]] = defaultdict(set)
    occupied: list[set[tuple[str, int, int]]] = []
    for index, record in enumerate(records):
        map_sha = str(record["source_map_sha256"])
        row = {
            (map_sha, math.floor(float(point[0]) / OVERLAP_DISTANCE_M), math.floor(float(point[1]) / OVERLAP_DISTANCE_M))
            for point in record["_centerline_samples_m"]
        }
        occupied.append(row)
        for cell in row:
            cells[cell].add(index)
    pairs: set[tuple[int, int]] = set()
    for index, row in enumerate(occupied):
        for map_sha, x_cell, y_cell in row:
            for x_offset in (-1, 0, 1):
                for y_offset in (-1, 0, 1):
                    for other in cells.get((map_sha, x_cell + x_offset, y_cell + y_offset), ()):
                        if other != index:
                            pairs.add(tuple(sorted((index, other))))
    for left, right in sorted(pairs):
        if union.find(left) != union.find(right) and _corridors_overlap(records[left], records[right]):
            union.union(left, right)

    members_by_root: dict[int, list[int]] = defaultdict(list)
    for index in range(len(records)):
        members_by_root[union.find(index)].append(index)
    result: list[dict[str, Any]] = []
    for members in members_by_root.values():
        route_ids = sorted(str(records[index]["route_id"]) for index in members)
        corridor_id = canonical_json_sha256(
            {
                "schema_version": CORRIDOR_SCHEMA_VERSION,
                "route_ids": route_ids,
                "overlap_thresholds": {
                    "distance_m": OVERLAP_DISTANCE_M,
                    "minimum_samples": MIN_OVERLAP_SAMPLES,
                    "heading_delta_deg": MAX_HEADING_DELTA_DEG,
                },
            }
        )
        for index in members:
            records[index]["corridor_id"] = corridor_id
        result.extend(records[index] for index in members)
    return sorted(result, key=lambda item: str(item["route_id"]))


def _stratum_key(candidate: Mapping[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(candidate["family_id"]),
        str(candidate["source_artifact_sha256"]),
        str(candidate["source_event_identity_sha256"]),
        str(candidate["risk_stratum_sha256"]),
        str(candidate["geometry_stratum"]),
    )


def _selection_seed(candidates: Sequence[Mapping[str, Any]]) -> str:
    return canonical_json_sha256(
        {
            "algorithm": SELECTION_ALGORITHM_ID,
            "target_clusters": SELECTION_TARGET_CLUSTERS,
            "candidate_route_id_sha256": canonical_json_sha256(
                sorted(str(item["route_id"]) for item in candidates)
            ),
        }
    )


def _rank(seed: str, candidate: Mapping[str, Any]) -> str:
    return canonical_json_sha256(
        {"selection_seed_sha256": seed, "route_id": str(candidate["route_id"])}
    )


def _select_candidates(candidates: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_stratum: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        by_stratum[_stratum_key(candidate)].append(dict(candidate))
    seed = _selection_seed(candidates)
    for rows in by_stratum.values():
        rows.sort(key=lambda item: (_rank(seed, item), str(item["route_id"])))
    target = min(SELECTION_TARGET_CLUSTERS, len({str(item["corridor_id"]) for item in candidates}))
    selected: list[dict[str, Any]] = []
    used_corridors: set[str] = set()
    selected_per_stratum: Counter[tuple[str, str, str, str, str]] = Counter()
    while len(selected) < target:
        available: list[tuple[int, str, tuple[str, str, str, str, str], dict[str, Any]]] = []
        for stratum, rows in by_stratum.items():
            candidate = next((item for item in rows if str(item["corridor_id"]) not in used_corridors), None)
            if candidate is not None:
                available.append((selected_per_stratum[stratum], canonical_json_sha256({"stratum": list(stratum)}), stratum, candidate))
        if not available:
            break
        _, _, stratum, candidate = min(available)
        selected.append(candidate)
        used_corridors.add(str(candidate["corridor_id"]))
        selected_per_stratum[stratum] += 1
    if len(selected) != target:
        raise RuntimeError("V26 identity-only selection could not realize its cluster capacity")
    return selected, {
        "algorithm_id": SELECTION_ALGORITHM_ID,
        "selection_seed_sha256": seed,
        "target_clusters": SELECTION_TARGET_CLUSTERS,
        "independent_cluster_capacity": len({str(item["corridor_id"]) for item in candidates}),
        "selected_cluster_count": len(selected),
        "capacity_ceiling": len(selected) < SELECTION_TARGET_CLUSTERS,
    }


def _coverage(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    families = Counter(str(row["family_id"]) for row in rows)
    corridors = Counter(str(row["corridor_id"]) for row in rows)
    source = Counter(str(row["source_artifact_sha256"]) for row in rows)
    events = Counter(str(row["source_event_identity_sha256"]) for row in rows)
    risks = Counter(str(row["risk_stratum_sha256"]) for row in rows)
    geometry = Counter(str(row["geometry_stratum"]) for row in rows)
    flags = {
        name: sum(bool(row["source_stratum"][name]) for row in rows)
        for name in ("traffic_light", "branch_intersection", "tight_corridor", "short_progress_opportunity")
    }
    return {
        "route_count": len(rows),
        "independent_corridor_count": len(corridors),
        "family_counts": dict(sorted(families.items())),
        "source_counts": dict(sorted(source.items())),
        "source_event_counts": dict(sorted(events.items())),
        "risk_counts": dict(sorted(risks.items())),
        "geometry_counts": dict(sorted(geometry.items())),
        "source_stratum_flag_counts": flags,
    }


def _external_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in candidate.items() if not key.startswith("_")}


def build_development_comparison_inventory(
    *,
    source_collection: Mapping[str, Any],
    camp_head: str,
    fixed_dp_checkpoint: Mapping[str, Any],
    adapted_selector: Mapping[str, Any],
    reference_selector: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze a route-disjoint development manifest from identity-only inputs."""

    if type(camp_head) is not str or len(camp_head) != 40:
        raise ValueError("V26 development inventory CAMP head is invalid")
    checkpoint = dict(fixed_dp_checkpoint)
    if set(checkpoint) != {"path", "sha256"}:
        raise ValueError("V26 development inventory checkpoint identity is invalid")
    _require_sha256(checkpoint["sha256"], "V26 development checkpoint SHA")
    if type(adapted_selector) is not dict or type(reference_selector) is not dict:
        raise ValueError("V26 development inventory selector identities are invalid")
    if source_collection.get("zero_model_calls") != _zero_calls():
        raise ValueError("V26 source inventory crossed the zero-model boundary")
    raw_candidates = [dict(item) for item in source_collection.get("candidates", [])]
    training = [dict(item) for item in source_collection.get("training_identities", [])]
    families = [dict(item) for item in source_collection.get("families", [])]
    if not raw_candidates or not families:
        raise ValueError("V26 source inventory candidate universe is absent")
    eligible = [
        item
        for item in raw_candidates
        if item.get("eligibility", {}).get("status") == "passed_v26_native_source_preflight"
    ]
    training_composites = {
        (
            str(item["route_id"]),
            str(item["corridor_id"]),
            str(item["derived_geometry_sha256"]),
            str(item["source_event_identity_sha256"]),
        )
        for item in training
    }
    training_physical = {str(item["physical_route_identity_sha256"]) for item in training}
    candidate_composites = {
        (
            str(item["route_id"]),
            str(item["provisional_corridor_id"]),
            str(item["derived_geometry_sha256"]),
            str(item["source_event_identity_sha256"]),
        )
        for item in eligible
    }
    # The literal composite tuple is separately recorded below.  Physical
    # identity exclusion prevents a seed/route-id namespace from disguising an
    # already trained geometry as a new route.
    physical_collisions = [
        item for item in eligible if str(item["physical_route_identity_sha256"]) in training_physical
    ]
    disjoint = [
        item for item in eligible if str(item["physical_route_identity_sha256"]) not in training_physical
    ]
    if not disjoint:
        raise ValueError("V26 development inventory has no source-authoritative route-disjoint candidate")
    corridor_ready = _assign_native_corridors(disjoint)
    selected, selection = _select_candidates(corridor_ready)
    if len({str(item["route_id"]) for item in selected}) != len(selected) or len(
        {str(item["corridor_id"]) for item in selected}
    ) != len(selected):
        raise ValueError("V26 development inventory selected route/corridor identity is not exact-once")
    selected_composites = {
        (
            str(item["route_id"]),
            str(item["corridor_id"]),
            str(item["physical_route_identity_sha256"]),
            str(item["source_event_identity_sha256"]),
        )
        for item in selected
    }
    if selected_composites.intersection(training_composites):
        raise ValueError("V26 development inventory composite identity intersects training")
    value = {
        "schema_version": SCHEMA_VERSION,
        "evidence_role": EVIDENCE_ROLE,
        "status": "prepared_identity_only_no_execution_no_claim",
        "camp_head": camp_head,
        "fixed_dp": {"head": FROZEN_FIXED_DP_HEAD, "checkpoint": checkpoint},
        "split": "development_nonholdout",
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "payload_read": False,
        "generator_topology": v26_generator_topology(),
        "arms": ["candidate0_row0", "CAMP-Static14D-adapted", "CAMP-Scene14D-adapted"],
        "closed_loop_topology": (
            "per_arm_own_state_compute_matched_single_same_ego_b8; "
            "no_cross_arm_pool_sharing"
        ),
        "endpoint_contract": {
            "schema_version": V26_FUTURE_EFFECT_SCHEMA,
            "domains": [
                "safety",
                "operation_progress",
                "planar_dynamics_filtered_body_frame_smoothness_proxy",
                "realtime",
            ],
            "weighted_total_score": False,
            "legacy_safetycost_role": V26_LEGACY_SAFETYCOST_ROLE,
        },
        "selectors": {"adapted": dict(adapted_selector), "reference": dict(reference_selector)},
        "source_families": families,
        "training_population": {
            "planned": 1783,
            "trainable": 1623,
            "typed_failure_excluded": 160,
            "identity_record_count_on_available_native_maps": len(training),
        },
        "disjointness": {
            "composite_fields": ["route_id", "corridor_id", "geometry_hash", "source_event_identity"],
            "training_composite_count": len(training_composites),
            "candidate_composite_count_before_selection": len(candidate_composites),
            "candidate_exact_composite_intersection_count": len(candidate_composites.intersection(training_composites)),
            "physical_geometry_collision_count": len(physical_collisions),
            "physical_geometry_collisions_excluded": len(physical_collisions),
            "selected_composite_intersection_count": len(selected_composites.intersection(training_composites)),
            "different_seed_or_state_creates_new_route": False,
        },
        "selection": selection,
        "candidate_universe": {
            "candidate_count": len(raw_candidates),
            "eligible_preflight_count": len(eligible),
            "typed_failure_count": len(raw_candidates) - len(eligible),
            "route_disjoint_eligible_count": len(corridor_ready),
            "route_disjoint_independent_corridor_capacity": len(
                {str(item["corridor_id"]) for item in corridor_ready}
            ),
            "coverage": _coverage(corridor_ready),
        },
        "candidate_universe_records": [
            _external_candidate(item) for item in raw_candidates
        ],
        "planned_denominator": {
            "cluster_is_independent_n": True,
            "planned": len(selected),
            "complete": 0,
            "typed_failure": 0,
            "unattempted": len(selected),
        },
        "selected_clusters": [_external_candidate(item) for item in selected],
        "selection_coverage": _coverage(selected),
        "invocation_counts": _zero_calls(),
        "claim_scope": (
            "development comparison preparation only; no effect, safety benefit, "
            "OOD, stability, or holdout-generalization conclusion"
        ),
        "inventory_sha256": "",
    }
    value["inventory_sha256"] = canonical_json_sha256(
        {key: item for key, item in value.items() if key != "inventory_sha256"}
    )
    return validate_development_comparison_inventory(value)


def validate_development_comparison_inventory(value: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed on identity, topology, or no-outcome drift."""

    result = dict(value)
    required = {
        "schema_version", "evidence_role", "status", "camp_head", "fixed_dp", "split",
        "holdout_accessed", "outcome_fields_consumed", "payload_read", "generator_topology",
        "arms", "closed_loop_topology", "endpoint_contract", "selectors", "source_families",
        "training_population", "disjointness", "selection", "candidate_universe",
        "candidate_universe_records",
        "planned_denominator", "selected_clusters", "selection_coverage", "invocation_counts",
        "claim_scope", "inventory_sha256",
    }
    if set(result) != required:
        raise ValueError("V26 development inventory field set drifted")
    if (
        result["schema_version"] != SCHEMA_VERSION
        or result["evidence_role"] != EVIDENCE_ROLE
        or result["status"] != "prepared_identity_only_no_execution_no_claim"
        or result["split"] != "development_nonholdout"
        or result["holdout_accessed"] is not False
        or result["outcome_fields_consumed"] != []
        or result["payload_read"] is not False
        or result["generator_topology"] != v26_generator_topology()
        or result["arms"] != ["candidate0_row0", "CAMP-Static14D-adapted", "CAMP-Scene14D-adapted"]
        or result["invocation_counts"] != _zero_calls()
    ):
        raise ValueError("V26 development inventory identity-only contract drifted")
    if result["fixed_dp"].get("head") != FROZEN_FIXED_DP_HEAD:
        raise ValueError("V26 development inventory fixed-DP head drifted")
    _require_sha256(result["fixed_dp"].get("checkpoint", {}).get("sha256"), "V26 comparison checkpoint")
    if (
        result["endpoint_contract"].get("schema_version") != V26_FUTURE_EFFECT_SCHEMA
        or result["endpoint_contract"].get("weighted_total_score") is not False
        or result["endpoint_contract"].get("legacy_safetycost_role") != V26_LEGACY_SAFETYCOST_ROLE
    ):
        raise ValueError("V26 development endpoint contract drifted")
    planned = dict(result["planned_denominator"])
    selected = list(result["selected_clusters"])
    universe = list(result["candidate_universe_records"])
    if len(universe) != result["candidate_universe"].get("candidate_count"):
        raise ValueError("V26 development inventory candidate universe count drifted")
    if (
        planned.get("planned") != len(selected)
        or planned.get("complete") != 0
        or planned.get("typed_failure") != 0
        or planned.get("unattempted") != len(selected)
        or planned.get("cluster_is_independent_n") is not True
    ):
        raise ValueError("V26 development inventory denominator drifted")
    route_ids = [str(item.get("route_id")) for item in selected]
    corridor_ids = [str(item.get("corridor_id")) for item in selected]
    if len(route_ids) != len(set(route_ids)) or len(corridor_ids) != len(set(corridor_ids)):
        raise ValueError("V26 development inventory selected identities are not exact-once")
    disjointness = dict(result["disjointness"])
    if (
        disjointness.get("candidate_exact_composite_intersection_count") != 0
        or disjointness.get("selected_composite_intersection_count") != 0
        or disjointness.get("different_seed_or_state_creates_new_route") is not False
    ):
        raise ValueError("V26 development inventory route-disjoint proof drifted")
    expected_hash = canonical_json_sha256(
        {key: item for key, item in result.items() if key != "inventory_sha256"}
    )
    if result["inventory_sha256"] != expected_hash:
        raise ValueError("V26 development inventory hash drifted")
    return result
