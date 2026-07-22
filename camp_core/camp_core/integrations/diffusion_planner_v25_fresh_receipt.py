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
from .diffusion_planner_v25_signal_safety import SIGNAL_SAFETY_SCHEMA_VERSION


CANDIDATE0_POOL_SCHEMA_VERSION = (
    "camp_dp_v25_candidate0_offline_candidate_pool_evidence_v2"
)
_POOL_FIELDS = {
    "schema_version",
    "candidate_tensor_source",
    "candidate_tensor_modified",
    "ticks",
    "outcome_fields_consumed",
    "fresh_protocol_changed",
}
_POOL_TICK_FIELDS = {
    "tick_index",
    "candidate_tensor_sha256",
    "candidate_row_sha256",
    "default_output_sha256",
    "source_valid_mask",
    "physical_feasible_mask",
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
) -> dict[str, Any]:
    """Project same-forward diagnostic masks without changing candidate0 selection."""

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
        "schema_version": CANDIDATE0_POOL_SCHEMA_VERSION,
        "candidate_tensor_source": "same_forward_fixed_k8_pre_atom_boundary",
        "candidate_tensor_modified": False,
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
        for tick, pool in zip(ticks, pool_ticks):
            if (
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
    if status not in {
        "fixed_dp_candidate_generation_capability_failure",
        "source_ineligible",
        "execution_failure",
    }:
        raise ValueError("Fresh failure status is invalid")
    if type(failure_class) is not str or not failure_class:
        raise ValueError("Fresh failure class must be nonempty")
    if (
        status == "fixed_dp_candidate_generation_capability_failure"
        and failure_class != "invalid_k8_heading_norm_envelope"
    ):
        raise ValueError("Fresh fixed-DP capability failure taxonomy drifted")
    authority = _validate_pair_authority(pair_authority, metadata)
    if metadata["signal_source_class"] == "no_signal":
        if signal_phase != "none":
            raise ValueError("no-signal failure row must use phase none")
    elif signal_phase not in {"green", "yellow", "red", "mixed"}:
        raise ValueError("mapped-signal failure row requires a frozen phase summary")
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
    ticks = value.get("ticks")
    if type(ticks) is not list or len(ticks) != FRESH_TICK_COUNT:
        raise ValueError("Fresh native receipt must contain exactly 64 ticks")
    for index, tick in enumerate(ticks):
        if type(tick) is not dict or tick.get("tick_index") != index:
            raise ValueError("Fresh native tick sequence drifted")
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
    if type(value) is not dict or set(value) != _POOL_FIELDS:
        raise ValueError("candidate0 offline pool evidence exact schema drifted")
    if (
        value["schema_version"] != CANDIDATE0_POOL_SCHEMA_VERSION
        or value["candidate_tensor_source"]
        != "same_forward_fixed_k8_pre_atom_boundary"
        or value["candidate_tensor_modified"] is not False
        or value["outcome_fields_consumed"] != []
        or value["fresh_protocol_changed"] is not False
        or type(value["ticks"]) is not list
        or len(value["ticks"]) != FRESH_TICK_COUNT
    ):
        raise ValueError("candidate0 offline pool evidence authority drifted")
    rows: list[dict[str, Any]] = []
    for index, tick in enumerate(value["ticks"]):
        if type(tick) is not dict or set(tick) != _POOL_TICK_FIELDS:
            raise ValueError("candidate0 pool tick schema drifted")
        rows.append(
            {
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
        )
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
