from __future__ import annotations

import pytest

from scripts.integrations.compare_diffusion_planner_candidate_availability import (
    compare_reports,
)


def _report(
    *,
    mean_feasible_candidates: float,
    joint0: float,
    joint005: float,
    hidden0: float = 0.0,
    hidden005: float = 0.0,
    proxy0: float = 0.0,
    proxy005: float = 0.0,
) -> dict:
    budgets = []
    for budget, joint, hidden, proxy in (
        (0.0, joint0, hidden0, proxy0),
        (0.05, joint005, hidden005, proxy005),
        (0.10, joint005, hidden005, proxy005),
        (0.25, joint005, hidden005, proxy005),
    ):
        budgets.append(
            {
                "progress_budget_m": budget,
                "outcome_joint_rate": joint,
                "outcome_weak_rate": joint,
                "hidden_outcome_weak_rate": hidden,
                "proxy_only_weak_rate": proxy,
            }
        )
    return {
        "records": {"nonfallback": 100},
        "diversity": {"mean_feasible_candidates": mean_feasible_candidates},
        "budgets": budgets,
    }


def test_candidate_availability_comparison_advances_only_after_all_gates() -> None:
    baseline = _report(
        mean_feasible_candidates=7.5,
        joint0=0.001,
        joint005=0.064,
        proxy005=0.05,
    )
    candidate = _report(
        mean_feasible_candidates=10.0,
        joint0=0.030,
        joint005=0.180,
        hidden005=0.01,
        proxy005=0.10,
    )

    report = compare_reports(
        baseline=baseline,
        candidates=[("k16_noise1p0", None, candidate)],
    )

    compared = report["candidates"][0]
    assert compared["gates"]["availability_gate_pass"] is True
    assert compared["gates"]["proxy_reliability_gate_pass"] is True
    assert compared["gates"]["candidate_pool_gate_pass"] is True
    assert compared["gates"]["latency_gate_pass"] is None
    assert compared["next_step"] == "advance_to_no_outcome_latency_smoke"


def test_candidate_availability_comparison_rejects_small_availability_gain() -> None:
    baseline = _report(mean_feasible_candidates=7.5, joint0=0.001, joint005=0.064)
    candidate = _report(mean_feasible_candidates=10.0, joint0=0.010, joint005=0.100)

    report = compare_reports(
        baseline=baseline,
        candidates=[("weak_gain", None, candidate)],
    )

    compared = report["candidates"][0]
    assert compared["gates"]["availability_gate_pass"] is False
    assert compared["next_step"] == "reject_or_redesign_candidate_generation"


def test_candidate_availability_comparison_requires_matching_budgets() -> None:
    baseline = _report(mean_feasible_candidates=7.5, joint0=0.001, joint005=0.064)
    candidate = _report(mean_feasible_candidates=10.0, joint0=0.030, joint005=0.180)
    candidate["budgets"] = candidate["budgets"][:2]

    with pytest.raises(ValueError, match="missing baseline budgets"):
        compare_reports(
            baseline=baseline,
            candidates=[("missing", None, candidate)],
        )
