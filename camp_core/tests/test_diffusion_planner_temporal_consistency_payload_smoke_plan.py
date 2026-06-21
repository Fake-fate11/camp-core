from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_temporal_consistency_payload import (
    TEMPORAL_CONSISTENCY_PAYLOAD_FIELD_NAMES,
    TEMPORAL_CONSISTENCY_PAYLOAD_LATENCY_KEYS,
    TEMPORAL_CONSISTENCY_PAYLOAD_SCHEMA_VERSION,
    build_temporal_consistency_payload,
)
from scripts.integrations.analyze_diffusion_planner_temporal_consistency_payload_smoke import (
    analyze,
)
from scripts.integrations.plan_diffusion_planner_temporal_consistency_payload_smoke import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    SmokeSpec,
    build_report,
    main,
    render_bash,
)


def _runtime_preflight(**decision_overrides: object) -> dict[str, object]:
    decision = {
        "status": "temporal_consistency_payload_runtime_preflight_ready",
        "passed": True,
        "runtime_preflight_ready": True,
        "authorized_next_work": (
            "default_off_temporal_consistency_tiny_paired_smoke_plan_only"
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
    return {"final_decision": decision}


def _candidates() -> np.ndarray:
    return np.asarray(
        [
            [[1.0, 0.0, 0.0, 0.0], [2.0, 0.0, 0.0, 0.0], [3.0, 0.0, 0.0, 0.0]],
            [[1.0, 1.0, 0.0, 0.0], [2.0, 1.0, 0.0, 0.0], [3.0, 1.0, 0.0, 0.0]],
        ],
        dtype=np.float64,
    )


def _previous() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0, 0.0],
            [3.0, 0.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    )


def _payload(*, available: bool) -> dict:
    return build_temporal_consistency_payload(
        candidates=_candidates(),
        previous_selected_plan=_previous() if available else None,
        support_steps=3,
        dt_s=0.1,
        elapsed_steps=1,
        min_overlap_steps=2,
    )


def _metadata(
    *,
    enabled: bool,
    records: int,
    available_records: int = 0,
    first_tick_fail_closed_records: int = 0,
) -> dict:
    return {
        "camp_temporal_consistency_payload_logging": {
            "schema_version": TEMPORAL_CONSISTENCY_PAYLOAD_SCHEMA_VERSION,
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
            "first_tick_fail_closed_records": first_tick_fail_closed_records,
            "fields": list(TEMPORAL_CONSISTENCY_PAYLOAD_FIELD_NAMES),
            "atom_candidate_names": ["previous_plan_temporal_consistency_rms_m"],
            "latency_fields": list(TEMPORAL_CONSISTENCY_PAYLOAD_LATENCY_KEYS),
        },
        "benchmark": {"seed": 1, "advance_mode": "perfect"},
    }


def _record(*, payload: dict | None) -> dict:
    record = {
        "selected_index": 0,
        "candidate_closed_loop_outcomes": None,
        "temporal_consistency_payload_logging": payload,
    }
    if payload is None:
        record.update({key: 0.0 for key in TEMPORAL_CONSISTENCY_PAYLOAD_LATENCY_KEYS})
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
                first_tick_fail_closed_records=len(
                    [
                        payload
                        for payload in payloads
                        if payload is not None
                        and payload.get("availability_reason")
                        == "previous_selected_plan_absent"
                    ]
                ),
            )
        ),
        encoding="utf-8",
    )


def test_temporal_consistency_payload_smoke_audit_accepts_expected_pattern(
    tmp_path: Path,
) -> None:
    payloads = [_payload(available=False), _payload(available=True), _payload(available=True)]
    _write_run(tmp_path / "baseline", enabled=False, payloads=[None, None, None])
    _write_run(tmp_path / "candidate", enabled=True, payloads=payloads)

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=3,
        expected_candidates=2,
        min_available_records=2,
        expected_first_tick_fail_closed=1,
    )

    assert report["final_decision"]["passed"] is True
    assert report["counts"]["candidate_payload_records"] == 3
    assert report["counts"]["available_payload_records"] == 2
    assert report["counts"]["first_tick_fail_closed_records"] == 1
    assert report["errors"] == []


def test_temporal_consistency_payload_smoke_audit_rejects_all_unavailable(
    tmp_path: Path,
) -> None:
    payloads = [_payload(available=False), _payload(available=False), _payload(available=False)]
    _write_run(tmp_path / "baseline", enabled=False, payloads=[None, None, None])
    _write_run(tmp_path / "candidate", enabled=True, payloads=payloads)

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=3,
        expected_candidates=2,
        min_available_records=2,
        expected_first_tick_fail_closed=1,
    )

    assert report["final_decision"]["passed"] is False
    assert any("available_payload_records" in error for error in report["errors"])
    assert any("first_tick_fail_closed_records" in error for error in report["errors"])


def test_temporal_consistency_payload_smoke_audit_rejects_negative_available_cost(
    tmp_path: Path,
) -> None:
    payload = deepcopy(_payload(available=True))
    payload["previous_plan_temporal_consistency_rms_m"] = [0.0, -1.0]
    _write_run(tmp_path / "baseline", enabled=False, payloads=[None])
    _write_run(tmp_path / "candidate", enabled=True, payloads=[payload])

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=2,
        min_available_records=1,
        expected_first_tick_fail_closed=0,
    )

    assert report["final_decision"]["passed"] is False
    assert any("negative" in error for error in report["errors"])


def test_temporal_consistency_payload_smoke_audit_rejects_formal_seed_path(
    tmp_path: Path,
) -> None:
    payload = _payload(available=True)
    _write_run(tmp_path / "baseline" / "seed_11", enabled=False, payloads=[None])
    _write_run(tmp_path / "candidate" / "seed_11", enabled=True, payloads=[payload])

    report = analyze(
        baseline_root=tmp_path / "baseline" / "seed_11",
        candidate_root=tmp_path / "candidate" / "seed_11",
        expected_logs=1,
        expected_records=1,
        expected_candidates=2,
        min_available_records=1,
        expected_first_tick_fail_closed=0,
    )

    assert report["final_decision"]["passed"] is False
    assert any("formal_seed_detected" in error for error in report["errors"])


def test_temporal_consistency_payload_smoke_plan_authorizes_paired_three_step_only() -> None:
    report = build_report(runtime_preflight=_runtime_preflight(), label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["new_replay_authorized"] is True
    assert report["final_decision"]["full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["final_decision"]["dp_modification_authorized"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
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
    assert "--camp_temporal_consistency_payload_logging" not in baseline_command
    assert "--camp_temporal_consistency_payload_logging" in candidate_command
    assert baseline_command[baseline_command.index("--steps") + 1] == "3"
    assert candidate_command[candidate_command.index("--seed") + 1] == "1"
    assert candidate_command[candidate_command.index("--num_candidates") + 1] == "8"
    assert (
        candidate_command[
            candidate_command.index(
                "--camp_temporal_consistency_payload_min_overlap_steps"
            )
            + 1
        ]
        == "2"
    )


def test_temporal_consistency_payload_smoke_plan_rejects_runtime_not_ready() -> None:
    report = build_report(
        runtime_preflight=_runtime_preflight(
            status="temporal_consistency_payload_runtime_preflight_blocked",
            passed=False,
            runtime_preflight_ready=False,
            authorized_next_work=None,
        )
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert report["final_decision"]["new_replay_authorized"] is False
    assert "runtime_status" in [
        check["name"] for check in report["plan_checks"] if not check["passed"]
    ]


def test_temporal_consistency_payload_smoke_plan_rejects_formal_seed() -> None:
    report = build_report(
        runtime_preflight=_runtime_preflight(),
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


def test_temporal_consistency_payload_smoke_plan_renders_bash_runbook() -> None:
    report = build_report(runtime_preflight=_runtime_preflight(), label="unit")

    bash = render_bash(report)

    assert bash.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in bash
    assert "cd /root/autodl-tmp/camp_core" in bash
    assert "== camp_sync ==" in bash
    assert "== head_audit ==" in bash
    assert "== baseline_replay ==" in bash
    assert "== candidate_replay ==" in bash
    assert "--camp_temporal_consistency_payload_logging" in bash
    assert "7a1d33da277a1992ec474b5383a0c963c72e04e4" in bash
    assert "Full36" in bash
    assert "temporal_consistency_payload_paired_three_step_smoke_complete" in bash


def test_temporal_consistency_payload_smoke_plan_cli_writes_bash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runtime = tmp_path / "runtime.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    output_bash = tmp_path / "run.sh"
    runtime.write_text(json.dumps(_runtime_preflight()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "temporal-smoke-plan",
            "--runtime_preflight_json",
            str(runtime),
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
    assert "Temporal Consistency Payload Smoke Plan" in output_md.read_text(
        encoding="utf-8"
    )
    assert "temporal_consistency_payload_paired_three_step_smoke_complete" in (
        output_bash.read_text(encoding="utf-8")
    )
