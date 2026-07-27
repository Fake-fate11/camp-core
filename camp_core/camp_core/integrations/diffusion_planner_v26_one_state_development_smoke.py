"""Minimal, nonholdout one-state B8 smoke contract for the V26 paper experiment."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping

from camp_core.integrations.diffusion_planner_v26_target_bounded_surface import (
    PRODUCTION_SURFACE_ID,
    production_surface_manifest,
    validate_production_surface_manifest,
)


SMOKE_MANIFEST_SCHEMA_VERSION = "camp_dp_v26_one_state_development_smoke_manifest_v1"
SMOKE_RECEIPT_SCHEMA_VERSION = "camp_dp_v26_one_state_development_smoke_receipt_v1"
EVIDENCE_ROLE = "development_nonholdout_smoke"
SMOKE_ARM = "Static14D"
SMOKE_STATE_COUNT = 1
SAME_EGO_BATCH_SIZE = 8
LATENT_SHAPE = [8, 321, 81, 4]
LATENT_DTYPE = "float32"


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
        raise ValueError(f"{name} must be a full 40-character git commit")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be hexadecimal") from exc
    return value


def _require_exact_keys(value: Any, expected: set[str], name: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise ValueError(f"{name} field set drifted")
    return dict(value)


def canonical_state_identity(
    *, route_sha256: str, scenario_seed: int, spawn_config: Mapping[str, Any]
) -> str:
    """Bind the development state identity without reading any outcome."""

    _require_sha256(route_sha256, "route_sha256")
    if type(scenario_seed) is not int or scenario_seed < 0:
        raise ValueError("scenario_seed must be a nonnegative integer")
    if type(spawn_config) is not dict:
        raise ValueError("spawn_config must be an object")
    payload = json.dumps(
        {
            "route_sha256": route_sha256,
            "scenario_seed": scenario_seed,
            "spawn_config": spawn_config,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_development_smoke_manifest(
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
    static14d_weights_sha256: str,
) -> dict[str, Any]:
    """Create the exact, outcome-free manifest for one Static14D invocation."""

    return validate_development_smoke_manifest(
        {
            "schema_version": SMOKE_MANIFEST_SCHEMA_VERSION,
            "evidence_role": EVIDENCE_ROLE,
            "state_count": SMOKE_STATE_COUNT,
            "operational_arm": SMOKE_ARM,
            "production_surface_manifest": production_surface_manifest(
                production_surface_id=PRODUCTION_SURFACE_ID,
                options={
                    "adaptation_diagnostics": False,
                    "sequential_forward_enabled": False,
                    "replay_extra_forward_enabled": False,
                    "guidance_policy": "disabled",
                    "evaluate_all_arms": False,
                },
            ),
            "state": {
                "split": "development_nonholdout",
                "holdout": False,
                "state_id_sha256": canonical_state_identity(
                    route_sha256=route_sha256,
                    scenario_seed=scenario_seed,
                    spawn_config=spawn_config,
                ),
                "route_sha256": route_sha256,
                "scenario_seed": scenario_seed,
            },
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
                "static14d_weights_sha256": static14d_weights_sha256,
            },
        }
    )


def validate_development_smoke_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    expected = {
        "schema_version",
        "evidence_role",
        "state_count",
        "operational_arm",
        "production_surface_manifest",
        "state",
        "latent_policy",
        "camp_head",
        "probe_config_sha256",
        "fixed_dp",
        "selector",
    }
    if set(result) != expected:
        raise ValueError("V26 one-state smoke manifest field set drifted")
    if result["schema_version"] != SMOKE_MANIFEST_SCHEMA_VERSION:
        raise ValueError("V26 one-state smoke manifest schema drifted")
    if result["evidence_role"] != EVIDENCE_ROLE:
        raise ValueError("V26 one-state smoke evidence role drifted")
    if result["state_count"] != SMOKE_STATE_COUNT:
        raise ValueError("V26 smoke requires exactly one planned state")
    if result["operational_arm"] != SMOKE_ARM:
        raise ValueError("V26 smoke requires the explicit Static14D arm")
    result["production_surface_manifest"] = validate_production_surface_manifest(
        result["production_surface_manifest"]
    )
    state = _require_exact_keys(
        result["state"],
        {"split", "holdout", "state_id_sha256", "route_sha256", "scenario_seed"},
        "V26 smoke state",
    )
    if state["split"] != "development_nonholdout" or state["holdout"] is not False:
        raise ValueError("V26 smoke rejects holdout identity")
    state["state_id_sha256"] = _require_sha256(
        state["state_id_sha256"], "state_id_sha256"
    )
    state["route_sha256"] = _require_sha256(state["route_sha256"], "route_sha256")
    if type(state["scenario_seed"]) is not int or state["scenario_seed"] < 0:
        raise ValueError("V26 smoke scenario_seed must be a nonnegative integer")
    result["state"] = state
    latent = _require_exact_keys(
        result["latent_policy"],
        {
            "candidate_seed_base",
            "same_ego_batch_size",
            "shape",
            "dtype",
            "row0_zero",
            "unique_rows_required",
        },
        "V26 smoke latent policy",
    )
    if (
        latent["candidate_seed_base"] != 24001
        or latent["same_ego_batch_size"] != SAME_EGO_BATCH_SIZE
        or latent["shape"] != LATENT_SHAPE
        or latent["dtype"] != LATENT_DTYPE
        or latent["row0_zero"] is not True
        or latent["unique_rows_required"] is not True
    ):
        raise ValueError("V26 smoke same-ego B8 latent policy drifted")
    result["latent_policy"] = latent
    result["camp_head"] = _require_commit(result["camp_head"], "camp_head")
    result["probe_config_sha256"] = _require_sha256(
        result["probe_config_sha256"], "probe_config_sha256"
    )
    fixed_dp = _require_exact_keys(
        result["fixed_dp"], {"head", "checkpoint", "args"}, "V26 smoke fixed DP"
    )
    fixed_dp["head"] = _require_commit(fixed_dp["head"], "fixed_dp.head")
    for name in ("checkpoint", "args"):
        item = _require_exact_keys(
            fixed_dp[name], {"path", "sha256"}, f"V26 smoke fixed DP {name}"
        )
        if type(item["path"]) is not str or not item["path"]:
            raise ValueError(f"V26 smoke fixed DP {name} path is required")
        item["sha256"] = _require_sha256(
            item["sha256"], f"fixed_dp.{name}.sha256"
        )
        fixed_dp[name] = item
    result["fixed_dp"] = fixed_dp
    selector = _require_exact_keys(
        result["selector"],
        {
            "training_root_sha256",
            "training_review_root_sha256",
            "atom_scales_sha256",
            "static14d_weights_sha256",
        },
        "V26 smoke selector",
    )
    for key, item in selector.items():
        selector[key] = _require_sha256(item, f"selector.{key}")
    result["selector"] = selector
    return result


def _validate_forward_calls(value: Any, *, completed: bool) -> dict[str, int]:
    result = _require_exact_keys(
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
        "V26 smoke forward calls",
    )
    if any(type(item) is not int or item < 0 for item in result.values()):
        raise ValueError("V26 smoke forward call counts must be nonnegative integers")
    if result["model_call_count_after"] - result["model_call_count_before"] != result[
        "model_call_delta"
    ]:
        raise ValueError("V26 smoke model call delta drifted")
    if completed:
        if any(
            result[name] != 0
            for name in (
                "sequential_forward_count",
                "post_pool_model_forward_count",
                "post_pool_dp_forward_count",
                "post_pool_latent_replacement_count",
                "post_pool_candidate_generation_count",
                "candidate_pool_mutation_count",
                "trajectory_regeneration_count",
            )
        ):
            raise ValueError("V26 smoke rejects extra or post-pool invocation paths")
        if (
            result["model_call_count_before"] != 0
            or result["model_call_count_after"] != 1
            or result["model_call_delta"] != 1
            or result["primary_forward_count"] != 1
        ):
            raise ValueError("V26 smoke completed unit requires exactly one B8 forward")
    return {key: int(item) for key, item in result.items()}


def _validate_tensor_metadata(value: Any) -> dict[str, dict[str, Any]]:
    if type(value) is not dict or not value:
        raise ValueError("V26 smoke input tensor metadata is required")
    result: dict[str, dict[str, Any]] = {}
    for key, item in value.items():
        if type(key) is not str or not key:
            raise ValueError("V26 smoke input tensor name is invalid")
        row = _require_exact_keys(item, {"shape", "dtype", "finite"}, "V26 smoke tensor")
        if (
            type(row["shape"]) is not list
            or not row["shape"]
            or any(type(size) is not int or size <= 0 for size in row["shape"])
            or type(row["dtype"]) is not str
            or not row["dtype"]
            or row["finite"] is not True
        ):
            raise ValueError("V26 smoke input tensor metadata drifted")
        result[key] = row
    return result


def _validate_completed_unit(value: Any, manifest: Mapping[str, Any]) -> dict[str, Any]:
    unit = _require_exact_keys(
        value,
        {
            "unit_index",
            "operational_arm",
            "state_sha256",
            "input",
            "latent",
            "candidate_pool",
            "forward_calls",
            "selection",
            "simulator",
            "terminal",
        },
        "V26 smoke completed unit",
    )
    if unit["unit_index"] != 0 or unit["operational_arm"] != SMOKE_ARM:
        raise ValueError("V26 smoke unit identity drifted")
    unit["state_sha256"] = _require_sha256(unit["state_sha256"], "unit.state_sha256")
    input_row = _require_exact_keys(
        unit["input"],
        {
            "source_input_sha256",
            "expanded_input_sha256",
            "same_ego_batch_size",
            "nonlatent_rows_identical",
            "tensor_metadata",
        },
        "V26 smoke input",
    )
    input_row["source_input_sha256"] = _require_sha256(
        input_row["source_input_sha256"], "source_input_sha256"
    )
    input_row["expanded_input_sha256"] = _require_sha256(
        input_row["expanded_input_sha256"], "expanded_input_sha256"
    )
    if (
        input_row["same_ego_batch_size"] != SAME_EGO_BATCH_SIZE
        or input_row["nonlatent_rows_identical"] is not True
    ):
        raise ValueError("V26 smoke same-ego input contract drifted")
    input_row["tensor_metadata"] = _validate_tensor_metadata(
        input_row["tensor_metadata"]
    )
    unit["input"] = input_row
    latent = _require_exact_keys(
        unit["latent"],
        {"seed", "shape", "dtype", "finite", "tensor_sha256", "row_sha256", "row0_zero"},
        "V26 smoke latent",
    )
    if (
        type(latent["seed"]) is not int
        or latent["shape"] != manifest["latent_policy"]["shape"]
        or latent["dtype"] != manifest["latent_policy"]["dtype"]
        or latent["finite"] is not True
        or latent["row0_zero"] is not True
    ):
        raise ValueError("V26 smoke latent receipt drifted")
    latent["tensor_sha256"] = _require_sha256(latent["tensor_sha256"], "latent.tensor_sha256")
    if (
        type(latent["row_sha256"]) is not list
        or len(latent["row_sha256"]) != SAME_EGO_BATCH_SIZE
    ):
        raise ValueError("V26 smoke latent row topology drifted")
    latent["row_sha256"] = [
        _require_sha256(item, "latent.row_sha256") for item in latent["row_sha256"]
    ]
    if len(set(latent["row_sha256"])) != SAME_EGO_BATCH_SIZE:
        raise ValueError("V26 smoke latent rows must remain unique")
    unit["latent"] = latent
    pool = _require_exact_keys(
        unit["candidate_pool"],
        {"shape", "dtype", "finite", "pool_sha256", "row_sha256", "candidate0"},
        "V26 smoke candidate pool",
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
        raise ValueError("V26 smoke candidate pool B8 metadata drifted")
    pool["pool_sha256"] = _require_sha256(pool["pool_sha256"], "pool.pool_sha256")
    if type(pool["row_sha256"]) is not list or len(pool["row_sha256"]) != SAME_EGO_BATCH_SIZE:
        raise ValueError("V26 smoke candidate row topology drifted")
    pool["row_sha256"] = [
        _require_sha256(item, "pool.row_sha256") for item in pool["row_sha256"]
    ]
    if len(set(pool["row_sha256"])) != SAME_EGO_BATCH_SIZE:
        raise ValueError("V26 smoke candidate rows must remain diverse")
    candidate0 = _require_exact_keys(
        pool["candidate0"], {"index", "row_sha256", "default_output_sha256"}, "V26 smoke candidate0"
    )
    if candidate0["index"] != 0:
        raise ValueError("V26 smoke candidate0 must be frozen row0")
    candidate0["row_sha256"] = _require_sha256(
        candidate0["row_sha256"], "candidate0.row_sha256"
    )
    candidate0["default_output_sha256"] = _require_sha256(
        candidate0["default_output_sha256"], "candidate0.default_output_sha256"
    )
    if (
        candidate0["row_sha256"] != pool["row_sha256"][0]
        or candidate0["default_output_sha256"] != pool["row_sha256"][0]
    ):
        raise ValueError("V26 smoke default output must bind frozen candidate0")
    pool["candidate0"] = candidate0
    unit["candidate_pool"] = pool
    unit["forward_calls"] = _validate_forward_calls(
        unit["forward_calls"], completed=True
    )
    selection = _require_exact_keys(
        unit["selection"], {"selected_index", "selected_row_sha256"}, "V26 smoke selection"
    )
    if type(selection["selected_index"]) is not int or not 0 <= selection["selected_index"] < SAME_EGO_BATCH_SIZE:
        raise ValueError("V26 smoke selected index drifted")
    selection["selected_row_sha256"] = _require_sha256(
        selection["selected_row_sha256"], "selection.selected_row_sha256"
    )
    if selection["selected_row_sha256"] != pool["row_sha256"][selection["selected_index"]]:
        raise ValueError("V26 smoke selection escaped the frozen pool")
    unit["selection"] = selection
    simulator = _require_exact_keys(
        unit["simulator"], {"selected_row_sha256"}, "V26 smoke simulator"
    )
    simulator["selected_row_sha256"] = _require_sha256(
        simulator["selected_row_sha256"], "simulator.selected_row_sha256"
    )
    if simulator["selected_row_sha256"] != selection["selected_row_sha256"]:
        raise ValueError("V26 smoke simulator row must bind the selected frozen row")
    unit["simulator"] = simulator
    terminal = _require_exact_keys(
        unit["terminal"], {"status", "failure_class", "failure_reason"}, "V26 smoke terminal"
    )
    if terminal != {"status": "complete", "failure_class": None, "failure_reason": None}:
        raise ValueError("V26 smoke completed terminal drifted")
    unit["terminal"] = terminal
    return unit


def _validate_failure_unit(value: Any) -> dict[str, Any]:
    unit = _require_exact_keys(
        value,
        {
            "unit_index",
            "operational_arm",
            "state_sha256",
            "input",
            "latent",
            "candidate_pool",
            "forward_calls",
            "selection",
            "simulator",
            "terminal",
        },
        "V26 smoke failed unit",
    )
    if unit["unit_index"] != 0 or unit["operational_arm"] != SMOKE_ARM:
        raise ValueError("V26 smoke failure unit identity drifted")
    if unit["state_sha256"] is not None:
        unit["state_sha256"] = _require_sha256(unit["state_sha256"], "failed.state_sha256")
    for name in ("input", "latent", "candidate_pool"):
        if unit[name] is not None and type(unit[name]) is not dict:
            raise ValueError(f"V26 smoke failed {name} must be a mapping or null")
    unit["forward_calls"] = _validate_forward_calls(
        unit["forward_calls"], completed=False
    )
    if unit["selection"] is not None or unit["simulator"] is not None:
        raise ValueError("V26 smoke typed failure must not claim an action or simulator row")
    terminal = _require_exact_keys(
        unit["terminal"], {"status", "failure_class", "failure_reason"}, "V26 smoke failure terminal"
    )
    if (
        terminal["status"] != "typed_failure"
        or type(terminal["failure_class"]) is not str
        or not terminal["failure_class"]
        or type(terminal["failure_reason"]) is not str
        or not terminal["failure_reason"]
    ):
        raise ValueError("V26 smoke typed failure terminal drifted")
    unit["terminal"] = terminal
    return unit


def build_development_smoke_receipt(
    *, manifest: Mapping[str, Any], unit: Mapping[str, Any]
) -> dict[str, Any]:
    normalized_manifest = validate_development_smoke_manifest(manifest)
    terminal = dict(unit).get("terminal")
    completed = type(terminal) is dict and terminal.get("status") == "complete"
    normalized_unit = (
        _validate_completed_unit(unit, normalized_manifest)
        if completed
        else _validate_failure_unit(unit)
    )
    denominator = (
        {"planned": 1, "complete": 1, "failed": 0, "unattempted": 0}
        if completed
        else {"planned": 1, "complete": 0, "failed": 1, "unattempted": 0}
    )
    return validate_development_smoke_receipt(
        {
            "schema_version": SMOKE_RECEIPT_SCHEMA_VERSION,
            "evidence_role": EVIDENCE_ROLE,
            "manifest": normalized_manifest,
            "denominator": denominator,
            "unit": normalized_unit,
        }
    )


def validate_development_smoke_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    expected = {"schema_version", "evidence_role", "manifest", "denominator", "unit"}
    if set(result) != expected:
        raise ValueError("V26 smoke receipt field set drifted")
    if result["schema_version"] != SMOKE_RECEIPT_SCHEMA_VERSION:
        raise ValueError("V26 smoke receipt schema drifted")
    if result["evidence_role"] != EVIDENCE_ROLE:
        raise ValueError("V26 smoke receipt evidence role drifted")
    result["manifest"] = validate_development_smoke_manifest(result["manifest"])
    denominator = _require_exact_keys(
        result["denominator"], {"planned", "complete", "failed", "unattempted"}, "V26 smoke denominator"
    )
    if any(type(item) is not int or item < 0 for item in denominator.values()):
        raise ValueError("V26 smoke denominator must be nonnegative integers")
    if denominator["planned"] != 1 or denominator["unattempted"] != 0:
        raise ValueError("V26 smoke denominator must retain exactly one planned unit")
    terminal = dict(result["unit"]).get("terminal") if type(result["unit"]) is dict else None
    completed = type(terminal) is dict and terminal.get("status") == "complete"
    expected_denominator = (
        {"planned": 1, "complete": 1, "failed": 0, "unattempted": 0}
        if completed
        else {"planned": 1, "complete": 0, "failed": 1, "unattempted": 0}
    )
    if denominator != expected_denominator:
        raise ValueError("V26 smoke terminal/denominator drifted")
    result["denominator"] = denominator
    result["unit"] = (
        _validate_completed_unit(result["unit"], result["manifest"])
        if completed
        else _validate_failure_unit(result["unit"])
    )
    return result
