"""Independent local-literal review for the V25 industrial multiroute stage.

This module intentionally does not import the multiroute producer module.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping, Sequence

from .diffusion_planner_v25_industrial_evaluation_review_v3 import (
    review_contract_v3_literal,
)


AUTHORITY_SHA256 = (
    "b5ca942b4a91c0ef0cbe4e9ff8180852fb193471fb9f73514f6017622547718f"
)
BASE_HEAD = "923e6b29b004778628cf63fe9981f64d45571c4f"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = (
    "camp_dp_v25_industrial_v3_multiroute_independent_nonholdout_contract_v1"
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
ARMS = ("pool_matched_candidate0", "Static14D", "Scene14D")
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
FS = ((8, 7), (7, 8), (7, 7), (7, 7), (8, 6), (6, 8), (7, 7))
GS = ((17, 16), (17, 17), (16, 17))
CAPTURE_CLASSES = (
    "runner_capture_direct",
    "runner_capture_plus_frozen_transform",
    "route_inapplicable",
    "receipt_field_gap_fixable_before_model",
    "transform_ambiguity",
    "permanent_evidence_missing",
)
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
CLONE_FIELDS = {
    "schema_version",
    "canonical_route_lanelet_arc_sha256",
    "route_geometry_sha256",
    "semantic_family",
    "risk_tier",
    "source_availability",
    "certified_signal_stopline_inventory_sha256",
    "canonical_state_actor_geometry_sha256",
    "scenario_source_bytes_sha256",
    "scenario_seed_sha256",
    "latent_instance_sha256",
}


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


def _sha(value: Any) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError("reviewed SHA is invalid")
    return value


def review_contract_literal(
    value: Mapping[str, Any],
    *,
    accepted_industrial_contract: Mapping[str, Any],
) -> dict[str, Any]:
    reviewed_industrial = review_contract_v3_literal(accepted_industrial_contract)
    candidate = deepcopy(dict(value))
    if (
        candidate.get("schema_version") != SCHEMA_VERSION
        or candidate.get("authority_sha256") != AUTHORITY_SHA256
        or candidate.get("base_head") != BASE_HEAD
        or candidate.get("fixed_dp_head") != FIXED_DP_HEAD
    ):
        raise ValueError("reviewed multiroute authority drifted")
    manifest = candidate.get("manifest", {})
    expected_manifest = {
        "cluster_count": 100,
        "families": list(FAMILIES),
        "risk_tiers": list(RISKS),
        "route_bins": list(ROUTES),
        "source_availability": list(SOURCES),
        "family_risk_quotas": [list(row) for row in FR],
        "family_route_quotas": [list(row) for row in FG],
        "family_source_quotas": [list(row) for row in FS],
        "route_source_quotas": [list(row) for row in GS],
    }
    if any(manifest.get(key) != expected for key, expected in expected_manifest.items()):
        raise ValueError("reviewed manifest literal topology drifted")
    if manifest.get("no_drop_replace_suffix_or_complete_case") is not True:
        raise ValueError("reviewed failure retention drifted")
    architecture = candidate.get("architecture", {})
    if (
        architecture.get("generator")
        != "new_single_invocation_batched_k8_candidate_pool"
        or architecture.get("arms") != list(ARMS)
        or architecture.get("formal_model_calls_per_attempted_tick") != 1
        or architecture.get("sequential_calls") != 0
        or architecture.get("post_pool_model_dp_latent_candidate_generation_calls")
        != 0
    ):
        raise ValueError("reviewed architecture topology drifted")
    denominator = candidate.get("denominator", {})
    if (
        denominator.get("paired_cluster_count") != 100
        or denominator.get("arm_run_count") != 300
        or denominator.get("ticks_per_arm") != 64
        or denominator.get("planned_tick_slots") != 19_200
        or denominator.get("planned_formal_model_calls") != 19_200
    ):
        raise ValueError("reviewed denominator drifted")
    capture = candidate.get("capture_matrix", {})
    if (
        capture.get("parent_count") != 56
        or capture.get("leaf_count") != 161
        or capture.get("classes") != list(CAPTURE_CLASSES)
        or capture.get("leaf_registry_sha256")
        != _digest(reviewed_industrial["scalar_leaf_registry"])
    ):
        raise ValueError("reviewed 161-leaf binding drifted")
    statistics = candidate.get("statistics", {})
    if (
        statistics.get("independent_n") != 100
        or statistics.get("cluster_first") is not True
        or statistics.get("ticks_arms_or_k8_rows_as_independent_n") is not False
        or statistics.get("numeric_margin_authorized") is not False
        or statistics.get("hard_stage_pass_depends_on_effect_direction") is not False
    ):
        raise ValueError("reviewed statistical topology drifted")
    claim = candidate.get("claim_boundary", {})
    if (
        claim.get("legacy_safetycost_role")
        != "immutable_legacy_exploratory_diagnostic_only"
        or claim.get("weighted_total_allowed") is not False
        or claim.get("fresh_or_confirmatory_claim") is not False
        or claim.get("legacy_honest_no_claim_unchanged") is not True
    ):
        raise ValueError("reviewed claim boundary drifted")
    if candidate.get("interpreter", {}).get("bare_python_or_python3_allowed") is not False:
        raise ValueError("reviewed interpreter policy drifted")
    return candidate


def _validate_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(row))
    if set(value) != {
        "clone_payload",
        "clone_key_sha256",
        "route_bin",
        "overlap_keys",
        "source_binding",
    }:
        raise ValueError("review candidate schema drifted")
    payload = value["clone_payload"]
    if type(payload) is not dict or set(payload) != CLONE_FIELDS:
        raise ValueError("review clone payload schema drifted")
    if payload.get("schema_version") != (
        "camp_dp_v25_industrial_v3_multiroute_id_free_clone_payload_v1"
    ):
        raise ValueError("review clone payload version drifted")
    if (
        payload.get("semantic_family") not in FAMILIES
        or payload.get("risk_tier") not in RISKS
        or payload.get("source_availability") not in SOURCES
        or value.get("route_bin") not in ROUTES
    ):
        raise ValueError("review candidate stratum drifted")
    for key, item in payload.items():
        if key in {
            "schema_version",
            "semantic_family",
            "risk_tier",
            "source_availability",
        }:
            continue
        _sha(item)
    if _digest(payload) != _sha(value["clone_key_sha256"]):
        raise ValueError("review clone key preimage drifted")
    overlap = value["overlap_keys"]
    if type(overlap) is not dict or set(overlap) != set(OVERLAP_LEVELS):
        raise ValueError("review overlap schema drifted")
    for item in overlap.values():
        _sha(item)
    semantic = _digest(
        {
            "family": payload["semantic_family"],
            "tier": payload["risk_tier"],
            "signal_stopline": payload[
                "certified_signal_stopline_inventory_sha256"
            ],
            "actor_geometry": payload["canonical_state_actor_geometry_sha256"],
        }
    )
    expected_layers = {
        "route": payload["canonical_route_lanelet_arc_sha256"],
        "geometry": payload["route_geometry_sha256"],
        "semantic": semantic,
        "source": payload["scenario_source_bytes_sha256"],
        "seed": payload["scenario_seed_sha256"],
        "latent_instance": payload["latent_instance_sha256"],
        "composite": value["clone_key_sha256"],
    }
    if any(overlap[key] != expected for key, expected in expected_layers.items()):
        raise ValueError("review overlap preimage drifted")
    binding = value["source_binding"]
    if (
        type(binding) is not dict
        or set(binding)
        != {
            "artifact_path",
            "artifact_root_sha256",
            "inventory_entry_path",
            "inventory_entry_sha256",
        }
    ):
        raise ValueError("review exact source binding drifted")
    _sha(binding["artifact_root_sha256"])
    _sha(binding["inventory_entry_sha256"])
    return value


def _cell(row: Mapping[str, Any]) -> tuple[int, int, int, int]:
    payload = row["clone_payload"]
    return (
        FAMILIES.index(payload["semantic_family"]),
        RISKS.index(payload["risk_tier"]),
        ROUTES.index(row["route_bin"]),
        SOURCES.index(payload["source_availability"]),
    )


def review_selected_manifest_literal(
    selected: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = [_validate_candidate(row) for row in selected]
    if len(rows) != 100 or len({row["clone_key_sha256"] for row in rows}) != 100:
        raise ValueError("review selected denominator or uniqueness drifted")
    if [row["clone_key_sha256"] for row in rows] != sorted(
        row["clone_key_sha256"] for row in rows
    ):
        raise ValueError("review selected order is not canonical")
    counts = Counter(_cell(row) for row in rows)
    for family in range(7):
        actual_risk = tuple(
            sum(
                counts[(family, risk, route, source)]
                for route in range(3)
                for source in range(2)
            )
            for risk in range(3)
        )
        actual_route = tuple(
            sum(
                counts[(family, risk, route, source)]
                for risk in range(3)
                for source in range(2)
            )
            for route in range(3)
        )
        actual_source = tuple(
            sum(
                counts[(family, risk, route, source)]
                for risk in range(3)
                for route in range(3)
            )
            for source in range(2)
        )
        if actual_risk != FR[family] or actual_route != FG[family] or actual_source != FS[family]:
            raise ValueError("review selected family margin drifted")
    actual_gs = tuple(
        tuple(
            sum(
                counts[(family, risk, route, source)]
                for family in range(7)
                for risk in range(3)
            )
            for source in range(2)
        )
        for route in range(3)
    )
    if actual_gs != GS:
        raise ValueError("review selected route/source margin drifted")
    return {
        "selected_count": 100,
        "family_risk": [list(row) for row in FR],
        "family_route": [list(row) for row in FG],
        "family_source": [list(row) for row in FS],
        "route_source": [list(row) for row in GS],
        "selected_sha256": _digest(rows),
    }


def review_overlap_literal(
    selected: Sequence[Mapping[str, Any]],
    forbidden: Mapping[str, Mapping[str, Sequence[str]]],
    expected_authorities: Sequence[str],
) -> dict[str, Any]:
    rows = [_validate_candidate(row) for row in selected]
    if set(forbidden) != set(expected_authorities):
        raise ValueError("review forbidden authority inventory drifted")
    result = {}
    for authority in expected_authorities:
        layers = forbidden[authority]
        if set(layers) != set(OVERLAP_LEVELS):
            raise ValueError("review forbidden overlap layer drifted")
        intersections = {}
        for level in OVERLAP_LEVELS:
            left = {row["overlap_keys"][level] for row in rows}
            right = {_sha(value) for value in layers[level]}
            intersections[level] = sorted(left.intersection(right))
        if any(intersections.values()):
            raise ValueError(f"review selected manifest overlaps {authority}")
        result[authority] = {
            "intersection_count": {
                level: len(intersections[level]) for level in OVERLAP_LEVELS
            },
            "intersection_sha256": {
                level: _digest(intersections[level]) for level in OVERLAP_LEVELS
            },
        }
    return result
