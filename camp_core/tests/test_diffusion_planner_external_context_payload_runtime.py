from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_external_context_payload import (
    EXTERNAL_CONTEXT_PAYLOAD_ATOM_CANDIDATE_NAMES,
    EXTERNAL_CONTEXT_PAYLOAD_FIELD_NAMES,
    EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS,
    EXTERNAL_CONTEXT_PAYLOAD_SCHEMA_VERSION,
    build_external_context_payload,
)


REPLAY_SCRIPT = Path(__file__).resolve().parents[2] / (
    "scripts/integrations/run_diffusion_planner_camp_replay.py"
)


def _candidates() -> np.ndarray:
    return np.asarray(
        [
            [[0.0, 0.0, 1.0, 0.0], [1.0, 0.0, 1.0, 0.0], [2.0, 0.0, 1.0, 0.0]],
            [[0.0, 0.0, 1.0, 0.0], [2.0, 0.0, 1.0, 0.0], [4.0, 0.0, 1.0, 0.0]],
        ],
        dtype=np.float64,
    )


def _route() -> np.ndarray:
    return np.asarray(
        [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0]],
        dtype=np.float64,
    )


def test_external_context_payload_absent_context_fails_closed() -> None:
    payload = build_external_context_payload(
        candidates=_candidates(),
        route_centerline_ego=None,
        support_steps=3,
        dt_s=1.0,
    )

    assert payload["schema_version"] == EXTERNAL_CONTEXT_PAYLOAD_SCHEMA_VERSION
    assert payload["enabled"] is True
    assert payload["default_off"] is True
    assert payload["selection_effect"] is False
    assert payload["future_outcome_leakage"] is False
    assert payload["closed_loop_outcome_fields_read"] is False
    assert payload["online_selector_change"] is False
    assert payload["deployed_atom_vector_change"] is False
    assert payload["classical_benders_claim"] is False
    assert payload["available"] is False
    assert payload["finite_checks"]["payload_valid"] is False
    assert payload["candidate_count"] == 2
    for field_name in EXTERNAL_CONTEXT_PAYLOAD_FIELD_NAMES:
        assert payload[field_name] is None
        assert payload["field_shapes"][field_name] is None
    assert set(payload["latency_ms"]) == set(EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS)
    assert all(float(value) >= 0.0 for value in payload["latency_ms"].values())


def test_external_context_payload_route_speed_context() -> None:
    payload = build_external_context_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        route_speed_limit_mps=1.5,
        route_has_speed_limit=True,
        support_steps=3,
        dt_s=1.0,
    )

    assert payload["available"] is True
    assert payload["route_speed_context_available"] is True
    assert payload["traffic_signal_context_available"] is False
    assert payload["availability_reason"] is None
    assert payload["candidate_route_speed_limit_min_mps"] == [1.5, 1.5]
    assert payload["candidate_speed_limit_excess_integral_mps"] == [0.0, 1.0]
    assert payload["candidate_speed_limit_available_fraction"] == [1.0, 1.0]
    assert payload["field_shapes"]["candidate_speed_limit_excess_integral_mps"] == [2]
    assert all(payload["finite_checks"].values())
    assert payload["atom_candidate_names"] == list(
        EXTERNAL_CONTEXT_PAYLOAD_ATOM_CANDIDATE_NAMES
    )
    assert "score_k(w)=a_k^T w" in payload["math_boundary"]


def test_external_context_payload_traffic_signal_context() -> None:
    payload = build_external_context_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        signal_context={
            "signal_s_m": 1.5,
            "current_phase": "red",
            "phase_remaining_s": 3.0,
            "blocked_phases": ["red"],
        },
        support_steps=3,
        dt_s=1.0,
    )

    assert payload["available"] is True
    assert payload["traffic_signal_context_available"] is True
    assert payload["route_speed_context_available"] is False
    assert payload["candidate_first_signal_arrival_time_s"] == [2.0, 1.0]
    assert payload["candidate_signal_phase_change_margin_s"] == [1.0, 2.0]
    assert payload["candidate_right_of_way_blocked_indicator"] == [1.0, 1.0]
    assert payload["field_shapes"]["candidate_first_signal_arrival_time_s"] == [2]
    assert all(payload["finite_checks"].values())


def test_external_context_payload_invalid_signal_context_fails_closed() -> None:
    payload = build_external_context_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        signal_context={
            "signal_s_m": 1.5,
            "current_phase": "unknown",
        },
        route_speed_limit_mps=1.5,
        route_has_speed_limit=True,
        support_steps=3,
        dt_s=1.0,
    )

    assert payload["available"] is False
    assert payload["finite_checks"]["payload_valid"] is False
    assert payload["finite_checks"]["traffic_signal_context_valid_or_absent"] is False
    assert "derived_external_context_invalid" in payload["availability_reason"]


def test_external_context_payload_does_not_accept_outcome_inputs() -> None:
    signature = inspect.signature(build_external_context_payload)

    assert "outcome" not in str(signature).lower()
    assert "closed_loop" not in str(signature).lower()
    assert list(signature.parameters) == [
        "candidates",
        "route_centerline_ego",
        "support_steps",
        "dt_s",
        "signal_context",
        "route_speed_limit_mps",
        "route_has_speed_limit",
    ]


def test_replay_script_wires_external_context_payload_default_off() -> None:
    source = REPLAY_SCRIPT.read_text(encoding="utf-8")

    assert "--camp_external_context_payload_logging" in source
    assert "build_external_context_payload(" in source
    assert "external_context_payload_logging=bool(" in source
    assert "args.camp_external_context_payload_logging" in source
    assert '"external_context_payload_logging": (' in source
    assert "external_context_payload_logging_payload" in source
    assert '"camp_external_context_payload_logging": (' in source
    assert "camp_external_context_payload_logging" in source
    assert "validation[\"camp_external_context_payload_logging\"]" in source
    assert "**external_context_payload_latency_ms" in source
