from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_tiny_materiality import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    analyze,
    main,
    render_markdown,
)


def _smoke_result(**overrides: object) -> dict[str, object]:
    decision = {
        "status": "candidate_set_consensus_payload_smoke_result_ready",
        "passed": True,
        "authorized_next_work": (
            "candidate_set_consensus_payload_tiny_smoke_materiality_diagnosis_only"
        ),
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
    }
    decision.update(overrides)
    return {"final_decision": decision}


def _record(
    *,
    selected_index: int = 2,
    costs: list[float] | None = None,
    scores: list[float] | None = None,
) -> dict[str, object]:
    costs = costs or [0.02, 0.01, 0.08]
    scores = scores or [0.4, 0.5, 0.1]
    return {
        "selected_index": selected_index,
        "feasible_mask": [True, True, True],
        "selection_scores": scores,
        "candidate_set_consensus_payload_logging": {
            "available": True,
            "candidate_set_consensus_center_rms_m": costs,
            "candidate_set_consensus_center_rms_rank": [1, 0, 2],
        },
    }


def _write_log(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(rows), encoding="utf-8")


def test_candidate_set_consensus_tiny_materiality_ready(tmp_path: Path) -> None:
    log = tmp_path / "camp_selection_log.json"
    _write_log(log, [_record(), _record(), _record()])

    report = analyze(selection_log=log, smoke_result=_smoke_result(), label="unit")
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["signal_present"] is True
    assert decision["materiality_gate_passed"] is False
    assert decision["sample_too_small_for_promotion"] is True
    assert decision["atom_promotion_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["safety_benefit_evidence"] is False
    assert report["record_summary"]["selected_not_consensus_best_records"] == 3
    assert report["record_summary"]["finite_lambda_records"] == 3
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_candidate_set_consensus_tiny_materiality_rejects_smoke_not_ready(
    tmp_path: Path,
) -> None:
    log = tmp_path / "camp_selection_log.json"
    _write_log(log, [_record(), _record(), _record()])

    report = analyze(
        selection_log=log,
        smoke_result=_smoke_result(status="candidate_set_consensus_rejected"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "smoke_result_status" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_candidate_set_consensus_tiny_materiality_rejects_no_spread(
    tmp_path: Path,
) -> None:
    log = tmp_path / "camp_selection_log.json"
    rows = [
        _record(selected_index=0, costs=[0.1, 0.1, 0.1], scores=[0.1, 0.2, 0.3])
        for _ in range(3)
    ]
    _write_log(log, rows)

    report = analyze(selection_log=log, smoke_result=_smoke_result())

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = report["final_decision"]["failed_checks"]
    assert "positive_spread_records" in failed
    assert "selected_not_consensus_best_records" in failed
    assert "finite_lambda_records" in failed


def test_candidate_set_consensus_tiny_materiality_markdown_states_no_promotion(
    tmp_path: Path,
) -> None:
    log = tmp_path / "camp_selection_log.json"
    _write_log(log, [_record(), _record(), _record()])

    markdown = render_markdown(analyze(selection_log=log, smoke_result=_smoke_result()))

    assert "Candidate-Set Consensus Tiny Materiality Diagnosis" in markdown
    assert "Materiality gate passed: `False`" in markdown
    assert "Atom promotion authorized: `False`" in markdown


def test_candidate_set_consensus_tiny_materiality_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log = tmp_path / "camp_selection_log.json"
    smoke = tmp_path / "smoke_result.json"
    output_json = tmp_path / "materiality.json"
    output_md = tmp_path / "materiality.md"
    _write_log(log, [_record(), _record(), _record()])
    smoke.write_text(json.dumps(_smoke_result()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-tiny-materiality",
            "--selection_log",
            str(log),
            "--smoke_result_json",
            str(smoke),
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--require_pass",
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Candidate-Set Consensus Tiny Materiality Diagnosis" in (
        output_md.read_text(encoding="utf-8")
    )
