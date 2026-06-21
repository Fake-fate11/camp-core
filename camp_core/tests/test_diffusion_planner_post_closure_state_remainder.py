from __future__ import annotations

import json

import pytest

from scripts.integrations.plan_diffusion_planner_post_closure_state_remainder import (
    build_report,
    main,
    render_markdown,
)


def _score_inventory(status: str = "no_leak_score_family_inventory_requires_new_design"):
    return {
        "analysis": {"name": "dp_camp_no_leak_score_family_inventory_v1"},
        "score_families": [
            {"name": "non_turn_interaction_family", "status": "rejected_or_limited"},
            {"name": "observable_interaction_family", "status": "rejected_or_limited"},
            {"name": "progress_lane_hard_context", "status": "rejected_or_limited"},
            {"name": "revised_context_atom_family", "status": "rejected_or_limited"},
            {"name": "relaxed_strict_atom_family", "status": "rejected_or_limited"},
            {"name": "turn_logit_atom_family", "status": "rejected_or_limited"},
        ],
        "final_decision": {
            "status": status,
            "new_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
        },
    }


def _coverage(
    status: str = "observable_state_payload_coverage_ready_for_offline_separability_design",
    fields: list[str] | None = None,
):
    if fields is None:
        fields = [
            "candidate_route_segment_index",
            "candidate_route_projection_s_m",
            "candidate_route_lateral_error_m",
            "candidate_red_stopline_distance_m",
            "candidate_red_heading_alignment",
            "candidate_route_heading_change_rad",
            "candidate_min_obstacle_clearance_lower_bound_m",
        ]
    return {
        "analysis": {"name": "dp_camp_observable_state_payload_coverage_v1"},
        "final_decision": {
            "status": status,
            "records_total": 48,
            "payload_records": 48,
            "material_candidate_fields": fields,
            "new_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
        },
    }


def _state_inventory():
    return {
        "analysis": {"name": "dp_camp_observable_state_inventory_v1"},
        "final_decision": {
            "status": "observable_state_inventory_missing_new_logged_state",
            "primary_bottleneck": "missing_logged_candidate_state",
            "available_new_candidate_state_families": [],
            "available_existing_proxy_families": [
                "existing_comfort_proxy",
                "existing_traffic_proxy",
            ],
        },
    }


def test_post_closure_remainder_requires_source_visibility_when_logged_fields_closed() -> None:
    report = build_report(
        score_inventory=_score_inventory(),
        payload_coverage=_coverage(),
        state_inventory=_state_inventory(),
        label="unit",
    )

    decision = report["final_decision"]
    assert (
        decision["status"]
        == "post_closure_state_remainder_requires_source_visibility_inventory"
    )
    assert decision["authorized_next_work"] == (
        "read_only_current_tick_tensor_visibility_inventory_only"
    )
    assert decision["new_replay_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert decision["unconsumed_material_candidate_fields"] == []

    closures = {row["closure_status"] for row in report["field_remainder"]}
    assert closures == {"consumed_by_closed_family"}
    assert "not a classical Benders decomposition" in render_markdown(report)


def test_post_closure_remainder_fails_closed_when_inventory_is_stale() -> None:
    inventory = _score_inventory()
    inventory["score_families"] = [
        row
        for row in inventory["score_families"]
        if row["name"] != "non_turn_interaction_family"
    ]
    report = build_report(
        score_inventory=inventory,
        payload_coverage=_coverage(),
        state_inventory=_state_inventory(),
        label="stale_inventory",
    )

    decision = report["final_decision"]
    assert decision["status"] == "post_closure_state_remainder_score_inventory_stale"
    assert decision["authorized_next_work"] == (
        "refresh_score_family_inventory_before_state_remainder"
    )
    assert decision["missing_closed_score_families"] == [
        "non_turn_interaction_family"
    ]
    assert decision["new_replay_authorized"] is False
    assert "non_turn_interaction_family" in render_markdown(report)


def test_post_closure_remainder_detects_untried_logged_field() -> None:
    report = build_report(
        score_inventory=_score_inventory(),
        payload_coverage=_coverage(
            fields=[
                "candidate_route_projection_s_m",
                "candidate_diffusion_uncertainty_cost",
            ]
        ),
        state_inventory=_state_inventory(),
    )

    decision = report["final_decision"]
    assert decision["status"] == "post_closure_state_remainder_has_untried_logged_fields"
    assert decision["authorized_next_work"] == (
        "predeclare_new_descriptor_family_from_unconsumed_logged_fields_design_only"
    )
    assert decision["unconsumed_material_candidate_fields"] == [
        "candidate_diffusion_uncertainty_cost"
    ]


def test_post_closure_remainder_fails_closed_when_score_inventory_not_closed() -> None:
    report = build_report(
        score_inventory=_score_inventory(status="no_leak_score_family_inventory_incomplete_evidence"),
        payload_coverage=_coverage(),
        state_inventory=_state_inventory(),
    )

    decision = report["final_decision"]
    assert decision["status"] == "post_closure_state_remainder_score_inventory_not_ready"
    assert decision["closed_loop_smoke_authorized"] is False


def test_post_closure_remainder_fails_closed_when_payload_coverage_not_ready() -> None:
    report = build_report(
        score_inventory=_score_inventory(),
        payload_coverage=_coverage(
            status="observable_state_payload_coverage_insufficient_for_materiality"
        ),
        state_inventory=_state_inventory(),
    )

    decision = report["final_decision"]
    assert decision["status"] == "post_closure_state_remainder_payload_coverage_not_ready"
    assert decision["new_replay_authorized"] is False


def test_post_closure_remainder_cli_writes_json_and_markdown(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    score_path = tmp_path / "score.json"
    coverage_path = tmp_path / "coverage.json"
    state_path = tmp_path / "state.json"
    score_path.write_text(json.dumps(_score_inventory()), encoding="utf-8")
    coverage_path.write_text(json.dumps(_coverage()), encoding="utf-8")
    state_path.write_text(json.dumps(_state_inventory()), encoding="utf-8")
    output_json = tmp_path / "remainder.json"
    output_md = tmp_path / "remainder.md"

    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--score_family_inventory_json",
            str(score_path),
            "--observable_payload_coverage_json",
            str(coverage_path),
            "--observable_state_inventory_json",
            str(state_path),
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
    assert payload["final_decision"]["status"] == (
        "post_closure_state_remainder_requires_source_visibility_inventory"
    )
    assert "Post-Closure State Remainder" in output_md.read_text(encoding="utf-8")
