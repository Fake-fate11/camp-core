from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.synthesize_diffusion_planner_relaxed_strict_atom_observability_limit import (
    NEXT_WORK,
    PRIMARY_GAP,
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    SOURCE_REDESIGN_STATUS,
    render_markdown,
    synthesize,
)


def _component_report(
    *,
    status: str = "relaxed_strict_label_atom_component_overlap_diagnosed",
    passed: bool = True,
    authorized_next_work: str = "record_relaxed_strict_atom_observability_limit",
) -> dict:
    return {
        "records": {
            "total_records": 48,
            "candidate_rows": 384,
            "formal_seed_records": 0,
        },
        "group_counts": {
            "blocked_beneficial": 40,
            "newly_admitted_harmful": 5,
        },
        "relaxation": {
            "target_retain_rate": 0.1,
            "threshold": 0.020622436025802878,
        },
        "best_component_screen": {
            "descriptor": "relaxed_strict_atom_lateral_rate_change_surrogate_v1",
            "good_retain_rate": 0.125,
            "harmful_block_rate": 1.0,
            "allowed_harmful_rate": 0.0,
        },
        "diagnosis": {
            "promising_component_separator_found": False,
        },
        "final_decision": {
            "status": status,
            "passed": passed,
            "primary_gap": (
                "component_atoms_do_not_separate_blocked_beneficial_from_"
                "leaked_harmful"
            ),
            "authorized_next_work": authorized_next_work,
        },
    }


def test_observability_limit_records_rejected_component_route() -> None:
    report = synthesize(component_overlap_report=_component_report())

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["primary_gap"] == PRIMARY_GAP
    assert report["final_decision"]["authorized_next_work"] == NEXT_WORK
    assert report["evidence"]["blocked_beneficial"] == 40
    assert report["evidence"]["newly_admitted_harmful"] == 5
    assert report["rejected_routes"]["threshold_tuning_current_relaxed_strict_atoms"]
    assert report["blocked_actions"]["camp_retraining_authorized"] is False
    assert report["blocked_actions"]["classic_benders_claim_authorized"] is False


def test_observability_limit_blocks_when_source_not_ready() -> None:
    report = synthesize(
        component_overlap_report=_component_report(status="unexpected", passed=False)
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["passed"] is False
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_component_overlap_source_before_limit_record"
    )
    assert report["rejected_routes"][
        "threshold_tuning_current_relaxed_strict_atoms"
    ] is False


def test_observability_limit_defers_when_component_redesign_is_supported() -> None:
    report = synthesize(
        component_overlap_report=_component_report(
            authorized_next_work="predeclare_component_level_no_leak_atom_redesign"
        )
    )

    assert report["final_decision"]["status"] == SOURCE_REDESIGN_STATUS
    assert report["final_decision"]["passed"] is False
    assert report["final_decision"]["primary_gap"] == (
        "component_overlap_found_a_promising_separator"
    )


def test_observability_limit_markdown_and_cli_payload(tmp_path: Path) -> None:
    report = synthesize(component_overlap_report=_component_report())
    rendered = render_markdown(report)

    assert "Relaxed Strict Atom Observability Limit" in rendered
    assert "does not construct a DP-side classical Benders" in rendered

    json_path = tmp_path / "limit.json"
    json_path.write_text(json.dumps(report), encoding="utf-8")
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded["final_decision"]["status"] == READY_STATUS
