from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .diffusion_planner_v25_signal_complete_runtime import (
    SCHEMA_VERSION as RUNTIME_SCHEMA_VERSION,
    build_signal_complete_scene_adapter,
)


CALIBRATION_CONFIG_SCHEMA_VERSION = (
    "camp_dp_v25_signal_complete_candidate0_calibration_v1"
)
FRESH_ARM_CONFIG_SCHEMA_VERSION = "camp_dp_v25_signal_complete_fresh_arm_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FRESH_PLAN_ARMS = (
    "candidate0_operational_default",
    "camp_static14d",
    "camp_scene14d_no_v2i",
)
_FRESH_ARM_ROTATIONS = frozenset(
    tuple(FRESH_PLAN_ARMS[offset:] + FRESH_PLAN_ARMS[:offset])
    for offset in range(len(FRESH_PLAN_ARMS))
)
_FRESH_ARM_CONTRACT = {
    "candidate0_operational_default": {
        "opening_arm": "candidate0",
        "native_arm": "dp",
        "fixed_k8_candidate0": True,
        "selector_role": "v25_fresh_candidate0_assets_bound_not_consumed",
        "selector_model": "DP-operational-default-candidate0",
        "static_weights_consumed": False,
        "scene_weight_provider_required": False,
    },
    "camp_static14d": {
        "opening_arm": "static14d",
        "native_arm": "camp",
        "fixed_k8_candidate0": False,
        "selector_role": "v25_fresh_static14d_sealed_runtime",
        "selector_model": "CAMP-Static14D",
        "static_weights_consumed": True,
        "scene_weight_provider_required": False,
    },
    "camp_scene14d_no_v2i": {
        "opening_arm": "scene14d",
        "native_arm": "camp",
        "fixed_k8_candidate0": False,
        "selector_role": "v25_fresh_scene14d_no_v2i_sealed_runtime",
        "selector_model": "CAMP-Scene14D",
        "static_weights_consumed": False,
        "scene_weight_provider_required": True,
    },
}


def build_fresh_b2_arm_config(
    *,
    probe_template: Mapping[str, Any],
    prepared_runtime: Mapping[str, Any],
    execution_unit: Mapping[str, Any],
    plan_arm: str,
    route_asset: Mapping[str, Any],
    dp_repo: Path,
    runtime_selector_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one unopened Fresh-B2 arm config from frozen authorities.

    The config is deliberately inert by itself.  The native runner additionally
    requires a validated one-time opening release and consumption receipt before
    it can construct any model/runtime state.
    """

    if type(probe_template) is not dict:
        raise ValueError("Fresh B2 probe template must be a mapping")
    if plan_arm not in _FRESH_ARM_CONTRACT:
        raise ValueError("Fresh B2 plan arm is not one of the frozen primary arms")
    prepared = copy.deepcopy(prepared_runtime)
    case = prepared.get("case")
    if type(case) is not dict or prepared.get("schema_version") != RUNTIME_SCHEMA_VERSION:
        raise ValueError("Fresh B2 runtime authority drifted")
    build_signal_complete_scene_adapter(prepared)
    unit = _fresh_execution_unit(execution_unit, prepared)
    arm_index = unit["ordered_arms"].index(plan_arm)
    route = _asset(route_asset, "route_asset")
    if route.get("name") != case.get("route_identity_sha256"):
        raise ValueError("Fresh B2 route asset identity drifted")
    authority = _runtime_selector_authority(runtime_selector_authority)
    contract = _FRESH_ARM_CONTRACT[plan_arm]

    fixed_dp = copy.deepcopy(_mapping(probe_template, "fixed_dp"))
    fixed_dp["repo"] = str(dp_repo.resolve())
    if fixed_dp.get("head") != FIXED_DP_HEAD:
        raise ValueError("Fresh B2 fixed DP HEAD drifted")
    selector = copy.deepcopy(_mapping(probe_template, "selector"))
    selector.update(
        {
            "atom_scales": dict(authority["atom_scales"]),
            "weights": dict(authority["static14d_weights"]),
            "role": contract["selector_role"],
            "runtime_model": contract["selector_model"],
            "selection_policy": "v22_source_valid",
            "candidate_k": 8,
            "static_weights_consumed": contract["static_weights_consumed"],
            "scene_weight_provider_required": contract[
                "scene_weight_provider_required"
            ],
        }
    )
    spawn = copy.deepcopy(_mapping(probe_template, "spawn_config"))
    seed = unit["seed"]
    spawn.update(
        {
            "seed": seed,
            "max_steps": 64,
            "static_npc_count": 0,
            "spawn_probability": 0.0,
            "max_active_npcs": 0,
            "enable_traffic_lights": True,
            "dump_npz_dir": None,
            "reward_config_path": None,
            "sequential_inference": False,
            "sg_smooth_enabled": False,
            "advance_mode": "mpc",
            "mpc_horizon_steps": 20,
            "mpc_n_knots": 5,
        }
    )
    config = {
        "schema_version": FRESH_ARM_CONFIG_SCHEMA_VERSION,
        "fixed_dp": fixed_dp,
        "selector": selector,
        "map": {
            "path": case["source_map_path"],
            "sha256": case["source_map_sha256"],
        },
        "routes": [dict(route)],
        "seeds": {
            "scenario": seed,
            "candidate": seed,
            "bootstrap": seed,
            "formal_forbidden": [
                11,
                12,
                13,
                24001,
                24002,
                24003,
                24004,
                24005,
                25001,
                25301,
                25302,
            ],
        },
        "spawn_config": spawn,
        "protocol": {
            "arm_order": [contract["native_arm"]],
            "fresh_b2_plan_arm": plan_arm,
            "fresh_b2_opening_arm": contract["opening_arm"],
            "arm_order_index": arm_index,
            "route_order": [case["route_identity_sha256"]],
            "fresh_b2_steps": 64,
            "candidate_k": 8,
            "fixed_k8_candidate0": contract["fixed_k8_candidate0"],
            "candidate0_semantics": "same_forward_operational_default_alias",
            "candidate0_offline_pool_evidence_required": (
                plan_arm == "candidate0_operational_default"
            ),
            "independent_reset_per_arm": True,
            "same_initial_state_and_exogenous_schedule_per_pair": True,
            "candidate_tensor_modification_authorized": False,
            "trajectory_postprocess_authorized": False,
            "certified_signal_safety_source_required": True,
            "safety_schema": "safety_cost_native_v22",
            "training_authorized": False,
            "calibration_authorized": False,
            "execution_authorized_by_config": False,
            "external_one_time_opening_release_required": True,
            "holdout_access_authorized_by_config": False,
            "fresh_b2_opened": False,
            "fresh_outcome_fields_consumed": [],
            "claim_authorized": False,
        },
        "signal_complete_runtime": prepared,
        "signal_complete_plan_authority": {
            "unit_ordinal": unit["unit_ordinal"],
            "unit_sha256": unit["unit_sha256"],
            "scenario_identity_sha256": unit["scenario_identity_sha256"],
            "route_identity_sha256": case["route_identity_sha256"],
            "semantic_parameter_block_sha256": case["parameter_block_id"],
            "seed": seed,
            "ordered_arms": list(unit["ordered_arms"]),
            "plan_arm": plan_arm,
            "arm_order_index": arm_index,
        },
        "runtime_selector_authority": authority,
    }
    return validate_fresh_b2_arm_config(config)


def validate_fresh_b2_arm_config(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "schema_version",
        "fixed_dp",
        "selector",
        "map",
        "routes",
        "seeds",
        "spawn_config",
        "protocol",
        "signal_complete_runtime",
        "signal_complete_plan_authority",
        "runtime_selector_authority",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("Fresh B2 arm config field set drifted")
    result = copy.deepcopy(value)
    if result.get("schema_version") != FRESH_ARM_CONFIG_SCHEMA_VERSION:
        raise ValueError("Fresh B2 arm config schema drifted")
    fixed = _mapping(result, "fixed_dp")
    if fixed.get("head") != FIXED_DP_HEAD or type(fixed.get("repo")) is not str:
        raise ValueError("Fresh B2 fixed DP authority drifted")
    _asset(_mapping(fixed, "checkpoint"), "checkpoint")
    _asset(_mapping(fixed, "args_json"), "args_json")
    if type(fixed.get("native_source_sha256")) is not dict:
        raise ValueError("Fresh B2 fixed DP source authority is missing")

    runtime = _mapping(result, "signal_complete_runtime")
    adapter = build_signal_complete_scene_adapter(runtime)
    case = adapter.case
    map_asset = _asset(_mapping(result, "map"), "map")
    routes = result.get("routes")
    if type(routes) is not list or len(routes) != 1:
        raise ValueError("Fresh B2 arm config requires one route asset")
    route = _asset(routes[0], "route")
    _require_sha(route.get("name"), "route.name")
    if (
        map_asset["path"] != case["source_map_path"]
        or map_asset["sha256"] != case["source_map_sha256"]
        or route["name"] != case["route_identity_sha256"]
    ):
        raise ValueError("Fresh B2 runtime assets drifted")

    authority = _runtime_selector_authority(
        _mapping(result, "runtime_selector_authority")
    )
    selector = _mapping(result, "selector")
    protocol = _mapping(result, "protocol")
    plan_arm = protocol.get("fresh_b2_plan_arm")
    if plan_arm not in _FRESH_ARM_CONTRACT:
        raise ValueError("Fresh B2 protocol arm drifted")
    contract = _FRESH_ARM_CONTRACT[plan_arm]
    if (
        not _strict_equal(selector.get("atom_scales"), authority["atom_scales"])
        or not _strict_equal(
            selector.get("weights"), authority["static14d_weights"]
        )
        or selector.get("role") != contract["selector_role"]
        or selector.get("runtime_model") != contract["selector_model"]
        or selector.get("selection_policy") != "v22_source_valid"
        or selector.get("candidate_k") != 8
        or selector.get("score_contract") != "score_k(w)=a_k^T w"
        or selector.get("nonnegative_simplex") is not True
        or selector.get("static_weights_consumed")
        is not contract["static_weights_consumed"]
        or selector.get("scene_weight_provider_required")
        is not contract["scene_weight_provider_required"]
    ):
        raise ValueError("Fresh B2 selector contract drifted")

    plan_authority = _mapping(result, "signal_complete_plan_authority")
    if set(plan_authority) != {
        "unit_ordinal",
        "unit_sha256",
        "scenario_identity_sha256",
        "route_identity_sha256",
        "semantic_parameter_block_sha256",
        "seed",
        "ordered_arms",
        "plan_arm",
        "arm_order_index",
    }:
        raise ValueError("Fresh B2 plan authority fields drifted")
    if (
        type(plan_authority["unit_ordinal"]) is not int
        or plan_authority["unit_ordinal"] < 0
        or plan_authority["scenario_identity_sha256"]
        != runtime["scenario_identity_sha256"]
        or plan_authority["route_identity_sha256"] != case["route_identity_sha256"]
        or plan_authority["semantic_parameter_block_sha256"]
        != case["parameter_block_id"]
        or plan_authority["plan_arm"] != plan_arm
        or plan_authority["ordered_arms"] is None
        or type(plan_authority["ordered_arms"]) is not list
        or tuple(plan_authority["ordered_arms"]) not in _FRESH_ARM_ROTATIONS
        or plan_authority["arm_order_index"]
        != plan_authority["ordered_arms"].index(plan_arm)
    ):
        raise ValueError("Fresh B2 plan authority drifted")
    for name in (
        "unit_sha256",
        "scenario_identity_sha256",
        "semantic_parameter_block_sha256",
    ):
        _require_sha(plan_authority[name], name)
    seed = plan_authority["seed"]
    if type(seed) is not int or seed < 0:
        raise ValueError("Fresh B2 seed authority drifted")
    expected_unit_sha = _canonical_sha(
        {
            "scenario_identity_sha256": plan_authority[
                "scenario_identity_sha256"
            ],
            "seed": seed,
            "ordered_arms": plan_authority["ordered_arms"],
        }
    )
    if plan_authority["unit_sha256"] != expected_unit_sha:
        raise ValueError("Fresh B2 unit SHA drifted")
    seeds = _mapping(result, "seeds")
    if seeds != {
        "scenario": seed,
        "candidate": seed,
        "bootstrap": seed,
        "formal_forbidden": [
            11,
            12,
            13,
            24001,
            24002,
            24003,
            24004,
            24005,
            25001,
            25301,
            25302,
        ],
    }:
        raise ValueError("Fresh B2 seed namespace drifted")
    spawn = _mapping(result, "spawn_config")
    critical_spawn = {
        "seed": seed,
        "max_steps": 64,
        "static_npc_count": 0,
        "spawn_probability": 0.0,
        "max_active_npcs": 0,
        "enable_traffic_lights": True,
        "dump_npz_dir": None,
        "reward_config_path": None,
        "sequential_inference": False,
        "sg_smooth_enabled": False,
        "advance_mode": "mpc",
        "mpc_horizon_steps": 20,
        "mpc_n_knots": 5,
    }
    if any(
        not _strict_equal(spawn.get(name), expected)
        for name, expected in critical_spawn.items()
    ):
        raise ValueError("Fresh B2 spawn contract drifted")
    expected_protocol = {
        "arm_order": [contract["native_arm"]],
        "fresh_b2_plan_arm": plan_arm,
        "fresh_b2_opening_arm": contract["opening_arm"],
        "arm_order_index": plan_authority["arm_order_index"],
        "route_order": [case["route_identity_sha256"]],
        "fresh_b2_steps": 64,
        "candidate_k": 8,
        "fixed_k8_candidate0": contract["fixed_k8_candidate0"],
        "candidate0_semantics": "same_forward_operational_default_alias",
        "candidate0_offline_pool_evidence_required": (
            plan_arm == "candidate0_operational_default"
        ),
        "independent_reset_per_arm": True,
        "same_initial_state_and_exogenous_schedule_per_pair": True,
        "candidate_tensor_modification_authorized": False,
        "trajectory_postprocess_authorized": False,
        "certified_signal_safety_source_required": True,
        "safety_schema": "safety_cost_native_v22",
        "training_authorized": False,
        "calibration_authorized": False,
        "execution_authorized_by_config": False,
        "external_one_time_opening_release_required": True,
        "holdout_access_authorized_by_config": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
        "claim_authorized": False,
    }
    if not _strict_equal(protocol, expected_protocol):
        raise ValueError("Fresh B2 protocol drifted")
    return result


def build_candidate0_calibration_config(
    *,
    probe_template: Mapping[str, Any],
    prepared_runtime: Mapping[str, Any],
    execution_unit: Mapping[str, Any],
    route_asset: Mapping[str, Any],
    dp_repo: Path,
) -> dict[str, Any]:
    """Build one candidate0-only config from frozen plan/runtime authority."""

    if type(probe_template) is not dict:
        raise ValueError("candidate0 calibration probe template must be a mapping")
    prepared = copy.deepcopy(prepared_runtime)
    case = prepared.get("case")
    if type(case) is not dict or prepared.get("schema_version") != RUNTIME_SCHEMA_VERSION:
        raise ValueError("candidate0 calibration runtime authority drifted")
    # Constructor validation proves both the controlled and no-script adapter
    # paths bind the exact route-level mapped signal chain.
    build_signal_complete_scene_adapter(prepared)
    unit = _execution_unit(execution_unit, prepared)
    route = _asset(route_asset, "route_asset")
    if route.get("name") != case.get("route_identity_sha256"):
        raise ValueError("candidate0 calibration route asset identity drifted")
    fixed_dp = copy.deepcopy(_mapping(probe_template, "fixed_dp"))
    fixed_dp["repo"] = str(dp_repo.resolve())
    if fixed_dp.get("head") != FIXED_DP_HEAD:
        raise ValueError("candidate0 calibration fixed DP HEAD drifted")
    selector = copy.deepcopy(_mapping(probe_template, "selector"))
    selector["role"] = "v25_candidate0_calibration_assets_bound_not_consumed"
    selector["selection_policy"] = "v22_source_valid"
    selector["candidate_k"] = 8
    spawn = copy.deepcopy(_mapping(probe_template, "spawn_config"))
    seed = unit["seed"]
    spawn.update(
        {
            "seed": seed,
            "max_steps": 64,
            "static_npc_count": 0,
            "spawn_probability": 0.0,
            "max_active_npcs": 0,
            "enable_traffic_lights": True,
            "dump_npz_dir": None,
            "reward_config_path": None,
            "sequential_inference": False,
            "sg_smooth_enabled": False,
            "advance_mode": "mpc",
            "mpc_horizon_steps": 20,
            "mpc_n_knots": 5,
        }
    )
    config = {
        "schema_version": CALIBRATION_CONFIG_SCHEMA_VERSION,
        "fixed_dp": fixed_dp,
        "selector": selector,
        "map": {
            "path": case["source_map_path"],
            "sha256": case["source_map_sha256"],
        },
        "routes": [dict(route)],
        "seeds": {
            "scenario": seed,
            "candidate": seed,
            "bootstrap": seed,
            "formal_forbidden": [11, 12, 13, 24001, 24002, 24003, 24004, 24005, 25001],
        },
        "spawn_config": spawn,
        "protocol": {
            "arm_order": ["dp"],
            "route_order": [case["route_identity_sha256"]],
            "calibration_steps": 64,
            "candidate_k": 8,
            "fixed_k8_candidate0": True,
            "candidate0_semantics": "same_forward_operational_default_alias",
            "candidate_tensor_modification_authorized": False,
            "certified_signal_safety_source_required": True,
            "safety_schema": "safety_cost_native_v22",
            "training_authorized": False,
            "calibration_authorized": True,
            "camp_method_outcomes_authorized": False,
            "holdout_access_authorized": False,
            "fresh_b2_opened": False,
            "fresh_outcome_fields_consumed": [],
            "claim_authorized": False,
        },
        "signal_complete_runtime": prepared,
        "signal_complete_plan_authority": {
            "unit_ordinal": unit["unit_ordinal"],
            "unit_sha256": unit["unit_sha256"],
            "scenario_identity_sha256": unit["scenario_identity_sha256"],
            "route_identity_sha256": case["route_identity_sha256"],
            "seed": seed,
        },
    }
    return validate_candidate0_calibration_config(config)


def validate_candidate0_calibration_config(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "schema_version", "fixed_dp", "selector", "map", "routes", "seeds",
        "spawn_config", "protocol", "signal_complete_runtime",
        "signal_complete_plan_authority",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("candidate0 calibration config field set drifted")
    result = copy.deepcopy(value)
    if result.get("schema_version") != CALIBRATION_CONFIG_SCHEMA_VERSION:
        raise ValueError("candidate0 calibration config schema drifted")
    fixed = _mapping(result, "fixed_dp")
    if fixed.get("head") != FIXED_DP_HEAD or type(fixed.get("repo")) is not str:
        raise ValueError("candidate0 calibration fixed DP authority drifted")
    _asset(_mapping(fixed, "checkpoint"), "checkpoint")
    _asset(_mapping(fixed, "args_json"), "args_json")
    if type(fixed.get("native_source_sha256")) is not dict:
        raise ValueError("candidate0 calibration fixed DP source authority is missing")
    selector = _mapping(result, "selector")
    _asset(_mapping(selector, "atom_scales"), "atom_scales")
    _asset(_mapping(selector, "weights"), "weights")
    if (
        selector.get("role") != "v25_candidate0_calibration_assets_bound_not_consumed"
        or selector.get("selection_policy") != "v22_source_valid"
        or selector.get("candidate_k") != 8
        or selector.get("score_contract") != "score_k(w)=a_k^T w"
        or selector.get("nonnegative_simplex") is not True
    ):
        raise ValueError("candidate0 calibration selector non-consumption contract drifted")
    map_asset = _asset(_mapping(result, "map"), "map")
    routes = result.get("routes")
    if type(routes) is not list or len(routes) != 1:
        raise ValueError("candidate0 calibration requires one route asset")
    route = _asset(routes[0], "route")
    _require_sha(route.get("name"), "route.name")
    runtime = _mapping(result, "signal_complete_runtime")
    adapter = build_signal_complete_scene_adapter(runtime)
    case = adapter.case
    if (
        map_asset["path"] != case["source_map_path"]
        or map_asset["sha256"] != case["source_map_sha256"]
        or route["name"] != case["route_identity_sha256"]
    ):
        raise ValueError("candidate0 calibration runtime assets drifted")
    authority = _mapping(result, "signal_complete_plan_authority")
    if set(authority) != {
        "unit_ordinal", "unit_sha256", "scenario_identity_sha256",
        "route_identity_sha256", "seed",
    }:
        raise ValueError("candidate0 calibration plan authority fields drifted")
    if (
        type(authority["unit_ordinal"]) is not int
        or authority["unit_ordinal"] < 0
        or authority["scenario_identity_sha256"]
        != runtime["scenario_identity_sha256"]
        or authority["route_identity_sha256"] != case["route_identity_sha256"]
    ):
        raise ValueError("candidate0 calibration plan authority drifted")
    _require_sha(authority["unit_sha256"], "unit_sha256")
    _require_sha(authority["scenario_identity_sha256"], "scenario_identity_sha256")
    seeds = _mapping(result, "seeds")
    seed = authority["seed"]
    if type(seed) is not int or seeds != {
        "scenario": seed,
        "candidate": seed,
        "bootstrap": seed,
        "formal_forbidden": [11, 12, 13, 24001, 24002, 24003, 24004, 24005, 25001],
    }:
        raise ValueError("candidate0 calibration seed authority drifted")
    if authority["unit_sha256"] != _canonical_sha(
        {
            "scenario_identity_sha256": authority["scenario_identity_sha256"],
            "seed": seed,
            "ordered_arms": ["candidate0_operational_default"],
        }
    ):
        raise ValueError("candidate0 calibration unit SHA drifted")
    spawn = _mapping(result, "spawn_config")
    critical_spawn = {
        "seed": seed, "max_steps": 64, "static_npc_count": 0,
        "spawn_probability": 0.0, "max_active_npcs": 0,
        "enable_traffic_lights": True, "dump_npz_dir": None,
        "reward_config_path": None, "sequential_inference": False,
        "sg_smooth_enabled": False, "advance_mode": "mpc",
        "mpc_horizon_steps": 20, "mpc_n_knots": 5,
    }
    if any(not _strict_equal(spawn.get(name), expected) for name, expected in critical_spawn.items()):
        raise ValueError("candidate0 calibration spawn contract drifted")
    protocol = _mapping(result, "protocol")
    expected_protocol = {
        "arm_order": ["dp"],
        "route_order": [case["route_identity_sha256"]],
        "calibration_steps": 64,
        "candidate_k": 8,
        "fixed_k8_candidate0": True,
        "candidate0_semantics": "same_forward_operational_default_alias",
        "candidate_tensor_modification_authorized": False,
        "certified_signal_safety_source_required": True,
        "safety_schema": "safety_cost_native_v22",
        "training_authorized": False,
        "calibration_authorized": True,
        "camp_method_outcomes_authorized": False,
        "holdout_access_authorized": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
        "claim_authorized": False,
    }
    if not _strict_equal(protocol, expected_protocol):
        raise ValueError("candidate0 calibration protocol drifted")
    return result


def _execution_unit(
    value: Mapping[str, Any], prepared: Mapping[str, Any]
) -> dict[str, Any]:
    fields = {"unit_ordinal", "scenario_identity_sha256", "seed", "ordered_arms", "unit_sha256"}
    if type(value) is not dict or set(value) != fields:
        raise ValueError("candidate0 calibration execution unit drifted")
    unit = dict(value)
    if (
        type(unit["unit_ordinal"]) is not int
        or unit["unit_ordinal"] < 0
        or unit["scenario_identity_sha256"] != prepared["scenario_identity_sha256"]
        or type(unit["seed"]) is not int
        or unit["seed"] < 0
        or unit["ordered_arms"] != ["candidate0_operational_default"]
    ):
        raise ValueError("candidate0 calibration execution unit authority drifted")
    _require_sha(unit["unit_sha256"], "unit_sha256")
    if unit["unit_sha256"] != _canonical_sha(
        {
            "scenario_identity_sha256": unit["scenario_identity_sha256"],
            "seed": unit["seed"],
            "ordered_arms": unit["ordered_arms"],
        }
    ):
        raise ValueError("candidate0 calibration execution unit SHA drifted")
    return unit


def _fresh_execution_unit(
    value: Mapping[str, Any], prepared: Mapping[str, Any]
) -> dict[str, Any]:
    fields = {
        "unit_ordinal",
        "scenario_identity_sha256",
        "seed",
        "ordered_arms",
        "unit_sha256",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("Fresh B2 execution unit fields drifted")
    unit = dict(value)
    if (
        type(unit["unit_ordinal"]) is not int
        or unit["unit_ordinal"] < 0
        or unit["scenario_identity_sha256"]
        != prepared["scenario_identity_sha256"]
        or type(unit["seed"]) is not int
        or unit["seed"] < 0
        or type(unit["ordered_arms"]) is not list
        or tuple(unit["ordered_arms"]) not in _FRESH_ARM_ROTATIONS
    ):
        raise ValueError("Fresh B2 execution unit authority drifted")
    _require_sha(unit["unit_sha256"], "unit_sha256")
    if unit["unit_sha256"] != _canonical_sha(
        {
            "scenario_identity_sha256": unit["scenario_identity_sha256"],
            "seed": unit["seed"],
            "ordered_arms": unit["ordered_arms"],
        }
    ):
        raise ValueError("Fresh B2 execution unit SHA drifted")
    return unit


def _runtime_selector_authority(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "training_artifact",
        "training_review_artifact",
        "calibration_contract_root_sha256",
        "preopen_qualification_root_sha256",
        "scenario_manifest_root_sha256",
        "model_registry_sha256",
        "training_scale_sha256",
        "context_scaler_sha256",
        "atom_scales",
        "static14d_weights",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("Fresh B2 runtime selector authority fields drifted")
    result = copy.deepcopy(value)
    for name in ("training_artifact", "training_review_artifact"):
        binding = result[name]
        if type(binding) is not dict or set(binding) != {"path", "root_sha256"}:
            raise ValueError(f"Fresh B2 {name} binding drifted")
        if type(binding["path"]) is not str or not binding["path"]:
            raise ValueError(f"Fresh B2 {name} path is invalid")
        _require_sha(binding["root_sha256"], f"{name}.root_sha256")
    for name in (
        "calibration_contract_root_sha256",
        "preopen_qualification_root_sha256",
        "scenario_manifest_root_sha256",
        "model_registry_sha256",
        "training_scale_sha256",
        "context_scaler_sha256",
    ):
        _require_sha(result[name], name)
    result["atom_scales"] = _asset(result["atom_scales"], "atom_scales")
    result["static14d_weights"] = _asset(
        result["static14d_weights"], "static14d_weights"
    )
    return result


def _asset(value: Mapping[str, Any], name: str) -> dict[str, Any]:
    if type(value) is not dict or type(value.get("path")) is not str or not value["path"]:
        raise ValueError(f"{name} path is invalid")
    _require_sha(value.get("sha256"), f"{name}.sha256")
    return dict(value)


def _mapping(value: Mapping[str, Any], name: str) -> dict[str, Any]:
    child = value.get(name)
    if type(child) is not dict:
        raise ValueError(f"{name} must be a native mapping")
    return dict(child)


def _require_sha(value: Any, name: str) -> None:
    if type(value) is not str or len(value) != 64 or set(value) - set("0123456789abcdef"):
        raise ValueError(f"{name} must be a lowercase SHA256")


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_strict_equal(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(_strict_equal(a, b) for a, b in zip(left, right, strict=True))
    return bool(left == right)


def _canonical_sha(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    payload = (payload + "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
