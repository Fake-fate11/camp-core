"""V25 industrial-v3 project-authored multiroute continuation contract.

This module contains only outcome-independent contract, manifest, latent, and
runtime-source construction.  Model execution lives in the versioned producer
script and is permitted only after the sealed source continuation and this
contract's independent review pass.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (
    V25ControlledSceneAdapter,
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


SCHEMA_VERSION = "camp_dp_v25_industrial_v3_multiroute_v2_contract_v1"
AUTHORITY_SHA256 = (
    "9315b09b33f80856e1bbdcf957f92542ccaeb495b4b00497231ef038909a20cb"
)
PARENT_B5CA_AUTHORITY_SHA256 = (
    "b5ca942b4a91c0ef0cbe4e9ff8180852fb193471fb9f73514f6017622547718f"
)
CONTINUATION_SHA256 = (
    "89e716d0fd13acea517853f93a67b1ab68abe312ae4815f2a4b8c678c0ec3a13"
)
SOURCE_CONTRACT_ROOT_SHA256 = (
    "18eba22f050151bd74e21908352be118714447d535a56621d8d36a700467e505"
)
SOURCE_CONTRACT_REVIEW_ROOT_SHA256 = (
    "6e81bfca7dc895db54762ed553364bf897ebca3526bed33e72565f3491073326"
)
SOURCE_MATERIALIZATION_ROOT_SHA256 = (
    "ebbc7140e65fb2d2baf2aed8fa1a990e3c47b8b8ed3f6f4583ae0e2121be065a"
)
SOURCE_MATERIALIZATION_REVIEW_ROOT_SHA256 = (
    "15f574596d21eaeec272ec181b744d3b508db02f431325cb198f26217927e9a3"
)
SOURCE_SELECTED_MANIFEST_SHA256 = (
    "b779319aa0d32847a13c7522edeffc35ac03a044483c176d699b60a97cb9c40c"
)
CONTINUATION_ROOT_SHA256 = (
    "98a616130190984c5d35f2255a902c4572f6111d40fd072d44fec3cdc5f3a0ce"
)
CONTINUATION_REVIEW_ROOT_SHA256 = (
    "1b99843ef25d76780010c7483fcef14e760dbcbedfe5d7debad05b24ef7520ea"
)
BASE_HEAD = "af33d4e6588b885311fc3b5b4f30fc3fed2ee891"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
INDUSTRIAL_CONTRACT_ROOT_SHA256 = (
    "908fe1d57014e4932f71462d6d7e73ec58390f3296b3018df38092e4c0b128cb"
)
INDUSTRIAL_CONTRACT_REVIEW_ROOT_SHA256 = (
    "23bb07ac537f9d53f7a2860b2314f55da4e2d468590d002c6cf25733f5e48556"
)
INDUSTRIAL_CAPABILITY_ROOT_SHA256 = (
    "fbcc8ab194520534c3b4986cccaf3d9a073b2cf975b6e3f006f61abe7791f20d"
)
INDUSTRIAL_CAPABILITY_REVIEW_ROOT_SHA256 = (
    "f32cb19b2c7bbd64e290f07a270f3e43462d31c86dc130a0c23a8b6eb363eec3"
)
GENERATOR_RAW_ROOT_SHA256 = (
    "731a715a0422f92e115bc078900d84c47b9f51f47c64181c3b8e71569cffdda4"
)
GENERATOR_RAW_REVIEW_ROOT_SHA256 = (
    "c0e24bb60a4eb9694bfda099d4d6d9b9be07f85fb486577275f0b32178cfbfc8"
)
GENERATOR_THRESHOLD_ROOT_SHA256 = (
    "a4f6c54cb46378119b261fe0ef19f83f8b92d18fa3be3e02693f7905f3f8ac89"
)
GENERATOR_THRESHOLD_REVIEW_ROOT_SHA256 = (
    "8882f0fa66d1690460662848fa67673657926cc663b0edf476866e1418034e0e"
)
SELECTOR_REPLAY_ROOT_SHA256 = (
    "9e89135981ace29e86ec6b0b270d17aad4ac089d8fbdec10d98a0aa14c3a0982"
)
SELECTOR_REPLAY_REVIEW_ROOT_SHA256 = (
    "3d2ac16d055f9957941d0d84b0b47282413a41559e47e67ce9a644ae8e3bc80b"
)
TRAINING_ROOT_SHA256 = (
    "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
)
TRAINING_REVIEW_ROOT_SHA256 = (
    "ef2e9748a9ba0fff5b35f010cba6efd1b16d8e1dc0d562f5a7960c8dcb3d9be9"
)
ATOM_SCALES_SHA256 = (
    "72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb"
)

ARMS = ("pool_matched_candidate0", "Static14D", "Scene14D")
CLUSTER_COUNT = 100
TICKS_PER_ARM = 64
PLANNED_ARMS = CLUSTER_COUNT * len(ARMS)
PLANNED_TICKS = PLANNED_ARMS * TICKS_PER_ARM
PLANNED_MODEL_CALLS = PLANNED_TICKS
SIMPLEX_NONNEGATIVE_ATOL = 1e-9
MIN_FREE_AFTER_BYTES = 10 * 1024**3
MIN_FREE_INODES_AFTER = 100_000
LATENT_SHAPE = (8, 321, 81, 4)
LATENT_DTYPE = np.dtype("<f4")

EXACT_PREFIX = (
    "/root/autodl-tmp/"
    "camp_dp_v25_industrial_v3_multiroute_v2_af33d4e6_89e716d0_"
)
EXACT_DIRS = {
    "contract": EXACT_PREFIX + "contract",
    "contract_review": EXACT_PREFIX + "contract_review",
    "hardening_matrix": EXACT_PREFIX + "hardening_matrix",
    "hardening_matrix_review": EXACT_PREFIX + "hardening_matrix_review",
    "hardening_focused": EXACT_PREFIX + "hardening_focused",
    "preflight": EXACT_PREFIX + "preflight",
    "preflight_review": EXACT_PREFIX + "preflight_review",
    "execution": EXACT_PREFIX + "execution",
    "execution_review": EXACT_PREFIX + "execution_review",
    "evaluation": EXACT_PREFIX + "evaluation",
    "evaluation_review": EXACT_PREFIX + "evaluation_review",
    "final_docs": EXACT_PREFIX + "final_docs",
}

LATENCY_NAMESPACES = (
    "pool_generation",
    "atoms",
    "context",
    "weights",
    "selector_pure_incremental",
    "end_to_end",
)
CAPTURE_CLASSES = (
    "runner_capture_direct",
    "runner_capture_plus_frozen_transform",
    "route_inapplicable",
    "receipt_field_gap_fixable_before_model",
    "transform_ambiguity",
    "permanent_evidence_missing",
)


def canonical_bytes(value: Any) -> bytes:
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


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{label} must be lowercase SHA256")
    return value


def contract() -> dict[str, Any]:
    value = {
        "schema_version": SCHEMA_VERSION,
        "authority": {
            "source_authority_sha256": AUTHORITY_SHA256,
            "parent_b5ca_authority_sha256": PARENT_B5CA_AUTHORITY_SHA256,
            "continuation_sha256": CONTINUATION_SHA256,
            "base_head": BASE_HEAD,
            "fixed_dp_head": FIXED_DP_HEAD,
        },
        "source_chain": {
            "contract_root_sha256": SOURCE_CONTRACT_ROOT_SHA256,
            "contract_review_root_sha256": SOURCE_CONTRACT_REVIEW_ROOT_SHA256,
            "materialization_root_sha256": SOURCE_MATERIALIZATION_ROOT_SHA256,
            "materialization_review_root_sha256": (
                SOURCE_MATERIALIZATION_REVIEW_ROOT_SHA256
            ),
            "selected_manifest_sha256": SOURCE_SELECTED_MANIFEST_SHA256,
            "continuation_root_sha256": CONTINUATION_ROOT_SHA256,
            "continuation_review_root_sha256": CONTINUATION_REVIEW_ROOT_SHA256,
            "candidate_count": 252,
            "selected_cluster_count": CLUSTER_COUNT,
            "model_pool_selector_outcome_calls": 0,
        },
        "accepted_upstream_roots": {
            "industrial_contract": INDUSTRIAL_CONTRACT_ROOT_SHA256,
            "industrial_contract_review": INDUSTRIAL_CONTRACT_REVIEW_ROOT_SHA256,
            "industrial_capability": INDUSTRIAL_CAPABILITY_ROOT_SHA256,
            "industrial_capability_review": INDUSTRIAL_CAPABILITY_REVIEW_ROOT_SHA256,
            "generator_raw": GENERATOR_RAW_ROOT_SHA256,
            "generator_raw_review": GENERATOR_RAW_REVIEW_ROOT_SHA256,
            "generator_threshold": GENERATOR_THRESHOLD_ROOT_SHA256,
            "generator_threshold_review": GENERATOR_THRESHOLD_REVIEW_ROOT_SHA256,
            "selector_replay": SELECTOR_REPLAY_ROOT_SHA256,
            "selector_replay_review": SELECTOR_REPLAY_REVIEW_ROOT_SHA256,
            "training": TRAINING_ROOT_SHA256,
            "training_review": TRAINING_REVIEW_ROOT_SHA256,
            "atom_scales_sha256": ATOM_SCALES_SHA256,
        },
        "denominator": {
            "independent_cluster_count": CLUSTER_COUNT,
            "paired_units": CLUSTER_COUNT,
            "arms": list(ARMS),
            "planned_arm_runs": PLANNED_ARMS,
            "ticks_per_arm": TICKS_PER_ARM,
            "planned_tick_slots": PLANNED_TICKS,
            "planned_formal_model_calls": PLANNED_MODEL_CALLS,
            "complete_plus_failed_plus_unattempted_equals": PLANNED_TICKS,
            "drop_replace_complete_case": False,
        },
        "generator": {
            "name": "new_single_invocation_batched_k8_candidate_pool",
            "same_ego_expanded_batch_size": 8,
            "agent_as_ego_batch": False,
            "formal_model_calls_per_attempted_tick": 1,
            "sequential_calls": 0,
            "latent_shape": list(LATENT_SHAPE),
            "latent_dtype": "<f4",
            "latent_seed_preimage": (
                "sha256(parent_b5ca_authority_sha256|cluster_clone_key_sha256|"
                "tick_ordinal), PCG64DXSM"
            ),
            "latent_arm_or_forward_or_time_inputs": False,
            "row0_zero_rows1_7_unique": True,
            "candidate_shape": [8, 80, 4],
            "neighbor_shape": [8, 32, 80, 4],
            "candidate0_rule": "same_arm_same_tick_immutable_pool_row0",
            "post_pool_model_dp_latent_generation_calls": 0,
        },
        "runtime_source_transform": {
            "controlled_scenario_rebuilt_from_sealed_source_record": True,
            "mapped_signal_non_red_family_same_tick_phase": "green",
            "mapped_signal_non_red_phase_reason": (
                "outcome_independent_nonrestrictive_current_phase_for_a_route_with_"
                "certified_mapped_signal_authority"
            ),
            "red_light_family_phase": "sealed_controlled_scenario_tier_phase",
            "no_signal_phase": "none",
            "future_phase_or_phase_remaining_consumed": False,
            "actors_applied_before_tensor_conversion": True,
            "signal_applied_before_tensor_conversion": True,
            "certified_signal_safety_capture_required": True,
        },
        "selector": {
            "production_paths": ["candidate0", "Static14D", "Scene14D_no_V2I"],
            "same_arm_same_tick_tensor": True,
            "simplex_nonnegative_atol": SIMPLEX_NONNEGATIVE_ATOL,
            "candidate_tensor_immutable": True,
            "tie_break": "lowest_eligible_index",
            "training_or_weight_change": False,
        },
        "capture": {
            "parent_endpoint_count": 56,
            "scalar_leaf_count": 161,
            "allowed_classes": list(CAPTURE_CLASSES),
            "accepted_reconstructable_baseline": 119,
            "baseline_evidence_missing": 41,
            "baseline_scientifically_inapplicable": 1,
            "prior_single_route_computed": 100,
            "prior_single_route_missing": 57,
            "prior_single_route_inapplicable": 4,
            "all_161_mapped_before_first_model_call": True,
            "legacy_safetycost_role": (
                "immutable_legacy_exploratory_diagnostic_only_not_computed"
            ),
            "weighted_total": False,
        },
        "statistics": {
            "independent_unit": "prespecified_route_corridor_semantic_cluster",
            "independent_n": CLUSTER_COUNT,
            "cluster_first": True,
            "candidate0_reference": True,
            "arms_compared": ["Static14D", "Scene14D"],
            "direction_oriented_paired_delta": True,
            "better_tie_worse_tie_rule": "exact_zero_float64_delta",
            "ordinary_paired_student_t_ci": {
                "level": 0.95,
                "sidedness": "two_sided",
                "descriptive_only": True,
            },
            "holm": "only_exact_v3_testable_family_with_margin_authority",
            "numeric_margin_authority": (
                "numeric_margin_not_authorized_until_future_preregistration"
            ),
            "missing_or_failure_family_policy": "fail_closed_not_evaluable",
            "ticks_arms_rows_as_independent_n": False,
            "claim_authorized": False,
        },
        "latency_namespaces": list(LATENCY_NAMESPACES),
        "capacity": {
            "class_projection": "ceil(single_route_payload*100*1.25)",
            "persistent": "sum(classes)+2GiB",
            "peak": "max(classes)",
            "reserve": "max(5GiB,ceil(peak*0.25))",
            "minimum_free_after_peak_and_persistent_bytes": MIN_FREE_AFTER_BYTES,
            "minimum_free_inodes_after_projection": MIN_FREE_INODES_AFTER,
        },
        "hardening": {
            "required_keyword_or_typed_config_for_all_production_callsites": True,
            "zero_model_pass_and_typed_failure_dry_run": True,
            "atomic_seal_and_independent_review_dry_run": True,
            "forbid_bare_python_or_python3": True,
            "local_interpreter": (
                "C:\\Users\\lenovo\\.cache\\codex-runtimes\\"
                "codex-primary-runtime\\dependencies\\python\\python.exe"
            ),
            "autodl_interpreter": "/root/autodl-tmp/dp312_venv/bin/python",
        },
        "exact_dirs": dict(EXACT_DIRS),
        "permissions": {
            "fresh_holdout_training_retraining": False,
            "old_outcome_read": False,
            "old_artifact_or_cas_write": False,
            "fixed_dp_checkpoint_weights_theta_atoms_scales_change": False,
            "claim_promotion_deployment": False,
        },
    }
    value["contract_sha256"] = canonical_sha256(value)
    return value


def validate_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    actual = deepcopy(dict(value))
    expected = contract()
    if actual != expected:
        raise ValueError("industrial multiroute-v2 contract semantic drifted")
    if actual["denominator"]["planned_tick_slots"] != 19_200:
        raise ValueError("industrial multiroute-v2 denominator drifted")
    if actual["generator"]["sequential_calls"] != 0:
        raise ValueError("sequential generator entered multiroute-v2")
    if actual["capture"]["weighted_total"] is not False:
        raise ValueError("weighted total entered multiroute-v2")
    return actual


def latent_seed(cluster_clone_key_sha256: str, tick_index: int) -> int:
    _sha(cluster_clone_key_sha256, "cluster clone key")
    if type(tick_index) is not int or not 0 <= tick_index < TICKS_PER_ARM:
        raise ValueError("multiroute latent tick is invalid")
    preimage = (
        f"{PARENT_B5CA_AUTHORITY_SHA256}|{cluster_clone_key_sha256}|"
        f"{tick_index}"
    ).encode("ascii")
    return int.from_bytes(hashlib.sha256(preimage).digest()[:8], "little")


def latent_tensor(cluster_clone_key_sha256: str, tick_index: int) -> np.ndarray:
    rng = np.random.Generator(
        np.random.PCG64DXSM(latent_seed(cluster_clone_key_sha256, tick_index))
    )
    value = np.zeros(LATENT_SHAPE, dtype=LATENT_DTYPE)
    value[1:] = rng.standard_normal(value[1:].shape).astype(LATENT_DTYPE)
    rows = [bytes_sha256(np.ascontiguousarray(row).tobytes()) for row in value]
    if (
        len(set(rows)) != 8
        or not np.array_equal(value[0], np.zeros(LATENT_SHAPE[1:], dtype=LATENT_DTYPE))
        or not np.isfinite(value).all()
    ):
        raise RuntimeError("multiroute latent policy failed")
    return value


def latent_receipt(cluster_clone_key_sha256: str, tick_index: int) -> dict[str, Any]:
    value = latent_tensor(cluster_clone_key_sha256, tick_index)
    rows = [bytes_sha256(np.ascontiguousarray(row).tobytes()) for row in value]
    return {
        "tick_index": tick_index,
        "seed": latent_seed(cluster_clone_key_sha256, tick_index),
        "shape": list(value.shape),
        "dtype": value.dtype.str,
        "tensor_sha256": bytes_sha256(value.tobytes()),
        "row_sha256": rows,
        "unique_row_sha256_cardinality": len(set(rows)),
    }


def _route_record(source_record: Mapping[str, Any]) -> dict[str, Any]:
    record = source_record
    route = record["route"]
    geometry = route["geometry"]
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
            sum(float(item) for item in geometry["segment_lengths_m"])
        ),
    }


def reconstruct_controlled_case(source_record: Mapping[str, Any]) -> dict[str, Any]:
    ordinal = int(source_record["ordinal"])
    rebuilt = build_source_record(ordinal)
    validate_source_record(source_record, rebuilt["map_bytes"])
    if rebuilt["record"] != dict(source_record):
        raise ValueError("sealed source record differs from deterministic source")
    route = _route_record(source_record)
    case = build_controlled_scenario_case(
        route=route,
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
    case["signal_source_class"] = source_class
    case["phase_authority_mode"] = (
        "controlled_same_tick_override" if source_class == "mapped_signal" else None
    )
    if source_class == "mapped_signal" and case["signal"]["phase"] == "none":
        case["signal"] = {
            "phase": "green",
            "mapped_source_required": True,
        }
        case["runtime_nonrestrictive_phase_transform"] = (
            "mapped_non_red_family_same_tick_green_v1"
        )
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
                    float(item)
                    for item in source_record["route"]["geometry"][
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


def validate_selected_manifest(
    selected_manifest: Mapping[str, Any],
    source_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if (
        selected_manifest.get("schema_version")
        != "camp_dp_v25_project_authored_multiroute_selected_manifest_v1"
        or selected_manifest.get("selected_count") != CLUSTER_COUNT
        or selected_manifest.get("manifest_sha256")
        != SOURCE_SELECTED_MANIFEST_SHA256
    ):
        raise ValueError("selected source manifest authority drifted")
    by_ordinal = {int(row["ordinal"]): dict(row) for row in source_records}
    selected = selected_manifest.get("entries")
    if type(selected) is not list or len(selected) != CLUSTER_COUNT:
        raise ValueError("selected source manifest denominator drifted")
    records = []
    for position, candidate in enumerate(selected):
        ordinal = int(
            candidate["source_binding"]["inventory_entry_path"].rsplit("/", 1)[-1]
        )
        if ordinal not in by_ordinal:
            raise ValueError("selected source ordinal is absent")
        record = by_ordinal[ordinal]
        if (
            candidate["source_binding"]["inventory_entry_sha256"]
            != record["source_record_sha256"]
            or candidate["clone_key_sha256"]
            != canonical_sha256(candidate["clone_payload"])
        ):
            raise ValueError("selected source binding drifted")
        records.append(
            {
                "cluster_index": position,
                "candidate": deepcopy(candidate),
                "source_record": record,
            }
        )
    return records
