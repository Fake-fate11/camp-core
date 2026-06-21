from __future__ import annotations

import time
from typing import Any

import numpy as np


TEMPORAL_CONSISTENCY_PAYLOAD_SCHEMA_VERSION = (
    "dp_camp_temporal_consistency_payload_v1"
)

TEMPORAL_CONSISTENCY_PAYLOAD_FIELD_NAMES = (
    "previous_plan_temporal_consistency_rms_m",
)

TEMPORAL_CONSISTENCY_PAYLOAD_LATENCY_KEYS = (
    "latency_ms_temporal_consistency_payload",
)

TEMPORAL_CONSISTENCY_PAYLOAD_ATOM_CANDIDATE_NAMES = (
    "previous_plan_temporal_consistency_rms_m",
)


def build_temporal_consistency_payload(
    *,
    candidates: np.ndarray,
    previous_selected_plan: np.ndarray | None,
    support_steps: int,
    dt_s: float = 0.1,
    elapsed_steps: int = 1,
    min_overlap_steps: int = 2,
) -> dict[str, Any]:
    """Build default-off previous-plan temporal consistency diagnostics.

    The payload compares fixed current-tick DP candidates against the selected
    planned trajectory emitted before the current tick, shifted by the elapsed
    planner samples. It does not read closed-loop outcomes, mutate atom
    schemas, call DP, or affect selection.
    """
    start = time.perf_counter()
    trajectories = np.asarray(candidates, dtype=np.float64)
    candidate_count = _validate_candidates(trajectories)
    dt = _validate_dt(dt_s)
    elapsed = _validate_nonnegative_int(elapsed_steps, "elapsed_steps")
    min_overlap = _validate_positive_int(min_overlap_steps, "min_overlap_steps")
    requested_steps = _validate_positive_int(support_steps, "support_steps")

    field_shapes = {
        "previous_plan_temporal_consistency_rms_m": None,
    }
    finite_checks = {
        "payload_valid": False,
        "candidate_count_matches": True,
        "previous_selected_plan_available": previous_selected_plan is not None,
        "previous_selected_plan_finite": True,
        "overlap_steps_sufficient": False,
        "previous_plan_temporal_consistency_rms_m_finite": True,
        "previous_plan_temporal_consistency_rms_m_nonnegative": True,
    }

    available = False
    availability_reason = "previous_selected_plan_absent"
    rms_cost: list[float] | None = None
    overlap_steps = 0
    previous_plan_shape: list[int] | None = None

    if previous_selected_plan is not None:
        previous = np.asarray(previous_selected_plan, dtype=np.float64)
        previous_plan_shape = list(previous.shape)
        if previous.ndim != 2 or previous.shape[1] < 2:
            availability_reason = "previous_selected_plan_invalid_shape"
            finite_checks["previous_selected_plan_finite"] = False
        elif not np.all(np.isfinite(previous[:, :2])):
            availability_reason = "previous_selected_plan_nonfinite"
            finite_checks["previous_selected_plan_finite"] = False
        else:
            overlap_steps = min(
                requested_steps,
                int(trajectories.shape[1]),
                max(int(previous.shape[0]) - elapsed, 0),
            )
            finite_checks["overlap_steps_sufficient"] = bool(
                overlap_steps >= min_overlap
            )
            if overlap_steps < min_overlap:
                availability_reason = "overlap_steps_insufficient"
            else:
                current_xy = trajectories[:, :overlap_steps, :2]
                previous_xy = previous[
                    elapsed : elapsed + overlap_steps,
                    :2,
                ]
                delta = current_xy - previous_xy[None, :, :]
                rms = np.sqrt(np.mean(np.sum(delta * delta, axis=2), axis=1))
                finite = bool(np.all(np.isfinite(rms)))
                nonnegative = bool(np.all(rms >= -1e-12))
                finite_checks[
                    "previous_plan_temporal_consistency_rms_m_finite"
                ] = finite
                finite_checks[
                    "previous_plan_temporal_consistency_rms_m_nonnegative"
                ] = nonnegative
                finite_checks["payload_valid"] = bool(finite and nonnegative)
                if finite_checks["payload_valid"]:
                    rms = np.maximum(rms, 0.0)
                    rms_cost = [float(value) for value in rms.tolist()]
                    field_shapes["previous_plan_temporal_consistency_rms_m"] = [
                        candidate_count
                    ]
                    available = True
                    availability_reason = None
                else:
                    availability_reason = "temporal_consistency_cost_invalid"

    latency_ms = (time.perf_counter() - start) * 1000.0
    return {
        "schema_version": TEMPORAL_CONSISTENCY_PAYLOAD_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "deployed_atom_vector_change": False,
        "definition": (
            "default-off current-tick candidate RMS deviation from the previous "
            "tick selected planned trajectory after shifting by elapsed planner "
            "samples"
        ),
        "candidate_count": int(candidate_count),
        "previous_selected_plan_shape": previous_plan_shape,
        "horizons": {
            "requested_support_steps": int(requested_steps),
            "effective_overlap_steps": int(overlap_steps),
            "minimum_overlap_steps": int(min_overlap),
            "elapsed_steps": int(elapsed),
            "dt_s": float(dt),
        },
        "available": bool(available),
        "availability_reason": availability_reason,
        "field_shapes": field_shapes,
        "finite_checks": finite_checks,
        "latency_ms": {
            "latency_ms_temporal_consistency_payload": float(latency_ms),
        },
        "previous_plan_temporal_consistency_rms_m": rms_cost,
        "atom_candidate_names": list(
            TEMPORAL_CONSISTENCY_PAYLOAD_ATOM_CANDIDATE_NAMES
        ),
        "math_boundary": (
            "The temporal consistency coefficient is fixed before CAMP scoring "
            "for each finite current-tick candidate. It is finite and "
            "nonnegative when available; missing memory fails closed. If later "
            "atomized after a separate gate, CAMP score remains affine in "
            "weights: score_k(w)=a_k^T w, and the simplex/CVaR/L2 master "
            "remains convex. No DP-side classical Benders claim is made."
        ),
        "classical_benders_claim": False,
    }


def _validate_candidates(candidates: np.ndarray) -> int:
    if candidates.ndim != 3 or candidates.shape[0] < 1 or candidates.shape[1] < 2:
        raise ValueError("candidates must have shape [K,T,>=2].")
    if candidates.shape[2] < 2:
        raise ValueError("candidates must contain x/y coordinates.")
    if not np.all(np.isfinite(candidates[:, :, :2])):
        raise ValueError("candidate coordinates must be finite.")
    return int(candidates.shape[0])


def _validate_dt(dt_s: float) -> float:
    dt = float(dt_s)
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("dt_s must be finite and positive.")
    return dt


def _validate_positive_int(value: int, name: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise ValueError(f"{name} must be positive.")
    return parsed


def _validate_nonnegative_int(value: int, name: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise ValueError(f"{name} must be nonnegative.")
    return parsed
