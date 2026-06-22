from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_route_topology_candidate_screen import (
    RouteTopologyCandidateConfig,
    _comfort_admissible,
    _comfort_failure_classes,
    _summarize_latency,
    _validate_config,
    route_failure_classes,
)


def _zero_tracker_delta() -> dict[str, float]:
    return {
        "command_jerk_worse_mps3": 0.0,
        "command_lateral_worse_mps2": 0.0,
        "rollout_distance_loss_m": 0.0,
        "rollout_jerk_worse_mps3": 0.0,
        "rollout_lateral_worse_mps2": 0.0,
    }


def test_default_policy_remains_default_off() -> None:
    config = RouteTopologyCandidateConfig()

    assert config.generator_policy == "lane_centerline_red_stop"
    assert config.generator_policy != "lane_projected_jerk_progress_red_stop"


def test_comfort_admissible_requires_current_gate_prerequisites() -> None:
    config = RouteTopologyCandidateConfig()

    assert _comfort_admissible(
        progress_loss=0.2,
        smoothness_loss=0.0,
        tracker_delta=_zero_tracker_delta(),
        lower_union_red=True,
        hard_feasible=True,
        progress_feasible=True,
        config=config,
    )

    assert not _comfort_admissible(
        progress_loss=0.2,
        smoothness_loss=0.0,
        tracker_delta=_zero_tracker_delta(),
        lower_union_red=False,
        hard_feasible=True,
        progress_feasible=True,
        config=config,
    )
    assert not _comfort_admissible(
        progress_loss=0.2,
        smoothness_loss=0.0,
        tracker_delta=_zero_tracker_delta(),
        lower_union_red=True,
        hard_feasible=False,
        progress_feasible=True,
        config=config,
    )
    assert not _comfort_admissible(
        progress_loss=0.2,
        smoothness_loss=0.0,
        tracker_delta=_zero_tracker_delta(),
        lower_union_red=True,
        hard_feasible=True,
        progress_feasible=False,
        config=config,
    )


def test_comfort_admissible_blocks_tracker_budget_regressions() -> None:
    tracker_delta = _zero_tracker_delta()
    tracker_delta["command_jerk_worse_mps3"] = 0.01

    assert not _comfort_admissible(
        progress_loss=0.2,
        smoothness_loss=0.0,
        tracker_delta=tracker_delta,
        lower_union_red=True,
        hard_feasible=True,
        progress_feasible=True,
        config=RouteTopologyCandidateConfig(),
    )


def test_comfort_failure_classes_pin_budget_family_labels() -> None:
    row = {
        "progress_loss_m": 2.0,
        "smoothness_loss": 1.5,
        "tracker_delta": {
            "command_jerk_worse_mps3": 0.1,
            "command_lateral_worse_mps2": 0.1,
            "rollout_distance_loss_m": 0.2,
            "rollout_jerk_worse_mps3": 0.1,
            "rollout_lateral_worse_mps2": 0.1,
        },
    }

    assert _comfort_failure_classes(row) == [
        "route_topology_comfort_blocked_progress_loss",
        "route_topology_comfort_blocked_smoothness_loss",
        "route_topology_comfort_blocked_command_jerk",
        "route_topology_comfort_blocked_command_lateral",
        "route_topology_comfort_blocked_rollout_distance",
        "route_topology_comfort_blocked_rollout_jerk",
        "route_topology_comfort_blocked_rollout_lateral",
    ]


def test_hard_feasibility_labels_are_reported_without_dp_changes() -> None:
    row = {
        "lower_union_red": True,
        "hard_reasons": ["dp_lane_crossing", "dp_red_light", "dp_kinematic"],
        "hard_feasible": False,
        "progress_feasible": False,
        "comfort_admissible": False,
    }

    assert route_failure_classes(row) == [
        "route_topology_lane_invalid",
        "route_topology_red_timing_invalid",
        "route_topology_dp_kinematic",
    ]


def test_latency_reporting_pins_candidate_build_and_total_fields() -> None:
    rows = [
        {
            "timings_ms": {
                "baseline_reward": 1.0,
                "baseline_tracker": 2.0,
                "candidate_build": 3.0,
                "generated_reward": 4.0,
                "generated_tracker": 5.0,
                "total": 6.0,
            }
        },
        {
            "timings_ms": {
                "baseline_reward": 2.0,
                "baseline_tracker": 3.0,
                "candidate_build": 4.0,
                "generated_reward": 5.0,
                "generated_tracker": 6.0,
                "total": 7.0,
            }
        },
    ]

    summary = _summarize_latency(rows)

    assert summary["candidate_build"]["count"] == 2
    assert summary["candidate_build"]["p50"] == 3.5
    assert summary["total"]["count"] == 2
    assert summary["total"]["p50"] == 6.5


def test_validate_config_rejects_invalid_remediation_budgets() -> None:
    with pytest.raises(ValueError, match="progress_loss_budgets_m"):
        _validate_config(
            RouteTopologyCandidateConfig(progress_loss_budgets_m=(-0.1,))
        )
    with pytest.raises(ValueError, match="smoothness_loss_budgets"):
        _validate_config(
            RouteTopologyCandidateConfig(smoothness_loss_budgets=(-0.1,))
        )
    with pytest.raises(ValueError, match="command_jerk_worse_budget_mps3"):
        _validate_config(
            RouteTopologyCandidateConfig(command_jerk_worse_budget_mps3=-0.1)
        )
