from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v21_native import safety_cost_native_v1
from camp_core.integrations.diffusion_planner_v25_power_pilot import (
    build_power_pilot_variance_receipt,
    project_candidate0_power_pilot_rows,
    validate_power_pilot_variance_receipt,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def _results() -> tuple[dict, list[dict]]:
    plan = build_signal_complete_execution_plan("calibration")
    identities = {
        row["scenario_identity_sha256"]: row for row in plan["identities"]
    }
    results = []
    red_cluster_values: dict[str, float] = {}
    for unit in plan["execution_units"]:
        identity = identities[unit["scenario_identity_sha256"]]
        ordinal = unit["unit_ordinal"]
        is_red = identity["scenario_family"] == "red_light_phase_timing"
        red = 0.0
        if is_red:
            corridor = identity["corridor_sha256"]
            if corridor not in red_cluster_values:
                red_cluster_values[corridor] = float(len(red_cluster_values) % 2)
            red = red_cluster_values[corridor]
        components = {
            "collision_any": 0.0,
            "near_miss_noncollision_rate": (ordinal % 5) / 100.0,
            "offroad_rate": 0.0,
            "wrong_way_rate": 0.0,
            "red_light_violation_any": red,
            "speed_limit_violation_rate": (ordinal % 3) / 100.0,
        }
        results.append(
            {
                "unit_ordinal": ordinal,
                "unit_sha256": unit["unit_sha256"],
                "scenario_identity_sha256": unit["scenario_identity_sha256"],
                "route_identity_sha256": identity["route_identity_sha256"],
                "seed": unit["seed"],
                "status": "complete",
                "native_receipt": {
                    "schema_version": "v21_native_arm_receipt_v1",
                    "status": "ok",
                    "arm": "dp",
                    "fixed_dp_head": FIXED_DP_HEAD,
                    "scenario_seed": unit["seed"],
                    "claim_authorized": False,
                    "safety": {
                        "schema_version": "safety_cost_native_v22",
                        "safety_cost": safety_cost_native_v1(components),
                        "components": components,
                    },
                },
                "failure_receipt": None,
                "fresh_b2_opened": False,
                "fresh_outcome_fields_consumed": [],
            }
        )
    return plan, results


def test_power_pilot_is_derived_from_candidate0_cluster_means() -> None:
    plan, results = _results()
    rows = project_candidate0_power_pilot_rows(plan, results)
    receipt = build_power_pilot_variance_receipt(
        rows,
        source_artifact_root_sha256="a" * 64,
    )
    assert len(rows) == 100
    assert receipt["calibration_arm"] == "candidate0_operational_default"
    assert receipt["total_independent_cluster_count"] >= 2
    assert receipt["red_independent_cluster_count"] >= 2
    assert receipt["safety_cost_cluster_standard_deviation"] > 0.0
    assert receipt["red_component_cluster_standard_deviation"] > 0.0
    assert (
        validate_power_pilot_variance_receipt(
            receipt, expected_root_sha256="a" * 64
        )
        == receipt
    )


def test_power_pilot_rejects_safety_and_root_mutations() -> None:
    plan, results = _results()
    results[0]["native_receipt"]["safety"]["safety_cost"] += 1.0
    with pytest.raises(ValueError, match="differs from components"):
        project_candidate0_power_pilot_rows(plan, results)

    plan, results = _results()
    receipt = build_power_pilot_variance_receipt(
        project_candidate0_power_pilot_rows(plan, results),
        source_artifact_root_sha256="a" * 64,
    )
    mutated = copy.deepcopy(receipt)
    mutated["source_artifact_root_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="exact value drifted"):
        validate_power_pilot_variance_receipt(
            mutated, expected_root_sha256="a" * 64
        )
