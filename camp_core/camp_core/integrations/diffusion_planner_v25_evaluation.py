from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner_v25_calibration import validate_v25_calibration_contract
from .diffusion_planner_v25_fresh_opening import (
    validate_fresh_b2_opening_consumption,
    validate_fresh_b2_opening_release,
)
from .diffusion_planner_v25_holdout_contract import (
    SCIENTIFIC_TERMINAL_STATUSES,
    validate_experiment_protocol,
    validate_holdout_identity,
)
from .diffusion_planner_v25_holdout_opening import (
    validate_holdout_opening_consumption,
    validate_holdout_opening_release,
)
from .diffusion_planner_v25_statistics import (
    NONINFERIORITY_METRICS,
    REQUIRED_CONTROLLED_EVENT_FAMILIES,
    SAFETY_COMPONENTS,
    clustered_paired_summary,
    evaluate_fresh_b2_claim,
)


ARMS = ("candidate0", "static14d", "scene14d")
METHOD_ARMS = ("static14d", "scene14d")
STATUSES = SCIENTIFIC_TERMINAL_STATUSES
BENCHMARK_STRATA = ("naturalistic", "controlled_stress")
CONTROLLED_TIERS = ("easy", "borderline", "high_risk")
NATURALISTIC_SCENARIO_FAMILY = "naturalistic_background"
NATURALISTIC_TIER = "naturalistic"
LATENCY_STAGES = (
    "dp_operational_default",
    "additional_k8_generation",
    "atoms",
    "context",
    "scene_weight",
    "selector",
    "tracker",
    "total_planning",
)
FRESH_TICK_COUNT = 64
SIGNAL_PHASES = ("none", "green", "yellow", "red", "mixed", "unavailable")
SIGNAL_SAFETY_METRICS = (
    "red_light_violation_rate",
    "stop_line_crossing_rate",
    "stop_line_margin_m",
    "crossing_speed_mps",
    "false_stop_on_green_rate",
)
SIGNAL_SAFETY_COUNT_FIELDS = frozenset(
    {
        "red_crossing_intervals",
        "red_violation_intervals",
        "green_false_stop_intervals",
    }
)
SIGNAL_SAFETY_DENOMINATOR_FIELDS = frozenset(
    {
        "red_phase_intervals",
        "green_phase_intervals",
        "green_unblocked_approach_intervals",
        "yellow_phase_intervals",
    }
)
SIGNAL_METRIC_PHASE = {
    "red_light_violation_rate": "red",
    "stop_line_crossing_rate": "red",
    "stop_line_margin_m": "red",
    "crossing_speed_mps": "red",
    "false_stop_on_green_rate": "green",
}
PAIR_AUTHORITY_FIELDS = frozenset(
    {
        "route_identity_sha256",
        "semantic_parameter_block_sha256",
        "native_route_sha256",
        "logical_map_sha256",
        "scenario_seed",
        "spawn_config_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
    }
)
ROW_FIELDS = frozenset(
    {
        "pair_key",
        "arm",
        "arm_order_index",
        *PAIR_AUTHORITY_FIELDS,
        "inference_cluster_id",
        "benchmark_stratum",
        "scenario_family",
        "tier",
        "source_class",
        "phase_authority_mode",
        "signal_phase",
        "status",
        "failure_class",
        "candidate_tensor_modified",
        "selected_index_sequence",
        "source_valid_candidate_count_sequence",
        "all_k_high_risk_tick_count",
        "candidate_pool_has_safe_candidate_tick_count",
        "safety",
        "performance",
        "signal_safety",
        "signal_safety_counts",
        "signal_safety_denominators",
        "latency_ms",
    }
)
SAFETY_FIELDS = frozenset({"total", *SAFETY_COMPONENTS})
ROOT_GATE_FIELDS = frozenset(
    {"failure_denominator_complete", "immutability_passed", "zero_overlap_passed"}
)


def evaluate_fresh_b2_three_arm(
    rows: Sequence[Mapping[str, Any]],
    *,
    calibration_contract: Mapping[str, Any],
    calibration_contract_root_sha256: str,
    preopen_qualification_root_sha256: str,
    opening_release: Mapping[str, Any],
    opening_release_root_sha256: str,
    opening_consumption_receipt: Mapping[str, Any],
    root_gates: Mapping[str, bool],
    _holdout_mode: bool = False,
) -> dict[str, Any]:
    """Evaluate the frozen candidate0/Static14D/Scene14D paired benchmark."""

    calibration = validate_v25_calibration_contract(calibration_contract)
    if (
        calibration["status"] != "calibration_freeze_passed"
        or calibration["fresh_preopen_qualification_allowed"] is not True
        or calibration["fresh_open_authorized"] is not False
        or calibration["one_time_opening_release_required"] is not True
        or calibration["fresh_b2_opened"] is not False
    ):
        raise ValueError("Fresh B2 evaluation requires an eligible unopened calibration freeze")
    _require_sha(calibration_contract_root_sha256, "calibration contract root")
    _require_sha(preopen_qualification_root_sha256, "preopen qualification root")
    _require_sha(opening_release_root_sha256, "opening release root")
    if _holdout_mode:
        release = validate_holdout_opening_release(opening_release)
        identity = validate_holdout_identity(release["holdout_identity"])
        protocol = validate_experiment_protocol(release["experiment_protocol"])
        if (
            release["preopen_authority"]["root_sha256"]
            != preopen_qualification_root_sha256
            or protocol["model_registry_sha256"]
            != calibration["frozen_model_registry_sha256"]
            or protocol["training_scale_sha256"]
            != calibration["training_scale_sha256"]
            or protocol["context_scaler_sha256"]
            != calibration["context_scaler_sha256"]
        ):
            raise ValueError("holdout opening release/calibration authority drifted")
        consumption = validate_holdout_opening_consumption(
            opening_consumption_receipt,
            opening_release=release,
            opening_release_root_sha256=opening_release_root_sha256,
        )
    else:
        release = validate_fresh_b2_opening_release(opening_release)
        identity = None
        protocol = None
        if (
            release["calibration_contract_root_sha256"]
            != calibration_contract_root_sha256
            or release["preopen_qualification_root_sha256"]
            != preopen_qualification_root_sha256
            or release["model_registry_sha256"]
            != calibration["frozen_model_registry_sha256"]
            or release["training_scale_sha256"]
            != calibration["training_scale_sha256"]
            or release["context_scaler_sha256"]
            != calibration["context_scaler_sha256"]
        ):
            raise ValueError("Fresh B2 opening release/calibration authority drifted")
        consumption = validate_fresh_b2_opening_consumption(
            opening_consumption_receipt,
            opening_release=release,
            release_root_sha256=opening_release_root_sha256,
        )
    component_regression_margins = calibration["component_guardrails"]["margins"]
    noninferiority_margins = calibration["noninferiority"]["margins"]
    gates = _root_gates(root_gates)
    normalized = [_row(row, index) for index, row in enumerate(rows)]
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in normalized:
        arm_rows = grouped[row["pair_key"]]
        if row["arm"] in arm_rows:
            raise ValueError("duplicate Fresh B2 pair/arm row")
        arm_rows[row["arm"]] = row
    if not grouped or any(set(arm_rows) != set(ARMS) for arm_rows in grouped.values()):
        raise ValueError("every Fresh B2 pair must contain all three arms")
    _validate_pair_metadata(grouped)
    _validate_unique_pair_authority(grouped)
    order_counts = _arm_order_counts(grouped)
    shared_eligible_pairs = [
        pair
        for pair in grouped.values()
        if all(pair[arm]["status"] == "complete" for arm in ARMS)
    ]
    coverage = _coverage(grouped, gates)

    method_reports: dict[str, dict[str, Any]] = {}
    for method in METHOD_ARMS:
        eligible_pairs = shared_eligible_pairs
        total = np.asarray(
            [pair[method]["safety"]["total"] - pair["candidate0"]["safety"]["total"] for pair in eligible_pairs],
            dtype=np.float64,
        )
        components = {
            name: np.asarray(
                [
                    pair[method]["safety"][name]
                    - pair["candidate0"]["safety"][name]
                    for pair in eligible_pairs
                ],
                dtype=np.float64,
            )
            for name in SAFETY_COMPONENTS
        }
        performance = {
            name: np.asarray(
                [
                    _performance_harm_delta(
                        name,
                        pair["candidate0"]["performance"][name],
                        pair[method]["performance"][name],
                    )
                    for pair in eligible_pairs
                ],
                dtype=np.float64,
            )
            for name in NONINFERIORITY_METRICS
        }
        clusters = [pair["candidate0"]["inference_cluster_id"] for pair in eligible_pairs]
        claim = (
            evaluate_fresh_b2_claim(
                total,
                components,
                performance,
                clusters,
                component_regression_margins=dict(component_regression_margins),
                noninferiority_margins=dict(noninferiority_margins),
                coverage=coverage,
            )
            if len(eligible_pairs) >= 2 and len(set(clusters)) >= 2
            else _insufficient_shared_pair_claim(
                paired_eligible_count=len(eligible_pairs),
                independent_cluster_count=len(set(clusters)),
                coverage=coverage,
                component_regression_margins=component_regression_margins,
                noninferiority_margins=noninferiority_margins,
            )
        )
        method_reports[method] = {
            "paired_eligible_count": len(eligible_pairs),
            "paired_arm_summaries": {
                arm: _paired_arm_summary(eligible_pairs, arm)
                for arm in ("candidate0", method)
            },
            "claim_decision": claim,
            "stratified_safety_cost": _stratified_summaries(
                eligible_pairs, method, total
            ),
            "signal_safety": _signal_safety_summary(eligible_pairs, method),
        }
    return {
        "schema_version": (
            "camp_dp_v25_holdout_three_arm_evaluation_v1"
            if _holdout_mode
            else "camp_dp_v25_fresh_b2_three_arm_evaluation_v2"
        ),
        **(
            {
                "holdout_identity_sha256": identity[
                    "holdout_identity_sha256"
                ],
                "experiment_protocol_sha256": protocol[
                    "experiment_protocol_sha256"
                ],
                "holdout_split": identity["split"],
                "holdout_opened_once_after_cas_consumption": True,
            }
            if _holdout_mode
            else {}
        ),
        "calibration_contract_root_sha256": calibration_contract_root_sha256,
        "preopen_qualification_root_sha256": preopen_qualification_root_sha256,
        "opening_release_root_sha256": opening_release_root_sha256,
        "opening_release_controller_decision_root_sha256": release[
            "controller_decision_root_sha256"
        ],
        "opening_release_consumption_marker_sha256": consumption["marker_sha256"],
        **(
            {"fresh_b2_opened_once_after_nonce_consumption": True}
            if not _holdout_mode
            else {}
        ),
        "calibration_model_registry_sha256": calibration[
            "frozen_model_registry_sha256"
        ],
        "calibration_training_scale_sha256": calibration["training_scale_sha256"],
        "calibration_context_scaler_sha256": calibration["context_scaler_sha256"],
        "noninferiority_margins_from_calibration_contract": True,
        "component_guardrails_from_calibration_contract": True,
        "arms": list(ARMS),
        "candidate0_semantics": "same_forward_operational_default_alias_not_native_ranked_top1",
        "full_plan_pair_count": len(grouped),
        "full_plan_arm_run_count": len(normalized),
        "shared_three_arm_paired_eligible_count": len(shared_eligible_pairs),
        "method_comparisons_use_identical_pair_set": True,
        "arm_order_position_counts": order_counts,
        "arm_order_balanced": True,
        "method_reports": method_reports,
        "failure_accounting": _failure_accounting(normalized),
        "latency_ms": {
            arm: _latency_summary(
                [row for row in normalized if row["arm"] == arm and row["status"] == "complete"]
            )
            for arm in ARMS
        },
        "selector_latency_separated_from_k8_system_overhead": True,
        "v2i_reporting": {
            "primary_mode": "no_v2i",
            "no_v2i_full_plan_pair_count": len(grouped),
            "no_v2i_shared_three_arm_paired_eligible_count": len(
                shared_eligible_pairs
            ),
            "v2i_full_plan_pair_count": 0,
            "v2i_separate_evaluation_authorized": False,
            "phase_remaining_consumed": False,
        },
        "failure_rows_retained_in_denominator": True,
        "safetycost_imputed_for_failed_pairs": False,
        "nine_dimensional_ablations_in_primary_table": False,
        "fresh_outcome_used_to_change_protocol": False,
        "promotion_deployment_activation_authorized": False,
    }


def evaluate_holdout_three_arm(
    rows: Sequence[Mapping[str, Any]],
    *,
    calibration_contract: Mapping[str, Any],
    calibration_contract_root_sha256: str,
    preopen_qualification_root_sha256: str,
    opening_release: Mapping[str, Any],
    opening_release_root_sha256: str,
    opening_consumption_receipt: Mapping[str, Any],
    root_gates: Mapping[str, bool],
) -> dict[str, Any]:
    """Evaluate a generic Fresh holdout under the unchanged V25 claim rules."""

    return evaluate_fresh_b2_three_arm(
        rows,
        calibration_contract=calibration_contract,
        calibration_contract_root_sha256=calibration_contract_root_sha256,
        preopen_qualification_root_sha256=preopen_qualification_root_sha256,
        opening_release=opening_release,
        opening_release_root_sha256=opening_release_root_sha256,
        opening_consumption_receipt=opening_consumption_receipt,
        root_gates=root_gates,
        _holdout_mode=True,
    )


def _require_sha(value: Any, label: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{label} must be a lowercase SHA256")


def _failure_accounting(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def counts(values: Sequence[Mapping[str, Any]]) -> dict[str, int]:
        counter = Counter(str(row["status"]) for row in values)
        return {status: int(counter.get(status, 0)) for status in STATUSES}

    grouped: dict[str, dict[str, dict[str, int]]] = {}
    grouping_fields = {
        "by_arm": "arm",
        "by_scenario_family": "scenario_family",
        "by_family_tier": None,
        "by_family_source": None,
    }
    for output_name, field in grouping_fields.items():
        buckets: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for row in rows:
            if output_name == "by_family_tier":
                key = f"{row['scenario_family']}/{row['tier']}"
            elif output_name == "by_family_source":
                key = f"{row['scenario_family']}/{row['source_class']}"
            else:
                key = str(row[field])
            buckets[key].append(row)
        grouped[output_name] = {
            key: counts(values) for key, values in sorted(buckets.items())
        }
    return {
        "full_plan_arm_run_count": len(rows),
        "all_status_counts": counts(rows),
        **grouped,
        "failed_rows_retained": True,
        "safetycost_imputed": False,
    }


def _row(value: Mapping[str, Any], index: int) -> dict[str, Any]:
    if type(value) is not dict or set(value) != ROW_FIELDS:
        raise ValueError(f"Fresh B2 row {index} field set drifted")
    row = dict(value)
    for field in PAIR_AUTHORITY_FIELDS - {"scenario_seed"}:
        _require_sha(row[field], f"Fresh B2 {field}")
    if type(row["scenario_seed"]) is not int:
        raise ValueError("Fresh B2 scenario seed must be a native integer")
    for field in (
        "pair_key",
        "inference_cluster_id",
        "scenario_family",
        "tier",
        "source_class",
        "signal_phase",
    ):
        if type(row[field]) is not str or not row[field]:
            raise ValueError(f"Fresh B2 row {index} {field} is invalid")
    if row["arm"] not in ARMS or row["status"] not in STATUSES:
        raise ValueError("Fresh B2 arm/status is invalid")
    if row["benchmark_stratum"] not in BENCHMARK_STRATA:
        raise ValueError("Fresh B2 benchmark stratum is invalid")
    if row["benchmark_stratum"] == "naturalistic":
        if (
            row["scenario_family"] != NATURALISTIC_SCENARIO_FAMILY
            or row["tier"] != NATURALISTIC_TIER
        ):
            raise ValueError("naturalistic Fresh B2 row metadata drifted")
    elif (
        row["scenario_family"] not in REQUIRED_CONTROLLED_EVENT_FAMILIES
        or row["tier"] not in CONTROLLED_TIERS
    ):
        raise ValueError("controlled Fresh B2 row is outside the frozen grammar")
    if row["signal_phase"] not in SIGNAL_PHASES:
        raise ValueError("Fresh B2 signal phase is invalid")
    if row["source_class"] == "mapped_signal":
        if (
            (
                row["status"] == "source_ineligible"
                and row["signal_phase"] != "unavailable"
            )
            or (
                row["status"] != "source_ineligible"
                and row["signal_phase"] in {"none", "unavailable"}
            )
            or row["phase_authority_mode"]
            not in {"controlled_same_tick_override", "observe_same_tick_request"}
        ):
            raise ValueError("mapped-signal Fresh B2 row requires a same-tick phase")
    elif row["source_class"] == "no_signal":
        if row["signal_phase"] != "none" or row["phase_authority_mode"] is not None:
            raise ValueError("no-signal Fresh B2 row cannot expose a signal phase")
    else:
        raise ValueError("Fresh B2 source class is invalid")
    if (
        row["scenario_family"] == "red_light_phase_timing"
        and row["source_class"] != "mapped_signal"
    ):
        raise ValueError("red-light Fresh B2 rows require mapped signal authority")
    if type(row["arm_order_index"]) is not int or row["arm_order_index"] not in (0, 1, 2):
        raise ValueError("Fresh B2 arm order index is invalid")
    if row["candidate_tensor_modified"] is not False:
        raise ValueError("Fresh B2 candidate tensor mutation is forbidden")
    if row["status"] == "complete":
        if row["failure_class"] is not None:
            raise ValueError("complete Fresh B2 row cannot have a failure class")
        selected = _native_integer_series(
            row["selected_index_sequence"],
            "selected index",
            minimum=0,
            maximum=7,
        )
        source_counts = _native_integer_series(
            row["source_valid_candidate_count_sequence"],
            "source-valid candidate count",
            minimum=1,
            maximum=8,
        )
        high_risk_count = row["all_k_high_risk_tick_count"]
        safe_count = row["candidate_pool_has_safe_candidate_tick_count"]
        if (
            type(high_risk_count) is not int
            or not 0 <= high_risk_count <= FRESH_TICK_COUNT
            or type(safe_count) is not int
            or not 0 <= safe_count <= FRESH_TICK_COUNT
            or high_risk_count + safe_count > FRESH_TICK_COUNT
        ):
            raise ValueError("complete Fresh B2 candidate-pool evidence drifted")
        if row["arm"] == "candidate0" and any(selected):
            raise ValueError(
                "candidate0 arm must select same-forward candidate index zero every tick"
            )
        row["selected_index_sequence"] = selected
        row["source_valid_candidate_count_sequence"] = source_counts
        row["safety"] = _numeric_mapping(row["safety"], SAFETY_FIELDS, "safety")
        row["performance"] = _numeric_mapping(
            row["performance"], frozenset(NONINFERIORITY_METRICS), "performance"
        )
        row["signal_safety"] = _signal_safety_mapping(row["signal_safety"])
        row["signal_safety_counts"] = _native_nonnegative_integer_mapping(
            row["signal_safety_counts"],
            SIGNAL_SAFETY_COUNT_FIELDS,
            "signal safety counts",
        )
        row["signal_safety_denominators"] = _native_nonnegative_integer_mapping(
            row["signal_safety_denominators"],
            SIGNAL_SAFETY_DENOMINATOR_FIELDS,
            "signal safety denominators",
        )
        _validate_signal_metric_accounting(row)
        if row["source_class"] == "no_signal" and any(
            value != 0.0 for value in row["signal_safety"].values()
        ):
            raise ValueError("no-signal Fresh B2 row must use zero signal outcomes")
        row["latency_ms"] = _latency_series_mapping(row["latency_ms"])
    else:
        if (
            type(row["failure_class"]) is not str
            or not row["failure_class"]
            or (
                row["status"]
                == "fixed_dp_candidate_generation_capability_failure"
                and row["failure_class"]
                != "invalid_k8_heading_norm_envelope"
            )
            or (
                row["status"] == "source_ineligible"
                and row["failure_class"]
                != "preregistered_source_ineligible"
            )
            or row["safety"] is not None
            or row["performance"] is not None
            or row["signal_safety"] is not None
            or row["signal_safety_counts"] is not None
            or row["signal_safety_denominators"] is not None
            or row["latency_ms"] is not None
            or row["selected_index_sequence"] is not None
            or row["source_valid_candidate_count_sequence"] is not None
            or row["all_k_high_risk_tick_count"] is not None
            or row["candidate_pool_has_safe_candidate_tick_count"] is not None
        ):
            raise ValueError("failed Fresh B2 row evidence contract drifted")
    return row


def validate_fresh_b2_evaluation_row(
    row: Mapping[str, Any], *, index: int = 0
) -> dict[str, Any]:
    """Public exact-schema validator for sealed execution-row producers."""

    if type(index) is not int or index < 0:
        raise ValueError("Fresh B2 evaluation row index must be nonnegative")
    return _row(row, index)


def _validate_pair_metadata(grouped: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> None:
    metadata = (
        "pair_key",
        *sorted(PAIR_AUTHORITY_FIELDS),
        "inference_cluster_id",
        "benchmark_stratum",
        "scenario_family",
        "tier",
        "source_class",
        "phase_authority_mode",
        "signal_phase",
    )
    for pair in grouped.values():
        baseline = pair["candidate0"]
        if {pair[arm]["arm_order_index"] for arm in ARMS} != {0, 1, 2}:
            raise ValueError("Fresh B2 pair arm order must be a permutation")
        for arm in METHOD_ARMS:
            if any(pair[arm][field] != baseline[field] for field in metadata):
                raise ValueError("Fresh B2 paired metadata drifted across arms")


def _validate_unique_pair_authority(
    grouped: Mapping[str, Mapping[str, Mapping[str, Any]]]
) -> None:
    seen: dict[tuple[Any, ...], str] = {}
    fields = tuple(sorted(PAIR_AUTHORITY_FIELDS))
    for pair_key, pair in grouped.items():
        authority = tuple(pair["candidate0"][field] for field in fields)
        previous = seen.setdefault(authority, pair_key)
        if previous != pair_key:
            raise ValueError(
                "Fresh B2 pair authority is duplicated under multiple pair keys"
            )


def _arm_order_counts(
    grouped: Mapping[str, Mapping[str, Mapping[str, Any]]]
) -> dict[str, Any]:
    pairs = list(grouped.values())
    result: dict[str, Any] = {"overall": _position_counts(pairs, "overall")}
    for field in ("benchmark_stratum", "scenario_family", "inference_cluster_id"):
        groups: dict[str, list[Mapping[str, Mapping[str, Any]]]] = defaultdict(list)
        for pair in pairs:
            groups[str(pair["candidate0"][field])].append(pair)
        output_name = "independent_cluster" if field == "inference_cluster_id" else field
        result[output_name] = {
            value: _position_counts(rows, f"{field}={value}")
            for value, rows in sorted(groups.items())
        }
    return result


def _position_counts(
    pairs: Sequence[Mapping[str, Mapping[str, Any]]], label: str
) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for arm in ARMS:
        counts = [
            sum(pair[arm]["arm_order_index"] == position for pair in pairs)
            for position in range(3)
        ]
        if max(counts) - min(counts) > 1:
            raise ValueError(f"Fresh B2 arm order is not balanced within {label}")
        result[arm] = counts
    return result


def _coverage(
    grouped: Mapping[str, Mapping[str, Mapping[str, Any]]],
    gates: Mapping[str, bool],
) -> dict[str, Any]:
    source_planned: Counter[str] = Counter()
    source_complete: Counter[str] = Counter()
    tier_planned: Counter[str] = Counter()
    tier_complete: Counter[str] = Counter()
    eligible = 0
    for pair in grouped.values():
        row = pair["candidate0"]
        mode = row["phase_authority_mode"] or "none"
        source_key = f"{row['scenario_family']}/{row['source_class']}/{mode}"
        tier_key = f"{row['scenario_family']}/{row['tier']}"
        source_planned[source_key] += 1
        tier_planned[tier_key] += 1
        complete = all(pair[arm]["status"] == "complete" for arm in ARMS)
        if complete:
            eligible += 1
            source_complete[source_key] += 1
            tier_complete[tier_key] += 1
    total = len(grouped)
    return {
        "full_plan_pair_count": total,
        "paired_eligible_count": eligible,
        "overall_eligible_rate": eligible / total,
        "planned_scenario_families": list(REQUIRED_CONTROLLED_EVENT_FAMILIES),
        "planned_family_source_strata": sorted(source_planned),
        "planned_family_tier_strata": sorted(tier_planned),
        "family_source_eligible_rates": {
            key: source_complete[key] / count for key, count in sorted(source_planned.items())
        },
        "family_tier_eligible_rates": {
            key: tier_complete[key] / count for key, count in sorted(tier_planned.items())
        },
        **gates,
    }


def _stratified_summaries(
    pairs: Sequence[Mapping[str, Mapping[str, Any]]],
    method: str,
    total_deltas: np.ndarray,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    strata = {
        "benchmark_stratum": BENCHMARK_STRATA,
        "event_family": (*REQUIRED_CONTROLLED_EVENT_FAMILIES, NATURALISTIC_SCENARIO_FAMILY),
    }
    for group_name, values in strata.items():
        groups: dict[str, Any] = {}
        field = "benchmark_stratum" if group_name == "benchmark_stratum" else "scenario_family"
        for value in values:
            indices = [i for i, pair in enumerate(pairs) if pair[method][field] == value]
            clusters = [pairs[i][method]["inference_cluster_id"] for i in indices]
            if len(set(clusters)) < 2:
                groups[value] = {
                    "status": "descriptive_only_fewer_than_two_independent_clusters",
                    "observation_count": len(indices),
                    "independent_cluster_count": len(set(clusters)),
                }
            else:
                groups[value] = clustered_paired_summary(total_deltas[indices], clusters)
        result[group_name] = groups
    clusters = [pair[method]["inference_cluster_id"] for pair in pairs]
    if len(set(clusters)) < 2:
        no_v2i: dict[str, Any] = {
            "status": "descriptive_only_fewer_than_two_independent_clusters",
            "observation_count": len(pairs),
            "independent_cluster_count": len(set(clusters)),
        }
    else:
        no_v2i = clustered_paired_summary(total_deltas, clusters)
    result["v2i_mode"] = {
        "no_v2i": no_v2i,
        "v2i": {
            "status": "not_authorized_not_evaluated",
            "observation_count": 0,
            "independent_cluster_count": 0,
            "phase_remaining_consumed": False,
        },
    }
    return result


def _latency_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            stage: {
                "status": "no_complete_runs",
                "run_count": 0,
                "tick_count": 0,
                "mean": None,
                "median": None,
                "p95": None,
                "p99": None,
                "max": None,
            }
            for stage in LATENCY_STAGES
        }
    result: dict[str, Any] = {}
    for stage in LATENCY_STAGES:
        values = np.asarray(
            [
                value
                for row in rows
                for value in row["latency_ms"][stage]
            ],
            dtype=np.float64,
        )
        result[stage] = {
            "run_count": len(rows),
            "tick_count": int(values.size),
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "p95": float(np.percentile(values, 95)),
            "p99": float(np.percentile(values, 99)),
            "max": float(np.max(values)),
        }
    return result


def _insufficient_shared_pair_claim(
    *,
    paired_eligible_count: int,
    independent_cluster_count: int,
    coverage: Mapping[str, Any],
    component_regression_margins: Mapping[str, float],
    noninferiority_margins: Mapping[str, float],
) -> dict[str, Any]:
    """Preserve the full denominator while refusing unsupported inference."""

    return {
        "schema_version": "camp_dp_v25_fresh_b2_insufficient_evidence_no_claim_v1",
        "status": "honest_no_claim_insufficient_shared_paired_evidence",
        "paired_eligible_count": paired_eligible_count,
        "independent_cluster_count": independent_cluster_count,
        "minimum_required_paired_count": 2,
        "minimum_required_independent_cluster_count": 2,
        "coverage": dict(coverage),
        "component_regression_margins": dict(component_regression_margins),
        "noninferiority_margins": dict(noninferiority_margins),
        "safetycost_imputed": False,
        "total_safety_inference_available": False,
        "component_inference_available": False,
        "performance_comfort_noninferiority_available": False,
        "safety_improvement_claim_passed": False,
        "red_light_improvement_claim_passed": False,
        "claim_scope": "unchanged_fixed_dp_valid_k8_preregistered_support_domain",
        "real_world_or_all_map_claim_authorized": False,
    }


def _latency_series_mapping(value: Any) -> dict[str, list[float]]:
    if type(value) is not dict or set(value) != set(LATENCY_STAGES):
        raise ValueError("Fresh B2 latency field set drifted")
    result: dict[str, list[float]] = {}
    for stage in LATENCY_STAGES:
        series = value[stage]
        if type(series) is not list or len(series) != FRESH_TICK_COUNT:
            raise ValueError(
                f"Fresh B2 latency {stage} must contain exactly "
                f"{FRESH_TICK_COUNT} tick values"
            )
        normalized: list[float] = []
        for item in series:
            if (
                type(item) not in (int, float)
                or not np.isfinite(float(item))
                or float(item) < 0.0
            ):
                raise ValueError(f"Fresh B2 latency {stage} contains an invalid tick")
            normalized.append(float(item))
        result[stage] = normalized
    return result


def _signal_safety_summary(
    pairs: Sequence[Mapping[str, Mapping[str, Any]]], method: str
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for metric in SIGNAL_SAFETY_METRICS:
        required_phase = SIGNAL_METRIC_PHASE[metric]
        denominator_field = (
            "green_unblocked_approach_intervals"
            if required_phase == "green"
            else "red_phase_intervals"
        )
        mapped_pairs = [
            pair
            for pair in pairs
            if pair[method]["source_class"] == "mapped_signal"
        ]
        candidate0_positive = [
            pair
            for pair in mapped_pairs
            if pair["candidate0"]["signal_safety_denominators"][denominator_field] > 0
        ]
        method_positive = [
            pair
            for pair in mapped_pairs
            if pair[method]["signal_safety_denominators"][denominator_field] > 0
        ]
        either_positive = [
            pair
            for pair in mapped_pairs
            if pair["candidate0"]["signal_safety_denominators"][denominator_field] > 0
            or pair[method]["signal_safety_denominators"][denominator_field] > 0
        ]
        selected = [
            pair
            for pair in mapped_pairs
            if pair["candidate0"]["signal_safety_denominators"][denominator_field] > 0
            and pair[method]["signal_safety_denominators"][denominator_field] > 0
        ]
        clusters = [pair[method]["inference_cluster_id"] for pair in selected]
        baseline = np.asarray(
            [pair["candidate0"]["signal_safety"][metric] for pair in selected],
            dtype=np.float64,
        )
        candidate = np.asarray(
            [pair[method]["signal_safety"][metric] for pair in selected],
            dtype=np.float64,
        )
        harm_delta = baseline - candidate if metric == "stop_line_margin_m" else candidate - baseline
        row: dict[str, Any] = {
            "required_signal_phase": required_phase,
            "required_positive_denominator": denominator_field,
            "harm_direction": "lower_margin_is_harm" if metric == "stop_line_margin_m" else "higher_is_harm",
            "mapped_signal_pair_count": len(mapped_pairs),
            "candidate0_positive_denominator_count": len(candidate0_positive),
            "method_positive_denominator_count": len(method_positive),
            "either_arm_positive_denominator_count": len(either_positive),
            "paired_observation_count": len(selected),
            "excluded_pair_count_one_sided_denominator": len(either_positive)
            - len(selected),
            "independent_cluster_count": len(set(clusters)),
            "candidate0_mean": float(np.mean(baseline)) if baseline.size else None,
            "method_mean": float(np.mean(candidate)) if candidate.size else None,
        }
        if len(set(clusters)) >= 2:
            row["paired_harm_delta"] = clustered_paired_summary(harm_delta, clusters)
        else:
            row["paired_harm_delta"] = {
                "status": "descriptive_only_fewer_than_two_independent_clusters"
            }
        result[metric] = row
    return result


def _performance_harm_delta(name: str, baseline: float, method: float) -> float:
    if name in {"progress", "completion"}:
        return float(baseline - method)
    return float(method - baseline)


def _paired_arm_summary(
    pairs: Sequence[Mapping[str, Mapping[str, Any]]], arm: str
) -> dict[str, Any]:
    rows = [pair[arm] for pair in pairs]
    if not rows:
        return {
            "run_count": 0,
            "status": "no_shared_three_arm_complete_runs",
            "safety_mean": {
                name: None for name in ("total", *SAFETY_COMPONENTS)
            },
            "performance_mean": {
                name: None for name in NONINFERIORITY_METRICS
            },
            "signal_safety_mean_all_rows_descriptive": {
                name: None for name in SIGNAL_SAFETY_METRICS
            },
            "signal_safety_count_totals": {
                name: 0 for name in SIGNAL_SAFETY_COUNT_FIELDS
            },
            "signal_safety_denominator_totals": {
                name: 0 for name in SIGNAL_SAFETY_DENOMINATOR_FIELDS
            },
            "selected_nonzero_tick_count": 0,
            "selected_nonzero_tick_rate": None,
            "all_k_high_risk_tick_count": 0,
            "candidate_pool_has_safe_candidate_tick_count": 0,
            "candidate_pool_has_safe_candidate_tick_rate": None,
            "source_valid_candidate_count_mean": None,
        }
    return {
        "run_count": len(rows),
        "safety_mean": {
            name: float(np.mean([row["safety"][name] for row in rows]))
            for name in ("total", *SAFETY_COMPONENTS)
        },
        "performance_mean": {
            name: float(np.mean([row["performance"][name] for row in rows]))
            for name in NONINFERIORITY_METRICS
        },
        "signal_safety_mean_all_rows_descriptive": {
            name: float(np.mean([row["signal_safety"][name] for row in rows]))
            for name in SIGNAL_SAFETY_METRICS
        },
        "signal_safety_count_totals": {
            name: int(sum(row["signal_safety_counts"][name] for row in rows))
            for name in SIGNAL_SAFETY_COUNT_FIELDS
        },
        "signal_safety_denominator_totals": {
            name: int(sum(row["signal_safety_denominators"][name] for row in rows))
            for name in SIGNAL_SAFETY_DENOMINATOR_FIELDS
        },
        "selected_nonzero_tick_count": int(
            sum(
                selected_index != 0
                for row in rows
                for selected_index in row["selected_index_sequence"]
            )
        ),
        "selected_nonzero_tick_rate": float(
            np.mean(
                [
                    selected_index != 0
                    for row in rows
                    for selected_index in row["selected_index_sequence"]
                ]
            )
        ),
        "all_k_high_risk_tick_count": int(
            sum(row["all_k_high_risk_tick_count"] for row in rows)
        ),
        "candidate_pool_has_safe_candidate_tick_count": int(
            sum(row["candidate_pool_has_safe_candidate_tick_count"] for row in rows)
        ),
        "candidate_pool_has_safe_candidate_tick_rate": float(
            sum(
                row["candidate_pool_has_safe_candidate_tick_count"] for row in rows
            )
            / (FRESH_TICK_COUNT * len(rows))
        ),
        "source_valid_candidate_count_mean": float(
            np.mean(
                [
                    count
                    for row in rows
                    for count in row["source_valid_candidate_count_sequence"]
                ]
            )
        ),
    }


def _numeric_mapping(value: Any, fields: frozenset[str], label: str) -> dict[str, float]:
    if type(value) is not dict or set(value) != fields:
        raise ValueError(f"Fresh B2 {label} field set drifted")
    result: dict[str, float] = {}
    for name, item in value.items():
        if type(item) not in (int, float) or not np.isfinite(float(item)) or float(item) < 0.0:
            raise ValueError(f"Fresh B2 {label} {name} is invalid")
        result[name] = float(item)
    return result


def _signal_safety_mapping(value: Any) -> dict[str, float]:
    if type(value) is not dict or set(value) != set(SIGNAL_SAFETY_METRICS):
        raise ValueError("Fresh B2 signal safety field set drifted")
    result: dict[str, float] = {}
    for name in SIGNAL_SAFETY_METRICS:
        item = value[name]
        if type(item) not in (int, float) or not np.isfinite(float(item)):
            raise ValueError(f"Fresh B2 signal safety {name} is invalid")
        number = float(item)
        if name.endswith("_rate") and not 0.0 <= number <= 1.0:
            raise ValueError(f"Fresh B2 signal safety {name} must lie in [0,1]")
        if name == "crossing_speed_mps" and number < 0.0:
            raise ValueError("Fresh B2 crossing speed must be nonnegative")
        result[name] = number
    return result


def _native_nonnegative_integer_mapping(
    value: Any, fields: frozenset[str], label: str
) -> dict[str, int]:
    if type(value) is not dict or set(value) != fields:
        raise ValueError(f"Fresh B2 {label} field set drifted")
    result: dict[str, int] = {}
    for name, item in value.items():
        if type(item) is not int or item < 0:
            raise ValueError(f"Fresh B2 {label} {name} is invalid")
        result[name] = item
    return result


def _native_integer_series(
    value: Any,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> list[int]:
    if type(value) is not list or len(value) != FRESH_TICK_COUNT:
        raise ValueError(
            f"Fresh B2 {label} must contain exactly {FRESH_TICK_COUNT} tick values"
        )
    if any(type(item) is not int or not minimum <= item <= maximum for item in value):
        raise ValueError(f"Fresh B2 {label} contains an invalid tick")
    return list(value)


def _validate_signal_metric_accounting(row: Mapping[str, Any]) -> None:
    metrics = row["signal_safety"]
    counts = row["signal_safety_counts"]
    denominators = row["signal_safety_denominators"]
    phase = row["signal_phase"]
    source_class = row["source_class"]
    red_denominator = denominators["red_phase_intervals"]
    green_denominator = denominators["green_phase_intervals"]
    green_approach = denominators["green_unblocked_approach_intervals"]
    yellow_denominator = denominators["yellow_phase_intervals"]
    if green_approach > green_denominator:
        raise ValueError("Fresh B2 green approach denominator exceeds green exposure")
    if counts["red_violation_intervals"] > counts["red_crossing_intervals"]:
        raise ValueError("Fresh B2 red violations exceed stop-line crossings")
    if counts["red_crossing_intervals"] > red_denominator:
        raise ValueError("Fresh B2 red crossings exceed red exposure")
    if counts["green_false_stop_intervals"] > green_approach:
        raise ValueError("Fresh B2 green false stops exceed approach exposure")

    expected_rates = {
        "red_light_violation_rate": counts["red_violation_intervals"]
        / max(red_denominator, 1),
        "stop_line_crossing_rate": counts["red_crossing_intervals"]
        / max(red_denominator, 1),
        "false_stop_on_green_rate": counts["green_false_stop_intervals"]
        / max(green_approach, 1),
    }
    for name, expected in expected_rates.items():
        if not np.isclose(metrics[name], expected, rtol=0.0, atol=1e-12):
            raise ValueError(f"Fresh B2 signal metric {name} disagrees with counts")
    if counts["red_crossing_intervals"] == 0 and metrics["crossing_speed_mps"] != 0.0:
        raise ValueError("Fresh B2 crossing speed requires a red crossing")

    if source_class == "no_signal":
        if phase != "none" or any(counts.values()) or any(denominators.values()) or any(
            value != 0.0 for value in metrics.values()
        ):
            raise ValueError("no-signal Fresh B2 row must use zero signal evidence")
        return

    exposures = {
        "red": red_denominator,
        "green": green_denominator,
        "yellow": yellow_denominator,
    }
    if phase in exposures:
        if exposures[phase] <= 0 or any(
            value > 0 for name, value in exposures.items() if name != phase
        ):
            raise ValueError("single-phase Fresh B2 row exposure accounting drifted")
    elif phase == "mixed":
        if sum(value > 0 for value in exposures.values()) < 2:
            raise ValueError("mixed-phase Fresh B2 row requires at least two phases")
    else:  # pragma: no cover - guarded by the row phase enum
        raise ValueError("mapped-signal Fresh B2 phase is invalid")

    if red_denominator == 0 and any(
        metrics[name] != 0.0
        for name in (
            "red_light_violation_rate",
            "stop_line_crossing_rate",
            "stop_line_margin_m",
            "crossing_speed_mps",
        )
    ):
        raise ValueError("Fresh B2 red metrics require red same-tick exposure")
    if green_approach == 0 and metrics["false_stop_on_green_rate"] != 0.0:
        raise ValueError("Fresh B2 false-stop metric requires green approach exposure")


def _root_gates(value: Mapping[str, bool]) -> dict[str, bool]:
    if type(value) is not dict or set(value) != ROOT_GATE_FIELDS:
        raise ValueError("Fresh B2 root gate field set drifted")
    if any(type(item) is not bool for item in value.values()):
        raise ValueError("Fresh B2 root gates must be native booleans")
    return dict(value)
