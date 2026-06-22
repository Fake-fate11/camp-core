from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.summarize_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_guarded_outcome_label_pass_execution import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    SUCCESS_MARKER,
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


def _authorization(**decision_overrides: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": (
            "candidate_set_consensus_shadow_atom_safety_score_"
            "guarded_outcome_label_pass_authorized"
        ),
        "passed": True,
        "authorized_next_work": (
            "candidate_set_consensus_shadow_atom_safety_score_"
            "guarded_outcome_label_pass_execution_only"
        ),
        "outcome_label_pass_execution_authorized": True,
        "formal_seeds_authorized": False,
        "label_attachment_authorized": False,
        "safety_score_evaluation_retry_authorized": False,
        "atom_promotion_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }
    decision.update(decision_overrides)
    return {
        "final_decision": decision,
        "plan_summary": {
            "expected_logs": 6,
            "expected_records": 60,
            "expected_candidates": 8,
            "route_run_ids": sorted(RUN_IDS),
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


def _write_logs(
    root: Path,
    *,
    include_outcomes: bool = True,
    run_ids: tuple[str, ...] = RUN_IDS,
) -> None:
    for run_id in run_ids:
        run_root = root / run_id
        run_root.mkdir(parents=True)
        rows = []
        for _ in range(10):
            row: dict[str, object] = {"num_candidates": 8}
            if include_outcomes:
                row["candidate_closed_loop_outcomes"] = [
                    _outcome(index) for index in range(8)
                ]
            rows.append(row)
        (run_root / "camp_selection_log.json").write_text(
            json.dumps(rows),
            encoding="utf-8",
        )


def _write_execution_files(root: Path, *, exit_code: str = "0", marker: bool = True) -> tuple[Path, Path]:
    log = root / "runbook.log"
    exit_code_path = root / "EXIT_CODE"
    log.write_text(SUCCESS_MARKER if marker else "failed", encoding="utf-8")
    exit_code_path.write_text(exit_code, encoding="utf-8")
    return log, exit_code_path


def test_guarded_outcome_label_pass_execution_summary_ready(tmp_path: Path) -> None:
    label_root = tmp_path / "labels"
    _write_logs(label_root)
    runbook_log, exit_code = _write_execution_files(tmp_path)

    report = build_report(
        authorization=_authorization(),
        label_root=label_root,
        runbook_log=runbook_log,
        exit_code_path=exit_code,
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["outcome_label_pass_executed"] is True
    assert decision["label_attachment_authorized"] is False
    assert decision["safety_score_evaluation_retry_authorized"] is False
    assert report["label_log_summary"]["log_count"] == 6
    assert report["label_log_summary"]["records"] == 60
    assert report["label_log_summary"]["complete_outcome_records"] == 60


def test_guarded_outcome_label_pass_execution_summary_rejects_auth_failure(
    tmp_path: Path,
) -> None:
    label_root = tmp_path / "labels"
    _write_logs(label_root)
    runbook_log, exit_code = _write_execution_files(tmp_path)

    report = build_report(
        authorization=_authorization(passed=False),
        label_root=label_root,
        runbook_log=runbook_log,
        exit_code_path=exit_code,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "authorization_passed" in report["final_decision"]["failed_checks"]


def test_guarded_outcome_label_pass_execution_summary_rejects_exit_failure(
    tmp_path: Path,
) -> None:
    label_root = tmp_path / "labels"
    _write_logs(label_root)
    runbook_log, exit_code = _write_execution_files(tmp_path, exit_code="1")

    report = build_report(
        authorization=_authorization(),
        label_root=label_root,
        runbook_log=runbook_log,
        exit_code_path=exit_code,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runbook_exit_code_zero" in report["final_decision"]["failed_checks"]


def test_guarded_outcome_label_pass_execution_summary_rejects_missing_outcomes(
    tmp_path: Path,
) -> None:
    label_root = tmp_path / "labels"
    _write_logs(label_root, include_outcomes=False)
    runbook_log, exit_code = _write_execution_files(tmp_path)

    report = build_report(
        authorization=_authorization(),
        label_root=label_root,
        runbook_log=runbook_log,
        exit_code_path=exit_code,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "label_complete_outcome_records" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_outcome_label_pass_execution_summary_rejects_formal_seed(
    tmp_path: Path,
) -> None:
    label_root = tmp_path / "labels"
    _write_logs(label_root, run_ids=("sample_tl59_seed11_npc0_tlon", *RUN_IDS[1:]))
    runbook_log, exit_code = _write_execution_files(tmp_path)

    report = build_report(
        authorization=_authorization(),
        label_root=label_root,
        runbook_log=runbook_log,
        exit_code_path=exit_code,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "label_no_formal_seed_logs" in report["final_decision"]["failed_checks"]
    assert "label_run_ids_match_authorization" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_outcome_label_pass_execution_summary_markdown_boundaries(
    tmp_path: Path,
) -> None:
    label_root = tmp_path / "labels"
    _write_logs(label_root)
    runbook_log, exit_code = _write_execution_files(tmp_path)

    markdown = render_markdown(
        build_report(
            authorization=_authorization(),
            label_root=label_root,
            runbook_log=runbook_log,
            exit_code_path=exit_code,
        )
    )

    assert "Outcome-Label Pass Execution Summary" in markdown
    assert "Label attachment authorized: `False`" in markdown
    assert "Safety-score retry authorized: `False`" in markdown
    assert "classical Benders" in markdown


def test_guarded_outcome_label_pass_execution_summary_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label_root = tmp_path / "labels"
    _write_logs(label_root)
    runbook_log, exit_code = _write_execution_files(tmp_path)
    auth_json = tmp_path / "authorization.json"
    output_json = tmp_path / "summary.json"
    output_md = tmp_path / "summary.md"
    auth_json.write_text(json.dumps(_authorization()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "summarize-guarded-outcome-label-pass-execution",
            "--authorization_json",
            str(auth_json),
            "--label_root",
            str(label_root),
            "--runbook_log",
            str(runbook_log),
            "--exit_code_path",
            str(exit_code),
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
    assert "Outcome-Label Pass Execution Summary" in output_md.read_text(
        encoding="utf-8"
    )
