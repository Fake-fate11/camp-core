from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping

from .diffusion_planner_v25_signal_complete_plan import (
    ARMS,
    validate_signal_complete_execution_plan,
)


SCHEMA_VERSION = "camp_dp_v25_paired_calibration_execution_plan_v1"
PAIR_COUNT = 100
ARM_RUN_COUNT = 300
TICKS_PER_ARM_RUN = 64
TOTAL_TICK_CAPACITY = ARM_RUN_COUNT * TICKS_PER_ARM_RUN


def build_paired_calibration_execution_plan(
    calibration_plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Lift the reviewed candidate0 calibration denominator to three paired arms.

    The route/scenario/seed inventory is unchanged.  Only the preregistered arm
    rotation is added, before any CAMP calibration outcome is observed.
    """

    base = validate_signal_complete_execution_plan(calibration_plan)
    if (
        base["split"] != "calibration"
        or base["execution_unit_count"] != PAIR_COUNT
        or base["planned_arm_run_count"] != PAIR_COUNT
        or base["ticks_per_arm_run"] != TICKS_PER_ARM_RUN
    ):
        raise ValueError("paired calibration base denominator drifted")
    units: list[dict[str, Any]] = []
    for base_unit in base["execution_units"]:
        offset = int(base_unit["unit_ordinal"]) % len(ARMS)
        ordered_arms = list(ARMS[offset:] + ARMS[:offset])
        payload = {
            "scenario_identity_sha256": base_unit["scenario_identity_sha256"],
            "seed": base_unit["seed"],
            "ordered_arms": ordered_arms,
        }
        units.append(
            {
                "unit_ordinal": base_unit["unit_ordinal"],
                **payload,
                "unit_sha256": _canonical_sha(payload),
            }
        )
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "outcome_blind_paired_calibration_plan_frozen",
        "split": "calibration",
        "base_plan_sha256": _canonical_sha(base),
        "base_execution_unit_sha256_by_ordinal": [
            row["unit_sha256"] for row in base["execution_units"]
        ],
        "map_count": base["map_count"],
        "intersection_count": base["intersection_count"],
        "corridor_count": base["corridor_count"],
        "route_count": base["route_count"],
        "identity_count": base["identity_count"],
        "seed_count": len(base["seeds"]),
        "seeds": list(base["seeds"]),
        "seeds_counted_as_independent": False,
        "pair_count": len(units),
        "paired_arms": list(ARMS),
        "arm_run_count": sum(len(row["ordered_arms"]) for row in units),
        "ticks_per_arm_run": TICKS_PER_ARM_RUN,
        "total_tick_capacity": TOTAL_TICK_CAPACITY,
        "identities": copy.deepcopy(base["identities"]),
        "execution_units": units,
        "scenario_family_counts": copy.deepcopy(base["scenario_family_counts"]),
        "risk_tier_counts": copy.deepcopy(base["risk_tier_counts"]),
        "benchmark_stratum_counts": copy.deepcopy(
            base["benchmark_stratum_counts"]
        ),
        "family_tier_counts": copy.deepcopy(base["family_tier_counts"]),
        "candidate_count": 8,
        "candidate0_semantics": "same_forward_operational_default_alias",
        "independent_reset_per_arm": True,
        "same_initial_state_and_exogenous_schedule_per_pair": True,
        "sequential_fixed_k8": True,
        "candidate_tensor_modified": False,
        "trajectory_postprocess_authorized": False,
        "phase_remaining_available": False,
        "v2i_enabled": False,
        "training_executed": False,
        "calibration_outcomes_consumed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
        "failed_run_policy": "retain_pair_denominator_no_replacement_no_imputation",
    }
    return validate_paired_calibration_execution_plan(result, calibration_plan=base)


def validate_paired_calibration_execution_plan(
    value: Mapping[str, Any],
    *,
    calibration_plan: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("paired calibration plan must be a native mapping")
    expected = _build_without_validation(calibration_plan)
    if not _strict_equal(value, expected):
        raise ValueError("paired calibration plan differs from reconstruction")
    return expected


def _build_without_validation(calibration_plan: Mapping[str, Any]) -> dict[str, Any]:
    base = validate_signal_complete_execution_plan(calibration_plan)
    if (
        base["split"] != "calibration"
        or base["execution_unit_count"] != PAIR_COUNT
        or base["planned_arm_run_count"] != PAIR_COUNT
        or base["ticks_per_arm_run"] != TICKS_PER_ARM_RUN
    ):
        raise ValueError("paired calibration base denominator drifted")
    units: list[dict[str, Any]] = []
    for base_unit in base["execution_units"]:
        offset = int(base_unit["unit_ordinal"]) % len(ARMS)
        ordered_arms = list(ARMS[offset:] + ARMS[:offset])
        payload = {
            "scenario_identity_sha256": base_unit["scenario_identity_sha256"],
            "seed": base_unit["seed"],
            "ordered_arms": ordered_arms,
        }
        units.append(
            {
                "unit_ordinal": base_unit["unit_ordinal"],
                **payload,
                "unit_sha256": _canonical_sha(payload),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "outcome_blind_paired_calibration_plan_frozen",
        "split": "calibration",
        "base_plan_sha256": _canonical_sha(base),
        "base_execution_unit_sha256_by_ordinal": [
            row["unit_sha256"] for row in base["execution_units"]
        ],
        "map_count": base["map_count"],
        "intersection_count": base["intersection_count"],
        "corridor_count": base["corridor_count"],
        "route_count": base["route_count"],
        "identity_count": base["identity_count"],
        "seed_count": len(base["seeds"]),
        "seeds": list(base["seeds"]),
        "seeds_counted_as_independent": False,
        "pair_count": len(units),
        "paired_arms": list(ARMS),
        "arm_run_count": sum(len(row["ordered_arms"]) for row in units),
        "ticks_per_arm_run": TICKS_PER_ARM_RUN,
        "total_tick_capacity": TOTAL_TICK_CAPACITY,
        "identities": copy.deepcopy(base["identities"]),
        "execution_units": units,
        "scenario_family_counts": copy.deepcopy(base["scenario_family_counts"]),
        "risk_tier_counts": copy.deepcopy(base["risk_tier_counts"]),
        "benchmark_stratum_counts": copy.deepcopy(
            base["benchmark_stratum_counts"]
        ),
        "family_tier_counts": copy.deepcopy(base["family_tier_counts"]),
        "candidate_count": 8,
        "candidate0_semantics": "same_forward_operational_default_alias",
        "independent_reset_per_arm": True,
        "same_initial_state_and_exogenous_schedule_per_pair": True,
        "sequential_fixed_k8": True,
        "candidate_tensor_modified": False,
        "trajectory_postprocess_authorized": False,
        "phase_remaining_available": False,
        "v2i_enabled": False,
        "training_executed": False,
        "calibration_outcomes_consumed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
        "failed_run_policy": "retain_pair_denominator_no_replacement_no_imputation",
    }


def _canonical_sha(value: Any) -> str:
    raw = (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)
