from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_external_context_payload import (
    EXTERNAL_CONTEXT_PAYLOAD_ATOM_CANDIDATE_NAMES,
    EXTERNAL_CONTEXT_PAYLOAD_FIELD_NAMES,
    EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS,
    EXTERNAL_CONTEXT_PAYLOAD_SCHEMA_VERSION,
    build_external_context_payload,
)
from scripts.integrations.analyze_diffusion_planner_external_context_payload_smoke import (
    analyze,
)
from scripts.integrations.plan_diffusion_planner_external_context_payload_smoke import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    SmokeSpec,
    build_report,
    main,
    render_bash,
)


def _candidates() -> np.ndarray:
    return np.asarray(
        [
            [[0.0, 0.0, 1.0, 0.0], [1.0, 0.0, 1.0, 0.0], [2.0, 0.0, 1.0, 0.0]],
            [[0.0, 0.0, 1.0, 0.0], [2.0, 0.0, 1.0, 0.0], [4.0, 0.0, 1.0, 0.0]],
        ],
        dtype=np.float64,
    )


def _route() -> np.ndarray:
    return np.asarray(
        [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0]],
        dtype=np.float64,
    )


def _payload(*, available: bool = True) -> dict:
    if available:
        return build_external_context_payload(
            candidates=_candidates(),
            route_centerline_ego=_route(),
            route_speed_limit_mps=1.5,
            route_has_speed_limit=True,
            support_steps=3,
            dt_s=1.0,
        )
    return build_external_context_payload(
        candidates=_candidates(),
        route_centerline_ego=None,
        support_steps=3,
        dt_s=1.0,
    )


def _metadata(*, enabled: bool, records: int, available_records: int = 0) -> dict:
    return {
        "camp_external_context_payload_logging": {
            "schema_version": EXTERNAL_CONTEXT_PAYLOAD_SCHEMA_VERSION,
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
            "invalid_records": 0,
            "fields": list(EXTERNAL_CONTEXT_PAYLOAD_FIELD_NAMES),
            "atom_candidate_names": list(
                EXTERNAL_CONTEXT_PAYLOAD_ATOM_CANDIDATE_NAMES
            ),
            "latency_fields": list(EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS),
        },
        "benchmark": {"seed": 1, "advance_mode": "perfect"},
    }


def _record(*, payload: dict | None) -> dict:
    record = {
        "selected_index": 0,
        "candidate_closed_loop_outcomes": None,
        "external_context_payload_logging": payload,
    }
    if payload is None:
        record.update({key: 0.0 for key in EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS})
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


def test_external_context_payload_smoke_audit_accepts_available_payloads(
    tmp_path: Path,
) -> None:
    payloads = [_payload(), _payload()]
    _write_run(tmp_path / "baseline", enabled=False, payloads=[None, None])
    _write_run(tmp_path / "candidate", enabled=True, payloads=payloads)

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=2,
        expected_candidates=2,
        min_available_records=1,
    )

    assert report["final_decision"]["passed"] is True
    assert report["counts"]["candidate_payload_records"] == 2
    assert report["counts"]["available_payload_records"] == 2
    assert report["counts"]["route_speed_available_records"] == 2
    assert report["counts"]["traffic_signal_available_records"] == 0
    assert report["errors"] == []


def test_external_context_payload_smoke_audit_rejects_unavailable_payloads(
    tmp_path: Path,
) -> None:
    payload = _payload(available=False)
    _write_run(tmp_path / "baseline", enabled=False, payloads=[None])
    _write_run(tmp_path / "candidate", enabled=True, payloads=[payload])

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=2,
        min_available_records=1,
    )

    assert report["final_decision"]["passed"] is False
    assert any("available_payload_records" in error for error in report["errors"])


def test_external_context_payload_smoke_audit_rejects_invalid_payload(
    tmp_path: Path,
) -> None:
    payload = deepcopy(_payload())
    payload["available"] = True
    payload["finite_checks"]["payload_valid"] = False
    _write_run(tmp_path / "baseline", enabled=False, payloads=[None])
    _write_run(tmp_path / "candidate", enabled=True, payloads=[payload])

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["passed"] is False
    assert any("finite_checks.payload_valid" in error for error in report["errors"])


def test_external_context_payload_smoke_audit_rejects_formal_seed_path(
    tmp_path: Path,
) -> None:
    payload = _payload()
    _write_run(tmp_path / "baseline" / "seed_11", enabled=False, payloads=[None])
    _write_run(tmp_path / "candidate" / "seed_11", enabled=True, payloads=[payload])

    report = analyze(
        baseline_root=tmp_path / "baseline" / "seed_11",
        candidate_root=tmp_path / "candidate" / "seed_11",
        expected_logs=1,
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["passed"] is False
    assert any("formal_seed_detected" in error for error in report["errors"])


def test_external_context_payload_smoke_plan_authorizes_paired_three_step_only() -> None:
    report = build_report(label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["new_replay_authorized"] is True
    assert report["final_decision"]["Full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    assert report["final_decision"]["DP_modification_authorized"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    assert "git pull" in report["analysis"]["sync_boundary"]
    camp_sync = report["commands"]["camp_sync"]
    head_audit = report["commands"]["head_audit"]
    baseline_command = report["commands"]["baseline_replay"]
    candidate_command = report["commands"]["candidate_replay"]
    assert camp_sync == [
        "git",
        "-C",
        "/root/autodl-tmp/camp_core",
        "pull",
        "--ff-only",
        "origin",
        "main",
    ]
    assert "7a1d33da277a1992ec474b5383a0c963c72e04e4" in head_audit[-1]
    assert "--camp_external_context_payload_logging" not in baseline_command
    assert "--camp_external_context_payload_logging" in candidate_command
    assert baseline_command[baseline_command.index("--steps") + 1] == "3"
    assert candidate_command[candidate_command.index("--seed") + 1] == "1"
    assert candidate_command[candidate_command.index("--num_candidates") + 1] == "8"


def test_external_context_payload_smoke_plan_renders_bash_runbook() -> None:
    report = build_report(label="unit")

    bash = render_bash(report)

    assert bash.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in bash
    assert "cd /root/autodl-tmp/camp_core" in bash
    assert "== camp_sync ==" in bash
    assert "== head_audit ==" in bash
    assert "== baseline_replay ==" in bash
    assert "== candidate_replay ==" in bash
    assert "--camp_external_context_payload_logging" in bash
    assert "7a1d33da277a1992ec474b5383a0c963c72e04e4" in bash
    assert "Full36" in bash
    assert "external_context_payload_paired_three_step_smoke_complete" in bash


def test_external_context_payload_smoke_plan_rejects_formal_seed() -> None:
    report = build_report(smoke=replace(SmokeSpec(), seed=11))

    assert report["final_decision"]["status"] != READY_STATUS
    assert report["final_decision"]["new_replay_authorized"] is False
    formal_check = next(
        check
        for check in report["plan_checks"]
        if check["name"] == "scope_seed_is_nonformal"
    )
    assert formal_check["passed"] is False


def test_external_context_payload_smoke_plan_rejects_missing_payload_audit(
    tmp_path: Path,
) -> None:
    report = build_report(payload_audit_source=tmp_path / "missing.py")

    assert report["final_decision"]["status"] != READY_STATUS
    assert report["final_decision"]["new_replay_authorized"] is False
    check = next(
        item for item in report["source_checks"] if item["name"] == "payload_audit_available"
    )
    assert check["passed"] is False


def test_external_context_payload_smoke_plan_cli_writes_bash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    output_bash = tmp_path / "run.sh"
    monkeypatch.setattr(
        "sys.argv",
        [
            "external-context-smoke-plan",
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
    assert "External Context Payload Smoke Plan" in output_md.read_text(
        encoding="utf-8"
    )
    assert "external_context_payload_paired_three_step_smoke_complete" in (
        output_bash.read_text(encoding="utf-8")
    )
