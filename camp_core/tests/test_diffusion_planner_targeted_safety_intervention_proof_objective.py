from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_targeted_safety_intervention_proof_objective import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    NORMAL_BUCKET,
    READY_STATUS,
    SAFETY_CRITICAL_BUCKETS,
    build_report,
    main,
    render_markdown,
)


def _post_bridge(
    *,
    status: str = "post_bridge_proof_objective_next_design_plan_ready",
    passed: bool = True,
    authorized_next_work: str = (
        "predeclare_targeted_safety_intervention_proof_objective_only"
    ),
    recommended_first_action: str = (
        "predeclare_targeted_safety_intervention_proof_objective"
    ),
    conflict: bool = False,
) -> dict[str, object]:
    return {
        "analysis": {
            "name": "dp_camp_post_bridge_proof_objective_next_design_v1"
        },
        "final_decision": {
            "status": status,
            "passed": passed,
            "authorized_next_work": authorized_next_work,
            "recommended_first_action": recommended_first_action,
            "training_execution_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": conflict,
            "camp_retraining_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def test_targeted_objective_predeclares_claim_without_authorizing_runs() -> None:
    report = build_report(post_bridge_plan=_post_bridge(), label="unit")

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["recommended_first_action"] == (
        "targeted_safety_intervention_scenario_manifest_design"
    )
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False

    objective = report["objective_contract"]
    assert objective["score"]["name"] == "SafetyCost_v1"
    assert objective["score"]["direction"] == "lower_is_better"
    assert set(SAFETY_CRITICAL_BUCKETS).issubset(objective["target_buckets"])
    assert NORMAL_BUCKET in objective["guard_buckets"]
    assert NORMAL_BUCKET not in objective["target_buckets"]
    assert "normal_non_degradation" in objective["guard_claims"]
    assert "overall_non_degradation" in objective["guard_claims"]
    assert "ci95_high(TargetSafetyCost_CAMP_minus_DP_Top1) < 0" in (
        objective["primary_claim"]["rule"]
    )
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_targeted_objective_blocks_when_source_status_is_not_ready() -> None:
    report = build_report(
        post_bridge_plan=_post_bridge(
            status="post_bridge_proof_objective_next_design_plan_blocked",
            passed=False,
            authorized_next_work=None,
        )
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert decision["authorized_next_work"] is None
    assert report["source_post_bridge_gate"]["passed"] is False


def test_targeted_objective_blocks_authorization_conflicts() -> None:
    report = build_report(post_bridge_plan=_post_bridge(conflict=True))

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert report["source_post_bridge_gate"]["blocked_action_conflicts"] == [
        "online_selector_authorized"
    ]


def test_targeted_objective_markdown_states_no_leak_and_no_benders() -> None:
    report = build_report(post_bridge_plan=_post_bridge(), label="unit")
    markdown = render_markdown(report)

    assert "Targeted Safety-Intervention Proof Objective" in markdown
    assert "SafetyCost_v1" in markdown
    assert "normal_non_degradation" in markdown
    assert "does not run DP" in markdown
    assert "No DP-side classical Benders" in markdown


def test_targeted_objective_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_path = tmp_path / "post_bridge_plan.json"
    output_json = tmp_path / "targeted_objective.json"
    output_md = tmp_path / "targeted_objective.md"
    source_path.write_text(json.dumps(_post_bridge()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "targeted_objective",
            "--post_bridge_plan_json",
            str(source_path),
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
    assert "Targeted Safety-Intervention" in output_md.read_text(encoding="utf-8")
