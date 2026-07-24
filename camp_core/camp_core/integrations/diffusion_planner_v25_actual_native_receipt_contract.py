from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "camp_dp_v25_actual_native_receipt_contract_v1"
NATIVE_RECEIPT_SCHEMA_VERSION = "v21_native_arm_receipt_v1"
BRANCHES = (
    "candidate0_primary",
    "candidate0_supplementary",
    "static14d",
    "scene14d",
)

_BASE_HEADER = frozenset(
    {
        "schema_version",
        "status",
        "route_name",
        "route_sha256",
        "logical_map_sha256",
        "fixed_dp_head",
        "checkpoint_sha256",
        "args_sha256",
        "arm",
        "scenario_seed",
        "spawn_config_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
        "ticks",
        "native_result",
        "safety",
        "secondary",
        "latency",
        "signal_safety",
        "runtime_annotation_compatibility",
        "claim_authorized",
        "actual_native_receipt_contract_sha256",
    }
)
_CAMP_HEADER = frozenset({*_BASE_HEADER, "selector_scale_contract"})

_COMMON_TICK = frozenset(
    {
        "tick_index",
        "status",
        "input_sha256",
        "padding",
        "tracker",
        "safety",
        "latency_ms",
        "pre_decision_speed_mps",
        "default_output_sha256",
        "planning_started_ns",
        "action_available_ns",
        "receipt_projected_ns",
    }
)
_CANDIDATE0_PRIMARY_TICK = frozenset(
    {
        *_COMMON_TICK,
        "candidate0_action_first",
        "selected_index",
        "selected_trajectory_sha256",
        "selection_policy",
        "score_contract",
        "eligibility_mask_name",
        "candidate0_operational_default",
        "candidate0_pool_evidence_collected_online",
        "candidate0_pool_evidence_required_post_action",
        "same_forward_claimed",
    }
)
_K8_COMMON_TICK = frozenset(
    {
        *_COMMON_TICK,
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "candidate_neighbor_sha256",
        "selected_trajectory_sha256",
        "global_rng_sha256_before",
        "global_rng_sha256_after",
        "candidate_row_sha256",
        "selection_policy",
        "score_contract",
        "eligibility_mask_name",
        "selected_index",
        "default_candidate0_identity",
        "causal_evidence_sha256",
        "route_lanes_sha256",
        "route_lanes_speed_limit_sha256",
        "route_lanes_has_speed_limit_sha256",
        "atom_matrix_sha256",
        "candidate0_operational_default",
        "npc_operational_outputs_unchanged",
        "physical_feasible_mask",
        "source_valid_mask",
        "source_complete_mask",
        "candidate_reasons",
        "all_k_high_risk",
        "controlled_scene",
    }
)
_CANDIDATE0_SUPPLEMENTARY_TICK = frozenset(
    {
        *_K8_COMMON_TICK,
        "post_divergence_cross_arm_tensor_identity_required",
    }
)
_STATIC_TICK = frozenset(
    {
        *_K8_COMMON_TICK,
        "normalized_atom_matrix_sha256",
        "scores",
        "tie_break_contract",
    }
    - {"candidate0_operational_default"}
)
_SCENE_TICK = frozenset({*_STATIC_TICK, "v25_context", "v25_scene_selector"})

HEADER_FIELDS_BY_BRANCH = {
    "candidate0_primary": _BASE_HEADER,
    "candidate0_supplementary": _BASE_HEADER,
    "static14d": _CAMP_HEADER,
    "scene14d": _CAMP_HEADER,
}
TICK_FIELDS_BY_BRANCH = {
    "candidate0_primary": _CANDIDATE0_PRIMARY_TICK,
    "candidate0_supplementary": _CANDIDATE0_SUPPLEMENTARY_TICK,
    "static14d": _STATIC_TICK,
    "scene14d": _SCENE_TICK,
}
LATENCY_FIELDS_BY_BRANCH = {
    "candidate0_primary": frozenset(
        {
            "input_materialization",
            "default_inference",
            "hook_total",
            "tracker",
            "total_planning",
        }
    ),
    "candidate0_supplementary": frozenset(
        {
            "input_materialization",
            "default_inference",
            "candidate_inference",
            "atom_materialization",
            "hook_total",
            "tracker",
            "total_planning",
        }
    ),
    "static14d": frozenset(
        {
            "input_materialization",
            "default_inference",
            "candidate_inference",
            "atom_materialization",
            "selector",
            "hook_total",
            "tracker",
            "total_planning",
        }
    ),
    "scene14d": frozenset(
        {
            "input_materialization",
            "default_inference",
            "candidate_inference",
            "atom_materialization",
            "context",
            "scene_weight",
            "selector",
            "hook_total",
            "tracker",
            "total_planning",
        }
    ),
}

_SHA_FIELDS = frozenset(
    {
        "input_sha256",
        "default_output_sha256",
        "selected_trajectory_sha256",
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "candidate_neighbor_sha256",
        "global_rng_sha256_before",
        "global_rng_sha256_after",
        "causal_evidence_sha256",
        "route_lanes_sha256",
        "route_lanes_speed_limit_sha256",
        "route_lanes_has_speed_limit_sha256",
        "atom_matrix_sha256",
        "normalized_atom_matrix_sha256",
    }
)
_BOOL_K8_FIELDS = frozenset(
    {"physical_feasible_mask", "source_valid_mask", "source_complete_mask"}
)
_TIMESTAMP_FIELDS = frozenset(
    {"planning_started_ns", "action_available_ns", "receipt_projected_ns"}
)
_SOURCE_STAGE = {
    "input_sha256": "pre_forward_causal_input_boundary",
    "default_output_sha256": "same_forward_default_output_boundary",
    "candidate_tensor_sha256_before": "post_forward_pre_selection_k8_boundary",
    "candidate_tensor_sha256_after": "post_selection_immutability_boundary",
    "candidate_row_sha256": "post_forward_pre_selection_k8_rows",
    "candidate_neighbor_sha256": "post_forward_candidate_neighbor_boundary",
    "atom_matrix_sha256": "post_forward_atom_materialization",
    "normalized_atom_matrix_sha256": "post_scale_pre_score_atom_materialization",
    "scores": "affine_score_boundary",
    "selected_index": "eligible_lowest_index_argmin_boundary",
    "selected_trajectory_sha256": "action_commit_boundary",
    "action_available_ns": "action_commit_boundary",
    "planning_started_ns": "planning_entry_boundary",
    "receipt_projected_ns": "post_action_receipt_projection_boundary",
    "latency_ms": "native_stage_timer_boundary",
    "controlled_scene": "same_tick_runtime_source_boundary",
    "v25_context": "scene_context_materialization_boundary",
    "v25_scene_selector": "scene_weight_materialization_boundary",
}

_CONTEXT_FEATURES = (
    "ego_speed_mps",
    "ego_longitudinal_acceleration_mps2",
    "ego_lateral_acceleration_mps2",
    "ego_yaw_rate_radps",
    "route_curvature_mean_abs_radpm",
    "route_curvature_max_abs_radpm",
    "route_lane_width_min_m",
    "route_lane_width_p50_m",
    "route_speed_limit_min_mps",
    "route_speed_limit_current_mps",
    "traffic_phase_red",
    "traffic_phase_yellow",
    "traffic_phase_green",
    "traffic_phase_unknown",
    "traffic_signal_distance_m",
    "traffic_signal_phase_remaining_s",
    "neighbor_count",
    "neighbor_min_distance_m",
    "neighbor_min_ttc_s",
    "neighbor_closing_speed_mps",
    "neighbor_lateral_gap_min_m",
    "candidate_consensus_rms_median_m",
    "candidate_consensus_rms_mad_m",
    "candidate_endpoint_xy_std_m",
    "candidate_progress_std_m",
    "candidate_source_valid_fraction",
)
_SAFETY_COMMON_FIELDS = frozenset(
    {
        "tick_index",
        "position_xy",
        "speed_mps",
        "ego_heading_rad",
        "route_heading_rad",
        "route_progress_m",
        "five_point_drivable_coverage",
        "min_obb_clearance_m",
        "red_light_at_interval_start",
        "front_center_prev_xy",
        "front_center_xy",
        "red_stop_lines",
        "speed_limit_mps",
        "constant_velocity_circle_ttc_diagnostic_s",
        "source_complete",
    }
)
_SAFETY_SIGNAL_FIELDS = frozenset(
    {
        "signal_phase_at_interval_start",
        "certified_signal_stop_lines",
        "pre_decision_speed_mps",
    }
)
_SAFETY_SIGNAL_PHASES = frozenset({"none", "green", "yellow", "red"})
_MAPPED_SIGNAL_PHASES = frozenset({"green", "yellow", "red"})
_CONTROLLED_SCENE_FIELDS = frozenset(
    {
        "scenario_id",
        "tick_index",
        "sim_time_s",
        "actor_count",
        "actors",
        "signal",
        "outcome_fields_consumed",
        "candidate_tensor_consumed",
        "selected_trajectory_consumed",
        "model_input_cache",
    }
)
_ACTOR_FIELDS = frozenset(
    {
        "id",
        "agent_type",
        "position_xy",
        "heading_rad",
        "velocity_xy_mps",
        "scripted_exogenous",
        "excluded_from_dp_control",
    }
)
_NO_SIGNAL_FIELDS = frozenset(
    {"phase", "source_row_count", "applied", "source_receipt"}
)
_MAPPED_SIGNAL_FIELDS = frozenset(
    {
        "phase",
        "source_row_count",
        "applied",
        "source_receipt",
        "tensor_evidence",
    }
)
_NO_SIGNAL_SOURCE_FIELDS = frozenset(
    {
        "schema_version",
        "scenario_id",
        "tick_index",
        "decision_time_s",
        "source_mode",
        "current_phase",
        "route_geometry_sha256",
        "route_lanelet_ids",
        "traffic_light_regulatory_element_ids",
        "source_chain_sha256",
        "semantic_clone_sha256",
        "phase_remaining_available",
        "source_valid",
        "applicable",
    }
)
_MAPPED_SIGNAL_SOURCE_FIELDS = frozenset(
    {
        "schema_version",
        "scenario_id",
        "tick_index",
        "phase_authority_mode",
        "current_phase",
        "decision_timestamp_s",
        "source_timestamp_s",
        "source_age_s",
        "freshness",
        "source_id",
        "regulatory_element_id",
        "physical_light_ids",
        "bulb_ids",
        "controlled_lanelet_ids",
        "stop_line_id",
        "stop_line_geometry_sha256",
        "route_geometry_sha256",
        "route_arc_m",
        "source_chain_sha256",
        "observed_route_lanelet_ids",
        "observed_map_lanelet_ids",
        "route_signal_tensor_sha256",
        "map_signal_tensor_sha256",
        "phase_remaining_available",
        "source_valid",
        "applicable",
    }
)
_TENSOR_EVIDENCE_FIELDS = frozenset(
    {
        "schema_version",
        "tick_index",
        "decision_timestamp_s",
        "source_timestamp_s",
        "route_signal_rows",
        "map_signal_rows",
        "current_phase",
        "route_signal_tensor_sha256",
        "map_signal_tensor_sha256",
        "future_schedule_consumed",
        "phase_remaining_available",
    }
)
_MODEL_INPUT_CACHE_FIELDS = frozenset(
    {
        "schema_version",
        "scenario_id",
        "tick_index",
        "signal_source_class",
        "phase_authority_mode",
        "scene_map_tl_sha256",
        "model_cache_tl_sha256_before",
        "model_cache_tl_sha256_after",
        "model_route_lanes_tl_sha256",
        "cache_matches_scene_after",
        "observe_cache_unchanged",
        "sync_applied_before_tensor_conversion",
        "future_schedule_consumed",
        "phase_remaining_available",
    }
)

_NESTED_SCHEMAS: dict[str, dict[str, Any]] = {
    "padding": {
        "kind": "exact_mapping",
        "fields": {
            "observed_frames": "native_nonnegative_int",
            "padded_frames": "native_nonnegative_int",
            "padding_policy": "nonempty_string",
        },
    },
    "tracker": {
        "kind": "exact_mapping",
        "fields": {"status": "nonempty_string"},
    },
    "default_candidate0_identity": {
        "kind": "exact_mapping",
        "fields": {
            "elementwise_equal": "native_bool",
            "max_abs_difference": "finite_float",
            "default_output_sha256": "sha256",
            "candidate0_sha256": "sha256",
            "native_ranked_k8": "native_bool",
        },
    },
    "v25_context": {
        "kind": "exact_mapping",
        "context_feature_names": list(_CONTEXT_FEATURES),
        "fields": {
            "raw_context": "finite_context_mapping",
            "schema_version": "nonempty_string",
            "source_complete": "bool_context_mapping",
            "source_receipt": "no_v2i_context_source_receipt",
        },
    },
    "v25_scene_selector": {
        "kind": "exact_mapping",
        "fields": {
            "context_scaler_sha256": "sha256",
            "fixed_dp_head": "git_sha",
            "model_name": "nonempty_string",
            "phi_sha256": "sha256",
            "runtime_projection": "native_bool",
            "schema_version": "nonempty_string",
            "softmax": "native_bool",
            "theta_sha256": "sha256",
            "training_review_root_sha256": "sha256",
            "training_root_sha256": "sha256",
            "weights_sha256": "sha256",
        },
    },
    "safety_record": {
        "kind": "certified_signal_exact_mapping",
        "common_fields": sorted(_SAFETY_COMMON_FIELDS),
        "signal_fields": sorted(_SAFETY_SIGNAL_FIELDS),
        "signal_phase_literals": sorted(_SAFETY_SIGNAL_PHASES),
    },
    "controlled_scene": {
        "kind": "discriminated_exact_mapping",
        "fields": sorted(_CONTROLLED_SCENE_FIELDS),
        "actor_fields": sorted(_ACTOR_FIELDS),
        "no_signal_fields": sorted(_NO_SIGNAL_FIELDS),
        "mapped_signal_fields": sorted(_MAPPED_SIGNAL_FIELDS),
        "no_signal_source_fields": sorted(_NO_SIGNAL_SOURCE_FIELDS),
        "mapped_signal_source_fields": sorted(_MAPPED_SIGNAL_SOURCE_FIELDS),
        "tensor_evidence_fields": sorted(_TENSOR_EVIDENCE_FIELDS),
        "signal_row_semantics": (
            "route_and_map_lists_may_individually_be_empty; combined rows must "
            "be nonempty, content-addressed, ID-bound, and encode one uniform "
            "current phase in finite Nx5 channel vectors"
        ),
        "model_input_cache_fields": sorted(_MODEL_INPUT_CACHE_FIELDS),
    },
}

_HEADER_TYPE_CONTRACT = {
    "schema_version": "nonempty_string",
    "status": "nonempty_string",
    "route_name": "nonempty_string",
    "route_sha256": "sha256",
    "logical_map_sha256": "sha256",
    "fixed_dp_head": "git_sha",
    "checkpoint_sha256": "sha256",
    "args_sha256": "sha256",
    "arm": "nonempty_string",
    "scenario_seed": "native_nonnegative_int",
    "spawn_config_sha256": "sha256",
    "initial_state_sha256": "sha256",
    "initial_input_sha256": "sha256",
    "ticks": "native_list",
    "native_result": "native_result",
    "safety": "mapping",
    "secondary": "mapping",
    "latency": "mapping",
    "signal_safety": "mapping",
    "runtime_annotation_compatibility": "nonempty_string",
    "claim_authorized": "native_bool",
    "actual_native_receipt_contract_sha256": "sha256",
    "selector_scale_contract": "mapping",
}

_TICK_TYPE_CONTRACT = {
    "tick_index": "native_nonnegative_int",
    "status": "nonempty_string",
    "input_sha256": "sha256",
    "padding": "nested:padding",
    "tracker": "nested:tracker",
    "safety": "nested:safety_record",
    "latency_ms": "finite_nonnegative_number_mapping",
    "pre_decision_speed_mps": "finite_float",
    "default_output_sha256": "sha256",
    "planning_started_ns": "native_nonnegative_int",
    "action_available_ns": "native_nonnegative_int",
    "receipt_projected_ns": "native_nonnegative_int",
    "candidate0_action_first": "native_bool",
    "selected_index": "native_nonnegative_int",
    "selected_trajectory_sha256": "sha256",
    "selection_policy": "nonempty_string",
    "score_contract": "nonempty_string",
    "eligibility_mask_name": "nonempty_string",
    "candidate0_operational_default": "native_bool",
    "candidate0_pool_evidence_collected_online": "native_bool",
    "candidate0_pool_evidence_required_post_action": "native_bool",
    "same_forward_claimed": "native_bool",
    "candidate_tensor_sha256_before": "sha256",
    "candidate_tensor_sha256_after": "sha256",
    "candidate_neighbor_sha256": "sha256",
    "global_rng_sha256_before": "sha256",
    "global_rng_sha256_after": "sha256",
    "candidate_row_sha256": "sha256_list:8",
    "default_candidate0_identity": "nested:default_candidate0_identity",
    "causal_evidence_sha256": "sha256",
    "route_lanes_sha256": "sha256",
    "route_lanes_speed_limit_sha256": "sha256",
    "route_lanes_has_speed_limit_sha256": "sha256",
    "atom_matrix_sha256": "sha256",
    "normalized_atom_matrix_sha256": "sha256",
    "post_divergence_cross_arm_tensor_identity_required": "native_bool",
    "npc_operational_outputs_unchanged": "native_bool",
    "physical_feasible_mask": "native_bool_list:8",
    "source_valid_mask": "native_bool_list:8",
    "source_complete_mask": "native_bool_list:8",
    "candidate_reasons": "string_matrix:8",
    "all_k_high_risk": "native_bool",
    "controlled_scene": "nested:controlled_scene",
    "scores": "finite_number_list:8",
    "tie_break_contract": "nonempty_string",
    "v25_context": "nested:v25_context",
    "v25_scene_selector": "nested:v25_scene_selector",
}


def actual_native_receipt_contract() -> dict[str, Any]:
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "frozen_actual_native_producer_projection_review_contract",
        "native_receipt_schema_version": NATIVE_RECEIPT_SCHEMA_VERSION,
        "branches": {
            branch: {
                "header": {
                    "required": sorted(HEADER_FIELDS_BY_BRANCH[branch]),
                    "optional": [],
                    "forbidden": sorted(
                        set().union(*HEADER_FIELDS_BY_BRANCH.values())
                        - HEADER_FIELDS_BY_BRANCH[branch]
                    ),
                },
                "tick": {
                    "required": sorted(TICK_FIELDS_BY_BRANCH[branch]),
                    "optional": [],
                    "forbidden": sorted(
                        set().union(*TICK_FIELDS_BY_BRANCH.values())
                        - TICK_FIELDS_BY_BRANCH[branch]
                    ),
                },
                "latency_fields": sorted(LATENCY_FIELDS_BY_BRANCH[branch]),
                "header_native_types": {
                    name: _HEADER_TYPE_CONTRACT[name]
                    for name in sorted(HEADER_FIELDS_BY_BRANCH[branch])
                },
                "tick_native_types": {
                    name: _TICK_TYPE_CONTRACT[name]
                    for name in sorted(TICK_FIELDS_BY_BRANCH[branch])
                },
                "tick_count": 64,
                "candidate_shape": [8, 80, 4],
                "mask_shape": [8],
                "field_source_stage": {
                    name: _SOURCE_STAGE.get(name, "native_public_receipt_projection")
                    for name in sorted(TICK_FIELDS_BY_BRANCH[branch])
                },
            }
            for branch in BRANCHES
        },
        "candidate0_primary_semantics": (
            "action_first_operational_default_without_online_k8_pool"
        ),
        "candidate0_supplementary_semantics": (
            "post_action_separate_actual_native_k8_pool_diagnostic"
        ),
        "literal_domains": {
            "header.status": ["ok"],
            "header.arm_by_branch": {
                "candidate0_primary": ["dp"],
                "candidate0_supplementary": ["dp"],
                "static14d": ["camp"],
                "scene14d": ["camp"],
            },
            "tick.status": ["ok"],
            "tick.safety.signal_phase_at_interval_start": sorted(
                _SAFETY_SIGNAL_PHASES
            ),
            "tick.controlled_scene.signal.phase": sorted(
                _SAFETY_SIGNAL_PHASES
            ),
            "tick.selection_policy_by_branch": {
                "candidate0_primary": ["candidate0_operational_default"],
                "candidate0_supplementary": [
                    "candidate0_operational_default"
                ],
                "static14d": ["v22_source_valid"],
                "scene14d": ["v22_source_valid"],
            },
            "tick.score_contract_by_branch": {
                "candidate0_primary": ["candidate0_operational_default"],
                "candidate0_supplementary": [
                    "candidate0_operational_default"
                ],
                "static14d": ["score_k=clip(a_k/s,0,10)^T w"],
                "scene14d": ["score_k=clip(a_k/s,0,10)^T w"],
            },
            "tick.eligibility_mask_name_by_branch": {
                "candidate0_primary": ["candidate0_operational_default"],
                "candidate0_supplementary": [
                    "candidate0_operational_default"
                ],
                "static14d": ["source_valid_mask"],
                "scene14d": ["source_valid_mask"],
            },
            "tick.tie_break_contract_by_branch": {
                "candidate0_primary": [],
                "candidate0_supplementary": [],
                "static14d": ["lowest_eligible_candidate_index"],
                "scene14d": ["lowest_eligible_candidate_index"],
            },
        },
        "cross_branch_relations": [
            (
                "candidate0 primary and supplementary bind identical route, "
                "map, fixed-DP, model asset, seed, spawn, initial-state, and "
                "initial-input authority"
            ),
            (
                "candidate0 supplementary planning begins no earlier than the "
                "primary action-available timestamp and cannot affect action, "
                "RNG, or the next tick"
            ),
            (
                "every K8 branch binds row0 to the same-forward default output "
                "and the selected row to the committed action"
            ),
            (
                "K8 safety signal phase equals the same-tick controlled-scene "
                "signal phase, including the explicit no-signal literal none"
            ),
            (
                "Static14D and Scene14D share fixed K8, atom, mask, affine "
                "selection, and tie contracts; only Scene14D carries context "
                "and scene-weight receipts"
            ),
        ],
        "default_or_none_backfill_allowed": False,
        "post_hoc_field_fabrication_allowed": False,
        "nested_schemas": _NESTED_SCHEMAS,
        "producer_and_projector_use_production_validator": True,
        "reviewer_reads_declaration_but_uses_independent_parser": True,
        "reviewer_imports_production_validator_or_projector": False,
        "fresh_outcome_fields_consumed": [],
    }
    result["contract_sha256"] = _canonical_sha(result)
    return result


def actual_native_receipt_contract_sha256() -> str:
    return actual_native_receipt_contract()["contract_sha256"]


def validate_actual_native_receipt(
    value: Mapping[str, Any],
    *,
    branch: str,
    expected_ticks: int = 64,
) -> dict[str, Any]:
    if branch not in BRANCHES:
        raise ValueError("actual-native receipt branch is invalid")
    if type(value) is not dict or set(value) != HEADER_FIELDS_BY_BRANCH[branch]:
        raise ValueError(f"{branch} actual-native header field set drifted")
    expected_arm = "dp" if branch.startswith("candidate0_") else "camp"
    if (
        value["schema_version"] != NATIVE_RECEIPT_SCHEMA_VERSION
        or value["status"] != "ok"
        or value["arm"] != expected_arm
        or value["claim_authorized"] is not False
        or type(value["route_name"]) is not str
        or not value["route_name"]
        or type(value["scenario_seed"]) is not int
        or type(value["ticks"]) is not list
        or len(value["ticks"]) != expected_ticks
        or value["actual_native_receipt_contract_sha256"]
        != actual_native_receipt_contract_sha256()
    ):
        raise ValueError(f"{branch} actual-native header value drifted")
    for name in (
        "route_sha256",
        "logical_map_sha256",
        "checkpoint_sha256",
        "args_sha256",
        "spawn_config_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
    ):
        if not _sha(value[name]):
            raise ValueError(f"{branch} actual-native header SHA drifted: {name}")
    if (
        type(value["fixed_dp_head"]) is not str
        or len(value["fixed_dp_head"]) != 40
        or set(value["fixed_dp_head"]) - set("0123456789abcdef")
    ):
        raise ValueError(f"{branch} actual-native fixed DP HEAD drifted")
    for name in ("native_result", "safety", "secondary", "latency", "signal_safety"):
        if type(value[name]) is not dict:
            raise ValueError(f"{branch} actual-native header type drifted: {name}")
    if (
        value["runtime_annotation_compatibility"]
        != "not_required_python310_or_newer"
    ):
        raise ValueError(
            f"{branch} runtime annotation compatibility drifted"
        )
    _validate_native_result(value["native_result"], branch=branch)
    if branch in {"static14d", "scene14d"} and type(
        value["selector_scale_contract"]
    ) is not dict:
        raise ValueError(f"{branch} selector scale contract drifted")
    result = dict(value)
    result["ticks"] = [
        validate_actual_native_tick(tick, branch=branch, tick_index=index)
        for index, tick in enumerate(value["ticks"])
    ]
    if result["ticks"][0]["input_sha256"] != result["initial_input_sha256"]:
        raise ValueError(f"{branch} initial input/tick0 binding drifted")
    return result


def validate_actual_native_tick(
    value: Mapping[str, Any], *, branch: str, tick_index: int
) -> dict[str, Any]:
    if branch not in BRANCHES:
        raise ValueError("actual-native tick branch is invalid")
    if type(value) is not dict or set(value) != TICK_FIELDS_BY_BRANCH[branch]:
        raise ValueError(f"{branch} actual-native tick field set drifted")
    if (
        type(value["tick_index"]) is not int
        or value["tick_index"] != tick_index
        or value["status"] != "ok"
        or type(value["pre_decision_speed_mps"]) is not float
        or not math.isfinite(value["pre_decision_speed_mps"])
    ):
        raise ValueError(f"{branch} actual-native tick scalar drifted")
    for name in _SHA_FIELDS & TICK_FIELDS_BY_BRANCH[branch]:
        if not _sha(value[name]):
            raise ValueError(f"{branch} actual-native tick SHA drifted: {name}")
    for name in _TIMESTAMP_FIELDS:
        if type(value[name]) is not int or value[name] < 0:
            raise ValueError(f"{branch} actual-native timestamp drifted: {name}")
    for name in ("padding", "tracker", "safety", "latency_ms"):
        if type(value[name]) is not dict:
            raise ValueError(f"{branch} actual-native nested type drifted: {name}")
    _validate_declared_nested(value["padding"], "padding")
    _validate_declared_nested(value["tracker"], "tracker")
    _validate_declared_nested(value["safety"], "safety_record")
    if set(value["latency_ms"]) != LATENCY_FIELDS_BY_BRANCH[branch] or any(
        type(item) not in {int, float}
        or type(item) is bool
        or not math.isfinite(float(item))
        or float(item) < 0.0
        for item in value["latency_ms"].values()
    ):
        raise ValueError(f"{branch} actual-native latency contract drifted")
    if branch == "candidate0_primary":
        if (
            value["candidate0_action_first"] is not True
            or value["candidate0_operational_default"] is not True
            or value["candidate0_pool_evidence_collected_online"] is not False
            or value["candidate0_pool_evidence_required_post_action"] is not True
            or value["same_forward_claimed"] is not False
            or value["selected_index"] != 0
            or value["selected_trajectory_sha256"] != value["default_output_sha256"]
            or value["selection_policy"] != "candidate0_operational_default"
            or value["score_contract"] != "candidate0_operational_default"
            or value["eligibility_mask_name"]
            != "candidate0_operational_default"
        ):
            raise ValueError("candidate0 primary action-first contract drifted")
        return dict(value)
    if value["candidate_tensor_sha256_before"] != value[
        "candidate_tensor_sha256_after"
    ]:
        raise ValueError(f"{branch} candidate tensor was modified")
    bool_names = [
        "npc_operational_outputs_unchanged",
        "all_k_high_risk",
    ]
    if branch == "candidate0_supplementary":
        bool_names.append(
            "post_divergence_cross_arm_tensor_identity_required"
        )
    for name in bool_names:
        if type(value[name]) is not bool:
            raise ValueError(f"{branch} native bool drifted: {name}")
    if branch == "candidate0_supplementary":
        if (
            value["candidate0_operational_default"] is not True
            or value["selection_policy"]
            != "candidate0_operational_default"
            or value["score_contract"] != "candidate0_operational_default"
            or value["eligibility_mask_name"]
            != "candidate0_operational_default"
        ):
            raise ValueError(
                "candidate0 supplementary selection contract drifted"
            )
    elif (
        value["selection_policy"] != "v22_source_valid"
        or value["score_contract"]
        != "score_k=clip(a_k/s,0,10)^T w"
        or value["eligibility_mask_name"] != "source_valid_mask"
    ):
        raise ValueError(f"{branch} CAMP selection contract drifted")
    rows = value["candidate_row_sha256"]
    selected = value["selected_index"]
    if (
        type(rows) is not list
        or len(rows) != 8
        or any(not _sha(item) for item in rows)
        or type(selected) is not int
        or not 0 <= selected < 8
        or rows[0] != value["default_output_sha256"]
        or rows[selected] != value["selected_trajectory_sha256"]
    ):
        raise ValueError(f"{branch} candidate row/selection contract drifted")
    for name in _BOOL_K8_FIELDS:
        raw = value[name]
        if type(raw) is not list or len(raw) != 8 or any(
            type(item) is not bool for item in raw
        ):
            raise ValueError(f"{branch} native bool[8] drifted: {name}")
    if any(
        physical and not source
        for physical, source in zip(
            value["physical_feasible_mask"],
            value["source_valid_mask"],
            strict=True,
        )
    ) or not any(value["source_valid_mask"]):
        raise ValueError(f"{branch} source/physical eligibility drifted")
    reasons = value["candidate_reasons"]
    if type(reasons) is not list or len(reasons) != 8 or any(
        type(row) is not list or any(type(item) is not str for item in row)
        for row in reasons
    ):
        raise ValueError(f"{branch} candidate reason shape drifted")
    for name in ("default_candidate0_identity", "controlled_scene"):
        if type(value[name]) is not dict:
            raise ValueError(f"{branch} nested receipt type drifted: {name}")
    _validate_declared_nested(
        value["default_candidate0_identity"], "default_candidate0_identity"
    )
    _validate_declared_nested(value["controlled_scene"], "controlled_scene")
    if (
        value["safety"]["signal_phase_at_interval_start"]
        != value["controlled_scene"]["signal"]["phase"]
    ):
        raise ValueError(f"{branch} safety/controlled-scene phase drifted")
    if branch in {"static14d", "scene14d"}:
        if (
            type(value["tie_break_contract"]) is not str
            or value["tie_break_contract"]
            != "lowest_eligible_candidate_index"
        ):
            raise ValueError(f"{branch} tie-break contract drifted")
        scores = value["scores"]
        if type(scores) is not list or len(scores) != 8 or any(
            type(item) not in {int, float}
            or type(item) is bool
            or not math.isfinite(float(item))
            for item in scores
        ):
            raise ValueError(f"{branch} score shape drifted")
    if branch == "scene14d" and (
        type(value["v25_context"]) is not dict
        or type(value["v25_scene_selector"]) is not dict
    ):
        raise ValueError("scene14d context/selector receipt drifted")
    if branch == "scene14d":
        _validate_declared_nested(value["v25_context"], "v25_context")
        if (
            value["v25_context"]["schema_version"]
            != "camp_dp_v25_causal_context_raw_v2"
        ):
            raise ValueError("scene14d context schema drifted")
        _validate_declared_nested(
            value["v25_scene_selector"], "v25_scene_selector"
        )
        selector = value["v25_scene_selector"]
        if (
            selector["schema_version"]
            != "camp_dp_v25_scene_weight_receipt_v3"
            or selector["model_name"] != "CAMP-Scene14D"
            or selector["runtime_projection"] is not False
            or selector["softmax"] is not False
        ):
            raise ValueError("scene14d selector receipt drifted")
    return dict(value)


def branch_for_native_receipt(
    value: Mapping[str, Any], *, expected_arm: str
) -> str:
    if expected_arm == "candidate0":
        ticks = value.get("ticks")
        if type(ticks) is not list or not ticks:
            raise ValueError("candidate0 native receipt ticks are missing")
        return (
            "candidate0_primary"
            if ticks[0].get("candidate0_action_first") is True
            else "candidate0_supplementary"
        )
    if expected_arm == "static14d":
        return "static14d"
    if expected_arm == "scene14d":
        return "scene14d"
    raise ValueError("native receipt arm is invalid")


def _sha(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and not (set(value) - set("0123456789abcdef"))
    )


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()


def _validate_declared_nested(value: Any, schema_name: str) -> None:
    schema = _NESTED_SCHEMAS[schema_name]
    if schema["kind"] == "certified_signal_exact_mapping":
        _validate_safety_record(value)
        return
    if schema["kind"] == "discriminated_exact_mapping":
        _validate_controlled_scene(value)
        return
    fields = schema["fields"]
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError(f"actual-native nested schema drifted: {schema_name}")
    for name, kind in fields.items():
        _validate_declared_kind(value[name], kind, f"{schema_name}.{name}")


def _validate_declared_kind(value: Any, kind: str, label: str) -> None:
    if kind == "native_nonnegative_int":
        valid = type(value) is int and value >= 0
    elif kind == "native_bool":
        valid = type(value) is bool
    elif kind == "nonempty_string":
        valid = type(value) is str and bool(value)
    elif kind == "sha256":
        valid = _sha(value)
    elif kind == "git_sha":
        valid = (
            type(value) is str
            and len(value) == 40
            and not (set(value) - set("0123456789abcdef"))
        )
    elif kind == "finite_float":
        valid = type(value) is float and math.isfinite(value)
    elif kind == "finite_number_list":
        valid = type(value) is list and all(
            type(item) in {int, float}
            and type(item) is not bool
            and math.isfinite(float(item))
            for item in value
        )
    elif kind == "native_bool_list":
        valid = type(value) is list and all(type(item) is bool for item in value)
    elif kind == "finite_context_mapping":
        valid = (
            type(value) is dict
            and set(value) == set(_CONTEXT_FEATURES)
            and all(
                type(item) is float and math.isfinite(item)
                for item in value.values()
            )
        )
    elif kind == "bool_context_mapping":
        valid = (
            type(value) is dict
            and set(value) == set(_CONTEXT_FEATURES)
            and all(type(item) is bool for item in value.values())
        )
    elif kind == "no_v2i_context_source_receipt":
        valid = (
            type(value) is dict
            and set(value)
            == {
                "mode",
                "phase_remaining_available",
                "regulatory_signal_mapped",
            }
            and value["mode"] == "no_v2i"
            and type(value["phase_remaining_available"]) is bool
            and value["phase_remaining_available"] is False
            and type(value["regulatory_signal_mapped"]) is bool
        )
    elif kind == "mapping":
        valid = type(value) is dict
    elif kind == "native_list":
        valid = type(value) is list
    elif kind == "native_result":
        try:
            _validate_native_result(value, branch=label)
            valid = True
        except (TypeError, ValueError):
            valid = False
    else:  # pragma: no cover - declaration construction owns this vocabulary.
        raise ValueError(f"unsupported actual-native declaration kind: {kind}")
    if not valid:
        raise ValueError(f"actual-native nested type drifted: {label}")


def _validate_safety_record(value: Any) -> None:
    if type(value) is not dict:
        raise ValueError("actual-native safety record must be an object")
    fields = set(value)
    if fields != set(_SAFETY_COMMON_FIELDS | _SAFETY_SIGNAL_FIELDS):
        raise ValueError("actual-native safety record field set drifted")
    for name in ("tick_index",):
        if type(value[name]) is not int or value[name] < 0:
            raise ValueError(f"actual-native safety {name} drifted")
    for name in (
        "speed_mps",
        "ego_heading_rad",
        "route_heading_rad",
        "route_progress_m",
        "min_obb_clearance_m",
    ):
        if type(value[name]) is not float or not math.isfinite(value[name]):
            raise ValueError(f"actual-native safety {name} drifted")
    if value["speed_mps"] < 0.0 or value["min_obb_clearance_m"] < 0.0:
        raise ValueError("actual-native safety nonnegative metric drifted")
    for name in ("position_xy", "front_center_prev_xy", "front_center_xy"):
        _finite_vector(value[name], length=2, label=f"safety.{name}")
    for name in ("five_point_drivable_coverage", "red_light_at_interval_start", "source_complete"):
        if type(value[name]) is not bool:
            raise ValueError(f"actual-native safety {name} drifted")
    if (
        type(value["red_stop_lines"]) is not list
        or any(
            type(line) is not list
            or len(line) != 2
            or any(
                type(point) is not list
                or len(point) != 2
                or any(
                    type(item) is not float or not math.isfinite(item)
                    for item in point
                )
                for point in line
            )
            for line in value["red_stop_lines"]
        )
    ):
        raise ValueError("actual-native safety red stop-line schema drifted")
    if (
        value["speed_limit_mps"] is not None
        and (
            type(value["speed_limit_mps"]) is not float
            or not math.isfinite(value["speed_limit_mps"])
            or value["speed_limit_mps"] <= 0.0
        )
    ):
        raise ValueError("actual-native safety speed limit drifted")
    if (
        value["constant_velocity_circle_ttc_diagnostic_s"] is not None
        and (
            type(value["constant_velocity_circle_ttc_diagnostic_s"]) is not float
            or not math.isfinite(
                value["constant_velocity_circle_ttc_diagnostic_s"]
            )
            or value["constant_velocity_circle_ttc_diagnostic_s"] < 0.0
        )
    ):
        raise ValueError("actual-native safety TTC drifted")
    if value["signal_phase_at_interval_start"] not in _SAFETY_SIGNAL_PHASES:
        raise ValueError("actual-native safety signal phase drifted")
    _stop_lines(
        value["certified_signal_stop_lines"],
        label="safety.certified_signal_stop_lines",
    )
    if (
        type(value["pre_decision_speed_mps"]) is not float
        or not math.isfinite(value["pre_decision_speed_mps"])
        or value["pre_decision_speed_mps"] < 0.0
    ):
        raise ValueError("actual-native safety pre-decision speed drifted")


def _validate_controlled_scene(value: Any) -> None:
    if type(value) is not dict or set(value) != set(_CONTROLLED_SCENE_FIELDS):
        raise ValueError("actual-native controlled-scene field set drifted")
    if (
        type(value["scenario_id"]) is not str
        or not value["scenario_id"]
        or type(value["tick_index"]) is not int
        or value["tick_index"] < 0
        or type(value["sim_time_s"]) is not float
        or not math.isfinite(value["sim_time_s"])
        or value["sim_time_s"] < 0.0
        or type(value["actor_count"]) is not int
        or value["actor_count"] < 0
        or type(value["actors"]) is not list
        or len(value["actors"]) != value["actor_count"]
        or value["outcome_fields_consumed"] != []
        or value["candidate_tensor_consumed"] is not False
        or value["selected_trajectory_consumed"] is not False
    ):
        raise ValueError("actual-native controlled-scene scalar drifted")
    for actor in value["actors"]:
        if type(actor) is not dict or set(actor) != set(_ACTOR_FIELDS):
            raise ValueError("actual-native actor field set drifted")
        if (
            type(actor["id"]) is not str
            or not actor["id"]
            or type(actor["agent_type"]) is not str
            or not actor["agent_type"]
            or type(actor["heading_rad"]) is not float
            or not math.isfinite(actor["heading_rad"])
            or actor["scripted_exogenous"] is not True
            or type(actor["excluded_from_dp_control"]) is not bool
        ):
            raise ValueError("actual-native actor scalar drifted")
        _finite_vector(actor["position_xy"], length=2, label="actor.position_xy")
        _finite_vector(
            actor["velocity_xy_mps"],
            length=2,
            label="actor.velocity_xy_mps",
        )
    _validate_controlled_signal(
        value["signal"],
        expected_tick=value["tick_index"],
        expected_scenario=value["scenario_id"],
    )
    _validate_model_input_cache(
        value["model_input_cache"],
        expected_tick=value["tick_index"],
        expected_scenario=value["scenario_id"],
    )


def _validate_controlled_signal(
    value: Any, *, expected_tick: int, expected_scenario: str
) -> None:
    if type(value) is not dict:
        raise ValueError("actual-native controlled signal must be an object")
    source = value.get("source_receipt")
    if type(source) is not dict:
        raise ValueError("actual-native controlled signal source is missing")
    if set(value) == set(_NO_SIGNAL_FIELDS):
        if (
            set(source) != set(_NO_SIGNAL_SOURCE_FIELDS)
            or value["phase"] != "none"
            or value["source_row_count"] != 0
            or value["applied"] is not False
            or source["schema_version"]
            != "camp_dp_v25_current_signal_runtime_receipt_v2"
            or source["source_mode"] != "same_tick_no_signal_rule_no_v2i"
            or source["current_phase"] != "none"
            or source["traffic_light_regulatory_element_ids"] != []
            or source["phase_remaining_available"] is not False
            or source["source_valid"] is not True
            or source["applicable"] is not False
        ):
            raise ValueError("actual-native no-signal receipt drifted")
        _validate_source_common(
            source,
            expected_tick=expected_tick,
            expected_scenario=expected_scenario,
        )
        _sha_value(source["route_geometry_sha256"], "no-signal route geometry")
        _sha_value(source["source_chain_sha256"], "no-signal source chain")
        _sha_value(source["semantic_clone_sha256"], "no-signal semantic clone")
        _native_int_list(source["route_lanelet_ids"], "no-signal route lanelets")
        return
    if set(value) != set(_MAPPED_SIGNAL_FIELDS):
        raise ValueError("actual-native controlled signal variant drifted")
    if (
        set(source) != set(_MAPPED_SIGNAL_SOURCE_FIELDS)
        or source["schema_version"]
        != "camp_dp_v25_family_independent_current_signal_receipt_v1"
        or value["phase"] != source["current_phase"]
        or type(value["source_row_count"]) is not int
        or value["source_row_count"] <= 0
        or type(value["applied"]) is not bool
        or source["phase_authority_mode"]
        not in {"controlled_same_tick_override", "observe_same_tick_request"}
        or source["current_phase"] not in _MAPPED_SIGNAL_PHASES
        or source["freshness"] != "same_tick"
        or source["source_id"]
        != "fixed_dp_current_request_route_map_signal_one_hot"
        or source["phase_remaining_available"] is not False
        or source["source_valid"] is not True
        or type(source["applicable"]) is not bool
        or source["applicable"] is not (source["current_phase"] == "red")
    ):
        raise ValueError("actual-native mapped-signal receipt drifted")
    _validate_source_common(
        source,
        expected_tick=expected_tick,
        expected_scenario=expected_scenario,
    )
    for name in (
        "decision_timestamp_s",
        "source_timestamp_s",
        "source_age_s",
        "route_arc_m",
    ):
        if (
            type(source[name]) is not float
            or not math.isfinite(source[name])
            or source[name] < 0.0
        ):
            raise ValueError(f"actual-native mapped signal {name} drifted")
    if abs(
        source["decision_timestamp_s"]
        - source["source_timestamp_s"]
        - source["source_age_s"]
    ) > 1e-12 or source["source_age_s"] > 1e-9:
        raise ValueError("actual-native mapped signal timestamp drifted")
    for name in (
        "stop_line_geometry_sha256",
        "route_geometry_sha256",
        "source_chain_sha256",
        "route_signal_tensor_sha256",
        "map_signal_tensor_sha256",
    ):
        _sha_value(source[name], f"mapped signal {name}")
    for name in (
        "physical_light_ids",
        "bulb_ids",
        "controlled_lanelet_ids",
        "observed_route_lanelet_ids",
        "observed_map_lanelet_ids",
    ):
        _native_int_or_string_list(source[name], f"mapped signal {name}")
    for name in ("regulatory_element_id", "stop_line_id"):
        if type(source[name]) not in {int, str} or type(source[name]) is bool:
            raise ValueError(f"actual-native mapped signal {name} drifted")
    evidence = value["tensor_evidence"]
    if type(evidence) is not dict or set(evidence) != set(
        _TENSOR_EVIDENCE_FIELDS
    ):
        raise ValueError("actual-native signal tensor evidence field set drifted")
    if (
        evidence["schema_version"]
        != "camp_dp_v25_production_signal_tensor_evidence_v2"
        or evidence["tick_index"] != expected_tick
        or evidence["current_phase"] != source["current_phase"]
        or evidence["future_schedule_consumed"] is not False
        or evidence["phase_remaining_available"] is not False
        or evidence["decision_timestamp_s"] != source["decision_timestamp_s"]
        or evidence["source_timestamp_s"] != source["source_timestamp_s"]
        or evidence["route_signal_tensor_sha256"]
        != source["route_signal_tensor_sha256"]
        or evidence["map_signal_tensor_sha256"]
        != source["map_signal_tensor_sha256"]
    ):
        raise ValueError("actual-native signal tensor evidence drifted")
    route_ids, route_phase = _signal_rows(
        evidence["route_signal_rows"], "route signal rows"
    )
    map_ids, map_phase = _signal_rows(
        evidence["map_signal_rows"], "map signal rows"
    )
    observed_phases = {
        phase for phase in (route_phase, map_phase) if phase is not None
    }
    if (
        not route_ids
        and not map_ids
        or route_ids != source["observed_route_lanelet_ids"]
        or map_ids != source["observed_map_lanelet_ids"]
        or value["source_row_count"] != len(route_ids) + len(map_ids)
        or observed_phases != {source["current_phase"]}
        or _canonical_sha(evidence["route_signal_rows"])
        != source["route_signal_tensor_sha256"]
        or _canonical_sha(evidence["map_signal_rows"])
        != source["map_signal_tensor_sha256"]
    ):
        raise ValueError("actual-native signal row authority drifted")


def _validate_source_common(
    value: Mapping[str, Any], *, expected_tick: int, expected_scenario: str
) -> None:
    if (
        value["scenario_id"] != expected_scenario
        or value["tick_index"] != expected_tick
    ):
        raise ValueError("actual-native source/tick binding drifted")
    if "decision_time_s" in value and (
        type(value["decision_time_s"]) is not float
        or not math.isfinite(value["decision_time_s"])
        or value["decision_time_s"] < 0.0
    ):
        raise ValueError("actual-native source decision time drifted")


def _validate_model_input_cache(
    value: Any, *, expected_tick: int, expected_scenario: str
) -> None:
    if type(value) is not dict or set(value) != set(_MODEL_INPUT_CACHE_FIELDS):
        raise ValueError("actual-native model-input cache field set drifted")
    if (
        value["schema_version"]
        != "camp_dp_v25_model_input_signal_cache_receipt_v1"
        or value["scenario_id"] != expected_scenario
        or value["tick_index"] != expected_tick
        or value["signal_source_class"] not in {"mapped_signal", "no_signal"}
        or value["phase_authority_mode"]
        not in {
            None,
            "controlled_same_tick_override",
            "observe_same_tick_request",
        }
        or value["cache_matches_scene_after"] is not True
        or type(value["observe_cache_unchanged"]) is not bool
        or value["sync_applied_before_tensor_conversion"] is not True
        or value["future_schedule_consumed"] is not False
        or value["phase_remaining_available"] is not False
    ):
        raise ValueError("actual-native model-input cache value drifted")
    if (
        value["signal_source_class"] == "no_signal"
        and value["phase_authority_mode"] is not None
    ) or (
        value["signal_source_class"] == "mapped_signal"
        and value["phase_authority_mode"] is None
    ):
        raise ValueError("actual-native model-input cache mode drifted")
    for name in (
        "scene_map_tl_sha256",
        "model_cache_tl_sha256_before",
        "model_cache_tl_sha256_after",
        "model_route_lanes_tl_sha256",
    ):
        _sha_value(value[name], f"model input cache {name}")
    if (
        value["model_cache_tl_sha256_after"]
        != value["scene_map_tl_sha256"]
    ):
        raise ValueError("actual-native model-input cache sync drifted")


def _finite_vector(value: Any, *, length: int, label: str) -> None:
    if (
        type(value) is not list
        or len(value) != length
        or any(type(item) is not float or not math.isfinite(item) for item in value)
    ):
        raise ValueError(f"actual-native {label} drifted")


def _stop_lines(value: Any, *, label: str) -> None:
    if type(value) is not list:
        raise ValueError(f"actual-native {label} drifted")
    for line in value:
        if type(line) is not list or len(line) != 2:
            raise ValueError(f"actual-native {label} drifted")
        for point in line:
            _finite_vector(point, length=2, label=label)


def _sha_value(value: Any, label: str) -> None:
    if not _sha(value):
        raise ValueError(f"actual-native {label} drifted")


def _native_int_list(value: Any, label: str) -> None:
    if type(value) is not list or any(type(item) is not int for item in value):
        raise ValueError(f"actual-native {label} drifted")


def _native_int_or_string_list(value: Any, label: str) -> None:
    if type(value) is not list or any(
        type(item) not in {int, str} or (type(item) is str and not item)
        for item in value
    ):
        raise ValueError(f"actual-native {label} drifted")


def _signal_rows(value: Any, label: str) -> tuple[list[int], str | None]:
    if type(value) is not list:
        raise ValueError(f"actual-native {label} drifted")
    ids: list[int] = []
    phases: set[str] = set()
    for row in value:
        if (
            type(row) is not dict
            or set(row) != {"lanelet_id", "signal_channels_8_12"}
            or type(row["lanelet_id"]) is not int
            or type(row["signal_channels_8_12"]) is not list
            or not row["signal_channels_8_12"]
        ):
            raise ValueError(f"actual-native {label} drifted")
        row_phases: set[str] = set()
        active_count = 0
        for channel_row in row["signal_channels_8_12"]:
            _finite_vector(channel_row, length=5, label=label)
            if all(item == 0.0 for item in channel_row):
                continue
            active_count += 1
            matches = []
            for phase, column in (("green", 0), ("yellow", 1), ("red", 2)):
                expected = [0.0] * 5
                expected[column] = 1.0
                if channel_row == expected:
                    matches.append(phase)
            if len(matches) != 1:
                raise ValueError(f"actual-native {label} phase drifted")
            row_phases.add(matches[0])
        if active_count == 0 or len(row_phases) != 1:
            raise ValueError(f"actual-native {label} phase drifted")
        ids.append(row["lanelet_id"])
        phases.update(row_phases)
    if len(ids) != len(set(ids)) or len(phases) > 1:
        raise ValueError(f"actual-native {label} authority drifted")
    return ids, next(iter(phases)) if phases else None


def _validate_native_result(value: Any, *, branch: str) -> None:
    fields = {
        "final_step",
        "goal_reached",
        "reason",
        "n_npc_spawned",
        "trajectory_log_path",
        "clearance_log_path",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or type(value["final_step"]) is not int
        or value["final_step"] < 0
        or type(value["goal_reached"]) is not bool
        or type(value["reason"]) is not str
        or not value["reason"]
        or type(value["n_npc_spawned"]) is not int
        or value["n_npc_spawned"] < 0
    ):
        raise ValueError(f"{branch} actual-native terminal schema drifted")
    if (
        type(value["trajectory_log_path"]) is not str
        or type(value["clearance_log_path"]) is not str
    ):
        raise ValueError(f"{branch} actual-native terminal path drifted")
    trajectory = Path(value["trajectory_log_path"])
    clearance = Path(value["clearance_log_path"])
    if (
        not trajectory.is_absolute()
        or not clearance.is_absolute()
        or str(trajectory) != str(trajectory.resolve())
        or str(clearance) != str(clearance.resolve())
        or trajectory.name != "trajectory_log.json"
        or clearance.name != "clearance_log.json"
        or trajectory.parent != clearance.parent
    ):
        raise ValueError(f"{branch} actual-native terminal path drifted")
