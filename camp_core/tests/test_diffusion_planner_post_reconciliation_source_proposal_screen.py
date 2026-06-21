from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_post_reconciliation_source_proposal_screen import (
    PAUSED_STATUS,
    READY_NEXT_WORK,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _decision(status: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "passed": True,
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }
    payload.update(overrides)
    return payload


def _goal_state(**overrides: object) -> dict[str, object]:
    return {
        "goal_state": {
            "candidate_pool_opportunity_exists": True,
            "no_new_runtime_source_available": True,
        },
        "final_decision": _decision(
            "post_reconciliation_current_goal_state_paused",
            authorized_next_work="submit_new_current_tick_source_proposal_or_keep_paused_only",
            selector_route_paused=True,
            deployable_camp_dp_selector_route_exists=False,
            development_gates_complete=False,
            formal_seeds_ready=False,
            **overrides,
        ),
    }


def _ledger() -> dict[str, object]:
    return {
        "source_family_ledger": {
            "closed_source_family_labels": [
                "temporal_consistency_atom_family",
                "external_context",
                "observable_interaction",
            ],
            "closed_score_families": ["route_topology"],
            "closed_or_existing_proxy_families": ["progress_lane_hard"],
        }
    }


def _proposal(**overrides: object) -> dict[str, object]:
    proposal: dict[str, object] = {
        "name": "candidate_set_consensus_density_source_v1",
        "source_family": "candidate_set_geometry_consensus",
        "score_family": "candidate_set_consensus_density_atom_family",
        "current_tick_available_before_selection": True,
        "candidate_level_or_deterministically_joinable": True,
        "finite_or_fail_closed": True,
        "deterministic": True,
        "uses_future_outcome_or_safetycost_label": False,
        "requires_dp_modification": False,
        "requires_dp_retraining": False,
        "requires_replay_to_compute_runtime_value": False,
        "requires_training_to_compute_runtime_value": False,
        "default_off_latency_accounted": True,
        "existing_log_materiality_predeclared": True,
        "atom_value_domain": "nonnegative",
        "non_equivalence_evidence": [
            "uses only current candidate-set geometry",
            "does not use previous-plan memory or traffic-signal state",
        ],
    }
    proposal.update(overrides)
    return proposal


def test_post_reconciliation_source_proposal_accepts_new_candidate_set_source() -> None:
    report = build_report(
        goal_state=_goal_state(),
        source_family_ledger=_ledger(),
        proposals=[_proposal()],
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["support_source_ready"] is True
    assert decision["authorized_next_work"] == READY_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert decision["admissible_sources"] == [
        "candidate_set_consensus_density_source_v1"
    ]


def test_post_reconciliation_source_proposal_pauses_without_proposal() -> None:
    report = build_report(
        goal_state=_goal_state(),
        source_family_ledger=_ledger(),
        proposals=[],
    )

    assert report["final_decision"]["status"] == PAUSED_STATUS
    assert report["final_decision"]["support_source_ready"] is False
    assert report["final_decision"]["selector_route_paused"] is True


def test_post_reconciliation_source_proposal_rejects_closed_family() -> None:
    report = build_report(
        goal_state=_goal_state(),
        source_family_ledger=_ledger(),
        proposals=[_proposal(score_family="temporal_consistency_atom_family")],
    )

    decision = report["final_decision"]
    assert decision["status"] == PAUSED_STATUS
    assert decision["support_source_ready"] is False
    assert decision["rejected_sources"] == ["candidate_set_consensus_density_source_v1"]
    assert "score_family_not_closed" in report["proposal_rows"][0]["rejection_reasons"]


def test_post_reconciliation_source_proposal_blocks_bad_goal_state() -> None:
    goal = _goal_state()
    goal["final_decision"]["selector_route_paused"] = False
    report = build_report(
        goal_state=goal,
        source_family_ledger=_ledger(),
        proposals=[_proposal()],
    )

    decision = report["final_decision"]
    assert decision["status"] == "post_reconciliation_source_proposal_screen_blocked"
    assert "goal_selector_route_paused" in decision["failed_checks"]
    assert decision["support_source_ready"] is False


def test_post_reconciliation_source_proposal_markdown_states_boundary() -> None:
    report = build_report(
        goal_state=_goal_state(),
        source_family_ledger=_ledger(),
        proposals=[_proposal()],
    )
    markdown = render_markdown(report)

    assert "Post-Reconciliation Source Proposal Screen" in markdown
    assert "candidate_set_consensus_density_source_v1" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "classical Benders" in markdown


def test_post_reconciliation_source_proposal_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    goal_path = tmp_path / "goal.json"
    ledger_path = tmp_path / "ledger.json"
    proposal_path = tmp_path / "proposal.json"
    output_json = tmp_path / "screen.json"
    output_md = tmp_path / "screen.md"
    goal_path.write_text(json.dumps(_goal_state()), encoding="utf-8")
    ledger_path.write_text(json.dumps(_ledger()), encoding="utf-8")
    proposal_path.write_text(json.dumps({"proposals": [_proposal()]}), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "source-proposal-screen",
            "--goal_state_json",
            str(goal_path),
            "--source_family_ledger_json",
            str(ledger_path),
            "--proposal_json",
            str(proposal_path),
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
    assert "Post-Reconciliation Source Proposal Screen" in output_md.read_text(
        encoding="utf-8"
    )
