import math

import numpy as np
import pytest


def _metrics():
    from camp_core.integrations import diffusion_planner_v21_native

    return diffusion_planner_v21_native


def _tick(index: int, **updates):
    record = {
        "tick_index": index,
        "min_obb_clearance_m": 3.0,
        "five_point_drivable_coverage": True,
        "speed_mps": 1.0,
        "ego_heading_rad": 0.0,
        "route_heading_rad": 0.0,
        "front_center_prev_xy": [float(index), -1.0],
        "front_center_xy": [float(index), 0.0],
        "red_light_at_interval_start": False,
        "red_stop_lines": np.empty((0, 2, 2), dtype=np.float64),
        "speed_limit_mps": 2.0,
        "position_xy": [float(index), 0.0],
    }
    record.update(updates)
    return record


def test_collision_and_noncollision_near_miss_thresholds() -> None:
    module = _metrics()
    records = [
        _tick(0, min_obb_clearance_m=0.0),
        _tick(1, min_obb_clearance_m=1e-6),
        _tick(2, min_obb_clearance_m=np.nextafter(1e-6, np.inf)),
        _tick(3, min_obb_clearance_m=2.0),
        _tick(4, min_obb_clearance_m=np.nextafter(2.0, np.inf)),
    ]

    summary = module.summarize_safety_cost_native_v1(records)

    assert summary["components"]["collision_any"] == 1.0
    assert summary["raw_counts"]["collision_ticks"] == 2
    assert summary["raw_counts"]["near_miss_noncollision_ticks"] == 2
    assert summary["denominators"]["clearance_ticks"] == 5
    assert summary["components"]["near_miss_noncollision_rate"] == pytest.approx(
        2 / 5
    )
    assert summary["minimum_clearance_m"] == 0.0
    assert summary["event_ticks"]["collision"] == [0, 1]
    assert summary["event_ticks"]["near_miss_noncollision"] == [2, 3]


def test_five_point_drivable_proxy_uses_injected_native_inside_callback() -> None:
    module = _metrics()
    points = np.array(
        [[0.0, 0.0], [-1.0, -1.0], [-1.0, 1.0], [1.0, 1.0], [1.0, -1.0]]
    )
    lanelets = ("left", "right")

    def inside(lanelet, point):
        return (lanelet == "left" and point[0] <= 0.0) or (
            lanelet == "right" and point[0] >= 0.0
        )

    assert module.five_point_drivable_coverage(points, lanelets, inside) is True
    outside = points.copy()
    outside[4, 0] = 2.0
    with pytest.raises(ValueError, match="exactly five"):
        module.five_point_drivable_coverage(outside[:4], lanelets, inside)
    assert module.five_point_drivable_coverage(
        outside,
        ("left",),
        inside,
    ) is False


def test_wrong_way_uses_moving_onroad_denominator_and_wrapped_heading() -> None:
    module = _metrics()
    records = [
        _tick(
            0,
            ego_heading_rad=-math.pi + 0.01,
            route_heading_rad=math.pi - 0.01,
        ),
        _tick(1, ego_heading_rad=math.pi, route_heading_rad=0.0),
        _tick(2, speed_mps=0.5, ego_heading_rad=math.pi),
        _tick(3, five_point_drivable_coverage=False, ego_heading_rad=math.pi),
    ]

    summary = module.summarize_safety_cost_native_v1(records)

    assert summary["denominators"]["moving_onroad_ticks"] == 2
    assert summary["raw_counts"]["wrong_way_ticks"] == 1
    assert summary["components"]["wrong_way_rate"] == 0.5
    assert summary["event_ticks"]["wrong_way"] == [1]


@pytest.mark.parametrize(
    ("a", "b", "c", "d", "expected"),
    (
        ((0, 0), (2, 0), (1, -1), (1, 1), True),
        ((0, 0), (1, 0), (1, 0), (2, 0), True),
        ((0, 0), (1, 0), (2, 0), (3, 0), False),
        ((0, 0), (1, 1), (0, 1), (1, 2), False),
    ),
)
def test_exact_2d_segment_intersection(a, b, c, d, expected: bool) -> None:
    module = _metrics()
    assert module.segments_intersect_2d(a, b, c, d) is expected


def test_red_light_violation_requires_red_at_start_speed_and_crossing() -> None:
    module = _metrics()
    stop_line = np.array([[[0.0, 0.0], [2.0, 0.0]]], dtype=np.float64)
    records = [
        _tick(
            0,
            front_center_prev_xy=[1.0, -1.0],
            front_center_xy=[1.0, 1.0],
            red_light_at_interval_start=True,
            red_stop_lines=stop_line,
        ),
        _tick(
            1,
            speed_mps=0.5,
            front_center_prev_xy=[1.0, -1.0],
            front_center_xy=[1.0, 1.0],
            red_light_at_interval_start=True,
            red_stop_lines=stop_line,
        ),
        _tick(
            2,
            front_center_prev_xy=[1.0, -1.0],
            front_center_xy=[1.0, 1.0],
            red_light_at_interval_start=False,
            red_stop_lines=stop_line,
        ),
    ]

    summary = module.summarize_safety_cost_native_v1(records)

    assert summary["components"]["red_light_violation_any"] == 1.0
    assert summary["raw_counts"]["red_light_violation_intervals"] == 1
    assert summary["event_ticks"]["red_light_violation"] == [0]


def test_speed_limit_rate_is_exact_and_missing_source_fails_closed() -> None:
    module = _metrics()
    records = [
        _tick(0, speed_mps=2.0 + 1e-6, speed_limit_mps=2.0),
        _tick(1, speed_mps=np.nextafter(2.0 + 1e-6, np.inf)),
        _tick(
            2,
            speed_mps=4.0,
            five_point_drivable_coverage=False,
            speed_limit_mps=None,
        ),
    ]

    summary = module.summarize_safety_cost_native_v1(records)

    assert summary["denominators"]["speed_limit_ticks"] == 2
    assert summary["raw_counts"]["speed_limit_violation_ticks"] == 1
    assert summary["components"]["speed_limit_violation_rate"] == 0.5
    assert summary["maximum_speed_excess_mps"] == pytest.approx(1e-6)

    records[0]["speed_limit_mps"] = None
    with pytest.raises(ValueError, match="speed_limit_mps"):
        module.summarize_safety_cost_native_v1(records)


def test_constant_velocity_circle_ttc_is_labeled_diagnostic_and_finite() -> None:
    module = _metrics()
    result = module.diagnostic_constant_velocity_circle_ttc_s(
        ego_position_xy=[0.0, 0.0],
        ego_velocity_xy=[1.0, 0.0],
        ego_radius_m=1.0,
        other_position_xy=[10.0, 0.0],
        other_velocity_xy=[-1.0, 0.0],
        other_radius_m=1.0,
    )
    assert result["name"] == "constant_velocity_circle_ttc_diagnostic_s"
    assert result["ttc_s"] == pytest.approx(4.0)
    assert result["observed_future_collision_claim"] is False

    diverging = module.diagnostic_constant_velocity_circle_ttc_s(
        ego_position_xy=[0.0, 0.0],
        ego_velocity_xy=[-1.0, 0.0],
        ego_radius_m=1.0,
        other_position_xy=[10.0, 0.0],
        other_velocity_xy=[1.0, 0.0],
        other_radius_m=1.0,
    )
    assert diverging["ttc_s"] is None


def test_route_comfort_summary_uses_point_one_second_grid() -> None:
    module = _metrics()
    records = [
        _tick(index, position_xy=[0.1 * index, 0.0], speed_mps=speed)
        for index, speed in enumerate((0.0, 1.0, 3.0, 6.0))
    ]

    summary = module.summarize_route_comfort_native(
        records,
        dt=0.1,
        route_progress_m=3.0,
        route_length_m=4.0,
        termination_reason="max_steps",
    )

    assert summary["dt_s"] == 0.1
    assert summary["route_completion_rate"] == 0.75
    assert summary["distance_traveled_m"] == pytest.approx(0.3)
    assert summary["stopped_fraction"] == 0.25
    assert summary["mean_speed_mps"] == pytest.approx(2.5)
    assert summary["max_acceleration_mps2"] == pytest.approx(30.0)
    assert summary["max_jerk_mps3"] == pytest.approx(100.0)
    assert summary["termination_reason"] == "max_steps"


def test_safety_formula_missing_components_and_zero_denominators_fail() -> None:
    module = _metrics()
    components = {
        "collision_any": 1.0,
        "near_miss_noncollision_rate": 0.5,
        "offroad_rate": 0.25,
        "wrong_way_rate": 0.5,
        "red_light_violation_any": 1.0,
        "speed_limit_violation_rate": 0.5,
    }
    assert module.safety_cost_native_v1(components) == 155.0

    missing = dict(components)
    missing.pop("offroad_rate")
    with pytest.raises(ValueError, match="components"):
        module.safety_cost_native_v1(missing)

    stopped = [_tick(0, speed_mps=0.0)]
    with pytest.raises(ValueError, match="moving_onroad_ticks"):
        module.summarize_safety_cost_native_v1(stopped)


def test_paired_delta_uses_camp_minus_dp_and_exact_tolerance() -> None:
    module = _metrics()
    better = module.paired_safety_delta(10.0, 8.0)
    tie = module.paired_safety_delta(10.0, 10.0 + 1e-12)
    worse = module.paired_safety_delta(10.0, 12.0)
    assert better == {"dp": 10.0, "camp": 8.0, "delta": -2.0, "result": "better"}
    assert tie["result"] == "tie"
    assert worse["result"] == "worse"

    aggregate = module.aggregate_paired_safety([better, tie, worse])
    assert aggregate["better_tie_worse"] == {"better": 1, "tie": 1, "worse": 1}
    assert aggregate["mean_delta"] == pytest.approx(0.0)
    assert aggregate["median_delta"] == pytest.approx(tie["delta"])


def test_route_projection_uses_native_geometry_not_line_type_channel_13() -> None:
    from camp_core.integrations import diffusion_planner_causal_atoms

    candidates = np.zeros((1, 80, 4), dtype=np.float32)
    candidates[0, :, 0] = np.linspace(0.1, 15.0, 80)
    candidates[0, :, 2] = 1.0
    route = np.zeros((25, 20, 33), dtype=np.float32)
    route[0, :, 0] = np.linspace(0.0, 20.0, 20)
    route[0, :, 2] = 1.0
    route[0, :, 5] = 2.0
    route[0, :, 7] = -2.0
    route[0, :, 17] = 1.0
    assert not route[..., 13].any()
    limits = np.zeros((25, 1), dtype=np.float32)
    limits[0] = 10.0
    has_limits = np.zeros((25, 1), dtype=bool)
    has_limits[0] = True

    result = diffusion_planner_causal_atoms.project_candidates_to_route(
        candidates, route, limits, has_limits
    )

    assert result["route_speed_source_eligible_mask"].tolist() == [True]
    assert result["route_progress"][0] > 14.0
