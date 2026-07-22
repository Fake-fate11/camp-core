from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_paired_calibration import (
    ARM_RUN_COUNT,
    PAIR_COUNT,
    TOTAL_TICK_CAPACITY,
    build_paired_calibration_execution_plan,
    validate_paired_calibration_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    ARMS,
    build_signal_complete_execution_plan,
)


def test_paired_calibration_plan_lifts_same_calibration_denominator() -> None:
    base = build_signal_complete_execution_plan("calibration")
    plan = build_paired_calibration_execution_plan(base)

    assert validate_paired_calibration_execution_plan(
        plan, calibration_plan=base
    ) == plan
    assert plan["pair_count"] == PAIR_COUNT == 100
    assert plan["arm_run_count"] == ARM_RUN_COUNT == 300
    assert plan["total_tick_capacity"] == TOTAL_TICK_CAPACITY == 19_200
    assert plan["map_count"] == 5
    assert plan["corridor_count"] == 5
    assert plan["route_count"] == 50
    assert plan["seeds"] == [25301, 25302]
    assert plan["paired_arms"] == list(ARMS)
    assert plan["fresh_b2_opened"] is False
    assert plan["fresh_outcome_fields_consumed"] == []
    assert [row["scenario_identity_sha256"] for row in plan["identities"]] == [
        row["scenario_identity_sha256"] for row in base["identities"]
    ]
    assert plan["execution_units"][0]["ordered_arms"] == list(ARMS)
    assert plan["execution_units"][1]["ordered_arms"] == [
        ARMS[1],
        ARMS[2],
        ARMS[0],
    ]
    assert plan["execution_units"][2]["ordered_arms"] == [
        ARMS[2],
        ARMS[0],
        ARMS[1],
    ]


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("arm_run_count",), 299),
        (("execution_units", 0, "ordered_arms"), list(reversed(ARMS))),
        (("execution_units", 0, "seed"), 25401),
        (("fresh_b2_opened",), True),
        (("candidate_tensor_modified",), True),
    ],
)
def test_paired_calibration_plan_mutations_fail_closed(
    path: tuple[object, ...], value: object
) -> None:
    base = build_signal_complete_execution_plan("calibration")
    mutated = copy.deepcopy(build_paired_calibration_execution_plan(base))
    target: object = mutated
    for part in path[:-1]:
        target = target[part]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    with pytest.raises(ValueError, match="differs from reconstruction"):
        validate_paired_calibration_execution_plan(
            mutated, calibration_plan=base
        )
