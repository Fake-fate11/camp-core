from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .diffusion_planner_v25_calibration import (
    FIXED_DP_HEAD,
    project_candidate0_ni_calibration_row,
)
from .diffusion_planner_v25_signal_complete_plan import (
    validate_signal_complete_execution_plan,
)


SCHEMA_VERSION = "camp_dp_v25_candidate0_calibration_corpus_projection_v1"
RUN_RESULT_SCHEMA_VERSION = "camp_dp_v25_candidate0_calibration_run_result_v1"
FAILURE_SCHEMA_VERSION = "camp_dp_v25_candidate0_calibration_retained_failure_v1"
FIXED_DP_FAILURE_CLASS = "fixed_dp_candidate_generation_capability_failure"
FIXED_DP_FAILURE_REASON = "invalid_k8_heading_norm_envelope"


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
                cluster_id=identity["map_geometry_sha256"],
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
        "independent_calibration_cluster_definition": "map_geometry_sha256",
        "independent_calibration_cluster_count": len(
            {row["cluster_id"] for row in candidate0_rows}
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
        "independent_calibration_cluster_definition",
        "independent_calibration_cluster_count", "candidate0_rows",
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
        "independent_calibration_cluster_definition": "map_geometry_sha256",
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
