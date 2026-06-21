from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_post_external_context_source_closure import (
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _source_inventory() -> dict:
    return {
        "final_decision": {
            "status": "external_source_visibility_inventory_has_design_candidate",
            "passed": True,
            "design_candidate_names": [
                "traffic_signal_phase_timing_or_right_of_way_state",
                "route_speed_limit_and_control_context",
            ],
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
        "rejected_visible_sources": [
            {"name": "turn_indicator_logits"},
            {"name": "dp_native_log_probability_or_candidate_score"},
        ],
    }


def _route_speed_gap() -> dict:
    return {
        "final_decision": {
            "status": "external_context_materiality_gap_diagnosed",
            "passed": True,
            "gap_names": [
                "traffic_signal_context_absent",
                "route_speed_context_available_but_no_candidate_excess",
                "route_speed_availability_constant",
                "nonmaterial_constant_speed_limit",
            ],
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


def _signal_counterfactual() -> dict:
    return {
        "summary": {
            "guarded_changed_records": 1,
            "guarded_atom_best_minus_selected_cost_mean": 5.178,
            "selected_preserving_guarded_changed_records": 0,
            "selected_preserving_guarded_atom_best_better_records": 0,
        },
        "final_decision": {
            "status": "external_context_atom_outcome_counterfactual_ready",
            "passed": True,
            "promotion_authorized": False,
            "tiny_counterfactual_noninferior": False,
            "guarded_tiny_counterfactual_noninferior": False,
            "selected_preserving_guarded_tiny_counterfactual_noninferior": True,
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


def _alternative_search() -> dict:
    return {
        "ranked_candidates": [
            {
                "name": "right_of_way_blocked_indicator_v1",
                "changed_records": 0,
                "changed_all_gate_records": 0,
            }
        ],
        "final_decision": {
            "status": "external_context_alternative_atom_search_rejected",
            "passed": False,
            "primary_gap": "no_alternative_external_context_atom_certificate_found",
            "passing_candidates": [],
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


def _report(**overrides: dict) -> dict:
    args = {
        "source_inventory": _source_inventory(),
        "route_speed_gap": _route_speed_gap(),
        "signal_counterfactual": _signal_counterfactual(),
        "alternative_search": _alternative_search(),
        "label": "unit",
    }
    args.update(overrides)
    return build_report(**args)


def test_post_external_context_source_closure_passes_when_both_sources_closed() -> None:
    report = _report()
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["external_context_source_route_closed"] is True
    assert decision["authorized_next_work"] == "scenario_objective_redesign_or_pause_only"
    assert decision["online_selector_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_post_external_context_source_closure_blocks_missing_route_speed_gap() -> None:
    route_speed = _route_speed_gap()
    route_speed["final_decision"]["gap_names"] = [
        "route_speed_context_available_but_no_candidate_excess"
    ]

    report = _report(route_speed_gap=route_speed)

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "route_speed_has_closure_gaps" in report["final_decision"]["failed_checks"]


def test_post_external_context_source_closure_blocks_signal_improvement() -> None:
    signal = _signal_counterfactual()
    signal["summary"]["selected_preserving_guarded_changed_records"] = 2

    report = _report(signal_counterfactual=signal)

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert (
        "signal_selected_preserving_changes_zero_records"
        in report["final_decision"]["failed_checks"]
    )


def test_post_external_context_source_closure_blocks_alternative_passing_candidate() -> None:
    alternative = _alternative_search()
    alternative["final_decision"]["passing_candidates"] = ["new_atom"]

    report = _report(alternative_search=alternative)

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "alternative_search_no_passing_candidates" in report["final_decision"]["failed_checks"]


def test_post_external_context_source_closure_markdown_states_boundary() -> None:
    markdown = render_markdown(_report())

    assert "Post External-Context Source Closure" in markdown
    assert "route_speed_context_available_but_no_candidate_excess" in markdown
    assert "No DP-side classical Benders" in markdown


def test_post_external_context_source_closure_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "source.json"
    route_path = tmp_path / "route.json"
    signal_path = tmp_path / "signal.json"
    alternative_path = tmp_path / "alternative.json"
    output_json = tmp_path / "closure.json"
    output_md = tmp_path / "closure.md"
    source_path.write_text(json.dumps(_source_inventory()), encoding="utf-8")
    route_path.write_text(json.dumps(_route_speed_gap()), encoding="utf-8")
    signal_path.write_text(json.dumps(_signal_counterfactual()), encoding="utf-8")
    alternative_path.write_text(json.dumps(_alternative_search()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "post-external-context-source-closure",
            "--source_inventory_json",
            str(source_path),
            "--route_speed_gap_json",
            str(route_path),
            "--signal_counterfactual_json",
            str(signal_path),
            "--alternative_search_json",
            str(alternative_path),
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
    assert "Post External-Context" in output_md.read_text(encoding="utf-8")
