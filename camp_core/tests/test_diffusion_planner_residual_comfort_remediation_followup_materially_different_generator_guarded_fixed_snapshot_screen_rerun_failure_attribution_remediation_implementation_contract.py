from __future__ import annotations

import numpy as np
import pytest

from scripts.integrations.analyze_diffusion_planner_route_topology_candidate_screen import (
    GENERATOR_POLICY_MATERIAL_SUPPORT,
    GENERATOR_POLICY_MATERIAL_SUPPORT_V2,
    REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1,
    REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2,
    REMEDIATION_PROFILE_OFF,
    RouteTopologyCandidateConfig,
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


def _v2_config(**overrides: object) -> RouteTopologyCandidateConfig:
    params: dict[str, object] = {
        "generator_policy": GENERATOR_POLICY_MATERIAL_SUPPORT_V2,
        "default_off_remediation_profile": REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2,
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


def test_v2_default_off_and_v1_behavior_unchanged() -> None:
    candidates, lane, red = _straight_fixture()

    default_generated, default_meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(),
    )
    v1_generated, v1_meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy=GENERATOR_POLICY_MATERIAL_SUPPORT,
            default_off_remediation_profile=REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1,
            red_stop_margins_m=(1.0,),
            backup_stop_offsets_m=(0.0,),
            prefix_steps=(1,),
            bridge_steps=(8,),
            lane_projected_offset_scales=(0.5, 0.0),
            max_remediation_candidates=3,
        ),
    )

    assert RouteTopologyCandidateConfig().default_off_remediation_profile == (
        REMEDIATION_PROFILE_OFF
    )
    assert {row["variant"] for row in default_meta} == {"lane_centerline_red_stop"}
    assert default_generated.shape[1:] == candidates.shape[1:]
    assert v1_generated.shape == (2, candidates.shape[1], candidates.shape[2])
    assert {row["profile"] for row in v1_meta} == {
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1
    }
    assert all("diagnostic_descriptor_payload_v2" not in row for row in v1_meta)
    assert all("lane_red_hard_feasibility_precheck" not in row for row in v1_meta)


def test_v2_requires_explicit_policy_profile_pair() -> None:
    candidates, lane, red = _straight_fixture()

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=RouteTopologyCandidateConfig(
            generator_policy=GENERATOR_POLICY_MATERIAL_SUPPORT_V2,
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
            generator_policy=GENERATOR_POLICY_MATERIAL_SUPPORT_V2,
        ),
    )

    assert generated.shape == (0, candidates.shape[1], candidates.shape[2])
    assert meta == []
    assert diagnostics["construction_status"] == "fail_closed"
    assert diagnostics["failure_reason"] == "material_support_profile_required"
    assert diagnostics["fail_closed_partition"] == "material_support_profile_required"

    with pytest.raises(ValueError, match="material_support_profile_required"):
        _validate_config(
            RouteTopologyCandidateConfig(
                generator_policy=GENERATOR_POLICY_MATERIAL_SUPPORT_V2,
            )
        )
    with pytest.raises(ValueError, match="material_support_policy_required"):
        _validate_config(
            RouteTopologyCandidateConfig(
                default_off_remediation_profile=REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2,
            )
        )


def test_v2_preserves_candidate0_and_dp_rows_while_appending_support() -> None:
    candidates, lane, red = _straight_fixture()
    original = candidates.copy()

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=_v2_config(),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=_v2_config(),
    )

    assert generated.shape == (2, candidates.shape[1], candidates.shape[2])
    assert len(meta) == 2
    assert {row["variant"] for row in meta} == {GENERATOR_POLICY_MATERIAL_SUPPORT_V2}
    assert all(row["profile"] == REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2 for row in meta)
    assert all(row["candidate0_preserved"] is True for row in meta)
    assert all(row["dp_rows_preserved"] is True for row in meta)
    assert all(row["append_after_existing_candidate_count"] == 2 for row in meta)
    assert all(row["source_candidate_index"] == 0 for row in meta)
    assert all(row["lane_red_hard_feasibility_precheck"] is True for row in meta)
    assert all(row["hard_feasibility_precheck_passed"] is True for row in meta)
    assert all(row["no_gate_relaxation"] is True for row in meta)
    assert all(row["jerk_limited_stop_and_creep_profiles"] is True for row in meta)
    np.testing.assert_allclose(candidates, original)
    np.testing.assert_allclose(generated[0, 0, :2], original[0, 0, :2])
    assert np.all(np.isfinite(generated))
    assert np.all(np.diff(generated[0, :, 0]) >= -1e-9)
    assert diagnostics["construction_status"] == "ready"
    assert diagnostics["failure_reason"] is None
    assert diagnostics["lane_red_hard_feasibility_precheck_passed"] is True
    assert diagnostics["lane_red_hard_feasible_windows"] == 1


def test_v2_hard_precheck_fails_closed_on_kinematic_margin() -> None:
    candidates, lane, red = _straight_fixture()

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=20.0,
        dt=0.1,
        config=_v2_config(),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=20.0,
        dt=0.1,
        config=_v2_config(),
    )

    assert generated.shape == (0, candidates.shape[1], candidates.shape[2])
    assert meta == []
    assert diagnostics["construction_status"] == "fail_closed"
    assert diagnostics["failure_reason"] == "kinematic_deceleration_margin_negative"
    assert diagnostics["fail_closed_partition"] == (
        "kinematic_deceleration_margin_negative"
    )
    assert diagnostics["lane_red_hard_feasibility_precheck_passed"] is False
    assert diagnostics["no_gate_relaxation"] is True


def test_v2_rejects_nonfinite_current_tick_inputs() -> None:
    candidates, lane, red = _straight_fixture()

    generated, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=np.nan,
        dt=0.1,
        config=_v2_config(),
    )
    diagnostics = route_topology_candidate_construction_diagnostics(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=np.nan,
        dt=0.1,
        config=_v2_config(),
    )

    assert generated.shape == (0, candidates.shape[1], candidates.shape[2])
    assert meta == []
    assert diagnostics["construction_status"] == "fail_closed"
    assert diagnostics["failure_reason"] == "current_tick_scalar_invalid"
    assert diagnostics["current_tick_features_only"] is True


def test_v2_descriptor_legality_and_affine_contract() -> None:
    candidates, lane, red = _straight_fixture()

    _, meta = build_route_topology_candidates(
        candidates,
        lane_centerline=lane,
        red_route_points=red,
        selected_index=0,
        current_speed_mps=3.0,
        dt=0.1,
        config=_v2_config(),
    )
    payload = meta[0]["remediation_descriptor_payload"]

    assert payload["payload_role"] == "report_only_current_tick_descriptor"
    assert payload["diagnostic_descriptor_payload_v2"] is True
    assert payload["descriptor_family"] == (
        "lane_red_hard_feasible_jerk_lateral_material_support"
    )
    assert payload["material_support_profile"] == REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2
    assert payload["current_tick_features_only"] is True
    assert payload["candidate_local"] is True
    assert payload["uses_outcome_labels"] is False
    assert payload["future_outcome_leakage"] is False
    assert payload["hard_feasibility_margin_hinges"] is True
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
        "hard_feasibility_red_ahead_margin_m",
        "hard_feasibility_stop_distance_margin_m",
        "hard_feasibility_forward_range_margin_m",
        "hard_feasibility_kinematic_deceleration_margin_mps2",
    ):
        assert payload[key] >= 0.0
