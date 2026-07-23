from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner_v25_evaluation import (
    ARMS,
    FRESH_TICK_COUNT,
    LATENCY_STAGES,
    NONINFERIORITY_METRICS,
    PAIR_AUTHORITY_FIELDS,
    ROW_FIELDS,
    SAFETY_COMPONENTS,
)
from .diffusion_planner_v25_fresh_b2 import (
    FIXED_DP_HEAD,
    validate_fresh_b2_manifest_row,
)
from .diffusion_planner_v25_holdout_contract import (
    SCIENTIFIC_TERMINAL_STATUSES,
)
from .diffusion_planner_v25_signal_safety import SIGNAL_SAFETY_SCHEMA_VERSION
from .diffusion_planner_v25_actual_native_receipt_contract import (
    actual_native_receipt_contract_sha256,
    validate_actual_native_receipt,
)


CANDIDATE0_POOL_SCHEMA_VERSION = (
    "camp_dp_v25_candidate0_supplementary_candidate_pool_evidence_v3"
)
LEGACY_CANDIDATE0_POOL_SCHEMA_VERSION = (
    "camp_dp_v25_candidate0_offline_candidate_pool_evidence_v2"
)
CANDIDATE0_SUPPLEMENTARY_NATIVE_SCHEMA_VERSION = (
    "camp_dp_v25_candidate0_supplementary_native_receipt_v1"
)
_EXECUTION_EVIDENCE_ENRICHMENT_FIELDS = frozenset(
    {
        "fresh_decision_evidence_reference",
        "fresh_decision_evidence_count",
    }
)
_LEGACY_POOL_FIELDS = {
    "schema_version",
    "candidate_tensor_source",
    "candidate_tensor_modified",
    "ticks",
    "outcome_fields_consumed",
    "fresh_protocol_changed",
}
_POOL_FIELDS = {
    *_LEGACY_POOL_FIELDS,
    "same_forward_claimed",
    "pool_evidence_affects_action",
    "pool_evidence_affects_rng_or_next_tick",
}
_LEGACY_POOL_TICK_FIELDS = {
    "tick_index",
    "candidate_tensor_sha256",
    "candidate_row_sha256",
    "default_output_sha256",
    "source_valid_mask",
    "physical_feasible_mask",
}
_POOL_TICK_FIELDS = {
    *_LEGACY_POOL_TICK_FIELDS,
    "input_sha256",
    "action_available_ns",
    "supplementary_started_ns",
    "supplementary_completed_ns",
}
_SUPPLEMENTARY_NATIVE_FIELDS = {
    "schema_version",
    "status",
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
    "claim_authorized",
    "outcome_fields_consumed",
    "actual_native_receipt_contract_sha256",
}
_SUPPLEMENTARY_NATIVE_TICK_FIELDS = {
    "tick_index",
    "input_sha256",
    "candidate_tensor_sha256_before",
    "candidate_tensor_sha256_after",
    "candidate_row_sha256",
    "default_output_sha256",
    "selected_trajectory_sha256",
    "default_candidate0_identity",
    "selected_index",
    "source_valid_mask",
    "physical_feasible_mask",
    "source_complete_mask",
    "atom_matrix_sha256",
    "latency_ms",
    "planning_started_ns",
    "action_available_ns",
    "receipt_projected_ns",
    "same_forward_claimed",
    "supplementary_only",
}
_COMPONENT_MAP = {
    "collision": "collision_any",
    "near_miss": "near_miss_noncollision_rate",
    "offroad": "offroad_rate",
    "red_light": "red_light_violation_any",
    "speed": "speed_limit_violation_rate",
    "wrong_way": "wrong_way_rate",
}
_PERFORMANCE_MAP = {
    "progress": "route_progress_m",
    "completion": "route_completion_rate",
    "mean_jerk": "mean_abs_jerk_mps3",
    "max_jerk": "max_jerk_mps3",
    "mean_lateral_acceleration": "mean_abs_lateral_acceleration_mps2",
    "max_lateral_acceleration": "max_abs_lateral_acceleration_mps2",
}
_LATENCY_SOURCE = {
    "dp_operational_default": "default_inference",
    "additional_k8_generation": "candidate_inference",
    "atoms": "atom_materialization",
    "context": "context",
    "scene_weight": "scene_weight",
    "selector": "selector",
    "tracker": "tracker",
    "total_planning": "total_planning",
}


def build_candidate0_pool_evidence(
    native_receipt: Mapping[str, Any],
    supplementary_native_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project candidate-pool diagnostics without changing candidate0 selection."""

    if supplementary_native_receipt is not None:
        return _build_supplementary_candidate0_pool(
            native_receipt, supplementary_native_receipt
        )

    if (
        type(native_receipt) is not dict
        or native_receipt.get("status") != "ok"
        or native_receipt.get("arm") != "dp"
        or native_receipt.get("fixed_dp_head") != FIXED_DP_HEAD
    ):
        raise ValueError("candidate0 pool requires a complete fixed-DP receipt")
    ticks = native_receipt.get("ticks")
    if type(ticks) is not list or len(ticks) != FRESH_TICK_COUNT:
        raise ValueError("candidate0 pool native tick denominator drifted")
    rows: list[dict[str, Any]] = []
    for index, tick in enumerate(ticks):
        if (
            type(tick) is not dict
            or tick.get("tick_index") != index
            or tick.get("candidate0_operational_default") is not True
            or tick.get("selected_index") != 0
            or tick.get("candidate_tensor_sha256_before")
            != tick.get("candidate_tensor_sha256_after")
        ):
            raise ValueError("candidate0 pool native tick authority drifted")
        rows.append(
            {
                "tick_index": index,
                "candidate_tensor_sha256": tick[
                    "candidate_tensor_sha256_before"
                ],
                "candidate_row_sha256": list(tick["candidate_row_sha256"]),
                "default_output_sha256": tick["default_output_sha256"],
                "source_valid_mask": _bool_k8(
                    tick.get("source_valid_mask"), "source_valid_mask"
                ),
                "physical_feasible_mask": _bool_k8(
                    tick.get("physical_feasible_mask"),
                    "physical_feasible_mask",
                ),
            }
        )
    result = {
        "schema_version": LEGACY_CANDIDATE0_POOL_SCHEMA_VERSION,
        "candidate_tensor_source": "same_forward_fixed_k8_pre_atom_boundary",
        "candidate_tensor_modified": False,
        "ticks": rows,
        "outcome_fields_consumed": [],
        "fresh_protocol_changed": False,
    }
    _candidate0_pool(result)
    return result


def project_candidate0_supplementary_native_receipt(
    native_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Remove simulator outcomes while retaining exact pool/input/action authority."""

    if (
        type(native_receipt) is not dict
        or native_receipt.get("schema_version") != "v21_native_arm_receipt_v1"
        or native_receipt.get("status") != "ok"
        or native_receipt.get("arm") != "dp"
        or native_receipt.get("fixed_dp_head") != FIXED_DP_HEAD
        or native_receipt.get("claim_authorized") is not False
    ):
        raise ValueError("supplementary candidate0 native receipt authority drifted")
    validate_actual_native_receipt(
        native_receipt,
        branch="candidate0_supplementary",
        expected_ticks=FRESH_TICK_COUNT,
    )
    header_names = (
        "route_sha256",
        "logical_map_sha256",
        "checkpoint_sha256",
        "args_sha256",
        "spawn_config_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
    )
    if any(not _sha256(native_receipt.get(name)) for name in header_names):
        raise ValueError("supplementary candidate0 native header SHA drifted")
    if type(native_receipt.get("scenario_seed")) is not int:
        raise ValueError("supplementary candidate0 scenario seed drifted")
    ticks = native_receipt.get("ticks")
    if type(ticks) is not list or len(ticks) != FRESH_TICK_COUNT:
        raise ValueError("supplementary candidate0 tick denominator drifted")
    projected_ticks = [
        _project_supplementary_candidate0_tick(tick, index)
        for index, tick in enumerate(ticks)
    ]
    result = {
        "schema_version": CANDIDATE0_SUPPLEMENTARY_NATIVE_SCHEMA_VERSION,
        "status": "ok",
        "route_sha256": native_receipt["route_sha256"],
        "logical_map_sha256": native_receipt["logical_map_sha256"],
        "fixed_dp_head": native_receipt["fixed_dp_head"],
        "checkpoint_sha256": native_receipt["checkpoint_sha256"],
        "args_sha256": native_receipt["args_sha256"],
        "arm": "dp",
        "scenario_seed": native_receipt["scenario_seed"],
        "spawn_config_sha256": native_receipt["spawn_config_sha256"],
        "initial_state_sha256": native_receipt["initial_state_sha256"],
        "initial_input_sha256": native_receipt["initial_input_sha256"],
        "ticks": projected_ticks,
        "claim_authorized": False,
        "outcome_fields_consumed": [],
        "actual_native_receipt_contract_sha256": (
            actual_native_receipt_contract_sha256()
        ),
    }
    _supplementary_candidate0_native(result)
    return result


def _build_supplementary_candidate0_pool(
    primary_native_receipt: Mapping[str, Any],
    supplementary_native_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        type(primary_native_receipt) is not dict
        or primary_native_receipt.get("schema_version")
        != "v21_native_arm_receipt_v1"
        or primary_native_receipt.get("status") != "ok"
        or primary_native_receipt.get("arm") != "dp"
        or primary_native_receipt.get("fixed_dp_head") != FIXED_DP_HEAD
        or primary_native_receipt.get("claim_authorized") is not False
    ):
        raise ValueError("candidate0 action-first native authority drifted")
    supplementary = _supplementary_candidate0_native(
        supplementary_native_receipt
    )
    for name in (
        "route_sha256",
        "logical_map_sha256",
        "fixed_dp_head",
        "checkpoint_sha256",
        "args_sha256",
        "scenario_seed",
        "spawn_config_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
    ):
        if primary_native_receipt.get(name) != supplementary[name]:
            raise ValueError(
                f"candidate0 supplementary native header drifted: {name}"
            )
    primary_ticks = primary_native_receipt.get("ticks")
    if type(primary_ticks) is not list or len(primary_ticks) != FRESH_TICK_COUNT:
        raise ValueError("candidate0 action-first tick denominator drifted")
    rows: list[dict[str, Any]] = []
    for index, (primary, diagnostic) in enumerate(
        zip(primary_ticks, supplementary["ticks"])
    ):
        if (
            type(primary) is not dict
            or primary.get("tick_index") != index
            or primary.get("candidate0_action_first") is not True
            or primary.get("candidate0_operational_default") is not True
            or primary.get("candidate0_pool_evidence_collected_online") is not False
            or primary.get("candidate0_pool_evidence_required_post_action") is not True
            or primary.get("same_forward_claimed") is not False
            or primary.get("selected_index") != 0
            or primary.get("selected_trajectory_sha256")
            != primary.get("default_output_sha256")
            or any(
                name in primary
                for name in (
                    "candidate_tensor_sha256_before",
                    "candidate_tensor_sha256_after",
                    "candidate_row_sha256",
                )
            )
        ):
            raise ValueError("candidate0 action-first tick contract drifted")
        if (
            diagnostic["tick_index"] != index
            or diagnostic["input_sha256"] != primary.get("input_sha256")
            or diagnostic["default_output_sha256"]
            != primary.get("default_output_sha256")
            or diagnostic["selected_trajectory_sha256"]
            != primary.get("selected_trajectory_sha256")
        ):
            raise ValueError(
                "candidate0 action/supplementary base-forward binding drifted"
            )
        action_available = _native_nonnegative_int(
            primary.get("action_available_ns"), "action_available_ns"
        )
        supplementary_started = _native_nonnegative_int(
            diagnostic.get("planning_started_ns"),
            "supplementary planning_started_ns",
        )
        supplementary_completed = _native_nonnegative_int(
            diagnostic.get("receipt_projected_ns"),
            "supplementary receipt_projected_ns",
        )
        if (
            supplementary_started < action_available
            or supplementary_completed < supplementary_started
        ):
            raise ValueError(
                "candidate0 supplementary evidence did not follow action availability"
            )
        rows.append(
            {
                "tick_index": index,
                "input_sha256": diagnostic["input_sha256"],
                "candidate_tensor_sha256": diagnostic[
                    "candidate_tensor_sha256_before"
                ],
                "candidate_row_sha256": list(
                    diagnostic["candidate_row_sha256"]
                ),
                "default_output_sha256": diagnostic[
                    "default_output_sha256"
                ],
                "source_valid_mask": list(diagnostic["source_valid_mask"]),
                "physical_feasible_mask": list(
                    diagnostic["physical_feasible_mask"]
                ),
                "action_available_ns": action_available,
                "supplementary_started_ns": supplementary_started,
                "supplementary_completed_ns": supplementary_completed,
            }
        )
    result = {
        "schema_version": CANDIDATE0_POOL_SCHEMA_VERSION,
        "candidate_tensor_source": (
            "post_action_same_tick_same_base_forward_supplementary"
        ),
        "candidate_tensor_modified": False,
        "same_forward_claimed": False,
        "pool_evidence_affects_action": False,
        "pool_evidence_affects_rng_or_next_tick": False,
        "ticks": rows,
        "outcome_fields_consumed": [],
        "fresh_protocol_changed": False,
    }
    _candidate0_pool(result)
    return result


def build_fresh_b2_complete_row(
    *,
    qualification_row: Mapping[str, Any],
    pair_key: str,
    arm: str,
    arm_order_index: int,
    native_receipt: Mapping[str, Any],
    candidate0_pool_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Mechanically project one complete native arm into the frozen Fresh row."""

    metadata = validate_fresh_b2_manifest_row(qualification_row)
    _pair_arm(pair_key, arm, arm_order_index)
    native = _native_receipt(native_receipt, arm)
    pair_authority = _pair_authority(metadata, native)
    ticks = native["ticks"]
    if arm == "candidate0":
        pool_ticks = _candidate0_pool(candidate0_pool_evidence)
        supplementary_pool = (
            candidate0_pool_evidence.get("schema_version")
            == CANDIDATE0_POOL_SCHEMA_VERSION
        )
        for tick, pool in zip(ticks, pool_ticks):
            if supplementary_pool:
                if (
                    pool["input_sha256"] != tick["input_sha256"]
                    or pool["default_output_sha256"]
                    != tick["default_output_sha256"]
                    or tick.get("candidate0_action_first") is not True
                    or tick.get("same_forward_claimed") is not False
                ):
                    raise ValueError(
                        "candidate0 supplementary pool is not bound to the "
                        "action-first base forward"
                    )
            elif (
                pool["candidate_tensor_sha256"]
                != tick["candidate_tensor_sha256_before"]
                or pool["candidate_tensor_sha256"]
                != tick["candidate_tensor_sha256_after"]
                or pool["candidate_row_sha256"] != tick["candidate_row_sha256"]
                or pool["default_output_sha256"] != tick["default_output_sha256"]
            ):
                raise ValueError(
                    "candidate0 offline pool is not bound to the same-forward K8"
                )
    else:
        if candidate0_pool_evidence is not None:
            raise ValueError("method arms cannot consume candidate0 pool evidence")
        pool_ticks = [
            {
                "tick_index": index,
                "source_valid_mask": _bool_k8(
                    tick.get("source_valid_mask"), "source_valid_mask"
                ),
                "physical_feasible_mask": _bool_k8(
                    tick.get("physical_feasible_mask"), "physical_feasible_mask"
                ),
            }
            for index, tick in enumerate(ticks)
        ]
    selected = [int(tick["selected_index"]) for tick in ticks]
    if arm == "candidate0" and any(selected):
        raise ValueError("candidate0 must select index zero on every tick")
    if arm == "scene14d":
        _validate_scene_receipts(ticks)
    elif any("v25_scene_selector" in tick for tick in ticks):
        raise ValueError("only Scene14D may expose scene selector receipts")

    source_counts: list[int] = []
    high_risk = 0
    safe_pool = 0
    for expected_index, pool in enumerate(pool_ticks):
        if pool["tick_index"] != expected_index:
            raise ValueError("candidate-pool tick indices drifted")
        source = np.asarray(pool["source_valid_mask"], dtype=np.bool_)
        physical = np.asarray(pool["physical_feasible_mask"], dtype=np.bool_)
        if np.any(physical & ~source) or not source.any():
            raise ValueError("candidate-pool source/physical contract drifted")
        source_counts.append(int(np.sum(source)))
        high_risk += int(bool(source.all() and not physical.any()))
        safe_pool += int(bool(physical.any()))

    safety = _mapping(native, "safety")
    components = _mapping(safety, "components")
    safety_row = {
        "total": _finite_nonnegative(safety.get("safety_cost"), "SafetyCost"),
        **{
            name: _finite_nonnegative(components.get(source), f"safety.{name}")
            for name, source in _COMPONENT_MAP.items()
        },
    }
    secondary = _mapping(native, "secondary")
    performance = {
        name: _finite_nonnegative(secondary.get(source), f"performance.{name}")
        for name, source in _PERFORMANCE_MAP.items()
    }
    performance["maximum_deceleration"] = max(
        max(
            _finite_nonnegative(tick.get("pre_decision_speed_mps"), "pre speed")
            - _finite_nonnegative(_mapping(tick, "safety").get("speed_mps"), "post speed"),
            0.0,
        )
        / 0.1
        for tick in ticks
    )
    if set(performance) != set(NONINFERIORITY_METRICS):
        raise AssertionError("internal performance projection drifted")

    signal = _mapping(native, "signal_safety")
    if (
        signal.get("schema_version") != SIGNAL_SAFETY_SCHEMA_VERSION
        or signal.get("source_class") != metadata["signal_source_class"]
        or signal.get("future_phase_schedule_consumed") is not False
        or signal.get("phase_remaining_consumed") is not False
    ):
        raise ValueError("certified signal-safety authority drifted")
    signal_phase = _signal_phase(ticks, metadata["signal_source_class"])
    latency = _latency_series(ticks, arm)
    row = {
        "pair_key": pair_key,
        "arm": arm,
        "arm_order_index": arm_order_index,
        **pair_authority,
        "inference_cluster_id": _cluster_id(metadata),
        "benchmark_stratum": metadata["benchmark_stratum"],
        "scenario_family": metadata["scenario_family"],
        "tier": metadata["tier"],
        "source_class": metadata["signal_source_class"],
        "phase_authority_mode": metadata["phase_authority_mode"],
        "signal_phase": signal_phase,
        "status": "complete",
        "failure_class": None,
        "candidate_tensor_modified": False,
        "selected_index_sequence": selected,
        "source_valid_candidate_count_sequence": source_counts,
        "all_k_high_risk_tick_count": high_risk,
        "candidate_pool_has_safe_candidate_tick_count": safe_pool,
        "safety": safety_row,
        "performance": performance,
        "signal_safety": dict(_mapping(signal, "metrics")),
        "signal_safety_counts": dict(_mapping(signal, "counts")),
        "signal_safety_denominators": dict(_mapping(signal, "denominators")),
        "latency_ms": latency,
    }
    if set(row) != ROW_FIELDS:
        raise AssertionError("internal Fresh B2 row field set drifted")
    return row


def build_fresh_b2_failure_row(
    *,
    qualification_row: Mapping[str, Any],
    pair_key: str,
    arm: str,
    arm_order_index: int,
    status: str,
    failure_class: str,
    signal_phase: str,
    pair_authority: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = validate_fresh_b2_manifest_row(qualification_row)
    _pair_arm(pair_key, arm, arm_order_index)
    if status not in set(SCIENTIFIC_TERMINAL_STATUSES) - {"complete"}:
        raise ValueError("Fresh failure status is invalid")
    if type(failure_class) is not str or not failure_class:
        raise ValueError("Fresh failure class must be nonempty")
    if (
        status == "fixed_dp_candidate_generation_capability_failure"
        and failure_class != "invalid_k8_heading_norm_envelope"
    ):
        raise ValueError("Fresh fixed-DP capability failure taxonomy drifted")
    if (
        status == "source_ineligible"
        and failure_class != "preregistered_source_ineligible"
    ):
        raise ValueError("Fresh source-ineligible taxonomy drifted")
    authority = _validate_pair_authority(pair_authority, metadata)
    if metadata["signal_source_class"] == "no_signal":
        if signal_phase != "none":
            raise ValueError("no-signal failure row must use phase none")
    elif status == "source_ineligible":
        if signal_phase != "unavailable":
            raise ValueError(
                "mapped source-ineligible row must use unavailable phase"
            )
    elif signal_phase not in {"green", "yellow", "red", "mixed"}:
        raise ValueError(
            "mapped-signal failure row requires a frozen phase summary"
        )
    row = {
        "pair_key": pair_key,
        "arm": arm,
        "arm_order_index": arm_order_index,
        **authority,
        "inference_cluster_id": _cluster_id(metadata),
        "benchmark_stratum": metadata["benchmark_stratum"],
        "scenario_family": metadata["scenario_family"],
        "tier": metadata["tier"],
        "source_class": metadata["signal_source_class"],
        "phase_authority_mode": metadata["phase_authority_mode"],
        "signal_phase": signal_phase,
        "status": status,
        "failure_class": failure_class,
        "candidate_tensor_modified": False,
        "selected_index_sequence": None,
        "source_valid_candidate_count_sequence": None,
        "all_k_high_risk_tick_count": None,
        "candidate_pool_has_safe_candidate_tick_count": None,
        "safety": None,
        "performance": None,
        "signal_safety": None,
        "signal_safety_counts": None,
        "signal_safety_denominators": None,
        "latency_ms": None,
    }
    if set(row) != ROW_FIELDS:
        raise AssertionError("internal failed Fresh B2 row field set drifted")
    return row


def _native_receipt(value: Mapping[str, Any], arm: str) -> dict[str, Any]:
    if type(value) is not dict or value.get("status") != "ok":
        raise ValueError("Fresh complete row requires an ok native receipt")
    if value.get("fixed_dp_head") != FIXED_DP_HEAD:
        raise ValueError("Fresh native receipt fixed DP authority drifted")
    if (
        value.get("schema_version") != "v21_native_arm_receipt_v1"
        or value.get("claim_authorized") is not False
        or any(
            not _sha256(value.get(name))
            for name in (
                "route_sha256",
                "logical_map_sha256",
                "checkpoint_sha256",
                "args_sha256",
                "spawn_config_sha256",
                "initial_state_sha256",
                "initial_input_sha256",
            )
        )
        or type(value.get("scenario_seed")) is not int
    ):
        raise ValueError("Fresh native run authority drifted")
    expected_native_arm = "dp" if arm == "candidate0" else "camp"
    if value.get("arm") != expected_native_arm:
        raise ValueError("native arm identity drifted")
    # Historical B2/B3 receipts predate the versioned actual-native ABI and
    # remain independently reopenable under their frozen schemas.  Every B4
    # receipt carries the ABI hash and must pass the current production
    # validator; absence is not backfilled.
    if "actual_native_receipt_contract_sha256" in value:
        if (
            value["actual_native_receipt_contract_sha256"]
            != actual_native_receipt_contract_sha256()
        ):
            raise ValueError("Fresh actual-native ABI hash drifted")
        branch = {
            "candidate0": "candidate0_primary",
            "static14d": "static14d",
            "scene14d": "scene14d",
        }[arm]
        actual_native = dict(value)
        present_enrichment = (
            set(actual_native) & _EXECUTION_EVIDENCE_ENRICHMENT_FIELDS
        )
        if present_enrichment not in (
            set(),
            set(_EXECUTION_EVIDENCE_ENRICHMENT_FIELDS),
        ):
            raise ValueError(
                "Fresh execution evidence enrichment field set drifted"
            )
        if present_enrichment:
            if (
                type(
                    actual_native["fresh_decision_evidence_reference"]
                )
                is not dict
                or type(actual_native["fresh_decision_evidence_count"])
                is not int
                or actual_native["fresh_decision_evidence_count"] < 0
            ):
                raise ValueError(
                    "Fresh execution evidence enrichment type drifted"
                )
            for name in _EXECUTION_EVIDENCE_ENRICHMENT_FIELDS:
                actual_native.pop(name)
        value = validate_actual_native_receipt(
            actual_native,
            branch=branch,
            expected_ticks=FRESH_TICK_COUNT,
        )
    ticks = value.get("ticks")
    if type(ticks) is not list or len(ticks) != FRESH_TICK_COUNT:
        raise ValueError("Fresh native receipt must contain exactly 64 ticks")
    for index, tick in enumerate(ticks):
        if type(tick) is not dict or tick.get("tick_index") != index:
            raise ValueError("Fresh native tick sequence drifted")
        if arm == "candidate0" and tick.get("candidate0_action_first") is True:
            if (
                tick.get("selected_index") != 0
                or not _sha256(tick.get("input_sha256"))
                or not _sha256(tick.get("default_output_sha256"))
                or tick.get("selected_trajectory_sha256")
                != tick.get("default_output_sha256")
                or tick.get("selection_policy")
                != "candidate0_operational_default"
                or tick.get("score_contract")
                != "candidate0_operational_default"
                or tick.get("eligibility_mask_name")
                != "candidate0_operational_default"
                or tick.get("candidate0_operational_default") is not True
                or tick.get("candidate0_pool_evidence_collected_online") is not False
                or tick.get("candidate0_pool_evidence_required_post_action") is not True
                or tick.get("same_forward_claimed") is not False
                or any(
                    name in tick
                    for name in (
                        "candidate_tensor_sha256_before",
                        "candidate_tensor_sha256_after",
                        "candidate_row_sha256",
                        "default_candidate0_identity",
                    )
                )
            ):
                raise ValueError(
                    "Fresh candidate0 action-first native tick drifted"
                )
            continue
        if tick.get("candidate_tensor_sha256_before") != tick.get(
            "candidate_tensor_sha256_after"
        ):
            raise ValueError("Fresh candidate tensor was modified")
        selected = tick.get("selected_index")
        if type(selected) is not int or not 0 <= selected < 8:
            raise ValueError("Fresh selected index is invalid")
        rows = tick.get("candidate_row_sha256")
        default_sha = tick.get("default_output_sha256")
        selected_sha = tick.get("selected_trajectory_sha256")
        identity = tick.get("default_candidate0_identity")
        if (
            type(rows) is not list
            or len(rows) != 8
            or any(not _sha256(item) for item in rows)
            or not _sha256(default_sha)
            or not _sha256(selected_sha)
            or rows[0] != default_sha
            or rows[selected] != selected_sha
            or type(identity) is not dict
            or set(identity)
            != {
                "elementwise_equal",
                "max_abs_difference",
                "default_output_sha256",
                "candidate0_sha256",
                "native_ranked_k8",
            }
            or identity["elementwise_equal"] is not True
            or type(identity["max_abs_difference"]) is not float
            or identity["max_abs_difference"] != 0.0
            or identity["default_output_sha256"] != default_sha
            or identity["candidate0_sha256"] != rows[0]
            or identity["native_ranked_k8"] is not False
        ):
            raise ValueError("Fresh fixed-K8 candidate0/default identity drifted")
        if arm == "candidate0":
            if (
                tick.get("candidate0_operational_default") is not True
                or tick.get("selection_policy")
                != "candidate0_operational_default"
                or tick.get("score_contract") != "candidate0_operational_default"
                or tick.get("eligibility_mask_name")
                != "candidate0_operational_default"
            ):
                raise ValueError("Fresh candidate0 operational-default contract drifted")
        elif (
            tick.get("selection_policy") != "v22_source_valid"
            or tick.get("score_contract") != "score_k(w)=a_k^T w"
            or tick.get("eligibility_mask_name") != "source_valid_mask"
        ):
            raise ValueError("Fresh CAMP source-valid affine contract drifted")
    return dict(value)


def _pair_authority(
    metadata: Mapping[str, Any], native: Mapping[str, Any]
) -> dict[str, Any]:
    return _validate_pair_authority(
        {
            "route_identity_sha256": metadata["route_identity_sha256"],
            "semantic_parameter_block_sha256": metadata[
                "semantic_parameter_block_sha256"
            ],
            "native_route_sha256": native["route_sha256"],
            "logical_map_sha256": native["logical_map_sha256"],
            "scenario_seed": native["scenario_seed"],
            "spawn_config_sha256": native["spawn_config_sha256"],
            "initial_state_sha256": native["initial_state_sha256"],
            "initial_input_sha256": native["initial_input_sha256"],
        },
        metadata,
    )


def _validate_pair_authority(
    value: Mapping[str, Any], metadata: Mapping[str, Any]
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != PAIR_AUTHORITY_FIELDS:
        raise ValueError("Fresh paired run authority field set drifted")
    result = dict(value)
    for name in PAIR_AUTHORITY_FIELDS - {"scenario_seed"}:
        if not _sha256(result[name]):
            raise ValueError("Fresh paired run authority SHA drifted")
    if (
        type(result["scenario_seed"]) is not int
        or result["route_identity_sha256"] != metadata["route_identity_sha256"]
        or result["semantic_parameter_block_sha256"]
        != metadata["semantic_parameter_block_sha256"]
        or result["logical_map_sha256"] != metadata["map_file_sha256"]
    ):
        raise ValueError("Fresh paired run authority value drifted")
    return result


def _candidate0_pool(value: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if type(value) is not dict:
        raise ValueError("candidate0 offline pool evidence exact schema drifted")
    schema = value.get("schema_version")
    if schema == LEGACY_CANDIDATE0_POOL_SCHEMA_VERSION:
        fields = _LEGACY_POOL_FIELDS
        tick_fields = _LEGACY_POOL_TICK_FIELDS
        source = "same_forward_fixed_k8_pre_atom_boundary"
    elif schema == CANDIDATE0_POOL_SCHEMA_VERSION:
        fields = _POOL_FIELDS
        tick_fields = _POOL_TICK_FIELDS
        source = "post_action_same_tick_same_base_forward_supplementary"
    else:
        raise ValueError("candidate0 offline pool evidence schema drifted")
    if set(value) != fields:
        raise ValueError("candidate0 offline pool evidence exact schema drifted")
    if (
        value["candidate_tensor_source"] != source
        or value["candidate_tensor_modified"] is not False
        or value["outcome_fields_consumed"] != []
        or value["fresh_protocol_changed"] is not False
        or type(value["ticks"]) is not list
        or len(value["ticks"]) != FRESH_TICK_COUNT
    ):
        raise ValueError("candidate0 offline pool evidence authority drifted")
    if schema == CANDIDATE0_POOL_SCHEMA_VERSION and (
        value["same_forward_claimed"] is not False
        or value["pool_evidence_affects_action"] is not False
        or value["pool_evidence_affects_rng_or_next_tick"] is not False
    ):
        raise ValueError(
            "candidate0 supplementary pool influence contract drifted"
        )
    rows: list[dict[str, Any]] = []
    for index, tick in enumerate(value["ticks"]):
        if type(tick) is not dict or set(tick) != tick_fields:
            raise ValueError("candidate0 pool tick schema drifted")
        row = {
            "tick_index": tick["tick_index"],
            "candidate_tensor_sha256": tick["candidate_tensor_sha256"],
            "candidate_row_sha256": tick["candidate_row_sha256"],
            "default_output_sha256": tick["default_output_sha256"],
            "source_valid_mask": _bool_k8(
                tick["source_valid_mask"], "source_valid_mask"
            ),
            "physical_feasible_mask": _bool_k8(
                tick["physical_feasible_mask"], "physical_feasible_mask"
            ),
        }
        if schema == CANDIDATE0_POOL_SCHEMA_VERSION:
            row.update(
                {
                    "input_sha256": tick["input_sha256"],
                    "action_available_ns": _native_nonnegative_int(
                        tick["action_available_ns"], "action_available_ns"
                    ),
                    "supplementary_started_ns": _native_nonnegative_int(
                        tick["supplementary_started_ns"],
                        "supplementary_started_ns",
                    ),
                    "supplementary_completed_ns": _native_nonnegative_int(
                        tick["supplementary_completed_ns"],
                        "supplementary_completed_ns",
                    ),
                }
            )
            if (
                not _sha256(row["input_sha256"])
                or row["supplementary_started_ns"]
                < row["action_available_ns"]
                or row["supplementary_completed_ns"]
                < row["supplementary_started_ns"]
            ):
                raise ValueError(
                    "candidate0 supplementary pool timestamp/input drifted"
                )
        rows.append(row)
        if rows[-1]["tick_index"] != index:
            raise ValueError("candidate0 pool tick order drifted")
        if (
            not _sha256(rows[-1]["candidate_tensor_sha256"])
            or type(rows[-1]["candidate_row_sha256"]) is not list
            or len(rows[-1]["candidate_row_sha256"]) != 8
            or any(not _sha256(item) for item in rows[-1]["candidate_row_sha256"])
            or not _sha256(rows[-1]["default_output_sha256"])
            or rows[-1]["candidate_row_sha256"][0]
            != rows[-1]["default_output_sha256"]
        ):
            raise ValueError("candidate0 pool fixed-K8 identity drifted")
    return rows


def _project_supplementary_candidate0_tick(
    value: Mapping[str, Any], tick_index: int
) -> dict[str, Any]:
    if type(value) is not dict or value.get("tick_index") != tick_index:
        raise ValueError("supplementary candidate0 native tick order drifted")
    rows = value.get("candidate_row_sha256")
    identity = value.get("default_candidate0_identity")
    source = _bool_k8(value.get("source_valid_mask"), "source_valid_mask")
    physical = _bool_k8(
        value.get("physical_feasible_mask"), "physical_feasible_mask"
    )
    source_complete = _bool_k8(
        value.get("source_complete_mask"), "source_complete_mask"
    )
    if (
        value.get("candidate_tensor_sha256_before")
        != value.get("candidate_tensor_sha256_after")
        or not _sha256(value.get("candidate_tensor_sha256_before"))
        or type(rows) is not list
        or len(rows) != 8
        or any(not _sha256(item) for item in rows)
        or not _sha256(value.get("input_sha256"))
        or not _sha256(value.get("default_output_sha256"))
        or value.get("selected_trajectory_sha256")
        != value.get("default_output_sha256")
        or rows[0] != value.get("default_output_sha256")
        or value.get("selected_index") != 0
        or type(identity) is not dict
        or identity.get("elementwise_equal") is not True
        or identity.get("max_abs_difference") != 0.0
        or identity.get("default_output_sha256")
        != value.get("default_output_sha256")
        or identity.get("candidate0_sha256") != rows[0]
        or identity.get("native_ranked_k8") is not False
        or np.any(
            np.asarray(physical, dtype=np.bool_)
            & ~np.asarray(source, dtype=np.bool_)
        )
        or not any(source)
        or not _sha256(value.get("atom_matrix_sha256"))
    ):
        raise ValueError("supplementary candidate0 native tick authority drifted")
    latency = value.get("latency_ms")
    required_latency = {
        "input_materialization",
        "default_inference",
        "candidate_inference",
        "atom_materialization",
        "hook_total",
        "tracker",
        "total_planning",
    }
    if (
        type(latency) is not dict
        or set(latency) != required_latency
        or any(
            type(item) not in {int, float}
            or type(item) is bool
            or not math.isfinite(float(item))
            or float(item) < 0.0
            for item in latency.values()
        )
    ):
        raise ValueError("supplementary candidate0 latency schema drifted")
    return {
        "tick_index": tick_index,
        "input_sha256": value["input_sha256"],
        "candidate_tensor_sha256_before": value[
            "candidate_tensor_sha256_before"
        ],
        "candidate_tensor_sha256_after": value[
            "candidate_tensor_sha256_after"
        ],
        "candidate_row_sha256": list(rows),
        "default_output_sha256": value["default_output_sha256"],
        "selected_trajectory_sha256": value["selected_trajectory_sha256"],
        "default_candidate0_identity": dict(identity),
        "selected_index": 0,
        "source_valid_mask": source,
        "physical_feasible_mask": physical,
        "source_complete_mask": source_complete,
        "atom_matrix_sha256": value["atom_matrix_sha256"],
        "latency_ms": {name: float(latency[name]) for name in sorted(latency)},
        "planning_started_ns": _native_nonnegative_int(
            value.get("planning_started_ns"), "planning_started_ns"
        ),
        "action_available_ns": _native_nonnegative_int(
            value.get("action_available_ns"), "action_available_ns"
        ),
        "receipt_projected_ns": _native_nonnegative_int(
            value.get("receipt_projected_ns"), "receipt_projected_ns"
        ),
        "same_forward_claimed": False,
        "supplementary_only": True,
    }


def _supplementary_candidate0_native(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _SUPPLEMENTARY_NATIVE_FIELDS
        or value.get("schema_version")
        != CANDIDATE0_SUPPLEMENTARY_NATIVE_SCHEMA_VERSION
        or value.get("status") != "ok"
        or value.get("arm") != "dp"
        or value.get("fixed_dp_head") != FIXED_DP_HEAD
        or value.get("claim_authorized") is not False
        or value.get("outcome_fields_consumed") != []
        or value.get("actual_native_receipt_contract_sha256")
        != actual_native_receipt_contract_sha256()
        or type(value.get("scenario_seed")) is not int
    ):
        raise ValueError(
            "supplementary candidate0 native receipt exact schema drifted"
        )
    for name in (
        "route_sha256",
        "logical_map_sha256",
        "checkpoint_sha256",
        "args_sha256",
        "spawn_config_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
    ):
        if not _sha256(value.get(name)):
            raise ValueError(
                f"supplementary candidate0 native header drifted: {name}"
            )
    ticks = value.get("ticks")
    if type(ticks) is not list or len(ticks) != FRESH_TICK_COUNT:
        raise ValueError("supplementary candidate0 tick denominator drifted")
    result = dict(value)
    result["ticks"] = []
    for index, tick in enumerate(ticks):
        if (
            type(tick) is not dict
            or set(tick) != _SUPPLEMENTARY_NATIVE_TICK_FIELDS
            or tick.get("tick_index") != index
            or tick.get("same_forward_claimed") is not False
            or tick.get("supplementary_only") is not True
        ):
            raise ValueError(
                "supplementary candidate0 native tick schema drifted"
            )
        result["ticks"].append(
            _project_supplementary_candidate0_tick(tick, index)
        )
    return result


def _native_nonnegative_int(value: Any, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a native nonnegative int")
    return value


def _validate_scene_receipts(ticks: Sequence[Mapping[str, Any]]) -> None:
    fields = {
        "schema_version",
        "model_name",
        "fixed_dp_head",
        "training_root_sha256",
        "training_review_root_sha256",
        "theta_sha256",
        "context_scaler_sha256",
        "phi_sha256",
        "weights_sha256",
        "runtime_projection",
        "softmax",
    }
    authority: tuple[str, str, str, str, str] | None = None
    for tick in ticks:
        receipt = tick.get("v25_scene_selector")
        if (
            type(receipt) is not dict
            or set(receipt) != fields
            or receipt.get("schema_version")
            != "camp_dp_v25_scene_weight_receipt_v3"
            or receipt.get("model_name") != "CAMP-Scene14D"
            or receipt.get("fixed_dp_head") != FIXED_DP_HEAD
            or receipt.get("runtime_projection") is not False
            or receipt.get("softmax") is not False
            or any(
                not _sha256(receipt.get(name))
                for name in (
                    "training_root_sha256",
                    "training_review_root_sha256",
                    "theta_sha256",
                    "context_scaler_sha256",
                    "phi_sha256",
                    "weights_sha256",
                )
            )
        ):
            raise ValueError("Scene14D per-tick selector receipt drifted")
        current = tuple(
            receipt[name]
            for name in (
                "fixed_dp_head",
                "training_root_sha256",
                "training_review_root_sha256",
                "theta_sha256",
                "context_scaler_sha256",
            )
        )
        if authority is None:
            authority = current
        elif current != authority:
            raise ValueError("Scene14D authority changed inside a run")


def _latency_series(ticks: Sequence[Mapping[str, Any]], arm: str) -> dict[str, list[float]]:
    result: dict[str, list[float]] = {}
    required_camp = {"atoms", "selector"} if arm != "candidate0" else set()
    required_scene = {"context", "scene_weight"} if arm == "scene14d" else set()
    for stage in LATENCY_STAGES:
        source = _LATENCY_SOURCE[stage]
        values: list[float] = []
        for tick in ticks:
            latency = _mapping(tick, "latency_ms")
            if source in latency:
                value = _finite_nonnegative(latency[source], f"latency.{source}")
            elif arm == "candidate0" and stage == "additional_k8_generation":
                # Action-first holdout candidate0 keeps supplementary K8 work
                # outside the operational latency namespace.
                value = 0.0
            elif stage in {"atoms", "context", "scene_weight", "selector"} and (
                stage not in required_camp and stage not in required_scene
            ):
                value = 0.0
            else:
                raise ValueError(f"required latency stage is missing: {source}")
            values.append(value)
        result[stage] = values
    if arm == "candidate0" and any(
        any(result[stage]) for stage in ("atoms", "context", "scene_weight", "selector")
    ):
        raise ValueError("candidate0 cannot report CAMP-only latency")
    if arm == "static14d" and any(result["scene_weight"]):
        raise ValueError("Static14D cannot report Scene weight latency")
    if arm == "scene14d" and not all(value >= 0.0 for value in result["scene_weight"]):
        raise ValueError("Scene14D latency drifted")
    return result


def _signal_phase(ticks: Sequence[Mapping[str, Any]], source_class: str) -> str:
    phases = {
        _mapping(tick, "safety").get("signal_phase_at_interval_start")
        for tick in ticks
    }
    if source_class == "no_signal":
        if phases != {"none"}:
            raise ValueError("no-signal run exposed a signal phase")
        return "none"
    if not phases or not phases <= {"green", "yellow", "red"}:
        raise ValueError("mapped-signal phase sequence is invalid")
    return next(iter(phases)) if len(phases) == 1 else "mixed"


def _cluster_id(metadata: Mapping[str, Any]) -> str:
    if metadata["signal_source_class"] == "mapped_signal":
        unit = metadata["intersection_sha256"]
        if type(unit) is not str:
            raise ValueError("mapped signal row requires an intersection cluster")
        kind = "intersection"
    else:
        unit = metadata["corridor_sha256"]
        kind = "corridor"
    return f"{metadata['map_geometry_sha256']}:{kind}:{unit}"


def _pair_arm(pair_key: Any, arm: Any, arm_order_index: Any) -> None:
    if type(pair_key) is not str or not pair_key:
        raise ValueError("Fresh pair_key must be nonempty")
    if arm not in ARMS:
        raise ValueError("Fresh arm is invalid")
    if type(arm_order_index) is not int or arm_order_index not in (0, 1, 2):
        raise ValueError("Fresh arm order index is invalid")


def _bool_k8(value: Any, label: str) -> list[bool]:
    if type(value) is not list or len(value) != 8 or any(type(x) is not bool for x in value):
        raise ValueError(f"{label} must be native bool [8]")
    return list(value)


def _finite_nonnegative(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be native numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{label} must be finite nonnegative")
    return result


def _mapping(value: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    result = value.get(field)
    if type(result) is not dict:
        raise ValueError(f"{field} must be an exact object")
    return result


def _sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and not (set(value) - set("0123456789abcdef"))
    )
