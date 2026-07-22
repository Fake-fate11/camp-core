from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_calibration_analysis import (
    analyze_paired_calibration_outcomes,
)
from camp_core.integrations.diffusion_planner_v25_calibration import (
    SAFETY_COMPONENT_NATIVE_FIELDS,
)


ARMS = (
    "candidate0_operational_default",
    "camp_static14d",
    "camp_scene14d_no_v2i",
)


def _corpus() -> dict:
    rows = []
    for unit in range(100):
        for arm_index, arm in enumerate(ARMS):
            improvement = 0.0 if arm_index == 0 else -0.05 * arm_index
            components = {
                native_name: max(0.0, 0.2 + improvement)
                for native_name in SAFETY_COMPONENT_NATIVE_FIELDS.values()
            }
            ticks = [
                {
                    "pre_decision_speed_mps": 8.0,
                    "safety": {"speed_mps": 7.99},
                    "selected_index": arm_index,
                    "all_k_high_risk": False,
                    "physical_feasible_mask": [True] * 8,
                    "source_valid_mask": [True] * 8,
                    "latency_ms": {
                        "default_inference": 1.0,
                        "candidate_inference": float(arm_index),
                        "selector": 0.01 * arm_index,
                        "tracker": 0.5,
                        "total_planning": 2.0 + arm_index,
                    },
                }
                for _ in range(64)
            ]
            rows.append(
                {
                    "unit_ordinal": unit,
                    "plan_arm": arm,
                    "status": "complete",
                    "map_sha256": f"map-{unit % 5}",
                    "intersection_sha256": f"intersection-{unit % 5}",
                    "corridor_sha256": f"corridor-{unit % 5}",
                    "route_identity_sha256": f"route-{unit // 2}",
                    "route_family_sha256": f"route-family-{unit % 10}",
                    "semantic_parameter_block_sha256": f"block-{unit}",
                    "scenario_family": (
                        "red_light_phase_timing" if unit % 7 == 0 else "cut_in_merge"
                    ),
                    "risk_tier": "borderline",
                    "benchmark_stratum": "controlled_stress",
                    "signal_source_class": "mapped_signal",
                    "phase_authority_mode": "observe_same_tick_request",
                    "seed": 25301 + unit % 2,
                    "native_receipt": {
                        "safety": {
                            "safety_cost": 10.0 + improvement,
                            "components": components,
                        },
                        "secondary": {
                            "route_progress_m": 40.0 - 0.1 * arm_index,
                            "route_completion_rate": 0.9,
                            "mean_abs_jerk_mps3": 0.5 + 0.01 * arm_index,
                            "max_jerk_mps3": 1.5 + 0.01 * arm_index,
                            "mean_abs_lateral_acceleration_mps2": 0.2,
                            "max_abs_lateral_acceleration_mps2": 0.8,
                        },
                        "ticks": ticks,
                        "signal_safety": {
                            "schema_version": "camp_dp_v25_certified_signal_safety_v1",
                            "source_class": "mapped_signal",
                            "metrics": {
                                "red_light_violation_rate": 0.0,
                                "stop_line_crossing_rate": 0.0,
                                "stop_line_margin_m": 1.0,
                                "crossing_speed_mps": 0.0,
                                "false_stop_on_green_rate": 0.0,
                            },
                            "counts": {
                                "red_crossing_intervals": 0,
                                "red_violation_intervals": 0,
                                "green_false_stop_intervals": 0,
                            },
                            "denominators": {
                                "red_phase_intervals": 1,
                                "green_phase_intervals": 1,
                                "green_unblocked_approach_intervals": 1,
                                "yellow_phase_intervals": 0,
                            },
                            "thresholds": {
                                "red_crossing_minimum_speed_mps": 0.5,
                                "false_stop_green_maximum_speed_mps": 0.5,
                                "false_stop_green_approach_distance_m": 5.0,
                                "false_stop_green_minimum_obb_clearance_m": 3.0,
                            },
                            "certified_stop_line_used": True,
                            "legacy_proximity_heuristic_used": False,
                            "future_phase_schedule_consumed": False,
                            "phase_remaining_consumed": False,
                        },
                    },
                }
            )
    return {
        "paired_eligible_pair_count": 100,
        "paired_eligible_rate": 1.0,
        "pair_count": 100,
        "planned_arm_run_count": 300,
        "terminal_arm_run_count": 300,
        "complete_arm_run_count": 300,
        "retained_fixed_dp_capability_failure_count": 0,
        "complete_count_by_arm": {arm: 100 for arm in ARMS},
        "failure_count_by_arm": {},
        "family_paired_eligible_rates": {
            "cut_in_merge": 1.0,
            "red_light_phase_timing": 1.0,
        },
        "source_paired_eligible_rates": {"mapped_signal": 1.0},
        "family_tier_paired_eligible_rates": {
            "cut_in_merge/borderline": 1.0,
            "red_light_phase_timing/borderline": 1.0,
        },
        "coverage_gate_passed": True,
        "arm_results": rows,
    }


def test_paired_calibration_analysis_reports_primary_ni_latency_and_power() -> None:
    report = analyze_paired_calibration_outcomes(_corpus())
    assert report["paired_eligible_pair_count"] == 100
    assert report["independent_unit_counts"]["corridors"] == 5
    assert report["seeds_or_ticks_counted_as_independent"] is False
    for name in (
        "camp_static14d_minus_candidate0",
        "camp_scene14d_no_v2i_minus_candidate0",
    ):
        comparison = report["paired_comparisons"][name]
        assert comparison["safety_cost"]["mean_delta"] < 0.0
        assert comparison["all_noninferiority_passed"] is True
        assert set(comparison["component_guardrails"]) == {
            "collision",
            "near_miss",
            "offroad",
            "red_light",
            "speed",
            "wrong_way",
        }
    assert report["latency"]["camp_static14d"]["selector"]["count"] == 6400
    assert report["latency"]["candidate0_operational_default"]["selector"][
        "available"
    ] is True
    assert report["main_table"]["camp_static14d"]["certified_signal_safety"][
        "legacy_proximity_heuristic_used"
    ] is False
    assert report["fresh_b2_opened"] is False
    assert report["claim_authorized"] is False


def test_paired_calibration_analysis_rejects_terminal_denominator_drift() -> None:
    corpus = copy.deepcopy(_corpus())
    corpus["arm_results"].pop()
    with pytest.raises(ValueError, match="300 terminal rows"):
        analyze_paired_calibration_outcomes(corpus)
