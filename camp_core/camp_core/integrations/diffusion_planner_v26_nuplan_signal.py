"""V26 official-nuPlan signal applicability receipts.

This adapter is intentionally limited to the source-bound case where current
traffic state exists but the official saved-state interface cannot bind a
stop-line geometry.  It marks exactly the red-light atoms unavailable; it
never recasts that condition as a certified no-signal route.
"""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from .diffusion_planner_v21_native import array_sha256
from .diffusion_planner_v25_semantic_authority import (
    CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION,
    canonical_json_sha256,
    validate_causal_signal_atom_input,
)


NUPLAN_V26_SIGNAL_APPLICABILITY_ADAPTER_ID = (
    "camp_dp_v26_official_nuplan_signal_applicability_adapter_v1"
)


def build_v26_nuplan_unavailable_signal_authority(
    *,
    source_identity: Mapping[str, Any],
    route_lanes: np.ndarray,
    decision_timestamp_us: int,
    traffic_light_state_available: bool,
) -> dict[str, Any]:
    required = {
        "source_identity_sha256",
        "source_db_sha256",
        "map_sha256",
        "mission_route_roadblock_chain_sha256",
    }
    if not required.issubset(source_identity):
        raise ValueError("official nuPlan signal source identity is incomplete")
    if isinstance(decision_timestamp_us, bool) or not isinstance(
        decision_timestamp_us, int
    ) or decision_timestamp_us < 0:
        raise ValueError("official signal decision timestamp is invalid")
    if not isinstance(traffic_light_state_available, bool):
        raise ValueError("official signal availability must be bool")
    route = np.ascontiguousarray(np.asarray(route_lanes, dtype=np.float64))
    if route.shape != (25, 20, 33) or not np.isfinite(route).all():
        raise ValueError("official signal route lanes must be finite [25,20,33]")
    route_geometry_sha256 = array_sha256(route)
    decision_time_s = float(decision_timestamp_us) / 1e6
    source_binding = {
        "adapter_id": NUPLAN_V26_SIGNAL_APPLICABILITY_ADAPTER_ID,
        "source_identity_sha256": str(source_identity["source_identity_sha256"]),
        "source_db_sha256": str(source_identity["source_db_sha256"]),
        "map_sha256": str(source_identity["map_sha256"]),
        "route_identity_sha256": str(
            source_identity["mission_route_roadblock_chain_sha256"]
        ),
        "route_geometry_sha256": route_geometry_sha256,
        "same_tick_traffic_light_state_available": traffic_light_state_available,
        "reason": "official_saved_state_has_no_source_bound_stop_line_geometry",
    }
    source_chain_sha256 = canonical_json_sha256(source_binding)
    runtime_receipt = {
        "schema_version": "camp_dp_v26_nuplan_signal_applicability_runtime_v1",
        "source_mode": "same_tick_signal_authority_unavailable_no_stopline_mapping",
        "source_state": "unavailable",
        "current_phase": "none",
        "decision_time_s": decision_time_s,
        "route_geometry_sha256": route_geometry_sha256,
        "source_chain_sha256": source_chain_sha256,
        "same_tick_traffic_light_state_available": traffic_light_state_available,
        "source_valid": False,
        "applicable": False,
    }
    causal_input = {
        "schema_version": CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION,
        "source_state": "unavailable",
        "source_valid": False,
        "applicable": False,
        "current_phase": "none",
        "decision_time_s": decision_time_s,
        "ego_position_world_m": None,
        "ego_heading_rad": None,
        "regulatory_element_id": None,
        "stop_line_id": None,
        "stop_line_geometry_world_m": None,
        "stop_line_geometry_ego_m": None,
        "stop_line_geometry_sha256": None,
        "route_tangent_world": None,
        "route_tangent_ego": None,
        "route_geometry_sha256": route_geometry_sha256,
        "route_arc_m": None,
        "source_chain_sha256": source_chain_sha256,
        "runtime_receipt": runtime_receipt,
        "runtime_receipt_sha256": canonical_json_sha256(runtime_receipt),
    }
    return {
        **source_binding,
        "source_state": "unavailable",
        "typed_missing_atoms": [
            "planned_red_light_cost",
            "red_stopping_margin_cost",
        ],
        "red_light_endpoint_status": "typed_missing_no_stopline_authority",
        "causal_signal_atom_input": validate_causal_signal_atom_input(
            causal_input,
            allow_unavailable=True,
        ),
    }
