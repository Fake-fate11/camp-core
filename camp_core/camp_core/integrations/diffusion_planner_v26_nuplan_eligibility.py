"""Outcome-blind V26 source eligibility for nuPlan corpus construction.

This module deliberately separates source eligibility from the legacy V17
fixed-input validator.  The latter may still reject an already assembled DP
tensor, but its historical 0.2 lateral-margin and 8 m route-gap checks are
recorded here only as diagnostics and never relabel raw nuPlan source data as
invalid.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


V26_NUPLAN_ELIGIBILITY_SCHEMA = "v26_nuplan_source_eligibility_v1"
FIXED_DP_HISTORY_STEPS = 31
FIXED_DP_HISTORY_DT_US = 100_000
FIXED_DP_HISTORY_SPAN_US = (FIXED_DP_HISTORY_STEPS - 1) * FIXED_DP_HISTORY_DT_US
SOURCE_HISTORY_INELIGIBLE = "source_history_ineligible_for_fixed_input"
LEGACY_CONSTRAINT_PENDING = "legacy_constraint_triggered_pending_v26_requalification"


class V26NuPlanEligibilityError(ValueError):
    """A source-side V26 eligibility failure with an explicit typed class."""

    def __init__(self, failure_class: str, message: str) -> None:
        super().__init__(message)
        self.failure_class = str(failure_class)


def _canonical_json_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalise_timestamps(timestamps_us: Iterable[int]) -> tuple[int, ...]:
    values = tuple(int(value) for value in timestamps_us)
    if not values:
        return values
    if any(right <= left for left, right in zip(values, values[1:])):
        raise V26NuPlanEligibilityError(
            "source_history_timestamp_order_invalid",
            "nuPlan source history timestamps must be strictly increasing",
        )
    return values


def qualify_fixed_dp_history_window(
    *,
    decision_timestamp_us: int,
    history_timestamps_us: Iterable[int],
) -> dict[str, Any]:
    """Check whether source timestamps can construct the fixed 31 x 0.1 s input.

    The check is identity/timestamp only.  It does not read trajectories,
    labels, candidate pools, or endpoint values.
    """

    decision_timestamp_us = int(decision_timestamp_us)
    timestamps = _normalise_timestamps(history_timestamps_us)
    target_start_us = decision_timestamp_us - FIXED_DP_HISTORY_SPAN_US
    base: dict[str, Any] = {
        "schema": V26_NUPLAN_ELIGIBILITY_SCHEMA,
        "kind": "fixed_dp_history_window",
        "fixed_input_steps": FIXED_DP_HISTORY_STEPS,
        "fixed_input_dt_us": FIXED_DP_HISTORY_DT_US,
        "fixed_input_span_us": FIXED_DP_HISTORY_SPAN_US,
        "decision_timestamp_us": decision_timestamp_us,
        "target_start_timestamp_us": target_start_us,
        "history_sample_count": len(timestamps),
        "history_first_timestamp_us": timestamps[0] if timestamps else None,
        "history_last_timestamp_us": timestamps[-1] if timestamps else None,
    }

    reason: str | None = None
    if len(timestamps) < 2:
        reason = "fewer_than_two_source_history_samples"
    elif timestamps[-1] != decision_timestamp_us:
        reason = "decision_timestamp_not_terminal_source_history_sample"
    elif timestamps[0] > target_start_us:
        reason = "source_history_shorter_than_fixed_three_second_window"

    if reason is not None:
        return {
            **base,
            "eligible": False,
            "classification": SOURCE_HISTORY_INELIGIBLE,
            "reason": reason,
        }

    return {
        **base,
        "eligible": True,
        "classification": None,
        "reason": None,
    }


def qualify_saved_state_history_window(
    *,
    db_path: str | Path,
    state_token: str,
    max_history_rows: int = 80,
) -> dict[str, Any]:
    """Read only nuPlan lidar timestamps needed for the manifest prefilter."""

    db_path = Path(db_path)
    with sqlite3.connect(str(db_path)) as connection:
        row = connection.execute(
            "SELECT scene_token, timestamp FROM lidar_pc WHERE token = ?",
            (str(state_token).encode("utf-8"),),
        ).fetchone()
        if row is None:
            raise V26NuPlanEligibilityError(
                "source_state_missing",
                f"state_token is absent from lidar_pc: {state_token}",
            )
        scene_token, decision_timestamp_us = row
        history_rows = connection.execute(
            """
            SELECT timestamp
            FROM lidar_pc
            WHERE scene_token = ? AND timestamp <= ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (scene_token, int(decision_timestamp_us), int(max_history_rows)),
        ).fetchall()
    timestamps = tuple(int(item[0]) for item in reversed(history_rows))
    receipt = qualify_fixed_dp_history_window(
        decision_timestamp_us=int(decision_timestamp_us),
        history_timestamps_us=timestamps,
    )
    return {
        **receipt,
        "state_token": str(state_token),
        "history_query_limit": int(max_history_rows),
    }


def _valid_route_lane_rows(route_lanes: np.ndarray) -> np.ndarray:
    if route_lanes.ndim != 3 or route_lanes.shape[-1] < 8:
        raise V26NuPlanEligibilityError(
            "ineligible_source_geometry",
            f"route_lanes must have shape (L, P, >=8), got {tuple(route_lanes.shape)}",
        )
    if not np.isfinite(route_lanes).all():
        raise V26NuPlanEligibilityError(
            "ineligible_source_geometry",
            "route_lanes contains a non-finite source geometry value",
        )
    valid = np.any(np.abs(route_lanes[..., :8]) > 1.0e-12, axis=(1, 2))
    if not valid.any():
        raise V26NuPlanEligibilityError(
            "ineligible_source_geometry",
            "route_lanes has no populated route-lane rows",
        )
    # A source route may have trailing empty slots, but not a gap between
    # populated slots; that would make its lane-to-source mapping ambiguous.
    first_empty = int(np.argmax(~valid)) if (~valid).any() else len(valid)
    if valid[first_empty:].any():
        raise V26NuPlanEligibilityError(
            "ineligible_source_geometry",
            "route_lanes has non-contiguous populated source-lane slots",
        )
    return route_lanes[:first_empty]


def _require_boundary_roles(
    route_lane_mapping: Sequence[Mapping[str, Any]],
    lane_count: int,
    roadblock_chain: Sequence[str],
) -> None:
    if len(route_lane_mapping) < lane_count:
        raise V26NuPlanEligibilityError(
            "ineligible_source_geometry",
            "route_lane_mapping is shorter than populated route-lane slots",
        )
    allowed_roadblocks = {str(value) for value in roadblock_chain}
    if not allowed_roadblocks:
        raise V26NuPlanEligibilityError(
            "ineligible_source_geometry",
            "mission-roadblock chain is empty",
        )
    for lane_index, mapping in enumerate(route_lane_mapping[:lane_count]):
        roadblock_id = str(mapping.get("roadblock_id", ""))
        roles = mapping.get("boundary_roles")
        if roadblock_id not in allowed_roadblocks:
            raise V26NuPlanEligibilityError(
                "ineligible_source_geometry",
                f"route lane {lane_index} is not bound to the mission-roadblock chain",
            )
        if not isinstance(roles, Mapping) or not roles.get("left") or not roles.get("right"):
            raise V26NuPlanEligibilityError(
                "ineligible_source_geometry",
                f"route lane {lane_index} lacks authoritative left/right boundary roles",
            )


def qualify_v26_authoritative_route(
    *,
    route_lanes: np.ndarray,
    route_lane_mapping: Sequence[Mapping[str, Any]],
    mission_roadblock_chain: Sequence[str],
) -> dict[str, Any]:
    """Apply V26 source qualification without inheriting V17 0.2/8 m gates.

    The authoritative checks are: mission-roadblock membership, explicit
    boundary roles, finite non-zero width, and a robust left/right orientation
    check.  Legacy constraints are returned as diagnostics only.
    """

    lanes = _valid_route_lane_rows(np.asarray(route_lanes, dtype=np.float64))
    chain = tuple(str(value) for value in mission_roadblock_chain)
    if len(set(chain)) != len(chain):
        raise V26NuPlanEligibilityError(
            "ineligible_source_geometry",
            "mission-roadblock chain contains a repeated authoritative roadblock",
        )
    _require_boundary_roles(route_lane_mapping, len(lanes), chain)

    robust_side_checks: list[dict[str, Any]] = []
    legacy_margin_triggered = False
    for lane_index, lane in enumerate(lanes):
        direction = lane[:, 2:4] - lane[:, 0:2]
        left = lane[:, 4:6] - lane[:, 0:2]
        right = lane[:, 6:8] - lane[:, 0:2]
        direction_norm = np.linalg.norm(direction, axis=1)
        left_norm = np.linalg.norm(left, axis=1)
        right_norm = np.linalg.norm(right, axis=1)
        if np.any(direction_norm <= 1.0e-9):
            raise V26NuPlanEligibilityError(
                "ineligible_source_geometry",
                f"route lane {lane_index} has a zero-length authoritative direction",
            )
        if np.any(left_norm <= 1.0e-9) or np.any(right_norm <= 1.0e-9):
            raise V26NuPlanEligibilityError(
                "ineligible_source_geometry",
                f"route lane {lane_index} has zero authoritative boundary width",
            )
        left_cross = direction[:, 0] * left[:, 1] - direction[:, 1] * left[:, 0]
        right_cross = direction[:, 0] * right[:, 1] - direction[:, 1] * right[:, 0]
        # Robust side semantics use quantiles rather than a V17 per-point
        # margin threshold.  A single sampled boundary artefact cannot flip a
        # whole authoritative lane when the signed geometry remains coherent.
        left_q10 = float(np.quantile(left_cross, 0.10))
        right_q90 = float(np.quantile(right_cross, 0.90))
        if left_q10 <= 0.0 or right_q90 >= 0.0:
            raise V26NuPlanEligibilityError(
                "ineligible_source_geometry",
                f"route lane {lane_index} fails robust authoritative side orientation",
            )
        left_sine = left_cross / (direction_norm * left_norm)
        right_sine = right_cross / (direction_norm * right_norm)
        legacy_margin_triggered = legacy_margin_triggered or bool(
            np.any(left_sine <= 0.2) or np.any(right_sine >= -0.2)
        )
        robust_side_checks.append(
            {
                "lane_index": lane_index,
                "left_cross_q10": left_q10,
                "right_cross_q90": right_q90,
                "minimum_total_width": float(np.min(left_norm + right_norm)),
            }
        )

    route_centers = lanes[:, 0, :2]
    route_gaps = np.linalg.norm(np.diff(route_centers, axis=0), axis=1)
    max_route_gap_m = float(np.max(route_gaps)) if len(route_gaps) else 0.0
    legacy_gap_triggered = bool(max_route_gap_m > 8.0)
    legacy_triggered = legacy_margin_triggered or legacy_gap_triggered
    return {
        "schema": V26_NUPLAN_ELIGIBILITY_SCHEMA,
        "kind": "authoritative_route_qualification",
        "eligible": True,
        "classification": (
            LEGACY_CONSTRAINT_PENDING if legacy_triggered else "v26_authoritative_source_eligible"
        ),
        "mission_roadblock_chain": list(chain),
        "lane_count": int(len(lanes)),
        "robust_side_checks": robust_side_checks,
        "legacy_constraints": {
            "legacy_all_point_lateral_margin_threshold": 0.2,
            "legacy_all_point_lateral_margin_triggered": legacy_margin_triggered,
            "legacy_route_gap_threshold_m": 8.0,
            "legacy_route_gap_triggered": legacy_gap_triggered,
            "legacy_max_route_gap_m": max_route_gap_m,
            "label": LEGACY_CONSTRAINT_PENDING if legacy_triggered else None,
        },
    }


def build_v26_eligibility_manifest(
    *,
    plan_sha256: str,
    anchor_records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind all planned identities to zero-model V26 eligibility receipts."""

    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in anchor_records:
        anchor_id = str(item["anchor_id"])
        if anchor_id in seen:
            raise V26NuPlanEligibilityError(
                "eligibility_manifest_duplicate_anchor",
                f"duplicate anchor_id in eligibility manifest: {anchor_id}",
            )
        seen.add(anchor_id)
        history = dict(item["history"])
        route = dict(item["route"])
        signal = dict(item["signal"])
        eligible = bool(history.get("eligible")) and bool(route.get("eligible"))
        if not bool(history.get("eligible")):
            exclusion_class = str(history.get("classification") or SOURCE_HISTORY_INELIGIBLE)
        elif not bool(route.get("eligible")):
            exclusion_class = str(route.get("classification") or "ineligible_source_geometry")
        else:
            exclusion_class = None
        records.append(
            {
                "anchor_id": anchor_id,
                "eligible": eligible,
                "exclusion_class": exclusion_class,
                "history": history,
                "route": route,
                "signal": signal,
            }
        )
    records.sort(key=lambda item: item["anchor_id"])
    classifications = Counter(
        str(record["exclusion_class"])
        for record in records
        if record["exclusion_class"] is not None
    )
    payload: dict[str, Any] = {
        "schema": V26_NUPLAN_ELIGIBILITY_SCHEMA,
        "kind": "v26_eligibility_manifest",
        "plan_sha256": str(plan_sha256),
        "planned_count": len(records),
        "eligible_count": sum(1 for record in records if record["eligible"]),
        "excluded_count": sum(1 for record in records if not record["eligible"]),
        "excluded_by_class": dict(sorted(classifications.items())),
        "records": records,
        "payload_read": False,
        "model_call_count": 0,
        "dp_call_count": 0,
        "gpu_call_count": 0,
        "pool_generation_count": 0,
    }
    payload["eligibility_manifest_sha256"] = _canonical_json_sha256(payload)
    return payload


def derive_v26_targeted_recovery_ids(
    *,
    legacy_rejected_anchor_ids: Iterable[str],
    eligibility_manifest: Mapping[str, Any],
    completed_anchor_ids: Iterable[str],
) -> tuple[str, ...]:
    """Return exactly legacy-rejected ∩ amended-eligible ∩ not-complete."""

    eligible = {
        str(record["anchor_id"])
        for record in eligibility_manifest.get("records", ())
        if bool(record.get("eligible"))
    }
    legacy_rejected = {str(value) for value in legacy_rejected_anchor_ids}
    completed = {str(value) for value in completed_anchor_ids}
    return tuple(sorted((legacy_rejected & eligible) - completed))
