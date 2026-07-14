from copy import deepcopy

import pytest

from camp_core.evaluation.diffusion_planner_v22_statistics import (
    analyze_retained_pairs,
)


GUARDS = {
    "artifact_sha_verified": True,
    "candidate_immutability_verified": True,
    "candidate0_default_identity_verified": True,
    "independent_review_passed": True,
    "split_zero_overlap_verified": True,
    "arm_symmetry_verified": True,
    "feature_identity_denylist_verified": True,
}


def _row(
    index: int,
    delta: float,
    *,
    collision_delta: float = 0.0,
    red_delta: float = 0.0,
    offroad_delta: float = 0.0,
    wrong_way_delta: float = 0.0,
    stress: bool = False,
    all_k_high_risk: bool = False,
) -> dict:
    dp_components = {
        "collision_any": 0.0,
        "near_miss_noncollision_rate": 0.0,
        "offroad_rate": 0.0,
        "red_light_violation_any": 0.0,
        "speed_limit_violation_rate": 0.2,
        "wrong_way_rate": 0.0,
    }
    component_delta = {
        "collision_any": collision_delta,
        "near_miss_noncollision_rate": delta,
        "offroad_rate": offroad_delta,
        "red_light_violation_any": red_delta,
        "speed_limit_violation_rate": 0.0,
        "wrong_way_rate": wrong_way_delta,
    }
    camp_components = {
        name: value + component_delta[name]
        for name, value in dp_components.items()
    }
    speed = {
        "sensitivity": {
            key: {"event_rate": 0.2}
            for key in ("0.0", "0.05", "0.1", "0.2")
        },
        "continuous": {
            "magnitude_duration_m": 1.0,
            "excess_duration_s": 0.5,
        },
    }
    map_index = index % 2
    route_index = index // 2
    return {
        "pair_key": f"holdout/route_{route_index}/seed_{30000 + index}",
        "split": "holdout",
        "logical_map_sha256": f"map_{map_index}",
        "group_sha256": f"group_{map_index}_{route_index // 2}",
        "route_identity_sha256": f"route_{route_index}",
        "seed": 30000 + index,
        "route_retained": True,
        "included_in_denominator": True,
        "paired_complete": True,
        "hard_invalid": False,
        "execution_failure": False,
        "all_k_high_risk": all_k_high_risk,
        "source_stratum": {
            "branch_intersection": stress,
            "tight_corridor": False,
            "traffic_light": False,
            "short_progress_opportunity": False,
        },
        "paired_delta": {
            "dp": 2.0,
            "camp": 2.0 + delta,
            "delta": delta,
            "result": "better" if delta < 0 else "worse" if delta > 0 else "tie",
        },
        "component_delta": component_delta,
        "dp_safety": {
            "components": dp_components,
            "speed_protocol": speed,
        },
        "camp_safety": {
            "components": camp_components,
            "speed_protocol": speed,
        },
        "dp_secondary": {
            "route_progress_m": 10.0,
            "route_completion_rate": 0.5,
            "stopped_fraction": 0.1,
            "mean_abs_jerk_mps3": 1.0,
        },
        "camp_secondary": {
            "route_progress_m": 11.0,
            "route_completion_rate": 0.55,
            "stopped_fraction": 0.05,
            "mean_abs_jerk_mps3": 0.8,
        },
        "dp_latency": {"total_planning": {"mean": 10.0}},
        "camp_latency": {
            "total_planning": {"mean": 15.0},
            "selector": {"mean": 0.1},
        },
    }


def _analyze(rows: list[dict], **kwargs) -> dict:
    return analyze_retained_pairs(
        [row["pair_key"] for row in rows],
        rows,
        bootstrap_resamples=200,
        bootstrap_seed=12345,
        evidence_guards=GUARDS,
        claim_evaluation=True,
        **kwargs,
    )


def test_statistics_are_deterministic_and_report_all_strata() -> None:
    rows = [
        _row(0, -1.0),
        _row(1, -0.5, stress=True),
        _row(2, 0.0, all_k_high_risk=True),
        _row(3, -0.25, stress=True),
    ]

    first = _analyze(rows)
    second = _analyze(rows)

    assert first == second
    assert first["coverage"] == {
        "planned_pair_count": 4,
        "retained_pair_count": 4,
        "paired_complete_count": 4,
        "hard_invalid_pair_count": 0,
        "execution_failure_pair_count": 0,
        "route_coverage": 1.0,
        "paired_complete_rate": 1.0,
        "hard_invalid_rate": 0.0,
    }
    assert first["strata"]["overall"]["better_tie_worse"] == {
        "better": 3,
        "tie": 1,
        "worse": 0,
    }
    assert first["strata"]["normal"]["pair_count"] == 1
    assert first["strata"]["stress"]["pair_count"] == 3
    assert first["strata"]["all_k_high_risk"]["pair_count"] == 1
    assert set(first["components"]) == set(rows[0]["component_delta"])
    assert first["secondary_mean_delta"]["route_progress_m"] == pytest.approx(1.0)
    assert first["latency_mean_ms"]["camp"]["selector"] == pytest.approx(0.1)


def test_missing_or_deleted_planned_pair_fails_closed() -> None:
    rows = [_row(0, -1.0), _row(1, -1.0)]
    planned = [row["pair_key"] for row in rows] + ["holdout/missing/seed_1"]

    with pytest.raises(ValueError, match="planned and observed pair keys"):
        analyze_retained_pairs(planned, rows)

    rows[0]["route_retained"] = False
    with pytest.raises(ValueError, match="retained in the denominator"):
        analyze_retained_pairs([row["pair_key"] for row in rows], rows)


def test_retained_hard_invalid_is_counted_but_not_imputed() -> None:
    rows = [_row(0, -1.0), _row(1, -1.0)]
    failed = rows[1]
    failed.update(
        {
            "paired_complete": False,
            "hard_invalid": True,
            "failure_class": "source_failure",
        }
    )
    for key in (
        "paired_delta",
        "component_delta",
        "dp_safety",
        "camp_safety",
        "dp_secondary",
        "camp_secondary",
        "dp_latency",
        "camp_latency",
    ):
        failed.pop(key)

    result = _analyze(rows)

    assert result["coverage"]["retained_pair_count"] == 2
    assert result["coverage"]["paired_complete_count"] == 1
    assert result["coverage"]["hard_invalid_pair_count"] == 1
    assert result["strata"]["overall"]["pair_count"] == 1


def test_claim_passes_only_when_every_preregistered_gate_passes() -> None:
    rows = [_row(index, -1.0) for index in range(8)]
    passed = _analyze(rows)

    assert passed["claim_decision"]["decision"] == "claim"
    assert all(passed["claim_decision"]["gates"].values())

    collision = deepcopy(rows)
    collision[0] = _row(0, -1.0, collision_delta=1.0)
    assert _analyze(collision)["claim_decision"]["decision"] == "honest_no_claim"

    bad_guard = dict(GUARDS, independent_review_passed=False)
    guarded = analyze_retained_pairs(
        [row["pair_key"] for row in rows],
        rows,
        bootstrap_resamples=200,
        bootstrap_seed=12345,
        evidence_guards=bad_guard,
        claim_evaluation=True,
    )
    assert guarded["claim_decision"]["decision"] == "honest_no_claim"
    assert guarded["claim_decision"]["gates"]["evidence_guards"] is False


def test_nonnegative_mean_or_ci_upper_produces_honest_no_claim() -> None:
    rows = [_row(0, -1.0), _row(1, 1.0), _row(2, 0.5), _row(3, 0.5)]

    result = _analyze(rows)

    assert result["claim_decision"]["decision"] == "honest_no_claim"
    assert result["claim_decision"]["gates"]["overall_mean_delta"] is False
    assert result["claim_decision"]["gates"]["overall_ci95_upper"] is False
