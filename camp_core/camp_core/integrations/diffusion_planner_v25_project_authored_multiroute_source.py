"""Project-authored, outcome-free V25 multiroute source generator.

This additive module never calls a model, selector, simulator, or evaluator.
It deterministically constructs the finite 252-candidate development source
universe authorized by High, validates every source byte, and selects the
lexicographically smallest feasible 100-cluster manifest.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence
import xml.etree.ElementTree as ET

import numpy as np

from .diffusion_planner_v25_controlled_scenarios import (
    build_controlled_scenario_case,
    validate_controlled_scenario_case,
)
from .diffusion_planner_v25_industrial_multiroute import (
    FAMILIES,
    FAMILY_RISK_QUOTAS,
    FAMILY_ROUTE_QUOTAS,
    FAMILY_SOURCE_QUOTAS,
    RISK_TIERS,
    ROUTE_BINS,
    ROUTE_SOURCE_QUOTAS,
    SOURCE_AVAILABILITY,
    select_lexicographically_smallest_feasible,
    validate_candidate,
)


SCHEMA_VERSION = "camp_dp_v25_project_authored_multiroute_source_contract_v1"
AUTHORITY_SCHEMA = (
    "camp_dp_v25_project_authored_multiroute_source_high_authority_v1_1"
)
AUTHORITY_SHA256 = (
    "9315b09b33f80856e1bbdcf957f92542ccaeb495b4b00497231ef038909a20cb"
)
AUTHORITY_V1_PREIMAGE_SHA256 = (
    "40693944e5eba29846b2f4c2c94da13f696210f6cee0514d0f1faab89f6c3d51"
)
PARENT_AUTHORITY_SHA256 = (
    "b5ca942b4a91c0ef0cbe4e9ff8180852fb193471fb9f73514f6017622547718f"
)
BASE_HEAD = "dea1a0a627df82317c3ff59cc1a5212c813a40dd"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
NAMESPACE = (
    "camp_v25_industrial_v3_project_authored_multiroute_development_source_v1"
)
LOCAL_INTERPRETER = (
    r"C:\Users\lenovo\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\python\python.exe"
)
AUTODL_INTERPRETER = "/root/autodl-tmp/dp312_venv/bin/python"

SOURCE_EXACT_DIRS = {
    "contract": (
        "/root/autodl-tmp/camp_dp_v25_project_authored_multiroute_"
        "source_dea1a0a6_9315b09b_contract"
    ),
    "contract_review": (
        "/root/autodl-tmp/camp_dp_v25_project_authored_multiroute_"
        "source_dea1a0a6_9315b09b_contract_review"
    ),
    "focused": (
        "/root/autodl-tmp/camp_dp_v25_project_authored_multiroute_"
        "source_dea1a0a6_9315b09b_focused"
    ),
    "materialization": (
        "/root/autodl-tmp/camp_dp_v25_project_authored_multiroute_"
        "source_dea1a0a6_9315b09b_materialization"
    ),
    "materialization_review": (
        "/root/autodl-tmp/camp_dp_v25_project_authored_multiroute_"
        "source_dea1a0a6_9315b09b_materialization_review"
    ),
    "continuation_authority": (
        "/root/autodl-tmp/camp_dp_v25_project_authored_multiroute_"
        "source_dea1a0a6_9315b09b_continuation_authority"
    ),
    "continuation_authority_review": (
        "/root/autodl-tmp/camp_dp_v25_project_authored_multiroute_"
        "source_dea1a0a6_9315b09b_continuation_authority_review"
    ),
}

AUDITED_BASE_SHA256 = {
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

UPSTREAM_DIAGNOSTIC_ROOTS = {
    "parent_contract": (
        "a35f550364e2a75ff958cf8c0df81f9d44376c9611342b916319106c7eb2cbfb"
    ),
    "parent_contract_review": (
        "b8dab88cd2a57dc501872a5c7a190ab43d2a8543211fad427f61713bdced6e19"
    ),
    "parent_manifest_failure": (
        "92d133e9acf7edac2c912442ddc10046e3854220b876120f1e80ea9557a89ea6"
    ),
    "parent_manifest_failure_review": (
        "bb566079e2c86abd64bae181b03e087e86cfcd5f659a23236c915b9722cf7dd7"
    ),
    "parent_final_docs": (
        "cad0c8b26e8a05a1c613cb4412eabd7fc66590508ef55119520c14d05917bd03"
    ),
}

REPLICAS_PER_CELL = 2
FULL_CELL_COUNT = 7 * 3 * 3 * 2
CANDIDATE_CEILING = FULL_CELL_COUNT * REPLICAS_PER_CELL
SELECTED_COUNT = 100
ORIGIN_LAT_LON = (35.0, 139.0)
OSM_VERSION = "0.6"
SPEED_LIMITS_KPH = (30.0, 40.0, 50.0)
HEADING_PROFILES = {
    ROUTE_BINS[0]: (0.0, 1.0 / 30.0, 1.0 / 15.0, 0.1),
    ROUTE_BINS[1]: (0.0, 0.15, 0.30, 0.45),
    ROUTE_BINS[2]: (0.0, 0.35, 0.70, 1.05),
}
ZERO_OVERLAP_LEVELS = (
    "route",
    "state",
    "geometry",
    "semantic",
    "source",
    "seed",
    "latent_instance",
    "composite",
)


def canonical_bytes(value: Any) -> bytes:
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


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{label} must be lowercase SHA256")
    return value


def source_contract() -> dict[str, Any]:
    value = {
        "schema_version": SCHEMA_VERSION,
        "authority_schema": AUTHORITY_SCHEMA,
        "authority_sha256": AUTHORITY_SHA256,
        "authority_v1_preimage_sha256": AUTHORITY_V1_PREIMAGE_SHA256,
        "authority_normalization": (
            "no_signal_authority_sha256 corrected; lowercase SHA hex comparison"
        ),
        "parent_authority_sha256": PARENT_AUTHORITY_SHA256,
        "base_head": BASE_HEAD,
        "fixed_dp_head": FIXED_DP_HEAD,
        "status": "frozen_outcome_independent_project_authored_source_contract",
        "exact_dirs": dict(SOURCE_EXACT_DIRS),
        "audited_generator_base_sha256": dict(AUDITED_BASE_SHA256),
        "license": {
            "spdx": "MIT",
            "sha256": AUDITED_BASE_SHA256["license"],
            "third_party_map_payload_derived": False,
        },
        "upstream_diagnostic_roots": dict(UPSTREAM_DIAGNOSTIC_ROOTS),
        "universe": {
            "namespace": NAMESPACE,
            "families": list(FAMILIES),
            "risk_tiers": list(RISK_TIERS),
            "route_bins": list(ROUTE_BINS),
            "source_availability": list(SOURCE_AVAILABILITY),
            "replicas_per_cell": REPLICAS_PER_CELL,
            "full_cell_count": FULL_CELL_COUNT,
            "candidate_ceiling": CANDIDATE_CEILING,
            "ordinal_formula": "(((((f*3)+r)*3+g)*2+s)*2)+replica",
            "ordinal_min": 0,
            "ordinal_max": 251,
            "candidate_253_allowed": False,
            "dynamic_replacement_allowed": False,
        },
        "seeds": {
            "scenario_seed": "2750000000+ordinal",
            "actor_seed": "2751000000+ordinal",
            "selection_latent_seed": "2752000000+ordinal",
            "model_or_outcome_in_seed": False,
        },
        "map_route": {
            "map_count_per_candidate": 1,
            "ordered_adjacent_lanelet_count": 4,
            "route_centerline_point_count": 5,
            "heading_profiles_rad": {
                key: list(value) for key, value in HEADING_PROFILES.items()
            },
            "segment_lengths_m": [
                "36+0.17*(ordinal%11)",
                "38+0.19*(ordinal%13)",
                "40+0.23*(ordinal%17)",
                "42+0.29*(ordinal%19)",
            ],
            "lane_width_m": "3.20+0.05*((ordinal+replica)%7)",
            "speed_limit_cycle_kph": list(SPEED_LIMITS_KPH),
            "origin_lat_lon": list(ORIGIN_LAT_LON),
            "osm_version": OSM_VERSION,
            "finite_nonzero_simple_connected_reachable_required": True,
            "geometry_sha_unique_across_252": True,
        },
        "source_semantics": {
            "mapped_signal_required_chain": [
                "TrafficLight regulatory relation",
                "physical light way",
                "red/yellow/green bulbs",
                "controlled route lanelet",
                "certified stopline",
                "route arc",
                "same-tick phase authority",
            ],
            "future_phase_embedded": False,
            "no_signal_byte_absence_required": [
                "regulatory traffic-light relation",
                "physical traffic light",
                "light bulbs",
                "stop line",
                "phase or future schedule",
            ],
            "red_light_no_signal_retained_as_typed_source_case": True,
            "controlled_scenario_semantics_sha256": (
                AUDITED_BASE_SHA256["controlled_scenario_semantics"]
            ),
            "variant": "ordinal",
            "actor_rng": "PCG64DXSM(actor_seed)",
        },
        "selection": {
            "selected_count": SELECTED_COUNT,
            "family_risk_quotas": [list(row) for row in FAMILY_RISK_QUOTAS],
            "family_route_quotas": [list(row) for row in FAMILY_ROUTE_QUOTAS],
            "family_source_quotas": [list(row) for row in FAMILY_SOURCE_QUOTAS],
            "route_source_quotas": [list(row) for row in ROUTE_SOURCE_QUOTAS],
            "cell_selection_ceiling": 1,
            "rule": (
                "lexicographically_smallest_ordered_clone_sha_vector_among_"
                "zero_overlap_exact_quota_feasible_sets"
            ),
            "feasibility_proof_sha256": (
                "1ed2bf08a10889de99447b025b5d3697768952b10599961f35c3851cb72c3610"
            ),
            "drop_replace_suffix_or_outcome_selection_allowed": False,
        },
        "zero_overlap": {
            "levels": list(ZERO_OVERLAP_LEVELS),
            "forbidden_authorities": [
                "training",
                "calibration",
                "legacy_nonholdout",
                "bounded_single_route",
                "corrected_64_state_development",
                "Fresh_B2",
                "Fresh_B3",
                "Fresh_B4",
            ],
            "caller_status_or_root_trusted": False,
            "forbidden_inventories_rebuilt_from_sealed_bytes": True,
        },
        "execution_boundary": {
            "model_pool_selector_calls": 0,
            "outcome_values_read": False,
            "old_artifact_or_cas_writes": 0,
            "training_or_retraining": False,
            "fresh_holdout_or_new_nonce": False,
            "fixed_dp_weights_theta_atoms_scales_change": False,
        },
        "continuation": {
            "only_after_contract_and_materialization_reviews_pass": True,
            "parent_b5ca_scientific_fields_unchanged": True,
            "continuation_preimage_is_canonical_ascii_json_lf": True,
            "multiroute_v2_exact_dir_template": (
                "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_v2_"
                "<implementation_first8>_<continuation_first8>_<role>"
            ),
        },
        "interpreter": {
            "local": LOCAL_INTERPRETER,
            "autodl": AUTODL_INTERPRETER,
            "minimum_version": [3, 10],
            "bare_python_or_python3_allowed": False,
        },
    }
    return validate_source_contract(value)


def validate_source_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    row = deepcopy(dict(value))
    if (
        row.get("schema_version") != SCHEMA_VERSION
        or row.get("authority_schema") != AUTHORITY_SCHEMA
        or row.get("authority_sha256") != AUTHORITY_SHA256
        or row.get("base_head") != BASE_HEAD
        or row.get("fixed_dp_head") != FIXED_DP_HEAD
        or row.get("exact_dirs") != SOURCE_EXACT_DIRS
        or row.get("audited_generator_base_sha256") != AUDITED_BASE_SHA256
    ):
        raise ValueError("project-authored source authority drifted")
    universe = row.get("universe", {})
    if (
        universe.get("candidate_ceiling") != 252
        or universe.get("replicas_per_cell") != 2
        or universe.get("full_cell_count") != 126
        or universe.get("candidate_253_allowed") is not False
        or universe.get("dynamic_replacement_allowed") is not False
    ):
        raise ValueError("project-authored source universe drifted")
    selection = row.get("selection", {})
    if (
        selection.get("selected_count") != 100
        or selection.get("cell_selection_ceiling") != 1
        or selection.get("family_risk_quotas")
        != [list(item) for item in FAMILY_RISK_QUOTAS]
        or selection.get("family_route_quotas")
        != [list(item) for item in FAMILY_ROUTE_QUOTAS]
        or selection.get("family_source_quotas")
        != [list(item) for item in FAMILY_SOURCE_QUOTAS]
        or selection.get("route_source_quotas")
        != [list(item) for item in ROUTE_SOURCE_QUOTAS]
    ):
        raise ValueError("project-authored source quota topology drifted")
    execution = row.get("execution_boundary", {})
    if (
        execution.get("model_pool_selector_calls") != 0
        or execution.get("outcome_values_read") is not False
        or execution.get("old_artifact_or_cas_writes") != 0
    ):
        raise ValueError("project-authored source execution boundary drifted")
    if row.get("interpreter", {}).get("bare_python_or_python3_allowed") is not False:
        raise ValueError("project-authored source interpreter policy drifted")
    return row


def decode_ordinal(ordinal: int) -> dict[str, Any]:
    if isinstance(ordinal, bool) or type(ordinal) is not int or not 0 <= ordinal < 252:
        raise ValueError("candidate ordinal must be in [0,251]")
    remainder, replica = divmod(ordinal, 2)
    remainder, source_index = divmod(remainder, 2)
    remainder, route_index = divmod(remainder, 3)
    family_index, risk_index = divmod(remainder, 3)
    if not 0 <= family_index < 7:
        raise RuntimeError("ordinal decoding drifted")
    return {
        "ordinal": ordinal,
        "family_index": family_index,
        "risk_index": risk_index,
        "route_index": route_index,
        "source_index": source_index,
        "replica": replica,
        "family": FAMILIES[family_index],
        "risk_tier": RISK_TIERS[risk_index],
        "route_bin": ROUTE_BINS[route_index],
        "source_availability": SOURCE_AVAILABILITY[source_index],
        "scenario_seed": 2_750_000_000 + ordinal,
        "actor_seed": 2_751_000_000 + ordinal,
        "selection_latent_seed": 2_752_000_000 + ordinal,
    }


def _segment_lengths(ordinal: int) -> tuple[float, float, float, float]:
    return (
        36.0 + 0.17 * (ordinal % 11),
        38.0 + 0.19 * (ordinal % 13),
        40.0 + 0.23 * (ordinal % 17),
        42.0 + 0.29 * (ordinal % 19),
    )


def _route_geometry(spec: Mapping[str, Any]) -> dict[str, Any]:
    headings = HEADING_PROFILES[str(spec["route_bin"])]
    lengths = _segment_lengths(int(spec["ordinal"]))
    centers = [(0.0, 0.0)]
    for length, heading in zip(lengths, headings, strict=True):
        x, y = centers[-1]
        centers.append(
            (x + length * math.cos(heading), y + length * math.sin(heading))
        )
    width = 3.20 + 0.05 * (
        (int(spec["ordinal"]) + int(spec["replica"])) % 7
    )
    left, right = _offset_polyline(centers, width)
    payload = {
        "schema_version": "camp_dp_v25_project_authored_route_geometry_v1",
        "centerline_points_m": _rounded_points(centers),
        "segment_headings_rad": [round(float(value), 12) for value in headings],
        "segment_lengths_m": [round(float(value), 12) for value in lengths],
        "left_boundary_m": _rounded_points(left),
        "right_boundary_m": _rounded_points(right),
        "lane_width_m": round(width, 12),
        "speed_limit_kph": SPEED_LIMITS_KPH[int(spec["ordinal"]) % 3],
    }
    _validate_geometry_payload(payload, expected_route_bin=str(spec["route_bin"]))
    return payload


def _rounded_points(points: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[round(float(point[0]), 9), round(float(point[1]), 9)] for point in points]


def _offset_polyline(
    centers: Sequence[tuple[float, float]], width: float
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    if len(centers) != 5 or not math.isfinite(width) or width <= 0.0:
        raise ValueError("route polyline or width is invalid")
    normals = []
    for start, end in zip(centers[:-1], centers[1:], strict=True):
        dx, dy = end[0] - start[0], end[1] - start[1]
        norm = math.hypot(dx, dy)
        if norm <= 0.0:
            raise ValueError("route segment is zero length")
        normals.append((-dy / norm, dx / norm))
    vertex_normals = [normals[0]]
    for left, right in zip(normals[:-1], normals[1:], strict=True):
        sx, sy = left[0] + right[0], left[1] + right[1]
        norm = math.hypot(sx, sy)
        vertex_normals.append(
            right if norm <= 1e-12 else (sx / norm, sy / norm)
        )
    vertex_normals.append(normals[-1])
    half = 0.5 * width
    left_points = [
        (point[0] + normal[0] * half, point[1] + normal[1] * half)
        for point, normal in zip(centers, vertex_normals, strict=True)
    ]
    right_points = [
        (point[0] - normal[0] * half, point[1] - normal[1] * half)
        for point, normal in zip(centers, vertex_normals, strict=True)
    ]
    return left_points, right_points


def _wrap(value: float) -> float:
    return (value + math.pi) % (2.0 * math.pi) - math.pi


def _route_bin(headings: Sequence[float]) -> str:
    delta = abs(_wrap(float(headings[-1]) - float(headings[0])))
    if delta <= 0.15:
        return ROUTE_BINS[0]
    if delta <= 0.75:
        return ROUTE_BINS[1]
    return ROUTE_BINS[2]


def _segments_intersect(
    a: Sequence[float],
    b: Sequence[float],
    c: Sequence[float],
    d: Sequence[float],
) -> bool:
    def orient(p: Sequence[float], q: Sequence[float], r: Sequence[float]) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (
            r[0] - p[0]
        )

    o1, o2 = orient(a, b, c), orient(a, b, d)
    o3, o4 = orient(c, d, a), orient(c, d, b)
    return o1 * o2 < 0.0 and o3 * o4 < 0.0


def _polyline_self_intersects(points: Sequence[Sequence[float]]) -> bool:
    for left in range(len(points) - 1):
        for right in range(left + 2, len(points) - 1):
            if _segments_intersect(
                points[left],
                points[left + 1],
                points[right],
                points[right + 1],
            ):
                return True
    return False


def _validate_geometry_payload(
    payload: Mapping[str, Any], *, expected_route_bin: str
) -> None:
    centers = np.asarray(payload.get("centerline_points_m"), dtype=np.float64)
    left = np.asarray(payload.get("left_boundary_m"), dtype=np.float64)
    right = np.asarray(payload.get("right_boundary_m"), dtype=np.float64)
    headings = np.asarray(payload.get("segment_headings_rad"), dtype=np.float64)
    lengths = np.asarray(payload.get("segment_lengths_m"), dtype=np.float64)
    if (
        centers.shape != (5, 2)
        or left.shape != (5, 2)
        or right.shape != (5, 2)
        or headings.shape != (4,)
        or lengths.shape != (4,)
        or not np.all(np.isfinite(np.concatenate((centers.ravel(), left.ravel(), right.ravel(), headings, lengths))))
        or np.any(lengths <= 0.0)
        or not math.isfinite(float(payload.get("lane_width_m", math.nan)))
        or float(payload["lane_width_m"]) <= 0.0
    ):
        raise ValueError("project-authored route geometry is invalid")
    measured = np.linalg.norm(np.diff(centers, axis=0), axis=1)
    if not np.allclose(measured, lengths, atol=2e-8, rtol=0.0):
        raise ValueError("project-authored segment length drifted")
    if _route_bin(headings.tolist()) != expected_route_bin:
        raise ValueError("project-authored route bin drifted")
    if _polyline_self_intersects(left.tolist()) or _polyline_self_intersects(
        right.tolist()
    ):
        raise ValueError("project-authored boundary self-intersects")
    for index in range(4):
        if _segments_intersect(
            left[index],
            left[index + 1],
            right[index],
            right[index + 1],
        ):
            raise ValueError("project-authored lanelet boundary crosses")


def _lat_lon(point: Sequence[float]) -> tuple[str, str]:
    lat0, lon0 = ORIGIN_LAT_LON
    lat = lat0 + float(point[1]) / 111_111.0
    lon = lon0 + float(point[0]) / (111_111.0 * math.cos(math.radians(lat0)))
    return f"{lat:.12f}", f"{lon:.12f}"


def _element(
    name: str,
    attrs: Mapping[str, Any],
    *,
    parent: ET.Element | None = None,
) -> ET.Element:
    node = ET.Element(name, {key: str(value) for key, value in attrs.items()})
    if parent is not None:
        parent.append(node)
    return node


def _tag(parent: ET.Element, key: str, value: Any) -> None:
    _element("tag", {"k": key, "v": value}, parent=parent)


def _map_bytes(
    spec: Mapping[str, Any], geometry: Mapping[str, Any]
) -> tuple[bytes, dict[str, Any]]:
    ordinal = int(spec["ordinal"])
    base = 3_000_000 + ordinal * 1_000
    root = _element(
        "osm",
        {
            "version": OSM_VERSION,
            "generator": "camp-v25-project-authored-multiroute-source-v1",
        },
    )
    centers = geometry["centerline_points_m"]
    left = geometry["left_boundary_m"]
    right = geometry["right_boundary_m"]
    left_node_ids = [base + 1 + index for index in range(5)]
    right_node_ids = [base + 11 + index for index in range(5)]
    for node_id, point in zip(left_node_ids, left, strict=True):
        lat, lon = _lat_lon(point)
        _element("node", {"id": node_id, "lat": lat, "lon": lon}, parent=root)
    for node_id, point in zip(right_node_ids, right, strict=True):
        lat, lon = _lat_lon(point)
        _element("node", {"id": node_id, "lat": lat, "lon": lon}, parent=root)
    boundary_ways = []
    for segment in range(4):
        pair = (base + 101 + 2 * segment, base + 102 + 2 * segment)
        for way_id, nodes in (
            (pair[0], left_node_ids[segment : segment + 2]),
            (pair[1], right_node_ids[segment : segment + 2]),
        ):
            way = _element("way", {"id": way_id}, parent=root)
            for node_id in nodes:
                _element("nd", {"ref": node_id}, parent=way)
            _tag(way, "type", "line_thin")
            _tag(way, "subtype", "solid")
        boundary_ways.append(pair)

    signal_chain: dict[str, Any]
    regulatory_id = None
    if spec["source_availability"] == "mapped_signal":
        p0, p1 = np.asarray(centers[0]), np.asarray(centers[1])
        stop_center = p0 + 0.82 * (p1 - p0)
        normal = np.asarray([0.0, 1.0])
        half = 0.54 * float(geometry["lane_width_m"])
        stop_points = [stop_center + half * normal, stop_center - half * normal]
        stop_nodes = [base + 31, base + 32]
        for node_id, point in zip(stop_nodes, stop_points, strict=True):
            lat, lon = _lat_lon(point)
            _element("node", {"id": node_id, "lat": lat, "lon": lon}, parent=root)
        stop_way = base + 201
        stop = _element("way", {"id": stop_way}, parent=root)
        for node_id in stop_nodes:
            _element("nd", {"ref": node_id}, parent=stop)
        _tag(stop, "type", "stop_line")
        _tag(stop, "subtype", "solid")

        light_points = [
            stop_center + np.asarray([2.0, float(geometry["lane_width_m"]) + 1.0]),
            stop_center + np.asarray([2.0, float(geometry["lane_width_m"]) + 1.8]),
        ]
        light_nodes = [base + 41, base + 42]
        for node_id, point in zip(light_nodes, light_points, strict=True):
            lat, lon = _lat_lon(point)
            node = _element(
                "node", {"id": node_id, "lat": lat, "lon": lon}, parent=root
            )
            _tag(node, "ele", "4.0")
        light_way = base + 202
        light = _element("way", {"id": light_way}, parent=root)
        for node_id in light_nodes:
            _element("nd", {"ref": node_id}, parent=light)
        _tag(light, "type", "traffic_light")
        _tag(light, "subtype", "red_yellow_green")

        bulb_nodes = [base + 51, base + 52, base + 53]
        for index, (node_id, color) in enumerate(
            zip(bulb_nodes, ("red", "yellow", "green"), strict=True)
        ):
            point = light_points[0] + np.asarray([0.0, 0.18 * index])
            lat, lon = _lat_lon(point)
            node = _element(
                "node", {"id": node_id, "lat": lat, "lon": lon}, parent=root
            )
            _tag(node, "ele", "4.25")
            _tag(node, "color", color)
        bulb_way = base + 203
        bulbs = _element("way", {"id": bulb_way}, parent=root)
        for node_id in bulb_nodes:
            _element("nd", {"ref": node_id}, parent=bulbs)
        _tag(bulbs, "type", "light_bulbs")
        _tag(bulbs, "traffic_light_id", light_way)

        regulatory_id = base + 301
        regulatory = _element("relation", {"id": regulatory_id}, parent=root)
        for way_id, role in (
            (stop_way, "ref_line"),
            (light_way, "refers"),
            (bulb_way, "light_bulbs"),
        ):
            _element(
                "member",
                {"type": "way", "ref": way_id, "role": role},
                parent=regulatory,
            )
        _tag(regulatory, "type", "regulatory_element")
        _tag(regulatory, "subtype", "traffic_light")
        signal_chain = {
            "traffic_light_regulatory_element_id": regulatory_id,
            "physical_traffic_light_id": light_way,
            "light_bulb_linestring_id": bulb_way,
            "certified_stop_line_id": stop_way,
            "certified_stop_line_geometry_m": _rounded_points(stop_points),
            "stop_line_route_arc_m": round(0.82 * float(geometry["segment_lengths_m"][0]), 9),
            "same_tick_phase_authority": (
                "controlled_scenario_phase_at_current_tick_no_future_phase"
            ),
            "future_phase_embedded": False,
        }
    else:
        signal_chain = {
            "absence_contract": (
                "no regulatory relation, light, bulbs, stopline, phase, or future schedule"
            ),
            "future_phase_embedded": False,
        }

    lanelet_ids = []
    for segment, (left_way, right_way) in enumerate(boundary_ways):
        lanelet_id = base + 401 + segment
        relation = _element("relation", {"id": lanelet_id}, parent=root)
        for way_id, role in ((left_way, "left"), (right_way, "right")):
            _element(
                "member",
                {"type": "way", "ref": way_id, "role": role},
                parent=relation,
            )
        if segment == 0 and regulatory_id is not None:
            _element(
                "member",
                {
                    "type": "relation",
                    "ref": regulatory_id,
                    "role": "regulatory_element",
                },
                parent=relation,
            )
        _tag(relation, "type", "lanelet")
        _tag(relation, "subtype", "road")
        _tag(relation, "one_way", "yes")
        _tag(relation, "participant:vehicle", "yes")
        _tag(relation, "speed_limit", geometry["speed_limit_kph"])
        lanelet_ids.append(lanelet_id)
    ET.indent(root, space="  ")
    raw = ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"
    inventory = {
        "source_availability": spec["source_availability"],
        "ordered_lanelet_ids": lanelet_ids,
        "lanelet_adjacency": [
            [lanelet_ids[index], lanelet_ids[index + 1]] for index in range(3)
        ],
        "signal_chain": signal_chain,
        "signal_chain_sha256": canonical_sha256(signal_chain),
        "runtime_phase_embedded": False,
        "future_phase_embedded": False,
        "outcome_fields_consumed": [],
    }
    _validate_map_bytes(raw, inventory, geometry)
    return raw, inventory


def _tags(element: ET.Element) -> dict[str, str]:
    return {
        str(tag.attrib.get("k")): str(tag.attrib.get("v"))
        for tag in element.findall("tag")
    }


def _validate_map_bytes(
    raw: bytes,
    inventory: Mapping[str, Any],
    geometry: Mapping[str, Any],
) -> None:
    if not raw.endswith(b"\n"):
        raise ValueError("project-authored OSM bytes require one terminal LF")
    root = ET.fromstring(raw)
    if root.tag != "osm" or root.attrib.get("version") != OSM_VERSION:
        raise ValueError("project-authored OSM root drifted")
    relations = root.findall("relation")
    lanelets = [
        item for item in relations if _tags(item).get("type") == "lanelet"
    ]
    if len(lanelets) != 4 or len(inventory.get("ordered_lanelet_ids", [])) != 4:
        raise ValueError("project-authored route requires four lanelets")
    if inventory.get("lanelet_adjacency") != [
        [
            inventory["ordered_lanelet_ids"][index],
            inventory["ordered_lanelet_ids"][index + 1],
        ]
        for index in range(3)
    ]:
        raise ValueError("project-authored lanelet adjacency drifted")
    all_tags = [_tags(item) for item in root.iter()]
    all_roles = [
        member.attrib.get("role", "")
        for relation in relations
        for member in relation.findall("member")
    ]
    source = inventory.get("source_availability")
    if source == "mapped_signal":
        regulatory = [
            item
            for item in relations
            if _tags(item)
            == {"type": "regulatory_element", "subtype": "traffic_light"}
        ]
        if len(regulatory) != 1:
            raise ValueError("mapped-signal regulatory relation missing")
        required_roles = {"ref_line", "refers", "light_bulbs"}
        roles = {
            member.attrib.get("role")
            for member in regulatory[0].findall("member")
        }
        if roles != required_roles:
            raise ValueError("mapped-signal physical chain drifted")
        if not any(tags.get("type") == "traffic_light" for tags in all_tags):
            raise ValueError("mapped-signal physical light missing")
        colors = {
            tags.get("color") for tags in all_tags if tags.get("color") is not None
        }
        if colors != {"red", "yellow", "green"}:
            raise ValueError("mapped-signal bulb colors drifted")
        if inventory["signal_chain"].get("future_phase_embedded") is not False:
            raise ValueError("mapped-signal future phase was embedded")
    elif source == "no_signal":
        prohibited_values = {
            "regulatory_element",
            "traffic_light",
            "light_bulbs",
            "stop_line",
            "phase",
            "future_schedule",
        }
        flattened = {value for tags in all_tags for value in tags.values()}
        if flattened.intersection(prohibited_values) or set(all_roles).intersection(
            {"ref_line", "refers", "light_bulbs", "regulatory_element"}
        ):
            raise ValueError("no-signal OSM contains hidden signal authority")
    else:
        raise ValueError("project-authored source availability drifted")
    _validate_geometry_payload(
        geometry, expected_route_bin=_route_bin(geometry["segment_headings_rad"])
    )


def _selection_latent(spec: Mapping[str, Any]) -> dict[str, Any]:
    rng = np.random.Generator(
        np.random.PCG64DXSM(int(spec["selection_latent_seed"]))
    )
    rows = np.zeros((8, 4), dtype="<f4")
    rows[1:] = rng.standard_normal(rows[1:].shape).astype("<f4")
    row_sha = [bytes_sha256(np.ascontiguousarray(row).tobytes()) for row in rows]
    if len(set(row_sha)) != 8 or not np.all(np.isfinite(rows)):
        raise RuntimeError("project-authored selection latent is invalid")
    return {
        "shape": [8, 4],
        "dtype": "<f4",
        "seed": int(spec["selection_latent_seed"]),
        "policy": "row0_zero_rows1_7_independent_pcg64dxsm_float32",
        "tensor_sha256": bytes_sha256(rows.tobytes()),
        "row_sha256": row_sha,
        "unique_row_sha256_cardinality": len(set(row_sha)),
        "raw_bytes_hex": rows.tobytes().hex(),
    }


def build_source_record(ordinal: int) -> dict[str, Any]:
    spec = decode_ordinal(ordinal)
    geometry = _route_geometry(spec)
    geometry_sha = canonical_sha256(geometry)
    map_bytes, signal_inventory = _map_bytes(spec, geometry)
    map_sha = bytes_sha256(map_bytes)
    centers = geometry["centerline_points_m"]
    headings = geometry["segment_headings_rad"]
    route_lanelet_arc_payload = {
        "ordered_lanelet_geometry": [
            {
                "start": centers[index],
                "end": centers[index + 1],
                "heading_rad": headings[index],
                "length_m": geometry["segment_lengths_m"][index],
            }
            for index in range(4)
        ],
        "speed_limit_kph": geometry["speed_limit_kph"],
    }
    route_sha = canonical_sha256(route_lanelet_arc_payload)
    route = {
        "record_key": f"project_source:{ordinal:03d}",
        "map_family_id": "project_authored_multiroute_source_v1",
        "identity_sha256": route_sha,
        "route_serialization_sha256": route_sha,
        "source_map_path": f"maps/{ordinal:03d}/lanelet2_map.osm",
        "source_map_sha256": map_sha,
        "route_spec": {
            "ordered_lanelet_ids": signal_inventory["ordered_lanelet_ids"],
            "centerline_points_m": centers,
            "goal_tolerance_m": 2.0,
            "goal_pass_window_m": 5.0,
        },
        "source_stratum": {
            "traffic_light": spec["source_availability"] == "mapped_signal",
            "branch_intersection": spec["route_bin"] != ROUTE_BINS[0],
        },
        "centerline_samples_m": centers,
        "centerline_headings_rad": headings,
        "source_route_length_m": round(
            sum(float(value) for value in geometry["segment_lengths_m"]), 9
        ),
    }
    scenario = build_controlled_scenario_case(
        route=route,
        corridor_group_sha256=canonical_sha256(
            {"namespace": NAMESPACE, "geometry_sha256": geometry_sha}
        ),
        split="project_authored_development_nonholdout",
        family=spec["family"],
        tier=spec["risk_tier"],
        variant=ordinal,
        seeds=(int(spec["scenario_seed"]),),
    )
    validate_controlled_scenario_case(scenario)
    actor_rng = np.random.Generator(np.random.PCG64DXSM(int(spec["actor_seed"])))
    actor_draws = actor_rng.standard_normal((max(1, len(scenario["actors"])), 4)).astype(
        "<f4"
    )
    actor_bytes = canonical_bytes(
        {
            "actors": scenario["actors"],
            "actor_rng_seed": spec["actor_seed"],
            "actor_rng_draws_sha256": bytes_sha256(actor_draws.tobytes()),
        }
    )
    selection_latent = _selection_latent(spec)
    no_signal_absence = {
        "regulatory_relation_count": 0,
        "physical_light_count": 0,
        "bulb_count": 0,
        "stopline_count": 0,
        "phase_or_future_schedule_count": 0,
    }
    if spec["source_availability"] == "mapped_signal":
        source_availability_receipt = {
            "class": "mapped_signal",
            "chain_sha256": signal_inventory["signal_chain_sha256"],
            "same_tick_phase_authority": True,
            "future_phase_embedded": False,
        }
    else:
        source_availability_receipt = {
            "class": "no_signal",
            "absence_inventory": no_signal_absence,
            "absence_inventory_sha256": canonical_sha256(no_signal_absence),
            "same_tick_phase_authority": False,
            "future_phase_embedded": False,
        }
    semantic_block = {
        "family": spec["family"],
        "risk_tier": spec["risk_tier"],
        "variant": ordinal,
        "controlled_scenario_parameters": scenario["parameters"],
        "actors": scenario["actors"],
        "signal_semantics": scenario["signal"],
        "source_availability": source_availability_receipt,
        "actor_rng": {
            "algorithm": "PCG64DXSM",
            "seed": spec["actor_seed"],
            "draw_shape": list(actor_draws.shape),
            "draw_dtype": "<f4",
            "draw_sha256": bytes_sha256(actor_draws.tobytes()),
        },
    }
    source_record = {
        "schema_version": (
            "camp_dp_v25_project_authored_multiroute_source_record_v1"
        ),
        "namespace": NAMESPACE,
        "ordinal": ordinal,
        "cell": {
            "family": spec["family"],
            "risk_tier": spec["risk_tier"],
            "route_bin": spec["route_bin"],
            "source_availability": spec["source_availability"],
            "replica": spec["replica"],
        },
        "seeds": {
            "scenario": spec["scenario_seed"],
            "actor": spec["actor_seed"],
            "selection_latent": spec["selection_latent_seed"],
        },
        "map": {
            "relative_path": route["source_map_path"],
            "sha256": map_sha,
            "logical_bytes": len(map_bytes),
            "osm_version": OSM_VERSION,
            "license_spdx": "MIT",
            "license_sha256": AUDITED_BASE_SHA256["license"],
            "third_party_payload_derived": False,
        },
        "route": {
            "route_lanelet_arc_payload": route_lanelet_arc_payload,
            "route_lanelet_arc_sha256": route_sha,
            "geometry": geometry,
            "geometry_sha256": geometry_sha,
            "route_bin": _route_bin(headings),
            "spawn_pose": [*centers[0], headings[0]],
            "goal_pose": [*centers[-1], headings[-1]],
            "spawn_to_goal_reachable": True,
        },
        "semantic_block": semantic_block,
        "semantic_block_sha256": canonical_sha256(semantic_block),
        "actor_bytes_sha256": bytes_sha256(actor_bytes),
        "source_availability_receipt": source_availability_receipt,
        "source_availability_receipt_sha256": canonical_sha256(
            source_availability_receipt
        ),
        "selection_latent_instance": selection_latent,
        "selection_latent_instance_sha256": canonical_sha256(selection_latent),
        "outcome_blind": True,
        "outcome_fields_consumed": [],
        "model_pool_selector_calls": 0,
    }
    source_record["source_record_sha256"] = canonical_sha256(source_record)
    validate_source_record(source_record, map_bytes)
    return {"record": source_record, "map_bytes": map_bytes}


def validate_source_record(
    value: Mapping[str, Any], map_bytes: bytes
) -> dict[str, Any]:
    row = deepcopy(dict(value))
    expected_sha = row.pop("source_record_sha256", None)
    if (
        row.get("schema_version")
        != "camp_dp_v25_project_authored_multiroute_source_record_v1"
        or row.get("namespace") != NAMESPACE
        or row.get("outcome_blind") is not True
        or row.get("outcome_fields_consumed") != []
        or row.get("model_pool_selector_calls") != 0
    ):
        raise ValueError("project-authored source record boundary drifted")
    if canonical_sha256(row) != _sha(expected_sha, "source record"):
        raise ValueError("project-authored source record SHA drifted")
    ordinal = row.get("ordinal")
    spec = decode_ordinal(ordinal)
    expected_cell = {
        "family": spec["family"],
        "risk_tier": spec["risk_tier"],
        "route_bin": spec["route_bin"],
        "source_availability": spec["source_availability"],
        "replica": spec["replica"],
    }
    if row.get("cell") != expected_cell or row.get("seeds") != {
        "scenario": spec["scenario_seed"],
        "actor": spec["actor_seed"],
        "selection_latent": spec["selection_latent_seed"],
    }:
        raise ValueError("project-authored source spec drifted")
    if bytes_sha256(map_bytes) != row["map"]["sha256"]:
        raise ValueError("project-authored map byte SHA drifted")
    if (
        row["map"].get("license_spdx") != "MIT"
        or row["map"].get("license_sha256") != AUDITED_BASE_SHA256["license"]
        or row["map"].get("third_party_payload_derived") is not False
        or row["map"].get("logical_bytes") != len(map_bytes)
        or row["map"].get("osm_version") != OSM_VERSION
    ):
        raise ValueError("project-authored map provenance drifted")
    geometry = row["route"]["geometry"]
    if canonical_sha256(geometry) != row["route"]["geometry_sha256"]:
        raise ValueError("project-authored geometry SHA drifted")
    _validate_geometry_payload(geometry, expected_route_bin=spec["route_bin"])
    _validate_map_bytes(map_bytes, _signal_inventory_from_record(row), geometry)
    if row["route"].get("spawn_to_goal_reachable") is not True:
        raise ValueError("project-authored route is not reachable")
    latent = row["selection_latent_instance"]
    raw = bytes.fromhex(latent["raw_bytes_hex"])
    array = np.frombuffer(raw, dtype="<f4").reshape((8, 4))
    actual_rows = [bytes_sha256(item.tobytes()) for item in array]
    if (
        bytes_sha256(raw) != latent["tensor_sha256"]
        or actual_rows != latent["row_sha256"]
        or len(set(actual_rows)) != 8
        or not np.array_equal(array[0], np.zeros((4,), dtype="<f4"))
        or not np.all(np.isfinite(array))
    ):
        raise ValueError("project-authored selection latent drifted")
    restored = deepcopy(dict(value))
    return restored


def _signal_inventory_from_record(row: Mapping[str, Any]) -> dict[str, Any]:
    source = row["cell"]["source_availability"]
    receipt = row["source_availability_receipt"]
    if source == "mapped_signal":
        signal_chain = {
            **row["semantic_block"]["source_availability"],
            "future_phase_embedded": False,
        }
        # The byte-level validator reconstructs the physical chain; this
        # normalized record only supplies the availability class.
        return {
            "source_availability": source,
            "ordered_lanelet_ids": row["route"]["route_spec_lanelet_ids"]
            if "route_spec_lanelet_ids" in row["route"]
            else _ordered_lanelet_ids_from_ordinal(int(row["ordinal"])),
            "lanelet_adjacency": _adjacency_from_ordinal(int(row["ordinal"])),
            "signal_chain": signal_chain,
        }
    return {
        "source_availability": source,
        "ordered_lanelet_ids": _ordered_lanelet_ids_from_ordinal(int(row["ordinal"])),
        "lanelet_adjacency": _adjacency_from_ordinal(int(row["ordinal"])),
        "signal_chain": receipt,
    }


def _ordered_lanelet_ids_from_ordinal(ordinal: int) -> list[int]:
    base = 3_000_000 + ordinal * 1_000
    return [base + 401 + index for index in range(4)]


def _adjacency_from_ordinal(ordinal: int) -> list[list[int]]:
    ids = _ordered_lanelet_ids_from_ordinal(ordinal)
    return [[ids[index], ids[index + 1]] for index in range(3)]


def candidate_from_source_record(
    source_record: Mapping[str, Any],
    *,
    source_contract_root_sha256: str,
) -> dict[str, Any]:
    record = deepcopy(dict(source_record))
    ordinal = int(record["ordinal"])
    route = record["route"]
    semantic = record["semantic_block"]
    signal_sha = record["source_availability_receipt_sha256"]
    actor_sha = record["actor_bytes_sha256"]
    seed_sha = canonical_sha256(record["seeds"])
    latent_sha = record["selection_latent_instance_sha256"]
    source_sha = record["source_record_sha256"]
    payload = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_id_free_clone_payload_v1"
        ),
        "canonical_route_lanelet_arc_sha256": route[
            "route_lanelet_arc_sha256"
        ],
        "route_geometry_sha256": route["geometry_sha256"],
        "semantic_family": record["cell"]["family"],
        "risk_tier": record["cell"]["risk_tier"],
        "source_availability": record["cell"]["source_availability"],
        "certified_signal_stopline_inventory_sha256": signal_sha,
        "canonical_state_actor_geometry_sha256": actor_sha,
        "scenario_source_bytes_sha256": source_sha,
        "scenario_seed_sha256": seed_sha,
        "latent_instance_sha256": latent_sha,
    }
    clone_key = canonical_sha256(payload)
    row = {
        "clone_payload": payload,
        "clone_key_sha256": clone_key,
        "route_bin": record["cell"]["route_bin"],
        "overlap_keys": {
            "route": route["route_lanelet_arc_sha256"],
            "state": canonical_sha256(
                {
                    "spawn": route["spawn_pose"],
                    "goal": route["goal_pose"],
                    "actors": actor_sha,
                    "source": source_sha,
                }
            ),
            "geometry": route["geometry_sha256"],
            "semantic": canonical_sha256(
                {
                    "family": semantic["family"],
                    "tier": semantic["risk_tier"],
                    "signal_stopline": signal_sha,
                    "actor_geometry": actor_sha,
                }
            ),
            "source": source_sha,
            "seed": seed_sha,
            "latent_instance": latent_sha,
            "composite": clone_key,
        },
        "source_binding": {
            "artifact_path": SOURCE_EXACT_DIRS["materialization"],
            "artifact_root_sha256": _sha(
                source_contract_root_sha256, "source contract root"
            ),
            "inventory_entry_path": f"source_records.json#/records/{ordinal}",
            "inventory_entry_sha256": source_sha,
        },
    }
    return validate_candidate(row)


def _select_project_source_manifest_unchecked(
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if len(candidates) != CANDIDATE_CEILING:
        raise ValueError("project-authored source candidate ceiling drifted")
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        row = validate_candidate(candidate)
        payload = row["clone_payload"]
        cell = (
            payload["semantic_family"],
            payload["risk_tier"],
            row["route_bin"],
            payload["source_availability"],
        )
        groups[cell].append(row)
    if len(groups) != FULL_CELL_COUNT or any(len(rows) != 2 for rows in groups.values()):
        raise ValueError("project-authored source cell/replica topology drifted")
    per_cell_minimum = [
        min(rows, key=lambda item: item["clone_key_sha256"])
        for rows in groups.values()
    ]
    selected = select_lexicographically_smallest_feasible(per_cell_minimum)
    selected["schema_version"] = (
        "camp_dp_v25_project_authored_multiroute_selected_manifest_v1"
    )
    selected["authority_sha256"] = AUTHORITY_SHA256
    selected["candidate_ceiling"] = CANDIDATE_CEILING
    selected["eligible_zero_overlap_count"] = CANDIDATE_CEILING
    selected["cell_selection_ceiling"] = 1
    selected["selected_source_record_ordinals"] = [
        int(row["source_binding"]["inventory_entry_path"].rsplit("/", 1)[-1])
        for row in selected["entries"]
    ]
    selected.pop("manifest_sha256", None)
    selected["manifest_sha256"] = canonical_sha256(selected)
    return selected


def select_project_source_manifest(
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    selected = _select_project_source_manifest_unchecked(candidates)
    validate_project_source_manifest(selected, candidates)
    return selected


def validate_project_source_manifest(
    manifest: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    row = deepcopy(dict(manifest))
    manifest_sha = row.pop("manifest_sha256", None)
    if canonical_sha256(row) != _sha(manifest_sha, "selected manifest"):
        raise ValueError("project-authored selected manifest SHA drifted")
    if (
        row.get("schema_version")
        != "camp_dp_v25_project_authored_multiroute_selected_manifest_v1"
        or row.get("authority_sha256") != AUTHORITY_SHA256
        or row.get("candidate_ceiling") != 252
        or row.get("selected_count") != 100
        or row.get("cell_selection_ceiling") != 1
    ):
        raise ValueError("project-authored selected manifest topology drifted")
    expected = _select_project_source_manifest_unchecked(candidates)
    if row != {key: value for key, value in expected.items() if key != "manifest_sha256"}:
        raise ValueError("project-authored selected manifest is not exact minimal")
    return deepcopy(dict(manifest))


def build_universe(
    *, source_contract_root_sha256: str
) -> dict[str, Any]:
    records = []
    candidates = []
    maps: dict[str, bytes] = {}
    for ordinal in range(CANDIDATE_CEILING):
        built = build_source_record(ordinal)
        record = built["record"]
        maps[record["map"]["relative_path"]] = built["map_bytes"]
        records.append(record)
        candidates.append(
            candidate_from_source_record(
                record,
                source_contract_root_sha256=source_contract_root_sha256,
            )
        )
    if (
        len({row["source_record_sha256"] for row in records}) != 252
        or len({row["route"]["geometry_sha256"] for row in records}) != 252
        or len({row["clone_key_sha256"] for row in candidates}) != 252
    ):
        raise RuntimeError("project-authored source universe uniqueness drifted")
    manifest = select_project_source_manifest(candidates)
    return {
        "records": records,
        "candidates": candidates,
        "maps": maps,
        "selected_manifest": manifest,
    }
