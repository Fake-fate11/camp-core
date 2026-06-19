from __future__ import annotations

from scripts.integrations.plan_diffusion_planner_next_design_boundary import (
    build_report,
    render_markdown,
)


def _evidence(name: str, status: str, **flags: bool) -> dict[str, object]:
    decision = {
        "status": status,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
    }
    decision.update(flags)
    return {
        "name": name,
        "path": f"/fake/{name}.json",
        "payload": {
            "analysis": {"name": f"{name}_analysis"},
            "final_decision": decision,
        },
    }


def test_next_design_boundary_requires_new_offline_design_when_routes_rejected() -> None:
    report = build_report(
        [
            _evidence(
                "descriptor_only",
                "descriptor_only_screen_rejected",
            ),
            _evidence(
                "mode_seeking_guidance",
                "mode_seeking_candidate_availability_rejected",
            ),
            _evidence(
                "source_donor_gate",
                "source_donor_support_insufficient",
            ),
            _evidence(
                "latest_safe_route_topology",
                "route_topology_failure_patterns_hard_support_insufficient",
            ),
        ],
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == "next_design_boundary_requires_new_offline_design"
    assert decision["closed_loop_smoke_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["missing_or_inconclusive_families"] == []
    families = {item["name"]: item for item in report["route_families"]}
    assert families["dp_candidate_native_selector"]["status"] == "rejected_or_blocked"
    assert families["mode_seeking_candidate_generation"]["status"] == "rejected_or_blocked"
    assert families["source_donor_or_graft_transform"]["status"] == "rejected_or_blocked"
    assert families["lane_projected_stop_target"]["status"] == "rejected_or_blocked"

    markdown = render_markdown(report)
    assert "DP-CAMP Next Design Boundary" in markdown
    assert "classical Benders decomposition" in markdown


def test_next_design_boundary_reports_missing_family_evidence() -> None:
    report = build_report(
        [
            _evidence("descriptor_only", "descriptor_only_screen_rejected"),
            _evidence("latest_safe_route_topology", "route_topology_candidate_support_insufficient"),
        ],
    )

    decision = report["final_decision"]
    assert decision["status"] == "next_design_boundary_incomplete_evidence"
    assert "mode_seeking_candidate_generation" in decision[
        "missing_or_inconclusive_families"
    ]
    assert "source_donor_or_graft_transform" in decision[
        "missing_or_inconclusive_families"
    ]


def test_next_design_boundary_rejects_source_authorization_conflict() -> None:
    report = build_report(
        [
            _evidence("descriptor_only", "descriptor_only_screen_rejected"),
            _evidence(
                "mode_seeking_guidance",
                "mode_seeking_candidate_availability_rejected",
                full36_authorized=True,
            ),
            _evidence("source_donor_gate", "source_donor_support_insufficient"),
            _evidence(
                "latest_safe_route_topology",
                "route_topology_failure_patterns_hard_support_insufficient",
            ),
        ],
    )

    decision = report["final_decision"]
    assert decision["status"] == "next_design_boundary_source_conflict"
    assert decision["source_authorization_conflicts"] == [
        "mode_seeking_guidance:full36_authorized"
    ]
