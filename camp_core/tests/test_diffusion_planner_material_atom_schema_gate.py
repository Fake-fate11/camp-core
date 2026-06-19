from __future__ import annotations

from scripts.integrations.plan_diffusion_planner_material_atom_schema_gate import (
    build_report,
    render_markdown,
)


def _boundary(*, status: str = "next_design_boundary_requires_new_offline_design") -> dict[str, object]:
    return {
        "final_decision": {
            "status": status,
            "missing_or_inconclusive_families": [],
            "support_present_families": [],
            "source_authorization_conflicts": [],
            "closed_loop_smoke_authorized": False,
            "online_selector_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
        },
        "route_families": [
            {
                "name": "dp_candidate_native_selector",
                "status": "rejected_or_blocked",
            },
            {
                "name": "mode_seeking_candidate_generation",
                "status": "rejected_or_blocked",
            },
            {
                "name": "source_donor_or_graft_transform",
                "status": "rejected_or_blocked",
            },
            {
                "name": "lane_projected_stop_target",
                "status": "rejected_or_blocked",
            },
        ],
        "next_design_boundary": {
            "authorized_next_work": "new_predeclared_offline_no_leak_design_gate_only",
        },
    }


def test_material_atom_schema_gate_authorizes_only_offline_availability_audit() -> None:
    report = build_report(next_design_boundary=_boundary(), label="unit")

    decision = report["final_decision"]
    assert decision["status"] == "material_atom_schema_gate_ready"
    assert (
        decision["authorized_implementation"]
        == "offline_material_atom_schema_availability_audit"
    )
    assert decision["camp_retraining_authorized"] is False
    assert decision["closed_loop_smoke_authorized"] is False
    assert report["proposed_schema"]["schema_name"] == (
        "material_support_certificate_atoms_v1"
    )
    assert report["offline_availability_gate"]["implementation_allowed_now"] is False
    assert report["preconditions"][0]["passed"] is True

    markdown = render_markdown(report)
    assert "Material CAMP Atom-Schema Gate" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "classical Benders" in markdown


def test_material_atom_schema_gate_blocks_when_boundary_not_ready() -> None:
    report = build_report(
        next_design_boundary=_boundary(status="next_design_boundary_incomplete_evidence")
    )

    decision = report["final_decision"]
    assert decision["status"] == "material_atom_schema_gate_blocked"
    assert "boundary_requires_new_offline_design" in decision["failed_preconditions"]
    assert decision["authorized_implementation"] is None


def test_material_atom_schema_gate_rejects_source_authorization_conflict() -> None:
    boundary = _boundary()
    boundary["final_decision"]["full36_authorized"] = True

    report = build_report(next_design_boundary=boundary)

    decision = report["final_decision"]
    assert decision["status"] == "material_atom_schema_gate_source_conflict"
    assert decision["source_authorization_conflicts"] == [
        "next_design_boundary:full36_authorized"
    ]
    assert decision["authorized_implementation"] is None
