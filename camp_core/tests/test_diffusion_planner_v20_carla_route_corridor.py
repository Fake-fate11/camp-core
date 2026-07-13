from types import SimpleNamespace

import pytest

from camp_core.integrations.carla_causal_adapter import (
    build_pre_generation_route_corridor,
)
from camp_core.integrations.carla_exact_speed_source import (
    LaneSectionBounds,
    parse_opendrive_lane_section_bounds,
)


XODR = """\
<OpenDRIVE>
  <road id="1" length="100">
    <lanes>
      <laneSection s="0" />
      <laneSection s="40" />
    </lanes>
  </road>
  <road id="2" length="25">
    <lanes>
      <laneSection s="0" />
    </lanes>
  </road>
</OpenDRIVE>
"""


class _Waypoint:
    def __init__(
        self,
        road_id: int,
        section_id: int,
        lane_id: int,
        s: float,
        x: float,
        *,
        predecessors=(),
        lane_width: float = 3.5,
        is_junction: bool = False,
    ) -> None:
        self.road_id = road_id
        self.section_id = section_id
        self.lane_id = lane_id
        self.s = s
        self.transform = SimpleNamespace(
            location=SimpleNamespace(x=x, y=0.0, z=0.0)
        )
        self.lane_width = lane_width
        self.is_junction = is_junction
        self._predecessors = tuple(predecessors)
        self.previous_calls = []

    def previous(self, distance: float):
        self.previous_calls.append(distance)
        return list(self._predecessors)


class _Map:
    def __init__(self, contact_gap_m: float = 0.0, lane_width: float = 3.5) -> None:
        self.contact_gap_m = contact_gap_m
        self.lane_width = lane_width
        self.xodr_calls = []

    def get_waypoint_xodr(self, road_id: int, lane_id: int, s: float):
        self.xodr_calls.append((road_id, lane_id, s))
        section_id = 0 if road_id == 2 or s < 40.0 else 1
        x = s if road_id == 1 else 40.0 + self.contact_gap_m + s
        return _Waypoint(
            road_id,
            section_id,
            lane_id,
            s,
            x,
            lane_width=self.lane_width,
        )


def _route_and_map(predecessor_count: int, contact_gap_m: float = 0.0):
    predecessors = [
        _Waypoint(1, 0, -1, 5.0 - index, 5.0 - index)
        for index in range(predecessor_count)
    ]
    route = [
        _Waypoint(1, 0, -1, 10.0, 10.0, predecessors=predecessors),
        _Waypoint(1, 0, -1, 20.0, 20.0),
        _Waypoint(2, 0, -1, 5.0, 45.0 + contact_gap_m),
        _Waypoint(2, 0, -1, 10.0, 50.0 + contact_gap_m),
    ]
    return route, _Map(contact_gap_m)


def _waypoint_record(waypoint: _Waypoint):
    location = waypoint.transform.location
    return (
        waypoint.road_id,
        waypoint.section_id,
        waypoint.lane_id,
        waypoint.s,
        location.x,
        location.y,
        location.z,
    )


def _corridor(route, map_api, contact_tolerance_m: float = 0.01):
    return build_pre_generation_route_corridor(
        route=route,
        map_api=map_api,
        opendrive_xml=XODR,
        route_sample_step_m=5.0,
        station_allowance_m=3.0518578125e-05,
        contact_tolerance_m=contact_tolerance_m,
    )


def test_lane_section_bounds_use_next_start_or_road_length() -> None:
    bounds = parse_opendrive_lane_section_bounds(XODR)

    assert bounds == (
        LaneSectionBounds("1", 0, 0.0, 40.0),
        LaneSectionBounds("1", 1, 40.0, 100.0),
        LaneSectionBounds("2", 0, 0.0, 25.0),
    )


def test_lane_section_bounds_reject_duplicate_starts() -> None:
    invalid = XODR.replace('<laneSection s="40" />', '<laneSection s="0" />')

    with pytest.raises(ValueError, match="lane-section bounds"):
        parse_opendrive_lane_section_bounds(invalid)


def test_corridor_adds_unique_predecessor_without_changing_route() -> None:
    route, map_api = _route_and_map(predecessor_count=1)
    original = tuple(_waypoint_record(item) for item in route)

    corridor = build_pre_generation_route_corridor(
        route=route,
        map_api=map_api,
        opendrive_xml=XODR,
        route_sample_step_m=5.0,
        station_allowance_m=3.0518578125e-05,
        contact_tolerance_m=0.01,
    )

    assert tuple(_waypoint_record(item) for item in route) == original
    assert route[0].previous_calls == [5.0]
    assert corridor["predecessor_receipt"]["predecessor_count"] == 1
    assert corridor["predecessor_receipt"]["route_step_m"] == 5.0
    assert corridor["route_samples"][0]["s"] < route[0].s
    assert len(corridor["corridor_sha256"]) == 64


def test_corridor_requires_five_meter_step_before_predecessor_lookup() -> None:
    route, map_api = _route_and_map(predecessor_count=1)

    with pytest.raises(ValueError, match="route step must equal 5.0"):
        build_pre_generation_route_corridor(
            route=route,
            map_api=map_api,
            opendrive_xml=XODR,
            route_sample_step_m=4.0,
            station_allowance_m=3.0518578125e-05,
            contact_tolerance_m=0.01,
        )

    assert route[0].previous_calls == []


@pytest.mark.parametrize("predecessor_count", [0, 2])
def test_corridor_requires_exactly_one_predecessor(predecessor_count: int) -> None:
    route, map_api = _route_and_map(predecessor_count=predecessor_count)

    with pytest.raises(ValueError, match="exactly one predecessor"):
        build_pre_generation_route_corridor(
            route=route,
            map_api=map_api,
            opendrive_xml=XODR,
            route_sample_step_m=5.0,
            station_allowance_m=3.0518578125e-05,
            contact_tolerance_m=0.01,
        )


def test_corridor_records_inward_verified_boundary_samples() -> None:
    route, map_api = _route_and_map(predecessor_count=1)

    corridor = _corridor(route, map_api)

    first = corridor["boundary_receipts"][0]
    assert first["exact_entry_s"] == 0.0
    assert first["lookup_entry_s"] == pytest.approx(3.0518578125e-05)
    assert first["direction"] == 1
    assert map_api.xodr_calls
    assert all(item["identity_verified"] for item in corridor["boundary_receipts"])
    assert set(first) == {
        "identity",
        "direction",
        "exact_entry_s",
        "exact_exit_s",
        "lookup_entry_s",
        "lookup_exit_s",
        "entry_xyz",
        "exit_xyz",
        "contact_to_next_m",
        "identity_verified",
    }


def test_corridor_rejects_unsupported_boundary_contact() -> None:
    route, map_api = _route_and_map(predecessor_count=1, contact_gap_m=0.02)

    with pytest.raises(ValueError, match="boundary contact"):
        _corridor(route, map_api, contact_tolerance_m=0.01)


def test_corridor_rejects_invalid_boundary_lane_width() -> None:
    route, _ = _route_and_map(predecessor_count=1)

    with pytest.raises(ValueError, match="waypoint metadata"):
        _corridor(route, _Map(lane_width=float("nan")))
