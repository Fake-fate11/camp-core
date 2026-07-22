from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner_v25_signal_complete_plan import (
    EVENT_FAMILIES,
    RISK_TIERS,
    validate_signal_complete_execution_plan,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_b2_explicit_coverage_v1"
ROW_SCHEMA_VERSION = "camp_dp_v25_fresh_b2_explicit_coverage_row_v1"
ROW_FIELDS = frozenset(
    {
        "schema_version",
        "identity_ordinal",
        "scenario_identity_sha256",
        "route_identity_sha256",
        "map_file_sha256",
        "map_geometry_sha256",
        "intersection_sha256",
        "corridor_sha256",
        "route_family_sha256",
        "semantic_parameter_block_sha256",
        "benchmark_stratum",
        "scenario_family",
        "risk_tier",
        "source_class",
        "phase_authority_mode",
        "controlled_current_phase",
        "movement",
        "maximum_route_turn_rad",
        "stop_line_route_arc_m",
        "initial_speed_mps",
        "headway_m",
        "trigger_time_s",
        "lead_stop",
        "lead_stop_rule",
        "occlusion",
        "occlusion_rule",
        "dilemma_zone",
        "dilemma_zone_time_to_stop_line_s",
        "dilemma_zone_interval_s",
        "all_k_bad_eligibility",
        "all_k_bad_eligibility_rule",
        "static_signal_chain_qualified",
        "runtime_same_tick_signal_required",
        "runtime_k8_support_required",
        "preopen_dp_forward_executed",
        "fresh_b2_opened",
        "outcome_fields_consumed",
    }
)


def build_fresh_b2_explicit_coverage(
    plan: Mapping[str, Any],
    *,
    prepared_runtime_cases: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Freeze outcome-blind coverage from physical plan/runtime inputs only."""

    frozen = validate_signal_complete_execution_plan(plan)
    if frozen["split"] != "fresh_b2":
        raise ValueError("Fresh B2 coverage requires the unopened Fresh plan")
    by_scenario = _runtime_cases(prepared_runtime_cases)
    expected = {row["scenario_identity_sha256"] for row in frozen["identities"]}
    if set(by_scenario) != expected:
        raise ValueError("Fresh B2 coverage runtime denominator drifted")
    rows = [
        _coverage_row(identity, by_scenario[identity["scenario_identity_sha256"]])
        for identity in frozen["identities"]
    ]
    census = _census(rows, frozen)
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_outcome_blind_explicit_coverage",
        "coverage_rows": rows,
        "coverage_rows_sha256": _canonical_sha(rows),
        "census": census,
        "runtime_same_tick_signal_receipts_deferred_to_execution": True,
        "actual_fixed_k8_support_deferred_to_execution": True,
        "preopen_model_loaded": False,
        "preopen_dp_forward_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    return validate_fresh_b2_explicit_coverage(result, plan=frozen)


def validate_fresh_b2_explicit_coverage(
    value: Mapping[str, Any], *, plan: Mapping[str, Any]
) -> dict[str, Any]:
    fields = {
        "schema_version",
        "status",
        "coverage_rows",
        "coverage_rows_sha256",
        "census",
        "runtime_same_tick_signal_receipts_deferred_to_execution",
        "actual_fixed_k8_support_deferred_to_execution",
        "preopen_model_loaded",
        "preopen_dp_forward_executed",
        "fresh_b2_opened",
        "outcome_fields_consumed",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("Fresh B2 coverage field set drifted")
    exact = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_outcome_blind_explicit_coverage",
        "runtime_same_tick_signal_receipts_deferred_to_execution": True,
        "actual_fixed_k8_support_deferred_to_execution": True,
        "preopen_model_loaded": False,
        "preopen_dp_forward_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    if any(not _strict_equal(value.get(key), item) for key, item in exact.items()):
        raise ValueError("Fresh B2 coverage authority drifted")
    frozen = validate_signal_complete_execution_plan(plan)
    rows = value.get("coverage_rows")
    if type(rows) is not list or len(rows) != frozen["identity_count"]:
        raise ValueError("Fresh B2 coverage denominator drifted")
    validated = [_validate_row(row, index=index) for index, row in enumerate(rows)]
    if value.get("coverage_rows_sha256") != _canonical_sha(validated):
        raise ValueError("Fresh B2 coverage row SHA drifted")
    identities = frozen["identities"]
    for index, (row, identity) in enumerate(zip(validated, identities, strict=True)):
        for name in (
            "identity_ordinal",
            "scenario_identity_sha256",
            "route_identity_sha256",
            "map_geometry_sha256",
            "intersection_sha256",
            "corridor_sha256",
            "route_family_sha256",
            "semantic_parameter_block_sha256",
            "benchmark_stratum",
            "scenario_family",
            "risk_tier",
            "phase_authority_mode",
            "controlled_current_phase",
        ):
            if row[name] != identity[name if name != "risk_tier" else "risk_tier"]:
                raise ValueError(f"Fresh B2 coverage identity {index} {name} drifted")
        if row["map_file_sha256"] != identity["map_sha256"]:
            raise ValueError("Fresh B2 coverage map SHA drifted")
    expected_census = _census(validated, frozen)
    if not _strict_equal(value.get("census"), expected_census):
        raise ValueError("Fresh B2 coverage census drifted")
    return {**dict(value), "coverage_rows": validated, "census": expected_census}


def _coverage_row(identity: Mapping[str, Any], prepared: Mapping[str, Any]) -> dict[str, Any]:
    if (
        prepared.get("status") != "signal_complete_runtime_case_source_qualified"
        or prepared.get("scenario_identity_sha256") != identity["scenario_identity_sha256"]
        or prepared.get("model_loaded") is not False
        or prepared.get("candidate_generation_executed") is not False
        or prepared.get("fresh_b2_opened") is not False
        or prepared.get("outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh B2 static runtime case drifted")
    chain = prepared.get("mapped_signal_authority")
    if (
        type(chain) is not dict
        or chain.get("route_identity_sha256") != identity["route_identity_sha256"]
        or chain.get("source_map_sha256") != identity["map_sha256"]
        or chain.get("phase_remaining_available") is not False
    ):
        raise ValueError("Fresh B2 static signal chain drifted")
    source = identity["source_chain"]
    exact_static_bindings = {
        "regulatory_element_ids": [source["traffic_light_regulatory_element_id"]],
        "physical_light_ids": [source["physical_traffic_light_id"]],
        "bulb_ids": [source["light_bulb_linestring_id"]],
        "controlled_lanelet_ids": [source["controlled_lanelet_id"]],
        "route_lanelet_ids": list(source["route_lanelet_ids"]),
        "stop_line_id": source["certified_stop_line_id"],
    }
    if any(chain.get(name) != item for name, item in exact_static_bindings.items()):
        raise ValueError("Fresh B2 static regulatory binding drifted")
    case = prepared.get("case")
    if type(case) is not dict or type(case.get("actors")) is not list:
        raise ValueError("Fresh B2 static case actors are missing")
    physical = identity["physical_payload"]
    turns = [abs(float(item)) for item in physical["turn_angles_rad"]]
    maximum_turn = max(turns)
    speed = float(identity["parameters"]["ego_speed_mps"])
    stop_arc = float(chain["route_arc_m"])
    if not all(math.isfinite(item) and item >= 0.0 for item in (maximum_turn, speed, stop_arc)):
        raise ValueError("Fresh B2 numeric coverage source is invalid")
    actors = [dict(item) for item in case["actors"]]
    lead_stop = _lead_stop(actors)
    occlusion = _occlusion(identity, actors)
    time_to_stop = stop_arc / speed if speed > 0.0 else math.inf
    dilemma = (
        identity["controlled_current_phase"] == "yellow"
        and 3.0 <= time_to_stop <= 5.0
    )
    parameters = identity["parameters"]
    all_k_bad = (
        float(parameters["headway_m"]) / max(speed, 1e-9) <= 2.0
        or abs(float(parameters["deceleration_mps2"])) >= 6.0
        or float(parameters["lateral_offset_m"]) <= 2.2
        or (identity["controlled_current_phase"] == "red" and time_to_stop <= 4.5)
    )
    return _validate_row(
        {
            "schema_version": ROW_SCHEMA_VERSION,
            "identity_ordinal": identity["identity_ordinal"],
            "scenario_identity_sha256": identity["scenario_identity_sha256"],
            "route_identity_sha256": identity["route_identity_sha256"],
            "map_file_sha256": identity["map_sha256"],
            "map_geometry_sha256": identity["map_geometry_sha256"],
            "intersection_sha256": identity["intersection_sha256"],
            "corridor_sha256": identity["corridor_sha256"],
            "route_family_sha256": identity["route_family_sha256"],
            "semantic_parameter_block_sha256": identity["semantic_parameter_block_sha256"],
            "benchmark_stratum": identity["benchmark_stratum"],
            "scenario_family": identity["scenario_family"],
            "risk_tier": identity["risk_tier"],
            "source_class": identity["signal_source_class"],
            "phase_authority_mode": identity["phase_authority_mode"],
            "controlled_current_phase": identity["controlled_current_phase"],
            "movement": "turn" if maximum_turn >= 0.08 else "straight",
            "maximum_route_turn_rad": maximum_turn,
            "stop_line_route_arc_m": stop_arc,
            "initial_speed_mps": speed,
            "headway_m": float(parameters["headway_m"]),
            "trigger_time_s": float(parameters["trigger_time_s"]),
            "lead_stop": lead_stop,
            "lead_stop_rule": "physical_actor_stationary_or_stops_within_6_4s_in_route_envelope",
            "occlusion": occlusion,
            "occlusion_rule": "stationary_vehicle_obb_intersects_ego_to_vulnerable_actor_line_of_sight",
            "dilemma_zone": dilemma,
            "dilemma_zone_time_to_stop_line_s": time_to_stop,
            "dilemma_zone_interval_s": [3.0, 5.0],
            "all_k_bad_eligibility": all_k_bad,
            "all_k_bad_eligibility_rule": "outcome_blind_numeric_stress_envelope_actual_k8_support_deferred",
            "static_signal_chain_qualified": True,
            "runtime_same_tick_signal_required": True,
            "runtime_k8_support_required": True,
            "preopen_dp_forward_executed": False,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        },
        index=identity["identity_ordinal"],
    )


def _lead_stop(actors: Sequence[Mapping[str, Any]]) -> bool:
    for actor in actors:
        if actor.get("agent_type") != "vehicle":
            continue
        speed = float(actor["longitudinal_speed_mps"])
        acceleration = float(actor["longitudinal_acceleration_mps2"])
        lateral = abs(float(actor["lateral_offset_m"]))
        if lateral <= 2.5 and speed == 0.0:
            return True
        if lateral <= 2.5 and speed > 0.0 and acceleration < 0.0:
            if speed / -acceleration <= 6.4:
                return True
    return False


def _occlusion(identity: Mapping[str, Any], actors: Sequence[Mapping[str, Any]]) -> bool:
    vulnerable = next(
        (item for item in actors if item.get("agent_type") in {"pedestrian", "bicycle"}),
        None,
    )
    if vulnerable is None:
        return False
    start = np.asarray(identity["initial_pose"][:2], dtype=np.float64)
    end = np.asarray(vulnerable["initial_xy"], dtype=np.float64)
    delta = end - start
    denominator = float(np.dot(delta, delta))
    if denominator <= 0.0:
        raise ValueError("Fresh B2 occlusion line of sight is degenerate")
    for actor in actors:
        if actor is vulnerable or actor.get("agent_type") != "vehicle":
            continue
        if abs(float(actor["longitudinal_speed_mps"])) > 1e-12:
            continue
        point = np.asarray(actor["initial_xy"], dtype=np.float64)
        ratio = float(np.dot(point - start, delta) / denominator)
        if not 0.0 < ratio < 1.0:
            continue
        distance = float(np.linalg.norm(point - (start + ratio * delta)))
        half_diagonal = 0.5 * math.hypot(float(actor["length_m"]), float(actor["width_m"]))
        if distance <= half_diagonal:
            return True
    return False


def _runtime_cases(values: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for value in values:
        if type(value) is not dict:
            raise ValueError("Fresh B2 prepared runtime case must be a native mapping")
        scenario = value.get("scenario_identity_sha256")
        _require_sha(scenario, "scenario_identity_sha256")
        if scenario in result:
            raise ValueError("Fresh B2 prepared runtime scenario is duplicated")
        result[scenario] = dict(value)
    return result


def _validate_row(value: Mapping[str, Any], *, index: int) -> dict[str, Any]:
    if type(value) is not dict or set(value) != ROW_FIELDS:
        raise ValueError(f"Fresh B2 coverage row {index} field set drifted")
    result = dict(value)
    for name in (
        "scenario_identity_sha256",
        "route_identity_sha256",
        "map_file_sha256",
        "map_geometry_sha256",
        "intersection_sha256",
        "corridor_sha256",
        "route_family_sha256",
        "semantic_parameter_block_sha256",
    ):
        _require_sha(result[name], name)
    if type(result["identity_ordinal"]) is not int or result["identity_ordinal"] != index:
        raise ValueError("Fresh B2 coverage identity ordinal drifted")
    if result["schema_version"] != ROW_SCHEMA_VERSION:
        raise ValueError("Fresh B2 coverage row schema drifted")
    if result["scenario_family"] not in {*EVENT_FAMILIES, "naturalistic_background"}:
        raise ValueError("Fresh B2 coverage family drifted")
    if result["risk_tier"] not in {*RISK_TIERS, "naturalistic"}:
        raise ValueError("Fresh B2 coverage tier drifted")
    if result["movement"] not in {"straight", "turn"}:
        raise ValueError("Fresh B2 movement coverage drifted")
    if result["controlled_current_phase"] not in {None, "green", "yellow", "red"}:
        raise ValueError("Fresh B2 controlled phase drifted")
    for name in (
        "lead_stop",
        "occlusion",
        "dilemma_zone",
        "all_k_bad_eligibility",
        "static_signal_chain_qualified",
        "runtime_same_tick_signal_required",
        "runtime_k8_support_required",
        "preopen_dp_forward_executed",
        "fresh_b2_opened",
    ):
        if type(result[name]) is not bool:
            raise ValueError(f"Fresh B2 coverage {name} must be a native bool")
    for name in (
        "maximum_route_turn_rad",
        "stop_line_route_arc_m",
        "initial_speed_mps",
        "headway_m",
        "trigger_time_s",
        "dilemma_zone_time_to_stop_line_s",
    ):
        if type(result[name]) is not float or not math.isfinite(result[name]) or result[name] < 0.0:
            raise ValueError(f"Fresh B2 coverage {name} is invalid")
    if result["dilemma_zone_interval_s"] != [3.0, 5.0]:
        raise ValueError("Fresh B2 dilemma-zone interval drifted")
    if (
        result["source_class"] != "mapped_signal"
        or result["static_signal_chain_qualified"] is not True
        or result["runtime_same_tick_signal_required"] is not True
        or result["runtime_k8_support_required"] is not True
        or result["preopen_dp_forward_executed"] is not False
        or result["fresh_b2_opened"] is not False
        or result["outcome_fields_consumed"] != []
    ):
        raise ValueError("Fresh B2 coverage source/outcome contract drifted")
    return result


def _census(rows: Sequence[Mapping[str, Any]], plan: Mapping[str, Any]) -> dict[str, Any]:
    bool_counts = {
        name: Counter(str(row[name]).lower() for row in rows)
        for name in ("lead_stop", "occlusion", "dilemma_zone", "all_k_bad_eligibility")
    }
    phases = Counter(
        row["controlled_current_phase"]
        for row in rows
        if row["controlled_current_phase"] is not None
    )
    movements = Counter(row["movement"] for row in rows)
    family_tier = Counter((row["scenario_family"], row["risk_tier"]) for row in rows)
    required_cells = {
        (family, tier) for family in EVENT_FAMILIES for tier in RISK_TIERS
    }
    if (
        len(rows) != 100
        or plan["map_count"] != 25
        or plan["execution_unit_count"] != 500
        or plan["planned_arm_run_count"] != 1500
        or plan["ticks_per_arm_run"] * plan["planned_arm_run_count"] != 96_000
        or set(movements) != {"straight", "turn"}
        or set(phases) != {"green", "yellow", "red"}
        or any(bool_counts[name]["true"] < 1 for name in bool_counts)
        or any(family_tier[cell] < 1 for cell in required_cells)
    ):
        raise ValueError("Fresh B2 explicit coverage census is incomplete")
    return {
        "map_count": 25,
        "intersection_count": 100,
        "corridor_count": 100,
        "route_count": 100,
        "semantic_block_count": 100,
        "seed_count": 5,
        "paired_unit_count": 500,
        "arm_run_count": 1500,
        "tick_capacity": 96_000,
        "static_signal_chain_qualified_count": sum(
            row["static_signal_chain_qualified"] is True for row in rows
        ),
        "movement_counts": dict(sorted(movements.items())),
        "controlled_phase_fixture_counts": dict(sorted(phases.items())),
        "boolean_coverage_counts": {
            name: dict(sorted(counts.items())) for name, counts in sorted(bool_counts.items())
        },
        "family_tier_counts": {
            f"{family}/{tier}": family_tier[(family, tier)]
            for family, tier in sorted(required_cells)
        },
        "seeds_or_ticks_counted_as_independent": False,
    }


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    ).hexdigest()


def _require_sha(value: Any, name: str) -> None:
    if type(value) is not str or len(value) != 64 or set(value) - set("0123456789abcdef"):
        raise ValueError(f"{name} must be a lowercase SHA256")


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_strict_equal(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_strict_equal(a, b) for a, b in zip(left, right, strict=True))
    return bool(left == right)
