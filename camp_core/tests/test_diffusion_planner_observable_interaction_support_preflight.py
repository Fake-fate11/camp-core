from __future__ import annotations

from scripts.integrations.plan_diffusion_planner_observable_interaction_support_preflight import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
)


def _geometry_report(
    *,
    status: str = "observable_interaction_geometry_bottleneck_diagnosed",
    passed: bool = True,
    next_work: str = (
        "reject_observable_interaction_route_or_predeclare_narrow_support_experiment"
    ),
    red_reason: str = "reduced_red_alignment_nonpositive",
    clearance_reason: str = "clearance_budget_never_active",
) -> dict:
    return {
        "geometry": {
            "red": {
                "reduced_near_budget_candidates": 2,
                "reduced_positive_alignment_candidates": 0,
            },
            "clearance": {
                "positive_obstacle_slot_candidates": 16,
                "inside_budget_candidates": 0,
            },
        },
        "bottlenecks": {
            "red_bottleneck": red_reason,
            "clearance_bottleneck": clearance_reason,
        },
        "final_decision": {
            "status": status,
            "passed": passed,
            "authorized_next_work": next_work,
            "current_observable_interaction_route_rejected": True,
            "new_replay_authorized": False,
            "offline_separability_authorized": False,
            "camp_retraining_authorized": False,
        },
    }


def test_support_preflight_rejects_current_route_and_authorizes_discovery_only() -> None:
    report = build_report(geometry_report=_geometry_report(), label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["current_observable_interaction_route_rejected"]
    assert report["final_decision"]["support_smoke_predeclared"] is False
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["new_replay_authorized"] is False
    assert report["final_decision"]["offline_separability_authorized"] is False
    assert report["final_decision"]["Full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    assert report["final_decision"]["DP_modification_authorized"] is False
    assert report["final_decision"]["classic_Benders_claim_authorized"] is False
    assert report["route_rejection"]["reject_current_route"] is True
    assert report["blocked_actions"]["run_replay_now"] is True
    assert "closed-loop outcome labels" in report["route_support_discovery_contract"][
        "forbidden_inputs"
    ]


def test_support_preflight_blocks_invalid_geometry_source() -> None:
    report = build_report(
        geometry_report=_geometry_report(
            status="observable_interaction_geometry_not_ready",
            passed=False,
            next_work="fix_geometry_source",
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["passed"] is False
    assert report["source_gate"]["passed"] is False
    assert report["final_decision"]["authorized_next_work"] is None
    assert report["final_decision"]["new_replay_authorized"] is False


def test_support_preflight_does_not_predeclare_when_route_is_not_rejected() -> None:
    report = build_report(
        geometry_report=_geometry_report(
            red_reason="red_context_supported",
            clearance_reason="clearance_budget_never_active",
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["route_rejection"]["reject_current_route"] is False
    assert report["final_decision"]["support_smoke_predeclared"] is False
    assert report["final_decision"]["new_replay_authorized"] is False
