from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_post_pause_source_family_ledger import (
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _post_pause(**decision_overrides: object) -> dict[str, object]:
    decision = {
        "status": "post_pause_deployability_proof_objective_predeclared",
        "passed": True,
        "deployability_first_objective_ready": True,
        "objective_only_reopening_allowed": False,
        "authorized_next_work": "new_current_tick_source_family_proposal_only",
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
    decision.update(decision_overrides)
    return {
        "final_decision": decision,
        "deployability_first_objective": {
            "observed_gap": {
                "candidate_pool_opportunity_confirmed": True,
                "new_no_leak_support_missing": True,
            },
            "next_source_family_requirements": [
                "must not be route-speed, signal/right-of-way, turn-logit, DP-prior deviation, Top-1 retention, progress/lane-hard, observable interaction, route topology, mode-seeking, or any other closed family unless new non-equivalence evidence is supplied",
                "must provide candidate coefficients a_k that are finite for every candidate or fail closed",
                "must preserve affine scoring and convex CAMP master if atomized",
            ],
            "required_preconditions_before_replay": [
                "new_source_family_predeclared",
                "current_tick_visibility_proven_before_selection",
            ],
            "forbidden_shortcuts": [
                "using SafetyCost or closed-loop outcomes as runtime features",
                "calling finite-candidate DP selection classical Benders",
            ],
        },
    }


def _source_gate(**decision_overrides: object) -> dict[str, object]:
    decision = {
        "status": "new_no_leak_targeted_support_source_not_available",
        "passed": True,
        "support_source_ready": False,
        "admissible_support_sources": [],
        "rejected_support_sources": ["postprocess_execution_distortion_source_v1"],
        "current_camp_dp_selector_route_rejected": True,
        "authorized_next_work": (
            "source_level_targeted_support_discovery_or_pause_current_selector_route_only"
        ),
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
    decision.update(decision_overrides)
    return {
        "final_decision": decision,
        "closed_support_sources": {
            "closed_score_families": [
                "observable_interaction_family",
                "progress_lane_hard_context",
                "turn_logit_atom_family",
            ],
            "closed_route_names": [
                "objective_label_sensitivity",
                "tensor_visibility_without_unclosed_runtime_source",
            ],
            "available_existing_or_closed_proxy_families": [
                "existing_traffic_proxy",
                "dp_reward_lane_proxy",
            ],
        },
        "proposals": [
            {
                "name": "postprocess_execution_distortion_source_v1",
                "score_family": "postprocess_tracker_descriptor_family",
                "source_family": "postprocess_tracker_descriptor_signal",
                "admissible": False,
                "rejection_reasons": ["equivalent_to_closed_family"],
                "next_gate": "reject_or_rewrite_source_proposal",
            }
        ],
    }


def _external_closure() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "post_external_context_source_route_closed",
            "passed": True,
            "external_context_source_route_closed": True,
            "current_camp_dp_selector_route_rejected": True,
            "authorized_next_work": "scenario_objective_redesign_or_pause_only",
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


def _report(**kwargs: object) -> dict[str, object]:
    inputs = {
        "post_pause_objective": _post_pause(),
        "latest_source_gate": _source_gate(),
        "post_external_context_closure": _external_closure(),
        "label": "unit",
    }
    inputs.update(kwargs)
    return build_report(**inputs)


def test_post_pause_source_family_ledger_records_paused_route_boundary() -> None:
    report = _report()
    decision = report["final_decision"]
    ledger = report["source_family_ledger"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["support_source_ready"] is False
    assert decision["authorized_next_work"] == (
        "materially_new_current_tick_source_family_discovery_or_keep_paused_only"
    )
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert "progress_lane_hard_context" in ledger["closed_score_families"]
    assert "postprocess_tracker_descriptor_family" in ledger["closed_source_family_labels"]
    assert ledger["rejected_source_proposals"][0]["rejection_reasons"] == [
        "equivalent_to_closed_family"
    ]


def test_post_pause_source_family_ledger_blocks_if_latest_gate_accepts_source() -> None:
    report = _report(
        latest_source_gate=_source_gate(
            status="new_no_leak_targeted_support_source_predeclared",
            support_source_ready=True,
            admissible_support_sources=["phase_timing_runtime_payload"],
            authorized_next_work="default_off_new_no_leak_support_payload_design_only",
        )
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert decision["authorized_next_work"] is None
    assert "latest_source_gate_status" in decision["failed_checks"]
    assert "support_source_not_ready" in decision["failed_checks"]
    assert "no_admissible_support_sources" in decision["failed_checks"]


def test_post_pause_source_family_ledger_blocks_on_replay_authorization_conflict() -> None:
    report = _report(post_pause_objective=_post_pause(new_replay_authorized=True))

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert decision["authorized_next_work"] is None
    assert "post_pause_no_blocked_actions" in decision["failed_checks"]


def test_post_pause_source_family_ledger_markdown_states_math_boundary() -> None:
    report = _report()
    markdown = render_markdown(report)

    assert "Post-Pause Source-Family Ledger" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "not a DP-side classical Benders" in markdown
    assert "current-tick finite-candidate" in markdown


def test_post_pause_source_family_ledger_cli_writes_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    post_pause = tmp_path / "post_pause.json"
    source_gate = tmp_path / "source_gate.json"
    external_closure = tmp_path / "external_closure.json"
    output_json = tmp_path / "ledger.json"
    output_md = tmp_path / "ledger.md"
    post_pause.write_text(json.dumps(_post_pause()), encoding="utf-8")
    source_gate.write_text(json.dumps(_source_gate()), encoding="utf-8")
    external_closure.write_text(json.dumps(_external_closure()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--post_pause_objective_json",
            str(post_pause),
            "--latest_source_gate_json",
            str(source_gate),
            "--post_external_context_closure_json",
            str(external_closure),
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
    assert "Post-Pause Source-Family Ledger" in output_md.read_text(encoding="utf-8")
