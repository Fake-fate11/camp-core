from __future__ import annotations

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_statistics import (
    NONINFERIORITY_METRICS,
    REQUIRED_CONTROLLED_EVENT_FAMILIES,
    SAFETY_COMPONENTS,
    clustered_paired_summary,
    evaluate_fresh_b2_claim,
    noninferiority_decision,
    prospective_cluster_sensitivity,
)


def _claim_inputs(delta: float = -1.0):
    total = np.full(6, delta, dtype=np.float64)
    components = {
        name: np.full(6, delta / len(SAFETY_COMPONENTS), dtype=np.float64)
        for name in SAFETY_COMPONENTS
    }
    performance = {
        name: np.zeros(6, dtype=np.float64) for name in NONINFERIORITY_METRICS
    }
    margins = {name: 0.1 for name in NONINFERIORITY_METRICS}
    component_margins = {name: 0.1 for name in SAFETY_COMPONENTS}
    family_source = [
        (
            f"{family}/mapped_signal/controlled_same_tick_override"
            if family == "red_light_phase_timing"
            else f"{family}/no_signal/none"
        )
        for family in REQUIRED_CONTROLLED_EVENT_FAMILIES
    ]
    family_tier = [
        f"{family}/easy" for family in REQUIRED_CONTROLLED_EVENT_FAMILIES
    ]
    coverage = {
        "full_plan_pair_count": 100,
        "paired_eligible_count": 98,
        "overall_eligible_rate": 0.98,
        "planned_scenario_families": list(REQUIRED_CONTROLLED_EVENT_FAMILIES),
        "planned_family_source_strata": family_source,
        "planned_family_tier_strata": family_tier,
        "family_source_eligible_rates": {key: 0.95 for key in family_source},
        "family_tier_eligible_rates": {key: 0.90 for key in family_tier},
        "failure_denominator_complete": True,
        "immutability_passed": True,
        "zero_overlap_passed": True,
    }
    return total, components, performance, margins, component_margins, coverage


def test_clustered_summary_counts_clusters_not_seed_rows() -> None:
    summary = clustered_paired_summary(
        np.asarray([-2.0, 0.0, -1.0, 1.0, -3.0], dtype=np.float64),
        ["map-a", "map-a", "map-b", "map-b", "map-c"],
    )
    assert summary["observation_count"] == 5
    assert summary["independent_cluster_count"] == 3
    assert summary["cluster_measurement_counts"] == {
        "map-a": 2,
        "map-b": 2,
        "map-c": 1,
    }
    assert summary["mean_delta"] == pytest.approx((-1.0 + 0.0 - 3.0) / 3.0)
    assert summary["better_tie_worse"] == [3, 1, 1]


def test_noninferiority_uses_one_sided_upper_harm_bound() -> None:
    decision = noninferiority_decision(
        np.asarray([0.05, 0.04, 0.03, 0.02], dtype=np.float64),
        ["a", "b", "c", "d"],
        margin=0.10,
    )
    assert decision["one_sided_upper"] < 0.10
    assert decision["passed"] is True
    failed = noninferiority_decision(
        np.asarray([0.15, 0.14, 0.13, 0.12], dtype=np.float64),
        ["a", "b", "c", "d"],
        margin=0.10,
    )
    assert failed["passed"] is False


def test_prospective_sensitivity_uses_independent_cluster_count() -> None:
    result = prospective_cluster_sensitivity(
        0.2,
        25,
        target_effect=0.1,
    )
    assert result["independent_cluster_count"] == 25
    assert result["expected_two_sided_ci_half_width"] > 0.0
    assert result["normal_approximation_mde"] > 0.0
    assert result["normal_approximation_required_clusters"] >= 2
    assert result["seeds_or_ticks_counted_as_independent"] is False


def test_fresh_b2_claim_requires_total_components_ni_and_coverage() -> None:
    total, components, performance, margins, component_margins, coverage = (
        _claim_inputs()
    )
    result = evaluate_fresh_b2_claim(
        total,
        components,
        performance,
        [f"cluster-{index}" for index in range(6)],
        component_regression_margins=component_margins,
        noninferiority_margins=margins,
        coverage=coverage,
    )
    assert result["safety_improvement_claim_passed"] is True
    assert result["red_light_improvement_claim_passed"] is True
    assert result["coverage"]["passed"] is True
    assert result["real_world_or_all_map_claim_authorized"] is False

    insufficient = dict(coverage)
    insufficient["paired_eligible_count"] = 94
    insufficient["overall_eligible_rate"] = 0.94
    failed = evaluate_fresh_b2_claim(
        total,
        components,
        performance,
        [f"cluster-{index}" for index in range(6)],
        component_regression_margins=component_margins,
        noninferiority_margins=margins,
        coverage=insufficient,
    )
    assert failed["coverage"]["passed"] is False
    assert failed["safety_improvement_claim_passed"] is False
    assert failed["red_light_improvement_claim_passed"] is False


def test_fresh_b2_red_claim_requires_red_component_improvement() -> None:
    total, components, performance, margins, component_margins, coverage = (
        _claim_inputs()
    )
    components["red_light"] = np.zeros(6, dtype=np.float64)
    result = evaluate_fresh_b2_claim(
        total,
        components,
        performance,
        [f"cluster-{index}" for index in range(6)],
        component_regression_margins=component_margins,
        noninferiority_margins=margins,
        coverage=coverage,
    )
    assert result["safety_improvement_claim_passed"] is True
    assert result["red_light_improvement_claim_passed"] is False


@pytest.mark.parametrize(
    ("deltas", "clusters", "message"),
    [
        (np.asarray([1.0]), ["only"], "at least two"),
        (np.asarray([True, False]), ["a", "b"], "native numeric"),
        (np.asarray([1.0, np.nan]), ["a", "b"], "finite"),
        (np.asarray([1.0, 2.0]), ["same", "same"], "at least two"),
    ],
)
def test_clustered_summary_fails_closed(
    deltas: np.ndarray, clusters: list[str], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        clustered_paired_summary(deltas, clusters)
