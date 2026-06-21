from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_payload_design import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _source_screen(**overrides: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": "post_reconciliation_source_proposal_screen_ready",
        "passed": True,
        "support_source_ready": True,
        "authorized_next_work": "default_off_current_tick_source_payload_design_only",
        "admissible_sources": ["candidate_set_consensus_density_source_v1"],
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
    decision.update(overrides)
    return {
        "final_decision": decision,
        "proposal_rows": [
            {
                "name": "candidate_set_consensus_density_source_v1",
                "source_family": "candidate_set_geometry_consensus",
                "score_family": "candidate_set_consensus_density_atom_family",
                "admissible": True,
            }
        ],
    }


def test_candidate_set_consensus_payload_design_ready() -> None:
    report = build_report(source_proposal_screen=_source_screen(), label="unit")
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert report["coefficient_contract"]["domain"] == (
        "nonnegative_finite_scalar_per_candidate"
    )
    assert "candidate_raw_trajectory_prefix" in (
        report["materiality_contract"]["required_existing_log_fields"]
    )


def test_candidate_set_consensus_payload_design_blocks_wrong_source_status() -> None:
    report = build_report(
        source_proposal_screen=_source_screen(
            status="post_reconciliation_source_proposal_screen_paused",
            support_source_ready=False,
        )
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "source_status" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_candidate_set_consensus_payload_design_blocks_missing_proposal() -> None:
    source = _source_screen()
    source["proposal_rows"] = []

    report = build_report(source_proposal_screen=source)

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "proposal_admissible" in report["final_decision"]["failed_checks"]


def test_candidate_set_consensus_payload_design_blocks_action_conflict() -> None:
    report = build_report(
        source_proposal_screen=_source_screen(new_replay_authorized=True)
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_candidate_set_consensus_payload_design_markdown_states_boundary() -> None:
    report = build_report(source_proposal_screen=_source_screen())
    markdown = render_markdown(report)

    assert "Candidate-Set Consensus Payload Design" in markdown
    assert "coordinate-wise median" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "classical Benders" in markdown
    assert "candidate_raw_trajectory_prefix" in markdown


def test_candidate_set_consensus_payload_design_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.json"
    output_json = tmp_path / "design.json"
    output_md = tmp_path / "design.md"
    source.write_text(json.dumps(_source_screen()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "payload-design",
            "--source_proposal_screen_json",
            str(source),
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
    assert "Candidate-Set Consensus Payload Design" in output_md.read_text(
        encoding="utf-8"
    )
