from __future__ import annotations

import copy
import json

import pytest

from scripts.integrations.analyze_diffusion_planner_matched_observable_descriptor_separability import (
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
)
from scripts.integrations.analyze_diffusion_planner_route_progress_support_envelope import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    analyze_records,
)


def _bottleneck(status: str = "observable_descriptor_bottleneck_diagnosed") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status == "observable_descriptor_bottleneck_diagnosed",
            "authorized_next_work": (
                "predeclare_next_descriptor_family_or_reject_observable_route"
            ),
        },
        "counts": {
            "dominant_allowed_harmful_reason": "progress_proxy_weakness",
            "dominant_blocked_beneficial_reason": (
                "top1_shape_calibration_overconservative"
            ),
        },
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": f"/tmp/route/seed_{seed}/camp_selection_log.json",
        "record_index": 0,
        "path_seeds": [seed],
    }


def _outcome(value: float, progress: float = 10.0) -> dict:
    return {
        "value": value,
        "feasible": True,
        "progress_m": progress,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
        "mean_jerk_mps3": 1.0,
        "mean_lateral_acceleration_mps2": 1.0,
    }


def _payload(candidate_projection: list[float], candidate_lateral: list[float]) -> dict:
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
            [0.0, 1.0, 2.0, 3.0],
            candidate_projection,
        ],
        "candidate_route_lateral_error_m": [
            [0.0, 0.0, 0.0, 0.0],
            candidate_lateral,
        ],
        "candidate_route_segment_index": [
            [0.0, 1.0, 2.0, 3.0],
            [0.0, 1.0, 2.0, 3.0],
        ],
        "candidate_route_heading_change_rad": [
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0],
        ],
        "candidate_min_obstacle_clearance_lower_bound_m": [5.0, 5.0],
        "candidate_obstacle_slot_count": [0.0, 0.0],
        "candidate_red_stopline_distance_m": None,
        "candidate_red_heading_alignment": None,
        "route_curvature_context_abs": [0.0, 0.0],
    }


def _record(*, cls: str, projection_loss: float, lateral: float = 0.0, seed: int = 1) -> dict:
    if cls == CLASS_HARMFUL:
        candidate = _outcome(-1.0, progress=9.0)
    elif cls == CLASS_BENEFICIAL:
        candidate = _outcome(1.0, progress=10.0)
    else:
        candidate = _outcome(0.0, progress=10.0)
    return {
        "num_candidates": 2,
        "seed": seed,
        "observable_state_logging": _payload(
            [0.0, 1.0, 2.0 - projection_loss, 3.0 - projection_loss],
            [0.0, lateral, lateral, lateral],
        ),
        "candidate_closed_loop_outcomes": [
            _outcome(0.0),
            candidate,
        ],
    }


def _item(raw: dict, seed: int = 1) -> dict:
    return {"raw": raw, "context": _context(seed)}


def test_route_progress_support_envelope_finds_toy_separator() -> None:
    items = [
        _item(_record(cls=CLASS_BENEFICIAL, projection_loss=0.0)),
        _item(_record(cls=CLASS_BENEFICIAL, projection_loss=0.05)),
        _item(_record(cls=CLASS_HARMFUL, projection_loss=1.0)),
        _item(_record(cls=CLASS_HARMFUL, projection_loss=1.5)),
    ]

    report = analyze_records(
        items,
        bottleneck_report=_bottleneck(),
        min_beneficial_candidates=2,
        min_harmful_candidates=2,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["analysis"]["future_outcome_labels_used_for_descriptors"] is False
    assert report["analysis"]["thresholds_are_offline_oracle_diagnostics"] is True
    assert report["final_decision"]["online_selector_authorized"] is False
    best = report["ranked_screens"][0]
    assert best["promising_screen"] is True
    assert best["harmful_block_rate"] == 1.0
    assert best["beneficial_retain_rate"] == 1.0


def test_route_progress_support_envelope_blocks_when_bottleneck_not_ready() -> None:
    source = copy.deepcopy(_bottleneck("observable_descriptor_bottleneck_source_not_ready"))

    report = analyze_records(
        [_item(_record(cls=CLASS_HARMFUL, projection_loss=1.0))],
        bottleneck_report=source,
        min_beneficial_candidates=0,
        min_harmful_candidates=1,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_route_progress_support_envelope_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [_item(_record(cls=CLASS_HARMFUL, projection_loss=1.0, seed=11), seed=11)],
            bottleneck_report=_bottleneck(),
            fail_on_formal_seeds=True,
            min_beneficial_candidates=0,
            min_harmful_candidates=1,
        )


def test_route_progress_support_descriptors_are_outcome_independent() -> None:
    base = _record(cls=CLASS_BENEFICIAL, projection_loss=0.1)
    mutated = copy.deepcopy(base)
    mutated["candidate_closed_loop_outcomes"][1]["mean_jerk_mps3"] = 99.0

    base_report = analyze_records(
        [_item(base)],
        bottleneck_report=_bottleneck(),
        min_beneficial_candidates=1,
        min_harmful_candidates=0,
    )
    mutated_report = analyze_records(
        [_item(mutated)],
        bottleneck_report=_bottleneck(),
        min_beneficial_candidates=1,
        min_harmful_candidates=0,
    )

    assert base_report["feature_coverage"] == mutated_report["feature_coverage"]
    assert base_report["feature_reports"] == mutated_report["feature_reports"]


def test_route_progress_support_cli_reads_selection_log(tmp_path) -> None:
    log_path = tmp_path / "route" / "seed_1" / "camp_selection_log.json"
    log_path.parent.mkdir(parents=True)
    log_path.write_text(
        json.dumps(
            [
                _record(cls=CLASS_BENEFICIAL, projection_loss=0.0),
                _record(cls=CLASS_HARMFUL, projection_loss=1.0),
            ]
        ),
        encoding="utf-8",
    )
    output_json = tmp_path / "envelope.json"

    report = analyze(
        [log_path],
        bottleneck_report=_bottleneck(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
        fail_on_formal_seeds=True,
    )
    output_json.write_text(json.dumps(report), encoding="utf-8")

    assert json.loads(output_json.read_text(encoding="utf-8"))["final_decision"][
        "status"
    ] == READY_STATUS
