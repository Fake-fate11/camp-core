from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.diagnose_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _plan() -> dict[str, object]:
    return {
        "final_decision": {
            "status": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "mixed_result_nonpromotion_diagnosis_plan_ready"
            ),
            "passed": True,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "mixed_result_nonpromotion_diagnosis_authorization_only"
            ),
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
        }
    }


def _result_review() -> dict[str, object]:
    return {
        "final_decision": {
            "status": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "evaluation_result_review_ready"
            ),
            "passed": True,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "mixed_result_nonpromotion_diagnosis_plan_only"
            ),
            "result_classification": "mixed_nonpromotion",
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
        }
    }


def _execution(*, no_worse: bool = False) -> dict[str, object]:
    lambda_rows = [
        {
            "lambda": 0.0,
            "changed_selected_index": False,
            "safety_cost_delta_vs_logged_selected": 0.0,
        },
        {
            "lambda": 0.2,
            "changed_selected_index": True,
            "safety_cost_delta_vs_logged_selected": -0.02,
            "hard_components_worse_than_logged": [],
        },
        {
            "lambda": 1.0,
            "changed_selected_index": True,
            "safety_cost_delta_vs_logged_selected": -0.01 if no_worse else 0.03,
            "hard_components_worse_than_logged": [],
        },
    ]
    records = []
    for index in range(4):
        records.append(
            {
                "run_id": "sample_tl59_seed1_npc0_tlon" if index < 2 else "nishi_release_seed2_npc4_tlon",
                "record_index": index,
                "fallback_retained": index >= 2,
                "passed": True,
                "lambda_results": lambda_rows,
            }
        )
    return {
        "final_decision": {
            "status": "candidate_set_consensus_shadow_atom_safety_score_evaluation_ready",
            "passed": True,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "evaluation_result_review_only"
            ),
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
        },
        "evaluation_records": records,
    }


def test_mixed_result_nonpromotion_diagnosis_ready() -> None:
    report = build_report(plan=_plan(), result_review=_result_review(), execution=_execution())
    decision = report["final_decision"]
    summary = report["diagnosis_summary"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["safety_benefit_evidence"] is False
    assert decision["atom_promotion_authorized"] is False
    assert summary["better_only_lambda_count"] == 1
    assert summary["worse_lambda_count"] == 1
    assert summary["by_fallback"]["fallback"]["changed_records"] == 4
    assert summary["by_fallback"]["nonfallback"]["changed_records"] == 4


def test_mixed_result_nonpromotion_diagnosis_rejects_unmixed_execution() -> None:
    report = build_report(
        plan=_plan(),
        result_review=_result_review(),
        execution=_execution(no_worse=True),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "diagnosis_worse_present" in report["final_decision"]["failed_checks"]


def test_mixed_result_nonpromotion_diagnosis_rejects_bad_source() -> None:
    plan = _plan()
    plan["final_decision"]["passed"] = False  # type: ignore[index]

    report = build_report(plan=plan, result_review=_result_review(), execution=_execution())

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_passed" in report["final_decision"]["failed_checks"]


def test_mixed_result_nonpromotion_diagnosis_markdown_boundaries() -> None:
    markdown = render_markdown(
        build_report(plan=_plan(), result_review=_result_review(), execution=_execution())
    )

    assert "Mixed Result Non-Promotion Diagnosis" in markdown
    assert "Safety benefit evidence: `False`" in markdown
    assert "Atom promotion authorized: `False`" in markdown
    assert "classical Benders" in markdown


def test_mixed_result_nonpromotion_diagnosis_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan_json = tmp_path / "plan.json"
    review_json = tmp_path / "review.json"
    execution_json = tmp_path / "execution.json"
    output_json = tmp_path / "diagnosis.json"
    output_md = tmp_path / "diagnosis.md"
    plan_json.write_text(json.dumps(_plan()), encoding="utf-8")
    review_json.write_text(json.dumps(_result_review()), encoding="utf-8")
    execution_json.write_text(json.dumps(_execution()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "mixed-result-nonpromotion-diagnosis",
            "--plan_json",
            str(plan_json),
            "--result_review_json",
            str(review_json),
            "--execution_json",
            str(execution_json),
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--require_pass",
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Non-Promotion Diagnosis" in output_md.read_text(encoding="utf-8")
