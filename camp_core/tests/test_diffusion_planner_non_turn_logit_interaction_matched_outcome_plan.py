from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_non_turn_logit_interaction_payload import (
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_LATENCY_KEYS,
    build_non_turn_logit_interaction_payload,
)
from scripts.integrations.analyze_diffusion_planner_non_turn_logit_interaction_matched_outcomes import (
    analyze,
)
from scripts.integrations.plan_diffusion_planner_non_turn_logit_interaction_matched_outcome import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)
from scripts.integrations.plan_diffusion_planner_non_turn_logit_interaction_payload_smoke import (
    SmokeSpec,
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


def _outcomes() -> list[dict]:
    return [
        {
            "value": 1.0,
            "feasible": True,
            "collision": False,
            "near_miss": False,
            "lane_violation": False,
            "red_light_violation": False,
            "mean_jerk_mps3": 0.2,
            "mean_lateral_acceleration_mps2": 0.1,
        },
        {
            "value": 0.5,
            "feasible": True,
            "collision": False,
            "near_miss": False,
            "lane_violation": False,
            "red_light_violation": False,
            "mean_jerk_mps3": 0.3,
            "mean_lateral_acceleration_mps2": 0.2,
        },
        {
            "value": -1.0,
            "feasible": False,
            "collision": True,
            "near_miss": True,
            "lane_violation": False,
            "red_light_violation": False,
            "mean_jerk_mps3": 1.0,
            "mean_lateral_acceleration_mps2": 0.8,
        },
    ]


def _record(*, payload: dict | None = None, outcomes: list[dict] | None = None) -> dict:
    payload = _payload() if payload is None else payload
    outcomes = _outcomes() if outcomes is None else outcomes
    record = {
        "non_turn_logit_interaction_payload_logging": payload,
        "candidate_closed_loop_outcomes": outcomes,
    }
    record.update(payload["latency_ms"])
    return record


def _write_log(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records), encoding="utf-8")


def _smoke(*, passed: bool = True, payload_latency: float = 0.05) -> dict:
    return {
        "final_decision": {
            "status": (
                "non_turn_logit_interaction_payload_smoke_passed"
                if passed
                else "non_turn_logit_interaction_payload_smoke_rejected"
            ),
            "passed": passed,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "counts": {
            "records": 3,
            "candidate_payload_records": 3,
            "available_payload_records": 3,
            "invalid_payload_records": 0,
        },
        "latency_ms": {
            "latency_ms_non_turn_logit_interaction_payload": payload_latency,
            "latency_ms_reward_route_progress": 5.0,
        },
    }


def _selector_equivalence(*, equivalent: bool = True, mismatches: int = 0) -> dict:
    return {
        "equivalent": equivalent,
        "exact_field_mismatches": {"selected_index": mismatches},
        "numeric_field_mismatches": {"scores": 0},
        "numeric_shape_mismatches": {"scores": 0},
        "numeric_nonexact_entries": {"scores": 0},
    }


def _dataset_audit(*, passed: bool = True) -> dict:
    return {
        "passed": passed,
        "checks": {
            "forbidden_seed_check": True,
            "closed_loop_outcomes_forbidden": True,
            "finite_candidate_contract_verified": True,
        },
    }


def _ready_report(**kwargs) -> dict:
    return build_report(
        payload_smoke_audit=kwargs.pop("payload_smoke_audit", _smoke()),
        selector_equivalence=kwargs.pop(
            "selector_equivalence",
            _selector_equivalence(),
        ),
        dataset_audit=kwargs.pop("dataset_audit", _dataset_audit()),
        **kwargs,
    )


def test_matched_outcome_contract_audit_accepts_payload_and_outcomes(
    tmp_path: Path,
) -> None:
    log = tmp_path / "camp_selection_log.json"
    _write_log(log, [_record(), _record()])

    report = analyze(
        [log],
        expected_logs=1,
        expected_records=2,
        expected_candidates=3,
    )

    assert report["final_decision"]["passed"] is True
    assert report["counts"]["payload_records"] == 2
    assert report["counts"]["outcome_records"] == 2
    assert report["counts"]["candidate_rows"] == 6
    assert set(report["latency_ms"]) == set(
        NON_TURN_LOGIT_INTERACTION_PAYLOAD_LATENCY_KEYS
    )


def test_matched_outcome_contract_audit_rejects_payload_with_outcomes(
    tmp_path: Path,
) -> None:
    payload = deepcopy(_payload())
    payload["candidate_closed_loop_outcomes"] = _outcomes()
    log = tmp_path / "camp_selection_log.json"
    _write_log(log, [_record(payload=payload)])

    report = analyze(
        [log],
        expected_logs=1,
        expected_records=1,
        expected_candidates=3,
    )

    assert report["final_decision"]["passed"] is False
    assert any("payload contains candidate outcomes" in error for error in report["validation"]["errors"])


def test_matched_outcome_contract_audit_rejects_missing_outcomes(
    tmp_path: Path,
) -> None:
    log = tmp_path / "camp_selection_log.json"
    record = _record()
    record.pop("candidate_closed_loop_outcomes")
    _write_log(log, [record])

    report = analyze(
        [log],
        expected_logs=1,
        expected_records=1,
        expected_candidates=3,
    )

    assert report["final_decision"]["passed"] is False
    assert any("candidate_closed_loop_outcomes" in error for error in report["validation"]["errors"])


def test_matched_outcome_contract_audit_rejects_formal_seed_path(
    tmp_path: Path,
) -> None:
    log = tmp_path / "seed_11" / "camp_selection_log.json"
    _write_log(log, [_record()])

    report = analyze(
        [tmp_path],
        expected_logs=1,
        expected_records=1,
        expected_candidates=3,
    )

    assert report["final_decision"]["passed"] is False
    assert any("formal_seed_records" in error for error in report["validation"]["errors"])


def test_matched_outcome_plan_ready_for_contract_scope() -> None:
    report = _ready_report(label="unit")

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["paired_smoke_execution_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["Full36_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["CAMP_retraining_authorized"] is False
    assert decision["outcome_separability_authorized"] is False
    assert report["coverage_targets"]["matched_records"] == 3
    assert report["coverage_targets"]["matched_candidate_rows"] == 24
    assert all(check["passed"] for check in report["source_checks"])
    assert all(check["passed"] for check in report["plan_checks"])

    assert "--camp_collect_closed_loop_outcomes" not in report["commands"]["baseline_replay"]
    assert "--camp_non_turn_logit_interaction_payload_logging" not in report["commands"]["baseline_replay"]
    assert "--camp_collect_closed_loop_outcomes" in report["commands"]["matched_replay"]
    assert "--camp_non_turn_logit_interaction_payload_logging" in report["commands"]["matched_replay"]
    dataset_command = report["commands"]["dataset_required_outcome_audit"]
    assert dataset_command[dataset_command.index("--closed_loop_outcome_policy") + 1] == "required"


def test_matched_outcome_plan_rejects_failed_source() -> None:
    report = _ready_report(payload_smoke_audit=_smoke(passed=False))

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "payload_smoke_passed" in failed


def test_matched_outcome_plan_rejects_formal_seed() -> None:
    report = _ready_report(spec=SmokeSpec(seed=11))

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert failed == ["formal_seed_excluded"]


def test_matched_outcome_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    smoke_path = tmp_path / "smoke.json"
    selector_path = tmp_path / "selector.json"
    dataset_path = tmp_path / "dataset.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    smoke_path.write_text(json.dumps(_smoke()), encoding="utf-8")
    selector_path.write_text(json.dumps(_selector_equivalence()), encoding="utf-8")
    dataset_path.write_text(json.dumps(_dataset_audit()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan_diffusion_planner_non_turn_logit_interaction_matched_outcome.py",
            "--payload_smoke_audit_json",
            str(smoke_path),
            "--selector_equivalence_json",
            str(selector_path),
            "--dataset_audit_json",
            str(dataset_path),
            "--label",
            "unit_cli",
            "--output_root",
            "/tmp/non_turn_matched",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["plan_spec"]["root"] == "/tmp/non_turn_matched"
    markdown = output_md.read_text(encoding="utf-8")
    assert "--camp_non_turn_logit_interaction_payload_logging" in markdown
    assert "--camp_collect_closed_loop_outcomes" in markdown
