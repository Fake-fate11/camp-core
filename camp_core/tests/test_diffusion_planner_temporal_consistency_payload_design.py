from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_temporal_consistency_payload_design import (
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _source_gate(**decision_overrides: object) -> dict[str, object]:
    decision = {
        "status": "new_no_leak_targeted_support_source_predeclared",
        "passed": True,
        "support_source_ready": True,
        "admissible_support_sources": [
            "previous_plan_temporal_consistency_source_v1"
        ],
        "authorized_next_work": "default_off_new_no_leak_support_payload_design_only",
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
    decision.update(decision_overrides)
    return {
        "final_decision": decision,
        "proposals": [
            {
                "name": "previous_plan_temporal_consistency_source_v1",
                "source_family": "closed_loop_plan_memory_temporal_consistency",
                "score_family": "temporal_consistency_atom_family",
                "admissible": True,
                "rejection_reasons": [],
            }
        ],
    }


def test_temporal_consistency_payload_design_predeclares_default_off_contract() -> None:
    report = build_report(source_proposal_gate=_source_gate(), label="unit")
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["payload_design_ready"] is True
    assert decision["authorized_next_work"] == (
        "default_off_temporal_consistency_payload_runtime_preflight_only"
    )
    assert decision["new_replay_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False

    payload = report["payload_contract"]
    assert payload["default_off"] is True
    assert payload["state_memory"]["future_outcome_leakage"] is False
    assert payload["state_memory"]["missing_memory_policy"] == (
        "fail_closed_before selector promotion"
    )
    atom = report["atom_contract"]
    assert atom["domain"] == "nonnegative_finite_scalar_per_candidate"
    assert "score_k(w)=a_k^T w" in atom["affine_score"]


def test_temporal_consistency_payload_design_blocks_if_source_not_ready() -> None:
    report = build_report(
        source_proposal_gate=_source_gate(
            status="new_no_leak_targeted_support_source_not_available",
            support_source_ready=False,
            admissible_support_sources=[],
            authorized_next_work=(
                "source_level_targeted_support_discovery_or_pause_current_selector_route_only"
            ),
        )
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert decision["authorized_next_work"] is None
    assert "source_status" in decision["failed_checks"]
    assert "temporal_source_admissible" in decision["failed_checks"]


def test_temporal_consistency_payload_design_blocks_action_conflict() -> None:
    report = build_report(
        source_proposal_gate=_source_gate(new_replay_authorized=True)
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert "source_no_blocked_actions" in decision["failed_checks"]
    assert decision["new_replay_authorized"] is False


def test_temporal_consistency_payload_design_markdown_states_boundary() -> None:
    markdown = render_markdown(build_report(source_proposal_gate=_source_gate()))

    assert "Temporal Consistency Payload Design" in markdown
    assert "previous selected plan" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "No DP-side classical" in markdown or "DP-side classical Benders" in markdown
    assert "does not authorize DP execution" in markdown


def test_temporal_consistency_payload_design_cli_writes_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.json"
    output_json = tmp_path / "payload.json"
    output_md = tmp_path / "payload.md"
    source.write_text(json.dumps(_source_gate()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--source_proposal_gate_json",
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
    assert "Temporal Consistency Payload Design" in output_md.read_text(encoding="utf-8")
