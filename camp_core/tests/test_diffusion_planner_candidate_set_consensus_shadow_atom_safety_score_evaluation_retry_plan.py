from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation_retry import (
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


def _source_review(
    *,
    status: str = (
        "candidate_set_consensus_shadow_atom_safety_score_"
        "outcome_label_source_review_ready"
    ),
    passed: bool = True,
    authorized_next_work: str | None = (
        "candidate_set_consensus_shadow_atom_safety_score_"
        "evaluation_retry_consideration_plan_only"
    ),
    compatibility_mismatch_count: int = 0,
    label_complete_outcome_records: int = 60,
    broader_outcome_records_present: int = 0,
    formal_seed_log_count: int = 0,
    payload_no_leak_records: int = 60,
    run_ids: tuple[str, ...] = RUN_IDS,
    **decision_overrides: object,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": passed,
        "authorized_next_work": authorized_next_work,
        "outcome_label_source_review_ready": passed,
        "safety_score_evaluation_retry_plan_authorized": passed,
        "label_attachment_authorized": False,
        "safety_score_evaluation_retry_authorized": False,
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
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
        "source_review": {
            "label_root": "/labels",
            "broader_candidate_root": "/broader",
            "run_count": len(run_ids),
            "run_ids": list(run_ids),
            "label_records": 60,
            "broader_records": 60,
            "records_compared": 60,
            "compatibility_mismatch_count": compatibility_mismatch_count,
            "label_complete_outcome_records": label_complete_outcome_records,
            "broader_outcome_records_present": broader_outcome_records_present,
            "payload_no_leak_records": payload_no_leak_records,
            "formal_seed_log_count": formal_seed_log_count,
            "errors": [],
        },
    }


def test_evaluation_retry_plan_ready() -> None:
    report = build_report(
        source_review=_source_review(),
        source_review_json="/artifact/source_review.json",
        weight_sensitivity_json="/artifact/weight.json",
        label_root="/labels",
        label="unit",
    )
    decision = report["final_decision"]
    plan = report["retry_consideration_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["safety_score_evaluation_retry_plan_ready"] is True
    assert decision["safety_score_evaluation_retry_authorization_gate_authorized"] is True
    assert decision["safety_score_evaluation_retry_authorized"] is False
    assert decision["label_attachment_authorized"] is False
    assert decision["atom_promotion_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["label_root"] == "/labels"
    assert plan["weight_sensitivity_json"] == "/artifact/weight.json"
    assert plan["scenario_coverage"]["traffic_light"]
    assert plan["scenario_coverage"]["turn"]
    assert plan["scenario_coverage"]["normal"]
    assert len(plan["scenario_coverage"]["nishishinjuku"]) == 2
    assert plan["attaches_labels_to_prior_artifacts"] is False
    assert plan["future_evaluator_command"][0] == "python"
    assert "--require_pass" in plan["future_evaluator_command"]
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_evaluation_retry_plan_rejects_source_not_ready() -> None:
    report = build_report(
        source_review=_source_review(
            status=(
                "candidate_set_consensus_shadow_atom_safety_score_"
                "outcome_label_source_review_rejected"
            ),
            passed=False,
            authorized_next_work=None,
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = report["final_decision"]["failed_checks"]
    assert "source_status" in failed
    assert "source_passed" in failed
    assert "source_authorizes_retry_plan" in failed


def test_evaluation_retry_plan_rejects_review_mismatch() -> None:
    report = build_report(
        source_review=_source_review(compatibility_mismatch_count=1)
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "review_compatibility_mismatches_zero" in report["final_decision"][
        "failed_checks"
    ]


def test_evaluation_retry_plan_rejects_formal_seed() -> None:
    report = build_report(
        source_review=_source_review(
            formal_seed_log_count=1,
            run_ids=(*RUN_IDS[:-1], "sample_tl59_seed11_npc4_tlon"),
        )
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "review_no_formal_seed_logs" in failed
    assert "scope_no_formal_seed_runs" in failed


def test_evaluation_retry_plan_rejects_blocked_action() -> None:
    report = build_report(
        source_review=_source_review(label_attachment_authorized=True)
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_evaluation_retry_plan_markdown_states_boundaries() -> None:
    markdown = render_markdown(build_report(source_review=_source_review()))

    assert "Safety-Score Evaluation Retry Plan" in markdown
    assert "Safety-score retry execution authorized: `False`" in markdown
    assert "Label attachment authorized: `False`" in markdown
    assert "candidate_closed_loop_outcomes" in markdown
    assert "classical Benders" in markdown
    assert "does not execute the retry" in markdown


def test_evaluation_retry_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_json = tmp_path / "source_review.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    source_json.write_text(json.dumps(_source_review()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "safety-score-evaluation-retry-plan",
            "--source_review_json",
            str(source_json),
            "--weight_sensitivity_json",
            "/artifact/weight.json",
            "--label_root",
            "/labels",
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
    assert payload["retry_consideration_plan"]["label_root"] == "/labels"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Safety-Score Evaluation Retry Plan" in output_md.read_text(
        encoding="utf-8"
    )
