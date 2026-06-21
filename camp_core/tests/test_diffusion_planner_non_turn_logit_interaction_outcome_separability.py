from __future__ import annotations

import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_non_turn_logit_interaction_payload import (
    build_non_turn_logit_interaction_payload,
)
from scripts.integrations.analyze_diffusion_planner_non_turn_logit_interaction_outcome_separability import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
)
from scripts.integrations.plan_diffusion_planner_non_turn_logit_interaction_outcome_separability import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS as PLAN_READY_STATUS,
    REJECT_STATUS as PLAN_REJECT_STATUS,
    build_report,
    main,
)


def _contract(*, passed: bool = True) -> dict:
    return {
        "final_decision": {
            "status": (
                "non_turn_logit_interaction_matched_outcome_contract_passed"
                if passed
                else "non_turn_logit_interaction_matched_outcome_contract_rejected"
            ),
            "passed": passed,
            "authorized_next_work": (
                "non_turn_logit_interaction_outcome_separability_plan_only"
                if passed
                else "fix_non_turn_logit_interaction_matched_outcome_contract"
            ),
        },
        "counts": {
            "records": 2,
            "payload_records": 2,
            "outcome_records": 2,
            "candidate_rows": 6,
            "formal_seed_records": 0,
        },
    }


def _dataset(*, passed: bool = True) -> dict:
    return {
        "passed": passed,
        "checks": {
            "closed_loop_outcomes_required": True,
            "complete_closed_loop_outcomes": True,
            "finite_candidate_contract_verified": True,
            "forbidden_seed_check": True,
        },
    }


def _selector(*, equivalent: bool = True, mismatches: int = 0) -> dict:
    return {
        "equivalent": equivalent,
        "exact_field_mismatches": {"selected_index": mismatches},
        "numeric_field_mismatches": {"scores": 0},
        "numeric_shape_mismatches": {"scores": 0},
        "numeric_nonexact_entries": {"scores": 0},
    }


def _outcome(
    value: float,
    *,
    feasible: bool = True,
    progress_m: float = 10.0,
    collision: bool = False,
    lane: bool = False,
    red: bool = False,
) -> dict:
    return {
        "value": value,
        "feasible": feasible,
        "progress_m": progress_m,
        "collision": collision,
        "near_miss": False,
        "lane_violation": lane,
        "red_light_violation": red,
        "mean_jerk_mps3": 1.0,
        "mean_lateral_acceleration_mps2": 0.2,
    }


def _payload() -> dict:
    return build_non_turn_logit_interaction_payload(
        candidate_route_progress=[10.0, 10.0, 8.0],
        candidate_dp_prior_jerk_excess_cost=[0.0, 0.0, 5.0],
        candidate_count=3,
    )


def _record(seed: int = 1) -> dict:
    payload = _payload()
    record = {
        "seed": seed,
        "num_candidates": 3,
        "non_turn_logit_interaction_payload_logging": payload,
        "candidate_closed_loop_outcomes": [
            _outcome(0.0, progress_m=10.0),
            _outcome(1.0, progress_m=10.0),
            _outcome(-1.0, feasible=False, progress_m=8.0),
        ],
    }
    record.update(payload["latency_ms"])
    return record


def _write_log(tmp_path: Path, rows: list[dict]) -> Path:
    root = tmp_path / "run_seed_1"
    root.mkdir()
    path = root / "camp_selection_log.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    return root


def test_non_turn_interaction_separability_finds_promising_screen(
    tmp_path: Path,
) -> None:
    root = _write_log(tmp_path, [_record(), _record()])

    report = analyze(
        [root],
        matched_contract_report=_contract(),
        matched_dataset_report=_dataset(),
        expected_logs=1,
        expected_records=2,
        expected_candidates=3,
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["analysis"]["future_outcome_labels_used_for_atoms"] is False
    assert report["records"]["class_counts"]["beneficial_alternative"] == 2
    assert report["records"]["class_counts"]["harmful_alternative"] == 2
    best = report["ranked_screens"][0]
    assert best["descriptor"] == "comfort_progress_interaction_cost"
    assert best["atom_candidate_eligible"] is True
    assert best["promising_screen"] is True


def test_non_turn_interaction_separability_blocks_failed_source(
    tmp_path: Path,
) -> None:
    root = _write_log(tmp_path, [_record(), _record()])

    report = analyze(
        [root],
        matched_contract_report=_contract(passed=False),
        matched_dataset_report=_dataset(),
        expected_logs=1,
        expected_records=2,
        expected_candidates=3,
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["source_gate"]["contract_passed"] is False


def test_non_turn_interaction_separability_rejects_outcome_inside_payload(
    tmp_path: Path,
) -> None:
    record = _record()
    record["non_turn_logit_interaction_payload_logging"][
        "candidate_closed_loop_outcomes"
    ] = []
    root = _write_log(tmp_path, [record])

    with pytest.raises(ValueError, match="embeds outcome labels"):
        analyze(
            [root],
            matched_contract_report=_contract(),
            matched_dataset_report=_dataset(),
            expected_logs=1,
            expected_records=1,
            expected_candidates=3,
        )


def test_non_turn_interaction_separability_forbids_formal_seed(
    tmp_path: Path,
) -> None:
    root = _write_log(tmp_path, [_record(seed=11)])

    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze(
            [root],
            matched_contract_report=_contract(),
            matched_dataset_report=_dataset(),
            expected_logs=1,
            expected_records=1,
            expected_candidates=3,
            fail_on_formal_seeds=True,
        )


def test_non_turn_interaction_separability_plan_ready() -> None:
    report = build_report(
        matched_contract=_contract(),
        matched_dataset=_dataset(),
        selector_equivalence=_selector(),
        matched_selection_log=(
            "/root/autodl-tmp/camp_dp_non_turn_logit_interaction_matched_outcome_"
            "contract_v1/matched_interaction_outcomes/camp_selection_log.json"
        ),
        audit_root="/root/autodl-tmp/non_turn_separability/audit",
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == PLAN_READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["CAMP_retraining_authorized"] is False
    command = report["commands"]["non_turn_logit_interaction_outcome_separability"]
    assert "--fail_on_formal_seeds" in command
    assert "--selection_log" in command
    assert all(check["passed"] for check in report["source_checks"])


def test_non_turn_interaction_separability_plan_rejects_failed_contract() -> None:
    report = build_report(
        matched_contract=_contract(passed=False),
        matched_dataset=_dataset(),
        selector_equivalence=_selector(),
        matched_selection_log="/tmp/camp_selection_log.json",
        audit_root="/tmp/audit",
    )

    assert report["final_decision"]["status"] == PLAN_REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "matched_contract_passed" in failed


def test_non_turn_interaction_separability_plan_rejects_missing_source(
    tmp_path: Path,
) -> None:
    report = build_report(
        matched_contract=_contract(),
        matched_dataset=_dataset(),
        selector_equivalence=_selector(),
        matched_selection_log="/tmp/camp_selection_log.json",
        audit_root="/tmp/audit",
        separability_audit_source=tmp_path / "missing.py",
    )

    assert report["final_decision"]["status"] == PLAN_REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "separability_audit_available" in failed


def test_non_turn_interaction_separability_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    contract_path = tmp_path / "contract.json"
    dataset_path = tmp_path / "dataset.json"
    selector_path = tmp_path / "selector.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    contract_path.write_text(json.dumps(_contract()), encoding="utf-8")
    dataset_path.write_text(json.dumps(_dataset()), encoding="utf-8")
    selector_path.write_text(json.dumps(_selector()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan_diffusion_planner_non_turn_logit_interaction_outcome_separability.py",
            "--matched_contract_json",
            str(contract_path),
            "--matched_dataset_audit_json",
            str(dataset_path),
            "--selector_equivalence_json",
            str(selector_path),
            "--matched_selection_log",
            "/tmp/camp_selection_log.json",
            "--audit_root",
            "/tmp/audit",
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
    assert payload["final_decision"]["status"] == PLAN_READY_STATUS
    markdown = output_md.read_text(encoding="utf-8")
    assert "comfort_progress_interaction_cost" in markdown
    assert "--fail_on_formal_seeds" in markdown
