from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (
    PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS,
    build_progress_lane_hard_context_logging_payload,
)
from scripts.integrations.analyze_diffusion_planner_progress_lane_hard_context_payload_coverage import (
    BROADER_PLAN_NEXT_WORK,
    INSUFFICIENT_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    SEPARABILITY_NEXT_WORK,
    analyze,
)


def _route() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [2.0, 0.0],
            [3.0, 0.6],
            [4.0, 1.5],
            [5.0, 2.2],
        ],
        dtype=np.float64,
    )


def _candidates(offset: float = 0.0) -> np.ndarray:
    return np.asarray(
        [
            [
                [0.0, 0.0],
                [1.0, 0.0],
                [2.0, 0.0],
                [3.0, 0.6],
                [4.0, 1.5],
                [5.0, 2.2],
            ],
            [
                [0.0, 0.0],
                [1.0, 0.7 + offset],
                [2.0, 1.3 + offset],
                [3.0, 1.8 + offset],
                [4.0, 2.0 + offset],
                [5.0, 2.4 + offset],
            ],
            [
                [0.0, 0.0],
                [1.0, -0.3 - offset],
                [2.0, -0.5 - offset],
                [3.0, -0.4 - offset],
                [4.0, 0.0],
                [5.0, 0.6],
            ],
        ],
        dtype=np.float64,
    )


def _payload(offset: float = 0.0) -> dict:
    return build_progress_lane_hard_context_logging_payload(
        candidates=_candidates(offset=offset),
        route_centerline_ego=_route(),
        support_steps=6,
        dt_s=0.1,
        corridor_half_width_m=1.0,
        corridor_safety_margin_m=0.25,
    )


def _record(payload: dict) -> dict:
    record = {
        "candidate_closed_loop_outcomes": None,
        "progress_lane_hard_context_logging": payload,
    }
    for field in PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS:
        record[field] = payload["latency_ms"][field]
    return record


def _write_log(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records), encoding="utf-8")


def test_context_payload_coverage_validates_tiny_smoke_as_insufficient(
    tmp_path: Path,
) -> None:
    records = [_record(_payload(offset=float(index) * 0.01)) for index in range(3)]
    log_path = tmp_path / "logging_enabled" / "camp_selection_log.json"
    _write_log(log_path, records)

    report = analyze([log_path], label="tiny")

    assert report["validation"]["errors"] == []
    assert report["final_decision"]["status"] == INSUFFICIENT_STATUS
    assert report["final_decision"]["primary_gap"] == (
        "too_few_logged_records_for_materiality"
    )
    assert report["counts"]["payload_records"] == 3
    assert report["final_decision"]["authorized_next_work"] == BROADER_PLAN_NEXT_WORK
    assert report["final_decision"]["closed_loop_replay_authorized"] is False


def test_context_payload_coverage_rejects_future_outcome_leakage(
    tmp_path: Path,
) -> None:
    payload = _payload()
    payload["candidate_closed_loop_outcomes"] = [{"collision": True}]
    record = _record(payload)
    record["candidate_closed_loop_outcomes"] = [{"collision": False}]
    log_path = tmp_path / "camp_selection_log.json"
    _write_log(log_path, [record])

    report = analyze([log_path], min_records_for_materiality=1)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["validation_passed"] is False
    assert any("closed-loop outcome" in error for error in report["validation"]["errors"])
    assert report["final_decision"]["authorized_next_work"] is None


def test_context_payload_coverage_rejects_negative_atom(tmp_path: Path) -> None:
    payload = copy.deepcopy(_payload())
    payload["progress_lane_hard_context_atoms"][0][0] = -1.0
    payload["finite_checks"]["progress_lane_hard_context_atoms_nonnegative"] = False
    log_path = tmp_path / "camp_selection_log.json"
    _write_log(log_path, [_record(payload)])

    report = analyze([log_path], min_records_for_materiality=1)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert any("finite_checks failed" in error for error in report["validation"]["errors"])


def test_context_payload_coverage_accepts_sufficient_synthetic_materiality(
    tmp_path: Path,
) -> None:
    records = [
        _record(_payload(offset=float(index) * 0.02))
        for index in range(12)
    ]
    log_path = tmp_path / "seed_1" / "camp_selection_log.json"
    _write_log(log_path, records)

    report = analyze([tmp_path], label="sufficient")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["materiality_gate_passed"] is True
    assert len(report["material_atom_fields"]) >= 2
    assert report["context"]["context_records"] >= 1
    assert report["final_decision"]["authorized_next_work"] == SEPARABILITY_NEXT_WORK
    assert report["final_decision"]["full36_authorized"] is False
    assert report["analysis"]["future_outcome_leakage"] is False
