from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (
    PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS,
    PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
    build_progress_lane_hard_context_logging_payload,
)
from scripts.integrations.analyze_diffusion_planner_progress_lane_hard_context_logging_smoke import (
    analyze,
)
from scripts.integrations.plan_diffusion_planner_progress_lane_hard_context_logging_smoke import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
)


def _route() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [2.0, 0.0],
            [3.0, 1.0],
            [4.0, 2.0],
        ],
        dtype=np.float64,
    )


def _candidates() -> np.ndarray:
    return np.asarray(
        [
            [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 1.0], [4.0, 2.0]],
            [[0.0, 0.0], [1.0, 1.4], [2.0, 2.0], [3.0, 2.5], [4.0, 3.0]],
            [[0.0, 0.0], [1.0, 0.1], [2.0, 0.2], [3.0, 1.0], [4.0, 2.0]],
        ],
        dtype=np.float64,
    )


def _payload() -> dict:
    return build_progress_lane_hard_context_logging_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        support_steps=5,
        dt_s=0.1,
        corridor_half_width_m=1.0,
        corridor_safety_margin_m=0.25,
    )


def _metadata(*, enabled: bool, records: int) -> dict:
    return {
        "camp_progress_lane_hard_context_logging": {
            "schema_version": PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
            "enabled": enabled,
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "online_selector_change": False,
            "classical_benders_claim": False,
            "records": records,
            "fields": list(PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES),
            "atom_names": list(PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES),
            "latency_fields": list(PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS),
        },
        "benchmark": {"seed": 1, "advance_mode": "perfect"},
    }


def _record(*, payload: dict | None) -> dict:
    record = {
        "candidate_closed_loop_outcomes": None,
        "progress_lane_hard_context_logging": payload,
    }
    if payload is not None:
        record.update(payload["latency_ms"])
    else:
        record.update({key: 0.0 for key in PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS})
    return record


def _write_run(root: Path, *, enabled: bool, payload: dict | None) -> None:
    root.mkdir(parents=True)
    root.joinpath("camp_selection_log.json").write_text(
        json.dumps([_record(payload=payload)]),
        encoding="utf-8",
    )
    root.joinpath("camp_validation_summary.json").write_text(
        json.dumps(_metadata(enabled=enabled, records=int(enabled))),
        encoding="utf-8",
    )


def test_context_logging_smoke_audit_accepts_paired_payload(tmp_path: Path) -> None:
    _write_run(tmp_path / "baseline", enabled=False, payload=None)
    _write_run(tmp_path / "candidate", enabled=True, payload=_payload())

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=3,
    )

    assert report["final_decision"]["passed"] is True
    assert report["counts"]["baseline_payload_records"] == 0
    assert report["counts"]["candidate_payload_records"] == 1
    assert report["errors"] == []


def test_context_logging_smoke_audit_rejects_future_payload_key(
    tmp_path: Path,
) -> None:
    payload = deepcopy(_payload())
    payload["candidate_closed_loop_outcomes"] = [{"collision": True}]
    _write_run(tmp_path / "baseline", enabled=False, payload=None)
    _write_run(tmp_path / "candidate", enabled=True, payload=payload)

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=3,
    )

    assert report["final_decision"]["passed"] is False
    assert any("future outcome key" in error for error in report["errors"])


def test_context_logging_smoke_audit_rejects_negative_atom(tmp_path: Path) -> None:
    payload = deepcopy(_payload())
    payload["progress_lane_hard_context_atoms"][1][0] = -0.5
    payload["finite_checks"]["progress_lane_hard_context_atoms_nonnegative"] = False
    _write_run(tmp_path / "baseline", enabled=False, payload=None)
    _write_run(tmp_path / "candidate", enabled=True, payload=payload)

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=3,
    )

    assert report["final_decision"]["passed"] is False
    assert any(
        "progress_lane_hard_context_atoms_nonnegative" in error
        for error in report["errors"]
    )


def test_context_logging_smoke_audit_rejects_formal_seed_path(
    tmp_path: Path,
) -> None:
    _write_run(tmp_path / "baseline" / "seed_11", enabled=False, payload=None)
    _write_run(tmp_path / "candidate" / "seed_11", enabled=True, payload=_payload())

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=3,
    )

    assert report["final_decision"]["passed"] is False
    assert any("formal_seed_detected" in error for error in report["errors"])


def test_context_logging_smoke_plan_authorizes_paired_three_step_only() -> None:
    report = build_report(label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["new_replay_authorized"] is True
    assert report["final_decision"]["closed_loop_smoke_authorized"] is True
    assert report["final_decision"]["Full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    baseline_command = report["commands"]["baseline_replay"]
    candidate_command = report["commands"]["candidate_replay"]
    assert "--camp_progress_lane_hard_context_logging" not in baseline_command
    assert "--camp_progress_lane_hard_context_logging" in candidate_command
    steps_index = candidate_command.index("--camp_progress_lane_hard_context_steps")
    assert candidate_command[steps_index + 1] == "10"
    assert baseline_command[baseline_command.index("--steps") + 1] == "3"
    assert candidate_command[candidate_command.index("--seed") + 1] == "1"


def test_context_logging_smoke_plan_rejects_missing_payload_audit(
    tmp_path: Path,
) -> None:
    report = build_report(payload_audit_source=tmp_path / "missing.py")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["new_replay_authorized"] is False
    failed = [check for check in report["source_checks"] if not check["passed"]]
    assert [check["name"] for check in failed] == ["payload_audit_available"]
