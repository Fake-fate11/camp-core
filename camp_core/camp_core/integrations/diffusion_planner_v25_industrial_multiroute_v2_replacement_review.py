"""Independent literal oracle for the multiroute-v2 consumer replacement."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from typing import Any, Mapping

import numpy as np

from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (
    build_controlled_scenario_case,
    validate_controlled_scenario_case,
)
from camp_core.integrations.diffusion_planner_v25_project_authored_multiroute_source import (
    NAMESPACE as SOURCE_NAMESPACE,
    build_source_record,
    validate_source_record,
)
from camp_core.integrations.diffusion_planner_v25_route_signal_authority import (
    MAPPED_SIGNAL_CHAIN_SCHEMA_VERSION,
    validate_mapped_signal_chain,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
    NO_SIGNAL_CHAIN_SCHEMA_VERSION,
    build_semantic_clone_payload,
    canonical_json_sha256,
    validate_no_signal_chain,
)


EXPECTED_AUTHORITY = (
    "c065e1b08e711a6cdeb84c14f94d5941019f613562ac452c028e8f903b537866"
)
EXPECTED_FIXED_DP = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_SELECTED_MANIFEST = (
    "b779319aa0d32847a13c7522edeffc35ac03a044483c176d699b60a97cb9c40c"
)
EXPECTED_OLD_CLASSIFICATION = (
    "post_model_runtime_no_signal_semantic_authority_binding_failure_"
    "after_5_of_100_clusters"
)
ROLE_NAMES = (
    "old_attempt_closeout",
    "old_attempt_closeout_review",
    "contract",
    "contract_review",
    "semantic_hardening_matrix",
    "semantic_hardening_matrix_review",
    "semantic_hardening_focused",
    "semantic_adapter_dryrun",
    "semantic_adapter_dryrun_review",
    "preflight",
    "preflight_review",
    "execution",
    "execution_review",
    "evaluation",
    "evaluation_review",
    "final_docs",
)


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def literal_exact_dirs(
    implementation_head: str, replacement_continuation_sha256: str
) -> dict[str, str]:
    prefix = (
        "/root/autodl-tmp/"
        "camp_dp_v25_industrial_v3_multiroute_v2_replacement_"
        f"{implementation_head[:8]}_{replacement_continuation_sha256[:8]}_"
    )
    return {role: prefix + role for role in ROLE_NAMES}


def review_contract_semantics(value: Mapping[str, Any]) -> dict[str, Any]:
    row = deepcopy(dict(value))
    digest = row.pop("contract_sha256", None)
    authority = row.get("authority", {})
    denominator = row.get("replacement_denominator")
    runtime = row.get("formal_runtime_semantics")
    if (
        _sha(row) != digest
        or row.get("schema_version")
        != (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "no_signal_consumer_replacement_v1"
        )
        or authority.get("high_authority_sha256") != EXPECTED_AUTHORITY
        or authority.get("fixed_dp_head") != EXPECTED_FIXED_DP
        or authority.get("selected_manifest_sha256")
        != EXPECTED_SELECTED_MANIFEST
        or row.get("old_attempt", {}).get("classification")
        != EXPECTED_OLD_CLASSIFICATION
        or row.get("old_attempt", {}).get("reuse") is not False
        or denominator
        != {
            "cluster_count": 100,
            "arm_run_count": 300,
            "ticks_per_arm": 64,
            "planned_tick_slots": 19_200,
            "formal_model_calls": 19_200,
            "start_from_zero": True,
            "old_partial_reuse": False,
            "sequential_calls": 0,
        }
        or runtime.get("dryrun_candidate_count") != 252
        or runtime.get("ticks_per_candidate") != 64
        or runtime.get("dryrun_receipt_count") != 16_128
        or runtime.get("family_raw_signal_is_formal_authority") is not False
        or runtime.get("no_signal")
        != {
            "phase": "none",
            "mapped_source_required": False,
            "phase_authority_mode": None,
            "regulatory_light_bulb_stopline_future_counts": 0,
        }
        or row.get("exact_dirs")
        != literal_exact_dirs(
            authority["implementation_head"],
            authority["replacement_continuation_sha256"],
        )
        or row.get("unchanged_scientific_contract", {}).get("weighted_total")
        is not False
        or row.get("unchanged_scientific_contract", {}).get("claim_authorized")
        is not False
    ):
        raise ValueError("independent replacement contract semantics drifted")
    return {**row, "contract_sha256": digest}


def _route_record(source_record: Mapping[str, Any]) -> dict[str, Any]:
    record = source_record
    route = record["route"]
    geometry = source_record["route"]["geometry"]
    headings = geometry["segment_headings_rad"]
    return {
        "record_key": f"project_source:{int(record['ordinal']):03d}",
        "map_family_id": "project_authored_multiroute_source_v1",
        "identity_sha256": route["route_lanelet_arc_sha256"],
        "route_serialization_sha256": route["route_lanelet_arc_sha256"],
        "source_map_path": record["map"]["relative_path"],
        "source_map_sha256": record["map"]["sha256"],
        "route_spec": {
            "ordered_lanelet_ids": [
                3_000_000 + int(record["ordinal"]) * 1_000 + 401 + index
                for index in range(4)
            ],
            "centerline_points_m": geometry["centerline_points_m"],
            "goal_tolerance_m": 2.0,
            "goal_pass_window_m": 5.0,
        },
        "source_stratum": {
            "traffic_light": (
                record["cell"]["source_availability"] == "mapped_signal"
            ),
            "branch_intersection": record["cell"]["route_bin"]
            != "heading_change_abs_le_0_15rad",
        },
        "centerline_samples_m": geometry["centerline_points_m"],
        "centerline_headings_rad": headings,
        "source_route_length_m": float(
            sum(float(value) for value in geometry["segment_lengths_m"])
        ),
    }


def _literal_case(source_record: Mapping[str, Any]) -> dict[str, Any]:
    rebuilt = build_source_record(int(source_record["ordinal"]))
    validate_source_record(source_record, rebuilt["map_bytes"])
    if rebuilt["record"] != dict(source_record):
        raise ValueError("reviewer deterministic source mismatch")
    case = build_controlled_scenario_case(
        route=_route_record(source_record),
        corridor_group_sha256=_sha(
            {
                "namespace": SOURCE_NAMESPACE,
                "geometry_sha256": source_record["route"]["geometry_sha256"],
            }
        ),
        split="project_authored_development_nonholdout",
        family=source_record["cell"]["family"],
        tier=source_record["cell"]["risk_tier"],
        variant=int(source_record["ordinal"]),
        seeds=(int(source_record["seeds"]["scenario"]),),
    )
    semantic = source_record["semantic_block"]
    if (
        case["parameters"] != semantic["controlled_scenario_parameters"]
        or case["actors"] != semantic["actors"]
        or case["signal"] != semantic["signal_semantics"]
    ):
        raise ValueError("reviewer raw family semantics mismatch")
    source_class = source_record["cell"]["source_availability"]
    if source_class == "no_signal":
        case["signal"] = {"phase": "none", "mapped_source_required": False}
        case["phase_authority_mode"] = None
    elif source_class == "mapped_signal":
        phase = str(case["signal"]["phase"])
        case["signal"] = {
            "phase": "green" if phase == "none" else phase,
            "mapped_source_required": True,
        }
        case["phase_authority_mode"] = "controlled_same_tick_override"
    else:
        raise ValueError("reviewer source availability unknown")
    case["signal_source_class"] = source_class
    validate_controlled_scenario_case(case)
    return case


def _point_polyline_distance(point: np.ndarray, line: np.ndarray) -> float:
    best = math.inf
    for start, end in zip(line[:-1], line[1:], strict=True):
        delta = end - start
        ratio = float(
            np.clip(np.dot(point - start, delta) / np.dot(delta, delta), 0.0, 1.0)
        )
        best = min(best, float(np.linalg.norm(point - (start + ratio * delta))))
    return best


def _literal_chain(
    source_record: Mapping[str, Any], case: Mapping[str, Any]
) -> dict[str, Any]:
    ordinal = int(source_record["ordinal"])
    base = 3_000_000 + ordinal * 1_000
    route_world = np.asarray(
        source_record["route"]["geometry"]["centerline_points_m"],
        dtype=np.float64,
    )
    route_ids = [base + 401 + index for index in range(4)]
    if source_record["cell"]["source_availability"] == "mapped_signal":
        stop_center = route_world[0] + 0.82 * (route_world[1] - route_world[0])
        half = 0.54 * float(source_record["route"]["geometry"]["lane_width_m"])
        stop = np.asarray(
            [
                stop_center + np.asarray([0.0, half]),
                stop_center - np.asarray([0.0, half]),
            ],
            dtype=np.float64,
        )
        semantic = build_semantic_clone_payload(
            case, route_polyline_world=route_world, stop_line_world=stop
        )
        tangent = route_world[1] - route_world[0]
        tangent = tangent / np.linalg.norm(tangent)
        body = {
            "schema_version": MAPPED_SIGNAL_CHAIN_SCHEMA_VERSION,
            "scenario_id": case["scenario_id"],
            "route_identity_sha256": source_record["route"][
                "route_lanelet_arc_sha256"
            ],
            "source_map_sha256": source_record["map"]["sha256"],
            "phase_authority_mode": "controlled_same_tick_override",
            "expected_current_phase": case["signal"]["phase"],
            "formal_phase": case["signal"]["phase"],
            "formal_mapped_source_required": True,
            "formal_route_mapped_traffic_light": True,
            "phase_remaining_available": False,
            "regulatory_element_ids": [base + 301],
            "physical_light_ids": [base + 202],
            "bulb_ids": [base + 203],
            "controlled_lanelet_ids": [base + 401],
            "route_lanelet_ids": route_ids,
            "route_geometry_sha256": canonical_json_sha256(
                {
                    "route_polyline_local_m": semantic["route_polyline_local_m"],
                    "stop_line_local_m": semantic["stop_line_local_m"],
                }
            ),
            "stop_line_id": base + 201,
            "stop_line_geometry_m": stop.tolist(),
            "stop_line_geometry_sha256": canonical_json_sha256(stop.tolist()),
            "stop_line_route_distance_m": _point_polyline_distance(
                stop.mean(axis=0), route_world
            ),
            "route_arc_m": 0.82
            * float(source_record["route"]["geometry"]["segment_lengths_m"][0]),
            "route_length_m": float(
                sum(
                    float(value)
                    for value in source_record["route"]["geometry"][
                        "segment_lengths_m"
                    ]
                )
            ),
            "route_tangent_world": tangent.tolist(),
            "semantic_clone_payload": semantic,
            "semantic_clone_sha256": canonical_json_sha256(semantic),
        }
        return validate_mapped_signal_chain(
            {**body, "source_chain_sha256": canonical_json_sha256(body)}
        )
    semantic = build_semantic_clone_payload(
        case, route_polyline_world=route_world, stop_line_world=None
    )
    body = {
        "schema_version": NO_SIGNAL_CHAIN_SCHEMA_VERSION,
        "scenario_id": case["scenario_id"],
        "route_identity_sha256": source_record["route"][
            "route_lanelet_arc_sha256"
        ],
        "source_map_sha256": source_record["map"]["sha256"],
        "route_lanelet_ids": route_ids,
        "route_geometry_sha256": canonical_json_sha256(
            {"route_polyline_local_m": semantic["route_polyline_local_m"]}
        ),
        "traffic_light_regulatory_element_ids": [],
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": canonical_json_sha256(semantic),
    }
    return validate_no_signal_chain(
        {**body, "source_chain_sha256": canonical_json_sha256(body)}
    )


def literal_semantic_receipt(
    source_record: Mapping[str, Any], tick_index: int
) -> dict[str, Any]:
    if not 0 <= tick_index < 64:
        raise ValueError("reviewer tick out of range")
    case = _literal_case(source_record)
    chain = _literal_chain(source_record, case)
    source_class = source_record["cell"]["source_availability"]
    if source_class == "mapped_signal":
        counts = {
            "regulatory": len(chain["regulatory_element_ids"]),
            "physical_light": len(chain["physical_light_ids"]),
            "bulb": len(chain["bulb_ids"]),
            "stopline": int(chain.get("stop_line_id") is not None),
        }
        phase = chain["formal_phase"]
        mapped = True
        same_tick = True
    else:
        counts = {
            "regulatory": len(chain["traffic_light_regulatory_element_ids"]),
            "physical_light": 0,
            "bulb": 0,
            "stopline": 0,
        }
        phase = chain["semantic_clone_payload"]["signal"]["current_phase"]
        mapped = chain["semantic_clone_payload"]["signal"][
            "mapped_source_required"
        ]
        same_tick = False
    payload = {
        "schema_version": (
            "camp_dp_v25_multiroute_v2_replacement_semantic_runtime_receipt_v1"
        ),
        "authority_sha256": EXPECTED_AUTHORITY,
        "ordinal": int(source_record["ordinal"]),
        "tick_index": tick_index,
        "cell": deepcopy(dict(source_record["cell"])),
        "source_record_sha256": source_record["source_record_sha256"],
        "map_sha256": source_record["map"]["sha256"],
        "route_sha256": source_record["route"]["route_lanelet_arc_sha256"],
        "semantic_block_sha256": source_record["semantic_block_sha256"],
        "source_availability_receipt_sha256": source_record[
            "source_availability_receipt_sha256"
        ],
        "source_availability": source_class,
        "formal_phase": phase,
        "formal_mapped_source_required": mapped,
        "phase_authority_mode": case["phase_authority_mode"],
        "same_tick_phase_authority": same_tick,
        "future_phase_consumed": False,
        "future_schedule_consumed": False,
        "formal_signal_object_counts": counts,
        "runtime_semantic_payload": chain["semantic_clone_payload"],
        "runtime_semantic_payload_sha256": chain["semantic_clone_sha256"],
        "source_chain_sha256": chain["source_chain_sha256"],
        "industrial_red_leaf_applicability": (
            "computed_from_same_tick_certified_source"
            if source_class == "mapped_signal"
            else "typed_evidence_missing_or_scientifically_inapplicable"
        ),
    }
    payload["receipt_sha256"] = _sha(payload)
    return payload
