from __future__ import annotations

import numpy as np
import pytest

from scripts.integrations.analyze_diffusion_planner_route_topology_candidate_screen import (
    GENERATOR_POLICY_MATERIAL_SUPPORT,
    GENERATOR_POLICY_MATERIAL_SUPPORT_V2,
    GENERATOR_POLICY_MATERIAL_SUPPORT_V3,
    REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1,
    REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2,
    REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3,
    RouteTopologyCandidateConfig,
    _effective_comfort_budgets,
    _validate_config,
    build_route_topology_candidates,
    route_topology_candidate_construction_diagnostics,
)


def _lane_fixture(
    *,
    horizon: int = 40,
    lateral_m: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    candidates = np.zeros((1, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.0, 8.0, horizon)
    candidates[0, :, 1] = lateral_m
    candidates[0, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 25.0, 31)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([np.linspace(14.0, 15.0, 3), np.zeros(3)])
    return candidates, lane, red


def _v3_config(**overrides: object) -> RouteTopologyCandidateConfig:
    params = {
        "generator_policy": GENERATOR_POLICY_MATERIAL_SUPPORT_V3,
        "default_off_remediation_profile": REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3,
        "red_stop_margins_m": (2.0,),
        "backup_stop_offsets_m": (0.0,),
        "prefix_steps": (1,),
        "bridge_steps": (0,),
        "lane_projected_offset_scales": (0.0,),
        "max_remediation_candidates": 2,
        "command_jerk_worse_budget_mps3": 1e6,
        "rollout_jerk_worse_budget_mps3": 1e6,
        "rollout_lateral_worse_budget_mps2": 1e6,
        "progress_loss_budgets_m": (1000.0,),
        "smoothness_loss_budgets": (1000.0,),
    }
    params.update(overrides)
    return RouteTopologyCandidateConfig(**params)


def test_v3_material_support_requires_explicit_profile_policy_pair() -> None:
    with pytest.raises(ValueError, match="material_support_profile_required"):
        _validate_config(
            RouteTopologyCandidateConfig(
                generator_policy=GENERATOR_POLICY_MATERIAL_SUPPORT_V3
            )
        )

    with pytest.raises(ValueError, match="material_support_policy_required"):
        _validate_config(
            RouteTopologyCandidateConfig(
                default_off_remediation_profile=(
                    REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3
                )
            )
        )

    _validate_config(_v3_config())


def test_v3_material_support_preserves_v1_v2_profile_mapping() -> None:
    _validate_config(
        RouteTopologyCandidateConfig(
            generator_policy=GENERATOR_POLICY_MATERIAL_SUPPORT,
            default_off_remediation_profile=REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1,
        )
    )
    _validate_config(
        RouteTopologyCandidateConfig(
            generator_policy=GENERATOR_POLICY_MATERIAL_SUPPORT_V2,
            default_off_remediation_profile=REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2,
        )
    )


def test_v3_material_support_appends_after_dp_rows_without_mutating_candidate0() -> None:
    candidates, lane, red = _lane_fixture()
    original = candidates.copy()

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=_v3_config(),
    )

    assert generated.shape == (1, candidates.shape[1], candidates.shape[2])
    np.testing.assert_allclose(candidates, original)
    assert meta[0]["append_after_existing_candidate_count"] == candidates.shape[0]
    assert meta[0]["candidate0_preserved"] is True
    assert meta[0]["dp_rows_preserved"] is True
    assert meta[0]["source_candidate_index"] == 0


def test_v3_material_support_fails_closed_on_hard_precheck() -> None:
    candidates, lane, red = _lane_fixture()

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=20.0,
        dt=0.1,
        config=_v3_config(max_deceleration_mps2=0.5),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=20.0,
        dt=0.1,
        config=_v3_config(max_deceleration_mps2=0.5),
    )

    assert generated.shape == (0, candidates.shape[1], candidates.shape[2])
    assert meta == []
    assert diagnostics["construction_status"] == "fail_closed"
    assert diagnostics["failure_reason"] == "kinematic_deceleration_margin_negative"
    assert diagnostics["lane_red_hard_feasibility_precheck_required"] is True
    assert diagnostics["lane_red_hard_feasible_windows"] == 0


def test_v3_material_support_fails_closed_on_comfort_first_precheck() -> None:
    candidates, lane, red = _lane_fixture(lateral_m=1.0)

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=_v3_config(),
    )

    assert generated.shape == (0, candidates.shape[1], candidates.shape[2])
    assert meta == []


def test_v3_effective_budgets_do_not_apply_v1_v2_budget_floors() -> None:
    config = _v3_config(
        command_jerk_worse_budget_mps3=0.0,
        rollout_lateral_worse_budget_mps2=0.0,
        progress_loss_budgets_m=(0.5,),
        smoothness_loss_budgets=(0.0,),
    )

    budgets = _effective_comfort_budgets(config)

    assert budgets["default_off_remediation_profile"] == (
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V3
    )
    assert budgets["progress_loss_budgets_m"] == (0.5,)
    assert budgets["smoothness_loss_budgets"] == (0.0,)
    assert budgets["command_jerk_worse_budget_mps3"] == 0.0
    assert budgets["rollout_lateral_worse_budget_mps2"] == 0.0


def test_v3_descriptor_channels_remain_report_only_and_affine_compatible() -> None:
    candidates, lane, red = _lane_fixture()

    _, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=2.0,
        dt=0.1,
        config=_v3_config(),
    )
    descriptor = meta[0]["remediation_descriptor_payload"]

    assert meta[0]["comfort_first_precheck_passed"] is True
    assert meta[0]["current_tick_features_only"] is True
    assert descriptor["diagnostic_descriptor_payload_v3"] is True
    assert descriptor["diagnostic_descriptor_payload_v3_report_only"] is True
    assert descriptor["uses_outcome_labels"] is False
    assert descriptor["nonnegative_descriptor_channels"] is True
    assert descriptor["hinge_signed_split_channels"] is True
    assert descriptor["affine_score_compatible"] is True
    assert descriptor["score_contract"] == "score_k(w)=a_k^T w"
    assert descriptor["convex_master_contract"] == "simplex/CVaR/L2 unchanged"
    assert descriptor["candidate_mutation"] is False
    assert descriptor["score_mutation"] is False
    assert descriptor["selected_index_mutation"] is False
    assert descriptor["fallback_mutation"] is False
    assert descriptor["online_selector_feature"] is False
    assert descriptor["runtime_atom_promotion"] is False
    assert descriptor["atom_promotion"] is False
    assert descriptor["online_selector_promotion"] is False
    assert descriptor["future_outcome_leakage"] is False
