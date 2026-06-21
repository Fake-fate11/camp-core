from __future__ import annotations

import time
from typing import Any

import numpy as np


TURN_LOGIT_PAYLOAD_SCHEMA_VERSION = "dp_camp_turn_logit_payload_v1"

TURN_LOGIT_PAYLOAD_FIELD_NAMES = (
    "candidate_turn_indicator_logits",
    "candidate_turn_indicator_probabilities",
    "candidate_turn_indicator_top_class",
)

TURN_LOGIT_PAYLOAD_LATENCY_KEYS = ("latency_ms_turn_logit_payload",)

TURN_LOGIT_PAYLOAD_ATOM_CANDIDATE_NAMES = (
    "turn_logit_entropy_cost_v1",
    "turn_logit_margin_shortfall_v1",
    "turn_logit_non_top1_disagreement_v1",
)

TURN_LOGIT_PAYLOAD_ATOM_CANDIDATE_DEFINITIONS = {
    "turn_logit_entropy_cost_v1": (
        "normalized categorical entropy of the candidate turn-indicator "
        "probability vector; finite and nonnegative"
    ),
    "turn_logit_margin_shortfall_v1": (
        "hinge on the gap between the largest and second-largest turn "
        "probability; finite and nonnegative"
    ),
    "turn_logit_non_top1_disagreement_v1": (
        "indicator that a candidate's top turn class differs from candidate0; "
        "finite and nonnegative"
    ),
}


def build_turn_logit_payload(
    *,
    turn_logits: Any,
    candidate_count: int,
) -> dict[str, Any]:
    """Build default-off turn-logit diagnostics.

    The payload uses only optional per-candidate turn-indicator logits already
    returned by the fixed DP wrapper before selection. It does not read
    closed-loop outcomes, simulator future state, or selected-candidate effects.
    """
    start = time.perf_counter()
    candidate_count_int = _validate_candidate_count(candidate_count)
    fields: dict[str, Any] = {
        "candidate_turn_indicator_logits": None,
        "candidate_turn_indicator_probabilities": None,
        "candidate_turn_indicator_top_class": None,
    }
    field_shapes: dict[str, list[int] | None] = {
        name: None for name in TURN_LOGIT_PAYLOAD_FIELD_NAMES
    }
    finite_checks = {
        "payload_valid": True,
        "candidate_count_matches": True,
        "candidate_turn_indicator_logits_finite": True,
        "candidate_turn_indicator_probabilities_finite": True,
        "candidate_turn_indicator_probabilities_row_sum_one": True,
        "candidate_turn_indicator_top_class_finite": True,
    }
    available = False
    availability_reason = "turn_indicator_logits_absent"

    if turn_logits is not None:
        logits = np.asarray(turn_logits, dtype=np.float64)
        field_shapes["candidate_turn_indicator_logits"] = list(logits.shape)
        count_matches = bool(logits.ndim >= 1 and logits.shape[0] == candidate_count_int)
        finite_checks["candidate_count_matches"] = count_matches
        if logits.ndim != 2 or logits.shape[1] < 1 or not count_matches:
            finite_checks["payload_valid"] = False
            availability_reason = "turn_indicator_logits_invalid_shape"
        elif not bool(np.all(np.isfinite(logits))):
            finite_checks["payload_valid"] = False
            finite_checks["candidate_turn_indicator_logits_finite"] = False
            availability_reason = "turn_indicator_logits_nonfinite"
        else:
            probabilities = _stable_softmax(logits)
            top_class = np.argmax(probabilities, axis=1).astype(np.int64)
            probabilities_finite = bool(np.all(np.isfinite(probabilities)))
            row_sum_one = bool(
                np.allclose(
                    np.sum(probabilities, axis=1),
                    np.ones(candidate_count_int, dtype=np.float64),
                    atol=1e-9,
                    rtol=1e-9,
                )
            )
            finite_checks["candidate_turn_indicator_probabilities_finite"] = (
                probabilities_finite
            )
            finite_checks["candidate_turn_indicator_probabilities_row_sum_one"] = (
                row_sum_one
            )
            finite_checks["candidate_turn_indicator_top_class_finite"] = bool(
                np.all(np.isfinite(top_class.astype(np.float64)))
            )
            finite_checks["payload_valid"] = bool(
                probabilities_finite
                and row_sum_one
                and finite_checks["candidate_turn_indicator_top_class_finite"]
            )
            if finite_checks["payload_valid"]:
                fields["candidate_turn_indicator_logits"] = logits.tolist()
                fields["candidate_turn_indicator_probabilities"] = (
                    probabilities.tolist()
                )
                fields["candidate_turn_indicator_top_class"] = top_class.tolist()
                field_shapes["candidate_turn_indicator_probabilities"] = list(
                    probabilities.shape
                )
                field_shapes["candidate_turn_indicator_top_class"] = list(
                    top_class.shape
                )
                available = True
                availability_reason = None
            else:
                availability_reason = "turn_indicator_logits_probability_invalid"

    latency_ms = (time.perf_counter() - start) * 1000.0
    return {
        "schema_version": TURN_LOGIT_PAYLOAD_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "source_field": "turn_indicator_logit",
        "definition": (
            "optional current-tick per-candidate turn-indicator logits returned "
            "by the fixed DP wrapper before CAMP selection"
        ),
        "candidate_count": candidate_count_int,
        "available": bool(available),
        "availability_reason": availability_reason,
        "field_shapes": field_shapes,
        "finite_checks": finite_checks,
        "latency_ms": {"latency_ms_turn_logit_payload": float(latency_ms)},
        **fields,
        "turn_logit_atomization_candidate_names": list(
            TURN_LOGIT_PAYLOAD_ATOM_CANDIDATE_NAMES
        ),
        "turn_logit_atomization_candidate_definitions": dict(
            TURN_LOGIT_PAYLOAD_ATOM_CANDIDATE_DEFINITIONS
        ),
        "turn_logit_atomization_candidates_available": bool(available),
        "math_boundary": (
            "Turn-logit atomization candidates would be fixed current-tick "
            "finite-candidate coefficients derived from logits/probabilities "
            "before selection. Entropy, margin shortfall, and candidate0-relative "
            "top-class disagreement are nonnegative. If later atomized, CAMP "
            "score remains affine in weights: score_k(w)=a_k^T w, and the "
            "simplex/CVaR/L2 master remains convex. No DP-side classical "
            "Benders claim is made."
        ),
        "classical_benders_claim": False,
    }


def _stable_softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=1, keepdims=True)


def _validate_candidate_count(candidate_count: int) -> int:
    candidate_count_int = int(candidate_count)
    if candidate_count_int < 1:
        raise ValueError("candidate_count must be positive.")
    return candidate_count_int
