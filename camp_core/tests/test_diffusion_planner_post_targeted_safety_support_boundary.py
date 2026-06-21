from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_post_targeted_safety_support_boundary import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _targeted_safety(**overrides: object) -> dict[str, object]:
    decision = {
        "status": "alternative_safety_source_materiality_ready",
        "passed": True,
        "authorized_next_work": "targeted_safety_support_scenario_or_source_design_only",
        "has_material_safety_source": True,
        "has_actionable_existing_safety_source": False,
        "actionable_existing_safety_sources": [],
        "material_but_current_selection_already_best": [
            "h30_union_planned_red_light_cost",
            "h80_full_planned_red_light_cost",
        ],
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
        "materiality_summary": {
            "records": 50,
            "available_records": 50,
            "valid_available_records": 50,
            "by_source": [
                {
                    "source": "h30_union_planned_red_light_cost",
                    "nonzero_range_records": 2,
                    "selected_not_best_records": 0,
                }
            ],
        },
    }


def _temporal_safety(**overrides: object) -> dict[str, object]:
    decision = {
        "status": "temporal_consistency_shadow_safety_proxy_ready",
        "passed": True,
        "authorized_next_work": (
            "reject_temporal_consistency_as_safety_source_or_predeclare_alternative_no_leak_atom_only"
        ),
        "safety_proxy_evidence": False,
        "safety_benefit_evidence": False,
        "max_changed_records": 14,
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
    return {"final_decision": decision}


def _ledger(**overrides: object) -> dict[str, object]:
    decision = {
        "status": "post_pause_source_family_ledger_ready",
        "passed": True,
        "authorized_next_work": "materially_new_current_tick_source_family_discovery_or_keep_paused_only",
        "support_source_ready": False,
        "current_camp_dp_selector_route_rejected": True,
        "closed_source_family_labels_count": 12,
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
        "source_family_ledger": {
            "closed_source_family_labels": [
                "external_context",
                "temporal_consistency",
                "turn_logit",
            ]
        },
    }


def _strict_source(**overrides: object) -> dict[str, object]:
    decision = {
        "status": "targeted_source_discovery_route_closed",
        "passed": True,
        "source_discovery_closed": True,
        "authorized_next_work": "proof_protocol_v2_or_scenario_objective_redesign_only",
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
    return {"final_decision": decision}


def _report(**kwargs: object) -> dict[str, object]:
    inputs = {
        "targeted_safety_materiality": _targeted_safety(),
        "temporal_safety_proxy": _temporal_safety(),
        "source_family_ledger": _ledger(),
        "strict_source_closure": _strict_source(),
        "label": "unit",
    }
    inputs.update(kwargs)
    return build_report(**inputs)


def test_post_targeted_safety_support_boundary_passes_when_routes_are_closed() -> None:
    report = _report()
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["selector_route_paused"] is True
    assert decision["support_source_ready"] is False
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert "temporal_consistency" in report["closed_source_labels"]
    assert "red_clearance_gap_to_best_current_tick" in report["closed_source_labels"]
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_post_targeted_safety_support_boundary_blocks_actionable_existing_source() -> None:
    report = _report(
        targeted_safety_materiality=_targeted_safety(
            has_actionable_existing_safety_source=True,
            actionable_existing_safety_sources=["h30_union_planned_red_light_cost"],
        )
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert "targeted_safety_no_actionable_existing_source" in decision["failed_checks"]
    assert "targeted_safety_actionable_sources_empty" in decision["failed_checks"]
    assert decision["formal_seeds_authorized"] is False


def test_post_targeted_safety_support_boundary_blocks_temporal_safety_evidence() -> None:
    report = _report(
        temporal_safety_proxy=_temporal_safety(
            safety_proxy_evidence=True,
            authorized_next_work="temporal_consistency_selector_budget_preflight_only",
        )
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert "temporal_safety_authorizes_only_reject_or_alternative_source" in (
        decision["failed_checks"]
    )
    assert "temporal_safety_proxy_evidence_false" in decision["failed_checks"]


def test_post_targeted_safety_support_boundary_markdown_states_contract() -> None:
    report = _report()
    markdown = render_markdown(report)

    assert "Post Targeted Safety Support Boundary" in markdown
    assert "repeat_red_or_clearance_only_materiality" in markdown
    assert "No DP-side classical Benders" in markdown
    assert "current-tick fixed finite candidate coefficient" in markdown


def test_post_targeted_safety_support_boundary_cli_writes_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    targeted = tmp_path / "targeted.json"
    temporal = tmp_path / "temporal.json"
    ledger = tmp_path / "ledger.json"
    strict = tmp_path / "strict.json"
    output_json = tmp_path / "boundary.json"
    output_md = tmp_path / "boundary.md"
    targeted.write_text(json.dumps(_targeted_safety()), encoding="utf-8")
    temporal.write_text(json.dumps(_temporal_safety()), encoding="utf-8")
    ledger.write_text(json.dumps(_ledger()), encoding="utf-8")
    strict.write_text(json.dumps(_strict_source()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--targeted_safety_materiality_json",
            str(targeted),
            "--temporal_safety_proxy_json",
            str(temporal),
            "--source_family_ledger_json",
            str(ledger),
            "--strict_source_closure_json",
            str(strict),
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
    assert "Post Targeted Safety Support Boundary" in output_md.read_text(
        encoding="utf-8"
    )
