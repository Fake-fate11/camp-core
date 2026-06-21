from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_candidate_set_consensus_payload import (
    CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES,
    CANDIDATE_SET_CONSENSUS_PAYLOAD_FIELD_NAMES,
    CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS,
    CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
    build_candidate_set_consensus_payload,
)
from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_payload_smoke import (
    analyze,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_payload_smoke import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    SmokeSpec,
    build_report,
    main,
    render_bash,
)


def _candidates(count: int = 3) -> np.ndarray:
    rows = []
    for index in range(count):
        offset = float(index) * 0.2
        rows.append(
            [
                [0.0 + offset, 0.0, 1.0, 0.0],
                [1.0 + offset, 0.0, 1.0, 0.0],
                [2.0 + offset, 0.0, 1.0, 0.0],
            ]
        )
    return np.asarray(rows, dtype=np.float64)


def _payload(count: int = 3) -> dict:
    return build_candidate_set_consensus_payload(
        candidates=_candidates(count),
        support_steps=3,
    )


def _metadata(*, enabled: bool, records: int, available_records: int = 0) -> dict:
    return {
        "camp_candidate_set_consensus_payload_logging": {
            "schema_version": CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
            "enabled": enabled,
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "online_selector_change": False,
            "deployed_atom_vector_change": False,
            "classical_benders_claim": False,
            "records": records,
            "available_records": available_records,
            "invalid_records": records - available_records,
            "fields": list(CANDIDATE_SET_CONSENSUS_PAYLOAD_FIELD_NAMES),
            "atom_candidate_names": list(
                CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES
            ),
            "latency_fields": list(CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS),
        },
        "benchmark": {"seed": 1, "advance_mode": "perfect"},
    }


def _record(*, payload: dict | None) -> dict:
    record = {
        "selected_index": 0,
        "candidate_closed_loop_outcomes": None,
        "candidate_set_consensus_payload_logging": payload,
    }
    if payload is None:
        record.update({key: 0.0 for key in CANDIDATE_SET_CONSENSUS_PAYLOAD_LATENCY_KEYS})
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


def _implementation(**decision_overrides: object) -> dict:
    payload = {"payload": _payload()}
    if decision_overrides:
        decision = {
            "status": "candidate_set_consensus_payload_implementation_unit_tests_ready",
            "authorized_next_work": (
                "candidate_set_consensus_default_off_tiny_smoke_plan_only"
            ),
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
        decision.update(decision_overrides)
        payload["final_decision"] = decision
    return payload


def test_candidate_set_consensus_payload_smoke_audit_accepts_available_payloads(
    tmp_path: Path,
) -> None:
    payloads = [_payload(), _payload(), _payload()]
    _write_run(tmp_path / "baseline", enabled=False, payloads=[None, None, None])
    _write_run(tmp_path / "candidate", enabled=True, payloads=payloads)

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=3,
        expected_candidates=3,
        min_available_records=3,
    )

    assert report["final_decision"]["passed"] is True
    assert report["counts"]["candidate_payload_records"] == 3
    assert report["counts"]["available_payload_records"] == 3
    assert report["errors"] == []


def test_candidate_set_consensus_payload_smoke_audit_rejects_unavailable_payload(
    tmp_path: Path,
) -> None:
    payload = build_candidate_set_consensus_payload(
        candidates=_candidates(1),
        support_steps=3,
    )
    _write_run(tmp_path / "baseline", enabled=False, payloads=[None])
    _write_run(tmp_path / "candidate", enabled=True, payloads=[payload])

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=1,
        min_available_records=1,
    )

    assert report["final_decision"]["passed"] is False
    assert any("available_payload_records" in error for error in report["errors"])


def test_candidate_set_consensus_payload_smoke_audit_rejects_negative_cost(
    tmp_path: Path,
) -> None:
    payload = deepcopy(_payload())
    payload["candidate_set_consensus_center_rms_m"] = [0.0, -1.0, 0.2]
    _write_run(tmp_path / "baseline", enabled=False, payloads=[None])
    _write_run(tmp_path / "candidate", enabled=True, payloads=[payload])

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=3,
        min_available_records=1,
    )

    assert report["final_decision"]["passed"] is False
    assert any("negative" in error for error in report["errors"])


def test_candidate_set_consensus_payload_smoke_audit_rejects_formal_seed_path(
    tmp_path: Path,
) -> None:
    _write_run(tmp_path / "baseline" / "seed_11", enabled=False, payloads=[None])
    _write_run(tmp_path / "candidate" / "seed_11", enabled=True, payloads=[_payload()])

    report = analyze(
        baseline_root=tmp_path / "baseline" / "seed_11",
        candidate_root=tmp_path / "candidate" / "seed_11",
        expected_logs=1,
        expected_records=1,
        expected_candidates=3,
        min_available_records=1,
    )

    assert report["final_decision"]["passed"] is False
    assert any("formal_seed_detected" in error for error in report["errors"])


def test_candidate_set_consensus_payload_smoke_plan_authorizes_three_step_only() -> None:
    report = build_report(implementation=_implementation(), label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["new_replay_authorized"] is True
    assert report["final_decision"]["full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["final_decision"]["dp_modification_authorized"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    assert "git pull" in report["analysis"]["sync_boundary"]
    baseline_command = report["commands"]["baseline_replay"]
    candidate_command = report["commands"]["candidate_replay"]
    assert "--camp_candidate_set_consensus_payload_logging" not in baseline_command
    assert "--camp_candidate_set_consensus_payload_logging" in candidate_command
    assert baseline_command[baseline_command.index("--steps") + 1] == "3"
    assert candidate_command[candidate_command.index("--seed") + 1] == "1"
    assert candidate_command[candidate_command.index("--num_candidates") + 1] == "8"


def test_candidate_set_consensus_payload_smoke_plan_rejects_bad_implementation() -> None:
    implementation = _implementation()
    implementation["payload"]["available"] = False

    report = build_report(implementation=implementation)

    assert report["final_decision"]["status"] != READY_STATUS
    assert report["final_decision"]["new_replay_authorized"] is False
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert "implementation_payload_available" in failed


def test_candidate_set_consensus_payload_smoke_plan_rejects_formal_seed() -> None:
    report = build_report(
        implementation=_implementation(),
        smoke=replace(SmokeSpec(), seed=11),
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert report["final_decision"]["new_replay_authorized"] is False
    formal_check = next(
        check
        for check in report["plan_checks"]
        if check["name"] == "scope_seed_is_nonformal"
    )
    assert formal_check["passed"] is False


def test_candidate_set_consensus_payload_smoke_plan_renders_bash_runbook() -> None:
    report = build_report(implementation=_implementation(), label="unit")

    bash = render_bash(report)

    assert bash.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in bash
    assert "cd /root/autodl-tmp/camp_core" in bash
    assert "== camp_sync ==" in bash
    assert "== head_audit ==" in bash
    assert "== baseline_replay ==" in bash
    assert "== candidate_replay ==" in bash
    assert "--camp_candidate_set_consensus_payload_logging" in bash
    assert "7a1d33da277a1992ec474b5383a0c963c72e04e4" in bash
    assert "Full36" in bash
    assert "candidate_set_consensus_payload_paired_three_step_smoke_complete" in bash


def test_candidate_set_consensus_payload_smoke_plan_cli_writes_bash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    implementation_path = tmp_path / "implementation.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    output_bash = tmp_path / "run.sh"
    implementation_path.write_text(json.dumps(_implementation()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-smoke-plan",
            "--implementation_json",
            str(implementation_path),
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--output_bash",
            str(output_bash),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Candidate-Set Consensus Payload Smoke Plan" in output_md.read_text(
        encoding="utf-8"
    )
    assert "candidate_set_consensus_payload_paired_three_step_smoke_complete" in (
        output_bash.read_text(encoding="utf-8")
    )
