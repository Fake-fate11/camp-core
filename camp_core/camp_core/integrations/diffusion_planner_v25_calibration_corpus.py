from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

from .diffusion_planner_v25_calibration import (
    FIXED_DP_HEAD,
    project_candidate0_ni_calibration_row,
)
from .diffusion_planner_v25_signal_complete_plan import (
    validate_signal_complete_execution_plan,
)
from .diffusion_planner_v25_paired_calibration import (
    validate_paired_calibration_execution_plan,
)


SCHEMA_VERSION = "camp_dp_v25_candidate0_calibration_corpus_projection_v2"
RUN_RESULT_SCHEMA_VERSION = "camp_dp_v25_candidate0_calibration_run_result_v1"
FAILURE_SCHEMA_VERSION = "camp_dp_v25_candidate0_calibration_retained_failure_v1"
FIXED_DP_FAILURE_CLASS = "fixed_dp_candidate_generation_capability_failure"
FIXED_DP_FAILURE_REASON = "invalid_k8_heading_norm_envelope"


def project_candidate0_calibration_corpus_from_paired_terminals(
    *,
    calibration_plan: Mapping[str, Any],
    paired_plan: Mapping[str, Any],
    candidate0_terminals: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Project only the candidate0 terminals from an accepted paired run.

    The caller may stream the 100 candidate0 terminal files independently
    rather than loading the 300-arm paired corpus.  The frozen paired plan
    supplies the exact run ordinal/order, while the base calibration plan
    supplies the map-geometry and semantic identities used by the diagnostic
    and exact-repeat keys.
    """

    base = validate_signal_complete_execution_plan(calibration_plan)
    paired = validate_paired_calibration_execution_plan(
        paired_plan, calibration_plan=base
    )
    identities = {
        row["scenario_identity_sha256"]: row for row in paired["identities"]
    }
    base_units = {
        row["unit_ordinal"]: row for row in base["execution_units"]
    }
    projected: list[dict[str, Any]] = []
    try:
        pairs = zip(
            paired["execution_units"], candidate0_terminals, strict=True
        )
        for unit, raw_terminal in pairs:
            terminal = dict(raw_terminal)
            candidate0_order = unit["ordered_arms"].index(
                "candidate0_operational_default"
            )
            expected_run_ordinal = unit["unit_ordinal"] * 3 + candidate0_order
            identity = identities[unit["scenario_identity_sha256"]]
            if (
                terminal.get("run_ordinal") != expected_run_ordinal
                or terminal.get("unit_ordinal") != unit["unit_ordinal"]
                or terminal.get("unit_sha256") != unit["unit_sha256"]
                or terminal.get("arm_order_index") != candidate0_order
                or terminal.get("plan_arm")
                != "candidate0_operational_default"
                or terminal.get("scenario_identity_sha256")
                != unit["scenario_identity_sha256"]
                or terminal.get("route_identity_sha256")
                != identity["route_identity_sha256"]
                or terminal.get("seed") != unit["seed"]
                or terminal.get("fresh_b2_opened") is not False
                or terminal.get("fresh_outcome_fields_consumed") != []
            ):
                raise ValueError("paired candidate0 terminal authority drifted")
            status = terminal.get("status")
            if status == "complete":
                native_receipt = terminal.get("native_receipt")
                failure_receipt = None
                if type(native_receipt) is not dict:
                    raise ValueError("paired candidate0 native receipt is missing")
            elif status == "retained_fixed_dp_capability_failure":
                native_receipt = None
                paired_failure = terminal.get("failure_receipt")
                if type(paired_failure) is not dict:
                    raise ValueError("paired candidate0 failure receipt is missing")
                failure_receipt = {
                    "schema_version": FAILURE_SCHEMA_VERSION,
                    "scenario_identity_sha256": identity[
                        "scenario_identity_sha256"
                    ],
                    "route_identity_sha256": identity["route_identity_sha256"],
                    "seed": unit["seed"],
                    "fixed_dp_head": FIXED_DP_HEAD,
                    "failure_class": paired_failure.get("failure_class"),
                    "reason": paired_failure.get("reason"),
                    "raw_failure_receipt_sha256": paired_failure.get(
                        "raw_failure_receipt_sha256"
                    ),
                    "training_eligible": False,
                    "calibration_eligible": False,
                    "evaluation_eligible": False,
                    "fresh_b2_opened": False,
                    "outcome_fields_consumed": [],
                }
            else:
                raise ValueError(
                    "paired candidate0 terminal status is not retainable"
                )
            projected.append(
                {
                    "schema_version": RUN_RESULT_SCHEMA_VERSION,
                    "unit_ordinal": unit["unit_ordinal"],
                    "unit_sha256": base_units[unit["unit_ordinal"]][
                        "unit_sha256"
                    ],
                    "scenario_identity_sha256": unit[
                        "scenario_identity_sha256"
                    ],
                    "route_identity_sha256": identity["route_identity_sha256"],
                    "seed": unit["seed"],
                    "status": status,
                    "native_receipt": native_receipt,
                    "failure_receipt": failure_receipt,
                    "fresh_b2_opened": False,
                    "fresh_outcome_fields_consumed": [],
                }
            )
    except ValueError as exc:
        if "zip() argument" in str(exc):
            raise ValueError(
                "paired candidate0 terminal denominator drifted"
            ) from exc
        raise
    return project_candidate0_calibration_corpus(base, projected)


def project_candidate0_calibration_corpus(
    plan: Mapping[str, Any], run_results: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Join reviewed candidate0 runs to the frozen calibration denominator.

    Every planned run contributes exactly one terminal row.  Complete runs are
    projected mechanically into NI rows; the only retainable failure is the
    unchanged fixed-DP invalid-K8 heading capability failure, which never
    enters calibration estimation or training.
    """

    validated = validate_signal_complete_execution_plan(plan)
    if (
        validated["split"] != "calibration"
        or validated["planned_arm_run_count"] != 100
        or validated["execution_unit_count"] != 100
        or validated["ticks_per_arm_run"] != 64
        or validated["paired_arms"] != []
        or validated["fresh_b2_opened"] is not False
        or validated["outcome_fields_consumed"] != []
    ):
        raise ValueError("candidate0 calibration plan contract drifted")
    rows = list(run_results)
    if len(rows) != validated["execution_unit_count"]:
        raise ValueError("candidate0 calibration terminal denominator drifted")
    identities = {
        row["scenario_identity_sha256"]: row for row in validated["identities"]
    }
    candidate0_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    seen_measurements: set[str] = set()
    for expected, actual in zip(validated["execution_units"], rows, strict=True):
        result = _run_result(actual, expected)
        identity = identities[expected["scenario_identity_sha256"]]
        if result["route_identity_sha256"] != identity["route_identity_sha256"]:
            raise ValueError("candidate0 calibration route identity drifted")
        if result["status"] == "complete":
            native = result["native_receipt"]
            if (
                native.get("route_name") != identity["route_identity_sha256"]
                or native.get("scenario_seed") != expected["seed"]
            ):
                raise ValueError("candidate0 calibration native plan binding drifted")
            projected = project_candidate0_ni_calibration_row(
                heterogeneity_cluster_id=identity["map_geometry_sha256"],
                run_instance_sha256=expected["unit_sha256"],
                scenario_identity_sha256=identity["scenario_identity_sha256"],
                route_identity_sha256=identity["route_identity_sha256"],
                semantic_parameter_block_sha256=identity[
                    "semantic_parameter_block_sha256"
                ],
                native_receipt=native,
            )
            if projected["measurement_sha256"] in seen_measurements:
                raise ValueError("candidate0 calibration measurement repeated")
            seen_measurements.add(projected["measurement_sha256"])
            candidate0_rows.append(projected)
        else:
            failures.append(_retained_failure(result["failure_receipt"], identity, expected))

    complete = len(candidate0_rows)
    retained = len(failures)
    eligible_rate = complete / len(rows)
    repeatability_counts: dict[str, int] = {}
    for row in candidate0_rows:
        digest = row["repeatability_identity_sha256"]
        repeatability_counts[digest] = repeatability_counts.get(digest, 0) + 1
    exact_duplicate_counts = {
        digest: count
        for digest, count in repeatability_counts.items()
        if count >= 2
    }
    status = (
        "passed_candidate0_calibration_corpus_projection"
        if eligible_rate >= 0.95
        else "candidate0_calibration_corpus_scientifically_ineligible"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "fixed_dp_head": FIXED_DP_HEAD,
        "planned_run_count": len(rows),
        "complete_run_count": complete,
        "retained_fixed_dp_capability_failure_count": retained,
        "paired_eligible_rate": eligible_rate,
        "minimum_paired_eligible_rate": 0.95,
        "map_count": validated["map_count"],
        "intersection_count": validated["intersection_count"],
        "corridor_count": validated["corridor_count"],
        "route_count": validated["route_count"],
        "heterogeneity_diagnostic_cluster_definition": (
            "map_geometry_sha256_with_cross_scenario_route_seed_variation"
        ),
        "heterogeneity_diagnostic_cluster_count": len(
            {row["heterogeneity_cluster_id"] for row in candidate0_rows}
        ),
        "repeatability_identity_definition": (
            "same_route_scenario_semantic_block_seed_initial_state_and_"
            "exogenous_schedule_binding"
        ),
        "exact_duplicate_repeatability_group_count": len(exact_duplicate_counts),
        "exact_duplicate_repeatability_measurement_count": sum(
            exact_duplicate_counts.values()
        ),
        "candidate0_rows": candidate0_rows,
        "candidate0_rows_sha256": _canonical_sha(candidate0_rows),
        "retained_failures": failures,
        "retained_failures_sha256": _canonical_sha(failures),
        "candidate0_same_forward_operational_default": True,
        "candidate_tensor_modified": False,
        "camp_method_outcomes_consumed": False,
        "training_eligible_failure_count": 0,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }


def validate_candidate0_calibration_corpus(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("candidate0 calibration corpus must be a native mapping")
    fields = {
        "schema_version", "status", "fixed_dp_head", "planned_run_count",
        "complete_run_count", "retained_fixed_dp_capability_failure_count",
        "paired_eligible_rate", "minimum_paired_eligible_rate", "map_count",
        "intersection_count", "corridor_count", "route_count",
        "heterogeneity_diagnostic_cluster_definition",
        "heterogeneity_diagnostic_cluster_count",
        "repeatability_identity_definition",
        "exact_duplicate_repeatability_group_count",
        "exact_duplicate_repeatability_measurement_count", "candidate0_rows",
        "candidate0_rows_sha256", "retained_failures",
        "retained_failures_sha256", "candidate0_same_forward_operational_default",
        "candidate_tensor_modified", "camp_method_outcomes_consumed",
        "training_eligible_failure_count", "fresh_b2_opened",
        "fresh_outcome_fields_consumed",
    }
    if set(value) != fields:
        raise ValueError("candidate0 calibration corpus field set drifted")
    result = dict(value)
    candidate0 = result.get("candidate0_rows")
    failures = result.get("retained_failures")
    if type(candidate0) is not list or type(failures) is not list:
        raise ValueError("candidate0 calibration corpus rows are malformed")
    planned = result.get("planned_run_count")
    complete = result.get("complete_run_count")
    retained = result.get("retained_fixed_dp_capability_failure_count")
    if (
        type(planned) is not int
        or type(complete) is not int
        or type(retained) is not int
        or planned != 100
        or complete != len(candidate0)
        or retained != len(failures)
        or complete + retained != planned
        or type(result.get("paired_eligible_rate")) is not float
        or result["paired_eligible_rate"] != complete / planned
        or result.get("candidate0_rows_sha256") != _canonical_sha(candidate0)
        or result.get("retained_failures_sha256") != _canonical_sha(failures)
    ):
        raise ValueError("candidate0 calibration corpus accounting drifted")
    exact = {
        "schema_version": SCHEMA_VERSION,
        "fixed_dp_head": FIXED_DP_HEAD,
        "minimum_paired_eligible_rate": 0.95,
        "heterogeneity_diagnostic_cluster_definition": (
            "map_geometry_sha256_with_cross_scenario_route_seed_variation"
        ),
        "repeatability_identity_definition": (
            "same_route_scenario_semantic_block_seed_initial_state_and_"
            "exogenous_schedule_binding"
        ),
        "candidate0_same_forward_operational_default": True,
        "candidate_tensor_modified": False,
        "camp_method_outcomes_consumed": False,
        "training_eligible_failure_count": 0,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    if any(not _strict_equal(result.get(name), expected) for name, expected in exact.items()):
        raise ValueError("candidate0 calibration corpus frozen contract drifted")
    expected_status = (
        "passed_candidate0_calibration_corpus_projection"
        if result["paired_eligible_rate"] >= 0.95
        else "candidate0_calibration_corpus_scientifically_ineligible"
    )
    if result.get("status") != expected_status:
        raise ValueError("candidate0 calibration corpus status drifted")
    heterogeneity_ids = {
        row.get("heterogeneity_cluster_id") for row in candidate0
    }
    repeatability_counts: dict[str, int] = {}
    for row in candidate0:
        digest = row.get("repeatability_identity_sha256")
        if type(digest) is not str:
            raise ValueError("candidate0 repeatability identity is missing")
        repeatability_counts[digest] = repeatability_counts.get(digest, 0) + 1
    exact_counts = [
        count for count in repeatability_counts.values() if count >= 2
    ]
    if (
        None in heterogeneity_ids
        or result.get("heterogeneity_diagnostic_cluster_count")
        != len(heterogeneity_ids)
        or result.get("exact_duplicate_repeatability_group_count")
        != len(exact_counts)
        or result.get("exact_duplicate_repeatability_measurement_count")
        != sum(exact_counts)
    ):
        raise ValueError("candidate0 calibration diagnostic accounting drifted")
    return result


def _run_result(value: Mapping[str, Any], expected: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "schema_version", "unit_ordinal", "unit_sha256",
        "scenario_identity_sha256", "route_identity_sha256", "seed", "status",
        "native_receipt", "failure_receipt", "fresh_b2_opened",
        "fresh_outcome_fields_consumed",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("candidate0 calibration run result schema drifted")
    result = dict(value)
    if (
        result.get("schema_version") != RUN_RESULT_SCHEMA_VERSION
        or result.get("unit_ordinal") != expected["unit_ordinal"]
        or result.get("unit_sha256") != expected["unit_sha256"]
        or result.get("scenario_identity_sha256")
        != expected["scenario_identity_sha256"]
        or result.get("seed") != expected["seed"]
        or result.get("fresh_b2_opened") is not False
        or result.get("fresh_outcome_fields_consumed") != []
    ):
        raise ValueError("candidate0 calibration run authority drifted")
    _require_sha(result.get("route_identity_sha256"), "route_identity_sha256")
    if result.get("status") == "complete":
        if type(result.get("native_receipt")) is not dict or result.get("failure_receipt") is not None:
            raise ValueError("complete candidate0 calibration result is malformed")
    elif result.get("status") == "retained_fixed_dp_capability_failure":
        if result.get("native_receipt") is not None or type(result.get("failure_receipt")) is not dict:
            raise ValueError("retained candidate0 calibration result is malformed")
    else:
        raise ValueError("candidate0 calibration result status is not retainable")
    return result


def _retained_failure(
    value: Mapping[str, Any], identity: Mapping[str, Any], unit: Mapping[str, Any]
) -> dict[str, Any]:
    expected = {
        "schema_version": FAILURE_SCHEMA_VERSION,
        "scenario_identity_sha256": identity["scenario_identity_sha256"],
        "route_identity_sha256": identity["route_identity_sha256"],
        "seed": unit["seed"],
        "fixed_dp_head": FIXED_DP_HEAD,
        "failure_class": FIXED_DP_FAILURE_CLASS,
        "reason": FIXED_DP_FAILURE_REASON,
        "raw_failure_receipt_sha256": value.get("raw_failure_receipt_sha256"),
        "training_eligible": False,
        "calibration_eligible": False,
        "evaluation_eligible": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    _require_sha(expected["raw_failure_receipt_sha256"], "raw_failure_receipt_sha256")
    if not _strict_equal(value, expected):
        raise ValueError("candidate0 calibration retained failure drifted")
    return expected


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    ).hexdigest()


def _require_sha(value: Any, name: str) -> None:
    if type(value) is not str or len(value) != 64 or set(value) - set("0123456789abcdef"):
        raise ValueError(f"{name} must be a lowercase SHA256")


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)
