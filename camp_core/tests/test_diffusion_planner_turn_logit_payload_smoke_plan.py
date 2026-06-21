from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_turn_logit_payload import (
    TURN_LOGIT_PAYLOAD_ATOM_CANDIDATE_NAMES,
    TURN_LOGIT_PAYLOAD_FIELD_NAMES,
    TURN_LOGIT_PAYLOAD_LATENCY_KEYS,
    TURN_LOGIT_PAYLOAD_SCHEMA_VERSION,
    build_turn_logit_payload,
)
from scripts.integrations.analyze_diffusion_planner_turn_logit_payload_smoke import (
    analyze,
)
from scripts.integrations.plan_diffusion_planner_turn_logit_payload_smoke import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    build_report,
)


def _metadata(*, enabled: bool, records: int, available_records: int = 0) -> dict:
    return {
        "camp_turn_logit_payload_logging": {
            "schema_version": TURN_LOGIT_PAYLOAD_SCHEMA_VERSION,
            "enabled": enabled,
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "online_selector_change": False,
            "classical_benders_claim": False,
            "records": records,
            "available_records": available_records,
            "invalid_records": 0,
            "fields": list(TURN_LOGIT_PAYLOAD_FIELD_NAMES),
            "atomization_candidate_names": list(
                TURN_LOGIT_PAYLOAD_ATOM_CANDIDATE_NAMES
            ),
            "latency_fields": list(TURN_LOGIT_PAYLOAD_LATENCY_KEYS),
        },
        "benchmark": {"seed": 1, "advance_mode": "perfect"},
    }


def _record(*, payload: dict | None) -> dict:
    record = {
        "selected_index": 0,
        "candidate_closed_loop_outcomes": None,
        "turn_logit_payload_logging": payload,
    }
    if payload is None:
        record.update({key: 0.0 for key in TURN_LOGIT_PAYLOAD_LATENCY_KEYS})
    else:
        record.update(payload["latency_ms"])
    return record


def _write_run(root: Path, *, enabled: bool, payloads: list[dict | None]) -> None:
    root.mkdir(parents=True)
    root.joinpath("camp_selection_log.json").write_text(
        json.dumps([_record(payload=payload) for payload in payloads]),
        encoding="utf-8",
    )
    root.joinpath("camp_validation_summary.json").write_text(
        json.dumps(
            _metadata(
                enabled=enabled,
                records=len([payload for payload in payloads if payload is not None]),
                available_records=len(
                    [
                        payload
                        for payload in payloads
                        if payload is not None and payload.get("available") is True
                    ]
                ),
            )
        ),
        encoding="utf-8",
    )


def test_turn_logit_payload_smoke_audit_accepts_null_safe_payloads(
    tmp_path: Path,
) -> None:
    payloads = [
        build_turn_logit_payload(turn_logits=None, candidate_count=3)
        for _ in range(2)
    ]
    _write_run(tmp_path / "baseline", enabled=False, payloads=[None, None])
    _write_run(tmp_path / "candidate", enabled=True, payloads=payloads)

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=2,
        expected_candidates=3,
    )

    assert report["final_decision"]["passed"] is True
    assert report["counts"]["candidate_payload_records"] == 2
    assert report["counts"]["available_payload_records"] == 0
    assert report["errors"] == []


def test_turn_logit_payload_smoke_audit_accepts_available_payload(
    tmp_path: Path,
) -> None:
    logits = np.asarray(
        [[1.0, 2.0, 0.0], [2.0, 0.5, 0.0], [0.1, 0.2, 3.0]],
        dtype=np.float64,
    )
    payload = build_turn_logit_payload(turn_logits=logits, candidate_count=3)
    _write_run(tmp_path / "baseline", enabled=False, payloads=[None])
    _write_run(tmp_path / "candidate", enabled=True, payloads=[payload])

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=3,
    )

    assert report["final_decision"]["passed"] is True
    assert report["counts"]["available_payload_records"] == 1
    assert report["record_reports"][0]["available"] is True


def test_turn_logit_payload_smoke_audit_rejects_invalid_payload(
    tmp_path: Path,
) -> None:
    payload = deepcopy(build_turn_logit_payload(turn_logits=None, candidate_count=3))
    payload["finite_checks"]["payload_valid"] = False
    _write_run(tmp_path / "baseline", enabled=False, payloads=[None])
    _write_run(tmp_path / "candidate", enabled=True, payloads=[payload])

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=3,
    )

    assert report["final_decision"]["passed"] is False
    assert any("finite_checks.payload_valid" in error for error in report["errors"])


def test_turn_logit_payload_smoke_audit_rejects_formal_seed_path(
    tmp_path: Path,
) -> None:
    payload = build_turn_logit_payload(turn_logits=None, candidate_count=3)
    _write_run(tmp_path / "baseline" / "seed_11", enabled=False, payloads=[None])
    _write_run(tmp_path / "candidate" / "seed_11", enabled=True, payloads=[payload])

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=3,
    )

    assert report["final_decision"]["passed"] is False
    assert any("formal_seed_detected" in error for error in report["errors"])


def test_turn_logit_payload_smoke_plan_authorizes_paired_three_step_only() -> None:
    report = build_report(label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["new_replay_authorized"] is True
    assert report["final_decision"]["Full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    baseline_command = report["commands"]["baseline_replay"]
    candidate_command = report["commands"]["candidate_replay"]
    assert "--camp_turn_logit_payload_logging" not in baseline_command
    assert "--camp_turn_logit_payload_logging" in candidate_command
    assert baseline_command[baseline_command.index("--steps") + 1] == "3"
    assert candidate_command[candidate_command.index("--seed") + 1] == "1"


def test_turn_logit_payload_smoke_plan_rejects_missing_payload_audit(
    tmp_path: Path,
) -> None:
    report = build_report(payload_audit_source=tmp_path / "missing.py")

    assert report["final_decision"]["status"] != READY_STATUS
    assert report["final_decision"]["new_replay_authorized"] is False
    check = next(
        item for item in report["source_checks"] if item["name"] == "payload_audit_available"
    )
    assert check["passed"] is False
