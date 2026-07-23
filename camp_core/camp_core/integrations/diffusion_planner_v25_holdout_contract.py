from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence


HOLDOUT_IDENTITY_SCHEMA_VERSION = "camp_dp_v25_holdout_identity_v1"
EXPERIMENT_PROTOCOL_SCHEMA_VERSION = "camp_dp_v25_holdout_experiment_protocol_v1"
REPLACEMENT_EXPERIMENT_PROTOCOL_SCHEMA_VERSION = (
    "camp_dp_v25_replacement_holdout_experiment_protocol_v2"
)
FORWARD_BINDING_SCHEMA_VERSION = "camp_dp_v25_holdout_forward_binding_v1"
LATENCY_SCHEMA_VERSION = "camp_dp_v25_holdout_latency_namespaces_v1"
TERMINAL_SCHEMA_VERSION = "camp_dp_v25_holdout_unit_terminal_v1"
FATAL_SCHEMA_VERSION = "camp_dp_v25_holdout_artifact_fatal_v1"
TOMBSTONE_SCHEMA_VERSION = "camp_dp_v25_holdout_cas_tombstone_v1"

ARMS = ("candidate0", "static14d", "scene14d")
SCIENTIFIC_TERMINAL_STATUSES = (
    "complete",
    "fixed_dp_candidate_generation_capability_failure",
    "source_ineligible",
)
CAS_STATES = (
    "reserved",
    "opened_consumed",
    "terminal_success",
    "terminal_failure",
)


def normative_holdout_contract() -> dict[str, Any]:
    return {
        "schema_version": "camp_dp_v25_holdout_normative_contract_v2",
        "status": "frozen_before_fresh_b4_opening",
        "candidate0_semantics": (
            "action_equivalent_operational_default_first_default_output_alias"
        ),
        "same_forward_contract": (
            "forward_execution_id_plus_input_model_action_digest"
        ),
        "supplementary_pool_evidence_mode": (
            "same_tick_same_base_forward_supplementary"
        ),
        "holdout_identity_excludes": [
            "nonce",
            "head",
            "output_path",
            "artifact_repackaging",
        ],
        "legacy_b2_b3_cas_states": list(CAS_STATES),
        "operational_attempt_states": [
            "release_reserved",
            "release_sealed",
            "pre_exposure_failure",
            "exposure_started",
        ],
        "scientific_ledger_states": [
            "unopened",
            "exposure_started",
            "full_denominator_formed",
            "evaluated",
            "terminal_success",
            "terminal_failure",
        ],
        "scientific_identity_consumed_at_release": False,
        "scientific_exposure_atomic_boundary": (
            "immediately_before_first_real_simulator_native_dp_forward"
        ),
        "pre_exposure_operational_failure_consumes_scientific_identity": False,
        "post_exposure_failure_consumes_scientific_identity": True,
        "scientific_unit_statuses": list(SCIENTIFIC_TERMINAL_STATUSES),
        "artifact_integrity_failure_scope": "artifact_fatal_not_scientific_row",
        "terminal_truth_table": (
            "exclusive_scientific_terminal_or_artifact_fatal_v1"
        ),
        "latency_namespaces": [
            "online_operational_latency_ms",
            "supplementary_evidence_latency_ms",
            "runtime_total_observed_ms",
        ],
        "online_allowed_by_arm": {
            arm: sorted(values) for arm, values in _ONLINE_ALLOWED.items()
        },
        "supplementary_allowed_by_arm": {
            arm: sorted(values)
            for arm, values in _SUPPLEMENTARY_ALLOWED.items()
        },
        "candidate0_action_available_before_supplementary": True,
        "supplementary_may_affect_action_rng_or_next_tick": False,
        "b2_disposition": (
            "consumed_one_shot_engineering_failure_no_fresh_evaluation"
        ),
        "b2_raw_run_count": 1,
        "b2_complete_paired_row_count": 0,
        "b2_pooling_into_future_experiment_allowed": False,
        "b3_requires_exact_production_preflight": True,
        "b3_disposition": (
            "post_exposure_engineering_fatal_consumed_no_fresh_evaluation"
        ),
        "b3_raw_run_count": 1,
        "b3_complete_paired_row_count": 0,
        "b3_pooling_into_future_experiment_allowed": False,
        "b4_requires_exact_actual_native_production_preflight": True,
        "b4_candidate0_pool_contract": (
            "action_first_primary_plus_separate_supplementary_actual_native_v1"
        ),
        "fresh_open_authorized_by_contract": False,
        "outcome_fields_consumed": [],
    }

ONLINE_LATENCY_FIELDS = (
    "dp_operational_default",
    "additional_k8_generation",
    "atoms",
    "context",
    "scene_weight",
    "selector",
)
SUPPLEMENTARY_LATENCY_FIELDS = (
    "candidate_pool_generation",
    "atoms",
    "context",
    "scene_weight",
    "receipt_hashing",
)

_ONLINE_ALLOWED = {
    "candidate0": frozenset({"dp_operational_default"}),
    "static14d": frozenset(
        {
            "dp_operational_default",
            "additional_k8_generation",
            "atoms",
            "selector",
        }
    ),
    "scene14d": frozenset(ONLINE_LATENCY_FIELDS),
}
_SUPPLEMENTARY_ALLOWED = {
    "candidate0": frozenset(
        {"candidate_pool_generation", "atoms", "receipt_hashing"}
    ),
    "static14d": frozenset({"receipt_hashing"}),
    "scene14d": frozenset({"receipt_hashing"}),
}

_HOLDOUT_IDENTITY_CORE_FIELDS = frozenset(
    {
        "split",
        "scenario_manifest_sha256",
        "map_suite_payload_sha256",
        "route_census_sha256",
        "corridor_census_sha256",
        "semantic_census_sha256",
        "execution_plan_sha256",
        "seeds",
        "arm_order_commit_sha256",
        "paired_unit_count",
        "arm_run_count",
        "tick_capacity",
    }
)
HOLDOUT_IDENTITY_FIELDS = frozenset(
    {"schema_version", *_HOLDOUT_IDENTITY_CORE_FIELDS, "holdout_identity_sha256"}
)

_EXPERIMENT_PROTOCOL_CORE_FIELDS = frozenset(
    {
        "model_registry_sha256",
        "training_scale_sha256",
        "context_scaler_sha256",
        "atom_contract_sha256",
        "threshold_contract_sha256",
        "noninferiority_contract_sha256",
        "multiplicity_contract_sha256",
        "claim_contract_sha256",
        "failure_contract_sha256",
        "candidate0_semantics",
        "same_forward_contract",
        "latency_contract",
        "terminal_truth_table",
    }
)
EXPERIMENT_PROTOCOL_FIELDS = frozenset(
    {
        "schema_version",
        *_EXPERIMENT_PROTOCOL_CORE_FIELDS,
        "experiment_protocol_sha256",
    }
)
REPLACEMENT_EXPERIMENT_PROTOCOL_FIELDS = frozenset(
    {
        "schema_version",
        *_EXPERIMENT_PROTOCOL_CORE_FIELDS,
        "prior_experiment_protocol_sha256",
        "holdout_generation_rule_sha256",
        "protocol_revision",
        "scientific_rules_unchanged_from_prior",
        "experiment_protocol_sha256",
    }
)

FORWARD_BINDING_FIELDS = frozenset(
    {
        "schema_version",
        "tick_index",
        "forward_execution_id",
        "input_sha256",
        "model_sha256",
        "action_sha256",
        "candidate_pool_sha256",
        "candidate0_semantics",
        "pool_evidence_mode",
        "pool_evidence_affects_action",
        "pool_evidence_affects_rng_or_next_tick",
        "evidence_binding_sha256",
    }
)

LATENCY_FIELDS = frozenset(
    {
        "schema_version",
        "arm",
        "online_operational_latency_ms",
        "supplementary_evidence_latency_ms",
        "runtime_total_observed_ms",
        "runtime_nondecision_overhead_ms",
        "action_available_timestamp_ns",
        "supplementary_started_timestamp_ns",
        "namespace_component_sum_ms",
        "total_reconciliation_residual_ms",
        "fields_double_counted",
    }
)

TERMINAL_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "failure_class",
        "all_k_bad",
        "planned_denominator_retained",
        "scientific_evidence_eligible",
        "training_eligible",
        "calibration_eligible",
        "evaluation_eligible",
    }
)

FATAL_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "block_class",
        "reason",
        "controller_decision_root_sha256",
        "opening_release_root_sha256",
        "marker_path",
        "marker_sha256",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "attempted_unit_ordinal",
        "attempted_arm",
        "planned_arm_run_count",
        "attempted_arm_run_count",
        "complete_arm_run_count",
        "unattempted_arm_run_count",
        "outcome_fields_consumed",
        "fresh_opened_once",
        "resume_allowed",
        "new_nonce_allowed",
        "suffix_allowed",
        "full_denominator_formed",
        "next_authority",
    }
)

TOMBSTONE_FIELDS = frozenset(
    {
        "schema_version",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "reservation_commitment_sha256",
        "state",
        "history",
        "opening_attempt_count",
        "opening_release_root_sha256",
        "marker_sha256",
        "terminal_artifact_root_sha256",
        "terminal_reason",
        "outcome_evaluation_completed",
        "second_opening_allowed",
    }
)


class HoldoutArtifactFatalError(RuntimeError):
    """Integrity/harness failure that must terminate the whole artifact."""


def freeze_holdout_identity(**values: Any) -> dict[str, Any]:
    if set(values) != _HOLDOUT_IDENTITY_CORE_FIELDS:
        raise ValueError("holdout identity core field set drifted")
    split = values["split"]
    if type(split) is not str or not split.startswith("fresh_b"):
        raise ValueError("holdout split must be a versioned Fresh benchmark")
    for name in (
        "scenario_manifest_sha256",
        "map_suite_payload_sha256",
        "route_census_sha256",
        "corridor_census_sha256",
        "semantic_census_sha256",
        "execution_plan_sha256",
        "arm_order_commit_sha256",
    ):
        _require_sha(values[name], name)
    seeds = _native_seed_list(values["seeds"])
    counts: dict[str, int] = {}
    for name in ("paired_unit_count", "arm_run_count", "tick_capacity"):
        item = values[name]
        if type(item) is not int or item <= 0:
            raise ValueError(f"{name} must be a positive native integer")
        counts[name] = item
    if counts["arm_run_count"] != counts["paired_unit_count"] * len(ARMS):
        raise ValueError("holdout arm-run denominator drifted")
    core = {
        "split": split,
        "scenario_manifest_sha256": values["scenario_manifest_sha256"],
        "map_suite_payload_sha256": values["map_suite_payload_sha256"],
        "route_census_sha256": values["route_census_sha256"],
        "corridor_census_sha256": values["corridor_census_sha256"],
        "semantic_census_sha256": values["semantic_census_sha256"],
        "execution_plan_sha256": values["execution_plan_sha256"],
        "seeds": seeds,
        "arm_order_commit_sha256": values["arm_order_commit_sha256"],
        **counts,
    }
    identity_payload = {
        "schema_version": HOLDOUT_IDENTITY_SCHEMA_VERSION,
        **core,
    }
    identity_payload["holdout_identity_sha256"] = canonical_sha256(identity_payload)
    return identity_payload


def validate_holdout_identity(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != HOLDOUT_IDENTITY_FIELDS:
        raise ValueError("holdout identity field set drifted")
    expected = freeze_holdout_identity(
        **{name: value[name] for name in _HOLDOUT_IDENTITY_CORE_FIELDS}
    )
    if not strict_equal(value, expected):
        raise ValueError("holdout identity exact value drifted")
    return expected


def freeze_experiment_protocol(**values: Any) -> dict[str, Any]:
    if set(values) != _EXPERIMENT_PROTOCOL_CORE_FIELDS:
        raise ValueError("experiment protocol core field set drifted")
    for name in (
        "model_registry_sha256",
        "training_scale_sha256",
        "context_scaler_sha256",
        "atom_contract_sha256",
        "threshold_contract_sha256",
        "noninferiority_contract_sha256",
        "multiplicity_contract_sha256",
        "claim_contract_sha256",
        "failure_contract_sha256",
    ):
        _require_sha(values[name], name)
    expected_literals = {
        "candidate0_semantics": (
            "action_equivalent_operational_default_first_default_output_alias"
        ),
        "same_forward_contract": (
            "forward_execution_id_plus_input_model_action_digest"
        ),
        "latency_contract": (
            "online_operational_plus_supplementary_evidence_plus_runtime_total_v1"
        ),
        "terminal_truth_table": "exclusive_scientific_terminal_or_artifact_fatal_v1",
    }
    for name, expected in expected_literals.items():
        if values[name] != expected:
            raise ValueError(f"{name} drifted")
    core = {name: values[name] for name in sorted(_EXPERIMENT_PROTOCOL_CORE_FIELDS)}
    protocol_payload = {
        "schema_version": EXPERIMENT_PROTOCOL_SCHEMA_VERSION,
        **core,
    }
    protocol_payload["experiment_protocol_sha256"] = canonical_sha256(
        protocol_payload
    )
    return protocol_payload


def validate_experiment_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != EXPERIMENT_PROTOCOL_FIELDS:
        raise ValueError("experiment protocol field set drifted")
    expected = freeze_experiment_protocol(
        **{name: value[name] for name in _EXPERIMENT_PROTOCOL_CORE_FIELDS}
    )
    if not strict_equal(value, expected):
        raise ValueError("experiment protocol exact value drifted")
    return expected


def freeze_replacement_experiment_protocol(
    *,
    prior_experiment_protocol: Mapping[str, Any],
    holdout_generation_rule_sha256: str,
    protocol_revision: str,
) -> dict[str, Any]:
    """Freeze a new holdout protocol identity without changing science rules.

    B4 uses a prospectively generated, clone-disjoint holdout.  Its protocol
    hash must therefore differ from the consumed B3 protocol even though every
    model, atom, margin, multiplicity, failure, and claim rule is unchanged.
    """

    prior = validate_experiment_protocol(prior_experiment_protocol)
    _require_sha(holdout_generation_rule_sha256, "holdout_generation_rule_sha256")
    if protocol_revision != "fresh_b4_outcome_blind_extension_v1":
        raise ValueError("replacement holdout protocol revision drifted")
    payload = {
        "schema_version": REPLACEMENT_EXPERIMENT_PROTOCOL_SCHEMA_VERSION,
        **{
            name: prior[name]
            for name in sorted(_EXPERIMENT_PROTOCOL_CORE_FIELDS)
        },
        "prior_experiment_protocol_sha256": prior[
            "experiment_protocol_sha256"
        ],
        "holdout_generation_rule_sha256": holdout_generation_rule_sha256,
        "protocol_revision": protocol_revision,
        "scientific_rules_unchanged_from_prior": True,
    }
    payload["experiment_protocol_sha256"] = canonical_sha256(payload)
    if (
        payload["experiment_protocol_sha256"]
        == prior["experiment_protocol_sha256"]
    ):
        raise ValueError("replacement holdout protocol hash was reused")
    return payload


def validate_replacement_experiment_protocol(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != REPLACEMENT_EXPERIMENT_PROTOCOL_FIELDS:
        raise ValueError("replacement experiment protocol field set drifted")
    prior = {
        "schema_version": EXPERIMENT_PROTOCOL_SCHEMA_VERSION,
        **{
            name: value[name]
            for name in sorted(_EXPERIMENT_PROTOCOL_CORE_FIELDS)
        },
    }
    prior["experiment_protocol_sha256"] = canonical_sha256(prior)
    if (
        prior["experiment_protocol_sha256"]
        != value["prior_experiment_protocol_sha256"]
    ):
        raise ValueError("replacement protocol prior-science binding drifted")
    expected = freeze_replacement_experiment_protocol(
        prior_experiment_protocol=prior,
        holdout_generation_rule_sha256=value[
            "holdout_generation_rule_sha256"
        ],
        protocol_revision=value["protocol_revision"],
    )
    if not strict_equal(value, expected):
        raise ValueError("replacement experiment protocol exact value drifted")
    return expected


def validate_holdout_experiment_protocol(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("holdout experiment protocol must be an object")
    if value.get("schema_version") == EXPERIMENT_PROTOCOL_SCHEMA_VERSION:
        return validate_experiment_protocol(value)
    if (
        value.get("schema_version")
        == REPLACEMENT_EXPERIMENT_PROTOCOL_SCHEMA_VERSION
    ):
        return validate_replacement_experiment_protocol(value)
    raise ValueError("holdout experiment protocol schema drifted")


def freeze_forward_binding(
    *,
    tick_index: int,
    input_sha256: str,
    model_sha256: str,
    action_sha256: str,
    candidate_pool_sha256: str,
) -> dict[str, Any]:
    if type(tick_index) is not int or tick_index < 0:
        raise ValueError("tick_index must be a nonnegative native integer")
    for name, value in {
        "input_sha256": input_sha256,
        "model_sha256": model_sha256,
        "action_sha256": action_sha256,
        "candidate_pool_sha256": candidate_pool_sha256,
    }.items():
        _require_sha(value, name)
    identity = {
        "tick_index": tick_index,
        "input_sha256": input_sha256,
        "model_sha256": model_sha256,
        "action_sha256": action_sha256,
    }
    result = {
        "schema_version": FORWARD_BINDING_SCHEMA_VERSION,
        "tick_index": tick_index,
        "forward_execution_id": canonical_sha256(identity),
        "input_sha256": input_sha256,
        "model_sha256": model_sha256,
        "action_sha256": action_sha256,
        "candidate_pool_sha256": candidate_pool_sha256,
        "candidate0_semantics": (
            "action_equivalent_operational_default_first_default_output_alias"
        ),
        "pool_evidence_mode": "same_tick_same_base_forward_supplementary",
        "pool_evidence_affects_action": False,
        "pool_evidence_affects_rng_or_next_tick": False,
    }
    result["evidence_binding_sha256"] = canonical_sha256(result)
    return result


def validate_forward_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != FORWARD_BINDING_FIELDS:
        raise ValueError("forward binding field set drifted")
    expected = freeze_forward_binding(
        tick_index=value["tick_index"],
        input_sha256=value["input_sha256"],
        model_sha256=value["model_sha256"],
        action_sha256=value["action_sha256"],
        candidate_pool_sha256=value["candidate_pool_sha256"],
    )
    if not strict_equal(value, expected):
        raise ValueError("forward binding exact value drifted")
    return expected


def freeze_latency_namespaces(
    *,
    arm: str,
    online_operational_latency_ms: Mapping[str, Any],
    supplementary_evidence_latency_ms: Mapping[str, Any],
    runtime_total_observed_ms: Any,
    runtime_nondecision_overhead_ms: Any,
    action_available_timestamp_ns: int,
    supplementary_started_timestamp_ns: int,
) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError("holdout latency arm drifted")
    online = _latency_mapping(
        online_operational_latency_ms,
        ONLINE_LATENCY_FIELDS,
        "online_operational_latency_ms",
    )
    supplementary = _latency_mapping(
        supplementary_evidence_latency_ms,
        SUPPLEMENTARY_LATENCY_FIELDS,
        "supplementary_evidence_latency_ms",
    )
    for name, allowed, values in (
        ("online", _ONLINE_ALLOWED[arm], online),
        ("supplementary", _SUPPLEMENTARY_ALLOWED[arm], supplementary),
    ):
        forbidden_nonzero = {
            field for field, value in values.items() if field not in allowed and value != 0.0
        }
        if forbidden_nonzero:
            raise ValueError(
                f"{arm} {name} latency contains forbidden nonzero fields: "
                f"{sorted(forbidden_nonzero)}"
            )
    if (
        type(action_available_timestamp_ns) is not int
        or type(supplementary_started_timestamp_ns) is not int
        or action_available_timestamp_ns < 0
        or supplementary_started_timestamp_ns < action_available_timestamp_ns
    ):
        raise ValueError("supplementary evidence must start after action availability")
    total = _finite_nonnegative(
        runtime_total_observed_ms, "runtime_total_observed_ms"
    )
    overhead = _finite_nonnegative(
        runtime_nondecision_overhead_ms, "runtime_nondecision_overhead_ms"
    )
    component_sum = float(sum(online.values()) + sum(supplementary.values()) + overhead)
    residual = float(total - component_sum)
    if abs(residual) > 1e-9:
        raise ValueError("holdout latency total does not reconcile")
    return {
        "schema_version": LATENCY_SCHEMA_VERSION,
        "arm": arm,
        "online_operational_latency_ms": online,
        "supplementary_evidence_latency_ms": supplementary,
        "runtime_total_observed_ms": total,
        "runtime_nondecision_overhead_ms": overhead,
        "action_available_timestamp_ns": action_available_timestamp_ns,
        "supplementary_started_timestamp_ns": supplementary_started_timestamp_ns,
        "namespace_component_sum_ms": component_sum,
        "total_reconciliation_residual_ms": residual,
        "fields_double_counted": [],
    }


def validate_latency_namespaces(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != LATENCY_FIELDS:
        raise ValueError("holdout latency field set drifted")
    expected = freeze_latency_namespaces(
        arm=value["arm"],
        online_operational_latency_ms=value["online_operational_latency_ms"],
        supplementary_evidence_latency_ms=value[
            "supplementary_evidence_latency_ms"
        ],
        runtime_total_observed_ms=value["runtime_total_observed_ms"],
        runtime_nondecision_overhead_ms=value[
            "runtime_nondecision_overhead_ms"
        ],
        action_available_timestamp_ns=value["action_available_timestamp_ns"],
        supplementary_started_timestamp_ns=value[
            "supplementary_started_timestamp_ns"
        ],
    )
    if not strict_equal(value, expected):
        raise ValueError("holdout latency exact value drifted")
    return expected


def freeze_unit_terminal(
    *,
    status: str,
    failure_class: str | None,
    all_k_bad: bool,
) -> dict[str, Any]:
    if status not in SCIENTIFIC_TERMINAL_STATUSES:
        raise HoldoutArtifactFatalError("non-scientific status is artifact-fatal")
    if type(all_k_bad) is not bool:
        raise TypeError("all_k_bad must be a native bool")
    if status == "complete":
        if failure_class is not None:
            raise ValueError("complete terminal cannot carry a failure class")
        scientific = True
        evaluation = True
    elif status == "fixed_dp_candidate_generation_capability_failure":
        if failure_class != "invalid_k8_heading_norm_envelope":
            raise ValueError("fixed-DP capability failure taxonomy drifted")
        if all_k_bad:
            raise ValueError("a fixed-DP generation failure cannot claim all-K-bad")
        scientific = True
        evaluation = False
    else:
        if failure_class != "preregistered_source_ineligible":
            raise ValueError("source-ineligible failure taxonomy drifted")
        if all_k_bad:
            raise ValueError("source-ineligible cannot claim all-K-bad")
        scientific = True
        evaluation = False
    return {
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "status": status,
        "failure_class": failure_class,
        "all_k_bad": all_k_bad,
        "planned_denominator_retained": True,
        "scientific_evidence_eligible": scientific,
        "training_eligible": False,
        "calibration_eligible": False,
        "evaluation_eligible": evaluation,
    }


def validate_unit_terminal(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != TERMINAL_FIELDS:
        raise ValueError("holdout unit terminal field set drifted")
    expected = freeze_unit_terminal(
        status=value["status"],
        failure_class=value["failure_class"],
        all_k_bad=value["all_k_bad"],
    )
    if not strict_equal(value, expected):
        raise ValueError("holdout unit terminal exact value drifted")
    return expected


def freeze_fatal_artifact(
    *,
    block_class: str,
    reason: str,
    controller_decision_root_sha256: str,
    opening_release_root_sha256: str,
    marker_path: str | None,
    marker_sha256: str | None,
    holdout_identity_sha256: str,
    experiment_protocol_sha256: str,
    attempted_unit_ordinal: int | None,
    attempted_arm: str | None,
    planned_arm_run_count: int,
    attempted_arm_run_count: int,
    complete_arm_run_count: int,
    outcome_fields_consumed: Sequence[str],
    fresh_opened_once: bool,
) -> dict[str, Any]:
    if type(block_class) is not str or not block_class:
        raise ValueError("fatal block_class must be nonempty")
    if type(reason) is not str or not reason:
        raise ValueError("fatal reason must be nonempty")
    for name, value in {
        "controller_decision_root_sha256": controller_decision_root_sha256,
        "opening_release_root_sha256": opening_release_root_sha256,
        "holdout_identity_sha256": holdout_identity_sha256,
        "experiment_protocol_sha256": experiment_protocol_sha256,
    }.items():
        _require_sha(value, name)
    if marker_path is None:
        if marker_sha256 is not None or fresh_opened_once is not False:
            raise ValueError("pre-marker fatal state drifted")
    else:
        if type(marker_path) is not str or not marker_path.startswith(
            "/root/autodl-tmp/"
        ):
            raise ValueError("fatal marker path drifted")
        _require_sha(marker_sha256, "marker_sha256")
        if fresh_opened_once is not True:
            raise ValueError("post-marker fatal state drifted")
    if attempted_unit_ordinal is not None and (
        type(attempted_unit_ordinal) is not int or attempted_unit_ordinal < 0
    ):
        raise ValueError("attempted_unit_ordinal drifted")
    if attempted_arm is not None and attempted_arm not in ARMS:
        raise ValueError("attempted_arm drifted")
    if (attempted_unit_ordinal is None) != (attempted_arm is None):
        raise ValueError("attempted unit/arm must be jointly present or absent")
    for name, value in {
        "planned_arm_run_count": planned_arm_run_count,
        "attempted_arm_run_count": attempted_arm_run_count,
        "complete_arm_run_count": complete_arm_run_count,
    }.items():
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a nonnegative native integer")
    if not 0 <= complete_arm_run_count <= attempted_arm_run_count <= planned_arm_run_count:
        raise ValueError("fatal partial denominator counts drifted")
    outcomes = _string_list(outcome_fields_consumed, "outcome_fields_consumed")
    return {
        "schema_version": FATAL_SCHEMA_VERSION,
        "status": "artifact_fatal",
        "block_class": block_class,
        "reason": reason,
        "controller_decision_root_sha256": controller_decision_root_sha256,
        "opening_release_root_sha256": opening_release_root_sha256,
        "marker_path": marker_path,
        "marker_sha256": marker_sha256,
        "holdout_identity_sha256": holdout_identity_sha256,
        "experiment_protocol_sha256": experiment_protocol_sha256,
        "attempted_unit_ordinal": attempted_unit_ordinal,
        "attempted_arm": attempted_arm,
        "planned_arm_run_count": planned_arm_run_count,
        "attempted_arm_run_count": attempted_arm_run_count,
        "complete_arm_run_count": complete_arm_run_count,
        "unattempted_arm_run_count": planned_arm_run_count
        - attempted_arm_run_count,
        "outcome_fields_consumed": outcomes,
        "fresh_opened_once": fresh_opened_once,
        "resume_allowed": False,
        "new_nonce_allowed": False,
        "suffix_allowed": False,
        "full_denominator_formed": False,
        "next_authority": "ultra_read_only_failure_closeout",
    }


def validate_fatal_artifact(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != FATAL_FIELDS:
        raise ValueError("fatal artifact field set drifted")
    expected = freeze_fatal_artifact(
        block_class=value["block_class"],
        reason=value["reason"],
        controller_decision_root_sha256=value[
            "controller_decision_root_sha256"
        ],
        opening_release_root_sha256=value["opening_release_root_sha256"],
        marker_path=value["marker_path"],
        marker_sha256=value["marker_sha256"],
        holdout_identity_sha256=value["holdout_identity_sha256"],
        experiment_protocol_sha256=value["experiment_protocol_sha256"],
        attempted_unit_ordinal=value["attempted_unit_ordinal"],
        attempted_arm=value["attempted_arm"],
        planned_arm_run_count=value["planned_arm_run_count"],
        attempted_arm_run_count=value["attempted_arm_run_count"],
        complete_arm_run_count=value["complete_arm_run_count"],
        outcome_fields_consumed=value["outcome_fields_consumed"],
        fresh_opened_once=value["fresh_opened_once"],
    )
    if not strict_equal(value, expected):
        raise ValueError("fatal artifact exact value drifted")
    return expected


def freeze_tombstone(
    *,
    holdout_identity_sha256: str,
    experiment_protocol_sha256: str,
    reservation_commitment_sha256: str,
    state: str,
    history: Sequence[Mapping[str, Any]],
    opening_attempt_count: int,
    opening_release_root_sha256: str | None,
    marker_sha256: str | None,
    terminal_artifact_root_sha256: str | None,
    terminal_reason: str | None,
    outcome_evaluation_completed: bool,
) -> dict[str, Any]:
    _require_sha(holdout_identity_sha256, "holdout_identity_sha256")
    _require_sha(experiment_protocol_sha256, "experiment_protocol_sha256")
    _require_sha(
        reservation_commitment_sha256, "reservation_commitment_sha256"
    )
    if state not in CAS_STATES:
        raise ValueError("holdout CAS state drifted")
    events = _tombstone_history(history)
    if not events or events[-1]["state"] != state:
        raise ValueError("holdout CAS history/current state drifted")
    expected_histories = {
        "reserved": ["reserved"],
        "opened_consumed": ["reserved", "opened_consumed"],
        "terminal_success": [
            "reserved",
            "opened_consumed",
            "terminal_success",
        ],
        "terminal_failure": [
            "reserved",
            "opened_consumed",
            "terminal_failure",
        ],
    }
    expected_prefix = expected_histories[state]
    if [event["state"] for event in events] != expected_prefix:
        raise ValueError("holdout CAS transition order drifted")
    if type(opening_attempt_count) is not int or opening_attempt_count not in (0, 1):
        raise ValueError("opening_attempt_count drifted")
    terminal = state in {"terminal_success", "terminal_failure"}
    opened = state != "reserved"
    for name, value in {
        "opening_release_root_sha256": opening_release_root_sha256,
        "marker_sha256": marker_sha256,
    }.items():
        if opened:
            _require_sha(value, name)
        elif value is not None:
            raise ValueError(f"reserved tombstone cannot bind {name}")
    if terminal:
        _require_sha(
            terminal_artifact_root_sha256, "terminal_artifact_root_sha256"
        )
        if type(terminal_reason) is not str or not terminal_reason:
            raise ValueError("terminal tombstone reason is missing")
    elif terminal_artifact_root_sha256 is not None or terminal_reason is not None:
        raise ValueError("nonterminal tombstone carries terminal evidence")
    if type(outcome_evaluation_completed) is not bool:
        raise TypeError("outcome_evaluation_completed must be a native bool")
    if state != "terminal_success" and outcome_evaluation_completed:
        raise ValueError("non-success tombstone cannot claim completed evaluation")
    return {
        "schema_version": TOMBSTONE_SCHEMA_VERSION,
        "holdout_identity_sha256": holdout_identity_sha256,
        "experiment_protocol_sha256": experiment_protocol_sha256,
        "reservation_commitment_sha256": reservation_commitment_sha256,
        "state": state,
        "history": events,
        "opening_attempt_count": opening_attempt_count,
        "opening_release_root_sha256": opening_release_root_sha256,
        "marker_sha256": marker_sha256,
        "terminal_artifact_root_sha256": terminal_artifact_root_sha256,
        "terminal_reason": terminal_reason,
        "outcome_evaluation_completed": outcome_evaluation_completed,
        "second_opening_allowed": False,
    }


def validate_tombstone(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != TOMBSTONE_FIELDS:
        raise ValueError("holdout tombstone field set drifted")
    expected = freeze_tombstone(
        holdout_identity_sha256=value["holdout_identity_sha256"],
        experiment_protocol_sha256=value["experiment_protocol_sha256"],
        reservation_commitment_sha256=value["reservation_commitment_sha256"],
        state=value["state"],
        history=value["history"],
        opening_attempt_count=value["opening_attempt_count"],
        opening_release_root_sha256=value["opening_release_root_sha256"],
        marker_sha256=value["marker_sha256"],
        terminal_artifact_root_sha256=value["terminal_artifact_root_sha256"],
        terminal_reason=value["terminal_reason"],
        outcome_evaluation_completed=value["outcome_evaluation_completed"],
    )
    if not strict_equal(value, expected):
        raise ValueError("holdout tombstone exact value drifted")
    return expected


def reserve_holdout_identity(
    cas_root: Path,
    *,
    holdout_identity: Mapping[str, Any],
    experiment_protocol: Mapping[str, Any],
    reservation_commitment_sha256: str,
) -> Path:
    identity = validate_holdout_identity(holdout_identity)
    protocol = validate_experiment_protocol(experiment_protocol)
    root = Path(cas_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{identity['holdout_identity_sha256']}.json"
    tombstone = freeze_tombstone(
        holdout_identity_sha256=identity["holdout_identity_sha256"],
        experiment_protocol_sha256=protocol["experiment_protocol_sha256"],
        reservation_commitment_sha256=_require_sha(
            reservation_commitment_sha256, "reservation_commitment_sha256"
        ),
        state="reserved",
        history=[{"state": "reserved"}],
        opening_attempt_count=0,
        opening_release_root_sha256=None,
        marker_sha256=None,
        terminal_artifact_root_sha256=None,
        terminal_reason=None,
        outcome_evaluation_completed=False,
    )
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        os.write(descriptor, canonical_json_bytes(tombstone))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return target


def install_terminal_tombstone(
    cas_root: Path,
    *,
    tombstone: Mapping[str, Any],
) -> Path:
    value = validate_tombstone(tombstone)
    if value["state"] not in {"terminal_success", "terminal_failure"}:
        raise ValueError("only a terminal tombstone may be installed directly")
    root = Path(cas_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{value['holdout_identity_sha256']}.json"
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        os.write(descriptor, canonical_json_bytes(value))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return target


def transition_holdout_identity(
    tombstone_path: Path,
    *,
    expected_state: str,
    next_state: str,
    opening_release_root_sha256: str | None = None,
    marker_sha256: str | None = None,
    terminal_artifact_root_sha256: str | None = None,
    terminal_reason: str | None = None,
    outcome_evaluation_completed: bool = False,
) -> dict[str, Any]:
    path = Path(tombstone_path)
    transition_lock = path.with_suffix(".transition.lock")
    lock_descriptor = os.open(
        transition_lock,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        os.write(lock_descriptor, b"holdout-cas-transition\n")
        os.fsync(lock_descriptor)
    finally:
        os.close(lock_descriptor)
    try:
        current = validate_tombstone(_strict_canonical_json(path))
        if current["state"] != expected_state:
            raise FileExistsError("holdout identity is already consumed or terminal")
        allowed = {
            ("reserved", "opened_consumed"),
            ("opened_consumed", "terminal_success"),
            ("opened_consumed", "terminal_failure"),
        }
        if (expected_state, next_state) not in allowed:
            raise ValueError("holdout CAS transition is not allowed")
        events = [*current["history"], {"state": next_state}]
        updated = freeze_tombstone(
            holdout_identity_sha256=current["holdout_identity_sha256"],
            experiment_protocol_sha256=current["experiment_protocol_sha256"],
            reservation_commitment_sha256=current[
                "reservation_commitment_sha256"
            ],
            state=next_state,
            history=events,
            opening_attempt_count=1,
            opening_release_root_sha256=(
                opening_release_root_sha256
                if expected_state == "reserved"
                else current["opening_release_root_sha256"]
            ),
            marker_sha256=(
                marker_sha256
                if expected_state == "reserved"
                else current["marker_sha256"]
            ),
            terminal_artifact_root_sha256=terminal_artifact_root_sha256,
            terminal_reason=terminal_reason,
            outcome_evaluation_completed=outcome_evaluation_completed,
        )
        temporary = path.with_suffix(".tmp")
        descriptor = os.open(
            temporary,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_BINARY", 0),
            0o600,
        )
        try:
            os.write(descriptor, canonical_json_bytes(updated))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, path)
        return updated
    finally:
        transition_lock.unlink(missing_ok=True)


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _strict_canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key in {path}: {key}")
            result[key] = value
        return result

    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite token in {path}: {token}")
        ),
    )
    if type(value) is not dict or raw != canonical_json_bytes(value):
        raise ValueError(f"noncanonical holdout CAS object: {path}")
    return value


def _latency_mapping(
    value: Mapping[str, Any], fields: Sequence[str], label: str
) -> dict[str, float]:
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError(f"{label} field set drifted")
    return {field: _finite_nonnegative(value[field], f"{label}.{field}") for field in fields}


def _finite_nonnegative(value: Any, name: str) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        raise TypeError(f"{name} must be a native number")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return result


def _native_seed_list(value: Any) -> list[int]:
    if (
        type(value) is not list
        or not value
        or any(type(item) is not int or item < 0 for item in value)
        or len(value) != len(set(value))
    ):
        raise ValueError("holdout seeds must be unique native nonnegative integers")
    return list(value)


def _string_list(value: Sequence[str], name: str) -> list[str]:
    if type(value) is not list or any(type(item) is not str or not item for item in value):
        raise ValueError(f"{name} must be a list of nonempty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} must not contain duplicates")
    return list(value)


def _tombstone_history(value: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if type(value) is not list:
        raise TypeError("tombstone history must be a list")
    result: list[dict[str, str]] = []
    for item in value:
        if type(item) is not dict or set(item) != {"state"} or item["state"] not in CAS_STATES:
            raise ValueError("tombstone history row drifted")
        result.append({"state": item["state"]})
    return result


def _require_sha(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return value
