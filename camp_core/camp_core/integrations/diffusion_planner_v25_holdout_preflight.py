from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Callable, Mapping

from .diffusion_planner_v25_holdout_contract import (
    ARMS,
    canonical_json_bytes,
    canonical_sha256,
    freeze_fatal_artifact,
    freeze_forward_binding,
    freeze_latency_namespaces,
    freeze_unit_terminal,
    strict_equal,
    validate_experiment_protocol,
    validate_fatal_artifact,
    validate_forward_binding,
    validate_holdout_identity,
    validate_latency_namespaces,
    validate_unit_terminal,
)
from .diffusion_planner_v25_holdout_execution import (
    validate_holdout_arm_config,
)


SCHEMA_VERSION = "camp_dp_v25_holdout_production_composition_preflight_v1"
CALLBACK_SCHEMA_VERSION = "camp_dp_v25_holdout_native_callback_preflight_v1"
AUTHORITY_SCHEMA_VERSION = (
    "camp_dp_v25_holdout_nonfresh_production_preflight_authority_v1"
)
TICKS_PER_ARM = 64

PLAN_ARM_BY_ARM = {
    "candidate0": "candidate0_operational_default",
    "static14d": "camp_static14d",
    "scene14d": "camp_scene14d_no_v2i",
}

PREFLIGHT_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "holdout_identity",
        "experiment_protocol",
        "nonfresh_preflight_authority",
        "fixture_root_sha256",
        "config_payloads",
        "config_sha256",
        "native_callback_receipts",
        "arm_terminals",
        "path_matrix",
        "paired_unit_count",
        "arm_run_count",
        "tick_count",
        "candidate0_offline_pool_evidence_required",
        "action_committed_before_supplementary_evidence",
        "fresh_opened",
        "outcome_fields_consumed",
        "preflight_payload_sha256",
    }
)

CALLBACK_FIELDS = frozenset(
    {
        "schema_version",
        "arm",
        "tick_index",
        "input_sha256",
        "model_sha256",
        "action_sha256",
        "candidate_pool_sha256",
        "forward_binding",
        "latency_namespaces",
        "candidate0_pool_evidence_composed",
        "receipt_projection_completed",
        "action_committed_before_supplementary_evidence",
        "selected_action_sha256",
    }
)

NativeCallback = Callable[[Mapping[str, Any], int], Mapping[str, Any]]

AUTHORITY_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "fixture_artifact_root_sha256",
        "fixture_recovery_root_sha256",
        "fixture_recovery_review_root_sha256",
        "device",
        "paired_unit_count",
        "arm_run_count",
        "tick_count",
        "fresh_opened",
        "outcome_fields_consumed",
        "model_or_dp_execution_authorized",
    }
)


def freeze_nonfresh_preflight_authority(
    *,
    holdout_identity_sha256: str,
    experiment_protocol_sha256: str,
    fixture_artifact_root_sha256: str,
    fixture_recovery_root_sha256: str,
    fixture_recovery_review_root_sha256: str,
) -> dict[str, Any]:
    for name, value in (
        ("holdout_identity_sha256", holdout_identity_sha256),
        ("experiment_protocol_sha256", experiment_protocol_sha256),
        ("fixture_artifact_root_sha256", fixture_artifact_root_sha256),
        ("fixture_recovery_root_sha256", fixture_recovery_root_sha256),
        (
            "fixture_recovery_review_root_sha256",
            fixture_recovery_review_root_sha256,
        ),
    ):
        _require_sha(value, name)
    return {
        "schema_version": AUTHORITY_SCHEMA_VERSION,
        "status": "authorized_nonfresh_exact_production_preflight_only",
        "holdout_identity_sha256": holdout_identity_sha256,
        "experiment_protocol_sha256": experiment_protocol_sha256,
        "fixture_artifact_root_sha256": fixture_artifact_root_sha256,
        "fixture_recovery_root_sha256": fixture_recovery_root_sha256,
        "fixture_recovery_review_root_sha256": (
            fixture_recovery_review_root_sha256
        ),
        "device": "cuda",
        "paired_unit_count": 1,
        "arm_run_count": 3,
        "tick_count": 192,
        "fresh_opened": False,
        "outcome_fields_consumed": [],
        "model_or_dp_execution_authorized": True,
    }


def validate_nonfresh_preflight_authority(
    value: Mapping[str, Any],
    *,
    holdout_identity_sha256: str,
    experiment_protocol_sha256: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != AUTHORITY_FIELDS:
        raise ValueError("holdout preflight authority field set drifted")
    expected = freeze_nonfresh_preflight_authority(
        holdout_identity_sha256=holdout_identity_sha256,
        experiment_protocol_sha256=experiment_protocol_sha256,
        fixture_artifact_root_sha256=value["fixture_artifact_root_sha256"],
        fixture_recovery_root_sha256=value["fixture_recovery_root_sha256"],
        fixture_recovery_review_root_sha256=value[
            "fixture_recovery_review_root_sha256"
        ],
    )
    if not strict_equal(value, expected):
        raise ValueError("holdout preflight authority value drifted")
    return expected


def run_production_composition_preflight(
    *,
    holdout_identity: Mapping[str, Any],
    experiment_protocol: Mapping[str, Any],
    nonfresh_preflight_authority: Mapping[str, Any],
    fixture_root_sha256: str,
    config_payloads: Mapping[str, Mapping[str, Any]],
    native_callback: NativeCallback,
) -> dict[str, Any]:
    identity = validate_holdout_identity(holdout_identity)
    protocol = validate_experiment_protocol(experiment_protocol)
    authority = validate_nonfresh_preflight_authority(
        nonfresh_preflight_authority,
        holdout_identity_sha256=identity["holdout_identity_sha256"],
        experiment_protocol_sha256=protocol["experiment_protocol_sha256"],
    )
    _require_sha(fixture_root_sha256, "fixture_root_sha256")
    configs = _validate_configs(config_payloads, identity, protocol)
    callbacks: dict[str, list[dict[str, Any]]] = {}
    terminals: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        rows = [
            _validate_callback_receipt(
                native_callback(configs[arm], tick_index),
                arm=arm,
                tick_index=tick_index,
            )
            for tick_index in range(TICKS_PER_ARM)
        ]
        callbacks[arm] = rows
        terminals[arm] = freeze_unit_terminal(
            status="complete", failure_class=None, all_k_bad=False
        )
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_exact_production_composition_preflight",
        "holdout_identity": identity,
        "experiment_protocol": protocol,
        "nonfresh_preflight_authority": authority,
        "fixture_root_sha256": fixture_root_sha256,
        "config_payloads": configs,
        "config_sha256": {
            arm: canonical_sha256(configs[arm]) for arm in ARMS
        },
        "native_callback_receipts": callbacks,
        "arm_terminals": terminals,
        "path_matrix": _path_matrix(identity, protocol),
        "paired_unit_count": 1,
        "arm_run_count": 3,
        "tick_count": len(ARMS) * TICKS_PER_ARM,
        "candidate0_offline_pool_evidence_required": True,
        "action_committed_before_supplementary_evidence": True,
        "fresh_opened": False,
        "outcome_fields_consumed": [],
    }
    result["preflight_payload_sha256"] = canonical_sha256(result)
    return validate_production_composition_preflight(result)


def validate_production_composition_preflight(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != PREFLIGHT_FIELDS:
        raise ValueError("production preflight field set drifted")
    result = json.loads(canonical_json_bytes(value))
    identity = validate_holdout_identity(result["holdout_identity"])
    protocol = validate_experiment_protocol(result["experiment_protocol"])
    validate_nonfresh_preflight_authority(
        result["nonfresh_preflight_authority"],
        holdout_identity_sha256=identity["holdout_identity_sha256"],
        experiment_protocol_sha256=protocol["experiment_protocol_sha256"],
    )
    _require_sha(result["fixture_root_sha256"], "fixture_root_sha256")
    configs = _validate_configs(result["config_payloads"], identity, protocol)
    if result["config_sha256"] != {
        arm: canonical_sha256(configs[arm]) for arm in ARMS
    }:
        raise ValueError("production preflight config SHA drifted")
    callbacks = result["native_callback_receipts"]
    if type(callbacks) is not dict or set(callbacks) != set(ARMS):
        raise ValueError("production preflight callback arm set drifted")
    for arm in ARMS:
        rows = callbacks[arm]
        if type(rows) is not list or len(rows) != TICKS_PER_ARM:
            raise ValueError("production preflight callback denominator drifted")
        for tick_index, row in enumerate(rows):
            _validate_callback_receipt(row, arm=arm, tick_index=tick_index)
    terminals = result["arm_terminals"]
    if type(terminals) is not dict or set(terminals) != set(ARMS):
        raise ValueError("production preflight terminal arm set drifted")
    for arm in ARMS:
        expected = freeze_unit_terminal(
            status="complete", failure_class=None, all_k_bad=False
        )
        if not strict_equal(validate_unit_terminal(terminals[arm]), expected):
            raise ValueError("production preflight complete terminal drifted")
    _validate_path_matrix(result["path_matrix"], identity, protocol)
    exact = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_exact_production_composition_preflight",
        "paired_unit_count": 1,
        "arm_run_count": 3,
        "tick_count": len(ARMS) * TICKS_PER_ARM,
        "candidate0_offline_pool_evidence_required": True,
        "action_committed_before_supplementary_evidence": True,
        "fresh_opened": False,
        "outcome_fields_consumed": [],
    }
    for name, expected in exact.items():
        if not strict_equal(result[name], expected):
            raise ValueError(f"production preflight {name} drifted")
    payload = dict(result)
    stored_sha = payload.pop("preflight_payload_sha256")
    if stored_sha != canonical_sha256(payload):
        raise ValueError("production preflight payload SHA drifted")
    return result


def deterministic_nonfresh_callback(
    config: Mapping[str, Any], tick_index: int
) -> dict[str, Any]:
    validated = validate_holdout_arm_config(config)
    protocol = validated["protocol"]
    arm = protocol["holdout_opening_arm"]
    if type(tick_index) is not int or not 0 <= tick_index < TICKS_PER_ARM:
        raise ValueError("production preflight tick index drifted")
    config_sha = canonical_sha256(validated)
    input_sha = _digest(config_sha, arm, tick_index, "input")
    model_sha = _digest(
        validated["fixed_dp"]["checkpoint"]["sha256"],
        validated["runtime_selector_authority"]["model_registry_sha256"],
        arm,
        "model",
    )
    action_sha = _digest(input_sha, model_sha, arm, tick_index, "action")
    pool_sha = _digest(input_sha, model_sha, tick_index, "candidate-pool")
    online = {
        "dp_operational_default": 1.0,
        "additional_k8_generation": 0.0,
        "atoms": 0.0,
        "context": 0.0,
        "scene_weight": 0.0,
        "selector": 0.0,
    }
    supplementary = {
        "candidate_pool_generation": 0.0,
        "atoms": 0.0,
        "context": 0.0,
        "scene_weight": 0.0,
        "receipt_hashing": 0.1,
    }
    if arm == "candidate0":
        supplementary["candidate_pool_generation"] = 7.0
        supplementary["atoms"] = 0.3
    else:
        online["additional_k8_generation"] = 7.0
        online["atoms"] = 0.3
        online["selector"] = 0.1
    if arm == "scene14d":
        online["context"] = 0.2
        online["scene_weight"] = 0.05
    overhead = 0.5
    total = sum(online.values()) + sum(supplementary.values()) + overhead
    action_timestamp = 1_000_000 + tick_index * 10
    latency = freeze_latency_namespaces(
        arm=arm,
        online_operational_latency_ms=online,
        supplementary_evidence_latency_ms=supplementary,
        runtime_total_observed_ms=total,
        runtime_nondecision_overhead_ms=overhead,
        action_available_timestamp_ns=action_timestamp,
        supplementary_started_timestamp_ns=action_timestamp + 1,
    )
    return {
        "schema_version": CALLBACK_SCHEMA_VERSION,
        "arm": arm,
        "tick_index": tick_index,
        "input_sha256": input_sha,
        "model_sha256": model_sha,
        "action_sha256": action_sha,
        "candidate_pool_sha256": pool_sha,
        "forward_binding": freeze_forward_binding(
            tick_index=tick_index,
            input_sha256=input_sha,
            model_sha256=model_sha,
            action_sha256=action_sha,
            candidate_pool_sha256=pool_sha,
        ),
        "latency_namespaces": latency,
        "candidate0_pool_evidence_composed": arm == "candidate0",
        "receipt_projection_completed": True,
        "action_committed_before_supplementary_evidence": True,
        "selected_action_sha256": action_sha,
    }


def project_actual_native_preflight_callbacks(
    *,
    config_payloads: Mapping[str, Mapping[str, Any]],
    primary_native_receipts: Mapping[str, Mapping[str, Any]],
    candidate0_supplementary_native_receipt: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Project real non-Fresh native runs into the normative callback contract."""

    configs = {
        arm: validate_holdout_arm_config(config_payloads[arm]) for arm in ARMS
    }
    if type(primary_native_receipts) is not dict or set(
        primary_native_receipts
    ) != set(ARMS):
        raise ValueError("actual preflight primary native arm set drifted")
    supplementary = _native_ticks(
        candidate0_supplementary_native_receipt,
        "candidate0 supplementary native receipt",
    )
    result: dict[str, list[dict[str, Any]]] = {}
    for arm in ARMS:
        primary = _native_ticks(
            primary_native_receipts[arm],
            f"{arm} primary native receipt",
        )
        model_sha = canonical_sha256(
            {
                "fixed_dp_head": configs[arm]["fixed_dp"]["head"],
                "checkpoint_sha256": configs[arm]["fixed_dp"]["checkpoint"][
                    "sha256"
                ],
                "args_sha256": configs[arm]["fixed_dp"]["args_json"]["sha256"],
                "model_registry_sha256": configs[arm][
                    "runtime_selector_authority"
                ]["model_registry_sha256"],
            }
        )
        rows: list[dict[str, Any]] = []
        for tick_index, tick in enumerate(primary):
            if tick["tick_index"] != tick_index:
                raise ValueError("actual preflight primary tick order drifted")
            action_sha = _require_sha(
                tick.get("selected_trajectory_sha256"),
                f"{arm} selected action SHA",
            )
            if arm == "candidate0":
                diagnostic = supplementary[tick_index]
                if (
                    diagnostic["tick_index"] != tick_index
                    or diagnostic["input_sha256"] != tick["input_sha256"]
                    or diagnostic["default_output_sha256"]
                    != tick["default_output_sha256"]
                    or diagnostic["selected_trajectory_sha256"] != action_sha
                    or tick.get("candidate0_action_first") is not True
                    or tick.get("same_forward_claimed") is not False
                ):
                    raise ValueError(
                        "candidate0 action/supplementary base-forward drifted"
                    )
                pool_sha = _require_sha(
                    diagnostic.get("candidate_tensor_sha256_before"),
                    "candidate0 supplementary candidate pool SHA",
                )
                latency = _candidate0_actual_latency(tick, diagnostic)
            else:
                pool_sha = _require_sha(
                    tick.get("candidate_tensor_sha256_before"),
                    f"{arm} candidate pool SHA",
                )
                latency = _camp_actual_latency(arm, tick)
            rows.append(
                _validate_callback_receipt(
                    {
                        "schema_version": CALLBACK_SCHEMA_VERSION,
                        "arm": arm,
                        "tick_index": tick_index,
                        "input_sha256": _require_sha(
                            tick["input_sha256"], f"{arm} input SHA"
                        ),
                        "model_sha256": model_sha,
                        "action_sha256": action_sha,
                        "candidate_pool_sha256": pool_sha,
                        "forward_binding": freeze_forward_binding(
                            tick_index=tick_index,
                            input_sha256=tick["input_sha256"],
                            model_sha256=model_sha,
                            action_sha256=action_sha,
                            candidate_pool_sha256=pool_sha,
                        ),
                        "latency_namespaces": latency,
                        "candidate0_pool_evidence_composed": (
                            arm == "candidate0"
                        ),
                        "receipt_projection_completed": True,
                        "action_committed_before_supplementary_evidence": True,
                        "selected_action_sha256": action_sha,
                    },
                    arm=arm,
                    tick_index=tick_index,
                )
            )
        result[arm] = rows
    return result


def _candidate0_actual_latency(
    primary: Mapping[str, Any], diagnostic: Mapping[str, Any]
) -> dict[str, Any]:
    primary_latency = _latency_mapping(primary, "candidate0 primary")
    diagnostic_latency = _latency_mapping(
        diagnostic, "candidate0 supplementary"
    )
    online_total = _latency_value(primary_latency, "hook_total")
    diagnostic_hook = _latency_value(diagnostic_latency, "hook_total")
    diagnostic_atoms = _latency_value(
        diagnostic_latency, "atom_materialization"
    )
    candidate_pool = diagnostic_hook - diagnostic_atoms
    if candidate_pool < 0.0:
        raise ValueError("candidate0 supplementary latency decomposition drifted")
    runtime_total = _latency_value(
        primary_latency, "total_planning"
    ) + _latency_value(diagnostic_latency, "total_planning")
    overhead = runtime_total - online_total - diagnostic_hook
    if overhead < 0.0:
        raise ValueError("candidate0 runtime total latency drifted")
    return freeze_latency_namespaces(
        arm="candidate0",
        online_operational_latency_ms={
            "dp_operational_default": online_total,
            "additional_k8_generation": 0.0,
            "atoms": 0.0,
            "context": 0.0,
            "scene_weight": 0.0,
            "selector": 0.0,
        },
        supplementary_evidence_latency_ms={
            "candidate_pool_generation": candidate_pool,
            "atoms": diagnostic_atoms,
            "context": 0.0,
            "scene_weight": 0.0,
            "receipt_hashing": 0.0,
        },
        runtime_total_observed_ms=runtime_total,
        runtime_nondecision_overhead_ms=overhead,
        action_available_timestamp_ns=_native_timestamp(
            primary, "action_available_ns"
        ),
        supplementary_started_timestamp_ns=_native_timestamp(
            diagnostic, "planning_started_ns"
        ),
    )


def _camp_actual_latency(
    arm: str, tick: Mapping[str, Any]
) -> dict[str, Any]:
    latency = _latency_mapping(tick, arm)
    hook_total = _latency_value(latency, "hook_total")
    components = {
        "additional_k8_generation": _latency_value(
            latency, "candidate_inference"
        ),
        "atoms": _latency_value(latency, "atom_materialization"),
        "context": (
            _latency_value(latency, "context")
            if arm == "scene14d"
            else 0.0
        ),
        "scene_weight": (
            _latency_value(latency, "scene_weight")
            if arm == "scene14d"
            else 0.0
        ),
        "selector": _latency_value(latency, "selector"),
    }
    dp_default = hook_total - sum(components.values())
    if dp_default < 0.0:
        raise ValueError(f"{arm} online latency decomposition drifted")
    runtime_total = _latency_value(latency, "total_planning")
    overhead = runtime_total - hook_total
    if overhead < 0.0:
        raise ValueError(f"{arm} runtime total latency drifted")
    return freeze_latency_namespaces(
        arm=arm,
        online_operational_latency_ms={
            "dp_operational_default": dp_default,
            **components,
        },
        supplementary_evidence_latency_ms={
            "candidate_pool_generation": 0.0,
            "atoms": 0.0,
            "context": 0.0,
            "scene_weight": 0.0,
            "receipt_hashing": 0.0,
        },
        runtime_total_observed_ms=runtime_total,
        runtime_nondecision_overhead_ms=overhead,
        action_available_timestamp_ns=_native_timestamp(
            tick, "action_available_ns"
        ),
        supplementary_started_timestamp_ns=_native_timestamp(
            tick, "receipt_projected_ns"
        ),
    )


def _native_ticks(
    receipt: Mapping[str, Any], label: str
) -> list[dict[str, Any]]:
    if (
        type(receipt) is not dict
        or receipt.get("status") != "ok"
        or type(receipt.get("ticks")) is not list
        or len(receipt["ticks"]) != TICKS_PER_ARM
    ):
        raise ValueError(f"{label} did not contain 64 successful ticks")
    return [dict(row) for row in receipt["ticks"]]


def _latency_mapping(
    tick: Mapping[str, Any], label: str
) -> dict[str, Any]:
    value = tick.get("latency_ms")
    if type(value) is not dict:
        raise ValueError(f"{label} native latency is missing")
    return dict(value)


def _latency_value(value: Mapping[str, Any], name: str) -> float:
    raw = value.get(name)
    if type(raw) not in {int, float} or type(raw) is bool:
        raise ValueError(f"native latency {name} must be numeric")
    result = float(raw)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"native latency {name} must be finite nonnegative")
    return result


def _native_timestamp(value: Mapping[str, Any], name: str) -> int:
    result = value.get(name)
    if type(result) is not int or result < 0:
        raise ValueError(f"native timestamp {name} drifted")
    return result


def _validate_configs(
    value: Mapping[str, Mapping[str, Any]],
    identity: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    if type(value) is not dict or set(value) != set(ARMS):
        raise ValueError("production preflight config arm set drifted")
    result: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        config = validate_holdout_arm_config(value[arm])
        authority = config["holdout_authority"]
        if (
            authority["holdout_identity_sha256"]
            != identity["holdout_identity_sha256"]
            or authority["experiment_protocol_sha256"]
            != protocol["experiment_protocol_sha256"]
            or config["protocol"]["holdout_plan_arm"] != PLAN_ARM_BY_ARM[arm]
            or config["protocol"]["holdout_opening_arm"] != arm
            or config["protocol"]["candidate0_offline_pool_evidence_required"]
            is not (arm == "candidate0")
        ):
            raise ValueError("production preflight config authority drifted")
        result[arm] = config
    return result


def _validate_callback_receipt(
    value: Mapping[str, Any], *, arm: str, tick_index: int
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != CALLBACK_FIELDS:
        raise ValueError("native callback preflight field set drifted")
    result = json.loads(canonical_json_bytes(value))
    for name in (
        "input_sha256",
        "model_sha256",
        "action_sha256",
        "candidate_pool_sha256",
        "selected_action_sha256",
    ):
        _require_sha(result[name], name)
    expected_binding = freeze_forward_binding(
        tick_index=tick_index,
        input_sha256=result["input_sha256"],
        model_sha256=result["model_sha256"],
        action_sha256=result["action_sha256"],
        candidate_pool_sha256=result["candidate_pool_sha256"],
    )
    exact = {
        "schema_version": CALLBACK_SCHEMA_VERSION,
        "arm": arm,
        "tick_index": tick_index,
        "forward_binding": expected_binding,
        "latency_namespaces": validate_latency_namespaces(
            result["latency_namespaces"]
        ),
        "candidate0_pool_evidence_composed": arm == "candidate0",
        "receipt_projection_completed": True,
        "action_committed_before_supplementary_evidence": True,
        "selected_action_sha256": result["action_sha256"],
    }
    for name, expected in exact.items():
        if not strict_equal(result[name], expected):
            raise ValueError(f"native callback preflight {name} drifted")
    validate_forward_binding(result["forward_binding"])
    return result


def _path_matrix(
    identity: Mapping[str, Any], protocol: Mapping[str, Any]
) -> dict[str, Any]:
    fatal_common = {
        "controller_decision_root_sha256": "1" * 64,
        "opening_release_root_sha256": "2" * 64,
        "holdout_identity_sha256": identity["holdout_identity_sha256"],
        "experiment_protocol_sha256": protocol["experiment_protocol_sha256"],
        "planned_arm_run_count": 3,
        "outcome_fields_consumed": [],
    }
    marker_path = (
        "/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas/"
        "synthetic-preflight-marker.json"
    )
    return {
        "success": freeze_unit_terminal(
            status="complete", failure_class=None, all_k_bad=False
        ),
        "typed_scientific_failure": freeze_unit_terminal(
            status="fixed_dp_candidate_generation_capability_failure",
            failure_class="invalid_k8_heading_norm_envelope",
            all_k_bad=False,
        ),
        "artifact_fatal": {
            "before_nonce": freeze_fatal_artifact(
                block_class="synthetic_preflight_crash_injection",
                reason="before_nonce_consumption",
                marker_path=None,
                marker_sha256=None,
                attempted_unit_ordinal=None,
                attempted_arm=None,
                attempted_arm_run_count=0,
                complete_arm_run_count=0,
                fresh_opened_once=False,
                **fatal_common,
            ),
            "after_marker_before_run": freeze_fatal_artifact(
                block_class="synthetic_preflight_crash_injection",
                reason="after_marker_before_run",
                marker_path=marker_path,
                marker_sha256="3" * 64,
                attempted_unit_ordinal=None,
                attempted_arm=None,
                attempted_arm_run_count=0,
                complete_arm_run_count=0,
                fresh_opened_once=True,
                **fatal_common,
            ),
            "after_run_before_receipt": freeze_fatal_artifact(
                block_class="synthetic_preflight_crash_injection",
                reason="after_run_before_receipt",
                marker_path=marker_path,
                marker_sha256="3" * 64,
                attempted_unit_ordinal=0,
                attempted_arm="candidate0",
                attempted_arm_run_count=1,
                complete_arm_run_count=0,
                fresh_opened_once=True,
                **fatal_common,
            ),
            "after_receipt_before_seal": freeze_fatal_artifact(
                block_class="synthetic_preflight_crash_injection",
                reason="after_receipt_before_seal",
                marker_path=marker_path,
                marker_sha256="3" * 64,
                attempted_unit_ordinal=0,
                attempted_arm="candidate0",
                attempted_arm_run_count=1,
                complete_arm_run_count=1,
                fresh_opened_once=True,
                **fatal_common,
            ),
        },
    }


def _validate_path_matrix(
    value: Mapping[str, Any],
    identity: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> None:
    if type(value) is not dict or set(value) != {
        "success",
        "typed_scientific_failure",
        "artifact_fatal",
    }:
        raise ValueError("production preflight path matrix drifted")
    validate_unit_terminal(value["success"])
    typed = validate_unit_terminal(value["typed_scientific_failure"])
    if typed["status"] != "fixed_dp_candidate_generation_capability_failure":
        raise ValueError("production preflight typed path drifted")
    fatal = value["artifact_fatal"]
    if type(fatal) is not dict or set(fatal) != {
        "before_nonce",
        "after_marker_before_run",
        "after_run_before_receipt",
        "after_receipt_before_seal",
    }:
        raise ValueError("production preflight fatal path matrix drifted")
    for name, row in fatal.items():
        receipt = validate_fatal_artifact(row)
        if (
            receipt["holdout_identity_sha256"]
            != identity["holdout_identity_sha256"]
            or receipt["experiment_protocol_sha256"]
            != protocol["experiment_protocol_sha256"]
            or receipt["fresh_opened_once"]
            is not (name != "before_nonce")
        ):
            raise ValueError("production preflight fatal path authority drifted")


def _digest(*values: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(list(values))).hexdigest()


def _require_sha(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return value
