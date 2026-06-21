from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_post_reconciliation_current_goal_state import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
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


def _reconciliation(**overrides: object) -> dict[str, object]:
    return {
        "final_decision": _decision(
            "post_oracle_selector_route_reconciliation_paused",
            authorized_next_work="new_current_tick_source_predeclaration_or_keep_paused_only",
            selector_route_paused=True,
            deployable_camp_dp_selector_route_exists=False,
            repeat_selector_label_weight_preflight_authorized=False,
            **overrides,
        )
    }


def _source_inventory(**overrides: object) -> dict[str, object]:
    return {
        "final_decision": _decision(
            "post_source_visibility_runtime_inventory_no_new_source_paused",
            authorized_next_work=(
                "keep_selector_route_paused_or_scenario_objective_redesign_only"
            ),
            support_source_ready=False,
            new_runtime_source_candidates=[],
            **overrides,
        )
    }


def _scenario_matrix(**overrides: object) -> dict[str, object]:
    matrix = {
        "missing_required_buckets": [],
        "formal_seeds": [],
        "planned_run_count": 108,
    }
    matrix.update(overrides.pop("matrix_overrides", {}))
    return {
        "matrix_source": matrix,
        "final_decision": _decision(
            "scenario_evidence_matrix_predeclared",
            authorized_next_work="candidate_branch_oracle_input_readiness_gate",
            **overrides,
        ),
    }


def _candidate_readiness(**overrides: object) -> dict[str, object]:
    return {
        "readiness_summary": {
            "logs": 108,
            "records": 21600,
            "missing_example_keys": [],
        },
        "final_decision": _decision(
            "candidate_branch_oracle_input_readiness_ready",
            authorized_next_work="candidate_branch_safety_cost_oracle_audit_only",
            **overrides,
        ),
    }


def _oracle(**overrides: object) -> dict[str, object]:
    logs = {"total": 108, "formal_seed_logs": 0}
    logs.update(overrides.pop("logs_overrides", {}))
    return {
        "opportunity_gate": {"passed": True},
        "logs": logs,
        "records": {"total": 21600},
        "coverage_gaps": {"missing_required_buckets": []},
        "overall": {
            "record_rates": {
                "hard_guarded_oracle_beats_top1": 0.86,
                "camp_matches_hard_guarded_oracle": 0.52,
            }
        },
    }


def _report(**overrides: object) -> dict[str, object]:
    inputs = {
        "reconciliation": _reconciliation(),
        "source_inventory": _source_inventory(),
        "scenario_matrix": _scenario_matrix(),
        "candidate_readiness": _candidate_readiness(),
        "safety_cost_oracle": _oracle(),
        "label": "unit",
    }
    inputs.update(overrides)
    return build_report(**inputs)


def test_post_reconciliation_goal_state_ready_and_paused() -> None:
    report = _report()
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["selector_route_paused"] is True
    assert decision["deployable_camp_dp_selector_route_exists"] is False
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["training_execution_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert report["goal_state"]["candidate_pool_opportunity_exists"] is True
    assert report["goal_state"]["no_new_runtime_source_available"] is True
    assert report["goal_state"]["development_gates_complete"] is False


def test_post_reconciliation_goal_state_blocks_new_source_inventory_candidate() -> None:
    inventory = _source_inventory()
    inventory["final_decision"]["new_runtime_source_candidates"] = ["new_runtime_source"]

    report = _report(source_inventory=inventory)

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "source_inventory_no_new_sources" in report["final_decision"][
        "failed_checks"
    ]


def test_post_reconciliation_goal_state_blocks_bad_reconciliation() -> None:
    reconciliation = _reconciliation()
    reconciliation["final_decision"]["selector_route_paused"] = False

    report = _report(reconciliation=reconciliation)

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "reconciliation_selector_paused" in report["final_decision"][
        "failed_checks"
    ]


def test_post_reconciliation_goal_state_blocks_oracle_formal_seeds() -> None:
    oracle = _oracle(logs_overrides={"formal_seed_logs": 1})

    report = _report(safety_cost_oracle=oracle)

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "oracle_no_formal_seed_logs" in report["final_decision"]["failed_checks"]


def test_post_reconciliation_goal_state_markdown_states_boundary() -> None:
    report = _report()
    markdown = render_markdown(report)

    assert "Post-Reconciliation Current Goal State" in markdown
    assert "candidate_pool_opportunity_exists" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "No DP-side classical Benders" in markdown


def test_post_reconciliation_goal_state_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = {
        "reconciliation": tmp_path / "reconciliation.json",
        "source_inventory": tmp_path / "source_inventory.json",
        "scenario_matrix": tmp_path / "scenario_matrix.json",
        "candidate_readiness": tmp_path / "candidate_readiness.json",
        "oracle": tmp_path / "oracle.json",
    }
    payloads = [
        _reconciliation(),
        _source_inventory(),
        _scenario_matrix(),
        _candidate_readiness(),
        _oracle(),
    ]
    for path, payload in zip(paths.values(), payloads, strict=True):
        path.write_text(json.dumps(payload), encoding="utf-8")
    output_json = tmp_path / "goal_state.json"
    output_md = tmp_path / "goal_state.md"

    monkeypatch.setattr(
        "sys.argv",
        [
            "goal-state",
            "--reconciliation_json",
            str(paths["reconciliation"]),
            "--source_inventory_json",
            str(paths["source_inventory"]),
            "--scenario_matrix_json",
            str(paths["scenario_matrix"]),
            "--candidate_readiness_json",
            str(paths["candidate_readiness"]),
            "--safety_cost_oracle_json",
            str(paths["oracle"]),
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
    assert "Post-Reconciliation Current Goal State" in output_md.read_text(
        encoding="utf-8"
    )
