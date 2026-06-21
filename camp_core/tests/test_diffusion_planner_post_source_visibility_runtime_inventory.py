from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_post_source_visibility_runtime_inventory import (
    CANDIDATE_NEXT_WORK,
    CANDIDATE_STATUS,
    PAUSED_NEXT_WORK,
    PAUSED_STATUS,
    build_report,
    main,
    render_markdown,
)


def _screen(**overrides: object) -> dict[str, object]:
    decision = {
        "status": "source_visibility_predeclaration_no_admissible_source_paused",
        "passed": True,
        "authorized_next_work": (
            "keep_selector_route_paused_or_submit_new_source_visibility_proposal_only"
        ),
        "selector_route_paused": True,
        "support_source_ready": False,
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
            "dp_prior_deviation",
            "external_context",
            "observable_interaction",
            "progress_lane_hard",
            "raw_prefix",
            "red_clearance_gap_to_best_current_tick",
            "route_topology",
            "signal_right_of_way",
            "source_donor",
            "top1_retention",
        ],
    }


def _new_candidate(**overrides: object) -> dict[str, object]:
    candidate = {
        "name": "new_current_tick_visibility_margin",
        "source_family": "visibility_margin_not_yet_closed",
        "runtime_evidence": ["current tick runtime field exists"],
        "current_tick_available_before_selection": True,
        "candidate_level_or_deterministically_joinable": True,
        "finite_or_fail_closed": True,
        "deterministic": True,
        "uses_future_outcome_or_safetycost_label": False,
        "requires_dp_modification": False,
        "requires_dp_retraining": False,
        "requires_replay_to_compute_runtime_value": False,
        "requires_training_to_compute_runtime_value": False,
        "atom_value_domain": "nonnegative",
        "equivalent_closed_labels": [],
        "math_note": "fixed current-tick nonnegative coefficient",
    }
    candidate.update(overrides)
    return candidate


def test_runtime_inventory_rejects_default_visible_families() -> None:
    report = build_report(screen=_screen(), label="unit")
    decision = report["final_decision"]

    assert decision["status"] == PAUSED_STATUS
    assert decision["passed"] is True
    assert decision["support_source_ready"] is False
    assert decision["selector_route_paused"] is True
    assert decision["authorized_next_work"] == PAUSED_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert len(decision["rejected_runtime_source_candidates"]) >= 5
    assert decision["new_runtime_source_candidates"] == []
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_runtime_inventory_routes_open_candidate_back_to_predeclaration() -> None:
    report = build_report(screen=_screen(), candidates=[_new_candidate()])
    decision = report["final_decision"]

    assert decision["status"] == CANDIDATE_STATUS
    assert decision["passed"] is True
    assert decision["support_source_ready"] is False
    assert decision["authorized_next_work"] == CANDIDATE_NEXT_WORK
    assert decision["new_runtime_source_candidates"] == [
        "new_current_tick_visibility_margin"
    ]
    assert decision["closed_loop_replay_authorized"] is False


def test_runtime_inventory_rejects_closed_equivalent_candidate() -> None:
    report = build_report(
        screen=_screen(),
        candidates=[
            _new_candidate(
                source_family="route_topology",
                equivalent_closed_labels=["route_topology"],
            )
        ],
    )
    row = report["runtime_source_candidates"][0]

    assert row["new_source_candidate"] is False
    assert row["rejection_reasons"] == ["not_equivalent_to_closed_source_labels"]
    assert report["final_decision"]["status"] == PAUSED_STATUS


def test_runtime_inventory_blocks_on_bad_screen() -> None:
    report = build_report(screen=_screen(status="source_visibility_predeclaration_ready"))
    decision = report["final_decision"]

    assert decision["status"] == "post_source_visibility_runtime_inventory_blocked"
    assert decision["passed"] is False
    assert "screen_status" in decision["failed_screen_checks"]
    assert decision["formal_seeds_authorized"] is False


def test_runtime_inventory_markdown_states_no_replay_authorization() -> None:
    report = build_report(screen=_screen())
    markdown = render_markdown(report)

    assert "Post Source-Visibility Runtime Inventory" in markdown
    assert "No DP-side classical Benders" in markdown
    assert "Full36" in markdown
    assert "intersection_stopline_crosswalk_map_context" in markdown


def test_runtime_inventory_cli_writes_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    screen = tmp_path / "screen.json"
    candidate = tmp_path / "candidate.json"
    output_json = tmp_path / "inventory.json"
    output_md = tmp_path / "inventory.md"
    screen.write_text(json.dumps(_screen()), encoding="utf-8")
    candidate.write_text(json.dumps({"candidates": [_new_candidate()]}), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--screen_json",
            str(screen),
            "--candidate_json",
            str(candidate),
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
    assert payload["final_decision"]["status"] == CANDIDATE_STATUS
    assert "Post Source-Visibility Runtime Inventory" in output_md.read_text(
        encoding="utf-8"
    )
