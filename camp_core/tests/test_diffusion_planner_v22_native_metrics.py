import numpy as np
import pytest


def _metrics():
    from camp_core.integrations import diffusion_planner_v22_native

    return diffusion_planner_v22_native


def _tick(index: int, *, excess_mps: float = 0.0, **updates):
    speed_limit = 10.0
    record = {
        "tick_index": index,
        "min_obb_clearance_m": 3.0,
        "five_point_drivable_coverage": True,
        "speed_mps": speed_limit + excess_mps,
        "ego_heading_rad": 0.0,
        "route_heading_rad": 0.0,
        "front_center_prev_xy": [float(index), -1.0],
        "front_center_xy": [float(index), 0.0],
        "red_light_at_interval_start": False,
        "red_stop_lines": np.empty((0, 2, 2), dtype=np.float64),
        "speed_limit_mps": speed_limit,
        "position_xy": [float(index), 0.0],
    }
    record.update(updates)
    return record


def test_speed_protocol_reports_strict_tolerance_sensitivity_and_severity() -> None:
    module = _metrics()
    records = [
        _tick(0, excess_mps=0.0),
        _tick(1, excess_mps=0.04),
        _tick(2, excess_mps=0.0927605),
        _tick(3, excess_mps=0.21),
    ]

    summary = module.summarize_speed_protocol(records, dt=0.1)

    assert summary["strict"]["event_count"] == 3
    assert summary["sensitivity"]["0.0"]["event_count"] == 3
    assert summary["sensitivity"]["0.05"]["event_count"] == 2
    assert summary["sensitivity"]["0.1"]["event_count"] == 1
    assert summary["sensitivity"]["0.2"]["event_count"] == 1
    assert summary["operational_tolerance_mps"] == 0.1
    assert summary["operational"]["event_count"] == 1
    assert summary["continuous"]["maximum_excess_mps"] == pytest.approx(0.21)
    assert summary["continuous"]["excess_duration_s"] == pytest.approx(0.3)
    assert summary["continuous"]["magnitude_duration_m"] == pytest.approx(
        0.1 * (0.04 + 0.0927605 + 0.21)
    )


def test_safety_cost_v22_uses_point_one_operational_speed_event() -> None:
    module = _metrics()
    records = [_tick(0), _tick(1, excess_mps=0.0927605)]

    summary = module.summarize_safety_cost_native_v22(records)

    assert summary["schema_version"] == "safety_cost_native_v22"
    assert summary["components"]["speed_limit_violation_rate"] == 0.0
    assert summary["speed_protocol"]["strict"]["event_count"] == 1
    assert summary["speed_protocol"]["operational"]["event_count"] == 0
    assert summary["safety_cost"] == 0.0


def test_existing_native_runner_dispatches_v22_safety_schema() -> None:
    from scripts.integrations import run_diffusion_planner_dp_camp_v21_native

    records = [_tick(0), _tick(1, excess_mps=0.0927605)]
    summary = run_diffusion_planner_dp_camp_v21_native._summarize_safety_records(
        records, "safety_cost_native_v22"
    )

    assert summary["schema_version"] == "safety_cost_native_v22"
    assert summary["speed_protocol"]["strict"]["event_count"] == 1
    assert summary["speed_protocol"]["operational"]["event_count"] == 0


def test_speed_protocol_missing_onroad_source_and_zero_denominator_fail() -> None:
    module = _metrics()
    with pytest.raises(ValueError, match="speed_limit_mps"):
        module.summarize_speed_protocol(
            [_tick(0, speed_limit_mps=None)], dt=0.1
        )
    with pytest.raises(ValueError, match="denominator"):
        module.summarize_speed_protocol(
            [_tick(0, five_point_drivable_coverage=False, speed_limit_mps=None)],
            dt=0.1,
        )


def test_retained_pair_row_keeps_source_and_execution_failures() -> None:
    module = _metrics()
    execution = module.retained_pair_row(
        pair_key="group-a/route-a/seed-21",
        split="holdout",
        dp_arm={"status": "ok"},
        camp_arm={
            "status": "failed",
            "failure_stage": "tracker",
            "reason": "tracker rejected reference",
        },
    )
    source = module.retained_pair_row(
        pair_key="group-b/route-b/seed-22",
        split="holdout",
        dp_arm={"status": "source_invalid", "reason": "candidate hash missing"},
        camp_arm={"status": "ok"},
    )

    assert execution["included_in_denominator"] is True
    assert execution["paired_complete"] is False
    assert execution["failure_class"] == "execution_failure"
    assert execution["camp_failure_stage"] == "tracker"
    assert source["included_in_denominator"] is True
    assert source["paired_complete"] is False
    assert source["failure_class"] == "source_failure"
    assert source["hard_invalid"] is True


def test_retained_pair_row_marks_complete_all_k_high_risk_pair() -> None:
    module = _metrics()
    row = module.retained_pair_row(
        pair_key="group-c/route-c/seed-23",
        split="calibration",
        dp_arm={"status": "ok"},
        camp_arm={"status": "ok", "all_k_high_risk": True},
    )

    assert row["included_in_denominator"] is True
    assert row["paired_complete"] is True
    assert row["failure_class"] is None
    assert row["all_k_high_risk"] is True
