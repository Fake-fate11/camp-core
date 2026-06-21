from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.summarize_diffusion_planner_temporal_consistency_payload_smoke_result import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _payload_smoke(**overrides: object) -> dict[str, object]:
    payload = {
        "counts": {
            "available_payload_records": 2,
            "baseline_records": 3,
            "candidate_payload_records": 3,
            "candidate_records": 3,
            "first_tick_fail_closed_records": 1,
        },
        "errors": [],
        "latency_ms": {
            "latency_ms_temporal_consistency_payload": {
                "count": 3,
                "min": 0.02,
                "mean": 0.05,
                "max": 0.08,
            }
        },
        "final_decision": {
            "status": "temporal_consistency_payload_smoke_audit_passed",
            "passed": True,
        },
    }
    payload.update(overrides)
    return payload


def _selector_equivalence(**overrides: object) -> dict[str, object]:
    payload = {
        "equivalent": True,
        "records": 3,
        "exact_field_mismatches": {
            "selected_index": 0,
            "feasible_mask": 0,
        },
        "numeric_field_mismatches": {
            "scores": 0,
            "selection_scores": 0,
        },
        "numeric_max_abs_diff": {
            "scores": 0.0,
            "selection_scores": 0.0,
        },
    }
    payload.update(overrides)
    return payload


def _dataset_audit(**overrides: object) -> dict[str, object]:
    payload = {"passed": True, "errors": []}
    payload.update(overrides)
    return payload


def _summary(*, enabled: bool, records: int, available: int, first_fail: int) -> dict:
    return {
        "camp_temporal_consistency_payload_logging": {
            "enabled": enabled,
            "records": records,
            "available_records": available,
            "first_tick_fail_closed_records": first_fail,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "classical_benders_claim": False,
        }
    }


def _baseline_summary() -> dict:
    return _summary(enabled=False, records=0, available=0, first_fail=0)


def _candidate_summary() -> dict:
    return _summary(enabled=True, records=3, available=2, first_fail=1)


def test_temporal_consistency_smoke_result_accepts_equivalent_tiny_smoke() -> None:
    report = build_report(
        payload_smoke=_payload_smoke(),
        selector_equivalence=_selector_equivalence(),
        dataset_audit=_dataset_audit(),
        baseline_summary=_baseline_summary(),
        candidate_summary=_candidate_summary(),
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["runtime_equivalence_ready"] is True
    assert decision["safety_benefit_evidence"] is False
    assert decision["atom_promotion_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["closed_loop_smoke_authorized"] is False
    assert report["materiality_summary"]["sufficient_for_broader_plan"] is True
    assert report["materiality_summary"]["sufficient_for_training"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_temporal_consistency_smoke_result_rejects_selector_mismatch() -> None:
    report = build_report(
        payload_smoke=_payload_smoke(),
        selector_equivalence=_selector_equivalence(
            equivalent=False,
            exact_field_mismatches={"selected_index": 1},
        ),
        dataset_audit=_dataset_audit(),
        baseline_summary=_baseline_summary(),
        candidate_summary=_candidate_summary(),
    )

    decision = report["final_decision"]
    assert decision["status"] == REJECT_STATUS
    assert decision["authorized_next_work"] is None
    assert "selector_equivalent" in decision["failed_checks"]
    assert "selector_exact_mismatch_total" in decision["failed_checks"]


def test_temporal_consistency_smoke_result_rejects_missing_available_records() -> None:
    report = build_report(
        payload_smoke=_payload_smoke(
            counts={
                "available_payload_records": 1,
                "baseline_records": 3,
                "candidate_payload_records": 3,
                "candidate_records": 3,
                "first_tick_fail_closed_records": 1,
            }
        ),
        selector_equivalence=_selector_equivalence(),
        dataset_audit=_dataset_audit(),
        baseline_summary=_summary(enabled=False, records=0, available=0, first_fail=0),
        candidate_summary=_summary(enabled=True, records=3, available=1, first_fail=1),
    )

    decision = report["final_decision"]
    assert decision["status"] == REJECT_STATUS
    assert "payload_available_records" in decision["failed_checks"]
    assert "candidate_payload_available_records" in decision["failed_checks"]


def test_temporal_consistency_smoke_result_markdown_states_boundaries() -> None:
    markdown = render_markdown(
        build_report(
            payload_smoke=_payload_smoke(),
            selector_equivalence=_selector_equivalence(),
            dataset_audit=_dataset_audit(),
            baseline_summary=_baseline_summary(),
            candidate_summary=_candidate_summary(),
        )
    )

    assert "Temporal Consistency Payload Smoke Result" in markdown
    assert "Safety benefit evidence: `False`" in markdown
    assert "Atom promotion authorized: `False`" in markdown
    assert "score_k(w)=a_k^T w" in markdown


def test_temporal_consistency_smoke_result_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_path = tmp_path / "payload.json"
    selector_path = tmp_path / "selector.json"
    dataset_path = tmp_path / "dataset.json"
    baseline_path = tmp_path / "baseline_summary.json"
    candidate_path = tmp_path / "candidate_summary.json"
    output_json = tmp_path / "result.json"
    output_md = tmp_path / "result.md"
    payload_path.write_text(json.dumps(_payload_smoke()), encoding="utf-8")
    selector_path.write_text(json.dumps(_selector_equivalence()), encoding="utf-8")
    dataset_path.write_text(json.dumps(_dataset_audit()), encoding="utf-8")
    baseline_path.write_text(json.dumps(_baseline_summary()), encoding="utf-8")
    candidate_path.write_text(json.dumps(_candidate_summary()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "result",
            "--payload_smoke_json",
            str(payload_path),
            "--selector_equivalence_json",
            str(selector_path),
            "--dataset_audit_json",
            str(dataset_path),
            "--baseline_summary_json",
            str(baseline_path),
            "--candidate_summary_json",
            str(candidate_path),
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
    assert "Temporal Consistency Payload Smoke Result" in output_md.read_text(
        encoding="utf-8"
    )
