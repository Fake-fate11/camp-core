from __future__ import annotations

import inspect

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_candidate_set_consensus_payload import (
    CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES,
    CANDIDATE_SET_CONSENSUS_PAYLOAD_FIELD_NAMES,
    CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS,
    CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
    build_candidate_set_consensus_payload,
)

def _candidates() -> np.ndarray:
    return np.asarray(
        [
            [[0.0, 0.0, 1.0, 0.0], [1.0, 0.0, 1.0, 0.0], [2.0, 0.0, 1.0, 0.0]],
            [[0.2, 0.0, 1.0, 0.0], [1.2, 0.0, 1.0, 0.0], [2.2, 0.0, 1.0, 0.0]],
            [[4.0, 0.0, 1.0, 0.0], [5.0, 0.0, 1.0, 0.0], [6.0, 0.0, 1.0, 0.0]],
        ],
        dtype=np.float64,
    )


def test_candidate_set_consensus_payload_schema_shapes_and_metadata() -> None:
    payload = build_candidate_set_consensus_payload(
        candidates=_candidates(),
        support_steps=3,
    )

    assert payload["schema_version"] == CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION
    assert payload["enabled"] is True
    assert payload["default_off"] is True
    assert payload["selection_effect"] is False
    assert payload["future_outcome_leakage"] is False
    assert payload["closed_loop_outcome_fields_read"] is False
    assert payload["classical_benders_claim"] is False
    assert "score_k(w)=a_k^T w" in payload["math_boundary"]
    assert payload["candidate_count"] == 3
    assert payload["horizons"] == {
        "requested_support_steps": 3,
        "effective_support_steps": 3,
    }
    assert payload["available"] is True
    assert payload["availability_reason"] is None
    assert set(payload["field_shapes"]) == set(CANDIDATE_SET_CONSENSUS_PAYLOAD_FIELD_NAMES)
    assert payload["field_shapes"]["candidate_set_consensus_center_xy"] == [3, 2]
    assert payload["field_shapes"]["candidate_set_consensus_center_rms_m"] == [3]
    assert payload["field_shapes"]["candidate_set_consensus_center_rms_rank"] == [3]
    assert payload["field_shapes"]["candidate_set_consensus_center_rms_median_m"] == []
    assert payload["field_shapes"]["candidate_set_consensus_center_rms_mad_m"] == []
    assert all(payload["finite_checks"].values())
    assert set(payload["latency_ms"]) == set(CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS)
    assert all(float(value) >= 0.0 for value in payload["latency_ms"].values())
    assert payload["atom_candidate_names"] == list(
        CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES
    )


def test_candidate_set_consensus_costs_are_nonnegative_and_ranked() -> None:
    payload = build_candidate_set_consensus_payload(
        candidates=_candidates(),
        support_steps=3,
    )
    costs = np.asarray(
        payload["candidate_set_consensus_center_rms_m"],
        dtype=np.float64,
    )
    ranks = np.asarray(
        payload["candidate_set_consensus_center_rms_rank"],
        dtype=np.int64,
    )

    assert np.all(costs >= 0.0)
    assert costs[1] == 0.0
    assert costs[2] > costs[0] > costs[1]
    assert ranks.tolist() == [1, 0, 2]


def test_candidate_set_consensus_payload_fails_closed_for_single_candidate() -> None:
    payload = build_candidate_set_consensus_payload(
        candidates=_candidates()[:1],
        support_steps=3,
    )

    assert payload["available"] is False
    assert payload["availability_reason"] == "candidate_count_less_than_two"
    assert payload["finite_checks"]["payload_valid"] is False
    assert payload["finite_checks"]["candidate_count_at_least_two"] is False
    assert payload["candidate_set_consensus_center_rms_m"] is None


def test_candidate_set_consensus_payload_does_not_accept_outcome_inputs() -> None:
    signature = inspect.signature(build_candidate_set_consensus_payload)

    assert "outcome" not in str(signature).lower()
    assert "closed_loop" not in str(signature).lower()
    assert list(signature.parameters) == ["candidates", "support_steps"]


def test_candidate_set_consensus_timing_does_not_change_logged_values() -> None:
    first = build_candidate_set_consensus_payload(
        candidates=_candidates(),
        support_steps=3,
    )
    second = build_candidate_set_consensus_payload(
        candidates=_candidates(),
        support_steps=3,
    )

    first_without_latency = dict(first)
    second_without_latency = dict(second)
    first_without_latency.pop("latency_ms")
    second_without_latency.pop("latency_ms")
    assert first_without_latency == second_without_latency


def test_candidate_set_consensus_payload_validates_inputs() -> None:
    with pytest.raises(ValueError, match="candidates must have shape"):
        build_candidate_set_consensus_payload(
            candidates=np.zeros((4, 2), dtype=np.float64),
            support_steps=3,
        )
    with pytest.raises(ValueError, match="x/y"):
        build_candidate_set_consensus_payload(
            candidates=np.zeros((2, 3, 1), dtype=np.float64),
            support_steps=3,
        )
    bad = _candidates()
    bad[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        build_candidate_set_consensus_payload(candidates=bad, support_steps=3)
    with pytest.raises(ValueError, match="support_steps"):
        build_candidate_set_consensus_payload(
            candidates=_candidates(),
            support_steps=0,
        )
