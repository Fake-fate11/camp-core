from __future__ import annotations

import time
from typing import Any

import numpy as np


NON_TURN_LOGIT_INTERACTION_PAYLOAD_SCHEMA_VERSION = (
    "dp_camp_non_turn_logit_interaction_payload_v1"
)

NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES = (
    "route_progress_deficit_vs_top1_m",
    "dp_prior_jerk_excess_cost",
    "comfort_progress_interaction_cost",
)

NON_TURN_LOGIT_INTERACTION_PAYLOAD_LATENCY_KEYS = (
    "latency_ms_non_turn_logit_interaction_payload",
)

NON_TURN_LOGIT_INTERACTION_PAYLOAD_ATOM_CANDIDATE_NAMES = (
    "comfort_progress_interaction_cost",
)

NON_TURN_LOGIT_INTERACTION_PAYLOAD_DIAGNOSTIC_FIELD_NAMES = (
    "route_progress_deficit_vs_top1_m",
    "dp_prior_jerk_excess_cost",
)

NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_DEFINITIONS = {
    "route_progress_deficit_vs_top1_m": (
        "max(candidate_route_progress[0] - candidate_route_progress[k], 0); "
        "diagnostic only because deployed CAMP already contains a related "
        "progress-shortfall atom"
    ),
    "dp_prior_jerk_excess_cost": (
        "existing current-tick DP-prior jerk-excess candidate cost; diagnostic "
        "only because deployed CAMP v10 already contains this atom"
    ),
    "comfort_progress_interaction_cost": (
        "route_progress_deficit_vs_top1_m * dp_prior_jerk_excess_cost; a new "
        "nonnegative interaction candidate coefficient, not appended to the "
        "deployed atom vector by this payload"
    ),
}


def build_non_turn_logit_interaction_payload(
    *,
    candidate_route_progress: Any,
    candidate_dp_prior_jerk_excess_cost: Any,
    candidate_count: int,
) -> dict[str, Any]:
    """Build default-off progress/comfort interaction diagnostics.

    The payload only consumes fixed current-tick candidate coefficients already
    available before selection. It does not read closed-loop outcomes, mutate
    CAMP atoms, or change the online selector.
    """
    start = time.perf_counter()
    candidate_count_int = _validate_candidate_count(candidate_count)
    fields: dict[str, Any] = {
        name: None for name in NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES
    }
    field_shapes: dict[str, list[int] | None] = {
        "candidate_route_progress": None,
        "candidate_dp_prior_jerk_excess_cost": None,
        **{
            name: None for name in NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES
        },
    }
    finite_checks = {
        "payload_valid": True,
        "candidate_count_matches": True,
        "candidate_route_progress_finite": True,
        "candidate_dp_prior_jerk_excess_cost_finite": True,
        "candidate_dp_prior_jerk_excess_cost_nonnegative": True,
        "route_progress_deficit_vs_top1_m_finite": True,
        "route_progress_deficit_vs_top1_m_nonnegative": True,
        "dp_prior_jerk_excess_cost_finite": True,
        "dp_prior_jerk_excess_cost_nonnegative": True,
        "comfort_progress_interaction_cost_finite": True,
        "comfort_progress_interaction_cost_nonnegative": True,
    }
    available = False
    availability_reason: str | None = None

    route_progress = _optional_vector(candidate_route_progress)
    jerk_excess = _optional_vector(candidate_dp_prior_jerk_excess_cost)
    if route_progress is None:
        finite_checks["payload_valid"] = False
        finite_checks["candidate_count_matches"] = False
        availability_reason = "candidate_route_progress_absent"
    elif jerk_excess is None:
        finite_checks["payload_valid"] = False
        finite_checks["candidate_count_matches"] = False
        availability_reason = "candidate_dp_prior_jerk_excess_cost_absent"
    else:
        field_shapes["candidate_route_progress"] = list(route_progress.shape)
        field_shapes["candidate_dp_prior_jerk_excess_cost"] = list(
            jerk_excess.shape
        )
        count_matches = bool(
            route_progress.shape == (candidate_count_int,)
            and jerk_excess.shape == (candidate_count_int,)
        )
        finite_checks["candidate_count_matches"] = count_matches
        if not count_matches:
            finite_checks["payload_valid"] = False
            availability_reason = "candidate_count_mismatch"
        elif not bool(np.all(np.isfinite(route_progress))):
            finite_checks["payload_valid"] = False
            finite_checks["candidate_route_progress_finite"] = False
            availability_reason = "candidate_route_progress_nonfinite"
        elif not bool(np.all(np.isfinite(jerk_excess))):
            finite_checks["payload_valid"] = False
            finite_checks["candidate_dp_prior_jerk_excess_cost_finite"] = False
            finite_checks["dp_prior_jerk_excess_cost_finite"] = False
            availability_reason = "candidate_dp_prior_jerk_excess_cost_nonfinite"
        elif bool(np.any(jerk_excess < -1e-12)):
            finite_checks["payload_valid"] = False
            finite_checks[
                "candidate_dp_prior_jerk_excess_cost_nonnegative"
            ] = False
            finite_checks["dp_prior_jerk_excess_cost_nonnegative"] = False
            availability_reason = "candidate_dp_prior_jerk_excess_cost_negative"
        else:
            progress_deficit = np.maximum(route_progress[0] - route_progress, 0.0)
            jerk_cost = np.maximum(jerk_excess, 0.0)
            interaction = progress_deficit * jerk_cost
            finite_checks["route_progress_deficit_vs_top1_m_finite"] = bool(
                np.all(np.isfinite(progress_deficit))
            )
            finite_checks["route_progress_deficit_vs_top1_m_nonnegative"] = bool(
                np.all(progress_deficit >= -1e-12)
            )
            finite_checks["dp_prior_jerk_excess_cost_finite"] = bool(
                np.all(np.isfinite(jerk_cost))
            )
            finite_checks["dp_prior_jerk_excess_cost_nonnegative"] = bool(
                np.all(jerk_cost >= -1e-12)
            )
            finite_checks["comfort_progress_interaction_cost_finite"] = bool(
                np.all(np.isfinite(interaction))
            )
            finite_checks["comfort_progress_interaction_cost_nonnegative"] = bool(
                np.all(interaction >= -1e-12)
            )
            finite_checks["payload_valid"] = bool(all(finite_checks.values()))
            if finite_checks["payload_valid"]:
                fields["route_progress_deficit_vs_top1_m"] = (
                    progress_deficit.tolist()
                )
                fields["dp_prior_jerk_excess_cost"] = jerk_cost.tolist()
                fields["comfort_progress_interaction_cost"] = interaction.tolist()
                field_shapes["route_progress_deficit_vs_top1_m"] = list(
                    progress_deficit.shape
                )
                field_shapes["dp_prior_jerk_excess_cost"] = list(jerk_cost.shape)
                field_shapes["comfort_progress_interaction_cost"] = list(
                    interaction.shape
                )
                available = True
            else:
                availability_reason = "derived_interaction_invalid"

    if availability_reason is None and not available:
        availability_reason = "payload_invalid"
    latency_ms = (time.perf_counter() - start) * 1000.0
    return {
        "schema_version": NON_TURN_LOGIT_INTERACTION_PAYLOAD_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "deployed_atom_vector_change": False,
        "definition": (
            "current-tick progress/comfort interaction diagnostics computed "
            "from fixed DP candidate route progress and DP-prior jerk-excess "
            "costs before selection"
        ),
        "candidate_count": candidate_count_int,
        "available": bool(available),
        "availability_reason": availability_reason,
        "field_shapes": field_shapes,
        "finite_checks": finite_checks,
        "latency_ms": {
            "latency_ms_non_turn_logit_interaction_payload": float(latency_ms)
        },
        **fields,
        "diagnostic_field_names": list(
            NON_TURN_LOGIT_INTERACTION_PAYLOAD_DIAGNOSTIC_FIELD_NAMES
        ),
        "atom_candidate_names": list(
            NON_TURN_LOGIT_INTERACTION_PAYLOAD_ATOM_CANDIDATE_NAMES
        ),
        "field_definitions": dict(
            NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_DEFINITIONS
        ),
        "math_boundary": (
            "The payload fields are fixed current-tick finite-candidate "
            "coefficients. Progress deficit and DP-prior jerk are logged as "
            "diagnostics only; their product is nonnegative and may later be "
            "audited as a candidate atom coordinate. If later promoted after "
            "separate evidence, CAMP score remains affine in weights: "
            "score_k(w)=a_k^T w, and the simplex/CVaR/L2 master remains "
            "convex. This payload makes no trajectory-coordinate convexity "
            "claim and no DP-side classical Benders claim."
        ),
        "classical_benders_claim": False,
    }


def _optional_vector(value: Any) -> np.ndarray | None:
    if value is None:
        return None
    array = np.asarray(value, dtype=np.float64).reshape(-1)
    return array


def _validate_candidate_count(candidate_count: int) -> int:
    candidate_count_int = int(candidate_count)
    if candidate_count_int < 1:
        raise ValueError("candidate_count must be positive.")
    return candidate_count_int
