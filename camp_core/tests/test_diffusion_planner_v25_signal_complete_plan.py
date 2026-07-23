from __future__ import annotations

import copy
from collections import Counter

import pytest

from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    ARMS,
    EVENT_FAMILIES,
    RISK_TIERS,
    build_signal_complete_execution_plan,
    validate_calibration_fresh_zero_overlap,
    validate_signal_complete_execution_plan,
)


def test_calibration_plan_has_fifty_corridor_clusters_and_two_repeats() -> None:
    plan = build_signal_complete_execution_plan("calibration")
    counts = Counter(
        identity["corridor_sha256"]
        for unit in plan["execution_units"]
        for identity in plan["identities"]
        if identity["scenario_identity_sha256"] == unit["scenario_identity_sha256"]
    )
    assert plan["map_count"] == 5
    assert plan["corridor_count"] == 50
    assert plan["route_count"] == 50
    assert plan["execution_unit_count"] == 100
    assert plan["planned_arm_run_count"] == 100
    assert set(counts.values()) == {2}
    assert all(unit["ordered_arms"] == [ARMS[0]] for unit in plan["execution_units"])


def test_fresh_plan_has_five_repeats_and_balanced_three_arm_order() -> None:
    plan = build_signal_complete_execution_plan("fresh_b2")
    positions = {arm: Counter() for arm in ARMS}
    for unit in plan["execution_units"]:
        assert set(unit["ordered_arms"]) == set(ARMS)
        for index, arm in enumerate(unit["ordered_arms"]):
            positions[arm][index] += 1
    assert plan["map_count"] == 25
    assert plan["route_count"] == 100
    assert plan["execution_unit_count"] == 500
    assert plan["planned_arm_run_count"] == 1500
    assert plan["benchmark_stratum_counts"] == {
        "naturalistic": 25,
        "controlled_stress": 75,
    }
    for counts in positions.values():
        assert max(counts.values()) - min(counts.values()) <= 1


@pytest.mark.parametrize(
    "split", ("calibration", "fresh_b2", "fresh_b3", "fresh_b4")
)
def test_all_family_tier_cells_and_same_tick_signal_modes_are_frozen(split: str) -> None:
    plan = build_signal_complete_execution_plan(split)
    assert set(plan["family_tier_counts"]) == {
        f"{family}/{tier}" for family in EVENT_FAMILIES for tier in RISK_TIERS
    }
    assert min(plan["family_tier_counts"].values()) >= 1
    for row in plan["identities"]:
        assert row["route_spec"]["lanelet_ids"] == row["source_chain"][
            "route_lanelet_ids"
        ]
        assert row["route_spec"]["start_pose"] == row["initial_pose"]
        assert row["route_spec"]["goal_pose"] == row["goal_pose"]
        assert row["signal_source_class"] == "mapped_signal"
        assert row["same_tick_current_phase_required"] is True
        assert row["phase_remaining_available"] is False
        assert row["future_phase_program_present"] is False
        if row["scenario_family"] == "red_light_phase_timing":
            assert row["phase_authority_mode"] == "controlled_same_tick_override"
            assert row["controlled_current_phase"] == {
                "easy": "green",
                "borderline": "yellow",
                "high_risk": "red",
            }[row["risk_tier"]]
        else:
            assert row["phase_authority_mode"] == "observe_same_tick_request"
            assert row["controlled_current_phase"] is None


def test_calibration_and_fresh_are_zero_overlap_at_every_independent_layer() -> None:
    calibration = build_signal_complete_execution_plan("calibration")
    fresh = build_signal_complete_execution_plan("fresh_b2")
    receipt = validate_calibration_fresh_zero_overlap(calibration, fresh)
    assert receipt["status"] == "passed_signal_complete_zero_overlap"
    assert all(receipt["checks"].values())
    assert receipt["checks"]["semantic_parameter_block_sha256"] is True
    assert receipt["fresh_b2_opened"] is False


def test_fresh_b3_is_zero_overlap_from_calibration_and_consumed_b2() -> None:
    calibration = build_signal_complete_execution_plan("calibration")
    fresh_b2 = build_signal_complete_execution_plan("fresh_b2")
    fresh_b3 = build_signal_complete_execution_plan("fresh_b3")
    independent_fields = (
        "map_sha256",
        "map_geometry_sha256",
        "corridor_sha256",
        "intersection_sha256",
        "route_identity_sha256",
        "route_family_sha256",
        "source_independent_geometry_sha256",
        "scenario_identity_sha256",
        "semantic_parameter_block_sha256",
    )
    for prior in (calibration, fresh_b2):
        assert prior["source_family"] != fresh_b3["source_family"]
        for field in independent_fields:
            assert {
                row[field] for row in prior["identities"]
            }.isdisjoint({row[field] for row in fresh_b3["identities"]})
        assert set(prior["seeds"]).isdisjoint(fresh_b3["seeds"])
    assert fresh_b3["execution_unit_count"] == 500
    assert fresh_b3["planned_arm_run_count"] == 1500


def test_fresh_b4_is_clone_aware_zero_overlap_from_all_prior_holdouts() -> None:
    fresh_b4 = build_signal_complete_execution_plan("fresh_b4")
    independent_fields = (
        "map_sha256",
        "map_geometry_sha256",
        "corridor_sha256",
        "intersection_sha256",
        "route_identity_sha256",
        "route_family_sha256",
        "source_independent_geometry_sha256",
        "scenario_identity_sha256",
        "semantic_parameter_block_sha256",
    )
    for split in ("calibration", "fresh_b2", "fresh_b3"):
        prior = build_signal_complete_execution_plan(split)
        for field in independent_fields:
            assert {
                row[field] for row in prior["identities"]
            }.isdisjoint({row[field] for row in fresh_b4["identities"]})
        assert set(prior["seeds"]).isdisjoint(fresh_b4["seeds"])
    assert fresh_b4["execution_unit_count"] == 500
    assert fresh_b4["planned_arm_run_count"] == 1500


def test_plan_is_deterministic_and_reconstructable() -> None:
    first = build_signal_complete_execution_plan("calibration")
    second = build_signal_complete_execution_plan("calibration")
    assert first == second
    assert validate_signal_complete_execution_plan(first) == first


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("fresh_b2_opened", True),
        ("phase_remaining_available", True),
        ("candidate_count", 7),
        ("fixed_dp_modified", True),
    ),
)
def test_plan_mutations_fail_closed(field: str, value: object) -> None:
    plan = build_signal_complete_execution_plan("calibration")
    mutated = copy.deepcopy(plan)
    mutated[field] = value
    with pytest.raises(ValueError, match="differs"):
        validate_signal_complete_execution_plan(mutated)


def test_unknown_split_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown"):
        build_signal_complete_execution_plan("train")
