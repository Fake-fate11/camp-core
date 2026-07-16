"""Outcome-blind-frozen retained-pair statistics for v24."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any

import numpy as np


EPS = 1e-12
BOOTSTRAP_RESAMPLES = 5_000
BOOTSTRAP_SEED = 24_047
SPEED_TOLERANCES = ("0.0", "0.05", "0.1", "0.2")
PRIMARY_CLUSTER_HIERARCHY = (
    "corridor_group_sha256",
    "route_identity_sha256",
    "seed",
)
LATENCY_STAGES = {
    "dp": {
        "default": "default_inference",
        "tracker": "tracker",
        "total": "total_planning",
    },
    "camp": {
        "default": "default_inference",
        "k8_candidate": "candidate_inference",
        "atom": "atom_materialization",
        "selector": "selector",
        "tracker": "tracker",
        "total": "total_planning",
    },
}
REGRESSION_EVENT_COMPONENTS = (
    "collision_any",
    "offroad_rate",
    "red_light_violation_any",
    "wrong_way_rate",
)
REQUIRED_EVIDENCE_GUARDS = (
    "artifact_sha_verified",
    "per_arm_candidate_immutability_verified",
    "per_arm_candidate0_default_identity_verified",
    "t0_cross_arm_input_and_candidate_identity_verified",
    "independent_review_passed",
    "split_zero_overlap_verified",
    "holdout_once_verified",
    "arm_order_balance_verified",
    "feature_identity_denylist_verified",
)


def analyze_retained_pairs(
    planned_pair_keys: Sequence[str],
    rows: Sequence[Mapping[str, Any]],
    *,
    bootstrap_resamples: int = BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = BOOTSTRAP_SEED,
    evidence_guards: Mapping[str, bool] | None = None,
    claim_evaluation: bool = False,
) -> dict[str, Any]:
    """Analyze exactly one frozen pair population without failure imputation."""
    planned = [str(value) for value in planned_pair_keys]
    observed = [str(row.get("pair_key")) for row in rows]
    if len(set(planned)) != len(planned) or len(set(observed)) != len(observed):
        raise ValueError("planned and observed pair keys must be unique")
    if set(planned) != set(observed):
        raise ValueError("planned and observed pair keys must match exactly")
    if any(
        row.get("route_retained") is not True
        or row.get("included_in_denominator") is not True
        or row.get("replacement_used") is not False
        for row in rows
    ):
        raise ValueError("every planned pair must be retained without replacement")
    if claim_evaluation:
        map_families = {str(row["map_family_id"]) for row in rows}
        corridors = {str(row["corridor_group_sha256"]) for row in rows}
        if len(map_families) != 1 or len(corridors) != 3:
            raise ValueError("v24 main claim evaluation requires one family/three corridors")

    complete = [row for row in rows if row.get("paired_complete") is True]
    for row in complete:
        _safety(row, "dp")
        _safety(row, "camp")
    coverage = _coverage(rows, len(planned))
    strata_rows = {
        "overall": complete,
        "all_k_high_risk": [
            row for row in complete if row.get("all_k_high_risk") is True
        ],
    }
    strata = {
        name: _paired_summary(
            subset,
            _safety_delta,
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        )
        for name, subset in strata_rows.items()
    }
    component_names = sorted(
        {
            name
            for row in complete
            for name in _mapping(_safety(row, "dp"), "components")
        }
    )
    components = {
        name: _paired_summary(
            complete,
            lambda row, component=name: _component_delta(row, component),
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        )
        for name in component_names
    }
    event_regressions = {
        name: _additional_event_pairs(complete, name)
        for name in REGRESSION_EVENT_COMPONENTS
    }
    guards = {
        name: bool((evidence_guards or {}).get(name, False))
        for name in REQUIRED_EVIDENCE_GUARDS
    }
    decision = _claim_decision(
        claim_evaluation=claim_evaluation,
        coverage=coverage,
        overall=strata["overall"],
        event_regressions=event_regressions,
        evidence_guards=guards,
    )
    return {
        "schema_version": "camp_dp_v24_retained_pair_statistics_v1",
        "bootstrap_contract": {
            "primary_hierarchy": list(PRIMARY_CLUSTER_HIERARCHY),
            "map_family_cluster_level_authorized": False,
            "resamples": int(bootstrap_resamples),
            "seed": int(bootstrap_seed),
        },
        "coverage": coverage,
        "failure_accounting": _failure_accounting(rows),
        "strata": strata,
        "components": components,
        "additional_event_pairs": event_regressions,
        "speed_sensitivity_event_rate_delta": _speed_sensitivity(
            complete,
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        ),
        "secondary_mean_delta": _secondary_mean_deltas(complete),
        "candidate_selection": _candidate_selection(complete),
        "latency": _latency_distributions(complete),
        "latency_comparison_authorized": False,
        "latency_reporting_role": "descriptive_instrumented_only",
        "evidence_guards": guards,
        "claim_decision": decision,
    }


def _mapping(container: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = container.get(name)
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _finite(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _safety(row: Mapping[str, Any], arm: str) -> Mapping[str, Any]:
    safety = _mapping(row, f"{arm}_safety")
    if safety.get("schema_version") != "safety_cost_native_v22":
        raise ValueError("v24 paired row safety schema mismatch")
    _finite(safety.get("safety_cost"), f"{arm} safety cost")
    _mapping(safety, "components")
    return safety


def _safety_delta(row: Mapping[str, Any]) -> float:
    return _finite(_safety(row, "camp")["safety_cost"], "camp safety") - _finite(
        _safety(row, "dp")["safety_cost"], "dp safety"
    )


def _component_delta(row: Mapping[str, Any], component: str) -> float:
    return _finite(
        _mapping(_safety(row, "camp"), "components")[component], component
    ) - _finite(_mapping(_safety(row, "dp"), "components")[component], component)


def _coverage(rows: Sequence[Mapping[str, Any]], planned_count: int) -> dict[str, Any]:
    retained = len(rows)
    complete = sum(row.get("paired_complete") is True for row in rows)
    source_invalid = sum(row.get("source_invalid") is True for row in rows)
    execution_invalid = sum(row.get("execution_failure") is True for row in rows)
    denominator = retained or 1
    return {
        "planned_pair_count": int(planned_count),
        "retained_pair_count": retained,
        "paired_complete_count": complete,
        "source_invalid_pair_count": source_invalid,
        "execution_invalid_pair_count": execution_invalid,
        "retention_rate": retained / (planned_count or 1),
        "paired_complete_rate": complete / denominator,
        "source_invalid_rate": source_invalid / denominator,
        "execution_invalid_rate": execution_invalid / denominator,
    }


def _failure_accounting(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "dp_status": dict(Counter(str(row.get("dp_status")) for row in rows)),
        "camp_status": dict(Counter(str(row.get("camp_status")) for row in rows)),
        "failure_class": dict(
            Counter(str(row.get("failure_class")) for row in rows)
        ),
        "failed_pairs_dropped": False,
        "replacement_or_resampling_used": False,
    }


def _paired_summary(
    rows: Sequence[Mapping[str, Any]],
    getter: Callable[[Mapping[str, Any]], Any],
    *,
    bootstrap_resamples: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    values = np.asarray(
        [_finite(getter(row), "paired statistic") for row in rows],
        dtype=np.float64,
    )
    if values.size == 0:
        return {
            "pair_count": 0,
            "mean": None,
            "median": None,
            "ci95_low": None,
            "ci95_high": None,
            "better_tie_worse": {"better": 0, "tie": 0, "worse": 0},
        }
    labels = Counter(
        "better" if value < -EPS else "worse" if value > EPS else "tie"
        for value in values
    )
    ci_low, ci_high = _corridor_route_bootstrap_ci(
        rows,
        getter,
        resamples=bootstrap_resamples,
        seed=bootstrap_seed,
    )
    return {
        "pair_count": int(values.size),
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "ci95_low": ci_low,
        "ci95_high": ci_high,
        "better_tie_worse": {
            "better": labels["better"],
            "tie": labels["tie"],
            "worse": labels["worse"],
        },
    }


def _corridor_route_bootstrap_ci(
    rows: Sequence[Mapping[str, Any]],
    getter: Callable[[Mapping[str, Any]], Any],
    *,
    resamples: int,
    seed: int,
) -> tuple[float | None, float | None]:
    if not rows or resamples <= 0:
        return None, None
    corridors = sorted({str(row["corridor_group_sha256"]) for row in rows})
    rng = np.random.default_rng(seed)
    means = np.empty(int(resamples), dtype=np.float64)
    for index in range(int(resamples)):
        sampled: list[float] = []
        for corridor in rng.choice(corridors, size=len(corridors), replace=True):
            corridor_rows = [
                row
                for row in rows
                if str(row["corridor_group_sha256"]) == corridor
            ]
            routes = sorted(
                {str(row["route_identity_sha256"]) for row in corridor_rows}
            )
            for route in rng.choice(routes, size=len(routes), replace=True):
                route_rows = [
                    row
                    for row in corridor_rows
                    if str(row["route_identity_sha256"]) == route
                ]
                seeds = sorted({int(row["seed"]) for row in route_rows})
                for scenario_seed in rng.choice(seeds, size=len(seeds), replace=True):
                    matching = [
                        row
                        for row in route_rows
                        if int(row["seed"]) == int(scenario_seed)
                    ]
                    if len(matching) != 1:
                        raise ValueError("route/seed pair must be unique")
                    sampled.append(_finite(getter(matching[0]), "bootstrap value"))
        means[index] = float(np.mean(sampled))
    return (
        float(np.percentile(means, 2.5)),
        float(np.percentile(means, 97.5)),
    )


def _speed_sensitivity(
    rows: Sequence[Mapping[str, Any]],
    *,
    bootstrap_resamples: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for tolerance in SPEED_TOLERANCES:
        result[tolerance] = _paired_summary(
            rows,
            lambda row, key=tolerance: _speed_event_rate(row, "camp", key)
            - _speed_event_rate(row, "dp", key),
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        )
    for field in ("magnitude_duration_m", "excess_duration_s"):
        result[f"continuous_{field}_delta"] = _paired_summary(
            rows,
            lambda row, name=field: _continuous_speed(row, "camp", name)
            - _continuous_speed(row, "dp", name),
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        )
    return result


def _speed_event_rate(row: Mapping[str, Any], arm: str, tolerance: str) -> float:
    protocol = _mapping(_safety(row, arm), "speed_protocol")
    sensitivity = _mapping(protocol, "sensitivity")
    return _finite(_mapping(sensitivity, tolerance)["event_rate"], "speed rate")


def _continuous_speed(row: Mapping[str, Any], arm: str, field: str) -> float:
    protocol = _mapping(_safety(row, arm), "speed_protocol")
    return _finite(_mapping(protocol, "continuous")[field], "continuous speed")


def _secondary_mean_deltas(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    if not rows:
        return {}
    fields: set[str] | None = None
    for row in rows:
        dp = _mapping(row, "dp_secondary")
        camp = _mapping(row, "camp_secondary")
        common = {
            name
            for name in dp
            if name in camp and _is_finite(dp[name]) and _is_finite(camp[name])
        }
        fields = common if fields is None else fields & common
    return {
        name: float(
            np.mean(
                [
                    _finite(_mapping(row, "camp_secondary")[name], name)
                    - _finite(_mapping(row, "dp_secondary")[name], name)
                    for row in rows
                ]
            )
        )
        for name in sorted(fields or set())
    }


def _candidate_selection(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    values = [
        int(index)
        for row in rows
        for index in row.get("camp_selected_indices", [])
    ]
    if any(index < 0 or index >= 8 for index in values):
        raise ValueError("CAMP selected index outside fixed K=8")
    return {
        "tick_count": len(values),
        "candidate0_selection_count": sum(index == 0 for index in values),
        "non_candidate0_selection_count": sum(index != 0 for index in values),
        "all_k_high_risk_pair_count": sum(
            row.get("all_k_high_risk") is True for row in rows
        ),
    }


def _latency_distributions(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for arm, aliases in LATENCY_STAGES.items():
        ticks = [
            tick
            for row in rows
            for tick in row.get(f"{arm}_tick_latency_ms", [])
        ]
        arm_result = {}
        for public_name, source_name in aliases.items():
            values = np.asarray(
                [
                    _finite(tick[source_name], f"{arm} {public_name} latency")
                    for tick in ticks
                    if source_name in tick
                ],
                dtype=np.float64,
            )
            if ticks and values.size != len(ticks):
                raise ValueError(f"missing required {arm} {public_name} latency")
            arm_result[public_name] = _distribution(values)
        result[arm] = arm_result
    return result


def _distribution(values: np.ndarray) -> dict[str, Any]:
    if values.size == 0:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p95": None,
            "p99": None,
            "max": None,
        }
    if not np.isfinite(values).all() or np.any(values < 0.0):
        raise ValueError("latency values must be finite and nonnegative")
    return {
        "count": int(values.size),
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "p95": float(np.percentile(values, 95.0)),
        "p99": float(np.percentile(values, 99.0)),
        "max": float(values.max()),
    }


def _additional_event_pairs(
    rows: Iterable[Mapping[str, Any]], component: str
) -> int:
    return sum(_component_delta(row, component) > EPS for row in rows)


def _claim_decision(
    *,
    claim_evaluation: bool,
    coverage: Mapping[str, Any],
    overall: Mapping[str, Any],
    event_regressions: Mapping[str, int],
    evidence_guards: Mapping[str, bool],
) -> dict[str, Any]:
    counts = _mapping(overall, "better_tie_worse")
    gates = {
        "claim_evaluation": bool(claim_evaluation),
        "retention_rate": coverage.get("retention_rate") == 1.0,
        "paired_complete_rate": coverage.get("paired_complete_rate") == 1.0,
        "source_invalid_rate": coverage.get("source_invalid_rate") == 0.0,
        "execution_invalid_rate": coverage.get("execution_invalid_rate") == 0.0,
        "overall_mean_delta": _strictly_below_zero(overall.get("mean")),
        "overall_ci95_upper": _strictly_below_zero(overall.get("ci95_high")),
        "better_pairs_exceed_worse_pairs": int(counts.get("better", 0))
        > int(counts.get("worse", 0)),
        "no_additional_collision_pairs": event_regressions["collision_any"] == 0,
        "no_additional_offroad_pairs": event_regressions["offroad_rate"] == 0,
        "no_additional_red_light_pairs": event_regressions[
            "red_light_violation_any"
        ]
        == 0,
        "no_additional_wrong_way_pairs": event_regressions["wrong_way_rate"] == 0,
        "evidence_guards": all(evidence_guards.values()),
    }
    failed = [name for name, passed in gates.items() if not passed]
    return {
        "decision": "limited_claim" if not failed else "honest_no_claim",
        "claim_scope": "frozen_held_out_map_family_and_three_corridor_groups_only",
        "map_family_level_ci": False,
        "unseen_map_generalization": False,
        "native_ranked_k8_superiority": False,
        "gates": gates,
        "failed_gates": failed,
    }


def _strictly_below_zero(value: Any) -> bool:
    return _is_finite(value) and float(value) < 0.0


def _is_finite(value: Any) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False
