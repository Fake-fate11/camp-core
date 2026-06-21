from __future__ import annotations

import time
from typing import Any

import numpy as np


CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION = (
    "dp_camp_candidate_set_consensus_payload_v1"
)

CANDIDATE_SET_CONSENSUS_PAYLOAD_FIELD_NAMES = (
    "candidate_set_consensus_center_xy",
    "candidate_set_consensus_center_rms_m",
    "candidate_set_consensus_center_rms_rank",
    "candidate_set_consensus_center_rms_median_m",
    "candidate_set_consensus_center_rms_mad_m",
)

CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS = (
    "latency_ms_candidate_set_consensus_payload",
)

CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES = (
    "candidate_set_consensus_center_rms_cost_v1",
)


def build_candidate_set_consensus_payload(
    *,
    candidates: np.ndarray,
    support_steps: int,
) -> dict[str, Any]:
    """Build default-off candidate-set consensus diagnostics.

    The payload uses only the fixed current-tick DP candidate tensor before
    selection. It does not read closed-loop outcomes, simulator future state,
    selected-candidate effects, DP internals, or hidden model scores.
    """
    start = time.perf_counter()
    trajectories = np.asarray(candidates, dtype=np.float64)
    candidate_count = _validate_candidates(trajectories)
    requested_steps = _validate_positive_int(support_steps, "support_steps")
    effective_steps = min(requested_steps, int(trajectories.shape[1]))

    fields: dict[str, Any] = {
        name: None for name in CANDIDATE_SET_CONSENSUS_PAYLOAD_FIELD_NAMES
    }
    field_shapes: dict[str, list[int] | None] = {
        name: None for name in CANDIDATE_SET_CONSENSUS_PAYLOAD_FIELD_NAMES
    }
    finite_checks = {
        "payload_valid": False,
        "candidate_count_at_least_two": bool(candidate_count >= 2),
        "candidate_xy_finite": True,
        "candidate_set_consensus_center_xy_finite": True,
        "candidate_set_consensus_center_rms_m_finite": True,
        "candidate_set_consensus_center_rms_m_nonnegative": True,
        "candidate_set_consensus_center_rms_rank_valid": True,
        "candidate_set_consensus_center_rms_median_m_finite": True,
        "candidate_set_consensus_center_rms_mad_m_finite": True,
        "candidate_set_consensus_center_rms_mad_m_nonnegative": True,
    }
    available = False
    availability_reason = "candidate_count_less_than_two"

    if candidate_count >= 2:
        xy = trajectories[:, :effective_steps, :2]
        center = np.median(xy, axis=0)
        squared_distance = np.sum((xy - center[None, :, :]) ** 2, axis=2)
        rms = np.sqrt(np.mean(squared_distance, axis=1))
        median_rms = float(np.median(rms))
        mad_rms = float(np.median(np.abs(rms - median_rms)))
        ranks = _stable_ranks(rms)
        finite_checks["candidate_set_consensus_center_xy_finite"] = bool(
            np.all(np.isfinite(center))
        )
        finite_checks["candidate_set_consensus_center_rms_m_finite"] = bool(
            np.all(np.isfinite(rms))
        )
        finite_checks["candidate_set_consensus_center_rms_m_nonnegative"] = bool(
            np.all(rms >= -1e-12)
        )
        finite_checks["candidate_set_consensus_center_rms_rank_valid"] = bool(
            np.array_equal(np.sort(ranks), np.arange(candidate_count))
        )
        finite_checks["candidate_set_consensus_center_rms_median_m_finite"] = (
            bool(np.isfinite(median_rms))
        )
        finite_checks["candidate_set_consensus_center_rms_mad_m_finite"] = bool(
            np.isfinite(mad_rms)
        )
        finite_checks["candidate_set_consensus_center_rms_mad_m_nonnegative"] = bool(
            mad_rms >= -1e-12
        )
        finite_checks["payload_valid"] = bool(
            all(
                value
                for key, value in finite_checks.items()
                if key != "payload_valid"
            )
        )
        if finite_checks["payload_valid"]:
            rms = np.maximum(rms, 0.0)
            mad_rms = max(mad_rms, 0.0)
            fields["candidate_set_consensus_center_xy"] = center.tolist()
            fields["candidate_set_consensus_center_rms_m"] = rms.tolist()
            fields["candidate_set_consensus_center_rms_rank"] = ranks.tolist()
            fields["candidate_set_consensus_center_rms_median_m"] = median_rms
            fields["candidate_set_consensus_center_rms_mad_m"] = mad_rms
            field_shapes["candidate_set_consensus_center_xy"] = [
                int(effective_steps),
                2,
            ]
            field_shapes["candidate_set_consensus_center_rms_m"] = [
                int(candidate_count)
            ]
            field_shapes["candidate_set_consensus_center_rms_rank"] = [
                int(candidate_count)
            ]
            field_shapes["candidate_set_consensus_center_rms_median_m"] = []
            field_shapes["candidate_set_consensus_center_rms_mad_m"] = []
            available = True
            availability_reason = None
        else:
            availability_reason = "candidate_set_consensus_fields_invalid"

    latency_ms = (time.perf_counter() - start) * 1000.0
    return {
        "schema_version": CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "deployed_atom_vector_change": False,
        "definition": (
            "default-off current-tick candidate RMS distance from the "
            "coordinate-wise median xy center of the fixed DP candidate set"
        ),
        "candidate_count": int(candidate_count),
        "horizons": {
            "requested_support_steps": int(requested_steps),
            "effective_support_steps": int(effective_steps),
        },
        "available": bool(available),
        "availability_reason": availability_reason,
        "field_shapes": field_shapes,
        "finite_checks": finite_checks,
        "latency_ms": {
            "latency_ms_candidate_set_consensus_payload": float(latency_ms),
        },
        **fields,
        "atom_candidate_names": list(
            CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES
        ),
        "math_boundary": (
            "The candidate-set consensus coefficient is fixed before CAMP "
            "scoring for each current-tick candidate. It is finite and "
            "nonnegative when available; too few candidates fail closed. If "
            "later atomized after separate evidence gates, CAMP score remains "
            "affine in weights: score_k(w)=a_k^T w, and the simplex/CVaR/L2 "
            "master remains convex. No trajectory-coordinate convexity or "
            "DP-side classical Benders claim is made."
        ),
        "classical_benders_claim": False,
    }


def _stable_ranks(values: np.ndarray) -> np.ndarray:
    order = np.lexsort((np.arange(values.size), values))
    ranks = np.empty(values.size, dtype=np.int64)
    ranks[order] = np.arange(values.size, dtype=np.int64)
    return ranks


def _validate_candidates(candidates: np.ndarray) -> int:
    if candidates.ndim != 3 or candidates.shape[0] < 1 or candidates.shape[1] < 2:
        raise ValueError("candidates must have shape [K,T,>=2].")
    if candidates.shape[2] < 2:
        raise ValueError("candidates must contain x/y coordinates.")
    if not np.all(np.isfinite(candidates[:, :, :2])):
        raise ValueError("candidate coordinates must be finite.")
    return int(candidates.shape[0])


def _validate_positive_int(value: int, name: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise ValueError(f"{name} must be positive.")
    return parsed
