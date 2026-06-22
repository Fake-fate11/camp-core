from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _dry_run(
    *,
    records: int = 60,
    changed_records: int = 39,
    ranking_signal_records: int = 60,
    **decision_overrides: object,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": "candidate_set_consensus_shadow_atom_dry_run_ready",
        "passed": True,
        "authorized_next_work": (
            "candidate_set_consensus_shadow_atom_dry_run_result_review_only"
        ),
        "shadow_atom_dry_run_ready": True,
        "atom_promotion_authorized": False,
        "safety_benefit_evidence": False,
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
        "max_shadow_zero_weight_score_abs_diff": 0.0,
        "max_shadow_zero_weight_selection_score_abs_diff": 0.0,
    }
    decision.update(decision_overrides)
    return {
        "final_decision": decision,
        "dry_run_summary": {
            "records": records,
            "valid_records": records,
            "available_records": records,
            "shadow_appended_records": records,
            "ranking_signal_records": ranking_signal_records,
            "consensus_only_would_change_selected_index_records": changed_records,
            "formal_seed_log_count": 0,
            "record_error_counts": {},
            "max_shadow_zero_weight_score_abs_diff": 0.0,
            "max_shadow_zero_weight_selection_score_abs_diff": 0.0,
        },
    }


def test_shadow_atom_weight_sensitivity_plan_ready() -> None:
    report = build_report(shadow_dry_run=_dry_run(), label="unit")
    decision = report["final_decision"]
    plan = report["sensitivity_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["weight_sensitivity_plan_ready"] is True
    assert decision["sensitivity_implementation_authorized"] is True
    assert decision["sensitivity_execution_authorized"] is False
    assert decision["atom_promotion_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["expected_logs"] == 6
    assert plan["expected_records"] == 60
    assert plan["expected_candidates"] == 8
    assert plan["lambda_grid"][0] == 0.0
    assert max(plan["lambda_grid"]) == 1.0
    assert "score'_k(lambda)" in report["analysis"]["math_boundary"]


def test_shadow_atom_weight_sensitivity_plan_rejects_source_not_ready() -> None:
    report = build_report(
        shadow_dry_run=_dry_run(
            status="candidate_set_consensus_shadow_atom_dry_run_rejected",
            passed=False,
            authorized_next_work=None,
            shadow_atom_dry_run_ready=False,
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = report["final_decision"]["failed_checks"]
    assert "source_status" in failed
    assert "source_passed" in failed
    assert "source_authorizes_result_review" in failed


def test_shadow_atom_weight_sensitivity_plan_rejects_missing_change_signal() -> None:
    report = build_report(shadow_dry_run=_dry_run(changed_records=0))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_consensus_only_change_present" in report["final_decision"][
        "failed_checks"
    ]


def test_shadow_atom_weight_sensitivity_plan_rejects_bad_lambda_grid() -> None:
    report = build_report(shadow_dry_run=_dry_run(), lambda_grid=(0.01, 0.1))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "lambda_grid_contains_zero" in report["final_decision"]["failed_checks"]


def test_shadow_atom_weight_sensitivity_plan_rejects_blocked_action() -> None:
    report = build_report(shadow_dry_run=_dry_run(camp_retraining_authorized=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_shadow_atom_weight_sensitivity_plan_markdown_states_boundaries() -> None:
    markdown = render_markdown(build_report(shadow_dry_run=_dry_run()))

    assert "Candidate-Set Consensus Shadow Atom Weight-Sensitivity Plan" in markdown
    assert "Sensitivity execution authorized: `False`" in markdown
    assert "score'_k(lambda)" in markdown
    assert "classical Benders" in markdown


def test_shadow_atom_weight_sensitivity_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_json = tmp_path / "shadow_dry_run.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    source_json.write_text(json.dumps(_dry_run()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-shadow-atom-weight-sensitivity-plan",
            "--shadow_dry_run_json",
            str(source_json),
            "--label",
            "unit_cli",
            "--candidate_root",
            "/tmp/replay/logging_enabled",
            "--audit_root",
            "/tmp/replay/audit",
            "--lambda_grid",
            "0.0",
            "--lambda_grid",
            "0.25",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["sensitivity_plan"]["candidate_root"] == "/tmp/replay/logging_enabled"
    assert payload["sensitivity_plan"]["lambda_grid"] == [0.0, 0.25]
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Candidate-Set Consensus Shadow Atom Weight-Sensitivity Plan" in (
        output_md.read_text(encoding="utf-8")
    )
