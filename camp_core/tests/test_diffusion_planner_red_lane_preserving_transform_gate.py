from __future__ import annotations

from scripts.integrations.plan_diffusion_planner_red_lane_preserving_transform_gate import (
    build_report,
    render_markdown,
)


def _support_gate() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "candidate_generation_support_gate_requires_new_design",
            "closed_loop_smoke_authorized": False,
            "online_selector_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
        },
        "route_families": [
            {"name": "current_route_lane_guidance", "status": "rejected"},
            {"name": "selector_threshold_or_weight_retraining", "status": "blocked"},
            {"name": "closed_loop_or_full36_before_offline_gate", "status": "blocked"},
        ],
        "next_design_requirements": {
            "authorized_next_work": "predeclared_offline_design_gate_only",
        },
    }


def _splice_reason() -> dict[str, object]:
    return {
        "analysis": {"name": "dp_camp_splice_shadow_pilot_audit_v1"},
        "records": {
            "selection_effect_values": [False],
            "online_selector_change_values": [False],
            "target_records": 75,
            "changed": 18,
            "no_budget": 57,
            "no_budget_class_counts": {
                "no_hard_feasible_transformed_candidates": 56,
                "splice_removed_lower_red_advantage": 1,
            },
            "hard_infeasible_reason_counts": {
                "dp_lane_crossing": 101,
                "dp_red_light": 237,
            },
            "lower_union_red_hard_infeasible_reason_counts": {
                "dp_lane_crossing": 83,
                "dp_red_light": 203,
            },
        },
        "latency": {
            "all_target_records": {"p95": 23.6},
        },
    }


def _h_anchor_grid(*, lower_hard_count: int = 0) -> dict[str, object]:
    return {
        "analysis": "seed2 npc4 tl_on no-budget splice transform design grid",
        "camp_commit": "347ae79",
        "dp_commit": "7a1d33d",
        "rows": [
            {
                "name": "anchor10_blend40_donor_offset",
                "anchor_steps": 10,
                "blend_steps": 40,
                "lower_union_red_count": 203,
                "lower_union_red_hard_feasible_count": lower_hard_count,
                "shadow_changed_snapshots": lower_hard_count,
                "lower_union_red_hard_infeasibility_reason_counts": {
                    "dp_lane_crossing": 83,
                    "dp_red_light": 203,
                },
            },
            {
                "name": "anchor40_blend40_donor_offset",
                "anchor_steps": 40,
                "blend_steps": 40,
                "lower_union_red_count": 72,
                "lower_union_red_hard_feasible_count": lower_hard_count,
                "shadow_changed_snapshots": lower_hard_count,
                "lower_union_red_hard_infeasibility_reason_counts": {
                    "dp_red_light": 72,
                },
            },
        ],
    }


def test_red_lane_transform_gate_authorizes_only_offline_bridge_screen() -> None:
    report = build_report(
        candidate_support_gate=_support_gate(),
        splice_reason=_splice_reason(),
        h_anchor_grid=_h_anchor_grid(),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == "red_lane_preserving_transform_gate_ready"
    assert (
        decision["authorized_implementation"]
        == "offline_world_frame_donor_tail_bridge_recompute_screen"
    )
    assert decision["closed_loop_smoke_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert report["design_contract"]["design_name"] == "world_frame_donor_tail_bridge"
    assert report["offline_recompute_gate"]["authorized_scope"] == (
        "offline_fixed_snapshot_recompute_only"
    )

    markdown = render_markdown(report)
    assert "Red/Lane-Preserving Transform Design Gate" in markdown
    assert "not optimize trajectory coordinates" in markdown


def test_red_lane_transform_gate_blocks_when_old_h_anchor_grid_has_support() -> None:
    report = build_report(
        candidate_support_gate=_support_gate(),
        splice_reason=_splice_reason(),
        h_anchor_grid=_h_anchor_grid(lower_hard_count=2),
    )

    decision = report["final_decision"]
    assert decision["status"] == "red_lane_preserving_transform_gate_blocked"
    assert "h_anchor_grid_failed_lower_red_hard_feasibility" in decision[
        "failed_preconditions"
    ]
    assert decision["authorized_implementation"] is None


def test_red_lane_transform_gate_rejects_source_authorization_conflict() -> None:
    support = _support_gate()
    support["final_decision"]["full36_authorized"] = True

    report = build_report(
        candidate_support_gate=support,
        splice_reason=_splice_reason(),
        h_anchor_grid=_h_anchor_grid(),
    )

    decision = report["final_decision"]
    assert decision["status"] == "red_lane_preserving_transform_gate_source_conflict"
    assert decision["source_authorization_conflicts"] == ["source_0:full36_authorized"]
    assert decision["authorized_implementation"] is None
