from __future__ import annotations

import inspect

import numpy as np

from scripts.integrations.analyze_diffusion_planner_route_topology_candidate_screen import (
    RouteTopologyCandidateConfig,
    _command_jerk_descriptor_payload,
    build_route_topology_candidates,
)


def _simple_fixture() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    horizon = 40
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.5, 16.0, horizon)
    candidates[0, :, 1] = 0.6
    candidates[0, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 25.0, 31)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([np.linspace(3.0, 3.5, 3), np.zeros(3)])
    return candidates, lane, red


def test_residual_comfort_remediation_default_off_preserves_candidate0() -> None:
    config = RouteTopologyCandidateConfig()

    assert config.generator_policy == "lane_centerline_red_stop"
    assert config.max_remediation_candidates == 12

    candidates, lane, red = _simple_fixture()
    original = candidates.copy()
    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=config,
    )

    np.testing.assert_allclose(candidates, original)
    assert generated.shape[1:] == candidates.shape[1:]
    assert all(row["variant"] == "lane_centerline_red_stop" for row in meta)
    assert all("remediation_descriptor_payload" not in row for row in meta)


def test_residual_comfort_remediation_report_only_descriptor_payload() -> None:
    candidates, lane, red = _simple_fixture()
    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="negative_support_coverage_first_lane_projected_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            lane_projected_offset_scales=(0.0,),
            min_stop_distance_m=2.0,
            max_remediation_candidates=1,
        ),
    )

    assert generated.shape == (1, candidates.shape[1], candidates.shape[2])
    payload = meta[0]["remediation_descriptor_payload"]
    assert payload["payload_role"] == "report_only_current_tick_descriptor"
    assert payload["descriptor_family"] == "command_jerk_hinge"
    assert payload["top_comfort_blocker"] == "route_topology_comfort_blocked_command_jerk"
    assert payload["current_tick_features_only"] is True
    assert payload["candidate_local"] is True
    assert payload["nonnegative_or_hinge_signed_split_legal"] is True
    assert payload["command_jerk_abs_max_mps3"] >= 0.0
    assert payload["command_jerk_hinge_mps3"] >= 0.0
    assert payload["score_contract"] == "score_k(w)=a_k^T w"
    assert payload["convex_master_contract"] == "simplex/CVaR/L2 unchanged"


def test_residual_comfort_remediation_blocks_candidate_mutation() -> None:
    candidates, lane, red = _simple_fixture()
    original = candidates.copy()
    _generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="negative_support_coverage_first_lane_projected_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            lane_projected_offset_scales=(0.0,),
            min_stop_distance_m=2.0,
            max_remediation_candidates=1,
        ),
    )

    np.testing.assert_allclose(candidates, original)
    payload = meta[0]["remediation_descriptor_payload"]
    assert payload["candidate_mutation"] is False
    assert payload["selected_index_mutation"] is False
    assert payload["fallback_mutation"] is False


def test_residual_comfort_remediation_blocks_online_selector_and_atoms() -> None:
    candidates, lane, red = _simple_fixture()
    _generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="negative_support_coverage_first_lane_projected_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            lane_projected_offset_scales=(0.0,),
            min_stop_distance_m=2.0,
            max_remediation_candidates=1,
        ),
    )

    payload = meta[0]["remediation_descriptor_payload"]
    assert payload["online_selector_feature"] is False
    assert payload["deployed_atom_schema_change"] is False
    assert "lambda" not in payload


def test_residual_comfort_remediation_preserves_affine_score_and_convex_master() -> None:
    source = inspect.getsource(_command_jerk_descriptor_payload)

    assert "score_k(w)=a_k^T w" in source
    assert "simplex/CVaR/L2 unchanged" in source
    assert "nonnegative_or_hinge_signed_split_legal" in source


def test_residual_comfort_remediation_blocks_dp_import_reward_tracker_recompute() -> None:
    candidates, lane, red = _simple_fixture()
    _generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy="negative_support_coverage_first_lane_projected_red_stop",
            red_stop_margins_m=(2.0,),
            backup_stop_offsets_m=(0.0,),
            lane_projected_offset_scales=(0.0,),
            min_stop_distance_m=2.0,
            max_remediation_candidates=1,
        ),
    )
    payload = meta[0]["remediation_descriptor_payload"]
    source = inspect.getsource(_command_jerk_descriptor_payload)

    assert payload["dp_import"] is False
    assert payload["reward_recompute"] is False
    assert payload["tracker_recompute"] is False
    assert "_score_trajectories" not in source
    assert "reward_metric_vector" not in source
    assert "reward_hard_feasibility" not in source
    assert "reward_progress_screen" not in source
    assert "_tracker_diagnostics" not in source
    assert "_tracker_delta" not in source


def test_residual_comfort_remediation_blocks_execution_training_replay_formal_seeds() -> None:
    source = inspect.getsource(_command_jerk_descriptor_payload)

    assert "formal" not in source.lower()
    assert "train" not in source.lower()
    assert "replay" not in source.lower()
    assert "seed=11" not in source
    assert "seed=12" not in source
    assert "seed=13" not in source


def test_residual_comfort_remediation_cli_contract_artifact() -> None:
    config = RouteTopologyCandidateConfig(
        generator_policy="negative_support_coverage_first_lane_projected_red_stop",
        max_remediation_candidates=2,
    )

    assert config.generator_policy == "negative_support_coverage_first_lane_projected_red_stop"
    assert config.max_remediation_candidates == 2
