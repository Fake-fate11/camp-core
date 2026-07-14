"""Frozen retained-pair statistics for the v22 native DP/CAMP study."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any

import numpy as np


EPS = 1e-12
BOOTSTRAP_RESAMPLES = 5_000
BOOTSTRAP_SEED = 12_345
SPEED_TOLERANCES = ("0.0", "0.05", "0.1", "0.2")
REQUIRED_EVIDENCE_GUARDS = (
    "artifact_sha_verified",
    "candidate_immutability_verified",
    "candidate0_default_identity_verified",
    "independent_review_passed",
    "split_zero_overlap_verified",
    "arm_symmetry_verified",
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
    """Analyze one frozen paired run without imputing failed pairs."""
    planned = [str(value) for value in planned_pair_keys]
    observed = [str(row.get("pair_key")) for row in rows]
    if len(set(planned)) != len(planned) or len(set(observed)) != len(observed):
        raise ValueError("planned and observed pair keys must be unique")
    if set(planned) != set(observed):
        raise ValueError("planned and observed pair keys must match exactly")
    if any(
        row.get("route_retained") is not True
        or row.get("included_in_denominator") is not True
        for row in rows
    ):
        raise ValueError("every planned pair must be retained in the denominator")

    complete = [row for row in rows if row.get("paired_complete") is True]
    for row in complete:
        _finite_float(_mapping(row, "paired_delta").get("delta"), "paired delta")
        _mapping(row, "component_delta")

    coverage = _coverage(rows, len(planned))
    strata_rows = {
        "overall": complete,
        "normal": [row for row in complete if not _is_stress(row)],
        "stress": [row for row in complete if _is_stress(row)],
        "all_k_high_risk": [
            row for row in complete if row.get("all_k_high_risk") is True
        ],
    }
    strata = {
        name: _paired_summary(
            subset,
            lambda row: _mapping(row, "paired_delta")["delta"],
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        )
        for name, subset in strata_rows.items()
    }
    component_names = sorted(
        {
            name
            for row in complete
            for name in _mapping(row, "component_delta").keys()
        }
    )
    components = {
        name: _paired_summary(
            complete,
            lambda row, atom=name: _mapping(row, "component_delta")[atom],
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        )
        for name in component_names
    }
    speed = _speed_sensitivity(
        complete,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
    )
    secondary = _secondary_mean_deltas(complete)
    latency = _latency_means(complete)
    additional_collision = _additional_event_pairs(
        complete, "collision_any"
    )
    additional_red_light = _additional_event_pairs(
        complete, "red_light_violation_any"
    )
    guards = {
        name: bool((evidence_guards or {}).get(name, False))
        for name in REQUIRED_EVIDENCE_GUARDS
    }
    decision = _claim_decision(
        claim_evaluation=claim_evaluation,
        coverage=coverage,
        overall=strata["overall"],
        components=components,
        additional_collision_pairs=additional_collision,
        additional_red_light_pairs=additional_red_light,
        evidence_guards=guards,
    )
    return {
        "schema_version": "camp_dp_v22_retained_pair_statistics_v1",
        "bootstrap_contract": {
            "hierarchy": [
                "logical_map_sha256",
                "group_sha256",
                "route_identity_sha256",
                "seed",
            ],
            "resamples": int(bootstrap_resamples),
            "seed": int(bootstrap_seed),
        },
        "coverage": coverage,
        "strata": strata,
        "components": components,
        "additional_collision_pairs": additional_collision,
        "additional_red_light_pairs": additional_red_light,
        "speed_sensitivity_event_rate_delta": speed,
        "secondary_mean_delta": secondary,
        "latency_mean_ms": latency,
        "evidence_guards": guards,
        "claim_decision": decision,
    }


def _mapping(container: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = container.get(name)
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _finite_float(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _coverage(rows: Sequence[Mapping[str, Any]], planned_count: int) -> dict[str, Any]:
    retained = len(rows)
    complete = sum(row.get("paired_complete") is True for row in rows)
    hard_invalid = sum(row.get("hard_invalid") is True for row in rows)
    execution_failure = sum(
        row.get("execution_failure") is True for row in rows
    )
    denominator = retained or 1
    return {
        "planned_pair_count": int(planned_count),
        "retained_pair_count": retained,
        "paired_complete_count": complete,
        "hard_invalid_pair_count": hard_invalid,
        "execution_failure_pair_count": execution_failure,
        "route_coverage": retained / (planned_count or 1),
        "paired_complete_rate": complete / denominator,
        "hard_invalid_rate": hard_invalid / denominator,
    }


def _is_stress(row: Mapping[str, Any]) -> bool:
    strata = _mapping(row, "source_stratum")
    return bool(row.get("all_k_high_risk") is True or any(strata.values()))


def _paired_summary(
    rows: Sequence[Mapping[str, Any]],
    getter: Callable[[Mapping[str, Any]], Any],
    *,
    bootstrap_resamples: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    values = np.asarray(
        [_finite_float(getter(row), "paired statistic") for row in rows],
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
    ci_low, ci_high = _cluster_bootstrap_ci(
        rows,
        getter,
        resamples=bootstrap_resamples,
        seed=bootstrap_seed,
    )
    return {
        "pair_count": int(values.size),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "ci95_low": ci_low,
        "ci95_high": ci_high,
        "better_tie_worse": {
            "better": labels["better"],
            "tie": labels["tie"],
            "worse": labels["worse"],
        },
    }


def _cluster_bootstrap_ci(
    rows: Sequence[Mapping[str, Any]],
    getter: Callable[[Mapping[str, Any]], Any],
    *,
    resamples: int,
    seed: int,
) -> tuple[float | None, float | None]:
    if not rows or resamples <= 0:
        return None, None
    rng = np.random.default_rng(seed)
    means = np.empty(int(resamples), dtype=np.float64)
    maps = sorted({str(row["logical_map_sha256"]) for row in rows})
    for index in range(int(resamples)):
        sampled: list[float] = []
        for map_id in rng.choice(maps, size=len(maps), replace=True):
            map_rows = [
                row for row in rows if str(row["logical_map_sha256"]) == map_id
            ]
            groups = sorted({str(row["group_sha256"]) for row in map_rows})
            for group_id in rng.choice(groups, size=len(groups), replace=True):
                group_rows = [
                    row
                    for row in map_rows
                    if str(row["group_sha256"]) == group_id
                ]
                routes = sorted(
                    {str(row["route_identity_sha256"]) for row in group_rows}
                )
                for route_id in rng.choice(routes, size=len(routes), replace=True):
                    route_rows = [
                        row
                        for row in group_rows
                        if str(row["route_identity_sha256"]) == route_id
                    ]
                    seeds = sorted({int(row["seed"]) for row in route_rows})
                    for scenario_seed in rng.choice(
                        seeds, size=len(seeds), replace=True
                    ):
                        row = next(
                            item
                            for item in route_rows
                            if int(item["seed"]) == int(scenario_seed)
                        )
                        sampled.append(
                            _finite_float(getter(row), "bootstrap statistic")
                        )
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
    reports: dict[str, Any] = {}
    for tolerance in SPEED_TOLERANCES:
        reports[tolerance] = _paired_summary(
            rows,
            lambda row, key=tolerance: _speed_event_rate(row, "camp", key)
            - _speed_event_rate(row, "dp", key),
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        )
    for field in ("magnitude_duration_m", "excess_duration_s"):
        reports[f"continuous_{field}_delta"] = _paired_summary(
            rows,
            lambda row, name=field: _continuous_speed(row, "camp", name)
            - _continuous_speed(row, "dp", name),
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        )
    return reports


def _speed_event_rate(row: Mapping[str, Any], arm: str, tolerance: str) -> float:
    safety = _mapping(row, f"{arm}_safety")
    protocol = _mapping(safety, "speed_protocol")
    sensitivity = _mapping(protocol, "sensitivity")
    return _finite_float(
        _mapping(sensitivity, tolerance).get("event_rate"), "speed event rate"
    )


def _continuous_speed(row: Mapping[str, Any], arm: str, field: str) -> float:
    safety = _mapping(row, f"{arm}_safety")
    protocol = _mapping(safety, "speed_protocol")
    return _finite_float(
        _mapping(protocol, "continuous").get(field), "continuous speed metric"
    )


def _secondary_mean_deltas(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    common = _common_numeric_fields(rows, "dp_secondary", "camp_secondary")
    return {
        name: float(
            np.mean(
                [
                    _finite_float(_mapping(row, "camp_secondary")[name], name)
                    - _finite_float(_mapping(row, "dp_secondary")[name], name)
                    for row in rows
                ]
            )
        )
        for name in common
    }


def _latency_means(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for arm in ("dp", "camp"):
        container_name = f"{arm}_latency"
        stages = sorted(
            {
                name
                for row in rows
                for name, value in _mapping(row, container_name).items()
                if isinstance(value, Mapping) and _is_finite(value.get("mean"))
            }
        )
        result[arm] = {
            stage: float(
                np.mean(
                    [
                        _finite_float(
                            _mapping(_mapping(row, container_name), stage)["mean"],
                            f"{arm} {stage} latency",
                        )
                        for row in rows
                        if stage in _mapping(row, container_name)
                    ]
                )
            )
            for stage in stages
        }
    return result


def _common_numeric_fields(
    rows: Sequence[Mapping[str, Any]], left: str, right: str
) -> list[str]:
    if not rows:
        return []
    fields: set[str] | None = None
    for row in rows:
        current = {
            name
            for name in _mapping(row, left)
            if name in _mapping(row, right)
            and _is_finite(_mapping(row, left)[name])
            and _is_finite(_mapping(row, right)[name])
        }
        fields = current if fields is None else fields & current
    return sorted(fields or set())


def _is_finite(value: Any) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _additional_event_pairs(
    rows: Iterable[Mapping[str, Any]], component: str
) -> int:
    return sum(
        _finite_float(
            _mapping(_mapping(row, "camp_safety"), "components")[component],
            component,
        )
        > _finite_float(
            _mapping(_mapping(row, "dp_safety"), "components")[component],
            component,
        )
        + EPS
        for row in rows
    )


def _claim_decision(
    *,
    claim_evaluation: bool,
    coverage: Mapping[str, Any],
    overall: Mapping[str, Any],
    components: Mapping[str, Mapping[str, Any]],
    additional_collision_pairs: int,
    additional_red_light_pairs: int,
    evidence_guards: Mapping[str, bool],
) -> dict[str, Any]:
    offroad = components.get("offroad_rate", {})
    wrong_way = components.get("wrong_way_rate", {})
    counts = _mapping(overall, "better_tie_worse")
    gates = {
        "claim_evaluation": bool(claim_evaluation),
        "overall_mean_delta": _strictly_below_zero(overall.get("mean")),
        "overall_ci95_upper": _strictly_below_zero(overall.get("ci95_high")),
        "better_pairs_exceed_worse_pairs": int(counts.get("better", 0))
        > int(counts.get("worse", 0)),
        "additional_collision_pairs": additional_collision_pairs == 0,
        "additional_red_light_pairs": additional_red_light_pairs == 0,
        "offroad_mean_delta": _at_most(offroad.get("mean"), 0.0),
        "offroad_ci95_upper": _at_most(offroad.get("ci95_high"), 0.005),
        "wrong_way_mean_delta": _at_most(wrong_way.get("mean"), 0.0),
        "wrong_way_ci95_upper": _at_most(wrong_way.get("ci95_high"), 0.005),
        "complete_failure_accounting": coverage.get("route_coverage") == 1.0,
        "evidence_guards": all(evidence_guards.values()),
    }
    failed = [name for name, passed in gates.items() if not passed]
    return {
        "decision": "claim" if not failed else "honest_no_claim",
        "claim_scope": (
            "two_fixed_logical_maps_unseen_route_family_corridor_and_seed"
        ),
        "unseen_map_generalization": False,
        "gates": gates,
        "failed_gates": failed,
    }


def _strictly_below_zero(value: Any) -> bool:
    return _is_finite(value) and float(value) < 0.0


def _at_most(value: Any, maximum: float) -> bool:
    return _is_finite(value) and float(value) <= maximum
