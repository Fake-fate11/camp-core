from __future__ import annotations

from scripts.integrations.plan_diffusion_planner_proof_protocol_redesign import (
    EXPECTED_CLOSED_SCORE_FAMILIES,
    build_report,
    render_markdown,
)


def _score_family_inventory(
    *,
    missing_family: str | None = None,
    blocked: bool = False,
) -> dict[str, object]:
    rows = []
    for family in EXPECTED_CLOSED_SCORE_FAMILIES:
        status = "candidate_open" if family == missing_family else "rejected_or_limited"
        rows.append({"name": family, "status": status})
    return {
        "analysis": {"name": "dp_camp_no_leak_score_family_inventory_v1"},
        "score_families": rows,
        "final_decision": {
            "status": "no_leak_score_family_inventory_requires_new_design",
            "online_selector_authorized": blocked,
        },
    }


def _tensor_visibility(
    *,
    candidate_sources: list[str] | None = None,
) -> dict[str, object]:
    return {
        "analysis": {"name": "dp_camp_current_tick_tensor_visibility_v1"},
        "final_decision": {
            "status": "current_tick_tensor_visibility_no_new_candidate_source",
            "primary_gap": "visible_candidate_tensor_sources_already_closed",
            "candidate_source_names": candidate_sources or [],
            "closed_visible_candidate_source_names": ["turn_indicator_logits"],
        },
    }


def _safety_cost_proof() -> dict[str, object]:
    return {
        "analysis": {"name": "dp_camp_safety_cost_proof_v1"},
        "gates": {
            "candidate_pool_opportunity": {"passed": True},
            "current_camp_vs_top1": {
                "passed": False,
                "bucket_failures": {"red_light_turn": 0.1},
            },
            "safety_cost_trained_selector_vs_top1": {
                "passed": True,
                "bucket_failures": {},
                "overall_ci_high": -0.2,
            },
        },
        "final_decision": {
            "status": "candidate_branch_proof_passes_for_safety_cost_trained_selector",
            "safety_cost_trained_selector_candidate_branch_proof": True,
            "current_camp_complete_proof": False,
        },
    }


def _proof_to_deployable_gap() -> dict[str, object]:
    return {
        "analysis": {"name": "dp_camp_proof_to_deployable_gap_v1"},
        "mechanism": {
            "candidate_support_exists": True,
            "candidate_branch_selector_passes": True,
            "deployable_gate_passes": False,
            "root_cause_class": "score_schema_feasibility_fallback_deployability_gap",
            "primary_blockers": ["high_all_infeasible_fallback"],
        },
        "final_decision": {"status": "deployable_gap_diagnosed"},
    }


def _support_bottleneck() -> dict[str, object]:
    return {
        "analysis": {"name": "dp_camp_support_bottleneck_synthesis_v1"},
        "final_decision": {
            "status": "current_fixed_dp_selector_calibration_exhausted",
            "reasons": ["descriptor_only_screen_rejected"],
        },
    }


def _next_design_preflight() -> dict[str, object]:
    return {
        "analysis": {"name": "dp_camp_next_design_gate_preflight_v1"},
        "final_decision": {
            "status": "next_design_preflight_has_conditional_paths",
            "conditional_paths": ["materially_new_no_leak_atom_schema"],
            "rejected_paths": ["current_descriptor_threshold_or_reweighting"],
        },
    }


def _report(
    *,
    score_family_inventory: dict[str, object] | None = None,
    tensor_visibility: dict[str, object] | None = None,
) -> dict[str, object]:
    return build_report(
        score_family_inventory=score_family_inventory or _score_family_inventory(),
        tensor_visibility=tensor_visibility or _tensor_visibility(),
        safety_cost_proof=_safety_cost_proof(),
        proof_to_deployable_gap=_proof_to_deployable_gap(),
        support_bottleneck=_support_bottleneck(),
        next_design_preflight=_next_design_preflight(),
        label="unit",
    )


def test_proof_protocol_redesign_gate_authorizes_design_only_protocol() -> None:
    report = _report()

    decision = report["final_decision"]
    assert decision["status"] == "proof_protocol_redesign_required"
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == (
        "predeclare_proof_protocol_v2_or_scenario_objective_design_only"
    )
    assert decision["online_selector_authorized"] is False
    assert decision["full36_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert "safetycost_candidate_branch_proof_exists" in decision["reasons"]

    contract = report["proof_protocol_v2_contract"]
    assert contract["score"]["name"] == "SafetyCost_v1"
    assert contract["score"]["direction"] == "lower_is_better"
    assert "red_light_turn" in contract["required_buckets"]
    assert "finite candidate selectors are not classical Benders" in (
        contract["math_boundary"]
    )

    markdown = render_markdown(report)
    assert "ProofProtocol v2 Contract" in markdown
    assert "not classical Benders" in markdown


def test_proof_protocol_redesign_gate_requires_closed_score_families() -> None:
    report = _report(
        score_family_inventory=_score_family_inventory(
            missing_family="turn_logit_atom_family"
        )
    )

    assert (
        report["final_decision"]["status"]
        == "proof_protocol_redesign_sources_incomplete"
    )
    assert report["final_decision"]["passed"] is False
    assert report["final_decision"]["incomplete_sources"] == [
        "score_family_inventory"
    ]
    assert report["sources"]["score_family_inventory"][
        "missing_or_unclosed_families"
    ] == ["turn_logit_atom_family"]


def test_proof_protocol_redesign_gate_requires_no_open_tensor_sources() -> None:
    report = _report(
        tensor_visibility=_tensor_visibility(
            candidate_sources=["candidate_rollout_cost_tensor"]
        )
    )

    assert (
        report["final_decision"]["status"]
        == "proof_protocol_redesign_sources_incomplete"
    )
    assert report["final_decision"]["incomplete_sources"] == ["tensor_visibility"]
    assert report["sources"]["tensor_visibility"]["candidate_sources"] == [
        "candidate_rollout_cost_tensor"
    ]


def test_proof_protocol_redesign_gate_rejects_source_authorization_conflict() -> None:
    report = _report(score_family_inventory=_score_family_inventory(blocked=True))

    decision = report["final_decision"]
    assert decision["status"] == "proof_protocol_redesign_source_conflict"
    assert decision["passed"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["source_authorization_conflicts"] == [
        "dp_camp_no_leak_score_family_inventory_v1:online_selector_authorized"
    ]
