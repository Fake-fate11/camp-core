from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_scenario_objective_redesign_or_external_source_contract import (
    BLOCKED_STATUS,
    READY_STATUS,
    REQUIRED_BUCKETS,
    build_report,
    main,
    render_markdown,
)


def _development_state(
    *,
    status: str = "current_development_gate_state_no_deployable_route_yet",
    passed: bool = True,
    authorized_next_work: str | None = (
        "scenario_objective_redesign_or_external_source_discovery_only"
    ),
    formal_ready: bool = False,
    blocked: bool = False,
    buckets: list[str] | None = None,
) -> dict[str, object]:
    return {
        "development_state": {
            "blocking_gap": (
                "candidate_pool_opportunity_exists_but_no_current_no_leak_deployable_selector_route"
            ),
            "proof_contract": {
                "primary_score": "SafetyCost_v1",
                "claim_rule": (
                    "hard_gate_passed and "
                    "ci95_high(SafetyCost_CAMP_minus_DP_Top1) < 0"
                ),
                "required_buckets": list(REQUIRED_BUCKETS)
                if buckets is None
                else buckets,
            },
        },
        "final_decision": {
            "status": status,
            "passed": passed,
            "authorized_next_work": authorized_next_work,
            "development_gates_complete": False,
            "formal_seeds_ready": formal_ready,
            "current_camp_dp_selector_route_rejected": True,
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": blocked,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def test_contract_ready_rejects_objective_only_and_authorizes_source_inventory() -> None:
    report = build_report(development_gate_state=_development_state(), label="unit")
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["scenario_objective_redesign_only_sufficient"] is False
    assert decision["external_source_contract_ready"] is True
    assert decision["authorized_next_work"] == (
        "external_source_visibility_inventory_or_pause_only"
    )
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["formal_seeds_authorized"] is False

    objective = report["objective_redesign_boundary"]
    assert objective["objective_only_redesign_sufficient_for_deployable_route"] is False
    assert "dropping DP Top-1 or current CAMP comparators" in objective[
        "forbidden_changes"
    ]
    contract = report["external_source_visibility_contract"]
    assert contract["ready_for_visibility_inventory"] is True
    assert "current_tick_available_before_selection" in contract[
        "required_properties"
    ]


def test_contract_blocks_if_development_state_is_not_current() -> None:
    report = build_report(
        development_gate_state=_development_state(
            status="current_development_gate_state_source_blocked",
            passed=False,
            authorized_next_work=None,
        )
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert decision["authorized_next_work"] is None
    assert report["source_gate"]["passed"] is False


def test_contract_blocks_formal_seed_ready_or_replay_conflict() -> None:
    report = build_report(
        development_gate_state=_development_state(formal_ready=True, blocked=True)
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert "source_formal_seeds_not_ready" in failed
    assert "source_no_blocked_action_conflicts" in failed
    assert decision["formal_seeds_authorized"] is False


def test_contract_blocks_missing_required_bucket() -> None:
    buckets = [bucket for bucket in REQUIRED_BUCKETS if bucket != "normal"]
    report = build_report(development_gate_state=_development_state(buckets=buckets))

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert "source_no_missing_required_buckets" in failed


def test_contract_markdown_states_no_leak_and_no_benders() -> None:
    report = build_report(development_gate_state=_development_state(), label="unit")
    markdown = render_markdown(report)

    assert "Scenario/Objective Redesign Or External Source Contract" in markdown
    assert "SafetyCost_v1" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "No DP-side classical Benders" in markdown


def test_contract_cli_writes_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "development_state.json"
    output_json = tmp_path / "out.json"
    output_md = tmp_path / "out.md"
    source.write_text(json.dumps(_development_state()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--development_gate_state_json",
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
    assert "External Source Contract" in output_md.read_text(encoding="utf-8")
