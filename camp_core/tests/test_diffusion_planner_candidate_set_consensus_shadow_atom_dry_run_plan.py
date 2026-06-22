from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_dry_run import (
    AUTHORIZED_NEXT_WORK,
    COEFFICIENT_FIELD,
    PAYLOAD_KEY,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _atom_review(**decision_overrides: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": "candidate_set_consensus_atom_design_review_plan_ready",
        "passed": True,
        "authorized_next_work": "candidate_set_consensus_shadow_atom_dry_run_plan_only",
        "atom_design_review_ready": True,
        "shadow_atom_dry_run_plan_authorized": True,
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
        "proposed_atom_design": {
            "atom_name": "candidate_set_consensus_center_rms_cost_v1",
            "payload_key": PAYLOAD_KEY,
            "coefficient_field": COEFFICIENT_FIELD,
            "nonnegative_by_definition": True,
            "hinge_required": False,
            "signed_split_required": False,
            "affine_score_compatible": True,
            "convex_master_compatible": True,
            "classic_benders_claim": False,
        },
    }


def test_shadow_atom_dry_run_plan_ready() -> None:
    report = build_report(atom_design_review=_atom_review(), label="unit")
    decision = report["final_decision"]
    plan = report["dry_run_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["shadow_atom_dry_run_plan_ready"] is True
    assert decision["dry_run_implementation_authorized"] is True
    assert decision["dry_run_execution_authorized"] is False
    assert decision["atom_promotion_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["expected_logs"] == 6
    assert plan["expected_records"] == 60
    assert plan["expected_candidates"] == 8
    assert plan["shadow_append_policy"]["weight_append_value"] == 0.0
    assert plan["shadow_append_policy"]["selection_weight_append_value"] == 0.0
    assert plan["shadow_append_policy"]["write_runtime_logs"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_shadow_atom_dry_run_plan_rejects_source_not_ready() -> None:
    report = build_report(
        atom_design_review=_atom_review(
            status="candidate_set_consensus_atom_design_review_plan_rejected",
            passed=False,
            authorized_next_work=None,
            atom_design_review_ready=False,
            shadow_atom_dry_run_plan_authorized=False,
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = report["final_decision"]["failed_checks"]
    assert "source_status" in failed
    assert "source_passed" in failed
    assert "source_authorizes_this_plan" in failed


def test_shadow_atom_dry_run_plan_rejects_blocked_action() -> None:
    report = build_report(atom_design_review=_atom_review(camp_retraining_authorized=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_shadow_atom_dry_run_plan_rejects_wrong_coefficient_field() -> None:
    source = _atom_review()
    source["proposed_atom_design"]["coefficient_field"] = "wrong_field"

    report = build_report(atom_design_review=source)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_coefficient_field" in report["final_decision"]["failed_checks"]


def test_shadow_atom_dry_run_plan_markdown_states_boundaries() -> None:
    markdown = render_markdown(build_report(atom_design_review=_atom_review()))

    assert "Candidate-Set Consensus Shadow Atom Dry-Run Plan" in markdown
    assert "Dry-run execution authorized: `False`" in markdown
    assert "zero weight" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "classical Benders" in markdown


def test_shadow_atom_dry_run_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_json = tmp_path / "atom_review.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    source_json.write_text(json.dumps(_atom_review()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-shadow-atom-dry-run-plan",
            "--atom_design_review_json",
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
    assert payload["dry_run_plan"]["candidate_root"] == "/tmp/replay/logging_enabled"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "Candidate-Set Consensus Shadow Atom Dry-Run Plan" in output_md.read_text(
        encoding="utf-8"
    )
