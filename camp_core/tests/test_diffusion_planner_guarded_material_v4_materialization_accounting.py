from __future__ import annotations

import numpy as np

from scripts.integrations.analyze_diffusion_planner_route_topology_candidate_screen import (
    GENERATOR_POLICY_MATERIAL_SUPPORT_V3,
    GENERATOR_POLICY_MATERIAL_SUPPORT_V4,
    REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3,
    REMEDIATION_PROFILE_MATERIAL_SUPPORT_V4,
    RouteTopologyCandidateConfig,
    _effective_comfort_budgets,
    _snapshot_report_row,
    build_route_topology_candidates,
    route_topology_candidate_construction_diagnostics,
)


def _straight_fixture(
    *,
    horizon: int = 40,
    selected_end_x: float = 8.0,
    red_start_x: float = 6.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.0, selected_end_x, horizon)
    candidates[0, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 25.0, 31)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([np.linspace(red_start_x, red_start_x + 1.0, 3), np.zeros(3)])
    return candidates, lane, red


def _v4_config(**overrides: object) -> RouteTopologyCandidateConfig:
    values = {
        "generator_policy": GENERATOR_POLICY_MATERIAL_SUPPORT_V4,
        "default_off_remediation_profile": REMEDIATION_PROFILE_MATERIAL_SUPPORT_V4,
        "red_stop_margins_m": (2.0,),
        "backup_stop_offsets_m": (0.0,),
        "prefix_steps": (1,),
        "bridge_steps": (0,),
        "lane_projected_offset_scales": (0.0,),
        "max_remediation_candidates": 2,
    }
    values.update(overrides)
    return RouteTopologyCandidateConfig(**values)


def test_v4_explicit_pair_required() -> None:
    candidates, lane, red = _straight_fixture()
    config = RouteTopologyCandidateConfig(
        generator_policy=GENERATOR_POLICY_MATERIAL_SUPPORT_V4,
        default_off_remediation_profile="off",
    )

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=config,
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=config,
    )

    assert generated.shape == (0, candidates.shape[1], candidates.shape[2])
    assert meta == []
    assert diagnostics["material_support_profile_required"] is True
    assert diagnostics["material_support_profile_evidence"] is False
    assert diagnostics["failure_reason"] == "material_support_profile_required"


def test_v4_ready_diagnostics_materialize_candidate_rows() -> None:
    candidates, lane, red = _straight_fixture(red_start_x=6.0)
    v3_config = RouteTopologyCandidateConfig(
        generator_policy=GENERATOR_POLICY_MATERIAL_SUPPORT_V3,
        default_off_remediation_profile=REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3,
        red_stop_margins_m=(2.0,),
        backup_stop_offsets_m=(0.0,),
        prefix_steps=(1,),
        bridge_steps=(0,),
        lane_projected_offset_scales=(0.0,),
        max_remediation_candidates=2,
    )

    v3_generated, v3_meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=v3_config,
    )
    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=_v4_config(),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=_v4_config(),
    )

    assert v3_generated.shape == (0, candidates.shape[1], candidates.shape[2])
    assert v3_meta == []
    assert diagnostics["construction_status"] == "ready"
    assert diagnostics["failure_reason"] is None
    assert diagnostics["candidate_materialization_v4"] is True
    assert generated.shape == (1, candidates.shape[1], candidates.shape[2])
    assert len(meta) == 1
    assert meta[0]["variant"] == GENERATOR_POLICY_MATERIAL_SUPPORT_V4
    assert meta[0]["profile"] == REMEDIATION_PROFILE_MATERIAL_SUPPORT_V4
    assert meta[0]["candidate_materialization_v4"] is True
    assert meta[0]["materialized_before_support_gate"] is True
    assert meta[0]["candidate0_preserved"] is True
    assert meta[0]["dp_rows_preserved"] is True
    assert meta[0]["append_after_existing_candidate_count"] == candidates.shape[0]
    assert meta[0]["comfort_first_precheck_report_only"] is True
    assert meta[0]["comfort_first_precheck_passed"] is False
    assert meta[0]["comfort_budget_relaxation"] is False


def test_v4_generated_count_matches_candidate_rows() -> None:
    candidates, lane, red = _straight_fixture(red_start_x=6.0)
    _, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=_v4_config(),
    )

    row = _snapshot_report_row(
        snapshot_path=__file__,
        arrays={},
        metadata={"selected_index": 0, "selection_step": 7},
        generated_meta=meta,
        baseline_scores={
            "union_red_cost": np.asarray([10.0]),
            "reward_breakdowns": [{"progress": 8.0, "smoothness": 0.0}],
        },
        generated_scores={
            "union_red_cost": np.asarray([5.0]),
            "near_red_cost": np.asarray([5.0]),
            "full_red_cost": np.asarray([5.0]),
            "reward_breakdowns": [{"progress": 8.0, "smoothness": 0.0}],
        },
        baseline_tracker={
            "command": {
                "jerk_magnitude_mps3": np.asarray([0.0]),
                "lateral_acceleration_magnitude_mps2": np.asarray([0.0]),
            },
            "open_loop": {
                "horizons": {
                    "3": {
                        "distance_m": np.asarray([8.0]),
                        "max_vector_jerk_mps3": np.asarray([0.0]),
                        "max_lateral_acceleration_mps2": np.asarray([0.0]),
                    }
                }
            },
        },
        generated_tracker={
            "command": {
                "jerk_magnitude_mps3": np.asarray([0.0]),
                "lateral_acceleration_magnitude_mps2": np.asarray([0.0]),
            },
            "open_loop": {
                "horizons": {
                    "3": {
                        "distance_m": np.asarray([8.0]),
                        "max_vector_jerk_mps3": np.asarray([0.0]),
                        "max_lateral_acceleration_mps2": np.asarray([0.0]),
                    }
                }
            },
        },
        config=_v4_config(),
        timings_ms={"candidate_build": 0.1, "total": 0.2},
        construction_diagnostics={
            "construction_status": "ready",
            "candidate_materialization_v4": True,
        },
    )

    assert row["generated_count"] == len(row["candidate_rows"]) == len(meta)
    assert row["candidate_rows"][0]["candidate_meta"]["candidate0_preserved"] is True
    assert row["candidate_rows"][0]["candidate_meta"]["dp_rows_preserved"] is True


def test_v4_red_stop_distance_window_fails_closed_without_candidates() -> None:
    candidates, lane, red = _straight_fixture(red_start_x=1.0)

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=_v4_config(),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=_v4_config(),
    )

    assert generated.shape == (0, candidates.shape[1], candidates.shape[2])
    assert meta == []
    assert diagnostics["construction_status"] == "fail_closed"
    assert diagnostics["failure_reason"] == "red_stop_distance_window"
    assert diagnostics["fail_closed_partition"] == "red_stop_distance_window"


def test_v4_requires_finite_current_tick_inputs_only() -> None:
    candidates, lane, red = _straight_fixture()

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=np.nan,
        dt=0.1,
        config=_v4_config(),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=np.nan,
        dt=0.1,
        config=_v4_config(),
    )

    assert generated.shape == (0, candidates.shape[1], candidates.shape[2])
    assert meta == []
    assert diagnostics["requires_current_tick_scalar_evidence"] is True
    assert diagnostics["current_tick_scalar_evidence"] is False
    assert diagnostics["failure_reason"] == "current_tick_scalar_invalid"
    assert diagnostics["current_tick_features_only"] is True


def test_v4_descriptor_legality_and_comfort_budget_contract() -> None:
    candidates, lane, red = _straight_fixture(red_start_x=6.0)
    config = _v4_config(
        command_jerk_worse_budget_mps3=0.0,
        command_lateral_worse_budget_mps2=0.0,
        rollout_jerk_worse_budget_mps3=0.0,
        rollout_lateral_worse_budget_mps2=0.0,
        progress_loss_budgets_m=(0.5, 1.0, 1.5),
        smoothness_loss_budgets=(0.0, 0.5, 1.0),
    )

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=config,
    )
    budgets = _effective_comfort_budgets(config)
    descriptor = meta[0]["remediation_descriptor_payload"]

    assert generated.shape[0] == 1
    assert budgets["default_off_remediation_profile"] == (
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V4
    )
    assert budgets["progress_loss_budgets_m"] == config.progress_loss_budgets_m
    assert budgets["smoothness_loss_budgets"] == config.smoothness_loss_budgets
    assert budgets["command_jerk_worse_budget_mps3"] == 0.0
    assert budgets["command_lateral_worse_budget_mps2"] == 0.0
    assert budgets["rollout_jerk_worse_budget_mps3"] == 0.0
    assert budgets["rollout_lateral_worse_budget_mps2"] == 0.0
    assert descriptor["diagnostic_descriptor_payload_v4"] is True
    assert descriptor["diagnostic_descriptor_payload_v4_report_only"] is True
    assert descriptor["nonnegative_descriptor_channels"] is True
    assert descriptor["hinge_signed_split_channels"] is True
    assert descriptor["affine_score_compatible"] is True
    assert descriptor["score_contract"] == "score_k(w)=a_k^T w"
    assert descriptor["convex_master_contract"] == "simplex/CVaR/L2 unchanged"
    assert descriptor["uses_outcome_labels"] is False
    assert descriptor["score_mutation"] is False
    assert descriptor["selected_index_mutation"] is False
    assert descriptor["fallback_mutation"] is False
    assert descriptor["online_selector_feature"] is False
    assert descriptor["deployed_atom_schema_change"] is False
    assert descriptor["future_outcome_leakage"] is False
    assert descriptor["candidate_materialization_v4"] is True
    assert descriptor["comfort_first_precheck_report_only"] is True
