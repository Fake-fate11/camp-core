from __future__ import annotations

import copy

from scripts.integrations.analyze_diffusion_planner_matched_observable_descriptor_separability import (
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
)
from scripts.integrations.analyze_diffusion_planner_observable_descriptor_bottleneck import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze_records,
)


def _separability(status: str = "matched_observable_descriptor_separability_rejected") -> dict:
    return {
        "final_decision": {
            "status": status,
            "authorized_next_work": (
                "diagnose_observable_descriptor_bottleneck_before_new_replay"
            ),
            "primary_gap": "observable_descriptors_do_not_separate_beneficial_and_harmful_candidates",
        },
        "failure_gap": {
            "best_screen": {
                "screen_name": "route_heading_change_worse_vs_top1_rad:allow_low",
                "feature_names": ["route_heading_change_worse_vs_top1_rad"],
                "directions": ["allow_low"],
                "thresholds": [0.0],
            }
        },
    }


def _outcome(value: float, progress: float = 10.0, *, red: bool = False) -> dict:
    return {
        "value": value,
        "feasible": True,
        "progress_m": progress,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": red,
        "mean_jerk_mps3": 1.0,
        "mean_lateral_acceleration_mps2": 1.0,
    }


def _record(*, cls: str, heading_worse: float) -> dict:
    if cls == CLASS_HARMFUL:
        candidate = _outcome(-1.0, progress=9.0)
    elif cls == CLASS_BENEFICIAL:
        candidate = _outcome(1.0, progress=10.0)
    else:
        candidate = _outcome(0.0, progress=10.0)
    return {
        "num_candidates": 2,
        "seed": 1,
        "observable_state_logging": {
            "schema_version": "dp_camp_observable_state_logging_v1",
            "enabled": True,
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "candidate_count": 2,
            "finite_checks": {
                "candidate_route_projection_s_m": True,
                "candidate_route_lateral_error_m": True,
                "candidate_route_segment_index": True,
                "candidate_route_heading_change_rad": True,
                "candidate_min_obstacle_clearance_lower_bound_m": True,
                "candidate_obstacle_slot_count": True,
                "route_curvature_context_abs": True,
            },
            "candidate_route_projection_s_m": [[0.0, 1.0], [0.0, 1.0]],
            "candidate_route_lateral_error_m": [[0.0], [0.0]],
            "candidate_route_segment_index": [[0.0], [0.0]],
            "candidate_route_heading_change_rad": [[0.0], [heading_worse]],
            "candidate_min_obstacle_clearance_lower_bound_m": [5.0, 5.0],
            "candidate_obstacle_slot_count": [0.0, 0.0],
            "candidate_red_stopline_distance_m": None,
            "candidate_red_heading_alignment": None,
            "route_curvature_context_abs": [0.0, 0.0],
        },
        "candidate_closed_loop_outcomes": [
            _outcome(0.0),
            candidate,
        ],
    }


def _item(raw: dict) -> dict:
    return {
        "raw": raw,
        "context": {
            "log_path": "/tmp/route/seed_1/camp_selection_log.json",
            "record_index": 0,
            "path_seeds": [1],
        },
    }


def test_bottleneck_diagnostic_counts_allowed_harmful_and_blocked_beneficial() -> None:
    allowed_harmful = _record(cls=CLASS_HARMFUL, heading_worse=0.0)
    blocked_beneficial = _record(cls=CLASS_BENEFICIAL, heading_worse=1.0)

    report = analyze_records(
        [_item(allowed_harmful), _item(blocked_beneficial)],
        separability_report=_separability(),
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["counts"]["allowed_harmful"] == 1
    assert report["counts"]["blocked_beneficial"] == 1
    assert report["counts"]["allowed_harmful_reasons"]["progress_proxy_weakness"] == 1
    assert report["counts"]["blocked_beneficial_reasons"][
        "top1_shape_calibration_overconservative"
    ] == 1
    assert report["final_decision"]["new_replay_authorized"] is False


def test_bottleneck_diagnostic_blocks_when_source_not_rejected() -> None:
    source = copy.deepcopy(_separability("matched_observable_descriptor_separability_ready"))

    report = analyze_records([_item(_record(cls=CLASS_HARMFUL, heading_worse=0.0))], separability_report=source)

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
