"""V25 multiroute-v2 no-signal consumer replacement contract.

This additive module preserves the original source materialization and makes
the formal runtime signal authority depend only on the sealed source
availability.  Raw family signal semantics remain source evidence; they are
not themselves a runtime signal authority.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

import numpy as np

from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (
    V25ControlledSceneAdapter,
    build_controlled_scenario_case,
    validate_controlled_scenario_case,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2 import (
    ARMS,
    ATOM_SCALES_SHA256,
    CAPTURE_CLASSES,
    CLUSTER_COUNT,
    FIXED_DP_HEAD,
    INDUSTRIAL_CAPABILITY_REVIEW_ROOT_SHA256,
    INDUSTRIAL_CAPABILITY_ROOT_SHA256,
    INDUSTRIAL_CONTRACT_REVIEW_ROOT_SHA256,
    INDUSTRIAL_CONTRACT_ROOT_SHA256,
    LATENCY_NAMESPACES,
    LATENT_DTYPE,
    LATENT_SHAPE,
    MIN_FREE_AFTER_BYTES,
    MIN_FREE_INODES_AFTER,
    PARENT_B5CA_AUTHORITY_SHA256,
    PLANNED_ARMS,
    PLANNED_MODEL_CALLS,
    PLANNED_TICKS,
    SIMPLEX_NONNEGATIVE_ATOL,
    SOURCE_CONTRACT_REVIEW_ROOT_SHA256,
    SOURCE_CONTRACT_ROOT_SHA256,
    SOURCE_MATERIALIZATION_REVIEW_ROOT_SHA256,
    SOURCE_MATERIALIZATION_ROOT_SHA256,
    SOURCE_SELECTED_MANIFEST_SHA256,
    TICKS_PER_ARM,
    TRAINING_REVIEW_ROOT_SHA256,
    TRAINING_ROOT_SHA256,
    _point_polyline_distance,
    bytes_sha256,
    canonical_bytes,
    canonical_sha256,
    latent_receipt,
    latent_tensor,
    validate_selected_manifest,
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


SCHEMA_VERSION = (
    "camp_dp_v25_industrial_v3_multiroute_v2_no_signal_consumer_replacement_v1"
)
AUTHORITY_SHA256 = (
    "c065e1b08e711a6cdeb84c14f94d5941019f613562ac452c028e8f903b537866"
)
PARENT_SOURCE_AUTHORITY_SHA256 = (
    "9315b09b33f80856e1bbdcf957f92542ccaeb495b4b00497231ef038909a20cb"
)
PARENT_CONTINUATION_SHA256 = (
    "89e716d0fd13acea517853f93a67b1ab68abe312ae4815f2a4b8c678c0ec3a13"
)
SOURCE_CONTINUATION_ROOT_SHA256 = (
    "98a616130190984c5d35f2255a902c4572f6111d40fd072d44fec3cdc5f3a0ce"
)
SOURCE_CONTINUATION_REVIEW_ROOT_SHA256 = (
    "1b99843ef25d76780010c7483fcef14e760dbcbedfe5d7debad05b24ef7520ea"
)
OLD_ATTEMPT_CLASSIFICATION = (
    "post_model_runtime_no_signal_semantic_authority_binding_failure_"
    "after_5_of_100_clusters"
)
OLD_ATTEMPT_CONTROL = (
    "/root/autodl-tmp/"
    ".camp_dp_v25_industrial_v3_multiroute_v2_9bef998d_89e716d0_"
    "execution_control"
)
OLD_ATTEMPT_LAUNCHER = (
    "/root/autodl-tmp/"
    ".camp_dp_v25_industrial_v3_multiroute_v2_9bef998d_89e716d0_"
    "execution_launcher"
)
OLD_ATTEMPT_STDERR_SHA256 = (
    "c6ad03d83a3a58bd6b7505bbd8338e58b3024d4575d412a850e203b1d516b7ae"
)
OLD_ATTEMPT_STDOUT_SHA256 = (
    "09d098f6e83a40b60fdab9d9eac49c1f991ea75e73e736a842b78ab5bcbed68c"
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


def replacement_exact_dirs(
    implementation_head: str, replacement_continuation_sha256: str
) -> dict[str, str]:
    if (
        len(implementation_head) != 40
        or len(replacement_continuation_sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in implementation_head + replacement_continuation_sha256
        )
    ):
        raise ValueError("replacement exact-dir authority is invalid")
    prefix = (
        "/root/autodl-tmp/"
        "camp_dp_v25_industrial_v3_multiroute_v2_replacement_"
        f"{implementation_head[:8]}_{replacement_continuation_sha256[:8]}_"
    )
    return {role: prefix + role for role in ROLE_NAMES}


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


def reconstruct_controlled_case(source_record: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild source semantics, then apply the formal availability transform."""

    ordinal = int(source_record["ordinal"])
    rebuilt = build_source_record(ordinal)
    validate_source_record(source_record, rebuilt["map_bytes"])
    if rebuilt["record"] != dict(source_record):
        raise ValueError("sealed source record differs from deterministic source")
    case = build_controlled_scenario_case(
        route=_route_record(source_record),
        corridor_group_sha256=canonical_sha256(
            {
                "namespace": SOURCE_NAMESPACE,
                "geometry_sha256": source_record["route"]["geometry_sha256"],
            }
        ),
        split="project_authored_development_nonholdout",
        family=source_record["cell"]["family"],
        tier=source_record["cell"]["risk_tier"],
        variant=ordinal,
        seeds=(int(source_record["seeds"]["scenario"]),),
    )
    semantic = source_record["semantic_block"]
    if (
        case["parameters"] != semantic["controlled_scenario_parameters"]
        or case["actors"] != semantic["actors"]
        or case["signal"] != semantic["signal_semantics"]
    ):
        raise ValueError("controlled scenario differs from sealed semantic block")
    source_class = source_record["cell"]["source_availability"]
    case["raw_family_runner_eligible"] = bool(case["runner_eligible"])
    if source_class == "no_signal":
        case["signal"] = {"phase": "none", "mapped_source_required": False}
        case["phase_authority_mode"] = None
        case["runner_eligible"] = True
        case["formal_runtime_execution_scope"] = (
            "execute_no_signal_source_case_with_red_leaves_typed_missing_v1"
        )
        case["runtime_signal_transform"] = (
            "source_availability_no_signal_forces_formal_none_v1"
        )
    elif source_class == "mapped_signal":
        raw_phase = str(case["signal"]["phase"])
        formal_phase = "green" if raw_phase == "none" else raw_phase
        if formal_phase not in {"green", "yellow", "red"}:
            raise ValueError("mapped source family phase is invalid")
        case["signal"] = {
            "phase": formal_phase,
            "mapped_source_required": True,
        }
        case["phase_authority_mode"] = "controlled_same_tick_override"
        case["formal_runtime_execution_scope"] = (
            "execute_mapped_same_tick_certified_source_case_v1"
        )
        case["runtime_signal_transform"] = (
            "source_availability_mapped_same_tick_phase_v1"
        )
    else:
        raise ValueError("source availability is unknown")
    case["signal_source_class"] = source_class
    validate_controlled_scenario_case(case)
    return case


def build_signal_authority(
    source_record: Mapping[str, Any], case: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    ordinal = int(source_record["ordinal"])
    base = 3_000_000 + ordinal * 1_000
    route_world = np.asarray(
        source_record["route"]["geometry"]["centerline_points_m"],
        dtype=np.float64,
    )
    route_ids = [base + 401 + index for index in range(4)]
    source_class = source_record["cell"]["source_availability"]
    if source_class == "mapped_signal":
        if (
            case["phase_authority_mode"] != "controlled_same_tick_override"
            or case["signal"]["mapped_source_required"] is not True
            or case["signal"]["phase"] not in {"green", "yellow", "red"}
        ):
            raise ValueError("mapped formal runtime semantics drifted")
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
            case,
            route_polyline_world=route_world,
            stop_line_world=stop,
        )
        tangent = route_world[1] - route_world[0]
        tangent = tangent / np.linalg.norm(tangent)
        without_hash = {
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
        chain = {
            **without_hash,
            "source_chain_sha256": canonical_json_sha256(without_hash),
        }
        return validate_mapped_signal_chain(chain), None
    if source_class != "no_signal":
        raise ValueError("source availability is unknown")
    if (
        case["phase_authority_mode"] is not None
        or case["signal"]
        != {"phase": "none", "mapped_source_required": False}
    ):
        raise ValueError("no-signal formal runtime semantics drifted")
    semantic = build_semantic_clone_payload(
        case,
        route_polyline_world=route_world,
        stop_line_world=None,
    )
    without_hash = {
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
    chain = {
        **without_hash,
        "source_chain_sha256": canonical_json_sha256(without_hash),
    }
    return None, validate_no_signal_chain(chain)


def build_scene_adapter(source_record: Mapping[str, Any]) -> V25ControlledSceneAdapter:
    case = reconstruct_controlled_case(source_record)
    mapped, no_signal = build_signal_authority(source_record, case)
    return V25ControlledSceneAdapter(
        case,
        mapped_signal_authority=mapped,
        no_signal_authority=no_signal,
    )


def semantic_runtime_receipt(
    source_record: Mapping[str, Any], tick_index: int
) -> dict[str, Any]:
    if not 0 <= tick_index < 64:
        raise ValueError("semantic dry-run tick is out of range")
    case = reconstruct_controlled_case(source_record)
    mapped, no_signal = build_signal_authority(source_record, case)
    source_class = source_record["cell"]["source_availability"]
    chain = mapped if mapped is not None else no_signal
    if chain is None:
        raise ValueError("formal source chain is absent")
    if source_class == "mapped_signal":
        counts = {
            "regulatory": len(chain["regulatory_element_ids"]),
            "physical_light": len(chain["physical_light_ids"]),
            "bulb": len(chain["bulb_ids"]),
            "stopline": int(chain.get("stop_line_id") is not None),
        }
        phase = chain["formal_phase"]
        mapped_required = chain["formal_mapped_source_required"]
        same_tick = True
    else:
        counts = {
            "regulatory": len(chain["traffic_light_regulatory_element_ids"]),
            "physical_light": 0,
            "bulb": 0,
            "stopline": 0,
        }
        phase = chain["semantic_clone_payload"]["signal"]["current_phase"]
        mapped_required = chain["semantic_clone_payload"]["signal"][
            "mapped_source_required"
        ]
        same_tick = False
    payload = {
        "schema_version": (
            "camp_dp_v25_multiroute_v2_replacement_semantic_runtime_receipt_v1"
        ),
        "authority_sha256": AUTHORITY_SHA256,
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
        "formal_mapped_source_required": mapped_required,
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
    payload["receipt_sha256"] = canonical_sha256(payload)
    return payload


def replacement_contract(
    *,
    implementation_head: str,
    replacement_continuation_sha256: str,
    replacement_continuation_root: str,
    replacement_continuation_review_root: str,
    old_attempt_closeout_root: str,
    old_attempt_closeout_review_root: str,
) -> dict[str, Any]:
    exact_dirs = replacement_exact_dirs(
        implementation_head, replacement_continuation_sha256
    )
    value = {
        "schema_version": SCHEMA_VERSION,
        "authority": {
            "high_authority_sha256": AUTHORITY_SHA256,
            "implementation_head": implementation_head,
            "fixed_dp_head": FIXED_DP_HEAD,
            "parent_source_authority_sha256": PARENT_SOURCE_AUTHORITY_SHA256,
            "parent_b5ca_authority_sha256": PARENT_B5CA_AUTHORITY_SHA256,
            "parent_continuation_sha256": PARENT_CONTINUATION_SHA256,
            "replacement_continuation_sha256": replacement_continuation_sha256,
            "replacement_continuation_root": replacement_continuation_root,
            "replacement_continuation_review_root": (
                replacement_continuation_review_root
            ),
            "source_roots": {
                "contract": SOURCE_CONTRACT_ROOT_SHA256,
                "contract_review": SOURCE_CONTRACT_REVIEW_ROOT_SHA256,
                "materialization": SOURCE_MATERIALIZATION_ROOT_SHA256,
                "materialization_review": SOURCE_MATERIALIZATION_REVIEW_ROOT_SHA256,
                "continuation": SOURCE_CONTINUATION_ROOT_SHA256,
                "continuation_review": SOURCE_CONTINUATION_REVIEW_ROOT_SHA256,
            },
            "selected_manifest_sha256": SOURCE_SELECTED_MANIFEST_SHA256,
        },
        "old_attempt": {
            "classification": OLD_ATTEMPT_CLASSIFICATION,
            "closeout_root": old_attempt_closeout_root,
            "closeout_review_root": old_attempt_closeout_review_root,
            "reuse": False,
            "outcome_values_read": False,
        },
        "formal_runtime_semantics": {
            "transform_order": (
                "deterministic_source_record_equality_then_"
                "source_availability_formal_transform"
            ),
            "family_raw_signal_is_formal_authority": False,
            "no_signal": {
                "phase": "none",
                "mapped_source_required": False,
                "phase_authority_mode": None,
                "regulatory_light_bulb_stopline_future_counts": 0,
                "formal_runner_eligible": True,
                "red_leaves": (
                    "typed_evidence_missing_or_scientifically_inapplicable"
                ),
            },
            "mapped_signal": {
                "phase_set": ["green", "yellow", "red"],
                "mapped_source_required": True,
                "phase_authority_mode": "controlled_same_tick_override",
                "future_phase_or_schedule_consumed": False,
            },
            "dryrun_candidate_count": 252,
            "ticks_per_candidate": 64,
            "dryrun_receipt_count": 16_128,
        },
        "replacement_denominator": {
            "cluster_count": CLUSTER_COUNT,
            "arm_run_count": PLANNED_ARMS,
            "ticks_per_arm": TICKS_PER_ARM,
            "planned_tick_slots": PLANNED_TICKS,
            "formal_model_calls": PLANNED_MODEL_CALLS,
            "start_from_zero": True,
            "old_partial_reuse": False,
            "sequential_calls": 0,
        },
        "unchanged_scientific_contract": {
            "arms": list(ARMS),
            "generator": "new_single_invocation_batched_k8_candidate_pool",
            "industrial_leaf_count": 161,
            "weighted_total": False,
            "safetycost_role": "immutable_legacy_exploratory_diagnostic_only",
            "claim_authorized": False,
        },
        "exact_dirs": exact_dirs,
        "forbidden": {
            "fresh_holdout_training_retraining": True,
            "old_outcome_or_effect_read": True,
            "old_artifact_or_cas_write": True,
            "model_dp_weights_atoms_scales_metric_claim_change": True,
            "second_replacement_after_first_model_call": True,
        },
    }
    value["contract_sha256"] = canonical_sha256(value)
    return value


def validate_replacement_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    row = deepcopy(dict(value))
    digest = row.pop("contract_sha256", None)
    if canonical_sha256(row) != digest:
        raise ValueError("replacement contract SHA drifted")
    authority = row["authority"]
    if (
        row["schema_version"] != SCHEMA_VERSION
        or authority["high_authority_sha256"] != AUTHORITY_SHA256
        or authority["fixed_dp_head"] != FIXED_DP_HEAD
        or authority["selected_manifest_sha256"]
        != SOURCE_SELECTED_MANIFEST_SHA256
        or row["formal_runtime_semantics"]["dryrun_receipt_count"] != 16_128
        or row["replacement_denominator"]
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
        or row["old_attempt"]["reuse"] is not False
        or row["unchanged_scientific_contract"]["weighted_total"] is not False
        or row["unchanged_scientific_contract"]["claim_authorized"] is not False
        or row["exact_dirs"]
        != replacement_exact_dirs(
            authority["implementation_head"],
            authority["replacement_continuation_sha256"],
        )
    ):
        raise ValueError("replacement contract semantics drifted")
    return {**row, "contract_sha256": digest}
