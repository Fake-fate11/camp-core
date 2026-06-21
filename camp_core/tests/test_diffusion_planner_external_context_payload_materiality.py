from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_external_context_payload import (
    EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS,
    build_external_context_payload,
)
from scripts.integrations.analyze_diffusion_planner_external_context_payload_materiality import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    analyze,
    main,
)


def _candidates(*, fast_second: bool = True) -> np.ndarray:
    second = [[0.0, 0.0, 1.0, 0.0], [2.0, 0.0, 1.0, 0.0], [4.0, 0.0, 1.0, 0.0]]
    if not fast_second:
        second = [[0.0, 0.0, 1.0, 0.0], [1.0, 0.0, 1.0, 0.0], [2.0, 0.0, 1.0, 0.0]]
    return np.asarray(
        [
            [[0.0, 0.0, 1.0, 0.0], [1.0, 0.0, 1.0, 0.0], [2.0, 0.0, 1.0, 0.0]],
            second,
        ],
        dtype=np.float64,
    )


def _route() -> np.ndarray:
    return np.asarray(
        [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0]],
        dtype=np.float64,
    )


def _payload(*, material: bool = True) -> dict:
    return build_external_context_payload(
        candidates=_candidates(fast_second=material),
        route_centerline_ego=_route(),
        route_speed_limit_mps=1.5 if material else 3.0,
        route_has_speed_limit=True,
        support_steps=3,
        dt_s=1.0,
    )


def _record(payload: dict) -> dict:
    record = {
        "selected_index": 0,
        "candidate_closed_loop_outcomes": None,
        "external_context_payload_logging": payload,
    }
    record.update({key: float(payload["latency_ms"][key]) for key in EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS})
    return record


def _write_log(root: Path, *, material: bool = True, records: int = 2) -> None:
    root.mkdir(parents=True)
    root.joinpath("camp_selection_log.json").write_text(
        json.dumps([_record(_payload(material=material)) for _ in range(records)]),
        encoding="utf-8",
    )


def _smoke_result(*, passed: bool = True) -> dict:
    return {
        "final_decision": {
            "status": (
                "external_context_payload_smoke_result_ready"
                if passed
                else "external_context_payload_smoke_result_rejected"
            ),
            "passed": passed,
            "authorized_next_work": (
                "external_context_payload_materiality_diagnosis_existing_smoke_only"
                if passed
                else None
            ),
            "new_replay_authorized": False,
            "camp_retraining_authorized": False,
            "formal_seeds_authorized": False,
        }
    }


def test_external_context_payload_materiality_accepts_route_speed_signal(
    tmp_path: Path,
) -> None:
    _write_log(tmp_path / "candidate", material=True)

    report = analyze(
        smoke_result=_smoke_result(),
        candidate_root=tmp_path / "candidate",
        expected_records=2,
        expected_candidates=2,
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    assert report["material_families"] == ["route_speed"]
    speed_excess = next(
        field
        for field in report["field_reports"]
        if field["field"] == "candidate_speed_limit_excess_integral_mps"
    )
    assert speed_excess["material"] is True
    assert speed_excess["nonzero_records"] == 2


def test_external_context_payload_materiality_rejects_constant_nonmaterial_payload(
    tmp_path: Path,
) -> None:
    _write_log(tmp_path / "candidate", material=False)

    report = analyze(
        smoke_result=_smoke_result(),
        candidate_root=tmp_path / "candidate",
        expected_records=2,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    assert report["material_families"] == []


def test_external_context_payload_materiality_rejects_failed_result_gate(
    tmp_path: Path,
) -> None:
    _write_log(tmp_path / "candidate", material=True)

    report = analyze(
        smoke_result=_smoke_result(passed=False),
        candidate_root=tmp_path / "candidate",
        expected_records=2,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["result_gate_checks"] if not check["passed"]]
    assert failed == [
        "result_gate_status_ready",
        "result_gate_passed",
        "result_gate_authorizes_materiality",
    ]


def test_external_context_payload_materiality_rejects_leaky_payload(
    tmp_path: Path,
) -> None:
    payload = deepcopy(_payload(material=True))
    payload["future_outcome_leakage"] = True
    root = tmp_path / "candidate"
    root.mkdir()
    root.joinpath("camp_selection_log.json").write_text(
        json.dumps([_record(payload), _record(payload)]),
        encoding="utf-8",
    )

    report = analyze(
        smoke_result=_smoke_result(),
        candidate_root=root,
        expected_records=2,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["record_checks"] if not check["passed"]]
    assert failed == [
        "record_0_future_outcome_leakage",
        "record_1_future_outcome_leakage",
    ]


def test_external_context_payload_materiality_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    candidate = tmp_path / "candidate"
    smoke_result = tmp_path / "smoke_result.json"
    output_json = tmp_path / "materiality.json"
    output_md = tmp_path / "materiality.md"
    _write_log(candidate, material=True)
    smoke_result.write_text(json.dumps(_smoke_result()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "external-context-materiality",
            "--smoke_result_json",
            str(smoke_result),
            "--candidate_root",
            str(candidate),
            "--expected_records",
            "2",
            "--expected_candidates",
            "2",
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "External Context Payload Materiality" in output_md.read_text(
        encoding="utf-8"
    )
