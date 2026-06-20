from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_progress_support_latency_diagnosis import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
)


def _smoke_report(*, passed: bool = True, latency_ms: float = 142.6) -> dict:
    return {
        "final_decision": {
            "status": (
                "progress_support_logging_smoke_passed"
                if passed
                else "progress_support_logging_smoke_rejected"
            ),
            "passed": passed,
        },
        "counts": {
            "baseline_payload_records": 0,
            "candidate_payload_records": 3,
            "paired_logs": 1,
            "records": 3,
        },
        "latency_ms": {
            "latency_ms_progress_support_logging": latency_ms,
        },
        "records": [
            {
                "candidate_count": 8,
                "support_steps": 10,
                "atom_count": 7,
            },
            {
                "candidate_count": 8,
                "support_steps": 10,
                "atom_count": 7,
            },
            {
                "candidate_count": 8,
                "support_steps": 10,
                "atom_count": 7,
            },
        ],
    }


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _helper_source(tmp_path: Path, *, include_nested_loop: bool = True) -> Path:
    nested = (
        "\n".join(
            [
                "    for cand_idx in range(candidates_xy.shape[0]):",
                "        for step_idx in range(candidates_xy.shape[1]):",
                "            for seg_idx, segment in enumerate(segments):",
                "                pass",
            ]
        )
        if include_nested_loop
        else "    return candidates_xy"
    )
    path = tmp_path / "diffusion_planner_progress_support.py"
    path.write_text(
        "\n".join(
            [
                "def build_progress_support_logging_payload(): pass",
                "def _route_progress_profiles(candidates_xy, route_xy):",
                nested,
                "def _plan_arc_length_profiles(): pass",
                "def _speed_profiles(): pass",
                "def _progress_support_atoms(): pass",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_progress_support_latency_diagnosis_plan_ready(tmp_path: Path) -> None:
    report = build_report(
        smoke_audit_json=_write_json(tmp_path / "smoke.json", _smoke_report()),
        helper_source=_helper_source(tmp_path),
        label="unit",
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["replay_authorized"] is False
    assert report["final_decision"]["Full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    assert report["dominant_hypothesis"]["name"] == (
        "route_projection_nested_loop_dominates_latency"
    )
    assert any(
        item["component"] == "route_projection"
        and item["expected_role"] == "dominant"
        for item in report["component_plan"]
    )
    assert any(
        "build_progress_support_logging_payload signature remains unchanged" in item
        for item in report["exact_equivalence_criteria"]
    )
    assert all(check["passed"] for check in report["source_checks"])


def test_progress_support_latency_diagnosis_rejects_unblocked_latency(
    tmp_path: Path,
) -> None:
    report = build_report(
        smoke_audit_json=_write_json(
            tmp_path / "smoke.json",
            _smoke_report(latency_ms=10.0),
        ),
        helper_source=_helper_source(tmp_path),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["latency_blocking_threshold_met"]


def test_progress_support_latency_diagnosis_rejects_failed_smoke(
    tmp_path: Path,
) -> None:
    report = build_report(
        smoke_audit_json=_write_json(
            tmp_path / "smoke.json",
            _smoke_report(passed=False),
        ),
        helper_source=_helper_source(tmp_path),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "smoke_audit_passed" in failed


def test_progress_support_latency_diagnosis_rejects_missing_payload_records(
    tmp_path: Path,
) -> None:
    source = deepcopy(_smoke_report())
    source["counts"]["candidate_payload_records"] = 0

    report = build_report(
        smoke_audit_json=_write_json(tmp_path / "smoke.json", source),
        helper_source=_helper_source(tmp_path),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "payload_records_present" in failed


def test_progress_support_latency_diagnosis_requires_nested_loop_source(
    tmp_path: Path,
) -> None:
    report = build_report(
        smoke_audit_json=_write_json(tmp_path / "smoke.json", _smoke_report()),
        helper_source=_helper_source(tmp_path, include_nested_loop=False),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check for check in report["source_checks"] if not check["passed"]]
    assert [check["name"] for check in failed] == [
        "helper_has_nested_route_projection_loop"
    ]
