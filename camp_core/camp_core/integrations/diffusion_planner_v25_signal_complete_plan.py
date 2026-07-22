from __future__ import annotations

from collections import Counter
import hashlib
import json
from typing import Any, Mapping

from .diffusion_planner_v25_signal_complete_maps import (
    SOURCE_FAMILY,
    build_signal_complete_suite,
    validate_signal_complete_suite,
)


SCHEMA_VERSION = "camp_dp_v25_signal_complete_execution_plan_v1"
EVENT_FAMILIES = (
    "lead_vehicle_hard_brake",
    "cut_in_merge",
    "pedestrian_cyclist_crossing",
    "unprotected_turn_oncoming_conflict",
    "red_light_phase_timing",
    "blocked_lane_static_obstacle",
    "narrow_encounter",
)
RISK_TIERS = ("easy", "borderline", "high_risk")
ARMS = (
    "candidate0_operational_default",
    "camp_static14d",
    "camp_scene14d_no_v2i",
)
PAPER_SUBSET_ABLATIONS = ("camp_static9d", "camp_scene9d_no_v2i")
NATURALISTIC_SCENARIO_FAMILY = "naturalistic_background"
NATURALISTIC_TIER = "naturalistic"
SPLIT_CONTRACT = {
    "calibration": {
        "seeds": (25301, 25302),
        "expected_routes": 50,
        "expected_maps": 5,
        "arms": (ARMS[0],),
    },
    "fresh_b2": {
        "seeds": (25401, 25402, 25403, 25404, 25405),
        "expected_routes": 100,
        "expected_maps": 25,
        "arms": ARMS,
    },
}

_TIER_PARAMETERS = {
    "easy": {
        "headway_m": 34.0,
        "ego_speed_mps": 7.0,
        "other_speed_mps": 7.0,
        "deceleration_mps2": -2.0,
        "trigger_time_s": 2.5,
        "lateral_offset_m": 4.0,
        "lateral_speed_mps": 0.6,
        "crossing_speed_mps": 1.2,
    },
    "borderline": {
        "headway_m": 22.0,
        "ego_speed_mps": 8.0,
        "other_speed_mps": 5.0,
        "deceleration_mps2": -4.0,
        "trigger_time_s": 1.5,
        "lateral_offset_m": 3.0,
        "lateral_speed_mps": 1.0,
        "crossing_speed_mps": 1.8,
    },
    "high_risk": {
        "headway_m": 14.0,
        "ego_speed_mps": 9.0,
        "other_speed_mps": 2.0,
        "deceleration_mps2": -6.0,
        "trigger_time_s": 0.8,
        "lateral_offset_m": 2.0,
        "lateral_speed_mps": 1.5,
        "crossing_speed_mps": 2.5,
    },
}


def build_signal_complete_execution_plan(split: str) -> dict[str, Any]:
    """Freeze an outcome-blind calibration or unopened Fresh B2 plan."""

    if split not in SPLIT_CONTRACT:
        raise ValueError(f"unknown signal-complete execution split: {split}")
    suite = build_signal_complete_suite(split)
    return _build_from_suite(split, suite)


def build_signal_complete_execution_plan_from_suite(
    split: str, suite: Mapping[str, Any]
) -> dict[str, Any]:
    """Build the plan from an explicitly supplied, already materialized suite."""

    if split not in SPLIT_CONTRACT:
        raise ValueError(f"unknown signal-complete execution split: {split}")
    if suite.get("split") != split:
        raise ValueError("signal-complete map suite split differs from plan split")
    return _build_from_suite(split, suite)


def validate_signal_complete_execution_plan(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("signal-complete execution plan must be a native mapping")
    split = value.get("split")
    if split not in SPLIT_CONTRACT:
        raise ValueError("signal-complete execution plan split drifted")
    expected = build_signal_complete_execution_plan(split)
    if not _strict_equal(value, expected):
        raise ValueError("signal-complete execution plan differs from reconstruction")
    return expected


def validate_calibration_fresh_zero_overlap(
    calibration: Mapping[str, Any], fresh_b2: Mapping[str, Any]
) -> dict[str, Any]:
    calibration_plan = validate_signal_complete_execution_plan(calibration)
    fresh_plan = validate_signal_complete_execution_plan(fresh_b2)
    calibration_rows = calibration_plan["identities"]
    fresh_rows = fresh_plan["identities"]
    checks = {
        "map_sha256": _disjoint(calibration_rows, fresh_rows, "map_sha256"),
        "corridor_sha256": _disjoint(
            calibration_rows, fresh_rows, "corridor_sha256"
        ),
        "route_identity_sha256": _disjoint(
            calibration_rows, fresh_rows, "route_identity_sha256"
        ),
        "source_independent_geometry_sha256": _disjoint(
            calibration_rows, fresh_rows, "source_independent_geometry_sha256"
        ),
        "scenario_identity_sha256": _disjoint(
            calibration_rows, fresh_rows, "scenario_identity_sha256"
        ),
        "semantic_parameter_block_sha256": _disjoint(
            calibration_rows, fresh_rows, "semantic_parameter_block_sha256"
        ),
        "seed_namespace": set(calibration_plan["seeds"]).isdisjoint(
            fresh_plan["seeds"]
        ),
    }
    if not all(checks.values()):
        raise ValueError("calibration/Fresh B2 zero-overlap contract failed")
    return {
        "schema_version": "camp_dp_v25_signal_complete_zero_overlap_v1",
        "status": "passed_signal_complete_zero_overlap",
        "checks": checks,
        "calibration_route_count": calibration_plan["route_count"],
        "fresh_b2_route_count": fresh_plan["route_count"],
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def _build_from_suite(split: str, suite: Mapping[str, Any]) -> dict[str, Any]:
    validated_suite = validate_signal_complete_suite(suite)
    contract = SPLIT_CONTRACT[split]
    rows = [row for item in validated_suite["maps"] for row in item["routes"]]
    if len(rows) != contract["expected_routes"]:
        raise ValueError("signal-complete route inventory drifted")
    identities = [
        _identity(split=split, route=row, ordinal=ordinal)
        for ordinal, row in enumerate(rows)
    ]
    units: list[dict[str, Any]] = []
    for identity in identities:
        for seed_index, seed in enumerate(contract["seeds"]):
            arms = list(contract["arms"])
            if split == "fresh_b2":
                offset = (identity["identity_ordinal"] + seed_index) % len(arms)
                arms = arms[offset:] + arms[:offset]
            unit_payload = {
                "scenario_identity_sha256": identity["scenario_identity_sha256"],
                "seed": seed,
                "ordered_arms": arms,
            }
            units.append(
                {
                    "unit_ordinal": len(units),
                    **unit_payload,
                    "unit_sha256": _canonical_sha(unit_payload),
                }
            )
    controlled = [
        row for row in identities if row["benchmark_stratum"] == "controlled_stress"
    ]
    family_tier = Counter(
        (row["scenario_family"], row["risk_tier"]) for row in controlled
    )
    family = Counter(row["scenario_family"] for row in identities)
    tier = Counter(row["risk_tier"] for row in identities)
    strata = Counter(row["benchmark_stratum"] for row in identities)
    plan = {
        "schema_version": SCHEMA_VERSION,
        "status": "outcome_blind_signal_complete_execution_plan_frozen",
        "split": split,
        "source_family": SOURCE_FAMILY,
        "map_count": validated_suite["map_count"],
        "intersection_count": validated_suite["corridor_count"],
        "corridor_count": validated_suite["corridor_count"],
        "route_count": len(identities),
        "identity_count": len(identities),
        "seeds": list(contract["seeds"]),
        "seeds_counted_as_independent": False,
        "execution_unit_count": len(units),
        "planned_arm_run_count": sum(len(unit["ordered_arms"]) for unit in units),
        "ticks_per_arm_run": 64,
        "identities": identities,
        "execution_units": units,
        "scenario_family_counts": {
            name: family[name] for name in (*EVENT_FAMILIES, NATURALISTIC_SCENARIO_FAMILY)
        },
        "risk_tier_counts": {
            name: tier[name] for name in (*RISK_TIERS, NATURALISTIC_TIER)
        },
        "benchmark_stratum_counts": {
            name: strata[name] for name in ("naturalistic", "controlled_stress")
        },
        "family_tier_counts": {
            f"{family_name}/{tier_name}": family_tier[(family_name, tier_name)]
            for family_name in EVENT_FAMILIES
            for tier_name in RISK_TIERS
        },
        "paired_arms": list(ARMS) if split == "fresh_b2" else [],
        "paper_subset_ablations": list(PAPER_SUBSET_ABLATIONS),
        "candidate_count": 8,
        "candidate0_semantics": "same_forward_operational_default_alias",
        "candidate_tensor_modified": False,
        "sequential_fixed_k8": True,
        "phase_remaining_available": False,
        "online_context_phase_program_consumed": False,
        "online_context_forbidden_fields": [
            "map_id",
            "route_id",
            "scenario_id",
            "split_id",
            "seed_id",
            "future_phase_program",
            "closed_loop_outcome",
            "fresh_outcome",
            "private_dp_latent",
        ],
        "failed_run_policy": "retain_denominator_no_replacement_no_imputation",
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "training_executed": False,
        "calibration_outcomes_consumed": False,
        "fixed_dp_modified": False,
    }
    _validate_counts(plan)
    return plan


def _identity(*, split: str, route: Mapping[str, Any], ordinal: int) -> dict[str, Any]:
    naturalistic = split == "fresh_b2" and ordinal % 4 == 0
    if naturalistic:
        family = NATURALISTIC_SCENARIO_FAMILY
        tier = NATURALISTIC_TIER
        variant = ordinal // 4
        parameters = {
            **_parameters_for_split("easy", split),
            "ego_speed_mps": 7.5,
            "variant": variant,
        }
        semantic_variant = NATURALISTIC_SCENARIO_FAMILY
        benchmark_stratum = "naturalistic"
    else:
        controlled_ordinal = (
            ordinal
            if split != "fresh_b2"
            else ordinal - (ordinal // 4 + 1)
        )
        family = EVENT_FAMILIES[controlled_ordinal % len(EVENT_FAMILIES)]
        tier = RISK_TIERS[
            (controlled_ordinal // len(EVENT_FAMILIES)) % len(RISK_TIERS)
        ]
        variant = controlled_ordinal // (len(EVENT_FAMILIES) * len(RISK_TIERS))
        parameters = {**_parameters_for_split(tier, split), "variant": variant}
        semantic_variant = _semantic_variant_name(family, variant, route)
        benchmark_stratum = "controlled_stress"
    phase_mode = (
        "controlled_same_tick_override"
        if family == "red_light_phase_timing"
        else "observe_same_tick_request"
    )
    controlled_phase = (
        {"easy": "green", "borderline": "yellow", "high_risk": "red"}[tier]
        if family == "red_light_phase_timing"
        else None
    )
    semantic_payload = {
        "scenario_family": family,
        "risk_tier": tier,
        "benchmark_stratum": benchmark_stratum,
        "semantic_variant": semantic_variant,
        "parameters": parameters,
        "phase_authority_mode": phase_mode,
        "controlled_current_phase": controlled_phase,
    }
    identity_payload = {
        "split": split,
        "route_identity_sha256": route["route_identity_sha256"],
        "semantic_parameter_block_sha256": _canonical_sha(semantic_payload),
    }
    return {
        "identity_ordinal": ordinal,
        "split": split,
        "scenario_identity_sha256": _canonical_sha(identity_payload),
        "map_sha256": route["map_sha256"],
        "map_geometry_sha256": route["map_geometry_sha256"],
        "map_relative_path": route["map_relative_path"],
        "corridor_sha256": route["corridor_sha256"],
        "intersection_sha256": route["intersection_sha256"],
        "route_identity_sha256": route["route_identity_sha256"],
        "route_family_sha256": route["route_family_sha256"],
        "source_independent_geometry_sha256": route[
            "source_independent_geometry_sha256"
        ],
        "physical_payload": route["physical_payload"],
        "source_chain_sha256": route["source_chain_sha256"],
        "source_chain": route["source_chain"],
        "initial_pose": route["initial_pose"],
        "goal_pose": route["goal_pose"],
        "route_spec": {
            "lanelet_ids": list(route["source_chain"]["route_lanelet_ids"]),
            "start_pose": list(route["initial_pose"]),
            "goal_pose": list(route["goal_pose"]),
        },
        "route_length_m": route["route_length_m"],
        "scenario_family": family,
        "risk_tier": tier,
        "benchmark_stratum": benchmark_stratum,
        "semantic_variant": semantic_variant,
        "variant_index": variant,
        "parameters": parameters,
        "semantic_parameter_block_sha256": _canonical_sha(semantic_payload),
        "signal_source_class": "mapped_signal",
        "phase_authority_mode": phase_mode,
        "controlled_current_phase": controlled_phase,
        "future_phase_program_present": False,
        "same_tick_current_phase_required": True,
        "phase_remaining_available": False,
        "source_timestamp_required": True,
        "decision_timestamp_required": True,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def _validate_counts(plan: Mapping[str, Any]) -> None:
    contract = SPLIT_CONTRACT[plan["split"]]
    if (
        plan["map_count"] != contract["expected_maps"]
        or plan["route_count"] != contract["expected_routes"]
        or any(value < 1 for value in plan["family_tier_counts"].values())
    ):
        raise ValueError("signal-complete plan coverage target failed")
    expected_units = contract["expected_routes"] * len(contract["seeds"])
    expected_arm_runs = expected_units * len(contract["arms"])
    if (
        plan["execution_unit_count"] != expected_units
        or plan["planned_arm_run_count"] != expected_arm_runs
    ):
        raise ValueError("signal-complete plan denominator drifted")


def _semantic_variant_name(
    family: str, variant: int, route: Mapping[str, Any]
) -> str:
    if family == "pedestrian_cyclist_crossing":
        return "cyclist_crossing" if variant % 2 else "pedestrian_crossing"
    if family == "unprotected_turn_oncoming_conflict":
        turn = max(abs(float(value)) for value in route["physical_payload"]["turn_angles_rad"])
        return "unprotected_turn" if turn >= 0.08 else "oncoming_conflict"
    return family


def _parameters_for_split(tier: str, split: str) -> dict[str, float]:
    values = dict(_TIER_PARAMETERS[tier])
    offsets = {
        "calibration": {
            "headway_m": 0.31,
            "ego_speed_mps": 0.11,
            "other_speed_mps": 0.07,
            "trigger_time_s": 0.07,
            "lateral_offset_m": 0.09,
            "crossing_speed_mps": 0.05,
        },
        "fresh_b2": {
            "headway_m": 0.67,
            "ego_speed_mps": 0.23,
            "other_speed_mps": 0.13,
            "trigger_time_s": 0.13,
            "lateral_offset_m": 0.17,
            "crossing_speed_mps": 0.09,
        },
    }[split]
    for name, delta in offsets.items():
        values[name] = round(values[name] + delta, 6)
    return values


def _disjoint(
    left: list[dict[str, Any]], right: list[dict[str, Any]], field: str
) -> bool:
    return set(row[field] for row in left).isdisjoint(row[field] for row in right)


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
