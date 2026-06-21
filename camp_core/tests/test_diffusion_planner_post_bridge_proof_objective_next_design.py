from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_post_bridge_proof_objective_next_design import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _bridge(
    *,
    status: str = "current_observable_separability_bridge_duplicate_rejected",
    authorized_next_work: str = "proof_objective_or_new_descriptor_family_design_only",
    closure_gate_passed: bool = True,
    duplicate: bool = True,
    materially_new: bool = False,
    uncovered: list[str] | None = None,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": status,
            "closure_gate_passed": closure_gate_passed,
            "authorized_next_work": authorized_next_work,
            "new_replay_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "camp_retraining_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "equivalence": {
            "duplicate_route_evidence": duplicate,
            "materially_new_route": materially_new,
            "current_records": 48,
            "current_candidate_rows": 384,
            "uncovered_current_material_fields": uncovered or [],
        },
    }


def test_post_bridge_plan_authorizes_targeted_proof_objective_only() -> None:
    report = build_report(bridge_report=_bridge(), label="unit")

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["recommended_first_action"] == (
        "predeclare_targeted_safety_intervention_proof_objective"
    )
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False

    first = report["candidate_next_objectives"][0]
    assert first["name"] == "targeted_safety_intervention_proof_objective"
    assert first["recommended_first"] is True
    assert first["status"] == "authorized_predeclaration_only"
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]

    closed = {row["name"] for row in report["closed_routes"]}
    assert "current_observable_descriptor_separability_rerun" in closed
    assert "camp_retraining_from_closed_descriptor_family" in closed


def test_post_bridge_plan_blocks_if_bridge_found_materially_new_route() -> None:
    report = build_report(
        bridge_report=_bridge(
            status="current_observable_separability_bridge_materially_new_route_ready",
            duplicate=False,
            materially_new=True,
            uncovered=["candidate_visibility_margin_m"],
        )
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    bridge_check = next(
        check for check in report["plan_checks"] if check["name"] == "bridge_has_closure_evidence"
    )
    assert bridge_check["passed"] is False


def test_post_bridge_plan_blocks_if_bridge_source_is_not_closed() -> None:
    report = build_report(
        bridge_report=_bridge(
            status="current_observable_separability_bridge_evidence_missing",
            closure_gate_passed=False,
            duplicate=False,
        )
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert any(not check["passed"] for check in report["plan_checks"])


def test_post_bridge_plan_markdown_states_boundaries() -> None:
    report = build_report(bridge_report=_bridge(), label="unit")
    markdown = render_markdown(report)

    assert "Post-Bridge Proof Objective Next Design Plan" in markdown
    assert "targeted_safety_intervention_proof_objective" in markdown
    assert "does not run DP" in markdown
    assert "not a classical Benders decomposition" in markdown


def test_post_bridge_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    bridge_path = tmp_path / "bridge.json"
    output_json = tmp_path / "post_bridge_plan.json"
    output_md = tmp_path / "post_bridge_plan.md"
    bridge_path.write_text(json.dumps(_bridge()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "post_bridge_plan",
            "--bridge_json",
            str(bridge_path),
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
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Post-Bridge Proof Objective" in output_md.read_text(encoding="utf-8")
