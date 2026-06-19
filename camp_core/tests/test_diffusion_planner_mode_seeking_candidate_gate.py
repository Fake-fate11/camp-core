from __future__ import annotations

from scripts.integrations.plan_diffusion_planner_mode_seeking_candidate_gate import (
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    render_markdown,
)


def _next_design_preflight(
    *,
    mode_status: str = "conditional_next_design",
    same_mode_status: str = "rejected",
) -> dict[str, object]:
    return {
        "analysis": {"name": "dp_camp_next_design_gate_preflight_v1"},
        "final_decision": {
            "status": "next_design_preflight_has_conditional_paths",
            "conditional_paths": ["new_mode_seeking_candidate_generation"],
        },
        "design_routes": [
            {
                "name": "new_mode_seeking_candidate_generation",
                "route_type": "candidate_generation",
                "status": mode_status,
            },
            {
                "name": "simple_k_noise_or_same_mode_generator",
                "route_type": "candidate_generation",
                "status": same_mode_status,
            },
        ],
    }


def _candidate_generation_controls(
    *,
    official_guidance: bool = True,
    prototype_support: bool = True,
    guidance_disabled: bool = True,
    dp_source_modification_required: bool = False,
    camp_atom_schema_change_required: bool = False,
) -> dict[str, object]:
    return {
        "analysis": {"name": "dp_candidate_generation_controls_audit_v1"},
        "admissibility": {
            "official_guidance_available": official_guidance,
            "prototype_support_available": prototype_support,
            "current_runner_guidance_disabled": guidance_disabled,
            "dp_source_modification_required": dp_source_modification_required,
            "camp_atom_schema_change_required": camp_atom_schema_change_required,
        },
        "next_gate": {
            "decision": "predeclare_default_off_guidance_candidate_set_diagnostic"
        },
    }


def test_mode_seeking_gate_authorizes_only_default_off_availability_diagnostic() -> None:
    report = build_report(
        next_design_preflight=_next_design_preflight(),
        candidate_generation_controls=_candidate_generation_controls(),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["implementation_authorized"] is True
    assert decision["authorized_implementation"] == (
        "default_off_candidate_availability_diagnostic"
    )
    assert decision["closed_loop_smoke_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["camp_retraining_authorized"] is False

    contract = report["design_contract"]
    assert contract["dp_source_modification_allowed"] is False
    assert contract["camp_atom_schema_change_allowed"] is False
    assert contract["baseline_preservation"]["candidate0_must_match_unguided_top1"]

    gate = report["candidate_availability_gate"]
    requirements = gate["outcome_free_requirements"]
    assert requirements["min_endpoint_pairwise_mean_m"] == 0.50
    assert requirements["min_mode_count_mean"] == 2.0
    assert requirements["non_top1_dense_lane_change_support_rate_min"] == 0.25

    markdown = render_markdown(report)
    assert "Mode-Seeking Candidate Design Gate" in markdown
    assert "not classical Benders decomposition" in markdown
    assert "default_off_candidate_availability_diagnostic" in markdown


def test_mode_seeking_gate_blocks_when_preconditions_fail() -> None:
    report = build_report(
        next_design_preflight=_next_design_preflight(
            mode_status="inconclusive",
            same_mode_status="inconclusive",
        ),
        candidate_generation_controls=_candidate_generation_controls(
            official_guidance=False,
            guidance_disabled=False,
            dp_source_modification_required=True,
        ),
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert decision["implementation_authorized"] is False
    assert decision["authorized_implementation"] is None
    assert "mode_route_is_conditional" in decision["failed_preconditions"]
    assert "same_mode_variants_rejected" in decision["failed_preconditions"]
    assert "official_guidance_available" in decision["failed_preconditions"]
    assert "current_runner_guidance_disabled" in decision["failed_preconditions"]
    assert "no_dp_source_modification_required" in decision["failed_preconditions"]


def test_mode_seeking_gate_requires_candidate_generation_controls() -> None:
    report = build_report(
        next_design_preflight=_next_design_preflight(),
        candidate_generation_controls=None,
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert "official_guidance_available" in decision["failed_preconditions"]
    assert "prototype_support_available" in decision["failed_preconditions"]
    assert "current_runner_guidance_disabled" in decision["failed_preconditions"]
