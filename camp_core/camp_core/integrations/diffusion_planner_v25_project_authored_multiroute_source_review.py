"""Independent local-literal review for the project-authored source stage.

This module intentionally does not import the source producer, its map
generator, clone builder, or selection functions.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from typing import Any, Mapping, Sequence
import xml.etree.ElementTree as ET

import numpy as np


AUTHORITY_SHA256 = (
    "9315b09b33f80856e1bbdcf957f92542ccaeb495b4b00497231ef038909a20cb"
)
BASE_HEAD = "dea1a0a627df82317c3ff59cc1a5212c813a40dd"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
NAMESPACE = (
    "camp_v25_industrial_v3_project_authored_multiroute_development_source_v1"
)
FAMILIES = (
    "lead_vehicle_hard_brake",
    "cut_in_merge",
    "pedestrian_cyclist_crossing",
    "unprotected_turn_oncoming_conflict",
    "red_light_phase_timing",
    "blocked_lane_static_obstacle",
    "narrow_encounter",
)
RISKS = ("easy", "borderline", "high_risk")
ROUTES = (
    "heading_change_abs_le_0_15rad",
    "heading_change_abs_gt_0_15_le_0_75rad",
    "heading_change_abs_gt_0_75rad",
)
SOURCES = ("mapped_signal", "no_signal")
FR = (
    (5, 5, 5),
    (5, 5, 5),
    (5, 5, 4),
    (5, 4, 5),
    (4, 5, 5),
    (5, 5, 4),
    (4, 5, 5),
)
FG = (
    (5, 5, 5),
    (5, 5, 5),
    (5, 5, 4),
    (4, 5, 5),
    (5, 5, 4),
    (5, 4, 5),
    (4, 5, 5),
)
FS = (
    (8, 7),
    (7, 8),
    (7, 7),
    (7, 7),
    (8, 6),
    (6, 8),
    (7, 7),
)
GS = ((17, 16), (17, 17), (16, 17))
HEADINGS = {
    ROUTES[0]: (0.0, 1.0 / 30.0, 1.0 / 15.0, 0.1),
    ROUTES[1]: (0.0, 0.15, 0.30, 0.45),
    ROUTES[2]: (0.0, 0.35, 0.70, 1.05),
}
TIER = {
    "easy": {
        "headway_m": 34.0,
        "ego_speed_mps": 7.0,
        "other_speed_mps": 7.0,
        "deceleration_mps2": -2.0,
        "trigger_time_s": 2.5,
        "lateral_offset_m": 4.0,
        "lateral_speed_mps": 0.6,
        "crossing_speed_mps": 1.2,
    },
    "borderline": {
        "headway_m": 22.0,
        "ego_speed_mps": 8.0,
        "other_speed_mps": 5.0,
        "deceleration_mps2": -4.0,
        "trigger_time_s": 1.5,
        "lateral_offset_m": 3.0,
        "lateral_speed_mps": 1.0,
        "crossing_speed_mps": 1.8,
    },
    "high_risk": {
        "headway_m": 14.0,
        "ego_speed_mps": 9.0,
        "other_speed_mps": 2.0,
        "deceleration_mps2": -6.0,
        "trigger_time_s": 0.8,
        "lateral_offset_m": 2.0,
        "lateral_speed_mps": 1.5,
        "crossing_speed_mps": 2.5,
    },
}
BASE_SHA = {
    "signal_complete_generator": (
        "9a0459bc2a7e9e498866afdd2dd0e8b6ae61599b8a83e6a2b646f4a04a818202"
    ),
    "materializer": (
        "11f9b3935bdef61ec37038345e1dd70a1b3be85bcbd6e5b35217909f80f1f6a7"
    ),
    "controlled_scenario_semantics": (
        "af401c128b7b462d821d0e0f6a871b901e39fc3a7de67904afe0f6c43628bb4d"
    ),
    "signal_plan": (
        "c4f174616708c8d5d25cefd71b0df3330e3cd73ac7ee079e950cfe3cc1317fbd"
    ),
    "signal_runtime": (
        "8136a10fa43b52e0cdf48b85304d47704cc1b36ea9091892e67f11831a307c83"
    ),
    "mapped_signal_authority": (
        "72d27e686a18e325f99aa53a66e30f125db225c8799d9fb33e99bdb467a41266"
    ),
    "no_signal_authority": (
        "82b363c53f8d53ce0e57e0cfcb93f7f9697807601b43f552c034cd0f338b6a5b"
    ),
    "license": (
        "d3d79d2e0cab6a7a2369dc973482a3ace35d17d1f389422c81ea8bcc833bfb61"
    ),
}
OVERLAP_LEVELS = (
    "route",
    "state",
    "geometry",
    "semantic",
    "source",
    "seed",
    "latent_instance",
    "composite",
)


def _bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def _digest(value: Any) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()


def _raw_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha(value: Any) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError("review expected lowercase SHA256")
    return value


def review_contract_literal(value: Mapping[str, Any]) -> dict[str, Any]:
    row = deepcopy(dict(value))
    if (
        row.get("schema_version")
        != "camp_dp_v25_project_authored_multiroute_source_contract_v1"
        or row.get("authority_schema")
        != "camp_dp_v25_project_authored_multiroute_source_high_authority_v1_1"
        or row.get("authority_sha256") != AUTHORITY_SHA256
        or row.get("base_head") != BASE_HEAD
        or row.get("fixed_dp_head") != FIXED_DP_HEAD
        or row.get("audited_generator_base_sha256") != BASE_SHA
    ):
        raise ValueError("review source contract identity drifted")
    universe = row.get("universe", {})
    if universe != {
        "namespace": NAMESPACE,
        "families": list(FAMILIES),
        "risk_tiers": list(RISKS),
        "route_bins": list(ROUTES),
        "source_availability": list(SOURCES),
        "replicas_per_cell": 2,
        "full_cell_count": 126,
        "candidate_ceiling": 252,
        "ordinal_formula": "(((((f*3)+r)*3+g)*2+s)*2)+replica",
        "ordinal_min": 0,
        "ordinal_max": 251,
        "candidate_253_allowed": False,
        "dynamic_replacement_allowed": False,
    }:
        raise ValueError("review source universe drifted")
    selection = row.get("selection", {})
    if (
        selection.get("selected_count") != 100
        or selection.get("family_risk_quotas") != [list(item) for item in FR]
        or selection.get("family_route_quotas") != [list(item) for item in FG]
        or selection.get("family_source_quotas") != [list(item) for item in FS]
        or selection.get("route_source_quotas") != [list(item) for item in GS]
        or selection.get("cell_selection_ceiling") != 1
        or selection.get("drop_replace_suffix_or_outcome_selection_allowed")
        is not False
    ):
        raise ValueError("review source selection topology drifted")
    boundary = row.get("execution_boundary", {})
    if (
        boundary.get("model_pool_selector_calls") != 0
        or boundary.get("outcome_values_read") is not False
        or boundary.get("old_artifact_or_cas_writes") != 0
        or boundary.get("training_or_retraining") is not False
        or boundary.get("fresh_holdout_or_new_nonce") is not False
    ):
        raise ValueError("review source execution boundary drifted")
    return row


def _decode(ordinal: int) -> tuple[int, int, int, int, int]:
    if isinstance(ordinal, bool) or type(ordinal) is not int or not 0 <= ordinal < 252:
        raise ValueError("review source ordinal drifted")
    value, replica = divmod(ordinal, 2)
    value, source = divmod(value, 2)
    value, route = divmod(value, 3)
    family, risk = divmod(value, 3)
    return family, risk, route, source, replica


def _expected_geometry(ordinal: int, route: int, replica: int) -> dict[str, Any]:
    lengths = (
        36.0 + 0.17 * (ordinal % 11),
        38.0 + 0.19 * (ordinal % 13),
        40.0 + 0.23 * (ordinal % 17),
        42.0 + 0.29 * (ordinal % 19),
    )
    headings = HEADINGS[ROUTES[route]]
    centers = [(0.0, 0.0)]
    for length, heading in zip(lengths, headings, strict=True):
        centers.append(
            (
                centers[-1][0] + length * math.cos(heading),
                centers[-1][1] + length * math.sin(heading),
            )
        )
    width = 3.20 + 0.05 * ((ordinal + replica) % 7)
    normals = [
        (-math.sin(heading), math.cos(heading)) for heading in headings
    ]
    vertex_normals = [normals[0]]
    for left, right in zip(normals[:-1], normals[1:], strict=True):
        sx, sy = left[0] + right[0], left[1] + right[1]
        norm = math.hypot(sx, sy)
        vertex_normals.append(
            right if norm <= 1e-12 else (sx / norm, sy / norm)
        )
    vertex_normals.append(normals[-1])
    half = width / 2.0
    left = [
        (point[0] + normal[0] * half, point[1] + normal[1] * half)
        for point, normal in zip(centers, vertex_normals, strict=True)
    ]
    right = [
        (point[0] - normal[0] * half, point[1] - normal[1] * half)
        for point, normal in zip(centers, vertex_normals, strict=True)
    ]
    rounded = lambda points: [
        [round(float(point[0]), 9), round(float(point[1]), 9)]
        for point in points
    ]
    return {
        "schema_version": "camp_dp_v25_project_authored_route_geometry_v1",
        "centerline_points_m": rounded(centers),
        "segment_headings_rad": [round(float(item), 12) for item in headings],
        "segment_lengths_m": [round(float(item), 12) for item in lengths],
        "left_boundary_m": rounded(left),
        "right_boundary_m": rounded(right),
        "lane_width_m": round(width, 12),
        "speed_limit_kph": (30.0, 40.0, 50.0)[ordinal % 3],
    }


def _map_review(
    raw: bytes,
    *,
    ordinal: int,
    source: str,
    geometry: Mapping[str, Any],
) -> dict[str, Any]:
    if not raw.endswith(b"\n"):
        raise ValueError("review OSM terminal LF missing")
    root = ET.fromstring(raw)
    if root.tag != "osm" or root.attrib.get("version") != "0.6":
        raise ValueError("review OSM root drifted")
    tags = [
        {
            str(tag.attrib.get("k")): str(tag.attrib.get("v"))
            for tag in element.findall("tag")
        }
        for element in root.iter()
    ]
    relations = root.findall("relation")
    lanelets = [
        item
        for item in relations
        if {
            str(tag.attrib.get("k")): str(tag.attrib.get("v"))
            for tag in item.findall("tag")
        }.get("type")
        == "lanelet"
    ]
    if len(lanelets) != 4:
        raise ValueError("review OSM lanelet count drifted")
    base = 3_000_000 + ordinal * 1_000
    expected_lanelets = [base + 401 + index for index in range(4)]
    if [int(item.attrib["id"]) for item in lanelets] != expected_lanelets:
        raise ValueError("review OSM ordered lanelets drifted")
    node_by_id = {
        int(node.attrib["id"]): node for node in root.findall("node")
    }
    lat0, lon0 = 35.0, 139.0
    recovered = []
    for node_id in [base + 1 + i for i in range(5)] + [
        base + 11 + i for i in range(5)
    ]:
        node = node_by_id[node_id]
        y = (float(node.attrib["lat"]) - lat0) * 111_111.0
        x = (
            (float(node.attrib["lon"]) - lon0)
            * 111_111.0
            * math.cos(math.radians(lat0))
        )
        recovered.append([x, y])
    expected_points = (
        list(geometry["left_boundary_m"]) + list(geometry["right_boundary_m"])
    )
    if not np.allclose(
        np.asarray(recovered),
        np.asarray(expected_points),
        atol=1e-5,
        rtol=0.0,
    ):
        raise ValueError("review OSM boundary coordinates drifted")
    values = {value for row in tags for value in row.values()}
    roles = {
        member.attrib.get("role", "")
        for relation in relations
        for member in relation.findall("member")
    }
    if source == "mapped_signal":
        if (
            "traffic_light" not in values
            or "light_bulbs" not in values
            or "stop_line" not in values
            or not {"ref_line", "refers", "light_bulbs"}.issubset(roles)
        ):
            raise ValueError("review mapped-signal chain incomplete")
        colors = {row.get("color") for row in tags if "color" in row}
        if colors != {"red", "yellow", "green"}:
            raise ValueError("review mapped-signal bulbs drifted")
    else:
        prohibited = {
            "traffic_light",
            "light_bulbs",
            "stop_line",
            "regulatory_element",
            "phase",
            "future_schedule",
        }
        if values.intersection(prohibited) or roles.intersection(
            {"ref_line", "refers", "light_bulbs", "regulatory_element"}
        ):
            raise ValueError("review no-signal hidden authority detected")
    return {
        "map_sha256": _raw_digest(raw),
        "lanelet_count": 4,
        "source_availability": source,
    }


def _expected_semantics(
    record: Mapping[str, Any],
    *,
    ordinal: int,
    family: str,
    risk: str,
    route: int,
) -> dict[str, Any]:
    params = dict(TIER[risk])
    params["variant"] = ordinal
    geometry = record["route"]["geometry"]
    centers = np.asarray(geometry["centerline_points_m"], dtype=np.float64)
    headings = np.asarray(geometry["segment_headings_rad"], dtype=np.float64)
    segments = np.linalg.norm(np.diff(centers, axis=0), axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(segments)))
    target = min(float(params["headway_m"]), float(cumulative[-1]) - 12.0)
    target = max(target, 8.0)
    index = min(
        int(np.searchsorted(cumulative, target, side="right") - 1),
        len(centers) - 2,
    )
    span = max(float(cumulative[index + 1] - cumulative[index]), 1e-9)
    ratio = (target - cumulative[index]) / span
    anchor = centers[index] * (1.0 - ratio) + centers[index + 1] * ratio
    heading = float(headings[index])
    tangent = np.asarray([math.cos(heading), math.sin(heading)])
    normal = np.asarray([-tangent[1], tangent[0]])
    common = {
        "route_tangent": tangent.tolist(),
        "route_normal": normal.tolist(),
        "trigger_time_s": float(params["trigger_time_s"]),
        "longitudinal_acceleration_mps2": 0.0,
        "lateral_target_m": None,
    }

    def actor(
        index_value: int,
        *,
        agent_type: str,
        longitudinal_speed: float,
        lateral_offset: float = 0.0,
        lateral_speed: float = 0.0,
        acceleration: float = 0.0,
        heading_offset: float = 0.0,
        length: float = 4.5,
        width: float = 1.8,
        lateral_target: float | None = None,
    ) -> dict[str, Any]:
        position = anchor + normal * lateral_offset
        return {
            **common,
            "id": f"static_npc_v25_{index_value}",
            "agent_type": agent_type,
            "initial_xy": position.tolist(),
            "initial_heading_rad": float(heading + heading_offset),
            "longitudinal_speed_mps": float(longitudinal_speed),
            "lateral_offset_m": float(lateral_offset),
            "lateral_speed_mps": float(lateral_speed),
            "lateral_target_m": lateral_target,
            "longitudinal_acceleration_mps2": float(acceleration),
            "length_m": float(length),
            "width_m": float(width),
            "wheelbase_m": float(max(length * 0.65, 0.5)),
        }

    actors: list[dict[str, Any]] = []
    signal = {"phase": "none", "phase_remaining_s": 0.0, "mapped_source_required": False}
    if family == FAMILIES[0]:
        actors.append(
            actor(
                0,
                agent_type="vehicle",
                longitudinal_speed=params["other_speed_mps"],
                acceleration=params["deceleration_mps2"],
            )
        )
    elif family == FAMILIES[1]:
        lateral = params["lateral_offset_m"]
        actors.append(
            actor(
                0,
                agent_type="vehicle",
                longitudinal_speed=params["other_speed_mps"],
                lateral_offset=lateral,
                lateral_speed=-params["lateral_speed_mps"],
                lateral_target=0.0,
                heading_offset=-0.18,
            )
        )
    elif family == FAMILIES[2]:
        lateral = params["lateral_offset_m"] + 1.5
        cycling = ordinal % 2 == 1
        actors.append(
            actor(
                0,
                agent_type="bicycle" if cycling else "pedestrian",
                longitudinal_speed=0.0,
                lateral_offset=lateral,
                lateral_speed=-params["crossing_speed_mps"],
                lateral_target=-lateral,
                heading_offset=-math.pi / 2.0,
                length=1.8 if cycling else 0.7,
                width=0.6,
            )
        )
        if risk != "easy":
            actors.append(
                actor(
                    1,
                    agent_type="vehicle",
                    longitudinal_speed=0.0,
                    lateral_offset=lateral * 0.72,
                    length=4.8,
                    width=2.0,
                )
            )
    elif family == FAMILIES[3]:
        actors.append(
            actor(
                0,
                agent_type="vehicle",
                longitudinal_speed=-max(params["other_speed_mps"], 5.0),
                lateral_offset=0.4 if route != 0 else 0.8,
                heading_offset=math.pi,
            )
        )
    elif family == FAMILIES[4]:
        signal = {
            "phase": {"easy": "green", "borderline": "yellow", "high_risk": "red"}[
                risk
            ],
            "phase_remaining_s": {
                "easy": 12.0,
                "borderline": 2.0,
                "high_risk": 8.0,
            }[risk],
            "mapped_source_required": True,
        }
    elif family == FAMILIES[5]:
        actors.append(actor(0, agent_type="vehicle", longitudinal_speed=0.0))
    elif family == FAMILIES[6]:
        actors.append(
            actor(
                0,
                agent_type="vehicle",
                longitudinal_speed=-max(params["other_speed_mps"], 4.0),
                lateral_offset=0.55,
                heading_offset=math.pi,
                width=2.0,
            )
        )
    return {"parameters": params, "actors": actors, "signal": signal}


def review_source_record_literal(
    record: Mapping[str, Any], map_bytes: bytes
) -> dict[str, Any]:
    row = deepcopy(dict(record))
    source_sha = row.pop("source_record_sha256", None)
    if _digest(row) != _sha(source_sha):
        raise ValueError("review source record SHA drifted")
    ordinal = row.get("ordinal")
    family_i, risk_i, route_i, source_i, replica = _decode(ordinal)
    family, risk, route_name, source = (
        FAMILIES[family_i],
        RISKS[risk_i],
        ROUTES[route_i],
        SOURCES[source_i],
    )
    if (
        row.get("namespace") != NAMESPACE
        or row.get("cell")
        != {
            "family": family,
            "risk_tier": risk,
            "route_bin": route_name,
            "source_availability": source,
            "replica": replica,
        }
        or row.get("seeds")
        != {
            "scenario": 2_750_000_000 + ordinal,
            "actor": 2_751_000_000 + ordinal,
            "selection_latent": 2_752_000_000 + ordinal,
        }
    ):
        raise ValueError("review source spec drifted")
    geometry = _expected_geometry(ordinal, route_i, replica)
    if row["route"].get("geometry") != geometry:
        raise ValueError("review source geometry formula drifted")
    if row["route"].get("geometry_sha256") != _digest(geometry):
        raise ValueError("review source geometry SHA drifted")
    map_review = _map_review(
        map_bytes,
        ordinal=ordinal,
        source=source,
        geometry=geometry,
    )
    if (
        map_review["map_sha256"] != row["map"].get("sha256")
        or row["map"].get("license_spdx") != "MIT"
        or row["map"].get("license_sha256") != BASE_SHA["license"]
        or row["map"].get("third_party_payload_derived") is not False
    ):
        raise ValueError("review source map/provenance drifted")
    expected_semantics = _expected_semantics(
        row,
        ordinal=ordinal,
        family=family,
        risk=risk,
        route=route_i,
    )
    semantic = row["semantic_block"]
    if (
        semantic.get("family") != family
        or semantic.get("risk_tier") != risk
        or semantic.get("variant") != ordinal
        or semantic.get("controlled_scenario_parameters")
        != expected_semantics["parameters"]
        or semantic.get("actors") != expected_semantics["actors"]
        or semantic.get("signal_semantics") != expected_semantics["signal"]
        or row.get("semantic_block_sha256") != _digest(semantic)
    ):
        raise ValueError("review source controlled semantics drifted")
    actor_rng = np.random.Generator(np.random.PCG64DXSM(2_751_000_000 + ordinal))
    draws = actor_rng.standard_normal((max(1, len(semantic["actors"])), 4)).astype(
        "<f4"
    )
    if semantic["actor_rng"] != {
        "algorithm": "PCG64DXSM",
        "seed": 2_751_000_000 + ordinal,
        "draw_shape": list(draws.shape),
        "draw_dtype": "<f4",
        "draw_sha256": _raw_digest(draws.tobytes()),
    }:
        raise ValueError("review source actor RNG drifted")
    latent = row["selection_latent_instance"]
    rng = np.random.Generator(np.random.PCG64DXSM(2_752_000_000 + ordinal))
    expected_latent = np.zeros((8, 4), dtype="<f4")
    expected_latent[1:] = rng.standard_normal((7, 4)).astype("<f4")
    row_sha = [_raw_digest(item.tobytes()) for item in expected_latent]
    if (
        latent.get("raw_bytes_hex") != expected_latent.tobytes().hex()
        or latent.get("tensor_sha256") != _raw_digest(expected_latent.tobytes())
        or latent.get("row_sha256") != row_sha
        or latent.get("unique_row_sha256_cardinality") != 8
        or row.get("selection_latent_instance_sha256") != _digest(latent)
    ):
        raise ValueError("review source selection latent drifted")
    return deepcopy(dict(record))


def review_candidate_literal(
    record: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    contract_root_sha256: str,
) -> dict[str, Any]:
    row = deepcopy(dict(candidate))
    payload = row.get("clone_payload")
    semantic = record["semantic_block"]
    signal_sha = record["source_availability_receipt_sha256"]
    actor_sha = record["actor_bytes_sha256"]
    seed_sha = _digest(record["seeds"])
    source_sha = record["source_record_sha256"]
    expected_payload = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_id_free_clone_payload_v1"
        ),
        "canonical_route_lanelet_arc_sha256": record["route"][
            "route_lanelet_arc_sha256"
        ],
        "route_geometry_sha256": record["route"]["geometry_sha256"],
        "semantic_family": record["cell"]["family"],
        "risk_tier": record["cell"]["risk_tier"],
        "source_availability": record["cell"]["source_availability"],
        "certified_signal_stopline_inventory_sha256": signal_sha,
        "canonical_state_actor_geometry_sha256": actor_sha,
        "scenario_source_bytes_sha256": source_sha,
        "scenario_seed_sha256": seed_sha,
        "latent_instance_sha256": record["selection_latent_instance_sha256"],
    }
    clone = _digest(expected_payload)
    if payload != expected_payload or row.get("clone_key_sha256") != clone:
        raise ValueError("review source clone preimage drifted")
    expected_overlap = {
        "route": record["route"]["route_lanelet_arc_sha256"],
        "state": _digest(
            {
                "spawn": record["route"]["spawn_pose"],
                "goal": record["route"]["goal_pose"],
                "actors": actor_sha,
                "source": source_sha,
            }
        ),
        "geometry": record["route"]["geometry_sha256"],
        "semantic": _digest(
            {
                "family": semantic["family"],
                "tier": semantic["risk_tier"],
                "signal_stopline": signal_sha,
                "actor_geometry": actor_sha,
            }
        ),
        "source": source_sha,
        "seed": seed_sha,
        "latent_instance": record["selection_latent_instance_sha256"],
        "composite": clone,
    }
    if row.get("overlap_keys") != expected_overlap:
        raise ValueError("review source overlap preimage drifted")
    binding = row.get("source_binding")
    if (
        binding
        != {
            "artifact_path": (
                "/root/autodl-tmp/camp_dp_v25_project_authored_multiroute_"
                "source_dea1a0a6_9315b09b_materialization"
            ),
            "artifact_root_sha256": _sha(contract_root_sha256),
            "inventory_entry_path": (
                f"source_records.json#/records/{int(record['ordinal'])}"
            ),
            "inventory_entry_sha256": source_sha,
        }
    ):
        raise ValueError("review source binding drifted")
    return row


def _cell(row: Mapping[str, Any]) -> tuple[int, int, int, int]:
    payload = row["clone_payload"]
    return (
        FAMILIES.index(payload["semantic_family"]),
        RISKS.index(payload["risk_tier"]),
        ROUTES.index(row["route_bin"]),
        SOURCES.index(payload["source_availability"]),
    )


def _risk_allocations(
    family: int,
    route_source: tuple[int, ...],
    lower: Mapping[tuple[int, int, int, int], int],
    upper: Mapping[tuple[int, int, int, int], int],
) -> tuple[tuple[int, ...], ...]:
    columns = [(route, source) for route in range(3) for source in range(2)]
    results: list[tuple[int, ...]] = []
    current: list[int] = []

    def rec(column: int, remaining: tuple[int, int, int]) -> None:
        if column == 6:
            if remaining == (0, 0, 0):
                results.append(tuple(current))
            return
        route, source = columns[column]
        target = route_source[column]
        lows = [int(lower.get((family, risk, route, source), 0)) for risk in range(3)]
        highs = [int(upper.get((family, risk, route, source), 0)) for risk in range(3)]
        for a in range(lows[0], min(highs[0], remaining[0], target) + 1):
            for b in range(lows[1], min(highs[1], remaining[1], target - a) + 1):
                c = target - a - b
                if not lows[2] <= c <= min(highs[2], remaining[2]):
                    continue
                next_remaining = (
                    remaining[0] - a,
                    remaining[1] - b,
                    remaining[2] - c,
                )
                minimum = [
                    sum(
                        int(
                            lower.get(
                                (family, risk, later_route, later_source), 0
                            )
                        )
                        for later_route, later_source in columns[column + 1 :]
                    )
                    for risk in range(3)
                ]
                maximum = [
                    sum(
                        int(
                            upper.get(
                                (family, risk, later_route, later_source), 0
                            )
                        )
                        for later_route, later_source in columns[column + 1 :]
                    )
                    for risk in range(3)
                ]
                if any(
                    next_remaining[risk] < minimum[risk]
                    or next_remaining[risk] > maximum[risk]
                    for risk in range(3)
                ):
                    continue
                current.extend((a, b, c))
                rec(column + 1, next_remaining)
                del current[-3:]

    rec(0, tuple(FR[family]))
    return tuple(results)


def _family_options(
    family: int,
    lower: Mapping[tuple[int, int, int, int], int],
    upper: Mapping[tuple[int, int, int, int], int],
) -> tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]:
    options = []
    route_target = FG[family]
    source0_target = FS[family][0]
    for r0s0 in range(route_target[0] + 1):
        for r1s0 in range(route_target[1] + 1):
            r2s0 = source0_target - r0s0 - r1s0
            if not 0 <= r2s0 <= route_target[2]:
                continue
            rs = (
                r0s0,
                route_target[0] - r0s0,
                r1s0,
                route_target[1] - r1s0,
                r2s0,
                route_target[2] - r2s0,
            )
            if any(
                not sum(
                    int(lower.get((family, risk, route, source), 0))
                    for risk in range(3)
                )
                <= rs[route * 2 + source]
                <= sum(
                    int(upper.get((family, risk, route, source), 0))
                    for risk in range(3)
                )
                for route in range(3)
                for source in range(2)
            ):
                continue
            for allocation in _risk_allocations(family, rs, lower, upper):
                full = []
                for risk in range(3):
                    for route in range(3):
                        for source in range(2):
                            full.append(allocation[(route * 2 + source) * 3 + risk])
                options.append((rs, tuple(full)))
    return tuple(options)


def _feasible(
    lower: Mapping[tuple[int, int, int, int], int],
    upper: Mapping[tuple[int, int, int, int], int],
) -> bool:
    options = [_family_options(family, lower, upper) for family in range(7)]
    if any(not item for item in options):
        return False
    target = tuple(GS[route][source] for route in range(3) for source in range(2))
    states = {(0,) * 6}
    for family_options in options:
        next_states = set()
        for accumulated in states:
            for route_source, _full in family_options:
                combined = tuple(
                    accumulated[index] + route_source[index] for index in range(6)
                )
                if all(combined[index] <= target[index] for index in range(6)):
                    next_states.add(combined)
        states = next_states
    return target in states


def _review_exact_selection(
    candidates: Sequence[Mapping[str, Any]],
) -> list[str]:
    groups: dict[tuple[int, int, int, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in candidates:
        groups[_cell(row)].append(row)
    if len(groups) != 126 or any(len(rows) != 2 for rows in groups.values()):
        raise ValueError("review source cell/replica topology drifted")
    rows = sorted(
        (min(items, key=lambda item: item["clone_key_sha256"]) for items in groups.values()),
        key=lambda item: item["clone_key_sha256"],
    )
    remaining = Counter(_cell(row) for row in rows)
    lower: Counter[tuple[int, int, int, int]] = Counter()
    if not _feasible(lower, remaining):
        raise ValueError("review source quota inventory infeasible")
    selected = []
    for row in rows:
        cell = _cell(row)
        remaining[cell] -= 1
        trial = Counter(lower)
        trial[cell] += 1
        upper = Counter(
            {
                key: trial[key] + remaining[key]
                for key in set(trial).union(remaining)
            }
        )
        if _feasible(trial, upper):
            lower = trial
            selected.append(row["clone_key_sha256"])
    if len(selected) != 100:
        raise ValueError("review source selection denominator drifted")
    return selected


def review_materialization_literal(
    *,
    records: Sequence[Mapping[str, Any]],
    maps: Mapping[str, bytes],
    candidates: Sequence[Mapping[str, Any]],
    selected_manifest: Mapping[str, Any],
    contract_root_sha256: str,
    forbidden: Mapping[str, Mapping[str, Sequence[str]]],
) -> dict[str, Any]:
    if len(records) != 252 or len(candidates) != 252 or len(maps) != 252:
        raise ValueError("review source universe denominator drifted")
    reviewed_candidates = []
    geometry = set()
    for ordinal, (record, candidate) in enumerate(zip(records, candidates, strict=True)):
        if record.get("ordinal") != ordinal:
            raise ValueError("review source record order drifted")
        path = record["map"]["relative_path"]
        if path not in maps:
            raise ValueError("review source map inventory missing")
        reviewed = review_source_record_literal(record, maps[path])
        reviewed_candidates.append(
            review_candidate_literal(
                reviewed,
                candidate,
                contract_root_sha256=contract_root_sha256,
            )
        )
        geometry.add(record["route"]["geometry_sha256"])
    if (
        len(geometry) != 252
        or len({row["clone_key_sha256"] for row in reviewed_candidates}) != 252
    ):
        raise ValueError("review source uniqueness drifted")
    expected_keys = _review_exact_selection(reviewed_candidates)
    selected = selected_manifest.get("selected_clone_key_sha256")
    if selected != expected_keys:
        raise ValueError("review source manifest is not lexicographically minimal")
    if selected_manifest.get("selected_count") != 100:
        raise ValueError("review source selected denominator drifted")
    selected_rows = [
        next(row for row in reviewed_candidates if row["clone_key_sha256"] == key)
        for key in selected
    ]
    counts = Counter(_cell(row) for row in selected_rows)
    for family in range(7):
        if tuple(
            sum(
                counts[(family, risk, route, source)]
                for route in range(3)
                for source in range(2)
            )
            for risk in range(3)
        ) != FR[family]:
            raise ValueError("review source family/risk quota drifted")
        if tuple(
            sum(
                counts[(family, risk, route, source)]
                for risk in range(3)
                for source in range(2)
            )
            for route in range(3)
        ) != FG[family]:
            raise ValueError("review source family/route quota drifted")
        if tuple(
            sum(
                counts[(family, risk, route, source)]
                for risk in range(3)
                for route in range(3)
            )
            for source in range(2)
        ) != FS[family]:
            raise ValueError("review source family/source quota drifted")
    if set(forbidden) != {
        "training",
        "calibration",
        "legacy_nonholdout",
        "bounded_single_route",
        "corrected_64_state_development",
        "Fresh_B2",
        "Fresh_B3",
        "Fresh_B4",
    }:
        raise ValueError("review source forbidden authority set drifted")
    overlap = {}
    for authority, layers in forbidden.items():
        if set(layers) != set(OVERLAP_LEVELS):
            raise ValueError("review source forbidden layer set drifted")
        overlap[authority] = {}
        for level in OVERLAP_LEVELS:
            left = {row["overlap_keys"][level] for row in selected_rows}
            right = {_sha(item) for item in layers[level]}
            intersection = sorted(left.intersection(right))
            if intersection:
                raise ValueError(
                    f"review project source overlaps {authority}/{level}"
                )
            overlap[authority][level] = {
                "forbidden_count": len(right),
                "intersection_count": 0,
                "intersection_sha256": _digest(intersection),
            }
    return {
        "candidate_count": 252,
        "selected_count": 100,
        "geometry_unique_count": 252,
        "selected_clone_key_sha256": expected_keys,
        "selected_vector_sha256": _digest(expected_keys),
        "zero_overlap": overlap,
        "reviewer_imported_source_producer": False,
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
    }

