from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.review_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_outcome_label_source import (
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


def _execution(**decision_overrides: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": (
            "candidate_set_consensus_shadow_atom_safety_score_"
            "guarded_outcome_label_pass_execution_complete"
        ),
        "passed": True,
        "authorized_next_work": (
            "candidate_set_consensus_shadow_atom_safety_score_"
            "outcome_label_source_review_only"
        ),
        "outcome_label_source_review_authorized": True,
        "label_attachment_authorized": False,
        "safety_score_evaluation_retry_authorized": False,
    }
    decision.update(decision_overrides)
    return {
        "final_decision": decision,
        "label_log_summary": {
            "run_ids": sorted(RUN_IDS),
            "log_count": 6,
            "records": 60,
            "complete_outcome_records": 60,
        },
    }


def _outcomes() -> list[dict[str, object]]:
    return [{"candidate_index": index, "progress_m": 1.0} for index in range(8)]


def _row(*, outcomes: bool) -> dict[str, object]:
    row: dict[str, object] = {
        "num_candidates": 8,
        "selected_index": 0,
        "scores": [float(index) for index in range(8)],
        "selection_scores": [float(index) for index in range(8)],
        "weights": [1.0],
        "selection_weights": [1.0],
        "atoms": [[float(index)] for index in range(8)],
        "normalized_atoms": [[float(index)] for index in range(8)],
        "candidate_first_reference_xy": [[float(index), 0.0] for index in range(8)],
        "candidate_route_progress": [float(index) for index in range(8)],
        "candidate_step_reach": [float(index) for index in range(8)],
        "candidate_horizon_union_planned_red_light_cost": [0.0] * 8,
        "feasible_mask": [True] * 8,
        "infeasibility_reasons": [[] for _ in range(8)],
        "candidate_set_consensus_payload_logging": {
            "candidate_count": 8,
            "candidate_set_consensus_center_rms_m": [float(index) for index in range(8)],
            "candidate_set_consensus_center_rms_rank": list(range(8)),
            "default_off": True,
            "closed_loop_outcome_fields_read": False,
            "future_outcome_leakage": False,
            "classical_benders_claim": False,
        },
    }
    row["candidate_closed_loop_outcomes"] = _outcomes() if outcomes else None
    return row


def _write_roots(label_root: Path, broader_root: Path) -> None:
    for run_id in RUN_IDS:
        for root, outcomes in ((label_root, True), (broader_root, False)):
            run_root = root / run_id
            run_root.mkdir(parents=True)
            rows = [_row(outcomes=outcomes) for _ in range(10)]
            (run_root / "camp_selection_log.json").write_text(
                json.dumps(rows),
                encoding="utf-8",
            )


def test_outcome_label_source_review_ready(tmp_path: Path) -> None:
    label_root = tmp_path / "labels"
    broader_root = tmp_path / "broader"
    _write_roots(label_root, broader_root)

    report = build_report(
        execution_summary=_execution(),
        label_root=label_root,
        broader_candidate_root=broader_root,
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["safety_score_evaluation_retry_plan_authorized"] is True
    assert decision["label_attachment_authorized"] is False
    assert decision["safety_score_evaluation_retry_authorized"] is False
    assert report["source_review"]["compatibility_mismatch_count"] == 0
    assert report["source_review"]["payload_no_leak_records"] == 60


def test_outcome_label_source_review_rejects_execution_failure(tmp_path: Path) -> None:
    label_root = tmp_path / "labels"
    broader_root = tmp_path / "broader"
    _write_roots(label_root, broader_root)

    report = build_report(
        execution_summary=_execution(passed=False),
        label_root=label_root,
        broader_candidate_root=broader_root,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "execution_passed" in report["final_decision"]["failed_checks"]


def test_outcome_label_source_review_rejects_candidate_mismatch(tmp_path: Path) -> None:
    label_root = tmp_path / "labels"
    broader_root = tmp_path / "broader"
    _write_roots(label_root, broader_root)
    path = label_root / RUN_IDS[0] / "camp_selection_log.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    rows[0]["scores"][0] = 99.0
    path.write_text(json.dumps(rows), encoding="utf-8")

    report = build_report(
        execution_summary=_execution(),
        label_root=label_root,
        broader_candidate_root=broader_root,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "review_compatibility_mismatches_zero" in report["final_decision"][
        "failed_checks"
    ]


def test_outcome_label_source_review_rejects_broader_outcomes(tmp_path: Path) -> None:
    label_root = tmp_path / "labels"
    broader_root = tmp_path / "broader"
    _write_roots(label_root, broader_root)
    path = broader_root / RUN_IDS[0] / "camp_selection_log.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    rows[0]["candidate_closed_loop_outcomes"] = _outcomes()
    path.write_text(json.dumps(rows), encoding="utf-8")

    report = build_report(
        execution_summary=_execution(),
        label_root=label_root,
        broader_candidate_root=broader_root,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "review_broader_outcomes_absent" in report["final_decision"][
        "failed_checks"
    ]


def test_outcome_label_source_review_markdown_boundaries(tmp_path: Path) -> None:
    label_root = tmp_path / "labels"
    broader_root = tmp_path / "broader"
    _write_roots(label_root, broader_root)

    markdown = render_markdown(
        build_report(
            execution_summary=_execution(),
            label_root=label_root,
            broader_candidate_root=broader_root,
        )
    )

    assert "Outcome-Label Source Review" in markdown
    assert "Label attachment authorized: `False`" in markdown
    assert "Safety-score retry authorized: `False`" in markdown
    assert "classical Benders" in markdown


def test_outcome_label_source_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label_root = tmp_path / "labels"
    broader_root = tmp_path / "broader"
    _write_roots(label_root, broader_root)
    execution_json = tmp_path / "execution.json"
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"
    execution_json.write_text(json.dumps(_execution()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "review-outcome-label-source",
            "--execution_summary_json",
            str(execution_json),
            "--label_root",
            str(label_root),
            "--broader_candidate_root",
            str(broader_root),
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
    assert "Outcome-Label Source Review" in output_md.read_text(encoding="utf-8")
