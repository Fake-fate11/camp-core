from __future__ import annotations

from collections import defaultdict
import math
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner_v21_native import safety_cost_native_v1
from .diffusion_planner_v25_signal_complete_plan import (
    validate_signal_complete_execution_plan,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
POWER_PILOT_ROW_SCHEMA_VERSION = "camp_dp_v25_candidate0_power_pilot_row_v1"
POWER_PILOT_RECEIPT_SCHEMA_VERSION = "camp_dp_v25_power_pilot_variance_receipt_v1"
RED_FAMILY = "red_light_phase_timing"


def project_candidate0_power_pilot_rows(
    plan: Mapping[str, Any], run_results: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Project reviewed candidate0 calibration results into cluster-pilot rows."""

    validated = validate_signal_complete_execution_plan(plan)
    if validated["split"] != "calibration":
        raise ValueError("power pilot projection requires the calibration plan")
    results = list(run_results)
    units = validated["execution_units"]
    identities = {
        row["scenario_identity_sha256"]: row for row in validated["identities"]
    }
    if len(results) != len(units):
        raise ValueError("power pilot planned denominator drifted")
    rows: list[dict[str, Any]] = []
    retained = 0
    for unit, result in zip(units, results, strict=True):
        identity = identities[unit["scenario_identity_sha256"]]
        if (
            type(result) is not dict
            or result.get("unit_ordinal") != unit["unit_ordinal"]
            or result.get("unit_sha256") != unit["unit_sha256"]
            or result.get("scenario_identity_sha256")
            != unit["scenario_identity_sha256"]
            or result.get("route_identity_sha256")
            != identity["route_identity_sha256"]
            or result.get("seed") != unit["seed"]
            or result.get("fresh_b2_opened") is not False
            or result.get("fresh_outcome_fields_consumed") != []
        ):
            raise ValueError("power pilot run-result authority drifted")
        if result.get("status") == "retained_fixed_dp_capability_failure":
            retained += 1
            continue
        if result.get("status") != "complete" or result.get("failure_receipt") is not None:
            raise ValueError("power pilot run result status drifted")
        native = result.get("native_receipt")
        if (
            type(native) is not dict
            or native.get("schema_version") != "v21_native_arm_receipt_v1"
            or native.get("status") != "ok"
            or native.get("arm") != "dp"
            or native.get("fixed_dp_head") != FIXED_DP_HEAD
            or native.get("scenario_seed") != unit["seed"]
            or native.get("claim_authorized") is not False
        ):
            raise ValueError("power pilot candidate0 native receipt drifted")
        safety = native.get("safety")
        if type(safety) is not dict or safety.get("schema_version") not in {
            "safety_cost_native_v1",
            "safety_cost_native_v22",
        }:
            raise ValueError("power pilot safety summary drifted")
        components = safety.get("components")
        if type(components) is not dict:
            raise ValueError("power pilot safety components are missing")
        total = safety_cost_native_v1(components)
        recorded = _finite_nonnegative(safety.get("safety_cost"), "safety_cost")
        if not math.isclose(total, recorded, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("power pilot SafetyCost differs from components")
        red_raw = _finite_nonnegative(
            components.get("red_light_violation_any"),
            "red_light_violation_any",
        )
        red_applicable = identity["scenario_family"] == RED_FAMILY
        rows.append(
            {
                "schema_version": POWER_PILOT_ROW_SCHEMA_VERSION,
                "arm": "candidate0_operational_default",
                "cluster_id": identity["corridor_sha256"],
                "scenario_family": identity["scenario_family"],
                "safety_cost_total": float(total),
                "red_light_safety_cost_component": float(30.0 * red_raw),
                "red_component_applicable": red_applicable,
                "fresh_b2_opened": False,
                "fresh_outcome_fields_consumed": [],
            }
        )
    if len(rows) + retained != len(results) or len(rows) / len(results) < 0.95:
        raise ValueError("power pilot complete coverage is below 95 percent")
    return [validate_power_pilot_row(row) for row in rows]


def build_power_pilot_variance_receipt(
    rows: Sequence[Mapping[str, Any]],
    *,
    source_artifact_root_sha256: str,
    source_split: str = "calibration_pilot",
) -> dict[str, Any]:
    _require_sha(source_artifact_root_sha256, "source_artifact_root_sha256")
    if source_split not in {"train_pilot", "calibration_pilot"}:
        raise ValueError("power pilot source split drifted")
    validated = [validate_power_pilot_row(row) for row in rows]
    total_by_cluster: dict[str, list[float]] = defaultdict(list)
    red_by_cluster: dict[str, list[float]] = defaultdict(list)
    for row in validated:
        total_by_cluster[row["cluster_id"]].append(row["safety_cost_total"])
        if row["red_component_applicable"]:
            red_by_cluster[row["cluster_id"]].append(
                row["red_light_safety_cost_component"]
            )
    total_means = [float(np.mean(values)) for values in total_by_cluster.values()]
    red_means = [float(np.mean(values)) for values in red_by_cluster.values()]
    if len(total_means) < 2 or len(red_means) < 2:
        raise ValueError("power pilot requires at least two total and red clusters")
    return {
        "schema_version": POWER_PILOT_RECEIPT_SCHEMA_VERSION,
        "status": "sealed_train_or_calibration_pilot_variance",
        "source_artifact_root_sha256": source_artifact_root_sha256,
        "source_split": source_split,
        "calibration_arm": "candidate0_operational_default",
        "cluster_estimator": "equal_mass_independent_cluster_standard_deviation",
        "variance_target": "candidate0_safety_cost_proxy_disclosed_not_paired_delta",
        "safety_cost_cluster_standard_deviation": float(
            np.std(np.asarray(total_means, dtype=np.float64), ddof=1)
        ),
        "red_component_cluster_standard_deviation": float(
            np.std(np.asarray(red_means, dtype=np.float64), ddof=1)
        ),
        "total_independent_cluster_count": len(total_means),
        "red_independent_cluster_count": len(red_means),
        "camp_method_outcomes_consumed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }


def validate_power_pilot_row(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "schema_version",
        "arm",
        "cluster_id",
        "scenario_family",
        "safety_cost_total",
        "red_light_safety_cost_component",
        "red_component_applicable",
        "fresh_b2_opened",
        "fresh_outcome_fields_consumed",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("power pilot row field set drifted")
    if (
        value.get("schema_version") != POWER_PILOT_ROW_SCHEMA_VERSION
        or value.get("arm") != "candidate0_operational_default"
        or type(value.get("cluster_id")) is not str
        or not value["cluster_id"]
        or type(value.get("scenario_family")) is not str
        or not value["scenario_family"]
        or type(value.get("red_component_applicable")) is not bool
        or value["red_component_applicable"]
        is not (value["scenario_family"] == RED_FAMILY)
        or value.get("fresh_b2_opened") is not False
        or value.get("fresh_outcome_fields_consumed") != []
    ):
        raise ValueError("power pilot row authority drifted")
    total = _finite_nonnegative(value["safety_cost_total"], "safety_cost_total")
    red = _finite_nonnegative(
        value["red_light_safety_cost_component"],
        "red_light_safety_cost_component",
    )
    return {
        **dict(value),
        "safety_cost_total": total,
        "red_light_safety_cost_component": red,
    }


def validate_power_pilot_variance_receipt(
    value: Mapping[str, Any], *, expected_root_sha256: str
) -> dict[str, Any]:
    _require_sha(expected_root_sha256, "expected_root_sha256")
    fields = {
        "schema_version",
        "status",
        "source_artifact_root_sha256",
        "source_split",
        "calibration_arm",
        "cluster_estimator",
        "variance_target",
        "safety_cost_cluster_standard_deviation",
        "red_component_cluster_standard_deviation",
        "total_independent_cluster_count",
        "red_independent_cluster_count",
        "camp_method_outcomes_consumed",
        "fresh_b2_opened",
        "fresh_outcome_fields_consumed",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("power pilot receipt field set drifted")
    exact = {
        "schema_version": POWER_PILOT_RECEIPT_SCHEMA_VERSION,
        "status": "sealed_train_or_calibration_pilot_variance",
        "source_artifact_root_sha256": expected_root_sha256,
        "calibration_arm": "candidate0_operational_default",
        "cluster_estimator": "equal_mass_independent_cluster_standard_deviation",
        "variance_target": "candidate0_safety_cost_proxy_disclosed_not_paired_delta",
        "camp_method_outcomes_consumed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    if any(type(value.get(name)) is not type(expected) or value.get(name) != expected for name, expected in exact.items()):
        raise ValueError("power pilot receipt exact value drifted")
    if value.get("source_split") not in {"train_pilot", "calibration_pilot"}:
        raise ValueError("power pilot source split drifted")
    for name in (
        "safety_cost_cluster_standard_deviation",
        "red_component_cluster_standard_deviation",
    ):
        _finite_nonnegative(value.get(name), name)
    for name in ("total_independent_cluster_count", "red_independent_cluster_count"):
        if type(value.get(name)) is not int or value[name] < 2:
            raise ValueError(f"power pilot {name} drifted")
    return dict(value)


def _finite_nonnegative(value: Any, name: str) -> float:
    if type(value) not in {int, float} or type(value) is bool:
        raise ValueError(f"power pilot {name} must be a native number")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"power pilot {name} must be finite and nonnegative")
    return result


def _require_sha(value: Any, name: str) -> str:
    if type(value) is not str or len(value) != 64 or set(value) - set("0123456789abcdef"):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return value
