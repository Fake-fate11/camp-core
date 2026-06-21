from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_source_visibility_predeclaration_screen import (
    AUTHORIZED_NEXT_WORK,
    PAUSED_NEXT_WORK,
    PAUSED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _boundary(**overrides: object) -> dict[str, object]:
    decision = {
        "status": "post_targeted_safety_support_boundary_ready",
        "passed": True,
        "authorized_next_work": (
            "new_current_tick_source_visibility_predeclaration_or_keep_selector_route_paused_only"
        ),
        "selector_route_paused": True,
        "support_source_ready": False,
        "current_camp_dp_selector_route_rejected": True,
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
        "atom_promotion_authorized": False,
    }
    decision.update(overrides)
    return {
        "final_decision": decision,
        "closed_source_labels": [
            "red_clearance_gap_to_best_current_tick",
            "temporal_consistency",
            "external_context",
            "route_speed",
            "signal_right_of_way",
            "turn_logit",
        ],
    }


def _valid_proposal(**overrides: object) -> dict[str, object]:
    proposal = {
        "name": "candidate_occlusion_visibility_buffer_v1",
        "source_family": "occlusion_visibility_buffer",
        "score_family": "occlusion_visibility_buffer_atom_family",
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
        "atom_value_domain": "nonnegative",
        "non_equivalence_evidence": [
            "not route_speed",
            "not signal_right_of_way",
            "not temporal_consistency",
        ],
    }
    proposal.update(overrides)
    return proposal


def test_source_visibility_screen_pauses_when_no_proposal() -> None:
    report = build_report(boundary=_boundary(), proposals=[], label="unit")
    decision = report["final_decision"]

    assert decision["status"] == PAUSED_STATUS
    assert decision["passed"] is True
    assert decision["selector_route_paused"] is True
    assert decision["support_source_ready"] is False
    assert decision["authorized_next_work"] == PAUSED_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_source_visibility_screen_accepts_genuinely_new_proposal() -> None:
    report = build_report(boundary=_boundary(), proposals=[_valid_proposal()])
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["support_source_ready"] is True
    assert decision["admissible_sources"] == ["candidate_occlusion_visibility_buffer_v1"]
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["closed_loop_replay_authorized"] is False
    assert report["proposals"][0]["admissible"] is True


def test_source_visibility_screen_rejects_closed_family() -> None:
    report = build_report(
        boundary=_boundary(),
        proposals=[
            _valid_proposal(
                source_family="temporal_consistency",
                score_family="temporal_consistency",
            )
        ],
    )
    decision = report["final_decision"]

    assert decision["status"] == PAUSED_STATUS
    assert decision["support_source_ready"] is False
    assert decision["rejected_sources"] == ["candidate_occlusion_visibility_buffer_v1"]
    assert report["proposals"][0]["rejection_reasons"] == [
        "source_family_not_closed",
        "score_family_not_closed",
    ]


def test_source_visibility_screen_blocks_bad_boundary() -> None:
    report = build_report(
        boundary=_boundary(status="post_targeted_safety_support_boundary_blocked"),
        proposals=[_valid_proposal()],
    )
    decision = report["final_decision"]

    assert decision["status"] == "source_visibility_predeclaration_blocked"
    assert "boundary_status" in decision["failed_checks"]
    assert decision["formal_seeds_authorized"] is False


def test_source_visibility_screen_markdown_states_pause_contract() -> None:
    report = build_report(boundary=_boundary(), proposals=[])
    markdown = render_markdown(report)

    assert "Source Visibility Predeclaration Screen" in markdown
    assert "none_provided" in markdown
    assert "No DP-side classical Benders" in markdown
    assert "requires_dp_modification=false" in markdown


def test_source_visibility_screen_cli_writes_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary = tmp_path / "boundary.json"
    proposal = tmp_path / "proposal.json"
    output_json = tmp_path / "screen.json"
    output_md = tmp_path / "screen.md"
    boundary.write_text(json.dumps(_boundary()), encoding="utf-8")
    proposal.write_text(json.dumps({"proposals": [_valid_proposal()]}), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--boundary_json",
            str(boundary),
            "--proposal_json",
            str(proposal),
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
    assert "Source Visibility Predeclaration Screen" in output_md.read_text(
        encoding="utf-8"
    )
