from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_candidate_set_consensus_payload import (
    build_candidate_set_consensus_payload,
)
from camp_core.integrations.diffusion_planner_causal_materializer import (
    validate_causal_dp_input,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
    validate_causal_signal_atom_input,
)


CONTEXT_SCHEMA_VERSION = "camp_dp_v25_causal_context_raw_v2"
LEGACY_CONTEXT_SCHEMA_VERSION = "camp_dp_v25_causal_context_raw_v1"
PHI_SCHEMA_VERSION = "camp_dp_v25_complement_lift_phi_v1"
RAW_FEATURE_NAMES = (
    "ego_speed_mps",
    "ego_longitudinal_acceleration_mps2",
    "ego_lateral_acceleration_mps2",
    "ego_yaw_rate_radps",
    "route_curvature_mean_abs_radpm",
    "route_curvature_max_abs_radpm",
    "route_lane_width_min_m",
    "route_lane_width_p50_m",
    "route_speed_limit_min_mps",
    "route_speed_limit_current_mps",
    "traffic_phase_red",
    "traffic_phase_yellow",
    "traffic_phase_green",
    "traffic_phase_unknown",
    "traffic_signal_distance_m",
    "traffic_signal_phase_remaining_s",
    "neighbor_count",
    "neighbor_min_distance_m",
    "neighbor_min_ttc_s",
    "neighbor_closing_speed_mps",
    "neighbor_lateral_gap_min_m",
    "candidate_consensus_rms_median_m",
    "candidate_consensus_rms_mad_m",
    "candidate_endpoint_xy_std_m",
    "candidate_progress_std_m",
    "candidate_source_valid_fraction",
)
RAW_FEATURE_COUNT = len(RAW_FEATURE_NAMES)
PHI_DIMENSION = 1 + 2 * RAW_FEATURE_COUNT
NO_NEIGHBOR_DISTANCE_M = 100.0
NO_NEIGHBOR_TTC_S = 30.0


@dataclass(frozen=True)
class V25ContextRecord:
    raw: np.ndarray
    source_complete: tuple[bool, ...]
    source_receipt: Mapping[str, Any]

    def as_dict(self) -> dict[str, float]:
        if np.asarray(self.raw).shape != (RAW_FEATURE_COUNT,):
            raise ValueError("V25 raw context dimension drifted")
        return {
            name: float(value)
            for name, value in zip(RAW_FEATURE_NAMES, self.raw)
        }


@dataclass(frozen=True)
class V25ContextScaler:
    q05: np.ndarray
    q95: np.ndarray

    def __post_init__(self) -> None:
        low = np.asarray(self.q05, dtype=np.float64).reshape(-1)
        high = np.asarray(self.q95, dtype=np.float64).reshape(-1)
        if low.shape != (RAW_FEATURE_COUNT,) or high.shape != (RAW_FEATURE_COUNT,):
            raise ValueError(
                f"q05/q95 must both have shape ({RAW_FEATURE_COUNT},)."
            )
        if not np.all(np.isfinite(low)) or not np.all(np.isfinite(high)):
            raise ValueError("q05/q95 must contain only finite values.")
        if np.any(high <= low):
            raise ValueError("Every train q95 must be strictly greater than q05.")
        object.__setattr__(self, "q05", low.copy())
        object.__setattr__(self, "q95", high.copy())

    def normalize(self, raw: np.ndarray) -> np.ndarray:
        values = _raw_matrix(raw)
        unit = np.clip((values - self.q05) / (self.q95 - self.q05), 0.0, 1.0)
        return unit[0] if np.asarray(raw).ndim == 1 else unit

    def lift(
        self,
        raw: np.ndarray,
        *,
        source_complete: np.ndarray | None = None,
    ) -> np.ndarray:
        unit = self.normalize(raw)
        if source_complete is None:
            return complement_lift(unit)
        return masked_complement_lift(unit, source_complete)


def build_v25_raw_context(
    *,
    causal_input: Mapping[str, Any],
    candidates: np.ndarray,
    source_valid_mask: np.ndarray,
    causal_signal_atom_input: Mapping[str, Any] | None = None,
    v2i_signal_timing: Mapping[str, Any] | None = None,
    allow_missing_route_speed_limit_context: bool = False,
) -> V25ContextRecord:
    """Build the frozen V25 context from current request/state and fixed K=8.

    The boundary deliberately accepts no identifiers, outcome fields, GT future,
    selected-candidate state, or private Diffusion Planner latent. Missing signal
    timing is represented by zero and marked incomplete in the no-V2I main
    method. A separate V2I mode requires a current-time source/timestamp/
    freshness receipt; frozen scenario schedules are never accepted. No-signal
    distance is censored at the visible route length. Empty-neighbor
    distance/TTC use fixed causal sentinels so every feature stays finite.
    """
    errors = validate_causal_dp_input(causal_input)
    if errors:
        raise ValueError("invalid causal input: " + "; ".join(errors))
    trajectories = np.asarray(candidates, dtype=np.float64)
    if trajectories.shape != (8, 80, 4) or not np.all(np.isfinite(trajectories)):
        raise ValueError("candidates must be finite with shape [8,80,4].")
    source_valid = np.asarray(source_valid_mask)
    if source_valid.shape != (8,) or source_valid.dtype != np.bool_:
        raise ValueError("source_valid_mask must be native bool with shape [8].")
    if not np.any(source_valid):
        raise ValueError("source_valid_mask must contain at least one valid candidate.")
    source_valid = source_valid.copy()

    ego = np.asarray(causal_input["ego_current_state"], dtype=np.float64).reshape(-1)
    if ego.shape != (10,) or not np.all(np.isfinite(ego)):
        raise ValueError("ego_current_state must be finite with shape [10].")
    ego_speed = max(float(ego[4]), 0.0)
    ego_longitudinal_acceleration = float(ego[6])
    ego_yaw_rate = float(ego[9])
    ego_lateral_acceleration = ego_speed * ego_yaw_rate

    route_rows, route_arc = _ordered_route_rows(causal_input["route_lanes"])
    curvature = _route_curvature(route_rows[:, :2])
    lane_widths = np.linalg.norm(route_rows[:, 4:6], axis=1) + np.linalg.norm(
        route_rows[:, 6:8], axis=1
    )
    if not np.all(np.isfinite(lane_widths)) or np.any(lane_widths <= 0.0):
        raise ValueError("route boundary offsets must yield positive lane widths.")

    route_limits = np.asarray(
        causal_input["route_lanes_speed_limit"], dtype=np.float64
    ).reshape(-1)
    route_has_limits = np.asarray(
        causal_input["route_lanes_has_speed_limit"], dtype=bool
    ).reshape(-1)
    available_limits = route_limits[route_has_limits]
    if available_limits.size:
        if not np.all(np.isfinite(available_limits)):
            raise ValueError("route speed-limit source marked available but is non-finite.")
        if np.any(available_limits <= 0.0):
            raise ValueError("route speed-limit source marked available but is non-positive.")
        speed_limit_context_complete = True
        route_speed_limit_min = float(np.min(available_limits))
        route_speed_limit_current = float(available_limits[0])
    else:
        if not allow_missing_route_speed_limit_context:
            raise ValueError("V25 context requires a current positive route speed limit.")
        # The finite placeholders are never consumed by masked_complement_lift:
        # both source-completeness bits below are false.  They are not a speed
        # default or an imputation, and the opt-in is reserved for source-bound
        # V26 endpoint-inapplicability handling.
        speed_limit_context_complete = False
        route_speed_limit_min = 0.0
        route_speed_limit_current = 0.0

    phase, signal_distance, phase_known = _resolved_signal_context(
        route_rows,
        route_arc,
        causal_signal_atom_input=causal_signal_atom_input,
    )
    phase_remaining, timing_known, timing_receipt = _v2i_timing_context(
        v2i_signal_timing,
        regulatory_signal_mapped=phase_known,
    )

    neighbor_values, neighbor_complete = _neighbor_context(
        causal_input["neighbor_agents_past"], ego_speed
    )
    consensus = build_candidate_set_consensus_payload(
        candidates=trajectories,
        support_steps=trajectories.shape[1],
    )
    if not consensus["available"]:
        raise ValueError("fixed K=8 candidate consensus context is unavailable.")
    endpoints = trajectories[:, -1, :2]
    endpoint_std = float(np.sqrt(np.var(endpoints[:, 0]) + np.var(endpoints[:, 1])))
    progress_std = float(
        np.std(_candidate_route_progress(trajectories[:, :, :2], route_rows[:, :2]))
    )

    phase_values = {
        "red": (1.0, 0.0, 0.0, 0.0),
        "yellow": (0.0, 1.0, 0.0, 0.0),
        "green": (0.0, 0.0, 1.0, 0.0),
        "unknown": (0.0, 0.0, 0.0, 1.0),
    }[phase]
    raw = np.asarray(
        [
            ego_speed,
            ego_longitudinal_acceleration,
            ego_lateral_acceleration,
            ego_yaw_rate,
            float(np.mean(curvature)),
            float(np.max(curvature)),
            float(np.min(lane_widths)),
            float(np.median(lane_widths)),
            route_speed_limit_min,
            route_speed_limit_current,
            *phase_values,
            signal_distance,
            phase_remaining,
            *neighbor_values,
            float(consensus["candidate_set_consensus_center_rms_median_m"]),
            float(consensus["candidate_set_consensus_center_rms_mad_m"]),
            endpoint_std,
            progress_std,
            float(np.mean(source_valid)),
        ],
        dtype=np.float64,
    )
    if raw.shape != (RAW_FEATURE_COUNT,) or not np.all(np.isfinite(raw)):
        raise ValueError("V25 raw context violated its finite 26D contract.")
    complete = (
        *(True for _ in range(8)),
        speed_limit_context_complete,
        speed_limit_context_complete,
        *(phase_known for _ in range(5)),
        timing_known,
        *(neighbor_complete for _ in range(5)),
        *(True for _ in range(5)),
    )
    if len(complete) != RAW_FEATURE_COUNT:
        raise AssertionError("internal V25 source-completeness dimension mismatch")
    return V25ContextRecord(
        raw=raw,
        source_complete=tuple(bool(x) for x in complete),
        source_receipt=timing_receipt,
    )


def _v2i_timing_context(
    payload: Mapping[str, Any] | None,
    *,
    regulatory_signal_mapped: bool,
) -> tuple[float, bool, Mapping[str, Any]]:
    if payload is None:
        return 0.0, False, {
            "mode": "no_v2i",
            "phase_remaining_available": False,
            "regulatory_signal_mapped": bool(regulatory_signal_mapped),
        }
    required = {
        "source_id",
        "phase_remaining_s",
        "decision_timestamp_s",
        "source_timestamp_s",
        "maximum_age_s",
        "valid",
    }
    if set(payload) != required:
        raise ValueError("V2I timing receipt fields do not match context-v2")
    source_id = payload["source_id"]
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("V2I timing source_id must be a nonempty receipt string")
    if payload["valid"] is not True:
        raise ValueError("V2I timing receipt is invalid")
    numeric_fields = (
        "phase_remaining_s",
        "decision_timestamp_s",
        "source_timestamp_s",
        "maximum_age_s",
    )
    if any(type(payload[name]) not in (int, float) for name in numeric_fields):
        raise ValueError("V2I timing receipt numeric fields must be native numbers")
    values = np.asarray([payload[name] for name in numeric_fields], dtype=np.float64)
    if not np.isfinite(values).all():
        raise ValueError("V2I timing receipt must be finite")
    phase_remaining, decision_timestamp, source_timestamp, maximum_age = (
        float(value) for value in values
    )
    if phase_remaining < 0.0 or maximum_age <= 0.0:
        raise ValueError("V2I phase remaining and maximum age are invalid")
    if source_timestamp > decision_timestamp:
        raise ValueError("V2I source timestamp cannot be in the future")
    age = decision_timestamp - source_timestamp
    if age > maximum_age:
        raise ValueError("V2I timing receipt is stale")
    if not regulatory_signal_mapped:
        raise ValueError("V2I timing requires a mapped current regulatory signal")
    return phase_remaining, True, {
        "mode": "v2i_current_time",
        "source_id": source_id,
        "decision_timestamp_s": decision_timestamp,
        "source_timestamp_s": source_timestamp,
        "age_s": age,
        "maximum_age_s": maximum_age,
        "fresh": True,
        "valid": True,
        "phase_remaining_available": True,
        "regulatory_signal_mapped": True,
    }


def fit_train_context_scaler(
    raw_contexts: np.ndarray,
    *,
    source_complete: np.ndarray | None = None,
    record_weights: np.ndarray | None = None,
    lower_quantile: float = 0.05,
    upper_quantile: float = 0.95,
    minimum_span: float = 1e-6,
) -> V25ContextScaler:
    values = _raw_matrix(raw_contexts)
    if values.shape[0] < 2:
        raise ValueError("train-only context scaling requires at least two records.")
    if not 0.0 <= lower_quantile < upper_quantile <= 1.0:
        raise ValueError("context scaler quantiles must satisfy 0<=low<high<=1.")
    if not np.isfinite(minimum_span) or minimum_span <= 0.0:
        raise ValueError("minimum_span must be finite and positive.")
    if source_complete is None:
        available = np.ones(values.shape, dtype=np.bool_)
    else:
        available = _strict_context_source_complete(source_complete, values.shape)
    weights = _context_record_weights(record_weights, values.shape[0])
    q05 = np.empty(RAW_FEATURE_COUNT, dtype=np.float64)
    q95 = np.empty(RAW_FEATURE_COUNT, dtype=np.float64)
    for feature_index in range(RAW_FEATURE_COUNT):
        mask = available[:, feature_index]
        if not np.any(mask):
            # This span is never consumed because the availability-aware lift
            # zeros both columns.  Keeping a fixed [0,1] span avoids treating
            # an unavailable no-V2I feature as observed zero support.
            q05[feature_index] = 0.0
            q95[feature_index] = 1.0
            continue
        q05[feature_index] = _weighted_context_quantile(
            values[mask, feature_index], weights[mask], lower_quantile
        )
        q95[feature_index] = _weighted_context_quantile(
            values[mask, feature_index], weights[mask], upper_quantile
        )
    q95 = np.maximum(q95, q05 + float(minimum_span))
    return V25ContextScaler(q05=q05, q95=q95)


def complement_lift(unit_context: np.ndarray) -> np.ndarray:
    values = _raw_matrix(unit_context)
    if np.any(values < -1e-12) or np.any(values > 1.0 + 1e-12):
        raise ValueError("normalized V25 context must lie in [0,1].")
    clipped = np.clip(values, 0.0, 1.0)
    lifted = np.empty((values.shape[0], PHI_DIMENSION), dtype=np.float64)
    lifted[:, 0] = 1.0
    lifted[:, 1::2] = clipped
    lifted[:, 2::2] = 1.0 - clipped
    lifted /= float(1 + RAW_FEATURE_COUNT)
    validate_phi(lifted)
    return lifted[0] if np.asarray(unit_context).ndim == 1 else lifted


def masked_complement_lift(
    unit_context: np.ndarray,
    source_complete: np.ndarray,
) -> np.ndarray:
    """Lift only source-complete current-tick context onto the simplex.

    Unavailable features contribute neither ``x`` nor ``1-x``.  The intercept
    and each available complement pair contribute one unit before row-wise
    normalization, so ``phi`` remains a simplex without softmax or runtime
    projection.  With all features available this is exactly
    :func:`complement_lift`.
    """

    values = _raw_matrix(unit_context)
    if np.any(values < -1e-12) or np.any(values > 1.0 + 1e-12):
        raise ValueError("normalized V25 context must lie in [0,1].")
    available = _strict_context_source_complete(source_complete, values.shape)
    clipped = np.clip(values, 0.0, 1.0)
    lifted = np.zeros((values.shape[0], PHI_DIMENSION), dtype=np.float64)
    lifted[:, 0] = 1.0
    lifted[:, 1::2] = np.where(available, clipped, 0.0)
    lifted[:, 2::2] = np.where(available, 1.0 - clipped, 0.0)
    lifted /= (1.0 + np.sum(available, axis=1, keepdims=True))
    validate_phi(lifted)
    return lifted[0] if np.asarray(unit_context).ndim == 1 else lifted


def validate_phi(phi: np.ndarray, *, atol: float = 1e-10) -> None:
    values = np.asarray(phi, dtype=np.float64)
    if values.ndim == 1:
        values = values.reshape(1, -1)
    if values.ndim != 2 or values.shape[1] != PHI_DIMENSION:
        raise ValueError(f"phi must have shape [N,{PHI_DIMENSION}].")
    if not np.all(np.isfinite(values)) or np.any(values < -atol):
        raise ValueError("phi must be finite and nonnegative.")
    if not np.allclose(values.sum(axis=1), 1.0, rtol=0.0, atol=atol):
        raise ValueError("every phi row must sum to one.")


def validate_column_simplex_theta(
    theta: np.ndarray,
    *,
    num_atoms: int | None = None,
    atol: float = 1e-8,
) -> np.ndarray:
    values = np.asarray(theta, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != PHI_DIMENSION:
        raise ValueError(
            f"V25 Theta must have shape [num_atoms,{PHI_DIMENSION}]."
        )
    if num_atoms is not None and values.shape[0] != int(num_atoms):
        raise ValueError("V25 Theta atom dimension mismatch.")
    if not np.all(np.isfinite(values)) or np.any(values < -atol):
        raise ValueError("every V25 Theta column must be finite and nonnegative.")
    if not np.allclose(values.sum(axis=0), 1.0, rtol=0.0, atol=atol):
        raise ValueError("every V25 Theta column must sum to one.")
    return values


def context_weights(theta: np.ndarray, phi: np.ndarray) -> np.ndarray:
    theta_values = validate_column_simplex_theta(theta)
    phi_values = np.asarray(phi, dtype=np.float64)
    one = phi_values.ndim == 1
    validate_phi(phi_values)
    if one:
        phi_values = phi_values.reshape(1, -1)
    weights = phi_values @ theta_values.T
    if np.any(weights < -1e-9) or not np.allclose(
        weights.sum(axis=1), 1.0, rtol=0.0, atol=1e-8
    ):
        raise ValueError("V25 context head violated the simplex guarantee.")
    return weights[0] if one else weights


def _raw_matrix(raw: np.ndarray) -> np.ndarray:
    values = np.asarray(raw, dtype=np.float64)
    if values.ndim == 1:
        values = values.reshape(1, -1)
    if values.ndim != 2 or values.shape[1] != RAW_FEATURE_COUNT:
        raise ValueError(f"raw context must have shape [N,{RAW_FEATURE_COUNT}].")
    if not np.all(np.isfinite(values)):
        raise ValueError("raw context must contain only finite values.")
    return values


def _strict_context_source_complete(
    source_complete: np.ndarray,
    shape: tuple[int, int],
) -> np.ndarray:
    available = np.asarray(source_complete)
    if available.dtype != np.bool_:
        raise ValueError("context source_complete must contain native booleans")
    if available.ndim == 1:
        available = available.reshape(1, -1)
    if available.shape != shape:
        raise ValueError(f"context source_complete must have shape {shape}")
    return available


def _context_record_weights(
    record_weights: np.ndarray | None,
    size: int,
) -> np.ndarray:
    if record_weights is None:
        return np.full(size, 1.0 / size, dtype=np.float64)
    values = np.asarray(record_weights)
    if (
        values.shape != (size,)
        or values.dtype.kind not in "fiu"
        or values.dtype.kind == "b"
    ):
        raise ValueError("context record_weights must be native numeric [N]")
    values = values.astype(np.float64, copy=False)
    if not np.all(np.isfinite(values)) or np.any(values <= 0.0):
        raise ValueError("context record_weights must be finite strictly positive")
    total = float(values.sum())
    if not np.isfinite(total) or total <= 0.0:
        raise ValueError("context record_weights must have finite positive total")
    return values / total


def _weighted_context_quantile(
    values: np.ndarray,
    weights: np.ndarray,
    quantile: float,
) -> float:
    order = np.argsort(values, kind="mergesort")
    ordered = np.asarray(values, dtype=np.float64)[order]
    mass = np.asarray(weights, dtype=np.float64)[order]
    cumulative = np.cumsum(mass)
    threshold = float(quantile) * float(cumulative[-1])
    index = int(np.searchsorted(cumulative, threshold, side="left"))
    return float(ordered[min(index, ordered.size - 1)])


def _ordered_route_rows(route_lanes: Any) -> tuple[np.ndarray, np.ndarray]:
    route = np.asarray(route_lanes, dtype=np.float64)
    if route.shape != (25, 20, 33) or not np.all(np.isfinite(route)):
        raise ValueError("route_lanes must be finite with shape [25,20,33].")
    rows: list[np.ndarray] = []
    for slot in route:
        valid = np.any(np.abs(slot[:, :8]) > 1e-8, axis=1)
        if valid.any():
            rows.extend(slot[valid])
    if len(rows) < 3:
        raise ValueError("route context requires at least three visible route points.")
    values = np.asarray(rows, dtype=np.float64)
    keep = np.r_[True, np.linalg.norm(np.diff(values[:, :2], axis=0), axis=1) > 1e-8]
    values = values[keep]
    if values.shape[0] < 3:
        raise ValueError("route context requires three distinct route points.")
    arc = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(values[:, :2], axis=0), axis=1))]
    return values, arc


def _route_curvature(points: np.ndarray) -> np.ndarray:
    deltas = np.diff(points, axis=0)
    lengths = np.linalg.norm(deltas, axis=1)
    if np.any(lengths <= 1e-8):
        raise ValueError("route context contains a zero-length segment.")
    headings = np.unwrap(np.arctan2(deltas[:, 1], deltas[:, 0]))
    curvature = np.zeros(points.shape[0], dtype=np.float64)
    if headings.size > 1:
        interior = np.abs(np.diff(headings)) / np.maximum(
            0.5 * (lengths[:-1] + lengths[1:]), 1e-8
        )
        curvature[1:-1] = interior
        curvature[0] = interior[0]
        curvature[-1] = interior[-1]
    return curvature


def _candidate_route_progress(candidates_xy: np.ndarray, route_xy: np.ndarray) -> np.ndarray:
    deltas = np.diff(route_xy, axis=0)
    lengths = np.linalg.norm(deltas, axis=1)
    valid = lengths > 1e-8
    if not valid.any():
        raise ValueError("route context has no projectable segment.")
    starts = route_xy[:-1][valid]
    directions = deltas[valid] / lengths[valid, None]
    segment_lengths = lengths[valid]
    full_arc = np.r_[0.0, np.cumsum(lengths)]
    arc_starts = full_arc[:-1][valid]
    result = np.empty(candidates_xy.shape[0], dtype=np.float64)
    for candidate_index, points in enumerate(candidates_xy):
        relative = points[:, None, :] - starts[None, :, :]
        along = np.clip(
            np.einsum("tsd,sd->ts", relative, directions),
            0.0,
            segment_lengths[None, :],
        )
        projections = starts[None, :, :] + directions[None, :, :] * along[:, :, None]
        nearest = np.argmin(
            np.linalg.norm(points[:, None, :] - projections, axis=2), axis=1
        )
        projected_arc = arc_starts[nearest] + along[np.arange(points.shape[0]), nearest]
        result[candidate_index] = float(np.max(projected_arc))
    return result


def _route_signal_context(
    route_rows: np.ndarray, route_arc: np.ndarray
) -> tuple[str, float, bool]:
    states = route_rows[:, 8:13]
    known = np.flatnonzero(np.sum(states[:, :4], axis=1) > 0.5)
    if known.size == 0:
        return "unknown", float(route_arc[-1]), False
    index = int(known[0])
    state_index = int(np.argmax(states[index, :4]))
    phase = ("green", "yellow", "red", "unknown")[state_index]
    return phase, float(route_arc[index]), True


def _resolved_signal_context(
    route_rows: np.ndarray,
    route_arc: np.ndarray,
    *,
    causal_signal_atom_input: Mapping[str, Any] | None,
) -> tuple[str, float, bool]:
    phase, distance, known = _route_signal_context(route_rows, route_arc)
    if causal_signal_atom_input is None:
        return phase, distance, known
    signal = validate_causal_signal_atom_input(causal_signal_atom_input)
    if signal["source_state"] == "not_applicable":
        if known:
            raise ValueError("no-signal authority conflicts with route signal rows")
        return phase, distance, known
    current_phase = str(signal["current_phase"])
    if known:
        if phase != current_phase:
            raise ValueError("route and certified current signal phases conflict")
        return phase, distance, known
    stop_line = np.asarray(signal["stop_line_geometry_ego_m"], dtype=np.float64)
    tangent = np.asarray(signal["route_tangent_ego"], dtype=np.float64)
    forward_distance = max(float(stop_line.mean(axis=0) @ tangent), 0.0)
    return current_phase, forward_distance, True


def _neighbor_context(neighbor_history: Any, ego_speed: float) -> tuple[tuple[float, ...], bool]:
    history = np.asarray(neighbor_history, dtype=np.float64)
    if history.shape != (32, 31, 11) or not np.all(np.isfinite(history)):
        raise ValueError("neighbor_agents_past must be finite with shape [32,31,11].")
    current = history[:, -1]
    active = (current[:, 6] > 0.0) & (current[:, 7] > 0.0)
    if not active.any():
        return (
            0.0,
            NO_NEIGHBOR_DISTANCE_M,
            NO_NEIGHBOR_TTC_S,
            0.0,
            NO_NEIGHBOR_DISTANCE_M,
        ), True
    rows = current[active]
    positions = rows[:, :2]
    distances = np.linalg.norm(positions, axis=1)
    relative_velocity = rows[:, 4:6] - np.array([ego_speed, 0.0])
    closing = -np.einsum("ij,ij->i", positions, relative_velocity) / np.maximum(
        distances, 1e-6
    )
    ttc = np.where(closing > 1e-6, distances / closing, NO_NEIGHBOR_TTC_S)
    closest = int(np.argmin(distances))
    return (
        float(rows.shape[0]),
        float(np.min(distances)),
        float(min(np.min(ttc), NO_NEIGHBOR_TTC_S)),
        float(closing[closest]),
        float(np.min(np.abs(positions[:, 1]))),
    ), True
