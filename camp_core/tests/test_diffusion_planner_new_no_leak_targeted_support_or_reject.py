from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_new_no_leak_targeted_support_or_reject import (
    BLOCKED_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _targeted_failure(**decision_overrides: object) -> dict[str, object]:
    decision = {
        "status": "targeted_failure_attribution_no_current_route",
        "passed": True,
        "current_camp_dp_selector_route_rejected": True,
        "authorized_next_work": (
            "predeclare_new_no_leak_targeted_support_source_or_reject_current_route_only"
        ),
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
        "failure_summary": {
            "candidate_pool_opportunity_confirmed": True,
            "current_camp_targeted_failure_confirmed": True,
            "old_training_and_sensitivity_routes_closed": True,
            "new_no_leak_support_missing_in_current_artifacts": True,
        },
    }


def _bridge() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "current_observable_separability_bridge_duplicate_rejected",
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
        },
        "equivalence": {
            "duplicate_route_evidence": True,
            "materially_new_route": False,
            "uncovered_current_material_fields": [],
        },
    }


def _inventory() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "current_tick_no_leak_atom_support_inventory_no_unclosed_fields",
            "admissible_unclosed_candidate_families": [],
            "available_existing_or_closed_proxy_families": [
                "existing_traffic_proxy",
                "existing_comfort_proxy",
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
    }


def _support_bottleneck() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "current_fixed_dp_selector_calibration_exhausted",
            "reasons": ["posterior_support_exists_but_no_leak_guarded_support_insufficient"],
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
    }


def _valid_proposal() -> dict[str, object]:
    return {
        "name": "phase_time_to_change_if_runtime_available",
        "score_family": "phase_timing_targeted_family",
        "source_family": "phase_timing_runtime_payload",
        "current_tick_available": True,
        "candidate_level": True,
        "finite": True,
        "deterministic": True,
        "available_before_selection": True,
        "uses_future_outcome_labels": False,
        "requires_dp_modification": False,
        "requires_replay_to_compute": False,
        "requires_training_to_compute": False,
        "equivalent_to_closed_family": False,
        "atom_value_domain": "nonnegative",
    }


def _report(**kwargs: object) -> dict[str, object]:
    inputs = {
        "targeted_failure_attribution": _targeted_failure(),
        "observable_bridge": _bridge(),
        "support_inventory": _inventory(),
        "support_bottleneck": _support_bottleneck(),
        "proposals": [],
        "label": "unit",
    }
    inputs.update(kwargs)
    return build_report(**inputs)


def test_gate_rejects_current_route_when_no_new_source_is_predeclared() -> None:
    report = _report()
    decision = report["final_decision"]

    assert decision["status"] == REJECT_STATUS
    assert decision["passed"] is True
    assert decision["support_source_ready"] is False
    assert decision["current_camp_dp_selector_route_rejected"] is True
    assert decision["authorized_next_work"] == (
        "source_level_targeted_support_discovery_or_pause_current_selector_route_only"
    )
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert "progress_lane_hard_context" in report["closed_support_sources"][
        "closed_score_families"
    ]


def test_gate_accepts_only_a_genuinely_new_no_leak_source_proposal() -> None:
    report = _report(proposals=[_valid_proposal()])
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["support_source_ready"] is True
    assert decision["admissible_support_sources"] == [
        "phase_time_to_change_if_runtime_available"
    ]
    assert decision["authorized_next_work"] == (
        "default_off_new_no_leak_support_payload_design_only"
    )
    assert decision["closed_loop_replay_authorized"] is False
    assert report["proposals"][0]["admissible"] is True


def test_gate_rejects_proposal_that_reopens_closed_family() -> None:
    proposal = _valid_proposal()
    proposal["score_family"] = "progress_lane_hard_context"
    report = _report(proposals=[proposal])

    decision = report["final_decision"]
    assert decision["status"] == REJECT_STATUS
    assert decision["rejected_support_sources"] == [
        "phase_time_to_change_if_runtime_available"
    ]
    assert report["proposals"][0]["rejection_reasons"] == [
        "score_family_not_closed"
    ]


def test_gate_blocks_when_targeted_failure_source_is_not_ready() -> None:
    report = _report(
        targeted_failure_attribution=_targeted_failure(
            current_camp_dp_selector_route_rejected=False
        )
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert decision["passed"] is False
    assert decision["authorized_next_work"] is None
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "targeted_route_rejected" in failed


def test_gate_markdown_states_math_boundary() -> None:
    report = _report()
    markdown = render_markdown(report)

    assert "New No-Leak Targeted Support Source Gate" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "not a DP-side classical Benders" in markdown
    assert "none_provided" in markdown


def test_gate_cli_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    targeted = tmp_path / "targeted.json"
    bridge = tmp_path / "bridge.json"
    inventory = tmp_path / "inventory.json"
    bottleneck = tmp_path / "bottleneck.json"
    proposal = tmp_path / "proposal.json"
    output_json = tmp_path / "out.json"
    output_md = tmp_path / "out.md"
    targeted.write_text(json.dumps(_targeted_failure()), encoding="utf-8")
    bridge.write_text(json.dumps(_bridge()), encoding="utf-8")
    inventory.write_text(json.dumps(_inventory()), encoding="utf-8")
    bottleneck.write_text(json.dumps(_support_bottleneck()), encoding="utf-8")
    proposal.write_text(json.dumps({"proposals": [_valid_proposal()]}), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--targeted_failure_attribution_json",
            str(targeted),
            "--observable_bridge_json",
            str(bridge),
            "--support_inventory_json",
            str(inventory),
            "--support_bottleneck_json",
            str(bottleneck),
            "--proposal_json",
            str(proposal),
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
    assert "New No-Leak Targeted Support Source Gate" in output_md.read_text(
        encoding="utf-8"
    )
