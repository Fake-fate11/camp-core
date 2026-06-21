from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_non_turn_logit_interaction_payload import (
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_ATOM_CANDIDATE_NAMES,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_DIAGNOSTIC_FIELD_NAMES,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_LATENCY_KEYS,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_SCHEMA_VERSION,
    build_non_turn_logit_interaction_payload,
)


REPLAY_SCRIPT = Path(__file__).resolve().parents[2] / (
    "scripts/integrations/run_diffusion_planner_camp_replay.py"
)


def test_non_turn_logit_interaction_payload_valid_fields() -> None:
    payload = build_non_turn_logit_interaction_payload(
        candidate_route_progress=np.asarray([10.0, 8.0, 12.0], dtype=np.float64),
        candidate_dp_prior_jerk_excess_cost=np.asarray(
            [0.0, 2.0, 1.5],
            dtype=np.float64,
        ),
        candidate_count=3,
    )

    assert payload["schema_version"] == NON_TURN_LOGIT_INTERACTION_PAYLOAD_SCHEMA_VERSION
    assert payload["enabled"] is True
    assert payload["default_off"] is True
    assert payload["selection_effect"] is False
    assert payload["future_outcome_leakage"] is False
    assert payload["closed_loop_outcome_fields_read"] is False
    assert payload["online_selector_change"] is False
    assert payload["deployed_atom_vector_change"] is False
    assert payload["classical_benders_claim"] is False
    assert payload["available"] is True
    assert payload["availability_reason"] is None
    assert payload["candidate_count"] == 3
    assert payload["route_progress_deficit_vs_top1_m"] == [0.0, 2.0, 0.0]
    assert payload["dp_prior_jerk_excess_cost"] == [0.0, 2.0, 1.5]
    assert payload["comfort_progress_interaction_cost"] == [0.0, 4.0, 0.0]
    assert payload["diagnostic_field_names"] == list(
        NON_TURN_LOGIT_INTERACTION_PAYLOAD_DIAGNOSTIC_FIELD_NAMES
    )
    assert payload["atom_candidate_names"] == list(
        NON_TURN_LOGIT_INTERACTION_PAYLOAD_ATOM_CANDIDATE_NAMES
    )
    assert set(payload["field_shapes"]) == {
        "candidate_route_progress",
        "candidate_dp_prior_jerk_excess_cost",
        *NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES,
    }
    assert payload["field_shapes"]["comfort_progress_interaction_cost"] == [3]
    assert all(payload["finite_checks"].values())
    assert set(payload["latency_ms"]) == set(
        NON_TURN_LOGIT_INTERACTION_PAYLOAD_LATENCY_KEYS
    )
    assert all(float(value) >= 0.0 for value in payload["latency_ms"].values())
    assert "score_k(w)=a_k^T w" in payload["math_boundary"]


def test_non_turn_logit_interaction_payload_missing_progress_fails_closed() -> None:
    payload = build_non_turn_logit_interaction_payload(
        candidate_route_progress=None,
        candidate_dp_prior_jerk_excess_cost=np.asarray([0.0, 1.0]),
        candidate_count=2,
    )

    assert payload["available"] is False
    assert payload["availability_reason"] == "candidate_route_progress_absent"
    assert payload["finite_checks"]["payload_valid"] is False
    assert payload["route_progress_deficit_vs_top1_m"] is None
    assert payload["comfort_progress_interaction_cost"] is None


def test_non_turn_logit_interaction_payload_count_mismatch_fails_closed() -> None:
    payload = build_non_turn_logit_interaction_payload(
        candidate_route_progress=np.asarray([2.0, 1.0, 0.0]),
        candidate_dp_prior_jerk_excess_cost=np.asarray([0.0, 1.0]),
        candidate_count=3,
    )

    assert payload["available"] is False
    assert payload["availability_reason"] == "candidate_count_mismatch"
    assert payload["finite_checks"]["payload_valid"] is False
    assert payload["finite_checks"]["candidate_count_matches"] is False
    assert payload["dp_prior_jerk_excess_cost"] is None


def test_non_turn_logit_interaction_payload_negative_jerk_fails_closed() -> None:
    payload = build_non_turn_logit_interaction_payload(
        candidate_route_progress=np.asarray([2.0, 1.0]),
        candidate_dp_prior_jerk_excess_cost=np.asarray([0.0, -0.1]),
        candidate_count=2,
    )

    assert payload["available"] is False
    assert (
        payload["availability_reason"]
        == "candidate_dp_prior_jerk_excess_cost_negative"
    )
    assert payload["finite_checks"]["payload_valid"] is False
    assert (
        payload["finite_checks"]["candidate_dp_prior_jerk_excess_cost_nonnegative"]
        is False
    )
    assert payload["comfort_progress_interaction_cost"] is None


def test_non_turn_logit_interaction_payload_does_not_accept_outcome_inputs() -> None:
    signature = inspect.signature(build_non_turn_logit_interaction_payload)

    assert "outcome" not in str(signature).lower()
    assert "closed_loop" not in str(signature).lower()
    assert list(signature.parameters) == [
        "candidate_route_progress",
        "candidate_dp_prior_jerk_excess_cost",
        "candidate_count",
    ]


def test_replay_script_wires_non_turn_logit_interaction_payload_default_off() -> None:
    source = REPLAY_SCRIPT.read_text(encoding="utf-8")

    assert "--camp_non_turn_logit_interaction_payload_logging" in source
    assert "build_non_turn_logit_interaction_payload(" in source
    assert "non_turn_logit_interaction_payload_logging=bool(" in source
    assert "args.camp_non_turn_logit_interaction_payload_logging" in source
    assert (
        "\"non_turn_logit_interaction_payload_logging\": ("
        in source
    )
    assert (
        "\"camp_non_turn_logit_interaction_payload_logging\": ("
        in source
    )
    assert (
        "validation[\"camp_non_turn_logit_interaction_payload_logging\"]"
        in source
    )
    assert "**non_turn_logit_interaction_payload_latency_ms" in source
    assert "\"deployed_atom_vector_change\": False" in source
