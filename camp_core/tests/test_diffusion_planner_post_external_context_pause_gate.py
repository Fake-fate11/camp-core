from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_post_external_context_pause_gate import (
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _development_gate_state() -> dict:
    return {
        "final_decision": {
            "status": "current_development_gate_state_no_deployable_route_yet",
            "passed": True,
            "authorized_next_work": "scenario_objective_redesign_or_external_source_discovery_only",
            "development_gates_complete": False,
            "formal_seeds_ready": False,
            "current_camp_dp_selector_route_rejected": True,
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "CAMP_retraining_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "DP_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def _scenario_objective_contract() -> dict:
    return {
        "objective_redesign_boundary": {
            "objective_only_redesign_sufficient_for_deployable_route": False
        },
        "final_decision": {
            "status": "scenario_objective_redesign_boundary_and_external_source_contract_ready",
            "passed": True,
            "scenario_objective_redesign_only_sufficient": False,
            "authorized_next_work": "external_source_visibility_inventory_or_pause_only",
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "CAMP_retraining_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "DP_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def _post_external_context_closure() -> dict:
    return {
        "final_decision": {
            "status": "post_external_context_source_route_closed",
            "passed": True,
            "external_context_source_route_closed": True,
            "current_camp_dp_selector_route_rejected": True,
            "authorized_next_work": "scenario_objective_redesign_or_pause_only",
            "failed_checks": [],
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "CAMP_retraining_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "DP_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def _report(**overrides: dict) -> dict:
    args = {
        "development_gate_state": _development_gate_state(),
        "scenario_objective_contract": _scenario_objective_contract(),
        "post_external_context_closure": _post_external_context_closure(),
        "label": "unit",
    }
    args.update(overrides)
    return build_report(**args)


def test_post_external_context_pause_gate_passes_and_pauses_selector_route() -> None:
    report = _report()
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["selector_route_paused"] is True
    assert decision["deployable_camp_dp_selector_route_exists"] is False
    assert (
        decision["authorized_next_work"]
        == "new_proof_objective_or_new_current_tick_source_predeclaration_only"
    )
    assert decision["online_selector_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_post_external_context_pause_gate_blocks_if_source_closure_not_closed() -> None:
    closure = _post_external_context_closure()
    closure["final_decision"]["external_context_source_route_closed"] = False

    report = _report(post_external_context_closure=closure)

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "external_context_source_route_closed" in report["final_decision"]["failed_checks"]


def test_post_external_context_pause_gate_blocks_objective_only_deployable_claim() -> None:
    contract = _scenario_objective_contract()
    contract["final_decision"]["scenario_objective_redesign_only_sufficient"] = True

    report = _report(scenario_objective_contract=contract)

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "objective_only_not_deployable" in report["final_decision"]["failed_checks"]


def test_post_external_context_pause_gate_blocks_action_conflict() -> None:
    development = _development_gate_state()
    development["final_decision"]["new_replay_authorized"] = True

    report = _report(development_gate_state=development)

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "development_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_post_external_context_pause_gate_markdown_states_reopening_boundary() -> None:
    markdown = render_markdown(_report())

    assert "Post External-Context CAMP-DP Pause Gate" in markdown
    assert "new_current_tick_candidate_level_source_predeclaration_only" in markdown
    assert "No DP-side classical Benders" in markdown


def test_post_external_context_pause_gate_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    development_path = tmp_path / "development.json"
    contract_path = tmp_path / "contract.json"
    closure_path = tmp_path / "closure.json"
    output_json = tmp_path / "pause_gate.json"
    output_md = tmp_path / "pause_gate.md"
    development_path.write_text(json.dumps(_development_gate_state()), encoding="utf-8")
    contract_path.write_text(json.dumps(_scenario_objective_contract()), encoding="utf-8")
    closure_path.write_text(json.dumps(_post_external_context_closure()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "post-external-context-pause-gate",
            "--development_gate_state_json",
            str(development_path),
            "--scenario_objective_contract_json",
            str(contract_path),
            "--post_external_context_closure_json",
            str(closure_path),
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
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "unit_cli" in output_md.read_text(encoding="utf-8")
