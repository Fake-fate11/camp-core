from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_signal_safety import (
    summarize_certified_signal_safety,
)


def _mapped_tick(
    tick_index: int,
    phase: str,
    *,
    previous_x: float,
    current_x: float,
    pre_speed: float,
    post_speed: float,
    minimum_clearance: float = 4.0,
) -> dict:
    return {
        "tick_index": tick_index,
        "signal_phase_at_interval_start": phase,
        "certified_signal_stop_lines": [[[10.0, -2.0], [10.0, 2.0]]],
        "front_center_prev_xy": [previous_x, 0.0],
        "front_center_xy": [current_x, 0.0],
        "route_heading_rad": 0.0,
        "pre_decision_speed_mps": pre_speed,
        "speed_mps": post_speed,
        "min_obb_clearance_m": minimum_clearance,
    }


def test_certified_signal_metrics_use_same_tick_phase_and_exact_stop_line() -> None:
    records = [
        _mapped_tick(
            0,
            "red",
            previous_x=9.0,
            current_x=11.0,
            pre_speed=2.0,
            post_speed=2.0,
        ),
        _mapped_tick(
            1,
            "red",
            previous_x=8.0,
            current_x=8.5,
            pre_speed=0.4,
            post_speed=0.4,
        ),
        _mapped_tick(
            2,
            "green",
            previous_x=9.0,
            current_x=9.0,
            pre_speed=0.3,
            post_speed=0.3,
        ),
        _mapped_tick(
            3,
            "green",
            previous_x=9.0,
            current_x=11.0,
            pre_speed=2.0,
            post_speed=2.0,
        ),
        _mapped_tick(
            4,
            "yellow",
            previous_x=7.0,
            current_x=8.0,
            pre_speed=1.0,
            post_speed=1.0,
        ),
    ]

    summary = summarize_certified_signal_safety(records)

    assert summary["source_class"] == "mapped_signal"
    assert summary["metrics"] == {
        "red_light_violation_rate": 0.5,
        "stop_line_crossing_rate": 0.5,
        "stop_line_margin_m": -1.0,
        "crossing_speed_mps": 2.0,
        "false_stop_on_green_rate": 0.5,
    }
    assert summary["counts"] == {
        "red_crossing_intervals": 1,
        "red_violation_intervals": 1,
        "green_false_stop_intervals": 1,
    }
    assert summary["denominators"] == {
        "red_phase_intervals": 2,
        "green_phase_intervals": 2,
        "green_unblocked_approach_intervals": 2,
        "yellow_phase_intervals": 1,
    }
    assert summary["certified_stop_line_used"] is True
    assert summary["legacy_proximity_heuristic_used"] is False
    assert summary["future_phase_schedule_consumed"] is False
    assert summary["phase_remaining_consumed"] is False


def test_no_signal_metrics_are_exact_zero() -> None:
    summary = summarize_certified_signal_safety(
        [
            {
                "tick_index": 0,
                "signal_phase_at_interval_start": "none",
                "certified_signal_stop_lines": [],
            }
        ]
    )

    assert summary["source_class"] == "no_signal"
    assert set(summary["metrics"].values()) == {0.0}
    assert set(summary["counts"].values()) == {0}
    assert set(summary["denominators"].values()) == {0}
    assert summary["certified_stop_line_used"] is False


def test_green_stop_behind_observable_obstacle_is_not_labeled_false() -> None:
    summary = summarize_certified_signal_safety(
        [
            _mapped_tick(
                0,
                "green",
                previous_x=9.0,
                current_x=9.0,
                pre_speed=0.2,
                post_speed=0.2,
                minimum_clearance=1.0,
            )
        ]
    )
    assert summary["counts"]["green_false_stop_intervals"] == 0
    assert summary["denominators"]["green_unblocked_approach_intervals"] == 0
    assert summary["metrics"]["false_stop_on_green_rate"] == 0.0


@pytest.mark.parametrize(
    ("mutation", "match"),
    (
        (lambda row: row.update(certified_signal_stop_lines=[]), "exactly one"),
        (
            lambda row: row.update(certified_signal_stop_lines=[[[10.0, -2.0], [10.0, -2.0]]]),
            "degenerate",
        ),
        (lambda row: row.update(pre_decision_speed_mps="0.2"), "native number"),
        (lambda row: row.update(signal_phase_at_interval_start="future_red"), "signal phase"),
    ),
)
def test_certified_signal_evidence_mutations_fail_closed(mutation, match: str) -> None:
    row = _mapped_tick(
        0,
        "red",
        previous_x=9.0,
        current_x=11.0,
        pre_speed=2.0,
        post_speed=2.0,
    )
    mutation(row)
    with pytest.raises(ValueError, match=match):
        summarize_certified_signal_safety([row])


def test_signal_source_class_cannot_change_inside_run() -> None:
    mapped = _mapped_tick(
        0,
        "green",
        previous_x=9.0,
        current_x=9.0,
        pre_speed=0.2,
        post_speed=0.2,
    )
    no_signal = copy.deepcopy(mapped)
    no_signal.update(
        tick_index=1,
        signal_phase_at_interval_start="none",
        certified_signal_stop_lines=[],
    )
    with pytest.raises(ValueError, match="source class changed"):
        summarize_certified_signal_safety([mapped, no_signal])
