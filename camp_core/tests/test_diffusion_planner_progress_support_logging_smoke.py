from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_progress_support import (
    PROGRESS_SUPPORT_ATOM_NAMES,
    PROGRESS_SUPPORT_FIELD_NAMES,
    PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
    build_progress_support_logging_payload,
)
from scripts.integrations.analyze_diffusion_planner_progress_support_logging_smoke import (
    analyze,
)
from scripts.integrations.plan_diffusion_planner_progress_support_logging_smoke import (
    READY_STATUS,
    REJECT_STATUS,
    build_report,
)


def _route() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0],
            [5.0, 0.0],
            [10.0, 0.0],
        ],
        dtype=np.float64,
    )


def _candidates() -> np.ndarray:
    return np.asarray(
        [
            [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0]],
            [[0.0, 0.0], [0.7, 0.0], [1.4, 0.0], [2.1, 0.0]],
            [[0.0, 0.0], [0.8, 0.0], [0.4, 0.0], [1.2, 0.0]],
        ],
        dtype=np.float64,
    )


def _payload() -> dict:
    return build_progress_support_logging_payload(
        candidates=_candidates(),
        route_centerline_ego=_route(),
        support_steps=4,
        dt_s=0.1,
    )


def _metadata(*, enabled: bool, records: int) -> dict:
    return {
        "camp_progress_support_logging": {
            "schema_version": PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
            "enabled": enabled,
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "online_selector_change": False,
            "classical_benders_claim": False,
            "records": records,
            "fields": list(PROGRESS_SUPPORT_FIELD_NAMES),
            "atom_names": list(PROGRESS_SUPPORT_ATOM_NAMES),
            "latency_fields": ["latency_ms_progress_support_logging"],
        },
        "benchmark": {"seed": 1, "advance_mode": "perfect"},
    }


def _record(*, payload: dict | None) -> dict:
    latency = 0.0
    if payload is not None:
        latency = payload["latency_ms"]["latency_ms_progress_support_logging"]
    return {
        "candidate_closed_loop_outcomes": None,
        "progress_support_logging": payload,
        "latency_ms_progress_support_logging": latency,
    }


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


def test_progress_support_logging_smoke_audit_accepts_paired_payload(
    tmp_path: Path,
) -> None:
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


def test_progress_support_logging_smoke_audit_rejects_future_payload_key(
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


def test_progress_support_logging_smoke_audit_rejects_negative_atom(
    tmp_path: Path,
) -> None:
    payload = deepcopy(_payload())
    payload["progress_support_atoms"][1][0] = -0.5
    payload["finite_checks"]["progress_support_atoms_nonnegative"] = False
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
    assert any("progress_support_atoms_nonnegative" in error for error in report["errors"])


def test_progress_support_logging_smoke_plan_authorizes_paired_three_step_only() -> None:
    report = build_report(label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["closed_loop_replay_authorized"] is True
    assert report["final_decision"]["Full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    baseline_command = report["commands"]["baseline_replay"]
    candidate_command = report["commands"]["candidate_replay"]
    assert "--camp_progress_support_logging" not in baseline_command
    assert "--camp_progress_support_logging" in candidate_command
    assert candidate_command[candidate_command.index("--camp_progress_support_steps") + 1] == "10"
    assert baseline_command[baseline_command.index("--steps") + 1] == "3"
    assert candidate_command[candidate_command.index("--seed") + 1] == "1"


def test_progress_support_logging_smoke_plan_rejects_missing_payload_audit(
    tmp_path: Path,
) -> None:
    report = build_report(payload_audit_source=tmp_path / "missing.py")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["closed_loop_replay_authorized"] is False
    failed = [check for check in report["source_checks"] if not check["passed"]]
    assert [check["name"] for check in failed] == ["payload_audit_available"]
