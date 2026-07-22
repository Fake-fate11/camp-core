from __future__ import annotations

import copy
import xml.etree.ElementTree as ET

import pytest
from pyproj import Transformer

from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (
    SPLIT_PLAN,
    build_signal_complete_suite,
    validate_signal_complete_suite,
)


def test_signal_complete_suites_are_deterministic_and_zero_overlap() -> None:
    calibration = build_signal_complete_suite("calibration")
    calibration_repeat = build_signal_complete_suite("calibration")
    fresh = build_signal_complete_suite("fresh_b2")

    assert calibration == calibration_repeat
    assert calibration["map_count"] == 5
    assert calibration["corridor_count"] == 50
    assert calibration["route_count"] == 50
    assert fresh["map_count"] == 25
    assert fresh["corridor_count"] == 100
    assert fresh["route_count"] == 100
    assert set(calibration["source_independent_geometry_sha256"]).isdisjoint(
        fresh["source_independent_geometry_sha256"]
    )
    assert validate_signal_complete_suite(calibration)["route_count"] == 50
    assert validate_signal_complete_suite(fresh)["route_count"] == 100


def test_lanelet2_geodetic_nodes_roundtrip_to_frozen_local_metric_geometry() -> None:
    suite = build_signal_complete_suite("calibration")
    payload = next(iter(suite["map_payloads"].values()))
    root = ET.fromstring(payload)
    nodes = root.findall("node")
    assert len(nodes) > 2
    assert nodes[0].attrib["lat"] == "35.000000000000"
    assert nodes[0].attrib["lon"] == "139.000000000000"
    projector = Transformer.from_crs("EPSG:4326", "EPSG:32654", always_xy=True)
    origin_easting, origin_northing = projector.transform(139.0, 35.0)
    for node in nodes:
        tags = {
            tag.attrib["k"]: tag.attrib["v"] for tag in node.findall("tag")
        }
        easting, northing = projector.transform(
            float(node.attrib["lon"]), float(node.attrib["lat"])
        )
        assert easting - origin_easting == pytest.approx(
            float(tags["local_x"]), abs=1e-5
        )
        assert northing - origin_northing == pytest.approx(
            float(tags["local_y"]), abs=1e-5
        )


@pytest.mark.parametrize("split", tuple(SPLIT_PLAN))
def test_every_route_has_exact_signal_chain_and_no_future_phase(split: str) -> None:
    suite = build_signal_complete_suite(split)
    for map_receipt in suite["maps"]:
        payload = suite["map_payloads"][map_receipt["relative_path"]]
        root = ET.fromstring(payload)
        ways = {int(way.attrib["id"]): way for way in root.findall("way")}
        relations = {
            int(relation.attrib["id"]): relation
            for relation in root.findall("relation")
        }
        for row in map_receipt["routes"]:
            chain = row["source_chain"]
            regulation = relations[chain["traffic_light_regulatory_element_id"]]
            roles = {
                member.attrib["role"] for member in regulation.findall("member")
            }
            assert roles == {"ref_line", "refers", "light_bulbs"}
            assert chain["controlled_lanelet_id"] == chain["route_lanelet_ids"][0]
            assert ways[chain["certified_stop_line_id"]].find(
                "tag[@k='type'][@v='stop_line']"
            ) is not None
            assert ways[chain["physical_traffic_light_id"]].find(
                "tag[@k='type'][@v='traffic_light']"
            ) is not None
            assert ways[chain["light_bulb_linestring_id"]].find(
                "tag[@k='type'][@v='light_bulbs']"
            ) is not None
            assert row["route_length_m"] >= 100.0
            assert row["phase_authority_modes_supported"] == [
                "controlled_same_tick_override",
                "observe_same_tick_request",
            ]
            assert row["runtime_phase_authority_frozen_in_execution_plan"] is False
            assert row["phase_remaining_available"] is False
            assert row["future_phase_schedule_consumed"] is False
            assert row["outcome_fields_consumed"] == []


@pytest.mark.parametrize(
    "mutation",
    (
        "map_bytes",
        "duplicate_geometry",
        "missing_stop_line",
        "future_schedule",
        "wrong_denominator",
    ),
)
def test_signal_complete_validation_fails_closed(mutation: str) -> None:
    suite = build_signal_complete_suite("calibration")
    if mutation == "map_bytes":
        path = next(iter(suite["map_payloads"]))
        suite["map_payloads"][path] += b" "
    elif mutation == "duplicate_geometry":
        duplicate = suite["maps"][0]["routes"][0][
            "source_independent_geometry_sha256"
        ]
        suite["maps"][0]["routes"][1][
            "source_independent_geometry_sha256"
        ] = duplicate
        suite["source_independent_geometry_sha256"][1] = duplicate
        suite["source_independent_geometry_sha256"].sort()
    elif mutation == "missing_stop_line":
        suite["maps"][0]["routes"][0]["source_chain"][
            "certified_stop_line_id"
        ] = 999999999
    elif mutation == "future_schedule":
        suite["maps"][0]["routes"][0]["future_phase_schedule_consumed"] = True
    else:
        suite["route_count"] -= 1
    with pytest.raises(ValueError):
        validate_signal_complete_suite(suite)


def test_license_and_candidate_contract_are_bounded() -> None:
    suite = build_signal_complete_suite("fresh_b2")
    assert suite["license"] == {
        "spdx": "MIT",
        "provenance": "project_authored_from_first_principles",
        "repository_license_path": "LICENSE",
        "third_party_map_payload_derived": False,
    }
    assert suite["fixed_dp_modified"] is False
    assert suite["candidate_tensor_modified"] is False
    assert suite["fresh_b2_opened"] is False
    assert suite["outcome_fields_consumed"] == []


def test_unknown_split_and_extra_control_field_fail_closed() -> None:
    with pytest.raises(ValueError, match="unknown"):
        build_signal_complete_suite("train")
    suite = build_signal_complete_suite("calibration")
    mutated = copy.deepcopy(suite)
    mutated["freshOutcome"] = False
    with pytest.raises(ValueError, match="field set"):
        validate_signal_complete_suite(mutated)
