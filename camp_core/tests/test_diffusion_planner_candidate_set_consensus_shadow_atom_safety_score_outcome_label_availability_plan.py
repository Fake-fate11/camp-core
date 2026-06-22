from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_outcome_label_availability import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


RUN_IDS = (
    "sample_tl59_seed1_npc0_tlon",
    "sample_tl59_seed2_npc4_tlon",
    "sample_tl59_seed3_npc4_tloff",
    "sample_normal2_seed1_npc0_tloff",
    "nishi_release_seed2_npc4_tlon",
    "nishi_lanechange_seed4_npc4_tloff",
)


def _execution(
    *,
    status: str = "candidate_set_consensus_shadow_atom_safety_score_evaluation_rejected",
    failed_checks: list[str] | None = None,
    valid_records: int = 0,
    outcome_available_records: int = 0,
    **decision_overrides: object,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": False,
        "authorized_next_work": None,
        "failed_checks": failed_checks
        or [
            "all_records_valid",
            "all_records_have_outcome_labels",
            "record_errors_empty",
            "positive_lambda_changes_present",
        ],
        "safety_score_evaluation_ready": False,
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }
    decision.update(decision_overrides)
    return {
        "final_decision": decision,
        "evaluation_summary": {
            "records": 60,
            "valid_records": valid_records,
            "outcome_available_records": outcome_available_records,
            "formal_seed_log_count": 0,
            "record_error_counts": {
                "outcome_evaluation_error:missing candidate outcomes": 60
            },
        },
    }


def _outcome(index: int) -> dict[str, object]:
    return {
        "candidate_index": index,
        "progress_m": 10.0,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
        "mean_jerk_mps3": 1.0,
        "mean_lateral_acceleration_mps2": 0.5,
    }


def _write_candidate_root(
    root: Path,
    *,
    include_outcomes: bool = False,
    formal_seed: bool = False,
) -> None:
    for run_id in RUN_IDS:
        actual_id = "sample_tl59_seed11_npc0_tlon" if formal_seed and run_id == RUN_IDS[0] else run_id
        run_root = root / actual_id
        run_root.mkdir(parents=True)
        rows = []
        for _ in range(10):
            row: dict[str, object] = {
                "num_candidates": 8,
                "selected_index": 0,
                "candidate_horizon_union_planned_red_light_cost": [0.0] * 8,
            }
            if include_outcomes:
                row["candidate_closed_loop_outcomes"] = [
                    _outcome(index) for index in range(8)
                ]
            rows.append(row)
        (run_root / "camp_selection_log.json").write_text(
            json.dumps(rows),
            encoding="utf-8",
        )


def test_outcome_label_availability_plan_ready_for_missing_labels(tmp_path: Path) -> None:
    root = tmp_path / "logging_enabled"
    _write_candidate_root(root)

    report = build_report(safety_execution=_execution(), candidate_root=root)
    decision = report["final_decision"]
    availability = report["current_candidate_root_availability"]
    plan = report["outcome_label_availability_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["outcome_label_availability_plan_ready"] is True
    assert decision["outcome_label_existing_source_search_authorized"] is True
    assert decision["outcome_label_generation_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["safety_benefit_evidence"] is False
    assert availability["log_count"] == 6
    assert availability["records"] == 60
    assert availability["candidate_count_compatible_records"] == 60
    assert availability["candidate_closed_loop_outcome_records"] == 0
    assert availability["planned_red_records"] == 60
    assert plan["existing_source_search_authorized"] is True
    assert plan["outcome_label_generation_authorized"] is False
    assert "candidate_closed_loop_outcomes" in report["analysis"]["math_boundary"]


def test_outcome_label_availability_plan_rejects_source_without_outcome_gap(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_candidate_root(root)

    report = build_report(
        safety_execution=_execution(failed_checks=["all_records_valid"]),
        candidate_root=root,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_outcome_label_failure" in report["final_decision"][
        "failed_checks"
    ]


def test_outcome_label_availability_plan_rejects_blocked_source_action(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_candidate_root(root)

    report = build_report(
        safety_execution=_execution(camp_retraining_authorized=True),
        candidate_root=root,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_outcome_label_availability_plan_rejects_formal_seed_log(tmp_path: Path) -> None:
    root = tmp_path / "logging_enabled"
    _write_candidate_root(root, formal_seed=True)

    report = build_report(safety_execution=_execution(), candidate_root=root)

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = report["final_decision"]["failed_checks"]
    assert "candidate_no_formal_seed_logs" in failed
    assert "candidate_run_ids_match_plan" in failed


def test_outcome_label_availability_plan_rejects_existing_outcomes(tmp_path: Path) -> None:
    root = tmp_path / "logging_enabled"
    _write_candidate_root(root, include_outcomes=True)

    report = build_report(safety_execution=_execution(), candidate_root=root)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "candidate_outcome_records_absent" in report["final_decision"][
        "failed_checks"
    ]


def test_outcome_label_availability_plan_markdown_states_boundaries(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_candidate_root(root)

    markdown = render_markdown(
        build_report(safety_execution=_execution(), candidate_root=root)
    )

    assert "Outcome-Label Availability Plan" in markdown
    assert "Outcome-label generation authorized: `False`" in markdown
    assert "Replay authorized: `False`" in markdown
    assert "existing-source search" in markdown
    assert "classical Benders" in markdown


def test_outcome_label_availability_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_candidate_root(root)
    source_json = tmp_path / "safety_execution.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    source_json.write_text(json.dumps(_execution()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-safety-score-outcome-label-availability-plan",
            "--safety_execution_json",
            str(source_json),
            "--candidate_root",
            str(root),
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
    assert "Outcome-Label Availability Plan" in output_md.read_text(encoding="utf-8")
