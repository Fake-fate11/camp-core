from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _result_review(
    *,
    status: str = (
        "candidate_set_consensus_shadow_atom_safety_score_"
        "evaluation_result_review_ready"
    ),
    passed: bool = True,
    authorized_next_work: str | None = (
        "candidate_set_consensus_shadow_atom_safety_score_"
        "mixed_result_nonpromotion_diagnosis_plan_only"
    ),
    classification: str = "mixed_nonpromotion",
    worse_lambda_count: int = 2,
    blocked_action: bool = False,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": status,
            "passed": passed,
            "authorized_next_work": authorized_next_work,
            "safety_score_evaluation_result_review_ready": passed,
            "mixed_result_nonpromotion_diagnosis_plan_authorized": passed,
            "result_classification": classification,
            "sample_too_small_for_promotion": True,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": blocked_action,
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
            "failed_checks": [],
        },
        "result_classification": {
            "classification": classification,
            "positive_changed_lambda_count": 5,
            "better_only_lambda_count": 3,
            "worse_lambda_count": worse_lambda_count,
            "positive_mean_worse_lambda_count": worse_lambda_count,
            "zero_lambda_changed_records": 0,
            "max_changed_records": 11,
            "sample_too_small_for_promotion": True,
            "safety_benefit_evidence": False,
            "atom_promotion_recommended": False,
        },
    }


def test_mixed_result_nonpromotion_diagnosis_plan_ready() -> None:
    report = build_report(
        result_review=_result_review(),
        result_review_json="/artifact/review.json",
        execution_root="/artifact/execution",
        label="unit",
    )
    decision = report["final_decision"]
    plan = report["diagnosis_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["mixed_result_nonpromotion_diagnosis_plan_ready"] is True
    assert decision["mixed_result_nonpromotion_diagnosis_authorization_gate_authorized"] is True
    assert decision["mixed_result_nonpromotion_diagnosis_authorized"] is False
    assert decision["safety_benefit_evidence"] is False
    assert decision["atom_promotion_authorized"] is False
    assert plan["executes_diagnosis_now"] is False
    assert plan["requires_new_replay"] is False
    assert plan["requires_atom_promotion"] is False
    assert len(plan["diagnostic_questions"]) >= 3
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_mixed_result_nonpromotion_diagnosis_plan_rejects_source_not_ready() -> None:
    report = build_report(
        result_review=_result_review(
            status=(
                "candidate_set_consensus_shadow_atom_safety_score_"
                "evaluation_result_review_rejected"
            ),
            passed=False,
            authorized_next_work=None,
        )
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_status" in failed
    assert "source_passed" in failed
    assert "source_authorizes_diagnosis_plan" in failed


def test_mixed_result_nonpromotion_diagnosis_plan_rejects_blocked_action() -> None:
    report = build_report(result_review=_result_review(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_atom_promotion" in report["final_decision"]["failed_checks"]
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_mixed_result_nonpromotion_diagnosis_plan_rejects_unmixed_source() -> None:
    report = build_report(
        result_review=_result_review(
            classification="directional_signal_only_not_promotable",
            worse_lambda_count=0,
        )
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_classification_mixed_nonpromotion" in failed
    assert "source_worse_lambdas_present" in failed


def test_mixed_result_nonpromotion_diagnosis_plan_markdown_boundaries() -> None:
    markdown = render_markdown(build_report(result_review=_result_review()))

    assert "Mixed Result Non-Promotion Diagnosis Plan" in markdown
    assert "Diagnosis execution authorized: `False`" in markdown
    assert "Safety benefit evidence: `False`" in markdown
    assert "Atom promotion authorized: `False`" in markdown
    assert "classical Benders" in markdown


def test_mixed_result_nonpromotion_diagnosis_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_json = tmp_path / "result_review.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    source_json.write_text(json.dumps(_result_review()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "mixed-result-nonpromotion-diagnosis-plan",
            "--result_review_json",
            str(source_json),
            "--execution_root",
            "/artifact/execution",
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
    assert payload["diagnosis_plan"]["execution_root"] == "/artifact/execution"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Non-Promotion Diagnosis Plan" in output_md.read_text(encoding="utf-8")
