from __future__ import annotations

from dataclasses import dataclass
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
