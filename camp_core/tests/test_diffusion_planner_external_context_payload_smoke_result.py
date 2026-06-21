from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from scripts.integrations.summarize_diffusion_planner_external_context_payload_smoke_result import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


def _selector(*, equivalent: bool = True) -> dict[str, object]:
    return {
        "equivalent": equivalent,
        "records": 3,
        "exact_field_mismatches": {"selected_index": 0, "feasible_mask": 0},
        "numeric_field_mismatches": {"scores": 0, "atoms": 0},
    }


def _payload(*, passed: bool = True, available: int = 3) -> dict[str, object]:
    return {
        "final_decision": {
            "status": (
                "external_context_payload_smoke_audit_passed"
                if passed
                else "external_context_payload_smoke_audit_rejected"
            ),
            "passed": passed,
        },
        "counts": {
            "candidate_payload_records": 3,
            "available_payload_records": available,
            "route_speed_available_records": available,
            "traffic_signal_available_records": 0,
        },
        "errors": [] if passed else ["payload_error"],
    }


def _dataset(*, passed: bool = True) -> dict[str, object]:
    return {
        "passed": passed,
        "counts": {"records": 3, "candidates": 24, "logs": 1},
        "checks": {
            "closed_loop_outcomes_forbidden": True,
            "forbidden_seed_check": True,
            "finite_candidate_contract_verified": True,
        },
    }


def _summary(*, enabled: bool, records: int) -> dict[str, object]:
    return {
        "camp_external_context_payload_logging": {
            "enabled": enabled,
            "records": records,
            "future_outcome_leakage": False,
            "selection_effect": False,
            "closed_loop_outcome_fields_read": False,
            "classical_benders_claim": False,
        }
    }


def _ready_report() -> dict[str, object]:
    return build_report(
        selector_equivalence=_selector(),
        payload_smoke=_payload(),
        dataset_audit=_dataset(),
        baseline_summary=_summary(enabled=False, records=0),
        candidate_summary=_summary(enabled=True, records=3),
        label="unit",
    )


def test_external_context_payload_smoke_result_ready() -> None:
    report = _ready_report()

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["Full36_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    assert report["observed_counts"]["available_payload_records"] == 3
    assert report["observed_counts"]["traffic_signal_available_records"] == 0


def test_external_context_payload_smoke_result_rejects_selector_mismatch() -> None:
    report = build_report(
        selector_equivalence=_selector(equivalent=False),
        payload_smoke=_payload(),
        dataset_audit=_dataset(),
        baseline_summary=_summary(enabled=False, records=0),
        candidate_summary=_summary(enabled=True, records=3),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["selector_equivalent"]


def test_external_context_payload_smoke_result_rejects_no_available_payload() -> None:
    report = build_report(
        selector_equivalence=_selector(),
        payload_smoke=_payload(available=0),
        dataset_audit=_dataset(),
        baseline_summary=_summary(enabled=False, records=0),
        candidate_summary=_summary(enabled=True, records=3),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == [
        "payload_available_records_nonzero",
        "payload_route_speed_available_records_nonzero",
    ]


def test_external_context_payload_smoke_result_rejects_leaky_summary() -> None:
    candidate_summary = deepcopy(_summary(enabled=True, records=3))
    candidate_summary["camp_external_context_payload_logging"][
        "future_outcome_leakage"
    ] = True

    report = build_report(
        selector_equivalence=_selector(),
        payload_smoke=_payload(),
        dataset_audit=_dataset(),
        baseline_summary=_summary(enabled=False, records=0),
        candidate_summary=candidate_summary,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["candidate_logging_no_leak"]


def test_external_context_payload_smoke_result_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
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
    baseline_path.write_text(
        json.dumps(_summary(enabled=False, records=0)),
        encoding="utf-8",
    )
    candidate_path.write_text(
        json.dumps(_summary(enabled=True, records=3)),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "external-context-smoke-result",
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
    assert "External Context Payload Smoke Result" in output_md.read_text(
        encoding="utf-8"
    )
