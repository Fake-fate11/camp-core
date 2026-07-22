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
    masked_complement_lift,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
    canonical_json_sha256,
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


def _mapped_causal_signal(*, phase: str, stop_x_m: float) -> dict:
    stop = [[stop_x_m, -2.0], [stop_x_m, 2.0]]
    stop_sha = canonical_json_sha256(stop)
    receipt = {
        "source_chain_sha256": "1" * 64,
        "stop_line_geometry_sha256": stop_sha,
        "route_geometry_sha256": "2" * 64,
        "regulatory_element_id": 101,
        "stop_line_id": 401,
        "current_phase": phase,
        "decision_timestamp_s": 0.0,
    }
    return {
        "schema_version": "camp_dp_v25_causal_signal_atom_input_v2",
        "source_state": "available",
        "source_valid": True,
        "applicable": phase == "red",
        "current_phase": phase,
        "decision_time_s": 0.0,
        "ego_position_world_m": [0.0, 0.0],
        "ego_heading_rad": 0.0,
        "regulatory_element_id": 101,
        "stop_line_id": 401,
        "stop_line_geometry_world_m": stop,
        "stop_line_geometry_ego_m": stop,
        "stop_line_geometry_sha256": stop_sha,
        "route_tangent_world": [1.0, 0.0],
        "route_tangent_ego": [1.0, 0.0],
        "route_geometry_sha256": "2" * 64,
        "route_arc_m": 10.0,
        "source_chain_sha256": "1" * 64,
        "runtime_receipt": receipt,
        "runtime_receipt_sha256": canonical_json_sha256(receipt),
    }


def test_map_only_same_tick_signal_fills_context_without_future_schedule() -> None:
    causal = _causal_input()
    causal["route_lanes"][:, :, 8:12] = 0.0
    record = build_v25_raw_context(
        causal_input=causal,
        candidates=_candidates(),
        source_valid_mask=np.ones(8, dtype=bool),
        causal_signal_atom_input=_mapped_causal_signal(
            phase="yellow", stop_x_m=12.5
        ),
    )
    values = record.as_dict()
    assert values["traffic_phase_yellow"] == 1.0
    assert values["traffic_phase_unknown"] == 0.0
    assert values["traffic_signal_distance_m"] == 12.5
    for name in (
        "traffic_phase_red",
        "traffic_phase_yellow",
        "traffic_phase_green",
        "traffic_phase_unknown",
        "traffic_signal_distance_m",
    ):
        assert record.source_complete[RAW_FEATURE_NAMES.index(name)] is True
    assert record.source_receipt == {
        "mode": "no_v2i",
        "phase_remaining_available": False,
        "regulatory_signal_mapped": True,
    }


def test_certified_current_signal_must_agree_with_visible_route_phase() -> None:
    with pytest.raises(ValueError, match="phases conflict"):
        build_v25_raw_context(
            causal_input=_causal_input(),
            candidates=_candidates(),
            source_valid_mask=np.ones(8, dtype=bool),
            causal_signal_atom_input=_mapped_causal_signal(
                phase="yellow", stop_x_m=12.5
            ),
        )


def test_raw_context_is_exact_finite_current_request_contract() -> None:
    causal = _causal_input()
    candidates = _candidates()
    before = candidates.copy()

    record = build_v25_raw_context(
        causal_input=causal,
        candidates=candidates,
        source_valid_mask=np.array([True] * 7 + [False]),
        v2i_signal_timing={
            "source_id": "unit-test-v2i",
            "phase_remaining_s": 4.5,
            "decision_timestamp_s": 10.0,
            "source_timestamp_s": 9.9,
            "maximum_age_s": 0.5,
            "valid": True,
        },
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


@pytest.mark.parametrize(
    "source_valid_mask",
    [
        np.ones(8, dtype=np.int64),
        np.asarray(["true"] * 8),
        np.zeros(8, dtype=np.bool_),
    ],
)
def test_raw_context_rejects_coerced_or_empty_source_valid_mask(
    source_valid_mask: np.ndarray,
) -> None:
    with pytest.raises(ValueError, match="source_valid_mask"):
        build_v25_raw_context(
            causal_input=_causal_input(),
            candidates=_candidates(),
            source_valid_mask=source_valid_mask,
        )


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("phase_remaining_s", "4.5"),
        ("decision_timestamp_s", True),
        ("source_timestamp_s", "9.9"),
        ("maximum_age_s", False),
    ],
)
def test_v2i_timing_rejects_numeric_type_smuggling(
    field: str,
    bad_value: object,
) -> None:
    timing = {
        "source_id": "unit-test-v2i",
        "phase_remaining_s": 4.5,
        "decision_timestamp_s": 10.0,
        "source_timestamp_s": 9.9,
        "maximum_age_s": 0.5,
        "valid": True,
    }
    timing[field] = bad_value
    with pytest.raises(ValueError, match="native numbers"):
        build_v25_raw_context(
            causal_input=_causal_input(),
            candidates=_candidates(),
            source_valid_mask=np.ones(8, dtype=np.bool_),
            v2i_signal_timing=timing,
        )


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


def test_no_v2i_masked_lift_removes_unavailable_feature_pair() -> None:
    raw = np.vstack(
        [
            np.linspace(0.0, 1.0, RAW_FEATURE_COUNT),
            np.linspace(1.0, 2.0, RAW_FEATURE_COUNT),
            np.linspace(2.0, 3.0, RAW_FEATURE_COUNT),
        ]
    )
    available = np.ones(raw.shape, dtype=np.bool_)
    timing_index = RAW_FEATURE_NAMES.index("traffic_signal_phase_remaining_s")
    available[:, timing_index] = False
    raw[:, timing_index] = [0.0, 999.0, -999.0]
    scaler = fit_train_context_scaler(
        raw,
        source_complete=available,
        record_weights=np.asarray([0.6, 0.3, 0.1], dtype=np.float64),
    )
    phi = scaler.lift(raw, source_complete=available)
    pair = phi[:, [1 + 2 * timing_index, 2 + 2 * timing_index]]
    np.testing.assert_array_equal(pair, np.zeros((3, 2), dtype=np.float64))
    np.testing.assert_allclose(phi.sum(axis=1), 1.0, rtol=0.0, atol=1e-12)
    assert scaler.q05[timing_index] == 0.0
    assert scaler.q95[timing_index] == 1.0


def test_masked_lift_matches_original_when_every_source_is_available() -> None:
    unit = np.linspace(0.0, 1.0, RAW_FEATURE_COUNT)
    np.testing.assert_array_equal(
        masked_complement_lift(unit, np.ones(RAW_FEATURE_COUNT, dtype=np.bool_)),
        complement_lift(unit),
    )
    with pytest.raises(ValueError, match="native booleans"):
        masked_complement_lift(unit, np.ones(RAW_FEATURE_COUNT, dtype=np.int64))


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
        selector.weights_for(
            raw_context=np.linspace(0.0, 1.0, RAW_FEATURE_COUNT),
            context_source_complete=np.ones(RAW_FEATURE_COUNT, dtype=np.bool_),
        ),
        [0.5, 0.5],
    )
    with pytest.raises(ValueError, match="context_source_complete"):
        selector.weights_for(raw_context=np.linspace(0.0, 1.0, RAW_FEATURE_COUNT))
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
    source_valid = np.ones((record_count, 3), dtype=bool)
    margins = np.zeros((record_count, 3), dtype=np.float64)
    margins[:, 1:] = 0.2

    warmup = v25_bradley_terry_warmup(
        atoms,
        phi,
        oracle,
        source_valid,
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
        source_valid,
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


def test_v25_bt_uses_record_mass_and_divides_it_across_pairs() -> None:
    pytest.importorskip("cvxpy")
    from camp_core.integrations.diffusion_planner_v25_context import context_weights
    from camp_core.outer_master.parametric_cvxpy_master import (
        v25_bradley_terry_warmup,
    )

    atoms = np.zeros((2, 2, 2), dtype=np.float64)
    atoms[0, 1, 0] = 1.0
    atoms[1, 1, 1] = 1.0
    phi = complement_lift(np.zeros((2, RAW_FEATURE_COUNT), dtype=np.float64))
    oracle = np.zeros(2, dtype=np.int64)
    source_valid = np.ones((2, 2), dtype=bool)
    weighted = v25_bradley_terry_warmup(
        atoms,
        phi,
        oracle,
        source_valid,
        record_weights=np.asarray([0.9, 0.1], dtype=np.float64),
        iterations=80,
        max_pairs=128,
    )
    weights = context_weights(weighted.theta, phi)
    assert np.all(weights[:, 0] > weights[:, 1])
    np.testing.assert_allclose(weighted.theta.sum(axis=0), 1.0, atol=1e-10)


def test_v25_master_uniform_record_mass_matches_default() -> None:
    pytest.importorskip("cvxpy")
    from camp_core.outer_master.parametric_cvxpy_master import (
        V25ParametricMasterConfig,
        solve_v25_parametric_cutting_plane,
    )

    records = 4
    atoms = np.zeros((records, 3, 2), dtype=np.float64)
    atoms[:, 1, 0] = np.linspace(0.5, 1.0, records)
    atoms[:, 2, 1] = np.linspace(1.0, 0.5, records)
    phi = complement_lift(np.zeros((records, RAW_FEATURE_COUNT), dtype=np.float64))
    oracle = np.zeros(records, dtype=np.int64)
    source_valid = np.ones((records, 3), dtype=bool)
    margins = np.zeros((records, 3), dtype=np.float64)
    margins[:, 1:] = 0.1
    config = V25ParametricMasterConfig(
        alpha=0.5,
        max_iter=5,
        tolerance=1e-6,
        bt_iterations=20,
        bt_max_pairs=128,
    )
    default = solve_v25_parametric_cutting_plane(
        atoms, phi, oracle, margins, source_valid, config=config
    )
    explicit = solve_v25_parametric_cutting_plane(
        atoms,
        phi,
        oracle,
        margins,
        source_valid,
        record_weights=np.full(records, 1.0 / records, dtype=np.float64),
        config=config,
    )
    np.testing.assert_allclose(default.theta, explicit.theta, rtol=0.0, atol=1e-9)
    assert default.final_master_gap == pytest.approx(explicit.final_master_gap, abs=1e-12)


def test_weighted_empirical_cvar_matches_direct_eta_enumeration() -> None:
    from camp_core.outer_master.parametric_cvxpy_master import (
        _weighted_empirical_cvar,
    )

    losses = np.asarray([0.0, 0.2, 0.2, 0.7, 1.4], dtype=np.float64)
    weights = np.asarray([0.05, 0.15, 0.20, 0.25, 0.35], dtype=np.float64)
    for alpha in (0.0, 0.5, 0.9):
        candidates = np.unique(np.concatenate((np.asarray([0.0]), losses)))
        direct = min(
            float(
                eta
                + np.sum(weights * np.maximum(losses - eta, 0.0))
                / (1.0 - alpha)
            )
            for eta in candidates
        )
        assert _weighted_empirical_cvar(losses, weights, alpha) == pytest.approx(
            direct, abs=1e-15
        )


@pytest.mark.parametrize(
    "record_weights",
    [
        np.asarray([True, False]),
        np.asarray([1.0, 0.0]),
        np.asarray([1.0, np.nan]),
        np.asarray([1.0]),
    ],
)
def test_v25_bt_rejects_invalid_record_mass(record_weights: np.ndarray) -> None:
    pytest.importorskip("cvxpy")
    from camp_core.outer_master.parametric_cvxpy_master import (
        v25_bradley_terry_warmup,
    )

    atoms = np.zeros((2, 2, 2), dtype=np.float64)
    atoms[:, 1, 0] = 1.0
    phi = complement_lift(np.zeros((2, RAW_FEATURE_COUNT), dtype=np.float64))
    with pytest.raises(ValueError, match="record_weights"):
        v25_bradley_terry_warmup(
            atoms,
            phi,
            np.zeros(2, dtype=np.int64),
            np.ones((2, 2), dtype=bool),
            record_weights=record_weights,
        )


def test_v25_master_rejects_non_clarabel_or_non_simplex_phi() -> None:
    pytest.importorskip("cvxpy")
    from camp_core.outer_master.parametric_cvxpy_master import (
        V25ParametricMasterConfig,
    )

    with pytest.raises(ValueError, match="strict CLARABEL"):
        V25ParametricMasterConfig(solver="SCS").validate()
    with pytest.raises(ValueError, match=r"\[0,1\]"):
        complement_lift(np.full(RAW_FEATURE_COUNT, 1.1))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("source_valid", np.ones((2, 2), dtype=np.int64), "native booleans"),
        ("oracle", np.zeros(2, dtype=np.float64), "native integers"),
        ("margins", np.zeros((2, 2), dtype=np.bool_), "native numeric"),
    ],
)
def test_v25_master_rejects_type_smuggling(
    field: str, value: np.ndarray, message: str
) -> None:
    pytest.importorskip("cvxpy")
    from camp_core.outer_master.parametric_cvxpy_master import (
        V25ParametricMasterConfig,
        solve_v25_parametric_cutting_plane,
    )

    atoms = np.zeros((2, 2, 2), dtype=np.float64)
    atoms[:, 1, 0] = 1.0
    phi = complement_lift(np.zeros((2, RAW_FEATURE_COUNT), dtype=np.float64))
    oracle = np.zeros(2, dtype=np.int64)
    margins = np.zeros((2, 2), dtype=np.float64)
    source_valid = np.ones((2, 2), dtype=np.bool_)
    arguments = {
        "oracle_indices": oracle,
        "margins": margins,
        "source_valid_mask": source_valid,
    }
    arguments[
        {
            "source_valid": "source_valid_mask",
            "oracle": "oracle_indices",
            "margins": "margins",
        }[field]
    ] = value
    with pytest.raises(ValueError, match=message):
        solve_v25_parametric_cutting_plane(
            atoms,
            phi,
            arguments["oracle_indices"],
            arguments["margins"],
            arguments["source_valid_mask"],
            config=V25ParametricMasterConfig(max_iter=1, bt_iterations=1),
        )


def test_context_scaler_rejects_record_weight_overflow() -> None:
    raw = np.vstack(
        [
            np.zeros(RAW_FEATURE_COUNT, dtype=np.float64),
            np.ones(RAW_FEATURE_COUNT, dtype=np.float64),
        ]
    )
    with pytest.raises(ValueError, match="finite positive total"):
        fit_train_context_scaler(
            raw,
            record_weights=np.asarray([np.finfo(np.float64).max] * 2),
        )
