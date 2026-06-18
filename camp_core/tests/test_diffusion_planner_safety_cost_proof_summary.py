from __future__ import annotations

from scripts.integrations.summarize_diffusion_planner_camp_safety_cost_proof import (
    DEFAULT_REQUIRED_BUCKETS,
    build_report,
    render_markdown,
)


def _ci(mean: float, high: float) -> dict[str, float]:
    return {"mean": mean, "ci95_low": mean - 0.1, "ci95_high": high}


def _hard_rates(camp_min: float = 0.8, hard_min: float = 1.0) -> dict[str, float]:
    return {
        "camp_collision_vs_top1": 1.0,
        "camp_near_miss_vs_top1": 0.9,
        "camp_lane_vs_top1": camp_min,
        "camp_realized_red_light_vs_top1": 0.95,
        "oracle_collision_vs_top1": 1.0,
        "oracle_near_miss_vs_top1": 0.8,
        "oracle_lane_vs_top1": 0.7,
        "oracle_realized_red_light_vs_top1": 0.6,
        "hard_guarded_oracle_collision_vs_top1": 1.0,
        "hard_guarded_oracle_near_miss_vs_top1": hard_min,
        "hard_guarded_oracle_lane_vs_top1": 1.0,
        "hard_guarded_oracle_realized_red_light_vs_top1": 1.0,
    }


def _oracle_entry(
    *,
    camp_high: float,
    hard_high: float = -0.2,
    gap_high: float = 0.3,
    cvar_high: float = -0.15,
    records: int = 10,
    logs: int = 2,
) -> dict[str, object]:
    return {
        "records": records,
        "logs": logs,
        "cost_mean": {
            "top1": 2.0,
            "camp": 1.0,
            "hard_guarded_oracle": 0.5,
        },
        "record_rates": {
            "camp_beats_top1": 0.7,
            "camp_matches_top1": 0.2,
            "camp_matches_hard_guarded_oracle": 0.4,
            "hard_guarded_oracle_beats_top1": 0.9,
            "hard_guarded_oracle_available": 1.0,
        },
        "run_level_delta_ci": {
            "camp_minus_top1": _ci(-0.1, camp_high),
            "hard_guarded_oracle_minus_top1": _ci(-0.3, hard_high),
            "camp_minus_hard_guarded_oracle": _ci(0.2, gap_high),
        },
        "run_level_cvar90_delta": {
            "camp_minus_top1": _ci(-0.12, cvar_high),
            "hard_guarded_oracle_minus_top1": _ci(-0.32, -0.25),
            "camp_minus_hard_guarded_oracle": _ci(0.22, 0.35),
        },
        "failure_mode_rates": {},
        "hard_component_nonworse_rate": _hard_rates(),
    }


def _coverage(available: float = 0.85) -> dict[str, float]:
    return {
        "hard_guarded_oracle_available_rate": available,
        "base_feasible_rate": 0.9,
        "fallback_all_infeasible_rate": 0.1,
        "mean_candidate_count": 8.0,
        "mean_eligible_candidate_count": 6.0,
        "top1_eligible_rate": 0.95,
        "camp_eligible_rate": 0.9,
    }


def _opportunity_diagnostics() -> dict[str, object]:
    return {
        "candidate_pool_coverage": _coverage(available=0.85),
        "failure_mode_rates": {
            "hard_guarded_oracle_unavailable": 0.15,
            "camp_not_hard_guarded_oracle_when_available": 0.6,
        },
        "by_bucket": [
            {
                "bucket": bucket,
                "candidate_pool_coverage": _coverage(available=0.75),
                "failure_mode_rates": {
                    "hard_guarded_oracle_unavailable": 0.25,
                    "camp_not_hard_guarded_oracle_when_available": 0.5,
                },
            }
            for bucket in ("overall", *DEFAULT_REQUIRED_BUCKETS)
        ],
    }


def _oracle_report(*, traffic_camp_high: float) -> dict[str, object]:
    by_bucket = [{"bucket": "overall", **_oracle_entry(camp_high=-0.1)}]
    for bucket in DEFAULT_REQUIRED_BUCKETS:
        high = traffic_camp_high if bucket == "traffic_light" else -0.05
        by_bucket.append({"bucket": bucket, **_oracle_entry(camp_high=high)})
    return {
        "analysis": {"name": "oracle"},
        "logs": {"total": 8, "formal_seed_logs": 0},
        "records": {"total": 80},
        "coverage_gaps": {"missing_required_buckets": []},
        "opportunity_gate": {"passed": True},
        "opportunity_diagnostics": _opportunity_diagnostics(),
        "overall": _oracle_entry(camp_high=-0.1),
        "by_bucket": by_bucket,
    }


def _selector_eval_report() -> dict[str, object]:
    evaluated_by_bucket = [{"bucket": "overall", **_oracle_entry(camp_high=-0.2)}]
    logged_by_bucket = [{"bucket": "overall", **_oracle_entry(camp_high=-0.1)}]
    for bucket in DEFAULT_REQUIRED_BUCKETS:
        evaluated_by_bucket.append({"bucket": bucket, **_oracle_entry(camp_high=-0.03)})
        logged_by_bucket.append({"bucket": bucket, **_oracle_entry(camp_high=-0.01)})
    return {
        "analysis": {
            "name": "selector_eval",
            "selector_name": "safety_cost_v1",
        },
        "logs": {"total": 8, "formal_seed_logs": 0},
        "records": {"total": 80},
        "coverage_gaps": {"missing_required_buckets": []},
        "opportunity_gate": {"passed": True},
        "evaluated_selector": {
            "overall": _oracle_entry(camp_high=-0.2, gap_high=0.4),
            "by_bucket": evaluated_by_bucket,
        },
        "logged_selector": {
            "overall": _oracle_entry(camp_high=-0.1, gap_high=0.3),
            "by_bucket": logged_by_bucket,
        },
        "selector_comparison": {
            "changed_record_rate": 0.25,
            "evaluated_minus_logged_cost_mean": 0.1,
            "run_level_evaluated_minus_logged_cost_ci": {
                "mean": 0.1,
                "ci95_high": 0.2,
            },
        },
    }


def test_safety_cost_proof_summary_separates_current_and_trained_gates() -> None:
    report = build_report(
        oracle_report=_oracle_report(traffic_camp_high=0.04),
        selector_eval_report=_selector_eval_report(),
    )

    assert report["gates"]["candidate_pool_opportunity"]["passed"] is True
    assert report["gates"]["current_camp_vs_top1"]["passed"] is False
    assert report["gates"]["current_camp_vs_top1"]["bucket_failures"] == {
        "traffic_light": 0.04
    }
    assert (
        report["gates"]["safety_cost_trained_selector_vs_top1"]["passed"] is True
    )
    assert report["gates"]["safety_cost_trained_selector_gap_closed"]["passed"] is False
    assert (
        report["final_decision"]["status"]
        == "candidate_branch_proof_passes_for_safety_cost_trained_selector"
    )
    assert report["final_decision"]["closed_loop_deployment_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert (
        report["current_camp"]["overall"]["cvar90_camp_minus_top1"]["ci95_high"]
        == -0.15
    )
    assert (
        report["current_camp"]["overall"]["candidate_pool_coverage"][
            "hard_guarded_oracle_available_rate"
        ]
        == 0.85
    )
    assert (
        report["current_camp"]["by_bucket"]["traffic_light"][
            "candidate_pool_coverage"
        ]["hard_guarded_oracle_available_rate"]
        == 0.75
    )

    markdown = render_markdown(report)
    assert "CAMP vs DP Top-1 SafetyCost Proof Summary" in markdown
    assert "traffic_light=0.040000" in markdown
    assert "CAMP-Top1 CVaR90 CI high" in markdown
    assert "HardOracle available" in markdown
    assert "CAMP hard-component nonworse min" in markdown
    assert "0.750000" in markdown
    assert "not classical Benders decomposition" in markdown
