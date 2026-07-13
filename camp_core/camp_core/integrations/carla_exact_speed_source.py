from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple
import xml.etree.ElementTree as ET


RUNG_ACTOR_LANDMARK = "A"
RUNG_EXPLICIT_NON_JUNCTION = "B"
RUNG_TOPOLOGY_DERIVED_JUNCTION = "C"
_RUNGS = {
    RUNG_ACTOR_LANDMARK,
    RUNG_EXPLICIT_NON_JUNCTION,
    RUNG_TOPOLOGY_DERIVED_JUNCTION,
}


SegmentKey = Tuple[str, int, int]
RouteIdentity = Tuple[str, int, int]


@dataclass(frozen=True)
class SegmentRef:
    road_id: str
    section_id: int
    lane_id: int
    s: float
    is_junction: bool

    @property
    def key(self) -> SegmentKey:
        return (self.road_id, self.section_id, self.lane_id)


@dataclass(frozen=True)
class RoadInfo:
    road_id: str
    junction_id: Optional[str]
    speeds: Tuple[Tuple[float, float], ...]
    driving_lanes_by_section: Tuple[Tuple[int, ...], ...]
    predecessor_roads: Tuple[str, ...]
    successor_roads: Tuple[str, ...]


@dataclass(frozen=True)
class OpenDriveSpeedIndex:
    roads: Mapping[str, RoadInfo]
    junction_incoming_by_connector: Mapping[str, Tuple[str, ...]]


@dataclass(frozen=True)
class SegmentSpeedDecision:
    eligible: bool
    speed_mps: Optional[float]
    reason: str


@dataclass(frozen=True)
class CandidateSourceDecision:
    eligible: bool
    speed_mps: Tuple[float, ...]
    reason: str


@dataclass(frozen=True)
class LandmarkSpeedSource:
    landmark_id: str
    road_id: str
    s: float
    from_lane: int
    to_lane: int
    value: float
    unit: str


@dataclass(frozen=True)
class LaneSurfaceSample:
    road_id: str
    section_id: int
    lane_id: int
    s: float
    x: float
    y: float
    z: float
    lane_width: float
    is_junction: bool

    @property
    def identity(self) -> RouteIdentity:
        return (self.road_id, self.section_id, self.lane_id)


@dataclass(frozen=True)
class LaneSectionBounds:
    road_id: str
    section_id: int
    start_s: float
    end_s: float


@dataclass(frozen=True)
class LiftingTolerances:
    geometry_epsilon_m: float
    station_epsilon_m: float
    z_epsilon_m: float
    continuity_epsilon_m: float


@dataclass(frozen=True)
class RouteLiftingContext:
    samples: Tuple[LaneSurfaceSample, ...]
    edges: Tuple[Tuple[RouteIdentity, RouteIdentity], ...]
    identity_directions: Tuple[Tuple[RouteIdentity, int], ...]
    route_sample_step_m: float
    tolerances: LiftingTolerances
    map_sha256: str
    source_sha256: str
    route_graph_sha256: str


def route_identity_directions(
    samples: Sequence[LaneSurfaceSample],
    continuity_epsilon_m: float,
) -> Tuple[Tuple[RouteIdentity, int], ...]:
    if not math.isfinite(continuity_epsilon_m) or continuity_epsilon_m < 0.0:
        raise ValueError("continuity epsilon must be finite and nonnegative")
    groups: list[tuple[RouteIdentity, list[LaneSurfaceSample]]] = []
    seen: set[RouteIdentity] = set()
    for sample in samples:
        if not groups or sample.identity != groups[-1][0]:
            if sample.identity in seen:
                raise ValueError("route identity must occupy one contiguous block")
            seen.add(sample.identity)
            groups.append((sample.identity, []))
        groups[-1][1].append(sample)
    directions = []
    for identity, group in groups:
        deltas = [right.s - left.s for left, right in zip(group, group[1:])]
        signs = {
            1 if delta > 0.0 else -1
            for delta in deltas
            if abs(delta) > continuity_epsilon_m
        }
        if len(signs) != 1:
            raise ValueError("route identity needs one nonzero station direction")
        direction = signs.pop()
        if any(
            direction * delta < -continuity_epsilon_m
            for delta in deltas
        ):
            raise ValueError("route identity station order is inconsistent")
        directions.append((identity, direction))
    return tuple(directions)


@dataclass(frozen=True)
class LiftedPointReceipt:
    candidate_index: int
    point_index: int
    ego_x: float
    ego_y: float
    world_x: float
    world_y: float
    road_id: Optional[str]
    section_id: Optional[int]
    lane_id: Optional[int]
    s: Optional[float]
    z: Optional[float]
    lateral_residual_m: Optional[float]
    unique_identity: bool
    unique_station: bool
    topology_continuous: bool
    reason: str

    @property
    def identity(self) -> Optional[RouteIdentity]:
        if self.road_id is None or self.section_id is None or self.lane_id is None:
            return None
        return (self.road_id, self.section_id, self.lane_id)


@dataclass(frozen=True)
class CandidateLiftDecision:
    eligible: bool
    points: Tuple[LiftedPointReceipt, ...]
    reason: str
    trajectory_lifting_sha256: str


@dataclass(frozen=True)
class _SurfaceMatch:
    road_id: str
    section_id: int
    lane_id: int
    s: float
    lateral_residual_m: float
    is_junction: bool

    @property
    def identity(self) -> RouteIdentity:
        return (self.road_id, self.section_id, self.lane_id)


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def parse_opendrive_lane_section_bounds(
    xml_text: str,
) -> Tuple[LaneSectionBounds, ...]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError("invalid OpenDRIVE XML") from exc
    result = []
    seen_roads = set()
    for road in root.findall("road"):
        road_id = road.get("id")
        try:
            length = float(road.get("length", ""))
        except ValueError as exc:
            raise ValueError("OpenDRIVE road length is invalid") from exc
        if (
            not road_id
            or road_id in seen_roads
            or not math.isfinite(length)
            or length <= 0.0
        ):
            raise ValueError("OpenDRIVE road metadata is invalid")
        seen_roads.add(road_id)
        starts = []
        for section in road.findall("./lanes/laneSection"):
            try:
                starts.append(float(section.get("s", "")))
            except ValueError as exc:
                raise ValueError("OpenDRIVE lane-section start is invalid") from exc
        if starts != sorted(starts) or any(
            not math.isfinite(value) or value < 0.0 or value >= length
            for value in starts
        ) or any(right <= left for left, right in zip(starts, starts[1:])):
            raise ValueError("OpenDRIVE lane-section bounds are invalid")
        for section_id, start_s in enumerate(starts):
            end_s = (
                starts[section_id + 1]
                if section_id + 1 < len(starts)
                else length
            )
            result.append(LaneSectionBounds(road_id, section_id, start_s, end_s))
    if not result:
        raise ValueError("OpenDRIVE contains no lane-section bounds")
    return tuple(result)


def freeze_lifting_tolerances(
    *,
    max_chord_error_m: float,
    max_station_roundtrip_error_m: float,
    max_z_roundtrip_error_m: float,
    coordinate_scale_m: float,
) -> LiftingTolerances:
    values = (
        max_chord_error_m,
        max_station_roundtrip_error_m,
        max_z_roundtrip_error_m,
    )
    if any(not math.isfinite(value) or value < 0.0 for value in values):
        raise ValueError("lifting source errors must be finite and nonnegative")
    if not math.isfinite(coordinate_scale_m) or coordinate_scale_m <= 0.0:
        raise ValueError("coordinate scale must be finite and positive")
    allowance = max(1e-9, 64.0 * math.ulp(float(coordinate_scale_m)))
    return LiftingTolerances(
        geometry_epsilon_m=max_chord_error_m + allowance,
        station_epsilon_m=max_station_roundtrip_error_m + allowance,
        z_epsilon_m=max_z_roundtrip_error_m + allowance,
        continuity_epsilon_m=max_station_roundtrip_error_m + allowance,
    )


def lift_candidate_to_route_surface(
    *,
    candidate_index: int,
    candidate: Sequence[Sequence[float]],
    agents_from_world_tf: Sequence[Sequence[float]],
    context: RouteLiftingContext,
    map_api: Any,
) -> CandidateLiftDecision:
    if candidate_index < 0:
        raise ValueError("candidate index must be nonnegative")
    if len(candidate) != 80:
        raise ValueError("candidate must contain exactly 80 points")
    _validate_lifting_context(context)
    world_xy = _inverse_transform_xy(candidate, agents_from_world_tf)
    chords = _surface_chords(context)
    points = []
    previous: Optional[LiftedPointReceipt] = None
    departed: set[RouteIdentity] = set()
    first_failure: Optional[str] = None
    continuity_broken = False
    for point_index, (raw_point, (world_x, world_y)) in enumerate(
        zip(candidate, world_xy)
    ):
        ego_x, ego_y = float(raw_point[0]), float(raw_point[1])
        match, failure = _unique_route_surface_match(
            world_x, world_y, context, chords
        )
        if failure is not None:
            receipt = _failed_point_receipt(
                candidate_index,
                point_index,
                ego_x,
                ego_y,
                world_x,
                world_y,
                failure,
            )
            continuity_broken = True
        else:
            assert match is not None
            receipt = _xodr_receipt(
                candidate_index,
                point_index,
                ego_x,
                ego_y,
                world_x,
                world_y,
                match,
                map_api,
                context.tolerances,
            )
            if receipt.reason != "lifted":
                continuity_broken = True
            elif continuity_broken or not _continuous(
                previous, receipt, departed, context
            ):
                receipt = replace(
                    receipt,
                    topology_continuous=False,
                    reason="route_topology_discontinuous",
                )
                continuity_broken = True
        points.append(receipt)
        if receipt.reason != "lifted" and first_failure is None:
            first_failure = receipt.reason
        if receipt.reason == "lifted":
            if previous is not None and previous.identity != receipt.identity:
                assert previous.identity is not None
                departed.add(previous.identity)
            previous = receipt
        else:
            previous = None
    payload = [
        {key: value for key, value in asdict(point).items() if key != "candidate_index"}
        for point in points
    ]
    return CandidateLiftDecision(
        eligible=first_failure is None,
        points=tuple(points),
        reason="source_complete" if first_failure is None else first_failure,
        trajectory_lifting_sha256=canonical_json_sha256(payload),
    )


def lift_k8_route_receipt(
    *,
    candidates: Any,
    operational_top1: Any,
    agents_from_world_tf: Any,
    context: RouteLiftingContext,
    map_api: Any,
    candidate_tensor_sha256: str,
    operational_top1_sha256: str,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    _reject_forbidden_receipt_fields(provenance)
    candidate_before = _array_sha256(candidates, (8, 80, 4), "candidates")
    operational_before = _array_sha256(
        operational_top1, (80, 4), "operational Top-1"
    )
    _validate_sha256(candidate_tensor_sha256, "candidate tensor")
    _validate_sha256(operational_top1_sha256, "operational Top-1")

    decisions = tuple(
        lift_candidate_to_route_surface(
            candidate_index=index,
            candidate=candidates[index],
            agents_from_world_tf=agents_from_world_tf,
            context=context,
            map_api=map_api,
        )
        for index in range(8)
    )
    default = lift_candidate_to_route_surface(
        candidate_index=0,
        candidate=operational_top1,
        agents_from_world_tf=agents_from_world_tf,
        context=context,
        map_api=map_api,
    )
    candidate_after = _array_sha256(candidates, (8, 80, 4), "candidates")
    operational_after = _array_sha256(
        operational_top1, (80, 4), "operational Top-1"
    )
    mask = [decision.eligible for decision in decisions]
    reasons = [decision.reason for decision in decisions]
    equivalent = (
        _array_sha256(candidates[0], (80, 4), "candidate 0")
        == operational_before
        and decisions[0].trajectory_lifting_sha256
        == default.trajectory_lifting_sha256
    )
    reason = _tick_failure_reason(
        mask=mask,
        candidate0_complete=decisions[0].eligible,
        operational_complete=default.eligible,
        equivalent=equivalent,
        candidate_expected=candidate_tensor_sha256,
        candidate_before=candidate_before,
        candidate_after=candidate_after,
        operational_expected=operational_top1_sha256,
        operational_before=operational_before,
        operational_after=operational_after,
    )
    payload = {
        "record_source_eligible": reason == "source_complete",
        "reason": reason,
        "selected_index": None,
        "candidate_tensor_sha256": candidate_tensor_sha256,
        "candidate_tensor_sha256_before": candidate_before,
        "candidate_tensor_sha256_after": candidate_after,
        "operational_top1_sha256": operational_top1_sha256,
        "operational_top1_sha256_before": operational_before,
        "operational_top1_sha256_after": operational_after,
        "candidate_source_eligible_mask": mask,
        "candidate_source_reasons": reasons,
        "candidate_receipts": [_decision_payload(item) for item in decisions],
        "operational_top1_receipt": _decision_payload(default),
        "dp_operational_top1_source_complete": default.eligible,
        "candidate0_operational_top1_equivalent": equivalent,
        "map_sha256": context.map_sha256,
        "source_sha256": context.source_sha256,
        "route_graph_sha256": context.route_graph_sha256,
        "provenance": dict(provenance),
    }
    payload["lifting_receipt_sha256"] = canonical_json_sha256(payload)
    return payload


def _array_sha256(value: Any, shape: Tuple[int, ...], name: str) -> str:
    try:
        actual_shape = tuple(int(item) for item in value.shape)
        dtype = str(value.dtype)
        payload = value.tobytes(order="C")
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a float32 array with shape {shape}") from exc
    if actual_shape != shape or dtype != "float32":
        raise ValueError(f"{name} must be a float32 array with shape {shape}")
    return hashlib.sha256(payload).hexdigest()


def _validate_sha256(value: str, name: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{name} SHA256 is invalid")


def _reject_forbidden_receipt_fields(value: Any) -> None:
    forbidden = ("expert_future", "holdout", "label", "outcome", "metric", "safety_cost")
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).casefold()
            if any(part in normalized for part in forbidden):
                raise ValueError(f"forbidden outcome field: {key}")
            _reject_forbidden_receipt_fields(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_forbidden_receipt_fields(item)


def _decision_payload(decision: CandidateLiftDecision) -> dict[str, Any]:
    return {
        "eligible": decision.eligible,
        "reason": decision.reason,
        "trajectory_lifting_sha256": decision.trajectory_lifting_sha256,
        "points": [asdict(point) for point in decision.points],
    }


def _tick_failure_reason(
    *,
    mask: Sequence[bool],
    candidate0_complete: bool,
    operational_complete: bool,
    equivalent: bool,
    candidate_expected: str,
    candidate_before: str,
    candidate_after: str,
    operational_expected: str,
    operational_before: str,
    operational_after: str,
) -> str:
    if candidate_expected != candidate_before:
        return "candidate_sha256_mismatch"
    if operational_expected != operational_before:
        return "operational_sha256_mismatch"
    if candidate_before != candidate_after:
        return "candidate_tensor_mutated"
    if operational_before != operational_after:
        return "operational_top1_mutated"
    if not any(mask):
        return "all_k_source_ineligible"
    if not candidate0_complete:
        return "candidate0_source_incomplete"
    if not operational_complete:
        return "dp_operational_top1_source_incomplete"
    if not equivalent:
        return "candidate0_operational_top1_mismatch"
    return "source_complete"


def _validate_lifting_context(context: RouteLiftingContext) -> None:
    if len(context.samples) < 2:
        raise ValueError("route lifting context needs at least two samples")
    if (
        not math.isfinite(context.route_sample_step_m)
        or context.route_sample_step_m <= 0
    ):
        raise ValueError("route sample step must be finite and positive")
    tolerances = context.tolerances
    for value in (
        tolerances.geometry_epsilon_m,
        tolerances.station_epsilon_m,
        tolerances.z_epsilon_m,
        tolerances.continuity_epsilon_m,
    ):
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("lifting tolerances must be finite and nonnegative")
    for digest in (
        context.map_sha256,
        context.source_sha256,
        context.route_graph_sha256,
    ):
        if len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise ValueError("lifting context SHA256 is invalid")
    for sample in context.samples:
        numeric = (sample.s, sample.x, sample.y, sample.z, sample.lane_width)
        if any(not math.isfinite(value) for value in numeric):
            raise ValueError("route surface sample must be finite")
        if sample.s < 0.0 or sample.lane_width <= 0.0 or sample.lane_id == 0:
            raise ValueError("route surface sample metadata is invalid")
    identities = {sample.identity for sample in context.samples}
    if any(
        source not in identities or target not in identities
        for source, target in context.edges
    ):
        raise ValueError("route edge identity is outside the frozen context")
    expected_directions = route_identity_directions(
        context.samples, context.tolerances.continuity_epsilon_m
    )
    if context.identity_directions != expected_directions:
        raise ValueError("route identity direction metadata mismatch")


def _inverse_transform_xy(
    candidate: Sequence[Sequence[float]],
    transform: Sequence[Sequence[float]],
) -> Tuple[Tuple[float, float], ...]:
    try:
        matrix = tuple(tuple(float(value) for value in row) for row in transform)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "agents_from_world_tf must be a finite planar homogeneous transform"
        ) from exc
    if (
        len(matrix) != 3
        or any(len(row) != 3 for row in matrix)
        or any(not math.isfinite(value) for row in matrix for value in row)
        or not all(
            math.isclose(value, expected, abs_tol=1e-9)
            for value, expected in zip(matrix[2], (0.0, 0.0, 1.0))
        )
    ):
        raise ValueError(
            "agents_from_world_tf must be a finite planar homogeneous transform"
        )
    a, b, tx = matrix[0]
    c, d, ty = matrix[1]
    determinant = a * d - b * c
    if (
        determinant <= 0.0
        or not math.isclose(a * a + b * b, 1.0, abs_tol=1e-6)
        or not math.isclose(c * c + d * d, 1.0, abs_tol=1e-6)
        or not math.isclose(a * c + b * d, 0.0, abs_tol=1e-6)
    ):
        raise ValueError("agents_from_world_tf must be a finite planar homogeneous transform")
    result = []
    for point in candidate:
        if len(point) < 2:
            raise ValueError("candidate points must contain x and y")
        ego_x, ego_y = float(point[0]), float(point[1])
        if not math.isfinite(ego_x) or not math.isfinite(ego_y):
            raise ValueError("candidate XY must be finite")
        shifted_x, shifted_y = ego_x - tx, ego_y - ty
        result.append((a * shifted_x + c * shifted_y, b * shifted_x + d * shifted_y))
    return tuple(result)


def _surface_chords(
    context: RouteLiftingContext,
) -> Tuple[Tuple[LaneSurfaceSample, LaneSurfaceSample], ...]:
    return tuple(
        (left, right)
        for left, right in zip(context.samples, context.samples[1:])
        if left.identity == right.identity
    )


def _unique_route_surface_match(
    world_x: float,
    world_y: float,
    context: RouteLiftingContext,
    chords: Sequence[Tuple[LaneSurfaceSample, LaneSurfaceSample]],
) -> Tuple[Optional[_SurfaceMatch], Optional[str]]:
    matches: Dict[RouteIdentity, list[_SurfaceMatch]] = {}
    for left, right in chords:
        dx, dy = right.x - left.x, right.y - left.y
        length_squared = dx * dx + dy * dy
        if length_squared <= 0.0:
            continue
        raw = ((world_x - left.x) * dx + (world_y - left.y) * dy) / length_squared
        if raw < 0.0 or raw > 1.0:
            continue
        projected_x, projected_y = left.x + raw * dx, left.y + raw * dy
        residual = math.hypot(world_x - projected_x, world_y - projected_y)
        width = left.lane_width + raw * (right.lane_width - left.lane_width)
        if residual > width / 2.0 + context.tolerances.geometry_epsilon_m:
            continue
        station = left.s + raw * (right.s - left.s)
        matches.setdefault(left.identity, []).append(
            _SurfaceMatch(
                left.road_id,
                left.section_id,
                left.lane_id,
                station,
                residual,
                left.is_junction,
            )
        )
    if not matches:
        return None, "lateral_residual_exceeds_tolerance"
    if len(matches) != 1:
        return None, "lane_identity_ambiguous"
    identity_matches = next(iter(matches.values()))
    stations = [match.s for match in identity_matches]
    if max(stations) - min(stations) > context.tolerances.station_epsilon_m:
        return None, "lane_station_ambiguous"
    return min(
        identity_matches,
        key=lambda match: (match.lateral_residual_m, match.s),
    ), None


def _xodr_receipt(
    candidate_index: int,
    point_index: int,
    ego_x: float,
    ego_y: float,
    world_x: float,
    world_y: float,
    match: _SurfaceMatch,
    map_api: Any,
    tolerances: LiftingTolerances,
) -> LiftedPointReceipt:
    try:
        waypoint = map_api.get_waypoint_xodr(
            int(match.road_id), int(match.lane_id), float(match.s)
        )
    except (AttributeError, TypeError, ValueError):
        waypoint = None
    if waypoint is None:
        return _failed_point_receipt(
            candidate_index,
            point_index,
            ego_x,
            ego_y,
            world_x,
            world_y,
            "xodr_waypoint_missing",
        )
    try:
        identity = (
            str(waypoint.road_id),
            int(waypoint.section_id),
            int(waypoint.lane_id),
        )
        station = float(waypoint.s)
        z = float(waypoint.transform.location.z)
        is_junction = bool(waypoint.is_junction)
    except (AttributeError, TypeError, ValueError):
        return _failed_point_receipt(
            candidate_index,
            point_index,
            ego_x,
            ego_y,
            world_x,
            world_y,
            "xodr_identity_mismatch",
        )
    if (
        identity != match.identity
        or is_junction != match.is_junction
        or not math.isfinite(station)
        or abs(station - match.s) > tolerances.station_epsilon_m
    ):
        return _failed_point_receipt(
            candidate_index,
            point_index,
            ego_x,
            ego_y,
            world_x,
            world_y,
            "xodr_identity_mismatch",
        )
    if not math.isfinite(z):
        return _failed_point_receipt(
            candidate_index,
            point_index,
            ego_x,
            ego_y,
            world_x,
            world_y,
            "xodr_elevation_missing",
        )
    return LiftedPointReceipt(
        candidate_index,
        point_index,
        ego_x,
        ego_y,
        world_x,
        world_y,
        match.road_id,
        match.section_id,
        match.lane_id,
        station,
        z,
        match.lateral_residual_m,
        True,
        True,
        True,
        "lifted",
    )


def _failed_point_receipt(
    candidate_index: int,
    point_index: int,
    ego_x: float,
    ego_y: float,
    world_x: float,
    world_y: float,
    reason: str,
) -> LiftedPointReceipt:
    return LiftedPointReceipt(
        candidate_index,
        point_index,
        ego_x,
        ego_y,
        world_x,
        world_y,
        None,
        None,
        None,
        None,
        None,
        None,
        False,
        False,
        False,
        reason,
    )


def _continuous(
    previous: Optional[LiftedPointReceipt],
    current: LiftedPointReceipt,
    departed: set[RouteIdentity],
    context: RouteLiftingContext,
) -> bool:
    if previous is None:
        return True
    assert previous.identity is not None and current.identity is not None
    assert previous.s is not None and current.s is not None
    if previous.identity == current.identity:
        direction = dict(context.identity_directions)[current.identity]
        return (
            direction * (current.s - previous.s)
            + context.tolerances.continuity_epsilon_m
            >= 0.0
        )
    return (
        current.identity not in departed
        and (previous.identity, current.identity) in set(context.edges)
    )


def project_world_point_to_segment(
    map_api: Any, location: Any, driving_lane_type: Any
) -> Optional[SegmentRef]:
    try:
        coordinates = tuple(float(getattr(location, axis)) for axis in ("x", "y", "z"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("CARLA world point must contain finite x,y,z") from exc
    if not all(math.isfinite(value) for value in coordinates):
        raise ValueError("CARLA world point must contain finite x,y,z")

    waypoint = map_api.get_waypoint(
        location,
        project_to_road=False,
        lane_type=driving_lane_type,
    )
    if waypoint is None:
        return None
    if waypoint.lane_type != driving_lane_type:
        raise ValueError("CARLA waypoint is not a driving lane")
    section_id = int(waypoint.section_id)
    lane_id = int(waypoint.lane_id)
    s = float(waypoint.s)
    if section_id < 0 or lane_id == 0 or not math.isfinite(s) or s < 0.0:
        raise ValueError("CARLA waypoint has invalid OpenDRIVE metadata")
    return SegmentRef(
        str(waypoint.road_id),
        section_id,
        lane_id,
        s,
        bool(waypoint.is_junction),
    )


def _speed_mps(raw: str, unit: str) -> float:
    value = float(raw)
    factors = {"m/s": 1.0, "mph": 0.44704, "km/h": 1.0 / 3.6}
    if unit not in factors:
        raise ValueError("unsupported OpenDRIVE speed unit: %s" % unit)
    value *= factors[unit]
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("OpenDRIVE speed must be finite and positive")
    return value


def parse_opendrive_speed_index(xml_text: str) -> OpenDriveSpeedIndex:
    root = ET.fromstring(xml_text)
    roads: Dict[str, RoadInfo] = {}
    for road in root.findall("road"):
        road_id = str(road.attrib["id"])
        junction_raw = road.get("junction", "-1")
        junction_id = None if junction_raw in {"", "-1"} else junction_raw
        speeds = tuple(
            sorted(
                (
                    float(type_node.get("s", "0")),
                    _speed_mps(speed.attrib["max"], speed.attrib["unit"]),
                )
                for type_node in road.findall("type")
                for speed in type_node.findall("speed")
            )
        )
        sections = []
        for section in road.findall("./lanes/laneSection"):
            sections.append(
                tuple(
                    sorted(
                        int(lane.attrib["id"])
                        for side in ("left", "right")
                        for lane in section.findall("./%s/lane" % side)
                        if lane.get("type") == "driving"
                    )
                )
            )

        def linked_roads(kind: str) -> Tuple[str, ...]:
            return tuple(
                sorted(
                    link.attrib["elementId"]
                    for link in road.findall("./link/%s" % kind)
                    if link.get("elementType") == "road"
                )
            )

        roads[road_id] = RoadInfo(
            road_id=road_id,
            junction_id=junction_id,
            speeds=speeds,
            driving_lanes_by_section=tuple(sections),
            predecessor_roads=linked_roads("predecessor"),
            successor_roads=linked_roads("successor"),
        )

    incoming: Dict[str, set[str]] = {}
    for connection in root.findall("./junction/connection"):
        connector = connection.get("connectingRoad")
        road_id = connection.get("incomingRoad")
        if connector is not None and road_id is not None:
            incoming.setdefault(connector, set()).add(road_id)
    return OpenDriveSpeedIndex(
        roads=roads,
        junction_incoming_by_connector={
            key: tuple(sorted(value)) for key, value in incoming.items()
        },
    )


def _reject(reason: str) -> SegmentSpeedDecision:
    return SegmentSpeedDecision(False, None, reason)


def resolve_landmark_segment_speed(
    segment: SegmentRef,
    landmarks: Sequence[LandmarkSpeedSource],
) -> SegmentSpeedDecision:
    candidates = [
        source
        for source in landmarks
        if source.road_id == segment.road_id
        and min(source.from_lane, source.to_lane)
        <= segment.lane_id
        <= max(source.from_lane, source.to_lane)
        and source.s <= segment.s
    ]
    if not candidates:
        return _reject("actor_landmark_mapping_missing")
    latest_s = max(source.s for source in candidates)
    latest = [source for source in candidates if source.s == latest_s]
    if len(latest) != 1:
        return _reject("actor_landmark_mapping_not_unique")
    try:
        speed = _speed_mps(str(latest[0].value), latest[0].unit)
    except (TypeError, ValueError):
        return _reject("actor_landmark_speed_not_finite_positive")
    return SegmentSpeedDecision(True, speed, "actor_landmark_exact_speed")


def _explicit_speed(road: RoadInfo, s: float) -> Optional[float]:
    available = [value for start, value in road.speeds if start <= s]
    return available[-1] if available else None


def _validate_segment(
    segment: SegmentRef, index: OpenDriveSpeedIndex
) -> Tuple[Optional[RoadInfo], Optional[SegmentSpeedDecision]]:
    road = index.roads.get(segment.road_id)
    if road is None:
        return None, _reject("road_missing")
    if (road.junction_id is not None) != segment.is_junction:
        return None, _reject("junction_flag_mismatch")
    if segment.section_id < 0 or segment.section_id >= len(
        road.driving_lanes_by_section
    ):
        return None, _reject("lane_section_missing")
    if segment.lane_id not in road.driving_lanes_by_section[segment.section_id]:
        return None, _reject("driving_lane_missing")
    return road, None


def _topology_speed(
    road: RoadInfo, index: OpenDriveSpeedIndex
) -> SegmentSpeedDecision:
    incoming = index.junction_incoming_by_connector.get(road.road_id, ())
    if (
        len(road.predecessor_roads) != 1
        or len(road.successor_roads) != 1
        or incoming != road.predecessor_roads
    ):
        return _reject("junction_topology_not_unique_two_sided")
    adjacent_ids = road.predecessor_roads + road.successor_roads
    values = []
    for road_id in adjacent_ids:
        adjacent = index.roads.get(road_id)
        if adjacent is None or adjacent.junction_id is not None:
            return _reject("junction_adjacent_road_missing_or_junction")
        unique = {value for _, value in adjacent.speeds}
        if not unique:
            return _reject("junction_adjacent_explicit_speed_missing")
        if len(unique) != 1:
            return _reject("junction_adjacent_road_speed_not_constant")
        values.extend(unique)
    if len(set(values)) != 1:
        return _reject("junction_adjacent_speeds_not_identical")
    return SegmentSpeedDecision(True, values[0], "topology_derived_exact_speed")


def resolve_segment_speed(
    segment: SegmentRef,
    index: OpenDriveSpeedIndex,
    actor_values: Mapping[SegmentKey, Sequence[float]],
    rung: str,
) -> SegmentSpeedDecision:
    if rung not in _RUNGS:
        raise ValueError("unknown exact-speed rung: %s" % rung)
    road, failure = _validate_segment(segment, index)
    if failure is not None:
        return failure
    assert road is not None

    if rung == RUNG_ACTOR_LANDMARK:
        values = tuple(actor_values.get(segment.key, ()))
        if not values:
            return _reject("actor_landmark_mapping_missing")
        if len(values) != 1:
            return _reject("actor_landmark_mapping_not_unique")
        value = float(values[0])
        if not math.isfinite(value) or value <= 0.0:
            return _reject("actor_landmark_speed_not_finite_positive")
        return SegmentSpeedDecision(True, value, "actor_landmark_exact_speed")

    if road.junction_id is None:
        value = _explicit_speed(road, segment.s)
        if value is None:
            return _reject("explicit_road_speed_missing")
        return SegmentSpeedDecision(True, value, "explicit_non_junction_speed")
    if rung == RUNG_EXPLICIT_NON_JUNCTION:
        return _reject("junction_not_allowed_by_rung_b")
    return _topology_speed(road, index)


def candidate_source_mask(
    candidate_segments: Sequence[SegmentRef],
    index: OpenDriveSpeedIndex,
    actor_values: Mapping[SegmentKey, Sequence[float]],
    rung: str,
) -> CandidateSourceDecision:
    if not candidate_segments:
        return CandidateSourceDecision(False, (), "candidate_segments_empty")
    speeds = []
    for position, segment in enumerate(candidate_segments):
        decision = resolve_segment_speed(segment, index, actor_values, rung)
        if not decision.eligible:
            return CandidateSourceDecision(
                False, (), "segment_%d:%s" % (position, decision.reason)
            )
        assert decision.speed_mps is not None
        speeds.append(decision.speed_mps)
    return CandidateSourceDecision(True, tuple(speeds), "source_complete")
