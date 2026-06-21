from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_post_oracle_selector_route_reconciliation import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _post_oracle_gap() -> dict:
    return {
        "final_decision": {
            "status": "post_oracle_deployable_gap_current_selector_misses_oracle",
            "passed": True,
            "authorized_next_work": "selector_label_weight_design_preflight_only",
            "current_selector_gap_closed": False,
            "oracle_passed": True,
            "source_inventory_passed": True,
            "reasons": ["current_selector_does_not_close_hard_guarded_oracle_gap"],
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "new_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def _source_inventory() -> dict:
    return {
        "final_decision": {
            "status": "post_source_visibility_runtime_inventory_no_new_source_paused",
            "passed": True,
            "authorized_next_work": (
                "keep_selector_route_paused_or_scenario_objective_redesign_only"
            ),
            "new_runtime_source_candidates": [],
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "new_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def _pause_gate() -> dict:
    return {
        "final_decision": {
            "status": "post_external_context_selector_route_paused",
            "passed": True,
            "authorized_next_work": (
                "new_proof_objective_or_new_current_tick_source_predeclaration_only"
            ),
            "selector_route_paused": True,
            "deployable_camp_dp_selector_route_exists": False,
            "current_camp_dp_selector_route_rejected": True,
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "new_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def test_post_oracle_selector_reconciliation_keeps_route_paused() -> None:
    report = build_report(
        post_oracle_gap=_post_oracle_gap(),
        source_inventory=_source_inventory(),
        pause_gate=_pause_gate(),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["selector_route_paused"] is True
    assert decision["repeat_selector_label_weight_preflight_authorized"] is False
    assert decision["offline_convex_selector_training_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert report["reconciliation_contract"]["repeat_old_selector_training_path_allowed"] is False


def test_post_oracle_selector_reconciliation_blocks_wrong_gap_status() -> None:
    gap = _post_oracle_gap()
    gap["final_decision"]["status"] = "post_oracle_deployable_gap_closed_candidate_branch"

    report = build_report(
        post_oracle_gap=gap,
        source_inventory=_source_inventory(),
        pause_gate=_pause_gate(),
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "post_oracle_status_gap_open" in report["final_decision"]["failed_checks"]


def test_post_oracle_selector_reconciliation_blocks_new_source_candidate() -> None:
    inventory = _source_inventory()
    inventory["final_decision"]["new_runtime_source_candidates"] = ["new_context"]

    report = build_report(
        post_oracle_gap=_post_oracle_gap(),
        source_inventory=inventory,
        pause_gate=_pause_gate(),
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "source_inventory_no_new_runtime_source" in report["final_decision"][
        "failed_checks"
    ]


def test_post_oracle_selector_reconciliation_blocks_unpaused_route() -> None:
    pause = _pause_gate()
    pause["final_decision"]["selector_route_paused"] = False

    report = build_report(
        post_oracle_gap=_post_oracle_gap(),
        source_inventory=_source_inventory(),
        pause_gate=pause,
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "pause_gate_selector_route_paused" in report["final_decision"]["failed_checks"]


def test_post_oracle_selector_reconciliation_markdown_states_boundary() -> None:
    report = build_report(
        post_oracle_gap=_post_oracle_gap(),
        source_inventory=_source_inventory(),
        pause_gate=_pause_gate(),
    )
    markdown = render_markdown(report)

    assert "Post-Oracle Selector Route Reconciliation" in markdown
    assert "Repeat selector label/weight preflight authorized: `False`" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "classical Benders" in markdown


def test_post_oracle_selector_reconciliation_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gap_path = tmp_path / "gap.json"
    inventory_path = tmp_path / "inventory.json"
    pause_path = tmp_path / "pause.json"
    output_json = tmp_path / "reconciliation.json"
    output_md = tmp_path / "reconciliation.md"
    gap_path.write_text(json.dumps(_post_oracle_gap()), encoding="utf-8")
    inventory_path.write_text(json.dumps(_source_inventory()), encoding="utf-8")
    pause_path.write_text(json.dumps(_pause_gate()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "post_oracle_reconciliation",
            "--post_oracle_gap_json",
            str(gap_path),
            "--source_inventory_json",
            str(inventory_path),
            "--pause_gate_json",
            str(pause_path),
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
    assert "Post-Oracle Selector Route Reconciliation" in output_md.read_text(
        encoding="utf-8"
    )
