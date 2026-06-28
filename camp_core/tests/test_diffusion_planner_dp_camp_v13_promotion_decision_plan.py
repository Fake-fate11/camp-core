from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_promotion_decision import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


CAMP_HEAD = "5dd1515575e7ab8fb50a9be137e8fec0153b5590"


def _result_review(*, safety_claim: bool = False) -> dict[str, object]:
    return {
        "schema_version": "dp_camp_v13_offline_nonpromotion_static_reranker_result_review_v1",
        "artifact_summary": {
            "records_total": 51200,
            "records_without_feasible_candidate": 14058,
            "records_with_feasible_candidate": 37142,
            "training_records": 11262,
            "validation_records": 2796,
            "num_candidates": 8,
            "num_atoms": 14,
            "atom_schema_version": "dp_camp_v10_14d",
            "score_expression": "score_k(w)=a_k^T w",
        },
        "final_decision": {
            "status": "dp_camp_v13_offline_nonpromotion_static_reranker_result_review_ready",
            "passed": True,
            "authorized_next_work": (
                "dp_camp_v13_promotion_decision_plan_only_after_explicit_user_authorization"
            ),
            "result_review_ready": True,
            "promotion_decision_plan_authorized": True,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": safety_claim,
            "camp_over_dp_top1_claim_authorized": False,
            "training_authorized": False,
            "training_execution_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "failed_checks": [],
        },
    }


def _report() -> dict[str, object]:
    return build_report(
        result_review=_result_review(),
        result_review_json="/tmp/result_review.json",
        current_camp_head=CAMP_HEAD,
        label="unit",
        enabled=True,
    )


def test_promotion_decision_plan_ready_but_does_not_promote() -> None:
    report = _report()
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["promotion_decision_plan_ready"] is True
    assert decision["evidence_package_preflight_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert report["promotion_decision_plan"]["recommendation"] == (
        "do_not_promote_from_current_evidence_alone"
    )


def test_promotion_decision_plan_accepts_candidate_expansion_expected_counts() -> None:
    payload = _result_review()
    payload["artifact_summary"]["records_total"] = 102400  # type: ignore[index]
    payload["artifact_summary"]["records_without_feasible_candidate"] = 28468  # type: ignore[index]
    payload["artifact_summary"]["records_with_feasible_candidate"] = 73932  # type: ignore[index]
    payload["artifact_summary"]["training_records"] = 22836  # type: ignore[index]
    payload["artifact_summary"]["validation_records"] = 5632  # type: ignore[index]

    report = build_report(
        result_review=payload,
        result_review_json="/tmp/result_review.json",
        current_camp_head=CAMP_HEAD,
        label="candidate_expansion",
        expected_counts={
            "records_total": 102400,
            "records_without_feasible_candidate": 28468,
            "training_records": 22836,
            "validation_records": 5632,
        },
        enabled=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["source_summary"]["records_total"] == 102400
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_promotion_decision_plan_rejects_missing_enable() -> None:
    report = build_report(
        result_review=_result_review(),
        result_review_json="/tmp/result_review.json",
        current_camp_head=CAMP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "planning_enabled" in report["final_decision"]["failed_checks"]


def test_promotion_decision_plan_rejects_source_claim_leak() -> None:
    report = build_report(
        result_review=_result_review(safety_claim=True),
        result_review_json="/tmp/result_review.json",
        current_camp_head=CAMP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_safety_benefit_claim_authorized_false" in report["final_decision"][
        "failed_checks"
    ]


def test_promotion_decision_plan_rejects_contract_drift() -> None:
    payload = _result_review()
    payload["artifact_summary"]["num_candidates"] = 9  # type: ignore[index]

    report = build_report(
        result_review=payload,
        result_review_json="/tmp/result_review.json",
        current_camp_head=CAMP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "num_candidates_fixed" in report["final_decision"]["failed_checks"]


def test_promotion_decision_plan_markdown_states_boundary() -> None:
    markdown = render_markdown(_report())

    assert "Promotion-Decision Plan" in markdown
    assert "Actual promotion authorized: `False`" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "does not promote atoms or selectors" in markdown


def test_promotion_decision_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result_review = tmp_path / "result_review.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    result_review.write_text(json.dumps(_result_review()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "v13-promotion-decision-plan",
            "--result_review_json",
            str(result_review),
            "--current_camp_head",
            CAMP_HEAD,
            "--enable_v13_promotion_decision_planning",
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    assert main() == 0

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Promotion-Decision Plan" in output_md.read_text(encoding="utf-8")
