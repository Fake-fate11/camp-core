from __future__ import annotations

import numpy as np
import pytest

from scripts.integrations.analyze_diffusion_planner_route_topology_candidate_screen import (
    GENERATOR_POLICY_MATERIAL_SUPPORT,
    REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1,
    REMEDIATION_PROFILE_OFF,
    REMEDIATION_PROFILE_SUPPORT_V1,
    RouteTopologyCandidateConfig,
    _effective_comfort_budgets,
    _validate_config,
    build_route_topology_candidates,
    route_topology_candidate_construction_diagnostics,
)


def _straight_fixture(
    *,
    horizon: int = 50,
    lateral: float = 0.6,
    red_start_m: float = 12.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    candidates = np.zeros((2, horizon, 4), dtype=float)
    candidates[0, :, 0] = np.linspace(0.4, 30.0, horizon)
    candidates[0, :, 1] = lateral
    candidates[0, :, 2] = 1.0
    candidates[1, :, 0] = np.linspace(0.2, 28.0, horizon)
    candidates[1, :, 1] = -0.2
    candidates[1, :, 2] = 1.0
    lane_x = np.linspace(-5.0, 45.0, 51)
    lane = np.column_stack([lane_x, np.zeros_like(lane_x)])
    red = np.column_stack([np.linspace(red_start_m, red_start_m + 1.0, 3), np.zeros(3)])
    return candidates, lane, red


def _material_config(**overrides: object) -> RouteTopologyCandidateConfig:
    params: dict[str, object] = {
        "generator_policy": GENERATOR_POLICY_MATERIAL_SUPPORT,
        "default_off_remediation_profile": REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1,
        "red_stop_margins_m": (1.0,),
        "backup_stop_offsets_m": (0.0,),
        "prefix_steps": (1,),
        "bridge_steps": (8,),
        "lane_projected_offset_scales": (0.5, 0.0),
        "max_deceleration_mps2": 3.0,
        "jerk_progress_max_jerk_mps3": 6.0,
        "max_remediation_candidates": 3,
    }
    params.update(overrides)
    return RouteTopologyCandidateConfig(**params)


def test_material_generator_default_config_remains_default_off() -> None:
    candidates, lane, red = _straight_fixture()
    original = candidates.copy()

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(),
    )

    assert RouteTopologyCandidateConfig().default_off_remediation_profile == (
        REMEDIATION_PROFILE_OFF
    )
    assert generated.shape[1:] == candidates.shape[1:]
    assert len(meta) == generated.shape[0]
    assert {row["variant"] for row in meta} == {"lane_centerline_red_stop"}
    assert all("candidate0_preserved" not in row for row in meta)
    np.testing.assert_allclose(candidates, original)


def test_material_generator_requires_explicit_policy_profile_pair() -> None:
    candidates, lane, red = _straight_fixture()

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy=GENERATOR_POLICY_MATERIAL_SUPPORT
        ),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy=GENERATOR_POLICY_MATERIAL_SUPPORT
        ),
    )

    assert generated.shape == (0, candidates.shape[1], candidates.shape[2])
    assert meta == []
    assert diagnostics["construction_status"] == "fail_closed"
    assert diagnostics["failure_reason"] == "material_support_profile_required"
    assert diagnostics["fail_closed_partition"] == "material_support_profile_required"
    assert diagnostics["candidate0_preserved"] is True
    assert diagnostics["dp_rows_preserved"] is True
    assert diagnostics["current_tick_features_only"] is True


def test_material_generator_builds_candidate0_preserving_support_rows() -> None:
    candidates, lane, red = _straight_fixture()
    original = candidates.copy()

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=_material_config(),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=_material_config(),
    )

    assert generated.shape == (2, candidates.shape[1], candidates.shape[2])
    assert len(meta) == 2
    assert {row["variant"] for row in meta} == {GENERATOR_POLICY_MATERIAL_SUPPORT}
    assert all(row["profile"] == REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1 for row in meta)
    assert all(row["candidate0_preserved"] is True for row in meta)
    assert all(row["dp_rows_preserved"] is True for row in meta)
    assert all(row["append_after_existing_candidate_count"] == 2 for row in meta)
    assert all(row["source_candidate_index"] == 0 for row in meta)
    assert all(row["current_tick_features_only"] is True for row in meta)
    assert all(row["uses_outcome_labels"] is False for row in meta)
    assert all(row["future_outcome_leakage"] is False for row in meta)
    assert all(row["candidate_budget_cap"] == 3 for row in meta)
    np.testing.assert_allclose(candidates, original)
    np.testing.assert_allclose(generated[0, 0, :2], original[0, 0, :2])
    assert np.all(np.isfinite(generated))
    assert np.all(np.diff(generated[0, :, 0]) >= -1e-9)
    assert diagnostics["construction_status"] == "ready"
    assert diagnostics["failure_reason"] is None
    assert diagnostics["candidate0_preserved"] is True
    assert diagnostics["dp_rows_preserved"] is True
    assert diagnostics["current_tick_features_only"] is True


def test_material_generator_descriptor_payload_is_report_only_and_nonnegative() -> None:
    candidates, lane, red = _straight_fixture()

    _, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=_material_config(),
    )
    payload = meta[0]["remediation_descriptor_payload"]

    assert payload["payload_role"] == "report_only_current_tick_descriptor"
    assert payload["descriptor_family"] == (
        "lane_station_jerk_limited_red_stop_material_support"
    )
    assert payload["material_support_profile"] == REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1
    assert payload["current_tick_features_only"] is True
    assert payload["candidate_local"] is True
    assert payload["uses_outcome_labels"] is False
    assert payload["future_outcome_leakage"] is False
    assert payload["nonnegative_descriptor_channels"] is True
    assert payload["hinge_signed_split_channels"] is True
    assert payload["affine_score_compatible"] is True
    assert payload["score_contract"] == "score_k(w)=a_k^T w"
    assert payload["convex_master_contract"] == "simplex/CVaR/L2 unchanged"
    assert payload["candidate_mutation"] is False
    assert payload["score_mutation"] is False
    assert payload["selected_index_mutation"] is False
    assert payload["fallback_mutation"] is False
    assert payload["online_selector_feature"] is False
    assert payload["deployed_atom_schema_change"] is False
    for key in (
        "command_jerk_hinge_mps3",
        "rollout_jerk_hinge_mps3",
        "lateral_error_signed_pos_m",
        "lateral_error_signed_neg_m",
        "lane_projection_residual_hinge_m",
        "progress_retention_hinge_m",
    ):
        assert payload[key] >= 0.0


def test_material_generator_fails_closed_on_nonfinite_current_tick_inputs() -> None:
    candidates, lane, red = _straight_fixture()

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=np.nan,
        dt=0.1,
        config=_material_config(),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=np.nan,
        dt=0.1,
        config=_material_config(),
    )

    assert generated.shape == (0, candidates.shape[1], candidates.shape[2])
    assert meta == []
    assert diagnostics["construction_status"] == "fail_closed"
    assert diagnostics["failure_reason"] == "current_tick_scalar_invalid"
    assert diagnostics["fail_closed_partition"] == "current_tick_scalar_invalid"
    assert diagnostics["current_tick_features_only"] is True


def test_material_generator_candidate_budget_cap_is_deterministic() -> None:
    candidates, lane, red = _straight_fixture(red_start_m=20.0)

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=4.0,
        dt=0.1,
        config=_material_config(
            red_stop_margins_m=(1.0, 2.0),
            backup_stop_offsets_m=(0.0, 1.0),
            prefix_steps=(1, 3),
            bridge_steps=(4, 8),
            lane_projected_offset_scales=(1.0, 0.5, 0.0),
            max_remediation_candidates=3,
        ),
    )

    assert generated.shape == (3, candidates.shape[1], candidates.shape[2])
    assert len(meta) == 3
    assert [row["candidate_budget_cap"] for row in meta] == [3, 3, 3]
    assert [row["lateral_offset_scale"] for row in meta] == [0.0, 0.0, 0.0]
    assert [row["prefix_steps"] for row in meta] == [1, 1, 3]


def test_material_generator_validate_config_rejects_profile_policy_mismatch() -> None:
    with pytest.raises(ValueError, match="material_support_profile_required"):
        _validate_config(
            RouteTopologyCandidateConfig(
                generator_policy=GENERATOR_POLICY_MATERIAL_SUPPORT,
            )
        )
    with pytest.raises(ValueError, match="material_support_policy_required"):
        _validate_config(
            RouteTopologyCandidateConfig(
                default_off_remediation_profile=REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1,
            )
        )


def test_material_generator_effective_budgets_match_reviewed_support_floor() -> None:
    support = _effective_comfort_budgets(
        RouteTopologyCandidateConfig(
            default_off_remediation_profile=REMEDIATION_PROFILE_SUPPORT_V1
        )
    )
    material = _effective_comfort_budgets(_material_config())

    assert material["default_off_remediation_profile"] == (
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1
    )
    assert material["progress_loss_budgets_m"] == support["progress_loss_budgets_m"]
    assert material["smoothness_loss_budgets"] == support["smoothness_loss_budgets"]
    assert material["command_jerk_worse_budget_mps3"] == (
        support["command_jerk_worse_budget_mps3"]
    )
    assert material["command_lateral_worse_budget_mps2"] == (
        support["command_lateral_worse_budget_mps2"]
    )
    assert material["rollout_lateral_worse_budget_mps2"] == (
        support["rollout_lateral_worse_budget_mps2"]
    )
