from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_no_leak_atom_or_proof_objective_redesign import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _diagnosis(
    *,
    status: str = "offline_convex_objective_label_sensitivity_results_diagnosed",
    credible: list[str] | None = None,
    persistent_failed_checks: list[str] | None = None,
) -> dict[str, object]:
    credible = credible or []
    persistent_failed_checks = persistent_failed_checks or [
        "component_nonpositive_collision",
        "component_nonpositive_near_miss",
        "logged_selector_nonworse_ci_high",
        "oracle_gap_gate_passed",
        "top1_bucket_gate_passed",
    ]
    passed = status == "offline_convex_objective_label_sensitivity_results_diagnosed"
    return {
        "final_decision": {
            "status": status,
            "passed": passed,
            "sensitivity_route_rejected": not credible if passed else None,
            "credible_direction_candidates": credible,
            "authorized_next_work": (
                "predeclare_no_leak_atom_or_proof_objective_redesign_plan_only"
                if passed and not credible
                else None
            ),
            "training_execution_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "route_diagnosis": {
            "sensitivity_route_rejected": not credible if passed else None,
            "persistent_failed_checks": persistent_failed_checks,
        },
        "comparison_summary": {
            "credible_direction_candidates": credible,
            "best_by_logged_nonworse_ci_high": {
                "name": "safety_guard_floor",
                "value": 0.17207710056260256,
            },
            "best_by_collision_delta": {
                "name": "tail_alpha_0p95",
                "value": 0.0787037037037037,
            },
            "best_by_near_miss_delta": {
                "name": "tail_alpha_0p95",
                "value": 0.006481481481481481,
            },
            "top1_failure_counts": {
                "tail_alpha_0p95": 3,
                "tail_alpha_0p95_l2_1e3": 3,
                "safety_guard_floor": 3,
                "balanced_comfort_progress_floor": 3,
            },
            "oracle_gap_failure_counts": {
                "tail_alpha_0p95": 7,
                "tail_alpha_0p95_l2_1e3": 7,
                "safety_guard_floor": 7,
                "balanced_comfort_progress_floor": 7,
            },
        },
    }


def test_redesign_plan_authorizes_support_inventory_only() -> None:
    report = build_report(diagnosis=_diagnosis(), label="unit")

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["recommended_first_action"] == "support_inventory_refresh"
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False

    rejected = {route["name"] for route in report["rejected_routes"]}
    assert "alpha_l2_simplex_floor_sensitivity" in rejected
    assert "future_outcome_online_feature" in rejected
    assert "classic_benders_claim_for_finite_selector" in rejected

    first_option = report["redesign_options"][0]
    assert first_option["name"] == "support_inventory_refresh"
    assert first_option["recommended_first"] is True
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    assert "nonnegative" in " ".join(
        report["atom_admissibility_contract"]["required_properties"]
    )

    markdown = render_markdown(report)
    assert "No-Leak Atom or Proof-Objective Redesign Plan" in markdown
    assert "not a classical Benders decomposition" in markdown


def test_redesign_plan_blocks_if_source_has_credible_sensitivity_direction() -> None:
    report = build_report(
        diagnosis=_diagnosis(credible=["tail_alpha_0p95"]),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert decision["authorized_next_work"] is None
    assert any(
        check["name"] == "no_credible_direction_candidates"
        and check["passed"] is False
        for check in report["source_checks"]
    )


def test_redesign_plan_blocks_when_required_failure_evidence_is_missing() -> None:
    report = build_report(
        diagnosis=_diagnosis(
            persistent_failed_checks=[
                "logged_selector_nonworse_ci_high",
                "oracle_gap_gate_passed",
                "top1_bucket_gate_passed",
            ]
        ),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert decision["authorized_next_work"] is None
    missing_check = next(
        check
        for check in report["plan_checks"]
        if check["name"] == "required_persistent_failures_present"
    )
    assert missing_check["passed"] is False
    assert missing_check["missing"] == [
        "component_nonpositive_collision",
        "component_nonpositive_near_miss",
    ]


def test_redesign_plan_cli_writes_json_and_markdown(
    tmp_path: Path,
    monkeypatch,
) -> None:
    diagnosis_path = tmp_path / "diagnosis.json"
    diagnosis_path.write_text(json.dumps(_diagnosis()), encoding="utf-8")
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--diagnosis_json",
            str(diagnosis_path),
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
    assert "No-Leak Atom" in output_md.read_text(encoding="utf-8")
