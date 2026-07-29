from __future__ import annotations

import copy

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v26_nuplan_eligibility import (
    LEGACY_CONSTRAINT_PENDING,
    SOURCE_HISTORY_INELIGIBLE,
    V26NuPlanEligibilityError,
    build_v26_eligibility_manifest,
    derive_v26_targeted_recovery_ids,
    qualify_fixed_dp_history_window,
    qualify_v26_authoritative_route,
)
from camp_core.integrations.diffusion_planner_v26_nuplan_signal import (
    build_v26_nuplan_signal_authority,
)
from camp_core.integrations import nuplan_causal_adapter


def _route_lanes(*, lane_count: int = 1, lateral_margin: float = 1.0, gap_m: float = 1.0):
    route = np.zeros((25, 20, 33), dtype=np.float64)
    for lane_index in range(lane_count):
        start = lane_index * (19.0 + gap_m)
        x = np.linspace(start, start + 19.0, 20)
        route[lane_index, :, 0] = x
        route[lane_index, :, 2] = x + 1.0
        # A largely longitudinal boundary vector has a valid robust side sign
        # but triggers the historical V17 sine-margin diagnostic.
        route[lane_index, :, 4] = x + 1.0
        route[lane_index, :, 5] = lateral_margin
        route[lane_index, :, 6] = x + 1.0
        route[lane_index, :, 7] = -lateral_margin
    return route


def _mapping(lane_count: int):
    return [
        {
            "roadblock_id": f"rb{index}",
            "lane_fid": index + 1,
            "boundary_roles": {"left": 100 + index, "right": 200 + index},
        }
        for index in range(lane_count)
    ]


def _source_identity():
    return {
        "source_identity_sha256": "1" * 64,
        "source_db_sha256": "2" * 64,
        "map_sha256": "3" * 64,
        "mission_route_roadblock_chain_sha256": "4" * 64,
    }


def test_history_prefilter_retains_exact_fixed_input_window_and_excludes_short_history():
    full = qualify_fixed_dp_history_window(
        decision_timestamp_us=3_000_000,
        history_timestamps_us=range(0, 3_000_001, 100_000),
    )
    assert full["eligible"] is True
    assert full["fixed_input_steps"] == 31
    assert full["fixed_input_dt_us"] == 100_000

    short = qualify_fixed_dp_history_window(
        decision_timestamp_us=3_000_000,
        history_timestamps_us=range(100_000, 3_000_001, 100_000),
    )
    assert short["eligible"] is False
    assert short["classification"] == SOURCE_HISTORY_INELIGIBLE
    assert short["reason"] == "source_history_shorter_than_fixed_three_second_window"


def test_authoritative_route_keeps_legacy_margin_and_gap_as_diagnostics_without_tensor_mutation():
    route = _route_lanes(lane_count=2, lateral_margin=0.15, gap_m=20.0)
    original_bytes = route.tobytes()
    receipt = qualify_v26_authoritative_route(
        route_lanes=route,
        route_lane_mapping=_mapping(2),
        mission_roadblock_chain=("rb0", "rb1"),
    )
    assert receipt["eligible"] is True
    assert receipt["classification"] == LEGACY_CONSTRAINT_PENDING
    assert receipt["legacy_constraints"]["legacy_all_point_lateral_margin_triggered"]
    assert receipt["legacy_constraints"]["legacy_route_gap_triggered"]
    assert route.tobytes() == original_bytes


def test_authoritative_route_requires_boundary_roles_and_chain_membership():
    with pytest.raises(V26NuPlanEligibilityError, match="boundary roles"):
        qualify_v26_authoritative_route(
            route_lanes=_route_lanes(),
            route_lane_mapping=[{"roadblock_id": "rb0", "lane_fid": 1}],
            mission_roadblock_chain=("rb0",),
        )
    with pytest.raises(V26NuPlanEligibilityError, match="mission-roadblock chain"):
        qualify_v26_authoritative_route(
            route_lanes=_route_lanes(),
            route_lane_mapping=_mapping(1),
            mission_roadblock_chain=("rb1",),
        )


def test_signal_presence_is_distinct_from_same_tick_phase_availability():
    route = _route_lanes()
    no_signal = build_v26_nuplan_signal_authority(
        source_identity=_source_identity(),
        route_lanes=route,
        decision_timestamp_us=3_000_000,
        signal_present=False,
        same_tick_phase_available=False,
    )
    assert no_signal["source_state"] == "not_applicable"
    assert no_signal["same_tick_phase_availability"] == "not_applicable"
    assert no_signal["causal_signal_atom_input"]["source_valid"] is True

    phase_missing = build_v26_nuplan_signal_authority(
        source_identity=_source_identity(),
        route_lanes=route,
        decision_timestamp_us=3_000_000,
        signal_present=True,
        same_tick_phase_available=False,
    )
    assert phase_missing["source_state"] == "unavailable"
    assert phase_missing["signal_presence"] == "present"
    assert phase_missing["same_tick_phase_availability"] == "unavailable"
    assert phase_missing["causal_signal_atom_input"]["source_valid"] is False
    assert not nuplan_causal_adapter._has_authoritative_signal_stop_line_reference("[]")
    assert nuplan_causal_adapter._has_authoritative_signal_stop_line_reference("[123]")


def test_manifest_and_recovery_set_are_exact_once_without_payload_reads():
    history = qualify_fixed_dp_history_window(
        decision_timestamp_us=3_000_000,
        history_timestamps_us=range(0, 3_000_001, 100_000),
    )
    route = qualify_v26_authoritative_route(
        route_lanes=_route_lanes(),
        route_lane_mapping=_mapping(1),
        mission_roadblock_chain=("rb0",),
    )
    signal = {"signal_presence": "absent", "same_tick_phase_availability": "not_applicable"}
    short = copy.deepcopy(history)
    short["eligible"] = False
    short["classification"] = SOURCE_HISTORY_INELIGIBLE
    manifest = build_v26_eligibility_manifest(
        plan_sha256="a" * 64,
        anchor_records=(
            {"anchor_id": "a", "history": history, "route": route, "signal": signal},
            {"anchor_id": "b", "history": short, "route": route, "signal": signal},
        ),
    )
    assert manifest["planned_count"] == 2
    assert manifest["eligible_count"] == 1
    assert manifest["excluded_count"] == 1
    assert manifest["payload_read"] is False
    assert derive_v26_targeted_recovery_ids(
        legacy_rejected_anchor_ids=("a", "b", "missing"),
        eligibility_manifest=manifest,
        completed_anchor_ids=("a",),
    ) == ()
    assert derive_v26_targeted_recovery_ids(
        legacy_rejected_anchor_ids=("a", "b", "missing"),
        eligibility_manifest=manifest,
        completed_anchor_ids=(),
    ) == ("a",)
