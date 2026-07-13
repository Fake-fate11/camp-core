from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.integrations.carla_exact_speed_source import (
    RUNG_ACTOR_LANDMARK,
    RUNG_EXPLICIT_NON_JUNCTION,
    RUNG_TOPOLOGY_DERIVED_JUNCTION,
    LaneSurfaceSample,
    LandmarkSpeedSource,
    LiftingTolerances,
    RouteLiftingContext,
    SegmentRef,
    candidate_source_mask,
    freeze_lifting_tolerances,
    lift_k8_route_receipt,
    lift_candidate_to_route_surface,
    project_world_point_to_segment,
    resolve_landmark_segment_speed,
    parse_opendrive_speed_index,
    resolve_segment_speed,
)
from camp_core.integrations.diffusion_planner_v19_nuplan_bridge import array_sha256


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


def test_landmark_mapping_uses_unique_same_road_lane_predecessor_only() -> None:
    segment = SegmentRef("1", 0, 2, 20.0, False)
    landmarks = (
        LandmarkSpeedSource("sign-a", "1", 10.0, 1, 3, 30.0, "mph"),
        LandmarkSpeedSource("sign-b", "1", 30.0, 1, 3, 60.0, "mph"),
        LandmarkSpeedSource("other-road", "2", 15.0, 1, 3, 90.0, "mph"),
    )

    decision = resolve_landmark_segment_speed(segment, landmarks)

    assert decision.eligible is True
    assert math.isclose(decision.speed_mps, 30.0 * 0.44704)
    assert decision.reason == "actor_landmark_exact_speed"


def test_landmark_mapping_rejects_missing_lane_and_duplicate_latest_source() -> None:
    segment = SegmentRef("1", 0, -1, 20.0, False)
    wrong_lane = (
        LandmarkSpeedSource("sign-a", "1", 10.0, 1, 3, 30.0, "mph"),
    )
    duplicate = (
        LandmarkSpeedSource("sign-a", "1", 10.0, -3, -1, 30.0, "mph"),
        LandmarkSpeedSource("sign-b", "1", 10.0, -3, -1, 30.0, "mph"),
    )

    assert (
        resolve_landmark_segment_speed(segment, wrong_lane).reason
        == "actor_landmark_mapping_missing"
    )
    assert (
        resolve_landmark_segment_speed(segment, duplicate).reason
        == "actor_landmark_mapping_not_unique"
    )


def test_world_point_projection_is_strict_and_fail_closed() -> None:
    location = SimpleNamespace(x=1.0, y=2.0, z=0.0)
    driving = object()
    calls = []

    class Map:
        waypoint = SimpleNamespace(
            road_id=7,
            section_id=2,
            lane_id=-1,
            s=12.5,
            is_junction=False,
            lane_type=driving,
        )

        def get_waypoint(self, point, *, project_to_road, lane_type):
            calls.append((point, project_to_road, lane_type))
            return self.waypoint

    map_api = Map()
    assert project_world_point_to_segment(map_api, location, driving) == SegmentRef(
        "7", 2, -1, 12.5, False
    )
    assert calls == [(location, False, driving)]

    map_api.waypoint = None
    assert project_world_point_to_segment(map_api, location, driving) is None

    map_api.waypoint = SimpleNamespace(
        road_id=7,
        section_id=2,
        lane_id=-1,
        s=12.5,
        is_junction=False,
        lane_type=object(),
    )
    with pytest.raises(ValueError, match="not a driving lane"):
        project_world_point_to_segment(map_api, location, driving)

    with pytest.raises(ValueError, match="finite x,y,z"):
        project_world_point_to_segment(
            map_api, SimpleNamespace(x=math.nan, y=2.0, z=0.0), driving
        )


class _FakeXodrMap:
    def __init__(
        self,
        *,
        z: float = 3.5,
        missing: bool = False,
        section_id: int = 0,
        is_junction: bool = False,
    ) -> None:
        self.z = z
        self.missing = missing
        self.section_id = section_id
        self.is_junction = is_junction

    def get_waypoint_xodr(self, road_id: int, lane_id: int, s: float):
        if self.missing:
            return None
        return SimpleNamespace(
            road_id=road_id,
            section_id=self.section_id,
            lane_id=lane_id,
            s=s,
            is_junction=self.is_junction,
            transform=SimpleNamespace(location=SimpleNamespace(z=self.z)),
        )


def _surface_samples(
    *,
    road_id: str = "1",
    lane_id: int = 1,
    start: int = 0,
    stop: int = 80,
    y: float = 20.0,
) -> tuple[LaneSurfaceSample, ...]:
    return tuple(
        LaneSurfaceSample(
            road_id=road_id,
            section_id=0,
            lane_id=lane_id,
            s=float(index),
            x=10.0 + float(index),
            y=y,
            z=3.5,
            lane_width=4.0,
            is_junction=False,
        )
        for index in range(start, stop + 1)
    )


def _route_context(
    samples: tuple[LaneSurfaceSample, ...],
    *,
    edges=(),
) -> RouteLiftingContext:
    return RouteLiftingContext(
        samples=samples,
        edges=tuple(edges),
        route_sample_step_m=1.0,
        tolerances=LiftingTolerances(
            geometry_epsilon_m=1e-6,
            station_epsilon_m=1e-6,
            z_epsilon_m=1e-6,
            continuity_epsilon_m=1e-6,
        ),
        map_sha256="a" * 64,
        source_sha256="b" * 64,
        route_graph_sha256="c" * 64,
    )


def _candidate(*, y: float = 0.0) -> tuple[tuple[float, ...], ...]:
    return tuple((float(index), y, 1.0, 0.0) for index in range(80))


def _lift(
    candidate=None,
    *,
    context=None,
    map_api=None,
):
    return lift_candidate_to_route_surface(
        candidate_index=0,
        candidate=_candidate() if candidate is None else candidate,
        agents_from_world_tf=(
            (1.0, 0.0, -10.0),
            (0.0, 1.0, -20.0),
            (0.0, 0.0, 1.0),
        ),
        context=(
            _route_context(_surface_samples()) if context is None else context
        ),
        map_api=_FakeXodrMap() if map_api is None else map_api,
    )


def test_route_lift_uses_unique_surface_and_official_xodr_z() -> None:
    candidate = _candidate()
    before = tuple(candidate)

    result = _lift(candidate)

    assert result.eligible is True
    assert result.reason == "source_complete"
    assert len(result.points) == 80
    assert result.points[0].world_x == 10.0
    assert result.points[0].world_y == 20.0
    assert result.points[0].z == 3.5
    assert result.points[-1].point_index == 79
    assert len(result.trajectory_lifting_sha256) == 64
    assert tuple(candidate) == before


@pytest.mark.parametrize(
    ("fixture", "reason"),
    [
        ("overlapping_lanes", "lane_identity_ambiguous"),
        ("station_ambiguity", "lane_station_ambiguous"),
        ("outside_surface", "lateral_residual_exceeds_tolerance"),
        ("missing_xodr", "xodr_waypoint_missing"),
        ("wrong_section", "xodr_identity_mismatch"),
        ("wrong_junction", "xodr_identity_mismatch"),
        ("backward_station", "route_topology_discontinuous"),
        ("branch_hop", "route_topology_discontinuous"),
    ],
)
def test_route_lift_fails_closed_with_all_point_receipts(
    fixture: str, reason: str
) -> None:
    candidate = _candidate()
    context = _route_context(_surface_samples())
    map_api = _FakeXodrMap()
    if fixture == "overlapping_lanes":
        context = _route_context(
            _surface_samples() + _surface_samples(road_id="2", lane_id=2)
        )
    elif fixture == "station_ambiguity":
        context = _route_context(
            (
                LaneSurfaceSample("1", 0, 1, 0.0, 10.0, 20.0, 3.5, 4.0, False),
                LaneSurfaceSample("1", 0, 1, 80.0, 90.0, 20.0, 3.5, 4.0, False),
                LaneSurfaceSample("1", 0, 1, 100.0, 10.0, 20.0, 3.5, 4.0, False),
                LaneSurfaceSample("1", 0, 1, 180.0, 90.0, 20.0, 3.5, 4.0, False),
            )
        )
    elif fixture == "outside_surface":
        candidate = _candidate(y=10.0)
    elif fixture == "missing_xodr":
        map_api = _FakeXodrMap(missing=True)
    elif fixture == "wrong_section":
        map_api = _FakeXodrMap(section_id=1)
    elif fixture == "wrong_junction":
        map_api = _FakeXodrMap(is_junction=True)
    elif fixture == "backward_station":
        candidate = tuple(
            (float(index if index < 40 else 79 - index), 0.0, 1.0, 0.0)
            for index in range(80)
        )
    elif fixture == "branch_hop":
        context = _route_context(
            _surface_samples(stop=39)
            + _surface_samples(road_id="2", lane_id=2, start=40)
        )

    result = _lift(candidate, context=context, map_api=map_api)

    assert result.eligible is False
    assert result.reason == reason
    assert len(result.points) == 80
    assert any(point.reason == reason for point in result.points)


def test_route_lift_rejects_nonfinite_transform() -> None:
    with pytest.raises(ValueError, match="finite planar homogeneous"):
        lift_candidate_to_route_surface(
            candidate_index=0,
            candidate=_candidate(),
            agents_from_world_tf=(
                (1.0, 0.0, math.nan),
                (0.0, 1.0, 0.0),
                (0.0, 0.0, 1.0),
            ),
            context=_route_context(_surface_samples()),
            map_api=_FakeXodrMap(),
        )


def test_route_lift_rejects_edges_outside_frozen_context() -> None:
    context = _route_context(
        _surface_samples(),
        edges=((('9', 0, 1), ('1', 0, 1)),),
    )

    with pytest.raises(ValueError, match="route edge identity"):
        _lift(context=context)


def test_tolerance_freeze_is_deterministic_and_source_sensitive() -> None:
    first = freeze_lifting_tolerances(
        max_chord_error_m=0.01,
        max_station_roundtrip_error_m=0.02,
        max_z_roundtrip_error_m=0.03,
        coordinate_scale_m=1000.0,
    )
    second = freeze_lifting_tolerances(
        max_chord_error_m=0.01,
        max_station_roundtrip_error_m=0.02,
        max_z_roundtrip_error_m=0.03,
        coordinate_scale_m=1000.0,
    )
    changed = freeze_lifting_tolerances(
        max_chord_error_m=0.01,
        max_station_roundtrip_error_m=0.02,
        max_z_roundtrip_error_m=0.04,
        coordinate_scale_m=1000.0,
    )

    assert first == second
    assert first != changed
    assert first.geometry_epsilon_m > 0.01
    assert first.station_epsilon_m > 0.02
    assert first.z_epsilon_m > 0.03
    assert first.continuity_epsilon_m == first.station_epsilon_m


def _k8_candidates(*, y: float = 0.0) -> np.ndarray:
    candidate = np.asarray(_candidate(y=y), dtype=np.float32)
    return np.repeat(candidate[None, :, :], 8, axis=0)


def _lifting_provenance() -> dict[str, object]:
    return {
        "scenario_token": "source-only-scenario",
        "agents_from_world_tf_sha256": "d" * 64,
        "baseline_name": "DP operational Top-1",
        "native_ranked_top1": False,
    }


def _lift_k8(
    candidates: np.ndarray,
    *,
    operational_top1: np.ndarray | None = None,
    map_api=None,
    candidate_tensor_sha256: str | None = None,
    operational_top1_sha256: str | None = None,
):
    default = candidates[0].copy() if operational_top1 is None else operational_top1
    return lift_k8_route_receipt(
        candidates=candidates,
        operational_top1=default,
        agents_from_world_tf=(
            (1.0, 0.0, -10.0),
            (0.0, 1.0, -20.0),
            (0.0, 0.0, 1.0),
        ),
        context=_route_context(_surface_samples()),
        map_api=_FakeXodrMap() if map_api is None else map_api,
        candidate_tensor_sha256=(
            array_sha256(candidates)
            if candidate_tensor_sha256 is None
            else candidate_tensor_sha256
        ),
        operational_top1_sha256=(
            array_sha256(default)
            if operational_top1_sha256 is None
            else operational_top1_sha256
        ),
        provenance=_lifting_provenance(),
    )


def test_k8_receipt_preserves_tensor_and_matches_operational_top1() -> None:
    candidates = _k8_candidates()
    before = candidates.copy()

    receipt = _lift_k8(candidates)

    np.testing.assert_array_equal(candidates, before)
    assert receipt["record_source_eligible"] is True
    assert receipt["candidate_source_eligible_mask"] == [True] * 8
    assert receipt["dp_operational_top1_source_complete"] is True
    assert receipt["candidate0_operational_top1_equivalent"] is True
    assert receipt["selected_index"] is None
    assert (
        receipt["candidate_receipts"][0]["trajectory_lifting_sha256"]
        == receipt["operational_top1_receipt"]["trajectory_lifting_sha256"]
    )
    assert (
        receipt["candidate_receipts"][0]["trajectory_lifting_sha256"]
        == receipt["candidate_receipts"][1]["trajectory_lifting_sha256"]
    )


@pytest.mark.parametrize("sha_field", ["candidate", "operational"])
def test_k8_receipt_fails_closed_on_input_sha_drift(sha_field: str) -> None:
    candidates = _k8_candidates()
    kwargs = {
        "candidate_tensor_sha256": "0" * 64,
    } if sha_field == "candidate" else {
        "operational_top1_sha256": "0" * 64,
    }

    receipt = _lift_k8(candidates, **kwargs)

    assert receipt["record_source_eligible"] is False
    assert receipt["reason"] == f"{sha_field}_sha256_mismatch"
    assert len(receipt["candidate_source_eligible_mask"]) == 8
    assert receipt["selected_index"] is None


def test_k8_receipt_fails_closed_on_operational_xy_drift() -> None:
    candidates = _k8_candidates()
    operational = candidates[0].copy()
    operational[0, 0] += np.float32(0.25)

    receipt = _lift_k8(candidates, operational_top1=operational)

    assert receipt["record_source_eligible"] is False
    assert receipt["reason"] == "candidate0_operational_top1_mismatch"
    assert receipt["candidate0_operational_top1_equivalent"] is False
    assert receipt["selected_index"] is None


class _OperationalZDriftMap(_FakeXodrMap):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def get_waypoint_xodr(self, road_id: int, lane_id: int, s: float):
        self.calls += 1
        self.z = 3.5 if self.calls <= 640 else 4.0
        return super().get_waypoint_xodr(road_id, lane_id, s)


def test_k8_receipt_fails_closed_on_independent_lifting_drift() -> None:
    receipt = _lift_k8(_k8_candidates(), map_api=_OperationalZDriftMap())

    assert receipt["record_source_eligible"] is False
    assert receipt["reason"] == "candidate0_operational_top1_mismatch"
    assert receipt["candidate0_operational_top1_equivalent"] is False


def test_k8_receipt_requires_candidate0_source_complete() -> None:
    candidates = _k8_candidates()
    candidates[0, :, 1] = np.float32(10.0)

    receipt = _lift_k8(candidates)

    assert receipt["record_source_eligible"] is False
    assert receipt["reason"] == "candidate0_source_incomplete"
    assert receipt["candidate_source_eligible_mask"][0] is False
    assert any(receipt["candidate_source_eligible_mask"][1:])
    assert receipt["selected_index"] is None


def test_k8_receipt_retains_all_reasons_when_all_k_ineligible() -> None:
    receipt = _lift_k8(_k8_candidates(y=10.0))

    assert receipt["record_source_eligible"] is False
    assert receipt["reason"] == "all_k_source_ineligible"
    assert receipt["candidate_source_eligible_mask"] == [False] * 8
    assert len(receipt["candidate_source_reasons"]) == 8
    assert receipt["selected_index"] is None


def test_k8_receipt_rejects_outcome_provenance() -> None:
    candidates = _k8_candidates()

    with pytest.raises(ValueError, match="forbidden outcome field"):
        lift_k8_route_receipt(
            candidates=candidates,
            operational_top1=candidates[0].copy(),
            agents_from_world_tf=((1.0, 0.0, 0.0),) * 3,
            context=_route_context(_surface_samples()),
            map_api=_FakeXodrMap(),
            candidate_tensor_sha256=array_sha256(candidates),
            operational_top1_sha256=array_sha256(candidates[0]),
            provenance={"safety_cost": 0.0},
        )
