from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_postprocess_tracker_descriptor_audit import (
    GROUP_SIGNAL_KEYS,
    analyze_materiality_rows,
    render_markdown,
)


def _row(
    *,
    tracker_jerk: float,
    tracker_lateral: float,
    prefix_jerk: float,
    rollout_jerk: float,
    rollout_lateral: float,
    progress: float,
    target_speed: float,
    prefix_distance: float,
) -> dict[str, float]:
    row = {
        "outcome_progress_delta_m": progress,
        "outcome_progress_deficit_m": max(0.0, -progress),
        "outcome_jerk_delta_mps3": -1.0,
        "outcome_lateral_delta_mps2": -0.5,
        "outcome_value_delta": -1.0,
        "raw_route_progress_delta_m": progress,
        "raw_step_reach_delta_m": progress / 10.0,
        "raw_dp_prior_jerk_excess_delta": -0.5,
        "raw_dp_prior_lateral_excess_delta": -0.2,
        "raw_horizon_lateral_delta": -0.3,
        "raw_horizon_yaw_delta": 0.0,
        "tracker_first_step_reach_delta_m": progress / 10.0,
        "tracker_tail_average_speed_delta_mps": target_speed,
        "tracker_target_speed_delta_mps": target_speed,
        "tracker_command_jerk_delta_mps3": tracker_jerk,
        "tracker_command_lateral_delta_mps2": tracker_lateral,
        "tracker_command_yaw_rate_delta_rps": 0.0,
        "prefix_max_xy_distance_m": prefix_distance,
        "prefix_mean_xy_distance_m": prefix_distance / 2.0,
        "prefix_jerk_proxy_delta": prefix_jerk,
    }
    for horizon in (3, 5, 10):
        row[f"prefix_h{horizon}_displacement_delta_m"] = progress / 10.0
        row[f"prefix_h{horizon}_path_delta_m"] = progress / 10.0
        row[f"rollout_h{horizon}_distance_m_delta"] = progress / 10.0
        row[f"rollout_h{horizon}_mean_vector_jerk_mps3_delta"] = rollout_jerk
        row[f"rollout_h{horizon}_max_vector_jerk_mps3_delta"] = rollout_jerk * 1.2
        row[
            f"rollout_h{horizon}_mean_lateral_acceleration_mps2_delta"
        ] = rollout_lateral
        row[
            f"rollout_h{horizon}_max_lateral_acceleration_mps2_delta"
        ] = rollout_lateral * 1.2
    return row


def test_postprocess_tracker_audit_finds_state_descriptor_signal() -> None:
    preserved = [
        _row(
            tracker_jerk=-0.4,
            tracker_lateral=-0.2,
            prefix_jerk=-0.01,
            rollout_jerk=-0.5,
            rollout_lateral=-0.3,
            progress=-0.01,
            target_speed=-0.01,
            prefix_distance=0.01,
        )
        for _ in range(4)
    ]
    flipped = [
        _row(
            tracker_jerk=0.5,
            tracker_lateral=0.2,
            prefix_jerk=0.01,
            rollout_jerk=0.7,
            rollout_lateral=0.3,
            progress=-0.6,
            target_speed=-0.8,
            prefix_distance=0.4,
        )
        for _ in range(4)
    ]

    report = analyze_materiality_rows(
        [*preserved, *flipped],
        label="unit",
        min_group_records=2,
        separation_threshold=0.5,
    )

    assert report["records"]["preserved_rows"] == 4
    assert report["records"]["flipped_rows"] == 4
    assert (
        report["final_decision"]["status"]
        == "state_conditioned_descriptor_signal_present"
    )
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False

    descriptor_keys = {
        item["key"] for item in report["descriptor_separation"]["top"]
    }
    assert report["final_decision"]["top_descriptor"]["key"] in descriptor_keys
    assert not descriptor_keys.intersection(GROUP_SIGNAL_KEYS)

    markdown = render_markdown(report)
    assert "Postprocess/Tracker Descriptor Audit" in markdown
    assert "not classical Benders decomposition" in markdown


def test_postprocess_tracker_audit_rejects_underpowered_groups() -> None:
    report = analyze_materiality_rows(
        [
            _row(
                tracker_jerk=-0.4,
                tracker_lateral=-0.2,
                prefix_jerk=-0.01,
                rollout_jerk=-0.5,
                rollout_lateral=-0.3,
                progress=-0.01,
                target_speed=-0.01,
                prefix_distance=0.01,
            ),
            _row(
                tracker_jerk=-0.3,
                tracker_lateral=-0.1,
                prefix_jerk=-0.02,
                rollout_jerk=-0.4,
                rollout_lateral=-0.2,
                progress=-0.02,
                target_speed=-0.02,
                prefix_distance=0.02,
            ),
        ],
        min_group_records=2,
    )

    assert (
        report["final_decision"]["status"]
        == "postprocess_tracker_audit_group_support_insufficient"
    )
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False


def test_postprocess_tracker_audit_rejects_formal_seed_counts() -> None:
    with pytest.raises(ValueError, match="Formal seed logs are forbidden"):
        analyze_materiality_rows(
            [],
            record_counts={
                "logs": 1,
                "formal_seed_logs": 1,
                "total": 0,
                "nonfallback": 0,
                "fallback": 0,
                "with_oracle_donor": 0,
                "without_oracle_donor": 0,
            },
            fail_on_formal_seeds=True,
        )
