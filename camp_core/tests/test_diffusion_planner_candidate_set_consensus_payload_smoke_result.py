from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.integrations.summarize_diffusion_planner_candidate_set_consensus_payload_smoke_result import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _selector(*, equivalent: bool = True) -> dict[str, object]:
    return {
        "equivalent": equivalent,
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


def _payload(*, passed: bool = True, available: int = 3) -> dict[str, object]:
    return {
        "counts": {
            "available_payload_records": available,
            "baseline_logs": 1,
            "baseline_payload_records": 0,
            "candidate_logs": 1,
            "candidate_payload_records": 3,
            "invalid_payload_records": 0,
            "records": 3,
        },
        "errors": [] if passed else ["payload_error"],
        "latency_ms": {
            "latency_ms_candidate_set_consensus_payload": {
                "count": 3,
                "min": 0.1,
                "mean": 0.2,
                "max": 0.3,
            }
        },
        "final_decision": {
            "status": (
                "candidate_set_consensus_payload_smoke_audit_passed"
                if passed
                else "candidate_set_consensus_payload_smoke_audit_rejected"
            ),
            "passed": passed,
        },
    }


def _dataset(*, passed: bool = True) -> dict[str, object]:
    return {
        "passed": passed,
        "errors": [] if passed else ["dataset_error"],
        "counts": {"logs": 1, "records": 3, "candidates": 24},
        "checks": {
            "closed_loop_outcomes_forbidden": True,
            "forbidden_seed_check": True,
            "finite_candidate_contract_verified": True,
        },
    }


def _summary(*, enabled: bool, records: int, available: int) -> dict[str, object]:
    return {
        "camp_candidate_set_consensus_payload_logging": {
            "enabled": enabled,
            "records": records,
            "available_records": available,
            "invalid_records": 0,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "online_selector_change": False,
            "deployed_atom_vector_change": False,
            "classical_benders_claim": False,
        }
    }


def _baseline_summary() -> dict[str, object]:
    return _summary(enabled=False, records=0, available=0)


def _candidate_summary() -> dict[str, object]:
    return _summary(enabled=True, records=3, available=3)


def _ready_report() -> dict[str, object]:
    return build_report(
        selector_equivalence=_selector(),
        payload_smoke=_payload(),
        dataset_audit=_dataset(),
        baseline_summary=_baseline_summary(),
        candidate_summary=_candidate_summary(),
        label="unit",
    )


def test_candidate_set_consensus_smoke_result_ready() -> None:
    report = _ready_report()
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["runtime_equivalence_ready"] is True
    assert decision["payload_logging_ready"] is True
    assert decision["safety_benefit_evidence"] is False
    assert decision["atom_promotion_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_candidate_set_consensus_smoke_result_rejects_selector_mismatch() -> None:
    report = build_report(
        selector_equivalence=_selector(equivalent=False),
        payload_smoke=_payload(),
        dataset_audit=_dataset(),
        baseline_summary=_baseline_summary(),
        candidate_summary=_candidate_summary(),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    assert "selector_equivalent" in report["final_decision"]["failed_checks"]


def test_candidate_set_consensus_smoke_result_rejects_missing_payload_records() -> None:
    report = build_report(
        selector_equivalence=_selector(),
        payload_smoke=_payload(available=2),
        dataset_audit=_dataset(),
        baseline_summary=_baseline_summary(),
        candidate_summary=_summary(enabled=True, records=3, available=2),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = report["final_decision"]["failed_checks"]
    assert "payload_available_records" in failed
    assert "candidate_summary_available_records" in failed


def test_candidate_set_consensus_smoke_result_rejects_leaky_summary() -> None:
    candidate_summary = deepcopy(_candidate_summary())
    candidate_summary["camp_candidate_set_consensus_payload_logging"][
        "future_outcome_leakage"
    ] = True

    report = build_report(
        selector_equivalence=_selector(),
        payload_smoke=_payload(),
        dataset_audit=_dataset(),
        baseline_summary=_baseline_summary(),
        candidate_summary=candidate_summary,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "candidate_summary_future_outcome_leakage" in (
        report["final_decision"]["failed_checks"]
    )


def test_candidate_set_consensus_smoke_result_markdown_states_boundaries() -> None:
    markdown = render_markdown(_ready_report())

    assert "Candidate-Set Consensus Payload Smoke Result" in markdown
    assert "Safety benefit evidence: `False`" in markdown
    assert "Atom promotion authorized: `False`" in markdown
    assert "score_k(w)=a_k^T w" in markdown


def test_candidate_set_consensus_smoke_result_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selector_path = tmp_path / "selector.json"
    payload_path = tmp_path / "payload.json"
    dataset_path = tmp_path / "dataset.json"
    baseline_path = tmp_path / "baseline_summary.json"
    candidate_path = tmp_path / "candidate_summary.json"
    output_json = tmp_path / "result.json"
    output_md = tmp_path / "result.md"
    selector_path.write_text(json.dumps(_selector()), encoding="utf-8")
    payload_path.write_text(json.dumps(_payload()), encoding="utf-8")
    dataset_path.write_text(json.dumps(_dataset()), encoding="utf-8")
    baseline_path.write_text(json.dumps(_baseline_summary()), encoding="utf-8")
    candidate_path.write_text(json.dumps(_candidate_summary()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-smoke-result",
            "--selector_equivalence_json",
            str(selector_path),
            "--payload_smoke_json",
            str(payload_path),
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
    assert "Candidate-Set Consensus Payload Smoke Result" in output_md.read_text(
        encoding="utf-8"
    )
