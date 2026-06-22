from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _weight_sensitivity(
    *,
    zero_changed: int = 0,
    max_changed: int = 11,
    formal_seed_log_count: int = 0,
    by_run: dict[str, object] | None = None,
    **decision_overrides: object,
) -> dict[str, object]:
    first_positive_changed = 0 if max_changed == 0 else 1
    by_lambda = [
        {"lambda": 0.0, "changed_records": zero_changed, "changed_rate": 0.0},
        {
            "lambda": 0.05,
            "changed_records": first_positive_changed,
            "changed_rate": first_positive_changed / 60.0,
        },
        {"lambda": 1.0, "changed_records": max_changed, "changed_rate": max_changed / 60.0},
    ]
    decision: dict[str, object] = {
        "status": "candidate_set_consensus_shadow_atom_weight_sensitivity_ready",
        "passed": True,
        "weight_sensitivity_ready": True,
        "authorized_next_work": (
            "candidate_set_consensus_shadow_atom_weight_sensitivity_result_review_only"
        ),
        "max_changed_records": max_changed,
        "min_critical_positive_lambda": 0.026845163286762983,
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
        "lambda_grid": [0.0, 0.05, 1.0],
        "sensitivity_summary": {
            "log_count": 6,
            "records": 60,
            "valid_records": 60,
            "available_records": 60,
            "ranking_signal_records": 46,
            "fallback_retained_records": 12,
            "formal_seed_log_count": formal_seed_log_count,
            "record_error_counts": {},
            "critical_positive_lambda_records": 39,
            "min_critical_positive_lambda": 0.026845163286762983,
            "lambda_grid": [0.0, 0.05, 1.0],
            "by_lambda": by_lambda,
            "by_run": by_run
            or {
                "sample_normal2_seed1_npc0_tloff": {
                    "records": 10,
                    "ranking_signal_records": 10,
                    "fallback_retained_records": 0,
                    "max_changed_records": 5,
                },
                "nishi_release_seed2_npc4_tlon": {
                    "records": 10,
                    "ranking_signal_records": 0,
                    "fallback_retained_records": 10,
                    "max_changed_records": 0,
                },
            },
        },
    }


def test_shadow_atom_safety_score_evaluation_plan_ready() -> None:
    report = build_report(weight_sensitivity=_weight_sensitivity(), label="unit")
    decision = report["final_decision"]
    plan = report["safety_score_evaluation_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["safety_score_evaluation_plan_ready"] is True
    assert decision["safety_score_evaluation_implementation_authorized"] is True
    assert decision["safety_score_evaluation_execution_authorized"] is False
    assert decision["atom_promotion_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["expected_logs"] == 6
    assert plan["expected_records"] == 60
    assert plan["expected_candidates"] == 8
    assert plan["lambda_grid"] == [0.0, 0.05, 1.0]
    assert "candidate_closed_loop_outcomes.progress_m" in plan["allowed_read_only_fields"]
    assert "candidate_horizon_union_planned_red_light_cost" in plan[
        "allowed_read_only_fields"
    ]
    assert plan["scenario_coverage"]["traffic_light"]
    assert plan["scenario_coverage"]["turn"]
    assert plan["scenario_coverage"]["normal"]
    assert len(plan["scenario_coverage"]["nishishinjuku"]) == 2
    assert "score'_k(lambda)" in report["analysis"]["math_boundary"]
    assert "candidate_closed_loop_outcomes" in report["analysis"]["math_boundary"]


def test_shadow_atom_safety_score_evaluation_plan_rejects_source_not_ready() -> None:
    report = build_report(
        weight_sensitivity=_weight_sensitivity(
            status="candidate_set_consensus_shadow_atom_weight_sensitivity_rejected",
            passed=False,
            weight_sensitivity_ready=False,
            authorized_next_work=None,
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = report["final_decision"]["failed_checks"]
    assert "source_status" in failed
    assert "source_passed" in failed
    assert "source_authorizes_result_review" in failed
    assert "source_weight_sensitivity_ready" in failed


def test_shadow_atom_safety_score_evaluation_plan_rejects_blocked_action() -> None:
    report = build_report(
        weight_sensitivity=_weight_sensitivity(camp_retraining_authorized=True)
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_shadow_atom_safety_score_evaluation_plan_rejects_lambda_zero_change() -> None:
    report = build_report(weight_sensitivity=_weight_sensitivity(zero_changed=1))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_lambda_zero_no_changes" in report["final_decision"]["failed_checks"]


def test_shadow_atom_safety_score_evaluation_plan_rejects_no_positive_change() -> None:
    report = build_report(weight_sensitivity=_weight_sensitivity(max_changed=0))

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = report["final_decision"]["failed_checks"]
    assert "source_positive_lambda_changes_present" in failed
    assert "source_max_changed_records_positive" in failed


def test_shadow_atom_safety_score_evaluation_plan_rejects_formal_seed_source() -> None:
    report = build_report(
        weight_sensitivity=_weight_sensitivity(formal_seed_log_count=1)
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_formal_seed_logs_zero" in report["final_decision"]["failed_checks"]


def test_shadow_atom_safety_score_evaluation_plan_markdown_states_boundaries() -> None:
    markdown = render_markdown(build_report(weight_sensitivity=_weight_sensitivity()))

    assert "Candidate-Set Consensus Shadow Atom Safety-Score Evaluation Plan" in markdown
    assert "Safety-score evaluation execution authorized: `False`" in markdown
    assert "Atom promotion authorized: `False`" in markdown
    assert "SafetyCost v1" in markdown
    assert "candidate_closed_loop_outcomes" in markdown
    assert "classical Benders" in markdown


def test_shadow_atom_safety_score_evaluation_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_json = tmp_path / "weight_sensitivity.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    source_json.write_text(json.dumps(_weight_sensitivity()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-shadow-atom-safety-score-evaluation-plan",
            "--weight_sensitivity_json",
            str(source_json),
            "--label",
            "unit_cli",
            "--candidate_root",
            "/tmp/replay/logging_enabled",
            "--audit_root",
            "/tmp/replay/audit",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["safety_score_evaluation_plan"]["candidate_root"] == (
        "/tmp/replay/logging_enabled"
    )
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Safety-Score Evaluation Plan" in output_md.read_text(encoding="utf-8")
