from __future__ import annotations

import copy
import json

import pytest

from scripts.integrations.analyze_diffusion_planner_affine_allowed_harmful_residual import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    analyze_records,
)


def _affine_source(status: str = "constrained_affine_upper_bound_rejected") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": False,
            "primary_gap": "constrained_affine_upper_bound_does_not_separate_candidates",
            "authorized_next_work": "reject_observable_route_or_design_new_logging_preflight",
        },
        "failure_gap": {
            "primary_gap": "allowed_harmful_rate_too_high",
            "best_screen": {
                "screen_name": "observable.route_projection_loss_vs_top1_m.low_risk:allow_low",
                "feature_names": ["observable.route_projection_loss_vs_top1_m.low_risk"],
                "directions": ["allow_low"],
                "thresholds": [0.1],
                "nonnegative_simplex_weights": {
                    "observable.route_projection_loss_vs_top1_m.low_risk": 1.0,
                },
            },
        },
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": f"/tmp/route/seed_{seed}/camp_selection_log.json",
        "record_index": 0,
        "path_seeds": [seed],
    }


def _outcome(
    value: float = 0.0,
    progress: float = 10.0,
    *,
    red: bool = False,
    lane: bool = False,
    collision: bool = False,
    near_miss: bool = False,
    jerk: float = 1.0,
    lateral_acc: float = 1.0,
) -> dict:
    return {
        "value": value,
        "feasible": True,
        "progress_m": progress,
        "collision": collision,
        "near_miss": near_miss,
        "lane_violation": lane,
        "red_light_violation": red,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral_acc,
    }


def _payload(projection_loss: float) -> dict:
    return {
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
        "candidate_route_projection_s_m": [
            [0.0, 1.0, 2.0],
            [0.0, 1.0, 2.0 - projection_loss],
        ],
        "candidate_route_lateral_error_m": [[0.0, 0.0], [0.0, 0.0]],
        "candidate_route_segment_index": [[0.0, 1.0], [0.0, 1.0]],
        "candidate_route_heading_change_rad": [[0.0, 0.0], [0.0, 0.0]],
        "candidate_min_obstacle_clearance_lower_bound_m": [5.0, 5.0],
        "candidate_obstacle_slot_count": [0.0, 0.0],
        "candidate_red_stopline_distance_m": None,
        "candidate_red_heading_alignment": None,
        "route_curvature_context_abs": [0.0, 0.0],
    }


def _record(candidate_outcome: dict, projection_loss: float, *, seed: int = 1) -> dict:
    return {
        "num_candidates": 2,
        "seed": seed,
        "observable_state_logging": _payload(projection_loss),
        "candidate_closed_loop_outcomes": [
            _outcome(),
            candidate_outcome,
        ],
    }


def _item(raw: dict, seed: int = 1) -> dict:
    return {"raw": raw, "context": _context(seed)}


def test_allowed_harmful_residual_counts_red_and_progress_reasons() -> None:
    items = [
        _item(_record(_outcome(value=1.0), projection_loss=0.0)),
        _item(_record(_outcome(red=True), projection_loss=0.0)),
        _item(_record(_outcome(progress=9.0), projection_loss=0.0)),
        _item(_record(_outcome(value=-1.0), projection_loss=2.0)),
    ]

    report = analyze_records(items, constrained_affine_report=_affine_source())

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["analysis"]["training"] is False
    assert report["analysis"]["future_outcome_labels_used_for_descriptors"] is False
    assert report["screen_application"]["allowed_harmful"] == 2
    residual = report["residual_allowed_harmful"]
    assert residual["count"] == 2
    assert residual["primary_reason_counts"]["progress_loss"] == 1
    assert residual["primary_reason_counts"]["red_light_violation"] == 1
    assert report["final_decision"]["online_selector_authorized"] is False


def test_allowed_harmful_residual_blocks_when_source_not_ready() -> None:
    source = copy.deepcopy(_affine_source("constrained_affine_upper_bound_ready"))
    source["final_decision"]["passed"] = True

    report = analyze_records(
        [_item(_record(_outcome(value=-1.0), projection_loss=0.0))],
        constrained_affine_report=source,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_allowed_harmful_residual_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [
                _item(
                    _record(_outcome(value=-1.0), projection_loss=0.0, seed=11),
                    seed=11,
                )
            ],
            constrained_affine_report=_affine_source(),
            fail_on_formal_seeds=True,
        )


def test_allowed_harmful_screen_application_is_outcome_independent() -> None:
    base = _record(_outcome(value=1.0), projection_loss=0.0)
    mutated = copy.deepcopy(base)
    mutated["candidate_closed_loop_outcomes"][1]["mean_jerk_mps3"] = 99.0

    base_report = analyze_records(
        [_item(base)],
        constrained_affine_report=_affine_source(),
    )
    mutated_report = analyze_records(
        [_item(mutated)],
        constrained_affine_report=_affine_source(),
    )

    assert base_report["screen_application"] == mutated_report["screen_application"]
    assert base_report["selected_screen"] == mutated_report["selected_screen"]


def test_allowed_harmful_residual_cli_reads_selection_log(tmp_path) -> None:
    log_path = tmp_path / "route" / "seed_1" / "camp_selection_log.json"
    log_path.parent.mkdir(parents=True)
    log_path.write_text(
        json.dumps(
            [
                _record(_outcome(value=1.0), projection_loss=0.0),
                _record(_outcome(red=True), projection_loss=0.0),
                _record(_outcome(value=-1.0), projection_loss=2.0),
            ]
        ),
        encoding="utf-8",
    )

    report = analyze(
        [log_path],
        constrained_affine_report=_affine_source(),
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["residual_allowed_harmful"]["primary_reason_counts"][
        "red_light_violation"
    ] == 1
