from __future__ import annotations

from scripts.integrations.plan_diffusion_planner_proof_protocol_v2 import (
    REQUIRED_SCENARIO_BUCKETS,
    build_report,
    render_markdown,
)


def _redesign_gate(
    *,
    status: str = "proof_protocol_redesign_required",
    passed: bool = True,
    authorized_next_work: str = (
        "predeclare_proof_protocol_v2_or_scenario_objective_design_only"
    ),
    blocked: bool = False,
    buckets: list[str] | None = None,
) -> dict[str, object]:
    return {
        "analysis": {"name": "dp_camp_proof_protocol_redesign_gate_v1"},
        "required_scenario_buckets": (
            list(REQUIRED_SCENARIO_BUCKETS) if buckets is None else buckets
        ),
        "final_decision": {
            "status": status,
            "passed": passed,
            "authorized_next_work": authorized_next_work,
            "online_selector_authorized": blocked,
            "reasons": ["proof_protocol_redesign_required"],
        },
    }


def test_proof_protocol_v2_predeclares_safety_claim_without_authorizing_runs() -> None:
    report = build_report(redesign_gate=_redesign_gate(), label="unit")

    decision = report["final_decision"]
    assert decision["status"] == "proof_protocol_v2_predeclared"
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == (
        "scenario_manifest_and_evidence_matrix_design_only"
    )
    assert decision["new_replay_authorized"] is False
    assert decision["closed_loop_smoke_authorized"] is False
    assert decision["full36_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False

    protocol = report["protocol"]
    assert protocol["primary_score"]["name"] == "SafetyCost_v1"
    assert protocol["primary_score"]["direction"] == "lower_is_better"
    assert "ci95_high(SafetyCost_CAMP_minus_DP_Top1) < 0" in (
        protocol["primary_score"]["claim_rule"]
    )
    assert "red_light_turn" in protocol["required_scenario_buckets"]
    assert "DP Top-1" in protocol["comparators"]
    assert "formal_seeds" in protocol["hard_gates"]
    assert "finite candidate ranking is not a classical Benders decomposition" in (
        protocol["camp_math_contract"]
    )

    markdown = render_markdown(report)
    assert "ProofProtocol v2 Predeclaration" in markdown
    assert "SafetyCost_v1" in markdown
    assert "not a classical Benders" in markdown


def test_proof_protocol_v2_blocks_when_redesign_gate_did_not_pass() -> None:
    report = build_report(
        redesign_gate=_redesign_gate(
            status="proof_protocol_redesign_sources_incomplete",
            passed=False,
        )
    )

    decision = report["final_decision"]
    assert (
        decision["status"]
        == "proof_protocol_v2_predeclaration_blocked_by_source_gate"
    )
    assert decision["passed"] is False
    assert decision["new_replay_authorized"] is False
    assert report["source_gate"]["passed"] is False


def test_proof_protocol_v2_blocks_authorization_conflicts() -> None:
    report = build_report(redesign_gate=_redesign_gate(blocked=True))

    assert (
        report["final_decision"]["status"]
        == "proof_protocol_v2_predeclaration_blocked_by_source_gate"
    )
    assert report["source_gate"]["blocked_true"] == ["online_selector_authorized"]


def test_proof_protocol_v2_requires_all_predeclared_buckets() -> None:
    buckets = [bucket for bucket in REQUIRED_SCENARIO_BUCKETS if bucket != "normal"]
    report = build_report(redesign_gate=_redesign_gate(buckets=buckets))

    assert report["source_gate"]["passed"] is False
    assert report["source_gate"]["missing_required_buckets"] == ["normal"]
    assert (
        report["final_decision"]["status"]
        == "proof_protocol_v2_predeclaration_blocked_by_source_gate"
    )
