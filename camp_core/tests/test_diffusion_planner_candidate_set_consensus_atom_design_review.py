from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_atom_design_review import (
    ATOM_NAME,
    AUTHORIZED_NEXT_WORK,
    COEFFICIENT_FIELD,
    PAYLOAD_KEY,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _materiality(**decision_overrides: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": "candidate_set_consensus_broader_nonformal_materiality_diagnosis_ready",
        "passed": True,
        "screen_completed": True,
        "materiality_gate_passed": True,
        "signal_present": True,
        "sample_too_small_for_promotion": False,
        "authorized_next_work": "candidate_set_consensus_atom_design_review_plan_only",
        "atom_design_review_plan_authorized": True,
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
    }
    decision.update(decision_overrides)
    return {
        "final_decision": decision,
        "record_summary": {
            "formal_seed_run_ids": [],
            "records": 60,
            "valid_records": 48,
            "valid_record_rate": 0.8,
            "candidate_rows": 480,
            "valid_candidate_rows": 384,
            "positive_spread_records": 46,
            "positive_spread_rate": 0.9583333333333334,
            "selected_not_consensus_best_records": 39,
            "finite_lambda_records": 39,
            "min_lambda_to_change_any_record": 0.026845163286762983,
        },
    }


def test_candidate_set_consensus_atom_design_review_ready() -> None:
    report = build_report(materiality=_materiality(), label="unit")
    decision = report["final_decision"]
    atom = report["proposed_atom_design"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["atom_design_review_ready"] is True
    assert decision["shadow_atom_dry_run_plan_authorized"] is True
    assert decision["atom_promotion_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert atom["atom_name"] == ATOM_NAME
    assert atom["payload_key"] == PAYLOAD_KEY
    assert atom["coefficient_field"] == COEFFICIENT_FIELD
    assert atom["nonnegative_by_definition"] is True
    assert atom["hinge_required"] is False
    assert atom["signed_split_required"] is False
    assert atom["affine_score_compatible"] is True
    assert atom["convex_master_compatible"] is True
    assert atom["classic_benders_claim"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_candidate_set_consensus_atom_design_review_rejects_weak_materiality() -> None:
    report = build_report(
        materiality=_materiality(
            materiality_gate_passed=False,
            authorized_next_work="candidate_set_consensus_broader_materiality_reject_or_redesign_review_only",
            atom_design_review_plan_authorized=False,
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = report["final_decision"]["failed_checks"]
    assert "source_authorizes_atom_design_review" in failed
    assert "source_materiality_gate_passed" in failed
    assert "source_atom_design_review_plan_authorized" in failed


def test_candidate_set_consensus_atom_design_review_rejects_formal_seed() -> None:
    materiality = _materiality()
    materiality["record_summary"]["formal_seed_run_ids"] = [
        "sample_tl59_seed11_npc0_tlon"
    ]

    report = build_report(materiality=materiality)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_formal_seed_runs" in report["final_decision"]["failed_checks"]


def test_candidate_set_consensus_atom_design_review_rejects_blocked_action() -> None:
    report = build_report(materiality=_materiality(camp_retraining_authorized=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_candidate_set_consensus_atom_design_review_markdown_states_boundaries() -> None:
    markdown = render_markdown(build_report(materiality=_materiality()))

    assert "Candidate-Set Consensus Atom Design Review Plan" in markdown
    assert "Atom promotion authorized: `False`" in markdown
    assert "shadow-only" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "classical Benders" in markdown


def test_candidate_set_consensus_atom_design_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    materiality_json = tmp_path / "materiality.json"
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"
    materiality_json.write_text(json.dumps(_materiality()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-atom-design-review",
            "--materiality_json",
            str(materiality_json),
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
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "Candidate-Set Consensus Atom Design Review Plan" in output_md.read_text(
        encoding="utf-8"
    )
