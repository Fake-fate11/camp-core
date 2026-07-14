from __future__ import annotations

import math
from typing import Any, Mapping

from camp_core.integrations.diffusion_planner_v21_native import (
    safety_cost_native_v1,
    summarize_safety_cost_native_v1,
)


SPEED_TOLERANCES_MPS = (0.0, 0.05, 0.1, 0.2)
OPERATIONAL_SPEED_TOLERANCE_MPS = 0.1
STRICT_SPEED_EPSILON_MPS = 1e-6
_ARM_STATUSES = frozenset({"ok", "source_invalid", "failed"})
_SPLITS = frozenset({"train", "calibration", "holdout", "diagnostic"})


def summarize_speed_protocol(
    records: Any,
    *,
    dt: float,
) -> dict[str, Any]:
    if not math.isfinite(dt) or not math.isclose(
        dt, 0.1, rel_tol=0.0, abs_tol=1e-12
    ):
        raise ValueError("native speed dt must equal 0.1 seconds")
    ticks = list(records)
    if not ticks:
        raise ValueError("speed protocol requires at least one tick")

    seen: set[int] = set()
    evaluated: list[tuple[int, float]] = []
    for record in ticks:
        index = record.get("tick_index")
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ValueError("tick_index must be a nonnegative integer")
        if index in seen:
            raise ValueError(f"duplicate tick_index: {index}")
        seen.add(index)
        coverage = record.get("five_point_drivable_coverage")
        if not isinstance(coverage, bool):
            raise ValueError("five_point_drivable_coverage must be bool")
        speed = float(record.get("speed_mps"))
        if not math.isfinite(speed) or speed < 0.0:
            raise ValueError("speed_mps must be finite and nonnegative")
        if not coverage:
            continue
        raw_limit = record.get("speed_limit_mps")
        if raw_limit is None:
            raise ValueError("on-road tick is missing speed_limit_mps")
        limit = float(raw_limit)
        if not math.isfinite(limit) or limit <= 0.0:
            raise ValueError("speed_limit_mps must be finite and positive")
        evaluated.append((index, max(speed - limit, 0.0)))

    if not evaluated:
        raise ValueError("speed_limit_ticks denominator is zero")
    denominator = len(evaluated)

    def event_summary(tolerance_mps: float) -> dict[str, Any]:
        event_ticks = [
            index
            for index, excess in evaluated
            if excess > float(tolerance_mps) + STRICT_SPEED_EPSILON_MPS
        ]
        return {
            "tolerance_mps": float(tolerance_mps),
            "event_count": len(event_ticks),
            "event_rate": len(event_ticks) / denominator,
            "event_ticks": event_ticks,
        }

    sensitivity = {
        _tolerance_key(tolerance): event_summary(tolerance)
        for tolerance in SPEED_TOLERANCES_MPS
    }
    excesses = [excess for _index, excess in evaluated]
    positive_ticks = [
        index for index, excess in evaluated if excess > 0.0
    ]
    strict = event_summary(0.0)
    strict["epsilon_mps"] = STRICT_SPEED_EPSILON_MPS
    return {
        "schema_version": "speed_protocol_v22",
        "dt_s": float(dt),
        "speed_limit_ticks": denominator,
        "strict": strict,
        "operational_tolerance_mps": OPERATIONAL_SPEED_TOLERANCE_MPS,
        "operational": sensitivity[
            _tolerance_key(OPERATIONAL_SPEED_TOLERANCE_MPS)
        ],
        "sensitivity": sensitivity,
        "continuous": {
            "maximum_excess_mps": max(excesses),
            "mean_excess_mps": sum(excesses) / denominator,
            "excess_duration_s": len(positive_ticks) * float(dt),
            "magnitude_duration_m": sum(excesses) * float(dt),
            "positive_excess_ticks": positive_ticks,
        },
    }


def summarize_safety_cost_native_v22(records: Any) -> dict[str, Any]:
    ticks = list(records)
    base = summarize_safety_cost_native_v1(ticks)
    speed = summarize_speed_protocol(ticks, dt=0.1)
    components = dict(base["components"])
    components["speed_limit_violation_rate"] = float(
        speed["operational"]["event_rate"]
    )
    raw_counts = dict(base["raw_counts"])
    raw_counts["strict_speed_limit_violation_ticks"] = raw_counts[
        "speed_limit_violation_ticks"
    ]
    raw_counts["speed_limit_violation_ticks"] = int(
        speed["operational"]["event_count"]
    )
    event_ticks = dict(base["event_ticks"])
    event_ticks["strict_speed_limit_violation"] = event_ticks[
        "speed_limit_violation"
    ]
    event_ticks["speed_limit_violation"] = list(
        speed["operational"]["event_ticks"]
    )
    return {
        **base,
        "schema_version": "safety_cost_native_v22",
        "safety_cost": safety_cost_native_v1(components),
        "components": components,
        "raw_counts": raw_counts,
        "maximum_speed_excess_mps": float(
            speed["continuous"]["maximum_excess_mps"]
        ),
        "event_ticks": event_ticks,
        "speed_protocol": speed,
    }


def retained_pair_row(
    *,
    pair_key: str,
    split: str,
    dp_arm: Mapping[str, Any],
    camp_arm: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(pair_key, str) or not pair_key:
        raise ValueError("pair_key must be nonempty")
    if split not in _SPLITS:
        raise ValueError("unknown split")
    dp_status = _arm_status(dp_arm, "dp")
    camp_status = _arm_status(camp_arm, "camp")
    hard_invalid = "source_invalid" in {dp_status, camp_status}
    execution_failure = "failed" in {dp_status, camp_status}
    failure_class = (
        "execution_failure"
        if execution_failure
        else "source_failure" if hard_invalid else None
    )
    return {
        "schema_version": "v22_retained_pair_row_v1",
        "pair_key": pair_key,
        "split": split,
        "included_in_denominator": True,
        "paired_complete": dp_status == camp_status == "ok",
        "failure_class": failure_class,
        "hard_invalid": hard_invalid,
        "execution_failure": execution_failure,
        "dp_status": dp_status,
        "camp_status": camp_status,
        "dp_failure_stage": dp_arm.get("failure_stage"),
        "camp_failure_stage": camp_arm.get("failure_stage"),
        "dp_failure_reason": dp_arm.get("reason"),
        "camp_failure_reason": camp_arm.get("reason"),
        "all_k_high_risk": bool(camp_arm.get("all_k_high_risk", False)),
    }


def _arm_status(arm: Mapping[str, Any], name: str) -> str:
    status = arm.get("status")
    if status not in _ARM_STATUSES:
        raise ValueError(f"{name} arm has unknown status")
    return str(status)


def _tolerance_key(value: float) -> str:
    return "0.0" if value == 0.0 else str(value)
