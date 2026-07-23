from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping

from .diffusion_planner_v25_holdout_contract import (
    ARMS,
    validate_holdout_experiment_protocol,
    validate_holdout_identity,
)
from .diffusion_planner_v25_signal_complete_execution import (
    FRESH_ARM_CONFIG_SCHEMA_VERSION,
    build_fresh_b2_arm_config,
    validate_fresh_b2_arm_config,
)


HOLDOUT_ARM_CONFIG_SCHEMA_VERSION = "camp_dp_v25_holdout_arm_config_v1"

_PLAN_TO_OPENING_ARM = {
    "candidate0_operational_default": "candidate0",
    "camp_static14d": "static14d",
    "camp_scene14d_no_v2i": "scene14d",
}

_PROTOCOL_RENAMES = {
    "fresh_b2_plan_arm": "holdout_plan_arm",
    "fresh_b2_opening_arm": "holdout_opening_arm",
    "fresh_b2_steps": "holdout_steps",
    "fresh_b2_opened": "holdout_opened",
}


def build_holdout_arm_config(
    *,
    holdout_identity: Mapping[str, Any],
    experiment_protocol: Mapping[str, Any],
    probe_template: Mapping[str, Any],
    prepared_runtime: Mapping[str, Any],
    execution_unit: Mapping[str, Any],
    plan_arm: str,
    route_asset: Mapping[str, Any],
    dp_repo: Path,
    runtime_selector_authority: Mapping[str, Any],
) -> dict[str, Any]:
    identity = validate_holdout_identity(holdout_identity)
    protocol_authority = validate_holdout_experiment_protocol(
        experiment_protocol
    )
    legacy = build_fresh_b2_arm_config(
        probe_template=probe_template,
        prepared_runtime=prepared_runtime,
        execution_unit=execution_unit,
        plan_arm=plan_arm,
        route_asset=route_asset,
        dp_repo=dp_repo,
        runtime_selector_authority=runtime_selector_authority,
    )
    return freeze_holdout_arm_config_from_legacy(
        legacy_config=legacy,
        holdout_identity=identity,
        experiment_protocol=protocol_authority,
    )


def freeze_holdout_arm_config_from_legacy(
    *,
    legacy_config: Mapping[str, Any],
    holdout_identity: Mapping[str, Any],
    experiment_protocol: Mapping[str, Any],
) -> dict[str, Any]:
    identity = validate_holdout_identity(holdout_identity)
    protocol_authority = validate_holdout_experiment_protocol(
        experiment_protocol
    )
    legacy = validate_fresh_b2_arm_config(legacy_config)
    result = copy.deepcopy(legacy)
    result["schema_version"] = HOLDOUT_ARM_CONFIG_SCHEMA_VERSION
    protocol = result["protocol"]
    for old, new in _PROTOCOL_RENAMES.items():
        protocol[new] = protocol.pop(old)
    protocol["holdout_split"] = identity["split"]
    protocol["candidate0_semantics"] = (
        "action_equivalent_operational_default_first_default_output_alias"
    )
    protocol["same_forward_contract"] = (
        "forward_execution_id_plus_input_model_action_digest"
    )
    protocol["candidate0_pool_evidence_mode"] = (
        "same_tick_same_base_forward_supplementary"
    )
    protocol["candidate0_action_return_before_supplementary_evidence"] = True
    result["holdout_authority"] = {
        "holdout_identity_sha256": identity["holdout_identity_sha256"],
        "experiment_protocol_sha256": protocol_authority[
            "experiment_protocol_sha256"
        ],
        "split": identity["split"],
    }
    return validate_holdout_arm_config(result)


def validate_holdout_arm_config(value: Mapping[str, Any]) -> dict[str, Any]:
    expected_fields = {
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
        "holdout_authority",
    }
    if type(value) is not dict or set(value) != expected_fields:
        raise ValueError("holdout arm config field set drifted")
    if value.get("schema_version") != HOLDOUT_ARM_CONFIG_SCHEMA_VERSION:
        raise ValueError("holdout arm config schema drifted")
    result = copy.deepcopy(value)
    holdout = result.get("holdout_authority")
    if type(holdout) is not dict or set(holdout) != {
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "split",
    }:
        raise ValueError("holdout arm authority field set drifted")
    for name in ("holdout_identity_sha256", "experiment_protocol_sha256"):
        _require_sha(holdout.get(name), name)
    split = holdout.get("split")
    if type(split) is not str or not split.startswith("fresh_b"):
        raise ValueError("holdout arm split drifted")

    protocol = result.get("protocol")
    if type(protocol) is not dict:
        raise ValueError("holdout arm protocol is missing")
    plan_arm = protocol.get("holdout_plan_arm")
    opening_arm = protocol.get("holdout_opening_arm")
    if (
        plan_arm not in _PLAN_TO_OPENING_ARM
        or opening_arm != _PLAN_TO_OPENING_ARM[plan_arm]
        or opening_arm not in ARMS
        or protocol.get("holdout_split") != split
        or protocol.get("holdout_steps") != 64
        or protocol.get("holdout_opened") is not False
        or protocol.get("candidate0_semantics")
        != "action_equivalent_operational_default_first_default_output_alias"
        or protocol.get("same_forward_contract")
        != "forward_execution_id_plus_input_model_action_digest"
        or protocol.get("candidate0_pool_evidence_mode")
        != "same_tick_same_base_forward_supplementary"
        or protocol.get("candidate0_action_return_before_supplementary_evidence")
        is not True
        or protocol.get("candidate0_offline_pool_evidence_required")
        is not (plan_arm == "candidate0_operational_default")
        or protocol.get("fresh_outcome_fields_consumed") != []
        or protocol.get("execution_authorized_by_config") is not False
        or protocol.get("external_one_time_opening_release_required") is not True
        or protocol.get("holdout_access_authorized_by_config") is not False
    ):
        raise ValueError("holdout arm protocol drifted")

    legacy = copy.deepcopy(result)
    legacy.pop("holdout_authority")
    legacy["schema_version"] = FRESH_ARM_CONFIG_SCHEMA_VERSION
    legacy_protocol = legacy["protocol"]
    for old, new in _PROTOCOL_RENAMES.items():
        legacy_protocol[old] = legacy_protocol.pop(new)
    for name in (
        "holdout_split",
        "same_forward_contract",
        "candidate0_pool_evidence_mode",
        "candidate0_action_return_before_supplementary_evidence",
    ):
        legacy_protocol.pop(name)
    legacy_protocol["candidate0_semantics"] = (
        "same_forward_operational_default_alias"
    )
    validate_fresh_b2_arm_config(legacy)
    return result


def _require_sha(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return value
