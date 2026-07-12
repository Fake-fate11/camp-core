from __future__ import annotations

import math

from camp_core.integrations.carla_exact_speed_source import (
    RUNG_ACTOR_LANDMARK,
    RUNG_EXPLICIT_NON_JUNCTION,
    RUNG_TOPOLOGY_DERIVED_JUNCTION,
    SegmentRef,
    candidate_source_mask,
    parse_opendrive_speed_index,
    resolve_segment_speed,
)


XODR = """
<OpenDRIVE>
  <road id="1" junction="-1" length="20">
    <link><successor elementType="junction" elementId="10"/></link>
    <type s="0"><speed max="25" unit="mph"/></type>
    <lanes><laneSection s="0"><left><lane id="1" type="driving"><width sOffset="0" a="3" b="0" c="0" d="0"/></lane></left></laneSection></lanes>
  </road>
  <road id="2" junction="10" length="5">
    <link>
      <predecessor elementType="road" elementId="1" contactPoint="end"/>
      <successor elementType="road" elementId="3" contactPoint="start"/>
    </link>
    <lanes><laneSection s="0"><left><lane id="1" type="driving"><width sOffset="0" a="3" b="0" c="0" d="0"/></lane></left></laneSection></lanes>
  </road>
  <road id="3" junction="-1" length="20">
    <link><predecessor elementType="junction" elementId="10"/></link>
    <type s="0"><speed max="25" unit="mph"/></type>
    <lanes><laneSection s="0"><left><lane id="1" type="driving"><width sOffset="0" a="3" b="0" c="0" d="0"/></lane></left></laneSection></lanes>
  </road>
  <junction id="10">
    <connection id="0" incomingRoad="1" connectingRoad="2" contactPoint="start"/>
  </junction>
</OpenDRIVE>
"""


def _segment(road_id: str, *, junction: bool = False) -> SegmentRef:
    return SegmentRef(
        road_id=road_id,
        section_id=0,
        lane_id=1,
        s=1.0,
        is_junction=junction,
    )


def test_rung_a_requires_one_unique_official_mapping() -> None:
    index = parse_opendrive_speed_index(XODR)
    segment = _segment("1")

    accepted = resolve_segment_speed(
        segment,
        index,
        {segment.key: (30.0 / 3.6,)},
        RUNG_ACTOR_LANDMARK,
    )
    missing = resolve_segment_speed(
        segment, index, {}, RUNG_ACTOR_LANDMARK
    )
    ambiguous = resolve_segment_speed(
        segment,
        index,
        {segment.key: (30.0 / 3.6, 30.0 / 3.6)},
        RUNG_ACTOR_LANDMARK,
    )

    assert accepted.eligible is True
    assert math.isclose(accepted.speed_mps, 30.0 / 3.6)
    assert missing.reason == "actor_landmark_mapping_missing"
    assert ambiguous.reason == "actor_landmark_mapping_not_unique"


def test_rung_b_accepts_explicit_non_junction_and_rejects_junction() -> None:
    index = parse_opendrive_speed_index(XODR)

    road = resolve_segment_speed(
        _segment("1"), index, {}, RUNG_EXPLICIT_NON_JUNCTION
    )
    connector = resolve_segment_speed(
        _segment("2", junction=True),
        index,
        {},
        RUNG_EXPLICIT_NON_JUNCTION,
    )

    assert road.eligible is True
    assert math.isclose(road.speed_mps, 25.0 * 0.44704)
    assert connector.reason == "junction_not_allowed_by_rung_b"


def test_rung_c_accepts_only_unique_all_adjacent_equal_topology() -> None:
    accepted = resolve_segment_speed(
        _segment("2", junction=True),
        parse_opendrive_speed_index(XODR),
        {},
        RUNG_TOPOLOGY_DERIVED_JUNCTION,
    )
    unequal = resolve_segment_speed(
        _segment("2", junction=True),
        parse_opendrive_speed_index(XODR.replace('max="25" unit="mph"/></type>\n    <lanes><laneSection s="0"><left><lane id="1" type="driving"', 'max="35" unit="mph"/></type>\n    <lanes><laneSection s="0"><left><lane id="1" type="driving"', 1)),
        {},
        RUNG_TOPOLOGY_DERIVED_JUNCTION,
    )
    one_sided = resolve_segment_speed(
        _segment("2", junction=True),
        parse_opendrive_speed_index(
            XODR.replace(
                '<successor elementType="road" elementId="3" contactPoint="start"/>',
                "",
            )
        ),
        {},
        RUNG_TOPOLOGY_DERIVED_JUNCTION,
    )

    assert accepted.eligible is True
    assert math.isclose(accepted.speed_mps, 25.0 * 0.44704)
    assert unequal.reason == "junction_adjacent_speeds_not_identical"
    assert one_sided.reason == "junction_topology_not_unique_two_sided"


def test_candidate_mask_is_all_segment_conjunction() -> None:
    index = parse_opendrive_speed_index(XODR)
    accepted = candidate_source_mask(
        [_segment("1"), _segment("3")],
        index,
        {},
        RUNG_EXPLICIT_NON_JUNCTION,
    )
    rejected = candidate_source_mask(
        [_segment("1"), _segment("2", junction=True), _segment("3")],
        index,
        {},
        RUNG_EXPLICIT_NON_JUNCTION,
    )

    assert accepted.eligible is True
    assert len(accepted.speed_mps) == 2
    assert rejected.eligible is False
    assert rejected.reason == "segment_1:junction_not_allowed_by_rung_b"
    assert rejected.speed_mps == ()
