from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner_v21_native import segments_intersect_2d


SIGNAL_SAFETY_SCHEMA_VERSION = "camp_dp_v25_certified_signal_safety_v1"
SIGNAL_PHASES = frozenset({"none", "green", "yellow", "red"})
RED_CROSSING_MINIMUM_SPEED_MPS = 0.5
FALSE_STOP_GREEN_MAXIMUM_SPEED_MPS = 0.5
FALSE_STOP_GREEN_APPROACH_DISTANCE_M = 5.0
FALSE_STOP_GREEN_MINIMUM_OBB_CLEARANCE_M = 3.0


def summarize_certified_signal_safety(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Summarize exact same-tick signal outcomes from certified stop lines.

    The stop line is supplied by the frozen route-level regulatory chain.  No
    map proximity search, future phase schedule, or phase-remaining value is
    consumed here.
    """

    ticks = list(records)
    if not ticks:
        raise ValueError("certified signal safety requires at least one tick")

    mapped: bool | None = None
    seen: set[int] = set()
    red_exposure = 0
    red_crossings = 0
    red_violations = 0
    red_margins: list[float] = []
    red_crossing_speeds: list[float] = []
    green_exposure = 0
    green_unblocked_approach_exposure = 0
    green_false_stops = 0
    yellow_exposure = 0

    for record in ticks:
        index = _native_int(record.get("tick_index"), "tick_index")
        if index in seen:
            raise ValueError(f"duplicate certified signal tick_index: {index}")
        seen.add(index)
        phase = record.get("signal_phase_at_interval_start")
        if type(phase) is not str or phase not in SIGNAL_PHASES:
            raise ValueError("signal phase must be none/green/yellow/red")
        tick_mapped = phase != "none"
        if mapped is None:
            mapped = tick_mapped
        elif mapped != tick_mapped:
            raise ValueError("signal source class changed inside one run")

        raw_lines = record.get("certified_signal_stop_lines")
        if type(raw_lines) is not list:
            raise ValueError("certified signal stop lines must be a native list")
        lines = _finite_array(raw_lines, "certified signal stop lines")
        if tick_mapped:
            if lines.shape != (1, 2, 2):
                raise ValueError("mapped signal tick requires exactly one certified [2,2] stop line")
        elif lines.shape != (0,):
            raise ValueError("no-signal tick must have an empty certified stop-line list")
        if not tick_mapped:
            continue

        previous_front = _finite_xy(record.get("front_center_prev_xy"), "front_center_prev_xy")
        current_front = _finite_xy(record.get("front_center_xy"), "front_center_xy")
        route_heading = _finite_number(record.get("route_heading_rad"), "route_heading_rad")
        pre_speed = _finite_nonnegative(
            record.get("pre_decision_speed_mps"), "pre_decision_speed_mps"
        )
        post_speed = _finite_nonnegative(record.get("speed_mps"), "speed_mps")
        minimum_clearance = _finite_nonnegative(
            record.get("min_obb_clearance_m"), "min_obb_clearance_m"
        )
        line = lines[0]
        signed_previous = _signed_stop_line_margin(
            previous_front, line, route_heading
        )
        signed_current = _signed_stop_line_margin(current_front, line, route_heading)
        crossing = segments_intersect_2d(
            previous_front, current_front, line[0], line[1]
        )

        if phase == "red":
            red_exposure += 1
            red_margins.append(signed_current)
            if crossing:
                red_crossings += 1
                red_crossing_speeds.append(post_speed)
                if post_speed > RED_CROSSING_MINIMUM_SPEED_MPS:
                    red_violations += 1
        elif phase == "green":
            green_exposure += 1
            if (
                0.0 <= signed_previous <= FALSE_STOP_GREEN_APPROACH_DISTANCE_M
                and minimum_clearance > FALSE_STOP_GREEN_MINIMUM_OBB_CLEARANCE_M
            ):
                green_unblocked_approach_exposure += 1
                if pre_speed <= FALSE_STOP_GREEN_MAXIMUM_SPEED_MPS:
                    green_false_stops += 1
        elif phase == "yellow":
            yellow_exposure += 1

    is_mapped = bool(mapped)
    if not is_mapped:
        return {
            "schema_version": SIGNAL_SAFETY_SCHEMA_VERSION,
            "source_class": "no_signal",
            "metrics": _zero_metrics(),
            "counts": _zero_counts(),
            "denominators": _zero_denominators(),
            "thresholds": _thresholds(),
            "certified_stop_line_used": False,
            "legacy_proximity_heuristic_used": False,
            "future_phase_schedule_consumed": False,
            "phase_remaining_consumed": False,
        }

    return {
        "schema_version": SIGNAL_SAFETY_SCHEMA_VERSION,
        "source_class": "mapped_signal",
        "metrics": {
            "red_light_violation_rate": red_violations / max(red_exposure, 1),
            "stop_line_crossing_rate": red_crossings / max(red_exposure, 1),
            "stop_line_margin_m": min(red_margins) if red_margins else 0.0,
            "crossing_speed_mps": (
                sum(red_crossing_speeds) / len(red_crossing_speeds)
                if red_crossing_speeds
                else 0.0
            ),
            "false_stop_on_green_rate": (
                green_false_stops / max(green_unblocked_approach_exposure, 1)
            ),
        },
        "counts": {
            "red_crossing_intervals": red_crossings,
            "red_violation_intervals": red_violations,
            "green_false_stop_intervals": green_false_stops,
        },
        "denominators": {
            "red_phase_intervals": red_exposure,
            "green_phase_intervals": green_exposure,
            "green_unblocked_approach_intervals": (
                green_unblocked_approach_exposure
            ),
            "yellow_phase_intervals": yellow_exposure,
        },
        "thresholds": _thresholds(),
        "certified_stop_line_used": True,
        "legacy_proximity_heuristic_used": False,
        "future_phase_schedule_consumed": False,
        "phase_remaining_consumed": False,
    }


def _signed_stop_line_margin(
    point_xy: np.ndarray, stop_line: np.ndarray, route_heading_rad: float
) -> float:
    tangent = np.asarray(stop_line[1] - stop_line[0], dtype=np.float64)
    length = float(np.linalg.norm(tangent))
    if not math.isfinite(length) or length <= 1e-9:
        raise ValueError("certified stop line is degenerate")
    tangent /= length
    normal = np.asarray([-tangent[1], tangent[0]], dtype=np.float64)
    route_direction = np.asarray(
        [math.cos(route_heading_rad), math.sin(route_heading_rad)], dtype=np.float64
    )
    alignment = float(normal @ route_direction)
    if abs(alignment) <= 1e-6:
        raise ValueError("certified stop line is parallel to the route direction")
    if alignment < 0.0:
        normal = -normal
    midpoint = np.asarray(stop_line, dtype=np.float64).mean(axis=0)
    return float((midpoint - point_xy) @ normal)


def _finite_array(value: Any, label: str) -> np.ndarray:
    def validate(item: Any) -> None:
        if type(item) is list:
            for child in item:
                validate(child)
            return
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"{label} must contain native numeric values")
        if not math.isfinite(float(item)):
            raise ValueError(f"{label} must be finite")

    validate(value)
    return np.asarray(value, dtype=np.float64)


def _finite_xy(value: Any, label: str) -> np.ndarray:
    if type(value) is not list or len(value) != 2:
        raise ValueError(f"{label} must be a native [2] list")
    result = _finite_array(value, label)
    if result.shape != (2,):
        raise ValueError(f"{label} must have shape [2]")
    return result


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a native number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _finite_nonnegative(value: Any, label: str) -> float:
    result = _finite_number(value, label)
    if result < 0.0:
        raise ValueError(f"{label} must be nonnegative")
    return result


def _native_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative native int")
    return value


def _thresholds() -> dict[str, float]:
    return {
        "red_crossing_minimum_speed_mps": RED_CROSSING_MINIMUM_SPEED_MPS,
        "false_stop_green_maximum_speed_mps": FALSE_STOP_GREEN_MAXIMUM_SPEED_MPS,
        "false_stop_green_approach_distance_m": FALSE_STOP_GREEN_APPROACH_DISTANCE_M,
        "false_stop_green_minimum_obb_clearance_m": (
            FALSE_STOP_GREEN_MINIMUM_OBB_CLEARANCE_M
        ),
    }


def _zero_metrics() -> dict[str, float]:
    return {
        "red_light_violation_rate": 0.0,
        "stop_line_crossing_rate": 0.0,
        "stop_line_margin_m": 0.0,
        "crossing_speed_mps": 0.0,
        "false_stop_on_green_rate": 0.0,
    }


def _zero_counts() -> dict[str, int]:
    return {
        "red_crossing_intervals": 0,
        "red_violation_intervals": 0,
        "green_false_stop_intervals": 0,
    }


def _zero_denominators() -> dict[str, int]:
    return {
        "red_phase_intervals": 0,
        "green_phase_intervals": 0,
        "green_unblocked_approach_intervals": 0,
        "yellow_phase_intervals": 0,
    }
