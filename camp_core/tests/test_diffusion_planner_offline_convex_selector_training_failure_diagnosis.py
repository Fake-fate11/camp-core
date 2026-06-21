from __future__ import annotations

import numpy as np

from scripts.integrations.diagnose_diffusion_planner_offline_convex_selector_training_failure import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
)


def _dry_run() -> dict:
    return {
        "final_decision": {
            "status": "offline_convex_selector_training_dry_run_complete",
            "passed": True,
            "authorized_next_work": "diagnose_offline_convex_selector_training_failure_modes",
            "candidate_branch_proof_passed": False,
        }
    }


def _training_summary() -> dict:
    return {
        "converged": True,
        "final_master_gap": 0.0,
        "input_records": 10,
        "num_records_after_hard_guarded_feasibility": 8,
        "dropped_records_without_eligible_candidate": 2,
        "atom_names": [
            "planned_red_light_cost",
            "red_stopping_margin_cost",
            "jerk_early",
        ],
        "train": {"oracle_match_rate": 0.6},
        "val": {"oracle_match_rate": 0.5},
    }


def _selector_eval() -> dict:
    return {
        "logs": {"formal_seed_logs": 0},
        "selector_comparison": {
            "changed_record_rate": 0.2,
            "evaluated_minus_logged_cost_mean": 0.12,
            "run_level_evaluated_minus_logged_cost_ci": {"ci95_high": 0.3},
            "cost_delta_record_rates": {"evaluated_worse": 0.25},
            "weighted_component_delta_mean": {
                "collision": 0.08,
                "route_shortfall": -0.01,
            },
            "when_evaluated_worse": {
                "records": 3,
                "weighted_component_delta_mean": {"collision": 0.4},
                "selected_atom_delta_mean": {"planned_red_light_cost": -0.2},
            },
            "by_bucket": [
                {
                    "bucket": "traffic_light",
                    "records": 10,
                    "changed_record_rate": 0.2,
                    "evaluated_minus_logged_cost_mean": 0.12,
                    "run_level_evaluated_minus_logged_cost_ci": {"ci95_high": 0.3},
                    "weighted_component_delta_mean": {"collision": 0.08},
                    "selected_atom_delta_mean": {"planned_red_light_cost": -0.2},
                }
            ],
        },
        "evaluated_selector": {
            "by_bucket": [
                {
                    "bucket": "traffic_light",
                    "records": 10,
                    "run_level_delta_ci": {
                        "camp_minus_top1": {"ci95_high": 0.25},
                        "camp_minus_hard_guarded_oracle": {"ci95_high": 1.0},
                    },
                    "cvar90_run_level_delta_ci": {
                        "camp_minus_top1": {"ci95_high": -0.5}
                    },
                    "candidate_pool_coverage": {
                        "hard_guarded_oracle_available_rate": 1.0
                    },
                    "failure_mode_rates": {"camp_worse_than_top1": 0.2},
                }
            ]
        },
    }


def _proof() -> dict:
    return {
        "final_decision": {
            "status": "proof_incomplete",
            "safety_cost_trained_selector_candidate_branch_proof": False,
        },
        "gates": {
            "safety_cost_trained_selector_vs_top1": {
                "passed": False,
                "overall_ci_high": -0.1,
                "bucket_failures": {"traffic_light": 0.25},
            },
            "safety_cost_trained_selector_gap_closed": {
                "passed": False,
                "overall_ci_high": 0.8,
                "bucket_failures": {"traffic_light": 1.0},
            },
        },
    }


def test_failure_diagnosis_rejects_failed_selector_and_authorizes_plan_only() -> None:
    report = build_report(
        dry_run=_dry_run(),
        training_summary=_training_summary(),
        selector_eval=_selector_eval(),
        proof=_proof(),
        static_weights=np.asarray([0.7, 0.2, 0.1]),
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["dry_run_selector_rejected"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["training_execution_authorized"] is False
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert report["selector_regression"]["regression_components"][0]["name"] == "collision"
    assert report["training_summary"]["top_weights"][0]["atom"] == "planned_red_light_cost"
    assert any(
        item["name"] == "critical_bucket_top1_gate_failure"
        for item in report["failure_hypotheses"]
    )
    assert "recompute_accept_reject_and_next_authorized_work" in report[
        "self_iteration_contract"
    ]["loop"]


def test_failure_diagnosis_blocks_when_source_is_not_failed_dry_run() -> None:
    dry_run = _dry_run()
    dry_run["final_decision"]["candidate_branch_proof_passed"] = True

    report = build_report(
        dry_run=dry_run,
        training_summary=_training_summary(),
        selector_eval=_selector_eval(),
        proof=_proof(),
        static_weights=np.asarray([0.7, 0.2, 0.1]),
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    assert any(not check["passed"] for check in report["source_checks"])
