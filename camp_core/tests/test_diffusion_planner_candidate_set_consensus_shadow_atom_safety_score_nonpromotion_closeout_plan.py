from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_nonpromotion_closeout import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _result_review_payload(
    *,
    status: str = (
        "candidate_set_consensus_shadow_atom_safety_score_"
        "mixed_result_nonpromotion_diagnosis_result_review_ready"
    ),
    passed: bool = True,
    classification: str = "confirmed_mixed_nonpromotion_closeout_needed",
    authorizes_closeout_plan: bool = True,
    blocked_action: bool = False,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": status,
            "passed": passed,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "nonpromotion_closeout_plan_only"
            ),
            "mixed_result_nonpromotion_diagnosis_result_review_ready": passed,
            "nonpromotion_closeout_plan_authorized": authorizes_closeout_plan,
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
        "result_review": {
            "closeout_classification": classification,
            "authorizes_closeout_plan": authorizes_closeout_plan,
            "interpretation": (
                "real but mixed non-promotion signal; not promotion-safe "
                "because worse rows remain present"
            ),
        },
    }


def test_nonpromotion_closeout_plan_ready() -> None:
    report = build_report(
        result_review=_result_review_payload(),
        result_review_json="/tmp/review.json",
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["nonpromotion_closeout_plan_ready"] is True
    assert decision["nonpromotion_closeout_authorization_gate_authorized"] is True
    assert decision["nonpromotion_closeout_authorized"] is False
    assert decision["atom_promotion_authorized"] is False
    assert report["closeout_plan"]["default_off_retained"] is True
    assert report["closeout_plan"]["requires_new_replay"] is False


def test_nonpromotion_closeout_plan_rejects_source_not_ready() -> None:
    report = build_report(
        result_review=_result_review_payload(status="candidate_set_consensus_bad", passed=False),
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_status" in failed
    assert "source_passed" in failed
    assert report["final_decision"]["authorized_next_work"] is None


def test_nonpromotion_closeout_plan_rejects_unconfirmed_classification() -> None:
    report = build_report(
        result_review=_result_review_payload(
            classification="promotion_candidate",
            authorizes_closeout_plan=False,
        ),
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_closeout_classification" in failed
    assert "source_review_authorizes_closeout" in failed


def test_nonpromotion_closeout_plan_rejects_blocked_action() -> None:
    report = build_report(result_review=_result_review_payload(blocked_action=True))

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_atom_promotion" in failed
    assert "source_no_blocked_actions" in failed
    assert report["final_decision"]["atom_promotion_authorized"] is False


def test_nonpromotion_closeout_plan_markdown_boundaries() -> None:
    markdown = render_markdown(build_report(result_review=_result_review_payload()))

    assert "Non-Promotion Closeout Plan" in markdown
    assert "Default-off retained: `True`" in markdown
    assert "Safety benefit evidence: `False`" in markdown
    assert "Atom promotion authorized: `False`" in markdown
    assert "formal seeds" in markdown
    assert "DP modification" in markdown
    assert "classical Benders" in markdown


def test_nonpromotion_closeout_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result_review_json = tmp_path / "review.json"
    output_json = tmp_path / "closeout_plan.json"
    output_md = tmp_path / "closeout_plan.md"
    result_review_json.write_text(
        json.dumps(_result_review_payload()),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "nonpromotion-closeout-plan",
            "--result_review_json",
            str(result_review_json),
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
    assert "Non-Promotion Closeout Plan" in output_md.read_text(encoding="utf-8")
