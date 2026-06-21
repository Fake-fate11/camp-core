from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_post_pause_deployability_proof_objective import (
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _pause_gate() -> dict:
    return {
        "final_decision": {
            "status": "post_external_context_selector_route_paused",
            "passed": True,
            "selector_route_paused": True,
            "deployable_camp_dp_selector_route_exists": False,
            "authorized_next_work": "new_proof_objective_or_new_current_tick_source_predeclaration_only",
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "CAMP_retraining_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "DP_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def _proof_gap() -> dict:
    return {
        "mechanism": {
            "candidate_support_exists": True,
            "candidate_branch_selector_passes": True,
            "deployable_gate_passes": False,
            "root_cause_class": "score_schema_feasibility_fallback_deployability_gap",
            "primary_blockers": [
                "dense_lane_change_safety_cost_regression",
                "low_candidate_feasible_rate",
            ],
        },
        "final_decision": {
            "status": "deployable_gap_diagnosed",
            "camp_retraining_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
        },
    }


def _targeted_failure() -> dict:
    return {
        "failure_summary": {
            "candidate_pool_opportunity_confirmed": True,
            "new_no_leak_support_missing_in_current_artifacts": True,
            "old_training_and_sensitivity_routes_closed": True,
        },
        "final_decision": {
            "status": "targeted_failure_attribution_no_current_route",
            "passed": True,
            "current_camp_dp_selector_route_rejected": True,
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "CAMP_retraining_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "DP_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def _source_closure() -> dict:
    return {
        "final_decision": {
            "status": "post_external_context_source_route_closed",
            "passed": True,
            "external_context_source_route_closed": True,
            "current_camp_dp_selector_route_rejected": True,
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "CAMP_retraining_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "DP_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def _report(**overrides: dict) -> dict:
    args = {
        "pause_gate": _pause_gate(),
        "proof_to_deployable_gap": _proof_gap(),
        "targeted_failure_attribution": _targeted_failure(),
        "post_external_context_closure": _source_closure(),
        "label": "unit",
    }
    args.update(overrides)
    return build_report(**args)


def test_post_pause_deployability_proof_objective_predeclares_source_first_contract() -> None:
    report = _report()
    decision = report["final_decision"]
    objective = report["deployability_first_objective"]

    assert decision["status"] == READY_STATUS
    assert decision["deployability_first_objective_ready"] is True
    assert decision["objective_only_reopening_allowed"] is False
    assert decision["authorized_next_work"] == "new_current_tick_source_family_proposal_only"
    assert objective["source_first"] is True
    assert objective["objective_only_sufficient"] is False
    assert objective["observed_gap"]["new_no_leak_support_missing"] is True
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    assert decision["classic_benders_claim_authorized"] is False


def test_post_pause_deployability_proof_objective_blocks_wrong_pause_source() -> None:
    pause = _pause_gate()
    pause["final_decision"]["authorized_next_work"] = "external_source_visibility_inventory_or_pause_only"

    report = _report(pause_gate=pause)

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "pause_authorizes_this_gate" in report["final_decision"]["failed_checks"]


def test_post_pause_deployability_proof_objective_blocks_if_deployable_gap_absent() -> None:
    proof = _proof_gap()
    proof["mechanism"]["deployable_gate_passes"] = True

    report = _report(proof_to_deployable_gap=proof)

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "deployable_gate_not_passing" in report["final_decision"]["failed_checks"]


def test_post_pause_deployability_proof_objective_blocks_if_support_is_not_missing() -> None:
    targeted = _targeted_failure()
    targeted["failure_summary"]["new_no_leak_support_missing_in_current_artifacts"] = False

    report = _report(targeted_failure_attribution=targeted)

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "targeted_no_new_support" in report["final_decision"]["failed_checks"]


def test_post_pause_deployability_proof_objective_blocks_action_conflict() -> None:
    targeted = _targeted_failure()
    targeted["final_decision"]["online_selector_authorized"] = True

    report = _report(targeted_failure_attribution=targeted)

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "targeted_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_post_pause_deployability_proof_objective_markdown_states_boundary() -> None:
    markdown = render_markdown(_report())

    assert "Post-Pause Deployability-First Proof Objective" in markdown
    assert "new_current_tick_source_family_proposal_only" in markdown
    assert "No DP-side classical Benders" in markdown


def test_post_pause_deployability_proof_objective_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pause_path = tmp_path / "pause.json"
    proof_path = tmp_path / "proof_gap.json"
    targeted_path = tmp_path / "targeted.json"
    closure_path = tmp_path / "closure.json"
    output_json = tmp_path / "objective.json"
    output_md = tmp_path / "objective.md"
    pause_path.write_text(json.dumps(_pause_gate()), encoding="utf-8")
    proof_path.write_text(json.dumps(_proof_gap()), encoding="utf-8")
    targeted_path.write_text(json.dumps(_targeted_failure()), encoding="utf-8")
    closure_path.write_text(json.dumps(_source_closure()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "post-pause-deployability-proof-objective",
            "--pause_gate_json",
            str(pause_path),
            "--proof_to_deployable_gap_json",
            str(proof_path),
            "--targeted_failure_attribution_json",
            str(targeted_path),
            "--post_external_context_closure_json",
            str(closure_path),
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
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "unit_cli" in output_md.read_text(encoding="utf-8")
