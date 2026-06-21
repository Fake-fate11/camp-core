from __future__ import annotations

from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_turn_logit_payload import (
    TURN_LOGIT_PAYLOAD_ATOM_CANDIDATE_NAMES,
    TURN_LOGIT_PAYLOAD_FIELD_NAMES,
    TURN_LOGIT_PAYLOAD_LATENCY_KEYS,
    TURN_LOGIT_PAYLOAD_SCHEMA_VERSION,
    build_turn_logit_payload,
)


REPLAY_SCRIPT = Path(__file__).resolve().parents[2] / (
    "scripts/integrations/run_diffusion_planner_camp_replay.py"
)


def test_turn_logit_payload_absent_is_null_safe() -> None:
    payload = build_turn_logit_payload(turn_logits=None, candidate_count=3)

    assert payload["schema_version"] == TURN_LOGIT_PAYLOAD_SCHEMA_VERSION
    assert payload["enabled"] is True
    assert payload["default_off"] is True
    assert payload["selection_effect"] is False
    assert payload["future_outcome_leakage"] is False
    assert payload["closed_loop_outcome_fields_read"] is False
    assert payload["classical_benders_claim"] is False
    assert payload["candidate_count"] == 3
    assert payload["available"] is False
    assert payload["availability_reason"] == "turn_indicator_logits_absent"
    assert payload["turn_logit_atomization_candidates_available"] is False
    assert payload["turn_logit_atomization_candidate_names"] == list(
        TURN_LOGIT_PAYLOAD_ATOM_CANDIDATE_NAMES
    )
    for field_name in TURN_LOGIT_PAYLOAD_FIELD_NAMES:
        assert payload[field_name] is None
        assert payload["field_shapes"][field_name] is None
    assert all(payload["finite_checks"].values())
    assert set(payload["latency_ms"]) == set(TURN_LOGIT_PAYLOAD_LATENCY_KEYS)
    assert all(float(value) >= 0.0 for value in payload["latency_ms"].values())


def test_turn_logit_payload_valid_logits_softmax_and_top_class() -> None:
    logits = np.asarray(
        [
            [1.0, 3.0, 0.0],
            [4.0, 2.0, 1.0],
        ],
        dtype=np.float64,
    )
    payload = build_turn_logit_payload(turn_logits=logits, candidate_count=2)

    assert payload["available"] is True
    assert payload["availability_reason"] is None
    assert payload["field_shapes"]["candidate_turn_indicator_logits"] == [2, 3]
    assert payload["field_shapes"]["candidate_turn_indicator_probabilities"] == [2, 3]
    assert payload["field_shapes"]["candidate_turn_indicator_top_class"] == [2]
    assert payload["candidate_turn_indicator_logits"] == logits.tolist()
    assert payload["candidate_turn_indicator_top_class"] == [1, 0]
    probabilities = np.asarray(
        payload["candidate_turn_indicator_probabilities"],
        dtype=np.float64,
    )
    np.testing.assert_allclose(probabilities.sum(axis=1), np.ones(2), atol=1e-12)
    assert all(payload["finite_checks"].values())
    assert payload["turn_logit_atomization_candidates_available"] is True
    assert "score_k(w)=a_k^T w" in payload["math_boundary"]


def test_turn_logit_payload_bad_shape_fails_closed() -> None:
    payload = build_turn_logit_payload(
        turn_logits=np.ones((3, 2), dtype=np.float64),
        candidate_count=2,
    )

    assert payload["available"] is False
    assert payload["availability_reason"] == "turn_indicator_logits_invalid_shape"
    assert payload["finite_checks"]["payload_valid"] is False
    assert payload["finite_checks"]["candidate_count_matches"] is False
    assert payload["field_shapes"]["candidate_turn_indicator_logits"] == [3, 2]
    assert payload["candidate_turn_indicator_logits"] is None
    assert payload["candidate_turn_indicator_probabilities"] is None
    assert payload["candidate_turn_indicator_top_class"] is None
    assert payload["turn_logit_atomization_candidates_available"] is False


def test_turn_logit_payload_nonfinite_logits_fail_closed() -> None:
    payload = build_turn_logit_payload(
        turn_logits=np.asarray([[0.0, np.nan], [1.0, 2.0]], dtype=np.float64),
        candidate_count=2,
    )

    assert payload["available"] is False
    assert payload["availability_reason"] == "turn_indicator_logits_nonfinite"
    assert payload["finite_checks"]["payload_valid"] is False
    assert payload["finite_checks"]["candidate_count_matches"] is True
    assert payload["finite_checks"]["candidate_turn_indicator_logits_finite"] is False
    assert payload["candidate_turn_indicator_logits"] is None
    assert payload["turn_logit_atomization_candidates_available"] is False


def test_replay_script_wires_turn_logit_payload_default_off() -> None:
    source = REPLAY_SCRIPT.read_text(encoding="utf-8")

    assert "--camp_turn_logit_payload_logging" in source
    assert "build_turn_logit_payload(" in source
    assert "turn_logit_payload_logging=bool(args.camp_turn_logit_payload_logging)" in source
    assert '"turn_logit_payload_logging": turn_logit_payload_logging_payload' in source
    assert '"camp_turn_logit_payload_logging": camp_turn_logit_payload_logging' in source
    assert "validation[\"camp_turn_logit_payload_logging\"]" in source
