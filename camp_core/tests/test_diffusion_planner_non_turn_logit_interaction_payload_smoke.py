from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_non_turn_logit_interaction_payload import (
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_ATOM_CANDIDATE_NAMES,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_DIAGNOSTIC_FIELD_NAMES,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_LATENCY_KEYS,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_SCHEMA_VERSION,
    build_non_turn_logit_interaction_payload,
)
from scripts.integrations.analyze_diffusion_planner_non_turn_logit_interaction_payload_smoke import (
    ROUTE_PROGRESS_LATENCY_KEY,
    analyze,
)
from scripts.integrations.plan_diffusion_planner_non_turn_logit_interaction_payload_smoke import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
)


def _payload() -> dict:
    return build_non_turn_logit_interaction_payload(
        candidate_route_progress=np.asarray([10.0, 8.0, 11.0], dtype=np.float64),
        candidate_dp_prior_jerk_excess_cost=np.asarray(
            [0.0, 2.0, 1.0],
            dtype=np.float64,
        ),
        candidate_count=3,
    )


def _metadata(*, enabled: bool, records: int, available_records: int = 0) -> dict:
    return {
        "camp_non_turn_logit_interaction_payload_logging": {
            "schema_version": NON_TURN_LOGIT_INTERACTION_PAYLOAD_SCHEMA_VERSION,
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
            "fields": list(NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES),
            "diagnostic_field_names": list(
                NON_TURN_LOGIT_INTERACTION_PAYLOAD_DIAGNOSTIC_FIELD_NAMES
            ),
            "atom_candidate_names": list(
                NON_TURN_LOGIT_INTERACTION_PAYLOAD_ATOM_CANDIDATE_NAMES
            ),
            "latency_fields": list(NON_TURN_LOGIT_INTERACTION_PAYLOAD_LATENCY_KEYS),
        },
        "benchmark": {"seed": 1, "advance_mode": "perfect"},
    }


def _record(*, payload: dict | None) -> dict:
    record = {
        "selected_index": 0,
        "candidate_closed_loop_outcomes": None,
        "non_turn_logit_interaction_payload_logging": payload,
        ROUTE_PROGRESS_LATENCY_KEY: 0.2,
    }
    if payload is None:
        record.update(
            {key: 0.0 for key in NON_TURN_LOGIT_INTERACTION_PAYLOAD_LATENCY_KEYS}
        )
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


def test_non_turn_logit_interaction_payload_smoke_audit_accepts_payload(
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
        expected_candidates=3,
    )

    assert report["final_decision"]["passed"] is True
    assert report["counts"]["candidate_payload_records"] == 2
    assert report["counts"]["available_payload_records"] == 2
    assert report["counts"]["invalid_payload_records"] == 0
    assert report["errors"] == []
    assert report["latency_ms"][ROUTE_PROGRESS_LATENCY_KEY] == 0.2


def test_non_turn_logit_interaction_payload_smoke_audit_rejects_bad_interaction(
    tmp_path: Path,
) -> None:
    payload = deepcopy(_payload())
    payload["comfort_progress_interaction_cost"][1] += 1.0
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
    assert any("interaction is not progress_deficit" in error for error in report["errors"])


def test_non_turn_logit_interaction_payload_smoke_audit_rejects_closed_loop_outcome(
    tmp_path: Path,
) -> None:
    payload = _payload()
    _write_run(tmp_path / "baseline", enabled=False, payloads=[None])
    _write_run(tmp_path / "candidate", enabled=True, payloads=[payload])
    rows = json.loads(
        (tmp_path / "candidate" / "camp_selection_log.json").read_text(
            encoding="utf-8"
        )
    )
    rows[0]["candidate_closed_loop_outcomes"] = [{"collision": True}]
    (tmp_path / "candidate" / "camp_selection_log.json").write_text(
        json.dumps(rows),
        encoding="utf-8",
    )

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=3,
    )

    assert report["final_decision"]["passed"] is False
    assert any("closed-loop outcomes" in error for error in report["errors"])


def test_non_turn_logit_interaction_payload_smoke_audit_rejects_formal_seed_path(
    tmp_path: Path,
) -> None:
    _write_run(tmp_path / "baseline" / "seed_11", enabled=False, payloads=[None])
    _write_run(tmp_path / "candidate" / "seed_11", enabled=True, payloads=[_payload()])

    report = analyze(
        baseline_root=tmp_path / "baseline",
        candidate_root=tmp_path / "candidate",
        expected_logs=1,
        expected_records=1,
        expected_candidates=3,
    )

    assert report["final_decision"]["passed"] is False
    assert any("formal_seed_detected" in error for error in report["errors"])


def test_non_turn_logit_interaction_payload_smoke_plan_authorizes_three_step_only() -> None:
    report = build_report(label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["new_replay_authorized"] is True
    assert report["final_decision"]["closed_loop_smoke_authorized"] is True
    assert report["final_decision"]["Full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    assert report["final_decision"]["matched_outcome_audit_authorized"] is False
    baseline_command = report["commands"]["baseline_replay"]
    candidate_command = report["commands"]["candidate_replay"]
    assert "--camp_non_turn_logit_interaction_payload_logging" not in baseline_command
    assert "--camp_non_turn_logit_interaction_payload_logging" in candidate_command
    assert baseline_command[baseline_command.index("--steps") + 1] == "3"
    assert candidate_command[candidate_command.index("--seed") + 1] == "1"


def test_non_turn_logit_interaction_payload_smoke_plan_rejects_missing_audit(
    tmp_path: Path,
) -> None:
    report = build_report(payload_audit_source=tmp_path / "missing.py")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["new_replay_authorized"] is False
    failed = [check for check in report["source_checks"] if not check["passed"]]
    assert [check["name"] for check in failed] == ["payload_audit_available"]
