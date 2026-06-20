from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pytest

REPLAY_SCRIPT = Path(__file__).resolve().parents[2] / (
    "scripts/integrations/run_diffusion_planner_camp_replay.py"
)

from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (
    PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS,
    PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
    build_progress_lane_hard_context_logging_payload,
)


def _route() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [2.0, 0.0],
            [3.0, 1.0],
            [4.0, 2.0],
        ],
        dtype=np.float64,
    )


def _candidates() -> np.ndarray:
    return np.asarray(
        [
            [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 1.0], [4.0, 2.0]],
            [[0.0, 0.0], [1.0, 1.4], [2.0, 2.0], [3.0, 2.5], [4.0, 3.0]],
            [[0.0, 0.0], [1.0, 0.1], [2.0, 0.2], [3.0, 1.0], [4.0, 2.0]],
        ],
        dtype=np.float64,
    )


def test_progress_lane_hard_context_payload_schema_shapes_and_metadata() -> None:
    payload = build_progress_lane_hard_context_logging_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        support_steps=5,
        dt_s=0.1,
        corridor_half_width_m=1.0,
        corridor_safety_margin_m=0.25,
    )

    assert payload["schema_version"] == PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION
    assert payload["enabled"] is True
    assert payload["default_off"] is True
    assert payload["selection_effect"] is False
    assert payload["future_outcome_leakage"] is False
    assert payload["closed_loop_outcome_fields_read"] is False
    assert payload["classical_benders_claim"] is False
    assert "score_k(w)=a_k^T w" in payload["math_boundary"]
    assert payload["candidate_count"] == 3
    assert payload["horizons"] == {"support_steps": 5, "dt_s": 0.1}
    assert set(payload["field_shapes"]) == set(PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES)
    assert payload["field_shapes"]["route_curvature_context_abs_radpm"] == [4]
    assert payload["field_shapes"]["candidate_lateral_error_rate_profile_mps"] == [3, 4]
    assert payload["field_shapes"]["candidate_speed_profile_mps"] == [3, 4]
    assert payload["field_shapes"]["candidate_route_progress_delta_profile_m"] == [3, 4]
    assert payload["field_shapes"]["candidate_route_corridor_margin_profile_m"] == [3, 5]
    assert payload["field_shapes"]["candidate_route_heading_error_profile_rad"] == [3, 5]
    assert all(payload["finite_checks"].values())
    assert set(payload["latency_ms"]) == set(PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS)
    assert all(float(value) >= 0.0 for value in payload["latency_ms"].values())
    assert payload["progress_lane_hard_context_atom_names"] == list(
        PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES
    )
    assert np.asarray(payload["progress_lane_hard_context_atoms"]).shape == (
        3,
        len(PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES),
    )


def test_progress_lane_hard_context_atoms_are_nonnegative_fixed_coefficients() -> None:
    payload = build_progress_lane_hard_context_logging_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        support_steps=5,
        dt_s=0.1,
        corridor_half_width_m=1.0,
        lateral_rate_margin_mps=0.2,
        corridor_safety_margin_m=0.25,
        heading_margin_rad=0.2,
        progress_lateral_rate_gain=0.5,
    )
    atoms = np.asarray(payload["progress_lane_hard_context_atoms"], dtype=np.float64)
    atom_index = {
        name: idx
        for idx, name in enumerate(payload["progress_lane_hard_context_atom_names"])
    }

    assert np.all(atoms >= 0.0)
    np.testing.assert_allclose(atoms[0], np.zeros(atoms.shape[1]), atol=1e-12)
    assert atoms[1, atom_index["curvature_conditioned_lateral_rate_excess_v1"]] > 0.0
    assert atoms[1, atom_index["corridor_margin_exhaustion_v1"]] > 0.0
    assert atoms[1, atom_index["heading_curvature_residual_v1"]] > 0.0
    assert atoms[1, atom_index["lane_progress_coherence_excess_v1"]] > 0.0
    assert (
        atoms[2, atom_index["corridor_margin_exhaustion_v1"]]
        <= atoms[1, atom_index["corridor_margin_exhaustion_v1"]]
    )


def test_progress_lane_hard_context_payload_accepts_width_profile() -> None:
    payload = build_progress_lane_hard_context_logging_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        support_steps=5,
        corridor_half_width_m=np.asarray([1.0, 1.1, 1.2, 1.3, 1.4], dtype=np.float64),
    )

    margin = np.asarray(
        payload["candidate_route_corridor_margin_profile_m"],
        dtype=np.float64,
    )
    assert margin.shape == (3, 5)
    assert np.all(np.isfinite(margin))


def test_progress_lane_hard_context_payload_does_not_accept_outcome_inputs() -> None:
    signature = inspect.signature(build_progress_lane_hard_context_logging_payload)

    assert "outcome" not in str(signature).lower()
    assert "closed_loop" not in str(signature).lower()
    assert list(signature.parameters) == [
        "candidates",
        "route_centerline_ego",
        "support_steps",
        "dt_s",
        "corridor_half_width_m",
        "curvature_lateral_rate_gain",
        "lateral_rate_margin_mps",
        "corridor_safety_margin_m",
        "heading_curvature_gain",
        "heading_margin_rad",
        "progress_lateral_rate_gain",
        "progress_curvature_gain",
    ]


def test_progress_lane_hard_context_timing_does_not_change_logged_values() -> None:
    first = build_progress_lane_hard_context_logging_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        support_steps=5,
        corridor_half_width_m=1.0,
    )
    second = build_progress_lane_hard_context_logging_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        support_steps=5,
        corridor_half_width_m=1.0,
    )

    assert set(first["latency_ms"]) == set(PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS)
    assert set(second["latency_ms"]) == set(PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS)
    first_without_latency = dict(first)
    second_without_latency = dict(second)
    first_without_latency.pop("latency_ms")
    second_without_latency.pop("latency_ms")
    assert first_without_latency == second_without_latency


def test_progress_lane_hard_context_payload_validates_inputs() -> None:
    with pytest.raises(ValueError, match="candidates must have shape"):
        build_progress_lane_hard_context_logging_payload(
            candidates=np.zeros((5, 2), dtype=np.float64),
            route_centerline_ego=_route(),
            support_steps=5,
        )
    with pytest.raises(ValueError, match="route_centerline_ego"):
        build_progress_lane_hard_context_logging_payload(
            candidates=_candidates(),
            route_centerline_ego=np.zeros((1, 2), dtype=np.float64),
            support_steps=5,
        )
    with pytest.raises(ValueError, match="dt_s"):
        build_progress_lane_hard_context_logging_payload(
            candidates=_candidates(),
            route_centerline_ego=_route(),
            support_steps=5,
            dt_s=0.0,
        )
    with pytest.raises(ValueError, match="corridor_half_width_m"):
        build_progress_lane_hard_context_logging_payload(
            candidates=_candidates(),
            route_centerline_ego=_route(),
            support_steps=5,
            corridor_half_width_m=0.0,
        )
    with pytest.raises(ValueError, match="heading_margin_rad"):
        build_progress_lane_hard_context_logging_payload(
            candidates=_candidates(),
            route_centerline_ego=_route(),
            support_steps=5,
            heading_margin_rad=-1.0,
        )


def test_progress_lane_hard_context_replay_wiring_is_default_off_and_neutral() -> None:
    source = REPLAY_SCRIPT.read_text(encoding="utf-8")

    assert "--camp_progress_lane_hard_context_logging" in source
    assert "action=\"store_true\"" in source
    assert (
        "build_progress_lane_hard_context_logging_payload("
        in source
    )
    assert (
        "\"progress_lane_hard_context_logging\": ("
        in source
    )
    assert "\"camp_progress_lane_hard_context_logging\"" in source
    assert "**progress_lane_hard_context_latency_ms" in source
    assert "\"selection_effect\": False" in source
    assert "\"future_outcome_leakage\": False" in source
    assert "\"closed_loop_outcome_fields_read\": False" in source
    assert "\"online_selector_change\": False" in source
    assert "\"classical_benders_claim\": False" in source
    assert (
        "progress_lane_hard_context_logging=bool("
        in source
    )
    assert (
        "or progress_lane_hard_context_logging"
        in source
    )
