from __future__ import annotations

from dataclasses import replace

from scripts.integrations.plan_diffusion_planner_observable_interaction_descriptor_preflight import (
    DESCRIPTOR_SPECS,
    NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    render_markdown,
)


def _report(status: str, *, passed: bool, next_work: str = "next") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": passed,
            "primary_gap": "gap",
            "authorized_next_work": next_work,
        }
    }


def _ready_inputs() -> dict:
    return {
        "observability_limit_report": _report(
            "relaxed_strict_atom_observability_limit_recorded",
            passed=True,
        ),
        "observable_separability_report": _report(
            "matched_observable_descriptor_separability_rejected",
            passed=False,
        ),
        "observable_bottleneck_report": _report(
            "observable_descriptor_bottleneck_diagnosed",
            passed=True,
        ),
    }


def test_interaction_descriptor_preflight_ready() -> None:
    report = analyze(**_ready_inputs())

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["authorized_next_work"] == NEXT_WORK
    assert report["descriptor_audit"]["passed"] is True
    assert report["descriptor_audit"]["min_interaction_degree"] >= 2
    assert report["descriptor_audit"]["all_required_fields_available"] is True
    assert report["blocked_actions"]["new_replay_authorized"] is False
    assert report["blocked_actions"]["classic_benders_claim_authorized"] is False


def test_interaction_descriptor_preflight_blocks_without_limit() -> None:
    inputs = _ready_inputs()
    inputs["observability_limit_report"] = _report("unexpected", passed=False)
    report = analyze(**inputs)

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["primary_gap"] == "observability_limit_not_recorded"


def test_interaction_descriptor_preflight_rejects_invalid_descriptor() -> None:
    invalid = replace(
        DESCRIPTOR_SPECS[0],
        name="route_projection_delta_m",
        interaction_degree=1,
    )
    report = analyze(
        **_ready_inputs(),
        descriptor_specs=(invalid,),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["descriptor_audit"]["passed"] is False
    assert any("not an interaction descriptor" in error for error in report["descriptor_audit"]["errors"])
    assert any("reuses a rejected" in error for error in report["descriptor_audit"]["errors"])


def test_interaction_descriptor_preflight_markdown_mentions_boundary() -> None:
    report = analyze(**_ready_inputs())
    rendered = render_markdown(report)

    assert "Observable Interaction Descriptor Preflight" in rendered
    assert "score_k(w)=a_k^T w" in rendered
    assert "classical Benders" in rendered
