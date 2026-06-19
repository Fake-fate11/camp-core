from __future__ import annotations

from scripts.integrations.plan_diffusion_planner_candidate_generation_support_gate import (
    build_report,
    render_markdown,
)


def _availability_report() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "mode_seeking_candidate_availability_rejected",
            "gates": {
                "candidate0_preserved": True,
                "candidate0_structural_preservation_contract": True,
                "non_top1_dense_lane_change_support_pass": False,
                "endpoint_pairwise_mean_pass": False,
                "endpoint_gain_pass": False,
                "latency_p95_pass": False,
            },
        },
        "aggregate": {"guided_latency_p95_ms": 382.1},
    }


def _failure_source_report(status: str) -> dict[str, object]:
    reward_gate = status == "mode_seeking_failure_source_reward_gate_suspect"
    return {
        "final_decision": {
            "status": status,
            "reward_gate_suspect": reward_gate,
            "geometry_or_tracker_support_insufficient": not reward_gate,
            "latency_blocked": not reward_gate,
            "contract_ok": True,
            "formal_seeds_absent": True,
            "closed_loop_smoke_authorized": False,
            "online_selector_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
        },
        "aggregate": {
            "candidate0_preservation_max_abs_xy_m": 0.0,
            "candidate_reward_feasible_total": 0,
            "combined_tracker_support_records": 0 if not reward_gate else 1,
            "endpoint_pairwise_mean_gain_m": -0.001 if not reward_gate else 0.3,
            "latency_p95_ms": 382.1 if not reward_gate else 90.0,
            "gates": {
                "candidate0_preserved": True,
                "reward_feasible_exists": False,
                "combined_tracker_support_exists": reward_gate,
                "endpoint_gain_pass": reward_gate,
            },
        },
    }


def _next_design_preflight() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "next_design_preflight_has_conditional_paths",
        },
        "design_routes": [
            {
                "name": "simple_k_noise_or_same_mode_generator",
                "status": "rejected",
            },
            {
                "name": "new_mode_seeking_candidate_generation",
                "status": "conditional_next_design",
            },
        ],
    }


def test_support_gate_requires_new_design_after_support_failure() -> None:
    report = build_report(
        availability=_availability_report(),
        failure_source=_failure_source_report(
            "mode_seeking_failure_source_candidate_support_insufficient"
        ),
        next_design_preflight=_next_design_preflight(),
        label="unit",
    )

    decision = report["final_decision"]
    assert (
        decision["status"]
        == "candidate_generation_support_gate_requires_new_design"
    )
    assert decision["closed_loop_smoke_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    routes = {route["name"]: route for route in report["route_families"]}
    assert routes["current_route_lane_guidance"]["status"] == "rejected"
    assert (
        routes["simple_k_noise_or_same_mode_generator"]["status"]
        == "rejected_by_prior_preflight"
    )
    assert (
        report["next_design_requirements"]["authorized_next_work"]
        == "predeclared_offline_design_gate_only"
    )

    markdown = render_markdown(report)
    assert "Candidate-Generation Support Design Gate" in markdown
    assert "not classical Benders decomposition" in markdown


def test_support_gate_redirects_reward_gate_suspect_to_gate_audit() -> None:
    report = build_report(
        availability=_availability_report(),
        failure_source=_failure_source_report(
            "mode_seeking_failure_source_reward_gate_suspect"
        ),
    )

    decision = report["final_decision"]
    assert (
        decision["status"]
        == "candidate_generation_support_gate_requires_reward_gate_audit"
    )
    assert "reward feasibility gate" in decision["next_step"]


def test_support_gate_rejects_source_authorization_conflict() -> None:
    failure = _failure_source_report(
        "mode_seeking_failure_source_candidate_support_insufficient"
    )
    failure["final_decision"]["full36_authorized"] = True

    report = build_report(
        availability=_availability_report(),
        failure_source=failure,
    )

    decision = report["final_decision"]
    assert decision["status"] == "candidate_generation_support_gate_source_conflict"
    assert decision["source_authorization_conflicts"] == ["source_1:full36_authorized"]
