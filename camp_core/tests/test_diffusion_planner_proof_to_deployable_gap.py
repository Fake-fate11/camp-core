from __future__ import annotations

from scripts.integrations.summarize_diffusion_planner_proof_to_deployable_gap import (
    build_report,
    render_markdown,
)


def _ci(high: float) -> dict[str, float]:
    return {"mean": high - 0.1, "ci95_low": high - 0.2, "ci95_high": high}


def _proof_metrics(*, camp_high: float) -> dict[str, object]:
    return {
        "records": 100,
        "logs": 5,
        "camp_minus_top1": _ci(camp_high),
        "cvar90_camp_minus_top1": _ci(camp_high - 0.5),
        "hard_guarded_oracle_minus_top1": _ci(-0.3),
        "camp_minus_hard_guarded_oracle": _ci(0.8),
        "candidate_pool_coverage": {
            "hard_guarded_oracle_available_rate": 0.9,
        },
        "record_rates": {
            "hard_guarded_oracle_available": 0.9,
            "hard_guarded_oracle_beats_top1": 0.8,
        },
        "hard_component_nonworse_rate": {
            "camp_collision_vs_top1": 1.0,
            "camp_near_miss_vs_top1": 0.99,
            "camp_lane_vs_top1": 0.97,
            "camp_realized_red_light_vs_top1": 1.0,
        },
    }


def _proof_report() -> dict[str, object]:
    return {
        "gates": {
            "candidate_pool_opportunity": {
                "passed": True,
                "overall_ci_high": -0.4,
                "bucket_failures": {},
            },
            "current_camp_vs_top1": {
                "passed": False,
                "overall_ci_high": 0.1,
                "bucket_failures": {"red_light_turn": 0.1},
            },
            "safety_cost_trained_selector_vs_top1": {
                "passed": True,
                "overall_ci_high": -0.2,
                "bucket_failures": {},
            },
            "safety_cost_trained_selector_gap_closed": {
                "passed": False,
                "overall_ci_high": 1.0,
                "bucket_failures": {"lane_change_or_merge": 1.0},
            },
        },
        "final_decision": {
            "status": "candidate_branch_proof_passes_for_safety_cost_trained_selector",
            "current_camp_complete_proof": False,
            "safety_cost_trained_selector_candidate_branch_proof": True,
            "hard_guarded_oracle_gap_closed": False,
        },
        "current_camp": {"overall": _proof_metrics(camp_high=0.1)},
        "safety_cost_trained_selector": {
            "evaluated": {"overall": _proof_metrics(camp_high=-0.2)}
        },
    }


def _worst_lane_row(*, safety: float, lane: float, latency: float) -> dict[str, object]:
    return {
        "route_name": "nishishinjuku_lane_change",
        "max_npcs": 8,
        "traffic_lights": False,
        "benchmark": {
            "delta_static_minus_top1": {
                "safety_cost_v1": safety,
                "route_completion_rate": -0.01,
                "near_miss_rate": 0.02,
                "lane_violation_rate": lane,
            },
            "static": {"p95_selection_latency_ms": latency},
        },
        "selection": {
            "fallback_rate": 0.51,
            "candidate_feasible_rate": 0.46,
            "selected_non_top1_rate": 0.9,
        },
        "top_infeasibility_reasons": [{"reason": "dp_lane_crossing", "count": 10}],
    }


def _deployable_report(*, safety: float = 0.74, lane: float = 0.03) -> dict[str, object]:
    return {
        "analysis": {"name": "deployable_failure"},
        "records": {"static_runs": 12, "selection_records": 2400},
        "overall": {
            "gate": {
                "hard_gate_passed": False,
                "safety_cost_claim_passed": False,
                "claim_rule": "unit deployable gate",
            },
            "mean_static_fallback_rate": 0.18,
            "mean_static_candidate_feasible_rate": 0.74,
            "mean_static_selected_non_top1_rate": 0.88,
            "benchmark_delta_means": {
                "safety_cost_v1": 0.08,
                "route_completion_rate": -0.02,
                "near_miss_rate": -0.01,
                "lane_violation_rate": 0.01,
                "mean_jerk_magnitude_mps3": 1.0,
            },
            "feature_deltas_selected_minus_top1": {
                "dp_prior_deviation": {
                    "changed_records": 100,
                    "mean_of_run_mean_delta": 0.5,
                    "mean_selected_better_or_equal_rate": 0.0,
                }
            },
            "global_infeasibility_reasons": [{"reason": "dp_lane_crossing", "count": 10}],
        },
        "worst_runs": [
            _worst_lane_row(safety=safety, lane=lane, latency=102.0),
        ],
    }


def test_proof_to_deployable_gap_identifies_transfer_failure() -> None:
    report = build_report(
        proof_report=_proof_report(),
        deployable_failure_report=_deployable_report(),
        top1_fallback_report=_deployable_report(safety=0.18, lane=0.02),
    )

    mechanism = report["mechanism"]
    assert mechanism["candidate_support_exists"] is True
    assert mechanism["candidate_branch_selector_passes"] is True
    assert mechanism["deployable_gate_passes"] is False
    assert (
        mechanism["root_cause_class"]
        == "score_schema_feasibility_fallback_deployability_gap"
    )
    assert "high_all_infeasible_fallback" in mechanism["primary_blockers"]
    assert "low_candidate_feasible_rate" in mechanism["primary_blockers"]
    assert "top1_fallback_insufficient" in mechanism["primary_blockers"]
    assert mechanism["top1_fallback_effect"]["safety_delta_reduction"] == -0.56
    assert report["final_decision"]["camp_retraining_authorized"] is False

    markdown = render_markdown(report)
    assert "CAMP Proof-to-Deployable Gap Summary" in markdown
    assert "candidate-branch proof" in markdown
    assert "not classical Benders decomposition" in markdown
