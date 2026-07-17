from __future__ import annotations

import numpy as np
import pytest
import torch

from camp_core.integrations.diffusion_planner import CAMPSelector
from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
)
from camp_core.integrations.diffusion_planner_v25_context import (
    CONTEXT_SCHEMA_VERSION,
    PHI_DIMENSION,
    RAW_FEATURE_COUNT,
    RAW_FEATURE_NAMES,
    build_v25_raw_context,
    complement_lift,
    context_weights,
    fit_train_context_scaler,
)
from camp_core.mapping_heads.linear_head import ComplementLiftedSimplexHead


def _lane(start_x: float, *, phase_index: int = 4, curve: float = 0.0) -> np.ndarray:
    lane = np.zeros((20, 33), dtype=np.float32)
    x = np.linspace(start_x, start_x + 19.0, 20)
    y = curve * (x - start_x) ** 2
    lane[:, 0] = x
    lane[:, 1] = y
    tangent = np.column_stack([np.ones(20), 2.0 * curve * (x - start_x)])
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    lane[:, 2:4] = tangent
    lane[:, 4:6] = np.column_stack([-2.0 * tangent[:, 1], 2.0 * tangent[:, 0]])
    lane[:, 6:8] = np.column_stack([2.0 * tangent[:, 1], -2.0 * tangent[:, 0]])
    lane[:, 8 + phase_index] = 1.0
    lane[:, 13] = 1.0
    lane[:, 23] = 1.0
    return lane


def _causal_input() -> dict[str, np.ndarray]:
    data = {
        key: np.zeros(shape, dtype=dtype)
        for key, (shape, dtype) in CAUSAL_DP_INPUT_SCHEMA.items()
    }
    data["version"] = np.array(1, dtype=np.int64)
    data["ego_current_state"] = np.array(
        [0.0, 0.0, 1.0, 0.0, 8.0, 0.0, -1.5, 0.0, 0.1, 0.2],
        dtype=np.float32,
    )
    route = np.zeros((25, 20, 33), dtype=np.float32)
    route[0] = _lane(0.0, phase_index=2, curve=0.001)
    route[1] = _lane(19.0, phase_index=4, curve=0.001)
    data["route_lanes"] = route
    data["lanes"][:2] = route[:2]
    data["route_lanes_has_speed_limit"][:2] = True
    data["route_lanes_speed_limit"][:2, 0] = [12.0, 15.0]
    data["lanes_has_speed_limit"][:2] = True
    data["lanes_speed_limit"][:2, 0] = [12.0, 15.0]
    neighbor = data["neighbor_agents_past"]
    neighbor[0, -1, :8] = [10.0, 1.5, 1.0, 0.0, 4.0, 0.0, 1.8, 4.5]
    neighbor[0, -1, 8] = 1.0
    neighbor[1, -1, :8] = [18.0, -2.0, 1.0, 0.0, 10.0, 0.0, 1.8, 4.5]
    neighbor[1, -1, 8] = 1.0
    return data


def _candidates() -> np.ndarray:
    candidates = np.zeros((8, 80, 4), dtype=np.float64)
    for index in range(8):
        candidates[index, :, 0] = np.linspace(0.1, 30.0 + index, 80)
        candidates[index, :, 1] = 0.05 * index * np.sin(np.linspace(0.0, np.pi, 80))
        candidates[index, :, 2] = 1.0
    return candidates


def test_raw_context_is_exact_finite_current_request_contract() -> None:
    causal = _causal_input()
    candidates = _candidates()
    before = candidates.copy()

    record = build_v25_raw_context(
        causal_input=causal,
        candidates=candidates,
        source_valid_mask=np.array([True] * 7 + [False]),
        signal_phase_remaining_s=4.5,
    )

    assert record.raw.shape == (RAW_FEATURE_COUNT,)
    assert len(RAW_FEATURE_NAMES) == 26
    assert np.isfinite(record.raw).all()
    np.testing.assert_array_equal(candidates, before)
    values = record.as_dict()
    assert values["ego_speed_mps"] == 8.0
    assert values["ego_lateral_acceleration_mps2"] == pytest.approx(1.6)
    assert values["traffic_phase_red"] == 1.0
    assert values["traffic_signal_phase_remaining_s"] == 4.5
    assert values["neighbor_count"] == 2.0
    assert values["neighbor_closing_speed_mps"] > 0.0
    assert values["candidate_source_valid_fraction"] == 0.875
    assert all(record.source_complete)


def test_train_only_scaler_complement_lift_and_universal_simplex() -> None:
    raw = np.vstack(
        [
            np.linspace(-2.0, 3.0, RAW_FEATURE_COUNT),
            np.linspace(-1.0, 4.0, RAW_FEATURE_COUNT),
            np.linspace(0.0, 5.0, RAW_FEATURE_COUNT),
        ]
    )
    scaler = fit_train_context_scaler(raw)
    phi = scaler.lift(raw)
    assert phi.shape == (3, PHI_DIMENSION)
    assert np.all(phi >= 0.0)
    np.testing.assert_allclose(phi.sum(axis=1), 1.0, atol=1e-12)
    np.testing.assert_allclose(phi[:, 1::2] + phi[:, 2::2], 1.0 / 27.0)

    theta = np.zeros((3, PHI_DIMENSION), dtype=np.float64)
    theta[0, ::3] = 1.0
    theta[1, 1::3] = 1.0
    theta[2, 2::3] = 1.0
    weights = context_weights(theta, phi)
    assert weights.shape == (3, 3)
    assert np.all(weights >= 0.0)
    np.testing.assert_allclose(weights.sum(axis=1), 1.0)


def test_strict_head_and_selector_use_no_softmax_or_runtime_projection() -> None:
    theta = np.full((2, PHI_DIMENSION), 0.5, dtype=np.float64)
    phi = complement_lift(np.linspace(0.0, 1.0, RAW_FEATURE_COUNT))
    head = ComplementLiftedSimplexHead(num_atoms=2, theta=theta)
    torch_weights = head(torch.as_tensor(phi[None], dtype=torch.float64))
    np.testing.assert_allclose(torch_weights.detach().numpy(), [[0.5, 0.5]])

    q05 = np.zeros(RAW_FEATURE_COUNT)
    q95 = np.ones(RAW_FEATURE_COUNT)
    selector = CAMPSelector(
        atom_scales=np.ones(2),
        theta=theta,
        context_q05=q05,
        context_q95=q95,
        context_feature_names=RAW_FEATURE_NAMES,
        context_schema_version=CONTEXT_SCHEMA_VERSION,
        mode="context_simplex",
    )
    np.testing.assert_allclose(
        selector.weights_for(raw_context=np.linspace(0.0, 1.0, RAW_FEATURE_COUNT)),
        [0.5, 0.5],
    )
    with pytest.raises(ValueError, match="rejects scene_embedding"):
        selector.weights_for(np.zeros(RAW_FEATURE_COUNT))
    with pytest.raises(ValueError, match="column must sum to one"):
        CAMPSelector(
            atom_scales=np.ones(2),
            theta=np.ones((2, PHI_DIMENSION)),
            context_q05=q05,
            context_q95=q95,
            context_feature_names=RAW_FEATURE_NAMES,
            mode="context_simplex",
        )


def test_train_only_bt_and_strict_cvar_master_converge() -> None:
    pytest.importorskip("cvxpy")
    from camp_core.outer_master.parametric_cvxpy_master import (
        V25ParametricMasterConfig,
        solve_v25_parametric_cutting_plane,
        v25_bradley_terry_warmup,
    )

    record_count = 6
    atoms = np.zeros((record_count, 3, 2), dtype=np.float64)
    atoms[:, 1, 0] = 1.0
    atoms[:, 2, 1] = 1.0
    raw = np.linspace(0.0, 1.0, record_count * RAW_FEATURE_COUNT).reshape(
        record_count, RAW_FEATURE_COUNT
    )
    phi = complement_lift(raw)
    oracle = np.zeros(record_count, dtype=np.int64)
    feasible = np.ones((record_count, 3), dtype=bool)
    margins = np.zeros((record_count, 3), dtype=np.float64)
    margins[:, 1:] = 0.2

    warmup = v25_bradley_terry_warmup(
        atoms,
        phi,
        oracle,
        feasible,
        iterations=20,
        max_pairs=128,
    )
    assert warmup.label_contract == "train_only_causal_oracle_pair_preferences"
    assert warmup.optimizer_contract.endswith("no_softmax")
    assert warmup.final_loss <= warmup.initial_loss + 1e-10
    np.testing.assert_allclose(warmup.theta.sum(axis=0), 1.0, atol=1e-10)

    result = solve_v25_parametric_cutting_plane(
        atoms,
        phi,
        oracle,
        margins,
        feasible,
        config=V25ParametricMasterConfig(
            max_iter=5,
            tolerance=1e-6,
            bt_iterations=20,
            bt_max_pairs=128,
        ),
    )
    assert result.converged
    assert result.final_master_gap <= 1e-6
    assert result.solver_status == "optimal"
    assert result.solver_name == "CLARABEL"
    assert result.iterations <= 5
    np.testing.assert_allclose(result.theta.sum(axis=0), 1.0, atol=1e-8)
    np.testing.assert_allclose(result.train_weights.sum(axis=1), 1.0, atol=1e-8)
    assert np.all(result.theta >= -1e-9)
    assert sum(result.cuts_per_scene) >= record_count


def test_v25_master_rejects_non_clarabel_or_non_simplex_phi() -> None:
    pytest.importorskip("cvxpy")
    from camp_core.outer_master.parametric_cvxpy_master import (
        V25ParametricMasterConfig,
    )

    with pytest.raises(ValueError, match="strict CLARABEL"):
        V25ParametricMasterConfig(solver="SCS").validate()
    with pytest.raises(ValueError, match=r"\[0,1\]"):
        complement_lift(np.full(RAW_FEATURE_COUNT, 1.1))
