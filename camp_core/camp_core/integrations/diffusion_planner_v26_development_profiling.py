"""Development-only same-pool B8 profiling contract for V26.

This module records descriptive selector behavior on one candidate0-driven
development trajectory.  It is deliberately not a closed-loop comparison
between arms and carries no support, OOD, stability, safety, benefit, or
training conclusion.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import statistics
from typing import Any, Mapping


PROFILE_MANIFEST_SCHEMA_VERSION = "camp_dp_v26_development_profiling_manifest_v1"
PROFILE_RECEIPT_SCHEMA_VERSION = "camp_dp_v26_development_profiling_receipt_v1"
EVIDENCE_ROLE = "development_nonholdout_profiling_support_description"
PROFILE_STATE_COUNT = 20
SAME_EGO_BATCH_SIZE = 8
LATENT_SHAPE = [8, 321, 81, 4]
LATENT_DTYPE = "float32"
OPERATIONAL_ARM = "pool_matched_candidate0"
PROFILE_ARMS = (
    OPERATIONAL_ARM,
    "Static9D",
    "Scene9D",
    "Static14D",
    "Scene14D",
)
ATOM_SET_BY_ARM = {
    OPERATIONAL_ARM: "candidate0_frozen_row0",
    "Static9D": "paper_9d_prefix_of_canonical_14d",
    "Scene9D": "paper_9d_prefix_of_canonical_14d",
    "Static14D": "canonical_14d_extension_ablation",
    "Scene14D": "canonical_14d_extension_ablation",
}
ACTIVE_ATOM_INDICES_BY_ARM = {
    OPERATIONAL_ARM: [],
    "Static9D": list(range(9)),
    "Scene9D": list(range(9)),
    "Static14D": list(range(14)),
    "Scene14D": list(range(14)),
}
ARM_ROLE_BY_ARM = {
    OPERATIONAL_ARM: "frozen_same_pool_candidate0_baseline",
    "Static9D": "paper_method_9d_bridge_static",
    "Scene9D": "paper_method_9d_bridge_scene_conditioned",
    "Static14D": "planning_domain_14d_static_ablation",
    "Scene14D": "planning_domain_14d_scene_ablation",
}
ATOM_PHASE_NAMES = (
    "projection",
    "obb_build",
    "candidate_tick_obstacle_feasibility",
    "atom_arithmetic",
)


def _require_sha256(value: Any, name: str) -> str:
    if type(value) is not str or len(value) != 64:
        raise ValueError(f"{name} must be a 64-character SHA256 string")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be hexadecimal") from exc
    return value


def _require_commit(value: Any, name: str) -> str:
    if type(value) is not str or len(value) != 40:
        raise ValueError(f"{name} must be a full 40-character commit")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be hexadecimal") from exc
    return value


def _exact_mapping(value: Any, expected: set[str], name: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise ValueError(f"{name} field set drifted")
    return dict(value)


def canonical_planned_state_identity(
    *,
    route_sha256: str,
    scenario_seed: int,
    spawn_config: Mapping[str, Any],
    unit_index: int,
) -> str:
    """Bind a deterministic development state plan without outcome data."""

    _require_sha256(route_sha256, "route_sha256")
    if type(scenario_seed) is not int or scenario_seed < 0:
        raise ValueError("scenario_seed must be a nonnegative integer")
    if type(spawn_config) is not dict:
        raise ValueError("spawn_config must be an object")
    if type(unit_index) is not int or not 0 <= unit_index < PROFILE_STATE_COUNT:
        raise ValueError("unit_index is outside the fixed 20-state plan")
    payload = {
        "route_sha256": route_sha256,
        "scenario_seed": scenario_seed,
        "spawn_config": dict(spawn_config),
        "unit_index": unit_index,
        "state_progression": "candidate0_row0_only",
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_development_profiling_manifest(
    *,
    camp_head: str,
    probe_config_sha256: str,
    route_sha256: str,
    scenario_seed: int,
    spawn_config: Mapping[str, Any],
    fixed_dp_head: str,
    checkpoint_path: str,
    checkpoint_sha256: str,
    args_path: str,
    args_sha256: str,
    training_root_sha256: str,
    training_review_root_sha256: str,
    atom_scales_sha256: str,
    static9d_weights_sha256: str,
    scene9d_theta_sha256: str,
    static14d_weights_sha256: str,
    scene14d_theta_sha256: str,
    context_scaler_sha256: str,
) -> dict[str, Any]:
    """Build the fixed 20-state, same-pool development profiling manifest."""

    return validate_development_profiling_manifest(
        {
            "schema_version": PROFILE_MANIFEST_SCHEMA_VERSION,
            "evidence_role": EVIDENCE_ROLE,
            "state_count": PROFILE_STATE_COUNT,
            "operational_arm": OPERATIONAL_ARM,
            "selector_arms": list(PROFILE_ARMS),
            "arm_roles": dict(ARM_ROLE_BY_ARM),
            "execution_topology": {
                "pool_generation": "one_same_ego_b8_forward_per_state",
                "candidate0": "frozen_row0_default_and_only_state_progression",
                "selector_comparison": "same_state_same_pool_counterfactual_only",
                "post_pool_model_dp_latent_generation_mutation_regeneration": 0,
            },
            "route": {
                "split": "development_nonholdout",
                "holdout": False,
                "route_sha256": route_sha256,
                "scenario_seed": scenario_seed,
                "spawn_config": dict(spawn_config),
            },
            "state_plan": [
                {
                    "unit_index": unit_index,
                    "planned_state_id_sha256": canonical_planned_state_identity(
                        route_sha256=route_sha256,
                        scenario_seed=scenario_seed,
                        spawn_config=spawn_config,
                        unit_index=unit_index,
                    ),
                }
                for unit_index in range(PROFILE_STATE_COUNT)
            ],
            "latent_policy": {
                "candidate_seed_base": 24001,
                "same_ego_batch_size": SAME_EGO_BATCH_SIZE,
                "shape": list(LATENT_SHAPE),
                "dtype": LATENT_DTYPE,
                "row0_zero": True,
                "unique_rows_required": True,
            },
            "camp_head": camp_head,
            "probe_config_sha256": probe_config_sha256,
            "fixed_dp": {
                "head": fixed_dp_head,
                "checkpoint": {"path": checkpoint_path, "sha256": checkpoint_sha256},
                "args": {"path": args_path, "sha256": args_sha256},
            },
            "selector": {
                "training_root_sha256": training_root_sha256,
                "training_review_root_sha256": training_review_root_sha256,
                "atom_scales_sha256": atom_scales_sha256,
                "static9d_weights_sha256": static9d_weights_sha256,
                "scene9d_theta_sha256": scene9d_theta_sha256,
                "static14d_weights_sha256": static14d_weights_sha256,
                "scene14d_theta_sha256": scene14d_theta_sha256,
                "context_scaler_sha256": context_scaler_sha256,
            },
        }
    )


def validate_development_profiling_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    expected = {
        "schema_version",
        "evidence_role",
        "state_count",
        "operational_arm",
        "selector_arms",
        "arm_roles",
        "execution_topology",
        "route",
        "state_plan",
        "latent_policy",
        "camp_head",
        "probe_config_sha256",
        "fixed_dp",
        "selector",
    }
    if set(result) != expected:
        raise ValueError("V26 profiling manifest field set drifted")
    if (
        result["schema_version"] != PROFILE_MANIFEST_SCHEMA_VERSION
        or result["evidence_role"] != EVIDENCE_ROLE
        or result["state_count"] != PROFILE_STATE_COUNT
        or result["operational_arm"] != OPERATIONAL_ARM
        or result["selector_arms"] != list(PROFILE_ARMS)
        or result["arm_roles"] != ARM_ROLE_BY_ARM
    ):
        raise ValueError("V26 profiling fixed identity drifted")
    topology = _exact_mapping(
        result["execution_topology"],
        {
            "pool_generation",
            "candidate0",
            "selector_comparison",
            "post_pool_model_dp_latent_generation_mutation_regeneration",
        },
        "V26 profiling execution topology",
    )
    if topology != {
        "pool_generation": "one_same_ego_b8_forward_per_state",
        "candidate0": "frozen_row0_default_and_only_state_progression",
        "selector_comparison": "same_state_same_pool_counterfactual_only",
        "post_pool_model_dp_latent_generation_mutation_regeneration": 0,
    }:
        raise ValueError("V26 profiling same-pool topology drifted")
    result["execution_topology"] = topology
    route = _exact_mapping(
        result["route"],
        {"split", "holdout", "route_sha256", "scenario_seed", "spawn_config"},
        "V26 profiling route",
    )
    if route["split"] != "development_nonholdout" or route["holdout"] is not False:
        raise ValueError("V26 profiling rejects holdout identity")
    route["route_sha256"] = _require_sha256(route["route_sha256"], "route_sha256")
    if type(route["scenario_seed"]) is not int or route["scenario_seed"] < 0:
        raise ValueError("V26 profiling scenario_seed must be a nonnegative integer")
    if type(route["spawn_config"]) is not dict:
        raise ValueError("V26 profiling spawn_config must be an object")
    result["route"] = route
    state_plan = result["state_plan"]
    if type(state_plan) is not list or len(state_plan) != PROFILE_STATE_COUNT:
        raise ValueError("V26 profiling must retain all 20 planned state identities")
    normalized_plan = []
    for unit_index, item in enumerate(state_plan):
        row = _exact_mapping(
            item,
            {"unit_index", "planned_state_id_sha256"},
            "V26 profiling planned state",
        )
        expected_id = canonical_planned_state_identity(
            route_sha256=route["route_sha256"],
            scenario_seed=route["scenario_seed"],
            spawn_config=route["spawn_config"],
            unit_index=unit_index,
        )
        if row["unit_index"] != unit_index or row["planned_state_id_sha256"] != expected_id:
            raise ValueError("V26 profiling planned state identity drifted")
        normalized_plan.append(row)
    result["state_plan"] = normalized_plan
    latent = _exact_mapping(
        result["latent_policy"],
        {
            "candidate_seed_base",
            "same_ego_batch_size",
            "shape",
            "dtype",
            "row0_zero",
            "unique_rows_required",
        },
        "V26 profiling latent policy",
    )
    if latent != {
        "candidate_seed_base": 24001,
        "same_ego_batch_size": SAME_EGO_BATCH_SIZE,
        "shape": LATENT_SHAPE,
        "dtype": LATENT_DTYPE,
        "row0_zero": True,
        "unique_rows_required": True,
    }:
        raise ValueError("V26 profiling same-ego B8 latent policy drifted")
    result["latent_policy"] = latent
    result["camp_head"] = _require_commit(result["camp_head"], "camp_head")
    result["probe_config_sha256"] = _require_sha256(
        result["probe_config_sha256"], "probe_config_sha256"
    )
    fixed_dp = _exact_mapping(
        result["fixed_dp"], {"head", "checkpoint", "args"}, "V26 profiling fixed DP"
    )
    fixed_dp["head"] = _require_commit(fixed_dp["head"], "fixed_dp.head")
    for name in ("checkpoint", "args"):
        item = _exact_mapping(
            fixed_dp[name], {"path", "sha256"}, f"V26 profiling fixed DP {name}"
        )
        if type(item["path"]) is not str or not item["path"]:
            raise ValueError(f"V26 profiling fixed DP {name} path is required")
        item["sha256"] = _require_sha256(item["sha256"], f"fixed_dp.{name}.sha256")
        fixed_dp[name] = item
    result["fixed_dp"] = fixed_dp
    selector = _exact_mapping(
        result["selector"],
        {
            "training_root_sha256",
            "training_review_root_sha256",
            "atom_scales_sha256",
            "static9d_weights_sha256",
            "scene9d_theta_sha256",
            "static14d_weights_sha256",
            "scene14d_theta_sha256",
            "context_scaler_sha256",
        },
        "V26 profiling selector",
    )
    for key, item in selector.items():
        selector[key] = _require_sha256(item, f"selector.{key}")
    result["selector"] = selector
    return result


def _validate_forward_calls(value: Any, *, completed: bool) -> dict[str, int]:
    result = _exact_mapping(
        value,
        {
            "model_call_count_before",
            "model_call_count_after",
            "model_call_delta",
            "primary_forward_count",
            "sequential_forward_count",
            "post_pool_model_forward_count",
            "post_pool_dp_forward_count",
            "post_pool_latent_replacement_count",
            "post_pool_candidate_generation_count",
            "candidate_pool_mutation_count",
            "trajectory_regeneration_count",
        },
        "V26 profiling forward calls",
    )
    if any(type(item) is not int or item < 0 for item in result.values()):
        raise ValueError("V26 profiling forward counts must be nonnegative integers")
    if result["model_call_count_after"] - result["model_call_count_before"] != result["model_call_delta"]:
        raise ValueError("V26 profiling model call delta drifted")
    forbidden = (
        "sequential_forward_count",
        "post_pool_model_forward_count",
        "post_pool_dp_forward_count",
        "post_pool_latent_replacement_count",
        "post_pool_candidate_generation_count",
        "candidate_pool_mutation_count",
        "trajectory_regeneration_count",
    )
    if any(result[name] != 0 for name in forbidden):
        raise ValueError("V26 profiling rejects extra or post-pool invocation paths")
    if completed and (
        result["model_call_delta"] != 1 or result["primary_forward_count"] != 1
    ):
        raise ValueError("V26 profiling completed state requires exactly one B8 forward")
    return {key: int(item) for key, item in result.items()}


def _validate_tensor_metadata(value: Any) -> dict[str, dict[str, Any]]:
    if type(value) is not dict or not value:
        raise ValueError("V26 profiling input tensor metadata is required")
    result: dict[str, dict[str, Any]] = {}
    for key, item in value.items():
        if type(key) is not str or not key:
            raise ValueError("V26 profiling input tensor name is invalid")
        row = _exact_mapping(item, {"shape", "dtype", "finite"}, "V26 profiling tensor")
        if (
            type(row["shape"]) is not list
            or not row["shape"]
            or any(type(size) is not int or size <= 0 for size in row["shape"])
            or type(row["dtype"]) is not str
            or not row["dtype"]
            or row["finite"] is not True
        ):
            raise ValueError("V26 profiling input tensor metadata drifted")
        result[key] = row
    return result


def _validate_mask(value: Any, name: str) -> list[bool]:
    if type(value) is not list or len(value) != SAME_EGO_BATCH_SIZE or any(type(item) is not bool for item in value):
        raise ValueError(f"{name} must be a native B8 boolean mask")
    return list(value)


def _validate_phase_timings(value: Any) -> dict[str, dict[str, Any]]:
    if type(value) is not dict or set(value) != set(ATOM_PHASE_NAMES):
        raise ValueError("V26 profiling atom phase receipt field set drifted")
    result: dict[str, dict[str, Any]] = {}
    for name in ATOM_PHASE_NAMES:
        row = _exact_mapping(value[name], {"status", "elapsed_ns"}, "V26 profiling atom phase")
        if row["status"] not in {"measured", "not_available"}:
            raise ValueError("V26 profiling atom phase status drifted")
        if row["status"] == "measured" and (type(row["elapsed_ns"]) is not int or row["elapsed_ns"] < 0):
            raise ValueError("V26 profiling measured atom phase requires elapsed_ns")
        if row["status"] == "not_available" and row["elapsed_ns"] is not None:
            raise ValueError("V26 profiling unavailable atom phase must be null")
        result[name] = row
    return result


def _validate_arm(
    value: Any, *, arm_id: str, pool_rows: list[str], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    arm = _exact_mapping(
        value,
        {
            "arm_id",
            "atom_set",
            "active_atom_indices",
            "weights_sha256",
            "scoring_weights_sha256",
            "weight_parameter_sha256",
            "status",
            "failure_reason",
            "selected_index",
            "selected_row_sha256",
            "scores",
            "physical_feasible_mask",
            "source_valid_mask",
            "eligible_count",
            "margin_best_vs_runner_up",
            "exact_tie_set",
            "weight_input_source_complete",
        },
        f"V26 profiling {arm_id} arm",
    )
    if (
        arm["arm_id"] != arm_id
        or arm["atom_set"] != ATOM_SET_BY_ARM[arm_id]
        or arm["active_atom_indices"] != ACTIVE_ATOM_INDICES_BY_ARM[arm_id]
    ):
        raise ValueError("V26 profiling atom-set arm identity drifted")
    expected_parameter = {
        "Static9D": manifest["selector"]["static9d_weights_sha256"],
        "Scene9D": manifest["selector"]["scene9d_theta_sha256"],
        "Static14D": manifest["selector"]["static14d_weights_sha256"],
        "Scene14D": manifest["selector"]["scene14d_theta_sha256"],
    }.get(arm_id)
    for name in ("weights_sha256", "scoring_weights_sha256", "weight_parameter_sha256"):
        if arm_id == OPERATIONAL_ARM:
            if arm[name] is not None:
                raise ValueError("V26 profiling candidate0 must not carry CAMP weights")
        else:
            arm[name] = _require_sha256(arm[name], f"{arm_id}.{name}")
    if arm_id != OPERATIONAL_ARM and arm["weight_parameter_sha256"] != expected_parameter:
        raise ValueError("V26 profiling arm parameter identity drifted")
    if arm_id.startswith("Static") and arm["weights_sha256"] != expected_parameter:
        raise ValueError("V26 profiling static runtime weight identity drifted")
    if arm["status"] not in {"ok", "typed_failure"}:
        raise ValueError("V26 profiling selector status drifted")
    arm["physical_feasible_mask"] = _validate_mask(
        arm["physical_feasible_mask"], f"{arm_id}.physical_feasible_mask"
    )
    arm["source_valid_mask"] = _validate_mask(
        arm["source_valid_mask"], f"{arm_id}.source_valid_mask"
    )
    eligible = int(sum(arm["source_valid_mask"]))
    if arm["eligible_count"] != eligible:
        raise ValueError("V26 profiling eligible count drifted")
    if arm["scores"] is not None:
        if (
            type(arm["scores"]) is not list
            or len(arm["scores"]) != SAME_EGO_BATCH_SIZE
            or any(type(item) not in {int, float} or not math.isfinite(float(item)) for item in arm["scores"])
        ):
            raise ValueError("V26 profiling score receipt drifted")
        arm["scores"] = [float(item) for item in arm["scores"]]
    if arm["margin_best_vs_runner_up"] is not None:
        if type(arm["margin_best_vs_runner_up"]) not in {int, float} or not math.isfinite(float(arm["margin_best_vs_runner_up"])):
            raise ValueError("V26 profiling margin must be finite or null")
        arm["margin_best_vs_runner_up"] = float(arm["margin_best_vs_runner_up"])
    if arm["status"] == "ok":
        if type(arm["selected_index"]) is not int or not 0 <= arm["selected_index"] < SAME_EGO_BATCH_SIZE:
            raise ValueError("V26 profiling selected index drifted")
        arm["selected_row_sha256"] = _require_sha256(
            arm["selected_row_sha256"], f"{arm_id}.selected_row_sha256"
        )
        if arm["selected_row_sha256"] != pool_rows[arm["selected_index"]]:
            raise ValueError("V26 profiling selection escaped its frozen pool")
        if arm["failure_reason"] is not None:
            raise ValueError("V26 profiling successful selector cannot carry failure")
        if type(arm["exact_tie_set"]) is not list or not arm["exact_tie_set"]:
            raise ValueError("V26 profiling successful selector tie receipt is required")
        if any(type(index) is not int or index not in range(SAME_EGO_BATCH_SIZE) for index in arm["exact_tie_set"]):
            raise ValueError("V26 profiling tie receipt index drifted")
    else:
        if (
            arm["failure_reason"] is None
            or type(arm["failure_reason"]) is not str
            or not arm["failure_reason"]
            or arm["selected_index"] is not None
            or arm["selected_row_sha256"] is not None
            or arm["exact_tie_set"] is not None
        ):
            raise ValueError("V26 profiling typed selector failure drifted")
    context = arm["weight_input_source_complete"]
    if arm_id.startswith("Scene"):
        if type(context) is not dict or not context or any(type(key) is not str or type(item) is not bool for key, item in context.items()):
            raise ValueError("V26 profiling Scene arm context coverage is required")
        arm["weight_input_source_complete"] = dict(context)
    elif context is not None:
        raise ValueError("V26 profiling Static/candidate0 arm must not carry scene coverage")
    return arm


def _validate_completed_unit(value: Any, manifest: Mapping[str, Any]) -> dict[str, Any]:
    unit = _exact_mapping(
        value,
        {
            "unit_index",
            "planned_state_id_sha256",
            "state_sha256",
            "input",
            "latent",
            "candidate_pool",
            "forward_calls",
            "arms",
            "comparison",
            "atom_phase_timings",
            "simulator",
            "terminal",
        },
        "V26 profiling completed unit",
    )
    index = unit["unit_index"]
    if type(index) is not int or not 0 <= index < PROFILE_STATE_COUNT:
        raise ValueError("V26 profiling unit index drifted")
    if unit["planned_state_id_sha256"] != manifest["state_plan"][index]["planned_state_id_sha256"]:
        raise ValueError("V26 profiling planned state binding drifted")
    unit["state_sha256"] = _require_sha256(unit["state_sha256"], "unit.state_sha256")
    input_row = _exact_mapping(
        unit["input"],
        {
            "source_input_sha256",
            "expanded_input_sha256",
            "same_ego_batch_size",
            "nonlatent_rows_identical",
            "tensor_metadata",
        },
        "V26 profiling input",
    )
    input_row["source_input_sha256"] = _require_sha256(input_row["source_input_sha256"], "source_input_sha256")
    input_row["expanded_input_sha256"] = _require_sha256(input_row["expanded_input_sha256"], "expanded_input_sha256")
    if input_row["same_ego_batch_size"] != SAME_EGO_BATCH_SIZE or input_row["nonlatent_rows_identical"] is not True:
        raise ValueError("V26 profiling same-ego input topology drifted")
    input_row["tensor_metadata"] = _validate_tensor_metadata(input_row["tensor_metadata"])
    unit["input"] = input_row
    latent = _exact_mapping(
        unit["latent"],
        {"seed", "shape", "dtype", "finite", "tensor_sha256", "row_sha256", "row0_zero"},
        "V26 profiling latent",
    )
    if (
        type(latent["seed"]) is not int
        or latent["shape"] != manifest["latent_policy"]["shape"]
        or latent["dtype"] != manifest["latent_policy"]["dtype"]
        or latent["finite"] is not True
        or latent["row0_zero"] is not True
    ):
        raise ValueError("V26 profiling latent receipt drifted")
    latent["tensor_sha256"] = _require_sha256(latent["tensor_sha256"], "latent.tensor_sha256")
    if type(latent["row_sha256"]) is not list or len(latent["row_sha256"]) != SAME_EGO_BATCH_SIZE:
        raise ValueError("V26 profiling latent row topology drifted")
    latent["row_sha256"] = [_require_sha256(item, "latent.row_sha256") for item in latent["row_sha256"]]
    if len(set(latent["row_sha256"])) != SAME_EGO_BATCH_SIZE:
        raise ValueError("V26 profiling latent rows must remain unique")
    unit["latent"] = latent
    pool = _exact_mapping(
        unit["candidate_pool"],
        {"shape", "dtype", "finite", "pool_sha256", "row_sha256", "candidate0"},
        "V26 profiling candidate pool",
    )
    if (
        type(pool["shape"]) is not list
        or len(pool["shape"]) != 3
        or pool["shape"][0] != SAME_EGO_BATCH_SIZE
        or any(type(size) is not int or size <= 0 for size in pool["shape"])
        or type(pool["dtype"]) is not str
        or not pool["dtype"]
        or pool["finite"] is not True
    ):
        raise ValueError("V26 profiling candidate pool B8 metadata drifted")
    pool["pool_sha256"] = _require_sha256(pool["pool_sha256"], "pool.pool_sha256")
    if type(pool["row_sha256"]) is not list or len(pool["row_sha256"]) != SAME_EGO_BATCH_SIZE:
        raise ValueError("V26 profiling candidate row topology drifted")
    pool["row_sha256"] = [_require_sha256(item, "pool.row_sha256") for item in pool["row_sha256"]]
    if len(set(pool["row_sha256"])) != SAME_EGO_BATCH_SIZE:
        raise ValueError("V26 profiling candidate rows must remain diverse")
    candidate0 = _exact_mapping(
        pool["candidate0"], {"index", "row_sha256", "default_output_sha256"}, "V26 profiling candidate0"
    )
    if candidate0["index"] != 0:
        raise ValueError("V26 profiling candidate0 must be row0")
    candidate0["row_sha256"] = _require_sha256(candidate0["row_sha256"], "candidate0.row_sha256")
    candidate0["default_output_sha256"] = _require_sha256(candidate0["default_output_sha256"], "candidate0.default_output_sha256")
    if candidate0["row_sha256"] != pool["row_sha256"][0] or candidate0["default_output_sha256"] != pool["row_sha256"][0]:
        raise ValueError("V26 profiling default output must bind frozen candidate0")
    pool["candidate0"] = candidate0
    unit["candidate_pool"] = pool
    unit["forward_calls"] = _validate_forward_calls(unit["forward_calls"], completed=True)
    arms = unit["arms"]
    if type(arms) is not dict or set(arms) != set(PROFILE_ARMS):
        raise ValueError("V26 profiling five-arm inventory drifted")
    normalized_arms = {
        arm_id: _validate_arm(
            arms[arm_id],
            arm_id=arm_id,
            pool_rows=pool["row_sha256"],
            manifest=manifest,
        )
        for arm_id in PROFILE_ARMS
    }
    baseline = normalized_arms[OPERATIONAL_ARM]
    if baseline["status"] != "ok" or baseline["selected_index"] != 0 or baseline["selected_row_sha256"] != pool["row_sha256"][0]:
        raise ValueError("V26 profiling candidate0 arm must bind frozen row0")
    reference_masks = (
        baseline["physical_feasible_mask"],
        baseline["source_valid_mask"],
    )
    for arm in normalized_arms.values():
        if (arm["physical_feasible_mask"], arm["source_valid_mask"]) != reference_masks:
            raise ValueError("V26 profiling arms must consume the same frozen masks")
    unit["arms"] = normalized_arms
    comparison = _exact_mapping(
        unit["comparison"],
        {
            "selection_disagrees_with_candidate0",
            "static9d_vs_static14d_flip",
            "scene9d_vs_scene14d_flip",
        },
        "V26 profiling comparison",
    )
    disagreements = comparison["selection_disagrees_with_candidate0"]
    if type(disagreements) is not dict or set(disagreements) != {"Static9D", "Scene9D", "Static14D", "Scene14D"}:
        raise ValueError("V26 profiling selection disagreement fields drifted")
    for arm_id, value in disagreements.items():
        expected = (
            None
            if normalized_arms[arm_id]["status"] != "ok"
            else normalized_arms[arm_id]["selected_index"] != 0
        )
        if value is not expected:
            raise ValueError("V26 profiling candidate0 disagreement drifted")
    for left, right, key in (
        ("Static9D", "Static14D", "static9d_vs_static14d_flip"),
        ("Scene9D", "Scene14D", "scene9d_vs_scene14d_flip"),
    ):
        expected = (
            None
            if normalized_arms[left]["status"] != "ok" or normalized_arms[right]["status"] != "ok"
            else normalized_arms[left]["selected_index"] != normalized_arms[right]["selected_index"]
        )
        if comparison[key] is not expected:
            raise ValueError("V26 profiling 9D-vs-14D flip drifted")
    unit["comparison"] = comparison
    unit["atom_phase_timings"] = _validate_phase_timings(unit["atom_phase_timings"])
    simulator = _exact_mapping(
        unit["simulator"], {"operational_arm", "selected_index", "selected_row_sha256"}, "V26 profiling simulator")
    if simulator["operational_arm"] != OPERATIONAL_ARM or simulator["selected_index"] != 0:
        raise ValueError("V26 profiling simulator must advance candidate0 only")
    simulator["selected_row_sha256"] = _require_sha256(simulator["selected_row_sha256"], "simulator.selected_row_sha256")
    if simulator["selected_row_sha256"] != pool["row_sha256"][0]:
        raise ValueError("V26 profiling simulator row must bind candidate0")
    unit["simulator"] = simulator
    terminal = _exact_mapping(unit["terminal"], {"status", "failure_class", "failure_reason"}, "V26 profiling terminal")
    if terminal != {"status": "complete", "failure_class": None, "failure_reason": None}:
        raise ValueError("V26 profiling completed terminal drifted")
    unit["terminal"] = terminal
    return unit


def _validate_noncomplete_unit(value: Any, manifest: Mapping[str, Any], *, status: str) -> dict[str, Any]:
    unit = _exact_mapping(
        value,
        {
            "unit_index",
            "planned_state_id_sha256",
            "state_sha256",
            "input",
            "latent",
            "candidate_pool",
            "forward_calls",
            "arms",
            "comparison",
            "atom_phase_timings",
            "simulator",
            "terminal",
        },
        f"V26 profiling {status} unit",
    )
    index = unit["unit_index"]
    if type(index) is not int or not 0 <= index < PROFILE_STATE_COUNT or unit["planned_state_id_sha256"] != manifest["state_plan"][index]["planned_state_id_sha256"]:
        raise ValueError("V26 profiling noncomplete state identity drifted")
    if unit["state_sha256"] is not None:
        unit["state_sha256"] = _require_sha256(unit["state_sha256"], "failed.state_sha256")
    for name in ("input", "latent", "candidate_pool", "arms", "comparison", "atom_phase_timings", "simulator"):
        if unit[name] is not None:
            raise ValueError(f"V26 profiling {status} unit must not claim a completed selector result")
    unit["forward_calls"] = _validate_forward_calls(unit["forward_calls"], completed=False)
    terminal = _exact_mapping(unit["terminal"], {"status", "failure_class", "failure_reason"}, "V26 profiling noncomplete terminal")
    if status == "typed_failure":
        if type(terminal["failure_class"]) is not str or not terminal["failure_class"] or type(terminal["failure_reason"]) is not str or not terminal["failure_reason"]:
            raise ValueError("V26 profiling typed failure terminal drifted")
    elif terminal["failure_class"] is not None or terminal["failure_reason"] is not None:
        raise ValueError("V26 profiling unattempted terminal must be null")
    if terminal["status"] != status:
        raise ValueError("V26 profiling terminal status drifted")
    unit["terminal"] = terminal
    return unit


def _validate_unit(value: Any, manifest: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or type(value.get("terminal")) is not dict:
        raise ValueError("V26 profiling unit terminal is required")
    status = value["terminal"].get("status")
    if status == "complete":
        return _validate_completed_unit(value, manifest)
    if status in {"typed_failure", "unattempted"}:
        return _validate_noncomplete_unit(value, manifest, status=status)
    raise ValueError("V26 profiling unit terminal status is invalid")


def _distribution(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"observed_count": 0, "minimum": None, "median": None, "maximum": None}
    return {
        "observed_count": len(values),
        "minimum": min(values),
        "median": float(statistics.median(values)),
        "maximum": max(values),
    }


def build_descriptive_summary(units: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate only descriptive masks, margins, choices, and inputs."""

    completed = [unit for unit in units if unit["terminal"]["status"] == "complete"]
    per_arm: dict[str, Any] = {}
    for arm_id in PROFILE_ARMS:
        rows = [unit["arms"][arm_id] for unit in completed]
        status_counts = {"ok": 0, "typed_failure": 0}
        selected_index_counts = {str(index): 0 for index in range(SAME_EGO_BATCH_SIZE)}
        margins: list[float] = []
        disagreement_count = 0
        disagreement_observed = 0
        for row, unit in zip(rows, completed):
            status_counts[row["status"]] += 1
            if row["status"] == "ok":
                selected_index_counts[str(row["selected_index"])] += 1
                if row["margin_best_vs_runner_up"] is not None:
                    margins.append(float(row["margin_best_vs_runner_up"]))
            if arm_id != OPERATIONAL_ARM:
                disagreement = unit["comparison"]["selection_disagrees_with_candidate0"][arm_id]
                if disagreement is not None:
                    disagreement_observed += 1
                    disagreement_count += int(disagreement)
        per_arm[arm_id] = {
            "selector_status_counts": status_counts,
            "selected_index_counts": selected_index_counts,
            "margin_best_vs_runner_up": _distribution(margins),
            "selection_disagrees_with_candidate0": {
                "observed_count": disagreement_observed,
                "count": disagreement_count,
            },
        }
    source_counts = [sum(unit["arms"][OPERATIONAL_ARM]["source_valid_mask"]) for unit in completed]
    physical_counts = [sum(unit["arms"][OPERATIONAL_ARM]["physical_feasible_mask"]) for unit in completed]
    scene_coverage: dict[str, dict[str, int]] = {}
    for unit in completed:
        for arm_id in ("Scene9D", "Scene14D"):
            context = unit["arms"][arm_id]["weight_input_source_complete"]
            for name, present in context.items():
                row = scene_coverage.setdefault(name, {"available": 0, "unavailable": 0})
                row["available" if present else "unavailable"] += 1
    phase_timings: dict[str, list[float]] = {name: [] for name in ATOM_PHASE_NAMES}
    for unit in completed:
        for name, row in unit["atom_phase_timings"].items():
            if row["status"] == "measured":
                phase_timings[name].append(float(row["elapsed_ns"]) / 1e6)
    flip_counts = {}
    for key in ("static9d_vs_static14d_flip", "scene9d_vs_scene14d_flip"):
        observed = [unit["comparison"][key] for unit in completed if unit["comparison"][key] is not None]
        flip_counts[key] = {"observed_pair_count": len(observed), "flip_count": int(sum(observed))}
    return {
        "description_scope": "descriptive profiling only; no threshold, support/OOD, stability, safety, benefit, or training conclusion",
        "state_execution": {"completed_state_count": len(completed), "operational_state_progression": "candidate0_row0_only"},
        "pool_mask_and_eligibility": {
            "source_valid_candidate_count": _distribution([float(value) for value in source_counts]),
            "physical_feasible_candidate_count": _distribution([float(value) for value in physical_counts]),
        },
        "selector_descriptions": per_arm,
        "nine_d_vs_fourteen_d_selection_flips": flip_counts,
        "weight_and_atom_input_coverage": {"scene_context_source_complete": scene_coverage},
        "atom_phase_timings_ms": {name: _distribution(values) for name, values in phase_timings.items()},
    }


def build_development_profiling_receipt(
    *, manifest: Mapping[str, Any], units: list[Mapping[str, Any]]
) -> dict[str, Any]:
    normalized_manifest = validate_development_profiling_manifest(manifest)
    if type(units) is not list or len(units) != PROFILE_STATE_COUNT:
        raise ValueError("V26 profiling must retain the full 20-state denominator")
    normalized_units = [_validate_unit(unit, normalized_manifest) for unit in units]
    if [unit["unit_index"] for unit in normalized_units] != list(range(PROFILE_STATE_COUNT)):
        raise ValueError("V26 profiling units must remain in deterministic state-plan order")
    denominator = {
        "planned": PROFILE_STATE_COUNT,
        "complete": sum(unit["terminal"]["status"] == "complete" for unit in normalized_units),
        "failed": sum(unit["terminal"]["status"] == "typed_failure" for unit in normalized_units),
        "unattempted": sum(unit["terminal"]["status"] == "unattempted" for unit in normalized_units),
    }
    return validate_development_profiling_receipt(
        {
            "schema_version": PROFILE_RECEIPT_SCHEMA_VERSION,
            "evidence_role": EVIDENCE_ROLE,
            "manifest": normalized_manifest,
            "denominator": denominator,
            "units": normalized_units,
            "descriptive_summary": build_descriptive_summary(normalized_units),
        }
    )


def validate_development_profiling_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    expected = {"schema_version", "evidence_role", "manifest", "denominator", "units", "descriptive_summary"}
    if set(result) != expected:
        raise ValueError("V26 profiling receipt field set drifted")
    if result["schema_version"] != PROFILE_RECEIPT_SCHEMA_VERSION or result["evidence_role"] != EVIDENCE_ROLE:
        raise ValueError("V26 profiling receipt identity drifted")
    result["manifest"] = validate_development_profiling_manifest(result["manifest"])
    if type(result["units"]) is not list or len(result["units"]) != PROFILE_STATE_COUNT:
        raise ValueError("V26 profiling receipt denominator unit count drifted")
    result["units"] = [_validate_unit(unit, result["manifest"]) for unit in result["units"]]
    if [unit["unit_index"] for unit in result["units"]] != list(range(PROFILE_STATE_COUNT)):
        raise ValueError("V26 profiling receipt unit ordering drifted")
    denominator = _exact_mapping(
        result["denominator"], {"planned", "complete", "failed", "unattempted"}, "V26 profiling denominator"
    )
    if any(type(item) is not int or item < 0 for item in denominator.values()) or denominator["planned"] != PROFILE_STATE_COUNT:
        raise ValueError("V26 profiling denominator drifted")
    expected_denominator = {
        "planned": PROFILE_STATE_COUNT,
        "complete": sum(unit["terminal"]["status"] == "complete" for unit in result["units"]),
        "failed": sum(unit["terminal"]["status"] == "typed_failure" for unit in result["units"]),
        "unattempted": sum(unit["terminal"]["status"] == "unattempted" for unit in result["units"]),
    }
    if denominator != expected_denominator or sum(denominator.values()) != PROFILE_STATE_COUNT * 2:
        raise ValueError("V26 profiling terminal/denominator drifted")
    result["denominator"] = denominator
    expected_summary = build_descriptive_summary(result["units"])
    if result["descriptive_summary"] != expected_summary:
        raise ValueError("V26 profiling descriptive summary drifted")
    result["descriptive_summary"] = expected_summary
    return result
